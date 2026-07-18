# Spritradar

Täglich um **7:30 Uhr** eine Telegram-Nachricht mit einer Bewertung von **1–10**,
wie gut der heutige Tag zum Tanken von **Super E10** ist – für zwei Standorte
(Zuhause & Arbeit).

Der Score misst das heutige Preisniveau **relativ zum jüngsten Verlauf**:
10 = so günstig wie lange nicht (kaufen), 1 = deutlich über dem jüngsten Niveau
(lieber warten).

## Wie es funktioniert

```
GitHub Actions (cron 7:30)
        │
        ├─ Tankerkönig-API   → aktuelle E10-Preise im Umkreis je Standort
        ├─ data/history.json → selbst gesammelte Preishistorie (letzte Tage)
        ├─ Scoring           → Preis von heute vs. Verlauf → Score 1–10
        └─ Telegram-Bot      → Nachricht an dich
```

- **Datenquelle Preise:** [Tankerkönig](https://creativecommons.tankerkoenig.de) (offizielle MTS-K-Preise, kostenlos).
- **Nachrichtenlage:** aktuelle Schlagzeilen zu Benzin/Öl/OPEC über Google-News-RSS
  (kostenlos, kein Key). Die Bewertung „heute vollmachen vs. warten" macht optional
  Claude Haiku (geringe Kosten, `ANTHROPIC_API_KEY`); ohne Key greift eine kostenlose
  Stichwort-Heuristik.
- **Historie:** Die freie API liefert nur aktuelle Preise. Deshalb speichert der
  Workflow jeden Morgen den günstigsten Preis in `data/history.json` und committet
  sie zurück. Der Score wird mit jedem Tag aussagekräftiger (ab ~4 Tagen Historie).
- **Zeitplan:** Zwei cron-Trigger (Sommer-/Winterzeit); das Skript prüft die echte
  Berliner Uhrzeit und sendet pro Tag nur einmal.

## Einrichtung

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

### 3. Aktivieren
`schedule`-Trigger laufen nur auf dem **Default-Branch**. Diesen Branch nach `main`
mergen, damit alle geplanten Workflows aktiv werden:
- **Spritradar Daily** – die 7:30-Nachricht
- **Spritradar Collect** – stündliches Preis-Sammeln (für die Charts)
- **Spritradar Bot** – Poller für den `Graphs`-Befehl

Sofort testen: `Actions → Spritradar Daily → Run workflow` (sendet direkt).

## Charts: „Graphs" im Telegram-Chat
Schreib dem Bot **`Graphs`** – er antwortet mit drei Charts (gestern / heute / morgen),
je Standort der Super-E10-Tagesverlauf über die Uhrzeit.

- **Durchgezogen = gemessen**, **gestrichelt = Prognose** (typisches Tagesprofil ans
  aktuelle Preisniveau angelegt). „Heute" ist bis zur aktuellen Uhrzeit gemessen,
  danach extrapoliert; „gestern" ist gemessen (sobald Daten vorliegen), „morgen"
  komplett Prognose.
- **Datenbasis:** ein **stündlicher** Sammel-Job (`Spritradar Collect`) schreibt echte
  Preise in `data/intraday.json`. In den ersten ein bis zwei Tagen sind die Kurven
  noch modelliert; danach werden gestern/heute real.
- **Antwortzeit:** GitHub kann nicht dauerhaft lauschen. Der Poller (`Spritradar Bot`)
  fragt alle **10 Minuten** ab → bis zu ~10 Min Verzögerung. Intervall in
  `.github/workflows/bot.yml` anpassbar.

> ⚠️ **Actions-Minuten:** Sammeln (stündlich) + Poller (alle 10 Min) verbrauchen bei
> **privaten** Repos Actions-Minuten (ggf. über dem Gratis-Kontingent). Bei einem
> **öffentlichen** Repo ist GitHub Actions kostenlos/unbegrenzt. Alternativ Intervalle
> verlängern.

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
