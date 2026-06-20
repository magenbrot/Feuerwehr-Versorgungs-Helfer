"""Zentrale Konfigurationsdatei für den Feuerwehr-Versorgungs-Helfer."""

import os
import sys
import logging
from dotenv import load_dotenv

# Umgebungsvariablen laden
load_dotenv()

# API-Einstellungen
API_URL = os.environ.get("API_URL")
API_KEY = os.environ.get("API_KEY")

# Allgemeine Einstellungen
MY_NAME = os.environ.get("MY_NAME", "give me a name")
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Reader-spezifische Einstellungen
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "-1"))
TOKEN_DELAY = int(os.environ.get("TOKEN_DELAY", "3"))
DISABLE_BUZZER = os.getenv('DISABLE_BUZZER', 'False') == 'True'

# Sound-Konfigurationen
SOUND_CONFIG = {
    "scan": os.getenv("SOUND_SCAN", "beep1"),
    "success": os.getenv("SOUND_SUCCESS", "plopp1"),
    "zero_balance": os.getenv("SOUND_ZERO_BALANCE", "badumtss"),
    "blocked": os.getenv("SOUND_BLOCKED", "wah-wah"),
    "locked": os.getenv("SOUND_LOCKED", "error"),
    "info": os.getenv("SOUND_INFO", "tagesschau"),
    "error": os.getenv("SOUND_ERROR", "error"),
    "transaction_end": os.getenv("SOUND_TRANSACTION_END", "none"),
}

TTS_VOICE = os.getenv("TTS_VOICE", "de-DE-KillianNeural")

# Logging-Konfiguration initialisieren
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def validate_config():
    """Validiert, ob alle notwendigen API-Einstellungen vorhanden sind."""
    if not API_URL:
        logger.critical("API_URL ist nicht in den Umgebungsvariablen definiert")
        sys.exit(1)
    if not API_KEY:
        logger.critical("API_KEY ist nicht in den Umgebungsvariablen definiert")
        sys.exit(1)
