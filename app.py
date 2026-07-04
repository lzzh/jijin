import streamlit as st
import pandas as pd
import json, os, time, random
import altair as alt

try:
    import requests as rlib
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

# ══════════════════════════════════════════════════════════
#  配置
# ══════════════════════════════════════════════════════════
st.set_page_config(page_title="定投监控看板", layout="centered", initial_sidebar_state="collapsed")

CONFIG_FILE  = "fund_config.json"
HISTORY_DIR  = "fund_history"
CURSOR_FILE  = "fund_cursor.json"
PE_HIST_DIR  = "pe_history"
for d in (HISTORY_DIR, PE_HIST_DIR):
    os.makedirs(d, exist_ok=True)

# index_secid: 东方财富行情代码（SH=1.XXXXXX / SZ=0.XXXXXX）
# 境外指数填 None，PE 只能手动维护
DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A', 'index_name': '标普红利低波50',
        'index_secid': None,
        'period': '每月21号', 'amount': 1100,
        'pe_ttm': 8.22, 'pe_percent': 84.82, 'div_yield': '4.85%',
    },
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A', 'index_name': '纳斯达克100',
        'index_secid': None,
        'period': '每天', 'amount': 80,
        'pe_ttm': 34.03, 'pe_percent': 76.97, 'div_yield': '0.36%',
    },
    '023882': {
        'name': '华夏创业板50ETF发起式联接A', 'index_name': '创业板50',
        'index_secid': '0.399673',
        'period': '每周二', 'amount': 100,
        'pe_ttm': 44.48, 'pe_percent': 60.78, 'div_yield': '0.80%',
    },
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A', 'index_name': '国证自由现金流',
        'index_secid': '0.399387',
        'period': '每周二', 'amount': 790,
        'pe_ttm': 11.68, 'pe_percent': 30.77, 'div_yield': '3.20%',
    },
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE, encoding='utf-8'))
        except Exception:
            pass
    return {k: dict(v) for k, v in DEFAULT_CONFIG.items()}

