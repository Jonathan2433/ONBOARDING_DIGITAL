# Compte rendu — LOT 3, sous-étape `T9`

**Révocation au départ**
**Story :** `MVP-L03-US006`, issue `#68`
**Réalisée le :** 22 août 2026
**Décision produite :** `DEC-535`
**Écart ouvert :** `ECART-035`
**Migration produite :** **aucune**
**Contrôle de recette rendu acquis :** **`§30.22`**

---

## 1. Trois sources, trois listes différentes — et un objet qui n'existe pas

| Source | Ce qu'elle exige de révoquer |
|---|---|
| cahier **§7.4** | les **sessions** |
| cahier **§6.2** | « l'archivage d'une appartenance **révoque les accès** et **clôture les relations actives** » |
| cahier **§30.22** | « le départ révoque **immédiatement** les sessions **et rôles** » |
| backlog **`US006`** | « sessions, **invitations** et futurs magic links » |
| **`RIGHTS-019`** | « la clôture d'une responsabilité révoque immédiatement les permissions associées » |

**`invitation` n'existe pas.** Mesure : **0** occurrence dans le modèle de données, **0** dans la
matrice. Le cahier ne le nomme que comme objet **audité** (§10.11), opération **idempotente**
(§18.6 — donc `async_job`, LOT 11, `DEC-532`) et tâche planifiée d'**expiration**. Aucun champ,
aucun cycle de vie, aucune table : **il n'y a rien à invalider.**

En inventer une table aurait été §6.5 — et **pire** : elle entrerait en collision avec ce que le
LOT 9 construira réellement, exactement le piège que `DEC-532` a évité en refusant une seconde clé
d'idempotence. C'est `ECART-035`, à reprendre au LOT 9.

---

## 2. La révocation tient au DÉPART, et le §24.1 le tranche

**Le §24.1 n'a AUCUNE transition `Active --> Archived`.** Le départ est `Active --> Departed` ;
l'archivage est `Departed --> Archived`, une étape **ultérieure** que le cahier appelle « archivage
fonctionnel ».

Si la révocation ne tenait qu'à l'archivage — la lettre de `US006` — il existerait une fenêtre
pendant laquelle un collaborateur parti **conserve une session active**. Le §7.4 et le §30.22 écrivent
tous deux **« immédiatement »**, ce qui l'interdit.

**Les deux transitions révoquent donc, et la seconde est idempotente** : elle ne trouve plus rien et
rend zéro. Aucune des trois sources n'est contredite — et un témoin le prouve, parce que sans lui
l'affirmation « la révocation tient au départ » serait une intention, pas un fait.

`Future --> Archived` — « arrivée annulée » — révoque **pour de bon** : aucun départ n'a eu lieu.

**Et une transition absente du §24.1 est refusée.** Sans ce refus, un appelant pourrait archiver
directement et l'état `departed` deviendrait décoratif.

---

## 3. L'ordre est imposé par un déclencheur, et il aurait cassé en production

`fn_dg_implique_dsm_local` se déclenche `BEFORE UPDATE` sur `entity_membership` dès que
`professional_category = 'dg'`, et exige une responsabilité DSM **active** dans la même entité —
**sans regarder l'état**.

Clore la responsabilité **avant** le changement d'état fait donc **échouer le départ d'un DG**, avec
un message parlant de catégorie `dg` et non de révocation. Le changement d'état vient en premier, et
**un test éprouve le départ d'un DG** : sans lui, le défaut n'apparaîtrait qu'au premier départ réel
d'un DG, sur une trace qui ne nomme pas sa cause.

C'est la cinquième idée du socle du LOT 2 — *un déclencheur `BEFORE ROW` peut ombrager ce qui le
suit* — appliquée à un **ordre d'écritures**.

---

## 4. Quatre situations rapportées plutôt que décidées — §7.20

