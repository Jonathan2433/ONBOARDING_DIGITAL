# Checklist de validation — porte `G5`

**Lot :** LOT 5 — collaborateurs, profils et organisation
**Préparée le :** 12 septembre 2026, à la sortie de `T12`
**Destinataire :** Jonathan — c'est lui qui franchit la porte
**Décision attendue :** `DEC-574`

---

**Comment lire ce document.** Chaque affirmation est suivie de **la commande qui la produit**. Rien
n'est recopié : tous les nombres ci-dessous ont été **dérivés le 12/09/2026**, et c'est la classe
d'erreur la plus fréquente du projet — `ECART-021`, §7.27. **Recompte avant de réutiliser.**

**Un seul des sept critères demande ton avis** — le septième. Les six autres sont **mécaniquement
prouvés**, ce qui veut dire qu'ils font échouer l'intégration continue si quelqu'un les casse.

---

## 1. Les sept critères de sortie de la roadmap

> **Le compte est dérivé, non supposé.** La fiche du lot raconte qu'il a d'abord été écrit « huit »,
> par symétrie avec les huit stories, et que la commande a dit **sept** :
>
> ```bash
> awk '/^# LOT 5/,/^# LOT 6/' docs/product/ROADMAP_MVP_V1_V2_EXALT.md \
>   | awk '/Critères de sortie/,/^## Dépendances/' | grep -c '^- '
> ```

| # | Critère | Comment il est tenu | Ce qui le prouve |
|---|---|---|---|
| 1 | « les miniatures sont **inférieures à la cible de 100 Ko** » | la borne est **en base**, migration `0016`, et portée au **seul** type `thumbnail` — la poser sur les cinq casserait le LOT 11 | un test la franchit **à l'octet** : 99 999 passe, 100 000 est refusé · `BORNE_MINIATURE_OCTETS == 100_000` est confronté à la migration |
| 2 | « **aucune photo non autorisée** n'est publiée » | **structurel** : la requête ne sélectionne pas `media_asset.object_key`, et la structure rendue n'a **aucun champ** qui puisse le porter | `make profil-check` compare les **OCTETS** servis à ceux de la miniature — deux contenus distincts déversés dans MinIO. Un contrôle « 200 et des octets » passerait si la route servait l'originale |
| 3 | « les permissions suivent **intégralement** la matrice » | **deux grilles de rôles**, pas une : `ROLES_D_ECRITURE` (cinq) et `ROLES_DU_CYCLE_DE_VIE` (trois). Le §6.1 met `DSM` et `BOOST` à **tiret** sur l'archivage alors que les deux **modifient** | `make permissions-check` · `make profil-check` — un DSM écrit dans son périmètre, est **refusé ailleurs**, et **refusé à l'archivage** |
| 4 | « les recherches respectent l'objectif de performance **avec 5 000 profils** » | le test **rapporte** le P95 et **exige** la justesse au volume — voir la réserve ci-dessous | mesure du 12/09/2026, ci-dessous |
| 5 | « **aucune requête N+1 critique** n'est détectée » | les comptes de requêtes sont **bornés et mesurés**, indépendants du nombre de lignes **et** du nombre de filtres | 3 par page de trombinoscope · 3 par fiche · 6 pour cinq axes d'historique, **4 pour trois** |
| 6 | « les **affectations structurantes** ne sont jamais écrasées » | **propriété du schéma, pas promesse** : `period` en bornes `[)` et une contrainte d'**exclusion** par table, si bien qu'une période **future** fait refuser l'écriture | traduit en `409` · concurrence optimiste du §18.4 ancrée sur la **racine** de l'agrégat |
| 7 | « **Jonathan valide le trombinoscope et les profils** » | **ta décision.** La démonstration du §3 est là pour cela | — |

### La mesure du quatrième critère, et sa réserve

```text
jeu engendre : 28 011 lignes en 23,6 s · entite la plus peuplee : 210 appartenances
40 mesures par cas, plus un premier appel rapporte a part

  sans filtre               P95  168,1 ms   max 169,1   a froid 165,8    76 resultat(s)
  recherche « ont »         P95   24,4 ms   max  24,8   a froid  24,3     9 resultat(s)
  recherche sans resultat   P95    3,6 ms   max   4,0   a froid   3,3     0 resultat(s)
  statut seul               P95  167,4 ms   max 167,7   a froid 159,0    35 resultat(s)
  recherche + deux filtres  P95   23,1 ms   max  23,9   a froid  23,3     4 resultat(s)

  jointure : 0 ligne(s) rejetee(s) pour 210 appartenances — le cout suit l'entite
  justesse au volume : 2 cas confrontes a une requete directe
```

