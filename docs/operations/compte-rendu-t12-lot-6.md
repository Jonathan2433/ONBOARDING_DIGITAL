# Compte rendu — `T12` du LOT 6 : recette, §30 et checklist `G6`

# 1. État du lot

LOT 6 — Framework, cercles, bureaux et contenus éditoriaux. Découpage validé le 13/09/2026
(`DEC-575`), douze sous-étapes. `T12` est la **dernière** : les **DOUZE sont faites**. Le lot ne
livre aucune story propre à `T12` — c'est la sous-étape de clôture, celle qui prouve que
l'ensemble tient, classe le §30 et prépare la décision de Jonathan à la porte `G6`.

# 2. Ce que la sous-étape a produit

## 2.1 La recette, épinglée sur la dernière publication réussie

`make images-pin` épingle `.env.recette` sur le commit `07571f9` (`T11`, dernière image publiée).
Base détruite et reconstruite (`make down-recette`, suppression du volume `db-data`,
`make up-recette`, `make migrate ENVIRONNEMENT=recette`) — jamais `make destroy`, qui emporterait
`caddy-data`. `make recette-check` : **57 contrôles, 0 échec**, les **7** séparations du cahier
§22.2 toutes prouvées sur l'état réel.

**Un incident rencontré et résolu, documenté plutôt que masqué.** Le premier `make up-recette` a
échoué : le port `8080` était occupé par `observatoire-ecom-studio`, un projet tiers de cette
machine — exactement le résiduel nommé au §7.23 de `CLAUDE.md`. Arrêté le temps de la recette
(`docker compose -p observatoire-ecom-studio stop`), relancé ensuite. Aucune donnée de ce projet
n'a été touchée. Un second incident, mineur : le conteneur Caddy de la recette s'est créé sans ses
ports publiés après le premier échec — recréé (`docker compose … rm -f -s caddy && … up -d
caddy`), publications vérifiées avant de poursuivre.

## 2.2 Un reclassement du §30, périmé depuis avant `T1`

`infra/scripts/verifier-recette-modele.py` classait `§30.8` — « un bureau publié possède entre un
et trois responsables » — `INAPPLICABLE`, citant `ECART-031` comme motif : « le §8.4 exige un
bureau publié, le §8.3 ne déclare aucun état de publication ». **`ECART-031` est clos depuis
`DEC-576`, à l'ouverture même du lot, avant `T1`** — le classement n'avait simplement jamais suivi.

Reclassé `PARTIEL`, ni `ACQUIS` ni `INAPPLICABLE` : le déclencheur de `T7` (migration `0018`,
`DEC-583`) garde la **transition** vers `published` — quatre tests le prouvent, sur les trois
valeurs valides (1, 2, 3) et les deux refusées (0, 4, plus une responsabilité future qui ne
compte pas) — mais pas l'**état permanent**. Un bureau publié conforme peut le rester en apparence
si ses responsables sont retirés ensuite ; rien ne l'en empêche, et `T4` ne ment pas sur ce
résiduel : sa lecture rend zéro à quatre responsables actifs, jamais une hypothèse. Même structure
que `§30.4`, déjà `PARTIEL` pour une raison analogue.

**13 acquis, 2 partiel, 10 reportés, 0 inapplicable** — contre 13/1/10/1 avant `T12`.

## 2.3 La checklist de la porte `G6`

`docs/operations/checklist-validation-G6.md` — les sept critères de sortie, les contrôles de
stack, une démonstration guidée en dix gestes, les grandeurs dérivées, la recette, le classement
du §30, ce que le lot n'a pas fait, et trois réserves. Soumise à la décision de Jonathan.

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make images-pin` | 3 empreintes relevées, identité `07571f9` vérifiée |
| `make recette-check` | **57** contrôles, 0 échec, 7/7 séparations |
| `make recette-modele-check` | 25/25 classés, 0 en trop, 1 reclassement |
| `make framework-check` | **77** contrôles, 0 échec (dev, inchangé depuis `T11`) |
| `make cadre-check` / `cadre-temoin` | 25 contrôles, 0 échec |
| `make ecrans-check` | 8 contrôles, 0 échec |
| `make permissions-check` | 0 échec |
| Les onze contrôles d'authentification | 0 échec, tous |
| Les contrôles de schéma (privilèges, secrets, isolation, historisation, migrations, alembic) | 0 échec, tous |
| `make check` (dev, base réelle) | 74 échecs pytest — **tous environnementaux**, comparés identiques à `origin/develop` par `git worktree` |
| `make residu-check` | 74 échecs environnementaux, **0 résidu** |
| `make icloud-verify`, `env-check`, `audit`, `docs-check` | 0 écart, tous |
| Vérification visuelle réelle | navigateur, session `demo.client@exemple.test`, entité `BORDEA00` — accueil, Framework, cercle, trombinoscope |

# 4. Décisions, écarts et questions

- `DEC-596` (détail complet dans `docs/decisions/registre-decisions.md`)
- Aucun écart ouvert, aucune question ouverte par cette sous-étape

# 5. Ce que `T12` laisse

- `checklist-validation-G6.md` attend la décision de Jonathan
- Le franchissement effectif de `G6` — fusion `develop` → `main`, tag `v0.6.0` — n'est **pas** fait
  ici : c'est la conséquence de la décision, pas une action de la sous-étape
- `QO-121` reste ouverte, hors du périmètre d'une clôture de lot

# Validation demandée à Jonathan

Le LOT 6 est **techniquement complet** — douze sous-étapes sur douze, `make check` vert hors des
74 échecs environnementaux connus, `make recette-check` et `make framework-check` verts. La
décision qui reste est la tienne : lis `checklist-validation-G6.md`, en particulier son §3 (la
démonstration guidée) et son §7 (ce que le lot n'a pas fait), et coche sa décision.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T12
gh pr close <n> --delete-branch            # retour arrière
```
