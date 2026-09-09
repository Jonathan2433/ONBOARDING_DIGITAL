# Compte rendu — `T5` du LOT 5 : la miniature de photo

**Sous-étape :** `T5` — les miniatures de photo, **et l'autorisation**
**Story :** `MVP-L05-US005`, issue #120
**Date :** 7 septembre 2026
**Décision :** `DEC-564`
**Écart ouvert et clos :** `ECART-052`

> **TOUS LES NOMBRES DE CE DOCUMENT ONT ÉTÉ DÉRIVÉS LE 07/09/2026**, chacun par la commande qui
> l'accompagne. Aucun n'est recopié d'un document antérieur.

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5 — collaborateurs, profils et organisation**, ouvert le 24/08/2026 (`DEC-558`) |
| Découpage | **onze** sous-étapes, et non douze : `T5` et `T6` sont **fusionnées** (`DEC-564`) |
| Faites | `T1` à `T4`, **et `T5`** — il en reste **six** |
| Prochaine | **`T7` — l'écriture dans son périmètre** (`US006`). **Corrigé le 07/09/2026** : j'avais écrit « les écrans de trombinoscope », qui sont `T10` et `T11`. Le libellé est **dérivé de la fiche**, et non de ma mémoire |

**Pourquoi onze et non douze.** La fiche découpait `US005` en `T5` « les miniatures » et `T6`
« l'autorisation ». Les deux moitiés ne tiennent pas debout séparément, et le motif est mesurable :

- on ne peut pas prouver « **sans autorisation, avatar neutre** » sans servir quelque chose ;
- servir une photo sans vérifier l'autorisation enfreindrait le §12.2 ;
- et surtout, **le critère « l'originale n'est jamais servie » serait parfaitement satisfait par une
  route qui ne sert RIEN** — c'est le §7.0, quatrième proposition, et c'est exactement le défaut
  `T2-3`, où **huit refus restaient verts** sur une route qui refusait tout.

Arbitrage de Jonathan du 06/09/2026.

---

# 2. Travail réalisé

## 2.1 La route, et pourquoi elle sert des octets

`GET /api/v1/entities/{code}/people/{appartenance}/photo` sert les **octets** de la variante
`thumbnail`, avec le type MIME dérivé de `variant_format`.

**Le corpus ne dit pas comment un média parvient au navigateur.** Mesure du 06/09/2026 : **zéro**
occurrence d'« URL signée », de « presigned » ou de CDN pour les médias, et le §16.1 dit seulement
« objets MinIO référencés par `object_key`, **jamais Base64** ». Trois options, et une seule
n'invente rien :

| Option | Ce qu'elle exigerait |
|---|---|
| une **URL signée** vers MinIO | exposer le port 9000 au navigateur — contre `DEC-460`, qui publie tout sur `127.0.0.1`, et contre `DEC-470`, qui pose **une** origine sans CORS |
| l'**`object_key` en clair** | exposer la disposition du stockage, et le navigateur n'en pourrait rien faire |
| **les octets par l'API** | une origine, un cookie de session, **aucun réglage nouveau** — et `boto3` est déjà une dépendance |

**Le choix reste réversible** : le jour où le LOT 11 voudra des URL signées, le chemin de la route ne
change pas, seul son corps.

## 2.2 Les quatre conditions, et d'où chacune vient

Une photo n'est servie que si les quatre sont réunies. **Chacune a son test de refus ET son
témoin** — sans quoi une requête qui ne rend jamais rien les satisferait toutes.

| Condition | Sa source | Ce qui la rend nécessaire |
|---|---|---|
| autorisation **ACTIVE** | §12.2 | « une photo ne peut être utilisée publiquement sans autorisation active ». Active = `granted_at` atteint **ET** `withdrawn_at` nul |
| média **`ready`** | §16.1 | « seuls les médias `ready` peuvent être affichés ». Les cinq autres états — dont `rejected` et `quarantined` — ne le sont pas |
| **même entité** | §25.3 | l'actif porte un `entity_id`, et une photo d'une autre entité ne doit pas apparaître ici |
| variante **`thumbnail`** | §16.2, §25.3 | c'est la « miniature trombinoscope », la **seule** que la liste sert |

