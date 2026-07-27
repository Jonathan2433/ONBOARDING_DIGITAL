# Contrats de données

**Produit en :** LOT 0, sous-étape S6 — story `MVP-L00-US004`

Ce dossier définit les contrats d'entrée et de qualité des données collaborateurs. Il ne
contient **aucun code** : l'analyseur d'import et les migrations appartiennent aux LOTS 9 et 2.

---

## 1. Documents

| Document | Objet |
|---|---|
| [schema-csv-collaborateurs.md](schema-csv-collaborateurs.md) | Les 19 champs logiques, formats, obligations, cibles dans le modèle de données |
| [codes-erreurs-import.md](codes-erreurs-import.md) | 68 codes stables, niveaux, messages utilisateur et résolutions |
| [listes-controlees.md](listes-controlees.md) | Valeurs admises champ par champ |
| [criteres-qualite-import.md](criteres-qualite-import.md) | Les 8 critères de qualité, la séquence de validation en 10 étapes, la réconciliation du rapport |
| [exemples/](exemples/README.md) | Jeu de 17 lignes **intégralement fictives**, vérifié par script |

---

## 2. Version du schéma

| Version | Date | Statut |
|---|---|---|
| `1.0-initiale` | 27 juillet 2026 | En vigueur |

Ce schéma est **initial**, pas définitif. Le schéma définitif relève de `QO-096`, bloquante
avant données réelles.

Deux points restent volontairement ouverts, plutôt que comblés par une hypothèse :

| Point ouvert | Suivi |
|---|---|
| Nomenclature et langue des en-têtes du fichier réel | `QO-110`, traité par le profil de correspondance versionné de `DEC-434` |
| Catalogue des métiers de l'entité | Aucun document validé ne l'énumère. Établi avec l'ESM, rattaché à `QO-096` |

---

## 3. Décisions applicables

| ID | Décision |
|---|---|
| `DEC-432` | Séparateur `;`, encodage UTF-8, virgule tolérée si non ambiguë, BOM retiré à la lecture |
| `DEC-433` | Champ `autorisation_photo` à trois valeurs, défaut `inconnu`, aucune photo publiée sans autorisation active |
| `DEC-434` | Le schéma définit des champs logiques `F01` à `F19` ; les en-têtes réelles sont associées par un profil de correspondance versionné, tracé avec le lot d'import |
| `DEC-435` | Imputation des anomalies portant sur plusieurs lignes : première occurrence retenue pour un doublon d'identifiant, toutes les lignes rejetées pour un conflit d'attribution métier |

---

## 4. Ce que ce dossier n'autorise pas

- inventer une valeur de liste contrôlée qu'aucun document validé n'établit ;
- déclarer `QO-096` close en livrant le schéma initial ;
- placer une donnée réelle dans le jeu d'exemple, qui est versionné ;
- versionner le CSV réel, sous quelque forme que ce soit ;
- créer automatiquement un client, un alias, un métier ou un cercle lors d'un import.
