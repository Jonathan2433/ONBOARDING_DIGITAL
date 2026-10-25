# Compte rendu — LOT 10, `T15`

**Sous-étape :** les écrans back-office — audit, reporting étendu, support (signalements, alertes,
demandes RGPD)
**Décision :** `DEC-669`
**Date :** 24 octobre 2026
**Stories concernées :** `MVP-L10-US001`/`US002`/`US003`/`US004`/`US006`/`US007`/`US008` (premier
écran consommateur, aucune n'est rouverte sur le fond)

---

## 1. Ce que `T15` devait faire

La fiche (`fiche-lot-10.md`) la décrit en une ligne : « Les écrans back-office — audit, reporting,
support — transversal — pattern `T14` du LOT 9, onglets de la page `administration` existante. »
`T8` à `T14` avaient posé sept domaines d'API sans aucun écran consommateur :

| Domaine | Sous-étape | Routes |
|---|---|---|
| Journal d'audit | `T8`/`T9` | `GET .../audit`, `POST .../audit/export` |
| Reporting étendu | `T10` | `GET .../reporting`, `.../reporting/onboarding`, `.../reporting/profils-incomplets` |
| Signalements (traitement) | `T12` | `GET .../bug-reports`, `.../historique`, `POST .../etat` |
| Alertes opérationnelles | `T13` | `GET /alerts`, `/alerts/{alerte}`, `.../commentaires`, `POST .../acquittement`, `.../commentaires`, `.../resolution` |
| Demandes RGPD | `T14` | `POST /data-subject-requests`, `GET .../`, `.../{demande}`, `.../historique`, `POST .../verification-identite`, `.../cloture` |

Dix-neuf routes au total, aucune nouvelle à poser : `T15` est une sous-étape de **consommation**,
comme `T14` du LOT 9 l'avait été pour le back-office du LOT 9.

## 2. Ce qui a été dérivé du corpus, et ce qui a été arbitré

### 2.1 Le seul point que le corpus ne tranche pas : l'organisation des onglets

Le cahier §10.8 ferme la liste des groupes du back-office à **sept** noms (Organisation,
Onboarding, Contenu, Données, Pilotage, Configuration, Super-administration) — une liste fermée,
sans « notamment ». Mais le cahier traite aussi Audit (§10.11), Reporting (§10.10) et Support
(§10.12) comme **trois sujets distincts**, chacun avec sa propre section numérotée, au même niveau
que Trombinoscope (§10.1) ou Événements (§10.6).

Mesuré avant toute décision :

- **Reporting** correspond déjà à un groupe existant. §10.8 liste « rapports » parmi les fonctions
  de l'Administration, et « Pilotage » héberge déjà le tableau de bord (LOT 9 `T5`) qui sert
  exactement cette fonction. `app/reporting/lecture.py` réutilise d'ailleurs LITTÉRALEMENT
  `ROLES_DU_TABLEAU_DE_BORD`/`PerimetreDuTableauDeBord`/`resoudre_le_perimetre_du_tableau_de_bord`
  (LOT 9 `T5`) : les quatre premières lignes de la matrice §15.1 portent la MÊME grille que le
  tableau de bord. Aucune ambiguïté ici.
- **Audit** et **Support** ne correspondent à AUCUN des sept groupes. Le §10.8 nomme « audit »
  comme une fonction séparée de « rapports », sans dire à quel groupe elle appartient ; « support »
  (signalements, alertes) n'apparaît dans AUCUNE des onze fonctions listées par §10.8 du tout.

Cette ambiguïté — combien d'onglets ajouter, et lesquels regrouper — n'est pas résolue par une
lecture plus attentive du corpus : c'est une décision de structure de navigation (IA), pas une
règle métier. Posée à Jonathan avant tout code (`AskUserQuestion`, reformulé sans jargon, trois
options avec leurs conséquences concrètes) :

> « Comment organiser les quatre nouvelles fonctions du LOT 10 (journal d'audit, reporting
> détaillé, signalements/alertes, demandes RGPD) dans la page Administration ? »

Réponse retenue : **deux onglets de plus** (« Audit », « Support »), le reporting étendu
rejoignant « Pilotage ». Jamais neuf onglets fusionnés en un (dense, mélangerait consultation et
actions), jamais un onglet par sujet (un « RGPD » séparé de « Support » aurait été défendable mais
moins conforme à la lexie du cahier, qui nomme littéralement « Support » en §10.12 et n'offre
aucun autre nom pour les demandes RGPD).

### 2.2 « Audit » : trois grilles de rôles, jamais fusionnées

`app/audit/perimetre.py` déclare trois constantes distinctes depuis `T8`/`T9` :
`ROLES_DE_L_AUDIT` (lecture générale, six rôles — DSM/ESM/BOOST/OFFICE/ADM-E/SUPER, EMP/NEW/ANON à
tiret), `ROLES_DES_DETAILS_TECHNIQUES` (ADM-E/SUPER, masque `resource_reference`/
`correlation_token`) et `ROLES_D_EXPORT_DE_L_AUDIT` (ADM-E/SUPER aussi — une coïncidence de valeur
entre deux lignes distinctes du §16, jamais une identité conceptuelle, déjà documenté par `T9`).
L'écran reflète fidèlement les trois : l'onglet lui-même est gardé par la première, la colonne
« référence/corrélation » par la deuxième, le bouton d'export par la troisième — trois contrôles
indépendants dans `SectionAudit.tsx`, jamais une grille unique qui en cacherait une des trois.

Un résidu nommé : le cinquième filtre de l'API, `acteur` (un identifiant de personne), n'a pas de
champ dans l'écran. Aucune route ne liste les personnes toutes entités confondues pour en faire un
sélecteur — même limite documentée que `premier_administrateur` dans `SectionOrganisation.tsx`
(LOT 9 `T14`). Un champ texte UUID n'aurait servi à personne sans connaître l'identifiant par
cœur.

### 2.3 « Support » : trois gardes indépendantes, un seul onglet toujours visible

Les trois sous-domaines de « Support » ont des degrés d'ouverture très différents, mesurés avant
d'écrire l'écran plutôt que supposés :

- **Signalements** (`T12`) : la LECTURE se dégrade jusqu'à `Soi` — aucun rôle n'est refusé,
  `PerimetreDesSignalements` plafonnant à `SOI` pour qui n'a ni ADM-E, ni SUPER, ni ESM. L'ÉCRITURE
  (changer l'état) exige `ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS` (ADM-E/SUPER seuls, confirmé dans
  `app/support/perimetre.py`).
- **Alertes** (`T13`) : la lecture elle-même refuse DSM/BOOST/OFFICE/EMP en bloc —
  `PerimetreDesAlertes` ne rend `LIMITE` qu'à l'ESM, `COMPLET` qu'à ADM-E/SUPER, `None` (refus) à
  tous les autres. **L'écriture (acquitter/commenter/résoudre) refuse aussi l'ESM** : mesuré dans
  `app/support/routes.py`, les trois routes `POST` partagent la MÊME garde
  (`garde_du_traitement_des_alertes`, construite sur `ROLES_DE_TRAITEMENT_DES_ALERTES`,
  `ADM-E`/`SUPER` seuls) — un ESM au périmètre `LIMITE` lit mais n'écrit jamais, confirmé en lisant
  le code des routes plutôt que supposé par symétrie avec les signalements.
- **Demandes RGPD** (`T14`) : une seule grille (`ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD`,
  ADM-E/SUPER) garde les six routes, lecture et écriture confondues — aucune visibilité partielle,
  aucun plancher `Soi`.

L'onglet « Support » lui-même reste **visible à toute session établie** (`visible: () => true`),
même parti que « Pilotage » : le masquer entièrement priverait un `DSM` ou un `OFFICE` de la seule
chose que la matrice leur accorde — consulter ses propres signalements. Chaque panneau se garde
ensuite séparément à l'intérieur de l'onglet.

### 2.4 Aucune route API nouvelle

Les dix-neuf routes consommées existaient toutes avant `T15`. Six nouvelles grilles de rôles ont
été ajoutées au manifeste (`rolesDeLAudit`, `rolesDetailsTechniquesDeLAudit`,
`rolesExportDeLAudit`, `rolesTraitementDesSignalements`, `rolesTraitementDesAlertes`,
`rolesTraitementDesDemandesRGPD`) — posées côté Python depuis `T8` à `T14` sans jamais avoir eu de
consommateur, même situation que les cinq grilles de `T14` du LOT 9. Chacune est confrontée à sa
constante Python réelle par un nouveau fichier de test, `test_contrat_roles_lot10.py`, dans les
deux sens — même discipline que `test_contrat_roles_lot9.py`.

## 3. Ce qui a été produit

### 3.1 Cinq nouveaux modules de contrat TypeScript

- `packages/contracts/src/audit.ts` — journal d'audit et export CSV. Pas de validateur pour
  l'export : la réponse est `text/csv` brut (`forme: "octets"` au manifeste), rien à valider dans
  des octets.
- `packages/contracts/src/reporting.ts` — indicateurs, détail onboarding, profils incomplets.
  Réutilise `ROLES_TABLEAU_DE_BORD`/`peutConsulterLeTableauDeBord` de `tableauDeBord.ts`, aucune
  déclaration propre.
- `packages/contracts/src/traitementDesSignalements.ts` — déclaré séparément de `signalement.ts`
  (LOT 10 `T11`), qui reste la SEULE écriture ouverte à toute session. Deux publics, deux modules,
  même discipline que `contenus.ts`/`gestionDuContenu.ts` au LOT 6.
- `packages/contracts/src/alertes.ts` — les six routes `/alerts/*`, ressource globale.
- `packages/contracts/src/rgpd.ts` — les six routes `/data-subject-requests*`, ressource globale.

Chacun suit le montage déjà établi : `endpoint('clé')` lit chemin et codes exploitables depuis
`contrat-api.json` (source unique, `DEC-492`), un validateur dédié par forme de réponse, aucun
`URLSearchParams` (bibliothèque DOM absente du `lib` TypeScript du paquet — un tableau de chaînes
et `encodeURIComponent` suffisent, même motif documenté dans `trombinoscope.ts`).

### 3.2 Les clients API frontend

`apps/web/src/api/audit.ts`, `reporting.ts`, `traitementDesSignalements.ts`, `alertes.ts`,
`rgpd.ts` — même montage que `organisation.ts` pour les écritures (jeton anti-CSRF lu au dernier
instant via `GET /auth/session`, clé d'idempotence par tentative). **Exception mesurée, pas
supposée** : l'export d'audit n'envoie AUCUN jeton CSRF, parce que `app/audit/routes.py` n'importe
jamais `proteger_du_csrf` — à la différence de `app/support/routes.py` et `app/privacy/routes.py`,
qui l'importent et l'appellent sur toutes leurs écritures. Le client reflète ce que l'API fait
réellement.

### 3.3 Trois composants d'écran

- `SectionAudit.tsx` — filtres, tableau du journal, pagination, export CSV déclenché par
  `URL.createObjectURL`/clic simulé/`URL.revokeObjectURL`.
- `SectionSupport.tsx` — trois panneaux (`PanneauSignalements`, `PanneauAlertes`, `PanneauRGPD`),
  chacun avec sa propre garde, sa propre liste et son propre formulaire d'action.
- `SectionPilotage.tsx` étendu d'une troisième section, `SectionReportingEtendu` : quatre
  grandeurs (onboardings terminés, progression moyenne, durée moyenne, arrivées à 30 jours) et
  trois répartitions (cercle/client/DSM), gardées par la MÊME fonction que le tableau de bord.

`PageAdministration.tsx` passe de sept à neuf onglets, les deux nouveaux ajoutés **après** les
sept du cahier plutôt que mélangés dedans — dire honnêtement qu'ils ne viennent pas de la même
liste.

## 4. Contrôles exécutés et résultats

```bash
pnpm --filter @onboarding/contracts exec tsc --noEmit     # vert
pnpm --filter @onboarding/web exec tsc --noEmit           # vert
pnpm exec eslint .                                        # vert
pnpm exec prettier --check .                               # vert
uv run ruff check . && uv run ruff format --check .        # vert
uv run mypy                                                 # vert, 276 fichiers
make sources-check                                          # vert
make parametres-check                                       # vert
make docs-check                                              # vert
```

`uv run pytest apps/api/tests/test_contrat_roles_lot10.py` : 6/6, les six grilles confrontées dans
les deux sens dès la première exécution — confirmant que le manifeste écrit pour `T15` reflète
EXACTEMENT les six constantes Python de `T8` à `T14`.

Vitest : **889 au total** (459 `contracts` + 120 `ui` + 310 `web`, +77 par rapport à `T14`) —
74 tests de contrat nouveaux (`audit.test.ts`, `reporting.test.ts`,
`traitementDesSignalements.test.ts`, `alertes.test.ts`, `rgpd.test.ts` : validateurs
positifs/négatifs, construction de chemin avec filtres et pagination, grilles de rôles pures), 3
tests nouveaux dans `SectionPilotage.test.tsx` pour le reporting étendu.

**Deux tests existants corrigés, régression ATTENDUE et non un défaut** : `PageAdministration.test.tsx`
supposait exactement sept onglets pour un `SUPER` et trois pour un `EMP` (Contenu, Pilotage,
Configuration) — devenu neuf et quatre (« Support » rejoint la liste de l'`EMP`, jamais « Audit »,
que `ROLES_DE_L_AUDIT` lui refuse). Corrigés pour affirmer la nouvelle réalité, pas pour masquer un
défaut.

`uv run pytest -q --collect-only` : **1 992 tests collectés** (+6 par rapport à `T14`, tous
unitaires — `test_contrat_roles_lot10.py` ne requiert aucune base). `uv run pytest -m integration
-q --collect-only` : 1 520, inchangé — aucun test d'intégration nouveau, `T15` ne touchant aucune
route.

Zéro régression mesurée par comparaison de worktree avec `origin/develop` (§7.22) : `pytest`
racine lancé sur les deux — `81 failed, 1911 passed` sur la branche, `83 failed, 1903 passed` sur
`origin/develop` — listes de tests en échec triées et comparées terme à terme. **La différence
porte EXCLUSIVEMENT sur `test_debit.py`** (3 échecs sur la branche contre 5 sur `origin/develop`,
jamais les mêmes trois tests précisément) : les deux `pytest` ont été lancés l'un après l'autre
contre le **même conteneur Redis réel** (127.0.0.1, le même `.env`), et les fenêtres de limitation
de débit par adresse (dix requêtes, cahier §20.2) se chevauchent d'une exécution à l'autre — un
état partagé entre les deux worktrees, jamais un défaut introduit par `T15`. **Sur les 78 AUTRES
échecs, les deux listes triées sont STRICTEMENT IDENTIQUES**, `diff` vide (`/tmp/t15_branch_no_
debit.txt` contre `/tmp/t15_baseline_no_debit.txt`). `T15` ne touchant aucune route ni aucun test
d'intégration, ce résultat était attendu — la preuve reste faite, pas supposée.

### 4.1 Aller-retour réel (§7.43)

Après `make code-refresh`, à travers Caddy en HTTPS, avec un compte `SUPER_ADMIN` créé pour
l'occasion (`person` + `entity_membership` active + `technical_role_assignment` global, lien
magique réel demandé et consommé via Mailpit — décor entièrement nettoyé après coup) :

1. les neuf onglets apparaissent dans l'ordre attendu ;
2. l'onglet « Audit » affiche le journal RÉEL de l'entité, y compris l'événement de connexion qui
   vient d'être posé (`MAGIC_LINK_USED`), avec la colonne « référence/corrélation » visible (le
   compte est `SUPER`) ;
