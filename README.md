# Spritradar

Auf Zuruf eine Telegram-Nachricht mit klarer Handlungsempfehlung – **WARTEN**
oder **JETZT TANKEN** – für **Super E10** in Krefeld, inkl. bestem Zeitfenster
heute und transparentem 0–100-Score je Fenster.

**Kein Zeitplan:** Du schreibst dem Bot `go`, er antwortet. `graphs` liefert
zusätzlich die drei Tagesverlauf-Charts.

**12-Uhr-Regime (KPAnG, seit 01.04.2026):** Tankstellen dürfen Preise nur noch
**1× täglich um 12:00 erhöhen**, Senkungen jederzeit. Daraus folgt hart: vor 12 Uhr
kann der Preis nicht steigen (Warten bis kurz vor 12 ist risikolos), um 12:00 ein
einmaliger Sprung (ADAC-Mittel ~14,6 ct/l bei E10), danach nur noch Rückgang bis
zum Abendtief. Das Modell ist genau darauf ausgerichtet.

## Wie es funktioniert

```
"go" im Telegram-Chat → Lauscher auf GitHub Actions (Long-Polling)
        │
        ├─ Tankerkönig-API   → aktuelle E10-Preise + Umkreis (Markt-Median)
        ├─ data/intraday.json→ selbst gesammelter Tagesverlauf (12-Uhr-Sprung, Abendtief)
        ├─ Regime-Modell     → bestes Fenster heute + Score + WARTEN/TANKEN (transparent)
        └─ Telegram-Bot      → Tankplan-Nachricht an dich
```

Das Modell ist **kein Blackbox-Orakel**, sondern additiv und nachvollziehbar:
lokaler Markt-Median (ist der Favorit wirklich günstig?), aus der Historie
geschätzter 12-Uhr-Sprung, erreichbares Tagestief, daraus Empfehlung + Score.
Je mehr eigene Daten, desto schärfer (stationsspezifisch ab ~4 Wochen).

