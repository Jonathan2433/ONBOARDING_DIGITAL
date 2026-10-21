# Compte rendu — `T11` du LOT 10 : le bouton « Reporter un bug » et le signalement

**Sous-étape :** la onzième du lot — signalement de bug, pied de page/pages d'erreur/menu mobile
**Date :** 21 octobre 2026
**Décision :** `DEC-665`
**Story :** `MVP-L10-US005`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, `T9`, `T10`, **`T11`** |
| Restent | `T12` à `T16` |
| Issues | épic `#267`, story `#272` |

---

# 2. Ce que le corpus décidait déjà, et ce qui restait à faire

**Qui peut signaler : résolu par comparaison de sources, aucun arbitrage nécessaire.** La matrice
§17 « Alertes, supervision et support » n'a que six colonnes (`DSM`/`ESM`/`BOOST`/`OFFICE`/`ADM-E`/
`SUPER`) et donne un `✓` sans exception sur la ligne « Reporter un bug » — la SEULE ligne du lot
sans aucun tiret. Elle n'énumère ni `EMP` ni `NEW` en colonne, ce qui pourrait suggérer un refus
par défaut (§2 de la matrice). Trois faits concordants écartent cette lecture :

1. le backlog nomme l'acteur de la story `Utilisateur` — jamais un rôle précis, contrairement à
   `US004` qui cite `ADM-E`/`SUPER` littéralement ;
2. le cahier §10.12 place le bouton au pied de page, sur les pages d'erreur et dans le menu
   mobile — des emplacements qu'`EMP` et `NEW` voient autant que les six rôles élargis, et un
   bouton qu'une partie des rôles qui le voient ne pourrait jamais actionner serait l'avertissement
   faux du §7.21 de la passation ;
3. même motif exact que `GET /entities/{code}/accueil` (LOT 8, `T8`) : « aucune garde de rôle
   au-delà d'une session établie ». Là, la matrice donnait « Lecture » aux huit rôles ; ici, « Reporter
   un bug » n'a simplement pas de colonne où `EMP` pourrait être refusé.

La garde retenue est donc `exiger_une_session`, jamais `exiger_un_role_dans_l_entite`.

**Quelle entité attacher à un signalement sans contexte : résolu par réutilisation, aucune règle
inventée.** Toutes les autres routes d'écriture du lot sont `/entities/{code}/...`. Le signalement
n'a pas cette désignation partout où le cahier le place : le pied de page et le menu mobile vivent
à l'intérieur d'une entité consultée, mais les pages d'erreur — démonstration citée au §9.6,
« création d'un signalement depuis une page d'erreur » — n'en portent structurellement AUCUNE : un
visiteur qui atteint le fourre-tout 404 n'a pas nécessairement navigué depuis une entité. Plutôt que
deux mécanismes ou une règle inventée sur quelle entité choisir dans ce cas, la route résout
TOUJOURS l'entité PRINCIPALE du rapporteur, via `app.permissions.services.entite_principale` (LOT 4,
déjà posée et prouvée) — la seule notion d'« entité de cette personne » qui existe déjà dans ce
dépôt, cohérente avec « Entité consultée » du modèle §21.4 dans le cas le plus fréquent.

**Limite documentée, non résolue davantage faute de décision du corpus** : un rôle qui consulte une
entité étrangère et y rencontre un bug le verra attaché à SA entité principale, jamais à l'entité
étrangère consultée. Aucun document ne nomme ce cas ; l'inventer serait trancher une question que
personne n'a posée (§6.5).

