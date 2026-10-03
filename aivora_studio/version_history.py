"""Released versions and the requests they implemented."""

VERSION_HISTORY = (
    (
        "Avant 1.0",
        "Demandes fonctionnelles initiales",
        (
            "Ajouter les types LIVE, STUDIO, EXTRAIT et MAP au titre et au "
            "nom de fichier, autoriser plusieurs types et ne pas suffixer "
            "STUDIO seul.",
            "Investiguer les faux diagnostics de fichiers audio incomplets "
            "et ajouter un outil de réparation audio.",
            "Vérifier que le dossier du fichier correspond au premier artiste, "
            "en ignorant le dossier exclu.",
            "Rendre les fonctionnalités activables individuellement dans les "
            "paramètres et corriger les erreurs de démarrage et de sélection "
            "des types.",
            "Retirer le projet web et conserver uniquement les outils Python.",
        ),
    ),
    (
        "1.0",
        "Nouvelle base Python",
        (
            "Réinitialiser le dépôt et repartir sur une version 1.0 propre.",
            "Conserver uniquement l’application et les outils Python.",
            "Remplacer l’ancien historique par un guide de versionnement.",
        ),
    ),
    (
        "1.0.001",
        "Premier compte à rebours",
        (
            "Ajouter à l’interface un compteur avant la mise à jour prévue "
            "le 9 octobre.",
        ),
    ),
    (
        "1.0.002",
        "Échéance hebdomadaire",
        (
            "Présenter le compte à rebours dans une carte dédiée.",
            "Fixer le rendez-vous des mises à jour au vendredi à 18 h.",
        ),
    ),
    (
        "1.0.003",
        "Personnalisation visuelle",
        (
            "Préparer un aperçu PySide6 distinct de l’application principale, "
            "avec métadonnées, onde visuelle et fenêtres Versions, Anomalies "
            "et Paramètres.",
            "Ajouter un bouton Enregistrer et un style sombre personnalisé, "
            "sans conserver l’apparence système par défaut.",
            "Rendre thèmes et densités interactifs, partager leur style avec "
            "les fenêtres modales et mémoriser les préférences.",
            "Compléter les commandes de démonstration et permettre d’ajouter, "
            "remplacer et supprimer une pochette.",
            "Afficher la cadence des correctifs, les prochaines versions et "
            "la cible majeure 1.1.",
        ),
    ),
    (
        "1.0.004",
        "Lecture des métadonnées",
        (
            "Charger un fichier depuis le sélecteur ou par glisser-déposer.",
            "Lire artiste, titre, album, artiste album, année, genre, BPM, "
            "piste, compositeur et commentaire dans les champs PySide6.",
            "Reconnaître les types dans le suffixe du titre.",
            "Garder le fichier original intact à l’ouverture ; l’écriture "
            "réelle des tags reste prévue pour une version ultérieure.",
            "Consigner les demandes et changements par version dans les "
            "historiques de l’application Python et de l’aperçu Qt.",
        ),
    ),
    (
        "1.0.005",
        "Édition et enregistrement",
        (
            "Enregistrer réellement les métadonnées éditées dans les formats "
            "audio pris en charge, sans toucher au fichier avant validation.",
            "Conserver les types multiples dans le titre et le nommage "
            "automatique des fichiers.",
            "Valider BPM et numéro de piste puis afficher les erreurs "
            "d’écriture ou de remplacement sans annoncer un faux succès.",
        ),
    ),
    (
        "1.0.006",
        "Audio et pochettes",
        (
            "Lire, prévisualiser, remplacer et supprimer les pochettes audio ; "
            "ne les intégrer au fichier qu’après Enregistrer.",
            "Remplacer l’onde fictive par une forme d’onde calculée depuis "
            "l’audio décodé par FFmpeg.",
            "Lire et mettre en pause le fichier, déplacer la tête de lecture "
            "et afficher sa durée réelle.",
            "Estimer le BPM depuis le signal audio et l’écrire dans le champ "
            "BPM, prêt à être enregistré avec les autres tags.",
        ),
    ),
    (
        "1.0.007",
        "Rail réel et déplacement après édition",
        (
            "Remplir le rail PySide6 depuis le dossier exclu avec scan "
            "asynchrone, pagination, actualisation et erreurs visibles.",
            "Activer par défaut le déplacement après enregistrement pour les "
            "fichiers ouverts depuis ce rail, avec option pour le désactiver.",
            "Choisir le dossier de destination à chaque déplacement, proposer "
            "le dossier surveillé configuré et demander confirmation avant "
            "de remplacer un fichier existant.",
            "Ne supprimer la source du dossier exclu qu’après copie réussie "
            "vers la destination.",
        ),
    ),
)
