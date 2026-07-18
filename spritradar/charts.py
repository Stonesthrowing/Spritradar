"""Drei Tagesverlauf-Charts (gestern / heute / morgen) als ein PNG rendern."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from . import intraday as itd  # noqa: E402
from .config import Config  # noqa: E402

# Validierte Kategorienfarben (hell), in fixer Reihenfolge.
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100"]
INK, SEC, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"


def _history_price(history: dict, plz: str, date: str) -> float | None:
    for e in history.get("locations", {}).get(plz, []):
        if e.get("date") == date:
            return float(e["min_price"])
    return None


def build_days(cfg: Config, store: dict, history: dict, now_local: dt.datetime):
    """Liste (label, mode, [(name, color, DaySeries)]) für die drei Tage."""
    today = now_local.date()
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    tomorrow = (today + dt.timedelta(days=1)).isoformat()
    today_s = today.isoformat()
    now_hour = now_local.hour + now_local.minute / 60.0

    days = [("Gestern", "past", yesterday), ("Heute", "today", today_s),
            ("Morgen", "future", tomorrow)]

    result = []
    for label, mode, date in days:
        entries = []
        for i, loc in enumerate(cfg.locations):
            color = CATEGORICAL[i % len(CATEGORICAL)]
            real = itd.day_points(store, loc.plz, date)
            # Ankerpreis: gestern/heute aus dem Tag selbst, morgen aus heute.
            anchor = _history_price(history, loc.plz, date if mode != "future" else today_s)
            if anchor is None and mode == "future":
                anchor = _history_price(history, loc.plz, today_s)
            series = itd.build_day(mode, real, anchor, now_hour)
            entries.append((loc.name, color, series))
        result.append((label, mode, entries))
    return result, now_hour


def render(days, now_hour: float, out_path: Path | str) -> str:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), sharey=True)
    fig.patch.set_facecolor(SURFACE)

    names_seen: list[tuple[str, str]] = []
    for ax, (label, mode, entries) in zip(axes, days):
        ax.set_facecolor(SURFACE)
        for name, color, series in entries:
            if (name, color) not in names_seen:
                names_seen.append((name, color))
            if series.real:
                xs = [h for h, _ in series.real]
                ys = [p for _, p in series.real]
                ax.plot(xs, ys, color=color, lw=2.2, marker="o", markersize=3)
            if series.model:
                xs = [h for h, _ in series.model]
                ys = [p for _, p in series.model]
                ax.plot(xs, ys, color=color, lw=2.0, ls=(0, (4, 3)), alpha=0.9)

        if mode == "today":
            ax.axvline(now_hour, color=MUTED, lw=1.0, ls=":")
            ax.text(now_hour + 0.2, ax.get_ylim()[0], "jetzt", color=MUTED,
                    fontsize=8, va="bottom")

        ax.set_title(label, color=INK, fontsize=12, fontweight="bold", pad=8)
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 6))
        ax.set_xticklabels([f"{h:02d}" for h in range(0, 25, 6)], color=MUTED, fontsize=9)
        ax.set_xlabel("Uhrzeit", color=SEC, fontsize=9)
        ax.grid(True, color=GRID, lw=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.2f}".replace(".", ","))

    axes[0].set_ylabel("Super E10 (€/L)", color=SEC, fontsize=9)

    handles = [Line2D([0], [0], color=c, lw=2.4, label=n) for n, c in names_seen]
    handles.append(Line2D([0], [0], color=MUTED, lw=2.0, ls=(0, (4, 3)),
                          label="Prognose (extrapoliert)"))
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, 1.02), labelcolor=INK)
    fig.suptitle("Spritradar – Tagesverlauf Super E10", color=INK, fontsize=13,
                 fontweight="bold", y=1.11)
    fig.tight_layout(rect=(0, 0, 1, 0.99))

    out = str(out_path)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return out
