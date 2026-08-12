# Compte rendu — sous-étape `T9` du LOT 1

**Exécutée le :** 29 juillet 2026
**Objet :** documentation d'exploitation locale — lancement, arrêt, réinitialisation, diagnostic
**Story :** `MVP-L01-US008`, issue [#9](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/9)
**Fondement :** cahier §22.2, §22.3 ; backlog `MVP-L01-US008` ; fiche §3 et §4.2
**Décisions produites :** `DEC-489`, `DEC-490` · **Écart ouvert et clos :** `ECART-024`

---

## 1. Le critère, et ce qui le prouve

> « Les procédures fonctionnent **depuis une machine propre** et identifient les ports, volumes et
> commandes utiles. » — backlog, littéral

**Le mot qui commande tout est « fonctionnent ».** Une procédure écrite de mémoire ne satisfait rien.
Chaque commande du document a donc été **exécutée**, et les sorties citées sont réelles.

| Volet du critère | Preuve | Résultat |
|---|---|---|
| Les procédures fonctionnent | les **13** commandes `make` du document, lancées une par une | **13 sur 13, code 0** |
| **Depuis une machine propre** | recette détruite — 0 volume, 0 conteneur, réseau supprimé — **et les 3 images retirées du cache local** | remontée en **34 s**, 8/8 sains |
| Les ports identifiés | **dérivés** par `make ports`, jamais recopiés | **14** publications, 7 + 7, bandes disjointes |
| Les volumes identifiés | **dérivés** par `docker volume ls --filter label=…` | **12** volumes, 6 + 6, aucun partagé |
| Les commandes utiles identifiées | `make help` désigné **source de vérité**, et 8 symptômes réels documentés | 50 cibles |

**Le démarrage à froid est véritable, et c'est le point le plus important.** `T6` et `T8` avaient
éprouvé une machine « propre » en supprimant **un** volume. `T9` a supprimé **tout** ce que la recette
possédait, images comprises : une machine qui n'aurait jamais vu ce projet est dans cet état exact.

Arbitrage de Jonathan du 29/07/2026 : détruire la recette, **pas** le développement. Motif : la
recette ne porte aucune donnée et son autorité de certification n'est pas approuvée dans le
trousseau ; détruire `dev` aurait coûté à Jonathan une réapprobation avec son mot de passe.

**Le développement est resté intact, vérifié après la destruction :** 6 volumes, et sa racine
toujours approuvée — `security verify-cert` code 0.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `docs/operations/exploitation-locale.md` | **Nouveau.** Le nom est celui que la fiche §4.2 attendait |
| `Makefile` | `destroy` **mesure** au lieu d'affirmer ; `web-check` paramétrée, origine **dérivée** |
| `infra/scripts/verifier-page-statut.sh` | **identifie la cible servie** et applique ses contrôles |
| Registres, index, fiche, `README`, `CLAUDE.md` | mis à jour dans la même pull request |

### 2.1 Ce que le document contient, et ce qu'il ne duplique pas

Le `README` porte déjà sept lignes pour démarrer : il reste la porte d'entrée. Le document
d'exploitation va au fond — arrêt, réinitialisation, diagnostic — et il désigne **`make help` comme
source de vérité** des commandes plutôt que d'en recopier la liste, qui vieillirait.

**Trois exceptions sont nommées explicitement** plutôt que laissées croire vérifiées : `make logs`
suit en continu et n'a donc pas de code de sortie, l'approbation d'une racine dans le trousseau est
l'action de Jonathan, et la relance du projet Docker tiers relève de sa décision.

---

## 3. Ce qui n'est PAS couvert, et il faut le dire

1. **La production temporaire locale** — LOT 13. Aucun `onboarding-prod-local` n'existe.
2. **La sauvegarde et la restauration.** Aucune procédure. LOT 13.
3. **La conservation calendaire des journaux** — `json-file` borne par la taille. `QO-113`.
4. **Le déploiement automatique de la recette** — pas d'exécuteur auto-hébergé, mesuré en `T7`.
5. **`ROAD-RSK-034`** est documenté comme un **résiduel accepté**, pas comme un problème résolu.
6. **Le document décrit l'état du commit `84dd33d`.** Il porte sa date de dernière vérification, et
   c'est délibéré : `make help` et les commandes de dérivation restent justes quand les nombres
   bougent, les tableaux non.

---

## 4. Contrôles exécutés, et leurs témoins

### 4.1 Le démarrage à froid, mesuré

```text
avant   volumes 0   conteneurs 0   reseau 0   images GHCR locales 0
apres   make up-recette -> code 0 en 34 s
        8 images tirees, bucket cree, Caddy recharge
        --> les 8 services sont sains
        --> 7 publications, toutes limitees a la boucle locale
```

Puis la migration, qui **n'est pas appliquée** par le démarrage :

```text
make migrate-status ENVIRONNEMENT=recette   ->  code 0, sortie VIDE
make migrate        ENVIRONNEMENT=recette   ->  code 0
make migrate-status ENVIRONNEMENT=recette   ->  0001 (head)
```

### 4.2 Trois cibles jamais exercées, désormais éprouvées

**Le défaut `T8-7` a enseigné qu'une cible non lancée n'est pas éprouvée.** Trois l'étaient encore.

| Cible | Pourquoi elle n'avait jamais tourné | Résultat |
|---|---|---|
| `make destroy` | destructive et **interactive** — jamais lancée depuis son paramétrage en `T8` | **2 défauts trouvés**, voir §5 |
| `make caddy-recreate` | paramétrée en `T8`, jamais appelée sur la recette | code 0 sur les **deux** environnements |
| `make web-check` sur la recette | l'origine était en dur sur le développement | **2 contrôles sur 6 en échec** — voir §5 |

### 4.3 Témoins — 8, tous concluants

| Maillon | Défaut injecté ou action réelle | Résultat |
|---|---|---|
| `destroy`, confirmation | réponse `oui` au lieu de `DETRUIRE` | **annulé**, code non nul, **6 volumes intacts** |
| `destroy`, nom du projet | appelée sur la recette | le message nomme **`onboarding-recette`** |
| `destroy`, trousseau | la **même** cible sur `dev` puis sur la recette | messages **différents**, chacun conforme à la mesure |
| Contrôle de page, cible dev | `https://app.onboarding.localhost` | `cible developpement`, `/src/main.tsx` en `text/javascript` |
| Contrôle de page, cible recette | `https://app.recette.onboarding.localhost:8443` | `cible execution`, `/assets/index-BVCc0Fm0.js` |
| Contrôle de page, **négatif** | l'hôte de l'**API**, qui ne sert pas la page | **2 échecs sur 6** : « ni racine React, ni cible reconnue » |
| Environnement fautif | `ENVIRONNEMENT=recete` | échec **à la lecture du `Makefile`**, noms valides **dérivés du disque** |
| Racines de certification | comparaison des deux empreintes | **distinctes** : `c9a952a9…` contre `fb8fbc2d…` |

### 4.4 Non-régression

Les onze contrôles de `dev` et les cinq de la recette, tous à **code 0**. **166 tests inchangés.**

Mesure des deux stacks simultanées, cohérente avec `T8` : **832,2 Mio pour 16 services, 10,5 %** du
budget — 533,8 Mio en développement, 298,3 Mio en recette.

---

## 5. Défauts détectés pendant `T9`

**Trois défauts. Les trois dans mon propre travail** — deux dans des contrôles hérités de `T2` et
`T5`, un dans ma méthode de mesure.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T9-1` | **`make destroy` annonçait une conséquence inexistante.** Son message avertissait, quel que soit l'environnement, que détruire `caddy-data` obligerait à réapprouver la racine dans le trousseau. Mesure : `security verify-cert` rend **0 pour `dev`** et **1 pour la recette**, dont la racine n'a **jamais** été approuvée | **Une affirmation fausse sur la cible la plus destructive du dépôt**, et son effet est pervers : un avertissement qui annonce une conséquence inexistante apprend à passer outre, si bien que le jour où il porte sur `dev`, où la conséquence est réelle, il n'est plus lu. Écrit en `T2` quand il n'existait qu'un environnement | La cible **mesure** désormais : elle extrait la racine du conteneur, interroge le trousseau, et dit ce qu'elle a mesuré — ou **« indéterminé »** quand elle ne peut pas mesurer, plutôt que de trancher. Elle **énumère** aussi les volumes réellement présents. `DEC-489`. Témoin dans les deux sens : le message diffère réellement entre les deux environnements |
| `T9-2` | **Le contrôle de page exigeait le comportement du serveur Vite.** Il demandait `/src/main.tsx` dans l'index servi ; l'artefact bâti de la recette référence `/assets/index-<empreinte>.js`, et `/src/main.tsx` n'y existe pas **par construction** (`DEC-479`). Mesuré : **2 contrôles sur 6 en échec sur une recette parfaitement saine** | **Un contrôle qui exige plus que l'environnement ne fournit** — exactement la classe du §7.20 de la passation, née en `T8` sur l'isolement réseau. Et classe `T6-4`/`T7-4` : un contrôle qui échoue pour une raison étrangère à ce qu'il mesure finit désactivé | Le contrôle **identifie la cible servie**, exige qu'elle soit l'une des **deux** formes connues, puis applique les contrôles de cette forme — et **échoue** s'il n'en reconnaît aucune, sans quoi un index vide passerait pour un cas non prévu. `DEC-490`. Trois témoins : les deux cibles réelles, et une origine qui ne sert pas la page |
| `T9-3` | **J'ai conclu qu'un workflow ne s'était pas déclenché alors qu'il ne s'était pas déclenché ENCORE.** Dix sondages de `gh run list --branch` sur trois minutes rendaient 0 ; j'ai annoncé à Jonathan que la CI n'avait pas démarré. La sonde `gh api repos/…/commits/<sha>/check-runs` montrait pourtant **2 contrôles `in_progress`**, et le run est apparu ensuite | **Une conclusion tirée d'une sonde qui ne couvrait pas ce que j'affirmais.** Ma sonde était juste ; ma conclusion non — « absent » et « pas encore là » sont deux choses différentes, et seule la seconde était vraie | Rectifié auprès de Jonathan dans le message suivant. **Et versé au document d'exploitation** comme fait opérationnel : `gh run list --branch` peut légitimement ne rien rendre pendant plusieurs minutes après l'ouverture d'une pull request ; la sonde qui répond tout de suite est celle des check-runs sur l'empreinte de tête |

### 5.1 Ce que ces trois défauts enseignent

**`T9-1` et `T9-2` partagent une propriété, et elle n'est pas la négligence.** Les deux contrôles
étaient **justes quand ils ont été écrits** : `T2` et `T5` ne connaissaient qu'un environnement. C'est
`T8`, en créant le second, qui les a rendus faux — sans que rien ne le signale.

> **Ce que `T9` ajoute à la règle du lot :** quand une sous-étape ajoute un environnement, une cible
> ou une plateforme, **relis les contrôles qui n'en connaissaient qu'un**. Un contrôle ne devient pas
> faux tout seul ; il le devient quand le monde change autour de lui, et ce changement, c'est nous
> qui le faisons.

**Et une leçon opérationnelle qui a valeur générale, tirée de `T9-3` :** avant d'annoncer qu'une
chose est absente, demande-toi si ta sonde peut distinguer **absent** de **pas encore là**. C'est la
même famille que `T2-1`, où un 429 masqué avait été lu comme une image inexistante, et que `T2-5`, où
un Mailpit vide et un volume effacé rendaient la même valeur.

---

## 6. Recommandations pour la suite

1. **`T10`** — design system et contrat API, story `US007`, **`P1`**. C'est la seule story de priorité
   `P1` du lot : elle peut faire l'objet d'un arbitrage de report sans empêcher la porte `G1`.
2. **`T11`** doit vérifier que les nombres de ce document et de la passation sont **toujours vrais**,
   par les commandes de dérivation, et non les recopier.
3. **Ne pas ajouter de contrôle de recette à l'intégration continue** sans traiter la résolution des
   sous-domaines `.localhost`, que Linux ne fait pas.
4. **`ROAD-RSK-034`** est à réévaluer avant le LOT 13.
5. **Le pointeur d'images de la recette vieillit.** Il est épinglé sur `1060ad6` ; `make images-pin`
   le rafraîchit sans commit, le figer durablement en demande un.

---

## 7. État à la sortie de `T9`

| | |
|---|---|
| Sous-étape | **`T9` terminée.** Story `MVP-L01-US008` prête pour validation, issue `#9` **à refermer à la main** |
| Décisions | `DEC-489`, `DEC-490`. Prochaine libre : **`DEC-491`** |
| Écarts | **`ECART-024` ouvert et clos.** 24 au total, 5 ouverts. Prochain libre : **`ECART-025`** |
| Risques | Aucun nouveau. Prochain libre : `ROAD-RSK-035` |
| Questions | Aucune nouvelle. 33 ouvertes sur 38. Prochaine libre : `QO-115` |
| Tests | **166** — inchangé. `T9` n'ajoute pas de test unitaire : ses preuves sont des procédures exécutées |
| Cibles `Makefile` | **50** — inchangé |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, `T6`, `T8`, **et depuis une machine réellement propre en `T9`** |
| ☑ | Les images multiarchitectures sont construites | `T7`, natif sur les deux depuis `T8` |
| ☑ | Aucun secret réel n'est présent | vérifié automatiquement depuis `T6`. **`T9` n'a créé aucun secret** |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, **et sur une base créée de zéro en `T9`** |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4` |
| ☑ | La CI bloque une erreur de lint, de test et de secret | `T6`, prouvé trois fois |
| ☐ | Jonathan valide le socle | `T11` |

**Et le critère du backlog §12 qui devenait applicable :** « la documentation minimale d'exploitation
existe et fonctionne depuis une machine propre » — **satisfait, et prouvé par exécution.**

### Ce qui attend `T10`

Design system minimal et contrat API partagé, story `MVP-L01-US007`, issue `#8`. **Seule story `P1`
du lot.** Critère : « tokens et composants de base sans dépendance visuelle arbitraire ; contrat
généré et partagé ». Les répertoires `packages/ui` et `packages/contracts` existent depuis `T1` avec
un test chacun ; ils ne portent aucun contenu.
