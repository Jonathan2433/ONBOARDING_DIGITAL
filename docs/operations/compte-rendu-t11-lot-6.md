# Compte rendu — `T11` du LOT 6 : le modèle générique, l'amorçage et la reprise relue

# 1. État du lot

LOT 6 — Framework, cercles, bureaux et contenus éditoriaux. Découpage validé le 13/09/2026
(`DEC-575`), douze sous-étapes. `T1` à `T10` faites. `T11` livre `MVP-L06-US007` et clôt le
**dernier** critère de sortie du lot qui restait à prouver — le critère 2, « le modèle générique
ne contient aucune donnée locale ». Les six autres critères étaient déjà prouvés par `T1` à `T10` ;
seul le septième, la démonstration guidée de Jonathan pour la porte `G6`, reste hors du périmètre
d'une sous-étape.

Trois questions bloquaient encore `T11` la veille : `QO-119`, `QO-123`, `QO-124`/`ECART-062`.
Toutes trois closes par arbitrage de Jonathan le 25/09/2026, avant `T11` (`DEC-592` à `DEC-594`) —
**aucune des trois ne change une ligne de code**, les trois confirment ce que `T6`/`T10` servaient
déjà. `QO-121` reste ouverte, par report **explicite** de Jonathan, non par oubli : les champs de
chaque bloc ne sont pas un choix unique mais onze petites décisions à écrire type par type.

# 2. Ce que la sous-étape a produit

## 2.1 Le témoin du critère de sortie 2 — une entité générique, sans aucun décor

La fiche nomme le piège directement : « le générique et le local se ressemblent — le critère 2 se
satisfait tout seul si le générique est vide et le local jamais créé ». Un décor jamais peuplé
passerait n'importe quel contrôle sans rien prouver.

`make framework-check` crée donc, en plus du décor existant, une entité **GÉNÉRIQUE** — active,
ville `Nantes`, sans aucun cercle, aucun bureau, aucune page — et interroge, à travers Caddy,
`/entities/{code}/framework` et `/entities/{code}` pour elle. Les octets servis sont cherchés pour
la chaîne `bordeaux`, insensible à la casse — pas la réponse JSON désérialisée, les octets HTTP
réels après Caddy, exactement ce que la fiche nomme.

**Sans un second contrôle, le premier ne prouverait rien** (§7.39) : une recherche cassée et une
recherche juste rendraient la même observation sur une entité qui n'a jamais contenu la chaîne
cherchée. L'entité active du décor de `T2` porte `city = 'Bordeaux'` depuis l'origine — un fait du
décor, pas une fuite — et sert donc de témoin positif : la même recherche, sur cette entité, doit
trouver `bordeaux`. Un troisième contrôle exige enfin que la forme générique soit **présente et
vide** — les quatre responsabilités du §6.2, zéro cercle, zéro bureau — et non absente : ce n'est
pas l'absence de réponse qui est exigée, c'est une réponse qui dit vide, même motif que
`test_les_trois_familles_sont_TOUJOURS_presentes_meme_vides` de `test_framework.py`, mais à
travers la pile réelle.

`make framework-check` passe de **74 à 77** contrôles.

## 2.2 Le contrôle a été mis en échec délibérément, avant d'être retenu

Un contrôle neuf n'est pas prouvé par sa seule réussite (§7.0). La ville de l'entité générique a
été changée en `'Bordeaux'` le temps d'une exécution : le contrôle 75 est tombé, pour la bonne
raison — `fuite=True` dans le message d'échec, pas un code muet. Restauré, `make framework-check`
revient à 77/77.

## 2.3 La reprise relue — le texte de présentation d'eXalt Bordeaux

`docs/prototype/V1.html` porte, dans sa fonction `BordeauxPresentation`, un paragraphe de
présentation entièrement rédigé :

> « eXalt Bordeaux rassemble des profils complémentaires autour d'une culture collaborative,
> humaine et orientée terrain. Cette page sert de repère onboarding pour aider les nouveaux
> arrivants à comprendre l'organisation locale, identifier les bons interlocuteurs et découvrir
> les cercles d'expertise. »