def save_config(cfg):
    json.dump(cfg, open(CONFIG_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def load_history(code):
    p = os.path.join(HISTORY_DIR, f'{code}.json')
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
    return []

def save_history(code, data):
    data = sorted(data, key=lambda x: x['日期'], reverse=True)
    json.dump(data, open(os.path.join(HISTORY_DIR, f'{code}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

def load_cursors():
    if os.path.exists(CURSOR_FILE):
        try:
            return json.load(open(CURSOR_FILE, encoding='utf-8'))
        except Exception:
            pass
    return {}

def save_cursors(c):
    json.dump(c, open(CURSOR_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def load_pe_history(code):
    p = os.path.join(PE_HIST_DIR, f'{code}.json')
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
    return []

def save_pe_history(code, records):
    json.dump(records, open(os.path.join(PE_HIST_DIR, f'{code}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

if 'cfg' not in st.session_state:
    st.session_state.cfg = load_config()

# ══════════════════════════════════════════════════════════
#  网络工具
# ══════════════════════════════════════════════════════════
_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'Accept': 'application/json, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

def http_get(url, extra_headers=None, timeout=15):
    """返回 (text, error)，失败时 text=None"""
    h = {**_HEADERS, **(extra_headers or {})}
    try:
        if HAS_REQUESTS:
            r = rlib.get(url, headers=h, timeout=timeout)
            r.raise_for_status()
            return r.text, None
        req = urllib.request.Request(url)
        for k, v in h.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        try:
            import gzip
            return gzip.decompress(raw).decode('utf-8'), None
        except Exception:
            return raw.decode('utf-8'), None
    except Exception as e:
        return None, str(e)

_INVALID = {'-', '--', '', 'null', 'None', '0', '0.0'}

def _parse_float(v):
    """安全转 float，失败返回 None"""
    try:
        f = float(v)
        return f if f > 0 else None
    except Exception:
        return None

def fetch_index_raw(secid):
    """
    从东方财富 push2 接口抓取指数全部常用字段，用于诊断哪个字段是 PE。
    返回 (field_dict, error)
    已知字段含义（股票/指数可能有差异）：
      f9   = 市盈率(动)   f114 = 市盈率(静)   f115 = 市盈率(TTM)
      f116 = 市净率(PB)   f117 = 市销率(PS)
      f162 = 股息率(动)   f163 = 股息率(静)
      f14  = 名称         f2   = 最新价
    """
    fields = 'f2,f9,f114,f115,f116,f117,f162,f163,f14'
    url = (
        'https://push2.eastmoney.com/api/qt/stock/get'
        f'?ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2&invt=2'
        f'&fields={fields}&secid={secid}'
    )
    text, err = http_get(url)
    if text is None:
        return None, err
    try:
        return json.loads(text).get('data', {}), None
    except Exception as e:
        return None, f'解析失败: {e}'

def fetch_index_valuation(secid):
    """
    多源交叉获取指数估值数据。
    返回 dict: {pe_ttm, pe_dyn, pe_static, pb, div_yield, source_notes}
    每个字段都有来源标注，供用户判断可信度。
    """
    result = {
        'pe_ttm': None, 'pe_dyn': None, 'pe_static': None,
        'pb': None, 'div_yield': None, 'notes': []
    }

    # ── 来源 A：push2 行情接口（字段诊断）──
    raw, err = fetch_index_raw(secid)
    if raw:
        # 东方财富对指数的字段含义与股票略有差异，f115 才是 PE TTM
        pe_ttm    = _parse_float(raw.get('f115'))
        pe_dyn    = _parse_float(raw.get('f9'))
        pe_static = _parse_float(raw.get('f114'))
        pb        = _parse_float(raw.get('f116'))
        div       = _parse_float(raw.get('f162'))

        result.update({
            'pe_ttm':    pe_ttm,
            'pe_dyn':    pe_dyn,
            'pe_static': pe_static,
            'pb':        pb,
            'div_yield': f'{div:.2f}%' if div else None,
        })
        result['notes'].append(
            f'push2[f9={raw.get("f9")} f114={raw.get("f114")} '
            f'f115={raw.get("f115")} f116={raw.get("f116")} f162={raw.get("f162")}]'
        )
    else:
        result['notes'].append(f'push2 失败: {err}')

    # ── 来源 B：东方财富数据中心（指数基本面专用表）──
    market, code_only = secid.split('.')
    suffix = 'SH' if market == '1' else 'SZ'
    secucode = f'{code_only}.{suffix}'
    dc_url = (
        'https://datacenter-web.eastmoney.com/api/data/v1/get'
        f'?reportName=RPT_INDEX_BASIC_FINDATA'
        f'&columns=SECUCODE,INDEX_CODE,PETTM,PE,PB,DIVIDENDYIELD'
        f'&filter=(SECUCODE="{secucode}")'
    )
    text2, err2 = http_get(dc_url)
    if text2:
        try:
            rows = json.loads(text2).get('result', {}).get('data') or []
            if rows:
                row = rows[0]
                dc_pe_ttm = _parse_float(row.get('PETTM'))
                dc_pe     = _parse_float(row.get('PE'))
                dc_pb     = _parse_float(row.get('PB'))
                dc_div    = _parse_float(row.get('DIVIDENDYIELD'))
                # 以数据中心结果覆盖（该接口为指数专用，更可信）
                if dc_pe_ttm: result['pe_ttm']    = dc_pe_ttm
                if dc_pe:     result['pe_static']  = dc_pe
                if dc_pb:     result['pb']          = dc_pb
                if dc_div:    result['div_yield']   = f'{dc_div:.2f}%'
                result['notes'].append(
                    f'datacenter[PETTM={row.get("PETTM")} PE={row.get("PE")} '
                    f'PB={row.get("PB")} DIV={row.get("DIVIDENDYIELD")}]'
                )
            else:
                result['notes'].append('datacenter 返回空行')
        except Exception as e:
            result['notes'].append(f'datacenter 解析失败: {e}')
    else:
        result['notes'].append(f'datacenter 失败: {err2}')

    return result

def fetch_nav_page(code, page):
    """
    抓取基金历史净值单页（东方财富标准接口）。
    返回 (records_list, error_str)
    records_list=None 表示网络/解析失败；[] 表示该页已到底
    """
    url = (
        f'https://api.fund.eastmoney.com/f10/lsjz'
        f'?fundCode={code}&pageIndex={page}&pageSize=40'
        f'&_={int(time.time()*1000)}'
    )
    extra = {
        'Referer': f'https://fundf10.eastmoney.com/lsjz_{code}.html',
        'Origin': 'https://fundf10.eastmoney.com',
        'X-Requested-With': 'XMLHttpRequest',
    }
    text, err = http_get(url, extra_headers=extra)
    if text is None:
        return None, err
    try:
        data = json.loads(text)
    except Exception:
        return None, f'返回非JSON（可能被拦截）: {text[:80]}'
    if data.get('Data') is None:
        return None, f'Data字段为空，可能触发限流'
    rows = data['Data'].get('LSJZList', [])
    if not rows:
        return [], '该页为空（已到历史底部）'
    records = []
    for r in rows:
        if not r.get('FSRQ') or not r.get('DWJZ'):
            continue
        try:
            growth = float(r['JZZZL']) if r.get('JZZZL') else 0.0
        except (ValueError, TypeError):
            growth = 0.0
        records.append({
            '日期': r['FSRQ'],
            '单位净值': float(r['DWJZ']),
            '累计净值': float(r.get('LJJZ') or r['DWJZ']),
            '净值增长率': growth,
        })
    return records, None

# ══════════════════════════════════════════════════════════
#  双向历史同步
# ══════════════════════════════════════════════════════════
def sync_forward(code, max_pages=10):
    """
    向前同步（追最新数据）：从第1页开始，直到整页数据全部已存在为止。
    返回 (new_count, log_lines)
    """
    local = load_history(code)
    existing = {r['日期'] for r in local}
    new_count, logs = 0, []
    for p in range(1, max_pages + 1):
        records, err = fetch_nav_page(code, p)
        if records is None:
            logs.append(f'  向前 第{p}页 ⚠️ {err}')
            break
        if not records:
            logs.append(f'  向前 第{p}页 已到底部')
            break
        new_on_page = [r for r in records if r['日期'] not in existing]
        if not new_on_page:
            logs.append(f'  向前 第{p}页 全部已存在，停止向前')
            break
        for r in new_on_page:
            local.append(r)
            existing.add(r['日期'])
        new_count += len(new_on_page)
        logs.append(f'  向前 第{p}页 ✅ +{len(new_on_page)}条')
        time.sleep(random.uniform(1.2, 2.0))
    if new_count:
        save_history(code, local)
    return new_count, logs

def sync_backward(code, pages=20):
    """
    向后同步（挖历史数据）：从上次游标继续往深处挖。
    返回 (new_count, log_lines, new_cursor)
    """
    local = load_history(code)
    existing = {r['日期'] for r in local}
    cursors = load_cursors()
    start_page = cursors.get(code, {}).get('backward_page', 1)
    new_count, logs = 0, []
    last_page = start_page
    for p in range(start_page, start_page + pages):
        records, err = fetch_nav_page(code, p)
        if records is None:
            logs.append(f'  向后 第{p}页 ⚠️ {err}')
            break
        if not records:
            logs.append(f'  向后 第{p}页 已到历史底部，全量同步完成 🎉')
            break
        new_on_page = [r for r in records if r['日期'] not in existing]
        for r in new_on_page:
            local.append(r)
            existing.add(r['日期'])
        new_count += len(new_on_page)
        last_page = p + 1
        logs.append(f'  向后 第{p}页 ✅ +{len(new_on_page)}条（已存{len(existing)}条）')
        time.sleep(random.uniform(1.5, 2.5))
    if new_count:
        save_history(code, local)
    cursors.setdefault(code, {})['backward_page'] = last_page
    save_cursors(cursors)
    return new_count, logs, last_page

# ══════════════════════════════════════════════════════════
#  PE 百分位：基于本地 PE 历史自动累积计算
# ══════════════════════════════════════════════════════════
def record_and_calc_pe_percent(code, pe_now):
    """
    将今日 PE 存入本地历史，并返回历史百分位（越多数据越准确）。
    """
    today = time.strftime('%Y-%m-%d')
    hist = load_pe_history(code)
    hist = [r for r in hist if r['date'] != today]  # 去重
    hist.append({'date': today, 'pe': pe_now})
    save_pe_history(code, hist)
    vals = [r['pe'] for r in hist]
    if len(vals) < 2:
        return None  # 数据太少，不显示百分位
    below = sum(1 for v in vals if v < pe_now)
    return round(below / len(vals) * 100, 1)

# ══════════════════════════════════════════════════════════
#  策略评估（纯函数，不存配置）
# ══════════════════════════════════════════════════════════
def evaluate_strategy(pe_percent, period, amount):
    half   = max(10, int(amount * 0.5))
    double = int(amount * 1.5)
    plan   = f"{period} {amount}元"
    if pe_percent >= 75:
        return 'high', f'🚨 PE百分位 {pe_percent:.1f}%，估值偏高。建议将定投金额临时下调至 {half} 元，保留现金仓位等待回调。'
    elif pe_percent <= 35:
        return 'low',  f'💎 PE百分位 {pe_percent:.1f}%，深度低估区！建议坚定执行 {plan}，或加码至 {period} {double} 元。'
    else:
        return 'mid',  f'⚖️ PE百分位 {pe_percent:.1f}%，估值均衡。严格按计划执行 {plan}。'

# ══════════════════════════════════════════════════════════
#  CSS（mobile-first 暗色金融终端）
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
#MainMenu,footer,header{visibility:hidden}
*{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Inter','PingFang SC',sans-serif;background:#080C12!important;color:#C9D1D9!important}
.block-container{padding:.75rem .75rem 3rem!important;max-width:680px!important}
@media(min-width:768px){.block-container{padding:1.5rem 2rem 2rem!important}}
[data-testid="stVerticalBlock"]>div{gap:0!important}

.dash-header{background:linear-gradient(135deg,#0D1117,#111827,#0D1117);border:1px solid #1F2937;border-radius:12px;padding:16px;margin-bottom:16px;position:relative;overflow:hidden}
.dash-header::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#F0A500,#58A6FF,transparent)}
.dash-header h1{font-size:17px!important;font-weight:700!important;color:#E6EDF3!important;margin:0 0 4px!important}
.dash-header .sub{font-size:11px;color:#6E7681;font-family:'JetBrains Mono',monospace;line-height:1.6}

.sec{font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#F0A500;margin:20px 0 12px;display:flex;align-items:center;gap:10px}
.sec::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,#1F2937,transparent)}
.divider{height:1px;background:linear-gradient(90deg,transparent,#1F2937,transparent);margin:18px 0}

.fcard{background:#0D1117;border:1px solid #1F2937;border-radius:12px;padding:14px 14px 14px 18px;margin-bottom:10px;position:relative}
.fcard::before{content:'';position:absolute;left:0;top:10px;bottom:10px;width:3px;border-radius:0 2px 2px 0}
.fcard.low::before{background:#2DA44E}.fcard.mid::before{background:#F0A500}.fcard.high::before{background:#F85149}
.fcard-hdr{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
@media(min-width:480px){.fcard-hdr{flex-direction:row;justify-content:space-between;align-items:flex-start}}
.fname{font-size:14px;font-weight:600;color:#E6EDF3;line-height:1.4}
.fcode{font-family:'JetBrains Mono',monospace;font-size:11px;color:#6E7681;margin-top:2px}
.badge{background:#161B22;border:1px solid #21262D;border-radius:20px;padding:5px 12px;font-size:12px;color:#58A6FF;font-family:'JetBrains Mono',monospace;white-space:nowrap;min-height:32px;display:flex;align-items:center;align-self:flex-start}

.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.mcell{background:#161B22;border-radius:8px;padding:10px 8px;text-align:center}
.mlbl{font-size:9px;color:#6E7681;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;line-height:1.3}
.mval{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:600;color:#E6EDF3}
@media(min-width:400px){.mval{font-size:17px}}
.mval.low{color:#2DA44E}.mval.mid{color:#F0A500}.mval.high{color:#F85149}

.sbox{border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.6;color:#C9D1D9}
.sbox.low{background:#0F2A1A;border:1px solid #2DA44E33}
.sbox.mid{background:#1F1A0A;border:1px solid #F0A50033}
.sbox.high{background:#2A0F0F;border:1px solid #F8514933}
.sbox.info{background:#0D1F33;border:1px solid #58A6FF33}

div[data-testid="stSelectbox"]>div>div,
div[data-testid="stTextInput"]>div>div>input,
div[data-testid="stNumberInput"]>div>div>input,
div[data-testid="stTextArea"]>div>textarea{background:#161B22!important;border-color:#21262D!important;color:#C9D1D9!important;border-radius:8px!important;font-size:16px!important}
div[data-testid="stButton"]>button{background:#161B22!important;border:1px solid #21262D!important;color:#C9D1D9!important;border-radius:8px!important;min-height:44px!important;font-size:14px!important;width:100%!important}
div[data-testid="stButton"]>button[kind="primary"]{background:linear-gradient(135deg,#1A3A5C,#0D2A45)!important;border-color:#58A6FF!important;color:#58A6FF!important}
div[data-testid="stRadio"]>div{gap:6px!important;flex-wrap:wrap!important}
div[data-testid="stRadio"] label{background:#161B22!important;border:1px solid #21262D!important;border-radius:8px!important;padding:8px 12px!important;min-height:40px!important;font-size:13px!important;display:flex!important;align-items:center!important}
div[data-testid="stRadio"] label:has(input:checked){border-color:#F0A500!important;background:#1F1A0A!important}
button[data-baseweb="tab"]{background:transparent!important;color:#6E7681!important;border-bottom:2px solid transparent!important;border-radius:0!important;font-size:12px!important;min-height:40px!important}
button[data-baseweb="tab"][aria-selected="true"]{color:#F0A500!important;border-bottom-color:#F0A500!important}
[data-testid="stDataFrame"]{border:1px solid #1F2937!important;border-radius:8px!important;overflow-x:auto!important}
[data-testid="stDataFrame"] td,[data-testid="stDataFrame"] th{font-size:12px!important;white-space:nowrap!important}
div[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,#F0A500,#58A6FF)!important}
label[data-testid="stCheckbox"]{color:#C9D1D9!important;min-height:40px!important;display:flex!important;align-items:center!important}
@supports(padding-bottom:env(safe-area-inset-bottom)){.block-container{padding-bottom:calc(3rem + env(safe-area-inset-bottom))!important}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════════════════
cfg = st.session_state.cfg
total_mo = sum(
    i['amount'] * 21 if i['period'] == '每天'
    else i['amount'] * 4.3 if '周' in i['period']
    else i['amount']
    for i in cfg.values()
)
st.markdown(f"""
<div class="dash-header">
  <h1>📊 定投监控看板</h1>
  <div class="sub">
    {len(cfg)} 只监控资产 &nbsp;·&nbsp;
    月投约 <span style="color:#F0A500;font-weight:600">{total_mo:,.0f}</span> 元
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  § 1  资产卡片
# ══════════════════════════════════════════════════════════
st.markdown('<div class="sec">资产配置 · 估值执行状态</div>', unsafe_allow_html=True)
for code, info in cfg.items():
    pe_p  = info.get('pe_percent', 50.0)
    lvl, strategy = evaluate_strategy(pe_p, info['period'], info['amount'])
    pc    = 'high' if pe_p >= 75 else ('low' if pe_p <= 35 else 'mid')
    secid = info.get('index_secid')
    pe_src = '手动' if secid is None else '自动'

    st.markdown(f"""
    <div class="fcard {lvl}">
      <div class="fcard-hdr">
        <div>
          <div class="fname">{info['name']}</div>
          <div class="fcode">{code} · {info['index_name']}</div>
        </div>
        <div class="badge">{info['period']}  {info['amount']} 元</div>
      </div>
      <div class="mgrid">
        <div class="mcell">
          <div class="mlbl">PE 百分位<br>({pe_src})</div>
          <div class="mval {pc}">{pe_p:.1f}%</div>
        </div>
        <div class="mcell">
          <div class="mlbl">PE TTM</div>
          <div class="mval">{info.get('pe_ttm', 0):.2f}</div>
        </div>
        <div class="mcell">
          <div class="mlbl">TTM 股息率</div>
          <div class="mval {lvl}">{info.get('div_yield','—')}</div>
        </div>
      </div>
      <div class="sbox {lvl}">{strategy}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  § 2  走势图
# ══════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec">净值走势穿透</div>', unsafe_allow_html=True)

chart_code = st.selectbox(
    '选择基金',
    list(cfg.keys()),
    format_func=lambda x: f'[{x}]  {cfg[x]["name"]}'
)
hist_data = load_history(chart_code)

if hist_data:
    df = pd.DataFrame(hist_data)
    df['日期'] = pd.to_datetime(df['日期'])
    df['月份'] = df['日期'].dt.strftime('%Y-%m')
    df_mo = df.groupby('月份').agg(月均=('单位净值','mean'), 月高=('单位净值','max')).reset_index()
    df = df.merge(df_mo, on='月份', how='left')

    tf = st.radio('时间视窗', ['近1月','近3月','近6月','近1年','全部'], horizontal=True, index=4)
    dmap = {'近1月':30,'近3月':90,'近6月':180,'近1年':365}
    df_f = df[df['日期'] >= df['日期'].max()-pd.Timedelta(days=dmap[tf])] if tf in dmap else df

    melted = df_f.melt('日期', ['单位净值','月均','月高'], '指标', '净值')
    chart = (
        alt.Chart(melted).mark_line(strokeWidth=1.8).encode(
            x=alt.X(
                '日期:T',
                title='',
                axis=alt.Axis(
                    labelColor='#6E7681',
                    gridColor='#1F2937',
                    domainColor='#1F2937',
                    labelExpr="month(datum.value)==0 ? substring(toString(year(datum.value)),2,4) : toString(month(datum.value)+1)"
                )
            ),
            y=alt.Y('净值:Q', title='', scale=alt.Scale(zero=False, padding=15),
                    axis=alt.Axis(labelColor='#6E7681', gridColor='#1F2937', domainColor='#1F2937')),
            color=alt.Color('指标:N',
                scale=alt.Scale(domain=['单位净值','月均','月高'], range=['#58A6FF','#2DA44E','#F85149']),
                legend=alt.Legend(title='', labelColor='#C9D1D9', orient='top-right')),
            tooltip=['日期:T','指标:N', alt.Tooltip('净值:Q', format='.4f')]
        ).properties(height=260, background='#0D1117')
        .configure_view(strokeOpacity=0)
        .configure_axis(labelFont='Inter')
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    df['年份'] = df['日期'].dt.year
    t1, t2, t3 = st.tabs(['📅 年度','🌙 月度','📄 逐日'])
    with t1:
        dy = df.groupby('年份').agg(天数=('日期','count'), 波动=('净值增长率','sum'),
                                     最高=('单位净值','max'), 最低=('单位净值','min')).reset_index().sort_values('年份', ascending=False)
        dy['波动'] = dy['波动'].map(lambda x: f'{x:+.2f}%')
        st.dataframe(dy, use_container_width=True, hide_index=True)
    with t2:
        dm = df.groupby('月份').agg(月均=('单位净值','mean'), 月高=('单位净值','max'),
                                     波动=('净值增长率','sum')).reset_index().sort_values('月份', ascending=False)
        dm['月均'] = dm['月均'].map(lambda x: f'{x:.4f}')
        dm['月高'] = dm['月高'].map(lambda x: f'{x:.4f}')
        dm['波动'] = dm['波动'].map(lambda x: f'{x:+.2f}%')
        st.dataframe(dm, use_container_width=True, hide_index=True)
    with t3:
        dd = df.copy().sort_values('日期', ascending=False)
        dd['日期'] = dd['日期'].dt.strftime('%Y-%m-%d')
        dd['净值增长率'] = dd['净值增长率'].map(lambda x: f'{x:+.2f}%')
        st.dataframe(dd[['日期','单位净值','累计净值','净值增长率']], use_container_width=True, hide_index=True)
else:
    st.markdown('<div class="sbox info">💡 本地暂无历史数据，请前往下方"数据同步"面板下载。</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  § 3  控制台
# ══════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec">数据同步 · 参数管理</div>', unsafe_allow_html=True)

tab_sync, tab_pe, tab_mgmt = st.tabs(['📡 历史净值同步', '📊 指数PE更新', '⚙️ 资产管理'])

# ─── Tab 1: 双向历史同步 ───────────────────────────────
with tab_sync:
    # 各基金本地数据概况
    rows = []
    cursors = load_cursors()
    for code, info in cfg.items():
        h = load_history(code)
        dates = sorted(r['日期'] for r in h)
        cursor_page = cursors.get(code, {}).get('backward_page', 1)
        rows.append({
            '基金': f'[{code}]',
            '已存条数': len(h),
            '最早日期': dates[0] if dates else '—',
            '最新日期': dates[-1] if dates else '—',
            '历史游标': f'第{cursor_page}页',
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown('**运行策略**：先向前追最新数据，再向后接着游标挖历史。')
    c1, c2 = st.columns(2)
    with c1:
        fwd_pages  = st.number_input('向前最多页数', value=5,  min_value=1, max_value=50)
    with c2:
        back_pages = st.number_input('向后挖掘页数', value=20, min_value=1, max_value=200)

    target = st.selectbox(
        '同步目标',
        ['全部基金'] + list(cfg.keys()),
        format_func=lambda x: x if x == '全部基金' else f'[{x}] {cfg[x]["name"]}'
    )

    if st.button('🚀 开始同步', type='primary'):
        codes = list(cfg.keys()) if target == '全部基金' else [target]
        log_store = []
        total_new = 0
        bar = st.progress(0)
        status = st.empty()
        for i, code in enumerate(codes):
            name = cfg[code]['name']
            # Phase 1: forward
            status.info(f'[{code}] {name} — 向前追新数据…')
            fn, fl = sync_forward(code, max_pages=int(fwd_pages))
            total_new += fn
            log_store += [f'**[{code}] 向前**'] + fl

            # Phase 2: backward
            status.info(f'[{code}] {name} — 向后挖历史…')
            bn, bl, _ = sync_backward(code, pages=int(back_pages))
            total_new += bn
            log_store += [f'**[{code}] 向后**'] + bl
            bar.progress((i+1)/len(codes))

        status.empty()
        bar.empty()
        st.session_state.sync_log = {'total': total_new, 'lines': log_store}
        st.rerun()

    if 'sync_log' in st.session_state and st.session_state.sync_log:
        slog = st.session_state.sync_log
        if slog['total'] > 0:
            st.success(f"✅ 本次共写入 {slog['total']} 条新数据")
        else:
            st.info('ℹ️ 本次无新数据写入')
        with st.expander('查看详细日志'):
            for l in slog['lines']:
                st.markdown(l)
        if st.button('清除日志'):
            st.session_state.sync_log = {}
            st.rerun()

# ─── Tab 2: PE 更新 ────────────────────────────────────
with tab_pe:
    st.markdown("""
    <div class="sbox info">
    📌 <b>数据来源说明</b><br>
    · <b>来源A</b>：东方财富 push2 行情接口（f115=PE TTM，f9=动态PE，f114=静态PE，f162=股息率）<br>
    · <b>来源B</b>：东方财富数据中心指数基本面专用表（PETTM / DIVIDENDYIELD，更可信）<br>
    · 两源结果会同时显示供你对比，不一致时以数据中心（B源）为准<br>
    · 境外指数（纳指/标普）无 A 股行情代码，只能手动维护
    </div>
    """, unsafe_allow_html=True)

    if st.button('🔍 获取所有 A 股指数估值（双源对比）', type='primary'):
        st.session_state.pe_fetch_results = {}
        for code, info in cfg.items():
            secid = info.get('index_secid')
            if not secid:
                continue
            with st.spinner(f'获取 [{code}] {info["index_name"]}…'):
                val = fetch_index_valuation(secid)
            st.session_state.pe_fetch_results[code] = val

    if st.session_state.get('pe_fetch_results'):
        st.markdown('---')
        st.markdown('**📊 原始数据对比（确认后点击应用）**')
        apply_targets = {}

        for code, val in st.session_state.pe_fetch_results.items():
            info = cfg[code]
            st.markdown(f"**[{code}] {info['index_name']}**")

            # 展示双源数据
            cols = st.columns(4)
            def show_val(col, label, v, highlight=False):
                color = '#F0A500' if highlight and v else '#E6EDF3'
                col.markdown(
                    f'<div class="mcell"><div class="mlbl">{label}</div>'
                    f'<div class="mval" style="color:{color};font-size:14px">'
                    f'{v if v is not None else "—"}</div></div>',
                    unsafe_allow_html=True
                )
            show_val(cols[0], 'PE TTM（推荐用）', val['pe_ttm'], highlight=True)
            show_val(cols[1], 'PE 动态',          val['pe_dyn'])
            show_val(cols[2], 'PE 静态',          val['pe_static'])
            show_val(cols[3], '股息率（自动）',    val['div_yield'])

            with st.expander('查看原始字段（诊断用）'):
                for note in val['notes']:
                    st.code(note, language=None)

            # 让用户确认要应用的值
            best_pe = val['pe_ttm'] or val['pe_dyn'] or val['pe_static']
            c1, c2 = st.columns(2)
            with c1:
                confirmed_pe = st.number_input(
                    f'确认 PE TTM [{code}]',
                    value=float(best_pe) if best_pe else float(info.get('pe_ttm', 15)),
                    step=0.1, format='%.2f', key=f'confirm_pe_{code}'
                )
            with c2:
                confirmed_div = st.text_input(
                    f'确认股息率 [{code}]',
                    value=val['div_yield'] or info.get('div_yield', ''),
                    key=f'confirm_div_{code}'
                )
            apply_targets[code] = {'pe': confirmed_pe, 'div': confirmed_div}
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        if st.button('✅ 应用所有确认值并保存'):
            for code, vals in apply_targets.items():
                pct = record_and_calc_pe_percent(code, vals['pe'])
                cfg[code]['pe_ttm'] = vals['pe']
                if vals['div']:
                    cfg[code]['div_yield'] = vals['div']
                if pct is not None:
                    cfg[code]['pe_percent'] = pct
                    st.markdown(f'✅ [{code}] PE={vals["pe"]}，股息率={vals["div"]}，'
                                f'百分位={pct}%（{len(load_pe_history(code))}个样本）')
                else:
                    st.markdown(f'✅ [{code}] PE={vals["pe"]}，股息率={vals["div"]}（样本不足，百分位请手动填）')
            save_config(cfg)
            st.session_state.cfg = cfg
            st.session_state.pe_fetch_results = {}
            st.rerun()

    st.markdown('---')
    st.markdown('**手动维护估值参数**（PE 百分位始终需手动或等样本积累）')
    edit_code = st.selectbox('选择基金', list(cfg.keys()),
                              format_func=lambda x: f'[{x}] {cfg[x]["name"]}',
                              key='pe_edit_sel')
    ei = cfg[edit_code]
    with st.form('pe_form'):
        c1, c2, c3 = st.columns(3)
        with c1: new_pe  = st.number_input('PE TTM',    value=float(ei.get('pe_ttm',15)), step=0.1, format='%.2f')
        with c2: new_pct = st.number_input('PE 百分位%', value=float(ei.get('pe_percent',50)), step=0.1, format='%.1f')
        with c3: new_div = st.text_input('TTM 股息率',  value=str(ei.get('div_yield','2.00%')))
        if st.form_submit_button('💾 保存'):
            cfg[edit_code].update({'pe_ttm': new_pe, 'pe_percent': new_pct, 'div_yield': new_div})
            save_config(cfg)
            st.session_state.cfg = cfg
            st.success('✅ 已保存')
            st.rerun()

# ─── Tab 3: 资产管理 ───────────────────────────────────
with tab_mgmt:
    mgmt_code = st.selectbox('选择基金', list(cfg.keys()),
                               format_func=lambda x: f'[{x}] {cfg[x]["name"]}',
                               key='mgmt_sel')
    mi = cfg[mgmt_code]
    with st.form('mgmt_form'):
        c1, c2 = st.columns(2)
        with c1: new_period = st.text_input('定投周期', value=mi['period'])
        with c2: new_amount = st.number_input('定投金额（元）', value=int(mi['amount']), step=10)
        new_index  = st.text_input('指数名称', value=mi.get('index_name',''))
        new_secid  = st.text_input('指数行情代码（如 0.399673，境外填空）',
                                    value=mi.get('index_secid','') or '')
        if st.form_submit_button('💾 保存'):
            cfg[mgmt_code].update({
                'period': new_period, 'amount': new_amount,
                'index_name': new_index,
                'index_secid': new_secid.strip() or None,
            })
            save_config(cfg)
            st.session_state.cfg = cfg
            st.success('✅ 已保存')
            st.rerun()

    st.markdown('---')
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown('##### ➕ 添加基金')
        with st.form('add_form'):
            a_code   = st.text_input('基金代码', max_chars=6)
            a_name   = st.text_input('基金简称')
            a_index  = st.text_input('指数名称')
            a_secid  = st.text_input('指数行情代码（境外填空）')
            a_period = st.text_input('定投周期', value='每周二')
            a_amount = st.number_input('金额（元）', value=100, step=10)
            if st.form_submit_button('创建'):
                if len(a_code) != 6 or not a_name:
                    st.error('⚠️ 代码或名称无效')
                else:
                    cfg[a_code] = {'name': a_name, 'index_name': a_index,
                                   'index_secid': a_secid.strip() or None,
                                   'period': a_period, 'amount': a_amount,
                                   'pe_ttm': 15.0, 'pe_percent': 50.0, 'div_yield': '2.00%'}
                    save_config(cfg)
                    st.session_state.cfg = cfg
                    st.success(f'✅ [{a_code}] 已添加')
                    st.rerun()
    with c_del:
        st.markdown('##### 🗑️ 删除基金')
        del_code = st.selectbox('目标', list(cfg.keys()),
                                 format_func=lambda x: f'[{x}] {cfg[x]["name"]}',
                                 key='del_sel')
        if st.checkbox('确认删除（不可恢复）'):
            if st.button('🔥 删除'):
                del cfg[del_code]
                save_config(cfg)
                st.session_state.cfg = cfg
                for f in [os.path.join(HISTORY_DIR, f'{del_code}.json'),
                          os.path.join(PE_HIST_DIR, f'{del_code}.json')]:
                    if os.path.exists(f):
                        os.remove(f)
                st.success('✅ 已删除')
                st.rerun()
