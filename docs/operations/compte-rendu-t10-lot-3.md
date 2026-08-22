# Compte rendu — LOT 3, sous-étape `T10`

**Comptes de service et scopes**
**Story :** `MVP-L03-US007` (`P1`), issue `#69`
**Réalisée le :** 22 août 2026
**Décision produite :** `DEC-536`
**Écarts ouverts et clos :** `ECART-036`, `ECART-037`
**Question close :** **`QO-072`** — par arbitrage de Jonathan
**Migration produite :** **`0013`**

---

## 1. Le §8 de la fiche annonçait trois choses, et deux étaient fausses

Il listait quatre points « que le corpus ne tranche pas ». Mesure faite avant d'écrire une ligne :

| Ce que la fiche annonçait | Ce que le corpus dit |
|---|---|
| « **Liste des scopes** — aucun document n'en énumère » | **le §22 en donne cinq.** `ECART-036` |
| « **Durée maximale d'un jeton** — le §10.5 dit configurable » | vrai, **et la question est déjà numérotée `QO-072`** dans le cahier §32, attribuée à « Jonathan / sécurité », échéance « LOT 3, story `MVP-L03-US007` » |
| (`QO-118`, politique de mot de passe) | juste |

**Le §8 de cette fiche a donc été faux trois fois sur quatre** — `ECART-034` en `T8` pour les seuils
de débit, `ECART-036` ici, et un troisième point qui existait déjà sous un numéro. **À annoncer à
`G3` :** un relecteur ne devrait pas s'y fier sans relire le cahier.

---

## 2. Les cinq scopes sont écrits, et la liste n'est PAS fermée

```text
people:read   people:import   media:process   email:send   reports:generate
```

**Deux mots changent tout : « Chaque compte de service possède des scopes explicites, PAR EXEMPLE ».**
C'est la forme du §25.1 du modèle — « à prévoir **notamment** » — où le LOT 2 a posé quatre unicités
de plus, chacune **dérivée** d'une règle écrite.

**Les deux erreurs symétriques, et la bonne lecture est entre elles :**

- inventer un vocabulaire aurait contredit le §22 ;
- **poser une liste blanche fermée** aurait contredit « par exemple » et **bloqué le LOT 9**, qui
  créera ses scopes d'import, et le LOT 11 pour les médias et les exports.

La validation porte donc sur la **forme** — `domaine:action`, dérivée des cinq exemples — et les cinq
sont déclarés comme le vocabulaire **connu**. **Deux tests relisent le cahier** : l'un pour les cinq
valeurs, l'autre pour les mots « par exemple ». Si le cahier fermait un jour sa liste, le second
échouerait, et il devrait.

**Et le mode d'échec d'une faute de frappe est bruyant.** Rien n'accorde `people:raed`, donc l'appel
qui l'exige est **refusé** — « refus par défaut », §20.1 — et non autorisé par erreur. C'est ce qui
rend la liste ouverte acceptable.

**`couvre` est une égalité exacte.** Aucun joker, aucune hiérarchie : il serait tentant que
`people:import` implique `people:read`, le cahier n'en écrit rien, et l'inventer accorderait des
droits que personne n'a accordés — ce que `RIGHTS-018` interdit.

---

## 3. `QO-072` — la première question du corpus close par arbitrage

Le cahier §7.4 dit « la durée maximale des jetons reste **à arbitrer avant leur création** », et le
§32 l'ouvre sous le numéro **`QO-072`**, échéance **cette sous-étape**. Aucun jeton réel n'existe,
donc l'arbitrage était dû.

**Réponse de Jonathan : 90 jours.** Son motif, dans ses termes : redonner une clé au script **quatre
fois par an**, contre une clé fuitée qui **cesse de fonctionner au bout de trois mois**.

Les deux options écartées le sont pour leur **conséquence**, non pour leur principe : 30 jours fait
tomber le script sur un renouvellement oublié — c'est son risque réel, pas la sécurité ; 365 jours
laisse une clé volée valable un an.

**Elle reste CONFIGURABLE**, par `SERVICE_TOKEN_MAX_DAYS`, et c'est le §10.5 littéralement. **C'est
l'inverse de `T8`** : les seuils du §20.2 sont en constantes parce que le cahier les écrit et que les
rendre réglables inviterait à les abaisser. Ici le cahier demande le contraire.

**Et c'est un plafond, pas un défaut** : demander davantage **lève**. Écrêter en silence ferait
qu'un appelant croirait avoir obtenu un an et découvrirait quatre-vingt-dix jours en production.

---

## 4. `ECART-037` — une relation que le diagramme déclare et que la table ne portait pas

Le modèle §11 déclare **`SERVICE_ACCOUNT ||--o{ AUTH_EVENT : produces`**. La table posée par `T2`
porte `person_id` et `user_account_id`, **et rien vers `service_account`**.

