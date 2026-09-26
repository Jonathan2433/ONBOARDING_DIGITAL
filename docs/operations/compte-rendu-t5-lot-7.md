# Compte rendu — `T5` du LOT 7 : les modèles et leurs versions

**Date :** 26 septembre 2026
**Sous-étape :** `T5` — `onboarding_template`, `_version`, `_task`
**Décision :** `DEC-604`
**Story :** `US003` (1/2)

---

# 1. État du lot

`T1` à `T5` du LOT 7 sont désormais faites. Dix sous-étapes restent, `T6` —
cycle de vie d'un modèle (publication, duplication, archivage, restauration)
— est la prochaine. Détail du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

Trois routes, dans l'ordre du §9 : créer un modèle (le conteneur,
`onboarding_template`), créer une nouvelle version brouillon
(`onboarding_template_version`), poser ou réordonner la liste de ses tâches
(`onboarding_template_task`). Nouveaux fichiers : `app/onboarding/gabarits.py`
(service), extensions de `app/onboarding/perimetre.py` et
`app/onboarding/routes.py`. Aucun module de contrat TypeScript : les trois
routes sont des écritures pures, même règle que la création de tâche du
catalogue en `T4`.

## 2.1 Un résidu nommé pour `T5` corrigé en préalable — migration `0021`

`onboarding_template_version.state` réutilisait `EtatDuModele`
(`draft`/`active`/`archived`, celle du conteneur) au lieu de sa propre
énumération (`draft`/`published`/`retired`, modèle §13.3). Ce résidu, trouvé
en préparant `T4`, n'était pas seulement cosmétique : **le témoin de cette
sous-étape — refuser d'écrire sur une version publiée — exigeait que la base
accepte `state = 'published'`, ce que la contrainte héritée de `0020`
refusait encore.** Corrigé par une NOUVELLE migration (`0021`), jamais en
modifiant `0020`, déjà appliquée. Zéro ligne existante rejetée : mesuré,
`onboarding_template_version` était vide avant la migration.

## 2.2 Ici, contrairement au catalogue, `Consultants` et `Cercle` ne se réduisent pas à l'entité

`onboarding_template` (modèle §13.2) porte de vraies colonnes de portée —
`scope_person_id`, `scope_circle_id` — qu'`onboarding_task_reference` n'a
pas. La limite qui collapsait `T4` à l'entité n'existe plus ici : un DSM ne
gère que SES propres modèles (`scope_person_id == lui-même`, §9.1 : « destiné
à ses consultants »), un Booster que ceux de SON cercle. Deux témoins
d'asymétrie le prouvent : un DSM est refusé sur le modèle d'un AUTRE DSM
actif ; un Booster est refusé sur un cercle de la même entité dont il n'est
pas responsable.

