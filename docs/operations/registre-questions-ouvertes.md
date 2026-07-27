# Registre des questions ouvertes

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 27 juillet 2026
**Source reprise :** cahier des charges §32

| Catégorie | Nombre | Dont closes |
|---|---:|---:|
| Bloquantes avant données réelles ou production générale | 17 | 0 |
| Non bloquantes pour le développement | 12 | 1 |
| Ouvertes par la réalisation, à partir de `QO-106` | 5 | 3 |
| **Total** | **34** | **4** |

**30 questions restent ouvertes.** Closes le 27 juillet 2026 en sous-étape `T0` : `QO-086`
(moteur Docker constaté), `QO-107` (protection de branche possible, prouvée, `DEC-449`),
`QO-108` (moyen de mise en place GitHub, `DEC-448` puis `DEC-449`), `QO-109` (atténuations
iCloud, `DEC-439` et `DEC-447`). Une question close conserve son identifiant, sa réponse et sa
date de clôture ; elle n'est jamais retirée du registre.

**Prochain identifiant libre : `QO-111`.**

> **Trous conservés dans la séquence.** La plage `QO-072` à `QO-105` couvre 34 numéros mais
> seules **29** questions sont présentes dans le corpus. Absentes : `QO-075`, `QO-079`,
> `QO-080`, `QO-082`, `QO-090`. Ces trous ne sont **jamais** comblés, conformément aux règles
> de numérotation. Voir `ECART-011`.

---

# 1. Bloquantes avant données réelles ou production générale

Aucune de ces questions ne bloque le développement local. Chacune bloque soit le chargement
de données réelles, soit l'ouverture générale.

| ID | Question | Responsable | Bloque | Statut |
|---|---|---|---|---|
| `QO-072` | Durée maximale des jetons de comptes de service | Jonathan / sécurité | LOT 3, story `MVP-L03-US007` | Ouverte |
| `QO-073` | Personnes morales exactes responsables de traitement | eXalt / juridique | Production générale | Ouverte |
| `QO-074` | Contact RGPD ou DPO | eXalt | Production générale | Ouverte |
| `QO-076` | Base légale exacte des traitements | eXalt / juridique | Production générale | Ouverte |
| `QO-077` | Nécessité d'une AIPD | eXalt / RGPD | Production générale | Ouverte |
| `QO-078` | Modalités d'effacement dans les sauvegardes | Architecture / RGPD | Production générale | Ouverte |
| `QO-081` | Hébergement permanent de production | Jonathan / eXalt | Production générale, LOT 14 | Ouverte |
| `QO-083` | Emplacement de sauvegarde local | Jonathan | LOT 13 | Ouverte |
| `QO-085` | RAM et espace disque exacts du Mac M5 | Jonathan | LOT 1 | **Mesurée, à confirmer** |
| `QO-087` | SSD externe de sauvegarde | Jonathan | LOT 13 | Ouverte |
| `QO-088` | Destination chiffrée hors site | Jonathan / eXalt | Production générale | Ouverte |
| `QO-096` | Schéma définitif des colonnes du CSV | Jonathan / ESM | Données réelles, LOT 9 | Ouverte |
| `QO-097` | Personne remettant formellement le CSV final | Léa / ESM | Données réelles, LOT 14 | Ouverte |
| `QO-098` | Preuves disponibles d'autorisation des photos | RH / ESM | Données réelles, LOT 5 | Ouverte |
| `QO-099` | Nombre maximal de lignes rejetées acceptable au lancement | Léa / Jonathan | LOT 9 | Ouverte |
| `QO-100` | Durée de conservation du CSV source | RGPD / architecture | Données réelles, LOT 9 | Ouverte |
| `QO-101` | Configuration matérielle de l'hébergement final | Jonathan / eXalt | Production générale | Ouverte |

## 1.1 Éléments de réponse constatés pour `QO-085`

Mesures relevées en lecture seule sur la machine de développement le 27 juillet 2026 :

| Grandeur | Valeur constatée |
|---|---|
| Processeur | Apple M5 |
| Mémoire vive | **16 Gio** |
| Espace disque disponible | 564 Gio sur 926 Gio |
| FileVault | Actif |
| Docker | 29.5.3, Compose v5.1.4 |

Ces constats **alimentent** la question, ils ne la ferment pas : la décision d'exploitation
appartient à Jonathan.

### Mesures complémentaires du 27 juillet 2026, sous-étape `T0`

Les 16 Gio de la machine **ne sont pas le plafond applicable**. Mesures directes :

| Grandeur | Valeur mesurée | Source |
|---|---|---|
| Mémoire allouée à la VM Docker | **7,75 Gio**, soit la moitié de la machine | `docker info --format '{{.MemTotal}}'` |
| Conteneurs tiers actifs au moment de la mesure | **5**, projet `observatoire-ecom-studio`, actifs depuis 5 jours | `docker ps` |
| Mémoire occupée par ces conteneurs | **~1,93 Gio, soit 25 % du budget Docker**, dont 1,77 Gio pour le seul worker | `docker stats --no-stream` |
| Marge restante pour les 8 services du LOT 1 | **~5,8 Gio** | déduction |
| Image disque de la VM Docker | 28 Go, sous `~/Library/Containers/`, **hors iCloud** | `du -sh` |

