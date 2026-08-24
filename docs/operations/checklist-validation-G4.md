# Checklist de validation — porte `G4`

**Lot :** LOT 4 — portail national, sélection d'entité et navigation
**Préparée le :** 24 août 2026, à la sortie de `T12`
**Destinataire :** Jonathan — c'est lui qui franchit la porte
**Décision attendue :** `DEC-556`

---

**Comment lire ce document.** Chaque affirmation est suivie de **la commande qui la produit**. Rien
n'est recopié : tous les nombres ci-dessous ont été dérivés le 24/08/2026, et c'est la classe d'erreur
la plus fréquente du projet (§7.27, `ECART-021`). **Recompte avant de réutiliser.**

Un point demande ton avis et non une mesure — le sixième critère de sortie. Les cinq autres sont
**mécaniquement prouvés**, ce qui veut dire qu'ils échouent en intégration continue si quelqu'un les
casse.

---

## 1. Les six critères de sortie de la roadmap

> **Les contrôles sont cités par ce qu'ILS DISENT, jamais par leur rang.** Un numéro d'ordre est un
> index recopié : il vieillit dès qu'un contrôle est inséré avant lui, et le lecteur chercherait alors
> la mauvaise ligne. Cherche donc la **phrase** dans la sortie de `make cadre-check` — c'est le §7.27
> appliqué à un document.

| # | Critère | Comment il est tenu | La ligne de `cadre-check` qui le prouve |
|---|---|---|---|
| 1 | « la liste précède la carte sur mobile » | l'ordre du **DOM**, et aucune règle CSS ne les réordonne — un `order` satisferait l'œil et pas la tabulation | `la liste PRECEDE la carte dans le DOM` |
| 2 | « la navigation est intégralement utilisable au clavier » | `:focus-visible` sur les **7** classes interactives, **aucun** `tabIndex` positif, lien d'évitement à cible **focusable**, les **2** replis en `<details>` sans manipulation de focus | `aucun tabIndex positif` · `cible FOCUSABLE` · `repli(s) sont des <details>` · `classes interactives ont une regle` |
| 3 | « l'entité active est visible sur toutes les pages internes » | **structurel** : les routes internes sont **enfants** de la route de mise en page `CadreApplicatif`, et c'est elle qui porte l'en-tête. La liste est **dérivée de `App.tsx`** | `les routes internes sont ENGENDREES depuis RUBRIQUES` |
| 4 | « les menus reflètent les permissions **sans les remplacer** » | le prédicat de visibilité est en **un seul** exemplaire, les **3** rôles viennent du **manifeste** lu par TS *et* Python, et l'API refuse par **403** — 12 tests sur de vraies requêtes HTTP | `le predicat de visibilite est UNIQUE` · `roles d'administration viennent du MANIFESTE` · plus `test_garde_de_role.py` |
| 5 | « les erreurs réseau n'indiquent jamais à tort qu'une action est sauvegardée » | **mécanique** : les états rendant `data-ton='succes'` et les états affectés dans un `catch` doivent avoir une intersection **vide** — 3 écrans à état de succès, 3 avec `catch` | `aucun etat de SUCCES n'est atteignable depuis un catch` |
| 6 | « **Jonathan valide les parcours de navigation** » | **ta décision.** La démonstration guidée du §3 est là pour cela | — |

```bash
make cadre-check && make cadre-temoin
```

```bash
uv run pytest apps/api/tests/test_garde_de_role.py -q
```

> **Le cinquième critère nommait un piège, et le §17.2 l'a résolu.** Ce lot est en **lecture seule** :
> il n'y a rien à sauvegarder. Le cahier écrit « aucune action n'est déclarée enregistrée **sans
> confirmation de l'API** » — et les écritures existent, ce sont celles du LOT 3. C'est sur elles que
> la règle porte, et c'est ce que le contrôle mesure.

---

## 2. Les contrôles de stack, et ce que chacun refuse

| Contrôle | Contrôles internes | Ce qu'il refuse |
|---|---:|---|
| `make entites-check` | 13 | une entité `draft`, `suspended` ou `archived` proposée par le portail ; deux refus qui ne seraient pas identiques |
| `make permissions-check` | 15 | une permission locale **transférée** ; un rôle clôturé ou futur qui accorderait ; une écriture dans les 4 tables de rattachement |
| `make cadre-check` | 25 | tout ce que le §1 énumère, plus : une couleur hors jetons, un composant exporté **sans consommateur**, une largeur fixe en pixels. **Le nombre est dérivé de sa propre sortie**, `--> N controles du cadre applicatif` |
| `make cadre-temoin` | 15 motifs | que `cadre-check` cesse de discriminer |
| `make residu-check` | — | qu'un test laisse une ligne derrière lui |

