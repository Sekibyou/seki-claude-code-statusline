# Claude Code 状态栏工具

一个用于 Claude Code 的自定义状态栏工具，支持双模式显示：会员模式显示限额进度和时间，非会员模式显示费用统计。

> 💡 **灵感来源：** [neo-claude-code-statusline](https://github.com/neorena-dev/neo-claude-code-statusline)

<img width="527" height="152" alt="preview" src="https://github.com/user-attachments/assets/72c4b775-570f-44a1-b7e8-f4c6a1433044" />


  
## 功能特性

### 会员模式 (配置了 `SUBSCRIPTION_TYPE`)
```
{模型名称} {会话token进度} {五小时限额进度} {城市名 时间段}
```
例：`Sonnet 4  ⠿⠿⠿⠿⠁⠀⠀⠀⠀⠀ 42%  ⠿⠁⠀⠀⠀⠀⠀⠀⠀⠀ 13%  Tokyo 15:00~20:00`

### 非会员模式 (未配置 `SUBSCRIPTION_TYPE`)
```
{模型名称} {会话token进度} {当日费用}/{当月费用}({趋势})
```
例：`Sonnet 4  ⠿⠿⠿⠿⠁⠀⠀⠀⠀⠀ 42%  $4.8/18.5(-15%)`

## 特性说明

- 🔵 **会话上下文进度** - 蓝色点阵进度条显示当前会话token使用情况（基于200k限制）
- 🟠 **五小时限额进度** - 橙色点阵进度条显示会员限额使用情况（仅会员模式）
- ⏰ **智能时区显示** - 自动检测系统时区，显示会话时间段（仅会员模式）
- 💰 **费用统计** - 显示当日/当月费用及趋势对比（仅非会员模式）

## 安装步骤

### 1. 安装ccusage
```bash
npm install -g ccusage
```

### 2. 复制文件
将脚本文件和配置文件复制到 `~/.claude/` 目录：

**Windows:**
```cmd
copy status-line.py %USERPROFILE%\.claude\
copy .env.example %USERPROFILE%\.claude\.env
```

**macOS/Linux:**
```bash
cp status-line.py ~/.claude/
cp .env.example ~/.claude/.env
```

### 3. 配置会员类型
编辑 `~/.claude/.env` 文件，设置你的会员类型：

```env
# 会员用户设置（根据你的实际会员类型）
SUBSCRIPTION_TYPE=max5x

# 非会员用户设置
SUBSCRIPTION_TYPE=
```

**会员类型说明：**
- `pro` - Pro用户 (20M tokens, 5小时限额)
- `max5x` - MAX 5X用户 (100M tokens, 5小时限额)
- `max20x` - MAX 20X用户 (400M tokens, 5小时限额)
- 留空或删除 - 非会员模式，显示费用分析

### 4. 配置settings.json
在 `~/.claude/` 目录中创建或编辑 `settings.json` 文件：

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "statusLine": {
    "type": "command",
    "command": "python C:/Users/{YourUsername}/.claude/status-line.py"
  }
}
```

**重要提示**：
- `command` 字段需要使用 `status-line.py` 的**完整绝对路径**
- Windows 示例：`"python C:/Users/{YourUsername}/.claude/status-line.py"`
- macOS/Linux 示例：`"python /Users/{YourUsername}/.claude/status-line.py"`
- 请将 `{YourUsername}` 替换为你的实际用户名

### 5. 重启Claude Code
配置完成后重启 Claude Code 即可看到新的状态栏。

## 显示说明

### 颜色含义
- 🔵 **蓝色** - 模型名称和会话token进度
- 🟠 **橙色** - 五小时限额进度和时间（会员模式）
- 🟡 **黄色** - 费用信息（非会员模式）
- 🟢 **绿色** - 费用高于平均值的百分比（非会员模式）
- 🔴 **红色** - 费用低于平均值的百分比（非会员模式）

### 时间显示
- 自动检测系统时区
- 24小时制格式：`Tokyo 15:00~20:00`
- 显示五小时会话的起止时间

## 系统要求

- Python 3.6+
- ccusage (npm包)
- Claude Code

## 故障排除

如果状态栏显示异常，请检查：
1. ccusage是否正确安装 (`ccusage --version`)
2. Python路径是否正确
3. settings.json配置是否正确
4. 查看调试输出排查问题
