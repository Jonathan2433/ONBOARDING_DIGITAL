# Compte rendu — `T9` du LOT 6 : les écrans de lecture — Framework, cercle, bureau

**Sous-étape :** `T9` sur douze, LOT 6
**Stories :** `MVP-L06-US001`, `MVP-L06-US002`, `MVP-L06-US003`
**Date :** 23 septembre 2026
**Décision :** `DEC-589`

---

# 1. État du lot

`T1` à `T8` sont faites. `T9` livre les trois écrans de lecture que l'API sert depuis `T2` à
`T4` — la page Framework, la page détaillée d'un cercle, la page détaillée d'un bureau — sans
toucher une seule ligne de `apps/api`. Aucune migration, aucune route, aucun test Python
nouveau : les 68 contrôles de `make framework-check` et les 372 tests unitaires Python restent
ceux de `T8`, rejoués à l'identique pour vérifier l'absence de régression.

Ce que `T9` ajoute vit entièrement dans `apps/web` : trois pages, un client API, une extension
du titre du cadre applicatif, et les tests qui les accompagnent.

---

# 2. Ce que la sous-étape a produit

## 2.1 Trois pages, un client, deux routes de plus

| Fichier | Rôle |
|---|---|
| `apps/web/src/api/organisation.ts` | Client des trois lectures — `lireLeFramework`, `lireLeCercle`, `lireLeBureau` — même patron que `trombinoscope.ts` : validation par le contrat, signal d'abandon, en-tête de corrélation lu avant le corps |
| `apps/web/src/pages/PageFramework.tsx` | Les trois familles de `GET …/framework`, toujours rendues, même vides |
| `apps/web/src/pages/PageCercle.tsx` | `GET …/circles/{code_cercle}`, pagination des membres reprise du §18.2 |
| `apps/web/src/pages/PageBureau.tsx` | `GET …/offices/{code_bureau}`, aucune pagination — les responsables sont bornés, pas une population |
| `apps/web/src/routes.ts` | Deux chemins de plus, `frameworkCercle` et `frameworkBureau`, au **même gabarit** que celui que l'API émettait déjà dans `carte.cheminDetaille` depuis `T2` |
| `apps/web/src/App.tsx` | `framework` entre dans `PAGES_LIVREES` ; deux routes de plus sous `CadreApplicatif`, au même rang que `SUFFIXE_PROFIL` |
| `apps/web/src/pages/application.css` | Les classes des trois écrans, et l'extension du bloc `@media (prefers-reduced-motion: reduce)` |
| `apps/web/src/pages/CadreApplicatif.tsx` | `useTitreDeLaPage` étendue à deux gabarits paramétrés — voir §2.4 |

## 2.2 Les cartes de responsabilité `DSM`/`ESM` restent de l'information, jamais des liens

`chemin_detaille` n'est pas `null` pour `DSM` et `ESM` — l'annexe A §10.1 leur donne une page
propre. Mais **`ECART-062` est ouvert et non tranché** : aucun `page_type` du §15.1 ne porte
cette page, personne ne sait aujourd'hui ce qu'elle afficherait, et aucune route de lecture ne
la sert. Construire un `<Link>` vers cette adresse aurait reproduit exactement le défaut que
`PageRubrique` existe pour éviter — « un lien qui aboutit au fourre-tout 404 est atteignable et
inutile ; la navigation ne serait pas prouvée, elle serait simulée ».

Les cartes de responsabilité sont donc rendues comme de l'**information** — type, titulaires —
jamais comme un lien, pour les quatre catégories, DSM et ESM compris. Le jour où `ECART-062` se
referme, la carte peut redevenir un lien sans qu'aucune autre décision de `T9` n'ait à changer.

`CLAUDE.md` avait explicitement demandé d'instruire `ECART-062` **avant** `T9`. Ce n'est pas
fait : Jonathan a donné le signal de lancer `T9` sans que la question soit remontée à Léa, et
la décision ci-dessus tient sans elle — aucune ligne de `T9` ne dépend de sa réponse. L'écart
reste porté au registre, non instruit.

## 2.3 La couleur n'est jamais seule — le couple du §7.42, prouvé côté écran

