# Checklist de validation — porte `G3`

**LOT 3 — Authentification, sessions et sécurité applicative**
**Remise le :** 22 août 2026, à la sortie de la sous-étape `T12`
**Destinataire :** Jonathan — c'est **sa** décision
**Tag à poser après validation :** `v0.3.0`, annoté, sur `main`

Ce document est fait pour être **lu et coché**. Chaque ligne porte la commande qui la prouve et le
résultat réellement obtenu le 22/08/2026. **Aucun nombre n'y est affirmé sans avoir été mesuré**, et
chaque grandeur est accompagnée de la commande qui la produit.

> **Ce que ce lot a produit, en une phrase :** l'authentification complète — magic link, comptes
> administrateurs, sessions, CSRF, limitation de débit, révocation au départ, comptes de service — plus
> les **huit écrans**, prouvée par **794 tests** et **onze contrôles de stack** dont chacun porte ses
> témoins.

---

## 1. Les six critères de sortie de la roadmap

| | Critère | État | Ce qui le prouve |
|:--:|---|---|---|
| ☑ | tous les scénarios autorisés et refusés sont testés | **acquis** | **661 tests pytest** dont **390 d'intégration**, plus **133 Vitest**. Chaque refus a son **témoin** : `isolation-temoin`, `sessions-temoin`, et un témoin nommé dans chacun des onze contrôles |
| ☑ | aucun jeton n'est stocké dans `localStorage` | **acquis** | `make sessions-check` — la règle est **structurelle** (`HttpOnly`, aucun jeton dans un corps) et le contrôle des sources la confirme, **commentaires retirés, chaînes gardées**, avec témoin dans les deux sens. `make ecrans-check` l'étend aux **sept** sources d'écran |
| ☑ | aucune adresse absente de la base ne peut se connecter | **acquis** | `make magic-link-check` — **15 contrôles**. La réponse est **identique** corps, code et en-têtes, connue ou non, et `make ecrans-check` prouve que **l'interface ne la défait pas** |
| ☑ | les magic links ne figurent pas dans les logs | **acquis** | `make magic-link-check` dans `api` **et** `caddy`, l'absence de journal d'accès Caddy étant **gardée** (`DEC-525`). `make evenements-check` le revérifie sur les **valeurs** en base et en journal, **avec témoin** |
| ☑ | les limites de débit produisent les résultats attendus | **acquis** | `make debit-check` — **12 contrôles, 3 témoins**, et les **deux** refus (adresse connue, inconnue) comparés **corps et en-têtes** |
| ☑ | **Jonathan valide l'authentification** | **VALIDÉ le 22/08/2026** | décision de Jonathan, tracée par `DEC-540` |

---

## 2. Les onze contrôles de stack, et ce que chacun refuse

Tous s'exécutent **à travers Caddy en HTTPS**, sur l'API du conteneur — pas sur une application
montée en processus.

```bash
make up && make migrate
make magic-link-check    # 15 controles — la reponse est IDENTIQUE, connue ou non
make admin-check         # 10 — le verrou se declenche, `admin-local` le leve
make sessions-check      # 13 — les trois attributs du cookie, le jeton hors navigateur
make csrf-check          # 10 — 5 ecritures refusees, une cle rejouee sans effet
make debit-check         # 12 — les seuils du 20.2, avec les DEUX refus compares
make revocation-check    #  6 — le depart revoque, et l'API rend 401 — MESURE
make service-check       # 11 — un jeton hors scope refuse, l'expiration effective
make ecrans-check        #  7 — les 8 chemins servis, aucune couleur hors jetons
make evenements-check    #  6 — les 7 evenements du 10.6, sans rien de sensible
make residu-check        # la suite d'integration, ET la preuve qu'elle ne laisse rien
make recette-modele-check # les 25 controles du 30, CLASSES
```

**Les onze sont dans l'intégration continue**, qui bloque la fusion sur `develop` et sur `main`.

---

## 3. La démonstration guidée — sept gestes, dans cet ordre

