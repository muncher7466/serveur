from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
import json
import os
from datetime import datetime, timedelta, date
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import logging

app = Flask(__name__)
app.secret_key = 'garage_automobile_secret_key'
app.permanent_session_lifetime = timedelta(days=7)

# Configuration du logging
app.logger.setLevel(logging.DEBUG)

# Décorateur pour vérifier si l'utilisateur est admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accès non autorisé. Vous devez être administrateur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Ajouter la variable now dans le contexte global
@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'datetime': datetime
    }

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

# Création des répertoires pour les données JSON si ils n'existent pas
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Chemins des fichiers JSON
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
VEHICULES_FILE = os.path.join(DATA_DIR, 'vehicules.json')
STOCK_FILE = os.path.join(DATA_DIR, 'stock.json')
SORTIES_FILE = os.path.join(DATA_DIR, 'sorties.json')
INTERVENTIONS_FILE = os.path.join(DATA_DIR, 'interventions.json')
CLIENTS_FILE = os.path.join(DATA_DIR, 'clients.json')
CONVERSATIONS_FILE = os.path.join(DATA_DIR, 'conversations.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.json')
REPORTS_FILE = os.path.join(DATA_DIR, 'reports.json')
FOURNISSEURS_FILE = os.path.join(DATA_DIR, 'fournisseurs.json')
PLANNINGS_FILE = os.path.join(DATA_DIR, 'plannings.json')
DELAIS_CONTROLES_FILE = os.path.join(DATA_DIR, 'delais_controles.json')
UNREAD_MESSAGES_FILE = os.path.join(DATA_DIR, 'unread_messages.json')
HISTORIQUE_STOCK_FILE = os.path.join(DATA_DIR, 'historique_stock.json')

# Seuil pour le stock faible
STOCK_FAIBLE_SEUIL = 5

# Constantes pour les statuts de planning
PLANNING_STATUTS = {
    'en_reparation': 'En réparation',
    'termine': 'Terminé',
    'en_attente': 'En attente',
    'en_diagnostic': 'En diagnostic',
    'pieces_commandees': 'Pièces commandées'
}

# Constantes pour les alertes de contrôle
DELAI_URGENT = 30  # 30 jours
DELAI_ATTENTION = 60  # 60 jours

# Classe User pour Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password, name, role):
        self.id = id
        self.username = username
        self.password = password
        self.name = name
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Fonction pour charger un utilisateur
@login_manager.user_loader
def load_user(user_id):
    users = load_data(USERS_FILE)
    user_data = next((u for u in users if u['id'] == user_id), None)
    if not user_data:
        return None
    return User(
        id=user_data['id'],
        username=user_data['username'],
        password=user_data['password'],
        name=user_data.get('name', user_data['username']),
        role=user_data.get('role', 'user')
    )

# Fonction pour charger les données JSON
def load_data(file_path):
    try:
        if not os.path.exists(file_path):
            # Si le fichier n'existe pas, créer un fichier vide avec une liste vide
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
        # En cas d'erreur, retourner une liste vide
        return []

# Fonction pour sauvegarder les données JSON
def save_data(file_path, data):
    try:
        # Créer le répertoire parent s'il n'existe pas
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde dans {file_path}: {str(e)}")
        raise

# Routes pour l'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    now = datetime.now()
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        users = load_data(USERS_FILE)
        user_data = next((u for u in users if u['username'] == username), None)
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                name=user_data.get('name', user_data['username']),
                role=user_data.get('role', 'user')
            )
            login_user(user, remember=remember)
            
            # Redirection vers la page demandée initialement ou la page d'accueil
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            
            flash(f'Bienvenue, {user.name} !', 'success')
            return redirect(next_page)
        else:
            error = 'Nom d\'utilisateur ou mot de passe incorrect.'
    
    return render_template('auth/login.html', error=error, now=now)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

# Routes pour la page d'accueil
@app.route('/')
@login_required
def index():
    now = datetime.now()
    
    # Charger les données nécessaires
    interventions = load_data(INTERVENTIONS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    
    # Associer les noms des propriétaires aux véhicules
    for vehicule in vehicules:
        if 'client_id' in vehicule:
            client = next((c for c in clients if c['id'] == vehicule['client_id']), None)
            if client:
                vehicule['proprietaire'] = f"{client['nom']} {client['prenom']}"
            else:
                vehicule['proprietaire'] = "Non spécifié"
        else:
            vehicule['proprietaire'] = "Non spécifié"
    
    # Filtrer les interventions en cours (des 7 derniers jours)
    date_limite = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    interventions_en_cours = []
    
    for intervention in interventions:
        if intervention['date'] >= date_limite:
            # Ajouter les informations du véhicule si disponible
            if intervention.get('vehicule_id'):
                vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)
                if vehicule:
                    intervention['vehicule_info'] = f"{vehicule['marque']} {vehicule['modele']} ({vehicule['immatriculation']})"
                    intervention['client_info'] = vehicule['proprietaire']  # Utiliser le propriétaire déjà associé
                else:
                    intervention['vehicule_info'] = 'Véhicule non trouvé'
                    intervention['client_info'] = 'Client non trouvé'
            else:
                intervention['vehicule_info'] = 'Sans véhicule'
                intervention['client_info'] = 'Sans client'
            
            interventions_en_cours.append(intervention)
    
    # Trier les interventions par date (plus récentes en premier)
    interventions_en_cours.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('index.html', 
                         now=now,
                         interventions_en_cours=interventions_en_cours)

# Routes pour la gestion des véhicules
@app.route('/vehicules')
@login_required
def liste_vehicules():
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    now = datetime.now()
    
    # Associer les noms des propriétaires aux véhicules
    for vehicule in vehicules:
        if 'client_id' in vehicule:
            client = next((c for c in clients if c['id'] == vehicule['client_id']), None)
            if client:
                vehicule['proprietaire'] = f"{client['nom']} {client['prenom']}"
            else:
                vehicule['proprietaire'] = "Non spécifié"
        else:
            vehicule['proprietaire'] = "Non spécifié"
    
    return render_template('vehicules/liste.html', vehicules=vehicules, now=now)

