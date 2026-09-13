# Conventions Git, branches, commits, tags et versions

**Produit en :** LOT 0, sous-étape S3 — story `MVP-L00-US003`
**Fondement :** cahier des charges sections 23.1 à 23.4 et 29.8, backlog section 11
**Décisions applicables :** `DEC-427`, `DEC-428`, `DEC-429`, **`DEC-495`**
**Mis à jour le :** 12 août 2026 — **§2 et §2.1 se contredisaient**, voir `ECART-026`

Ce document est la référence normative. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) en donne
le mode d'emploi au quotidien.

---

## 1. Modèle de branches

Le modèle est imposé par le cahier des charges : une fusion sur `develop` déploie la recette
locale (§23.2), un tag versionné déclenche le déploiement en production temporaire (§23.3).

```text
  feat/l02-us004-historisation-dsm ──┐
  fix/l03-us002-magic-link-rejoue  ──┤
  docs/l00-us003-conventions-git   ──┤
                                     ▼
                                 develop ──────────► recette locale (automatique)
                                     │
                                     ▼
                                   main ───► tag vX.Y.Z ───► production temporaire
                                                              (après validation manuelle)
```

| Branche | Rôle | Règles |
|---|---|---|
| `main` | État livrable. Porte les tags de version. | Protégée. Aucun push direct, aucun push forcé. Fusion uniquement par pull request. |
| `develop` | Intégration continue. Déploie la recette locale à chaque fusion. | Fusion uniquement par pull request depuis une branche de travail. |
| branches de travail | Une story ou une correction. | Créées **depuis `develop`**, fusionnées **dans `develop`**. Supprimées après fusion. |
| `hotfix/*` | Correction urgente d'un défaut bloquant en production. | Créée depuis `main`. Fusionnée dans `main` **et** dans `develop`, pour éviter la régression au cycle suivant. |

### 1.1 Nommage des branches de travail

```text
<type>/l<NN>-us<NNN>-<resume-court-en-kebab-case>
```

| Élément | Règle | Exemple |
|---|---|---|
| `<type>` | Même vocabulaire que les types de commit | `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`, `build` |
| `l<NN>` | Numéro du lot sur deux chiffres | `l00`, `l02`, `l14` |
| `us<NNN>` | Numéro de la story dans le lot | `us004` |
| résumé | Kebab-case, minuscules, sans accent, 5 mots maximum | `historisation-dsm` |

Exemples valides :

```text
feat/l02-us004-historisation-dsm
fix/l03-us002-magic-link-rejoue
docs/l00-us006-registres-projet
chore/l01-us005-ci-lint-types
```

Une branche sans story rattachée n'est acceptée que pour un travail transverse explicitement
décidé ; elle porte alors le type `chore` et un résumé sans identifiant de story.

### 1.2 Application du circuit

**Décision `DEC-427` :** le circuit branche + pull request s'applique **à partir du premier
commit de code du LOT 1**. Les sous-étapes documentaires restantes du LOT 0 (S3 à S8)
continuent en commits directs sur `main`, chacune validée explicitement par Jonathan avant
la suivante — la revue existe donc déjà, à chaque sous-étape.

Motif : au LOT 0 aucune chaîne d'intégration continue n'existe encore. Une pull request n'y
vérifierait rien automatiquement.

---

## 2. Protection de la branche `main`

**Décision `DEC-429` :** `main` est protégée avec pull request obligatoire et **zéro
approbation requise**.

Motif : GitHub interdit d'approuver sa propre pull request. Exiger une approbation
bloquerait toute fusion tant que Jonathan est l'unique relecteur — c'est l'objet de la
question ouverte `QO-094`, second référent technique avant production. La revue reste
effective : elle est portée par la validation de sous-étape et la lecture avant fusion.

Réglages à appliquer sur `main`, puis sur `develop` :

