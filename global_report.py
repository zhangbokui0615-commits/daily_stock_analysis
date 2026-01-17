import yfinance as yf
import os
import requests
import sys
import concurrent.futures
import time

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
# 🤖 角色 A: Gemini (QFII 外资视角) - 带自动重试
# -------------------------------------------------------------------
def call_gemini(market_data, news_data, api_key):
    if not api_key: return "⚠️ 未配置 Google Key"
    
    # 轮询策略：Flash 和 Pro 轮着试
    models_to_try = ["models/gemini-1.5-flash", "models/gemini-pro"]
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    你是一位掌管百亿美金的华尔街QFII基金经理。请基于数据撰写备忘录：
    【行情】：{market_data}
    【新闻】：{news_data}
    请输出简报（300字内）：
    1. ⚠️ **全球情报**：投行喊单与地缘风险。
    2. 🌍 **宏观传导**：铜金油波动对【紫金矿业】是利好
