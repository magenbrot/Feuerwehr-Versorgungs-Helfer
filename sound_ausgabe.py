""" Test App für Sprachsynthese mit Pygame und gTTS """

import os
import logging
import time
import sys
import pygame
from gtts import gTTS
from gtts.tts import gTTSError

# Logger konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def _initialize_mixer():
    """Initializes pygame.mixer if not already initialized."""

    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
            logging.info("Pygame mixer initialized.")
        except pygame.error as e: # pylint: disable=no-member
            logging.error("Failed to initialize pygame mixer: %s", e)
            raise  # Re-raise the exception to be caught by the main function

def play_sound_effect(sound_datei_name: str | None) -> bool:
    """
    Spielt einen Soundeffekt ab, falls angegeben und gefunden.

    Args:
        sound_datei_name (str | None): Der Name der Sounddatei (z. B. "alarm")
                                       oder None.

    Returns:
        bool: True, wenn kein Sound angefordert oder der Sound erfolgreich
              abgespielt wurde. False, bei einem Fehler oder wenn die Datei
              nicht gefunden wurde.
    """

    if not sound_datei_name:
        return True

    if not pygame.mixer.get_init():
        try:
            _initialize_mixer()
        except pygame.error:  # pylint: disable=no-member
            logging.error("Pygame-Mixer konnte nicht initialisiert werden.")
            return False

    try:
        base_path = "static/sounds/"
        sound_file = f"{sound_datei_name}.mp3" if not sound_datei_name.endswith(".mp3") else sound_datei_name
        full_sound_path = os.path.join(base_path, sound_file)

        if not os.path.exists(full_sound_path):
            logging.warning("Sound-Datei nicht gefunden: %s", full_sound_path)
            return False

        effekt = pygame.mixer.Sound(full_sound_path)
        logging.info("Spiele Soundeffekt ab: %s", full_sound_path)
        effekt.play()
        time.sleep(effekt.get_length())  # Warten, bis der Sound zu Ende ist
        return True

    except pygame.error as e:  # pylint: disable=no-member
        logging.error("Pygame-Fehler beim Abspielen des Sounds '%s': %s", full_sound_path, e)
        return False  # Fehler explizit zurückgeben

    except Exception as e:  # pylint: disable=W0718
        logging.error("Unerwarteter Fehler in play_sound_effect: %s", e, exc_info=True)
        return False  # Fehler explizit zurückgeben

def _cleanup_tts_resources(filename: str | None = None) -> None:
    """
    Stoppt den Pygame-Mixer und entfernt optional die TTS-Ausgabedatei.

    Args:
        filename (str, optional): Der Name der temporären TTS-Datei, die entfernt
                                  werden soll. Wenn None, wird keine Datei
                                  entfernt. Standard ist None.
    """

    # pylint: disable=no-member
    if pygame.mixer.get_init():
        try:
            # Stellt sicher, dass die Musik gestoppt ist, bevor der Mixer beendet wird
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.quit()
            logging.info("Pygame-Mixer wurde beendet.")
        except pygame.error as e:
            logging.error("Fehler beim Beenden des Pygame-Mixers: %s", e)

    # Datei nur entfernen, wenn ein Dateiname angegeben wurde und existiert
    if filename and os.path.exists(filename):
        try:
            os.remove(filename)
            logging.info("Temporäre TTS-Datei entfernt: %s", filename)
        except OSError as e:
            logging.error("Fehler beim Löschen der temporären TTS-Datei '%s': %s", filename, e)

def sprich_text(sound_datei=None, text="Hier ist was kaputt!", sprache='de', slow=False):
    """
    Synthetisiert den übergebenen Text in Sprache und spielt ihn über Pygame ab.

    Args:
        sound_datei (str, optional): Name of the sound file (e.g., "alarm") to play before speech.
        text (str): Der Text, der gesprochen werden soll.
        sprache (str, optional): Sprachcode (z.B. 'de'). Standard: 'de'.
        slow (bool, optional): Wenn True, wird der Text langsamer gesprochen. Standard: False.
    """

    temp_tts_filename = "output.mp3"

    try:
        # Generate TTS
        logging.info("Generating TTS for text: '%s'", text)
        tts = gTTS(text=text, lang=sprache, slow=slow)
        tts.save(temp_tts_filename)
        logging.info("TTS saved to %s", temp_tts_filename)

        # Play optional sound effect
        # If play_sound_effect returns False (e.g. file not found), we might choose to continue or stop
        # For now, it logs a warning and continues with TTS playback.
        play_sound_effect(sound_datei)

        if not pygame.mixer.get_init():
            try:
                _initialize_mixer()
            except pygame.error: # pylint: disable=no-member
                # If mixer fails to init, we can't play sounds. Log and exit or handle.
                logging.error("Cannot proceed without pygame mixer.")
                return  # Or raise an error

        # Play the generated speech
        pygame.mixer.music.load(temp_tts_filename)
        logging.info("Playing TTS: %s", temp_tts_filename)
        pygame.mixer.music.play()

        # Wait for speech to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        logging.info("TTS playback finished.")

    except gTTSError as e:
        logging.error("gTTS Error: %s", e)
    except pygame.error as e: # pylint: disable=no-member
        # This will catch errors from mixer.init, music.load, music.play
        logging.error("Pygame Error during TTS playback: %s", e)
    except IOError as e:
        # This could be from tts.save()
        logging.error("IO Error (e.g., saving TTS file '%s'): %s", temp_tts_filename, e)
    except Exception as e:  # pylint: disable=W0718
        logging.error("An unexpected error occurred in sprich_text: %s", e, exc_info=True)
    finally:
        # Cleanup resources regardless of success or failure
        _cleanup_tts_resources(temp_tts_filename)

if __name__ == "__main__":
    sprich_text("alarm", "Du hast kein Guthaben mehr, stell das Getränk zurück in den Schrank!", sprache="de")
    sprich_text("badumtss", "Dein Guthaben ist jetzt auf 0 €!", sprache="de")
    sprich_text("mario-victory", "Hat geklappt, lass es dir schmecken!", sprache="de")