**Les quatre champs « ajoutés automatiquement » du cahier §10.12, et leur source exacte.** Le
modèle §21.4 marque `application_version`, `environment` et `browser_summary` comme automatiques.
Lus depuis ce que le SERVEUR sait déjà sur lui-même (`Parametres.APP_VERSION`/`APP_ENV`, posés
depuis le LOT 1) et sur la requête (l'en-tête `User-Agent`, minimisé à 200 caractères) — jamais
depuis une valeur que le client soumettrait, ce qui ne serait pas « automatique » mais une donnée
qu'on ferait croire l'être. Seul `page_path` reste fourni par l'appelant : la route du frontend
affichée au clic, que l'API ne peut structurellement pas connaître.

**`correlation_token` : la colonne est nullable au schéma, le service la remplit quand même.** Le
critère de sortie 5 du lot (« l'identifiant de corrélation relie interface, API et logs ») ne
distingue pas `audit_event` de `bug_report`. Le service reprend donc le même repli
qu'`enregistrer_un_evenement` (`correlation_courante() ou engendrer()`), sans jamais laisser la
colonne vide en pratique — « nullable au schéma » n'est pas « optionnel au service ».

**Aucun second `audit_event` pour cette écriture.** `T2` à `T7` ont câblé l'audit sur des actions
qui modifient des données métier protégées ; déposer un signalement n'en modifie aucune, et c'est
sa propre trace (qui, quand, depuis quelle page, avec quelle corrélation) — même raisonnement que
celui qui épargne `audit_event` lui-même d'un méta-événement pour sa propre écriture.

**Aucun arbitrage de Jonathan n'a été nécessaire.**

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/support/` — nouveau module

- `signalement.py` : `creer_un_signalement` (INSERT `bug_report`, RETURNING id/state/created_at),
  `_resumer_le_navigateur` (minimise l'en-tête `User-Agent`).
- `routes.py` : `POST /bug-reports`, gardée par `exiger_une_session` seule, protégée par les deux
  barrières CSRF (`proteger_du_csrf`, `DEC-531`), entité résolue via `entite_principale`.

## 3.2 Frontend — un composant partagé, trois placements

- `packages/contracts/src/signalement.ts` : le chemin (constante, sans code d'entité), les codes
  exploitables, les types de la demande/réponse, le validateur.
- `apps/web/src/api/signalement.ts` : le client, CSRF via `lireLaSession`, aucune clé
  d'idempotence (non consommée côté API, contrairement à `gestionDesLiens.ts`).
- `apps/web/src/pages/BoutonSignalerUnBug.tsx` : `<details>` natif, formulaire (description
  requise, étapes de reproduction facultatives), `chemin_de_page` depuis
  `window.location.pathname`, message distinct sur un 401 (§7.21).
- Wiring : le pied de page de `CadreApplicatif` (son `Squelette` partagé par les six états du
  cadre), les trois pages d'erreur de `PagesErreur.tsx`, le panneau « Plus » de `BarreMobile.tsx`
  (désormais toujours présent, plus jamais vide).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `pytest` racine | 1 850 collectés (+13 : 10 d'intégration, 3 unitaires), 1 773 passés / 77 échecs |
| Comparaison de worktree avec `origin/develop` | 77 échecs environnementaux **identiques**, `diff` vide |
| `uv run mypy` (racine) | vert, 267 fichiers (+3) |
| `uv run ruff check`/`format` | vert, dépôt entier |
| `pnpm -r exec tsc --noEmit` | vert |
| `pnpm exec eslint .` / `prettier --check .` | verts, dépôt entier |
| Vitest | 812 au total (+10 : 385 `contracts`, 120 `ui`, 307 `web`) |
| `make isolation-check` | 37 tables locales, 29 clés composites, 0 référence nue — aucune migration |
| `make migrations-check` | schéma identique, tête `0027` inchangée |
| `make parametres-check` | aucun paramètre lié partagé entre deux types |
| `make docs-check` / `sources-check` | verts |
| `test_contrat.py` | 5/5, manifeste étendu à 92 chemins (`signalerUnBug`) |

**Un défaut trouvé et corrigé en construisant la route, confirmant un piège déjà documenté dans ce
dépôt** : `appelant: Annotated[SessionEtablie, Depends(exiger_une_session(parametres))]` n'était
pas résolu par FastAPI — le module porte `from __future__ import annotations`, et FastAPI résout
l'annotation dans les globals du module, où la fermeture `parametres` n'existe pas (exactement le
piège documenté dans `app/content/routes.py` depuis le LOT 4 `T1`). La route traitait alors
`appelant` comme un paramètre de requête (`query.appelant: Field required`), et les 12 premiers
tests écrits échouaient tous en 422. Corrigé en `Depends()` en valeur par défaut, la forme déjà en
usage partout ailleurs dans ce dépôt.

**Aller-retour réel effectué** (§7.43 de la passation), après `make code-refresh` : un lien
magique réel consommé dans le navigateur (`t8l10f97bb11cab-esm-b0062b@exalt-company.com`, un
résidu de test `@exalt-company.com` du LOT 8 `T10` trouvé dans la base de développement, les
adresses `@exemple.test` du jeu de démo n'étant pas sur le domaine autorisé). Un signalement
envoyé depuis le pied de page (`/entites/t8l10f97bb11cab-home`) et un second depuis la page 404
(`/n-importe-quoi-de-faux`, sans entité dans l'adresse) — les deux lignes `bug_report` vérifiées en
base : `page_path` reflète exactement la route affichée, `application_version`/`environment`
reflètent la configuration serveur, `browser_summary` capture le `User-Agent` réel,
`correlation_token` rempli, `entity_id` résolu à l'entité principale du rapporteur dans les DEUX
cas. Vérifié aussi en largeur mobile (375 px) : le panneau « Plus » du menu mobile contient
« Reporter un bug », et les cinq cellules de la barre (quatre rubriques + Plus) ne dépassent pas le
seuil de rupture à deux lignes déjà mesuré par `T5` du LOT 4 — aucune régression visuelle. Décor
nettoyé après coup (`DELETE FROM bug_report WHERE description LIKE 'Verification reelle T11%'`).

---

# 5. Décisions et écarts

`DEC-665` consigne cette sous-étape. Aucun écart ouvert ni fermé, aucune question ouverte créée.

---

# 6. Ce que `T11` laisse

- **Le traitement des signalements** (états, commentaires, historique) reste `T12` — `US006`,
  `QO-092` (destination des signalements) à trancher à ce moment.
- **Les alertes opérationnelles** restent `T13`.

---

**Validation demandée à Jonathan.**

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
