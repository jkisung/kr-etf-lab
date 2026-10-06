import os
from flask import Flask, jsonify, request, send_from_directory
import numpy as np
import data, analytics

app = Flask(__name__, static_folder="static", static_url_path="")

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/etfs")
def etfs():
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("cat", "")
    sort = request.args.get("sort", "mcap_100m")
    items = data.etf_list()
    if q: items = [e for e in items if q in e["name"].lower() or q in e["code"]]
    if cat: items = [e for e in items if e["cat"] == cat]
    if sort in ("mcap_100m", "value_mil", "ret_3m", "change_rate", "volume"):
        items = sorted(items, key=lambda e: (e.get(sort) is None, -(e.get(sort) or 0)))
    return jsonify({"total": len(items), "cats": list(data.CATS.values()), "items": items[:int(request.args.get("limit", 100))]})

@app.get("/api/etf/<code>")
def etf(code):
    info = data.etf_info(code)
    if not info: return jsonify(error="없는 종목코드예요"), 404
    h = data.history(code, 5)
    closes = [c for _, c in h]
    out = {"info": info, "history": [{"d": d, "c": c} for d, c in (h[::max(1, len(h)//300)] + h[-1:])]}
    if len(closes) > 30:
        r = np.array(closes[1:]) / np.array(closes[:-1]) - 1
        out["stats"] = {k: float(v) for k, v in analytics.stats(r).items()}
        out["stats"]["days"] = len(r)
    return jsonify(out)

def _parse(body):
    items = body.get("items", [])
    codes = [i["code"] for i in items]
    if not 1 <= len(codes) <= 15 or len(set(codes)) != len(codes):
        raise ValueError("ETF를 1~15개 (중복 없이) 골라주세요")
    for c in codes:
        if not data.etf_info(c): raise ValueError(f"없는 종목코드: {c}")
    return items, codes, min(max(float(body.get("years", 3)), 0.5), 10)

@app.post("/api/portfolio")
def portfolio():
    try:
        items, codes, years = _parse(request.get_json(force=True))
        w = [max(float(i.get("weight", 0)), 0) for i in items]
        if sum(w) <= 0: raise ValueError("비중 합이 0이에요")
        return jsonify(analytics.portfolio(codes, w, years, request.get_json().get("rebalance", "yearly")))
    except (ValueError, KeyError) as e:
        return jsonify(error=str(e)), 400

@app.post("/api/suggest")
def suggest():
    try:
        body = request.get_json(force=True)
        items, codes, years = _parse(body)
        _, _, rets = analytics.aligned_returns(codes, years)
        w = analytics.suggest(rets, body.get("method", "inv_vol"), float(body.get("max_weight", 1)))
        return jsonify({"weights": {c: round(float(x), 4) for c, x in zip(codes, w)}})
    except (ValueError, KeyError) as e:
        return jsonify(error=str(e)), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
