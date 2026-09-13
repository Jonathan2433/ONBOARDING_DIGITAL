# Compte rendu — `T1` du LOT 6 : les trois tables éditoriales

**Sous-étape :** la **première** du lot — `content_page`, `content_block`, `internal_link`
**Date :** 13 septembre 2026
**Décision :** `DEC-578` · **Question ouverte :** `QO-120`
**Stories :** `MVP-L06-US001` à `US007` — **les sept en dépendent**

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T12` |
| Issues | épic `#145`, stories `#146` à `#152`, jalon `G6` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/content/modeles.py` | les trois tables du §15, leurs quatre énumérations |
| `apps/api/alembic/versions/0017_tables_editoriales.py` | la migration, **appliquée et rejouée à vide** |
| `apps/api/tests/test_contenus.py` | **48 tests**, chaque refus apparié à son témoin |

**Le schéma passe de 29 à 32 tables**, et de 16 à 17 migrations, tête `0017`.

## 2.1 Trois décisions de conception, toutes dérivées du corpus

**`content_block` porte un `entity_id` que le §15.2 n'écrit pas.** Le §15.2 énumère
`content_page_id`, `block_type`, `display_order`, des champs structurés et un `payload_json` —
aucun `entity_id`. **Mais le §25.3 est aussi le modèle**, et il prescrit que les tables locales
exposent un couple unique `(id, entity_id)`. Sans lui, la clé vers `content_page` serait **simple**,
et un bloc pourrait pointer la page d'une **autre entité**.

> C'est mot pour mot le raisonnement écrit pour `media_variant` en `T1` du LOT 5, et il était **dans
> le dépôt**, pas dans ma mémoire. §7.24 : deux sections du même document, chacune défendable seule ;
> les confronter donne la réponse.

**Le §15.1 ne reçoit que son IMPLICATION, et c'est la lecture stricte.** Il écrit « `circle_id` |
requis pour une page de cercle » et n'écrit **aucune interdiction ailleurs**. Le §8.4, lui, dit en
toutes lettres que « `BOOSTER` exige `circle_id` et **interdit** `office_id` » — et `T8` du LOT 2 a
posé la contrainte exhaustive. **Les deux sections sont du même document** : là où le modèle veut une
interdiction, il l'écrit.

> « Une permission du modèle n'est pas une interdiction » — §4.14, troisième idée du socle du LOT 2.
> **Un test exige que la permission tienne** : si un lot ultérieur veut interdire, il échouera, et
> celui qui interdit saura qu'il **décide** au lieu de croire appliquer (§7.32).

**`block_type` porte ONZE types, la lecture la plus large de `DEC-577`.** Fusionner détruirait une
distinction que le cahier — document **prévalent** — écrit en deux puces séparées ; séparer n'en
détruit aucune. `QO-119` tranchera, et ce sera une migration d'une ligne.

## 2.2 Deux unicités dérivées, et une borne que `T1` refuse de poser

| Unicité | D'où elle vient |
|---|---|
| slug sur le **triplet** entité / type / slug | §15.1, littéralement : « unique dans l'entité **et** le type ». Partielle sur `archived_at IS NULL`, comme `job_catalog`, `circle` et `office` : une page archivée ne doit pas réserver son slug pour toujours |
| **ordre total** des blocs d'une page | deux blocs de même rang rendraient l'affichage **non déterministe** — le défaut que `T2` du LOT 5 a corrigé sur le trombinoscope. Le §25.1 s'ouvrant par « à prévoir **notamment** », une unicité dérivée d'une règle écrite est ce que `T2` du LOT 3 a fait quatre fois |

**Et la borne que `T1` ne pose pas.** Le §15.3 et le cahier §13 écrivent tous deux « Les URL sont
validées selon une **liste de protocoles autorisés** ». **Mesure du 13/09/2026 : le corpus contient
exactement deux occurrences du mot « protocole », et ce sont ces deux phrases.** La liste n'existe
nulle part. Poser `https` seul serait plausible et non dérivé — §7.0, septième point — et casserait
un lien SharePoint en `ms-`, que le §15.3 nomme pourtant parmi les « autres ressources internes ».

