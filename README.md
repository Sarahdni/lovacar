# Lovacar

Système d'automatisation pour la recherche d'annonces automobiles sur AutoScout24 et la génération d'offres de prix stratégiques.

## Objectifs

1. Scraper les annonces dans un rayon de 50 km autour de Waterloo
2. Extraire les estimations de prix et les informations du marché
3. Calculer des offres de prix stratégiques
4. Générer des messages personnalisés pour contacter les vendeurs

## Structure du projet

- `config/` : Configuration du projet
- `scrapers/` : Modules de scraping
- `data_processing/` : Traitement des données
- `price_engine/` : Calcul des prix
- `message_generator/` : Génération de messages
- `database/` : Gestion de la base de données
- `utils/` : Utilitaires

## Installation

1. Cloner le dépôt
2. Créer un environnement virtuel : `python -m venv venv`
3. Activer l'environnement virtuel : `source venv/bin/activate` (macOS/Linux) ou `venv\Scripts\activate` (Windows)
4. Installer les dépendances : `pip install -r requirements.txt`

## Utilisation

En cours de développement.

Prochaines étapes
Automatisation de la récupération des emails
Pour automatiser complètement le processus de récupération des emails AutoScout24 sans intervention manuelle, plusieurs options ont été identifiées:

Solution locale temporaire:

Mettre en place un script avec schedule qui vérifie périodiquement les nouveaux emails
Conserver l'authentification OAuth2 actuelle (nécessite une authentification manuelle initiale)


Solutions cloud (à implémenter ultérieurement):

Cloud Functions + Cloud Scheduler: Déployer une fonction serverless déclenchée à intervalles réguliers
Cloud Run + Cloud Scheduler: Alternative plus flexible pour les applications complexes
App Engine + Cron Jobs: Plateforme complète d'hébergement avec planification intégrée



Ces solutions cloud offriront:

Une exécution fiable sans besoin de serveur local ou d'ordinateur allumé
Une intégration native avec les APIs Google
Une évolutivité pour les fonctionnalités futures

TODO: Compléter l'automatisation locale avant d'implémenter la solution cloud.