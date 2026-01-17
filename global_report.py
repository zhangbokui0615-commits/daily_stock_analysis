import yfinance as yf
import os
import requests
import sys
import concurrent.futures
import time

# -------------------------------------------------------------------
# 1. 监控名单
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# 行情快照
# -------------------------------------------------------------------
def get_market_data():
    summary = "🌍 【全球行情快照】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="5d")
            
            # 数据不足检查
            if len(data) < 2:
                summary += f"{name}: ⏳ 数据不足\n"
                continue
                
            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            pct = ((curr - prev) / prev) * 100
            
            # 趋势符号
            if pct >= 2: trend = "🚀"
            elif pct > 0: trend = "🔺"
            elif pct <= -2: trend = "🩸"
            else: trend = "🔻"
            
            summary += f"{name}: {curr:.2f} ({pct:+.2f}%) {trend}\n"
        except Exception as e: 
            summary += f"{name}: ⏳ 暂无数据\n"
    return summary

# -------------------------------------------------------------------
# 即时新闻
# -------------------------------------------------------------------
def get_breaking_news():
    news_summary = "📰 【关联即时情报】\n"
    target_tickers = ["^IXIC", "GC=F", "601899.SS"] 
    collected_titles = []
    
    for code in target_tickers:
        try:
            ticker = yf.Ticker(code)
            news_list = ticker.news
            if news_list:
                for item in news_list[:2]:
                    title = item.get('title', '')
                    if title and title not in collected_titles:
                        collected_titles.append(title)
                        news_summary += f"• {title}\n"
        except:
            continue
            
    if not collected_titles:
        news_summary += "• 暂无重大突发新闻。\n"
    return news_summary

# -------------------------------------------------------------------
# 核心：Gemini 通用请求 (补全了您中断的部分)
# -------------------------------------------------------------------
def ask_gemini(prompt, api_key):
    if not api_key: return "⚠️ 未配置 Google Key"
    
    # 轮询两个模型，增加成功率
    models = ["models/gemini-1.5-flash", "models/gemini-pro"]
    headers = {'Content-Type': 'application/json'}
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 429: # 如果拥堵
                time.sleep(5) # 休息5秒
                continue # 换个模型再试
            elif res.status_code == 404:
                continue 
            else:
                # 打印错误但不崩溃，尝试下一个
                print(f"Model {model} error: {res.status_code}")
                continue
        except Exception as e:
            print(f"Connection error: {e}")
            continue
            
    return "⚠️ Gemini 暂时太累了，请稍后自动重试。"

# -------------------------------------------------------------------
# 🎭 角色 A: QFII 外资 (理性派)
# -------------------------------------------------------------------
def role_qfii(market_data, news_data, api_key):
    prompt = f"""
    【角色设定】：你是一位掌管百亿美金的华尔街QFII基金经理，理性、冷静、看重宏观数据。
    【数据】：{market_data}
    【新闻】：{news_data}
    
    请输出《全球宏观备忘录》（300字内）：
    1. ⚠️ **全球情报**：投行喊单与地缘风险。
    2. 🌍 **宏观传导**：铜金油波动对【紫金矿业】估值的影响。
    3. 🇨🇳 **A股态度**：站在全球配置角度，今天是买入中国核心资产的机会，还是撤退？
    """
    return ask_gemini(prompt, api_key)

# -------------------------------------------------------------------
# 🎭 角色 B: A股游资 (激进派) - 由 Gemini 扮演
# -------------------------------------------------------------------
def role_tycoon(market_data, news_data, api_key):
    prompt = f"""
    【角色设定】：你是一位A股实战派游资大佬，犀利、短线、懂情绪、只会说大白话。
    【数据】：{market_data}
    【新闻】：{news_data}
    
    请输出《主力操盘指令》（200字内）：
    1. 🕵️ **主力意图**：大宗商品的波动，是主力的诱多陷阱还是真突破？
    2. ⚡️ **个股指令**：
       - 【紫金矿业】：当前位置追高、低吸还是止盈？
       - 【半导体ETF】：是主升浪还是反弹结束？
       - 【大盘】：看涨还是看跌？
    """
    return ask_gemini(prompt, api_key)

# -------------------------------------------------------------------
# 主程序
# -------------------------------------------------------------------
def main():
    gemini_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    print("📡 扫描行情...")
    market_data = get_market_data()
    news_data = get_breaking_news()
    
    print("🧠 Gemini 正在左右互搏 (影分身模式)...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 同时启动两个任务，都用 Gemini Key，但是 Prompt 不同
        future_qfii = executor.submit(role_qfii, market_data, news_data, gemini_key)
        
        # 稍微错开一点时间，防止瞬间并发太高
        time.sleep(2) 
        
        future_tycoon = executor.submit(role_tycoon, market_data, news_data, gemini_key)
        
        report_qfii = future_qfii.result()
        report_tycoon = future_tycoon.result()

    final_report = f"""
{market_data}

{news_data}

🤖 **【QFII外资视角】Google Gemini**
{report_qfii}

🐲 **【游资主力视角】Gemini (分身)**
{report_tycoon}
    """

    # 推送逻辑
    try:
        requests.post("http://www.pushplus.plus/send", json={
            "token": push_token,
            "title": "⚖️ A股多空辩论 (Gemini独奏版)",
            "content": final_report
        })
        print("推送完成。")
    except Exception as e:
        print(f"推送失败: {e}")
        
    sys.exit(0)

if __name__ == "__main__":
    main()
