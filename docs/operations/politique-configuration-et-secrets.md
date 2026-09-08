# Politique de configuration et de secrets

**Produit en :** LOT 0, sous-étape S5 — story `MVP-L00-US007`
**Fondement :** cahier des charges §20.3, §22.2, §28.2 ; roadmap §2.3 ; backlog §12
**Modèle associé :** [`.env.example`](../../.env.example) version 0.1

---

## 1. Principe

**La configuration passe exclusivement par des variables d'environnement.** Aucune valeur de
configuration n'est codée en dur, ni dans le backend, ni dans le frontend, ni dans une image
Docker.

| Règle | Statut |
|---|---|
| `.env` local **jamais** versionné | Non négociable — cahier §20.3 |
| `.env.example` versionné, **sans aucun secret** | Non négociable — cahier §20.3 |
| Validation de la configuration au démarrage | Non négociable — cahier §20.3 |
| Refus de démarrer en production si un secret est absent ou si une option de développement est active | Non négociable — cahier §20.3 |
| Aucun secret dans Git | Non négociable — roadmap §2.3 |
| Aucun secret dans les logs, l'audit ou un message de commit | Non négociable — cahier §28.2, §10.11 |

Le versionnement d'un secret **empêche la validation de toute porte** (backlog §12).

---

## 2. Statut du modèle : **version 1.6, 84 variables** — `ECART-006` clos

`.env.example` a été livré en **version 0.1** au LOT 0, avec la seule limitation que le contenu
exhaustif dépendait du LOT 1 : `ECART-006`, **clos en `T3` du LOT 1**.

**Il est aujourd'hui en version 1.6 et porte 84 variables**, chacune annotée de sa source
documentaire et du lot où elle devient effective. Les compter, jamais les recopier :

```bash
grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example                # 84 variables
grep -cE '^[A-Z_][A-Z0-9_]*=CHANGE_ME' .env.example       # 9 encore a renseigner
```

> **`make env` NE RÉCONCILIE RIEN, et c'est la cause d'un défaut à chaque lot.** Il ne touche
> **jamais** un `.env` existant — c'est voulu, il porte des secrets engendrés — donc une variable
> ajoutée au modèle **après** la première création n'y arrive **jamais**. `make env-check` est la
> parade : il **nomme** les manquantes, et il est dans `make check`.
>
> Mesuré : le `.env` de cette machine comptait **74 affectations contre 78** en `T7` du LOT 1 —
> `APP_REVISION`, `LOG_MAX_SIZE` et `LOG_MAX_FILES` y manquaient depuis `T3` et `T4`. Le fichier
> déclarait aussi **`APP_REVISION` deux fois**, en blocs identiques : dans un fichier de
> configuration, **c'est la dernière qui gagne, en silence**, le jour où elles divergent.
> `ECART-022`.

**Deux valeurs `CHANGE_ME` ne sont pas engendrées, et ce n'est pas un oubli** :
`IMPORT_SOURCE_RETENTION_DAYS` attend `QO-100` au LOT 9, `UPTIME_KUMA_PUSH_URL` attend le LOT 13.
Les sept autres le sont par `make env`, sur 48 caractères (`DEC-461`).

**Et cinq variables ne sont consommées par personne** — les seuils du cahier §20.2, `ECART-034`.
Elles portent l'annotation qui le dit, plutôt que de laisser croire qu'elles agissent.

### Les trois rôles PostgreSQL, et employer le mauvais coûte une heure

Depuis `T1` du LOT 3 (`DEC-520`), quatre variables décrivent **deux comptes de moindre privilège**
en plus du superutilisateur :

| Variables | Compte | Ce qu'il peut |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `onboarding_app` | **tout** — `initdb` et `make roles-provision` seulement |
| `POSTGRES_MIGRATIONS_USER` / `_PASSWORD` | `onboarding_migrations` | possède le schéma, crée et modifie les tables |
| `POSTGRES_RUNTIME_USER` / `_PASSWORD` | `onboarding_runtime` | **lire et écrire des LIGNES** — rien de plus |

