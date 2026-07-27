# Backlog initial priorisé — eXalt Onboarding Digital

**Version :** 1.0 — livrable de cadrage 4/6  
**Date :** 25 juillet 2026  
**Statut :** validé par Jonathan le 25 juillet 2026  
**Références :**

- `MATRICE_ROLES_PERMISSIONS_EXALT.md` version 1.1 validée ;
- `MODELE_DONNEES_EXALT.md` version 1.0 validée ;
- `ROADMAP_MVP_V1_V2_EXALT.md` version 1.0 validée ;
- décisions `DEC-001` à `DEC-417` et arbitrages validés des ateliers 1 à 34.

---

# 1. Objet du document

Ce backlog transforme la roadmap validée en unités de réalisation testables et ordonnées. Il constitue la référence initiale pour les agents IA, les revues de Jonathan et le futur suivi GitHub.

Il ne remplace ni la matrice des permissions, ni le modèle de données, ni les critères de sortie des lots. En cas de divergence, la décision validée la plus récente et le document spécialisé correspondant prévalent.

# 2. Règles de structuration

## 2.1 Hiérarchie

```text
Version → Lot / Epic → User story → Tâches techniques → Tests et preuves
```

- un lot correspond à une porte de validation de la roadmap ;
- une user story produit une valeur démontrable ou garantit un invariant technique indispensable ;
- les tâches techniques sont créées au moment de préparer le lot ;
- une story ne peut pas être déclarée terminée sans ses tests et sa documentation utile.

## 2.2 Priorités

| Priorité | Sens | Règle |
|---|---|---|
| `P0` | Bloquant de lot ou de sécurité | Doit être terminé pour franchir la porte |
| `P1` | Important dans le périmètre validé | Doit normalement être terminé dans le lot, sauf arbitrage explicite |
| `P2` | Amélioration différable | Ne commence qu’après les P0 et P1 du lot |

Une exigence de sécurité, d’intégrité, d’isolation multi-entités ou de protection des données est toujours au minimum `P0`.

## 2.3 Tailles relatives

| Taille | Interprétation |
|---|---|
| `S` | Changement local, peu de dépendances |
| `M` | Plusieurs composants ou règles simples |
| `L` | Fonction complète avec tests de bout en bout |
| `XL` | Sujet transversal à découper en sous-tâches avant réalisation |

Ces tailles servent à détecter la complexité. Elles ne constituent pas une promesse de durée.

## 2.4 États

| État | Usage |
|---|---|
| `Planned` | Définie mais lot non ouvert |
| `Ready` | Critères d’entrée remplis et lot ouvert par Jonathan |
| `In progress` | Réalisation commencée |
| `Review` | Démonstration, tests et revue en cours |
| `Done` | Critères d’acceptation et définition de terminé satisfaits |
| `Blocked` | Dépendance ou décision empêche d’avancer |
| `Deferred` | Déplacée par décision formelle |

Seul le lot actuellement validé pour réalisation peut contenir des stories `Ready` ou `In progress`.

# 3. Définition de Ready

Une story peut passer à `Ready` lorsque :

- son besoin et son périmètre sont compris ;
- ses critères d’acceptation sont vérifiables ;
- ses dépendances obligatoires sont terminées ;
- les règles de droits et de données concernées sont identifiées ;
- les maquettes ou contenus indispensables sont disponibles, ou une solution provisoire validée existe ;
- une story `XL` a été découpée en tâches ou sous-stories ;
- Jonathan a ouvert le lot correspondant.

# 4. Définition de Done

Une story est `Done` lorsque :

- tous ses critères d’acceptation réussissent ;
- les tests unitaires, intégration, API, UI et sécurité pertinents sont présents ;
- les permissions autorisées et refusées sont testées ;
- les migrations et données de test sont incluses si nécessaire ;
- l’accessibilité et le responsive sont vérifiés pour toute interface ;
- les logs, audits, métriques et erreurs utiles sont ajoutés ;
- aucun secret ni donnée réelle n’est versionné ;
- la documentation d’exploitation ou d’usage est mise à jour ;
- la CI est verte ;
- la démonstration est acceptée dans la revue du lot.

# 5. Vue synthétique du MVP

| Lot | Epic | Porte | Stories | P0 | P1 |
|---:|---|---|---:|---:|---:|
| 0 | Référentiel projet et préparation | G0 | 7 | 6 | 1 |
| 1 | Monorepo, qualité et environnement local | G1 | 8 | 7 | 1 |
| 2 | Socle de données et isolation multi-entités | G2 | 8 | 7 | 1 |
| 3 | Authentification, sessions et sécurité applicative | G3 | 8 | 7 | 1 |
| 4 | Portail national, sélection d’entité et navigation | G4 | 7 | 5 | 2 |
| 5 | Collaborateurs, profils et organisation | G5 | 8 | 7 | 1 |
| 6 | Framework, cercles, bureaux et contenus éditoriaux | G6 | 7 | 5 | 2 |
| 7 | Fiches d’arrivée et onboarding | G7 | 8 | 8 | 0 |
| 8 | Événements et accueil dynamique | G8 | 6 | 4 | 2 |
| 9 | Back-office, administration et import CSV | G9 | 8 | 6 | 2 |
| 10 | Audit, reporting, supervision fonctionnelle et support | G10 | 8 | 5 | 3 |
| 11 | Médias, worker et tâches planifiées | G11 | 8 | 7 | 1 |
| 12 | Qualité transversale, sécurité, accessibilité et performance | G12 | 8 | 8 | 0 |
| 13 | Production temporaire locale | G13 | 6 | 5 | 1 |
| 14 | Préparation et ouverture de la production générale | G14 | 7 | 7 | 0 |

Le backlog MVP initial contient **112 user stories**, dont **94 P0**. Les stories P0 matérialisent principalement les exigences Must, la sécurité, les données, l’isolation, la recette et l’exploitation.

# 6. Backlog MVP détaillé

# EPIC MVP-L00 — Référentiel projet et préparation

