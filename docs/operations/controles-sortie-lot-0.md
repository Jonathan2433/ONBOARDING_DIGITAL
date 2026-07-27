# Contrôles de sortie du LOT 0 — porte `G0`

**Produit en :** LOT 0, sous-étape S8
**Date d'exécution :** 27 juillet 2026
**Porte :** `G0` — « Fin du référentiel : Jonathan confirme les documents et conventions »
**Statut :** contrôles exécutés — **porte `G0` validée par Jonathan le 27 juillet 2026** (`DEC-438`)

Ce document apporte la preuve, commande par commande et sortie par sortie, que les critères de
sortie du LOT 0 sont satisfaits. Il est réexécutable.

---

## 1. Les cinq critères de sortie de la roadmap

Source : roadmap, LOT 0, section « Critères de sortie ».

| # | Critère | Verdict |
|---:|---|---|
| 1 | Les documents de cadrage sont présents dans le dépôt | **Satisfait** |
| 2 | Chaque décision possède un identifiant stable | **Satisfait** |
| 3 | Les responsabilités produit et techniques sont identifiées | **Satisfait** |
| 4 | Aucun fichier réel de collaborateurs n'est versionné | **Satisfait** |
| 5 | Jonathan valide le référentiel | **Satisfait** — 27 juillet 2026, `DEC-438` |

---

## 2. Critère 1 — Les documents de cadrage sont présents

### 2.1 Intégrité des cinq documents validés

Les empreintes ont été relevées **avant toute action**, alors que les documents se trouvaient
encore dans le dossier `DOCS/` d'origine.

```bash
shasum -a 256 -c <<'EOF'
2b111351a688f4abb82bc7244778b22ed96e595ac40cbd7e610d8bf979d14ee5  docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md
53d0ae26b09ffb9b0e8352dcba263fae94acc47ccdd3a670e8ffa5e2b522fb5b  docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md
70a5d833d42f7b050a5815e71c56f20bb692ef31ff2f0834db1546b4f4eb6a2b  docs/product/ROADMAP_MVP_V1_V2_EXALT.md
400dae776fe98090da5347c1bac524c68195c12f295c2a87cf525d66c46ba265  docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
2c60227d2cd8bf9bdf8afcb55d93c00556bfe592248368219321a989316641ee  docs/architecture/MODELE_DONNEES_EXALT.md
EOF
```

Sortie réelle :

```text
docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md: OK
docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md: OK
docs/product/ROADMAP_MVP_V1_V2_EXALT.md: OK
docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md: OK
docs/architecture/MODELE_DONNEES_EXALT.md: OK
```

**5 sur 5 identiques.** Git certifie par ailleurs les cinq déplacements à 100 % de similarité.

### 2.2 Arborescence exigée par la roadmap

| Dossier | Présent | Fichiers versionnés |
|---|---|---:|
| `docs/product/` | oui | 10 |
| `docs/architecture/` | oui | 9 |
| `docs/decisions/` | oui | 3 |
| `docs/operations/` | oui | 8 |

### 2.3 Conformité des annexes du cahier des charges

Le cahier intègre les quatre autres documents en annexes contractuelles A à D. Une divergence
créerait deux vérités concurrentes.

| Annexe | Document spécialisé | Divergences de contenu |
|---|---|---|
| A | Matrice v1.1 | 1 séparateur `---`, aucune divergence de contenu |
| B | Modèle de données v1.0 | 1 séparateur `---` |
| C | Roadmap v1.0 | 1 séparateur `---` |
| D | Backlog v1.0 | **aucune** |

Méthode et commandes : [integrite-et-conformite-documents.md](integrite-et-conformite-documents.md).

**Verdict du critère 1 : satisfait.**

---

## 3. Critère 2 — Chaque décision possède un identifiant stable

### 3.1 Complétude du registre

```bash
D=docs/decisions/registre-decisions.md
for p in 'RIGHTS-[0-9]{3}' 'DATA-[0-9]{3}' 'ROAD-[0-9]{3}' 'BACKLOG-[0-9]{3}' \
         'ARB-DROIT-[0-9]{3}' 'ARB-DATA-[0-9]{3}' 'ARB-ROAD-[0-9]{3}' 'ARB-BACK-[0-9]{3}' 'DEC-[0-9]{3}'; do
  printf "%-22s %s\n" "$p" "$(grep -cE "^\| \`$p\`" $D)"
done
```

