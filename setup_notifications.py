# setup_notifications.py
from scrapers.gmail_api_scraper import GmailApiScraper
from utils.helpers import logger

# Remplacer par les valeurs de ton projet Google Cloud
PROJECT_ID = "lovacar"  # Ton ID de projet
TOPIC_NAME = f"projects/{PROJECT_ID}/topics/gmail-notifications"

def setup_gmail_watch():
    """
    Configure la surveillance des emails Gmail
    """
    scraper = GmailApiScraper()
    
    # Authentifier avec interaction forcée
    if not scraper.authenticate(force_interactive=True):
        logger.error("Échec d'authentification pour la configuration de la surveillance")
        return False
        
    # Configurer la surveillance
    result = scraper.setup_watch(topic_name=TOPIC_NAME)
    
    if result:
        logger.info("Surveillance des emails configurée avec succès")
        logger.info(f"Expiration (historyId: {result.get('historyId')})")
        logger.info(f"Expiration: {result.get('expiration')} ms (~7 jours)")
        return True
    else:
        logger.error("Échec de configuration de la surveillance des emails")
        return False

if __name__ == "__main__":
    setup_gmail_watch()