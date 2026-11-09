"""가짜 30영업일 데이터로 카드를 만들어보는 테스트. 사용: python -m tests.sample /tmp/sample"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from bot import render

BASE = {"JPY": 935.91, "USD": 1490.20, "EUR": 1716.93, "CNY": 216.59, "TWD": 48.86, "THB": 45.85, "VND": 5.67, "PHP": 25.47}
SPREAD = {"JPY": 1.75, "USD": 1.75, "EUR": 1.99, "CNY": 5, "TWD": 8, "THB": 6, "VND": 9, "PHP": 7}


def sample_history(seed: int = 1) -> tuple[dict, str]:
    random.seed(seed)
    vals = {k: v * 1.01 for k, v in BASE.items()}
    days, d = [], date(2026, 9, 25)
    while len(days) < 31:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    hist = {}
    for i, dd in enumerate(days):
        rates = {}
        for k in BASE:
            vals[k] *= 1 + random.gauss(0, 0.003)
            v = round(BASE[k] if i == len(days) - 1 else vals[k], 2)
            rates[k] = {"base": v, "cash_buy": round(v * (1 + SPREAD[k] / 100), 2), "cash_sell": round(v * (1 - SPREAD[k] / 100), 2)}
        hist[dd.isoformat()] = {"rates": rates, "meta": {"time": "09:03", "round": 1}}
    return hist, days[-1].isoformat()


if __name__ == "__main__":
    hist, day = sample_history()
    res = render.build(hist, day, Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sample"), video="--no-video" not in sys.argv)
    print(res["caption"])
    print([f.name for f in res["files"]])
