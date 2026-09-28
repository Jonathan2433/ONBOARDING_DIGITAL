# Compte rendu — `T13` du LOT 7 : les écrans du nouvel arrivant

**Sous-étape :** `T13` — Écrans du nouvel arrivant (fiche d'arrivée, parcours, tâches)
**Décision :** `DEC-613`
**Date :** 28 septembre 2026
**Branche :** `feature/lot7-t13-ecrans-nouvel-arrivant`, depuis `develop` à jour (`3252350`, tête après
fusion de `T12`, PR [#197](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/pull/197))

---

# 1. État du lot

LOT 7 ouvert le 25/09/2026 (`DEC-598`), quinze sous-étapes. `T1` à `T12` déjà fusionnées. `T13`
livre les **trois** écrans que le découpage nomme dans son intitulé — fiche d'arrivée, parcours,
tâches — mais **une seule page les compose**, `PageMonOnboarding.tsx`, sous la rubrique
`mon-onboarding` réservée depuis `T4` du LOT 4 (`RUBRIQUES`, `routes.ts`).

**Aucune route API nouvelle.** `T2`/`T3` livraient déjà la fiche d'arrivée (lecture, complétion,
validation/publication) ; `T7` le parcours ; `T8` terminer/annuler une tâche. `T13` est le premier
**consommateur écran** de ces six routes, posées entre le 25 et le 27/09/2026 sans qu'aucun bouton
ne les appelle encore.

---

# 2. Ce que la sous-étape a produit

## 2.1 Une seule page, jamais trois écrans distincts

Le découpage de `fiche-lot-7.md` §3 nomme « fiche d'arrivée, parcours, tâches », et `RUBRIQUES`
(LOT 4) ne réserve qu'**un** chemin, `mon-onboarding`. Composer trois routes distinctes aurait donc
soit inventé deux chemins que le corpus ne nomme pas, soit rendu la troisième inatteignable. La
page compose donc deux sections — `SectionFiche` et `SectionParcours`, cette dernière rendant
chaque tâche par `LigneDeTache` — exactement comme `PageProfil` (LOT 5, `T11`) compose la fiche et
l'historique en un seul appel `Promise.all`.

**Cette page ne prend jamais d'appartenance en paramètre**, et c'est le point : contrairement à
`PageProfil` (`/trombinoscope/:appartenance`), il n'y a aucun `:appartenance` dans l'adresse — c'est
toujours « la mienne ».

## 2.2 `GET …/permissions` étendu d'un champ `appartenance` — le seul moyen de savoir « qui je suis »

Aucune route de l'onboarding n'accepte de cible implicite (matrice §7, §8.1) : chacune exige un
`entity_membership_id` explicite dans son chemin. Or rien, avant `T13`, ne donnait au frontend
l'identifiant de l'appartenance de l'appelant dans l'entité consultée.

**Option retenue, validée par Jonathan** : étendre `GET /entities/{code}/permissions` (LOT 4, `T8`)
d'un champ `appartenance` — l'entity_membership_id **occupant** de l'appelant, `null` hors de
l'entité principale ou sans appartenance occupante. Nouvelle fonction
`_appartenance_occupante` (`app/permissions/services.py`), même prédicat que `entite_principale`
(le même index unique du LOT 2, `uq_entity_membership_person_id_occupante`, garantit qu'il n'y en a
jamais deux). Cette réponse est **déjà appelée une fois par page** par `CadreApplicatif` : la
réutiliser évite un aller-retour réseau de plus, contre l'alternative — une route dédiée — qui en
aurait ajouté un à chaque chargement de l'écran.

Cette extension ne décide **rien** de nouveau côté permissions : c'est une identité, pas une règle
d'accès. Le contrat TypeScript (`portail.ts`) et la route (`permissions/routes.py`) sont mis à jour
en conséquence, avec leurs tests.

## 2.3 « Mon onboarding » apparaît VRAIMENT dans le menu, désormais

`droitsDeNavigation` (`routes.ts`, LOT 4 `T9`) rendait `aUnParcoursActif` figé à une constante
`UN_PARCOURS_ACTIF_EST_POSSIBLE = false`, posée sciemment au LOT 4 faute de table de parcours — et
un test l'épinglait pour forcer ce lot-ci à la changer **délibérément** (§7.32 du LOT 5).

Elle devient une fonction **pure** prenant `aUnParcoursActif` en argument réel.
`CadreApplicatif` interroge `GET …/onboarding-parcours` de l'appelant, mais **séquencé** après la
réponse de `/permissions` (dont il a besoin de `appartenance`) — jamais en parallèle des trois
autres appels (entité, liste des entités, permissions), qui ne dépendent d'aucune autre réponse.
`aUnParcoursActif` vaut `true` seulement si `instance.etat === 'active'` : une instance `archived`
ou `replaced` ne rend pas la rubrique visible.

## 2.4 Défaut trouvé et corrigé, dans un code écrit à `T7`, jamais exercé par un écran avant `T13`

`validerLeParcours` (`packages/contracts/src/parcoursOnboarding.ts`) exigeait que `instance`,
`progression` **et** `prochaine_tache` soient nuls ENSEMBLE, ou aucun des trois. C'est **faux**
pour `prochaine_tache` : `_prochaine_tache` (`app/onboarding/instances.py`) rend `None` dès que plus
aucune tâche n'est `todo`/`reopened` — **même** quand l'instance reste `active` (une version sans
aucune tâche obligatoire, dont toutes les tâches facultatives sont terminées, n'est jamais archivée
automatiquement : `T11` n'archive que sur la DERNIÈRE tâche obligatoire).

Une réponse `200` parfaitement légitime aurait donc levé côté client et rendu `corps: null`,
silencieusement — même classe que le défaut `T11-7` du LOT 5. Trouvé en écrivant le témoin d'un
test (`parcoursOnboarding.test.ts`), jamais en production. Corrigé pour distinguer les deux
invariants réels : `instance`/`progression` nuls ensemble (`lire_le_parcours` ne calcule jamais
l'un sans l'autre) ; `prochaine_tache` n'est contraint QUE quand `instance` est nul (aucun parcours
affecté).

## 2.5 Le frontend ne propose pas un droit déjà refusé, et ne calcule aucune règle métier

- **« Valider et publier » reste désactivé** tant que la présentation courte est vide, ou que des
  modifications locales ne sont pas enregistrées — pas parce que l'API l'exigerait autrement (elle
  refuserait de toute façon en 422/409), mais parce que proposer un bouton dont l'échec est déjà
  connu serait l'avertissement faux du §7.21 du LOT 6.
- **Après publication (§6.2)**, le nouvel arrivant perd le droit de modifier directement sa fiche :
  la présentation et le fun fact basculent en lecture seule, aucun champ de saisie n'est rendu.
- **Aucune fenêtre de cinq minutes n'est calculée côté client.** Le bouton « Annuler » est proposé
  pour TOUTE tâche `completed` ; c'est le `409` de l'API — `delai_d_annulation_depasse` ou
  `transition_de_tache_invalide`, indistingués côté client, même convention que `messageDeRefus` de
  `PanneauEditionDeContenu.tsx` (LOT 6, `T10`), qui ne lit jamais le corps d'erreur — qui referme la
  fenêtre. Un calcul client dupliquerait la règle du §8.3 et divergerait à la première horloge
  désynchronisée (même classe que `T8-4`/§7.33 du LOT 6).

Un changement de `state` après un enregistrement réussi remonte le composant `SectionFiche` par sa
`key={version}`, jamais un `setState` synchrone dans un effet — `react-hooks/set-state-in-effect`
l'aurait refusé — même parade que « le chargement est dérivé, il n'est pas un état posé »
(`PageProfil`).

---

# 3. Contrôles exécutés

- `ruff check`, `ruff format --check`, `mypy` (backend) : 0 erreur.
- `pnpm run lint` (ESLint, tout le monorepo), `pnpm run format:check` (Prettier) : 0 erreur.
- `pnpm --filter web run typecheck`, `pnpm --filter @onboarding/contracts run typecheck` : 0 erreur.
- `make docs-check`, `make sources-check`, `make parametres-check` : verts.
- `make cadre-check` (dans `make check`) : 25 contrôles, 0 échec — le fil `appartenance → parcours →
  visibilité du lien` n'y est pas encore inclus (il vit dans les tests Vitest, §3.2).
- Backend : 2 nouveaux tests d'intégration (`test_permissions.py`, le champ `appartenance` dans
  l'entité principale et hors d'elle), tous les tests `test_permissions.py`/`test_contrat.py` : 21
  passés.
- Frontend : 308 tests `@onboarding/contracts` (+26 : `portail.test.ts`, `ficheArrivee.test.ts`,
  `parcoursOnboarding.test.ts`), 111 `@onboarding/ui` (inchangé), 247 `web` (+22 : 17 nouveaux dans
  `PageMonOnboarding.test.tsx`, 4 nouveaux + 2 réécrits dans `CadreApplicatif.test.tsx`, 2 réécrits
  délibérément dans `AffichageConditionnel.test.tsx`).

## 3.1 Zéro régression

Comparaison nommée sur la même base (`git worktree` sur `origin/develop`, `3252350`, tête après
fusion de `T12`), `pytest` bare (sans filtre `-m integration`, comme `make check`) lancé **depuis la
racine des deux côtés** — la leçon posée par `T12` elle-même (`CLAUDE.md` §9.2, item 18) :

```text
origin/develop (baseline)   75 échecs, 1329 passés  →  1404 tests
feature/lot7-t13 (branche)  75 échecs, 1331 passés  →  1406 tests
```

Les deux listes de 75 échecs, triées et comparées par `diff`, sont **identiques** — tous
environnementaux (le jeu de démo de la base de dev fait échouer des tests qui comptent des lignes
en absolu, §5.3 de `CLAUDE.md`), sans rapport avec `T13`. `-m integration` : 1 025 → 1 027 (+2, les
deux nouveaux tests de `test_permissions.py`).

## 3.2 Aller-retour réel effectué avant de déclarer l'écran terminé (§7.43 du LOT 6)

Un bouchon `fetch` ne prouve que ce qu'on a écrit dans le bouchon, jamais ce que l'API fait
réellement — la leçon du LOT 5, `T11`. Décor **réel** posé par `psql` sur la base de dev (une
personne, une appartenance active dans `BORDEA00`, un modèle publié à une tâche obligatoire, une
instance affectée), connexion par **lien magique réel** consommé dans le navigateur (`Mailpit`),
puis dans l'ordre :

| Geste | Requête réelle | Résultat |
|---|---|---|
| Lecture de la fiche et du parcours | `GET .../arrival-profile`, `GET .../onboarding-parcours` | `200`, champs organisationnels corrects, tâche `todo` affichée |
| Complétion de la présentation | `PATCH .../arrival-profile` | `200`, persistée après remontage (`key={version}`) |
| Validation et publication | `POST .../arrival-profile/validation` | `200`, état `Publiée`, champs passés en lecture seule |
| Complétion de la tâche | `POST .../taches/{tache}/completion` | `200`, progression `1/1`, bouton `Annuler` proposé |
| Annulation de cette complétion | `POST .../taches/{tache}/annulation` | `200`, tâche revenue à `todo` |

Le lien « Mon onboarding » est apparu dans le menu réel, confirmant le fil `appartenance → parcours
→ aUnParcoursActif` de bout en bout. Tous les appels réels à `200`, journal réseau et capture
d'écran à l'appui. Le décor a été **entièrement nettoyé** après la vérification (personne,
appartenance, modèle, instance, tâche, sessions et traces d'audit associées).

---

# 4. Décisions, écarts et questions

**`DEC-613`** ajoutée au registre. Aucun écart nouveau.

**Décision de Jonathan, le 28/09/2026 : pas de script `make onboarding-check` dans cette
sous-étape.** Chaque écran des LOTS 5/6 a reçu son propre script de pile dans la CI
(`verifier-profil.py`, `verifier-framework.py`, chacun 1 800+ lignes). `T14` livre aussi des écrans
(catalogue, modèles, suivi par périmètre) et recevra sa propre preuve outillée — combinée pour
`T13` et `T14` plutôt que dupliquée à deux reprises consécutives. Jusque-là, les tests
d'intégration, les tests Vitest et l'aller-retour réel du §3.2 tiennent lieu de preuve.

`ECART-012` (report à Léa) reste ouvert, non bloquant. Aucun rapport avec `T13`.

---

# 5. Ce que `T13` laisse

- La rubrique « Mon onboarding » et son écran sont livrés et vérifiés réellement.
- **`T14` reste à faire** : écrans d'administration — catalogue des tâches, modèles et leurs
  versions, suivi par périmètre. Mêmes grilles de rôles que celles déjà posées côté API (`T4` à
  `T6`, `T12`) : `OFFICE` ne doit voir apparaître aucune action de gestion sur les modèles
  d'onboarding.
- **`T14` devra aussi construire le script de pile différé par `T13`**, couvrant les deux
  sous-étapes.
- `T15` — recette, §30, checklist `G7` — reste la dernière sous-étape du lot.
- Issue `#183` (`US008`) reste **ouverte** : son corps nomme `T11`, `T12` et `T14` comme
  contributeurs, jamais `T13`.

---

# Validation demandée à Jonathan

`T13` est prête pour fusion : zéro régression mesurée, aller-retour réel effectué et documenté,
défaut pré-existant trouvé et corrigé, décision de report du script de pile actée. Pouvez-vous
valider la fusion ?

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