**Porte de validation :** `G0`  
**État initial :** `Planned`  
**Dépendance principale :** Aucune.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L00-US001` | P0 | Jonathan | Créer le dépôt GitHub privé et l’arborescence documentaire de référence. | Le dépôt est privé; les dossiers produit, architecture, décisions et opérations existent; les droits sont limités aux personnes autorisées. | — | S |
| `MVP-L00-US002` | P0 | Équipe projet | Versionner la matrice des droits, le modèle de données, la roadmap et le backlog validés. | Chaque document possède une version, un statut, une date et des références croisées; aucune décision n’est perdue. | US001 | S |
| `MVP-L00-US003` | P0 | Jonathan | Définir les conventions Git, branches, commits, tags et revues. | Les règles sont documentées; une PR est obligatoire; les branches et tags suivent une convention stable. | US001 | S |
| `MVP-L00-US004` | P0 | Jonathan/ESM | Définir le schéma initial du CSV collaborateurs. | Les colonnes, formats, valeurs obligatoires, listes contrôlées et erreurs sont documentés; l’e-mail officiel est obligatoire. | US002 | M |
| `MVP-L00-US005` | P1 | Tess/Léa/Diane | Inventorier les contenus du prototype à reprendre. | Les textes de présentation, descriptions de cercles, descriptions de bureaux et liens sont listés avec propriétaire et statut de relecture. | US002 | M |
| `MVP-L00-US006` | P0 | Jonathan | Créer le registre des dépendances externes et des questions ouvertes. | Chaque dépendance possède responsable, échéance, impact, statut et caractère bloquant. | US002 | S |
| `MVP-L00-US007` | P0 | Développeur | Fournir les modèles de configuration sans secrets. | Un `.env.example` documenté existe; aucune valeur réelle ni donnée collaborateur n’est versionnée. | US001 | S |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G0` avant l’ouverture du lot suivant.

---

# EPIC MVP-L01 — Monorepo, qualité et environnement local

**Porte de validation :** `G1`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L01-US001` | P0 | Développeur | Initialiser le monorepo avec les applications et packages validés. | Les répertoires web, api, worker, ui, contracts, infra et docs sont exécutables et documentés. | L00 | M |
| `MVP-L01-US002` | P0 | Développeur | Démarrer la stack Docker locale complète sur le Mac M5. | PostgreSQL, Redis, MinIO, Mailpit, Caddy, web, API et worker démarrent avec une commande; les volumes survivent au redémarrage. | US001 | L |
| `MVP-L01-US003` | P0 | Exploitant | Exposer les endpoints de santé live, ready et version. | Chaque endpoint retourne un statut explicite; readiness vérifie les dépendances nécessaires; la version correspond au build. | US002 | M |
| `MVP-L01-US004` | P0 | Exploitant | Produire des logs JSON corrélés. | Chaque requête et job possède un correlation_id; aucun secret n’est journalisé; la rotation est configurable. | US002 | M |
| `MVP-L01-US005` | P0 | Équipe projet | Mettre en place la CI de qualité et sécurité. | Lint, formatage, types, tests, migrations, secrets et vulnérabilités sont contrôlés; une erreur bloque la PR. | US001 | L |
| `MVP-L01-US006` | P0 | Exploitant | Construire et publier des images ARM64/AMD64 dans GHCR privé. | Une même version immuable fonctionne sur Apple Silicon et AMD64; l’accès au registre est authentifié. | US005 | L |
| `MVP-L01-US007` | P1 | Développeur | Créer le socle du design system et du contrat API. | Les tokens, composants de base et génération/partage des contrats sont initialisés sans dépendance visuelle arbitraire. | US001 | M |
| `MVP-L01-US008` | P0 | Jonathan | Documenter lancement, arrêt, réinitialisation et diagnostic local. | Les procédures fonctionnent depuis une machine propre et identifient les ports, volumes et commandes utiles. | US002 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G1` avant l’ouverture du lot suivant.

---

# EPIC MVP-L02 — Socle de données et isolation multi-entités

**Porte de validation :** `G2`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L02-US001` | P0 | Super-administrateur | Créer et configurer une entité. | Une entité possède UUID, nom, statut, paramètres et domaines autorisés; l’archivage ne supprime pas l’historique. | L01 | L |
| `MVP-L02-US002` | P0 | Administrateur | Créer une personne et son appartenance principale. | Une personne globale possède un e-mail normalisé unique; une seule appartenance principale active est possible. | US001 | L |
| `MVP-L02-US003` | P0 | Administrateur | Gérer les catalogues métier et clients. | Métiers, statuts, clients globaux, activations locales et alias sont historisables; les rapprochements ne fusionnent rien automatiquement. | US001 | L |
| `MVP-L02-US004` | P0 | ESM | Historiser DSM, client, cercle et responsabilités. | Toute modification clôture la relation précédente et crée une nouvelle période; les chevauchements interdits sont rejetés. | US002,US003 | XL |
| `MVP-L02-US005` | P0 | Plateforme | Faire respecter les contraintes de rôles et périmètres. | Un seul Booster actif par cercle; DG implique DSM local; aucune responsabilité métier active dans plusieurs entités. | US004 | L |
| `MVP-L02-US006` | P0 | Plateforme | Bloquer toute référence croisée non autorisée entre entités. | Les contraintes SQL et services refusent les relations incohérentes; les tests démontrent l’absence de fuite. | US001-US005 | L |
| `MVP-L02-US007` | P1 | Développeur | Générer un jeu de données fictif représentatif. | Le générateur produit jusqu’à 25 entités et 5 000 profils avec historiques cohérents et cas limites. | US001-US006 | M |
| `MVP-L02-US008` | P0 | Développeur | Créer et tester les migrations Alembic initiales. | Une base vide est construite uniquement par migrations; les migrations sont testées sur PostgreSQL réel. | US001-US006 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G2` avant l’ouverture du lot suivant.

---

# EPIC MVP-L03 — Authentification, sessions et sécurité applicative