| | Geste | Ce que tu dois voir |
|:--:|---|---|
| 1 | ouvrir `https://app.onboarding.localhost/connexion` | l'écran de connexion, aux couleurs des jetons de `packages/ui` |
| 2 | saisir **ton** adresse, puis une adresse inventée | **le même message, mot pour mot.** C'est le critère central du lot |
| 3 | ouvrir Mailpit sur `http://127.0.0.1:8025` | **un seul** message, pour la seule adresse qui existe |
| 4 | cliquer le lien reçu | connexion établie — et **le jeton disparaît de la barre d'adresse** |
| 5 | recliquer le **même** lien | « Ce lien n'est plus valable » : usage unique |
| 6 | aller sur `/deconnexion` et fermer la session | la session est révoquée **côté serveur**, pas seulement oubliée |
| 7 | recharger `/connexion/administrateur` directement | la page s'affiche : le **repli SPA** fonctionne, ce qui n'avait jamais été exercé avant `T11` |

**Et un huitième geste, si tu veux voir un refus :** cinq mots de passe faux d'affilée sur l'écran
administrateur. Le sixième essai répond « trop de tentatives » — la limitation de `T8` — et non
« identifiants refusés » : la distinction est utile à toi et **n'apprend rien** à un attaquant, la
limite s'appliquant à toute adresse.

---

## 4. Les grandeurs, avec la commande qui les produit

| Grandeur | Valeur au 22/08/2026 | Commande |
|---|---|---|
| Tests pytest | **661**, dont **390 d'intégration** | `uv run pytest -q --collect-only \| tail -1` |
| Tests Vitest | **133** — 1 `contracts`, 90 `ui`, 42 `web` | `make test-frontend` |
| Migrations | **13**, tête `0013` | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Cibles `make` | **75** | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Décisions | **205** au total, **120** de réalisation | `make docs-check` les **dérive** |
| Écarts | **37** | `grep -c '^## \`ECART-0' docs/decisions/registre-ecarts.md` |
| Comptes rendus du lot | **11**, `T1` à `T11` | `ls docs/operations/compte-rendu-t*-lot-3.md \| wc -l` |
| Défauts consignés au LOT 3 | **57** | `grep -ohE '\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-3.md \| sort -u \| wc -l` |

> **Le compte de défauts est un MINORANT**, et le dire vaut mieux que de laisser croire à un total
> exact : quelques défauts sont décrits sans identifiant dans les comptes rendus.

---

## 5. Ce que le lot n'a PAS fait, et qu'il ne faut pas croire acquis

| Point | État réel |
|---|---|
| **les alertes du §20.2** | **non faites.** Cinq des six lignes du §20.2 disent « alerte », et une alerte suppose `operational_alert` du §21.2 — **LOT 10**. `T8` livre la **détection**, journalisée |
| **les invitations** | **elles n'existent pas.** `ECART-035` : 0 occurrence dans le modèle et dans la matrice. Le critère de `US006` les nomme, et il n'y a rien à invalider — **LOT 9** |
| **l'idempotence durable** | Redis n'est pas durable. La garantie couvre la **double soumission**, pas un rejeu différé — `async_job.idempotency_key`, **LOT 11** |
| **`audit_log` du §21.1** | **LOT 10.** `auth_event` est l'historique **spécialisé** de l'authentification, pas l'audit général — et le §30.20 reste `reporté` |
| **aucune route ne consomme un scope** | le mécanisme de `T10` est livré et prouvé ; sa première consommatrice viendra avec la première route métier. **Même parti que le CSRF de `T7`** |
| **`axe` et Playwright** | nommés au §17.1, appartiennent au **LOT 12**. `jsx-a11y` examine les huit écrans, mais **aucun audit automatisé de page rendue** |
| **les cinq largeurs de recette** | `LARGEURS_RECETTE` existe depuis `T10` du LOT 1 ; **aucune mesure de débordement** n'est faite. **LOT 12** |
| **le « retrait d'accès »** du §7.4 | seconde cause de révocation. La constante est **nommée sans être employée** : elle suppose un écran de gestion des rôles |
| **Row-Level Security** | le §2.5 la cite en « compatibilité future ». Rien ne la datant, elle **n'est pas** mise en place — ce n'est pas un oubli |
| **la recette** | **elle exécute des images de révision antérieure à `T1`**, et son API se connecte encore en **superutilisateur**, mesuré. Voir §7 |