`jeton_de_couleur` est nullable au catalogue depuis `T3`. Un test monte deux cartes de cercle
côte à côte, l'une avec jeton, l'autre sans, et vérifie **les deux** : la propriété personnalisée
CSS `--framework-cercle-couleur` est posée dans un cas, absente dans l'autre, et le **nom** du
cercle est du texte visible dans les deux cas. Sans le couple, un code qui ne poserait jamais la
couleur — ou qui la poserait toujours — passerait le test aussi bien.

`couleurDuCercle`, posée en `T11` du LOT 5, est réutilisée telle quelle : troisième consommateur,
aucune copie.

## 2.4 Un défaut réel trouvé dans un navigateur, pas dans un contrôle

Vérification visuelle sur `/entites/BORDEA00/framework/bureaux/SIEGE` : le contenu affichait
correctement « Siège Bordeaux », et le `<h1>` de la page disait **« Accueil de l'entité »** — une
affirmation fausse, pas seulement générique.

Cause : `useTitreDeLaPage`, posée en `T3` du LOT 4, ne compare le chemin courant qu'à
l'**égalité** de `cheminDeRubrique(code, rubrique.suffixe)`. Toute route imbriquée sous une
rubrique — plus profonde qu'elle — ne correspond à rien et retombe sur le titre par défaut.

Corrigé pour les deux routes que `T9` introduit : `TITRES_DE_SOUS_PAGE` dérive ses deux gabarits
de `CHEMINS.frameworkCercle` et `CHEMINS.frameworkBureau` — jamais recopiés — et les compare au
chemin courant segment par segment.

**Le même défaut existe déjà sur la fiche profil du LOT 5 `T11`**, vérifié dans le même
navigateur : `/entites/BORDEA00/trombinoscope/...` affiche aussi « Accueil de l'entité » en
`<h1>`. Il n'est **pas** corrigé ici — rouvrir un fichier d'un lot déjà fusionné et passé sa
porte pour une sous-étape du LOT 6 déborderait son périmètre (§2, règle n°1 de `CLAUDE.md`).
`ECART-065` le porte, avec sa recommandation : la prochaine sous-étape qui touche
`CadreApplicatif.tsx` doit généraliser `TITRES_DE_SOUS_PAGE` plutôt qu'empiler un troisième cas.

## 2.5 Un rôle de la matrice et une catégorie du Framework partagent le même sigle

`make cadre-check` refuse tout code de `rolesAdministration` (`ESM`, `ADM-E`, `SUPER`) écrit en
littéral dans le frontend — source unique du manifeste, lue par TypeScript et par Python. Une
première version de `PageFramework.tsx` écrivait `ESM: 'ESM'` dans une table de libellés
français, et le contrôle l'a signalé : un faux positif au sens strict, aucune autorisation
n'étant décidée dans cette table, mais le garde-fou textuel ne peut pas distinguer les deux
vocabulaires — c'est structurellement la même classe que le motif `* [0-9]` du §7.34, écrit
contre un cas et aveugle à l'autre.