**Porte de validation :** `G3`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L03-US001` | P0 | Collaborateur | Demander un magic link sans révéler l’existence du compte. | La réponse est générique; seuls les profils actifs et autorisés reçoivent un lien; Mailpit capte le message en recette. | L02 | L |
| `MVP-L03-US002` | P0 | Collaborateur | Consommer un magic link à usage unique. | Le lien expire après 15 minutes; le dernier invalide les précédents; un second usage échoue sans exposer le jeton. | US001 | L |
| `MVP-L03-US003` | P0 | Administrateur | Se connecter avec un compte local sécurisé. | Le mot de passe est correctement haché; les tentatives sont limitées; le verrouillage et la récupération sont audités. | L02 | L |
| `MVP-L03-US004` | P0 | Utilisateur | Utiliser une session sécurisée et se déconnecter. | Cookie HttpOnly/Secure/SameSite; inactivité 7 jours; durée absolue 30 jours; déconnexion et révocation effectives. | US002,US003 | L |
| `MVP-L03-US005` | P0 | Plateforme | Protéger les écritures contre CSRF et doubles soumissions. | Les requêtes sensibles exigent la protection prévue; les clés d’idempotence empêchent les effets multiples. | US004 | M |
| `MVP-L03-US006` | P0 | Administrateur | Révoquer immédiatement les accès au départ. | L’archivage d’un collaborateur invalide sessions, invitations et futurs magic links dans la même action métier. | US004 | M |
| `MVP-L03-US007` | P1 | Intégration interne | Utiliser un compte de service à périmètre minimal. | Le jeton est révocable, expirant et limité à des scopes; chaque appel est audité. | US004 | M |
| `MVP-L03-US008` | P0 | Jonathan | Auditer les événements d’authentification et alertes. | Succès, échecs, limitations, verrouillages et révocations sont tracés sans mot de passe ni lien complet. | US001-US007 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G3` avant l’ouverture du lot suivant.

---

# EPIC MVP-L04 — Portail national, sélection d’entité et navigation

**Porte de validation :** `G4`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L04-US001` | P0 | Employé | Choisir une entité depuis la page nationale. | La liste accessible précède la carte sur mobile; seules les entités actives sont proposées; le choix est mémorisé pour la session. | L03 | L |
| `MVP-L04-US002` | P0 | Employé | Changer d’entité consultée à tout moment. | L’entité active reste visible; le changement recharge les données autorisées; aucune permission locale n’est transférée. | US001 | M |
| `MVP-L04-US003` | P0 | Utilisateur mobile | Naviguer avec une barre inférieure responsive. | Les rubriques principales restent accessibles à 320 et 390 px; le focus et les libellés sont corrects. | US001 | L |
| `MVP-L04-US004` | P0 | Utilisateur desktop | Naviguer avec les layouts tablette et bureau. | La navigation est cohérente à 768, 1280 et 1920 px; le clavier permet d’atteindre toutes les actions. | US001 | M |
| `MVP-L04-US005` | P0 | Utilisateur | Voir uniquement les menus correspondant à ses droits. | Les menus masquent les actions non pertinentes; l’API refuse néanmoins toute action non autorisée. | US002 | M |
| `MVP-L04-US006` | P1 | Utilisateur | Comprendre une perte de connexion ou une erreur. | Un état hors connexion après chargement, des pages 403/404/500 et un identifiant de corrélation sont disponibles. | L01 | M |
| `MVP-L04-US007` | P1 | Équipe design | Stabiliser les composants de navigation et retours système. | Boutons, menus, alertes, loaders, états vides et notifications sont documentés et accessibles. | L01 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G4` avant l’ouverture du lot suivant.

---

# EPIC MVP-L05 — Collaborateurs, profils et organisation

**Porte de validation :** `G5`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L05-US001` | P0 | Employé | Consulter un trombinoscope paginé. | La pagination propose 25, 50 ou 100 éléments; seules les données autorisées et miniatures sont retournées. | L04 | L |
| `MVP-L05-US002` | P0 | Employé | Rechercher et filtrer les collaborateurs. | La recherche démarre après environ 300 ms; filtres entité, cercle, DSM, client, métier et statut sont combinables et performants. | US001 | L |
| `MVP-L05-US003` | P0 | Employé | Utiliser une carte retournable accessible. | Le recto/verso fonctionne au clic, toucher et clavier; une alternative reduced-motion existe; “Voir plus” ouvre le profil. | US001 | M |
| `MVP-L05-US004` | P0 | Employé | Consulter une fiche profil complète. | Métier, statut, client, DSM, cercles, responsabilités, présentation et fun fact respectent les règles de visibilité. | US001 | L |
| `MVP-L05-US005` | P0 | Collaborateur | Gérer une photo facultative avec autorisation. | Sans autorisation, avatar neutre; retrait possible; la photo originale n’est pas servie dans la liste. | US004 | L |
| `MVP-L05-US006` | P0 | Responsable autorisé | Modifier un profil dans son périmètre. | DSM, ESM, Booster, responsable de bureau et administrateurs sont limités exactement par la matrice; les refus sont testés. | US004 | XL |
| `MVP-L05-US007` | P0 | ESM/Administrateur | Archiver et restaurer un profil. | L’archivage révoque l’accès et clôture les relations; la restauration suit les rôles validés et exige les contrôles nécessaires. | US006 | L |
| `MVP-L05-US008` | P1 | Responsable autorisé | Consulter l’historique organisationnel pertinent. | Les périodes DSM, client, cercle et responsabilités sont lisibles sans exposer les audits techniques. | US006 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G5` avant l’ouverture du lot suivant.

---

# EPIC MVP-L06 — Framework, cercles, bureaux et contenus éditoriaux

