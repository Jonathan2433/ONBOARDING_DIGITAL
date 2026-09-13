# Compte rendu — `T8` du LOT 5 : archivage et restauration

**Story :** `MVP-L05-US007` — *Archiver et restaurer un profil*, `P0`, taille **L**, issue `#122`
**Décision :** `DEC-569`
**Écart ouvert et clos :** `ECART-058`
**Date :** 10 septembre 2026

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026 (`DEC-558`), **onze** sous-étapes depuis `DEC-564` |
| Faites | `T1` à `T5`, `T7`, et **`T8`** |
| Prochaine | **`T9` — l'historique organisationnel** (`US008`, issue `#123`) |
| Périmètre de `T8` | **les trois lignes d'archivage du §6.1** : archiver un profil, réactiver un profil archivé, consulter un profil archivé. Arbitrages de Jonathan du 10/09/2026 |
| Hors périmètre, **nommé** | le retrait d'autorisation photo — la fiche du lot le laissait à « `T8` ou le LOT 9 », arbitrage : **pas ici**, il a sa propre grille de rôles (« soi sur demande », « support ») et n'est pas un archivage. **Et aucune ÉNUMÉRATION des archives**, le corpus n'en décrivant aucune |
| Issue `#122` | **reste ouverte** : `T8` ne livre aucun écran, et `US007` en suppose un |

---

# 2. Ce que la sous-étape a produit

## 2.1 La moitié « révoque et clôture » existait déjà, et il ne fallait pas la réécrire

**Mesure d'abord.** `apps/api/app/people/services.py` — **LOT 3, `T9`, story `MVP-L03-US006`** —
porte `enregistrer_un_depart` et `archiver_une_appartenance` depuis le mois d'août : révocation des
sessions, invalidation des liens actifs, clôture des **six** relations historisées du §25.2, et
quatre situations rapportées plutôt que décidées. `make recette-modele-check` classe le **§30.22
`ACQUIS`** depuis lors, et le §30.11 — « un profil archivé ne reçoit plus de magic link » — l'est
depuis `T3` du LOT 3.

**Ce qui manquait, mesuré le 10/09/2026 :**

| Manque | Mesure |
|---|---|
| la **quatrième** transition du §24.1 | `grep -rniE 'reactiv\|restaur'` sur `apps/api/app/` : **zéro** implémentation. `TRANSITIONS_AUTORISEES` portait **trois** des quatre |
| **aucune route** | 20 routes dans le projet, **une seule** écriture métier — le `PATCH` de `T7`. Le service du LOT 3 n'était appelé que par ses tests et son vérificateur |
| la grille de rôles | `ROLES_D_ECRITURE` compte **cinq** rôles ; les trois lignes du §6.1 n'en donnent que **trois** |

Ce module n'en refait donc rien. Il ajoute ces trois choses, la concurrence optimiste, et la
traduction des refus — rien d'autre.

## 2.2 Le §6.1 porte DEUX grilles, et réutiliser la première aurait élargi un droit

Ses trois lignes d'archivage mettent **`DSM` et `BOOST` à TIRET**, alors que les deux portent un
droit de modification et figurent dans `ROLES_D_ECRITURE` :

```text
| Action                      | EMP | NEW | DSM | ESM     | BOOST | OFFICE | ADM-E  | SUPER  |
| Archiver un profil          |  —  |  —  |  —  | Entite  |   —   |   —    | Entite | Global |
| Reactiver un profil archive |  —  |  —  |  —  | Condit. |   —   |   —    | Entite | Global |
| Consulter un profil archive |  —  |  —  |  —  | Entite* |   —   |   —    | Entite | Global |
```

Le §6.2 le redit en mots : « l'archivage d'un collaborateur est réservé à l'ESM, à l'administrateur
d'entité et au super-administrateur ». Deux grilles, donc, parce que le document en porte deux —
`ROLES_DU_CYCLE_DE_VIE` à côté de `ROLES_D_ECRITURE`, et un test exige l'**égalité** de la première
avec les trois rôles, non l'inclusion : un test qui vérifierait « l'ESM est dedans » passerait sur
une grille qui contient les huit.

