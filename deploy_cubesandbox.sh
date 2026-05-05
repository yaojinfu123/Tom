#!/bin/bash
#
# CubeSandbox 一键部署脚本
# 适用于: WSL2 / Linux 物理机 / 云裸金属服务器
#
# 环境要求:
# - KVM 支持的 x86_64 Linux 环境
# - 至少 8GB 内存 (推荐 16GB+)
# - 至少 50GB 磁盘空间
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          CubeSandbox 部署脚本                            ║"
    echo "║     腾讯云开源 AI Agent 安全沙箱服务                      ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "建议使用 root 用户运行此脚本"
        log_info "尝试使用 sudo..."
        exec sudo "$0" "$@"
    fi
}

check_kvm() {
    log_info "检查 KVM 支持..."

    if [[ ! -e /dev/kvm ]]; then
        log_error "未找到 /dev/kvm 设备"
        log_error "请确保:"
        echo "  1. CPU 支持虚拟化 (Intel VT-x 或 AMD-V)"
        echo "  2. BIOS 中已启用虚拟化"
        echo "  3. 已加载 KVM 模块"
        echo ""
        echo "尝试加载 KVM 模块:"
        if grep -q "vmx" /proc/cpuinfo 2>/dev/null; then
            modprobe kvm_intel 2>/dev/null || true
        elif grep -q "svm" /proc/cpuinfo 2>/dev/null; then
            modprobe kvm_amd 2>/dev/null || true
        fi
        modprobe kvm 2>/dev/null || true

        if [[ -e /dev/kvm ]]; then
            log_info "KVM 模块加载成功!"
        else
            log_error "无法加载 KVM 模块，请检查系统配置"
            exit 1
        fi
    else
        log_info "KVM 设备可用: /dev/kvm"
    fi

    if ! ls -la /dev/kvm | grep -q "$(whoami)"; then
        log_warn "当前用户无 /dev/kvm 访问权限，尝试添加到 kvm 组..."
        usermod -aG kvm "$(whoami)" 2>/dev/null || true
        log_warn "请重新登录或重启系统以使组权限生效"
    fi
}

check_system() {
    log_info "检查系统环境..."

    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    local avail_disk=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')

    log_info "总内存: ${total_mem}MB"
    log_info "可用磁盘: ${avail_disk}GB"

    if [[ $total_mem -lt 8000 ]]; then
        log_warn "内存不足 8GB，可能影响沙箱性能"
    fi

    if [[ $avail_disk -lt 30 ]]; then
        log_warn "磁盘空间不足 30GB，可能无法完成安装"
    fi
}

install_dependencies() {
    log_info "安装依赖包..."

    if command -v apt-get &>/dev/null; then
        apt-get update
        apt-get install -y wget curl git qemu-utils qemu-system-x86 ripgrep docker.io docker-compose
    elif command -v yum &>/dev/null; then
        yum install -y wget curl git qemu-img qemu-kvm ripgrep docker docker-compose
    elif command -v dnf &>/dev/null; then
        dnf install -y wget curl git qemu-img qemu-kvm ripgrep docker docker-compose
    else
        log_error "不支持的包管理器，请手动安装依赖"
        exit 1
    fi

    systemctl enable docker
    systemctl start docker
}

clone_repository() {
    local install_dir="${1:-/opt/CubeSandbox}"

    log_info "克隆 CubeSandbox 仓库..."

    if [[ -d "$install_dir" ]]; then
        log_warn "目录已存在: $install_dir"
        read -p "是否删除并重新克隆? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$install_dir"
        else
            log_info "使用现有目录"
            return
        fi
    fi

    if [[ "$USE_MIRROR" == "cn" ]]; then
        git clone https://cnb.cool/CubeSandbox/CubeSandbox "$install_dir"
    else
        git clone https://github.com/TencentCloud/CubeSandbox.git "$install_dir"
    fi

    log_info "仓库克隆完成: $install_dir"
}

prepare_dev_env() {
    local install_dir="${1:-/opt/CubeSandbox}"

    log_info "准备开发环境..."

    cd "$install_dir/dev-env"

    if [[ ! -f "prepare_image.sh" ]]; then
        log_error "未找到 prepare_image.sh 脚本"
        exit 1
    fi

    chmod +x *.sh 2>/dev/null || true

    if command -v dos2unix &>/dev/null; then
        dos2unix *.sh 2>/dev/null || true
    fi

    log_info "下载并准备虚拟机镜像 (约 400MB)..."
    ./prepare_image.sh
}

