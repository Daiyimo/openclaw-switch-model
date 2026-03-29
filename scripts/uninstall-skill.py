#!/usr/bin/env python3
"""
uninstall-skill.py — 一键卸载 switch-model skill（面向 Agent）

用法:
  python3 uninstall-skill.py          # 普通卸载
  python3 uninstall-skill.py --force # 强制卸载（跳过确认）

功能:
  1. 确认卸载（除非使用 --force）
  2. 移除 ~/.openclaw/skills/switch-model 目录
  3. 可选：保留备份于 ~/.openclaw/skills/switch-model.bak

退出码: 0 成功, 1 失败, 2 用户取消
"""

import io
import os
import shutil
import sys

# Windows 下强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SKILL_NAME = "switch-model"
INSTALL_DIR = os.path.expanduser("~/.openclaw/skills/" + SKILL_NAME)
BACKUP_DIR = os.path.expanduser("~/.openclaw/skills/" + SKILL_NAME + ".bak")


def log(msg):
    print("[uninstall] " + msg, flush=True)


def error(msg):
    sys.stderr.write("[ERROR] " + msg + "\n")


def confirm():
    """交互式确认"""
    try:
        answer = input("确定要卸载 " + SKILL_NAME + " 吗？(yes/no): ").strip().lower()
        return answer in ("yes", "y")
    except EOFError:
        # 非交互环境，默认 no
        return False


def main():
    force = "--force" in sys.argv

    log("开始卸载 " + SKILL_NAME)

    # 检查是否已安装
    if not os.path.isdir(INSTALL_DIR):
        error("未找到安装目录: " + INSTALL_DIR)
        sys.exit(1)

    # 确认（除非 force）
    if not force:
        if not confirm():
            log("已取消卸载")
            sys.exit(2)

    # 移除安装目录
    try:
        shutil.rmtree(INSTALL_DIR)
        log("已移除安装目录: " + INSTALL_DIR)
    except Exception as e:
        error("移除失败: " + str(e))
        sys.exit(1)

    # 清理备份（可选，不强制删除）
    if os.path.isdir(BACKUP_DIR):
        log("备份保留于: " + BACKUP_DIR + "（如需删除请手动移除）")

    log("✅ 卸载完成！")
    sys.exit(0)


if __name__ == "__main__":
    main()
