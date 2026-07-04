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
#  全局样式：暗色金融终端风格
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
/* 桌面端宽一些 */
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

/* 卡片头部：移动端竖排，桌面端横排 */
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

/* ── 指标网格：移动端自适应 ── */
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

/* ── Streamlit 原生控件：手机端放大触控区 ── */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input,
div[data-testid="stTextArea"] > div > textarea {
    background-color: #161B22 !important;
    border-color: #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
    font-size: 16px !important; /* 防 iOS 自动缩放 */
}
div[data-testid="stTextArea"] > div > textarea:focus,
div[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #58A6FF !important;
    box-shadow: 0 0 0 2px #58A6FF22 !important;
}

/* 按钮：最小 44px 高度符合触控规范 */
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

/* Radio：移动端自动换行，不溢出 */
div[data-testid="stRadio"] > div {
    gap: 6px !important;
    flex-wrap: wrap !important;
}
div[data-testid="stRadio"] label {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    min-height: 40px !important;
    font-size: 13px !important;
    display: flex !important;
    align-items: center !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    border-color: #F0A500 !important;
    background: #1F1A0A !important;
}

/* info/success/error */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-width: 1px !important;
    font-size: 13px !important;
}

/* Tab：移动端小字 */
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
    background: transparent !important;
}

/* Dataframe：横向滚动 */
[data-testid="stDataFrame"] {
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
}
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
    font-size: 12px !important;
    white-space: nowrap !important;
}

/* Progress */
div[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #F0A500, #58A6FF) !important;
}

/* Slider */
div[data-testid="stSlider"] div[role="slider"] { background: #F0A500 !important; }
div[data-testid="stSlider"] { padding: 4px 0 !important; }

/* Checkbox：放大触控区 */
label[data-testid="stCheckbox"] {
    color: #C9D1D9 !important;
    min-height: 40px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
label[data-testid="stCheckbox"] > span { font-size: 14px !important; }

/* Metric */
div[data-testid="stMetric"] {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 10px;
    padding: 12px !important;
}
div[data-testid="stMetric"] label { color: #6E7681 !important; font-size: 11px !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 18px !important;
    color: #E6EDF3 !important;
}

/* HR 替代 */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1F2937, transparent);
    margin: 18px 0;
}
@media (min-width: 768px) {
    .divider { margin: 24px 0; }
}

/* ── 底部安全区（iOS Home Indicator） ── */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
    .block-container {
        padding-bottom: calc(3rem + env(safe-area-inset-bottom)) !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  配置 & 数据层（保持原逻辑不变）
# ══════════════════════════════════════════════
CONFIG_FILE = "my_fund_settings.json"
HISTORY_DIR = "fund_history_db"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A',
        'index_name': '标普红利低波50',
        'period': '每月21号', 'amount': 1100,
        'pe_ttm': 8.22, 'pe_percent': 84.82,
        'div_yield': '4.85%',
        'status': '估值偏高、股息最优',
        'base_strategy': '⚠️ 估值百分位偏高(>80%)。建议【维持当前定投不加仓】。',
        'pe_level': 'high'
    },
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A',
        'index_name': '纳斯达克100',
        'period': '每天', 'amount': 80,
        'pe_ttm': 34.03, 'pe_percent': 76.97,
        'div_yield': '0.36%',
        'status': '显著高估、轻微红利',
        'base_strategy': '🚨 处于历史高位区间。建议将当前的 {plan} 【下调至 {half_amount} 元左右】。',
        'pe_level': 'high'
    },
    '023882': {
        'name': '华夏创业板50ETF发起式联接A',
        'index_name': '创业板50',
        'period': '每周二', 'amount': 100,
        'pe_ttm': 44.48, 'pe_percent': 60.78,
        'div_yield': '0.80%',
        'status': '中性偏贵、低股息',
        'base_strategy': '等权观望。建议【严格执行常规计划 {plan}】。',
        'pe_level': 'mid'
    },
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A',
        'index_name': '国证自由现金流',
        'period': '每周二', 'amount': 790,
        'pe_ttm': 11.68, 'pe_percent': 30.77,
        'div_yield': '3.20%',
        'status': '深度低估、均衡现金流',
        'base_strategy': '💎 绝对核心加仓区！建议【坚定执行当前计划 {plan}】。',
        'pe_level': 'low'
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