**Le témoin le plus utile du lot est celui-là**, et il ne diffère que par la grille consultée :

```text
ok   LE CRITERE : un DSM modifie SON consultant — 200                        (controle 19)
ok   LE REFUS APPARIE : le MEME DSM qui a ecrit au controle 19 est REFUSE
     a l'archivage — 403, le §6.1 le met a TIRET sur cette ligne             (controle 30)
```

Sans lui, un refus d'archivage pourrait venir d'un décor incomplet — c'est exactement le défaut
`T7-5`, où cinq contrôles rendaient `403` parce que le DSM n'avait pas d'appartenance, et où **la
garde avait raison**.

## 2.3 « Conditionnel » n'est pas une décision en suspens — §7.29, sixième occurrence

Le §6.1 vaut **`Conditionnel`** pour l'ESM sur la réactivation. Le mot ressemble à une case vide ;
la condition est écrite ailleurs, en deux endroits concordants :

- matrice §18 : « Restaurer un collaborateur | — | **Entité, restauration fonctionnelle** | … » ;
- **`ARB-DROIT-003`** : « L'ESM peut restaurer dans son entité un profil, un contenu, un événement,
  un cercle ou un bureau. Les restaurations **techniques, massives ou liées aux imports** restent
  réservées à l'administrateur d'entité et au super-administrateur. »

Un profil à l'unité par une route dédiée **est** une restauration fonctionnelle : l'ESM est
autorisé. Inventer une condition ou ouvrir une question aurait été l'erreur que le §7.29 décrit.

**Et il existe une SECONDE ligne « Réactiver un profil archivé », qui n'est pas celle-ci.** Le §14 —
imports CSV — la reprend en exigeant une « **Confirmation explicite** » de l'ESM et de l'ADM-E.
C'est le LOT 9, et l'appliquer ici ajouterait une exigence que le §6.1 ne porte pas.

## 2.4 Archiver quelqu'un d'actif est un CHEMIN, pas une transition

Le §24.1 ne porte **aucune** transition `Active --> Archived`. Le §6.1 n'a qu'une action. Les deux se
concilient sans rien inventer :

```text
Active   --> Departed  : depart enregistre        puis  Departed --> Archived
Future   --> Archived  : « arrivee annulee »            (aucun depart)
Departed --> Archived  : archivage fonctionnel seul
```

**Et les deux étapes révoquent, ce qui rend l'ordre inoffensif** — `T9` du LOT 3 l'avait établi et
mesuré. La réponse expose les **deux** révocations séparément plutôt que sommées, et c'est ce qui
rend l'idempotence lisible :

```python
assert archivage.revocations[0].sessions_revoquees == 1   # le DEPART a tout pris
assert archivage.revocations[1].sessions_revoquees == 0   # l'archivage ne trouve plus rien
```

Lire « la seconde n'a rien trouvé » **est** la preuve que la première avait tout pris. Si la
révocation ne tenait qu'à l'archivage, il existerait une fenêtre pendant laquelle un parti garde sa
session — ce que le §7.4 et le §30.22 interdisent tous deux par le mot « immédiatement ».

**Le témoin qui discrimine l'« arrivée annulée » est `departure_date`.** Forcer un départ depuis
`future` daterait une sortie qui n'a jamais eu lieu, et la contrainte `depart_date_si_departed` ne
l'aurait pas dit — elle ne vaut que pour `departed`. **Seule l'absence de date le prouve.**

## 2.5 Les transitions vivent dans le modèle, et les deux grilles en sont DÉRIVÉES

Deux modules ont besoin du §24.1, pour des raisons différentes : le service pour **refuser** une
transition, la grille de permissions pour savoir quelle **action** l'état rend possible. Les laisser
dans le service ferait dépendre le module de permissions d'un module d'écriture ; une copie dans
chacun divergerait au premier ajout.

