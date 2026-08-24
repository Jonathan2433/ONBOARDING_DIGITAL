# Compte rendu — LOT 4, sous-étape `T6`

**La page nationale, et l'adresse que le corpus ne nommait pas**
**Story :** `MVP-L04-US001` · **Réalisée le :** 23 août 2026
**Décision produite :** `DEC-549` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. L'adresse : une question posée, une mesure d'abord

J'avais signalé ce point à la sortie de `T5` : le cahier §4.1 dit « une page nationale **après
authentification** », le diagramme du §8.1 la place juste après la connexion, la séquence du §9.1
finit sur « Accueil national » — et **aucun document ne nomme d'adresse**. Or `/` servait la page de
statut depuis `T5` du LOT 1, et `make web-check` l'exigeait.

**Avant de poser la question, j'ai mesuré ce qu'elle coûtait.** `verifier-page-statut.sh` n'exige de
`/` que **la coquille React** et le mandatement des endpoints de santé : il ne vérifie **jamais** le
contenu de la page de statut. Déplacer celle-ci ne cassait donc rien.

> C'est ce qui a permis de présenter les trois options **sur leur seul sens d'usage**, et non sur un
> coût technique. Arbitrage de Jonathan : **`/` est la page nationale, le statut passe à `/statut`,
> même contenu.**

**Et le contrôle a été complété**, parce que rien ne garantissait plus que `/statut` existe :
`verifier-page-statut.sh` passe de 6 à **7** contrôles et exige que l'adresse soit **servie**. Le
repli SPA rendant `text/html` pour n'importe quel chemin, c'est le **type MIME** qui fait foi, pas le
code HTTP — leçon `T5-6` du LOT 1.

**Une affirmation devenue fausse a été corrigée du même geste.** L'écran de consommation du magic
link disait « Le portail arrive dans une prochaine version ; **aucune page ne vous attend ici** ».
C'était vrai jusqu'à `T6`. Le laisser aurait été laisser exactement ce que le §9.0 de la passation
reproche au corpus : une affirmation jamais revue.

---

## 2. Trois décisions structurelles, et le motif de chacune

### La page nationale n'emploie pas `CadreApplicatif`

Le cadre **résout une entité consultée** et la porte dans son en-tête. Ici on est **au-dessus** de
l'entité : on la choisit. L'employer exigerait une entité pour afficher la page dont l'objet est de la
choisir.

Elle porte donc son propre en-tête minimal, son lien d'évitement et son `<main tabIndex={-1}>` — la
condition sans laquelle le lien d'évitement ne saute rien, `ECART-043`.

### « La liste précède la carte dans le DOM, pas seulement à l'œil »

C'est le critère de sortie, et la distinction est tout :

> Un ordre obtenu par `order` en CSS satisferait le regard sur mobile et laisserait la carte **avant**
> la liste pour un lecteur d'écran et pour la tabulation. **L'échec produirait la même observation que
> le succès sur une capture d'écran.**

Le contrôle porte donc sur la **source** : la liste doit exister, aucune règle CSS ne doit la
réordonner, et la carte — quand `T7` l'apportera avec la classe `nat-carte` — devra venir **après**.
**Il mordra à `T7`**, et en attendant il rapporte que la carte est absente plutôt que de se taire.

`T7` a par ailleurs une contrainte que le §8.3 impose : la carte n'est dite que « **illustrative** »,
donc elle ne devra **jamais** être le seul moyen d'atteindre une entité. La liste l'est, et elle vient
d'abord.

### Le frontend ne refiltre rien

`GET /api/v1/entities` filtre sur `status = active` — cahier §8.3, « un accès à chaque entité
**active** » — et `make entites-check` le prouve à travers Caddy. Refaire le filtre côté écran
donnerait **deux règles**, et le jour où l'une change l'autre mentirait.

**Mesuré de bout en bout** : sur quatre entités dont une `draft` nommée « NE DOIT PAS APPARAITRE », la
page en affiche **trois**.

---

## 3. Quatre états, dont deux qu'on confond facilement

