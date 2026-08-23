# Compte rendu — LOT 4, sous-étape `T1`

**Lister les entités, côté API — la première route métier du projet**
**Story :** `MVP-L04-US001` (partiellement — `T2`, `T6` et `T7` la complètent)
**Réalisée le :** 23 août 2026
**Décisions produites :** `DEC-543`, `DEC-544` · **Écart consigné :** `ECART-039`
**Migration produite :** **aucune** — `entity` existe depuis le LOT 2, `T2`

---

## 1. Ce que cette sous-étape devait faire

Le critère de la fiche : « `GET …/entities` : les entités **actives** seulement, et le contrat
partagé. Une entité `suspended` ou `archived` **n'est pas rendue**, avec témoin · le contrat est lu
par TypeScript **et** vérifié côté Python. »

C'est **la première route métier du projet**. Les LOTS 1 à 3 n'exposaient que trois endpoints de
santé, la racine du contrat versionné, et six routes d'authentification.

---

## 2. Trois lectures du corpus, faites avant d'écrire une ligne

| Question | Ce que j'aurais pu supposer | Ce que le corpus dit |
|---|---|---|
| **quels statuts sont proposés ?** | « actives », d'après le backlog | le **cahier §8.3** l'écrit en toutes lettres : « un accès à chaque entité **active** ». Deux sources concordantes, donc aucune invention |
| **qui a le droit de lister ?** | les employés, sans doute | la **matrice §5** met `ANON` à **tiret** et les **huit** rôles authentifiés à la coche — `EMP`, `NEW`, `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E`, `SUPER`. **Aucun rôle à distinguer** : la seule question est « une session valide, oui ou non » |
| **et un compte de service ?** | il faudrait un scope | le **§22** dit « les comptes de service ne correspondent à **aucun rôle humain** », et `RIGHTS-018` le redit. `SERVICE` n'est **pas** une colonne du tableau §5 : lui ouvrir la page nationale serait inventer une ligne |

**Sur la troisième, j'ai failli ouvrir un écart** en constatant que `SERVICE` manque au tableau §5.
Le §22 l'explique : ce n'est pas un trou, c'est une exclusion voulue. **C'est le §7.29 dans l'autre
sens** — avant de déclarer qu'un document a manqué quelque chose, cherche s'il l'a dit ailleurs.

**Un contrôle de rôle ici aurait exigé plus que la matrice**, ce qui est le défaut du §7.20 : un
contrôle qui échoue sur un livrable conforme.

---

## 3. `ECART-039` — le critère nommait deux états là où le modèle en déclare trois

`StatutEntite` déclare **quatre** valeurs : `draft`, `active`, `suspended`, `archived`. Le critère de
la fiche ne nomme que « `suspended` ou `archived` » : ce sont deux **exemples**, et `draft` est le
troisième état non actif.

**Suivre le critère à la lettre aurait produit un témoin incomplet** — une entité en brouillon
proposée sur la page nationale, avec un critère qui se lit satisfait. C'est exactement le §7.34,
écrit la veille de cette sous-étape : *un motif écrit contre un exemple ne couvre que cet exemple.*

Trois parades, toutes mécaniques :

1. le filtre est écrit `= active` et **non** `NOT IN (suspended, archived)` — la forme positive
   couvre tout état futur ;
2. la valeur comparée est **dérivée** de `StatutEntite.ACTIVE`, jamais la chaîne littérale ;
3. un test **sans base** exige que l'énumération contienne exactement les quatre valeurs connues :
   si un lot en ajoute une cinquième, il échoue et oblige à décider si elle est active ou non.
   Sans lui, mes trois témoins d'exclusion continueraient de passer en ne couvrant plus la classe.

---

## 4. `exiger_une_session` — et le résiduel de `DEC-531` réexaminé

La dépendance réutilise **`lire_et_rafraichir`**, le seul chemin de validation de session du projet.
En écrire un second, en lecture seule, aurait donné deux chemins qui divergent — ce que `DEC-466`
interdit pour le masquage et `ECART-022` pour les modèles de configuration.

**Conséquence, et elle doit être dite : chaque lecture métier écrit désormais `last_activity_at`.**
`T6` du LOT 3 avait nommé comme une entorse assumée le fait qu'un `GET` écrive, sur la seule route de
session, et `DEC-531` renvoyait le réexamen au LOT 4. Le réexamen donne ceci :

