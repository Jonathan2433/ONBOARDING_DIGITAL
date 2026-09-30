# Compte rendu — `T4` du LOT 7 : le catalogue des tâches

**Date :** 26 septembre 2026
**Sous-étape :** `T4` — `onboarding_task_reference`, identifiants stables
**Décision :** `DEC-603`
**Story :** aucune — structurel, ferme `ECART-013`

---

# 1. État du lot

`T1` à `T4` du LOT 7 sont désormais faites (`DEC-599`, `DEC-600`, `DEC-601` + correctif
`DEC-602`, `DEC-603`). Onze sous-étapes restent, `T5` — les modèles et leurs versions —
est la prochaine. Détail du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

`onboarding_task_reference` existait déjà depuis `T1` (migration `0020`) — huit colonnes,
deux index partiels d'unicité (un par périmètre, entité ou global). `T4` pose le **service**
et les **deux routes** qui l'exploitent :

- `GET /entities/{code}/onboarding/task-references` — le catalogue reutilisable dans cette
  entité, UNION des tâches propres à l'entité et des tâches GLOBALES ;
- `POST /entities/{code}/onboarding/task-references` — créer une tâche, `portee: "ENTITE"`
  (par défaut) ou `portee: "GLOBAL"`.

Nouveaux fichiers : `app/onboarding/catalogue.py` (lecture + écriture), extensions de
`app/onboarding/perimetre.py` et `app/onboarding/routes.py`. Contrat partagé :
`packages/contracts/src/catalogueDesTaches.ts` (lecture, avec son test) et deux entrées au
manifeste JSON — la création, écriture pure, n'a pas de module TypeScript propre, même règle
que la complétion/validation de `T3`.

## 2.1 Une seule grille gouverne cinq des sept lignes du §9

Confrontation du 26/09/2026 : « Créer une tâche de référence » et « Réutiliser une tâche de
référence » portent EXACTEMENT la même grille — `DSM` Consultants, `ESM` Entité, `BOOST`
Cercle, `OFFICE` tiret, `ADM-E` Entité, `SUPER` Global. Les deux lignes écartées —
« Consulter les modèles publiés » (une grille plus large, sans objet pour le catalogue
lui-même) et « Restaurer une version » (`Conditionnel` pour `ESM`, `ECART-066`, hors
périmètre de `T4`) — ne portent pas sur `onboarding_task_reference`.

Une seule fonction de périmètre (`peut_creer_une_tache_de_reference_globale`) plus un
ensemble de rôles déclaré (`ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES`) suffisent donc, exactement
comme `T2`/`T3` avaient factorisé leurs trois premières lignes concordantes (§7.27).

## 2.2 `Consultants` et `Cercle` se réduisent à l'Entité — et ce n'est pas une lecture large

**Le piège mesuré, documenté dans l'en-tête de `perimetre.py`.** `onboarding_task_reference`
(modèle §13.1) ne porte QUE `entity_id`, nullable pour le global — ni `scope_circle_id` ni
`scope_person_id`, à la différence d'`onboarding_template` qui les recevra à `T5`. Une tâche
de référence n'est rattachée à AUCUN cercle ni AUCUN DSM en particulier : elle n'a pas de
CIBLE, contrairement à `arrival_profile` où `_MEMBRE_DU_CERCLE_DU_BOOSTER` vérifie un
rattachement réel entre l'acteur et la personne visée.

Le `DSM` et le `BOOST` reçoivent donc, pour CETTE ressource précisément, la même portée que
l'`ESM` et l'administrateur d'entité : LEUR entité. Ajouter une colonne pour distinguer plus
finement serait une invention que le corpus ne demande pas (§6.5) ; refuser purement et
simplement `DSM`/`BOOST` en serait une autre, tout aussi fausse — la matrice leur accorde un
droit, elle ne dit simplement pas comment le réduire plus loin que l'entité pour cette
table-là. Seize tests le prouvent rôle par rôle : `test_un_DSM_cree_une_tache_de_reference_
dans_SON_entite`, `test_un_BOOSTER_cree_une_tache_de_reference`, et leurs refus symétriques
pour `OFFICE` et l'employé nu.

## 2.3 `GLOBAL` est réservé à `SUPER` — une asymétrie, pas une absence de droit

Seule la colonne `SUPER` du §9 atteint `Global` sur la ligne « Créer une tâche de
référence ». Un `ESM` ou un `ADM-E` qui demande `portee: "GLOBAL"` obtient `403
acces_refuse` — et deux tests le distinguent explicitement d'un refus général :
`test_un_ESM_NE_cree_PAS_de_tache_GLOBALE` et `test_un_ADM_E_NE_cree_PAS_de_tache_GLOBALE`
prouvent que ces deux rôles POSSÈDENT le droit `ENTITE` juste avant de le voir refuser en
`GLOBAL` — la même discipline que l'asymétrie `BOOST` mesurée en `T3`.

