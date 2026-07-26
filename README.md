# Spritradar

Täglich früh eine Telegram-Nachricht mit klarer Handlungsempfehlung – **WARTEN**
oder **JETZT TANKEN** – für **Super E10** an zwei Standorten (Zuhause & Arbeit),
inkl. bestem Zeitfenster heute und transparentem 0–100-Score je Fenster.

**12-Uhr-Regime (KPAnG, seit 01.04.2026):** Tankstellen dürfen Preise nur noch
**1× täglich um 12:00 erhöhen**, Senkungen jederzeit. Daraus folgt hart: vor 12 Uhr
kann der Preis nicht steigen (Warten bis kurz vor 12 ist risikolos), um 12:00 ein
einmaliger Sprung (ADAC-Mittel ~14,6 ct/l bei E10), danach nur noch Rückgang bis
zum Abendtief. Das Modell ist genau darauf ausgerichtet.

## Wie es funktioniert

```
Mini-PC (Task Scheduler, morgens)
        │
        ├─ Tankerkönig-API   → aktuelle E10-Preise je Standort + Umkreis (Markt-Median)
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
- **Historie:** Die freie API liefert nur aktuelle Preise. Deshalb speichert der
  Workflow jeden Morgen den günstigsten Preis in `data/history.json` und committet
  sie zurück. Der Score wird mit jedem Tag aussagekräftiger (ab ~4 Tagen Historie).
- **Zeitplan:** läuft **lokal auf einem Mini-PC** (Windows Task Scheduler), weil
  GitHubs geplante Läufe auf dem Gratis-Tarif regelmäßig ~2 h zu spät kamen. Der
  Task Scheduler ist pünktlich → Nachricht ~07:30. Einrichtung: siehe
  [`windows/README.md`](windows/README.md). Die GitHub-Workflows bleiben als
  **manueller Auslöser** (`Run workflow`) erhalten.

## Einrichtung (Mini-PC)

Die vollständige Schritt-für-Schritt-Anleitung steht in **[`windows/README.md`](windows/README.md)**
(Python installieren, Repo klonen, `secrets.bat` ausfüllen, drei Task-Scheduler-Aufgaben:
Daily 07:30, Collect stündlich, Bot alle 2 Min).

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
`Actions → Spritradar Daily → Run workflow` sendet sofort eine Nachricht.

## Charts: „Graphs" im Telegram-Chat
Schreib dem Bot **`Graphs`** – er antwortet mit drei Charts (gestern / heute / morgen),
je Standort der Super-E10-Tagesverlauf über die Uhrzeit.

- **Durchgezogen = gemessen**, **gestrichelt = Prognose** (typisches Tagesprofil ans
  aktuelle Preisniveau angelegt). „Heute" ist bis zur aktuellen Uhrzeit gemessen,
  danach extrapoliert; „gestern" ist gemessen (sobald Daten vorliegen), „morgen"
  komplett Prognose.
- **Datenbasis:** der **stündliche** Sammel-Job (`spritradar.collect`, Task auf dem
  Mini-PC) schreibt echte Preise in `data/intraday.json`. In den ersten ein bis zwei
  Tagen sind die Kurven noch modelliert; danach werden gestern/heute real.
- **Antwortzeit:** Der `Graphs`-Poller (`spritradar.bot`) läuft lokal alle **2 Minuten**
  → Antwort fast sofort. Intervall im Task Scheduler anpassbar.

## Standorte & Einstellungen anpassen
Alles in `config.json`:
- **Standorte:** `lat`/`lng` (Kartenkoordinaten), `radius_km` (Suchradius). Aktuell
  abgedeckt: **47798 Krefeld** und **47506 Neukirchen-Vluyn**.
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
