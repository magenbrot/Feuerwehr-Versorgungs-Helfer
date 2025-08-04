"""
Dieses Skript liest kontinuierlich NFC-Token von einem ACR122U-Reader,
extrahiert ATS und ggf. UID und sendet diese an eine konfigurierte API, um eine
Transaktion zu erstellen. Die API-URL und der API-Schlüssel werden aus
Umgebungsvariablen (.env-Datei) geladen.
"""

import base64
import binascii
import logging
import time
import os
import sys
from smartcard.Exceptions import NoCardException, CardConnectionException, SmartcardException, NoReadersException
from smartcard.System import readers
from smartcard.util import toHexString
from dotenv import load_dotenv
import handle_requests as hr
import sound_ausgabe

load_dotenv()
api_url = os.environ.get("API_URL")
api_key = os.environ.get("API_KEY")
token_delay = int(os.environ.get("TOKEN_DELAY"))
my_name = os.environ.get("MY_NAME")
disable_buzzer = os.getenv('DISABLE_BUZZER', 'False') == 'True'
log_level = os.getenv('LOG_LEVEL', 'INFO')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

logging.basicConfig(
    level=log_level,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

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

def person_transaktion_erstellen(token_hex: str) -> bool:
    """
    Verarbeitet eine NFC-Token-Transaktion durch Senden der UID an eine API.

    Diese Funktion nimmt die Hex-UID eines NFC-Tokens entgegen, konvertiert sie,
    sendet sie an einen API-Endpunkt und verarbeitet die Antwort. Sie gibt
    akustisches Feedback basierend auf dem Ergebnis.

    Args:
        token_hex: Die eindeutige ID (UID) des erkannten NFC-Tokens
                   als Hex-String.

    Returns:
        True, wenn die API-Transaktion erfolgreich war (Status 2xx),
        andernfalls False bei jeglicher Art von Fehler.
    """
    erfolgreich = False
    put_url = f"{api_url}/nfc-transaktion"
    put_headers = {'X-API-Key': api_key}
    response = None

    try:
        # 1. Token vorbereiten und validieren
        token_hex_sauber = token_hex.replace(" ", "")
        token_bytes = binascii.unhexlify(token_hex_sauber)
        token_base64 = base64.b64encode(token_bytes).decode('utf-8')
        put_daten = {
            'token': token_base64,
            'beschreibung': my_name,
        }

        # 2. API-Anfrage senden und auf HTTP-Fehler prüfen
        logger.info("Sende NFC-Token %s an die API...", token_hex_sauber)
        response = hr.put_request(put_url, put_headers, put_daten)
        response.raise_for_status()  # Löst bei 4xx/5xx eine Exception aus

        # 3. Erfolgreiche Antwort (2xx) verarbeiten
        antwort_json = response.json()
        nachricht = antwort_json.get('message', 'Aktion erfolgreich.')

        if antwort_json.get('action') == 'block':
            sound_ausgabe.sprich_text("wah-wah", nachricht, sprache="de")
        else:
            if int(antwort_json.get('saldo')) == 0:
                sound_ausgabe.sprich_text("badumtss", nachricht, sprache="de")
            else:
                sound_ausgabe.sprich_text("plopp1", nachricht, sprache="de")
        erfolgreich = True

    except hr.requests.exceptions.RequestException as e:
        # Gezielte Fehlerbehandlung für HTTP-Statuscodes
        if response is not None and response.status_code == 404:
            logger.warning("Benutzer mit Token %s nicht gefunden (404).", token_hex_sauber)
            sound_ausgabe.sprich_text("error", "Benutzer nicht gefunden.", sprache="de")
        elif response is not None and response.status_code == 403:
            fehler_nachricht = response.json().get('error', 'Benutzer gesperrt.')
            logger.warning("Benutzer ist gesperrt (403): %s", fehler_nachricht)
            sound_ausgabe.sprich_text("error", fehler_nachricht, sprache="de")
        else:
            logger.error("Fehler bei der API-Anfrage: %s", e)
            sound_ausgabe.sprich_text("error", "API-Fehler, bitte informiere einen Administrator.", sprache="de")

    except binascii.Error:
        logger.error("Fehler: Ungültiger Hexadezimalstring: %s", token_hex_sauber)
        sound_ausgabe.sprich_text("error", "Ungültiger Token gelesen.", sprache="de")

    except Exception as e:  # pylint: disable=W0718
        logger.error("Allgemeiner Fehler: %s", e, exc_info=True)
        sound_ausgabe.sprich_text("error", "Ein unerwarteter Fehler ist aufgetreten.", sprache="de")

    return erfolgreich

def lese_nfc_token_uid(connection):
    """
    Liest die UID von dem Token.

    Args:
        connection: Die Tokennverbindung.

    Returns:
        str: Die UID als Hex-String, oder None im Fehlerfall.
    """

    try:
        get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(get_uid)

        if sw1 == 0x90 and sw2 == 0x00:
            return toHexString(response)
        return None
    except Exception as e:  # pylint: disable=W0718
        logger.error("Fehler beim Lesen der Token-UID: %s", e)
        return None

def lese_nfc_token_ats(connection):
    """
    Liest die ATS von dem Token.

    Args:
        connection: Die Tokennverbindung.

    Returns:
        str: Die ATS als Hex-String, oder None im Fehlerfall.
    """

    try:
        get_ats = [0xFF, 0xCA, 0x01, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(get_ats)

        if sw1 == 0x90 and sw2 == 0x00:
            return toHexString(response)
        return None
    except Exception as e:  # pylint: disable=W0718
        logger.error("Fehler beim Lesen des Token-ATS: %s", e)
        return None

def verarbeite_token(token_hex, last_token_time):
    """
    Verarbeitet den gelesenen Token.

    Args:
        token_hex: Daten des Tokens (UID oder ATS)
        last_token_time:  Zeitpunkt der letzten erfolgreichen Verarbeitung des Tokens.

    Returns:
        float: Aktualisierte letzte Verarbeitungszeit oder None.
    """

    jetzt = time.time()

    if last_token_time is None or jetzt - last_token_time >= token_delay:
        # beep sound wenn Token gescannt wurde
        sound_ausgabe.play_sound_effect("beep1")
        transaktion_erfolgreich = person_transaktion_erstellen(token_hex)
        #saldo_ausgeben_erfolgreich = person_daten_lesen(token_hex)
        #if transaktion_erfolgreich and saldo_ausgeben_erfolgreich:
        if transaktion_erfolgreich:
            return jetzt  # Aktualisiere den Zeitstempel
        return None
    logger.info("Token %s wurde kürzlich verarbeitet. Ignoriere.", token_hex)
    return last_token_time

def schalte_buzzer_ab(nfc_reader):
    """
    Versucht den Hardware-Buzzer abzuschalten.

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """

    connection = None
    try:
        connection = nfc_reader.createConnection()
        connection.connect()
        code_disable_buzzer = [0xFF, 0x00, 0x52, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(code_disable_buzzer)

        # Überprüfe Status Code 90 00h für Erfolg
        if sw1 == 0x90 and sw2 == 0x00:
            logger.info("Buzzer erfolgreich ausgeschaltet. Antwort Daten (Hex): %s", toHexString(bytes(response)))
        else:
            logger.warning("Kommando zum Deaktivieren des Buzzers nicht erfolgreich. Status: %02X %02X", sw1, sw2)
            # Laut API Doku (Seite 9/Anhang A) bedeuten andere SWs Fehler
            if sw1 == 0x63 and sw2 == 0x00:
                logger.warning("Laut API-Dokumentation: Operation fehlgeschlagen (Status Code 63 00h).")
    except NoCardException:
        logger.debug("Es ist kein Token aufgelegt.")
        time.sleep(0.2)
    except CardConnectionException as e:
        error_message = str(e)
        if "No smart card inserted" in error_message:
            logger.debug("Es ist keine Karte aufgelegt: %s", e)
            time.sleep(0.2)
        else:
            logger.error("Fehler bei der Tokenverbindung: %s", e)
            time.sleep(0.2)
    except Exception as e:  # pylint: disable=W0718
        logger.error("Unerwarteter Fehler beim Lesen: %s", e)
        time.sleep(0.2)
    finally:
        if connection:
            try:
                connection.disconnect()
            except Exception:  # pylint: disable=W0718 # nosec B110
                pass  # Fehler beim Trennen sind nicht kritisch

def lies_nfc_kontinuierlich(nfc_reader):  # pylint: disable=R0912
    """
    Startet eine kontinuierliche NFC-Leseschleife für den angegebenen Reader.

    Erkennt neue Token und ruft die Funktion 'token_gefunden' auf.

    Verhindert die mehrfache Verarbeitung desselben Tokens innerhalb eines Zeitfensters,
    wenn der Token entfernt und wieder aufgelegt wird.

    Handys liefern eine zufällige UID. Deswegen wird zuerst versucht Daten per ATS zu bekommen.
    Sofern das nicht funktioniert wird die UID abgefragt.

    Fängt KeyboardInterrupt (CTRL+C) ab, um das Programm sauber zu beenden.

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """

    logger.info("Starte kontinuierliche NFC-Lesung auf Reader: %s", nfc_reader)
    last_token_time = None  # Speichert die letzte Verarbeitungszeit des Tokens

    try:
        while True:
            connection = None
            try:
                connection = nfc_reader.createConnection()
                connection.connect()
                code_disable_buzzer = [0xFF, 0x00, 0x52, 0x00, 0x00]
                connection.transmit(code_disable_buzzer)

                ats_hex = None
                uid_hex = None

                ats_hex = lese_nfc_token_ats(connection)
                if ats_hex:
                    #logger.info("ATS gefunden.")
                    last_token_time = verarbeite_token(ats_hex, last_token_time)
                else:
                    #logger.info("Kein ATS gefunden.")
                    uid_hex = lese_nfc_token_uid(connection)
                    if uid_hex:
                        #logger.info("UID gefunden.")
                        last_token_time = verarbeite_token(uid_hex, last_token_time)

                if not ats_hex and not uid_hex:
                    if last_token_time is not None:
                        last_token_time = None  # Setze Zeit zurück, wenn Token entfernt
                    time.sleep(0.2)  # Wartezeit, wenn kein Token gelesen wird

            except CardConnectionException as e:
                error_message = str(e)
                if "No smart card inserted" in error_message:
                    if last_token_time is not None:
                        last_token_time = None # Setze Zeit zurück, wenn kein Token mehr da
                    time.sleep(0.2)
                else:
                    logger.critical("Fehler bei der Tokenverbindung: %s", e)
                    time.sleep(0.2)
            except Exception:  # pylint: disable=W0718
                #logger.warning(f"Unerwarteter Fehler in der Leseschleife: {e}")
                time.sleep(0.2)
            finally:
                if connection:
                    try:
                        connection.disconnect()
                    except Exception:  # pylint: disable=W0718 # nosec B110
                        pass  # Fehler beim Trennen sind nicht kritisch

    except KeyboardInterrupt:
        logger.info("NFC-Leser wird durch Benutzer beendet.")
    finally:
        logger.info("NFC-Leser beendet.")

if __name__ == "__main__":
    if not api_url or not api_key:
        logger.critical("API_URL oder API_KEY sind nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)

    try:
        if healthcheck() is None:
            logger.critical("Healthcheck fehlgeschlagen. Beende Skript.")
            sys.exit(1)
        logger.info("API Healthcheck erfolgreich.")

        reader_list = readers()
        if not reader_list:
            logger.critical("Keine PC/SC-Reader gefunden.")
            sys.exit()
        logger.info("Verfügbare Reader: %s", reader_list)

        version = get_api_version()
        logger.info("Bereitschaft (Version %s).", version)

        ACR_READER = None
        for reader in reader_list:
            if "ACR122U" in str(reader) or "ACR1252" in str(reader):
                ACR_READER = reader
                break

        if ACR_READER:
            if disable_buzzer:
                logger.info("Deaktiviere Buzzer...")
                schalte_buzzer_ab(ACR_READER)
            # Starte Leseschleife
            lies_nfc_kontinuierlich(ACR_READER)
        else:
            logger.critical("Kein kompatibler Reader gefunden.")

    except NoReadersException as e:
        logger.critical("Fehler: %s", e)
        sys.exit(1)
    except CardConnectionException as e:
        logger.critical("Fehler bei der Tokenverbindung: %s", e)
        sys.exit(1)
    except SmartcardException as e:
        logger.critical("Ein Smartcard-Fehler ist aufgetreten: %s", e)
        sys.exit(1)
    except Exception as e:  # pylint: disable=W0718
        logger.critical("Ein unerwarteter Fehler im Hauptteil ist aufgetreten: %s", e)
        sys.exit(1)
    finally:
        logger.info("Programm beendet.")
