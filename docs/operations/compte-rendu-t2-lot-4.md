# Compte rendu — LOT 4, sous-étape `T2`

**L'entité consultée : où elle vit — et le cahier l'avait déjà tranché**
**Story :** `MVP-L04-US001` et `MVP-L04-US002` (partiellement)
**Réalisée le :** 23 août 2026
**Décision produite :** `DEC-545` · **Écart consigné :** `ECART-040`
**Migration produite :** **aucune**, et c'est le résultat principal de la sous-étape

---

## 1. Le point que la fiche disait ouvert était fermé

Le §8 de [`fiche-lot-4.md`](fiche-lot-4.md) annonçait « **où vit l'entité consultée** — `US001` dit
“mémorisé pour la session”, et `user_session` n'a **aucune colonne d'entité** ». Les deux moitiés sont
vraies. La conclusion — qu'il y avait là une décision à prendre — ne l'était pas.

**Quatre endroits du cahier déterminent le parcours, et ils concordent :**

| Où | Ce qui est écrit |
|---|---|
| §4.1 | « une page nationale **après authentification** » |
| §8.1 | `LOGIN → Accueil national → Choix de l'entité → Accueil de l'entité → {Framework, …}` |
| §9.1 | la séquence de connexion finit sur « Accueil national » |
| §9.2 | « 1. connexion ; 2. affichage de l'**accueil national** ; 3. sélection d'une entité ; … 6. retour possible à la liste des entités » |

> **On atterrit TOUJOURS sur la page nationale.** Une mémoire serveur du dernier choix n'aurait donc
> **aucun consommateur** : elle servirait à sauter un écran que le cahier prescrit.

Et « le choix est mémorisé pour la session » ne peut alors signifier qu'une chose : **le choix
persiste pendant qu'on navigue**, non « on saute la page nationale la prochaine fois ».

**C'est le §7.29, pour la troisième fois en deux lots.** `ECART-040`.

---

## 2. Ce que le §23.3 disait, et que la fiche ne citait pas

Le cahier a une section entière, **§23.3 « Changement d'entité »**, qui donne **cinq** règles :

- ne modifie pas l'entité principale de la personne ;
- ne transfère pas ses responsabilités ;
- recharge les permissions ;
- **annule les requêtes et caches associés à l'entité précédente** ;
- doit être visible dans l'en-tête de l'application.

La quatrième est **exécutable dès maintenant**, et elle est implémentée : `PageEntite` porte un
`AbortController` par code, et l'état affiché est **couplé au code auquel il appartient**. Sans cela,
une réponse lente pour l'entité quittée arriverait **après** celle de la nouvelle et l'écraserait :
l'écran afficherait Bordeaux alors que l'adresse dit Paris.

**Le défaut n'apparaît que sous latence**, donc jamais en développement local — c'est le §7.16 sous un
autre jour. Un test le fabrique : Bordeaux répond lentement, Paris répond tout de suite, puis
Bordeaux répond ; l'écran doit rester sur Paris.

Les trois autres règles relèvent de `T3` (en-tête), `T8` (rechargement) et `T9` (permissions).

---

## 3. `DEC-545` — l'adresse fait foi, et rien n'est stocké

| Ce qui a été écarté | Pourquoi |
|---|---|
| une colonne `consulted_entity_id` sur `user_session` | **aucun consommateur** (§1). Et deux onglets partageraient une seule mémoire : ouvrir Paris dans le second changerait le premier |
| `localStorage` ou `sessionStorage` | le contrôle du frontend interdit **tout** usage des deux, plus strict que le cahier §7.4 qui ne parle que de « donnée d'authentification durable ». Le relâcher exigerait de **juger** ce qui est une donnée d'authentification, donc d'introduire une **heuristique dans un contrôle** — ce que le §7.25 nomme un défaut |
| un cookie dédié | il voyagerait sur **chaque** requête, y compris celles qui n'ont que faire de l'entité, et deux onglets se le disputeraient de la même façon |

**Retenu : l'entité vit dans l'adresse**, `/entites/{code}`. Conséquences, toutes vérifiables :

- **la règle 5 est satisfaite sans ambiguïté** — l'API reçoit l'entité explicitement à chaque requête
  et la valide ;
- **deux onglets peuvent consulter deux entités** sans se marcher dessus ;
- **un lien partagé ouvre la même entité**, et le rechargement tient — prouvé au niveau de la stack ;
- **le §23.3 quatrième point est naturel** : une autre adresse est une autre clé de cache ;
- **aucune migration**, aucune colonne, aucun stockage.

