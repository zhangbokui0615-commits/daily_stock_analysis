import yfinance as yf
import os
import google.generativeai as genai
from google.generativeai.types import RequestOptions
import requests
import sys

# 1. 配置全球观察名单
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
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
        except:
            summary += f"· {name}: 获取失败\n"
    return summary

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    market_data = get_market_data()
    
    # 2. 核心修正：使用 RequestOptions 强制指定 API 版本
    try:
        genai.configure(api_key=api_key)
        
        # 强制使用 v1 版本接口，解决 v1beta 下的 404 问题
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        你是一位资深财经分析师。请针对以下数据进行深度解读：
        {market_data}
        要求：
        1. 详细分析市场走势逻辑。
        2. 给中国投资者提供今日 A 股的操作策略。
        3. 总字数不少于 400 字，增加信息含金量。
        """
        
        # 使用 request_options 强制兼容性
        response = model.generate_content(
            prompt, 
            request_options=RequestOptions(api_version='v1')
        )
        ai_report = response.text
    except Exception as e:
        ai_report = f"⚠️ AI 分析触发了版本兼容性保护，请手动检查。错误: {str(e)}"

    # 3. 推送
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报 (AI 深度版)",
        "content": f"{market_data}\n\n🔍 【AI 深度策略研报】\n{ai_report}"
    })
    
    # 强制结束，防止 GitHub Actions “一直跑”
    print("任务已完成。")
    sys.exit(0)

if __name__ == "__main__":
    main()
