import yfinance as yf
import os
import google.generativeai as genai
import requests

# 1. 配置全球市场观察名单（美股、日股、A股、日元汇率）
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_global_data():
    summary = "【全球市场最新数据快报】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                price = hist['Close'].iloc[-1]
                change = ((price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                summary += f"{name}: {price:.2f} ({change:+.2f}%)\n"
        except:
            continue
    return summary

def analyze_and_push():
    # 获取全球数据
    market_info = get_global_data()
    
    # 2. 调用 AI 进行多市场趋势分析
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"你是一个精通全球市场的财经专家。请根据以下数据，简明总结昨晚美股和今早日股的动态，并给中国投资者提供一条今日建议：\n{market_info}"
    
    response = model.generate_content(prompt)
    final_report = f"🌍 全球财经早报\n\n{market_info}\n\n💡 AI 专家解读：\n{response.text}"
    
    # 3. 推送到微信 (使用 PUSHPLUS_TOKEN)
    token = os.getenv("PUSHPLUS_TOKEN")
    if token:
        requests.post("http://www.pushplus.plus/send", json={
            "token": token,
            "title": "全球财经早报",
            "content": final_report.replace("\n", "<br>"),
            "template": "html"
        })
    print("分析完成并已尝试发送")

if __name__ == "__main__":
    analyze_and_push()
