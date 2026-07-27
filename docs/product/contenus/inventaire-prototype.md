# Inventaire des contenus du prototype à reprendre

**Produit en :** LOT 0, sous-étape S7 — story `MVP-L00-US005`, priorité `P1`
**Séquence d'identifiants :** `CONT-nnn`, créée par `DEC-436`
**Statut global de relecture :** **aucun contenu n'est validé ni publié**
**Destination :** LOT 6, story `MVP-L06-US007` « Reprendre les textes validés du prototype »

---

## 1. Portée et méthode

Le cahier des charges §2.2 limite strictement ce que le prototype peut fournir :

> « conserver l'intention visuelle ; identifier les fonctions utiles ; reprendre après relecture
> certains textes, descriptions de cercles, descriptions de bureaux et liens internes. »

Méthode d'extraction, en lecture seule :

1. retrait de toutes les chaînes Base64, soit 2,64 Mo sur 2,83 Mo, ramenant le fichier à
   194 566 caractères de texte réellement analysable ;
2. relevé des structures éditoriales et des textes visibles ;
3. décodage de la page d'onboarding embarquée, 52 442 caractères ;
4. **écartement à la source** de toute donnée personnelle.

Le prototype reste non versionné. Aucune ligne de son code n'est reprise.

### 1.1 Statuts de relecture

| Statut | Sens |
|---|---|
| `à relire` | Relevé fidèlement, en attente de relecture par son propriétaire |
| `validé` | Relu et approuvé, reprise autorisée |
| `à réécrire` | Le fond est utile, la formulation doit changer |
| `écarté` | Ne sera pas repris |

**Tous les éléments ci-dessous sont au statut `à relire`.** Aucun ne peut être publié avant
validation par son propriétaire.

---

## 2. Textes éditoriaux généraux

| ID | Type | Contenu relevé | Destination | Propriétaire | Statut |
|---|---|---|---|---|---|
| `CONT-001` | Présentation de l'entité | « eXalt Bordeaux rassemble des profils complémentaires autour d'une culture collaborative, humaine et orientée terrain. Cette page sert de repère onboarding pour aider les nouveaux arrivants à comprendre l'organisation locale, identifier les bons interlocuteurs et découvrir les cercles d'expertise. » | Accueil d'entité, section 1 (`MVP-L06-US005`) | Léa | `à relire` |
| `CONT-002` | Présentation du Framework | « Le framework eXalt accompagne les consultants dans leur évolution et favorise l'intelligence collective. » | Page Framework (`MVP-L06-US001`) | Tess | `à relire` |
| `CONT-003` | Accroche onboarding | « Ta fiche d'arrivée, ta checklist personnalisée (intercontrat ou mission) et tes réunions clés — tout est ici. » | Accès onboarding | Diane | `à relire` |
| `CONT-004` | Accroche vie interne | « Bureaux, événements, agenda… Découvre l'ambiance et la culture eXalt au quotidien. » | Section bureaux et événements | Tess | `à relire` |
| `CONT-005` | Accroche nouvel arrivant | « 🚀 Tu viens d'arriver chez eXalt Bordeaux ? » | Bandeau d'accueil | Diane | `à relire` |

### 2.1 Titres de sections relevés

| ID | Titre relevé | Observation | Propriétaire | Statut |
|---|---|---|---|---|
| `CONT-006` | « eXalt Bordeaux » | Titre de la page d'accueil | Léa | `à relire` |
| `CONT-007` | « Vision » | Section de présentation | Léa | `à relire` |
| `CONT-008` | « Personnes liées au framework » | Formulation à revoir : les documents validés parlent de **responsabilités** Framework, non de personnes liées | Tess | `à réécrire` |
| `CONT-009` | « Les X du cercle » | Le « X » renvoie à l'icône de la charte eXalt. Intention visuelle, à confirmer | Tess | `à relire` |
| `CONT-010` | « Découvre ton parcours d'onboarding » | Accès au parcours | Diane | `à relire` |
| `CONT-011` | « La Vie eXalt Bordeaux » | Section vie interne | Tess | `à relire` |

---

## 3. Bureaux

Le prototype fournit, pour les trois bureaux, un **intitulé complet** et une **description**.
C'est l'apport éditorial le plus directement exploitable.

| ID | Code | Intitulé complet relevé | Description relevée | Propriétaire | Statut |
|---|---|---|---|---|---|
| `CONT-012` | `BDS` | Bureau Des Sports | « Escalade, crossfit, padel, pétanque… Le BDS organise des événements sportifs pour tous les niveaux. Inscris-toi aux prochaines sessions ! » | Tess | `à relire` |
| `CONT-013` | `BDE` | Bureau des Exaltés | « Hot Ones, Face à Face, drinks, afterworks… Le BDE crée des moments inoubliables. Inscris-toi et vis l'ambiance eXalt à fond. » | Tess | `à relire` |
| `CONT-014` | `BDG` | Bureau De Gaming | « Mario Kart, tournois, jeux de société… Le BDG organise des sessions gaming pour décompresser entre collègues. » | Tess | `à relire` |

### 3.1 Observation de relecture

Les trois descriptions contiennent un appel à l'action « Inscris-toi ». Or le MVP est
**strictement informatif** : aucune inscription, aucune liste de participants, aucune
notification métier d'événement (cahier §10.6, roadmap LOT 8). Ces formulations devront être
adaptées, sans quoi elles promettraient une fonctionnalité absente.

Cette observation vaut décision de relecture pour `CONT-012`, `CONT-013` et `CONT-014`.

---

## 4. Cercles

