# price_engine/offer_calculator.py
import os
import logging
from datetime import datetime

from config.settings import (
    MIN_DISCOUNT_PERCENTAGE, MAX_DISCOUNT_PERCENTAGE
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

# Exemple d'utilisation direct (pour les tests)
if __name__ == "__main__":
    calculator = OfferCalculator()
    
    # Exemple de calcul d'offre
    listing_price = 15000
    estimated_value = 13000
    
    offer = calculator.calculate_offer(listing_price, estimated_value)
    
    print(f"Prix affiché: {listing_price}€")
    print(f"Valeur estimée: {estimated_value}€")
    print(f"Position sur le marché: {offer['market_position']['position_percentage']:.1f}%")
    print(f"Stratégie: {offer['strategy']}")
    print(f"Remise calculée: {offer['discount_percentage']:.1f}% ({offer['discount_amount']}€)")
    print(f"Offre suggérée: {offer['suggested_offer']}€")