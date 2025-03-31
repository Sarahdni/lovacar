# test_scraper.py
from scrapers.autoscout_scraper import AutoScoutScraper
import logging
import os

def test_autoscout_scraper():
    print("Test du scraper AutoScout24")
    
    # Configurer le logging en mode DEBUG pour plus d'informations
    logging.basicConfig(level=logging.DEBUG)
    
    scraper = AutoScoutScraper()
    
    # Exemple avec des filtres minimalistes pour un test rapide
    filters = {
        'max_price': 30000
    }
    
    # Récupérer juste la page HTML brute pour voir ce qui est retourné
    url = scraper.get_search_url(page=1, **filters)
    html_content = scraper.fetch_page(url)
    
    # Sauvegarder le HTML dans un fichier pour analyse
    with open("autoscout_response.html", "w", encoding="utf-8") as f:
        f.write(html_content if html_content else "Aucun contenu HTML récupéré")
    
    print(f"HTML enregistré dans 'autoscout_response.html'")
    
    # Essayer quand même le scraping normal
    listings = scraper.scrape_listings(max_pages=1, **filters)
    
    print(f"Nombre d'annonces récupérées: {len(listings)}")

if __name__ == "__main__":
    test_autoscout_scraper()