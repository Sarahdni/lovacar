# setup.py
import os
import sys
import subprocess

def check_mongo():
    """
    Vérifie si MongoDB est installé et en cours d'exécution.
    """
    try:
        # Vérifier si le service MongoDB est en cours d'exécution
        from pymongo import MongoClient
        client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')  # Vérification de la connexion
        
        print("✅ MongoDB est installé et en cours d'exécution")
        return True
    except Exception as e:
        print(f"❌ MongoDB n'est pas accessible: {str(e)}")
        print("   Veuillez vous assurer que MongoDB est installé et en cours d'exécution.")
        print("   Pour installer MongoDB: https://docs.mongodb.com/manual/installation/")
        print("   Pour démarrer MongoDB: `mongod`")
        return False

def check_google_credentials():
    """
    Vérifie si les credentials Google sont configurés.
    """
    credentials_dir = 'credentials'
    credentials_file = os.path.join(credentials_dir, 'gmail_credentials.json')
    
    # Créer le répertoire credentials s'il n'existe pas
    if not os.path.exists(credentials_dir):
        os.makedirs(credentials_dir)
        print(f"✅ Répertoire '{credentials_dir}' créé")
    
    # Vérifier si le fichier credentials existe
    if os.path.exists(credentials_file):
        print(f"✅ Fichier '{credentials_file}' trouvé")
        return True
    else:
        print(f"❌ Fichier '{credentials_file}' non trouvé")
        print("   Veuillez suivre ces étapes pour créer vos credentials Google:")
        print("   1. Rendez-vous sur https://console.cloud.google.com/")
        print("   2. Créez un nouveau projet et activez l'API Gmail")
        print("   3. Créez des identifiants OAuth2 et téléchargez le fichier JSON")
        print(f"   4. Renommez-le en 'gmail_credentials.json' et placez-le dans le dossier '{credentials_dir}'")
        return False

def check_dependencies():
    """
    Vérifie si toutes les dépendances sont installées.
    """
    requirements_file = 'requirements.txt'
    
    if not os.path.exists(requirements_file):
        print(f"❌ Fichier '{requirements_file}' non trouvé")
        return False
    
    try:
        # Vérifier si toutes les dépendances sont installées
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
        print("✅ Toutes les dépendances sont installées")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        return False

def main():
    """
    Point d'entrée principal du script de configuration.
    """
    print("\n===== CONFIGURATION DE LOVACAR =====\n")
    
    # Vérifier les dépendances
    deps_ok = check_dependencies()
    
    # Vérifier si MongoDB est installé et en cours d'exécution
    mongo_ok = check_mongo()
    
    # Vérifier les credentials Google
    google_ok = check_google_credentials()
    
    # Afficher le résultat
    print("\n===== RÉSULTAT DE LA CONFIGURATION =====\n")
    
    if deps_ok and mongo_ok and google_ok:
        print("✅ Tout est correctement configuré ! Vous pouvez utiliser Lovacar.")
        print("   Pour commencer, exécutez: python main.py --help")
    else:
        print("❌ La configuration n'est pas complète. Veuillez corriger les problèmes ci-dessus.")
        
    print("\n=======================================\n")

if __name__ == "__main__":
    main()