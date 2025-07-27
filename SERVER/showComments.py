# tradeshowTrade.py
from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
import os
import json
import traceback

comments_bp = Blueprint('comments', __name__)
DBPATH = os.path.join('../DATA/trading.db')
@comments_bp.route('/api/commentsDB', methods=['GET'])
def get_commentsDB():
    """
    Endpoint pour récupérer les commentaires et évaluations des trades depuis la base de données.

    Returns:
        JSON: {
            status: "success" | "error",
            data: {
                "id": {
                    "text": "...",
                    "satisfaction": int,
                    "confiance": int,
                    "attente": "...",
                    "date": "...",
                    "status": "...",
                    "printer": "...",
                    "created_at": "...",
                    "updated_at": "..."
                },
                ...
            }
        }
    """
    try:
        # Connexion à la base SQLite
        db_path = DBPATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # pour accès par nom de colonne
        cursor = conn.cursor()

        # Récupération des commentaires
        cursor.execute("SELECT * FROM comments")
        rows = cursor.fetchall()
        conn.close()

        # Construction de la réponse JSON
        comments = {}
        for row in rows:
            comments[str(row["id"])] = {
                "text": row["text"] or "",
                "satisfaction": int(row["satisfaction"]) if row["satisfaction"] is not None else 0,
                "confiance": int(row["confiance"]) if row["confiance"] is not None else 0,
                "attente": row["attente"] or "",
                "date": row["date"] or "",
                "status": row["status"] or "",
                "printer": row["printer"] or "",
                "created_at": row["created_at"] or "",
                "updated_at": row["updated_at"] or ""
            }

        return jsonify({"status": "success", "data": comments}), 200

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@comments_bp.route('/api/comments/editDB', methods=['POST'])
def edit_commentDB():
    """
    Modifier un commentaire existant dans la base de données SQLite.
    Champs modifiables : text, satisfaction (0-5), confiance (0-5), attente
    """
    try:
        # Lecture du payload JSON ou form-data
        payload = request.get_json(silent=True)
        if not payload:
            payload = request.form.to_dict()

        if not payload:
            return jsonify({"status": "error", "message": "Données manquantes"}), 400

        if 'id' not in payload:
            return jsonify({"status": "error", "message": "Le paramètre 'id' est obligatoire"}), 400

        try:
            comment_id = int(payload['id'])
        except ValueError:
            return jsonify({"status": "error", "message": "ID invalide (doit être un entier)"}), 400

        # Champs modifiables
        editable_fields = ['text', 'satisfaction', 'confiance', 'attente']
        update_data = {}
        for field in editable_fields:
            if field in payload:
                if field in ['text', 'attente']:
                    if not isinstance(payload[field], str):
                        return jsonify({"status": "error", "message": f"Le champ {field} doit être une chaîne"}), 400
                    update_data[field] = payload[field].strip()
                elif field in ['satisfaction', 'confiance']:
                    try:
                        value = int(payload[field])
                    except ValueError:
                        return jsonify({"status": "error", "message": f"Le champ {field} doit être un entier"}), 400
                    if not 0 <= value <= 5:
                        return jsonify({"status": "error", "message": f"Le champ {field} doit être entre 0 et 5"}), 400
                    update_data[field] = value

        if not update_data:
            return jsonify({"status": "error", "message": "Aucun champ à modifier fourni"}), 400

        # Connexion DB
        db_path = os.path.abspath(os.path.join('..', 'DATA', 'trading.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Vérifier que le commentaire existe
        cursor.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            return jsonify({"status": "error", "message": f"Commentaire ID {comment_id} introuvable"}), 404

        # Construire la requête UPDATE dynamiquement
        set_clause = ', '.join(f"{key} = ?" for key in update_data)
        values = list(update_data.values())
        values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # updated_at
        values.append(comment_id)

        sql = f"UPDATE comments SET {set_clause}, updated_at = ? WHERE id = ?"
        cursor.execute(sql, values)
        conn.commit()

        # Retourner le commentaire mis à jour
        cursor.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
        updated_comment = dict(cursor.fetchone())

        conn.close()

        return jsonify({
            "status": "success",
            "updated": updated_comment,
            "message": "Commentaire mis à jour avec succès"
        }), 200

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite: {str(e)}"}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Erreur inattendue lors de la mise à jour"}), 500