Contourner par un commentaire d'exemption aurait été le défaut du §7.25. La table ne porte donc
plus que les deux catégories qui ont vraiment besoin d'une traduction — `BOOSTER` → « Booster »,
`OFFICE_MANAGER` → « Responsable de bureau » — et `DSM`/`ESM` s'affichent tels que l'API les
rend, sans qu'aucune chaîne ne soit réécrite en dur : ils se lisent sans traduction de toute
façon.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make typecheck` (mypy strict, `tsc --noEmit`) | 0 erreur |
| `make lint` (Ruff, ESLint) | 0 erreur |
| `make format-check` (Ruff format, Prettier) | conforme |
| `make test-frontend` | **540 tests**, 0 échec — 223 `contracts`, 111 `ui`, **207** `web` (+17 sur les trois écrans, +1 sur le titre du cadre) |
| `make test-unit` (pytest, hors intégration) | 372 tests, 0 échec — aucune ligne de `T9` ne touche l'API |
| `make cadre-check` | **25 contrôles, 0 échec** — 4 transitions déclarées, toutes neutralisées sous `prefers-reduced-motion` |
| `make cadre-temoin` | discrimine — les quinze motifs attendus sont nommés |
| `make ecrans-check` | **8 contrôles, 0 échec** — les 4 modules neufs servis en JavaScript par le conteneur `web` à jour, 0 couleur littérale |
| `make sources-check` / `sources-temoin` | 446 fichiers examinés, aucun ignoré à tort ; le témoin discrimine |
| `make framework-check` | **68 contrôles, 0 échec** — sanity check, aucune ligne de `T9` ne touche l'API |
| `make images-check`, `parametres-check`, `parametres-temoin`, `sessions-temoin`, `recette-modele-check` | 0 échec |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes, 12+12 contrôles de totaux |
| Vérification visuelle réelle | session administrateur locale, entité `BORDEA00` du jeu de démonstration, à travers Caddy en HTTPS |

**Non exécuté délibérément :** `uv run pytest` complet (intégration comprise). La base de
développement porte le jeu de démonstration client, et `make residu-check` y rendrait un grand
nombre d'échecs environnementaux déjà documentés au §11 de `CLAUDE.md`, sans rapport avec `T9`.
Aucune ligne Python n'étant touchée, `make test-unit` (372 tests, non intégration) suffit à
couvrir le risque de régression côté API ; la porte de la pull request, qui tourne sur une base
neuve, fait foi pour le reste.

---

# 4. Défauts trouvés

## `T9-1` — un rôle de la matrice collisionne avec une catégorie Framework de même sigle

Voir §2.5. Trouvé par `make cadre-check` lui-même, à la première exécution. Corrigé en retirant
`DSM`/`ESM` de la table de libellés plutôt qu'en affaiblissant le contrôle.

## `T9-2` — le titre `<h1>` du cadre est faux sur une sous-page paramétrée

Voir §2.4. Trouvé dans un navigateur, pas dans un contrôle automatisé : les 540 tests
frontend passaient déjà, `cadre-check` passait déjà — c'est le §7.0, quatrième proposition, une
fois de plus. Corrigé pour les deux routes de `T9` ; `ECART-065` porte le résiduel sur la fiche
profil du LOT 5.

---

# 5. Décisions, écarts et questions

**`DEC-589`** — voir le registre des décisions.

**`ECART-065`** ouvert — le titre `<h1>` du cadre sur une sous-page paramétrée, résiduel sur la
fiche profil.

**`ECART-062`** reste ouvert, non instruit — voir §2.2. `CLAUDE.md` demandait de l'instruire
avant `T9` ; ce n'est pas fait, et aucune ligne de `T9` n'en dépendait.

**Aucune question nouvelle.**

---

# 6. Ce que `T9` ne fait pas

Aucun rendu de bloc éditorial sur les pages de cercle et de bureau : `cercles.py` et `bureaux.py`
le disent explicitement dans leur en-tête, « aucun contenu éditorial », les blocs étant le sujet
de `T5` et leur écran celui de `T10`. Aucune écriture, aucune action de cycle de vie sur ces
deux écrans — lecture seule, comme les stories `US001` à `US003` le demandent. Aucune page pour
les responsabilités `DSM`/`ESM` — voir §2.2.

---

# 7. Ce que `T9` laisse

`ECART-062` non instruit, prochaine action naturelle pour Léa avant que la carte de
responsabilité puisse redevenir un lien. `ECART-065` ouvert sur la fiche profil du LOT 5.
`T10` — les écrans d'édition — est la prochaine sous-étape ; elle consommera le rendu des blocs
de `T5` et l'écriture de `T6`, tous deux déjà livrés.

---

# Validation demandée à Jonathan

Les trois écrans sont en ligne, vérifiés à l'écran sur le jeu de démonstration. `ECART-062` n'a
pas été instruit avec Léa avant cette sous-étape, contrairement à ce que la passation demandait
— la décision retenue (§2.2) ne bloque rien, mais la question reste posée.

```bash
~/.local/bin/gh pr merge <numero> --squash --delete-branch
```

```bash
~/.local/bin/gh pr close <numero> --delete-branch
```
