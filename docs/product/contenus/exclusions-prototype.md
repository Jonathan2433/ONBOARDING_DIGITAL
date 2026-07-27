# Exclusions explicites du prototype

**Produit en :** LOT 0, sous-étape S7 — story `MVP-L00-US005`, priorité `P1`

Ce document énumère ce qui, dans le prototype, ne sera **jamais** repris, et pourquoi. Son
objet est de rendre l'exclusion opposable : un contenu absent de l'inventaire n'est pas un
oubli, c'est une exclusion motivée.

---

## 1. Données personnelles — exclusion absolue

| Contenu du prototype | Volume constaté | Motif d'exclusion |
|---|---|---|
| Noms et prénoms de collaborateurs | environ 130 personnes, réparties dans les huit listes de cercles, deux listes DSM et une liste Framework | Roadmap, LOT 0, critère de sortie n°4 : aucun fichier réel de collaborateurs n'est versionné. La source officielle des collaborateurs est le CSV validé (cahier §12.1) |
| Photographies de personnes | 160 chaînes Base64 | Cahier §21.2 : la photo exige une autorisation explicite. Aucune preuve d'autorisation n'est disponible : `QO-098`, bloquante avant données réelles |
| Photographies de bureaux | structure dédiée | Même motif : autorisation et provenance inconnues |
| Rôles, clients et dates de mission individuels | structure `peopleInfo` | Données professionnelles nominatives. RGPD, minimisation. Leur source officielle est le CSV |
| Représentants de cercle et de bureau nommés | plusieurs listes | Les responsabilités seront attribuées par l'ESM, avec audit (`ARB-DROIT-002`) |

**Aucune de ces données n'a été relevée, transposée ni recopiée**, y compris dans les documents
de travail temporaires conservés hors du dépôt.

Les données collaborateurs du prototype ne constituent **jamais** une source officielle
(cahier §2.2).

---

## 2. Éléments techniques — exclusion absolue

| Contenu | Motif |
|---|---|
| Tout le code source, React, JSX et JavaScript | Cahier §2.2 : le prototype ne constitue pas une base de code réutilisable |
| Mot de passe administrateur en clair dans le code | Cahier §7.3. Le mot de passe est **compromis par construction** et ne doit jamais être réutilisé (`ROAD-RSK-025`) |
| Stockage navigateur des modifications, 11 usages de `localStorage` | Roadmap §2.3 : aucune donnée métier durable dans `localStorage` |
| Dépendances CDN publiques : React, ReactDOM, Babel, Tailwind, Google Fonts | Roadmap §2.3 : aucune dépendance essentielle à un CDN public |
| Logo eXalt en Base64 | Modèle §2.6 et cahier §19.1 : aucun Base64, aucun média dans Git. Le logo officiel est la dépendance `DEP-006` |
| Compilation Babel dans le navigateur | Incompatible avec la chaîne validée React, TypeScript strict et Vite |
| Mécanisme d'export et de redistribution manuelle du fichier | Remplacé par une base relationnelle et un back-office |
| Police « Plus Jakarta Sans » chargée depuis Google Fonts | La police officielle relève de `DEP-006`, sous réserve de licence web (cahier §13.1) |

---

## 3. Fonctions du prototype sans équivalent au MVP

| Fonction du prototype | Traitement |
|---|---|
| Panneau d'administration protégé par un mot de passe unique en dur | Remplacé par les magic links, les comptes administrateurs locaux et la matrice des droits |
| Modifications appliquées à un seul appareil | Remplacé par PostgreSQL comme source de vérité |
| Appels à l'inscription aux événements, présents dans les descriptions de bureaux | Le MVP est **strictement informatif** : aucune inscription, aucune liste de participants, aucune notification métier (cahier §10.6). Les descriptions doivent être adaptées, voir `CONT-012` à `CONT-014` |
| Liens de création de réunion Teams dans la page d'onboarding | Les intégrations Microsoft sont en V2 (`ROAD-009`, `DEP-017`) |

---

## 4. Éléments absents du prototype, contrairement à ce qu'annonçait le cadrage

Ces éléments ne sont pas exclus : ils **n'existent pas** dans le prototype et devront être
produits.

| Élément annoncé par le cahier §2.2 et §12.1 | Réalité constatée | Où il sera produit |
|---|---|---|
| Descriptions de cercles | **Aucune.** Les huit cercles ne portent qu'une couleur et une variante d'icône | À rédiger au LOT 6 |
| Liens internes | **Aucun.** Voir [liens-internes-a-confirmer.md](liens-internes-a-confirmer.md) | À fournir au LOT 6 |
| Vidéos | Onze emplacements, **tous vides** | LOT 6 et V1 |

Écart enregistré : `ECART-015`.

---

## 5. Statut du fichier prototype

Le fichier `docs/prototype/V1.html` est conservé sur disque pour historisation, par `DEC-420`,
et **exclu du suivi Git**. Voir [docs/prototype/README.md](../../prototype/README.md).

L'analyse ayant produit cet inventaire s'est faite en lecture seule, sur une copie de travail
placée hors du dépôt et dépouillée de ses chaînes Base64. Cette copie n'est pas conservée.

---

## 6. Règle générale

En cas de doute sur un contenu du prototype, la règle est l'**exclusion**. Le prototype est une
référence d'intention, pas une source de données ni de code. Un contenu utile mais douteux se
réécrit ; il ne se recopie pas.