start_vm() {
    local install_dir="${1:-/opt/CubeSandbox}"
    local memory="${VM_MEMORY_MB:-8192}"

    log_info "启动虚拟机 (内存: ${memory}MB)..."
    log_info "按 Ctrl+A 然后按 X 退出虚拟机"

    cd "$install_dir/dev-env"
    VM_MEMORY_MB=$memory ./run_vm.sh
}

install_cubesandbox() {
    log_info "在虚拟机中安装 CubeSandbox..."
    log_info "请先在另一个终端运行: ./login.sh"
    log_info "然后在虚拟机中执行安装命令..."

    echo ""
    echo "国内用户请执行:"
    echo "  curl -sL https://cnb.cool/CubeSandbox/CubeSandbox/-/git/raw/master/deploy/one-click/online-install.sh | MIRROR=cn bash"
    echo ""
    echo "海外用户请执行:"
    echo "  curl -sL https://github.com/tencentcloud/CubeSandbox/raw/master/deploy/one-click/online-install.sh | bash"
}

create_template() {
    log_info "创建代码解释器模板..."

    echo "执行以下命令创建模板:"
    echo ""
    echo "  cubemastercli tpl create-from-image \\"
    echo "    --image ccr.ccs.tencentyun.com/ags-image/sandbox-code:latest \\"
    echo "    --writable-layer-size 1G \\"
    echo "    --expose-port 49999 \\"
    echo "    --expose-port 49983 \\"
    echo "    --probe 49999"
    echo ""
    echo "查看构建进度:"
    echo "  cubemastercli tpl watch --job-id <job_id>"
    echo ""
    echo "模板就绪后，记录 template_id 用于后续使用"
}

show_env_config() {
    log_info "环境变量配置"

    echo ""
    echo "请设置以下环境变量:"
    echo ""
    echo "  export E2B_API_URL=\"http://127.0.0.1:3000\""
    echo "  export E2B_API_KEY=\"dummy\""
    echo "  export CUBE_TEMPLATE_ID=\"<your-template-id>\""
    echo "  export SSL_CERT_FILE=\"/root/.local/share/mkcert/rootCA.pem\""
    echo ""
}

run_test() {
    log_info "运行测试..."

    pip install e2b-code-interpreter 2>/dev/null || pip3 install e2b-code-interpreter

    python3 -c "
import os
from e2b_code_interpreter import Sandbox

template_id = os.environ.get('CUBE_TEMPLATE_ID', '')
if not template_id:
    print('请设置 CUBE_TEMPLATE_ID 环境变量')
    exit(1)

with Sandbox.create(template_id=template_id) as sandbox:
    result = sandbox.run_code('print(\"Hello from CubeSandbox!\")')
    print(result)
"
}

usage() {
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  check       检查系统环境"
    echo "  install     安装依赖并克隆仓库"
    echo "  prepare     准备开发环境 (下载镜像)"
    echo "  start       启动虚拟机"
    echo "  deploy      完整部署流程"
    echo "  test        运行测试"
    echo ""
    echo "环境变量:"
    echo "  USE_MIRROR=cn      使用国内镜像"
    echo "  VM_MEMORY_MB=8192  虚拟机内存 (MB)"
    echo ""
    echo "示例:"
    echo "  $0 check"
    echo "  USE_MIRROR=cn $0 deploy"
}

main() {
    local command="${1:-deploy}"
    local install_dir="${INSTALL_DIR:-/opt/CubeSandbox}"

    print_banner

    case "$command" in
        check)
            check_kvm
            check_system
            ;;
        install)
            check_root "$@"
            check_kvm
            install_dependencies
            clone_repository "$install_dir"
            ;;
        prepare)
            prepare_dev_env "$install_dir"
            ;;
        start)
            start_vm "$install_dir"
            ;;
        deploy)
            check_root "$@"
            check_kvm
            check_system
            install_dependencies
            clone_repository "$install_dir"
            prepare_dev_env "$install_dir"
            echo ""
            install_cubesandbox
            echo ""
            create_template
            show_env_config
            ;;
        test)
            run_test
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "未知命令: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
