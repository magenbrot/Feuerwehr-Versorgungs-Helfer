"""
Dieses Skript liest kontinuierlich NFC-Token von einem ACR122U-Reader,
extrahiert die UID und sendet diese an eine konfigurierte API, um eine
Transaktion zu erstellen. Die API-URL und der API-Schlüssel werden aus
Umgebungsvariablen (.env-Datei) geladen.
"""

import time
import os
import sys
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
        else:
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
    letzte_bekannte_uid = None
    verarbeitungs_status = {}  # Speichert den Status der Verarbeitung pro UID ("verarbeitet", "nicht_gefunden", None)

    while True:
        try:
            connection = nfc_reader.createConnection()
            connection.connect()

            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)

            if sw1 == 0x90 and sw2 == 0x00:
                aktuelle_uid = toHexString(response)
                if aktuelle_uid != letzte_bekannte_uid:
                    letzte_bekannte_uid = aktuelle_uid
                    if aktuelle_uid not in verarbeitungs_status or verarbeitungs_status[aktuelle_uid] is None:
                        api_erfolgreich = token_gefunden(aktuelle_uid)
                        verarbeitungs_status[aktuelle_uid] = "verarbeitet" if api_erfolgreich else "nicht_gefunden"
                        time.sleep(2)  # Deutlich längere Wartezeit nach Verarbeitung/Fehler
                    elif verarbeitungs_status[aktuelle_uid] == "nicht_gefunden":
                        print(f"Benutzer mit UID {aktuelle_uid} weiterhin nicht gefunden.")
                        time.sleep(2)  # Längere Wartezeit, wenn Benutzer nicht gefunden
                elif aktuelle_uid == letzte_bekannte_uid and letzte_bekannte_uid is not None:
                    if verarbeitungs_status.get(aktuelle_uid) == "verarbeitet":
                        time.sleep(2)  # Längere Wartezeit, wenn Token bekannt und verarbeitet
                    elif verarbeitungs_status.get(aktuelle_uid) == "nicht_gefunden":
                        time.sleep(2)  # Längere Wartezeit, wenn Token bekannt und nicht gefunden
                    else:
                        time.sleep(0.5) # Etwas längere Wartezeit, falls Status unbekannt
            else:
                letzte_bekannte_uid = None
                verarbeitungs_status = {}  # Reset Status, wenn keine Karte erkannt
                time.sleep(1)

            connection.disconnect()

        except Exception as e:
            error_message = str(e)
            if "Card was reset" in error_message or "Card protocol mismatch" in error_message:
                print(f"NFC-Kartenfehler erkannt: '{error_message}'. Ignoriere.")
                time.sleep(1)
            elif "No smart card inserted" in error_message:
                letzte_bekannte_uid = None
                verarbeitungs_status = {}
                time.sleep(1)
            else:
                letzte_bekannte_uid = None
                verarbeitungs_status = {}
                time.sleep(1)
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
            exit(1)

        reader_list = readers()
        if not reader_list:
            print("Keine PC/SC-Reader gefunden.")
            exit()

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
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
