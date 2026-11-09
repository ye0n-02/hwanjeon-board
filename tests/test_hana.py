from pathlib import Path

from bot import hana

HTML = (Path(__file__).parent / "fixtures" / "hana_sample.html").read_text(encoding="utf-8")


def test_parse():
    r = hana.parse_rates(HTML)
    assert r["USD"]["base"] == 1490.20
    assert r["JPY"]["base"] == 935.91
    assert r["VND"]["base"] == 5.67
    assert hana.parse_meta(HTML) == {"date": "2026-11-09", "round": 1, "time": "09:03"}