@comments_bp.route('/api/comments/addDB', methods=['POST'])
def add_commentDB():
    """
    Ajouter un nouveau commentaire dans la base de données.
    - Requiert : id (doit correspondre à un trade existant dans la table 'trades')
    - Au moins un des champs : text ou attente
    - Remplace le commentaire existant si l'ID est déjà présent
    """
    try:
        # Récupération des données
        payload = request.get_json(silent=True) or request.form.to_dict()
        if not payload or 'id' not in payload:
            return jsonify({"status": "error", "message": "ID du trade requis"}), 400

        try:
            trade_id = int(payload['id'])
        except ValueError:
            return jsonify({"status": "error", "message": "ID invalide"}), 400

        # Connexion à la base
        db_path = os.path.abspath(os.path.join('..', 'DATA', 'trading.db'))
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Vérifie que le trade existe
        cursor.execute("SELECT ticket FROM trades WHERE ticket = ?", (trade_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": f"Trade ID {trade_id} introuvable"}), 404

        # Vérifie qu'au moins text ou attente est fourni
        if not any(payload.get(field) for field in ['text', 'attente']):
            return jsonify({"status": "error", "message": "Texte ou attente requis"}), 400

        # Préparation des champs
        text = payload.get('text', '').strip()
        attente = payload.get('attente', '').strip()
        satisfaction = int(payload.get('satisfaction', 0))
        confiance = int(payload.get('confiance', 0))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_human = datetime.now().strftime("%Y.%m.%d %H:%M")

        # Remplace ou insère
        cursor.execute("""
            INSERT INTO comments (id, text, satisfaction, confiance, attente, date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                text=excluded.text,
                satisfaction=excluded.satisfaction,
                confiance=excluded.confiance,
                attente=excluded.attente,
                date=excluded.date,
                updated_at=excluded.updated_at
        """, (trade_id, text, satisfaction, confiance, attente, date_human, now, now))

        conn.commit()

        # Retour du commentaire ajouté ou mis à jour
        cursor.execute("SELECT * FROM comments WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()

        added = {
            "id": row[0],
            "text": row[1],
            "satisfaction": row[2],
            "confiance": row[3],
            "attente": row[4],
            "date": row[5],
            "status": row[6],
            "printer": row[7],
            "created_at": row[8],
            "updated_at": row[9]
        }

        return jsonify({
            "status": "success",
            "added": added,
            "message": f"Commentaire {'ajouté' if row else 'remplacé'}"
        }), 201

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite : {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erreur serveur : {str(e)}"}), 500

@comments_bp.route('/api/comments/deleteDB', methods=['POST'])
def delete_commentDB():
    """
    Supprimer un commentaire existant dans la base de données.
    - Requiert : id
    """
    try:
        payload = request.get_json()
        if not payload or 'id' not in payload:
            return jsonify({"status": "error", "message": "Le paramètre 'id' est obligatoire"}), 400

        try:
            comment_id = int(payload['id'])
        except ValueError:
            return jsonify({"status": "error", "message": "ID invalide"}), 400

        db_path = os.path.abspath(os.path.join('..', 'DATA', 'trading.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Vérifie si le commentaire existe
        cursor.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "error", "message": f"Commentaire ID {comment_id} introuvable"}), 404

        # Supprime le commentaire
        cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "deleted_id": comment_id,
            "message": f"Commentaire {comment_id} supprimé avec succès"
        }), 200

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite : {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erreur serveur : {str(e)}"}), 500
