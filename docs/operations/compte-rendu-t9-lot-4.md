# Compte rendu — LOT 4, sous-étape `T9`

**L'affichage conditionnel, et le résiduel qu'on nomme au lieu de l'inventer**
**Story :** `MVP-L04-US005` · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-553` · **Écart consigné :** `ECART-046`
**Migration produite :** **aucune**

---

## 1. Le §8.2 ne dit pas quelles permissions, et le §20 de la matrice le dit

Le cahier §8.2 écrit « **Administration, uniquement selon les permissions** ». Lesquelles ? Il ne le
dit pas. Le §20 de la matrice s'appelle « **Rôles, responsabilités et comptes administrateurs** », et
**son tableau donne une colonne à trois rôles** : `ESM`, `ADM-E`, `SUPER`.

C'est la section dédiée que le §7.29 apprend à chercher, et elle ferme la question sans rien inventer.

> **`ESM` est le rôle qu'on perdrait.** L'intuition dit « administrateur d'entité et
> super-administrateur ». Le §20 met l'ESM dans le tableau et lui donne **quatre actions
> d'attribution que `ADM-E` n'a pas** — affecter un DSM, affecter un ESM, affecter ou remplacer un
> Booster, affecter un responsable de bureau. Écrire deux rôles aurait masqué le menu à celui qui en
> a le plus besoin.
>
> **Et aucune des trois colonnes n'est vide** : les trois partagent « consulter l'historique des
> rôles ». Aucune n'est donc à retirer.

---

## 2. La liste vit dans le manifeste, parce que je l'avais écrite deux fois

Ma première version déclarait `ROLES_ADMINISTRATION` dans `apps/web/src/routes.ts` **et** dans
`apps/api/tests/test_garde_de_role.py`. Deux dérivations du **même** §20, dans deux langages, **sans
rien pour les confronter**.

C'est §7.27, et la parade existait déjà : `DEC-492` a posé le manifeste
`packages/contracts/src/contrat-api.json` comme **source unique lue par TypeScript et par Python**.
La liste y vit désormais, avec sa dérivation écrite à côté de la valeur.

**Et deux garde-fous l'y maintiennent :**

- `make cadre-check` **interdit** qu'un rôle d'administration apparaisse en littéral dans le
  frontend — et les codes cherchés sont **dérivés du manifeste**, jamais recopiés dans le contrôle ;
- le test Python **convertit** les codes du manifeste en `RoleDeLaMatrice`, ce qui fait lever un code
  inconnu au lieu de rendre la garde inerte en silence.

---

## 3. Le prédicat de visibilité était dupliqué depuis `T4`

`T4` avait écrit, **deux fois**, la même décision sous forme de `if` sur la clé de la rubrique — une
fois dans `NavigationPrincipale.tsx`, une fois dans `BarreMobile.tsx`.

Deux copies divergent, et la conséquence aurait été visible : « Administration » dans le menu et pas
dans la barre, ou l'inverse. Le prédicat vit maintenant en **un seul exemplaire**, dans `routes.ts`,
et `make cadre-check` **interdit à tout composant de comparer une clé de rubrique** — les clés
conditionnelles étant, là aussi, dérivées de `RUBRIQUES`.

**Un test attrape l'oubli qui serait silencieux :** une septième rubrique conditionnelle ajoutée sans
branche dans le prédicat retomberait sur `return rubrique.condition === undefined`, donc serait
masquée **pour toujours**, y compris au super-administrateur, sans que rien ne le dise.

---

## 4. « Mon onboarding » est masqué pour tout le monde, et ce n'est pas un oubli

Le §8.2 conditionne la rubrique à « **lorsqu'un parcours actif existe** ». Le schéma ne porte
**aucune** table de parcours ni de fiche d'arrivée : elles appartiennent aux LOTS 7 et 8.

La condition est donc **trivialement fausse**. Ce n'est pas une invention : c'est l'évaluation
correcte d'une condition sur un domaine vide. Et ce n'est pas un `false` en dur qu'on oublierait —
`UN_PARCOURS_ACTIF_EST_POSSIBLE` est **épinglé par un test**, si bien que le lot qui créera les
parcours devra le changer **délibérément**. §7.32 : un test est un meilleur véhicule qu'un
commentaire.

---

## 5. Le garde-fou d'API, et les deux vérifications du §2.6 qui ne s'appliquent pas

Le §2.6 exige de chaque requête sensible **huit** vérifications. `exiger_un_role_dans_l_entite` en
fait **six**, et **nomme les deux autres** plutôt que de les laisser croire (§7.20) :

| § | Vérification | État |
|---|---|---|
| 1 | l'identité de la personne | **faite** — `exiger_une_session`, chemin unique du projet |
| 2 | l'état actif du compte | **faite**, indirectement : `T9` du LOT 3 révoque au départ, donc un compte non actif n'a pas de session valide |
| 3 | l'entité principale | **faite** — `entite_principale` |
| 4 | l'entité actuellement consultée | **faite** — lue du chemin, résolue **active** |
| 5 | les responsabilités actives | **faite** — `period @> instant`, jamais `ends_at IS NULL` |
| 6 | le périmètre exact de la ressource | **ne s'applique pas** : ce lot n'expose aucune ressource au-delà de l'entité |
| 7 | l'état de la ressource | **faite** — une entité non active rend 404 |
| 8 | contraintes métier supplémentaires | **ne s'applique pas** : le lot est en lecture seule |

**Le 403 est choisi contre le 404, et le motif compte.** Un 404 dirait « cette entité n'existe pas »,
ce qui est **faux** : l'appelant la consulte légitimement, il y a les droits `EMP`. Et cela ne fuite
rien — la matrice §5 donne la lecture de l'entité aux **huit** rôles authentifiés. Le 404 reste
réservé aux entités non actives, comme partout depuis `T2`.

**Le motif du refus ne sort pas.** Distinguer « vous n'êtes pas ESM » de « vous n'êtes pas dans votre
entité principale » serait un oracle : on apprendrait, en changeant d'entité, où se trouvent les
administrateurs. Un test l'exige, sur **cinq** termes interdits.

---

## 6. Le résiduel a été arbitré, et il est nommé — `ECART-046`

**Le critère de `T9` demande « un appel direct à la route refusé par l'API ». Le lot n'a aucune route
métier à refuser.** Mesuré : ses trois routes — `/entities`, `/entities/{code}`,
`/entities/{code}/permissions` — sont ouvertes aux huit rôles authentifiés par la matrice §5, et le
§9.4 écarte « aucun écran d'administration ».

Le seul candidat était « consulter l'historique des rôles », dernière ligne du §20 et seule action
que les trois rôles partagent. **La question a été posée à Jonathan** — c'était une décision de
périmètre, pas une décision technique — et il a arbitré de **laisser le garde-fou en attente**.

**Ce qui est donc prouvé, et ce qui ne l'est pas :**

| Prouvé | Non prouvé |
|---|---|
| le refus, par **12 tests** sur une vraie application FastAPI, avec de vrais codes HTTP | **la traversée de Caddy** pour le refus par rôle |
| le masquage, par **23 tests** frontend, dans les **deux** sens | — |

C'est exactement ce que `T9` du **LOT 3** a fait avec `exiger_un_scope` : livré, prouvé sur une
application jetable, et nommé sans consommateur. Le premier consommateur réel sera le LOT 5, et son
contrôle de stack devra prouver le refus **à travers Caddy**.

---

## 7. Défauts et corrections

| Défaut | Ce qui l'a révélé |
|---|---|
| `T9-1` | **ma fixture de test commitait dans une fixture à rollback.** Ces tests émettent de vraies requêtes HTTP, donc l'API lit sur une **autre** connexion : il faut commiter. Le premier run a laissé ses lignes, le second a échoué sur `code_unique` avec un message qui ne nommait pas la cause. **Huitième occurrence de la classe du §7.30.** Nettoyage désormais explicite, **dérivé du préfixe**, et **vérifié** — la fixture échoue si un résidu subsiste |
| `T9-2` | **la session était ouverte APRÈS le commit**, donc invisible à l'autre connexion : le garde rendait **401** au lieu de **403**. L'erreur s'est nommée elle-même parce que les deux refus sont distincts et que le test les distingue — c'est pour cela que l'ordre des refus est testé séparément |
| `T9-3` | **`raise_server_exceptions` se lit à la CONSTRUCTION** de `TestClient` : le poser après coup n'a aucun effet, et le test du garde-fou de montage échouait pour cela. §7.10 |
| `T9-4` | **mon assertion cherchait `/refus[ée]/i` et échouait sur ma propre phrase** — « c'est l'API qui refuse les actions non autorisées ». Un contrôle trop large refuse du texte correct, §7.25. Rendue exacte : elle porte sur le **verdict**, pas sur le mot |
| `T9-5` | **l'apostrophe typographique.** Le JSX emploie `&rsquo;`, donc le texte rendu porte `’` et une assertion écrite avec `'` échouait sur un livrable correct |
| `T9-6` | **deux `getByRole` ambigus**, et l'application avait raison dans les deux cas : « Administration » est dans le menu **et** dans la barre, et il y a **deux** `role="status"` — la mention du §5.1 et l'explication de la rubrique. Mes assertions ont été précisées, pas l'application |

