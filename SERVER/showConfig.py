# showTrade.py
from flask import Blueprint, jsonify, request
import os
import json

config_bp = Blueprint('config', __name__)
CONFIG_PATH = os.path.join("..//data//config.json")

@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """
    Endpoint pour récupérer la configuration actuelle
    Auteur: Theglitchis
    
    Returns:
        Response: Un objet JSON contenant:
            - status: 'success' ou 'error'
            - data: La configuration complète si succès
            - message: Message d'erreur si échec
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

@config_bp.route('/api/config/edit', methods=['POST'])
def edit_config():
    """
    Endpoint pour modifier la configuration
    Auteur: Theglitchis
    
    Paramètres (JSON):
        - closeBloc_allTrade (bool): Optionnel - Valeur booléenne pour le paramètre racine
        OU
        - section (str): Obligatoire - 'auto_stop_loss' ou 'trailing_stop'
        - enabled (bool): Optionnel - État d'activation
        - distance_pips (int): Optionnel - Valeur des pips (entier positif)
    
    Returns:
        Response: Un objet JSON contenant:
            - status: 'success' ou 'error'
            - updated: La section modifiée si succès
            - message: Message d'erreur si échec
    """
    try:
        # Charger la config existante
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        payload = request.get_json()

        # Cas spécial pour closeBloc_allTrade (pas une section mais un paramètre racine)
        if "closeBloc_allTrade" in payload:
            if not isinstance(payload["closeBloc_allTrade"], bool):
                return jsonify({"status": "error", "message": "'closeBloc_allTrade' doit être un booléen"}), 400
            config_data["config"]["closeBloc_allTrade"] = payload["closeBloc_allTrade"]
            # Écriture dans le fichier
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            return jsonify({"status": "success", "updated": {"closeBloc_allTrade": payload["closeBloc_allTrade"]}}), 200

        # Pour les sections auto_stop_loss et trailing_stop
        section = payload.get("section")
        if section not in ["auto_stop_loss", "trailing_stop"]:
            return jsonify({"status": "error", "message": f"Section '{section}' invalide. Choisissez 'auto_stop_loss' ou 'trailing_stop'"}), 400

        target = config_data["config"][section]

        # Modifier uniquement les champs fournis
        if "enabled" in payload:
            if not isinstance(payload["enabled"], bool):
                return jsonify({"status": "error", "message": "'enabled' doit être un booléen"}), 400
            target["enabled"] = payload["enabled"]

        if "distance_pips" in payload:
            dp = payload["distance_pips"]
            if not isinstance(dp, int) or dp < 0:
                return jsonify({"status": "error", "message": "'distance_pips' doit être un entier positif"}), 400
            target["distance_pips"] = dp

        # Écriture dans le fichier
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)

        return jsonify({"status": "success", "updated": config_data["config"][section]}), 200

    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Fichier config.json introuvable."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500