# scrapers/local_email_scraper.py
import email
import os
import json
import logging
import re
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime

from config.settings import DATABASE_PATH
from utils.helpers import logger, sanitize_text, extract_number_from_text

class LocalEmailScraper:
    """
    Scraper pour analyser les fichiers .eml d'AutoScout24 sauvegardés localement.
    """
    
    def __init__(self, emails_dir="emails"):
        """
        Initialise le scraper avec le dossier des emails.
        
        Args:
            emails_dir (str): Chemin vers le dossier contenant les fichiers .eml
        """
        self.emails_dir = emails_dir
        
        # Créer le dossier s'il n'existe pas
        os.makedirs(emails_dir, exist_ok=True)
    
    def list_email_files(self):
        """
        Liste tous les fichiers .eml dans le dossier des emails.
        
        Returns:
            list: Liste des chemins vers les fichiers .eml
        """
        email_files = []
        
        try:
            for file in os.listdir(self.emails_dir):
                if file.endswith(".eml"):
                    email_files.append(os.path.join(self.emails_dir, file))
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du dossier {self.emails_dir}: {str(e)}")
        
        return email_files
    
    def parse_email_file(self, email_file):
        """
        Parse un fichier .eml pour extraire les annonces.
        
        Args:
            email_file (str): Chemin vers le fichier .eml
            
        Returns:
            dict: Informations extraites du fichier
        """
        try:
            # Vérifier que le fichier existe
            if not os.path.exists(email_file):
                logger.error(f"Le fichier {email_file} n'existe pas")
                return None
            
            # Lire le fichier email
            with open(email_file, 'rb') as f:
                msg = email.message_from_binary_file(f)
            
            # Extraire l'objet de l'email
            subject = msg["Subject"]
            if subject:
                subject = email.header.decode_header(subject)[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
            
            # Extraire la date de réception
            date_str = msg["Date"]
            
            # Extraire le contenu HTML
            html_body = None
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode()
                    break
            
            if not html_body:
                logger.warning(f"Pas de contenu HTML trouvé dans l'email {email_file}")
                return None
            
            # Extraire les annonces
            car_listings = self.extract_car_listings(html_body)
            
            # Créer le résultat
            result = {
                "email_file": email_file,
                "subject": subject,
                "date": date_str,
                "car_listings": car_listings,
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Email {email_file} parsé avec succès, {len(car_listings)} annonces trouvées")
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors du parsing de l'email {email_file}: {str(e)}")
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
                        "source": "local_email",
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
    
    def process_emails(self, max_emails=10):
        """
        Traite les fichiers .eml dans le dossier des emails.
        
        Args:
            max_emails (int): Nombre maximum de fichiers à traiter
            
        Returns:
            list: Liste des annonces extraites
        """
        all_listings = []
        
        # Lister tous les fichiers .eml
        email_files = self.list_email_files()
        
        # Limiter le nombre de fichiers à traiter
        if max_emails > 0 and len(email_files) > max_emails:
            email_files = email_files[:max_emails]
        
        logger.info(f"Traitement de {len(email_files)} fichiers .eml")
        
        # Traiter chaque fichier
        for email_file in email_files:
            result = self.parse_email_file(email_file)
            if result and "car_listings" in result:
                all_listings.extend(result["car_listings"])
        
        # Stocker les annonces dans la base de données
        if all_listings:
            stored_count = self.store_listings_in_db(all_listings)
            logger.info(f"{stored_count} annonces stockées dans la base de données")
        
        logger.info(f"Traitement terminé, {len(all_listings)} annonces extraites")
        
        return all_listings

# Exemple d'utilisation
if __name__ == "__main__":
    scraper = LocalEmailScraper()
    listings = scraper.process_emails()
    print(f"Traitement terminé. {len(listings)} annonces trouvées.")