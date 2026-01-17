import yfinance as yf
import os
import google.generativeai as genai
import requests

# 1. 监控全球重点市场（你可以根据需要增删代码）
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_data():
    summary = "📊 【全球市场实时数据快报】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if pct>0 else ''}{pct:.2f}%)\n"
        except:
            summary += f"· {name}: 获取失败\n"
    return summary

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    market_data = get_market_data()
    
    try:
        genai.configure(api_key=api_key)
        # 修正模型名称，确保 AI 正常响应
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 强化 Prompt 指令，要求 AI 增加信息量
        prompt = f"""
        你是一位资深全球宏观策略分析师。请针对以下最新的市场数据：
        {market_data}
        进行深度解读，要求：
        1. 总结昨晚美股和今早日股的走势逻辑。
        2. 分析这些波动对中国投资者（A股/港股）的潜在影响。
        3. 提供具体的投资建议或避险提示。
        4. 字数控制在400字左右，分段输出，保持专业且易懂。
        """
        response = model.generate_content(prompt)
        ai_analysis = response.text
    except Exception as e:
        ai_analysis = f"⚠️ AI 深度解读暂时不可用，错误原因：{str(e)}"

    # 发送推送
    full_content = f"{market_data}\n\n🔍 【AI 深度策略研报】\n{ai_analysis}"
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报（深度版）",
        "content": full_content
    })

if __name__ == "__main__":
    main()
