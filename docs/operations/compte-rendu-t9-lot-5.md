# Compte rendu — `T9` du LOT 5 : l'historique organisationnel

**Story :** `MVP-L05-US008` — *Consulter l'historique organisationnel pertinent*, `P1`, taille **M**, issue `#123`
**Décision :** `DEC-570`
**Écart ouvert :** `ECART-059`
**Date :** 12 septembre 2026

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026 (`DEC-558`), **onze** sous-étapes depuis `DEC-564` |
| Faites | `T1` à `T5`, `T7`, `T8`, et **`T9`** |
| Prochaine | **`T10` — le trombinoscope à l'écran** (`US003`) |
| Périmètre de `T9` | **cinq axes** — métier, statut et client, cercle, DSM, responsabilités — servis par `GET .../historique`. Trois arbitrages de Jonathan du 12/09/2026 |
| Hors périmètre, **nommé** | `technical_role_assignment` (§8.6, sécurité et non organisation) · les périodes d'appartenance elles-mêmes · toute pagination · toute énumération d'archives, qui reste ouverte depuis `T8` |
| Issue `#123` | **reste ouverte** : `T9` ne livre aucun écran, et `US008` en suppose un |

---

# 2. Ce que la sous-étape a produit

## 2.1 Le corpus ne dit rien des affectations passées, et « pertinent » non plus

**Mesure d'abord, avant d'écrire une ligne.**

```bash
grep -niE "ancien(ne)? (dsm|mission|client|cercle)|affectation(s)? (passee|precedente)" \
  docs/product/*.md docs/architecture/*.md
#  -> aucune occurrence

grep -niE "historique.{0,30}pertinent" docs/product/*.md
#  -> deux lignes, et ce sont les DEUX COPIES du critere de `US008` lui-meme
```

Le mot « **pertinent** » du titre de la story ne paraît donc nulle part ailleurs — **exactement la
forme d'`ECART-051`**, où « règles de visibilité » ne paraissait que dans les deux copies du critère
de `US004`. La leçon de `T4` s'applique telle quelle : on ne bâtit pas sur un mot que le corpus ne
définit pas ; on cherche la règle **applicable**.

## 2.2 La grille vient de la ligne « Audit » du §5, et elle refuse `EMP` et `NEW`

C'est le **seul** endroit où la matrice règle la consultation d'un historique :

```text
| Audit | ANON — | EMP — | NEW — | DSM Consultants | ESM Modifications fonctionnelles
        | BOOST Cercle | OFFICE Bureau | ADM-E Entite | SUPER Global |
```

C'est ce que le backlog appelle « **Responsable autorisé** », et l'arbitrage de Jonathan du
12/09/2026 l'a retenue : **savoir qui a managé qui et chez quel client est une information de
gestion, non une donnée d'annuaire**. L'alternative — les huit rôles, comme la fiche — publierait à
chaque employé la suite des clients chez qui un collègue est passé, ce qu'aucun document n'autorise.

**Les prédicats du DSM et du Booster sont ceux de `T7`, réemployés et non recopiés** : la résolution
vit dans le même module, et les deux requêtes sont les mêmes constantes. Un Booster ne voit que les
membres **principaux** de son cercle — le §6.2 limite ses actions « aux données du cercle », et
l'historique des missions d'une personne n'en est pas une.

## 2.3 `OFFICE` n'obtient rien, et deux sources concordantes le disent — `ECART-059`

La cellule « Bureau » de la matrice **n'a rien à quoi s'accrocher pour une personne** :

| Mesure | Résultat |
|---|---|
| `grep office_id apps/api/app/*/modeles.py` | **une seule table**, `framework_responsibility_assignment` |
| modèle §8.4 | « `office_id` — obligatoire uniquement pour `OFFICE_MANAGER` » |
| une table d'appartenance à un bureau ? | **aucune.** La seule appartenance modélisée est celle aux **cercles**, §8.2 |
| matrice §6.2 | « un responsable de bureau **n'obtient aucun droit général sur les profils** du seul fait de sa responsabilité de bureau » |

La cellule porte donc sur l'audit du **bureau comme ressource**, qui est du LOT 6. C'est `ECART-059`,
et c'est la forme exacte d'`ECART-031` — une matrice qui décrit une portée que le modèle ne porte
pas. **Rien n'est inventé** : la conclusion vient de deux sources concordantes, et le contrôle
l'éprouve **avec une responsabilité `OFFICE_MANAGER` réelle**, pour que le refus ne puisse pas venir
d'un décor vide.

