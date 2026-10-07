# Checklist de validation — porte `G8`

**Lot :** LOT 8 — Événements et accueil dynamique
**Préparée le :** 7 octobre 2026, à la sortie de `T14`
**Destinataire :** Jonathan — il coordonne la validation technique et l'exploitation
**Décision de franchissement :** `DEC-634`, validée le 7 octobre 2026

---

**Comment lire ce document.** Les chiffres sont accompagnés de la commande qui les produit. Les
contrôles techniques sont exécutés ; la validation nominative du corpus reste un geste humain, et
n'est donc jamais présentée comme accomplie par la CI.

## 1. Les six critères de sortie — fiche LOT 8 §1.2

| # | Critère | État | Preuve ou geste restant |
|---|---|---|---|
| 1 | Aucune donnée de participants n'existe | **Tenu** | `T1` : aucune table/colonne de récurrence, participant, inscription, présence ou notification métier. Étendu au corps de requête par `T3` et à la réponse/manifeste par `T9`/`T10` — un témoin balaie les cinq tables et le contrat à chaque niveau |
| 2 | Aucune vidéo complète n'est téléchargée avant interaction | **SANS OBJET** | `US005` (vidéo d'accueil) est explicitement **reportée** (`T12`, `DEC-631`) : aucune fixture, route ni composant du dépôt n'exerce un bloc `VIDEO`. Un critère négatif satisfait par l'absence de la fonctionnalité ne prouve rien (§7.39 de la passation) — voir le compte rendu de `T14` §3.2 |
| 3 | Les événements passés sont calculés de manière cohérente | **Tenu** | `T2` : `ends_at <= instant` avec la même ancre des deux côtés ; `T13` le reprouve sur l'horloge réelle du conteneur, à travers Caddy/HTTPS |
| 4 | Les règles d'archivage et de restauration sont respectées | **Tenu** | `T5` : grilles distinctes (DSM « Périmètre » pour Annuler/Archiver, jamais « créé OU rattaché ») ; `ARB-DROIT-003` exclut DSM/BOOST en bloc de la restauration. `T13` le reprouve sur DEUX évènements, sur la pile réelle |
| 5 | L'accueil respecte l'ordre et le design validés | **Tenu** | `T11` (desktop, cinq sections dans l'ordre du cahier §8.4) et `T12` (mobile, carrousels accessibles) ; `T13` prouve la composition sur la pile réelle |
| 6 | Jonathan valide l'accueil et les événements | **Tenu** | Validation explicite de Jonathan transmise le 07/10/2026 : « Je valide la checklist G8 » |

**Sur le critère 2 :** le marquer « Tenu » masquerait que rien ne l'exerce réellement. Le marquer
« Non tenu » laisserait croire à un défaut alors qu'il s'agit d'un report délibéré, validé par toi
le 06/10/2026 avant tout code. « Sans objet » est la formulation qui dit le vrai : ce critère sera
réellement exerçable le jour où `QO-121` tranchera un vocabulaire de `payload_json` pour un bloc
`VIDEO`, hors périmètre de ce lot.

## 2. Contrôles exécutés

| Contrôle | Résultat relevé le 07/10/2026 |
|---|---|
| `make recette-check` | 57 contrôles, 0 échec ; 7/7 séparations effectives |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé répondent, révision `3f5e542` |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec ; artefact bâti servi par Caddy en HTTPS |
| `make accueil-check ENVIRONNEMENT=recette` | 29 contrôles, 0 échec — grille à deux visages du DSM, asymétrie entre deux Boosters, `ARB-DROIT-003` dans le sens du refus (×2), classement temporel réel, fenêtre réelle des arrivées récentes |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec (témoin transversal du LOT 7, rejoué sur la même recette) |
| `make recette-modele-check` | 25 contrôles classés : 16 acquis, 2 partiel, 7 reportés, 0 inapplicable — inchangé depuis `G7` |
| `pytest` depuis la racine | 1 564 collectés ; 74 échecs environnementaux identiques à ceux mesurés avant `T13`, dus au jeu de démonstration de développement |
| `make test-frontend` | 794 Vitest (380 `contracts`, 120 `ui`, 294 `web`), inchangé |
| `make check` (qualité) | Ruff, Prettier, ESLint, `mypy` (197 fichiers), `tsc --noEmit` : tous verts |
| `make audit` | zéro avis, deux analyseurs |

Les 74 échecs viennent du jeu de démonstration de développement (33 entités, 5 169 personnes). La
comparaison porte sur la **liste** des identifiants de test en échec, pas seulement leur nombre :
elle est identique à celle mesurée avant `T13`, et aucune ligne Python applicative n'a changé
entre les deux mesures.

## 3. Démonstration guidée à Jonathan

1. Lire la fiche LOT 8 §1.2 et les six critères de sortie ci-dessus.
2. Ouvrir `PageEntite.tsx` (l'accueil d'une entité) : présentation, Framework, arrivées récentes,
   événements à venir, liens internes, dans cet ordre — desktop et mobile (carrousels sous
   768 px).
3. Ouvrir l'écran de consultation des événements (deux onglets, à venir/passés) et l'écran de
   gestion (créer/modifier/publier/annuler/archiver/restaurer/médias).
4. Vérifier la grille à deux visages du DSM : un évènement qu'il a seulement créé se modifie mais
   ne se publie pas ; un évènement où il est nommé (portée « consultants ») se publie, s'annule,
   s'archive.
5. Vérifier qu'un évènement annulé reste visible avec son badge, et qu'un évènement archivé
   disparaît de la consultation.
6. Vérifier qu'une fiche d'arrivée publiée par anticipation apparaît immédiatement dans les
   arrivées récentes de l'accueil, avant la date d'arrivée réelle.
7. Confirmer que `US005` (vidéo) reste reportée à ta satisfaction, et que rien n'a été inventé à
   sa place.
8. Consigner ton accord (ou tes réserves) sur les critères 1 à 5, et valider le critère 6.

## 4. La recette réellement exécutée

La recette a été épinglée sur les images publiées de la révision `3f5e542` (fusion de `T13`),
puis son seul volume PostgreSQL a été supprimé et recréé — même discipline qu'à `G7` : prouver
que la chaîne complète de migrations (jusqu'à la tête `0023`) s'applique proprement sur une base
vide, pas seulement qu'elle continue de fonctionner sur une base déjà peuplée.

Un premier démarrage a rencontré le port `8080` déjà déclaré par le projet tiers
`observatoire-ecom-studio`, même conflit que `T15` du LOT 7 sur la même machine. Son seul
conteneur `web` a été arrêté temporairement puis relancé après la recette. Caddy, créé pendant ce
conflit sans ses publications réelles, a été recréé par `make caddy-recreate
ENVIRONNEMENT=recette` ; les sept ports effectifs ont ensuite été mesurés conformes.

`make accueil-check` et `make onboarding-check` ont ensuite été rejoués sur la recette, à travers
Caddy en HTTPS, sur les conteneurs tournant nativement en `aarch64` sur l'image **publiée** —
jamais une reconstruction locale, vérifié par empreinte.

## 5. Contrôles du modèle §30

`make recette-modele-check` relit directement les 25 contrôles du §30 du modèle immuable. Aucun
des 25 ne porte sur les tables événementielles ou sur l'accueil — vérifié en relisant chacun des
25 libellés avant de conclure, pas supposé par habitude du geste de `T15` du LOT 7. Le résultat
reste **16 acquis, 2 partiel, 7 reportés, 0 inapplicable**, identique à celui validé à `G7`. Les
sept reports relèvent des LOTS 9 à 12, hors périmètre de ce lot.

## 6. Réserves et écarts ouverts

- `ECART-012` reste à décider par Léa et ne bloque pas la porte technique.
- `ECART-068` reste ouvert : l'audit de modification/publication/annulation/archivage appartient
  au domaine `audit_event` du LOT 10. `US004` reste donc ouverte au registre des issues au-delà de
  la porte technique, comme documenté depuis `T5`.
- `QO-121` reste ouverte ; elle rend le critère de sortie 2 **sans objet** plutôt que tenu.
- `ROAD-RSK-033` et `ROAD-RSK-034` restent à réévaluer avant le LOT 13, inchangés par ce lot.

## 7. Décision de Jonathan

**Ce que tu valides :** les six critères du LOT 8, en distinguant les cinq preuves techniques
(dont une marquée sans objet, §1) de ta propre confirmation requise par le sixième.

**Ce que la porte clôt :** le LOT 8 ; elle n'ouvre aucun autre lot sans instruction explicite.

| | |
|---|---|
| Date | 7 octobre 2026 |
| Décision | ☒ franchie ☐ à reprendre — `DEC-634` |
| Validation de Jonathan | « Je valide la checklist G8, tu peux franchir la porte, nous reviendrons sur les éléments mis de côté sur les prochains lots au besoin » |
| Réserves | `ECART-012`, `ECART-068`, `QO-121` restent ouvertes, non bloquantes pour `G8` — à reprendre aux lots suivants au besoin |
