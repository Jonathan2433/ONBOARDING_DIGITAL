# Compte rendu — LOT 5, sous-étape `T2`

**Objet :** le trombinoscope en lecture — route paginée, story `MVP-L05-US001`, issue #116
**Réalisé le :** 26 août 2026
**Décisions :** `DEC-561`
**Écarts :** `ECART-049` ouvert

---

## 1. Qui peut lire : la matrice ne distingue aucun rôle, et je l'avais annoncé de travers

**J'avais écrit à Jonathan, au rapport de `T1`, que « le §5.1 de la matrice s'applique à cette route
comme aux autres » et que `exiger_un_role_dans_l_entite` y trouverait son premier consommateur.
**C'était faux, et la matrice le dit en une ligne.**

Son §5 donne « Trombinoscope » à **`ANON` = tiret** et aux **huit** rôles authentifiés — `EMP`,
`NEW`, `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E`, `SUPER` — tous à **« Lecture »**. Le tableau du
cahier porte la même ligne.

Le §5.1 n'y change rien, et c'est ce que je n'avais pas déroulé : hors de son entité principale, une
personne n'a que `EMP` — **et `EMP` a « Lecture » sur cette ressource**. La restriction du §5.1 porte
sur l'écriture, qui est `T7`.

> **Une session valide suffit donc, et aucun rôle n'est examiné.** Ajouter ici un contrôle de rôle
> exigerait plus que la matrice : c'est le défaut du §7.20, un contrôle qui échoue sur un livrable
> conforme. `exiger_un_role_dans_l_entite` **attend toujours** son premier consommateur, et le dire
> vaut mieux que de laisser croire que `T2` l'a activé.

---

## 2. Ce qui est rendu : quatre états exclus, et les deux filtres sont NÉCESSAIRES

Le **§6.1 de la matrice** distingue deux lignes :

| Action | EMP | NEW | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---|---|---|---|---|---|---|---|
| Consulter un profil **actif** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Consulter un profil **archivé** | — | — | — | Entité | — | — | Entité | Global |

Le trombinoscope est l'annuaire ouvert à tous : il porte la **première** ligne. La consultation d'un
archivé est un acte délibéré — le §6.1 écrit « besoin fonctionnel » — et elle appartient à **`T8`**.
La rendre ici obligerait à inventer un listage privilégié que le corpus ne décrit pas.

**Le modèle déclare pourtant quatre états d'appartenance et trois visibilités** ; le §6.1 n'en nomme
que deux. C'est la classe de `ECART-039` : le critère nomme des exemples, le modèle déclare la
classe.

### Et voici pourquoi il faut les DEUX colonnes, mesuré et non supposé

| Si l'on ne filtrait que… | Ce qui passerait |
|---|---|
| `profile_visibility` | **`_appliquer` de `people/services.py` ne touche PAS `profile_visibility`.** Il pose `membership_state`, `departure_date`, ferme les relations, révoque les sessions — rien d'autre. **Le §22.5 étape 5 « masquage du profil » n'est implémenté nulle part** : zéro occurrence hors des modèles et des fabriques. Un partant reste donc `published`, donc **listé** |
| `membership_state` | un nouvel arrivant a une appartenance `active` dès sa date d'arrivée, et un profil `draft` jusqu'à validation de sa fiche (§10.2). Il serait listé **avant d'exister publiquement** |

Le décor des tests **et** celui du contrôle de stack donnent donc `published` aux lignes `departed`
et `archived` : c'est l'état **réel** de la base après un départ, et c'est ce qui rend l'épreuve
discriminante.

**Un test fige les exclusions pour un appelant `SUPER`** — §7.32. Un lot qui voudrait un listage
privilégié devra casser ce test, donc le décider. Un commentaire ne l'aurait pas obtenu.

---

## 3. Deux décisions que le corpus ne tranchait pas, posées à Jonathan

Aucune n'était dérivable, et les deux changent ce que voit l'utilisateur.

| Question | Arbitrage du 25/08/2026 |
|---|---|
| Le §18.2 dit « options 25, 50 et 100 ; maximum 100 ». L'API accepte-t-elle 37 ? | **Non — liste blanche des trois.** Une API stricte s'assouplit sans rien casser ; l'inverse casse ceux qui s'y étaient fiés |
| Dans quel ordre ? Aucun document ne le dit | **Nom, puis prénom** — l'ordre d'un annuaire |

