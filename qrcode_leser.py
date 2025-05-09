"""Liest QR-Codes über Webcam und agiert auf enhaltene Codes"""

import sys
import time
import json
import os
from dotenv import load_dotenv
import cv2
import requests
# import numpy as np # nur für optionale Visualisierung
from pyzbar.pyzbar import decode

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
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.delete(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim DELETE-Request: {e}.")
        return response


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
        response.raise_for_status() # Wirft eine Exception für fehlerhafte Statuscodes
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim GET-Request: {e}.")
        return response


def post_request(url, headers=None, json_data=None):
    """Führt einen POST-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
        json_data (dict, optional): Ein Dictionary, das als JSON-Daten gesendet wird. Defaults to None.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.post(url, headers=headers,
                                 json=json_data, timeout=5)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim POST-Request: {e}.")
        return response


def put_request(url, headers=None, json_data=None):
    """
    Führt einen PUT-Request an die angegebene URL aus.

    Args:
        url (str): Die URL, an die der Request gesendet werden soll.
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
        json_data (dict, optional): Ein Dictionary, das als JSON-Daten gesendet wird. Defaults to None.

    Returns:
        requests.Response: Das Response-Objekt.
    """
    try:
        response = requests.put(url, headers=headers,
                                json=json_data, timeout=5)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim PUT-Request: {e}.")
        return response


def json_daten_ausgeben(daten):
    """
    Gibt die JSON-Daten in einem menschenlesbaren Format aus.

    Args:
        daten (str): Ein JSON-String.
    """

    spalte1_breite = 35
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
        print("\nAktuelle Kontostände:")
        print("-" * 40)
        for eintrag in daten_obj:
            if isinstance(eintrag, dict):
                # print("-" * 40)
                # print(f"ID: {eintrag.get('id', 'N/A')}")
                # print(f"Code: {eintrag.get('code', 'N/A')}")
                # print(f"Name: {eintrag.get('name', 'N/A')}")
                # print(f"Kontostand: {eintrag.get('kontostand', 'N/A')}")
                # print(f"{eintrag.get('name', 'N/A')}: {eintrag.get('kontostand', 'N/A')}")
                print(
                    f"{eintrag.get('benutzername', 'N/A'):<{spalte1_breite}}: {eintrag.get('summe_credits', 'N/A'):>{spalte2_breite}}")
            else:
                print(
                    "Fehler: Jeder Eintrag in der Liste sollte ein Dictionary sein.")
                return
        print("-" * 40)
    elif isinstance(daten_obj, dict):
        # print("-" * 40)
        # print(f"ID: {daten_obj.get('id', 'N/A')}")
        # print(f"Code: {daten_obj.get('code', 'N/A')}")
        # print(f"Name: {daten_obj.get('name', 'N/A')}")
        # print(f"Kontostand: {daten_obj.get('kontostand', 'N/A')}")
        print(
            f"{daten_obj.get('benutzername', 'N/A')}: {daten_obj.get('summe_credits', 'N/A')}")
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
    elif (qr_code) == "6f75c49f98c66696babf1e1e0fe91a2":
        kontostand_reset_alle()
        print("Kontostand für alle Personen wurde auf 0 gesetzt.")
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
    aktion = usercode[-1]
    code = usercode[:10]

    # lade den Benutzer aus der DB
    print(f"Benutzer: {code} - Aktion: {aktion}. ", end='')

    if (aktion) == "a":
        # Erstelle eine Transaktion wenn ein QR-Code mit a-Aktion gescannt wird
        # defaultmäßig ist das ein Getränk im Wert von 1 Credit
        artikel = "Getränk"
        credits_change = "1"
        person_transaktion_erstellen(code, artikel, credits_change)
        print("Transaktion erfolgreich regisriert. ", end='')
        abfrage = person_daten_lesen(code)
        if abfrage:
            name, aktueller_kontostand = abfrage
            print(f"Der Kontostand für {name} ist jetzt {aktueller_kontostand}.")
    elif (aktion) == "k":
        # Aktuellen Kontostand ausgeben
        abfrage = person_daten_lesen(code)
        if abfrage:
            name, aktueller_kontostand = abfrage
            print(f"Der Kontostand für {name} ist {aktueller_kontostand}.")
    elif (aktion) == "r":
        # Kontostand auf 0 setzen
        person_transaktionen_loeschen(code)
        print(f"Kontostand für {code} wurde auf 0 gesetzt.")
    elif (aktion) == "l":
        # Person löschen
        person_loeschen(code)
        print(f"Person mit {code} wurde gelöscht.")
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

    get_response = get_request(get_url, get_headers)
    if get_response:
        return get_response.json()
    return None

def daten_lesen_alle():
    """
    Daten aller Benutzer ausgeben.

    Returns:
        dict or None: Die JSON-Antwort der API oder None bei einem Fehler.
    """

    get_url = f"{api_url}/credits-total"
    get_headers = {
        'X-API-Key': api_key
    }

    get_response = get_request(get_url, get_headers)
    if get_response:
        return get_response.json()
    return None


def kontostand_reset_alle():
    """
    Kontostand aller Personen auf 0 setzen.

    Returns:
        dict or None: Die JSON-Antwort der API oder None bei einem Fehler.
    """

    delete_url = f"{api_url}/transaktionen"

    delete_headers = {
        'X-API-Key': api_key
    }

    delete_response = delete_request(delete_url, delete_headers)
    if delete_response:
        return delete_response.json()
    return None


def person_daten_lesen(code):
    """
    Daten einer Person ausgeben, gibt die summierten Credits zurück.

    Args:
        code (str): Der Code der Person, deren Daten gelesen werden sollen.

    Returns:
        tuple or None: Ein Tupel mit (name, summe_credits) oder None bei einem Fehler.
    """

    get_url = f"{api_url}/person/{code}"

    get_headers = {
        'X-API-Key': api_key
    }

    get_response = get_request(get_url, get_headers)

    person_daten = get_response.json()
    if 'error' in person_daten:
        print(f"Fehler beim Abrufen der Personendaten: {person_daten['error']}.")
        return None  # Oder eine andere Fehlerbehandlung, z.B. eine Exception werfen
    if person_daten:
        return (person_daten['name'], person_daten['summe_credits'])
    else:
        return None # Fallback, falls die Antwort leer ist (was unwahrscheinlich ist, wenn kein Fehler vorliegt)


def person_loeschen(code):
    """
    Eine Person aus der Datenbank löschen.

    Args:
        code (str): Der Code der zu löschenden Person.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """

    delete_url = f"{api_url}/person/{code}"

    delete_headers = {
        'X-API-Key': api_key
    }

    delete_response = delete_request(delete_url, delete_headers)
    if delete_response:
        return delete_response
    return None


def person_transaktion_erstellen(code, artikel, credits_change):
    """
    Transaktion für eine Person ausführen.

    Args:
        code (str): Der Code der Person, für die die Transaktion erstellt wird.
        artikel (str): Die Beschreibung des Artikels.
        credits_change (str): Die Änderung der Credits.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """

    put_url = f"{api_url}/person/{code}"
    put_headers = {
        'X-API-Key': api_key
    }

    put_daten = {
        'artikel': artikel,
        'credits': credits_change
    }

    put_response = put_request(put_url, put_headers, put_daten)
    if put_response:
        return put_response
    return None


def person_transaktionen_loeschen(code):
    """
    Transaktionen einer Person löschen.

    Args:
        code (str): Der Code der Person, deren Transaktionen gelöscht werden sollen.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """

    delete_url = f"{api_url}/person/transaktionen/{code}"
    delete_headers = {
        'X-API-Key': api_key
    }

    delete_response = delete_request(delete_url, delete_headers)
    if delete_response:
        return delete_response
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
        healthcheck()
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
