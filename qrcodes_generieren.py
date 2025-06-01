"""QR-Codes für die Personen in der Datenbank erzeugen"""

import argparse
import os
import sys
from dotenv import load_dotenv
import qrcode
from PIL import Image, ImageDraw, ImageFont
import handle_requests as hr

# Format der QR-Codes
# Der Benutzercode hat 11 Stellen.
# Die letzte Stelle kann sein:
# a (erstelle eine Transaktion Saldo -1)
# k (gib den Saldo aus)

# Spezialcodes:
# Alle Salden anzeigen: 39b3bca191be67164317227fec3bed

load_dotenv()
api_url = os.environ.get("API_URL")
api_key = os.environ.get("API_KEY")

def healthcheck():
    """
    Healthcheck gegen API ausführen.
    """
    get_url = f"{api_url}/health-protected"
    get_headers = {'X-API-Key': api_key}
    get_response = hr.get_request(get_url, get_headers)
    if get_response:
        try:
            return get_response.json()
        except ValueError: # Beinhaltet JSONDecodeError
            print(f"Fehler beim Parsen der JSON-Antwort vom Healthcheck: {get_response.text}")
            return None
    return None

def fetch_all_users_from_api():
    """
    Ruft alle Benutzer (Code, Nachname, Vorname) vom API-Endpunkt /users ab.

    Returns:
        list: Eine Liste von Benutzer-Dictionaries
              (z.B. [{'code': '123...', 'nachname': 'Muster', 'vorname': 'Max'}, ...])
              oder eine leere Liste bei Fehlern.
    """
    get_url = f"{api_url}/users"
    get_headers = {'X-API-Key': api_key}

    print(f"Versuche, Benutzerdaten von {get_url} abzurufen...")
    response = hr.get_request(get_url, get_headers)

    if response and response.status_code == 200:
        try:
            users = response.json()
            #print(f"Erfolgreich {len(users)} Benutzer von der API erhalten.")
            return users
        except ValueError:
            print(f"Fehler beim Parsen der JSON-Antwort von {get_url}: {response.text}")
            return []
    elif response:
        print(f"Fehler beim Abrufen aller Benutzer von API ({get_url}): Status {response.status_code} - {response.text}")
        return []
    else:
        print(f"Fehler beim Abrufen aller Benutzer von API ({get_url}): Keine Antwort erhalten.")
        return []

