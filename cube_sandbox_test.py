"""
CubeSandbox 使用示例代码
腾讯云开源的 AI Agent 安全沙箱服务

环境要求:
- KVM 支持的 x86_64 Linux 环境 (WSL2 / 物理机 / 云裸金属)
- Python >= 3.10
- e2b-code-interpreter 包

安装依赖:
    pip install e2b-code-interpreter

环境变量设置:
    export E2B_API_URL="http://your-cube-server:3000"
    export E2B_API_KEY="dummy"
    export CUBE_TEMPLATE_ID="your-template-id"
"""

import os
import sys
import time
import json
import httpx
from typing import Optional, Any


class CubeSandboxClient:
    """CubeSandbox 客户端封装类"""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        template_id: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.api_url = api_url or os.environ.get("E2B_API_URL", "http://127.0.0.1:3000")
        self.api_key = api_key or os.environ.get("E2B_API_KEY", "dummy")
        self.template_id = template_id or os.environ.get("CUBE_TEMPLATE_ID", "")
        self.timeout = timeout
        self._sandbox: Optional[Any] = None

    def check_connection(self) -> dict:
        """
        测试与 CubeSandbox 服务的连通性

        Returns:
            dict: 包含连接状态和信息的字典
        """
        result = {
            "connected": False,
            "api_url": self.api_url,
            "error": None,
            "latency_ms": None
        }

        try:
            start_time = time.time()

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/health",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

            end_time = time.time()
            result["latency_ms"] = round((end_time - start_time) * 1000, 2)

            if response.status_code == 200:
                result["connected"] = True
                result["status"] = response.json() if response.text else {"status": "ok"}
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

        except httpx.ConnectError as e:
            result["error"] = f"连接失败: {str(e)}"
        except httpx.TimeoutException:
            result["error"] = f"连接超时 (>{self.timeout}s)"
        except Exception as e:
            result["error"] = f"未知错误: {str(e)}"

        return result

    def list_templates(self) -> dict:
        """
        列出可用的沙箱模板

        Returns:
            dict: 模板列表信息
        """
        result = {
            "success": False,
            "templates": [],
            "error": None
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/templates",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

            if response.status_code == 200:
                result["success"] = True
                result["templates"] = response.json()
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def create_sandbox(self) -> Any:
        """
        创建一个新的沙箱实例

        Returns:
            Sandbox 对象
        """
        try:
            from e2b_code_interpreter import Sandbox

            self._sandbox = Sandbox.create(template_id=self.template_id)
            return self._sandbox
        except ImportError:
            raise ImportError(
                "请先安装 e2b-code-interpreter: pip install e2b-code-interpreter"
            )

    def run_code(self, code: str, language: str = "python") -> dict:
        """
        在沙箱中执行代码

        Args:
            code: 要执行的代码
            language: 编程语言 (python, javascript, etc.)

        Returns:
            dict: 执行结果
        """
        if not self._sandbox:
            self.create_sandbox()

        result = self._sandbox.run_code(code, language=language)
        return result

    def run_shell(self, command: str) -> dict:
        """
        在沙箱中执行 Shell 命令

        Args:
            command: Shell 命令

        Returns:
            dict: 执行结果
        """
        if not self._sandbox:
            self.create_sandbox()

        result = self._sandbox.shell.run(command)
        return result

    def close(self):
        """关闭沙箱实例"""
        if self._sandbox:
            self._sandbox.close()
            self._sandbox = None


def test_connection_basic():
    """基础连通性测试"""
    print("=" * 60)
    print("CubeSandbox 连通性测试")
    print("=" * 60)

    client = CubeSandboxClient()

    print(f"\nAPI URL: {client.api_url}")
    print(f"Template ID: {client.template_id or '(未设置)'}")
    print(f"API Key: {'*' * 8 if client.api_key else '(未设置)'}")

    print("\n正在测试连接...")
    result = client.check_connection()

    print("\n" + "-" * 40)
    if result["connected"]:
        print("✅ 连接成功!")
        print(f"延迟: {result['latency_ms']} ms")
        print(f"状态: {result.get('status', {})}")
    else:
        print("❌ 连接失败!")
        print(f"错误: {result['error']}")

    print("-" * 40)
    return result


def test_sandbox_operations():
    """沙箱操作测试"""
    print("\n" + "=" * 60)
    print("CubeSandbox 沙箱操作测试")
    print("=" * 60)

    client = CubeSandboxClient()

    try:
        print("\n1. 创建沙箱...")
        sandbox = client.create_sandbox()
        print("✅ 沙箱创建成功!")

        print("\n2. 执行 Python 代码...")
        code = """
import sys
print(f"Python 版本: {sys.version}")
print("Hello from CubeSandbox!")

result = sum(range(1, 101))
print(f"1+2+...+100 = {result}")
"""
        result = client.run_code(code)
        print("执行结果:")
        if hasattr(result, 'stdout'):
            print(result.stdout)
        else:
            print(result)

        print("\n3. 执行 Shell 命令...")
        shell_result = client.run_shell("uname -a && echo '---' && df -h /")
        print("Shell 输出:")
        if hasattr(shell_result, 'stdout'):
            print(shell_result.stdout)
        else:
            print(shell_result)

        print("\n4. 关闭沙箱...")
        client.close()
        print("✅ 沙箱已关闭!")

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        client.close()


def test_with_e2b_sdk():
    """使用 E2B SDK 直接测试"""
    print("\n" + "=" * 60)
    print("E2B SDK 兼容性测试")
    print("=" * 60)

    try:
        from e2b_code_interpreter import Sandbox
    except ImportError:
        print("❌ 请先安装: pip install e2b-code-interpreter")
        return

    api_url = os.environ.get("E2B_API_URL", "http://127.0.0.1:3000")
    template_id = os.environ.get("CUBE_TEMPLATE_ID", "")

    print(f"\nAPI URL: {api_url}")
    print(f"Template ID: {template_id or '(未设置)'}")

    if not template_id:
        print("\n⚠️ 请设置 CUBE_TEMPLATE_ID 环境变量")
        print("示例: export CUBE_TEMPLATE_ID='your-template-id'")
        return

    try:
        print("\n创建沙箱...")
        with Sandbox.create(template_id=template_id) as sandbox:
            print("✅ 沙箱创建成功!")

            print("\n执行测试代码...")
            execution = sandbox.run_code("print('Hello from CubeSandbox!')")

            if execution.stdout:
                print(f"输出: {execution.stdout}")

            if execution.error:
                print(f"错误: {execution.error}")

            print("\n✅ 测试完成!")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          CubeSandbox 测试工具 v1.0                       ║
║     腾讯云开源 AI Agent 安全沙箱服务                      ║
╚══════════════════════════════════════════════════════════╝
""")

    print("\n环境变量配置:")
    print(f"  E2B_API_URL      = {os.environ.get('E2B_API_URL', '(未设置)')}")
    print(f"  E2B_API_KEY      = {'*' * 8 if os.environ.get('E2B_API_KEY') else '(未设置)'}")
    print(f"  CUBE_TEMPLATE_ID = {os.environ.get('CUBE_TEMPLATE_ID', '(未设置)')}")

    result = test_connection_basic()

    if result["connected"]:
        print("\n是否继续进行沙箱操作测试? (需要有效的 Template ID)")
        test_sandbox_operations()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
