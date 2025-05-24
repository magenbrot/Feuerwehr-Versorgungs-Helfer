# Feuerwehr-Versorgungs-Helfer: Client-Anwendungen & Verwaltungs-Skripte 📱💻🛠️

## Übersicht ℹ️

Dieses Repository enthält Client-Anwendungen (Terminals) und Verwaltungs-Skripte für das digitale Strichlisten-System "Feuerwehr-Versorgungs-Helfer". Diese Python-Skripte ermöglichen es Benutzern, über QR-Codes oder NFC-Tokens "Striche zu machen" (d.h. Guthaben abzubuchen) bzw. Administratoren, Benutzer anzulegen und QR-Codes zu generieren. Alle Komponenten kommunizieren mit dem [separaten Backend-System](https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer-API).

## Funktionsweise 🎯

Die Anwendungen und Skripte dienen unterschiedlichen Zwecken:

* **QR-Code Leser (`qrcode_leser.py`)**: Verwendet eine angeschlossene Webcam, um spezielle QR-Codes zu erkennen und Aktionen auszulösen.
* **NFC-Leser (`nfc_reader.py`)**: Verwendet einen ACR122U NFC-Kartenleser, um NFC-Tokens (Karten, Anhänger, Smartphones) zu erkennen und Transaktionen zu starten. Der Code ist eventuell auch mit anderen USB-NFC-Readern kompatibel.
* **Personen Anlegen (`personen_anlegen.py`)**: Ein Skript für Administratoren, um neue Benutzer aus einer CSV-Datei in der Datenbank anzulegen.
* **QR-Code Generierung (`qrcodes_generieren.py`)** Generiert QR-Codes für die Benutzer in der Datenbank.

## Allgemeine Voraussetzungen 🛠️

* Python 3.x
* Eine funktionierende Instanz des [Feuerwehr-Versorgungs-Helfer Backends](https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer-API)
* Eine `.env`-Datei im Stammverzeichnis dieses Projekts mit folgenden Umgebungsvariablen:
  * `API_URL`: Die vollständige URL zum API-Endpunkt des Backends (z.B. `http://localhost:5000`).
  * `API_KEY`: Ein gültiger API-Schlüssel für die Authentifizierung am Backend.
  * `MY_NAME` (optional, für `qrcode_leser.py` & `nfc_reader.py`): Ein Name für das Terminal (z.B. "Kasse Theke"), der als Beschreibung für Transaktionen verwendet wird.
  * `DEFAULT_PASSWORD` (für `personen_anlegen.py`): Ein Standardpasswort, das für neu angelegte Benutzer gesetzt wird.

## Installation 🔧

Umgebung vorbereiten:

