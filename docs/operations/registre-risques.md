# Registre des risques

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 27 juillet 2026
**Sources reprises :** roadmap §14 et cahier des charges §33

| Origine | Identifiants | Nombre |
|---|---|---:|
| Roadmap §14, déjà numérotés | `ROAD-RSK-001` à `012` | 12 |
| Cahier des charges §33, numérotés par `DEC-430` | `ROAD-RSK-013` à `024` | 12 |
| Constatés pendant la réalisation | `ROAD-RSK-025` à `028` | 4 |
| **Total** | | **28** |

**Prochain identifiant libre : `ROAD-RSK-029`.**

Échelle d'impact reprise des documents sources : `Très élevé`, `Critique`, `Élevé`, `Moyen`,
plus les qualifications spécifiques `Accessibilité` et `Calendrier` employées au cahier §33.

---

# 1. Risques de roadmap — `ROAD-RSK-001` à `012`

Repris sans altération de la roadmap §14.

| ID | Risque | Impact | Mesure | Statut |
|---|---|---|---|---|
| `ROAD-RSK-001` | Le séquencement strict augmente le délai global | Élevé | Lots démontrables, périmètres fermes et validation rapide | Actif |
| `ROAD-RSK-002` | Un lot validé doit être rouvert après découverte tardive | Élevé | Tests d'intégration précoces et analyse d'impact | Actif |
| `ROAD-RSK-003` | Le lot collaborateurs devient trop volumineux | Moyen | Sous-démonstrations internes sans changer la porte de validation | Actif, LOT 5 |
| `ROAD-RSK-004` | Le vrai CSV arrive tardivement | Élevé | Schéma et données fictives préparés dès le LOT 0 | **Mesure en cours** — sous-étape S6 |
| `ROAD-RSK-005` | L’hébergement final retarde l’ouverture | Très élevé | Production temporaire locale et chantier infrastructure parallèle | Actif, lié à `QO-081` et `DEP-001` |
| `ROAD-RSK-006` | La charte officielle tarde | Moyen | Design tokens provisoires remplaçables sans refonte | Actif, lié à `DEP-006` |
| `ROAD-RSK-007` | Les dépendances Microsoft perturbent le MVP | Élevé | Maintien strict en V2 | Actif |
| `ROAD-RSK-008` | Les exigences de performance sont vérifiées trop tard | Élevé | Jeu de 5 000 profils dès le LOT 2 et mesures régulières | Actif |
| `ROAD-RSK-009` | La conformité vidéo reste incomplète | Moyen | Dérogation documentée et support facultatif des sous-titres en V1 | Actif |
| `ROAD-RSK-010` | Jonathan devient un goulot de validation | Élevé | Démonstration structurée et checklist concise à chaque porte | **Mesure en cours** — checklist `G0` prévue en S8 |
| `ROAD-RSK-011` | Un lot technique ne produit aucun résultat visible | Moyen | Démonstration obligatoire même pour le socle | Actif, LOT 1 |
| `ROAD-RSK-012` | Une fonction V1 est ajoutée prématurément | Moyen | Liste d'exclusion MVP et contrôle du backlog | Actif |

---

# 2. Risques majeurs du cahier des charges — `ROAD-RSK-013` à `024`

Repris sans altération du cahier §33. Ces risques n'y portaient **aucun identifiant** :
la décision `DEC-430` leur en attribue un afin de les rendre référençables et suivables.
Leur libellé et leur impact sont inchangés.

