# Compte rendu — LOT 4, sous-étape `T10`

**Le piège du critère, et un message faux vu à l'écran**
**Story :** `MVP-L04-US006` · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-554` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. Le critère nommait un piège, et le §17.2 le résout

La fiche écrit : « un `fetch` qui échoue **après l'envoi** n'affiche **jamais** “sauvegardé” ». Or ce
lot est en **lecture seule** — il n'y a rien à sauvegarder. J'ai donc cherché la section dédiée avant
de décider, comme le §7.29 l'apprend.

**Cahier §17.2, dernière phrase :**

> « Après perte de connexion sur une page déjà chargée, l'utilisateur voit un état explicite et
> **aucune action n'est déclarée enregistrée sans confirmation de l'API**. »

Le critère est donc la reformulation de cette phrase, et la règle est claire : **le succès doit venir
de la réponse**, jamais du fait d'avoir émis la requête. Et les écritures existent — ce sont celles
du LOT 3 : connexion, connexion administrateur, déconnexion, demande de magic link.

**Il n'y avait donc rien à inventer, et aucune question à poser.**

> **Et le §17.4 est plus exigeant que la fiche.** Elle écrit « l'identifiant de corrélation est
> **affiché** » ; le cahier écrit « identifiant de corrélation **copiable** ». Le cahier prévaut.
> C'est la classe de `ECART-023` — une fiche moins exigeante que sa source — et il valait mieux le
> voir avant d'écrire que de le découvrir en recette.

---

## 2. La règle est rendue MÉCANIQUE, pas testée

Un test par écran vieillirait au premier écran ajouté. `make cadre-check` porte donc un contrôle qui
confronte **deux ensembles dérivés du code** :

| Ensemble | Comment il est lu |
|---|---|
| les états qui rendent `data-ton='succes'` | de l'expression du ton, `=== 'X' ? 'succes'` |
| les états affectés **dans** un `catch` | des corps de `catch`, `setEtat('Y')` |

**Leur intersection doit être vide.** Un succès atteignable depuis un `catch` est littéralement une
action déclarée aboutie sans réponse de l'API.

**La mesure est exacte, pas heuristique** : elle ne cherche aucun mot dans aucun message — ce serait
la classe de défaut du §7.25. Et le contrôle **exige d'avoir trouvé les deux ensembles**, sinon un
fichier où l'extraction ne trouverait rien passerait en silence (§7.0) : il annonce
**3 écrans à état de succès, 3 avec `catch`**.

**Éprouvé en injectant le défaut réel :** `setEtat('connecte')` à la place de `setEtat('indisponible')`
dans le `catch` de la connexion administrateur — c'est-à-dire « une panne réseau déclare la session
ouverte ». Le contrôle a nommé **le fichier et l'état** :

```text
ECHEC    un etat de SUCCES est atteignable depuis un `catch` :
         ["PageConnexionAdministrateur.tsx : ['connecte']"]
