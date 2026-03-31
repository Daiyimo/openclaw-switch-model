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
    """恢复备份（原子性：先拷贝到临时位置，再原子替换）"""
    if not os.path.isdir(BACKUP_DIR):
        error("未找到备份目录: " + BACKUP_DIR)
        return False

    # 原子恢复：先复制到临时目录，再原子替换，避免中途失败导致安装目录丢失
    temp_dir = INSTALL_DIR + ".tmp_restore_" + str(os.getpid())
    old_dir = None  # 保存旧安装目录用于回滚
    try:
        # 1. 复制备份到临时目录
        shutil.copytree(BACKUP_DIR, temp_dir)

        # 2. 如果旧安装目录存在，先移动到临时位置作为回滚点
        if os.path.isdir(INSTALL_DIR):
            old_dir = INSTALL_DIR + ".old_" + str(os.getpid())
            os.rename(INSTALL_DIR, old_dir)

        # 3. 原子重命名临时目录为正式安装目录
        os.rename(temp_dir, INSTALL_DIR)

        # 4. 成功：清理旧版本（如果存在）
        if old_dir and os.path.isdir(old_dir):
            try:
                shutil.rmtree(old_dir)
            except Exception:
                pass  # 旧版本清理失败不影响更新结果

        log("已恢复备份（原子操作）")
        return True
    except Exception as e:
        error("恢复备份失败: " + str(e))

        # 尝试回滚到旧安装目录
        if old_dir and os.path.isdir(old_dir):
            try:
                if os.path.isdir(INSTALL_DIR):
                    shutil.rmtree(INSTALL_DIR)
                os.rename(old_dir, INSTALL_DIR)
                log("已回滚到旧版本")
            except Exception:
                pass

        # 清理临时文件
        for d in [temp_dir, old_dir]:
            if d and os.path.isdir(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass
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
            err_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
            error("拉取失败: " + err_msg)
            # 检测常见失败原因
            if any(keyword in err_msg.lower() for keyword in
                   ["non-fast-forward", "conflict", "need to merge", "rebase"]):
                error("提示：检测到本地有未推送的提交或冲突。请手动执行 git pull 解决，或使用 update-skill.py 的复制模式。")
            return False
    except Exception as e:
        error("拉取异常: " + str(e))
        return False


def update_via_copy():
    """通过复制当前目录更新（备选方案，需确保从独立源目录执行）"""
    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 防止自拷贝：如果源目录就是安装目录，复制将导致数据丢失
    if os.path.normpath(source_dir) == os.path.normpath(INSTALL_DIR):
        error("复制方式失败：检测到源目录与安装目录相同，这会导致技能被清空。")
        error("请从 Git 仓库目录执行更新，或使用以下命令手动重新克隆：")
        error("  git clone https://github.com/Daiyimo/openclaw-switch-model ~/.openclaw/skills/switch-model")
        return False

    log("正在从源目录复制文件: " + source_dir)

    if not validate_install(source_dir):
        error("源目录文件不完整，无法复制")
        return False

    try:
        # 原子更新：先复制到临时目录，再原子替换
        temp_dir = INSTALL_DIR + ".tmp_update_" + str(os.getpid())
        shutil.copytree(source_dir, temp_dir)

        # 如果旧安装目录存在，先移动到临时位置作为回滚点
        old_dir = None
        if os.path.isdir(INSTALL_DIR):
            old_dir = INSTALL_DIR + ".old_" + str(os.getpid())
            os.rename(INSTALL_DIR, old_dir)

        # 原子重命名
        os.rename(temp_dir, INSTALL_DIR)

        # 成功：清理旧版本（如果存在）
        if old_dir and os.path.isdir(old_dir):
            try:
                shutil.rmtree(old_dir)
            except Exception:
                pass  # 旧版本清理失败不影响更新结果

        log("复制完成（原子操作）")
        return True
    except Exception as e:
        error("复制失败: " + str(e))

        # 尝试回滚
        if old_dir and os.path.isdir(old_dir):
            try:
                if os.path.isdir(INSTALL_DIR):
                    shutil.rmtree(INSTALL_DIR)
                os.rename(old_dir, INSTALL_DIR)
                log("已回滚到旧版本")
            except Exception:
                pass

        # 清理临时文件
        for d in [temp_dir, old_dir]:
            if d and os.path.isdir(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass
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
