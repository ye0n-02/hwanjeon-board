"""매일 수집한 환율 기록 (data/history.json) 관리와 30일 통계."""
from __future__ import annotations

import json
from pathlib import Path

from .config import CHEAP_MAX_PCT, HISTORY_DAYS, PRICEY_MIN_PCT

PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {}


def save(hist: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(hist.items()))
    PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")


def upsert(hist: dict, day: str, rates: dict, meta: dict | None = None) -> None:
    hist[day] = {"rates": rates, "meta": meta or {}}


def series(hist: dict, code: str, upto: str, days: int = HISTORY_DAYS) -> list[tuple[str, float]]:
    pts = [(d, v["rates"][code]["base"]) for d, v in sorted(hist.items()) if d <= upto and code in v["rates"]]
    return pts[-days:]


def verdict(pct: float) -> str:
    if pct <= CHEAP_MAX_PCT:
        return "싼 편"
    if pct >= PRICEY_MIN_PCT:
        return "비싼 편"
    return "보통"


def stats(hist: dict, code: str, day: str) -> dict:
    pts = series(hist, code, day)
    today = hist[day]["rates"][code]["base"]
    prev = pts[-2][1] if len(pts) >= 2 else None
    window = [v for _, v in pts]
    avg = sum(window) / len(window)
    # 오늘 값이 최근 30일 중 아래에서 몇 % 위치인지 (낮을수록 싸다)
    below = sum(1 for v in window if v < today)
    equal = sum(1 for v in window if v == today)
    pct = 100 * (below + 0.5 * equal) / len(window) if len(window) > 1 else 50.0
    return {
        "today": today,
        "prev": prev,
        "diff": (today - prev) if prev is not None else None,
        "avg": avg,
        "avg_diff_pct": (today - avg) / avg * 100,
        "pct": round(pct),
        "verdict": verdict(pct),
        "n": len(window),
        "series": pts,
    }
