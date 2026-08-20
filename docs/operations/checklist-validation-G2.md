# Checklist de validation — porte `G2`

**LOT 2 — Socle de données et isolation multi-entités**
**Remise le :** 20 août 2026, à la sortie de la sous-étape `T12`
**Destinataire :** Jonathan — c'est **sa** décision
**Tag à poser après validation :** `v0.2.0`, annoté, sur `main`

Ce document est fait pour être **lu et coché**. Chaque ligne porte la commande qui la prouve et le
résultat réellement obtenu, le 20/08/2026. Aucun nombre n'y est affirmé sans avoir été mesuré.

> **Ce que ce lot a produit, en une phrase :** **18 tables métier**, **10 migrations** rejouables,
> **94 contraintes**, **85 index**, **8 déclencheurs**, et **373 tests** — dont l'isolation
> inter-entités prouvée par **8 clés étrangères composites** et un jeu de recette de **27 936
> lignes** dont toutes les requêtes répondent **sous 1,3 ms**.

---

## 1. Les sept critères de sortie de la roadmap

| | Critère | État | Ce qui le prouve |
|:--:|---|---|---|
| ☑ | toutes les migrations s'appliquent sur une base **vide** | **acquis** | `make migrations-check` — base jetable créée vide, `0` table au départ, chaîne appliquée, tête `0011` |
| ☑ | les migrations sont **rejouables** | **acquis** | même contrôle — descente à `base` sans table métier survivante, remontée à signature **identique** |
| ☑ | les contraintes critiques disposent de tests PostgreSQL | **acquis** | **373 tests**, dont **204** d'intégration sur PostgreSQL réel — dérivé par `pytest -m integration --collect-only`. Chaque refus a son **témoin** |
| ☑ | les relations structurantes sont **historisées** | **acquis** | `make historisation-check` — les **7** relations du §25.2, compte **dérivé du modèle** |
| ☑ | les tests d'**isolation** réussissent | **acquis** | `make isolation-check` + `make isolation-temoin` — 8 clés composites, 0 référence nue, et le témoin prouve les 4 discriminations |
| ☑ | **aucune dépendance à SQLite** | **acquis** | `make migrations-check` — 99 fichiers examinés, **0 usage réel**. Le contrôle cherche un `import`, une URL ou une dépendance, **non le mot** |
| ☐ | **Jonathan valide le modèle implémenté** | **ta décision** | ce document |

---

## 2. Les huit stories du lot

| Story | Objet | Sous-étape | État |
|---|---|---|---|
| `MVP-L02-US001` | entités, paramètres, domaines e-mail | `T2`, `T7` | **Done** — issue `#39` close |
| `MVP-L02-US002` | personnes et appartenances | `T3`, `T4` | **Done** — issue `#40` close |
| `MVP-L02-US003` | métiers, statuts, clients | `T5`, `T6`, `T7` | **Done** — issue `#41` close |
| `MVP-L02-US004` | historisation | `T8`, `T9` | **Done** — issue `#42` close |
| `MVP-L02-US005` | rôles et périmètres | `T10` | **Done** — issue `#43` close. **`ECART-032` ouvert**, voir §7 |
| `MVP-L02-US006` | isolation inter-entités | `T11` | **Done** — issue `#44` close |
| `MVP-L02-US007` (`P1`) | jeu de données fictif | `T12` | **Done** — 25 entités, 5 000 profils, 7 cas limites nommés |
| `MVP-L02-US008` | migrations Alembic | `T1`, `T12` | **Done** — 10 migrations, chaîne prouvée |

**Les sept `P0` sont `Done`, et la seule `P1` l'est aussi** — donc aucun arbitrage de dégradation
n'est demandé.

---

## 3. Les 25 contrôles de recette du modèle §30, classés

`make recette-modele-check` les **lit dans le modèle** et exige que chacun soit classé. Un contrôle
nouveau ou reformulé ferait échouer la cible plutôt que d'être ignoré.

| Statut | Nombre | Ce que cela veut dire |
|---|---:|---|
| **acquis** | **10** | prouvé par un test nommé, dont l'existence est vérifiée |
| **partiel** | **1** | §30.4 — voir ci-dessous |
| reporté | **13** | portent sur des tables que le LOT 2 ne crée pas, chacun rattaché à son lot |
| **inapplicable** | **1** | §30.8 — `ECART-031` |

