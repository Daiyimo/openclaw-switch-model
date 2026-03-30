---
name: switch-model
description: 切换当前使用的 AI 模型。当用户想切换模型、选择不同的 AI 提供商、查看可用模型列表、询问当前用的哪个模型、测试模型是否正常时触发。
version: 1.1.0
homepage: https://github.com/Daiyimo/openclaw-switch-model
user-invocable: true
metadata: {"openclaw":{"emoji":"🔀","requires":{"config":["models"]}}}
agent-invocable-commands:
  - "更新 switch-model"
  - "更新这个 skill"
  - "升级 switch-model"
  - "卸载 switch-model"
  - "删除 switch-model"
  - "移除 switch-model"
---

# switch-model — AI 模型切换助手

帮助用户安全地检测并切换 OpenClaw 配置中的 AI 模型，切换前自动探测各模型连通性和 Key 有效性，避免切换到不可用的模型导致服务中断。

---

## 工作流程

### 第一步：读取模型列表

运行以下命令，获取所有配置的模型和当前 primary 模型：

```bash
python3 "{baseDir}/scripts/list-models.py"
```

输出格式：
- 第一行：当前 primary 模型 ID（如 `stepfun/step-3.5-flash`）
- 后续每行：`provider/modelId\t模型名称`

---

### 第二步：探测所有模型连通性与 Key 有效性

> ⚠️ **这一步必须执行，不可跳过**：Key 过期或网络故障会导致切换后 openclaw 完全不可用。

```bash
python3 "{baseDir}/scripts/probe-models.py"
```

每行输出格式：
- `provider/modelId\tOK\t模型名称` — 连通且 Key 有效
- `provider/modelId\tFAIL\t模型名称\t失败原因` — 失败（原因见下方分类）

执行前告知用户：
> "正在检测各模型连通性和 Key 有效性，请稍候……"

---

### 第三步：解读失败原因并向用户展示

**失败原因分类标准**（根据失败原因文字判断）：

| 失败原因包含关键词 | 判定类型 | 含义 |
|---|---|---|
| `HTTP 401` / `HTTP 403` / `unauthorized` / `invalid.*key` / `key.*expired` / `authentication` / `access denied` | 🔑 **Key 失效** | API Key 过期或无效，必须更换 |
| `HTTP 404` / `does not exist` / `not found` / `no access` | 🚫 **模型不可用** | 模型 ID 错误或无权访问 |
| `HTTP 429` / `rate limit` / `quota` | ⏱️ **配额超限** | 超出调用频率或额度 |
| `连接失败` / `URLError` / `timeout` / `timed out` | 🌐 **网络问题** | 网络不通，可能是临时故障 |
| 其他 | ❓ **未知错误** | 其他原因 |

**展示格式**（在可选项编号前标注状态）：

```
🔍 模型检测完成：

  ✅ 1. Step 3.5 Flash    stepfun/step-3.5-flash  ← 当前
  ✅ 2. Step 3.5 Flash Free  openrouter/stepfun/...
  🔑    MiniMax M2.5       minimax/MiniMax-M2.5   (Key 已失效)

当前使用：Step 3.5 Flash（stepfun/step-3.5-flash）✅ 正常

请问想切换到哪个模型？（输入编号或名称）
```

特殊提示：
- 当前模型 FAIL → 在列表前额外显示：`⚠️ 当前模型 [模型名] 检测不可用（[失败原因类型]），建议立即切换！`
- 全部 FAIL → 告知所有模型均不可用，停止流程，不询问切换

---

### 第四步：等待用户选择

用户可用以下方式表达：
- 编号（如 `1`、`选 2`）
- 名称片段（如 `MiniMax`、`flash`，大小写不敏感）
- 完整 ID（如 `minimax/MiniMax-M2.5`）

**匹配后的阻断规则（按优先级）**：

1. **Key 失效 / 模型不可用 / 配额超限** → **直接拒绝，不切换**
   > "❌ 该模型检测到 [失败原因类型]，切换后 openclaw 将无法正常使用。如需使用，请先更新 API Key。"

