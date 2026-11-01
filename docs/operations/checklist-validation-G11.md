# Checklist de validation — porte `G11`

**Lot :** LOT 11 — Médias, worker et tâches planifiées, périmètre élargi (organisation et démo)
**Préparée le :** 1er novembre 2026, à la sortie de `T7`
**Destinataire :** Jonathan — il coordonne la validation technique
**Décision de franchissement :** **en attente**

---

**Comment lire ce document.** Les chiffres sont accompagnés de la commande qui les produit. Les
contrôles techniques sont exécutés ; la validation nominative du corpus reste un acte humain — elle
n'est jamais présentée comme accomplie par la CI.

## 1. Les sept critères de sortie — fiche LOT 11 §1.4

| # | Critère | État | Preuve |
|---|---|---|---|
| 1 | seuls les médias `ready` sont servis | **Tenu** | `T2` — garde déjà posée au LOT 5 (`ETAT_AFFICHABLE`), reprise par l'upload et la génération de variantes |
| 2 | Redis peut être vidé sans perte de la source de vérité métier | **Tenu** | `T1` — `async_job`/`outbox_message` persistés dans PostgreSQL ; Redis sert uniquement au transport et à l'exécution (`ARB-DATA-005`) |
| 3 | un job rejoué ne duplique pas son effet | **Tenu** | `T1`/`T2`, §30.19 reclassé ACQUIS par `T7` — deux témoins décisifs (relais e-mail, génération de variante), tous deux simulant un relais interrompu |
| 4 | les tâches planifiées ne s'exécutent pas en parallèle | **Tenu** | `T4` — index unique PARTIEL `scheduled_task_run.task_name WHERE state='running'`, même mécanisme que `async_job`/`outbox_message` |
| 5 | les fichiers rejetés sont supprimés selon la politique | **Tenu** | `T4`, §30.21 reclassé ACQUIS par `T7` — délai de sept jours, même règle pour rejeté/temporaire/orphelin, suppression réelle vérifiée dans MinIO |
| 6 | les workers et files sont supervisés | **Tenu** | `T4` — battement unique poussé vers Uptime Kuma, no-op si l'URL reste vide |
| 7 | Jonathan valide les traitements asynchrones | **Ta confirmation** | cette checklist, section 6 |

Les six premiers critères n'ont exigé aucun code nouveau à `T7` : cinq étaient déjà prouvés par `T1`
à `T4`, et `T7` n'a fait que les relire, confronter au §30 du modèle, et corriger un défaut trouvé en
vérifiant l'état réel des images publiées (section 3).

## 2. `T6` est vide, fusionnée avec `T7`

La fiche (§3) anticipait ce cas et exigeait qu'il soit « annoncé avant d'être exécuté, jamais décidé
a priori ». Mesuré par recherche dans le code (pas par mémoire des comptes rendus) : tous les écrans
de `T2` (photo de profil) et `T3` (organisation) sont reliés à la navigation (rubriques
« trombinoscope » et « administration ») ; `T1` est pur backend sans écran prévu ; `T4` n'a aucun
écran ; `T5` modifie un écran déjà relié. Le seul stub du dépôt (`SectionAVenir.tsx`) appartient à un
périmètre hors LOT 11, posé par le LOT 9. Annoncé à Jonathan, confirmé explicitement le 01/11/2026.
`T6` ne livre donc aucun code et n'ouvre aucune pull request propre.

## 3. Un défaut réel trouvé et corrigé avant la recette

`gh run list --workflow=images.yml` a montré que les cinq publications d'images du LOT 11 (`T1` à
`T5`) étaient toutes en échec sur la porte « Trivy sur les images publiées » — jamais remarqué car
cette porte n'est pas un contrôle requis de pull request (§9.4 de la passation). Cause mesurée :
`CVE-2026-111497` (`CRITICAL`, corrigeable) sur `brotli-libs` dans la base `caddy:2.11-alpine` de
l'image `web`, publiée par Alpine entre le 28 et le 30/10/2026 — ce défaut **précède** le LOT 11
(déjà présent à « Chantier front S14 », 30/10/2026). Corrigé par une couche `apk` épinglée
(`brotli-libs=1.2.1-r0`), même classe que `DEC-581` pour `perl-base`, vérifiée construite et lancée
sur les deux architectures avant d'être poussée. Détail complet :
[`compte-rendu-t7-lot-11.md`](compte-rendu-t7-lot-11.md) §3.1.

