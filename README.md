🚀 Présentation Générale

YouTube Downloader Pro est une application de bureau cross-plateforme (Windows & macOS) moderne et intuitive, développée en Python. Elle permet aux utilisateurs de télécharger, convertir et gérer localement des vidéos et des playlists entières depuis YouTube.

Conçue avec une approche centrée sur l'expérience utilisateur (UX), l'application se distingue par son interface "Dark Mode" épurée, sa capacité à gérer des téléchargements multiples simultanés et sa robustesse technique grâce à l'intégration de moteurs de traitement vidéo avancés.
🌟 Fonctionnalités Clés
1. Gestion de Contenu Avancée

    Support des Playlists : Analyse intelligente des liens pour détecter s'il s'agit d'une vidéo unique ou d'une playlist complète.

    Sélection Granulaire : Affichage de la liste des vidéos détectées avec des cases à cocher, permettant à l'utilisateur de choisir précisément quels fichiers télécharger (ou d'utiliser l'option "Tout sélectionner").

2. Contrôle de la Qualité et des Formats

    Multi-Formats : Choix flexible entre le téléchargement vidéo (MP4) ou l'extraction audio (MP3).

    Résolution Adaptative : Menu déroulant dynamique permettant de choisir la qualité d'image, allant de la haute définition (1080p, 720p) aux résolutions plus légères (480p, 360p, 240p) pour économiser de la bande passante.

    Post-Traitement Automatique : Utilisation intégrée de FFmpeg pour fusionner les meilleurs flux vidéo et audio garantissant la qualité maximale sans désynchronisation.

3. Expérience Utilisateur (UX) & Interface

    Interface Réactive (GUI) : Construite avec Flet (basé sur Flutter), offrant un design Material Design moderne et fluide.

    Tableau de Bord de Progression : Suivi en temps réel avec barre de progression, vitesse de téléchargement, temps restant (ETA) et pourcentage.

    Contrôles de Flux : Possibilité de mettre en Pause, de Reprendre ou d'Annuler un téléchargement en cours à tout moment.

    Internationalisation (i18n) : Détection automatique de la langue du système d'exploitation (Windows/macOS) pour afficher l'interface en Français ou en Anglais.

4. Intégration Système

    Feedback Sonore : Notification audio native à la fin du traitement (compatible macOS et Windows).

    Accès Rapide : Création automatique du dossier de destination (/Videos) et bouton d'ouverture directe du dossier une fois le téléchargement terminé.

    Verrouillage Dimensionnel : Fenêtre optimisée et figée pour garantir que l'interface reste ergonomique sur tous les écrans.

🛠️ Architecture Technique

Le projet repose sur une stack technique robuste et moderne :

    Langage : Python 3.10+

    Frontend : Flet (Framework UI cross-platform).

    Backend / Engine :

        yt-dlp : Le standard de l'industrie pour l'extraction de flux vidéo, gérant les restrictions et les mises à jour de YouTube.

        imageio-ffmpeg : Gestionnaire de binaires FFmpeg autonome (évite à l'utilisateur d'installer des dépendances complexes).

    Threading : Utilisation du multi-threading pour empêcher le gel de l'interface (freezing) durant les opérations lourdes de téléchargement et de conversion.

    OS Interaction : Modules ctypes (Windows API) et subprocess (macOS Shell) pour l'intégration native.

🎯 Utilité et Cas d'Usage

Cette application répond à plusieurs besoins concrets :

    Archivage et Sauvegarde : Permet aux créateurs de contenu de sauvegarder leurs propres vidéos ou aux utilisateurs de conserver des vidéos susceptibles d'être supprimées.

    Consommation Hors-Ligne : Idéal pour regarder des conférences, des tutoriels ou des divertissements dans des zones sans connexion internet (avion, train, zones blanches).

    Usage Éducatif : Facilite la récupération de matériel pédagogique pour les enseignants ou étudiants souhaitant intégrer des extraits vidéo dans des présentations sans dépendre d'une connexion internet en classe.

    Conversion Audio : Permet de transformer facilement des podcasts vidéo ou des clips musicaux en fichiers MP3 pour une écoute sur mobile ou baladeur.

📱 Évolutivité (Mobile)

Une version allégée pour Android a également été prototypée. Elle adapte l'interface aux écrans tactiles et utilise une logique de téléchargement simplifiée (sans dépendance binaire lourde) pour respecter les contraintes de l'environnement mobile (sandboxing, stockage).
💡 Le mot du développeur

    "Ce projet a été conçu pour combler le fossé entre les outils en ligne de commande puissants mais complexes (comme yt-dlp) et les utilisateurs finaux qui désirent une interface graphique simple, belle et fonctionnelle. Il démontre la puissance de Python pour créer des applications de bureau complètes."
