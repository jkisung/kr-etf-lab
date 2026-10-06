# KR ETF Lab

국내 상장 ETF 조회 + 포트폴리오 구성 도우미 (Flask + 바닐라 JS, DB 없음).

## 실행
    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py        # http://localhost:5000

## 기능
- ETF 목록: 전체 상장 ETF(약 1,170개) 검색/분류/정렬, 현재가·NAV·괴리율·3개월수익률·시총
- 상세: 5년 종가 차트, 연환산 수익률/변동성/최대낙폭/샤프
- 포트폴리오: 비중 입력, 투자금 -> 종목별 매수 수량, 백테스트(연/월 리밸런싱), 상관계수
- 비중 자동 제안: 동일비중 / 변동성 역가중 / 리스크 패리티 / 최소분산(long-only, 종목당 상한 설정)

## 데이터
네이버 금융 공개 엔드포인트 (API 키 불필요, 비공식이라 변경될 수 있음)
- 목록: finance.naver.com/api/sise/etfItemList.nhn
- 시세: fchart.stock.naver.com/sise.nhn
pykrx는 2026년 현재 KRX 로그인(KRX_ID/PW)이 필요해서 쓰지 않았어요.
수익률은 가격 기준(분배금 미포함). 투자 권유가 아니에요.

## 무료 배포 (Render)
GitHub에 올린 뒤 Render > New Web Service, render.yaml 자동 인식 (Free 플랜).
15분 유휴 시 잠들고 첫 접속에 약 1분 걸려요. 또는 Procfile 사용 가능한 PaaS 어디든.