**L'ordre n'est pas un goût : c'est une nécessité technique.** Une pagination sans ordre **total**
répète des lignes et en saute d'autres. `last_name` et `first_name` ne sont pas uniques ; le tri
porte donc aussi sur la **clé primaire**, ce qui rend l'ordre total, donc reproductible, donc
testable.

**Et le tri est bien français, prouvé par une épreuve discriminante** plutôt que par la lecture du
fichier Compose :

```text
pg_database.datlocprovider = i        (ICU)
pg_database.datlocale      = fr-FR    ← la colonne s'appelle datlocale depuis PostgreSQL 17
                                        daticulocale N'EXISTE PLUS
cote < coté < côte < côté             ← l'ordre FRANÇAIS
```

`datcollate` affiche `en_US.utf8` : c'est le champ libc qu'une base ICU conserve sans l'employer.
**S'y fier aurait fait conclure à une collation anglaise.**

---

## 4. `T2-3` — la route refusait les TROIS tailles valides, et huit contrôles verts ne le voyaient pas

**Le défaut le plus instructif de cette sous-étape, et il n'aurait été vu par aucun test de refus.**

J'avais typé `taille` en `Literal[25, 50, 100]` — le type qui décrit exactement le domaine. Un
paramètre d'URL arrive **toujours en chaîne** :

```text
TypeAdapter(Literal[25, 50, 100]).validate_python("25")   ->  REFUSE
TypeAdapter(IntEnum(...)).validate_python("25")           ->  25
```

La route refusait donc **25, 50 et 100** dès qu'elles étaient écrites dans l'URL, et n'acceptait plus
que le défaut implicite.

**Mes huit épreuves de refus passaient toutes.** Elles demandaient un refus — pour 0, 1, 24, 26, 37,
99, 101, 1000 — et elles l'obtenaient, **pour la mauvaise raison**. Mesuré en réintroduisant le
défaut dans le contrôle de stack :

```text
8 sur 8 des controles de REFUS restaient VERTS
7 echecs, tous dans les temoins et la recomposition
```

> **La leçon, sans jargon :** un type juste dans le **domaine** peut être faux à la **frontière**,
> parce que la frontière transporte des chaînes. C'est le §7.0 sixième proposition — deux grandeurs
> qui semblent la même — appliqué non à deux nombres mais à **deux représentations d'une même
> valeur**. Et c'est la troisième proposition qui l'attrape : seul le témoin qui exige que les trois
> tailles **soient servies** discrimine.

`TailleDePage` est donc un **`IntEnum`**, `TAILLES_DE_PAGE` en est dérivé, et il n'y a **qu'un**
endroit où les trois valeurs sont écrites.

---

## 5. Les cinq autres défauts

| | |
|---|---|
| `T2-1` | **mon attendu d'ordre contredisait mon propre commentaire.** J'avais écrit l'ordre **octet** — « Élodie » après « Zola » — trois lignes sous un commentaire disant qu'« Élodie » doit se classer avec les E. Écrire l'attendu du **mode d'échec** au lieu de celui du succès : aucune relecture ne l'attrape, seule l'exécution le dit |
| `T2-2` | mon test lisait `corps["code"]` là où `construire_corps` **niche** le §18.3 sous `erreur` |
| `T2-4` | **le `# noqa: S608` que j'ai posé sur la ligne d'ouverture d'une chaîne triple s'est retrouvé DANS le SQL.** Il aurait été exécuté par `psql`. Pour une chaîne triple, le marqueur va sur la ligne de **fermeture** |
| `T2-5` | **le témoin central de mon contrôle de stack ne regardait que la PAGE 1.** Le décor trie `zzvisible` en dernier — c'est le point du volume — donc elle est en page 3 sur 3. Mon contrôle **échouait sur un livrable conforme**, en confondant « est rendue » et « est en tête ». §7.20 |
| `T2-6` | **mon nettoyage nommait `entity_role`, une table qui n'existe pas** — elle s'appelle `technical_role_assignment`. Le nettoyage étant **une seule transaction**, l'erreur l'a **annulé entièrement** : rien n'a été supprimé, six décors de 127 lignes se sont accumulés, et **23 tests d'intégration du LOT 2 ont échoué** parce qu'ils comptent `entity_membership` en absolu |

