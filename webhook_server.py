# webhook_server.py
from flask import Flask, request, jsonify
import os
import subprocess
import logging
from utils.helpers import logger

app = Flask(__name__)

@app.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    """
    Point d'entrée pour les notifications Gmail
    """
    try:
        logger.info("Notification Gmail reçue!")
        
        # Exécuter le script principal pour traiter les emails
        subprocess.Popen(["python", "main.py", "--scrape", "--estimate", "--calculate"])
        
        return jsonify({'status': 'success', 'message': 'Traitement démarré'}), 200
    
    except Exception as e:
        logger.error(f"Erreur dans le webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    logger.info("Démarrage du serveur webhook...")
    app.run(host='0.0.0.0', port=5000)