@app.route('/vehicules/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_vehicule():
    if request.method == 'POST':
        try:
            vehicules = load_data(VEHICULES_FILE)
            nouveau_vehicule = {
                'id': str(uuid.uuid4()),
                'marque': request.form['marque'],
                'modele': request.form['modele'],
                'immatriculation': request.form['immatriculation'],
                'code_parc': request.form['code_parc'],
                'numero_serie': request.form['numero_serie'],
                'client_id': request.form['client_id'],
                'type_vehicule': request.form['type_vehicule'],
                'annee': request.form['annee'],
                'kilometrage': int(request.form['kilometrage']),
                'date_ajout': datetime.now().strftime('%Y-%m-%d')
            }

            # Ajouter les dates de contrôle seulement si elles sont fournies
            # et si le type de véhicule les requiert
            type_vehicule = request.form['type_vehicule']
            
            if type_vehicule not in ['remorque', 'materiel']:
                if type_vehicule in ['voiture', 'camion', 'utilitaire'] and request.form.get('date_dernier_ct'):
                    nouveau_vehicule['date_dernier_ct'] = request.form['date_dernier_ct']
                
                if type_vehicule == 'camion':
                    if request.form.get('date_dernier_mine'):
                        nouveau_vehicule['date_dernier_mine'] = request.form['date_dernier_mine']
                    if request.form.get('date_dernier_tachy'):
                        nouveau_vehicule['date_dernier_tachy'] = request.form['date_dernier_tachy']
                
                if type_vehicule == 'engin' and request.form.get('date_dernier_vgp'):
                    nouveau_vehicule['date_dernier_vgp'] = request.form['date_dernier_vgp']

            vehicules.append(nouveau_vehicule)
            save_data(VEHICULES_FILE, vehicules)
            
            flash('Véhicule ajouté avec succès!', 'success')
            return redirect(url_for('liste_vehicules'))
            
        except Exception as e:
            flash(f'Erreur lors de l\'ajout du véhicule : {str(e)}', 'danger')
            return redirect(url_for('ajouter_vehicule'))

    clients = load_data(CLIENTS_FILE)
    return render_template('vehicules/ajouter.html', clients=clients)

@app.route('/vehicules/<vehicule_id>')
@login_required
def details_vehicule(vehicule_id):
    vehicules = load_data(VEHICULES_FILE)
    vehicule = next((v for v in vehicules if v['id'] == vehicule_id), None)
    
    if not vehicule:
        flash('Véhicule non trouvé', 'danger')
        return redirect(url_for('liste_vehicules'))
    
    # Charger les interventions
    interventions = load_data(INTERVENTIONS_FILE)
    historique = [i for i in interventions if i.get('vehicule_id') == vehicule_id]
    
    # Trier l'historique par date (plus anciennes en premier)
    historique.sort(key=lambda x: x.get('date', ''))
    
    # Calculer les statistiques
    total_interventions = len(historique)
    total_cout = sum(float(i.get('cout_total', 0)) for i in historique)
    derniere_intervention = historique[-1] if historique else None
    
    return render_template('vehicules/details.html',
                         vehicule=vehicule,
                         historique=historique,
                         total_interventions=total_interventions,
                         total_cout=total_cout,
                         derniere_intervention=derniere_intervention)

@app.route('/vehicules/<vehicule_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_vehicule(vehicule_id):
    vehicules = load_data(VEHICULES_FILE)
    vehicule = next((v for v in vehicules if v['id'] == vehicule_id), None)
    
    if vehicule is None:
        flash('Véhicule non trouvé.', 'danger')
        return redirect(url_for('liste_vehicules'))
    
    if request.method == 'POST':
        try:
            # Mettre à jour les informations de base
            vehicule['marque'] = request.form['marque']
            vehicule['modele'] = request.form['modele']
            vehicule['immatriculation'] = request.form['immatriculation']
            vehicule['code_parc'] = request.form['code_parc']
            vehicule['numero_serie'] = request.form['numero_serie']
            vehicule['client_id'] = request.form['client_id']
            vehicule['type_vehicule'] = request.form['type_vehicule']
            vehicule['annee'] = request.form['annee']
            vehicule['kilometrage'] = int(request.form['kilometrage'])
            
            # Mettre à jour les dates de contrôle
            if 'date_dernier_ct' in request.form and request.form['date_dernier_ct']:
                vehicule['date_dernier_ct'] = request.form['date_dernier_ct']
            elif 'date_dernier_ct' in vehicule:
                del vehicule['date_dernier_ct']
            
            if 'date_dernier_mine' in request.form and request.form['date_dernier_mine']:
                vehicule['date_dernier_mine'] = request.form['date_dernier_mine']
            elif 'date_dernier_mine' in vehicule:
                del vehicule['date_dernier_mine']
            
            if 'date_dernier_tachy' in request.form and request.form['date_dernier_tachy']:
                vehicule['date_dernier_tachy'] = request.form['date_dernier_tachy']
            elif 'date_dernier_tachy' in vehicule:
                del vehicule['date_dernier_tachy']
            
            if 'date_dernier_vgp' in request.form and request.form['date_dernier_vgp']:
                vehicule['date_dernier_vgp'] = request.form['date_dernier_vgp']
            elif 'date_dernier_vgp' in vehicule:
                del vehicule['date_dernier_vgp']
            
            save_data(VEHICULES_FILE, vehicules)
            flash('Véhicule modifié avec succès!', 'success')
            return redirect(url_for('liste_vehicules'))
        except Exception as e:
            flash(f'Erreur lors de la modification du véhicule : {str(e)}', 'danger')
    
    clients = load_data(CLIENTS_FILE)
    return render_template('vehicules/modifier.html', vehicule=vehicule, clients=clients)

# Routes pour la gestion du stock
@app.route('/stock')
@login_required
def liste_stock():
    pieces = load_data(STOCK_FILE)
    fournisseurs = load_data(FOURNISSEURS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    sorties = load_data(SORTIES_FILE)
    
    # Calculer le nombre de pièces en stock faible
    stock_faible = len([p for p in pieces if p['quantite'] < p.get('quantite_min', 0)])
    
    # Calculer la valeur totale du stock
    valeur_stock = sum(p['quantite'] * p['prix_achat'] for p in pieces)
    
    # Ajouter les informations des sorties récentes
    for piece in pieces:
        piece['sorties_recentes'] = []
        for sortie in sorties:
            if sortie['piece_id'] == piece['id']:
                vehicule = next((v for v in vehicules if v['id'] == sortie['vehicule_id']), None)
                if vehicule:
                    sortie['vehicule_info'] = f"{vehicule['marque']} {vehicule['modele']} ({vehicule['immatriculation']})"
                    sortie['client_info'] = vehicule.get('proprietaire', 'Propriétaire non spécifié')  # Gérer en toute sécurité l'accès à la clé 'proprietaire'
                    piece['sorties_recentes'].append(sortie)
    
    return render_template('stock/liste.html', 
                         pieces=pieces, 
                         fournisseurs=fournisseurs,
                         stock_faible=stock_faible,
                         valeur_stock=valeur_stock)

@app.route('/stock/historique')
@login_required
def historique_sorties():
    sorties = load_data(SORTIES_FILE)
    pieces = load_data(STOCK_FILE)
    vehicules = load_data(VEHICULES_FILE)
    interventions = load_data(INTERVENTIONS_FILE)
    clients = load_data(CLIENTS_FILE)
    
    # Associer les noms des propriétaires aux véhicules
    for vehicule in vehicules:
        if 'client_id' in vehicule:
            client = next((c for c in clients if c['id'] == vehicule['client_id']), None)
            if client:
                vehicule['proprietaire'] = f"{client['nom']} {client['prenom']}"
            else:
                vehicule['proprietaire'] = "Non spécifié"
        else:
            vehicule['proprietaire'] = "Non spécifié"
    
    # Ajouter les informations complètes pour chaque sortie
    for sortie in sorties:
        # Informations de la pièce
        sortie['valeur'] = 0  # Initialiser la valeur à 0 par défaut
        piece = next((p for p in pieces if p['id'] == sortie['piece_id']), None)
        if piece:
            sortie['piece_info'] = f"{piece['nom']} ({piece['reference']})"
            sortie['valeur'] = sortie['quantite'] * piece['prix_achat']  # Mettre à jour la valeur
        
        # Informations du véhicule et du client
        vehicule = next((v for v in vehicules if v['id'] == sortie['vehicule_id']), None)
        if vehicule:
            sortie['vehicule_info'] = f"{vehicule['marque']} {vehicule['modele']} ({vehicule['immatriculation']})"
            sortie['client_info'] = vehicule['proprietaire']  # Utiliser le propriétaire déjà associé
        
        # Informations de l'intervention
        if sortie.get('intervention_id'):
            intervention = next((i for i in interventions if i['id'] == sortie['intervention_id']), None)
            if intervention:
                sortie['intervention_info'] = f"{intervention['type']} - {intervention['date']}"
    
    # Trier les sorties par date (plus récentes en premier)
    sorties.sort(key=lambda x: x['date_sortie'], reverse=True)
    
    return render_template('stock/historique.html', 
                         sorties=sorties,
                         pieces=pieces)

@app.route('/stock/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_piece():
    if request.method == 'POST':
        try:
            pieces = load_data(STOCK_FILE)
            fournisseurs = load_data(FOURNISSEURS_FILE)
            
            # Vérifier si une pièce avec la même référence existe déjà
            reference = request.form['reference']
            piece_existante = next((p for p in pieces if p['reference'].lower() == reference.lower()), None)
            if piece_existante:
                flash('Une pièce avec cette référence existe déjà dans le stock', 'danger')
                return redirect(url_for('ajouter_piece'))
            
            # Vérifier si le fournisseur existe
            fournisseur_id = request.form.get('fournisseur_id')
            if fournisseur_id:
                fournisseur = next((f for f in fournisseurs if f['id'] == fournisseur_id), None)
                if not fournisseur:
                    flash('Fournisseur non trouvé', 'danger')
                    return redirect(url_for('ajouter_piece'))
            
            # Convertir les prix en float avec 2 décimales
            prix_achat = round(float(request.form['prix_achat']), 2)
            prix_vente = round(float(request.form['prix_vente']), 2)
            
            nouvelle_piece = {
                'id': str(uuid.uuid4()),
                'reference': request.form['reference'],
                'nom': request.form['nom'],
                'description': request.form['description'],
                'quantite': int(request.form['quantite']),
                'quantite_min': int(request.form['quantite_min']),
                'prix_achat': prix_achat,
                'prix_vente': prix_vente,
                'fournisseur_id': fournisseur_id,
                'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            pieces.append(nouvelle_piece)
            save_data(STOCK_FILE, pieces)
            flash('Pièce ajoutée avec succès!', 'success')
            return redirect(url_for('liste_stock'))
        except Exception as e:
            flash(f'Erreur lors de l\'ajout de la pièce : {str(e)}', 'danger')
    
    fournisseurs = load_data(FOURNISSEURS_FILE)
    return render_template('stock/ajouter.html', fournisseurs=fournisseurs)

@app.route('/stock/modifier/<id>', methods=['GET', 'POST'])
@login_required
def modifier_piece(id):
    pieces = load_data(STOCK_FILE)
    piece = next((p for p in pieces if p['id'] == id), None)
    fournisseurs = load_data(FOURNISSEURS_FILE)
    
    if not piece:
        flash('Pièce non trouvée', 'danger')
        return redirect(url_for('liste_stock'))
    
    if request.method == 'POST':
        try:
            # Vérifier si le fournisseur existe
            fournisseur_id = request.form.get('fournisseur_id')
            if fournisseur_id:
                fournisseur = next((f for f in fournisseurs if f['id'] == fournisseur_id), None)
                if not fournisseur:
                    flash('Fournisseur non trouvé', 'danger')
                    return redirect(url_for('modifier_piece', id=id))
            
            # Convertir les prix en float avec 2 décimales
            prix_achat = round(float(request.form['prix_achat']), 2)
            prix_vente = round(float(request.form['prix_vente']), 2)
            
            piece['reference'] = request.form['reference']
            piece['nom'] = request.form['nom']
            piece['description'] = request.form['description']
            piece['quantite'] = int(request.form['quantite'])
            piece['quantite_min'] = int(request.form['quantite_min'])
            piece['prix_achat'] = prix_achat
            piece['prix_vente'] = prix_vente
            piece['fournisseur_id'] = fournisseur_id
            
            save_data(STOCK_FILE, pieces)
            flash('Pièce modifiée avec succès!', 'success')
            return redirect(url_for('liste_stock'))
        except Exception as e:
            flash(f'Erreur lors de la modification de la pièce : {str(e)}', 'danger')
    
    return render_template('stock/modifier.html', piece=piece, fournisseurs=fournisseurs)

@app.route('/stock/ajuster/<piece_id>', methods=['POST'])
@login_required
def ajuster_stock(piece_id):
    stock = load_data(STOCK_FILE)
    piece = next((p for p in stock if p['id'] == piece_id), None)
    
    if not piece:
        return jsonify({'success': False, 'message': 'Pièce non trouvée!'})
    
    quantite = int(request.form['quantite'])
    piece['quantite'] = quantite
    
    save_data(STOCK_FILE, stock)
    return jsonify({'success': True, 'message': 'Stock ajusté avec succès!'})

@app.route('/stock/sortie', methods=['POST'])
@login_required
def sortir_piece():
    try:
        pieces = load_data(STOCK_FILE)
        vehicules = load_data(VEHICULES_FILE)
        sorties = load_data(SORTIES_FILE)
        
        piece_id = request.form['piece_id']
        vehicule_id = request.form['vehicule_id']
        quantite = int(request.form['quantite'])
        intervention_id = request.form.get('intervention_id')  # Nouveau champ
        
        # Vérifier si la pièce existe et si le stock est suffisant
        piece = next((p for p in pieces if p['id'] == piece_id), None)
        if not piece or piece['quantite'] < quantite:
            return jsonify({'success': False, 'message': 'Stock insuffisant!'})
        
        # Vérifier si le véhicule existe
        vehicule = next((v for v in vehicules if v['id'] == vehicule_id), None)
        if not vehicule:
            return jsonify({'success': False, 'message': 'Véhicule non trouvé!'})
        
        # Mettre à jour le stock
        piece['quantite'] -= quantite
        
        # Créer la sortie
        nouvelle_sortie = {
            'id': str(uuid.uuid4()),
            'piece_id': piece_id,
            'vehicule_id': vehicule_id,
            'quantite': quantite,
            'date_sortie': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'utilisateur': current_user.name,
            'intervention_id': intervention_id  # Ajouter l'ID de l'intervention
        }
        
        sorties.append(nouvelle_sortie)
        save_data(SORTIES_FILE, sorties)
        save_data(STOCK_FILE, pieces)
        
        return jsonify({'success': True, 'message': 'Pièce sortie avec succès!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Routes pour la gestion des interventions
@app.route('/interventions')
@login_required
def liste_interventions():
    interventions = load_data(INTERVENTIONS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    now = datetime.now()

    for intervention in interventions:
        if intervention.get('vehicule_id'):
            vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)
            if vehicule:
                intervention['vehicule_marque'] = vehicule['marque']
                intervention['vehicule_modele'] = vehicule['modele']
                intervention['vehicule_code_parc'] = vehicule.get('code_parc', 'N/A')
        
        if intervention.get('client_id'):
            client = next((c for c in clients if c['id'] == intervention['client_id']), None)
            if client:
                intervention['client_nom'] = f"{client['nom']} {client['prenom']}"
    
    interventions.sort(key=lambda x: x.get('date', ''), reverse=True)
    return render_template('interventions/liste.html', interventions=interventions)

@app.route('/interventions/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_intervention():
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    stock = load_data(STOCK_FILE)
    sorties = load_data(SORTIES_FILE)
    interventions = load_data(INTERVENTIONS_FILE)
    users = load_data(USERS_FILE)
    now = datetime.now()

    if request.method == 'POST':
        # Récupérer les informations du véhicule
        vehicule = next((v for v in vehicules if v['id'] == request.form['vehicule_id']), None)
        if not vehicule:
            flash('Véhicule non trouvé!', 'danger')
            return redirect(url_for('liste_interventions'))

        # Vérifier que le nouveau kilométrage n'est pas inférieur à l'actuel
        if 'kilometrage' in request.form and request.form['kilometrage']:
            nouveau_km = float(request.form['kilometrage'])
            ancien_km = float(vehicule.get('kilometrage', 0))
            if nouveau_km < ancien_km:
                flash(f'Le kilométrage saisi ({nouveau_km} km) ne peut pas être inférieur au kilométrage actuel du véhicule ({ancien_km} km)!', 'danger')
                return redirect(url_for('ajouter_intervention'))

        # Récupérer le technicien
        technicien = next((u for u in users if u['id'] == request.form['technicien']), None)
        if not technicien:
            flash('Technicien non trouvé!', 'danger')
            return redirect(url_for('liste_interventions'))

        # Créer la nouvelle intervention
        nouvelle_intervention = {
            'id': str(uuid.uuid4()),
            'vehicule_id': request.form['vehicule_id'],
            'client_id': request.form['client_id'],
            'date': request.form['date'],
            'type': request.form['type'],
            'description': request.form['description'],
            'kilometrage': request.form['kilometrage'],
            'technicien': technicien['name'],  # On sauvegarde le nom du technicien
            'heures': float(request.form['heures']),
            'pieces_utilisees': [],
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'statut': 'En cours'
        }
        
        # Traiter les pièces utilisées
        piece_ids = request.form.getlist('piece_id[]')
        quantites = request.form.getlist('quantite[]')
        
        for piece_id, quantite in zip(piece_ids, quantites):
            if piece_id and quantite and int(quantite) > 0:
                quantite = int(quantite)
                piece = next((p for p in stock if p['id'] == piece_id), None)
                
                if piece and piece['quantite'] >= quantite:
                    # Ajouter la pièce à l'intervention
                    nouvelle_intervention['pieces_utilisees'].append({
                        'piece_id': piece_id,
                        'nom': piece['nom'],
                        'prix_unitaire': piece['prix_vente'],
                        'quantite': quantite,
                        'total': float(piece['prix_vente']) * quantite
                    })
                    
                    # Mettre à jour le stock
                    piece['quantite'] -= quantite
                    
                    # Créer une sortie de pièce
                    nouvelle_sortie = {
                        'id': str(uuid.uuid4()),
                        'piece_id': piece_id,
                        'vehicule_id': request.form['vehicule_id'],
                        'quantite': quantite,
                        'date_sortie': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'utilisateur': current_user.name,
                        'intervention_id': nouvelle_intervention['id']
                    }
                    sorties.append(nouvelle_sortie)
                else:
                    flash(f'Stock insuffisant pour la pièce {piece["nom"]}!', 'danger')
                    return redirect(url_for('ajouter_intervention'))

        # Sauvegarder les modifications
        interventions.append(nouvelle_intervention)
        save_data(INTERVENTIONS_FILE, interventions)
        save_data(STOCK_FILE, stock)
        save_data(SORTIES_FILE, sorties)

        # Mettre à jour le kilométrage du véhicule
        if 'kilometrage' in request.form and request.form['kilometrage']:
            # Trouver et mettre à jour le véhicule
            for v in vehicules:
                if v['id'] == request.form['vehicule_id']:
                    v['kilometrage'] = request.form['kilometrage']
                    break
            save_data(VEHICULES_FILE, vehicules)

        flash('Intervention ajoutée avec succès!', 'success')
        return redirect(url_for('liste_interventions'))

    return render_template('interventions/ajouter.html', 
                         vehicules=vehicules,
                         clients=clients,
                         stock=stock,
                         users=users,
                         now=now)

@app.route('/interventions/<intervention_id>')
@login_required
def details_intervention(intervention_id):
    interventions = load_data(INTERVENTIONS_FILE)
    intervention = next((i for i in interventions if i['id'] == intervention_id), None)
    
    if not intervention:
        flash('Intervention non trouvée!', 'danger')
        return redirect(url_for('liste_interventions'))
    
    # Charger les données nécessaires
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    users = load_data(USERS_FILE)
    
    # Récupérer les informations du véhicule, du client et du technicien
    vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)
    client = next((c for c in clients if c['id'] == intervention['client_id']), None)
    technicien = next((u for u in users if u['name'] == intervention['technicien']), None)
    
    # Si on trouve le technicien, utiliser son nom, sinon garder l'ID
    if technicien:
        intervention['technicien'] = technicien['name']
    
    # Calculer le coût de la main d'œuvre (taux horaire fixé à 60€)
    taux_horaire = 60.0
    intervention['cout_main_oeuvre'] = intervention['heures'] * taux_horaire
    
    # Calculer le total des pièces
    total_pieces = sum(float(piece['total']) for piece in intervention.get('pieces_utilisees', []))
    
    return render_template('interventions/details.html',
                         intervention=intervention,
                         vehicule=vehicule,
                         client=client,
                         taux_horaire=taux_horaire,
                         total_pieces=total_pieces)

@app.route('/interventions/<intervention_id>/statut', methods=['POST'])
@login_required
def modifier_statut_intervention(intervention_id):
    try:
        data = request.get_json()
        nouveau_statut = data.get('statut')
        
        if not nouveau_statut:
            return jsonify({'success': False, 'message': 'Statut manquant'})
        
        interventions = load_data(INTERVENTIONS_FILE)
        intervention_trouvee = False
        
        for intervention in interventions:
            if intervention['id'] == intervention_id:
                intervention['statut'] = nouveau_statut
                intervention_trouvee = True
                break
        
        if not intervention_trouvee:
            return jsonify({'success': False, 'message': 'Intervention non trouvée'})
        
        save_data(INTERVENTIONS_FILE, interventions)
        return jsonify({'success': True, 'message': 'Statut mis à jour avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour : {str(e)}'})

@app.route('/interventions/modifier/<intervention_id>', methods=['GET', 'POST'])
@login_required
def modifier_intervention(intervention_id):
    interventions = load_data(INTERVENTIONS_FILE)
    intervention = next((i for i in interventions if i['id'] == intervention_id), None)
    
    if not intervention:
        flash('Intervention non trouvée!', 'danger')
        return redirect(url_for('liste_interventions'))
    
    vehicules = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    stock = load_data(STOCK_FILE)
    users = load_data(USERS_FILE)
    now = datetime.now()

    if request.method == 'POST':
        # Récupérer les informations du véhicule
        vehicule = next((v for v in vehicules if v['id'] == request.form['vehicule_id']), None)
        if not vehicule:
            flash('Véhicule non trouvé!', 'danger')
            return redirect(url_for('modifier_intervention', intervention_id=intervention_id))

        # Vérifier que le nouveau kilométrage n'est pas inférieur à l'actuel
        if 'kilometrage' in request.form and request.form['kilometrage']:
            nouveau_km = float(request.form['kilometrage'])
            ancien_km = float(vehicule.get('kilometrage', 0))
            if nouveau_km < ancien_km:
                flash(f'Le kilométrage saisi ({nouveau_km} km) ne peut pas être inférieur au kilométrage actuel du véhicule ({ancien_km} km)!', 'danger')
                return redirect(url_for('modifier_intervention', intervention_id=intervention_id))

        # Mettre à jour l'intervention
        anciennes_pieces = intervention.get('pieces_utilisees', [])
        intervention.update({
            'vehicule_id': request.form['vehicule_id'],
            'client_id': request.form['client_id'],
            'date': request.form['date'],
            'type': request.form['type'],
            'description': request.form['description'],
            'kilometrage': request.form['kilometrage'],
            'technicien': request.form['technicien'],
            'heures': float(request.form['heures']),
            'pieces_utilisees': anciennes_pieces  # Garder les anciennes pièces
        })

        # Traiter les nouvelles pièces
        piece_ids = request.form.getlist('piece_id[]')
        quantites = request.form.getlist('quantite[]')
        sorties = load_data(SORTIES_FILE)  # Charger le fichier des sorties
        
        for piece_id, quantite in zip(piece_ids, quantites):
            if piece_id and quantite and int(quantite) > 0:
                quantite = int(quantite)
                piece = next((p for p in stock if p['id'] == piece_id), None)
                
                if piece and piece['quantite'] >= quantite:
                    # Ajouter la pièce à l'intervention
                    intervention['pieces_utilisees'].append({
                        'piece_id': piece_id,
                        'nom': piece['nom'],
                        'prix_unitaire': piece['prix_vente'],
                        'quantite': quantite,
                        'total': float(piece['prix_vente']) * quantite
                    })
                    
                    # Mettre à jour le stock
                    piece['quantite'] -= quantite

                    # Ajouter dans l'historique des sorties
                    nouvelle_sortie = {
                        'id': str(uuid.uuid4()),
                        'piece_id': piece_id,
                        'vehicule_id': request.form['vehicule_id'],
                        'quantite': quantite,
                        'date_sortie': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'utilisateur': current_user.name,
                        'intervention_id': intervention_id
                    }
                    sorties.append(nouvelle_sortie)
                else:
                    flash(f'Stock insuffisant pour la pièce {piece["nom"] if piece else "inconnue"}!', 'danger')
                    return redirect(url_for('modifier_intervention', intervention_id=intervention_id))

        # Sauvegarder les modifications
        save_data(INTERVENTIONS_FILE, interventions)
        save_data(STOCK_FILE, stock)
        save_data(SORTIES_FILE, sorties)  # Sauvegarder l'historique des sorties
        
        # Mettre à jour le kilométrage du véhicule
        if 'kilometrage' in request.form and request.form['kilometrage']:
            # Trouver et mettre à jour le véhicule
            for v in vehicules:
                if v['id'] == request.form['vehicule_id']:
                    v['kilometrage'] = request.form['kilometrage']
                    break
            save_data(VEHICULES_FILE, vehicules)
        
        flash('Intervention modifiée avec succès!', 'success')
        return redirect(url_for('liste_interventions'))

    # Récupérer les informations du client et du véhicule
    client = next((c for c in clients if c['id'] == intervention['client_id']), None)
    vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)

    return render_template('interventions/modifier.html',
                         intervention=intervention,
                         vehicules=vehicules,
                         clients=clients,
                         stock=stock,
                         users=users,
                         client_selectionne=client,
                         vehicule_selectionne=vehicule,
                         now=now)

# Routes pour la gestion des clients
@app.route('/clients')
@login_required
def liste_clients():
    clients = load_data(CLIENTS_FILE)
    now = datetime.now()
    return render_template('clients/liste.html', clients=clients, now=now)

@app.route('/clients/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_client():
    now = datetime.now()
    if request.method == 'POST':
        clients = load_data(CLIENTS_FILE)
        nouveau_client = {
            'id': str(uuid.uuid4()),
            'nom': request.form['nom'],
            'prenom': request.form['prenom'],
            'telephone': request.form['telephone'],
            'email': request.form['email'],
            'adresse': request.form['adresse'],
            'date_ajout': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        clients.append(nouveau_client)
        save_data(CLIENTS_FILE, clients)
        flash('Client ajouté avec succès!', 'success')
        return redirect(url_for('liste_clients'))
    return render_template('clients/ajouter.html', now=now)

@app.route('/clients/<client_id>')
@login_required
def details_client(client_id):
    clients = load_data(CLIENTS_FILE)  # Charge les données des clients
    vehicules = load_data(VEHICULES_FILE)  # Charge les données des véhicules
    interventions = load_data(INTERVENTIONS_FILE)  # Charge les données des interventions
    now = datetime.now()
    
    # Trouver le client correspondant
    client = next((c for c in clients if c['id'] == client_id), None)
    if not client:
        flash('Client non trouvé!', 'danger')
        return redirect(url_for('liste_clients'))
    
    # Filtrer les véhicules appartenant au client
    vehicules_client = [v for v in vehicules if v.get('client_id') == client_id]
    
    # Récupérer toutes les interventions pour les véhicules du client
    interventions_client = [
        {**intervention, 'vehicule': next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)}
        for intervention in interventions
        if intervention.get('vehicule_id') in [v['id'] for v in vehicules_client]
    ]
    
    # Trier les interventions par date (plus récentes en premier)
    interventions_client.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)
    
    # Compter le nombre total d'interventions
    total_interventions = len(interventions_client)
    
    # Transmettre les données au template
    return render_template('clients/details.html', 
                         client=client, 
                         vehicules=vehicules_client, 
                         interventions=interventions_client,
                         total_interventions=total_interventions, 
                         now=now)

@app.route('/clients/modifier/<client_id>', methods=['GET', 'POST'])
@login_required
def modifier_client(client_id):
    clients = load_data(CLIENTS_FILE)
    client = next((c for c in clients if c['id'] == client_id), None)
    
    if not client:
        flash('Client non trouvé!', 'danger')
        return redirect(url_for('liste_clients'))
    
    if request.method == 'POST':
        # Mise à jour des informations du client
        client.update({
            'nom': request.form['nom'],
            'prenom': request.form['prenom'],
            'telephone': request.form['telephone'],
            'email': request.form['email'],
            'adresse': request.form['adresse']
        })
        
        # Mettre à jour la liste des clients
        clients = [c if c['id'] != client_id else client for c in clients]
        save_data(CLIENTS_FILE, clients)
        
        flash('Client modifié avec succès!', 'success')
        return redirect(url_for('details_client', client_id=client_id))
    
    return render_template('clients/modifier.html', client=client)

@app.route('/api/vehicules')
@login_required
def api_vehicules():
    vehicules = load_data(VEHICULES_FILE)
    return jsonify(vehicules)

@app.route('/api/stock')
@login_required
def api_stock():
    stock = load_data(STOCK_FILE)
    return jsonify(stock)

@app.route('/api/interventions')
@login_required
def api_interventions():
    interventions = load_data(INTERVENTIONS_FILE)
    return jsonify(interventions)

@app.route('/api/clients')
@login_required
def api_clients():
    clients = load_data(CLIENTS_FILE)
    return jsonify(clients)

@app.route('/api/users')
@login_required
def api_users():
    users = load_data(USERS_FILE)
    # Ne renvoyer que les informations nécessaires
    return jsonify([{
        'id': user['id'],
        'name': user.get('name', user['username']),
        'username': user['username']
    } for user in users])

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    users = load_data(USERS_FILE)
    return [{'id': user['id'], 'name': user['name']} for user in users]

@app.route('/api/conversations', methods=['POST'])
@login_required
def create_conversation():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'participants' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        conversations = load_data(CONVERSATIONS_FILE)
        new_conversation = {
            'id': str(uuid.uuid4()),
            'name': data['name'],
            'participants': data['participants'],
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.id
        }
        
        conversations.append(new_conversation)
        save_data(CONVERSATIONS_FILE, conversations)
        
        return jsonify(new_conversation)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/delete/<conversation_id>', methods=['DELETE'])
@login_required
def api_delete_conversation(conversation_id):
    try:
        conversations = load_data(CONVERSATIONS_FILE)
        messages = load_data(MESSAGES_FILE)
        users = load_data(USERS_FILE)
        
        # Vérifier si l'utilisateur existe et est admin
        current_user_data = next((u for u in users if u['id'] == current_user.id), None)
        is_admin = current_user_data and current_user_data.get('role') == 'admin'
        
        # Vérifier si la conversation existe
        conversation = next((c for c in conversations if c['id'] == conversation_id), None)
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
            
        # Vérifier les permissions :
        # 1. L'utilisateur est admin, ou
        # 2. L'utilisateur est le créateur de la conversation
        if not (is_admin or conversation['created_by'] == current_user.id):
            return jsonify({'error': 'Accès non autorisé. Seuls les administrateurs et le créateur peuvent supprimer cette conversation.'}), 403
            
        # Supprimer la conversation
        conversations = [c for c in conversations if c['id'] != conversation_id]
        save_data(CONVERSATIONS_FILE, conversations)
        
        # Supprimer les messages associés
        messages = [m for m in messages if m['conversation_id'] != conversation_id]
        save_data(MESSAGES_FILE, messages)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports', methods=['POST'])
@login_required
def create_report():
    try:
        data = request.get_json()
        if not data or 'type' not in data or 'content' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        reports = load_data(REPORTS_FILE)
        new_report = {
            'id': str(uuid.uuid4()),
            'type': data['type'],
            'content': data['content'],
            'conversation_id': data.get('conversation_id'),
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.id,
            'status': 'pending'
        }
        
        reports.append(new_report)
        save_data(REPORTS_FILE, reports)
        
        return jsonify(new_report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route pour initialiser un utilisateur admin si aucun n'existe
@app.route('/init-admin', methods=['GET'])
def init_admin():
    users = load_data(USERS_FILE)
    
    if not any(u['username'] == 'admin' for u in users):
        admin_user = {
            'id': 'admin',
            'username': 'admin',
            'password': generate_password_hash('admin'),
            'name': 'Administrateur',
            'role': 'admin'
        }
        users.append(admin_user)
        save_data(USERS_FILE, users)
        flash('Utilisateur administrateur créé avec succès. Identifiant: admin, Mot de passe: admin', 'success')
    else:
        flash('Un utilisateur administrateur existe déjà.', 'info')
    
    return redirect(url_for('login'))

@app.route('/admin/create-account', methods=['GET', 'POST'])
@login_required
def create_account():
    if current_user.role != 'admin':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role')
        
        users = load_data(USERS_FILE)
        if any(u['username'] == username for u in users):
            flash('Ce nom d\'utilisateur existe déjà', 'danger')
            return redirect(url_for('create_account'))
        
        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'password': generate_password_hash(password),
            'name': name,
            'role': role
        }
        
        users.append(new_user)
        save_data(USERS_FILE, users)
        flash('Compte créé avec succès', 'success')
        return redirect(url_for('index'))
    
    return render_template('admin/create_account.html')

@app.route('/admin/chat')
@login_required
def chat():
    return render_template('admin/chat.html')

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))
    return render_template('admin/reports.html')

@app.route('/api/conversations')
@login_required
def api_conversations():
    conversations = load_data(CONVERSATIONS_FILE)
    # Filtrer les conversations pour ne montrer que celles de l'utilisateur courant
    if current_user.role != 'admin':
        conversations = [c for c in conversations if current_user.id in c['participants']]
    return jsonify(conversations)

@app.route('/api/messages/<conversation_id>')
@login_required
def api_messages(conversation_id):
    messages = load_data(MESSAGES_FILE)
    conversations = load_data(CONVERSATIONS_FILE)
    
    # Vérifier si l'utilisateur a accès à cette conversation
    conversation = next((c for c in conversations if c['id'] == conversation_id), None)
    if not conversation or (current_user.role != 'admin' and current_user.id not in conversation['participants']):
        return jsonify([])
    
    conversation_messages = [m for m in messages if m['conversation_id'] == conversation_id]
    return jsonify(conversation_messages)

@app.route('/messages/marquer_lu/<message_id>', methods=['POST'])
@login_required
def marquer_message_lu(message_id):
    try:
        messages = load_data(MESSAGES_FILE)
        message_updated = False
        
        for message in messages:
            if message['id'] == message_id:
                # Initialiser le dictionnaire 'lu' si nécessaire
                if 'lu' not in message:
                    message['lu'] = {}
                # Marquer comme lu pour l'utilisateur courant
                message['lu'][current_user.id] = True
                message_updated = True
                break
        
        if message_updated:
            save_data(MESSAGES_FILE, messages)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Message non trouvé'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unread-count')
@login_required
def get_unread_count():
    messages = load_data(MESSAGES_FILE)
    conversations = load_data(CONVERSATIONS_FILE)
    
    # Compter les messages non lus
    unread_count = 0
    for message in messages:
        # Vérifier si le message appartient à une conversation de l'utilisateur
        conversation = next((c for c in conversations if c['id'] == message['conversation_id']), None)
        if (conversation and 
            current_user.id in conversation['participants'] and 
            message['sender_id'] != current_user.id and 
            not message.get('lu', {}).get(current_user.id, False)):
            unread_count += 1
            
    return jsonify({'count': unread_count})

@app.route('/api/reports', methods=['GET', 'POST'])
@login_required
def api_reports():
    if request.method == 'POST':
        data = request.get_json()
        reports = load_data(REPORTS_FILE)
        
        new_report = {
            'id': str(uuid.uuid4()),
            'user_id': current_user.id,
            'user_name': current_user.name,
            'content': data['content'],
            'type': data['type'],
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        reports.append(new_report)
        save_data(REPORTS_FILE, reports)
        return jsonify(new_report)
    
    # GET - Vérifier si l'utilisateur est admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    reports = load_data(REPORTS_FILE)
    return jsonify(reports)

@app.route('/api/reports/<report_id>/resolve', methods=['POST'])
@login_required
def resolve_report(report_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    reports = load_data(REPORTS_FILE)
    
    for report in reports:
        if report['id'] == report_id:
            report['status'] = 'resolved'
            report['resolved_by'] = current_user.id
            report['resolved_at'] = datetime.now().isoformat()
            report['resolution_note'] = data.get('note', '')
            break
    
    save_data(REPORTS_FILE, reports)
    return jsonify({'success': True})

@app.route('/api/reports/<report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    reports = load_data(REPORTS_FILE)
    reports = [r for r in reports if r['id'] != report_id]
    save_data(REPORTS_FILE, reports)
    return jsonify({'success': True})

@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json()
        if not data or 'content' not in data or 'conversation_id' not in data:
            return jsonify({'error': 'Données manquantes'}), 400

        messages = load_data(MESSAGES_FILE)
        conversations = load_data(CONVERSATIONS_FILE)
        
        # Vérifier si l'utilisateur a accès à cette conversation
        conversation = next((c for c in conversations if c['id'] == data['conversation_id']), None)
        if not conversation or current_user.id not in conversation['participants']:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        # Créer le message avec un dictionnaire de statut de lecture
        new_message = {
            'id': str(uuid.uuid4()),
            'conversation_id': data['conversation_id'],
            'sender_id': current_user.id,
            'sender_name': current_user.name,
            'content': data['content'],
            'created_at': datetime.now().isoformat(),
            'lu': {current_user.id: True}  # Le message est automatiquement lu par l'expéditeur
        }
        
        messages.append(new_message)
        save_data(MESSAGES_FILE, messages)
        
        return jsonify(new_message)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route pour créer une nouvelle conversation
@app.route('/api/conversations', methods=['POST'])
@login_required
def api_create_conversation():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400

        conversations = load_data(CONVERSATIONS_FILE)
        
        # S'assurer que les participants sont uniques et incluent l'utilisateur courant
        participants = list(set([current_user.id] + (data.get('participants', []))))
        
        new_conversation = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', 'Nouvelle conversation'),
            'participants': participants,
            'created_at': datetime.now().isoformat()
        }
        
        conversations.append(new_conversation)
        save_data(CONVERSATIONS_FILE, conversations)
        return jsonify(new_conversation)
    except Exception as e:
        print(f"Erreur lors de la création de la conversation: {str(e)}")
        return jsonify({'error': 'Erreur lors de la création de la conversation'}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    conversations = load_data(CONVERSATIONS_FILE)
    messages = load_data(MESSAGES_FILE)
    unread_messages = load_data(UNREAD_MESSAGES_FILE)
    
    # Vérifier si l'utilisateur a accès à cette conversation
    conversation = next((c for c in conversations if c['id'] == conversation_id), None)
    if not conversation or (current_user.role != 'admin' and current_user.id not in conversation['participants']):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Supprimer la conversation
    conversations = [c for c in conversations if c['id'] != conversation_id]
    save_data(CONVERSATIONS_FILE, conversations)
    
    # Supprimer les messages associés
    messages = [m for m in messages if m['conversation_id'] != conversation_id]
    save_data(MESSAGES_FILE, messages)
    
    # Supprimer les messages non lus associés
    unread_messages = [m for m in unread_messages if m['conversation_id'] != conversation_id]
    save_data(UNREAD_MESSAGES_FILE, unread_messages)
    
    return jsonify({'success': True})

@app.route('/admin/panel')
@login_required
@admin_required
def admin_panel():
    # Récupérer toutes les données nécessaires
    users = load_data(USERS_FILE)
    vehicles = load_data(VEHICULES_FILE)
    clients = load_data(CLIENTS_FILE)
    interventions = load_data(INTERVENTIONS_FILE)
    stock = load_data(STOCK_FILE)
    reports = load_data(REPORTS_FILE)
    fournisseurs = load_data(FOURNISSEURS_FILE)
    
    # Statistiques
    stats = {
        'total_users': len(users),
        'total_vehicles': len(vehicles),
        'total_clients': len(clients),
        'total_interventions': len(interventions),
        'total_stock': len(stock),
        'total_fournisseurs': len(fournisseurs),
        'pending_reports': len([r for r in reports if r['status'] == 'pending']),
        'low_stock': len([s for s in stock if s.get('quantite', 0) < STOCK_FAIBLE_SEUIL])}
    
    return render_template('admin/panel.html', 
                         users=users,
                         vehicles=vehicles,
                         clients=clients,
                         interventions=interventions,
                         stock=stock,
                         reports=reports,
                         fournisseurs=fournisseurs,
                         stats=stats)

@app.route('/interventions/heures')
@login_required
def statistiques_heures():
    interventions = load_data(INTERVENTIONS_FILE)
    users = load_data(USERS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    now = datetime.now()
    
    # Calculer les statistiques par utilisateur
    stats_utilisateurs = {}
    for user in users:
        if user['role'] != 'admin':  # Ne pas inclure les admins
            user_interventions = [i for i in interventions if i.get('technicien') == user['name']]
            total_heures = sum(float(i.get('heures', 0)) for i in user_interventions)
            
            stats_utilisateurs[user['name']] = {
                'total_heures': total_heures,
                'nombre_interventions': len(user_interventions),
                'interventions': user_interventions
            }
    
    # Trier les utilisateurs par nombre d'heures
    stats_utilisateurs = dict(sorted(stats_utilisateurs.items(), 
                                   key=lambda x: x[1]['total_heures'], 
                                   reverse=True))
    
    return render_template('interventions/heures.html', 
                         stats_utilisateurs=stats_utilisateurs,
                         now=now)

@app.route('/interventions/mes-heures')
@login_required
def mes_heures():
    interventions = load_data(INTERVENTIONS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    now = datetime.now()
    
    # Filtrer les interventions pour l'utilisateur connecté
    mes_interventions = [i for i in interventions if i.get('technicien') == current_user.name]
    
    # Trier les interventions par date (plus anciennes en premier)
    mes_interventions.sort(key=lambda x: x.get('date', ''))
    
    # Calculer les statistiques
    total_heures = 0
    for intervention in mes_interventions:
        # S'assurer que heures est un nombre
        try:
            heures = float(intervention.get('heures', 0))
        except (ValueError, TypeError):
            heures = 0
            
        total_heures += heures
        
        # Ajouter les infos du véhicule
        if intervention.get('vehicule_id'):
            vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)
            if vehicule:
                intervention['vehicule_info'] = f"{vehicule['marque']} {vehicule['modele']} ({vehicule['immatriculation']})"
    
    stats = {
        'total_heures': total_heures,
        'nombre_interventions': len(mes_interventions),
        'interventions': mes_interventions
    }
    
    return render_template('interventions/mes_heures.html', 
                         stats=stats,
                         vehicules=vehicules,
                         now=now)

@app.route('/interventions/heures_supplementaires', methods=['GET', 'POST'])
@login_required
def heures_supplementaires():
    now = datetime.now()
    
    if request.method == 'POST':
        try:
            # Vérifier que tous les champs requis sont présents
            if not all(key in request.form for key in ['date', 'heures_travaillees', 'description']):
                flash('Tous les champs sont obligatoires', 'danger')
                return render_template('interventions/heures_supplementaires.html', now=now)
            
            # Valider les données
            date = request.form['date']
            heures = float(request.form['heures_travaillees'])
            description = request.form['description'].strip()
            
            if heures <= 0:
                flash('Le nombre d\'heures doit être supérieur à 0', 'danger')
                return render_template('interventions/heures_supplementaires.html', now=now)
            
            if not description:
                flash('La description ne peut pas être vide', 'danger')
                return render_template('interventions/heures_supplementaires.html', now=now)
            
            interventions = load_data(INTERVENTIONS_FILE)
            
            nouvelle_intervention = {
                'id': str(uuid.uuid4()),
                'date': date,
                'type': 'Tâche administrative',
                'description': description,
                'technicien': current_user.name,
                'heures': heures,
                'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            interventions.append(nouvelle_intervention)
            save_data(INTERVENTIONS_FILE, interventions)
            
            flash('Heures supplémentaires ajoutées avec succès!', 'success')
            return redirect(url_for('mes_heures'))
            
        except ValueError:
            flash('Le nombre d\'heures doit être un nombre valide', 'danger')
            return render_template('interventions/heures_supplementaires.html', now=now)
        except Exception as e:
            flash(f'Erreur lors de l\'ajout des heures supplémentaires : {str(e)}', 'danger')
            return render_template('interventions/heures_supplementaires.html', now=now)
    
    return render_template('interventions/heures_supplementaires.html', now=now)

# Routes pour la suppression dans le panel admin
@app.route('/admin/delete/user/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    users = load_data(USERS_FILE)
    users = [u for u in users if u['id'] != user_id]
    save_data(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/admin/delete/vehicle/<vehicle_id>', methods=['DELETE'])
@login_required
def delete_vehicle(vehicle_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    vehicles = load_data(VEHICULES_FILE)
    vehicles = [v for v in vehicles if v['id'] != vehicle_id]
    save_data(VEHICULES_FILE, vehicles)
    return jsonify({'success': True})

@app.route('/admin/delete/client/<client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    clients = load_data(CLIENTS_FILE)
    clients = [c for c in clients if c['id'] != client_id]
    save_data(CLIENTS_FILE, clients)
    return jsonify({'success': True})

@app.route('/admin/delete/intervention/<intervention_id>', methods=['DELETE', 'POST'])
@login_required
def delete_intervention(intervention_id):
    if current_user.role != 'admin':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('liste_interventions'))
    
    interventions = load_data(INTERVENTIONS_FILE)
    interventions = [i for i in interventions if i['id'] != intervention_id]
    save_data(INTERVENTIONS_FILE, interventions)
    
    if request.method == 'DELETE':
        return jsonify({'success': True})
    else:
        flash('Intervention supprimée avec succès', 'success')
        return redirect(url_for('liste_interventions'))

@app.route('/admin/delete/stock/<piece_id>', methods=['DELETE'])
@login_required
def delete_stock(piece_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    stock = load_data(STOCK_FILE)
    stock = [s for s in stock if s['id'] != piece_id]
    save_data(STOCK_FILE, stock)
    return jsonify({'success': True})

@app.route('/admin/heures')
@login_required
def admin_heures():
    if current_user.role != 'admin':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))
    
    # Récupérer toutes les interventions
    interventions = load_data(INTERVENTIONS_FILE)
    
    # Récupérer tous les utilisateurs
    users = load_data(USERS_FILE)
    
    # Récupérer tous les véhicules
    vehicules = load_data(VEHICULES_FILE)
    
    # Associer les informations des véhicules aux interventions
    for intervention in interventions:
        if 'vehicule_id' in intervention:
            vehicule = next((v for v in vehicules if v['id'] == intervention['vehicule_id']), None)
            if vehicule:
                intervention['vehicule_info'] = f"{vehicule.get('marque', '')} {vehicule.get('modele', '')} - {vehicule.get('immatriculation', '')}"
            else:
                intervention['vehicule_info'] = "Véhicule non trouvé"
        else:
            intervention['vehicule_info'] = "Non spécifié"
    
    # Calculer les statistiques par utilisateur
    stats_utilisateurs = {}
    for user in users:
        if user['role'] != 'admin':  # Ne pas inclure les admins
            user_interventions = [i for i in interventions if i.get('technicien') == user['name']]
            total_heures = sum(float(i.get('heures', 0)) for i in user_interventions)
            
            stats_utilisateurs[user['name']] = {
                'nombre_interventions': len(user_interventions),
                'total_heures': total_heures,
                'moyenne_heures': total_heures / len(user_interventions) if user_interventions else 0
            }
    
    return render_template('admin/heures.html', 
                         stats_utilisateurs=stats_utilisateurs,
                         interventions=interventions,
                         users=users)

@app.route('/admin/heures/ajuster', methods=['POST'])
@login_required
def ajuster_heures():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    try:
        data = request.get_json()
        intervention_id = data.get('intervention_id')
        heures = float(data.get('heures', 0))  # Convertir en float et utiliser 0 comme valeur par défaut
        
        if not intervention_id:
            return jsonify({'success': False, 'message': 'ID d\'intervention manquant'})
        
        interventions = load_data(INTERVENTIONS_FILE)
        intervention_trouvee = False
        
        for intervention in interventions:
            if intervention['id'] == intervention_id:
                intervention['heures'] = heures
                intervention_trouvee = True
                break
        
        if not intervention_trouvee:
            return jsonify({'success': False, 'message': 'Intervention non trouvée'})
        
        save_data(INTERVENTIONS_FILE, interventions)
        return jsonify({'success': True, 'message': 'Heures mises à jour avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour : {str(e)}'})

@app.route('/fournisseurs')
@login_required
def liste_fournisseurs():
    fournisseurs = load_data(FOURNISSEURS_FILE)
    return render_template('fournisseurs/liste.html', fournisseurs=fournisseurs)

@app.route('/fournisseurs/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_fournisseur():
    if request.method == 'POST':
        try:
            fournisseurs = load_data(FOURNISSEURS_FILE)
            nouveau_fournisseur = {
                'id': str(uuid.uuid4()),
                'nom': request.form['nom'],
                'contact': request.form['contact'],
                'telephone': request.form['telephone'],
                'email': request.form['email'],
                'adresse': request.form['adresse'],
                'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            fournisseurs.append(nouveau_fournisseur)
            save_data(FOURNISSEURS_FILE, fournisseurs)
            flash('Fournisseur ajouté avec succès!', 'success')
            return redirect(url_for('liste_fournisseurs'))
        except Exception as e:
            flash(f'Erreur lors de l\'ajout du fournisseur : {str(e)}', 'danger')
    
    return render_template('fournisseurs/ajouter.html')

@app.route('/fournisseurs/modifier/<id>', methods=['GET', 'POST'])
@login_required
def modifier_fournisseur(id):
    fournisseurs = load_data(FOURNISSEURS_FILE)
    fournisseur = next((f for f in fournisseurs if f['id'] == id), None)
    
    if not fournisseur:
        flash('Fournisseur non trouvé', 'danger')
        return redirect(url_for('liste_fournisseurs'))
    
    if request.method == 'POST':
        try:
            fournisseur['nom'] = request.form['nom']
            fournisseur['contact'] = request.form['contact']
            fournisseur['telephone'] = request.form['telephone']
            fournisseur['email'] = request.form['email']
            fournisseur['adresse'] = request.form['adresse']
            save_data(FOURNISSEURS_FILE, fournisseurs)
            flash('Fournisseur modifié avec succès!', 'success')
            return redirect(url_for('liste_fournisseurs'))
        except Exception as e:
            flash(f'Erreur lors de la modification du fournisseur : {str(e)}', 'danger')
    
    return render_template('fournisseurs/modifier.html', fournisseur=fournisseur)

@app.route('/fournisseurs/details/<id>')
@login_required
def details_fournisseur(id):
    fournisseurs = load_data(FOURNISSEURS_FILE)
    pieces = load_data(STOCK_FILE)
    fournisseur = next((f for f in fournisseurs if f['id'] == id), None)
    
    if not fournisseur:
        flash('Fournisseur non trouvé', 'danger')
        return redirect(url_for('liste_fournisseurs'))
    
    # Filtrer les pièces associées à ce fournisseur
    pieces_fournisseur = [p for p in pieces if p.get('fournisseur_id') == id]
    
    # Calculer les statistiques
    stats = {
        'nombre_pieces': len(pieces_fournisseur),
        'valeur_stock': sum(p['quantite'] * p['prix_achat'] for p in pieces_fournisseur),
        'pieces_stock_faible': len([p for p in pieces_fournisseur if p['quantite'] < p['quantite_min']])
    }
    
    return render_template('fournisseurs/details.html', 
                         fournisseur=fournisseur,
                         pieces=pieces_fournisseur,
                         stats=stats)

@app.route('/fournisseurs/supprimer/<id>', methods=['DELETE'])
@login_required
def supprimer_fournisseur(id):
    try:
        fournisseurs = load_data(FOURNISSEURS_FILE)
        stock = load_data(STOCK_FILE)
        
        # Vérifier si le fournisseur existe
        fournisseur = next((f for f in fournisseurs if f['id'] == id), None)
        if not fournisseur:
            return jsonify({'success': False, 'message': 'Fournisseur non trouvé'})
        
        # Vérifier si le fournisseur a des pièces associées
        pieces_associees = [p for p in stock if p.get('fournisseur_id') == id]
        if pieces_associees:
            return jsonify({
                'success': False, 
                'message': 'Impossible de supprimer le fournisseur car il a des pièces associées'
            })
        
        # Supprimer le fournisseur
        fournisseurs = [f for f in fournisseurs if f['id'] != id]
        save_data(FOURNISSEURS_FILE, fournisseurs)
        
        return jsonify({'success': True, 'message': 'Fournisseur supprimé avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/planning')
@login_required
def planning():
    plannings = load_data(PLANNINGS_FILE)
    vehicules = load_data(VEHICULES_FILE)
    
    # Ajouter les informations du véhicule à chaque planning
    for planning in plannings:
        vehicule = next((v for v in vehicules if v['id'] == planning['vehicule_id']), None)
        if vehicule:
            planning['vehicule_marque'] = vehicule.get('marque', 'N/A')
            planning['vehicule_modele'] = vehicule.get('modele', 'N/A')
    
    return render_template('admin/planning.html', 
                         plannings=plannings,
                         statuts=PLANNING_STATUTS)

@app.route('/planning/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_planning():
    if request.method == 'POST':
        vehicule_id = request.form.get('vehicule_id')
        date_debut = request.form.get('date_debut')
        date_retour_estimee = request.form.get('date_retour_estimee')
        commentaire = request.form.get('commentaire')
        statut = request.form.get('statut')

        if not vehicule_id or not date_debut or not statut:
            flash('Tous les champs requis doivent être remplis.', 'danger')
            return redirect(url_for('ajouter_planning'))

        if statut not in PLANNING_STATUTS.values():
            flash('Statut invalide.', 'danger')
            return redirect(url_for('ajouter_planning'))

        planning = {
            'id': str(uuid.uuid4()),
            'vehicule_id': vehicule_id,
            'date_debut': date_debut,
            'date_retour_estimee': date_retour_estimee,
            'statut': statut,
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'commentaire': commentaire
        }

        plannings = load_data(PLANNINGS_FILE)
        plannings.append(planning)
        save_data(PLANNINGS_FILE, plannings)

        flash('Planning ajouté avec succès.', 'success')
        return redirect(url_for('planning'))

    vehicules = load_data(VEHICULES_FILE)
    return render_template('admin/ajouter_planning.html', 
                         vehicules=vehicules,
                         statuts=PLANNING_STATUTS)

@app.route('/planning/<id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_planning(id):
    plannings = load_data(PLANNINGS_FILE)
    planning = next((p for p in plannings if p['id'] == id), None)
    
    if not planning:
        flash('Planning non trouvé.', 'danger')
        return redirect(url_for('planning'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire avec get() pour éviter les erreurs
            vehicule_id = request.form.get('vehicule_id')
            date_debut = request.form.get('date_debut')
            date_retour_estimee = request.form.get('date_retour_estimee', '')  # Valeur par défaut vide si non fournie
            statut = request.form.get('statut')
            commentaire = request.form.get('commentaire', '')  # Valeur par défaut vide si non fourni
            
            # Validation des champs requis
            if not vehicule_id or not date_debut or not statut:
                flash('Tous les champs requis doivent être remplis.', 'danger')
                return redirect(url_for('modifier_planning', id=id))
            
            # Mise à jour du planning
            planning['vehicule_id'] = vehicule_id
            planning['date_debut'] = date_debut
            planning['date_retour_estimee'] = date_retour_estimee
            planning['statut'] = statut
            planning['commentaire'] = commentaire
            
            save_data(PLANNINGS_FILE, plannings)
            flash('Planning modifié avec succès!', 'success')
            return redirect(url_for('planning'))
            
        except Exception as e:
            flash(f'Erreur lors de la modification du planning : {str(e)}', 'danger')
            return redirect(url_for('modifier_planning', id=id))
    
    vehicules = load_data(VEHICULES_FILE)
    return render_template('admin/modifier_planning.html', 
                         planning=planning,
                         vehicules=vehicules,
                         statuts=PLANNING_STATUTS)

@app.route('/planning/supprimer/<id>', methods=['POST'])
@login_required
def supprimer_planning(id):
    try:
        plannings = load_data(PLANNINGS_FILE)
        planning = next((p for p in plannings if p['id'] == id), None)
        
        if not planning:
            flash('Planning non trouvé.', 'danger')
            return redirect(url_for('planning'))
        
        plannings.remove(planning)
        save_data(PLANNINGS_FILE, plannings)
        
        flash('Planning supprimé avec succès.', 'success')
        return redirect(url_for('planning'))
    except Exception as e:
        flash(f'Erreur lors de la suppression du planning : {str(e)}', 'danger')
        return redirect(url_for('planning'))

@app.route('/api/vehicules/<vehicule_id>/interventions')
@login_required
def api_interventions_vehicule(vehicule_id):
    interventions = load_data(INTERVENTIONS_FILE)
    vehicule_interventions = [i for i in interventions if i.get('vehicule_id') == vehicule_id]
    return jsonify(vehicule_interventions)

@app.route('/admin/delete/fournisseur/<id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_fournisseur(id):
    try:
        fournisseurs = load_data(FOURNISSEURS_FILE)
        stock = load_data(STOCK_FILE)
        
        # Vérifier si le fournisseur existe
        fournisseur = next((f for f in fournisseurs if f['id'] == id), None)
        if not fournisseur:
            return jsonify({'success': False, 'message': 'Fournisseur non trouvé'})
        
        # Vérifier si le fournisseur a des pièces associées
        pieces_associees = [p for p in stock if p.get('fournisseur_id') == id]
        if pieces_associees:
            return jsonify({
                'success': False, 
                'message': 'Impossible de supprimer le fournisseur car il a des pièces associées'
            })
        
        # Supprimer le fournisseur
        fournisseurs = [f for f in fournisseurs if f['id'] != id]
        save_data(FOURNISSEURS_FILE, fournisseurs)
        
        return jsonify({'success': True, 'message': 'Fournisseur supprimé avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/interventions/<intervention_id>/ajouter-piece', methods=['POST'])
@login_required
def ajouter_piece_intervention(intervention_id):
    try:
        data = request.get_json()
        piece_id = data.get('piece_id')
        quantite = data.get('quantite')
        
        if not piece_id or not quantite:
            return jsonify({'success': False, 'message': 'Données manquantes'})
        
        # Charger les données
        interventions = load_data(INTERVENTIONS_FILE)
        stock = load_data(STOCK_FILE)
        sorties = load_data(SORTIES_FILE)
        
        # Trouver l'intervention
        intervention = next((i for i in interventions if i['id'] == intervention_id), None)
        if not intervention:
            return jsonify({'success': False, 'message': 'Intervention non trouvée'})
        
        # Trouver la pièce
        piece = next((p for p in stock if p['id'] == piece_id), None)
        if not piece:
            return jsonify({'success': False, 'message': 'Pièce non trouvée'})
        
        # Vérifier le stock
        if piece['quantite'] < quantite:
            return jsonify({'success': False, 'message': 'Stock insuffisant'})
        
        # Ajouter la pièce à l'intervention
        intervention['pieces_utilisees'].append({
            'piece_id': piece_id,
            'nom': piece['nom'],
            'prix_unitaire': piece['prix_vente'],
            'quantite': quantite,
            'total': float(piece['prix_vente']) * quantite
        })
        
        # Mettre à jour le stock
        piece['quantite'] -= quantite
        
        # Créer une sortie de pièce
        nouvelle_sortie = {
            'id': str(uuid.uuid4()),
            'piece_id': piece_id,
            'vehicule_id': intervention['vehicule_id'],
            'quantite': quantite,
            'date_sortie': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'utilisateur': current_user.name,
            'intervention_id': intervention_id
        }
        sorties.append(nouvelle_sortie)
        
        # Sauvegarder les modifications
        save_data(INTERVENTIONS_FILE, interventions)
        save_data(STOCK_FILE, stock)
        save_data(SORTIES_FILE, sorties)
        
        return jsonify({'success': True, 'message': 'Pièce ajoutée avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/interventions/<intervention_id>/supprimer-piece/<piece_id>', methods=['DELETE'])
@login_required
def supprimer_piece_intervention(intervention_id, piece_id):
    try:
        # Charger les données
        interventions = load_data(INTERVENTIONS_FILE)
        stock = load_data(STOCK_FILE)
        sorties = load_data(SORTIES_FILE)
        
        # Trouver l'intervention
        intervention = next((i for i in interventions if i['id'] == intervention_id), None)
        if not intervention:
            return jsonify({'success': False, 'message': 'Intervention non trouvée'})
        
        # Trouver la pièce dans l'intervention
        piece_utilisee = next((p for p in intervention['pieces_utilisees'] if p['piece_id'] == piece_id), None)
        if not piece_utilisee:
            return jsonify({'success': False, 'message': 'Pièce non trouvée dans l\'intervention'})
        
        # Trouver la pièce dans le stock
        piece = next((p for p in stock if p['id'] == piece_id), None)
        if piece:
            # Restaurer le stock
            piece['quantite'] += piece_utilisee['quantite']
            save_data(STOCK_FILE, stock)
        
        # Supprimer la pièce de l'intervention
        intervention['pieces_utilisees'] = [p for p in intervention['pieces_utilisees'] if p['piece_id'] != piece_id]
        
        # Supprimer la sortie correspondante
        sorties = [s for s in sorties if not (s['intervention_id'] == intervention_id and s['piece_id'] == piece_id)]
        
        # Sauvegarder les modifications
        save_data(INTERVENTIONS_FILE, interventions)
        save_data(SORTIES_FILE, sorties)
        
        return jsonify({'success': True, 'message': 'Pièce supprimée avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/conversations/<conversation_id>/participants')
@login_required
def get_conversation_participants(conversation_id):
    # Récupérer la conversation
    conversation = next((c for c in load_data(CONVERSATIONS_FILE) if c['id'] == conversation_id), None)
    if not conversation:
        return jsonify({'error': 'Conversation non trouvée'}), 404
        
    # Vérifier que l'utilisateur fait partie de la conversation
    if str(current_user.id) not in conversation['participants']:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    # Récupérer les informations des participants
    participants = []
    for user_id in conversation['participants']:
        user = next((u for u in load_data(USERS_FILE) if u['id'] == user_id), None)
        if user:
            participants.append({
                'id': str(user['id']),
                'name': user['name'],
                'role': user['role']
            })
            
    return jsonify(participants)

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/modifier_statut_planning/<id>', methods=['POST'])
@login_required
def modifier_statut_planning(id):
    plannings = load_data(PLANNINGS_FILE)
    planning = next((p for p in plannings if p['id'] == id), None)
    
    if not planning:
        flash('Planning non trouvé.', 'danger')
        return redirect(url_for('planning'))
    
    nouveau_statut = request.form.get('statut')
    if nouveau_statut not in PLANNING_STATUTS.values():
        flash('Statut invalide.', 'danger')
        return redirect(url_for('planning'))
    
    planning['statut'] = nouveau_statut
    save_data(PLANNINGS_FILE, plannings)
    
    flash(f'Statut du planning modifié en "{nouveau_statut}".', 'success')
    return redirect(url_for('planning'))

@app.route('/admin/modifier_mdp/<user_id>', methods=['POST'])
@login_required
@admin_required
def admin_modifier_mdp(user_id):
    users = load_data(USERS_FILE)
    password = request.form.get('password')
    
    if not password or len(password) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        return redirect(url_for('admin_panel'))
    
    for user in users:
        if user['id'] == user_id:
            user['password'] = generate_password_hash(password)
            save_data(USERS_FILE, users)
            flash('Mot de passe modifié avec succès.', 'success')
            break
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/supprimer_utilisateur/<user_id>', methods=['POST'])
@login_required
@admin_required
def admin_supprimer_utilisateur(user_id):
    # Ne pas permettre la suppression de l'administrateur principal
    if user_id == 'admin':
        flash('Impossible de supprimer l\'administrateur principal.', 'danger')
        return redirect(url_for('admin_panel'))

    users = load_data(USERS_FILE)
    
    # Vérifier si l'utilisateur existe
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Supprimer l'utilisateur
    users = [u for u in users if u['id'] != user_id]
    save_data(USERS_FILE, users)
    
    flash('Utilisateur supprimé avec succès.', 'success')
    return redirect(url_for('admin_panel'))

# Filtre pour calculer le total des pièces
@app.template_filter('total_pieces')
def total_pieces(pieces):
    return sum(float(piece.get('total', 0)) for piece in pieces)

# Filtre pour convertir les retours à la ligne en <br>
@app.template_filter('nl2br')
def nl2br(value):
    if not value:
        return ''
    return value.replace('\n', '<br>')

@app.route('/api/pieces')
def get_pieces():
    pieces = load_data(STOCK_FILE)
    return jsonify(pieces)

@app.route('/stock/inventaire', methods=['POST'])
def update_inventaire():
    try:
        data = request.get_json()
        pieces = load_data(STOCK_FILE)
        
        # Mettre à jour les quantités
        for update in data['updates']:
            piece_id = update['pieceId']
            nouvelle_quantite = int(update['quantite'])
            
            # Trouver et mettre à jour la pièce
            for piece in pieces:
                if str(piece['id']) == str(piece_id):
                    ancienne_quantite = int(piece['quantite'])
                    piece['quantite'] = nouvelle_quantite
                    
                    # Ajouter une entrée dans l'historique
                    historique = load_data(HISTORIQUE_STOCK_FILE)
                    nouvelle_entree = {
                        'id': str(uuid.uuid4()),
                        'piece_id': piece_id,
                        'type': 'inventaire',
                        'ancienne_quantite': ancienne_quantite,
                        'nouvelle_quantite': nouvelle_quantite,
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'commentaire': f"Ajustement lors de l'inventaire (Écart: {nouvelle_quantite - ancienne_quantite})"
                    }
                    historique.append(nouvelle_entree)
                    save_data(HISTORIQUE_STOCK_FILE, historique)
                    break
        
        # Sauvegarder les modifications
        save_data(STOCK_FILE, pieces)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/vehicules/alertes')
@login_required
def alertes_controles():
    vehicules = load_data(VEHICULES_FILE)
    delais = load_data(DELAIS_CONTROLES_FILE)
    today = date.today()
    alertes = []
    
    for vehicule in vehicules:
        # Contrôle technique
        if 'date_dernier_ct' in vehicule:
            dernier_ct = datetime.strptime(vehicule['date_dernier_ct'], '%Y-%m-%d').date()
            prochain_ct = dernier_ct + timedelta(days=delais['ct']['periode'])
            jours_restants = (prochain_ct - today).days
            
            if jours_restants <= delais['ct']['urgent']:
                urgence = 'urgent'
            elif jours_restants <= delais['ct']['attention']:
                urgence = 'attention'
            else:
                urgence = 'ok'
                
            alertes.append({
                'id': f"ct_{vehicule['id']}",
                'vehicule': vehicule,
                'type': 'ct',
                'dernier_controle': vehicule['date_dernier_ct'],
                'prochain_controle': prochain_ct.strftime('%Y-%m-%d'),
                'jours_restants': jours_restants,
                'urgence': urgence
            })
        
        # Mines
        if 'date_dernier_mine' in vehicule:
            dernier_mine = datetime.strptime(vehicule['date_dernier_mine'], '%Y-%m-%d').date()
            prochain_mine = dernier_mine + timedelta(days=delais['mine']['periode'])
            jours_restants = (prochain_mine - today).days
            
            if jours_restants <= delais['mine']['urgent']:
                urgence = 'urgent'
            elif jours_restants <= delais['mine']['attention']:
                urgence = 'attention'
            else:
                urgence = 'ok'
                
            alertes.append({
                'id': f"mine_{vehicule['id']}",
                'vehicule': vehicule,
                'type': 'mine',
                'dernier_controle': vehicule['date_dernier_mine'],
                'prochain_controle': prochain_mine.strftime('%Y-%m-%d'),
                'jours_restants': jours_restants,
                'urgence': urgence
            })
        
        # Tachygraphe
        if 'date_dernier_tachy' in vehicule:
            dernier_tachy = datetime.strptime(vehicule['date_dernier_tachy'], '%Y-%m-%d').date()
            prochain_tachy = dernier_tachy + timedelta(days=delais['tachy']['periode'])
            jours_restants = (prochain_tachy - today).days
            
            if jours_restants <= delais['tachy']['urgent']:
                urgence = 'urgent'
            elif jours_restants <= delais['tachy']['attention']:
                urgence = 'attention'
            else:
                urgence = 'ok'
                
            alertes.append({
                'id': f"tachy_{vehicule['id']}",
                'vehicule': vehicule,
                'type': 'tachy',
                'dernier_controle': vehicule['date_dernier_tachy'],
                'prochain_controle': prochain_tachy.strftime('%Y-%m-%d'),
                'jours_restants': jours_restants,
                'urgence': urgence
            })
        
        # VGP
        if 'date_dernier_vgp' in vehicule:
            dernier_vgp = datetime.strptime(vehicule['date_dernier_vgp'], '%Y-%m-%d').date()
            prochain_vgp = dernier_vgp + timedelta(days=delais['vgp']['periode'])
            jours_restants = (prochain_vgp - today).days
            
            if jours_restants <= delais['vgp']['urgent']:
                urgence = 'urgent'
            elif jours_restants <= delais['vgp']['attention']:
                urgence = 'attention'
            else:
                urgence = 'ok'
                
            alertes.append({
                'id': f"vgp_{vehicule['id']}",
                'vehicule': vehicule,
                'type': 'vgp',
                'dernier_controle': vehicule['date_dernier_vgp'],
                'prochain_controle': prochain_vgp.strftime('%Y-%m-%d'),
                'jours_restants': jours_restants,
                'urgence': urgence
            })
    
    # Trier par urgence puis par date
    alertes.sort(key=lambda x: (
        0 if x['urgence'] == 'urgent' else 1 if x['urgence'] == 'attention' else 2,
        x['prochain_controle']
    ))
    
    return render_template('vehicules/alertes.html', alertes=alertes, delais=delais)

@app.route('/vehicules/controle/effectue', methods=['POST'])
@login_required
def marquer_controle_effectue():
    try:
        data = request.get_json()
        alerte_id = data['alerte_id']
        vehicule_id = data['vehicule_id']
        date = data['date']
        
        type_controle = alerte_id.split('_')[0]  # ct, mine ou tachy
        vehicules = load_data(VEHICULES_FILE)
        
        # Trouver et mettre à jour le véhicule
        for vehicule in vehicules:
            if vehicule['id'] == vehicule_id:
                if type_controle == 'ct':
                    vehicule['date_dernier_ct'] = date
                elif type_controle == 'mine':
                    vehicule['date_dernier_mine'] = date
                elif type_controle == 'tachy':
                    vehicule['date_dernier_tachy'] = date
                elif type_controle == 'vgp':
                    vehicule['date_dernier_vgp'] = date
                break
        
        save_data(VEHICULES_FILE, vehicules)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/alertes/delais', methods=['GET', 'POST'])
@login_required
@admin_required
def gerer_delais_controles():
    if request.method == 'POST':
        delais = {
            'ct': {
                'attention': int(request.form['ct_attention']),
                'urgent': int(request.form['ct_urgent']),
                'periode': int(request.form['ct_periode'])
            },
            'mine': {
                'attention': int(request.form['mine_attention']),
                'urgent': int(request.form['mine_urgent']),
                'periode': int(request.form['mine_periode'])
            },
            'tachy': {
                'attention': int(request.form['tachy_attention']),
                'urgent': int(request.form['tachy_urgent']),
                'periode': int(request.form['tachy_periode'])
            },
            'vgp': {
                'attention': int(request.form['vgp_attention']),
                'urgent': int(request.form['vgp_urgent']),
                'periode': int(request.form['vgp_periode'])
            }
        }
        save_data(DELAIS_CONTROLES_FILE, delais)
        flash('Les délais ont été mis à jour avec succès.', 'success')
        return redirect(url_for('alertes_controles'))
    
    delais = load_data(DELAIS_CONTROLES_FILE)
    return render_template('vehicules/delais_controles.html', delais=delais)

@app.route('/api/vehicules_client/<client_id>')
@login_required
def api_vehicules_client(client_id):
    vehicules = load_data(VEHICULES_FILE)
    vehicules_client = [v for v in vehicules if v.get('client_id') == client_id]
    return jsonify(vehicules_client)

@app.route('/static/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/static/js/service-worker.js')
def serve_service_worker():
    return send_from_directory('static/js', 'service-worker.js', mimetype='text/javascript')

if __name__ == '__main__':
    # Note pour Steven Muncher : Ceci est une application de gestion de Garage Sobeca
    # Configuration pour l'accès local sur mobile
    app.run(host='0.0.0.0', port=5000, debug=True)
