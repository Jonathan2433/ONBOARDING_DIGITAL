# Checklist de validation — porte `G7`

**Lot :** LOT 7 — Fiches d'arrivée et onboarding  
**Préparée le :** 29 septembre 2026, à la sortie de `T15`  
**Destinataire :** Jonathan — il coordonne la validation technique et l'exploitation  
**Décision de franchissement :** `DEC-617`, validée le 30 septembre 2026

---

**Comment lire ce document.** Les chiffres sont accompagnés de la commande qui les produit. Les
contrôles techniques sont exécutés ; les validations nominatives du corpus restent des gestes
humains, et ne sont donc jamais présentées comme accomplies par la CI.

## 1. Les sept critères de sortie — fiche LOT 7 §1.2

| # | Critère | État | Preuve ou geste restant |
|---|---|---|---|
| 1 | Les parcours mission et intercontrat sont validés par Tess, Léa, Diane et Jonathan | **Tenu** | Accord collectif des quatre validatrices et valideurs transmis explicitement par Jonathan le 30/09/2026 |
| 2 | Les règles de périmètre DSM, Booster et ESM sont testées | **Tenu** | Témoins d'intégration de `T4` à `T12` ; `make onboarding-check` prouve sur HTTPS l'asymétrie DSM/ESM |
| 3 | La progression est calculée, non stockée | **Tenu** | `T7` et recette `T15` : `0/2`, puis `1/2`, puis `2/2`, lus après chaque geste |
| 4 | Les événements de tâche sont historisés | **Tenu** | `T7`/`T8`/`T9` : `ASSIGNED`, `COMPLETED`, `CANCELLED`, `REOPENED`, chacun avec son témoin |
| 5 | Le départ archive le parcours et révoque les sessions | **Tenu** | `T11`, tests d'intégration et `make revocation-check` |
| 6 | Un parcours réel complet est exécuté en recette | **Tenu** | `T15`, base de recette réinitialisée ; voir §4 |
| 7 | Jonathan valide l'organisation et l'onboarding | **Tenu** | Validation explicite de Jonathan le 30/09/2026 |

## 2. Contrôles exécutés

| Contrôle | Résultat relevé le 29/09/2026 |
|---|---|
| `make recette-check` | 57 contrôles, 0 échec ; 7/7 séparations effectives |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé répondent, révision `3db3cab` |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec ; application React servie par Caddy en HTTPS |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec ; asymétrie DSM/ESM, cycle de vie et refus DSM à la restauration |
| Parcours de recette `T15` | 14 contrôles, 0 échec ; voir §4 |
| `make recette-modele-check` | 25 contrôles classés : 16 acquis, 2 partiels, 7 reportés, 0 inapplicable |
| Témoins des reclassements §30.13–15 | 9 tests d'intégration, 0 échec |
| `pytest` depuis la racine, comparé à `origin/develop` | 75 échecs environnementaux identiques ; 1 339 succès de chaque côté |

Les 75 échecs viennent du jeu de démonstration de développement. La comparaison se fait sur la
même pile et compare les **listes** d'échecs, pas seulement leur nombre.

## 3. Démonstration guidée à Jonathan

1. Lire la fiche LOT 7 §1.2 et les deux parcours de modèle (`mission`, `intercontract`).
2. Examiner `PageMonOnboarding` : fiche préremplie, complétion, validation/publication, puis
   parcours et tâches.
3. Vérifier le scénario de progression : une première tâche terminée laisse l'instance active ; la
   dernière tâche obligatoire l'archive automatiquement.
4. Examiner `PageAdministration` : catalogue, modèles/version et suivi ; un DSM/Booster voit le
   point d'entrée pour gérer son périmètre, un rôle `OFFICE` ne reçoit pas d'action de gestion.
5. Vérifier qu'un changement de statut conserve les tâches communes terminées et remplace les
   autres selon `T10`.
6. Vérifier qu'après cinq minutes, seule la grille ESM/ADM-E/SUPER réouvre avec un motif.
7. Recueillir et consigner les accords de Tess, Léa, Diane et Jonathan sur les deux modèles ; aucun
   document de cadrage ne donne le canal ou l'identité opérationnelle de Tess et Diane.

## 4. La recette réellement exécutée

La recette a été épinglée sur les images publiées de la révision `3db3cab`, puis son seul volume
PostgreSQL a été supprimé et recréé. Les huit services ont été démarrés et migrés jusqu'à la tête
`0021`. Le développement, son volume et son jeu de démonstration n'ont pas été touchés.

Un premier démarrage a rencontré le port `8080` déjà déclaré par le projet tiers
`observatoire-ecom-studio`. Son seul conteneur web a été arrêté temporairement. Caddy, créé pendant
ce conflit sans ses publications réelles, a ensuite été recréé par `make caddy-recreate
ENVIRONNEMENT=recette` ; les sept ports effectifs ont alors été mesurés par `make recette-check`.

Le parcours métier a ensuite traversé Caddy en HTTPS avec deux identités distinctes : un ESM et un
nouvel arrivant. La fiche initiale a été lue, complétée puis validée/publiée (`200`). L'ESM a créé
deux tâches de référence, un modèle `intercontract`, sa version et ses deux tâches obligatoires,
puis l'a publié (`201`/`200`). L'affectation a rendu deux tâches avec des échéances mesurées à
`J+1` et `J+5` de la vraie `arrival_date`. La première complétion a rendu la progression `1/2` et
l'instance `active`; la seconde a rendu `2/2`, l'instance `archived` et `completed_at` non nul.
Tous les appels ont répondu `200` ou `201`. Le décor marqué a été supprimé à la fin.

## 5. Contrôles du modèle §30

`make recette-modele-check` relit directement les 25 contrôles du §30 du modèle immuable. `T15`
reclasse les trois éléments qui avaient été livrés mais étaient restés inscrits comme reportés :

- §30.13 — unicité de l'instance active (`T7`), index partiel et refus `409` de seconde affectation ;
- §30.14 — conservation des tâches communes (`T10`), par `task_reference_id` stable ;
- §30.15 — réouverture après délai (`T9`), rôle autorisé et motif exigés.

Le résultat est **16 acquis, 2 partiels, 7 reportés, 0 inapplicable**. Les sept reports relèvent
uniquement des LOTS 9 à 12, hors périmètre de ce lot.

## 6. Réserves et écarts ouverts

- `ECART-012` reste à décider par Léa et ne bloque pas la porte technique.
- `ECART-064` reste à instruire avec l'audit au LOT 10.
- `QO-121` reste hors périmètre ; elle ne bloque pas l'onboarding.
- Les accords de Tess, Léa, Diane et Jonathan ont été confirmés collectivement par Jonathan le
  30/09/2026. Cette confirmation humaine reste distincte des preuves produites par la CI.

## 7. Décision de Jonathan

**Ce que tu valides :** les sept critères du LOT 7, en distinguant les six preuves techniques des
accords humains requis par le premier critère.

**Ce que la porte clôt :** le LOT 7 ; elle n'ouvre aucun autre lot sans instruction explicite.

| | |
|---|---|
| Date | 30 septembre 2026 |
| Décision | ☒ franchie ☐ à reprendre — `DEC-617` |
| Accords de Tess, Léa, Diane et Jonathan | Validés collectivement, confirmation transmise par Jonathan |
| Réserves | `ECART-012`, `ECART-064` et `QO-121` restent ouvertes, non bloquantes pour `G7` |
