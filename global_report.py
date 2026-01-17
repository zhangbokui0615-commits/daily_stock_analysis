import yfinance as yf
import os
import requests
import sys

# 1. 扩充后的全球核心资产监控名单
# yfinance 代码说明：
# ^GSPC: 标普500 (美股晴雨表) | ^IXIC: 纳斯达克 (科技股风向)
# ^N225: 日经225 (亚洲资金流向) | ^HXC: 纳斯达克金龙中国指数 (中概股风向)
# GC=F: COMEX黄金 (避险/战争指标) | CL=F: NYMEX原油 (通胀/地缘政治指标)
# ^TNX: 10年期美债收益率 (全球资产定价之锚) | ^VIX: 恐慌指数 (市场情绪)
MARKETS = {
    "🇺🇸美股-纳指": "^IXIC",
    "🇺🇸美股-标普": "^GSPC",
    "🇯🇵日股-日经": "^N225",
    "🇨🇳中概-金龙": "^HXC",
    "💰商品-黄金": "GC=F",
    "🛢商品-原油": "CL=F",
    "📉宏观-美债": "^TNX",
    "😱宏观-恐慌": "^VIX",
    "🇨🇳A股-上证": "000001.SS",
    "⚡️持仓-特变": "600089.SS",
    "☢️持仓-核电": "601985.SS"
}

def get_market_data():
    summary = "🌍 【全球宏观 & 市场数据监测】\n"
    for name, code in MARKETS.items():
        try:
            ticker = yf.Ticker(code)
            # 获取最近5天数据，方便计算短期趋势
            data = ticker.history(period="5d")
            if len(data) >= 2:
                curr = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                
                # 简单的趋势判断符号
                trend = "🔴大涨" if pct > 2 else ("🔺上涨" if pct > 0 else ("🔻下跌" if pct > -2 else "💚大跌"))
                summary += f"{name}: {curr:.2f} ({pct:+.2f}%) {trend}\n"
        except: 
            summary += f"{name}: ⏳ 数据暂时延迟\n"
    return summary

# 自动查找可用模型逻辑（保留之前的成功逻辑）
def find_working_model(api_key):
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = requests.get(list_url, timeout=10)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            for m in models:
                name = m['name']
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'flash' in name: return name
                    if 'pro' in name: return name
            if models: return models[0]['name']
    except: pass
    return "models/gemini-1.5-flash"

def main():
    api_key = os.getenv("GEMINI_API_KEY") 
    push_token = os.getenv("PUSHPLUS_TOKEN")
    
    if not api_key:
        print("❌ 错误：未读取到 GEMINI_API_KEY")
        sys.exit(1)

    market_data = get_market_data()
    model_name = find_working_model(api_key)
    print(f"🤖 使用模型: {model_name}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    
    # 🔥 升级后的超级指令：加入宏观、战争、经济分析要求
    prompt = f"""
    你是一位具有全球视野的顶级宏观对冲基金经理。请基于以下最新的全球市场数据进行深度复盘：
    
    {market_data}
    
    请撰写一份《全球宏观与A股策略日报》，内容必须包含以下四个维度（字数600字左右，分点陈述，风格犀利）：
    
    1. 🌍 **全球战局与经济大事**：
       - 通过【黄金】和【原油】的涨跌，反推当前地缘政治（如中东、俄乌战争）是否升级？
       - 通过【美债收益率】和【恐慌指数VIX】，判断全球资金是在避险还是贪婪？美联储降息预期如何？
       
    2. 🇺🇸🇯🇵 **外围股市映射**：
       - 美股（纳指/标普）和日股的走势，对全球科技股和风险偏好有何指引？
       - 【中概股金龙指数】昨晚的表现，通常直接预示今天港股和A股的开盘情绪，请重点解读。
       
    3. 🇨🇳 **A股大势研判**：
       - 结合上述外围环境（是利好共振还是利空压制？），判断今日上证指数的关键压力位和支撑位。
       
    4. 🎯 **持仓个股操作指令**：
       - **特变电工** & **中国核电**：在外围通胀预期或科技周期的背景下，今天该【锁仓不动】、【逢高减仓】还是【趁势加仓】？给出明确理由。
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            ai_report = response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            ai_report = f"⚠️ AI 分析异常: {response.text[:100]}"
    except Exception as e:
        ai_report = f"网络请求失败: {str(e)}"

    # 推送
    requests.post("http://www.pushplus.plus/send", json={
        "token": push_token,
        "title": "🌍 全球宏观 & A股策略 (加强版)",
        "content": f"{market_data}\n\n🧠 【顶级基金经理复盘】\n{ai_report}"
    })
    print("任务完成。")
    sys.exit(0)

if __name__ == "__main__":
    main()
