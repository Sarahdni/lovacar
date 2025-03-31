# direct_gmail_api_final.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
import base64
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lovacar")

# Paramètres
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
GMAIL_CREDENTIALS_PATH = 'credentials/gmail_credentials.json'
GMAIL_TOKEN_PATH = 'credentials/gmail_token.json'
EMAIL_ACCOUNT = 'lovacar.waterloo@gmail.com'  # Remplacez par votre adresse email

def get_credentials():
    """
    Obtient les credentials OAuth2 pour l'API Gmail.
    """
    creds = None
    
    # Créer le dossier credentials s'il n'existe pas
    os.makedirs(os.path.dirname(GMAIL_CREDENTIALS_PATH), exist_ok=True)
    
    # Vérifier si les tokens existent et sont valides
    if os.path.exists(GMAIL_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(GMAIL_TOKEN_PATH)), 
                SCOPES
            )
            logger.info("Token existant chargé.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du token: {str(e)}")
            # Supprimer le token corrompu
            if os.path.exists(GMAIL_TOKEN_PATH):
                os.remove(GMAIL_TOKEN_PATH)
            creds = None
    
    # Si pas de credentials valides, démarrer le flux d'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Tokens rafraîchis avec succès")
            except Exception as e:
                logger.warning(f"Impossible de rafraîchir le token: {str(e)}")
                # Supprimer le token invalide
                if os.path.exists(GMAIL_TOKEN_PATH):
                    os.remove(GMAIL_TOKEN_PATH)
                creds = None
        
        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Fichier de credentials Google non trouvé: {GMAIL_CREDENTIALS_PATH}"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_PATH, 
                SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("Nouvelle authentification réussie")
            
            # Sauvegarder les tokens pour la prochaine fois
            with open(GMAIL_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Tokens sauvegardés dans {GMAIL_TOKEN_PATH}")
    
    return creds

def get_autoscout_emails(service, max_emails=5, unread_only=True):
    """
    Récupère les emails d'AutoScout24 via l'API Gmail.
    
    Args:
        service: Service Gmail API
        max_emails: Nombre max d'emails à récupérer
        unread_only: Si True, ne récupère que les emails non lus
        
    Returns:
        list: Liste des messages trouvés
    """
    # Construire la requête
    query = 'from:no-reply@rtm.autoscout24.com'
    if unread_only:
        query += ' is:unread'
    
    # Exécuter la recherche
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_emails
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"Trouvé {len(messages)} emails d'AutoScout24")
        return messages
    
    except Exception as e:
        logger.error(f"Erreur lors de la recherche d'emails: {str(e)}")
        return []

def extract_html_from_message(service, message_id):
    """
    Extrait le contenu HTML d'un message.
    
    Args:
        service: Service Gmail API
        message_id: ID du message
        
    Returns:
        str: Contenu HTML ou None
    """
    try:
        # Récupérer le message complet
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Extraire les parties du message
        payload = message.get('payload', {})
        parts = payload.get('parts', [])
        
        # Fonction récursive pour trouver le contenu HTML
        def find_html_part(parts):
            for part in parts:
                # Si la partie a des sous-parties, chercher récursivement
                if 'parts' in part:
                    html = find_html_part(part['parts'])
                    if html:
                        return html
                
                # Vérifier si c'est une partie HTML
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
            
            return None
        
        # Chercher dans les parties
        if parts:
            html = find_html_part(parts)
            if html:
                return html
        
        # Si pas trouvé dans les parties, chercher directement dans le corps
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            content = base64.urlsafe_b64decode(data).decode('utf-8')
            if '<html' in content.lower():
                return content
        
        logger.warning(f"Pas de contenu HTML trouvé dans le message {message_id}")
        return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du contenu HTML: {str(e)}")
        return None

def extract_number_from_text(text):
    """
    Extrait un nombre d'un texte en gérant les séparateurs de milliers spéciaux.
    
    Args:
        text: Texte contenant un nombre (ex: "10 000 €", "156 000 km")
        
    Returns:
        int/float: Nombre extrait ou None
    """
    if not text:
        return None
    
    try:
        # Supprimer tous les caractères non numériques sauf le point et la virgule
        # \u202f est un espace insécable étroit (narrow no-break space) utilisé comme séparateur de milliers en français
        cleaned_text = re.sub(r'[^\d.,]', '', text.replace('\u202f', '').replace(' ', ''))
        
        # Trouver tous les nombres
        numbers = re.findall(r'\d+[.,]?\d*', cleaned_text)
        
        if numbers:
            # Convertir en float (gérer le point et la virgule comme séparateur décimal)
            return float(numbers[0].replace(',', '.'))
        
        return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du nombre depuis '{text}': {str(e)}")
        return None

