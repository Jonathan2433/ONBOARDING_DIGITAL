# Guide de présentation — démonstration client

Ce guide prépare et déroule une démonstration locale d'Onboarding Digital. Toutes les personnes,
adresses et organisations ajoutées par ce décor sont fictives. Les adresses utilisent le domaine
réservé `exemple.test` et aucune photographie réelle n'est chargée.

## 1. Préparer la démonstration

### Vérifier que le développement est bien présent

Une branche Git créée avec `git branch demo` part uniquement du commit actuellement extrait : elle
ne récupère pas le développement de démonstration. Avant de démarrer Docker, vérifie donc que les
cibles ont réellement été intégrées dans ta révision :

```bash
make help | grep 'demo-'
```

La commande doit afficher `demo-init`, `demo-check`, `demo-info` et `demo-reset`. Si Make répond
`No rule to make target 'demo-init'`, la stack n'est pas en cause : le commit de démonstration n'est
pas dans la branche courante. Récupère et fusionne la pull request de démonstration, puis relance ce
contrôle. Ne crée pas une branche locale vide portant simplement le même nom.

### Première installation ou base déjà utilisée

Les tests d'intégration et le jeu de démonstration ne doivent pas partager une base peuplée. Pour
repartir proprement, puis préparer le décor :

```bash
make up
make migrate
make demo-reset
make demo-init
```

`make demo-reset` vide les tables applicatives de la base de **développement uniquement**. Il
conserve le schéma, les migrations, les volumes des autres services et l'autorité locale de Caddy.
Ne l'exécute pas sur une base contenant un travail à conserver.

`make demo-init` :

1. démarre les huit services locaux ;
2. applique les migrations ;
3. engendre 25 entités et 5 000 profils fictifs ;
4. transforme huit profils de Bordeaux en personas stables et pose l'identité fictive du compte
   de démonstration ;
5. reconstruit les services applicatifs ;
6. crée le compte `demo.client@exemple.test` ;
7. affiche un mot de passe temporaire, qui n'est jamais enregistré ;
8. vérifie le décor et imprime les URL utiles.

Copie le mot de passe dans un gestionnaire temporaire ou garde le terminal ouvert. Si tu le perds,
relance `make demo-init` **après** `make demo-reset` : un nouveau mot de passe sera produit.

### Contrôle juste avant le rendez-vous

```bash
make demo-check
make stack-check
make demo-info
```

Ouvre l'application dans Safari, Chrome ou Edge. Firefox utilise son propre magasin de certificats
et peut afficher un avertissement sur l'autorité HTTPS locale.

## 2. Conducteur conseillé — 10 à 15 minutes

### Étape 1 — Connexion

Ouvre `https://app.onboarding.localhost/connexion/administrateur`.

- Identifiant : `demo.client@exemple.test`
- Mot de passe : celui affiché par `make demo-init`

**À dire :** « L'accès est réellement contrôlé par l'API. Le navigateur ne stocke aucun jeton de
session dans son stockage durable. »

Après le message de succès, ouvre manuellement `https://app.onboarding.localhost/` : la version
actuelle n'effectue pas encore de redirection automatique.

### Étape 2 — Portail national

Montre la carte et les entités actives, puis choisis **eXalt Bordeaux 0**.

**À dire :** « Le produit est multi-entités dès sa fondation. La carte ne rend que les entités
actives et l'entité consultée reste visible dans tout le cadre applicatif. »

### Étape 3 — Navigation et permissions

Sur `/entites/BORDEA00`, montre :

- l'entité active ;
- le sélecteur d'entité ;
- la navigation principale ;
- la rubrique Administration visible pour le compte super-administrateur.

**À dire :** « Le frontend adapte la navigation, mais l'API reste l'autorité finale. Masquer un
bouton n'est jamais considéré comme une protection. »

### Étape 4 — Trombinoscope

Ouvre `/entites/BORDEA00/trombinoscope`.

Montre successivement :

