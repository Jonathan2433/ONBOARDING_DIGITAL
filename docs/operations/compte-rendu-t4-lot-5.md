# Compte rendu — LOT 5, sous-étape `T4`

**Objet :** la fiche profil complète et les règles de visibilité — story `MVP-L05-US004`, issue #119
**Réalisé le :** 26 août 2026
**Décisions :** `DEC-563`
**Écarts :** `ECART-051` ouvert et clos

---

## 1. Le critère renvoie à des règles que le corpus ne définit pas

Le critère de `T4` dit « chaque champ visible **ou** masqué selon la matrice, **les deux sens**
testés ». Et `US004` : « Métier, statut, client, DSM, cercles, responsabilités, présentation et fun
fact **respectent les règles de visibilité** ».

**Ces règles n'existent nulle part.** Mesuré :

| Ce que j'ai cherché | Ce que la mesure donne |
|---|---|
| « règles de visibilité » dans tout le corpus | **2 occurrences**, et ce sont les **deux copies du critère de `US004` lui-même** |
| « masquer » dans la matrice | **une phrase**, et elle porte sur les **actions** : « le frontend peut masquer ou afficher les **actions** [...] mais l'API reste l'autorité finale » |
| le §6.1 de la matrice | des **actions** — consulter, créer, modifier, archiver — jamais des champs |
| le §6.2 | uniquement de la **modification** |

Les règles applicables sont donc celles du **§5**, qui traite « Fiches collaborateur », « Statut
mission/intercontrat » et « Client actif » comme **trois ressources distinctes** — et donne
**« Lecture » aux huit** rôles authentifiés sur chacune.

> **Deux erreurs symétriques étaient possibles**, et c'est ce qui rend ce cas instructif. Suivre le
> critère à la lettre aurait fait **inventer** un masquage — quels champs, pour quels rôles ? — ce
> que la règle §6.5 interdit. Mais conclure « rien n'est masqué » **sans le dire** aurait laissé un
> relecteur de la fiche croire que le critère était traité, alors qu'il aura été **écarté**.
>
> La bonne réponse est entre les deux : **nommer l'absence, et figer le choix par un test.**

**Et le corpus définit bien ce qui est masqué — mais ailleurs, et autrement :**

| Ce qui est réellement masqué | Où, et par quelle règle |
|---|---|
| tout, pour `ANON` | matrice §5, porté par `exiger_une_session` |
| les profils `draft`, `hidden`, `departed`, `archived` | la population de `T2`, et pour la même raison |
| **la photo** sans autorisation active | §12.2 — avatar neutre. C'est **`T6`** |

---

## 2. Ce que `T4` livre

`GET /api/v1/entities/{code}/people/{appartenance}` — les champs du §10.2, **moins la photo**.

**Aucun champ n'est masqué**, et le test qui le prouve appelle avec un compte qui n'a **aucune
appartenance dans l'entité, aucune responsabilité, aucun rôle technique** : le cas le plus dépourvu
qu'une session puisse porter. Il voit **tout**. `ECART-051`.

**La population est exactement celle du trombinoscope.** Une fiche accessible alors que la liste
l'exclut rendrait le filtre de la liste **décoratif** — et aucun contrôle de la liste seule ne le
verrait.

---

## 3. La cardinalité est prouvée par le SCHÉMA, pas supposée

Le §10.2 donne treize champs. Cinq relations sont **uniques à un instant donné**, et ce ne sont pas
des suppositions de lecture : des **contraintes d'exclusion** l'imposent.

| Relation | La contrainte qui l'impose |
|---|---|
| métier | `ex_membership_job_assignment_sans_chevauchement` |
| statut **et** client | `ex_professional_status_assignment_sans_chevauchement` |
| DSM | `ex_dsm_assignment_sans_chevauchement` |
| cercle principal | `ex_circle_membership_principal_sans_chevauchement` |

**Les `LEFT JOIN` ne peuvent donc pas multiplier les lignes.** Et un test **exige que ces quatre
contraintes continuent d'exister** : le jour où l'une serait relâchée, la fiche deviendrait fausse
**en silence**, et celui qui la relâche doit l'apprendre par un échec, pas par un commentaire
(§7.32).

**Deux relations sont multiples**, et leurs exclusions le disent aussi : le §8.4 n'exclut le
chevauchement que **par type** pour `DSM`/`ESM`, **par cercle** pour `BOOSTER`, **par bureau** pour
`OFFICE_MANAGER` — une personne peut cumuler. Et `circle_membership` n'unifie que le **principal**.

**Elles ont donc chacune leur requête** : les joindre toutes rendrait le **produit** des deux — trois
cercles secondaires et deux responsabilités feraient six lignes à recomposer en Python. Trois
requêtes constantes coûtent moins, et **se comptent**.

