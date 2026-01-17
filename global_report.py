import yfinance as yf
import os
import google.generativeai as genai
import requests

# 1. 监控市场列表
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_data():
    summary = "【全球市场实时数据】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if pct>0 else ''}{pct:.2f}%)\n"
        except: summary += f"· {name}: 获取失败\n"
    return summary

def main():
    # 获取环境变量
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    # 获取数据并调用 AI
    data_text = get_market_data()
    try:
        genai.configure(api_key=api_key)
        # 统一使用 gemini-1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        report = model.generate_content(f"简评以下财经数据并给中国投资者一句建议：\n{data_text}").text
    except Exception as e:
        report = f"AI分析暂时离线: {str(e)}"

    # 发送推送
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报 (修正版)",
        "content": f"{data_text}\n\n【AI深度解读】\n{report}"
    })

if __name__ == "__main__":
    main()
