# Compte rendu — `T11` du LOT 7 : l'archivage automatique du parcours terminé et la révocation au départ

**Date :** 28 septembre 2026
**Sous-étape :** `T11` — archivage automatique + révocation au départ
**Décision :** `DEC-611`
**Story :** aucune story dédiée — ferme `§30.13` et `ECART-066` (volet parcours)

---

# 1. État du lot

`T1` à `T11` du LOT 7 sont désormais faites. Quatre sous-étapes restent — `T12` (suivi par
périmètre), `T13`/`T14` (écrans), `T15` (recette, §30, checklist `G7`) — `T12` est la prochaine.
Détail du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

**Aucune des huit stories du lot n'est fermée par `T11`.** Contrairement aux sous-étapes
précédentes, la ligne « Stories » du découpage (`fiche-lot-7.md` §3) ne nomme aucun `US00x` pour
`T11` — mesuré sur les huit issues GitHub (`#176` à `#183`) : `US008` (« Suivre les onboardings
dans son périmètre ») est `T12`, et aucune autre n'attend `T11`. `T11` ferme le critère de sortie 5
et `§30.13`, pas une story. **Aucune issue à fermer à la main pour cette sous-étape.**

---

# 2. Ce que la sous-étape a produit

**Aucune nouvelle table, aucune nouvelle colonne, aucune migration.** Le modèle §13.5 déclarait
déjà les quatre valeurs de `state` (`active`, `completed`, `archived`, `replaced`) sur
`onboarding_instance` depuis `T1` — `archived` n'avait simplement jamais été écrit avant cette
sous-étape.

Matrice §8.1, ligne « Archiver un parcours terminé » : `NEW` = Automatique,
`ESM`/`ADM-E`/`SUPER` = Entité/Entité/Global. **Deux mécanismes distincts, pas un seul**, parce que
la ligne accorde à la fois un comportement automatique ET un droit réel aux trois rôles d'entité —
et parce que « le départ d'un collaborateur archive le parcours » (§8.2) est un second déclencheur,
sans rapport avec la complétion des tâches.

## 2.1 Deux déclencheurs automatiques, aucune route propre — sous-effets d'actions déjà gardées

`archiver_le_parcours_si_termine` (`app/onboarding/instances.py`), appelée par
`taches.terminer_une_tache` après CHAQUE complétion, vérifie si toutes les tâches obligatoires de
l'instance sont désormais `completed` et, si oui, transitionne `active -> archived` en posant
`completed_at`. Elle ne fait RIEN, silencieusement, sinon — ce n'est jamais un échec de la
complétion elle-même. Aucune garde propre : le geste qui la déclenche, « Marquer une tâche comme
terminée », est déjà gardé par `Soi` seul (`T8`).

`archiver_le_parcours_au_depart`, appelée par `app.people.archivage.archiver_un_profil` (LOT 5,
`T8`) **au départ** (`Active -> Departed`, LOT 3 `T9`) — jamais à l'archivage fonctionnel ultérieur
de l'appartenance — transitionne de même `active -> archived`, mais **`completed_at` n'est jamais
posé** : un parcours interrompu par un départ n'a pas été achevé. Elle s'accroche à
`enregistrer_un_depart` **sans le dupliquer** (§7.27) : c'est `archiver_un_profil`, déjà gardée par
sa propre route (LOT 5), qui l'appelle, dans la MÊME branche que la revocation des sessions —
même raison que la revocation elle-même est ancrée au départ et non à l'archivage fonctionnel
(§7.4) : entre le départ et l'archivage, une fenêtre existerait sinon.

Le résultat est **rapporté, jamais tu** : `Archivage.parcours_onboarding_archive` (nouveau champ)
porte l'identifiant du parcours archivé, ou `None` si aucun n'était actif — visible dans la réponse
de `POST .../people/{appartenance}/archivage` (LOT 5).

## 2.2 `EtatInstance.COMPLETED` reste déclaré mais jamais produit, et c'est vérifié

Le modèle §13.5 liste `completed` comme une des quatre valeurs possibles de `state`. Aucune section
du corpus ne décrit pourtant de transition qui y mène : le cahier dit partout « un parcours
terminé est **archivé** » (règle métier §8.2, critères de sortie `US007`/`US008`), jamais
« … est **complété** ». La transition automatique va donc directement `active -> archived`, sans
jamais écrire `completed` — même classe que « `Completed -> Preserved` » pour les tâches (`T10`,
§2.3 de son compte rendu) : une valeur du modèle qui ne correspond à AUCUN état réellement écrit.
Documenté explicitement dans le docstring de `lire_l_instance_active`, pas laissé à deviner.

## 2.3 Deux gestes manuels, avec route propre — confirmés par Jonathan, en plus de l'automatique

La matrice accorde à `ESM`/`ADM-E`/`SUPER` un droit réel (pas un tiret) sur « Archiver un parcours
terminé », en plus de la colonne `NEW` = Automatique. Question posée à Jonathan en clair : fallait-il
construire un geste manuel en plus de l'automatique, ou l'automatique seul suffisait-il ? **Réponse :
ajouter le geste manuel**, comme filet pour le résiduel que l'automatique ne couvrirait pas —
`POST .../onboarding-parcours/archivage`.

