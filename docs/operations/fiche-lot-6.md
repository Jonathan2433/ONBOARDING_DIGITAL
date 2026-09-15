# Fiche de lot — LOT 6

**Intitulé :** Framework, cercles, bureaux et contenus éditoriaux
**Épic :** `MVP-L06`
**Ouvert par Jonathan le :** 13 septembre 2026
**État :** **OUVERT**, découpage **validé** le 13/09/2026 — `DEC-575`
**Porte de sortie :** `G6`, tag `v0.6.0` prévu

> **TOUS LES NOMBRES DE CETTE FICHE SONT DÉRIVÉS, PAS RECOPIÉS**, et chacun est accompagné de la
> commande qui le produit. C'est la classe `ECART-021`, rejouée une douzaine de fois dans ce projet,
> et le LOT 5 l'a encore payée deux fois — « 11 des 25 » contrôles du §30 là où la mesure en donne
> **10**, et « les cinq issues » là où **neuf** étaient ouvertes.

---

# 1. Ce que le lot doit produire

## 1.1 Les **sept** stories, comptées dans le backlog

```bash
grep -cE '^\| `MVP-L06-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Dépend de |
|---|---|---|---|---|
| `MVP-L06-US001` | `P0` | M | Découvrir le Framework depuis une page synthétique | LOT 5 |
| `MVP-L06-US002` | `P0` | L | Consulter les pages des cercles | `US001` |
| `MVP-L06-US003` | `P0` | L | Consulter les pages des bureaux | `US001` |
| `MVP-L06-US004` | `P0` | **XL** | Éditer un contenu avec des blocs contrôlés | `US002`, `US003` |
| `MVP-L06-US005` | `P0` | M | Gérer la présentation et les liens internes de l'entité | `US004` |
| `MVP-L06-US006` | `P1` | L | Prévisualiser puis publier un contenu | `US004` |
| `MVP-L06-US007` | `P1` | M | Reprendre les textes validés du prototype | LOT 0, `US004` |

**Cinq `P0`, deux `P1`.** `US004` est la seule `XL` du lot, et c'est elle dont tout le reste dépend.

## 1.2 Les **sept** critères de sortie — dérivés des **deux** sources, qui concordent

La roadmap autonome et l'annexe C du cahier portent chacune la liste. **Elles ont été comparées
avant d'être recopiées ici**, parce qu'un document dérivé peut prescrire autre chose que sa source
dès sa rédaction (`ECART-023`) :

| # | Critère | Ce qui devra le prouver |
|---|---|---|
| 1 | les contenus de Bordeaux sont relus avant publication | l'état `draft` est le défaut, et la publication est un **geste distinct** et audité |
| 2 | le modèle générique ne contient **aucune** donnée locale | une entité créée depuis le générique, et le contrôle qui cherche les chaînes de Bordeaux dans les **octets** servis |
| 3 | les composants respectent le design system | `cadre-check`, étendu aux composants nouveaux ; aucune couleur hors jetons dans les feuilles |
| 4 | les couleurs de cercle ne sont **jamais** l'unique information | un cercle **avec** jeton et un cercle **sans** — le couple du §7.42 — et le libellé présent dans les deux |
| 5 | les animations respectent `prefers-reduced-motion` | l'alternative servie, comme `T10` du LOT 5 l'a fait pour la carte retournable |
| 6 | aucun contenu arbitraire ne peut injecter du code | le **témoin positif** : un bloc légitime rendu, **et** une charge d'injection refusée |
| 7 | Jonathan valide l'organisation et l'édition | la démonstration guidée de la checklist `G6` |

> **QUATRE DE CES SEPT CRITÈRES SONT NÉGATIFS** — « aucune donnée locale », « jamais l'unique
> information », « aucun contenu arbitraire », et la relecture avant publication. **Un critère
> négatif se satisfait tout seul quand la fonctionnalité n'existe pas** : c'est le §7.39, et il a
> coûté la fusion de `T5` et `T6` au LOT 5. Chacun reçoit donc son **témoin positif dans la même
> sous-étape**, et c'est ce qui commande le découpage du §3.

