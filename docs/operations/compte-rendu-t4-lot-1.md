# Compte rendu — sous-étape `T4` du LOT 1

**Exécutée le :** 28 juillet 2026
**Objet :** journalisation JSON corrélée, API et worker
**Story :** `MVP-L01-US004`, issue [#5](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/5)
**Fondement :** cahier §28.1 (format), §28.2 (confidentialité), §28.3 (conservation)
**Décisions produites :** `DEC-466` à `DEC-469`

---

## 1. Critère d'acceptation, et ce qui le prouve

> « Chaque requête et chaque job possède un `correlation_id` ; aucun secret n'est journalisé ;
> la rotation est configurable. » — backlog, littéral

| Volet | Preuve | Résultat |
|---|---|---|
| Chaque **requête** porte un `correlation_id` | Journaux réels du conteneur, trace fournie reprise et trace absente engendrée | **vérifié** |
| Chaque **job** porte un `correlation_id` | Intergiciel Dramatiq : l'identifiant voyage **dans le message**, est relu côté worker, et effacé après | **vérifié** |
| Aucun secret journalisé | **3 barrières** de masquage, 30 tests dédiés, chacun avec son témoin | **vérifié** |
| Rotation configurable | Pilote `json-file` avec `max-size` et `max-file` sur les **8 services** | **8/8** |

Sortie réelle, à travers Caddy :

```text
{"date":"...","niveau":"info","service":"api","environnement":"development",
 "version":"0.0.0-dev","identifiant_correlation":"trace-preuve-t4",
 "route":"GET /api/v1/","duree_ms":3,"resultat":"succes","code_erreur":null,
 "message":"requete servie","contexte":{"statut_http":200}}
```

Les **dix champs** du §28.1 sont présents, toujours, même à `null` — vérifié sur un journal
réel de conteneur, pas seulement en test.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `packages/observabilite/` | **Nouveau paquet Python partagé** : format JSON, masquage, corrélation |
| `observabilite/journalisation.py` | Formateur des 10 champs du §28.1, configuration du journal |
| `observabilite/masquage.py` | Les **3 barrières** du §28.2 |
| `observabilite/correlation.py` | Porteur commun. A déménagé depuis `apps/api/app/shared/` |
| `apps/api/app/shared/journal.py` | Journal des requêtes : route de gabarit, durée, résultat, code |
| `apps/worker/worker/journal.py` | Intergiciel Dramatiq : corrélation et journal des jobs |
| `infra/compose/` | Rotation `json-file` sur les 8 services |
| `.env.example` | `LOG_MAX_SIZE`, `LOG_MAX_FILES` |

**131 tests**, dont **30 sur le masquage et le format**.

### Pourquoi un paquet partagé — `DEC-466`

Le filtre de masquage doit servir à l'API **et** au worker. Le dupliquer aurait été la pire
option : deux filtres finissent par diverger, et le jour où l'un oublie un motif, la fuite est
silencieuse. Une seule implémentation, deux consommateurs, une seule suite de tests.

`packages/` est l'un des sept répertoires du cahier §15.3, qui ne le réserve pas au JavaScript.
`pnpm-workspace.yaml` liste ses membres explicitement : ce paquet Python n'y entre pas par
accident.

---

## 3. Les trois barrières du masquage — §28.2

> « Aucune donnée sensible, aucun secret, aucun jeton, aucun magic link complet, aucun CSV
> complet et aucun corps complet d'e-mail. »

| Barrière | Ce qu'elle attrape | Ce qu'elle laisse passer |
|---|---|---|
| **Nom de la clé** | `password`, `APP_SECRET_KEY`, `token`, `cookie`, `magic_link`… masqués sans même examiner la valeur | Un secret recopié dans un champ nommé `message` |
| **Forme de la valeur** | Clé PEM, jeton GitHub, clé AWS, JWT, URL de connexion, en-tête `Bearer`, magic link — même dans un champ anodin | Un secret court et sans forme reconnaissable |
| **Troncature** | Toute valeur de plus de 512 caractères. C'est la seule parade générique contre le CSV complet et le corps d'e-mail complet, qu'aucun motif ne reconnaît | — |

**Aucune ne suffit seule, et le module le dit.** Il ne promet pas de deviner un secret à la fois
court, sans forme reconnaissable et dans un champ au nom anodin : cela relève de la revue de
code. Le filtre réduit la surface, il ne la supprime pas.

### Ce qui n'est JAMAIS journalisé — `DEC-469`

| Élément | Motif |
|---|---|
| La **chaîne de requête** | Un magic link du LOT 3 y passera : `?token=…`. Ne pas l'écrire du tout est la parade la plus sûre |
| Les **arguments d'un job** | Ils porteront une adresse e-mail, un identifiant de personne, un jeton. Seul leur **nombre** est journalisé |
| Les **traces d'exception** | Une trace contient les variables locales, donc des secrets. Seul le **type** sort ; le diagnostic passe par la corrélation |
| Le **journal d'accès d'uvicorn** | Il double la ligne applicative sans aucun des dix champs, journalise les sondes de santé toutes les 10 s — **8 640 lignes par jour et par service** — et écrit le chemin brut avec sa chaîne de requête |
| Les journaux de `httpx`, `botocore`, `urllib3` | Ils écrivent des URL complètes, dont des URL signées portant des paramètres d'authentification |

---

## 4. La rotation — `DEC-467`, et ce qui reste découvert

Le §28.3 exige « rotation et limite de taille obligatoires ». Les processus écrivent sur
**stdout** et n'ouvrent aucun fichier : c'est le pilote de journalisation de Docker qui collecte
et rotate, avec `max-size` et `max-file`, sur les huit services.

Écrire dans un fichier à l'intérieur d'un conteneur aurait produit une donnée d'état que
`DEC-447` interdit de sortir par un bind mount, et que personne n'aurait rotatée.

> **Ce qui n'est pas couvert, et il faut le dire.** Le §28.3 demande aussi une conservation de
> **30 jours** pour les logs techniques. Le pilote `json-file` borne par la **taille**, jamais par
> la durée : la conservation calendaire suppose une collecte centralisée, qui appartient au
> **LOT 13**. `LOG_RETENTION_DAYS` porte l'intention et sera consommée là. **`QO-113` ouverte.**

---

## 5. Défauts détectés pendant `T4`

Cinq défauts. Le premier est le plus important du lot jusqu'ici.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T4-1` | Le motif d'URL de connexion exigeait un nom d'utilisateur : `\|[^\s:/@]+:[^\s@]+@`. Il laissait donc passer **`redis://:motdepasse@redis:6379/0`** — **exactement le format produit par `Parametres.url_redis()`**, donc le secret le plus susceptible d'apparaître dans ces journaux | **Trou de sécurité dans le filtre.** Détecté par **mon propre test**, qui énumérait les formes d'URL du projet plutôt que des exemples génériques | Utilisateur rendu optionnel. Six cas vérifiés, dont trois qui doivent **passer** — une URL sans identifiants doit rester lisible |
| `T4-2` | Le build du worker échouait : `uv sync` répondait « Failed to determine installation plan ». Le workspace avait un troisième membre que les `Dockerfile` ne copiaient pas | Livrable incomplet | `COPY packages/observabilite` ajouté aux deux images |
| `T4-3` | J'ai lu `build code=0` alors que le build venait d'échouer : le code lu était celui du `grep` en fin de tuyau. La stack est remontée sur les **anciennes images**, et affichait « 8 services sains » | **Contrôle menteur.** Quatrième occurrence du piège du tuyau dans ce lot | Sortie capturée en variable, code lu directement, et arrêt immédiat si non nul |
| `T4-4` | `uvicorn.access` doublait chaque ligne de requête, sondes de santé comprises, avec le chemin brut | Bruit et risque `§28.2` | Réduit aux avertissements. Mesuré sur les journaux réels, pas supposé |
| `T4-5` | Un 404 était journalisé `resultat=succes` à côté de `code_erreur=http_404` | **Contradiction à la lecture**, et agrégation ambiguë : `succes` comptait-il les refus ? | Trois résultats : `succes` 2xx-3xx, `refus` 4xx, `echec` 5xx. Seul `echec` justifie un niveau `error` — sinon une adresse mal tapée fait sonner une alerte |

### 5.1 Ce que `T4-1` enseigne

Le trou n'a pas été trouvé par relecture, mais parce que le test énumérait **les formes d'URL
réellement produites par ce projet** — `postgresql://user:pass@`, `redis://:pass@` — au lieu
d'exemples génériques tirés d'une documentation. Un test écrit à partir du code qu'il protège
trouve ce qu'une relecture ne voit pas.

`T4-3` est la **quatrième** occurrence du piège du tuyau dans ce seul lot, après `T0-1`, `T2-4`
et `T3-6`. Le remède est mécanique et devrait être systématique : **capturer la sortie dans une
variable, lire le code de sortie, ne jamais conclure depuis un tuyau.**

---

## 6. État à la sortie de `T4`

| | |
|---|---|
| Sous-étape | **`T4` terminée.** Story `MVP-L01-US004` prête pour validation |
| Décisions | `DEC-466` à `DEC-469`. Prochaine libre : **`DEC-470`** |
| Questions | **`QO-113` ouverte** — conservation calendaire des journaux, au LOT 13. Prochaine libre : `QO-114` |
| Écarts | Aucun ouvert. Prochain libre : `ECART-020` |
| Risques | Aucun ouvert. Prochain libre : `ROAD-RSK-031` |
| Tests | **131** — 123 unitaires, 8 d'intégration |
| `make check` · `stack-check` · `api-check` · `test-integration` | Tous **code 0** |
| Sous-étape suivante | **`T5`** — frontend Vite, page de statut, stories `MVP-L01-US002` et `US003`, issues `#3` et `#4` |

**Ce qui attend `T5`.** La page de statut consommera `/health/ready` et `/health/version`, déjà
livrés. Elle s'affichera dans un navigateur sur `app.onboarding.localhost` — et **c'est là que
l'absence d'approbation de la racine Caddy deviendra visible**, sous la forme d'un avertissement
de certificat. L'approbation est l'action de Jonathan : elle demande son mot de passe.