**Porte de validation :** `G6`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L06-US001` | P0 | Employé | Découvrir le Framework depuis une page synthétique. | Les catégories et responsabilités sont compréhensibles; les cartes mènent aux pages détaillées. | L05 | M |
| `MVP-L06-US002` | P0 | Employé | Consulter les pages des cercles. | Les huit cercles initiaux sont configurables; couleur, description, membres et Booster sont affichés sans reposer uniquement sur la couleur. | US001 | L |
| `MVP-L06-US003` | P0 | Employé | Consulter les pages des bureaux. | BDS, BDE et BDG sont configurables; un à trois responsables actifs sont affichés. | US001 | L |
| `MVP-L06-US004` | P0 | Responsable autorisé | Éditer un contenu avec des blocs contrôlés. | Aucun HTML arbitraire; les blocs autorisés sont validés; le périmètre suit la matrice. | US002,US003 | XL |
| `MVP-L06-US005` | P0 | ESM | Gérer la présentation et les liens internes de l’entité. | Présentation, Hub, Academy et SharePoint sont modifiables localement; les URL sont validées. | US004 | M |
| `MVP-L06-US006` | P1 | Éditeur | Prévisualiser puis publier un contenu. | Brouillon et publication sont distingués; la version publiée est identifiable; les modifications sont auditées. | US004 | L |
| `MVP-L06-US007` | P1 | Équipe contenu | Reprendre les textes validés du prototype. | Seuls les textes et liens autorisés, relus et attribués à un propriétaire sont publiés. | L00,US004 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G6` avant l’ouverture du lot suivant.

---

# EPIC MVP-L07 — Fiches d’arrivée et onboarding

**Porte de validation :** `G7`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L07-US001` | P0 | Nouveau collaborateur | Compléter sa fiche d’arrivée. | Les champs organisationnels préremplis sont verrouillés; présentation obligatoire; photo et fun fact restent facultatifs. | L05 | L |
| `MVP-L07-US002` | P0 | Responsable autorisé | Valider et publier une fiche d’arrivée. | La publication peut précéder l’arrivée; les corrections ultérieures sont limitées aux rôles autorisés et auditées. | US001 | M |
| `MVP-L07-US003` | P0 | Administrateur onboarding | Créer et versionner un modèle mission ou intercontrat. | Le catalogue de tâches utilise des identifiants stables; duplication, ordre, archivage et version sont gérés. | L02,L05 | XL |
| `MVP-L07-US004` | P0 | Plateforme | Créer un onboarding depuis la date d’arrivée. | Le bon modèle est instancié; les échéances sont calculées; l’instance reste liée à la version utilisée. | US003 | L |
| `MVP-L07-US005` | P0 | Nouveau collaborateur | Terminer et annuler une tâche pendant cinq minutes. | La progression et la prochaine étape sont recalculées; l’annulation n’est possible que pendant la fenêtre validée. | US004 | L |
| `MVP-L07-US006` | P0 | ESM/Administrateur/Superadmin | Réouvrir une tâche après cinq minutes. | Seuls les trois rôles validés peuvent agir; le motif et l’ancien/nouvel état sont audités. | US005 | M |
| `MVP-L07-US007` | P0 | Plateforme | Changer automatiquement de parcours mission/intercontrat. | Les tâches communes terminées sont conservées par identifiant stable; l’ancien parcours est archivé sans perte d’historique. | US003-US005 | XL |
| `MVP-L07-US008` | P0 | Responsable autorisé | Suivre les onboardings dans son périmètre. | ESM, DSM et Booster voient uniquement leur périmètre; les onboardings terminés sont archivés et consultables selon droits. | US004-US007 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G7` avant l’ouverture du lot suivant.

---

# EPIC MVP-L08 — Événements et accueil dynamique

**Porte de validation :** `G8`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L08-US001` | P0 | Employé | Consulter l’accueil d’une entité dans l’ordre validé. | Présentation, Framework, arrivées récentes, événements et liens apparaissent dans l’ordre défini. | L06,L07 | L |
| `MVP-L08-US002` | P0 | Employé | Voir les arrivées récentes pendant un mois. | Une fiche validée apparaît immédiatement; elle quitte automatiquement la section un mois après la date d’arrivée. | L07 | M |
| `MVP-L08-US003` | P0 | Employé | Consulter les événements à venir et passés. | Les onglets sont distincts; le classement bascule après la fin; un événement annulé reste visible avec badge. | L06 | L |
| `MVP-L08-US004` | P0 | Responsable autorisé | Créer, modifier, annuler et archiver un événement. | Les rôles et périmètres suivent la matrice; début/fin sont validés; aucune inscription ou participant n’est géré. | US003 | L |
| `MVP-L08-US005` | P1 | Employé | Lire une vidéo d’accueil uniquement sur action. | Aucun autoplay; commandes lecture et volume; chargement complet différé; sous-titres facultatifs si fournis. | L06 | M |
| `MVP-L08-US006` | P1 | Employé | Accéder rapidement aux ressources internes. | Les cartes Hub, Academy et SharePoint utilisent les liens configurés et indiquent clairement l’ouverture externe. | L06 | S |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G8` avant l’ouverture du lot suivant.

---

# EPIC MVP-L09 — Back-office, administration et import CSV

**Porte de validation :** `G9`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L09-US001` | P0 | Administrateur d’entité | Consulter un tableau de bord administratif. | Profils actifs, arrivées futures, onboardings, retards, profils incomplets et derniers imports sont comptabilisés dans son entité. | L05-L08 | L |
| `MVP-L09-US002` | P0 | Administrateur | Gérer collaborateurs et affectations individuellement. | CRUD, archivage, restauration et changements structurants respectent transactions, historique et matrice. | L05 | XL |
| `MVP-L09-US003` | P1 | Administrateur | Effectuer des opérations de masse contrôlées. | La prévisualisation indique l’impact; les opérations sont idempotentes et auditées; les erreurs partielles sont explicites. | US002 | L |
| `MVP-L09-US004` | P0 | Administrateur | Téléverser et prévisualiser un CSV réel. | Le fichier est analysé sans écrire en base; erreurs, avertissements, doublons et rapprochements sont détaillés. | L00,L02 | XL |
| `MVP-L09-US005` | P0 | Administrateur | Valider les rapprochements de clients et corrections de mapping. | Aucune fusion automatique; chaque décision humaine est mémorisée dans le lot d’import. | US004 | L |
| `MVP-L09-US006` | P0 | Administrateur | Importer uniquement les lignes valides et obtenir un rapport. | Créations, mises à jour, rejets et avertissements sont comptés; les lignes sans e-mail sont bloquées; le fichier a une empreinte. | US004,US005 | XL |
| `MVP-L09-US007` | P0 | Super-administrateur | Créer une nouvelle entité depuis des modèles génériques. | Aucune donnée Bordeaux n’est copiée; rôles, contenus et onboarding génériques sont initialisés puis configurables. | L02,L06,L07 | L |
| `MVP-L09-US008` | P1 | Administrateur | Restaurer les ressources archivées autorisées. | Les restaurations simples suivent la matrice; les restaurations techniques ou massives restent réservées aux rôles prévus. | US002 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G9` avant l’ouverture du lot suivant.

