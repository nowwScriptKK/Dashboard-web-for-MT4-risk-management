# showTrade.py
from flask import Blueprint, jsonify
import os
import json

trade_bp = Blueprint('trade', __name__)
CONFIG_PATH = os.path.join("..//data//dashboard_data.json")

@trade_bp.route('/api/trades', methods=['GET'])
def get_trades():
    """
    Endpoint pour récupérer l'historique des trades
    Auteur: Theglitchis
    
    Returns:
        Response: Un objet JSON contenant:
            - status: 'success' ou 'error'
            - data: Liste des trades historiques si succès
            - message: Message d'erreur si échec

    Structure attendue du fichier JSON:
        [
            {
                'id': 'trade123',
                'pair': 'EURUSD',
                'direction': 'BUY',
                'entry_price': 1.1234,
                'exit_price': 1.1256,
                'profit': 22,
                'timestamp': '2023-01-01T12:00:00'
            },
            ...
        ]
    """
    try:
        json_path = os.path.join(CONFIG_PATH)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({"status": "success", "data": data}), 200

    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Fichier dashboard_data.json introuvable."}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@trade_bp.route('/api/capital', methods=['GET'])
def get_capital():
    """
    Endpoint pour récupérer le capital de départ défini dans la variable d'environnement MT4_DASHBOARD_BALANCE.
    """
    capital = os.getenv('MT4_DASHBOARD_BALANCE')

    if capital is None:
        return jsonify({"status": "error", "message": "La variable d'environnement MT4_DASHBOARD_BALANCE n'est pas définie."}), 404

    try:
        # On tente de convertir en float pour plus de robustesse
        capital_float = float(capital)
    except ValueError:
        return jsonify({"status": "error", "message": "La variable MT4_DASHBOARD_BALANCE n'est pas un nombre valide."}), 400

    return jsonify({"status": "success", "capital": capital_float}), 200