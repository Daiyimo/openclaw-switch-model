#!/usr/bin/env python3
"""
update-skill.py — 一键更新 switch-model skill 到最新版本（面向 Agent）

用法:
  python3 update-skill.py

功能:
  1. 备份当前版本到 ~/.openclaw/skills/switch-model.bak
  2. 从 Git 拉取最新代码（或复制当前目录）
  3. 验证脚本完整性
  4. 报告更新结果

退出码: 0 成功, 1 失败, 2 无权限
"""

import io
import json
import os
import shutil
import subprocess
import sys

# Windows 下强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SKILL_NAME = "switch-model"
INSTALL_DIR = os.path.expanduser("~/.openclaw/skills/" + SKILL_NAME)
BACKUP_DIR = os.path.expanduser("~/.openclaw/skills/" + SKILL_NAME + ".bak")
REPO_URL = "https://github.com/Daiyimo/openclaw-switch-model"

# 需要验证的关键文件
REQUIRED_FILES = [
    "SKILL.md",
    "scripts/list-models.py",
    "scripts/probe-models.py",
    "scripts/set-model.py",
    "scripts/reload-gateway.py",
]


def log(msg):
    print("[update] " + msg, flush=True)


def error(msg):
    sys.stderr.write("[ERROR] " + msg + "\n")


def backup_current():
    """备份当前安装的版本"""
    if os.path.isdir(INSTALL_DIR):
        log("正在备份当前版本到 " + BACKUP_DIR)
        if os.path.isdir(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        try:
            shutil.copytree(INSTALL_DIR, BACKUP_DIR)
            log("备份完成")
            return True
        except Exception as e:
            error("备份失败: " + str(e))
            return False
    return True  # 没有现有版本，无需备份


def restore_backup():
    """恢复备份（先完全删除安装目录，再复制）"""
    if os.path.isdir(BACKUP_DIR):
        if os.path.isdir(INSTALL_DIR):
            try:
                shutil.rmtree(INSTALL_DIR)
            except Exception as e:
                error("清理旧安装目录失败: " + str(e))
                return False
        try:
            shutil.copytree(BACKUP_DIR, INSTALL_DIR)
            log("已恢复备份")
            return True
        except Exception as e:
            error("恢复备份失败: " + str(e))
            return False
    return False


def validate_install(skill_dir):
    """验证安装目录完整性"""
    for f in REQUIRED_FILES:
        path = os.path.join(skill_dir, f)
        if not os.path.isfile(path):
            error("缺少关键文件: " + f)
            return False
    return True


def update_via_git():
    """通过 Git 更新"""
    if not os.path.isdir(INSTALL_DIR):
        # 首次安装：克隆仓库
        log("首次安装，正在克隆仓库...")
        try:
            parent = os.path.dirname(INSTALL_DIR)
            os.makedirs(parent, exist_ok=True)
            subprocess.run(
                ["git", "clone", REPO_URL, INSTALL_DIR],
                check=True,
                capture_output=True,
            )
            log("克隆完成")
            return True
        except subprocess.CalledProcessError as e:
            error("Git 克隆失败: " + e.stderr.decode() if e.stderr else str(e))
            return False
        except FileNotFoundError:
            error("未找到 git 命令，请确认已安装 Git")
            return False

    # 已有安装：尝试 git pull（自动检测当前分支）
    log("正在拉取最新代码...")
    try:
        # 获取当前分支名
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=INSTALL_DIR,
            capture_output=True,
            text=True,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        if not branch:
            branch = "main"

        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=INSTALL_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log("拉取成功（分支: " + branch + "）")
            return True
        else:
            error("拉取失败: " + result.stderr)
            return False
    except Exception as e:
        error("拉取异常: " + str(e))
        return False


def update_via_copy():
    """通过复制当前目录更新（备选方案）"""
    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log("正在从当前目录复制文件...")

    if not validate_install(source_dir):
        error("源目录文件不完整，无法复制")
        return False

    try:
        # 移除旧安装
        if os.path.isdir(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR)

        # 复制新版本
        shutil.copytree(source_dir, INSTALL_DIR)
        log("复制完成")
        return True
    except Exception as e:
        error("复制失败: " + str(e))
        return False


def main():
    log("开始更新 " + SKILL_NAME)

    # 1. 备份
    if not backup_current():
        error("备份失败，停止更新")
        sys.exit(2)

    # 2. 尝试 Git 更新
    success = update_via_git()

    # 3. Git 失败则使用复制方式
    if not success:
        log("Git 更新失败，尝试使用复制方式...")
        # 先恢复备份，再复制
        if not restore_backup():
            error("恢复备份失败，无法使用复制方式更新")
            sys.exit(1)
        if not update_via_copy():
            error("复制方式也失败，已恢复备份")
            sys.exit(1)

    # 4. 验证安装
    if not validate_install(INSTALL_DIR):
        error("安装验证失败，已恢复备份")
        restore_backup()
        sys.exit(1)

    log("✅ 更新完成！版本已安装到 " + INSTALL_DIR)
    sys.exit(0)


if __name__ == "__main__":
    main()