L'API, le worker et **tous** les tests d'intégration emploient le troisième. Ce qu'il refuse est
mesuré et testé : `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`, `CREATE ROLE`, et **`TRUNCATE`** —
un DDL déguisé qui contourne les déclencheurs `ON DELETE`.

Une variable ne doit **jamais** être ajoutée à ce fichier sans source validée. Si un besoin de
configuration apparaît sans décision correspondante, c'est une décision à prendre, pas une
variable à inventer.

---

## 3. Les trois environnements

Chaque environnement possède, sans aucune valeur partagée (cahier §22.2) :

| Élément | Développement | Recette | Production locale |
|---|---|---|---|
| Fichier | `.env` | `.env.recette` | `.env.prod-local` |
| Projet Docker | `onboarding-dev` | `onboarding-recette` | `onboarding-prod-local` |
| Base PostgreSQL | distincte | distincte | distincte |
| Bucket MinIO | distinct | distinct | distinct |
| Volumes | distincts | distincts | distincts |
| Réseau | distinct | distinct | distinct |
| Ports hôte | distincts | distincts | distincts |
| Secrets | **distincts** | **distincts** | **distincts** |
| `APP_ENV` | `development` | `recette` | `production` |
| E-mails | Mailpit | **Mailpit exclusivement** | fournisseur réel |

Les trois fichiers sont exclus de Git par le motif `.env.*`, la seule exception réinjectée
étant `.env.example`. Vérification :

```bash
git check-ignore -v .env .env.recette .env.prod-local
```

**Aucun secret n'est jamais réutilisé d'un environnement à l'autre.** Une clé de développement
qui se retrouverait en production annulerait la séparation des environnements.

---

## 4. Ce qui est un secret

| Catégorie | Exemples de variables |
|---|---|
| Clés applicatives | `APP_SECRET_KEY` |
| Mots de passe de service | `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ROOT_PASSWORD`, `SMTP_PASSWORD` |
| Identifiants d'accès | `MINIO_ROOT_USER`, `SMTP_USER` |
| URLs porteuses d'un jeton | `UPTIME_KUMA_PUSH_URL` |
| Jetons de comptes de service | générés en base, jamais en fichier de configuration |
| Mots de passe administrateurs | **jamais** en configuration : hachés en base, table `admin_password_credential` |

### 4.1 Variables exposées au navigateur

Toute variable préfixée `VITE_` est **incluse dans le bundle JavaScript** et devient publique.

**Aucun secret ne doit jamais porter le préfixe `VITE_`.** Cette règle est absolue et sans
exception. Un secret placé dans une variable `VITE_` est un secret publié.

---

## 5. Génération des secrets

```bash
# Cle applicative, 48 octets aleatoires
openssl rand -base64 48

# Mot de passe de service, 32 octets sans caractere ambigu
openssl rand -base64 32 | tr -d '/+=' | head -c 32
```

Exigences :

- longueur minimale de 32 caractères pour un mot de passe de service ;
- longueur minimale de 48 octets pour `APP_SECRET_KEY` ;
- aucune valeur devinable, aucune référence au projet, à eXalt, à une date ou à un prénom ;
- aucune réutilisation entre environnements ;
- aucune réutilisation d'un secret ayant existé dans le prototype historique — le mot de
  passe qu'il contient est **compromis par construction** (`ROAD-RSK-025`).

---

## 6. Garde-fous de démarrage

Le cahier des charges §20.3 exige un refus de démarrage. **Les onze contrôles sont implémentés et
testés depuis `T3` du LOT 1**, dans `apps/api/app/configuration/settings.py` : quatre dans tous les
environnements, sept en production seule.

> **Le message nomme la variable, JAMAIS sa valeur**, et un test l'éprouve. Un garde-fou qui
> afficherait la valeur fautive écrirait un secret dans les journaux au moment précis où il
> prétend protéger la configuration.
>
> **Chaque garde-fou a DEUX tests** : celui qui l'enfreint, et le **témoin** qui le respecte. Les
> sept contrôles de production sont éprouvés **en forçant `APP_ENV=production`**, plus un test qui
> prouve qu'ils **ne s'appliquent pas** en développement.
>
> **Et deux d'entre eux ne pouvaient pas se déclencher** : `SESSION_COOKIE_SECURE` et
> `CSRF_PROTECTION_ENABLED` n'étaient **pas transmises au conteneur** — zéro occurrence, mesuré en
> `T6` du LOT 3. Une variable déclarée n'est pas une variable transmise. Le garde-fou porte sur ce
> que l'API **déclare** (`DEC-464`), et `make env-check` sur ce que le fichier contient ; **aucun
> des deux ne vérifiait la frontière de processus**.

