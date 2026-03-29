#!/usr/bin/env python3
"""
probe-models.py — 对 openclaw.json 中每个配置的模型发送最小化 API 探针请求，
                  检测该 provider/model 的连通性和 Key 有效性。

用法:
  python3 probe-models.py              # 探测所有模型
  python3 probe-models.py provider/id  # 仅探测指定模型

输出格式（每行一条，stdout）：
  provider/modelId\tOK\t模型名称
  provider/modelId\tFAIL\t模型名称\t失败原因

支持的 API 类型（根据 provider.api 字段）：
  - anthropic-messages: POST /v1/messages (Anthropic 兼容)
  - openai-completions: POST /v1/chat/completions (OpenAI 兼容)
  - openai-chatCompletions: POST /v1/chat/completions (OpenAI Chat 兼容)
  - openai: POST /v1/completions (OpenAI 旧兼容)

探针策略：
  - max_tokens=1，内容为 "Hi"，最小化请求
  - 超时 10 秒，避免长时间阻塞
  - 仅读取 baseUrl、api、apiKey/authHeader 等连接字段，不读取其他配置

安全说明：
  - API Key 仅用于构造鉴权请求头，不输出、不记录、不外传
  - 网络请求仅发送到 provider 配置的 baseUrl，不访问第三方地址
退出码：0 所有模型均可用，1 至少一个失败，2 配置读取失败
"""

import io
import json
import os
import sys
import urllib.request
import urllib.error

# Windows 下强制 stdout/stderr 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
PROBE_TIMEOUT = 10  # 秒


def load_config():
    if not os.path.isfile(CONFIG_PATH):
        sys.stderr.write("ERROR: 配置文件不存在: " + CONFIG_PATH + "\n")
        sys.exit(2)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write("ERROR: 读取配置文件失败: " + str(e) + "\n")
        sys.exit(2)


def get_auth_token(config):
    """从 gateway.auth.token 读取本地 gateway token（用于 auth 模式鉴权，非 provider key）"""
    try:
        return config["gateway"]["auth"]["token"]
    except (KeyError, TypeError):
        return None


def get_api_endpoint(api_type):
    """根据 API 类型返回对应的端点路径"""
    endpoints = {
        "anthropic-messages": "/v1/messages",
        "openai-completions": "/v1/chat/completions",
        "openai-chatCompletions": "/v1/chat/completions",
        "openai": "/v1/completions",
    }
    return endpoints.get(api_type, "/v1/chat/completions")


def get_request_body(api_type, model_id, probe_content="Hi"):
    """根据 API 类型返回对应的请求体"""
    base_body = {
        "model": model_id,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": probe_content}]
    }

    if api_type == "openai":
        # OpenAI 旧兼容 API 使用 prompt 而非 messages
        return {
            "model": model_id,
            "max_tokens": 1,
            "prompt": probe_content
        }
    return base_body


def get_extra_headers(api_type, base_url):
    """根据 API 类型返回额外的请求头"""
    extra = {}
    if api_type == "anthropic-messages":
        extra["anthropic-version"] = "2023-06-01"
        # Anthropic 原生 API 需要 x-api-key
        if "anthropic.com" in base_url:
            extra["x-api-key"] = "placeholder"  # 实际会在 build_headers_and_body 中替换
    return extra