La contrainte borne donc la **forme** — `url` non vide — et **`QO-120`** est ouverte pour `T8`.

## 2.3 La part structurelle de « aucun HTML arbitraire »

Un test exige qu'**aucune des trois tables ne porte de colonne** nommée `html`, `body`, `content`,
`raw` ou `markup`. Le contenu voyage dans un `payload_json`, et c'est `T5` qui le validera **par
type**.

> **Ce test ne prouve pas le critère de sortie n°6, et il ne le prétend pas.** « Aucun contenu
> arbitraire ne peut injecter du code » se satisfait tout seul quand rien n'est rendu : c'est §7.39,
> et le témoin positif — un bloc légitime **servi** — vit en `T5`. Ce que `T1` tient est la moitié
> **structurelle** : il n'y a pas de colonne où mettre du HTML libre.

---

# 3. Contrôles exécutés

```text
make check              code=0    961 pytest (642 d'integration) · 440 Vitest
make icloud-verify      code=0
make docs-check         code=0
make migrate            code=0    32 tables
make migrations-check   code=0    ← la chaine REJOUEE sur une base VIDE, schema compare
make alembic-check      code=0    une seule tete : 0017
make isolation-check · isolation-temoin · historisation-check              code=0
make recette-modele-check · code-refresh · code-check                      code=0
```

---

# 4. Défauts trouvés — **deux**, et le premier n'est pas de moi

## `T1-1` — `alembic --autogenerate` a proposé de SUPPRIMER l'index de recherche du LOT 5

La migration engendrée portait, dans le même `upgrade()` que les trois tables :

```python
op.drop_index(op.f('ix_person_recherche_nom'), table_name='person')
```

**C'est l'index de la recherche du trombinoscope**, posé en SQL brut par la migration `0015`. C'est
un index **sur expression** — `fn_normaliser_pour_recherche((first_name || ' ') || last_name)` — et
autogenerate ne sait pas les réconcilier : il le voit en base, absent des métadonnées, et conclut
qu'il faut le détruire.

**Le livrer aurait supprimé la recherche du LOT 5 en silence**, dans une migration dont le titre ne
parle que de contenus éditoriaux. C'est le §7.24 : un outil qui réussit ne prouve rien, seul le
**résultat** discrimine.

**Et la mesure dit que le piège était debout pour tout le monde :**

| Question | Mesure du 13/09/2026 |
|---|---|
| l'index est-il déclaré dans un module de `app/` ? | **non**, zéro occurrence |
| un test exige-t-il son existence ? | **non**, zéro occurrence |
| autogenerate le proposera-t-il encore ? | **oui, à chaque fois** |

**La seule part de la correction qui vaille est le test.** Retirer le `drop` corrige une instance ;
`test_l_index_de_recherche_du_LOT_5_EXISTE_TOUJOURS` **nommera l'index** le jour où quelqu'un le fera
disparaître. §7.32, et §7.31 : un garde-fou peut être exact pour un mode de défaillance et aveugle à
un autre — ici, aucun garde-fou ne regardait celui-là.

> **Et j'ai prouvé l'absence par l'AST, pas par un `grep`.** Le nom de l'index figure **une** fois
> dans la migration, dans la docstring qui explique pourquoi il a été retiré. Un `grep -c` rend 1 et
> ne discrimine pas ; `ast.parse` dit **zéro appel exécutable**. §7.0, quatrième proposition : un
> contrôle dont l'échec produirait la même observation que le succès ne prouve rien.

## `T1-2` — `inconsistent types deduced for parameter $1`, la quatrième fois de ce projet

Mes helpers de test employaient `:c` pour `entity.code` — `character varying(64)` — **et** pour
`display_name` et `city`, qui sont `text`. **39 tests sur 46 ont échoué**, et le message ne nomme ni
la table ni la colonne.

