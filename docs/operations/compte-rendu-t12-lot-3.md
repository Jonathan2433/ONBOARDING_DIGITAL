# Compte rendu — LOT 3, sous-étape `T12`

**Audit des événements, recette et checklist `G3`**
**Story :** `MVP-L03-US008`, issue `#70`
**Réalisée le :** 22 août 2026
**Décision produite :** `DEC-538`
**Migration produite :** **aucune**

---

## 1. Les sept événements sont produits par des appels réels, non insérés

**Insérer sept lignes dans `auth_event` prouverait que la table accepte sept valeurs**, pas que les
actions les produisent. Le scénario passe donc par sept gestes, chacun à travers Caddy en HTTPS :

```text
MAGIC_LINK_REQUESTED      demander un lien
MAGIC_LINK_USED           le consommer
LOGIN_FAILURE             un mot de passe faux
ACCOUNT_LOCKED            cinq echecs
LOGIN_SUCCESS             une connexion
SESSION_REVOKED           une deconnexion
ADMIN_PASSWORD_CHANGED    un changement de mot de passe
```

**Le compte est importé de `TypeEvenementAuth`, pas écrit.** Un huitième type ajouté au code ferait
échouer ce contrôle — **et c'est son rôle** : `T12` audite exactement les types que le §10.6 déclare.

**Et les deux acteurs sont exigés.** `auth_event` porte `person_id` **et** `service_account_id` depuis
la migration `0013` : un contrôle qui ne compterait que le premier déclarerait l'audit acquis **en
ignorant les comptes de service**, ce que le §22.1 interdit. C'était le point que `T10` s'était écrit.

**La limitation de débit de `T8` gêne ce scénario, et c'est normal** : cinq échecs suffisent à bloquer
l'adresse. Les compteurs sont purgés entre les phases, par le helper partagé — même geste que
`admin-check` et `csrf-check`.

---

## 2. Le témoin est ce qui rend l'absence de fuite significative

Le contrôle vérifie qu'aucun mot de passe, aucun jeton et aucune adresse ne figure dans
`auth_event.detail`, ni dans les journaux de `api` et `caddy`.

**Un tel contrôle rend « 0 » quoi qu'il arrive si son motif est cassé.** Il insère donc **exprès** un
mot de passe dans `auth_event`, exige de le trouver, puis le retire. Sans ce témoin, l'absence
prouverait l'absence de contrôle plutôt que l'absence de fuite — §7.0, quatrième proposition.

---

## 3. Deux contrôles structurels, à la place d'une huitième promesse

### `make residu-check` — sept occurrences d'une même classe de défaut

| Défaut | Ce qu'il a coûté |
|---|---|
| `T3-3` | 18 lignes `auth_event` résiduelles → **2 tests de `T2`** en échec |
| `T4-3` | un nettoyage supprimé par une réécriture → exécution suivante cassée |
| `T4-5` | les `LOGIN_FAILURE` sans personne échappaient au nettoyage |
| `T5-5` | idem, dans un autre fichier |
| `T6-2` | cinq nettoyages antérieurs à `user_session` → **10 tests sans rapport** en échec |
| `T9` | six défauts de décor, tous trouvés par la base |
| `T10-2` | 13 événements sans acteur — **une sous-étape après avoir écrit la leçon** |

**La septième est celle qui décide.** J'avais écrit dans le compte rendu de `T9` : « la trace d'un
refus sans acteur échappe à tout nettoyage par identité ». Je l'ai recommise en `T10`. Le §7.2 dit quoi
faire : **quand une classe d'erreur résiste à la vigilance, change d'outil au lieu de promettre d'être
plus attentif.**

**La mesure est exacte, pas heuristique.** Chercher des marqueurs — `t3api`, `%.test`, `t12-verif-` —
serait une **liste** qui vieillit au premier ajout et une **heuristique** dans un contrôle, ce qui est
un défaut (§7.25, leçon `T9-2`). Le contrôle compare donc un **avant/après table par table**, la liste
des tables étant **dérivée du catalogue** : il fonctionne aussi bien sur une base vide que sur le jeu
de recette de 27 936 lignes.

**Il remplace `make test-integration` dans la CI**, il ne s'y ajoute pas : lancer la suite deux fois
doublerait cinquante secondes pour rien, et son code de sortie porte **les deux verdicts**.

**Témoin négatif exécuté** : un seul nettoyage retiré →

```text
ECHEC : 1 table(s) ont change de compte — RESIDU
    auth_event                             0 -> 5  (+5)
```

…avec les trois causes connues imprimées. C'est l'outil que les sept occurrences réclamaient.

### `make icloud-verify` — le garde-fou existait et était aveugle

Pendant cette sous-étape, **quatre fichiers ont été remis à une version antérieure sans aucune action
de session** — `apps/web/package.json`, `pnpm-lock.yaml`, `fiche-lot-3.md`, `exploitation-locale.md`.

