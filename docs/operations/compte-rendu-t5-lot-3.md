# Compte rendu — LOT 3, sous-étape `T5`

**Le compte administrateur local, et la dette du §8.4**
**Story :** `MVP-L03-US003`, issue `#65`
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-526`, `DEC-527`, `DEC-528`
**Question ouverte :** `QO-118`
**Migration produite :** **aucune**

---

## 1. Une seule décision t'appartenait, et le corpus en laissait trois autres ouvertes

Le §8 de la fiche du lot annonçait **une** décision pour `T5` : l'algorithme de hachage, que « le
§10.2 exige en colonnes sans nommer d'algorithme ». Elle t'a été posée, avec les trois options
**mesurées**. Ton arbitrage : `scrypt` de la bibliothèque standard.

**Trois autres n'étaient pas dans la fiche, et je les ai instruites sans te les demander parce
qu'elles réutilisent des valeurs déjà écrites :**

| Question | Ce que le corpus écrit, et ce qu'il n'écrit pas |
|---|---|
| seuil du verrouillage | §20.2 : « **5 échecs** administrateur en **15 minutes** : alerte ». Il parle d'**alerte** ; le verrouillage du §7.5 et `locked_until` du §10.1 n'ont **aucun** seuil |
| durée du verrou | nulle part. **15 minutes**, le second nombre de la même phrase |
| « la récupération est auditée » | le §7 de la fiche demande « prévoir et **documenter** le déverrouillage local, et l'éprouver ». Aucun document ne décrit d'envoi de lien de réinitialisation |

**Et une quatrième qui manquait vraiment : `QO-118`.** Aucun document n'écrit de **politique de mot
de passe**. Le §7.3 parle du **stockage** — « jamais en clair », « jamais dans les logs » — jamais de
la **force** ; le §20.3 ne borne que `APP_SECRET_KEY`, qui est une clé machine. Et le §8 de la fiche
ne la mentionne pas : personne ne l'avait vue.

Accepter un mot de passe d'un caractère serait pourtant contraire à tout le chapitre 7. **Un plancher
de 12 caractères est appliqué comme RECOMMANDATION**, en une seule constante, et il est **déclaré non
dérivé du corpus** plutôt que déguisé en décision — « une hypothèse déguisée en décision est pire
qu'une case vide » (§6.5).

---

## 2. Le motif du choix de `scrypt` est la MÉMOIRE, pas la durée

Mesure du 21/08/2026, **dans le conteneur** `python:3.12-slim` :

| `N` | durée | mémoire par calcul |
|---|---|---|
| 2^15 | ~65 ms | 32 Mio |
| **2^16** | **~130 ms** | **64 Mio** |
| 2^17 | ~260 ms | 128 Mio |

La limite du service `api` est de **1 024 Mio** (`DEC-440`). À 128 Mio par calcul, **huit connexions
simultanées suffiraient à la saturer** — ce qui ferait de la page de connexion un levier de déni de
service. `N = 2^16` est retenu pour cette raison, et non parce que 130 ms « paraît bien ».

**Zéro dépendance ajoutée.** `argon2-cffi` et `bcrypt` embarquent du code compilé qui devrait se
construire pour les **deux** architectures de nos images publiées. `bcrypt` a de plus un défaut
propre et **silencieux** : il ignore tout au-delà de 72 caractères, donc tronquerait un mot de passe
long sans que rien ne le signale.

**Résiduel nommé :** les recommandations publiques placent `argon2id` en premier. Le §10.2 exige
`algorithm` et `parameters` **en colonnes** précisément pour qu'un changement reste possible, et **un
test le prouve** — une empreinte produite avec `N = 2^14` reste vérifiable **avec ses paramètres à
elle**. Le passage à `argon2id` serait un rehachage à la prochaine connexion, non une migration
destructive.

---

## 3. Le compteur d'échecs est une COURSE, comme l'usage unique de `T4`

Lire `failed_login_count`, l'incrémenter puis écrire laisserait trois tentatives simultanées lire la
même valeur et n'en compter qu'une : le compteur avancerait de **1 au lieu de 3**, et **le
verrouillage n'arriverait jamais sous charge**. C'est le même défaut que `T4` a mesuré sur l'usage
unique, et la même parade : **un seul `UPDATE ... RETURNING`**, dont la valeur rendue est déjà la
valeur incrémentée. La fenêtre de 15 minutes est portée par le même `UPDATE`.

**Le témoin négatif est décisif :**

```text
implementation lire-puis-ecrire :
  test de concurrence -> ECHEC  « le compteur vaut 1 au lieu de 2 : deux tentatives
                                  concurrentes n'en ont compte qu'une, et le
                                  verrouillage n'arrivera jamais sous charge »
