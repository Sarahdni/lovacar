# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parents[1] / '.env'
load_dotenv(dotenv_path=env_path)

# Paramètres de recherche
SEARCH_RADIUS = 50  # km autour de Waterloo
LOCATION = "Waterloo, Belgique"
LOCATION_COORDINATES = {
    "lat": 50.7159,
    "lng": 4.3994
}

# Paramètres de scraping
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]
REQUEST_TIMEOUT = 30  # secondes
REQUEST_DELAY = (3, 7)  # délai aléatoire entre les requêtes (min, max) en secondes

# URLs d'AutoScout24
BASE_URL = "https://www.autoscout24.be/fr/"
SEARCH_URL = f"{BASE_URL}lst/"
ESTIMATE_URL = "https://www.autoscout24.be/fr/vente-vehicule/venteexpress/"

# Paramètres email (depuis .env)
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_SERVER = os.getenv('EMAIL_SERVER', 'imap.gmail.com')
EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'INBOX')

# Nouveaux paramètres OAuth2 pour Gmail
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')

# Paramètres de la base de données
DATABASE_PATH = "database/car_listings.db"

# Paramètres des offres
MIN_DISCOUNT_PERCENTAGE = 10  # pourcentage minimum de réduction par rapport au prix affiché
MAX_DISCOUNT_PERCENTAGE = 20  # pourcentage maximum de réduction par rapport au prix affiché

# Paramètres des messages (depuis .env)
SENDER_NAME = os.getenv('SENDER_NAME', 'Acheteur intéressé')
COMPANY_NAME = os.getenv('COMPANY_NAME', '')
CONTACT_PHONE = os.getenv('CONTACT_PHONE', '')
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', EMAIL_ACCOUNT)

# Paramètres de l'estimateur de valeur
PROXY_SERVER = os.getenv('PROXY_SERVER')  # Serveur proxy si nécessaire
ZIPCODE = os.getenv('ZIPCODE', '1410')  # Code postal pour l'estimation (Waterloo)
HEADLESS_BROWSER = True  # Exécuter le navigateur en mode invisible