1. la pagination ;
2. les cartes collaborateurs ;
3. les métiers, statuts, clients et cercles ;
4. le nom du cercle et sa bordure colorée ;
5. le retournement d'une carte au clic ;
6. le même retournement avec `Tab`, puis `Entrée` ou `Espace`.

**À dire :** « La couleur n'est jamais la seule porteuse d'information : le nom du cercle reste
écrit. Les cartes utilisent un bouton natif, utilisable à la souris, au toucher et au clavier. »

### Étape 5 — Recherche

Recherche `Alice`, puis `alice`.

Ouvre la carte **Alice Martin**. Le jeu est déterministe : Alice porte toujours l'adresse fictive
`demo.alice.martin@exemple.test` et dispose d'une présentation et d'une anecdote.

Tu peux également montrer la recherche sans accents avec `ber`, puis `bér` : les résultats doivent
être identiques.

**À dire :** « La recherche normalise la casse et les accents des deux côtés. Elle attend la fin de
la saisie pour éviter une requête à chaque frappe. »

### Étape 6 — Fiche profil

Clique sur **Voir plus** pour Alice Martin.

Montre :

- l'identité ;
- la présentation courte ;
- le fun fact ;
- le métier et la situation professionnelle ;
- le cercle principal ;
- les responsabilités ;
- les cinq axes d'historique.

**À dire :** « La fiche agrège plusieurs dimensions historisées sans écraser les affectations
précédentes. Les périodes se succèdent et les chevauchements interdits sont bloqués en base. »

### Étape 7 — Cycle de vie

Sur un profil autre qu'Alice si tu veux conserver le profil vedette visible :

1. clique **Archiver ce profil** ;
2. lis la conséquence annoncée avant confirmation ;
3. confirme ;
4. constate que le profil quitte le trombinoscope ;
5. ouvre à nouveau sa fiche depuis l'historique du navigateur ;
6. clique **Restaurer**.

**À dire :** « L'archivage révoque les sessions et clôt les affectations. La restauration ne
réinvente pas l'organisation passée : elle nomme ce qui n'a pas été rouvert. »

### Étape 8 — Fin de session

Ouvre `/deconnexion`, puis retourne sur le trombinoscope.

**À dire :** « La protection ne dépend pas du routeur React : après révocation de la session,
l'API refuse l'accès avec un 401. »

## 3. Limites à annoncer sans les masquer

- Les portraits sont volontairement remplacés par des avatars neutres. L'API sait servir une
  miniature autorisée, mais le pipeline qui les fabrique appartient à un lot ultérieur.
- Deux filtres sont visibles ; les quatre listes de référence supplémentaires ne sont pas encore
  exposées par l'API.
- La modification d'un profil existe côté API mais n'a pas encore d'écran.
- Les rubriques Framework, onboarding, événements et administration détaillée affichent encore
  leur état d'attente.
- Le changement de mot de passe imposé à la première connexion reste un écart connu de ce stade du
  produit.

Une démo crédible montre le produit présent ; elle ne simule pas les fonctions futures.

## 4. Plan de secours

| Symptôme | Action |
|---|---|
| `No rule to make target 'demo-init'` | la révision courante ne contient pas le développement ; fusionner ou extraire la pull request, puis vérifier avec `make help \| grep 'demo-'` |
| Mot de passe perdu | `make demo-reset && make demo-init` |
| Page servant un ancien frontend | `make code-refresh && make code-check` |
| Service indisponible | `make stack-check`, puis `make logs` |
| Certificat refusé | utiliser Safari, Chrome ou Edge et vérifier l'autorité Caddy locale |
| Décor incomplet | `make demo-check` ; si échec, `make demo-reset && make demo-init` |
| Profil archivé par une répétition précédente | refaire le décor avec les deux commandes précédentes |

## 5. Après la présentation

Pour remettre la base dans un état vide compatible avec les tests d'intégration :

```bash
make demo-reset
make demo-check  # doit alors échouer : le décor n'existe plus
```

Le second échec est attendu. Relance ensuite les contrôles depuis une base vide selon le besoin du
développement.