| État | Ce qu'il dit | Ce qu'il ne dit pas |
|---|---|---|
| chargement | « Chargement des entités… » | — |
| liste | une carte par entité | — |
| **aucune entité active** | « il n'y a rien à choisir, et **ce n'est pas une erreur** » | rien sur une panne |
| erreur 401 | « votre session a expiré », + lien de reconnexion | **ne parle pas de réseau** |
| erreur réseau | « vérifiez votre connexion » | **ne prétend rien** sur l'existence des entités |

**« Aucune entité active » est un état légitime** — une plateforme neuve — et le confondre avec une
panne dirait à l'utilisateur une chose fausse. C'est le même parti qu'en `T2` pour « introuvable »
contre « erreur ». **Les deux sont mesurés**, et le test du 401 vérifie explicitement que le message
ne parle **pas** de réseau.

---

## 4. Les mesures, dans un vrai navigateur

| Largeur | Colonnes | Cartes | Débordement | Brouillon affiché |
|---:|---:|---|---|---|
| **320** | 1 | 304×63 et 304×88 | **non** | **non** |
| **1 280** | **3** | 379 px, **les trois sur une ligne** | **non** | **non** |

**Le parcours complet, mesuré** : `/` → la liste des trois entités actives → clic → `/entites/t6-bordeaux`,
l'entité dans l'en-tête, le `<h1>` « Accueil de l'entité », la barre mobile en place. Puis
déconnexion, rechargement de `/` : « Votre session a expiré », un lien vers la connexion, **aucune
liste**, et **aucune mention de réseau**.

---

## 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest, **191** Vitest (90 `ui`, **84 `web`**, 17 `contracts`) |
| `make cadre-check` | **code 0** — **19 contrôles**, dans `make check` et dans la CI |
| `make cadre-temoin` | **code 0** — il échoue en nommant **les huit** motifs attendus |
| `make web-check` | **code 0** — **7 contrôles** (6 + 1), `/statut` servie |
| `entites-check` `residu-check` `ecrans-check` `api-check` `sessions-check` `csrf-check` | **code 0** pour les six |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

**Un contrôle a couvert le nouveau code sans que j'y touche** : `cadre-check` exige qu'un élément
interactif ait une règle `:focus-visible`, et sa liste est dérivée du **TSX** depuis `T5`. La nouvelle
classe `.nat-entite`, portée par un `<Link>`, a donc été prise en compte automatiquement. C'est ce que
`T5` avait gagné en remplaçant une dérivation par nommage — qui avait produit un faux positif — par
une dérivation par type d'élément.

---

## 6. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **la carte de France** | `T7`. `entity` ne porte **ni latitude ni longitude** — le seul point du §8 de la fiche qui reste ouvert |
| **le changement d'entité de bout en bout** | `T8`, où les cinq règles du §23.3 deviennent toutes exigibles |
| **la redirection automatique après connexion** | l'écran de consommation du lien **propose** le portail ; il n'y redirige pas. Une redirection automatique masquerait l'écran de confirmation, que le corpus énumère comme un des huit écrans (§17.5) |
| **que React monte bien la page de statut à `/statut`** | le contrôle prouve que l'adresse est **servie** ; l'exécuter demanderait un moteur de rendu, donc Playwright, **LOT 12** |

---

## 7. Ce que `T7` devra savoir

1. **la carte se pose APRÈS la liste**, avec la classe `nat-carte` — c'est ce que `cadre-check`
   attend, et il échouera si elle vient avant ou si une règle CSS réordonne la liste ;
2. **elle est « illustrative »**, et c'est le seul mot du corpus. Elle ne doit **jamais** être le seul
   moyen d'atteindre une entité ;
3. **`entity` ne porte ni latitude ni longitude** — mesuré sur le schéma réel. Trois options se
   dessinaient au §8 de la fiche : carte décorative sans marqueurs, positions portées par le code pour
   les villes connues, ou une colonne au modèle — qui serait une **modification du schéma**, donc à
   instruire ;
4. **`city` est le seul champ géographique exposé** par `GET /api/v1/entities`, et il l'est pour la
   **liste**, pas pour la carte.
