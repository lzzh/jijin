import streamlit as st
import pandas as pd
import urllib.request
import json
import os

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
HISTORY_DIR = "fund_history_db" # 创建一个本地增量历史数据库文件夹
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

DEFAULT_CONFIG = {
    '008163': {'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50', 'period': '每月21号', 'amount': 1100, 'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%', 'status': '估值偏高、股息最优', 'base_strategy': '⚠️ 估值百分位偏高(>80%)。建议【维持当前定投不加仓】。'}, 
    '016452': {'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100', 'period': '每天', 'amount': 80, 'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%', 'status': '显著高估、轻微红利', 'base_strategy': '🚨 处于历史高位区间。建议将当前的 {plan} 【下调至 {half_amount} 元左右】。'}, 
    '023882': {'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50', 'period': '每周二', 'amount': 100, 'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%', 'status': '中性偏贵、低股息', 'base_strategy': '等权观望。建议【严格执行常规计划 {plan}】。'},   
    '023917': {'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流', 'period': '每周二', 'amount': 790, 'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%', 'status': '深度低估、均衡现金流', 'base_strategy': '💎 绝对核心加仓区！建议【坚定执行当前计划 {plan}】。'}   
}

if 'fund_config' not in st.session_state:
    st.session_state.fund_config = DEFAULT_CONFIG

# --- 🛠️ 核心：蚂蚁搬家式文件读取与安全增量累加器 ---
def load_local_history(fund_code):
    """读取本地已经攒下来的历史数据档案"""
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_local_history(fund_code, data_list):
    """将搬家合并后的最新大总库固化写入文件"""
    file_path = os.path.join(HISTORY_DIR, f"{fund_code}_hist.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

def move_ants_history(fund_code, page_index=1):
    """蚂蚁搬家主力：单次只安全抓取 1 页（40条），拉下来后与本地历史库合并去重"""
    local_data = load_local_history(fund_code)
    
    try:
        # 单次只请求 40 条，绝对安全，不会被天天基金风控拦截
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex={page_index}&pageSize=40"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        
        with urllib.request.urlopen(req, timeout=3) as response:
            html = response.read().decode('utf-8')
        data = json.loads(html)
        
        if data and data.get("Data") is None:
            return local_data, "今日云端搬运次数触发频繁限制，请稍后再试。"
            
        raw_list = data["Data"]["LSJZList"]
        new_count = 0
        
        # 提取已有日期的集合，便于去重
        existing_dates = {item['日期'] for item in local_data}
        
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): continue
            date_str = item["FSRQ"]
            if date_str not in existing_dates:
                try: growth = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
                except: growth = 0.0
                
                local_data.append({
                    "日期": date_str,
                    "单位净值": float(item["DWJZ"]),
                    "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]),
                    "净值增长率": growth
                })
                new_count += 1
                
        if new_count > 0:
            # 重新按日期从新到旧排序
            local_data = sorted(local_data, key=lambda x: x['日期'], reverse=True)
            save_local_history(fund_code, local_data)
            return local_data, f"🎉 蚂蚁搬家成功！本次新搬运储存了 {new_count} 天历史数据！"
        else:
            return local_data, "👌 本页数据已存在于本地历史总库中，无需重复搬运。"
            
    except Exception as e:
        return local_data, f"搬运时网络开小差了 ({str(e)})，已自动展示本地现有库存。"


# --- 1. 全景卡片看板 ---
st.subheader("📋 我的定投核心资产智能执行卡片")
for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    st.markdown(f'<div class="fund-card"><div class="fund-title">📈 {info['name']} ({code})</div><div class="fund-tag">跟踪指数: {info['index_name']}</div> | <div class="fund-tag" style="color:#FFF;">当前计划: {plan_str}</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("10年 PE 百分位", f"{info['pe_percent']:.2f}%")
    c2.metric("当前 PE", f"{info['pe_ttm']:.2f}")
    c3.metric("TTM 股息率", info['div_yield'])
    st.info(strategy_str)

st.markdown("<hr>", unsafe_allow_html=True)


# --- 2. 智能化多维增量穿透大盘（核心进化区） ---
st.subheader("🔍 单只基金历史多维增量穿透总库")
select_detail = st.selectbox("选择要分析/搬运数据的基金：", list(st.session_state.fund_config.keys()),
                             format_func=lambda x: st.session_state.fund_config[x]['name'])

# 初始化加载或增量搬运
current_db = load_local_history(select_detail)

col_btn1, col_btn2, col_info = st.columns([1.5, 1.5, 5])
with col_btn1:
    if st.button("🔄 蚂蚁搬家：顺路下载最新40天数据"):
        current_db, msg = move_ants_history(select_detail, page_index=1)
        st.toast(msg)
with col_btn2:
    # 允许深入历史老数据页面去挖掘更早的40天
    target_page = st.number_input("搬运更深历史(页码)", min_value=1, max_value=100, value=2, step=1)
    if st.button("⛏️ 深度挖掘旧历史"):
        current_db, msg = move_ants_history(select_detail, page_index=target_page)
        st.toast(msg)

# 转换数据用于面板分析
if current_db:
    df_raw = pd.DataFrame(current_db)
    df_raw['日期'] = pd.to_datetime(df_raw['日期'])
    df_raw['年份'] = df_raw['日期'].dt.year
    df_raw['月份'] = df_raw['日期'].dt.strftime('%Y-%m')
    
    st.caption(f"📊 当前本地历史总库已复利滚雪球至：**{len(df_raw)} 天** 历史长度。随着你搬运次数越多，分析越精准！")
    
    t_year, t_month, t_day = st.tabs(["📅 累计年度大盘分析", "🌙 累计月度公允价格中枢", "📄 总库原生日流水"])
    
    with t_year:
        df_year = df_raw.groupby('年份').agg(
            该年有记录天数=('日期', 'count'),
            期间涨跌波动=('净值增长率', 'sum'),
            期间最高单位净值=('单位净值', 'max'),
            期间最低单位净值=('单位净值', 'min')
        ).reset_index().sort_values(by='年份', ascending=False)
        df_year['期间涨跌波动'] = df_year['期间涨跌波动'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)
        
    with t_month:
        df_month = df_raw.groupby('月份').agg(
            月度平均价中枢=('单位净值', 'mean'),
            当月最高价边界=('单位净值', 'max'),
            月度累计波动幅=('净值增长率', 'sum')
        ).reset_index().sort_values(by='月份', ascending=False)
        df_month['月度平均价中枢'] = df_month['月度平均价中枢'].map(lambda x: f"{x:.4f}")
        df_month['当月最高价边界'] = df_month['当月最高价边界'].map(lambda x: f"{x:.4f}")
        df_month['月度累计波动幅'] = df_month['月度累计波动幅'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_month, use_container_width=True, hide_index=True)
        
    with t_day:
        df_display = df_raw.copy()
        df_display['日期'] = df_display['日期'].dt.strftime('%Y-%m-%d')
        df_display['净值增长率'] = df_display['净值增长率'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_display[['日期', '单位净值', '累计净值', '净值增长率']], use_container_width=True, hide_index=True)
else:
    st.info("💡 当前该基金本地总库为空。请点击上方的【蚂蚁搬家】按钮，系统将立刻开始无感建立你的第一批专属历史数据库！")
