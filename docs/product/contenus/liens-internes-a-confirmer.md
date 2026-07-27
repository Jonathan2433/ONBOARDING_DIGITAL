# Liens internes à confirmer

**Produit en :** LOT 0, sous-étape S7 — story `MVP-L00-US005`, priorité `P1`
**Destination :** LOT 6, story `MVP-L06-US005` « Gérer la présentation et les liens internes de l'entité »

---

## 1. Constat principal

**Le prototype ne contient aucun lien interne exploitable.**

C'est un résultat contre-intuitif, puisque le cahier des charges §2.2 et §12.1 annoncent que le
prototype fournit des « liens internes ». La vérification établit qu'il n'en fournit aucun.

### 1.1 Inventaire exhaustif des URL présentes dans le prototype

Sept URL au total, aucune n'étant un lien interne eXalt.

| URL | Nature | Réutilisable |
|---|---|---|
| `https://cdnjs.cloudflare.com/…/react.production.min.js` | Dépendance CDN | Non |
| `https://cdnjs.cloudflare.com/…/react-dom.production.min.js` | Dépendance CDN | Non |
| `https://cdnjs.cloudflare.com/…/babel.min.js` | Dépendance CDN | Non |
| `https://cdn.tailwindcss.com` | Dépendance CDN | Non |
| `https://fonts.googleapis.com/…Plus+Jakarta+Sans…` | Police via CDN | Non |
| `https://stream.microsoft.com/...` | **Exemple dans un commentaire de code**, littéralement avec les points de suspension | Non |
| `https://ton-sharepoint.com/.../logo.png` | **Exemple dans un commentaire de code**, domaine fictif | Non |

Les quatre premières sont des dépendances CDN publiques, formellement interdites par la roadmap
§2.3. Les deux dernières sont des indications d'usage laissées à l'attention de la personne
maintenant le prototype, pas des adresses réelles.

La page d'onboarding embarquée contient deux URL supplémentaires vers `teams.microsoft.com`, dont
`https://teams.microsoft.com/l/meeting/new`. Elles ne sont pas des liens internes eXalt, et les
intégrations Microsoft restent en V2 (`ROAD-009`).

### 1.2 Vérification des mentions textuelles

| Terme | Occurrences dans le texte réel | Nature |
|---|---:|---|
| **Hub** | **0** | Le terme n'apparaît nulle part |
| **eXalt Academy** | 3, uniquement dans les tâches d'onboarding | Cité comme destination de formation, sans lien |
| **SharePoint** | 7, **toutes dans des commentaires de code** | Instructions d'usage : « Colle l'URL SharePoint de ton logo » |

> **Correction d'un constat antérieur.** Mon rapport de prise en charge du LOT 0 annonçait 96
> occurrences de « Hub », 96 de « BDS », 46 de « BDE » et 79 de « BDG ». Ces comptages étaient
> **faux** : ils portaient sur le fichier entier, chaînes Base64 incluses, où des séquences de
> caractères produisent des correspondances fortuites. Sur les 194 566 caractères de texte réel,
> les comptages sont : Hub 0, BDS 7, BDE 5, BDG 5. Le contenu éditorial des bureaux est
> néanmoins bien présent et relevé dans l'[inventaire](inventaire-prototype.md).

---

## 2. Conséquence

Les trois cartes de liens internes attendues à l'accueil d'entité — Hub, eXalt Academy,
SharePoint (cahier §8.4, position 5) — devront être **renseignées de zéro**.

| Lien attendu | Source dans le prototype | Qui fournit l'URL | Échéance utile |
|---|---|---|---|
| Hub | aucune | Léa ou Tess | LOT 6, `MVP-L06-US005` |
| eXalt Academy | aucune, seulement des mentions textuelles | Léa ou Tess | LOT 6, `MVP-L06-US005` |
| SharePoint de l'entité | aucune | Tess ou ESM | LOT 6, `MVP-L06-US005` |

Ce n'est **pas bloquant pour le LOT 0** : la story `MVP-L06-US005` prévoit que ces liens sont
modifiables localement par l'ESM et l'administrateur d'entité. Le LOT 6 peut donc livrer la
fonctionnalité avec des emplacements vides, puis les liens sont saisis en configuration.

Ce n'est pas non plus une dépendance externe au sens de `DEP-nnn` : il s'agit d'une saisie de
configuration, non d'un élément à obtenir d'un tiers.

---

## 3. Exigences applicables aux URL, quand elles seront fournies

| Exigence | Source |
|---|---|
| Les URL sont validées selon une liste de protocoles autorisés | Modèle §15.3 |
| Une carte de lien indique clairement qu'elle ouvre une ressource externe | Backlog `MVP-L08-US006` |
| Les liens sont modifiables localement par l'ESM et l'administrateur d'entité | Matrice §13, `MVP-L06-US005` |
| Toute modification de lien est auditée | `RIGHTS-016` |
| Aucune dépendance essentielle à un CDN public | Roadmap §2.3 |

---

## 4. Statut

| Élément | Statut |
|---|---|
| Lien Hub | **à fournir** |
| Lien eXalt Academy | **à fournir** |
| Lien SharePoint | **à fournir** |
| Liens repris du prototype | **aucun** |

Écart enregistré : `ECART-015`.
