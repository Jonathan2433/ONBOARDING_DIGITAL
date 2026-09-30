# Compte rendu — `T15` du LOT 7 : recette, §30 et checklist `G7`

**Sous-étape :** `T15` — Recette complète, contrôles du §30, checklist de porte `G7`  
**Décision :** `DEC-615`  
**Date :** 29 septembre 2026  
**Branche :** `feature/lot7-t15-recette-g7`, depuis `develop` à jour (`3db3cab`, fusion de `T14`, PR #199)

---

# État du lot

LOT 7 est ouvert depuis le 25/09/2026 (`DEC-598`) et comprend quinze sous-étapes. `T15` est la
dernière : les quinze sont techniquement réalisées. La porte `G7` n'est **pas** déclarée franchie
ici : le corpus exige encore les validations humaines de Tess, Léa, Diane et Jonathan.

# Sous-étape en cours

`T15` clôture techniquement le lot : recette sur les images publiées, relecture exécutable des 25
contrôles du §30, non-régression comparée à `origin/develop`, et préparation de la checklist `G7`.

# Travail réalisé

- Recette réinitialisée uniquement sur le volume PostgreSQL de recette, démarrée sur les images
  publiées de `3db3cab`, migrée jusqu'à `0021`.
- Parcours réel complet à travers Caddy/HTTPS : fiche lue, complétée et publiée ; modèle
  `intercontract` créé/versionné/publié par un ESM ; deux tâches affectées depuis `arrival_date` ;
  progression `0/2`, `1/2`, `2/2` et archivage automatique observés.
- Classement §30 corrigé : `§30.13`, `§30.14` et `§30.15` passent de reportés à acquis, chacun lié
  à des tests existants.
- Checklist [`checklist-validation-G7.md`](checklist-validation-G7.md) créée ; elle sépare les
  preuves techniques des validations humaines encore à recueillir.
- Issues `#176`, `#177` et `#180` refermées manuellement avec leurs preuves ; l'épic `#175` reste
  ouvert jusqu'à la décision de porte.

# Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make recette-check` | 57 contrôles, 0 échec ; 7/7 séparations |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé conformes |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec |
| Témoin HTTPS temporaire de parcours complet | 14 contrôles, 0 échec ; décor supprimé |
| `make recette-modele-check` | 25/25 classés ; 16 acquis, 2 partiels, 7 reportés |
| 9 tests des reclassements §30.13–15 | 9 passés |
| `pytest` racine, worktree `origin/develop` | 75 échecs identiques, 1 339 succès de chaque côté |
| `make check` final | sortie `0` ; 386 passés, 1 028 ignorés faute de PostgreSQL de développement actif, 706 Vitest passés |

# Résultats

La recette exerce réellement l'artefact publié, non le code local. Le chemin `arrival_date →
tâches → complétions → archivage` est positif et discriminant : après une première tâche, l'instance
reste `active`; après la dernière obligatoire, elle devient `archived` et porte `completed_at`.

Les 75 échecs `pytest` sont préexistants et environnementaux : les 75 identifiants sont identiques
à `origin/develop`, sur la même base de démonstration. Le premier essai de comparaison est écarté :
le worktree ne contenait pas le `.env` ignoré et ne mesurait donc pas la pile ; il a été relancé avec
le même fichier de configuration local avant toute conclusion.

Au terme de la sous-étape, les environnements `dev` et `recette` sont arrêtés et le volume de
développement est intact. Le `make check` final est vert, mais ses tests PostgreSQL sont alors
ignorés : il ne remplace ni la comparaison worktree faite avec la pile active, ni le parcours réel
de recette ci-dessus.

# Décisions ajoutées ou modifiées

- `DEC-615` — recette `T15`, reclassement du §30 et préparation de `G7`.
- `DEC-616` reste réservé à la décision de franchissement de porte, si Jonathan recueille les
  validations humaines exigées.

# Risques et écarts

- **`T15-1`, corrigé avant validation :** le premier nettoyeur du témoin temporaire cherchait un
  modèle dont le nom commençait par le marqueur, alors que le marqueur était au milieu. La clé
  étrangère a refusé la suppression de la tâche de référence ; aucun décor n'a été laissé après le
  nettoyage borné par `entity_id` et le rejeu positif.
- Le démarrage de recette a rencontré le conflit de port tiers prévu ; seul son conteneur web a été
  arrêté temporairement. Caddy a été recréé après vérification de ses publications réelles.
- `ECART-012` et `ECART-064` restent ouverts, hors correctif de `T15`.

# Questions ouvertes

`QO-121` reste ouverte et non bloquante. Le canal de recueil des validations de Tess et Diane n'est
nommé dans aucun document : la checklist le signale à Jonathan sans inventer un interlocuteur ni une
procédure.

# Validation demandée à Jonathan

`T15` est techniquement prête à fusionner. Peux-tu valider la pull request, puis indiquer comment
tu souhaites recueillir les accords de Tess, Léa et Diane pour que la décision `G7` soit traçable ?

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T15 après validation
gh pr close <n> --delete-branch            # retour arrière avant fusion
```