---

# EPIC MVP-L10 — Audit, reporting, supervision fonctionnelle et support

**Porte de validation :** `G10`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L10-US001` | P0 | Administrateur autorisé | Consulter un journal d’audit filtrable. | Résumé lisible, données structurées, ancien/nouveau pertinent, motif et corrélation sont disponibles selon le périmètre. | L03-L09 | XL |
| `MVP-L10-US002` | P0 | Plateforme | Appliquer la politique de contenu et conservation de l’audit. | Aucun secret, magic link, CSV complet ou e-mail brut; conservation un an; accès et export eux-mêmes audités. | US001 | L |
| `MVP-L10-US003` | P0 | Responsable autorisé | Consulter les indicateurs collaborateurs et onboarding. | Compteurs et tableaux respectent ESM, DSM, Booster, admin et superadmin; aucun graphique ni export reporting au MVP. | L05,L07,L09 | XL |
| `MVP-L10-US004` | P1 | Administrateur | Exporter l’audit en CSV. | Seuls les administrateurs autorisés peuvent exporter; le périmètre est respecté; l’export est journalisé et limité. | US001 | M |
| `MVP-L10-US005` | P0 | Utilisateur | Reporter un bug depuis l’application. | Description, action, contexte technique non sensible, version et corrélation sont enregistrés; aucune saisie métier n’est jointe automatiquement. | L04 | L |
| `MVP-L10-US006` | P1 | Jonathan | Traiter les signalements utilisateurs. | États nouveau, en analyse, corrigé et rejeté; compteur back-office; commentaires et historique. | US005 | M |
| `MVP-L10-US007` | P1 | Administrateur | Suivre les alertes fonctionnelles importantes. | Ouverture, acquittement, commentaire, résolution et réouverture sont gérés; Jonathan est affecté par défaut en local. | L01,L11 | L |
| `MVP-L10-US008` | P0 | Responsable RGPD | Suivre une demande de droit. | Réception, vérification d’identité, export structuré, actions, délais et clôture sont tracés sans créer un faux consentement global. | L02,L05 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G10` avant l’ouverture du lot suivant.

---

# EPIC MVP-L11 — Médias, worker et tâches planifiées

**Porte de validation :** `G11`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L11-US001` | P0 | Développeur | Exécuter des jobs Dramatiq persistés. | Les files validées existent; PostgreSQL conserve état et tentatives; Redis n’est pas la source de vérité. | L01 | XL |
| `MVP-L11-US002` | P0 | Plateforme | Publier les effets externes via une outbox transactionnelle. | L’action métier et l’outbox sont atomiques; une reprise ne produit pas de doublon. | US001 | L |
| `MVP-L11-US003` | P0 | Plateforme | Envoyer les e-mails via une interface fournisseur. | Mailpit est exclusif en recette; les templates texte/HTML sont versionnés; les échecs sont rejouables et supervisés. | L03,US001 | L |
| `MVP-L11-US004` | P0 | Éditeur | Téléverser un média en quarantaine. | MIME réel, taille, extension, dimensions/durée, empreinte et nom serveur sont contrôlés; seul `ready` est servi. | L06,L08 | XL |
| `MVP-L11-US005` | P0 | Plateforme | Générer miniatures et variantes sans doublon. | La relance est idempotente; les variantes respectent les budgets; l’original reste protégé. | US004 | L |
| `MVP-L11-US006` | P0 | Exploitant | Planifier les tâches périodiques avec verrou. | Expiration, événements passés, anonymisation, purge, nettoyage et jobs bloqués s’exécutent une seule fois logiquement. | US001 | XL |
| `MVP-L11-US007` | P1 | Exploitant | Nettoyer les médias rejetés, temporaires et orphelins. | La politique de délai est appliquée; aucun média encore référencé n’est supprimé; chaque suppression sensible est auditable. | US004-US006 | M |
| `MVP-L11-US008` | P0 | Jonathan | Superviser files, workers et tâches par Uptime Kuma. | Healthchecks et heartbeats Push détectent absence, retard et échec; les seuils validés sont appliqués. | US001-US007 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G11` avant l’ouverture du lot suivant.

---

# EPIC MVP-L12 — Qualité transversale, sécurité, accessibilité et performance

**Porte de validation :** `G12`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L12-US001` | P0 | Équipe projet | Atteindre la couverture de tests obligatoire. | Couverture globale ≥80%; scénarios complets pour permissions, isolation, transactions et opérations sensibles. | L01-L11 | XL |
| `MVP-L12-US002` | P0 | Jonathan | Valider la sécurité applicative. | Secrets, dépendances, images, CSRF, cookies, rate limits, révocations, exports et multi-entités sont contrôlés sans défaut critique. | L03,L10,L11 | XL |
| `MVP-L12-US003` | P0 | Utilisateur en situation de handicap | Utiliser les parcours essentiels conformément à la cible AA. | Clavier, focus, contraste, zoom, lecteur d’écran, reduced-motion et axe sont validés; dérogation vidéo documentée. | L04-L10 | XL |
| `MVP-L12-US004` | P0 | Utilisateur mobile | Exécuter les parcours sur la matrice d’appareils. | Chrome/Safari Mac, Edge, Firefox, iOS, Android et largeurs 320 à 1920 sont couverts. | L04-L10 | L |
| `MVP-L12-US005` | P0 | Jonathan | Valider les performances et la charge. | 25 entités, 5 000 profils, 100 utilisateurs; P95 API/recherche conforme; taux d’erreur <1% hors erreurs voulues. | L02,L05,L11 | XL |
| `MVP-L12-US006` | P0 | Administrateur | Répéter l’import du vrai CSV en recette. | Le fichier versionné et hashé produit un rapport conforme; les rejets sont expliqués; les contrôles métier réussissent. | L09 | L |
| `MVP-L12-US007` | P0 | Exploitant | Tester sauvegarde, restauration et rollback. | PostgreSQL, MinIO et configuration sont restaurés isolément; le rollback respecte la compatibilité du schéma. | L01,L11 | XL |
| `MVP-L12-US008` | P0 | Validateurs | Clôturer la recette sans défaut bloquant. | Tess, Léa, Diane et Jonathan valident leurs périmètres; aucune anomalie critique/bloquante ou majeure centrale. | US001-US007 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G12` avant l’ouverture du lot suivant.

