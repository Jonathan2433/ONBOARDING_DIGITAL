# Compte rendu — LOT 3, sous-étape `T2`

**Les sept tables d'authentification du modèle §10**
**Stories :** les huit du lot en dépendent — `MVP-L03-US001` à `US008`
**Réalisée le :** 21 août 2026
**Décision produite :** `DEC-521`
**Migration produite :** `0012`

---

## 1. Ce que le modèle impose, et ce qu'il laisse ouvert

**Mesure d'abord**, avant d'écrire une ligne :

| Section | Ce qu'elle impose aux sept tables |
|---|---|
| §25.1, index uniques | **deux** : `magic_link_request(token_hash)` et `user_session(session_token_hash)` |
| §25.2, historisation | **aucune** |
| §25.3, clés composites | **aucune** |
| §25.4, règles inter-tables | **aucune** |

**Aucune contrainte d'exclusion n'est donc posée**, et le mixin `Periode` n'est pas employé : ces
tables n'ont pas de période de validité au sens du §25.2. En poser serait **exiger plus que le
modèle** — le défaut du §7.20, qu'un contrôle de `T8` du LOT 1 avait déjà illustré.

---

## 2. « À prévoir notamment » — quatre unicités de plus, toutes dérivées

Le §25.1 s'ouvre par **« À prévoir notamment »** : la liste est **explicitement non exhaustive**.
Ajouter est donc permis, à condition de **dériver d'une règle écrite** et non d'inventer — §6.5.

| Unicité ajoutée | Règle dont elle est dérivée |
|---|---|
| `user_account(person_id, account_type)` | §10.1 : « un compte employé et, si nécessaire, un compte administrateur local **distinct** » |
| `admin_password_credential(user_account_id)` **partielle** | §10.2 : `revoked_at` implique qu'**au plus un** est actif |
| `magic_link_request(person_id)` **partielle** | §10.3 : « le dernier lien **invalide** les précédents encore actifs » |
| `service_token(token_hash)` | §10.5 : « un hash du jeton ». **Deux jetons de même empreinte rendraient l'authentification ambiguë** — défaut de sécurité, non préférence |

---

## 3. Le §10.3 décrit une ACTION, l'index porte son INVARIANT

C'est la distinction que `T10` du LOT 2 a établie, appliquée une seconde fois.

| Le modèle dit | Ce qui l'exécute | Ce que la base garantit |
|---|---|---|
| « le dernier lien invalide les précédents » | le service, `T4` | **au plus un lien actif par personne** |

**L'index ne fait pas l'invalidation : il la rend obligatoire.** Un service qui insérerait sans
invalider verrait son insertion refusée. C'est ce qui transforme un oubli possible en oubli
**impossible**, et c'est exactement le parti de `DEC-514`.

**Deux témoins l'établissent** : un nouveau lien est accepté après **invalidation**, et après
**consommation**. Sans eux, l'index pourrait passer pour une interdiction de réémettre.

---

## 4. Trois lectures du modèle, posées plutôt que supposées

**`person_id` est `NOT NULL` sur `user_account`.** Le §10.1 écrit « obligatoire pour les comptes
humains », ce qui laisserait croire à des comptes machine dans cette table — **mais les deux seules
valeurs de `account_type` qu'il déclare sont humaines**, et `service_account` existe pour les
machines. Ajouter un type machine ici serait une migration **et** une décision.

**Les sept types de `auth_event` sont nommés ici.** Le §10.6 les décrit **en français, sans
identifiant** : « succès, échec, magic link demandé… ». Les nommer est une dérivation, déclarée dans
la docstring de l'énumération, en casse majuscule comme les types du §10.1 et dans l'ordre du modèle.

**L'état de `service_account` écarte `locked`.** Le §10.5 dit « un état » sans l'énumérer. Un compte
machine n'a pas de mot de passe, donc rien à verrouiller après des échecs. L'élargir serait une
migration d'une ligne — doctrine `DEC-499`.

---

## 5. `make secrets-check` — et mon premier contrôle échouait sur mon propre code

La fiche exige : « **aucun mot de passe ni jeton en clair** dans une colonne, vérifié par contrôle ».