---

# 2. Ce que le corpus tranche déjà, et qu'il ne faut pas réinventer

| Point | Où c'est écrit | Ce qui est tranché |
|---|---|---|
| Les **huit** cercles initiaux | cahier §10.3 | Change, Data, Design, Forge, IT, Produit, Projet, Shield — **« configurables en base de données »**, donc amorcés et non codés en dur |
| Les **trois** bureaux initiaux | cahier §10.3 | BDS, BDE, BDG — **« entièrement configurables »** |
| Les blocs autorisés | cahier §10.7 **et** modèle §15.2 | **deux listes, et elles diffèrent** — voir §8.3 |
| Le modèle éditorial | `ARB-DATA-003` | pages **typées** composées de blocs autorisés, associées à `circle`, `office`, `event` et `internal_link`. **Pas de CMS libre** |
| La table des responsabilités | `ARB-DATA-002` | **une seule** table `framework_responsibility_assignment`, déjà posée au LOT 2 |
| Ce que « Conditionnel » veut dire | `ARB-DROIT-003` | l'ESM restaure **fonctionnellement** dans son entité — profil, contenu, événement, cercle, bureau. Les restaurations **techniques, massives ou liées aux imports** restent à l'`ADM-E` et au `SUPER` |
| Les membres secondaires | `ARB-DROIT-004` | le Booster gère l'appartenance **secondaire** à son cercle et les contenus liés. Il **ne peut pas** modifier le cercle principal, le DSM, le client ni le statut d'un membre seulement secondaire |
| L'accessibilité | cahier §14.2 | information **jamais** portée uniquement par la couleur · `prefers-reduced-motion` · alternatives aux animations |

## 2.1 Le piège de la matrice, mesuré avant de commencer

**Le LOT 5 portait le piège de la colonne `OFFICE`, entièrement à tiret. Le LOT 6 en porte trois,
et ils vont tous dans le même sens : `ADM-E` n'a PAS tout dans son entité.**

| Ligne de la matrice | La cellule | Ce qu'un raccourci ferait |
|---|---|---|
| §10.2 « Affecter ou remplacer le Booster » | `ADM-E` → **tiret**, `ESM` → Entité, `SUPER` → Global | accorder à l'administrateur d'entité un droit que la matrice lui refuse **en cellule et en toutes lettres** |
| §10.3 « Affecter les responsables » | `ADM-E` → **tiret** | le même, sur les bureaux |
| §10.3 « Modifier la structure du bureau » | `OFFICE` → **« Bureau, contenu uniquement »** | laisser un responsable de bureau modifier la **structure**, alors que la cellule ne lui donne que le **contenu** |

Et la matrice le redit en prose, sous le tableau §10.2 :

> « L'attribution des responsabilités Framework est réservée à l'ESM et au super-administrateur.
> **L'administrateur d'entité ne peut pas attribuer ces responsabilités.** »

**Une quatrième nuance, plus discrète.** Au §13, l'ESM a « Entité » pour créer et modifier, mais
**« Périmètre »** pour publier et archiver. Les deux mots ne sont pas synonymes, et une grille unique
par rôle les confondrait.

**Et une condition qui n'est pas un droit mais une règle métier :** §10.2, « Archiver un cercle |
Entité, **si aucun membre actif** ». Ce n'est pas une case de rôle, c'est un état de la ressource —
§23.2, une interdiction liée à la ressource prévaut sur le cumul des rôles, exactement comme le
`409` de `T8` du LOT 5.

---

# 3. Le découpage — **douze** sous-étapes, validées le 13/09/2026 (`DEC-575`)

Chaque sous-étape porte le témoin **positif** qui rend son critère non trivial (§7.39), et une seule
pull request la fusionne. **Une sous-étape à la fois**, et elle part toujours de `develop`.

