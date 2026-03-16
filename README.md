# switch-model

> OpenClaw Skill · 安全切换 AI 模型，切换前自动检测 Key 有效性，防止切换到不可用模型导致服务中断。

---

## 功能特性

- 🔍 **自动探测**：切换前对所有配置的模型发送探针请求，检测连通性和 API Key 有效性
- 🔑 **Key 有效性检测**：能识别 Key 过期（401/403）、模型不可用（404）、配额超限（429）等具体原因
- 🛡️ **切换保护**：Key 失效或模型不可用时直接拒绝切换，避免 OpenClaw 因切换到不可用模型而崩溃
- 🌐 **代理模式支持**：对走 OpenClaw gateway 代理的 provider（如 MiniMax），通过 gateway 转发探针，准确检测真实 Key 状态
- ♻️ **热重载**：写入配置后自动触发 gateway 热重载，`model.primary` 变更无需完整重启即可生效
- 🖥️ **跨平台**：兼容 Windows / macOS / Linux，Python 3 标准库实现，无需额外依赖
- 🤝 **多 Provider 兼容**：支持 Claude、GLM、MiniMax、Stepfun、OpenRouter 等任意在 `openclaw.json` 中配置的模型

---

## 使用方式

在 OpenClaw 对话中输入：

```
/switch-model
```

或直接用自然语言触发：

```
帮我切换模型
我想换一个 AI
查看当前可用的模型
```

**典型对话流程：**

```
用户: /switch-model

AI: 正在检测各模型连通性和 Key 有效性，请稍候……

AI: 🔍 模型检测完成：

  ✅ 1. Step 3.5 Flash      stepfun/step-3.5-flash  ← 当前
  ✅ 2. Step 3.5 Flash Free openrouter/stepfun/step-3.5-flash:free
  🔑    MiniMax M2.5        minimax/MiniMax-M2.5   (Key 已失效)

  当前使用：Step 3.5 Flash ✅ 正常
  请问想切换到哪个模型？

用户: 换第 2 个

AI: ✅ 已从 Step 3.5 Flash（stepfun/step-3.5-flash）
      切换到 Step 3.5 Flash Free（openrouter/stepfun/step-3.5-flash:free）
      配置已热重载，当前对话即刻生效，继续吧！
```

---

## 安装

### 方式一：手动安装（推荐）

将本仓库克隆或下载到 OpenClaw skills 目录：

```bash
# macOS / Linux
git clone https://github.com/Daiyimo/openclaw-switch-model \
  ~/.openclaw/skills/switch-model

# Windows（PowerShell）
git clone https://github.com/Daiyimo/openclaw-switch-model `
  "$env:USERPROFILE\.openclaw\skills\switch-model"
```

### 方式二：通过水产市场安装

```bash
openclawmp install skill/@Daiyimo/switch-model
```

### 安装验证

```bash
openclaw skill validate switch-model
```

---

## 文件结构

```
switch-model/
├── SKILL.md                  # Skill 主入口，定义触发规则和执行流程
└── scripts/
    ├── list-models.py         # 读取 openclaw.json 中的模型列表和当前 primary 模型
    ├── probe-models.py        # 对每个模型发探针请求，检测连通性和 Key 有效性
    ├── set-model.py           # 将目标模型 ID 写入 agents.defaults.model.primary
    ├── reload-gateway.py      # 等待 gateway 自动 hot reload 完成并确认恢复（不主动触发）
```

---

## 探测失败原因分类

| 图标 | 类型 | 触发条件 | 处理方式 |
|------|------|---------|---------|
| 🔑 | Key 失效 | HTTP 401 / 403 / unauthorized / key expired | **直接拒绝切换** |
| 🚫 | 模型不可用 | HTTP 404 / model not found / no access | **直接拒绝切换** |
| ⏱️ | 配额超限 | HTTP 429 / rate limit / quota exceeded | **直接拒绝切换** |
| 🌐 | 网络问题 | 连接超时 / URLError | 询问用户确认后才切换 |

---

## 系统要求

| 要求 | 说明 |
|------|------|
| OpenClaw | 任意版本，需已配置 `models.providers` |
| Python | 3.6+（使用标准库，无需 pip 安装） |
| 配置文件 | `~/.openclaw/openclaw.json` 存在且可读写 |

---

## 安全说明

- **API Key 不输出**：Key 仅在内存中用于构造请求头，不会被打印、记录或传到任何第三方
- **最小写权限**：`set-model.py` 仅修改 `agents.defaults.model.primary` 一个字段，不触碰其他配置
- **无外部网络请求**：所有网络请求仅发向 provider 配置的 `baseUrl`，`reload-gateway.py` 仅调用本机 `localhost`
- **原子写入**：配置文件通过临时文件 + `os.replace()` 原子替换，避免写入中断损坏原文件

---

## 许可证

MIT License · © 2026 [Daiyimo](https://github.com/Daiyimo)
