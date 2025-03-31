# database/mongo_database.py
import os
import logging
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure

from utils.helpers import logger

class MongoDatabase:
    """
    Gestion de la base de données MongoDB pour Lovacar.
    """
    
    def __init__(self, host='localhost', port=27017, db_name='lovacar'):
        """
        Initialise la connexion à MongoDB.
        
        Args:
            host (str): Hôte MongoDB
            port (int): Port MongoDB
            db_name (str): Nom de la base de données
        """
        self.host = host
        self.port = port
        self.db_name = db_name
        self.client = None
        self.db = None
    
    def connect(self):
        """
        Établit la connexion à MongoDB.
        
        Returns:
            bool: True si la connexion a réussi, False sinon
        """
        try:
            # Créer un client MongoDB
            self.client = MongoClient(self.host, self.port)
            
            # Vérifier la connexion
            self.client.admin.command('ping')
            
            # Sélectionner la base de données
            self.db = self.client[self.db_name]
            
            logger.info(f"Connexion établie à MongoDB: {self.host}:{self.port}/{self.db_name}")
            return True
        
        except ConnectionFailure as e:
            logger.error(f"Erreur de connexion à MongoDB: {str(e)}")
            return False
    
    def close(self):
        """
        Ferme la connexion à MongoDB.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("Connexion à MongoDB fermée")
    
    def init_database(self):
        """
        Initialise la structure de la base de données.
        
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        if not self.db:
            if not self.connect():
                return False
        
        try:
            # Créer la collection 'listings' si elle n'existe pas
            if 'listings' not in self.db.list_collection_names():
                self.db.create_collection('listings')
            
            # Créer les index
            self.db.listings.create_index([('url', 1)], unique=True)
            self.db.listings.create_index([('price', 1)])
            self.db.listings.create_index([('make', 1), ('model', 1)])
            self.db.listings.create_index([('discount_percentage', -1)])
            
            logger.info("Base de données MongoDB initialisée")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
            return False
    
    def store_listings(self, listings):
        """
        Stocke les annonces dans la base de données.
        
        Args:
            listings (list): Liste des annonces à stocker
            
        Returns:
            dict: Résultat de l'opération (nb_inserts, nb_updates)
        """
        if not self.db:
            if not self.connect():
                return {'nb_inserts': 0, 'nb_updates': 0}
        
        nb_inserts = 0
        nb_updates = 0
        
        for listing in listings:
            try:
                # Vérifier si l'annonce existe déjà
                existing = self.db.listings.find_one({'url': listing.get('url')})
                
                if existing:
                    # Mettre à jour l'annonce existante
                    listing['updated_at'] = datetime.now()
                    
                    # Conserver les champs calculés s'ils existent déjà
                    if existing.get('estimated_value'):
                        listing['estimated_value'] = existing.get('estimated_value')
                    if existing.get('suggested_offer'):
                        listing['suggested_offer'] = existing.get('suggested_offer')
                    if existing.get('discount_percentage'):
                        listing['discount_percentage'] = existing.get('discount_percentage')
                    if existing.get('contacted'):
                        listing['contacted'] = existing.get('contacted')
                    
                    self.db.listings.update_one(
                        {'_id': existing['_id']},
                        {'$set': listing}
                    )
                    
                    nb_updates += 1
                    logger.debug(f"Annonce mise à jour: {listing.get('title')}")
                else:
                    # Ajouter des champs supplémentaires
                    listing['created_at'] = datetime.now()
                    listing['updated_at'] = datetime.now()
                    listing['contacted'] = False
                    listing['visited'] = False
                    
                    # Insérer la nouvelle annonce
                    self.db.listings.insert_one(listing)
                    
                    nb_inserts += 1
                    logger.debug(f"Nouvelle annonce ajoutée: {listing.get('title')}")
            
            except DuplicateKeyError:
                # Gérer le cas où l'URL est en double (race condition)
                logger.warning(f"URL en double: {listing.get('url')}")
                continue
            
            except Exception as e:
                logger.error(f"Erreur lors du stockage de l'annonce: {str(e)}")
                continue
        
        logger.info(f"Stockage terminé: {nb_inserts} inserts, {nb_updates} updates")
        return {'nb_inserts': nb_inserts, 'nb_updates': nb_updates}
    
    def get_unestimated_listings(self, limit=10):
        """
        Récupère les annonces sans estimation de valeur.
        
        Args:
            limit (int): Nombre maximum d'annonces à récupérer
            
        Returns:
            list: Liste des annonces sans estimation
        """
        if not self.db:
            if not self.connect():
                return []
        
        try:
            cursor = self.db.listings.find(
                {'estimated_value': {'$exists': False}},
                limit=limit
            )
            
            return list(cursor)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des annonces non estimées: {str(e)}")
            return []
    
    def update_listing_estimation(self, listing_id, estimated_value):
        """
        Met à jour l'estimation de valeur d'une annonce.
        
        Args:
            listing_id: ID de l'annonce (ObjectId)
            estimated_value (int): Valeur estimée
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        if not self.db:
            if not self.connect():
                return False
        
        try:
            result = self.db.listings.update_one(
                {'_id': listing_id},
                {
                    '$set': {
                        'estimated_value': estimated_value,
                        'updated_at': datetime.now()
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'estimation: {str(e)}")
            return False
    
    def get_unprocessed_listings(self, limit=50):
        """
        Récupère les annonces qui ont une valeur estimée mais pas d'offre calculée.
        
        Args:
            limit (int): Nombre maximum d'annonces à récupérer
            
        Returns:
            list: Liste d'annonces à traiter
        """
        if not self.db:
            if not self.connect():
                return []
        
        try:
            cursor = self.db.listings.find(
                {
                    'estimated_value': {'$exists': True, '$ne': None},
                    'suggested_offer': {'$exists': False}
                },
                limit=limit
            )
            
            return list(cursor)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des annonces non traitées: {str(e)}")
            return []
    
    def update_listing_offer(self, listing_id, offer_details):
        """
        Met à jour l'annonce avec les détails de l'offre.
        
        Args:
            listing_id: ID de l'annonce (ObjectId)
            offer_details (dict): Détails de l'offre calculée
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        if not self.db:
            if not self.connect():
                return False
        
        try:
            update_data = {
                'suggested_offer': offer_details['suggested_offer'],
                'discount_percentage': offer_details['discount_percentage'],
                'updated_at': datetime.now()
            }
            
            result = self.db.listings.update_one(
                {'_id': listing_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'offre: {str(e)}")
            return False
    
    def get_best_deals(self, min_discount=10, limit=10):
        """
        Récupère les meilleures affaires selon le pourcentage de remise.
        
        Args:
            min_discount (float): Pourcentage minimum de remise
            limit (int): Nombre maximum d'annonces à récupérer
            
        Returns:
            list: Liste des meilleures affaires
        """
        if not self.db:
            if not self.connect():
                return []
        
        try:
            cursor = self.db.listings.find(
                {
                    'discount_percentage': {'$gte': min_discount},
                    'contacted': False
                }
            ).sort([('discount_percentage', DESCENDING)]).limit(limit)
            
            return list(cursor)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des meilleures affaires: {str(e)}")
            return []
    
    def mark_as_contacted(self, listing_id):
        """
        Marque une annonce comme contactée.
        
        Args:
            listing_id: ID de l'annonce (ObjectId)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        if not self.db:
            if not self.connect():
                return False
        
        try:
            result = self.db.listings.update_one(
                {'_id': listing_id},
                {
                    '$set': {
                        'contacted': True,
                        'contact_date': datetime.now()
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Erreur lors du marquage de l'annonce comme contactée: {str(e)}")
            return False

# Exemple d'utilisation
if __name__ == "__main__":
    db = MongoDatabase()
    
    if db.connect():
        db.init_database()
        
        # Exemple d'annonce
        sample_listing = {
            "title": "BMW 118 118i",
            "make": "BMW",
            "model": "118",
            "price": 12250,
            "price_text": "€ 12 250,-",
            "mileage": 116200,
            "year": 2017,
            "url": "https://www.autoscout24.be/fr/offres/bmw-118-118i-essence-7bcfed64-e58c-4fe3-8e79-862e5416d1c1",
            "source": "test",
            "scraped_at": datetime.now().isoformat()
        }
        
        result = db.store_listings([sample_listing])
        print(f"Résultat du stockage: {result}")
        
        db.close()