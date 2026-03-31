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

探针策略：
  - anthropic-messages API: POST /messages, max_tokens=1, content="Hi"
  - openai-completions API: POST /chat/completions, max_tokens=1, content="Hi"
  - 超时 30 秒，避免长时间阻塞
  - 仅读取 baseUrl、api、apiKey/authHeader 等连接字段，不读取其他配置

安全说明：
  - API Key 仅用于构造鉴权请求头，不输出、不记录、不外传
  - 网络请求仅发送到 provider 配置的 baseUrl 或本地网关，不访问第三方地址
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
PROBE_TIMEOUT = 30  # 秒（免费模型如 openrouter 可能响应较慢）
MAX_RESPONSE_SIZE = 1024 * 1024  # 限制响应体为 1MB，防止内存耗尽


def check_gateway_health(port, token):
    """前置检查：网关是否可用"""
    url = "http://127.0.0.1:" + str(port) + "/health"
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200, None
    except urllib.error.HTTPError as e:
        return False, "网关健康检查返回 HTTP " + str(e.code)
    except urllib.error.URLError as e:
        reason_str = str(e.reason) if e.reason else str(e)
        return False, "无法连接到网关: " + reason_str
    except Exception as e:
        return False, "网关检查异常: " + str(e)


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


def build_headers_and_body(provider_name, provider_cfg, model_id, config):
    """
    根据 provider 配置构建请求头和请求体。
    返回 (url, headers_dict, body_bytes, error_msg)，
    如果 error_msg 不为 None 表示无法构建请求。
    API Key 仅在内存中使用，不输出。

    关键点：
    - baseUrl 应该是完整的 API 端点 URL（包含路径），不进行端点拼接
    - authHeader=true：通过本地 gateway 代理，使用 gateway token 而非 provider key
    - authHeader=false：直接使用 provider apiKey 进行请求
    """
    base_url = provider_cfg.get("baseUrl", "").rstrip("/")
    api_type = provider_cfg.get("api", "openai-completions")

    if not base_url:
        return None, None, None, "缺少 baseUrl 配置"

    # --- 构建鉴权头 ---
    headers = {"Content-Type": "application/json"}

    # 若 authHeader=true，则通过本地 openclaw gateway 代理探测
    # （适用于 minimax 等 provider，gateway 会注入真实 key 再转发）
    use_auth_header = provider_cfg.get("authHeader", False)
    if use_auth_header:
        gw_token = get_auth_token(config)
        if not gw_token:
            return None, None, None, "网关未配置 token（gateway.auth.token 缺失），无法通过网关代理探测"
        headers["Authorization"] = "Bearer " + gw_token
        gw_port = config.get("gateway", {}).get("port", 18789)
        # 重要：通过 gateway 代理时，baseUrl 被替换为 localhost gateway 地址
        # gateway 会根据 model id 中的 provider 前缀进行路由
        base_url = "http://127.0.0.1:" + str(gw_port) + "/v1"
    else:
        # 直连模式：使用 provider 配置的 apiKey
        api_key = provider_cfg.get("apiKey", "")
        if not api_key:
            return None, None, None, "未配置 apiKey 且未启用网关代理（authHeader=false）"
        headers["Authorization"] = "Bearer " + api_key

    # 发给 API 的 model 字段：
    # - authHeader 模式（gateway 代理）：保留 full id（如 "minimax/MiniMax-M2.5"），gateway 依靠此字段路由
    # - 直连模式：去掉 provider 前缀（如 "stepfun/step-3.5-flash" → "step-3.5-flash"），直接发给上游 API
    api_model_id = model_id
    if not use_auth_header and api_model_id.startswith(provider_name + "/"):
        api_model_id = api_model_id[len(provider_name) + 1:]

    # --- 构建请求体和 URL ---
    url = base_url

    # 构建请求体（根据 API 类型选择字段）
    if api_type == "anthropic-messages":
        body = {
            "model": api_model_id,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "Hi"}]
        }
        # Anthropic 原生 API 需要 x-api-key 头而非 Authorization（仅直连模式）
        if not use_auth_header:
            if "Authorization" in headers:
                del headers["Authorization"]
            headers["x-api-key"] = provider_cfg.get("apiKey", "")
            headers["anthropic-version"] = "2024-01-01"  # 使用较新的 API 版本
    else:
        # OpenAI-compatible completions
        body = {
            "model": api_model_id,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "Hi"}]
        }

    return url, headers, json.dumps(body).encode("utf-8"), None


def probe_one(full_id, model_name, provider_name, provider_cfg, model_id, config):
    """探测单个模型，返回 (full_id, True/False, model_name, reason)"""
    url, headers, body, error_msg = build_headers_and_body(provider_name, provider_cfg, model_id, config)
    if error_msg:
        return (full_id, False, model_name, error_msg)

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            status = resp.status
            # 限制响应体大小，防止恶意或错误的大响应耗尽内存
            resp_body_bytes = resp.read(MAX_RESPONSE_SIZE)
            # 检查是否还有更多数据未读
            if resp.read(1):  # 尝试再读 1 字节
                return (full_id, False, model_name, "响应体过大（超过 1MB）")
            resp_body = resp_body_bytes.decode("utf-8", errors="replace")
            # 2xx 均视为成功；某些 provider 返回 200 但 body 含 error 字段
            if 200 <= status < 300:
                # 检查 body 中是否有明确的 error 字段
                try:
                    resp_json = json.loads(resp_body)
                    if "error" in resp_json:
                        err = resp_json["error"]
                        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                        return (full_id, False, model_name, "API 错误: " + msg[:120])
                except json.JSONDecodeError:
                    # 响应不是 JSON，发出警告但仍视为成功（某些 provider 返回纯文本）
                    sys.stderr.write("[WARNING] 模型 " + full_id + " 响应非 JSON 格式，但仍视为成功\n")
                except (KeyError, TypeError):
                    # JSON 结构不符合预期，视为成功
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
        # e.reason 可能是异常对象，使用 str() 统一转换
        reason_str = str(e.reason) if e.reason else str(e)
        return (full_id, False, model_name, "连接失败: " + reason_str[:120])
    except Exception as e:
        return (full_id, False, model_name, "未知错误: " + str(e)[:120])


def main():
    config = load_config()

    # 解析 filter（可选）：空白字符串视为无过滤
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    filter_id = filter_arg.strip() or None

    # 安全获取 providers，确保是字典类型
    models_section = config.get("models")
    if not isinstance(models_section, dict):
        models_section = {}
    providers = models_section.get("providers", {})
    if not isinstance(providers, dict):
        providers = {}

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

    # 前置检查：如果存在使用 authHeader 的 provider，先验证网关可用性
    needs_gateway = any(
        isinstance(p_cfg, dict) and p_cfg.get("authHeader", False)
        for _, _, _, p_cfg, _ in tasks
    )
    if needs_gateway:
        gw_port = config.get("gateway", {}).get("port", 18789)
        gw_token = get_auth_token(config)
        gw_ok, gw_err = check_gateway_health(gw_port, gw_token)
        if not gw_ok:
            sys.stderr.write("[WARNING] 网关健康检查失败: " + gw_err + "\n")
            sys.stderr.write("  提示: 使用 authHeader=true 的 provider 依赖本地 gateway，请确认 gateway 正在运行\n")
            sys.stderr.write("  可通过 `sudo openclaw gateway status` 查看状态\n")

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
