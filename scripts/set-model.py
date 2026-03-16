#!/usr/bin/env python3
"""
set-model.py — 将 openclaw.json 中的 agents.defaults.model.primary 更新为指定模型 ID。

用法: python3 set-model.py <model_id>
  model_id: 格式为 "provider/modelId"，例如 "minimax/MiniMax-M2.5"

成功时输出 OK（stdout），失败时输出 ERROR: <原因>（stdout）。
本脚本仅修改 agents.defaults.model.primary 一个字段，不读取或修改 API Key 等凭证字段。
退出码：0 成功，1 失败
"""

import io
import json
import os
import sys
import tempfile

# Windows 下强制 stdout/stderr 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("ERROR: 未指定目标模型 ID")
        sys.exit(1)

    target_model_id = sys.argv[1].strip()

    if not os.path.isfile(CONFIG_PATH):
        print("ERROR: 配置文件不存在: " + CONFIG_PATH)
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
    except Exception as e:
        print("ERROR: 读取配置文件失败: " + str(e))
        sys.exit(1)

    # 确保路径存在，逐层创建（不修改已有字段）
    if "agents" not in config or not isinstance(config["agents"], dict):
        config["agents"] = {}
    if "defaults" not in config["agents"] or not isinstance(config["agents"]["defaults"], dict):
        config["agents"]["defaults"] = {}
    if "model" not in config["agents"]["defaults"] or not isinstance(config["agents"]["defaults"]["model"], dict):
        config["agents"]["defaults"]["model"] = {}

    # 仅更新 primary 字段
    config["agents"]["defaults"]["model"]["primary"] = target_model_id

    # 原子写入：先写临时文件，再替换，防止写入中途断电损坏原文件
    config_dir = os.path.dirname(CONFIG_PATH)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=config_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception:
            os.unlink(tmp_path)
            raise
        # 替换原文件
        os.replace(tmp_path, CONFIG_PATH)
    except Exception as e:
        print("ERROR: 写入配置文件失败: " + str(e))
        sys.exit(1)

    print("OK")


if __name__ == "__main__":
    main()