**Cinq sur six sont dans mes propres tests**, et le sixième dans une fixture. C'est la forme la plus
insidieuse : on croit avoir prouvé.

---

## 8. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **709**, dont 12 nouveaux dans `test_garde_de_role.py` |
| Vitest | **220** — 90 `ui`, **113** `web`, 17 `contracts` |
| `make cadre-check` | **23 contrôles**, 0 échec — 21 avant `T9` |
| `make cadre-temoin` | **13 motifs** exigés et nommés — 11 avant |
| `make residu-check` | **0** — « 23 tables comptées, **0 ligne(s) avant** », donc la nouvelle fixture ne laisse rien |
| `make permissions-check` · `entites-check` | **0** · **0** |
| Endpoints du contrat | **13**, inchangé — `T9` n'en ajoute aucun |
| Migration | **aucune** |

---

## 9. Ce que `T9` laisse à la suite

- **`T10`** — les états d'erreur et la perte de connexion, `US006`. Le critère nomme un piège précis :
  « un `fetch` qui échoue **après l'envoi** n'affiche **jamais** “sauvegardé” ». Ce lot étant en
  lecture seule, il n'y a rien à sauvegarder : c'est donc `T10` qui devra dire ce que ce critère
  signifie ici, et le §7.29 s'appliquera — chercher la section dédiée avant de décider ;
- **au LOT 5**, la première route métier écrivante devra porter `exiger_un_role_dans_l_entite`, et
  son contrôle de stack devra prouver le refus **à travers Caddy** — c'est la seule chose que
  `ECART-046` laisse ouverte. Les deux vérifications du §2.6 marquées « ne s'applique pas » devront
  alors être ajoutées ;
- **et une chose à ne pas défaire** : le prédicat de visibilité et la liste des rôles ont chacun **un
  seul exemplaire**, tenus par `make cadre-check`. Les deux avaient déjà été dupliqués une fois.