En pratique, l'automatique ayant déjà agi dès la dernière complétion, cette route ne trouve
normalement rien à archiver dans le cas courant : le témoin positif (`test_esm_archive_
manuellement_un_parcours_termine_que_l_automatique_n_a_pas_couvert`) construit donc délibérément le
cas résiduel — toutes les tâches obligatoires marquées `completed` **directement en base**, sans
jamais passer par `terminer_une_tache`, pour prouver que le filet fonctionne vraiment et pas
seulement qu'il ne casse rien.

« Restaurer un parcours archivé » (§8.1) reçoit sa propre route,
`POST .../onboarding-parcours/{instance}/restauration` — `{instance}` explicite dans le chemin,
parce que plusieurs instances archivées ou remplacées peuvent exister historiquement pour la même
appartenance (chaque changement de statut, `T10`, en crée une nouvelle), et seul l'appelant sait
laquelle restaurer.

## 2.4 `ECART-066` (volet parcours) résolu — reposé explicitement, jamais présumé

`T6` avait résolu le volet « version de modèle » : l'ESM restaure librement dans son entité,
`DEC-605`. L'écart lui-même distinguait un parcours (objet nominatif et temporaire) d'une version
de modèle (objet structurant) — présumer la même réponse aurait été l'erreur exacte que l'écart met
en garde contre. La question a donc été reposée à Jonathan, en clair, spécifiquement pour le
parcours : **même réponse, l'ESM restaure librement dans son entité**, même régime que les cinq
ressources d'`ARB-DROIT-003`.

`perimetre.ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS` gouverne les deux gestes manuels — alias
de `_ROLES_ENTITE`, mêmes trois rôles que la grille de réouverture (`T9`) : `DSM`/`BOOST` EXCLUS EN
BLOC, aucun sous-cas « son propre consultant/cercle » comme sur l'affectation (`T7`). Aucune fonction
`peut_...` séparée n'est nécessaire — une instance d'onboarding vit toujours dans une entité, jamais
au niveau global, même parti que la réouverture.

Restaurer **ne rouvre aucune tâche** : les tâches `completed`/`cancelled` de l'instance restent
telles quelles — restaurer un parcours n'est pas restaurer une personne (`restaurer_un_profil`, LOT
5), et rien dans le corpus n'exige de rouvrir quoi que ce soit ici. `completed_at` est en revanche
DÉSAPPOSÉ à la restauration : une instance de nouveau `active` ne doit pas porter la marque d'un
archivage passé — même motif que `departure_date` dans `restaurer_un_profil`.

## 2.5 Un défaut trouvé et corrigé avant la fusion, dans mes propres tests

**Après avoir branché l'archivage automatique dans `terminer_une_tache`, 13 tests DÉJÀ FUSIONNÉS de
`T8` et `T9` sont tombés.** Compléter la DERNIÈRE tâche obligatoire archive l'instance dans le MÊME
geste — et `_resoudre_l_instance_active_ou_404` (filtrée sur `state='active'`, en usage depuis `T8`)
ne retrouvait alors plus le parcours pour l'annulation dans les cinq minutes (`T8`, `DEC-608`) ni
pour la réouverture administrative (`T9`, `DEC-609`). La fenêtre de cinq minutes aurait donc été
**fermée** pour exactement la tâche qui termine le parcours — une dégradation d'une exigence déjà
livrée, ce que la règle n°7 du §2 de `CLAUDE.md` interdit sans décision explicite et tracée.

Diagnostiqué en relançant la suite complète (`T8`+`T9`+`T10`+`T11`) avant de conclure quoi que ce
soit, jamais en supposant le défaut isolé aux nouveaux tests. Corrigé en distinguant **deux**
résolutions d'instance plutôt qu'en relâchant la précondition d'archivage automatique :

- `lire_l_instance_active` (stricte, `state='active'`) — réservée à l'affectation (`T7`) et à
  l'archivage MANUEL (`T11`, §2.3) ;
- `lire_l_instance_actionnable` (NOUVELLE, `T11`) — `active` OU `archived`, **jamais** `replaced` —
  employée par les trois routes de tâches (`terminer_une_tache`/`annuler_la_completion`/
  `reouvrir_une_tache`, `T8`/`T9`). Une instance `replaced` (`T10`) reste VRAIMENT supplantée, ses
  tâches frigées pour toujours ; une instance `archived` par complétion automatique reste, elle, LE
  MÊME parcours — son annulation et sa réouverture administrative doivent continuer d'agir, sans
  jamais réactiver l'instance elle-même (seule `restaurer_un_parcours`, geste EXPLICITE, le fait).

Les 13 tests de `T8`/`T9` repassent tous au vert avec ce correctif, sans qu'aucune de leurs
assertions n'ait dû changer.

## 2.6 Contrat mis à jour