**Sans cette colonne, « chaque appel est audité » était insatisfaisable sans inventer** : soit un
**huitième** type d'événement — que le §10.6 interdit en en déclarant sept, et que `T12` auditera
précisément — soit un audit **anonyme**.

Migration **`0013`** : la colonne, sa clé étrangère, son index, et une contrainte
`ck_auth_event_un_seul_acteur`. **Les deux nuls restent permis, et c'est indispensable** — un magic
link demandé pour une adresse inconnue ne désigne personne, et l'interdire casserait la réponse
générique de `T3`.

**La cause est instructive** : le §10.6 décrit `auth_event` **par ses événements**, pas par ses
colonnes ; le lien n'est déclaré que dans le **diagramme**. Classe `ECART-023` — un document a
plusieurs endroits qui se complètent, et lire l'un sans l'autre laisse un trou.

---

## 5. Deux choix d'implémentation dont l'inverse perd quelque chose

**Un seul `UPDATE … RETURNING` pose `last_used_at` ET vérifie la validité** — sixième occurrence du
compare-et-pose après `T4`, `T5`, `T6`, `T7` et `T8`. Le §10.5 déclare « la dernière utilisation » et
le critère dit « **chaque** appel » : une trace posée dans un second temps peut manquer.

**L'état du compte est vérifié APRÈS, et c'est le point délicat.** Le mettre dans la clause `WHERE`
aurait été plus court et aurait **perdu `last_used_at`** — or un compte désactivé qu'on continue de
solliciter est exactement ce qu'un opérateur veut voir. Un test l'éprouve en lisant la colonne après
un refus.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **661 tests, 0 échec** — 630 avant `T10`, dont **390 d'intégration** |
| `make check` · `make audit` | **0** · **0** |
| **`make service-check`** | **0 — 11 contrôles**, dont **trois témoins** |
| **`make migrations-check`** | une base vide reconstruite par la seule chaîne donne un schéma **identique** |
| `alembic-check` · `code-check` | **une seule tête**, `0013` · **le conteneur exécute le code du dépôt** |
| `revocation` · `debit` · `csrf` · `sessions` · `admin` · `magic-link` | **6** · **12** · **10** · **13** · **10** · **15**, tous à 0 |

```text
le conteneur voit SERVICE_TOKEN_MAX_DAYS=90
TEMOIN — proprietaire inconnu REFUSE, aucune personne creee
duree de 91 jours REFUSEE — aucune ecretation
scope mal forme REFUSE
jeton cree, affiche UNE seule fois
TEMOIN — le jeton legitime passe avec `people:read`
jeton HORS SCOPE refuse (`scope_manquant`)
expiration effective a J+31 — le temps est INJECTE
3 appels, 3 evenements, 1 succes — `service_account_id` porte
`last_used_at` pose, et `token_hash` est une empreinte SHA-256
aucun jeton dans le journal de `api`
```

**Le contrôle lit `SERVICE_TOKEN_MAX_DAYS` DANS le conteneur**, pas dans le `.env` : `T7` a montré
qu'une variable qui ne traverse pas la frontière de processus produit un échec dont le message ne
nomme pas la cause.

**Témoin négatif exécuté** : contrôle de scope neutralisé → **3 tests échouent**, dont celui du
critère et celui du gabarit unique de refus.

---

## 7. Deux défauts, et le second est une leçon que je venais d'écrire

| № | Défaut | Comment |
|:--:|---|---|
| `T10-1` | **Le refus d'un jeton périmé ou révoqué n'était attribué à AUCUN compte.** `make service-check` a compté **2** événements attribués au lieu de 3, et il avait raison : avec un critère qui exige que « chaque appel soit audité », un refus anonyme n'audite rien d'utile — un opérateur veut voir **quel** compte s'obstine avec une clé morte | le contrôle a échoué sur du code que je croyais conforme |
| `T10-2` | **13 événements sans acteur laissés en base.** Un jeton mal formé ou inconnu ne désigne ni personne ni compte : il **échappe aux deux filtres par identité**. Mon nettoyage n'avait pas de borne temporelle | mesure de l'état après la suite |

> **`T10-2` EST LA SIXIÈME OCCURRENCE DE CETTE LEÇON DANS CE LOT**, et je l'avais écrite dans le
> compte rendu de `T9` **une sous-étape plus tôt** : *la trace d'un refus sans acteur échappe à tout
> nettoyage par identité ; seule la borne temporelle l'attrape.*
>
> C'est la cinquième fois dans ce projet qu'un piège **documenté** est rejoué — §9.0 : *un piège
> documenté n'est pas un piège désarmé.* Et la parade du §7.2 s'applique : quand une classe d'erreur
> résiste à la vigilance, **change d'outil**. Ici l'outil serait un contrôle qui mesure le résidu
> après chaque suite — je le recommande pour `T12`, qui porte la qualité transversale, plutôt que de
> promettre d'être plus attentif une septième fois.

