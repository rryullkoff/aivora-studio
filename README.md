# Aivora Studio

Aivora Studio est une application Windows pour modifier les métadonnées audio,
gérer les pochettes et organiser les fichiers.

## Lancer l'application

Double-clique sur **Start Aivora Studio.bat**. Au premier démarrage, le lanceur
crée un environnement Python isolé, installe si nécessaire les dépendances de
[`requirements.txt`](./requirements.txt), puis démarre l'application. Les
démarrages suivants réutilisent cet environnement sans réinstaller les paquets.

Python 3 doit être installé sur Windows et accessible via `py`, `python` ou
`python3`. Une connexion Internet est nécessaire au premier démarrage pour
télécharger les dépendances.

Pour lancer l'application manuellement après l'installation :

```powershell
.\.venv\Scripts\python.exe -m aivora_studio
```

## Organisation du code

- [`aivora_studio/app.py`](./aivora_studio/app.py) assemble la fenêtre principale.
- [`aivora_studio/interface.py`](./aivora_studio/interface.py) contient
  l'interface et l'historique des versions.
- [`aivora_studio/editor.py`](./aivora_studio/editor.py) gère le chargement,
  l'édition et l'enregistrement des métadonnées.
- [`aivora_studio/covers.py`](./aivora_studio/covers.py) gère les pochettes.
- [`aivora_studio/audio_tools.py`](./aivora_studio/audio_tools.py) gère
  l'analyse BPM et la forme d'onde.
- [`aivora_studio/monitoring.py`](./aivora_studio/monitoring.py) gère la
  conversion, la réparation et la surveillance du dossier audio.
- [`aivora_studio/config.py`](./aivora_studio/config.py) contient la version,
  les couleurs et les paramètres.

Le fichier [`audio_metadata_editor.py`](./audio_metadata_editor.py) reste
disponible comme ancien point de lancement.

## Fonctions

- Chargement audio par sélection ou glisser-déposer.
- Édition des métadonnées et des pochettes.
- Types `LIVE`, `STUDIO`, `EXTRAIT` et `MAP`, combinables et ajoutés au titre
  et au nom de fichier (ex. `NOM DU SON (LIVE + STUDIO)`). `STUDIO` seul
  conserve le titre et le nom de fichier standard.
- Réparation audio par FFmpeg ; l'original n'est remplacé qu'après validation
  du fichier réparé.
- Conversion en MP3, analyse BPM et surveillance du dossier configuré dans
  `aivora_studio/config.py`.
- Guide et numérotation des versions accessibles en cliquant sur le badge de version.
- Guide des versions : grandes mises à jour environ chaque semaine (1.0, 1.1,
  1.2…) et petits correctifs environ chaque jour (1.0.001, 1.0.002…). Chaque
  petit correctif est livré dans un commit séparé ; les nouvelles fonctionnalités
  sont regroupées dans une livraison hebdomadaire (1.1.000, 1.2.000…). Une
  carte dans l’interface compte le temps restant jusqu’à chaque vendredi
  à 18 h, à partir du 9 octobre 2026.
- Forme d'onde audio lissée, redessinée en haute résolution avec un dégradé
  doux.
- Fenêtre Paramètres pour personnaliser la palette, les dossiers surveillés
  et l'intervalle de vérification. Les préférences restent sur cet ordinateur.
- Paramètres pour activer ou désactiver séparément le rail de sélection,
  l'édition des pochettes, l'analyse BPM/forme d'onde, la surveillance,
  la conversion, la réparation, le renommage, le contrôle du dossier artiste,
  les types de piste et les majuscules automatiques.
- Vérification après enregistrement : le nom du dossier doit correspondre au
  premier artiste. Les fichiers du dossier exclu et de ses sous-dossiers sont
  ignorés ; un emplacement incorrect affiche un avertissement sans bloquer
  l'enregistrement. Cette vérification peut être désactivée dans les paramètres.
- Typographie cohérente et commandes avec retour visuel au survol et au clavier.
- Rail « Sélection rapide » pour ouvrir les fichiers audio du dossier exclu,
  avec pagination et indication du fichier chargé.

Les paramètres locaux sont enregistrés dans `%APPDATA%\Aivora Studio\settings.json`.

Version actuelle : **1.0.002**.