**`ESM`/`ADM-E`/`SUPER`, eux, ne sont pas bornés à un scope_type précis** —
même parti que `ROLES_DE_PORTEE_ENTITE` en `app/content/perimetre.py` (LOT
6) : un rôle de portée ENTITE gère aussi ce qu'un rôle LOCAL gérerait, jamais
l'inverse. Un ESM crée donc un modèle `DSM` pour N'IMPORTE QUEL DSM actif de
son entité, ou `CIRCLE` pour N'IMPORTE QUEL cercle — exactement ce que le
modèle §13.2 exige structurellement (« un scope DSM exige un DSM actif dans
l'entité », « un scope CIRCLE exige un cercle de la même entité »). Seize
tests couvrent les six lignes de la grille et les deux asymétries.

## 2.3 Deux résidus nommés par `T1`, instruits par le service — pas par la base

`app/onboarding/modeles.py` documentait depuis `T1` pourquoi
`onboarding_template.scope_circle_id` et `onboarding_template_task.
task_reference_id` portent des clés étrangères SIMPLES plutôt que
composites : `make isolation-check` exige `entity_id NOT NULL` à la SOURCE
pour toute clé composite, et les deux tables visées ont un `entity_id`
nullable. La cohérence d'entité n'était donc PAS garantie en base :

- un modèle `CIRCLE` doit viser un cercle de la MÊME entité — vérifié par
  `peut_gerer_un_modele_de_cette_portee`, avant toute écriture ;
- une tâche de référence ajoutée à une version doit être GLOBALE ou de la
  MÊME entité que le modèle — jamais celle d'une autre. Vérifié par
  `_tache_dans_le_perimetre_du_modele`, la même règle que `T4` documentait
  déjà (compte-rendu `T4`, §2.4) : « un modèle d'une entité peut réutiliser
  une tâche PROPRE à cette entité ou une tâche GLOBALE ».

Les deux résidus sont clos : un test par sens (accepté, refusé) pour chacun.

## 2.4 L'immuabilité d'une version publiée — le témoin de cette sous-étape

Aucune route de `T5` ne publie — `T6`. Le décor de test force donc
`state = 'published'` (et `'retired'`) DIRECTEMENT en base, exactement comme
les décors précédents écrivent des états qu'aucune route ne sait encore
produire. Poser des tâches sur une telle version rend `409
version_de_modele_immuable`, sans toucher la liste précédente — vérifié en
relisant qu'aucune ligne n'a été ajoutée après le refus.

## 2.5 « Ajouter ou réordonner » est une seule ligne : la liste entière remplace la précédente

Même lecture que `content_block` (LOT 6, `T6`) : `display_order` vaut
l'INDEX de la ligne dans le tableau reçu, et poser une nouvelle liste
REMPLACE l'ancienne — jamais un ajout qui empilerait. Un test le prouve
explicitement : deux tâches posées, puis les deux mêmes renvoyées dans
l'ordre inverse rendent toujours DEUX lignes, pas quatre, avec l'ordre
attendu. Aucune archive n'est écrite sur les lignes retirées : rien ne les
référence encore, aucune instance n'existe avant `T7`.

## 2.6 Ce que `T5` ne fait pas, et ce n'est pas un oubli

Ni publication, ni archivage, ni restauration, ni duplication d'un modèle ou
d'une version — matrice §9, lignes « Publier une version », « Archiver une
version », « Restaurer une version » : c'est `T6`, « Cycle de vie d'un
modèle » (`fiche-lot-7.md` §3), qui instruira aussi `ECART-066`. Aucune
lecture non plus : ni « Consulter les modèles publiés », ni
« Prévisualiser » — résiduels nommés, pour les écrans (`T13`/`T14`) ou le
cycle de vie.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` | 0 erreur |
| `uv run ruff format --check .` | conforme |
| `pnpm run format:check` (Prettier) | conforme |
| `make typecheck` (mypy strict + `tsc --noEmit`) | 0 erreur, 165 fichiers Python |
| `uv run pytest apps/api/tests/test_modeles_onboarding.py -q` | **29 nouveaux tests, tous verts** |
| `apps/api/tests/test_contrat.py` | 5/5 — les trois nouvelles routes déclarées au manifeste |
| `make migrate` (migration `0021`) | appliquée, tête `0021` |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un
`git worktree` sur `origin/develop` (`23f5151`), `.env` copié, a rendu **87
échecs environnementaux** (pollution du jeu de démo, `CLAUDE.md` §11) —
contre 87 sur cette branche également, et la comparaison `comm` des deux
listes triées de noms est **vide dans les deux sens** : aucun nouvel échec,
aucun échec disparu. Le 88ᵉ échec observé en cours de route
(`test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste`) était réel
— même classe qu'en `T4`, le manifeste ne déclarait pas encore les trois
routes — et corrigé avant cette mesure finale.

`uv run pytest -q --collect-only` : **1 296** tests (1 267 → 1 296, +29,
tous marqués `integration` puisqu'ils exercent la pile réelle) ;
`-m integration` : **917** (888 → 917, +29). `make test-frontend` :
inchangé, **270 + 111 + 225 = 606** — aucun module de contrat pour trois
écritures pures.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-604` | `T5` livrée : les modèles d'onboarding et leurs versions, scopes `GLOBAL`/`ENTITY`/`DSM`/`CIRCLE`, migration `0021` |

**Aucun écart nouveau, aucune question nouvelle.** `ECART-066`
(restauration « Conditionnelle ») reste ouvert, bloquant pour `T6`/`T11`
seulement — sans objet pour `T5`, qui ne publie ni n'archive rien.

---

# 5. Ce que `T5` laisse

- Aucun modèle réel n'est créé par cette sous-étape : aucune tâche commune
  du prototype n'est encore associée à une version — c'est `T10` (`US007`)
  qui décide quels modèles les consomment.
- `T6` — cycle de vie d'un modèle — est la prochaine sous-étape, et devra
  trancher `ECART-066` avant d'écrire la restauration.
- Les deux tables `onboarding_instance`/`onboarding_instance_task` restent
  intouchées : `T7` les instanciera depuis une version publiée.

---

# Validation demandée à Jonathan

Merci de valider `T5` pour fusion. Commande de fusion et de retour arrière
ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