> **CE TEST N'EXIGE AUCUNE DURÉE, ET C'EST UNE DÉCISION MESURÉE.** Le §25.2 vise « moins de 800 ms au
> P95 » : c'est un objectif de **production**, sous charge réelle. Un poste de développement ne
> mesure pas cela — `ECART-055`, `DEC-567`, et la démonstration tient en deux lignes :
>
> - le banc engendre son volume dans une transaction **annulée**, et `ANALYZE` ne publie **rien
>   d'exploitable** sur des lignes non validées : le planificateur croit les tables **vides** et
>   choisit des plans qu'il ne choisirait pas en service ;
> - un plafond « prudent » calibré ici a rendu **3 663 ms** sur l'exécuteur de la CI. Un seuil sur une
>   grandeur non mesurable ne mesure que la machine.
>
> Le test **exige** donc la **justesse au volume** — la requête rend exactement ce qu'une requête SQL
> directe rend — et il **rapporte** le reste. **Le chiffre qui compte ici n'est pas le P95 : c'est
> `0 ligne(s) rejetée(s)`**, la propriété structurelle qui distingue un plan dont le coût suit
> l'**entité** d'un plan qui parcourt la **table**. C'est elle qui répond au cinquième critère.

```bash
uv run pytest apps/api/tests/test_recherche_et_filtres.py -q -k "effondre" -s
```

---

## 2. Les contrôles de stack, et ce que chacun refuse

| Contrôle | Contrôles internes | Ce qu'il refuse |
|---|---:|---|
| `make profil-check` | **45** | une fiche qui masquerait un champ ; l'**originale** servie à la place de la miniature ; un DSM qui archiverait ; un historique portant une colonne technique ; un jeton de couleur servi en chaîne `"None"` |
| `make trombinoscope-check` | **38** | une taille de page hors des trois du §18.2 ; une page qui répéterait ou sauterait une ligne ; un profil non publié ou non actif ; un verso dont les quatre champs seraient nuls |
| `make entites-check` | **13** | une entité `draft`, `suspended` ou `archived` proposée par le portail |
| `make cadre-check` | **25** | une couleur hors jetons ; une propriété personnalisée **non définie** ; un composant exporté **sans consommateur** ; un état de succès atteignable depuis un `catch` |
| `make ecrans-check` | **8** | une couleur littérale dans l'une des **quatre** feuilles ; un jeton dans `localStorage` ; **un conteneur `web` qui porterait un code plus ancien que le dépôt** |
| `make permissions-check` | 15 | une permission locale **transférée** hors de l'entité principale |
| `make residu-check` | — | qu'un test laisse une ligne derrière lui |

```bash
make profil-check && make trombinoscope-check && make entites-check
make cadre-check && make cadre-temoin && make ecrans-check && make residu-check
```

**Tous sont dans l'intégration continue** — `ci.yml` appelle **46** cibles une par une, dérivé — donc
bloquants sur chaque pull request.

> **`make check` N'EST PAS APPELÉ PAR LA CI**, et c'est un piège de ce dépôt : une cible ajoutée à
> `make check` n'entre **pas** dans la porte. Il faut l'ajouter à `ci.yml`. §7.36.

---

## 3. La démonstration guidée — huit gestes, dans cet ordre

**Ouvre Safari, Chrome ou Edge.** Pas Firefox, qui gère son propre magasin de certificats.

| # | Où | Ce que tu regardes |
|---|---|---|
| 1 | `https://app.onboarding.localhost/connexion/administrateur` | Le message « Identifiants acceptes. Votre session est ouverte. » **Il n'y a pas de redirection** — tape l'adresse suivante à la main. Un mauvais mot de passe rend **exactement** le même refus que cinq autres causes |
| 2 | `https://app.onboarding.localhost/` | La carte de France et les **25** entités listables. Clique une pastille |
| 3 | `…/entites/BORDEA00` | Le cadre, le sélecteur d'entité, le menu. **« Administration » apparaît** parce que tu es `SUPER` : l'affichage conditionnel est piloté par l'API, jamais par le frontend |
| 4 | `…/entites/BORDEA00/trombinoscope` | **76** collaborateurs, **4** pages de 25. **Clique une carte** : elle se retourne. **Tab + Entrée** et **Tab + Espace** font la même chose — la face est un `<button>` natif. La **bordure** porte la couleur du cercle, et le **nom** du cercle est toujours écrit : la couleur n'est jamais seule (§10.1) |
| 5 | la barre de recherche | Tape `ber`, puis `bér` : **les mêmes résultats**. La recherche ignore les accents **des deux côtés**, attend **300 ms** après la dernière frappe, et les résultats précédents restent visibles pendant le chargement |
| 6 | **« Voir plus »** sur une carte | La fiche : identité, informations professionnelles, cercles, responsabilités, présentation, et **l'historique en cinq axes**. Un axe hors de ton périmètre dirait « Hors de votre perimetre » — tu es `SUPER`, tu les vois tous |
| 7 | le bloc **« Cycle de vie »**, en bas de la fiche | **Archiver ce profil** → la conséquence est annoncée **avant** : sessions révoquées, affectations clôturées. Confirme. Le profil quitte le trombinoscope, et sa fiche affiche « **archivé** » avec **Restaurer**. Restaure-le : la réponse **NOMME** les affectations qui n'ont **pas** été rouvertes |
| 8 | `…/deconnexion` puis retour en **4** | L'API rend **401** |

