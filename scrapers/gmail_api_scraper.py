# scrapers/gmail_api_scraper.py
import os
import pickle
import re
import logging
from datetime import datetime
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
    """
    
    def __init__(self, credentials_file='credentials/gmail_credentials.json', token_file='credentials/token.pickle'):
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
    
    def authenticate(self):
        """
        Authentifie l'application avec l'API Gmail.
        
        Returns:
            bool: True si l'authentification a réussi, False sinon
        """
        creds = None
        
        # Charger le token existant s'il existe
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                try:
                    creds = pickle.load(token)
                    logger.info("Token existant chargé.")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du token: {str(e)}")
        
        # Si pas de credentials valides, demander à l'utilisateur de s'authentifier
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Token rafraîchi.")
                except Exception as e:
                    logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                    logger.info("Nouvelles credentials obtenues.")
                except Exception as e:
                    logger.error(f"Erreur lors de l'obtention des credentials: {str(e)}")
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
    
    def get_email_content(self, msg_id):
        """
        Récupère le contenu d'un email spécifique.
        
        Args:
            msg_id (str): ID du message Gmail
            
        Returns:
            dict: Contenu de l'email (sujet, date, corps HTML)
        """
        if self.service is None:
            if not self.authenticate():
                logger.error("Impossible de s'authentifier avec l'API Gmail")
                return None
        
        try:
            # Récupérer le message complet
            message = self.service.users().messages().get(
                userId='me', 
                id=msg_id['id'],
                format='full'
            ).execute()
            
            # Extraire les headers (sujet, date)
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), None)
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
            
            # Extraire le corps HTML
            html_content = None
            
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/html':
                        html_content = part['body'].get('data', '')
                        break
            elif message['payload']['mimeType'] == 'text/html':
                html_content = message['payload']['body'].get('data', '')
            
            if html_content:
                # Décoder le contenu Base64
                html_content = base64.urlsafe_b64decode(html_content.encode('ASCII')).decode('utf-8')
            
            return {
                'id': msg_id['id'],
                'subject': subject,
                'date': date,
                'html_content': html_content
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contenu de l'email {msg_id['id']}: {str(e)}")
            return None
    
    def extract_car_listings(self, html_content):
        """
        Extrait les informations des annonces de voiture à partir du contenu HTML.
        
        Args:
            html_content (str): Contenu HTML de l'email
            
        Returns:
            list: Liste des annonces extraites
        """
        listings = []
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Trouver toutes les tables de véhicules
            vehicle_tables = soup.select('table.border-container')
            logger.info(f"Tables de véhicules trouvées: {len(vehicle_tables)}")
            
            for table in vehicle_tables:
                try:
                    # Extraire l'URL de l'annonce (lien "Détails")
                    details_link = None
                    links = table.select('a')
                    for link in links:
                        if link.text.strip() == "Détails":
                            details_link = link
                            break
                    
                    listing_url = details_link.get('href') if details_link else None
                    
                    # Nettoyer l'URL (supprimer les redirections)
                    if listing_url and "click.mails.autoscout24.com" in listing_url:
                        # Extraire l'URL d'origine si possible
                        if "autoscout24.be/fr/offres/" in listing_url:
                            match = re.search(r'autoscout24.be/fr/offres/([^?&]+)', listing_url)
                            if match:
                                listing_url = f"https://www.autoscout24.be/fr/offres/{match.group(1)}"
                    
                    # Extraire le titre
                    title_elem = table.select_one('div.card-title a')
                    if not title_elem:
                        title_elem = table.select_one('div.card-right-part-ellipse-container a')
                    title = sanitize_text(title_elem.text) if title_elem else "Titre inconnu"
                    
                    # Extraire le prix
                    price_elem = table.select_one('a.price')
                    price_text = sanitize_text(price_elem.text) if price_elem else "Prix non spécifié"
                    price = extract_number_from_text(price_text)
                    
                    # Extraire les détails (kilométrage, année, etc.)
                    details_elem = table.select_one('a.small-details')
                    details_text = sanitize_text(details_elem.text) if details_elem else ""
                    
                    # Extraire le kilométrage et l'année
                    mileage = None
                    year = None
                    if details_text:
                        mileage_match = re.search(r'(\d+[\s.]?\d*)\s*km', details_text)
                        if mileage_match:
                            mileage_str = mileage_match.group(1).replace(' ', '').replace('.', '')
                            mileage = int(mileage_str)
                        
                        year_match = re.search(r'(\d{2})/(\d{4})', details_text)
                        if year_match:
                            year = int(year_match.group(2))
                    
                    # Extraire l'image
                    img_elem = table.select_one('img[alt="vehicle"]')
                    img_url = img_elem.get('src') if img_elem else None
                    
                    # Extraire la marque et le modèle du titre
                    make = None
                    model = None
                    if title:
                        parts = title.split()
                        if len(parts) > 0:
                            make = parts[0]
                        if len(parts) > 1:
                            model = ' '.join(parts[1:]) if len(parts) > 2 else parts[1]
                    
                    # Créer l'objet annonce
                    listing = {
                        "title": title,
                        "make": make,
                        "model": model,
                        "price": price,
                        "price_text": price_text,
                        "details": details_text,
                        "mileage": mileage,
                        "year": year,
                        "url": listing_url,
                        "image_url": img_url,
                        "source": "gmail_api",
                        "scraped_at": datetime.now().isoformat()
                    }
                    
                    listings.append(listing)
                    logger.info(f"Annonce extraite: {title}")
                
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction d'une annonce: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des annonces: {str(e)}")
        
        return listings
    
    def mark_as_read(self, msg_id):
        """
        Marque un email comme lu.
        
        Args:
            msg_id (str): ID du message Gmail
            
        Returns:
            bool: True si le message a été marqué comme lu, False sinon
        """
        if self.service is None:
            if not self.authenticate():
                logger.error("Impossible de s'authentifier avec l'API Gmail")
                return False
        
        try:
            # Modifier les libellés pour supprimer UNREAD
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors du marquage de l'email {msg_id} comme lu: {str(e)}")
            return False
    
    def process_emails(self, max_emails=5, unread_only=True, mark_as_read=True):
        """
        Traite les emails d'alerte AutoScout24.
        
        Args:
            max_emails (int): Nombre maximum d'emails à traiter
            unread_only (bool): Si True, ne traite que les emails non lus
            mark_as_read (bool): Si True, marque les emails traités comme lus
            
        Returns:
            list: Liste des annonces extraites
        """
        all_listings = []
        
        # Récupérer les emails
        emails = self.fetch_autoscout_emails(max_emails, unread_only)
        
        for email in emails:
            # Récupérer le contenu de l'email
            email_content = self.get_email_content(email)
            
            if email_content and email_content.get('html_content'):
                # Extraire les annonces
                listings = self.extract_car_listings(email_content['html_content'])
                all_listings.extend(listings)
                
                # Marquer l'email comme lu
                if mark_as_read and unread_only:
                    self.mark_as_read(email['id'])
        
        logger.info(f"Traitement terminé, {len(all_listings)} annonces extraites")
        return all_listings

# Exemple d'utilisation
if __name__ == "__main__":
    scraper = GmailApiScraper()
    listings = scraper.process_emails(max_emails=3)
    
    if listings:
        print(f"\nAnnonces extraites: {len(listings)}")
        for i, listing in enumerate(listings[:3], 1):
            print(f"\n{i}. {listing['make']} {listing['model']}")
            print(f"   Prix: {listing['price_text']}")
            print(f"   Année: {listing['year']}, Kilométrage: {listing['mileage']} km")
            print(f"   URL: {listing['url']}")
    else:
        print("Aucune annonce trouvée.")