---

# EPIC MVP-L13 — Production temporaire locale

**Porte de validation :** `G13`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L13-US001` | P0 | Jonathan | Déployer une stack prod-local isolée. | Volumes, réseaux, secrets, bases et buckets diffèrent de dev/recette; HTTPS local et version sont visibles. | L12 | L |
| `MVP-L13-US002` | P0 | Jonathan | Déployer depuis un tag et des images GHCR immuables. | La CI construit; une approbation manuelle précède le déploiement; aucun `latest` seul n’est utilisé. | L01,US001 | L |
| `MVP-L13-US003` | P0 | Exploitant | Sauvegarder avant migration et quotidiennement. | Dump PostgreSQL, MinIO et configuration sont chiffrés; RPO 24 h; rétention 14/8/6 appliquée. | US001 | XL |
| `MVP-L13-US004` | P0 | Exploitant | Restaurer la production temporaire dans un environnement isolé. | Profils, événement, onboarding, média et compte de test sont vérifiés; le test est documenté. | US003 | L |
| `MVP-L13-US005` | P0 | Jonathan | Exécuter smoke tests et rollback de version. | Healthchecks, auth, lecture et écriture critique réussissent; la version précédente peut redémarrer si le schéma le permet. | US002-US004 | L |
| `MVP-L13-US006` | P1 | Jonathan | Superviser la prod-local depuis une machine distincte. | Uptime Kuma externe ou Beelink détecte les pannes; sauvegardes et tâches émettent des heartbeats. | US001-US005 | M |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G13` avant l’ouverture du lot suivant.

---

# EPIC MVP-L14 — Préparation et ouverture de la production générale

**Porte de validation :** `G14`  
**État initial :** `Planned`  
**Dépendance principale :** lot précédent validé et dépendances de la roadmap.

| ID | Priorité | Persona | User story / résultat attendu | Critères d’acceptation synthétiques | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `MVP-L14-US001` | P0 | Jonathan/eXalt | Provisionner l’hébergement permanent et les secrets. | Hôte disponible, sauvegardé et supervisé; séparation des environnements; accès d’administration sécurisé. | L13 | XL |
| `MVP-L14-US002` | P0 | Jonathan/DSI | Configurer domaine, DNS, HTTPS et e-mails réels. | Le certificat est valide; le fournisseur transactionnel délivre les magic links; aucun Mailpit ni contournement. | US001 | XL |
| `MVP-L14-US003` | P0 | Exploitant | Migrer la version et les données validées. | Migration ou restauration répétable; sauvegarde préalable; contrôles d’intégrité; version et schéma identifiés. | US001,US002 | XL |
| `MVP-L14-US004` | P0 | Administrateur | Importer le CSV final validé. | Empreinte attendue, critères qualité, rapport complet et validation Léa/Jonathan; aucun doublon ou incohérence critique. | L09,L12,US003 | L |
| `MVP-L14-US005` | P0 | Jonathan | Valider charge, sauvegarde et supervision sur l’hôte final. | 100 utilisateurs, RPO 24 h, restauration, alertes externes et disponibilité mesurable sont validés. | US001-US004 | XL |
| `MVP-L14-US006` | P0 | Léa/Jonathan | Autoriser l’ouverture immédiate à tous. | Produit et technique sont approuvés; toutes les dépendances bloquantes sont fermées; aucune anomalie interdite. | US001-US005 | M |
| `MVP-L14-US007` | P0 | Exploitant | Surveiller le lancement et déclencher un rollback si nécessaire. | Les critères validés sont automatisés/documentés; auth, isolation, intégrité et disponibilité sont surveillées renforcées. | US006 | L |

## Validation du lot

- toutes les stories `P0` ci-dessus sont `Done` ;
- les stories `P1` non terminées ont fait l’objet d’un arbitrage explicite ;
- les critères de sortie du lot dans la roadmap sont satisfaits ;
- la démonstration et les preuves sont présentées à Jonathan ;
- Jonathan valide explicitement la porte `G14` avant l’ouverture du lot suivant.

---

# 7. Backlog V1

La V1 reste à l’état `Planned` puis `Blocked` tant que le MVP n’est pas en production générale et qu’au moins un parcours d’arrivée réel n’a pas été exécuté. Les stories ci-dessous structurent le futur travail sans autoriser son démarrage anticipé.

## EPIC V1-01 — Événements récurrents

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L01-US001` | P0 | Créateur d’événement | Définir une règle de récurrence validée. | Fréquence, intervalle, fin et fuseau sont contrôlés; aperçu des occurrences. | MVP G14 | L |
| `V1-L01-US002` | P0 | Créateur d’événement | Modifier une occurrence, une série ou les suivantes. | Les trois portées sont explicites; aucune occurrence passée n’est modifiée silencieusement. | US001 | XL |
| `V1-L01-US003` | P0 | Plateforme | Générer les occurrences de façon idempotente. | Une relance ne crée aucun doublon; annulations et exceptions restent stables. | US001,US002 | L |

## EPIC V1-02 — Médiathèque avancée

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L02-US001` | P0 | Éditeur | Rechercher et réutiliser un média existant. | Filtres entité, type, statut et usage; droits respectés; aucune copie inutile. | MVP G14 | L |
| `V1-L02-US002` | P0 | Éditeur | Remplacer ou archiver un média en connaissant ses usages. | Les contenus impactés sont listés; aucune référence active n’est cassée. | US001 | L |
| `V1-L02-US003` | P1 | Administrateur | Configurer des quotas si la mesure le justifie. | Alerte avant blocage; quotas globaux ou par type; aucune rétroactivité destructive. | US001 | M |

