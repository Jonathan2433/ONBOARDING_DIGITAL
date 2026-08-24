# Compte rendu — LOT 4, sous-étape `T12`

**Aucun reclassement, et le dire vaut mieux que d'en fabriquer un**
**Story :** — · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-556` · **Écart consigné :** aucun
**Migration produite :** **aucune** — comme les onze sous-étapes précédentes

---

## 1. Le critère demandait des reclassements. Il n'y en a aucun.

La fiche écrit : « les contrôles du §30 qui deviennent acquis le sont **avec un test nommé** ».
J'ai donc commencé par mesurer, et non par chercher lequel reclasser.

```text
make recette-modele-check
  info     12 acquis · 1 partiel · 11 reportes · 1 inapplicable
  --> les 25 controles du §30 sont classes, et chaque acquis nomme un test qui EXISTE
```

**Inchangé.** Et le motif est **structurel**, pas un oubli :

| Les 11 reportés portent sur | Échéance |
|---|---|
| photos et autorisations | LOT 6 |
| onboarding, tâches, réouverture | LOT 7 |
| imports CSV | LOT 9 |
| jobs et idempotence | LOT 10 |
| exports | LOT 11 |
| audit, purge, anonymisation | LOT 12 |

Le §30 du modèle de données énumère des invariants **de données**. Le LOT 4 livre des **écrans et de
la navigation**, et n'a produit **aucune migration** — pas une seule des douze sous-étapes.

> **Fabriquer un reclassement pour cocher le critère aurait produit exactement la même observation
> qu'un vrai acquis**, et c'est ce que le §7.0 interdit. Le contrôle, lui, **échouerait** si un acquis
> cessait de nommer un test qui existe : c'est ce qui rend l'inchangé lisible.

---

## 2. Cinq des six critères de sortie sont mécaniquement prouvés

« Prouvé » veut dire ici : **cela échoue en intégration continue si quelqu'un le casse.** Aucun n'est
coché sur ma parole — chacun renvoie à un contrôle **numéroté** de `cadre-check`, lui-même éprouvé par
`cadre-temoin` sur **15 motifs**.

| # | Critère | Contrôle |
|---|---|---|
| 1 | la liste précède la carte sur mobile | `cadre-check` **23** — l'ordre du **DOM**, et aucun `order` CSS |
| 2 | navigation intégralement utilisable au clavier | `cadre-check` **11, 13, 16, 22** |
| 3 | l'entité active visible sur **toutes** les pages internes | `cadre-check` **8** — les routes internes sont **enfants** de la route de mise en page, liste **dérivée de `App.tsx`** |
| 4 | les menus reflètent les permissions **sans les remplacer** | `cadre-check` **18, 19** + **12 tests** du garde-fou sur de vraies requêtes HTTP |
| 5 | les erreurs réseau n'indiquent jamais à tort qu'une action est sauvegardée | `cadre-check` **20** |
| 6 | **Jonathan valide les parcours de navigation** | sa décision — la démonstration guidée est au §3 de la checklist |

**Le troisième est le plus intéressant, parce qu'il est structurel et non testé.** L'entité n'est pas
« affichée sur chaque page » par discipline : les routes internes sont **engendrées** depuis
`RUBRIQUES` **à l'intérieur** de la route de mise en page, et c'est elle qui porte l'en-tête. Un
oubli exigerait de sortir une route du bloc, ce que le contrôle refuse. C'est le §7.2 — changer de
forme plutôt que promettre de l'attention.

**Et le cinquième nommait un piège**, instruit en `T10` : « n'affiche jamais “sauvegardé” » sur un lot
en **lecture seule**. Le §17.2 l'a résolu — « aucune action n'est déclarée enregistrée **sans
confirmation de l'API** » — et les écritures existent, ce sont celles du LOT 3.

---

## 3. La recette a tourné, et dire sur QUOI est plus utile que dire qu'elle a tourné

| Mesure | Résultat |
|---|---|
| `make images-pin` | épinglée sur **`1850d8d`** |
| `make up-recette` | **8/8 services sains** |
| `make recette-check` | **0 échec** — un e-mail part du conteneur `api` de la recette, son Mailpit passe de 11 à **12**, celui de dev **ne bouge pas** (180 → 180) |
| `make separations-check` | **57 contrôles, 0 échec**, **7 séparations sur 7** |
| révision servie | `{"version":"0.0.0-dev","revision":"1850d8d","environnement":"recette"}` |
| forme servie | l'**artefact bâti**, `/assets/index-CDe_VX_M.js` — et non le serveur Vite |
| routes du portail | `/`, `/statut`, `/connexion`, `/entites/x` → **200** ; `/api/v1/entities` → **401** |
| mémoire des deux stacks | **1 020,3 Mio** sur 7 936 alloués |

> **`1850d8d` EST LA FUSION DE `T8`, ET `T9` À `T11` N'Y SONT PAS.** `make images-pin` épingle sur la
> dernière publication **réussie** ; celle de `T9` était encore en cours au moment de la mesure.
>
> Cette recette prouve donc le **mécanisme** — les sept séparations, l'artefact publié, l'isolement
> des captures d'e-mails — et **pas le contenu complet du lot**. Taire cette nuance aurait laissé
> croire davantage que ce qui est vrai, ce que le §7.20 interdit.
>
> **La recette finale est un geste post-fusion, et il appartient à Jonathan** : publier est une action
> vers l'extérieur, et le §12 dit de ne rien y pousser sans son accord. La commande est écrite,
> prête, au §5 de la checklist.

---

## 4. Ce que `T12` a produit

- **`docs/operations/checklist-validation-G4.md`** — 218 lignes, neuf sections : les six critères avec
  leur contrôle, les contrôles de stack et ce que chacun **refuse**, une démonstration guidée en
  **huit gestes**, les grandeurs **avec la commande qui les produit**, la recette et sa révision, le
  §30 inchangé et pourquoi, ce que le lot **n'a pas fait**, les trois points à connaître, et la
  décision ;
- **`DEC-556`** — les quatre partis de cette sous-étape ;
- la fiche du lot, **les douze sous-étapes barrées**.

**Aucun code.** `T12` ne livre pas de fonctionnalité : elle rend le lot **vérifiable par quelqu'un
d'autre**, ce qui est son objet.

---

## 5. Les grandeurs du lot entier, dérivées

| Grandeur | Valeur au 24/08/2026 |
|---|---|
| tests | **709** pytest, dont **426** d'intégration |
| tests frontend | **235** Vitest — 97 `ui`, 121 `web`, 17 `contracts` |
| cibles `Makefile` | **81** |
| migrations | **13**, tête `0013` — **aucune** au LOT 4 |
| endpoints du contrat | **13** |
| composants du design system | **5**, tous testés **et** employés |
| décisions | **224** |
| écarts | **46** — 34 clos, **9 ouverts**, 3 acceptés. Le LOT 4 en a ouvert **neuf** : sept **clos**, `ECART-045` **ouvert**, `ECART-046` **accepté** |
| défauts nommés au LOT 4 | **19** |
| contrôles de `cadre-check` | **25**, témoin sur **15** motifs |

```bash
uv run pytest -q --collect-only | tail -1
grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile
grep -ohE '`T[0-9]+-[0-9]+`' docs/operations/compte-rendu-t*-lot-4.md | sort -u | wc -l
```

---

## 6. Trois choses que la porte `G4` doit connaître

**`DEP-006` est ouverte, et son échéance était ce lot.** Les jetons de `DEC-491` sont **relevés du
prototype et recalculés** contre WCAG 2.2 AA — deux sources concordantes, donc pas une invention — mais
ce ne sont pas les jetons officiels. Le jour où la charte arrive, `packages/ui/src/jetons.ts` change,
**en un seul endroit**.

**`ECART-045`** — quatre endroits justifient une sélection de cible par « le rechargement à chaud »,
que `T5` du LOT 1 avait **délibérément écarté**. Ce sont les **motifs** à rectifier, pas le livrable :
le §7.17 a mesuré qu'iCloud remplace les **répertoires**, et un conteneur ne re-résout pas la source
d'un montage lié après sa création.

**`ECART-046`** — le garde-fou d'autorisation est prouvé par 12 tests sur une vraie application
FastAPI, **pas à travers Caddy** : le lot n'a aucune route métier à refuser. Le LOT 5 devra le monter
sur sa première route écrivante.

**Et une convergence qui n'est le critère d'aucune sous-étape :** `PageStatut` emploie encore les
classes neutres d'avant `packages/ui`. Elle partage la **logique** avec le portail depuis `T10`, mais
pas le balisage — le même message de copie s'affiche dans **deux habillages**.

---

## 7. Ce que le LOT 5 doit savoir avant de commencer

- **`exiger_un_role_dans_l_entite` attend sa première route.** Il fait **six** des huit vérifications
  du §2.6 ; les deux qui manquent — « le périmètre exact de la ressource » et « les contraintes métier
  supplémentaires » — ne s'appliquaient pas à un lot en lecture seule. Elles s'appliqueront ;
- **la matrice §5.1 est la règle, et elle est déjà implémentée** : hors de son entité principale, une
  personne n'a que `EMP`. Chaque route métier n'aura donc à trancher que sur **sa** ressource, ce que
  le §5.1 dit explicitement ;
- **TanStack Query reste à réexaminer**, et c'est au LOT 5 que son apport serait réel — le §17.3 le
  nomme pour « les données serveur », et deux décisions l'ont écarté faute d'usage. Les mutations
  métier arrivent là ;
- **`make apercu` existe pour regarder l'écran**, et il dit ses deux limites : `make check` échoue tant
  que son décor est posé, et il n'y a **aucun rechargement à chaud**.
