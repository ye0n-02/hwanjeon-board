"""데이터 → 카드 HTML → JPEG 7장 + 1장 MP4 + 캡션."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from . import history as H
from .config import ACCOUNT, BY_CODE, CHART_CODES, CURRENCIES, LOCAL_PRICES

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
TIPS = json.loads((ROOT / "content" / "tips.json").read_text(encoding="utf-8"))
WEEKDAY = "월화수목금토일"
FLAG = {"JPY": "🇯🇵", "USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳", "TWD": "🇹🇼", "THB": "🇹🇭", "VND": "🇻🇳", "PHP": "🇵🇭"}
SLIDES = ["s1_board", "s2_pick", "s3_fees", "s4_trend", "s5_local", "s6_tip", "s7_cta"]
TITLES = {
    "s1_board": ("Exchange Rates", "오늘의 환전"),
    "s2_pick": ("TODAY'S PICK", "오늘의 픽"),
    "s3_fees": ("HOW MUCH YOU PAY", "우대율별 내는 돈"),
    "s4_trend": ("30-DAY TREND", "최근 30일 흐름"),
    "s5_local": ("LOCAL PRICES", "현지 물가 환산"),
    "s6_tip": ("TRAVEL TIP", "오늘의 팁"),
    "s7_cta": ("SEE YOU TOMORROW", "내일 또 만나"),
}


def won(v: float, nd: int = 2) -> str:
    return f"{v:,.{nd}f}"


def short(d: str) -> str:
    return f"{d[5:7]}.{d[8:10]}"


def cls_of(verdict: str) -> str:
    return {"싼 편": "cheap", "비싼 편": "pricey"}.get(verdict, "normal")


def pos_text(pct: int) -> str:
    return f"하위 {pct}%" if pct <= 50 else f"상위 {100 - pct}%"


def chart_svg(series: list[tuple[str, float]], avg: float, color: str, w: int = 900, h: int = 190) -> str:
    vals = [v for _, v in series]
    lo, hi = min(vals + [avg]), max(vals + [avg])
    pad = (hi - lo) * 0.15 or hi * 0.002
    lo, hi = lo - pad, hi + pad
    n = max(len(vals) - 1, 1)
    y = lambda v: h - (v - lo) / (hi - lo) * h
    pts = " ".join(f"{i * w / n:.1f},{y(v):.1f}" for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h + 10}" viewBox="0 -5 {w} {h + 10}" aria-hidden="true">'
            f'<line x1="0" y1="{y(avg):.1f}" x2="{w}" y2="{y(avg):.1f}" stroke="#BFD3FF" stroke-width="2" stroke-dasharray="8 8"/>'
            f'<polyline points="{pts}" fill="none" stroke="#FFD400" stroke-width="4"/>'
            f'<circle cx="{(len(vals) - 1) * w / n - (8 if len(vals) > 1 else 0):.1f}" cy="{y(vals[-1]):.1f}" r="10" fill="{color}"/></svg>')


def build_context(hist: dict, day: str) -> dict:
    today = hist[day]
    rows = []
    for c in CURRENCIES:
        code = c["code"]
        if code not in today["rates"]:
            continue
        r = today["rates"][code]
        s = H.stats(hist, code, day)
        diff = s["diff"]
        if diff is None or abs(diff) < 0.005:
            delta_s, delta_cls = "－ 0.00", "normal"
        elif diff < 0:
            delta_s, delta_cls = f"▼ {won(-diff)}", "cheap"
        else:
            delta_s, delta_cls = f"▲ {won(diff)}", "pricey"
        per = lambda v: v / c["unit"] * c["travel_qty"]
        best, none = per(r["base"]), per(r["cash_buy"])
        rows.append({
            **c,
            "today_s": won(s["today"]),
            "prev_s": won(s["prev"]) if s["prev"] is not None else won(s["today"]),
            "delta_s": delta_s, "delta_cls": delta_cls,
            "delta_long_s": ("변동 없음" if delta_cls == "normal" else f"{delta_s[0]} {delta_s[2:]}원"),
            "verdict": s["verdict"], "verdict_cls": cls_of(s["verdict"]),
            "pct": s["pct"], "pos_s": pos_text(s["pct"]), "n": s["n"],
            "avg_s": won(s["avg"]), "avg_diff_pct": s["avg_diff_pct"],
            "spread_pct_s": f"{(r['cash_buy'] / r['base'] - 1) * 100:.2f}",
            "fee_best_s": won(best, 0), "fee_80_s": won(best + 0.2 * (none - best), 0), "fee_none_s": won(none, 0),
            "travel_best_s": won(best, 0),
            "stats": s,
        })
    pick = min(rows, key=lambda x: (x["pct"], x["avg_diff_pct"]))
    by = {r["code"]: r for r in rows}
    color = {"cheap": "#3BE07E", "pricey": "#FF5B4F", "normal": "#FFFFFF"}
    charts = []
    for code in CHART_CODES:
        if code not in by:
            continue
        r = by[code]
        s = r["stats"]
        charts.append({**r, "svg": chart_svg(s["series"], s["avg"], color[r["verdict_cls"]]),
                       "first_s": f"{s['n']}영업일 전" if s["n"] > 1 else "오늘"})
    local = []
    for l in LOCAL_PRICES:
        if l["code"] in today["rates"]:
            c = BY_CODE[l["code"]]
            local.append({**l, "krw_s": won(l["qty"] * today["rates"][l["code"]]["base"] / c["unit"], 0)})
    dates = sorted(d for d in hist if d < day)
    dt = date.fromisoformat(day)
    nxt = dt + timedelta(days=3 if dt.weekday() == 4 else 1)
    return {
        "day": day,
        "date_short": short(day),
        "prev_date_short": short(dates[-1]) if dates else short(day),
        "date_long": f"{dt.month}월 {dt.day}일({WEEKDAY[dt.weekday()]})",
        "time": today.get("meta", {}).get("time", "09:00"),
        "rows": rows,
        "pick": pick,
        "pick_headline": "오늘 환전하기 좋은 통화" if pick["verdict"] == "싼 편" else "오늘 상대적으로 덜 비싼 통화",
        "charts": charts,
        "local": local,
        "tip": TIPS[dt.toordinal() % len(TIPS)],
        "next_label": "월요일 아침" if dt.weekday() == 4 else "내일 아침",
        "account": ACCOUNT,
    }


def render_html(d: dict, out: Path) -> list[Path]:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    paths = []
    for i, name in enumerate(SLIDES, 1):
        en, ko = TITLES[name]
        html = env.get_template(f"{name}.html.j2").render(d=d, idx=i, total=len(SLIDES), en_title=en, ko_title=ko)
        p = out / f"{i:02d}.html"
        p.write_text(html, encoding="utf-8")
        paths.append(p)
    return paths


def caption(d: dict) -> str:
    lines = [f"✈️ 오늘의 환전 | {d['date_long']} {d['time']} 하나은행 첫 고시 기준", ""]
    for r in d["rows"]:
        lines.append(f"{FLAG[r['code']]} {r['short']} {r['today_s']}원 ({r['unit_label']}) {r['delta_s'].replace(' ', '')} · {r['verdict']}")
    p = d["pick"]
    lines += ["", f"💡 오늘의 픽: {p['short']} · 최근 {p['n']}영업일 중 {p['pos_s']}", "",
              "📌 매매기준율 기준이며 환율 예측이 아니에요. 실제 환전 금액은 은행·우대율에 따라 달라요.", "",
              "#환율 #오늘환율 #환전 #엔화환율 #달러환율 #유로환율 #여행준비 #해외여행 #환전꿀팁 #트래블카드"]
    return "\n".join(lines)


def shoot(html_paths: list[Path], out: Path, video: bool = True) -> list[Path]:
    from playwright.sync_api import sync_playwright

    files = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for i, hp in enumerate(html_paths, 1):
            page.goto(hp.as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            if i == 1:
                page.evaluate("document.getAnimations().forEach(a => { a.pause(); a.currentTime = 6000; })")
            jpg = out / f"{i:02d}.jpg"
            page.screenshot(path=str(jpg), type="jpeg", quality=92, full_page=False)
            files.append(jpg)
            if i == 1 and video:
                files.append(record_board(page, out))
        browser.close()
    return files


def record_board(page, out: Path, seconds: float = 7.0, fps: int = 30) -> Path:
    tmp = Path(tempfile.mkdtemp())
    for f in range(int(seconds * fps)):
        t = f * 1000 / fps
        page.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {t}; }})")
        page.screenshot(path=str(tmp / f"f{f:04d}.png"))
    mp4 = out / "01.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f%04d.png"),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(mp4)], check=True)
    shutil.rmtree(tmp)
    return mp4


def build(hist: dict, day: str, out: Path, video: bool = True) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    d = build_context(hist, day)
    html_paths = render_html(d, out)
    files = shoot(html_paths, out, video=video)
    cap = caption(d)
    (out / "caption.txt").write_text(cap, encoding="utf-8")
    for p in html_paths:
        p.unlink()
    summary = {"day": day, "files": [f.name for f in files], "pick": d["pick"]["code"],
               "rows": [{k: r[k] for k in ("code", "today_s", "delta_s", "verdict", "pct")} for r in d["rows"]]}
    (out / "data.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"context": d, "caption": cap, "files": files}