> **l'entorse ne disparaît pas, elle se généralise** — et elle reste acceptable pour la raison que
> `T6` avait déjà mesurée : l'effet porte sur la session de l'appelant lui-même, si bien qu'un site
> tiers qui la déclencherait ne ferait que prolonger la session de sa victime. Aucun gain pour lui.

**Et c'est la sémantique que le mot « inactivité » exige** : un utilisateur qui navigue sans jamais
appeler la route de session serait autrement déconnecté alors qu'il est actif.

**Un test le MESURE** plutôt que de l'affirmer — `last_activity_at` avant et après un appel réel.

La dépendance pose aussi **`Cache-Control: no-store`** sur toutes les routes qu'elle protège. Caddy
est devant : sans cet en-tête, un mandataire partagé pourrait servir à un second appelant la réponse
construite pour le premier. La route de session de `T6` le posait déjà, une route à la fois ; le
faire dans la dépendance évite d'avoir à s'en souvenir.

---

## 5. Le piège `Annotated`, MESURÉ — un livrable qui paraîtrait protégé

FastAPI offre trois formes pour attacher une dépendance. `T10` du LOT 3 avait tranché entre les deux
premières. **La troisième est un piège, et il ne plante pas.**

```python
# Sous `from __future__ import annotations`, l'annotation est une CHAINE que
# FastAPI resout dans les GLOBALS du module. `parametres` est une variable de
# FERMETURE : elle n'y est pas.
def lister(a: Annotated[SessionEtablie, Depends(exiger_une_session(parametres))]): ...
```

**Mesure du 23/08/2026 sur un double jetable** : la route rend **422**, avec
`'loc': ['query', 'a']`. FastAPI n'a pas vu la dépendance et a pris le paramètre pour une **chaîne de
requête**.

> **Le défaut n'est donc pas un plantage mais un livrable qui paraît protégé** : il ne refuse pas les
> appels sans session — il refuse **tout le monde**, en réclamant un paramètre d'URL. Un test
> d'autorisation qui vérifierait « un appel sans cookie est refusé » **passerait**.

C'est la quatrième proposition du §7.0 : l'échec produit une observation voisine du succès. La forme
retenue est `dependencies=[Depends(...)]`, celle que `T10` annonçait, et le piège est écrit **juste
au-dessus de la route** pour que `T2` — qui aura besoin de l'identité de l'appelant — ne le
rencontre pas.

---

## 6. Quatre colonnes sur sept, et le motif de chaque absence

| Colonne | Exposée ? | Motif |
|---|---|---|
| `id`, `code`, `display_name`, `city` | **oui** | le §8.3 demande une liste et un accès. `city` est la seule colonne géographique de la table |
| `status` | non | **toute ligne rendue est active** : le champ serait constant. Un champ constant apprend à ne pas le lire — c'est le §7.21 sur les avertissements faux, dans un autre costume |
| `timezone` | non | aucun écran du LOT 4 n'affiche d'heure locale. Livrer une donnée sans consommateur est ce que `T10` du LOT 1 et `T11` de ce lot refusent tous deux |
| `country_code` | non | le §5.1 dit « `FR` dans le MVP ». Une carte **de France** n'a pas à distinguer les pays |

**`city` est exposée et la carte n'en vit pas.** `entity` ne porte **ni latitude ni longitude** —
mesuré sur le schéma réel — et c'est ce qui laisse le format de la carte ouvert en `T7`.

**Un objet et non un tableau à la racine.** `{"entites": [...]}` peut recevoir un champ voisin ; un
tableau ne peut pas. `T2` devra dire **quelle entité est consultée**, et c'est le point que le §8 de
la fiche laisse ouvert. Aucune pagination, et c'est mesuré : le §30.25 borne la recette à
**25 entités**.

**L'ordre est TOTAL, et c'est une nécessité.** `ORDER BY display_name` seul laisserait PostgreSQL
libre de rendre deux homonymes dans un ordre différent d'un appel à l'autre. Le tri porte aussi sur
`code`, qui est `UNIQUE` : l'ordre devient reproductible, donc testable — et un test l'exige sur
**trois** appels consécutifs.

---

