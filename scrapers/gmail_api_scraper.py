# scrapers/gmail_api_scraper.py
import os
import pickle
import re
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

from utils.helpers import logger, sanitize_text, extract_number_from_text

class GmailApiScraper:
    """
    Scraper utilisant l'API Gmail pour extraire les annonces automobiles
    directement depuis les emails d'alerte AutoScout24.
    Support pour l'authentification non-interactive.
    """
    
    def __init__(self, credentials_file='credentials/gmail_credentials.json', token_file='credentials/gmail_token.pickle'):
        """
        Initialise le scraper avec les fichiers d'authentification Google.
        
        Args:
            credentials_file (str): Chemin vers le fichier de credentials OAuth2
            token_file (str): Chemin vers le fichier de token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        self.service = None
        self.token_refresh_timestamp = None
    
    def is_token_valid(self, creds):
        """
        Vérifie si le token est valide et pas trop proche de l'expiration.
        
        Args:
            creds: Les credentials à vérifier
            
        Returns:
            bool: True si le token est valide, False sinon
        """
        if not creds or not creds.valid:
            return False
            
        # Si la dernière actualisation est récente, considérer comme valide
        if self.token_refresh_timestamp:
            last_refresh = datetime.fromtimestamp(self.token_refresh_timestamp)
            if datetime.now() - last_refresh < timedelta(hours=1):
                return True
                
        # Vérifier si le token expire bientôt (dans les 10 minutes)
        if hasattr(creds, 'expiry'):
            now = datetime.now()
            if creds.expiry and (creds.expiry - now).total_seconds() < 600:
                return False
                
        return True
    
    def authenticate(self, force_interactive=False):
        """
        Authentifie l'application avec l'API Gmail.
        
        Args:
            force_interactive (bool): Force l'authentification interactive
            
        Returns:
            bool: True si l'authentification a réussi, False sinon
        """
        creds = None
        
        # Charger le token existant s'il existe
        if os.path.exists(self.token_file) and not force_interactive:
            with open(self.token_file, 'rb') as token:
                try:
                    creds = pickle.load(token)
                    logger.info("Token existant chargé.")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du token: {str(e)}")
        
        # Si pas de credentials valides, essayer de rafraîchir
        if not self.is_token_valid(creds):
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Token rafraîchi.")
                    self.token_refresh_timestamp = datetime.now().timestamp()
                except Exception as e:
                    logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}")
                    creds = None
            
            # Si toujours pas de credentials valides et qu'une authentification interactive est possible
            if not creds:
                if force_interactive:
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.scopes)
                        creds = flow.run_local_server(port=0)
                        logger.info("Nouvelles credentials obtenues.")
                        self.token_refresh_timestamp = datetime.now().timestamp()
                    except Exception as e:
                        logger.error(f"Erreur lors de l'obtention des credentials: {str(e)}")
                        return False
                else:
                    logger.error("Pas de token valide et authentification interactive désactivée")
                    return False
            
            # Sauvegarder le token pour la prochaine fois
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
                logger.info("Token sauvegardé.")
        
        try:
            # Créer le service Gmail
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création du service Gmail: {str(e)}")
            return False
    
    def setup_watch(self, topic_name):
        """
        Configure la surveillance des emails pour les notifications push.
        
        Args:
            topic_name (str): Nom du topic Pub/Sub (format: 'projects/{project_id}/topics/{topic_name}')
            
        Returns:
            dict: Résultat de la configuration ou None en cas d'échec
        """
        if self.service is None:
            if not self.authenticate():
                logger.error("Impossible de s'authentifier avec l'API Gmail")
                return None
        
        try:
            # Configurer la surveillance des emails
            result = self.service.users().watch(
                userId='me',
                body={
                    'topicName': topic_name,
                    'labelIds': ['INBOX']
                }
            ).execute()
            
            logger.info(f"Surveillance des emails configurée: {result}")
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la configuration de la surveillance: {str(e)}")
            return None
    
    def fetch_autoscout_emails(self, max_emails=10, unread_only=True):
        """
        Récupère les emails d'alerte d'AutoScout24.
        
        Args:
            max_emails (int): Nombre maximum d'emails à récupérer
            unread_only (bool): Si True, ne récupère que les emails non lus
            
        Returns:
            list: Liste des IDs d'emails récupérés
        """
        if self.service is None:
            if not self.authenticate():
                logger.error("Impossible de s'authentifier avec l'API Gmail")
                return []
        
        try:
            # Construire la requête de recherche
            query = 'from:no-reply@rtm.autoscout24.com'
            if unread_only:
                query += ' is:unread'
            
            # Récupérer les IDs des messages
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_emails
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("Aucun email d'AutoScout24 trouvé")
                return []
            
            logger.info(f"Trouvé {len(messages)} emails d'AutoScout24")
            return messages
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des emails: {str(e)}")
            return []
    
    # Le reste des méthodes reste inchangé
    def get_email_content(self, msg_id):
        # [Code existant inchangé]
        pass
    
    def extract_car_listings(self, html_content):
        # [Code existant inchangé]
        pass
    
    def mark_as_read(self, msg_id):
        # [Code existant inchangé]
        pass
    
    def process_emails(self, max_emails=5, unread_only=True, mark_as_read=True):
        # [Code existant inchangé]
        pass