Elles vivent donc dans `app/people/modeles.py`, **aux côtés d'`ETATS_OCCUPANTS`** — exactement le
constat qu'un **import circulaire** avait déjà imposé en `T5` pour `ETAT_LISTE`.

Et les deux ensembles s'en dérivent **par le sens de la transition** :

```python
#  services.py — elle REVOQUE si elle quitte l'occupation
TRANSITIONS_AUTORISEES = {(d, v) for d, v in TRANSITIONS_DU_CYCLE_DE_VIE if v not in ETATS_OCCUPANTS}
#  archivage.py — elle RESTAURE si elle y ramene
TRANSITIONS_QUI_RESTAURENT = {(d, v) for d, v in TRANSITIONS_DU_CYCLE_DE_VIE if v in ETATS_OCCUPANTS}
```

**Ajouter `Archived --> Active` a donc exclu automatiquement cette transition du service de
révocation** — ce qu'une troisième liste recopiée n'aurait pas fait (§7.27). Un test exige que les
deux **partitionnent** les états de départ : une erreur de sens dans l'un des deux `if` les rendrait
égaux, et chacun pris seul paraîtrait juste.

## 2.6 La restauration ne rouvre rien, et elle DIT ce qui manque

Arbitrage de Jonathan du 10/09/2026, sur trois motifs concordants :

- le §23.4 dit « la suppression d'un rôle actif **clôture** la relation au lieu d'effacer
  l'historique ». Rouvrir d'anciennes valeurs sur une période neuve n'est pas restaurer un
  historique, c'est **décider à nouveau** ;
- la quatrième idée du socle du LOT 2 — « inventer un attributeur **fabriquerait** une trace d'audit
  fausse » — s'applique littéralement : un DSM réaffecté par la plateforme est un DSM que personne
  n'a désigné ;
- le corpus n'en dit rien. §6.5.

**La conséquence est rapportée, jamais taie.** `relations_a_redonner` mesure, relation par relation,
et la forme est ce qui la rend **exacte** :

```sql
SELECT bool_or(period @> :instant) FROM <table> WHERE <lien> = :cible AND archived_at IS NULL
```

| Valeur | Sens | Rapporté ? |
|---|---|---|
| `NULL` | la relation n'a **jamais** existé | non — on ne redonne pas ce qui n'a pas été donné |
| `FALSE` | elle a existé et n'existe plus | **oui** |
| `TRUE` | une période courante existe | non |

Le cas `NULL` est la raison de cette forme, et il a été **mesuré** : voir le défaut `T8-6`.

**Et la date de départ est désapposée, ce qui est la moitié qui compte.** `period` est
`GENERATED ALWAYS AS daterange(arrival_date, departure_date)` : la garder rendrait une appartenance
`active` dont la période est **déjà close**, donc invisible à toutes les lectures en
`period @> :instant` — `T3`, `T4`, `T7` — **en paraissant justes**. Un test qui n'aurait vérifié que
`membership_state` serait resté vert.

## 2.7 La base arbitre les deux refus de la restauration, et c'est voulu

Repasser dans un état occupant et rouvrir la période peut violer deux garde-fous du schéma, et
**ils ont raison** :

| Contrainte | Ce qu'elle refuse |
|---|---|
| `uq_entity_membership_person_id_occupante` | la personne occupe déjà une appartenance, ici ou ailleurs (§25.1) |
| `excl_entity_membership_sans_chevauchement` | la période redevenue ouverte chevauche une appartenance postérieure |

Écrire ces deux vérifications en Python donnerait une seconde règle, qui divergerait le jour où le
§25.1 changerait — et elle serait de toute façon sujette à la course que l'index, lui, ne laisse pas
passer. C'est le §7.32.