## EPIC V1-03 — Import avancé et rollback complet

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L03-US001` | P0 | Administrateur | Prévisualiser le rollback d’un lot d’import. | Toutes les modifications et conflits postérieurs sont identifiés avant action. | MVP G14 | XL |
| `V1-L03-US002` | P0 | Administrateur | Exécuter un rollback avec motif obligatoire. | Les opérations compatibles sont transactionnelles; aucune modification métier postérieure n’est supprimée sans décision. | US001 | XL |
| `V1-L03-US003` | P0 | Auditeur | Vérifier le résultat et l’historique du rollback. | Contrôles d’intégrité, rapport et audit complet sont disponibles. | US002 | L |

## EPIC V1-04 — Reporting visuel et exports

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L04-US001` | P0 | Responsable autorisé | Consulter des graphiques accessibles et filtrables. | Le périmètre correspond aux tableaux MVP; une alternative textuelle existe; couleurs non exclusives. | MVP G14 | L |
| `V1-L04-US002` | P0 | Responsable autorisé | Demander un export CSV ou PDF asynchrone. | Le worker génère le fichier; permissions revalidées; expiration et téléchargement sécurisé. | US001 | XL |
| `V1-L04-US003` | P0 | Jonathan | Surveiller et auditer les exports. | Débit limité; alertes anormales; contenu, demandeur et périmètre journalisés sans données excessives. | US002 | M |

## EPIC V1-05 — Fiches d’arrivée multicanales

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L05-US001` | P0 | Éditeur | Prévisualiser et générer une fiche 16:9. | La charte, les zones sûres et l’autorisation photo sont respectées. | MVP G14 | L |
| `V1-L05-US002` | P0 | Éditeur | Générer un texte prêt à copier dans Teams. | Le texte correspond à la fiche publiée et reste modifiable avant copie. | US001 | M |
| `V1-L05-US003` | P1 | Administrateur | Historiser les exports multicanaux. | Version source, auteur, date et canal sont conservés. | US001,US002 | S |

## EPIC V1-06 — Compléments éditoriaux et vidéos

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V1-L06-US001` | P0 | Équipe contenu | Ajouter les vidéos métier manquantes. | Chaque vidéo possède propriétaire, durée, texte alternatif contextuel et statut de validation. | MVP G14 | M |
| `V1-L06-US002` | P1 | Éditeur | Joindre et activer des fichiers de sous-titres facultatifs. | Formats acceptés validés; activation utilisateur; aucune lecture automatique. | US001 | M |
| `V1-L06-US003` | P1 | Référent accessibilité | Suivre les écarts vidéo restants. | Chaque écart possède justification, portée et plan éventuel de correction. | US001,US002 | S |

# 8. Backlog V2 conditionnel

La V2 reste `Blocked` jusqu’à validation de la DSI, des accès Microsoft, des scopes, des responsabilités et des sources de vérité. La présence de ces stories ne constitue pas un engagement de réalisation.

## EPIC V2-01 — Microsoft Entra ID

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L01-US001` | P0 | Employé | Se connecter par SSO Entra ID. | Identité immuable associée à `person`; comptes désactivés refusés; audit complet. | Autorisation DSI | XL |
| `V2-L01-US002` | P0 | Administrateur | Conserver un accès de secours contrôlé. | Le mécanisme est limité, surveillé et documenté; il ne contourne pas les politiques DSI. | US001 | L |
| `V2-L01-US003` | P0 | Jonathan/DSI | Migrer progressivement depuis les magic links. | Coexistence temporaire, métriques, rollback et date de retrait sont définis. | US001,US002 | L |

## EPIC V2-02 — Microsoft Graph et synchronisation

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L02-US001` | P0 | Administrateur | Prévisualiser les changements Graph avant application. | Créations, modifications, départs et conflits sont listés; aucune suppression automatique incontrôlée. | V2-01 | XL |
| `V2-L02-US002` | P0 | Plateforme | Rapprocher les personnes par identifiant immuable. | Aucun rapprochement uniquement par nom; les conflits exigent une décision humaine. | US001 | L |
| `V2-L02-US003` | P0 | Administrateur | Définir la source de vérité par champ. | Graph n’écrase que les champs explicitement gouvernés; les données métier locales restent protégées. | US001,US002 | L |

## EPIC V2-03 — Intégration Teams

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L03-US001` | P0 | Éditeur | Prévisualiser puis publier une fiche dans un canal Teams. | Canal, contenu et photo sont confirmés; les scopes sont minimaux. | V2-01 | XL |
| `V2-L03-US002` | P0 | Plateforme | Rendre la publication Teams idempotente. | Une relance ne crée pas de doublon; erreurs et destination sont auditées. | US001 | L |
| `V2-L03-US003` | P1 | Administrateur | Gérer l’identité technique Teams. | Secret, expiration, scopes et révocation sont supervisés. | US001 | M |

## EPIC V2-04 — Automatisation des arrivées et départs

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L04-US001` | P0 | Plateforme | Préparer automatiquement fiche et onboarding à l’arrivée. | Date et données sources déclenchent une proposition contrôlée; les cas ambigus sont bloqués. | V2-02 | XL |
| `V2-L04-US002` | P0 | Plateforme | Révoquer et archiver automatiquement au départ. | Sessions immédiatement révoquées; visibilité retirée; conservation trois mois puis anonymisation selon règles. | US001 | L |
| `V2-L04-US003` | P0 | Administrateur | Traiter les conflits d’automatisation. | Une file de validation explique le conflit et permet décision/audit sans perte. | US001,US002 | M |