Le contrôle examine le **catalogue PostgreSQL**, pas de la prose — la distinction compte, parce que la
leçon `T12-2` du LOT 2 disait de chercher un **usage** et non un mot. Ici, **un nom de colonne n'est
pas un commentaire, c'est la déclaration elle-même** : une colonne nommée `password` *est* le défaut.

**Il a trouvé deux choses, et il avait tort sur l'une :**

- **`admin_password_credential.password_hash` était signalée** parce qu'elle n'est pas bornée à 64
  caractères. **Le contrôle avait tort** : une empreinte **argon2** est de longueur **variable**, elle
  embarque son sel et ses paramètres. Exiger 64 la rendrait impossible à stocker — §7.20 ;
- **`circle.color_token` était signalée** : c'est une **référence de couleur** du §8.1, et le motif se
  déclenche sur le mot « token ». Faux positif **nommé** plutôt que toléré — §7.25.

**Le contrôle distingue donc deux familles**, et le second critère est meilleur que le premier :

| Famille | Ce qui la rend vérifiable |
|---|---|
| empreinte de **jeton** | SHA-256 hexadécimal, **bornée à 64 caractères** |
| empreinte de **mot de passe** | la présence des colonnes `algorithm` et `parameters`, que le §10.2 exige |

**Vérifier la présence des colonnes d'accompagnement vaut mieux qu'une borne de longueur** : sans
elles, aucune vérification ne serait possible après un changement d'algorithme.

**Et les deux comptes du rapport final sont distincts, non additionnés** : 3 empreintes de jeton
bornées, 1 empreinte de mot de passe accompagnée, 1 exception déclarée. Les totaliser produirait un
nombre qui ne veut rien dire — sixième proposition du §7.0.

---

## 6. Le point de passation de `T1`, vérifié sur les tables réelles

`T1` demandait : « un test devra vérifier que les tables de `T2` sont **immédiatement lisibles** par
l'exécution, **pas seulement sur une table jetable** ».

**Mesuré : 7/7 tables lisibles par le rôle d'exécution, sans aucun `GRANT` explicite.** Les privilèges
par défaut posés en `T1` fonctionnent sur les tables réelles. C'est la différence entre « le mécanisme
fonctionne » et « il a fonctionné pour celles-là ».

---

## 7. Un test inversé, et c'est la bonne façon de le faire

`test_AUCUNE_table_d_authentification_n_existe`, écrit en `T3` du **LOT 2**, prouvait l'interdit du
lot : « créer une seule table d'authentification » figurait au §11 de sa fiche.

**`T2` l'a rendu faux délibérément.** C'est le §7.21 dans sa forme la plus pure — un contrôle ne
devient pas faux tout seul, il le devient quand le monde change autour de lui, et ici le changement
**est** le livrable.

**Le supprimer aurait perdu son information.** Il exige désormais la **présence** des sept, et **le
compte est dérivé** de la déclaration du module `auth` : une huitième table apparaîtrait sans
décision, et ce test la nommerait.

---

## 8. `autogenerate` était fidèle, et cela confirme la rectification de `DEC-500`

`DEC-500` pose qu'`autogenerate` est un **brouillon, jamais un livrable**. Mesure du 21/08/2026 : sur
des tables **neuves**, il a rendu les **12** contraintes de vérification, les **2** clauses `WHERE`
des index partiels, et un ordre de création respectant les dépendances de clés étrangères.

**La rectification de `T4` du LOT 2 est donc confirmée** : il rend fidèlement à la **création**, et
c'est la **détection de dérive** ensuite qui lui échappe. Ce qu'il a fallu corriger : la révision
`4bc9ac468e8a` renommée `0012`, et l'en-tête.

---

## 9. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make migrate` | **code 0** — `0012 (head)`, appliquée par le rôle de migration |
| `alembic check` | « No new upgrade operations detected » — modèle et base concordent |
| `make migrations-check` | **code 0** — base vide, chaîne rejouée, schéma **comparé** |
| `make secrets-check` | **code 0** — 375 colonnes examinées, 5 évoquant un secret, toutes justifiées |
| `make privileges-check` | **code 0** |
| `make isolation-check` · `isolation-temoin` | **code 0** · **code 0** |
| `make historisation-check` · `recette-modele-check` | **code 0** · **code 0** |
| `uv run pytest` | **415 tests, 0 échec** — 390 avant `T2` |
| `make check` | **code 0** |

