# Compte rendu — `T3` du LOT 7 : validation et publication de la fiche d'arrivée

**Sous-étape :** la troisième du lot — compléter, valider et publier la fiche d'arrivée
**Date :** 26 septembre 2026
**Décision :** `DEC-601`
**Stories :** `MVP-L07-US001` (2/2), `MVP-L07-US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 7**, ouvert le 25/09/2026 (`DEC-598`), **quinze** sous-étapes |
| Faites | `T1`, `T2`, **`T3`** |
| Restent | `T4` à `T15` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/onboarding/ecriture.py` | **NOUVEAU.** `completer_la_fiche_arrivee` (crée ou modifie), `valider_et_publier_la_fiche_arrivee` (les deux en un geste) |
| `apps/api/app/onboarding/perimetre.py` | Refactoré : `_dans_le_perimetre_personnel_non_publie` factorise la grille commune à « Consulter » (×2) et « Compléter » ; `peut_completer_la_fiche_arrivee` (nouveau) l'appelle ; `peut_valider_et_publier_la_fiche_arrivee` (nouveau) est **séparée**, la seule ligne du §7 où `BOOST` diverge |
| `apps/api/app/onboarding/routes.py` | Deux routes : `PATCH .../arrival-profile` (compléter), `POST .../arrival-profile/validation` (valider et publier) |
| `packages/contracts/src/contrat-api.json` | Deux entrées d'endpoint (`completionDeLaFicheArrivee`, `validationDeLaFicheArrivee`) — **écriture pure, aucun module TypeScript** : la règle du LOT 6 (`liens.ts`) veut qu'une sous-étape qui SERT une lecture pose son module, celles qui servent une écriture ne le font pas |
| `apps/api/tests/test_validation_de_la_fiche_arrivee.py` | **20 tests d'intégration**, à travers le routeur réel, CSRF compris |

**1 841 tests** au total désormais (+20 sur `T2`) : 1 246 pytest (867 d'intégration), 595 Vitest (inchangé, écriture pure).

## 2.1 La publication est automatique à la validation — un seul appel, pas deux

Matrice §7.1, à la lettre : « La fiche est publiée automatiquement lorsque le nouvel arrivant la
valide. » Le modèle §12.1 déclare bien un état `validated` intermédiaire dans son énumération
(`draft, validated, published, archived`), mais **aucune règle du corpus ne produit un état où
une fiche serait validée sans être publiée** — l'inventer aurait été une deuxième règle non
écrite. `valider_et_publier_la_fiche_arrivee` fait donc passer `state` de `draft` à `published`
**directement**, `validated_at` et `published_at` portant le même instant.

Le témoin central, `test_la_validation_PUBLIE_dans_le_MEME_appel`, prouve qu'un **seul** appel
HTTP suffit — un critère qui aurait exigé deux gestes distincts aurait reconduit le défaut §7.39
du LOT 6 (un critère qui suppose une action que le corpus ne demande pas).

## 2.2 `recent_until` est calculé par PostgreSQL, pas par Python

« Un mois après la date d'arrivée » (modèle §12.1) est une arithmétique de **calendrier**, pas
une durée fixe : `arrival_date + INTERVAL '1 month'` gère nativement les fins de mois (31 août →
30 septembre) que `timedelta(days=30)` ne gérerait pas, et le projet n'a aucune dépendance de
calendrier (`dateutil` absent de `pyproject.toml`). Vérifié empiriquement contre la base réelle :
`'2026-01-31'::date + INTERVAL '1 month'` rend `2026-02-28`, du type `date`, sans caster
explicitement le résultat de l'addition. Un test le prouve sur le décor (`arrival_date`
2026-10-15 → `recent_until` 2026-11-15).

## 2.3 `Support` n'est nulle part dans la légende — le même piège que `§7.45`/`§7.46`

