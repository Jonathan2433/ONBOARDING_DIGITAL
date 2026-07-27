# Intégrité et conformité des documents de cadrage

**Objet :** preuve vérifiable que les cinq documents validés sont entrés dans le dépôt sans
altération, et que les annexes du cahier des charges sont conformes aux documents
spécialisés.

**Produit en :** LOT 0, sous-étape S2 — story `MVP-L00-US002`
**Date des contrôles :** 27 juillet 2026
**Exécuté par :** agent chef de projet technique, contrôles en lecture seule

---

## 1. Pourquoi ce document existe

La story `MVP-L00-US002` exige que chaque document possède une version, un statut, une date
et des références croisées, et qu'**aucune décision ne soit perdue**. Le critère de sortie
n°2 du LOT 0 exige que chaque décision possède un identifiant stable.

Ces exigences imposent deux garanties :

1. les documents versionnés sont **identiques** aux documents validés le 25 juillet 2026 ;
2. la règle de préséance du cahier des charges ne masque **aucune** divergence entre le
   document consolidé et ses annexes.

Ce document apporte les deux preuves. Il est réexécutable : chaque commande est fournie.

---

## 2. Preuve d'intégrité par empreinte SHA-256

Les empreintes ont été relevées **avant** toute action, alors que les documents se
trouvaient encore dans le dossier `DOCS/` d'origine, puis **après** renommage du dossier,
déplacement dans l'arborescence cible et mise sous suivi Git.

| Document | Chemin final | SHA-256 | Avant = Après |
|---|---|---|---|
| Cahier des charges | `docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` | `2b111351a688f4abb82bc7244778b22ed96e595ac40cbd7e610d8bf979d14ee5` | Oui |
| Matrice des rôles et permissions | `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` | `53d0ae26b09ffb9b0e8352dcba263fae94acc47ccdd3a670e8ffa5e2b522fb5b` | Oui |
| Roadmap MVP, V1 et V2 | `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` | `70a5d833d42f7b050a5815e71c56f20bb692ef31ff2f0834db1546b4f4eb6a2b` | Oui |
| Backlog initial priorisé | `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` | `400dae776fe98090da5347c1bac524c68195c12f295c2a87cf525d66c46ba265` | Oui |
| Modèle de données | `docs/architecture/MODELE_DONNEES_EXALT.md` | `2c60227d2cd8bf9bdf8afcb55d93c00556bfe592248368219321a989316641ee` | Oui |

Le prototype historique, non versionné, porte l'empreinte
`232f0700b9fdc3467ad8d8bd4e5c2260b6cacad09dd140a991669e662aa9ba2d`.

Commande de vérification :

```bash
shasum -a 256 docs/product/*.md docs/architecture/*.md docs/prototype/V1.html
```

**Conséquence de la décision `DEC-423` :** la validation du cahier des charges par Jonathan
n'a pas modifié le fichier. Valider n'est pas une évolution de contenu, la procédure du
cahier des charges section 35 n'exige donc aucun changement de version. Le statut validé
est porté par le registre des décisions et par l'index `docs/README.md`. Cela préserve la
capacité de prouver par empreinte qu'aucun document validé n'a été altéré.

---

## 3. Preuve de conformité des annexes

Le cahier des charges intègre les quatre autres documents en annexes A à D. Sa section 35
en fait des documents contractuels, et la règle de préséance le place au-dessus d'eux. Une
divergence entre une annexe et son document spécialisé créerait deux vérités concurrentes.

Bornes des annexes dans le cahier des charges :

| Annexe | Titre | Lignes |
|---|---|---|
| A | Matrice détaillée des rôles et permissions | 1968 – 2757 |
| B | Modèle de données complet et diagrammes Mermaid | 2758 – 4567 |
| C | Roadmap MVP, V1 et V2 | 4568 – 6143 |
| D | Backlog initial priorisé | 6144 – 6857 |

Méthode : comparaison ligne à ligne après normalisation du niveau de titre — une annexe est
décalée d'un niveau `#` par rapport au document autonome — et suppression des lignes vides.

```bash
C=docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md
norm() { sed 's/^#\{1,\} /# /' "$1" | sed '/^[[:space:]]*$/d'; }
diff <(norm docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md) \
     <(awk 'NR>=1970&&NR<=2756' "$C" | sed 's/^#\{1,\} /# /' | sed '/^[[:space:]]*$/d')
```

### Résultat

