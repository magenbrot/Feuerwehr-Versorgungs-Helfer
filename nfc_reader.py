"""
Diese App liest kontinuierlich NFC-Token von einem ACR122U-Reader,
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
import requests
from smartcard.Exceptions import NoCardException, CardConnectionException, SmartcardException, NoReadersException
from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.CardConnection import CardConnection
from smartcard.CardMonitoring import CardMonitor, CardObserver
import sound_ausgabe
import config
import api_client

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
logger = logging.getLogger(__name__)


class NFCCardObserver(CardObserver):  # pylint: disable=too-few-public-methods
    """
    Observer-Klasse zur Überwachung von Karten-Ereignissen auf dem NFC-Reader.
    Reagiert auf das Auflegen und Entfernen von Token.
    """

    def __init__(self, target_reader):
        self.target_reader = target_reader
        self.last_token_time = None

    def update(self, observable, handlers):
        (addedcards, removedcards) = handlers

        # 1. Wenn eine Karte entfernt wird
        for card in removedcards:
            self._handle_removed_card(card)

        # 2. Wenn eine Karte aufgelegt wird
        for card in addedcards:
            self._handle_added_card(card)

    def _handle_removed_card(self, card):
        if card.reader == self.target_reader.name:
            logger.info("Token entfernt.")
            self.last_token_time = None

    def _handle_added_card(self, card):
        if card.reader != self.target_reader.name:
            return

        connection = None
        try:
            connection = card.createConnection()
            # Bevorzuge T=1 Protokoll für schnellere Verbindung
            connection.connect(CardConnection.T1_protocol)

            token_hex = self._determine_token_hex(connection)

            if token_hex:
                self.last_token_time = verarbeite_token(token_hex, self.last_token_time)

        except CardConnectionException as e:
            logger.debug("Verbindungsfehler beim Auflegen des Tokens: %s", e)
        except Exception as e:  # pylint: disable=W0718
            logger.error("Fehler beim Verarbeiten des aufgelegten Tokens: %s", e)
        finally:
            if connection:
                try:
                    connection.disconnect()
                except Exception:  # pylint: disable=W0718
                    pass

    def _determine_token_hex(self, connection):
        """
        Ermittelt den NFC-Token-Hexwert (bevorzugt UID, oder ATS bei Zufalls-UIDs/Fallback).
        """
        # 1. Zuerst UID prüfen (Schnelle Abfrage für reguläre Karten)
        uid_hex = lese_nfc_token_uid(connection)
        if not uid_hex:
            # Fallback falls UID nicht lesbar war, aber ATS existiert
            return lese_nfc_token_ats(connection)

        uid_clean = uid_hex.replace(" ", "")
        # Wenn die UID mit "08" beginnt (Zufalls-UID z.B. bei Handys),
        # versuchen wir die stabilere ATS auszulesen
        if uid_clean.startswith("08"):
            ats_hex = lese_nfc_token_ats(connection)
            return ats_hex if ats_hex else uid_hex
        return uid_hex


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
    response = None

    try:
        # 1. Token vorbereiten und validieren
        token_hex_sauber = token_hex.replace(" ", "")
        token_bytes = binascii.unhexlify(token_hex_sauber)
        token_base64 = base64.b64encode(token_bytes).decode('utf-8')

        # 2. API-Anfrage senden und auf HTTP-Fehler prüfen
        logger.info("Sende NFC-Token %s an die API...", token_hex_sauber)
        response = api_client.nfc_transaktion_erstellen(token_base64, config.MY_NAME)
        if response is None:
            sound_ausgabe.sprich_text("error", "API-Fehler, bitte informiere einen Administrator.", sprache="de")
            return False
        response.raise_for_status()  # Löst bei 4xx/5xx eine Exception aus

        # 3. Erfolgreiche Antwort (2xx) verarbeiten
        antwort_json = response.json()
        nachricht = antwort_json.get('message', 'Aktion erfolgreich.')

        if antwort_json.get('action') == 'block':
            sound_ausgabe.sprich_text("blocked", nachricht, sprache="de")
        else:
            if int(antwort_json.get('saldo')) == 0:
                sound_ausgabe.sprich_text("zero_balance", nachricht, sprache="de")
            else:
                sound_ausgabe.sprich_text("success", nachricht, sprache="de")
            sound_ausgabe.play_sound_effect("transaction_end")
        erfolgreich = True

    except requests.exceptions.RequestException as e:
        # Gezielte Fehlerbehandlung für HTTP-Statuscodes
        if response is not None and response.status_code == 404:
            fehler_nachricht = response.json().get('error', 'Dieser Token wurde noch nicht registriert. Die Administratoren wurden per E-Mail informiert.')
            logger.warning("Token %s nicht registriert (404): %s", token_hex_sauber, fehler_nachricht)
            sound_ausgabe.sprich_text("error", fehler_nachricht, sprache="de")
        elif response is not None and response.status_code == 403:
            fehler_nachricht = response.json().get('error', 'Benutzer gesperrt.')
            logger.warning("Benutzer ist gesperrt (403): %s", fehler_nachricht)
            sound_ausgabe.sprich_text("locked", fehler_nachricht, sprache="de")
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

    if last_token_time is None or jetzt - last_token_time >= config.TOKEN_DELAY:
        # beep sound wenn Token gescannt wurde
        sound_ausgabe.play_sound_effect("scan")
        transaktion_erfolgreich = person_transaktion_erstellen(token_hex)
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


def lies_nfc_kontinuierlich(nfc_reader):
    """
    Startet eine kontinuierliche, eventbasierte NFC-Lesung.

    Args:
        nfc_reader (smartcard.pcsc.PCSCReader): Das Reader-Objekt, das für die NFC-Kommunikation verwendet wird.
    """

    logger.info("Starte kontinuierliche NFC-Lesung auf Reader: %s", nfc_reader)

    # Observer und Monitor initialisieren und registrieren
    observer = NFCCardObserver(nfc_reader)
    monitor = CardMonitor()
    monitor.addObserver(observer)

    try:
        # Halteschleife, um den Hauptthread am Leben zu erhalten
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("NFC-Leser wird durch Benutzer beendet.")
    finally:
        monitor.removeObserver(observer)
        logger.info("NFC-Leser beendet.")


if __name__ == "__main__":
    config.validate_config()

    try:
        if api_client.healthcheck() is None:
            logger.critical("Healthcheck fehlgeschlagen. Beende Skript.")
            sys.exit(1)
        logger.info("API Healthcheck erfolgreich.")

        reader_list = readers()
        if not reader_list:
            logger.critical("Keine PC/SC-Reader gefunden.")
            sys.exit()
        logger.info("Verfügbare Reader: %s", reader_list)

        version = api_client.get_api_version()
        logger.info("Bereitschaft (Version %s).", version)

        acr_reader = None  # pylint: disable=C0103
        for reader in reader_list:
            if "ACR122U" in str(reader) or "ACR1252" in str(reader):
                acr_reader = reader
                break

        if acr_reader:
            if config.DISABLE_BUZZER:
                logger.info("Deaktiviere Buzzer...")
                schalte_buzzer_ab(acr_reader)
            # Starte Leseschleife
            lies_nfc_kontinuierlich(acr_reader)
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
