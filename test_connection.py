#!/usr/bin/env python3
"""
CubeSandbox 快速连通性测试
测试与 CubeSandbox API 的连接是否正常
"""

import socket
import sys
import time
import httpx


def test_port(host: str, port: int, timeout: float = 5.0) -> dict:
    """测试端口连通性"""
    result = {
        "host": host,
        "port": port,
        "open": False,
        "latency_ms": None,
        "error": None
    }

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        result["open"] = True
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
    except socket.timeout:
        result["error"] = "连接超时"
    except socket.gaierror as e:
        result["error"] = f"DNS解析失败: {e}"
    except ConnectionRefusedError:
        result["error"] = "连接被拒绝"
    except Exception as e:
        result["error"] = str(e)

    return result


def test_http(url: str, timeout: float = 10.0) -> dict:
    """测试 HTTP 连接"""
    result = {
        "url": url,
        "success": False,
        "status_code": None,
        "latency_ms": None,
        "error": None
    }

    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            result["status_code"] = resp.status_code
            result["success"] = resp.status_code < 500
            result["latency_ms"] = round((time.time() - start) * 1000, 2)
    except httpx.ConnectError as e:
        result["error"] = f"连接失败: {e}"
    except httpx.TimeoutException:
        result["error"] = "请求超时"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    print("=" * 50)
    print("CubeSandbox 连通性测试")
    print("=" * 50)

    import os
    api_url = os.environ.get("E2B_API_URL", "http://127.0.0.1:3000")

    from urllib.parse import urlparse
    parsed = urlparse(api_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    print(f"\n目标地址: {api_url}")
    print(f"主机: {host}")
    print(f"端口: {port}")

    print("\n[1] 测试 TCP 端口连通性...")
    tcp_result = test_port(host, port)
    if tcp_result["open"]:
        print(f"  ✅ 端口开放, 延迟: {tcp_result['latency_ms']}ms")
    else:
        print(f"  ❌ {tcp_result['error']}")

    print("\n[2] 测试 HTTP API...")
    http_result = test_http(f"{api_url}/health")
    if http_result["success"]:
        print(f"  ✅ API 响应正常, 状态码: {http_result['status_code']}, 延迟: {http_result['latency_ms']}ms")
    else:
        print(f"  ❌ {http_result['error']}")

    print("\n[3] 测试模板列表 API...")
    tpl_result = test_http(f"{api_url}/templates")
    if tpl_result["success"]:
        print(f"  ✅ 模板 API 可用, 状态码: {tpl_result['status_code']}")
    else:
        print(f"  ❌ {tpl_result['error']}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

    if tcp_result["open"] and http_result["success"]:
        print("\n✅ CubeSandbox 服务可用!")
        return 0
    else:
        print("\n❌ CubeSandbox 服务不可用")
        print("\n排查建议:")
        print("  1. 检查服务是否已启动")
        print("  2. 检查防火墙设置")
        print("  3. 检查 E2B_API_URL 环境变量是否正确")
        return 1


if __name__ == "__main__":
    sys.exit(main())
