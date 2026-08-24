# Fiche de lot — LOT 5

**Collaborateurs, profils et organisation**
**Ouvert par :** Jonathan, le 24 août 2026 (`DEC-558`)
**Porte de sortie :** `G5`
**Découpage :** douze sous-étapes, **validé le 24 août 2026 avant qu'une ligne ne soit écrite**
**Avancement :** **`T1` terminée** le 24/08/2026. Onze sous-étapes restantes

---

**Tous les nombres de cette fiche sont DÉRIVÉS, pas recopiés.** C'est la classe d'erreur la plus
fréquente du projet — `ECART-021`, rejouée une douzaine de fois — et trois fois au LOT 3 c'est le §8
d'une fiche qui a annoncé faux. Chaque grandeur ci-dessous est accompagnée de sa source.

---

# 1. Ce que le lot doit produire

## 1.1 Les huit stories, comptées dans le backlog

```bash
grep -c 'MVP-L05-US' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| ID | Priorité | Taille | Résultat attendu |
|---|---|---|---|
| `US001` | `P0` | L | consulter un trombinoscope **paginé** — 25, 50 ou 100 |
| `US002` | `P0` | L | rechercher et filtrer — six axes combinables, **300 ms** |
| `US003` | `P0` | M | une **carte retournable accessible** — clic, toucher, clavier |
| `US004` | `P0` | L | consulter une **fiche profil complète** |
| `US005` | `P0` | L | gérer une **photo facultative avec autorisation** |
| `US006` | `P0` | **XL** | **modifier un profil dans son périmètre** |
| `US007` | `P0` | L | **archiver et restaurer** un profil |
| `US008` | `P1` | M | consulter l'**historique organisationnel** |

**Sept `P0` et une `P1`.** `US006` est la seule `XL` du MVP à ce jour, et c'est cohérent : elle porte
à elle seule les quinze actions du §6.1 de la matrice.

## 1.2 Les **sept** critères de sortie de la roadmap

1. les miniatures sont **inférieures à la cible de 100 Ko** ;
2. **aucune photo non autorisée** n'est publiée ;
3. les permissions suivent **intégralement** la matrice ;
4. les recherches respectent l'objectif de performance **avec 5 000 profils** ;
5. **aucune requête N+1 critique** n'est détectée ;
6. les **affectations structurantes** ne sont jamais écrasées ;
7. Jonathan valide le trombinoscope et les profils.

> **Sept, et le compte est DÉRIVÉ, non supposé.** J'ai d'abord écrit « huit » de tête, par symétrie
> avec les huit stories — puis la commande a dit sept. C'est exactement `ECART-021`, attrapé avant
> d'être écrit :
>
> ```bash
> awk '/^# LOT 5/,/^# LOT 6/' docs/product/ROADMAP_MVP_V1_V2_EXALT.md \
>   | awk '/Critères de sortie/,/^## Dépendances/' | grep -c '^- '
> ```

---

# 2. Ce que le corpus tranche déjà, et qu'il ne faut pas réinventer

| Question | Où c'est tranché |
|---|---|
| qui peut faire quoi sur un profil | **matrice §6.1** — quinze actions × huit rôles — et **§6.2**, huit règles complémentaires |
| ce qu'une photo exige | **cahier §21.2** : « facultative ; autorisation explicite ; retrait possible ; **avatar neutre sinon** » |
| qui gère les médias | **matrice §12.1**, tableau MVP — six rôles, sept actions |
| les tables de photo et de média | **modèle §12.2** `photo_authorization`, **§16.1** `media_asset`, **§16.2** `media_variant`, **§16.3** `media_usage` |
| la pagination | **cahier §18.2** : « 25 par défaut ; options 25, 50 et 100 ; **maximum 100** » |
| hors de son entité principale | **matrice §5.1** — déjà implémenté au LOT 4, et il s'applique ici à chaque route |

## 2.1 Le piège de la matrice §6, mesuré avant de commencer

**`OFFICE` n'a AUCUN droit sur les profils.** Sa colonne du §6.1 est **entièrement à tiret**, et le
§6.2 le dit en clair : « un responsable de bureau n'obtient **aucun** droit général sur les profils du
seul fait de sa responsabilité de bureau ».

> C'est le piège **symétrique** de `T9` du LOT 4, où `ESM` était le rôle qu'on perdait en écrivant
> « administrateur d'entité et super-administrateur ». Ici l'erreur serait d'**ajouter** `OFFICE`
> parce qu'il figure dans les autres tableaux de la matrice. **Chaque tableau a ses propres
> colonnes**, et il faut lire celui de la ressource.

**Et `EMP` a un droit, un seul, qui surprend** : « enregistrer l'autorisation photo — **Soi lors de
l'action** ». Un employé sans aucune responsabilité peut donc autoriser **sa** photo. Le retirer
serait plus restrictif que la matrice, ce que le §7.20 interdit.

---

# 3. Le découpage — douze sous-étapes

**L'ordre suit les dépendances du backlog** : les tables d'abord, la lecture avant l'écriture, les
écrans **après** les routes qu'ils consomment — comme `T11` du LOT 4, qui arrivait après les écrans
employant ses composants.

| | Objet | Story | Critère de sortie |
|---|---|---|---|
| ~~**`T1`**~~ | ~~**Les trois tables de média et d'autorisation de photo**, et le §30.12 reclassé~~ **TERMINÉE le 24/08/2026.** `DEC-559`. **DEUX SECTIONS DU MODÈLE ONT DÛ ÊTRE CONFRONTÉES** : le §16.2 ne donne pas d'`entity_id` à `media_variant`, mais le §25.3 prescrit le couple `(id, entity_id)` pour toute table **locale** — et sans lui la clé serait **simple**, donc une variante pourrait pointer l'actif d'une autre entité. `isolation-check` compte désormais **neuf** clés composites. **`photo_authorization` reste globale**, et la dérivation du contrôle le confirme. **Un déclencheur rend `deleted` terminal** — le §24.3 le dit par son diagramme, et un `CHECK` ne peut pas l'exprimer. **Une seule unicité, dérivée** du §16.2 ; **aucune** sur `photo_authorization`, et un test **fige l'absence** pour que `T6` la traite. **La borne « photo 10 Mo » n'est PAS en base** : une photo est une image, la distinction est un **usage**, et `media_usage` est reportée. **Deux garde-fous du LOT 2 ont fait leur travail** : `noms_de_contraintes_trop_longs` a attrapé un nom de **66 caractères** que PostgreSQL aurait tronqué en silence, et `TABLES_DECLAREES` a échoué sur les trois tables nouvelles — c'est son objet. **729 tests** dont 20 nouveaux, migration **`0014`** rejouable sur base vide avec une signature **identique**. Compte rendu : [`compte-rendu-t1-lot-5.md`](compte-rendu-t1-lot-5.md) | — | ☑ |
| **`T2`** | **Le trombinoscope en lecture** : route paginée 25/50/100 | `US001` | les trois tailles · le maximum de 100 **refusé au-delà** · **aucune donnée non autorisée** rendue |
| **`T3`** | **Recherche et filtres** — six axes combinables | `US002` | 300 ms · performance **mesurée sur 5 000 profils** · **aucun N+1**, compté et non supposé |
| **`T4`** | **La fiche profil** et les règles de visibilité | `US004` | chaque champ visible **ou** masqué selon la matrice, **les deux sens** testés |
| **`T5`** | **Les miniatures** : variantes et cible 100 Ko | `US005` | **< 100 Ko mesuré** · la photo **originale jamais servie** dans la liste |
| **`T6`** | **L'autorisation de photo** : sans elle, avatar neutre | `US005` | aucune photo non autorisée publiée · le **retrait** effectif |
| **`T7`** | **L'écriture dans son périmètre** — la matrice §6 exigible | `US006` | un DSM modifie **son** consultant · **refusé** sur un autre · `OFFICE` **refusé partout** |
| **`T8`** | **Archivage et restauration** | `US007` | l'archivage **révoque** et clôture · la restauration suit les rôles validés |
| **`T9`** | **L'historique organisationnel** | `US008` | les périodes lisibles **sans** exposer l'audit technique |
| **`T10`** | **Le trombinoscope à l'écran** : liste, pagination, **carte retournable** | `US003` | recto/verso au **clic, toucher ET clavier** · alternative `reduced-motion` |
| **`T11`** | **La page de profil à l'écran**, et les composants consolidés | `US003`, `US004` | chaque composant livré est **employé** · contraste mesuré |
| **`T12`** | **Recette, reclassements du §30 et checklist `G5`** | — | les **sept** critères de sortie prouvés |

**Une pull request par sous-étape**, un compte rendu, et les registres tenus **dans la même pull
request** que le travail.

> **`T1` NE CRÉE QUE TROIS TABLES SUR QUATRE, ET C'EST UN ARBITRAGE.** `media_usage` (§16.3) ne sert
> qu'à la médiathèque **V1** — « voir les usages », « détecter les médias inutilisés », matrice §12.2
> — donc la créer maintenant serait une table **sans consommateur**, ce que `T10` du LOT 1 et
> `DEC-537` refusent. Elle est **nommée comme reportée**, pas oubliée.

---

# 4. Ce que ce lot NE fera PAS

**Au-delà de son périmètre :** aucun cercle ni bureau créé ou modifié (LOT 6) · aucun contenu éditorial
(LOT 6) · aucune fiche d'arrivée ni onboarding (LOT 7) · aucun événement (LOT 8) · aucun import CSV
(LOT 9) · aucun export (LOT 11) · aucune médiathèque V1 · **aucune purge définitive**, réservée au
super-administrateur et rattachée au LOT 12.

**Les interdits absolus, qui ne dépendent d'aucun lot :** aucun contournement de l'authentification ·
aucun jeton ni mot de passe en clair · aucun jeton dans `localStorage` · **aucune donnée réelle de
collaborateur, aucune photo réelle** · aucune modification d'une migration déjà appliquée ni des cinq
documents de cadrage · aucune exposition de PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur
`127.0.0.1` · aucune référence d'image par `latest` seul · ni Kubernetes, ni PWA, ni hors ligne, ni
Entra ID · aucune ligne du prototype historique.

---

# 5. Ce qui est livré et attend son premier consommateur

| Livré | Où, et ce que ce lot doit en faire |
|---|---|
| **`exiger_un_role_dans_l_entite`** | `app/permissions/dependances.py`, LOT 4 `T9`. Il fait **six** des huit vérifications du §2.6 ; les deux qui manquent — « le **périmètre exact de la ressource** » et « les contraintes métier supplémentaires » — ne s'appliquaient pas à un lot en lecture seule. **Elles s'appliquent ici**, et `ECART-046` attend que ce lot prouve le refus **à travers Caddy** |
| **le jeu de 5 000 profils** | `make jeu-de-donnees` — 25 entités, 5 000 profils, LOT 2 `T12`. C'est **exactement** ce que le quatrième critère de sortie réclame |
| **`exiger_un_scope`** | LOT 3 `T9`, toujours sans consommateur. Les comptes de service liront des profils au LOT 9 |
| **le bucket MinIO** | `onboarding-dev-media`, créé par `make up` depuis `DEC-477`, et **jamais employé**. `T5` sera son premier consommateur |

---

# 6. Les risques propres à ce lot

| Risque | Ce qui le tient |
|---|---|
| **la matrice §6 est dense** — quinze actions, huit rôles, huit règles complémentaires | `T7` doit en faire un **contrôle** dérivé du document, jamais une liste recopiée (§7.27). Le LOT 4 l'a fait pour trois rôles ; ici il y en a quinze × huit |
| **la performance à 5 000 profils** | le jeu existe. `T3` doit mesurer la **durée**, qui est la grandeur du critère, et **rapporter** le plan — exiger « aucun Seq Scan » exigerait le contraire de la performance sur des tables de cette taille (§7.26) |
| **le N+1** | il se **compte**, il ne se suppose pas. `T3` doit compter les requêtes émises, et confronter ce compte à un attendu |
| **une photo est une donnée personnelle** | aucune photo réelle, jamais. Le jeu de données est fictif, et `T5` devra engendrer ses images |
| **les affectations structurantes écrasées** | sixième critère de sortie. Le socle du LOT 2 porte des **relations historisées** : une modification **clôture** et ouvre, elle n'écrase pas. `T7` doit l'exiger, et le §24.4 du modèle le dit |

---

# 7. Trois leçons du LOT 4 qui s'appliquent directement

**`§7.29` — cherche la section dédiée avant de décider.** Elle a servi quatre fois au LOT 4, dont deux
fois où un point annoncé « ouvert » était déjà tranché ailleurs. Ici les sections dédiées sont la
matrice **§6** et **§12**, le cahier **§21.2** et **§18.2**, et le modèle **§12.2** et **§16**.

**`§7.35` — quand une propriété n'est observable par aucun contrôle, change le code.** Le LOT 4 l'a
payée sur l'ordre d'une liste de rôles. Ici la même question se posera sur l'ordre du trombinoscope :
un `ORDER BY` sur un seul champ non unique laisse PostgreSQL libre, et la pagination devient
**non déterministe** — deux pages pourraient omettre ou répéter une personne.

**`§7.27` — une liste recopiée vieillit au premier ajout.** Neuf occurrences au LOT 4, dont trois dans
mes propres contrôles et une **dans le manifeste du contrat**. La matrice §6 est le plus gros
gisement de listes du projet.

---

# 8. Ce que le corpus NE tranche PAS — **deux points, et ils sont nommés**

## 8.1 `ECART-012` — « intercontrat » sur une fiche de direction générale

**Ouvert, instruit, et il attend Léa.** `professional_status_assignment` n'offre que **deux** valeurs,
que le modèle validé écrit ; pour une catégorie `dg`, `intercontrat` est la seule possible. Le
trombinoscope l'**afficherait**, et cela serait lu comme une erreur.

**Non bloquant pour le lot**, mais il devient **visible** à `T4` et `T10`. Les deux options sont
chiffrées, et la moins coûteuse ne touche pas le modèle : conditionner l'**affichage** à la catégorie.
**`T4` doit donc rendre le statut d'une façon qui laisse ce choix ouvert**, et ne rien inventer.

## 8.2 Le format et la taille exacte des miniatures

Le critère dit « **inférieures à la cible de 100 Ko** ». Le corpus ne donne **ni dimension, ni
format** — mesuré : aucune occurrence de `webp`, `avif`, ni de dimension en pixels dans les cinq
documents de cadrage.

**`T5` devra donc décider, et le motif de chaque valeur devra être mesuré**, non choisi : c'est
exactement la situation de `DEC-491` au LOT 1, où les jetons ont été **relevés** du prototype puis
**recalculés** contre WCAG. Une valeur plausible plutôt que mesurée est ce que le §7.0 interdit.

---

# 9. Traçabilité GitHub

À créer **après validation du découpage** — donc maintenant : un epic `MVP-L05`, **huit** issues pour
les huit stories, et le jalon `G5`.

**Et la routine qui ne change pas :** une pull request par sous-étape, `Closes #N` **ne fonctionne pas
depuis `develop`** (§7.19), donc chaque issue est refermée **à la main** avec ses critères cochés et
leurs preuves.
