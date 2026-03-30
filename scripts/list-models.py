#!/usr/bin/env python3
"""
list-models.py — 读取 openclaw.json 中配置的模型列表及当前 primary 模型。

输出格式（stdout）：
  第一行: 当前 primary 模型 ID（agents.defaults.model.primary），无则输出空行
  后续每行: provider/modelId\t模型名称
  （每个 provider 下的每个 model 输出一行）

不读取、不输出任何 API Key 或凭证字段。
退出码：0 成功，1 配置文件不存在或解析失败
"""

import io
import json
import os
import sys

# Windows 下强制 stdout/stderr 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")


def main():
    if not os.path.isfile(CONFIG_PATH):
        print("", flush=True)  # current line: empty
        sys.stderr.write("ERROR: 配置文件不存在: " + CONFIG_PATH + "\n")
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
    except Exception as e:
        print("", flush=True)
        sys.stderr.write("ERROR: 读取配置文件失败: " + str(e) + "\n")
        sys.exit(1)

    # 读取当前 primary 模型（仅读取该字段，不涉及 apiKey 等凭证）
    current = ""
    try:
        current = config["agents"]["defaults"]["model"]["primary"]
    except (KeyError, TypeError):
        pass

    print(current, flush=True)

    # 遍历 models.providers，仅提取 id 和 name，跳过所有凭证字段
    providers = {}
    try:
        providers = config.get("models", {}).get("providers", {})
    except (AttributeError, TypeError):
        pass

    for provider_name, provider_cfg in providers.items():
        if not isinstance(provider_cfg, dict):
            continue
        models = provider_cfg.get("models", [])
        if not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict):
                continue
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)
            if not model_id:
                continue
            # 输出格式: provider/modelId\t模型名称
            # 若 model_id 已以 "provider_name/" 开头（配置中带了 provider 前缀），则不重复拼接
            if model_id.startswith(provider_name + "/"):
                full_id = model_id
            else:
                full_id = provider_name + "/" + model_id
            print(full_id + "\t" + model_name, flush=True)


if __name__ == "__main__":
    main()
