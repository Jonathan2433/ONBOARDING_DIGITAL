# Passation — agent chef de projet technique

**Projet :** eXalt Onboarding Digital
**Rédigé le :** 28 juillet 2026, à la sortie de `T4` du LOT 1
**Mis à jour le :** 4 octobre 2026, après `T4` du LOT 8 (`DEC-623`)
**Destinataire :** l'agent qui réalise le **LOT 8 — Événements et accueil dynamique**
**Interlocuteur unique :** Jonathan — technique et exploitation. Léa décide du produit.

Ce document dit **où en est le projet**, **ce qui a été fait et comment**, **les constantes à
connaître**, **les erreurs à ne plus commettre**, et **par où commencer**. Lis-le en entier avant
d'agir.

> **TOUS LES NOMBRES DE CE DOCUMENT ONT ÉTÉ DÉRIVÉS LE 22/09/2026, PAS RECOPIÉS.** C'est la classe
> d'erreur la plus fréquente du projet — `ECART-021`, rejouée une douzaine de fois. Chaque grandeur
> est accompagnée de la commande qui la produit. **Recompte avant de réutiliser.**

---

# 1. En un coup d'œil

| | |
|---|---|
| Lots terminés | **LOT 0** (`G0`, 27/07) · **LOT 1** (`G1`, 12/08, `v0.1.0`) · **LOT 2** (`G2`, 20/08, `v0.2.0`) · **LOT 3** (`G3`, 22/08, `v0.3.0`) · **LOT 4** (`G4`, 24/08, `v0.4.0`) · **LOT 5** (`G5`, 13/09, `v0.5.0`) · **LOT 6** (`G6`, 25/09, `v0.6.0`) · **LOT 7** (`G7`, 30/09, `v0.7.0`, `DEC-617`) |
| **Lot en cours** | **LOT 8 — Événements et accueil dynamique.** Ouvert par Jonathan le 01/10/2026 (`DEC-619`), découpage validé en quatorze sous-étapes. `T1` à `T4` sont faites (`DEC-620` à `DEC-623`) ; `T5` est la suivante. |
| Sous-étapes faites | **LOT 3 : les DOUZE.** **LOT 4 : les DOUZE.** **LOT 5 : les ONZE.** **LOT 6 : les DOUZE — LOT VERROUILLÉ, porte `G6` FRANCHIE le 25/09/2026 (`DEC-597`), tag `v0.6.0` posé sur `d2d639e`.** **LOT 7 : les QUINZE**, de la structure et des parcours aux deux écrans, puis à la recette complète, au classement du §30 (**16 acquis, 2 partiels, 7 reportés**) et à la checklist `G7` (`DEC-615`). |
| **Prochaine action** | **Réaliser `T5` du LOT 8 depuis `develop` : annulation, archivage et restauration d'un événement.** `T4` (`DEC-623`) a livré Modifier/Publier : la grille diverge pour le DSM entre les deux verbes (voir §1 « Tests »/registre). `ECART-068` reste ouvert — l'audit de la modification/publication doit être résolu avant la fermeture de `US004`, et n'anticipe pas silencieusement `audit_event` (LOT 10). |
| Stories `Done` | LOT 0 : 7 · LOT 1 : 8 · LOT 2 : 8 · LOT 3 : **8** · LOT 4 : **7 sur 7** · LOT 5 : **6 sur 8** · LOT 6 : **5 sur 7** · LOT 7 : **8 sur 8**. Les stories `#176` à `#183` sont fermées sur leurs preuves propres et l'épic `#175` est clos à `G7`. Les stories encore ouvertes des LOTS 5 et 6 restent nommées dans leurs fiches : un critère non tenu ne se referme pas. |
| Dépôt distant | `Jonathan2433/ONBOARDING_DIGITAL` — **privé**, prouvé par `gh api … --jq .private` |
| Branche `demo` | **FUSIONNÉE dans `develop` le 19/09/2026, et elle n'existe plus.** Elle portait une **démonstration client** produite par Codex — quatre cibles `make`, le script `infra/scripts/preparer-demo-client.py`, le guide `docs/demo/` et quatre tests statiques — et elle a vécu trois jours à côté de `develop` sans jamais voir la porte : `ci.yml` filtre `branches: [develop, main]`, et **aucun run n'a jamais tourné sur `demo`** — mesuré, `gh run list --branch demo` rendait zéro. **Elle a décroché DEUX fois en deux jours**, à la fusion en squash de `T6` puis de `T7`, chacune remplaçant le commit sur lequel son histoire était posée. C'est structurel et non accidentel : **toute branche qui vit à côté de `develop` décroche à chaque squash**, et la seule issue durable est de la fusionner ou de la supprimer. Arbitrage de Jonathan du 19/09/2026 : **fusionnée**, et ses quatre fichiers sont désormais éprouvés par la porte comme le reste. |
| Branches | `main` et `develop`, **les deux protégées**, CI **bloquante** sur les deux. **`main` n'était PAS un ancêtre de `develop`** avant `G3` — le squash de `G2` avait coupé l'histoire, `ECART-026`. Vérifie l'**arbre**, jamais le verdict de `git merge` |
| Tags | `v0.1.0` (`G1`), `v0.2.0` (`G2`), `v0.3.0` (`G3`), `v0.4.0` (`G4`), `v0.5.0` (`G5`), `v0.6.0` (`G6`), **`v0.7.0` (`G7`)**. À chaque porte depuis `G3`, `develop` reste ancêtre de `main`, les arbres sont identiques et la livraison porte deux parents (`ECART-026`) |
| **Tests** | **2 195** : **1 489 pytest** — dont **1 094 d'intégration** — et **706 Vitest** (**336 `contracts`**, **111 `ui`**, **259 `web`**). Dérivés depuis la racine le 04/10/2026 après `T4` du LOT 8 (`DEC-623`, +20 pytest dont +17 d'intégration). **DÉRIVÉS DEPUIS LA RACINE DU DÉPÔT, PAS DEPUIS `apps/api/`** : `pyproject.toml` déclare `testpaths` sur `apps/api/tests`, `apps/worker/tests` **et** `packages/observabilite/tests`, et c'est depuis la racine que `make check`/`make test` invoquent `pytest` — lancé depuis `apps/api/` seul, le compte diverge, un écart qui n'a rien à voir avec la sous-étape en cours. **Recompte**, ne recopie pas |
| Schéma PostgreSQL | **44 tables métier**, **10 déclencheurs**, **23 migrations**, tête `0023`. `T1` du LOT 8 ajoute les quatre tables événementielles et six clés composites, sans déclencheur ; `T3` ajoute la cinquième, `event_dsm_scope` (`ECART-067`, `DEC-622`), et une clé composite de plus — **25 au total**. `make migrations-check` confronte une base vide au schéma réel et prouve la chaîne complète. **Recompte**, ne recopie pas |
| Comptes PostgreSQL | **TROIS** : `onboarding_app` **[superutilisateur]**, `onboarding_migrations`, `onboarding_runtime`. Voir §5.9 |
| Intégration continue | 3 tâches, les 11 contrôles du cahier §23.1, ~1 min 20 de qualité + ~4 min de stack. **Chaque contrôle de sous-étape y entre** : douze depuis `T1` du LOT 4 |
| Images | 3 images multiarchitecture dans GHCR privé, étiquettes `0.2.0`, `develop`, `sha-*`. **Aucun `latest`** |
| Makefile | **94 cibles** documentées — **89 avant la fusion de `demo`**, qui en apporte quatre : `demo-init`, `demo-check`, `demo-info`, `demo-reset`. **`T3` À `T13` N'EN ONT AJOUTÉ AUCUNE** : `framework-check` est passé de 13 à **21**, puis **29**, **35**, **49**, **61**, **68**, **74**, puis **77** contrôles avec `T11` — servis par la même cible étendue, bénéfice direct du §7.27. **`T14` EN AJOUTE UNE, LA PREMIÈRE DEPUIS `T2`** : `onboarding-check`, le script de pile différé par `T13`, nommé dans `ci.yml` (§7.36 : une cible ajoutée à `make check` n'entre pas dans la CI, il faut l'y nommer). **`ECART-049` : des cibles ne sont PAS dans `.PHONY`** — le compte de l'écart datait de 86 documentées et n'est plus dérivé ; **`make help` fait foi**, et c'est la seule formulation qui ne vieillit pas |
| `.env.example` | **v1.6**, **84 variables**. **Cinq d'entre elles ne sont consommées par personne** — les seuils du §20.2, `ECART-034` — et elles portent l'annotation qui le dit |
| Registres | **206 décisions** `DEC-418+` · **68 écarts** (**13 ouverts**, dont `ECART-068` ouvert au LOT 8 — `ECART-067` est clos par `DEC-622`) · **48 questions** (**34 ouvertes**) · **34 risques** `ROAD-RSK` · **17 dépendances** `DEP` · **29 contenus** `CONT`. `make docs-check` dérive ces nombres depuis les registres et lit aussi ce document ; ne les modifie jamais sans le relancer |
| Défauts consignés | LOT 1 : **71** · LOT 2 : **44** · LOT 3 : **57** · LOT 4 : **19** · LOT 5 : **62** · **LOT 6 : 26**, dérivés le 24/09/2026 par la règle exacte ci-dessous. **Et ce nombre a changé SEPT fois en six sous-étapes** : consigner un défaut change le compte, ce qui est précisément pourquoi il est **dérivé** et jamais recopié — la liste est dans les comptes rendus, pas ici. **ET LA COMMANDE DU §7 SUR-COMPTE, MESURÉ LE 13/09/2026** : elle relève tout marqueur `Tn-m` d'un compte rendu, **y compris ceux d'un autre lot cités comme précédents**. Le compte rendu de `T1` du LOT 6 cite `T4-2` et `T8-3` — deux défauts du **LOT 2** — et la commande rend **4** là où il y en a **2**. La règle exacte : un défaut appartient à la **sous-étape dont le compte rendu le déclare**, donc un marqueur `Tn-m` dans `compte-rendu-tN-lot-L.md` ne compte que si `n == N`. **Les nombres des LOTS 3 et 4 sont affectés de 2 et de 1, et ils ne sont PAS corrigés ici** : la méthode exacte ne distingue pas une citation d'un défaut déclaré tardivement, et réécrire un compte historique sans pouvoir trancher serait pire que de le nommer |

**Les commandes qui produisent ces nombres :**

```bash
git log --oneline -1 && git tag -l
uv run pytest -q --collect-only | tail -1
uv run pytest -m integration -q --collect-only | tail -1
make test-frontend 2>&1 | grep -oE 'Tests  [0-9]+ passed'
grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile
grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example
ls apps/api/alembic/versions/*.py | wc -l
for l in 1 2 3 4 5 6; do grep -ohE '`T[0-9]+-[0-9]+`' docs/operations/compte-rendu-t*-lot-$l.md | sort -u | wc -l; done

# La regle EXACTE -- un marqueur `Tn-m` ne compte que dans `compte-rendu-tN` si n == N.
# La commande ci-dessus SUR-COMPTE : elle releve aussi les defauts d'un AUTRE lot cites
# comme precedents. Celle-ci ne compte que les defauts DECLARES.
# LE HEREDOC N'EST PAS UN ORNEMENT : en `python3 -c "..."`, les accents graves du motif
# sont interpretes par le SHELL -- « Td+-d+: command not found », puis une SyntaxError.
# Mesure du 15/09/2026, defaut `T3-3`. Vois aussi le §7.2 : ici encore, la parade est de
# ne pas faire traverser le shell a ce qu'on veut passer tel quel.
LOT=6 python3 - <<'PY'
import os, pathlib, re
lot, d = os.environ["LOT"], set()
for f in pathlib.Path("docs/operations").glob(f"compte-rendu-t*-lot-{lot}.md"):
    n = re.match(r"compte-rendu-t(\d+)-", f.name).group(1)
    d |= {m for m in re.findall(r"`(T\d+-\d+)`", f.read_text()) if m.split("-")[0] == f"T{n}"}
print(len(d), sorted(d))
PY
```

> **DEUX NOMBRES ONT ÉTÉ RETIRÉS DE CE TABLEAU PLUTÔT QUE CORRIGÉS : le compte de commits et le
> compte de lignes.** Tous deux ont été faux plusieurs fois, pour une raison structurelle — un
> document qui est lui-même commité se décrit dans son état **d'avant son propre commit**, et toute
> correction change le compte qu'il annonce. **Un nombre qu'on ne peut pas tenir, on ne l'affirme
> pas.**
>
> **Et la façon de traiter ces nombres est elle-même une leçon, qui a coûté quatre passes.** `T6` du
> LOT 1 a retiré le compte de commits ; le compte de lignes est devenu faux au commit suivant. `T7` a
> trouvé que le compte de fichiers YAML était faux aussi. Puis, à la clôture de `G2`, le contrôle
> d'hygiène du §11 annonçait « deux fichiers » là où il y en a **trois** depuis `T8` du LOT 1.
> **Une instance corrigée n'est pas la classe corrigée.**

**La plateforme démarre, répond, s'affiche, elle est empaquetée, et elle existe désormais en DEUX
environnements isolés.** `make up` lève les huit services du développement, `make up-recette` lève
les huit de la recette **sur les images publiées**, et les **sept** séparations du cahier §22.2 sont
prouvées sur l'état réel — 57 contrôles, 0 échec. L'API sert ses trois endpoints de santé à travers
Caddy en HTTPS dans les deux, la migration initiale s'applique dans les deux, les journaux sortent en
JSON corrélé, et la page de statut est servie sur `app.onboarding.localhost` et
`app.recette.onboarding.localhost`. Il n'existe **aucun écran métier** ni **aucune donnée métier**.

**Le régime de contribution est contraignant.** `main` et `develop` sont protégées avec
`enforce_admins` : **aucun commit direct**, y compris documentaire, y compris pour Jonathan.
Toute modification passe par une branche et une pull request vers `develop`.

---

# 2. Les règles qui ne se négocient pas

1. **Un lot à la fois.** Seul le lot ouvert par Jonathan peut être réalisé (`ROAD-003`,
   `ARB-BACK-003`, `BACKLOG-006`). **LE LOT 6 EST VERROUILLÉ** — porte `G6` franchie le 25/09/2026
   (`DEC-597`), tag `v0.6.0`. **LE LOT 7 EST VERROUILLÉ** depuis le 30/09/2026 : porte `G7`
   franchie (`DEC-617`), tag `v0.7.0`. **LE LOT 8 EST OUVERT** depuis le 01/10/2026 (`DEC-619`) :
   son découpage compte quatorze sous-étapes, `T1` à `T4` sont faites (`DEC-620` à `DEC-623`) et `T5`
   est la suivante.
   N'écris **rien** qui appartienne au LOT 9 — import CSV — au LOT 10 — audit et pilotage — ni au
   LOT 11 — génération des miniatures, worker et exports.
   Et **une sous-étape à la fois**, partant toujours de `develop`, **jamais empilée**.

   > **CETTE RÈGLE A NOMMÉ LE MAUVAIS LOT PENDANT DEUX SEMAINES**, du 24/08 au 08/09/2026 : elle
   > disait « LE LOT 4 EST OUVERT […] la suivante est `T2` » et **interdisait le LOT 5**, qui était
   > le lot ouvert. Le §1 était juste ; la **règle**, non. Un agent qui applique la première des dix
   > règles refuse donc de faire `T7`. `ECART-054` — et la parade n'est pas cette correction, c'est
   > `make docs-check`, qui **lit désormais ce document**.
2. **Aucun secret dans Git.** Ni fichier, ni message de commit, ni titre de branche, ni
   description de pull request.
3. **Aucune donnée réelle de collaborateur versionnée.** Aucun CSV réel, aucune photo.
4. **Aucune ligne de code du prototype réutilisée.** `docs/prototype/V1.html` est une référence
   d'intention, pas une base de code.
5. **L'API est l'autorité finale** sur les permissions. Jamais le frontend seul.
6. **Aucun contournement de l'authentification**, à aucun moment, même en développement.
7. **Aucune exigence `Must` ni story `P0`** supprimée, fusionnée ou dégradée sans décision
   explicite et tracée.
8. **Toute proposition nouvelle est une recommandation** jusqu'à validation de Jonathan.
9. **Ne repose jamais une question déjà tranchée.** Lis avant de demander.
10. **Ne déclare jamais une sous-étape terminée sans preuve.** Contrôles exécutés, sorties
    réelles montrées, critères vérifiés un par un.

