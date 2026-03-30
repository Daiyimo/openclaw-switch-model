#!/usr/bin/env python3
"""
reload-gateway.py — 等待 OpenClaw gateway 完成 hot reload 并确认恢复正常。

背景：
  修改 agents.defaults.model.primary 后，gateway 的文件监听器会自动触发 hot reload。
  本脚本不主动触发任何 reload 或 restart，只负责等待 gateway 自动完成重载后确认其恢复正常。
  只有在等待超时（gateway 未能自动恢复）时，才作为最后兜底执行 restart。

策略（优先级从高到低）：
  1. 等待最多 3 秒，直到 gateway 因 hot reload 下线（文件监听 debounce ~300ms）
  2. 若在此期间 gateway 下线 → 等待最多 10 秒直到其恢复上线 → 输出 HOT_RELOAD
  3. 若 3 秒内 gateway 未下线 → 说明 hot reload 无需重启进程，直接生效 → 输出 HOT_RELOAD
  4. 若等待恢复超时（异常情况）→ 兜底执行 `openclaw gateway restart`
  5. 等待重启完成最多 15 秒 → 输出 RESTARTED 或 FAILED:...

安全说明：
  - 正常流程不执行任何 CLI 命令，仅轮询本机 localhost 健康检查端点
  - 仅在异常兜底时调用 openclaw gateway restart
  - 不访问外部网络，不修改任何配置文件

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
HEALTH_TIMEOUT = 3       # 单次 /health 请求超时秒数
TRIGGER_WAIT = 3         # 等待 hot reload 触发（gateway 下线）的最大秒数
HOT_RELOAD_WAIT = 10     # 等待 hot reload 完成（gateway 恢复）的最大秒数
RESTART_WAIT = 15        # 兜底重启后等待恢复的最大秒数
POLL_INTERVAL = 0.3      # 轮询间隔秒数


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


def wait_for_unhealthy(port, token, max_wait):
    """轮询直到 gateway 下线（hot reload 触发），返回是否在超时前下线"""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if not check_health(port, token):
            return True
        time.sleep(POLL_INTERVAL)
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
            timeout=20
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except FileNotFoundError:
        return False, "", "找不到 openclaw 命令，请确认 openclaw CLI 已安装并在 PATH 中"
    except Exception as e:
        return False, "", str(e)


def main():
    port, token = load_gateway_info()

    # 第一阶段：等待 hot reload 触发（gateway 文件监听 debounce ~300ms）
    # 若 gateway 在此期间下线，说明 hot reload 已开始
    went_down = wait_for_unhealthy(port, token, max_wait=TRIGGER_WAIT)

    if not went_down:
        # Gateway 未下线：hot reload 无需重启进程，配置已在线生效
        print("HOT_RELOAD", flush=True)
        sys.exit(0)

    # 第二阶段：gateway 已下线，等待其重新上线
    alive = wait_for_health(port, token, HOT_RELOAD_WAIT)
    if alive:
        print("HOT_RELOAD", flush=True)
        sys.exit(0)

    # 超时未恢复（异常情况）：兜底执行完整重启
    ok, stdout, stderr = run_cmd(["openclaw", "gateway", "restart"])
    if not ok:
        print("FAILED:" + (stderr or stdout or "重启命令执行失败"), flush=True)
        sys.exit(1)

    alive = wait_for_health(port, token, RESTART_WAIT)
    if alive:
        print("RESTARTED", flush=True)
        sys.exit(0)
    else:
        print("FAILED:重启命令成功但 gateway 未能在 " + str(RESTART_WAIT) + "s 内恢复", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


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
HEALTH_TIMEOUT = 3       # 单次 /health 请求超时秒数
HOT_RELOAD_WAIT = 8      # 等待 hot reload 自动完成的最大秒数
RESTART_WAIT = 15        # 兜底重启后等待恢复的最大秒数
POLL_INTERVAL = 0.5      # 轮询间隔秒数


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
            timeout=20
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except FileNotFoundError:
        return False, "", "找不到 openclaw 命令，请确认 openclaw CLI 已安装并在 PATH 中"
    except Exception as e:
        return False, "", str(e)


def main():
    port, token = load_gateway_info()

    # 等待 gateway 自动完成 hot reload 并恢复
    # gateway 文件监听有 300ms debounce，hot reload 本身耗时极短，8 秒绰绰有余
    alive = wait_for_health(port, token, HOT_RELOAD_WAIT)

    if alive:
        print("HOT_RELOAD", flush=True)
        sys.exit(0)

    # 超时未恢复（异常情况）：兜底执行完整重启
    ok, stdout, stderr = run_cmd(["openclaw", "gateway", "restart"])
    if not ok:
        print("FAILED:" + (stderr or stdout or "重启命令执行失败"), flush=True)
        sys.exit(1)

    alive = wait_for_health(port, token, RESTART_WAIT)
    if alive:
        print("RESTARTED", flush=True)
        sys.exit(0)
    else:
        print("FAILED:重启命令成功但 gateway 未能在 " + str(RESTART_WAIT) + "s 内恢复", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

