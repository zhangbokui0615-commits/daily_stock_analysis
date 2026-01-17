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
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if change>0 else ''}{change:.2f}%)\n"
        except:
            summary += f"· {name}: 数据获取失败\n"
    return summary

def analyze_and_push():
    gemini_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    market_data = get_market_data()
    
    # 2. AI 深度分析
    try:
        genai.configure(api_key=gemini_key)
        
        # 核心修正：使用 v1 版本最兼容的旧版模型标识符
        # 针对 404 错误，尝试使用不带 -latest 的版本
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"你是一个资深财经分析师。请根据以下全球市场数据进行深度点评：\n{market_data}\n要求：1. 详细总结市场情绪。2. 分析其对中国A股的潜在影响。3. 提供具体的投资建议。总字数在300-400字左右，增加信息量。"
        
        # 强制指定版本可能解决 404 问题
        response = model.generate_content(prompt)
        ai_report = response.text
    except Exception as e:
        # 如果还是不行，尝试备选模型
        try:
            model = genai.GenerativeModel('gemini-pro')
            ai_report = model.generate_content(prompt).text
        except:
            ai_report = f"AI 分析暂时不可用: {str(e)}"

    content = f"{market_data}\n\n【AI 深度研报】\n{ai_report}"
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报 (AI深度版)",
        "content": content
    })

if __name__ == "__main__":
    analyze_and_push()
