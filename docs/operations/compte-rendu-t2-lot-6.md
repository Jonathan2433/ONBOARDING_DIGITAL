# Compte rendu — `T2` du LOT 6 : la page Framework en lecture

**Sous-étape :** la deuxième du lot · **Date :** 13 septembre 2026
**Décision :** `DEC-579` · **Story :** `MVP-L06-US001`, issue `#146`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faites | `T1`, **`T2`** |
| Restent | `T3` à `T12` |

---

# 2. Ce que la sous-étape a produit

| Fichier | |
|---|---|
| `apps/api/app/organization/framework.py` | le service de lecture, trois familles |
| `apps/api/app/organization/routes.py` | `GET /entities/{code}/framework` |
| `packages/contracts/src/framework.ts` | la forme partagée, lue du manifeste |
| `apps/api/tests/test_framework.py` | **17 tests** |
| `packages/contracts/src/framework.test.ts` | **12 tests** |
| `infra/scripts/verifier-framework.py` | **13 contrôles** à travers Caddy |

`make framework-check` entre dans `ci.yml` : **une cible ajoutée à `make check` n'entre pas dans la
CI de ce projet** — §7.36, défaut `T1-5` du LOT 5.

## 2.1 Qui lit, et le piège que la seule annexe A aurait fait commettre

**La matrice §5 donne « Framework | `ANON` — | `EMP` Lecture | `NEW` Lecture | … » : huit rôles
authentifiés, sans distinction.** La route exige donc une session et **n'examine aucun rôle**,
exactement comme le trombinoscope de `T2` du LOT 5, dont la ligne du §5 est identique.

> **L'ANNEXE A §10.1 N'A NI COLONNE `EMP` NI COLONNE `NEW`.** Ses colonnes commencent à `DSM`. La
> lire seule aurait exclu **l'acteur que la story nomme** — « **Employé** : Découvrir le Framework ».
>
> C'est la forme exacte du piège de la colonne `OFFICE` au LOT 5 : **un tableau qui paraît faire
> autorité, et dont l'ensemble de colonnes est plus étroit que la question.** La parade n'est pas la
> vigilance, c'est de savoir **quel** tableau règle **quelle** question — le §5 règle la consultation,
> le §10.x règle la modification.

## 2.2 Le mot « catégories » n'est nulle part dans le document qui prévaut

Le backlog et la roadmap écrivent « **catégories** et responsabilités ». **Mesure du 13/09/2026 : ce
mot ne vit que dans ces deux documents dérivés et dans la copie qu'en fait l'annexe C.** Le cahier
§10.3, qui **prévaut**, écrit « des pages détaillées pour : les **responsabilités** ; les **cercles** ;
les **bureaux** ».

La lecture qui réconcilie est au §6.2 : « Responsabilités Framework : DSM ; ESM ; Booster ;
responsable de bureau ». **Ce sont les catégories.** Et l'annexe A §10.1 le confirme en donnant à
`DSM` et `ESM` leurs propres pages — « Modifier la page DSM », « Modifier la page ESM » — tandis que
les deux autres se rejoignent **par** les cercles et les bureaux. D'où exactement les trois familles.

> **`chemin_detaille` vaut donc `null` pour `BOOSTER` et `OFFICE_MANAGER`**, et `null` n'est pas une
> chaîne vide : vide dirait « la page existe, son adresse est inconnue ». C'est la leçon `null` ≠ `[]`
> de `T9` du LOT 5, transposée.

## 2.3 La couleur n'est jamais l'unique information, et c'est structurel

Le critère de sortie n°4 du lot est tenu par la **structure** et non par un contrôle qu'on pourrait
retirer : `code` et `nom` sont obligatoires sur un cercle, `jeton_de_couleur` est `string | null`.
**Il n'existe aucune valeur de ce type où le jeton serait présent et le nom absent** — §7.35.

---

# 3. Contrôles exécutés

```text
make check              code=0
make framework-check    13 controles, 0 echec   ← a travers Caddy, vraie session
make typecheck          code=0
make docs-check         code=0
```

**Le témoin du contrôle de stack est exécuté DANS LES DEUX SENS.** Le défaut `T10-8` a été
réintroduit — `str(ligne[4])` au lieu de la garde — et le contrôle **a échoué en le nommant** :

