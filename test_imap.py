import imaplib

# Tentative de connexion
mail = imaplib.IMAP4_SSL('imap.gmail.com')
print("Connexion au serveur établie")

# Tentative d'authentification
try:
    mail.login('lovacar.waterloo@gmail.com', 'fxznahxqgeuedpik')
    print("Authentification réussie!")
    
    # Sélectionner la boîte de réception
    mail.select('INBOX')
    print("Boîte de réception sélectionnée")
    
    # Rechercher des emails
    status, messages = mail.search(None, 'ALL')
    print(f"Statut de recherche: {status}")
    print(f"Nombre d'emails trouvés: {len(messages[0].split())}")
    
    mail.logout()
except Exception as e:
    print(f"Erreur: {e}")