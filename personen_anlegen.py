"""Personen aus CSV lesen und in der Datenbank anlegen"""

import argparse
import csv
import os
import sys
from dotenv import load_dotenv
import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont

# Format der QR-Codes
# Der Benutzercode hat 11 Stellen.
# Die letzte Stelle kann sein:
# a (addiere 1 Credit)
# r (Benutzer auf 0 setzen)
# k (gib den Kontostand aus)
# l (Benutzer löschen)

# Spezialcodes:
# Alle Benutzerkontostände ausgeben: 39b3bca191be67164317227fec3bed
# Alle Kontostände auf 0 setzen: 6f75c49f98c66696babf1e1e0fe91a2

# debugging
# import pdb; pdb.set_trace()

load_dotenv()
api_url=os.environ.get("API_URL")
api_key=os.environ.get("API_KEY")

def delete_request(url, headers=None):
    """
    Führt einen DELETE-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.delete(url, headers=headers, timeout=5)
        response.raise_for_status()
        # print("DELETE-Request erfolgreich!")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim DELETE-Request: {e}.")
        return None


def get_request(url, headers=None, params=None):
    """Führt einen GET-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
        params (dict, optional): Ein Dictionary mit Query-Parametern. Defaults to None.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()  # Wirft eine Exception für fehlerhafte Statuscodes
        # print("GET-Request erfolgreich!")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim GET-Request: {e}.")
        sys.exit(0)


def post_request(url, headers=None, json=None):
    """Führt einen POST-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
        json (dict, optional): Ein Dictionary, das als JSON-Daten gesendet wird. Defaults to None.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.post(url, headers=headers, json=json, timeout=5)
        response.raise_for_status()
        # print("POST-Request erfolgreich!")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim POST-Request: {e}.")
        sys.exit(0)


def put_request(url, headers=None, json=None):
    """
    Führt einen PUT-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
        json (dict, optional): Ein Dictionary, das als JSON-Daten gesendet wird. Defaults to None.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.put(url, headers=headers, json=json, timeout=5)
        response.raise_for_status()
        # print("PUT-Request erfolgreich!")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim PUT-Request: {e}.")
        return None


def healthcheck():
    """
    Healthcheck gegen API ausführen.

    Args:
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
                                    Falls nicht angegeben, werden die Standard-Header verwendet.
                                    Defaults to None.

    Returns:
        dict or None: Die JSON-Antwort der Healthcheck-Endpunktes oder None bei einem Fehler.
    """

    get_url = f"{api_url}/health-protected"
    get_headers = {
        'X-API-Key': api_key
    }

    get_response = get_request(get_url, get_headers)
    if get_response:
        return get_response.json()


def person_einfuegen(person_code, person_name):
    """
    Eine neue Person in die Datenbank einfügen.

    Args:
        person_code (str): Der Code der einzufügenden Person.
        person_name (str): Der Name der einzufügenden Person.
    """

    post_url = f"{api_url}/person"
    post_headers = {
        'X-API-Key': api_key
    }

    post_daten = {
        'code': person_code,
        'name': person_name
    }

    post_response = post_request(post_url, post_headers, json=post_daten)
    if post_response:
        # print("POST Response Body:")
        # print(post_response.json())
        print(
            f"\nDatensatz für '{person_name}' wurde hinzugefügt.")


def person_existent(person_code):
    """
    Prüft, ob eine Person bereits in der Datenbank angelegt wurde.

    Args:
        person_code (str): Der Code der Person.

    Returns:
        True or False, wenn die Person existiert oder None bei Fehler.
    """

    get_url = f"{api_url}/person/existent/{person_code}"

    get_headers = {
        'X-API-Key': api_key
    }

    get_response = get_request(get_url, get_headers)

    person_daten = get_response.json()
    if None in person_daten:
        print("Fehler beim Abrufen der Personendaten.")
        return None  # Oder eine andere Fehlerbehandlung, z.B. eine Exception werfen
    elif not 'error' in person_daten:
        return True
    return False


