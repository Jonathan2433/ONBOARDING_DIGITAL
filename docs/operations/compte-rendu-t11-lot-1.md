# Compte rendu — sous-étape `T11` du LOT 1

**Exécutée le :** 12 août 2026
**Objet :** contrôles de sortie, checklist de validation et préparation de la porte `G1`
**Story :** aucune. `T11` ne construit rien : elle prouve, elle documente, elle jalonne
**Fondement :** roadmap LOT 1, sept critères de sortie ; backlog §12, neuf critères d'empêchement ; fiche §10 ; `DEC-428`
**Livrable principal :** [`checklist-validation-G1.md`](checklist-validation-G1.md)

---

## 1. Ce que `T11` devait produire, et ce qu'elle produit

| Attendu | Fait |
|---|---|
| Rejouer tous les contrôles et citer leurs **codes de sortie réels** | **33 contrôles, tous à 0** — 24 en développement, 9 en recette, plus les deux qui exigent les deux stacks |
| Vérifier les nombres **par les commandes de dérivation** | tous dérivés, aucun recopié. Détail au §3 |
| Une **checklist** remise à Jonathan | 11 sections, dont une **démonstration guidée** des six éléments de la roadmap |
| Le tag `v0.1.0` | **non posé.** Il attend la validation, et c'est l'ordre que `DEC-428` impose |

**Aucune ligne de code n'a été écrite.** `T11` ne touche que la documentation.

---

## 2. Les contrôles, avec leurs codes de sortie

**Développement — 24 contrôles, tous à 0 :**

```text
tools · versions · tree · icloud-verify · env-check
lint · format-check · typecheck · test · test-unit · test-integration · test-frontend
check · docs-check · audit · images-check
stack-check · health · ports · api-check · web-check
alembic-check · migrate-status · persistence-test
```

**Recette — 9 contrôles, tous à 0 :**

```text
env-check · health · ports · stack-check · api-check
web-check · alembic-check · migrate-status · persistence-test
```

**Les deux ensemble :** `separations-check` → **0**, *57 contrôles, 0 échec, 7 séparations attendues
/ 7 vérifiées*. `recette-check` → **0**.

**Et l'intégration continue, sur les deux branches protégées :**

```text
Integration continue | main    | success | 31606327386
Integration continue | develop | success | 31606316038
```

---

## 3. Les nombres, dérivés et non recopiés

C'est la recommandation 2 du compte rendu de `T9`, et la classe `ECART-021` a coûté trois passes à
ce projet.

| Grandeur | Valeur | Source |
|---|---:|---|
| Tests | **260** — 144 pytest, 116 Vitest | `make check` |
| Cibles `Makefile` | **50** | 50 lignes `##` **et** 50 noms `.PHONY`, dérivé deux fois |
| Fichiers suivis | **170** | `git ls-files` |
| Décisions en usage | **76**, max `DEC-493` | `make docs-check` les **dérive** depuis `T8` |
| Écarts | **24**, 5 ouverts | idem |
| Questions | **39**, 34 ouvertes | idem |
| Risques | **34** | idem |
| Publications de ports | **14** — 7 + 7 | `make ports` par environnement |
| Volumes | **12** — 6 + 6, aucun partagé | `docker volume ls --filter label=…` |
| Comptes rendus de sous-étape | **11** | `ls docs/operations/compte-rendu-t*` |

**Deux vérifications qui ne sont pas des nombres, et que je n'avais pas mesurées moi-même :**

- **`gh secret list` est vide, code 0**, et `gh variable list` aussi : aucun secret ni variable de
  dépôt n'existe. Le critère 3 de sortie repose là-dessus ;
- **la page de statut nomme explicitement les trois services qu'elle ne sonde pas.** Relevé dans
  `PageStatut.tsx` : « worker, Mailpit et Caddy ne sont pas sondés par l'API. La page les nomme
  explicitement plutôt que de laisser croire qu'elle couvre les huit services. »

---

## 4. Un constat sur l'état de `main`, et il aurait pu être mal lu

**Jonathan a fusionné `develop` dans `main` avant `T11`** — pull request #30, commit `be65b53`.

**Une lecture naïve du graphe de commits aurait fait croire que `main` était incomplète :**

```text
git rev-list --left-right --count origin/main...origin/develop   ->  1   18
git rev-list --left-right --count origin/main    origin/develop  ->  0   32
```

Deux syntaxes, deux nombres, et **aucun des deux ne répond à la question**. Ce sont des artefacts
d'une fusion en **squash** : les commits de `develop` n'existent pas dans `main` **par leur
empreinte**, alors que leur **contenu** y est.

**Ce qui fait foi est l'arbre, et il est identique :**

```text
arbre origin/main    : 82086516bff9883d772448fc8ceeb8dd46f91a3b
arbre origin/develop : 82086516bff9883d772448fc8ceeb8dd46f91a3b
git diff --stat origin/main origin/develop  ->  vide
```

