import streamlit as st
import pandas as pd
import urllib.request
import json
import os

# 设置网页布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")

# --- 手机端防乱码、防重叠、支持自动换行纯净 CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
    /* 核心文本容器：支持手机端完美自动换行 */
    .stMarkdown div p {
        word-break: break-all !important;
        white-space: pre-wrap !important;
    }
    
    /* 仿手机原生 App 卡片设计 */
    .fund-card {
        background-color: #1E232A;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 1px;
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
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 我的智能化定投实时监控看板")

CONFIG_FILE = "my_fund_settings.json"
HISTORY_DIR = "fund_history_db"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': {'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50', 'period': '每月21号', 'amount': 1100, 'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%', 'status': '估值偏高、股息最优', 'base_strategy': '⚠️ 估值百分位偏高(>80%)。建议【维持当前定投不加仓】。'}, 
    '016452': {'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100', 'period': '每天', 'amount': 80, 'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%', 'status': '显著高估、轻微红利', 'base_strategy': '🚨 处于历史高位区间。建议将当前的 {plan} 【下调至 {half_amount} 元左右】。'}, 
    '023882': {'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50', 'period': '每周二', 'amount': 100, 'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%', 'status': '中性偏贵、低股息', 'base_strategy': '等权观望。建议【严格执行常规计划 {plan}】。'},   
    '023917': {'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流', 'period': '每周二', 'amount': 790, 'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%', 'status': '深度低估、均衡现金流', 'base_strategy': '💎 绝对核心加仓区！建议【坚定执行当前计划 {plan}】。'}   
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

def load_local_history(fund_code):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_local_history(fund_code, data_list):
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    with open(file_path, "w", encoding="utf-8") as f: json.dump(data_list, f, ensure_ascii=False, indent=4)

def move_ants_history(fund_code, page_index=1):
    local_data = load_local_history(fund_code)
    try:
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex={page_index}&pageSize=40"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        with urllib.request.urlopen(req, timeout=3) as response: html = response.read().decode('utf-8')
        data = json.loads(html)
        if data and data.get("Data") is None: return local_data, "今日搬运太频繁，请稍后再试。"
        raw_list = data["Data"]["LSJZList"]
        new_count = 0
        existing_dates = {item['日期'] for item in local_data}
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): continue
            date_str = item["FSRQ"]
            if date_str not in existing_dates:
                try: growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
                except: growth = 0.0
                local_data.append({"日期": date_str, "单位净值": float(item["DWJZ"]), "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]), "净值增长率": growth})
                new_count += 1
        if new_count > 0:
            local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
            save_local_history(fund_code, local_data)
            return local_data, f"🎉 成功搬运储存了 {new_count} 天历史数据！"
        return local_data, "👌 本页数据已存在，无需重复搬运。"
    except Exception as e: return local_data, f"搬运遭遇波动 ({str(e)})"

# --- 1. 全景卡片看板 ---
st.subheader("📋 我的定投核心资产智能执行卡片")
for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    st.markdown(f'<div class="fund-card"><div class="fund-title">📈 {info["name"]} ({code})</div><div class="fund-tag">跟踪指数: {info["index_name"]}</div> | <div class="fund-tag" style="color:#FFF;">当前计划: {plan_str}</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("10年 PE 百分位", f"{info['pe_percent']:.2f}%")
    c2.metric("当前 PE", f"{info['pe_ttm']:.2f}")
    c3.metric("TTM 股息率", info['div_yield'])
    st.info(strategy_str)

st.markdown("<hr>", unsafe_allow_html=True)

# --- 2. 纯原生管理面板（防小图标乱码） ---
st.subheader("🛠️ 智能基金配置与数据搬运控制台")
edit_code = st.selectbox("选择要修改或搬运数据的基金：", list(st.session_state.fund_config.keys()), format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
current_info = st.session_state.fund_config[edit_code]

# 修改计划表单
with st.form("edit_plan_form"):
    st.markdown("**1️⃣ 修改并永久保存定投计划**")
    col_p, col_a = st.columns(2)
    with col_p: new_period = st.text_input("定投周期：", value=current_info['period'])
    with col_a: new_amount = st.number_input("定投金额 (元)：", value=int(current_info['amount']), step=10)
    submit_plan = st.form_submit_with_button_label("💾 确认更新并永久保存计划")
    if submit_plan:
        st.session_state.fund_config[edit_code]['period'] = new_period
        st.session_state.fund_config[edit_code]['amount'] = new_amount
        save_config(st.session_state.fund_config)
        st.success("🎉 配置已固化到云端！正在自动刷新看板...")
        st.rerun()

# 蚂蚁搬家管理
st.markdown("**2️⃣ 蚂蚁搬家数据流管理**")
col_btn1, col_btn2, _ = st.columns([2, 2, 4])
current_db = load_local_history(edit_code)

with col_btn1:
    if st.button("🔄 蚂蚁搬家：顺路下载最新40天数据", key="btn_ants"):
        current_db, msg = move_ants_history(edit_code, page_index=1)
        st.toast(msg)
        st.rerun()
with col_btn2:
    target_page = st.number_input("搬运更深历史(页码)", min_value=1, max_value=100, value=2, step=1, key="num_page")
    if st.button("⛏️ 深度挖掘旧历史", key="btn_dig"):
        current_db, msg = move_ants_history(edit_code, page_index=target_page)
        st.toast(msg)
        st.rerun()

# --- 3. 多维增量穿透大盘 + 原生交互折线图 ---
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader(f"🔍 穿透明细：【{st.session_state.fund_config[edit_code]['name']}】多维透视面板")

if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    
    # 📈 --- 纯原生轻量级交互折线图（自带手机端单指滑动悬浮窗、双指捏合缩放） ---
    st.markdown("**📉 历史趋势全动态走势图（单指滑动可查看精准日期与净值）**")
    df_chart = df_raw.set_index('日期').sort_index()[['单位净值']]
    st.line_chart(df_chart, x_label="交易日期", y_label="基金单位净值")
    
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')
    
    # 三选项卡数据面板
    t_year, t_month, t_day = st.tabs(["📅 累计年度表现", "🌙 累计月度价格中枢", "📄 完整日流水账明细"])
    
    with t_year:
        df_year = df_raw.groupby('年份').agg(该年记录天数=('日期', 'count'), 期间涨跌波动=('净值增长率', 'sum'), 期间最高单位净值=('单位净值', 'max'), 期间最低单位净值=('单位净值', 'min')).reset_index().sort_values(by='年份', ascending=False)
        df_year['期间涨跌波动'] = df_year['期间涨跌波动'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)
        
    with t_month:
        df_month = df_raw.groupby('月份').agg(月度平均价中枢=('单位净值', 'mean'), 当月最高价边界=('单位净值', 'max'), 月度累计波动幅=('净值增长率', 'sum')).reset_index().sort_values(by='月份', ascending=False)
        df_month['月度平均价中枢'] = df_month['月度平均价中枢'].map(lambda x: f"{x:.4f}")
        df_month['当月最高价边界'] = df_month['当月最高价边界'].map(lambda x: f"{x:.4f}")
        df_month['月度累计波动幅'] = df_month['月度累计波动幅'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_month, use_container_width=True, hide_index=True)
        
    with t_day:
        df_display = df_raw.copy().sort_values(by='日期', ascending=False)
        df_display['日期'] = df_display['日期'].dt.strftime('%Y-%m-%d')
        df_display['净值增长率'] = df_display['净值增长率'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_display[['日期', '单位净值', '累计净值', '净值增长率']], use_container_width=True, hide_index=True)
else:
    st.info("💡 当前该基金本地总库为空。请在上方控制台点击【蚂蚁搬家】按钮，开始建立历史数据库！")
