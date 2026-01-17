import yfinance as yf
import os
import requests
import sys
import concurrent.futures
import time # 引入时间库，用于休息

# 1. 监控名单
MARKETS = {
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "^HXC",
    "💰商品-黄金": "GC=F",
    "🔩商品-铜": "HG=F",    
    "⚪️商品-白银": "SI=F",
    "🛢商品-原油": "CL=F",
    "📉宏观-美债": "^TNX",
    "😱宏观-恐慌": "^VIX",
    "🇨🇳A股-上证": "000001.SS",
    "⛰️持仓-紫金": "601899.SS",
    "📱持仓-半导": "512480.SS"
}

def get_market_data():
    summary = "🌍 【全球行情快照】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="5d")
            if len(data) >= 2:
                curr = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                trend = "🔴" if pct > 2 else ("🔺" if pct > 0 else ("🔻" if pct > -2 else "💚"))
                summary += f"{name}: {curr:.2f} ({pct:+.2f}%) {trend}\n"
        except: 
            summary += f"{name}: ⏳ 暂无数据\n"
    return summary

def get_breaking_news():
    news_summary = "📰 【关联即时情报】\n"
    target_tickers = ["^IXIC", "GC=F", "601899.SS"] 
    collected_titles = []
    try:
        for code in target_tickers:
            ticker = yf.Ticker(code)
            news_list = ticker.news
            if news_list:
                for item in news_list[:2]:
                    title = item.get('title', '')
                    if title and title not in collected_titles:
                        collected_titles.append(title)
                        news_summary += f"• {title}\n"
    except:
        news_summary += "• (接口繁忙，以AI内部知识为准)\n"
    if not collected_titles:
        news_summary += "• 暂无重大突发新闻。\n"
    return news_summary

# -------------------------------------------------------------------
# 🤖 角色 A: Gemini (QFII 外资视角) - 增加重试机制
# -------------------------------------------------------------------
def call_gemini(market_data, news_data, api_key):
    if not api_key: return "⚠️ 未配置 Google Key"
    
    # 直接指定最常用的模型，节省一次“问路”请求
    models_to_try = ["models/gemini-1.5-flash", "models/gemini-pro"]
    
    headers = {'Content-Type': 'application/json'}
    prompt = f"""
    你是一位掌管百亿美金的华尔街QFII基金经理。请基于数据撰写备忘录：
    【行情】：{market_data}
    【新闻】：{news_data}
    请输出简报（300字内）：
    1. ⚠️ **全球情报**：投行喊单与地缘风险。
    2. 🌍 **宏观传导**：铜金油波动对【紫金矿业】是利好还是利空？
    3. 🇨🇳 **A股态度**：今天是“黄金坑”还是“接盘侠”？结合中概股，你会【买入中国】还是【撤退】？
    """
    
    # 🔄 自动重试循环
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        try:
            # 尝试发送请求
            res = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            
            # ✅ 成功：直接返回结果
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            
            # 🚦 遇到 429 (太快了)：休息 5 秒再试
            elif res.status_code == 429:
                time.sleep(5) 
                continue # 换下一个模型或者重试
                
            # 🚫 遇到 404 (找不到)：换下一个模型试
            elif res.status_code == 404:
                continue 
                
            # 其他错误
            else:
                return f"Google 拒绝 (代码 {res.status_code}): {res.text[:100]}"
                
        except Exception as e:
            continue # 网络错误也重试
            
    return "⚠️ Gemini 暂时拥堵，请稍后自动重试。"

# -------------------------------------------------------------------
# 🐲 角色 B: DeepSeek (A股 游资视角)
# -------------------------------------------------------------------
def call_deepseek(market_data, news_data, api_key):
    if not api_key: return "⚠️ (提示：请配置 DEEPSEEK_API_KEY 以解锁内资视角)"
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    prompt = f"""
    你是A股游资大佬。
    【行情】：{market_data}
    【消息】：{news_data}
    请给出指令（200字内）：
    1. 🕵️ **主力