**Les 25 tests nouveaux** couvrent les quatre unicités dérivées **avec leurs témoins**, les
contraintes de vérification, les sept types d'événement, et la lisibilité des sept tables par le rôle
d'exécution.

---

## 10. Quatre défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T2-1` | Mon contrôle des secrets exigeait **64 caractères d'une empreinte argon2**, de longueur variable | sa première exécution, sur mon propre code |
| `T2-2` | Le même contrôle signalait **`circle.color_token`**, une référence de couleur | même exécution |
| `T2-3` | `isolation-check` portait une **liste recopiée** de 4 tables globales — `T2` en a ajouté **six** | `isolation-check`, après la migration |
| `T2-4` | La détection d'exception de `isolation-check` exigeait un titre de section **à un seul nom** ; le §10.5 en nomme **deux** | même exécution |

**`T2-3` est la deuxième fois en deux sous-étapes qu'une liste recopiée de ma main vieillit au premier
ajout** — la première était `verifier-images.py` en `T1`. Les deux sont désormais **dérivées** : le
critère de « légitimement globale » est *« la section du modèle qui décrit cette table ne mentionne
pas `entity_id` »*, ce qui ne vieillit pas.

**`T2-4` a exigé un choix de méthode.** Le §10.5 déclare la nullabilité **en prose** — « une entité
facultative » — sans écrire `entity_id`. Élargir le motif sur du français aurait été **une heuristique
dans un contrôle**, défaut `T9-2`. Le rattachement est donc **déclaré**, comme `RELATIONS_ATTENDUES`
dans `verifier-historisation.py`, et le contrôle **exige que chaque entrée corresponde à une table
réelle** : une entrée devenue fausse échouerait au lieu d'être ignorée.

---

## 11. Ce qui n'est PAS couvert

- **l'usage unique d'un magic link** est une règle de processus : `used_at` ne se pose qu'une fois, ce
  qu'aucune contrainte de ligne n'exprime. **`T4`**, et l'invariant structurant est déjà là ;
- **la réponse générique anti-énumération** du §10.3 est une règle d'API, sans traduction en schéma.
  **`T3`** ;
- **l'expiration par inactivité de 7 jours** n'a pas de colonne, et ce n'est pas un oubli : elle se
  **calcule** sur `last_activity_at`. Une colonne divergerait de sa source dès la première mise à
  jour — motif de la colonne générée `period` en `T1` du LOT 2 ;
- **« aucun lien complet dans les logs »** est une règle d'observabilité. **`T4`**, et les trois
  barrières de `packages/observabilite` devront recevoir les formats que ce lot produit ;
- **`make secrets-check` n'inspecte aucune DONNÉE.** Une colonne correctement nommée et bornée pourrait
  recevoir une valeur en clair de 64 caractères : ce serait un défaut de **code**, que `T4` devra
  couvrir sur le service d'émission. Ce contrôle ferme la porte du **schéma**, pas celle du code ;
- **`§30.11` et `§30.22`** restent classés « reportés au LOT 3 » : `T2` crée les tables, `T3` et `T9`
  porteront les comportements. `make recette-modele-check` le vérifie.

---

## 12. Ce que `T3` devra savoir

1. **`T3` porte la demande de magic link**, `US001` — et son critère est une **égalité** : la réponse
   doit être identique pour une adresse connue et inconnue. **Comparer le corps ET les en-têtes**, pas
   seulement le code HTTP : le §7 de la fiche le nomme comme risque de sécurité.
2. **L'index partiel de `magic_link_request` refusera un second lien actif.** Le service **doit** donc
   invalider le précédent avant d'insérer — ce n'est pas une option, c'est ce que la base impose.
3. **`§30.11`, « un profil archivé ne reçoit pas de magic link »**, devient acquis en `T3`, et
   `make recette-modele-check` **échouera** tant que son classement n'aura pas été mis à jour avec le
   test qui le prouve.
4. **`auth_event` accepte un événement sans personne**, et c'est délibéré : un échec sur une adresse
   inconnue doit pouvoir être tracé sans rattacher l'événement à une personne inexistante. C'est ce
   que la réponse générique protège.
