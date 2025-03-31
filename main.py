# main.py
import logging
import argparse
import os
from datetime import datetime

from utils.helpers import logger
from scrapers.gmail_api_scraper import GmailApiScraper
from price_engine.value_estimator import AutoScoutValueEstimator
from price_engine.offer_calculator import OfferCalculator
from database.mongo_database import MongoDatabase
from bson.objectid import ObjectId
import time

def init_database():
    """
    Initialise la base de données MongoDB.
    
    Returns:
        MongoDatabase: Instance de la base de données initialisée
    """
    db = MongoDatabase()
    
    if db.connect():
        if db.init_database():
            logger.info("Base de données MongoDB initialisée avec succès")
        else:
            logger.error("Échec de l'initialisation de la base de données MongoDB")
    else:
        logger.error("Échec de la connexion à MongoDB")
    
    return db

def scrape_emails(db, max_emails=5, unread_only=True, mark_as_read=True):
    """
    Utilise l'API Gmail pour extraire les annonces des emails AutoScout24.
    
    Args:
        db (MongoDatabase): Instance de la base de données
        max_emails (int): Nombre maximum d'emails à traiter
        unread_only (bool): Si True, ne traite que les emails non lus
        mark_as_read (bool): Si True, marque les emails traités comme lus
        
    Returns:
        int: Nombre total d'annonces extraites et stockées
    """
    logger.info("Démarrage de l'extraction des emails via l'API Gmail...")
    
    # Initialiser le scraper Gmail
    scraper = GmailApiScraper()
    
    # Extraire les annonces des emails
    listings = scraper.process_emails(
        max_emails=max_emails, 
        unread_only=unread_only,
        mark_as_read=mark_as_read
    )
    
    if not listings:
        logger.info("Aucune annonce extraite")
        return 0
        
    # Stocker les annonces dans MongoDB
    result = db.store_listings(listings)
    
    logger.info(f"Extraction terminée: {len(listings)} annonces trouvées, {result['nb_inserts']} nouvelles, {result['nb_updates']} mises à jour")
    return result['nb_inserts'] + result['nb_updates']

def estimate_car_values(db, limit=5):
    """
    Estime la valeur des voitures qui n'ont pas encore d'estimation.
    
    Args:
        db (MongoDatabase): Instance de la base de données
        limit (int): Nombre maximum d'annonces à traiter
        
    Returns:
        int: Nombre d'annonces estimées
    """
    logger.info("Démarrage de l'estimation des valeurs...")
    
    # Récupérer les annonces sans estimation
    listings = db.get_unestimated_listings(limit=limit)
    
    if not listings:
        logger.info("Aucune annonce à estimer")
        return 0
    
    # Initialiser l'estimateur
    estimator = AutoScoutValueEstimator()
    estimated_count = 0
    
    try:
        for listing in listings:
            make = listing.get('make')
            model = listing.get('model')
            year = listing.get('year')
            mileage = listing.get('mileage')
            
            if not make or not model:
                logger.warning(f"Marque ou modèle manquant pour l'annonce {listing['_id']}")
                continue
            
            logger.info(f"Estimation pour {make} {model} ({year}, {mileage} km)")
            estimation = estimator.estimate_car_value(
                make=make,
                model=model,
                year=str(year) if year else None,
                mileage=mileage
            )
            
            if estimation and estimation.get("success"):
                # Mettre à jour l'estimation dans la base de données
                if db.update_listing_estimation(listing["_id"], estimation["avg_price"]):
                    estimated_count += 1
                    logger.info(f"Estimation mise à jour: {make} {model} = {estimation['avg_price']}€")
            else:
                error = estimation.get("error", "Raison inconnue")
                logger.warning(f"Échec de l'estimation pour {make} {model}: {error}")
            
            # Pause pour éviter de surcharger le serveur
            time.sleep(2)
    
    finally:
        # Fermer l'estimateur
        estimator.close()
    
    logger.info(f"Estimation terminée, {estimated_count} annonces estimées")
    return estimated_count