## 7. Le contrat : le contrôle a fait son travail avant que je le lui demande

Le manifeste `contrat-api.json` déclare l'endpoint ; `test_contrat.py` exige l'égalité **dans les
deux sens** entre chemins déclarés et chemins servis.

**Témoin, non provoqué :** j'ai monté la route avant de la déclarer. Le contrôle a échoué en nommant
exactement `('/api/v1/entities', 'get')` dans « servis seulement ». Après déclaration : 5 tests
verts. Le témoin a donc été exercé **dans les deux sens**, sans mise en scène.

**Deux primitives extraites plutôt que dupliquées.** `estObjet` et `exigerChaine` étaient privées à
`sante.ts`. Le validateur du portail en a besoin ; les recopier aurait produit **deux exemplaires
d'une même règle**. Elles vivent dans `formes.ts`, **non réexporté** par `index.ts` : un consommateur
qui validerait lui-même ne passerait plus par les validateurs du contrat.

**Zod a été réexaminé, non archivé.** Le commentaire de `sante.ts` disait « `DEC-456` n'installe pas
Zod **avant le LOT 4**, faute d'usage ». Nous y sommes. Réponse : **trois formes ne le justifient pas
davantage**, `make audit` est à zéro avis et zéro tolérance depuis `DEC-493`, et chaque dépendance
ajoutée est une surface de plus. C'est le §7.22 — un résiduel se réévalue, il ne s'archive pas.

---

## 8. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **674** pytest (661 + 13), **143** Vitest (133 + 10) |
| `make entites-check` | **code 0** — **10 contrôles**, 0 échec, à travers Caddy en HTTPS |
| `make residu-check` | **code 0** — 23 tables comptées, **aucun résidu** |
| `make code-check` | **code 0** — les 56 fichiers du conteneur sont ceux du dépôt |
| `make api-check` · `web-check` | **code 0** · **code 0** |
| `make sessions-check` · `sessions-temoin` | **code 0** · **code 0** |
| `make csrf-check` · `ecrans-check` · `evenements-check` | **code 0** · **code 0** · **code 0** |
| `make icloud-verify` · `docs-check` · `audit` | **code 0** · **code 0** · **code 0** |

**Les treize tests Python et les dix tests TypeScript**, en résumé : l'entité active est rendue
(témoin central) · les **trois** états non actifs sont exclus, un test paramétré par état · sans
cookie 401 · jeton inconnu refusé **à l'identique** · session révoquée refusée · exactement quatre
champs · `Cache-Control: no-store` · ordre total sur trois appels · l'activité **est** rafraîchie ·
les quatre statuts du modèle sont connus du test · le validateur refuse six formes invalides et
**ignore** un champ supplémentaire.

### Les témoins négatifs, tous exécutés

| Témoin | Attendu | Observé |
|---|---|---|
| filtre `active` retiré, **requête valide** | les 3 exclusions échouent | **exactement 3**, zéro erreur SQL, les 10 autres passent |
| dépendance de session retirée | les refus échouent | **5 échecs** : sans cookie, jeton inconnu, révocation, cache, activité |
| champ `statut` ajouté à la réponse | le test des 4 champs échoue | **1 échec**, exactement celui-là |
| filtre retiré **sur le conteneur reconstruit** | `entites-check` échoue | **3 échecs**, « 4 entités rendues » au lieu de 1 |
| réversion fabriquée sur `README.md` | `icloud-verify` échoue | code **1**, le fichier et le commit nommés ; code **0** après restauration |

---

## 9. Quatre défauts, tous dans mon travail

**`T1-1` — mon premier témoin négatif ne prouvait rien du contrôle qu'il visait.** J'avais neutralisé
le filtre en écrivant `WHERE :statut_actif IS NOT NULL`. PostgreSQL a rendu
`IndeterminateDatatype: could not determine data type of parameter $1`, la route a rendu **500**, et
**9 tests sur 13** ont échoué — dont ceux du cache et de la révocation, qui n'ont rien à voir avec le
filtre. **L'échec avait une autre cause que celle visée.** C'est la leçon `T11` du LOT 3 : *un témoin
qui n'exerce pas un contrôle ne prouve rien de ce contrôle.* Refait en retirant la clause `WHERE`
entière : **exactement 3 échecs, zéro erreur SQL**.

