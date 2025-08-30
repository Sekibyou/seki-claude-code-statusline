# Claude Code 状态栏工具

一个用于 Claude Code 的自定义状态栏工具，显示模型信息、会话token进度、block使用比较、费用统计和时间范围。

> 💡 **灵感来源：** [neo-claude-code-statusline](https://github.com/neorena-dev/neo-claude-code-statusline)

<img width="444" height="141" alt="preview" src="https://github.com/user-attachments/assets/b7ae5ab7-a4aa-4b70-9b0e-17a07190684f" />

## 功能特性

### 双行状态栏显示
```
第一行：{模型名称} {会话token进度} {费用信息}
第二行：{block使用比较} {活跃时间范围}
```

**示例显示：**
```
Sonnet 4  ⠿⠿⠿⠿⠁⠀⠀⠀⠀⠀ ⠀42%  $12.8/40.1(d/m)
          ⠿⠁⠀⠀⠀⠀⠀⠀⠀⠀ ⠀35%  Tokyo 1:00~6:00
```

## 特性说明

- 🔵 **会话上下文进度** - 浅蓝色点阵进度条显示当前会话token使用情况（基于160k限制）
- 🟠 **Block使用比较** - 橙色点阵进度条显示当前活跃block与历史最大token block的比较  
- 💰 **费用统计** - 黄色显示每日/每月费用，格式：`$日费用/月费用(d/m)`
- 🕐 **时间范围** - 橙色显示活跃block的时间范围，自动检测并转换为系统本地时区

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
- 🔵 **浅蓝色** - 模型名称和会话token进度
- 🟠 **橙色** - Block使用比较进度和时间范围
- 🟡 **黄色** - 费用信息

### 显示特点
- **智能对齐**: 两行进度条完美垂直对齐，百分比动态占位对齐（⠀⠀0%, ⠀35%, 100%）
- **时间格式**: 自动去除小时前导零（1:00 而非 01:00）
- **时区转换**: 自动检测系统时区并转换UTC时间，智能显示友好的地区名称
- **费用展示**: 紧凑的费用格式，清晰标注日/月

### Block比较逻辑
- 通过 `ccusage blocks -j` 获取所有blocks数据
- 找到当前活跃的block (isActive=true) 和历史上token使用量最多的block
- 计算当前活跃block相对于最大block的token使用比例
- 这样可以直观了解当前session相对于历史最重的session的使用情况

### 时间范围功能
- 通过 `ccusage blocks --active -j` 获取活跃block的startTime和endTime
- 自动检测系统时区并转换UTC时间
- 基于UTC偏移量智能识别时区：
  - UTC+9 → Tokyo
  - UTC+8 → Beijing  
  - UTC-5/-4 → NewYork (自动处理EST/EDT)
  - UTC-8/-7 → LosAngeles (自动处理PST/PDT)
  - UTC+0 → London
  - UTC+1/+2 → Berlin (自动处理CET/CEST)
  - UTC+5.5 → NewDelhi
  - UTC+10 → Sydney
  - 其他时区显示UTC偏移量（如UTC+3, UTC-6）
- 显示格式：`地区 开始时间~结束时间`（如：Tokyo 1:00~6:00）

## 系统要求

- Python 3.6+
- ccusage (npm包)  
- Claude Code

## 自定义配置

### 添加时区识别
如果你希望为你的时区添加友好显示名称，可以编辑 `status-line.py` 文件中的UTC偏移量识别逻辑：
```python
# 在时区识别部分添加你的时区
elif utc_offset == 3:  # UTC+3
    tz_display = 'Moscow'
elif utc_offset == -3:  # UTC-3
    tz_display = 'SaoPaulo'
```

这种方法比名称映射更可靠，因为它基于实际的时间偏移量而不是时区名称字符串。

## 故障排除

如果状态栏显示异常，请检查：
1. ccusage是否正确安装 (`ccusage --version`)
2. Python路径是否正确
3. settings.json配置是否正确
4. 可以修改脚本中的 `DEBUG_TOKENS = True` 来查看调试输出

## 更新日志

### 最新版本特性
- ✨ 新增双行显示布局，信息更丰富
- ✨ 新增活跃block时间范围显示
- ✨ 智能百分比对齐，显示更整洁  
- ✨ 自动系统时区检测，无需手动配置
- ✨ 智能时区名称映射，友好显示地区名称
- ✨ 优化费用显示格式，更加紧凑清晰
- ✨ 统一颜色方案，视觉效果更佳
- 🔧 移除pytz依赖，使用Python内置时区功能
