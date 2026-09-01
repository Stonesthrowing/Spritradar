# Spritradar auf dem Mini-PC (Windows)

Spritradar schickt **keine Nachricht mehr von allein**. Der Tankplan kommt nur
noch auf Zuruf: Du schreibst dem Bot in Telegram **`go`**, er antwortet.

Damit „go" gehört wird, muss auf dem Mini-PC ein kleiner Poller laufen — der
fragt alle 2 Minuten bei Telegram nach. Genau das richten diese Skripte ein.
GitHub hat **keinen Zeitplan mehr**; alle Workflows dort sind nur noch manuell.

| Befehl im Chat | Antwort |
| --- | --- |
| `go` | aktueller Tankplan für Krefeld (Favorit JET Oranierring + günstigste vor Ort) |
| `graphs` | drei Tagesverlauf-Charts (gestern / heute / morgen) |

Zwei Aufgaben laufen dafür im Hintergrund:

| Aufgabe | Takt | Zweck |
| --- | --- | --- |
| `Spritradar Bot` | alle 2 Min | hört auf `go` / `graphs` |
| `Spritradar Collect` | stündlich | stille Preis-Momentaufnahme (sendet nichts) |

Das Sammeln kostet **keine Claude-Tokens** — es ruft nur Tankerkönig ab. Tokens
fallen nur bei `go` an (eine kurze News-Analyse). Ohne das Sammeln fällt die
Tagesverlauf-Prognose auf ein Standardprofil zurück und die Charts zeigen für
neue Tage nichts Gemessenes.

## Einrichtung

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

### 3. Secrets eintragen
Am sichersten in der Eingabeaufforderung (vermeidet die `.txt`-Falle):
```
cd C:\Spritradar
copy windows\secrets.example.bat windows\secrets.bat
notepad windows\secrets.bat
```
Werte eintragen, speichern. `secrets.bat` bleibt lokal (steht in `.gitignore`).

> ⚠️ **Häufigster Fehler:** Legt man die Datei per Rechtsklick/Notepad an, heißt sie
> oft in Wirklichkeit `secrets.bat.txt` (Windows blendet bekannte Endungen aus) – dann
> meldet das Skript „secrets.bat fehlt". Prüfen mit `dir windows` in der
> Eingabeaufforderung; ggf. `ren windows\secrets.bat.txt secrets.bat`.

### 4. Doppelklick auf `windows\install-tasks.bat`

Das erledigt den Rest allein: Python-Umgebung anlegen, Abhängigkeiten
installieren, beide Aufgaben registrieren (und eine alte „Spritradar Daily"
entfernen, die es nicht mehr braucht). Das Fenster bleibt offen und sagt bei
jedem Schritt, ob er geklappt hat.

Danach in Telegram **`go`** schicken — die Antwort kommt innerhalb von ~2 Minuten.

> Meldet das Skript, die Aufgabe lasse sich nicht anlegen: per Rechtsklick →
> **„Als Administrator ausführen"** starten.

Die Aufgaben laufen, **solange der Benutzer angemeldet ist**. Wenn der Mini-PC
dauerhaft angemeldet durchläuft, passt das. Sonst in der Aufgabenplanung beim
Task unter „Allgemein" auf **„Unabhängig von der Benutzeranmeldung ausführen"**
umstellen (Windows fragt einmal das Kontopasswort ab).

### Von Hand statt per Skript

Falls du die Aufgaben lieber selbst anlegst — Eingabeaufforderung als
Administrator:
```
schtasks /Create /F /TN "Spritradar Bot"     /TR "C:\Spritradar\windows\run-bot.bat quiet"     /SC MINUTE /MO 2
schtasks /Create /F /TN "Spritradar Collect" /TR "C:\Spritradar\windows\run-collect.bat quiet" /SC HOURLY /ST 00:05
```

## Testen ohne Aufgaben

- `windows\run-bot.bat` (Doppelklick) → arbeitet alle offenen Chat-Befehle ab.
  Also erst in Telegram `go` schicken, dann das Skript starten.
- `windows\run-collect.bat` → schreibt einen Messpunkt in `data\intraday.json`.
- `windows\run-daily.bat` → schickt den Tankplan sofort, ohne Umweg über den Chat.

## Status prüfen

Doppelklick auf **`windows\status.bat`** – zeigt auf einen Blick:
- ob die beiden Aufgaben überhaupt **angelegt** sind,
- **letzte / nächste Laufzeit** und **letztes Ergebnis** (`0` = ok),
- ob `secrets.bat` und die Python-Umgebung da sind,
- die letzten Zeilen aus **`logs\spritradar.log`**.

## Updates einspielen
```
cd C:\Spritradar
git pull
.venv\Scripts\pip install -r requirements.txt
```

## Fehlerbehebung

Immer aus **`C:\Spritradar`** starten (nicht aus `C:\` oder `C:\Windows`):
```
cd C:\Spritradar
windows\run-bot.bat
```

| Meldung | Ursache & Lösung |
| --- | --- |
| `windows\secrets.bat fehlt` | Datei nicht vorhanden – oder sie heißt in Wirklichkeit `secrets.bat.txt`. Prüfen: `dir windows` · Umbenennen: `ren windows\secrets.bat.txt secrets.bat` |
| `No module named 'requests'` (o. ä.) | Abhängigkeiten fehlen: `.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `Python-Umgebung fehlt` | `windows\install-tasks.bat` legt sie an; manuell: `py -m venv .venv` |
| `Das System kann den angegebenen Pfad nicht finden` | Falsches Verzeichnis – erst `cd C:\Spritradar` |
| `go` bleibt unbeantwortet | Aufgabe fehlt oder schlägt fehl. `windows\status.bat` prüfen – „Letztes Ergebnis" muss `0` sein. Fehlt die Aufgabe, `windows\install-tasks.bat` ausführen. |
| Aufgabe existiert, „Letztes Ergebnis" ≠ 0 | Skript bricht ab – einmal von Hand starten (`cd C:\Spritradar` + `windows\run-bot.bat`), Meldung lesen |
| `"py" ist nicht als Befehl erkannt` | Python fehlt: von python.org installieren, dabei **„Add python.exe to PATH"** ankreuzen |