if 'fund_config' not in st.session_state:
    st.session_state.fund_config = load_config()
    # 补全旧配置缺失的 pe_level 字段
    for code, info in st.session_state.fund_config.items():
        if 'pe_level' not in info:
            pct = info.get('pe_percent', 50)
            info['pe_level'] = 'high' if pct >= 75 else ('low' if pct <= 40 else 'mid')

def load_local_history(fund_code):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_local_history(fund_code, data_list):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

def move_ants_history(fund_code, page_index=1):
    local_data = load_local_history(fund_code)
    
    # 完整请求头，缺任何一项都可能被拦截
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html',
        'Origin': 'https://fundf10.eastmoney.com',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    timestamp = int(time.time() * 1000)
    url = (
        f"https://api.fund.eastmoney.com/f10/lsjz"
        f"?fundCode={fund_code}&pageIndex={page_index}&pageSize=40&_={timestamp}"
    )
    
    # 优先用 requests（头部处理更可靠），没有就降级到 urllib
    html = None
    last_error = ""
    
    try:
        import requests as req_lib
        resp = req_lib.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        html = resp.text
    except ImportError:
        # urllib 降级路径
        try:
            request_obj = urllib.request.Request(url)
            for k, v in headers.items():
                request_obj.add_header(k, v)
            with urllib.request.urlopen(request_obj, timeout=20) as response:
                raw = response.read()
                # 自动处理 gzip 压缩响应
                import gzip as gz
                try:
                    html = gz.decompress(raw).decode('utf-8')
                except Exception:
                    html = raw.decode('utf-8')
        except Exception as e:
            last_error = str(e)
    except Exception as e:
        last_error = str(e)
    
    if html is None:
        return local_data, 0, f"网络错误: {last_error}"
    
    try:
        data = json.loads(html)
    except json.JSONDecodeError as e:
        # 返回内容不是 JSON，说明被拦截或返回了 HTML 错误页
        preview = html[:120].replace('\n', ' ')
        return local_data, 0, f"返回非JSON（可能被拦截）: {preview}"
    
    if not data or data.get("Data") is None:
        return local_data, 0, f"接口返回空 Data，可能触发限流。原始: {str(data)[:80]}"
    
    if "LSJZList" not in data["Data"]:
        return local_data, 0, f"响应缺少 LSJZList 字段，keys={list(data['Data'].keys())}"
    
    raw_list = data["Data"]["LSJZList"]
    if not raw_list:
        return local_data, 0, "无数据（该页为空）"
    
    new_count = 0
    existing_dates = {item['日期'] for item in local_data}
    for item in raw_list:
        if not item.get("FSRQ") or not item.get("DWJZ"):
            continue
        date_str = item["FSRQ"]
        if date_str not in existing_dates:
            try:
                growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
            except (ValueError, TypeError):
                growth = 0.0
            local_data.append({
                "日期": date_str,
                "单位净值": float(item["DWJZ"]),
                "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]),
                "净值增长率": growth
            })
            new_count += 1

    if new_count > 0:
        local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
        save_local_history(fund_code, local_data)
        return local_data, new_count, "成功"
    return local_data, 0, "无新数据（全部已在本地）"


# ══════════════════════════════════════════════
#  顶部 Banner
# ══════════════════════════════════════════════
total_monthly = sum(
    (info['amount'] * 21 if info['period'] == '每天' else
     info['amount'] * 4.3 if '周' in info['period'] else
     info['amount'])
    for info in st.session_state.fund_config.values()
)
fund_count = len(st.session_state.fund_config)

