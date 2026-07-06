import streamlit as st
import pandas as pd
import json, os, time, random, base64
import altair as alt
import html # 关键：转义 HTML 特殊字符

try:
    import requests as rlib
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

# ══════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════
st.set_page_config(page_title="定投监控看板", layout="wide", initial_sidebar_state="collapsed")

CONFIG_FILE = "fund_config.json"
HISTORY_DIR = "fund_history"
CURSOR_FILE = "fund_cursor.json"
PE_HIST_DIR = "pe_history"

for d in (HISTORY_DIR, PE_HIST_DIR):
    os.makedirs(d, exist_ok=True)

# index_secid: 东方财富行情代码（SH=1.XXXXXX / SZ=0.XXXXXX）
# 境外指数填 None，PE 只能手动维护
DEFAULT_CONFIG = {
    '008163': {
        'name': '南方标普红利低波50ETF联接A',
        'index_name': '标普红利低波50',
        'index_secid': None,
        'period': '每月21号',
        'amount': 1100,
        'pe_ttm': 8.22,
        'pe_percent': 84.82,
        'div_yield': '4.85%',
    },
    '016452': {
        'name': '南方纳斯达克100指数发起（QDII）A',
        'index_name': '纳斯达克100',
        'index_secid': None,
        'period': '每天',
        'amount': 80,
        'pe_ttm': 34.03,
        'pe_percent': 76.97,
        'div_yield': '0.36%',
    },
    '023882': {
        'name': '华夏创业板50ETF发起式联接A',
        'index_name': '创业板50',
        'index_secid': '0.399673',
        'period': '每周二',
        'amount': 100,
        'pe_ttm': 44.48,
        'pe_percent': 60.78,
        'div_yield': '0.80%',
    },
    '023917': {
        'name': '华夏国证自由现金流ETF发起式联接A',
        'index_name': '国证自由现金流',
        'index_secid': '0.399387',
        'period': '每周二',
        'amount': 790,
        'pe_ttm': 11.68,
        'pe_percent': 30.77,
        'div_yield': '3.20%',
    },
}

# ══════════════════════════════════════════════════════════
# GitHub 持久化层（替代 Streamlit Cloud 临时文件系统）
# Secrets 需配置：GITHUB_TOKEN / GITHUB_REPO / GITHUB_BRANCH(可选)
# ══════════════════════════════════════════════════════════
def _gh_enabled():
    try:
        return bool(st.secrets.get("GITHUB_TOKEN") and st.secrets.get("GITHUB_REPO"))
    except Exception:
        return False

def _gh_headers():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "") or ""
    except Exception:
        token = ""
    if not token: return {}
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

def gh_read(path):
    """从 GitHub 仓库读取文件，返回 (content_str, sha) 或 (None, None)"""
    if not _gh_enabled(): return None, None
    try:
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main") or "main"
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
        
        if HAS_REQUESTS:
            r = rlib.get(url, headers=_gh_headers(), timeout=10)
            if r.status_code == 200:
                d = r.json()
                return base64.b64decode(d['content']).decode('utf-8'), d['sha']
        else:
            req = urllib.request.Request(url)
            for k, v in _gh_headers().items(): req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read())
                return base64.b64decode(d['content']).decode('utf-8'), d['sha']
    except Exception:
        pass
    return None, None