### 6.1 Dans tous les environnements

| Contrôle | Effet si en échec |
|---|---|
| Toute variable obligatoire est présente | Refus de démarrer, message explicite nommant la variable |
| Aucune variable ne vaut encore `CHANGE_ME_*` | Refus de démarrer |
| Les valeurs typées sont valides — entiers, booléens, énumérations | Refus de démarrer |
| `LOG_FORMAT=json` | Refus de démarrer |

### 6.2 Uniquement lorsque `APP_ENV=production`

| Contrôle | Motif |
|---|---|
| `APP_SECRET_KEY` présente, suffisamment longue, distincte des autres environnements | Sécurité des sessions |
| `EMAIL_PROVIDER` **différent** de `mailpit` | Aucun contournement de l'envoi réel |
| `API_DOCS_ENABLED=false` | Documentation interactive interdite en production, cahier §18.1 |
| `SESSION_COOKIE_SECURE=true` | Cahier §7.4 |
| `CSRF_PROTECTION_ENABLED=true` | Cahier §7.4, §20.1 |
| `DB_AUTO_CREATE=false` | Aucune création automatique de table, cahier §16.2 |
| `PUBLIC_BASE_URL` en `https://` | Cookie `Secure` inutilisable sinon |

Le message d'erreur doit nommer la variable fautive **sans jamais afficher sa valeur**.

### 6.3 Recette

`EMAIL_PROVIDER` doit valoir `mailpit`. La recette ne doit envoyer **aucun e-mail réel**
(cahier §16.5, critère de sortie du LOT 13). Un fournisseur réel configuré en recette est un
défaut bloquant.

---

## 7. Valeurs qui ne sont pas librement modifiables

Certaines variables portent des valeurs issues de décisions validées. Les modifier revient à
changer une exigence, ce qui exige un arbitrage explicite et tracé.

| Variable | Valeur validée | Source |
|---|---|---|
| `MAGIC_LINK_TTL_MINUTES` | 15 | Cahier §7.2 |
| `SESSION_IDLE_DAYS` | 7 | Cahier §7.4 |
| `SESSION_ABSOLUTE_DAYS` | 30 | Cahier §7.4 |
| `ONBOARDING_TASK_UNDO_MINUTES` | 5 | `ARB-DROIT-001`, `RIGHTS-021` |
| `RECENT_ARRIVAL_MONTHS` | 1 | Matrice §7.2 |
| `AUDIT_RETENTION_DAYS` | 365 | Cahier §10.11 |
| `DEPARTURE_ARCHIVE_MONTHS` | 3 | Cahier §21.3 |
| `MEDIA_MAX_PHOTO_MB` / `IMAGE` / `VIDEO_MB` / `VIDEO_MINUTES` | 10 / 20 / 1024 / 20 | Cahier §19.3 |
| `API_PAGE_SIZE_DEFAULT` / `MAX` | 25 / 100 | Cahier §18.2 |
| `DRAMATIQ_QUEUES` | les 7 files validées | Cahier §16.4 |
| Seuils de sécurité, section 8 du modèle | 5/15, 10, 50, 5 | Cahier §20.2 |

Ces valeurs sont paramétrables **techniquement** pour permettre les tests, pas
**fonctionnellement** pour permettre de les changer sans décision.

`IMPORT_SOURCE_RETENTION_DAYS` est délibérément laissée en `CHANGE_ME` : la durée de
conservation du CSV source relève de `QO-100`, question **bloquante avant données réelles**.

---

## 8. Modification des seuils en cours d'exploitation

Seul le super-administrateur peut modifier les paramètres d'authentification et les seuils de
sécurité (matrice §19). Ces valeurs vivront à terme dans `platform_setting`, avec audit.