## 2.4 Deux lignes de la matrice se contredisent, et la plus étroite gagne

Le §5 donne au DSM et au Booster une portée d'audit. Le **§20** réserve « Consulter l'historique des
**rôles** » à l'`ESM`, l'`ADM-E` et le `SUPER`. Le **§23.2** tranche : « une interdiction liée à la
**ressource** prévaut sur le cumul des rôles ».

L'axe des responsabilités vaut donc `null` pour un DSM, et la réponse porte **un axe de plus ou de
moins selon l'appelant**. Arbitrage de Jonathan.

> **Ce n'est pas une fuite**, et le motif est net : un axe absent l'est pour **toutes** les cibles de
> ce rôle, jamais selon la cible. On n'apprend rien de la personne consultée.

## 2.5 `null` n'est pas `[]`, et les deux sont éprouvés dans le même test

| Valeur | Sens |
|---|---|
| `[]` | il n'y a **rien à montrer** |
| `null` | ce n'est **pas dans ton périmètre** |

Les confondre ferait croire à un DSM que son consultant n'a **jamais** porté de responsabilité — une
affirmation **fausse**, et le §7.21 dit qu'un champ qui ment apprend à ne pas le lire. Le décor du
test donne au même profil une responsabilité **réelle** et **aucun** métier : un seul appel suffit
donc à observer les deux formes.

La clé reste **présente** à `null` plutôt qu'absente — même parti que les cinq champs toujours
présents du format d'erreur du §18.3.

## 2.6 Aucune grille d'état, et c'est prouvé par comparaison plutôt qu'affirmé

`T7` exige une appartenance occupante parce qu'on ne modifie pas un archivé ; `T8` exige un état
précis parce que chaque action en dépend. **Lire un historique n'a aucune de ces raisons** — un profil
`departed` ou `archived` a justement l'historique le plus intéressant, et exiger un état occupant le
rendrait inaccessible **au moment où il sert**.

Un test appelle les **deux** résolutions sur la même cible archivée, au même instant, avec le même
rôle le plus large :

```python
assert _acces(cx, entite, acteur, cible, {SUPER}).axes == frozenset(AxeHistorique)
#  Le MEME decor, refuse a l'ecriture — `T7`, et c'est juste.
assert resoudre_le_perimetre(...).champs == frozenset()
```

C'est la seule observation qui distingue « j'ai oublié la grille d'état » de « je ne dois pas en
avoir » — et si un lot ultérieur en ajoutait une ici, ce test tomberait.

## 2.7 « Sans exposer les audits techniques » est STRUCTUREL, pas filtré

**Aucune requête de ce module ne touche une table d'audit.** `auth_event` n'y paraît pas, et le §28
`audit_event` n'existe pas encore — LOT 12. Le §16.2 énumère ce qu'aucun rôle ne peut consulter
depuis l'audit — mots de passe, jetons de session, magic links complets, secrets, CSV complets,
contenu brut des e-mails — et **rien de tout cela ne vit dans les tables lues ici**.

> **On ne filtre pas ce qu'on ne lit pas**, et c'est la forme la plus forte de conformité.

Et les colonnes techniques des tables **lues** — `created_by_person_id`, `updated_by_person_id`,
`assigned_by_person_id`, `version`, `created_at`, `updated_at`, `archived_at` — ne sont **ni
sélectionnées, ni portables** par les structures rendues. **Deux** contrôles le figent, et les deux
sont nécessaires :

| Contrôle | Ce qu'il voit |
|---|---|
| test unitaire | les **champs des dataclasses**. Une structure qui n'a pas le champ ne peut pas le porter, et le perdre exigerait de la réécrire (§7.35) |
| contrôle de stack | les **octets servis par Caddy**. Une structure propre servie par un sérialiseur bavard rendrait quand même les colonnes, et rien d'autre ne le dirait |

Le test unitaire porte son propre témoin : une requête sur `information_schema` **exige que ces sept
colonnes existent** sur les tables lues. Sans lui, l'assertion serait satisfaite par n'importe quoi.

## 2.8 Le nombre de requêtes est borné par les AXES, jamais par les périodes

C'est le **cinquième critère de sortie du lot** — « aucune requête N+1 critique » — et il se
**compte** (§7.0, troisième proposition) :

```text
neuf periodes sur cinq axes   ->  6 requetes   (une par axe, plus la lecture de la personne)
les memes, trois axes permis  ->  4 requetes
```

