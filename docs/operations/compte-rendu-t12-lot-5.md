# Compte rendu — `T12` du LOT 5 : la recette et la checklist `G5`

**Sous-étape :** la **dernière** du lot — recette, reclassements du §30, checklist de porte
**Date :** 12 septembre 2026
**Décision attendue :** `DEC-574`, prise par Jonathan à la porte

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026, **onze** sous-étapes |
| Faites | **les onze** — `T1` à `T5` et `T7` à `T12` |
| Ce que `T12` produit | [`checklist-validation-G5.md`](checklist-validation-G5.md) · la recette exécutée · la vérification du §30 |
| Issues | **les cinq restent ouvertes** — c'est Jonathan qui les referme à la porte |

---

# 2. Ce que la sous-étape a fait

## 2.1 La recette a tourné sur une base REMISE À ZÉRO, et c'est le point

La base de développement portait le jeu de démonstration — 26 entités, 5 154 personnes — et
**soixante-douze tests d'intégration y comptent des lignes en absolu**. C'est le défaut `T10-7`, et
il rendait impossible toute mesure honnête de la suite complète.

La base a donc été **détruite et reconstruite** avant la recette, par le chemin documenté :

```bash
make down && docker volume rm onboarding-dev_db-data && make up && make migrate
```

**Pas `make destroy`**, qui emporterait `caddy-data` — donc l'autorité approuvée dans le trousseau de
Jonathan, et une réapprobation à sa charge.

```text
make check   code=0   915 pytest · 440 Vitest · « Tous les controles sont passes »
```

**Puis les trente-deux contrôles de stack, tous en code 0** — les onze d'authentification, les dix de
schéma, et les onze de métier et d'écran. Le détail est au §5 de la checklist.

> **`make code-refresh` A ÉTÉ LANCÉ AVANT LES CONTRÔLES D'ÉCRAN**, et c'est la leçon `T11-1` : trois
> contrôles étaient passés sur un frontend **périmé**, parce que le repli SPA rend `text/html` avec
> le point de montage pour **n'importe quel** chemin. `make ecrans-check` le refuse désormais, sur
> les **32** modules.

## 2.2 Les reclassements du §30 : il n'y en a **aucun**, et c'est mesuré

Le libellé de `T12` annonce des « reclassements du §30 ». La mesure dit qu'il n'y en a pas à faire :

| Statut | Nombre |
|---|---:|
| acquis | **13** |
| partiel — §30.4 | 1 |
| inapplicable — §30.8 | 1 |
| **reportés** | **10** |

**Les dix reportés vont aux LOTS 7, 9, 10, 11 et 12.** Aucun ne portait sur le périmètre du LOT 5 :

```text
§30.13 · §30.14 · §30.15   LOT 7  — onboarding
§30.17 · §30.18            LOT 9  — imports CSV
§30.19                     LOT 10 — jobs et idempotence
§30.20 · §30.21 · §30.23   LOT 12 — audit, purge, anonymisation
§30.24                     LOT 11 — exports
```

**Deux acquis portent déjà la trace du LOT 5**, et ils ont été posés par les sous-étapes qui les ont
produits, non par `T12` : le §30.12 cite `T5` et son contrôle sur les **octets** ; le §30.4, partiel,
nomme **`T8`** comme couvrant son second chemin — une restauration remet une personne en `active`
**sans DSM**, et `restaurer_un_profil` le **nomme**.

> **Un libellé qui annonce un travail ne prouve pas qu'il y en ait.** Inventer un reclassement pour
> honorer le mot aurait été pire que de constater qu'il n'y en a pas — c'est le §6.5 appliqué à une
> fiche de lot, et la cinquième fois de ce projet qu'un document annonce plus qu'il n'y a (§7.29).

## 2.3 Un nombre de la passation était faux

`CLAUDE.md` annonçait « **11 des 25** contrôles du §30 reportés ». La mesure en donne **10** —
13 acquis + 1 partiel + 1 inapplicable + 10 reportés = 25.