Liste complète : [`README.md`](README.md) §4 et [`CONTRIBUTING.md`](CONTRIBUTING.md) §7.
Interdictions propres au LOT 1 : [`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) §11.

---

# 3. Où est la vérité

| Question | Document |
|---|---|
| Que doit faire le produit ? | `docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` — **prévaut sur tout** |
| Qui a le droit de faire quoi ? | `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` |
| Comment sont structurées les données ? | `docs/architecture/MODELE_DONNEES_EXALT.md` |
| Dans quel ordre construit-on ? | `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` |
| Quelle est l'unité de travail ? | `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` |
| **Que fait-on au LOT 8 ?** | **`docs/operations/fiche-lot-8.md`** — **6** stories, quatre `P0` et deux `P1`, **6** critères de sortie et **QUATORZE** sous-étapes validées le 01/10/2026 (`DEC-619`). `ECART-067` (portée « consultants » du DSM) est **clos** par `DEC-622` — cinquième table `event_dsm_scope` ; `ECART-068` (audit obligatoire alors que `audit_event` appartient au LOT 10) reste ouvert, à résoudre avant la fermeture de `US004`. |
| **Comment a-t-on fait `T1` à `T4` du LOT 8 ?** | **`docs/operations/compte-rendu-t{1,2,3,4}-lot-8.md`** — `T1` pose les quatre tables du §17, migration `0022`, six nouvelles clés composites. `T2` sert `GET …/events`, paginé, avec `ends_at > instant` à venir et `<= instant` passé ; annulé visible, brouillon et archive absents. Tous les rôles authentifiés lisent, y compris hors de leur entité principale. `T3` (`DEC-622`) sert `POST …/events` : chaque rôle porte EXACTEMENT une portée de création — sauf le DSM, qui en porte deux (`Entité` ou `consultants`, `ECART-067` clos par la cinquième table `event_dsm_scope`, migration `0023`) — et le rattachement précis au cercle ou au bureau nommé est revalidé au service, jamais à la seule garde de rôle de la route. **`T4` (`DEC-623`) sert `PUT …/events/{evenement}` et `POST …/publication`** : mêmes portées qu'à la création pour `ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`, mais le DSM porte DEUX grilles distinctes — « Modifier » accepte « créé OU rattaché à son périmètre », « Publier » n'accepte QUE « Périmètre », qui pour ce rôle dénote ses consultants nommés (`event_dsm_scope`), jamais son entité (§7.45, déjà mesuré au LOT 6 pour l'ESM où les deux mots coïncident — ici ils NE coïncident PAS). `cercles`/`bureaux` remplacent la liste complète des rattachements si fournis (rattachements multiples, modèle §17.2) ; chaque code est revalidé INDÉPENDAMMENT du périmètre global déjà vérifié par la route (§23.1). **Défaut trouvé et corrigé dans mes propres tests avant tout commit** : les requêtes d'archivage des portées référençaient `:instant` sans que l'appel ne le fournisse. |
| **Que fait-on au LOT 7 ?** | **`docs/operations/fiche-lot-7.md`** — **8** stories, toutes `P0`, **deux** `XL` (`US003`, `US007`), **7** critères de sortie **dérivés des DEUX sources qui concordent** (roadmap et cahier, texte identique). **QUINZE** sous-étapes validées le 25/09/2026 (`DEC-598`). **Son §2.1 porte deux pièges mesurés** : `DSM`/`BOOST` ont un périmètre de CONSULTATION sur le parcours d'un collaborateur mais sont à **tiret** sur toute ACTION sur une tâche ; `OFFICE` est à tiret partout sur les modèles d'onboarding, troisième occurrence de ce piège en trois lots. **Son §8.3 ouvre `ECART-066`** : la matrice dit `ESM` → « Conditionnel » sur la restauration d'un parcours ou d'une version de modèle, et `ARB-DROIT-003` — qui définit ce mot pour cinq autres ressources — ne nomme ni l'un ni l'autre. **Son §8.1 reconduit `ECART-012`** sans le résoudre — toujours à Léa. **Son §8.4 signale un point non technique** : le critère de sortie 1 (et `docs/README.md` §6) nomme Tess et Diane, deux validatrices dont aucun document ne dit qui elles sont ni comment recueillir leur accord |
| **Comment a-t-on fait les sous-étapes du LOT 7 ?** | **`docs/operations/compte-rendu-t{1,2,3,4,5,6,7,8,9,10,11,12,13,14}-lot-7.md`** — `T1`, les huit tables. **`make isolation-check` a trouvé deux classes de défaut inédites** : une clé composite structurellement correcte mais refusée quand même (le contrôle exige `entity_id` NOT NULL à la source, sans condition) ; et une clé composite dont la table CIBLE a un `entity_id` légitimement nullable, qui aurait refusé silencieusement tout usage GLOBAL — `verifier-isolation.py` reçoit une troisième raison légitime à une clé simple. **Un témoin a trouvé un défaut NULL classique** dans ma propre contrainte : `length(btrim(NULL)) > 0` est accepté par une `CHECK`, `IS NOT NULL` explicite ajouté. **Cinquième occurrence du paramètre lié partagé** (§7.25), cette fois dans mon propre test. **`T2` : la fiche en lecture** — données organisationnelles réutilisées de `lire_la_fiche` (LOT 5), `DSM` à tiret malgré un rattachement réel prouvé par témoin, `resoudre_les_permissions` exige une appartenance PROPRE pour accorder un rôle de responsabilité (règle du LOT 4 jamais exercée ainsi jusque-là). **`T3` : complétion, validation et publication** — un seul appel valide ET publie (matrice §7.1, pas un second geste), `recent_until` calculé par PostgreSQL (`+ INTERVAL '1 month'`, jamais par Python), `Support` (absent de la légende §4, même piège que §7.45/§7.46) couvre exactement Entité/Cercle/Global, et `BOOST` diverge sur la SEULE ligne « Valider et publier » du §7 (aide à compléter, jamais à valider) — permission écrite en fonction séparée. **Une affirmation fausse corrigée avant commit** : `entity_membership.short_bio`/`fun_fact` ne sont PAS déjà éditables depuis le LOT 5 — `T7` du LOT 5 les avait explicitement reportés, jamais rattrapés ; la passerelle avec `arrival_profile.short_intro`/`fun_fact` reste un résidu du LOT 5. **Correctif post-fusion `DEC-602`** : une quatrième ligne du §7, « Corriger après publication », manquée à la première lecture — sa grille s'inverse sur `NEW` (perd le droit après publication) et `DSM` (le retrouve, à tiret sur « Compléter ») ; sans elle, `US002` restait incomplète. **`T4` : le catalogue des tâches** (`DEC-603`) — ferme `ECART-013` structurellement. Une seule grille gouverne cinq des sept lignes du §9 ; `DSM`/`BOOST` (`Consultants`/`Cercle`) se réduisent à l'`Entité` pour cette table précisément, qui ne porte ni cercle ni DSM — collapsage documenté, pas une lecture large. Seul `SUPER` atteint `Global`. **Un résidu du modèle trouvé en lisant `T5` en avance** : `onboarding_template_version.state` réutilise l'énumération du conteneur au lieu de `draft`/`published`/`retired` (§13.3) — nommé pour `T5`, non bloquant pour `T4`. **`T5` : les modèles et leurs versions** (`DEC-604`) — le résidu nommé par `T4` est corrigé en préalable, migration `0021`, jamais en modifiant `0020` déjà appliquée : sans lui, le témoin d'immuabilité de la sous-étape (une version `published` refuse toute écriture de ses tâches) était irréalisable. **Contrairement au catalogue de `T4`, `Consultants`/`Cercle` ne se réduisent PAS à l'entité ici** : `onboarding_template` porte de vraies colonnes de portée, et un DSM/Booster ne gère que SON propre DSM-ship/cercle — deux témoins d'asymétrie le prouvent — tandis qu'`ESM`/`ADM-E`/`SUPER` gèrent n'importe quel DSM ou cercle de l'entité, même parti que `ROLES_DE_PORTEE_ENTITE` du LOT 6. Deux résidus nommés par `T1` (cohérence d'entité modèle↔cercle, modèle↔tâche de référence) sont instruits par le service, faute de clé composite sûre. **`T6` : le cycle de vie d'une version** (`DEC-605`) — publier, archiver, restaurer, aucune nouvelle table. `ECART-066` (volet version de modèle) résolu AVANT la route : l'ESM restaure librement dans son entité, comme les cinq ressources d'`ARB-DROIT-003` ; son volet « parcours » résolu à `T11`, même régime. **Restaurer ne rouvre PAS l'édition** : contrairement à `restaurer_une_page` (LOT 6, qui rend `draft`), une version restaurée redevient `published` — le modèle §13.3 déclare l'immutabilité d'une publication SANS exception, et un témoin le prouve directement (`PUT .../tasks` refuse toujours après restauration). DSM/Booster sont exclus EN BLOC sur cette seule ligne du §9, jamais un sous-cas de leur propre modèle. **`T7` : affecter et consulter un parcours** (`DEC-606`) — aucune nouvelle table, `onboarding_instance`/`_task` existent depuis `T1`. **La priorité de résolution du modèle n'était tranchée nulle part** : arbitrage de Jonathan, `DSM` > `CIRCLE` > `ENTITY` > `GLOBAL`, le plus spécifique gagne — quatre témoins postent les quatre modèles EN MÊME TEMPS. `DSM` a ici « Consultants » plein (troisième grille du module, contrairement à `T2` où il est à tiret). « Affecter » n'a pas de `Soi`, seule asymétrie avec la lecture. Une seule instance active par appartenance éprouvée au VOLUME (§7.26 du LOT 6), 40 affectations distinctes. **`T8` : terminer/annuler une tâche** (`DEC-608`) — aucune nouvelle table. Les DEUX lignes du §8.1 sont `Soi` SEUL, la grille la plus stricte du module : `DSM`/`BOOST` à tiret malgré un rattachement réel, un témoin le prouve sur un `DSM` rattaché à son consultant. `annuler_la_completion` ne produit JAMAIS l'état `cancelled` (réservé à `T10`) — la tâche redevient `todo`, un témoin re-termine la même tâche après annulation pour le prouver. La fenêtre de cinq minutes est ANCRÉE à `completed_at`, jamais une horloge mockée — le témoin « hors délai » recule cette valeur par SQL. **Correctif `DEC-607`** trouvé en écrivant `T8` : `T7` ne posait aucun événement `onboarding_task_event` malgré le critère de sortie 4 — `ASSIGNED` est désormais posé par l'affectation, `COMPLETED`/`CANCELLED` par `T8`, une seule fonction partagée. **Mon propre décor a reproduit le défaut `T7-5`** : un modèle `GLOBAL` créé avec la session de l'ESM, refusé 403 — seul `SUPER` gère `GLOBAL` — corrigé en `ENTITY`, que l'ESM gère pleinement. **`T9` : réouvrir une tâche après le délai** (`DEC-609`) — aucune nouvelle table. CINQUIÈME grille du module, INVERSE exacte de la quatrième (`T8`) : `ESM`/`ADM-E`/`SUPER` seulement, `Soi`/`DSM`/`BOOST` exclus EN BLOC malgré un rattachement réel — deux témoins le prouvent, un DSM et un Booster rattachés. Aucune fonction `peut_...` séparée : la garde de rôle coarse EST la vérification complète, même parti que le catalogue des tâches (`T4`). La fenêtre est l'INVERSE STRICT de celle de `T8`, ancrée à la MÊME colonne `completed_at`. **Correctif au diagramme §24.2** : `terminer_une_tache` (`T8`) n'acceptait que `todo`, jamais `reopened` — sans lui, une tâche réouverte restait dans une impasse permanente ; un témoin re-termine la tâche après sa réouverture. Motif obligatoire au corps ET à la base (contrainte posée dès `T1`, jamais exercée avant) — la PREMIÈRE route du projet à exiger et écrire un motif. **`T10` : le changement automatique de parcours au changement de statut** (`DEC-610`, `US007`) — aucune nouvelle table, aucune route propre : `remplacer_le_parcours_apres_changement_de_statut` est appelée par `_ecrire_le_statut` (LOT 5, `app/people/ecriture.py`) dans la MÊME transaction, après les cinq écritures organisationnelles. **AUCUNE GRILLE DE PERMISSION PROPRE, ET C'EST VÉRIFIÉ CONTRE LE CODE** : la grille du parcours (`T7`, DSM/BOOSTER rattachés SANS condition de type d'appartenance) est strictement plus large que celle qui autorise déjà l'écriture de `statut` (LOT 5, qui exige un Booster PRINCIPAL) — quiconque écrit `statut` est *a fortiori* dans le périmètre du parcours. `ECART-013` mis à l'épreuve pour de vrai : une tâche `completed` commune aux deux modèles (même `task_reference_id`) est RETENUE dans la nouvelle instance — `completed_at`/`completed_by_person_id` COPIÉS, `title_snapshot`/`due_at` RECALCULÉS depuis la nouvelle version — événement `RETAINED_ON_REPLACEMENT` ; les tâches `todo`/`reopened` de l'ancienne deviennent `cancelled`, événement `CANCELLED_ON_REPLACEMENT` — les deux dernières transitions du diagramme §24.2. Un changement de `client` seul, même statut, ne déclenche rien. `reference_date` de la nouvelle instance est l'INSTANT du changement, jamais `arrival_date`. **Deux points confirmés par Jonathan, pas présumés** : `replacement_reason` reste `NULL` (`DemandeDeModification` ne porte aucun champ motif), et aucun `outbox_message`/`async_job` n'est écrit (mesuré : aucune ligne du dépôt n'écrit encore ces deux tables, réservées au LOT 11). **`T11` : l'archivage automatique du parcours terminé et la révocation au départ** (`DEC-611`, ferme `§30.13` et `ECART-066`) — aucune nouvelle table. DEUX déclencheurs AUTOMATIQUES sans route propre, matrice §8.1/§8.2 : `archiver_le_parcours_si_termine` transitionne `active -> archived` dès que la dernière tâche obligatoire est `completed` (appelée par `terminer_une_tache`, `T8`, `completed_at` posé) ; `archiver_le_parcours_au_depart` fait de même AU DÉPART (appelée par `archiver_un_profil`, LOT 5 `T8`, accrochée SANS dupliquer `enregistrer_un_depart` — `completed_at` jamais posé, un parcours interrompu n'est pas achevé). DEUX gestes MANUELS avec route propre, `ESM`/`ADM-E`/`SUPER` seulement (même grille que la réouverture, `T9`) : archiver un parcours résiduel — un filet pour le cas que l'automatique ne couvrirait pas, ajouté sur confirmation explicite de Jonathan, en plus de l'automatique et non à sa place — et restaurer un parcours archivé, `ECART-066` (volet parcours) RÉSOLU en reposant la question EXPLICITEMENT, jamais en présumant la réponse donnée pour la version de modèle (`T6`) : même réponse, l'ESM restaure librement dans son entité. **Défaut trouvé et corrigé avant la fusion, dans mes propres tests** : brancher l'archivage automatique dans `terminer_une_tache` cassait 13 tests DÉJÀ FUSIONNÉS de `T8`/`T9` — compléter la dernière tâche obligatoire archivait l'instance dans le même geste, fermant sa résolution (`state='active'` strict) pour l'annulation en cinq minutes et la réouverture administrative, une dégradation d'exigences déjà livrées interdite sans décision explicite (§2, règle n°7). Corrigé en distinguant `lire_l_instance_active` (stricte, affectation et archivage manuel) de `lire_l_instance_actionnable` (`active` OU `archived`, JAMAIS `replaced`), employée par les trois routes de tâches. Contrat mis à jour (`contrat-api.json`, forme `InstanceDeParcours` déjà validée en `T7`). 16 tests d'intégration, zéro régression (`pytest` bare, sans filtre, comme `make check` : 75 échecs environnementaux identiques des deux côtés). **`T12` : le suivi par périmètre** (`DEC-612`, `US008`) — nouveau module `app/onboarding/suivi.py`, `GET …/onboarding-suivi/taches-en-retard`, aucune nouvelle table. Dernière ligne de consultation du §8.1 sans consommateur après `T11` : les deux autres — « Consulter le parcours d'un collaborateur » (`T7`) et l'archivage/restauration (`T11`) — étaient déjà servies, `T12` ajoute le REPORTING. AUCUN RÔLE N'EST REFUSÉ : la portée s'ajuste au rôle le plus large détenu — Entité (ESM/ADM-E/SUPER), Consultants (DSM), Cercle (Booster), ou `Soi` en dernier recours, résolu par une fonction PURE et testable sans base (`resoudre_le_perimetre_du_suivi`), disponible à n'importe qui sur SES PROPRES tâches — jamais une conséquence du rôle `OFFICE`, à tiret sur cette ligne comme partout ailleurs sur les modèles d'onboarding. « Reporting de base » SEULEMENT (cahier, Inclus) : aucun graphique, aucun export — LOT 10. « En retard » n'est pas restreint aux tâches obligatoires (`state IN ('todo', 'reopened')` et `due_at < instant`, sur TOUTE tâche), mais SEULES LES INSTANCES `active` SONT COMPTÉES, délibérément : une instance `archived` a déjà vu ses tâches obligatoires terminées (`T11`), et une tâche non obligatoire encore en retard dessus est un résidu que rien dans le corpus ne demande de signaler — un témoin construit ce cas précis plutôt que de l'affirmer. Pagination du cahier §18.2 réutilisée depuis `app/shared/pagination.py`, première consommation par l'onboarding. **Erreur de méthode trouvée et corrigée dans la preuve de zéro régression elle-même, avant toute fusion** : `pytest` lancé depuis `apps/api/` ne rend que 1 326 tests contre les 1 393 attendus — `testpaths` du `pyproject.toml` RACINE couvre aussi `apps/worker/tests` et `packages/observabilite/tests`, et c'est depuis la RACINE que `make check`/`make test` invoquent `pytest`. Relancée depuis la racine : 1 393 sur `origin/develop`, 1 404 (+11) sur la branche, 75 échecs environnementaux IDENTIQUES des deux côtés. **Défaut trouvé dans mes propres tests avant fusion** : les 11 tests manquaient `@pytest.mark.integration`, invisibles à `make test-integration` bien qu'exigeant PostgreSQL. Contrat mis à jour (`suiviDesTachesEnRetard`, forme `PageDeSuiviOnboarding`, aucun module TypeScript propre — même parti que `CatalogueDeTaches`, `T4`). **`T13` : les écrans du nouvel arrivant** (`DEC-613`) — UNE SEULE page, `PageMonOnboarding.tsx`, sous la rubrique `mon-onboarding` réservée par `T4` du LOT 4 ; aucune route API nouvelle, `T2`/`T3`/`T7`/`T8` livraient déjà tout ce que l'écran consomme. `GET …/permissions` (LOT 4, `T8`) ÉTENDU d'un champ `appartenance` — l'entity_membership_id occupant de l'appelant, `null` hors de l'entité principale, nouvelle fonction `_appartenance_occupante` — seul moyen dont dispose le frontend de savoir quelle URL appeler pour SA propre fiche et SON propre parcours, aucune route de l'onboarding n'acceptant de cible implicite ; réutilise une réponse déjà appelée une fois par page plutôt qu'un aller-retour de plus. `droitsDeNavigation` devient une fonction PURE prenant `aUnParcoursActif` en argument RÉEL, retirant la constante figée à `false` posée au LOT 4 — `CadreApplicatif` interroge `GET …/onboarding-parcours`, SÉQUENCÉ après `/permissions` dont il a besoin de `appartenance`. **DÉFAUT TROUVÉ ET CORRIGÉ, DANS UN CODE ÉCRIT À `T7`, JAMAIS EXERCÉ PAR UN ÉCRAN AVANT `T13`** : `validerLeParcours` (contrat TypeScript) exigeait `instance`/`progression`/`prochaine_tache` nuls ENSEMBLE ou aucun des trois — faux pour `prochaine_tache`, qui peut être nul même avec une instance `active` (aucune tâche `todo`/`reopened` restante) ; une réponse `200` légitime aurait levé côté client, silencieusement. **AUCUNE FENÊTRE DE CINQ MINUTES N'EST CALCULÉE CÔTÉ CLIENT** : le bouton « Annuler » est proposé pour toute tâche `completed`, c'est le `409` de l'API qui referme la fenêtre. **LE FRONTEND NE PROPOSE PAS UN DROIT DÉJÀ REFUSÉ** : « Valider et publier » désactivé sans présentation courte ou avec des modifications non enregistrées ; après publication (§6.2), la fiche bascule en lecture seule. **ALLER-RETOUR RÉEL EFFECTUÉ (§7.43 du LOT 6)** : décor psql réel, lien magique réel consommé dans le navigateur, lecture/complétion/validation-publication/complétion de tâche/annulation — tous les appels réels à `200`, décor nettoyé après coup. **Décision explicite de Jonathan : aucun script `make onboarding-check` à `T13`**, reporté à `T14`, combiné pour les deux sous-étapes plutôt que dupliqué deux fois de suite. **`T14` : les écrans d'administration** (`DEC-614`) — UNE SEULE page, `PageAdministration.tsx`, sous la rubrique `administration` réservée par `T4` du LOT 4 ; trois sections (catalogue, modèles, suivi). **Décision de Jonathan : le menu s'élargit** — nouvelle liste `rolesAdministrationOnboarding` (DSM, ESM, BOOST, ADM-E, SUPER), déclarée SÉPARÉMENT de `rolesAdministration` (§20), jamais fusionnée (§7.27) ; `droitsDeNavigation` en prend l'UNION ; le suivi n'y entre PAS, sa grille ne refusant jamais personne. **Route API nouvelle, trouvée en construisant l'écran** : `GET …/onboarding/templates` (`app/onboarding/gabarits.py` : `lister_les_modeles`, `lister_les_versions`) — ni `T5` ni `T6` n'avaient posé de LECTURE des modèles, filtrage par rôle appliqué en Python sur la liste brute, jamais une seconde règle SQL (§7.27) ; chaque modèle avec ses versions imbriquées. Le droit de lecture d'OFFICE (« Consulter les modèles publiés », §9) reste SANS route : aucun critère actuel ne le réclame. Troisième liste, `rolesRestaurationDesModelesOnboarding` (ESM, ADM-E, SUPER), gate le seul bouton « Restaurer » — DSM/BOOSTER exclus EN BLOC de cette ligne du §9, `ECART-066`. **LE SCRIPT DE PILE DIFFÉRÉ PAR `T13` EST CONSTRUIT ICI, COMBINÉ POUR LES DEUX** : `infra/scripts/verifier-administration-onboarding.py` (14 contrôles, pile RÉELLE — Caddy, HTTPS) — témoin d'asymétrie DSM/ESM (les deux rôles dans la MÊME entité, chacun voit un ensemble de modèles DIFFÉRENT), cycle de vie complet exercé une fois en vrai (créer, composer les tâches, publier, archiver, restaurer), OFFICE refusé (403) sur les modèles MAIS reçu (200) sur le suivi, `ECART-066` éprouvé DANS LE SENS DU REFUS. Ajouté à `make check`, nommé dans `ci.yml`. `make ecrans-check` couvre `PageAdministration.tsx` SANS AUCUNE MODIFICATION DU CONTRÔLE — glob générique, 47 modules contre 30 avant `T14`, bénéfice direct du §7.27. **ALLER-RETOUR RÉEL EFFECTUÉ (§7.43 du LOT 6)** : décor psql réel, lien magique réel, cycle complet créer/composer/publier/archiver/restaurer — tous les appels réels à `200`/`201`, décor nettoyé après coup |
| **Que fait-on au LOT 6 ?** | **`docs/operations/fiche-lot-6.md`** — **7** stories, **7** critères de sortie **dérivés des DEUX sources qui concordent**, **DOUZE** sous-étapes validées le 13/09/2026 (`DEC-575`). **Son §2.1 porte TROIS pièges mesurés**, tous dans le même sens : `ADM-E` est à **tiret** sur l'affectation du Booster et des responsables, et `OFFICE` n'a que le **contenu** d'un bureau, pas sa structure. **Son §8 instruit SEPT écarts** — deux sont clos par `DEC-576`, trois relèvent de **Léa**. **Et son §8.3 a trouvé ce que personne n'avait relevé** : le cahier §10.7 et le modèle §15.2 donnent **deux listes de blocs différentes**, dont l'union vaut **neuf ou dix** selon une lecture qu'aucun document ne tranche — `QO-119` |
| **Comment a-t-on fait les sous-étapes du LOT 6 ?** | **`docs/operations/compte-rendu-t{1,…}-lot-6.md`** — `T1` les trois tables éditoriales, `T2` la page Framework, `T3` la page détaillée d'un cercle, `T4` celle d'un bureau, `T5` le rendu des blocs, `T6` l'**écriture**, `T7` le **cycle de vie**, `T8` les **liens internes**, `T9` les **trois écrans de lecture**, `T10` les **écrans d'édition**. **LE §3 DE `T10` PORTE LA LEÇON LA PLUS TRANSFÉRABLE DU LOT, ET LE CONTRÔLE DE PILE L'A TROUVÉE AVANT LA FUSION** : la route posée pour retrouver une page ARCHIVÉE exigeait `MODIFIER`, que `_actions_selon_l_etat` ne rend jamais sur une page archivée — seulement `RESTAURER`. Un test unitaire ne l'avait pas vu, parce qu'il testait la fonction et non la garde de la route ; `make framework-check`, étendu de 68 à 74 contrôles, l'a fait tomber au premier aller-retour réel — corrigé en exigeant l'ensemble **non vide** plutôt qu'une action précise. **Son §2.1 porte un second constat, structurel** : `T6` avait exposé au manifeste ses propres grilles de rôles pour ses propres écrans, comme `T7` et `T8` l'avaient fait — sauf que `T6` ne l'avait PAS fait, un oubli de la discipline `DEC-492` que seule l'écriture de `T10` a révélé, faute d'écran consommateur avant elle. **LE §2.2 DE `T8` PORTE LE CONSTAT LE PLUS TRANSFÉRABLE DU LOT APRÈS CELUI DE `T7`, ET IL CONTREDIT LA LECTURE LITTÉRALE D'UNE EXIGENCE ÉCRITE DEUX FOIS** : le corpus demande que les URL soient validées « selon une **liste de protocoles autorisés** », et **une liste de protocoles ne suffit pas** — `https:alert(1)` a pour protocole `https` et n'adresse aucune ressource. L'API exige **aussi un hôte**. **Son §2.5 est un résultat déguisé en absence** : la « présentation de l'entité » du §13 n'a demandé **aucune ligne de code**, sa grille étant identique cellule par cellule à « Créer un contenu général » et `HOME` tombant par soustraction dans le régime des rôles d'entité — deux tests le **mesurent**. **Son §4 porte le seul défaut de la sous-étape**, `T8-1`, et il est **non déterministe** : le décalage de la réécriture d'ordre était dérivé du **nombre** de liens, ce qui ne vaut que si les rangs vivants sont `0..n-1` **sans trou** — ce que l'archivage d'un lien détruit. J'avais **mesuré** `max + 1` dans ma sonde préalable, puis écrit `len(ordre)` « pour faire plus simple ». **Son §3.3 est la deuxième campagne du lot à finir avec ZÉRO filtre muet** : six l'étaient, cinq étaient de vrais trous — et le sixième, `FOR UPDATE`, n'est observable par **aucun** test séquentiel, ce qui est **dit** plutôt que tu. **Le §2.1 de `T7` porte la leçon la plus transférable du lot, et elle a clos un écart** : `Périmètre` est employé dans plus de vingt cellules de la matrice et **ne figure pas dans la légende §4** — mais le **§3 le définit**, dans une colonne intitulée « Périmètre principal », où l'`ESM` a « ensemble de son entité », soit mot pour mot la définition de `Entité`. `ECART-063` annonçait deux grilles divergentes pour l'archivage ; il n'en restait **qu'une cellule**, et elle n'est pas exprimable dans le modèle. **Son §3.4 est la première campagne de témoins du projet à finir avec ZÉRO filtre muet** — cinq l'étaient, et les cinq étaient de vrais trous : tous mes autres cas passaient par le périmètre, si bien que la précondition du **service** n'était exercée par personne. **Son §3.3 dit ce que le déclencheur du §8.4 NE garantit pas** : il garde la **transition**, pas l'état permanent, et un bureau publié peut redevenir non conforme — ce qui **explique** la lecture tolérante de `T4` au lieu de la rendre obsolète. **Le §4 de `T6` porte le défaut le plus transférable du lot** : mon vérificateur de témoins a **menti en silence**, parce que CPython invalide un `.pyc` sur le couple `(mtime TRONQUÉ À LA SECONDE, taille)` et que quatre de mes variantes pesaient **exactement** 13 487 octets. Trois d'entre elles ont exécuté le bytecode d'une variante **précédente**, et le vérificateur annonçait « 0 échec » — la **même observation** que « ce filtre ne travaille pas ». Parade : `PYTHONDONTWRITEBYTECODE=1`, **mesurée avant d'être appliquée**. **Son §3.3 nomme deux filtres REDONDANTS**, troisième occurrence après `T4-2` et `T5-1` — et trois fois sur trois, ce qui protégeait était une **contrainte ailleurs**. **Le §2.2 de `T5` dit ce que le LOT 6 ne validera PAS** : le §15.2 veut « des champs structurés ; un `payload_json` validé par type », et **le corpus n'en nomme aucun** — le contenu est donc servi comme une **donnée opaque**, et `QO-121` porte la question à Léa. **Le §4 de `T4` porte la leçon la plus transférable du lot** : la fiche ET cette passation annonçaient que `T4` poserait le **déclencheur** du comptage borné, et c'était une **prévision** (§7.41) — le critère de la story dit « affichés », et la borne ne mord qu'à la publication, qu'aucune route n'écrit encore. `DEC-583` l'envoie à `T7`. **Le §2.1 de `T3` porte une leçon de structure** : les trois tailles du §18.2 vivaient dans le trombinoscope, et `T3` en étant le second consommateur, un **import circulaire mesuré** a imposé de les déplacer dans `app/shared/pagination.py` — *un fait du CAHIER se déclare dans `shared`, pas dans le premier module qui en a eu besoin*. Même remède que pour `ETAT_LISTE`. **Son §4 porte le défaut le plus utile du lot** : `alembic --autogenerate` a proposé de **supprimer l'index de recherche du LOT 5**, un index sur EXPRESSION qu'il ne sait pas réconcilier. Il n'était déclaré dans **aucun** module et **aucun test** n'exigeait son existence — le piège était debout pour toutes les sous-étapes suivantes. **Lis cette section avant de relancer un `--autogenerate`** |
| **Que fait-on au LOT 5 ?** | **`docs/operations/fiche-lot-5.md`** — 8 stories, **7** critères de sortie **dérivés**, **ONZE** sous-étapes : validées à douze le 24/08/2026, **révisées le 06/09/2026** quand `T5` et `T6` ont été fusionnées (`DEC-564`). **Son §2.1 porte un piège mesuré**, et son **§8.2 se trompait de lot** — il attribuait à `T5` le choix du format des miniatures, qui appartient à qui les **produit**, donc au LOT 11. `ECART-052`, clos |
| **Comment a-t-on fait les sous-étapes du LOT 5 ?** | **`docs/operations/compte-rendu-t{1,…,5,7,…,12}-lot-5.md`** — les trois tables de média, le trombinoscope en lecture, la recherche, la fiche, la miniature, l'écriture, l'archivage, l'historique, et le **premier écran métier**. **Ne recopie pas leur nombre de défauts** : `grep -ohE '`\`T[0-9]+-[0-9]+\`'` sur ces fichiers, `sort -u | wc -l` — **62** au 12/09/2026, et **presque tous sont dans mes propres contrôles**. `T3` en a nommé treize à elle seule, dont **six dans la mesure** |
| **Que faisait-on au LOT 4 ?** | **`docs/operations/fiche-lot-4.md`** — 12 sous-étapes, **les DOUZE barrées**, **découpage validé le 22/08/2026**. **LES DOUZE sont faites**, et son §8 n'a plus aucun point ouvert. **Son §8 n'a plus AUCUN point ouvert**, et une mise à jour du 24/08/2026 y dit que **les cinq règles du §23.3 sont tenues et prouvées**. **Son §8 porte une correction en tête** : il annonçait deux points ouverts, il n'en reste qu'un |
| **Comment a-t-on fait les DOUZE sous-étapes du LOT 4 ?** | **`docs/operations/compte-rendu-t{1,…,12}-lot-4.md`** — la première route métier, l'entité consultée, le cadre, la navigation, la barre mobile, la page nationale, puis la carte. **Le §8 de la fiche s'est trompé sur l'un de ses deux points ouverts** (`ECART-040`) ; **`T3` a trouvé deux défauts qui vivaient depuis un mois** (`ECART-041`, `ECART-042`) ; et **`T4` en a trouvé deux de plus dans MES propres contrôles** (`ECART-043`, `ECART-044`). **`T8` en a trouvé quatre, dont TROIS dans mes contrôles** — et le quatrième, un vrai défaut du livrable, n'a été vu que **dans un navigateur** |
| Que faisait-on au LOT 3 ? | `docs/operations/fiche-lot-3.md` — 12 sous-étapes, **les douze barrées** |
| **Comment a-t-on fait `T1` et `T2` du LOT 3 ?** | **`docs/operations/compte-rendu-t{1,2}-lot-3.md`**. `T1` : le moindre privilège. `T2` : les sept tables du §10 |
| Quelles sont les 7 tables d'authentification ? | Modèle **§10.1 à §10.6**, et `apps/api/app/auth/modeles.py` en porte la lecture |
| Que faisait-on au LOT 2 ? | `docs/operations/fiche-lot-2.md` — 12 sous-étapes, **`T1` barrée**. Découpage validé le 18/08/2026 |
| **Comment a-t-on fait les DOUZE sous-étapes du LOT 2 ?** | **`docs/operations/compte-rendu-t{1,…,12}-lot-2.md`**. **Ne recopie pas leur nombre** : `grep -ohE '`\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-2.md \| sort -u \| wc -l` — **37** au 20/08/2026, et **les dix de `T10` et `T11` sont tous dans mon travail** |
| Que faisait-on au LOT 1 ? | `docs/operations/fiche-lot-1.md` — 12 sous-étapes, **les 12 barrées** |
| **Comment a-t-on fait `T1` à `T11` ?** | **`docs/operations/compte-rendu-t{0,…,11}-lot-1.md`** |
| **Qu'a validé Jonathan à la porte `G6`, FRANCHIE le 25/09/2026 ?** | **`docs/operations/checklist-validation-G6.md`** — les **sept** critères de sortie avec ce qui prouve chacun, **dix** gestes de démonstration, les cinquante-sept contrôles de la recette, le classement du §30, et **son §7 : ce que le lot n'a PAS fait**. C'est ce §7 qu'il faut lire en premier |
| **Qu'a validé Jonathan à la porte `G5`, FRANCHIE le 13/09/2026 ?** | **`docs/operations/checklist-validation-G5.md`** — les **sept** critères de sortie avec ce qui prouve chacun, **huit** gestes de démonstration, les trente-deux contrôles de la recette, et **son §7 : ce que le lot n'a PAS fait**. C'est ce §7 qu'il faut lire en premier |
| **Que valide Jonathan à la porte `G4` ?** | **`docs/operations/checklist-validation-G4.md`** — les **six** critères avec le contrôle qui prouve chacun, huit gestes de démonstration, et **ce que le lot n'a PAS fait** |
| **Que valide Jonathan à la porte `G2` ?** | **`docs/operations/checklist-validation-G2.md`** — les 7 critères, les 25 contrôles du §30 **classés**, et une démonstration guidée |
| **Qu'a produit `T15` du LOT 7 ?** | **[`docs/operations/compte-rendu-t15-lot-7.md`](docs/operations/compte-rendu-t15-lot-7.md)** et **[`checklist-validation-G7.md`](docs/operations/checklist-validation-G7.md)** — recette isolée sur les images publiées, parcours HTTPS réel, §30 à **16 acquis, 2 partiels, 7 reportés** ; validations humaines acquises le 30/09/2026, porte `G7` franchie (`DEC-617`) |
| Que validait-il à `G1` ? | `docs/operations/checklist-validation-G1.md` — 33 contrôles |
| **Comment EXPLOITE-t-on la plateforme ?** | **`docs/operations/exploitation-locale.md`** — toutes ses commandes ont été exécutées |
| Qu'a-t-on décidé depuis le début ? | `docs/decisions/registre-decisions.md` — **le compte est au §1, et `make docs-check` le dérive**. Ne le recopie pas ici : c'est le seul endroit qu'un contrôle lit |
| Comment travaille-t-on ? | `CONTRIBUTING.md` et `docs/operations/conventions-git-et-versions.md` |

Les cinq documents de cadrage sont **immuables**. Intégrité prouvée par empreinte SHA-256 dans
`docs/operations/integrite-et-conformite-documents.md`. **Ne les modifie pas** — et vois §7.9,
un formateur a failli les réécrire.

Règle de préséance : le cahier prévaut ; une décision plus récente prévaut sur une plus
ancienne ; les annexes précisent le détail ; **aucune hypothèse ne remplace une décision
explicite de Jonathan**.

---

# 4. Ce qui a été livré, et comment

## 4.1 LOT 0 — référentiel documentaire

Sept stories, huit sous-étapes. 5 documents de cadrage versionnés avec preuve d'intégrité,
`CONTRIBUTING.md`, 5 registres, `.env.example`, schéma CSV, inventaire du prototype.

## 4.2 `T0` — prérequis et arbitrages, hors lot

3 prérequis bloquants levés, 7 choix techniques tranchés, traçabilité GitHub posée par `gh`.
Détail : [`compte-rendu-t0-lot-1.md`](docs/operations/compte-rendu-t0-lot-1.md).

## 4.3 `T1` — squelette du monorepo

Les **sept répertoires** du cahier §15.3, chacun avec son `README.md`. Workspaces `pnpm` **et**
`uv`. Ruff, mypy strict, pytest, ESLint avec `jsx-a11y`, Prettier, `tsc --noEmit` strict, Vitest.
`Makefile` comme point d'entrée unique.

**Comment :** chaque maillon de la chaîne a reçu un **défaut réel** pour vérifier qu'il sait
échouer — **10 témoins négatifs sur 10**. Un contrôle qui ne peut pas échouer ne prouve rien.

## 4.4 `T2` — stack Docker locale

`make up` construit, démarre et attend l'état sain des **huit services**. Compose en base +
surcouche, projet `onboarding-dev`. **8 images toutes épinglées par empreinte `sha256`**, toutes
vérifiées `linux/amd64` **et** `linux/arm64`. 6 volumes nommés. 7 publications **toutes sur
127.0.0.1**. HTTPS local par autorité interne Caddy.

**Comment :** `make persistence-test` relève cinq empreintes, arrête, redémarre, compare. Le
témoin négatif a été **réellement exécuté** — volume `redis-data` supprimé, contrôle en échec.

## 4.5 `T3` — API, santé, migration

Les **11 garde-fous** de démarrage du cahier §20.3. Les trois endpoints du §18.7. Format
d'erreur unique du §18.3. Migration `0001_initial`, **volontairement vide** (`DEC-463`). Worker
Dramatiq avec les **7 files** du §16.4.

**Comment :** `ready` a été éprouvé en **arrêtant réellement Redis** — 503, `redis
indisponible`, motif `ConnectionError`, PostgreSQL et MinIO toujours disponibles. Chaque
garde-fou a **deux** tests : celui qui l'enfreint, et le témoin qui le respecte. Les sept
contrôles de production sont éprouvés **en forçant `APP_ENV=production`**, plus un test qui
prouve qu'ils **ne s'appliquent pas** en développement.

## 4.6 `T4` — journalisation JSON corrélée

Les **dix champs** du §28.1 dans les journaux réels des conteneurs. Corrélation en **requête et
en job** : elle traverse Caddy, revient dans la réponse, et **voyage dans le message Dramatiq**.
**Trois barrières** de masquage du §28.2. Rotation `json-file` sur les huit services.

**Comment :** un **paquet Python partagé**, `packages/observabilite`, plutôt que du code
dupliqué — deux filtres de masquage finissent par diverger, et le jour où l'un oublie un motif
la fuite est silencieuse.

## 4.7 `T5` — page de statut

La page est servie sur `app.onboarding.localhost`. Elle affiche les **trois** dépendances que
l'API sonde, la version du build, et **dit sur elle-même** que le worker, Mailpit et Caddy ne
sont pas sondés — plutôt que de laisser croire à un tableau de bord des huit services.
**Cinq états** et non trois : chargement, nominal, **dégradé**, erreur, hors connexion.

**Comment :** un 503 de `/health/ready` porte **la même forme JSON** qu'un 200. Le lire comme une
erreur réseau jetterait le diagnostic au moment où il devient utile — le client accepte donc 200
**et** 503 pour `ready`, 200 seul pour `version`. Le critère « affiche l'état réel » a été éprouvé
en **arrêtant réellement Redis** : 503, `redis indisponible`, motif `ConnectionError`.

**Et un contrôle qui n'existait pas :** `eslint-plugin-jsx-a11y`, motif déterminant de `DEC-451`,
n'avait jamais eu un seul fichier JSX à examiner — il n'existait aucun `.tsx` dans ce dépôt.
Éprouvé par témoin négatif, il examine et il **sait échouer**.

## 4.8 `T6` — intégration continue

**Le test le plus important du lot, et il exigeait de prouver l'échec.** Les 11 contrôles du
cahier §23.1 tournent sur chaque pull request en **~2 min 20**, découpés en deux tâches — la
qualité rend son verdict en une minute sans attendre Docker — et une **porte** unique qui conclut.

**Comment :** trois défauts introduits **un par un** dans une pull request jetable, chacun dans sa
propre poussée pour que l'échec soit attribuable. Lint, test, secret : trois exécutions rouges,
`mergeStateStatus: BLOCKED` dans les trois cas. Témoin positif indispensable : la même porte
laisse passer la branche de `T6`, `MERGEABLE` / `CLEAN`.

> **Piège de vocabulaire GitHub.** Le champ `mergeable` ne parle que des conflits et vaut
> `MERGEABLE` même sur une pull request refusée. C'est **`mergeStateStatus`** qui fait foi.

**Et deux défauts dormants réveillés** : le `Makefile` n'avait jamais tourné ailleurs que sur
macOS avec des volumes déjà peuplés. `make env` employait la forme BSD de `sed`, et `make up`
n'avait **jamais** fonctionné sur une machine propre. Voir §7.16.

## 4.9 `T7` — images multiarchitecture et publication GHCR

**Le dernier critère technique de la porte `G1`, et il exigeait de LANCER, pas de construire.** Les
trois images sont construites pour `linux/amd64` **et** `linux/arm64` en une **liste de manifestes
unique**, publiées dans GHCR privé, et **lancées sur les deux architectures** — 39 contrôles
fonctionnels, 0 échec.

**Comment :** en lisant, **dans** chaque conteneur, une valeur que l'autre architecture ne pourrait
pas produire — `uname -m` à `x86_64` ou `aarch64`. Un contrôle qui se contenterait de « le
conteneur a démarré » donnerait la même observation sur les deux, et ne prouverait rien.

**Deux risques clos d'un même geste.** `Dockerfile` `web` à **deux cibles nommées** (`DEC-479`) :
`developpement` garde le serveur Vite, `execution` sert l'artefact de `vite build` par Caddy. La
cible publiée passe de **1,02 Gio à 84,9 Mo**, et ni Node, ni Vite, ni ESLint n'y subsistent.
`ROAD-RSK-030` et `ROAD-RSK-031` sont clos.

**Et un gisement que le risque ne visait pas :** `docker history` a montré qu'un `RUN chown -R`
pesait **230 Mio** dans `web` et **143 Mio** dans `api` et `worker`. Une couche d'image
réenregistre le fichier **entier** dès qu'une métadonnée change : elle duplique l'arborescence dont
elle ne modifie que le propriétaire. `api` et `worker` perdent 29 % à ce seul titre.

**Trivy : mesuré avant d'être réglé.** `python:3.12-slim` porte **23 avis `HIGH`/`CRITICAL` dont
aucun n'a de correctif**. Bloquer sur `HIGH` aurait rendu la chaîne définitivement rouge sans
remède. La porte bloque donc sur `CRITICAL` **corrigeable** seulement, et rapporte le reste
visiblement (`DEC-482`). Second constat de la mesure : **nos couches n'ajoutent aucune
vulnérabilité**, les totaux sont exactement ceux des images de base.

> **Une réserve à connaître, et elle est dans la fiche §3.1.** `arm64` n'est prouvé **nativement**
> que sur une liste de manifestes construite localement, pas sur l'image publiée — le jeton `gh`
> n'a pas `read:packages`, et Jonathan a arbitré de ne pas l'ajouter. Sur l'image publiée, `amd64`
> est natif et `arm64` est **émulé**. Les deux empreintes sont nommées au compte rendu.

## 4.10 `T8` — environnement de recette isolé, sur les images publiées

**Les SEPT séparations du cahier §22.2, et la fiche n'en énumérait que six.** Le critère écrit dans
la fiche omettait « projet Docker distinct » — celle qui **produit** les volumes et le réseau
distincts, Compose les préfixant du nom de projet. C'est `ECART-023`, exactement la classe de
`ECART-018`. **Compte-les sur le cahier, jamais sur une fiche.**

**Comment :** chaque séparation est lue sur l'**état réel**, jamais sur un fichier `.env` — une
variable déclarée n'est pas une base servie, et `T7-8` l'avait montré. Deux séparations exigeaient
mieux qu'une comparaison de noms : la base et le bucket de l'autre environnement doivent être
**ABSENTS**, parce que deux noms distincts dans deux services qui partageraient un volume donneraient
la même observation. **57 contrôles, 0 échec, et le vérificateur compte les séparations examinées.**

**La recette exécute l'artefact PUBLIÉ, épinglé par empreinte** (`DEC-486`). Le fichier de base
déclare `build:` : sans garde-fou, une image absente ferait construire localement et la recette
exercerait un autre artefact **en paraissant saine**. `--no-build` rend l'échec bruyant — éprouvé
avant l'authentification : `unauthorized`, **0 conteneur démarré, 0 construction de repli**.

**La réserve `arm64` de la fiche §3.1 est LEVÉE.** Jonathan a élargi son jeton à `read:packages`
(`DEC-483`, qui renverse l'arbitrage de `T7`), la recette tire l'image publiée sur ce Mac, et
`uname -m` y rend **`aarch64` 3 fois sur 3**. Les deux architectures sont désormais natives **sur le
même artefact**.

**Et un constat que le critère ne visait pas.** Mon contrôle d'isolement réseau a échoué sur un
livrable conforme. Diagnostic avant correction : **publier un port perce l'isolement inter-réseaux
de Docker** — mesuré sur un **même conteneur**, `mailpit:8025` publié est joignable depuis la
recette, `mailpit:1025` non publié ne l'est pas. La règle `ACCEPT` d'un port publié précède les
règles `DOCKER-ISOLATION`. **Ce qui protège est la cinquième séparation, les secrets** : avec le mot
de passe de la recette, la base de dev **refuse**. `ROAD-RSK-034`, et vois §7.20.

---

## 4.11 `T9` — documentation d'exploitation locale

**Le critère disait « les procédures FONCTIONNENT depuis une machine propre ». Le mot qui commande
tout est « fonctionnent ».** Les 13 commandes `make` du document ont donc été exécutées une par une,
et les sorties citées sont réelles.

**Le démarrage à froid est véritable, et il l'est plus qu'en `T6` et `T8`.** Ces deux sous-étapes
avaient supprimé **un** volume. `T9` a détruit **tout** ce que la recette possédait — 6 volumes,
conteneurs, réseau — **et retiré les 3 images du cache local**. Une machine qui n'aurait jamais vu ce
projet est dans cet état exact. Remontée : **34 secondes**, 8/8 sains.

**Le développement n'a pas été touché**, sur arbitrage de Jonathan : détruire `dev` aurait supprimé
`caddy-data`, donc l'autorité approuvée dans son trousseau, et lui aurait coûté une réapprobation.

**Deux faits d'exploitation que seule l'exécution révèle :**

- **après un démarrage à froid, la migration n'est PAS appliquée.** Et `make migrate-status` sur une
  base non migrée affiche **rien** en sortant en **0** : une sortie vide ne veut pas dire « tout va
  bien », elle veut dire « rien n'est appliqué » ;
- **les 14 publications et les 12 volumes sont DÉRIVÉS** par commande dans le document, jamais
  recopiés. Toute liste recopiée est un `ECART-021` en puissance.

**Et trois cibles n'avaient jamais tourné.** `make destroy` — destructive et interactive — n'avait
jamais été lancée depuis son paramétrage en `T8` ; `make caddy-recreate` jamais sur la recette ; et
`make web-check` avait son origine en dur sur le développement. **Les trois ont été éprouvées, et
deux portaient un défaut.** Voir §7.21.

---

## 4.12 `T10` — design system et contrat API partagé

**Le critère disait « sans dépendance visuelle arbitraire », et c'était le seul endroit du lot où la
règle §6.5 — ne jamais inventer ce qui n'est pas décidé — était en jeu aussi directement.**

**Mesure d'abord :** le cahier §13.1 exige « la charte graphique » et « la police officielle » ;
**aucune des deux n'est dans le corpus**, aucun fichier de design n'est versionné, et le cahier ne
contient **aucune** couleur hexadécimale. Zéro occurrence.

**Le prototype, lui, NOMME sa palette** — `EXALT_BLUE = #5853FF`, `EXALT_DARK_BLUE = #2F2F9B`,
`EXALT_PINK = #FF2C9B`, `EXALT_YELLOW = #FFDA3E` — et cela corrobore littéralement le « dégradés
bleu, rose et violet » du §13.2. Deux sources concordantes, donc pas une invention. Arbitrage de
Jonathan sur quatre options.

**Et la mesure a CORRIGÉ le prototype, ce qui est le résultat le plus utile.** Le jaune rend **1,37**
de contraste sur fond clair, le bleu foncé **1,69** sur fond sombre : les couleurs de marque sont des
**surfaces** portant un texte apparié mesuré, pas des couleurs de texte libres. Le prototype ne
prévoyait du texte foncé que pour le jaune ; **le rose et le vert le réclament aussi**. Le reprendre
tel quel aurait reconduit deux défauts d'accessibilité.

**Le contrat : le sens de vérification est INVERSÉ, et c'est mesuré.** `components.schemas` du schéma
OpenAPI servi est **vide** — les routes rendent des dictionnaires sans modèle. Générer aurait produit
des types `unknown`, donc l'illusion d'un contrat typé. Un **manifeste JSON unique** déclare donc le
contrat, lu par TypeScript **et** par un contrôle Python qui vérifie que le schéma le respecte.

**Un constat produit par ce contrôle dès sa première exécution :** l'API ne documentait **pas** le
503 de `/health/ready`, que le frontend traite comme un état exploitable depuis `T5`.

**Et un événement extérieur qui ferme un risque.** `make audit` est passé de 1 avis toléré à 4 avis
hauts **sans que `T10` y soit pour rien** — vérifié sur un arbre créé avant `T10`, qui rend les mêmes
4. Ce sont des avis nouvellement publiés. Les deux sont corrigeables par montée de correctif, et
`brace-expansion@1.1.18` corrige au passage l'avis que `T6` avait mesuré **sans correctif
possible**. L'audit passe à **zéro avis, zéro tolérance** : `ROAD-RSK-032` est clos, `DEC-493`. Vois
§7.22.

---

## 4.14 LOT 2 — le socle de données, en douze sous-étapes

**Verrouillé le 20/08/2026, `G2` franchie, tag `v0.2.0`.** Ce qu'il a produit : **18 tables métier**,
**11 migrations** rejouables, **8 clés étrangères composites**, **7 relations historisées**, et un jeu
de recette de **27 936 lignes**. **Ce paragraphe annonçait « toutes les requêtes répondent sous
1,3 ms », et ce nombre n'est pas reproductible** : cinq exécutions du même test le 08/09/2026 ont
rendu de **74,7 à 1 171 ms** sur du code identique, parce que le banc d'essai engendre son volume
dans une transaction **annulée** et que le planificateur croit alors les tables vides. Le test
n'exige donc plus **aucune** durée : il exige la **justesse** et rapporte le reste. `ECART-055`,
`DEC-567`.

**Les six idées qui structurent tout le socle, et qu'il faut connaître avant d'y toucher :**

1. **Une contrainte d'exclusion dont la clé contient une colonne NULLABLE ne contraint RIEN** sur les
   lignes où elle est nulle — `=` ne rapproche jamais deux NULL. Défaut `T8-1`, qui valait **trois
   types sur quatre**. Toutes les exclusions sont donc **partielles et autoportantes**, et
   `make historisation-check` l'exige ;
2. **Les clés étrangères COMPOSITES `(id, entity_id)` du §25.3 sont ce qui porte l'isolation**, pas un
   déclencheur. Il y en a **huit**, et `make isolation-check` prouve qu'aucune référence locale n'y
   échappe. **`MATCH SIMPLE` rend une clé composite inerte dès qu'une colonne est nulle** : le
   contrôle exige `entity_id NOT NULL` à la source ;
3. **Une permission du modèle n'est pas une interdiction.** Le §8.2 autorise plusieurs cercles
   secondaires, le §8.4 plusieurs Boosters dans une même entité : un index unique naïf les casserait
   **et le livrable paraîtrait correct**. Chaque permission a son témoin ;
4. **Le modèle décrit parfois une ACTION, et seule l'IMPLICATION est applicable en base.** « Un DG
   reçoit automatiquement une responsabilité DSM » suppose un attributeur, que la base ne connaît
   pas ; inventer un attributeur **fabriquerait une trace d'audit fausse**. La base porte
   l'implication, le service porte l'action ;
5. **Un déclencheur `BEFORE ROW` s'exécute AVANT les clés étrangères**, et peut donc **ombrager** l'une
   d'elles. Quand c'est le cas, la clé est conservée et **le catalogue prouve ce que le comportement
   ne peut plus prouver** ;
6. **Les dépôts rendent le cloisonnement structurel.** `DepotLocal` ne sait pas construire une requête
   sans son `entity_id`, et `DepotGlobal` **refuse** une table locale — sans quoi il rendrait les
   lignes de toutes les entités **en paraissant fonctionner**.

## 4.15 LOT 3 — où en est l'authentification

**`T1` — le moindre privilège PostgreSQL** (`QO-116` close, `DEC-520`). Trois comptes et non deux, le
transfert de propriété **explicite et filtré** — 188 des 196 fonctions appartiennent à `btree_gist` —
et les **privilèges par défaut** qui couvrent les tables futures. Tout rejoué sur une base **recréée de
zéro**. Voir §5.9.

**`T2` — les sept tables du §10** (`DEC-521`, migration `0012`). Les §25.2 à §25.4 n'imposent **aucune**
contrainte à ces tables ; le §25.1 s'ouvrant par « à prévoir **notamment** », **quatre unicités de
plus** sont posées, chacune **dérivée** d'une règle écrite. L'index partiel de `magic_link_request`
porte l'**invariant** du §10.3 — « au plus un lien actif par personne » — et non son action : **il ne
fait pas l'invalidation, il la rend obligatoire.**

**Et `make secrets-check` distingue deux familles d'empreintes** : celles de **jeton**, SHA-256 bornées
à 64 caractères, et celles de **mot de passe**, de longueur variable, dont ce qui les rend exploitables
est la présence des colonnes `algorithm` et `parameters` que le §10.2 exige.

---

## 4.13 Les décisions qui contraignent ton travail quotidien

Toutes sont dans `docs/decisions/registre-decisions.md` — leur compte est au §1, dérivé. Celles que tu appliqueras :

| ID | Décision |
|---|---|
| `DEC-418` | Le dépôt réside dans iCloud Drive. Risque accepté, **matérialisé une fois**, voir §7.1 |
| `DEC-427`, `DEC-429` | Branche + PR obligatoires. `main` et `develop` protégées, **0 approbation** |
| `DEC-428` | **`v0.1.0` à `G1`**, tag annoté sur `main` |
| `DEC-439`, `DEC-453`, `DEC-457` | `node_modules`, `.venv` et caches exclus d'iCloud. **Non durable** : vois §7.1 |
| `DEC-440` | **Un seul environnement à la fois.** Limites mémoire par service |
| `DEC-441`, `DEC-455` | `pnpm` workspaces **et** workspace `uv` unique. Le `Makefile` orchestre |
| `DEC-442` | **`mypy` strict** |
| `DEC-443`, `DEC-458` | Versions épinglées, **empreinte `sha256` partout**, aucun `latest` |
| `DEC-444` | Compose base + surcouches, `COMPOSE_PROJECT_NAME` distinct |
| `DEC-445` | `ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}` |
| `DEC-446` | Caddy `tls internal` sur `app.` et `api.onboarding.localhost` |
| `DEC-447` | **Volumes nommés exclusivement.** Bind mount de configuration en lecture seule toléré |
| `DEC-451` | **ESLint** flat config + **Prettier**. `jsx-a11y` est le motif déterminant |
| `DEC-452` | « Exécutable » à `T1` = chaîne d'outils, pas application qui écoute |
| `DEC-454` | **Le Markdown est exclu de tout formatage automatique.** Vois §7.9 |
| `DEC-456` | Outillage posé par archive officielle, **empreinte SHA-256 vérifiée** |
| `DEC-459` | Healthcheck `api` sur `/health/ready`, `worker` sur ping du courtier |
| `DEC-460` | **Publications de ports sur `127.0.0.1` uniquement.** `make ports` le vérifie |
| `DEC-461` | `make env` génère 5 secrets locaux, en laisse 2 en `CHANGE_ME` |
| `DEC-462` | **API synchrone.** `uvicorn --factory`, configuration sur `app.state` |
| `DEC-463` | **Migration `0001_initial` vide.** Extensions au LOT 2, `QO-112` |
| `DEC-464` | Le garde-fou `CHANGE_ME` porte sur les variables que l'API **déclare** |
| `DEC-466` | Journalisation et masquage dans **`packages/observabilite`**, partagé |
| `DEC-467` | Rotation par le pilote `json-file`. **La conservation 30 jours n'est PAS couverte** |
| `DEC-468` | `resultat` prend **trois** valeurs : `succes`, `refus`, `echec` |
| `DEC-469` | **Jamais journalisés** : chaîne de requête, arguments de job, traces, accès uvicorn |
| `DEC-470` | **Page et API sur une SEULE origine**, mandatée par Caddy. Ni CORS, ni proxy Vite |
| `DEC-471` | Testing Library sur **`jsdom`**. `restoreMocks` et `unstubGlobals` actifs |
| `DEC-472` | Le `Caddyfile` est monté **par son répertoire**, et `make up` **recharge** Caddy |
| `DEC-473` | **`.dockerignore`** : `node_modules`, `.venv`, caches, `.git`, `docs/prototype`, `.env` |
| `DEC-474` | Audit : **une seule tolérance nommée**, `GHSA-mh99-v99m-4gvg`. Tout autre avis bloque |
| `DEC-475` | Workflow en **2 tâches + 1 porte**. Actions épinglées **par empreinte de commit** |
| `DEC-476` | **CI obligatoire sur `develop` ET `main`**, contexte unique, `strict` actif |
| `DEC-477` | **`make up` en deux temps** : bucket MinIO créé AVANT que l'API doive être saine |
| `DEC-478` | **Multiarchitecture sur `develop` ET sur les tags.** Le cahier §23.2 et §23.3 divergeaient |
| `DEC-479` | Image `web` à **2 cibles nommées**, socle d'exécution **Caddy**, **port 5173 conservé**. Chaque surcouche **nomme sa cible**, `make images-check` échoue sinon. `chown -R` supprimé des 3 images |
| `DEC-480` | **Version et révision gravées** dans l'image par `ARG`→`ENV`, + **4 étiquettes OCI**. Compose les transmet à `api` **et** `worker` |
| `DEC-481` | Étiquettes : `sha-<empreinte>`, `develop`, version exacte. **Aucun `latest` publié** — plus strict que les conventions §4.1 |
| `DEC-482` | **Trivy bloque sur `CRITICAL` corrigeable seulement**, et rapporte le reste visiblement |

## 4.14 Les séquences d'identifiants — à respecter absolument

Un identifiant n'est **jamais** réutilisé, **jamais** renuméroté, et un trou n'est **jamais**
comblé.

| Séquence | Étendue | Prochain libre |
|---|---|---|
| `DEC-nnn` | `001`–`417` **réservés**, `418`–`623` en usage | **`DEC-624`** |
| `ECART-nnn` | `001`–`068` | **`ECART-069`** |
| `QO-nnn` | `072`–`124`, **5 trous** | **`QO-125`** |
| `ROAD-RSK-nnn` | `001`–`034` | **`ROAD-RSK-035`** |
| `DEP-nnn` | `001`–`017` | **`DEP-018`** |
| `CONT-nnn` | `001`–`029` | **`CONT-030`** |

Trous jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090` (`ECART-011`).
**L'index à jour est dans [`docs/README.md`](docs/README.md) §4. Consulte-le avant de créer un
identifiant — et `make docs-check` échoue désormais si un marqueur ne correspond pas au maximum
réellement en usage. C'est ce contrôle qui aurait attrapé `ECART-021`.**

---

# 5. Constantes et variables à connaître

## 5.1 Outillage de la machine

| Élément | Valeur | Remarque |
|---|---|---|
| `gh` | **`~/.local/bin/gh`**, 2.96.0 | **Pas dans le `PATH`.** `export PATH="$HOME/.local/bin:$PATH"` |
| `uv` | **`~/.local/bin/uv`**, **0.11.32** | Posé en `T1`, archive officielle, **empreinte SHA-256 vérifiée** |
| Homebrew | `/opt/homebrew`, **inutilisable** | Appartient à `admin`. `test -w` échoue sur `bin` **et** `Cellar` |
| **Droits d'administration** | **AUCUN** | Mesuré le 29/07/2026 : `id -Gn` → `staff everyone localcounts…`, **pas de groupe `admin`**, et `sudo` répond « is not in the sudoers file ». Vois ci-dessous |
| Node / npm | **v24.16.0** / 11.13.0 | Via `nvm` |
| `pnpm` | **11.17.0**, par `corepack` | Épinglé par `packageManager` **avec empreinte d'intégrité** |
| Python | **3.12.13**, géré par `uv` | Le Python système 3.9.6 n'est **jamais** utilisé |
| Docker | 29.5.3, Compose **v5.1.4** | Pas de clé `version:`. **7,75 Gio alloués** |
| `make` | GNU Make **3.81** | Pas de `.ONESHELL`, pas de `$(file …)` |

## 5.2 Versions épinglées et images

Épinglage `majeur.mineur` dans les fichiers de version, **empreinte `sha256` dans les
`Dockerfile` et dans Compose**. **Aucune référence à `latest`**, contrôlée à chaque sous-étape.

| Rôle | Référence |
|---|---|
| db | `postgres:17.7@sha256:2006493727bd…` — **Debian, pas Alpine** : musl gère mal les locales. **Depuis `T1` du LOT 2, `POSTGRES_INITDB_ARGS` impose ICU `fr-FR`** (`DEC-497`) |
| redis | `redis:8.4-alpine@sha256:bd4a0d37e7cd…` |
| minio | `bitnamilegacy/minio:2025.7.23-debian-12-r5@sha256:6dabb4a2088c9a79…`, `user: root` — **bascule du 25/09/2026, `DEC-590`, hors lot**. `quay.io/minio/minio` a fermé l'accès anonyme le 24/09/2026, après le retrait de `minio/minio` de Docker Hub le 12/09/2026. Résiduel nommé : archive **gelée**, dernière version réelle datée du 23/07/2025, plus aucune mise à jour de sécurité à attendre — même classe que `ROAD-RSK-033` |
| mailpit | `ghcr.io/axllent/mailpit:v1.30@sha256:7f33095f80e9…` |
| caddy | `caddy:2.11-alpine@sha256:5f5c8640aae0…` |
| api, worker | `python:3.12-slim@sha256:78387bc3881b…` — **slim, pas Alpine** : roues absentes en musl. **Montée de `3.12.13` à `3.12.14-slim-trixie` le 14/09/2026, `DEC-581`**, et les deux `Dockerfile` portent désormais **une couche `apt` épinglée** : `perl-base=5.40.1-6+deb13u1`. **La montée seule n'aurait rien corrigé** — mesuré, le condensat amont porte encore la version vulnérable sur les **deux** architectures |
| web | `node:24.16-alpine@sha256:21f403ab171f…` |
| construction | `ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96…` |

> **Docker Hub applique une limite de débit anonyme.** Elle a fait échouer une inspection en
> `T2`. MinIO vient de **quay.io**, Mailpit de **ghcr.io** : leurs registres de publication, non
> limités. Si une inspection d'image échoue, **lis l'erreur** avant de conclure à une absence.

## 5.3 Les cibles du `Makefile`, et le paramètre qui les commande

> **Cette liste est indicative et `make help` fait foi.** Elle a annoncé « 53 cibles » alors qu'il y en avait 81 : un nombre recopié dans un titre vieillit à la première addition, et celui-là a vieilli de trente. **Dérive-le** : `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile`.

```text
Environnement   tools versions tree icloud-exclude icloud-verify install
Qualité         lint format format-check typecheck test test-unit test-integration check
                docs-check sources-check sources-temoin audit
                parametres-check parametres-temoin      ← hors lot, DEC-580
                (SANS BASE : les types viennent des METADONNEES, pas du
                 catalogue, donc le controle tourne dans la tache QUALITE.
                 Le moment ou il faut le savoir est la PULL REQUEST)
Stack           env env-check up down destroy ps logs health ports minio-bucket
                stack-check persistence-test caddy-reload caddy-recreate
API             migrate migrate-status api-check alembic-check
                code-refresh code-check                           ← LOT 2, T1
                historisation-check                               ← LOT 2, T9
                isolation-check isolation-temoin                  ← LOT 2, T11
                migrations-check recette-modele-check             ← LOT 2, T12
                roles-provision privileges-check                  ← LOT 3, T1
                secrets-check                                     ← LOT 3, T2
                entites-check                                     ← LOT 4, T1
                trombinoscope-check                               ← LOT 5, T2
                profil-check                          ← LOT 5, T4, T5, T7 et T8
                (NI T5, NI T7, NI T8 n'ajoutent de cible : les trois ETENDENT
                 profil-check, de 10 a 17 puis 26 puis 36 controles. Un second
                 verificateur aurait duplique le decor, la connexion et le
                 menage -- §7.27. Et aucune cible nouvelle = rien a ajouter
                 dans `ci.yml`, ce qui est le benefice direct de la lecon)
                permissions-check                                 ← LOT 4, T8
                (T9 n'ajoute AUCUNE cible : son garde-fou est prouve par
                 12 tests, pas par un controle de stack. Voir ECART-046)
                onboarding-check                                  ← LOT 7, T14
                (differe par T13, construite ici, combinee pour les deux --
                 14 controles sur la pile REELLE : l'asymetrie DSM/ESM, le
                 cycle de vie complet, ECART-066 eprouve dans le sens du refus)
                cadre-check cadre-temoin                          ← LOT 4, T3
                jeu-de-donnees                                    ← LOT 2, T12
                (ATTENTION : elle COMMITE 25 entites et 5 000 profils dans la
                 base visee, et n'a AUCUNE cible de nettoyage. Lancee sur la
                 base de DEV, elle fait echouer 66 tests d'integration qui
                 comptent des lignes en ABSOLU -- mesure du 12/09/2026, et
                 aucun des 66 messages ne nomme la cause. Remede : `make down`,
                 `docker volume rm onboarding-dev_db-data`, `make up`,
                 `make migrate`. PAS `make destroy`, qui emporte caddy-data)
Frontend        web-check test-frontend
Images          images-check images-build images-inspect images-verify images-push
                images-pin                                            ← T8
Recette (T8)    separations-check up-recette down-recette
                stack-check-recette recette-check
Nettoyage       clean clean-deps
Aide            help
```

> **DEPUIS `T8`, LES 15 CIBLES DE STACK SONT PARAMÉTRÉES PAR `ENVIRONNEMENT`**, dont `dev` est le
> défaut. `make up` reste `make up` ; `make up ENVIRONNEMENT=recette` lève la recette, et
> `make up-recette` en est l'alias. Les alias **délèguent** et ne portent aucune logique propre :
> deux copies d'une même recette divergent en silence, c'est `ECART-022` et `DEC-466`.
>
> **Un nom d'environnement fautif échoue à la LECTURE du `Makefile`**, avant toute action, et la
> liste des noms valides est **dérivée du disque** : `ENVIRONNEMENT=recete` répond
> « Environnements disponibles : dev recette ».
>
> `.env` sert le développement, `.env.recette` la recette — **déjà couvert par `.env.*` dans
> `.gitignore`, vérifié par `git check-ignore`**. Le modèle reste **unique**, `.env.example`, plus un
> **calque de différences versionné** par environnement : un second modèle divergerait
> — et le dire **sans nombre** est la formulation qui ne vieillit pas.
>
> **`make separations-check` exige que les DEUX stacks tournent.** C'est une exception bornée à
> `DEC-440`, motivée : l'épreuve d'isolement réseau serait sans valeur si la cible était arrêtée.

`make check` = qualité complète. `make stack-check` = santé des 8 services + ports.
`make web-check` = la page vue **comme un navigateur la voit**, à travers Caddy en HTTPS.
`make caddy-reload` est appelée par `make up` : **Caddy ne surveille pas son fichier**, et sans
rechargement il sert une configuration périmée en paraissant sain (`DEC-472`, défaut `T5-2`).
`make docs-check` recalcule les 5 empreintes SHA-256 des documents immuables et **échoue si un
marqueur d'identifiant libre ne correspond pas au maximum en usage**. `make audit` tolère **un**
avis nommé, `DEC-474`. **`make help` est la source de vérité**, pas cette liste.

**Les quatre cibles d'images, et laquelle a besoin de Docker.** `images-check` est **statique** :
elle n'ouvre aucune connexion au démon, tourne dans la tâche « qualité » de la CI, et est incluse
dans `make check`. `images-build` construit les 3 images pour les 2 architectures **en local**,
`--load`, puis appelle `images-inspect` — manifestes, utilisateur non privilégié, étiquettes OCI,
plafonds de taille. `images-verify` **lance** les conteneurs. `images-push` publie, et n'est appelée
que par le workflow. **`env-check` compare `.env` à `.env.example`** et nomme les variables
manquantes : elle existe parce que `make env` est idempotent et ne réconcilie **rien** — trois
variables manquaient depuis `T3` et `T4` (`ECART-022`).

**`make caddy-recreate` est le remède au piège du §7.17.** Elle recrée le seul conteneur Caddy pour
lui faire re-résoudre son montage lié.

## 5.4 Variables de `.env.example` — **v1.6**, `ECART-006` et `ECART-022` clos

**84 variables, 84 noms distincts, aucun secret.** `T1` du LOT 3 a ajouté les **quatre** des deux rôles du moindre privilège (`DEC-520`). `T8` a ajouté `CADDY_SITE_APP` et `CADDY_SITE_API`. **9** valent `CHANGE_ME` (`ECART-019` : la chaîne
apparaît 11 fois, mais deux occurrences sont des commentaires — compte le motif
`^[A-Z_][A-Z0-9_]*=CHANGE_ME`).

> **Ces trois nombres disaient « 83 », « 7 » et « quatre » jusqu'au 08/09/2026**, et le §5.4
> donnait lui-même la commande qui les démentait. **Le code était juste** — `composer-env.py`
> engendre bien **six** secrets depuis `DEC-520` — c'est ce paragraphe qui avait vieilli.
> `ECART-054`.

> **`ECART-022` : le fichier annonçait 78 variables et déclarait `APP_REVISION` DEUX FOIS**, en
> blocs strictement identiques. Dans un fichier de configuration, deux déclarations d'une variable,
> c'est **la dernière qui gagne, en silence**, le jour où elles divergent.
>
> **Et un défaut plus sérieux, dormant depuis `T3` :** `make env` ne touche **jamais** un `.env`
> existant — c'est voulu, il porte des secrets engendrés. Une variable ajoutée au modèle **après**
> la première création du `.env` n'y arrive donc **jamais**. Le `.env` de cette machine comptait
> **74 affectations contre 78** : `APP_REVISION` (`T3`), `LOG_MAX_SIZE` et `LOG_MAX_FILES` (`T4`) y
> manquaient. **Lance `make env-check` en début de session** : c'est la parade, et elle nomme les
> manquantes.

`make env` **génère localement** **six** secrets sur 48 caractères — `APP_SECRET_KEY`,
`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ROOT_PASSWORD`, et depuis `DEC-520`
`POSTGRES_MIGRATIONS_PASSWORD` et `POSTGRES_RUNTIME_PASSWORD` — plus un `MINIO_ROOT_USER` lisible.
La liste fait foi dans `SECRETS_ALEATOIRES` de `infra/scripts/composer-env.py`, pas ici. **Restent en
`CHANGE_ME`, et ce n'est pas un oubli** : `IMPORT_SOURCE_RETENTION_DAYS` (`QO-100`, bloquante,
LOT 9) et `UPTIME_KUMA_PUSH_URL` (LOT 13).

| Variable | Valeur par défaut |
|---|---|
| `APP_ENV` · `APP_VERSION` · `APP_REVISION` | `development` · `0.0.0-dev` · `inconnue`. **Gravées dans l'image depuis `T7`** (`DEC-480`), et Compose emploie des défauts explicites `${…:-…}` |
| `API_PREFIX` · `API_DOCS_ENABLED` | `/api/v1` · `true` — **`false` obligatoire en production** |
| `LOG_FORMAT` · `LOG_LEVEL` | **`json` obligatoire** · `info` |
| `LOG_RETENTION_DAYS` · `LOG_MAX_SIZE` · `LOG_MAX_FILES` | `30` (non consommée, `QO-113`) · `10m` · `5` |
| `POSTGRES_HOST` · `PORT` · `DB` · `HOST_PORT` | `db` · `5432` · `onboarding_dev` · `5432` |
| `REDIS_HOST` · `PORT` · `HOST_PORT` | `redis` · `6379` · `6379` |
| `MINIO_ENDPOINT` · `BUCKET` · `HOST_PORT` · `CONSOLE_HOST_PORT` | `minio:9000` · `onboarding-dev-media` · `9000` · `9001` |
| `SMTP_HOST` · `PORT` · `MAILPIT_HOST_PORT` | `mailpit` · `1025` · `8025` |
| `CADDY_HTTP_HOST_PORT` · `HTTPS_HOST_PORT` | `80` · `443` |
| `DRAMATIQ_QUEUES` | `default,emails,imports,media,exports,maintenance,security` |
| `DB_AUTO_CREATE` · `SESSION_COOKIE_SECURE` · `CSRF_PROTECTION_ENABLED` | `false` · `true` · `true` |
| `VITE_API_BASE_URL` | `/api/v1` |

## 5.9 LES TROIS COMPTES POSTGRESQL — à connaître avant toute requête

**Depuis `T1` du LOT 3 (`QO-116`, `DEC-520`), la base a trois comptes distincts.** Employer le
mauvais produit une erreur dont le message ne dit pas que le rôle est en cause.

| Compte | Variables | Ce qu'il peut | Qui l'emploie |
|---|---|---|---|
| `onboarding_app` | `POSTGRES_USER` / `POSTGRES_PASSWORD` | **tout** — superutilisateur créé par `initdb`, propriétaire du cluster | **`initdb` et `make roles-provision`. RIEN D'AUTRE.** |
| `onboarding_migrations` | `POSTGRES_MIGRATIONS_USER` / `_PASSWORD` | possède le schéma, crée et modifie les tables, installe `btree_gist` | **Alembic seul**, et les rares tests qui créent des objets |
| `onboarding_runtime` | `POSTGRES_RUNTIME_USER` / `_PASSWORD` | **lire et écrire des LIGNES** — rien de plus | l'API, le worker, et **tous** les tests d'intégration |

**En code :** `moteur(parametres)` rend le moteur d'**exécution**, `moteur_migrations(parametres)`
celui des **migrations**. `Parametres` expose trois URL, et `url_postgresql()` est celle de
l'application.

> **Ce que le rôle d'exécution REFUSE, mesuré et testé** : `CREATE TABLE` (« permission denied for
> schema public »), `DROP TABLE` et `ALTER TABLE` (« must be owner of table »), `CREATE ROLE`, et
> **`TRUNCATE`** — un DDL déguisé qui contourne les déclencheurs `ON DELETE`.
>
> **Un test qui crée une table doit employer `moteur_migrations()`.** Sinon il échoue sur
> « permission denied for schema public », et le message ne dit pas que la cause est le rôle. C'est
> ce qui est arrivé à neuf tests du socle en `T1`.

**Trois conséquences pratiques :**

1. **une base jetable doit être créée avec `OWNER <rôle de migration>`**, sinon Alembic n'y a aucun
   droit — `test_integration.py` et `verifier-migrations.py` le font ;
2. **les privilèges par défaut** couvrent les tables créées **par le rôle de migration**. Une table
   créée hors migration ne serait pas lisible par l'exécution, et c'est voulu ;
3. **`alembic_version` est une métadonnée de migration** : la lire avec la connexion des migrations.

```bash
make roles-provision    # idempotent, appelée par `make up`
make privileges-check   # EXIGE une base migrée, et le dit
```

---

## 5.5 Les 11 garde-fous de démarrage — **implémentés et testés**

`apps/api/app/configuration/settings.py`. **4 dans tous les environnements** : variable
obligatoire absente, `CHANGE_ME` résiduel, valeur typée invalide, `LOG_FORMAT` ≠ `json`.
**7 en production seule** : `APP_SECRET_KEY` d'au moins 32 caractères, `EMAIL_PROVIDER` ≠
`mailpit`, `API_DOCS_ENABLED=false`, `SESSION_COOKIE_SECURE=true`,
`CSRF_PROTECTION_ENABLED=true`, `DB_AUTO_CREATE=false`, `PUBLIC_BASE_URL` en `https://`.

**Le message nomme la variable, jamais sa valeur.** Un test l'éprouve.

## 5.6 Hôtes locaux et HTTPS

```text
app.onboarding.localhost   → 127.0.0.1   page NATIONALE depuis T6 du LOT 4 (DEC-549)
                                         la page de statut est passee a /statut
                                         + /health/* et /api/* mandates vers l'API (DEC-470)
api.onboarding.localhost   → 127.0.0.1   API, operationnelle depuis T3
```

macOS les résout **sans toucher à `/etc/hosts`** — vérifié, 0 occurrence dans le fichier.

**Depuis `T5`, la page et l'API partagent une origine** (`DEC-470`) : le bloc
`app.onboarding.localhost` mandate `/health/*` et `/api/*` vers `api:8000`, le reste vers
`web:5173`. Le frontend appelle donc `/health/ready` **en relatif**, sans CORS. Ne remets pas ce
montage en cause sans lire `DEC-470` : il existe pour que les cookies `Secure` et `SameSite` du
LOT 3 soient éprouvables.

> **✅ La racine de l'autorité interne de Caddy EST approuvée** depuis le 29/07/2026.
> `security verify-cert` sort en **0**, « certificate verification successful » — il sortait en
> **1**, `CSSMERR_TP_NOT_TRUSTED`, avant. `curl` **sans** `-k` aboutit désormais, la page répond
> 200, et elle a été **vue dans un vrai navigateur** : rendu complet, console sans erreur, cinq
> largeurs de recette sans débordement.
>
> **La commande qui figurait ici était fausse et ne pouvait pas fonctionner.** Elle employait
> `sudo` et le trousseau **système**, or Jonathan n'a **aucun droit d'administration** sur cette
> machine (§5.1). Le drapeau `-d` visait le magasin administrateur ; sans lui, `security` écrit
> dans le domaine **utilisateur**, et cela suffit. Si le volume `caddy-data` est un jour détruit,
> une nouvelle racine est engendrée et l'approbation doit être refaite — **c'est l'action de
> Jonathan**, elle demande son mot de passe **de session**, non celui d'un administrateur :
>
> ```bash
> docker cp onboarding-dev-caddy-1:/data/caddy/pki/authorities/local/root.crt /tmp/caddy-onboarding-root.crt && security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db /tmp/caddy-onboarding-root.crt
> ```
>
> Couvre Safari, Chrome et Edge. **Pas Firefox**, qui gère son propre magasin. Mes contrôles
> restent en `curl -k` : ils ne doivent pas dépendre d'une action humaine.
>
> **C'est aussi pourquoi `make destroy` n'est pas anodin** : il supprime `caddy-data` avec le
> reste. Pour éprouver une machine propre, supprime le **seul** volume utile — c'est ce que `T6` a
> fait pour reproduire le défaut du bucket MinIO.

## 5.7 Contrainte mémoire

| Grandeur | Valeur mesurée |
|---|---|
| RAM machine | 16 Gio |
| **RAM allouée à Docker** | **7,75 Gio** |
| Les 8 services, **code applicatif en marche** | **483 à 494 Mio, 6,1 à 6,2 %** — deux mesures du 29/07/2026, sous-étape `T7`. C'était 389 Mio en `T5` |
| Pour mémoire, les mêmes au repos en `T2` | 146 Mio, 2 % — `api`, `worker` et `web` attendaient |
| Le service le plus sollicité | `api`, à **9,0 %** de sa limite de 1 024 Mio |
| Limites déclarées | 6 144 Mio au total, **effectivement appliquées** |
| Images | `web` **1,02 Gio** — `ROAD-RSK-030` **aggravé** · `api` et `worker` 662 Mio |
| Projet tiers `observatoire-ecom-studio` | **arrêté** par `docker compose stop`, volumes intacts |

**La marge est confortable pour UN environnement**, et c'est tout ce qui est prouvé. `DEC-440`
n'autorise qu'un environnement à la fois ; la mesure de deux stacks simultanées relève de `T8`,
et c'est là que `QO-085` pourra se clore.

**Remise en route du projet tiers, quand le LOT 1 sera fini :**

```bash
docker compose -p observatoire-ecom-studio start
```

## 5.8 Images, registre et étiquettes — les constantes de `T7`

**Elles n'existaient pas avant `T7`. Toutes sont déclarées dans le `Makefile`, en une seule source
de vérité, et le workflow n'en redéfinit aucune.**

| Constante | Valeur | Où, et pourquoi cette valeur |
|---|---|---|
| `REGISTRE_IMAGES` | `ghcr.io/jonathan2433/onboarding-digital` | `DEC-445`. **Minuscules obligatoires** : GHCR refuse une majuscule dans un nom de paquet, alors que le compte s'écrit `Jonathan2433` |
| `PLATEFORMES_IMAGES` | `linux/amd64,linux/arm64` | Cahier §22.3, littéralement : `arm64` pour le Mac M5, `amd64` pour un futur serveur x86 |
| `IMAGES_SPEC` | `api::130 worker::130 web:execution:35` | `<service>:<cible>:<plafond Mio>`. **Une liste littérale, et non trois familles de variables** : une variable Make n'est **pas** visible du shell d'une recette, et l'indirection `$${CIBLE_$$service}` y vaudrait la chaîne vide — `web` n'aurait jamais reçu `--target execution`, **en silence** |
| `VERSION_IMAGE` · `REVISION_IMAGE` | `0.0.0-dev` · `inconnue` | Défauts. La CI passe la version et l'empreinte du commit réels |
| `ETIQUETTE_LOCALE` | `onboarding-local` | Les listes de manifestes construites **localement**. Jamais poussées |

**Les plafonds portent sur la taille de CONTENU, pas sur l'usage disque, et c'est mesuré.** Une
image a **deux** tailles qui diffèrent d'un facteur quatre : `api` `arm64` pèse **115 Mo de contenu**
et **473 Mo sur disque**. `T2` et `T5` citaient la seconde, `docker images` la rapportant.

> **Pourquoi la première, et le motif est décisif :** l'usage disque **n'est pas comparable d'une
> plateforme à l'autre**. `docker image ls --tree` annonce **473 Mo** pour la variante `arm64` et
> **114 Mo** pour la variante `amd64` de la **même** image — seule la variante native est dépaquetée
> localement. Un plafond fondé sur cette grandeur passerait ou échouerait selon l'architecture de
> l'exécuteur. C'est le défaut `T7-6`, et il a produit un plafond **4,5 fois trop large**.

**Étiquettes publiées** — `DEC-481`, conventions §4.1 :

| Étiquette | Quand | Usage |
|---|---|---|
| `sha-<empreinte courte>` | **toujours** | traçabilité, diagnostic, rejeu |
| `develop` | poussée sur `develop` | recette locale **seulement** |
| version exacte, `0.1.0` | tag `v*` | **seule** référence autorisée en production |
| ~~`latest`~~ | **jamais** | `DEC-481`, plus strict que les conventions. `make images-check` échoue si le mot apparaît |

> **Les étiquettes locales de Compose, `onboarding-dev-web:latest`, sont hors de cette
> interdiction** : Compose les engendre pour toute image construite sans étiquette explicite, elles
> ne sont jamais poussées, et c'est exactement le cas que les conventions §4.1 tolèrent. Le contrôle
> les distingue, avec témoin dans les deux sens — la première version criait au loup sur
> `runs-on: ubuntu-latest`, qui est un **label d'exécuteur**.

**Deux plateformes de plus, à connaître :**

- **`linux/s390x`** est la **plateforme témoin** du vérificateur. Elle est volontairement absente de
  nos manifestes, et le contrôle **exige que son inspection échoue** : sans cela, un
  `docker image inspect --platform` qui réussirait pour n'importe quelle valeur donnerait la même
  observation qu'un manifeste correct ;
- **`ARM64-COW-BUG`** est un avertissement Redis, supprimé **uniquement** sur le double jetable du
  vérificateur. Voir §7.18 — ne le porte **jamais** dans Compose.

**Le magasin d'images containerd est un prérequis mesuré.** `docker info` doit rapporter
`io.containerd.snapshotter.v1` : sans lui, `docker buildx build --platform … --load` refuse de
charger une liste de manifestes. Vérifié le 29/07/2026 sur cette machine.

---

# 6. La méthode de travail

## 6.1 La boucle

```text
1. Annoncer          ce qui va être modifié, pourquoi, les risques, le point de retour
2. Exécuter          une seule sous-étape, jamais deux
3. Contrôler         en lecture seule, après modification, avec témoins
4. Rapporter         au format imposé, avec les sorties réelles
5. Attendre          la validation explicite de Jonathan
6. Fusionner         une pull request par sous-étape, squash, JAMAIS EMPILEE
7. REFERMER l'issue  A LA MAIN : `Closes #N` ne marche pas depuis develop, voir §7.19
```

**L'étape 7 n'est pas une formalité et elle a été oubliée à la fusion de `T7`.** Le commentaire de
fermeture est aussi l'endroit où cocher les critères d'acceptation avec leurs preuves, ce que le
backlog §11 exige.

**Et l'étape 6 porte « JAMAIS EMPILÉE » depuis `T1` du LOT 5, où le coût a été payé.** J'avais ouvert
la pull request de `T1` sur la branche d'ouverture du lot, non encore fusionnée, pour que son diff
montre exactement la sous-étape. Deux conséquences, toutes deux mesurées :

| Conséquence | Mesure |
|---|---|
| **aucune intégration continue** | `ci.yml` filtre `branches: [develop, main]` : une pull request visant une autre base n'en déclenche **aucune**. Ce n'était pas « pas encore là » — c'était structurel |
| **fermée d'office, sans avertissement** | la fusion de la base avec `--delete-branch` a **supprimé** la branche de base, et GitHub a **clos** la pull request. `gh pr reopen` refuse ensuite : « Could not open the pull request » |

**Une sous-étape part toujours de `develop`.** Si elle dépend d'un travail non fusionné, attends la
fusion — et le rebase se fait `--onto origin/develop <ancienne base>`, puis on vérifie le **diff**,
pas le verdict du rebase (§7.24).

## 6.2 Le format de rapport imposé

```text
État du lot · Sous-étape en cours · Travail réalisé · Contrôles exécutés · Résultats
Décisions ajoutées ou modifiées · Risques et écarts · Questions ouvertes
Validation demandée à Jonathan
```

Termine par la **commande de fusion** et celle de **retour arrière** :

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```

**Vérifie toujours `git status -sb` avant d'annoncer un point de retour.**

## 6.3 Les questions à Jonathan

Utilise **l'outil de question** : 2 à 4 options, la recommandée en premier avec
« (Recommandé) », et une description qui explique la **conséquence**.

**Jonathan a répondu « je ne comprends pas la question » deux fois pendant ce lot.** La cause
était la même : la question employait un vocabulaire technique sans dire ce qui changeait pour
lui. Quand cela arrive, **reformule sans jargon, explique ce que chaque option engage
concrètement, et dis qui décide de quoi.** N'insiste pas sur la formulation initiale.

Ne l'interroge que si la réponse change réellement le travail. S'il demande qu'un point reste en
suspens, **adapte la conception** pour qu'il reste ouvert sans bloquer, et ouvre une question au
registre. C'est ce qui a produit `DEC-434`, `QO-111`, `QO-112` et `QO-113`.

## 6.4 Générer plutôt que transcrire

Pour tout volume — 44 tâches, 68 codes d'erreur, 8 issues, 8 empreintes d'images — **génère
depuis la source par script** au lieu de recopier.

## 6.5 Ne jamais inventer ce qui n'est pas décidé

**C'est la règle la plus utilisée de ce lot.** Trois fois, la fiche annonçait un contenu que le
corpus ne définissait pas. Trois fois, la bonne réponse a été d'ouvrir une question :

- les **extensions PostgreSQL** de `0001_initial` : aucun document n'en nomme une seule →
  migration vide, `QO-112` ;
- le **fournisseur de collation** PostgreSQL : le modèle §26.1 le laisse ouvert → valeurs par
  défaut, `QO-111` ;
- la **conservation calendaire** des journaux : le pilote Docker ne sait pas le faire → dit
  explicitement, `QO-113`.

**Une hypothèse déguisée en décision est pire qu'une case vide.**

---

# 7. Les erreurs à ne plus commettre

**279 défauts NOMMÉS au 24/09/2026** : **71** au LOT 1, **44** au LOT 2, **57** au LOT 3, **19** au LOT 4, **62** au LOT 5 et **26** au LOT 6 — 71 + 44 + 57 + 19 + 62 + 26,
dérivés par la commande ci-dessous et non recopiés. **Le « 15 au LOT 3 » qui figurait ici était faux** :
il datait de `T2`, et le total de 172 qui l'accompagnait était juste, ce qui rendait l'erreur invisible
à la lecture. S'y ajoutent 7 au LOT 0 et 3 en `T0`, qui ne portent pas de marqueur `Tn-m` et n'entrent
donc pas dans la dérivation. Ils sont tous dans les comptes rendus de sous-étape, et **presque tous étaient dans
mes propres contrôles** — c'est la forme la plus insidieuse, parce qu'on croit avoir prouvé.

> **Le second nombre est DÉRIVÉ, et il l'est parce que j'ai d'abord écrit « 39 » de tête** — 33 + 6,
> où le 33 était lui-même un calcul non vérifié. La commande fait foi :
>
> ```bash
> grep -ohE '`T[0-9]+-[0-9]+`' docs/operations/compte-rendu-t*-lot-2.md | sort -u | wc -l
> ```
>
> Elle compte les défauts **nommés**, lot par lot :
>
> ```bash
> for l in 1 2 3 4 5 6; do grep -ohE '`T[0-9]+-[0-9]+`' docs/operations/compte-rendu-t*-lot-$l.md \
>   | sort -u | wc -l; done
> ```
>
> Quelques défauts sont décrits **sans identifiant** dans les comptes rendus de `T6` et `T7` du LOT 2 :
> le compte est donc un **minorant**, et le dire vaut mieux que de laisser croire à un total exact.
> Classe `ECART-021`, pour la énième fois.

## 7.0 La règle qui résume tout

> **Un contrôle qui ne peut pas échouer ne prouve rien. Un contrôle dont on ne lit pas le code
> de sortie ne prouve rien non plus. Un contrôle qui n'annonce pas combien d'éléments il a
> examinés peut toujours n'en avoir examiné qu'un. Et un contrôle dont l'échec produirait la
> même observation que le succès ne prouve rien, quel que soit le nombre d'éléments comptés.**

Les troisième et quatrième propositions sont l'apport de ce lot. Parades, toutes deux mécaniques :
**compter, et confronter le compte à un attendu** ; puis **se demander quelle valeur produirait
l'échec**.

La quatrième vient de `T5-6`. Mon contrôle annonçait « 7 modules sur 7 résolus » et avait bien
examiné 7 modules — mais il concluait sur un **code HTTP 200**, or Vite répond 200 avec
`index.html` pour tout chemin inconnu : un module absent aurait donné la même observation. La
parade du lot était respectée, et le contrôle ne prouvait rien. Corrigé en discriminant sur le
**type MIME**. Même mécanisme que `T2-5`, où un Mailpit vide et un volume effacé donnaient tous
deux `{"total":0}`.

**C'est le témoin négatif qui les révèle** : quand il **passe** alors qu'il devait échouer, ce
n'est pas le témoin qui est mauvais, c'est le contrôle qui ne discrimine pas.

**Cinquième proposition, apport de `T6` — elle ne porte plus sur les contrôles mais sur les
corrections :** avant d'appliquer un correctif, mesure **ce que le correctif casse**. Un avis de
sécurité désigne un problème, jamais une solution. En `T6`, forcer la version « corrigée » de
`brace-expansion` aurait neutralisé ESLint, donc `jsx-a11y`, donc le seul garde-fou
d'accessibilité du projet — pour un déni de service théorique dans une dépendance de
développement. Seul le fait d'installer la version et de l'appeler l'a montré.

**Sixième proposition, apport de `T7` — et elle attrape un contrôle que les cinq autres laissaient
passer :** un contrôle qui compare deux nombres doit prouver qu'ils mesurent **la même grandeur**.

Mon contrôle de plafond de taille pouvait échouer, on lisait son code, il annonçait combien
d'éléments il avait examinés, et l'échec aurait produit une observation différente du succès —
**les cinq propositions étaient respectées**. Et il ne prouvait rien : il comparait une **taille de
contenu** de 109 Mio à un plafond de 500 Mio calibré sur l'**usage disque**. Un facteur 4,5, donc un
plafond qui passait quoi qu'il arrive. La question qui manquait : *le nombre que j'affiche et le
seuil auquel je le compare mesurent-ils la même chose ?*

**Et un septième point, qui n'est pas une proposition mais un interdit.** En `T7` j'ai écrit une
**empreinte SHA-256 inventée** dans un workflow, comme « garde-fou secondaire » de l'installation
de Trivy. Aucune des six propositions ne l'attrape : le contrôle aurait « fonctionné ». Une valeur
plausible plutôt que mesurée, dans un contrôle de sécurité, **fabrique la preuve au lieu de la
produire**. N'écris jamais une empreinte, un compte ou une mesure que tu n'as pas relevée.

## 7.1 iCloud : le risque s'est matérialisé

`ROAD-RSK-026` n'est plus théorique. Chronologie sur horodatages d'inode :

| Moment | Fait |
|---|---|
| 27/07 **17:21:19** | Création d'un **`node_modules 2`** — copie de conflit iCloud, 178 Mio, 11 066 fichiers |
| 27/07 **23:30:28** | Changement de métadonnées sur les deux, **sans aucune action de session** |
| 28/07 matin | La **copie** portait l'attribut d'exclusion, l'**original** l'avait perdu |

**L'attribut d'exclusion n'est pas durable.** `make icloud-verify` l'a détecté — pas une
inspection manuelle. Risque résiduel **accepté** par `DEC-457`.

```bash
make icloud-verify   # en DEBUT DE SESSION, ce n'est pas une formalite
```

**QUATRE** motifs sont exclus dans `.gitignore` — `* [0-9]` et `* [0-9][0-9]` pour les
**répertoires**, `* [0-9].*` et `* [0-9][0-9].*` pour les **fichiers** — plus `.prettierignore`,
Ruff et ESLint. `icloud-verify` **échoue** s'il trouve une telle copie, **à toutes les
profondeurs**, et il **exige en plus** que `git check-ignore` ignore effectivement quatre noms
témoins. **Les deux motifs de fichier manquaient jusqu'au 23/08/2026, et 115 fichiers sont entrés
dans un commit** : `ECART-038`, `DEC-542`, et la leçon est au §7.34.

## 7.2 Les espaces dans le chemin — **4 occurrences, dont une en `T7`**

Le dépôt vit sous `~/Library/Mobile Documents/`. **`$(CURDIR)` contient une espace.**

| Où | Symptôme |
|---|---|
| `Makefile`, `--env-file $(ENV_FILE)` non cité | `couldn't find env file: /Users/.../Library/Mobile` |
| Scripts, `eval docker compose … "$@"` | `eval` redécoupe les arguments, un `sh -c '…'` explose |
| Shell ad hoc, `DC="docker compose --env-file $PWD/.env …"` | `code=127`, **la commande n'a jamais tourné** |
| **`T7`, le même `DC="…"` exactement** | `code=127`, et je venais de citer ce piège dans mon propre rapport |

```bash
# TOUJOURS citer :
docker compose --env-file "$PWD/.env" -f fichier.yml "$@"
# JAMAIS eval pour assembler une commande dont un argument est cité.
# Une FONCTION shell, jamais une variable :
dc() { docker compose --env-file "$PWD/.env" -f base.yml -f dev.yml "$@"; }
```

Dans les scripts, le montage retenu : `$COMPOSE_FILES` **non cité** — le découpage est voulu,
ces chemins n'ont pas d'espace — et `$env_file` **cité**. Le script **refuse de continuer** si un
chemin Compose contient une espace.

> **La parade que `T7` a retenue, et c'est la seule qui ne dépende pas de ta mémoire.** Ce piège a
> été commis quatre fois, dont deux fois par un agent qui l'avait lu le jour même. Les contrôles de
> `T7` sont donc écrits en **Python**, avec `subprocess.run([...])` et sans `shell=True` : les
> arguments sont passés tels quels, **aucune redécoupe n'a lieu**, et `returncode` ne peut pas être
> celui d'un autre maillon. Le piège n'y **existe pas**. Quand une classe d'erreur résiste à la
> vigilance, change d'outil au lieu de promettre d'être plus attentif.

## 7.3 Le code de sortie — **7 occurrences**, et la dernière est d'un autre type

```bash
sortie=$(commande 2>&1); code=$?          # correct... SAUF sous `set -e`
if commande | sed 's/x/y/'; then …        # teste sed, JAMAIS commande
echo "code=$?"   # apres un tuyau : c'est le code du DERNIER maillon
```

En `T4`, j'ai lu « build code=0 » alors que le build venait d'échouer : la stack est remontée
sur les **anciennes images** en affichant « 8 services sains ». En `zsh`, `${pipestatus[1]}`
donne le code du premier maillon.

> **`T7` a ajouté une sixième occurrence, et elle n'est PAS un tuyau.** Le journal de chaque étape
> GitHub Actions porte `shell: /usr/bin/bash -e {0}` : **`-e` est déjà actif, et `set -uo pipefail`
> ne le retire pas.** Un `commande ; code=$?` fait donc sortir bash **à l'échec de la commande, avant
> la lecture du code**. Mon étape échouait sans produire **une seule ligne de sortie**, alors que
> c'était un contrôle dont **l'échec de la commande était le résultat attendu** — prouver qu'un
> tirage anonyme du registre est refusé.
>
> ```bash
> # Dans une étape de workflow, pour une commande dont l'échec est ATTENDU :
> sortie=$(commande 2>&1) && code=0 || code=$?
> ```
>
> **Et cela dit la limite du remède du §7.2.** Écrire les contrôles en Python immunise le
> vérificateur ; les étapes d'un workflow restent du shell, avec un `-e` qu'on n'a pas écrit. Un
> remède structurel ne couvre que le périmètre où il s'applique, et il faut savoir dire où il
> s'arrête.

## 7.4 Les contrôles qui sous-couvrent — **3 occurrences**

| Contrôle | Ce qu'il annonçait | Ce qu'il avait examiné |
|---|---|---|
| `make ports` | « aucune exposition hors de 127.0.0.1 » | **5 publications sur 7** |
| Persistance | « les 5 volumes ont survécu » | **1 empreinte sur 5** |
| Témoin Mailpit | « identique » | `{"total":0}` — **un volume effacé aurait donné la même valeur** |

Causes : un découpage qui ne gardait que la première correspondance ; un `docker compose exec`
qui **consommait l'entrée standard** dans une boucle `while read` ; un témoin dont la valeur
initiale était indistinguable de l'échec.

```bash
# Lire un fichier dans une boucle qui lance des commandes : descripteur 3
while IFS= read -r ligne <&3; do commande </dev/null; done 3< "$fichier"
# Puis COMPARER le nombre examine au nombre attendu, et echouer sinon.
```

## 7.5 `zsh` ne découpe pas les variables en mots — **rejoué trois fois en une seule session**

```bash
CIBLES="a b c"
for d in $CIBLES; do …   # UNE seule iteration en zsh, sur "a b c"
```

En `T1`, cela a créé un répertoire portant huit noms concaténés. Le `Makefile` force
`SHELL := /bin/bash` pour cette raison. Ailleurs : boucle `while read` sur un document en ligne,
**et comptage des itérations**.

## 7.6 `2>/dev/null` masque les erreurs qu'il faut lire

Ma sonde d'empreintes d'images signalait `caddy:2-alpine` **ABSENT**. Le registre renvoyait
**429 Too Many Requests**. J'aurais conclu qu'une image officielle n'existe pas.

**Ne supprime jamais l'erreur d'un contrôle dont tu vas interpréter le silence.**

## 7.7 Un livrable difficile à tester est un livrable qu'on ne teste pas

Deux défauts en `T3`, tous deux corrigés **pour rendre les tests possibles**, et qui ont produit
un meilleur code :

- `app/main.py` finissait par `application = creer_application()` : importer le module lisait
  l'environnement, et la **collecte** des tests échouait → `uvicorn --factory` ;
- les routes lisaient un cache global : impossible de tester « `ready` répond 503 » sans arrêter
  des services → configuration portée par `app.state`.

## 7.8 Un test faux — 3 occurrences

- un test qui **court-circuite le point d'entrée réel** ne prouve pas ce qu'il croit ;
- un test qui cherche `court` échoue sur le libellé légitime « plus **court**e que 32
  caracteres », pas sur une fuite ;
- un test de filtre de sécurité doit énumérer **les formes réellement produites par ce projet**,
  pas des exemples de documentation. C'est ainsi qu'a été trouvé le trou de `T4-1` :
  `redis://:motdepasse@` — le format exact de `url_redis()` — **passait à travers le filtre**.

## 7.9 Un formateur a failli réécrire les documents immuables

Mesuré, exclusion neutralisée : **Prettier réécrivait les cinq documents de cadrage**, ajoutant
**54 661 octets** au seul cahier des charges, soit **+21,7 %**. Ruff voyait **41 Markdown** au
lieu de 4 fichiers Python.

La preuve d'intégrité SHA-256 — élément de la porte `G0` — aurait été invalidée **sans qu'aucun
contrôle existant ne le signale**, le contenu restant sémantiquement identique.

**Le Markdown est exclu de tout formatage automatique** (`DEC-454`). `ROAD-RSK-029` reste ouvert :
tout outil ajouté plus tard rouvrirait le risque. **Recommandation pour `T6` : un contrôle de CI
qui recalcule les cinq empreintes et échoue si l'une diffère.**

## 7.10 Les outils changent, la documentation vieillit

| Ce que je croyais | Ce qui est |
|---|---|
| `store-dir` se déclare dans `.npmrc` | **pnpm 11 ne lit plus ces clés depuis `.npmrc`** → `pnpm-workspace.yaml` |
| `reactHooks.configs['recommended-latest']` est en flat config | Il est en `eslintrc`, **ESLint 10 le refuse** → `configs.flat.recommended` |
| `defineConfig` de `vite` connaît la clé `test` | **Non**, avec Vitest 4 → `vitest/config` |
| `bash` est disponible dans une image Node | **Non**, `node:alpine` n'a que `sh` |
| L'image MinIO contient `grep` | **Non** → `mc stat`, pas `mc ls \| grep` |
| Vite sert le dev server sur toutes les interfaces | **Non**, défaut `localhost` → `server.host` à `0.0.0.0`, sinon injoignable en conteneur |
| Vite accepte n'importe quel en-tête `Host` | **Non**, Vite 8 installe un contrôle d'hôte dès que le serveur n'est pas lui-même en HTTPS → `server.allowedHosts` |
| Vite renvoie 404 sur un chemin inconnu | **Non**, il renvoie **200 + `index.html`** → discrimine sur le type MIME, jamais sur le code |
| `@testing-library/dom` vient avec `@testing-library/react` | **Non** depuis la v16, c'est un **pair** à installer explicitement |
| `pnpm` lit `auditConfig` dans `package.json` | **Non**, pnpm 11 lit ses réglages d'espace de travail dans **`pnpm-workspace.yaml`** — comme `storeDir` en `T1`. Même classe, autre clé |
| Une liste blanche Gitleaks est comparée à la ligne | **Non**, au **secret capturé** seul. Sans `regexTarget = "match"`, un motif écrit sur la ligne ne correspond à rien |
| `brace-expansion` 5.x remplace 1.x sans risque | **Non**, son export CommonJS est un **objet** portant `.expand`, non une fonction. `minimatch@3` casse |

**Inspecte les exports réels avant de les utiliser**, ne te fie pas à ta mémoire d'une API.

## 7.11 Vérifier ce que la documentation affirme

Ce lot a corrigé **huit** affirmations fausses du corpus, presque toutes des nombres non dérivés
de la source : le bandeau « LOT 1 non ouvert » après son ouverture (`ECART-017`), « 8 contrôles
de CI » là où le cahier en énumère **11** (`ECART-018`), « 9 placeholders `CHANGE_ME` » là où il y
en a **7** (`ECART-019`), les décisions de `T0` bornées à `DEC-447` au lieu de `DEC-449`, et les
quatre de `ECART-021` : **131 tests au lieu de 139** dans deux documents, « 30 tests » de masquage
non reproductible, les compteurs de commits et de lignes de ce document, et un **« prochain
identifiant libre : `DEC-451` »** dans le registre des décisions alors que `DEC-469` était en
usage — **19 décisions de retard**, donc une collision garantie pour qui s'y fierait.

Une affirmation fausse qui n'était pas un nombre, et celle-là a coûté du temps :
**`CLAUDE.md` §9.3 affirmait « `Caddyfile` inchangé : le mandatement existe déjà »**, alors
qu'aucune route n'y menait à l'API. Voir §9.0.

**Vérifie l'état réel par `git`, `gh` et les mesures. Et dérive les nombres de la source.**
`T6` doit poser en CI un contrôle qui les recalcule et échoue s'ils divergent — recommandation de
`ECART-021`, à joindre à celle de `ROAD-RSK-029` sur les cinq empreintes SHA-256.

## 7.12 Outils macOS différents de GNU

| N'existe pas | Utiliser |
|---|---|
| `cat -A` | `cat -vet` |
| `grep -P` | `grep -E` ou Python |
| `timeout` | rien d'équivalent |
| `sed -i` sans argument | `sed -i ''` |

`grep` est ici **`ugrep`**, qui échoue avec « exceeds complexity limits » sur certains motifs.
**Passe par Python** pour les extractions non triviales. Le système de fichiers est **insensible
à la casse** : tout renommage ne différant que par la casse exige deux temps.

**Depuis `T6`, ce n'est plus seulement une gêne locale : tout ce que tu écris tourne aussi sur un
exécuteur Linux.** Deux pièges mesurés le 29/07/2026 :

| Sur macOS | Sur Linux |
|---|---|
| `sed -i ''` fonctionne | **GNU sed échoue en code 2** : il lit le script comme un nom de fichier. Emploie `sed … > f.tmp && mv f.tmp f` |
| `app.onboarding.localhost` se résout | **`gaierror`, aucune adresse.** Linux ne résout pas les sous-domaines de `.localhost`. Le workflow pose deux lignes dans `/etc/hosts` |

Écris désormais du shell **portable**, et fais-le vérifier par la CI.

## 7.13 Ne jamais `grep` le prototype en entier

`V1.html` fait 2,83 Mo dont **2,64 Mo de Base64**. Travaille sur une version dépouillée, hors
du dépôt.

## 7.14 Ne jamais manipuler les identifiants de Jonathan

`git` et `gh` savent s'authentifier seuls. **N'extrais jamais le jeton du trousseau macOS**, et
**n'entre jamais d'identifiants à sa place** — `gh auth login`, mot de passe `sudo`, approbation
de la racine Caddy dans le trousseau sont **ses** actions.

## 7.15 Un service peut être sain et servir une configuration périmée

Trois pièges découverts en `T5`, tous les trois **silencieux** : rien n'échouait, tout paraissait
correct.

**1. Un bind mount de FICHIER unique épingle l'inode.** La plupart des éditeurs n'écrivent pas en
place : ils écrivent un temporaire puis renomment, ce qui produit un inode neuf. Le conteneur
continue de pointer vers l'ancien, désormais supprimé — `ls` affiche encore l'entrée, mais toute
ouverture répond « No such file or directory ». Mesure : le conteneur voyait un `Caddyfile` de
**1 573 octets** quand l'hôte en portait **2 844**, et Caddy servait donc une configuration
périmée **en étant `healthy`**, son API d'administration répondant très bien — sur l'ancienne
configuration.

```yaml
- ../caddy:/etc/caddy:ro      # le REPERTOIRE : le chemin est resolu a chaque ouverture
- ../caddy/Caddyfile:/etc/caddy/Caddyfile:ro   # le FICHIER : epingle l'inode, ne fais plus ca
```

**2. Compose ne recrée pas un conteneur quand seul le CONTENU du fichier monté change, et Caddy ne
surveille pas son fichier.** `make up` appelle donc `caddy-reload`. Si tu modifies le `Caddyfile`
et que rien ne change, c'est là qu'il faut regarder.

**3. Aucun `.dockerignore` n'existait avant `T5`.** `COPY apps/web ./apps/web` recopiait le
`node_modules` de l'**hôte** par-dessus celui de l'image. Non actif — les liens sont relatifs et
pointent vers le magasin du conteneur — mais l'hôte résout `darwin-arm64` là où l'image résout
`linux-arm64-musl`. Le défaut est resté invisible tant qu'aucune image n'avait besoin
d'**exécuter** le code copié.

**La leçon commune :** un healthcheck qui interroge un service ne dit rien de la **configuration**
que ce service a chargée. Compare toujours l'état chargé au fichier présent.

## 7.16 Ce qui n'a jamais tourné ailleurs n'est pas éprouvé

**Leçon centrale de `T6`, et elle vaut pour tout ce que tu écriras.** Le `Makefile` fonctionnait
depuis `T1` — sur **une** machine, sous macOS, avec des volumes **déjà peuplés**. La première
exécution sur un exécuteur neuf a révélé deux défauts qui n'étaient pas des régressions, mais des
**conditions jamais rencontrées** :

1. **`make env`** employait `sed -i ''`. GNU sed échoue. Toute la tâche « stack » cassait.
2. **`make up` n'avait jamais fonctionné sur une machine propre.** La sonde `ready` de l'API fait
   un `head_bucket` ; sans bucket elle répond 503, `api` n'est jamais sain, `up --wait` échoue. Or
   le bucket n'était créé qu'**après** cette attente. En local le volume `minio-data` survit à
   `make down`, et le bucket y était déjà : le défaut ne pouvait pas se montrer.

Le second aurait attendu **`T9`** pour se manifester, sur le critère « les procédures fonctionnent
depuis une machine propre » — et il aurait alors fallu comprendre pourquoi la stack ne démarre pas
chez quelqu'un d'autre. `DEC-477` le corrige, et **`T8` devra reproduire cet ordre** dans la
surcouche de recette.

**Pour éprouver une machine propre sans tout casser :** ne lance pas `make destroy`, qui
supprimerait `caddy-data` et l'approbation du certificat avec. Supprime le **seul** volume utile.

---

## 7.17 Monter le répertoire ne suffit pas : iCloud remplace aussi les répertoires

**Découvert en `T7`, et cela élargit le périmètre de `DEC-472`.** `make up` a échoué : le conteneur
`caddy` voyait un `/etc/caddy` **vide** alors que l'hôte portait bien son `Caddyfile`.

| Fait | Mesure du 29/07/2026 |
|---|---|
| Conteneur `caddy` créé à | **09:51:38** |
| `ctime` de `infra/caddy` **et** de `infra/caddy/Caddyfile` | **10:06:49**, 15 min plus tard |
| Action de session à 10:06:49 | **aucune** — même signature que le 27/07 à 23:30:28 |
| Conteneur **neuf** sur la même source | voyait le fichier sans peine, 2 844 octets |

**`T5` avait résolu le remplacement du FICHIER par un éditeur, en montant le répertoire. Cela ne
protège pas du remplacement du RÉPERTOIRE par iCloud** : un conteneur ne re-résout **pas** la source
d'un montage lié après sa création. Et pendant ce temps, les huit services étaient `healthy` et
Caddy servait la configuration chargée à 09:51.

```bash
make caddy-recreate   # le seul geste qui repare : le conteneur re-resout son montage
```

**`caddy-reload` compare désormais l'empreinte SHA-256 du `Caddyfile` vu par le conteneur à celle
de l'hôte**, et ne masque plus son erreur — elle annonçait « configuration invalide ou service
absent » là où le message réel était « no such file or directory ». Deuxième leçon, donc : le piège
du §7.6 était dans un contrôle que le projet avait lui-même écrit.

---

## 7.18 Diagnostiquer avant de corriger — `T7` y a perdu trois cycles

**Le défaut le plus coûteux de `T7`, et il n'était pas technique.** Ma sonde du worker échouait sous
émulation. J'ai corrigé **deux fois** sans avoir diagnostiqué :

| Tentative | Hypothèse | Résultat |
|---|---|---|
| 1 | une course : Redis pas encore prêt | j'ajoute une attente → échoue toujours |
| 2 | l'attente est trop courte | j'allonge à 120 s → « **JAMAIS en 120 s** » |
| 3 | **je fais dire au contrôle l'état de la dépendance qu'il démarre** | `exited code=1`, et le journal donne la cause en une ligne |

La cause : **sous QEMU, Redis détecte le bug copie-sur-écriture d'ARM64 et sort exprès**, pour ne pas
corrompre ses données. Aucune attente n'y pouvait rien. Trois cycles d'intégration continue — une
heure — pour un problème que le premier journal aurait nommé.

> **La leçon, sans jargon :** quand un contrôle échoue et que tu ne sais pas pourquoi, **la première
> correction à écrire est celle qui te le dira.** Un contrôle qui masque la cause de son échec ne
> coûte pas un message : il coûte des cycles entiers. C'est le §7.6 à l'échelle d'une sous-étape.

**Et une précaution sur le correctif retenu**, parce qu'on pourrait le généraliser à tort :
`--ignore-warnings ARM64-COW-BUG` **supprime un garde-fou contre la corruption de données**. Il est
posé sur le **double jetable** du vérificateur — sans donnée, `--save ""`, le temps d'un `PING` — et
**vérifié absent des fichiers Compose, 0 occurrence dans les YAML**. Le Redis du projet tourne
nativement sur `aarch64` et n'a jamais déclenché cet avertissement. **Ne le porte pas dans
`docker-compose.base.yml`** : ce serait exactement la classe de correctif que `T6-7` a appris à
mesurer avant d'appliquer.

---

## 7.19 `Closes #N` ne referme pas une issue depuis `develop`

**Constaté à la fusion de `T7`.** La pull request `#23` portait `Closes #7` ; après fusion, l'issue
`#7` était **toujours ouverte**.

GitHub n'applique le mot-clé que pour une fusion dans la branche **par défaut**, ici `main`. Or
**toutes** les fusions du LOT 1 vont dans `develop` : aucune ne referme son issue automatiquement.

```bash
gh issue close <n> --comment "…"   # a faire A LA MAIN, apres chaque fusion
```

Les sous-étapes précédentes le faisaient déjà sans que ce soit écrit. **C'est une routine à tenir
jusqu'à `T11`**, pas un incident — et le commentaire de fermeture est le bon endroit pour cocher les
critères d'acceptation avec leurs preuves, ce que le backlog §11 exige.

## 7.20 Un contrôle qui échoue sur un livrable conforme : ne l'affaiblis pas

**Découvert en `T8`, et c'est la leçon la plus utile de cette sous-étape.** Mon contrôle
d'isolement réseau exigeait que la base du développement soit injoignable depuis la recette. Il a
échoué. Le livrable était pourtant conforme au cahier.

**J'ai diagnostiqué avant de corriger** — leçon `T7-13` — et l'épreuve décisive a porté sur un
**même conteneur**, ce qui élimine toute cause propre à un service :

| Cible | Publié sur l'hôte ? | Depuis la recette |
|---|---|---|
| `dev mailpit 172.20.0.4:8025` | **oui** | **JOIGNABLE** |
| `dev mailpit 172.20.0.4:1025` | non | `TimeoutError` |

**Docker installe pour chaque port publié une règle `ACCEPT` dans la chaîne `FORWARD`, et elle
précède ses règles `DOCKER-ISOLATION`.** Le paquet est accepté avant que l'isolement n'ait la
parole. Le préfixe `127.0.0.1` de `DEC-460` protège du réseau local et du pare-feu de macOS ; il ne
protège **pas** d'un autre réseau Docker de la même machine.

**Le cahier §22.2 exige un « réseau distinct », pas l'inatteignabilité mutuelle.** Mon contrôle
exigeait donc plus que le critère. Trois réactions possibles, et une seule est bonne :

- le **supprimer** — on perd l'information ;
- l'**affaiblir** en le faisant porter sur les noms de réseau — il ne prouverait plus rien ;
- **le faire dire le vrai**, ce qui a été retenu.

> **La règle, sans jargon :** fais-lui **exiger** ce qui est exigible — noms, sous-réseaux, DNS, et
> les ports **non publiés** ; **rapporter visiblement** ce qui ne l'est pas, en le nommant ; et
> **exiger la barrière** qui rend le résiduel acceptable. Ici c'est la cinquième séparation : avec
> le mot de passe de la recette, la base de dev **refuse**. Une barrière qui rend un résiduel
> acceptable doit être un **contrôle**, jamais une affirmation.

C'est le parti de `DEC-482` pour Trivy, transposé. **Et le taire aurait été le pire choix** : le
contrôle aurait annoncé « 7 séparations prouvées » en laissant croire davantage que ce qui est vrai.

---

## 7.21 Un contrôle juste hier peut être faux aujourd'hui, et c'est toi qui l'as rendu faux

**Apport de `T9`, et les deux défauts qui l'ont produit sont instructifs parce qu'ils ne sont pas de
la négligence.**

| Défaut | Ce qu'il affirmait | Ce que la mesure dit |
|---|---|---|
| `make destroy`, écrite en `T2` | « détruire `caddy-data` obligera à réapprouver la racine dans le trousseau » | vrai pour `dev` — `verify-cert` code 0 — **faux pour la recette**, code 1, racine jamais approuvée |
| Contrôle de page, écrit en `T5` | l'index doit référencer `/src/main.tsx` | vrai du serveur Vite, **faux de l'artefact bâti**, qui référence `/assets/…js` |

**Les deux étaient JUSTES quand ils ont été écrits.** `T2` et `T5` ne connaissaient qu'un
environnement. C'est `T8`, en créant le second, qui les a rendus faux — sans que rien ne le signale,
parce qu'aucun contrôle ne les exerçait dans le nouvel environnement.

> **La règle, sans jargon :** quand une sous-étape ajoute un environnement, une cible de
> construction ou une plateforme, **relis les contrôles qui n'en connaissaient qu'un**. Un contrôle
> ne devient pas faux tout seul : il le devient quand le monde change autour de lui, et ce
> changement, c'est nous qui le faisons.

**Le remède est le même dans les deux cas, et c'est celui du §7.20 :** faire **mesurer** au lieu
d'affirmer. `destroy` interroge le trousseau et dit ce qu'elle a mesuré — ou dit **« indéterminé »**
quand elle ne peut pas mesurer, plutôt que de trancher. Le contrôle de page **identifie** la cible
servie, exige qu'elle soit l'une des deux formes connues, et **échoue** s'il n'en reconnaît aucune.

**Un avertissement faux est pire qu'une absence d'avertissement.** Celui de `destroy` portait sur la
cible la plus destructive du dépôt : annoncer une conséquence inexistante apprend à passer outre, si
bien que le jour où il porte sur `dev`, où la conséquence est réelle, il n'est plus lu.

**Et une troisième leçon, de méthode celle-là.** J'ai annoncé à Jonathan qu'un workflow ne s'était
pas déclenché. Il ne s'était pas déclenché **encore** : `gh run list --branch` rendait 0 pendant trois
minutes alors que les check-runs sur l'empreinte de tête montraient deux contrôles en cours. **Avant
d'annoncer qu'une chose est absente, demande-toi si ta sonde distingue « absent » de « pas encore
là ».** Même famille que `T2-1`, où un 429 masqué avait été lu comme une image inexistante.

---

## 7.22 Un résiduel accepté n'est pas un dossier clos

**Apport de `T10`, et il renverse une mesure de `T6` en un seul jour.**

`T6` avait accepté un avis de sécurité, `GHSA-mh99-v99m-4gvg`, avec un motif **mesuré et solide** :

- la dernière version publiée de la ligne 1.x de `brace-expansion` **était** `1.1.16` — aucun
  correctif n'existait dans cette ligne ;
- forcer la ligne 5 **cassait ESLint** : son export CommonJS est un objet portant `.expand`, non une
  fonction, là où `minimatch@3` appelle `expand(motif)`. Le « correctif » aurait neutralisé
  `eslint-plugin-jsx-a11y`, motif déterminant de `DEC-451`.

**Mesure du 30/07/2026 : la ligne 1.x a reçu `1.1.18`.** Ce que `T6` avait mesuré comme inexistant
existe. Un `pnpm update -r`, dans les plages déjà déclarées, sans forcer aucune version majeure.
Vérifié dans les deux sens — l'audit est vert **avec et sans** la tolérance — et rien n'est cassé.

> **La règle, sans jargon :** un risque accepté parce qu'« aucun correctif n'existe » décrit
> l'écosystème **à une date**. Réévalue-le, ne l'archive pas. Et **retire la tolérance dès qu'elle ne
> couvre plus rien** : une tolérance morte avalerait silencieusement une réapparition du même avis,
> donc elle est moins sûre que pas de tolérance du tout.

**`ROAD-RSK-033` ÉTAIT EXACTEMENT DANS CETTE SITUATION, ET LA SURPRISE A EU LIEU LE 14/09/2026.**
23 avis `HIGH`/`CRITICAL` de `python:3.12-slim` « dont aucun n'a de correctif », mesuré en `T7` — et
`CVE-2026-13221` de `perl-base`, **`CRITICAL`**, en a reçu un : `5.40.1-6+deb13u1`, candidat dans
`trixie/main`. **Deuxième fois que cette leçon paie**, après `brace-expansion` en `T10` du LOT 1.

> **ET LE DÉCLENCHEUR DE RÉÉVALUATION DU RISQUE ÉTAIT ÉCRIT UN CRAN TROP EN AVAL.** Il disait « la
> publication […] d'un `python:3.12-slim` **corrigeant** `perl-base` ». Or l'image amont ne l'a pas
> corrigé — **c'est Debian qui a publié le correctif**, et l'image de base ne l'a pas encore reprise.
> Mesuré : le condensat amont du 01/09/2026 porte encore `5.40.1-6` sur `amd64` **et** `arm64`.
>
> **Un correctif devient actionnable quand la DISTRIBUTION le publie, pas quand l'image de base le
> reprend.** Attendre le second, c'est attendre un tiers qui n'a aucune raison de se presser. Le
> déclencheur est corrigé au registre, et `DEC-581` prend le correctif par une **couche `apt`
> épinglée** plutôt que d'attendre.

**Et une seconde leçon, sur la façon d'attribuer une régression.** Quand `make audit` est devenu
rouge en cours de sous-étape, la tentation était de chercher ce que `T10` avait cassé. La mesure
juste a été de créer un arbre de travail sur le commit **d'avant** et d'y relancer l'audit : mêmes
quatre avis. **Avant d'attribuer une régression à ton travail, mesure l'état d'avant** — `pnpm audit`
interroge une base qui change sans toi.

---

## 7.23 Un état DORMANT ne se voit pas dans ce qui tourne

**Apport du correctif postérieur à la porte `G1`, et il complète le §7.21.**

En `T8`, j'ai choisi la bande de ports de la recette après avoir mesuré que `8080` était **libre**.
La mesure employait `lsof -nP -iTCP -sTCP:LISTEN` : elle regardait **ce qui écoutait**.

Le projet tiers `observatoire-ecom-studio` **déclarait** `127.0.0.1:8080` depuis toujours. Il était
**arrêté** au moment de ma mesure — et **un conteneur arrêté déclare ses ports sans en occuper
aucun**. À sa relance : `Bind for 127.0.0.1:8080 failed: port is already allocated`.

**Et la mesure refaite correctement en a révélé un second, antérieur au projet** : `5432`, entre
`onboarding-dev` et `ticket_master`, arrêté depuis quatre semaines et donc jamais manifesté.

> **La règle, sans jargon :** ma mesure répondait à « ce port est-il occupé **maintenant** ? » quand
> la question était « ce port sera-t-il disponible **quand ce projet démarrera** ? ». **Quand tu
> mesures une ressource partagée, demande-toi qui la RÉCLAME, pas seulement qui la détient.** Un état
> dormant — conteneur arrêté, service désactivé, tâche planifiée qui n'a pas encore tourné — ne se
> voit pas dans l'état courant.

**Et une limite que ma première correction portait encore.** Le contrôle ne lisait que les conteneurs
existants. Or `make down` **supprime** les conteneurs : un environnement arrêté ne déclare plus rien,
et le contrôle était donc aveugle à lui — **il n'aurait pas attrapé le défaut qui l'a fait naître**,
puisque la recette n'existait pas encore comme conteneurs quand j'ai choisi ses ports. `make ports`
confronte désormais **deux sources** : les conteneurs existants **et** la configuration Compose
assemblée, qui ne demande aucun conteneur. `DEC-494`, `ECART-025`.

---

## 7.27 Une liste recopiée vieillit au PREMIER ajout — et j'en ai écrit trois

**Apport du LOT 3, et c'est la classe `ECART-021` appliquée à mes propres contrôles, trois fois en
deux sous-étapes.**

| Où | La liste recopiée | Ce qui l'a cassée | Conséquence |
|---|---|---|---|
| `verifier-images.py` | **7** variables d'environnement pour lancer les conteneurs | `T1` en a ajouté **4** | **la publication des images est devenue ROUGE sur `develop`** |
| `verifier-isolation.py` | **4** tables globales attendues | `T2` en a ajouté **6** | le contrôle échouait sur un livrable conforme |
| `test_socle_modele.py` | `TABLES_DECLAREES`, **18** tables | `T2` en a ajouté **7** | échec attendu — c'est le rôle de ce garde-fou |

**Les deux premières sont des défauts, la troisième est une fonctionnalité**, et la différence est
nette : `TABLES_DECLAREES` **doit** échouer à chaque table nouvelle, c'est son objet ; les deux autres
prétendaient décrire un état dérivable.

> **La règle, sans jargon :** avant d'écrire une liste dans un contrôle, demande-toi **d'où elle vient**.
> Si elle décrit un état que le code ou le modèle porte déjà, **dérive-la** — un `ast` sur le fichier de
> réglages, une requête sur le catalogue, une lecture du modèle. Si elle est une **interprétation** que
> rien ne porte, déclare-la **et exige qu'elle corresponde au réel**, comme `RELATIONS_ATTENDUES` dans
> `verifier-historisation.py`.

**Et la dérivation a ses propres pièges, tous les deux mesurés :**

- **importer pour dériver peut casser un contrôle qui n'a pas les dépendances.** `verifier-images.py`
  est invoqué par `python3`, hors environnement virtuel : importer `Parametres` exigeait `pydantic` et
  cassait `make check`. La lecture passe donc par **`ast`**, qui n'exige rien ;
- **une dérivation sur de la prose est une heuristique, donc un défaut.** Le §10.5 déclare la
  nullabilité par « une entité **facultative** », sans écrire `entity_id`. Élargir le motif sur du
  français aurait reconduit le défaut `T9-2` — le rattachement est **déclaré**.

---

## 7.28 Deux cibles de noms voisins, dont une seule éprouve ce qui t'intéresse

**Apport de `T1` du LOT 3, et c'est ce qui a rougi la publication.**

J'ai lancé `make check`, qui contient **`images-check`** — un contrôle **statique** qui n'ouvre aucune
connexion au démon Docker et ne démarre rien. J'ai cru avoir éprouvé les images. La cible qui **lance**
les conteneurs est **`images-verify`**, et je ne l'avais pas rejouée.

| Cible | Ce qu'elle fait | Dans `make check` ? |
|---|---|---|
| `images-check` | **statique** : épinglage, étiquetage, sélection de cible | **oui** |
| `images-build` | construit 3 images × 2 architectures, en local | non |
| `images-verify` | **LANCE les conteneurs** sur les deux architectures | non |

> **La règle, sans jargon :** quand tu changes ce dont un conteneur a besoin pour démarrer — une
> variable, un réglage, un point d'entrée — **la seule preuve est de le LANCER**. Un contrôle statique
> ne dira rien, et il te donnera la fausse confiance d'un code de sortie à zéro.

**La même distinction existe ailleurs** : `stack-check` regarde la santé, `api-check` fait un
aller-retour applicatif réel ; `env-check` compare des fichiers, `roles-provision` touche la base.
**Lis ce que la cible fait, pas ce que son nom suggère.**

---

## 7.26 Ce qui n'a jamais tourné à l'ÉCHELLE n'est pas éprouvé

**Apport de `T12`, et cela élargit le §7.16.** Ce paragraphe disait : ce qui n'a jamais tourné
**ailleurs** n'est pas éprouvé. Il faut y ajouter **l'autre volume**.

Mon générateur formait l'indice d'un Booster par `800_000 + rang`, une valeur **identique d'une entité
à l'autre**. À **trois** entités, les prénoms tirés au hasard suffisaient à éviter la collision. À
**vingt-cinq** entités et quatre cercles — cent tirages sur soixante-quatre combinaisons —
`email_normalized_unique` a été violée au premier essai à l'échelle.

> **La règle, sans jargon :** un jeu de données réduit n'éprouve pas les contraintes d'**unicité**,
> parce que la collision est un événement de **volume**. Quand un contrôle porte sur une unicité, une
> borne ou un comptage, **fais-le tourner au volume que le critère nomme** — ici cinq mille profils,
> pas trente.

**Et deux corollaires mesurés en `T12` :**

- **`ANALYZE` est indispensable après un jeu engendré dans une transaction.** PostgreSQL choisit ses
  plans sur des **statistiques** : sans lui, il raisonne sur des tables qu'il croit vides, et la
  mesure de performance ne dit rien de la réalité ;
- **un test de performance ne doit pas exiger l'usage d'un index.** Sur 5 000 lignes, un parcours
  séquentiel est souvent le plan **optimal** : exiger « aucun Seq Scan » exigerait le **contraire** de
  la performance, et échouerait sur un livrable conforme. Exige la **durée**, qui est la grandeur du
  critère, et **rapporte** le plan.

---

## 7.25 Un garde-fou à faux positifs est pire qu'aucun garde-fou

**Apport de `T11`, et c'est la troisième fois qu'un même défaut se rejoue : `T4-2`, `T8-3`, puis six
fabriques d'un coup.** Un paramètre lié partagé par deux colonnes rend `inconsistent types deduced
for parameter $1`, et le message ne nomme ni la table ni la colonne.

La parade du §7.2 s'applique — **changer d'outil plutôt que promettre de l'attention** — mais **deux
versions syntaxiques du garde-fou ont échoué sur du code conforme** :

- la première se déclenchait sur le **commentaire** expliquant le motif qu'elle interdit ;
- la seconde sur `:p` employé pour `person_id` **et** `assigned_by_person_id` — deux colonnes `uuid`,
  réutilisation parfaitement légitime.

**Le discriminant n'était pas dans le texte source : c'est le TYPE de colonne.** Mesuré :
`entity.code` est `character varying(64)` quand `display_name` et `city` sont `text` — d'où l'échec ;
mais `person.email` et `email_normalized` sont **tous deux** `character varying(320)`.

> **La règle, sans jargon :** un garde-fou qui refuse du code correct **apprend à passer outre**, si
> bien que le jour où il a raison, il n'est plus lu. C'est l'avertissement faux de `make destroy` au
> §7.21, dans un autre costume. **Un contrôle exact vaut mieux qu'un contrôle large** — et si
> l'exactitude demande de lire le catalogue au lieu du texte, lis le catalogue. Une heuristique dans
> un contrôle est un défaut : leçon `T9-2`, confirmée.

**LE GARDE-FOU EXISTE DEPUIS LE 14/09/2026, ET IL A FALLU UNE QUATRIÈME OCCURRENCE POUR L'ÉCRIRE.**
`DEC-580`, `make parametres-check`, dans `make check` **et** dans `ci.yml`.

> **Ce paragraphe a longtemps décrit deux tentatives échouées sans dire qu'aucune troisième n'avait
> été livrée**, et un agent — moi, le 13/09/2026 — y a lu qu'un garde-fou existait. Il a écrit dans
> un compte rendu que « le garde-fou s'est tu », puis a dû se corriger après l'avoir cherché par son
> nom, par son motif et dans le `Makefile` : **il n'existait pas**. C'est le §9.0 appliqué à ce
> document-ci.
>
> **Ce que le contrôle fait, et c'est exactement ce que ce paragraphe spécifiait déjà :** il relève
> chaque paramètre partagé par plusieurs colonnes dans une requête `text(...)`, résout chaque colonne
> **positionnellement**, lit son type dans les **métadonnées SQLAlchemy compilées pour PostgreSQL**,
> et refuse quand les types diffèrent. Le type est compilé pour le bon dialecte parce que c'est le
> **serveur** qui produit l'erreur : `Uuid` rend `CHAR(32)` en générique et `UUID` en PostgreSQL.
>
> **Le nombre qui justifie l'exactitude est 34.** Mesure du 14/09/2026 : 653 requêtes lues dans
> 161 fichiers, et **34 partages parfaitement légitimes** — autant de faux positifs qu'un contrôle
> textuel aurait produits, et un garde-fou à faux positifs apprend à passer outre.
>
> **Il lit les MÉTADONNÉES et non le catalogue**, donc aucune base n'est requise et il tourne dans la
> tâche **qualité** : le moment où il faut le savoir est la **pull request**. `make migrations-check`
> prouve déjà que le schéma égale ces métadonnées.
>
> **Et il DIT où il s'arrête** : `INSERT … VALUES` et `UPDATE … SET`, dont la résolution est
> positionnelle donc exacte — **pas** les `WHERE a = :x` d'une requête à jointures, dont la
> résolution de colonne serait une **heuristique**. Les **quatre** occurrences historiques étaient
> toutes des `INSERT`. Les **58** SQL en f-string sont **comptés en sortie**, jamais devinés (§7.20).

**Et une seconde leçon, sur les témoins.** `T11` a écrit un témoin qui exige les **quatre** messages
attendus, non un simple code de sortie non nul. Il a servi immédiatement : sa première version ne
portait qu'une clé étrangère **simple**, si bien que le contrôle qu'elle devait éprouver **n'était
jamais atteint**. **Un témoin qui n'exerce pas un contrôle ne prouve rien de ce contrôle**, et seul
un témoin qui nomme ce qu'il attend le dit.

---

## 7.24 Deux règles justes séparément peuvent s'exclure, et un outil qui réussit ne prouve rien

**Apport du correctif de stratégie de fusion, et il tient deux leçons distinctes.**

**La première porte sur les documents.** Les conventions Git posaient, à onze lignes d'intervalle,
« historique linéaire requis » (ligne 94) et « `develop` → `main` : merge commit » (ligne 106).
**Aucune des deux n'est fausse** — la première sert la lisibilité de `develop`, la seconde la
traçabilité de `main`. Elles sont **incompatibles** : l'historique linéaire refuse tout merge commit.
Les deux ont été appliquées, si bien que la fusion s'est rabattue sur le squash, ce qui a coupé `main`
de l'histoire de `develop` — et **9 fichiers sont entrés en conflit alors que le contenu ne
divergeait pas**.

> **La règle, sans jargon :** relire une règle ne suffit pas, il faut **confronter les règles entre
> elles**. Et le défaut ne s'est manifesté qu'à la **seconde** fusion vers `main` : une contradiction
> peut rester invisible tant qu'une seule de ses branches a été exercée. C'est `ECART-023` élargi —
> un document dérivé ne fait pas que vieillir, il peut **prescrire l'impossible dès sa rédaction**.

**La seconde porte sur les outils, et c'est la quatrième proposition du §7.0 appliquée à `git`.** Ma
résolution en `git merge -X theirs` **a réussi** : code 0, aucun conflit signalé. Et elle avait gardé,
du côté abandonné, un fragment **non conflictuel** — le bloc `§3.1` de `fiche-lot-1.md` — **en plus**
de la version qui le remplaçait. Soit **41 lignes dupliquées**, et une réserve `arm64` réapparaissant
*après* le texte qui la lève.

**Le succès de la fusion et sa justesse sont deux grandeurs différentes.** « Aucun conflit » ne veut
pas dire « le résultat est celui que je veux » : les deux produisent exactement la même observation.
Le contrôle qui discrimine ne porte pas sur le verdict de l'outil mais sur son **résultat** —
l'arbre :

```bash
git rev-parse origin/main^{tree} origin/develop^{tree}   # doivent etre IDENTIQUES
git merge-base --is-ancestor origin/develop origin/main  # doit sortir en 0
git rev-parse origin/main^@ | wc -l                      # 2 = merge commit, 1 = squash
```

**Et c'est ce contrôle-là qui a attrapé le défaut.** Sans lui, cette fusion passait en paraissant
propre — comme `T2-5`, où un Mailpit vide et un volume effacé rendaient tous deux `{"total":0}`.

---

---

## 7.29 Un document peut annoncer une décision À PRENDRE alors qu'elle est déjà prise

**Apport du LOT 3, et c'est l'inverse de l'avertissement habituel du §9.0.** Trois fois, le §8 de
`fiche-lot-3.md` m'a annoncé qu'une valeur restait à choisir :

| Ce que la fiche annonçait | Ce que le cahier dit |
|---|---|
| « le cahier exige une limitation, **sans donner de seuil** » | le §20.2 en donne **six**, et `.env.example` en porte cinq depuis le LOT 0 (`ECART-034`) |
| « **aucun document n'énumère** » les scopes | le §22 en donne **cinq** (`ECART-036`) |
| « durée maximale d'un jeton : à instruire » | la question portait **déjà** le numéro **`QO-072`** dans le cahier §32 |

**Suivre la fiche aurait produit des valeurs inventées qui contredisent le cahier**, lequel prévaut
sur tout. Et en ouvrir une nouvelle question aurait créé une collision de numéro.

> **La règle, sans jargon :** quand un document te dit qu'il te reste une décision à prendre,
> **cherche-la d'abord dans le cahier**. Le §9.0 t'apprenait à vérifier avant de bâtir sur une
> affirmation ; celle-ci t'apprend à vérifier avant de **décider**.

**Et une nuance qui compte, sinon on tombe dans l'erreur symétrique.** Le §22 énumère cinq scopes
**« par exemple »**. Conclure « le cahier tranche, il suffit de recopier » aurait produit une liste
blanche **fermée**, qui bloquerait le LOT 9. Même forme que le « à prévoir **notamment** » du §25.1.
**Les deux erreurs sont symétriques, et la bonne lecture est entre elles.**

**QUATRIÈME OCCURRENCE, EN `T2` DU LOT 4 — ET ELLE AFFINE LA PARADE.** Le §8 de `fiche-lot-4.md`
annonçait « où vit l'entité consultée » comme un point ouvert. Le cahier ne dit effectivement pas où
elle est **stockée** — mais il détermine entièrement le **parcours**, en quatre endroits concordants,
et cela ferme la question : on atterrit **toujours** sur la page nationale, donc une mémoire serveur
du dernier choix n'aurait **aucun consommateur**. `ECART-040`.

> **Ce qui manquait : chercher le sujet par ses SYNONYMES, pas par le mot que la fiche emploie.** Le
> mot de la fiche était « mémorisé », et il ne donne rien d'utile. Ce sont **« changement d'entité »**,
> **« entité consultée »** et le **diagramme du §8.1** qui ont tranché. Une recherche sur le seul
> terme de la fiche aurait conclu comme la fiche.
>
> **Et demande-toi si le cahier a une SECTION dédiée.** Le §23.3 s'appelle « Changement d'entité », il
> donne **cinq** règles, et la fiche instruisait le changement d'entité sans le citer. Une section
> entière manquée n'est pas un détail : sa quatrième règle — « annule les requêtes et caches associés
> à l'entité précédente » — était exécutable dès `T2`, et l'ignorer aurait laissé un défaut visible
> seulement **sous latence**.

---

## 7.30 Quand une classe d'erreur résiste SEPT fois, change d'outil

**Apport de `T12`, et c'est le §7.2 appliqué à une classe qui a résisté tout un lot.**

Une seule classe s'est rejouée **sept fois** : un nettoyage de test incomplet laisse un résidu, et le
résidu fait échouer des tests **sans rapport**. `T3-3`, `T4-3`, `T4-5`, `T5-5`, `T6-2`, les six
défauts de décor de `T9`, et `T10-2`.

**La septième est celle qui décide** : j'avais écrit la leçon dans le compte rendu de `T9` — « la
trace d'un refus sans acteur échappe à tout nettoyage par identité » — et je l'ai **recommise en
`T10`**. Une huitième promesse de vigilance ne valait rien.

**`make residu-check`** compare un **avant/après table par table**, la liste des tables **dérivée du
catalogue**, et il **remplace** `make test-integration` dans la CI. Il nomme la table et l'écart.

> **Et la mesure devait être EXACTE, pas heuristique.** Chercher des marqueurs — `t3api`, `%.test` —
> aurait été une **liste** qui vieillit au premier ajout **et** une heuristique dans un contrôle, ce
> que le §7.25 nomme un défaut. Un avant/après ne suppose rien de ce qui est « du test », et il
> fonctionne aussi bien sur une base vide que sur le jeu de recette de 27 936 lignes.

**HUITIÈME OCCURRENCE EN `T2` DU LOT 4, ET ELLE AJOUTE UN MÉCANISME QU'IL FAUT CONNAÎTRE.** Le
nettoyage d'une fixture est **une seule transaction**. Un ordre de suppression fautif — j'avais oublié
`entity_membership` avant `person` — la fait échouer, et **son échec l'annule ENTIÈREMENT** : rien
n'est supprimé, pas même ce qui aurait pu l'être. Quatorze lignes sont restées commitées.

**La conséquence a été bien plus large que l'erreur.** Au run suivant, **23 tests d'intégration du
LOT 2 ont échoué** — `test_appartenance.py` et six autres fichiers — parce qu'ils comptent
`entity_membership` **en absolu** dans une transaction en rollback, ce qui ne vaut que sur une base
propre. **Aucun de ces 23 messages ne nommait la cause** ; ils disaient « assert 3 == 2 ».

> C'est `make residu-check` qui l'a dite, en annonçant « **14 ligne(s) avant** ». Le contrôle posé en
> `T12` du LOT 3 pour exactement cette classe a fonctionné — et c'est la seule raison pour laquelle le
> diagnostic a pris deux minutes au lieu d'une heure. **Lis son « n ligne(s) avant », et lis la
> VENTILATION qui le suit désormais.**
>
> **« SUR UNE BASE PROPRE IL VAUT 0 » ÉTAIT ÉCRIT ICI, ET C'EST FAUX.** Mesure du 08/09/2026 : il
> valait **7**, et les sept étaient des traces de refus **sans acteur** dans `auth_event`, écrites
> par nos propres `magic-link-check` et `admin-check` — qui demandent **délibérément** un lien pour
> une adresse inconnue, pour prouver que la réponse est identique connue ou non (§22.5). Le §12.2
> interdit de rattacher ces traces à quiconque : les rattacher **révélerait l'existence de
> l'adresse**. **Aucun nettoyage par identité ne peut donc les atteindre** — c'est le §7.32 — et
> exiger zéro exigerait de renoncer à la preuve.
>
> **La valeur normale n'est donc pas un nombre, c'est une VENTILATION**, et le contrôle la donne
> table par table depuis `DEC-566` : les traces sans acteur d'`auth_event` sont nommées
> **structurelles**, tout le reste est nommé **inexpliqué**. L'exemption porte sur les **colonnes
> d'acteur**, jamais sur la table : exempter `auth_event` en bloc masquerait une trace **portant**
> un acteur, laissée par un test qui n'a pas nettoyé. Discriminant dans la colonne et non dans le
> nom — §7.25.
>
> **Et le contrôle passait au vert pendant tout ce temps**, parce qu'il mesure l'**écart** avant /
> après et non l'état initial : exact pour son mode de défaillance, aveugle à celui-là. §7.31, une
> quatrième fois. `ECART-054`.

---

## 7.31 Un garde-fou peut être exact pour un mode de défaillance et AVEUGLE à un autre

**Apport de `T12`, et c'est le §7.0 quatrième proposition appliqué à un garde-fou qui existait déjà.**

Quatre fichiers ont été **remis à une version antérieure** sans aucune action de session — même mtime
**à la seconde** sur les quatre, signature d'une réécriture en lot. **`make icloud-verify` est passé
au vert.**

Il ne cherchait que les copies de conflit `* [0-9]` : **exact** pour ce mode de défaillance,
**aveugle** à celui-ci — un fichier silencieusement réverté ne laisse aucune copie. Il donnait donc
l'impression de couvrir iCloud tout en ne prouvant rien de cette classe.

**Le remède a été d'ÉTENDRE le garde-fou existant, non d'en ajouter un parallèle** : la routine du
§11 reste inchangée, et personne n'a une habitude de plus à prendre. Il compare l'**arbre** de `HEAD`
à celui de l'amont et échoue si les deux sont identiques **alors que des fichiers sont modifiés** —
combinaison qui n'a pas d'autre cause plausible.

> **La règle, sans jargon :** quand un garde-fou passe au vert sur un problème réel, ne conclus pas
> qu'il est cassé — demande-toi **quel mode de défaillance il couvre**, et lequel il ne voit pas. Un
> garde-fou nommé « vérifie iCloud » ne vérifie que ce qu'il regarde.

---

## 7.32 N'écris pas de défense contre un état que la base interdit — exige qu'elle l'interdise

**Apport de `T9`.** J'avais codé une garde : ne pas révoquer les sessions si la personne garde une
appartenance active ailleurs. **Cet état est impossible** —
`uq_entity_membership_person_id_occupante` est un index unique **partiel sur `person_id` seul**.

La garde était du code mort, et **un champ de rapport qui ne peut jamais être vrai apprend à ne pas le
lire** — c'est le §7.21 dans un autre costume.

**Elle a été remplacée par un test qui exige que la base continue de l'interdire**, sur le **nom** de
la contrainte violée. Si un lot ultérieur relâchait cet index, ce test échouerait — **et celui qui le
relâche saurait qu'il doit relire la révocation.** Un test est un meilleur véhicule qu'un commentaire.

---

## 7.33 Un délai n'est pas une borne si la bibliothèque REPREND

**Apport de `T8-7`, et il a bloqué l'intégration continue.**

`socket_connect_timeout=1` avait l'air de borner l'attente. **redis-py 8 applique par défaut dix
reprises** : le délai vaut pour **chaque** tentative, et le total mesure **4,06 s** sur un port fermé,
contre 0,003 s avec la reprise bornée.

| Conséquence | Où |
|---|---|
| **quatre secondes par requête** | sur le chemin d'une requête, le « refus par défaut » du §20.1 ne vaut que s'il est **rapide** — sinon une panne de Redis devient un vecteur de saturation |
| **plus de quarante minutes** | la tâche « qualité » de la CI n'a pas de stack, et une fixture payait ce prix **deux fois par test** |

> **C'est la sixième proposition du §7.0 sous un autre jour** : *un contrôle qui compare deux nombres
> doit prouver qu'ils mesurent la même grandeur.* « Délai de connexion » et « attente totale » sont
> deux grandeurs différentes, d'un **facteur dix**.

**Et une leçon de méthode, désagréable.** J'avais formé cette hypothèse plus tôt, puis je l'avais
**réfutée** — en mesurant les **descripteurs de fichier** au lieu du **temps**. La mesure était juste,
la question était fausse. *Réfuter une hypothèse exige de mesurer la grandeur qu'elle prédit, pas une
grandeur voisine.*

---

## 7.34 Un motif écrit contre UN EXEMPLE ne couvre que cet exemple

**Apport du 23/08/2026, à l'ouverture du LOT 4, et il a coûté un commit fautif de 115 fichiers.**

Le §7.31 disait : un garde-fou peut être exact pour un mode de défaillance et aveugle à un autre.
Voici la même chose **un niveau plus bas** — dans le **motif** lui-même.

| Ce que le motif couvrait | Ce qu'il ne couvrait pas |
|---|---|
| `node_modules 2` — un **répertoire**, donc sans extension | `modeles 2.py` — un **fichier**, où le chiffre est suivi de l'extension |

`* [0-9]` a été écrit en `T1` du LOT 1 contre l'incident réel de ce jour-là, une copie de
**répertoire**. Il est resté juste treize mois pour ce cas, et **il n'a jamais rien couvert pour les
fichiers**. Mesuré : `git check-ignore` rend `IGNORE` sur le premier nom et `NON IGNORE` sur le
second. iCloud a produit **142** copies de fichiers, dont **115 sont entrées dans un commit par
`git add -A`** — parmi elles une seconde migration `0013`, qui a donné **deux têtes Alembic du même
numéro** et **1 007 tests collectés au lieu de 661**.

> **La règle, sans jargon :** quand tu écris un motif, une liste blanche ou une règle de filtrage à
> partir d'un **incident**, tu décris cet incident, pas sa classe. Demande-toi **quelles autres
> formes la même cause produit** — ici, la même cause iCloud produit des copies de fichiers *et* de
> répertoires — et **écris un témoin par forme**.

**Et la seule part de la correction qui vaille : le TÉMOIN PERMANENT.** Corriger le motif corrige une
instance ; `make icloud-verify` **exige** désormais que `git check-ignore` ignore effectivement
**quatre noms témoins**, un par forme. Le motif ne peut plus redevenir aveugle sans que le garde-fou
le dise, au début de chaque session. C'est aussi ce qui empêche les **deux copies de la même règle**
— `.gitignore` et le `Makefile` — de diverger en silence. `ECART-038`, `DEC-542`.

**Trois autres choses ont échoué le même jour, et chacune est une leçon déjà écrite ici :**

1. **le `find` s'arrêtait à `-maxdepth 3`** quand les copies étaient à la profondeur 4. Même si le
   motif avait été juste, le contrôle ne regardait pas là. **Un contrôle borné doit dire où il
   s'arrête** — §7.0, troisième proposition : il n'annonçait pas ce qu'il avait examiné ;
2. **le contrôle d'arbre que j'avais ajouté en `T12` était un FAUX POSITIF.** Il exigeait « arbre de
   `HEAD` identique à l'amont **et** fichiers modifiés » — l'état **normal** de toute sous-étape en
   cours de travail. Il ne visait pas la bonne grandeur : la signature réelle est qu'un fichier porte
   **exactement, à l'octet, le contenu d'une version antérieure**, ce qu'aucune édition humaine ne
   produit. Rendu exact et non affaibli (§7.20), dans `verifier-reversion-icloud.py`, avec son témoin
   exécuté **dans les deux sens** ;
3. **et j'ai lu `make check` en code 2 comme un succès**, pour la **septième** fois de la classe
   §7.3 : mon `&&` portait sur le `echo` qui suivait, pas sur le `make`. Puis, dans la commande même
   où j'annonçais lire le code correctement, un `echo` intermédiaire a écrasé `PIPESTATUS`.
   **La seule forme immunisée, désormais la seule à employer :**

```bash
make check > /tmp/check.log 2>&1
code=$?          # ligne SUIVANTE, aucun tuyau, aucune commande entre les deux
echo "code=$code"
```


## 7.35 Quand une propriété n'est observable par AUCUN contrôle, change le code

**Apport de `T8` du LOT 4, et c'est la seule issue que les six propositions du §7.0 ne donnaient
pas.**

Ma résolution de permissions rendait `tuple(sorted(ensemble))`, et un contrôle vérifiait l'ordre.
J'ai retiré le tri pour éprouver le contrôle : **les quinze contrôles sont passés trois fois sur
trois.**

| Version du contrôle | Verdict avec le défaut |
|---|---|
| deux appels comparés entre eux | **vert** — l'itération d'un `set` est stable **au sein d'un processus**, et les deux appels tombent sur le même worker |
| « la réponse doit être triée » | **vert** — l'ordre du `set` de ce décor **coïncide** avec l'ordre alphabétique |
| plus loin | impossible : deux ensembles égaux s'itèrent **identiquement** en CPython, quel que soit l'ordre d'insertion |

**L'ordre ne varie qu'entre PROCESSUS** — le hachage des chaînes est aléatoire par processus — et
aucune exécution unique, ni de stack ni unitaire, n'observe cela.

> **La règle, sans jargon :** quand tu découvres qu'aucun contrôle ne peut voir la disparition d'une
> propriété, **arrête de renforcer le contrôle**. Les §7.20 et §7.21 t'apprenaient à rendre un
> contrôle **exact** ; celle-ci dit quoi faire quand l'exactitude ne suffit pas — **rendre la
> propriété structurelle**, de sorte que la perdre exige de casser le code plutôt que de retirer un
> appel.

Ici l'ordre vient désormais de l'**itération de l'énumération** : `tuple(m for m in RoleDeLaMatrice
if m in roles)`. Le perdre exigerait de supprimer la boucle. C'est le §7.32 — « n'écris pas de
défense contre un état que la base interdit » — transposé du schéma au code applicatif.

**Et un bénéfice qui n'était pas cherché :** l'ordre obtenu est celui du **tableau §3 de la
matrice**, donc celui du document, meilleur qu'alphabétique.

**Deux corollaires mesurés le même jour :**

- **mes deux autres contrôles RETRIAIENT la réponse avant de la comparer**, donc ils étaient aveugles
  à l'ordre eux aussi. `sorted(reponse) == attendu` ne dit rien de l'ordre de `reponse` : compare la
  réponse **telle qu'elle est**, à un attendu **dérivé** ;
- **un défaut du livrable n'a été vu que dans un NAVIGATEUR.** Les droits arrivés **avant** l'entité
  étaient perdus ; l'API rendait la bonne valeur, l'écran ne l'affichait pas. Aucun des cinq tests ne
  l'attrapait, parce qu'un `fetch` bouchonné résout dans l'ordre de **création des promesses** et que
  le cadre demande l'entité en premier. **Un stub qui ne fixe pas l'ordre en fixe un quand même —
  celui de ton code.** Écris un test par ordre d'arrivée que la production peut produire.

---

## 7.36 Un contrôle vert n'atteste pas que ton code EST DANS le commit

**Apport de `T1` du LOT 5, et c'est le seul défaut de ce projet qu'aucune des sept propositions du
§7.0 ne pouvait attraper — parce qu'il ne porte pas sur ce que les contrôles mesurent, mais sur ce
qu'ils mesurent SANS LE SAVOIR : le disque, et non l'index de git.**

J'ai écrit `apps/api/app/media/`, ses vingt tests passaient, `make check` est sorti en **0**,
`make icloud-verify` en **0**. Puis `git add -A` **n'a pas ajouté le module**, et `git status
--short` ne le montrait pas.

| Ce qui l'a causé | Mesure |
|---|---|
| `.gitignore` ligne 60 portait `media/`, **sans barre oblique de tête** | un motif de répertoire sans `/` interne vaut **à toute profondeur** |
| écrit au LOT 0 contre les **médias déposés** localement | il attrapait `apps/api/app/media/`, un **module source** du même nom |
| **`git check-ignore -v`** sur les deux fichiers | `.gitignore:60:media/` — la cause en une ligne |

**C'est la deuxième occurrence de la classe §7.34.** Le motif `* [0-9]` avait été écrit contre une
copie de **répertoire** et ne couvrait pas les **fichiers**. Celui-ci a été écrit contre un
répertoire de **données** et ne prévoyait pas les **modules**. Les deux décrivent l'incident du
jour, pas sa classe — et les deux sont restés justes pour leur cas pendant plus d'un an.

> **La règle, sans jargon :** tous tes contrôles lisent le **disque**. Git lit son **index**. Ce
> sont deux grandeurs différentes — le §7.0 sixième proposition, appliquée non pas à deux nombres
> mais à deux **sources**. Un `make check` vert ne dit rien de ce qui sera commité. **Lis
> `git status --short` après chaque `git add`, et compare-le à ce que tu viens d'écrire.**

**Et la seule part de la correction qui vaille est le contrôle, pas le motif.** Les huit motifs qui
nomment un répertoire de **données locales** sont ancrés à la racine — `/media/` et non `media/`,
mesuré : aucun de ces huit répertoires n'existe ailleurs dans ce dépôt. Ceux de **vrais artefacts**
produits à toute profondeur — `dist/`, `node_modules/`, les caches — restent non ancrés, parce que
c'est leur intention.

**`make sources-check` exige qu'aucun fichier source du disque ne soit ignoré par git**, la liste
**dérivée du disque** à chaque exécution. Il est dans **`make check`** *et* **nommé explicitement
dans `ci.yml`** : le moment où il faut le savoir est la **pull request**, pas le début de session.

> **Et le « donc dans la CI » que j'avais d'abord écrit était FAUX** — `T1-5`, cinquième défaut de
> cette sous-étape. **`ci.yml` n'invoque pas `make check`** : il appelle les cibles **une par une**,
> **41** d'entre elles, dérivées le 08/09/2026 — et j'avais écrit « quarante » deux commandes
> avant d'en ajouter une quarante-et-unième dans la même pull request, ce qui est la
> démonstration la plus courte du problème. Ma première mesure avait matché `make check` dans un
> **commentaire** du workflow. C'est le §7.28 — lis ce que la cible fait, pas ce que son nom suggère —
> et le §7.11 : **vérifie ce que la documentation affirme, même quand c'est toi qui l'écris.**
> **Une cible ajoutée à `make check` n'entre PAS dans la CI de ce projet.** Ajoute-la à `ci.yml`. **Éprouvé sur le défaut qui
l'a fait naître** — remis à `media/`, il rend 1 et nomme les deux fichiers avec leur ligne — et son
témoin l'exerce **dans les deux sens**. Les deux seules exceptions, `AGENTS.md` et
`docs/prototype/V1.html`, sont déclarées avec leur motif, et **le contrôle échoue aussi si l'une
cesse d'être ignorée** (§7.22). Le résiduel est **nommé dans la sortie** : `dist` et `build` sont
des noms qu'un module pourrait porter.

**Et un second garde-fou du même jour, de la même classe §7.31.** `make docs-check` faisait un
`re.search` du marqueur « prochain identifiant libre » : il lisait le **premier** et ne voyait
jamais les autres. Le registre des écarts en portait **deux** — `ECART-048` en tête, et
**`ECART-045` à la toute fin**, trois de retard. C'est le dommage exact de `ECART-021`, **dans le
garde-fou écrit pour `ECART-021`**, et c'est la fin du fichier que déroule qui cherche un numéro.
Le contrôle exige désormais **un seul** marqueur par registre, et non pas seulement leur accord :
deux marqueurs qui concordent aujourd'hui divergent le jour où une sous-étape n'en met qu'un à
jour — ce qui est précisément ce qui s'est passé. `ECART-048`, `DEC-560`.

---

## 7.37 Un type juste dans le DOMAINE peut être faux à la FRONTIÈRE

**Apport de `T2` du LOT 5, et c'est le §7.0 sixième proposition appliqué non pas à deux nombres mais
à deux REPRÉSENTATIONS d'une même valeur.**

Le cahier §18.2 donne trois tailles de page : 25, 50, 100. Le type qui décrit exactement ce domaine
est `Literal[25, 50, 100]`, et je l'ai employé pour le paramètre d'URL. **Un paramètre d'URL arrive
toujours en chaîne** :

```text
TypeAdapter(Literal[25, 50, 100]).validate_python("25")   ->  REFUSE
TypeAdapter(IntEnum(...)).validate_python("25")           ->  25
```

La route refusait donc **les trois tailles valides** dès qu'elles étaient écrites dans l'adresse, et
n'acceptait plus que le défaut implicite.

**Et huit contrôles verts ne le voyaient pas.** J'avais écrit une épreuve de refus par valeur hors
liste — 0, 1, 24, 26, 37, 99, 101, 1000 — et **les huit passaient** : elles demandaient un refus, et
elles l'obtenaient, **pour la mauvaise raison**. Mesuré en réintroduisant le défaut :

| Famille de contrôles | Verdict avec le défaut |
|---|---|
| les **huit** refus | **8 verts sur 8** |
| le témoin « 25, 50 et 100 SONT servies » | 3 échecs |
| la recomposition des pages | 3 échecs |

> **La règle, sans jargon :** quand une valeur traverse une frontière — URL, formulaire, variable
> d'environnement, fichier, en-tête — elle y devient **du texte**. Un type qui décrit bien le
> domaine ne décrit pas forcément ce qui arrive. **Demande-toi sous quelle forme la valeur arrive
> RÉELLEMENT, et éprouve la conversion elle-même**, pas seulement le domaine.

**Et la parade qui l'a attrapé est la troisième proposition du §7.0, pas une quatrième :** un
contrôle qui n'exige que des refus est satisfait par une route qui refuse tout. **Toute famille de
contrôles négatifs a besoin de son témoin positif** — et ici le témoin devait porter sur les
**trois** valeurs, pas sur une seule, puisque c'est la conversion qui échoue et non une valeur
particulière.

**Un corollaire de la même sous-étape, sur le lieu de la vérification.** Le service vérifie *aussi*
la taille, et ce n'est pas une redondance : il est appelable hors HTTP — un export, un script — et
une fonction qui accepterait 10 000 rendrait la borne du cahier **dépendante de son appelant**. La
route, elle, ne l'écrit nulle part : c'est le type qui refuse, et `gerer_erreur_validation` produit
le format du §18.3. Écrire un second refus dans la route donnerait **deux** formes pour une même
cause, et la seconde serait celle qu'aucun test de format n'examine.

---

## 7.38 Un test de performance mesure le système, son HARNAIS, et l'ÉTAT PHYSIQUE de la base

**Apport de `T3` du LOT 5, et il a coûté quatre diagnostics dont DEUX étaient faux.**

La même requête, le même code, le même volume : **2 ms** isolément, **1 400 ms** en fin de suite
complète. Et le plan `EXPLAIN ANALYZE` donnait `Execution Time: 478 ms` avec
**`Rows Removed by Join Filter: 45 294`** — la base parcourait `person` **en entier à chaque
appartenance**.

| Hypothèse | Ce que la mesure a dit |
|---|---|
| « la fonction SQL n'est pas *inlinée* » | **réfutée** — la fonction, l'expression en clair et `lower()` seul rendent **0,6 ms** tous les trois |
| « mon compteur fuit un écouteur » | **vraie, mais pas la cause** — corrigée, et la lenteur est revenue |
| « le planificateur sous-estime des colonnes corrélées » | **réfutée par l'expérience faite pour la confirmer** |
| **les tuples MORTS laissés par le harnais** | **confirmée** — 467, 490, 539 ms sur trois tours, puis **0,5 ms** la base nettoyée |

Chaque test du fichier engendre 28 000 lignes dans une transaction **annulée**. Les lignes annulées
restent **physiquement en table** jusqu'à `autovacuum` : `Buffers: shared hit=372 681` dans le plan
lent, contre **326** dans le plan sain.

> **La règle, sans jargon :** quand une mesure de performance varie d'un facteur 500 sans que le code
> change, ne cherche pas d'abord dans le produit. **Sépare les trois grandeurs** — le temps serveur,
> le temps du harnais, et l'état physique de la base — parce qu'un banc d'essai qui se salue
> lui-même attribue au produit ce qui lui appartient.

**ET UNE HYPOTHÈSE NE SE CONFIRME PAS EN APPLIQUANT SON REMÈDE. DEUX FOIS DE SUITE.** J'ai d'abord
posé des `CREATE STATISTICS` sur les colonnes que je croyais corrélées, mesuré « après », vu que
c'était rapide, et conclu. En mesurant **avec ET sans**, l'estimation restait la même et les durées
étaient **identiques**. Puis j'ai posé une CTE `MATERIALIZED` pour borner le travail à l'entité :
**elle n'a rien corrigé non plus** — 45 879 lignes encore rejetées.

**Les deux changements ont été retirés.** Garder un correctif dont le motif est faux laisse croire
que la cause est traitée, ce qui est pire que le défaut — et un correctif dont l'effet est **nul**
en plus du motif faux ne laisse même pas l'excuse du doute.

**Et ce qu'un test PEUT prouver n'est pas toujours ce que le critère énonce.** Le §25.2 vise « moins
de 800 ms au P95 » : c'est un objectif de **production**, sous charge réelle. Un poste de
développement ne mesure pas cela. Le test **rapporte** donc le P95, et **exige** deux choses qui,
elles, se prouvent :

- **aucun effondrement**, avec un plafond large et assumé — c'est le parti de `test_jeu_de_recette.py`
  au LOT 2, « détecter un effondrement, non mesurer une milliseconde » ;
- **la propriété STRUCTURELLE, RAPPORTÉE et non exigée** : `Rows Removed by Join Filter` dit si la
  jointure suit l'**entité** ou la **table**, et c'est ce qui distingue le plan à 0,15 ms de celui à
  478 ms. **Mais l'exiger ferait échouer un livrable conforme**, pour une raison mesurée le
  26/08/2026 et qui vaut pour tout ce projet :

> **`ANALYZE` NE PUBLIE RIEN D'EXPLOITABLE SUR DES LIGNES NON VALIDÉES.**
>
> ```text
> apres VACUUM (ANALYZE) sur base validee   reltuples(entity_membership) = 0
> apres 5 155 insertions NON validees
>   puis ANALYZE dans la transaction        reltuples(entity_membership) = 0
> ```
>
> Un test qui engendre son volume dans une transaction **annulée** — le patron posé par `T12` du
> LOT 2 et repris depuis — mesure donc un planificateur qui croit les tables **vides** : il estime
> `rows=1` partout et choisit des plans qu'il ne choisirait pas en service. **Aucune conclusion sur
> le PLAN ne peut être tirée de ce banc d'essai**, et le commentaire hérité du LOT 2 — « sans
> `ANALYZE`, PostgreSQL raisonne sur des tables qu'il croit vides » — est faux dans ce contexte : il
> les croit vides quand même.

**Et la conclusion se paie une seconde fois si l'on n'y va pas jusqu'au bout.** J'avais gardé un
plafond d'« effondrement » de 3 000 ms — large, assumé, et **calibré sur ma machine** : il passait
chez moi et a rendu **3 663, 4 791 et 3 511 ms** sur l'exécuteur de la CI. Or c'est la conséquence
directe de ce qui précède : si le plan n'est pas celui de la production, **la durée ne l'est pas non
plus**. Le test n'exige donc plus **aucune** durée. Il exige la **justesse au volume** — la requête
rend exactement ce qu'une requête SQL directe rend — et il **rapporte** tout le reste.

> **La règle, sans jargon :** quand tu as établi qu'un banc d'essai ne peut pas mesurer une
> grandeur, n'en garde pas un seuil « prudent ». Un seuil sur une grandeur non mesurable ne mesure
> que la machine, et il finira par échouer ailleurs que chez toi.
>
> **ET DEMANDE ENSUITE QUELS AUTRES CONTRÔLES PORTENT LA MÊME EXIGENCE — CETTE MOITIÉ-LÀ A ÉTÉ
> OUBLIÉE, ET ELLE A COÛTÉ DEUX SEMAINES.** `T3` a retiré ses exigences de durée, `T4` a corrigé le
> plafond de `T3` après l'exécuteur de la CI, et **personne n'a demandé si un autre test en portait
> une**. `test_jeu_de_recette.py` du LOT 2 gardait **500 ms par requête** : mesuré le 08/09/2026,
> **un succès sur cinq** exécutions isolées, 211 à 1 165 ms — et le seuil tombait au **milieu** de la
> dispersion, un tour rendant 497,9 ms. C'est la forme exacte de `ECART-054` transposée aux
> **contrôles** : un correctif appliqué à l'instance qu'on regarde. `ECART-055`.
>
> **Et le plan complet est ce qui clôt ce genre de question, pas la durée.** `EXPLAIN (ANALYZE,
> BUFFERS)` sur la requête fautive : `rows=1` partout, `Nested Loop` à **5 001 tours**,
> **1 028 870** combinaisons rejetées sur 1 029 071, et des **`Heap Fetches` sur un *Index Only*
> Scan** — la carte de visibilité n'est pas positionnée pour des lignes non validées, ce qui **nomme
> la source de la variance**. En service, avec de vraies statistiques, le planificateur prendrait un
> Hash Join : le problème n'est pas dans le produit.
>
> **UN COROLLAIRE QUE J'AI PAYÉ DEUX FOIS DANS LA MÊME HEURE.** J'avais mesuré `circle_membership` à
> 130 pages et **5 065 tuples morts**, la requête à 642–950 ms gonflée contre **171 ms** nettoyée :
> corrélation nette, causalité fausse. Le `VACUUM` préalable écrit là-dessus a laissé **quatre échecs
> sur cinq**, dont un tour à 1 078 ms alors que le ménage annonçait « 0 table sale ». *Une hypothèse
> ne se confirme pas en appliquant son remède* — c'est écrit six paragraphes plus haut, et je l'ai
> rejoué. **Et ma première mesure des tuples morts m'avait fait les écarter à tort** : `n_dead_tup >
> 1000` rendait zéro table, ce qui était juste **à cet instant**, l'autovacuum venant de passer. Je
> demandais « y en a-t-il maintenant ? » quand la question était « y en a-t-il **quand le test
> tourne** ? ». §7.23, l'état dormant, dans la mesure elle-même.

**Enfin, un piège de nettoyage qui vaut d'être connu :** un `VACUUM` lancé pendant qu'une
transaction de fixture est **déjà ouverte** ne récupère **rien** — son instantané l'en empêche. Il
faut une connexion séparée, en autovalidation, **avant** d'ouvrir celle qui mesure.

---

---

## 7.39 Un CRITÈRE de non-fuite est satisfait par une route qui ne sert RIEN

**Apport de `T5` du LOT 5, et c'est la quatrième proposition du §7.0 appliquée non pas à un
contrôle mais au CRITÈRE lui-même.**

La fiche découpait `US005` en deux sous-étapes : `T5` « les miniatures », `T6` « l'autorisation ».
Le critère de `T5` était « la photo **originale jamais servie** dans la liste ».

**Ce critère est parfaitement satisfait par une route qui ne sert rien du tout.** Une `T5` qui aurait
posé les variantes sans servir d'octets aurait pu cocher son critère, en toute bonne foi, et n'aurait
rien prouvé. Le manque n'était pas dans un contrôle à écrire : il était dans le **découpage**.

| Ce que la fiche voulait séparer | Pourquoi c'est indissociable |
|---|---|
| `T5` : les miniatures | on ne peut pas prouver « l'originale n'est jamais servie » sans **servir** la miniature |
| `T6` : l'autorisation | on ne peut pas prouver « sans autorisation, avatar neutre » sans **servir** quelque chose non plus — et servir sans vérifier l'autorisation enfreindrait le §12.2 |

Arbitrage de Jonathan du 06/09/2026 : **une seule sous-étape**, et le lot passe à onze.

> **La règle, sans jargon :** un critère qui interdit quelque chose — « jamais servi », « aucune
> fuite », « pas de doublon » — se satisfait tout seul quand la fonctionnalité n'existe pas.
> **Avant d'accepter un découpage, demande-toi de chaque critère négatif : quel témoin POSITIF le
> rend non trivial, et cette sous-étape le contient-elle ?** Si le témoin est dans la sous-étape
> suivante, les deux n'en font qu'une.

**Et la même sous-étape en a donné une seconde forme, plus fine encore.** Une fois `T5` et `T6`
fusionnées, j'ai écrit cinq épreuves de refus — pas d'autorisation, retirée, future, média non
`ready`, aucune variante — **et les cinq donnent la même observation côté client**, c'est le §21.2 qui
le veut. Cinq refus indistinguables : un `WHERE` faux aurait refusé tout, et les cinq seraient restés
verts, exactement comme les **huit** refus du défaut `T2-3`.

Chaque refus a donc été **apparié à un témoin qui ne diffère que par LA valeur en cause**. Et le plus
utile n'est pas un refus : c'est celui de l'autorisation **future**, où **seul l'instant avance** —
la même ligne, le même actif, la même variante, et la photo devient servable. Sans lui, le refus
mesuré pouvait venir de n'importe quel filtre trop large.

**La mesure du témoin le confirme :** en retirant `granted_at <= :instant` — donc en gardant
`withdrawn_at IS NULL` seul, ce qui semble suffisant — **quatre** tests échouent, dont ceux de la
route de liste. Sans ce témoin, aucun.

**Un corollaire de la même sous-étape, sur les propriétés qu'on ne peut pas tester par le refus.**
« L'originale n'est jamais servie » ne se prouve pas en montrant qu'elle ne sort pas : il faut
montrer que **ce qui sort est autre chose**. Deux objets de contenus **distincts** sont donc déversés
dans MinIO, et le contrôle compare les **octets** — pas le code HTTP, pas la longueur. Éprouvé :
`a.object_key` sélectionné au lieu de `v.object_key`, et le contrôle nomme les octets reçus,
`b'ORIGINAL-QUI-NE-DOIT-JAMAIS-SORTIR-ooooo'`. Un contrôle qui aurait vérifié « 200 et des octets »
serait resté vert.

---

## 7.40 Un garde-fou écrit contre UNE instance ne couvre pas la CLASSE d'objets

**Apport de la mise à jour documentaire de `T5` du LOT 5, et c'est le §7.34 appliqué non pas à un
motif mais à un PÉRIMÈTRE.**

`controler_totaux_decisions` a été écrit en `T8` du LOT 1 contre un défaut réel : les deux tableaux
de synthèse du registre des décisions annonçaient **145** quand son corps en déclarait **150**. Le
contrôle est bien écrit, il porte son motif dans son docstring, et **il est exact pour ce
registre-là.**

**Personne n'a demandé combien de registres existent.** Il y en a **six**, et **un seul était
couvert**. Mesure du 07/09/2026 :

| Registre | Annoncé | Déclaré |
|---|---|---|
| risques | **33**, et son §3 titré « `025` à `033` » | **34** — `ROAD-RSK-034` ouvert en `T8` du LOT 1 |
| questions, dans `CLAUDE.md` §1 | « **40** questions (**33** ouvertes) » | **42**, dont 10 closes, donc **32** ouvertes |

**Et la cellule fautive affirmait, dans la même phrase, que `make docs-check` DÉRIVE ces totaux.**
C'est le §7.11 au carré : vérifie ce que la documentation affirme, y compris quand elle affirme
qu'elle est protégée. `ECART-053`, `DEC-565`.

> **La règle, sans jargon :** quand tu écris un garde-fou contre une instance, demande-toi
> **combien d'objets de la même nature existent dans le dépôt**, et si le garde-fou les couvre
> tous. « Six registres, un couvert » est la réponse qu'il fallait obtenir avant de considérer
> `ECART-021` traité.
>
> **Et la parade qui dure est de DÉRIVER le périmètre, pas de l'étendre à la main.** La liste des
> registres vient de `SEQUENCES`, qui pilote déjà la vérification des séquences : un septième
> registre y entrera **sans que personne y pense**. Écrire les cinq chemins en dur aurait reproduit
> exactement la faute que le contrôle corrige.

**ET LE DÉFAUT ÉTAIT MASQUÉ PAR UN SECOND, PLUS INSIDIEUX : LE RELEVÉ NE VOYAIT PAS LES
DÉCLARATIONS BARRÉES.**

`identifiants_en_usage` exigeait l'identifiant **immédiatement** après le `|` ou le `#`. Une
déclaration close — `| ~~`QO-072`~~ |`, `## ~~`ROAD-RSK-032`~~` — était donc **ignorée en
silence** : 40 questions relevées pour 42, 33 risques pour 34.

**Ma première version du nouveau contrôle comparait donc deux grandeurs différentes** — §7.0
sixième proposition, dans le contrôle écrit pour cette classe. Elle accusait le registre des
questions, qui était **juste**.

**Et c'était un défaut DORMANT du contrôle de séquences, pas seulement de celui des totaux.** Le
jour où l'identifiant le **plus haut** d'un registre serait clos et barré, le maximum relevé
baisserait, le marqueur « prochain identifiant libre » serait jugé trop haut, et **un numéro
pourrait être réutilisé** — ce que les règles de tenue interdisent absolument. Aucun registre n'est
dans ce cas aujourd'hui, **et c'est exactement ce qui rendait le défaut invisible** : §7.31, une
troisième fois.

**Le témoin qui compte n'est pas un échec, c'est une ABSENCE d'échec.** Barrer une entrée qui ne
l'était pas **ne change plus le compte** — 42 reste 42 — là où l'ancien relevé serait tombé à 41 et
aurait fait échouer le contrôle sur des données **justes**. Les deux témoins d'échec, eux, ne
prouvaient que la moitié de la correction.

**Un dernier constat de la même passe, et il vaut pour toute mise à jour documentaire.** J'ai écrit
« `T7` — les écrans de trombinoscope » dans **trois** documents, dont deux que je venais de
rédiger. La fiche du lot dit « `T7` — **l'écriture dans son périmètre** », les écrans étant `T10` et
`T11`. **Je l'ai trouvé en DÉRIVANT les libellés de la fiche** pour remplir un tableau, non en
relisant. *Une relecture confirme ce qu'on croit ; une dérivation le contredit.*

> **ET CETTE CORRECTION ELLE-MÊME ÉTAIT INCOMPLÈTE — TROIS INSTANCES ONT SURVÉCU, DÉCOUVERTES LE
> 08/09/2026.** J'avais corrigé les **trois** documents que je regardais ; la classe en comptait
> **six**. Ont subsisté : le §7 du compte rendu de `T5` — dont la **ligne 21 annonce pourtant la
> correction**, 428 lignes plus haut — le §7.15 d'`exploitation-locale.md`, et le `README.md`
> racine.
>
> **Le compte n'a pas été relevé, il a été DÉRIVÉ**, et c'est la seule raison pour laquelle les
> trois sont apparues :
>
> ```bash
> grep -rniE 'T7.{0,60}écran|écran.{0,60}T7' --include='*.md' .
> ```
>
> **La leçon n'est donc pas « dérive au lieu de relire » — c'est « dérive sur le DÉPÔT, pas sur les
> fichiers ouverts ».** Une dérivation dont le périmètre est ma pile d'onglets a exactement la
> portée d'une relecture. C'est le §7.34 d'un cran plus haut : un motif écrit contre un exemple ne
> couvre que cet exemple, et **une correction appliquée aux fichiers sous la main ne couvre que
> ceux-là**. `ECART-054`.

**ET LE MÊME JOUR, LA MÊME LEÇON A ÉTÉ PAYÉE UN CRAN PLUS HAUT ENCORE — C'EST LE FOND DE
`ECART-054`.** `ECART-053` avait posé la bonne question : *combien d'objets de la même nature
existent dans le dépôt ?* Réponse : six registres, un couvert. Le garde-fou a donc été étendu **aux
six registres**. Deux semaines plus tard, `CLAUDE.md` portait **seize** affirmations fausses sur ces
mêmes registres.

| Ce que `ECART-053` a demandé | Ce qu'il fallait demander |
|---|---|
| quels **objets** de cette nature existent ? | qui **PARLE** de ces objets ? |
| → six registres | → six registres **et leurs résumés**, dont la passation que tout agent lit en entier |

> **La règle, sans jargon :** un registre et un résumé de registre ne sont pas de la même nature, et
> **c'est le résumé qu'on lit**. Étendre un garde-fou à une classe d'objets ne protège pas ce qui
> les cite : `make docs-check` vérifiait la cohérence **interne** de chaque registre — son tableau
> de tête contre son corps — et **n'ouvrait aucun autre fichier**. Un résumé pouvait donc vieillir
> indéfiniment sans que rien ne s'en aperçoive. **Quand tu poses un garde-fou sur une donnée,
> demande-toi où cette donnée est RECOPIÉE**, et fais lire ces endroits-là.
>
> **Et deux des seize faisaient AGIR de travers, pas seulement croire de travers** — c'est la
> distinction qui compte pour prioriser : la **règle n°1 du §2** interdisait le lot ouvert, et le
> tableau §4.14 aurait fait **réutiliser un identifiant**. Un compte faux trompe un lecteur ; un
> « prochain libre » faux corrompt le registre. `DEC-566` couvre les deux, avec `make docs-temoin`
> pour prouver qu'il mord — **et ce témoin a lui-même vieilli dans l'heure** parce que sa première
> version **recopiait** les chaînes du corpus au lieu de les dériver. `ECART-021`, dans le témoin
> écrit pour `ECART-054`. La démonstration la plus courte possible du §7.27.

---

## 7.41 Un test qu'on t'annonce comme devant céder est une PRÉDICTION, pas une mesure

**Apport de `T8` du LOT 5, et c'est le §9.0 retourné contre ce document-ci.**

Ce document disait, en toutes lettres et dans sa cellule « Prochaine action » : « **`T7` lui laisse
DEUX TESTS À CASSER, ET C'EST LEUR RÔLE** […] `T8` devra la relâcher **délibérément**, et deux tests
l'y obligeront. » La formulation était juste sur le mécanisme — c'est bien le §7.32, un test vaut
mieux qu'un commentaire pour forcer une décision — et **fausse sur la décision à prendre**.

| Le test qui « devait céder » | Pourquoi il avait raison de tenir |
|---|---|
| le trombinoscope exclut les archivés, **même pour `SUPER`** | le §6.1 lui donne la ligne « profil **actif** ». « Consulter un profil archivé » est une **autre** ligne, à **trois** rôles : deux droits que le document sépare |
| `resoudre_le_perimetre` refuse une cible archivée | on ne **modifie** pas un archivé, on le **restaure**. Le refus est exact |

La bonne forme n'était pas de relâcher, c'était d'**ajouter à côté** : une seconde route servant une
seconde population, avec sa propre grille de rôles. Les deux tests sont restés verts, et le §6.1 est
suivi de plus près qu'il ne l'aurait été en élargissant le premier.

> **La règle, sans jargon :** quand une passation, un commentaire ou un test te dit « le lot suivant
> devra me casser », il t'annonce qu'une **décision** t'attend — pas laquelle. **Va lire la source
> qui a fait poser ce test, et demande-toi si la décision n'est pas d'en écrire un second.** Un test
> qu'on relâche perd sa preuve ; un test qu'on double la garde et en ajoute une.

**Et le corollaire porte sur ce document.** Le §9.0 apprend à se méfier de ce que les documents
**affirment** ; celui-ci ajoute qu'il faut se méfier de ce qu'ils **prévoient**. Une affirmation se
vérifie par la mesure ; une prévision de conception ne se vérifie que **contre le corpus**, au
moment de la faire.

---

## 7.42 Un décor qui ne produit JAMAIS la valeur en cause ne dit rien d'elle

**Apport de `T10-8`, trouvé en préparant une démonstration — donc APRÈS que la porte
d'intégration continue est passée au vert.**

`circle.color_token` est **nullable** au catalogue. Le service faisait `str(color_token)`, ce qui
sur `None` rend la chaîne **`"None"`** : un jeton d'apparence parfaitement plausible, servi sur
**100 des 100 cercles** du jeu de données, par la fiche **et** par la liste.

| Ce qui existait | Ce que ça valait |
|---|---|
| trois décors de test, trois fixtures | **les trois écrivaient `'bleu'`** |
| un contrôle de stack « les quatre champs du verso sont RENSEIGNÉS » | `cercle` est une **structure**, donc renseignée — avec un jeton mensonger dedans |
| `mypy --strict` | `str(x)` rend bien un `str`. Il n'avait rien à dire |

**Les sept propositions du §7.0 étaient toutes respectées.** Les contrôles pouvaient échouer, on
lisait leur code de sortie, ils annonçaient combien d'éléments ils avaient examinés, et leur échec
aurait produit une autre observation. Ils n'ont rien vu, parce que **la valeur qui déclenche le
défaut n'était présente dans aucun décor.**

> **La règle, sans jargon :** quand une colonne est **nullable**, un décor qui la renseigne toujours
> n'éprouve que la moitié de son domaine. **Demande-toi, de chaque colonne facultative que ton code
> traverse : mon décor produit-il l'absence ?** Si non, le code qui la traite n'est exercé par
> personne — et c'est la version *nullable* du §7.26, où une contrainte d'unicité ne s'éprouve
> qu'au volume.

**La parade est un COUPLE dans chaque décor**, deux lignes ne différant que par la colonne en cause
— un cercle avec jeton, un cercle sans. Ni moitié ne suffit : sans le témoin, un code qui ne
rendrait **jamais** de jeton passerait ; sans le cas, `str(None)` reste invisible.

**Et deux constats de méthode, tous deux mesurés :**

- **le périmètre a été DÉRIVÉ du catalogue, pas listé de mémoire.** Une requête sur
  `information_schema.columns` dit que `circle.color_token` est la **seule** colonne textuelle
  nullable qui atterrisse dans un champ non optionnel, sur les onze tables traversées. Trois sites,
  deux modules, et la mesure dit qu'il n'y en a pas un quatrième. Sans elle, j'aurais corrigé la
  liste — que je venais d'écrire — et laissé la fiche, qui portait le défaut **depuis `T4`** : le
  §7.40 exactement ;
- **une moitié de la correction n'est observable par AUCUN test.** `COULEURS_DE_CERCLE[null]` rend
  `undefined`, exactement comme le chemin gardé : les 140 tests d'écran restent **verts** avec le
  défaut en place. Ce qui le refuse est le **type** — `TS2538: Type 'null' cannot be used as an
  index type`. C'est le §7.35 dans l'autre sens : là où aucun contrôle ne peut voir la propriété,
  c'est la **structure** qui la tient, et il faut le **dire** plutôt que de laisser croire qu'un
  test la prouve.

---

## 7.43 Un bouchon prouve ce que TU as écrit dans le bouchon, jamais ce que l'API fait

**Apport de `T11`, seconde partie, et c'est le §7.16 appliqué non pas à une machine mais à l'autre
bout d'un appel.**

J'allais écrire « aucun défaut dans cette partie » : **192 tests d'écran passaient**, les **six**
contrôles de stack étaient verts, et `mypy` comme `tsc` étaient muets. Deux défauts sont tombés
**coup sur coup** dès que j'ai exercé le parcours sur la pile réelle.

| Défaut | Ce que le bouchon rendait | Ce que l'API fait |
|---|---|---|
| `T11-6` | `200` sur un corps `{}` | `422` — `version` est **obligatoire**, §18.4 |
| `T11-7` | la forme que j'avais **inventée** | deux formes **différentes** selon l'action |

**Les deux sont de la même nature :** mon client parlait à un `fetch` bouchonné qui rendait ce que
*j'avais décidé*. Un bouchon ne connaît pas le contrat — il connaît **ma lecture** du contrat, et
c'est exactement ce qui était faux.

> **La règle, sans jargon :** un test qui bouchonne une frontière — `fetch`, un client HTTP, une
> base, un service tiers — éprouve **ton code des deux côtés du bouchon**. Il ne peut rien dire de
> ce qui est **au-delà**. **Avant de déclarer un client terminé, fais-lui faire un aller-retour
> RÉEL**, une fois, à la main. Une seule suffit : les deux défauts sont apparus au premier appel.

**Et la parade qui reste dans le dépôt n'est pas une promesse, c'est un test de forme.** Le
validateur du contrat porte désormais **les deux formes relevées sur la pile**, en clair, avec la
date du relevé — et un test exige qu'il refuse l'une là où l'on attend l'autre. Le prochain qui
changera une réponse cassera ce test au lieu de casser un écran.

**Deux corollaires mesurés le même jour :**

- **le test qui manquait n'était pas un test de plus, c'était un test d'une AUTRE nature.** Mes onze
  tests lisaient la **réponse** ; aucun ne lisait le **corps envoyé**. Celui qui l'a fait —
  `JSON.parse(action.body)` — tient en trois lignes, et il aurait attrapé `T11-6` seul. *Quand tu
  bouchonnes une frontière, teste ce que tu ENVOIES autant que ce que tu reçois* ;
- **ce que l'API rend en plus vaut souvent la peine d'être montré.** `relations_closes` et
  `sessions_revoquees` n'étaient dans aucun de mes plans : ils sont apparus dans la réponse réelle,
  et l'écran les affiche désormais. **Annoncer une conséquence avant le geste est une promesse ; la
  montrer après est une mesure.**

---

---

## 7.44 Quand tu retires un filtre pour l'éprouver, PROUVE que le processus l'a vu

**Apport de `T6` du LOT 6, et c'est le §7.0 quatrième proposition appliqué non pas à un contrôle
mais à L'OUTIL QUI MESURE LES CONTRÔLES.**

La campagne de témoins de `T6` retire quinze filtres un par un et compte les tests qui tombent. Elle
a annoncé **cinq** filtres muets. Rejoué **isolément**, l'un d'eux faisait pourtant tomber son test.

Diagnostic avant correction (§7.18) : une sonde qui compare l'empreinte du SQL **vu par le
processus** à celle du SQL **du disque**.

```text
responsibility_type    taille=13458  attendu=c30214dda39c  vu=c30214dda39c  OK
person_id              taille=13487  attendu=52a5534c10bb  vu=52a5534c10bb  OK
entity_id resp.        taille=13487  attendu=ed527f756226  vu=52a5534c10bb  ** BYTECODE PERIME **
archived_at page       taille=13487  attendu=e51fb5bc463e  vu=52a5534c10bb  ** BYTECODE PERIME **
entity_id page         taille=13487  attendu=482a3ce77fae  vu=52a5534c10bb  ** BYTECODE PERIME **
```

**CPython invalide un `.pyc` sur le couple `(mtime TRONQUÉ À LA SECONDE, taille en octets)`.** Quatre
variantes pesaient **exactement 13 487 octets** — retirer ` AND entity_id = :entite` et retirer
` AND archived_at IS NULL` coûtent le même nombre de caractères — et chaque exécution durait moins
d'une seconde. Trois d'entre elles ont donc exécuté le bytecode d'une variante **précédente**.

> **La règle, sans jargon :** « 0 échec » était la **même observation** pour deux causes opposées —
> « ce filtre ne travaille pas » et « ce filtre n'a jamais été retiré ». C'est le §7.0 quatrième
> proposition, et il faut le retourner contre l'outil : **quand tu modifies un fichier pour
> l'éprouver, fais dire au processus ce qu'il a réellement chargé.** Une empreinte suffit.
>
> **Et le défaut est NON DÉTERMINISTE**, ce qui le rend pire qu'un défaut franc : selon le temps que
> prend chaque exécution, il se manifeste ou non. Deux campagnes successives donnaient des résultats
> différents sur le même code.

**Parade, et elle est mécanique plutôt que vigilante** — c'est le §7.2 : quand une classe d'erreur
dépend de l'attention, change d'outil.

```bash
# Dans toute campagne qui MODIFIE des sources entre deux executions :
subprocess.run([...], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
```

**Elle a été MESURÉE avant d'être appliquée** (§7.38) : la même sonde sous
`PYTHONDONTWRITEBYTECODE=1` rend les quatre empreintes attendues. Puis la campagne relancée a donné
un résultat stable — et c'est elle qui a révélé **deux vrais trous de couverture** que la première
passe avait noyés parmi cinq faux.

**Et le résultat final vaut d'être lu :** sur quinze filtres, **treize travaillent**, et les **deux**
qui restent sont mesurés **redondants** au catalogue — une biconditionnelle de vérification et une
clé étrangère composite. Troisième occurrence de la classe `T4-2` / `T5-1`, et trois fois sur trois,
ce qui protégeait vraiment était **une contrainte ailleurs, déjà sous contrôle**.

## 7.45 Un mot employé comme VALEUR et absent de la légende se définit AILLEURS

**Apport de `T7` du LOT 6, et il a clos un écart que `T6` croyait insoluble.**

`ECART-063` annonçait que l'annexe A **§13 et §18 donnent deux grilles différentes** pour
« Archiver un contenu », divergentes **dans les deux sens**. `T6` avait lu, prudemment : *deux
mots différents dans la même colonne du même tableau, donc deux droits différents* — et la
consigne était de retenir la plus restrictive de chaque cellule.

**Ce qui a corrigé cette lecture n'est pas un raisonnement, c'est une recherche du mot dans
tout le document.**

| Mesure du 19/09/2026 | Résultat |
|---|---|
| la **légende §4** définit-elle `Périmètre` ? | **NON** — elle définit dix valeurs, et pas celle-là |
| combien de cellules l'emploient ? | **plus de vingt**, dans six sections différentes |
| le document le définit-il ailleurs ? | **OUI — le §3**, dans une colonne intitulée « **Périmètre principal** » |

Et ce que le §3 donne referme la question : l'`ESM` y a « **ensemble de son entité** », soit
**mot pour mot** la définition de `Entité` au §4. Les deux mots dénotent le même ensemble, cinq
rôles sur six concordaient déjà, et la sixième cellule — celle du `DSM` — **n'est pas
exprimable** : son périmètre est un ensemble de **personnes**, et `content_page` ne porte
aucune colonne qui rattache une page à un DSM.

> **La règle, sans jargon :** quand un tableau emploie un mot que sa légende ne définit pas,
> **ne déduis pas son sens de son contraste avec les autres**. Cherche-le dans le document —
> en titre de section, en en-tête de colonne, en prose sous un tableau. Le §7.29 apprenait à
> chercher une décision qu'on te dit à prendre ; celui-ci apprend à chercher un **mot** dont on
> te laisse deviner le sens.

**Et la leçon vaut dans l'autre sens, ce qui la rend utilisable.** `T6` a eu **raison** de ne
pas trancher : lire deux mots comme deux droits est la lecture restrictive, et elle était sans
risque. Ce qu'il fallait faire n'était pas deviner mieux, c'était **mesurer** — et la mesure
demandait trois minutes. *Quand deux lectures d'un document s'opposent, la question n'est pas
laquelle est la plus plausible, c'est ce que le document dit **ailleurs**.*

---

## 7.46 Quand un document NOMME une validation, demande-toi si c'est LA validation

**Apport de `T8` du LOT 6, et c'est le §7.29 d'un cran plus bas.**

Le §7.29 apprend à chercher une décision qu'on te dit à prendre ; le §7.45, à chercher
un **mot** dont on te laisse deviner le sens. Celui-ci porte sur une **règle** que le
document écrit en toutes lettres, et qui **ne suffit pas**.

Le modèle §15.3 et le cahier §13 écrivent tous deux, mot pour mot : « Les URL sont
validées selon une **liste de protocoles autorisés** ». C'est une exigence claire, écrite
deux fois, et l'appliquer à la lettre laisse un trou. Mesure du 22/09/2026 :

| Adresse | `scheme` | `netloc` | Une liste blanche de protocoles ? |
|---|---|---|---|
| `https://hub.exemple.test/` | `https` | `hub.exemple.test` | acceptée, et c'est juste |
| **`https:alert(1)`** | **`https`** | **vide** | **acceptée, et elle n'adresse RIEN** |
| `https:/hub.exemple.test` | `https` | vide | acceptée, idem |
| `https://` | `https` | vide | acceptée, idem |

**Un contrôle qui aurait fait exactement ce que le corpus demande aurait accepté trois
chaînes qui ne désignent aucune ressource**, et qu'un navigateur traite comme des
références relatives.

> **La règle, sans jargon :** quand un document nomme une validation — « selon une liste
> de protocoles », « au format attendu », « parmi les valeurs autorisées » — il nomme **un**
> critère, pas forcément **le** critère. **Demande-toi ce que la valeur doit DÉSIGNER, pas
> seulement de quoi elle a l'air.** Une URL doit désigner un serveur ; un protocole
> autorisé n'en fait pas une adresse.

**Et la parade est celle du §7.0, quatrième proposition, posée à l'endroit du besoin :**
avant d'écrire le contrôle, énumère ce qui le **passerait** sans satisfaire l'intention.
Trois minutes de `urlsplit` sur dix chaînes ont donné la réponse, et le refus manquant —
`url_sans_hote` — est devenu le cinquième code d'erreur.

**Un second constat de la même mesure, et il porte sur les analyseurs.** `urlsplit`
**retire silencieusement** `\t`, `\r` et `\n` : `java\nscript:` rend le protocole
`javascript`. Un contrôle qui lirait la chaîne **brute** verrait `java\nscript` là où le
navigateur verra `javascript`.

La parade retenue n'énumère **aucun caractère interdit** — recopier la liste interne de
CPython la ferait vieillir à la première version (§7.27), et c'est précisément la faute que
le §7.34 décrit. Elle exige que **le segment tapé soit, à la casse près, celui que
l'analyseur a lu**, et refuse toute divergence sans chercher laquelle. *Quand tu ne peux pas
énumérer ce qui est dangereux, exige que ce que tu lis soit ce qui a été écrit.*

---

## 7.47 Une date ABSOLUE dans un test est une bombe à retardement datée

**Apport du correctif du 22/09/2026, `DEC-588`, et c'est la seule classe de ce projet
qui fait rougir `develop` SANS QUE PERSONNE N'AIT TOUCHÉ UNE LIGNE.**

La porte était verte le 19/09 à la fusion de `#164`. Le 22/09, la même `develop` rend
**dix échecs** — mesuré dans un `git worktree` sur `origin/develop`, sans une ligne de
la sous-étape en cours.

| Ce qui bougeait | Ce qui ne bougeait pas | Ce qui les compare |
|---|---|---|
| `created_at` au défaut `now()` de la base | `expires_at`, dérivé d'un `instant` **injecté** au 22/08/2026 | `ck_service_token_expiration_apres_creation` |
| `arrival_date` à `current_date - 30` | `departure_date` au 20/08/2026 | le `daterange` du §25.2 |

Le premier a tenu **trente jours** puis a fait tomber **neuf** tests d'un coup ; le second
a basculé le 20/09, quand `current_date - 30` a dépassé le 20/08 et que l'arrivée est
passée **après** le départ.

> **La règle, sans jargon :** c'est le §7.0, sixième proposition, appliqué au **temps** —
> deux grandeurs qu'une contrainte compare doivent venir de la **même source**. Quand tu
> écris une date dans un décor, demande-toi **à quoi elle sera comparée** : si l'autre
> borne vient de `now()` ou de `current_date`, alors **elle aussi doit en venir**.

**Et aucune des sept propositions du §7.0 ne pouvait l'attraper**, ce qui est le point.
Les tests **passaient**. Ils étaient justes le jour de leur écriture, et ils le sont restés
jusqu'à une date qu'on pouvait calculer mais que personne n'avait calculée. C'est le §7.21
dans sa forme la plus pure — *un contrôle juste hier peut être faux aujourd'hui* — sauf
qu'ici **ce n'est pas nous qui l'avons rendu faux, c'est le calendrier**.

**La correction porte sur le MÉCANISME, pas sur les instances.** `creer_un_jeton` écrit
désormais `created_at` depuis l'instant qu'on lui injecte, ce qui est déjà l'idiome de
`app/content/ecriture.py` et de `liens.py` — ce service en était l'exception. Et l'ancre
`INSTANT` est **dérivée de `now()`** : elle ne perd aucun déterminisme, aucune assertion
du fichier ne dépendant d'une date du calendrier, toutes étant **relatives** à l'ancre.
*La figer garantissait une panne datée sans rien apporter.*

**LE RÉSIDUEL EST NOMMÉ, ET AUCUN GARDE-FOU AUTOMATIQUE N'EST POSÉ.** Recensement du
22/09/2026 : **66 dates absolues** dans les tests, dont **11 dans le futur** — neuf
`DECEMBRE = 2026-12-01`, un `2027-01-01` dans `test_bureaux.py`, un
`PLUS_TARD = 2027-06-01` dans `test_cycle_de_vie_des_contenus.py`. **Ce sont des
échéances, pas des défauts.**

Et l'absence de garde-fou est **délibérée, parce qu'elle est mesurée** : la co-occurrence
d'une date absolue et d'un `now()` dans un même fichier signale **30 fichiers sur 31**.
Un garde-fou à faux positifs apprend à passer outre (§7.25), et il n'aurait rien discriminé.
**Une liste datée est actionnable ; une heuristique ne l'aurait pas été.**

> **Si `develop` rougit un matin sans qu'aucun commit ne l'explique, commence ici.** Lis la
> date des valeurs en cause avant de chercher une régression : le `git worktree` sur
> `origin/develop` **sur la même base** donne le verdict en deux minutes (§7.22).

---

# 8. Ce qui reste ouvert

## 8.1 Écarts — **14 ouverts**, dérivés du registre le 01/10/2026 (le total est au §1)

> **Ce compte était resté en état LOT 1 — « 5 ouverts sur 22 » — jusqu'à `T10`.** Il ne l'a pas été
> par négligence : les cinq écarts du LOT 1 étaient tous justes, et le LOT 2 en a ouvert deux de plus
> sans que ce tableau ne les reçoive. **Classe `ECART-021` : un compte qui n'est pas dérivé de sa
> source vieillit en silence.** La source est `docs/decisions/registre-ecarts.md`, dont l'en-tête
> porte le total, et `make docs-check` en dérive les séquences. **Recompte avant de réutiliser.**

| ID | Objet | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV définitif relève de `QO-096` | LOT 9 |
| `ECART-012` | `intercontrat` imposé à une direction générale. **Instruit en `T5` du LOT 5**, position de Jonathan reconduite sans trancher à l'ouverture du LOT 7 (§8.1 de `fiche-lot-7.md`) : **la décision revient toujours à Léa** | **Échéance dépassée depuis le LOT 6.** Non bloquant |
| `ECART-013` | Les 5 tâches communes du prototype ont des identifiants différents | LOT 7, se résout structurellement à `T4` |
| `ECART-014` | « Représentant de cercle » contre « Booster » | **Échéance dépassée** — n'a pas mordu au LOT 6, à confirmer par Léa si un écran du LOT 7 reprend ce vocabulaire |
| `ECART-015` | Le prototype ne fournit ni descriptions de cercles ni liens internes | **Échéance dépassée** — sans objet direct pour le LOT 7, qui ne touche ni cercle ni lien |
| `ECART-066` | **NOUVEAU, ouverture du LOT 7.** La matrice donne `ESM` → « Conditionnel » sur la restauration d'un parcours d'onboarding archivé et d'une version de modèle, et `ARB-DROIT-003` — qui définit « Conditionnel » pour cinq autres ressources — ne nomme ni l'un ni l'autre | LOT 7, à trancher avant `T6`/`T11` |
| `ECART-031` | Le §8.4 exige « un bureau **publié** avec un à trois responsables actifs », mais le §8.3 ne déclare **aucun état de publication** sur `office` | avant le LOT 6 |
| `ECART-033` | **CLOS en `T1` du LOT 3.** `make ports` concaténait les deux flux de Compose puis parsait le tout en JSON : un avertissement le cassait, **sans nommer la cause**. Il était juste à sa date — `ECART-024` à l'identique |
| `ECART-061` | **Un mot de passe provisoire n'est jamais forcé de changer** : `must_change` est servi par l'API sous le nom `changement_exige`, **aucun écran ne le lit**, et la session est ouverte quand même. `DEC-527` affirme le contraire. **Mesuré le 12/09/2026** | avant production, à instruire au LOT 13 |
| ~~`ECART-062`~~ | **CLOS le 25/09/2026, `QO-124`, `DEC-594`.** La lecture restrictive du §13 — le DSM n'a aucune page à éditer — est définitive. Aucun code ne change | close |
| `ECART-064` | **Le §18.1 exige un motif pour « toute intervention du super-administrateur dans une entité », et AUCUNE route du dépôt n'en demande un.** `archive_reason` et `assignment_reason` existent depuis le LOT 2 et **rien ne les écrit** — zéro occurrence mesurée le 19/09/2026 hors de leur déclaration. Non bloquant pour le MVP ; **à instruire au LOT 10 avec `audit_event`**, où le motif trouvera une table qui le conserve et un lecteur qui le lit |
| `ECART-065` | **NOUVEAU, `T9`.** Le `<h1>` du cadre applicatif, `useTitreDeLaPage`, ne compare le chemin courant qu'à l'ÉGALITÉ d'un chemin de rubrique : toute sous-page paramétrée retombe sur « Accueil de l'entité », un titre **faux**. Corrigé pour les deux routes de `T9` (cercle, bureau). **La fiche profil du LOT 5 `T11` porte le même défaut et n'est pas corrigée** — hors périmètre d'une sous-étape du LOT 6 | LOT 7 ou 9, à la prochaine sous-page paramétrée |
| `ECART-032` | **Le backlog interdit plus large que le cahier, la matrice ET le modèle réunis** : « aucune responsabilité **métier** active dans plusieurs entités » là où les trois autres restreignent au seul **Booster**. Le cahier prévaut, le livrable est conforme — **mais un relecteur du backlog conclurait à un critère manquant** | à annoncer à `G2` |

`ECART-023` est ouvert et clos en **`T8`** — la fiche énumérait six des sept séparations du cahier §22.2, et empruntait « Mailpit exclusif » aux LOTS 11 et 13.

`ECART-006` est **clos** en `T3`, et `ECART-022` en **`T7`** : `.env.example` est en **v1.1**,
77 variables, 77 noms distincts. `ECART-022` couvrait cinq constats d'une même classe — un nombre
ou une affirmation non dérivés de leur source — dont le plus sérieux n'était pas documentaire :
**`make env` ne réconcilie pas un `.env` existant**, et trois variables y manquaient depuis `T3` et
`T4`. `make env-check` est la parade, et elle est dans `make check`.

## 8.2 Questions ouvertes utiles à la suite du LOT 1

| ID | Objet | Quand |
|---|---|---|
| ~~`QO-085`~~ | **CLOSE en `T8`.** Deux stacks **simultanées** mesurées : **836,6 Mio pour seize services, 10,5 %** des 7 936 Mio. `DEC-440` reste en vigueur — mesurer la simultanéité ne l'autorise pas | close |
| `QO-111` | **Fournisseur de collation PostgreSQL.** Ne se change pas sans recréer le cluster | LOT 2 |
| `QO-112` | **Liste des extensions PostgreSQL.** `CREATE EXTENSION` exige des droits élevés | LOT 2 |
| `QO-113` | **Conservation calendaire des journaux.** `json-file` borne par la taille | LOT 13 |
| `QO-094` | Second référent technique — conditionne `DEC-429` | avant production |
| `QO-106` | 9 étiquettes GitHub par défaut subsistent | choix de Jonathan |
| `QO-114` | **Droits d'administration pour la production temporaire locale.** Jonathan n'en a aucun : `restic`, Uptime Kuma et les services au démarrage en réclament habituellement | **LOT 13, à instruire avant** |
| ~~`QO-120`~~ | **CLOSE en `T8` du LOT 6**, `DEC-587` : un lien interne n'accepte que `https`, et `http` est refusé **sous son propre code**. Le corpus exigeait « une liste de protocoles autorisés » **sans la donner** — zéro occurrence mesurée | close |
| ~~`QO-123`~~ | **CLOSE le 25/09/2026**, `DEC-591` pour la bibliothèque (`lucide-react`), `DEC-593` pour la convention (référence facultative, texte libre — déjà ce que `T10` sert) | close |
| ~~`QO-119`~~ | **CLOSE le 25/09/2026**, `DEC-592` : onze types de blocs, la lecture la plus large — déjà ce que `DEC-577` applique depuis `T1` | close |
| `QO-121` | **Quels champs chaque type de bloc porte-t-il dans son `payload_json` ?** Onze petites décisions, pas une seule — **reportée par Jonathan le 25/09/2026**, explicitement. `T11` avance sur ses autres critères, le contenu reste opaque | **bloquante avant qu'un écran ne propose la création d'un bloc** |

## 8.3 Risques ouverts qui te concernent

| ID | Objet |
|---|---|
| `ROAD-RSK-026` | iCloud — **matérialisé**, résiduel accepté par `DEC-457`. `make icloud-verify` |
| `ROAD-RSK-029` | Un formateur peut réécrire les documents immuables. **Garde-fou posé en `T6`** : `make docs-check` recalcule les 5 empreintes à chaque pull request. Le risque reste ouvert — tout outil ajouté plus tard le rouvrirait — mais il est désormais **détecté** |
| ~~`ROAD-RSK-030`~~ | **CLOS en `T7`.** Image `web` de 1,02 Gio → **84,9 Mo**. Résiduel nommé : `uv` et `uvx`, **55,1 Mio**, restent dans `api` et `worker` — poids seulement, Trivy n'y trouve rien |
| ~~`ROAD-RSK-031`~~ | **CLOS en `T7`.** Deux cibles nommées. **`T8` doit encore SÉLECTIONNER `execution`** dans la surcouche de recette — `make images-check` échoue si elle ne nomme aucune cible |
| `ROAD-RSK-015` | Secret intégré au code — **mesure effective depuis `T6`** : Gitleaks sur chaque pull request, historique compris, avec des règles taillées sur les formats de ce projet |
| `ROAD-RSK-032` | Avis `GHSA-mh99-v99m-4gvg`, sévérité haute, dans une dépendance **de développement** de `jsx-a11y`. **Aucun correctif applicable** : la 1.x n'en a pas, et la 5.x casse le lint — mesuré. Tolérance nommée, `DEC-474` |
| `ROAD-RSK-033` | Les images publiées héritent des vulnérabilités de leurs bases : `python:3.12-slim` porte **23 avis `HIGH`/`CRITICAL` dont AUCUN corrigeable**. **Nos couches n'en ajoutent aucune.** Résiduel accepté par `DEC-482`, à réévaluer **avant le LOT 13** |
| `ROAD-RSK-034` | **Nouveau, et mesuré en `T8`.** **Publier un port perce l'isolement inter-réseaux de Docker** : la règle `ACCEPT` d'un port publié précède les règles `DOCKER-ISOLATION`. Les **7** ports publiés du développement sont joignables depuis la recette, et une connexion à sa base **aboutit**. Le cahier §22.2 exige un réseau **distinct**, ce qui est acquis — pas l'inatteignabilité. **La barrière effective est la cinquième séparation, les secrets**, et `make separations-check` en fait une **exigence** : avec le mot de passe de la recette, la base de dev **refuse**. Résiduel accepté au LOT 1, **à réévaluer avant le LOT 13**, où la production locale portera des données réelles |

## 8.4 Contenus en attente de relecture

Les 29 éléments `CONT-001` à `CONT-029` sont au statut **`à relire`**. **Aucun n'est publiable en
l'état.**

---

# 9. Par où commencer : `G7` est franchie, aucun lot suivant n'est ouvert

## 9.0 Ce que les documents ont démenti, et ce qu'il faut en retenir

**Ce document, les fiches de lot et le backlog ont affirmé faux une vingtaine de fois**, et chaque
fois c'était une affirmation **jamais mesurée**. La liste s'allonge par des voies différentes, et
c'est cela qui compte :

- **une FICHE de lot**, six fois. Six séparations là où le cahier en compte sept (`ECART-023`) ; « le
  cahier exige une limitation **sans donner de seuil** » alors que le §20.2 en donne six
  (`ECART-034`) ; « **aucun document n'énumère** les scopes » alors que le §22 en donne cinq
  (`ECART-036`) ; une question à ouvrir qui portait **déjà** le numéro `QO-072` ; et trois lignes du
  §30 annonçant des reclassements **déjà faits** ou dus à un autre lot. **Le §8 de `fiche-lot-3.md` a
  été faux trois fois sur quatre.**
- **le BACKLOG** — `US006` exige d'invalider les **invitations**, qui n'existent nulle part dans le
  modèle (`ECART-035`) ; `US005` attache la révocation à l'archivage quand le §24.1 n'a **aucune**
  transition `Active --> Archived` ;
- **le MODÈLE** — son diagramme §11 déclare `SERVICE_ACCOUNT ||--o{ AUTH_EVENT`, et la table posée
  par `T2` ne portait pas ce lien (`ECART-037`) ;
- **des CONTRÔLES du dépôt**, justes quand ils ont été écrits et rendus faux par un second
  environnement, par un avertissement de Compose, ou par nos propres ajouts ;
- **un GARDE-FOU qui passait au vert sur un vrai problème** : `make icloud-verify` ne cherchait que
  les copies de conflit, et quatre fichiers ont été **remis à une version antérieure** sans qu'il ne
  dise rien.

**Vérifie avant de bâtir dessus — surtout quand un document t'annonce qu'il te reste une décision à
prendre.** C'est le sens inverse de l'avertissement habituel, et il s'est produit trois fois au LOT 3.

---

## 9.1 Où en est exactement le projet

**Les LOTS 0 à 7 sont terminés.** `G7` a été franchie le **30/09/2026** (`DEC-617`), tag `v0.7.0`
sur `main`. Les quinze sous-étapes du LOT 7 sont réalisées, de la structure au parcours, aux deux
écrans puis à la recette HTTPS réelle. Le §30 est classé à **16 acquis, 2 partiels et 7 reportés** ;
Tess, Léa, Diane et Jonathan ont validé les parcours mission et intercontrat. **Le LOT 8 est ouvert
depuis le 01/10/2026** (`DEC-619`) ; `T1` à `T4` sont faites (`DEC-620` à `DEC-623`) et `T5` est la sous-étape suivante.

| Fait | Ce que ça donne |
|---|---|
| LOT 3 | l'authentification complète : magic link, comptes administrateurs, sessions, CSRF, limitation de débit, révocation au départ, comptes de service, **et les huit écrans** |
| LOT 4 | le portail national, le cadre applicatif, l'entité consultée, la navigation, la carte, et la résolution des permissions de la matrice §23.1 |
| LOT 5, les ONZE | les trois tables de média, le trombinoscope paginé, la recherche sans accents, la fiche profil, la miniature et son autorisation, l'écriture dans son périmètre, l'archivage et la restauration, l'historique organisationnel, et les **deux écrans** — le trombinoscope et la page de profil |
| LOT 6, les DOUZE — **VERROUILLÉ** | les trois tables éditoriales (migration `0017`), la page Framework, les pages détaillées d'un cercle et d'un bureau, le **rendu** des blocs, l'**écriture** d'un contenu dans son périmètre, son **cycle de vie** — brouillon, publication, archivage, restauration — les **liens internes**, les **trois écrans de lecture**, les **écrans d'édition**, **le témoin du critère de sortie 2** et **la reprise relue** (`T11`), puis **la recette et le §30** (`T12`, un reclassement trouvé et corrigé). Détail : `fiche-lot-6.md` |
| LOT 7, `T1`–`T15` — **VERROUILLÉ** | les huit tables, la fiche d'arrivée, les modèles, parcours et tâches, leur cycle de vie, le suivi et les deux écrans ont été construits dans `T1` à `T14`. **`T15`** les a rejoués sur la recette isolée, à travers Caddy/HTTPS, dans un parcours complet `arrival_date` → deux échéances → progression `1/2` puis `2/2` → archivage automatique ; le décor a été nettoyé. Il corrige aussi le classement périmé de `§30.13` à `§30.15` : **16 acquis, 2 partiels, 7 reportés**. Les validations humaines sont acquises et `G7` est franchie (`DEC-617`). Détail : `compte-rendu-t{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}-lot-7.md` |
| LOT 8 — **OUVERT**, `T1`–`T4` faites | six stories, quatre `P0` et deux `P1`, découpées en quatorze sous-étapes. Épic `#206`, stories `#207` à `#212`. Les quatre tables du modèle événementiel sont posées par la migration `0022` (`DEC-620`) ; `T2` sert leur lecture paginée à venir/passée, annulés inclus, archives exclues (`DEC-621`) ; `T3` sert la création, `ECART-067` clos par la cinquième table `event_dsm_scope` (migration `0023`, `DEC-622`) ; `T4` sert la modification et la publication, avec rattachements multiples et deux grilles distinctes pour le DSM (`DEC-623`). `T5` est la suivante. Détail : `fiche-lot-8.md`, `compte-rendu-t{1,2,3,4}-lot-8.md` |
| Recette | **réépinglée** sur les images de `07571f9` (`T11` du LOT 6), rôle d'**exécution** — `DEC-539`, mesuré |
| Contrôles | les contrôles de stack sont **tous** dans la CI, chacun portant ses témoins. **`make help` et `ci.yml` font foi sur leur nombre**, jamais cette cellule |

**`ECART-066` est CLOS** : ses deux volets — version de modèle (`T6`, `DEC-605`) et parcours (`T11`,
`DEC-611`) — sont résolus, l'ESM restaurant librement dans son entité dans les deux cas, la seconde
réponse ayant été reposée EXPLICITEMENT et jamais présumée de la première. **`QO-121` reste
ouverte**, héritée du LOT 6 (champs de `payload_json`, report explicite de Jonathan, non bloquante).
`ECART-012` (statut professionnel d'une direction générale, à Léa) reste ouvert et non bloquant.
**Un résidu du LOT 5, retrouvé en écrivant `T3`, reste sans propriétaire** : `entity_membership.
short_bio`/`fun_fact` n'ont toujours aucune route d'écriture — reporté à `T7` du LOT 5, jamais
rattrapé depuis — et rien ne relie `arrival_profile.short_intro` à ce champ.

---

## 9.2 Ce qu'il reste à faire, et dans quel ordre

**Le LOT 7 est verrouillé** — quinze sous-étapes, `DEC-598` à `DEC-615`, porte `G7` franchie par
`DEC-617`. **Le LOT 8 est ouvert** par `DEC-619`, avec quatorze sous-étapes validées. `T1` à `T4`
sont faites par `DEC-620` à `DEC-623`. **`ECART-067` est CLOS** — la portée « consultants » du
DSM, inexprimable par l'entité ou les cercles/bureaux du modèle, est posée par une cinquième
table symétrique aux deux portées existantes, `event_dsm_scope` (migration `0023`), sur
arbitrage explicite de Jonathan : table dédiée plutôt qu'une colonne unique sur `event`, pour
rester cohérente avec le motif déjà posé par `T1`. **`T4` a livré la modification et la
publication** : même grille que la création pour `ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`, mais le
DSM en porte DEUX distinctes — « Modifier » accepte un événement créé OU rattaché à son
périmètre, « Publier » n'accepte QUE son périmètre (ses consultants nommés), jamais l'entité
d'un événement qu'il a simplement créé. Les rattachements multiples (plusieurs cercles/bureaux à
la fois) sont revalidés code par code, indépendamment du périmètre global déjà vérifié. La
prochaine étape est `T5` — annulation, archivage et restauration. `ECART-068` borne toujours les
écritures ultérieures et doit être résolu avant de fermer `US004` ; il ne justifie pas
d'anticiper silencieusement `audit_event` (LOT 10).
**`ECART-066` est CLOS** — les deux
volets (version de modèle, `T6` ; parcours, `T11`) sont résolus, la seconde réponse ayant été
reposée explicitement, jamais présumée de la première. `T11` s'est accroché à
`enregistrer_un_depart` (LOT 3, `T9`) sans dupliquer sa logique de révocation, exactement comme
prévu. `T12` a fermé la dernière ligne de consultation du §8.1 encore sans consommateur —
« Consulter les tâches en retard » — sans écrire de route sur les deux autres, déjà servies par
`T7` et `T11`. `T13` a livré les écrans en réutilisant intégralement les routes de `T2`/`T3`/`T7`/
`T8` : aucune route API nouvelle, une seule extension d'identité sur `/permissions` — et a trouvé,
dans un contrat écrit à `T7`, un défaut jamais exercé par un écran avant elle. `T14` a livré les
écrans d'administration, construit le script de pile que `T13` avait différé, et a dû ajouter UNE
route API — `GET …/onboarding/templates` — trouvée en construisant l'écran : ni `T5` ni `T6` n'en
avaient posé la lecture. `T15` a produit la recette complète et la checklist ; les quatre
validations nominatives sont acquises et la porte `G7` est franchie.

1. **Lire la matrice §7, §8 et §9 DANS LE DOCUMENT**, jamais dans un résumé. Le §2.1 de la fiche
   porte **deux** pièges mesurés : `DSM`/`BOOST` ont un périmètre de **consultation** sur le parcours
   d'un collaborateur (§8.1) mais sont à **tiret** sur toute **action** de tâche ; `OFFICE` est à
   tiret partout sur les modèles d'onboarding (§9). **L'erreur serait d'accorder le droit d'agir
   parce que le droit de consulter existe déjà.**
2. **`photo_authorization` existe déjà** depuis le LOT 5 (`0014`) — `T1` ne l'a pas recréée,
   `arrival_profile.photo_media_id` s'y rattache.
3. **`ECART-013` est résolu STRUCTURELLEMENT depuis `T4`** (`DEC-603`) : un identifiant fonctionnel
   unique par tâche commune, jamais la numérotation à deux préfixes du prototype. **MIS À
   L'ÉPREUVE POUR DE VRAI PAR `T10`** (`DEC-610`, `US007`) : un changement de statut effectif
   retient les tâches `completed` communes par leur `task_reference_id`, `completed_at`/
   `completed_by_person_id` copiés, `title_snapshot`/`due_at` recalculés depuis la nouvelle
   version.
4. ~~La fenêtre de cinq minutes doit être injectable dès `T8`.~~ **FAIT PAR `T8` ET `T9`** : la
   précondition compare l'`instant` réel de la requête à `completed_at`, une valeur déjà STOCKÉE en
   base — les témoins « hors délai » reculent cette valeur par SQL, jamais un `sleep()` ni une
   horloge mockée. **`T9` a réouvert après le MÊME délai**, inversé strictement (`completed_at <
   instant - 5 min` contre `>=` pour l'annulation) : réutilise la lecture de `completed_at`,
   n'invente pas un second mécanisme de fenêtre — aucune sous-étape suivante n'a plus besoin de
   fenêtre temporelle sur cette table.
5. **Vérifier les points du §8 de la fiche contre le corpus avant d'instruire quoi que ce soit**
   (§7.29, huitième occurrence : `ECART-066` en est la preuve, trouvé en cherchant « Conditionnel »
   dans tout le corpus plutôt qu'en le devinant).
6. **`make isolation-check` connaît désormais TROIS raisons légitimes à une clé simple** entre deux
   tables locales — cible globale, source `entity_id` nullable (`T8-1`), et depuis `T1` : cible
   `entity_id` nullable. Si une nouvelle table nullable apparaît, relis
   `infra/scripts/verifier-isolation.py` §1 avant d'improviser une composite qui casserait le cas
   global.
7. **`resoudre_les_permissions` n'accorde un rôle de responsabilité que dans l'entité PRINCIPALE de
   l'acteur** (LOT 4, `est_principale`). Tout décor de test qui donne une responsabilité ESM/DSM/
   Booster à un acteur SANS lui donner sa propre appartenance dans l'entité obtient un ensemble de
   rôles VIDE, en silence — trouvé en `T2` du LOT 7, une règle préexistante que le lot n'avait
   simplement jamais exercée avec un acteur dépourvu d'appartenance locale.
8. **`entity_membership.short_bio`/`fun_fact` n'ont AUCUNE route d'écriture**, malgré ce qu'une
   lecture rapide du §6.1 pourrait laisser croire. `T7` du LOT 5 les a explicitement **reportés**
   (`compte-rendu-t7-lot-5.md`), et rien depuis ne les a rattrapés — vérifié par `grep` avant
   d'écrire `T3`, une affirmation contraire avait été rédigée puis corrigée (§2.5 de
   `compte-rendu-t3-lot-7.md`). Ne suppose jamais qu'un champ du modèle a une route parce qu'il a
   une lecture : vérifie par `grep`, pas par mémoire.
9. **`Support` (et `Support cercle`) n'est dans AUCUNE légende du corpus** — §4 de la matrice ne
   le définit pas, comme `Périmètre` au LOT 6 (§7.45). S'il réapparaît dans une cellule d'un lot
   futur, cherche-le dans TOUT le corpus avant de lui inventer une règle : au §7, il couvre
   exactement `Entité`/`Cercle`/`Global`, sans exigence supplémentaire.
10. **Une table de la matrice peut porter une ligne DE PLUS que celle qu'on vient de coder** —
    `T3` a fusionné en bloquant toute écriture après publication, avant de trouver « Corriger
    après publication », une quatrième ligne du §7 juste sous les trois déjà lues (`DEC-602`).
    Avant de déclarer une grille de permissions complète, relis les lignes VOISINES de celles que
    tu codes, pas seulement celles que la fiche de lot nomme explicitement.
11. ~~`onboarding_template_version.state` réutilise la MAUVAISE énumération, posée par `T1`.~~
    **CORRIGÉ PAR `T5`, MIGRATION `0021`** : `EtatDeLaVersionDuModele` (`draft`/`published`/
    `retired`) remplace `EtatDuModele` sur `onboarding_template_version.state`, jamais en modifiant
    `0020` déjà appliquée. Zéro ligne existante rejetée.
12. ~~`onboarding_template` porte de vraies colonnes de portée, `T6` en héritera pour la
    restauration.~~ **FAIT PAR `T6`** : `peut_restaurer_une_version_de_modele`
    (`app/onboarding/perimetre.py`) résout `ECART-066` (volet modèle) — DSM/BOOST exclus EN BLOC,
    ESM/ADM-E/SUPER autorisés. **FAIT PAR `T11` POUR `onboarding_instance`** : la question a été
    reposée à Jonathan EXPLICITEMENT pour le parcours, jamais présumée de la réponse donnée pour le
    modèle — même réponse, `ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS` (alias de la grille de
    réouverture, `T9`). `ECART-066` est désormais CLOS dans ses deux volets.
13. **Une ancre de test dérivée d'une date absolue peut être fausse LE JOUR MÊME où elle est
    écrite**, pas seulement des semaines plus tard comme au §7.47 du LOT 6. `T7` a fixé `ANCRAGE`
    au lendemain matin, croyant nommer « aujourd'hui » — l'horloge UTC réelle n'avait pas encore
    atteint minuit, et la session de test semblait donc créée dans le FUTUR : `lire_et_
    rafraichir` a refusé `last_activity_at > created_at`. Corrigé en dérivant `ANCRAGE` de
    `now() - buffer`, jamais une date/heure figée. **Toute sous-étape qui ouvre des sessions de
    test dans son décor doit faire de même** — `T8` en particulier, dont la fenêtre de cinq
    minutes manipule le temps directement.
14. **Un critère de sortie du lot peut rester non tenu par une sous-étape qui l'annonçait déjà
    couverte, sans que personne ne le nomme.** Le critère 4 (§1.2 de la fiche) dit « les
    événements de tâche sont historisés […] écrit à `T7`-`T10` » — `T7` livrait la table et
    l'affectation sans y écrire un seul événement, et son propre §2.7 (« ce que `T7` ne fait
    pas ») ne le mentionnait pas. Trouvé en relisant le critère AVANT d'écrire `T8`, jamais après
    la fusion. **Vérifié à nouveau avant `T9`** : le critère tient toujours, `T9` n'écrit qu'un
    événement de plus (`REOPENED`) au même critère. **VÉRIFIÉ UNE TROISIÈME FOIS AVANT `T10`** : le
    critère tient toujours, `T10` ajoute `RETAINED_ON_REPLACEMENT` et `CANCELLED_ON_REPLACEMENT` —
    les deux derniers événements du §13.7, tous les six désormais posés. `T11` n'a plus
    d'événement de tâche à ajouter à ce critère.
15. **Mon propre décor a rejoué le défaut `T7-5`** : un modèle `ENTITY`/`GLOBAL` créé pour le test
    doit l'être avec la session du rôle qui le GÈRE réellement (`ENTITY` → ESM/ADM-E, `GLOBAL` →
    SUPER seul, règle de `T5`), jamais celle de l'acteur dont on teste le GESTE suivant. Un décor
    de test n'est pas le livrable, mais s'y tromper coûte un cycle de diagnostic à chaque fois.
16. **LE DIAGRAMME §24.2 DU MODÈLE EST LA SOURCE DE VÉRITÉ DES TRANSITIONS, ET IL PEUT NOMMER UNE
    TRANSITION QU'UNE SOUS-ÉTAPE ANTÉRIEURE N'AVAIT PAS PRÉVUE.** `T8` avait écrit
    `terminer_une_tache` pour le seul état `todo` ; le diagramme donne pourtant `Reopened ->
    Completed` (« le nouvel arrivant termine à nouveau »), une transition que `T9` seule pouvait
    exercer. Sans le correctif trouvé en écrivant `T9`, une tâche réouverte restait dans une
    impasse permanente — un défaut qui n'aurait pu être vu qu'à l'usage, jamais par un test de
    `T8` seul, puisque `T8` ne connaissait pas encore l'état `reopened`. **`T10` A LU LE MÊME
    DIAGRAMME ET ÉCRIT SES DEUX DERNIÈRES TRANSITIONS** : `Todo -> Cancelled` ET `Reopened ->
    Cancelled` (le diagramme ne nomme que `Todo`, mais `reopened` est le même état « pas terminé »
    sous un autre nom — les deux rejoignent `cancelled`, sans quoi une tâche réouverte laissée
    traînante sur une instance `replaced` serait une troisième forme d'orpheline que rien ne
    décrit) ; « `Completed -> Preserved` » ne correspond à AUCUN état écrit — le modèle §13.6 ne
    déclare que quatre états sur `onboarding_instance_task`, pas de cinquième valeur `preserved` :
    une tâche retenue reste `completed`, dans une instance qui n'est plus `active`, ce qui suffit
    (aucune route n'agit sur une instance non active depuis `T8`/`T9`). **Aucune fonction
    existante n'a eu besoin d'un correctif symétrique à celui de `T9`** : `lire_l_instance_active`
    filtre déjà sur `state='active'`, donc une instance `replaced` cesse d'être vue par
    `terminer_une_tache`/`annuler_la_completion`/`reouvrir_une_tache` sans qu'aucun des trois n'ait
    besoin d'être modifié. Le diagramme n'a donc plus rien à donner : les six transitions sur les
    quatre états sont désormais toutes exercées.
17. **UN NOUVEAU DÉCLENCHEUR AUTOMATIQUE PEUT FERMER LA RÉSOLUTION D'UNE RESSOURCE QUE DES
    SOUS-ÉTAPES ANTÉRIEURES, DÉJÀ FUSIONNÉES, SUPPOSAIENT TOUJOURS OUVERTE.** `T11` a branché
    l'archivage automatique dans `terminer_une_tache` (`T8`) : compléter la DERNIÈRE tâche
    obligatoire archive l'instance dans le MÊME geste. Or `T8` et `T9` résolvaient « l'instance
    actionnable » par `lire_l_instance_active` (`state='active'` strict) — 13 de leurs tests,
    DÉJÀ FUSIONNÉS, sont tombés : la fenêtre de cinq minutes pour annuler, et la réouverture
    administrative, ne trouvaient plus le parcours une fois archivé. **Corrigé en distinguant DEUX
    résolutions** plutôt qu'en relâchant la précondition d'archivage : `lire_l_instance_active`
    (stricte, réservée à l'affectation et à l'archivage manuel) et `lire_l_instance_actionnable`
    (`active` OU `archived`, JAMAIS `replaced` — une instance supplantée par `T10` reste vraiment
    frigée). **La leçon, générale** : avant de brancher un déclencheur automatique sur une action
    déjà livrée, relis TOUS les appelants de la fonction de résolution qu'il pourrait fermer, pas
    seulement le chemin qu'on ajoute — et fais tourner leurs tests, pas seulement les nouveaux.
18. **`uv run pytest` NE RECOMPTE PAS LA MÊME CHOSE SELON LE RÉPERTOIRE D'OÙ IL EST LANCÉ, ET
    `make check`/`make test` LE LANCENT DEPUIS LA RACINE, JAMAIS DEPUIS `apps/api/`.** `T12` a
    d'abord comparé sa preuve de zéro régression depuis `apps/api/`, et obtenu 1 326 tests contre
    les 1 393 attendus — `testpaths` du `pyproject.toml` RACINE couvre `apps/api/tests`,
    `apps/worker/tests` **et** `packages/observabilite/tests`, si bien qu'un `pytest` lancé plus
    bas dans l'arborescence en oublie deux. C'est le §7.28 (« lis ce que la cible fait, pas ce que
    son nom suggère ») appliqué au **répertoire de travail** plutôt qu'à la commande elle-même :
    tout `git worktree` de comparaison doit lancer `pytest` depuis sa **racine**, jamais depuis un
    sous-répertoire, quelle que soit la sous-étape.
19. **UN VALIDATEUR DE CONTRAT ÉCRIT LE MÊME JOUR QU'UNE ROUTE PEUT NE JAMAIS ÊTRE EXERCÉ PAR LES
    VALEURS QUE CETTE ROUTE PRODUIT RÉELLEMENT, TANT QU'AUCUN ÉCRAN NE L'APPELLE.** `validerLeParcours`
    (`T7`) exigeait `instance`/`progression`/`prochaine_tache` nuls ENSEMBLE ou aucun des trois — un
    invariant plausible, écrit en lisant le type de la réponse, jamais en énumérant ce que la fonction
    Python source (`_prochaine_tache`) peut réellement rendre. Elle rend `None` dès qu'aucune tâche
    n'est `todo`/`reopened`, MÊME avec une instance `active` — un cas que `T7` à `T12` n'avaient aucune
    raison de produire dans leurs propres tests (bâtis pour éprouver la permission, pas l'épuisement
    des tâches), et qu'aucun écran n'avait encore appelé en conditions réelles avant `T13`. Le défaut
    est resté invisible **six sous-étapes**, jusqu'à ce qu'un fixture de test l'exerce enfin. **La
    règle, transposable** : quand tu écris un validateur de contrat contre le TYPE d'une réponse,
    relis aussi la fonction qui la PRODUIT côté serveur, et énumère les valeurs qu'elle peut
    réellement rendre — pas seulement celles que les tests déjà écrits exercent.

**Ce qui est livré et attend, ou n'attend plus :**

| État | Où c'est |
|---|---|
| ~~**`exiger_un_role_dans_l_entite`**~~ | **CONSOMMÉE au LOT 5 et au LOT 6** — plusieurs grilles de rôles distinctes déjà en usage, `T4` à `T12` du LOT 7 en ajoutent d'autres pour l'onboarding |
| ~~la **protection CSRF sur une route métier**~~ | **CONSOMMÉE depuis le LOT 5.** Elle vit dans `app/auth/dependances.py` et ne doit **jamais** être recopiée (`DEC-466`) |
| **`exiger_un_scope`** | `apps/api/app/auth/dependances.py`, LOT 3 `T9`. **Attend toujours** : c'est la dépendance des **comptes de service**, qui liront des profils au **LOT 9** |
| ~~**`enregistrer_un_depart`**~~ | **CONSOMMÉE par `T11` du LOT 7** — `archiver_le_parcours_au_depart` s'y accroche depuis `app.people.archivage.archiver_un_profil`, sans dupliquer la logique de révocation, LOT 3 `T9` |
| le **rafraîchissement de session** | `GET …/auth/session` reste la seule écriture n'exigeant pas de jeton — **résiduel nommé depuis le LOT 3, à réexaminer** |
| ~~**les six routes de la fiche d'arrivée et du parcours (`T2`/`T3`/`T7`/`T8`)**~~ | **CONSOMMÉES PAR LEUR PREMIER ÉCRAN, `T13` du LOT 7** — posées entre le 25 et le 27/09/2026, aucune n'avait de bouton avant `PageMonOnboarding.tsx` |
| ~~**les cinq routes du catalogue et des modèles (`T4`/`T5`/`T6`), le suivi (`T12`)**~~ | **CONSOMMÉES PAR LEUR PREMIER ÉCRAN, `T14` du LOT 7** — `T14` a dû AJOUTER une sixième route, `GET …/onboarding/templates` (lister), qu'aucune des trois sous-étapes précédentes n'avait posée faute de consommateur |
| ~~**le script de pile de l'écran du nouvel arrivant**~~ | **CONSTRUIT PAR `T14`, COMBINÉ AVEC LE SIEN, DÉCISION DE JONATHAN TENUE** — `make onboarding-check`, 14 contrôles sur la pile réelle |

---

## 9.3 Ce qui reste ouvert, et qu'il faut savoir

| Élément | Ce qu'il faut savoir |
|---|---|
| **`ECART-012`** | **Attend Léa, et l'échéance est DÉPASSÉE depuis le LOT 6.** Position de Jonathan reconduite le 25/09/2026 sans trancher : rien n'est affiché pour une direction générale sans mission — ce n'est **pas** la résolution de l'écart |
| ~~**`ECART-066`**~~ | **CLOS.** Volet « version de modèle » résolu par `T6` (`DEC-605`) et volet « parcours archivé » résolu par `T11` (`DEC-611`) : l'ESM restaure librement dans son entité dans les deux cas — la seconde réponse a été reposée explicitement, jamais présumée de la première |
| **`ECART-031`** | Clos par `DEC-576`, à l'ouverture du LOT 6. Conservé ici pour mémoire |
| **`ECART-032`** | Le backlog interdit plus large que le cahier, la matrice **et** le modèle. Le cahier prévaut |
| **`ECART-035`** | **Les invitations n'existent pas** dans le modèle. À reprendre au **LOT 9**, où le back-office les créera : la révocation de `T9` du LOT 3 devra alors recevoir une ligne de plus |
| **`ECART-061`** | **`changement_exige` n'a AUCUN consommateur.** Ni garde d'API ni écran : décision de Jonathan, **LOT 13** |
| **`ECART-064`** | Aucune route n'écrit `archive_reason` ni `assignment_reason` — motif d'intervention du super-administrateur, §18.1. **À instruire au LOT 10 avec `audit_event`** ; `T9` du LOT 7 pose son propre `reopen_reason`, **ne pas confondre les deux** |
| **`QO-113`, `QO-114`** | Conservation calendaire des journaux · droits d'administration pour la production locale. **LOT 13** |
| **`ROAD-RSK-033`, `034`** | avis sans correctif dans `python:3.12-slim` · les ports publiés percent l'isolement inter-réseaux. **À réévaluer avant le LOT 13**, inchangés |
| **7 des 25 contrôles du §30** | reportés, chacun rattaché à son lot par `make recette-modele-check`, qui **échoue** si un contrôle cesse d'être classé. Mesure de `T15` : **16 acquis, 2 partiels, 0 inapplicable, 7 reportés**. `§30.13`, `§30.14`, `§30.15`, restés reportés par erreur de registre, sont reclassés acquis sur les témoins existants de `T7`, `T10`, `T9` |
| `CONT-001` à `CONT-029` | 29 contenus au statut **`à relire`**. Aucun n'est publiable en l'état |

---

## 9.4 Ce que le LOT 7 ne doit pas faire

**Au-delà de son périmètre :** aucune table d'un lot postérieur · **aucun événement** ni accueil
dynamique (LOT 8) · aucun import CSV (LOT 9) · **aucun reporting graphique ni export** de suivi —
LOT 10, et la matrice marque « Exporter le suivi », l'export image 16:9 et le texte Teams `V1` ·
**aucune médiathèque avancée** (matrice §12.2, `V1`) · **aucun commentaire ni pièce jointe** sur une
tâche, **aucune validation par un tiers** (matrice §8.2, hors MVP explicitement).

**Les interdits absolus, qui ne dépendent d'aucun lot :** **aucun contournement de
l'authentification**, à aucun moment, même en développement · **aucun jeton ni mot de passe en clair**
en base, en journal, en audit ou dans un message d'erreur · **aucun jeton dans `localStorage`** ·
aucune donnée réelle de collaborateur · aucune modification d'une migration déjà appliquée ni des cinq
documents de cadrage · aucune exposition de PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur
`127.0.0.1` · aucune référence d'image par `latest` seul · ni Kubernetes, ni PWA, ni hors ligne, ni
Entra ID, Graph, Teams ou MFA · aucune ligne du prototype historique.

---

# 10. Cartographie du dépôt

```text
.
├── CLAUDE.md                    ← ce document. AGENTS.md est un lien symbolique, NON VERSIONNÉ
├── README.md · CONTRIBUTING.md
├── Makefile                     ← cibles parametrees par ENVIRONNEMENT (T8, DEC-485)
├── .env.example                 ← v1.6, 84 variables, aucun secret. DERIVE :
│                                 grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example
├── .dockerignore                ← DEC-473. node_modules, .venv, caches, .env
├── .gitleaks.toml               ← regles taillees sur les formats de CE projet (T6)
├── .node-version · .python-version
├── package.json · pnpm-workspace.yaml    ← pnpm épinglé, store hors iCloud
├── pyproject.toml               ← workspace uv, Ruff, mypy strict, pytest
├── tsconfig.base.json · eslint.config.js · .prettierrc.json · .prettierignore
├── apps/
│   ├── api/      app/{configuration,entities,health,shared}, alembic/, tests/, Dockerfile
│                 app/modeles.py         ← importe TOUS les modeles (LOT 2, T2)
│                 app/shared/modele.py   ← socle declaratif (LOT 2, T1, DEC-499)
│                 app/entities/routes.py  ← GET /api/v1/entities : la PREMIERE
│                                          route METIER du projet (LOT 4, T1)
│                 app/people/trombinoscope.py ← le trombinoscope EN LECTURE
│                                          (LOT 5, T2). DEUX filtres, et aucun
│                                          n'est redondant : le 22.5 etape 5
│                                          « masquage du profil » n'est
│                                          implemente NULLE PART, donc un
│                                          partant reste `published`
│                 app/people/modeles.py   ← les enumerations, ET les regles qui
                                          s'en DERIVENT : ETATS_OCCUPANTS, puis
                                          ETAT_LISTE et VISIBILITE_LISTEE depuis
                                          T5. Ces deux-la vivaient dans le
                                          trombinoscope ; un import CIRCULAIRE
                                          avec media/photo.py a dit qu'elles
                                          n'appartenaient a aucun des deux
                 app/shared/pagination.py ← les TROIS tailles du §18.2 (LOT 6, T3).
                                          Elles vivaient dans le trombinoscope ; un import
                                          CIRCULAIRE l'a refuse -- `people` importe DEJA
                                          `organization.modeles`. Un fait du CAHIER se
                                          declare dans `shared`, pas dans le premier module
                                          qui en a eu besoin
                 app/organization/cercles.py ← la page DETAILLEE d'un cercle (LOT 6, T3).
                                          Elle REUTILISE `ETAT_LISTE` et `VISIBILITE_LISTEE`
                                          de `people/modeles.py` -- une copie divergerait au
                                          premier ajout. La couleur n'est jamais seule, et
                                          c'est le §8.1 du MODELE qui l'exige : `code` et
                                          `nom` obligatoires, jeton NULLABLE
                 app/organization/bureaux.py ← la page DETAILLEE d'un bureau (LOT 6, T4).
                                          Elle NE PAGINE PAS, et c'est le raisonnement de
                                          `cercles.py` a l'envers : le §18.2 regit les
                                          POPULATIONS, et le §8.4 declare les responsables
                                          d'un bureau BORNES. Mais la borne N'EST PAS TENUE
                                          en base -- le declencheur est en T7, DEC-583 --
                                          donc la lecture ne la suppose pas : elle rend
                                          ZERO et rend QUATRE. `publie` vient de la PAGE de
                                          contenu, jamais de la table `office`, qui ne porte
                                          aucun etat de publication (DEC-576)
                 app/organization/framework.py ← la SYNTHESE Framework (LOT 6, T2). La
                                          matrice §5 l'accorde aux HUIT roles ; l'annexe A
                                          §10.1 n'a ni colonne `EMP` ni `NEW`
                 app/content/perimetre.py ← QUI peut ECRIRE quoi (LOT 6, T6). La
                                          grille du §13, et elle n'est PAS celle du
                                          LOT 5 : `DSM` y est a TIRET alors qu'il
                                          porte cinq champs au §6.1, et `OFFICE` y
                                          porte un droit REEL alors que sa colonne
                                          du §6.1 est entierement a tiret -- les deux
                                          grilles different dans les DEUX sens.
                                          `TYPES_SANS_PORTEE_LOCALE` est derive par
                                          SOUSTRACTION : un sixieme type de page
                                          tomberait dans le regime le plus
                                          RESTRICTIF sans que personne y pense
                 app/content/cycle_de_vie.py ← PUBLIER, ARCHIVER, RESTAURER (LOT 6,
                                          T7). La grille de la RESTAURATION est plus
                                          ETROITE que celle de l'archivage, et TROIS
                                          sources concordantes le disent : le Booster
                                          ARCHIVE la page de son cercle et ne la
                                          RESTAURE pas. La restauration rend un
                                          BROUILLON, jamais un publie -- restaurer
                                          n'est pas publier, et le §13 en fait deux
                                          lignes a deux grilles. Il n'existe AUCUNE
                                          depublication : le §13 n'en porte pas de
                                          ligne, et retirer une page du public se fait
                                          en l'ARCHIVANT. `state` et `archived_at` sont
                                          ecrits dans le MEME `UPDATE`, si bien qu'ils
                                          ne peuvent pas diverger par cette API -- mais
                                          AUCUNE contrainte ne les couple, le decor de
                                          `T4` produisant les deux divergences EXPRES
                 app/content/liens.py    ← LES LIENS INTERNES (LOT 6, T8), et le
                                          module qui clot `QO-120`. `PROTOCOLES_AUTORISES`
                                          = {`https`}, `DEC-587` -- et **une liste de
                                          protocoles NE SUFFIT PAS** : `https:alert(1)` a
                                          pour protocole `https` et n'adresse RIEN, d'ou
                                          `url_sans_hote`. `url_ambigue` n'enumere AUCUN
                                          caractere interdit -- recopier la liste interne
                                          de CPython vieillirait -- mais exige que le
                                          protocole TAPE soit celui qui a ete LU.
                                          Le RANG n'est jamais recu : la creation ajoute EN
                                          QUEUE, et la reecriture d'ordre vaut l'index de
                                          la liste. Un echange en un seul `UPDATE` est
                                          REFUSE par l'index unique partiel de `T1`, mesure
                                          -- d'ou deux temps, et un decalage `max + 1`
                                          DERIVE EN SQL, jamais le NOMBRE de liens
                                          (defaut `T8-1`, NON DETERMINISTE).
                                          AUCUNE route n'ARCHIVE un lien : ni le §13 ni le
                                          §19 n'en portent la ligne. On DESACTIVE
                 app/content/ecriture.py  ← le verbe « ACCEPTE » (LOT 6, T6), tenu
                                          par la STRUCTURE : la demande n'offre
                                          AUCUN champ par lequel declarer qu'une
                                          chaine est du balisage. Un filtre textuel
                                          serait une heuristique (§7.25).
                                          `display_order` vaut l'INDEX du tableau,
                                          donc deux blocs de meme rang sont
                                          INEXPRIMABLES. Les blocs retires sont
                                          ARCHIVES (modele §2.4), et cela n'exige
                                          AUCUN motif -- le §18.1 en enumere cinq,
                                          et retirer un bloc n'y est pas. `state` et
                                          `published_at` ne sont JAMAIS touches
                 app/content/modeles.py  ← les TROIS tables du §15 (LOT 6, T1).
                                          `content_block` porte un `entity_id`
                                          que le §15.2 n'ecrit PAS : le §25.3 est
                                          AUSSI le modele, et sans lui la cle vers
                                          `content_page` serait SIMPLE. Le §15.1
                                          ne recoit que son IMPLICATION -- il dit
                                          « requis pour », jamais « interdit
                                          ailleurs », au contraire du §8.4
                 app/media/photo.py      ← la MINIATURE (LOT 5, T5). Elle ne
                                          SELECTIONNE PAS `media_asset.object_key`,
                                          et `MiniatureServie` n'a AUCUN champ qui
                                          puisse le porter : l'original ne peut pas
                                          fuir par cette structure (§7.35). Ses
                                          CONDITIONS sont une source UNIQUE,
                                          partagee avec le trombinoscope -- en
                                          EXISTS la-bas, en SELECT ici
                 app/media/objets.py     ← lire un objet MinIO. L'API sert les
                                          OCTETS et non une URL signee : le corpus
                                          ne dit RIEN de la facon dont un media
                                          parvient au navigateur, et une URL vers
                                          MinIO exposerait le port 9000 (DEC-460,
                                          DEC-470). Reversible : seul le corps de
                                          la route changerait
                 app/people/profil.py    ← la FICHE (LOT 5, T4). Quatre
│                                          contraintes d'EXCLUSION rendent les
│                                          LEFT JOIN surs, et un test exige
│                                          qu'elles existent toujours. AUCUN
│                                          champ n'est masque : ECART-051.
│                                          Depuis T5 elle porte `photo`, et le
│                                          test de T4 qui EXIGEAIT son absence
│                                          est RETOURNE -- c'etait son role
│                 app/people/routes.py    ← GET .../people. `taille` est un
│                                          IntEnum et NON un Literal : un
│                                          parametre d'URL arrive en CHAINE,
│                                          et Literal la REFUSE. Defaut T2-3
│                 app/entities/services.py ← le filtre `= active`, DERIVE de
│                                          l'enumeration (DEC-544), et la
│                                          resolution par code (T2, DEC-545)
│                 app/auth/dependances.py ← exiger_une_session ET exiger_un_scope :
│                                          DEUX natures d'appelant (DEC-543)
│                 app/{entities,people,clients,organization}/
│                                        ← 18 tables METIER (LOT 2, T2 a T8)
│                                          19 avec alembic_version : DIS LAQUELLE
│                 alembic/versions/      ← 0019 : la CONTRAINTE de protocole du §15.3,
                                          `ck_internal_link_url_https` (LOT 6, T8,
                                          DEC-587). AUCUNE colonne, AUCUNE table. `T1`
                                          l'avait REFUSEE, et il avait raison a sa date --
                                          « inventer la liste ici la figerait dans le
                                          schema ». Ce qui a change n'est pas l'argument,
                                          c'est que la liste n'est plus une invention.
                                          Elle est le PLANCHER : trois ecrivains futurs
                                          sont deja nommes au corpus et n'appellent pas
                                          `app.content.liens` -- la reprise du prototype
                                          (T11), les modeles generiques du §19, les imports
                                          du LOT 9. Elle ne sait PAS exiger un hote, et
                                          c'est pourquoi le service valide AUSSI
                                          0018 : le DECLENCHEUR de la borne du §8.4,
│                                          « un a trois responsables actifs lorsqu'il
│                                          est publie » (LOT 6, T7, DEC-583). Il garde
│                                          la TRANSITION -- `BEFORE UPDATE OF state` --
│                                          exactement comme le declencheur du §23.2 de
│                                          la migration 0008. Il ne garantit donc PAS
│                                          qu'un bureau publie RESTE conforme, et un
│                                          test le mesure : c'est ce qui rend la lecture
│                                          tolerante de `T4` NECESSAIRE
│                                          0001 vide, 0002 ext., 0003 entites,
│                                          0004 person, 0005 appartenance,
│                                          0006 metiers, 0007 clients,
│                                          0008 cercles et bureaux,
│                                          0009 responsabilites et DSM,
│                                          0010 exclusions autoportantes,
│                                          0011 roles et perimetres (T10)
│                                          0012 tables d'authentification (L3 T2)
│                                          T11 n'en ecrit AUCUNE : rien a changer
│                 app/shared/depot.py    ← DepotLocal / DepotGlobal (T11, DEC-515)
│                 app/shared/database.py ← moteur() ET moteur_migrations() :
│                                          DEUX ROLES depuis LOT 3, T1 (DEC-520)
│                 app/organization/services.py ← l'ACTION du 8.4 (T11)
│                 app/shared/fabriques.py ← jeu fictif DETERMINISTE (T12)
│                 app/auth/modeles.py    ← les 7 tables du 10 (L3 T2, DEC-521)
│   ├── worker/   worker/{main,journal}.py, tests/, Dockerfile
│   └── web/      index.html, vite.config.ts
│                 Dockerfile              ← 2 CIBLES depuis T7 (DEC-479)
│                 Caddyfile.execution     ← sert l'artefact statique, port 5173
│       └── src/  main.tsx · App.tsx · FrontiereErreur.tsx · styles.css
│                 api/sante.ts          ← client des 2 endpoints, 200 ET 503
│                 pages/PageStatut.tsx  ← les 5 états
├── packages/
│   ├── observabilite/    journal JSON, masquage, corrélation (DEC-466)
│   ├── ui/               design system (T10) — jetons RELEVES du prototype et
│   │                     RECALCULES contre WCAG 2.2 AA (DEC-491)
│   │                     contraste.ts · jetons.ts · jetons.css · composants.css
│   │                     Bouton · Badge · Carte, 90 tests
│   └── contracts/        contrat API partagé (T10, DEC-492)
│                         contrat-api.json  ← SOURCE UNIQUE, lue par TS ET Python
│                         portail.ts        ← la PREMIERE forme METIER : les
│                                             entites du portail (LOT 4, T1)
│                         formes.ts         ← estObjet / exigerChaine, EXTRAITES
│                                             de sante.ts, un seul exemplaire
│                         liens.ts          ← LA LECTURE des liens internes (LOT 6, T8).
                                             LE PARTAGE DU LOT : une sous-etape qui sert une
                                             LECTURE pose son module de contrat, celles qui
                                             servent une ECRITURE ne le font pas -- T6 et T7
                                             n'ont rien ajoute ici. `urlEstServable` est la
                                             TROISIEME barriere, pas la premiere, et elle
                                             minuscule le protocole : sans cela elle
                                             refuserait « HTTPS:// » que l'API ACCEPTE, donc
                                             un faux positif (§7.25)
                         portail.ts porte aussi `cheminEntite`, qui ENCODE le
│                         code et LEVE sur une chaine vide -- sinon le chemin
│                         obtenu serait celui de la LISTE (T2)

├── infra/
│   ├── compose/  base + surcouches dev ET recette (T8)
│   │             la surcouche NOMME sa cible de construction (DEC-479)
│   │             differences-recette.env  ← calque VERSIONNÉ, aucun secret
│   ├── caddy/    Caddyfile — monté PAR SON RÉPERTOIRE (DEC-472), tls internal
│   └── scripts/  exclure-icloud · verifier-{ports,persistance,sante,page-statut}
│                  verifier-documentation.py  ← empreintes, sequences, ET
│                                                totaux DÉRIVÉS (T8, DEC-488)
│                  verifier-images.py         ← 6 sous-commandes, controles de T7
│                  provisionner-roles.py       ← les 2 roles, idempotent (T1 L3)
                  verifier-secrets-en-clair.py ← 2 familles d'empreintes (L3 T2)
                  verifier-privileges.py      ← le DDL doit ECHOUER, et le DML
                                                REUSSIR — le temoin est la
                  verifier-migrations.py      ← base VIDE, chaine rejouee, et
                                                le schema COMPARE (T12)
                  verifier-recette-modele.py  ← les 25 controles du 30, CLASSES
                  engendrer-jeu-de-donnees.py ← make jeu-de-donnees (T12)
                  verifier-isolation.py       ← 2.5 et 25.3 : COLONNES, pas
                                                contraintes ; MATCH SIMPLE ; --temoin
                  verifier-separations.py    ← les 7 separations du cahier 22.2,
│                                                l'artefact en marche, l'archi,
│                                                Mailpit, QO-085          (T8)
│                  composer-env.py            ← modele + calque + secrets (T8)
│                  epingler-images.py         ← make images-pin           (T8)
│                  verifier-sources-suivies.py ← AUCUN fichier source du disque ne
│                                                doit etre ignore par git. Existe parce
│                                                que `media/` attrapait le module
│                                                `apps/api/app/media/` : make check a
│                                                0, et `git add -A` n'ajoutait rien.
│                                                ECART-048, §7.36
│                  verifier-reversion-icloud.py ← un contenu de travail EGAL a une
│                                                version anterieure = reecriture
│                                                iCloud. Remplace un controle a FAUX
│                                                POSITIFS. DEC-542, §7.34
│                  verifier-trombinoscope.py  ← 23 controles a travers Caddy. Son
                                                controle le plus utile est un TEMOIN,
                                                pas un refus : avec le defaut T2-3, les
                                                HUIT refus restaient verts (LOT 5, T2)
                  verifier-entites.py        ← les 4 etats du modele, une entite
│                                                par etat, a travers Caddy. Le
│                                                critere n'en nommait que 2 :
│                                                ECART-039        (LOT 4, T1)
│                  Tous en Python : le motif est en §7.2
└── docs/
    ├── product/ · architecture/     ← IMMUABLES
    ├── decisions/                   ← registre des decisions et registre des ecarts
    │                                 (comptes au §1, DERIVES -- pas recopies ici)
    └── operations/                  ← fiche-lot-1, comptes rendus T0 à T11, registres
                                        checklist-validation-G1.md  ← T11, la porte
                                        exploitation-locale.md  ← T9, toutes commandes exécutées
```

`.github/` porte les gabarits d'issue et de pull request, et **deux workflows** :

| Workflow | Déclencheurs | Contenu |
|---|---|---|
| **`ci.yml`** (`T6`) | pull request **et** poussée sur `develop`/`main` | 3 tâches, les 11 contrôles du cahier §23.1, et **la porte que la protection de branche exige** |
| **`images.yml`** (`T7`) | poussée sur `develop`, tags `v*`, **et `workflow_dispatch`** | 4 tâches : publier, lancer sur 2 architectures, Trivy, porte. **Jamais sur une pull request** — cahier §23.1. Sa porte n'est **pas** et ne doit **pas** devenir un contrôle requis : voir §9.4 |

---

# 11. Démarrage type d'une session

```bash
export PATH="$HOME/.local/bin:$PATH"        # gh et uv n'y sont PAS par defaut
git switch develop && git pull && git log --oneline -3 && git status -sb

make icloud-verify        # PAS une formalite : il a manque une reversion silencieuse de
                          # 4 fichiers (§7.31), PUIS 115 copies de conflit de FICHIERS que
                          # son motif ne couvrait pas (§7.34). Il porte desormais les 4
                          # motifs, cherche a toutes les profondeurs, EXIGE que
                          # `git check-ignore` les honore, et detecte une reversion en
                          # comparant le contenu de travail aux versions de l'historique.
make env-check            # .env contre .env.example — une variable a manque a CHAQUE lot
                          # `sources-check` et `docs-check` sont dans `make check` : le moment
                          # ou il faut savoir qu'un motif de .gitignore attrape du source est
                          # la PULL REQUEST, pas le debut de session. §7.36
make check                # qualite complete, tests compris
make audit                # zero avis, zero tolerance depuis DEC-493

# ETAT DE CETTE MACHINE AU 18/09/2026 : LA BASE DE DEV PORTE UN JEU DE DEMO.
#
#   Mesure du 22/09/2026 : 26 entites, 5 155 personnes, 100 cercles.
#   Consequence : `make residu-check` rend 84 ECHECS, et AUCUN ne vient du
#   code -- le nombre disait 74 au 18/09, et il DERIVE avec le jeu de demo,
#   donc ne le recopie pas : mesure-le. Ce
#   sont des tests des LOTS 2 et 3 qui comptent des lignes en ABSOLU --
#   « assert 5157 == 2 » -- exactement le piege que le §5.3 decrit pour
#   `make jeu-de-donnees`.
#
#   **NE REINITIALISE PAS LA BASE SANS L'ACCORD DE JONATHAN.** Ces donnees
#   servent une DEMO CLIENT preparee sur la branche `demo`. Le remede du §5.3
#   les detruirait.
#
#   Ce qui PROUVE quand meme ton travail, et c'est suffisant :
#     - les tests de TA sous-etape, lances seuls, passent sur cette base ;
#     - la PORTE de la pull request tourne sur une base NEUVE, et c'est elle
#       qui fait foi (§7.28 : lis ce que la cible fait, pas son nom) ;
#     - et le GESTE qui tranche, pose par `T8` : compare la LISTE des tests
#       en echec a celle d'`origin/develop`, dans un `git worktree`, SUR LA
#       MEME BASE. Avant d'attribuer une regression a ton travail, mesure
#       l'etat d'avant (§7.22). `T8` a mesure 84 des deux cotes, dont une
#       SEULE difference -- un test que `T8` CORRIGE. Attention : le
#       worktree partage la base, donc il subit DEJA tes migrations.
#   Verifie donc `gh pr checks <n>` plutot que de conclure sur le `make check`
#   local -- et DIS dans ton rapport que les 74 echecs sont environnementaux.

make up                   # les 8 services, le bucket MinIO, les DEUX roles, Caddy recharge
make stack-check          # sante + ports
make migrate              # rafraichit le code embarque EN DEV, applique, pose le domaine
make api-check && make web-check

# Les ONZE controles d'authentification du LOT 3, tous dans la CI
make magic-link-check     # 15 — la reponse est IDENTIQUE, connue ou non
make admin-check          # 10 — le verrou se declenche, `admin-local` le leve
make sessions-check       # 13 — les trois attributs du cookie, le jeton hors navigateur
make sessions-temoin      #      le temoin, SANS stack — il est dans `make check`
make csrf-check           # 10 — 5 ecritures refusees, une cle rejouee sans effet
make debit-check          # 12 — les seuils du 20.2, les DEUX refus compares
make revocation-check     #  6 — le depart revoque, et l'API rend 401, MESURE
make service-check        # 11 — un jeton hors scope refuse, l'expiration effective
make ecrans-check         #  8 — les 8 chemins servis, aucune couleur hors jetons dans
                          #      les QUATRE feuilles (une seule etait lue avant T11), et
                          #      les 30 MODULES d'ecran servis en JAVASCRIPT. Ce dernier
                          #      est le seul qui distingue un conteneur `web` a jour d'un
                          #      conteneur perime : le repli SPA rend `text/html` avec le
                          #      point de montage pour N'IMPORTE QUEL chemin, si bien que
                          #      les trois autres controles d'ecran passent sur le code
                          #      d'un autre lot. §7.0, quatrieme proposition. Lance
                          #      `make code-refresh` AVANT, jamais apres
make evenements-check     #  6 — les 7 evenements du 10.6, sans rien de sensible
make residu-check         #      la suite d'integration, ET la preuve qu'elle ne laisse rien
                          #      Il REMPLACE `make test-integration`, il ne s'y ajoute pas.

# Le controle du LOT 4, dans la CI comme les onze precedents. Il EXIGE que le
# conteneur porte le code du depot : lance `make code-refresh && make code-check`
# d'abord, sinon il eprouve un autre artefact en paraissant sain. §7.28
make permissions-check    # 15 — l'union du 23.1 dans l'entite principale, `EMP` SEULEMENT
                          #      ailleurs ALORS QUE LE DROIT LOCAL EXISTE, un role clos et
                          #      une affectation FUTURE qui n'accordent rien, le
                          #      super-administrateur partout, et les QUATRE tables de
                          #      rattachement INCHANGEES avant/apres — regles 1 et 2 du 23.3
make profil-check         # 45 — il RELIE la fiche a la liste : l'identifiant vient du
                          #      trombinoscope, et un profil EXCLU rend le MEME 404. Les six
                          #      champs sensibles sont TOUS renseignes (ECART-051).
                          #      DEPUIS T5 il deverse DEUX objets de contenus distincts
                          #      dans MinIO et exige que les octets servis soient
                          #      EXACTEMENT ceux de la MINIATURE : un controle
                          #      « 200 et des octets » passerait si la route servait
                          #      l'original. C'est le PREMIER consommateur du bucket.
                          #      DEPUIS T7 un DSM ecrit dans SON perimetre et est REFUSE
                          #      ailleurs ; DEPUIS T8 le MEME DSM est REFUSE a
                          #      l'archivage, que seul l'ESM mene -- le §6.1 porte DEUX
                          #      grilles de roles. Les NEUF controles de T8 viennent en
                          #      DERNIER, parce qu'ils archivent le profil complet : plus
                          #      haut, ils casseraient le « exactement deux profils » du
                          #      controle 2 et l'historique intact du temoin 26.
                          #      DEPUIS T9 il lit l'HISTORIQUE : cinq axes pour l'ESM,
                          #      QUATRE pour le DSM -- l'axe des responsabilites vaut
                          #      `null`, §20 et §23.2 -- et AUCUNE des sept colonnes
                          #      techniques ne parait dans les OCTETS servis. Ses
                          #      controles viennent AVANT ceux de T8 : apres
                          #      l'archivage, le DSM n'est plus le DSM de personne,
                          #      et il rendait 404 a juste titre (defaut T9-3).
                          #      DEPUIS T10 il exige que les QUATRE champs du VERSO
                          #      soient RENSEIGNES : « douze champs ni plus ni
                          #      moins » passerait avec les quatre a `null`, ce
                          #      que rendrait une jointure qui ne joint rien.
                          #      ET le JETON de couleur y est un COUPLE : « bleu »
                          #      sur le cercle principal, `null` sur un second
                          #      cercle qui n'en porte aucun -- `color_token` est
                          #      NULLABLE, et `str(None)` servait la chaine
                          #      « None » sur 100 % des cercles (defaut T10-8).
                          #      La chaine est cherchee dans les OCTETS servis
make trombinoscope-check  # 38 — les TROIS tailles SERVIES (le temoin qui a trouve T2-3),
                          #      huit refus au format du 18.3, la recomposition des pages
                          #      qui exige un ordre TOTAL, et les quatre etats exclus
make entites-check        # 13 — une entite par etat, les TROIS non actifs exclus, les
                          #      deux refus compares corps ET en-tetes, la resolution
                          #      par code, et `/entites/<code>` servi : le choix
                          #      SURVIT a un rechargement

# Le controle du LOT 6, et il N'ETAIT DANS AUCUNE ROUTINE DE CE §11 jusqu'au
# 19/09/2026 -- cinq sous-etapes l'ont etendu sans que personne l'y inscrive.
# C'est la classe §7.40 appliquee a cette page : une liste qui enumere les
# controles et en oublie un. Il EXIGE que le conteneur porte le code du depot :
# lance `make code-refresh` d'abord, sinon il eprouve un autre artefact en
# paraissant sain (§7.28).
make framework-check      # 77 — la page Framework, les pages de cercle et de bureau, le
                          #      RENDU des blocs, l'ECRITURE d'un contenu, et depuis
                          #      `T7` le CYCLE DE VIE. Son controle le plus utile est un
                          #      COUPLE D'ADRESSES IDENTIQUES : la meme URL rend 404 en
                          #      brouillon, 200 publiee, 404 archivee, **404 RESTAUREE**
                          #      -- restaurer n'est pas publier -- puis 200 republiee.
                          #      Sans la derniere ligne, la quatrieme serait satisfaite
                          #      par une restauration cassee (§7.39).
                          #      Il porte aussi le SEUL geste du projet qui fasse mordre
                          #      la borne du §8.4 : publier la page d'un bureau a zero
                          #      responsable rend 409, et un responsable ACTIF ajoute
                          #      fait passer LA MEME publication.
                          #      DEPUIS `T8` il eprouve les LIENS INTERNES : les trois
                          #      destinations que le critere NOMME -- Hub, eXalt Academy,
                          #      SharePoint -- creees par l'API puis SERVIES par l'accueil ;
                          #      les CINQ refus d'URL sous CINQ codes distincts, dont
                          #      `url_sans_hote`, le seul qu'une lecture litterale de
                          #      « liste de protocoles autorises » aurait omis ; et un
                          #      `javascript:` insere EN SQL, refuse par la contrainte de
                          #      la migration `0019` -- le PLANCHER, que le service ne peut
                          #      pas apporter. Son controle le plus utile apres le temoin
                          #      est la PERMUTATION : les liens sont inverses en un geste,
                          #      ce qu'un seul `UPDATE` ne peut pas faire.
                          #      DEPUIS `T10` il eprouve les DEUX routes de gestion posees
                          #      pour l'editeur -- `/pages/gestion` et `/pages/{page}/
                          #      gestion` -- et son controle le plus utile est le COUPLE
                          #      CENTRAL : la MEME page rend 404 en lecture PUBLIQUE une
                          #      fois archivee, et 200 `archived` en GESTION -- c'est ce
                          #      couple qui a fait tomber le defaut `T10-1` avant la
                          #      fusion (garde qui exigeait `MODIFIER`, jamais rendu sur
                          #      une page archivee -- seul `RESTAURER` l'est).
                          #      DEPUIS `T11` il porte le TEMOIN du critere de sortie 2 du
                          #      lot : une entite GENERIQUE (ville Nantes, aucun cercle, aucun
                          #      bureau) ne sert AUCUN octet « bordeaux » sur Framework ni sur
                          #      sa fiche d'entite -- et un second controle, TEMOIN POSITIF,
                          #      prouve que la recherche discrimine reellement en la relancant
                          #      sur l'entite du decor dont `city = 'Bordeaux'` (§7.39). Sans
                          #      ce second controle, une recherche cassee et une recherche
                          #      juste rendraient la MEME observation.

# Le controle du LOT 7, differe par T13, construit et combine ici par T14 --
# 14 controles sur la pile REELLE, Caddy en HTTPS, conteneurs en marche.
make onboarding-check     # 14 — le TEMOIN D'ASYMETRIE DSM/ESM : les deux roles poses dans
                          #      la MEME entite, chacun voit un ensemble de modeles
                          #      DIFFERENT -- un controle a un seul role rendrait la meme
                          #      observation quel que soit le defaut (§7.0, quatrieme
                          #      proposition). Le CYCLE DE VIE COMPLET exerce une fois en
                          #      vrai : creer, composer les taches, publier, archiver,
                          #      restaurer -- chaque transition change le code HTTP attendu
                          #      de la suivante. OFFICE refuse (403) sur les modeles MAIS
                          #      recu (200) sur le suivi, les deux extremes de la meme
                          #      matrice dans le meme script. `ECART-066` eprouve DANS LE
                          #      SENS DU REFUS : un DSM proprietaire de sa propre version
                          #      archivee est refuse (403) en la restaurant.

# Les controles de schema
make privileges-check && make secrets-check && make isolation-check && make isolation-temoin
make historisation-check && make migrations-check && make recette-modele-check
make alembic-check && make code-check

# Si tu touches aux images : `images-check` est STATIQUE, elle ne lance RIEN. §7.28
make images-build && make images-verify

# Recette, sur les images PUBLIEES et epinglees (DEC-539, revision 3bc68b9).
# `make migrate ENVIRONNEMENT=recette` NE reconstruit rien : l'image est publiee. §7.21
make up-recette && make recette-check && make separations-check && make down-recette
```

**Et regarde l'intégration continue, qui bloque :**

```bash
gh run list --limit 5 && gh pr checks <numero>
gh run list --workflow=images.yml --limit 3
```

Si Docker ne répond pas : `open -a Docker`, puis attendre.

**Dans quel ordre lire :**

1. **ce document**, en entier — son §7 porte **48 leçons** payées par **279 défauts nommés** — 71 + 44 + 57 + 19 + 62 + 26, dérivés par la commande du §7 ;
2. [`docs/README.md`](docs/README.md) : quelle porte, quel prochain identifiant ;
3. [`checklist-validation-G3.md`](docs/operations/checklist-validation-G3.md) : ce que le LOT 3 a
   prouvé, et surtout **ce qu'il n'a pas fait** ;
4. le **compte rendu de la dernière sous-étape** — `compte-rendu-t12-lot-3.md` — dont le §7 dit ce
   qu'il laisse à la suite ;
5. [`exploitation-locale.md`](docs/operations/exploitation-locale.md) : lancement, arrêt, et **quinze
   symptômes de diagnostic réellement rencontrés** ;
6. **vérifier l'état réel** par `git`, `gh` et les mesures — **pas** par ce que la doc affirme (§9.0).

**Contrôle d'hygiène, à tout moment :**

```bash
git ls-files | grep -Ei '\.(csv|env|pem|key|mp4|html)$'   # 3 attendus, nommes ci-dessous
git ls-files | grep -c 'V1.html'                          # doit valoir 0
git status --short                                        # doit etre vide
```

Le premier montre **trois** fichiers, et les trois sont légitimes :

| Fichier | Pourquoi il est là |
|---|---|
| `docs/architecture/donnees/exemples/collaborateurs-exemple-fictif.csv` | explicitement **fictif**, LOT 0 |
| `apps/web/index.html` | point d'entrée **imposé par Vite** depuis `T5` du LOT 1 |
| `infra/compose/differences-recette.env` | **calque de différences versionné**, `T8` du LOT 1. **Aucune valeur sensible** |

> **Toute entrée que ce tableau ne nomme pas est une anomalie** — c'est la formulation qui ne
> vieillit pas, là où un nombre vieillit à la première addition.

# 12. Une dernière chose

Jonathan valide vite et lit sérieusement. Ce qui fonctionne avec lui :

- des rapports **denses mais courts**, avec les chiffres réels et non des approximations ;
- **signaler ses propres erreurs** dès que les contrôles les révèlent, sans les enjoliver. Les
  279 défauts sont documentés, y compris le trou de sécurité que j'avais laissé dans mon propre
  filtre de masquage, les **six** fois où j'ai conclu sur un code de sortie qui n'était pas celui
  que je croyais lire, et l'**empreinte SHA-256 inventée** que `T7` a écrite dans un workflow avant
  de la remplacer par la valeur mesurée. En `T5`, **cinq défauts sur huit étaient dans mes
  contrôles** ; en `T7`, **dix sur treize** — c'est la forme la plus insidieuse : on croit avoir
  prouvé. En `T6` **et** en `T7`, j'ai rejoué une leçon **écrite dans ce document** : un piège
  documenté n'est pas un piège désarmé. La parade de `T7` a été de **changer d'outil** plutôt que de
  promettre plus de vigilance ;
- distinguer nettement **ce qui est prouvé** de **ce qui est recommandé** ;
- dire ce qui **n'est pas** couvert, plutôt que de le laisser croire. La conservation de 30 jours
  des journaux n'est pas faite, et `QO-113` le dit ;
- lui donner à chaque fois la commande de fusion **et** celle de retour arrière ;
- ne rien pousser vers l'extérieur sans son accord ;
- **reformuler sans jargon** quand il dit ne pas comprendre une question. C'est arrivé deux fois,
  et les deux fois c'était ma question qui était mauvaise, pas sa lecture.

Le projet a une exigence de traçabilité inhabituellement élevée — le compte des décisions est au §1, dérivé — et un compte
rendu par sous-étape qui consigne jusqu'aux défauts de mes propres contrôles. Ce n'est pas de la
bureaucratie. C'est ce qui permettra, au LOT 9, de justifier chaque ligne rejetée d'un import de
données personnelles réelles — et, plus tôt, de ne pas refaire quatre fois la même erreur de
tuyau. **Tiens les registres à jour dans la même pull request que le travail — jamais après.**

**Et une chose qui a marché à chaque fois, sur les cinq lots :** quand un contrôle échoue et que tu
ne sais pas pourquoi, **la première correction à écrire est celle qui te le dira**. Trois cycles
d'intégration continue perdus en `T7` du LOT 1, un `REASSIGN OWNED` diagnostiqué en deux nombres en
`T1` du LOT 3 : la différence est là. Un contrôle qui masque la cause de son échec ne coûte pas un
message, il coûte des heures.
