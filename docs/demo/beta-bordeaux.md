# Beta eXalt Bordeaux

**État :** prête pour recette de démonstration au 4 novembre 2026
**Décision :** `DEC-685`
**Branche :** `codex/beta-bordeaux`

Cette édition de démonstration conserve l'architecture multi-entité, mais ne
provisionne et n'expose qu'une entité active : `BORDEAUX` (`eXalt Bordeaux`).
Le sélecteur d'entité, le portail national, l'import CSV et les exports ne font
pas partie du parcours de la Beta. Leur code n'est pas supprimé : il est laissé
en sommeil pour une reprise ultérieure du produit multi-entité.

## Périmètre fonctionnel

- un accueil Bordeaux inspiré du prototype, avec direction, repères, parcours
  d'onboarding et temps forts ;
- un Framework présentant les DSM, ESM, TAS, DG, cercles et bureaux ;
- un trombinoscope avec recherche, filtre par cercle, défilement continu,
  huit cartes par ligne sur grand écran et retournement au survol ;
- une fiche collaborateur sans métier, client, statut de carte ni historique
  organisationnel dans le parcours de démonstration ;
- un parcours d'onboarding Bordeaux avec fiche d'arrivée modifiable, date
  d'arrivée facultative et checklist Intercontrat ;
- une gestion des événements avec image, publication automatique et diffusion
  sur la page Événements, l'accueil, l'agenda, la liste des prochains rendez-vous
  et le bandeau déroulant.

## Données installées

- 124 personnes issues de `extract exalt bdx 301026.xlsx` ;
- 7 cercles : Produit, Projet, Design, IT, Forge, Shield et Data ; les lignes
  `CHANGE` de la source sont rattachées à Projet ;
- 3 bureaux : BDG, BDS et BDE ;
- 6 DSM, 3 DG, 2 TAS, 2 ESM, 7 boosters et 5 attributions de responsable de
  bureau ;
- les photos JPEG, PNG et WebP fournies, avec conversion locale des RAW Sony
  `.ARW` lorsque `sips` est disponible ;
- un placeholder pour tout profil sans photo exploitable ;
- un modèle Intercontrat Bordeaux inspiré du prototype : 28 tâches réparties
  entre avant l'arrivée, J1, J2, J3, J5 et le premier mois ;
- une fiche d'arrivée et une instance de ce parcours affectées au profil de
  démonstration `jonathan.dupau@exalt-company.com`, ancrées au jour de la
  première exécution.

Le métier et le client ne sont pas renseignés. Leur modèle n'est pas supprimé :
ils restent disponibles pour une reprise ultérieure du produit multi-entité.
La date d'arrivée peut rester inconnue ; l'application conserve alors une date
technique d'appartenance distincte pour garantir la cohérence de l'historique.

Les trois DG restent distincts des six DSM dans cette édition. La catégorie
technique `dg` du modèle historique implique automatiquement une responsabilité
DSM ; elle n'est donc pas utilisée par le provisionnement Bordeaux, afin de ne
pas transformer artificiellement les trois DG en trois DSM supplémentaires.

## Règles d'interface propres à la Beta

- le logo eXalt du bandeau renvoie à l'accueil Bordeaux ;
- aucune action de changement d'entité n'est proposée ;
- les responsables de cercle et de bureau utilisent leur photographie quand
  elle est disponible, sinon le placeholder commun ;
- `BDG` signifie « Bureau du Gaming », `BDS` « Bureau des sports » et `BDE`
  « Bureau des eXaltées » ;
- Romain Hoarau et Charles Vallais sont tous deux responsables du BDG ;
- un événement créé depuis l'écran de gestion suit le flux
  `création → image éventuelle → publication`. Il n'est donc plus laissé en
  brouillon et devient immédiatement éligible aux lectures publiques ;
- le motif d'audit est demandé lorsque l'action est autorisée par le rôle
  `SUPER`, puis transmis à la création, au média et à la publication.

## Provisionnement

Après le démarrage de la pile et l'application des migrations :

```sh
.venv/bin/python infra/scripts/provisionner-bordeaux.py \
  --classeur "/chemin/vers/extract exalt bdx 301026.xlsx" \
  --photos "/chemin/vers/Photos"
```

La commande est rejouable. Elle met à jour les référentiels et les personnes,
ne duplique aucune responsabilité et ne remplace pas une photo déjà prête.
Les sources Excel et photo restent hors du dépôt Git.

Après une modification du code de la Beta, reconstruire les services :

```sh
make code-refresh ENVIRONNEMENT=dev
```

## Contrôle rapide

Le résultat attendu est :

```text
Bordeaux provisionne : 124 personnes, 7 cercles, 3 bureaux, … photos,
28 taches d'onboarding, 1 parcours affecte(s).
```

Vérifier ensuite dans l'application :

1. le trombinoscope, ses filtres, le défilement et les placeholders ;
2. les sept cercles, leur liste dépliable et les photos des responsables ;
3. les équipes DSM, Framework, DG, TAS, ESM et les trois bureaux ;
4. la création d'un événement avec ou sans image et son passage immédiat à
   l'état `Publié` ;
5. son apparition sur la page Événements, le bandeau, l'agenda et les prochains
   rendez-vous de l'accueil ;
6. la rubrique « Mon onboarding », sa fiche modifiable, ses 28 tâches et leur
   validation.

## Contrôles techniques exécutés

La clôture du chantier vérifie :

- les tests frontend et contrats ;
- le typage TypeScript et le build de production ;
- les tests API ciblés sur les collaborateurs, le Framework, l'onboarding et
  les événements ;
- la migration `0030_date_arrivee_facultative` ;
- la reconstruction locale des images et l'état sain des services `web`,
  `api` et `worker`.