**§30.4 — « un consultant actif possède un DSM actif », et la distinction compte.**
L'**unicité** est acquise : un consultant n'a jamais deux DSM actifs, prouvé par exclusion.
L'**existence**, elle, **ne peut pas être portée par la base** : l'appartenance doit exister avant
qu'une affectation DSM ne la référence, donc une contrainte à l'insertion serait circulaire. C'est
une règle de **processus**, rattachée au LOT 7.

**§30.8 — « un bureau publié possède entre un et trois responsables » est inapplicable**, et pas
faute d'effort : le §8.3 ne déclare **aucun état de publication** sur `office`. La condition n'a rien
à quoi se rattacher. C'est `ECART-031`, à instruire avant le LOT 6.

---

## 4. Les contrôles rejoués, avec leurs codes de sortie réels

Tous exécutés le 20/08/2026, sur cette machine, code de sortie lu par
`sortie=$(commande) && code=0 || code=$?`.

| Contrôle | Code | Ce qu'il a mesuré |
|---|:--:|---|
| `make check` | **0** | qualité complète : versions, iCloud, `docs-check`, `images-check`, `recette-modele-check`, format, lint, mypy strict, tests |
| `uv run pytest` | **0** | **373 tests**, 0 échec |
| `make migrations-check` | **0** | 269 colonnes, 94 contraintes, 85 index, 8 déclencheurs **identiques** entre base neuve et base courante |
| `make isolation-check` | **0** | 14 tables locales, 8 clés composites, **0** référence nue, **0** clé simple entre deux tables locales |
| `make isolation-temoin` | **0** | les **4** défauts délibérés détectés **et nommés** |
| `make historisation-check` | **0** | 7 relations, 10 exclusions, 3 colonnes nullables toutes protégées |
| `make recette-modele-check` | **0** | 25 contrôles classés, chaque acquis nomme un test qui **existe** |
| `make alembic-check` | **0** | une seule tête de migration |
| `make code-check` | **0** | 34 fichiers `.py` identiques entre dépôt et conteneur |
| `make docs-check` | **0** | 5 empreintes, 6 séquences, 7 totaux **dérivés** |

---

## 5. Démonstration guidée

### 5.1 Une base vide se construit **uniquement** par migrations

```bash
make migrations-check
```

Le contrôle crée une base **jetable**, vérifie qu'elle porte **0 table**, applique la chaîne, puis
**compare le schéma obtenu à celui qui tourne** — c'est cette comparaison qui prouve le critère.
Sans elle, on saurait que la chaîne s'applique, pas qu'elle produit le bon schéma.

Puis il redescend à `base`, exige qu'**aucune table métier** ne survive, remonte, et exige une
signature **identique**. La base jetable est supprimée même en cas d'échec.

### 5.2 L'isolation inter-entités, refusée **par la base**

```bash
make isolation-check
make isolation-temoin
```

Le premier examine les **colonnes**, non les contraintes — parce qu'une référence posée **sans** clé
étrangère donnerait la même observation qu'un schéma sain. Le second crée deux tables percées et
**exige que le contrôle échoue en nommant les quatre défauts**.

### 5.3 Le jeu de recette, au volume du critère

```bash
uv run pytest apps/api/tests/test_jeu_de_recette.py -s
```

**Mesuré le 20/08/2026 :** 27 936 lignes en 21,5 s, 26 entités, 5 129 personnes.

| Requête | Durée | Lignes |
|---|---:|---:|
| recherche d'une personne par e-mail normalisé | **0,6 ms** | 1 |
| membres occupants d'une entité | **1,0 ms** | 208 |
| missions actives d'une entité, avec leur client | **0,8 ms** | 101 |
| cercle principal actif de chaque membre | **1,3 ms** | 201 |
| responsabilités Framework actives | **0,6 ms** | 6 |
| comptage via `DepotLocal` | **0,8 ms** | 209 |

> **Le test n'exige PAS l'usage d'un index, délibérément.** Sur 5 000 lignes, un parcours séquentiel
> est souvent le plan **optimal** : PostgreSQL le choisit parce qu'il est plus rapide. Un test qui
> exigerait « aucun Seq Scan » exigerait donc le **contraire** de la performance. Il exige une
> **durée** — la grandeur du critère — et **rapporte** le plan.