**Et une observation qu'il faut signaler sans la surinterpréter.** Le test de performance du LOT 2 —
`test_le_jeu_de_recette_reste_exploitable_avec_les_index_definis`, §30.25 — a échoué **une fois**,
immédiatement après une purge manuelle de `auth_event` que j'avais faite pour mesurer le résidu.
**Non reproduit** : 6/6 sur son fichier seul, et **661/661 sur deux suites complètes** ensuite. Un
test qui mesure des durées inférieures à la milliseconde est sensible à la charge ; le signaler est
plus honnête que d'affirmer un correctif que je n'ai pas fait. **À rattacher à `T12`**, qui porte la
performance.

**Le correctif est le §7.20 appliqué à la lettre** : ne pas affaiblir le contrôle, faire dire le vrai
au code. Une **seconde lecture, sur le seul chemin de refus**, attribue l'événement — elle ne coûte
rien au chemin normal, et elle ne fuite rien : le motif reste interne, et l'appelant reçoit le même
refus dans les deux cas.

Deux motifs internes désormais, `jeton_de_service_inconnu` et
`jeton_de_service_perime_ou_revoque`, **un seul gabarit vers l'extérieur**.

---

## 8. Ce qui n'est PAS couvert

- **aucune route ne consomme encore le scope.** Aucun document n'énumère les routes qu'un compte de
  service peut appeler, et aucune route métier n'existe — le portail est le LOT 4. En inventer une
  serait §6.5, et créerait une surface à maintenir pour rien. **Même parti que `T7` pour le CSRF** :
  le mécanisme est livré et prouvé par une application minimale **du test**, et le résiduel est nommé
  dans l'en-tête de `dependances.py` ;
- **la gestion des comptes de service par écran.** Back-office, **LOT 9**. `make compte-de-service`
  est l'équivalent de `make admin-local` : un geste d'exploitation, pas une interface ;
- **la rotation automatique** des jetons. Rien ne la décrit ; `make compte-de-service` crée un
  **nouveau** jeton sans révoquer les précédents, ce qui est le comportement voulu — on renouvelle
  avant de retirer l'ancien, sinon le script tombe en panne ;
- **`audit_log` du §21.1**, pour « chaque appel **sensible** » au sens large. **LOT 10** ;
- **la révocation au départ ne touche pas les comptes de service**, et c'est voulu : ils appartiennent
  à une entité, pas à une personne. Le §9 du compte rendu de `T9` le disait déjà ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T11` devra savoir

1. **`T11` est les HUIT écrans d'authentification**, et la fiche ne lui attache **aucune story** — son
   périmètre est la liste d'interfaces du LOT 3 dans la roadmap : page de connexion, confirmation de
   demande de lien, lien expiré ou consommé, connexion administrateur, déconnexion, pages `403`, `404`
   et erreur générale. **Compte-les sur la roadmap, jamais sur la fiche** — le §8 de la fiche s'est
   trompé trois fois sur quatre.
2. **Le design system existe depuis `T10` du LOT 1** : `packages/ui`, jetons **relevés du prototype et
   recalculés contre WCAG 2.2 AA** (`DEC-491`). **Les couleurs de marque sont des SURFACES**, pas des
   couleurs de texte : le jaune rend 1,37 de contraste, le bleu foncé 1,69. N'invente pas de couleur.
3. **Le contrat API partagé est en v1.6**, `packages/contracts/src/contrat-api.json`, et il porte
   **dix endpoints** avec leurs codes exploitables. Le frontend doit le lire, pas deviner.
4. **`eslint-plugin-jsx-a11y` est actif et sait échouer** — éprouvé par témoin négatif en `T5` du
   LOT 1. Huit écrans neufs, c'est le premier vrai volume qu'il examinera.
5. **Aucun jeton dans `localStorage`** — interdit absolu du §9.5. Le cookie de session est `HttpOnly`,
   donc le frontend ne le lit **jamais** ; `make sessions-check` le vérifie **sur les sources**, en
   retirant les commentaires et en gardant les chaînes.
6. **Le jeton anti-CSRF est délivré par `GET …/auth/session`** et doit voyager dans l'en-tête
   `X-CSRF-Token` sur les écritures. Un frontend qui recharge le perd et doit le réobtenir — c'est la
   raison pour laquelle cette route ne l'exige pas elle-même.
7. **La réponse de la demande de lien est IDENTIQUE que l'adresse existe ou non.** Un écran qui
   afficherait deux messages différents rouvrirait l'oracle que `T3` a fermé, côté interface.