| # | Sous-étape | Stories | Ce qui la rend non triviale |
|---|---|---|---|
| ~~`T1`~~ | ~~**Les trois tables éditoriales** — `content_page`, `content_block`, `internal_link`, migration `0017`~~ **FAITE le 13/09/2026**, `DEC-578`, `QO-120` ouverte | socle | **Aucune des trois n'existait** : mesuré sur le schéma réel, 28 tables plus `alembic_version`. Et **`ECART-031` s'instruit ICI**, parce que c'est le seul endroit où un état de publication peut naître |
| ~~`T2`~~ | ~~**La page Framework en lecture** — les trois familles de cartes~~ **FAITE le 13/09/2026**, `DEC-579` | `US001` | la page est une **synthèse**, donc elle joint trois sources ; un contrôle « 200 et des cartes » passerait avec une famille vide |
| ~~`T3`~~ | ~~**Les cercles en lecture** — liste et page détaillée~~ **FAITE le 14/09/2026**, `DEC-582`. La liste vient de `T2` ; `T3` sert la **page détaillée**, membres paginés | `US002` | **le couple du §7.42** : un cercle **avec** jeton et un cercle **sans**, `color_token` étant nullable. C'est le critère 4, et c'est le défaut `T10-8` qui l'a appris |
| `T4` | **Les bureaux en lecture** — liste et page détaillée | `US003` | « un à trois responsables actifs » est un **comptage borné**, qu'aucune contrainte de ligne n'exprime. Voir `ECART-031` |
| `T5` | **Le rendu des blocs, et le refus de l'injection** | `US004` (1/3) | **les deux ensemble ou aucun** : « aucun HTML arbitraire » est satisfait par une route qui ne rend rien. Le témoin positif est un bloc légitime **rendu** |
| `T6` | **L'écriture d'un contenu dans son périmètre** | `US004` (2/3) | **les trois pièges du §2.1** — et la grille de l'écriture du LOT 5 ne se réemploie pas, elle **élargirait un droit** |
| `T7` | **Brouillon, publication, archivage, restauration** | `US006` | `ARB-DROIT-003` distingue la restauration **fonctionnelle** de la **technique** ; le §13 distingue « Entité » de « Périmètre » |
| `T8` | **La présentation de l'entité et les liens internes** | `US005` | les URL sont validées « selon une **liste de protocoles autorisés** » (§15.3), et une liste blanche fermée est aussi fautive qu'une absence de liste (§7.29) |
| `T9` | **Les écrans de lecture** — Framework, cercle, bureau | `US001`–`US003` | le critère 5, `prefers-reduced-motion`, et le critère 4 **à l'écran** : la couleur n'est jamais seule |
| `T10` | **Les écrans d'édition** | `US004` (3/3), `US005` | **un aller-retour RÉEL avant de déclarer le client terminé** — §7.43, deux défauts sont tombés ainsi en `T11` du LOT 5 |
| `T11` | **Le modèle générique, l'amorçage et la reprise relue** | `US007` | le critère 2 se prouve en **créant une entité neuve** et en cherchant les chaînes de Bordeaux dans les **octets** servis |
| `T12` | **Recette, §30 et checklist `G6`** | — | la recette tourne sur une base **remise à zéro**, leçon `T12` du LOT 5 |

**`US004` est découpée en trois** — `T5` lire, `T6` écrire, `T10` l'écran — parce que c'est la seule
`XL` du lot et que les trois n'ont ni les mêmes contrôles ni les mêmes risques.

---

# 4. Ce que ce lot NE fera PAS

**Hors périmètre, et c'est un autre lot :**

- **aucun onboarding** ni modèle de parcours — LOT 7 ;
- **aucun événement** : la table `event` est citée par `ARB-DATA-003`, mais les événements sont un
  lot à part entière. `content_page` ne recevra **pas** de `event_id` tant que la table n'existe pas ;