st.markdown(f"""
<div class="dash-header">
    <h1>📊 定投监控看板</h1>
    <div class="subtitle">
        {fund_count} 只基金 &nbsp;·&nbsp; 月投约 <span style="color:#F0A500;font-weight:600">{total_monthly:,.0f}</span> 元<br>
        智能估值感知 · 实时净值追踪
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  § 1  核心资产卡片
# ══════════════════════════════════════════════
st.markdown('<div class="section-label">核心资产 · 智能执行状态</div>', unsafe_allow_html=True)

def pe_level(info):
    return info.get('pe_level', 'mid')

for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']}  {info['amount']} 元"
    strategy_str = info['base_strategy'].format(
        plan=plan_str, half_amount=int(info['amount'] / 2)
    )
    lvl = pe_level(info)
    # 百分位颜色
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
st.markdown('<div class="section-label">综合管理控制台</div>', unsafe_allow_html=True)

edit_code = st.selectbox(
    "当前操作基金",
    list(st.session_state.fund_config.keys()),
    format_func=lambda x: f"[{x}]  {st.session_state.fund_config[x]['name']}"
)
current_info = st.session_state.fund_config[edit_code]

op_mode = st.radio(
    "功能模块",
    ["📝 修改定投计划", "🔄 智能搬家", "📋 批量导入", "➕ 增删基金"],
    horizontal=True
)

st.markdown('<div class="console-card">', unsafe_allow_html=True)

if op_mode == "📝 修改定投计划":
    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_period = st.text_input("定投周期", value=current_info['period'])
        with c2:
            new_amount = st.number_input("定投金额（元）", value=int(current_info['amount']), step=10)
        c3, c4 = st.columns(2)
        with c3:
            new_pe_ttm = st.number_input("当前 PE (TTM)", value=float(current_info['pe_ttm']), step=0.01, format="%.2f")
        with c4:
            new_pe_pct = st.number_input("PE 百分位（%）", value=float(current_info['pe_percent']), step=0.1, format="%.2f")
        new_div = st.text_input("TTM 股息率（如 4.85%）", value=current_info['div_yield'])
        new_strategy = st.text_area("执行策略描述", value=current_info['base_strategy'], height=80)
        submitted = st.form_submit_button("💾 保存更新")
        if submitted:
            st.session_state.fund_config[edit_code].update({
                'period': new_period,
                'amount': new_amount,
                'pe_ttm': new_pe_ttm,
                'pe_percent': new_pe_pct,
                'div_yield': new_div,
                'base_strategy': new_strategy,
                'pe_level': 'high' if new_pe_pct >= 75 else ('low' if new_pe_pct <= 40 else 'mid')
            })
            save_config(st.session_state.fund_config)
            st.success("✅ 配置已保存")
            st.rerun()

elif op_mode == "🔄 智能搬家":
    st.markdown("**全员历史净值追溯**（爬取东方财富，含防反爬延迟）")

    # 持久化显示上次运行结果
    if 'migration_log' in st.session_state and st.session_state.migration_log:
        total_new = st.session_state.migration_log.get('total_new', 0)
        lines = st.session_state.migration_log.get('lines', [])
        if total_new > 0:
            st.success(f"✅ 上次搬运共写入 {total_new} 条新数据")
        else:
            st.warning("⚠️ 上次搬运未写入新数据，详见下方日志")
        for l in lines:
            st.markdown(l)
        if st.button("🗑️ 清除日志"):
            st.session_state.migration_log = {}
            st.rerun()
        st.markdown("---")

    max_pages = st.slider("追溯深度（页数，每页40条）", 1, 5, 2)

    col_test, col_run = st.columns(2)
    with col_test:
        if st.button("🔍 先测试网络连通性"):
            with st.spinner("测试中…"):
                test_url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=008163&pageIndex=1&pageSize=5"
                try:
                    import requests as rlib
                    r = rlib.get(test_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': 'https://fundf10.eastmoney.com/lsjz_008163.html',
                        'Accept': 'application/json, */*',
                    }, timeout=15)
                    if r.status_code == 200 and 'LSJZList' in r.text:
                        st.success(f"✅ 网络正常，接口可达（HTTP {r.status_code}）")
                    else:
                        st.error(f"❌ 接口响应异常：HTTP {r.status_code}，内容：{r.text[:100]}")
                except Exception as e:
                    st.error(f"❌ 连接失败：{e}")

    with col_run:
        if st.button("🚀 启动全员搬运", type="primary"):
            all_codes = list(st.session_state.fund_config.keys())
            total_steps = len(all_codes) * max_pages
            step_now = 0
            bar = st.progress(0)
            live_status = st.empty()
            total_new = 0
            log_lines = []

            for code in all_codes:
                fname = st.session_state.fund_config[code]['name']
                for p in range(1, max_pages + 1):
                    step_now += 1
                    live_status.info(f"⏳ [{code}] {fname} · 第 {p}/{max_pages} 页…")
                    _, n, msg = move_ants_history(code, page_index=p)
                    total_new += n
                    bar.progress(step_now / total_steps)
                    icon = "✅" if n > 0 else ("ℹ️" if "无新数据" in msg else "⚠️")
                    log_lines.append(f"{icon} **[{code}]** 第{p}页：{msg}（+{n}条）")
                    time.sleep(random.uniform(1.5, 2.8))

            live_status.empty()
            bar.empty()

            # 结果存入 session_state，刷新后仍可见
            st.session_state.migration_log = {
                'total_new': total_new,
                'lines': log_lines,
            }
            st.rerun()

elif op_mode == "📋 批量导入":
    st.markdown(f"""
    **智能分流粘贴通道**  
    含 6 位基金代码的行自动归入对应基金；无代码则默认归入：**{current_info['name']}**
    """)
    raw_text = st.text_area(
        "粘贴历史净值数据",
        height=160,
        placeholder="示例（可混贴多只）：\n008163  2026-07-03  1.2345\n016452  2026-07-03  2.5640\n2026-07-02  1.2210"
    )
    if st.button("⚡ 清洗并导入", type="primary"):
        if not raw_text.strip():
            st.error("⚠️ 内容为空，请先粘贴数据")
        else:
            lines = raw_text.split('\n')
            memory_db = {c: load_local_history(c) for c in st.session_state.fund_config}
            import_details = {c: 0 for c in st.session_state.fund_config}
            pattern = re.compile(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s+([0-9.]+)')
            code_pattern = re.compile(r'\b(\d{6})\b')
            for line in lines:
                m = pattern.search(line)
                if not m:
                    continue
                raw_date = m.group(1).replace('/', '-').replace('.', '-')
                parts = raw_date.split('-')
                standard_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                try:
                    dwjz = float(m.group(2))
                    gm = re.search(r'([-+]?[0-9.]+)%', line)
                    growth = float(gm.group(1)) if gm else 0.0
                    target = edit_code
                    cm = code_pattern.search(line)
                    if cm and cm.group(1) in memory_db:
                        target = cm.group(1)
                    memory_db[target] = [i for i in memory_db[target] if i['日期'] != standard_date]
                    memory_db[target].append({"日期": standard_date, "单位净值": dwjz, "累计净值": dwjz, "净值增长率": growth})
                    import_details[target] += 1
                except:
                    continue
            total = 0
            for c, cnt in import_details.items():
                if cnt > 0:
                    memory_db[c] = sorted(memory_db[c], key=lambda x: x['日期'], reverse=True)
                    save_local_history(c, memory_db[c])
                    total += cnt
            if total > 0:
                msg = f"✅ 写入 {total} 条：" + "  ".join(f"[{c}] +{n}" for c, n in import_details.items() if n > 0)
                st.success(msg)
                st.rerun()
            else:
                st.error("⚠️ 未识别到有效数据，请检查格式")

else:
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown("##### ➕ 添加基金")
        with st.form("add_form"):
            add_code = st.text_input("基金代码（6位）", max_chars=6)
            add_name = st.text_input("基金简称")
            add_index = st.text_input("关联指数名称")
            r2c1, r2c2 = st.columns(2)
            with r2c1: add_period = st.text_input("定投周期", value="每周二")
            with r2c2: add_amount = st.number_input("定投金额（元）", value=100, step=10)
            if st.form_submit_button("添加入库"):
                if len(add_code) != 6 or not add_name:
                    st.error("⚠️ 请填写完整的代码和简称")
                else:
                    st.session_state.fund_config[add_code] = {
                        'name': add_name, 'index_name': add_index or '自定义',
                        'period': add_period, 'amount': add_amount,
                        'pe_ttm': 20.0, 'pe_percent': 50.0,
                        'div_yield': '1.50%', 'status': '新入库',
                        'base_strategy': '🎯 建议【严格执行常规计划 {plan}】。',
                        'pe_level': 'mid'
                    }
                    save_config(st.session_state.fund_config)
                    st.success(f"✅ [{add_code}] 已添加")
                    st.rerun()

    with c_del:
        st.markdown("##### 🗑️ 删除基金")
        del_target = st.selectbox(
            "选择要删除的基金",
            list(st.session_state.fund_config.keys()),
            format_func=lambda x: f"[{x}] {st.session_state.fund_config[x]['name']}",
            key="del_sel"
        )
        confirm = st.checkbox("⚠️ 我确认此操作不可逆")
        if st.button("🔥 永久删除", disabled=not confirm):
            del st.session_state.fund_config[del_target]
            save_config(st.session_state.fund_config)
            hist = os.path.join(HISTORY_DIR, f"{del_target}_hist.json")
            if os.path.exists(hist):
                try:
                    os.remove(hist)
                except:
                    pass
            st.success(f"✅ [{del_target}] 及历史数据已删除")
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  § 3  历史走势穿透面板
# ══════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-label">走势穿透 · {st.session_state.fund_config[edit_code]["name"]}</div>', unsafe_allow_html=True)

current_db = load_local_history(edit_code)

if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')

    df_global = df_raw.groupby('月份').agg(
        月度平均价中枢=('单位净值', 'mean'),
        当月最高价边界=('单位净值', 'max')
    ).reset_index()
    df_enriched = pd.merge(df_raw, df_global, on='月份', how='left')

    time_frame = st.radio(
        "时间视窗",
        ["近1个月", "近3个月", "近6个月", "近1年", "全部"],
        horizontal=True, index=4
    )
    latest = df_enriched['日期'].max()
    day_map = {"近1个月": 30, "近3个月": 90, "近6个月": 180, "近1年": 365}
    if time_frame in day_map:
        df_f = df_enriched[df_enriched['日期'] >= (latest - pd.Timedelta(days=day_map[time_frame]))]
    else:
        df_f = df_enriched.copy()

    if not df_f.empty:
        c_ck, c_mn, c_mx = st.columns([1, 1, 1])
        with c_ck:
            manual_y = st.checkbox("手动锁定纵轴", value=False)
        cur_min = float(df_f['单位净值'].min())
        cur_max = float(df_f['当月最高价边界'].max())
        pad = (cur_max - cur_min) * 0.08 if cur_max != cur_min else 0.05
        with c_mn:
            y_min = st.number_input("Y轴下限", value=round(cur_min - pad, 2), step=0.02, disabled=not manual_y)
        with c_mx:
            y_max = st.number_input("Y轴上限", value=round(cur_max + pad, 2), step=0.02, disabled=not manual_y)

        df_melted = df_f.melt(
            id_vars=['日期'],
            value_vars=['单位净值', '月度平均价中枢', '当月最高价边界'],
            var_name='指标', value_name='净值'
        )
        y_scale = alt.Scale(domain=[y_min, y_max], clamp=True) if manual_y else alt.Scale(zero=False, padding=15)
        color_scale = alt.Scale(
            domain=['单位净值', '月度平均价中枢', '当月最高价边界'],
            range=['#58A6FF', '#2DA44E', '#F85149']
        )
        chart = (
            alt.Chart(df_melted)
            .mark_line(strokeWidth=1.8)
            .encode(
                x=alt.X('日期:T', title='', axis=alt.Axis(labelColor='#6E7681', gridColor='#1F2937', domainColor='#1F2937')),
                y=alt.Y('净值:Q', title='单位净值', scale=y_scale, axis=alt.Axis(labelColor='#6E7681', gridColor='#1F2937', domainColor='#1F2937')),
                color=alt.Color('指标:N', scale=color_scale, legend=alt.Legend(title="", labelColor='#C9D1D9', orient='top-right')),
                tooltip=['日期:T', '指标:N', alt.Tooltip('净值:Q', format='.4f')]
            )
            .properties(height=280, background='#0D1117')
            .configure_view(strokeOpacity=0)
            .configure_axis(labelFont='Inter', titleFont='Inter')
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    tab_y, tab_m, tab_d = st.tabs(["📅 年度汇总", "🌙 月度中枢", "📄 逐日明细"])

    with tab_y:
        df_year = df_raw.groupby('年份').agg(
            记录天数=('日期', 'count'),
            期间涨跌=('净值增长率', 'sum'),
            最高净值=('单位净值', 'max'),
            最低净值=('单位净值', 'min')
        ).reset_index().sort_values('年份', ascending=False)
        df_year['期间涨跌'] = df_year['期间涨跌'].map(lambda x: f"{x:+.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)

    with tab_m:
        df_month = df_raw.groupby('月份').agg(
            月均净值=('单位净值', 'mean'),
            月度最高=('单位净值', 'max'),
            累计波动=('净值增长率', 'sum')
        ).reset_index().sort_values('月份', ascending=False)
        df_month['月均净值'] = df_month['月均净值'].map(lambda x: f"{x:.4f}")
        df_month['月度最高'] = df_month['月度最高'].map(lambda x: f"{x:.4f}")
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
    💡 该基金本地数据库为空。<br>
    请使用上方控制台的 <strong>【批量导入】</strong> 粘贴历史净值，
    或使用 <strong>【智能搬家】</strong> 自动从东方财富抓取数据。
    </div>
    """, unsafe_allow_html=True)
