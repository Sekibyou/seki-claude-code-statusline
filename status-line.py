#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code StatusLine - 统一版本
实时显示模型信息、token使用情况和费用统计
所有功能集成在一个脚本中，避免多层subprocess调用
"""

import sys
import json
import subprocess
import os
import io
import shutil
from pathlib import Path
from datetime import datetime
import calendar
import pytz
import time

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 临时调试函数（稍后会重新定义）
def debug_log(message):
    pass

# 加载.env配置
def load_env_config():
    """加载.env配置文件"""
    config = {}
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            debug_log(f"读取.env文件时出错: {e}")
    return config

# 加载配置
ENV_CONFIG = load_env_config()

def get_system_timezone():
    """获取系统时区"""
    try:
        # 方法1: 使用datetime获取本地时区偏移（最可靠的方法）
        local_time = datetime.now()
        utc_time = datetime.utcnow()
        offset = local_time - utc_time
        offset_hours = offset.total_seconds() / 3600
        
        debug_log(f"系统时区偏移: UTC{offset_hours:+.1f}小时")
        
        # 根据偏移量推测常见时区
        timezone_map = {
            8.0: 'Asia/Shanghai',         # UTC+8 中国/新加坡
            9.0: 'Asia/Tokyo',            # UTC+9 日本/韩国
            -5.0: 'America/New_York',     # UTC-5 美东
            -8.0: 'America/Los_Angeles',  # UTC-8 美西  
            0.0: 'UTC',                   # UTC+0 格林威治
            1.0: 'Europe/London',         # UTC+1 英国夏时制
            -6.0: 'America/Chicago',      # UTC-6 美中
        }
        
        # 查找最接近的时区
        best_match = None
        min_diff = float('inf')
        
        for offset_key, timezone_name in timezone_map.items():
            diff = abs(offset_hours - offset_key)
            if diff < min_diff and diff < 0.5:  # 允许30分钟的误差
                min_diff = diff
                best_match = timezone_name
        
        if best_match:
            debug_log(f"自动检测时区: {best_match}")
            return best_match
        
        # 方法2: 尝试Windows特定的时区检测
        try:
            import subprocess
            result = subprocess.run(['tzutil', '/g'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                win_tz = result.stdout.strip()
                debug_log(f"Windows时区: {win_tz}")
                
                # Windows时区到IANA时区的映射
                win_tz_map = {
                    'China Standard Time': 'Asia/Shanghai',
                    'Tokyo Standard Time': 'Asia/Tokyo', 
                    'Korea Standard Time': 'Asia/Seoul',
                    'Eastern Standard Time': 'America/New_York',
                    'Pacific Standard Time': 'America/Los_Angeles',
                    'UTC': 'UTC',
                }
                
                if win_tz in win_tz_map:
                    debug_log(f"映射到IANA时区: {win_tz_map[win_tz]}")
                    return win_tz_map[win_tz]
        except:
            pass
            
    except Exception as e:
        debug_log(f"获取系统时区失败: {e}")
    
    # 默认返回UTC
    debug_log("使用默认时区: UTC")
    return 'UTC'

# 配置项
DEBUG_TOKENS = ENV_CONFIG.get('DEBUG_TOKENS', '0') == '1'
SUBSCRIPTION_TYPE = ENV_CONFIG.get('SUBSCRIPTION_TYPE', '').lower()
TIMEZONE = ENV_CONFIG.get('TIMEZONE', '').strip() or get_system_timezone()

# 会员限额映射
SUBSCRIPTION_LIMITS = {
    'pro': 20000000,      # 20M
    'max5x': 100000000,   # 100M  
    'max20x': 400000000,  # 400M
}

# 判断是否为会员模式
IS_SUBSCRIPTION_MODE = SUBSCRIPTION_TYPE in SUBSCRIPTION_LIMITS

# 预生成所有可能的进度条状态，避免运行时重复计算
# 使用6级点阵字符实现精细渐变：0个点到6个点表示不同进度（最多三行点）
# 100%映射到60个点（10个字符 × 6个点/字符）
DOT_CHARS = ['⠀', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿']  # 0-6个点（最多三行）
PROGRESS_BARS = {}

# 生成精细进度条缓存
for percentage in range(0, 101):
    total_dots = int((percentage * 60) / 100)  # 总共60个点
    full_chars = total_dots // 6  # 完整字符数（6个点）
    remaining_dots = total_dots % 6  # 剩余点数
    
    # 构建进度条 - 纯彩色点阵
    progress = DOT_CHARS[6] * full_chars  # 满点字符（⠿）
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

def generate_progress_bar(used_percentage):
    """生成进度条 - 使用预生成的缓存提升性能"""
    # 限制百分比范围并使用预生成的进度条
    percentage = min(100, max(0, used_percentage))
    return PROGRESS_BARS.get(percentage, "\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m")

def format_tokens(tokens):
    """格式化token数量 - 返回使用百分比和进度条（基于200k限制）"""
    # 基于200k计算使用百分比
    used_percentage = min(100, round((tokens * 100) / 200000))
    
    # 调试输出具体数值
    debug_log(f"蓝色进度条计算: tokens={tokens}, 200k限制, 百分比={(tokens * 100) / 200000:.2f}%, 四舍五入={used_percentage}%")
    
    # 直接从缓存中获取进度条，避免函数调用开销
    progress_bar = PROGRESS_BARS.get(used_percentage, "\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m")
    
    # 返回蓝色的进度条（会话上下文进度）
    return f"\033[0;34m{progress_bar}\033[0m \033[0;34m{used_percentage}%\033[0m"

def process_transcript(transcript_path):
    """处理transcript文件，提取token使用量"""
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 从后往前查找最后一个有效的assistant消息
        for line in reversed(lines):
            try:
                data = json.loads(line.strip())
                
                # 检查是否是assistant消息且包含usage信息
                if (data.get('type') == 'assistant' and 
                    'message' in data and 
                    'usage' in data['message']):
                    
                    usage = data['message']['usage']
                    
                    # 检查是否有所需的所有字段
                    if all(key in usage for key in ['input_tokens', 'cache_creation_input_tokens', 
                                                     'cache_read_input_tokens', 'output_tokens']):
                        # 计算总token数
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
    """获取token使用情况"""
    try:
        # 提取transcript_path
        transcript_path = data.get('transcript_path', '')
        debug_log(f"提取的transcript_path: {transcript_path}")
        
        if not transcript_path:
            debug_log("错误: transcript_path为空")
            return "\033[0;34m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;34m0%\033[0m"
        
        # 处理transcript文件
        total_tokens = process_transcript(transcript_path)
        
        if total_tokens > 0:
            formatted_tokens = format_tokens(total_tokens)
            debug_log(f"最终输出: {formatted_tokens}")
            return formatted_tokens
        else:
            debug_log("最终输出: \033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m 0% (未找到有效token数据)")
            return "\033[0;34m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;34m0%\033[0m"
            
    except Exception as e:
        debug_log(f"发生错误: {e}")
        return "\033[0;34m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[0;34m0%\033[0m"

def format_cost(cost, with_dollar_sign=True):
    """格式化费用显示（统一显示一位小数）"""
    if cost == "N/A" or not isinstance(cost, (int, float)):
        return "N/A"
    
    # 统一格式：一位小数
    if cost < 1000:  # 小于1000美元
        formatted = f"{cost:.1f}"
    elif cost < 1000000:  # 1k-999k美元
        k_value = cost / 1000
        formatted = f"{k_value:.1f}k"
    else:  # >= 1m美元
        m_value = cost / 1000000
        formatted = f"{m_value:.1f}m"
    
    # 根据参数决定是否添加美元符号
    if with_dollar_sign:
        return f"${formatted}"
    else:
        return formatted

def get_city_name_from_timezone(timezone_name):
    """从时区名称获取城市名称"""
    city_mapping = {
        'Asia/Shanghai': 'Shanghai',
        'Asia/Tokyo': 'Tokyo', 
        'Asia/Seoul': 'Seoul',
        'America/New_York': 'NYC',
        'America/Los_Angeles': 'LA',
        'America/Chicago': 'Chicago',
        'Europe/London': 'London',
        'UTC': 'UTC',
    }
    
    # 如果有直接映射就使用
    if timezone_name in city_mapping:
        return city_mapping[timezone_name]
    
    # 否则从时区名称中提取城市名（如 Asia/Bangkok -> Bangkok）
    try:
        if '/' in timezone_name:
            return timezone_name.split('/')[-1]
        return timezone_name
    except:
        return 'Local'

def format_session_time(start_time, end_time, timezone_name):
    """格式化会话时间段显示（如 Tokyo 15:00~20:00）"""
    try:
        # 解析ISO时间
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # 转换到指定时区
        target_tz = pytz.timezone(timezone_name)
        start_local = start_dt.astimezone(target_tz)
        end_local = end_dt.astimezone(target_tz)
        
        # 格式化为 15:00~20:00 格式（24小时制）
        start_str = start_local.strftime('%H:%M')
        end_str = end_local.strftime('%H:%M')
        
        # 获取城市名称
        city_name = get_city_name_from_timezone(timezone_name)
        
        return f"{city_name} {start_str}~{end_str}"
        
    except Exception as e:
        debug_log(f"格式化时间出错: {e}")
        return "N/A"

def get_subscription_info():
    """获取会员模式的限额进度和时间信息"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m0%\033[0m", "\033[38;5;208mN/A\033[0m"
    
    try:
        # 获取用户配置的限额
        user_limit = SUBSCRIPTION_LIMITS.get(SUBSCRIPTION_TYPE, 100000000)
        
        # 使用配置的限额获取tokenLimitStatus
        result = subprocess.run(
            ['ccusage', 'blocks', '--token-limit', str(user_limit), '--active', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            blocks = data.get('blocks', [])
            
            if blocks and blocks[0].get('isActive'):
                block = blocks[0]
                
                # 获取进度百分比
                progress_info = ""
                token_limit_status = block.get('tokenLimitStatus', {})
                if 'percentUsed' in token_limit_status:
                    percent_used_raw = token_limit_status.get('percentUsed', 0)
                    percent_used = min(100, round(percent_used_raw))
                    
                    debug_log(f"会员模式进度条: 限额={user_limit}, 使用率={percent_used_raw:.2f}%, 四舍五入={percent_used}%")
                    progress_bar = PROGRESS_BARS.get(percent_used, "\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m")
                    progress_info = f"\033[38;5;208m{progress_bar}\033[0m \033[38;5;208m{percent_used}%\033[0m"
                else:
                    progress_info = "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m0%\033[0m"
                
                # 获取时间段信息
                start_time = block.get('startTime', '')
                end_time = block.get('endTime', '')
                time_info = ""
                
                if start_time and end_time:
                    formatted_time = format_session_time(start_time, end_time, TIMEZONE)
                    time_info = f"\033[38;5;208m{formatted_time}\033[0m"
                else:
                    time_info = "\033[38;5;208mN/A\033[0m"
                
                return progress_info, time_info
        
        # 默认返回值
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m0%\033[0m", "\033[38;5;208mN/A\033[0m"
        
    except Exception as e:
        debug_log(f"获取会员信息时出错: {e}")
        return "\033[38;5;208m\033[38;5;240m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\033[0m\033[0m \033[38;5;208m0%\033[0m", "\033[38;5;208mN/A\033[0m"

def get_ccusage_data():
    """获取ccusage的费用数据"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        debug_log("ccusage命令不可用")
        return None, None, []
    
    try:
        # 获取过去30天的日常费用数据
        from datetime import datetime, timedelta
        
        # 计算30天前的日期
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        result = subprocess.run(
            ['ccusage', 'daily', '--since', thirty_days_ago, '-j'],
            capture_output=True,
            text=True,
            timeout=10,  # 增加超时时间，因为可能有更多数据
            encoding='utf-8',
            shell=True
        )
        
        daily_data = []
        daily_cost = None
        
        debug_log(f"ccusage daily 返回码: {result.returncode}")
        debug_log(f"ccusage daily 输出: {result.stdout[:200]}...")
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            daily_data = data.get('daily', [])
            debug_log(f"获取到 {len(daily_data)} 天的数据")
            
            if daily_data:
                daily_cost = daily_data[-1].get('totalCost')
                debug_log(f"今日费用原始值: {daily_cost}")
                if daily_cost is not None:
                    daily_cost = float(daily_cost)  # 保持浮点数精度
                    debug_log(f"今日费用转换后: {daily_cost}")
        
        # 获取当月总费用
        monthly_result = subprocess.run(
            ['ccusage', 'monthly', '-j'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            shell=True
        )
        
        monthly_cost = None
        debug_log(f"ccusage monthly 返回码: {monthly_result.returncode}")
        
        if monthly_result.returncode == 0:
            data = json.loads(monthly_result.stdout)
            monthly_data = data.get('monthly', [])
            debug_log(f"月度数据: {monthly_data}")
            
            if monthly_data:
                monthly_cost = monthly_data[-1].get('totalCost')
                debug_log(f"本月费用原始值: {monthly_cost}")
                if monthly_cost is not None:
                    monthly_cost = float(monthly_cost)  # 保持浮点数精度
                    debug_log(f"本月费用转换后: {monthly_cost}")
        
        debug_log(f"最终返回: daily_cost={daily_cost}, monthly_cost={monthly_cost}, daily_data长度={len(daily_data)}")
        return daily_cost, monthly_cost, daily_data
            
    except Exception as e:
        debug_log(f"获取ccusage数据时出错: {e}")
        return None, None, []

def calculate_percentage_diff(daily_cost, daily_data):
    """计算相对于历史平均的百分比差异"""
    if daily_cost is None or not daily_data or len(daily_data) < 2:
        return ""
    
    try:
        # 排除今天，计算过去几天的平均值
        past_days_data = daily_data[:-1]  # 排除最后一天（今天）
        
        if past_days_data:
            # 计算过去几天的平均费用
            past_total = sum(day.get('totalCost', 0) for day in past_days_data)
            past_days_count = len(past_days_data)
            average_cost = past_total / past_days_count
            
            # 计算百分比差异
            if average_cost > 0:
                diff = daily_cost - average_cost
                percentage = int(round((diff / average_cost) * 100))
                
                # 只有差异大于1%才显示
                if abs(percentage) > 1:
                    if percentage > 0:
                        # 高于平均值，绿色
                        return f"(\033[0;32m+{percentage}%\033[0m)"
                    else:
                        # 低于平均值，红色
                        return f"(\033[0;31m{percentage}%\033[0m)"
    except Exception:
        pass
    
    return ""

def get_cost():
    """获取费用信息"""
    try:
        # 获取费用数据
        daily_cost, monthly_cost, daily_data = get_ccusage_data()
        
        if daily_cost is None:
            daily_cost = "N/A"
        if monthly_cost is None:
            monthly_cost = "N/A"
        
        # 计算百分比差异
        percentage_diff = ""
        if daily_cost != "N/A":
            percentage_diff = calculate_percentage_diff(daily_cost, daily_data)
        
        # 格式化显示费用 - 只有第一个有美元符号
        daily_cost_formatted = format_cost(daily_cost, with_dollar_sign=True)
        monthly_cost_formatted = format_cost(monthly_cost, with_dollar_sign=False)
        
        # 输出格式：$当日费用/当月总费用 [+/-X%]
        return f"{daily_cost_formatted}/{monthly_cost_formatted}{percentage_diff}"
        
    except Exception as e:
        return "N/A/N/A"

def main():
    """主函数"""
    try:
        # 从stdin读取JSON输入
        input_data = sys.stdin.read()
        debug_log(f"读取到输入数据: {input_data[:100]}...")
        debug_log(f"配置模式: 会员模式={IS_SUBSCRIPTION_MODE}, 会员类型={SUBSCRIPTION_TYPE}, 时区={TIMEZONE}")
        
        if not input_data:
            debug_log("没有输入数据")
            print("[Test] Unified Status Line Working")
            return
        
        data = json.loads(input_data)
        debug_log(f"解析JSON成功: {data}")
        
        # 获取模型信息
        model = get_model_name(data)
        debug_log(f"模型名称: {model}")
        
        # 获取会话token进度（蓝色，两种模式都显示）
        context_tokens = get_session_tokens(data)
        debug_log(f"上下文进度条: {context_tokens}")
        
        # 模型名称 - 蓝色
        model_colored = f"\033[0;38;2;91;155;214m{model}\033[0m"
        
        if IS_SUBSCRIPTION_MODE:
            # 会员模式: 模型 + 会话tokens(蓝色) + 橙色进度条 + 时间段
            limit_progress, session_time = get_subscription_info()
            debug_log(f"会员模式 - 限额进度条: {limit_progress}")
            debug_log(f"会员模式 - 会话时间: {session_time}")
            
            print(f"{model_colored}  {context_tokens}  {limit_progress}  {session_time}")
        else:
            # 非会员模式: 模型 + 会话tokens(蓝色) + 费用分析(黄色)
            cost = get_cost()
            debug_log(f"非会员模式 - 费用信息: {cost}")
            
            # 费用信息 - 黄色
            cost_colored = f"\033[0;38;5;178m{cost}\033[0m"
            print(f"{model_colored}  {context_tokens}  {cost_colored}")
        
    except json.JSONDecodeError as e:
        # JSON解析失败时的默认输出
        debug_log(f"JSON解析失败: {e}")
        print("[Test] Unified Status Line Working")
    except Exception as e:
        # 其他错误时的默认输出
        debug_log(f"发生异常: {e}")
        print(f"[Error] Status Line Error: {str(e)}", file=sys.stderr)
        print("[Test] Unified Status Line Working")

if __name__ == "__main__":
    main()