| Réglage | Valeur | Motif |
|---|---|---|
| Pull request obligatoire avant fusion | Activé | Cahier §23.1 |
| Nombre d'approbations requises | **0** | Éviter le blocage par auto-approbation impossible |
| Rejet des push directs | Activé | Intégrité de l'historique |
| Rejet des push forcés | Activé | Un historique validé ne se réécrit pas |
| Rejet des suppressions de branche | Activé | — |
| Contrôles d'intégration obligatoires | **Activés** depuis `T6` du LOT 1 — la porte de `ci.yml`, **contexte unique**, `strict` actif, sur `develop` **et** `main` (`DEC-476`) | Cahier §23.1 |
| ~~La porte de `images.yml`~~ | **NON requise, et ne doit pas le devenir** — elle ne s'exécute jamais sur une pull request (cahier §23.1), donc l'exiger bloquerait toute fusion sur un contrôle qui ne peut pas rendre de verdict | `DEC-475` |
| Résolution des conversations avant fusion | Activé | Traçabilité de la revue |
| Historique linéaire requis | **Sur `develop` seulement** | Voir l'avertissement ci-dessous : appliqué à `main`, ce réglage rend le §2.1 inapplicable. `DEC-495` |

> **⚠️ Ce réglage et la stratégie de fusion du §2.1 S'EXCLUENT sur `main`, et cela a été mesuré,
> non déduit.** « Historique linéaire requis » **refuse tout merge commit**. Appliqué à `main`, il
> rend la ligne « `develop` → `main` : merge commit » du §2.1 **impossible à honorer**, et la fusion
> se rabat sur le squash — **qui coupe `main` de l'histoire de `develop`**.
>
> **La conséquence est cumulative, et c'est ce qui la rend sérieuse.** Deux branches qui ne partagent
> aucune histoire conflictent sur **tout** fichier touché des deux côtés, alors que le contenu ne
> divergeait pas. Constaté le 12/08/2026 sur la pull request `#33` : **9 fichiers en conflit,
> insolubles** — leur résolution exigeait elle-même un merge commit sur `develop`.
>
> **Réglage retenu, `DEC-495` :** exigé sur **`develop`**, où toutes les fusions sont des squash de
> branches de travail ; **retiré sur `main`**, qui reçoit des merge commits. Mesuré après
> application le 12/08/2026 : `main` → `false`, `develop` → `true`, les six autres réglages
> inchangés. Voir `ECART-026`.

Si le plan GitHub du compte ne permet pas les règles de protection sur un dépôt privé
personnel, le repli documenté est un garde-fou local `pre-push` refusant tout push direct
sur `main` et `develop`. Ce repli ne remplace pas la protection côté serveur et doit être
consigné comme risque accepté.

### 2.1 Stratégie de fusion

| Contexte | Méthode | Motif |
|---|---|---|
| Branche de travail → `develop` | **Squash and merge** | Un commit lisible par story, historique de `develop` propre |
| `develop` → `main` | **Merge commit** | Conserve la traçabilité de l'ensemble intégré et validé |
| `hotfix/*` → `main` | **Merge commit** | Conserve le contexte de l'urgence |

> **Le merge commit de `develop` → `main` n'est pas un ornement : il est ce qui fait de `develop` un
> ANCÊTRE de `main`.** Sans lui les deux branches ne partagent aucune histoire, et chaque porte
> reconflicte. Un **squash annulerait l'effet** en aplatissant les deux parents — c'est ce qui est
> arrivé à la PR `#30`, et il a fallu la PR `#35` pour le réparer.
>
> **Il exige que « historique linéaire requis » soit RETIRÉ sur `main`** : voir l'avertissement du §2
> et `DEC-495`.
>
> **Contrôle de la fusion, et il ne porte pas sur la résolution mais sur son RÉSULTAT :** après une
> fusion `develop` → `main`, l'arbre de `main` doit égaler celui de `develop` **à l'octet près**, et
> `develop` doit être un **ancêtre** de `main`.
>
> ```bash
> git rev-parse origin/main^{tree} origin/develop^{tree}   # doivent etre IDENTIQUES
> git merge-base --is-ancestor origin/develop origin/main  # doit sortir en 0
> git rev-parse origin/main^@ | wc -l                      # 2 = merge commit, 1 = squash
> ```
>
> **Ce contrôle a attrapé un défaut réel le 12/08/2026.** Une résolution en `git merge -X theirs`
> avait rendu un arbre **divergent** : la stratégie conserve les fragments **non conflictuels** du
> côté abandonné, et elle avait gardé un bloc de `fiche-lot-1.md` **en plus** de la version qui le
> remplaçait — **41 lignes dupliquées, aucun conflit signalé**. Sans la comparaison des arbres, cette
> fusion passait en paraissant propre.