**Le `code` est la clé, et c'est mesuré.** `code_unique` n'a **aucune clause partielle** : une entité
archivée garde son code réservé, donc un code n'est **jamais réattribué** — exactement ce qu'on exige
d'un identifiant d'adresse. Un `uuid` ferait la même chose mais serait opaque, alors que le §9.2
demande un « affichage clair de l'entité consultée ».

**Le code est encodé partout où il entre dans un chemin**, côté contrat et côté routeur. `entity.code`
est une chaîne libre de 64 caractères — le modèle ne lui impose **aucun motif**, mesuré sur le schéma
— et un `/` non encodé appellerait une autre route. Un test l'exige sur `bord/eaux`, `a?b#c` et `..`.

---

## 4. Une entité non active rend la même chose qu'une entité absente

Le §8.3 donne accès aux entités **actives**. Pour l'appelant, une entité `draft`, `suspended` ou
`archived` n'est donc pas « interdite » : elle **n'existe pas**.

> Distinguer les deux apprendrait qu'un brouillon existe — et **le LOT 9 en créera avant
> publication**.

Le refus est un **seul gabarit**, `404`, et les deux réponses sont **comparées** — statut, corps et
en-têtes, la corrélation étant **fixée** plutôt qu'un champ exclu. Trois états non actifs, non deux.

**Et l'égalité est vérifiée APRÈS avoir exigé 404** : deux `200` seraient identiques eux aussi, et
l'assertion passerait sur un livrable ouvert. C'est le défaut `T8-1` du LOT 3, qui avait fait passer
mon test de limitation de débit.

**Aucun `403`, et ce n'est pas un oubli** : la matrice §5 ne distingue aucun rôle sur cette ressource.

---

## 5. « Aucune permission locale n'est transférée », au niveau que `T2` atteint

Le critère de la fiche l'exige « prouvé sur une entité où la personne n'a aucun rôle ». À `T2`,
**aucune route ne lit de permission** — c'est `T9`. Ce qui est prouvable, et prouvé :

> la réponse est **identique** que l'appelant appartienne à l'entité ou non, statut, corps et
> en-têtes comparés.

Un test crée deux personnes — une avec une appartenance active dans l'entité, une sans aucune — et
exige l'égalité. **Le contraire serait un défaut silencieux** : une réponse enrichie pour un membre
laisserait le frontend déduire l'appartenance depuis une lecture que la matrice veut identique pour
tous. Ce test ferme aussi la porte à un filtrage introduit plus tard « pour bien faire ».

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest (674 + 9), **156** Vitest (90 `ui`, **49 `web`**, **17 `contracts`**) |
| `make entites-check` | **code 0** — **13 contrôles** (10 + 3), à travers Caddy en HTTPS, **dans la CI** |
| `make residu-check` | **code 0** — 23 tables, **0 ligne avant**, aucun résidu |
| `make ecrans-check` | **code 0** — et il **annonce** le chemin paramétré qu'il écarte |
| `api-check` `web-check` `sessions-check` `csrf-check` `evenements-check` | **code 0** pour les cinq |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

### Les témoins négatifs, tous exécutés

| Témoin | Attendu | Observé |
|---|---|---|
| filtre de résolution retiré, **requête valide** | les 3 égalités de 404 échouent | **exactement 3**, zéro erreur SQL, 19 autres passent |
| le refus **distingue** non-active et inconnue (403 / 404) | les 3 égalités échouent | **exactement 3** |
| filtre retiré **sur le conteneur reconstruit** | `entites-check` échoue | **1 contrôle sur 13**, et il **nomme** : `['draft -> 200', 'suspended -> 200', 'archived -> 200']` |
| réponse tardive de l'entité quittée | l'écran reste sur la nouvelle | Paris reste affiché, Bordeaux n'apparaît pas |

---

## 7. Quatre défauts, tous dans mon travail

**`T2-1` — mon nettoyage de test était incomplet, et la base l'a dit.** Le test « appartenir ou non ne
change rien » insère une `entity_membership` ; la suppression de `person` a rendu
`ForeignKeyViolation` sur `fk_entity_membership_person_id_person`. **Septième occurrence de cette
classe dans le projet** (§7.30).

**`T2-2` — et la conséquence a été bien plus large que l'erreur.** Le nettoyage est **une seule
transaction** : son échec l'a **entièrement annulée**, si bien que 14 lignes sont restées commitées.
Au run suivant, **23 tests d'intégration du LOT 2 ont échoué** — `test_appartenance.py` et six autres
— parce qu'ils comptent `entity_membership` **en absolu** dans une transaction en rollback, ce qui ne
vaut que sur une base propre.