---

## 4. La photo n'est pas dans la fiche, et c'est délibéré

Le §10.2 la nomme **en premier**, et le §12.2 impose un avatar neutre sans autorisation active.
`T5` pose les variantes, `T6` l'autorisation.

> **Un champ `photo` qui vaudrait toujours `null` laisserait croire que la règle du §12.2 est
> appliquée.** C'est le §7.21 sur les avertissements faux, dans un autre costume — et un test exige
> qu'aucun champ de la fiche ne porte « photo » ni « avatar », pour que son apparition soit une
> **décision**.

---

## 5. Ce que le contrôle de stack prouve, et que les tests ne prouvent pas

`make profil-check` ouvre une **vraie session à travers Caddy en HTTPS**, et son épreuve la plus
utile **relie la fiche à la liste** :

1. il appelle le **trombinoscope** et prend l'identifiant qu'il rend ;
2. il vérifie que **la fiche de cet identifiant** est servie ;
3. il prend le profil que la liste **exclut** et exige le **même 404** qu'un identifiant inconnu.

**Éprouvé** : en retirant le filtre de population du service, le contrôle rend « refus divergents :
**200**/404 » — le profil exclu était servi.

---

## 6. Trois défauts, et le premier est celui de `T3` que la CI a révélé

| | |
|---|---|
| **`T4-1`** | **le plafond d'effondrement de `T3` mesurait MA MACHINE.** 3 000 ms passait chez moi, la CI a rendu **3 663, 4 791 et 3 511 ms**. Et c'est la conséquence de ce que `T3` avait déjà prouvé : le planificateur ne voyant pas les lignes non validées, **le plan mesuré n'est pas celui de la production — donc la durée non plus**. Exiger une durée, c'était exiger une grandeur dont on avait déjà établi qu'elle ne mesure pas le critère |
| `T4-2` | ma requête de référence pour la **justesse au volume** n'appliquait que la recherche, alors que le cas comparé portait aussi un filtre de statut : elle rendait 9 là où la route rendait 4. Le contrôle échouait sur un livrable conforme parce que **les deux membres ne mesuraient pas la même chose** |
| `T4-3` | et ce même contrôle annonçait « **5 cas confrontés** » quand il en comparait **deux** — un `continue` bien placé, un compte faux. Le nombre est désormais **confronté à un attendu** (§7.0, troisième proposition) |

**`T4-1` change ce que `T3` prouve, et il faut le dire.** Le test de recherche **n'exige plus aucune
durée**. Il exige la **justesse au volume** — la recherche rend exactement ce qu'une requête SQL
directe rend, grandeur qui ne dépend ni de la machine ni du planificateur — et il **rapporte** le
P95, le maximum, le premier appel à froid, le plan et `Rows Removed by Join Filter`.

> **Le budget du §25.2 se vérifie donc en RECETTE**, sous charge réelle et sur des données
> **validées** — la seule condition où le planificateur voit ce qu'il verra en service. C'est déjà
> ce que `ECART-050` disait ; la CI l'a rendu incontournable.

---

## 7. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **806**, dont **504** d'intégration — **11 nouveaux** dans `test_fiche_profil.py` |
| Vitest | **287** — 69 `contracts` (**+22**), 97 `ui`, 121 `web` |
| endpoints du contrat | **15** — `ficheDuProfil` est le quinzième |
| cibles du `Makefile` | **85** — `profil-check` est nouvelle |
| `make profil-check` | **0** — **10 contrôles**, à travers Caddy en HTTPS |
| le même, filtre de population retiré | **1** — « refus divergents : 200/404 » |
| requêtes par fiche | **3**, comptées, **identiques** pour un profil complet et un profil vide |
| `make check` | **0** |

---

## 8. Ce que `T4` laisse à la suite

- **`T5` et `T6`** — la photo. Aucun champ de la fiche n'en porte trace aujourd'hui, et un test
  l'exige ;
- **`T7`** — l'écriture. La matrice §6.1 y devient exigible : « modifier les données
  organisationnelles » est **refusé à `EMP` et `NEW`**, et `OFFICE` n'obtient **aucun** droit sur les
  profils du seul fait de sa responsabilité de bureau (§6.2). C'est là que
  `exiger_un_role_dans_l_entite` trouvera enfin son premier consommateur ;
- **`T9`** — l'historique organisationnel. `T4` ne rend que l'état **actif** à un instant ; les
  périodes closes sont dans les mêmes tables, et le §24.12 gouverne leur lecture ;
- **`T11`** — l'écran de la fiche. `cheminProfil` et `validerLaFiche` l'attendent, et le validateur
  distingue déjà « champ absent » de « champ nul » — un consultant sans mission n'a pas de client.
