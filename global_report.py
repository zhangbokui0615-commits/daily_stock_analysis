import yfinance as yf
import os
import google.generativeai as genai
import requests
import sys

# 1. 配置全球重点观察名单
MARKETS = {
    "美股-纳斯达克": "^IXIC",
    "美股-标普500": "^GSPC",
    "日股-日经225": "^N225",
    "A股-上证指数": "000001.SS",
    "汇率-美元/日元": "JPY=X"
}

def get_market_data():
    """抓取全球金融数据"""
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
    # 获取环境变量
    api_key = os.getenv("GEMINI_API_KEY")
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    # 抓取实时数据
    market_data = get_market_data()
    
    # 2. AI 深度分析 (兼容性增强逻辑)
    try:
        genai.configure(api_key=api_key)
        
        # 针对 404 错误，尝试使用最基础的模型标识符
        # 如果 gemini-1.5-flash 依然报错，代码会自动捕获异常
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 强制增加信息量：要求 AI 必须分析 A 股逻辑并提供策略
        prompt = f"""
        你是一位全球宏观策略分析师。请针对以下最新的市场数据：
        {market_data}
        
        进行深度解读，要求：
        1. 详细总结昨晚美股和今早日股的波动逻辑。
        2. 深入分析外盘走势对今日中国 A 股（特别是电力、核电、半导体板块）的传导影响。
        3. 给出今日的具体投资建议、风险提示以及止损参考位。
        4. 字数必须在 400-600 字之间，分段清晰，杜绝废话。
        """
        response = model.generate_content(prompt)
        ai_analysis = response.text
    except Exception as e:
        # 如果 1.5-flash 失败，尝试切换到旧版稳定的 Pro 模型
        try:
            model = genai.GenerativeModel('gemini-pro')
            ai_analysis = model.generate_content(prompt).text
        except:
            ai_analysis = f"⚠️ AI 深度解析暂时不可用 (错误详情: {str(e)})"

    # 3. 发送微信推送
    full_content = f"{market_data}\n\n🔍 【AI 深度策略研报】\n{ai_analysis}"
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球财经早报 (AI深度版)",
        "content": full_content
    })
    
    # 【核心修复】解决脚本“一直在跑”的问题：强制退出程序
    print("分析完成，安全退出。")
    sys.exit(0)

if __name__ == "__main__":
    main()