```bash
make entites-check && make permissions-check && make residu-check
```

**Les cinq sont dans l'intégration continue**, donc bloquants sur chaque pull request.

---

## 3. La démonstration guidée — huit gestes, dans cet ordre

```bash
make up && make apercu
```

`make apercu` imprime l'adresse, l'identifiant et un **mot de passe régénéré à chaque appel**.

1. **connexion** — `https://app.onboarding.localhost/connexion/administrateur`, avec ce que l'aperçu
   a imprimé ;
2. **la page nationale** — `https://app.onboarding.localhost/` : la **liste** des entités actives,
   puis la **carte** en dessous. Sur mobile, la liste est bien **avant** ;
3. **choisir une entité** — un clic, et l'adresse devient `/entites/<code>`. Recharge la page : le
   choix **survit**, parce qu'il vit dans l'adresse ;
4. **l'en-tête** — le nom et la ville de l'entité, sur **toutes** les pages internes, plus la mention
   « Consultation uniquement » puisque le compte de démonstration n'a pas d'entité principale ;
5. **changer d'entité** — le bouton « Changer d'entité », puis l'autre entité. L'en-tête suit, et le
   bouton « précédent » du navigateur ramène à la première ;
6. **le clavier seul** — Tab depuis le haut : « Aller au contenu », le sélecteur, les rubriques, le
   contenu. Chaque arrêt est **visible** ;
7. **les largeurs** — réduis la fenêtre à ~375 px : le menu disparaît, la barre inférieure apparaît,
   et les deux **ne coexistent jamais** ;
8. **une erreur** — coupe le Wi-Fi une seconde : l'écran dit « Hors connexion » et que ce qu'il
   affiche **date d'avant la coupure**. Rebranche : il recharge **seul**.

```bash
make apercu-fin
```

> **`make apercu-fin` avant `make check`.** Les tests d'intégration du LOT 2 comptent `person` et
> `entity` **en absolu** ; l'aperçu doit **commiter** ses lignes pour que le navigateur les voie. Les
> deux ne peuvent pas coexister, et l'outil le dit lui-même en sortie.

---

## 4. Les grandeurs, avec la commande qui les produit

| Grandeur | Valeur au 24/08/2026 | Commande |
|---|---|---|
| tests | **709** pytest, dont **426** d'intégration | `uv run pytest -q --collect-only \| tail -1` |
| tests frontend | **235** Vitest — 97 `ui`, 121 `web`, 17 `contracts` | `make test-frontend` |
| cibles `Makefile` | **81** | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| migrations | **13**, tête `0013` — **aucune** au LOT 4 | `ls apps/api/alembic/versions/*.py \| wc -l` |
| endpoints du contrat | **13** | lire `packages/contracts/src/contrat-api.json` |
| composants du design system | **5**, tous testés **et** employés | `make cadre-check` |
| décisions | **223** | `make docs-check` |
| défauts nommés au LOT 4 | **19** | `grep -ohE '\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-4.md \| sort -u \| wc -l` |

**Le LOT 4 n'a produit aucune migration.** C'est normal et c'est le signe qu'il est resté dans son
périmètre : il livre des écrans et de la navigation sur le socle du LOT 2.

---

## 5. La recette — FAITE le 24/08/2026, et sur quelle révision

| Mesure | Résultat |
|---|---|
| `make images-pin` | épinglée sur **`1850d8d`** — la dernière publication réussie au moment de la mesure |
| `make up-recette` | **8/8 services sains** |
| `make recette-check` | **0 échec** — un e-mail part du conteneur `api` de la recette, son Mailpit passe de 11 à **12**, et celui de dev **ne bouge pas** (180 → 180) |
| `make separations-check` | **57 contrôles, 0 échec**, **7 séparations sur 7** |
| révision réellement servie | `{"version":"0.0.0-dev","revision":"1850d8d","environnement":"recette"}` |
| forme servie | l'**artefact bâti** — `/assets/index-CDe_VX_M.js`, et non le serveur Vite |
| les routes du portail | `/`, `/statut`, `/connexion`, `/entites/x` → **200** ; `/api/v1/entities` → **401** sans session |
| mémoire des deux stacks | **1 020,3 Mio** sur 7 936 alloués |

> **CE QUE CETTE RECETTE N'EXERCE PAS, ET IL FAUT LE SAVOIR.** `1850d8d` est la fusion de **`T8`**.
> Les sous-étapes **`T9`, `T10` et `T11`** — affichage conditionnel, états d'erreur, design system —
> **ne sont pas dans ces images**. Le mécanisme de recette est prouvé ; le **contenu complet du
> LOT 4** ne l'est pas encore en recette.
>
> **La recette finale est un geste POST-FUSION**, et il t'appartient : publier suppose de pousser vers
> l'extérieur, ce que je ne fais pas sans ton accord (§12). Une fois `T12` fusionnée et
> `images.yml` passé :
>
> ```bash
> make images-pin && make up-recette && make recette-check && make separations-check && make down-recette
> ```

