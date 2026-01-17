import yfinance as yf
import os
import requests
import sys
import time
import pandas as pd

# -------------------------------------------------------------------
# 1. 监控名单
# -------------------------------------------------------------------
MARKETS = {
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "PGJ",
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
# 📊 技术指标计算引擎 (保留 V3.0 的量能+KDJ)
# -------------------------------------------------------------------
def calculate_technicals(df):
    if len(df) < 30: return "数据不足"
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    vol = df['Volume']
    
    # --- 1. MA 均线 ---
    ma5 = close.rolling(window=5).mean().iloc[-1]
    ma20 = close.rolling(window=20).mean().iloc[-1]
    ma_trend = "🔴多头" if ma5 > ma20 else "💚空头"
    
    # --- 2. Volume 量能 ---
    vol_ma5 = vol.rolling(window=5).mean().iloc[-1]
    current_vol = vol.iloc[-1]
    vol_ratio = current_vol / vol_ma5 if vol_ma5 > 0 else 1
    
    if vol_ratio > 1.8: vol_msg = "🔥放量"
    elif vol_ratio < 0.6: vol_msg = "❄️缩量"
    else: vol_msg = "平量"

    # --- 3. MACD ---
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    signal = macd.ewm(span=9, adjust=False).mean()
    
    if macd.iloc[-1] > signal.iloc[-1]: macd_msg = "🔴金叉"
    else: macd_msg = "💚死叉"

    # --- 4. KDJ ---
    low_min = low.rolling(window=9).min()
    high_max = high.rolling(window=9).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    df['K'] = rsv.ewm(com=2).mean()
    df['D'] = df['K'].ewm(com=2).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    j_val = df['J'].iloc[-1]
    if j_val > 100: kdj_msg = "⚠️J值超买"
    elif j_val < 0: kdj_msg = "💎J值超跌"
    else: kdj_msg = f"J:{int(j_val)}"

    return f"{ma_trend}|{macd_msg}|{vol_msg}|{kdj_msg}"

# -------------------------------------------------------------------
# 行情快照
# -------------------------------------------------------------------
def get_market_data():
    summary = "" # 纯数据，不带标题，方便塞入 Prompt
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="3mo")
            
            if len(data) < 30:
                summary += f"{name}: 数据不足\n"
                continue
                
            curr = data['Close'].iloc[-1]
            pct = ((curr - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
            
            # 计算技术指标
            tech_info = calculate_technicals(data)
            
            # A股颜色习惯
            pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
            
            summary += f"{name}: {curr:.2f} ({pct_str}) [{tech_info}]\n"
        except: 
            summary += f"{name}: 暂无数据\n"
    return summary

# -------------------------------------------------------------------
# 华尔街宏观雷达
# -------------------------------------------------------------------
def get_breaking_news():
    news_summary = ""
    macro_tickers = ["^DJI", "^TNX", "DX-Y.NYB", "CL=F"] 
    collected_titles = []
    
    for code in macro_tickers:
        try:
            ticker = yf.Ticker(code)
            news_list = ticker.news
            if news_list:
                for item in news_list[:1]: # 只取最新一条
                    title = item.get('title', '')
                    if title and title not in collected_titles:
                        collected_titles.append(title)
                        label = "美债" if "TNX" in code else ("美元" if "DX-Y" in code else "宏观")
                        news_summary += f"• [{label}] {title}\n"
        except: continue
            
    if not collected_titles: news_summary = "暂无重大宏观突发。"
    return news_summary

# -------------------------------------------------------------------
# 🏗️ 构建 Prompt (您的代码)
# -------------------------------------------------------------------
def build_gemini_prompt(market_data, news_data):
    return f"""
你是一名顶级金融分析 AI，需要在同一份报告中，
分别模拟【外资QFII】与【A股游资主力】两种视角。

以下是【客观市场数据】，请严格基于数据分析，不要编造事实。

====================
【全球市场行情与技术结构】
{market_data}

【关联即时情报】
{news_data}
====================

请按以下结构输出，总字数不超过 400 字：

一、【外资 QFII 视角｜全球配置】
- 判断当前全球风险偏好（Risk-On / Risk-Off）
- 大宗商品（铜 / 金 / 原油）对中国资源股的传导
- 对 A 股核心资产的配置态度（加仓 / 观望 / 减仓）
- 语气：理性、克制、偏中期

二、【A股游资视角｜短线博弈】
- 判断当前市场情绪（修复 / 分歧 / 退潮）
- 商品波动是诱多还是趋势
- 明确点评：
  • 紫金矿业（追高 / 低吸 / 回避）
  • 半导体ETF（主升 / 反弹 / 结束）
  • 大盘方向（偏强 / 震荡 / 偏弱）
- 语气：偏交易，但不要低俗

最后给出一句【综合结论】：
“今天更适合 ___（进攻 / 防守 / 观望）型策略。”
"""

# -------------------------------------------------------------------
# 🚀 Gemini 请求函数 (您的代码 - 优化版)
# -------------------------------------------------------------------
def ask_gemini(prompt, api_key):
    if not api_key:
        return "⚠️ 未配置 GEMINI_API_KEY"

    # 使用 1.5-pro 模型，逻辑更强
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-1.5-pro:generateContent"
        f"?key={api_key}"
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    # 重试机制
    for retry in range(3):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif res.status_code == 429:
                # 遇到拥堵，递增等待时间
                time.sleep(6 + retry * 3)
            else:
                print(f"Gemini Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Connection Error: {e}")
            time.sleep(5)

    return "⚠️ Gemini 当前负载较高，建议稍后重试。"

# -------------------------------------------------------------------
# 主程序
# -------------------------------------------------------------------
def main():
    gemini_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    print("📡 1. 获取行情与技术指标...")
    market_data = get_market_data()
    
    print("📰 2. 获取华尔街新闻...")
    news_data = get_breaking_news()
    
    print("🧠 3. Gemini 深度思考中 (QFII vs 游资)...")
    prompt = build_gemini_prompt(market_data, news_data)
    analysis_report = ask_gemini(prompt, gemini_key)

    # 组合最终报告
    final_report = f"""
{market_data}
------------------
{news_data}

{analysis_report}
    """

    # 推送
    try:
        requests.post("http://www.pushplus.plus/send", json={
            "token": push_token,
            "title": "⚖️ A股双核深度复盘 (V4.0)",
            "content": final_report
        })
        print("✅ 推送完成。")
    except Exception as e:
        print(f"❌ 推送失败: {e}")
        
    sys.exit(0)

if __name__ == "__main__":
    main()