**Trois choses à dire pendant la démonstration, parce qu'elles se voient :**

- **aucune photo** — le jeu fictif n'en contient pas, et les avatars neutres sont le comportement
  prévu (§21.2). L'API **sert** les miniatures depuis `T5` ; elle n'en **fabrique** aucune, c'est le
  LOT 11 ;
- **quatre filtres sur six manquent** — `ECART-060` : ils prennent un identifiant, et aucun endpoint
  ne sert ces listes. Cercles au LOT 6, métiers, clients et DSM au LOT 9. Aucun sélecteur vide n'a
  été simulé ;
- **`ECART-012` est à l'écran** : un `dg` s'affiche sans statut. **Léa doit trancher**, et l'échéance
  est dépassée.

> **Les couleurs de cercle sont une donnée de démonstration**, posée à la main dans la base locale :
> le générateur du LOT 2 laisse `color_token` nul sur ses 100 cercles. Réversible par
> `UPDATE circle SET color_token = NULL;`. Le faire dans le **générateur** appartiendrait au LOT 6.

---

## 4. Les grandeurs, avec la commande qui les produit

| Grandeur | Valeur | Commande |
|---|---:|---|
| Tests | **1 355** | ci-dessous |
| — `pytest` | **915** | `uv run pytest -q --collect-only \| tail -1` |
| — dont d'intégration | **602** | `uv run pytest -m integration -q --collect-only \| tail -1` |
| — `Vitest` | **440** | `make test-frontend` — 137 `contracts`, 111 `ui`, 192 `web` |
| Tables PostgreSQL | **29** | `information_schema.tables` |
| Migrations | **16**, tête `0016` | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Endpoints du contrat | **21** | `packages/contracts/src/contrat-api.json` |
| Cibles du `Makefile` | **86** | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Cibles appelées par `ci.yml` | **46** | `grep -oE 'make [a-z-]+' .github/workflows/ci.yml \| sort -u \| wc -l` |
| Variables de `.env.example` | **84** | `grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example` |
| **Défauts nommés au LOT 5** | **62** | `grep -ohE '\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-5.md \| sort -u \| wc -l` |
| Jeu de démonstration | **26** entités, **5 154** personnes, **28 017** lignes | mesuré en base |

---

## 5. La recette — FAITE le 12/09/2026, sur une base REMISE À ZÉRO

**La base a été détruite et reconstruite avant la mesure**, par le chemin documenté : `make down`,
suppression du **seul** volume `db-data`, `make up`, `make migrate`. Pas `make destroy`, qui
emporterait `caddy-data` et l'autorité approuvée dans ton trousseau.

```text
make check                 code=0   915 pytest · 440 Vitest · « Tous les controles sont passes »
make code-refresh          code=0   ← AVANT les controles d'ecran
make code-check            code=0
make residu-check          code=0
make profil-check          code=0   45 controles, 0 echec
make trombinoscope-check   code=0   38 controles, 0 echec
make entites-check         code=0   13 controles, 0 echec
make permissions-check     code=0
make cadre-check           code=0   25 controles, 0 echec
make cadre-temoin          code=0
make ecrans-check          code=0    8 controles, 32 modules servis
make web-check             code=0
make api-check             code=0

Les ONZE controles d'authentification
  magic-link-check 15 · admin-check 10 · sessions-check 13 · sessions-temoin
  csrf-check 10 · debit-check 12 · revocation-check 6 · service-check 11
  evenements-check 6                                    tous en code=0

Les controles de schema
  privileges-check · secrets-check · isolation-check · isolation-temoin
  historisation-check · migrations-check · recette-modele-check · alembic-check
  stack-check · ports                                   tous en code=0
```

---

## 6. Les contrôles du §30 : **aucun reclassement**, et c'est mesuré

```text
make recette-modele-check   code=0
  info  25 controles enumeres par le §30, LUS dans le modele
  ok    les 25 controles sont classes, aucun en trop
```

