"""하나은행 고시환율 수집.

조회 페이지가 내부적으로 호출하는 주소에 POST로 요청해서 표를 받아온다.
페이지 구조가 바뀌어도 최대한 버티도록 열 위치 대신 숫자 관계로 값을 찾는다:
  - 매매기준율 = 현찰 살 때와 현찰 팔 때의 중간값 (스프레드가 대칭)
"""
from __future__ import annotations

import os
import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from .config import CODES

URL = "https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; hwanjeon-board-bot/1.0)",
    "Referer": "https://www.kebhana.com/cms/rate/index.do?contentUrl=/cms/rate/wpfxd651_01i.do",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# 최초 고시를 뜻하는 고시구분 값. 실제 값은 check 워크플로로 확인해서 바꿀 수 있게 환경변수로 뺐다.
FIRST_NOTICE_CODE = os.environ.get("HANA_PBLD_DV_CD", "1")


class FetchError(RuntimeError):
    pass


def _num(text: str) -> float | None:
    t = text.replace(",", "").strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    return float(t)


def fetch_html(day: date, pbld_dv_cd: str | None = None, timeout: int = 20) -> str:
    data = {
        "ajax": "true",
        "curCd": "",
        "tmpInqStrDt": day.strftime("%Y-%m-%d"),
        "pbldDvCd": pbld_dv_cd or FIRST_NOTICE_CODE,
        "pbldSqn": "",
        "hid_key_data": "",
        "inqStrDt": day.strftime("%Y%m%d"),
        "inqKindCd": "1",
        "hid_enc_data": "",
        "requestTarget": "searchContentDiv",
    }
    r = requests.post(URL, data=data, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_meta(html: str) -> dict:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    meta = {}
    m = re.search(r"(\d{4})\s*[.\-년]\s*(\d{1,2})\s*[.\-월]\s*(\d{1,2})", text)
    if m:
        meta["date"] = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d+)\s*회차", text)
    if m:
        meta["round"] = int(m.group(1))
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text) or re.search(r"(\d{1,2})\s*시\s*(\d{1,2})\s*분", text)
    if m:
        meta["time"] = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return meta


def parse_rates(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    rates = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 4:
            continue
        head = cells[0].get_text(" ", strip=True)
        m = re.search(r"\b([A-Z]{3})\b", head)
        if not m or m.group(1) not in CODES:
            continue
        code = m.group(1)
        nums = [_num(c.get_text(" ", strip=True)) for c in cells[1:]]
        vals = [n for n in nums if n is not None and n > 0]
        if len(vals) < 3:
            continue
        cash_buy, cash_sell = vals[0], None
        # 현찰 살 때 다음에 스프레드(작은 값)가 오고 그다음이 현찰 팔 때
        for v in vals[1:]:
            if v < cash_buy and v > cash_buy * 0.5:
                cash_sell = v
                break
        if cash_sell is None:
            continue
        # 매매기준율 = 송금 보낼 때/받을 때의 중간값 (동남아 통화는 현찰 스프레드가 비대칭이라 송금 쪽이 정확)
        base = None
        for i in range(len(vals) - 1):
            a, b = vals[i], vals[i + 1]
            if not (a > b > cash_sell * 0.9):
                continue
            mid = (a + b) / 2
            hits = [v for v in vals[i + 2:] if abs(v - mid) / mid < 0.002]
            if hits:
                base = hits[0]
                break
        if base is None:
            mid = (cash_buy + cash_sell) / 2
            base = min(vals, key=lambda v: abs(v - mid))
            if abs(base - mid) / mid > 0.003:
                base = round(mid, 2)
        if not (cash_sell < base < cash_buy):
            continue
        rates[code] = {"base": base, "cash_buy": cash_buy, "cash_sell": cash_sell}
    return rates


def fetch(day: date, pbld_dv_cd: str | None = None) -> tuple[dict, dict, str]:
    html = fetch_html(day, pbld_dv_cd)
    rates = parse_rates(html)
    meta = parse_meta(html)
    if not rates:
        raise FetchError("환율 표를 찾지 못했어 (페이지 구조 변경 또는 고시 전)")
    return rates, meta, html
