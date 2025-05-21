"""Liest QR-Codes über Webcam und agiert auf enhaltene Codes"""

import sys
import time
import json
import os
from dotenv import load_dotenv
import cv2
# import numpy as np # nur für optionale Visualisierung
from pyzbar.pyzbar import decode
import handle_requests as hr

# Format der QR-Codes
# Der Benutzercode hat 11 Stellen.
# Die letzte Stelle kann sein:
# a Saldoänderung -1
# r Benutzer auf 0 setzen
# k gib das Saldo des Benutzers aus
# l Benutzer löschen -- Funktion auskommentiert

# Spezialcodes:
# Das Saldo aller Benutzer anzeigen: 39b3bca191be67164317227fec3bed

# debugging
# import pdb; pdb.set_trace()

load_dotenv()
api_url=os.environ.get("API_URL")
api_key=os.environ.get("API_KEY")
my_name = os.environ.get("MY_NAME")

def json_daten_ausgeben(daten):
    """
    Gibt die JSON-Daten in einem menschenlesbaren Format aus.

    Args:
        daten (str): Ein JSON-String.
    """

    spalte1_breite = 20
    spalte2_breite = 2

    # Prüfe, ob die Eingabe ein String ist
    if isinstance(daten, str):
        # Versuche, den String als JSON zu laden.
        try:
            daten_obj = json.loads(daten)
        except json.JSONDecodeError as e:
            print(f"Fehler beim Dekodieren des JSON-Strings: {e}.")
            return
    else:
        daten_obj = daten

    # Stelle sicher, dass wir eine Liste von Dictionaries haben.
    if isinstance(daten_obj, list):
        print("\nAktuelle Salden:")
        print("-" * 40)
        for eintrag in daten_obj:
            if isinstance(eintrag, dict):
                print(
                    f"{eintrag.get('nachname', 'N/A')} {eintrag.get('vorname', 'N/A'):<{spalte1_breite}}: {eintrag.get('saldo', 'N/A'):>{spalte2_breite}}")
            else:
                print(
                    "Fehler: Jeder Eintrag in der Liste sollte ein Dictionary sein.")
                return
        print("-" * 40)
    elif isinstance(daten_obj, dict):
        print(
            f"{daten_obj.get('nachname', 'N/A')} {daten_obj.get('vorname', 'N/A')}: {daten_obj.get('saldo', 'N/A')}")
    else:
        print(
            "Fehler: Die Eingabe sollte ein gültiger JSON-String oder eine Liste/Dictionary sein.")
        return


def qr_code_lesen(cap_video):
    """
    Liest QR-Codes vor der Kamera.

    Args:
        cap_video (cv2.VideoCapture): Das VideoCapture-Objekt der Kamera.
    """

    letzter_inhalt = None
    wartezeit_aktiv = False
    wartezeit_start = 0

    while True:
        ret, frame = cap_video.read()
        if not ret:
            print("Frame konnte nicht gelesen werden!")
            break

        if wartezeit_aktiv and (time.time() - wartezeit_start < 5):
            # Videobild als Fenster öffnen
            # cv2.imshow('QR-Code Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue  # Überspringe die QR-Code-Erkennung während der Wartezeit
        if wartezeit_aktiv:
            wartezeit_aktiv = False
            letzter_inhalt = None  # Zurücksetzen, um neue Erkennung zu ermöglichen

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_objects = decode(gray)

        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            if qr_data != letzter_inhalt:
                werte_qr_code_aus(str(qr_data))
                letzter_inhalt = qr_data
                wartezeit_aktiv = True
                wartezeit_start = time.time()

                # # Optionale Visualisierung
                # points = obj.polygon
                # if len(points) > 4:
                #     hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                #     hull = list(map(tuple, np.int0(hull)))
                # else:
                #     hull = points
                # n = len(hull)
                # for j in range(0, n):
                #     cv2.line(frame, hull[j], hull[(j + 1) % n], (0, 255, 0), 2)

        # Videobild als Fenster öffnen
        # cv2.imshow('QR-Code Scanner', frame)

        # Abbruch mit Taste q
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break


def werte_qr_code_aus(qr_code):
    """
    Führt Code entsprechend der Anweisung auf dem QR-Code aus.

    Args:
        qr_code (str): Der Inhalt des gelesenen QR-Codes.
    """
    # print(f"Code gelesen: {qr_code}")
    system_beep_ascii()
    if (qr_code) == "39b3bca191be67164317227fec3bed":
        daten_alle = daten_lesen_alle()
        json_daten_ausgeben(daten_alle)
    else:
        if (len(qr_code)) == 11:
            its_a_usercode(qr_code)
        else:
            print(f"\nUnbekannter Code: {qr_code}")

    # Leerzeile am Ende
    # print()