Ce texte est repris **verbatim** — aucune reformulation — dans le contenu `HOME`/`presentation` de
l'entité `BORDEA00`, qui n'avait **aucune** page avant cette sous-étape (mesuré : zéro ligne dans
`content_page` pour cette entité). La création, l'écriture et la publication passent par l'API
existante depuis `T6` et `T7` : **aucune ligne de code nouvelle côté écriture**. C'est le produit
déjà livré qui sert de véhicule, exactement ce que `US007` demande d'éprouver.

Aller-retour réel, à travers Caddy, session `demo.client@exemple.test` :

1. `POST /entities/BORDEA00/pages` — `201`, page créée en `draft`, version 1
2. `PUT /entities/BORDEA00/pages/{page}/contenu` — `200`, un bloc `TITLE` et un bloc `RICH_TEXT`
   portant le texte ci-dessus mot pour mot, version 2
3. `POST /entities/BORDEA00/pages/{page}/publication` — `200`, `état: published`, version 3
4. `GET /entities/BORDEA00/pages/HOME/presentation` — `200`, les octets exacts du prototype
5. Vérification visuelle réelle dans le navigateur, à travers Caddy : « État : Publiée — version 3 »,
   les deux blocs affichés

**L'attribution au propriétaire est structurelle, pas ajoutée pour l'occasion** — `created_by_person_id`
et `updated_by_person_id` sur `content_page` existent depuis le LOT 2 (`ChampsCommuns`, §3.1) et
pointent tous deux, mesuré en base, la personne authentifiée qui a écrit et publié la page.

## 2.4 Ce que `T11` ne fait pas

`ECART-015` nomme ce que le prototype ne fournit pas : ni description de cercle, ni lien interne.
`T11` n'en invente aucun — ce sont des contenus à produire par Léa, pas à halluciner (§6.5). Un
second texte existe dans le prototype, pour un bureau (« Le BDE crée des moments inoubliables… ») ;
il n'est **pas** repris ici, faute d'un besoin exprimé au-delà du critère de sortie du lot —
résiduel nommé, pas oublié.

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make framework-check` | **77** contrôles, 0 échec (+3 : générique, témoin, forme vide) |
| Contrôle 75 mis en échec délibérément (ville falsifiée) | tombe pour la bonne raison, `fuite=True` |
| `ruff format --check`, `ruff check` | 0 écart |
| `make docs-check` | vert, 6 séquences cohérentes |
| pytest complet vs `origin/develop`, même base, `git worktree` | **74 échecs sur 74, listes identiques** — zéro régression, pollution du jeu de démo |
| Aller-retour réel de la reprise relue (création → écriture → publication → lecture) | 201, 200, 200, 200 — octets exacts du prototype |
| Attribution du propriétaire, en base | `created_by_person_id` = `updated_by_person_id` = la personne authentifiée |
| Vérification visuelle réelle, navigateur, session `demo.client@exemple.test`, entité `BORDEA00` | « État : Publiée — version 3 », les deux blocs affichés |

# 4. Décisions, écarts et questions

- `DEC-595` (détail complet dans `docs/decisions/registre-decisions.md`)
- `QO-119`, `QO-123`, `QO-124`/`ECART-062` : closes avant `T11` (`DEC-592` à `DEC-594`)
- `QO-121` : reste ouverte, report explicite de Jonathan

# 5. Ce que `T11` laisse

- Le texte de bureau du prototype (BDE), non repris — résiduel nommé au §2.4
- `QO-121` bloque toujours un écran qui proposerait la création d'un bloc ou l'édition de ses champs
- `T12` — recette, §30 et checklist `G6` — est la dernière sous-étape du lot

# Validation demandée à Jonathan

`T11` est prête. `make check` vert hors des 74 échecs environnementaux pré-existants (comparés
identiques à `origin/develop`), `make docs-check` vert, `make framework-check` 77/77.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