**`T2-6` est la NEUVIÈME occurrence de la classe §7.30**, et le mécanisme est exactement celui que
j'avais écrit dans le docstring de mon propre fichier de tests le jour même. **Un piège documenté
n'est pas un piège désarmé** — et cette fois c'est `make residu-check`, posé en `T12` du LOT 3 pour
cette classe précise, qui l'a nommé en une ligne : « 1542 ligne(s) avant ».

**Et deux règles de la base m'ont été apprises par la base**, ce qui est la bonne façon de les
apprendre :

- `ck_entity_membership_depart_date_si_departed` exige une `departure_date` pour `departed` —
  **et pas pour `archived`**, qu'un décor datant les deux aurait masqué ;
- `ck_technical_role_assignment_portee_selon_le_role` exige `entity_id IS NULL` pour un
  `SUPER_ADMIN` : le super-administrateur est **global**, matrice §5.1, et le lier à une entité
  serait une contradiction que le schéma refuse.

---

## 6. Ce que `T2` ne fait pas, et il faut le dire

Le §10.1 veut un recto « photo et identité » et un verso « informations professionnelles
principales ». Cette route rend l'**identité** et ce que `entity_membership` porte lui-même ; elle ne
joint **ni** le métier, **ni** le statut, **ni** le client, **ni** le DSM, **ni** les cercles.

**Ce n'est pas un oubli :** ce sont exactement les **six axes de filtre** de `T3`, dont le critère de
sortie est « aucun N+1, compté et non supposé ». Les joindre ici ferait le travail de `T3` sans son
contrôle de performance. La photo attend `T5` — ses variantes — et `T6` — son autorisation.

---

## 7. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **761**, dont **465** d'intégration — **32 nouveaux** dans `test_trombinoscope.py` |
| Vitest | **261** — 43 `contracts` (**+26**), 97 `ui`, 121 `web` |
| endpoints du contrat | **14** — `trombinoscopeDeLEntite` est le quatorzième |
| cibles du `Makefile` | **84** — `trombinoscope-check` est nouvelle |
| invocations dans `ci.yml` | **39** — la cible y est **nommée**, `make check` n'étant pas invoqué (§7.36) |
| `make trombinoscope-check` | **0** — **23 contrôles**, 0 échec, à travers Caddy en HTTPS |
| le même, défaut `T2-3` réintroduit | **1** — 7 échecs, et **8 contrôles de refus sur 8 restaient verts** |
| `make check` | **0** |
| `make residu-check` | **0** — 26 tables, aucun résidu |
| `make sources-check` · `sources-temoin` | **0** · **0** |

---

## 8. Ce que `T2` laisse à la suite

- **`T3`** — recherche et filtres. Les **six axes** — entité, cercle, DSM, client, métier et statut —
  demandent les jointures que `T2` n'a pas faites, et son critère est « aucun N+1, **compté** » ;
- **`T5` et `T6`** — la photo. La ligne rendue n'en porte aucune trace aujourd'hui ;
- **`T8`** — l'archivage. C'est lui qui portera « consulter un profil archivé » pour `ESM`, `ADM-E` et
  `SUPER`, et **il devra casser un test de `T2`** pour le faire, ce qui est l'objet de ce test ;
- **`T10`** — l'écran. `cheminTrombinoscope` et `validerLeTrombinoscope` l'attendent, et
  `TAILLES_DE_PAGE` est côté contrat pour que le sélecteur ne propose que des valeurs valides ;
- **le §22.5 étape 5 n'est toujours pas implémenté** — un départ ne masque pas le profil. `T2` s'en
  protège par son second filtre, mais la règle reste à écrire, en `T8` ;
- **`ECART-049`** — 25 des 84 cibles documentées manquent à `.PHONY`. Inoffensif aujourd'hui, latent
  le jour où un fichier portera l'un de ces noms. La correction juste est de **dériver** `.PHONY`,
  pas d'y recopier 25 noms de plus.
