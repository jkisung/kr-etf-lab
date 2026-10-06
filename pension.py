"""연금저축 월 분배금 포트폴리오 도구 (교육/참고용, 투자 권유 아님).
분배율은 직접 관리하는 값입니다 (집계 사이트 TTM 기준, 세전). 가격은 data.py의 네이버 시세를 사용합니다.
"""
import math
from flask import jsonify, request
import data

ASOF = "2026-09-30"
SOURCE = "pension.habitfactory.co 등 집계 사이트의 최근 12개월(TTM) 분배율, 세전. 정확한 값은 운용사 공시를 확인하세요."

ETFS = {
    "458730": dict(name="TIGER 미국배당다우존스", y=3.1, fee=0.01, style="배당성장", note="안정적 분배, 낮은 분배율"),
    "446720": dict(name="SOL 미국배당다우존스", y=3.2, fee=0.01, style="배당성장", note="월 분배금 변동이 큰 편"),
    "490490": dict(name="SOL 미국배당미국채혼합50", y=3.1, fee=0.15, style="주식+채권 혼합", note="미국배당주 50% + 미국 10년 국채 50%, 환노출"),
    "441640": dict(name="KODEX 미국배당커버드콜액티브", y=9.7, fee=0.19, style="커버드콜", note="S&P500 기반, 상승장 수익 제한"),
    "458760": dict(name="TIGER 미국배당다우존스타겟커버드콜2호", y=10.7, fee=0.39, style="커버드콜", note="최근 3개월 가격 약 -12%, 원금 잠식 주의"),
    "498410": dict(name="KODEX 금융고배당TOP10타겟위클리커버드콜", y=16.5, fee=0.39, style="커버드콜(국내 금융)", note="목표 분배율 연 15%, 지속성 가장 불확실"),
}
REF_ONLY = {"472150": "TIGER 배당커버드콜액티브: TTM 22%대이나 가격 급등(+96.8%) 영향이고 월 분배금 편차가 커서 기준 분배율로 쓰지 않음"}

MIXES = {
    "stable": dict(label="안정형", desc="배당성장 + 주식/채권 혼합 중심. 분배율은 낮지만 원금 변동과 잠식 우려가 작은 편",
                   w={"490490": 50, "458730": 25, "446720": 25}),
    "balanced": dict(label="균형형", desc="커버드콜 약 50% + 배당성장 30% + 혼합 20%",
                     w={"441640": 25, "458760": 25, "458730": 30, "490490": 20}),
    "high": dict(label="고배당형", desc="커버드콜 비중이 큼. 분배율은 높지만 NAV 하락(원금 잠식) 위험이 가장 큼",
                 w={"441640": 30, "458760": 30, "498410": 20, "458730": 20}),
}
PENSION_TAX = 5.5  # 만 70세 미만 연금소득세율(%)

CAVEATS = [
    "참고용 계산이며 투자 권유가 아닙니다. 분배율은 과거(최근 12개월) 기준이고 미래 분배금은 보장되지 않습니다.",
    "커버드콜 ETF는 분배율이 높아도 기초지수 상승을 일부 포기하고, 하락장에서는 NAV(가격)가 줄어 원금이 잠식될 수 있습니다.",
    "연금저축계좌 안에서 받은 분배금은 계좌 안에서 재투자됩니다. 현금으로 받으려면 만 55세 이후 연금수령(10년 이상 분할)을 신청해야 합니다.",
    "연금수령 시 연금소득세 3.3~5.5%(연령별)가 부과됩니다. 사적연금 합계가 연 1,500만원을 넘으면 종합과세(또는 16.5% 분리과세) 대상입니다.",
    "연금저축 연 납입한도는 1,800만원(IRP 합산 시 세액공제 한도는 별도)입니다. 필요한 원금이 크면 여러 해에 걸쳐 납입해야 합니다.",
    "연금저축펀드(증권사)에서만 ETF 매매가 가능하며, 연금저축보험은 불가합니다. 레버리지/인버스, 해외상장 ETF는 연금계좌에서 살 수 없습니다.",
    "가격은 비공식 네이버 시세(지연 가능), 분배율은 수동 관리 값입니다. 주수는 현재가 기준 내림이며 매매 수수료/스프레드는 반영하지 않았습니다.",
]

def build(target, mix_key, after_tax):
    mix = MIXES[mix_key]
    gross_month = target / (1 - PENSION_TAX / 100) if after_tax else target
    blended = sum(ETFS[c]["y"] * w / 100 for c, w in mix["w"].items())
    principal = gross_month * 12 / (blended / 100)
    rows, tot_cost, tot_month = [], 0, 0.0
    for c, w in mix["w"].items():
        e = ETFS[c]; info = data.etf_info(c) or {}
        price = info.get("price") or 0
        alloc = principal * w / 100
        shares = math.floor(alloc / price) if price else None
        cost = shares * price if shares is not None else None
        month = (cost if cost is not None else alloc) * e["y"] / 100 / 12
        if cost is not None: tot_cost += cost
        tot_month += month
        rows.append(dict(code=c, name=e["name"], style=e["style"], weight=w, yield_pct=e["y"], fee=e["fee"], note=e["note"],
                         price=price or None, alloc=round(alloc), shares=shares, cost=cost, month=round(month),
                         ret_3m=info.get("ret_3m"), asof=ASOF))
    warns = []
    if gross_month * 12 > 15_000_000:
        warns.append("연 연금수령액이 1,500만원을 넘어 종합과세/분리과세 검토가 필요합니다.")
    if principal > 18_000_000:
        warns.append(f"필요 원금이 연 납입한도 1,800만원을 넘으므로 약 {math.ceil(principal / 18_000_000)}년 이상 납입이 필요합니다.")
    if mix_key == "high":
        warns.append("고배당형은 커버드콜 비중이 커서 NAV 하락 위험이 큽니다. 분배율이 높아도 총수익은 낮을 수 있습니다.")
    return dict(mix=mix_key, label=mix["label"], desc=mix["desc"], target=target, after_tax=after_tax,
                gross_month=round(gross_month), blended_yield=round(blended, 2), principal=round(principal),
                invested=tot_cost or None, expected_month=round(tot_month),
                expected_month_after_tax=round(tot_month * (1 - PENSION_TAX / 100)),
                rows=rows, warnings=warns, asof=ASOF, source=SOURCE, caveats=CAVEATS)

def register(app):
    @app.get("/pension")
    def pension_page():
        from flask import send_from_directory
        return send_from_directory("static", "pension.html")

    @app.get("/api/pension/universe")
    def pension_universe():
        return jsonify(asof=ASOF, source=SOURCE, etfs=[dict(code=c, **e) for c, e in ETFS.items()],
                       ref_only=REF_ONLY, mixes={k: dict(label=m["label"], desc=m["desc"], w=m["w"]) for k, m in MIXES.items()},
                       caveats=CAVEATS)

    @app.get("/api/pension/plan")
    def pension_plan():
        try:
            target = int(float(request.args.get("target", "0")))
            if not 10_000 <= target <= 10_000_000:
                raise ValueError("목표 월 분배금은 1만원~1,000만원 사이로 입력해주세요")
            mix = request.args.get("mix", "balanced")
            if mix not in MIXES: raise ValueError("알 수 없는 구성이에요")
            after = request.args.get("after_tax", "0") in ("1", "true")
            return jsonify(build(target, mix, after))
        except ValueError as e:
            return jsonify(error=str(e)), 400