```bash
git clone https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer.git
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1. QR-Code Leser (`qrcode_leser.py`) 📷

Dieses Skript startet eine Webcam, erkennt QR-Codes und führt basierend auf dem Inhalt Aktionen über die API aus.

#### Spezifische Einrichtung für QR-Code Leser

* Eine angeschlossene Webcam.
* Zusätzliche Python-Bibliotheken installieren:

    ```bash
    pip install opencv-python pyzbar python-dotenv requests
    ```

#### Funktionalität des QR-Code Lesers

* **Kontinuierliche Erkennung**: Die Webcam sucht ständig nach QR-Codes im Bild.
* **Aktionssteuerung per QR-Code**:
  * Ein Standard-Benutzercode ist 11 Zeichen lang. Die ersten 10 Zeichen identifizieren den Benutzer, das letzte Zeichen die Aktion.
    * Endung `a`: Bucht einen Standardbetrag (-1) vom Guthaben des Benutzers ab. Der aktuelle Saldo wird danach abgefragt und angezeigt.
    * Endung `k`: Fragt den aktuellen Saldo des Benutzers ab und zeigt ihn an.
  * **Spezialcode**: Der Code `39b3bca191be67164317227fec3bed` löst die Anzeige der Salden aller Benutzer aus.
* **Verzögerung**: Um doppelte Scans zu vermeiden, gibt es eine kurze Wartezeit (5 Sekunden), bevor derselbe Code erneut verarbeitet wird.
* **Feedback**: Ein System-Piepton signalisiert die erfolgreiche Erkennung eines QR-Codes. Die Ergebnisse oder Fehlermeldungen werden in der Konsole ausgegeben.
* **API-Interaktion**: Nutzt das `handle_requests.py` Modul für API-Aufrufe an Endpunkte wie `/health-protected`, `/saldo-alle`, `/person/{code}` (GET und PUT).

#### Starten des QR-Code Lesers

```bash
python qrcode_leser.py
```

### 2. NFC-Leser (`nfc_reader.py`) 💳📲

Dieses Skript verwendet einen ACR122U NFC-Kartenleser, um NFC-Chips auszulesen und entsprechende Transaktionen über die API auszulösen.

#### Spezifische Einrichtung für NFC-Leser

* Ein angeschlossener ACR122U NFC-Kartenleser mit korrekt installierten Treibern.
* Zusätzliche Python-Bibliotheken installieren:

    ```bash
    pip install pyscard python-dotenv requests
    ```

* Umgebungsvariable `TOKEN_DELAY` in der `.env`-Datei setzen (Verzögerung in Sekunden zwischen der Verarbeitung desselben Tokens).
* Umgebungsvariable `DISABLE_BUZZER` (optional, `True` oder `False`) in der `.env`-Datei, um den Piepton des Lesers zu steuern.

#### Funktionalität des NFC-Lesers

* **Kontinuierliche Token-Suche**: Sucht permanent nach NFC-Tokens auf dem Lesegerät.
* **Token-Identifikation**:
  * Versucht primär, die ATS (Answer to Select) des Tokens zu lesen.
  * Falls keine ATS verfügbar ist, wird die UID (Unique Identifier) des Tokens gelesen.
* **API-Transaktion**:
  * Die gelesenen Token-Daten (ATS oder UID im Hex-Format) werden in Base64 umgewandelt und an den `/nfc-transaktion` Endpunkt der API gesendet.
  * Die API bucht dann einen Standardbetrag vom Konto des zum Token gehörenden Benutzers ab.
  * Die Erfolgs- oder Fehlermeldung der API wird in der Konsole ausgegeben.
* **Verzögerung (`TOKEN_DELAY`)**: Verhindert mehrfache Verarbeitung desselben Tokens.
* **Buzzer-Steuerung**: Deaktiviert ggf. den Buzzer des Lesers.
* **API-Interaktion**: Nutzt das `handle_requests.py` Modul für API-Aufrufe an `/health-protected` und `/nfc-transaktion`.

#### Starten des NFC-Lesers

```bash
python nfc_reader.py
```

### 3. Personen Anlegen (`personen_anlegen.py`) 🧑‍💼

Dieses Skript dient Administratoren dazu, neue Benutzer gesammelt aus einer CSV-Datei zu importieren und sie im Backend-System anzulegen.

#### Spezifische Einrichtung `personen_anlegen.py`

* Erstellen Sie eine CSV-Datei namens `mitglieder.csv` im selben Verzeichnis wie das Skript.
  * Format pro Zeile: `10-stelliger-Code,Nachname,Vorname` (z.B. `7812934560,Völker,Oliver`).
* Eine Schriftart-Datei (z.B. `Hack-Bold.ttf`) sollte unter `/usr/share/fonts/TTF/` verfügbar sein für die Beschriftung der QR-Codes. Falls nicht, wird eine Standardschrift verwendet (die könnte aber schwieriger zu lesen sein).

#### Funktionalität `personen_anlegen.py`

* **CSV-Import**: Liest Benutzerdaten (Code, Nachname, Vorname) aus der `mitglieder.csv`.
* **Benutzeranlage via API**:
  * Für jeden neuen Benutzer wird das in der `.env`-Datei festgelegte `DEFAULT_PASSWORD` gehasht.
  * Die Benutzerdaten inklusive des gehashten Passworts werden an den `/person` Endpunkt der API gesendet, um den Benutzer im System anzulegen.
  * Es wird geprüft, ob ein Benutzer mit dem Code bereits existiert, um Duplikate zu vermeiden (kann mit `--force-creation` umgangen werden).

#### Starten des Skripts

```bash
python personen_anlegen.py
```

### 4. QR-Code Generierung (`qrcodes_generieren.py`) ➕

Dieses Skript generiert QR-Codes für die Benutzer in der Datenbank.

#### Funktionalität `qrcodes_generieren.py`

* **QR-Code-Generierung**:
  * Für jeden neu angelegten (oder per `--force-creation` erzwungenen) Benutzer werden zwei QR-Codes erstellt und in einem Unterverzeichnis `qr-codes/Nachname Vorname/` gespeichert:
    * `1x bezahlen.png`: Enthält den Code `BENUTZERCODEa` (löst eine Abbuchung aus).
    * `Saldo anzeigen.png`: Enthält den Code `BENUTZERCODEk` (zeigt den Saldo an).
  * Ein spezieller QR-Code für "Alle Personen anzeigen" (`39b3bca191be67164317227fec3bed`) wird im Ordner `qr-codes/admin-codes/` erstellt.
* **Ausgabeordner**: Alle QR-Codes werden im Hauptverzeichnis `qr-codes/` und entsprechenden Unterordnern abgelegt.

#### Starten des Skripts `qrcodes_generieren.py`

```bash
python qrcodes_generieren.py
```

### Wichtige Hinweise ⚠️

* Stellen Sie sicher, dass die in der `.env`-Datei konfigurierten `API_URL`, `API_KEY` und ggf. `DEFAULT_PASSWORD` korrekt sind und mit Ihrem Backend übereinstimmen.
* Die Client-Terminals (`qrcode_leser.py`, `nfc_reader.py`) führen beim Start einen Healthcheck gegen die API aus, um die Verbindung zu überprüfen.
* Das Skript `personen_anlegen.py` sollte nur von Administratoren und mit Bedacht ausgeführt werden, da es Änderungen an der Benutzerdatenbank vornimmt.