def its_a_usercode(usercode):
    """
    Wenn es sich um einen Benutzercode handelt wird entsprechend der Aktion verfahren.

    Args:
        usercode (str): Der gelesene Benutzercode.
    """

    print("")
    aktion = usercode[-1] # letztes Zeichen im usercode bestimmt die auszuführende Aktion
    code = usercode[:10] # die ersten 10 Stellen des usercodes sind dem Benutzer zugeordnet
    beschreibung = my_name

    # lade den Benutzer aus der DB
    print(f"Benutzer: {code} - Aktion: {aktion}. ", end='')

    if (aktion) == "a":
        saldo_aenderung = "-1"
        person_transaktion_erstellen(code, beschreibung, saldo_aenderung)
        print("Transaktion erfolgreich regisriert. ", end='')
        abfrage = person_daten_lesen(code)
        if abfrage:
            nachname, vorname, saldo = abfrage
            print(f"Der Saldo für {nachname} {vorname} ist jetzt {saldo}.")
    elif (aktion) == "k":
        # Aktuelles Saldo anzeigen
        abfrage = person_daten_lesen(code)
        if abfrage:
            nachname, vorname, saldo = abfrage
            print(f"Der Saldo für {nachname} {vorname} ist {saldo}.")
    else:
        print("Mit dem Code stimmt etwas nicht.")


def healthcheck():
    """
    Healthcheck gegen API ausführen.

    Returns:
        dict or None: Die JSON-Antwort der Healthcheck-Endpunktes oder None bei einem Fehler.
    """

    get_url = f"{api_url}/health-protected"
    get_headers = {
        'X-API-Key': api_key
    }

    get_response = hr.get_request(get_url, get_headers)
    if get_response:
        return get_response.json()
    return None


def daten_lesen_alle():
    """
    Daten aller Benutzer anzeigen.

    Returns:
        dict or None: Die JSON-Antwort der API oder None bei einem Fehler.
    """

    get_url = f"{api_url}/saldo-alle"
    get_headers = {
        'X-API-Key': api_key
    }

    get_response = hr.get_request(get_url, get_headers)
    if get_response:
        return get_response.json()
    return None


def person_daten_lesen(code):
    """
    Daten einer Person anzeigen, gibt den aktuellen Saldo zurück.

    Args:
        code (str): Der Code der Person, deren Daten gelesen werden sollen.

    Returns:
        tuple or None: Ein Tupel mit (nachname, vorname, saldo) oder None bei einem Fehler.
    """

    get_url = f"{api_url}/person/{code}"

    get_headers = {
        'X-API-Key': api_key
    }

    get_response = hr.get_request(get_url, get_headers)

    person_daten = get_response.json()
    if 'error' in person_daten:
        print(f"Fehler beim Abrufen der Personendaten: {person_daten['error']}.")
        return None
    if person_daten:
        return (person_daten['nachname'], person_daten['vorname'], person_daten['saldo'])
    return None


def person_transaktion_erstellen(code, beschreibung, saldo_aenderung):
    """
    Transaktion für eine Person ausführen.

    Args:
        code (str): Der Code der Person, für die die Transaktion erstellt wird.
        beschreibung (str): Die Beschreibung der Buchung.
        saldo_aenderung (str): Der Wert um den sich der Saldo ändern soll.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """

    put_url = f"{api_url}/person/{code}"
    put_headers = {
        'X-API-Key': api_key
    }

    put_daten = {
        'beschreibung': beschreibung,
        'saldo_aenderung': saldo_aenderung
    }

    put_response = hr.put_request(put_url, put_headers, put_daten)
    if put_response:
        return put_response
    return None


def system_beep_ascii():
    """
    Gibt einen Piepton aus.
    """

    print('\a', end='', flush=True)
    time.sleep(0.1)  # kurze Pause, um den Ton hörbarer zu machen


def exit_gracefully(cap_video):
    """
    Räume auf und beende das Programm ordentlich.

    Args:
        cap_video (cv2.VideoCapture): Das VideoCapture-Objekt der Kamera.
    """

    print('Räume auf und beende das Programm ordentlich.')
    cap_video.release()
    cv2.destroyAllWindows()
    sys.exit(0)


if __name__ == "__main__":
    if not api_url:
        print("Fehler: API_URL ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)
    if not api_key:
        print("Fehler: API_KEY ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)

    try:
        health_status = healthcheck()
        if health_status is None:
            print("Healthcheck fehlgeschlagen. Beende Skript.")
            sys.exit(1)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise IOError("Kamera konnte nicht geöffnet werden.")
        print("\nBereitschaft.\n")
        qr_code_lesen(cap)
    except ImportError as e:
        print(f"Ein Importfehler ist aufgetreten: {e}.")
    except IOError as e:
        print(f"Fehler beim Öffnen der Kamera: {e}.")
    except KeyboardInterrupt:
        pass
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        exit_gracefully(cap)
