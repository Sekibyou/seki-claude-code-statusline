#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code StatusLine - 重构版本
显示：模型信息、会话token进度(蓝色)、block token比较(橙色)、美元费用
"""

import sys
import json
import subprocess
import shutil
import io
from datetime import datetime, timedelta
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 调试开关
DEBUG_TOKENS = False

# 预生成进度条缓存
DOT_CHARS = ['⠀', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿']  # 0-6个点
PROGRESS_BARS = {}

# 生成精细进度条缓存
for percentage in range(0, 101):
    total_dots = int((percentage * 60) / 100)  # 总共60个点
    full_chars = total_dots // 6  # 完整字符数
    remaining_dots = total_dots % 6  # 剩余点数
    
    # 构建进度条
    progress = DOT_CHARS[6] * full_chars  # 满点字符
    if remaining_dots > 0 and full_chars < 10:
        progress += DOT_CHARS[remaining_dots]  # 部分点字符
        empty_chars = 10 - full_chars - 1
    else:
        empty_chars = 10 - full_chars
    
    # 添加空字符（灰色）
    progress += "\033[38;5;240m" + DOT_CHARS[0] * empty_chars + "\033[0m"
    
    PROGRESS_BARS[percentage] = progress

def debug_log(message):
    """调试日志输出"""
    if DEBUG_TOKENS:
        print(f"[DEBUG] {message}", file=sys.stderr)

def get_model_name(data):
    """获取模型显示名称"""
    try:
        return data.get('model', {}).get('display_name', 'Unknown')
    except:
        return 'Unknown'

def process_transcript(transcript_path):
    """处理transcript文件，提取token使用量"""
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 从后往前查找最后一个有效的assistant消息
        for line in reversed(lines):
            try:
                data = json.loads(line.strip())
                
                if (data.get('type') == 'assistant' and 
                    'message' in data and 
                    'usage' in data['message']):
                    
                    usage = data['message']['usage']
                    
                    if all(key in usage for key in ['input_tokens', 'cache_creation_input_tokens', 
                                                     'cache_read_input_tokens', 'output_tokens']):
                        total_tokens = (
                            usage.get('input_tokens', 0) +
                            usage.get('cache_creation_input_tokens', 0) +
                            usage.get('cache_read_input_tokens', 0) +
                            usage.get('output_tokens', 0)
                        )
                        
                        debug_log(f"找到有效token数据: {total_tokens}")
                        return total_tokens
                        
            except json.JSONDecodeError:
                continue
            except Exception as e:
                debug_log(f"处理行时出错: {e}")
                continue
        
        debug_log("未找到有效的token数据")
        return 0
        
    except FileNotFoundError:
        debug_log(f"transcript文件不存在: {transcript_path}")
        return 0
    except Exception as e:
        debug_log(f"读取transcript文件出错: {e}")
        return 0

def get_session_tokens(data):
    """获取会话token使用情况（蓝色进度条）"""
    try:
        transcript_path = data.get('transcript_path', '')
        debug_log(f"提取的transcript_path: {transcript_path}")
        
        if not transcript_path:
            debug_log("错误: transcript_path为空")
            return "\033[0;38;2;91;155;214m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;38;2;91;155;214m⠀⠀0%\033[0m"
        
        # 处理transcript文件
        total_tokens = process_transcript(transcript_path)
        
        if total_tokens > 0:
            # 基于160k计算使用百分比
            actual_percentage = round((total_tokens * 100) / 160000)
            display_percentage = min(100, actual_percentage)
            
            debug_log(f"蓝色进度条计算: tokens={total_tokens}, 160k限制, 实际百分比={actual_percentage}%, 显示百分比={display_percentage}%")
            
            progress_bar = PROGRESS_BARS.get(display_percentage, "\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m")
            
            # 返回蓝色的进度条，百分比显示实际值（动态对齐到3位数宽度）
            percentage_padding = ""
            if actual_percentage < 10:
                percentage_padding = "⠀⠀"  # 两个占位符
            elif actual_percentage < 100:
                percentage_padding = "⠀"    # 一个占位符
            return f"\033[0;38;2;91;155;214m{progress_bar}\033[0m \033[0;38;2;91;155;214m{percentage_padding}{actual_percentage}%\033[0m"
        else:
            return "\033[0;38;2;91;155;214m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;38;2;91;155;214m⠀⠀0%\033[0m"
            
    except Exception as e:
        debug_log(f"发生错误: {e}")
        return "\033[0;38;2;91;155;214m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;38;2;91;155;214m⠀⠀0%\033[0m"

def get_blocks_comparison():
    """获取blocks token比较（橙色进度条）"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        debug_log("ccusage命令不可用")
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m⠀⠀0%\033[0m"
    
    try:
        result = subprocess.run(
            ['ccusage', 'blocks', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            blocks = data.get('blocks', [])
            
            if not blocks:
                debug_log("没有blocks数据")
                return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m⠀⠀0%\033[0m"
            
            # 找到当前活跃的block
            active_block = None
            max_tokens = 0
            
            for block in blocks:
                total_tokens = block.get('totalTokens', 0)
                if total_tokens > max_tokens:
                    max_tokens = total_tokens
                
                if block.get('isActive', False):
                    active_block = block
            
            if active_block is None:
                debug_log("没有找到活跃block")
                return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m⠀⠀0%\033[0m"
            
            active_tokens = active_block.get('totalTokens', 0)
            
            if max_tokens == 0:
                actual_percentage = 0
            else:
                actual_percentage = round((active_tokens * 100) / max_tokens)
            
            display_percentage = min(100, actual_percentage)
            
            debug_log(f"橙色进度条计算: active_tokens={active_tokens}, max_tokens={max_tokens}, 实际百分比={actual_percentage}%, 显示百分比={display_percentage}%")
            
            progress_bar = PROGRESS_BARS.get(display_percentage, "\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m")
            
            # 返回橙色的进度条，百分比显示实际值（动态对齐到3位数宽度）
            percentage_padding = ""
            if actual_percentage < 10:
                percentage_padding = "⠀⠀"  # 两个占位符
            elif actual_percentage < 100:
                percentage_padding = "⠀"    # 一个占位符
            return f"\033[38;5;208m{progress_bar}\033[0m \033[38;5;208m{percentage_padding}{actual_percentage}%\033[0m"
        
        # 默认返回值
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m⠀⠀0%\033[0m"
        
    except Exception as e:
        debug_log(f"获取blocks信息时出错: {e}")
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m⠀⠀0%\033[0m"

def get_active_block_time_range():
    """获取活跃block的时间范围，转换为本地时区显示"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        debug_log("ccusage命令不可用")
        return "N/A"
    
    try:
        result = subprocess.run(
            ['ccusage', 'blocks', '--active', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            blocks = data.get('blocks', [])
            
            # 找到活跃的block
            for block in blocks:
                if block.get('isActive', False):
                    start_time_str = block.get('startTime')
                    end_time_str = block.get('endTime')
                    
                    if start_time_str and end_time_str:
                        # 解析UTC时间
                        start_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        end_utc = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        
                        # 自动使用系统本地时区
                        start_local = start_utc.astimezone()
                        end_local = end_utc.astimezone()
                        
                        # 获取时区显示名称 - 使用UTC偏移量自动识别
                        try:
                            # 获取UTC偏移量（单位：秒）
                            utc_offset = start_local.utcoffset().total_seconds() / 3600
                            
                            # 根据UTC偏移量自动识别常见时区
                            if utc_offset == 9:  # UTC+9
                                tz_display = 'Tokyo'
                            elif utc_offset == 8:  # UTC+8
                                tz_display = 'Beijing'
                            elif utc_offset == -5:  # UTC-5
                                tz_display = 'NewYork'
                            elif utc_offset == -4:  # UTC-4 (EDT)
                                tz_display = 'NewYork'
                            elif utc_offset == -8:  # UTC-8
                                tz_display = 'LosAngeles'
                            elif utc_offset == -7:  # UTC-7 (PDT)
                                tz_display = 'LosAngeles'
                            elif utc_offset == 0:  # UTC+0
                                tz_display = 'London'
                            elif utc_offset == 1:  # UTC+1 (CET)
                                tz_display = 'Berlin'
                            elif utc_offset == 2:  # UTC+2 (CEST)
                                tz_display = 'Berlin'
                            elif utc_offset == 5.5:  # UTC+5.5
                                tz_display = 'NewDelhi'
                            elif utc_offset == 10:  # UTC+10
                                tz_display = 'Sydney'
                            else:
                                # 对于其他时区，显示UTC偏移量
                                if utc_offset >= 0:
                                    tz_display = f'UTC+{int(utc_offset)}'
                                else:
                                    tz_display = f'UTC{int(utc_offset)}'
                        except:
                            tz_display = 'Local'
                        
                        # 格式化时间显示（去掉小时前导零）
                        start_formatted = start_local.strftime('%H:%M').lstrip('0') or '0:' + start_local.strftime('%M')
                        end_formatted = end_local.strftime('%H:%M').lstrip('0') or '0:' + end_local.strftime('%M')
                        
                        debug_log(f"时间范围: {tz_display} {start_formatted}-{end_formatted}")
                        return f"{tz_display} {start_formatted}~{end_formatted}"
            
            debug_log("没有找到活跃block")
            return "N/A"
        
        debug_log(f"ccusage命令失败: {result.returncode}")
        return "N/A"
        
    except Exception as e:
        debug_log(f"获取时间范围时出错: {e}")
        return "N/A"

def format_cost(cost):
    """格式化费用显示"""
    if cost == "N/A" or not isinstance(cost, (int, float)):
        return "N/A"
    
    if cost < 1000:  # 小于1000美元
        return f"{cost:.1f}"
    elif cost < 1000000:  # 1k-999k美元
        k_value = cost / 1000
        return f"{k_value:.1f}k"
    else:  # >= 1m美元
        m_value = cost / 1000000
        return f"{m_value:.1f}m"

def get_cost_info():
    """获取费用信息"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        debug_log("ccusage命令不可用")
        return "N/A", "N/A"
    
    try:
        # 获取今日费用
        result = subprocess.run(
            ['ccusage', 'daily', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        daily_cost = "N/A"
        if result.returncode == 0:
            data = json.loads(result.stdout)
            daily_data = data.get('daily', [])
            if daily_data:
                cost = daily_data[-1].get('totalCost')
                if cost is not None:
                    daily_cost = float(cost)
        
        # 获取本月费用
        monthly_result = subprocess.run(
            ['ccusage', 'monthly', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        monthly_cost = "N/A"
        if monthly_result.returncode == 0:
            data = json.loads(monthly_result.stdout)
            monthly_data = data.get('monthly', [])
            if monthly_data:
                cost = monthly_data[-1].get('totalCost')
                if cost is not None:
                    monthly_cost = float(cost)
        
        # 格式化显示费用
        daily_formatted = format_cost(daily_cost)
        monthly_formatted = format_cost(monthly_cost)
        
        debug_log(f"费用信息: 今日={daily_formatted}, 本月={monthly_formatted}")
        
        return daily_formatted, monthly_formatted
        
    except Exception as e:
        debug_log(f"获取费用信息时出错: {e}")
        return "N/A", "N/A"

def main():
    """主函数"""
    try:
        # 从stdin读取JSON输入
        input_data = sys.stdin.read()
        debug_log(f"读取到输入数据: {input_data[:100]}...")
        
        if not input_data:
            debug_log("没有输入数据")
            print("[Test] Unified Status Line Working")
            return
        
        data = json.loads(input_data)
        debug_log(f"解析JSON成功")
        
        # 获取模型信息
        model = get_model_name(data)
        debug_log(f"模型名称: {model}")
        
        # 获取会话token进度（蓝色）
        context_tokens = get_session_tokens(data)
        debug_log(f"蓝色进度条: {context_tokens}")
        
        # 获取blocks token比较（橙色）
        blocks_comparison = get_blocks_comparison()
        debug_log(f"橙色进度条: {blocks_comparison}")
        
        # 获取费用信息（黄色）
        daily_cost, monthly_cost = get_cost_info()
        debug_log(f"费用信息: 今日={daily_cost}, 本月={monthly_cost}")
        
        # 获取活跃block时间范围
        time_range = get_active_block_time_range()
        debug_log(f"时间范围: {time_range}")
        
        # 模型名称 - 蓝色
        model_colored = f"\033[0;38;2;91;155;214m{model}\033[0m"
        
        # 费用信息 - 黄色
        cost_info = f"${daily_cost}/{monthly_cost} (d/m)" if daily_cost != "N/A" else "N/A"
        cost_colored = f"\033[0;38;5;178m{cost_info}\033[0m"
        
        # 计算模型名称的显示宽度（用于对齐）
        model_display_width = len(model) + 2  # 模型名称 + 两个空格
        
        # 第一行：模型 + 会话tokens(蓝色) + 费用(黄色)
        first_line = f"{model_colored}  {context_tokens}  {cost_colored}"
        
        # 第二行：用不可见字符对齐 + blocks比较(橙色) + 时间范围（橙色）
        time_colored = f"\033[38;5;208m{time_range}\033[0m"
        # 使用盲文空格字符来对齐（盲文字符宽度为半角，所以需要乘以2）
        padding = "\033[0m" + "⠀" * model_display_width
        second_line = f"{padding}{blocks_comparison}  {time_colored}"
        
        # 输出两行
        print(first_line)
        print(second_line)
        
    except json.JSONDecodeError as e:
        debug_log(f"JSON解析失败: {e}")
        print("[Test] Unified Status Line Working")
    except Exception as e:
        debug_log(f"发生异常: {e}")
        print(f"[Error] Status Line Error: {str(e)}", file=sys.stderr)
        print("[Test] Unified Status Line Working")

if __name__ == "__main__":
    main()