- **Datenquelle Preise:** [Tankerkönig](https://creativecommons.tankerkoenig.de) (offizielle MTS-K-Preise, kostenlos).
- **Nachrichtenlage:** aktuelle Schlagzeilen zu Benzin/Öl/OPEC über Google-News-RSS
  (kostenlos, kein Key). Die Bewertung „heute vollmachen vs. warten" macht optional
  Claude Haiku (geringe Kosten, `ANTHROPIC_API_KEY`); ohne Key greift eine kostenlose
  Stichwort-Heuristik.
- **Historie:** Die freie API liefert nur aktuelle Preise. Deshalb speichert jeder
  `go`-Lauf den günstigsten Preis in `data/history.json`, und ein stündlicher
  stiller Sammler schreibt Momentaufnahmen nach `data/intraday.json`. Der Score
  wird mit jedem Tag aussagekräftiger (ab ~4 Tagen Historie).
- **Es sendet nichts von allein.** Der Tankplan kommt ausschließlich auf `go`.
- **Was laufen muss:** ein Lauscher, der `go` überhaupt hört. Der läuft auf
  **GitHub Actions** (`.github/workflows/bot.yml`) – keine Einrichtung nötig.

### Warum ein Lauscher und kein Poll-Zeitplan

GitHub drosselt geplante Läufe massiv. Der frühere Poller stand auf `*/10`,
also **144 geplante Läufe am Tag** – ausgeliefert wurden am 24.07.2026 real
**drei**, im Abstand von ~2 h. Ein kurzer Poll pro Lauf hieße also bis zu
zwei Stunden Wartezeit auf `go`.

Deshalb bleibt der Lauf, der durchkommt, per **Telegram-Long-Polling** offen
(`POLL_SECONDS`, Standard 5 h 30) und antwortet in Sekunden. Eine
`concurrency`-Gruppe hält immer nur einen Lauscher am Leben; der nächste
geplante Lauf wartet und übernimmt nahtlos. Die stündliche Preismessung
erledigt derselbe Lauf nebenbei – dafür braucht es keinen zweiten Zeitplan.

**Abdeckung:** 03:00–20:00 UTC (05:00–22:00 Ortszeit im Sommer). Ein `go`
mitten in der Nacht wird beantwortet, sobald morgens der erste Lauscher startet.

## Einrichtung

Nichts zu tun – nur die Secrets müssen im Repo hinterlegt sein (siehe unten).
Der Mini-PC ist **optional**: Er antwortet noch schneller und deckt auch die
Nacht ab. Anleitung: **[`windows/README.md`](windows/README.md)**.

## Manueller Betrieb über GitHub (optional / Test)

### 1. Secrets im Repo hinterlegen
`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Wert |
| --- | --- |
| `TANKERKOENIG_API_KEY` | dein Tankerkönig-API-Key |
| `TELEGRAM_BOT_TOKEN` | Bot-Token vom BotFather |
| `TELEGRAM_CHAT_ID` | *(zunächst leer lassen – siehe Schritt 2)* |
| `ANTHROPIC_API_KEY` | *(optional – aktiviert die LLM-Nachrichtenanalyse; ohne läuft die kostenlose Heuristik)* |

### 2. Chat-ID ermitteln
1. In Telegram den Bot öffnen (`t.me/Spritradar_bot`) und **`/start`** senden.
2. `Actions → Get Telegram Chat ID → Run workflow` starten.
3. Die angezeigte Chat-ID als Secret **`TELEGRAM_CHAT_ID`** eintragen.

### 3. Wenn `go` nicht beantwortet wird
Es gibt **bewusst keinen Weg mehr, eine Nachricht ohne `go` auszulösen** – auch
keinen Knopf. Antwortet der Bot nicht, läuft gerade kein Lauscher: dann
`Actions → Spritradar Bot → Run workflow` starten und danach `go` schicken.

## Charts: „graphs" im Telegram-Chat
Schreib dem Bot **`graphs`** – er antwortet mit drei Charts (gestern / heute / morgen),
dem Super-E10-Tagesverlauf über die Uhrzeit.

- **Durchgezogen = gemessen**, **gestrichelt = Prognose** (typisches Tagesprofil ans
  aktuelle Preisniveau angelegt). „Heute" ist bis zur aktuellen Uhrzeit gemessen,
  danach extrapoliert; „gestern" ist gemessen (sobald Daten vorliegen), „morgen"
  komplett Prognose.
- **Datenbasis:** die **stündliche** Preismessung (`spritradar.collect`) schreibt
  echte Preise in `data/intraday.json`; der Lauscher erledigt sie nebenbei mit.
  In den ersten ein bis zwei Tagen sind die Kurven noch modelliert; danach
  werden gestern/heute real.
- **Antwortzeit:** Sekunden, solange ein Lauscher aktiv ist (05:00–22:00
  Ortszeit). Nachts erst, wenn morgens der nächste startet.

## Standorte & Einstellungen anpassen
Alles in `config.json`:
- **Standorte:** `lat`/`lng` (Kartenkoordinaten), `radius_km` (Suchradius). Aktuell
  abgedeckt: **47798 Krefeld**. Weitere Standorte lassen sich als zusätzliche
  Einträge in `locations` ergänzen.
- **Bevorzugte Tankstelle** je Standort unter `preferred` (Marke/Straße/Ort) – wird
  zusätzlich zur günstigsten mit Aufpreis angezeigt.
- **Tägliche Fixwerte** unter `daily_tips` (`best_time`, `best_weekday`) – erscheinen
  ganz am Ende der Nachricht in Klammern.
- **Nachrichten** unter `news` (`enabled`, `model`, `query`, `max_headlines`).

## Lokal testen
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Werte eintragen
set -a && source .env && set +a
FORCE=1 python -m spritradar.main
```

## Roadmap / Ideen
- Makro-Signale ergänzen (Brent-Rohöl-Trend, EUR/USD, Rotterdam-Großhandel) für
  bessere Bewertung schon in den ersten Tagen.
- Nachrichten-Sentiment stärker in den Score einfließen lassen (aktuell separat angezeigt).
- Backtesting gegen die Baseline „mittwochs abends tanken“.
