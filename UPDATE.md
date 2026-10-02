# Feuille de route des versions

La version actuelle est **1.0.002**. Chaque correctif `1.0.xxx` doit rester
petit, testable et faire l'objet de son propre commit. Les nouvelles fonctions
de la refonte PySide6 sont préparées progressivement ; elles ne remplacent pas
l'application principale avant que les parcours existants soient vérifiés.

## Prochains correctifs

### 1.0.003 — Personnalisation visuelle

- Rendre le choix du thème et de la densité réellement interactif dans
  l'aperçu PySide6.
- Centraliser les couleurs, espacements et rayons des composants pour qu'un
  changement de thème s'applique aussi aux fenêtres modales.

### 1.0.004 — Chargement et lecture des métadonnées

- Ouvrir un fichier audio avec le sélecteur ou le glisser-déposer.
- Lire et afficher les tags existants dans les champs PySide6.
- Garder les fichiers originaux inchangés tant que l'utilisateur n'enregistre
  pas.

### 1.0.005 — Édition et enregistrement

- Relier le bouton Enregistrer à l'écriture réelle des tags.
- Conserver les types multiples, le nommage et la vérification des données.
- Afficher clairement les erreurs d'écriture et confirmer le succès seulement
  après une sauvegarde réussie.

### 1.0.006 — Audio et pochettes

- Relier la pochette à l'ouverture, à l'aperçu, au remplacement et à la
  sauvegarde dans le fichier audio.
- Remplacer la forme d'onde fictive par les données réelles et connecter la
  lecture audio ainsi que le BPM.

### 1.0.007 — Outils et anomalies

- Relier le modal d'anomalies aux résultats réels de la surveillance.
- Migrer la conversion, la réparation et la sélection rapide, avec des erreurs
  explicites et des actions non bloquantes.

### 1.0.008 — Paramètres persistants et validation

- Enregistrer et restaurer les choix de thème, de densité et de fonctionnalités.
- Vérifier les parcours principaux sur les formats audio pris en charge et
  corriger les écarts visuels et d'accessibilité.

## Livraison majeure

### 1.1.000 — Refonte PySide6

- Passer PySide6 au lancement par défaut après validation de la parité des
  outils et des paramètres.
- Conserver les fonctions Python existantes ; retirer Tkinter seulement après
  vérification de tous les parcours et de l'installateur Windows.

Le calendrier visé est un petit correctif environ chaque jour et une livraison
majeure environ chaque vendredi à 18 h. Les numéros indiquent l'ordre prévu ;
le contenu peut être ajusté si les tests révèlent un prérequis ou un problème.