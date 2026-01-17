import yfinance as yf
import os
import requests
import sys
import concurrent.futures

# 1. 监控名单：核心资产 + 宏观指标
MARKETS = {
    # --- 全球核心 ---
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "^HXC",
    
    # --- 强周期商品 ---
    "💰商品-黄金": "GC=F",
    "🔩商品-铜": "HG=F",    # 紫金的核心锚点
    "⚪️商品-白银": "SI=F",
    "🛢商品-原油": "CL=F",
    
    # --- 风险指标 ---
    "📉宏观-美债": "^TNX",
    "😱宏观-恐慌": "^VIX",
    
    # --- A股持仓 ---
    "🇨🇳A股-上证": "000001.SS",
    "⛰️持仓-紫金": "601899.SS",
    "📱持仓-半导": "512480.SS"
}

# 2. 获取行情数据
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

# 3. 获取突发新闻标题 (利用 yfinance 免费源)
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
        news_summary += "• (新闻接口繁忙，以AI内部知识为准)\n"
        
    if not collected_titles:
        news_summary += "• 暂无重大突发新闻，市场相对平静。\n"
        
    return news_summary

# -------------------------------------------------------------------
# 🤖 角色 A: Google Gemini (华尔街情报 & 外资观点)
# -------------------------------------------------------------------
def call_gemini(market_data, news_data, api_key):
    if not api_key: return "⚠️ 未配置 Google Key。"
    
    model_name = "models/gemini-1.5-flash"
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(list_url, timeout=5).json()
        for m in resp.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                if 'flash' in m['name'] or 'pro' in m['name']:
                    model_name = m['name']
                    break
    except: pass

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # 🔥 核心升级：增加第3点“A股外资观点”
    prompt = f"""
    你是一位掌管百亿美金的华尔街QFII基金经理。请结合【最新行情】和【新闻】输出投资备忘录：
    
    【行情】：
    {market_data}
    【新闻】：
    {news_data}
    
    请输出简报（分点，字数300字以内）：
    1. ⚠️ **全球情报与投行观点**：
       - 高盛/摩根等大行最近有什么喊单？有无地缘政治黑天鹅？
    2. 🌍 **宏观传导逻辑**：
       - 铜金油的波动对全球通胀意味着什么？对【紫金矿业】是利好还是利空？
    3. 🇨🇳 **A股外资观点 (重点)**：
       - 站在全球资产配置的角度，现在的A股是“便宜的黄金坑”还是“有毒资产”？
       - 结合中概股(金龙指数)表现，你今天会**买入中国资产**还是**卖出**？
    """
    try:
        res = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"Gemini 连线中断: {str(e)}"

# -------------------------------------------------------------------
# 🐲 角色 B: DeepSeek (A股本土游资)
# -------------------------------------------------------------------
def call_deepseek(market_data, news_data, api_key):
    if not api_key: return "⚠️ (请配置 DEEPSEEK_API_KEY 以解锁)"
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    prompt = f"""
    你是A股游资大佬，擅长短线博弈和资金流分析。
    
    【行情】：{market_data}
    【消息】：{news_data}
    
    请给出犀利的操盘指令（200字以内）：
    1. 🕵️ **内资主力动向**：
       - 主力会利用外围的消息（如金属大涨）进行诱多出货还是真突破？
    2. ⚡️ **个股实操指令**：
       - 【紫金矿业】：当前位置是追高、低吸还是止盈？
       - 【半导体ETF】：是主升浪还是反弹结束？
       - 【A股大盘】：今天是看涨还是看跌？
    """
    try:
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except Exception as e: return f"DeepSeek 思考中断: {str(e)}"

# -------------------------------------------------------------------
# 主程序
# -------------------------------------------------------------------
def main():
    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    print("📡 正在扫描全球行情...")
    market_data = get_market_data()
    
    print("📰 正在抓取头条新闻...")
    news_data = get_breaking_news()
    
    print("🧠 AI 双核正在辩论 A 股走势...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_gemini = executor.submit(call_gemini, market_data, news_data, gemini_key)
        future_deepseek = executor.submit(call_deepseek, market_data, news_data, deepseek_key)
        
        report_gemini = future_gemini.result()
        report_deepseek = future_deepseek.result()

    final_report = f"""
{market_data}

{news_data}

🤖 **【QFII外资视角】Google Gemini**
{report_gemini}

🐲 **【游资主力视角】DeepSeek**
{report_deepseek}
    """

    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "⚖️ A股多空辩论 (外资 vs 游资)",
        "content": final_report
    })
    print("多空报告推送完成。")
    sys.exit(0)

if __name__ == "__main__":
    main()
