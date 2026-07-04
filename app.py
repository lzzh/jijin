import streamlit as st
import json
import os
import time
import random
import requests

st.set_page_config(page_title="精简版定投监控看板", layout="centered", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════
#  极简金融终端样式
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

#MainMenu, footer, header { visibility: hidden; }
* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background-color: #080C12 !important;
    color: #C9D1D9 !important;
}

.block-container {
    padding: 1rem 0.75rem 3rem 0.75rem !important;
    max-width: 650px !important;
}

.dash-header {
    background: linear-gradient(135deg, #0D1117 0%, #111827 100%);
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    position: relative;
}
.dash-header h1 {
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #E6EDF3 !important;
    margin: 0 0 4px 0 !important;
}
.dash-header .subtitle {
    font-size: 11px;
    color: #6E7681;
}

.section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #F0A500;
    margin: 20px 0 12px 0;
}

.fund-card {
    background: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 10px;
    position: relative;
}
.fund-card::before {
    content: '';
    position: absolute;
    left: 0; top: 12px; bottom: 12px;
    width: 3px;
    border-radius: 0 2px 2px 0;
}
.fund-card.status-low::before  { background: #2DA44E; }
.fund-card.status-mid::before  { background: #F0A500; }
.fund-card.status-high::before { background: #F85149; }

.fund-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
}
.fund-name {
    font-size: 14px;
    font-weight: 600;
    color: #E6EDF3;
}
.fund-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #6E7681;
}
.fund-plan-badge {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    color: #58A6FF;
    font-family: 'JetBrains Mono', monospace;
}

.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 10px;
}
.metric-cell {
    background: #161B22;
    border-radius: 6px;
    padding: 8px 4px;
    text-align: center;
}
.metric-label {
    font-size: 9px;
    color: #6E7681;
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #E6EDF3;
}
.metric-value.low  { color: #2DA44E; }
.metric-value.mid  { color: #F0A500; }
.metric-value.high { color: #F85149; }

.strategy-box {
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 12px;
    line-height: 1.5;
    background: #161B22;
    border-left: 2px solid #30363D;
}

.console-card {
    background: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 14px;
}

div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input {
    background-color: #161B22 !important;
    border-color: #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 6px !important;
}

div[data-testid="stButton"] > button {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  配置存储层（不存复杂历史，只存状态）
# ══════════════════════════════════════════════
CONFIG_FILE = "my_fund_pure_settings.json"

DEFAULT_CONFIG = {
    '008163': { 'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50', 'period': '每月21号', 'amount': 1100, 'latest_nv': 0.0, 'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%' },
    '016452': { 'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100', 'period': '每天', 'amount': 80, 'latest_nv': 0.0, 'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%' },
    '023882': { 'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50', 'period': '每周二', 'amount': 100, 'latest_nv': 0.0, 'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%' },
    '023917': { 'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流', 'period': '每周二', 'amount': 790, 'latest_nv': 0.0, 'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%' }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

if 'pure_config' not in st.session_state:
    st.session_state.pure_config = load_config()

# ══════════════════════════════════════════════
#  🌐 超轻量数据一键抓取逻辑
# ══════════════════════════════════════════════
def fetch_fund_all_data(fund_code):
    """
    通过移动端单一无防爬开放接口，秒级抓取净值与估值三要素（不追溯历史）
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36'}
    
    # 1. 抓取最新净值
    nv_url = f"https://fundmobapi.eastmoney.com/FundMApi/FundMNvSearch?FCODE={fund_code}&pageIndex=1&pageSize=1&plat=Wap&product=EFund"
    latest_nv = 0.0
    try:
        r1 = requests.get(nv_url, headers=headers, timeout=5).json()
        if r1.get("Data") and len(r1["Data"]) > 0:
            latest_nv = float(r1["Data"][0].get("DWJZ", 0.0))
    except: pass

    # 2. 抓取最新估值综合要素
    val_url = f"https://fundmobapi.eastmoney.com/FundMApi/FundVarietieValuationDetail?FCODE={fund_code}&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0"
    pe, pct, div = None, None, None
    try:
        r2 = requests.get(val_url, headers=headers, timeout=5).json()
        if r2.get("Expansion") and r2["Expansion"].get("GZData"):
            gz = r2["Expansion"]["GZData"]
            pe = float(gz.get("PE", 0))
            pct = float(gz.get("PE_PERCENT", 0))
            div_yield = gz.get("D_YIELD", "0.00%")
            div = f"{float(div_yield):.2f}%" if "%" not in str(div_yield) else div_yield
    except: pass

    return latest_nv, pe, pct, div

# ══════════════════════════════════════════════
#  极简策略输出
# ══════════════════════════════════════════════
def get_strategy_tips(pe_percent):
    if pe_percent >= 75.0: return "high", "🚨 估值高危区：触发防御机制，建议减少扣款或静待回调。"
    elif pe_percent <= 35.0: return "low", "💎 黄金低估区：安全边际极高，坚决执行，甚至可酌情加码！"
    return "mid", "⚖️ 中性均衡区：水位平稳，无看空或看多信号，雷打不动执行原计划。"

# ══════════════════════════════════════════════
#  前端看板核心展示
# ══════════════════════════════════════════════
st.markdown("""
<div class="dash-header">
    <h1>📊 定投数据监控仓</h1>
    <div class="subtitle">实时抓取最新单位净值、当前 PE、历史百分位及最新股息率</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">资产池精细状态</div>', unsafe_allow_html=True)

for code, info in st.session_state.pure_config.items():
    lvl, tips = get_strategy_tips(info['pe_percent'])
    pct_cls = 'high' if info['pe_percent'] >= 75 else ('low' if info['pe_percent'] <= 35 else 'mid')
    
    st.markdown(f"""
    <div class="fund-card status-{lvl}">
        <div class="fund-card-header">
            <div>
                <div class="fund-name">{info['name']}</div>
                <div class="fund-code">{code} · {info['index_name']}</div>
            </div>
            <div class="fund-plan-badge">{info['period']} | {info['amount']}元</div>
        </div>
        <div class="metrics-row">
            <div class="metric-cell">
                <div class="metric-label">最新净值</div>
                <div class="metric-value" style="color:#58A6FF">{info['latest_nv']:.4f}</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">PE百分位</div>
                <div class="metric-value {pct_cls}">{info['pe_percent']:.2f}%</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">当前 PE (TTM)</div>
                <div class="metric-value">{info['pe_ttm']:.2f}</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">最新股息率</div>
                <div class="metric-value" style="color:#2DA44E">{info['div_yield']}</div>
            </div>
        </div>
        <div class="strategy-box">{tips}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  数据交互控制台
# ══════════════════════════════════════════════
st.markdown('<div class="section-label">核心操作中心</div>', unsafe_allow_html=True)
st.markdown('<div class="console-card">', unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])
with c1:
    target_code = st.selectbox("选择目标资产进行操作", list(st.session_state.pure_config.keys()), 
                               format_func=lambda x: f"[{x}] {st.session_state.pure_config[x]['name']}")
with c2:
    st.write("") # 补齐高度
    st.write("")
    if st.button("🔄 仅更新当前选中项", type="primary", use_container_width=True):
        with st.spinner("正在联网读取数据..."):
            nv, pe, pct, div = fetch_fund_all_data(target_code)
            if nv > 0: st.session_state.pure_config[target_code]['latest_nv'] = nv
            if pe: st.session_state.pure_config[target_code]['pe_ttm'] = pe
            if pct: st.session_state.pure_config[target_code]['pe_percent'] = pct
            if div: st.session_state.pure_config[target_code]['div_yield'] = div
            save_config(st.session_state.pure_config)
            st.toast(f"✅ {target_code} 数据已精准同步！")
            st.rerun()

if st.button("🚀 懒人通道：一键更新全员数据", use_container_width=True):
    with st.spinner("全员数据同步中..."):
        for code in st.session_state.pure_config.keys():
            nv, pe, pct, div = fetch_fund_all_data(code)
            if nv > 0: st.session_state.pure_config[code]['latest_nv'] = nv
            if pe: st.session_state.pure_config[code]['pe_ttm'] = pe
            if pct: st.session_state.pure_config[code]['pe_percent'] = pct
            if div: st.session_state.pure_config[code]['div_yield'] = div
            time.sleep(random.uniform(0.2, 0.4))
        save_config(st.session_state.pure_config)
        st.toast("🎉 所有资产估值要素刷新完成！")
        st.rerun()

# ══════════════════════════════════════════════
#  底座计划基础修改与常规增删
# ══════════════════════════════════════════════
st.markdown("---")
op_mode = st.radio("其他常规管理", ["📝 调整基本扣款计划", "➕ 新增资产卡片", "🗑️ 移除当前卡片"], horizontal=True)

if op_mode == "📝 调整基本扣款计划":
    with st.form("edit_form"):
        curr = st.session_state.pure_config[target_code]
        st.markdown(f"修改 **{curr['name']}** 的扣款计划")
        cc1, cc2 = st.columns(2)
        with cc1: u_period = st.text_input("定投周期", value=curr['period'])
        with cc2: u_amount = st.number_input("定投金额", value=int(curr['amount']), step=10)
        if st.form_submit_button("保存计划修改"):
            st.session_state.pure_config[target_code].update({'period': u_period, 'amount': u_amount})
            save_config(st.session_state.pure_config)
            st.rerun()

elif op_mode == "➕ 新增资产卡片":
    with st.form("add_pure_form"):
        a_code = st.text_input("基金代码 (6位)", max_chars=6)
        a_name = st.text_input("基金简称")
        a_index = st.text_input("跟踪指数名称", value="宽基指数")
        a_period = st.text_input("周期", value="每周二")
        a_amount = st.number_input("定投金额", value=100, step=10)
        if st.form_submit_button("确认建立空白卡片"):
            if len(a_code) == 6 and a_name:
                st.session_state.pure_config[a_code] = {
                    'name': a_name, 'index_name': a_index, 'period': a_period, 'amount': a_amount,
                    'latest_nv': 0.0, 'pe_ttm': 0.0, 'pe_percent': 50.0, 'div_yield': '0.00%'
                }
                save_config(st.session_state.pure_config)
                st.rerun()
            else: st.error("输入有误")

elif op_mode == "🗑️ 移除当前卡片":
    st.warning(f"确定要从看板中移除基金： [{target_code}] {st.session_state.pure_config[target_code]['name']} 吗？")
    if st.button("💥 确认擦除卡片"):
        del st.session_state.pure_config[target_code]
        save_config(st.session_state.pure_config)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
