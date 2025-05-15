"""
Dieses Skript liest kontinuierlich NFC-Token von einem ACR122U-Reader,
extrahiert die UID und sendet diese an eine konfigurierte API, um eine
Transaktion zu erstellen. Die API-URL und der API-Schlüssel werden aus
Umgebungsvariablen (.env-Datei) geladen.
"""

import base64
import binascii
import time
import os
import sys
from smartcard.Exceptions import CardConnectionException, SmartcardException, NoReadersException
from smartcard.System import readers
from smartcard.util import toHexString
from dotenv import load_dotenv
import handle_requests as hr

load_dotenv()
api_url = os.environ.get("API_URL")
api_key = os.environ.get("API_KEY")
token_delay = int(os.environ.get("TOKEN_DELAY"))


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


def token_gefunden(uid_hex):
    """
    Wird aufgerufen, wenn ein NFC-Token erkannt wurde. Sendet die UID als Bytes an die API.

    Args:
        uid_hex (str): Die eindeutige ID (UID) des erkannten NFC-Tokens als Hex-String.

    Returns:
        bool: True, wenn die API-Anfrage erfolgreich war (Statuscode 2xx), False bei anderen Fehlern.
    """

    put_url = f"{api_url}/nfc-transaction"
    put_headers = {
        'X-API-Key': api_key
    }

    try:
        # Entferne die Leerzeichen aus dem Hex-String
        uid_hex_ohne_leerzeichen = uid_hex.replace(" ", "")
        uid_bytes = binascii.unhexlify(uid_hex_ohne_leerzeichen)
        uid_base64 = base64.b64encode(uid_bytes).decode('utf-8')
        put_daten = {
            'uid': uid_base64,
        }

        print(f"NFC-Token mit UID {uid_hex} ({uid_hex_ohne_leerzeichen}) erkannt! Sende an API...")
        response = hr.put_request(put_url, put_headers, put_daten)
        response.raise_for_status()
        print(f"API-Antwort: {response.json()}")
        return True
    except hr.requests.exceptions.RequestException as e:
        if response is not None and response.status_code == 404:
            print(f"Benutzer mit UID {uid_hex} nicht gefunden (404).")
            return False  # API-Anfrage fehlgeschlagen, Benutzer nicht gefunden
        print(f"Fehler beim Senden der UID an die API: {e}")
        return False  # Andere API-Fehler
    except binascii.Error:
        print(f"Fehler: Ungültiger Hexadezimalstring: {uid_hex}")
        return False


def lese_karte(connection):
    """
    Liest die UID von der Karte.

    Args:
        connection: Die Kartenverbindung.

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
        print(f"Fehler beim Lesen der Karte: {e}")
        return None


def verarbeite_uid(uid_hex, last_uid_time):
    """
    Verarbeitet die gelesene UID.

    Args:
        uid_hex: Die gelesene UID.
        last_uid_time:  Zeitpunkt der letzten erfolgreichen Verarbeitung der UID.

    Returns:
        float: Aktualisierte letzte Verarbeitungszeit oder None.
    """

    jetzt = time.time()

    if last_uid_time is None or jetzt - last_uid_time >= token_delay:
        api_erfolgreich = token_gefunden(uid_hex)
        if api_erfolgreich:
            return jetzt  # Aktualisiere den Zeitstempel
        return None
    print(f"Token {uid_hex} wurde kürzlich verarbeitet. Ignoriere.")
    return last_uid_time


def schalte_buzzer_ab(nfc_reader):
    """
    Schaltet den Hardware-Buzzer ab

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """

    connection = None
    try:
        connection = nfc_reader.createConnection()
        connection.connect()
        code_disable_buzzer = [0xFF, 0x00, 0x52, 0x00, 0x00]
        connection.transmit(code_disable_buzzer)

        # Überprüfe Status Code 90 00h für Erfolg
        if sw1 == 0x90 and sw2 == 0x00:
            print("Buzzer erfolgreich ausgeschaltet (Status Code 90 00h).")
        else:
            print(f"Kommando nicht erfolgreich. Status Code: {sw1:02X} {sw2:02X}")
            # Laut API Doku (Seite 9/Anhang A) bedeuten andere SWs Fehler
            if sw1 == 0x63 and sw2 == 0x00:
                print("Laut API-Dokumentation: Operation fehlgeschlagen (Status Code 63 00h).")
            # Hier könnten Sie weitere spezifische Fehlercodes aus Appendix A prüfen
    except CardConnectionException as e:
        error_message = str(e)
        if "No smart card inserted" in error_message:
            if last_uid_time is not None:
                last_uid_time = None # Setze Zeit zurück, wenn keine Karte mehr da
            time.sleep(0.2)
        else:
            print(f"Fehler bei der Kartenverbindung: {e}")
            time.sleep(0.2)
    except Exception:  # pylint: disable=W0718
        #print(f"Unerwarteter Fehler in der Leseschleife: {e}")
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

    Erkennt neue UIDs und ruft die Funktion 'token_gefunden' auf.
    Verhindert die mehrfache Verarbeitung derselben UID innerhalb eines Zeitfensters,
    wenn der Token entfernt und wieder aufgelegt wird.
    Fängt KeyboardInterrupt (CTRL+C) ab, um das Programm sauber zu beenden.

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """
    print(f"Starte kontinuierliche NFC-Lesung auf Reader: {nfc_reader}")
    last_uid_time = None  # Speichert die letzte Verarbeitungszeit der UID

    try:
        while True:
            connection = None
            try:
                connection = nfc_reader.createConnection()
                connection.connect()
                code_disable_buzzer = [0xFF, 0x00, 0x52, 0x00, 0x00]
                connection.transmit(code_disable_buzzer)

                uid_hex = lese_karte(connection)
                if uid_hex:
                    last_uid_time = verarbeite_uid(uid_hex, last_uid_time)
                else:
                    if last_uid_time is not None:
                        last_uid_time = None  # Setze Zeit zurück, wenn Token entfernt
                    time.sleep(0.2)  # Wartezeit, wenn keine UID gelesen wird

            except CardConnectionException as e:
                error_message = str(e)
                if "No smart card inserted" in error_message:
                    if last_uid_time is not None:
                        last_uid_time = None # Setze Zeit zurück, wenn keine Karte mehr da
                    time.sleep(0.2)
                else:
                    print(f"Fehler bei der Kartenverbindung: {e}")
                    time.sleep(0.2)
            except Exception:  # pylint: disable=W0718
                #print(f"Unerwarteter Fehler in der Leseschleife: {e}")
                time.sleep(0.2)
            finally:
                if connection:
                    try:
                        connection.disconnect()
                    except Exception:  # pylint: disable=W0718 # nosec B110
                        pass  # Fehler beim Trennen sind nicht kritisch

    except KeyboardInterrupt:
        print("\nNFC-Reader wird beendet.")
    finally:
        print("NFC-Reader beendet.")


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
            schalte_buzzer_ab(ACR122U_READER)
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
    except Exception as e:  # pylint: disable=W0718
        print(f"Ein unerwarteter Fehler im Hauptteil des Skripts ist aufgetreten: {e}")
        sys.exit(1)
