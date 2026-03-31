#!/usr/bin/env python3
"""
reload-gateway.py — 使用 sudo stop/config/start 方案管理 OpenClaw gateway 重启。

背景：
  修改 agents.defaults.model.primary 后，需要完整重启 gateway 以使配置生效。
  本脚本执行以下操作：
    1. sudo openclaw gateway stop     - 停止 gateway
    2. sudo openclaw config set agents.defaults.model.primary <model_id> - 设置新模型
    3. sudo openclaw gateway start    - 启动 gateway
  
  然后等待 gateway 恢复正常，通过 /health 端点确认。

安全说明：
  - 使用 sudo 执行需要权限的命令
  - 命令执行通过 subprocess 进行，参数安全传递
  - 不访问外部网络，仅轮询本机 localhost 健康检查端点
  - 不读取或输出 API Key 等凭证

退出码：0 成功，1 失败
"""

import io
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# Windows 下强制 stdout/stderr 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
HEALTH_TIMEOUT = 3       # 单次 /health 请求超时秒数
START_WAIT = 15          # 启动后等待 gateway 恢复的最大秒数
POLL_INTERVAL = 0.5      # 轮询间隔秒数
IS_WINDOWS = sys.platform == "win32"


def find_openclaw_cmd():
    """查找 openclaw 命令的绝对路径，避免 sudo 环境下 PATH 问题"""
    # 常见的可执行文件位置
    candidates = ["openclaw", "openclaw.exe"]

    # 根据平台选择查找命令
    if IS_WINDOWS:
        find_cmd = ["where"] + candidates
    else:
        find_cmd = ["which"] + candidates

    try:
        result = subprocess.run(
            find_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        # 返回第一个找到的路径
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # 尝试直接运行（依赖用户 PATH 配置）
    return "openclaw"


def is_admin():
    """检查当前是否具有管理员/root权限"""
    if IS_WINDOWS:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            # 如果 ctypes 不可用或调用失败，保守返回 False
            return False
    else:
        try:
            return os.geteuid() == 0
        except AttributeError:
            # 某些系统没有 geteuid，保守返回 False
            return False


def load_gateway_info():
    """读取 gateway port 和 auth token，用于健康检查"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
        port = config.get("gateway", {}).get("port", 18789)
        token = config.get("gateway", {}).get("auth", {}).get("token", "")
        return port, token
    except Exception:
        return 18789, ""


def check_health(port, token):
    """调用 GET /health，返回 True 表示 gateway 在线且正常"""
    url = "http://127.0.0.1:" + str(port) + "/health"
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_health(port, token, max_wait):
    """轮询直到 gateway 恢复健康，返回是否在超时前恢复"""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if check_health(port, token):
            return True
        time.sleep(POLL_INTERVAL)
    return False


def run_cmd(cmd_list):
    """执行命令，返回 (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except FileNotFoundError:
        return False, "", "找不到 openclaw 命令，请确认 openclaw CLI 已安装并在 PATH 中"
    except PermissionError:
        if IS_WINDOWS:
            return False, "", "权限不足，请以管理员身份运行此脚本"
        else:
            return False, "", "权限不足，请确认已配置 sudo 权限"
    except OSError as e:
        return False, "", "系统错误: " + str(e)
    except Exception as e:
        return False, "", str(e)


def main():
    # 获取模型 ID（如果从命令行参数传入）
    model_id = sys.argv[1].strip() if len(sys.argv) > 1 else None

    # Windows 上检查管理员权限
    if IS_WINDOWS and not is_admin():
        sys.stderr.write("ERROR: 此操作需要管理员权限。请以管理员身份运行命令提示符或 PowerShell 后重试。\n")
        sys.exit(2)

    # 查找 openclaw 命令路径（避免 sudo 环境下 PATH 问题）
    openclaw_cmd = find_openclaw_cmd()

    port, token = load_gateway_info()

    # 根据平台决定是否使用 sudo
    sudo_prefix = [] if IS_WINDOWS else ["sudo"]

    # 第一步：停止 gateway
    print("正在停止 gateway...", flush=True)
    ok, stdout, stderr = run_cmd(sudo_prefix + [openclaw_cmd, "gateway", "stop"])
    if not ok:
        print("FAILED:停止 gateway 失败: " + (stderr or stdout or "未知错误"), flush=True)
        sys.exit(1)

    # 给 gateway 足够时间关闭
    time.sleep(1)

    # 第二步：设置新模型（如果提供了模型 ID）
    if model_id:
        print("正在设置新模型...", flush=True)
        ok, stdout, stderr = run_cmd(sudo_prefix + [openclaw_cmd, "config", "set",
                                       "agents.defaults.model.primary", model_id])
        if not ok:
            print("FAILED:设置模型失败: " + (stderr or stdout or "未知错误"), flush=True)
            sys.exit(1)

    # 第三步：启动 gateway
    print("正在启动 gateway...", flush=True)
    ok, stdout, stderr = run_cmd(sudo_prefix + [openclaw_cmd, "gateway", "start"])
    if not ok:
        print("FAILED:启动 gateway 失败: " + (stderr or stdout or "未知错误"), flush=True)
        sys.exit(1)

    # 第四步：等待 gateway 恢复正常
    print("等待 gateway 恢复...", flush=True)
    alive = wait_for_health(port, token, START_WAIT)
    if alive:
        print("RESTARTED", flush=True)
        sys.exit(0)
    else:
        print("FAILED:gateway 未能在 " + str(START_WAIT) + "s 内恢复", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
