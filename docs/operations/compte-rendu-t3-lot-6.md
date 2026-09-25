# Compte rendu — `T3` du LOT 6 : les cercles en lecture

**Sous-étape :** la troisième du lot · **Date :** 14 septembre 2026
**Décision :** `DEC-582` · **Story :** `MVP-L06-US002`, issue `#147`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faites | `T1`, `T2`, **`T3`** |
| Restent | `T4` à `T12` |

---

# 2. Ce que la sous-étape a produit

| Fichier | |
|---|---|
| `apps/api/app/shared/pagination.py` | **nouveau** — la pagination du §18.2, une seule déclaration pour le projet |
| `apps/api/app/organization/cercles.py` | le service de lecture, membres paginés |
| `apps/api/app/organization/routes.py` | `GET /entities/{code}/circles/{code_cercle}` |
| `packages/contracts/src/cercles.ts` | la forme partagée, lue du manifeste |
| `apps/api/tests/test_cercles.py` | **31 tests** |
| `packages/contracts/src/cercles.test.ts` | **15 tests** |
| `infra/scripts/verifier-framework.py` | **étendu** de 13 à **21** contrôles |

**Aucune cible `make` nouvelle**, donc **rien à ajouter dans `ci.yml`.** C'est le bénéfice direct du
§7.27 : un second vérificateur aurait dupliqué le décor, la session et le ménage.

## 2.1 Un préalable qu'un import circulaire a imposé

**Les trois tailles du §18.2 vivaient dans `app/people/trombinoscope.py`**, posées en `T2` du LOT 5
parce que le trombinoscope était alors la seule liste paginée. `T3` en est le **second
consommateur**, et le §18.2 s'applique à elle : il s'intitule « Pagination », vit dans le chapitre
**API** du cahier, et ne nomme **aucune** ressource.

**Mais `app/organization` ne peut pas importer `app/people`.** Mesuré : `people` importe **déjà**
`app.organization.modeles` — `TypeAppartenanceCercle`, dans `trombinoscope.py` **et** dans
`ecriture.py`. L'import inverse fermerait le cycle.

| Issue | Ce qu'elle coûte |
|---|---|
| **dupliquer** | deux déclarations d'une même règle du cahier, et pire qu'une liste recopiée puisqu'il s'agit d'un **type** — §7.27 |
| **déplacer vers `shared`** | quatre fichiers à rediriger, tous mécaniques |

Le déplacement est retenu, et **ce projet l'a déjà fait** : `ETAT_LISTE` et `VISIBILITE_LISTEE` ont
migré vers `app/people/modeles.py` quand un import circulaire entre le trombinoscope et
`media/photo.py` a montré qu'elles n'appartenaient à aucun des deux.

> **Un fait du CAHIER se déclare dans `shared`, pas dans le premier module qui en a eu besoin.**
> Vérifié après coup : les **36 tests** du trombinoscope passent inchangés.

## 2.2 La visibilité est RÉUTILISÉE, jamais redéclarée

`ETAT_LISTE` et `VISIBILITE_LISTEE` sont importées de `app/people/modeles.py`, avec leur motif : le
§22.5 étape 5 « masquage du profil » n'est implémenté nulle part, donc un partant reste `published` ;
et un nouvel arrivant est `active` dès son arrivée avec un profil `draft`. **Les deux filtres sont
nécessaires**, et le vérificateur le prouve — voir §3.

## 2.3 La couleur n'est jamais seule, et c'est le MODÈLE qui l'exige

Le §8.1 porte, parmi les contraintes de `circle` : « **la couleur ne constitue jamais la seule
information visuelle** ». **Ce n'est donc pas qu'un critère de sortie de la roadmap.**

Et la propriété est tenue par la **structure** : `code` et `nom` sont obligatoires,
`jeton_de_couleur` est `str | None`. **Il n'existe aucune valeur de ce type où le jeton serait
présent et le nom absent** — §7.35, la propriété est portée par le type et non par un contrôle qu'on
pourrait retirer.

## 2.4 Ce que la route ne sert pas