| ID | Risque | Impact | Réponse principale | Statut |
|---|---|---|---|---|
| `ROAD-RSK-013` | Fuite entre entités | Critique | Contrôles API, contraintes SQL et tests systématiques | Actif dès le LOT 2 |
| `ROAD-RSK-014` | Perte ou corruption de données | Critique | Transactions, sauvegardes et restauration testée | Actif |
| `ROAD-RSK-015` | Secret intégré au code | Critique | Scan de secrets et configuration externe | **Mesure partielle en place** — `.gitignore` et contrôles manuels ; détection automatique au LOT 1 |
| `ROAD-RSK-016` | Authentification indisponible | Élevé | Healthchecks, fournisseur validé et rollback | Actif dès le LOT 3 |
| `ROAD-RSK-017` | CSV réel exposé | Critique | FileVault, accès restreint, hors Git et sauvegardes chiffrées | **Mesure partielle** — FileVault constaté actif, `*.csv` exclu de Git |
| `ROAD-RSK-018` | Photo publiée sans autorisation | Élevé | Autorisation enregistrée et avatar par défaut | Actif dès le LOT 5 |
| `ROAD-RSK-019` | Mac local indisponible | Élevé | Production temporaire uniquement et migration vers hôte permanent | Actif |
| `ROAD-RSK-020` | Sauvegarde inutilisable | Critique | Test mensuel de restauration | Actif dès le LOT 13 |
| `ROAD-RSK-021` | Migration empêchant le rollback | Critique | Migrations progressives et compatibilité temporaire | **Mesure en place** — règle écrite dans les conventions de versions |
| `ROAD-RSK-022` | Jonathan seul référent | Élevé | Documentation, automatisation et second référent futur | Actif, lié à `QO-094` |
| `ROAD-RSK-023` | Sous-titres absents | Accessibilité | Écart documenté et ajout progressif | Actif |
| `ROAD-RSK-024` | Périmètre complet retardant l’ouverture | Calendrier | Lots séquentiels, sans sacrifice des exigences centrales | Actif |

---

# 3. Risques constatés pendant la réalisation — `ROAD-RSK-025` à `028`

## `ROAD-RSK-025` — Données personnelles et mot de passe en clair dans le prototype conservé

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S1 |
| Description | `docs/prototype/V1.html` contient environ 130 noms de collaborateurs, leurs photos en Base64, leurs clients, et un mot de passe administrateur en clair. Le fichier est conservé sur disque pour historisation par `DEC-420`. |
| Impact | **Critique** en cas de versionnement accidentel : l'historique Git est quasi indélébile. |
| Mesures en place | Exclusion par `.gitignore`, vérifiée par contrôle automatique ; interdiction explicite documentée dans `docs/prototype/README.md` ; contrôle de contenu à chaque commit vérifiant l'absence du mot de passe et de données Base64. |
| Mesure complémentaire | Le mot de passe du prototype doit être considéré comme **compromis** et ne jamais être réutilisé, dans aucun environnement. |
| Statut | **Atténué**, surveillance permanente. Retirer ce fichier de `.gitignore` exigerait une décision explicite et une analyse d'impact RGPD. |
| Écart associé | `ECART-002` |

## `ROAD-RSK-026` — Dépôt et futurs volumes dans iCloud Drive

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S1 |
| Description | Le dépôt réside dans iCloud Drive par `DEC-418`. La synchronisation peut corrompre `.git`, provoquer des conflits, ou évincer des fichiers du disque local. À partir du LOT 1, `node_modules/`, les volumes Docker et les sauvegardes se trouveront dans une arborescence synchronisée. |
| Impact | Élevé sur les LOTS 1, 12 et 13. |
| Mesures en place | `.gitignore` empêche Git de suivre `node_modules/`, `data/`, `volumes/`, `backups/`. **Cela n'empêche pas iCloud de les synchroniser.** |
| **Mesure du 27/07/2026, sous-étape `T0`** | Le périmètre réel du risque est **plus étroit qu'annoncé**. `docker info` rapporte `Docker Root Dir : /var/lib/docker`, à l'intérieur de la machine virtuelle Docker Desktop, dont l'image disque de 28 Go réside sous `~/Library/Containers/com.docker.docker/Data/vms` — **hors iCloud Drive**. Tout **volume Docker nommé est donc déjà hors iCloud**, sans aucune action. Le risque ne portait réellement que sur `node_modules/`, le cache de paquets, et sur d'éventuels bind mounts de données vers le dépôt. |
| Atténuations retenues | `DEC-439` : `node_modules/` et le cache de paquets exclus de la synchronisation iCloud, store `pnpm` placé hors du dossier synchronisé, le dépôt restant dans iCloud. `DEC-447` : volumes nommés exclusivement, **aucun bind mount de donnée d'état** vers `./data`, `./volumes` ou `./backups` — c'est le seul geste qui ramènerait le risque sur les données. |
| Risque résiduel | La synchronisation de `.git` lui-même demeure, inchangée depuis `DEC-418`. Conflits et éviction de fichiers restent possibles sur le dépôt, non sur les données de service. |
| Statut | **Accepté** par `DEC-418`, **atténué** par `DEC-439` et `DEC-447`. `QO-109` close. |

