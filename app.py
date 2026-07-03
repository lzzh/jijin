import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# 设置网页标题和布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")
st.title("📊 我的智能化定投实时监控看板")
st.markdown("根据底层指数近 10 年真实 PE 百分位及 TTM 股息率，自动输出量化定投执行建议（支持动态修改定投计划）")

# --- 1. 初始化 Session State（确保用户修改的定投计划不会因页面刷新而丢失） ---
if 'fund_config' not in st.session_state:
    st.session_state.fund_config = {
        '008163': {
            'name': '南方标普红利低波50ETF联接A', 
            'index_name': '标普红利低波50',
            'period': '每月21号',
            'amount': 1100,
            'pe_ttm': 8.22, 
            'pe_percent': 84.82,  
            'div_yield': '4.85%', 
            'status': '估值偏高、股息最优',
            'base_strategy': '⚠️ 估值百分位偏高(>80%)。虽然4.85%的股息极具防守性，但短期拥挤度高。建议【维持当前定投不加仓】，或将当前的 {plan} 缩减20%，积攒现金。'
        }, 
        '016452': {
            'name': '南方纳斯达克100指数发起（QDII）A', 
            'index_name': '纳斯达克100',
            'period': '每天',
            'amount': 80,
            'pe_ttm': 34.03, 
            'pe_percent': 76.97, 
            'div_yield': '0.36%', 
            'status': '显著高估、轻微红利',
            'base_strategy': '🚨 处于历史高位区间。美股科技股目前溢价较高，且无红利保护。建议将当前的 {plan} 【下调至 {half_amount} 元左右（防御模式）】，保留子弹等待回调。'
        }, 
        '023882': {
            'name': '华夏创业板50ETF发起式联接A', 
            'index_name': '创业板50',
            'period': '每周二',
            'amount': 100,
            'pe_ttm': 44.48, 
            'pe_percent': 60.78, 
            'div_yield': '0.80%', 
            'status': '中性偏贵、低股息',
            'base_strategy': '等权观望。估值处于60%的中枢偏上位置，成长股弹性较大。建议【严格执行常规计划 {plan}】，不主动防御也不盲目加仓，保持自动扣款。'
        },   
        '023917': {
            'name': '华夏国证自由现金流ETF发起式联接A', 
            'index_name': '国证自由现金流',
            'period': '每周二',
            'amount': 790,
            'pe_ttm': 11.68, 
            'pe_percent': 30.77, 
            'div_yield': '3.20%', 
            'status': '深度低估、均衡现金流',
            'base_strategy': '💎 绝对核心加仓区！PE分位仅30.77%且股息率高达3.2%。属于典型的性价比高地。建议【坚定执行当前计划 {plan}】，甚至可在发薪日额外手动肉身加仓。'
        }   
    }

@st.cache_data(ttl=1800)
def get_fund_history_clean(fund_code):
    """抓取完整的基金历史净值明细"""
    try:
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize=40"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode('utf-8')
        data = json.loads(html)
        
        if data.get("Data") is None or not data["Data"].get("LSJZList"):
            return None, "暂无历史净值流水"
            
        raw_list = data["Data"]["LSJZList"]
        records = []
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): 
                continue 
            records.append({
                "日期": item["FSRQ"],
                "单位净值": float(item["DWJZ"]),
                "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]),
                "净值增长率": f"{item['JZZZL']}%" if item.get("JZZZL") else "0.00%"
            })
        df = pd.DataFrame(records)
        return df, None
    except Exception as e:
        return None, str(e)


# --- 2. 首页核心：全景定投智能化诊断大表（从状态机中动态读取和拼接） ---
st.subheader("📋 我的定投核心资产配置与智能执行看板")

summary_records = []
for code, info in st.session_state.fund_config.items():
    # 动态组装定投计划字符串
    plan_str = f"{info['period']} {info['amount']}元"
    
    # 动态把新的计划金额塞进建议文本里
    strategy_str = info['base_strategy'].format(
        plan=plan_str, 
        half_amount=int(info['amount'] / 2)
    )
    
    summary_records.append({
        "基金代码": code,
        "跟踪指数": info['index_name'],
        "我的定投计划": plan_str,
        "PE-TTM": f"{info['pe_ttm']:.2f}",
        "近10年 PE 百分位": f"{info['pe_percent']:.2f}%",
        "TTM 股息率": info['div_yield'],
        "资产快照定性": info['status'],
        "💡 实时动态定投调整建议": strategy_str
    })

df_summary = pd.DataFrame(summary_records)

# CSS 样式表，保持完美换行
html_style = """
<style>
    .custom-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 14px; color: #E0E0E0; }
    .custom-table th { background-color: #1E232A; color: #FFFFFF; text-align: left; padding: 12px; border: 1px solid #3A3F47; }
    .custom-table td { padding: 12px; border: 1px solid #3A3F47; white-space: normal !important; word-break: break-all; vertical-align: top; }
    .custom-table tr:nth-child(even) { background-color: #161A1F; }
    .custom-table tr:nth-child(odd) { background-color: #0E1116; }
</style>
"""
table_html = df_summary.to_html(classes='custom-table', index=False, escape=False)
st.markdown(html_style + table_html, unsafe_allow_html=True)


# --- 3. 【控制台】动态修改定投计划（周期与金额） ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⚙️ 点击展开：修改每支基金的定投计划（周期/金额）"):
    st.markdown("如果你的定投扣款金额或频率发生了变更，请在下方修改：")
    
    edit_code = st.selectbox("选择要修改定投计划的基金", list(st.session_state.fund_config.keys()), 
                             format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
    
    current_info = st.session_state.fund_config[edit_code]
    
    col_p, col_a = st.columns(2)
    with col_p:
        new_period = st.text_input(f"修改【{current_info['name']}】的定投周期：", value=current_info['period'])
    with col_a:
        new_amount = st.number_input(f"修改【{current_info['name']}】的每期定投金额 (元)：", value=int(current_info['amount']), step=10)
    
    if st.button(f"💾 确认更新 {edit_code} 的定投计划"):
        st.session_state.fund_config[edit_code]['period'] = new_period
        st.session_state.fund_config[edit_code]['amount'] = new_amount
        st.success(f"更新成功！【{current_info['name']}】已变更为 {new_period} {new_amount}元。")
        st.rerun()


st.markdown("<hr>", unsafe_allow_html=True)


# --- 4. 交互展开明细流 ---
st.subheader("🔍 单只基金穿透：点击下方切换基金查看历史净值流水")

tabs = st.tabs([f"📄 {info['name']}" for info in st.session_state.fund_config.values()])

for index, (code, info) in enumerate(st.session_state.fund_config.items()):
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    
    with tabs[index]:
        col1, col2 = st.columns([4, 5])
        with col1:
            st.warning(f"**当前定投模式**: {plan_str}")
            st.info(f"**量化执行指引**: {strategy_str}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("10年市盈率分位", f"{info['pe_percent']:.2f}%")
            c2.metric("当前估值 PE", f"{info['pe_ttm']:.2f}")
            c3.metric("成份股滚动股息率", info['div_yield'])
        
        with col2:
            with st.spinner(f'正在拉取 {info["name"]} 的完整历史交易明细...'):
                df_hist, err = get_fund_history_clean(code)
            if err is None and df_hist is not None:
                st.write(f"📊 **{info['name']} ({code})** 近期历史交易日明细流：")
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.warning(f"该基金历史数据抓取提示：{err}")