def build_headers_and_body(provider_name, provider_cfg, model_id, config):
    """
    根据 provider 配置构建请求头和请求体。
    返回 (url, headers_dict, body_bytes) 或 None（如果无法构建）。
    API Key 仅在内存中使用，不输出。
    """
    base_url = provider_cfg.get("baseUrl", "").rstrip("/")
    api_type = provider_cfg.get("api", "openai-completions")

    if not base_url:
        return None

    # 发给 API 的 model 字段：若 model_id 带有 "provider_name/" 前缀，则去掉
    # 例如 stepfun 配置 id="stepfun/step-3.5-flash"，但 API 需要 "step-3.5-flash"
    api_model_id = model_id
    if api_model_id.startswith(provider_name + "/"):
        api_model_id = api_model_id[len(provider_name) + 1:]

    # --- 构建鉴权头 ---
    headers = {"Content-Type": "application/json"}

    # 优先使用 provider 配置的 apiKey
    api_key = provider_cfg.get("apiKey", "")

    # 若 authHeader=true，则使用 openclaw gateway token 作为鉴权
    # （适用于 minimax 等走 openclaw 本地代理的 provider）
    use_auth_header = provider_cfg.get("authHeader", False)
    if use_auth_header:
        # authHeader 模式：请求需经过本地 openclaw gateway 代理转发
        # gateway 会注入真实的 provider key，因此必须通过 gateway 发探针才能检测 key 是否有效
        # 用 gateway token 作为鉴权头，将请求发到 gateway 的 /v1 端点
        gw_token = get_auth_token(config)
        if not gw_token:
            return None  # 无 gateway token，无法代理探测
        headers["Authorization"] = "Bearer " + gw_token
        gw_port = config.get("gateway", {}).get("port", 18789)
        base_url = "http://127.0.0.1:" + str(gw_port) + "/v1"
    elif api_key:
        headers["Authorization"] = "Bearer " + api_key
    else:
        # 无鉴权信息，无法探测
        return None

    # --- 构建请求体和 URL ---
    endpoint = get_api_endpoint(api_type)
    url = base_url + endpoint
    body = get_request_body(api_type, api_model_id)

    # 根据 API 类型添加额外 headers
    extra_headers = get_extra_headers(api_type, base_url)
    if extra_headers.get("x-api-key"):
        # 替换为实际 api_key
        headers["x-api-key"] = api_key
        del extra_headers["x-api-key"]
    headers.update(extra_headers)

    return url, headers, json.dumps(body).encode("utf-8")


def probe_one(full_id, model_name, provider_name, provider_cfg, model_id, config):
    """探测单个模型，返回 (full_id, True/False, model_name, reason)"""
    result = build_headers_and_body(provider_name, provider_cfg, model_id, config)
    if result is None:
        return (full_id, False, model_name, "无法构建请求（缺少 baseUrl 或鉴权信息）")

    url, headers, body = result

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            status = resp.status
            resp_body = resp.read(512).decode("utf-8", errors="replace")
            # 2xx 均视为成功；某些 provider 返回 200 但 body 含 error 字段
            if 200 <= status < 300:
                # 检查 body 中是否有明确的 error 字段
                try:
                    resp_json = json.loads(resp_body + resp.read().decode("utf-8", errors="replace"))
                    if "error" in resp_json:
                        err = resp_json["error"]
                        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                        return (full_id, False, model_name, "API 错误: " + msg[:120])
                except Exception:
                    pass
                return (full_id, True, model_name, "")
            else:
                return (full_id, False, model_name, "HTTP " + str(status))
    except urllib.error.HTTPError as e:
        reason = "HTTP " + str(e.code)
        try:
            err_body = e.read(256).decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                msg = ""
                if "error" in err_json:
                    err_obj = err_json["error"]
                    msg = err_obj.get("message", str(err_obj)) if isinstance(err_obj, dict) else str(err_obj)
                if msg:
                    reason = reason + " — " + msg[:120]
            except Exception:
                if err_body.strip():
                    reason = reason + " — " + err_body.strip()[:120]
        except Exception:
            pass
        return (full_id, False, model_name, reason)
    except urllib.error.URLError as e:
        return (full_id, False, model_name, "连接失败: " + str(e.reason)[:120])
    except Exception as e:
        return (full_id, False, model_name, "未知错误: " + str(e)[:120])


def main():
    config = load_config()

    # 解析 filter（可选）
    filter_id = sys.argv[1].strip() if len(sys.argv) > 1 else None

    providers = {}
    try:
        providers = config.get("models", {}).get("providers", {})
    except (AttributeError, TypeError):
        pass

    tasks = []
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
            if model_id.startswith(provider_name + "/"):
                full_id = model_id
            else:
                full_id = provider_name + "/" + model_id
            if filter_id and full_id != filter_id:
                continue
            tasks.append((full_id, model_name, provider_name, provider_cfg, model_id))

    if not tasks:
        sys.stderr.write("ERROR: 未找到任何模型配置\n")
        sys.exit(2)

    any_fail = False
    for full_id, model_name, provider_name, provider_cfg, model_id in tasks:
        full_id_out, ok, name, reason = probe_one(
            full_id, model_name, provider_name, provider_cfg, model_id, config
        )
        if ok:
            print(full_id_out + "\tOK\t" + name, flush=True)
        else:
            print(full_id_out + "\tFAIL\t" + name + "\t" + reason, flush=True)
            any_fail = True

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