**Le `409` ne nomme pas la cause** : elle porte sur une appartenance possiblement d'une **autre
entité**, que le §5.1 ne laisse pas lire à l'appelant. Elle est journalisée côté serveur, avec le
nom de la contrainte — même parti que la miniature illisible de `T5`.

## 2.8 « Consulter un profil archivé » : une route DISTINCTE, et deux tests qui restent verts

Le §6.1 traite « Consulter un profil **actif** » — les huit rôles — et « Consulter un profil
**archivé** » — trois rôles, « besoin fonctionnel » — comme deux lignes différentes. Élargir la fiche
ordinaire les aurait fusionnées **et cassé le test de `T4`** qui exige le même 404 pour un profil
exclu, dont c'est précisément le rôle.

> **LA PASSATION ANNONÇAIT QUE `T8` DEVAIT CASSER DEUX TESTS. LA MESURE DIT LE CONTRAIRE, ET LES
> DEUX RESTENT VERTS.** Le trombinoscope continue d'exclure les archivés y compris pour un `SUPER` —
> le §6.1 lui donne la ligne « profil actif » — et `resoudre_le_perimetre` continue de refuser une
> cible archivée, ce qui est **juste** : on ne *modifie* pas un archivé, on le restaure. Une seconde
> population servie par une seconde route est plus fidèle au document qu'un assouplissement de la
> première. La population est un **paramètre** de `lire_la_fiche`, jamais une copie de sa requête.

**La visibilité n'est pas filtrée**, et l'ouverture est motivée : l'archivage ne touche pas
`profile_visibility`, donc un archivé peut être `draft`, `published` ou `hidden`. Filtrer ferait
échouer un acte que le §6.1 autorise, pour une raison que le corpus n'écrit nulle part (§7.25). Un
test l'éprouve sur **les trois** visibilités, avec la fiche ordinaire pour témoin — elle rend `None`
sur les trois.

**Aucun chemin de photo n'est rendu** : il mène à une route qui exige un profil listable, donc un
404 garanti. Un champ toujours nul est ce que `T4` avait refusé pour la photo elle-même.

## 2.9 Aucune énumération des archives, et c'est nommé plutôt que comblé

**Mesure du 10/09/2026, zéro occurrence :**

```bash
grep -niE 'liste.{0,40}archiv|archiv.{0,40}liste|rechercher.{0,30}archiv|archiv.{0,30}recherch' \
  docs/product/*.md docs/architecture/*.md
```

Le corpus ne décrit **aucune** liste ni recherche de profils archivés — et les axes de filtre que le
`MVP-L05-US002` énumère sont entité, cercle, DSM, client, métier et statut, **pas l'état
d'appartenance**. Ajouter un septième axe ou une route de listage aurait été le §6.5, et aurait cassé
le témoin de `T2` pour la mauvaise raison.

> **Conséquence à annoncer à la porte `G5`, et elle est réelle :** l'identifiant d'un archivé doit
> venir d'ailleurs. Deux candidats existent déjà — l'**historique organisationnel** de `T9`, la
> sous-étape suivante, et le **back-office** du LOT 9, dont le cahier §7 range « archivage et
> restauration » dans ses fonctions principales. La décision leur appartient.

## 2.10 La concurrence optimiste, et la date de départ facultative

§18.4 : « les modifications **sensibles** utilisent une concurrence optimiste ». L'archivage l'est —
le §11.3 range les opérations sensibles à part, et le §6.1 le réserve à trois rôles. L'ancre est
`entity_membership.version`, **racine** de l'agrégat comme en `T7`, si bien qu'un archivage et une
modification organisationnelle concurrents se **séquencent** au lieu de s'écraser. Le service du
LOT 3 écrivant en SQL direct ne la touche pas : elle est incrémentée explicitement.

**La date de départ est facultative, et ce n'est pas une invention** : le cahier §2.1 range « date de
départ » parmi les informations que porte `entity_membership`, et le §24.1 libelle la transition
« départ **enregistré** ». La rendre facultative permet d'archiver quelqu'un parti la semaine
dernière sans écrire une date fausse ; à défaut, le jour de l'appel.

