# Prototype historique — `V1.html`

Ce dossier conserve le prototype d'origine à des fins d'**historisation**, sur décision de
Jonathan.

---

## 1. Statut

| Élément | Valeur |
|---|---|
| Fichier | `V1.html` |
| Taille | 2 833 866 octets (2,83 Mo), 2 053 lignes |
| Empreinte SHA-256 | `232f0700b9fdc3467ad8d8bd4e5c2260b6cacad09dd140a991669e662aa9ba2d` |
| Présence sur disque | Oui, dans ce dossier |
| Suivi par Git | **Non** — exclu par `.gitignore` |
| Réutilisable comme base de code | **Non** |

---

## 2. Pourquoi ce fichier n'est pas versionné

Le prototype contient des données et des éléments qui, versionnés, empêcheraient de valider
la porte `G0` et créeraient un risque durable.

| Contenu constaté | Volume constaté | Règle enfreinte si versionné |
|---|---|---|
| Noms et prénoms de collaborateurs réels | environ 130 personnes, réparties dans les huit cercles, les listes DSM et la liste Framework | Roadmap, LOT 0, critère de sortie n°4 : « aucun fichier réel de collaborateurs n'est versionné » |
| Photographies de personnes encodées en Base64 | 160 occurrences de `base64` | Cahier des charges 21.2 : la photo exige une autorisation explicite. Modèle de données 2.6 et cahier 19.1 : aucun Base64, aucun média dans Git |
| Clients et affectations professionnelles | structure `peopleInfo` | RGPD, minimisation des données |
| Mot de passe administrateur en clair dans le code | 1 constante, ligne 1073 | Cahier des charges 7.3 : aucun mot de passe intégré au code. Backlog 12 : une porte ne peut être validée si un secret a été versionné |
| Stockage navigateur des modifications | 11 usages de `localStorage` | Roadmap 2.3 : aucune donnée métier durable dans `localStorage` |
| Dépendances chargées depuis des CDN publics | React, ReactDOM, Babel, Tailwind, Google Fonts | Roadmap 2.3 : aucune dépendance essentielle à un CDN public |

Le mot de passe présent dans ce fichier doit être considéré comme **compromis** et ne doit
jamais être réutilisé, dans aucun environnement.

---

## 3. Ce que le prototype peut légitimement fournir

Conformément au cahier des charges, section 2.2, le prototype sert uniquement à :

- conserver l'intention visuelle ;
- identifier les fonctions utiles ;
- reprendre, **après relecture**, certains textes, descriptions de cercles, descriptions de
  bureaux et liens internes.

L'inventaire structuré de ces contenus est produit en sous-étape **S7** du LOT 0
(story `MVP-L00-US005`, priorité P1) et sera déposé dans `docs/product/contenus/`.
Cet inventaire ne contiendra aucune donnée personnelle.

Les données collaborateurs du prototype ne constituent **jamais** une source officielle :
la source officielle est le CSV validé (cahier des charges, section 12.1).

---

## 4. Interdictions explicites

- ne pas réutiliser une ligne de code de ce fichier ;
- ne pas importer ses données collaborateurs ;
- ne pas réutiliser le mot de passe qu'il contient ;
- ne pas le retirer de `.gitignore` sans décision explicite et tracée de Jonathan,
  accompagnée d'une analyse d'impact RGPD.

---

## 5. Historique des décisions liées

| Date | Décision |
|---|---|
| 27 juillet 2026 | Jonathan décide que le prototype reste conservé dans `docs/` pour historisation. L'exclusion du suivi Git est appliquée pour respecter le critère de sortie n°4 du LOT 0. Décision à consigner au registre en sous-étape S4. |
