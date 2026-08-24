# Compte rendu — LOT 5, sous-étape `T1`

**Deux sections du modèle qu'il fallait confronter, et deux garde-fous du LOT 2 qui ont servi**
**Story :** — · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-559` · **Écart consigné :** aucun — `ECART-047` est **traité**
**Migration produite :** **`0014`**

---

## 1. Deux sections du même document, et il fallait les confronter

Le **§16.2** décrit `media_variant` en prose : « chaque variante porte : dimensions ; format ;
taille ; checksum ; `object_key` propre ». **Aucun `entity_id`.**

Le **§25.3**, lui, prescrit : « pour empêcher les références inter-entités accidentelles, les tables
**locales** exposent un couple unique `(id, entity_id)` ». Et une variante appartient à un
`media_asset`, qui appartient à une entité : elle est **locale en substance**.

**Sans cette colonne, la clé étrangère vers `media_asset` serait simple**, et une variante pourrait
pointer l'actif d'une **autre** entité — exactement ce que le §25.3 existe pour empêcher.

> **C'est le §7.24 :** deux sections, chacune défendable seule. Lire la seule §16.2 aurait produit une
> table sans garde-fou d'isolation, et rien ne l'aurait signalé — `isolation-check` ne vérifie que les
> tables qui **ont** un `entity_id`.

`make isolation-check` compte désormais **neuf** clés composites, et `test_isolation.py` exige un
**test de refus par clé** — un garde-fou du LOT 2 dont le docstring dit : « une neuvième clé composite
fera échouer ce test ». Il l'a fait.

**Et `photo_authorization` reste globale**, sans `entity_id`. Elle lie une personne — table
**globale** — à un actif. Lui en donner un ferait de l'autorisation une donnée d'entité, ce que le
§12.2 n'écrit pas et que le sens contredit : c'est la personne qui autorise sa photo. La dérivation
d'`isolation-check` la classe globale, en lisant les sections du modèle.

---

## 2. Ce que le §25.4 range hors de la base, et qui n'y est pas mis

Le §25.4 énumère les règles « nécessitant service ou trigger contrôlé », et **« la publication d'une
photo uniquement avec autorisation active » en fait partie**.

Son absence de la migration n'est donc **pas un oubli** : c'est ce que le modèle prescrit. Elle
appartient à `T6`, et `make recette-modele-check` garde le §30.12 en **`REPORTE`** jusque-là — le
passer `ACQUIS` maintenant nommerait un test qui n'existe pas, ce que le contrôle refuse.

**Trois autres règles du §16.1 sont dans le même cas**, et pour la raison exacte du LOT 2 — le modèle
décrit une **action**, seule l'**implication** est applicable en base :

| Règle du §16.1 | Où elle vit |
|---|---|
| « aucun `object_key` fourni par le client » | le contrat de la **route** — la base ne sait pas qui a proposé la valeur |
| « seuls les médias `ready` peuvent être affichés » | la **lecture** |
| « vérification du contenu réel obligatoire » | le **worker**, qui compare `mime_declared` à `mime_detected` |

---

## 3. Une ambiguïté mesurée : « photo 10 Mo » contre « image 20 Mo »

Le §16.1 pose quatre bornes : « photo 10 Mo maximum ; image 20 Mo maximum ; vidéo 1 Go et 20 minutes
maximum ».

**Or une photo EST une image.** La distinction n'est pas un `media_type` — il n'en existe que trois,
`image`, `video`, `document` — mais un **usage**, et c'est `media_usage` qui le porterait avec son
`usage_type = 'PROFILE_PHOTO'`. Cette table est **reportée** (`DEC-558`).

**La base n'exprime donc que ce qu'elle connaît** : 20 Mo pour une image, 1 Go et 20 minutes pour une
vidéo. **La borne de 10 Mo propre à la photo de profil appartient au service, en `T5`**, et elle est
nommée dans le module, dans la migration et ici — pour qu'on ne la croie pas acquise.

---

## 4. Deux garde-fous du LOT 2 ont fait leur travail

### `T1-1` — `noms_de_contraintes_trop_longs` : un nom de 66 caractères

La convention de nommage du socle ajoute `ck_<table>_`. Mes noms le portaient **aussi**, d'où :

```text
ck_photo_authorization_ck_photo_authorization_retrait_apres_octroi   (66)
```

**PostgreSQL tronque à 63, en silence.** Deux contraintes auraient pu se retrouver avec le même nom
tronqué, et le message d'erreur aurait nommé une contrainte qui n'est pas celle qu'on croit.

> Un garde-fou écrit en `T1` du **LOT 2**, treize mois plus tôt, qui attrape la faute d'aujourd'hui.
> C'est exactement ce que le §7.0 troisième proposition cherche à obtenir.

### `TABLES_DECLAREES` — trois tables nouvelles

Elle a échoué en nommant `media_asset`, `media_variant` et `photo_authorization`. **C'est sa
fonction**, et son commentaire le dit : « son objet est d'exiger qu'une table **nouvelle** soit
inscrite ici, donc **décidée** ». Étendue délibérément, dans la même pull request que la migration.

---

## 5. Une unicité dérivée, une non-unicité figée, et une absence assumée

| Table | Ce qui est posé | D'où cela vient |
|---|---|---|
| `media_variant` | **une variante par type et par actif** | **dérivé** du §16.2 : sa liste s'intitule « Versions générées » et en donne **cinq**, nommées. Deux miniatures du même actif seraient deux réponses à une même question |
| `media_asset` | **aucune** unicité sur `(entity_id, checksum_sha256)` | le §25.1 écrit **`INDEX`** là où il écrit `UNIQUE` **treize fois** dans la même liste. Un test **fige la non-unicité** |
| `photo_authorization` | **aucune** unicité | « au plus une autorisation active par personne » n'est écrit **ni** au §12.2, **ni** au §25.1, **ni** au §25.4 |

**L'absence sur `photo_authorization` est figée par un test**, et c'est le point : `T6` devra dire ce
que le service fait de deux autorisations actives, et **ouvrir une question** si le corpus reste muet.
Sans ce test, l'absence serait indistinguable d'un oubli.

---

## 6. Le déclencheur, et son témoin

Le §24.3 donne la machine à états, et **`Deleted --> [*]`** : aucune transition n'en sort. Même motif
que `person.account_state = 'anonymized'` au LOT 2 — ce que la suppression a effacé n'est plus là pour
être restauré.

**Un `CHECK` ne peut pas l'exprimer** : il ne voit pas l'ancienne valeur. D'où le déclencheur,
`BEFORE UPDATE OF state`, qui ne se réveille que si l'état figure parmi les colonnes affectées.

> **Et le témoin exige que les AUTRES transitions restent permises.** Sans lui, un déclencheur qui
> refuserait tout changement d'état passerait le test du refus — l'échec produirait la même
> observation que le succès (§7.0). Le témoin parcourt `Ready → Archived → Ready → Deleted`, les trois
> écrites au §24.3.

---

## 7. `T1-2` — un défaut de mon propre test

`test_une_variante_ne_peut_pas_pointer_l_actif_d_une_AUTRE_entite` employait **le même type de
variante** des deux côtés. C'est `uq_media_variant_asset_type_non_archive` qui se déclenchait, **pas
la clé composite** : l'unicité ne porte pas `entity_id`, donc elle voit le doublon d'abord.

Le test échouait **en nommant la mauvaise contrainte**. §7.25, seconde leçon : « un témoin qui
n'exerce pas un contrôle ne prouve rien de ce contrôle ». Même situation qu'au LOT 2, où deux
contraintes se partagent une règle et où la première masque la seconde.

Corrigé en donnant un **type différent** à la tentative inter-entités, ce qui laisse la clé composite
parler.

---

## 7 bis. `T1-3` et `T1-4` — deux garde-fous de ce dépôt étaient AVEUGLES

Les deux ont été trouvés **après** que `make check` soit sorti en 0, et le premier est le défaut le
plus instructif de cette sous-étape : **aucune des sept propositions du §7.0 ne pouvait l'attraper.**

### `T1-3` — `make check` était vert, et `git add -A` n'a pas ajouté le module

```text
$ git commit …          # puis, dans git status --short :
M  apps/api/app/modeles.py          <- present
A  apps/api/tests/test_medias.py    <- present
                                    <- apps/api/app/media/ ABSENT
