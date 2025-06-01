"""Personen aus CSV lesen und in der Datenbank anlegen"""

import csv
import os
import sys
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import handle_requests as hr

load_dotenv()
api_url = os.environ.get("API_URL")
api_key = os.environ.get("API_KEY")
default_password = os.environ.get("DEFAULT_PASSWORD")

def healthcheck():
    """
    Healthcheck gegen API ausführen.

    Args:
        headers (dict, optional): Ein Dictionary mit zu sendenden Request-Headern.
                                    Falls nicht angegeben, werden die Standard-Header verwendet.
                                    Defaults to None.

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

def person_einfuegen(person_code, person_nachname, person_vorname):
    """
    Eine neue Person in die Datenbank einfügen.

    Args:
        person_code (str): Der Code der einzufügenden Person.
        person_name (str): Der Name der einzufügenden Person.
    """

    post_url = f"{api_url}/person"
    post_headers = {
        'X-API-Key': api_key
    }

    post_daten = {
        'code': person_code,
        'nachname': person_nachname,
        'vorname': person_vorname
    }

    # Erzeuge den Hash des Standardpassworts
    try:
        hashed_password = generate_password_hash(default_password)
    except Exception as e: # pylint: disable=W0718
        print(f"FEHLER: Konnte Passwort-Hash nicht erzeugen: {e}")
        return

    post_daten = {
        'code': person_code,
        'nachname': person_nachname,
        'vorname': person_vorname,
        'password': hashed_password  # Füge das gehashte Passwort hinzu
    }

    #print(f"POST-URL: {post_url}, POST-Headers: {post_headers}, POST-Daten: {post_daten}")
    post_response = hr.post_request(post_url, post_headers, post_daten)
    if post_response:
        # print("POST Response Body:")
        # print(post_response.json())
        print(
            f"\nDatensatz für '{person_nachname} {person_vorname}' wurde hinzugefügt.")

def person_existent(person_code):
    """
    Prüft, ob eine Person bereits in der Datenbank angelegt wurde.

    Args:
        person_code (str): Der Code der Person.

    Returns:
        True or False, wenn die Person existiert oder None bei Fehler.
    """

    get_url = f"{api_url}/person/existent/{person_code}"

    get_headers = {
        'X-API-Key': api_key
    }

    get_response = hr.get_request(get_url, get_headers)

    #print(f"GET-URL: {get_url}, GET-Headers: {get_headers}, GET-Response: {get_response}")
    person_daten = get_response.json()
    if None in person_daten:
        print("Fehler beim Abrufen der Personendaten.")
        return None  # Oder eine andere Fehlerbehandlung, z.B. eine Exception werfen
    if not 'error' in person_daten:
        return True
    return False

def exit_gracefully():
    """
    Räumt auf und beendet das Programm ordentlich.
    """

    print('Räume auf und beende das Programm ordentlich.')
    sys.exit(0)

if __name__ == "__main__":
    if not api_url:
        print("Fehler: API_URL ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)
    if not api_key:
        print("Fehler: API_KEY ist nicht in den Umgebungsvariablen definiert.")
        sys.exit(1)

    CSV_PERSONEN = "mitglieder.csv"

    try:
        # Erstelle den Ausgabeordner, falls er nicht existiert
        healthcheck()
        with open(CSV_PERSONEN, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 2:  # Es sollte Code und Nachname Vorname in der Datei stehen
                    # Nimm den ersten Eintrag (den 10-stelligen Code) und entferne Leerzeichen
                    code = row[0].strip()
                    nachname = row[1].strip()
                    vorname = row[2].strip()
                    # Überprüfe, ob es ein 10-stelliger Zahlencode ist
                    if len(code) == 10 and code.isdigit():
                        # Prüfe, ob die Person bereits angelegt wurde
                        if not person_existent(code):
                            # Speichere Person in Datenbank
                            person_einfuegen(code, nachname, vorname)
                        else:
                            print(f"Code {code} ({nachname} {vorname}) existiert bereits in der Datenbank.")
                    else:
                        print(
                            f"Zeile '{row}' in der CSV-Datei enthält keinen gültigen 10-stelligen Zahlencode.")
                else:
                    print(f"Ungültige Zeile in der CSV-Datei: '{row}'.")

    except FileNotFoundError:
        print(f"Fehler: Die CSV-Datei '{CSV_PERSONEN}' wurde nicht gefunden.")
    except ImportError as e:
        print(f"Ein Importfehler ist aufgetreten: {e}.")
    except IOError as e:
        print(f"Ein Fehler beim Lesen der CSV-Datei ist aufgetreten: {e}.")
    except KeyboardInterrupt:
        pass
    except Exception as e: # pylint: disable=W0718
        print(f"Es ist ein allgemeiner Fehler aufgetreten: {e}")
    finally:
        exit_gracefully()
