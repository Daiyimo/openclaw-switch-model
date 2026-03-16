#!/usr/bin/env python3
"""
reload-gateway.py — 触发 OpenClaw gateway 配置热重载或重启，以使新模型配置生效。

策略（优先级从高到低）：
  1. 先等待 1 秒，检测 gateway 是否已通过文件监听自动热重载（GET /health）
  2. 若已热重载（health 正常），则输出 HOT_RELOAD 并退出
  3. 若未热重载，尝试执行 `openclaw gateway reload`（软重载）
  4. 若软重载失败，执行 `openclaw gateway restart`（完整重启），等待最多 15 秒恢复
  5. 输出最终状态：RELOADED / RESTARTED / FAILED:<原因>

安全说明：
  - 仅调用 openclaw 官方 CLI 命令和本机 localhost 健康检查端点
  - 不访问外部网络，不修改任何配置文件
  - 使用 gateway token 仅用于健康检查鉴权（从配置读取）

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
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
HEALTH_TIMEOUT = 5
RESTART_WAIT = 15  # 等待重启完成的最大秒数


def load_gateway_info():
    """读取 gateway port 和 auth token，用于健康检查"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
        port = config.get("gateway", {}).get("port", 18789)
        token = config.get("gateway", {}).get("auth", {}).get("token", "")
        reload_mode = config.get("gateway", {}).get("reload", "hybrid")
        return port, token, reload_mode
    except Exception:
        return 18789, "", "hybrid"


def check_health(port, token):
    """调用 GET /health 检查 gateway 是否在线"""
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


def run_cmd(cmd_list):
    """执行命令，返回 (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=20
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except FileNotFoundError:
        return False, "", "找不到 openclaw 命令，请确认 openclaw CLI 已安装并在 PATH 中"
    except Exception as e:
        return False, "", str(e)


def wait_for_health(port, token, max_wait):
    """等待 gateway 恢复健康，最多等待 max_wait 秒，返回是否成功"""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if check_health(port, token):
            return True
        time.sleep(0.8)
    return False


def main():
    port, token, reload_mode = load_gateway_info()

    # 若配置为 reload: "off"，直接走重启路径
    if reload_mode == "off":
        ok, stdout, stderr = run_cmd(["openclaw", "gateway", "restart"])
        if ok:
            alive = wait_for_health(port, token, RESTART_WAIT)
            if alive:
                print("RESTARTED", flush=True)
                sys.exit(0)
            else:
                print("FAILED:重启命令成功但 gateway 未能在 " + str(RESTART_WAIT) + "s 内恢复", flush=True)
                sys.exit(1)
        else:
            print("FAILED:" + (stderr or stdout or "重启命令执行失败"), flush=True)
            sys.exit(1)

    # 等待热重载（model.primary 变更属于热重载范畴）
    time.sleep(1.2)
    if check_health(port, token):
        print("HOT_RELOAD", flush=True)
        sys.exit(0)

    # 热重载未触发或 gateway 无响应，尝试软重载
    ok, stdout, stderr = run_cmd(["openclaw", "gateway", "reload"])
    if ok:
        time.sleep(1.0)
        if check_health(port, token):
            print("RELOADED", flush=True)
            sys.exit(0)

    # 软重载无效，执行完整重启
    ok, stdout, stderr = run_cmd(["openclaw", "gateway", "restart"])
    if ok:
        alive = wait_for_health(port, token, RESTART_WAIT)
        if alive:
            print("RESTARTED", flush=True)
            sys.exit(0)
        else:
            print("FAILED:重启命令成功但 gateway 未能在 " + str(RESTART_WAIT) + "s 内恢复", flush=True)
            sys.exit(1)
    else:
        print("FAILED:" + (stderr or stdout or "重启命令执行失败"), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