def calculate_offers(db, limit=50):
    """
    Calcule des offres pour les annonces qui ont une estimation mais pas d'offre.
    
    Args:
        db (MongoDatabase): Instance de la base de données
        limit (int): Nombre maximum d'annonces à traiter
        
    Returns:
        int: Nombre d'offres calculées
    """
    logger.info("Démarrage du calcul des offres...")
    
    # Récupérer les annonces sans offre calculée
    listings = db.get_unprocessed_listings(limit=limit)
    
    if not listings:
        logger.info("Aucune annonce à traiter")
        return 0
    
    # Initialiser le calculateur d'offres
    calculator = OfferCalculator()
    processed_count = 0
    
    for listing in listings:
        listing_id = listing["_id"]
        listing_price = listing["price"]
        estimated_value = listing["estimated_value"]
        
        # Calculer l'offre
        offer_details = calculator.calculate_offer(listing_price, estimated_value)
        
        # Mettre à jour l'offre dans la base de données
        if offer_details["suggested_offer"] and db.update_listing_offer(listing_id, offer_details):
            processed_count += 1
            logger.info(f"Offre calculée: {listing.get('make')} {listing.get('model')} = {offer_details['suggested_offer']}€")
    
    logger.info(f"Calcul terminé, {processed_count} offres calculées")
    return processed_count

def display_best_deals(db, min_discount=15, limit=5):
    """
    Affiche les meilleures affaires selon le pourcentage de remise.
    
    Args:
        db (MongoDatabase): Instance de la base de données
        min_discount (float): Pourcentage minimum de remise
        limit (int): Nombre maximum d'annonces à afficher
    """
    # Récupérer les meilleures affaires
    deals = db.get_best_deals(min_discount=min_discount, limit=limit)
    
    if not deals:
        print("\nAucune bonne affaire trouvée correspondant aux critères")
        return
    
    print(f"\n===== MEILLEURES AFFAIRES ({len(deals)} trouvées) =====")
    
    for i, deal in enumerate(deals, 1):
        make = deal.get('make', 'Inconnu')
        model = deal.get('model', 'Inconnu')
        year = deal.get('year', 'Année inconnue')
        price = deal.get('price', 0)
        estimated_value = deal.get('estimated_value', 0)
        suggested_offer = deal.get('suggested_offer', 0)
        discount_percentage = deal.get('discount_percentage', 0)
        url = deal.get('url', '#')
        
        print(f"\n{i}. {make} {model} ({year})")
        print(f"   Prix affiché: {price}€")
        print(f"   Valeur estimée: {estimated_value}€")
        print(f"   Offre suggérée: {suggested_offer}€")
        print(f"   Remise: {discount_percentage:.1f}%")
        print(f"   URL: {url}")

def main():
    """
    Point d'entrée principal de l'application.
    """
    # Configurer l'analyseur d'arguments
    parser = argparse.ArgumentParser(description="Lovacar - Automatisation des offres sur AutoScout24")
    parser.add_argument("--emails", type=int, default=5, help="Nombre maximum d'emails à traiter")
    parser.add_argument("--estimates", type=int, default=5, help="Nombre maximum d'annonces à estimer")
    parser.add_argument("--all", action="store_true", help="Exécuter tout le processus")
    parser.add_argument("--scrape", action="store_true", help="Extraire les annonces des emails")
    parser.add_argument("--estimate", action="store_true", help="Estimer les valeurs")
    parser.add_argument("--calculate", action="store_true", help="Calculer les offres")
    parser.add_argument("--deals", action="store_true", help="Afficher les meilleures affaires")
    parser.add_argument("--min-discount", type=float, default=15, help="Pourcentage minimum de remise pour les meilleures affaires")
    parser.add_argument("--mark-read", action="store_true", help="Marquer les emails comme lus après traitement")
    
    args = parser.parse_args()
    
    logger.info("Démarrage de l'application Lovacar")
    
    # Initialiser la base de données MongoDB
    db = init_database()
    
    try:
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
            scrape_emails(db, max_emails=args.emails, mark_as_read=args.mark_read)
        
        if run_estimate:
            estimate_car_values(db, limit=args.estimates)
        
        if run_calculate:
            calculate_offers(db)
        
        if run_deals:
            display_best_deals(db, min_discount=args.min_discount)
    
    finally:
        # Fermer la connexion à la base de données
        db.close()
    
    logger.info("Fin de l'application Lovacar")

if __name__ == "__main__":
    main()