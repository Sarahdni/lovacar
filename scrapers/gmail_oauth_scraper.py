# scrapers/gmail_oauth_scraper.py
import imaplib
import email
import os
import json
import logging
import re
import sqlite3
import base64
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from config.settings import (
    DATABASE_PATH, EMAIL_ACCOUNT, GMAIL_TOKEN_PATH, GMAIL_CREDENTIALS_PATH
)
from utils.helpers import logger, sanitize_text, extract_number_from_text

class GmailOAuthScraper:
    """
    Scraper pour les emails d'alerte AutoScout24 via Gmail avec authentification OAuth2.
    """
    
    def __init__(self, email_account=EMAIL_ACCOUNT):
        """
        Initialise le scraper avec l'authentification OAuth2 pour Gmail.
        
        Args:
            email_account (str): Adresse email pour se connecter
        """
        self.email_account = email_account
        self.mail = None
        self.scopes = ['https://mail.google.com/']
        
        # Dossier pour sauvegarder les emails bruts pour debug
        self.email_debug_dir = "debug_emails"
        os.makedirs(self.email_debug_dir, exist_ok=True)
    
    def get_credentials(self):
        """
        Obtient ou rafraîchit les credentials OAuth2 pour Gmail.
        
        Returns:
            Credentials: Les credentials OAuth2
        """
        creds = None
        
        # Vérifier si les tokens existent et sont valides
        if os.path.exists(GMAIL_TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.load(open(GMAIL_TOKEN_PATH)), 
                    self.scopes
                )
            except Exception as e:
                logger.error(f"Erreur lors du chargement des tokens: {str(e)}")
        
        # Si pas de credentials valides, démarrer le flux d'authentification
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Tokens rafraîchis avec succès")
                except RefreshError:
                    logger.warning("Impossible de rafraîchir le token, nouvelle authentification requise")
                    creds = None
            
            if not creds:
                if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Fichier de credentials Google non trouvé: {GMAIL_CREDENTIALS_PATH}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_PATH, 
                    self.scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("Nouvelle authentification réussie")
            
            # Sauvegarder les tokens pour la prochaine fois
            with open(GMAIL_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Tokens sauvegardés dans {GMAIL_TOKEN_PATH}")
        
        return creds
    
    def connect(self):
        """
        Se connecte au serveur IMAP de Gmail avec OAuth2.
        
        Returns:
            bool: True si la connexion réussit, False sinon
        """
        try:
            # Créer une connexion sécurisée au serveur IMAP
            self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
            
            # Obtenir les credentials OAuth2
            creds = self.get_credentials()
            
            # Authentification OAuth2
            auth_string = f'user={self.email_account}\1auth=Bearer {creds.token}\1\1'
            auth_string = base64.b64encode(auth_string.encode()).decode()
            
            self.mail.authenticate('XOAUTH2', lambda x: auth_string)
            
            logger.info(f"Connexion OAuth2 réussie à Gmail avec le compte {self.email_account}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur de connexion OAuth2: {str(e)}")
            if self.mail:
                try:
                    self.mail.logout()
                except:
                    pass
            return False
    
    def disconnect(self):
        """
        Se déconnecte du serveur IMAP.
        """
        if self.mail:
            try:
                self.mail.logout()
                logger.info("Déconnexion du serveur IMAP")
            except Exception as e:
                logger.error(f"Erreur lors de la déconnexion: {str(e)}")
    
    def fetch_autoscout_emails(self, max_emails=10, unread_only=True, folder="INBOX"):
        """
        Récupère les emails d'alerte d'AutoScout24.
        
        Args:
            max_emails (int): Nombre maximum d'emails à récupérer
            unread_only (bool): Si True, ne récupère que les emails non lus
            folder (str): Dossier à rechercher
            
        Returns:
            list: Liste des IDs d'emails récupérés
        """
        try:
            # Sélectionner le dossier
            self.mail.select(folder)
            
            # Définir les critères de recherche
            search_criteria = '(FROM "no-reply@rtm.autoscout24.com")'
            if unread_only:
                search_criteria = f'(UNSEEN {search_criteria})'
            
            # Rechercher les emails
            status, email_ids = self.mail.search(None, search_criteria)
            
            if status != "OK":
                logger.error("Erreur lors de la recherche d'emails")
                return []
            
            # Convertir la réponse en liste d'IDs
            email_id_list = email_ids[0].split()
            
            # Limiter le nombre d'emails
            if max_emails > 0 and len(email_id_list) > max_emails:
                email_id_list = email_id_list[-max_emails:]
            
            logger.info(f"Trouvé {len(email_id_list)} emails d'AutoScout24")
            return email_id_list
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des emails: {str(e)}")
            return []
    
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
            
            # Trouver toutes les tables de véhicules (comme observé dans l'exemple d'email)
            vehicle_tables = soup.select('table.border-container')
            
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
                        # Pour une utilisation réelle, il faudrait suivre la redirection
                        # Ici on extrait l'URL d'origine si possible
                        if "autoscout24.be/fr/offres/" in listing_url:
                            match = re.search(r'autoscout24.be/fr/offres/([^?&]+)', listing_url)
                            if match:
                                listing_url = f"https://www.autoscout24.be/fr/offres/{match.group(1)}"
                    
                    # Extraire le titre
                    title_elem = table.select_one('div.card-title a')
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
                            model = parts[1]
                    
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
                        "source": "email",
                        "scraped_at": datetime.now().isoformat()
                    }
                    
                    listings.append(listing)
                    logger.debug(f"Annonce extraite: {title}")
                
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction d'une annonce: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des annonces: {str(e)}")
        
        return listings
    
    def parse_email(self, email_id):
        """
        Parse un email spécifique pour extraire les annonces de voitures.
        
        Args:
            email_id (bytes): ID de l'email à parser
            
        Returns:
            dict: Informations extraites de l'email
        """
        try:
            # Récupérer l'email
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                logger.error(f"Erreur lors de la récupération de l'email {email_id}")
                return None
            
            # Décoder l'email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extraire l'objet de l'email
            subject = email.header.decode_header(email_message["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            
            # Extraire la date de réception
            date_str = email_message["Date"]
            
            # Sauvegarder l'email brut pour debug
            email_filename = f"{self.email_debug_dir}/{email_id.decode()}.eml"
            with open(email_filename, "wb") as f:
                f.write(raw_email)
            
            # Extraire le contenu HTML
            html_body = None
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode()
                    break
            
            if not html_body:
                logger.warning(f"Pas de contenu HTML trouvé dans l'email {email_id}")
                return None
            
            # Extraire les annonces
            car_listings = self.extract_car_listings(html_body)
            
            # Créer le résultat
            result = {
                "email_id": email_id.decode(),
                "subject": subject,
                "date": date_str,
                "car_listings": car_listings,
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Email {email_id} parsé avec succès, {len(car_listings)} annonces trouvées")
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors du parsing de l'email {email_id}: {str(e)}")
            return None
    
    def store_listings_in_db(self, listings):
        """
        Stocke les annonces dans la base de données.
        
        Args:
            listings (list): Liste des annonces à stocker
            
        Returns:
            int: Nombre d'annonces stockées avec succès
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # S'assurer que le dossier de la base de données existe
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        # Créer la table si elle n'existe pas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            make TEXT,
            model TEXT,
            price INTEGER,
            price_text TEXT,
            mileage INTEGER,
            year INTEGER,
            url TEXT UNIQUE,
            image_url TEXT,
            source TEXT,
            scraped_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estimated_value INTEGER,
            suggested_offer INTEGER,
            discount_percentage REAL,
            visited BOOLEAN DEFAULT 0,
            contacted BOOLEAN DEFAULT 0,
            details TEXT
        )
        ''')
        
        successful_inserts = 0
        
        for listing in listings:
            try:
                # Vérifier si l'annonce existe déjà
                cursor.execute("SELECT id FROM listings WHERE url = ?", (listing.get('url'),))
                existing = cursor.fetchone()
                
                if existing:
                    # Mettre à jour l'annonce existante
                    fields = []
                    values = []
                    
                    for key, value in listing.items():
                        if key != 'url' and value is not None:
                            fields.append(f"{key} = ?")
                            values.append(value)
                    
                    fields.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(existing[0])  # ID pour la clause WHERE
                    
                    cursor.execute(
                        f"UPDATE listings SET {', '.join(fields)} WHERE id = ?",
                        values
                    )
                    
                    logger.debug(f"Annonce mise à jour: {listing.get('title')}")
                    successful_inserts += 1
                else:
                    # Insérer une nouvelle annonce
                    fields = []
                    placeholders = []
                    values = []
                    
                    for key, value in listing.items():
                        if value is not None:
                            fields.append(key)
                            placeholders.append('?')
                            values.append(value)
                    
                    cursor.execute(
                        f"INSERT INTO listings ({', '.join(fields)}) VALUES ({', '.join(placeholders)})",
                        values
                    )
                    
                    logger.debug(f"Nouvelle annonce ajoutée: {listing.get('title')}")
                    successful_inserts += 1
            
            except Exception as e:
                logger.error(f"Erreur lors du stockage de l'annonce: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        return successful_inserts
    
    def process_emails(self, max_emails=10, unread_only=True):
        """
        Traite tous les emails d'alerte AutoScout24.
        
        Args:
            max_emails (int): Nombre maximum d'emails à traiter
            unread_only (bool): Si True, ne traite que les emails non lus
            
        Returns:
            list: Liste des annonces extraites
        """
        all_listings = []
        
        try:
            if not self.connect():
                return []
            
            # Récupérer les IDs des emails
            email_ids = self.fetch_autoscout_emails(max_emails, unread_only)
            
            for email_id in email_ids:
                result = self.parse_email(email_id)
                if result and "car_listings" in result:
                    all_listings.extend(result["car_listings"])
            
            # Stocker les annonces dans la base de données
            if all_listings:
                stored_count = self.store_listings_in_db(all_listings)
                logger.info(f"{stored_count} annonces stockées dans la base de données")
            
            # Marquer les emails comme lus si nécessaire
            if unread_only and email_ids:
                for email_id in email_ids:
                    self.mail.store(email_id, '+FLAGS', '\Seen')
                logger.info(f"Marqué {len(email_ids)} emails comme lus")
            
            logger.info(f"Traitement terminé, {len(all_listings)} annonces extraites")
            
        finally:
            self.disconnect()
        
        return all_listings

# Exemple d'utilisation
if __name__ == "__main__":
    scraper = GmailOAuthScraper()
    listings = scraper.process_emails(max_emails=5, unread_only=True)
    print(f"Traitement terminé. {len(listings)} annonces trouvées.")