**Aucun MOTIF n'est exigé** : les **cinq** cas du §18.1 — purge définitive, révocation manuelle d'un
accès actif, changement sensible de rôle, rollback d'import, intervention du super-administrateur —
ne comprennent pas l'archivage. En ajouter un serait le §6.5.

---

# 3. Contrôles exécutés

## 3.1 Les tests

```text
uv run pytest -q --collect-only | tail -1
#  888 tests collected            (+31)
uv run pytest -m integration -q --collect-only | tail -1
#  577/888 tests collected        (+31 — les trente-et-un sont d'integration)

uv run pytest apps/api/tests/test_archivage.py -q
#  29 passed

make check
#  code=0 — Tous les controles sont passes.
make residu-check
#  577 passed, 311 deselected in 291.20s
#  26 tables comptees, aucun residu, et la suite est verte
```

**Les `7 ligne(s) avant`** de `residu-check` sont les traces sans acteur d'`auth_event`, nommées
**structurelles** par la ventilation de `DEC-566` : rien de nouveau.

## 3.2 Le contrôle de stack, à travers Caddy en HTTPS

`make profil-check` passe de **26 à 36** contrôles. **Aucune cible nouvelle**, donc rien à ajouter
dans `ci.yml` — c'est le bénéfice direct du §7.27, et le troisième lot de suite où il s'applique.

```text
ok   TEMOIN : l'ESM se connecte, et `GET /auth/session` rend son jeton
ok   sans session : 401 — l'archivage n'est pas anonyme
ok   sans jeton CSRF : 403 — la SECONDE ecriture metier du projet est protegee
ok   LE REFUS APPARIE : le MEME DSM qui a ecrit au controle 19 est REFUSE a l'archivage — 403
ok   LE CRITERE : l'ESM archive — 200, `active` -> `archived` en passant par le depart,
     et les 5 relations du decor sont CLOSES, nommees table par table — dont la
     responsabilite BOOSTER, qui est la moitie « et roles » du §30.22
ok   l'archive DISPARAIT : la liste passe de ['Complete', 'Retiree'] a ['Retiree'],
     et sa fiche ordinaire rend 404
ok   « Consulter un profil archive » : 200 a l'ESM sur une route DISTINCTE, et AUCUN
     chemin de photo — il menerait a un 404 garanti
ok   le MEME DSM est REFUSE sur la fiche archivee — 403
ok   LE CRITERE : la restauration ramene dans la liste ET dans la fiche — 200 — et
     NOMME les 5 affectations restees closes
ok   restaurer un profil ACTIF est refuse — 403 `action_hors_perimetre`

    controles executes : 36   echecs : 0
```

**Ces neuf contrôles viennent en DERNIER, et ce n'est pas un détail.** Ils archivent le profil
complet, ce qui clôt ses relations et le retire de la liste : placés plus haut, ils casseraient le
« exactement deux profils » du contrôle 2 et l'historique intact du témoin 26. **Et c'est ce qui les
rend forts** — ils relient l'archivage à la **liste** et à la **fiche**, si bien qu'un archivage qui
n'aurait changé que `membership_state` ne passerait pas.

**Un troisième compte connectable est AJOUTÉ, jamais un existant modifié.** Donner un rôle d'ESM à
l'appelant sans rôle aurait détruit le témoin d'`ECART-051` — « aucun champ n'est masqué à quelqu'un
sans appartenance, ni responsabilité, ni rôle technique » — et au DSM celui du refus hors périmètre.
C'est le parti que `T7` avait pris pour le DSM, tenu une seconde fois. Sa visibilité est `draft`,
pour la même raison qu'en `T7` : le contrôle 2 exige exactement deux profils listés.

Et le conteneur porte bien le code du dépôt, vérifié avant de conclure (§7.28) :

