# Compte rendu — `T12` du LOT 8 : l'accueil mobile et les carrousels accessibles

**Sous-étape :** la douzième du lot — carrousels manuels et accessibles pour les listes
de l'accueil ; `MVP-L08-US005` (vidéo sur action) explicitement reportée
**Date :** 6 octobre 2026
**Décision :** `DEC-631`
**Stories :** `MVP-L08-US005` (reportée, arbitrage explicite de Jonathan)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1` à `T11`, **`T12`** |
| Restent | `T13`, `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. La question posée avant tout code, et sa réponse

La fiche attribue à `T12` « l'accueil mobile, les carrousels accessibles **et la vidéo sur
action** ». Construire la vidéo suppose de lire un bloc de contenu de type `VIDEO` dans la
présentation — mais :

- **aucune fixture du dépôt** (Python, TypeScript, tests de composant) n'exerce jamais un
  bloc `VIDEO` : `texteDuBloc(bloc, 'texte')`, la clef reprise par `T11`, n'a de précédent
  que pour du texte ;
- `QO-121` (quels champs un bloc porte dans son `payload_json`) reste **explicitement
  ouverte** — Jonathan l'a reportée le 25/09/2026, non bloquante ;
- `CONT-026` confirme que les **onze** emplacements vidéo du prototype sont **vides**, leur
  production relevant de la V1.

Inventer maintenant un champ de `payload_json` pour porter l'adresse d'une vidéo aurait
tranché une partie de `QO-121` par anticipation, avant que les dix autres types de blocs ne
soient eux-mêmes décidés — exactement ce que le §6.5 interdit.

**Question posée à Jonathan avant tout code** (deux options : décider maintenant un champ
minimal pour les seuls blocs `VIDEO`, ou reporter `US005` explicitement). **Réponse : reporter.**
`T12` construit donc uniquement les carrousels mobiles pour les trois listes déjà servies par
l'agrégat de `T8`.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `packages/ui/src/Carrousel.tsx` | Nouveau composant : piste défilante manuelle, deux commandes, aucune minuterie |
| `packages/ui/src/Carrousel.test.tsx` | **9 tests** |
| `packages/ui/src/composants.css` | Classes `.ui-carrousel*`, mobile d'abord, repli liste verticale dès 768 px |
| `packages/ui/src/index.ts` | Export de `Carrousel`/`ProprietesCarrousel` |
| `apps/web/src/pages/PageEntite.tsx` | Les trois listes (arrivées, événements, liens internes) passent par `<Carrousel>` |
| `apps/web/src/pages/PageEntite.test.tsx` | **4 tests** supplémentaires (describe `T12`) |
| `apps/web/src/pages/application.css` | Retrait des classes de liste devenues inutiles (portées par le carrousel) |

## 3.1 Un seul composant pour trois listes — §7.27

Les trois sections concernées (arrivées récentes, événements à venir, liens internes)
partageaient déjà la même forme : une liste capée ou non, avec un lien « voir plus » pour
deux d'entre elles. `Carrousel` est écrit une fois dans `packages/ui`, consommé trois fois
dans `PageEntite.tsx` — jamais une copie par section.

**Les liens internes n'avaient JAMAIS été bornés par `NOMBRE_MONTRE`** : `T11` affichait déjà
la liste entière, sans aucune troncature ni lien « voir plus ». C'est donc, sur mobile, la
section la plus exposée à un défilement vertical sans fin — et le premier bénéficiaire réel
du carrousel.

## 3.2 Manuel par construction, pas par choix non exercé

Le cahier §13.4/§13.5 exige des carrousels « manuels » : aucune minuterie n'existe dans
`Carrousel.tsx`, et il ne peut donc pas en acquérir une par erreur future — un test à
minuteur factice (`vi.useFakeTimers`) le vérifie explicitement.

## 3.3 Pas de second repère d'accessibilité — un défaut trouvé et corrigé avant la fusion

Première version : la piste était enveloppée d'un `<div role="region" aria-label={libelle}>`.
Mesuré directement en écrivant le test : `<Carte titre="…">` (packages/ui, LOT 1) est
**déjà** une région nommée par ce même titre, et le composant unique qui consomme
`Carrousel` est toujours imbriqué dans une `Carte`. Envelopper la piste d'un second
`role="region"` du même nom produit **deux régions identiques** — mesuré,
`getByRole('region', { name })` en trouvait alors deux au lieu d'une.

**Corrigé en retirant le rôle de région** : `libelle` nomme désormais la **liste** elle-même
(`aria-label` sur le `<ul>`, rôle `list`, jamais `region`) et les deux boutons
(« … : élément précédent »/« … : élément suivant »). Seule une `<Carte titre="…">`
englobante porte la région — ce qui était déjà le cas avant `T12`.

## 3.4 Seul le mobile voit les commandes — même discipline que la barre du LOT 4