**Le second compte est le témoin qui rend le premier non trivial** : un service qui émettrait ses
cinq requêtes puis filtrerait rendrait **six** dans les deux cas.

---

# 3. Contrôles exécutés

## 3.1 Les tests

```text
uv run pytest -q --collect-only | tail -1
#  912 tests collected            (+24)
uv run pytest -m integration -q --collect-only | tail -1
#  601/912 tests collected        (+24 — les vingt-quatre sont d'integration)

uv run pytest apps/api/tests/test_historique.py -q
#  24 passed

make check           code=0 — Tous les controles sont passes
make residu-check    code=0 — 26 tables comptees, aucun residu
```

## 3.2 Le contrôle de stack, à travers Caddy en HTTPS

`make profil-check` passe de **36 à 43** contrôles. **Aucune cible nouvelle**, donc rien à ajouter
dans `ci.yml` — troisième sous-étape de suite où le §7.27 paie directement.

```text
ok   LE CRITERE : l'ESM lit les 5 axes — et 1 periode(s) CLOSES y figurent : le PASSE
     est bien rendu, non les seules affectations courantes
ok   AUCUNE des 7 colonnes techniques ne parait dans les octets servis — §16.2
ok   le DSM lit SON consultant, et `responsabilites` vaut `null` — le §20 reserve
     l'historique des roles a l'ESM, l'ADM-E et le SUPER, et le §23.2 fait prevaloir
     la regle la plus etroite
ok   LE REFUS APPARIE : le MEME DSM sur un consultant NON rattache — 404
ok   sans role d'historique : 403 — la ligne « Audit » du §5 met `EMP` et `NEW` a TIRET
ok   sans session : 401 — la matrice §5 refuse `ANON`
ok   l'historique porte ce que l'archivage a CLOS : 1 periode(s) closes avant,
     6 apres, et PLUS AUCUNE ouverte — la restauration ne rouvre rien, et
     l'historique le montre

    controles executes : 43   echecs : 0
```

**Le contrôle 43 croise deux sous-étapes**, et c'est le plus fort du lot : l'archivage de `T8` a clos
cinq relations, la restauration ne les a pas rouvertes, et l'historique **porte ces clôtures-là**.
C'est la preuve qu'il lit l'état **réel** de la base, et non une vue figée au moment du décor.

---

# 4. Défauts trouvés — **trois, tous dans mon propre travail**

## `T9-1` — Une factorisation qui ne factorisait rien, et qui coûtait cinq exemptions

J'avais fait de l'`ORDER BY` un gabarit interpolé, `"ORDER BY {alias}.starts_at DESC, {alias}.id"`.
Ruff a levé **`S608` cinq fois** — interpoler dans une chaîne SQL — et il avait raison.

**Et la factorisation ne factorisait RIEN** : l'alias diffère à chaque requête, donc aucune chaîne
n'était partagée. Cinq `noqa` pour économiser **zéro** duplication auraient été le pire des deux
mondes — un garde-fou qu'on apprend à contourner, §7.25, et exactement le défaut `T7-3` sous une
autre forme. Les requêtes sont donc des **littéraux**, comme celles de `ecriture.py`, et la règle ne
s'y applique plus.

## `T9-2` — J'ai écrit un rôle qui n'existe pas, parce que je lisais la matrice et non l'énumération

`RoleDeLaMatrice.NOUVEL_ARRIVANT` n'existe pas. L'énumération ne porte que les **sept** rôles qu'une
session de **personne** peut porter : `NEW` et `SERVICE` en sont absents par construction — son
docstring le dit — et `ANON` est l'absence de session.

J'écrivais depuis les **huit rôles de la matrice**, qui est la bonne source pour les *droits* et la
mauvaise pour les *identifiants de code*. Attrapé à la collecte des tests, donc sans coût — mais
c'est la même classe que `T8-2` : **les valeurs viennent des énumérations, pas de ma mémoire du
document**.

## `T9-3` — Mes contrôles étaient dans le mauvais ordre, et la mesure l'a dit

J'avais placé les contrôles de `T9` **après** ceux de `T8`, pour profiter des périodes que
l'archivage ferme. Résultat : le DSM du décor rendait **404** sur son propre consultant.