Aucune requête SQL n'est nécessaire pour distinguer `SUPER` : `resoudre_les_permissions`
l'ajoute sans condition d'entité (§5.1, l'exception globale), donc sa présence dans `roles`
suffit — `peut_creer_une_tache_de_reference_globale` est une fonction pure.

## 2.4 Le catalogue est une UNION, et l'isolement se prouve dans les deux sens

Modèle §13.1 : un modèle d'une entité peut réutiliser une tâche PROPRE à cette entité ou une
tâche GLOBALE — jamais celle d'une AUTRE entité. Deux témoins le prouvent :
`test_le_catalogue_UNIT_les_taches_de_l_entite_ET_les_GLOBALES` (les deux apparaissent
ensemble dans la même entité) et `test_une_tache_D_ENTITE_reste_INVISIBLE_dans_une_AUTRE_
entite` (une tâche d'entité n'apparaît PAS dans le catalogue d'une entité voisine, tandis
qu'une tâche globale, elle, y apparaît). Sans le second témoin, le premier serait satisfait
par une requête qui ne filtrerait rien du tout.

## 2.5 Un défaut réel trouvé en écrivant le décor de test : `person`/`user_session` avant `person`

**Un vrai défaut de mon propre test, trouvé avant la fusion.** Le premier jet du `decor`
supprimait `person` avant `user_session` (les sessions ouvertes par `_session()`), ce que la
clé étrangère `fk_user_session_person_id_person` refuse. Puisque le nettoyage tourne dans une
**seule transaction**, l'échec faisait tout annuler — y compris la suppression, pourtant
réussie jusque-là, des lignes `onboarding_task_reference` du test. Les tâches globales de
tests interrompus polluaient alors les tests suivants du même run, faisant échouer un témoin
d'isolement qui n'avait rien de faux (`§7.30` du LOT 5 : un nettoyage incomplet fait échouer
des tests sans rapport). Corrigé en ajoutant `auth_event` et `user_session` à la liste de
nettoyage, dans le bon ordre — même discipline que le `decor` de `T3`.

## 2.6 Un résidu du modèle, trouvé en lisant `T5` en avance, laissé à `T5`

**`onboarding_template_version.state` réutilise `EtatDuModele` (`draft`/`active`/`archived`),
et le modèle §13.3 exige `draft`/`published`/`retired` — une énumération DIFFÉRENTE de celle
du conteneur `onboarding_template` (§13.2).** Posé par `T1`, ce n'est PAS un défaut de `T4` —
`onboarding_task_reference` ne touche à aucune de ces deux tables — mais il a été repéré en
lisant le modèle §13 en préparant ce compte rendu. Il ne peut pas rester silencieux : le jour
où `T5` tentera d'écrire `state = 'published'`, la contrainte `state_valide` actuelle le
REFUSERA — bruyamment, sous le nom de la contrainte, jamais en silence. **Non bloquant pour
`T4`, nommé pour `T5`**, qui devra ajouter une énumération propre (`draft`/`published`/
`retired`) et corriger la contrainte par une nouvelle migration — jamais en modifiant `0020`.

## 2.7 Ce que `T4` ne fait pas, et ce n'est pas un oubli

Ni modification, ni désactivation, ni archivage d'une tâche de référence : aucune ligne du
§9 ne les nomme. `active` et `archived_at` restent des colonnes du modèle SANS écrivain — un
résiduel nommé plutôt qu'inventé (§6.5). Si `T5`, `T10` ou un lot ultérieur en a besoin, c'est
à lui de le décider et de l'écrire.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` | 0 erreur |
| `uv run ruff format --check .` | conforme |
| `pnpm run format:check` (Prettier) | conforme, après un passage `--write` sur les deux nouveaux fichiers TypeScript |
| `make typecheck` (mypy strict + `tsc --noEmit`) | 0 erreur, 162 fichiers Python, 3 paquets TypeScript |
| `uv run pytest -q` | **16 nouveaux tests, tous verts** — `apps/api/tests/test_catalogue_des_taches.py` |
| `make test-frontend` (Vitest) | **270 + 111 + 225 = 606** (259 → 270 pour `contracts`, +11 pour `catalogueDesTaches.test.ts`) |
| `apps/api/tests/test_contrat.py` | 5/5 — chemins et codes du manifeste conformes au schéma réellement servi |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes, tous les totaux dérivés confirmés |

**Zéro régression, prouvée par comparaison nommée.** `uv run pytest -q` sur `develop` avant
`T4` rendait **74 échecs environnementaux** (pollution du jeu de démo, voir `CLAUDE.md` §11).
Après `T4` : toujours **74**, et la comparaison `comm` des deux listes triées est **vide dans
les deux sens** — aucun nouvel échec, aucun échec disparu. Le 75ᵉ échec observé en cours de
route (`test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste`) était réel — le
manifeste ne déclarait pas encore les deux routes — et a été corrigé avant cette mesure finale.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-603` | `T4` livrée : le catalogue des tâches, lecture et création, ferme `ECART-013` structurellement |

**`ECART-013` est fermé structurellement, pas par contenu.** Le remède posé — un identifiant
fonctionnel unique par tâche commune, partagé par construction via `onboarding_template_task.
task_reference_id` — existe désormais dans le service. La **preuve par l'usage réel** (les
cinq tâches communes du prototype effectivement partagées entre mission et intercontrat) est
`T10` (`US007`), qui met la conservation par référence stable à l'épreuve d'un changement de
parcours réel. Le registre des écarts est mis à jour pour dire les deux : structurellement
clos ici, éprouvé à `T10`.

**Aucune question nouvelle.** `ECART-066` (restauration « Conditionnelle ») reste ouvert,
bloquant pour `T6`/`T11` seulement — sans objet pour `T4`.

---

# 5. Ce que `T4` laisse

- Le catalogue est vide de toute donnée de référence réelle : aucune tâche commune du
  prototype n'a été créée par cette sous-étape — ce serait anticiper `T5`/`T10`, qui décident
  quels modèles les consomment. `T4` pose le SERVICE, pas le contenu.
- Le résidu `onboarding_template_version.state` (§2.6) est nommé pour `T5`.
- `T5` — les modèles et leurs versions — est la prochaine sous-étape.

---

# Validation demandée à Jonathan

Merci de valider `T4` pour fusion. Commande de fusion et de retour arrière ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