def extract_car_listings(html_content):
    """
    Extrait les annonces de voitures du contenu HTML.
    
    Args:
        html_content: Contenu HTML d'un email
        
    Returns:
        list: Liste des annonces trouvées
    """
    listings = []
    
    try:
        # Créer un dossier pour sauvegarder les emails
        debug_dir = "debug_emails"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Sauvegarder le HTML pour débogage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"{debug_dir}/email_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Parser le HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Trouver toutes les tables d'annonces
        vehicle_tables = soup.select('table.border-container')
        logger.info(f"Tables de véhicules trouvées: {len(vehicle_tables)}")
        
        for i, table in enumerate(vehicle_tables):
            try:
                # Extraire l'URL (lien "Détails")
                details_link = None
                links = table.select('a')
                for link in links:
                    if link.text.strip() == "Détails":
                        details_link = link
                        break
                
                listing_url = details_link.get('href') if details_link else None
                
                # Nettoyer l'URL (enlever la redirection)
                if listing_url and "click.mails.autoscout24.com" in listing_url:
                    if "autoscout24.be/fr/offres/" in listing_url:
                        match = re.search(r'autoscout24.be/fr/offres/([^?&]+)', listing_url)
                        if match:
                            listing_url = f"https://www.autoscout24.be/fr/offres/{match.group(1)}"
                
                # Extraire le titre
                title_elem = table.select_one('div.card-title a, div.card-right-part-ellipse-container a')
                title = title_elem.text.strip() if title_elem else f"Véhicule {i+1}"
                
                # Extraire le prix
                price_elem = table.select_one('a.price, span.price')
                price_text = price_elem.text.strip() if price_elem else "Prix non spécifié"
                price = extract_number_from_text(price_text)
                
                # Extraire les détails (kilométrage, année)
                details_elem = table.select_one('a.small-details')
                details_text = details_elem.text.strip() if details_elem else ""
                
                # Extraire le kilométrage
                mileage = None
                if details_text:
                    mileage_match = re.search(r'(\d+[\s\u202f]?\d*)\s*km', details_text)
                    if mileage_match:
                        mileage_text = mileage_match.group(1)
                        mileage = extract_number_from_text(mileage_text)
                
                # Extraire l'année
                year = None
                if details_text:
                    year_match = re.search(r'(\d{2})/(\d{4})', details_text)
                    if year_match:
                        year = int(year_match.group(2))
                
                # Extraire l'image
                img_elem = table.select_one('img[alt="vehicle"]')
                img_url = img_elem.get('src') if img_elem else None
                
                # Extraire la marque et le modèle
                make = None
                model = None
                if title:
                    parts = title.split()
                    if len(parts) > 0:
                        make = parts[0]
                    if len(parts) > 1:
                        model = parts[1]
                
                # Créer l'annonce
                listing = {
                    "title": title,
                    "make": make,
                    "model": model,
                    "price_text": price_text,
                    "price": price,
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
                logger.error(f"Erreur lors de l'extraction de l'annonce {i+1}: {str(e)}")
        
        return listings
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des annonces: {str(e)}")
        return []

def mark_emails_as_read(service, message_ids):
    """
    Marque des messages comme lus.
    
    Args:
        service: Service Gmail API
        message_ids: Liste d'IDs de messages
        
    Returns:
        bool: Succès de l'opération
    """
    try:
        # Créer la requête de modification
        body = {
            'removeLabelIds': ['UNREAD']
        }
        
        # Marquer chaque message
        for message in message_ids:
            service.users().messages().modify(
                userId='me',
                id=message['id'],
                body=body
            ).execute()
        
        logger.info(f"{len(message_ids)} emails marqués comme lus")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors du marquage des emails: {str(e)}")
        return False

def save_to_mongodb(listings):
    """
    Sauvegarde les annonces dans MongoDB.
    
    Args:
        listings: Liste des annonces à sauvegarder
        
    Returns:
        int: Nombre d'annonces sauvegardées
    """
    try:
        # Cette fonction sera implémentée plus tard pour utiliser MongoDB
        # Pour l'instant, retournons simplement le nombre d'annonces
        logger.info(f"MongoDB: {len(listings)} annonces seraient sauvegardées")
        return len(listings)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde dans MongoDB: {str(e)}")
        return 0

def test_direct_gmail_api():
    """
    Teste l'accès direct à l'API Gmail.
    """
    print("Test d'accès direct à l'API Gmail")
    
    try:
        # Obtenir les credentials
        creds = get_credentials()
        
        # Créer le service Gmail
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Service Gmail créé avec succès")
        
        # Rechercher les emails d'AutoScout24
        messages = get_autoscout_emails(service, max_emails=5, unread_only=False)
        
        if not messages:
            print("ℹ️ Aucun email d'AutoScout24 trouvé")
            return
        
        print(f"✅ {len(messages)} emails d'AutoScout24 trouvés")
        
        # Extraire le contenu HTML du premier message
        html_content = extract_html_from_message(service, messages[0]['id'])
        
        if not html_content:
            print("❌ Impossible d'extraire le contenu HTML")
            return
        
        print("✅ Contenu HTML extrait avec succès")
        
        # Extraire les annonces
        listings = extract_car_listings(html_content)
        
        if not listings:
            print("❌ Aucune annonce trouvée dans l'email")
            return
        
        print(f"✅ {len(listings)} annonces trouvées!")
        
        # Afficher les détails des annonces
        for i, listing in enumerate(listings):
            print(f"\nAnnonce {i+1}:")
            print(f"  Titre: {listing['title']}")
            print(f"  Prix: {listing['price_text']} ({listing['price']})")
            print(f"  Année: {listing['year']}")
            if listing.get('mileage'):
                print(f"  Kilométrage: {listing['mileage']} km")
            else:
                print(f"  Kilométrage: Non spécifié")
            if listing['url']:
                print(f"  URL: {listing['url']}")
        
        # Marquer automatiquement les emails comme lus
        mark_emails_as_read(service, messages)
        print("✅ Emails marqués comme lus automatiquement")
        
        # Préparer pour MongoDB
        print(f"ℹ️ Préparation pour MongoDB: {len(listings)} annonces à sauvegarder")
    
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")

if __name__ == "__main__":
    test_direct_gmail_api()