```

---

## 3. Un message faux, vu à l'écran — le 401

**Ce défaut n'était dans aucun contrôle : il était dans le livrable, et seul le navigateur l'a
montré.** Ma session de démonstration avait expiré. L'API rendait **401**, et le cadre affichait :

> « L'entité n'a pas pu être chargée. **Cela ne dit rien de son existence** : le service a peut-être
> refusé la demande… »

**C'est faux.** L'utilisateur n'a pas un problème de chargement, il est **déconnecté** — et le remède
n'est pas « réessayer » mais « se reconnecter ». Un `else` attrapait 401 avec tout le reste.

Même classe que `T8-4` : le message était **plausible**, et rien ne pouvait le contredire sans le
regarder.

**Correction :** trois états distincts là où il y en avait un.

| État | Ce qu'il dit | Réessai ? |
|---|---|---|
| **hors connexion** | la connexion est perdue, et ce qui est affiché **date d'avant la coupure** | non — le retour de connexion recharge seul |
| **session expirée** (401) | reconnectez-vous ; *cette adresse vous ramènera à la même entité* | **non** — réessayer ne peut pas aboutir sans session |
| **erreur** | le service a refusé ou la réponse n'a pas abouti | **oui**, et il relance vraiment |

**Aucune redirection**, et c'est la règle déjà posée : `DEC-537` a tranché pour le 404 — « rend la
page **sans rediriger** » — parce que changer l'URL fait perdre l'adresse suivie. Ici cela compte
davantage : l'adresse porte **l'entité consultée**.

**Et le hors connexion n'est pas un alias de l'erreur.** `navigator.onLine` ne dit pas « le service
répond » : derrière un portail captif il rend `true`. Les confondre dirait à l'utilisateur de vérifier
sa connexion alors que c'est l'API qui est tombée — §7.6.

---

## 4. Le réessai est un bouton qui réessaie

Avant `T10`, le portail écrivait « vérifiez votre connexion, puis **réessayez** » — **sans rien pour
réessayer**. L'utilisateur devait recharger la page, ce qui lui fait perdre son contexte.

Une phrase qui demande une action que l'écran ne propose pas est de la famille de l'avertissement
faux du §7.21 : elle apprend à ne pas lire les messages.

Le bouton incrémente un compteur qui est **dans les dépendances de l'effet**, donc il relance les
**trois** appels avec un signal neuf. Même mécanisme que `PageStatut` depuis `T5` du LOT 1. Et le
**retour de connexion** le déclenche seul — c'est le §17.2, « l'utilisateur voit un état explicite »
et ce qu'il voyait est devenu obsolète à la coupure.

---

## 5. L'extraction porte sur la LOGIQUE, pas sur le balisage

`PageStatut` portait les deux mécanismes du §17.2 et §17.4 depuis `T5` du LOT 1 : l'écoute de
`online`/`offline`, et la copie du presse-papiers avec son repli. Le portail en avait besoin.

**Extraire un composant aurait imposé un balisage commun** — or les deux écrans n'ont pas la même
feuille : `PageStatut` emploie les classes neutres écrites avant que `packages/ui` existe. Les faire
converger est le travail de `T11`, qui consolide « les composants du design system que ces écrans
emploient ».

**Ce qui divergerait en silence est la logique** : le nettoyage des écouteurs, la remise à zéro de
l'état de copie, le repli quand le presse-papiers est refusé. Elle vit donc dans `apps/web/src/reseau.ts`,
en un seul exemplaire, et `PageStatut` la consomme — sans quoi il y en aurait deux.

> **Deux tests de `T5` ont refusé ma réécriture, et ils avaient raison.** J'avais profité de
> l'extraction pour désaccentuer le message de copie. Ce sont des textes **vus par l'utilisateur**, et
> les tests les épinglent : la formulation d'origine est conservée.

---

## 6. Ce que `T10` ne fait pas, et pourquoi

- **aucune branche 403.** Mesuré sur le manifeste du contrat : `/entities` déclare `[200, 401]`, les
  deux autres `[200, 401, 404]`. **Aucune des trois routes du portail ne peut rendre 403**, et
  `ECART-046` le dit déjà. Les trois pages 403/404/erreur **existent et sont routées** depuis `T11`
  du LOT 3. Livrer une branche que rien ne peut atteindre est ce que `T10` du LOT 1 et `DEC-537`
  refusent ;
- **aucune notification.** Le §17.4 en demande, et elles relèvent de `T11` — qui consolide le design
  system à partir de ce que les écrans ont réellement eu besoin ;
- **aucun message de champ nouveau.** Le §17.4 en demande, et les formulaires d'authentification en
  portent depuis `T11` du LOT 3 ;
- **TanStack Query n'est toujours pas installé**, et cela a été réexaminé. Le §17.3 écrit « TanStack
  Query gère les données serveur », et `T10` est précisément son domaine — réessai, données périmées,
  hors ligne. **Mais `DEC-537` et `DEC-544` l'ont écarté deux fois** pour un motif qui tient encore :
  `make audit` est à **zéro avis, zéro tolérance** depuis `DEC-493`, et le code écrit à la main est
  désormais **prouvé**, y compris sur le défaut qu'il avait eu (`T8-4`). Le remplacer en `T10`
  rouvrirait du code éprouvé pour un critère qui ne l'exige pas. **À réexaminer au LOT 5**, où les
  mutations métier arrivent — c'est là que son apport serait réel.

---

## 7. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **709** — inchangé, `T10` est frontend seul |
| Vitest | **228** — 90 `ui`, **121** `web`, 17 `contracts` |
| `make cadre-check` | **24 contrôles**, 0 échec — 23 avant `T10` |
| `make cadre-temoin` | **14 motifs** exigés et nommés — 13 avant |
| `make residu-check` · `permissions-check` · `entites-check` · `ecrans-check` | **0** · **0** · **0** · **0** |
| Migration · endpoints du contrat | **aucune** · **13**, inchangé |

**Quatre défauts injectés un par un**, tous rattrapés :

| Défaut | Ce qui l'a dit |
|---|---|
| `setEtat('connecte')` dans un `catch` | `cadre-check`, en nommant le fichier **et** l'état |
| la branche hors connexion neutralisée | 1 test |
| le compteur retiré des dépendances de l'effet | 2 tests — « recharge de lui-même » et « le bouton réessaie » |
| la corrélation plus affichée | 2 tests |

**Et vu dans un vrai navigateur** : le panneau d'erreur avec sa corrélation et son bouton, l'état
« Session expiree » avec son lien, la coupure de connexion puis le **rechargement automatique** au
retour — l'entité et le sélecteur reviennent seuls.

---

## 8. Ce que `T10` laisse à la suite

- **`T11`** — les composants du design system que ces écrans emploient, `US007`. Elle a désormais de
  quoi consolider : le **panneau d'erreur**, le **bouton d'action** et ses deux variantes, le
  **sélecteur** en `<details>`, et les **notifications** que le §17.4 demande et que ce lot n'a pas
  livrées. Et une convergence à faire : `PageStatut` emploie encore les classes neutres d'avant
  `packages/ui`, si bien que le même message de copie s'affiche dans deux habillages différents ;
- **`T12`** — recette, reclassements du §30 et checklist `G4` ;
- **au LOT 5**, réexaminer **TanStack Query** : c'est là que les mutations métier arrivent, donc là
  que son apport serait réel. Le §17.3 le nomme, et deux décisions l'ont écarté pour absence d'usage.