| Situation | Ce qui est fait |
|---|---|
| **rôles globaux** | **conservés et comptés.** Le §8.6 rend `entity_id` nullable pour `SUPER_ADMIN` : quitter une entité ne retire pas un rôle global, et le retirer dépasserait le §30.22 |
| **relations futures** | **conservées et comptées.** `period` est `GENERATED ALWAYS AS tstzrange(starts_at, ends_at)` : poser `ends_at` avant `starts_at` produirait une plage refusée. Ce qu'il faut en faire — annuler, décaler — n'est écrit nulle part |
| **consultants du DSM partant** | **nommés.** La responsabilité du partant EST close, donc `RIGHTS-019` est satisfait et **les permissions sont révoquées** ; le lien `dsm_assignment` est conservé. Désigner le remplaçant est une **décision humaine** — le §30.4 est classé `PARTIEL` précisément parce que cette existence « ne peut pas être acquise en base » |
| **liens déjà consommés** | **non touchés.** `used_at` est une trace, et poser `invalidated_at` par-dessus réécrirait l'histoire |

> **Conséquence à connaître sur les consultants orphelins** : le déclencheur
> `dsm_responsabilite_active` refusera désormais **toute modification** de leurs lignes jusqu'à la
> réaffectation. C'est bruyant, donc diagnosticable — et c'est pourquoi ils sont **nommés** et pas
> seulement comptés.

---

## 5. Une garde retirée plutôt qu'écrite, et le test qui la remplace est plus fort

J'avais codé une défense : ne pas révoquer les sessions si la personne garde une appartenance active
ou future ailleurs. **Cet état est impossible.**

`uq_entity_membership_person_id_occupante` est un index unique **partiel sur `person_id` seul**,
restreint aux états `future` et `active` — §25.1. Une personne qui quitte son appartenance occupante
n'en a donc **aucune autre**.

**La garde était du code mort, et le champ de rapport une fausse promesse** : un champ qui ne peut
jamais être vrai apprend à ne pas le lire — c'est le §7.21 dans un autre costume.

Elle est remplacée par **un test qui prouve l'invariant en base**, et qui exige le **nom** de la
contrainte violée plutôt qu'« une erreur a eu lieu ». Si un lot ultérieur relâchait cet index pour
autoriser l'appartenance multi-entités, ce test échouerait — **et celui qui le relâche saurait qu'il
doit relire cette révocation.**