> **Aucun de ces 23 messages ne nommait la cause.** Ils disaient « assert 3 == 2 ». C'est `make
> residu-check` qui l'a dite, en annonçant « **14 ligne(s) avant** » — le contrôle posé en `T12` du
> LOT 3 pour exactement cette classe. Il a fonctionné.

Les 14 lignes ont été **nommées avant d'être supprimées** — toutes portaient mon marqueur — et
`residu-check` annonce désormais « 0 ligne avant ».

**`T2-3` — mon test cherchait un texte présent DEUX fois.** `getByText(/eXalt Bordeaux/)` trouvait le
titre **et** le message : le test échouait sur un livrable correct. Corrigé en ciblant le **rôle**
`heading`, ce qui est plus exact **et** prouve davantage — le §9.2 étape 4 demande un « affichage
clair de l'entité consultée ».

**`T2-4` — deux fois `mypy` strict, et deux fois la même leçon.** `Entity.__table__.c.code.type.length`
ne passe pas : `TypeEngine` n'a pas cet attribut. La tentation était `or 64`, qui aurait satisfait
`mypy` et donné **un nombre qu'on ne peut pas tenir** — si la colonne cessait d'être une chaîne
bornée, la borne silencieuse deviendrait une invention. La dérivation **échoue bruyamment** à la
place, et le test exige `isinstance(String)` plutôt qu'un `cast` qui mentirait.

**Et un défaut évité de justesse, côté TypeScript.** `let repondreBordeaux: (() => void) | null = null`
assigné dans une fermeture : TypeScript restreint à `null` et refuse l'appel. Un `!` aurait menti sur
ce qu'on sait ; une **fonction inerte** dit la vérité — si la fermeture n'a pas tourné, l'appel ne
fait rien et le test échoue sur son assertion, pas sur un plantage.

---

## 8. Un contrôle que mon changement a rendu inexact, et rendu exact

`verifier-ecrans.py` tire **littéralement** toutes les valeurs de `CHEMINS`. Mon `/entites/:code` y
serait entré comme une adresse — et aurait rendu **200** par le repli SPA, donc un `ok` obtenu pour
une raison sans rapport avec le critère (§7.0, quatrième proposition).

Il écarte désormais les chemins **paramétrés** — le `:` est la grammaire de React Router, pas une
heuristique sur du texte — **et il annonce ce qu'il a écarté** :

```
info     1 chemin(s) parametre(s) ecarte(s) : /entites/:code
         ce ne sont pas des adresses. `make entites-check` les eprouve
         avec un code reel.
ok       8 chemins servis en `text/html` avec le point de montage
```

Taire l'exclusion aurait laissé croire davantage que ce qui est vrai — §7.20.

---

## 9. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **l'entité visible sur toutes les pages** | `T3`. Ici elle est le titre de la seule page qui existe |
| **la liste nationale d'où l'on choisit** | `T6`. `T2` livre le mécanisme, pas l'écran de sélection |
| **le changement d'entité de bout en bout** | `T8`. Les cinq règles du §23.3 y seront toutes exigibles |
| **« recharge les permissions »** (§23.3) | aucune route ne lit de permission avant `T9` |
| **un 401 traité par une redirection** | le cahier veut des « route guards **uniquement ergonomiques** ». Les disperser dans chaque page serait le contraire ; `T9` posera la règle en un seul endroit |
| **la carte de France** | `T7`. `entity` ne porte **ni latitude ni longitude** — le seul point du §8 qui reste ouvert |

---

## 10. Ce que la suite devra savoir

1. **le §8 de la fiche n'a plus qu'UN point ouvert**, la carte. L'autre est fermé par le cahier ;
2. **les tests du LOT 2 comptent `entity_membership` en ABSOLU.** Tout test qui **commite** une ligne
   dans une table partagée doit la nettoyer, et son nettoyage est **une seule transaction** : un ordre
   fautif l'annule entièrement. `make residu-check` est le garde-fou, et il nomme le nombre de lignes
   présentes **avant** la suite ;
3. **`make entites-check` exige que le conteneur porte le code du dépôt** — `make code-refresh` puis
   `make code-check` avant de conclure quoi que ce soit (§7.28) ;
4. **pour obtenir l'appelant dans une route**, employer la forme à défaut d'argument avec
   `noqa: B008`, et **jamais** `Annotated[...]` : le piège est mesuré au §5 du compte rendu de `T1` ;
5. **`cheminEntite` lève sur un code vide.** Sans ce refus elle rendrait `/api/v1/entities/`, que
   l'API sert comme **la liste** : un 200 avec toutes les entités au lieu d'un 404.
