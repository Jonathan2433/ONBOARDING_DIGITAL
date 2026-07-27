---
name: Anomalie
about: Défaut constaté, avec sa gravité et son effet sur la porte en cours
title: "[Anomalie] "
labels: ''
assignees: ''
---

<!--
  Gravites definies par le cahier des charges section 29.3.
  N'inscrire ici AUCUNE donnee personnelle, aucun secret, aucun magic link,
  aucun extrait de CSV reel et aucun corps d'e-mail.
-->

## Gravité

- [ ] **Bloquante** — interrompt la préparation de la porte
- [ ] **Critique** — interrompt la préparation de la porte
- [ ] **Majeure** — doit être corrigée dans le lot si elle touche un parcours central
- [ ] **Mineure** — reportable selon les règles de recette validées

## Nature

- [ ] Sécurité
- [ ] Intégrité ou perte de données
- [ ] Isolation multi-entités
- [ ] Permissions
- [ ] Accessibilité essentielle
- [ ] Fonctionnelle
- [ ] Performance
- [ ] Exploitation

> Une anomalie de sécurité, d'intégrité, d'isolation ou d'accessibilité essentielle devient
> **immédiatement prioritaire** sur toute story du lot en cours (`ARB-BACK-005`).

## Contexte

| Champ | Valeur |
|---|---|
| Environnement | dev / recette / prod-local |
| Version applicative | |
| Identifiant de corrélation | |
| Lot et story concernés | |
| Rôle utilisé | `EMP` / `NEW` / `DSM` / `ESM` / `BOOST` / `OFFICE` / `ADM-E` / `SUPER` |
| Entité principale | |
| Entité consultée | |
| Navigateur ou appareil | |
| Largeur d'écran | |

## Comportement observé

<!-- Ce qui se produit reellement. -->

## Comportement attendu

<!-- Ce que prevoit le document valide, avec sa reference. -->

Référence : <!-- ex : cahier §10.4, matrice §8.3, DATA-013 -->

## Étapes de reproduction

1.
2.
3.

## Effet sur la porte en cours

- [ ] Empêche la validation de la porte
- [ ] N'empêche pas la validation, mais doit être enregistrée
- [ ] Sans effet sur la porte

## Correction envisagée

<!-- Facultatif a la creation. -->