C'est **le piège du §7.25**, dont l'exemple mesuré est **littéralement ces trois colonnes**, et qui s'est déjà rejoué trois fois — `T4-2`, `T8-3`, puis six
fabriques d'un coup au LOT 2. Je l'ai rejoué **dans le fichier où je citais la leçon**.

Corrigé sur les quatre helpers : **un paramètre par colonne**, jamais un paramètre partagé.

> **J'AI D'ABORD ÉCRIT QUE « LE GARDE-FOU EXISTE ET S'EST TU ». C'EST FAUX, ET JE NE L'AVAIS PAS
> MESURÉ.** Cherché par son nom, par son motif et dans le `Makefile` : **aucun garde-fou de cette
> nature n'existe dans ce dépôt.** Le §7.25 documente **deux tentatives qui ont échoué** — l'une se
> déclenchait sur le commentaire expliquant le motif qu'elle interdit, l'autre sur une réutilisation
> légitime entre deux colonnes `uuid` — et conclut que le discriminant est le **type de colonne**.
> **Il ne dit nulle part qu'une troisième version a été livrée.**
>
> C'est le §9.0 retourné contre moi : *vérifie ce que la documentation affirme* — y compris quand
> c'est toi qui la lis vite.
>
> **ET LE CONSTAT EST PLUS DUR QUE MON ERREUR.** L'exemple que le §7.25 **mesure**, en toutes
> lettres, est : « `entity.code` est `character varying(64)` quand `display_name` et `city` sont
> `text` — d'où l'échec ». **Ce sont exactement les trois colonnes sur lesquelles je suis tombé.**
> La leçon nommait le cas, personne ne l'a outillé, et il s'est rejoué **une quatrième fois** —
> `T4-2`, `T8-3`, les six fabriques du LOT 2, puis celle-ci.
>
> **Le §7.30 dit quoi faire quand une classe résiste : changer d'outil, pas promettre d'attention.**
> La recommandation est au §5, et elle n'est pas une promesse : elle décrit le contrôle exact que le
> §7.25 spécifie déjà — lire le catalogue, pas le texte.

## Ce qu'un garde-fou a exigé, et qui n'est pas un défaut

`test_les_cles_composites_sont_toutes_couvertes` a **échoué**, et il a eu raison : j'avais posé
**trois** chemins composites et n'en éprouvais que **deux**. Le troisième — `content_page` vers
`office` — a été écrit à cause de lui. Le compte passe de **9 à 12**, et il est écrit en dur
**délibérément** : sa mise à jour est ce qui force la décision.

C'est la même classe que `TABLES_DECLAREES`, qui a elle aussi échoué en **nommant** les trois tables
nouvelles. **Deux garde-fous qui doivent échouer, et qui ont échoué exactement quand il fallait.**

---

# 5. Ce que `T1` laisse

| Point | Où il va |
|---|---|
| **`QO-120`** — la liste des protocoles d'URL | Jonathan et Léa. **Avant `T8`**, qui écrit les liens internes |
| **`QO-119`** — le vocabulaire des blocs | Léa. **Avant `T11`**. `T1` pose **onze** types, la lecture la plus large |
| **Le garde-fou du paramètre lié N'EXISTE PAS** | **Recommandation, pas promesse.** Le §7.25 spécifie déjà le contrôle exact : relever chaque paramètre lié partagé par plusieurs colonnes dans une requête, résoudre chaque colonne, **lire son type au catalogue**, et refuser quand les types diffèrent. Il ne se déclenche donc ni sur un commentaire, ni sur `:p` réutilisé entre deux `uuid`. **C'est un contrôle transverse, pas un morceau de `T1`** : il mérite sa propre sous-étape et la décision de Jonathan. La classe a résisté **quatre** fois |
| **Le rendu des blocs et le refus de l'injection** | `T5`. `T1` tient la moitié **structurelle** : aucune colonne ne peut porter du HTML libre |
| **Le déclencheur « un à trois responsables actifs »** | `T4`. C'est un **comptage borné**, qu'aucune contrainte de ligne n'exprime, et `DEC-576` dit à partir de quand il mord |
