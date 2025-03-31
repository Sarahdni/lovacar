# test_selenium_scraper.py
from scrapers.selenium_scraper import AutoScoutSeleniumScraper

def test_selenium_scraper():
    print("Test du scraper Selenium pour AutoScout24")
    
    # Créer le scraper avec le mode headless (sans interface graphique)
    scraper = AutoScoutSeleniumScraper(headless=True)
    
    try:
        # Exemple avec des filtres minimalistes pour un test rapide
        filters = {
            'max_price': 30000
        }
        
        # Limiter à une seule page pour le test
        listings = scraper.scrape_listings(max_pages=1, **filters)
        
        print(f"Nombre d'annonces récupérées: {len(listings)}")
        
        # Afficher les 3 premières annonces
        for i, listing in enumerate(listings[:3]):
            print(f"\nAnnonce {i+1}:")
            print(f"Titre: {listing['title']}")
            print(f"Prix: {listing.get('price_text', 'Non spécifié')}")
            print(f"URL: {listing.get('url', 'Non spécifié')}")
            
            # Afficher les autres détails
            print("Détails supplémentaires:")
            for key, value in listing.items():
                if key not in ['title', 'price_text', 'url']:
                    print(f"  {key}: {value}")
    finally:
        # S'assurer que le navigateur est fermé, même en cas d'erreur
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.close()

if __name__ == "__main__":
    test_selenium_scraper()