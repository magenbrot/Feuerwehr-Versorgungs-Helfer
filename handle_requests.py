"""Definiert gemeinsam genutzte Funktionen für HTTP-Anfragen."""

import requests


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
        response = requests.delete(url, headers=headers, timeout=10)
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
        response = requests.get(url, headers=headers, params=params, timeout=10)
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
                                 json=json_data, timeout=10)
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
                                json=json_data, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim PUT-Request: {e}.")
        return response
