"""Zentraler API-Client für den Feuerwehr-Versorgungs-Helfer."""

import logging
import handle_requests as hr
import config

logger = logging.getLogger(__name__)


def healthcheck():
    """
    Healthcheck gegen API ausführen.

    Returns:
        dict or None: Die JSON-Antwort des Healthcheck-Endpunktes oder None bei einem Fehler.
    """
    get_url = f"{config.API_URL}/health-protected"
    get_headers = {
        'X-API-Key': config.API_KEY
    }

    get_response = hr.get_request(get_url, get_headers)
    if get_response:
        return get_response.json()
    return None


def get_api_version():
    """
    API nach aktueller Version fragen.

    Returns:
        str or None: Die Versionsnummer oder None bei einem Fehler.
    """
    get_url = f"{config.API_URL}/version"
    get_headers = {
        'X-API-Key': config.API_KEY
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
    get_url = f"{config.API_URL}/saldo-alle"
    get_headers = {
        'X-API-Key': config.API_KEY
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
    get_url = f"{config.API_URL}/person/{code}"
    get_headers = {
        'X-API-Key': config.API_KEY
    }

    get_response = hr.get_request(get_url, get_headers)
    if get_response is None:
        return None

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
    put_url = f"{config.API_URL}/person/{code}/transaktion"
    put_headers = {
        'X-API-Key': config.API_KEY
    }
    put_daten = {
        'beschreibung': beschreibung,
    }

    put_response = hr.put_request(put_url, put_headers, put_daten)
    if put_response is not None:
        return put_response
    return None


def nfc_transaktion_erstellen(token_base64, beschreibung):
    """
    Transaktion für ein NFC-Token ausführen.

    Args:
        token_base64 (str): Der base64-kodierte Token.
        beschreibung (str): Die Beschreibung der Buchung.

    Returns:
        requests.Response or None: Das Response-Objekt oder None bei einem Fehler.
    """
    put_url = f"{config.API_URL}/nfc-transaktion"
    put_headers = {
        'X-API-Key': config.API_KEY
    }
    put_daten = {
        'token': token_base64,
        'beschreibung': beschreibung,
    }

    put_response = hr.put_request(put_url, put_headers, put_daten)
    if put_response is not None:
        return put_response
    return None
