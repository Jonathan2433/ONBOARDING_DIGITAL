# Référentiel documentaire — eXalt Onboarding Digital

Ce dossier est la source de vérité du projet. Aucune décision de conception ne doit être
prise en dehors de ce qui y est écrit.

---

## 1. Documents de cadrage validés

| Document | Emplacement | Version | Statut | Date de validation |
|---|---|---|---|---|
| Cahier des charges consolidé | [`product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md`](product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md) | 1.0 | **Validé** par Jonathan — décision `DEC-423` | 27 juillet 2026 |
| Matrice des rôles et permissions | [`product/MATRICE_ROLES_PERMISSIONS_EXALT.md`](product/MATRICE_ROLES_PERMISSIONS_EXALT.md) | 1.1 | **Validé** par Jonathan | 25 juillet 2026 |
| Modèle de données et diagrammes | [`architecture/MODELE_DONNEES_EXALT.md`](architecture/MODELE_DONNEES_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |
| Roadmap MVP, V1 et V2 | [`product/ROADMAP_MVP_V1_V2_EXALT.md`](product/ROADMAP_MVP_V1_V2_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |
| Backlog initial priorisé | [`product/BACKLOG_INITIAL_PRIORISE_EXALT.md`](product/BACKLOG_INITIAL_PRIORISE_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |

Ces cinq fichiers sont **immuables** en l'état. Leur intégrité est prouvée par empreinte
SHA-256 et la conformité des annexes du cahier des charges est vérifiée :
voir [`operations/integrite-et-conformite-documents.md`](operations/integrite-et-conformite-documents.md).

Le cahier des charges intègre les quatre autres documents en annexes contractuelles A à D.
Le contrôle de conformité établit qu'il n'existe **aucune divergence de contenu** entre les
annexes et les documents spécialisés.

### Statut du cahier des charges

Le fichier porte en en-tête la mention « soumis à validation finale de Jonathan », qui
correspond à son état du 25 juillet 2026. Jonathan l'a validé le 27 juillet 2026. Par
décision `DEC-423`, cette validation est enregistrée au registre des décisions **sans
modifier le fichier** : valider n'est pas une évolution de contenu, la procédure du cahier
des charges section 35 n'exige donc pas de changement de version, et l'immuabilité du
fichier préserve la preuve d'intégrité par empreinte. Le statut faisant foi est celui du
présent index et du registre des décisions.

---

## 2. Organisation des dossiers

| Dossier | Contenu | Responsable principal |
|---|---|---|
| [`product/`](product/README.md) | Cahier des charges, matrice des droits, roadmap, backlog, contenus éditoriaux | Léa (produit), Tess et Diane (contenus) |
| [`architecture/`](architecture/README.md) | Modèle de données, schéma du CSV collaborateurs, listes contrôlées, décisions d'architecture | Jonathan |
| [`decisions/`](decisions/README.md) | Registre des décisions, registre des écarts | Jonathan |
| `operations/` | Conventions Git et versions, traçabilité GitHub, registres des risques, des questions ouvertes et des dépendances externes, responsabilités, politique de configuration et de secrets, contrôles de sortie, fiches de lot | Jonathan |
| [`prototype/`](prototype/README.md) | Prototype historique, conservé pour historisation, non versionné, non réutilisable | — |

---

## 3. Règle de préséance

En cas de contradiction entre deux sources :

1. le cahier des charges consolidé prévaut ;
2. une décision validée plus récente prévaut sur une décision plus ancienne ;
3. les annexes validées précisent les règles détaillées ;
4. aucune hypothèse ne remplace une décision explicite de Jonathan.

Procédure d'évolution, cahier des charges section 35 :

1. une décision explicite est enregistrée ;
2. le document spécialisé concerné change de version ;
3. l'impact sur le modèle, la roadmap, le backlog et les tests est évalué ;
4. le cahier des charges est mis à jour ;
5. le contrôle de conformité des annexes est rejoué.

---

## 4. Séquences d'identifiants

Les identifiants ne sont **jamais** réutilisés. Toute nouvelle entrée poursuit la séquence
existante.

| Séquence | Objet | Étendue | Prochain libre | Registre |
|---|---|---|---|---|
| `DEC-nnn` | Décisions de projet | `001` à `417` **réservés** ; `418` à `556` en usage | `DEC-557` | [décisions](decisions/registre-decisions.md) |
| `RIGHTS-nnn` | Décisions de droits | `001` à `025` | `RIGHTS-026` | [décisions](decisions/registre-decisions.md) |
| `DATA-nnn` | Décisions de modèle | `001` à `018` | `DATA-019` | [décisions](decisions/registre-decisions.md) |
| `ROAD-nnn` | Décisions de roadmap | `001` à `012` | `ROAD-013` | [décisions](decisions/registre-decisions.md) |
| `BACKLOG-nnn` | Décisions de backlog | `001` à `010` | `BACKLOG-011` | [décisions](decisions/registre-decisions.md) |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK-nnn` | Arbitrages | `-001` à `-005` chacun | `-006` | [décisions](decisions/registre-decisions.md) |
| `ECART-nnn` | Écarts | `001` à `046` | `ECART-047` | [écarts](decisions/registre-ecarts.md) |
| `QO-nnn` | Questions ouvertes | `072` à `105` avec **5 trous**, puis `106` à `118` | `QO-119` | [questions](operations/registre-questions-ouvertes.md) |
| `ROAD-RSK-nnn` | Risques | `001` à `034` | `ROAD-RSK-035` | [risques](operations/registre-risques.md) |
| `DEP-nnn` | Dépendances externes | `001` à `017` | `DEP-018` | [dépendances](operations/registre-dependances-externes.md) |
| `CONT-nnn` | Contenus éditoriaux inventoriés | `001` à `029` | `CONT-030` | [inventaire](product/contenus/inventaire-prototype.md) |
| `MVP-Lnn-USnnn` | User stories | `MVP-L00-US001` à `MVP-L14-US007` | — | backlog validé |
| `Gn` | Portes de validation | `G0` à `G14` | — | roadmap validée |

Trous conservés et jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`
(`ECART-011`). Les règles de tenue figurent dans
[`decisions/README.md`](decisions/README.md).

### Traitement de la référence `DEC-001` à `DEC-417`

Les cinq documents référencent des décisions `DEC-001` à `DEC-417` issues des ateliers de
cadrage, mais la table correspondante n'est présente dans aucun document du corpus
(écart `ECART-004`).

Décision `DEC-422` : les **85 décisions et arbitrages consolidés** — `RIGHTS-*`, `DATA-*`,
`ROAD-*`, `BACKLOG-*` et `ARB-*` — font foi comme registre décisionnel du projet. La
référence `DEC-001` à `DEC-417` est conservée comme référence historique aux ateliers, et la
plage est **réservée** afin qu'un import ultérieur ne produise aucun conflit d'identifiant.
Les nouvelles décisions du projet démarrent à `DEC-418`.

Les registres sont créés en sous-étape **S4** du LOT 0.

---

## 5. Conventions de nommage

Décision retenue le 27 juillet 2026 :

- les **cinq documents validés** conservent leur nom d'origine en majuscules, afin de
  préserver la traçabilité avec le prompt de cadrage et les références croisées internes ;
- les **documents produits par le projet** utilisent le kebab-case minuscule, par exemple
  `registre-decisions.md`, `schema-csv-collaborateurs.md`.

Le système de fichiers de la machine de développement est **insensible à la casse** : tout
renommage ne différant que par la casse exige une manœuvre en deux temps.

---

## 6. Portes de validation

| Porte | Moment | Validation obligatoire | État |
|---|---|---|---|
| `G0` | Fin du référentiel | Jonathan confirme les documents et conventions | **Validée** le 27/07/2026 |
| `G1` | Fin du socle local | Stack, CI et images validées | **FRANCHIE** le 12/08/2026 — tag `v0.1.0` posé sur `main` |
| ~~`G2`~~ | Fin du modèle implémenté | Contraintes et isolation validées | **FRANCHIE le 20/08/2026** — les 7 critères acquis, [checklist](operations/checklist-validation-G2.md) instruite, tag `v0.2.0`. `DEC-517` |
| `G3` | Fin de l'authentification | Sécurité et sessions validées | **Porte courante** — LOT 3 ouvert le 20/08/2026 (`DEC-518`), tag `v0.3.0` prévu. Plan : [`fiche-lot-3.md`](operations/fiche-lot-3.md), **12 sous-étapes soumises à validation** |
| `G4` | Fin du portail national | Navigation et lecture inter-entités validées | Planifiée |
| `G5` | Fin du trombinoscope | Profils et permissions validés | Planifiée |
| `G6` | Fin du Framework | Contenus et périmètres éditoriaux validés | Planifiée |
| `G7` | Fin de l'onboarding | Tess, Léa, Diane et Jonathan valident les parcours | Planifiée |
| `G8` | Fin de l'accueil | Événements et page d'accueil validés | Planifiée |
| `G9` | Fin du back-office | Import réel répété et validé | Planifiée |
| `G10` | Fin du pilotage | Audit, reporting et support validés | Planifiée |
| `G11` | Fin des traitements | Médias, worker et planification validés | Planifiée |
| `G12` | Fin de recette | Aucun défaut bloquant selon les règles convenues | Planifiée |
| `G13` | Production temporaire | Déploiement, sauvegarde et restauration validés | Planifiée |
| `G14` | Production générale | Léa valide le produit, Jonathan la technique | Planifiée |

Aucun lot dépendant ne commence avant validation explicite du lot précédent
(décision `ROAD-003`, arbitrage `ARB-BACK-003`).

---

## 7. Avancement du LOT 0 — **lot terminé et verrouillé**

| Sous-étape | Objet | Story | État |
|---|---|---|---|
| S1 | Dépôt, arborescence documentaire, barrières de sécurité | `MVP-L00-US001` | **Validée** par Jonathan le 27 juillet 2026 |
| S2 | Versionnement des documents validés | `MVP-L00-US002` | **Validée** par Jonathan le 27 juillet 2026 |
| S3 | Conventions Git, versions et contribution | `MVP-L00-US003` | **Validée** par Jonathan le 27 juillet 2026 |
| S4 | Registres décisions, risques, questions, dépendances, écarts | `MVP-L00-US006` | **Validée** par Jonathan le 27 juillet 2026 |
| S5 | Modèles de configuration sans secrets | `MVP-L00-US007` | **Validée** par Jonathan le 27 juillet 2026 |
| S6 | Schéma initial du CSV collaborateurs | `MVP-L00-US004` | **Validée** par Jonathan le 27 juillet 2026 |
| S7 | Inventaire des contenus du prototype | `MVP-L00-US005` (`P1`) | **Validée** par Jonathan le 27 juillet 2026, statut `à relire` (`DEC-437`) |
| S8 | Contrôles de sortie et préparation de la porte `G0` | — | **Validée**. Porte `G0` franchie le 27 juillet 2026 (`DEC-438`) |

---

## 8. Avancement du LOT 1 — **terminé**, porte `G1` **franchie**

Ouvert par Jonathan le 27 juillet 2026 (`DEC-450`), **verrouillé le 12 août 2026**. Plan :
[`operations/fiche-lot-1.md`](operations/fiche-lot-1.md). Arbitrages préalables :
[`operations/compte-rendu-t0-lot-1.md`](operations/compte-rendu-t0-lot-1.md).
Comptes rendus de sous-étape :
[`T1`](operations/compte-rendu-t1-lot-1.md) · [`T2`](operations/compte-rendu-t2-lot-1.md) · [`T3`](operations/compte-rendu-t3-lot-1.md) · [`T4`](operations/compte-rendu-t4-lot-1.md) · [`T5`](operations/compte-rendu-t5-lot-1.md) · [`T6`](operations/compte-rendu-t6-lot-1.md) · [`T7`](operations/compte-rendu-t7-lot-1.md) · [`T8`](operations/compte-rendu-t8-lot-1.md) · [`T9`](operations/compte-rendu-t9-lot-1.md) · [`T10`](operations/compte-rendu-t10-lot-1.md) · [`T11`](operations/compte-rendu-t11-lot-1.md).
Checklist de la porte : [`checklist-validation-G1.md`](operations/checklist-validation-G1.md).

| Sous-étape | Objet | Story | Issue | État |
|---|---|---|---|---|
| `T0` | Prérequis et arbitrages techniques | — | — | **Terminée** hors lot. 3 prérequis levés, 7 choix tranchés (`DEC-439`–`DEC-449`, dont `DEC-449` qui remplace `DEC-448`) |
| `T1` | Squelette du monorepo, outillage, versions épinglées | `MVP-L01-US001` | `#2` | **Terminée** les 27 et 28/07/2026. 7 répertoires, chaîne de qualité Python et TypeScript, versions épinglées. `DEC-451`–`DEC-457`, `ECART-017` et `ECART-018` clos, `ROAD-RSK-029` ouvert, `ROAD-RSK-026` matérialisé puis résiduel accepté |
| `T2` | Compose développement, 8 services sains | `MVP-L01-US002` | `#3` | **Terminée** le 28/07/2026. Les 8 services sains par une commande, volumes prouvés persistants. `DEC-458`–`DEC-461`, `ECART-019` clos, `ROAD-RSK-030` et `QO-111` ouverts |
| `T3` | API FastAPI, 3 healthchecks, migration initiale | `MVP-L01-US003` | `#4` | **Terminée** le 28/07/2026. 3 endpoints, 11 garde-fous testés, migration `0001` sur PostgreSQL réel, 61 tests. `DEC-462`–`DEC-465`, `ECART-006` clos, `QO-112` ouverte |
| `T4` | Journalisation JSON corrélée | `MVP-L01-US004` | `#5` | **Terminée** le 28/07/2026. Les 10 champs du cahier §28.1, 3 barrières de masquage, corrélation requête **et** job, rotation sur les 8 services. **139 tests** — corrigé de 131 au titre de `ECART-021`. `DEC-466`–`DEC-469`, `QO-113` ouverte |
| `T5` | Frontend Vite, page de statut | `MVP-L01-US002` | `#3` | **Terminée** le 28/07/2026. Page servie par Caddy, état réel des 3 dépendances éprouvé **en arrêtant Redis**, version du build, 5 états, 25 tests Vitest et Testing Library. `DEC-470`–`DEC-473`, `ECART-020` et `ECART-021` clos, `ROAD-RSK-031` ouvert, `ROAD-RSK-030` aggravé, `QO-085` mesurée |
| `T6` | CI GitHub Actions, 3 échecs volontaires prouvés | `MVP-L01-US005` | `#6` | **Terminée** le 29/07/2026. Les 11 contrôles du cahier §23.1 exécutés sur chaque pull request, pipeline vert, et **les trois échecs prouvés** — lint, test et secret, chacun bloquant la fusion. CI rendue **obligatoire** sur `develop` et `main`. `DEC-474`–`DEC-477`, `ROAD-RSK-032` et `QO-114` ouverts |
| `T7` | Images multiarchitecture, GHCR privé | `MVP-L01-US006` | `#7` | **Terminée** le 29/07/2026. Les 3 images construites pour `linux/amd64` **et** `linux/arm64` en une liste de manifestes unique, **lancées sur les deux** — 39 contrôles fonctionnels, 0 échec. Image `web` de **1,02 Gio à 84,9 Mo** par deux cibles nommées, `ROAD-RSK-030` et `ROAD-RSK-031` **clos**. Version et révision **gravées** dans les images. Trivy mesuré puis réglé. `DEC-478`–`DEC-482`, `ECART-022` clos, **`ROAD-RSK-033` ouvert** |
| `T8` | Environnement de recette isolé | `MVP-L01-US002` | `#3` | **Terminée** le 29/07/2026. Les **sept** séparations du cahier §22.2 prouvées sur l'état réel des deux environnements — **57 contrôles, 0 échec**, dont l'isolement du routage éprouvé avec ses témoins. La recette exécute les **images publiées épinglées par empreinte**, et `arm64` y est **natif** : la réserve de la fiche §3.1 est **levée**. `Makefile` paramétré par environnement, 44 → **50 cibles**, sans duplication. `DEC-483`–`DEC-488`, `ECART-023` clos, **`ROAD-RSK-034` ouvert**, **`QO-085` CLOSE** — 836,6 Mio pour deux stacks simultanées |
| `T9` | Documentation d'exploitation locale | `MVP-L01-US008` | `#9` | **Terminée** le 29/07/2026. [`exploitation-locale.md`](operations/exploitation-locale.md) créé, **toutes** ses commandes exécutées. Démarrage à froid véritable prouvé — 0 volume, 0 image, remontée en **34 s**. 14 publications et 12 volumes **dérivés**. Trois cibles jamais exercées éprouvées, dont `make destroy`, dont l'avertissement était **faux** pour la recette. `DEC-489`, `ECART-024` |
| `T10` | Design system et contrat API | `MVP-L01-US007` (`P1`) | `#8` | **Terminée** le 30/07/2026. Jetons **relevés** du prototype et **recalculés** contre WCAG 2.2 AA — la mesure a corrigé deux défauts d'accessibilité que le prototype portait. 3 composants de base, contrat partagé par manifeste unique lu par **TypeScript et Python**. **260 tests**, 11 témoins, **aucune dépendance ajoutée**. `DEC-491`–`DEC-493`, `QO-115` ouverte, **`ROAD-RSK-032` CLOS** — l'audit passe à **zéro avis, zéro tolérance** |
| `T11` | Contrôles de sortie et porte `G1` | — | — | **Terminée** le 12/08/2026. **33 contrôles rejoués, tous à 0**, tous les nombres **dérivés**. [Checklist](operations/checklist-validation-G1.md) remise à Jonathan avec une démonstration guidée. Aucune décision ajoutée. **Le tag `v0.1.0` attend la validation** |

Traçabilité GitHub en place (`DEC-449`) : 13 étiquettes, 15 milestones, epic `#1`, stories `#2`
à `#9`. **`main` et `develop` sont protégées** — toute modification passe par une pull request.

---

## 9. Avancement du LOT 3 — **lot ouvert**, porte `G3`

**Ouvert par Jonathan le 20 août 2026 (`DEC-518`), découpage validé le même jour.** Plan :
[`operations/fiche-lot-3.md`](operations/fiche-lot-3.md) — **12 sous-étapes, `T1` à `T12`**,
8 stories dont **7 en `P0`**, les **7 tables** du modèle §10, tag `v0.3.0`.
Traçabilité GitHub : epic `#62`, jalon `G3`, stories `#63` à `#70`.

> **`T1` est le moindre privilège PostgreSQL, avant l'authentification elle-même** — arbitrage de
> Jonathan, `DEC-518`. Motif : le LOT 3 est celui qui introduit l'accès extérieur, donc celui où
> l'exposition de `QO-116` cesse d'être théorique.

| | Sous-étape | Story | État |
|:--:|---|---|---|
| `T1` | Moindre privilège PostgreSQL — deux rôles | — | **Terminée** le 20/08/2026. **`QO-116` close.** Trois comptes et non deux : `initdb` crée un superutilisateur, ce qui change c'est que l'application ne l'emploie plus. `btree_gist` est **`trusted`**, mesuré — sans quoi la migration `0002` aurait été inapplicable. `REASSIGN OWNED` a échoué : **188 des 196 fonctions appartiennent à l'extension**. Tout rejoué sur une base **recréée de zéro** : 8 services sains, 11 migrations, **390 tests**. `DEC-520`, `ECART-033` |
| `T2` | Les sept tables du modèle §10, migration `0012` | toutes | **Terminée** le 21/08/2026. **Les §25.2 à §25.4 n'imposent AUCUNE contrainte** à ces tables : aucune exclusion, aucune clé composite — en poser serait exiger plus que le modèle. Le §25.1 s'ouvrant par « à prévoir **notamment** », **quatre unicités de plus** sont posées, chacune **dérivée** d'une règle écrite. L'index partiel de `magic_link_request` porte l'**invariant** du §10.3, pas son action. **`make secrets-check`** distingue les empreintes de jeton (SHA-256, bornées) des empreintes de mot de passe (format variable, accompagnées de leur algorithme). **415 tests.** `DEC-521` |
| `T3` | Magic link — la **demande**, réponse générique | `MVP-L03-US001` | **Terminée** le 21/08/2026. **Le critère est une ÉGALITÉ, pas un refus** : la route n'a **qu'un seul gabarit de réponse**, ce qui rend la divergence impossible plutôt qu'improbable — `202`, 143 octets, 7 en-têtes, **0 divergence** entre adresse connue, inconnue et profil archivé, mesuré **à travers Caddy en HTTPS**, témoin du comparateur compris. **`§30.11` passe de `reporte` à `acquis`** — 11 acquis contre 10. **L'autorité des domaines est la TABLE**, modèle §5.4 littéral, et `make domaines-provision` pose la ligne initiale **sans jamais réactiver** un domaine qu'un administrateur a coupé (`DEC-523`). Le jeton porte un **préfixe** qui rend les deux détecteurs **exacts** au lieu d'heuristiques, et la famille est **réservée** pour `T6` et `T10`. **`PUBLIC_BASE_URL` était fausse et n'était transmise à personne** — §7.16, elle n'avait jamais eu de consommateur. **469 tests**, `make magic-link-check` **dans la CI**. `DEC-522`, `DEC-523` |
| `T4` | Magic link — la **consommation**, usage unique | `MVP-L03-US002` | **Terminée** le 21/08/2026. **L'usage unique est une COURSE, pas une vérification** : un **compare-et-pose atomique** dont le nombre de lignes affectées EST le verdict. **Trois versions du test de concurrence, et les deux premières ne prouvaient rien** — la seconde ne discriminait pas, un service lire-puis-écrire prenant le **même** verrou au moment d'écrire. Le témoin négatif est décisif : sur une implémentation vulnérable, le test concurrent échoue sur `'lien_consomme' == 'lien_refuse'` **et les deux autres tests passent**. **Le jeton voyage dans le CORPS, jamais dans l'URL** — historique du navigateur, `Referer`, journal d'un mandataire : trois canaux que `DEC-469` ne couvre pas. Un **seul** gabarit de refus pour quatre causes, dérivé de l'écran unique de `T11`, et son contrôle a trouvé une divergence réelle — l'identifiant de corrélation du §18.3. **L'absence de journal d'accès Caddy est rapportée comme une ABSENCE et GARDÉE** : 0 ligne « handled request » sur 3 171, et le contrôle échoue si un bloc de site en déclare un sans filtre. **482 tests**, `magic-link-check` de 10 à **15 contrôles**. `DEC-524`, `DEC-525` |
| `T5` | Compte administrateur local, hachage et verrouillage | `MVP-L03-US003` | **Terminée** le 21/08/2026. `scrypt` de la bibliothèque standard (`DEC-526`), **et le motif du choix est la MÉMOIRE** : 64 Mio par calcul, contre 128 à `N = 2^17` pour une limite de service de 1 024 Mio — **huit connexions simultanées suffiraient à la saturer**. Zéro dépendance ajoutée ; `bcrypt` aurait de plus tronqué silencieusement au-delà de 72 caractères. Le verrouillage **réutilise les deux nombres du §20.2** au lieu d'en inventer, **se relâche seul** — la parade au risque « le verrouillage bloque Jonathan lui-même » — et une tentative sur un compte verrouillé **ne le prolonge pas**, sans quoi il deviendrait un déni de service permanent. Le compteur est un **compare-et-pose atomique**, comme l'usage unique de `T4` : le témoin négatif échoue sur « le compteur vaut 1 au lieu de 2 ». **La dette du §8.4 que `T11` du LOT 2 avait laissée est acquittée** — deux tables, deux portées, et la **période** exigée plutôt que `ends_at IS NULL`, parce qu'une affectation future a elle aussi `ends_at` nul. **Le jeu de recette a révélé une lacune de lui-même** : il attribuait `dg` par un DSM et ne créait aucun ESM. **525 tests**, `make admin-check` dans la CI. `DEC-526` à `DEC-528`, **`QO-118` ouverte** |
| `T6` | Sessions, cookie et déconnexion | `MVP-L03-US004` | **Terminée** le 21/08/2026. **Rien n'était à inventer, et j'allais le faire** : le cahier §7.4 exige `SameSite` sans dire laquelle, et `.env.example` écrit **`lax`** depuis la sous-étape S5 du LOT 0 — avec le nom du cookie et les deux durées. Quatre valeurs déjà tranchées, §9.0. **Le jeton n'apparaît dans AUCUN corps de réponse** : c'est ce qui rend « aucun jeton dans `localStorage` » **structurel** plutôt que disciplinaire — un frontend qui reçoit un jeton finit par le stocker. Le contrôle des sources du frontend est **exact** : il retire les commentaires, garde les chaînes, et son témoin l'éprouve **dans les deux sens** — un usage réel doit être vu, un commentaire ne doit pas l'être. Les deux expirations sont bornées **des deux côtés**, et un test les **distingue** : une session gardée active par des lectures régulières meurt au trentième jour. Le rafraîchissement est un **compare-et-pose atomique** — troisième occurrence du patron dans le lot — et le témoin négatif montre que les **8 tests séquentiels sont aveugles** au défaut. **`SESSION_COOKIE_SECURE` et `CSRF_PROTECTION_ENABLED` n'étaient pas transmises au conteneur**, 0 occurrence : deux des sept garde-fous de production du §20.3 ne pouvaient donc pas se déclencher. **550 tests**, `make sessions-check` et `make sessions-temoin`. `DEC-529`, `DEC-530` |
| `T7` | CSRF et idempotence | `MVP-L03-US005` | **Terminée** le 21/08/2026. **Deux barrières, et leur portée diffère** : l'en-tête `Origin` sur les **cinq** écritures — le navigateur le pose lui-même et aucun script ne peut le falsifier, ce qui protège les **trois** routes qui précèdent toute session — et un jeton **dérivé de la session par HMAC**, jamais stocké, sur celles qui en ont une. **`SameSite=lax` ne suffit pas, et c'est le §7.4 qui le dit** : il raisonne par site, non par origine. **L'idempotence est adossée à Redis sans inventer de table** — le modèle place déjà la clé sur `async_job`, LOT 11 — et le résiduel est **nommé** : Redis n'est pas durable, la garantie couvre la double soumission, pas un rejeu à plusieurs jours. **`APP_SECRET_KEY` devient obligatoire dans tous les environnements**, `T7` la consommant sans repli, et le garde-fou a immédiatement nommé quatre tests où elle ne traversait pas la frontière de processus — **la leçon de `T1` rejouée**. **585 tests**, `make csrf-check` dans la CI. **Huit tests antérieurs ont échoué, tous légitimement** : c'est la sous-étape où le §7.21 s'est manifesté le plus largement, parce qu'elle change une règle qui traverse **toutes** les écritures. `DEC-531`, `DEC-532` |
| `T8` | Limitation de débit | `MVP-L03-US001`, `US003` | **Terminée** le 21/08/2026. **Le cahier §20.2 donne les seuils, et le §8 de la fiche affirmait le contraire** — `ECART-034`, ouvert et clos : « Seuils initiaux » en énumère **six**, et `.env.example` en porte cinq **depuis le LOT 0**. Choisir une valeur aurait **contredit le cahier**, qui prévaut sur tout ; deux tests **relisent le cahier** pour l'empêcher de se reproduire. **Deux verbes, et la distinction commande tout** : « limitation » pour l'adresse → refus **429** ; « alerte » pour l'origine et les échecs administrateur → **détection journalisée**, l'alerte elle-même exigeant `operational_alert` du §21.2, **LOT 10**. En faire un refus bloquerait **tout un bureau derrière un partage d'adresse**. **Le compteur porte sur l'adresse normalisée AVANT toute lecture de la base** : s'il ne valait que pour les adresses connues, le 429 dirait « ce compte existe » et **rouvrirait l'oracle de `T3`** — les deux refus sont donc comparés corps **et** en-têtes. Adresse et origine entrent dans Redis en **empreinte HMAC**, jamais en clair. **Le compteur d'échecs par adresse comble le trou du verrou de `T5`** — `failed_login_count` vit sur `user_account`, donc une adresse sans compte n'a aucun compteur — avec les **mêmes** deux nombres, et il est **effacé sur succès**. **613 tests**, `make debit-check` — **12 contrôles, 3 témoins** — dans la CI. `DEC-533`, `DEC-534` |
| `T9` | Révocation au départ | `MVP-L03-US006` | **Terminée** le 22/08/2026. **`§30.22` devient ACQUIS.** **La révocation tient au DÉPART, non au seul archivage, et c'est le §24.1 qui le tranche** : il n'existe **aucune** transition `Active --> Archived`, si bien qu'attendre l'archivage — la lettre de `US006` — laisserait une fenêtre pendant laquelle un collaborateur parti conserve une session active, ce que le §7.4 et le §30.22 interdisent tous deux par le mot « **immédiatement** ». Les deux transitions révoquent donc, la seconde étant **idempotente**, et un témoin le prouve. **`invitation` n'existe pas** — 0 occurrence dans le modèle et dans la matrice, le cahier ne le nommant que comme objet audité, opération idempotente (LOT 11) et tâche d'expiration : `ECART-035`, à reprendre au LOT 9. **L'ordre des écritures est imposé par un déclencheur** : `fn_dg_implique_dsm_local` exige une responsabilité DSM active dès que la catégorie vaut `dg`, **sans regarder l'état**, donc clore les rôles d'abord ferait échouer le départ d'un DG — un test l'éprouve. **Quatre situations sont rapportées et non décidées** : rôles globaux, relations futures, consultants privés de DSM, liens déjà consommés. **Et une garde a été retirée plutôt qu'écrite** — l'index partiel `uq_entity_membership_person_id_occupante` rend impossible l'état contre lequel elle défendait — remplacée par un test qui **exige que la base continue de l'interdire**. **630 tests**, `make revocation-check` — **6 contrôles, 3 témoins** — dans la CI. `DEC-535` |
| `T10` | Comptes de service et scopes | `MVP-L03-US007` (`P1`) | **Terminée** le 22/08/2026. **Le §8 de la fiche annonçait deux choses fausses**, et c'est le premier travail de la sous-étape : le cahier **§22 énumère cinq scopes** (`ECART-036`), et la durée des jetons était **déjà numérotée `QO-072`** dans le cahier §32. **Mais les deux mots « par exemple » disent que la liste des scopes n'est PAS fermée** — même forme que le « à prévoir notamment » du §25.1 — si bien que les deux erreurs sont **symétriques** : inventer un vocabulaire, ou le fermer par liste blanche et bloquer les LOTS 9 et 11. La validation porte donc sur la **forme** `domaine:action`, et deux tests relisent le cahier — dont un pour les mots « par exemple » eux-mêmes. **`QO-072` est CLOSE par arbitrage de Jonathan : 90 jours**, et la valeur reste **configurable**, ce que le §10.5 exige littéralement — l'inverse exact des seuils de `T8`. **`ECART-037`, et il produit la migration `0013`** : `auth_event` ne portait pas le lien vers `service_account` que le diagramme §11 déclare, or sans lui « chaque appel est audité » exigeait un **huitième** type d'événement que le §10.6 interdit. **Un défaut, trouvé par mon propre contrôle** : le refus d'un jeton périmé n'était attribué à aucun compte, donc l'audit ne disait pas **qui** s'obstine avec une clé morte. **661 tests**, `make service-check` — **11 contrôles, 3 témoins** — dans la CI. **Résiduel nommé** : aucune route ne consomme encore le scope. `DEC-536` |
| `T11` | Les huit écrans d'authentification | — | **Terminée** le 22/08/2026. **Le compte est DÉRIVÉ du cahier** : six puces dont la dernière nomme trois pages → **5 + 3 = huit**, et chaque libellé déclaré est confronté **mot pour mot** au document — une reformulation « qui veut dire la même chose » ne serait pas vérifiable. **Et un écran n'est pas une route** : « lien expiré ou déjà consommé » est **l'état d'échec** de la route qui consomme le lien. **`DEC-456` tranchait déjà le routeur, dans l'autre sens que mon instinct** — j'allais en écrire un minimal : le cahier §17.1 **nomme React Router**, et `DEC-456` ne l'installait pas « faute d'usage **avant le LOT 4** ». `T11` crée cet usage une étape plus tôt, donc la condition est remplie ; les **quatre autres** bibliothèques restent dehors, par le même raisonnement appliqué honnêtement. **Le contrôle exerce pour la première fois le repli `try_files`** posé en `T7` du LOT 1, qui l'anticipait mais n'avait jamais eu de chemin à replier — §7.16 — et le **type MIME fait foi**, Vite rendant 200 + `index.html` pour tout chemin inconnu. Il vérifie aussi que `/api/*` **ne reçoit pas** l'artefact statique, ce que `DEC-470` interdit. **Trois invariants que l'interface pouvait défaire** : la réponse générique — deux adresses différentes, un rendu **identique** — le jeton de magic link **retiré de la barre d'adresse** et envoyé dans le corps, et **aucun stockage navigateur**. **Et le linter a imposé un meilleur découpage que le mien** : une lecture pure et un effet de bord ne devaient pas être la même fonction. **794 tests**, `make ecrans-check` — **7 contrôles** — dans la CI. `DEC-537` |
| `T12` | Audit des événements, recette et checklist `G3` | `MVP-L03-US008` | **Terminée** le 22/08/2026. **Les sept types du §10.6 sont produits par des appels HTTP RÉELS**, non insérés — insérer sept lignes prouverait que la table accepte sept valeurs, pas que les actions les produisent. Le compte est **importé** de `TypeEvenementAuth`, donc un huitième type ferait échouer le contrôle, **et c'est son rôle**. **Les deux acteurs sont exigés** — un contrôle qui ne compterait que `person_id` déclarerait l'audit acquis en ignorant les comptes de service. **Et le contrôle porte son témoin** : un mot de passe inséré exprès, qu'il doit trouver, sans quoi l'absence de fuite prouverait l'absence de contrôle. **Deux contrôles structurels remplacent une huitième promesse de vigilance** : `make residu-check`, un avant/après **exact** table par table — la liste des tables étant dérivée du catalogue, pas une liste de marqueurs qui vieillirait — qui **remplace** `test-integration` dans la CI ; et `make icloud-verify` étendu à la comparaison de l'**arbre** avec l'amont, le garde-fou existant s'étant révélé **aveugle** à une réversion silencieuse de quatre fichiers survenue pendant cette sous-étape. Les deux ont leur **témoin négatif exécuté**. **Les trois lignes que la fiche annonçait pour `§30` étaient inexactes** — quatrième fois pour ce document. **794 tests**, `evenements-check` et `residu-check` dans la CI. `DEC-538`, checklist `G3` remise |

---

## 10. Avancement du LOT 2 — **lot VERROUILLÉ**, porte `G2` franchie

**Ouvert par Jonathan le 18 août 2026 (`DEC-496`).** Plan soumis à validation :
[`operations/fiche-lot-2.md`](operations/fiche-lot-2.md) — **12 sous-étapes, `T1` à `T12`**,
8 stories dont **7 en `P0`**, **16 tables** du modèle, tag `v0.2.0`.
**Découpage validé par Jonathan le 18/08/2026.** `ECART-012` est échu dans ce lot, rattaché à `T5`.

| | Sous-étape | Story | État |
|:--:|---|---|---|
| `T1` | Socle technique du modèle et extensions | `MVP-L02-US008` | **Terminée** le 18/08/2026. Collation **ICU `fr-FR`** posée avant la première table, `btree_gist` seule extension, socle déclaratif éprouvé — **20 tests**, dont le refus de chevauchement par la base et ses trois témoins. `QO-111` et `QO-112` **closes**, les **7** choix du §9.2 tranchés. `DEC-497`–`DEC-500`, `ECART-027` clos, **`QO-116` ouverte** |
| `T2` | Entités, paramètres et domaines e-mail | `MVP-L02-US001` | **Terminée** le 19/08/2026. **Les 4 premières tables du projet**, migration `0003` éprouvée en montée, descente et remontée. Règle « `code` immuable après activation » portée par **déclencheur** — 26 tests, chaque refus avec son témoin. `alembic check` sans écart. `DEC-501`, `DEC-502`, `ECART-028` clos |
| `T3` | La table `person` | `MVP-L02-US002` | **Terminée** le 19/08/2026. Identité **globale**, `ARB-DATA-001` : aucun `entity_id`. **`ECART-029` clos** — l'index du §25.1 ne satisfaisait pas l'unicité insensible à la casse du §6.1. Anonymisation **terminale** par déclencheur. **Aucune table d'authentification**, vérifié par contrôle. 19 tests. `DEC-503`, `DEC-504` |
| `T4` | `entity_membership` | `MVP-L02-US002` | **Terminée** le 19/08/2026. **La règle centrale de `US002`** : une seule appartenance occupante par personne. **Deux** contraintes complémentaires, et deux tests montrent chacun ce que l'autre ne verrait pas. Verrou optimiste câblé. **`ECART-030` clos**, **`DEC-507`** pose le nommage des exclusions. 24 tests. `DEC-505`–`DEC-507` |
| `T5` | Métiers et statuts professionnels | `MVP-L02-US003` | **Terminée** le 19/08/2026. **Clés étrangères COMPOSITES** du §25.3 : un métier d'une autre entité est refusé **par la base**. Deux index que j'avais ajoutés sont **retirés** — la mesure a montré qu'ils ne pouvaient jamais se déclencher. **`ECART-012` instruit**, il attend Léa. **`DEC-509`** pose la doctrine de nommage après deux collisions. 23 tests. `DEC-508`, `DEC-509` |
| `T6` | Clients, activations locales et alias | `MVP-L02-US003` | **Terminée** le 19/08/2026. **La dette de `T5` est acquittée** : clé étrangère de `client_id`. Normalisation **volontairement minimale** — `DATA-005` interdit tout rapprochement automatique. **`QO-117` ouverte** : le modèle ne pose aucune unicité sur les alias, et la portée est un choix métier. 21 tests, dont deux sur des **non-actions**. `DEC-510` |
| `T7` | Cercles, bureaux et appartenance aux cercles | `MVP-L02-US001`, `US003` | **Terminée** le 19/08/2026, et elle **clôt les deux stories**. **L'exclusion est PARTIELLE** — une exclusion sans `WHERE` aurait interdit les cercles secondaires multiples, et le livrable aurait **paru correct**. Un **résiduel du §8.1 est nommé, non comblé**. 17 tests. `DEC-511` |
| `T8` | DSM, responsabilités Framework et rôles techniques | `MVP-L02-US004` | **Terminée** le 19/08/2026. **Un défaut qui valait trois types sur quatre** : une clé d'exclusion contenant une colonne **nullable** ne contraint rien sur les lignes où elle est nulle. Deux **permissions** distinguées de deux interdictions voisines. **`ECART-031` ouvert** — le §8.4 exige un état de publication que `office` ne déclare pas. 19 tests. `DEC-512` |
| `T9` | Historisation et contraintes temporelles | `MVP-L02-US004` | **Terminée** le 19/08/2026. **Aucune table créée** : les 7 relations existaient. Elle pose le contrôle qui les **compte**, avec l'attendu **dérivé du §25.2** — et **il a trouvé un défaut le jour même**. **`alembic check` est AVEUGLE aux exclusions**, mesuré : 10 déclarées, 9 en base, code 0. 8 tests. `DEC-513` |
| `T10` | Contraintes de rôles et de périmètres | `MVP-L02-US005` | **Terminée** le 19/08/2026. **Deux des trois critères étaient DÉJÀ ACQUIS en `T8`** — vérifiés, non réimplémentés. **`ECART-032` ouvert** : le backlog interdit plus large que le cahier, la matrice **et** le modèle, qui restreignent tous au seul **Booster**. « DG implique DSM » appliqué comme **implication** — un déclencheur ne connaît pas l'attributeur et **inventerait une trace d'audit fausse**. Un **ombrage** de clé étrangère par un déclencheur `BEFORE` a inversé un test de `T6`. 11 tests, dont un sur une **non-action**. `DEC-514` |
| `T11` | Isolation inter-entités | `MVP-L02-US006` | **Terminée** le 20/08/2026. **Aucune migration** : les 8 clés composites du §25.3 fermaient déjà tous les chemins locaux. **Ma première mesure ne prouvait rien** — une référence sans clé étrangère aurait donné la même observation ; le contrôle examine les **colonnes**, pas les contraintes. `MATCH SIMPLE` rend une clé composite **inerte** sur une colonne nulle : `T8-1` transposé. **Dépôts cloisonnés** dont les deux types ne peuvent se confondre, et le service qui referme `DEC-514`. 34 tests, témoin en CI. `DEC-515` |
| `T12` | Factories, jeu de test et recette du modèle | `MVP-L02-US007`, `US008` | **Terminée** le 20/08/2026. **Trois contrôles qui prouvent ce que onze sous-étapes avaient fait à la main** : `migrations-check` compare le schéma d'une base **neuve** à celui qui tourne — 269 colonnes, 94 contraintes, 85 index, 8 déclencheurs **identiques** ; `recette-modele-check` **lit les 25 contrôles du §30** et exige leur classement, avec le test nommé dont l'existence est vérifiée ; l'absence de SQLite est cherchée comme un **usage**, jamais comme le mot. Jeu de **27 936 lignes**, toutes requêtes **sous 1,3 ms**. **373 tests**. `DEC-516`, [checklist `G2`](operations/checklist-validation-G2.md) |

---