Les secrets ne sont **jamais** enregistrés dans `platform_setting` (modèle §5.2) ni dans
`entity_setting` (modèle §5.3).

---

## 9. Rotation

| Secret | Fréquence recommandée | Déclencheur impératif |
|---|---|---|
| `APP_SECRET_KEY` | Annuelle | Suspicion de fuite. La rotation invalide toutes les sessions actives |
| Mots de passe PostgreSQL, Redis, MinIO | Annuelle | Suspicion de fuite, départ d'un porteur d'accès |
| Identifiants SMTP de production | Selon le fournisseur | Suspicion de fuite |
| Jetons de comptes de service | Expiration configurée | Départ, changement de périmètre, suspicion de fuite. Durée maximale encore ouverte : `QO-072` |

Toute rotation d'un secret de production est précédée d'une sauvegarde et suivie d'un contrôle
de démarrage et des healthchecks.

---

## 10. Conduite à tenir en cas de fuite

Ordre impératif — la rotation précède l'analyse, car un secret exposé doit d'abord cesser
d'être valide.

1. **Révoquer immédiatement** le secret exposé, sans attendre d'avoir mesuré l'impact.
2. **Générer et déployer** un remplaçant sur l'environnement concerné uniquement.
3. **Révoquer les sessions** si `APP_SECRET_KEY` est concernée.
4. **Ouvrir une anomalie** de gravité au minimum critique, étiquetée `security`. Elle préempte
   le travail du lot en cours (`ARB-BACK-005`).
5. **Mesurer l'exposition** : durée, canal, personnes ayant pu y accéder.
6. **Si le secret a été poussé sur GitHub**, considérer qu'il est définitivement compromis.
   Le retirer d'un commit ne suffit pas : il reste dans l'historique, dans les forks et dans
   les caches. La rotation est la seule réponse valable.
7. **Enregistrer** l'incident au registre des risques et, si un choix structurant en découle,
   au registre des décisions.
8. **Ne jamais** citer la valeur du secret dans l'anomalie, le commit, l'audit ou les logs.

---

## 11. Contrôles

### 11.1 Manuels, disponibles dès maintenant

```bash
# Aucun fichier .env ne doit etre suivi par Git
git ls-files | grep -E '^\.env' | grep -v '^\.env\.example$' && echo "ALERTE" || echo "OK"

# Les trois fichiers d'environnement doivent etre ignores
git check-ignore -q .env && git check-ignore -q .env.recette && echo "OK"

# .env.example ne doit contenir aucune valeur reelle
grep -nE '^[A-Z_]+=.+' .env.example | grep -viE '=(CHANGE_ME|true|false|json|info|development|recette|production|onboarding|localhost|db|redis|minio|mailpit|no-reply|eXalt|/api|exalt-company|lax|exalt_session|eu-west-1|[0-9,.:/-]+$)' || echo "OK"
```

### 11.2 Automatiques, au LOT 1

| Contrôle | Outil candidat | Story |
|---|---|---|
| Détection de secrets dans l'historique et les commits | Gitleaks | `MVP-L01-US005` |
| Audit des dépendances | pip-audit | `MVP-L01-US005` |
| Analyse des images | Trivy | `MVP-L01-US005` |
| Validation de la configuration au démarrage | code applicatif | `MVP-L01-US002` |

La chaîne d'intégration doit **bloquer volontairement** une erreur de secret : c'est un
critère de sortie explicite du LOT 1.

---

## 12. Interdictions

- placer un secret dans `.env.example`, un README, un commentaire de code, un message de
  commit, un titre de branche, une issue ou une description de pull request ;
- préfixer un secret par `VITE_` ;
- réutiliser un secret entre deux environnements ;
- réutiliser un secret ayant existé dans le prototype historique ;
- stocker un secret dans `platform_setting` ou `entity_setting` ;
- journaliser ou auditer la valeur d'un secret, d'un jeton ou d'un magic link complet ;
- démarrer en production avec une variable manquante ou une option de développement active ;
- utiliser Mailpit en production, ou un fournisseur réel en recette ;
- exposer publiquement PostgreSQL, Redis, MinIO ou Mailpit ;
- contourner ces règles au motif qu'il s'agit d'un environnement local.
