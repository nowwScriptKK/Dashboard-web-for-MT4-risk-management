# tradeshowTrade.py
from flask import Blueprint, jsonify, request
from datetime import datetime
import os
import json
import traceback

comments_bp = Blueprint('comments', __name__)
CONFIG_PATH = os.path.join("..//data//comments.json")
CONFIG_PATH_TRADE = os.path.join("..//data//dashboard_data.json")

@comments_bp.route('/api/comments', methods=['GET'])
def get_comments():
    """
    Endpoint pour récupérer les commentaires et évaluations des trades
    Auteur: [Votre Nom]
    
    Returns:
        Response: Un objet JSON contenant:
            - status: 'success' ou 'error'
            - data: Dictionnaire des commentaires si succès, structuré comme :
                {
                    "comment_id": {
                        "text": "contenu du commentaire",
                        "satisfaction": note (1-10),
                        "confiance": note (1-10),
                        "attente": "analyse pré-trade",
                        "date": "YYYY.MM.DD HH:MM"
                    },
                    ...
                }
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
 
@comments_bp.route('/api/comments/edit', methods=['POST'])
def edit_comment():
    """
    Endpoint pour modifier un commentaire existant.
    Format de date requis : "YYYY.MM.DD HH:MM" (ex: "2025.07.03 17:11")
    
    Paramètres attendus (JSON ou form-data):
    - id (string): obligatoire
    - text (string): optionnel
    - satisfaction (int 0-5): optionnel
    - confiance (int 0-5): optionnel
    - attente (string): optionnel
    """
    try:
        # Essayer de récupérer JSON
        payload = request.get_json(silent=True)

        # Sinon récupérer form-data classique
        if not payload:
            payload = request.form.to_dict()

        if not payload:
            return jsonify({"status": "error", "message": "Données manquantes"}), 400

        if 'id' not in payload:
            return jsonify({"status": "error", "message": "Le paramètre 'id' est obligatoire"}), 400

        comment_id = str(payload['id'])
        editable_fields = ['text', 'satisfaction', 'confiance', 'attente']

        if not any(field in payload for field in editable_fields):
            return jsonify({"status": "error", "message": "Au moins un champ à modifier doit être fourni"}), 400

        # Chargement des commentaires existants
        if not os.path.exists(CONFIG_PATH):
            return jsonify({"status": "error", "message": "Fichier de commentaires introuvable"}), 500

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)

        if "comments" not in comments_data or comment_id not in comments_data["comments"]:
            return jsonify({"status": "error", "message": f"Commentaire ID {comment_id} introuvable"}), 404

        comment = comments_data["comments"][comment_id]

        # Modifier text
        if 'text' in payload:
            if not isinstance(payload['text'], str):
                return jsonify({"status": "error", "message": "Le texte doit être une chaîne de caractères"}), 400
            comment['text'] = payload['text'].strip()

        # Modifier satisfaction et confiance, conversion en int + validation 0-5
        for field in ['satisfaction', 'confiance']:
            if field in payload:
                try:
                    value = int(payload[field])
                except (ValueError, TypeError):
                    return jsonify({"status": "error", "message": f"Le champ {field} doit être un entier entre 0 et 5"}), 400
                if not 0 <= value <= 5:
                    return jsonify({"status": "error", "message": f"Le champ {field} doit être un entier entre 0 et 5"}), 400
                comment[field] = value

        # Modifier attente
        if 'attente' in payload:
            if not isinstance(payload['attente'], str):
                return jsonify({"status": "error", "message": "L'attente doit être une chaîne de caractères"}), 400
            comment['attente'] = payload['attente'].strip()

        # Mise à jour de la date
        comment['date'] = datetime.now().strftime("%Y.%m.%d %H:%M")

        # Sauvegarde atomique
        temp_path = f"{CONFIG_PATH}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, CONFIG_PATH)

        return jsonify({
            "status": "success",
            "updated": comment,
            "message": "Commentaire mis à jour avec succès"
        }), 200

    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Format JSON invalide"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Erreur lors de la mise à jour du commentaire"}), 500


@comments_bp.route('/api/comments/add', methods=['POST'])
def add_comment():
    """
    Endpoint pour ajouter un nouveau commentaire à un trade existant
    Requiert:
    - id: doit correspondre à un trade existant dans dashboard_data.json
    - Au moins text ou attente doit être fourni
    """
    try:
        # Essaie de récupérer JSON
        payload = request.get_json(silent=True)

        # Si pas JSON, récupère les données POST classiques
        if not payload:
            payload = request.form.to_dict()

        if not payload or 'id' not in payload:
            return jsonify({"status": "error", "message": "ID du trade requis"}), 400

        trade_id = str(payload['id'])

        # Vérification que le trade existe
        with open(CONFIG_PATH_TRADE, 'r', encoding='utf-8') as f:
            trades_data = json.load(f)

        trade_found = any(
            str(trade.get('ticket')) == trade_id
            for trade in trades_data.get('open_trades', []) + trades_data.get('closed_trades', [])
        )

        if not trade_found:
            return jsonify({"status": "error", "message": f"Trade ID {trade_id} introuvable"}), 404

        # Vérification des champs requis : au moins 'text' ou 'attente'
        if not any(field in payload and payload[field] for field in ['text', 'attente']):
            return jsonify({"status": "error", "message": "Texte ou attente requis"}), 400

        # Chargement des commentaires existants
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                comments_data = json.load(f)
        else:
            comments_data = {"comments": {}}

        # Sauvegarde du nouveau commentaire, en nettoyant/sanitisant les champs si besoin
        comments_data["comments"][trade_id] = {
            "text": payload.get('text', ''),
            "satisfaction": int(payload.get('satisfaction', 0)),
            "confiance": int(payload.get('confiance', 0)),
            "attente": payload.get('attente', ''),
            "date": datetime.now().strftime("%Y.%m.%d %H:%M")
        }

        # Sauvegarde dans le fichier
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "status": "success",
            "added": comments_data["comments"][trade_id],
            "message": "Commentaire ajouté"
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@comments_bp.route('/api/comments/delete', methods=['POST'])
def delete_comment():
    """
    Endpoint pour supprimer un commentaire existant
    Requiert:
    - id (string): ID du trade dont on veut supprimer le commentaire
    """
    try:
        # Récupération de l'ID depuis le JSON
        payload = request.get_json()
        if not payload or 'id' not in payload:
            return jsonify({"status": "error", "message": "Le paramètre 'id' est obligatoire"}), 400

        comment_id = str(payload['id'])

        # Chargement des commentaires existants
        if not os.path.exists(CONFIG_PATH):
            return jsonify({"status": "error", "message": "Aucun commentaire existant"}), 404

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)

        # Vérification que le commentaire existe
        if "comments" not in comments_data or comment_id not in comments_data["comments"]:
            return jsonify({"status": "error", "message": f"Commentaire ID {comment_id} introuvable"}), 404

        # Suppression du commentaire
        deleted_comment = comments_data["comments"].pop(comment_id)

        # Sauvegarde des modifications
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "status": "success",
            "deleted": deleted_comment,
            "message": f"Commentaire {comment_id} supprimé avec succès"
        }), 200

    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Format JSON invalide"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erreur serveur: {str(e)}"}), 500