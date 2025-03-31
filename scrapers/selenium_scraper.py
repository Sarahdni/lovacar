# scrapers/selenium_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import random
import os
from urllib.parse import urljoin

from config.settings import (
    BASE_URL, SEARCH_URL, USER_AGENTS,
    REQUEST_TIMEOUT, REQUEST_DELAY,
    LOCATION, SEARCH_RADIUS
)
from utils.helpers import logger, wait_random_delay, sanitize_text, extract_number_from_text

class AutoScoutSeleniumScraper:
    """
    Scraper pour AutoScout24 utilisant Selenium pour contourner les protections anti-bot.
    """
    
    def __init__(self, headless=True):
        """
        Initialise le scraper avec un navigateur Chrome.
        
        Args:
            headless (bool): Si True, le navigateur s'exécute en arrière-plan (sans interface graphique)
        """
        self.headless = headless
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """
        Configure le driver Selenium Chrome.
        """
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")  # Mode headless moderne
        
        # Ajouter des options pour éviter la détection comme un bot
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        
        # Ajouter un User-Agent aléatoire
        user_agent = random.choice(USER_AGENTS)
        options.add_argument(f"--user-agent={user_agent}")
        
        # Initialiser le driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Configurer des délais d'attente implicites
        self.driver.implicitly_wait(10)  # Attendre jusqu'à 10 secondes pour que les éléments apparaissent
        
        # Modifier les propriétés du navigateur pour éviter la détection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Driver Selenium initialisé avec succès")
    
    def close(self):
        """
        Ferme le navigateur.
        """
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Driver Selenium fermé")
    
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
    
    def navigate_to_page(self, url):
        """
        Navigue vers l'URL spécifiée et attend que la page soit chargée.
        
        Args:
            url (str): URL de la page à visiter
            
        Returns:
            bool: True si la navigation a réussi, False sinon
        """
        try:
            # Attendre un délai aléatoire pour éviter d'être détecté comme un bot
            wait_random_delay(*REQUEST_DELAY)
            
            # Naviguer vers l'URL
            self.driver.get(url)
            
            # Attendre que la page soit chargée
            WebDriverWait(self.driver, REQUEST_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Petit délai supplémentaire pour s'assurer que le contenu JavaScript est chargé
            time.sleep(3)
            
            # Prendre une capture d'écran pour le débogage
            screenshot_path = "page_screenshot.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Capture d'écran enregistrée: {os.path.abspath(screenshot_path)}")
            
            # Obtenir le HTML de la page pour analyse
            html_content = self.driver.page_source
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("HTML de la page enregistré dans 'page_source.html'")
            
            logger.info(f"Navigation réussie vers: {url}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers: {url}, erreur: {str(e)}")
            return False
    
    def parse_listing_page(self):
        """
        Parse la page de résultats de recherche pour extraire les informations des annonces.
        
        Returns:
            list: Liste de dictionnaires contenant les informations des annonces
        """
        listings = []
        
        try:
            # Attendre que le contenu principal soit chargé
            time.sleep(5)  # Attente prolongée pour s'assurer que tout est chargé
            
            # Méthode 1: Rechercher les annonces par la classe principale de la liste de résultats
            # Regardons d'abord ce qui est disponible
            main_elements = self.driver.find_elements(By.CSS_SELECTOR, "main")
            if main_elements:
                logger.info(f"Élément main trouvé, ID: {main_elements[0].get_attribute('id')}")
            
            # Essayer différents sélecteurs, car la structure a pu changer
            selectors_to_try = [
                "article[data-article-id]",
                "div[data-testid='list-item']",
                "div.listing-item",
                "div.result-item",
                "div[data-item-index]",
                "div.sc-grid-item"
            ]
            
            listing_containers = []
            for selector in selectors_to_try:
                listing_containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listing_containers:
                    logger.info(f"Sélecteur fonctionnel trouvé: {selector}")
                    break
            
            # Si aucun sélecteur n'a fonctionné, essayer une approche plus générique
            if not listing_containers:
                logger.warning("Aucun sélecteur spécifique n'a fonctionné, tentative plus générique...")
                # Chercher tous les liens qui pourraient être des annonces
                links = self.driver.find_elements(By.TAG_NAME, "a")
                pattern = "/fr/voiture/"  # Un motif qui pourrait être présent dans les URLs d'annonces
                
                listing_urls = []
                for link in links:
                    href = link.get_attribute("href")
                    if href and pattern in href and href not in listing_urls:
                        listing_urls.append(href)
                
                logger.info(f"URLs d'annonces trouvées: {len(listing_urls)}")
                
                # Créer des annonces basiques à partir des URLs
                for url in listing_urls:
                    listing = {
                        'id': url.split("/")[-1] if "/" in url else "unknown",
                        'title': "Titre non extrait",
                        'url': url,
                        'price_text': "Prix non extrait",
                        'price': None,
                        'scrape_date': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    listings.append(listing)
                
                return listings
            
            logger.info(f"Nombre d'annonces trouvées: {len(listing_containers)}")
            
            for i, container in enumerate(listing_containers):
                try:
                    # Log HTML pour le premier conteneur pour aider au débogage
                    if i == 0:
                        container_html = container.get_attribute('outerHTML')
                        logger.debug(f"HTML du premier conteneur: {container_html[:500]}...")
                    
                    # Extraire l'ID de l'annonce (essayer différentes méthodes)
                    listing_id = container.get_attribute('data-article-id') or container.get_attribute('id') or f"unknown-{i}"
                    
                    # Extraire le titre (essayer différentes méthodes)
                    title_element = None
                    for selector in ["h2", "h3", ".title", "[data-testid='title']"]:
                        elements = container.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            title_element = elements[0]
                            break
                    
                    title = sanitize_text(title_element.text) if title_element else f"Annonce {i+1}"
                    
                    # Extraire l'URL de l'annonce
                    link_element = container.find_element(By.TAG_NAME, "a")
                    listing_url = link_element.get_attribute('href') if link_element else None
                    
                    # Extraire le prix (essayer différentes méthodes)
                    price_text = "Prix non disponible"
                    price = None
                    for price_selector in ["[data-testid='price']", ".price", "span.sc-font-bold", "div.price"]:
                        price_elements = container.find_elements(By.CSS_SELECTOR, price_selector)
                        if price_elements:
                            price_text = sanitize_text(price_elements[0].text)
                            price = extract_number_from_text(price_text)
                            break
                    
                    # Créer l'objet annonce
                    listing = {
                        'id': listing_id,
                        'title': title,
                        'url': listing_url,
                        'price': price,
                        'price_text': price_text,
                        'scrape_date': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    listings.append(listing)
                    logger.debug(f"Annonce extraite: {listing['title']} - {listing['price_text']}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction de l'annonce {i}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la page: {str(e)}")
        
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
        
        try:
            for page in range(1, max_pages + 1):
                logger.info(f"Scraping de la page {page}/{max_pages}")
                
                # Construire l'URL de recherche pour cette page
                url = self.get_search_url(page=page, **filters)
                
                # Naviguer vers la page
                success = self.navigate_to_page(url)
                
                if not success:
                    logger.warning(f"Impossible de naviguer vers la page {page}, arrêt du scraping")
                    break
                
                # Vérifier si nous devons accepter les cookies (première page seulement)
                if page == 1:
                    self.handle_cookie_consent()
                
                # Parser les annonces de cette page
                page_listings = self.parse_listing_page()
                
                if not page_listings:
                    logger.warning(f"Aucune annonce trouvée sur la page {page}, arrêt du scraping")
                    break
                
                # Ajouter les annonces de cette page à la liste complète
                all_listings.extend(page_listings)
                
                logger.info(f"Total d'annonces récupérées jusqu'à présent: {len(all_listings)}")
                
                # Pause aléatoire entre les pages
                if page < max_pages:
                    wait_time = random.uniform(3, 8)
                    logger.debug(f"Pause de {wait_time:.2f} secondes avant la prochaine page")
                    time.sleep(wait_time)
            
        finally:
            # Assurez-vous de fermer le navigateur à la fin
            self.close()
        
        return all_listings
    
    def handle_cookie_consent(self):
        """
        Gère la boîte de dialogue de consentement aux cookies si elle apparaît.
        """
        try:
            # Attendre un peu que la boîte de cookies apparaisse
            time.sleep(2)
            
            # Chercher le bouton "Accepter tout" et cliquer dessus s'il existe
            accept_buttons = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='as24-cmp-accept-all-button']")
            if accept_buttons:
                accept_buttons[0].click()
                logger.info("Boîte de dialogue de cookies acceptée")
                time.sleep(1)  # Attendre que la boîte se ferme
            else:
                # Essayer un autre sélecteur
                accept_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'Accepter tout') or contains(., 'Tout accepter')]")
                if accept_buttons:
                    accept_buttons[0].click()
                    logger.info("Boîte de dialogue de cookies acceptée (sélecteur alternatif)")
                    time.sleep(1)
                else:
                    logger.debug("Aucune boîte de dialogue de cookies trouvée")
        except Exception as e:
            logger.warning(f"Erreur lors de la gestion des cookies: {str(e)}")
    
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
    scraper = AutoScoutSeleniumScraper(headless=True)
    
    # Exemple de filtres
    filters = {
        'max_price': 30000
    }
    
    listings = scraper.scrape_listings(max_pages=1, **filters)
    
    for i, listing in enumerate(listings[:5]):  # Afficher les 5 premières annonces
        print(f"\nAnnonce {i+1}:")
        print(f"Titre: {listing['title']}")
        print(f"Prix: {listing['price_text']}")
        print(f"URL: {listing['url']}")
        for key, value in listing.items():
            if key not in ['title', 'price_text', 'url']:
                print(f"{key}: {value}")