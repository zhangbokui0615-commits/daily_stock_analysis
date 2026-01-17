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
    # ✅ 修正的核心：这里填的是“保险箱的名字”，程序会自动去取里面的钥匙
    # 只要您 GitHub Secrets 里那个保险箱的名字叫 GEMINI_API_KEY，这里就不用改
    api_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    # 🕵️‍♂️ 自动检查：如果钥匙没取到，直接告诉您（而不是报 404）
    if not api_key:
        print("❌ 错误：程序没找到 GEMINI_API_KEY。请检查 GitHub Secrets 设置。")
        requests.post("http://www.pushplus.plus/send", json={
            "token": push_token, "title": "脚本配置报错", "content": "未读取到 GEMINI_API_KEY，请检查 Secrets 名字是否对应。"
        })
        sys.exit(1)

    market_data = get_market_data()
    
    # 使用最通用的 v1beta 接口
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"""
                你是一位 A 股资深操盘手。请分析以下最新数据：
                {market_data}
                
                请输出一份实战复盘，要求：
                1. 分析【特变电工】和【中国核电】的今日走势（主力意图）。
                2. 结合纳斯达克和汇率，判断外部环境对 A 股的影响。
                3. 给出明确的【持股/减仓/抄底】建议。
                4. 字数 400 字左右，风格犀利，不要废话。
                """
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            ai_report = response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # 如果这里报错，说明 Key 本身有问题（比如项目没开通权限）
            ai_report = f"⚠️ AI 分析失败 (状态码 {response.status_code})。请检查 Key 是否有效或项目权限是否开启。"
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
