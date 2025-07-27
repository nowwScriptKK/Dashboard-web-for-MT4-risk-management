from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os

# === Configuration de base ===
app = Flask(__name__,  static_folder="../CLIENT/static", static_url_path="/static")          # correspond à l'URL appelée dans le HTML
CORS(app)  # Autorise les appels cross-origin (utile pour le client web)

# === Import des endpoints ===
from showTrade import trade_bp
app.register_blueprint(trade_bp)

# === Import des endpoints ===
from showConfig import config_bp
app.register_blueprint(config_bp)

# === Import des endpoints ===
from showComments import comments_bp
app.register_blueprint(comments_bp)

@app.route('/dashboard')
def show_dashboard():
    """Affiche le fichier dashboard.html tel quel"""
    return send_from_directory("../CLIENT/", "dashboard.html")


# Si jamais tu veux une route personnalisée (optionnel)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory("../CLIENT/static", filename)

# === Point d'entrée principal ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 80))
    print(f"[INFO] Serveur API en cours d'exécution sur http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)  # debug=True pour rechargement auto
