# Checklist de validation — porte `G10`

**Lot :** LOT 10 — Audit, reporting, supervision fonctionnelle et support
**Préparée le :** 24 octobre 2026, à la sortie de `T16`
**Destinataire :** Jonathan — il coordonne la validation technique
**Décision de franchissement :** en attente

---

**Comment lire ce document.** Les chiffres sont accompagnés de la commande qui les produit. Les
contrôles techniques sont exécutés ; la validation nominative du corpus reste un acte humain — elle
n'est jamais présentée comme accomplie par la CI.

## 1. Les six critères de sortie — fiche LOT 10 §1.2

| # | Critère | État | Preuve |
|---|---|---|---|
| 1 | les événements sensibles sont atomiques avec l'action métier | **Tenu** | CINQ témoins, un par domaine câblé par `T2`-`T6` (authentification, organisation, contenus, événements, onboarding), tous nommés `test_un_echec_APRES_l_ecriture_annule_AUSSI_l_audit_event`, tous portant `ARB-DATA-005/§30.20` dans leur en-tête : un échec forcé après l'écriture de `audit_event`, dans la MÊME transaction que l'action métier, annule les deux écritures ensemble |
| 2 | aucune donnée interdite n'apparaît dans l'audit | **Tenu** | `T8` — `test_aucune_donnee_interdite_et_la_correlation_est_tracee` (`apps/api/tests/test_journal_d_audit.py`) |
| 3 | les rapports respectent les mêmes droits que les écrans source | **Tenu** | `T9` — l'export CSV (`lister_tout_le_journal_d_audit`) RÉUTILISE la même construction SQL que la lecture (`T8`, `_cte_et_source`), jamais une seconde résolution de périmètre ; `test_le_perimetre_de_l_export_est_celui_de_la_lecture` |
| 4 | les durées de conservation sont configurées | **Tenu** | `T1` — `retention_until` posé à un an par défaut ; `T8` — `test_retention_jusqua_est_un_an_apres_l_occurrence` |
| 5 | l'identifiant de corrélation relie interface, API et logs | **Tenu** | `T2`-`T7` — réutilisation de `correlation_courante()` (`packages/observabilite`, LOT 1 `T4`), jamais un second mécanisme ; même test que le critère 2 |
| 6 | Jonathan valide l'audit et le pilotage | **En attente** | Cette checklist, section 6 |

Aucun des six critères n'a exigé de code nouveau à `T16` : les cinq premiers étaient déjà prouvés
par `T1` à `T15`, et `T16` n'a fait que les relire, confronter au §30 du modèle, et classer le
sixième comme restant à ta charge.

## 2. Reclassement du §30 du modèle

`make recette-modele-check` relit directement les 25 contrôles du §30. La fiche signalait quatre
annotations `lot=` fautives sur `§30.19`-`§30.24`, écrites avant que la roadmap ne fixe l'ordre
définitif des lots : vérifiées contre la roadmap réelle plutôt que recopiées, elles se corrigent
ainsi —

| § | Libellé | Correction |
|---|---|---|
| `§30.19` (jobs, idempotence) | reporté | échéance corrigée `LOT 10` → `LOT 11` |
| `§30.20` (`audit_event`, atomicité) | **reclassé ACQUIS** | c'est le critère de sortie 1 de ce lot, cinq témoins existants |
| `§30.21` (purge sans orphelin) | reporté | échéance corrigée `LOT 12` → `LOT 11` (trouvé en vérifiant la classe, pas seulement les quatre exemples cités) |
| `§30.23` (anonymisation, durées) | reporté | échéance corrigée `LOT 12` → `LOT 11` |
| `§30.24` (exports au périmètre de la lecture) | **reclassé ACQUIS** | c'est l'export d'audit de ce lot (`T9`), deux tests existants |

Résultat : **20 acquis, 2 partiel, 3 reportés, 0 inapplicable** — contre 18/2/5/0 depuis `T16` du
LOT 9. Les trois reports restants (`§30.19`, `§30.21`, `§30.23`) appartiennent tous au LOT 11, hors
périmètre de ce lot.

## 3. Contrôles exécutés

