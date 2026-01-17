import yfinance as yf
import os
import google.generativeai as genai
import requests

# 1. 配置全球观察名单
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_data():
    summary = "【全球市场最新数据快报】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                close_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2]
                change = ((close_price - prev_price) / prev_price) * 100
                summary += f"· {name}: {close_price:.2f} ({'+' if change>0 else ''}{change:.2f}%)\n"
        except:
            summary += f"· {name}: 获取失败\n"
    return summary

def analyze_and_push():
    # 获取环境变量
    gemini_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    # 1. 抓取数据
    market_data = get_market_data()
    
    # 2. AI 深度分析
    try:
        genai.configure(api_key=gemini_key)
        # 终极修正：使用 gemini-1.5-flash-latest 确保接口匹配
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"你是一个资深财经分析师。请根据以下全球市场数据进行简短点评：\n{market_data}\n要求：1. 总结表现情绪。2. 为中国投资者提供一句今日建议。3. 字数200字内。"
        response = model.generate_content(prompt)
        ai_report = response.text
    except Exception as e:
        ai_report = f"AI 分析暂时不可用: {str(e)}"

    # 3. 推送到微信
    content = f"{market_data}\n\n【AI 深度解读】\n{ai_report}"
    payload = {
        "token": push_token,
        "title": "🌍 全球财经早报 (AI版)",
        "content": content
    }
    requests.post("http://www.pushplus.plus/send", json=payload)

if __name__ == "__main__":
    analyze_and_push()
