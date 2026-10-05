# Compte rendu — `T9` du LOT 8 : les écrans de consultation des événements

**Sous-étape :** la neuvième du lot — `GET /entities/{code}/evenements` à l'écran
**Date :** 5 octobre 2026
**Décision :** `DEC-628`
**Story :** `MVP-L08-US003` (2/2)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, **`T9`** |
| Restent | `T10` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `packages/contracts/src/evenements.ts` | contrat de la lecture : `ClassementEvenement`, `EvenementDuClassement`, `PageDesEvenements`, `validerLaPageDesEvenements`, `cheminEvenements` |
| `packages/contracts/src/evenements.test.ts` | **16 tests** |
| `packages/contracts/src/index.ts` | réexport du module `evenements.js` |
| `apps/web/src/api/evenements.ts` | `lireLesEvenements`, même montage que `organisation.ts`/`profil.ts` |
| `apps/web/src/pages/PageEvenements.tsx` | l'écran : deux onglets, cartes d'événement, badge « Annulé », pagination |
| `apps/web/src/pages/PageEvenements.test.tsx` | **7 tests** |
| `apps/web/src/App.tsx` | `PageEvenements` entre dans `PAGES_LIVREES`, remplace le stub `PageRubrique` pour la rubrique `evenements` |
| `apps/web/src/pages/application.css` | classes `.evenements-*`, mobile d'abord |

Aucune migration, aucune route API nouvelle : `T2` sert déjà `GET /entities/{code}/events`
depuis le 04/10/2026 — `T9` est le **premier écran consommateur**, même partage que les liens
internes (LOT 6, `T8`/`T10`) et le catalogue des tâches (LOT 7, `T4`/`T14`) : une lecture pose son
module de contrat quand un écran en a besoin.

## 2.1 La route existait déjà, et le menu aussi

La rubrique `evenements` et sa route `/entites/:code/evenements` ont été posées dès `T4` du
LOT 4 (`routes.ts`), **sans condition** — la matrice §5 donne « Lecture » aux huit rôles
authentifiés sur « Événements », sans divergence, donc aucune garde de rôle à calculer côté
client. Jusqu'à cette sous-étape, le chemin rendait le stub générique `PageRubrique` (« la
rubrique Événements… arrive plus tard »). `T9` remplace ce stub dans `PAGES_LIVREES` de
`App.tsx` — aucune route, aucun libellé de menu à modifier.

## 2.2 La frontière vient de l'API, jamais recalculée côté client

Le cahier §10.6 et la matrice §11 donnent deux classements — « à venir » et « passés » — et `T2`
a déjà tranché leur frontière unique : `ends_at > instant` contre `ends_at <= instant`, le même
`instant` alimentant les deux. L'écran envoie donc `classement` à chaque appel et affiche ce que
l'API répond ; aucune horloge ni aucune règle de classement n'est recopiée côté navigateur — la
règle 5 du projet, l'API est l'autorité finale.

## 2.3 Les onglets sont deux vrais `<button>`, aucun composant nouveau

`packages/ui/src/index.ts` le dit explicitement : aucune primitive d'onglets n'existe dans le
design system, et en livrer une sans écran qui l'emploie serait du code non éprouvé. Le motif
WAI-ARIA (`tablist`/`tab`/`tabpanel`) est donc posé à la main sur deux `<button>` natifs : la
réponse au clavier (Tab pour atteindre l'onglet, Entrée ou Espace pour l'activer) est
**structurelle**, même parti que `CarteRetournable` et `NavLink` ailleurs dans ce dépôt — aucun
gestionnaire de touche écrit à la main, donc aucune divergence possible avec le comportement natif
du navigateur. Changer d'onglet réinitialise la page à 1 : la page 2 des événements passés n'a
aucun sens pour les événements à venir.

## 2.4 Un événement annulé reste visible, avec un badge — jamais une couleur seule

Cahier §10.6 : « un événement annulé reste visible avec un badge "Annulé" ». `Badge` exige un
texte dans son type (WCAG 1.4.1, `packages/ui/src/Badge.tsx`) : aucune carte ne peut donc
signaler une annulation par la seule couleur. Le badge n'apparaît QUE sur `etat === 'cancelled'` ;
un événement `published` n'en porte aucun.

## 2.5 Les dates se lisent dans la chaîne, jamais par `Date`