3. le bouton « Exporter en CSV » déclenche un POST réel, `200`, téléchargement effectif ;
4. l'onglet « Support » affiche ses trois panneaux, états vides corrects pour les signalements et
   les alertes (aucune donnée de démonstration dans l'entité visée) ;
5. le cycle RGPD complet est exécuté en direct : réception (`POST /data-subject-requests`, `201`,
   `due_at` = `received_at` + exactement 30 jours mesuré), liste rafraîchie, vérification
   d'identité (`200`, `identite_verifiee: true`), clôture avec réponse (`200`, `etat: closed`) —
   chaque écriture relue immédiatement dans le tableau.

Signalements et alertes n'avaient aucune donnée à exercer en écriture lors de cet aller-retour
(aucun signalement ni alerte n'existait dans l'entité visée, et en créer directement en base
aurait contourné les écritures réelles que l'aller-retour doit justement prouver) ; leurs panneaux
ont été vérifiés en lecture et leurs clients API partagent exactement le même montage CSRF/clé
d'idempotence que celui prouvé en direct pour la RGPD — déjà éprouvé côté API par les 35 et 54
tests de `T12`/`T13` respectivement.

### 4.2 Deux défauts trouvés par la CI sur la pull request, corrigés avant la fusion

**`T15-1` : un rôle écrit en littéral dans le frontend.** `make cadre-check` a refusé
`SectionSupport.tsx` : `roles.includes('ESM')` écrivait un rôle en dur côté client, en violation de
`DEC-492` (les rôles viennent du manifeste, source unique de TypeScript et Python). Le périmètre
`LIMITE` de l'ESM sur les alertes n'a pas de grille statique exposée par l'API
(`app/support/perimetre_alertes.py`) — le défaut est corrigé en exportant `peutLireLesAlertes`
depuis `packages/contracts/src/alertes.ts`, qui encapsule l'union `peutTraiterLesAlertes` ∪ `ESM`
sans qu'aucun littéral de rôle ne vive plus dans `apps/web`.

**`T15-2` : un override pnpm écrit comme un plancher était une épingle exacte.** `make audit` a
trouvé trois avis publiés depuis la dernière exécution de la CI, sans rapport avec `T15` —
`uv.lock`/`pnpm-lock.yaml` étaient identiques à `origin/develop` avant ces commits. `filelock`
(trois CVE, dépendance transitive de `pip-audit` lui-même, jamais consommée en exécution) et `zod`
(dépendance de développement d'`eslint-plugin-react-hooks`) se sont corrigés par une simple montée
dans les plages déjà déclarées. `undici` (trois CVE, corrigées en `8.12.2`) a révélé un défaut plus
sérieux, dormant depuis `GHSA-3wwx-pv8p-q78v` : `pnpm-workspace.yaml` portait
`overrides: { undici: 8.10.2 }`, posé comme un **plancher corrigé** — mais une version NUE dans
`overrides` est une **épingle exacte** pour pnpm, jamais un plancher. Elle bloquait donc
silencieusement toute résolution plus récente, y compris celle que `jsdom@30.1.3` demande déjà
(`^8.12.1`). Même classe que `§7.34` de la passation : un garde-fou écrit contre un incident ne
couvre pas sa classe. Corrigé en `>=8.10.2` (et `source-map-js: >=1.2.2`, même défaut, même
correctif), `jsdom` monté à `^30.1.3` dans les deux `package.json` qui le déclarent.

Vérifié dans les deux sens après chaque correctif : `make audit`/`make cadre-check`/`make
format-check`/`lint`/`typecheck`/`mypy` verts, 889 Vitest et 472 tests pytest unitaires inchangés.
Aucun des deux défauts n'a nécessité de nouvel arbitrage de Jonathan ni de nouvelle décision —
corrections mécaniques sous la discipline déjà posée par `DEC-492` et `DEC-474`/`DEC-493`.

## 5. Décisions et écarts

`DEC-669` : organisation des écrans back-office du LOT 10 en deux onglets de plus (« Audit »,
« Support »), le reporting étendu rejoignant « Pilotage » — arbitrage explicite de Jonathan.

Aucun écart ouvert ni fermé. `QO-126` (ligne « Consulter les événements » du §15.1, non construite
par `T10`) reste ouverte et non bloquante, `T15` n'y touchant pas.

## 6. Ce que `T15` laisse

- Le filtre `acteur` du journal d'audit n'a pas de champ dans l'écran, faute de route listant les
  personnes toutes entités confondues (résidu nommé, §2.2).
- Aucune donnée de démonstration n'existe pour les signalements et les alertes dans l'entité
  vérifiée en direct : un geste futur de recette (`T16`) ou une démonstration client devra en
  déposer pour montrer ces deux panneaux en écriture.
- `T16` est la sous-étape suivante : la recette de clôture du LOT 10 — reclassement du §30 du
  modèle, checklist `G10`.

---

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