| Annexe | Document spécialisé | Lignes de contenu divergentes | Nature de la divergence |
|---|---|---:|---|
| A | Matrice des rôles et permissions v1.1 | 1 | Séparateur `---` de fin d'annexe |
| B | Modèle de données v1.0 | 1 | Séparateur `---` de fin d'annexe |
| C | Roadmap v1.0 | 1 | Séparateur `---` de fin d'annexe |
| D | Backlog v1.0 | 0 | Aucune |

**Conclusion : aucune divergence de contenu.** Les seules différences sont trois traits
horizontaux de mise en forme séparant les annexes. Les caractères ont été rendus visibles
pour l'établir :

```bash
diff <(norm docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md) \
     <(awk 'NR>=1970&&NR<=2756' "$C" | sed 's/^#\{1,\} /# /' | sed '/^[[:space:]]*$/d') \
  | grep '^[<>]' | cat -vet
# > ---$
```

La règle de préséance ne masque donc aucune contradiction à la date de ce contrôle. Ce
contrôle devra être rejoué à chaque évolution de version d'un document.

---

## 4. Contrôles de cohérence interne du backlog

Vérification que les totaux annoncés correspondent au contenu réel, afin de garantir
qu'aucune story n'a été perdue.

```bash
grep -E '^\| *[0-9]+ \|.*\| G[0-9]+ \|' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md \
  | awk -F'|' '{n++; s+=$5; p0+=$6; p1+=$7} END {printf "lots=%d stories=%d P0=%d P1=%d\n", n, s, p0, p1}'
```

| Grandeur | Recomptée | Annoncée dans le document | Verdict |
|---|---:|---|---|
| Lots MVP | 15 | 15, numérotés 0 à 14 (`ARB-ROAD-001`) | Conforme |
| User stories MVP | 112 | 112 | Conforme |
| Stories `P0` | 94 | 94 | Conforme |
| Stories `P1` | 18 | non annoncé globalement | Cohérent : 94 + 18 = 112 |

Stories du LOT 0 : 7 déclarées, identifiants `MVP-L00-US001` à `MVP-L00-US007`, sans trou
ni doublon.

---

## 5. Inventaire des séquences de décisions reprises

Décisions et arbitrages effectivement présents dans le corpus versionné. Cet inventaire
alimente le registre des décisions créé en sous-étape S4.

| Séquence | Source | Nombre |
|---|---|---:|
| `RIGHTS-001` à `RIGHTS-025` | Matrice, section 26 | 25 |
| `DATA-001` à `DATA-018` | Modèle de données, section 32 | 18 |
| `ROAD-001` à `ROAD-012` | Roadmap, section 17 | 12 |
| `BACKLOG-001` à `BACKLOG-010` | Backlog, section 14 | 10 |
| `ARB-DROIT-001` à `-005` | Matrice, section 25 | 5 |
| `ARB-DATA-001` à `-005` | Modèle de données, section 31 | 5 |
| `ARB-ROAD-001` à `-005` | Roadmap, section 16 | 5 |
| `ARB-BACK-001` à `-005` | Backlog, section 13 | 5 |
| **Total** | | **85** |

| Autre séquence | Source | Étendue |
|---|---|---|
| `QO-072` à `QO-105` | Cahier des charges, section 32 | 34 questions, dont 17 bloquantes |
| `ROAD-RSK-001` à `ROAD-RSK-012` | Roadmap, section 14 | 12 risques identifiés |
| Risques du cahier, section 33 | Cahier des charges | 12 risques **sans identifiant** |

**Écart `ECART-004` :** les cinq documents référencent des décisions `DEC-001` à `DEC-417`
issues des ateliers de cadrage, mais la table correspondante n'est présente dans aucun
document du corpus. Tranché par la décision `DEC-422` : les 85 décisions et arbitrages
consolidés ci-dessus font foi, la plage `DEC-001` à `DEC-417` est réservée pour un import
ultérieur sans conflit d'identifiant, et les nouvelles décisions démarrent à `DEC-418`.

---

## 6. Limites connues de ces contrôles

- Le caractère privé du dépôt distant n'est pas vérifiable depuis cette machine : `gh`
  n'est pas installé et aucun connecteur GitHub n'est disponible. Un accès anonyme à l'URL
  du dépôt retourne HTTP 404, comportement attendu d'un dépôt privé, mais également d'un
  dépôt inexistant. Jonathan a confirmé le 27 juillet 2026 que le dépôt est privé ; cette
  confirmation constitue la preuve retenue.
- Les contrôles portent sur la conformité et l'intégrité, non sur la justesse métier du
  contenu, qui relève des validations de Léa, Tess et Diane selon leurs périmètres.
