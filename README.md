# Claude Code 状态栏工具

一个用于 Claude Code 的自定义状态栏工具，实时显示模型信息、token使用情况和费用统计。

## 功能特性

状态栏显示格式：
```
{模型名称} {当前会话token使用进度条+百分比} {五小时限额进度条+百分比} {当日费用}/{当月费用}({本日用量对比当月平均值百分比})
```

- 🔵 **会话上下文进度** - 蓝色进度条显示当前会话token使用情况（基于160k限制）
- 🟠 **会话限额进度** - 橙色进度条显示五小时token限额使用情况
- 💰 **费用统计** - 显示当日费用/当月费用，以及相对历史平均值的变化百分比
- 📊 **智能格式化** - 自动使用k/m单位进位显示大数值

## 安装步骤

### 1. 安装ccusage
```bash
npm install -g ccusage
```

### 2. 复制脚本文件
将 `status-line.py` 复制到 `~/.claude/` 目录：

**Windows:**
```cmd
copy status-line.py %USERPROFILE%\.claude\
```

**macOS/Linux:**
```bash
cp status-line.py ~/.claude/
```

### 3. 配置settings.json
在 `~/.claude/` 目录中创建或编辑 `settings.json` 文件：

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "statusLine": {
    "type": "command",
    "command": "python status-line.py"
  }
}
```

### 4. 重启Claude Code
配置完成后重启 Claude Code 即可看到新的状态栏。

## 颜色说明

- 🔵 **蓝色** - 模型名称和会话token进度
- 🟠 **橙色** - 五小时限额进度  
- 🟡 **黄色** - 费用信息
- 🟢 **绿色** - 费用高于平均值的百分比
- 🔴 **红色** - 费用低于平均值的百分比

## 调试模式

设置环境变量开启调试模式：
```bash
set DEBUG_TOKENS=1  # Windows
export DEBUG_TOKENS=1  # macOS/Linux
```

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