```

La barrière est la même que celle de `T4` : `pg_blocking_pids()`, une condition **observée**, pas un
délai espéré. Et les deux bornes restent **écartées** — 10 s pour la barrière, 60 s pour le verrou —
parce que la leçon `T4-4` est qu'un `lock_timeout` égal au délai de la barrière rend le test instable
une fois sur trois.

> **Une nuance honnête, et elle diffère de `T4`.** En `T4`, les tests séquentiels passaient tous sur
> l'implémentation vulnérable. Ici, **un test séquentiel a aussi échoué** — mon substitut naïf
> abandonnait également la logique de fenêtre. Seul le test concurrent **nomme** le défaut de
> concurrence, et son assertion est explicite.

---

## 4. Trois propriétés du verrouillage, et la troisième est la plus importante

| Propriété | Pourquoi elle compte |
|---|---|
| il se **déclenche** au cinquième échec | et les quatre premiers ne verrouillent pas : un verrou au premier échec passerait un test qui ne compterait que le cinquième |
| il se **relâche** seul après 15 minutes | **la parade au risque nommé au §7 de la fiche** — « le verrouillage administrateur bloque Jonathan lui-même ». Aucun verrou définitif, donc aucune intervention obligatoire |
| une tentative sur un compte verrouillé **ne le prolonge pas** | **sans cela, le verrouillage deviendrait un déni de service permanent** : un attaquant qui continue de frapper repousserait la fin du verrou à chaque coup, et le titulaire ne pourrait plus jamais se connecter |

La troisième explique l'ordre du code : le verrou est examiné **avant** le mot de passe, et le
compteur n'avance pas.

**Cinq causes de refus rendent la même réponse** — compte inconnu, mot de passe faux, compte
verrouillé, compte désactivé, compte sans mot de passe actif. Un refus qui dirait « verrouillé »
confirmerait qu'une adresse porte un compte administrateur, et **pire, apprendrait à un attaquant
qu'il a réussi** à verrouiller le titulaire. L'opérateur lit la cause exacte dans `auth_event` — six
motifs distincts.

---

## 5. `make admin-local` : créer, déverrouiller, et ne jamais écraser

Deux besoins, une cible : l'**amorçage** — `user_account` naît vide, et la démonstration de `G3`
n'aurait rien à exercer — et le **déverrouillage immédiat**, que le §7 de la fiche demande de
documenter et d'éprouver.

**Trois refus délibérés :**

- **elle ne crée aucune personne.** Une identité métier vient du LOT 5 ou de l'import du LOT 9,
  jamais d'une commande d'exploitation. Le script le dit et sort en erreur ;
- **elle ne touche jamais un mot de passe existant** sans `--reinitialiser`. Le reposer à chaque
  exécution serait une **porte dérobée** : quiconque peut lancer `make` prendrait la main sur le
  compte. Même parti que `provisionner-domaines.py`, qui ne réactive jamais un domaine coupé ;
- **elle ne lit aucun mot de passe.** Ni argument — il finirait dans l'historique du shell et dans la
  liste des processus — ni fichier, ni saisie : le §7.14 interdit de saisir un identifiant à ta
  place. Il est **engendré** sur 32 caractères, **affiché une seule fois**, et `must_change` est à
  vrai.

**Éprouvé sur la stack réelle, connexion à travers Caddy en HTTPS :**

```text
{"message":"Identifiants acceptes.","personne":"6f0dbe6f-...","changement_exige":true}
HTTP 200
```

---

## 6. La dette de `T11` du LOT 2, acquittée — et le jeu de recette a révélé une lacune de lui-même

Le §8.4 exige que l'attributeur d'une catégorie `dg` soit « ESM ou super-administrateur ». `T11`
avait posé l'attributeur en paramètre obligatoire et **laissé la vérification du droit** à ce lot.

**Les deux droits ne vivent pas dans la même table, et c'est le point :**

| Droit | Table | Portée |
|---|---|---|
| `ESM` | `framework_responsibility_assignment` | **une** entité (§8.4) |
| `SUPER_ADMIN` | `technical_role_assignment` | **global**, `entity_id` nul (§8.6) |

Les confondre donnerait à un ESM une portée globale, ou refuserait au super-administrateur ce que la
matrice lui accorde partout — « la seule exception globale ».

**Et la vérification exige la PÉRIODE, non `ends_at IS NULL`.** Une affectation **future** a elle
aussi `ends_at` nul, et n'accorde rien aujourd'hui. C'est littéralement le contrôle §24.12 du cahier,
« un rôle clôturé ne continue pas à accorder des permissions ». Deux tests bornent : clôturé, et
futur.

**Cinq tests du jeu de recette ont échoué, avec raison.** Le générateur attribuait la catégorie `dg`
par un **DSM** — qui a un rôle légitime, mais pas celui-là — et il ne créait **aucun ESM**, alors que
la matrice en fait « le responsable fonctionnel de l'entité ». Lui ajouter un ESM par entité le rend
**plus fidèle au modèle**, non seulement conforme au nouveau contrôle.

**Et quatre tests de service ont échoué aussi.** Ils nommaient déjà leur attributeur `esm` — mais il
n'était ESM de rien. L'intention du nom est désormais portée par la base. §7.21.

---

## 7. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **525 tests, 0 échec** — 487 avant `T5`, 482 avant la dette du §8.4 |
| — et **zéro résidu** en base, mesuré | `person` 0, `user_account` 0, `auth_event` 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make admin-check`** | **0 — 10 contrôles**, à travers Caddy en HTTPS |
| **`make admin-local`** | création, puis **déverrouillage**, puis **refus d'écraser** — les trois éprouvés |
| `make magic-link-check` | **0 — 15 contrôles** |
| 12 autres contrôles | tous à **0** |