def erzeuge_qr_code(daten, text, qr_code_dateiname="qr_code.png"):
    """
    Erzeugt einen QR-Code mit zusätzlichem Infotext als PNG-Datei.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(daten)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    breite, hoehe = img.size
    text_farbe = "black"
    hintergrund_farbe = "white"
    schriftgroesse = 20
    text_abstand_unten = 20 # Gesamter Abstand unten für den Textbereich

    try:
        # Versuche eine spezifische Schriftart zu laden, falls nicht vorhanden, nimm Standard
        schriftart = ImageFont.truetype(
            "/usr/share/fonts/TTF/Hack-Bold.ttf", schriftgroesse)
    except IOError:
        schriftart = ImageFont.load_default()
        print("Schriftart 'Hack-Bold.ttf' nicht gefunden. Verwende Standardschriftart.")

    zeichne_temp = ImageDraw.Draw(Image.new("RGB", (1,1))) # Temporäres Objekt für Text-BoundingBox

    if hasattr(zeichne_temp, "textbbox"):
        # Pillow 10.0.0+
        text_box = zeichne_temp.textbbox((0,0), text, font=schriftart)
        text_breite_val = text_box[2] - text_box[0]
        text_hoehe_val = text_box[3] - text_box[1]
    elif hasattr(zeichne_temp, "textsize"):
        # Ältere Pillow Versionen
        text_breite_val, text_hoehe_val = zeichne_temp.textsize(text, font=schriftart)
    else:
        # Fallback, falls keine Textgrößenmethode gefunden wird (sehr unwahrscheinlich)
        text_breite_val = len(text) * (schriftgroesse // 2) # Grobe Schätzung
        text_hoehe_val = schriftgroesse # Grobe Schätzung

    # Höhe des neuen Bildes berechnen: QR-Code Höhe + Texthöhe + Padding oben/unten im Textbereich
    padding_text_vertikal = (text_abstand_unten - text_hoehe_val) // 2
    padding_text_vertikal = max(padding_text_vertikal, 5)

    neue_hoehe = hoehe + text_hoehe_val + 2 * padding_text_vertikal

    neues_bild = Image.new("RGBA", (breite, neue_hoehe), hintergrund_farbe) # Hintergrund für Textbereich direkt setzen
    neues_bild.paste(img, (0, 0)) # QR-Code auf das neue Bild kopieren

    zeichne_neu = ImageDraw.Draw(neues_bild)

    text_x = (breite - text_breite_val) // 2
    text_y = hoehe + padding_text_vertikal # Text beginnt nach dem QR-Code + oberes Padding

    zeichne_neu.text((text_x, text_y), text, fill=text_farbe, font=schriftart)

    try:
        neues_bild.save(qr_code_dateiname)
        print(
            f"QR-Code für '{daten}' wurde als '{qr_code_dateiname}' gespeichert.")
    except FileNotFoundError:
        print(
            f"Fehler: Das angegebene Verzeichnis für '{qr_code_dateiname}' wurde nicht gefunden.")
    except PermissionError:
        print(
            f"Fehler: Keine Berechtigung, um in '{qr_code_dateiname}' zu schreiben.")
    except OSError as e:
        print(
            f"Ein unerwarteter Fehler beim Speichern des QR-Codes ist aufgetreten: {e}.")

def exit_gracefully():
    """
    Räumt auf und beendet das Programm ordentlich.
    """
    print('Räume auf und beende das Programm ordentlich.')
    sys.exit(0)

if __name__ == "__main__":
    if not api_url:
        print("Fehler: API_URL ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)
    if not api_key:
        print("Fehler: API_KEY ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)

    AUSGABE_ORDNER = "qr-codes/"

    parser = argparse.ArgumentParser(description="Erzeuge QR-Codes für Benutzer aus der Datenbank via API.")
    parser.add_argument("--force-creation", action="store_true",
                        help="Erzwingt die Neuerstellung der QR-Codes, auch wenn sie bereits existieren (überschreibt existierende Dateien).")
    args = parser.parse_args()

    try:
        print("Führe Healthcheck aus...")
        health_status = healthcheck()
        if health_status:
            print(f"Healthcheck erfolgreich: {health_status.get('message', 'OK')}")
        else:
            print("Healthcheck fehlgeschlagen. Überprüfe API-Verbindung und Schlüssel.")
            # Optional: Programm beenden, wenn Healthcheck fehlschlägt
            # sys.exit(1)

        os.makedirs(os.path.join(AUSGABE_ORDNER, 'admin-codes'), exist_ok=True)

        print("\nRufe Benutzerdaten von der API ab...")
        user_list_from_api = fetch_all_users_from_api()

        if not user_list_from_api:
            print("Keine Benutzerdaten von der API erhalten oder API-Endpunkt nicht verfügbar/leer.")
            print("Es werden keine benutzerspezifischen QR-Codes generiert.")
        else:
            print(f"{len(user_list_from_api)} Benutzerdatensätze von der API erhalten. Verarbeite...")

        for user_data in user_list_from_api:
            code = user_data.get('code')
            nachname = user_data.get('nachname')
            vorname = user_data.get('vorname')

            if not (code and nachname and vorname):
                print(f"Unvollständige Benutzerdaten übersprungen: {user_data}")
                continue

            if not (len(code) == 10 and code.isdigit()):
                print(
                    f"Benutzerdaten für '{vorname} {nachname}' enthalten keinen gültigen 10-stelligen Zahlencode ('{code}'). Überspringe.")
                continue

            print(f"\nVerarbeite Benutzer: {vorname} {nachname} (Code: {code})")
            user_qr_folder = os.path.join(AUSGABE_ORDNER, f"{nachname.strip()} {vorname.strip()}")

            # Dateipfade für die QR-Codes dieses Benutzers
            qr_bezahlen_pfad = os.path.join(user_qr_folder, "1x bezahlen.png")
            qr_saldo_pfad = os.path.join(user_qr_folder, "Saldo anzeigen.png")

            # Logik für --force-creation: Wenn nicht gesetzt, überspringe existierende Dateien
            generate_bezahlen = True # pylint: disable=C0103
            if os.path.exists(qr_bezahlen_pfad) and not args.force_creation:
                #print(f"Datei '{qr_bezahlen_pfad}' existiert bereits. Übersprungen (--force-creation nicht gesetzt).")
                generate_bezahlen = False # pylint: disable=C0103

            generate_saldo = True # pylint: disable=C0103
            if os.path.exists(qr_saldo_pfad) and not args.force_creation:
                #print(f"Datei '{qr_saldo_pfad}' existiert bereits. Übersprungen (--force-creation nicht gesetzt).")
                generate_saldo = False # pylint: disable=C0103

            if generate_bezahlen or generate_saldo: # Nur Ordner erstellen, wenn auch was generiert wird
                os.makedirs(user_qr_folder, exist_ok=True)

            if generate_bezahlen:
                erzeuge_qr_code(code + "a", "1x bezahlen", qr_bezahlen_pfad)

            if generate_saldo:
                erzeuge_qr_code(code + "k", "Saldo anzeigen", qr_saldo_pfad)

        print("\nSondercodes speichern:")
        dateiname_special = os.path.join(AUSGABE_ORDNER, 'admin-codes', "Alle Personen anzeigen.png")
        if os.path.exists(dateiname_special) and not args.force_creation:
            print(f"Datei '{dateiname_special}' existiert bereits. Übersprungen (--force-creation nicht gesetzt).")
        else:
            erzeuge_qr_code("39b3bca191be67164317227fec3bed",
                            "Alle Personen anzeigen", dateiname_special)

        if user_list_from_api:
            print(f"\nQR-Code-Generierung für Benutzer abgeschlossen. Ergebnisse im Ordner '{AUSGABE_ORDNER}'.")
        else:
            print(f"\nNur Spezial-QR-Codes wurden im Ordner '{os.path.join(AUSGABE_ORDNER, 'admin-codes')}' gespeichert/aktualisiert (keine Benutzerdaten von API).")

    except FileNotFoundError as e:
        print(f"Fehler: Ein benötigtes Verzeichnis konnte nicht gefunden oder erstellt werden: {e}")
    except ImportError as e:
        print(f"Ein Importfehler ist aufgetreten: {e}.")
    except IOError as e:
        print(f"Ein Fehler bei Dateioperationen ist aufgetreten: {e}.")
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer unterbrochen.")
    except Exception as e: # pylint: disable=W0718
        print(f"Es ist ein allgemeiner Fehler aufgetreten: {e}")
    finally:
        exit_gracefully()
