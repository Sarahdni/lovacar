# test_gmail_oauth_fixed.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import imaplib
import base64
import json
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lovacar")

# Paramètres
SCOPES = ['https://mail.google.com/']
GMAIL_CREDENTIALS_PATH = 'credentials/gmail_credentials.json'
GMAIL_TOKEN_PATH = 'credentials/gmail_token.json'
EMAIL_ACCOUNT = 'lovacar.waterloo@gmail.com'  # Remplacez par votre adresse email

def get_credentials():
    """
    Obtient les credentials OAuth2 pour Gmail.
    """
    creds = None
    
    # Vérifier si les tokens existent et sont valides
    if os.path.exists(GMAIL_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(GMAIL_TOKEN_PATH)), 
                SCOPES
            )
            logger.info("Token existant chargé.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du token: {str(e)}")
            creds = None
    
    # Si pas de credentials valides, démarrer le flux d'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Tokens rafraîchis avec succès")
            except Exception as e:
                logger.warning(f"Impossible de rafraîchir le token: {str(e)}")
                creds = None
        
        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Fichier de credentials Google non trouvé: {GMAIL_CREDENTIALS_PATH}"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_PATH, 
                SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("Nouvelle authentification réussie")
            
            # Sauvegarder les tokens pour la prochaine fois
            with open(GMAIL_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Tokens sauvegardés dans {GMAIL_TOKEN_PATH}")
    
    return creds

def test_gmail_connection():
    """
    Teste la connexion à Gmail avec OAuth2 - version corrigée
    """
    print("Test de connexion OAuth2 à Gmail")
    
    try:
        # Obtenir les credentials
        creds = get_credentials()
        if not creds:
            print("❌ Échec de l'obtention des credentials")
            return False
        
        # Créer une connexion IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        
        # CORRECTION: Format correct de la chaîne d'authentification OAuth2
        # Utiliser l'email et le token d'accès (pas le client_id)
        auth_string = f'user={EMAIL_ACCOUNT}\x01auth=Bearer {creds.token}\x01\x01'
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        # Authentification
        status, response = mail.authenticate('XOAUTH2', lambda x: auth_b64)
        
        if status == 'OK':
            print("✅ Connexion réussie!")
            
            # Tester la sélection d'un dossier
            mail.select('INBOX')
            print("✅ Dossier INBOX sélectionné")
            
            # Rechercher quelques emails
            status, messages = mail.search(None, 'ALL')
            print(f"✅ Recherche d'emails: {status}")
            print(f"✅ Nombre d'emails trouvés: {len(messages[0].split())}")
            
            # Rechercher spécifiquement les emails d'AutoScout24
            status, messages = mail.search(None, '(FROM "no-reply@rtm.autoscout24.com")')
            print(f"✅ Emails d'AutoScout24 trouvés: {len(messages[0].split())}")
            
            # Déconnexion
            mail.logout()
            print("✅ Déconnexion réussie")
            return True
        else:
            print(f"❌ Échec de l'authentification: {response}")
            return False
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

if __name__ == "__main__":
    # S'assurer que le dossier credentials existe
    os.makedirs(os.path.dirname(GMAIL_CREDENTIALS_PATH), exist_ok=True)
    
    # Tester la connexion
    test_gmail_connection()