```text
make code-check
#  info     conteneur : 73 fichier(s) .py
#  ok       les 73 fichiers sont identiques de part et d'autre
```

## 3.3 Le contrat et les registres

```text
python3 -c "import json;print(len(json.load(open('packages/contracts/src/contrat-api.json'))['endpoints']))"
#  20   (+3)
make docs-check
#  5 documents immuables intacts, 6 sequences d'identifiants coherentes,
#  12 controles de totaux derives et 12 controles sur la passation
```

**`make docs-check` a nommé les CINQ cascades** de `DEC-569` et `ECART-058` avec leur numéro de
ligne, dont deux portant le mot **COLLISION** — le tableau §4.14 de la passation et l'index du §4 de
`docs/README.md` annonçaient des identifiants désormais en usage. C'est le garde-fou de `DEC-566`
qui fait son travail, et c'est une meilleure preuve qu'un témoin.

---

# 4. Défauts trouvés — **six, et cinq sont dans mon propre travail de vérification**

## `T8-1` — Une exemption de règle posée « par précaution », qui n'exemptait rien

J'ai écrit `# noqa: S608` sur une interpolation de nom de table où la règle **ne se déclenche pas**.
`RUF100` l'a dit immédiatement : « Unused `noqa` directive ». C'est **exactement** le défaut `T7-3`,
rejoué le lendemain — et la parade est celle que `T7` avait retenue : la règle est **nommée** dans
les commentaires, jamais écrite, parce que ruff lit une directive écrite en clair.

## `T8-2` — Mon décor ignorait quatre contraintes que le décor de `T7` respectait

Quatre échecs d'un coup, et **la base les a tous nommés avec précision** :

| Contrainte | Ce que j'avais écrit |
|---|---|
| `ck_person_email_normalise_en_minuscules` | une adresse formée depuis `role.value`, qui vaut `ESM`, `ADM-E`, `SUPER` — **trois tests tombés ensemble** |
| déclencheur `dsm_responsabilite_active` | une affectation DSM **sans** la responsabilité DSM préalable. Le message nommait la règle **et** les deux identifiants |
| `ck_framework_responsibility_assignment_portee_selon_le_type` | `"booster"` en minuscules, quand le §8.4 écrit `BOOSTER` |
| `ck_technical_role_assignment_portee_selon_le_role` | `"super_admin"`, quand l'énumération vaut `SUPER_ADMIN` |
| `ck_entity_membership_depart_date_si_departed` | un état `departed` **sans** date de départ |

**La leçon n'est pas « lis les contraintes » — c'est que les valeurs viennent des ÉNUMÉRATIONS, pas
de ma mémoire.** Les deux dernières auraient été impossibles en écrivant
`TypeResponsabilite.BOOSTER.value` du premier coup, ce que le décor de `T7` faisait déjà. `DEC-499`
le dit : les noms suivent le modèle à la lettre.

## `T8-3` — Une substitution non vérifiée, qui n'a rien fait en silence

J'ai corrigé le décor de l'état `departed` par un `str.replace` **sans assertion sur le nombre
d'occurrences**. La chaîne avait été reformatée sur une seule ligne par `ruff format` entre-temps :
la substitution n'a rien remplacé, le fichier n'a pas changé, et le test a **continué d'échouer pour
la raison d'origine** — que j'ai d'abord cru être une seconde cause.

> **C'est le §7.0 troisième proposition appliqué à mes propres outils.** Une substitution qui
> n'annonce pas combien d'occurrences elle a touchées peut toujours n'en avoir touché **aucune**.
> Toutes les substitutions de cette sous-étape portent désormais un `assert t.count(a) == 1` — et
> c'est cet `assert` qui a attrapé les trois suivantes.

## `T8-4` — J'ai prévu la mauvaise contrainte, et ma branche neuve était du code jamais exécuté