## 4. Reclassement du §30 du modèle

`make recette-modele-check` relit directement les 25 contrôles du §30. Les trois contrôles que `T16`
du LOT 10 avait déjà attribués à ce lot (`§30.19`, `§30.21`, `§30.23`) sont reclassés ACQUIS en
réutilisant des témoins **déjà existants** de `T1`, `T2` et `T4`, jamais rapprochés du §30 avant
cette relecture — aucun test nouveau.

Résultat : **23 acquis, 2 partiel, 0 reporté, 0 inapplicable** — contre 20/2/3/0 depuis `T16` du
LOT 10. Les deux partiels (`§30.4`, `§30.8`) sont des résiduels de processus antérieurs au LOT 11,
documentés depuis les LOTS 3/5/7 ; aucun n'appartient à ce lot.

## 5. Contrôles exécutés

| Contrôle | Résultat relevé le 01/11/2026 |
|---|---|
| `make recette-modele-check` | 25 contrôles classés : **23 acquis, 2 partiel, 0 reporté, 0 inapplicable** |
| `make docs-check` | vert — `DEC-681` prochain libre, 12 contrôles de totaux dérivés |
| `make sources-check` / `isolation-check` / `migrations-check` | tous verts |
| `make check` (qualité) | Ruff, Prettier, ESLint, `mypy`, `tsc --noEmit` : tous verts |
| `pytest` depuis la racine | 2 092 collectés, inchangé ; échecs environnementaux identiques un par un à `origin/develop` (comparaison de worktree) |
| `make test-frontend` | 992 Vitest, inchangé |
| `make residu-check` | aucun résidu laissé |
| Construction locale `apps/web/Dockerfile` (deux architectures) | `brotli-libs-1.2.1-r0` installé, artefact lancé et sert |
| `images.yml` rejoué sur la branche de `T7` (`workflow_dispatch`) | porte verte, Trivy confirme `CRITICAL: 0` sur les trois images |
| `make images-pin` / `make recette-check` (images publiées corrigées) | 57 contrôles, 0 échec, 7/7 séparations |
| `make back-office-check` / `onboarding-check` / `accueil-check` / `framework-check` (développement et recette) | tous verts, mêmes résultats dans les deux environnements |

## 6. Décision de Jonathan

**Ce que tu valides :** les sept critères de sortie du LOT 11 (§1.4 de la fiche), en distinguant les
six preuves techniques tenues de ta propre confirmation requise par le septième — les traitements
asynchrones construits par ce lot (jobs persistés, outbox, miniatures, planification avec verrou,
nettoyage des médias, supervision).

**Ce que la porte clôt :** le LOT 11 ; elle n'ouvre aucun autre lot sans instruction explicite.
L'intégration des données de démonstration (entité EXALT Bordeaux) reste une action distincte,
postérieure, sur ton instruction.

| | |
|---|---|
| Date | — |
| Décision | ☐ franchie ☐ à reprendre |
| Validation de Jonathan | — |
| Réserves | `ECART-012` (Léa), `ECART-061` (LOT 13), `QO-092` (volet canal externe), `QO-096`/`QO-097`/`QO-099`/`QO-100`/`QO-110`/`QO-121`/`QO-125`/`QO-126`, `ROAD-RSK-033`/`ROAD-RSK-034` restent ouvertes, non bloquantes pour `G11` — à reprendre aux lots suivants au besoin |

Décision à consigner au registre une fois validée (`DEC-682` probable). Tag `v0.11.0` à poser sur
`main` après fusion de `T7` et validation.