### 5.4 Le jeu de données, écrit pour de bon

```bash
make jeu-de-donnees
```

Écrit 25 entités et 5 000 profils dans la base de développement, et **refuse** de s'exécuter si elle
porte déjà des personnes.

> **À savoir avant de la lancer :** de nombreux tests d'intégration comparent des comptes **absolus**.
> **Semer la base et lancer la suite s'excluent.** La cible le dit en sortie.

---

## 6. Ce que tu valides précisément

1. **le modèle est implémenté** : 18 tables métier du §5 au §8, avec leurs contraintes ;
2. **les migrations sont la seule source du schéma** : aucune table créée à la main, prouvé ;
3. **l'isolation inter-entités est portée par la base**, pas seulement par le code ;
4. **l'historisation est complète** sur les 7 relations que le §25.2 nomme ;
5. **un jeu de recette au volume du critère existe et reste exploitable** ;
6. **20 décisions** ont été prises et tracées pendant ce lot — `DEC-497` à `DEC-516`, toutes au
   registre. **Le nombre est dérivé de la plage, non estimé** : j'avais d'abord écrit « 43 ».

---

## 7. Ce que tu ne valides PAS, et qu'il faut savoir avant de trancher

| Élément | Ce qu'il faut savoir |
|---|---|
| **`ECART-012`** | **Attend Léa, et c'est le seul point du lot en attente d'une décision produit.** « `intercontrat` est imposé à une direction générale, faute d'une troisième valeur. » Le coût des deux options est mesuré depuis `T5` ; aucune n'est techniquement décisive. **Échu au plus tard avant le LOT 5** |
| **`ECART-031`** | Le §8.4 exige « un bureau **publié** », le §8.3 ne déclare aucun état de publication. La règle est **inapplicable**, non oubliée. À instruire **avant le LOT 6** |
| **`ECART-032`** | Le backlog interdit « aucune responsabilité **métier** active dans plusieurs entités » là où le **cahier**, la **matrice** et le **modèle** restreignent tous au seul **Booster**. Le cahier prévaut, le livrable est **conforme** — mais un relecteur du backlog conclurait à un critère manquant. **À dire à la porte** |
| **`QO-116`** | L'application se connecte à PostgreSQL en **superutilisateur**, alors que le cahier §20.1 pose le moindre privilège. **Arbitrage déjà pris : LOT 3** |
| **`QO-117`** | Aucune unicité sur `client_alias` : la portée est un choix métier. **LOT 9** |
| **Row-Level Security** | Le §2.5 la cite comme « compatibilité future ». Rien dans le corpus ne la datant, elle **n'est pas** mise en place, et ce n'est pas un oubli |
| **Les 13 contrôles reportés du §30** | Ils portent sur des tables que ce lot ne crée pas. Chacun est rattaché à son lot par `make recette-modele-check` |

---

## 8. Ce que la pose du tag déclenchera

1. **`v0.2.0` sur `main` fera tourner `images.yml`**, comme `v0.1.0` l'a fait. Les trois images
   seront publiées avec l'étiquette **`0.2.0`**. **Aucun `latest`** — `DEC-481`.
2. **`main` devra recevoir le contenu de `develop` par une VRAIE fusion.** `required_linear_history`
   a été retiré de `main` en `T11` du LOT 1 (`DEC-495`, `ECART-026`) précisément pour que cette
   porte ne reconflicte pas. **Compare les ARBRES, pas les commits** — §9.0 de la passation.
3. **Un tag posé ne se déplace jamais** — conventions §4.

---

## 9. Décision demandée

**Valides-tu la porte `G2` ?**

- **oui** → je fusionne `develop` dans `main` par une vraie fusion, je pose `v0.2.0` annoté, et
  j'ouvre le LOT 3 sur ta décision tracée ;
- **oui, avec réserve** → dis laquelle : je la consigne au registre et je l'annonce au LOT 3 ;
- **non** → dis ce qui manque : je le traite avant de reposer la question.

**Les six critères techniques sont acquis et mesurés. Le septième est le tien.**
