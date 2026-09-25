# Compte rendu — `T10` du LOT 6 : les écrans d'édition

**Sous-étape :** `T10` sur douze, LOT 6 — Framework, cercles, bureaux et contenus éditoriaux
**Stories :** `MVP-L06-US004` (3 sur 3), `MVP-L06-US005`
**Décision :** `DEC-591`
**Date :** 24 septembre 2026

---

# 1. État du lot

Neuf sous-étapes faites avant celle-ci — `T1` à `T9`. Le découpage à douze reste celui validé le
13/09/2026 (`DEC-575`). `T10` est la troisième et dernière tranche de `US004` (« Éditer un contenu
avec des blocs contrôlés »), après `T5` (le rendu) et `T6` (l'écriture), et la première tranche de
`US005` (« Gérer la présentation et les liens internes de l'entité ») côté écran — l'API de `US005`
est faite depuis `T8`.

**Deux blocages levés avant d'écrire une ligne**, par des questions à Jonathan :

- `QO-121` (vocabulaire de `payload_json`) et `QO-123` (vocabulaire de `icon_reference`) restent
  ouvertes, adressées à Léa. Jonathan a confirmé : ne pas inventer, avancer sur ce qui n'en dépend
  pas.
- Le choix de la bibliothèque d'icônes pour `QO-123`, qui relevait de Jonathan, est tranché :
  `lucide-react`, licence ISC, chargement paresseux par nom.
- `ECART-062` (la page DSM sans `page_type`) est relancé formellement vers Léa sous `QO-124`, sur
  décision de Jonathan — il ne bloquait pas `T10`, dont le code applique déjà la lecture
  restrictive de façon cohérente depuis `T6`.

---

# 2. Ce que la sous-étape a produit

## 2.1 Un trou depuis `T6`, comblé par deux routes — et c'est la moitié du travail

**Mesure avant d'écrire un écran :** aucune route ne servait un contenu en dehors de son état
`published`, avec sa `version`. La lecture de `T5` (`GET …/pages/{type}/{slug}`) ne sert QUE le
publié, à dessein (`US006`). Un éditeur qui recharge son écran en cours de rédaction, ou revient
sur un brouillon jamais publié, ou veut retrouver une page archivée pour la restaurer, n'avait
donc aucun moyen de relire son propre travail. Ce n'était pas un report voulu par `T6` : rien dans
sa fiche ni son compte rendu ne l'anticipait.

Deux routes nouvelles, dans `apps/api/app/content/pages.py` et `routes.py` :

- `GET /entities/{code}/pages/gestion` — toutes les pages de l'entité, tous états confondus.
- `GET /entities/{code}/pages/{page:uuid}/gestion` — une page et ses blocs, tous états, avec sa
  `version`.

Même parti que `T8` pour les liens internes (`/liens` ne sert que l'actif, `/liens/gestion` sert
les deux) : la lecture publique ne sert que le publié, la gestion sert les trois états.

**Un piège de collision de route, mesuré avant d'être écrit.** `/pages/{page}/gestion` partage sa
forme — deux segments après `/pages/` — avec la lecture publique `/pages/{type_de_page}/{slug}`.
Un slug utilisateur peut valoir littéralement « gestion » (texte libre, jusqu'à 160 caractères) :
sans garde, la route de lecture, enregistrée en premier, aurait intercepté `GET
…/pages/{type_de_page}/gestion` d'une page publiée réelle, avant tout contrôle applicatif — mesuré
avec `Route.matches()` de Starlette. Deux parades, mesurées dans les deux sens : la route de
gestion est déclarée AVANT la lecture publique (même ordre que `/liens/ordre` face à
`/liens/{lien}`), et son premier segment porte le convertisseur `{page:uuid}`, qui refuse à la
racine tout segment non-UUID et laisse la lecture publique reprendre la main.

## 2.2 Le manifeste exposait deux grilles depuis `T7`, mais pas les deux qu'il fallait

`rolesRestaurationDUnContenu` (`T7`) et `rolesGestionDesLiensInternes` (`T8`) étaient déjà
exposées dans le manifeste, en anticipation d'un écran qui n'existait pas encore. `T6` n'avait pas
fait de même pour SES deux grilles — `rolesCreationDeContenu` et `rolesEcritureEditoriale` —, un
oubli de la discipline `DEC-492`, pas une décision. `T10` les ajoute, avec un test Python qui
confronte les deux clés aux constantes réelles de `app/content/perimetre.py`, dans les deux sens.

**Les deux clés ne sont pas équivalentes.** `rolesCreationDeContenu` vaut `ROLES_DE_CREATION` — la
ligne unique de création du §13, sans `BOOST` ni `OFFICE`. `rolesEcritureEditoriale` vaut
`ROLES_D_ECRITURE_EDITORIALE`, strictement plus large : elle y ajoute les deux rôles de portée
locale, parce qu'un Booster ne peut pas créer une page mais peut modifier celle de son cercle. Un
test exige l'inclusion stricte.

## 2.3 L'écran d'édition d'un contenu ne propose AUCUN formulaire de création de bloc

`PanneauEditionDeContenu` (`apps/web/src/pages/`) réordonne (monter/descendre) et retire les blocs
**existants** d'une page — ce qui ne suppose rien de leurs champs — et affiche leur `contenu` en
JSON brut, sans tenter de l'interpréter. Il ne propose **aucun** moyen d'ajouter un nouveau bloc :
`QO-121` n'étant pas tranchée, en inventer un serait exactement §6.5, une hypothèse déguisée en
décision.

Le titre et la liste des blocs modifiée localement ne s'enregistrent qu'au clic sur
« Enregistrer », qui envoie la liste **complète** — l'API remplace la liste et archive les blocs
absents (modèle §2.4). Le panneau porte aussi le cycle de vie (publier / archiver / restaurer),
gardé par les mêmes prédicats `peutEditerUnContenu` / `peutRestaurerUnContenu` du contrat, qui ne
décident rien — l'API reste l'autorité finale (matrice §2.6).

Deux écrans consommateurs : `PageEditionDeCercle` et `PageEditionDeBureau`, qui résolvent d'abord
le cercle ou le bureau par son code pour obtenir son `identifiant` — seul moyen de filtrer la
liste de gestion sur `circle_id`/`office_id`, la ressource et sa page de contenu n'étant reliées
que par cet identifiant, jamais par le code.

## 2.4 L'écran de gestion des liens internes complète `T8`

`PageGestionDesLiens` : liste (actifs et inactifs, avec la même route de gestion que `T8` avait
déjà posée sans écran), création, modification, réordonnancement (deux boutons, un appel à
`PUT …/liens/ordre` par geste), et bascule actif/inactif — jamais d'archivage, aucune route ne
l'offrant (§13, §19).

L'icône est un champ **texte libre** : le nom d'une icône `lucide-react`, en kebab-case,
prévisualisée par `DynamicIcon` (chargement paresseux, aucune des ~1500 icônes n'entre dans le
paquet tant qu'un lien ne la référence pas) si le nom correspond à une icône connue, rien sinon.
Aucune convention n'est imposée — ni obligation, ni mappage par `link_type` — faute de décision de
Léa sur `QO-123`.

## 2.5 `PageEntite` cesse d'être un pur espace réservé, partiellement

La page d'accueil d'une entité (`LOT 4`, `T2`/`T3`) annonçait depuis son origine que ses sections
« arrivent aux LOTS 5 à 7 ». `T10` en écrit deux : la présentation de l'entité (une page `HOME`,
éditée via `PanneauEditionDeContenu`) et un lien vers la gestion des liens internes. **Le reste de
l'accueil reste hors périmètre** : aucun écran ne compose encore la synthèse Framework, les
arrivées récentes ni les événements dans cette page — Framework a son propre écran depuis `T9`
(`/framework`), arrivées récentes et événements restent LOTS 7 et 8. Le dire explicitement plutôt
que de laisser croire à un accueil complet.

---

# 3. Un défaut réel, trouvé par le contrôle de pile avant la fusion

## `T10-1` — la lecture de gestion d'une page ARCHIVÉE rendait 403

**Ce qu'un test bouchonné n'aurait pas pu voir.** Les tests unitaires de la fonction
`lire_une_page_pour_edition` passaient : elle sert bien une page archivée. Le défaut vivait dans
la **garde** de la route HTTP, qui exigeait `ActionEditoriale.MODIFIER in perimetre.actions` —
exactement le motif déjà en place pour l'écriture, recopié sans le reconsidérer.

`_actions_selon_l_etat` (`app/content/perimetre.py`) ne rend jamais `MODIFIER` sur une page
ARCHIVÉE — seulement `RESTAURER` : « on ne modifie pas un archivé, on le restaure ». La route qui
existe précisément pour retrouver une page archivée refusait donc systématiquement, en 403, la
seule situation qui la justifie.

**Trouvé par `make framework-check`**, étendu de 68 à 74 contrôles, au premier passage réel contre
la pile — pas par les 43 tests Python ni par les 27 tests Vitest, tous verts au moment où le
contrôle a échoué. Corrigé en testant l'ensemble **non vide** (`if not perimetre.actions`) plutôt
que la présence d'une action précise — le même motif que le §7.32 du projet : ne pas exiger une
condition plus étroite que ce que la ressource permet réellement.

**Éprouvé deux fois après correction** : un test unitaire dédié
(`test_le_PERIMETRE_d_une_page_ARCHIVEE_n_est_PAS_l_ensemble_vide`), et un aller-retour réel dans
un navigateur — création d'un cercle, publication, archivage, **rechargement complet de la page**,
puis restauration — sur l'entité `BORDEA00` du jeu de démonstration, session administrateur
locale. Les données de test créées pendant cette vérification (une page de cercle, une page de
bureau, un lien) ont été retirées de la base avant de conclure, la base de développement portant
le jeu de démonstration protégé.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_ecriture_des_contenus.py` | 44 tests, 0 échec (36 avant `T10`, **8** nouveaux) |
| `uv run pytest` sur les fichiers `content`/`contrat` touchés | 126 tests, 0 échec |
| `uv run ruff check` / `ruff format --check` | 0 écart |
| `uv run mypy` (racine du projet) | 0 erreur sur le code touché |
| `pnpm run typecheck` | 0 erreur, 3 paquets |
| `pnpm run lint` | 0 écart |
| `pnpm run format:check` (Prettier) | 0 écart après une passe de reformatage |
| `pnpm run test` (Vitest) | **586** tests, 0 échec — 250 `contracts` (+27), 111 `ui` (inchangé), 225 `web` (+18) |
| `make framework-check` | **74** contrôles, 0 échec (68 avant `T10`, **6** nouveaux — voir §3) |
| `make docs-check` | 0 écart après mise à jour des registres |
| `make audit` | 0 avis, 0 tolérance — `lucide-react` ajouté, licence ISC |
| Comparaison des échecs pytest `origin/develop` vs cette branche, `git worktree`, même base | **74 échecs sur 74, listes IDENTIQUES** — zéro régression, pollution 100 % environnementale (jeu de démonstration) |
| Aller-retour réel, navigateur, session administrateur locale, entité `BORDEA00` | Cercle : créé → publié → archivé → **rechargé** → restauré. Bureau : créé. Lien : créé avec icône, désactivé. Titres `<h1>` corrects sur les trois nouvelles routes. Données de test retirées après vérification |

---

# 5. Décisions, écarts et questions

- **`DEC-591`** couvre l'ensemble de la sous-étape — voir le registre des décisions pour le détail
  complet, y compris le défaut `T10-1` et sa correction.
- **`QO-121` et `QO-123` restent ouvertes**, adressées à Léa. Leurs entrées dans le registre sont
  mises à jour : non bloquantes pour `T10` (mesuré, pas supposé), bloquantes avant `T11` — la
  reprise relue, où un auteur devra pour la première fois choisir des champs et une icône réels.
- **`QO-123` porte désormais que la bibliothèque est tranchée** (`lucide-react`, `DEC-591`) ; seule
  la convention reste à Léa.
- **`ECART-062` est relancé formellement sous `QO-124`** — voir le registre des écarts. Il ne
  bloquait pas `T10` : le code applique la lecture restrictive du §13 de façon cohérente depuis
  `T6`, sans qu'aucun écran n'accorde ou ne refuse à tort une action au DSM.

---

# 6. Ce que `T10` ne fait pas

- Aucun formulaire de création d'un nouveau bloc — `QO-121`.
- Aucune convention d'icône imposée, aucun mappage par `link_type` — `QO-123`.
- Aucune page DSM — `ECART-062` / `QO-124`, à Léa.
- Aucun assemblage de l'accueil complet de l'entité (Framework embarqué, arrivées récentes,
  événements) — hors périmètre, non découpé dans aucune des douze sous-étapes du lot.
- Aucune ligne côté LOT 7 (onboarding), LOT 9 (import CSV) ni LOT 11 (miniatures, exports).

---

# 7. Ce que `T10` laisse

- `T11` — le modèle générique, l'amorçage et la reprise relue — aura besoin des réponses de Léa à
  `QO-119` (déjà requis), `QO-121` et `QO-123` pour poser du contenu réel.
- `ECART-064` (motif d'intervention du super-administrateur) reste à instruire au LOT 10, avec
  `audit_event`, sans lien avec `T10`.
- `T12` — recette, §30 et checklist `G6` — est la dernière sous-étape du lot.

---

# Validation demandée à Jonathan

- [ ] Les deux routes de gestion (`/pages/gestion`, `/pages/{page}/gestion`) et l'exposition des
      deux rôles au manifeste sont-elles acceptées comme plomberie nécessaire, hors du périmètre
      strictement visuel d'un « écran » ?
- [ ] Le choix de `lucide-react` est confirmé (déjà tranché en amont, consigné ici).
- [ ] La relance de `ECART-062` sous `QO-124` vers Léa est-elle la bonne forme ?
- [ ] Fusion de la pull request après CI verte.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
