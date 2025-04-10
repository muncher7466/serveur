# Application de Gestion de Garage Sobeca

Cette application web permet de gérer un Garage Sobeca avec les fonctionnalités suivantes :
- Gestion des véhicules
- Gestion du stock de pièces détachées
- Suivi des interventions techniques
- Gestion des clients

## Fonctionnalités

### Gestion des véhicules
- Ajout, modification et consultation des véhicules
- Suivi du Compteur
- Historique des interventions par véhicule

### Gestion du stock
- Inventaire des pièces détachées
- Suivi des quantités
- Alertes de stock faible
- Ajustement des quantités

### Suivi des interventions
- Enregistrement des interventions techniques
- Utilisation des pièces du stock
- Calcul automatique des coûts
- Historique complet

### Gestion des clients
- Informations des propriétaires de véhicules
- Liste des véhicules par client

## Installation

1. Assurez-vous d'avoir Python installé (version 3.8 ou supérieure)
2. Double-cliquez sur le fichier `lancer_application.bat` pour installer les dépendances et démarrer l'application

## Utilisation

Après avoir lancé l'application, ouvrez votre navigateur et accédez à :
```
http://localhost:5000
```

## Stockage des données

Toutes les données sont stockées au format JSON dans le dossier `data` :
- `vehicules.json` : Informations sur les véhicules
- `stock.json` : Inventaire des pièces détachées
- `interventions.json` : Historique des interventions
- `clients.json` : Informations sur les clients
