# switch-model — 安装指南

## For Humans

复制这句话给你的 AI Agent（OpenClaw、Claude Code、Cursor 等）：

```
帮我安装 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/install.md
```

---

## For AI Agents

### 目标

将 switch-model skill 安装到用户的 OpenClaw skills 目录，让用户可以通过 `/switch-model` 指令或自然语言安全地切换 AI 模型。

### ⚠️ 边界约束

- **不要**使用 `sudo` 执行任何命令，除非用户明确要求
- **不要**修改 `~/.openclaw/skills/switch-model/` 之外的 OpenClaw 配置
- **不要**在用户的项目工作目录中创建文件
- **不要**安装除 Python 3（标准库）以外的任何依赖
- 如遇权限问题，告知用户，由用户决定如何处理

### 📁 目录规则

| 用途 | 目录 |
|------|------|
| Skill 主目录 | `~/.openclaw/skills/switch-model/` |
| OpenClaw 配置 | `~/.openclaw/openclaw.json` |

**不要在用户的项目目录中写入任何文件。**

---

### Step 1：检查环境

确认以下条件满足，任一不满足则告知用户并停止：

```bash
# 检查 Python 3 是否可用
python3 --version

# 检查 OpenClaw 配置文件是否存在
ls ~/.openclaw/openclaw.json
```

如果 `openclaw.json` 不存在，告知用户：
> "未找到 OpenClaw 配置文件（~/.openclaw/openclaw.json）。请确认 OpenClaw 已安装并完成初始配置后再安装此 skill。"

---

### Step 2：克隆仓库到 skills 目录

```bash
# macOS / Linux
git clone https://github.com/Daiyimo/openclaw-switch-model \
  ~/.openclaw/skills/switch-model

# Windows（PowerShell）
git clone https://github.com/Daiyimo/openclaw-switch-model `
  "$env:USERPROFILE\.openclaw\skills\switch-model"
```

如果目录已存在，告知用户：
> "switch-model 已安装。如需更新，请说「更新 switch-model」。"
> 然后停止，不要覆盖现有安装。

---

### Step 3：验证安装

检查关键文件是否存在：

```bash
# macOS / Linux
ls ~/.openclaw/skills/switch-model/SKILL.md
ls ~/.openclaw/skills/switch-model/scripts/list-models.py
ls ~/.openclaw/skills/switch-model/scripts/probe-models.py
ls ~/.openclaw/skills/switch-model/scripts/set-model.py
ls ~/.openclaw/skills/switch-model/scripts/reload-gateway.py

# Windows（PowerShell）
Test-Path "$env:USERPROFILE\.openclaw\skills\switch-model\SKILL.md"
```

所有文件存在 → 安装成功，进入 Step 4。
有文件缺失 → 告知用户哪个文件缺失，建议重新执行 Step 2。

---

### Step 4：快速冒烟测试

运行以下命令，确认脚本可正常读取配置：

```bash
# macOS / Linux
python3 ~/.openclaw/skills/switch-model/scripts/list-models.py

# Windows（PowerShell）
python3 "$env:USERPROFILE\.openclaw\skills\switch-model\scripts\list-models.py"
```

- 输出模型列表 → 一切正常，继续 Step 5
- 输出 `ERROR: 配置文件不存在` → openclaw.json 路径异常，告知用户检查 OpenClaw 是否正确安装
- 输出 `ERROR: 未找到任何模型配置` → openclaw.json 中尚未配置任何模型，告知用户先在 OpenClaw 中添加至少一个 provider

---

### Step 5：完成，告知用户

安装成功后，向用户说明：

```
✅ switch-model 安装完成！

现在你可以：
  • 输入 /switch-model 查看并切换可用模型
  • 直接说「帮我切换模型」、「换一个 AI」也能触发

切换前会自动检测每个模型的 Key 有效性和网络连通性，Key 失效的模型会被标出，防止切换到不可用的模型。
```

---

## 后续维护

安装完成后，你（Agent）也可以帮用户维护：

### 更新 switch-model

```bash
python3 ~/.openclaw/skills/switch-model/scripts/update-skill.py
```

### 卸载 switch-model

```bash
# 有确认提示
python3 ~/.openclaw/skills/switch-model/scripts/uninstall-skill.py

# 跳过确认（自动化流程用）
python3 ~/.openclaw/skills/switch-model/scripts/uninstall-skill.py --force
```
