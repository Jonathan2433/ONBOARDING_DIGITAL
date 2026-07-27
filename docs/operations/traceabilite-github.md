# Traçabilité GitHub

**Produit en :** LOT 0, sous-étape S3 — story `MVP-L00-US003`
**Fondement :** backlog section 11, « Traçabilité GitHub recommandée », et décision `BACKLOG-010`

Objectif : qu'on puisse remonter, pour n'importe quelle ligne de code, à la story, à la
décision qui la justifie et à la preuve de test qui la valide.

```text
Lot  ──►  Epic (issue)  ──►  Story (issue)  ──►  Pull request  ──►  Preuve de test
 │                                │                    │
 └──► Milestone = porte Gx        └──► Decision source  └──► Closes #story
```

---

## 1. Structure imposée par le backlog

| Élément | Règle |
|---|---|
| Epic | Une issue d'epic par lot, soit 15 epics MVP |
| Story | Une issue par user story, soit 112 issues MVP |
| Tâches techniques | Sous-issues ou liste de cases à cocher dans l'issue de story |
| Milestone | Correspond à la porte de validation, `G0` à `G14` |
| Lien source | Lien obligatoire vers la décision ou le document source |
| Pull request | Liée à l'issue, avec preuve de test dans la description |

---

## 2. Étiquettes

### 2.1 Étiquettes prescrites par le backlog

Ces trois familles sont imposées. Elles ne se substituent pas les unes aux autres : une story
porte normalement une étiquette de version, une de priorité et au moins une de domaine.

| Famille | Étiquettes | Couleur proposée |
|---|---|---|
| Version | `mvp`, `v1`, `v2` | `#0E8A16`, `#FBCA04`, `#D93F0B` |
| Priorité | `p0`, `p1`, `p2` | `#B60205`, `#D93F0B`, `#FEF2C0` |
| Domaine | `frontend`, `backend`, `data`, `infra`, `security`, `a11y`, `content` | `#1D76DB`, `#5319E7`, `#0052CC`, `#006B75`, `#B60205`, `#7057FF`, `#C2E0C6` |

### 2.2 Compléments recommandés

**Statut : recommandation, non prescrite par les documents validés.** À valider par Jonathan
avant création.

| Famille | Étiquettes | Utilité |
|---|---|---|
| Type | `epic`, `story`, `anomalie`, `dette`, `question`, `risque` | Distinguer la nature d'une issue au premier regard |
| Gravité | `bloquante`, `critique`, `majeure`, `mineure` | Rendre visible l'effet sur la porte, cahier §29.3 |
| État | `blocked`, `deferred` | Rendre visibles les états du backlog §2.4 qui ne sont pas déductibles de la colonne du tableau de bord |

Les états `Planned`, `Ready`, `In progress`, `Review` et `Done` sont portés par les colonnes
du tableau de projet, pas par des étiquettes, afin d'éviter deux sources de vérité.

---

## 3. Milestones

Une milestone par porte de validation. Elle est fermée quand Jonathan valide la porte.

| Milestone | Titre | Stories |
|---|---|---:|
| `G0` | Référentiel projet et préparation | 7 |
| `G1` | Monorepo, qualité et environnement local | 8 |
| `G2` | Socle de données et isolation multi-entités | 8 |
| `G3` | Authentification, sessions et sécurité applicative | 8 |
| `G4` | Portail national, sélection d'entité et navigation | 7 |
| `G5` | Collaborateurs, profils et organisation | 8 |
| `G6` | Framework, cercles, bureaux et contenus éditoriaux | 7 |
| `G7` | Fiches d'arrivée et onboarding | 8 |
| `G8` | Événements et accueil dynamique | 6 |
| `G9` | Back-office, administration et import CSV | 8 |
| `G10` | Audit, reporting, supervision fonctionnelle et support | 8 |
| `G11` | Médias, worker et tâches planifiées | 8 |
| `G12` | Qualité transversale, sécurité, accessibilité et performance | 8 |
| `G13` | Production temporaire locale | 6 |
| `G14` | Préparation et ouverture de la production générale | 7 |

Total : **112 stories**, dont **94 `P0`** — chiffres recomptés et vérifiés en sous-étape S2.

---

## 4. Règles de fermeture

| Élément | Se ferme quand |
|---|---|
| Story | Sa définition de Done est satisfaite et sa pull request est fusionnée |
| Epic | Toutes ses stories `P0` sont fermées et ses `P1` sont fermées ou arbitrées |
| Milestone | Jonathan valide explicitement la porte |
| Anomalie | Corrigée et vérifiée, ou rejetée avec motif tracé |

Une porte ne peut pas être fermée si (backlog §12) :

- une story `P0` du lot n'est pas terminée ;
- une permission critique n'est pas testée ;
- une migration ne fonctionne pas sur une base propre ;
- un secret ou une donnée réelle a été versionné ;
- une anomalie bloquante ou critique reste ouverte ;
- un comportement mobile ou clavier essentiel est inutilisable ;
- la démonstration ne correspond pas aux critères de la roadmap ;
- la documentation minimale de reprise ou d'exploitation manque ;
- Jonathan n'a pas donné sa validation explicite.

---

## 5. Mise en place

Ces éléments se créent dans l'interface GitHub, ou en ligne de commande lorsque `gh` sera
installé. `gh` n'est **pas** installé sur la machine à ce jour : les commandes ci-dessous
sont fournies pour exécution ultérieure et n'ont pas été exécutées.

### 5.1 Étiquettes prescrites

```bash
# Version
gh label create mvp      --color 0E8A16 --description "Perimetre MVP"
gh label create v1       --color FBCA04 --description "Perimetre V1"
gh label create v2       --color D93F0B --description "Perimetre V2 conditionnel"
# Priorite
gh label create p0       --color B60205 --description "Bloquant de lot ou de securite"
gh label create p1       --color D93F0B --description "Important dans le perimetre valide"
gh label create p2       --color FEF2C0 --description "Amelioration differable"
# Domaine
gh label create frontend --color 1D76DB
gh label create backend  --color 5319E7
gh label create data     --color 0052CC
gh label create infra    --color 006B75
gh label create security --color B60205
gh label create a11y     --color 7057FF
gh label create content  --color C2E0C6
```

### 5.2 Milestones

```bash
for i in $(seq 0 14); do
  gh api repos/:owner/:repo/milestones -f title="G$i" -f state=open >/dev/null
done
```

### 5.3 Protection des branches

À appliquer par Jonathan, conformément à la décision `DEC-429` : pull request obligatoire,
**zéro approbation requise**, rejet des push directs et forcés. Les réglages détaillés
figurent dans
[conventions-git-et-versions.md, section 2](conventions-git-et-versions.md).

Chemin dans l'interface : `Settings` → `Branches` → `Add branch protection rule`, ou
`Settings` → `Rules` → `Rulesets` selon ce que propose le plan du compte.

---

## 6. Limite connue

Aucune de ces créations n'a été effectuée : `gh` n'est pas installé et aucun connecteur
GitHub n'est disponible dans la session de travail. La mise en place effective des
étiquettes, des milestones, des epics, des issues et de la protection de branche reste à
réaliser, et constitue un prérequis de la traçabilité attendue au LOT 1.