> **`withdrawn_at IS NULL` NE SUFFIT PAS SEUL, et c'est la condition qui compte.** Une autorisation
> datée du **futur** a elle aussi un retrait nul. C'est la leçon des périodes du §7.38, et c'est le
> seul des cinq refus qu'un `WHERE` trop large laisserait passer — le témoin qui **n'avance que
> l'instant** est ce qui le prouve.

## 2.3 L'originale n'est jamais servie, et c'est **structurel**

`resoudre_la_miniature` ne lit **pas** `media_asset.object_key`. Elle ne le sélectionne pas, donc
elle ne peut pas le rendre par erreur : **le perdre exigerait de réécrire la requête, pas d'oublier
un filtre.** C'est le §7.35 — rendre la propriété structurelle plutôt que de renforcer un contrôle.

Et `MiniatureServie` porte **trois** champs, tous de la variante : aucun ne peut contenir
l'original. Trois contrôles l'attaquent par trois bouts différents :

| Contrôle | Ce qu'il prouve |
|---|---|
| la **structure** ne porte aucun champ d'original | ajouter l'original exigerait de l'écrire, donc de le décider |
| la **requête** ne contient pas `a.object_key`, et contient bien `v.object_key` **deux fois** | un `SELECT` qu'on jetterait ensuite ferait quand même voyager la valeur, et un journal de requêtes lentes la montrerait |
| `make profil-check` compare les **OCTETS** | deux contenus distincts déversés dans MinIO. Un contrôle « 200 et des octets » passerait si la route servait l'originale |

## 2.4 La liste et la fiche : un **chemin**, jamais des octets

Les deux portent un champ `photo` qui vaut le chemin de la route, ou `null`.

