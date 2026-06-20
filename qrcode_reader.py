"""Liest QR-Codes über Webcam und agiert auf enhaltene Codes"""

import logging
import sys
import time
import json
import os
from contextlib import redirect_stderr
import cv2
# import numpy as np # nur für optionale Visualisierung
from pyzbar.pyzbar import decode
import sound_ausgabe
import config
import api_client

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
                    "Fehler: Jeder Eintrag in der Liste sollte ein Dictionary sein")
                return
        logger.info("-" * 40)
    elif isinstance(daten_obj, dict):
        log_message = f"{daten_obj.get('nachname', 'N/A')} {daten_obj.get('vorname', 'N/A')}: {daten_obj.get('saldo', 'N/A')}"
        logger.info(log_message)
    else:
        logger.error(
            "Fehler: Die Eingabe sollte ein gültiger JSON-String oder eine Liste/Dictionary sein")
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
    wartezeit_dauer = 5  # in Sekunden

    letzte_dekodierung_zeit = 0
    dekodierungs_intervall = 0.15  # Dekodieren alle 150 ms (ca. 6-7 Mal pro Sekunde)

    with open(os.devnull, 'w', encoding='utf-8') as devnull_file:
        while True:
            # 1. Immer einen Frame lesen, um den OpenCV-Kamerabuffer frisch zu halten
            ret, frame = cap_video.read()
            if not ret:
                logger.error("Frame konnte nicht gelesen werden!")
                break

            # 2. Cooldown-Handling (Kamera auslesen, aber Dekodierung überspringen)
            if wartezeit_aktiv:
                if time.time() - wartezeit_start >= wartezeit_dauer:
                    # Wartezeit abgelaufen
                    wartezeit_aktiv = False
                    letzter_inhalt = None  # Zurücksetzen, um neue Erkennung zu ermöglichen
                continue

            # 3. Drosselung der Dekodierung zur CPU-Schonung
            jetzt = time.time()
            if jetzt - letzte_dekodierung_zeit >= dekodierungs_intervall:
                letzte_dekodierung_zeit = jetzt

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                with redirect_stderr(devnull_file):
                    decoded_objects = decode(gray)

                for obj in decoded_objects:
                    qr_data = obj.data.decode('utf-8')
                    if qr_data != letzter_inhalt:
                        werte_qr_code_aus(str(qr_data))
                        letzter_inhalt = qr_data
                        wartezeit_aktiv = True
                        wartezeit_start = time.time()
                        break


def werte_qr_code_aus(qr_code):
    """
    Führt Code entsprechend der Anweisung auf dem QR-Code aus.

    Args:
        qr_code (str): Der Inhalt des gelesenen QR-Codes.
    """
    # logger.info("Code gelesen: %s", qr_code)
    if (qr_code) == "39b3bca191be67164317227fec3bed":
        daten_alle = api_client.daten_lesen_alle()
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

    code = usercode[:10]  # die ersten 10 Stellen des usercodes sind dem Benutzer zugeordnet
    aktion = usercode[-1]  # letztes Zeichen im usercode bestimmt die auszuführende Aktion
    beschreibung = config.MY_NAME

    logger.info("Benutzer: %s - Aktion: %s.", code, aktion)

    # beep sound wenn Token gescannt wurde
    sound_ausgabe.play_sound_effect("scan")

    if (aktion) == "a":
        # lade den Benutzer aus der DB
        response = api_client.person_transaktion_erstellen(code, beschreibung)
        if response is None:
            sound_ausgabe.sprich_text("error", "API-Fehler, bitte informiere einen Administrator.", sprache="de")
        elif response.json().get('action') == 'block':
            sound_ausgabe.sprich_text("blocked", f"{response.json()['message']}", sprache="de")
        elif response.json().get('action') == 'locked':
            sound_ausgabe.sprich_text("locked", f"{response.json()['message']}", sprache="de")
        else:
            new_saldo = int(response.json().get('saldo'))
            if new_saldo == 0:
                sound_ausgabe.sprich_text("zero_balance", f"Grüße {response.json().get('vorname')}! Dein Kontostand beträgt momentan {new_saldo}€.", sprache="de")
            else:
                sound_ausgabe.sprich_text("success", f"{response.json()['message']}", sprache="de")
            sound_ausgabe.play_sound_effect("transaction_end")
    elif (aktion) == "k":
        # Personendaten und aktuelles Saldo holen
        abfrage = api_client.person_daten_lesen(code)
        if abfrage:
            nachname, vorname, saldo = abfrage
            logger.info("Der Saldo für %s %s ist %s€.", vorname, nachname, saldo)
            sound_ausgabe.sprich_text("info", f"Grüße {vorname}! Dein Kontostand beträgt momentan {saldo}€.", sprache="de")
        else:
            sound_ausgabe.sprich_text("error", "Benutzer nicht gefunden oder API-Fehler.", sprache="de")
    else:
        logger.error("Mit dem QR-Code stimmt etwas nicht!")
        sound_ausgabe.sprich_text("error", "Mit deinem QR-Code stimmt etwas nicht. Bitte wende dich an deinen Administrator.", sprache="de")




def exit_gracefully(cap_video=None):
    """
    Räume auf und beende das Programm ordentlich.

    Args:
        cap_video (cv2.VideoCapture): Das VideoCapture-Objekt der Kamera.
    """

    logger.info('Räume auf und beende das Programm ordentlich')
    if cap_video:
        cap_video.release()
        cv2.destroyAllWindows()
    sys.exit(0)


if __name__ == "__main__":
    config.validate_config()

    try:
        health_status = api_client.healthcheck()
        if health_status is None:
            logger.critical("Healthcheck fehlgeschlagen. Beende Skript")
            sys.exit(1)

        version = api_client.get_api_version()

        cap = cv2.VideoCapture(config.CAMERA_INDEX)
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