def erzeuge_qr_code(daten, text, qr_code_dateiname="qr_code.png"):
    """
    Erzeugt einen QR-Code mit zusätzlichem Infotext als PNG-Datei.

    Args:
        daten (str): Die Daten, die im QR-Code kodiert werden sollen.
        text (str): Der Infotext, der unter dem QR-Code angezeigt wird.
        qr_code_dateiname (str, optional): Der Name der zu speichernden PNG-Datei.
                                           Defaults to "qr_code.png".
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
    text_abstand_unten = 20

    # Schriftart laden (stelle sicher, dass die Schriftartdatei existiert)
    try:
        schriftart = ImageFont.truetype(
            "/usr/share/fonts/TTF/Hack-Bold.ttf", schriftgroesse)
    except IOError:
        schriftart = ImageFont.load_default()
        print("Schriftart nicht gefunden. Verwende Standardschriftart.")

    # Bild vergrößern und Infotext anfügen
    zeichne = ImageDraw.Draw(img)
    text_bbox = zeichne.textbbox((0, 0), text, font=schriftart)
    text_hoehe = text_bbox[3] - text_bbox[1]

    # Füge den Abstand zur neuen Höhe hinzu
    neue_hoehe = hoehe + text_hoehe + text_abstand_unten
    neues_bild = Image.new("RGBA", (breite, neue_hoehe), (0, 0, 0, 0))
    neues_bild.paste(img, (0, 0))
    zeichne_neu = ImageDraw.Draw(neues_bild)

    hintergrund_y = hoehe
    zeichne_neu.rectangle(
        [(0, hintergrund_y), (breite, neue_hoehe)], fill=hintergrund_farbe)

    text_breite = text_bbox[2] - text_bbox[0]
    text_x = (breite - text_breite) // 2
    text_y = neue_hoehe - text_abstand_unten - text_hoehe

    zeichne_neu.text((text_x, text_y), text, fill=text_farbe,
                     font=schriftart, anchor="lt")

    # print(f"Breite {breite} - Höhe {hoehe} - neue Höhe {neue_hoehe}")
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

    CSV_PERSONEN = "mitglieder.csv"
    AUSGABE_ORDNER = "qr-codes/"

    parser = argparse.ArgumentParser(description="Erzeuge QR-Codes entsprechend der Liste in der csv-Datei.")
    parser.add_argument("--force-creation", action="store_true", help="Erzwingt die Erstellung der QR-Codes auch wenn die Person bereits in der Datenbank angelegt wurde.")

    args = parser.parse_args()

    try:
        # Erstelle den Ausgabeordner, falls er nicht existiert
        healthcheck()
        os.makedirs(AUSGABE_ORDNER + 'admin-codes', exist_ok=True)
        with open(CSV_PERSONEN, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 2:  # Es sollte Code und Nachname Vorname in der Datei stehen
                    # Nimm den ersten Eintrag (den 10-stelligen Code) und entferne Leerzeichen
                    code = row[0].strip()
                    person = row[1].strip()
                    # Überprüfe, ob es ein 10-stelliger Zahlencode ist
                    if len(code) == 10 and code.isdigit():
                        # Prüfe, ob die Person bereits angelegt wurde

                        if not person_existent(code) or args.force_creation:
                            # Speichere Person in Datenbank
                            person_einfuegen(code, person)
                            # Aktion a - Addiere 1 Credit
                            dateiname = os.path.join(
                                AUSGABE_ORDNER, f"{code} - {person} - Addiere 1 Credit.png")
                            erzeuge_qr_code(
                                code + "a", "1 Credit berechnen", dateiname)
                            # Aktion r - Credits auf 0 setzen
                            dateiname = os.path.join(
                                AUSGABE_ORDNER, f"{code} - {person} - Credits auf 0 setzen.png")
                            erzeuge_qr_code(
                                code + "r", "Kontostand auf 0 setzen", dateiname)
                            # Aktion k - Kontostand ausgeben
                            dateiname = os.path.join(
                                AUSGABE_ORDNER, f"{code} - {person} - Kontostand ausgeben.png")
                            erzeuge_qr_code(
                                code + "k", "Kontostand ausgeben", dateiname)
                            # Aktion l - Person löschen
                            dateiname = os.path.join(
                                AUSGABE_ORDNER, f"{code} - {person} - Person löschen.png")
                            erzeuge_qr_code(
                                code + "l", "Benutzer löschen", dateiname)
                        else:
                            print(f"Person mit Code {code} existiert bereits in der Datenbank.")
                    else:
                        print(
                            f"Zeile '{row}' in der CSV-Datei enthält keinen gültigen 10-stelligen Zahlencode.")
                else:
                    print(f"Ungültige Zeile in der CSV-Datei: '{row}'.")

        print("\nSondercodes speichern:")
        dateiname = os.path.join(AUSGABE_ORDNER + 'admin-codes', "Alle Personen ausgeben.png")
        erzeuge_qr_code("39b3bca191be67164317227fec3bed",
                        "Alle Personen ausgeben", dateiname)
        dateiname = os.path.join(
            AUSGABE_ORDNER + 'admin-codes', "Alle Konten auf 0 setzen.png")
        erzeuge_qr_code("6f75c49f98c66696babf1e1e0fe91a2",
                        "Alle Konten auf 0 setzen", dateiname)

        print(
            f"\nQR-Codes wurden basierend auf den Codes in '{CSV_PERSONEN}' im Ordner '{AUSGABE_ORDNER}' gespeichert.")

    except FileNotFoundError:
        print(f"Fehler: Die CSV-Datei '{CSV_PERSONEN}' wurde nicht gefunden.")
    except ImportError as e:
        print(f"Ein Importfehler ist aufgetreten: {e}.")
    except IOError as e:
        print(f"Ein Fehler beim Lesen der CSV-Datei ist aufgetreten: {e}.")
    except KeyboardInterrupt:
        pass
    finally:
        exit_gracefully()