**Un cercle archivé rend 404**, indistinguable des quatre autres causes. Le §10.2 porte bien une
ligne « Restaurer un cercle », donc une lecture d'archivé viendra — et elle aura sa **propre** route
avec sa propre grille de rôles, comme `fiche-archivee` au LOT 5 `T8`. Élargir celle-ci confondrait
deux droits que la matrice sépare (§7.41).

**Aucun contenu éditorial** : la page est structurelle, les blocs sont `T5`.

---

# 3. Contrôles exécutés

```text
make check              code=0   1 011 pytest (688 d'integration) · 467 Vitest
make framework-check    21 controles, 0 echec   ← a travers Caddy, vraie session
make parametres-check   36 partages legitimes, 0 faute
make typecheck · docs-check · icloud-verify                        tous code=0
```

> **ET LE `make check` DE CLÔTURE A TROUVÉ DEUX CHOSES QUE LES CIBLES PRISES UNE PAR UNE N'AVAIENT
> PAS DITES** — `ruff format` voulait rejoindre une expression sur une ligne de 98 caractères, et
> `mypy` refusait un `return` (défaut `T3-2`). **Le lancer en entier à la fin n'est pas une
> formalité** : c'est ce que la porte de la pull request lancera, et c'est le seul moment où l'on
> exerce les onze contrôles **ensemble**, dans l'ordre où `ci.yml` les appelle.

**Le témoin est exécuté dans les deux sens, et il porte sur ce qui compte.** J'ai retiré le filtre de
visibilité — une seule ligne de `WHERE` — et le contrôle a **échoué en nommant** :

```text
ECHEC  membres : total=3, natures=['principal', 'secondary'],
       noms=['Brouillon', 'Principale', 'Secondaire']
ECHEC : 1 controle(s) non conformes sur 21
```

Remis sain : **21 contrôles, 0 échec**. Le filtre fait donc un travail réel, ce n'est pas une
affirmation.

> **Le décor porte TROIS membres et c'est la troisième qui vaut.** Deux appartenances `active` +
> `published`, l'une **principale** l'autre **secondaire** — et une troisième dont le profil est
> `draft`. **Sans elle, un filtre de visibilité absent aurait donné exactement la même
> observation** : deux membres rendus.

---

# 4. Défauts trouvés — **trois**

## `T3-1` — `departed` exige une date de départ, et mon décor ne la posait pas

Le paramétrage `[departed]` a échoué sur `ck_entity_membership_depart_date_si_departed` :

```sql
CHECK (membership_state <> 'departed' OR departure_date IS NOT NULL)
```

**La contrainte a raison** : un partant sans date de départ n'existe pas. Le décor la respecte
désormais, et le commentaire dit pourquoi plutôt que de la contourner.

## `T3-2` — mon `return` rendait `Any` là où le type annonçait un `UUID`

`make typecheck` a refusé la fabrique d'appartenance, et le message nomme exactement la classe :

```text
apps/api/tests/test_cercles.py:163: error: Returning Any from function declared
to return "UUID"  [no-any-return]
```

`Connection.execute(...).scalar_one()` est typé `Any` : le rendre depuis une fonction annotée
`-> uuid.UUID` fait perdre le type **en silence pour tout appelant**, et `mypy` strict est là pour
ça (`DEC-442`).

**La correction n'est pas une invention : c'est l'idiome que ce dépôt emploie déjà — et le
périmètre a été DÉRIVÉ, pas estimé.** J'avais d'abord écrit « une quarantaine, et toutes portent
l'annotation » ; le relevé dit **96** fabriques `-> uuid.UUID` dans `apps/api/tests/`, et
**non, pas toutes** :

| Forme | Combien | Ce qu'elle fait | Exemple |
|---|---|---|---|
| `# type: ignore[no-any-return]` sur le `return` | **75** | **supprime** le contrôle | `test_appartenance.py::_entite` |
| `uuid.UUID(str(…))` autour de l'appel | **16** | **prouve** le type, sans suppression | `test_administrateur.py::_personne` |
| rend une variable **déjà** typée | **5** | rien à suppléer | `test_depots_et_services.py::_esm` |