Au-delà de 768 px, `composants.css` repasse la piste en liste verticale (`flex-direction:
column`, `overflow-x: visible`) et masque les boutons (`display: none`) — exactement le
motif déjà retenu pour la barre de navigation inférieure (LOT 4, `T5`) : deux repères de
navigation pour le même contenu dupliqueraient l'ordre de tabulation.

## 3.5 `scrollBy` n'impose jamais `behavior` — CSS seul décide du mouvement

`scroll-behavior: smooth` est déclaré en CSS sur la piste, neutralisé sous
`@media (prefers-reduced-motion: reduce)` — même forme que `CarteRetournable` (LOT 5) et
`application.css`/`styles.css` depuis le LOT 1. `Carrousel.scrollBy({ left })` n'impose
jamais `behavior` explicite : un second mécanisme en JavaScript aurait été une deuxième
règle pour la même chose (`DEC-466`/`ECART-022`).

## 3.6 Les boutons s'épuisent aux extrémités

« Précédent » et « Suivant » se désactivent en butée, mesuré sur
`scrollLeft`/`scrollWidth`/`clientWidth` du nœud réel — un bouton actionnable qui ne ferait
rien apprendrait à l'ignorer (§7.21).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q --collect-only` | **1 564**, inchangé — aucune ligne Python touchée |
| `uv run mypy` (depuis la racine) | vert, **197** fichiers, inchangé |
| `pnpm --filter @onboarding/ui test` | **120/120** (+9, le nouveau `Carrousel.test.tsx`) |
| `pnpm --filter web test` | **294/294** (+4) |
| `pnpm --filter @onboarding/contracts test` | **380/380**, inchangé |
| `pnpm run typecheck` (tsc, 3 paquets) | vert |
| `pnpm run lint` / `pnpm run format:check` | vert |
| `make sources-check` | **571** fichiers source examinés, 0 ignoré hors les 2 exceptions connues |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| **aller-retour réel** (§7.43) | décor psql réel (entité `t12demo`, personne de connexion `@exalt-company.com` sans droit éditorial, deux arrivées, deux événements, deux liens internes), lien magique réel demandé par l'API et récupéré via Mailpit, consommé en HTTPS — vérifié en mobile (375 px) **et** en desktop ; décor nettoyé après coup, zéro résidu vérifié |
| **témoin central — mobile** | les trois carrousels défilent, les boutons s'activent/se désactivent aux bonnes butées, aucune section n'affiche de commande inutile |
| **témoin central — desktop** | **zéro régression visuelle** : les trois sections redeviennent des listes verticales, aucune commande visible — identique à `T11` |

**Zéro régression** : le total Vitest passe de **781** à **794** (+13 : +9 `ui`, +4 `web`), le
total pytest reste à **1 564** puisqu'aucune ligne Python n'a été touchée — confirmé par
`git status`.

**Un défaut trouvé et corrigé avant tout commit** (§3.3 ci-dessus) : la première version du
composant produisait une collision de région, détectée en écrivant son propre test
(`getByRole('region', …)` en trouvait deux) avant même d'atteindre `PageEntite.test.tsx`.

**Une limite de l'automatisation du navigateur, nommée plutôt que cachée** : l'activation au
clavier (Entrée/Espace) d'un `<button>` natif n'a pas pu être démontrée par l'outil de
navigation de cette session — une sonde minimale (bouton neuf, sans aucune logique)
confirme que ni `Return` ni `Espace` ne déclenchent de `click` synthétique dans cet
environnement d'automatisation, y compris sur un bouton entièrement nu. Ce n'est pas un
défaut du composant : la garantie clavier est **structurelle** (un `<button type="button">`
natif, exactement la même preuve que `CarteRetournable`, LOT 5, §7.35) et ne dépend d'aucun
outil particulier pour être vraie dans un navigateur réel. L'activation à la souris/au
toucher, elle, a été vérifiée directement (clics réels sur « précédent »/« suivant »,
mesurés par `scrollLeft`).

---

# 5. Décisions

- `DEC-631` consigne la réalisation de `T12`, y compris le report explicite de `US005` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact ; `QO-121` reste ouverte,
  non davantage instruite.

---

# 6. Ce que `T12` laisse

- l'accueil mobile complet : les trois listes défilent en carrousel manuel et accessible
  sous 768 px, redeviennent une liste verticale au-delà, zéro régression desktop ;
- `MVP-L08-US005` (vidéo sur action) reste à instruire — pas avant que `QO-121` ne tranche
  un vocabulaire de `payload_json`, ou qu'une décision narrow équivalente à celle
  envisagée ici (et refusée) ne soit explicitement prise par Jonathan ;
- `T13` (contrôle de pile réelle) devra couvrir l'accueil et les événements — aucun script
  `make accueil-check`/`evenements-check` dédié n'existe encore pour l'accueil, à construire
  ou à combiner avec le script différé depuis `T9`/`T10` du lot.

# Validation demandée à Jonathan

`T12` est faite. Après fusion, la prochaine sous-étape est `T13` : le contrôle de pile
réelle événements et accueil.