## EPIC V2-05 — Intégrations Hub et eXalt Academy

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L05-US001` | P1 | Employé | Accéder à des ressources contextualisées. | Les liens ou ressources proviennent d’une API officielle et respectent les droits. | API disponibles | L |
| `V2-L05-US002` | P1 | Employé | Consulter une progression externe autorisée. | Seules les données validées sont synchronisées; source et fraîcheur sont visibles. | US001 | XL |
| `V2-L05-US003` | P0 | Jonathan/DSI | Auditer les échanges avec les plateformes externes. | Scopes, erreurs, corrélation et conservation sont définis. | US001,US002 | M |

## EPIC V2-06 — Renforcement de l’authentification

| ID | Priorité | Persona | Résultat attendu | Critères d’acceptation | Dépendances | Taille |
|---|---|---|---|---|---|---|
| `V2-L06-US001` | P0 | Administrateur | Utiliser MFA ou politiques conditionnelles. | Les politiques DSI s’appliquent; récupération et secours sont documentés. | V2-01 | L |
| `V2-L06-US002` | P0 | Administrateur | Se réauthentifier avant une action sensible. | La liste des actions et durée d’élévation sont configurées; abandon sans effet. | US001 | L |
| `V2-L06-US003` | P1 | Super-administrateur | Obtenir une élévation temporaire de privilège. | Durée courte, motif, approbation éventuelle et audit renforcé. | US001,US002 | L |

# 9. Règles de gestion des anomalies et de la dette

- une anomalie bloquante ou critique interrompt la préparation de la porte ;
- une anomalie de sécurité, de données ou d’isolation devient prioritaire sur toute story fonctionnelle ;
- une anomalie majeure sur un parcours central doit être corrigée dans le lot ;
- une anomalie mineure peut être reportée uniquement selon les règles de recette validées ;
- une dette technique créée volontairement doit être enregistrée avec cause, impact, propriétaire et lot de résolution ;
- aucune dette ne peut contourner migration, tests, permissions, sauvegarde ou audit.

# 10. Préparation opérationnelle de chaque lot

Avant le démarrage d’un lot, l’agent chef de projet devra produire une fiche de lot contenant :

1. les stories sélectionnées ;
2. leur ordre interne ;
3. les sous-tâches techniques ;
4. les fichiers et modules probablement affectés ;
5. les migrations prévues ;
6. les tests à écrire avant ou avec l’implémentation ;
7. la démonstration attendue ;
8. les risques propres au lot ;
9. les décisions encore nécessaires ;
10. la checklist de validation de Jonathan.

# 11. Traçabilité GitHub recommandée

- un epic GitHub par lot ;
- une issue par user story ;
- sous-issues ou checklist pour les tâches techniques ;
- labels de version : `mvp`, `v1`, `v2` ;
- labels de priorité : `p0`, `p1`, `p2` ;
- labels de domaine : `frontend`, `backend`, `data`, `infra`, `security`, `a11y`, `content` ;
- milestone correspondant à la porte de validation ;
- lien obligatoire vers la décision ou le document source ;
- PR liée à l’issue et preuve de test dans la description.

# 12. Critères globaux empêchant la clôture d’une porte

Une porte ne peut pas être validée si :

- une story P0 du lot n’est pas terminée ;
- une permission critique n’est pas testée ;
- une migration ne fonctionne pas sur une base propre ;
- un secret ou une donnée réelle a été versionné ;
- une anomalie bloquante ou critique reste ouverte ;
- un comportement mobile ou clavier essentiel est inutilisable ;
- la démonstration ne correspond pas aux critères de la roadmap ;
- la documentation minimale de reprise ou d’exploitation manque ;
- Jonathan n’a pas donné sa validation explicite.

# 13. Arbitrages validés par Jonathan

## ARB-BACK-001 — Priorités

**Décision validée :** retenir `P0`, `P1` et `P2`, avec interdiction de franchir une porte tant qu’une story `P0` reste ouverte.

## ARB-BACK-002 — Tailles

**Décision validée :** utiliser les tailles relatives `S`, `M`, `L` et `XL`, sans convertir ces tailles en délais. Toute story `XL` doit être découpée avant réalisation.

## ARB-BACK-003 — Ouverture des lots

**Décision validée :** seul le lot explicitement ouvert par Jonathan peut passer à `Ready` ou `In progress`. Les lots suivants restent `Planned`, même si un agent pourrait techniquement les commencer.

## ARB-BACK-004 — V1 et V2

**Décision validée :** conserver les stories V1 et V2 dans le backlog pour la traçabilité, mais les laisser `Blocked` jusqu’aux conditions de la roadmap, sans développement anticipé.

## ARB-BACK-005 — Défauts prioritaires

**Décision validée :** tout défaut critique de sécurité, de données, d’isolation ou d’accessibilité essentielle devient immédiatement prioritaire sur les fonctionnalités du lot en cours.

# 14. Décisions validées

| ID | Décision validée |
|---|---|
| BACKLOG-001 | Le backlog est structuré par les 15 lots MVP validés. |
| BACKLOG-002 | Les priorités P0, P1 et P2 gouvernent l’ordre de réalisation. |
| BACKLOG-003 | Une story P0 ouverte empêche la validation de sa porte. |
| BACKLOG-004 | Les tailles relatives ne constituent pas des estimations de délai. |
| BACKLOG-005 | Toute story XL est découpée avant implémentation. |
| BACKLOG-006 | Seul le lot ouvert par Jonathan peut être réalisé. |
| BACKLOG-007 | Les stories V1 et V2 ne sont pas développées avant leurs conditions d’entrée. |
| BACKLOG-008 | Les défauts critiques préemptent les fonctions prévues. |
| BACKLOG-009 | Une story n’est Done qu’avec tests, documentation et démonstration. |
| BACKLOG-010 | GitHub conserve la traçabilité entre story, décision, PR, tests et porte. |

# 15. Statut du livrable

Les cinq arbitrages `ARB-BACK-001` à `ARB-BACK-005` ont été validés par Jonathan le 25 juillet 2026. Ce backlog constitue désormais la référence de découpage des lots, des epics et des user stories.

Il sert d’entrée obligatoire au cahier des charges consolidé et à la préparation du premier agent IA de réalisation. Toute modification de priorité, de lot ou de porte de validation devra être explicitement tracée et approuvée.
