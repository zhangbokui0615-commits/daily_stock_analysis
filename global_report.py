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

# 强制系统输出为 UTF-8，防止 GitHub Actions 日志乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ==========================================
# ⚙️ 配置区 (已涵盖美、日、中、大宗、有色)
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
    # --- A股使用 6 位数字代码 ---
    "🇨🇳A股-上证": "000001", 
    "⛰️持仓-紫金": "601899",
    "📱持仓-半导": "512480"
}

# ==========================================
# 1. 数据引擎 (增加格式归一化)
# ==========================================
def fetch_data(symbol, retries=3):
    for i in range(retries):
        try:
            if symbol.isdigit():  # A股通道
                if symbol == "000001":
                    df = ak.stock_zh_index_daily(symbol="sh000001")
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                # 统一列名为大写
                df.columns = [c.capitalize() for c in df.columns]
                df.rename(columns={'日期': 'Date', '收盘': 'Close', '开盘': 'Open', '最高': 'High', '最低': 'Low', '成交量': 'Volume'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df.tail(60)
            else:  # 全球通道
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="6mo", interval="1d", auto_adjust=True)
                # 处理 yfinance 的 MultiIndex 问题
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if not df.empty: return df
        except Exception as e:
            print(f"抓取 {symbol} 异常: {e}")
            time.sleep(3)
    return None

# ==========================================
# 2. 技术指标 (增加零波动保护)
# ==========================================
def calculate_technicals(df):
    if df is None or len(df) < 30: return "数据不足"
    close = df['Close']
    
    # MA 均线
    ma5 = close.rolling(5).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    trend = "🔴多头" if ma5 > ma20 else "🟢偏弱"
    
    # 枢轴点 (S2/S1/R1/R2)
    last = df.iloc[-1]
    p = (last['High'] + last['Low'] + last['Close']) / 3
    s1, r1 = 2 * p - last['Low'], 2 * p - last['High']
    s2, r2 = p - (last['High'] - last['Low']), p + (last['High'] - last['Low'])
    
    # KDJ
    low_9 = df['Low'].rolling(9).min()
    high_9 = df['High'].rolling(9).max()
    diff = (high_9 - low_9).replace(0, 0.001)
    rsv = (close - low_9) / diff * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    j_val = (3 * k - 2 * d).iloc[-1]
    kdj_msg = "⚠️超买" if j_val > 100 else ("💎超跌" if j_val < 0 else f"J:{int(j_val)}")

    return f"{trend} | S1:{s1:.2f} R1:{r1:.2f} | {kdj_msg}"

# ==========================================
# 3. Gemini 1.5 Pro 请求
# ==========================================
def ask_gemini(prompt, api_key):
    if not api_key: return "⚠️ 未配置 API_KEY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for _ in range(3):
        try:
            res = requests.post(url, json=payload, timeout=40)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Gemini API 错误: {res.status_code} - {res.text}")
            time.sleep(5)
        except: continue
    return "AI 推演失败。"

# ==========================================
# 4. 主程序
# ==========================================
def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    sh_tz = pytz.timezone('Asia/Shanghai')
    now_str = datetime.now(sh_tz).strftime('%Y-%m-%d %H:%M')

    report_data = ""
    for name, code in MARKETS.items():
        df = fetch_data(code)
        if df is not None:
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            pct = (curr - prev) / prev * 100
            report_data += f"{name}: {curr:.2f} ({pct:+.2f}%) [{calculate_technicals(df)}]\n"
        else:
            report_data += f"{name}: 数据获取失败\n"

    # 宏观深度 Prompt
    prompt = f"""
    时间：{now_str}。作为全球对冲基金经理，基于数据：
    {report_data}
    请深入分析：1.美债利率/美元对科技股及半导体ETF的估值压制。2.有色期货对紫金矿业的盈利传导。3.明确给出今日持仓建议与防守位（400字内）。
    """
    
    analysis = ask_gemini(prompt, api_key)
    final_content = f"【全景数据】\n{report_data}\n\n【实战推演】\n{analysis}"

    # 推送至微信
    if push_token:
        requests.post("http://www.pushplus.plus/send", json={
            "token": push_token,
            "title": f"⚖️ 全球宏观双核内参 ({now_str})",
            "content": final_content.replace("\n", "<br>")
        })
    print("任务执行完毕。")
    sys.exit(0)

if __name__ == "__main__":
    main()