---

## 6. Les contrôles du §30 : **aucun reclassement**, et c'est mesuré

Le critère de `T12` dit « les contrôles du §30 qui deviennent acquis le sont **avec un test nommé** ».
**Aucun ne devient acquis**, et le dire vaut mieux que d'en fabriquer un.

```bash
make recette-modele-check
```

| Classe | Nombre |
|---|---:|
| acquis | **12** |
| partiel | **1** — §30.4, une règle de **processus** que la base ne peut pas porter |
| reportés | **11** |
| inapplicable | **1** — §30.8, `ECART-031` |

**Le motif est structurel** : le §30 du modèle de données énumère des invariants **de données** —
photos, onboarding, imports, jobs, audit, purge, anonymisation, exports. Le LOT 4 livre des **écrans
et de la navigation**, et n'a produit **aucune migration**. Il n'y a donc rien à reclasser, et
`recette-modele-check` **échouerait** si un acquis cessait de nommer un test qui existe.

---

## 7. Ce que le lot n'a PAS fait, et qu'il ne faut pas croire acquis

- **aucun écran métier de collaborateur, de cercle ou d'événement** : les rubriques existent, sont
  atteignables au clavier, et **disent quel lot apportera leur contenu**. C'est délibéré — un lien qui
  tombe en 404 rendrait la navigation « simulée » plutôt que prouvée ;
- **aucune écriture métier.** Le lot est en **lecture seule**, et c'est ce qui a rendu le cinquième
  critère de sortie délicat à instruire ;
- **aucun écran d'administration.** Seule sa **visibilité conditionnelle** est ici, et le garde-fou
  d'API qui la double **n'a pas encore de route à garder** — `ECART-046` ;
- **`axe` et Playwright ne sont pas installés** : ils appartiennent au LOT 12. Le débordement
  horizontal réel a donc été mesuré **dans un vrai navigateur**, à 320, 375, 390, 768, 1 280 et
  1 920 px, et consigné aux comptes rendus — pas par un contrôle automatisé ;
- **la carte de France est un provisoire assumé** : tracée à la main, approximative, **décorative**.
  Remplaçable en une ligne quand `DEP-006` livrera.

---

## 8. Trois choses à connaître avant de valider

**`DEP-006` est OUVERTE, et son échéance était ce lot.** « Charte, logo et typographie officiels
exploitables », Léa / eXalt. Les jetons de `DEC-491` sont **relevés du prototype et recalculés** contre
WCAG 2.2 AA — deux sources concordantes, donc pas une invention — mais ce ne sont pas les jetons
officiels. Le jour où la charte arrive, c'est `packages/ui/src/jetons.ts` qui change, **en un seul
endroit**.

**`ECART-045` reste ouvert, et volontairement.** Quatre endroits du dépôt justifient la sélection de
`target: developpement` par « le rechargement à chaud », que `T5` du LOT 1 avait **délibérément
écarté**. Le conteneur `web` a **0 montage**, mesuré. La sélection de cible reste **nécessaire** pour
un autre motif — la forme servie, que les contrôles distinguent — donc ce sont les **motifs** qu'il
faut rectifier, pas le livrable.

**`ECART-046` est accepté, sur ton arbitrage.** Le garde-fou d'autorisation est prouvé par 12 tests sur
une vraie application FastAPI, mais **pas à travers Caddy** : le lot n'a aucune route métier à
refuser. Le LOT 5 devra le monter sur sa première route écrivante et le prouver de bout en bout.

**Et une convergence à faire, qui n'est le critère d'aucune sous-étape :** `PageStatut` emploie encore
les classes neutres d'avant `packages/ui`. Elle partage la **logique** avec le portail depuis `T10`,
mais pas le balisage — si bien que le même message de copie s'affiche dans **deux habillages**.

---

## 9. Ta décision — **PRISE le 24 août 2026**

- [x] **`G4` franchie.** `DEC-557`. Le LOT 5 — collaborateurs, profils et organisation — **peut** être
      ouvert ; son ouverture et la validation de son découpage restent un acte distinct, et Jonathan
      seul le pose (règle 1).
- [ ] ~~`G4` refusée~~

**Si tu franchis**, trois gestes suivent, et aucun n'est automatique :

1. la **recette finale** sur les images de `T12`, avec la commande du §5 ;
2. le tag **`v0.4.0`**, annoté, sur `main` — comme `v0.3.0` à `G3` ;
3. l'ouverture du **LOT 5** et la validation de son découpage **avant** qu'une ligne ne soit écrite.