2. **网络问题** → 询问用户是否确认（给出风险提示）
   > "⚠️ 该模型目前网络不通，可能是临时故障。仍然切换吗？（yes/no）"
   > 用户确认 yes 才继续，no 则重新让用户选择。

3. **目标与当前相同且当前 OK** → 告知已在使用该模型，不做写入，结束。

4. **OK 的模型** → 直接进入写入步骤。

---

### 第五步：重启 gateway 并应用配置

确认目标模型 ID 后，运行以下脚本执行完整的 stop/config/start 流程（需要 sudo 权限）：

```bash
python3 "{baseDir}/scripts/reload-gateway.py" "TARGET_MODEL_ID"
```

将 `TARGET_MODEL_ID` 替换为实际的模型 ID 字符串（如 `stepfun/step-3.5-flash`）。

脚本会执行以下步骤：
1. `sudo openclaw gateway stop` - 停止 gateway
2. `sudo openclaw config set agents.defaults.model.primary TARGET_MODEL_ID` - 设置新模型
3. `sudo openclaw gateway start` - 启动 gateway
4. 等待 gateway 恢复正常（最多 15 秒）

根据输出给出对应反馈：

| 输出 | 含义 | 向用户说明 |
|------|------|-----------|
| `RESTARTED` | gateway 已成功重启并恢复正常 | "✅ 已从 [旧模型] 切换到 [新模型]，gateway 已恢复" |
| `FAILED:...` | gateway 重启失败 | "⚠️ gateway 重启失败：[原因]。请手动执行 `sudo openclaw gateway start`" |

---

### 第七步：最终确认

切换完成后，用一句话总结：

```
✅ 已从 [旧模型名]（[旧模型ID]）切换到 [新模型名]（[新模型ID]），继续吧！
```

## 边界情况处理

- **probe-models.py 执行超时或崩溃**：告知用户探测失败，**不继续切换流程**，建议检查网络后重试
- **reload-gateway.py 执行失败**：告知配置更新失败，提示手动执行 `sudo openclaw gateway stop && sudo openclaw config set agents.defaults.model.primary <model_id> && sudo openclaw gateway start`
- **没有任何模型配置**：提示用户在 `openclaw.json` 的 `models.providers` 中添加模型

---

## 注意事项

- 本 skill 探测模型时仅发送 `max_tokens=1` 的最小请求，不产生有效对话内容
- API Key 在内存中使用，不会被输出、记录或外传
- `reload-gateway.py` 需要 sudo 权限执行 gateway 启停和配置命令
- 重启 gateway 通常需要 5-15 秒，期间会短暂中断服务

---

## Agent 维护命令

### 更新 switch-model

当用户说"更新 switch-model"、"升级这个 skill"等时触发。

运行更新脚本：

```bash
python3 "{baseDir}/scripts/update-skill.py"
```

**流程**：
1. 自动备份当前版本到 `~/.openclaw/skills/switch-model.bak`
2. 优先使用 Git 拉取最新代码
3. Git 失败时，使用复制当前目录方式更新
4. 验证关键文件完整性

**向用户说明**：
- 更新前告知："正在更新 switch-model 到最新版本，请稍候……"
- 成功时："✅ switch-model 已更新到最新版本"
- 失败时："⚠️ 更新失败，已恢复原版本：[原因]"

---

### 卸载 switch-model

当用户说"卸载 switch-model"、"删除这个 skill"等时触发。

运行卸载脚本：

```bash
python3 "{baseDir}/scripts/uninstall-skill.py"
```

如需强制卸载（跳过确认）：

```bash
python3 "{baseDir}/scripts/uninstall-skill.py" --force
```

**流程**：
1. 确认用户意图（除非 --force）
2. 移除 `~/.openclaw/skills/switch-model` 目录
3. 保留备份目录于 `~/.openclaw/skills/switch-model.bak`

**向用户说明**：
- 确认时："确定要卸载 switch-model 吗？卸载后将无法使用 /switch-model 命令。"
- 成功时："✅ switch-model 已卸载完成"