Sortie réelle :

| Séquence | Attendu | Présent | Verdict |
|---|---:|---:|---|
| `RIGHTS-nnn` | 25 | 25 | OK |
| `DATA-nnn` | 18 | 18 | OK |
| `ROAD-nnn` | 12 | 12 | OK |
| `BACKLOG-nnn` | 10 | 10 | OK |
| `ARB-DROIT-nnn` | 5 | 5 | OK |
| `ARB-DATA-nnn` | 5 | 5 | OK |
| `ARB-ROAD-nnn` | 5 | 5 | OK |
| `ARB-BACK-nnn` | 5 | 5 | OK |
| `DEC-418` à `DEC-436` | 19 | 19 | OK |
| **Total** | **104** | **104** | **OK** |

### 3.2 Fidélité au texte source

Les 85 décisions reprises ne doivent pas seulement porter le bon identifiant : leur **texte**
doit être identique à celui des documents validés. Ce contrôle avait initialement été omis, ce
qui avait laissé passer 16 libellés altérés par une apostrophe.

| Ensemble vérifié | Libellés | Altérés |
|---|---:|---:|
| Décisions `RIGHTS`, `DATA`, `ROAD`, `BACKLOG` | 65 | **0** |
| Risques de la roadmap §14 | 12 | **0** |
| Risques du cahier §33 | 12 | **0** |
| **Total** | **89** | **0** |

### 3.3 Unicité et continuité

- **Aucun identifiant n'est défini deux fois**, toutes séquences confondues ;
- séquences continues sans absence : `RIGHTS` 1 à 25, `DATA` 1 à 18, `ROAD` 1 à 12,
  `BACKLOG` 1 à 10, `DEC` 418 à 436 ;