Même leçon que `PageProfil.tsx` (LOT 5, `T11`) : un accesseur local sur un `Date` construit
depuis une chaîne ISO servie en UTC peut rendre une heure ou un jour différent de celui que l'API
a réellement servi. `dateComplete` (jour/mois/année) est donc **reprise** de `PageProfil.tsx`
plutôt que recopiée — même partage que `PageAdministration.tsx` et `PageMonOnboarding.tsx`, qui
l'importent déjà directement — et une nouvelle fonction locale `heure` applique la même méthode :
un segment lu à position fixe (`iso.slice(11, 16)`) dans la chaîne, jamais un accesseur de `Date`.

## 2.6 Aucune page de détail n'est créée

Le diagramme du cahier §8.1 montre « Événements --> Page événement », mais aucun document n'en
donne le contenu ni la raison, et chaque carte affiche déjà titre, horaire, lieu et description en
ligne. Construire un lien vers une adresse qu'aucune route ne sert serait exactement ce que
`PageRubrique` évite depuis le LOT 4 — « un lien qui aboutit au fourre-tout 404 est atteignable et
INUTILE ». `T10` (l'écran de GESTION) aura besoin d'une cible propre pour éditer ; la lecture n'en
a pas besoin.

## 2.7 `pages` peut valoir zéro, et le validateur le vérifie par le calcul

`PageDuCercle.pages` du LOT 6 vaut toujours au moins 1 — un cercle existe même sans membre. Une
entité sans aucun événement d'un classement donné a un total de zéro, et l'API rend `pages = 0`
(`-(-0 // taille)`). Exiger `pages >= 1` ici — par réflexe, en copiant le validateur du cercle —
aurait refusé une réponse parfaitement légitime. Le validateur confronte donc `pages` au calcul
`total`/`taille` plutôt qu'à une borne fixe : deux sources pour une même grandeur doivent
coïncider (§7.0, sixième proposition), et c'est ce calcul — pas une constante — qui les confronte.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `pnpm --filter @onboarding/contracts test` | **352/352** (+16) |
| `pnpm --filter web test` | **266/266** (+7) |
| `pnpm --filter @onboarding/ui test` | **111/111**, inchangé |
| `make typecheck` (mypy + tsc, depuis la racine) | vert, **196** fichiers Python inchangés |
| `make lint` (Ruff + ESLint) | vert |
| `make format-check` (Ruff + Prettier) | vert |
| `python3 infra/scripts/verifier-cadre.py` | **25 contrôles, 0 échec** — routes/menu toujours engendrés depuis `RUBRIQUES` |
| `python3 infra/scripts/verifier-sources-suivies.py` | OK, aucun fichier source ignoré |
| `python3 infra/scripts/verifier-documentation.py` | 5 documents immuables intacts, séquences cohérentes |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5**, inchangé — aucune route API touchée |
| collecte pytest depuis la racine | **1 547** inchangé, dont **1 145** d'intégration |
| **aller-retour réel** (§7.43) | décor psql réel (3 événements : publié à venir, annulé à venir, publié passé), compte de vérification `t9-verification@exalt-company.com` rattaché à `BORDEA00`, lien magique réel consommé dans le navigateur, écran vu à travers Caddy en HTTPS — desktop **et** mobile (375 px), décor nettoyé après coup |

**Zéro régression frontend** : le dépôt n'ajoute aucun fichier Python, et `test_contrat.py` —
qui confronte le manifeste au schéma réellement servi — reste vert à l'identique. La preuve
`git worktree` sur `origin/develop` n'apporte rien de plus pour une sous-étape qui ne touche
aucune ligne de `apps/api/` : c'est la collecte pytest identique (1 547/1 145) qui en tient lieu.

---

# 4. Décisions

- `DEC-628` consigne la réalisation de `T9` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert — sans objet direct ici,
  cette sous-étape ne porte aucune écriture.

---

# 5. Ce que `T9` laisse

- l'écran de consultation des événements, deux onglets « À venir »/« Passés », badge « Annulé »,
  accessible au clavier et en mobile ;
- `T10` (écran de gestion : créer, modifier, publier, annuler, archiver, restaurer, médias) reste
  à faire, et posera sa propre cible de navigation pour éditer un événement ;
- `T11`/`T12` (accueil final desktop puis mobile) consommeront l'agrégat de `T8`, qui compose déjà
  la section « événements à venir » — aucun changement nécessaire ici pour eux.

# Validation demandée à Jonathan

`T9` est faite. Après fusion, la prochaine sous-étape est `T10` : l'écran de gestion des
événements.