$ git check-ignore -v apps/api/app/media/modeles.py
.gitignore:60:media/    apps/api/app/media/modeles.py
```

`media/`, **sans barre oblique de tête**, vaut **à toute profondeur**. Le motif a été écrit au LOT 0
contre les **médias déposés** localement ; il attrapait un **module source** du même nom. La
migration et les vingt tests seraient partis **sans le module qu'ils exercent**.

**C'est la deuxième occurrence de la classe §7.34.** `* [0-9]` avait été écrit contre une copie de
**répertoire** et ne couvrait pas les **fichiers** ; `media/` a été écrit contre un répertoire de
**données** et ne prévoyait pas les **modules**. Les deux sont restés justes pour leur cas pendant
plus d'un an.

> **La leçon, et elle est nouvelle** : tous mes contrôles lisent le **disque**, git lit son
> **index**. Deux grandeurs différentes — le §7.0 sixième proposition appliquée non pas à deux
> nombres mais à deux **sources**. Un `make check` vert ne dit rien de ce qui sera commité.

**Mesuré avant de corriger** : des vingt-sept motifs de répertoire non ancrés, **huit** nomment un
répertoire de **données locales** et pourraient nommer un module — `secrets/`, `uploads/`, `media/`,
`data/`, `volumes/`, `backups/`, `restic-repo/`, `logs/`. Aucun des huit n'existe ailleurs qu'à la
racine dans ce dépôt : **les ancrer ne coûte rien**. Les motifs de vrais artefacts produits à toute
profondeur restent non ancrés, parce que c'est leur intention.

**Et la seule part qui vaille est le contrôle.** `make sources-check` balaye le disque et exige que
`git check-ignore` ne refuse **aucun** fichier source, la liste **dérivée du disque** à chaque
exécution. Il est dans **`make check`** *et* **nommé explicitement dans `ci.yml`** : le moment où il
faut le savoir est la **pull request**, pas le début de session. Voir `T1-5` — le « donc dans la
CI » que j'avais d'abord écrit était faux.

| Épreuve | Résultat |
|---|---|
| sur l'arbre corrigé | **0** — 338 fichiers examinés, 2 exceptions déclarées |
| **sur le défaut qui l'a fait naître**, `.gitignore` remis à `media/` | **1**, et il nomme les deux fichiers avec `.gitignore:60` |
| `make sources-temoin`, dans les deux sens | **0** — sans témoin il passe ; avec un vrai fichier source à un vrai chemin ignoré il échoue **en le nommant**, et n'en voit **qu'un** |

Le résiduel est **nommé dans la sortie** et non tu : `dist` et `build` sont des noms qu'un module
pourrait porter, et un module ainsi nommé échapperait au contrôle. Les deux exceptions, `AGENTS.md`
et `docs/prototype/V1.html`, sont déclarées **avec leur motif**, et le contrôle **échoue aussi si
l'une cesse d'être ignorée** — une exception morte avalerait la réapparition du cas (§7.22).

### `T1-4` — le contrôle des marqueurs d'identifiant lisait le premier et ignorait les autres

`marqueur_declare` faisait un `re.search`. Le registre des écarts portait **deux** marqueurs :

| Ligne | Valeur |
|---|---|
| 114 | `ECART-048` — juste, et la seule que le contrôle lisait |
| **704**, la toute fin du fichier | **`ECART-045`** — **trois de retard** |

Et la fin du fichier est l'endroit que déroule naturellement qui cherche le prochain numéro. **C'est
le dommage exact de `ECART-021`, dans le garde-fou écrit pour `ECART-021`** — §7.31, un garde-fou
exact pour un mode de défaillance et aveugle à un autre.

**Mesuré sur les six registres** avant correction : cinq en portaient **un**, celui-ci en portait
**deux**. Le contrôle exige désormais **un seul** marqueur, et non pas seulement leur accord : deux
marqueurs qui concordent aujourd'hui divergent le jour où une sous-étape n'en met qu'un à jour, ce
qui est précisément ce qui s'est produit. Il nomme chaque ligne — éprouvé, il rend
« 2 marqueurs au lieu d'un seul (ligne 114 -> ECART-048 ; ligne 704 -> ECART-045) ».

### `T1-5` — « donc dans la CI » était faux, et c'est moi qui venais de l'écrire

J'ai écrit, au commit, à la pull request, au registre et dans `CLAUDE.md` : « il est dans
`make check`, **donc dans la CI** ». Puis j'ai voulu le vérifier.

```text
$ grep -oE 'make [a-z][a-z0-9-]*' .github/workflows/ci.yml | sort -u | grep check
make check          <-- mais c'etait un COMMENTAIRE
```

**`ci.yml` n'invoque pas `make check`.** Il appelle les cibles **une par une** — trente-six
invocations réelles avant cette sous-étape. Ma première mesure avait matché le texte `make check`
dans un **commentaire** du workflow, et j'en avais tiré une conclusion inverse de la vérité.

| Ce que j'ai mesuré d'abord | Ce que dit la mesure juste |
|---|---|
| `grep` sur tout le fichier | matche les **commentaires** |
| « `make check` apparaît, donc il est invoqué » | **36 invocations**, aucune n'est `check` |

> **C'est le §7.28 — lis ce que la cible fait, pas ce que son nom suggère — et le §7.11 : vérifie ce
> que la documentation affirme, y compris quand c'est toi qui viens de l'écrire.** Et c'est aussi le
> §7.6 dans un autre costume : un `grep` qui ne distingue pas le code du commentaire est un contrôle
> dont on interprète le silence.

**Corrigé dans le sens qui rend l'affirmation vraie** : `make sources-check` et
`make sources-temoin` sont **nommées dans `ci.yml`**, dans la tâche qualité — elles n'exigent ni
démon Docker ni base, seulement `git` et `python3`. Elles restent aussi dans `make check`, pour le
local. **Mesure après correction : 38 invocations, `sources-check` et `sources-temoin` présentes.**

**Et une conséquence à retenir pour toute la suite du projet, écrite dans le `Makefile` lui-même :
une cible ajoutée à `make check` n'entre PAS dans l'intégration continue.** Il faut l'ajouter à
`ci.yml`.

---

## 8. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| tables du schéma | **29** — 26 + 3 |
| déclencheurs | **9** — 8 + 1 |
| migration | **`0014`**, tête. `downgrade base` ne laisse **aucune** table métier |
| pytest | **729**, dont **438** d'intégration — 20 nouveaux dans `test_medias.py` |
| clés composites | **9**, chacune avec son test de refus |
| `isolation-check` · `isolation-temoin` | **0** · **0** |
| `historisation-check` · `secrets-check` · `privileges-check` | **0** · **0** · **0** |
| `migrations-check` | **0** — la chaîne rejouée sur base **vide** rend une signature **identique** |
| `recette-modele-check` | **0** — §30.12 reclassé, 12 acquis · 1 partiel · 11 reportés · 1 inapplicable |
| `residu-check` | **0** — 26 tables comptées, **0 ligne avant** |
| `sources-check` · `sources-temoin` | **0** · **0** — 338 fichiers source examinés, **1** sur le défaut d'origine. **Nommées dans `ci.yml`**, tâche qualité |
| `docs-check` | **0** — 143 décisions, 48 écarts, **6** séquences, marqueur unique par registre |
| `make check` | **0** — 729 pytest, 235 Vitest, et les deux cibles nouvelles dedans |

**`residu-check` compte 26 quand le catalogue en porte 29, et c'est correct** : `TABLES_HORS_COMPTE`
exclut `alembic_version`, `platform_setting` et `allowed_email_domain`, chacune avec son motif écrit
dans le script. J'ai vérifié avant de conclure à un défaut.

---

## 9. Ce que `T1` laisse à la suite

- **`T2`** — le trombinoscope paginé. Le §18.2 donne les trois tailles et le **maximum de 100** : le
  contrôle devra exiger le refus **au-delà**, pas seulement l'acceptation des trois ;
- **`T5`** — les miniatures. Deux choses l'attendent : la **borne de 10 Mo** propre à la photo de
  profil, que la base ne peut pas porter, et le **format** des variantes, que le corpus ne donne pas
  — mesuré, **zéro** occurrence de `webp` ou `avif`. Le §8.2 de la fiche le nomme, et `DEC-491` donne
  la méthode : **mesurer** le motif de chaque valeur ;
- **`T6`** — l'autorisation. C'est elle qui portera la règle du §25.4, et qui devra trancher sur deux
  autorisations actives ou ouvrir une question. **Et c'est elle qui fera passer le §30.12 en
  `ACQUIS`**, avec un test nommé ;
- **`media_usage` reste reportée**, et un test l'exige : sa création devra être une **décision**.
