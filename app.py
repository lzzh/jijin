import streamlit as st
import pandas as pd
import urllib.request
import json
import os
import time

# 设置网页布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")

# --- 手机端纯净体验 CSS 注入 ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    .stMarkdown div p { word-break: break-all !important; white-space: pre-wrap !important; }
    .fund-card { background-color: #1E232A; border-radius: 12px; padding: 16px; margin-bottom: 1px; border: 1px solid #3A3F47; }
    .fund-title { font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 8px; border-bottom: 1px solid #3A3F47; padding-bottom: 6px; }
    .fund-tag { background-color: #2A2F35; color: #A1C4FD; padding: 2px 8px; border-radius: 4px; font-size: 12px; display: inline-block; margin-bottom: 5px; }
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
        if data and data.get("Data") is None: return local_data, "云端接口限流，请稍后再试。"
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
            return local_data, f"🎉 成功搬运 {new_count} 天数据！"
        return local_data, "👌 数据已最新，无需更新。"
    except Exception as e: return local_data, f"波动 ({str(e)})"


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


# --- 2. 纯净控制台：集成三大核心功能 ---
st.subheader("🛠️ 基金综合管理控制台")
edit_code = st.selectbox("🎯 当前选中的基金（用于数据穿透查看）：", list(st.session_state.fund_config.keys()), format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
current_info = st.session_state.fund_config[edit_code]

op_mode = st.radio("请选择操作功能：", ["📝 修改定投计划", "🔄 蚂蚁搬家数据同步", "✨ 快捷添加新基金"], horizontal=True)

# 功能 A：修改计划
if op_mode == "📝 修改定投计划":
    with st.form("my_edit_form"):
        col_p, col_a = st.columns(2)
        with col_p: new_period = st.text_input("定投周期：", value=current_info['period'])
        with col_a: new_amount = st.number_input("定投金额 (元)：", value=int(current_info['amount']), step=10)
        submit_plan = st.form_submit_button("💾 确认更新并永久保存计划")
        if submit_plan:
            st.session_state.fund_config[edit_code]['period'] = new_period
            st.session_state.fund_config[edit_code]['amount'] = new_amount
            save_config(st.session_state.fund_config)
            st.success("🎉 配置已成功保存！看盘卡片已同步刷新。")
            st.rerun()

# 功能 B：增量搬运数据流
elif op_mode == "🔄 蚂蚁搬家数据同步":
    st.markdown("#### 🚀 一键全员同步机制（省时省力）")
    if st.button("🔥 触发：一键全员下载最新一页（第1页）数据"):
        success_funds = []
        progress_bar = st.progress(0)
        all_codes = list(st.session_state.fund_config.keys())
        
        for idx, code in enumerate(all_codes):
            _, msg = move_ants_history(code, page_index=1)
            success_funds.append(f"• **{code}**: {msg}")
            progress_bar.progress((idx + 1) / len(all_codes))
            time.sleep(0.2) # 微秒级延迟，确保接口安全
            
        st.success("📊 【全员最新数据同步完毕！】各基金同步状态如下：")
        for res in success_funds:
            st.markdown(res)
        st.rerun()
        
    st.markdown("---")
    st.markdown("#### ⛏️ 针对当前选中基金深度挖掘老历史")
    col_btn1, _ = st.columns([3, 5])
    with col_btn1:
        target_page = st.number_input("拓展历史页码", min_value=1, max_value=100, value=2, step=1, key="num_page")
        if st.button("挖掘该基金此页老历史", key="btn_dig"):
            _, msg = move_ants_history(edit_code, page_index=target_page)
            st.toast(msg)
            st.rerun()

# 功能 C：动态添加新基金
else:
    with st.form("add_new_fund_form"):
        st.markdown("**✨ 添加一只核心资产基金到自选池**")
        add_code = st.text_input("请输入6位基金代码（例如：001630）：", max_chars=6)
        add_name = st.text_input("请输入基金简称（例如：天弘计算机C）：")
        add_index = st.text_input("关联跟踪的指数名称（例如：计算机指数）：")
        
        st.caption("💡 提示：新基金的估值数据（PE/股息率）会在后续接入实时API后自动更新，此处先初始化基础定投规则。")
        col_ap1, col_ap2 = st.columns(2)
        with col_ap1: add_period = st.text_input("设定定投周期：", value="每周二")
        with col_ap2: add_amount = st.number_input("设定定投金额(元)：", value=100, step=10)
            
        submit_add = st.form_submit_button("➕ 确认添加这只基金")
        if submit_add:
            if len(add_code) != 6 or not add_name:
                st.error("⚠️ 请输入正确的6位基金代码和基金简称！")
            elif add_code in st.session_state.fund_config:
                st.error("💡 该基金已在你的清单中，无需重复添加。")
            else:
                st.session_state.fund_config[add_code] = {
                    'name': add_name,
                    'index_name': add_index if add_index else '自定义指数',
                    'period': add_period,
                    'amount': add_amount,
                    'pe_ttm': 20.0, # 初始给个中性占位值
                    'pe_percent': 50.0,
                    'div_yield': '1.50%',
                    'status': '新入库跟踪',
                    'base_strategy': '🎯 刚刚加入自选池。建议【严格执行常规计划 {plan}】。'
                }
                save_config(st.session_state.fund_config)
                st.success(f"🎉 基金 【{add_code} - {add_name}】 已成功永久添加！")
                st.rerun()


# --- 3. 多维增量穿透大盘 + 原生缩放折线图 ---
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader(f"🔍 穿透明细：【{st.session_state.fund_config[edit_code]['name']}】多维透视面板")

current_db = load_local_history(edit_code)

if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    
    st.markdown("**📉 历史趋势全动态走势图（单指滑动可查看精准日期与净值）**")
    df_chart = df_raw.set_index('日期').sort_index()[['单位净值']]
    st.line_chart(df_chart, x_label="交易日期", y_label="基金单位净值")
    
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')
    
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
    st.info("💡 当前该基金本地总库为空。请在控制台切换到【🔄 蚂蚁搬家数据同步】触发同步，开始建立历史趋势图！")
