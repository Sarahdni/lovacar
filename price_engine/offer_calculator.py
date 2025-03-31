# price_engine/offer_calculator.py
import os
import sqlite3
import logging
from datetime import datetime

from config.settings import (
    DATABASE_PATH, MIN_DISCOUNT_PERCENTAGE, MAX_DISCOUNT_PERCENTAGE
)
from utils.helpers import logger

class OfferCalculator:
    """
    Calcule des offres stratégiques pour les véhicules en fonction 
    de leur prix affiché et de leur valeur estimée.
    """
    
    def __init__(self, min_discount=MIN_DISCOUNT_PERCENTAGE, max_discount=MAX_DISCOUNT_PERCENTAGE):
        """
        Initialise le calculateur d'offres.
        
        Args:
            min_discount (float): Pourcentage minimum de remise
            max_discount (float): Pourcentage maximum de remise
        """
        self.min_discount = min_discount
        self.max_discount = max_discount
    
    def get_unprocessed_listings(self, limit=50):
        """
        Récupère les annonces qui ont une valeur estimée mais pas d'offre calculée.
        
        Args:
            limit (int): Nombre maximum d'annonces à récupérer
            
        Returns:
            list: Liste d'annonces à traiter
        """
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM listings 
            WHERE estimated_value IS NOT NULL 
            AND suggested_offer IS NULL
            LIMIT ?
            """,
            (limit,)
        )
        
        listings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return listings
    
    def calculate_market_position(self, listing_price, estimated_value):
        """
        Calcule la position du prix de l'annonce par rapport au marché.
        
        Args:
            listing_price (int): Prix affiché de l'annonce
            estimated_value (int): Valeur estimée du véhicule
            
        Returns:
            dict: Position relative du prix (en %)
        """
        if not listing_price or not estimated_value or estimated_value == 0:
            return {
                "relative_position": 0,
                "is_overpriced": False,
                "is_underpriced": False,
                "position_percentage": 0
            }
        
        difference = listing_price - estimated_value
        position_percentage = (difference / estimated_value) * 100
        
        return {
            "relative_position": difference,
            "is_overpriced": position_percentage > 5,  # Plus de 5% au-dessus de l'estimation
            "is_underpriced": position_percentage < -5,  # Plus de 5% en dessous de l'estimation
            "position_percentage": position_percentage
        }
    
    def calculate_offer(self, listing_price, estimated_value):
        """
        Calcule une offre stratégique pour un véhicule.
        
        Args:
            listing_price (int): Prix affiché de l'annonce
            estimated_value (int): Valeur estimée du véhicule
            
        Returns:
            dict: Détails de l'offre
        """
        # Vérifier les valeurs
        if not listing_price or not estimated_value:
            return {
                "suggested_offer": None,
                "discount_amount": None,
                "discount_percentage": None,
                "market_position": None,
                "strategy": "Pas assez d'informations"
            }
        
        # Calculer la position sur le marché
        market_position = self.calculate_market_position(listing_price, estimated_value)
        position_percentage = market_position["position_percentage"]
        
        # Déterminer la stratégie d'offre
        strategy = None
        discount_percentage = None
        
        if position_percentage > 15:
            # Véhicule très surévalué
            strategy = "Forte remise - véhicule surévalué"
            discount_percentage = min(25, self.max_discount)  # Jusqu'à 25% de remise
            
        elif position_percentage > 5:
            # Véhicule légèrement surévalué
            strategy = "Remise moyenne - prix au-dessus du marché"
            discount_percentage = min(15, self.max_discount)  # Jusqu'à 15% de remise
            
        elif position_percentage > -5 and position_percentage <= 5:
            # Véhicule correctement évalué
            strategy = "Remise standard - prix conforme au marché"
            discount_percentage = self.min_discount  # Remise standard
            
        elif position_percentage <= -5:
            # Véhicule sous-évalué
            strategy = "Remise minimale - bonne affaire"
            discount_percentage = max(5, self.min_discount / 2)  # Remise minimale
        
        # Calculer l'offre
        discount_amount = int(listing_price * (discount_percentage / 100))
        suggested_offer = listing_price - discount_amount
        
        # S'assurer que l'offre n'est pas inférieure à la valeur estimée moins 10%
        min_acceptable_offer = int(estimated_value * 0.9)
        if suggested_offer < min_acceptable_offer:
            suggested_offer = min_acceptable_offer
            discount_amount = listing_price - suggested_offer
            discount_percentage = (discount_amount / listing_price) * 100
        
        return {
            "suggested_offer": suggested_offer,
            "discount_amount": discount_amount,
            "discount_percentage": discount_percentage,
            "market_position": market_position,
            "strategy": strategy
        }
    
    def update_listing_with_offer(self, listing_id, offer_details):
        """
        Met à jour l'annonce avec les détails de l'offre.
        
        Args:
            listing_id (int): ID de l'annonce
            offer_details (dict): Détails de l'offre calculée
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                UPDATE listings SET
                suggested_offer = ?,
                discount_percentage = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    offer_details["suggested_offer"],
                    offer_details["discount_percentage"],
                    listing_id
                )
            )
            
            conn.commit()
            logger.info(f"Offre mise à jour pour l'annonce {listing_id}: {offer_details['suggested_offer']}€")
            return True
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de la mise à jour de l'offre pour l'annonce {listing_id}: {str(e)}")
            return False
        
        finally:
            conn.close()
    
    def process_all_unprocessed_listings(self):
        """
        Traite toutes les annonces qui n'ont pas encore d'offre calculée.
        
        Returns:
            int: Nombre d'annonces traitées
        """
        listings = self.get_unprocessed_listings()
        processed_count = 0
        
        for listing in listings:
            listing_id = listing["id"]
            listing_price = listing["price"]
            estimated_value = listing["estimated_value"]
            
            offer_details = self.calculate_offer(listing_price, estimated_value)
            
            if offer_details["suggested_offer"] and self.update_listing_with_offer(listing_id, offer_details):
                processed_count += 1
        
        logger.info(f"Offres calculées pour {processed_count} annonces")
        return processed_count
    
    def get_best_deals(self, min_discount=10, limit=10):
        """
        Récupère les meilleures affaires selon le pourcentage de remise.
        
        Args:
            min_discount (float): Pourcentage minimum de remise
            limit (int): Nombre maximum d'annonces à récupérer
            
        Returns:
            list: Liste des meilleures affaires
        """
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM listings 
            WHERE discount_percentage >= ? 
            AND contacted = 0
            ORDER BY discount_percentage DESC
            LIMIT ?
            """,
            (min_discount, limit)
        )
        
        deals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return deals

# Exemple d'utilisation
if __name__ == "__main__":
    calculator = OfferCalculator()
    processed_count = calculator.process_all_unprocessed_listings()
    print(f"Offres calculées pour {processed_count} annonces")
    
    # Afficher les meilleures affaires
    best_deals = calculator.get_best_deals(min_discount=15)
    print(f"\nMeilleures affaires ({len(best_deals)} trouvées) :")
    
    for i, deal in enumerate(best_deals):
        print(f"\n{i+1}. {deal['make']} {deal['model']} ({deal['year']})")
        print(f"   Prix affiché: {deal['price']}€")
        print(f"   Valeur estimée: {deal['estimated_value']}€")
        print(f"   Offre suggérée: {deal['suggested_offer']}€")
        print(f"   Remise: {deal['discount_percentage']:.1f}%")