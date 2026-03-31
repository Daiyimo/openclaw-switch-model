# switch-model

> OpenClaw Skill · 安全切换 AI 模型，切换前自动检测 Key 有效性，防止切换到不可用模型导致服务中断。

---

## 功能特性

- 🔍 **自动探测**：切换前对所有配置的模型发送探针请求，检测连通性和 API Key 有效性
- 🔑 **Key 有效性检测**：能识别 Key 过期（401/403）、模型不可用（404）、配额超限（429）等具体原因
- 🛡️ **切换保护**：Key 失效或模型不可用时直接拒绝切换，避免 OpenClaw 因切换到不可用模型而崩溃
- 🌐 **代理模式支持**：对走 OpenClaw gateway 代理的 provider（如 MiniMax），通过 gateway 转发探针，准确检测真实 Key 状态
- ♻️ **完整重启**：使用 sudo（Unix/Linux）或管理员权限（Windows）执行 stop/config/start 流程确保配置可靠生效
- 🖥️ **跨平台**：兼容 Windows / macOS / Linux，Python 3 标准库实现，无需额外依赖（Windows 需要管理员权限）
- 🤝 **多 Provider 兼容**：支持 Claude、GLM、MiniMax、Stepfun、OpenRouter 等任意在 `openclaw.json` 中配置的模型
- 🔄 **一键更新**：Agent 可调用更新脚本自动拉取最新版本，支持 Git 拉取和目录复制两种方式
- 🗑️ **一键卸载**：Agent 可调用卸载脚本完整移除 skill

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
      gateway 已重启恢复，继续吧！
```

---

## 安装

### 方式零：Agent 一键安装（最省心）

复制这句话给你的 AI Agent（OpenClaw、Claude Code、Cursor 等）：

```
帮我安装 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/install.md
```

Agent 会自动完成克隆、验证和冒烟测试，几步搞定。

> 🔄 **已装过？更新也是一句话：**
> ```
> 帮我更新 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/update.md
> ```

> 🗑️ **想卸载？同样一句话：**
> ```
> 帮我卸载 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/uninstall.md
> ```

---

### 方式一：手动安装

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
├── .gitattributes            # Git 配置：统一行尾符、二进制文件
├── .gitignore                # Git 忽略：Python 缓存、临时文件
├── LICENSE                   # MIT License 许可证
├── README.md                 # 项目说明文档
├── SKILL.md                  # Skill 主入口，定义触发规则和执行流程
├── docs/
│   ├── install.md            # Agent 安装指南
│   ├── uninstall.md          # Agent 卸载指南
│   └── update.md             # Agent 更新指南
└── scripts/
    ├── list-models.py         # 读取 openclaw.json 中的模型列表和当前 primary 模型
    ├── probe-models.py        # 对每个模型发探针请求，检测连通性和 Key 有效性
    ├── reload-gateway.py      # 使用 sudo（Unix）或管理员权限（Windows）执行 stop/config/start 重启 gateway
    ├── update-skill.py        # 一键更新 skill 到最新版本（面向 Agent）
    └── uninstall-skill.py     # 一键卸载 skill（面向 Agent）
```

---

## Agent 一键维护命令

### 更新 skill

复制给 Agent（推荐）：

```
帮我更新 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/update.md
```

或直接调用脚本：

```bash
python3 ~/.openclaw/skills/switch-model/scripts/update-skill.py
```

- 自动备份当前版本到 `~/.openclaw/skills/switch-model.bak`
- 优先使用 Git 拉取，失败时使用复制当前目录方式
- 验证关键文件完整性后完成更新

### 卸载 skill

复制给 Agent（推荐）：

```
帮我卸载 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/uninstall.md
```

或直接调用脚本：

```bash
# 普通卸载（会询问确认）
python3 ~/.openclaw/skills/switch-model/scripts/uninstall-skill.py

# 强制卸载（跳过确认，用于自动化流程）
python3 ~/.openclaw/skills/switch-model/scripts/uninstall-skill.py --force
```

- 移除 `~/.openclaw/skills/switch-model` 目录
- 备份目录 `~/.openclaw/skills/switch-model.bak` 保留不动

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
| 权限 | Unix/Linux: 已配置 sudo 权限；Windows: 以管理员身份运行 |

---

## 安全说明

- **API Key 不输出**：Key 仅在内存中用于构造请求头，不会被打印、记录或传到任何第三方
- **最小写权限**：`reload-gateway.py` 通过 sudo（Unix/Linux）或管理员权限（Windows）执行 config 命令，仅修改 `agents.defaults.model.primary` 一个字段
- **无外部网络请求**：所有网络请求仅发向 provider 配置的 `baseUrl`，`reload-gateway.py` 仅调用本机 `localhost` 健康检查
- **原子操作**：stop/config/start 流程确保 gateway 一致性，避免部分更新导致的不一致状态；更新 skill 时采用备份-替换-清理的原子操作，失败可回滚

---

## 许可证

MIT License · © 2026 [Daiyimo](https://github.com/Daiyimo)
