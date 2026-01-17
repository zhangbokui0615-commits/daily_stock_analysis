import yfinance as yf
import os
import requests
import sys
import concurrent.futures
import json

# 1. 监控名单：全球核心 + A股持仓
MARKETS = {
    # --- 外围风向 ---
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "^HXC",
    
    # --- 强周期锚点 ---
    "💰商品-黄金": "GC=F",
    "🔩商品-铜": "HG=F",    
    "⚪️商品-白银": "SI=F",
    "🛢商品-原油": "CL=F",
    
    # --- 情绪指标 ---
    "📉宏观-美债": "^TNX",
    "😱宏观-恐慌": "^VIX",
    
    # --- A股战场 ---
    "🇨🇳A股-上证": "000001.SS",
    "⛰️持仓-紫金": "601899.SS",
    "📱持仓-半导": "512480.SS"
}

# 2. 获取行情
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

# 3. 抓取新闻
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

# 4. 🔥 核心修复：独立且稳健的模型查找函数
def find_working_model(api_key):
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = requests.get(list_url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            # 优先找 Flash，其次 Pro
            for m in models:
                name = m['name']
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'flash' in name: return name
            for m in models:
                name = m['name']
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'pro' in name: return name
            # 实在不行返回第一个
            if models: return models[0]['name']
    except:
        pass
    return "models/gemini-1.5-flash" # 最后的倔强

# -------------------------------------------------------------------
# 🤖 角色 A: Gemini (QFII 外资视角)
# -------------------------------------------------------------------
def call_gemini(market_data, news_data, api_key):
    if not api_key: return "⚠️ 未配置 Google Key"
    
    # 1. 先找到正确的模型名字
    model_name = find_working_model(api_key)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    你是一位掌管百亿美金的华尔街QFII基金经理。请基于数据撰写投资备忘录：
    
    【行情】：{market_data}
    【新闻】：{news_data}
    
    请输出简报（300字内）：
    1. ⚠️ **全球情报**：
       - 高盛/摩根等投行有无最新喊单？地缘政治风险如何？
    2. 🌍 **宏观传导**：
       - 铜金油的波动对全球通胀意味着什么？对【紫金矿业】是利好还是利空？
    3. 🇨🇳 **A股外资态度**：
       - 站在全球配置角度，今天的A股是“便宜的黄金坑”还是“有毒资产”？
       - 结合中概股表现，你会【买入中国】还是【减仓撤退】？
    """
    
    try:
        res = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        
        # 🔥 增加错误检查：如果不是 200，说明出问题了
        if res.status_code != 200:
            return f"🚫 Google 拒绝服务 (代码 {res.status_code}): {res.text[:100]}"
            
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception
