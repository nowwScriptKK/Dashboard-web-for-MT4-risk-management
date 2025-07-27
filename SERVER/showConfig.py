# showTrade.py
from flask import Blueprint, jsonify, request
import sqlite3
import os
import json

config_bp = Blueprint('config', __name__)
CONFIG_PATH = os.path.join("..//data//config.json")



@config_bp.route('/api/configDB', methods=['GET'])
def get_configDB():
    """
    Endpoint pour récupérer la configuration actuelle depuis SQLite
    Auteur: Theglitchis
    
    Returns:
        Response: Un objet JSON contenant:
            - status: 'success' ou 'error'
            - data: La configuration complète si succès
            - message: Message d'erreur si échec
    """
    try:
        # Chemin vers la base de données SQLite
        db_path = os.path.join('..', 'DATA', 'trading.db')
        
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Récupération de la configuration
        cursor.execute("SELECT * FROM config")
        config_row = cursor.fetchone()
        
        # Fermeture de la connexion
        conn.close()
        
        if config_row is None:
            return jsonify({"status": "error", "message": "Configuration introuvable dans la base de données"}), 404
        
        # Mapping des colonnes (selon la structure de la table config)
        columns = [
            'id',
            'auto_stop_loss_enabled',
            'auto_stop_loss_distance_pips',
            'trailing_stop_enabled',
            'trailing_stop_distance_pips',
            'closeBloc_allTrade',
            'status',
            'printer',
            'created_at',
            'updated_at'
        ]
        
        # Création d'un dictionnaire à partir des résultats
        config_data = dict(zip(columns, config_row))
        
        # Formatage des données pour correspondre à l'ancienne structure JSON
        formatted_data = {
            "config": {
                "auto_stop_loss": {
                    "enabled": bool(config_data['auto_stop_loss_enabled']),
                    "distance_pips": config_data['auto_stop_loss_distance_pips']
                },
                "trailing_stop": {
                    "enabled": bool(config_data['trailing_stop_enabled']),
                    "distance_pips": config_data['trailing_stop_distance_pips']
                },
                "closeBloc_allTrade": bool(config_data['closeBloc_allTrade'])
            }
        }
        
        return jsonify({
            "status": "success",
            "data": formatted_data
        }), 200

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite: {str(e)}"}), 500
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@config_bp.route('/api/config/editDB', methods=['POST'])
def edit_configDB():
    """
    Endpoint pour modifier la configuration dans la base de données SQLite
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
        payload = request.get_json()
        print(f"Received payload: {payload}")
        db_path = os.path.join('..', 'DATA', 'trading.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Vérifier/Créer la configuration si elle n'existe pas
        cursor.execute("SELECT 1 FROM config WHERE id = 'global_config'")
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO config (id) 
            VALUES ('global_config')
            ''')
            conn.commit()
            print("Configuration initiale créée")

        # Cas spécial pour closeBloc_allTrade
        if "closeBloc_allTrade" in payload:
            if not isinstance(payload["closeBloc_allTrade"], bool):
                conn.close()
                return jsonify({"status": "error", "message": "'closeBloc_allTrade' doit être un booléen"}), 400
            
            cursor.execute('''
            UPDATE config 
            SET closeBloc_allTrade = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 'global_config'
            ''', (int(payload["closeBloc_allTrade"]),))
            
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "updated": {"closeBloc_allTrade": payload["closeBloc_allTrade"]}}), 200

        # Pour les sections auto_stop_loss et trailing_stop
        section = payload.get("section")
        if section not in ["auto_stop_loss", "trailing_stop"]:
            conn.close()
            return jsonify({"status": "error", "message": f"Section '{section}' invalide. Choisissez 'auto_stop_loss' ou 'trailing_stop'"}), 400

        # Récupérer les valeurs actuelles
        cursor.execute("SELECT * FROM config WHERE id = 'global_config'")
        current_data = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        current_config = dict(zip(columns, current_data))

        # Préparer les mises à jour
        updates = []
        values = []
        
        # Mapper les champs à leurs colonnes SQL
        field_map = {
            "auto_stop_loss": {
                "enabled": "auto_stop_loss_enabled",
                "distance_pips": "auto_stop_loss_distance_pips"
            },
            "trailing_stop": {
                "enabled": "trailing_stop_enabled",
                "distance_pips": "trailing_stop_distance_pips"
            }
        }

        # Vérifier et ajouter les champs à mettre à jour
        if "enabled" in payload:
            if not isinstance(payload["enabled"], bool):
                conn.close()
                return jsonify({"status": "error", "message": "'enabled' doit être un booléen"}), 400
            col_name = field_map[section]["enabled"]
            updates.append(f"{col_name} = ?")
            values.append(int(payload["enabled"]))

        if "distance_pips" in payload:
            dp = payload["distance_pips"]
            if not isinstance(dp, int) or dp < 0:
                conn.close()
                return jsonify({"status": "error", "message": "'distance_pips' doit être un entier positif"}), 400
            col_name = field_map[section]["distance_pips"]
            updates.append(f"{col_name} = ?")
            values.append(dp)

        # S'il n'y a rien à mettre à jour
        if not updates:
            conn.close()
            return jsonify({"status": "error", "message": "Aucun champ valide à mettre à jour"}), 400

        # Construire la requête SQL
        set_clause = ", ".join(updates)
        query = f'''
        UPDATE config 
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = 'global_config'
        '''
        
        # Exécuter la mise à jour
        cursor.execute(query, tuple(values))
        conn.commit()
        conn.close()

        # Formater la réponse
        updated_data = {}
        if "enabled" in payload:
            updated_data["enabled"] = payload["enabled"]
        if "distance_pips" in payload:
            updated_data["distance_pips"] = payload["distance_pips"]

        return jsonify({
            "status": "success", 
            "updated": {section: updated_data}
        }), 200

    except sqlite3.Error as e:
        print(f"SQLite error: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return jsonify({"status": "error", "message": f"Erreur SQLite: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500