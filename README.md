### ⏳ Changement à venir :
- **Correction script MQ4** Correction de la mise à jour du TP suite a une modification manuel sur le trade dans le script MQ4.
- **Refonte complète JavaScript** Correction de la mise à jour du des calcul RR etc côté javascript + refonte complète du script .js refactorisation pour avoir une cohérence complète avec l'architecture modulaire du projet.
- **Ré-implémentation de l'automatisation de prise de trade** Suite a la dernière mise à jour les fonctionnalité de TP/SL, fermeture de toutes les positions etc on était temporairement mis en pause, il est necessaire de retaper le JS pour avoir une belle cohérence des données

<center><img src="https://github.com/nowwScriptKK/Dashboard-web-for-MT4-risk-management/blob/main/CAPTURE2.png" style="text-align: center;" alt="Texte alternatif"></center>

## ⚙️ Configuration initiale

### Étapes :

1. **Installer Python 3.13+**
2. **Configurer le fichier `config.cmd`** :
   - Clic droit → Modifier
   - Modifier cette ligne :
     ```cmd
     set "MT4_PATH=C:\Users\1234\AppData\Roaming\MetaQuotes\Terminal\XXXXXX\MQL4"
     ```
     > Pour trouver ce chemin, ouvrir MT4 → Fichier → *Ouvrir le dossier des données* → Copier le chemin jusqu’à `MQL4`
   - Facultatif : personnaliser le solde de départ
     ```cmd
     set "STARTING_BALANCE=10000"
     ```
3. **Lancer `config.cmd` en tant qu’administrateur**
4. **Charger l’Expert Advisor** dans MT4 :
   - Copier les fichiers du dossier `MT4Dashboard/MQ4` dans :
     ```
     MQL4/Experts/
     ```
     Ou importer le depuis l'onglet 
     ```"Expert consultant" dans MT4```
   - Redémarrer MetaTrader 4
   - Glisser l’EA sur un graphique ou double cliquez dessus avec un graphique selectionné
   - Autoriser les DLL, le trading automatique et l'adresse http : http://local.host/ (Les 3 se trouve dans "Options", "Expert consultant"

Ensuite vous pouvez accéder à l'adresse http://127.0.0.1/dashboard ou http://local.host/dashboard

---


### ✅ Changements récents :
- **Passage complet de JSON à SQLite** pour remplacer les fichiers JSON, avec un énorme gain de performances.
- **Refonte complète des API** avec ajout d’endpoints pour la **modification, l’ajout et la suppression** des données via l’interface, l'interface client n'a pas changé et les données récupérer par le JS sont exactement les mêmes que pour le JSON.
- **Gain de performance significatif** : anciennement ~4 secondes par mise à jour, maintenant testé à **0.5s**, en fonction de vos ressources, avec le nombre de requête il est éventuellement possible de décendre à 0.1s/MAJ.
- **Mise à jour du fichier cmd** : Ajout d'une configuration de modification fichier "host" pour ajouté local.host à 127.0.0.1(necessaire pour MT4).

### 🧪 Fonctionnalités expérimentales :
- **Incrémentation d’un LLM en cours de test** (non inclus dans cette version – manque de tests concluants, en local avec une petite machine le LLM a du mal a faire des retours rapdie).
- **Creation de scrapeur API FED** (non inclus dans cette version).

### 🐞 Bugs connus :
- Sur le script MT4, **le TP ne se met pas encore à jour automatiquement**. La correction arrive très prochainement.

### ⚠️ Précautions à prendre :
- Le fichier `.cmd` ajoute une redirection locale : `127.0.0.1` → `local.host`.
- **MT4 ne prend pas en charge** les adresses `localhost`, `127.0.0.1`, `0.0.0.0`, etc.
- **L’utilisateur doit autoriser manuellement les requêtes vers l’endpoint `http://local.host/` dans MT4.**


# 💹 MT4 Web Dashboard

Interface web complète de **gestion des trades** et de **l'analyse du risque** pour MetaTrader 4.

Ce projet permet de **visualiser, analyser et commenter vos positions de trading** en temps réel depuis une page web. Il récupère automatiquement les données grâce à un **Expert Advisor MT4**, en exploitant un backend **Python Flask**, des fichiers **JSON**, et une interface **HTML/CSS/JS**.

J'avais auparavant développé un outil basé sur l'IA pour MT4, mais il avait une architecture complexe et pas maintenable avec une multitude de dépendances externes, rendant son installation longue et fastidieuse.

Avec ce nouveau projet, j'ai voulu restructurer entièrement l'approche : une configuration simple, rapide, et modulaire. L’objectif est de poser des bases solides pour en faire un véritable outil de management du trading, avec des fonctionnalités avancées à venir — dont l’intégration progressive de l’IA.

1 seul fichier à configurer après avoir installer python : config.cmd

2 lancer l'expert advisor sur MT4
<br>