- **aucun import CSV** — LOT 9 ;
- **aucune GÉNÉRATION de miniature ni de variante** — LOT 11. Le LOT 5 en **sert** une, il n'en
  fabrique aucune, et le format reste non tranché (`ECART-052`) ;
- **aucun export** — LOT 11 ;
- **aucune médiathèque avancée** : le §12.2 de la matrice est explicitement « V1 » ;
- **aucune récurrence d'événement**, **aucun sous-titre** : cahier §10.6 et §13.5, différés en V1.

**Les interdits absolus, qui ne dépendent d'aucun lot :** aucun contournement de l'authentification ·
aucun jeton ni mot de passe en clair · aucun jeton dans `localStorage` · aucune donnée réelle de
collaborateur · **aucun HTML arbitraire stocké ou exécuté** (cahier §10.7) · aucune modification d'une
migration déjà appliquée ni des cinq documents de cadrage · aucune ligne du prototype historique
réutilisée comme code.

---

# 5. Ce qui est déjà livré et que ce lot consomme

| Élément | D'où il vient |
|---|---|
| `circle`, `office`, `circle_membership`, `framework_responsibility_assignment` | LOT 2, `T8`. **Les quatre existent**, colonnes relevées sur le schéma réel |
| `media_asset`, `media_variant`, `photo_authorization` | LOT 5, `T1`. Les images et vidéos des contenus s'y rattachent |
| `resoudre_le_perimetre`, `exiger_un_role_dans_l_entite` | LOT 4 `T8` et LOT 5 `T7`. **Deux grilles distinctes existent déjà** — le §6.1 en portait deux, le §10 en portera d'autres |
| la protection CSRF sur une route métier | LOT 5, `T7`. Elle vit dans `app/auth/dependances.py` et **ne doit jamais être recopiée** (`DEC-466`) |
| le design system, `CarteRetournable`, les jetons de couleur | LOT 1 `T10`, LOT 5 `T10` |
| le manifeste `contrat-api.json` | LOT 1 `T10`, `DEC-492` — **source unique** lue par TypeScript **et** par Python |

**Et une chose attend toujours son premier consommateur :** `exiger_un_scope`, posée au LOT 3 `T9`.
C'est la dépendance des **comptes de service**, qui liront des profils au **LOT 9**. Le LOT 6 ne la
consomme pas.

---

# 6. Les risques propres à ce lot

| Risque | Pourquoi il est réel ici |
|---|---|
| **Le modèle éditorial est le plus gros morceau du MVP** | `US004` est la seule `XL`, et trois autres stories en dépendent. Un `content_block` mal typé se paie sur toutes les pages |
| **« Aucun HTML arbitraire » est une exigence de sécurité, pas de confort** | un bloc de « texte riche limité » est exactement l'endroit où une injection entre. Le refus doit être **structurel**, pas un filtre |
| **Les contenus de Bordeaux sont des données réelles d'entreprise** | textes, liens et images relus avant publication (critère 1). **Aucune donnée réelle de collaborateur** n'entre, règle n°3 |
| **Le générique et le local se ressemblent** | le critère 2 se satisfait tout seul si le générique est vide et le local jamais créé. Le témoin est une **entité neuve réellement créée** |
| **`ROAD-RSK-033` / `034`** | avis sans correctif dans `python:3.12-slim` · les ports publiés percent l'isolement inter-réseaux. **À réévaluer avant le LOT 13**, inchangés ici |
| ~~**`images.yml` est rouge**~~ **REFERMÉE le 14/09/2026, `DEC-581`** | **Et cette ligne nommait la mauvaise cause** : elle annonçait `CVE-2026-56854` sur `web`, héritée de `caddy:2.11-alpine`. La mesure du 13/09 sur le run réel dit `CVE-2026-13221` dans **`perl-base`**, sur **`api` et `worker`**, héritée de `python:3.12-slim`. Ni le même avis, ni la même image. **La montée d'empreinte seule n'aurait rien corrigé** — mesuré : le condensat amont porte encore la version vulnérable sur les deux architectures. Le correctif est pris par une **couche `apt` à version épinglée**, et la porte est verte |