**Classe `ECART-021`, pour la énième fois** : un nombre qui n'est pas dérivé de sa source vieillit en
silence. Corrigé, et la commande qui le produit est dans la checklist.

---

# 3. Contrôles exécutés

Tous sur une base **remise à zéro**, puis le jeu de démonstration réensemencé pour la recette de
Jonathan.

```text
make check                 code=0   915 pytest (602 d'integration) · 440 Vitest
make icloud-verify         code=0
make env-check             code=0
make docs-check            code=0
make audit                 code=0

make code-refresh          code=0   ← AVANT les controles d'ecran, lecon `T11-1`
make code-check · residu-check · api-check · web-check · stack-check · ports      code=0
make profil-check          45 controles, 0 echec
make trombinoscope-check   38 controles, 0 echec
make entites-check         13 controles, 0 echec
make cadre-check           25 controles, 0 echec   · cadre-temoin      code=0
make ecrans-check           8 controles, 32 modules servis
make permissions-check     code=0

magic-link-check 15 · admin-check 10 · sessions-check 13 · sessions-temoin
csrf-check 10 · debit-check 12 · revocation-check 6 · service-check 11
evenements-check 6                                                      tous code=0

privileges-check · secrets-check · isolation-check · isolation-temoin
historisation-check · migrations-check · recette-modele-check · alembic-check   tous code=0
```

**Le parcours métier complet, exercé à travers Caddy avec une vraie session :**

```text
connexion         200 + cookie de session
permissions       ["SUPER"]
BORDEA00          76 profils, 4 pages de 25
fiche             200      historique  200      page du profil  200
jetons de cercle  bleu 42 · bleu-fonce 17 · rose 9 · aucun 8
```

---

# 4. Défauts trouvés — **aucun**

**Et je le dis en sachant ce que cela vaut.** `T11` a failli conclure de même, et deux défauts sont
tombés dès que la **pile réelle** a été exercée — §7.43.

Ici, la recette **est** l'exercice de la pile : `make check` complet sur une base neuve, trente-deux
contrôles de stack, et le parcours métier de bout en bout avec une vraie session. Ce qui reste non
éprouvé est nommé au §7 de la checklist, et la première ligne en est la plus importante : **je n'ai
pas vu le rendu visuel**, et c'est l'objet de la démonstration guidée.

---

---

# 6. Après la porte : la fusion vers `main` et le tag `v0.5.0`

**Anticipée le 12/09/2026, à la demande de Jonathan — et RÉPÉTÉE EN LOCAL, pas seulement décrite.**

## 6.1 Pourquoi une branche de livraison, et non `develop → main`

**`main` n'est PAS un ancêtre de `develop`, et ce n'est pas une anomalie** : c'est la forme que
prend cette procédure depuis `G1`. Mesure du 12/09/2026 :

```text
main    = e0629fe    develop = 978c824
main ancetre de develop ?  NON        develop ancetre de main ?  NON
base commune : fdfa64a1   main..develop : 14 commits   develop..main : 8 commits
```

**Les huit commits que `main` a en plus sont TOUS des commits de fusion** — un par porte, `G1`,
`G3`, `G4` — que `develop` n'a jamais reçus.

**Conséquence mesurée, et elle est décisive** : `main` porte `strict: true`, donc GitHub exige que la
branche de tête contienne la tête de la base. `develop` est **behind**, et une pull request
`develop → main` est **mesurément infusionnable**. C'est ce que `G4` a constaté sur sa `#125`, et la
parade est la même depuis `G1` : **une branche partie de `main`, dans laquelle `develop` est
fusionné**, puis proposée à `main`.

## 6.2 La répétition, faite le 12/09/2026

Une branche jetable créée depuis `origin/main`, `develop`+`T12` fusionné dedans, **rien poussé** :

```text
git merge          code=0
arbre de l'essai   b174ca8151b18c947ed2b926e4008dd4bd5b0f45
arbre de la source b174ca8151b18c947ed2b926e4008dd4bd5b0f45   ← IDENTIQUES
la source est un ANCETRE : OUI        parents du commit : 2 (merge commit)
```

> **LE VERDICT DE `git merge` NE PROUVE RIEN, ET C'EST §7.24.** À `G3`, un `merge -X theirs` avait
> rendu **0 sans conflit** tout en gardant, du côté abandonné, un fragment non conflictuel — 41
> lignes dupliquées et une réserve `arm64` réapparaissant *après* le texte qui la levait. **Ce qui
> discrimine est l'ARBRE**, et c'est lui qui a été comparé ci-dessus.

## 6.3 La procédure, dans l'ordre

**Rien de ceci ne se fait avant que la porte soit franchie et que `#142` soit fusionnée.**

```bash
git fetch origin && git switch -c release/g5-rattraper-develop-dans-main origin/main
git merge --no-ff origin/develop
```

Puis **vérifier l'arbre AVANT de pousser** — si ces trois lignes ne disent pas ce qu'elles doivent,
ne pousse pas :

```bash
git rev-parse HEAD^{tree} origin/develop^{tree}      # doivent etre IDENTIQUES
git merge-base --is-ancestor origin/develop HEAD     # doit sortir en 0
git rev-parse HEAD^@ | wc -l                         # 2 = merge commit
```

```bash
git push -u origin release/g5-rattraper-develop-dans-main
~/.local/bin/gh pr create --base main --title "merge: rattraper le contenu de develop dans main apres la porte G5"
```

**La fusion se fait en MERGE COMMIT, jamais en squash** — c'est ce qui fait de `develop` un ancêtre
de `main`, et le squash de `G2` avait coupé l'histoire (`ECART-026`) :

```bash
~/.local/bin/gh pr merge <n> --merge --delete-branch
```

**Puis les trois mêmes contrôles sur `origin/main`**, et seulement ensuite le tag :

```bash
git fetch origin && git rev-parse origin/main^{tree} origin/develop^{tree}
git merge-base --is-ancestor origin/develop origin/main && echo "ancetre : ok"
git rev-parse origin/main^@ | wc -l
```

```bash
git switch main && git pull --ff-only
git tag -a v0.5.0 -m "LOT 5 — collaborateurs, profils et organisation, porte G5 franchie le <date> (DEC-574)"
git push origin v0.5.0
```

**Le tag est ANNOTÉ, sur `main`, et il porte la décision** — c'est la forme des quatre précédents,
vérifiable par `git tag -n9 v0.4.0`.

## 6.4 Deux choses à ne pas oublier

| | |
|---|---|
| **les cinq issues** | `#118`, `#119`, `#121`, `#122`, `#123` — refermées **à la main** avec leurs preuves : `Closes #N` ne marche pas depuis `develop` (§7.19) |
| **une branche distante résiduelle** | `release/g4-rattraper-develop-dans-main` existe encore. La supprimer évite de la confondre avec celle de `G5` : `git push origin --delete release/g4-rattraper-develop-dans-main` |

# 7. Ce que `T12` laisse

| Point | Où il va |
|---|---|
| **la décision `DEC-574`** | Jonathan, à la porte `G5` |
| **les cinq issues ouvertes** | refermées par Jonathan à la porte, avec leurs preuves |
| **le tag `v0.5.0`** | après la porte, sur `main`. **La procédure est au §6, et elle a été RÉPÉTÉE en local** : l'arbre obtenu est identique à celui de `develop` |
| **`ECART-012`** | Léa. Échéance **dépassée**, et c'est à l'écran |
| **`ECART-061`** | LOT 13 — le mot de passe provisoire n'est jamais forcé de changer |
| **`US006` sans écran** | annoncé à `G5`, à reprendre quand un lot lui donnera un écran |
