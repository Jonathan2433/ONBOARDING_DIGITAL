<!--
  Gabarit de pull request — eXalt Onboarding Digital
  Backlog section 11 : lien obligatoire vers la decision ou le document source,
  et preuve de test dans la description.
  Ne pas inscrire de secret, de donnee personnelle ni de magic link ici.
-->

## Rattachement

| Champ | Valeur |
|---|---|
| Lot | `LOT ` |
| Story | `MVP-Lxx-USxxx` |
| Priorité | `P0` / `P1` / `P2` |
| Porte concernée | `Gx` |
| Issue | Closes # |
| Document ou décision source | <!-- ex : matrice §8.2, DATA-007, ARB-DROIT-001 --> |

## Objet

<!-- Ce que change cette PR et pourquoi. Deux a cinq lignes. -->

## Critères d'acceptation

<!-- Recopier les criteres de la story et cocher ceux qui passent. -->

- [ ]
- [ ]

## Preuves de test

<!-- Commandes executees et resultats reels. Ne pas ecrire "teste manuellement" seul. -->

```text

```

| Type de test | Présent | Commentaire |
|---|---|---|
| Unitaires | [ ] | |
| Intégration PostgreSQL réel | [ ] | |
| API | [ ] | |
| Interface (Vitest / Testing Library) | [ ] | |
| Bout en bout (Playwright) | [ ] | |
| Accessibilité (axe) | [ ] | |
| Migration appliquée sur base vide | [ ] | |
| Migration appliquée depuis la version précédente | [ ] | |

## Permissions et isolation

À remplir dès que la PR touche aux droits, aux périmètres ou aux données d'entité.

- [ ] Les cas **autorisés** sont testés
- [ ] Les cas **refusés** sont testés, y compris avec une requête construite manuellement
- [ ] L'isolation multi-entités est testée : aucune fuite entre entités
- [ ] Le contrôle est appliqué **côté API**, pas uniquement dans l'interface
- [ ] Sans objet pour cette PR

## Interface

À remplir dès que la PR touche l'interface.

- [ ] Navigation complète au clavier, focus visible
- [ ] Vérifié à 320, 390, 768, 1280 et 1920 px
- [ ] Aucune information portée uniquement par la couleur
- [ ] `prefers-reduced-motion` pris en charge
- [ ] États vides, chargement et erreurs traités
- [ ] Aucune action déclarée enregistrée sans confirmation de l'API
- [ ] Sans objet pour cette PR

## Exploitation

- [ ] Logs utiles ajoutés, avec identifiant de corrélation, sans donnée sensible
- [ ] Audit ajouté si l'action est sensible, atomique avec l'action métier
- [ ] Documentation d'exploitation ou d'usage mise à jour
- [ ] Sans objet pour cette PR

## Impact sur les registres

- [ ] Aucune entrée nécessaire
- [ ] Décision ajoutée : `DEC-`
- [ ] Écart ajouté ou clos : `ECART-`
- [ ] Question ouverte ajoutée ou close : `QO-`
- [ ] Risque ajouté ou réévalué : `ROAD-RSK-`
- [ ] Dépendance externe mise à jour : `DEP-`
- [ ] Dette technique enregistrée, avec cause, impact, propriétaire et lot de résolution

## Contrôles bloquants

Une porte ne peut pas être validée si l'un de ces points est en échec.

- [ ] Aucun secret ajouté
- [ ] Aucune donnée réelle de collaborateur, aucun CSV réel, aucune photo réelle
- [ ] Aucun média ni fichier binaire volumineux versionné
- [ ] Aucune donnée personnelle dans les tests automatisés
- [ ] Aucun contournement d'authentification introduit
- [ ] Aucune exigence `Must` ni story `P0` dégradée
- [ ] Aucune fonction explicitement exclue du MVP introduite

## Anomalies connues laissées ouvertes

| Gravité | Description | Décision |
|---|---|---|
| | | |
