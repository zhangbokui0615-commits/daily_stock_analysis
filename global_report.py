import akshare as ak
import yfinance as yf
import os
import requests
import sys
import time
import pandas as pd
from datetime import datetime
import pytz
import io

# 强制 UTF-8 环境
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ==========================================
# ⚙️ 配置区 (涵盖美/日/中/商品/有色/持仓)
# ==========================================
MARKETS = {
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "PGJ",
    "💰商品-黄金": "GC=F",
    "🔩商品-铜": "HG=F",    
    "🛢商品-原油": "CL=F",
    "📉宏观-美债": "^TNX",
    "💵美元-汇率": "DX-Y.NYB",
    "🇨🇳A股-上证": "000001", 
    "⛰️持仓-紫金": "601899",
    "📱持仓-半导": "512480"
}

# ==========================================
# 1. 智能数据引擎 (针对 ETF 专项优化)
# ==========================================
def fetch_data(symbol, retries=3):
    for i in range(retries):
        try:
            if symbol.isdigit():  # A股逻辑
                if symbol == "000001":
                    df = ak.stock_zh_index_daily(symbol="sh000001")
                elif symbol.startswith(('5', '1')): # 💡 修复：针对 ETF 使用东财接口
                    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                
                df.columns = [c.capitalize() for c in df.columns]
                df.rename(columns={'日期':'Date','date':'Date','收盘':'Close','开盘':'Open','最高':'High','最低':'Low','成交量':'Volume'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df.tail(60)
            else:  # 全球逻辑
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="6mo", interval="1d", auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if not df.empty: return df
        except Exception as e:
            print(f"抓取 {symbol} 失败，第 {i+1} 次尝试...")
            time.sleep(3)
    return None

# ==========================================
# 2. 技术指标引擎 (枢轴点 + KDJ)
# ==========================================
def calculate_technicals(df):
    if df is None or len(df) < 20: return "数据不足"
    close, high, low = df['Close'], df['High'], df['Low']
    
    # 均线趋势
    ma5, ma20 = close.rolling(5).mean().iloc[-1], close.rolling(20).mean().iloc[-1]
    trend = "🔴多头" if ma5 > ma20 else "🟢偏弱"
    
    # 枢轴点计算
    last = df.iloc[-1]
    p = (last['High'] + last['Low'] + last['Close']) / 3
    s1, r1 = 2 * p - last['Low'], 2 * p - last['High']
    
    # KDJ 计算
    l9, h9 = low.rolling(9).min(), high.rolling(9).max()
    rsv = (close - l9) / (h9 - l9).replace(0, 0.001) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    j_val = (3 * k - 2 * d).iloc[-1]
    kdj_msg = f"J:{int(j_val)}"
    if j_val > 100: kdj_msg = "⚠️超买"
    elif j_val < 0: kdj_msg = "💎超跌"

    return f"{trend} | S1:{s1:.2f} R1:{r1:.2f} | {kdj_msg}"

# ==========================================
# 3. Gemini 智能决策 (含重试逻辑)
# ==========================================
def ask_gemini(prompt, api_key):
    if not api_key: return "未配置 API KEY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    for _ in range(3):
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
            time.sleep(10) # 拥堵时等待
        except: continue
    return "AI 思考中断，建议手动对照数据。"

# ==========================================
# 4. 主程序流程
# ==========================================
def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    sh_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(sh_tz).strftime('%Y-%m-%d %H:%M')

    report_data = ""
    for name, code in MARKETS.items():
        df = fetch_data(code)
        if df is not None:
            curr = df['Close'].iloc[-1]
            pct = (curr - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
            report_data += f"{name}: {curr:.2f} ({pct:+.2f}%) [{calculate_technicals(df)}]\n"
        else:
            report_data += f"{name}: 抓取失败\n"

    prompt = f"""
    时间：{now}。你是一名华尔街操盘手，基于以下行情数据：
    {report_data}
    请从【外资配置】与【游资短线】两个视角分析：
    1. 美元指数走强对紫金矿业的压制深度。
    2. 美债利率波动对半导体 ETF 的影响。
    3. 给出今日明确的防守价位与操作建议（400字内）。
    """
    
    analysis = ask_gemini(prompt, api_key)
    final_content = f"【全景数据】\n{report_data}\n\n【实战推演】\n{analysis}"

    if push_token:
        requests.post("http://www.pushplus.plus/send", json={
            "token": push_token,
            "title": f"⚖️ 全球宏观双核复盘 ({now})",
            "content": final_content.replace("\n", "<br>")
        })
    print("分析推送任务完成。")
    sys.exit(0)

if __name__ == "__main__":
    main()