---

## 3. Convention de messages de commit

Format retenu : **Conventional Commits**, rédigé en français.

```text
<type>(<portée>): <sujet à l'impératif, en minuscules, sans point final>

<corps : ce qui change et pourquoi, avec le lot et la story concernés>

<pied : références, changement incompatible, co-auteurs>
```

### 3.1 Types autorisés

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité ou capacité métier |
| `fix` | Correction d'un défaut |
| `docs` | Documentation seule |
| `chore` | Outillage, dépendances, tâches sans effet fonctionnel |
| `refactor` | Restructuration sans changement de comportement |
| `test` | Ajout ou correction de tests |
| `perf` | Amélioration de performance |
| `ci` | Chaîne d'intégration et de déploiement |
| `build` | Construction, images, empaquetage |
| `revert` | Annulation d'un commit antérieur |

### 3.2 Portées autorisées

Alignées sur le monorepo et sur les modules backend validés.

| Groupe | Portées |
|---|---|
| Applications et paquets | `web`, `api`, `worker`, `ui`, `contracts`, `infra` |
| Modules backend | `auth`, `entities`, `people`, `organization`, `onboarding`, `events`, `media`, `imports`, `reporting`, `audit`, `administration`, `jobs`, `configuration`, `shared` |
| Transverse | `docs`, `cadrage`, `repo`, `ci`, `deps`, `security`, `a11y`, `perf`, `data` |

La portée est facultative pour un changement réellement transverse.

### 3.3 Règles de rédaction

- sujet de 72 caractères au maximum, à l'impératif : « ajouter », non « ajout » ni « ajoute » ;
- corps recommandé dès que le « pourquoi » n'est pas évident, lignes de 80 caractères au plus ;
- le corps cite le lot et la story : `LOT 2 - story MVP-L02-US004` ;
- le pied référence l'issue : `Refs: #42` ;
- un changement incompatible se déclare par `BREAKING CHANGE:` en pied, et impose une
  décision tracée si une exigence validée est touchée ;
- **aucun secret, aucun jeton, aucun mot de passe, aucun magic link, aucune donnée
  personnelle** dans un message de commit : un message est aussi indélébile que le code.

### 3.4 Exemple

```text
feat(onboarding): conserver les taches communes lors d'un changement de parcours

LOT 7 - story MVP-L07-US007.

Le passage intercontrat vers mission remplace l'instance active. Les taches
communes deja terminees sont conservees par identifiant stable de tache de
reference, conformement a DATA-007 et a la matrice section 8.2.

L'ancienne instance passe en etat replaced sans perte d'historique. L'audit et
les evenements de tache sont ecrits dans la meme transaction.

Refs: #57
```

---

## 4. Versions et tags

**Décision `DEC-428` :** versionnement sémantique préfixé `v`, jalonné sur les portes de
validation. Un tag mineur est posé sur `main` à chaque porte validée ; `v1.0.0` marque
l'ouverture générale.