Ces éléments **ne closent pas** `QO-085` : le dimensionnement définitif reste à confirmer par
Jonathan une fois les 8 services démarrés et mesurés en charge. Ils ont en revanche conduit à
réécrire `ROAD-RSK-027`, dont les deux prémisses étaient inexactes, et à la décision `DEC-440`
— exécution non simultanée et arrêt du projet tiers pendant le LOT 1.

---

# 2. Non bloquantes pour commencer le développement

| ID | Question | Responsable | Échéance utile | Statut |
|---|---|---|---|---|
| `QO-084` | Introduction immédiate ou différée de PostgreSQL RLS | Architecture | LOT 2 | Ouverte |
| `QO-086` | Installation actuelle de Docker Desktop ou moteur alternatif | Jonathan | LOT 1 | **Close le 27/07/2026**, sous-étape `T0` : Docker Desktop 29.5.3, Compose v5.1.4, pilote `overlayfs`, `aarch64`. Aucun moteur alternatif |
| `QO-089` | Confirmation du RTO de quatre heures | Exploitation | LOT 13 | Ouverte |
| `QO-091` | Supervision du Mac par Tailscale ou moniteurs Push | Jonathan | LOT 13 | Ouverte |
| `QO-092` | Destination des signalements de bugs | Jonathan / eXalt | LOT 10 | Ouverte |
| `QO-093` | Pièce jointe de capture d'écran dans les bugs | Produit | LOT 10 | Ouverte |
| `QO-094` | Second référent technique avant production | eXalt | Production générale | Ouverte |
| `QO-095` | Suivi des maintenances annoncées dans Uptime Kuma | Exploitation | LOT 13 | Ouverte |
| `QO-102` | Volumétrie vidéo annuelle attendue | Tess / ESM | LOT 11 | Ouverte |
| `QO-103` | Limites médias configurables dès la V1 | Produit | V1 | Ouverte |
| `QO-104` | Outil de charge : k6 ou Locust | Architecture | LOT 12 | Ouverte |
| `QO-105` | Taux d'erreur maximal contractuel | Produit / technique | LOT 12 | Ouverte |

`QO-094` mérite une attention particulière : elle conditionne la décision `DEC-429`. Tant que
Jonathan est l'unique relecteur, aucune approbation de pull request ne peut être exigée,
GitHub interdisant l'auto-approbation.

---

# 3. Questions ouvertes par la réalisation

| ID | Question | Responsable | Bloque | Statut |
|---|---|---|---|---|
| `QO-106` | Retient-on les compléments d'étiquettes GitHub proposés — familles `type`, `gravité` et `état` ? Ils ne sont pas prescrits par les documents validés. | Jonathan | Non. Confort de suivi. | Ouverte |
| `QO-107` | Le plan GitHub du compte permet-il les règles de protection de branche sur un dépôt privé personnel ? Si non, le repli documenté est un garde-fou local `pre-push`, qui ne remplace pas la protection côté serveur. | Jonathan | Non pour `G0`. Prérequis du LOT 1 pour rendre `DEC-429` effective. | **Close le 27/07/2026 par l'affirmative.** Le plan autorise la protection classique sur ce dépôt privé personnel : `main` et `develop` sont protégées avec `enforce_admins`, et le rejet du push direct est prouvé (`GH006`). **Le repli `pre-push` devient sans objet.** `DEC-449` |
| `QO-108` | Comment réalise-t-on la mise en place GitHub — installation de `gh`, interface web, ou connecteur ? Aucun outil d'accès à l'API GitHub n'est disponible dans la session de travail. | Jonathan | Non pour `G0`. Prérequis du LOT 1. | **Close le 27/07/2026.** Réponse initiale `DEC-448` — mise en place dans l'interface par Jonathan. **Réponse effective `DEC-449`, qui remplace `DEC-448`** : installation du binaire `gh` 2.96.0 dans `~/.local/bin` par l'agent, Homebrew étant inutilisable, puis authentification par Jonathan et exécution par `gh` |
| `QO-109` | Quelles atténuations retient-on pour les volumes Docker et les dépendances, le dépôt résidant dans iCloud Drive par `DEC-418` ? `.gitignore` empêche Git de les suivre mais n'empêche pas iCloud de les synchroniser. | Jonathan / architecture | Non pour `G0`. Était à trancher au LOT 1, avant création des volumes. | **Close le 27/07/2026**, sous-étape `T0`, par `DEC-439` et `DEC-447` |
| `QO-110` | Quelle nomenclature et quelle langue pour les en-têtes du CSV collaborateurs ? Jonathan n'a pas encore de visibilité sur la source de données réelle. Traitement retenu en attendant : le schéma définit des champs logiques `F01` à `F19` et un profil de correspondance versionné associe les en-têtes réelles (`DEC-434`). Un profil provisoire, non normatif, est utilisé dans le jeu d'exemple. | Jonathan / ESM | Non pour `G0`. Rattachée à `QO-096`, **bloquante avant l'import réel** au LOT 9. | Ouverte |

---

# 4. Règles de tenue

- une question fermée conserve son identifiant, sa réponse et sa date de clôture ;
- une question qui devient bloquante voit son statut modifié, jamais son identifiant ;
- une réponse partielle est consignée comme élément de réponse, sans clore la question ;
- une question résolue par un arbitrage renvoie vers la décision `DEC-nnn` correspondante ;
- les trous de séquence ne sont jamais comblés.