---

# 7. Les leçons du LOT 5 qui s'appliquent directement

| Leçon | Où elle mordra dans ce lot |
|---|---|
| **§7.42** — un décor qui ne produit jamais la valeur en cause ne dit rien d'elle | `circle.color_token` est **nullable**, et `str(None)` a servi la chaîne « None » sur **100 %** des cercles pendant deux lots. Le LOT 6 sert les cercles partout : **le couple avec / sans jeton dans chaque décor** |
| **§7.43** — un bouchon prouve ce que TU as écrit dans le bouchon | les écrans d'édition font des **écritures**. Un aller-retour réel avant de déclarer le client terminé, une fois, à la main |
| **§7.39** — un critère négatif est satisfait par une route qui ne sert rien | **quatre des sept critères** de ce lot sont négatifs |
| **§7.36** — un contrôle vert n'atteste pas que ton code est dans le commit | `git status --short` après chaque `git add`, et `make sources-check` dans `make check` |
| **§7.29** — un document peut annoncer une décision déjà prise | **sept occurrences**. Le §8 de cette fiche est le premier endroit à confronter au cahier |
| **§7.1 et §7.34** — iCloud | **mesuré le 13/09/2026, à l'ouverture de ce lot : 50 copies de conflit**, dont **deux migrations Alembic** donnant `0014` et `0016` en double. `make icloud-verify` les a toutes nommées ; la routine du §11 avait été sautée. **Elle n'est pas une formalité** |

---

# 8. Ce que le corpus NE tranche PAS — **sept écarts citent ce lot**

**Quatre sont à instruire AVANT d'écrire une ligne**, trois se règlent pendant. **Et trois d'entre eux n'appartiennent ni à moi ni à Jonathan** : `ECART-012`, `ECART-014` et `ECART-015` relèvent de **Léa**, qui décide du produit.

```bash
# derives des TROIS sources : synthese du registre, corps du registre, CLAUDE.md §8.1
```

## 8.1 Les quatre qui devaient être instruits **avant** d'écrire une ligne — **deux sont clos**

### `ECART-012` — « intercontrat » imposé à une direction générale — **ET IL N'EST PAS À NOUS**

**Son échéance a changé, et c'est le registre qui fait foi :** elle était « LOT 2, avant LOT 5 », elle
est désormais **« avant le LOT 6, puisque celle du LOT 5 est dépassée »**. `CLAUDE.md` §8.1 porte
encore l'ancienne — classe `ECART-021`, entre deux documents cette fois.

**`T5` du LOT 5 l'a instruit et a mesuré le coût des deux options ; il n'a pas tranché, et il ne
devait pas — Léa décide du produit.** Jonathan a formulé sa position le 12/09/2026 : ne rien
afficher pour la direction générale. **Ce n'est pas la résolution de l'écart**, c'est une position à
porter à Léa.

> **Ce que le LOT 6 y change : rien techniquement, et tout en visibilité.** Le LOT 5 l'a rendu
> visible sur la fiche profil ; le LOT 6 publie les pages de cercles et de bureaux, où les mêmes
> statuts professionnels s'affichent. **Plus le lot avance, plus la correction coûte cher**, et
> l'échéance a déjà glissé d'un lot entier.


### `ECART-031` — un bureau « publié », et aucune table ne porte la publication

Le §8.4 pose « un bureau possède entre un et trois responsables actifs **lorsqu'il est publié** », et
le §25.4 la reprend. **Or le §8.3 ne déclare aucun état de publication sur `office`** — vérifié sur
le schéma réel le 13/09/2026 : `office` porte `code`, `name`, `description`, `location_text`,
`display_order`, les champs communs du §3.1 et `archived_at`. **Rien d'autre.**

