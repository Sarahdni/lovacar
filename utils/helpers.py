# utils/helpers.py
import random
import time
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lovacar.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("lovacar")

def get_random_delay(min_delay=3, max_delay=7):
    """
    Génère un délai aléatoire entre min_delay et max_delay.
    Utile pour éviter la détection de bot.
    """
    return random.uniform(min_delay, max_delay)

def wait_random_delay(min_delay=3, max_delay=7):
    """
    Attend un délai aléatoire entre min_delay et max_delay.
    """
    delay = get_random_delay(min_delay, max_delay)
    logger.debug(f"Attente de {delay:.2f} secondes...")
    time.sleep(delay)
    return delay

def format_timestamp():
    """
    Retourne un timestamp formaté pour les noms de fichiers.
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def sanitize_text(text):
    """
    Nettoie un texte en supprimant les caractères spéciaux et les espaces multiples.
    """
    if not text:
        return ""
    # Supprimer les caractères spéciaux et les espaces multiples
    import re
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_number_from_text(text):
    """
    Extrait un nombre à partir d'un texte.
    Par exemple, "10 000 €" -> 10000
    """
    if not text:
        return None
    import re
    # Trouver tous les chiffres dans le texte
    numbers = re.findall(r'\d+[\.,]?\d*', text.replace(' ', ''))
    if numbers:
        # Convertir la chaîne de caractères en nombre
        try:
            return float(numbers[0].replace(',', '.'))
        except ValueError:
            return None
    return None