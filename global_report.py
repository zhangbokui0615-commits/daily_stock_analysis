import yfinance as yf
import os
import requests
import sys

# 1. 自选股名单
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

# 🔥 新增功能：自动查找可用的模型
def find_working_model(api_key):
    # 问 Google：我的 Key 能用哪些模型？
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = requests.get(list_url, timeout=10)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            # 优先找 Flash 或 Pro，找到了就返回它的准确名字
            for m in models:
                name = m['name'] # 格式如 "models/gemini-1.5-flash-001"
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'flash' in name: return name
                    if 'pro' in name: return name
            # 如果没找到偏好的，就返回第一个能用的
            if models: return models[0]['name']
    except:
        pass
    # 如果实在问不到，才使用保底的默认值
    return "models/gemini-1.5-flash"

def main():
    api_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    if not api_key:
        print("❌ 错误：未读取到 GEMINI_API_KEY")
        sys.exit(1)

    market_data = get_market_data()
    
    # 1. 先自动寻找正确的模型名字
    model_name = find_working_model(api_key)
    print(f"🤖 自动匹配到的模型: {model_name}")
    
    # 2. 使用匹配到的名字去请求
    # 注意：model_name 已经包含了 'models/' 前缀，所以 URL 里不需要再写
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
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
            # 如果还是不行，把从"问路"到"请求"的所有信息都打印出来调试
            ai_report = f"⚠️ 自动匹配模型 ({model_name}) 依然失败。\n状态码: {response.status_code}\n错误: {response.text[:100]}"
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
