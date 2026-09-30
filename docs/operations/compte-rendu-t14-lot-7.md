# Compte rendu — `T14` du LOT 7 : les écrans d'administration

**Sous-étape :** `T14` — Écrans d'administration (catalogue, modèles, suivi par périmètre)
**Décision :** `DEC-614`
**Date :** 29 septembre 2026
**Branche :** `feature/lot7-t14-ecrans-administration`, depuis `develop` à jour (`2b15653`, tête après
fusion de `T13`, PR [#198](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/pull/198))

---

# 1. État du lot

LOT 7 ouvert le 25/09/2026 (`DEC-598`), quinze sous-étapes. `T1` à `T13` déjà fusionnées. `T14`
livre les **trois** écrans que le découpage nomme — catalogue, modèles, suivi par périmètre — sous
la rubrique `administration` réservée depuis `T4` du LOT 4 (`RUBRIQUES`, `routes.ts`), avec la même
discipline qu'à `T13` : **une seule page** compose les trois, `PageAdministration.tsx`.

`T15` — recette, §30, checklist `G7` — reste la dernière sous-étape du lot après `T14`.

---

# 2. Ce que la sous-étape a produit

## 2.1 Une seule page, jamais trois écrans distincts

Même raisonnement qu'à `T13` : `RUBRIQUES` ne réserve qu'**un** chemin, `administration`. La page
compose donc trois sections — `SectionCatalogue`, `SectionModeles` (chaque modèle rendu par
`CarteDeModele`, chaque version par `CarteDeVersion`), `SectionSuivi` — plutôt que d'inventer des
chemins que le corpus ne nomme pas.

## 2.2 Décision de Jonathan : le menu s'élargit à DSM/BOOST, un seul chemin d'accès

**Trouvé en préparant le travail, avant d'écrire une ligne de code.** La rubrique « Administration »
n'affichait son entrée qu'aux rôles `ESM`/`ADM-E`/`SUPER` (`ROLES_ADMINISTRATION`, câblé au LOT 4
`T9`, dérivé du §20 de la matrice — qui ne parle QUE de l'attribution des rôles). Or le §9 donne à
un `DSM` et à un `BOOSTER` de VRAIS droits de gestion sur le catalogue et les modèles d'onboarding,
dans leur propre périmètre. Sans élargissement, ces deux rôles n'auraient jamais vu l'entrée de
menu pour exercer un droit qu'ils détiennent réellement côté API.

**Question posée explicitement à Jonathan, trois options :** élargir le menu (un seul chemin
d'accès) ; ouvrir un second point d'entrée (deux chemins vers le même écran) ; reporter DSM/Booster
à un lot futur (un écart documenté). **Retenu : élargir le menu.**

Une nouvelle liste de rôles, `rolesAdministrationOnboarding` (`DSM`, `ESM`, `BOOST`, `ADM-E`,
`SUPER`), est posée **séparément** de `rolesAdministration` — jamais fusionnée, même discipline que
`rolesCycleDeVie`/`rolesRestaurationDUnContenu` (LOT 5/6, §7.27) : les deux gardent la MÊME
rubrique pour DEUX raisons indépendantes, et les fusionner ferait suivre l'une quand l'autre change,
en silence. `droitsDeNavigation` (`routes.ts`) en prend l'UNION avec `ROLES_ADMINISTRATION`.

**Le suivi par périmètre (`T12`) n'entre PAS dans ce calcul** : sa grille ne refuse jamais personne
(dégrade jusqu'à `Soi`), et l'inclure aurait rendu la rubrique visible à tout le monde — ce qui
aurait vidé le refus par défaut du §20.1 de son sens pour cette rubrique précisément.

## 2.3 Route API nouvelle, trouvée en construisant l'écran — `GET …/onboarding/templates`

**Second point trouvé en inventoriant l'API, avant d'écrire l'écran :** ni `T5` ni `T6` n'avaient
posé de route pour LISTER les modèles ou leurs versions — seulement les créer et faire évoluer leur
cycle de vie. Sans lecture, « gérer les modèles » ne pouvait agir que sur ce qui vient d'être créé
DANS LA MÊME SESSION, jamais revenir sur un modèle existant à une session ultérieure — un écran
d'administration qui ne survivrait pas à un rechargement de page ne serait pas un écran
d'administration.

`GET /entities/{code}/onboarding/templates` (`app/onboarding/gabarits.py` : `lister_les_modeles`,
`lister_les_versions` ; `routes.py` : `lister_les_modeles_onboarding`) rend les modèles ATTEIGNABLES
par l'appelant dans son propre périmètre — même grille que la création (`peut_gerer_un_modele_de_
cette_portee`, appliquée en Python sur la liste brute, jamais une seconde règle en SQL, §7.27) —
chacun avec ses versions imbriquées, en un seul appel. Même précédent que l'extension de
`/permissions` à `T13` : consommer, sauf quand consommer révèle un manque, auquel cas on le comble
et on le dit.

**Le droit de lecture d'`OFFICE`, « Consulter les modèles publiés » (§9, grille plus large), reste
SANS route.** Aucun critère actuel du backlog ne le réclame — `T14` ne l'invente pas.

## 2.4 La restauration reste refusée à DSM/BOOST, même sur leur propre modèle — `ECART-066`

Le §9 exclut `DSM` et `BOOSTER` **en bloc** de la seule ligne « Restaurer une version » — jamais un
sous-cas de leur propre modèle, à la différence des cinq autres gestes de la même grille. Une
troisième liste de rôles, `rolesRestaurationDesModelesOnboarding` (`ESM`, `ADM-E`, `SUPER`), gate
donc spécifiquement le bouton « Restaurer » — sans elle, un DSM aurait vu un bouton que l'API
refuse systématiquement (403), l'avertissement faux du §7.21.

## 2.5 Le frontend ne propose pas un droit déjà refusé, et n'invente aucune scope supplémentaire

- Le catalogue et les modèles ne lancent **aucun appel réseau** si les rôles de l'appelant n'ouvrent
  ni `ROLES_ADMINISTRATION` ni `ROLES_ADMINISTRATION_ONBOARDING` — même discipline que
  `PanneauDuCycleDeVie` (LOT 5, `T11`) : rien n'est rendu plutôt qu'un bouton grisé.
- Le suivi, lui, est chargé et affiché **inconditionnellement** — aucun rôle n'y est jamais refusé.
- Les formulaires de création (tâche de référence, modèle) ne proposent que la portée `ENTITE`/
  `ENTITY` : les portées `DSM`/`CIRCLE`/`GLOBAL` existent côté API (§9) mais aucun critère de `T14`
  ne réclame un sélecteur de portée à l'écran — laissé pour un lot ultérieur si le besoin se
  confirme, plutôt qu'inventé maintenant.

---

# 3. Contrôles exécutés

- `ruff check`, `ruff format --check`, `mypy` (backend, strict) : 0 erreur.
- `pnpm run lint` (ESLint, tout le monorepo), `pnpm run format:check` (Prettier) : 0 erreur.
- `pnpm --filter web run typecheck`, `pnpm --filter @onboarding/contracts run typecheck` : 0 erreur.
- `make docs-check`, `make sources-check`, `make parametres-check`, `make cadre-check`,
  `make ecrans-check` (47 modules d'écran servis en JavaScript, dont `PageAdministration.tsx` —
  couvert SANS aucune modification du contrôle, glob générique sur `apps/web/src/pages/*.tsx`) :
  verts.
- Backend : 8 nouveaux tests (`test_modeles_onboarding.py` : 6 tests de la nouvelle liste, dont le
  témoin d'asymétrie DSM/ESM ; 2 tests de confrontation manifeste ↔ service pour les deux nouvelles
  listes de rôles), `test_contrat.py` (cohérence manifeste ↔ routes servies, dans les deux sens) :
  tous verts.
- Frontend : 336 tests `@onboarding/contracts` (+28 : `modelesOnboarding.test.ts`,
  `suiviOnboarding.test.ts`), 111 `@onboarding/ui` (inchangé), 259 `web` (+12 : `PageAdministration.
  test.tsx`, 1 test réécrit dans `AffichageConditionnel.test.tsx` — devenu obsolète par la décision
  du §2.2).

## 3.1 Zéro régression

Comparaison nommée sur la même base (`git worktree` sur `origin/develop`, `2b15653`, tête après
fusion de `T13`), `pytest` bare (sans filtre `-m integration`, comme `make check`) lancé **depuis la
racine des deux côtés** :

```text
origin/develop (baseline)         75 échecs, 1331 passés  →  1406 tests
feature/lot7-t14 (branche)        75 échecs, 1339 passés  →  1414 tests
```

Les deux listes de 75 échecs, triées et comparées par `diff`, sont **identiques** — tous
environnementaux (le jeu de démo de la base de dev), sans rapport avec `T14`. `-m integration` :
1 027 → 1 033 (+6, les tests de la nouvelle route de liste).

## 3.2 Aller-retour réel effectué avant de déclarer l'écran terminé (§7.43 du LOT 6)

**Un décor réel, une session ESM réelle par lien magique, un navigateur réel.** Décor posé par
`psql` (une personne, une appartenance active dans `BORDEA00`, une responsabilité `ESM`), lien
magique réel consommé dans le navigateur (Mailpit), puis dans l'ordre, sur la page
`/entites/BORDEA00/administration` :

| Geste | Requête réelle | Résultat |
|---|---|---|
| Chargement de la page | `GET .../onboarding/templates`, `GET .../task-references`, `GET .../onboarding-suivi/taches-en-retard?page=1&taille=25` | `200` × 3 |
| Création d'une tâche de référence | `POST .../task-references` | `201` |
| Création d'un modèle | `POST .../onboarding/templates` | `201` |
| Création d'une version | `POST .../templates/{id}/versions` | `201` |
| Composition des tâches | `PUT .../versions/{id}/tasks` | `200`, `due_offset_days: 5` confirmé dans le corps envoyé |
| Publication | `POST .../versions/{id}/publication` | `200`, bouton « Archiver » apparu à la place de « Publier » |
| Archivage | `POST .../versions/{id}/archivage` | `200`, bouton « Restaurer » apparu (rôle ESM) |
| Restauration | `POST .../versions/{id}/restauration` | `200` |

Tous les appels réels à `200`/`201`, journal réseau à l'appui. Le décor a été **entièrement
nettoyé** après la vérification (personne, appartenance, responsabilité, tâche de référence,
modèle, version, tâche composée, sessions et traces d'audit associées) — confirmé par requête de
comptage à zéro.

## 3.3 Le script de pile différé par `T13` est construit, combiné pour les deux sous-étapes

**Décision de Jonathan à `T13` : reporter `make onboarding-check` à `T14`.** Construit ici,
`infra/scripts/verifier-administration-onboarding.py` (14 contrôles), sur la pile RÉELLE — Caddy,
HTTPS, conteneurs en marche — ce que `TestClient` ne peut pas prouver (§7.28) :

- **le témoin d'asymétrie DSM/ESM** : les deux rôles posés dans la MÊME entité, chacun voit un
  ensemble de modèles DIFFÉRENT — un contrôle à un seul rôle rendrait la même observation quel que
  soit le défaut (§7.0, quatrième proposition) ;
- **le cycle de vie complet exercé une fois, en vrai** : créer, composer les tâches, publier,
  archiver, restaurer — chaque transition change le code HTTP attendu de la suivante ;
- **`OFFICE` refusé (403) sur les modèles, mais reçu (200) sur le suivi** — les deux extrêmes de la
  même matrice, dans le même script ;
- **`ECART-066` éprouvé dans le sens du refus** : un DSM, propriétaire de sa propre version
  archivée, est refusé (403) en la restaurant — le cas précis que la grille large aurait laissé
  passer à tort.

Non couvert par ce script, et ce n'est pas un oubli : `make ecrans-check` (extension générique déjà
en place) et `make residu-check` (dérivé du catalogue) couvrent déjà, sans une ligne ajoutée, la
fraîcheur du conteneur `web` et l'absence de ligne orpheline — les répéter ici aurait été une
troisième déclaration de la même preuve (§7.27). Aucun mode `--temoin` séparé n'a été ajouté :
l'asymétrie et le refus `ECART-066` sont déjà des témoins positifs et négatifs à l'intérieur du même
script, chacun produisant une observation différente d'un défaut plausible.

Ajouté à `make check`, nommé dans `ci.yml` (§7.36).

---

# 4. Décisions, écarts et questions

**`DEC-614`** ajoutée au registre — couvre l'élargissement du menu (§2.2), l'extension de l'API
(§2.3) et le script de pile combiné (§3.3). Aucun écart nouveau.

`ECART-012` (report à Léa) reste ouvert, non bloquant. Aucun rapport avec `T14`.

---

# 5. Ce que `T14` laisse

- La rubrique « Administration » et ses trois sections sont livrées et vérifiées réellement.
- **`T15` reste à faire** : recette, §30, checklist `G7` — la dernière sous-étape du lot.
- Issue [#178](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/178) (`US003`) et
  [#183](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/183) (`US008`) se referment à la
  main après la fusion, leurs critères désormais tenus par `T14`.
- Un sélecteur de portée (`DSM`/`CIRCLE`/`GLOBAL`) pour la création d'un modèle ou d'une tâche de
  référence n'est pas construit — aucun critère actuel ne le réclame, noté pour un lot ultérieur si
  le besoin se confirme (§2.5).

---

# Validation demandée à Jonathan

`T14` est prête pour fusion : zéro régression mesurée, aller-retour réel effectué et documenté,
script de pile différé construit et vert, décisions du menu et de l'extension API actées. Pouvez-
vous valider la fusion ?

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
