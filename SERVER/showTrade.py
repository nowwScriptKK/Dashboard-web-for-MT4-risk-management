from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
import os
import json
from contextlib import contextmanager

trade_bp = Blueprint('trade', __name__)
DB_PATH = os.path.join('../DATA/trading.db')

# Gestionnaire de connexion sécurisé
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)  # Timeout augmenté à 30 secondes
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Gestionnaire de curseur sécurisé
@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor, conn
        finally:
            cursor.close()

def convert_sqlite_timestamp(timestamp):
    return timestamp.replace('-', '.').replace(' 0', ' ').replace(':00', '')

@trade_bp.route('/api/trades/editDB', methods=['POST'])
def edit_trade():
    try:
        data = request.get_json(force=True)
        print("Données reçues pour édition:", data)
        if 'updates' not in data:
            if 'field' in data and 'value' in data:
                data['updates'] = {data['field']: data['value']}
        if not data or 'id' not in data:
            return jsonify({"status": "error", "message": "Paramètre manquant : 'id' est requis"}), 400

        trade_id = data['id']

        if 'updates' in data:
            updates = data['updates']
            if not isinstance(updates, dict) or not updates:
                return jsonify({"status": "error", "message": "'updates' doit être un dictionnaire non vide"}), 400
        elif 'field' in data and 'value' in data:
            updates = {data['field']: data['value']}
        else:
            return jsonify({"status": "error", "message": "Format invalide : utilisez 'updates' ou 'field'/'value'"}), 400

        allowed_fields = {
            'close_price': 'float', 'close_time': 'datetime', 'comment': 'str', 'commission': 'float',
            'lots': 'float', 'open_price': 'float', 'open_time': 'datetime', 'profit': 'float',
            'sl': 'float', 'swap': 'float', 'symbol': 'str', 'tp': 'float', 'type': 'int', 'status': 'str'
        }

        invalid_fields = [f for f in updates if f not in allowed_fields]
        if invalid_fields:
            return jsonify({
                "status": "error",
                "message": f"Champs non autorisés : {', '.join(invalid_fields)}"
            }), 400

        converted_updates = {}
        for field, value in updates.items():
            try:
                if allowed_fields[field] == 'float':
                    converted_updates[field] = float(value) if value not in [None, 'null', ''] else None
                elif allowed_fields[field] == 'int':
                    converted_updates[field] = int(value) if value not in [None, 'null', ''] else None
                elif allowed_fields[field] == 'datetime':
                    if value in [None, 'null', '']:
                        converted_updates[field] = None
                    elif str(value).lower() == 'now':
                        converted_updates[field] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        dt_str = str(value).replace('.', '-', 2) if '.' in str(value) else str(value)
                        converted_updates[field] = dt_str
                else:
                    converted_updates[field] = str(value) if value not in [None, 'null', ''] else None
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erreur de conversion du champ {field}: {str(e)}"
                }), 400

        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM trades WHERE ticket = ?", (trade_id,))
            trade = cursor.fetchone()
            if not trade:
                return jsonify({"status": "error", "message": f"Trade ID {trade_id} introuvable"}), 404

            set_parts = []
            params = []
            
            for field, value in converted_updates.items():
                if field in ['close_time', 'open_time'] and value:
                    try:
                        if isinstance(value, str):
                            if ' ' in value:
                                dt_obj = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                            else:
                                dt_obj = datetime.strptime(value, "%Y-%m-%d")
                            value = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                
                set_parts.append(f"{field} = ?")
                params.append(value)

            if 'close_price' in converted_updates and 'close_time' not in converted_updates:
                if not trade['close_time']:
                    set_parts.append("close_time = CURRENT_TIMESTAMP")

            if 'open_price' in converted_updates and 'open_time' not in converted_updates:
                if not trade['open_time']:
                    set_parts.append("open_time = CURRENT_TIMESTAMP")

            set_parts.append("updated_at = CURRENT_TIMESTAMP")
            update_query = f"UPDATE trades SET {', '.join(set_parts)} WHERE ticket = ?"
            params.append(trade_id)

            cursor.execute(update_query, params)
            conn.commit()

            if 'status' in converted_updates and converted_updates['status'].lower() == 'closed':
                cursor.execute("SELECT 1 FROM unit_close_trade WHERE ticket = ?", (trade_id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO unit_close_trade (ticket, action_finish) VALUES (?, ?)", (trade_id, 1))
                    conn.commit()

            cursor.execute("SELECT * FROM trades WHERE ticket = ?", (trade_id,))
            updated = cursor.fetchone()
            
            return jsonify({
                "status": "success",
                "message": f"Trade {trade_id} mis à jour",
                "updated_fields": list(converted_updates.keys()),
                "trade": dict(updated)
            }), 200

    except Exception as e:
        print("Erreur inattendue:", str(e))
        return jsonify({
            "status": "error",
            "message": f"Erreur inattendue : {str(e)}"
        }), 500

@trade_bp.route('/api/account/update', methods=['POST'])
def update_account():
    try:
        data = request.get_json()
        if not data or 'account' not in data:
            return jsonify({"status": "error", "message": "Données manquantes"}), 400
        
        acc = data['account']
        required_fields = ['number', 'name', 'currency', 'leverage', 
                          'balance', 'equity', 'free_margin', 'margin']
        
        if not all(field in acc for field in required_fields):
            return jsonify({"status": "error", "message": "Champs manquants"}), 400
        
        acc_data = {
            'number': int(acc['number']),
            'name': str(acc['name']),
            'currency': str(acc['currency']),
            'leverage': int(acc['leverage']),
            'balance': float(acc['balance']),
            'equity': float(acc['equity']),
            'free_margin': float(acc['free_margin']),
            'margin': float(acc['margin'])
        }
        
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT number FROM accounts WHERE number = ?", (acc_data['number'],))
            exists = cursor.fetchone()
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if exists:
                query = """
                    UPDATE accounts SET
                        name = ?,
                        currency = ?,
                        leverage = ?,
                        balance = ?,
                        equity = ?,
                        free_margin = ?,
                        margin = ?,
                        updated_at = ?
                    WHERE number = ?
                """
                params = (
                    acc_data['name'],
                    acc_data['currency'],
                    acc_data['leverage'],
                    acc_data['balance'],
                    acc_data['equity'],
                    acc_data['free_margin'],
                    acc_data['margin'],
                    now,
                    acc_data['number']
                )
            else:
                query = """
                    INSERT INTO accounts (
                        number, name, currency, leverage, balance, 
                        equity, free_margin, margin, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    acc_data['number'],
                    acc_data['name'],
                    acc_data['currency'],
                    acc_data['leverage'],
                    acc_data['balance'],
                    acc_data['equity'],
                    acc_data['free_margin'],
                    acc_data['margin'],
                    now,
                    now
                )
            
            cursor.execute(query, params)
            conn.commit()
            
            return jsonify({"status": "success", "message": "Compte mis à jour"}), 200
            
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Type error: {str(e)}"}), 400
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"SQLite error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@trade_bp.route('/api/tradesDB', methods=['GET'])
def get_tradesDB():
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM accounts LIMIT 1")
            account = cursor.fetchone()
            
            if not account:
                return jsonify({"status": "error", "message": "Aucun compte trouvé dans la base de données"}), 404
            
            account_data = {
                "balance": account['balance'],
                "currency": account['currency'],
                "equity": account['equity'],
                "free_margin": account['free_margin'],
                "leverage": account['leverage'],
                "margin": account['margin'],
                "name": account['name'],
                "number": account['number']
            }
            
            cursor.execute("""
                SELECT * FROM trades 
                WHERE close_time IS NOT NULL
                ORDER BY close_time DESC
            """)
            closed_trades = []
            for trade in cursor.fetchall():
                closed_trades.append({
                    "close_price": trade['close_price'],
                    "close_time": convert_sqlite_timestamp(trade['close_time']),
                    "comment": trade['comment'] if trade['comment'] else "",
                    "commission": trade['commission'],
                    "lots": trade['lots'],
                    "open_price": trade['open_price'],
                    "open_time": convert_sqlite_timestamp(trade['open_time']),
                    "profit": trade['profit'],
                    "sl": trade['sl'],
                    "swap": trade['swap'],
                    "symbol": trade['symbol'] if trade['symbol'] else "",
                    "ticket": trade['ticket'],
                    "tp": trade['tp'],
                    "type": trade['type']
                })
            
            cursor.execute("""
                SELECT * FROM trades 
                WHERE close_time IS NULL
                ORDER BY open_time DESC
            """)
            open_trades = []
            for trade in cursor.fetchall():
                open_trades.append({
                    "comment": trade['comment'] if trade['comment'] else "",
                    "commission": trade['commission'],
                    "lots": trade['lots'],
                    "open_price": trade['open_price'],
                    "open_time": convert_sqlite_timestamp(trade['open_time']),
                    "profit": trade['profit'],
                    "sl": trade['sl'],
                    "swap": trade['swap'],
                    "symbol": trade['symbol'],
                    "ticket": trade['ticket'],
                    "tp": trade['tp'],
                    "type": trade['type']
                })
            
            return jsonify({
                "data": {
                    "account": account_data,
                    "closed_trades": closed_trades,
                    "open_trades": open_trades
                }
            }), 200

    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erreur SQLite: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@trade_bp.route('/api/trades/closesDB', methods=['GET'])
def tradeCloseDB():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'status': 'error', 'message': 'Requête JSON vide ou invalide'}), 400

        trade_id = data.get('id')
        if trade_id is None:
            return jsonify({'status': 'error', 'message': 'ID de trade manquant dans la requête'}), 400

        try:
            trade_id = int(trade_id)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'ID invalide (doit être un entier)'}), 400

        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT ticket FROM trades WHERE ticket = ?", (trade_id,))
            trade_exists = cursor.fetchone()
            if not trade_exists:
                return jsonify({'status': 'error', 'message': f"Trade ID {trade_id} introuvable dans 'trades'"}), 404

            cursor.execute("DELETE FROM unit_close_trade WHERE ticket = ?", (trade_id,))
            cursor.execute('''
                INSERT INTO unit_close_trade (ticket, action_finish)
                VALUES (?, ?)
            ''', (trade_id, 0))
            conn.commit()

            return jsonify({'status': 'success', 'id': trade_id}), 200

    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f"Erreur SQLite: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@trade_bp.route('/api/trades/pending_closes', methods=['POST'])
def get_pending_closes():
    try:
        data = request.get_json()
        if not data or 'open_tickets' not in data:
            return jsonify({"status": "error", "message": "Données invalides"}), 400

        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT ticket FROM unit_close_trade WHERE action_finish = 0")
            pending_tickets = [row[0] for row in cursor.fetchall()]
            
            open_tickets = set(data['open_tickets'])
            tickets_to_close = [t for t in pending_tickets if t in open_tickets]
            
            return jsonify({
                "status": "success",
                "tickets_to_close": tickets_to_close
            }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@trade_bp.route('/api/account/editDB', methods=['POST'])
def edit_account_db():
    try:
        data = request.get_json()
        if not data or 'account' not in data:
            return jsonify({"status": "error", "message": "Données manquantes"}), 400
        
        return update_account()
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@trade_bp.route('/api/capitalDB', methods=['GET'])
def get_capitalDB():
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT balance FROM accounts LIMIT 1")
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    "status": "error", 
                    "message": "Aucun compte trouvé dans la base de données"
                }), 404
                
            capital = float(result[0])
            return jsonify({
                "status": "success", 
                "capital": capital
            }), 200

    except sqlite3.Error as e:
        return jsonify({
            "status": "error", 
            "message": f"Erreur SQLite: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@trade_bp.route('/api/trades/add', methods=['POST'])
def add_trade():
    try:
        print(f"\nRequête brute reçue: {request.data}")
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    "status": "error",
                    "message": "Données JSON manquantes ou invalides"
                }), 400
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Erreur de parsing JSON: {str(e)}"
            }), 400

        print(f"Données parsées: {data}")

        if 'ticket' not in data:
            return jsonify({
                "status": "error",
                "message": "Le champ 'ticket' est obligatoire"
            }), 400

        def safe_convert(value, target_type, default=None):
            if value is None:
                return default
            try:
                return target_type(value)
            except (ValueError, TypeError):
                return default

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade = {
            'ticket': int(data['ticket']),
            'account_id': safe_convert(data.get('account_number'), int, 0),
            'symbol': safe_convert(data.get('symbol'), str, 'UNKNOWN'),
            'type': safe_convert(data.get('type'), int, 0),
            'lots': safe_convert(data.get('lots'), float),
            'open_price': safe_convert(data.get('open_price'), float),
            'close_price': safe_convert(data.get('close_price'), float),
            'sl': safe_convert(data.get('sl'), float),
            'tp': safe_convert(data.get('tp'), float),
            'profit': safe_convert(data.get('profit'), float),
            'swap': safe_convert(data.get('swap'), float),
            'commission': safe_convert(data.get('commission'), float),
            'comment': safe_convert(data.get('comment'), str, ''),
            'status': 'active',
            'printer': 'trade_printer',
            'created_at': current_time,
            'updated_at': current_time
        }

        try:
            trade['open_time'] = datetime.strptime(
                data.get('open_time', '').replace('.', '-', 2), 
                "%Y-%m-%d %H:%M:%S"
            ) if data.get('open_time') else datetime.now()
        except:
            trade['open_time'] = datetime.now()

        try:
            trade['close_time'] = datetime.strptime(
                data.get('close_time', '').replace('.', '-', 2),
                "%Y-%m-%d %H:%M:%S"
            ) if data.get('close_time') else None
        except:
            trade['close_time'] = None

        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT 1 FROM trades WHERE ticket = ?", (trade['ticket'],))
            if cursor.fetchone():
                return jsonify({
                    "status": "success",
                    "message": f"Trade {trade['ticket']} existe déjà",
                    "trade_id": trade['ticket']
                }), 200

            cursor.execute("""
            INSERT INTO trades (
                ticket, account_id, symbol, type, lots, 
                open_price, close_price, open_time, close_time,
                sl, tp, profit, swap, commission, comment,
                status, printer, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['ticket'],
                trade['account_id'],
                trade['symbol'],
                trade['type'],
                trade['lots'],
                trade['open_price'],
                trade['close_price'],
                trade['open_time'].strftime("%Y-%m-%d %H:%M:%S"),
                trade['close_time'].strftime("%Y-%m-%d %H:%M:%S") if trade['close_time'] else None,
                trade['sl'],
                trade['tp'],
                trade['profit'],
                trade['swap'],
                trade['commission'],
                trade['comment'],
                trade['status'],
                0,
                trade['created_at'],
                trade['updated_at']
            ))

            conn.commit()
            return jsonify({
                "status": "success",
                "message": "Trade ajouté",
                "trade_id": trade['ticket']
            }), 201

    except sqlite3.Error as e:
        print(f"Erreur SQLite: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Erreur base de données: {str(e)}"
        }), 500
    except Exception as e:
        print(f"Erreur globale: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Erreur inattendue: {str(e)}"
        }), 500

@trade_bp.route('/debug', methods=['GET', 'POST'])
def debug_endpoint():
    print(f"\n[DEBUG] Headers: {request.headers}")
    print(f"[DEBUG] Data: {request.data}")
    print(f"[DEBUG] Args: {request.args}")
    print(f"[DEBUG] Form: {request.form}\n")
    return jsonify({"status": "debug_ok"}), 200

def convert_mt4_time(mt4_time_str):
    if not mt4_time_str or mt4_time_str.lower() in ['null', 'none', '']:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if '.' in mt4_time_str:
            return datetime.strptime(mt4_time_str, "%Y.%m.%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        else:
            return datetime.strptime(mt4_time_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_float(value):
    if value is None or str(value).lower() in ['null', 'none', '']:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0