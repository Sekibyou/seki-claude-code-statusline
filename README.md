# Claude Code 状态栏工具

一个用于 Claude Code 的自定义状态栏工具，显示模型信息、会话token进度、block使用比较和费用统计。

> 💡 **灵感来源：** [neo-claude-code-statusline](https://github.com/neorena-dev/neo-claude-code-statusline)

<img width="444" height="141" alt="preview" src="https://github.com/user-attachments/assets/b7ae5ab7-a4aa-4b70-9b0e-17a07190684f" />


  
## 功能特性

### 状态栏显示
```
{模型名称} {会话token进度} {block使用比较} {费用信息}
```
例：`Sonnet 4  ⠿⠿⠿⠿⠁⠀⠀⠀⠀⠀ 42%  ⠿⠁⠀⠀⠀⠀⠀⠀⠀⠀ 13%  $4.8/18.5`

## 特性说明

- 🔵 **会话上下文进度** - 蓝色点阵进度条显示当前会话token使用情况（基于160k限制）
- 🟠 **Block使用比较** - 橙色点阵进度条显示当前活跃block与历史最大token block的比较
- 💰 **费用统计** - 黄色显示当日/当月费用

## 安装步骤

### 1. 安装ccusage
```bash
npm install -g ccusage
```

### 2. 复制文件
将脚本文件复制到 `~/.claude/` 目录：

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
    "command": "python C:/Users/{YourUsername}/.claude/status-line.py"
  }
}
```

**重要提示**：
- `command` 字段需要使用 `status-line.py` 的**完整绝对路径**
- Windows 示例：`"python C:/Users/{YourUsername}/.claude/status-line.py"`
- macOS/Linux 示例：`"python /Users/{YourUsername}/.claude/status-line.py"`
- 请将 `{YourUsername}` 替换为你的实际用户名

### 4. 重启Claude Code
配置完成后重启 Claude Code 即可看到新的状态栏。

## 显示说明

### 颜色含义
- 🔵 **蓝色** - 模型名称和会话token进度
- 🟠 **橙色** - Block使用比较进度
- 🟡 **黄色** - 费用信息

### Block比较逻辑
- 通过 `ccusage blocks -j` 获取所有blocks数据
- 找到当前活跃的block (isActive=true) 和历史上token使用量最多的block
- 计算当前活跃block相对于最大block的token使用比例
- 这样可以直观了解当前session相对于历史最重的session的使用情况

## 系统要求

- Python 3.6+
- ccusage (npm包)
- Claude Code

## 故障排除

如果状态栏显示异常，请检查：
1. ccusage是否正确安装 (`ccusage --version`)
2. Python路径是否正确
3. settings.json配置是否正确
4. 可以修改脚本中的 `DEBUG_TOKENS = True` 来查看调试输出
