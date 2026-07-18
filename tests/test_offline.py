"""Offline-Tests für die reine Logik (kein Netzwerk)."""

import datetime as dt
from zoneinfo import ZoneInfo

from spritradar.scoring import score_today
from spritradar.message import build_message, LocationResult, PreferredResult
from spritradar.tankerkoenig import Station, find_preferred
from spritradar.config import PreferredSpec, DailyTips
from spritradar.analysis import analyze_with_heuristic
from spritradar.news import Headline


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


def _stations():
    return [
        Station("1", "Die Zapfsäule", "", 2.129, 0.5, True, "Krefeld", "Hauptstr.", "1", "47798"),
        Station("2", "JET Tankstelle", "JET", 2.159, 1.2, True, "Krefeld", "Oranierring", "51", "47798"),
        Station("3", "Aral", "ARAL", 2.199, 0.8, True, "Krefeld", "Ostwall", "10", "47798"),
    ]


def test_find_preferred_by_brand_and_street():
    spec = PreferredSpec(label="JET Oranierring", brand="JET", street="Oranierring", house_number="51")
    match = find_preferred(_stations(), spec)
    assert match is not None
    assert match.id == "2"
    assert match.price == 2.159


def test_find_preferred_missing_returns_none():
    spec = PreferredSpec(label="PM", brand="PM", place="Neukirchen-Vluyn")
    assert find_preferred(_stations(), spec) is None


def test_heuristic_bullish_says_vorher_tanken():
    hl = [
        Headline("OPEC+ kürzt Fördermenge, Ölpreis steigt deutlich", "X", ""),
        Headline("Neue Sanktionen gegen Öllieferungen", "Y", ""),
    ]
    ins = analyze_with_heuristic(hl)
    assert ins.tendency == "steigend"
    assert ins.advice == "vorher_tanken"
    assert ins.source == "heuristik"


def test_heuristic_bearish_says_kann_warten():
    hl = [
        Headline("Ölpreis fällt: Nachfrage schwächelt weiter", "X", ""),
        Headline("Rohöl wird billiger nach Einigung", "Y", ""),
    ]
    ins = analyze_with_heuristic(hl)
    assert ins.tendency == "fallend"
    assert ins.advice == "kann_warten"


def test_message_builds():
    now = dt.datetime(2026, 7, 10, 7, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    good = score_today(2.129, [2.20, 2.18, 2.21, 2.19, 2.17], min_history=4)
    thin = score_today(2.179, [2.18], min_history=4)
    news = analyze_with_heuristic(
        [Headline("OPEC+ kürzt Förderung, Ölpreis steigt", "X", "")]
    )
    msg = build_message(
        now,
        [
            LocationResult(
                "Zuhause – Krefeld", "🏠", good, "Die Zapfsäule (Krefeld)",
                [PreferredResult("JET Oranierring", 2.159, 2.159 - 2.129)],
            ),
            LocationResult(
                "Arbeit – Neukirchen-Vluyn", "🏢", thin, "PM (Neukirchen-Vluyn)",
                [PreferredResult("PM Neukirchen-Vluyn", 2.179, 0.0, is_cheapest=True)],
            ),
        ],
        news=news,
        daily_tips=DailyTips(best_time="18–19 Uhr", best_weekday="Dienstag"),
    )
    assert "Spritradar" in msg
    assert "10.07.2026" in msg
    assert "2,129 €" in msg
    assert "/10" in msg
    assert "JET Oranierring" in msg
    assert "+3,0 ct teurer" in msg
    assert "= günstigste hier" in msg
    assert "📰" in msg
    assert msg.rstrip().endswith("Bester Wochentag: Dienstag)")
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
