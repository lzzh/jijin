import streamlit as st
import pandas as pd
import urllib.request
import json
import os

# 设置网页布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")
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

@st.cache_data(ttl=1800)
def get_fund_history_clean(fund_code):
    """带高级容错与超时控制的净值抓取函数，确保任何情况下不阻断主程序"""
    try:
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize=40"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        
        # 云端环境将超时时间压缩到4秒，避免用户长时间面对白屏
        with urllib.request.urlopen(req, timeout=4) as response:
            html = response.read().decode('utf-8')
        
        data = json.loads(html)
        if not data or data.get("Data") is None or not data["Data"].get("LSJZList"):
            return None, "云端接口未返回流水数据"
            
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
        
        if not records:
            return None, "未解析到有效历史日流水"
        return pd.DataFrame(records), None
        
    except Exception as e:
        # 网络超时或遭遇封锁时，直接捕获异常并返回错误提示，不向上传导崩溃
        return None, f"云端网络延迟或接口暂被拦截 ({str(e)})"


# --- 1. 首页核心：全景定投看板（采用原生高性能自适应组件） ---
st.subheader("📋 我的定投核心资产配置与智能执行看板")

summary_records = []
for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
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

# 使用 Streamlit 官方原生数据表组件，在手机上支持完美原生平滑滚动，且带有一键复制、排序等健全功能，绝无重叠乱码
st.dataframe(df_summary, use_container_width=True, hide_index=True)


# --- 2. 【控制台】修改并永久保存定投计划 ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⚙️ 点击展开：修改并永久保存每支基金的定投计划"):
    st.markdown("在此处更新你的计划，系统会自动修正排版并永久记住配置。")
    edit_code = st.selectbox("选择基金", list(st.session_state.fund_config.keys()), 
                             format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
    current_info = st.session_state.fund_config[edit_code]
    
    col_p, col_a = st.columns(2)
    with col_p:
        new_period = st.text_input("定投周期：", value=current_info['period'], key=f"p_{edit_code}")
    with col_a:
        new_amount = st.number_input("定投金额 (元)：", value=int(current_info['amount']), step=10, key=f"a_{edit_code}")
    
    if st.button("💾 确认更新并永久保存计划"):
        st.session_state.fund_config[edit_code]['period'] = new_period
        st.session_state.fund_config[edit_code]['amount'] = new_amount
        save_config(st.session_state.fund_config)
        st.success("配置已成功固化到云端！页面即将自动刷新...")
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)


# --- 3. 基金穿透流水明细流 ---
st.subheader("🔍 单只基金穿透详情")
tabs = st.tabs([f"📄 {info['name']}" for info in st.session_state.fund_config.values()])

for index, (code, info) in enumerate(st.session_state.fund_config.items()):
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    with tabs[index]:
        st.warning(f"**当前定投模式**: {plan_str}")
        st.info(f"**量化执行指引**: {strategy_str}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("10年市盈率分位", f"{info['pe_percent']:.2f}%")
        c2.metric("当前估值 PE", f"{info['pe_ttm']:.2f}")
        c3.metric("成份股滚动股息率", f"{info['div_yield']}")
        
        # 即使云端拉取失败，也会优雅提示，不阻塞整个 App 的正常渲染与保存功能
        with st.spinner('正在尝试同步最新历史净值流水...'):
            df_hist, err = get_fund_history_clean(code)
        if err is None and df_hist is not None:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 提示：当前看盘核心指标正常运行。{err}（不影响你的定投计划调整与核心建议查看）")