**Les 43 tests nouveaux** : 38 dans `test_administrateur.py`, 5 dans `test_depots_et_services.py`.

**Ce que `make admin-check` prouve, en dix contrôles :**

```text
bon mot de passe accepte, `changement_exige` = true          (§10.2)
3 causes de refus indistinguables (2 comparaisons)           hors correlation
TEMOIN — le comparateur distingue un refus d'un succes
verrou declenche apres 5 echecs                              le bon mot de passe rend 400
le verrou ne se lit pas dans la reponse
audit — ACCOUNT_LOCKED 1, LOGIN_FAILURE 7, LOGIN_SUCCESS 1   (§10.6)
`make admin-local` LEVE le verrou, sans toucher au mot de passe
mot de passe change — le nouveau passe, l'ancien non
`changement_exige` est retombe a false
aucun mot de passe dans les journaux, ni en clair en base
```

> **Ce que `admin-check` ne prouve PAS, et il le dit.** Le relâchement **après quinze minutes** n'est
> pas éprouvé là : l'API lit l'horloge réelle, et l'attendre coûterait quinze minutes à chaque
> exécution. Cette moitié est éprouvée par
> `test_le_verrouillage_se_RELACHE_apres_quinze_minutes`, où l'instant est **injecté**. Le contrôle
> prouve l'autre moitié : que le déverrouillage manuel fonctionne sur la stack réelle.

---

## 8. Six défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T5-1` | `RETURNING id` rendait l'identifiant **et** le tag `INSERT 0 1` : `psql()` fusionne les deux flux à dessein, et la requête suivante répondait « invalid input syntax for type uuid » | première exécution du provisionnement sur la stack réelle. Aucun script précédent n'employait `RETURNING` |
| `T5-2` | Quatre tests de service et cinq du jeu de recette ont échoué sur la nouvelle vérification du §8.4 | `uv run pytest`, et **ils avaient raison** — le jeu attribuait `dg` par un DSM |
| `T5-3` | Deux tests comptaient **toute** la table `framework_responsibility_assignment` : le décor y pose désormais la responsabilité ESM de l'attributeur | mêmes exécutions. Le compte n'a pas été relâché mais **rendu exact**, sur `DSM` |
| `T5-4` | Mon contrôle comparait le premier refus **à lui-même** : le comparateur exige que les identifiants de corrélation diffèrent, et il avait raison de le signaler | première exécution de `make admin-check` — un faux positif sur du code conforme, §7.20 |
| `T5-5` | Le nettoyage de `admin-check` ne pouvait pas atteindre les `LOGIN_FAILURE` **sans personne** | comptage du résidu après la batterie : **4** lignes |
| `T5-6` | Le nettoyage de `magic-link-check` **nommait** `MAGIC_LINK_REQUESTED` : `T4` avait ajouté des `LOGIN_FAILURE` sans personne, qu'il ne voyait pas | même comptage : **2** lignes. Le type n'est plus nommé, seule la borne temporelle délimite |