Trois lignes du §7 emploient `Support` (et `Support cercle`) comme valeur de cellule, et **la
légende du §4 ne le définit pas**. Cherché dans tout le corpus — les deux occurrences du §6.1
(« Enregistrer/retirer l'autorisation photo »), et l'énumération `self_service`/`admin_support`/
`migration` de `photo_authorization.source` (modèle §12.2) — rien ne lui attache de règle
supplémentaire (motif, fenêtre temporelle, audit) au-delà de la portée déjà lisible : **`Support`
couvre exactement `Entité`/`Cercle`/`Global`**, l'unique différence étant sémantique — une
assistance sur la fiche d'un AUTRE, jamais une portée plus large. En inventer une aurait été
§6.5.

**Parce que les trois lignes concordent, le même calcul les gouverne toutes les trois** (§7.27) :
`peut_completer_la_fiche_arrivee` appelle le même helper privé que `peut_lire_la_fiche_arrivee`,
refactoré de `T2` sans changer son comportement externe — les 11 tests de `T2` restent verts sans
modification.

## 2.4 L'asymétrie `BOOST` — la seule ligne du §7 où il diverge

`BOOST` porte `Support cercle` sur « Compléter » et **tiret** sur « Valider et publier » — la
seule des trois lignes de la fiche où il diffère. `peut_valider_et_publier_la_fiche_arrivee` est
donc une fonction **séparée**, qui n'appelle pas le helper des deux lignes précédentes.

Le témoin, `test_un_BOOSTER_NE_VALIDE_PAS`, prouve d'abord que le Booster **peut** compléter la
fiche (sans quoi son refus de valider ne prouverait qu'une absence générale de droit, pas
l'asymétrie elle-même), puis qu'il ne peut pas la valider.

## 2.5 Une correction en cours de rédaction : ce que `T7` du LOT 5 a réellement livré

Ma première rédaction affirmait que « modifier la présentation après validation »
(`entity_membership.short_bio`/`fun_fact`, §6.1) était **déjà livrée** par `T6`/`T11` du LOT 5.
**Mesuré avant de le laisser dans le code** : `grep` sur `short_bio` dans `apps/api/app/` ne
rend **aucune** écriture, seulement sa lecture (`profil.py`, `routes.py`). Relu
`compte-rendu-t7-lot-5.md` : l'arbitrage de Jonathan à cette sous-étape a explicitement
**reporté** « présentation courte, fun fact et cercles secondaires », les nommant comme tels —
ce n'est pas un oubli, c'est une décision déjà prise et documentée, jamais rattrapée depuis.

**Conséquence pour `T3` : `arrival_profile.short_intro`/`fun_fact` et
`entity_membership.short_bio`/`fun_fact` restent deux champs distincts, sans passerelle entre
eux.** Une fois une fiche d'arrivée publiée, la présentation qu'un nouvel arrivant y a écrite
n'alimente PAS sa fiche profil ordinaire (LOT 5, `MVP-L05-US004`) — qui affichera un `short_bio`
vide tant que le résidu du LOT 5 n'est pas comblé. **Rien dans le corpus ne demande cette
passerelle** : les deux lignes du §6.1 concernées restent des résidus non livrés du LOT 5, hors
périmètre de `T3`. Corrigé dans les trois endroits où l'affirmation fausse avait été écrite —
`ecriture.py`, `routes.py`, `contrat-api.json` — avant de committer, pas après (§7.11).

## 2.6 Deux résidus nommés, ni l'un ni l'autre inventé

- **`photo_media_id` n'est pas accepté par la complétion.** Aucune route d'upload ni
  d'autorisation de média n'existe encore dans ce dépôt — `photo_authorization` (LOT 5) n'a
  jamais eu de service d'écriture, seulement sa déclaration en base. L'accepter aurait inventé
  un chaînon que rien ne construit (§6.5), exactement comme `T2` l'avait déjà décliné pour la
  lecture de la miniature ;
- **la passerelle `short_intro` → `short_bio`** décrite au §2.5 ci-dessus, résidu du LOT 5, non
  du LOT 7.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_validation_de_la_fiche_arrivee.py -m integration` | **20/20** |
| `uv run pytest apps/api/tests/test_fiche_arrivee.py -m integration` | **11/11**, aucune régression après le refactor de `perimetre.py` |
| `uv run pytest apps/api/tests/test_contrat.py` | vert — deux chemins déclarés au manifeste, codes documentés |
| `make test-frontend` | 595/595, inchangé (écriture pure, aucun module TS) |
| `uv run pytest` (base réelle, jeu de démo) | 74 échecs, **identiques byte pour byte** à `origin/develop` |
| `make lint`, `make typecheck`, `make parametres-check`, `make icloud-verify`, `make sources-check`, `make audit` | tous verts |
| `make parametres-check` | 58 partages légitimes (inchangé), aucun paramètre partagé entre deux colonnes de types différents dans le nouveau code |

---

# 4. Décisions, écarts et questions

- `DEC-601` (détail dans `docs/decisions/registre-decisions.md`)
- Aucun écart ouvert par cette sous-étape — le résidu du §2.5 est déjà porté par le LOT 5, pas
  un défaut nouveau

---

# 5. Ce que `T3` laisse

- Compléter et valider/publier sont faits ; `T4` — le catalogue des tâches, `onboarding_task_reference` —
  est la prochaine, et clôt structurellement `ECART-013`
- `photo_media_id` reste un résidu nommé, à réexaminer quand une route d'upload existera
- La passerelle `short_intro`/`short_bio` reste un résidu du LOT 5, non traité ici
- `ECART-012` et `ECART-066` restent ouverts, non touchés, non bloquants pour `T4`

# Validation demandée à Jonathan

`T3` est faite : la fiche se complète et se valide, la publication est automatique en un seul
geste, `recent_until` est exact, et l'asymétrie `BOOST` (aide à compléter, jamais à valider) est
prouvée. Zéro régression. La prochaine est `T4`.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T3
gh pr close <n> --delete-branch            # retour arrière
```