| Statut | Nombre |
|---|---:|
| **acquis**, chacun nommant un test qui **existe** | **13** |
| **partiel** — §30.4, dont la moitié applicable est acquise | 1 |
| **inapplicable** — §30.8 | 1 |
| **reportés**, chacun rattaché à son lot | **10** |

**Les dix reportés vont aux LOTS 7, 9, 10, 11 et 12 — aucun n'appartenait au LOT 5**, mesuré. `T12`
n'avait donc **rien à reclasser**, et c'est un constat, pas un oubli.

> **Deux acquis portent la trace du LOT 5** : le §30.12 — « une photo sans autorisation ne peut pas
> être publiée » — cite `T5` et son contrôle sur les **octets** ; et le §30.4, partiel, nomme
> **`T8` de ce lot** comme couvrant son second chemin : une restauration remet une personne en
> `active` **sans DSM**, et `restaurer_un_profil` le **nomme**.

---

## 7. Ce que le lot n'a PAS fait, et qu'il ne faut pas croire acquis

| Point | État réel |
|---|---|
| **Modifier un profil à l'écran** | **`US006` n'a AUCUN écran.** L'API est complète depuis `T7` — six champs, deux grilles de rôles, concurrence optimiste — et **aucun frontend ne l'appelle**. Délibérément hors du périmètre de `T11` |
| **Retirer une autorisation de photo** | la **lecture** honore le retrait, et `make profil-check` l'éprouve — mais **aucune route ne permet de retirer**. Cela suppose un écran et une écriture : LOT 9 |
| **Fabriquer une miniature** | `T5` en **sert** une, elle n'en **fabrique** aucune. `MVP-L11-US005`, et le **format** des variantes reste volontairement non tranché (`ECART-052`) |
| **Énumérer les profils archivés** | aucune liste. Zéro occurrence dans le corpus, et les six axes de filtre de `US002` n'incluent pas l'état d'appartenance |
| **Quatre filtres sur six** | `ECART-060` — ils prennent un identifiant, et aucun endpoint ne sert ces listes. LOT 6 et LOT 9 |
| **Le rendu visuel** | **je ne l'ai pas vu.** Il faut une session, donc un compte, et je n'en crée ni n'en saisis (§7.14). C'est l'objet du §3 |
| **`media_usage`** | la quatrième table du §16.3 n'est pas créée : elle ne sert qu'à la médiathèque **V1**. Nommée comme reportée |

---

## 8. Trois choses à connaître avant de valider

**1. `ECART-012` attend Léa, et l'échéance est dépassée.** Elle était « avant le LOT 5 », lequel est
ouvert depuis le 24/08/2026. Une catégorie `dg` ne peut porter que `intercontrat`, que le
trombinoscope **et** la fiche affichent désormais. Les deux options sont chiffrées ; la moins
coûteuse ne touche pas le modèle.

**2. `ECART-061` est nouveau, et il touche la sécurité.** `make admin-local` pose un mot de passe
provisoire et `must_change = true` ; la connexion le remonte fidèlement, **et rien ne s'ensuit** :
la session s'ouvre, toutes les routes répondent. Les **huit** écrans du LOT 3 sont ceux que le cahier
§17.5 énumère, et le changement de mot de passe **n'y est pas**. `DEC-527` affirme le contraire de ce
qui est. Deux options nommées au registre, à instruire au **LOT 13**.

**3. `images.yml` est rouge, et ce n'est pas bloquant.** Seule la tâche **Trivy** échoue, sur la
**seule** image `web` : `CVE-2026-56854`, `CRITICAL` et **corrigeable**, héritée de la base
`caddy:2.11-alpine`. **La porte fait exactement son travail** — `DEC-482` bloque sur `CRITICAL`
corrigeable. Elle n'est **pas** un contexte requis, donc les fusions ne sont pas bloquées. Une montée
de base Caddy doit d'abord être **mesurée** dans ce qu'elle casse.

---

## 9. Ta décision

**Ce que tu valides :** les sept critères de sortie du LOT 5, dont le septième est ton avis sur le
trombinoscope et les profils, formé au §3.

**Ce que la porte ouvre :** le **LOT 6** — Framework, cercles, bureaux et contenus éditoriaux.

**Ce qu'elle ne clôt pas :** `ECART-012` — Léa · `ECART-031` — avant le LOT 6 · `ECART-060` — LOT 6
et LOT 9 · `ECART-061` — LOT 13 · `US006` sans écran.

| | |
|---|---|
| Date | |
| Décision | ☐ franchie ☐ à reprendre |
| Réserves | |
