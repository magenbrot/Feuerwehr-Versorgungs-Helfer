#!/usr/bin/env python3

"""Liest QR-Codes über Webcam und agiert auf enhaltene Codes"""

import logging
import sys
import time
import json
import os
from dotenv import load_dotenv
import cv2

# import numpy as np # nur für optionale Visualisierung
from pyzbar.pyzbar import decode

import handle_requests as hr
import sound_ausgabe

load_dotenv()
api_url=os.environ.get("API_URL")
api_key=os.environ.get("API_KEY")
my_name = os.environ.get("MY_NAME")
camera_index = int(os.environ.get("CAMERA_INDEX"))
log_level = os.getenv('LOG_LEVEL', 'INFO')

logging.basicConfig(
    level=log_level,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

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
            logger.error("Fehler beim Dekodieren des JSON-Strings: %s.", e)
            return
    else:
        daten_obj = daten

    # Stelle sicher, dass wir eine Liste von Dictionaries haben.
    if isinstance(daten_obj, list):
        logger.info("\nAktuelle Salden:")
        logger.info("-" * 40)
        for eintrag in daten_obj:
            if isinstance(eintrag, dict):
                log_message = (
                    f"{eintrag.get('nachname', 'N/A')} {eintrag.get('vorname', 'N/A'):<{spalte1_breite}}: "
                    f"{eintrag.get('saldo', 'N/A'):>{spalte2_breite}}"
                )
                logger.info(log_message)
            else:
                logger.error(
                    "Fehler: Jeder Eintrag in der Liste sollte ein Dictionary sein.")
                return
        logger.info("-" * 40)
    elif isinstance(daten_obj, dict):
        log_message = f"{daten_obj.get('nachname', 'N/A')} {daten_obj.get('vorname', 'N/A')}: {daten_obj.get('saldo', 'N/A')}"
        logger.info(log_message)
    else:
        logger.error(
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
            logger.error("Frame konnte nicht gelesen werden!")
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
    # logger.info("Code gelesen: %s", qr_code)
    system_beep_ascii()
    if (qr_code) == "39b3bca191be67164317227fec3bed":
        daten_alle = daten_lesen_alle()
        json_daten_ausgeben(daten_alle)
    else:
        if (len(qr_code)) == 11:
            its_a_usercode(qr_code)
        else:
            logger.warning("Unbekannter Code: %s", qr_code)

def its_a_usercode(usercode):
    """
    Wenn es sich um einen Benutzercode handelt wird entsprechend der Aktion verfahren.

    Args:
        usercode (str): Der gelesene Benutzercode.
    """

    code = usercode[:10] # die ersten 10 Stellen des usercodes sind dem Benutzer zugeordnet
    aktion = usercode[-1] # letztes Zeichen im usercode bestimmt die auszuführende Aktion
    beschreibung = my_name

    logger.info("Benutzer: %s - Aktion: %s.", code, aktion)

    # beep sound wenn Token gescannt wurde
    sound_ausgabe.play_sound_effect("beep1")

    if (aktion) == "a":
        # lade den Benutzer aus der DB
        response = person_transaktion_erstellen(code, beschreibung)
        if response.json().get('action') == 'block':
            sound_ausgabe.sprich_text("wah-wah", f"{response.json()['message']}", sprache="de")
            return
        if  response.json().get('action') == 'locked':
            sound_ausgabe.sprich_text("error", f"{response.json()['message']}", sprache="de")
            return
        sound_ausgabe.sprich_text("plopp1", f"{response.json()['message']}", sprache="de")
        return
    if (aktion) == "k":
        # Personendaten und aktuelles Saldo holen
        abfrage = person_daten_lesen(code)
        if abfrage:
            nachname, vorname, saldo = abfrage
            logger.info("Der Saldo für %s %s ist %s €.", vorname, nachname, saldo)
            if saldo == 0:
                sound_ausgabe.sprich_text("badumtss", f"Hallo {vorname}! Dein Kontostand beträgt momentan {saldo} €.", sprache="de")
                return
            sound_ausgabe.sprich_text("tagesschau", f"Hallo {vorname}! Dein Kontostand beträgt momentan {saldo} €.", sprache="de")
            return
    else:
        logger.error("Mit dem Code stimmt etwas nicht.")
        sound_ausgabe.sprich_text("error", "Mit deinem QR-Code stimmt etwas nicht. Bitte wende dich an deinen Administrator.", sprache="de")
        return

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

def get_api_version():
    """
    API nach aktueller Version fragen.

    Returns:
        dict or None: Die JSON-Antwort des Version-Endpunktes oder None bei einem Fehler.
    """

    get_url = f"{api_url}/version"
    get_headers = {
        'X-API-Key': api_key
    }

    get_response = hr.get_request(get_url, get_headers)
    if get_response:
        return get_response.json().get('version')
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
        logger.error("Fehler beim Abrufen der Personendaten: %s.", person_daten['error'])
        return None
    if person_daten:
        return (person_daten['nachname'], person_daten['vorname'], person_daten['saldo'])
    return None

def person_transaktion_erstellen(code, beschreibung):
    """
    Transaktion für eine Person ausführen.

    Args:
        code (str): Der Code der Person, für die die Transaktion erstellt wird.
        beschreibung (str): Die Beschreibung der Buchung.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """

    put_url = f"{api_url}/person/{code}/transaktion"
    put_headers = {
        'X-API-Key': api_key
    }

    put_daten = {
        'beschreibung': beschreibung,
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

def exit_gracefully(cap_video=None):
    """
    Räume auf und beende das Programm ordentlich.

    Args:
        cap_video (cv2.VideoCapture): Das VideoCapture-Objekt der Kamera.
    """

    logger.info('Räume auf und beende das Programm ordentlich.')
    if cap_video:
        cap_video.release()
        cv2.destroyAllWindows()
    sys.exit(0)

if __name__ == "__main__":
    if not api_url:
        logger.critical("API_URL ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)
    if not api_key:
        logger.critical("API_KEY ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)

    try:
        health_status = healthcheck()
        if health_status is None:
            logger.critical("Healthcheck fehlgeschlagen. Beende Skript.")
            sys.exit(1)

        version = get_api_version()

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise IOError("Kamera konnte nicht geöffnet werden.")
        logger.info("Bereitschaft (Version %s).", version)
        qr_code_lesen(cap)
    except ImportError as e:
        logger.critical("Ein Importfehler ist aufgetreten: %s.", e)
    except IOError as e:
        logger.error("Fehler beim Öffnen der Kamera: %s.", e)
    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=W0718
        logger.critical("Ein unerwarteter Fehler im Hauptteil ist aufgetreten: %s", e)
        sys.exit(1)
    finally:
        if cap and cap.isOpened():
            exit_gracefully(cap)
        exit_gracefully()