## `ROAD-RSK-027` — Mémoire vive insuffisante pour trois environnements simultanés

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026. **Réévalué le 27 juillet 2026** en sous-étape `T0`, sur mesures directes |
| Description d'origine | La machine dispose de **16 Gio** de mémoire vive. Chaque environnement compte environ huit services : PostgreSQL, Redis, MinIO, Caddy, API, worker, web, Mailpit. Trois environnements séparés sont exigés — développement, recette, production temporaire — soit environ 24 conteneurs si tous tournaient ensemble. |
| **Correction des prémisses** | Les deux prémisses d'origine étaient inexactes, dans le sens **défavorable**. **Premièrement**, le plafond réel n'est pas 16 Gio : `docker info` rapporte **7,75 Gio** alloués à la machine virtuelle Docker Desktop, soit la moitié de la mémoire physique. **Deuxièmement**, ce budget n'est pas libre : un projet tiers sans rapport avec eXalt, `observatoire-ecom-studio`, y exécutait **5 conteneurs depuis 5 jours** pour **~1,93 Gio**, soit **25 % du budget Docker**, dont 1,77 Gio pour son seul worker. La marge réellement disponible pour les 8 services du LOT 1 était donc d'environ **5,8 Gio**, et non de 16. |
| Impact | Élevé sur les LOTS 1, 12 et 13 : lenteur, échecs de démarrage, tests de charge non représentatifs. La coexistence de deux stacks complètes, envisagée en sous-étape `T8`, est **hors d'atteinte** sans intervention. |
| Mesures | `DEC-440` : les trois environnements ne sont jamais exécutés simultanément ; limites mémoire fixées par service ; mesure de performance réservée à un environnement exécuté seul ; **`observatoire-ecom-studio` arrêté pendant la durée du LOT 1**, ce qui porte le budget disponible à ~7,7 Gio pour une stack. La sous-étape `T8` prouve la **séparation** des environnements par démarrages **successifs** : le cahier §22.2 exige des ressources distinctes, il n'exige nulle part la simultanéité. |
| Statut | **Actif, traité** par `DEC-440`. Alimente `QO-085` d'un élément de réponse chiffré. |

## `ROAD-RSK-028` — Statut ambigu de la source de vérité prévalente

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Description | Le cahier des charges, qui prévaut sur les quatre annexes validées, portait le statut « soumis à validation finale ». |
| Impact | Moyen : une source de vérité au statut incertain fragilise tout arbitrage qui s'en réclame. |
| Mesure | Validation explicite enregistrée sans modification du fichier. |
| Statut | **Clos** par `DEC-423`, le 27 juillet 2026. |
| Écart associé | `ECART-003` |

---

# 4. Règles de tenue

- un risque clos conserve son identifiant, son texte et la mesure qui l'a traité ;
- un risque accepté reste actif au registre avec la mention `Accepté` et la décision associée ;
- les libellés repris des documents validés ne sont **jamais** reformulés ;
- un risque de sécurité, d'intégrité, d'isolation ou d'accessibilité essentielle qui se
  matérialise devient une anomalie prioritaire sur le lot en cours (`ARB-BACK-005`) ;
- chaque porte de validation revoit l'état des risques du lot concerné.