Trois issues, et le choix **n'est pas technique** : ajouter un état de publication à `office` ;
rattacher la publication aux **contenus** du §15, qui portent déjà `state` et `published_at` ; ou lire
« publié » comme « non archivé », **la plus simple et la plus contestable**.

> **TRANCHÉ le 13/09/2026 — `DEC-576`, la deuxième.** La publication est portée par la **page de
> contenu**, jamais par la table `office` : un bureau est « publié » quand sa `content_page` de type
> `OFFICE` est à l'état `published`. C'est la seule des trois qui n'invente rien — le §15.1 déclare
> **déjà** `state` et `published_at`, et `ARB-DATA-003` associe explicitement les pages typées aux
> bureaux. La première exigeait une nouvelle version d'un document **immuable** ; la troisième
> rendrait publié tout bureau **dès sa création**.
>
> **La conséquence est assumée et elle commande `T4`** : un bureau **sans page publiée** n'est pas
> publié, et la règle « entre un et trois responsables actifs » ne mord qu'à partir de là. Comme
> « entre un et trois » est un **comptage borné** qu'aucune contrainte de ligne n'exprime, `T4`
> posera un **déclencheur**. `ECART-031` est **clos**.

### `ECART-059` — le responsable de bureau a un périmètre « Bureau », et rien ne rattache une personne à un bureau

**Même table et même absence que `ECART-031`, et le registre le dit lui-même.** La matrice §5 donne
au responsable de bureau un périmètre « Bureau » sur l'audit ; aucune table ne rattache un
collaborateur à un bureau. Le §6.2 tranche dans le même sens — « un responsable de bureau n'obtient
aucun droit général sur les profils du seul fait de sa responsabilité de bureau » — donc la cellule
porte sur le **bureau comme ressource**, qui est un contenu de ce lot.

**Les deux se traitent ensemble, en une seule décision** — `DEC-576` — et la recommandation du
registre est suivie : **aucune table d'appartenance à un bureau n'est créée**.

> **Et le périmètre d'audit devient calculable sans elle** : ce sont les pages de contenu de type
> `OFFICE` rattachées au bureau par `framework_responsibility_assignment.office_id`, qui existe
> depuis `T8` du LOT 2. `ECART-059` est **clos**.

### `ECART-032` — le backlog interdit plus large que le cahier, la matrice et le modèle réunis

Le backlog écrit « aucune **responsabilité métier** active dans plusieurs entités » ; les trois autres
documents restreignent au seul **Booster**. Le cahier prévaut, le livrable du LOT 2 est conforme.
**Le LOT 6 expose les responsabilités**, donc c'est ici que la lecture devient visible.

> **Techniquement immédiat dans les deux sens** : le déclencheur de `T8` du LOT 2 teste
> `NEW.responsibility_type = 'BOOSTER'`, et retirer cette condition suffit. **Ma recommandation :
> ne rien changer** — un refus est un échec dur, une permission se resserre plus tard.
>
> **`ECART-032` reste OUVERT, et il n'est pas bloquant** : le livrable du LOT 2 est conforme au
> document prévalent. Ce que le LOT 6 doit faire est de l'**annoncer** quand il expose les
> responsabilités, pour qu'un relecteur du backlog ne conclue pas à un critère manquant.

## 8.2 Les trois qui se règlent **pendant** le lot, et deux relèvent de Léa

| Écart | Ce qu'il demande |
|---|---|
| `ECART-014` | Le prototype dit « Représentant de cercle », les documents validés disent « Booster ». **Le corpus prévaut** : l'écran dira « Booster ». À confirmer par Léa, qui possède le vocabulaire produit |
| `ECART-015` | Le prototype ne fournit **ni descriptions de cercles ni liens internes**, contrairement à ce qu'annonce le cahier §2.2. `US007` ne peut donc pas « reprendre » ce qui n'existe pas : ce sont des **contenus à produire**, et ils relèvent de Léa |
| `ECART-060` | Quatre des cinq filtres du trombinoscope n'ont **aucune liste de référence** à proposer. Les **cercles** en sont une, et ce lot la produit : `ECART-060` se referme partiellement ici, le reste au LOT 9 |