**`T1-2` — mon décor de test violait une contrainte de la base.** Je reculais `last_activity_at`
d'une heure pour me donner un écart confortable ;
`ck_user_session_activite_apres_creation` l'a refusé, l'activité devenant antérieure à la création.
Classe `T9-1` du LOT 3. **Aucun décor n'est nécessaire** : l'écart naturel entre l'ouverture de
session et l'appel HTTP suffit, `now()` étant l'instant de début de transaction en microsecondes.

**`T1-3` — mon contrôle de stack échouait sur un livrable conforme, et son message ne disait pas
pourquoi.** À travers Caddy, une réponse réelle porte un en-tête `date` qui change d'une requête à
l'autre ; le test en processus ne le voyait pas, le client de test n'en ajoutant aucun. **Deux
défauts en un** :

- le contrôle exigeait plus que le critère → rendu **exact** et non affaibli (§7.20) : il exclut
  `date`, exige l'égalité de tout le reste — `x-request-id` compris, la corrélation étant fixée — et
  **annonce en sortie ce qu'il n'a pas comparé** ;
- son message affichait **les deux dictionnaires tronqués à 110 caractères**, sans dire lequel
  différait. C'est le §7.18 : *la première correction à écrire est celle qui te dira pourquoi.* Il
  nomme désormais chaque en-tête fautif, un par un.

**`T1-4` — ma sonde de diagnostic employait `timeout`, qui n'existe pas sur macOS.** `make
code-refresh` échouait sur `DeadlineExceeded` en résolvant `docker.io/docker/dockerfile:1`. Ma sonde
`timeout 25 docker manifest inspect …` a rendu « ECHEC » — parce que **`timeout: command not
found`**, non parce que Docker Hub était injoignable. Le §7.12 le dit noir sur blanc, et je l'ai
rejoué. Sans `timeout`, `manifest inspect` **réussit** et le `pull` direct aussi : la cause était un
délai transitoire, et la reconstruction a abouti au troisième essai.

**Et une chose que je n'ai pas mesurée moi-même, mais que le contrat a mesurée pour moi** : la
correspondance entre le manifeste et les chemins servis. Voir §7.

---

## 10. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **où vit l'entité consultée** | `user_session` n'a **aucune** colonne d'entité. Point ouvert du §8 de la fiche, à instruire en **`T2`** |
| **la carte de France** | ni latitude ni longitude dans `entity`, et le corpus ne dit que « illustrative ». **`T7`** |
| **la liste avant la carte dans le DOM** | c'est un critère de **`T6`**, l'écran. `T1` ne rend que des données |
| **le CSRF sur cette route** | c'est un `GET` : il n'y a rien à protéger. Le premier vrai consommateur sera l'écriture de **`T8`**, si le changement d'entité en est une — point de `T2` |
| **la dépendance de scope** | toujours sans consommateur, et la matrice ne l'autorise pas ici. Le résiduel reste **nommé** |
| **un compte de service sur cette route** | refusé faute de session, et c'est la lecture conservatrice du §22. Si le LOT 9 en a besoin, ce sera une décision, pas une déduction |

---

## 11. Ce que `T2` devra savoir

1. **la forme de la réponse est un objet**, précisément pour qu'un champ voisin puisse y arriver.
   L'entité consultée y a sa place sans casser un consommateur ;
2. **la dépendance rend `SessionEtablie(personne, identifiant)`** — `identifiant` est l'id de la
   ligne `user_session`, ce qu'il faudra si le choix d'entité s'y attache ;
3. **pour obtenir l'appelant, employer la forme à défaut d'argument** avec `noqa: B008`, et
   **jamais** `Annotated[...]` : le piège est mesuré au §5 ;
4. **`GET …/auth/session` écrit toujours sans jeton CSRF**, et le réexamen du §4 conclut que
   l'entorse se généralise plutôt qu'elle ne disparaît. Si `T2` fait du choix d'entité une
   **écriture**, elle devra porter un jeton — et ce sera le premier consommateur réel de `_proteger_du_csrf` ;
5. **`make entites-check` exige que le conteneur porte le code du dépôt.** `make code-refresh` puis
   `make code-check` avant de conclure quoi que ce soit d'un contrôle de stack : §7.28.
