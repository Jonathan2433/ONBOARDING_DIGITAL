# `packages/contracts` — contrat API partagé

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Rempli en :** LOT 1, sous-étape `T10`, `DEC-492`
**Fondement :** cahier des charges §15.3, §18.1
**Dernière mise à jour :** 7 septembre 2026, `T5` du LOT 5

---

## 1. Le sens de vérification est INVERSÉ, et c'est mesuré

> **Ce document a longtemps affirmé le contraire** — « le contrat est **généré**, jamais transcrit
> à la main » — et c'était la bonne intention avec le mauvais mécanisme. `T10` du LOT 1 a mesuré
> pourquoi elle ne tient pas.

**`components.schemas` du schéma OpenAPI servi est VIDE.** Les routes rendent des dictionnaires
sans modèle Pydantic pour une partie d'entre elles, et générer depuis ce schéma aurait produit des
types `unknown` : **l'illusion d'un contrat typé**, ce qui est pire que pas de contrat du tout.

Le mécanisme retenu inverse le sens :

```text
contrat-api.json        SOURCE UNIQUE, ecrite a la main et RELUE
        |
        +--> TypeScript lit le manifeste et en derive ses chemins et ses codes
        |
        +--> un controle PYTHON verifie que le schema OpenAPI SERVI le respecte
             (apps/api/tests/test_contrat.py, 5 tests)
```

**Ce contrôle a produit un constat dès sa première exécution** : l'API ne documentait **pas** le 503
de `/health/ready`, que le frontend traite comme un état exploitable depuis `T5` du LOT 1.

Il exige trois choses, et la première est celle qui compte :

| Ce qu'il vérifie | Pourquoi |
|---|---|
| les chemins du schéma servi sont **exactement** ceux du manifeste | ni plus ni moins : une route ajoutée sans être déclarée fait échouer, une route déclarée et absente aussi |
| chaque **code exploitable** déclaré est documenté par l'opération | un client qui traite 503 comme un état doit pouvoir le lire dans le schéma |
| le préfixe versionné et l'en-tête de corrélation sont ceux que l'API emploie | deux copies d'une constante divergent |

---

## 2. Ce que le paquet contient

**16 endpoints déclarés, 81 tests.** Les compter, jamais les recopier :

```bash
python3 -c "import json,pathlib; print(len(json.loads(pathlib.Path('packages/contracts/src/contrat-api.json').read_text())['endpoints']))"
pnpm --filter @onboarding/contracts test
```

| Fichier | Ce qu'il porte |
|---|---|
| `contrat-api.json` | **la source unique**, lue par TypeScript **et** par Python |
| `sante.ts` | les trois sondes, et `endpoint()` qui lit le manifeste |
| `formes.ts` | `estObjet` / `exigerChaine`, **extraites** de `sante.ts` — un seul exemplaire. **Non réexporté** : la frontière n'est pas contournable |
| `portail.ts` | les entités du portail, et `cheminEntite` |
| `trombinoscope.ts` | la liste paginée, ses cinq filtres, et `cheminDePhotoOuNul` |
| `profil.ts` | la fiche complète — **elle importe** `cheminDePhotoOuNul`, elle ne la recopie pas |

---

## 3. La frontière `snake_case` → `camelCase` est ICI

L'API rend du `snake_case`, les composants consomment du `camelCase`. **La traduction est dans le
validateur**, et le validateur n'est pas contournable — `formes.ts` n'est pas réexporté par
`index.ts`, donc un consommateur ne peut pas valider lui-même en contournant la frontière.

**Et l'absence n'est pas `null`.** Un champ **manquant** est une réponse malformée ; un champ à
`null` est une donnée légitimement absente. Les confondre ferait écrire un jour « ce champ est nul,
donc l'appelant n'y a pas droit » — ce qui serait faux : **aucun champ n'est masqué** (`ECART-051`).

```ts
chaineOuNul(valeur, 'client')   // null accepte, absence REFUSEE
exigerChaine(valeur, 'id')      // ni null ni absence
```

---

## 4. Les pièges mesurés sur ce paquet

### Un chemin vide donne le chemin de la LISTE

`cheminEntite('')` produirait `/api/v1/entities/` — donc la **liste** au lieu d'une entité, et le
client croirait consulter un élément. Les fonctions de chemin **lèvent** sur une chaîne vide, et
elles **encodent** leurs segments.

### Un validateur de type ne suffit pas pour une CLÉ D'OBJET

`cheminDePhotoOuNul` refuse toute valeur qui ne commence pas par le préfixe versionné. **C'est le
contrôle le plus utile du paquet** : si l'API rendait un jour l'`object_key` de MinIO au lieu du
chemin de la route, **tous** les contrôles de type resteraient verts — c'est une chaîne. Seul le
préfixe discrimine, et le §16.1 veut que la disposition du stockage ne sorte jamais.

Il refuse aussi une donnée `data:image/jpeg;base64,…`, que le §16.1 interdit en propre.

### Deux validateurs qui concordent aujourd'hui divergeront demain

La liste et la fiche annoncent le **même** chemin de photo. Un test prouve qu'ils emploient
**exactement la même fonction**, par l'identité du message d'erreur **à l'octet** — comparer leurs
verdicts sur un échantillon ne prouverait rien, deux implémentations distinctes peuvent concorder
sur tous les cas essayés.

### Un tableau absent est indistinguable d'un tableau vide

`validerLaFiche` **exige** `cercles_secondaires` et `responsabilites`. Une réponse tronquée
rendrait autrement une liste vide, indistinguable d'un collaborateur qui n'a légitimement aucun
cercle secondaire — l'échec produirait la même observation que le succès.

---

## 5. Ce que le paquet ne fait PAS

| Absent | Pourquoi |
|---|---|
| les **paramètres de requête** ne sont pas au manifeste | il déclare des chemins et des codes, pas des paramètres. Les listes de valeurs — tailles de page, statuts professionnels — sont donc **écrites** dans le `.ts`, et **le dire vaut mieux que de laisser croire qu'elles sont dérivées**. L'API reste l'autorité : ces listes servent seulement à ce que l'écran ne **propose** que des valeurs valides |
| aucun type de table | le modèle de données est **immuable** et fait foi. Ce paquet décrit ce que l'**API** rend, pas ce que la base stocke |

---

## 6. Commandes

```bash
pnpm --filter @onboarding/contracts test        # 81 tests
make typecheck                                  # tsc --noEmit strict
uv run pytest apps/api/tests/test_contrat.py    # le schema SERVI respecte-t-il le manifeste
```
