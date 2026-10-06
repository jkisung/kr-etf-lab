import numpy as np
from data import history

TD = 252

def aligned_returns(codes, years):
    series = {c: dict(history(c, years)) for c in codes}
    dates = sorted(set.intersection(*[set(s) for s in series.values()]))
    if len(dates) < 30:
        raise ValueError("겹치는 거래일이 너무 적어요 (상장 기간이 짧은 ETF가 있을 수 있어요)")
    dates = dates[-int(years * TD):]
    px = np.array([[series[c][d] for c in codes] for d in dates], dtype=float)
    return dates, px, px[1:] / px[:-1] - 1

def stats(daily):
    daily = np.asarray(daily)
    n = len(daily)
    eq = np.cumprod(1 + daily)
    cagr = eq[-1] ** (TD / n) - 1
    vol = daily.std(ddof=1) * np.sqrt(TD)
    peak = np.maximum.accumulate(eq)
    mdd = (eq / peak - 1).min()
    sharpe = daily.mean() * TD / vol if vol > 0 else 0.0   # rf=0
    return {"cagr": cagr, "vol": vol, "mdd": mdd, "sharpe": sharpe, "total": eq[-1] - 1}

def backtest(rets, weights, dates, rebalance="yearly"):
    w0 = np.asarray(weights, float)
    w = w0.copy()
    port = []
    for i, r in enumerate(rets):
        g = w * (1 + r)
        tot = g.sum()
        port.append(tot - 1)
        w = g / tot
        d, nd = dates[i + 1], dates[i + 2] if i + 2 < len(dates) else None
        if nd:
            if rebalance == "monthly" and d[:6] != nd[:6]:
                w = w0.copy()
            elif rebalance == "yearly" and d[:4] != nd[:4]:
                w = w0.copy()
    return np.array(port)

def _proj_simplex(v):
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1
    k = np.nonzero(u - css / (np.arange(len(v)) + 1) > 0)[0][-1]
    return np.maximum(v - css[k] / (k + 1), 0)

def suggest(rets, method, max_w=1.0):
    n = rets.shape[1]
    cov = np.cov(rets.T) * TD if n > 1 else np.array([[rets.var(ddof=1) * TD]])
    cov = np.atleast_2d(cov)
    vol = np.sqrt(np.diag(cov))
    if method == "equal":
        w = np.ones(n) / n
    elif method == "inv_vol":
        w = (1 / vol) / (1 / vol).sum()
    elif method == "min_var":
        w = np.ones(n) / n
        lr = 0.5 / max(np.linalg.eigvalsh(cov).max(), 1e-9)
        for _ in range(3000):
            w = _proj_simplex(w - lr * 2 * cov @ w)
    elif method == "risk_parity":
        w = (1 / vol) / (1 / vol).sum()
        for _ in range(500):
            rc = w * (cov @ w)
            w = w * (rc.mean() / np.maximum(rc, 1e-12)) ** 0.5
            w /= w.sum()
    else:
        raise ValueError("unknown method")
    if max_w < 1 and max_w * n >= 1:
        for _ in range(20):
            over = w > max_w
            if not over.any(): break
            excess = (w[over] - max_w).sum()
            w[over] = max_w
            free = ~over
            w[free] += excess * w[free] / w[free].sum()
    return w

def portfolio(codes, weights, years, rebalance):
    dates, px, rets = aligned_returns(codes, years)
    w = np.asarray(weights, float); w = w / w.sum()
    port = backtest(rets, w, dates, rebalance)
    eq = np.cumprod(1 + port)
    peak = np.maximum.accumulate(eq)
    corr = np.corrcoef(rets.T) if len(codes) > 1 else np.array([[1.0]])
    step = max(1, len(eq) // 250)
    idx = list(range(0, len(eq), step))
    if idx[-1] != len(eq) - 1: idx.append(len(eq) - 1)
    per = [{"code": c, **{k: float(v) for k, v in stats(rets[:, i]).items()}} for i, c in enumerate(codes)]
    return {
        "start": dates[0], "end": dates[-1], "days": len(rets),
        "weights": [float(x) for x in w],
        "stats": {k: float(v) for k, v in stats(port).items()},
        "per_asset": per,
        "corr": [[float(x) for x in row] for row in corr],
        "curve": [{"d": dates[i + 1], "v": float(eq[i] * 100), "dd": float((eq[i] / peak[i] - 1) * 100)} for i in idx],
    }
