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

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

DEBUG_TOKENS = os.environ.get('DEBUG_TOKENS', '0') == '1'

# 预生成所有可能的进度条状态，避免运行时重复计算
PROGRESS_BARS = {
    i: "▓" * (i // 10) + "░" * (10 - i // 10) for i in range(0, 101)
}

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
    return PROGRESS_BARS.get(percentage, "▒▒▒▒▒▒▒▒▒▒")

def format_tokens(tokens):
    """格式化token数量 - 返回使用百分比和进度条（基于160k限制）"""
    # 基于160k（80% * 200k）计算使用百分比
    used_percentage = min(100, round((tokens * 100) / 160000))
    
    # 调试输出具体数值
    debug_log(f"蓝色进度条计算: tokens={tokens}, 160k限制, 百分比={(tokens * 100) / 160000:.2f}%, 四舍五入={used_percentage}%")
    
    # 直接从缓存中获取进度条，避免函数调用开销
    progress_bar = PROGRESS_BARS.get(used_percentage, "▒▒▒▒▒▒▒▒▒▒")
    
    # 返回蓝色的进度条（会话上下文进度）
    return f"\033[0;34m{progress_bar} {used_percentage}%\033[0m"

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
            return "\033[0;34m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"
        
        # 处理transcript文件
        total_tokens = process_transcript(transcript_path)
        
        if total_tokens > 0:
            formatted_tokens = format_tokens(total_tokens)
            debug_log(f"最终输出: {formatted_tokens}")
            return formatted_tokens
        else:
            debug_log("最终输出: ▒▒▒▒▒▒▒▒▒▒ 0% (未找到有效token数据)")
            return "\033[0;34m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"
            
    except Exception as e:
        debug_log(f"发生错误: {e}")
        return "\033[0;34m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"

def format_cost(cost):
    """格式化费用显示（添加k和m进位）"""
    if cost == "N/A" or not isinstance(cost, (int, float)):
        return "N/A"
    
    # 转换为美分单位（乘以100），便于整数计算和格式化
    cost_cents = int(cost * 100)
    
    # 格式化规则（基于美分）：
    # < 100美分(1美元): 显示美分，如 "50¢"
    # 100-999美分(1-9.99美元): 显示美元，如 "$1.50"
    # >= 1000美分(10美元): 使用k、m进位
    
    if cost_cents < 100:  # 小于1美元
        return f"{cost_cents}¢"
    elif cost_cents < 1000:  # 1-9.99美元
        return f"${cost:.2f}"
    elif cost < 10:  # 10-99.99美元
        return f"${cost:.1f}"
    elif cost < 1000:  # 100-999美元
        return f"${int(cost)}"
    elif cost < 10000:  # 1k-9.9k美元
        k_value = cost / 1000
        return f"${k_value:.1f}k"
    elif cost < 1000000:  # 10k-999k美元
        k_value = cost // 1000
        return f"${k_value}k"
    else:  # >= 1m美元
        if cost < 10000000:
            m_value = cost / 1000000
            return f"${m_value:.1f}m"
        else:
            m_value = cost // 1000000
            return f"${m_value}m"

def get_session_limit_progress():
    """获取会话限额进度（橙色进度条）"""
    # 检查ccusage是否可用
    if not shutil.which('ccusage'):
        return "\033[38;5;208m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"
    
    try:
        # 获取会话限额信息 - 使用20M token限制来获取tokenLimitStatus
        result = subprocess.run(
            ['ccusage', 'blocks', '--token-limit', '20000000', '--active', '-j'],
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
                token_limit_status = block.get('tokenLimitStatus', {})
                
                # 使用当前已使用的token数计算五小时限额使用率
                if 'limit' in token_limit_status:
                    limit = token_limit_status.get('limit', 0)
                    total_tokens = block.get('totalTokens', 0)
                    
                    if limit > 0 and total_tokens > 0:
                        percent_used_raw = (total_tokens * 100) / limit
                        percent_used = min(100, round(percent_used_raw))
                        
                        # 调试输出具体数值
                        debug_log(f"橙色进度条计算(五小时限额): total_tokens={total_tokens}, limit={limit}, 百分比={percent_used_raw:.2f}%, 四舍五入={percent_used}%")
                        progress_bar = PROGRESS_BARS.get(percent_used, "▒▒▒▒▒▒▒▒▒▒")
                        return f"\033[38;5;208m{progress_bar} {percent_used}%\033[0m"
                
                # 备用方案：使用projection数据
                else:
                    total_tokens = block.get('totalTokens', 0)
                    projection = block.get('projection', {})
                    projected_tokens = projection.get('totalTokens', 0)
                    
                    if projected_tokens > 0 and total_tokens > 0:
                        percent_used = min(100, round((total_tokens * 100) / projected_tokens))
                        # 调试输出具体数值
                        debug_log(f"橙色进度条计算(projection): total_tokens={total_tokens}, projected_tokens={projected_tokens}, 百分比={(total_tokens * 100) / projected_tokens:.2f}%, 四舍五入={percent_used}%")
                        progress_bar = PROGRESS_BARS.get(percent_used, "▒▒▒▒▒▒▒▒▒▒")
                        return f"\033[38;5;208m{progress_bar} {percent_used}%\033[0m"
        
        return "\033[38;5;208m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"
        
    except Exception:
        return "\033[38;5;208m▒▒▒▒▒▒▒▒▒▒ 0%\033[0m"

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
        
        # 格式化显示费用
        daily_cost_formatted = format_cost(daily_cost)
        monthly_cost_formatted = format_cost(monthly_cost)
        
        # 输出格式：当日费用 / 当月总费用 [+/-X%]
        return f"{daily_cost_formatted}/{monthly_cost_formatted}{percentage_diff}"
        
    except Exception as e:
        return "N/A/N/A"

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
        debug_log(f"解析JSON成功: {data}")
        
        # 获取各项信息
        model = get_model_name(data)
        debug_log(f"模型名称: {model}")
        
        context_tokens = get_session_tokens(data)  # 蓝色进度条（会话上下文）
        debug_log(f"上下文进度条: {context_tokens}")
        
        limit_tokens = get_session_limit_progress()  # 橙色进度条（会话限额）
        debug_log(f"限额进度条: {limit_tokens}")
        
        cost = get_cost()
        debug_log(f"费用信息: {cost}")
        
        # 使用ANSI颜色代码格式化输出
        # 模型名称 - 蓝色
        model_colored = f"\033[0;38;2;91;155;214m{model}\033[0m"
        # 费用信息 - 黄色
        cost_colored = f"\033[0;38;5;178m{cost}\033[0m"
        
        # 输出格式化的状态行: 模型名字 + 蓝色进度条 + 橙色进度条 + 费用信息
        print(f"{model_colored}  {context_tokens}  {limit_tokens}  {cost_colored}")
        
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