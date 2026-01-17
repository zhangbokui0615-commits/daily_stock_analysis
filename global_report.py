import yfinance as yf
import os
import requests
import sys
import json

# 1. 观察名单
MARKETS = {
    "纳指": "^IXIC", "标普500": "^GSPC",
    "日经225": "^N225", "上证指数": "000001.SS",
    "美元/日元": "JPY=X"
}

def get_market_data():
    summary = "📊 【市场数据】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if pct>0 else ''}{pct:.2f}%)\n"
        except: summary += f"· {name}: 抓取失败\n"
    return summary

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    market_data = get_market_data()

    # 2. 深度兼容性逻辑：依次尝试 4 种不同的官方调用路径
    # 彻底解决 404 models/gemini-1.5-flash is not found
    test_urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    ]
    
    payload = {
        "contents": [{"parts": [{"text": f"你是一位财经分析师。请针对以下数据进行深度解读（300字以上）：\n{market_data}"}]}]
    }
    
    ai_report = ""
    error_log = ""

    for url in test_urls:
        try:
            response = requests.post(url, json=payload, timeout=20)
            res_json = response.json()
            if 'candidates' in res_json:
                ai_report = res_json['candidates'][0]['content']['parts'][0]['text']
                break
            else:
                error_log += f"路径失败: {url.split('models/')[1].split(':')[0]} | 响应: {response.text[:100]}\n"
        except Exception as e:
            error_log += f"请求错误: {str(e)}\n"

    if not ai_report:
        ai_report = f"⚠️ AI 生成失败。尝试日志：\n{error_log}"

    # 3. 发送微信
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经 & 股票深度复盘",
        "content": f"{market_data}\n\n🔍 【AI 深度解读】\n{ai_report}"
    })
    sys.exit(0)

if __name__ == "__main__":
    main()
