"""Korean ETF data via Naver Finance public endpoints (no API key).
- list : https://finance.naver.com/api/sise/etfItemList.nhn   (all KRX-listed ETFs, NAV, price, volume, market cap)
- chart: https://fchart.stock.naver.com/sise.nhn              (daily OHLCV)
Unofficial endpoints: they can change. Data is for information only.
"""
import json, re, time, threading
import requests

UA = {"User-Agent": "Mozilla/5.0 (kr-etf-lab)"}
CATS = {1: "국내 시장지수", 2: "국내 업종/테마", 3: "국내 파생", 4: "해외 주식",
        5: "원자재", 6: "채권", 7: "기타"}
_lock = threading.Lock()
_cache = {}

def _cached(key, ttl, fn):
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (now, val)
    return val

def _fetch_list():
    r = requests.get("https://finance.naver.com/api/sise/etfItemList.nhn", headers=UA, timeout=15)
    r.raise_for_status()
    items = json.loads(r.content.decode("euc-kr"))["result"]["etfItemList"]
    out = []
    for x in items:
        nav = x.get("nav") or 0
        price = x.get("nowVal") or 0
        out.append({
            "code": x["itemcode"], "name": x["itemname"],
            "cat": CATS.get(x.get("etfTabCode"), "기타"),
            "price": price, "change_rate": x.get("changeRate"),
            "nav": nav or None,
            "premium": round((price / nav - 1) * 100, 2) if nav and price else None,
            "ret_3m": x.get("threeMonthEarnRate"),
            "volume": x.get("quant"),
            "value_mil": x.get("amonut"),      # 거래대금 (백만원)
            "mcap_100m": x.get("marketSum"),   # 시가총액 (억원)
        })
    return out

def etf_list():
    return _cached("list", 600, _fetch_list)

def etf_info(code):
    return next((e for e in etf_list() if e["code"] == code), None)

def _fetch_history(code, count):
    r = requests.get("https://fchart.stock.naver.com/sise.nhn",
                     params={"symbol": code, "timeframe": "day", "count": count, "requestType": 0},
                     headers=UA, timeout=20)
    r.raise_for_status()
    txt = r.content.decode("euc-kr", "ignore")
    rows = re.findall(r'data="(\d{8})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)"', txt)
    return [(d, int(c)) for d, _o, _h, _l, c, _v in rows if int(c) > 0]

def history(code, years=5):
    count = int(years * 252) + 10
    return _cached(f"h:{code}:{count}", 1800, lambda: _fetch_history(code, count))