> **La règle, sans jargon :** n'écris pas une défense contre un état que la base interdit. **Exige
> qu'elle continue de l'interdire.**

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **630 tests, 0 échec** — 613 avant `T9`, dont **377 d'intégration** |
| zéro résidu mesuré | `person` 0, `entity` 0, `user_account` 0, `auth_event` 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make revocation-check`** | **0 — 6 contrôles**, à travers Caddy en HTTPS |
| **`make recette-modele-check`** | **§30.22 passe de `reporté` à `ACQUIS`** — 12 acquis, 1 partiel, 11 reportés, 1 inapplicable |
| `debit` · `csrf` · `sessions` · `admin` · `magic-link` | **12** · **10** · **13** · **10** · **15**, tous à 0 |
| 13 autres contrôles | tous à **0** |

**Ce que `make revocation-check` prouve :**

```text
TEMOIN — la session repond (200) avant le depart
`Active --> Archived` refusee — le §24.1 n'a pas ce raccourci
depart : 1 session revoquee, et l'API rend 401 — MESURE
la responsabilite ESM est close — §30.22, « et roles »
audit — 1 `SESSION_REVOKED` de motif `depart`
TEMOIN — l'archivage ne trouve plus rien : la revocation tient au DEPART
```

**Le 401 est MESURÉ par un aller-retour HTTP réel**, non déduit de l'écriture de `revoked_at` :
l'écriture et le refus sont deux grandeurs différentes tant qu'on n'a pas interrogé l'API. C'est la
quatrième proposition du §7.0 — sans cela, un service qui aurait perdu son filtre
`revoked_at IS NULL` donnerait la même observation.

**Témoin négatif exécuté** : la révocation retirée du service, **7 des 17 tests de
`test_revocation.py` échouent**.

---

## 7. Défauts — six, tous dans mes propres décors, et tous trouvés par la base

| № | Défaut | Ce que la base a dit |
|:--:|---|---|
| `T9-1` | Session ouverte à un instant **futur** dans le test qui passe par la vraie route | `ck_user_session_activite_apres_creation` — la route rafraîchit avec `now()`, antérieur à `created_at` |
| `T9-2` | `assigned_by_person_id` omis | **`NOT NULL`.** Quatrième idée du socle du LOT 2 : le modèle décrit une **action**, et une action a un auteur. Une trace d'audit sans attributeur serait fausse |
| `T9-3` | Colonne `technical_role` inventée | elle s'appelle **`role_type`** |
| `T9-4` | Deux appartenances **actives** dans mon décor | `ex_entity_membership_sans_chevauchement` — `EXCLUDE (person_id WITH =, period WITH &&)`, **sans prédicat partiel** |
| `T9-5` | Puis deux appartenances **non chevauchantes** | `uq_entity_membership_person_id_occupante` — et c'est ce défaut qui a révélé que **ma garde était du code mort**, §5 |
| `T9-6` | `BOOSTER` sans `circle_id` | `ck_..._portee_selon_le_type` — `BOOSTER` exige un cercle, `DSM`/`ESM` exigent l'absence des deux |

**Aucun n'était dans le livrable : les six étaient dans mes décors de test**, et à chaque fois la
base a fait son travail. C'est la forme la plus utile d'échec — mais aussi celle qui dit que **je
n'avais pas mesuré le schéma avant d'écrire le décor**. `T9-4` et `T9-5` ont produit le résultat le
plus précieux de la sous-étape : sans eux, je livrais une garde inutile et un champ de rapport
inatteignable.

---

## 8. Ce qui n'est PAS couvert

- **les invitations** — elles n'existent pas. `ECART-035`, à reprendre au **LOT 9** ;
- **le « retrait d'accès »** du §7.4, seconde cause de révocation. `REVOCATION_RETRAIT_D_ACCES` est
  **nommé sans être employé** : le retrait suppose un écran de gestion des rôles, qui n'existe pas.
  Le nommer sans l'employer vaut mieux que de faire passer un retrait pour un départ ;
- **la réaffectation** des consultants privés de DSM. Rapportée, non décidée — §30.4 est `PARTIEL` ;
- **l'anonymisation** — `Departed --> Anonymized`, §24.1. **LOT 12** ;
- **aucune route HTTP** n'expose le départ : le back-office est le **LOT 9**. Le service est appelé
  par les tests et par le contrôle, et c'est le périmètre de `US006` — « dans la même action
  métier », non « par un écran » ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T10` devra savoir

1. **`T10` est les comptes de service et les scopes**, story `US007`, **`P1`**. Les tables
   `service_account` et `service_token` **existent depuis `T2`** — vérifie leur forme avant d'écrire.
2. **Deux choses ne sont pas tranchées par le corpus**, et le §8 de la fiche les nomme : la **durée
   maximale** d'un jeton de service — le §10.5 dit « configurable **avant** leur création réelle » —
   et la **liste des scopes**, qu'aucun document n'énumère. **Ne les invente pas** ; et `T8` a montré
   l'inverse du piège : **vérifie d'abord que le cahier ne les donne pas**, la fiche s'étant déjà
   trompée une fois dans ce sens exact (`ECART-034`).
3. **La famille de préfixes de jeton est déjà posée** : `oml_`, `oss_`, `ost_` dans
   `packages/observabilite/observabilite/masquage.py`. **`ost_` est celui des jetons de service**, et
   il est déjà couvert par les trois barrières de masquage et par la règle Gitleaks. `T10` n'a rien à
   y ajouter.
4. **`auth_event` n'a que SEPT types**, et aucun ne dit « jeton de service employé ». Le §10.5 exige
   que « chaque appel soit audité » : ne crée pas un huitième type — `T12` auditera exactement les
   sept du §10.6. Instruis ce point plutôt que de trancher seul.
5. **La révocation de `T9` ne touche pas les comptes de service**, et c'est voulu : ils appartiennent
   à une entité, pas à une personne. Si `T10` les lie à une personne, **il devra revenir dans
   `_appliquer`** — le compte rendu le dit ici pour que le lien soit trouvable.
6. **`make revocation-check` ouvre une vraie session par la route de connexion.** Si `T10` change
   quoi que ce soit à cette route, ce contrôle le dira — c'est le §7.21, et il s'est manifesté à
   chaque sous-étape de ce lot.
