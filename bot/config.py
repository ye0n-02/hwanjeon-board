"""통화 목록, 현지 물가 예시, 판정 기준 같은 고정 설정."""

# 표시 순서대로. unit = 하나은행 고시 단위 (JPY, VND는 100단위)
CURRENCIES = [
    {"code": "JPY", "name": "일본 엔화", "short": "엔화", "unit": 100, "unit_label": "100엔", "travel_qty": 10000, "travel_label": "1만엔"},
    {"code": "USD", "name": "미국 달러", "short": "달러", "unit": 1, "unit_label": "1달러", "travel_qty": 100, "travel_label": "100달러"},
    {"code": "EUR", "name": "유로", "short": "유로", "unit": 1, "unit_label": "1유로", "travel_qty": 100, "travel_label": "100유로"},
    {"code": "CNY", "name": "중국 위안", "short": "위안", "unit": 1, "unit_label": "1위안", "travel_qty": 1000, "travel_label": "1,000위안"},
    {"code": "TWD", "name": "대만 달러", "short": "대만달러", "unit": 1, "unit_label": "1대만달러", "travel_qty": 5000, "travel_label": "5,000대만달러"},
    {"code": "THB", "name": "태국 바트", "short": "바트", "unit": 1, "unit_label": "1바트", "travel_qty": 10000, "travel_label": "1만바트"},
    {"code": "VND", "name": "베트남 동", "short": "베트남 동", "unit": 100, "unit_label": "100동", "travel_qty": 1000000, "travel_label": "100만동"},
    {"code": "PHP", "name": "필리핀 페소", "short": "페소", "unit": 1, "unit_label": "1페소", "travel_qty": 10000, "travel_label": "1만페소"},
]
CODES = [c["code"] for c in CURRENCIES]
BY_CODE = {c["code"]: c for c in CURRENCIES}

# 30일 중 위치(백분위) 기준 판정
CHEAP_MAX_PCT = 30   # 이하면 싼 편
PRICEY_MIN_PCT = 70  # 이상이면 비싼 편
HISTORY_DAYS = 30

# 안전장치: 전일 대비 이 이상 움직이면 게시 중단하고 실패 처리
MAX_DAILY_MOVE_PCT = 3.0

# 4장 그래프에 고정으로 그릴 통화
CHART_CODES = ["JPY", "USD", "EUR"]

# 5장 현지 물가 (대략적인 예시 가격)
LOCAL_PRICES = [
    {"code": "JPY", "city": "도쿄", "item": "라멘 한 그릇", "label": "1,000엔", "qty": 1000},
    {"code": "USD", "city": "뉴욕", "item": "아메리카노", "label": "$5", "qty": 5},
    {"code": "EUR", "city": "파리", "item": "크루아상", "label": "€1.5", "qty": 1.5},
    {"code": "CNY", "city": "상하이", "item": "훠궈 1인", "label": "100위안", "qty": 100},
    {"code": "TWD", "city": "타이베이", "item": "버블티", "label": "NT$60", "qty": 60},
    {"code": "THB", "city": "방콕", "item": "팟타이", "label": "60바트", "qty": 60},
    {"code": "VND", "city": "다낭", "item": "쌀국수", "label": "50,000동", "qty": 50000},
    {"code": "PHP", "city": "세부", "item": "망고 셰이크", "label": "120페소", "qty": 120},
]

ACCOUNT = "@hwanjeon.board"
