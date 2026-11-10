"""실행 진입점.

python -m bot.main build      # 오늘 환율 수집 → 카드 생성 (docs/posts/날짜/)
python -m bot.main publish    # Pages에 올라간 카드를 인스타에 게시 (POST_ENABLED=true일 때만)
python -m bot.main backfill   # 지난 영업일 환율을 채워 30일 통계 준비
python -m bot.main probe      # 하나은행 응답 구조 확인용
python -m bot.main whoami     # 인스타 토큰 확인용
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from . import hana
from . import history as H
from .config import CODES, MAX_DAILY_MOVE_PCT

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "docs" / "posts"
PAGES_BASE = os.environ.get("PAGES_BASE", "https://ye0n-02.github.io/hwanjeon-board").rstrip("/")


def out(key: str, value: str) -> None:
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"[{key}] {value}")


def today_kst() -> date:
    return datetime.now(KST).date()


def cmd_build(args) -> int:
    day = date.fromisoformat(args.date) if args.date else today_kst()
    if day.weekday() >= 5:
        out("skip", "weekend")
        return 0
    if (POSTS / day.isoformat() / "posted.json").exists():
        out("skip", "already-posted")
        return 0
    hist = H.load()
    rates = meta = None
    for attempt in range(args.retries + 1):
        try:
            rates, meta, _ = hana.fetch(day)
            if meta.get("date") and meta["date"] != day.isoformat():
                raise hana.FetchError(f"오늘 고시가 아직 없음 (페이지 날짜 {meta['date']})")
            break
        except Exception as e:  # noqa: BLE001
            print(f"수집 실패 {attempt + 1}회: {e}")
            rates = None
            if attempt < args.retries:
                time.sleep(args.wait)
    if not rates:
        # 공휴일이면 고시가 없다. 실패로 처리해서 메일 알림을 받되, 게시는 안 한다.
        out("skip", "no-data")
        return 1
    missing = [c for c in CODES if c not in rates]
    if missing:
        print(f"경고: 빠진 통화 {missing}")
    H.upsert(hist, day.isoformat(), rates, meta)

    # 안전장치: 전일 대비 급변
    prev_days = sorted(d for d in hist if d < day.isoformat())
    if prev_days:
        prev = hist[prev_days[-1]]["rates"]
        for c, r in rates.items():
            if c in prev:
                move = abs(r["base"] / prev[c]["base"] - 1) * 100
                if move > MAX_DAILY_MOVE_PCT:
                    H.save(hist)
                    out("skip", f"anomaly-{c}-{move:.1f}pct")
                    print(f"{c}가 전일 대비 {move:.1f}% 움직임. 숫자 확인 전까지 게시 안 함.")
                    return 1
    H.save(hist)

    from . import render
    folder = POSTS / day.isoformat()
    render.build(hist, day.isoformat(), folder, video=not args.no_video)
    (ROOT / "docs" / "latest.json").write_text(json.dumps({"day": day.isoformat()}, ensure_ascii=False), encoding="utf-8")
    out("skip", "false")
    out("day", day.isoformat())
    return 0


def wait_public(url: str, timeout: int = 600) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.head(url, timeout=15, allow_redirects=True)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(15)
    raise RuntimeError(f"Pages에 아직 안 올라옴: {url}")


def cmd_publish(args) -> int:
    day = args.date or json.loads((ROOT / "docs" / "latest.json").read_text())["day"]
    folder = POSTS / day
    data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    if (folder / "posted.json").exists():
        print("이미 게시한 날짜야. 건너뜀.")
        return 0
    enabled = os.environ.get("POST_ENABLED", "").lower() == "true"
    media = []
    for name in data["files"]:
        if name == "01.jpg" and "01.mp4" in data["files"]:
            continue  # 1장은 영상으로
        kind = "video" if name.endswith(".mp4") else "image"
        media.append({"type": kind, "url": f"{PAGES_BASE}/posts/{day}/{name}"})
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    print(json.dumps(media, ensure_ascii=False, indent=1))
    if not enabled:
        print("확인 모드 (POST_ENABLED != true): 인스타에는 안 올림.")
        out("posted", "false")
        return 0
    for m in media:
        wait_public(m["url"])
    from . import instagram
    mid = instagram.publish_carousel(os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"], media, caption)
    (folder / "posted.json").write_text(json.dumps({"media_id": mid, "at": datetime.now(KST).isoformat()}), encoding="utf-8")
    out("posted", mid)
    return 0


def cmd_backfill(args) -> int:
    hist = H.load()
    end = today_kst() - timedelta(days=1)
    d, added = end, 0
    while d >= end - timedelta(days=args.days):
        if d.weekday() < 5 and d.isoformat() not in hist:
            try:
                rates, meta, _ = hana.fetch(d)
                if meta.get("date") in (None, d.isoformat()):
                    H.upsert(hist, d.isoformat(), rates, meta)
                    added += 1
                    print(d, len(rates), meta)
                else:
                    print(d, "다른 날짜 고시 반환 (공휴일로 보고 건너뜀)", meta)
            except Exception as e:  # noqa: BLE001
                print(d, "실패", e)
            time.sleep(1)
        d -= timedelta(days=1)
    H.save(hist)
    print(f"{added}일 추가, 총 {len(hist)}일")
    return 0


def cmd_probe(args) -> int:
    day = date.fromisoformat(args.date) if args.date else today_kst()
    dump = ROOT / "probe"
    dump.mkdir(exist_ok=True)
    for code in ["1", "2", "3", "4"]:
        try:
            html = hana.fetch_html(day, code)
            (dump / f"pbld_{code}.html").write_text(html, encoding="utf-8")
            print(f"pbldDvCd={code}: meta={hana.parse_meta(html)} 통화={sorted(hana.parse_rates(html))}")
            r = hana.parse_rates(html)
            if "USD" in r:
                print("  USD", r["USD"])
        except Exception as e:  # noqa: BLE001
            print(f"pbldDvCd={code}: 실패 {e}")
    return 0


def cmd_whoami(args) -> int:
    from . import instagram
    tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    for host in ["graph.facebook.com", "graph.instagram.com"]:
        instagram.HOST = host
        try:
            print(host, "OK", instagram.whoami(tok, uid))
        except Exception as e:  # noqa: BLE001
            print(host, "실패", e)
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--date")
    b.add_argument("--retries", type=int, default=6)
    b.add_argument("--wait", type=int, default=300)
    b.add_argument("--no-video", action="store_true")
    pb = sub.add_parser("publish")
    pb.add_argument("--date")
    bf = sub.add_parser("backfill")
    bf.add_argument("--days", type=int, default=50)
    pr = sub.add_parser("probe")
    pr.add_argument("--date")
    sub.add_parser("whoami")
    args = p.parse_args()
    return {"build": cmd_build, "publish": cmd_publish, "backfill": cmd_backfill,
            "probe": cmd_probe, "whoami": cmd_whoami}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
