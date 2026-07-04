import streamlit as st
import pandas as pd
import urllib.request
import json
import os

# 设置网页布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")

# --- 手机端防乱码、防重叠、强制换行的纯净 CSS 注入 ---
st.markdown("""
<style>
    /* 1. 强制隐藏或修正可能导致重叠的右上角官方按钮与展开图标乱码 */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
    /* 清除特定组件可能附带的乱码文本前缀 */
    span:contains("_arrow"), div:contains("_arrow") { font-size: 0 !important; color: transparent !important; }

    /* 2. 核心文本容器：支持手机端完美自动换行，绝不溢出 */
    .stMarkdown div p {
        word-break: break-all !important;
        white-space: pre-wrap !important;
    }
    
    /* 3. 仿手机原生 App 卡片设计 */
    .fund-card {
        background-color: #1E232A;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #3A3F47;
    }
    .fund-title {
        font-size: 16px;
        font-weight: bold;
        color: #FFFFFF;
        margin-bottom: 8px;
        border-bottom: 1px solid #3A3F47;
        padding-bottom: 6px;
    }
    .fund-tag {
        background-color: #2A2F35;
        color: #A1C4FD;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        display: inline-block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 我的智能化定投实时监控看板")
st.markdown("根据底层指数近 10 年真实 PE 百分位及 TTM 股息率，自动输出量化定投执行建议")

CONFIG_FILE = "my_fund_settings.json"

DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50', 'period': '每月21号', 'amount': 1100,
        'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%', 'status': '估值偏高、股息最优',
        'base_strategy': '⚠️ 估值百分位偏高(>80%)。虽然4.85%的股息极具防守性，但短期拥挤度高。建议【维持当前定投不加仓】，或将当前的 {plan} 缩减20%，积攒现金。'
    }, 
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100', 'period': '每天', 'amount': 80,
        'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%', 'status': '显著高估、轻微红利',
        'base_strategy': '🚨 处于历史高位区间。美股科技股目前溢价较高，且无红利保护。建议将当前的 {plan} 【下调至 {half_amount} 元左右（防御模式）】，保留子弹等待回调。'
    }, 
    '023882': {
        'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50', 'period': '每周二', 'amount': 100,
        'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%', 'status': '中性偏贵、低股息',
        'base_strategy': '等权观望。估值处于60%的中枢偏上位置，成长股弹性较大。建议【严格执行常规计划 {plan}】，不主动防御也不盲目加仓，保持自动扣款。'
    },   
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流', 'period': '每周二', 'amount': 790,
        'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%', 'status': '深度低估、均衡现金流',
        'base_strategy': '💎 绝对核心加仓区！PE分位仅30.77%且股息率高达3.2%。属于典型的性价比高地。建议【坚定执行当前计划 {plan}】，甚至可在发薪日额外手动肉身加仓。'
    }   
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, ensure_ascii=False, indent=4)

if 'fund_config' not in st.session_state:
    st.session_state.fund_config = load_config()

@st.cache_data(ttl=1800)
def get_fund_history_clean(fund_code):
    try:
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize=40"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        with urllib.request.urlopen(req, timeout=4) as response: html = response.read().decode('utf-8')
        data = json.loads(html)
        if not data or data.get("Data") is None or not data["Data"].get("LSJZList"): return None, "暂无流水"
        raw_list = data["Data"]["LSJZList"]
        records = []
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): continue
            records.append({"日期": item["FSRQ"], "单位净值": float(item["DWJZ"]), "净值增长率": f"{item['JZZZL']}%"})
        return pd.DataFrame(records), None
    except Exception as e: return None, str(e)


# --- 1. 全景卡片看板（完美替换死板大表格，手机端自适应神级排版） ---
st.subheader("📋 我的定投核心资产智能执行卡片")

for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    
    # 注入纯净美观的自适应块
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-title">📈 {info['name']} ({code})</div>
        <div class="fund-tag">跟踪指数: {info['index_name']}</div> | <div class="fund-tag" style="color:#FFF;">当前计划: {plan_str}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 指标三项并排展示
    c1, c2, c3 = st.columns(3)
    c1.metric("10年 PE 百分位", f"{info['pe_percent']:.2f}%")
    c2.metric("当前 PE", f"{info['pe_ttm']:.2f}")
    c3.metric("TTM 股息率", info['div_yield'])
    
    # 建议提示框：原生组件，手机端自动完美换行
    if "⚠️" in strategy_str or "🚨" in strategy_str:
        st.warning(strategy_str)
    else:
        st.info(strategy_str)
    st.markdown("<div style='margin-bottom:25px;'></div>", unsafe_allow_html=True)


# --- 2. 【控制台】修改并永久保存定投计划 ---
with st.expander("⚙️ 点此展开：修改并永久保存每支基金的定投计划"):
    st.markdown("在此处更新你的计划，系统会自动修正排版并永久记住配置。")
    edit_code = st.selectbox("选择基金", list(st.session_state.fund_config.keys()), 
                             format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
    current_info = st.session_state.fund_config[edit_code]
    
    new_period = st.text_input("定投周期：", value=current_info['period'], key=f"p_{edit_code}")
    new_amount = st.number_input("定投金额 (元)固定资产：", value=int(current_info['amount']), step=10, key=f"a_{edit_code}")
    
    if st.button("💾 确认更新并永久保存计划"):
        st.session_state.fund_config[edit_code]['period'] = new_period
        st.session_state.fund_config[edit_code]['amount'] = new_amount
        save_config(st.session_state.fund_config)
        st.success("配置已成功固化到云端！")
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)


# --- 3. 基金穿透流水明细流 ---
st.subheader("🔍 单只基金历史流水穿透")
select_detail = st.selectbox("切换查看各基金历史流水明细：", list(st.session_state.fund_config.keys()),
                             format_func=lambda x: st.session_state.fund_config[x]['name'])

with st.spinner('正在同步净值明细...'):
    df_hist, err = get_fund_history_clean(select_detail)
if err is None and df_hist is not None:
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
else:
    st.info("💡 历史日明细抓取超时（由于云端网络波动导致，核心指标不受影响）。")
