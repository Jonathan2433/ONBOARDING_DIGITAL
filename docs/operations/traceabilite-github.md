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

> **✅ Mise en place effectuée le 27 juillet 2026**, en sous-étape `T0` du LOT 1, par `gh` en
> ligne de commande (`DEC-449`). `gh` **2.96.0 est installé** dans `~/.local/bin/gh` — hors
> Homebrew, dont les répertoires appartiennent à l'utilisateur `admin`. Ce chemin **n'est pas
> dans le `PATH`** : préfixer par `export PATH="$HOME/.local/bin:$PATH"`.
>
> Les commandes ci-dessous ont été **exécutées et contrôlées**. Elles sont conservées comme
> référence reproductible.

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

## 6. État de la mise en place

Au 27 juillet 2026, sous-étape `T0` du LOT 1. `ECART-010` **clos**, `QO-107` et `QO-108`
**closes**. **État des issues remesuré le 13 septembre 2026**, `T1` du LOT 6.

**À la porte `G5`, franchie le 13/09/2026 :** six des huit stories du LOT 5 ont été refermées —
`#116`, `#117`, `#118`, `#119`, `#122`, `#123` — chacune avec un commentaire cochant ses critères
d'acceptation et leurs preuves, ce que le backlog §11 exige. **`#120`, `#121` et l'épic `#115`
restent OUVERTES**, et ce n'est pas un oubli : `US005` porte un critère « retrait possible » qui
n'est pas tenu, et `US006` a une API complète qu'aucun écran n'appelle. **Un critère d'acceptation
non tenu ne se referme pas.**

**Le LOT 6 a reçu sa traçabilité le 13/09/2026** : épic `#145`, stories `#146` à `#152`, jalon `G6`.
Les huit corps ont été **engendrés depuis le backlog** et non transcrits — §6.4.

> **LES NOMBRES CI-DESSOUS SE DÉRIVENT, ET LA COMMANDE FAIT FOI.** Ce tableau a annoncé
> « épics et stories des LOTS 2 à 14 : **non créés** » pendant **quatre lots** — classe
> `ECART-021`.
>
> ```bash
> ~/.local/bin/gh issue list --state all  --limit 300 --json number --jq 'length'   # 52
> ~/.local/bin/gh issue list --state open --limit 300 --json number --jq 'length'   # 11
> ```

| Élément | État | Contrôle |
|---|---|---|
| 13 étiquettes prescrites | **Créées** | 13/13 conformes en **nom et couleur** |
| Étiquettes complémentaires `type`, `gravité`, `état` | **Non créées** | Non prescrites — `QO-106` reste ouverte |
| 9 étiquettes GitHub par défaut | **Conservées** | Leur suppression appartient à Jonathan |
| 15 milestones `G0` à `G14` | **Créées** | 15/15, **`G0` fermée** (`DEC-438`) |
| Epic du LOT 1 | **Créé** — issue `#1` | Rattaché à `G1` |
| Stories du LOT 1 | **Créées** — issues `#2` à `#9` | 8/8 sur `G1`, 7 `p0` + 1 `p1`, intitulés et critères **générés depuis le backlog**, fidélité 8/8 |
| Epics et stories des LOTS 2, 3 et 4 | **Créés et CLOS** | LOT 2 : epic + 8 stories · LOT 3 : epic `#62`, stories `#63`–`#70` · LOT 4 : epic `#91`, stories `#92`–`#98`, **les sept closes**, `#92` le 24/08/2026 à 15:31 UTC |
| Epic et stories du LOT 5 | **Créés, OUVERTS** | epic `#115`, stories `#116` à `#123` — **les neuf seules issues ouvertes du dépôt**. `#120` reste ouverte après `T5` : « retrait possible » n'est tenu **qu'en lecture**, aucune route ne permet de retirer |
| Epics et stories des LOTS 6 à 14 | **Non créés** | À créer lot par lot, **quand chaque fiche existe** — jamais par anticipation |
| Protection de `main` et `develop` | **Posée** | PR obligatoire, 0 approbation, `enforce_admins` actif, push forcés et suppressions rejetés, historique linéaire, résolution des conversations |
| Contrôles d'intégration obligatoires | **Posés** | La porte de `ci.yml` est requise sur `develop` **et** `main`, contexte unique, `strict` actif (`DEC-476`). **La porte de `images.yml` n'est PAS requise, et ne doit pas le devenir** |

**Preuve d'effectivité de la protection**, et non simple constat de réglage : un push direct
d'un commit vide sur `main` puis sur `develop` a été **rejeté** par le serveur —
`GH006 : Protected branch update failed … Changes must be made through a pull request`. Témoin
positif : le même push vers une branche neuve non protégée a **réussi**, ce qui établit que le
test distingue bien un succès d'un échec.

Le repli `pre-push` envisagé par `QO-107` est **sans objet** : le plan du compte autorise la
protection de branche sur ce dépôt privé personnel.