J'avais ajouté au traducteur une branche `UniqueViolation` en écrivant un test censé l'exercer : une
personne active ailleurs, dont on restaure l'appartenance archivée. **La mesure a dit
`periode_incompatible`**, donc `ExclusionViolation` — désapposer `departure_date` rend la période
**non bornée**, laquelle chevauche alors toute appartenance postérieure. L'exclusion se déclenche
avant l'unicité.

Les deux refus sont légitimes, et la base choisit celui qu'elle rencontre. **Mais ma branche
`UniqueViolation` n'était atteinte par aucun test**, et rien ne l'aurait signalé — §7.25, « un témoin
qui n'exerce pas un contrôle ne prouve rien de ce contrôle ». Un **second** test l'atteint, avec une
appartenance antérieure à l'arrivée de celle qu'on restaure : la période rouverte ne la chevauche
pas, et seule l'unicité de l'occupation reste violée.

**Et je n'ai pas changé le décor pour avoir raison** : le premier test assume désormais la cause
mesurée, avec le motif écrit.

## `T8-5` — Mon attendu comptait quatre relations, le service en clôt cinq

Mon contrôle de stack exigeait que l'archivage close les **quatre** relations de l'appartenance —
métier, statut, DSM, cercle. Il en a rendu **cinq**, et la différence nommée était
`framework_responsibility_assignment` : « Ada Complete » porte une responsabilité `BOOSTER` dans le
décor, et le service du `T9` du LOT 3 clôt aussi les relations de la **personne** bornées à l'entité
quittée.

**C'est la moitié « et rôles » du §30.22, et le contrat réel est meilleur que celui que j'avais
écrit.** Le contrôle avait raison ; je l'ai aligné sur lui, pas l'inverse.

> **Et l'échec ne le disait pas au premier essai.** Mon message imprimait un extrait tronqué du
> dictionnaire, qui cachait précisément la clé en cause. Il nomme désormais l'écart : « relations
> closes manquantes […], en trop […] ». C'est le §7.18 — la première correction à écrire est celle
> qui te dira pourquoi.

## `T8-6` — Mon rapport nommait une relation qui n'avait JAMAIS existé

Après avoir étendu `relations_a_redonner` aux six relations du §25.2, le contrôle a nommé
`technical_role_assignment` sur un profil qui **n'en a jamais porté**. Le rapport disait « pas de
période courante », ce qui est vrai — et **faux comme avertissement** : on ne redonne pas ce qui n'a
pas été donné.

> **§7.21 : un avertissement faux est pire qu'une absence d'avertissement**, parce qu'il apprend à
> passer outre. La correction n'a pas été de retirer la table de la liste — ce qui aurait recréé une
> liste recopiée — mais de rendre la **mesure** exacte : `bool_or(period @> :instant)` distingue
> `NULL` (jamais existé), `FALSE` (a existé, plus maintenant) et `TRUE` (courante). Une seule valeur,
> trois sens, et un test par sens.

## Deux choses que la base et le harnais m'ont apprises, et qui ne sont pas des défauts

- **un ordre refusé avorte la transaction PostgreSQL entière** — « current transaction is aborted,
  commands ignored until end of transaction block ». Le décor de ces fichiers est une seule
  transaction annulée à la fin : le témoin positif d'un refus **ne peut pas** vivre dans le même
  test. C'est un fait du harnais, pas du produit, et il est nommé dans le test qui l'a rencontré ;
- **`make code-refresh` reconstruit aussi `web`**, dont l'image de base vient de Docker Hub. Le
  téléchargement de métadonnées a bloqué plus de dix minutes. `T8` ne touche **aucun** fichier du
  frontend : seuls `api` et `worker` ont été reconstruits, et `make code-check` le prouve — 73
  fichiers identiques de part et d'autre. La cible complète reste la bonne routine dès qu'un fichier
  du frontend change.

---

# 5. Écart ouvert et clos

## `ECART-058` — une colonne générée refuse avant toute contrainte, et le refus sortait en 500

