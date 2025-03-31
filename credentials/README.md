# Dossier de credentials

Ce dossier contient les fichiers de credentials nécessaires pour l'authentification OAuth2 avec Gmail.

## Fichiers requis

1. `gmail_credentials.json` - Fichier de credentials de l'API Google
2. `gmail_token.json` - Fichier de token généré lors de l'authentification (créé automatiquement)

## Comment obtenir le fichier gmail_credentials.json

1. Rendez-vous sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet (ou sélectionnez un projet existant)
3. Accédez à "API et services" > "Identifiants"
4. Cliquez sur "Créer des identifiants" > "ID client OAuth"
5. Configurez l'écran de consentement OAuth (Type: Externe)
6. Pour le type d'application, sélectionnez "Application de bureau"
7. Donnez un nom à votre application (par exemple, "Lovacar Gmail Scraper")
8. Cliquez sur "Créer"
9. Téléchargez le fichier JSON et renommez-le en `gmail_credentials.json`
10. Placez ce fichier dans ce dossier

## APIs Google à activer

Dans la console Google Cloud, assurez-vous d'activer les APIs suivantes:
- Gmail API

## Important

- Ne partagez jamais ces fichiers de credentials
- Ajoutez ce dossier à votre fichier .gitignore
- Pour plus de sécurité, stockez le chemin vers ces fichiers dans des variables d'environnement