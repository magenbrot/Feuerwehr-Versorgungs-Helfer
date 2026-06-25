# Beitragen zum Feuerwehr-Versorgungs-Helfer (Client-Anwendungen) 📱💻🛠️

Vielen Dank, dass du dich für eine Mitarbeit an den Client-Anwendungen des Feuerwehr-Versorgungs-Helfers interessierst! Dieses Dokument beschreibt die Richtlinien und Best Practices für Beiträge zu diesem Repository.

---

## 📋 Inhaltsverzeichnis

1. [Verhaltenskodex](#-verhaltenskodex)
2. [Wie kann ich beitragen?](#-wie-kann-ich-beitragen)
   - [Fehler melden (Issues)](#fehler-melden-issues)
   - [Features vorschlagen](#features-vorschlagen)
   - [Code-Beiträge leisten (Pull Requests)](#code-beiträge-leisten-pull-requests)
3. [Lokale Entwicklung & Setup](#-lokale-entwicklung--setup)
   - [Voraussetzungen](#voraussetzungen)
   - [Entwicklungsumgebung vorbereiten](#entwicklungsumgebung-vorbereiten)
   - [Hardware-Entwicklung & Berechtigungen](#hardware-entwicklung--berechtigungen)
4. [Code-Richtlinien & Qualitätssicherung](#-code-richtlinien--qualitätssicherung)
   - [Stilrichtlinien](#stilrichtlinien)
   - [Linting mit Pylint](#linting-mit-pylint)
5. [Pull Request Workflow](#-pull-request-workflow)
   - [Branch-Namenskonventionen](#branch-namenskonventionen)
   - [Commit-Nachrichten](#commit-nachrichten)
   - [PR einreichen](#pr-einreichen)

---

## 🤝 Verhaltenskodex

Bitte achte auf einen freundlichen, respektvollen und konstruktiven Umgangston. Wir möchten eine einladende Gemeinschaft für alle Beteiligten schaffen.

---

## 💡 Wie kann ich beitragen?

### Fehler melden (Issues)

Wenn du einen Fehler findest, öffne bitte ein Issue im Repository. Um uns die Behebung zu erleichtern, stelle sicher, dass du folgende Informationen angibst:

* Eine präzise Beschreibung des Fehlers und wie man ihn reproduziert.
* Die genutzte Hardware-Umgebung (z. B. Raspberry Pi 5, Kameramodell, NFC-Reader Typ wie ACR122U).
* Version von Python sowie Betriebssystem (z. B. Raspberry Pi OS / Debian).
* Relevante Auszüge aus den Log-Dateien (via `journalctl -u fvh-nfc-reader` / `fvh-qrcode-reader` oder direkt aus der Konsole).
* Was das erwartete Verhalten gewesen wäre.

### Features vorschlagen

Vorschläge für neue Funktionen sind herzlich willkommen! Beschreibe deine Idee bitte in einem Issue und erkläre den Nutzen für das System sowie die Feuerwehrleute bzw. Anwender vor Ort.

### Code-Beiträge leisten (Pull Requests)

1. **Forke** das Repository und erstelle deinen eigenen Entwicklungs-Branch.
2. Nimm deine Änderungen vor und stelle sicher, dass keine bestehende Funktionalität beeinträchtigt wird.
3. Teste deine Änderungen lokal mit deiner Hardware oder entsprechenden Mock-Skripten.
4. Führe das Linting durch und behebe eventuelle Fehler.
5. Sende einen Pull Request (PR) an den `main`-Branch des Original-Repositories.

---

## 🛠️ Lokale Entwicklung & Setup

### Voraussetzungen

* Python 3.11+
* Laufender Docker-Container oder eine manuelle Instanz des [Feuerwehr-Versorgungs-Helfer Backends (API)](https://github.com/magenbrot/Feuerwehr-Versorgungs-Helfer-API).

### Entwicklungsumgebung vorbereiten

1. Clone deinen Fork und wechsle in das Verzeichnis:
   ```bash
   git clone https://github.com/DEIN-BENUTZERNAME/Feuerwehr-Versorgungs-Helfer.git
   cd Feuerwehr-Versorgungs-Helfer
   ```
2. Erstelle eine virtuelle Umgebung und installiere die Abhängigkeiten:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Kopiere die Vorlage für die Umgebungsvariablen und passe sie an:
   ```bash
   cp .env.dist .env
   ```
   *Trage hier die Zugangsdaten und die URL deiner lokalen API-Testinstanz ein.*

### Hardware-Entwicklung & Berechtigungen

* Da dieses Projekt direkt mit Hardware-Schnittstellen (Kamera über OpenCV, NFC-Reader über `pyscard`) arbeitet, stelle sicher, dass dein Benutzer in den entsprechenden Systemgruppen ist (z. B. `video` für Kameras und `plugdev` für USB-Smartcard-Reader).
* Beachte die Installationsanweisungen in der [README.md](README.md#umgebung-vorbereiten-root) bezüglich der Kernel-Blacklist für NFC-Reader, um Konflikte zu vermeiden.
* Wenn du lokale Änderungen testest, stoppe gegebenenfalls die im Hintergrund laufenden Systemd-Dienste, um Port- oder Schnittstellenkonflikte zu vermeiden:
  ```bash
  sudo systemctl stop fvh-qrcode-reader.service
  sudo systemctl stop fvh-nfc-reader.service
  ```

---

## 📐 Code-Richtlinien & Qualitätssicherung

### Stilrichtlinien

* Verwende standardmäßige Python-PEP-8-Richtlinien.
* Halte den Code lesbar, übersichtlich und dokumentiere komplexe Logik (wie NFC-APDU-Befehle oder Bildverarbeitungsschritte) ausführlich mit Kommentaren.
* Verwende aussagekräftige Variablen- und Funktionsnamen auf Englisch (oder passend zum bestehenden Projektkontext).

### Linting mit Pylint

Bevor du deine Änderungen committest, solltest du Pylint über deinen Code laufen lassen. Wir nutzen Pylint im CI-Workflow, um Code-Qualität sicherzustellen:

```bash
# Stelle sicher, dass die virtuelle Umgebung aktiv ist
pylint $(git ls-files '*.py')
```

Bitte behebe alle Warnungen und Fehler, die von Pylint gemeldet werden, bevor du einen PR einreichst.

---

## 🚀 Pull Request Workflow

### Branch-Namenskonventionen

Verwende prägnante Namen für deine Entwicklungs-Branches:

* `feature/mein-neues-feature` für neue Funktionen.
* `fix/behebung-eines-bugs` für Bugfixes.
* `docs/doku-anpassung` für Dokumentations-Updates.

### Commit-Nachrichten

Schreibe klare und verständliche Commit-Nachrichten. Verwende idealerweise das folgende Format:

```
[Typ] Kurze Zusammenfassung der Änderungen in der Gegenwartsform

- Detail 1 der Änderung
- Detail 2 der Änderung
```

Beispiele für Typen: `Feat` (Feature), `Fix` (Bugfix), `Docs` (Dokumentation), `Refactor` (Code-Refactoring).

### PR einreichen

* Stelle sicher, dass der Ziel-Branch deines PRs `main` ist.
* Beschreibe im PR kurz, was geändert wurde und warum.
* Verlinke eventuell zugehörige Issues (z. B. `Closes #12`).
* Sobald der PR erstellt ist, läuft das automatisierte Github Action Linting (Pylint). Stelle sicher, dass dieses erfolgreich durchläuft.