`packages/contracts/src/contrat-api.json` déclare les deux nouvelles routes
(`archivageManuelDUnParcours`, `restaurationDUnParcours`), forme `InstanceDeParcours` — déjà
validée comme partie de `parcoursOnboarding.ts` (`T7`), aucun nouveau module de contrat. Sans cette
mise à jour, `test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste` (LOT 1, `T10`) aurait
échoué : mesuré, c'est exactement ce qui s'est produit avant la correction.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur, dépôt entier |
| `uv run mypy` | 0 erreur, 174 fichiers Python |
| `uv run pytest apps/api/tests/test_archivage_onboarding.py -q` | **16 tests, tous verts** |
| `uv run pytest -m integration -q` (onboarding + archivage LOT 5) | **108 tests, tous verts** — `test_archivage_onboarding.py`, `test_taches_onboarding.py`, `test_reouverture_onboarding.py`, `test_instances_onboarding.py`, `test_remplacement_onboarding.py`, `test_archivage.py` |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux |
| `make sources-check` / `make icloud-verify` / `make parametres-check` | OK |
| `pnpm run typecheck` / `pnpm run lint` / `pnpm run format:check` | OK, `packages/contracts` inclus |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base, avec la commande EXACTE de
`make check`.** Un `git worktree` sur `origin/develop` (`b1a3097`, tête après fusion de `T10`),
`.env` copié, `uv sync --frozen`. **`pytest` bare, sans filtre `-m integration`** — la commande que
`make test`/`make check` invoquent réellement, pas seulement le sous-ensemble intégration — a rendu
**75 échecs environnementaux** des deux côtés (base de développement polluée par le jeu de
démonstration, §11 de `CLAUDE.md`), et la comparaison des deux listes triées de noms de tests en
échec est **vide dans les deux sens** : aucune régression, aucun défaut masqué par le bruit
environnemental.

**Un écart d'un test entre les deux méthodes de comparaison a été mesuré, pas ignoré.** La première
comparaison, restreinte à `-m integration`, rendait 75 des deux côtés — identique. La seconde,
`pytest` bare comme `make check` l'exécute réellement, en rendait 76 sur la branche `T11` contre 75
sur `develop` : `test_contrat.py::test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste`
(non marqué `integration`, donc invisible du premier filtre) venait de détecter le contrat non mis
à jour (§2.6). Corrigé, la seconde comparaison redevient identique des deux côtés.

`uv run pytest -q --collect-only` : **1 393** tests (1 377 → 1 393, +16) ; `-m integration` :
**1 014** (998 → 1 014, +16). `make test-frontend` : inchangé, **282 + 111 + 225 = 618** — deux
routes nouvelles, aucun écran, aucun module de contrat propre au-delà d'une entrée de manifeste.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-611` | `T11` livrée : archivage automatique du parcours terminé (deux déclencheurs sans route propre) et deux gestes manuels avec route propre (`ESM`/`ADM-E`/`SUPER`). `ECART-066` (volet parcours) résolu. Défaut de régression sur les fenêtres de `T8`/`T9` trouvé et corrigé avant fusion, en distinguant `lire_l_instance_active` de `lire_l_instance_actionnable` |

**`ECART-066` est désormais CLOS** dans ses deux volets (version de modèle, `T6` ; parcours, `T11`).
Aucun écart nouveau, aucune question nouvelle.

**Une erreur de process a été commise et corrigée avant toute fusion.** Ce travail a d'abord été
écrit sur la branche non fusionnée de `T10` (`feature/lot7-t10-changement-mission-intercontrat`),
en violation de la règle « une sous-étape part toujours de `develop`, jamais empilée » (§2, règle
n°1 de `CLAUDE.md`). Signalé à Jonathan dès la découverte ; il a validé la fusion de `T10` (PR
`#195`, squash sur `develop`), l'issue `#182` a été fermée à la main avec ses critères d'acceptation
cochés, puis ce travail a été mis de côté (`git stash`) et repris sur une branche neuve
(`feature/lot7-t11-archivage-et-depart`) depuis `develop` à jour.

---

# 5. Ce que `T11` laisse

- `T12` — suivi par périmètre (DSM/ESM/Booster/ADM-E/SUPER, `US008`) — est la prochaine. « Reporting
  de base » SEULEMENT (cahier, Inclus) : aucun graphique, aucun export, ce serait le LOT 10.
- Les quatre valeurs de `EtatInstance` sont désormais toutes exercées par au moins une route :
  `active` (`T7`), `replaced` (`T10`), `archived` (`T11`) — sauf `completed`, jamais produit et
  documenté comme tel (§2.2). Une future sous-étape qui aurait besoin d'un état intermédiaire
  observable « tâches complètes, pas encore archivé » devra soit l'inventer avec une décision
  explicite, soit constater qu'`archived` avec `completed_at` posé suffit déjà à le distinguer.
- `outbox_message`/`async_job` restent des tables sans écrivain, toujours réservées au LOT 11 (le
  lot, sans rapport avec cette sous-étape `T11`) — non touché ici, aucune progression n'étant
  stockée pour un worker à recalculer.

---

# Validation demandée à Jonathan

Merci de valider `T11` pour fusion. Commande de fusion et de retour arrière ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
