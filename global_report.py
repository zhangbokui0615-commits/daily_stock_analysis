import yfinance as yf
import os
import requests
import sys

# 1. 您的自选监控名单
MARKETS = {
    "纳斯达克": "^IXIC", "上证指数": "000001.SS",
    "特变电工": "600089.SS", "中国核电": "601985.SS",
    "美元/日元": "JPY=X"
}

def get_market_data():
    summary = "📊 【自选股实时快报】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            data = ticker.history(period="2d")
            if len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary += f"· {name}: {curr:.2f} ({'+' if pct>0 else ''}{pct:.2f}%)\n"
        except: summary += f"· {name}: 暂时无法获取\n"
    return summary

def main():
    # 读取您刚才已经更新好的 新 Key，不用动 Secrets
    api_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    if not api_key:
        print("❌ 错误：未读取到 GEMINI_API_KEY")
        sys.exit(1)

    market_data = get_market_data()
    
    # -------------------------------------------------------
    # 🔄 核心修正：改回 'gemini-pro'
    # 之前的 404 是因为 Flash 模型在新号上没激活
    # Pro 模型是 Google 的“基石”，新号默认一定有权限！
    # -------------------------------------------------------
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"""
                你是一位 A 股资深操盘手。请分析以下最新数据：
                {market_data}
                
                请输出一份实战复盘，要求：
                1. 分析【特变电工】和【中国核电】的今日走势。
                2. 结合纳指和汇率判断外部环境。
                3. 给出明确的【持股/减仓/抄底】建议。
                4. 字数 400 字左右，风格犀利。
                """
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            ai_report = response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            ai_report = f"⚠️ AI 分析异常 (状态码 {response.status_code})。错误信息: {response.text}"
    except Exception as e:
        ai_report = f"网络请求失败: {str(e)}"

    # 推送
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🚀 A股 & 全球深度策略 (AI实盘)",
        "content": f"{market_data}\n\n🧠 【AI 操盘手分析】\n{ai_report}"
    })
    print("任务完成。")
    sys.exit(0)

if __name__ == "__main__":
    main()