---

## 6. Trois écarts à connaître avant de valider

| ID | Ce qu'il dit | Ce que ça change pour toi |
|---|---|---|
| `ECART-032` | le **backlog** interdit plus large que le cahier, la matrice **et** le modèle réunis | rien au livrable — le cahier prévaut — mais un relecteur du backlog conclurait à un critère manquant |
| `ECART-035` | le critère de `US006` exige d'invalider les **invitations**, qui n'existent pas | la case correspondante est **décochée et expliquée** dans l'issue `#68`, plutôt que cochée à tort |
| **`ECART-034`, `036`** | **le §8 de `fiche-lot-3.md` a été faux trois fois sur quatre** | ne t'y fie pas sans relire le cahier. Il annonçait trois décisions à prendre : deux étaient déjà prises par le cahier, et une portait déjà un numéro (`QO-072`) |

**Et une question close par ton arbitrage :** `QO-072`, la durée maximale des jetons de service —
**90 jours**, configurable, et c'est un **plafond** : demander davantage échoue plutôt que d'être
écrêté en silence.

---

## 7. La recette — FAIT le 22/08/2026, avec ton accord

**C'était le seul point restant, et il est clos** — `DEC-539`. Ce qui a été mesuré :

| | Avant | Après |
|---|---|---|
| révision embarquée | antérieure à `T1` | **`3bc68b9`**, le commit de `T12` |
| rôle de connexion de l'API | `onboarding_app`, **superutilisateur** | **`onboarding_recette_runtime`** — « ne peut que lire et écrire des lignes » |
| séparations du cahier §22.2 | — | **7 sur 7**, 57 contrôles, 0 échec |

**Et deux défauts trouvés en le faisant**, qui ne pouvaient apparaître qu'en exécutant réellement la
recette : `make migrate ENVIRONNEMENT=recette` appelait `code-refresh`, qui tente un `build` sur une
image référencée par **empreinte** — Docker refuse, et reconstruire localement **déferait le principe
même** de la recette. Et `.env.recette` déclarait **83 variables sur 84** : `make env-check` a nommé
la manquante, ce qui est exactement la parade posée par `ECART-022`.

La procédure, pour mémoire :

```bash
# 1. la publication se fait par le workflow `images.yml`, sur poussee vers `develop`
gh run list --workflow=images.yml --limit 3

# 2. puis reepingler la recette sur les nouvelles empreintes
make images-pin

# 3. et prouver que la recette tourne sous le regime actuel
make up-recette && make recette-check && make separations-check && make down-recette
```

**Je ne l'avais pas fait de mon propre chef** : republier pousse vers un registre externe, et le §12
dit de ne rien pousser vers l'extérieur sans ton accord. Tu l'as donné le 22/08/2026.

---

## 8. Ta décision

| | |
|---|---|
| ☑ | **Je valide le LOT 3.** — **décision de Jonathan du 22/08/2026**, tracée par `DEC-540` |
| ~~☐~~ | ~~Je demande des corrections avant de valider~~ — sans objet |

**Si tu valides**, la suite est :

1. une décision au registre (`DEC-538+`) tracant le franchissement de `G3` ;
2. la fusion de `develop` vers `main` — **par un merge commit**, et l'arbre doit être **identique**
   des deux côtés, ce que `git rev-parse origin/main^{tree} origin/develop^{tree}` prouve. C'est la
   leçon `ECART-026` : « aucun conflit » ne veut pas dire « le résultat est celui que je veux » ;
3. le tag `v0.3.0`, annoté ;
4. l'ouverture du **LOT 4 — portail et accueil**, qui est **ta** décision.