**Trouvé en cherchant pourquoi MON refus de date n'était pas traduit**, puis en demandant *quel
autre code porte la même exigence* — la moitié du §7.38 que `T3` avait oubliée et qu'`ECART-055` a
coûtée deux semaines plus tard.

`entity_membership.period` est `GENERATED ALWAYS AS daterange(arrival_date, departure_date)`. Une
arrivée postérieure au départ rend « **range lower bound must be less than or equal to range upper
bound** » — une `DataException`, donc un `DataError` de SQLAlchemy, que `except IntegrityError` **ne
voit pas**. Mesuré par sonde avant toute correction : le `PATCH` de `T7` sortait en **500** sur un
état parfaitement atteignable, une appartenance `active` **pouvant** porter une `departure_date`.

Le traducteur gagne une quatrième branche — `DataException` → **`422 valeur_refusee`**, parce que
c'est la **valeur envoyée** qui est refusée — et les deux appelants capturent
`(IntegrityError, DataError)`, **et non `DatabaseError`** : ce dernier couvre aussi
`OperationalError`, une panne de connexion, qu'il ne faut surtout pas traduire en refus métier.

Détail complet au registre. **Clos.**

---

# 6. Ce que `T8` laisse à la suite

| Point | Où il va |
|---|---|
| **`#122` reste OUVERTE** | `T8` ne livre aucun écran, et `US007` en suppose un. Comme `#120` et `#121` |
| **aucune ÉNUMÉRATION des archives** | le corpus n'en décrit aucune. `T9` — l'historique — ou le back-office du LOT 9. **À annoncer à `G5`** |
| **le retrait d'autorisation photo** | toujours sans route, comme `T5` l'avait nommé. Sa grille du §6.1 est propre — « soi sur demande », « support » — donc ce n'est pas un archivage. LOT 9, ou une sous-étape dédiée |
| **`exiger_un_scope` attend TOUJOURS son premier consommateur** | LOT 3, `T9`. `T8` consomme `exiger_un_role_dans_l_entite` et la protection CSRF, pas celle-là. Les comptes de service liront des profils au LOT 9 |
| **`resoudre_le_perimetre` refuse toujours un archivé** | et c'est **juste** : on ne modifie pas un archivé, on le restaure. Le test qui le fige reste vert, contrairement à ce que la passation annonçait |
| **la purge définitive** | quatrième ligne du §6.1, `SUPER` seul. Modèle §24.1 : `Archived --> Anonymized`, « délai RGPD atteint ». **LOT 12**, §30.21 et §30.23 y sont reportés |
| **`ECART-012`** | attend toujours Léa, échéance dépassée. Devient visible à `T10` et `T11` |

---

# 7. Chiffres, tous dérivés le 10/09/2026

| Grandeur | Valeur | Commande |
|---|---|---|
| Tests | **888** dont **577** d'intégration | `uv run pytest -q --collect-only \| tail -1` |
| Tests nouveaux | **31**, tous d'intégration | 29 dans `test_archivage.py`, 2 dans `test_ecriture_organisationnelle.py` |
| Vitest | **299** — 81 `contracts`, 97 `ui`, 121 `web` | `make test-frontend` |
| Contrôles de `profil-check` | **36** (+10) | sortie du contrôle |
| Endpoints du contrat | **20** (+3) | `jq '.endpoints \| length'` |
| Cibles du `Makefile` | **86**, inchangé | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Migrations | **16**, inchangé — `T8` n'en écrit **aucune** | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Contrôles du §30 | **13 acquis · 1 partiel · 10 reportés · 1 inapplicable**, inchangé | `make recette-modele-check` |

**Aucune migration, et ce n'est pas un oubli** : `T8` n'ajoute ni table, ni colonne, ni contrainte.
Les quatre transitions du §24.1 étaient déjà toutes permises par
`ck_entity_membership_membership_state_valide`, et l'archivage n'est pas un état de schéma nouveau —
c'est un chemin dans un état existant.
