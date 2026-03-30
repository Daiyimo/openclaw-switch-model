# switch-model — 更新指南

## For Humans

复制这句话给你的 AI Agent（OpenClaw、Claude Code、Cursor 等）：

```
帮我更新 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/update.md
```

---

## For AI Agents

### 目标

将用户已安装的 switch-model skill 更新到最新版本，保留备份，验证完整性。

### ⚠️ 边界约束

- **不要**修改 `~/.openclaw/skills/switch-model/` 之外的任何文件
- **不要**在用户的项目工作目录中创建文件
- 更新失败时自动恢复备份，不要让用户手动处理

---

### Step 1：确认已安装

```bash
# macOS / Linux
ls ~/.openclaw/skills/switch-model/SKILL.md

# Windows（PowerShell）
Test-Path "$env:USERPROFILE\.openclaw\skills\switch-model\SKILL.md"
```

如果目录不存在，告知用户：
> "未找到 switch-model 安装。请先安装：复制「帮我安装 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/install.md」给 Agent 即可。"
> 然后停止。

---

### Step 2：运行更新脚本

```bash
# macOS / Linux
python3 ~/.openclaw/skills/switch-model/scripts/update-skill.py

# Windows（PowerShell）
python3 "$env:USERPROFILE\.openclaw\skills\switch-model\scripts\update-skill.py"
```

脚本会自动完成：
1. 备份当前版本到 `~/.openclaw/skills/switch-model.bak`
2. 优先通过 `git pull` 拉取最新代码
3. Git 失败时自动切换为目录复制方式
4. 验证关键文件完整性，失败则自动恢复备份

输出以 `✅ 更新完成` 结尾 → 成功，进入 Step 3。
输出包含 `[ERROR]` → 告知用户具体错误信息，建议手动 `git clone` 重新安装。

---

### Step 3：验证更新结果

```bash
# macOS / Linux
python3 ~/.openclaw/skills/switch-model/scripts/list-models.py

# Windows（PowerShell）
python3 "$env:USERPROFILE\.openclaw\skills\switch-model\scripts\list-models.py"
```

能正常输出模型列表 → 更新成功，告知用户：

```
✅ switch-model 已更新到最新版本！
/switch-model 命令可正常使用。
```

---

### 备份说明

更新前的旧版本备份保存于：
- macOS / Linux：`~/.openclaw/skills/switch-model.bak`
- Windows：`%USERPROFILE%\.openclaw\skills\switch-model.bak`

如需回滚，手动将 `.bak` 目录重命名为 `switch-model` 即可。
