import streamlit as st
import pandas as pd
import urllib.request
import json
import os
import time
import random
import re
import altair as alt

# ──────────────────────────────────────────────
# 页面配置
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="智能定投监控看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────────
# 全局 CSS —— 高端金融暗色主题
# ──────────────────────────────────────────────
st.markdown("""
<style>
    /* ── 根变量 ── */
    :root {
        --bg-root: #0b0d11;
        --bg-surface: #13161d;
        --bg-card: #191d26;
        --bg-elevated: #1e2230;
        --border-subtle: #262b38;
        --border-default: #333a4a;
        --text-primary: #e8ecf1;
        --text-secondary: #8b93a5;
        --text-tertiary: #5c6478;
        --accent-gold: #d4a853;
        --accent-gold-dim: #8b6d2f;
        --accent-teal: #2dd4bf;
        --accent-rose: #f87171;
        --accent-green: #4ade80;
        --accent-blue: #60a5fa;
        --shadow-card: 0 1px 3px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.35);
        --shadow-elevated: 0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04);
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
    }

    /* ── 全局重置 ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}

    .stApp {
        background: var(--bg-root);
    }

    /* 主内容区 */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    /* ── 标题区域 ── */
    .dashboard-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 0 0 20px 0;
        margin-bottom: 8px;
    }
    .dashboard-header .icon-ring {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: linear-gradient(135deg, #d4a853 0%, #8b6d2f 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        box-shadow: 0 0 20px rgba(212, 168, 83, 0.18);
    }
    .dashboard-header h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.01em;
        margin: 0;
    }
    .dashboard-header .subtitle {
        font-size: 0.82rem;
        color: var(--text-tertiary);
        font-weight: 400;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    /* ── 区域标题 ── */
    .section-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-tertiary);
        margin: 28px 0 12px 0;
        padding-left: 2px;
        border-left: 2px solid var(--accent-gold);
        padding: 0 0 0 10px;
    }

    /* ── 基金卡片（新版） ── */
    .fund-card-v2 {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px 24px;
        margin-bottom: 0px;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .fund-card-v2:hover {
        border-color: var(--border-default);
        box-shadow: var(--shadow-elevated);
    }
    .fund-card-v2 .card-accent-bar {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        border-radius: 3px 0 0 3px;
    }
    .fund-card-v2 .card-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin-bottom: 14px;
        padding-left: 8px;
    }
    .fund-card-v2 .fund-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.01em;
    }
    .fund-card-v2 .fund-code {
        font-size: 0.7rem;
        color: var(--text-tertiary);
        font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
        letter-spacing: 0.04em;
        background: var(--bg-surface);
        padding: 2px 8px;
        border-radius: 4px;
    }
    .fund-card-v2 .card-tags {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 16px;
        padding-left: 8px;
    }
    .fund-tag-v2 {
        font-size: 0.72rem;
        font-weight: 500;
        padding: 4px 10px;
        border-radius: 5px;
        letter-spacing: 0.02em;
    }
    .tag-index {
        background: rgba(96,165,250,0.1);
        color: var(--accent-blue);
        border: 1px solid rgba(96,165,250,0.18);
    }
    .tag-plan {
        background: rgba(212,168,83,0.1);
        color: var(--accent-gold);
        border: 1px solid rgba(212,168,83,0.18);
    }
    .tag-status {
        background: rgba(45,212,191,0.08);
        color: var(--accent-teal);
        border: 1px solid rgba(45,212,191,0.15);
        font-size: 0.68rem;
    }

    /* ── 自定义 Metric ── */
    .custom-metric {
        text-align: center;
        padding: 10px 4px;
    }
    .custom-metric .metric-label {
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-tertiary);
        margin-bottom: 4px;
    }
    .custom-metric .metric-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
    }
    .custom-metric .metric-sub {
        font-size: 0.68rem;
        color: var(--text-tertiary);
        margin-top: 2px;
    }

    /* ── 策略提示条 ── */
    .strategy-banner {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 12px 16px;
        border-radius: var(--radius-md);
        margin-top: 14px;
        font-size: 0.82rem;
        line-height: 1.55;
        font-weight: 500;
    }
    .strategy-banner.caution {
        background: rgba(248,113,113,0.07);
        border: 1px solid rgba(248,113,113,0.15);
        color: #fca5a5;
    }
    .strategy-banner.warning {
        background: rgba(251,191,36,0.07);
        border: 1px solid rgba(251,191,36,0.15);
        color: #fde68a;
    }
    .strategy-banner.bullish {
        background: rgba(74,222,128,0.07);
        border: 1px solid rgba(74,222,128,0.15);
        color: #86efac;
    }
    .strategy-banner.neutral {
        background: rgba(96,165,250,0.07);
        border: 1px solid rgba(96,165,250,0.15);
        color: #93c5fd;
    }
    .strategy-banner .banner-icon {
        font-size: 1rem;
        flex-shrink: 0;
        margin-top: 1px;
    }

    /* ── 控制台 ── */
    .console-panel {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 24px;
        margin-bottom: 20px;
    }
    .console-panel .panel-header {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── Radio 美化 ── */
    div[role="radiogroup"] {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 4px;
        display: inline-flex !important;
        gap: 2px;
        border: 1px solid var(--border-subtle);
    }
    div[role="radiogroup"] label {
        padding: 6px 16px !important;
        border-radius: 7px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        cursor: pointer;
        transition: all 0.15s ease;
        color: var(--text-secondary) !important;
        margin: 0 !important;
    }
    div[role="radiogroup"] label:hover {
        color: var(--text-primary) !important;
        background: rgba(255,255,255,0.03);
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }

    /* ── 按钮 ── */
    .stButton > button {
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.01em;
        padding: 8px 20px !important;
        transition: all 0.15s ease !important;
        border: 1px solid transparent !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent-gold) !important;
        color: #0b0d11 !important;
        border-color: var(--accent-gold) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #e0b85f !important;
        box-shadow: 0 0 0 3px rgba(212,168,83,0.2);
    }
    .stButton > button[kind="secondary"] {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-default) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--text-tertiary) !important;
    }

    /* ── 输入框 ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-size: 0.84rem !important;
        padding: 9px 12px !important;
        transition: border-color 0.15s ease;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 3px rgba(212,168,83,0.1) !important;
    }
    .stTextArea textarea {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-size: 0.8rem !important;
        font-family: 'SF Mono', 'Fira Code', monospace !important;
        padding: 12px !important;
    }
    .stTextArea textarea:focus {
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 3px rgba(212,168,83,0.1) !important;
    }

    /* ── Select Box ── */
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
    }

    /* ── Slider ── */
    .stSlider > div > div > div > div {
        background: var(--accent-gold) !important;
    }

    /* ── Progress ── */
    .stProgress > div > div > div {
        background: var(--accent-gold) !important;
        border-radius: 4px !important;
    }
    .stProgress > div > div {
        background: var(--bg-elevated) !important;
        border-radius: 4px !important;
    }

    /* ── 分割线 ── */
    hr {
        border: none !important;
        height: 1px !important;
        background: var(--border-subtle) !important;
        margin: 28px 0 !important;
    }

    /* ── 表单 ── */
    div[data-testid="stForm"] {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px !important;
    }

    /* ── 透视面板 ── */
    .insight-panel {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 24px;
    }

    /* ── 手机适配 ── */
    @media (max-width: 768px) {
        .fund-card-v2 { padding: 14px 16px; }
        .fund-card-v2 .fund-name { font-size: 0.85rem; }
        .dashboard-header h1 { font-size: 1.2rem; }
        div[role="radiogroup"] { flex-wrap: wrap; }
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 标题
# ──────────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <div class="icon-ring">📊</div>
    <div>
        <h1>智能定投监控看板</h1>
        <div class="subtitle">Multi-Asset Investment Dashboard</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 数据层（完全保持原逻辑）
# ──────────────────────────────────────────────
CONFIG_FILE = "my_fund_settings.json"
HISTORY_DIR = "fund_history_db"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A',
        'index_name': '标普红利低波50',
        'period': '每月21号', 'amount': 1100,
        'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%',
        'status': '估值偏高、股息最优',
        'base_strategy': '⚠️ 估值百分位偏高(>80%)。建议【维持当前定投不加仓】。'
    },
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A',
        'index_name': '纳斯达克100',
        'period': '每天', 'amount': 80,
        'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%',
        'status': '显著高估、轻微红利',
        'base_strategy': '🚨 处于历史高位区间。建议将当前的 {plan} 【下调至 {half_amount} 元左右】。'
    },
    '023882': {
        'name': '华夏创业板50ETF发起式联接A',
        'index_name': '创业板50',
        'period': '每周二', 'amount': 100,
        'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%',
        'status': '中性偏贵、低股息',
        'base_strategy': '等权观望。建议【严格执行常规计划 {plan}】。'
    },
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A',
        'index_name': '国证自由现金流',
        'period': '每周二', 'amount': 790,
        'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%',
        'status': '深度低估、均衡现金流',
        'base_strategy': '💎 绝对核心加仓区！建议【坚定执行当前计划 {plan}】。'
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


if 'fund_config' not in st.session_state:
    st.session_state.fund_config = load_config()


def load_local_history(fund_code):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_local_history(fund_code, data_list):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)


def move_ants_history(fund_code, page_index=1):
    local_data = load_local_history(fund_code)
    try:
        timestamp = int(time.time() * 1000)
        url = (
            f"https://api.fund.eastmoney.com/f10/lsjz?"
            f"fundCode={fund_code}&pageIndex={page_index}&pageSize=40&_={timestamp}"
        )
        req = urllib.request.Request(url)
        req.add_header(
            'User-Agent',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
        data = json.loads(html)
        if not data or data.get("Data") is None or "LSJZList" not in data["Data"]:
            return local_data, 0, "限流"
        raw_list = data["Data"]["LSJZList"]
        if not raw_list:
            return local_data, 0, "无数据"
        new_count = 0
        existing_dates = {item['日期'] for item in local_data}
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"):
                continue
            date_str = item["FSRQ"]
            if date_str not in existing_dates:
                try:
                    growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
                except Exception:
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
        return local_data, 0, "无新数据"
    except Exception as e:
        return local_data, 0, f"断流({str(e)})"


def _strategy_class(info):
    """根据 base_strategy 关键词返回 banner 类型"""
    s = info.get('base_strategy', '')
    if '不加仓' in s or '下调' in s:
        return 'caution'
    if '高位' in s or '高估' in s:
        return 'warning'
    if '加仓' in s or '坚定' in s:
        return 'bullish'
    return 'neutral'


# ──────────────────────────────────────────────
# 1. 全景卡片看板
# ──────────────────────────────────────────────
st.markdown('<div class="section-label">核心资产 · 智能执行卡片</div>', unsafe_allow_html=True)

# 一行 2 列布局
fund_codes = list(st.session_state.fund_config.keys())
for i in range(0, len(fund_codes), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        idx = i + j
        if idx >= len(fund_codes):
            break
        code = fund_codes[idx]
        info = st.session_state.fund_config[code]

        plan_str = f"{info['period']} · {info['amount']}元"
        strategy_str = info['base_strategy'].format(
            plan=plan_str,
            half_amount=int(info['amount'] / 2)
        )
        banner_cls = _strategy_class(info)

        # 颜色条（根据估值百分位）
        pe_pct = info['pe_percent']
        if pe_pct > 80:
            bar_color = '#f87171'
        elif pe_pct > 60:
            bar_color = '#fbbf24'
        elif pe_pct > 30:
            bar_color = '#60a5fa'
        else:
            bar_color = '#4ade80'

        with col:
            st.markdown(f"""
            <div class="fund-card-v2">
                <div class="card-accent-bar" style="background:{bar_color};"></div>
                <div class="card-header">
                    <span class="fund-name">{info['name']}</span>
                    <span class="fund-code">{code}</span>
                </div>
                <div class="card-tags">
                    <span class="fund-tag-v2 tag-index">📐 {info['index_name']}</span>
                    <span class="fund-tag-v2 tag-plan">📋 {plan_str}</span>
                    <span class="fund-tag-v2 tag-status">{info['status']}</span>
                </div>
            """, unsafe_allow_html=True)

            # 三列指标
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"""
                <div class="custom-metric">
                    <div class="metric-label">10Y PE 百分位</div>
                    <div class="metric-value" style="color:{bar_color};">{pe_pct:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="custom-metric">
                    <div class="metric-label">当前 PE</div>
                    <div class="metric-value">{info['pe_ttm']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="custom-metric">
                    <div class="metric-label">TTM 股息率</div>
                    <div class="metric-value" style="color:var(--accent-gold);">{info['div_yield']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="strategy-banner {banner_cls}">
                <span class="banner-icon">
                    {'🔴' if banner_cls == 'caution' else '🟡' if banner_cls == 'warning' else '🟢' if banner_cls == 'bullish' else '🔵'}
                </span>
                <span>{strategy_str}</span>
            </div>
            </div>
            """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 2. 控制台
# ──────────────────────────────────────────────
st.markdown('<div class="section-label">综合管理控制台</div>', unsafe_allow_html=True)

st.markdown('<div class="console-panel">', unsafe_allow_html=True)

edit_code = st.selectbox(
    "当前选中的基金",
    fund_codes,
    format_func=lambda x: f"{x}  {st.session_state.fund_config[x]['name']}",
    label_visibility="collapsed"
)
current_info = st.session_state.fund_config[edit_code]

st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
op_mode = st.radio(
    "操作功能",
    ["修改定投计划", "智能一键搬家", "极速批量导入", "快捷增删基金"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown('<div style="margin-top:4px;"></div>', unsafe_allow_html=True)

if op_mode == "修改定投计划":
    with st.form("my_edit_form"):
        col_p, col_a = st.columns(2)
        with col_p:
            new_period = st.text_input("定投周期", value=current_info['period'])
        with col_a:
            new_amount = st.number_input("定投金额 (元)", value=int(current_info['amount']), step=10)
        submit_plan = st.form_submit_button("确认更新并保存", type="primary")
        if submit_plan:
            st.session_state.fund_config[edit_code]['period'] = new_period
            st.session_state.fund_config[edit_code]['amount'] = new_amount
            save_config(st.session_state.fund_config)
            st.success("配置已成功保存！")
            st.rerun()

elif op_mode == "智能一键搬家":
    st.markdown("##### 全员多页联动增量搬运")
    max_pages = st.slider("搬运深度（页数）", min_value=1, max_value=5, value=2)
    if st.button("启动全员自动追溯", type="primary"):
        all_codes = list(st.session_state.fund_config.keys())
        total_steps = len(all_codes) * max_pages
        step_now = 0
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_new = 0
        for code in all_codes:
            for p_idx in range(1, max_pages + 1):
                step_now += 1
                status_text.markdown(
                    f"⏳ 正在搬运 **{st.session_state.fund_config[code]['name']}** 第 {p_idx} 页..."
                )
                _, downloaded, _ = move_ants_history(code, page_index=p_idx)
                total_new += downloaded
                progress_bar.progress(step_now / total_steps)
                time.sleep(random.uniform(1.5, 2.8))
        status_text.empty()
        if total_new > 0:
            st.success(f"成功搬运 {total_new} 条最新数据！")
        else:
            st.info("接口响应为空或已是最新状态，可尝试批量导入功能。")
        st.rerun()

elif op_mode == "极速批量导入":
    st.markdown("##### 智能多源文本批量粘贴")
    st.caption(
        f"💡 混合粘贴即可自动分流。含6位代码的行归入对应基金，"
        f"未标代码则默认归属 **{st.session_state.fund_config[edit_code]['name']}**。"
    )
    raw_paste_text = st.text_area(
        "粘贴历史数据明细",
        height=160,
        placeholder="008163  2026-07-03  1.2345\n016452  2026-07-03  2.5640\n2026-07-02  1.2210",
        label_visibility="collapsed"
    )
    if st.button("启动智能清洗并导入", type="primary"):
        if not raw_paste_text.strip():
            st.error("粘贴板为空，请先复制数据！")
        else:
            lines = raw_paste_text.split('\n')
            memory_db = {}
            for code in st.session_state.fund_config.keys():
                memory_db[code] = load_local_history(code)
            import_details = {code: 0 for code in st.session_state.fund_config.keys()}
            pattern = re.compile(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s+([0-9.]+)')
            code_pattern = re.compile(r'\b(\d{6})\b')

            for line in lines:
                match = pattern.search(line)
                if match:
                    raw_date = match.group(1).replace('/', '-').replace('.', '-')
                    parts = raw_date.split('-')
                    standard_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    try:
                        dwjz_val = float(match.group(2))
                        growth_match = re.search(r'([-+]?[0-9.]+)%', line)
                        growth_val = float(growth_match.group(1)) if growth_match else 0.0
                        target_code = edit_code
                        code_match = code_pattern.search(line)
                        if code_match and code_match.group(1) in memory_db:
                            target_code = code_match.group(1)
                        memory_db[target_code] = [
                            item for item in memory_db[target_code]
                            if item['日期'] != standard_date
                        ]
                        memory_db[target_code].append({
                            "日期": standard_date,
                            "单位净值": dwjz_val,
                            "累计净值": dwjz_val,
                            "净值增长率": growth_val
                        })
                        import_details[target_code] += 1
                    except Exception:
                        continue

            total_imported = 0
            for code, count in import_details.items():
                if count > 0:
                    memory_db[code] = sorted(
                        memory_db[code], key=lambda x: x['日期'], reverse=True
                    )
                    save_local_history(code, memory_db[code])
                    total_imported += count

            if total_imported > 0:
                summary = f"智能分流导入成功，共写入 {total_imported} 条！"
                for code, count in import_details.items():
                    if count > 0:
                        summary += f" [{code}] +{count}条"
                st.success(summary)
                st.rerun()
            else:
                st.error("未能识别有效数据，请检查格式。")

else:  # 快捷增删基金
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown("##### ➕ 添加新基金")
        with st.form("add_new_fund_form"):
            add_code = st.text_input("6位基金代码", max_chars=6)
            add_name = st.text_input("基金简称")
            add_index = st.text_input("关联指数名称")
            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                add_period = st.text_input("定投周期", value="每周二")
            with col_ap2:
                add_amount = st.number_input("定投金额(元)", value=100, step=10)
            submit_add = st.form_submit_button("确认添加", type="primary")
            if submit_add:
                if len(add_code) != 6 or not add_name:
                    st.error("请输入正确的代码和简称！")
                else:
                    st.session_state.fund_config[add_code] = {
                        'name': add_name,
                        'index_name': add_index if add_index else '自定义指数',
                        'period': add_period,
                        'amount': add_amount,
                        'pe_ttm': 20.0,
                        'pe_percent': 50.0,
                        'div_yield': '1.50%',
                        'status': '新入库跟踪',
                        'base_strategy': '🎯 建议【严格执行常规计划 {plan}】。'
                    }
                    save_config(st.session_state.fund_config)
                    st.success("基金永久添加成功！")
                    st.rerun()

    with c_del:
        st.markdown("##### 🗑️ 删除基金")
        st.caption("删除配置同时清除本地历史缓存。")
        del_target = st.selectbox(
            "选择要销毁的基金",
            list(st.session_state.fund_config.keys()),
            format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}",
            key="del_select",
            label_visibility="collapsed"
        )
        confirm_del = st.checkbox("我确认此操作不可逆，同意删除")
        if st.button("彻底从系统中抹除", disabled=not confirm_del, type="secondary"):
            if del_target in st.session_state.fund_config:
                del st.session_state.fund_config[del_target]
                save_config(st.session_state.fund_config)
                hist_file = os.path.join(HISTORY_DIR, f"{del_target}_hist.json")
                if os.path.exists(hist_file):
                    try:
                        os.remove(hist_file)
                    except Exception:
                        pass
                st.success(f"基金 {del_target} 已永久卸载！")
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 3. 透视面板
# ──────────────────────────────────────────────
st.markdown('<div class="section-label">穿透明细 · 多维透视</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="insight-panel">
<div style="font-weight:700;font-size:0.9rem;color:var(--text-primary);margin-bottom:16px;">
    🔍 {st.session_state.fund_config[edit_code]['name']}
    <span style="font-weight:400;color:var(--text-tertiary);font-size:0.75rem;margin-left:8px;">{edit_code}</span>
</div>
""", unsafe_allow_html=True)

current_db = load_local_history(edit_code)

if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')

    df_global_metrics = df_raw.groupby('月份').agg(
        月度平均价中枢=('单位净值', 'mean'),
        当月最高价边界=('单位净值', 'max')
    ).reset_index()
    df_raw_enriched = pd.merge(df_raw, df_global_metrics, on='月份', how='left')

    time_frame = st.radio(
        "图表视窗",
        ["近1个月", "近3个月", "近6个月", "近1年", "全部数据"],
        horizontal=True,
        index=4,
        label_visibility="collapsed"
    )

    latest_date = df_raw_enriched['日期'].max()
    days_map = {
        "近1个月": 30, "近3个月": 90, "近6个月": 180, "近1年": 365
    }
    if time_frame in days_map:
        df_filtered = df_raw_enriched[
            df_raw_enriched['日期'] >= (latest_date - pd.Timedelta(days=days_map[time_frame]))
        ]
    else:
        df_filtered = df_raw_enriched.copy()

    if not df_filtered.empty:
        st.markdown(
            f'<div style="font-size:0.75rem;color:var(--text-tertiary);margin-bottom:12px;">'
            f'视窗：{time_frame}  ·  红线：最高价边界  ·  绿线：月度均价中枢'
            f'</div>',
            unsafe_allow_html=True
        )

        c_axis1, c_axis2, c_axis3 = st.columns([1, 1, 1])
        with c_axis1:
            is_manual_y = st.checkbox("手动锁定纵轴", value=False)

        current_min = float(df_filtered['单位净值'].min())
        current_max = float(df_filtered['当月最高价边界'].max())
        padding = (current_max - current_min) * 0.08 if current_max != current_min else 0.05

        with c_axis2:
            manual_min = st.number_input(
                "Y 轴下限", value=round(current_min - padding, 2),
                step=0.02, disabled=not is_manual_y, label_visibility="collapsed"
            )
        with c_axis3:
            manual_max = st.number_input(
                "Y 轴上限", value=round(current_max + padding, 2),
                step=0.02, disabled=not is_manual_y, label_visibility="collapsed"
            )

        df_melted = df_filtered.melt(
            id_vars=['日期'],
            value_vars=['单位净值', '月度平均价中枢', '当月最高价边界'],
            var_name='指标类型', value_name='净值数值'
        )

        y_scale = (
            alt.Scale(domain=[manual_min, manual_max], clamp=True)
            if is_manual_y else alt.Scale(zero=False, padding=15)
        )
        color_scale = alt.Scale(
            domain=['单位净值', '月度平均价中枢', '当月最高价边界'],
            range=['#e8ecf1', '#4ade80', '#f87171']
        )

        chart = alt.Chart(df_melted).mark_line(
            strokeWidth=2
        ).encode(
            x=alt.X('日期:T', title=None, axis=alt.Axis(
                grid=False, domainColor='#262b38',
                tickColor='#262b38', labelColor='#5c6478'
            )),
            y=alt.Y('净值数值:Q', title=None, scale=y_scale, axis=alt.Axis(
                gridColor='#1e2230', domainColor='#262b38',
                tickColor='#262b38', labelColor='#5c6478'
            )),
            color=alt.Color(
                '指标类型:N', scale=color_scale,
                legend=alt.Legend(
                    title=None, orient='top',
                    labelColor='#8b93a5', labelFontSize=12
                )
            )
        ).properties(
            height=380
        ).configure_view(
            stroke=None,
            fill='#13161d'
        ).interactive()

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("当前时间范围内暂无数据。")

    # Tabs
    t_year, t_month, t_day = st.tabs(["年度表现", "月度中枢", "日流水账"])
    with t_year:
        df_year = (
            df_raw.groupby('年份')
            .agg(
                记录天数=('日期', 'count'),
                涨跌波动=('净值增长率', 'sum'),
                最高净值=('单位净值', 'max'),
                最低净值=('单位净值', 'min')
            )
            .reset_index()
            .sort_values(by='年份', ascending=False)
        )
        df_year['涨跌波动'] = df_year['涨跌波动'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)
    with t_month:
        df_month = (
            df_raw.groupby('月份')
            .agg(
                均价中枢=('单位净值', 'mean'),
                最高价=('单位净值', 'max'),
                累计波动=('净值增长率', 'sum')
            )
            .reset_index()
            .sort_values(by='月份', ascending=False)
        )
        df_month['均价中枢'] = df_month['均价中枢'].map(lambda x: f"{x:.4f}")
        df_month['最高价'] = df_month['最高价'].map(lambda x: f"{x:.4f}")
        df_month['累计波动'] = df_month['累计波动'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_month, use_container_width=True, hide_index=True)
    with t_day:
        df_display = df_raw.copy().sort_values(by='日期', ascending=False)
        df_display['日期'] = df_display['日期'].dt.strftime('%Y-%m-%d')
        df_display['净值增长率'] = df_display['净值增长率'].map(lambda x: f"{x:.2f}%")
        st.dataframe(
            df_display[['日期', '单位净值', '累计净值', '净值增长率']],
            use_container_width=True, hide_index=True
        )
else:
    st.info("本地数据库为空，可使用「极速批量导入」功能粘贴历史数据。")

st.markdown('</div>', unsafe_allow_html=True)