## 8.3 Un point que personne n'a encore relevé — **les deux listes de blocs diffèrent**

**Mesuré le 13/09/2026 en confrontant les deux sources**, et il faudra trancher :

| Cahier §10.7 | Modèle §15.2 |
|---|---|
| titres · textes · cartes · listes · liens · images · vidéos · **blocs de présentation** | titre · texte riche limité · image · vidéo · **carte de lien** · **citation** · liste · **appel à l'action interne** |

Le cahier ne nomme ni **citation** ni **appel à l'action interne** ; le modèle ne nomme pas **bloc de
présentation**, et il fond « cartes » et « liens » en une seule « carte de lien ».

**Cinq types sont communs** — titre, texte, image, vidéo, liste. Trois n'existent que dans le cahier
— cartes, liens, blocs de présentation. Trois n'existent que dans le modèle — carte de lien,
citation, appel à l'action interne.

> **ET L'UNION N'A PAS DE COMPTE UNIQUE, CE QUI EST PRÉCISÉMENT LE PROBLÈME.** Tout tient au trio
> « cartes » et « liens » du cahier contre « carte de lien » du modèle : **neuf** types si les trois
> libellés n'en désignent qu'un, **dix** si « cartes » vaut « carte de lien » et « liens » est à
> part, **onze** s'ils sont distincts. **Aucune des trois lectures n'est déductible des documents.**
>
> **CE COMPTE A ÉTÉ FAUX DEUX FOIS DE SUITE, ET LES DEUX FOIS DE MA MAIN.** J'ai d'abord écrit
> « huit » sans compter, puis « neuf ou dix » avec un script dont l'arithmétique comptait « carte
> de lien » deux fois. Le §7.0 septième point interdit d'écrire un compte qu'on n'a pas relevé ;
> il faut y ajouter qu'un compte relevé par un script faux n'est pas relevé.
>
> **TRANCHÉ le 13/09/2026 — `DEC-577` : l'UNION, et `QO-119` est OUVERTE.** Le cahier prévaut (§3),
> mais sa liste n'est pas fermée — « Le produit permet de gérer », même forme que le « à prévoir
> **notamment** » du §25.1 et le « par exemple » du §22 — et le modèle est plus précis sans être
> plus autorisé. **Le type reste contrôlé en base dans tous les cas**, et chaque type sera rattaché
> au document qui le nomme. §6.5 : une hypothèse déguisée en décision est pire qu'une case vide.
>
> **`QO-119` pose trois questions précises à Léa** : *(a)* « cartes » et « liens » font-ils un type
> ou deux ? *(b)* le « bloc de présentation » est-il un type propre ou une composition ? *(c)* la
> « citation » et l'« appel à l'action interne » entrent-ils au MVP ? Elle n'est **pas bloquante pour
> `T1`** — le type reste contrôlé en base, et restreindre plus tard est une migration d'une ligne —
> mais elle doit être tranchée **avant `T11`**, où un auteur devra choisir un type pour de vrai.

---

# 9. Traçabilité GitHub

**À créer à l'ouverture**, sur le modèle du LOT 5 :

| Élément | Valeur |
|---|---|
| épic | `[EPIC MVP-L06] Framework, cercles, bureaux et contenus éditoriaux` |
| stories | **sept** issues, `MVP-L06-US001` à `US007` |
| jalon | `G6` |

> **`Closes #N` ne referme pas une issue depuis `develop`** (§7.19) : la branche par défaut est
> `main`. Chaque issue se referme **à la main**, et son commentaire de fermeture est l'endroit où
> cocher les critères d'acceptation avec leurs preuves, ce que le backlog §11 exige.
>
> **Et le LOT 5 a montré que cette routine se perd** : ses **neuf** issues étaient encore ouvertes au
> 13/09/2026, alors que le compte rendu de `T12` n'en annonçait que cinq.