| Porte validée | Tag | Signification |
|---|---|---|
| `G1` | `v0.1.0` | Socle local exécutable |
| `G2` | `v0.2.0` | Modèle de données implémenté |
| `G3` | `v0.3.0` | Authentification et sessions |
| `G4` | `v0.4.0` | Portail national et navigation |
| `G5` | `v0.5.0` | Trombinoscope et profils |
| `G6` | `v0.6.0` | Framework, cercles, bureaux, contenus |
| `G7` | `v0.7.0` | Fiches d'arrivée et onboarding |
| `G8` | `v0.8.0` | Événements et accueil |
| `G9` | `v0.9.0` | Back-office et import CSV |
| `G10` | `v0.10.0` | Audit, reporting, support |
| `G11` | `v0.11.0` | Médias, worker, planification |
| `G12` | `v0.12.0` | Recette transverse close |
| `G13` | `v0.13.0` | Production temporaire locale |
| `G14` | **`v1.0.0`** | Ouverture générale à tous les employés |

Règles complémentaires :

- `PATCH` est incrémenté pour une correction sur un lot déjà validé, par exemple `v0.5.1` ;
- `G0` ne produit aucun tag : le LOT 0 ne livre aucun exécutable ;
- un tag est **annoté** et posé exclusivement sur `main` ;
- un tag posé n'est jamais déplacé ni supprimé ;
- la version doit être exposée par l'API sur `/health/version` et correspondre au build
  (cahier §18.7, story `MVP-L01-US003`).

```bash
git tag -a v0.1.0 -m "LOT 1 valide - porte G1 - socle local executable"
git push origin v0.1.0
```

### 4.1 Étiquetage des images

Cahier §23.3 : « La production utilise des références immuables, jamais uniquement
`latest` ».

| Étiquette | Exemple | Usage |
|---|---|---|
| Version exacte | `:0.1.0` | **Seule** référence autorisée en production temporaire et générale |
| Empreinte de commit | `:sha-4e60857` | Traçabilité, diagnostic, rejeu |
| `develop` | `:develop` | Recette locale uniquement |
| `latest` | `:latest` | Toléré comme alias de commodité en développement ; **interdit** comme référence unique de déploiement |

Chaque image est construite pour `linux/arm64` et `linux/amd64` (cahier §22.3) et publiée
dans GHCR privé.

### 4.2 Compatibilité de schéma et retour arrière

Cahier §29.8 : « Un rollback applicatif doit vérifier la compatibilité du schéma avant
redémarrage d'une ancienne image ».

- une migration doit rester compatible avec la version applicative précédente à l'intérieur
  d'une même version mineure, chaque fois que c'est possible ;
- une migration destructive ou incompatible est signalée dans le message de commit **et**
  dans les notes de version, et impose une sauvegarde préalable ;
- avant tout retour arrière, la compatibilité du schéma est vérifiée : à défaut, la
  restauration de sauvegarde prévaut sur le redémarrage d'une ancienne image.

---

## 5. Revue et fusion

Une pull request n'est fusionnable que si :

1. elle référence une story et le document ou la décision source (backlog §11) ;
2. la définition de Done de la story est satisfaite (backlog §4) ;
3. les preuves de test figurent dans la description ;
4. les permissions autorisées **et refusées** sont testées, dès que la story touche aux droits ;
5. les contrôles d'intégration sont verts, dès le LOT 1 ;
6. aucun secret, aucune donnée réelle, aucun média n'est ajouté ;
7. les conversations de revue sont résolues.

Une anomalie de sécurité, d'intégrité, d'isolation multi-entités ou d'accessibilité
essentielle **préempte** le travail du lot en cours (`ARB-BACK-005`, `BACKLOG-008`).

---

## 6. Interdictions

- pousser directement sur `main` ou `develop` ;
- réécrire l'historique d'une branche partagée ;
- fusionner sans pull request, dès le LOT 1 ;
- déplacer ou supprimer un tag publié ;
- référencer `latest` seul pour un déploiement ;
- versionner un secret, un CSV réel, une photo, un média ou une donnée personnelle ;
- inscrire une donnée sensible dans un message de commit, un titre de branche ou une
  description de pull request ;
- contourner une exigence `Must` ou une story `P0` sans décision explicite et tracée.