**Les deux premières sont des partis différents, et la seconde est la plus stricte** : elle
construit réellement un `UUID` au lieu de faire taire `mypy`. J'ai retenu la **première**, et pour
une raison de forme et non de goût — la classe majoritaire à **75 sur 96**, et surtout le
**précédent de forme identique** : `test_historique.py:286` lie aussi son identifiant parce qu'un
second `INSERT` s'en sert, exactement comme ma fabrique. Introduire la forme stricte dans ce seul
fichier aurait posé un **troisième** usage sans décision. *Que la forme stricte existe dans ce dépôt
est noté ici plutôt que tranché* : c'est une hygiène de suite, pas de `T3`.

**Pourquoi ce défaut n'a pas été vu plus tôt** : ma fabrique liait d'abord l'identifiant — elle en a
besoin pour l'`INSERT` dans `circle_membership` — si bien que le `return` s'est retrouvé **sans** le
commentaire que les autres portent. C'est le §7.27 sous un jour inhabituel : non pas une liste
recopiée, mais un idiome du dépôt **que ma variante de forme a fait sortir du motif**.

## `T3-3` — j'ai écrit dans `CLAUDE.md` une commande que je n'avais pas lancée TELLE QU'ÉCRITE

Le §1 annonce « LOT 6 : 6 défauts », et il annonce aussi la **commande qui produit ce nombre** —
c'est la règle de ce tableau. La commande large du §7 **sur-compte** : elle relève tout marqueur
`Tn-m`, y compris ceux d'un autre lot cités comme précédent. J'ai donc écrit la commande exacte,
en `python3 -c "…"`. **Je l'avais mesurée sous une autre forme, pas sous celle-là.** Extraite du
document et lancée :

```text
/tmp/cmd.sh: line 2: Td+-d+: command not found
  File "<string>", line 7
    d |= {m for m in re.findall(r'\', f.read_text()) if m.split('-')[0] == f'T{n}'}
                                                                             ^
SyntaxError: invalid syntax
code=1
```

**Les accents graves du motif — ceux qui entourent `` `T3-1` `` dans les comptes rendus — sont
interprétés par le SHELL** avant que Python ne voie quoi que ce soit : il tente d'exécuter
`Td+-d+` comme une commande, puis livre à Python un motif amputé. La forme retenue est un
**heredoc `<<'PY'`**, dont le délimiteur cité empêche toute substitution — et le nombre en est
**dérivé**, `6`, avec la liste des six.

> **C'est le §7.2 une cinquième fois, dans un costume que je n'avais pas vu venir** : non pas une
> espace dans un chemin, mais un **accent grave dans un motif**. Même cause — du texte qui traverse
> le shell alors qu'il devait arriver tel quel — et même parade : *ne fais pas traverser le shell à
> ce que tu veux passer littéralement*. Et c'est le §7.11 dans sa forme la plus nue : **vérifie ce
> que la documentation affirme, y compris quand c'est toi qui viens de l'écrire, et vérifie-la dans
> la forme EXACTE où tu l'as écrite.** Une commande mesurée « sous une autre forme » n'est pas une
> commande mesurée.

**La parade posée dans le dépôt n'est pas la correction, c'est la MÉTHODE** : la commande a été
**re-extraite du document par un script** et relancée, et c'est ce geste — extraire, puis exécuter —
qui l'a attrapée. Une relecture aurait confirmé ce que je croyais (§7.40).

---

> **Et deux pièges déjà payés ont été ÉVITÉS cette fois**, parce qu'ils sont désormais outillés ou
> écrits : `email_normalized` en minuscules — défaut `T2-1` — et **un paramètre lié par colonne**,
> que `make parametres-check` refuserait maintenant. La différence entre une leçon écrite et une
> leçon outillée est exactement celle-là.

---

# 5. Ce que `T3` laisse

| Point | Où il va |
|---|---|
| **La page détaillée d'un bureau** | `T4`, et avec elle le **déclencheur** du comptage borné « un à trois responsables actifs », que `DEC-576` rattache à la publication de la page de contenu |
| **La lecture d'un cercle archivé** | avec la restauration du §10.2. **Sa propre route**, comme `fiche-archivee` — élargir celle-ci confondrait deux droits |
| **Aucun contenu éditorial** | `T5`. La page est structurelle |
| **`QO-119`** | Léa, avant `T11` — le vocabulaire des blocs |
| **`QO-120`** | Jonathan et Léa, avant `T8` — la liste des protocoles d'URL |
