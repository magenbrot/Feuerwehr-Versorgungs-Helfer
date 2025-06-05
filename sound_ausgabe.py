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

def _play_sound_effect(sound_datei_name):
    """
    Plays a sound effect if specified and found.
    Args:
        sound_datei_name (str): The name of the sound file (e.g., "alarm") or full filename (e.g., "alarm.mp3").
    Returns:
        bool: True if sound played or no sound was specified, False if sound file not found.
    """
    if not sound_datei_name:
        return True # No sound effect requested

    base_path = "static/sounds/"
    # Construct the full path, ensuring .mp3 extension
    if not sound_datei_name.endswith(".mp3"):
        full_sound_path = os.path.join(base_path, sound_datei_name + ".mp3")
    else:
        full_sound_path = os.path.join(base_path, sound_datei_name)

    if os.path.exists(full_sound_path):
        try:
            effekt = pygame.mixer.Sound(full_sound_path)
            logging.info("Playing sound effect: %s", full_sound_path)
            effekt.play()
            # Wait for the sound effect to finish before proceeding
            time.sleep(effekt.get_length())
            return True
        except pygame.error as e: # pylint: disable=no-member
            logging.error("Pygame error playing sound effect '%s': %s", full_sound_path, e)
            return False # Indicate failure to play sound
    else:
        logging.warning("Sound effect file not found: %s", full_sound_path)
        # Optionally, raise FileNotFoundError if this should halt execution
        # raise FileNotFoundError(f"Die Sounddatei '{full_sound_path}' wurde nicht gefunden.")
        return False # Indicate sound file not found

def _cleanup_tts_resources(filename="output.mp3"):
    """
    Stops the pygame mixer if it's initialized and removes the TTS output file.
    Args:
        filename (str): The name of the temporary TTS file to remove.
    """
    if pygame.mixer.get_init():
        try:
            # Ensure music is stopped before quitting mixer
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.quit()
            logging.info("Pygame mixer quit.")
        except pygame.error as e: # pylint: disable=no-member
            logging.error("Error quitting pygame mixer: %s", e)


    if os.path.exists(filename):
        try:
            os.remove(filename)
            logging.info("Removed temporary TTS file: %s", filename)
        except OSError as e:
            logging.error("Error deleting temporary TTS file '%s': %s", filename, e)

def sprich_text(sound_datei=None, text="Hier ist was kaputt!", sprache='de', slow=False):
    """
    Synthetisiert den gegebenen Text in Sprache und spielt ihn über Pygame ab.

    Args:
        sound_datei (str, optional): Name of the sound file (e.g., "alarm") to play before speech.
        text (str): Der Text, der gesprochen werden soll.
        sprache (str, optional): Sprachcode (z.B. 'de'). Standard: 'de'.
        slow (bool, optional): Wenn True, wird der Text langsamer gesprochen. Standard: False.
    """
    temp_tts_filename = "output.mp3"
    # Ensure mixer is initialized at the start of the core logic
    # This also helps in making _cleanup_tts_resources more reliable
    # as it can check pygame.mixer.get_init()
    if not pygame.mixer.get_init():
        try:
            _initialize_mixer()
        except pygame.error: # pylint: disable=no-member
             # If mixer fails to init, we can't play sounds. Log and exit or handle.
            logging.error("Cannot proceed without pygame mixer.")
            return # Or raise an error

    try:
        # Generate TTS
        logging.info("Generating TTS for text: '%s'", text)
        tts = gTTS(text=text, lang=sprache, slow=slow)
        tts.save(temp_tts_filename)
        logging.info("TTS saved to %s", temp_tts_filename)

        # Play optional sound effect
        # If _play_sound_effect returns False (e.g. file not found), we might choose to continue or stop
        # For now, it logs a warning and continues with TTS playback.
        _play_sound_effect(sound_datei)

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
