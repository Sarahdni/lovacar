# scrapers/autoscout_scraper.py
import requests
from bs4 import BeautifulSoup
import random
import time
import logging
from urllib.parse import urljoin
from config.settings import (
    BASE_URL, SEARCH_URL, USER_AGENTS, 
    REQUEST_TIMEOUT, REQUEST_DELAY, 
    LOCATION, SEARCH_RADIUS
)
from utils.helpers import logger, wait_random_delay, sanitize_text, extract_number_from_text

class AutoScoutScraper:
    """
    Scraper pour AutoScout24.
    Permet de récupérer les annonces de voitures d'occasion.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.update_headers()
    
    def update_headers(self):
        """
        Met à jour les en-têtes HTTP avec un User-Agent aléatoire.
        """
        user_agent = random.choice(USER_AGENTS)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': BASE_URL,
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        logger.debug(f"Headers mis à jour avec User-Agent: {user_agent}")
    
    def get_search_url(self, page=1, **filters):
        """
        Construit l'URL de recherche avec les filtres spécifiés.
        
        Args:
            page (int): Numéro de page
            **filters: Filtres supplémentaires (marque, modèle, prix, etc.)
            
        Returns:
            str: URL de recherche complète
        """
        # URL de base pour la recherche
        url = SEARCH_URL
        
        # Ajouter les paramètres de base
        params = {
            'page': page,
            'loc': LOCATION.replace(' ', '+'),
            'rad': SEARCH_RADIUS,
            'sort': 'age',
            'desc': '0',
            'cy': 'B',  # Belgique
            'atype': 'C',  # Voitures
            'ustate': 'N,U',  # Neuf et occasion
        }
        
        # Ajouter les filtres supplémentaires
        if 'brand' in filters:
            params['mmvmk0'] = filters['brand']
        if 'model' in filters:
            params['mmvmd0'] = filters['model']
        if 'max_price' in filters:
            params['priceto'] = filters['max_price']
        if 'min_price' in filters:
            params['pricefrom'] = filters['min_price']
        if 'max_mileage' in filters:
            params['kmto'] = filters['max_mileage']
        if 'min_year' in filters:
            params['fregfrom'] = filters['min_year']
        
        # Construire l'URL finale
        query_parts = [f"{k}={v}" for k, v in params.items()]
        url += "?" + "&".join(query_parts)
        
        logger.debug(f"URL de recherche générée: {url}")
        return url
    
    def fetch_page(self, url):
        """
        Récupère une page web et renvoie son contenu HTML.
        
        Args:
            url (str): URL de la page à récupérer
            
        Returns:
            str: Contenu HTML de la page
        """
        try:
            # Attendre un délai aléatoire pour éviter d'être détecté comme un bot
            wait_random_delay(*REQUEST_DELAY)
            
            # Mettre à jour les en-têtes avec un User-Agent aléatoire
            self.update_headers()
            
            # Faire la requête HTTP
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            
            # Vérifier si la requête a réussi
            if response.status_code == 200:
                logger.info(f"Page récupérée avec succès: {url}")
                return response.text
            else:
                logger.error(f"Erreur lors de la récupération de la page: {url}, code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Exception lors de la récupération de la page: {url}, erreur: {str(e)}")
            return None
    
    def parse_listing_page(self, html_content):
        """
        Parse le contenu HTML d'une page de listings et extrait les informations des annonces.
        
        Args:
            html_content (str): Contenu HTML de la page
            
        Returns:
            list: Liste de dictionnaires contenant les informations des annonces
        """
        if not html_content:
            return []
        
        listings = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Trouver tous les conteneurs d'annonces
        listing_containers = soup.select('div.cldt-listing')
        logger.info(f"Nombre d'annonces trouvées: {len(listing_containers)}")
        
        for container in listing_containers:
            try:
                # Extraire les informations de base
                listing_id = container.get('id', '').replace('lst-id-', '')
                
                # Extraire le titre
                title_element = container.select_one('h2')
                title = sanitize_text(title_element.text) if title_element else "Titre inconnu"
                
                # Extraire l'URL de l'annonce
                link_element = container.select_one('a.cldt-link')
                listing_url = urljoin(BASE_URL, link_element.get('href', '')) if link_element else None
                
                # Extraire le prix
                price_element = container.select_one('span.cldt-price')
                price_text = sanitize_text(price_element.text) if price_element else "Prix non spécifié"
                price = extract_number_from_text(price_text)
                
                # Extraire les détails du véhicule
                details = {}
                detail_elements = container.select('div.cldt-data span')
                for detail in detail_elements:
                    text = sanitize_text(detail.text)
                    if 'km' in text.lower():
                        details['mileage'] = extract_number_from_text(text)
                    elif any(word in text.lower() for word in ['diesel', 'essence', 'électrique', 'hybride']):
                        details['fuel_type'] = text
                    elif any(word in text.lower() for word in ['automatique', 'manuelle']):
                        details['transmission'] = text
                    elif any(char.isdigit() for char in text) and '/' in text:
                        details['first_registration'] = text
                    elif 'kw' in text.lower() or 'ch' in text.lower():
                        details['power'] = text
                
                # Créer l'objet annonce
                listing = {
                    'id': listing_id,
                    'title': title,
                    'url': listing_url,
                    'price': price,
                    'price_text': price_text,
                    **details,
                    'scrape_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                listings.append(listing)
                logger.debug(f"Annonce extraite: {listing['title']} - {listing['price_text']}")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction d'une annonce: {str(e)}")
                continue
        
        return listings
    
    def scrape_listings(self, max_pages=5, **filters):
        """
        Scrape les annonces sur plusieurs pages.
        
        Args:
            max_pages (int): Nombre maximum de pages à scraper
            **filters: Filtres de recherche
            
        Returns:
            list: Liste de toutes les annonces
        """
        all_listings = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping de la page {page}/{max_pages}")
            
            # Construire l'URL de recherche pour cette page
            url = self.get_search_url(page=page, **filters)
            
            # Récupérer le contenu HTML de la page
            html_content = self.fetch_page(url)
            
            if not html_content:
                logger.warning(f"Impossible de récupérer la page {page}, arrêt du scraping")
                break
            
            # Parser les annonces de cette page
            page_listings = self.parse_listing_page(html_content)
            
            if not page_listings:
                logger.warning(f"Aucune annonce trouvée sur la page {page}, arrêt du scraping")
                break
            
            # Ajouter les annonces de cette page à la liste complète
            all_listings.extend(page_listings)
            
            logger.info(f"Total d'annonces récupérées jusqu'à présent: {len(all_listings)}")
        
        return all_listings
    
    def get_listing_details(self, listing_url):
        """
        Récupère les détails complets d'une annonce.
        
        Args:
            listing_url (str): URL de l'annonce
            
        Returns:
            dict: Détails complets de l'annonce
        """
        # À implémenter ultérieurement
        # Cette méthode permettra de récupérer les détails complets d'une annonce en visitant sa page
        pass


# Exemple d'utilisation
if __name__ == "__main__":
    scraper = AutoScoutScraper()
    
    # Exemple de filtres
    filters = {
        'brand': 'Audi',  # Code de la marque Audi
        'model': '1580',  # Code du modèle A4
        'max_price': 30000,
        'min_year': 2015
    }
    
    listings = scraper.scrape_listings(max_pages=2, **filters)
    
    for i, listing in enumerate(listings[:5]):  # Afficher les 5 premières annonces
        print(f"\nAnnonce {i+1}:")
        print(f"Titre: {listing['title']}")
        print(f"Prix: {listing['price_text']}")
        print(f"URL: {listing['url']}")
        for key, value in listing.items():
            if key not in ['title', 'price_text', 'url']:
                print(f"{key}: {value}")