- trous conservés et documentés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`
  (`ECART-011`) ; plage `DEC-001` à `DEC-417` réservée (`DEC-422`).

### 3.4 Registres complémentaires

| Registre | Entrées recomptées |
|---|---:|
| Écarts `ECART` | 15 |
| Questions ouvertes `QO` | 34 |
| Risques `ROAD-RSK` | 28 |
| Dépendances externes `DEP` | 17 |
| Contenus inventoriés `CONT` | 29 |

**Verdict du critère 2 : satisfait.**

---

## 4. Critère 3 — Les responsabilités sont identifiées

Document dédié : [responsabilites-projet.md](responsabilites-projet.md).

| Contrôle | Résultat |
|---|---|
| Les 8 domaines de décision du cahier §5.1 sont repris | 9 lignes de table, en-tête incluse |
| Léa citée | 6 fois |
| Jonathan cité | 20 fois |
| Tess citée | 4 fois |
| Diane citée | 4 fois |
| Validateur de chacune des 15 portes | identifié |
| Validation métier de l'import | reprise de la matrice §14.1 |
| Responsabilités d'exploitation en phase locale | identifiées |

**Verdict du critère 3 : satisfait.**

---

## 5. Critère 4 — Aucun fichier réel de collaborateurs n'est versionné

C'est le critère le plus sensible du lot, et le seul dont l'échec serait irréversible : un
historique Git ne se nettoie pas.

### 5.1 Types de fichiers interdits parmi les fichiers suivis

```bash
git ls-files | grep -Ei '\.(csv|tsv|xlsx|xls|env|pem|key|p12|mp4|mov|webm|html)$'
```

Sortie réelle : **une seule ligne**, `docs/architecture/donnees/exemples/collaborateurs-exemple-fictif.csv`.

C'est l'exception explicitement prévue par `.gitignore`, et le fichier est intégralement
fictif : un seul patronyme `EXEMPLE`, prénoms de l'alphabet radio, domaine externe en `.example`
réservé par la RFC 2606.

### 5.2 Le prototype n'est pas suivi

```bash
git ls-files | grep -c 'V1.html'      # -> 0
test -f docs/prototype/V1.html         # -> present sur disque
```

Le fichier est conservé pour historisation (`DEC-420`) et exclu du suivi, exclusion vérifiée par
`git check-ignore`.

### 5.3 Absence de fuite dans les fichiers, sur tout l'historique

```bash
git log --all --pretty=format: --name-only --diff-filter=A | sort -u
```

**45 fichiers ont existé** dans l'historique des 7 commits. Un seul est d'un type sensible : le
CSV d'exemple fictif. Aucun fichier interdit n'a donc jamais été ajouté puis retiré.

### 5.4 Absence de fuite dans le contenu, sur tout l'historique

Contrôle appliqué aux 7 commits, avec **validation de la méthode par témoins**. Cette
précaution n'est pas superflue : une première version de ce contrôle ne détectait rien du tout,
ce qui produisait un faux « OK ».

```bash
scan() {
  total=0
  for c in $(git rev-list --all); do
    n=$(git grep -cEi "$1" "$c" 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
    total=$((total+n))
  done
  echo "$total"
}
```

| Contrôle | Motif | Résultat |
|---|---|---:|
| **Témoin positif** | `CHANGE_ME_GENERER`, présent dans `.env.example` | 3 → méthode opérante |
| **Témoin négatif** | `MOTIF_IMPOSSIBLE_XYZ123` | 0 → aucun faux positif |
| Mot de passe du prototype | `eXalt2026` | **0** |
| Clé privée | `BEGIN … PRIVATE KEY` | **0** |
| Données en Base64 | `data:image/…;base64` | **0** |
| Stockage navigateur | `localStorage` | 58, **toutes légitimes** |

Les 58 occurrences de `localStorage` sont des **interdictions énoncées dans la documentation** —
« aucune donnée métier durable dans `localStorage` » — et non du code en faisant usage. Elles
proviennent du cahier des charges validé, de la roadmap, du `README`, de `.env.example` et des
documents d'inventaire.

### 5.5 Absence de fuite d'identités depuis le prototype

Contrôle exécuté en sous-étape S7, le plus important de l'inventaire : les **128 patronymes**
présents dans le prototype ont été extraits, puis confrontés à l'intégralité des fichiers
versionnés.

| Résultat | Valeur |
|---|---|
| Patronymes extraits du prototype | 128 |
| Patronymes présents dans le dépôt | **0** |
| Prénoms signalés à vérifier | 6 |

Origine des 6 prénoms signalés :

| Prénom | Origine | Légitime |
|---|---|---|
| Jonathan, Diane, Tess | Décideurs nommés au cahier des charges §5.1, document validé | oui |
| Omar | **1 seule occurrence, dans le cahier des charges validé §8.4.** Aucune dans un fichier produit par le LOT 0 | oui |
| Consultant, Prénom | Faux positifs de l'expression de recherche, mots communs | oui |

**Verdict du critère 4 : satisfait.**

---

## 6. Critères d'empêchement de porte du backlog §12

Une porte ne peut pas être validée si l'un de ces neuf points est en échec.

| Critère | État | Justification |
|---|---|---|
| Une story `P0` du lot n'est pas terminée | **Non** | Les 6 stories `P0` sont réalisées et validées une à une |
| Une permission critique n'est pas testée | **Sans objet** | Le LOT 0 ne produit aucun code ni règle d'autorisation exécutable |
| Une migration ne fonctionne pas sur une base propre | **Sans objet** | Aucune migration au LOT 0 ; elles appartiennent au LOT 2 |
| Un secret ou une donnée réelle a été versionné | **Non** | Section 5, contrôles 5.1 à 5.5 |
| Une anomalie bloquante ou critique reste ouverte | **Non** | Aucune anomalie ouverte. Voir section 7 |
| Un comportement mobile ou clavier essentiel est inutilisable | **Sans objet** | Aucune interface au LOT 0 |
| La démonstration ne correspond pas aux critères de la roadmap | **Non** | La roadmap n'exige pas de démonstration exécutable pour le LOT 0 ; la preuve est documentaire et figure dans ce document |
| La documentation minimale de reprise ou d'exploitation manque | **Non** | 36 documents Markdown versionnés, dont conventions, politique de configuration et registres |
| Jonathan n'a pas donné sa validation explicite | **Non** | Validation donnée le 27 juillet 2026, `DEC-438` |

---

## 7. Anomalies et défauts rencontrés pendant le lot

Aucune anomalie n'est ouverte. Sept défauts ont été détectés par les contrôles **pendant** le
lot, et tous ont été corrigés avant la fin de la sous-étape concernée. Ils sont listés par
honnêteté de compte rendu.

| # | Sous-étape | Défaut | Correction |
|---:|---|---|---|
| 1 | S1 | Contrôle `.gitignore` faux : `git check-ignore -v` sort avec 0 même sur une règle de négation | Contrôle remplacé par une inspection de la règle correspondante, validé par cas témoin |
| 2 | S4 | Décompte des questions ouvertes erroné : 34 annoncées au lieu de 29, confusion entre l'étendue de la plage et le nombre d'entrées | Corrigé, commande de vérification inscrite, `ECART-011` créé |
| 3 | S4 | 16 libellés repris altérés par une apostrophe droite au lieu de l'apostrophe typographique, alors que le registre affirmait « repris sans altération » | Texte source réinjecté par script ; 89 libellés désormais vérifiés au caractère près |
| 4 | S5 | BOM `EF BB BF` en tête de `.env.example`, susceptible de casser le parsing selon l'outil | Retiré, absence vérifiée sur tous les fichiers |
| 5 | S6 | Classification du jeu d'exemple erronée : un doublon et un conflit de Booster entraînaient les lignes correctes | Sémantique tranchée par `DEC-435`, jeu ajusté, classification vérifiée par script |
| 6 | S6 | Total des codes d'erreur erroné : 58 annoncés sur 11 domaines au lieu de 68 sur 12 | Recompté automatiquement, corrigé et propagé |
| 7 | S8 | Contrôle de secrets sur l'historique **inopérant** : `zsh` ne découpe pas une variable en mots, les 7 hachages étaient passés comme un seul argument, et l'erreur était masquée par `2>/dev/null` | Boucle explicite, méthode validée par témoin positif et témoin négatif |

Le septième est le plus instructif : il produisait un faux « OK » sur le contrôle le plus
sensible du lot. Il n'a été découvert que parce qu'un témoin positif a été ajouté.
**Tout contrôle de sécurité de ce projet doit désormais être accompagné d'un témoin.**

---

## 8. Volumétrie du référentiel livré

| Grandeur | Valeur |
|---|---:|
| Commits | 7 |
| Fichiers versionnés | 41 |
| Documents Markdown | 36 |
| Lignes versionnées | 16 938 |
| Décisions au registre | 104 |
| Écarts suivis | 15 |
| Questions ouvertes suivies | 34 |
| Risques suivis | 28 |
| Dépendances externes suivies | 17 |
| Contenus inventoriés | 29 |
| Champs logiques du schéma CSV | 19 |
| Codes d'erreur d'import | 68 |

---

## 9. État de publication

Les 7 commits sont **locaux**. Aucun envoi vers GitHub n'a été effectué : c'est une action
sortante, qui appartient à Jonathan.

```bash
git push -u origin main
```

---

## 10. Ce qui reste ouvert à la sortie du LOT 0

Aucun de ces points n'empêche la validation de `G0`. Ils sont listés pour que la porte soit
franchie en connaissance de cause.

| Élément | Nature | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV initial livré ; le schéma définitif relève de `QO-096` | LOT 9 |
| `ECART-006` | `.env.example` en v0.1, à compléter | LOT 1 |
| `ECART-010` | Traçabilité GitHub non mise en place : étiquettes, milestones, protection de branche | **Prérequis du LOT 1** |
| `ECART-012` | Vocabulaire `intercontrat` appliqué à une direction générale | LOT 2, avant LOT 5 |
| `ECART-013` | Identifiants de tâches non stables dans le prototype | **Structurant pour le LOT 7** |
| `ECART-014` | Terminologie « Représentant de cercle » contre « Booster » | LOT 6 |
| `ECART-015` | Descriptions de cercles et liens internes à produire | LOT 6 |
| `QO-107`, `QO-108` | Faisabilité de la protection de branche et moyen d'accès à l'API GitHub | **Prérequis du LOT 1** |
| `QO-109` | Atténuations iCloud pour les volumes Docker | **À trancher au LOT 1** |
| `ROAD-RSK-027` | 16 Gio de mémoire vive pour trois environnements | **À arbitrer au LOT 1** |
| `CONT-001` à `CONT-029` | Contenus au statut `à relire` par Léa, Tess et Diane | LOT 6 |
