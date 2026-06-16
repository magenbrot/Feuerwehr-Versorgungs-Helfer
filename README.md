# Feuerwehr-Versorgungs-Helfer: Client-Anwendungen & Verwaltungs-Skripte 📱💻🛠️

## Übersicht ℹ️

Dieses Repository enthält Client-Anwendungen (Terminals) für das digitale Strichlisten-System "Feuerwehr-Versorgungs-Helfer". Diese Python-Skripte ermöglichen es Benutzern, über QR-Codes oder NFC-Tokens "Striche zu machen" (d.h. Guthaben abzubuchen). Alle Komponenten kommunizieren mit dem [separaten Backend-System](https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer-API).

## Funktionsweise 🎯

Die Anwendungen und Skripte dienen unterschiedlichen Zwecken:

* **QR-Code Leser (`qrcode_leser.py`)**: Verwendet eine angeschlossene Webcam, um spezielle QR-Codes zu erkennen und Aktionen auszulösen.
* **NFC-Leser (`nfc_reader.py`)**: Verwendet einen ACR122U/ACR1252U NFC-Kartenleser, um NFC-Tokens (Karten, Anhänger, Smartphones) zu erkennen und Transaktionen zu starten. Der Code ist eventuell auch mit anderen USB-NFC-Readern kompatibel.

## Allgemeine Voraussetzungen 🛠️

### Hardware

* Eine kompatible Hardware-Plattform. Die App wurde ausführlich mit dem RasperryPi 5 getestet
* Eine kompatible Kamera, z.B. eine USB-Kamera 720p von Logitech
* Einen kompatiblen NFC-Kartenleser, unterstützt werden die Chips ACR122U oder ACR1252U
* Einen kompatiblen Lautsprecher, z.B. via USB oder ein Bildschirm mit HDMI

### Software

* Python 3.11+
* Eine funktionierende Instanz des [Feuerwehr-Versorgungs-Helfer Backends](https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer-API)
* Eine `.env`-Datei im Stammverzeichnis dieses Projekts mit folgenden Umgebungsvariablen:
  * `API_URL`: Die vollständige URL zum API-Endpunkt des Backends (z.B. `http://localhost:5000`).
  * `API_KEY`: Ein gültiger API-Schlüssel für die Authentifizierung am Backend (wird über die Web-GUI angelegt)
  * `TOKEN_DELAY`: Zeit in Sekunden, die der aufgelegte NFC-Token für weitere Transaktionen blockiert wird.
  * `MY_NAME` (optional, für `qrcode_leser.py` & `nfc_reader.py`): Ein Name für das Terminal (z.B. "Kasse Theke"), der als Beschreibung für Transaktionen verwendet wird.
  * `DISABLE_BUZZER`: Versucht den eingebauten Hardware-Signalton des NFC-Readers zu deaktivieren. True = deaktivieren, False = aktivieren.

## Installation 🔧

### Umgebung vorbereiten (root)

Für NFC-Kartenleser mit dem ACR122U Chipsatz ist es notwendig die Kernelmodule zu blockeren, die eventuell automatisch geladen werden und den korrekten Zugriff auf der Reader verhindern.

Dazu müssen die Module in der Kernel Blacklist hinterlegt werden:

```bash
cat << EOF > /etc/modprobe.d/blacklist-nfc.conf
blacklist pn533
blacklist nfc
blacklist pn533_usb
EOF
```

Danach den initramfs aktualisieren: `sudo update-initramfs -k all -u` (bei Debian/Ubuntu) oder `sudo dracut -f` (bei Fedora/CentOS) und neu starten (alternativ die Module mit `modprobe -r` entladen).

Jetzt muss ggf. noch eine Regel für das Policy Kit hinzugefügt werden (z.B. bei Ubuntu), damit der Benutzer auch auf den NFC-Reader zugreifen darf.

```bash
cat << EOF > /etc/polkit-1/rules.d/90-pcscd-access.rules
// Allow any active user in "plugdev" group to access pcscd and cards
polkit.addRule(function(action, subject) {
    if (action.id == "org.debian.pcsc-lite.access_pcsc" || // Zugriff auf den Daemon
        action.id == "org.debian.pcsc-lite.access_card") {  // Zugriff auf die Karte
        if (subject.isInGroup("plugdev")) {
            return polkit.Result.YES;
        }
    }
});
EOF
systemctl restart polkit.service
```

Jetzt können die Tools und weiteren Voraussetzungen installiert werden:

```bash
apt update
apt install git libacsccid1 pcscd pcsc-tools libpcsclite-dev libgl1 libzbar0 python3-dev
```

Folgende Pakete sind wichtig:

* `libacsccid1`: Eine Library zur Unterstützung von NFC-Readern mit dem ACS ACR122U (oder ähnlichen) Chipsätzen
* `pcscd` `pcsc-tools` `libpcsclite-dev`: SmartCard Tools für Linux, notwendig für den USB NFC-Reader und das Python-Modul `pyscard`
* `libgl1`: Für das Python-Modul `opencv-python`
* `libzbar0` (bzw. `libzbar0t64` bei Armbian) : Für das Python-Modul `pyzbar`

### Hardware testen

Testen des NFC-Readers über das Tool `pcsc_scan`. Es sollten dann die passenden Events ausgegeben werden:

```bash
root@rock64 ~# pcsc_scan
PC/SC device scanner
V 1.7.1 (c) 2001-2022, Ludovic Rousseau <ludovic.rousseau@free.fr>
Using reader plug'n play mechanism
Scanning present readers...
0: ACS ACR122U PICC Interface 00 00

Thu Jun  5 11:13:20 2025
 Reader 0: ACS ACR122U PICC Interface 00 00
  Event number: 1
  Card state: Card inserted,
  ATR: 3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 6A
[...]
```

#### Soundausgabe konfigurieren

Die Sounds für verschiedene System-Ereignisse können über die `.env` Datei frei konfiguriert werden. Die Töne müssen im Verzeichnis `static/sounds/` liegen (ohne Angabe der Dateiendung `.mp3`). Falls ein Ereignis keinen Ton abspielen soll, kann der Wert auf `none`, `false` oder leer gelassen werden.

Folgende Events können in der `.env` konfiguriert werden:

| Variable | Beschreibung | Standard-Sound |
|---|---|---|
| `SOUND_SCAN` | Wird abgespielt, sobald ein NFC-Token oder QR-Code gescannt wird. | `beep1` |
| `SOUND_SUCCESS` | Erfolgreiche Buchung (Kontostand > 0). | `plopp1` |
| `SOUND_ZERO_BALANCE` | Buchung erfolgreich, aber neuer Kontostand ist genau 0€. | `badumtss` |
| `SOUND_BLOCKED` | Buchung fehlgeschlagen, da der Benutzer blockiert ist (`block` Aktion). | `wah-wah` |
| `SOUND_LOCKED` | Benutzerkonto ist gesperrt (`locked` Aktion / HTTP 403). | `error` |
| `SOUND_INFO` | Informations-Abfrage (z. B. Kontostandsabfrage per QR-Code). | `tagesschau` |
| `SOUND_ERROR` | Fehlerhafte Aktionen, unbekannte Benutzer oder API-Fehler. | `error` |

##### via HDMI

Die Soundausgabe via HDMI hat auf dem RaspberryPi 5 ohne weitere Änderungen direkt funktioniert. Die Funktion kann über den direkten Aufruf des Scripts `python3 sound_ausgabe.py` getestet werden (venv aktivieren nicht vergessen).

##### via USB-Lautsprecher

Für die Soundausgabe via USB-Lautsprecher musste ich auf dem RaspberryPi 5 die VC4 Treiber deaktivieren und Alsamixer konfigurieren.

In der `/boot/firmware/config.txt` diese beiden Einträge anpassen:
```
# Enable audio (loads snd_bcm2835)
dtparam=audio=off

# Enable DRM VC4 V3D driver
dtoverlay=vc4-kms-v3d,noaudio
```

Die Datei `/etc/asound.conf` mit folgendem Inhalt anlegen:
```
pcm.!default {
    type hw
    card 1
}
 
ctl.!default {
    type hw           
    card 1
}
```

Danach muss das System einmal rebootet werden.

##### Lautstärke einstellen

zum Beispiel auf 80% setzen:
```
amixer set 'PCM' 80%
```
Die Lautstärke kann über den direkten Aufruf des Scripts `python3 sound_ausgabe.py` getestet werden (venv aktivieren nicht vergessen).

### Umgebung vorbereiten (user)

```bash
git clone https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer.git
cd Feuerwehr-Versorgungs-Helfer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Systemd Service einrichten

Der Start der Applikationen soll über systemd erfolgen. Dazu sollten sie bereits läuffähig sein (also ein Python3 venv existieren und die benötigten Module installiert sein, siehe unten).

* Die Dateien aus `installation/systemd` nach `/etc/systemd/system/` kopieren und anpassen.
* Systemd reloaden `systemctl daemon-reload`
* Die beiden Services aktivieren: `systemctl enable --now fvh-qrcode-reader.service; systemctl enable --now fvh-nfc-reader.service`
* Logfiles prüfen:
  1. `journalctl -u fvh-qrcode-reader.service`
  2. `journalctl -u fvh-nfc-reader.service`

## Die Applikationen

### 1. QR-Code Leser (`qrcode_leser.py`) 📷

Dieses Skript startet eine Webcam, erkennt QR-Codes und führt basierend auf dem Inhalt Aktionen über die API aus.

#### Aufbau der QR-Codes

* Format der QR-Codes
* Der Benutzercode hat 11 Stellen. Die letzte Stelle kann sein:
  * a Saldoänderung -1
  * k gib das Saldo des Benutzers aus
* Spezialcodes:
  * Das Saldo aller Benutzer anzeigen: 39b3bca191be67164317227fec3bed

#### Spezifische Einrichtung für QR-Code Leser

* Eine angeschlossene Webcam.
* Benutzer sollte entsprechende Systemrechte haben (Gruppe `video`)

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
* Benutzer sollte entsprechende Systemrechte haben, bzw. das System vorbereitet haben (siehe oben)
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

### Wichtige Hinweise ⚠️

* Stellen Sie sicher, dass die in der `.env`-Datei konfigurierten `API_URL` und `API_KEY` korrekt sind und mit Ihrem Backend übereinstimmen.
* Die Client-Terminals (`qrcode_leser.py`, `nfc_reader.py`) führen beim Start einen Healthcheck gegen die API aus, um die Verbindung zu überprüfen.