def gh_write(path, content_str):
    """将文件写入 GitHub 仓库（自动获取 SHA，新建或覆盖均可）"""
    if not _gh_enabled(): return False
    try:
        _, sha = gh_read(path)
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main") or "main"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        
        payload = {
            "message": f"auto: update {path}",
            "content": base64.b64encode(content_str.encode('utf-8')).decode(),
            "branch": branch,
        }
        if sha: payload["sha"] = sha
        
        if HAS_REQUESTS:
            r = rlib.put(url, headers=_gh_headers(), json=payload, timeout=20)
            return r.status_code in (200, 201)
        else:
            body = json.dumps(payload).encode('utf-8')
            h = {**_gh_headers(), "Content-Type": "application/json"}
            req = urllib.request.Request(url, data=body, method="PUT")
            for k, v in h.items(): req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status in (200, 201)
    except Exception:
        pass
    return False

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE, encoding='utf-8'))
        except Exception: pass
    
    content, _ = gh_read(CONFIG_FILE)
    if content:
        try:
            data = json.loads(content)
            json.dump(data, open(CONFIG_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            return data
        except Exception: pass
    return {k: dict(v) for k, v in DEFAULT_CONFIG.items()}

def save_config(cfg):
    content = json.dumps(cfg, ensure_ascii=False, indent=2)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: f.write(content)
    gh_write(CONFIG_FILE, content)

def load_history(code):
    p = os.path.join(HISTORY_DIR, f'{code}.json')
    if os.path.exists(p):
        try: return json.load(open(p, encoding='utf-8'))
        except Exception: pass
    
    content, _ = gh_read(f'{HISTORY_DIR}/{code}.json')
    if content:
        try:
            data = json.loads(content)
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            return data
        except Exception: pass
    return []

def save_history(code, data):
    data = sorted(data, key=lambda x: x['日期'], reverse=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    with open(os.path.join(HISTORY_DIR, f'{code}.json'), 'w', encoding='utf-8') as f: f.write(content)
    gh_write(f'{HISTORY_DIR}/{code}.json', content)

def load_cursors():
    if os.path.exists(CURSOR_FILE):
        try: return json.load(open(CURSOR_FILE, encoding='utf-8'))
        except Exception: pass
    
    content, _ = gh_read(CURSOR_FILE)
    if content:
        try:
            data = json.loads(content)
            json.dump(data, open(CURSOR_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            return data
        except Exception: pass
    return {}

def save_cursors(c):
    content = json.dumps(c, ensure_ascii=False, indent=2)
    with open(CURSOR_FILE, 'w', encoding='utf-8') as f: f.write(content)
    gh_write(CURSOR_FILE, content)

def load_pe_history(code):
    p = os.path.join(PE_HIST_DIR, f'{code}.json')
    if os.path.exists(p):
        try: return json.load(open(p, encoding='utf-8'))
        except Exception: pass
    
    content, _ = gh_read(f'{PE_HIST_DIR}/{code}.json')
    if content:
        try:
            data = json.loads(content)
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            return data
        except Exception: pass
    return []

def save_pe_history(code, records):
    content = json.dumps(records, ensure_ascii=False, indent=2)
    with open(os.path.join(PE_HIST_DIR, f'{code}.json'), 'w', encoding='utf-8') as f: f.write(content)
    gh_write(f'{PE_HIST_DIR}/{code}.json', content)

if 'cfg' not in st.session_state:
    st.session_state.cfg = load_config()

# ══════════════════════════════════════════════════════════
# 网络工具
# ══════════════════════════════════════════════════════════
_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'Accept': 'application/json, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

def http_get(url, extra_headers=None, timeout=30): # 超时延长至30秒
    """返回 (text, error)，失败时 text=None"""
    h = {**_HEADERS, **(extra_headers or {})}
    try:
        if HAS_REQUESTS:
            r = rlib.get(url, headers=h, timeout=timeout)
            r.raise_for_status()
            return r.text, None
        else:
            req = urllib.request.Request(url)
            for k, v in h.items(): req.add_header(k, v)
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
    """
    fields = 'f2,f9,f114,f115,f116,f117,f162,f163,f14'
    url = (
        'https://push2.eastmoney.com/api/qt/stock/get'
        f'?ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2&invt=2'
        f'&fields={fields}&secid={secid}'
    )
    text, err = http_get(url)
    if text is None: return None, err
    try:
        return json.loads(text).get('data', {}), None
    except Exception as e:
        return None, f'解析失败: {e}'

def fetch_index_valuation(secid):
    """
    多源交叉获取指数估值数据。
    来源A: 东方财富 push2（字段诊断用）
    来源B: 深交所官方估值接口（SZ指数专用，最权威）
    来源C: 上交所官方接口（SH指数专用）
    返回 dict: {pe_ttm, pe_static, pb, div_yield, notes}
    """
    result = {'pe_ttm': None, 'pe_static': None, 'pb': None, 'div_yield': None, 'notes': []}
    market, code_only = secid.split('.')
    
    # ── 来源 A：push2 行情接口（字段说明）────────────────
    # 对"指数"，各字段实际含义与股票不同：
    # f9 = 动态PE（指数通常为空）
    # f114 = 静态PE（有值，可参考）
    # f115 = 对指数无意义，常为0，不可用
    # f116 = 总市值（万亿量级），不是PB
    # f162 = 股息率（可能为空）
    raw, err = fetch_index_raw(secid)
    if raw:
        pe_static = _parse_float(raw.get('f114'))
        div = _parse_float(raw.get('f162'))
        pb_raw = _parse_float(raw.get('f116'))
        pb = pb_raw if (pb_raw and pb_raw < 100) else None
        
        if pe_static: result['pe_static'] = pe_static
        if pb: result['pb'] = pb
        if div: result['div_yield'] = f'{div:.2f}%'
        
        result['notes'].append(
            f'push2 ▶ f9(动态PE)={raw.get("f9")} '
            f'f114(静态PE)={raw.get("f114")} '
            f'f115(指数无效)={raw.get("f115")} '
            f'f116(总市值非PB)={raw.get("f116")} '
            f'f162(股息率)={raw.get("f162")}'
        )
    else:
        result['notes'].append(f'push2 失败: {err}')

    # ── 来源 B：深交所官方估值（SZ指数）────────────────
    if market == '0': # 深交所指数估值：尝试多个公开端点
        szse_urls = [
            (
                'https://www.szse.cn/api/report/ShowReport/data'
                '?SHOWTYPE=JSON&CATALOGID=1815_zhishu&TABKEY=tab1&random=0.1',
                {'Referer': 'https://www.szse.cn/market/bond/index/index.html'}
            ),
            (
                'https://www.szse.cn/market/product/index/index/index.html',
                {'Referer': 'https://www.szse.cn/'}
            ),
        ]
        fetched = False
        for szse_url, extra_h in szse_urls:
            text_sz, err_sz = http_get(szse_url, extra_headers=extra_h)
            if text_sz and text_sz.strip().startswith('['):
                try:
                    rows = json.loads(text_sz)
                    matched = [r for r in rows if str(r.get('zqdm', '')).strip() == code_only]
                    if matched:
                        r = matched[0]
                        pe_ttm = _parse_float(r.get('syl2'))
                        pe_static = _parse_float(r.get('syl1'))
                        pb = _parse_float(r.get('sjl'))
                        div_raw = str(r.get('jzl', '')).replace('%', '').strip()
                        div = _parse_float(div_raw)
                        
                        if pe_ttm: result['pe_ttm'] = pe_ttm
                        if pe_static and not result['pe_static']: result['pe_static'] = pe_static
                        if pb: result['pb'] = pb
                        if div: result['div_yield'] = f'{div:.2f}%'
                        
                        result['notes'].append(
                            f'深交所官方 ▶ {r.get("zqjc")} '
                            f'滚动PE={r.get("syl2")} 静态PE={r.get("syl1")} '
                            f'PB={r.get("sjl")} 股息率={r.get("jzl")}'
                        )
                        fetched = True
                        break
                    else:
                        result['notes'].append(f'深交所 ▶ 未找到 {code_only}，共{len(rows)}条')
                        fetched = True
                        break
                except Exception as e:
                    result['notes'].append(f'深交所 ▶ 解析失败: {e}')
            else:
                result['notes'].append(f'深交所 ▶ {szse_url[:50]}… 失败: {err_sz or "非JSON响应"}')
        
        if not fetched:
            # 所有深交所端点均失败，降级用 push2 的 f114 静态PE
            result['notes'].append('深交所所有接口不可用，PE 仅参考 push2 静态值（f114）')

    # ── 来源 C：上交所官方估值（SH指数）────────────────
    elif market == '1':
        sse_url = (
            'http://query.sse.com.cn/sseQuery/commonSoaQuery.do'
            '?sqlId=COMMON_SSE_ZQPZ_XXPL_GFZQPZ_L&fileType=json&isPagination=false'
        )
        text_sh, err_sh = http_get(
            sse_url,
            extra_headers={'Referer': 'http://www.sse.com.cn/'},
            timeout=15
        )
        if text_sh:
            try:
                rows = json.loads(text_sh).get('result', [])
                matched = [r for r in rows if str(r.get('ZQDM', '')).strip() == code_only]
                if matched:
                    r = matched[0]
                    pe_ttm = _parse_float(r.get('HQSYL'))
                    pb = _parse_float(r.get('HQSJL'))
                    if pe_ttm: result['pe_ttm'] = pe_ttm
                    if pb: result['pb'] = pb
                    result['notes'].append(
                        f'上交所官方 ▶ 滚动PE={r.get("HQSYL")} PB={r.get("HQSJL")}'
                    )
                else:
                    result['notes'].append(f'上交所 ▶ 未找到代码 {code_only}，共{len(rows)}条')
            except Exception as e:
                result['notes'].append(f'上交所 ▶ 解析失败: {e}')
        else:
            result['notes'].append(f'上交所 ▶ 请求失败: {err_sh}')
            
    return result

def fetch_nav_page(code, page):
    """
    抓取基金历史净值单页（东方财富标准接口）。
    返回 (records_list, error_str) records_list=None 表示网络/解析失败；[] 表示该页已到底
    """
    url = (
        f'https://api.fund.eastmoney.com/f10/lsjz'
        f'?fundCode={code}&pageIndex={page}&pageSize=40'
        f'&_{int(time.time()*1000)}'
    )
    extra = {
        'Referer': f'https://fundf10.eastmoney.com/lsjz_{code}.html',
        'Origin': 'https://fundf10.eastmoney.com',
        'X-Requested-With': 'XMLHttpRequest',
    }
    text, err = http_get(url, extra_headers=extra)
    if text is None: return None, err
    try:
        data = json.loads(text)
    except Exception:
        return None, f'返回非JSON（可能被拦截）: {text[:80]}'
    
    if data.get('Data') is None:
        return None, f'Data字段为空，可能触发限流'
    
    rows = data['Data'].get('LSJZList', [])
    if not rows: return [], '该页为空（已到历史底部）'
    
    records = []
    for r in rows:
        if not r.get('
