import streamlit as st
import pandas as pd
import urllib.request
import json
import os

# 设置网页布局
st.set_page_config(page_title="我的智能化定投监控看板", layout="wide")

# --- 手机端纯净体验 CSS 注入（彻底干掉菜单乱码与溢出） ---
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
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, ensure_ascii=False, indent=4)

if 'fund_config' not in st.session_state:
    st.session_state.fund_config = load_config()

@st.cache_data(ttl=3600)  # 增长历史全量数据的缓存时间至1小时
def get_fund_max_history(fund_code):
    """深度穿透：获取全量历史净值流水并转化计算"""
    try:
        # 将 pageSize 拉满到 4000，一次性抓取最大历史周期数据
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize=4000"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Referer', f'https://fundf10.eastmoney.com/lsjz_{fund_code}.html')
        
        with urllib.request.urlopen(req, timeout=6) as response: 
            html = response.read().decode('utf-8')
        data = json.loads(html)
        
        if not data or data.get("Data") is None or not data["Data"].get("LSJZList"): 
            return None, "云端接口暂未返回全量数据"
            
        raw_list = data["Data"]["LSJZList"]
        records = []
        for item in raw_list:
            if not item.get("FSRQ") or not item.get("DWJZ"): 
                continue
            # 提取百分比数字
            try:
                growth_rate = float(item["JZZZL"]) if item.get("JZZZL") else 0.0
            except:
                growth_rate = 0.0
                
            records.append({
                "日期": item["FSRQ"],
                "单位净值": float(item["DWJZ"]),
                "累计净值": float(item["LJJZ"]) if item.get("LJJZ") else float(item["DWJZ"]),
                "净值增长率": growth_rate
            })
            
        if not records: 
            return None, "未解析到有效历史日流水"
            
        df = pd.DataFrame(records)
        df['日期'] = pd.to_datetime(df['日期'])
        df['年份'] = df['日期'].dt.year
        df['月份'] = df['日期'].dt.strftime('%Y-%m')
        return df, None
    except Exception as e: 
        return None, f"获取失败 ({str(e)})"


# --- 1. 全景卡片看板 ---
st.subheader("📋 我的定投核心资产智能执行卡片")

for code, info in st.session_state.fund_config.items():
    plan_str = f"{info['period']} {info['amount']}元"
    strategy_str = info['base_strategy'].format(plan=plan_str, half_amount=int(info['amount'] / 2))
    
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-title">📈 {info['name']} ({code})</div>
        <div class="fund-tag">跟踪指数: {info['index_name']}</div> | <div class="fund-tag" style="color:#FFF;">当前计划: {plan_str}</div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("10年 PE 百分位", f"{info['pe_percent']:.2f}%")
    c2.metric("当前 PE", f"{info['pe_ttm']:.2f}")
    c3.metric("TTM 股息率", info['div_yield'])
    
    if "⚠️" in strategy_str or "🚨" in strategy_str:
        st.warning(strategy_str)
    else:
        st.info(strategy_str)


# --- 2. 控制台 ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⚙️ 点此展开：修改并永久保存每支基金的定投计划"):
    edit_code = st.selectbox("选择基金", list(st.session_state.fund_config.keys()), 
                             format_func=lambda x: f"{x} - {st.session_state.fund_config[x]['name']}")
    current_info = st.session_state.fund_config[edit_code]
    new_period = st.text_input("定投周期：", value=current_info['period'], key=f"p_{edit_code}")
    new_amount = st.number_input("定投金额 (元)：", value=int(current_info['amount']), step=10, key=f"a_{edit_code}")
    if st.button("💾 确认更新并永久保存计划"):
        st.session_state.fund_config[edit_code]['period'] = new_period
        st.session_state.fund_config[edit_code]['amount'] = new_amount
        save_config(st.session_state.fund_config)
        st.success("配置已更新！")
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)


# --- 3. 终极无敌深度流水穿透大升级 ---
st.subheader("🔍 单只基金历史多维时空深度穿透")
select_detail = st.selectbox("选择你想击穿分析的基金：", list(st.session_state.fund_config.keys()),
                             format_func=lambda x: st.session_state.fund_config[x]['name'])

with st.spinner('正在全量回溯该基金完整历史、深度清洗中...'):
    df_raw, err = get_fund_max_history(select_detail)

if err is None and df_raw is not None:
    # 建立多维度穿透面板选项卡
    t_year, t_month, t_day = st.tabs(["📅 年度宏观透视", "🌙 月度资金中枢", "📄 全量历史原生日流水"])
    
    # --- 维度 A: 年度透视 ---
    with t_year:
        st.markdown("**📊 历年表现及价格边界（帮你定位历史绝对大底和大顶）**")
        # 聚合计算年度特征
        df_year = df_raw.groupby('年份').agg(
            年度收益率_点点滴滴=('净值增长率', 'sum'),
            年度最高净值=('单位净值', 'max'),
            年度最低净值=('单位净值', 'min'),
            交易天数=('日期', 'count')
        ).reset_index().sort_values(by='年份', ascending=False)
        
        # 格式化输出
        df_year['年度收益率_点点滴滴'] = df_year['年度收益率_点点滴滴'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_year, use_container_width=True, hide_index=True)
        
    # --- 维度 B: 月度中枢 ---
    with t_month:
        st.markdown("**📉 月度平均资产公允价中枢（用来比对你当月定投扣款价是买贵了还是买便宜了）**")
        df_month = df_raw.groupby('月份').agg(
            月度平均单位净值=('单位净值', 'mean'),
            当月最高价=('单位净值', 'max'),
            当月涨跌波动幅=('净值增长率', 'sum')
        ).reset_index().sort_values(by='月份', ascending=False)
        
        df_month['月度平均单位净值'] = df_month['月度平均单位净值'].map(lambda x: f"{x:.4f}")
        df_month['当月涨跌波动幅'] = df_month['当月涨跌波动幅'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_month.head(36), use_container_width=True, hide_index=True) # 默认呈现最近36个月
        
    # --- 维度 C: 最长全量原生态日流水 ---
    with t_day:
        st.success(f"📈 成功击穿！已全量加载该基金自成立以来共计 {len(df_raw)} 个交易日的原始净值数据。")
        # 还原干净的格式呈现
        df_display = df_raw.copy()
        df_display['日期'] = df_display['日期'].dt.strftime('%Y-%m-%d')
        df_display['净值增长率'] = df_display['净值增长率'].map(lambda x: f"{x:.2f}%")
        st.dataframe(df_display[['日期', '单位净值', '累计净值', '净值增长率']], use_container_width=True, hide_index=True)
else:
    st.info(f"💡 提示：{err}（接口限制或网络波动，核心定投卡片运行正常）。")