| Contrôle | Résultat relevé le 24/10/2026 |
|---|---|
| `make recette-modele-check` | 25 contrôles classés : **20 acquis, 2 partiel, 3 reportés, 0 inapplicable** |
| `make recette-check` (images publiées `b4e3b92`) | 57 contrôles, 0 échec ; 7/7 séparations effectives |
| `make back-office-check ENVIRONNEMENT=recette` | 16 contrôles, 0 échec |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec |
| `make accueil-check ENVIRONNEMENT=recette` | 29 contrôles, 0 échec |
| `make back-office-check` / `onboarding-check` / `accueil-check` / `framework-check` (développement) | 16 / 14 / 29 / 77 contrôles, 0 échec |
| `make isolation-check` / `migrations-check` / `permissions-check` | tous verts |
| `pytest` depuis la racine | 1 992 collectés, inchangé ; 78 échecs environnementaux, **identiques un par un** à `origin/develop` (comparaison de worktree) |
| `make test-frontend` | 889 Vitest (459 `contracts`, 120 `ui`, 310 `web`), inchangé |
| `make check` (qualité) | Ruff, Prettier, ESLint, `mypy` (276 fichiers) : tous verts |
| `make audit` | zéro avis, zéro tolérance |
| `make residu-check` | 78 échecs environnementaux, aucun résidu laissé |

Les 78 échecs viennent du jeu de démonstration de développement (§11 de la passation). La
comparaison porte sur la **liste** des identifiants de test en échec, pas seulement leur nombre :
elle est identique, un par un, entre `origin/develop` et la branche de `T16`.

## 4. La recette réellement exécutée

La recette a été épinglée sur les images publiées de la révision `b4e3b92` (fusion de `T15`,
exécution `40128090340`). Un premier démarrage a rencontré le port `8080` déjà déclaré par le
projet tiers `observatoire-ecom-studio`, même conflit que documenté depuis `T15` du LOT 7 sur la
même machine — son conteneur a été arrêté temporairement puis relancé après la recette.

**L'épinglage de `.env.recette` datait du 13/10/2026, avant l'ouverture du LOT 10** :
`alembic upgrade head` rendait `0026`, pas `0027` — mesuré, pas supposé, avant toute conclusion.
`make images-pin` l'a réépinglé sur `b4e3b92`, puis `make migrate ENVIRONNEMENT=recette` a amené la
tête à `0027`.

`make back-office-check`, `make onboarding-check` et `make accueil-check` ont ensuite été rejoués
sur la recette, à travers Caddy en HTTPS, sur les conteneurs tournant nativement en `aarch64` sur
l'image **publiée** — jamais une reconstruction locale, vérifié par empreinte. Les trois donnent les
mêmes résultats qu'en développement.

## 5. Réserves et écarts ouverts

- `ECART-012` (statut professionnel d'une direction générale) reste à décider par Léa et ne bloque
  pas la porte technique.
- `QO-092` reste ouverte pour son seul volet hors périmètre (un canal de notification externe pour
  les signalements, LOT 11/13) — résolue par la matrice pour l'application elle-même, `T12`.
- `QO-096`, `QO-097`, `QO-099`, `QO-100`, `QO-110` restent ouvertes, héritées du LOT 9 : elles
  bloquent uniquement le chargement de données réelles, jamais ce lot.
- `QO-121` (vocabulaire de `payload_json` par type de bloc) reste ouverte, héritée du LOT 6.
- `QO-125` (filtrage DSM/Booster du rapport d'import) reste ouverte, héritée du LOT 9.
- `QO-126` (sixième ligne du §15.1, « Consulter les événements » du reporting) reste ouverte,
  ouverte par `T10` de ce lot — absente du cahier §10.10 et des critères d'acceptation littéraux
  d'`US003`, non bâtie sur une inférence.
- `ROAD-RSK-033` et `ROAD-RSK-034` restent à réévaluer avant le LOT 13, inchangés par ce lot.

Aucun de ces points n'est bloquant pour la porte technique `G10` — tous sont déjà nommés comme tels
par la fiche LOT 10 §2.1 et par la passation.

## 6. Décision de Jonathan

**Ce que tu valides :** les six critères de sortie du LOT 10, en distinguant les cinq preuves
techniques tenues (§1) de ta propre confirmation requise par le sixième.

**Ce que la porte clôt :** le LOT 10 ; elle n'ouvre aucun autre lot sans instruction explicite.

| | |
|---|---|
| Date | — |
| Décision | ☐ franchie ☐ à reprendre |
| Validation de Jonathan | en attente |
| Réserves | `ECART-012`, `QO-092` (volet canal externe), `QO-096`/`QO-097`/`QO-099`/`QO-100`/`QO-110`/`QO-121`/`QO-125`/`QO-126`, `ROAD-RSK-033`/`ROAD-RSK-034` restent ouvertes, non bloquantes pour `G10` — à reprendre aux lots suivants au besoin |
