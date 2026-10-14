# Checklist de validation — porte `G9`

**Lot :** LOT 9 — Back-office, administration et import CSV
**Préparée le :** 13 octobre 2026, à la sortie de `T16`
**Destinataire :** Jonathan — il coordonne la validation technique et l'exploitation
**Décision de franchissement :** **franchie, `DEC-652`, validée le 14/10/2026**

---

**Comment lire ce document.** Les chiffres sont accompagnés de la commande qui les produit. Les
contrôles techniques sont exécutés ; la validation nominative du corpus, et les gestes qui exigent
des données réelles, restent des actes humains — ils ne sont jamais présentés comme accomplis par
la CI.

## 1. Les huit critères de sortie — fiche LOT 9 §1.2

| # | Critère | État | Preuve ou geste restant |
|---|---|---|---|
| 1 | Le CSV réel n'est ni dans Git ni dans une image | **Tenu** | Structurel depuis le LOT 0 : `.gitignore` exclut `*.csv` (seule exception, le jeu fictif) ; `make sources-check` n'examine pas cette extension ; les motifs génériques de `make icloud-verify` couvriraient une copie de conflit. Témoin direct exécuté à `T16` : un CSV à la racine est immédiatement ignoré par `git check-ignore`, absent de `git status --short` |
| 2 | Les données réelles ne sont chargées qu'après vérification FileVault et sauvegarde | **Geste procédural, à exercer au moment d'un import réel** | Non éprouvable techniquement avant une production réelle (`exploitation-locale.md` §4 : « la sauvegarde et la restauration, aucune procédure n'existe, LOT 13 »). Avant tout chargement d'un CSV réel : confirmer FileVault actif sur la machine, et qu'une sauvegarde récente existe |
| 3 | Le rapport correspond à l'empreinte du fichier | **Tenu** | `T10` : `import_batch.source_checksum_sha256` confronté au rapport |
| 4 | Les règles d'intégrité de la reprise réussissent | **Tenu** | Critères de qualité du cahier §12.6, témoins à `T9`/`T10` |
| 5 | Aucune ligne rejetée n'est masquée | **Tenu** | `T10` : rapport exhaustif (créations/mises à jour/avertissements/rejets), total réconcilié par `GROUP BY` sur `import_row.state`, jamais un cache |
| 6 | L'isolation multi-entités est testée pendant l'import | **Tenu** | `T15` : `make back-office-check`, témoin dédié — les trois routes scopées par lot refusent systématiquement `404` depuis une autre entité, y compris quand la même requête rendrait `409` depuis la bonne, et jusque sur une ligne qui rend `409`/`404` avec les mêmes identifiants selon l'entité appelante seule |
| 7 | Léa et Jonathan valident le rapport de répétition en recette | **Démonstration à organiser** | Aucun canal de recueil n'est nommé par le corpus pour Léa — même résidu que Tess/Diane à `G7` et `G8`. Signalé ici plutôt qu'inventé |
| 8 | Jonathan valide le lot | **En attente** | Cette checklist, section 7 |

**Sur le critère 1 :** aucun code n'a été ajouté à `T16` pour le tenir — c'est un résultat déguisé
en absence (même parti que le §2.5 du LOT 6) : le mécanisme existait depuis le LOT 0, et personne
n'avait mesuré qu'il couvrait ce cas précis avant `T16`. Le marquer « Tenu » sans la mesure aurait
été une affirmation ; la mesure est faite et citée ci-dessus.

**Sur les critères 2 et 7 :** aucun des deux n'est marqué « Tenu » par un code ou un contrôle, parce
qu'aucun des deux ne PEUT l'être sans donnée réelle ni production — le critère 2 l'énonce lui-même
(« les données réelles ne sont chargées qu'après... ») et le critère 7 nomme une validation humaine.
Les marquer « Tenu » serait inventer une preuve ; les marquer « Non tenu » laisserait croire à un
défaut du développement. Ce sont des gestes qui restent à ta main, documentés plutôt que simulés.

## 2. Contrôles exécutés

| Contrôle | Résultat relevé le 13/10/2026 |
|---|---|
| `make recette-check` | 57 contrôles, 0 échec ; 7/7 séparations effectives |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé répondent, révision `5f30443` |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec ; artefact bâti servi par Caddy en HTTPS |
| `make back-office-check ENVIRONNEMENT=recette` | 16 contrôles, 0 échec — asymétrie de rôles, isolation multi-entités pendant l'import |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec (témoin transversal du LOT 7, rejoué sur la même recette) |
| `make accueil-check ENVIRONNEMENT=recette` | 29 contrôles, 0 échec (témoin transversal du LOT 8, rejoué sur la même recette) |
| `make recette-modele-check` | 25 contrôles classés : **18 acquis, 2 partiel, 5 reportés, 0 inapplicable** — `§30.17`/`§30.18` reclassés par `T16` |
| `pytest` depuis la racine | 1 708 collectés ; 74 échecs environnementaux, **identiques un par un** à `origin/develop` (comparaison de worktree) |
| `make test-frontend` | 802 Vitest (380 `contracts`, 120 `ui`, 302 `web`), inchangé |
| `make check` (qualité) | Ruff, Prettier, ESLint, `mypy` (238 fichiers) : tous verts |
| `make residu-check` | 74 échecs environnementaux, aucun résidu laissé par le nouveau test |

Les 74 échecs viennent du jeu de démonstration de développement. La comparaison porte sur la
**liste** des identifiants de test en échec, pas seulement leur nombre : elle est identique, un par
un, entre `origin/develop` et la branche de `T16`.

## 3. Démonstration guidée à Jonathan

1. Lire la fiche LOT 9 §1.2 et les huit critères de sortie ci-dessus.
2. Ouvrir la page back-office (`T14`) : les sept groupes en onglets — Organisation, Onboarding,
   Contenu (à venir), Données, Pilotage, Configuration (à venir), Super-administration.
3. Depuis « Données », déposer un petit CSV (fictif, jamais réel), suivre l'aperçu, résoudre une
   décision de rapprochement client si proposée, lancer l'import, lire le rapport, rejouer une
   ligne rejetée si présente.
4. Vérifier qu'un DSM ne voit, sur le tableau de bord (« Pilotage »), que ses propres consultants —
   jamais toute l'entité, contrairement à un ESM dans la même entité.
5. Vérifier qu'un dépôt d'import tenté par un DSM ou un `OFFICE` est refusé, et qu'une création
   d'entité (« Super-administration ») n'est accessible qu'à `SUPER`.
6. Confirmer qu'aucune des deux stories `P1` (`US003`, `US008`) n'a été dégradée par rapport au
   backlog initial, et que `ECART-035` (invitations) reste fermé par constat, sans table inventée.
7. Consigner ton accord (ou tes réserves) sur les critères 1, 3, 4, 5 et 6, prendre connaissance
   des gestes 2 et 7 encore à ta main, et valider le critère 8.

## 4. La recette réellement exécutée

La recette a été épinglée sur les images publiées de la révision `5f30443` (fusion de `T15`), sur
son environnement déjà en place depuis `G8`. Un premier démarrage a rencontré le port `8080` déjà
déclaré par le projet tiers `observatoire-ecom-studio`, même conflit que `T15` du LOT 7 et `T14` du
LOT 8 sur la même machine — son seul conteneur `web` a été arrêté temporairement puis relancé après
la recette. Caddy, créé pendant ce conflit sans ses publications réelles, a été recréé par
`make caddy-recreate ENVIRONNEMENT=recette`.

**La base de recette était restée à la migration `0023`, l'état du LOT 8** : contrairement à `G7`
et `G8`, dont la recette avait été recréée depuis un volume vide, celle-ci portait encore le schéma
d'avant le LOT 9. `make back-office-check ENVIRONNEMENT=recette` l'a révélé en échouant sur
« relation `import_decision` does not exist » — mesuré, pas supposé — avant que
`make migrate ENVIRONNEMENT=recette` ne l'amène à la tête `0026`.

`make back-office-check`, `make onboarding-check` et `make accueil-check` ont ensuite été rejoués
sur la recette, à travers Caddy en HTTPS, sur les conteneurs tournant nativement en `aarch64` sur
l'image **publiée** — jamais une reconstruction locale, vérifié par empreinte. Les trois donnent les
mêmes résultats qu'en développement.

## 5. Contrôles du modèle §30

`make recette-modele-check` relit directement les 25 contrôles du §30 du modèle immuable.
`§30.17` et `§30.18` — les deux seuls contrôles que la fiche nommait explicitement « à vérifier »
pour ce lot — sont désormais **acquis** : le premier par un nouveau test falsifiable
(`test_aucune_ecriture_metier_avant_le_lancement_de_l_import`), le second par un test déjà existant
de `T9` (`test_une_ligne_en_echec_n_empeche_pas_les_autres_d_etre_importees`), jamais reclassé
jusqu'ici. Le résultat passe à **18 acquis, 2 partiel, 5 reportés, 0 inapplicable** — contre
16/2/7/0 depuis `G7`. Les cinq reports restants relèvent des LOTS 10, 11 et 12, hors périmètre de
ce lot.

## 6. Réserves et écarts ouverts

- `ECART-012` (statut professionnel d'une direction générale) reste à décider par Léa et ne bloque
  pas la porte technique.
- `ECART-060` reste ouvert pour ses volets métier/DSM : seul le volet « clients » a été fermé par
  `T8` du LOT 9.
- `ECART-064` (motif d'intervention du super-administrateur) reste ouvert, réservé au LOT 10 avec
  `audit_event` — non anticipé silencieusement dans ce lot.
- `ECART-068` reste ouvert, hérité du LOT 8, non lié à ce lot.
- `QO-096`, `QO-097`, `QO-099`, `QO-100`, `QO-110` restent ouvertes : elles bloquent uniquement le
  chargement de **données réelles**, jamais la construction du pipeline.
- `QO-121` (vocabulaire de `payload_json` par type de bloc) reste ouverte, héritée du LOT 6.
- `QO-125` (filtrage DSM/Booster du rapport d'import) reste ouverte, ouverte par `T10` de ce lot.
- `ROAD-RSK-033` et `ROAD-RSK-034` restent à réévaluer avant le LOT 13, inchangés par ce lot.

Aucun de ces points n'est bloquant pour la porte technique `G9` — tous sont déjà nommés comme tels
par la fiche LOT 9 §2.1 et par la passation.

## 7. Décision de Jonathan

**Ce que tu valides :** les huit critères du LOT 9, en distinguant les cinq preuves techniques
tenues (§1), le geste procédural et la démonstration encore à organiser (critères 2 et 7), de ta
propre confirmation requise par le huitième.

**Ce que la porte clôt :** le LOT 9 ; elle n'ouvre aucun autre lot sans instruction explicite.

| | |
|---|---|
| Date | 14/10/2026 |
| Décision | ☒ franchie ☐ à reprendre |
| Validation de Jonathan | Confirmée explicitement (`AskUserQuestion`, reformulée sans jargon) : « Oui, G9 est franchie » — les critères 2 et 7 restent des gestes à organiser, pas des blocages techniques, et les réserves ci-dessous restent ouvertes sans bloquer le lot. Consignée `DEC-652` |
| Réserves | `ECART-012`, `ECART-060` (métier/DSM), `ECART-064`, `ECART-068`, `QO-096`/`QO-097`/`QO-099`/`QO-100`/`QO-110`/`QO-121`/`QO-125` restent ouvertes, non bloquantes pour `G9` — à reprendre aux lots suivants au besoin |
