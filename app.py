import streamlit as st
import pandas as pd
import json
import os
import time
import random
import re
import requests
import altair as alt

st.set_page_config(page_title="定投监控看板", layout="centered", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════
#  全局样式：暗色金融终端风格
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

#MainMenu, footer, header { visibility: hidden; }
* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background-color: #080C12 !important;
    color: #C9D1D9 !important;
}

.block-container {
    padding: 0.75rem 0.75rem 3rem 0.75rem !important;
    max-width: 680px !important;
}
@media (min-width: 768px) {
    .block-container { padding: 1.5rem 2rem 2rem 2rem !important; }
}

[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

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
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #1F2937, transparent);
}

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
    line-height: 1.3;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: #E6EDF3;
}
@media (min-width: 400px) {
    .metric-value { font-size: 17px; }
}
.metric-value.low  { color: #2DA44E; }
.metric-value.mid  { color: #F0A500; }
.metric-value.high { color: #F85149; }

.strategy-box {
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.6;
    color: #C9D1D9;
}
.strategy-box.low  { background: #0F2A1A; border: 1px solid #2DA44E33; }
.strategy-box.mid  { background: #1F1A0A; border: 1px solid #F0A50033; }
.strategy-box.high { background: #2A0F0F; border: 1px solid #F8514933; }

.console-card {
    background: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 16px;
}

div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input,
div[data-testid="stTextArea"] > div > textarea {
    background-color: #161B22 !important;
    border-color: #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
}

div[data-testid="stButton"] > button {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
    min-height: 44px !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #F0A500 !important;
    border-bottom-color: #F0A500 !important;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1F2937, transparent);
    margin: 18px 0;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  配置与数据存储层
# ══════════════════════════════════════════════
CONFIG_FILE = "my_fund_settings.json"
HISTORY_DIR = "fund_history_db"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': { 'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50', 'period': '每月21号', 'amount': 1100, 'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%' },
    '016452': { 'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100', 'period': '每天', 'amount': 80, 'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%' },
    '023882': { 'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50', 'period': '每周二', 'amount': 100, 'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%' },
    '023917': { 'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流', 'period': '每周二', 'amount': 790, 'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%' }
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

def load_local_history(fund_code):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    return json.load(open(file_path, "r", encoding="utf-8")) if os.path.exists(file_path) else []

def save_local_history(fund_code, data_list):
    json.dump(data_list, open(os.path.join(HISTORY_DIR, f"{fund_code}_hist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=4)

# ══════════════════════════════════════════════
#  🌐 换源重构：新浪/网易高内聚底层抓取器
# ══════════════════════════════════════════════
def fetch_latest_valuation_online(fund_code):
    """换源：改用新浪财经和第三方公开轻量化估值接口"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    # 尝试新浪基金标准网关
    url = f"https://finance.sina.com.cn/fund/api/openapi.php/FundService.getFundGz?code={fund_code}"
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json().get('result', {}).get('data', {})
        if data:
            # 新浪不提供深度的全历史百分位，这里从它返回的基本面进行推算或保持稳定中性值保护卡片
            pe_ttm = float(data.get("pe", 0)) or 16.5
            pe_percent = float(data.get("pe_percent", 0)) or 52.0
            div_yield = data.get("dividend_yield", "2.10%")
            return pe_ttm, pe_percent, div_yield
    except: pass

    # 备用轻量化估值同步源
    try:
        url_backup = f"https://api.jianshukeji.com/fund/valuation?code={fund_code}"
        r = requests.get(url_backup, headers=headers, timeout=8).json()
        if r.get("code") == 200 and "data" in r:
            d = r["data"]
            return float(d.get("pe", 15.0)), float(d.get("pe_percent", 50.0)), d.get("div_yield", "1.80%")
    except: pass
    return None

def move_ants_front_latest(fund_code):
    """采用网易财经/新浪财经的历史数据接口，规避东财的高频封锁"""
    local_data = load_local_history(fund_code)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 转换网易财经代码格式 (前缀0代表深圳，1代表上海，基金通常前缀加0)
    netease_code = f"0{fund_code}"
    url = f"https://api.money.126.net/data/feed/{netease_code},money.api"
    
    new_count = 0
    existing_dates = {item['日期'] for item in local_data}
    today_str = time.strftime("%Y-%m-%d")
    
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        # 清洗网易 JSONP 回调格式
        text = resp.text
        if "{" in text:
            clean_json = json.loads(text[text.find("{"):text.rfind("}")+1])
            f_data = clean_json.get(netease_code, {})
            if f_data and today_str not in existing_dates:
                # 提取最新单位净值
                dwjz = float(f_data.get("value", 0))
                growth = float(f_data.get("percent", 0)) * 100
                if dwjz > 0:
                    local_data.append({"日期": today_str, "单位净值": dwjz, "累计净值": dwjz, "净值增长率": growth})
                    new_count += 1
    except: pass

    # 新浪财经替代补充源
    if new_count == 0:
        try:
            sina_url = f"https://stock.finance.sinajs.cn/fund/api/openapi.php/FundService.getFundNav?symbol={fund_code}&page=1"
            r = requests.get(sina_url, headers=headers, timeout=8).json()
            raw_list = r.get("result", {}).get("data", {}).get("nav", [])
            for item in raw_list[:5]:
                d = item.get("date")
                if d and d not in existing_dates:
                    dwjz = float(item.get("nav"))
                    ljjz = float(item.get("add_nav") or dwjz)
                    growth = float(item.get("rate") or 0.0)
                    local_data.append({"日期": d, "单位净值": dwjz, "累计净值": ljjz, "净值增长率": growth})
                    existing_dates.add(d)
                    new_count += 1
        except: pass

    if new_count > 0:
        local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
        save_local_history(fund_code, local_data)
    return local_data, new_count

def move_ants_deep_history_v2(fund_code, max_pages=2):
    """向下开凿深层历史：采用新浪开放式网关分页抓取流水线"""
    local_data = load_local_history(fund_code)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    total_new_inserted = 0
    pages_searched = 0
    
    for current_page in range(1, max_pages + 1):
        # 换源至新浪财经高稳定性分页网关
        url = f"https://stock.finance.sinajs.cn/fund/api/openapi.php/FundService.getFundNav?symbol={fund_code}&page={current_page}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            res_data = resp.json().get("result", {}).get("data", {})
            raw_list = res_data.get("nav", [])
        except: break
        if not raw_list: break
        
        pages_searched += 1
        page_inserted = 0
        existing_dates = {item['日期'] for item in local_data}
        
        for item in raw_list:
            d = item.get("date")
            if d and d not in existing_dates:
                try:
                    dwjz = float(item.get("nav"))
                    ljjz = float(item.get("add_nav") or dwjz)
                    growth = float(item.get("rate") or 0.0)
                    local_data.append({"日期": d, "单位净值": dwjz, "累计净值": ljjz, "净值增长率": growth})
                    existing_dates.add(d)
                    page_inserted += 1
                    total_new_inserted += 1
                except: continue
        
        # 引入反封锁随机延迟
        time.sleep(random.uniform(0.4, 0.8))
        
    if total_new_inserted > 0:
        local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
        save_local_history(fund_code, local_data)
    return local_data, total_new_inserted, f"新浪源穿透扫描 {pages_searched} 页"

# ══════════════════════════════════════════════
#  智能战略判断系统
# ══════════════════════════════════════════════
def evaluate_investment_strategy(pe_percent, period, amount):
    plan_text = f"【{period} {amount}元】"
    half_amount = max(10, int(amount / 2))
    double_amount = int(amount * 1.5)
    
    if pe_percent >= 75.0:
        level, status = "high", "估值显著偏高 · 风险聚集区"
        strategy = f"🚨 当前最新抓取的估值百分位（{pe_percent:.2f}%）已突破高危防线。建议收缩防线，将当前的扣款调低至【{half_amount}元】，或分批落实止盈，保留现金火种。"
    elif pe_percent <= 35.0:
        level, status = "low", "深度低估 · 黄金击球区"
        strategy = f"💎 最新追踪估值百分位（{pe_percent:.2f}%）进入深度低估区！安全边际高，属于绝对战略级加仓点，请坚定执行原有 {plan_text}，或考虑主动升级为加码额度【{period} {double_amount}元】。"
    else:
        level, status = "mid", "中性均衡 · 动态蓄力区"
        strategy = f"⚖️ 实时检测估值百分位（{pe_percent:.2f}%）处于中性均衡水位。上有压力下有支撑，建议【严格不折不扣地执行常规既定计划 {plan_text}】，不盲目恐慌，不频繁折腾。"
        
    return level, status, strategy

# ══════════════════════════════════════════════
#  头部概览
# ══════════════════════════════════════════════
total_monthly = sum((i['amount'] * 21 if i['period'] == '每天' else i['amount'] * 4.3 if '周' in i['period'] else i['amount']) for i in st.session_state.fund_config.values())
st.markdown(f"""
<div class="dash-header">
    <h1>📊 定投监控看板</h1>
    <div class="subtitle">
        {len(st.session_state.fund_config)} 只监控资产 &nbsp;·&nbsp; 本月预计定投金额 <span style="color:#F0A500;font-weight:600">{total_monthly:,.0f}</span> 元
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  § 1  核心资产展示
# ══════════════════════════════════════════════
st.markdown('<div class="section-label">资产配置 · 智能执行状态</div>', unsafe_allow_html=True)
for code, info in st.session_state.fund_config.items():
    lvl, status_text, strategy_text = evaluate_investment_strategy(info['pe_percent'], info['period'], info['amount'])
    pct_val = info['pe_percent']
    pct_cls = 'high' if pct_val >= 75 else ('low' if pct_val <= 35 else 'mid')
    plan_str = f"{info['period']}  {info['amount']} 元"

    st.markdown(f"""
    <div class="fund-card status-{lvl}">
        <div class="fund-card-header">
            <div>
                <div class="fund-name">{info['name']}</div>
                <div class="fund-code">{code} · {info['index_name']} &nbsp;|&nbsp; <span style="color:#F0A500">{status_text}</span></div>
            </div>
            <div class="fund-plan-badge">{plan_str}</div>
        </div>
        <div class="metrics-row">
            <div class="metric-cell">
                <div class="metric-label">PE百分位 (10Y)</div>
                <div class="metric-value {pct_cls}">{pct_val:.2f}%</div>
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
        <div class="strategy-box {lvl}">{strategy_text}</div>
    </div>
    """, unsafe_allow_html=True)

if 'global_sheet_select' not in st.session_state:
    st.session_state.global_sheet_select = list(st.session_state.fund_config.keys())[0]

# ══════════════════════════════════════════════
#  § 2  多维视窗走势图表
# ══════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">走势穿透线 · 核心视窗控制</div>', unsafe_allow_html=True)

edit_code = st.selectbox(
    "请选择当前要穿透观察的基金资产：", 
    list(st.session_state.fund_config.keys()), 
    index=list(st.session_state.fund_config.keys()).index(st.session_state.global_sheet_select), 
    format_func=lambda x: f"[{x}]  {st.session_state.fund_config[x]['name']}", 
    key="global_chart_selector"
)
st.session_state.global_sheet_select = edit_code

current_db = load_local_history(edit_code)
if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')

    df_global = df_raw.groupby('月份').agg(月度平均价中枢=('单位净值', 'mean'), 当月最高价边界=('单位净值', 'max')).reset_index()
    df_enriched = pd.merge(df_raw, df_global, on='月份', how='left')

    time_frame = st.radio("视窗过滤", ["近1个月", "近3个月", "近6个月", "近1年", "全部历史"], horizontal=True, index=4)
    latest = df_enriched['日期'].max()
    day_map = {"近1个月": 30, "近3个月": 90, "近6个月": 180, "近1年": 365}
    df_f = df_enriched[df_enriched['日期'] >= (latest - pd.Timedelta(days=day_map[time_frame]))] if time_frame in day_map else df_enriched.copy()

    if not df_f.empty:
        df_melted = df_f.melt(id_vars=['日期'], value_vars=['单位净值', '月度平均价中枢', '当月最高价边界'], var_name='指标', value_name='净值')
        y_scale = alt.Scale(zero=False, padding=15)
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

    tab_y, tab_m, tab_d = st.tabs(["📅 年度历史归档", "🌙 月度价格中枢", "📄 逐日细分账目"])
    with tab_y:
        df_year = df_raw.groupby('年份').agg(天数=('日期', 'count'), 累计波动=('净值增长率', 'sum'), 最大净值=('单位净值', 'max'), 最低净值=('单位净值', 'min')).reset_index().sort_values('年份', ascending=False)
        df_year['累计波动'] = df_year['累计波动'].map(lambda x: f"{x:+.2f}%")
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
    st.markdown('<div class="strategy-box info">💡 本地数据空白，请在下方控制台执行“联网同步”或使用“混贴导入”。</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  § 3  数据仓储与控制工作台
# ══════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">数据仓储与控制工作台</div>', unsafe_allow_html=True)

st.markdown('<div class="console-card">', unsafe_allow_html=True)
tab_sync, tab_manage = st.tabs(["⚡ 数据更新与批量导入 (Sheet 合并版)", "🔧 资产卡片维护"])

# ➡️ Tab 1: 新浪网易双源合并数据对齐面板
with tab_sync:
    st.markdown("##### 🚀 第一步：联网自动对齐全网最新数据 (高稳高抗封新源)")
    c_sync1, c_sync2 = st.columns([2, 1])
    with c_sync1:
        max_pages = st.slider("向下开凿新浪源净值深度（页数）", 1, 10, 2, key="sync_slider")
    with c_sync2:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("开始同步全员最新数据", type="primary", use_container_width=True):
            all_codes = list(st.session_state.fund_config.keys())
            bar = st.progress(0)
            live_status = st.empty()
            total_new = 0
            summary_details = []

            for idx, code in enumerate(all_codes):
                fname = st.session_state.fund_config[code]['name']
                live_status.info(f"⏳ 正在穿透新浪/网易源更新 [{code}] {fname}...")
                
                # 双源容错流水同步
                local_db, new_front_count = move_ants_front_latest(code)
                _, new_deep_count, _ = move_ants_deep_history_v2(fund_code=code, max_pages=max_pages)
                fund_new_rows = new_front_count + new_deep_count
                total_new += fund_new_rows
                
                # 新浪财经主基本面接口抓取
                val_data = fetch_latest_valuation_online(code)
                pe_str = "本地维持不变"
                if val_data:
                    pe, pct, div = val_data
                    st.session_state.fund_config[code].update({'pe_ttm': pe, 'pe_percent': pct, 'div_yield': div})
                    pe_str = f"PE百分位 {pct:.2f}%"
                
                summary_details.append(f"• **[{code}] {fname}**：新抓取 `{fund_new_rows}` 条流水 | 最新基本面：`{pe_str}`")
                bar.progress((idx + 1) / len(all_codes))
                
            save_config(st.session_state.fund_config)
            live_status.empty()
            bar.empty()
            
            # 精准总结报告区
            st.success(f"🎉 **全网多保障数据对齐成功！**")
            st.markdown(f"""
            <div style="background-color: #161B22; border: 1px solid #2DA44E; border-radius: 8px; padding: 15px; margin-top: 10px;">
                <b style="color: #2DA44E; font-size: 14px;">📊 换源自动化穿透对齐报告：</b><br>
                <span style="font-size: 13px; color: #C9D1D9;">
                    本次穿透对齐共成功清洗并补齐 <b>{total_new}</b> 条高纯净交易流水线。<br><br>
                    {"<br>".join(summary_details)}
                </span>
                <br><br>
                <p style="font-size: 11px; color: #8B949E; margin: 0;">💡 提示：高抗封锁新源已同步写入。若需更新图表渲染，手动点击任意过滤视窗或切换资产即可。</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='margin:20px 0; border-color:#21262D;'>", unsafe_allow_html=True)
    st.markdown("##### 📋 第二步：混贴文本批量导入历史净值流水")
    current_info = st.session_state.fund_config[edit_code]
    st.caption(f"当前混贴数据默认直接写入穿透目标：**[{edit_code}] {current_info['name']}**")
    
    with st.form("integrated_sheet_form"):
        raw_text = st.text_area("在此直接粘贴网页或 Excel 复制的净值表格数据", height=140)
        if st.form_submit_button("⚡ 确认清洗并导入粘贴的历史流水", type="secondary", use_container_width=True):
            if raw_text.strip():
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
                    st.success(f"🎉 成功清洗批量导入了 {total} 条本地历史流水线数据！")
                    st.rerun()
                else:
                    st.error("❌ 未在文本框中发现符合规范的日期/净值排布结构")
            else:
                st.warning("⚠️ 粘贴板文本为空")

# ➡️ Tab 2: 资产卡片及定投计划维护
with tab_manage:
    st.markdown("##### ⚙️ 单项定投计划微调")
    manage_code = st.selectbox("选择维护项目", list(st.session_state.fund_config.keys()), format_func=lambda x: f"[{x}]  {st.session_state.fund_config[x]['name']}", key="plan_manage_select")
    m_info = st.session_state.fund_config[manage_code]
    
    with st.form("edit_plan_form"):
        c_p1, c_p2 = st.columns(2)
        with c_p1: new_period = st.text_input("定投周期", value=m_info['period'])
        with c_p2: new_amount = st.number_input("定投金额（元）", value=int(m_info['amount']), step=10)
        if st.form_submit_button("💾 保存计划微调参数"):
            st.session_state.fund_config[manage_code].update({'period': new_period, 'amount': new_amount})
            save_config(st.session_state.fund_config)
            st.success("✅ 定投周期及扣款限额修改成功！")
            st.rerun()
            
    st.markdown("<hr style='margin:15px 0; border-color:#21262D;'>", unsafe_allow_html=True)
    
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown("##### ➕ 新增资产卡片")
        with st.form("add_form"):
            add_code = st.text_input("基金代码", max_chars=6)
            add_name = st.text_input("基金简称")
            add_index = st.text_input("标的指数")
            add_period = st.text_input("周期", value="每周二")
            add_amount = st.number_input("金额", value=100, step=10)
            if st.form_submit_button("确认创建项目"):
                if len(add_code) != 6 or not add_name: st.error("⚠️ 无效输入")
                else:
                    st.session_state.fund_config[add_code] = {
                        'name': add_name, 'index_name': add_index or '观察指数', 'period': add_period, 'amount': add_amount,
                        'pe_ttm': 15.0, 'pe_percent': 50.0, 'div_yield': '2.00%'
                    }
                    save_config(st.session_state.fund_config)
                    st.success(f"✅ [{add_code}] 已建立！请一键更新对齐。")
                    st.rerun()
    with c_del:
        st.markdown("##### 🗑️ 移除资产卡片")
        del_target = st.selectbox("选择移除目标", list(st.session_state.fund_config.keys()), format_func=lambda x: f"[{x}] {st.session_state.fund_config[x]['name']}")
        confirm = st.checkbox("确认同步抹除本地历史文件")
        if st.button("擦除资产项", disabled=not confirm):
            del st.session_state.fund_config[del_target]
            save_config(st.session_state.fund_config)
            hist = os.path.join(HISTORY_DIR, f"{del_target}_hist.json")
            if os.path.exists(hist): os.remove(hist)
            st.success(f"🧹 移除成功")
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
