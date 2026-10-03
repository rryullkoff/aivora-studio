# Feuille de route des versions

La version actuelle est **1.0.007**. Chaque correctif `1.0.xxx` doit rester
petit, testable et faire l'objet de son propre commit. Les nouvelles fonctions
de la refonte PySide6 sont préparées progressivement ; elles ne remplacent pas
l'application principale avant que les parcours existants soient vérifiés.

## Historique des demandes et changements

Chaque entrée consigne les demandes fonctionnelles et les changements connus,
y compris les demandes antérieures à la remise à zéro. L’historique est affiché
dans les fenêtres Versions de l’application Python et de l’aperçu PySide6.
L’entrée « Avant 1.0 » récapitule les fonctions héritées ; l’historique des
versions publiées repart de la nouvelle base 1.0.

### Avant 1.0 — Demandes fonctionnelles initiales

- Ajouter les types `LIVE`, `STUDIO`, `EXTRAIT` et `MAP` au titre et au nom du
  fichier, accepter plusieurs types et laisser `STUDIO` seul sans suffixe.
- Investiguer les faux diagnostics de fichiers audio incomplets et ajouter la
  réparation audio.
- Vérifier la correspondance entre le premier artiste et le dossier du fichier,
  en excluant le dossier dédié.
- Permettre d’activer séparément les fonctionnalités et corriger les erreurs
  des champs et de la sélection des types.
- Retirer le projet web pour garder les outils Python.

### 1.0 — Nouvelle base Python

- Repartir sur une base et un dépôt propres en version 1.0.
- Retirer le projet web et garder l’application et les outils Python.
- Recommencer le guide de versions avec le nouveau cycle de numérotation.

### 1.0.001 — Premier compte à rebours

- Ajouter à l’interface le temps restant jusqu’à la mise à jour annoncée
  pour le 9 octobre.

### 1.0.002 — Échéance hebdomadaire

- Présenter l’échéance dans une carte dédiée plutôt qu’en texte seul.
- Faire du vendredi à 18 h le rendez-vous hebdomadaire des mises à jour.

### 1.0.003 — Personnalisation visuelle

- Préparer un aperçu PySide6 séparé du lancement principal, avec champs de
  métadonnées, forme d’onde illustrative et fenêtres Versions, Anomalies et
  Paramètres.
- Ajouter un bouton Enregistrer dans l’aperçu et personnaliser son apparence.
- Rendre le thème et la densité réglables, les appliquer aussi aux fenêtres
  modales et mémoriser les préférences confirmées.
- Compléter les commandes visuelles et ajouter, remplacer ou supprimer une
  pochette.
- Permettre d’activer et désactiver les fonctions représentées dans l’aperçu.
- Afficher la cadence des correctifs, les prochaines versions et la cible 1.1.

### 1.0.004 — Chargement et lecture des métadonnées

- Ouvrir un fichier avec le sélecteur ou par glisser-déposer.
- Lire avec Mutagen artiste, titre, album, artiste album, année, genre, BPM,
  piste, compositeur et commentaire, puis remplir les champs PySide6.
- Reconnaître les types présents dans le suffixe du titre.
- Ne pas modifier le fichier original lors de son ouverture ; l’écriture
  réelle des tags reste à venir.
- Consigner les demandes et changements par version dans l’historique visible
  de l’application Python et de l’aperçu Qt.

### 1.0.005 — Édition et enregistrement

- Enregistrer les métadonnées éditées depuis l’interface PySide6 pour les
  formats audio pris en charge.
- Préparer une copie temporaire, écrire les tags puis remplacer atomiquement
  le fichier chargé pour protéger l’original en cas d’échec.
- Conserver les types multiples dans le titre et le renommage automatique,
  avec confirmation avant le remplacement d’un nom déjà existant.
- Valider BPM et numéro de piste ; expliquer les erreurs d’écriture et les
  échecs de renommage.
- Avertir si le dossier parent ne correspond pas au premier artiste, sans
  bloquer la sauvegarde.

### 1.0.006 — Audio et pochettes

- **Livré** : extraire et prévisualiser les pochettes des formats audio pris en
  charge ; leur ajout, remplacement ou suppression n’est appliqué qu’après
  Enregistrer.
- **Livré** : calculer une vraie forme d’onde depuis l’audio décodé avec FFmpeg.
- **Livré** : lecture, pause, positionnement et durée réelle avec Qt Multimedia.
- **Livré** : estimer le BPM depuis le signal et remplir le champ BPM avant
  l’enregistrement des métadonnées.

### 1.0.007 — Rail réel et déplacement après édition

- **Livré** : alimenter le rail PySide6 depuis le dossier exclu avec recherche
  asynchrone, pagination et actualisation.
- **Livré** : activer par défaut le déplacement après enregistrement des sons
  ouverts depuis le rail, avec une option dédiée dans les paramètres.
- **Livré** : choisir le dossier de destination à chaque fois ; le dossier
  surveillé configuré est proposé par défaut.
- **Livré** : demander confirmation avant d’écraser un fichier et ne retirer
  la source qu’après la copie réussie.

## Prochains correctifs

### 1.0.008 — Outils et paramètres

- Relier le modal d'anomalies aux résultats réels de la surveillance.
- Migrer la conversion, la réparation et la sélection rapide, avec des erreurs
  explicites et des actions non bloquantes.
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