**Et il avait raison.** L'archivage avait clos son `dsm_assignment`, la restauration ne l'a pas
rouvert — décision de `T8` — donc il n'était plus le DSM de personne. **Le contrôle était juste,
l'ordre était faux.** Même famille que `T7-5`, où cinq contrôles rendaient `403` parce que le décor
était incomplet et où la garde avait raison.

Les contrôles de `T9` viennent donc **avant** ceux de `T8`, le décor porte un métier **passé** posé
pour cette sous-étape — sans lui, aucune période close n'existerait à ce moment-là, et « l'historique
rend le PASSÉ » ne serait prouvé par rien — et un **contrôle 43**, après l'archivage, vérifie que les
clôtures apparaissent bien.

## Et une leçon de `T8` qui a servi le lendemain

`T8-3` avait établi que toute substitution doit porter son `assert t.count(a) == 1`. Elle a servi
**trois fois** en `T9` : ruff avait reformaté une condition entre-temps — il inverse les comparaisons
où une constante en capitales est à gauche, `SIM300` — et sans l'assertion, trois corrections auraient
échoué **en silence**, exactement comme `T8-3`.

---

# 5. Écart ouvert

## `ECART-059` — une portée « Bureau » qui n'a rien à quoi s'accrocher

La matrice donne au responsable de bureau la portée « Bureau » sur l'audit, et **aucune table ne
rattache un collaborateur à un bureau**. Même forme qu'`ECART-031`, sur la même table.

**Non bloquant** : le §6.2 tranche dans le même sens — « aucun droit général sur les profils ». `T9`
l'applique, le nomme, et ne comble rien. **À reprendre avec `ECART-031`, avant le LOT 6**, qui est le
lot des bureaux.

---

# 6. Ce que `T9` laisse à la suite, et une conséquence qu'il faut connaître

> **UN DSM PERD L'ACCÈS À L'HISTORIQUE DE SON ANCIEN CONSULTANT DÈS QUE CELUI-CI EST ARCHIVÉ PUIS
> RESTAURÉ SANS RÉAFFECTATION.** Ce n'est pas un défaut : `period @> :instant` le veut, et le §6.2
> aussi — « **ses** consultants » se lit au présent. C'est la mesure qui l'a révélé, en `T9-3`, et
> c'est une conséquence directe du parti de `T8` — la restauration ne rouvre rien. **À annoncer à la
> porte `G5`** : si l'usage montre que c'est gênant, la réponse n'est pas d'élargir le prédicat, mais
> de réaffecter le DSM, ce que le `PATCH` de `T7` permet déjà.

| Point | Où il va |
|---|---|
| **`#123` reste OUVERTE** | `T9` ne livre aucun écran, et `US008` en suppose un |
| **`ECART-059`** | avant le **LOT 6**, avec `ECART-031` — même table, même absence |
| **aucune énumération des archives** | toujours ouvert depuis `T8`. `T9` ne la fournit pas : son historique est celui d'**une** personne, dont l'identifiant vient d'ailleurs. Le back-office du **LOT 9** reste le candidat |
| **`technical_role_assignment`** | hors périmètre, nommé. S'il devait être lisible un jour, ce serait au titre de la **sécurité**, donc au LOT 10 ou 12 |
| **aucune pagination** | à rouvrir le jour où une fiche dense le demandera — pas avant |
| **`exiger_un_scope`** | attend **toujours** son premier consommateur. LOT 9 |
| **`ECART-012`** | attend toujours Léa. Devient visible à `T10` et `T11`, les deux prochaines |

---

# 7. Chiffres, tous dérivés le 12/09/2026

| Grandeur | Valeur | Commande |
|---|---|---|
| Tests | **912** dont **601** d'intégration | `uv run pytest -q --collect-only \| tail -1` |
| Tests nouveaux | **24**, tous d'intégration | `test_historique.py` |
| Vitest | **299**, inchangé | `make test-frontend` |
| Contrôles de `profil-check` | **43** (+7) | sortie du contrôle |
| Endpoints du contrat | **21** (+1) | `jq '.endpoints \| length'` |
| Cibles du `Makefile` | **86**, inchangé | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Migrations | **16**, inchangé — `T9` n'en écrit **aucune** | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Requêtes par historique | **6** pour cinq axes, **4** pour trois | comptées par un écouteur de pilote |

**Aucune migration, et c'est attendu** : `T9` ne fait que **lire** des périodes que le §25.2 historise
depuis le LOT 2. Elle n'ajoute ni table, ni colonne, ni contrainte — et c'est le premier signe qu'un
socle historisé posé tôt paie tard.
