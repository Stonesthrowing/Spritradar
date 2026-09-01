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
"go" im Telegram-Chat → Poller auf dem Mini-PC (alle 2 Min)
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
- **Zeitplan:** keiner. Es gibt keine geplanten Läufe mehr – weder hier noch bei
  GitHub. Alle Workflows in `.github/workflows/` sind nur noch manuell
  auslösbar (`Run workflow`) und dienen als Notnagel.
- **Was laufen muss:** ein Poller, der `go` überhaupt hört. Der läuft auf dem
  Mini-PC (Windows Task Scheduler, alle 2 Minuten) – Antwort in Sekunden.
  Einrichtung mit einem Doppelklick: **[`windows/README.md`](windows/README.md)**.

## Einrichtung

Auf dem Mini-PC: Repo klonen, `windows\secrets.bat` ausfüllen, dann
`windows\install-tasks.bat` doppelklicken – das legt die beiden Aufgaben an
(Bot alle 2 Min, Collect stündlich). Details:
**[`windows/README.md`](windows/README.md)**.

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

### 3. Manuell auslösen
Alle Workflows haben nur noch `workflow_dispatch` (kein Zeitplan mehr):
`Actions → Spritradar Tankplan (manuell) → Run workflow` sendet sofort eine
Nachricht – der Notnagel, falls der Mini-PC aus ist.

## Charts: „graphs" im Telegram-Chat
Schreib dem Bot **`graphs`** – er antwortet mit drei Charts (gestern / heute / morgen),
dem Super-E10-Tagesverlauf über die Uhrzeit.

- **Durchgezogen = gemessen**, **gestrichelt = Prognose** (typisches Tagesprofil ans
  aktuelle Preisniveau angelegt). „Heute" ist bis zur aktuellen Uhrzeit gemessen,
  danach extrapoliert; „gestern" ist gemessen (sobald Daten vorliegen), „morgen"
  komplett Prognose.
- **Datenbasis:** der **stündliche** Sammel-Job (`spritradar.collect`, Task auf dem
  Mini-PC) schreibt echte Preise in `data/intraday.json`. In den ersten ein bis zwei
  Tagen sind die Kurven noch modelliert; danach werden gestern/heute real.
- **Antwortzeit:** Der Poller (`spritradar.bot`) läuft lokal alle **2 Minuten**
  → Antwort fast sofort. Intervall im Task Scheduler anpassbar.

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