**Mesure :** les quatre portaient le **même mtime à la seconde** et des ctime à 1 s d'écart — une
réécriture **en lot**, pas quatre éditions. C'est la signature d'`ROAD-RSK-026` documentée au §7.1 et
§7.17.

**Et `make icloud-verify` est passé au vert.** Il cherche les copies de conflit `* [0-9]` : exact pour
ce mode de défaillance, **aveugle à celui-ci** — un fichier silencieusement réverté ne laisse aucune
copie. C'est le §7.0 quatrième proposition appliqué à un garde-fou existant : il ne prouvait rien de
cette classe **tout en donnant l'impression de couvrir iCloud**.

Le garde-fou est donc **étendu plutôt que doublé** — la routine du §11 reste inchangée : il compare
l'**arbre** de `HEAD` à celui de l'amont et échoue si les deux sont identiques **alors que des fichiers
sont modifiés**. Cette combinaison n'a pas d'autre cause plausible.

**Témoin négatif exécuté** dans un arbre de travail jetable : arbre identique à l'amont plus un fichier
modifié → **échec**, fichiers nommés, chemin de diagnostic donné.

**Rien n'a été perdu** dans l'incident : le diff ne contenait que des retraits de contenu déjà commité,
et les arbres ont été vérifiés identiques après restauration — la preuve qui fait foi selon §7.24.

---

## 4. Ce que la fiche annonçait pour `T12`, et ce que la mesure dit

| Ce que la fiche annonçait | Ce que la mesure dit |
|---|---|
| « `recette-modele-check` reclasse `§30.11` » | **déjà acquis depuis `T3`** |
| « … `§30.22` » | **déjà acquis depuis `T9`** |
| « … et le résiduel de `§30.4` » | son échéance est le **LOT 7**, et son résiduel est une règle de **processus** que rien ne peut acquérir en base |

**Le reclasser serait faux ; ne rien dire serait incomplet.** `T9` en couvre désormais la moitié
utile — `enregistrer_un_depart` **nomme** les consultants privés de DSM. Le résiduel passe donc de
« rien ne le voit » à « **rien ne le corrige automatiquement** ».

> **Quatrième fois que le §8 ou le §3 de cette fiche affirme faux** — `ECART-034`, `ECART-036`, la
> durée des jetons déjà numérotée `QO-072`, et ces trois lignes. C'est consigné dans la checklist `G3`
> pour qu'un relecteur ne s'y fie pas sans relire le cahier.

---

## 5. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **661 tests, 0 échec** — dont **390 d'intégration** |
| Vitest | **133 tests** — 1 `contracts`, 90 `ui`, 42 `web` |
| `make check` · `make audit` | **0** · **0** |
| **`make evenements-check`** | **0 — 6 contrôles**, dont le témoin |
| **`make residu-check`** | **0 — 23 tables comptées, aucun résidu**, suite verte |
| **`make icloud-verify`** | **0**, et son nouveau contrôle éprouvé par témoin négatif |
| `recette-modele-check` | **12 acquis**, 1 partiel, 11 reportés, 1 inapplicable |
| Les 9 autres contrôles du lot | tous à **0** |

---

## 6. Ce qui reste à faire avant le tag, et pourquoi je ne l'ai pas fait

**La recette exécute des images de révision antérieure à `T1`** — son API se connecte encore en
**superutilisateur**, mesuré. Il faut republier les trois images, puis `make images-pin`, puis
`make separations-check`.

**Je ne l'ai pas fait de mon propre chef** : republier pousse vers un registre externe, et le §12 dit
de ne rien pousser vers l'extérieur sans l'accord de Jonathan. La procédure est écrite au §7 de la
checklist `G3`.

---

## 7. Ce que le LOT 4 devra savoir

1. **Le portail est le LOT 4**, et il consommera trois choses livrées ici sans consommateur : la
   **dépendance de scope** de `T10`, la **protection CSRF** sur les routes métier (`T7`), et le
   **rafraîchissement de session** — dont `GET …/auth/session` est aujourd'hui la seule écriture
   n'exigeant pas de jeton, **résiduel nommé à réexaminer à ce moment-là**.
2. **`packages/contracts` est en v1.6, dix endpoints.** Le frontend le lit, il ne devine pas — et un
   contrôle Python vérifie que le schéma OpenAPI le respecte.
3. **Le routeur existe** depuis `T11`, et `routes.ts` est la source unique des chemins. Les quatre
   autres bibliothèques du §17.1 restent hors du dépôt **faute d'usage** : c'est le LOT 4 qui créera
   celui de TanStack Query et de Radix UI, et il faudra alors les installer **avec la même
   justification mesurée**.
4. **`make residu-check` remplace `make test-integration`.** Si le LOT 4 ajoute une table, ce contrôle
   dira immédiatement quel nettoyage l'a oubliée — c'est ce pour quoi il existe.
5. **`make icloud-verify` en début de session n'est pas une formalité**, et il l'est encore moins
   depuis qu'il compare l'arbre à l'amont. L'incident de cette sous-étape s'est manifesté comme un
   `git pull` refusé ; il se manifestera désormais comme un échec nommé.
