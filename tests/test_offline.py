"""Offline-Tests für die reine Logik (kein Netzwerk)."""

import datetime as dt
from zoneinfo import ZoneInfo

from spritradar.scoring import score_today
from spritradar.message import build_message


def test_score_cheapest_day_is_ten():
    hist = [1.75, 1.74, 1.76, 1.73, 1.77]
    sc = score_today(1.70, hist, min_history=4)
    assert sc.value == 10
    assert sc.pct_cheaper == 1.0


def test_score_most_expensive_is_low():
    hist = [1.60, 1.62, 1.61, 1.63, 1.64]
    sc = score_today(1.70, hist, min_history=4)
    assert sc.value == 1


def test_score_middle():
    hist = [1.60, 1.65, 1.70, 1.75, 1.80]
    sc = score_today(1.70, hist, min_history=4)
    # 3 von 5 Tagen >= 1.70 -> pct 0.6 -> 1 + 9*0.6 = 6.4 -> 6
    assert sc.value == 6


def test_insufficient_history_returns_none():
    sc = score_today(1.70, [1.72, 1.71], min_history=4)
    assert sc.value is None
    assert sc.avg is not None  # Kontext trotzdem vorhanden


def test_no_history():
    sc = score_today(1.70, [], min_history=4)
    assert sc.value is None
    assert sc.avg is None


def test_message_builds():
    now = dt.datetime(2026, 7, 10, 7, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    good = score_today(1.699, [1.75, 1.74, 1.76, 1.73, 1.72], min_history=4)
    thin = score_today(1.80, [1.79], min_history=4)
    msg = build_message(
        now,
        [
            ("Zuhause – Krefeld", "🏠", good, "Aral (Krefeld)"),
            ("Arbeit – Neukirchen-Vluyn", "🏢", thin, "JET (Neukirchen-Vluyn)"),
        ],
    )
    assert "Spritradar" in msg
    assert "10.07.2026" in msg
    assert "1,699 €" in msg
    assert "/10" in msg
    print("\n" + msg)


if __name__ == "__main__":
    import sys
    import traceback

    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    sys.exit(1 if failed else 0)