**`T5-5` et `T5-6` sont `T3-3` et `T4-5` pour la troisième et la quatrième fois.** La classe est
maintenant claire, et elle mérite d'être écrite en une phrase : **la trace d'un refus sans personne
échappe à tout nettoyage fondé sur l'identité.** Quatre contrôles l'ont rencontrée, chacun à sa
manière, et chacun a été corrigé séparément. `T5-6` ajoute la variante `ECART-021` : le filtre
**nommait un type d'événement**, et il a vieilli au premier ajout d'un autre.

**`T5-4` est le §7.20 dans sa forme la plus nette** : un contrôle qui échoue sur du code conforme ne
doit pas être affaibli, il doit être rendu **exact**. Le comparateur avait raison — c'est son usage
qui était faux.

---

## 9. Ce qui n'est PAS couvert

- **la session.** Aucune, et c'est explicite : `ReponseDeConnexion` ne porte ni cookie ni jeton.
  `T6`, `US004` ;
- **la limitation de débit** sur la connexion. `T8`. Une adresse **sans compte** ne fait avancer
  aucun compteur — le compteur vit sur `user_account`, et sans compte il n'existe pas. C'est la
  limitation par **origine** qui couvre ce cas, et elle est de `T8` ;
- **le rehachage automatique** quand les paramètres sont durcis. `parametres_a_durcir` rend
  l'information au seul instant où le mot de passe en clair est disponible, mais **`T5` ne rehache
  pas** : écrire pendant une lecture mérite sa propre décision ;
- **la politique de mot de passe.** `QO-118`, et le plancher actuel est déclaré comme
  recommandation ;
- **le relâchement après quinze minutes sur la stack réelle.** Éprouvé par test, non par
  `admin-check`. Voir §7 ;
- **les trois autres types d'événement du §10.6.** `T5` en produit quatre ; `MAGIC_LINK_*` viennent
  de `T3` et `T4`, `SESSION_REVOKED` de `T9`. L'exhaustivité est de `T12` ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 10. Ce que `T6` devra savoir

1. **`authentifier_un_administrateur` et `consommer_un_magic_link` rendent tous deux un identifiant
   de personne, et aucun accès.** C'est exactement le point de raccord : `T6` attache la session aux
   deux, sans rien changer aux deux services.
2. **`LOGIN_SUCCESS` est tracé à la connexion administrateur, PAS à la consommation d'un magic
   link** — parce que rien n'y est encore connecté. Quand `T6` créera la session, c'est là qu'un
   `LOGIN_SUCCESS` de magic link deviendra légitime. Ne le dédouble pas côté administrateur.
3. **Le préfixe `oss_` est déjà réservé** pour les jetons de session, dans
   `observabilite.masquage` : rien à ajouter au filtre ni à `.gitleaks.toml`. Mais **éprouve-le** —
   une règle déclarée et jamais exercée est une règle dont on ne sait pas si elle marche.
4. **Le compare-et-pose atomique est un patron, et il a servi deux fois.** `T6` en aura besoin une
   troisième : le rafraîchissement de `last_activity_at` sous requêtes concurrentes, et la
   révocation. **Éprouve-les sous concurrence** : les tests séquentiels ne voient pas cette classe de
   défaut, `T4` et `T5` l'ont mesuré deux fois.
5. **`must_change` est remonté par la route de connexion.** Un écran qui l'ignorerait laisserait un
   administrateur travailler avec un mot de passe provisoire ; `T11` doit le consommer.
6. **`make admin-local` est ton point d'entrée pour tester.** Elle crée ou déverrouille, et son mot
   de passe s'affiche une seule fois.
