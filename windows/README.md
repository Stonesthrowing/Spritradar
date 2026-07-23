# Spritradar auf dem Mini-PC (Windows)

GitHubs Zeitplan war unzuverlässig (Nachricht kam oft erst 9–10 Uhr). Deshalb läuft
Spritradar jetzt **lokal auf dem Mini-PC** über den **Windows Task Scheduler** –
pünktlich, unabhängig von GitHub, ohne Token. Der `Graphs`-Bot antwortet dadurch
außerdem fast sofort.

Alles bleibt lokal (Daten in `data\*.json`). GitHub dient nur noch als Code-Ablage.

## Einmalige Einrichtung

### 1. Python installieren
[python.org/downloads](https://www.python.org/downloads/) → Python 3.12 →
beim Installer **„Add python.exe to PATH" ankreuzen**. Prüfen:
```
py --version
```

### 2. Repo holen
Mit Git ([git-scm.com](https://git-scm.com/download/win)) – erlaubt später einfache Updates:
```
cd C:\
git clone https://github.com/Stonesthrowing/Spritradar.git
```
→ Ordner `C:\Spritradar`. (Alternativ „Code → Download ZIP" auf GitHub und nach `C:\Spritradar` entpacken.)

### 3. Abhängigkeiten installieren
```
cd C:\Spritradar
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

### 4. Secrets eintragen
`windows\secrets.example.bat` kopieren zu **`windows\secrets.bat`** und die Werte
eintragen (dieselben wie in den GitHub-Secrets). `secrets.bat` bleibt lokal (gitignore).

### 5. Testen (Doppelklick)
- `windows\run-daily.bat` → es sollte eine **Telegram-Nachricht** kommen.
- `windows\run-collect.bat` → schreibt einen Messpunkt in `data\intraday.json`.
- Dem Bot in Telegram `Graphs` schicken, dann `windows\run-bot.bat` → **Charts** kommen.

## Task Scheduler (Aufgabenplanung) einrichten

`Win`-Taste → „Aufgabenplanung" öffnen → rechts **„Aufgabe erstellen…"** (nicht „einfache Aufgabe").

### Task „Spritradar Daily" (die 7:30-Nachricht)
- **Trigger:** Täglich, Start **07:30**.
- **Aktion:** Programm/Skript = `C:\Spritradar\windows\run-daily.bat`
- **Bedingungen:** „Computer für die Ausführung reaktivieren" ankreuzen (falls der PC schläft).
- **Einstellungen:** „Aufgabe so schnell wie möglich nach verpasstem Start ausführen" ankreuzen.

### Task „Spritradar Collect" (stündlich sammeln)
- **Trigger:** Täglich 00:00 → „Wiederholen alle: **1 Stunde**", „für die Dauer von: **Unbegrenzt**".
- **Aktion:** `C:\Spritradar\windows\run-collect.bat`

### Task „Spritradar Bot" (schnelle Graphs-Antwort)
- **Trigger:** Täglich 00:00 → „Wiederholen alle: **2 Minuten**", „für die Dauer von: **Unbegrenzt**".
- **Aktion:** `C:\Spritradar\windows\run-bot.bat`

**Tipp:** In jedem Task unter „Allgemein" die Option **„Unabhängig von der Benutzeranmeldung
ausführen"** wählen, dann laufen die Skripte im Hintergrund ohne aufblitzendes Fenster
(Windows fragt einmal dein Kontopasswort ab). Alternativ „Nur ausführen, wenn Benutzer
angemeldet ist", wenn der Mini-PC ohnehin dauerhaft angemeldet bleibt.

**Energie/Standby:** Damit der Daily-Task den PC aus dem Ruhezustand weckt:
Systemsteuerung → Energieoptionen → Energiesparplan-Einstellungen → Erweitert →
„Ruhezustand" → „Wecktimer zulassen" = **Aktiviert**.

## Updates einspielen
Wenn hier im Repo etwas geändert wird:
```
cd C:\Spritradar
git pull
.venv\Scripts\pip install -r requirements.txt
```

## Uhrzeit anpassen
Die 7:30 stehen im Task-Trigger (nicht mehr in der Config). Trigger-Zeit im Task
Scheduler ändern – fertig.
