# config/settings.py

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
    # Ajoutez d'autres user agents pour la rotation
]
REQUEST_TIMEOUT = 30  # secondes
REQUEST_DELAY = (3, 7)  # délai aléatoire entre les requêtes (min, max) en secondes

# URLs d'AutoScout24
BASE_URL = "https://www.autoscout24.be/fr/"
SEARCH_URL = f"{BASE_URL}lst/"

# Paramètres de la base de données
DATABASE_PATH = "database/car_listings.db"

# Paramètres des offres
MIN_DISCOUNT_PERCENTAGE = 10  # pourcentage minimum de réduction par rapport au prix affiché
MAX_DISCOUNT_PERCENTAGE = 20  # pourcentage maximum de réduction par rapport au prix affiché

# Paramètres des messages
SENDER_NAME = "Votre nom"
COMPANY_NAME = "Votre entreprise"
CONTACT_PHONE = "Votre numéro de téléphone"
CONTACT_EMAIL = "votre.email@exemple.com"