> **La leçon, et elle est de la même famille que celles du lot :** quand tu veux savoir si deux
> références portent le même **contenu**, compare les **arbres**, pas les commits. Un compte de
> commits répond à une autre question que celle qu'on croit poser — c'est la sixième proposition de
> la règle du lot, « deux nombres comparés doivent mesurer la même grandeur ».

**Conséquence pratique :** les documents de `T11` demanderont **une seconde fusion** `develop` →
`main` avant que le tag puisse être posé sur un `main` complet.

---

## 5. Défauts détectés pendant `T11`

**Un seul, et il est entièrement de mon fait.**

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T11-1` | **J'ai rejoué le piège du découpage de mots de `zsh`, pour la troisième fois de cette session.** Une boucle `for e in "url nom" …` suivie de `set -- $e` : en `zsh`, la variable n'est pas découpée en mots, et les six requêtes de la démonstration guidée ont produit `curl: (3) URL rejected: Malformed input to a URL function` | **Le piège §7.5, et je l'avais déjà commis deux fois dans les mêmes heures.** Il n'a rien cassé — l'échec était bruyant et immédiat — mais il a coûté un cycle, et surtout il confirme que **la vigilance ne suffit pas** | Refait en **Python**, où le piège n'existe pas. C'est la parade structurelle de `T7-3` : quand une classe d'erreur résiste à l'attention, on change d'outil au lieu de promettre d'être plus attentif |

### 5.1 Ce que ce défaut unique enseigne, et pourquoi il mérite une ligne

**Ce piège est documenté depuis `T1`, il porte un numéro de section, et je l'ai commis trois fois en
une session.** `T6` et `T7` l'avaient déjà rejoué après l'avoir cité. La conclusion n'est pas qu'il
faut mieux lire la documentation : c'est que **tout contrôle un peu structuré doit être écrit en
Python dans ce dépôt**, et que le shell doit rester réservé aux commandes d'une ligne.

Les cinq scripts de contrôle livrés par le projet suivent déjà cette règle. Ce sont mes commandes
**ad hoc** d'exploration qui y échappent — et c'est précisément là que le piège frappe.

---

## 6. Ce que `T11` ne fait pas, et ne doit pas faire

1. **Elle ne pose pas le tag.** `DEC-428` impose la validation de Jonathan d'abord, puis la fusion
   dans `main`, puis le tag **sur `main`**. Dans cet ordre.
2. **Elle ne fusionne pas dans `main`.** `main` est protégée avec `enforce_admins` : la fusion passe
   par une pull request, et c'est l'action de Jonathan.
3. **Elle ne referme pas l'epic `#1`.** Elle se referme à la validation.
4. **Elle ne relance pas le projet Docker tiers.** C'est l'action de Jonathan, à la fin du lot.
5. **Elle ne modifie aucun document de cadrage.** Les cinq restent immuables, empreintes vérifiées.
6. **Elle n'ajoute ni décision, ni écart, ni risque, ni question.** Il n'y avait rien à trancher :
   les sept critères étaient déjà acquis à l'entrée, et aucun contrôle n'a produit de constat neuf.

---

## 7. État à la sortie de `T11`

| | |
|---|---|
| Sous-étape | **`T11` terminée.** La checklist est remise à Jonathan |
| Décisions | **aucune ajoutée.** Prochaine libre : `DEC-494` |
| Écarts · risques · questions | **aucun ajouté.** `ECART-025` · `ROAD-RSK-035` · `QO-116` |
| Dépendances | aucune ajoutée. `DEP-018` |
| Tests | **260** — inchangé |
| Contrôles rejoués | **33, tous à 0** |
| Tag `v0.1.0` | **non posé**, en attente de validation |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, `T6`, `T8`, machine réellement propre en `T9` |
| ☑ | Les images multiarchitectures sont construites | `T7`, natives sur les deux depuis `T8`, **revérifié en `T11`** |
| ☑ | Aucun secret réel n'est présent | Gitleaks, 47 commits, 0 fuite. **`gh secret list` vide, mesuré** |
| ☑ | Une migration Alembic s'exécute | `T3`, base créée de zéro en `T9` |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4`, en-tête partagé depuis `T10` |
| ☑ | La CI bloque lint, test et secret | `T6`, prouvé trois fois |
| ☐ | **Jonathan valide le socle** | **la checklist lui est remise** |

**Les six critères techniques sont acquis, les huit stories sont livrées, et les 33 contrôles sont à
zéro.** Il ne reste que la décision.

### Ce qui attend la validation

1. Fusionner `develop` dans `main` — une **seconde** fois, pour y porter les documents de `T11`.
2. Poser le tag annoté **`v0.1.0`** sur `main`. Il déclenchera `images.yml` avec la **version
   exacte** : première publication d'une version non `develop`.
3. Refermer l'epic `#1`.
4. Relancer `observatoire-ecom-studio` — action de Jonathan.
5. **Ouvrir le LOT 2**, ce qui est une décision à tracer. `ROAD-003` et `ARB-BACK-003` l'exigent
   explicitement : aucun lot dépendant ne commence avant validation du précédent.
