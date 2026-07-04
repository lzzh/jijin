import streamlit as st
import pandas as pd
import urllib.request
import json
import os
import time
import random
import re
import altair as alt

st.set_page_config(page_title="定投监控看板", layout="centered", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════
#  全局样式：暗色金融终端风格（完美移动端自适应与触控优化）
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── 基础重置 ── */
#MainMenu, footer, header { visibility: hidden; }
* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background-color: #080C12 !important;
    color: #C9D1D9 !important;
}

/* ── 移动端优先容器 ── */
.block-container {
    padding: 0.75rem 0.75rem 3rem 0.75rem !important;
    max-width: 680px !important;
}
@media (min-width: 768px) {
    .block-container { padding: 1.5rem 2rem 2rem 2rem !important; }
}

[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

/* ── 顶部 Banner ── */
.dash-header {
    background: linear-gradient(135deg, #0D1117 0%, #111827 50%, #0D1117 100%);
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}
@media (min-width: 768px) {
    .dash-header { border-radius: 16px; padding: 24px 32px; margin-bottom: 24px; }
}
.dash-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #F0A500, #58A6FF, transparent);
}
.dash-header h1 {
    font-size: 17px !important;
    font-weight: 700 !important;
    color: #E6EDF3 !important;
    margin: 0 0 4px 0 !important;
    letter-spacing: -0.3px;
}
@media (min-width: 768px) {
    .dash-header h1 { font-size: 22px !important; }
}
.dash-header .subtitle {
    font-size: 11px;
    color: #6E7681;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.6;
}

/* ── 分区标题 ── */
.section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #F0A500;
    margin: 20px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
@media (min-width: 768px) {
    .section-label { font-size: 11px; margin: 28px 0 14px 0; }
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #1F2937, transparent);
}

/* ── 基金主卡片 ── */
.fund-card {
    background: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 14px 14px 14px 18px;
    margin-bottom: 10px;
    position: relative;
}
.fund-card::before {
    content: '';
    position: absolute;
    left: 0; top: 10px; bottom: 10px;
    width: 3px;
    border-radius: 0 2px 2px 0;
}
.fund-card.status-low::before  { background: #2DA44E; }
.fund-card.status-mid::before  { background: #F0A500; }
.fund-card.status-high::before { background: #F85149; }

.fund-card-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
}
@media (min-width: 480px) {
    .fund-card-header { flex-direction: row; justify-content: space-between; align-items: flex-start; }
}
.fund-name {
    font-size: 14px;
    font-weight: 600;
    color: #E6EDF3;
    line-height: 1.4;
}
@media (min-width: 768px) {
    .fund-name { font-size: 15px; }
}
.fund-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #6E7681;
    margin-top: 2px;
}
.fund-plan-badge {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #58A6FF;
    font-family: 'JetBrains Mono', monospace;
    align-self: flex-start;
    white-space: nowrap;
    min-height: 32px;
    display: flex;
    align-items: center;
}

/* ── 指标网格 ── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}
.metric-cell {
    background: #161B22;
    border-radius: 8px;
    padding: 10px 8px;
    text-align: center;
}
.metric-label {
    font-size: 9px;
    color: #6E7681;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    font-weight: 500;
    line-height: 1.3;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: #E6EDF3;
    line-height: 1;
}
@media (min-width: 400px) {
    .metric-value { font-size: 17px; }
    .metric-label { font-size: 10px; letter-spacing: 0.8px; }
}
.metric-value.low  { color: #2DA44E; }
.metric-value.mid  { color: #F0A500; }
.metric-value.high { color: #F85149; }

/* ── 策略提示框 ── */
.strategy-box {
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.6;
    color: #C9D1D9;
    word-break: break-all;
}
.strategy-box.low  { background: #0F2A1A; border: 1px solid #2DA44E33; }
.strategy-box.mid  { background: #1F1A0A; border: 1px solid #F0A50033; }
.strategy-box.high { background: #2A0F0F; border: 1px solid #F8514933; }
.strategy-box.info { background: #0D1F33; border: 1px solid #58A6FF33; }

/* ── 控制台 ── */
.console-card {
    background: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
}
@media (min-width: 768px) {
    .console-card { padding: 24px; }
}

/* ── 原生控件触控区优化 ── */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input,
div[data-testid="stTextArea"] > div > textarea {
    background-color: #161B22 !important;
    border-color: #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
    font-size: 16px !important;
}
div[data-testid="stTextArea"] > div > textarea:focus,
div[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #58A6FF !important;
    box-shadow: 0 0 0 2px #58A6FF22 !important;
}

div[data-testid="stButton"] > button {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    min-height: 44px !important;
    font-size: 14px !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stButton"] > button:active {
    background: #0D1F33 !important;
    border-color: #58A6FF !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #1A3A5C, #0D2A45) !important;
    border-color: #58A6FF !important;
    color: #58A6FF !important;
}

div[data-testid="stRadio"] > div { gap: 6px !important; flex-wrap: wrap !important; }
div[data-testid="stRadio"] label {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    min-height: 40px !important;
    font-size: 13px !important;
    display: flex !important;
    align-items: center !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    border-color: #F0A500 !important;
    background: #1F1A0A !important;
}

div[data-testid="stAlert"] { border-radius: 8px !important; border-width: 1px !important; font-size: 13px !important; }

button[data-baseweb="tab"] {
    background: transparent !important;
    color: #6E7681 !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    font-size: 12px !important;
    padding: 8px 10px !important;
    min-height: 40px !important;
}
@media (min-width: 480px) {
    button[data-baseweb="tab"] { font-size: 13px !important; padding: 8px 16px !important; }
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #F0A500 !important;
    border-bottom-color: #F0A500 !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
    overflow-x: auto !important;
}
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { font-size: 12px !important; white-space: nowrap !important; }
div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #F0A500, #58A6FF) !important; }
div[data-testid="stSlider"] div[role="slider"] { background: #F0A500 !important; }

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1F2937, transparent);
    margin: 18px 0;
}
@supports (padding-bottom: env(safe-area-inset-bottom)) {
    .block-container { padding-bottom: calc(3rem + env(safe-area-inset-bottom)) !important; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  配置与数据管理层
# ══════════════════════════════════════════════
CONFIG_FILE = "my_fund_settings.json"
HISTORY_DIR = "fund_history_db"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50',
        'period': '每月21号', 'amount': 1100, 'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%',
        'status': '估值偏高、股息最优', 'base_strategy': '⚠️ 估值百分位偏高(>80%)。建议【维持当前定投不加仓】。', 'pe_level': 'high'
    },
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100',
        'period': '每天', 'amount': 80, 'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%',
        'status': '显著高估、轻微红利', 'base_strategy': '🚨 处于历史高位区间。建议将当前的 {plan} 【下调至 {half_amount} 元左右】。', 'pe_level': 'high'
    },
    '023882': {
        'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50',
        'period': '每周二', 'amount': 100, 'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%',
        'status': '中性偏贵、低股息', 'base_strategy': '等权观望。建议【严格执行常规计划 {plan}】。', 'pe_level': 'mid'
    },
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流',
        'period': '每周二', 'amount': 790, 'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%',
        'status': '深度低估、均衡现金流', 'base_strategy': '💎 绝对核心加仓区！建议【坚定执行当前计划 {plan}】。', 'pe_level': 'low'
    }
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

if 'fund_config' not in st.session_state:
    st.session_state.fund_config = load_config()
    for code, info in st.session_state.fund_config.items():
        if 'pe_level' not in info:
            pct = info.get('pe_percent', 50)
            info['pe_level'] = 'high' if pct >= 75 else ('low' if pct <= 40 else 'mid')

def load_local_history(fund_code):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_local_history(fund_code, data_list):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

# ══════════════════════════════════════════════
#  ⚡ 核心机制 1：无条件前置最新数据拉取
# ══════════════════════════════════════════════
def move_ants_front_latest(fund_code):
    local_data = load_local_history(fund_code)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36', 'Referer': f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html'}
    timestamp = int(time.time() * 1000)
    url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize=40&_={timestamp}"
    
    try:
        import requests as req_lib
        resp = req_lib.get(url, headers=headers, timeout=15)
        data = json.loads(resp.text)
        raw_list = data["Data"]["LSJZList"]
    except:
        return local_data, 0, "网络异常/拦截"
        
    if not raw_list:
        return local_data, 0, "无数据"
        
    new_count = 0
    existing_dates = {item['日期'] for item in local_data}
    
    for item in raw_list:
        if not item.get("FSRQ") or not item.get("DWJZ"): continue
        date_str = item["FSRQ"]
        if date_str not in existing_dates:
            try: growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
            except: growth = 0.0
            local_data.append({
                "日期": date_str, "单位净值": float(item["DWJZ"]),
                "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]), "净值增长率": growth
            })
            existing_dates.add(date_str)
            new_count += 1
            
    if new_count > 0:
        local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
        save_local_history(fund_code, local_data)
        
    return local_data, new_count, "最新前端同步完毕"

# ══════════════════════════════════════════════
#  ⚡ 核心机制 2：锚定本地终点连续深度向下挖掘机制
# ══════════════════════════════════════════════
def move_ants_deep_history(fund_code, start_page=1, max_pages=2):
    local_data = load_local_history(fund_code)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    total_new_inserted = 0
    pages_actually_dug = 0
    
    for offset in range(max_pages):
        current_page = start_page + offset
        timestamp = int(time.time() * 1000)
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex={current_page}&pageSize=40&_={timestamp}"
        
        try:
            import requests as req_lib
            resp = req_lib.get(url, headers=headers, timeout=15)
            data = json.loads(resp.text)
            raw_list = data["Data"]["LSJZList"]
        except:
            break
            
        if not raw_list: break
        pages_actually_dug += 1
        existing_dates = {item['日期'] for item in local_data}
        
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): continue
            date_str = item["FSRQ"]
            if date_str not in existing_dates:
                try: growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
                except: growth = 0.0
                local_data.append({
                    "日期": date_str, "单位净值": float(item["DWJZ"]),
                    "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]), "净值增长率": growth
                })
                existing_dates.add(date_str)
                total_new_inserted += 1
        time.sleep(random.uniform(1.2, 1.9))

    if total_new_inserted > 0:
        local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
        save_local_history(fund_code, local_data)
        
    return local_data, total_new_inserted, f"从第 {start_page} 页连续深挖了 {pages_actually_dug} 页"

# ══════════════════════════════════════════════
#  看板顶部核心资产概览
# ══════════════════════════════════════════════
total_monthly = sum(
    (info['amount'] * 21 if info['period'] == '每天' else info['amount'] * 4.3 if '周' in info['period'] else info['amount'])
    for info in st.session_state.fund_config.values()
)
st.markdown(f"""
<div class="dash-header">
    <h1>📊 定投监控看板</h1>
    <div class="subtitle">
        {len(st.session_state.fund_config)} 只核心资产 &nbsp;·&nbsp; 月定投估算 <span style="color:#F0A500;font-weight:600">{total_monthly:,.0f}</span> 元<br>
        智能双向吞噬挖掘引擎已就绪
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  § 1  核心资产卡片层
# ══════════════════════════════════════════════
st.markdown('<div class="section-label">资产配置 · 智能执行状态</div>', unsafe_allow_html=True)
for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']}  {info['amount']} 元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    lvl = info.get('pe_level', 'mid')
    pct_val = info['pe_percent']
    pct_cls = 'high' if pct_val >= 75 else ('low' if pct_val <= 40 else 'mid')

    st.markdown(f"""
    <div class="fund-card status-{lvl}">
        <div class="fund-card-header">
            <div>
                <div class="fund-name">{info['name']}</div>
                <div class="fund-code">{code} · {info['index_name']}</div>
            </div>
            <div class="fund-plan-badge">{plan_str}</div>
        </div>
        <div class="metrics-row">
            <div class="metric-cell">
                <div class="metric-label">PE百分位 (10Y)</div>
                <div class="metric-value {pct_cls}">{pct_val:.1f}%</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">当前 PE (TTM)</div>
                <div class="metric-value">{info['pe_ttm']:.2f}</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">TTM 股息率</div>
                <div class="metric-value {lvl}">{info['div_yield']}</div>
            </div>
        </div>
        <div class="strategy-box {lvl}">{strategy_str}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  § 2  综合管理控制台
# ══════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">数据仓储与策略管理</div>', unsafe_allow_html=True)

edit_code = st.selectbox("当前操作项目", list(st.session_state.fund_config.keys()), format_func=lambda x: f"[{x}]  {st.session_state.fund_config[x]['name']}")
current_info = st.session_state.fund_config[edit_code]
op_mode = st.radio("系统功能切换", ["📝 修改计划", "🔄 智能智能搬家", "📋 批量导入", "➕ 增删管理"], horizontal=True)

st.markdown('<div class="console-card">', unsafe_allow_html=True)

if op_mode == "📝 修改计划":
    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1: new_period = st.text_input("定投周期", value=current_info['period'])
        with c2: new_amount = st.number_input("定投金额（元）", value=int(current_info['amount']), step=10)
        c3, c4 = st.columns(2)
        with c3: new_pe_ttm = st.number_input("当前 PE (TTM)", value=float(current_info['pe_ttm']), step=0.01, format="%.2f")
        with c4: new_pe_pct = st.number_input("PE 百分位（%）", value=float(current_info['pe_percent']), step=0.1, format="%.2f")
        new_div = st.text_input("TTM 股息率", value=current_info['div_yield'])
        new_strategy = st.text_area("执行策略模板描述", value=current_info['base_strategy'], height=80)
        if st.form_submit_button("💾 覆盖保存配置"):
            st.session_state.fund_config[edit_code].update({
                'period': new_period, 'amount': new_amount, 'pe_ttm': new_pe_ttm, 'pe_percent': new_pe_pct,
                'div_yield': new_div, 'base_strategy': new_strategy, 'pe_level': 'high' if new_pe_pct >= 75 else ('low' if new_pe_pct <= 40 else 'mid')
            })
            save_config(st.session_state.fund_config)
            st.success("✅ 资产卡片联动策略已更新")
            st.rerun()

elif op_mode == "🔄 智能智能搬家":
    st.markdown("**双向智能合并对齐系统**")
    st.caption("逻辑机制：1. 抓取网页第1页对比本地最新，确保最前方无缝合并； 2. 统计本地已有行数计算历史断点，直接从断流页码向下打井深挖。")

    if 'migration_log' in st.session_state and st.session_state.migration_log:
        total_new = st.session_state.migration_log.get('total_new', 0)
        if total_new > 0: st.success(f"🎉 引擎本次共捕捉并安全存盘了 {total_new} 条新历史数据！")
        else: st.warning("ℹ️ 本次检测未发现未抓取的深层历史。")
        for l in st.session_state.migration_log.get('lines', []): st.markdown(l)
        if st.button("🗑️ 清空运行日志"):
            st.session_state.migration_log = {}
            st.rerun()
        st.markdown("---")

    max_pages = st.slider("单只基金向下开辟深度的页数（每页40条）", 1, 5, 2)

    if st.button("🚀 启动全员双向智能吞吞合拢", type="primary"):
        all_codes = list(st.session_state.fund_config.keys())
        bar = st.progress(0)
        live_status = st.empty()
        total_new = 0
        log_lines = []

        for idx, code in enumerate(all_codes):
            fname = st.session_state.fund_config[code]['name']
            live_status.info(f"⏳ 正在执行 [{code}] {fname} 前端最新对齐...")
            
            # 1. 优先捕获前置最新数据
            local_db, new_front_count, _ = move_ants_front_latest(code)
            
            # 2. 锚定本地数据库总行数，计算精准深挖起点页码
            local_total_count = len(local_db)
            calculated_start_page = max(1, (local_total_count // 40) + 1)
            
            # 如果本地是完全空白状态，强制深挖时从第2页继续承接
            if new_front_count > 25 and calculated_start_page == 1:
                calculated_start_page = 2
                
            live_status.info(f"⛏️ 正在从第 {calculated_start_page} 页连续向历史更深处开凿...")
            _, new_deep_count, debug_info = move_ants_deep_history(fund_code=code, start_page=calculated_start_page, max_pages=max_pages)
            
            this_fund_total = new_front_count + new_deep_count
            total_new += this_fund_total
            
            bar.progress((idx + 1) / len(all_codes))
            icon = "🔥" if this_fund_total > 0 else "ℹ️"
            log_lines.append(f"{icon} **[{code}]** {debug_info}：最新前增 +{new_front_count}，断点深挖 +{new_deep_count} (本地总存量: {len(load_local_history(code))} 条)")

        live_status.empty()
        bar.empty()
        st.session_state.migration_log = {'total_new': total_new, 'lines': log_lines}
        st.rerun()

elif op_mode == "📋 批量导入":
    st.markdown(f"**多源清洗分流文本通道**（支持混贴，若单行不含6位代码则归入当前基金：**{current_info['name']}**）")
    raw_text = st.text_area("在此粘贴网页或Excel表格复制的数据明细", height=150, placeholder="例如：\n2026-07-03   1.2345   -0.12%\n008163   2026-07-02   1.2110")
    if st.button("⚡ 自动解析注入", type="primary"):
        if not raw_text.strip(): st.error("⚠️ 缓冲区内未发现任何文本输入")
        else:
            lines = raw_text.split('\n')
            memory_db = {c: load_local_history(c) for c in st.session_state.fund_config}
            import_details = {c: 0 for c in st.session_state.fund_config}
            pattern = re.compile(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s+([0-9.]+)')
            code_pattern = re.compile(r'\b(\d{6})\b')
            
            for line in lines:
                m = pattern.search(line)
                if not m: continue
                raw_date = m.group(1).replace('/', '-').replace('.', '-')
                parts = raw_date.split('-')
                standard_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                try:
                    dwjz = float(m.group(2))
                    gm = re.search(r'([-+]?[0-9.]+)%', line)
                    growth = float(gm.group(1)) if gm else 0.0
                    target = edit_code
                    cm = code_pattern.search(line)
                    if cm and cm.group(1) in memory_db: target = cm.group(1)
                    
                    memory_db[target] = [i for i in memory_db[target] if i['日期'] != standard_date]
                    memory_db[target].append({"日期": standard_date, "单位净值": dwjz, "累计净值": dwjz, "净值增长率": growth})
                    import_details[target] += 1
                except: continue
                
            total = 0
            for c, cnt in import_details.items():
                if cnt > 0:
                    memory_db[c] = sorted(memory_db[c], key=lambda x: x['日期'], reverse=True)
                    save_local_history(c, memory_db[c])
                    total += cnt
            if total > 0:
                st.success(f"🎉 成功清洗合并： " + " ".join(f"[{c}]:+{n}条" for c, n in import_details.items() if n > 0))
                st.rerun()
            else: st.error("❌ 格式不匹配，无法提取到合法的日期和净值数据")

else:
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown("##### ➕ 新增项目建档")
        with st.form("add_form"):
            add_code = st.text_input("基金代码", max_chars=6)
            add_name = st.text_input("基金简称")
            add_index = st.text_input("跟踪标的指数")
            r2c1, r2c2 = st.columns(2)
            with r2c1: add_period = st.text_input("定投周期", value="每周二")
            with r2c2: add_amount = st.number_input("定投面额", value=100, step=10)
            if st.form_submit_button("确认创建"):
                if len(add_code) != 6 or not add_name: st.error("⚠️ 代码或简称不合规")
                else:
                    st.session_state.fund_config[add_code] = {
                        'name': add_name, 'index_name': add_index or '自选指数', 'period': add_period, 'amount': add_amount,
                        'pe_ttm': 20.0, 'pe_percent': 50.0, 'div_yield': '1.50%', 'status': '新录入观测',
                        'base_strategy': '🎯 建议【严格执行常规计划 {plan}】。', 'pe_level': 'mid'
                    }
                    save_config(st.session_state.fund_config)
                    st.success(f"✅ [{add_code}] 空白档案已创建")
                    st.rerun()

    with c_del:
        st.markdown("##### 🗑️ 物理抹除资产")
        del_target = st.selectbox("选择销毁目标", list(st.session_state.fund_config.keys()), format_func=lambda x: f"[{x}] {st.session_state.fund_config[x]['name']}", key="del_sel")
        confirm = st.checkbox("🔥 我确认同时抹除该基金全部JSON历史数据流水且不可逆")
        if st.button("彻底安全擦除", disabled=not confirm):
            del st.session_state.fund_config[del_target]
            save_config(st.session_state.fund_config)
            hist = os.path.join(HISTORY_DIR, f"{del_target}_hist.json")
            if os.path.exists(hist):
                try: os.remove(hist)
                except: pass
            st.success(f"🧹 [{del_target}] 及其本地数据库已全部粉碎")
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  § 3  多维视窗走势分析（Altair 冷调图表穿透）
# ══════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-label">走势穿透线 · {st.session_state.fund_config[edit_code]["name"]}</div>', unsafe_allow_html=True)

current_db = load_local_history(edit_code)

if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')

    # 计算全局多维指标边界
    df_global = df_raw.groupby('月份').agg(月度平均价中枢=('单位净值', 'mean'), 当月最高价边界=('单位净值', 'max')).reset_index()
    df_enriched = pd.merge(df_raw, df_global, on='月份', how='left')

    time_frame = st.radio("视窗过滤", ["近1个月", "近3个月", "近6个月", "近1年", "全部历史"], horizontal=True, index=4)
    latest = df_enriched['日期'].max()
    day_map = {"近1个月": 30, "近3个月": 90, "近6个月": 180, "近1年": 365}
    df_f = df_enriched[df_enriched['日期'] >= (latest - pd.Timedelta(days=day_map[time_frame]))] if time_frame in day_map else df_enriched.copy()

    if not df_f.empty:
        c_ck, c_mn, c_mx = st.columns([1, 1, 1])
        with c_ck: manual_y = st.checkbox("手动锁定坐标轴边界", value=False)
        cur_min, cur_max = float(df_f['单位净值'].min()), float(df_f['当月最高价边界'].max())
        pad = (cur_max - cur_min) * 0.08 if cur_max != cur_min else 0.05
        with c_mn: y_min = st.number_input("轴线下限", value=round(cur_min - pad, 2), step=0.02, disabled=not manual_y)
        with c_mx: y_max = st.number_input("轴线上限", value=round(cur_max + pad, 2), step=0.02, disabled=not manual_y)

        df_melted = df_f.melt(id_vars=['日期'], value_vars=['单位净值', '月度平均价中枢', '当月最高价边界'], var_name='指标', value_name='净值')
        y_scale = alt.Scale(domain=[y_min, y_max], clamp=True) if manual_y else alt.Scale(zero=False, padding=15)
        color_scale = alt.Scale(domain=['单位净值', '月度平均价中枢', '当月最高价边界'], range=['#58A6FF', '#2DA44E', '#F85149'])
        
        chart = (
            alt.Chart(df_melted).mark_line(strokeWidth=1.8).encode(
                x=alt.X('日期:T', title='', axis=alt.Axis(labelColor='#6E7681', gridColor='#1F2937', domainColor='#1F2937')),
                y=alt.Y('净值:Q', title='', scale=y_scale, axis=alt.Axis(labelColor='#6E7681', gridColor='#1F2937', domainColor='#1F2937')),
                color=alt.Color('指标:N', scale=color_scale, legend=alt.Legend(title="", labelColor='#C9D1D9', orient='top-right')),
                tooltip=['日期:T', '指标:N', alt.Tooltip('净值:Q', format='.4f')]
            )
            .properties(height=260, background='#0D1117')
            .configure_view(strokeOpacity=0).configure_axis(labelFont='Inter', titleFont='Inter').interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    tab_y, tab_m, tab_d = st.tabs(["📅 年度数据归档", "🌙 月度价格中枢", "📄 逐日细分账目"])

    with tab_y:
        df_year = df_raw.groupby('年份').agg(追踪天数=('日期', 'count'), 累计波动率=('净值增长率', 'sum'), 区间最大值=('单位净值', 'max'), 区间最低值=('单位净值', 'min')).reset_index().sort_values('年份', ascending=False)
        df_year['累计波动率'] = df_year['累计波动率'].map(lambda x: f"{x:+.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)

    with tab_m:
        df_month = df_raw.groupby('月份').agg(价格中枢=('单位净值', 'mean'), 月度峰值=('单位净值', 'max'), 累计波动=('净值增长率', 'sum')).reset_index().sort_values('月份', ascending=False)
        df_month['价格中枢'] = df_month['价格中枢'].map(lambda x: f"{x:.4f}")
        df_month['月度峰值'] = df_month['月度峰值'].map(lambda x: f"{x:.4f}")
        df_month['累计波动'] = df_month['累计波动'].map(lambda x: f"{x:+.2f}%")
        st.dataframe(df_month, use_container_width=True, hide_index=True)

    with tab_d:
        df_d = df_raw.copy().sort_values('日期', ascending=False)
        df_d['日期'] = df_d['日期'].dt.strftime('%Y-%m-%d')
        df_d['净值增长率'] = df_d['净值增长率'].map(lambda x: f"{x:+.2f}%")
        st.dataframe(df_d[['日期', '单位净值', '累计净值', '净值增长率']], use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div class="strategy-box info">
    💡 当前资产本地历史数据为空。<br>
    请使用上方控制台 <strong>【📋 批量导入】</strong> 直接复制贴入，或点击 <strong>【🔄 智能智能搬家】</strong> 激活引擎自动打井深挖历史。
    </div>
    """, unsafe_allow_html=True)