```text
ECHEC  jeton : avec='bleu', sans_a_null=False, « None » dans les octets = True
ECHEC : 1 controle(s) non conformes sur 13
```

Remis sain : **13 contrôles, 0 échec**. Un contrôle qui ne peut pas échouer ne prouve rien.

---

# 4. Défauts trouvés — **deux**, et le second est dans mon propre contrôle

## `T2-1` — `email_normalized` doit être en minuscules, et mon marqueur ne l'était pas

Six tests d'intégration ont échoué sur
`ck_person_email_normalise_en_minuscules`. Mon marqueur est `L6T2`, en majuscules, et je le passais
tel quel dans les deux colonnes.

**Ce n'est pas une gêne, c'est le garde-fou qui fait son travail** : la normalisation d'une adresse
n'est pas décorative, elle est ce qui rend l'unicité fiable. Le décor la respecte désormais, et le
commentaire dit pourquoi.

> **Et le piège du §7.25 a été ÉVITÉ cette fois**, parce que `T1` venait de le payer : les
> helpers de ce fichier passent **un paramètre par colonne**, jamais un paramètre partagé entre une
> colonne `varchar` et une colonne `text`.

## `T2-2` — mon nettoyage échouait en SILENCE, et neuf tests sans rapport sont tombés

`make check` a rendu **9 échecs** dans `test_authentification.py`, `test_personnes.py` et
`test_jeu_de_recette.py` — des fichiers des LOTS 2 et 3, que `T2` ne touche pas. **Aucun des neuf
messages ne nommait la cause** ; l'un disait « `MultipleResultsFound` », un autre « une donnée du jeu
ressemble à une adresse RÉELLE ».

**Trois personnes de mon vérificateur étaient restées en base**, et leur adresse porte le domaine
autorisé — donc un domaine réel. Deux causes, et la seconde est la vraie :

| Cause | Mesure |
|---|---|
| mon `DELETE` visait `user_session WHERE user_account_id IN (…)` | **cette colonne n'existe pas** : `user_session` est rattaché par `person_id` |
| **mon nettoyage ne lisait pas son code de sortie** | le `DELETE` errait, et l'échec était **invisible** |

**La seconde est le vrai défaut**, et c'est le §7.3 : *un contrôle dont on ne lit pas le code de
sortie ne prouve rien.* Je l'ai écrit dans un fichier neuf, en 2026, après sept occurrences
documentées de cette classe.

**Le nettoyage lit désormais chaque code et NOMME la table qui résiste.** Ce qui l'a prouvé
immédiatement : à la première exécution corrigée, il a rendu

```text
ECHEC  nettoyage de `user_account` : violates foreign key constraint
       "fk_auth_event_user_account_id_user_account" on table "auth_event"
```

— un **second** défaut d'ordre, que la version silencieuse aurait laissé passer. `auth_event`
référence la personne **et** son compte : il se supprime avant `user_account`. Après correction :
**13 contrôles, 0 échec, 0 résidu**.

> C'est la huitième occurrence de la classe §7.30 — « un nettoyage incomplet fait échouer des tests
> sans rapport » — et `make residu-check` existe précisément pour la dire. Il aurait nommé la table
> et l'écart ; c'est `make check` qui a parlé le premier, en neuf messages muets sur la cause.

---

# 5. Ce que `T2` laisse

| Point | Où il va |
|---|---|
| **Les pages détaillées des cercles et des bureaux** | `T3` et `T4`. `T2` sert leur **chemin** ; que la cible n'existe pas encore ne rend pas l'adresse fausse |
| **Le déclencheur « un à trois responsables actifs »** | `T4`. `T2` rend ce qui est, **zéro compris**, et `DEC-576` dit à partir de quand la borne mord |
| **Aucun contenu éditorial** | `T5`. La synthèse est structurelle |
| **`content_page` de type `DSM` ou `ESM`** | **à instruire en `T5`** : le §15.1 énumère `HOME`, `FRAMEWORK`, `CIRCLE`, `OFFICE`, `LEGAL` et « autre type contrôlé », et **aucun de ces cinq ne désigne la page DSM ni la page ESM** que l'annexe A §10.1 exige. La formule « autre type contrôlé » autorise l'ajout ; le **choix** reste à faire |
