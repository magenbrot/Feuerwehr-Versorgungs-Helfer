"""
Dieses Skript liest kontinuierlich NFC-Token von einem ACR122U-Reader,
extrahiert die UID und sendet diese an eine konfigurierte API, um eine
Transaktion zu erstellen. Die API-URL und der API-Schlüssel werden aus
Umgebungsvariablen (.env-Datei) geladen.
"""

import time
import os
import sys
from smartcard.Exceptions import CardConnectionException, SmartcardException, NoReadersException
from smartcard.System import readers
from smartcard.util import toHexString
from dotenv import load_dotenv
import handle_requests as hr


load_dotenv()
api_url=os.environ.get("API_URL")
api_key=os.environ.get("API_KEY")


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


def token_gefunden(uid):
    """
    Wird aufgerufen, wenn ein NFC-Token erkannt wurde. Sendet die UID an die API.

    Args:
        uid (str): Die eindeutige ID (UID) des erkannten NFC-Tokens als Hex-String.

    Returns:
        bool: True, wenn die API-Anfrage erfolgreich war (Statuscode 2xx), False bei anderen Fehlern.
    """

    print(f"NFC-Token mit UID {uid} erkannt! Sende an API...")

    put_url = f"{api_url}/nfc-transaction"
    put_headers = {
        'X-API-Key': api_key
    }

    put_daten = {
        'uid': uid,
    }

    try:
        response = hr.put_request(put_url, put_headers, put_daten)
        response.raise_for_status()
        print(f"API-Antwort: {response.json()}")
        return True
    except hr.requests.exceptions.RequestException as e:
        if response is not None and response.status_code == 404:
            print(f"Benutzer mit UID {uid} nicht gefunden (404).")
            return False  # API-Anfrage fehlgeschlagen, Benutzer nicht gefunden
        print(f"Fehler beim Senden der UID an die API: {e}")
        return False  # Andere API-Fehler


def lies_nfc_kontinuierlich(nfc_reader):
    """
    Startet eine kontinuierliche NFC-Leseschleife für den angegebenen Reader.

    Erkennt neue UIDs und ruft die Funktion 'token_gefunden' auf.
    Verhindert die mehrfache Verarbeitung derselben UID, bis das Token entfernt wird,
    insbesondere wenn die API mit einem 404 (Benutzer nicht gefunden) antwortet.
    Implementiert eine verlängerte Wartezeit nach erfolgreicher Verarbeitung.

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """
    print(f"Starte kontinuierliche NFC-Lesung auf Reader: {nfc_reader}")
    last_uid = None
    aktuell_verarbeitete_uid = None

    while True:
        try:
            connection = nfc_reader.createConnection()
            connection.connect()

            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)

            if sw1 == 0x90 and sw2 == 0x00:
                uid = toHexString(response)
                if uid not in (last_uid, aktuell_verarbeitete_uid):
                    api_erfolgreich = token_gefunden(uid)
                    if not api_erfolgreich:
                        aktuell_verarbeitete_uid = uid
                    last_uid = uid
                elif uid == aktuell_verarbeitete_uid and uid != last_uid:
                    # Token wurde möglicherweise entfernt und wieder aufgelegt
                    aktuell_verarbeitete_uid = None
                    last_uid = None # Zurücksetzen, um erneute Verarbeitung zu ermöglichen
                elif uid == last_uid:
                    time.sleep(0.1) # Kurze Wartezeit, wenn UID gleich bleibt
            else:
                last_uid = None
                aktuell_verarbeitete_uid = None
                time.sleep(0.2)

            connection.disconnect()

        except Exception as e: # pylint: disable=W0718
            error_message = str(e)
            if "Card was reset" in error_message or "Card protocol mismatch" in error_message or "Card is unpowered" in error_message:
                print(f"NFC-Kartenfehler erkannt: '{error_message}'. Ignoriere.")
                time.sleep(0.5)
            elif "No smart card inserted" in error_message:
                last_uid = None
                aktuell_verarbeitete_uid = None
                time.sleep(0.2)
            else:
                last_uid = None
                aktuell_verarbeitete_uid = None
                time.sleep(0.2)
                print(f"Ein Fehler ist aufgetreten: {e}")


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

        reader_list = readers()
        if not reader_list:
            print("Keine PC/SC-Reader gefunden.")
            sys.exit()

        print("Verfügbare Reader:")
        for i, reader in enumerate(reader_list):
            print(f"[{i}] {reader}")

        ACR122U_READER = None
        for reader in reader_list:
            if "ACR122U" in str(reader):
                ACR122U_READER = reader
                break

        if ACR122U_READER:
            lies_nfc_kontinuierlich(ACR122U_READER)
        else:
            print("ACR122U Reader nicht gefunden.")

    except ImportError:
        print("Das Modul 'pyscard' ist nicht installiert.")
    except NoReadersException as e:
        print(f"{e}")
        sys.exit(1)
    except CardConnectionException as e:
        print(f"Fehler bei der Kartenverbindung: {e}")
        sys.exit(1)
    except SmartcardException as e:
        print(f"Smartcard-Fehler ist aufgetreten: {e}")
        sys.exit(1)
    except Exception as e: # pylint: disable=W0718
        print(f"Ein unerwarteter Fehler im Hauptteil des Skripts ist aufgetreten: {e}")
        sys.exit(1)
