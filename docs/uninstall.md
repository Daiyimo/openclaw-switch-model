# switch-model — 卸载指南

## For Humans

复制这句话给你的 AI Agent（OpenClaw、Claude Code、Cursor 等）：

```
帮我卸载 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/uninstall.md
```

---

## For AI Agents

### 目标

完整移除用户已安装的 switch-model skill，并告知用户操作结果。

### ⚠️ 边界约束

- **不要**删除 `~/.openclaw/skills/switch-model.bak` 备份目录（保留备份，由用户自行决定是否删除）
- **不要**修改 `~/.openclaw/openclaw.json` 或其他 OpenClaw 配置
- **必须先确认用户意图**，再执行卸载

---

### Step 1：向用户确认

在执行任何操作之前，先向用户确认：

> "确定要卸载 switch-model 吗？卸载后将无法使用 `/switch-model` 命令。如果以后想重新安装，重新运行安装指令即可。"

等待用户明确回复"确定"、"是"、"yes"等肯定意图后再继续。
用户回复取消则停止，**不执行任何操作**。

---

### Step 2：运行卸载脚本

```bash
# macOS / Linux
python3 ~/.openclaw/skills/switch-model/scripts/uninstall-skill.py --force

# Windows（PowerShell）
python3 "$env:USERPROFILE\.openclaw\skills\switch-model\scripts\uninstall-skill.py" --force
```

`--force` 跳过脚本内置的交互确认（你已在 Step 1 向用户确认过了）。

输出以 `✅ 卸载完成` 结尾 → 成功，进入 Step 3。
输出包含 `[ERROR]` → 告知用户错误详情，建议手动删除安装目录。

---

### Step 3：验证已移除

```bash
# macOS / Linux
ls ~/.openclaw/skills/switch-model 2>/dev/null && echo "仍然存在" || echo "已移除"

# Windows（PowerShell）
if (Test-Path "$env:USERPROFILE\.openclaw\skills\switch-model") { "仍然存在" } else { "已移除" }
```

确认目录不存在后，告知用户：

```
✅ switch-model 已卸载完成。
/switch-model 命令已停用。
备份保留于 ~/.openclaw/skills/switch-model.bak，如需彻底清除可手动删除。
```

---

### 重新安装

如果用户将来想重新安装，复制以下内容给 Agent：

```
帮我安装 switch-model：https://raw.githubusercontent.com/Daiyimo/openclaw-switch-model/main/docs/install.md
```