**`T4` avait écrit un test qui EXIGEAIT l'absence de ce champ**, pour que son apparition soit une
**décision** et non une dérive (§7.32 : un test est un meilleur véhicule qu'un commentaire). La
décision est prise, et **le test est retourné** : il exige désormais que ce soit un chemin — le
§16.1 interdit Base64 en propre, et un champ qui porterait les octets ferait grossir chaque ligne de
plusieurs dizaines de kilo-octets.

**Une seule source pour les conditions, et une seule pour le chemin.** La liste doit savoir s'il y a
une photo, sans quoi elle émettrait un chemin qui rend 404 ; la route doit lire la variante. Si les
deux portaient leurs propres conditions, elles divergeraient au premier ajout — la liste montrerait
une photo que la route refuse, ou l'inverse.

```text
CONDITIONS_DE_LA_MINIATURE  ->  la liste l'emploie en EXISTS  (aucune multiplication de lignes)
                            ->  la route l'emploie en SELECT  (elle lit la variante)
GABARIT_PHOTO               ->  la route le declare, les DEUX reponses l'emploient
```

**Et la liste ne paie pas une requête par ligne** : l'`EXISTS` est **dans la requête de page**, donc
deux requêtes quel que soit le nombre de lignes — un test les compte. Résoudre la variante ligne par
ligne aurait été le N+1 que le critère de `T3` interdit ; joindre `photo_authorization` aurait
multiplié les lignes, le §12.2 n'imposant **aucune** unicité (mesuré en `T1`).

## 2.5 La borne des 100 Ko, et pourquoi elle ne porte que sur la miniature

Migration `0016` : `ck_media_variant_miniature_sous_cent_ko`.

```sql
CHECK ((variant_type <> 'thumbnail') OR (size_bytes < 100000))
```

**Bornée au SEUL type `thumbnail`, et c'est décisif.** Le §25.3 borne « la miniature
trombinoscope ». La porter sur les **cinq** types casserait le LOT 11, où l'original et la variante
`full_width` pèsent bien davantage — et **rien ne le dirait avant ce lot-là**. Un contrôle le prouve
dans les deux sens : les autres types acceptent 5 000 000 octets.

**100 000 et non 102 400** : c'est la lecture la plus stricte de « Ko », et 102 400 laisserait passer
2,4 Ko de plus que le cahier n'autorise.

**Un test la franchit À L'OCTET** — 99 999 passe, 100 000 est refusé, la contrainte **nommée** dans
le message. Un test à 50 Ko et 200 Ko passerait avec une borne posée **n'importe où** entre les deux :
il mesurerait qu'une borne existe, pas qu'elle est celle du cahier (§7.0, sixième proposition).

Et la valeur est en **une seule source** : le module la déclare, la migration la pose, un test lit la
définition **dans le catalogue** — pas dans le fichier de migration, parce que ce qui compte est ce
que la base applique.

## 2.6 Ce que `T5` ne fait PAS, et c'est écrit dans un test

**Elle ne fabrique aucune miniature.** `MVP-L11-US005` — « Générer miniatures et variantes sans
doublon », dans « Médias, worker et tâches planifiées » — le fait, au LOT 11. Mesure du 06/09/2026 :
**aucune bibliothèque de traitement d'image n'est installée**, zéro occurrence de `pillow` ou `vips`.
Écrire un générateur ici enfreindrait la règle 1 — un lot à la fois.

**Conséquence à connaître, et elle est normale :** dans l'état actuel du projet, **aucun objet de
miniature n'existe dans MinIO**. La route rend donc 404 pour tout le monde, et un test l'exige
explicitement — c'est la sixième cause de 404, celle qui n'est pas en base.

---

# 3. Contrôles exécutés

## 3.1 Les tests

```bash
uv run pytest apps/api/tests/test_photo_de_profil.py -q
#  32 passed
uv run pytest -q --collect-only | tail -1
#  838 tests collected
uv run pytest -m integration -q --collect-only | tail -1
#  530/838 tests collected (308 deselected)
make test-frontend 2>&1 | grep -oE 'Tests  [0-9]+ passed'
#  Tests  81 passed   (contracts)
#  Tests  97 passed   (ui)
#  Tests  121 passed  (web)
```

**32 tests pour `T5`**, dont **6 sans base de données** — la structure, la requête, le gabarit du
chemin, les paramètres partagés, le type MIME d'un format inconnu.

## 3.2 Les sept témoins, chacun exécuté

**Un contrôle qui ne peut pas échouer ne prouve rien.** Chaque filtre a été retiré, un par un, et
les contrôles remis en état après chaque essai.

| Témoin | Défaut injecté | Tests en échec |
|---|---|---|
| 1 | `granted_at <= :instant` retiré (`withdrawn_at IS NULL` seul) | **4** — dont la route de liste |
| 2 | `a.entity_id = em.entity_id` retiré | 1 |
| 3 | `a.state = :etat_media` retiré | 3 |
| 4 | `v.variant_type = :variante` retiré | 3 |
| 5 | le filtre de **population** retiré | 2 |
| 6 | **`a.object_key` sélectionné** au lieu de `v.object_key` | **4**, dont celui qui compare les octets |
| 7 | la borne **déplacée à 200 000 en base**, puis restaurée | 2 |

> **Le témoin 1 attrape le défaut en QUATRE endroits, dont la route de liste** — c'est la preuve que
> les conditions sont bien **partagées** : un filtre corrigé d'un seul côté ne passerait pas.
>
> **Le témoin 7 a été fait en base, pas dans le fichier de migration** : `ALTER TABLE` pour déplacer
> la contrainte, mesure, puis restauration vérifiée par comparaison de `pg_get_constraintdef`.

## 3.3 Le contrôle de stack, à travers Caddy en HTTPS

`make profil-check` passe de **10 à 17 contrôles**. Il est déjà nommé dans `ci.yml` ligne 451.

```text
  Fiche profil complete — US004, cahier §10.2
    info     origine https://app.onboarding.localhost
    info     17 champs attendus, dont 6 sensibles
    ok       decor : un profil COMPLET, un profil EXCLU, + un admin local
    ok       TEMOIN : la connexion reussit et pose un cookie
    ok       la liste rend EXACTEMENT les 2 profils listables — le parti en est absent
    ok       la fiche de l'identifiant rendu par la LISTE est servie
    ok       17 champs servis, ni plus ni moins
    ok       les 6 champs sensibles sont TOUS renseignes — la matrice ne masque aucun champ
    ok       cercle principal et responsabilite BOOSTER portee sur le CERCLE
    ok       le profil EXCLU de la liste rend le MEME 404 qu'un identifiant inconnu
    ok       la meme appartenance est INTROUVABLE sous une autre entite
    ok       sans session : 401 — la matrice §5 refuse `ANON`
    ok       identifiant mal forme refuse, champ nomme, format du §18.3
    ok       MinIO : miniature 100 o, original 4035 o — contenus DISTINCTS
    ok       la LISTE annonce le chemin pour le profil autorise, `null` pour
             l'autorisation RETIREE, et AUCUNE cle d'objet
    ok       la FICHE annonce le MEME chemin que la liste — une source
    ok       les octets servis sont EXACTEMENT ceux de la miniature (100 o < 100000),
             type image/jpeg
    ok       l'original (4035 o) n'est rendu par aucune des 2 tentatives — dont un
             parametre `?variante=original`
    ok       autorisation RETIREE : 404 au format du §18.3
    ok       sans session : 401, et AUCUN octet

    controles executes : 17   echecs : 0
```

**Et son témoin, sur le défaut qui compte le plus** — l'original sélectionné au lieu de la variante :

```text
    ECHEC    photo : 200, 4035 o, debut b'ORIGINAL-QUI-NE-DOIT-JAMAIS-SORTIR-ooooo',
             type 'image/jpeg'
    ECHEC    l'original a fuite par : [...people/.../photo?variante=original]
    controles executes : 17   echecs : 2
```

Le message **nomme les octets servis**. Un contrôle qui dirait « échec » sans les montrer coûterait
un cycle de diagnostic.

**Pourquoi ce harnais et non un second.** La miniature est un **champ** de la fiche et un **champ**
de la liste ; son critère porte sur les deux. Un second vérificateur aurait dupliqué le décor, la
connexion et le ménage — trois sources pour une seule règle (§7.27). Et la borne y est lue **par
`ast`**, sans importer le module : ce script est invoqué par `python3` hors environnement virtuel, et
`app.media.photo` importe SQLAlchemy. C'est le piège mesuré en `T1` du LOT 3, et la même parade.

## 3.4 Aucun résidu, et **un résidu antérieur nommé puis levé**

```bash
make residu-check
#  530 passed, 308 deselected en 4 min 16
#  info     26 tables comptees, 0 ligne(s) avant
#  --> 26 tables comptees, aucun residu, et la suite est verte
```

**La première exécution annonçait « 1 ligne(s) avant ».** Le §7.30 dit de la **nommer avant de la
supprimer**, et c'est ce qui a été fait :

| Fait | Mesure |
|---|---|
| table | `auth_event` |
| contenu | `MAGIC_LINK_REQUESTED`, résultat `adresse_inconnue`, **`person_id` nul** |
| date | **05/09/2026** — donc **antérieure à cette sous-étape**, qui est du 07/09 |

**C'est exactement la classe que le §7.32 nomme** : « la trace d'un refus sans acteur échappe à tout
nettoyage par identité ». Un nettoyage qui supprime par `person_id` ne peut pas la voir. Elle a été
supprimée, et `residu-check` annonce désormais **0**.

## 3.5 La qualité complète

```bash
make check > /tmp/check.log 2>&1
code=$?          # ligne SUIVANTE, aucun tuyau, aucune commande entre les deux
echo "code=$code"
```

**Et cette forme a servi deux fois dans cette sous-étape.** La première exécution est sortie en
**2** ; la notification de tâche annonçait « exit code 0 » — c'était le code de l'**enveloppe**, non
celui de `make`. Mon propre `echo` disait le vrai. C'est la huitième occurrence de la classe §7.3, et
la seule parade est de ne jamais lire un code que l'on n'a pas soi-même relevé sur la ligne suivante.

---

# 4. Les quatre défauts de cette sous-étape

**Trois sur quatre sont dans mes contrôles ou mes commentaires**, et le premier est le plus
instructif parce qu'il portait sur du code que **j'avais écrit le même jour**.

## `T5-1` — J'avais écrit « la cause reste au journal », et rien ne la journalisait

Le corps de la route portait ce commentaire, sur le refus qui suit un échec de lecture MinIO :

> « **LE MÊME REFUS, ET LA CAUSE RESTE AU JOURNAL.** L'exploitant, lui, a le journal corrélé. »

**Mesure du 07/09/2026 sur `app/shared/errors.py` : `gerer_erreur_applicative` ne journalise RIEN.**
Il traduit l'exception en réponse, c'est tout. Mon commentaire décrivait ce qui **devrait** être.

C'est le §7.11 — *vérifie ce que la documentation affirme, même quand c'est toi qui l'écris* — et le
remède n'était pas d'affaiblir le commentaire : **sans journal, une panne de MinIO produirait des
avatars neutres en silence sur tout le trombinoscope**, et rien ne le dirait. La correction est de
rendre l'affirmation vraie, à l'endroit où la cause est connue.

```python
journal.error(
    "miniature illisible dans le stockage : avatar neutre servi",
    extra={"resultat": "echec", "code_erreur": "miniature_illisible",
           "cle_objet": miniature.object_key},
)
```

`resultat: echec` et non `refus` (`DEC-468`) : l'appelant n'a rien fait de mal. **Et un test fige
l'affirmation**, pour qu'elle ne redevienne pas fausse.

## `T5-2` — Un décor ancré sur une date en dur, et deux horloges

`ANCRAGE = 2026-06-15`, et l'autorisation « future » posée à `ANCRAGE + 10 jours`, soit le
**25/06/2026 — déjà passé**.

| Famille de tests | Verdict |
|---|---|
| ceux qui appellent `resoudre_la_miniature` et **injectent** leur instant | **tous verts** |
| celui qui passe par la **route**, laquelle lit l'horloge réelle | **échec** |

**« Instant injecté » et « instant de l'horloge » sont deux grandeurs** — §7.0, sixième proposition,
appliquée non pas à deux nombres mais à deux **sources de temps**. Un décor ancré sur la première ne
prouve rien de la seconde. Et c'est aussi le §7.21 : une date en dur est juste **le jour où on
l'écrit**.

Le décor relève désormais l'heure **du serveur** — `SELECT now()` — et tout y est relatif. Le cas
futur est à `maintenant + 30 jours`, donc futur pour les deux horloges.

## `T5-3` — `caplog` ne voyait rien, parce que l'application remplace les poignées

Mon test de journalisation employait `caplog`. Il ne captait **aucun** enregistrement, et échouait sur
un livrable correct : `creer_application` remplace les poignées de la racine par la sienne.

La convention du projet, posée par `T4` du LOT 1, est de **détourner le flux de la poignée racine**.
Elle est meilleure, et pas seulement plus juste : elle éprouve **en plus** le formateur JSON du §28.1
et les barrières de masquage du §28.2, que `caplog` aurait contournées.

**Et deux erreurs de plus dans ce seul test, toutes deux du §7.11 :**

| Ce que j'affirmais | Ce que la mesure dit |
|---|---|
| `cle_objet` est à la racine de la trace | le formateur émet **dix champs nommés** ; tout `extra=` supplémentaire rejoint un sous-objet **`contexte`**, masqué |
| le champ de corrélation s'appelle `correlation_id` | il s'appelle **`identifiant_correlation`** — les dix champs sont nommés en français |

**Et un troisième, qui a changé le test pour le mieux.** J'exigeais que la trace porte `route`. Elle
vaut `None` : `route` est renseigné par le journal de **requête**, non par un appel émis depuis un
gestionnaire. L'exiger aurait fait échouer un livrable correct (§7.20). Ce qui se prouve — et qui est
ce dont l'exploitant a besoin — est que **les deux traces partagent l'identifiant de corrélation**,
donc que l'échec est rattachable à la requête, laquelle nomme la route.

## `T5-4` — J'ai écrit deux membres d'énumération qui n'existent pas

`TypeVarianteMedia.MOYENNE` et `.GRANDE`, écrits **de mémoire** dans mon décor. Les cinq membres du
§16.2 sont `MINIATURE_TROMBINOSCOPE`, `CARTE`, `PLEINE_LARGEUR`, `APERCU_VIDEO`, `FORMAT_OPTIMISE`.

Corrigé en les **dérivant** :

```python
AUTRES_VARIANTES = tuple(
    m.value for m in TypeVarianteMedia if m is not TypeVarianteMedia.MINIATURE_TROMBINOSCOPE
)
```

§7.27, et le remède est le même que partout : une liste écrite de mémoire est un `ECART-021` en
puissance.

## Un cinquième constat, qui n'est pas un défaut : un import circulaire **utile**

`app/media/photo.py` avait besoin du filtre de population que `app/people/trombinoscope.py`
définissait, lequel avait besoin des conditions de la photo. Python a refusé.

**Le cycle disait la vérité : cette règle n'appartient à aucun des deux.** Elle est **dérivée des
deux énumérations** `EtatAppartenance` et `VisibiliteProfil`, trois modules l'emploient, et sa place
est dans `app/people/modeles.py`, aux côtés d'`ETATS_OCCUPANTS`, qui est de la même nature.

> **Un import circulaire n'est pas toujours un problème d'architecture à contourner** : c'est parfois
> le langage qui nomme une constante mal placée. La parade a été de la déplacer là où elle est
> dérivée, non d'ajouter un import différé.

## Et deux tests antérieurs ont échoué **parce qu'ils devaient**

| Test | Ce qu'il exigeait | Réaction |
|---|---|---|
| `test_l_enveloppe_porte_ses_cinq_champs_et_les_lignes_leurs_sept` | **sept** champs par ligne | attendu porté à **huit** — l'addition est **voulue** |
| onze tests de contrat TypeScript | des fixtures **sans** champ `photo` | fixtures mises à jour, et **cinq tests ajoutés** pour le nouveau champ |

**La bonne réaction était de mettre l'attendu à jour, non d'affaiblir le test** en comparant par
inclusion : c'est précisément « une colonne ajoutée sans être voulue fait échouer » qui rend
l'addition visible en revue.

---

# 5. Le contrat partagé

| Fichier | Ce qui change |
|---|---|
| `contrat-api.json` | l'endpoint **`photoDuProfil`**, `forme: "octets"` — le seul du contrat dans ce cas, et le déclarer évite qu'un client tente d'en lire le JSON. Les entrées de la liste et de la fiche sont **corrigées** : elles annonçaient la photo comme absente |
| `trombinoscope.ts` | `cheminDePhotoOuNul`, et le champ `photo` sur la ligne |
| `profil.ts` | le champ `photo`, validé par **la même fonction** — importée, non recopiée |

**Le validateur refuse une clé d'objet déguisée en chemin**, et c'est le contrôle le plus utile du
lot TypeScript : si l'API rendait un jour l'`object_key`, **tous** les contrôles de type resteraient
verts — c'est une chaîne. Seul le préfixe versionné discrimine. Il refuse aussi une donnée
`data:image/jpeg;base64,…`, que le §16.1 interdit en propre.

**Et un test prouve que les deux validateurs sont la MÊME fonction**, par l'identité du message
d'erreur à l'octet. Comparer leurs verdicts sur un échantillon ne prouverait rien : deux
implémentations distinctes peuvent concorder sur tous les cas essayés.

`packages/contracts` passe de **69 à 81 tests**.

---

# 6. Écart ouvert et clos : `ECART-052`

**Le §8.2 de la fiche annonçait que `T5` devait décider du format des miniatures.** La fiche a raison
sur le constat — le corpus ne nomme **aucun** format, mesuré : zéro occurrence de `webp`, `avif`,
`jpeg` ou `png` dans les cinq documents — et **tort sur qui décide**.

**Le format appartient à celui qui PRODUIT les variantes**, donc à `MVP-L11-US005`, au LOT 11. Une
liste blanche `('webp', 'avif')` écrite ici aurait **fait échouer le LOT 11** le jour où il produit du
`jpeg`, et le message n'aurait pas dit que la cause est une décision prise trop tôt.

> **Cinquième occurrence du §7.29, et elle en affine la parade.** Le §7.29 apprenait : quand un
> document t'annonce une décision à prendre, **cherche-la d'abord dans le cahier**. Ici le cahier ne
> la porte pas, et la fiche a raison là-dessus. Ce qui manquait est l'**autre** question : *à quel
> lot appartient cette décision ?* Elle se répond en cherchant qui **produit** la donnée, jamais qui
> la **consomme** — un consommateur peut toujours lire un format qu'il n'a pas choisi.

**La taille, elle, est bien dans le corpus** : le §25.3 dit « moins de 100 Ko », et elle est posée en
base. `T1` du même lot avait laissé la même note — `FORMATS_VARIANTE` vide, à charge pour `T5` de
« décider et mesurer » — et elle s'est propagée d'une sous-étape à l'autre sans que personne ne
demande de quel lot relève la production.

**Un format inconnu tombe sur `application/octet-stream`** plutôt que de lever : un octet servi vaut
mieux qu'une page cassée, et le LOT 11 n'aura rien à défaire.

---

# 7. Ce que cette sous-étape laisse à la suite

| Point | Ce qu'il faut savoir |
|---|---|
| **aucune miniature n'existe** | `T5` n'en fabrique pas, et rien d'autre non plus : la route rend donc 404 pour tout le monde aujourd'hui. **C'est l'état normal**, et un test l'exige explicitement. Le LOT 11 (`MVP-L11-US005`) produira les variantes |
| **le format des variantes n'est pas tranché** | volontairement, `ECART-052`. Le LOT 11 le choisira, et `_MIMES` de `app/media/photo.py` accueille déjà les formats courants |
| **le retrait de photo n'a aucune ROUTE** | `US005` dit « retrait possible ». La **lecture** honore le retrait — prouvé par deux contrôles — mais **rien ne permet de retirer** : cela suppose un écran et une écriture, donc `T8` (back-office de profil) ou le LOT 9. **À nommer à la porte `G5`** |
| **`exiger_un_role_dans_l_entite` attend TOUJOURS son premier consommateur** | inchangé depuis `T1` : la matrice §5 ne distingue aucun rôle en lecture, et la restriction du §5.1 porte sur l'**écriture**. Donc `T7` ou après |
| **`ECART-049` reste ouvert** | **26** des 85 cibles du `Makefile` ne sont pas dans `.PHONY` — dérivé le 08/09/2026, et ce paragraphe annonçait 25. La correction juste est de **dériver** `.PHONY`, pas de recopier 26 noms |
| **le champ `photo` est un CHEMIN** | les écrans de **`T10` et `T11`** devront le suivre avec le cookie de session, et servir l'avatar neutre du §21.2 sur `null`. **Ne pas essayer de deviner laquelle des cinq causes** : le §21.2 ne veut pas le dire |

---

# 8. Chiffres, tous dérivés le 07/09/2026

| Grandeur | Valeur | Commande |
|---|---|---|
| Tests pytest | **838** | `uv run pytest -q --collect-only \| tail -1` |
| dont d'intégration | **530** | `uv run pytest -m integration -q --collect-only \| tail -1` |
| Tests Vitest | **299** — 81 `contracts`, 97 `ui`, 121 `web` | `make test-frontend 2>&1 \| grep -oE 'Tests  [0-9]+ passed'` |
| Migrations | **16**, tête `0016` | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Tables PostgreSQL | **29** | requête sur `information_schema.tables` |
| Cibles `Makefile` | **85** | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Variables `.env.example` | **84** | `grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example` |
| Défauts nommés au LOT 5 | **32** | `grep -ohE '\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-5.md \| sort -u \| wc -l` |

**Aucune cible nouvelle** : `T5` étend `make profil-check`, elle n'en ajoute pas. Les 85 cibles sont
donc les mêmes qu'à `T4` — et le vérifier valait mieux que de l'affirmer.
