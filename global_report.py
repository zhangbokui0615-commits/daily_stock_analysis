import yfinance as yf
import os
import requests
import sys

# 1. 监控名单
MARKETS = {
    "美股-纳斯达克": "^IXIC", "美股-标普500": "^GSPC",
    "日股-日经225": "^N225", "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_data():
    summary = "📊 【全球市场实时快报】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if change>0 else ''}{change:.2f}%)\n"
        except: summary += f"· {name}: 获取失败\n"
    return summary

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    market_data = get_market_data()
    
    # 2. 核心修正：直接使用 API 链接，不再使用报错的库
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"你是一位资深财经分析师。请针对以下数据进行深度解读，字数不少于400字，分段清晰，给A股投资者具体建议：\n{market_data}"
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        res_json = response.json()
        # 提取 AI 回复内容
        ai_report = res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        ai_report = f"⚠️ AI 深度研报生成失败。详细日志: {str(response.text if 'response' in locals() else e)}"

    # 3. 推送微信
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报 (AI 深度版)",
        "content": f"{market_data}\n\n🔍 【AI 深度策略研报】\n{ai_report}"
    })
    sys.exit(0)

if __name__ == "__main__":
    main()
