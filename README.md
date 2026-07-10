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

- **Datenquelle:** [Tankerkönig](https://creativecommons.tankerkoenig.de) (offizielle MTS-K-Preise, kostenlos).
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

### 2. Chat-ID ermitteln
1. In Telegram den Bot öffnen (`t.me/Spritradar_bot`) und **`/start`** senden.
2. `Actions → Get Telegram Chat ID → Run workflow` starten.
3. Die angezeigte Chat-ID als Secret **`TELEGRAM_CHAT_ID`** eintragen.

### 3. Aktivieren
Der `schedule`-Trigger läuft nur auf dem **Default-Branch**. Diesen Branch nach
`main` mergen, damit die 7:30-Nachricht automatisch kommt.
Sofort testen: `Actions → Spritradar Daily → Run workflow` (sendet direkt).

## Standorte anpassen
In `config.json`. `lat`/`lng` sind die Kartenkoordinaten, `radius_km` der Suchradius.
Die aktuellen Werte decken **47798 Krefeld** und **47506 Neukirchen-Vluyn** ab.

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
- „Warten oder kaufen?“-Ausblick über mehrere Tage.
- Nachrichten-/Ereignis-Sentiment (OPEC+, Raffinerie-Ausfälle) – niedrige Priorität.
- Backtesting gegen die Baseline „mittwochs abends tanken“.
