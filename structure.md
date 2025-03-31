lovacar/
├── config/                 # Configuration du projet
│   └── settings.py         # Paramètres globaux
├── scrapers/               # Modules de scraping
│   ├── __init__.py
│   ├── autoscout_scraper.py
│   └── proxy_manager.py
├── data_processing/        # Traitement des données
│   ├── __init__.py
│   ├── data_cleaner.py
│   └── data_analyzer.py
├── price_engine/           # Calcul des prix
│   ├── __init__.py
│   ├── market_analyzer.py
│   └── offer_calculator.py
├── message_generator/      # Génération de messages
│   ├── __init__.py
│   └── template_engine.py
├── database/               # Gestion de la base de données
│   ├── __init__.py
│   ├── db_manager.py
│   └── models.py
├── utils/                  # Utilitaires
│   ├── __init__.py
│   └── helpers.py
├── main.py                 # Point d'entrée de l'application
├── requirements.txt        # Dépendances
└── README.md               # Documentation