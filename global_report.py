import yfinance as yf
import os
import google.generativeai as genai
import requests

# 1. 监控的全球重点市场
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_summary():
    data_str = "【全球市场实时数据】\n"
    for name, ticker_code in MARKETS.items():
        try:
            ticker = yf.Ticker(ticker_code)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                pct = ((current - prev) / prev) * 100
                data_str += f"· {name}: {current:.2f} ({'+' if pct>0 else ''}{pct:.2f}%)\n"
        except:
            data_str += f"· {name}: 获取失败\n"
    return data_str

def main():
    # 读取配置
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    # 抓取数据
    summary_data = get_market_summary()
    
    # AI 深度分析
    try:
        genai.configure(api_key=api_key)
        # 修正模型名称，彻底解决 NotFound 报错
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"你是一位资深美股与全球宏观分析师。请针对以下数据进行点评，并为中国投资者提供今日操作建议（200字以内）：\n{summary_data}"
        response = model.generate_content(prompt)
        ai_analysis = response.text
    except Exception as e:
        ai_analysis = f"AI 分析暂时离线（错误：{str(e)}）"

    # 推送至微信
    full_content = f"{summary_data}\n\n【AI 策略视角】\n{ai_analysis}"
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球市场早报（AI版）",
        "content": full_content
    })

if __name__ == "__main__":
    main()
