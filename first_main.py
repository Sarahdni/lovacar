# main.py
import logging
import argparse
import os
import sqlite3
from datetime import datetime

from utils.helpers import logger
from scrapers.email_scraper import AutoScoutEmailScraper
from price_engine.value_estimator import AutoScoutValueEstimator
from price_engine.offer_calculator import OfferCalculator
from config.settings import DATABASE_PATH

def init_database():
    """
    Initialise la base de données si elle n'existe pas.
    """
    # S'assurer que le répertoire de la base de données existe
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Créer la table d'annonces
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        make TEXT,
        model TEXT,
        price INTEGER,
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
    
    conn.commit()
    conn.close()
    
    logger.info(f"Base de données initialisée: {DATABASE_PATH}")

def scrape_emails(max_emails=5, unread_only=True):
    """
    Scrape les emails d'alerte AutoScout24.
    
    Args:
        max_emails (int): Nombre maximum d'emails à traiter
        unread_only (bool): Si True, ne traite que les emails non lus
        
    Returns:
        int: Nombre d'annonces extraites
    """
    logger.info("Démarrage du scraping des emails...")
    scraper = AutoScoutEmailScraper()
    listings = scraper.process_emails(max_emails=max_emails, unread_only=unread_only)
    logger.info(f"Scraping terminé, {len(listings)} annonces extraites")
    return len(listings)

def get_unestimated_listings(limit=10):
    """
    Récupère les annonces sans estimation de valeur.
    
    Args:
        limit (int): Nombre maximum d'annonces à récupérer
        
    Returns:
        list: Liste des annonces sans estimation
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT * FROM listings 
        WHERE estimated_value IS NULL 
        LIMIT ?
        """,
        (limit,)
    )
    
    listings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return listings

def update_listing_estimation(listing_id, estimation):
    """
    Met à jour l'estimation de valeur d'une annonce.
    
    Args:
        listing_id (int): ID de l'annonce
        estimation (dict): Détails de l'estimation
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        estimated_value = estimation.get("avg_price")
        if not estimated_value:
            logger.warning(f"Pas de valeur moyenne trouvée pour l'annonce {listing_id}")
            return False
        
        cursor.execute(
            """
            UPDATE listings SET
            estimated_value = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (estimated_value, listing_id)
        )
        
        conn.commit()
        logger.info(f"Estimation mise à jour pour l'annonce {listing_id}: {estimated_value}€")
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la mise à jour de l'estimation pour l'annonce {listing_id}: {str(e)}")
        return False
    
    finally:
        conn.close()

def estimate_car_values(limit=5):
    """
    Estime la valeur des voitures qui n'ont pas encore d'estimation.
    
    Args:
        limit (int): Nombre maximum d'annonces à traiter
        
    Returns:
        int: Nombre d'annonces estimées
    """
    logger.info("Démarrage de l'estimation des valeurs...")
    
    listings = get_unestimated_listings(limit=limit)
    if not listings:
        logger.info("Aucune annonce à estimer")
        return 0
    
    estimator = AutoScoutValueEstimator()
    estimated_count = 0
    
    try:
        for listing in listings:
            make = listing.get("make")
            model = listing.get("model")
            year = listing.get("year")
            mileage = listing.get("mileage")
            
            if not make or not model:
                logger.warning(f"Marque ou modèle manquant pour l'annonce {listing['id']}")
                continue
            
            logger.info(f"Estimation pour {make} {model} ({year}, {mileage} km)")
            estimation = estimator.estimate_car_value(
                make=make,
                model=model,
                year=str(year) if year else None,
                mileage=mileage
            )
            
            if estimation and estimation.get("success"):
                if update_listing_estimation(listing["id"], estimation):
                    estimated_count += 1
            else:
                error = estimation.get("error", "Raison inconnue")
                logger.warning(f"Échec de l'estimation pour {make} {model}: {error}")
    
    finally:
        estimator.close()
    
    logger.info(f"Estimation terminée, {estimated_count} annonces estimées")
    return estimated_count

def calculate_offers():
    """
    Calcule des offres pour les annonces qui ont une estimation mais pas d'offre.
    
    Returns:
        int: Nombre d'offres calculées
    """
    logger.info("Démarrage du calcul des offres...")
    calculator = OfferCalculator()
    processed_count = calculator.process_all_unprocessed_listings()
    logger.info(f"Calcul terminé, {processed_count} offres calculées")
    return processed_count

def display_best_deals(min_discount=15, limit=5):
    """
    Affiche les meilleures affaires.
    
    Args:
        min_discount (float): Pourcentage minimum de remise
        limit (int): Nombre maximum d'annonces à afficher
    """
    calculator = OfferCalculator()
    best_deals = calculator.get_best_deals(min_discount=min_discount, limit=limit)
    
    print(f"\n===== MEILLEURES AFFAIRES ({len(best_deals)} trouvées) =====")
    
    for i, deal in enumerate(best_deals):
        print(f"\n{i+1}. {deal['make']} {deal['model']} ({deal['year']})")
        print(f"   Prix affiché: {deal['price']}€")
        print(f"   Valeur estimée: {deal['estimated_value']}€")
        print(f"   Offre suggérée: {deal['suggested_offer']}€")
        print(f"   Remise: {deal['discount_percentage']:.1f}%")
        print(f"   URL: {deal['url']}")

def main():
    """
    Point d'entrée principal de l'application.
    """
    parser = argparse.ArgumentParser(description="Lovacar - Automatisation des offres sur AutoScout24")
    parser.add_argument("--emails", type=int, default=5, help="Nombre maximum d'emails à traiter")
    parser.add_argument("--estimates", type=int, default=5, help="Nombre maximum d'annonces à estimer")
    parser.add_argument("--all", action="store_true", help="Exécuter tout le processus")
    parser.add_argument("--scrape", action="store_true", help="Scraper les emails")
    parser.add_argument("--estimate", action="store_true", help="Estimer les valeurs")
    parser.add_argument("--calculate", action="store_true", help="Calculer les offres")
    parser.add_argument("--deals", action="store_true", help="Afficher les meilleures affaires")
    parser.add_argument("--min-discount", type=float, default=15, help="Pourcentage minimum de remise pour les meilleures affaires")
    
    args = parser.parse_args()
    
    logger.info("Démarrage de l'application Lovacar")
    
    # Initialiser la base de données si nécessaire
    init_database()
    
    # Déterminer les actions à exécuter
    run_scrape = args.all or args.scrape
    run_estimate = args.all or args.estimate
    run_calculate = args.all or args.calculate
    run_deals = args.all or args.deals
    
    # Si aucune action spécifiée, afficher l'aide
    if not (run_scrape or run_estimate or run_calculate or run_deals):
        parser.print_help()
        return
    
    # Exécuter les actions demandées
    if run_scrape:
        scrape_emails(max_emails=args.emails)
    
    if run_estimate:
        estimate_car_values(limit=args.estimates)
    
    if run_calculate:
        calculate_offers()
    
    if run_deals:
        display_best_deals(min_discount=args.min_discount)
    
    logger.info("Fin de l'application Lovacar")

if __name__ == "__main__":
    main()