| ID | Constat | Conséquence |
|---|---|---|
| `CONT-015` | **Aucune description de cercle n'existe dans le prototype.** Les huit cercles ne portent qu'une couleur et une variante d'icône. | Le cahier §2.2 et §12.1 annoncent que le prototype fournit des « descriptions de cercles ». Il n'en fournit aucune. Les huit descriptions devront être **rédigées** au LOT 6, non reprises. Écart `ECART-015`. |

### 4.1 Intention visuelle relevée, à titre indicatif

Ces valeurs relèvent de l'intention visuelle, pas du contenu éditorial. Elles ne préjugent pas
de la charte officielle, dont l'indisponibilité est suivie en `DEP-006` et `ROAD-RSK-006`.

| ID | Cercle | Couleur du prototype | Variante d'icône | Propriétaire | Statut |
|---|---|---|---|---|---|
| `CONT-016` | Produit | `#5853FF` | `flow` | Tess | `à relire` |
| `CONT-017` | Design | `#FF2C9B` | `value` | Tess | `à relire` |
| `CONT-018` | Projet | `#2F2F9B` | `flow` | Tess | `à relire` |
| `CONT-019` | Change | `#FFDA3E` | `nilo` | Tess | `à relire` |
| `CONT-020` | Data | `#9B53FF` | `fi` | Tess | `à relire` |
| `CONT-021` | Shield | `#FF5398` | `shield` | Tess | `à relire` |
| `CONT-022` | Forge | `#53B4FF` | `pixel` | Tess | `à relire` |
| `CONT-023` | IT | `#FF8C53` | `dots` | Tess | `à relire` |

Le prototype prévoyait une couleur de texte foncée sur le fond jaune du cercle Change, signe
d'un problème de contraste déjà identifié à l'époque. Le cahier §14.2 impose des contrastes
suffisants, « quitte à ajuster certaines couleurs de la charte », et interdit qu'une information
soit portée uniquement par la couleur. Ces huit couleurs sont donc à **vérifier au contraste**
avant reprise.

---

## 5. Parcours d'onboarding

| ID | Contenu | Volume | Propriétaire | Statut |
|---|---|---|---|---|
| `CONT-024` | Parcours **intercontrat** : 6 phases, 28 tâches | relevé intégral | Diane, Tess | `à relire` |
| `CONT-025` | Parcours **mission** : 3 phases, 16 tâches | relevé intégral | Diane, Tess | `à relire` |

Relevé complet, tâche par tâche, avec identifiants d'origine et analyse des tâches communes :
[parcours-onboarding-prototype.md](parcours-onboarding-prototype.md).

C'est l'apport le plus substantiel du prototype. Il alimente directement le LOT 7, stories
`MVP-L07-US003` et `MVP-L07-US007`.

---

## 6. Médias

| ID | Constat | Conséquence |
|---|---|---|
| `CONT-026` | Le prototype prévoyait **onze emplacements vidéo** : présentation du General Manager, DSM, Framework, et une par cercle. **Les onze sont vides.** | Aucune vidéo n'est récupérable. Leur production relève du LOT 6 et de la V1 (`V1-L06-US001`). Volumétrie attendue : `QO-102`. |
| `CONT-027` | Le logo eXalt était intégré en Base64 dans le code. | Non repris. Le logo officiel est une dépendance externe, `DEP-006`. |
| `CONT-028` | Les photographies de personnes et de bureaux étaient intégrées en Base64. | **Écartées.** Voir [exclusions-prototype.md](exclusions-prototype.md). |

---

## 7. Liens internes

| ID | Constat |
|---|---|
| `CONT-029` | **Le prototype ne contient aucun lien interne exploitable.** |

Détail et conséquences : [liens-internes-a-confirmer.md](liens-internes-a-confirmer.md).

---

## 8. Synthèse

| Catégorie | Éléments | Exploitables après relecture |
|---|---:|---|
| Textes éditoriaux généraux | 5 | oui |
| Titres de sections | 6 | oui, dont 1 à réécrire |
| Bureaux : intitulés et descriptions | 3 | oui, avec adaptation obligatoire |
| Cercles : descriptions | 0 | **à rédiger intégralement** |
| Cercles : intention visuelle | 8 | indicatif, à vérifier au contraste |
| Parcours d'onboarding | 2 parcours, 44 tâches | oui, matière de départ du LOT 7 |
| Médias | 0 | rien de récupérable |
| Liens internes | 0 | rien de récupérable |

**29 éléments inventoriés**, `CONT-001` à `CONT-029`. Prochain identifiant libre : `CONT-030`.

---

## 9. Ce que cet inventaire n'autorise pas

- publier un contenu au statut `à relire` ;
- reprendre une ligne de code du prototype ;
- reprendre une donnée personnelle, une photographie ou un nom ;
- considérer les couleurs relevées comme la charte officielle ;
- traiter les descriptions de bureaux comme validées : leur appel à l'inscription contredit le
  périmètre informatif du MVP.

---

## 10. Propriétaires de la relecture

| Propriétaire | Périmètre | Fondement |
|---|---|---|
| **Léa** | Arbitrages produit, présentation de l'entité | Cahier §5.1 |
| **Tess** | Validation fonctionnelle et éditoriale : Framework, cercles, bureaux, vie interne | Cahier §5.1 |
| **Diane** | Validation métier des contenus et parcours d'onboarding | Cahier §5.1 |

La relecture n'est pas réalisable dans le cadre du LOT 0 : elle dépend de ces trois personnes.
La story `MVP-L00-US005` est de priorité `P1`, ce qui autorise un arbitrage explicite de
Jonathan pour franchir la porte `G0` avec un inventaire au statut `à relire`.