<center><img src="https://github.com/nowwScriptKK/Dashboard-web-for-MT4-risk-management/blob/main/Capture_1.PNG" style="text-align: center;" alt="Texte alternatif"></center>
⚠️Le projet et fait pour tourner en local.

---

## 🔧 Technologies utilisées

- **MQL4** : Expert Advisor pour MetaTrader 4 (extraction des données)
- **Python Flask** : Serveur backend API
- **HTML/CSS/JS** : Interface utilisateur
- **SQLite** : Stockage et échange des données

---

## 📡 Endpoints API

| Endpoint | Description |
|----------|-------------|
| `api/tradesDB` | Récupère tous les trades (ouverts/fermés/Info du compte) |
| `api/trades/editDB` | Edition de trade |
| `api/trades/closesDB` | Ferme un trade ouvert |
| `api/trades/add` | Ajouter un trade |
| `api/commentsDB` | Liste les commentaires |
| `api/comments/addDB` | Ajout d’un commentaire |
| `api/comments/editDB` | Modification d’un commentaire |
| `api/comments/deleteDB` | Suppression d’un commentaire |
| `api/configDB` | Récupère la configuration |
| `api/config/editDB` | Édite la configuration |
| `/api/capitalDB` | Récupère le capital |
| `/api/account/update`  | Mise à jour de la table compte |
---

## 💻 Fonctionnalités

### 📊 Analyse et Affichage - C'est cette parti qui sera modifier pour la prochaine mise à jour
- Vue en **€ ou %**
- **Mode sombre**
- **Tableau récapitulatif des performances**
  - Moyenne de gain
  - Meilleur / Pire trade
  - Drawdown actuel
- Données de compte :
  - Balance, Equity, Free Margin, Margin, Leverage
  - Devise du compte, Numéro de compte
  - Capital actuel, RR moyen, etc.
- **Graphiques** dynamiques en fonction du capital de départ
- **Historique complet** récupéré depuis MT4

### 🧠 Gestion des trades
- Liste des trades **ouverts** avec ajout/modification/suppression de commentaires :
  - `Attente:`, `Confiance (0-5)`, `Satisfaction`, `Texte libre`
- Liste des trades **fermés** avec commentaires
- **Fonctions de gestion** :
  - Fermer tous les trades
  - Stop Loss automatique (en pips)
  - Trailing Stop (en pips)

---



---

## 🧱 Architecture du projet

Le projet est organisé de manière modulaire :

```
MT4Dashboard/
│
├── CLIENT/         # Interface web (HTML/CSS/JS)
├── DATA/           # Fichiers sql
├── MQ4/            # Expert Advisor pour MetaTrader 4 (.mq4)
├── SERVER/         # Backend Flask en Python
└── config.cmd      # Script de configuration automatique
```

- `config.cmd` permet de **configurer rapidement le serveur, les dépendances et le site**.
- Un **lien symbolique est créé** entre le dossier MT4 (`MQL4/Files`) et le dossier `DATA/` du projet, afin d’échanger les données automatiquement.
- Il est **important de lancer le script `config.cmd` avant MT4**, pour que tout soit bien connecté.

---

## 🔌 Backend Python Flask

L’application utilise le système de **Blueprints Flask** pour organiser les routes de l’API :

```python
# === Import des endpoints ===
from showTrade import trade_bp
app.register_blueprint(trade_bp)

from showConfig import config_bp
app.register_blueprint(config_bp)

from showComments import comments_bp
app.register_blueprint(comments_bp)
```

Chaque fichier déclare son propre blueprint :

```python
comments_bp = Blueprint('comments', __name__)
```

## 📄 Licence

Ce projet est sous licence **Creative Commons BY-NC 4.0**.  
Vous pouvez l'utiliser, l’adapter et le partager librement **à condition de ne pas l’utiliser à des fins commerciales, interdiction a la revente ou usage commercial**.

👉 [Détails de la licence](https://creativecommons.org/licenses/by-nc/4.0/



## 👤 Auteur

- **Discord** : `Theglitch_is`




Cette architecture permet de séparer proprement les fonctionnalités du serveur.
<center><img src="https://github.com/nowwScriptKK/Dashboard-web-for-MT4-risk-management/blob/main/Capture1.PNG" style="text-align: center;" alt="Texte alternatif"></center>



## ⚠️ Avertissement :
Ce programme est fourni à titre informatif et éducatif uniquement. Il ne constitue en aucun cas un conseil en investissement, en trading ou en gestion financière.

Toute décision d'utilisation de ce logiciel ou d'exécution de trades automatisés reste de la responsabilité exclusive de l'utilisateur.

L'auteur ne saurait être tenu responsable des pertes financières, directes ou indirectes, pouvant résulter de l'utilisation de ce programme.

Le trading comporte des risques importants de perte. Il est fortement recommandé de bien tester ce système sur compte démo avant toute utilisation en conditions réelles.
