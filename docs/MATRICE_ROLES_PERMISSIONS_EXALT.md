# Matrice détaillée des rôles et permissions — eXalt Onboarding Digital

**Version :** 1.1 — livrable de cadrage 1/6  
**Date :** 25 juillet 2026  
**Statut :** validé par Jonathan le 25 juillet 2026  
**Périmètre :** MVP et règles structurantes V1/V2

---

## 1. Objet du document

Cette matrice définit :

- les rôles fonctionnels et techniques de la plateforme ;
- leur périmètre géographique et organisationnel ;
- les droits de consultation, création, modification, publication, archivage, restauration, export et suppression ;
- les règles de cumul entre les fonctions professionnelles et les responsabilités du Framework ;
- les restrictions applicables lors de la consultation d’une autre entité ;
- les contrôles obligatoires à appliquer côté API.

La matrice applique un principe de **refus par défaut** : une action non explicitement autorisée est interdite.

---

## 2. Principes structurants

### 2.1 Une seule entité principale

Chaque personne possède une seule entité principale active.

Dans cette entité, elle peut cumuler plusieurs responsabilités métier ou techniques. Dans toutes les autres entités, elle dispose uniquement d’un accès de consultation, sauf si elle est super-administratrice de plateforme.

### 2.2 Séparation des dimensions

Les notions suivantes ne doivent jamais être fusionnées dans un champ unique `role` :

| Dimension | Exemples |
|---|---|
| Catégorie professionnelle | Consultant, DG |
| Situation professionnelle | Mission, intercontrat |
| Métier | Data Analyst, Product Owner, développeur |
| Responsabilité Framework | DSM, ESM, Booster, responsable de bureau |
| Autorisation technique | Administrateur d’entité, super-administrateur |
| Rattachement organisationnel | Entité, cercle, bureau, client |

### 2.3 Cumuls autorisés

Une même personne peut notamment être :

- consultante et Booster ;
- consultante et responsable de bureau ;
- consultante, Booster et responsable de bureau ;
- consultante et ESM ;
- ESM et responsable de bureau ;
- administratrice d’entité et consultante ;
- DG et DSM.

Les permissions accordées dans l’entité principale correspondent à l’union des droits associés aux responsabilités actives de la personne.

### 2.4 Cas du DG

Un DG reçoit automatiquement la responsabilité DSM dans sa propre entité.

Le DG n’est pas un rôle technique global. Il ne reçoit aucun droit spécial sur les autres entités.

### 2.5 Booster

Une personne ne peut pas être Booster active simultanément dans plusieurs entités.

Un cercle ne peut avoir qu’un seul Booster actif à un instant donné.

### 2.6 Contrôle côté serveur

Le frontend peut masquer ou afficher les actions pour améliorer l’expérience, mais l’API reste l’autorité finale.

Chaque requête sensible doit vérifier :

1. l’identité de la personne ;
2. l’état actif du compte ;
3. l’entité principale ;
4. l’entité actuellement consultée ;
5. les responsabilités actives ;
6. le périmètre exact de la ressource ;
7. l’état de la ressource ;
8. les éventuelles contraintes métier supplémentaires.

---

## 3. Typologie des utilisateurs

| Code | Type | Description | Périmètre principal |
|---|---|---|---|
| `ANON` | Visiteur non authentifié | Accès aux seules pages publiques techniques | Connexion, mentions légales, erreurs |
| `EMP` | Employé authentifié | Collaborateur actif présent dans la base | Lecture de toutes les entités |
| `NEW` | Nouvel arrivant | Employé disposant d’une fiche d’arrivée ou d’un onboarding actif | Lecture générale + actions sur ses propres objets |
| `DSM` | DSM | Responsable des consultants qui lui sont rattachés | Ses consultants dans son entité |
| `ESM` | ESM | Responsable fonctionnel de l’entité | Ensemble de son entité |
| `BOOST` | Booster | Responsable d’un cercle | Son cercle et ses membres |
| `OFFICE` | Responsable de bureau | Responsable d’un bureau interne | Son bureau |
| `ADM-E` | Administrateur d’entité | Administrateur fonctionnel et support local | Ensemble de son entité |
| `SUPER` | Super-administrateur | Administration globale de la plateforme | Toutes les entités |
| `SERVICE` | Compte de service | Identité technique utilisée par un script interne | Scopes explicitement accordés |

### 3.1 Types qui ne constituent pas un rôle d’autorisation autonome

Les éléments suivants ne donnent pas, seuls, des droits supplémentaires :

- consultant en mission ;
- consultant en intercontrat ;
- métier ;
- client ;
- cercle principal ou secondaire ;
- membre du Framework sans responsabilité active ;
- ancien collaborateur archivé.

---

## 4. Légende des permissions

| Symbole | Signification |
|---|---|
| `✓` | Autorisé dans le périmètre indiqué |
| `—` | Interdit |
| `Soi` | Uniquement sur ses propres données ou tâches |
| `Consultants` | Uniquement pour les consultants rattachés au DSM |
| `Cercle` | Uniquement pour le cercle du Booster |
| `Bureau` | Uniquement pour le bureau du responsable |
| `Entité` | Ensemble de l’entité principale |
| `Global` | Ensemble de la plateforme |
| `Lecture` | Consultation uniquement, sans modification |
| `Conditionnel` | Autorisé si une règle métier complémentaire est satisfaite |

---

# 5. Matrice générale de consultation

| Ressource | ANON | EMP | NEW | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Page nationale et carte des entités | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Accueil d’une entité | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Présentation de l’entité | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Framework | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Cercles | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Bureaux | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Trombinoscope | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Fiches collaborateur | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Statut mission/intercontrat | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Client actif | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Événements | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Arrivées récentes | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Liens Hub/Academy/SharePoint | — | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture | Lecture |
| Onboarding personnel | — | — | Soi | — | — | — | — | — | — |
| Onboardings d’autres personnes | — | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Reporting collaborateurs | — | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Audit | — | — | — | Consultants | Modifications fonctionnelles de l’entité | Cercle | Bureau | Entité | Global |
| Supervision technique | — | — | — | — | Consultation fonctionnelle limitée | — | — | Entité | Global |
| Administration | — | — | — | Périmètre métier | Entité | Cercle | Bureau | Entité | Global |

### 5.1 Accès inter-entités

Lorsqu’une personne consulte une entité différente de son entité principale :

- elle possède uniquement les droits `EMP` ;
- ses responsabilités DSM, ESM, Booster, responsable de bureau ou administrateur d’entité ne s’appliquent pas ;
- aucune action de création, modification, publication, archivage, restauration ou export n’est proposée ;
- les contrôles côté API utilisent l’entité de la ressource, et non uniquement l’entité sélectionnée dans le frontend.

Le super-administrateur constitue la seule exception globale.

---

# 6. Collaborateurs et profils

## 6.1 Consultation et gestion des profils

| Action | EMP | NEW | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Consulter un profil actif | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer manuellement un profil | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Modifier les données organisationnelles | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Modifier métier, statut, DSM, client ou cercle principal | — | — | Consultants | Entité | Cercle, hors changement de DSM | — | Entité | Global |
| Gérer les cercles secondaires | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Modifier la courte présentation après validation | — | — | Consultants | Entité | Cercle | — | Entité | Global |
| Modifier ou retirer un fun fact | — | Soi avant validation | Consultants | Entité | Cercle | — | Entité | Global |
| Ajouter ou remplacer une photo | — | Soi avant validation | Consultants | Entité | Cercle | — | Entité | Global |
| Enregistrer l’autorisation photo | Soi lors de l’action | Soi | — | Support | Support | — | Support | Support |
| Retirer l’autorisation photo | Soi sur demande | Soi | — | Support | Support | — | Support | Support |
| Archiver un profil | — | — | — | Entité | — | — | Entité | Global |
| Réactiver un profil archivé | — | — | — | Conditionnel | — | — | Entité | Global |
| Consulter un profil archivé | — | — | — | Entité, besoin fonctionnel | — | — | Entité | Global |
| Purger définitivement | — | — | — | — | — | — | — | Global |

### 6.2 Règles complémentaires

- Le nouvel arrivant ne modifie que la photo, la présentation et le fun fact avant validation.
- La date d’arrivée, le métier, le statut, le DSM, le client et le cercle principal sont préremplis et verrouillés pour le nouvel arrivant.
- Après validation de la fiche d’arrivée, le collaborateur ne peut plus modifier directement son profil.
- Un DSM ne peut modifier que les consultants ayant un rattachement DSM actif vers lui.
- Un Booster ne peut modifier que les membres actifs de son cercle. Pour un membre secondaire, ses actions doivent rester limitées aux données du cercle et ne pas permettre de modifier un autre cercle principal sans autorisation supérieure.
- Un responsable de bureau n’obtient aucun droit général sur les profils du seul fait de sa responsabilité de bureau.
- L’archivage d’un collaborateur est réservé à l’ESM, à l’administrateur d’entité et au super-administrateur.
- La purge définitive est réservée au super-administrateur.

---

# 7. Fiches d’arrivée

| Action | NEW | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|
| Consulter sa fiche non publiée | Soi | — | Entité | Cercle | — | Entité | Global |
| Compléter photo, présentation et fun fact | Soi | — | Support | Support cercle | — | Support | Support |
| Consulter les informations préremplies | Soi | — | Entité | Cercle | — | Entité | Global |
| Modifier les informations organisationnelles | — | Consultants | Entité | Cercle limité | — | Entité | Global |
| Prévisualiser | Soi | Consultants | Entité | Cercle | — | Entité | Global |
| Valider et publier | Soi | — | Support | — | — | Support | Support |
| Corriger après publication | — | Consultants | Entité | Cercle | — | Entité | Global |
| Archiver | — | — | Entité | — | — | Entité | Global |
| Export image 16:9 | V1 | V1 périmètre | V1 Entité | V1 Cercle | — | V1 Entité | V1 Global |
| Générer le texte Teams | V1 | V1 périmètre | V1 Entité | V1 Cercle | — | V1 Entité | V1 Global |

### 7.1 Publication

La fiche est publiée automatiquement lorsque le nouvel arrivant la valide. La validation ne nécessite pas une approbation préalable d’un responsable.

### 7.2 Affichage

La fiche reste mise en avant dans la section « Ils nous ont rejoints récemment » jusqu’à un mois après la date d’arrivée.

---

# 8. Onboarding individuel

## 8.1 Consultation et actions

| Action | NEW | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|
| Consulter son parcours | Soi | — | — | — | — | — | — |
| Consulter le parcours d’un collaborateur | — | Consultants | Entité | Cercle | — | Entité | Global |
| Marquer une tâche comme terminée | Soi | — | — | — | — | — | — |
| Annuler la complétion dans les 5 minutes | Soi | — | — | — | — | — | — |
| Réouvrir après le délai de 5 minutes | — | — | Entité | — | — | Entité | Global |
| Affecter un parcours | — | Consultants | Entité | Cercle | — | Entité | Global |
| Remplacer le parcours après changement de statut | — | Consultants | Entité | Cercle | — | Entité | Global |
| Modifier une échéance individuelle | — | Consultants | Entité | Cercle | — | Entité | Global |
| Consulter les tâches en retard | Soi | Consultants | Entité | Cercle | — | Entité | Global |
| Archiver un parcours terminé | Automatique | — | Entité | — | — | Entité | Global |
| Restaurer un parcours archivé | — | — | Conditionnel | — | — | Entité | Global |
| Exporter le suivi | V1 | V1 Consultants | V1 Entité | V1 Cercle | — | V1 Entité | V1 Global |

### 8.2 Règles métier

- Le parcours est déterminé par la situation mission ou intercontrat.
- En cas de changement de situation, le parcours est remplacé par le nouveau modèle.
- Les tâches communes déjà terminées sont conservées grâce à une référence métier stable.
- Le parcours est terminé lorsque toutes les tâches obligatoires sont terminées.
- Aucun commentaire ni document joint n’est prévu dans le MVP.
- Aucun tiers ne valide les tâches dans le MVP.
- Les responsables ne peuvent pas marquer une tâche comme terminée à la place du nouvel arrivant, sauf correction technique explicitement auditée par l’administrateur ou le super-administrateur.

### 8.3 Réouverture après cinq minutes

Après le délai de cinq minutes, une tâche terminée ne peut être réouverte que par :

- l’ESM de l’entité ;
- l’administrateur de l’entité ;
- le super-administrateur.

La réouverture exige un motif et génère un événement d’audit. Le DSM et le Booster ne peuvent pas effectuer cette correction.

---

# 9. Modèles d’onboarding

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter les modèles publiés | ✓ | ✓ | ✓ | Lecture | ✓ | ✓ |
| Créer un modèle | Consultants | Entité | Cercle | — | Entité | Global |
| Créer une nouvelle version | Consultants | Entité | Cercle | — | Entité | Global |
| Ajouter ou réordonner des tâches | Consultants | Entité | Cercle | — | Entité | Global |
| Réutiliser une tâche de référence | Consultants | Entité | Cercle | — | Entité | Global |
| Créer une tâche de référence | Consultants | Entité | Cercle | — | Entité | Global |
| Prévisualiser | Consultants | Entité | Cercle | — | Entité | Global |
| Publier une version | Consultants | Entité | Cercle | — | Entité | Global |
| Archiver une version | Consultants | Entité | Cercle | — | Entité | Global |
| Restaurer une version | — | Conditionnel | — | — | Entité | Global |

### 9.1 Limitation de périmètre

- Un modèle créé par un DSM doit être destiné à ses consultants ou partir d’un modèle d’entité autorisé.
- Un modèle créé par un Booster doit être explicitement rattaché à son cercle.
- L’ESM et l’administrateur d’entité peuvent créer des modèles transverses à l’entité.
- Le super-administrateur peut créer les modèles génériques eXalt utilisés lors de l’initialisation d’une nouvelle entité.

---

# 10. Framework, cercles et bureaux

## 10.1 Structure Framework

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter la page Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modifier la présentation générale | — | Entité | — | — | Entité | Global |
| Modifier la page DSM | Entité ou propre contenu | Entité | — | — | Entité | Global |
| Modifier la page ESM | — | Entité | — | — | Entité | Global |
| Gérer les vidéos Framework | — | Entité | — | — | Entité | Global |
| Publier les modifications | — | Entité | — | — | Entité | Global |
| Archiver/restaurer une page | — | Conditionnel | — | — | Entité | Global |

## 10.2 Cercles

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter tous les cercles | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer un cercle | — | Entité | — | — | Entité | Global |
| Modifier la structure d’un cercle | — | Entité | — | — | Entité | Global |
| Modifier le contenu du cercle | — | Entité | Cercle | — | Entité | Global |
| Modifier description, ressources et vidéo | — | Entité | Cercle | — | Entité | Global |
| Gérer les membres principaux | Consultants limités | Entité | Cercle limité | — | Entité | Global |
| Gérer les membres secondaires | Consultants limités | Entité | Cercle | — | Entité | Global |
| Affecter ou remplacer le Booster | — | Entité | — | — | — | Global |
| Archiver un cercle | — | Entité, si aucun membre actif | — | — | Entité, si aucun membre actif | Global |
| Restaurer un cercle | — | Conditionnel | — | — | Entité | Global |

L’attribution des responsabilités Framework est réservée à l’ESM et au super-administrateur. L’administrateur d’entité ne peut pas attribuer ces responsabilités.

## 10.3 Bureaux

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter tous les bureaux | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer un bureau | — | Entité | — | — | Entité | Global |
| Modifier la structure du bureau | — | Entité | — | Bureau, contenu uniquement | Entité | Global |
| Modifier description, vidéo et ressources | — | Entité | — | Bureau | Entité | Global |
| Gérer la galerie | — | Entité | — | Bureau | Entité | Global |
| Affecter les responsables | — | Entité | — | — | — | Global |
| Archiver un bureau | — | Entité | — | — | Entité | Global |
| Restaurer un bureau | — | Conditionnel | — | — | Entité | Global |

---

# 11. Événements

| Action | EMP | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|
| Consulter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer | — | Entité ou consultants | Entité | Cercle | Bureau | Entité | Global |
| Modifier | — | Événements créés ou rattachés à son périmètre | Entité | Cercle | Bureau | Entité | Global |
| Publier | — | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Ajouter une image ou vidéo | — | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Rattacher à plusieurs cercles ou bureaux | — | Périmètre autorisé | Entité | Cercle + autres seulement si autorisé | Bureau + autres seulement si autorisé | Entité | Global |
| Annuler | — | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Archiver | — | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Restaurer | — | — | Conditionnel | — | — | Entité | Global |
| Créer une récurrence | V1 | V1 Périmètre | V1 Entité | V1 Cercle | V1 Bureau | V1 Entité | V1 Global |

### 11.1 Règles

- Les événements sont informatifs : aucune inscription, liste de participants ou notification métier dans le MVP.
- Un événement annulé reste visible avec un badge « Annulé ».
- Un événement passe automatiquement dans l’onglet « Passés » après son heure de fin.
- La modification et la publication sont immédiates en un clic et toujours auditées.

---

# 12. Médias

## 12.1 MVP

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Charger un média | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Remplacer un média | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Consulter les médias liés | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Archiver un média non partagé | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Remplacer un média partagé | Conditionnel | Entité | Conditionnel | Conditionnel | Entité | Global |
| Restaurer | — | Conditionnel | — | — | Entité | Global |
| Purger définitivement | — | — | — | — | — | Global |

## 12.2 V1 — médiathèque avancée

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rechercher et filtrer | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Réutiliser un média | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Voir les usages | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Détecter les médias inutilisés | — | Entité | Cercle | Bureau | Entité | Global |
| Opération multiple | — | Entité | Cercle limité | Bureau limité | Entité | Global |

### 12.3 Sécurité

Le droit de chargement ne contourne jamais :

- la validation du type réel du fichier ;
- les limites de taille et de durée ;
- la quarantaine ;
- le rattachement à l’entité ;
- les règles d’autorisation photo.

---

# 13. Contenus éditoriaux et liens internes

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer un contenu général | — | Entité | — | — | Entité | Global |
| Modifier la présentation de l’entité | — | Entité | — | — | Entité | Global |
| Modifier un contenu de cercle | — | Entité | Cercle | — | Entité | Global |
| Modifier un contenu de bureau | — | Entité | — | Bureau | Entité | Global |
| Gérer les cartes Hub/Academy/SharePoint | — | Entité | — | — | Entité | Global |
| Publier immédiatement | — | Périmètre | Cercle | Bureau | Entité | Global |
| Archiver | — | Périmètre | Cercle | Bureau | Entité | Global |
| Restaurer | — | Conditionnel | — | — | Entité | Global |

---

# 14. Imports CSV

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Charger un CSV | — | Entité | — | — | Entité | Global |
| Prévisualiser et corriger les correspondances | Consultants en validation métier | Entité | Cercle en validation métier | — | Entité | Global |
| Valider les rapprochements clients | Consultants | Entité | — | — | Entité | Global |
| Lancer l’import | — | Entité | — | — | Entité | Global |
| Consulter le rapport | Consultants | Entité | Cercle limité | — | Entité | Global |
| Rejouer les lignes rejetées | — | Entité | — | — | Entité | Global |
| Réactiver un profil archivé | — | Confirmation explicite | — | — | Confirmation explicite | Global |
| Rollback complet | V1 — | V1 selon décision | — | — | V1 Entité | V1 Global |
| Exporter le rapport | — | Entité | — | — | Entité | Global |

### 14.1 Validation métier

- L’ESM valide les collaborateurs, statuts, arrivées et contenus généraux.
- Les DSM valident les consultants, missions et clients de leur périmètre.
- Les Boosters valident les membres de leur cercle.
- Les responsables de bureau valident les contenus de leur bureau, hors import collaborateur.
- Jonathan valide la structure technique et le rapport.
- Léa et Jonathan valident le chargement final.

---

# 15. Reporting et exports

## 15.1 MVP

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter les compteurs | Consultants | Entité | Cercle | — | Entité | Global |
| Consulter le détail onboarding | Consultants | Entité | Cercle | — | Entité | Global |
| Consulter les profils incomplets | Consultants | Entité | Cercle | — | Entité | Global |
| Consulter les arrivées à 30 jours | Consultants | Entité | Cercle | — | Entité | Global |
| Filtrer par période, DSM, cercle, client | Périmètre | Entité | Cercle | — | Entité | Global |
| Consulter les événements | Périmètre | Entité | Cercle | Bureau | Entité | Global |

## 15.2 V1

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Afficher les graphiques | Consultants | Entité | Cercle | Bureau | Entité | Global |
| Exporter un tableau CSV | Consultants | Entité | Cercle | Bureau | Entité | Global |
| Exporter une synthèse PDF | Consultants | Entité | Cercle | Bureau | Entité | Global |

Les exports doivent respecter exactement le même périmètre que la consultation à l’écran.

---

# 16. Audit

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Consulter | Consultants | Modifications fonctionnelles de l’entité | Historique du cercle | Historique du bureau | Entité | Global |
| Rechercher et filtrer | Consultants | Périmètre | Cercle | Bureau | Entité | Global |
| Voir ancien/nouveau contenu | Périmètre | Périmètre | Cercle | Bureau | Entité | Global |
| Exporter en CSV | — | — | — | — | Entité | Global |
| Consulter les détails techniques non sensibles | Limité | Limité | Limité | Limité | Entité | Global |
| Purger les audits arrivés à échéance | — | — | — | — | — | Traitement global automatique/supervision |

### 16.1 Durée

Les journaux d’audit sont conservés un an.

### 16.2 Contenu interdit

Aucun rôle ne peut consulter depuis l’audit :

- mots de passe ;
- jetons de session ;
- magic links complets ;
- secrets ;
- fichiers CSV complets ;
- contenu brut complet des e-mails.

---

# 17. Alertes, supervision et support

| Action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Reporter un bug | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Consulter ses signalements | Soi | Soi | Soi | Soi | Entité | Global |
| Consulter les signalements de l’entité | — | Lecture fonctionnelle | — | — | Entité | Global |
| Modifier l’état d’un signalement | — | — | — | — | Entité | Global |
| Consulter les KPI techniques | — | Limité | — | — | Entité | Global |
| Consulter les alertes de sécurité | — | Limité fonctionnel | — | — | Entité | Global |
| Acquitter une alerte | — | — | — | — | Entité | Global |
| Résoudre ou commenter une alerte | — | — | — | — | Entité | Global |
| Modifier les seuils | — | — | — | — | — | Global |

Pendant la phase locale, Jonathan est l’unique destinataire des alertes Uptime Kuma.

---

# 18. Archives, restauration et purge

| Ressource/action | DSM | ESM | BOOST | OFFICE | ADM-E | SUPER |
|---|---:|---:|---:|---:|---:|---:|
| Archiver un collaborateur | — | Entité | — | — | Entité | Global |
| Archiver un contenu dans son périmètre | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Archiver un événement | Périmètre | Entité | Cercle | Bureau | Entité | Global |
| Archiver un cercle ou bureau | — | Entité | — | — | Entité | Global |
| Restaurer un collaborateur | — | Entité, restauration fonctionnelle | — | — | Entité | Global |
| Restaurer un contenu | — | Entité, restauration fonctionnelle | — | — | Entité | Global |
| Restaurer un cercle ou bureau | — | Entité, restauration fonctionnelle | — | — | Entité | Global |
| Restaurer un import complet | V1 — | V1 conditionnel | — | — | V1 Entité | V1 Global |
| Purger définitivement une donnée | — | — | — | — | — | Global |
| Lancer l’anonymisation RGPD | — | — | — | — | Entité contrôlée | Global |

### 18.1 Motif obligatoire

Un motif est obligatoire pour :

- purge définitive ;
- révocation manuelle d’un accès actif ;
- changement sensible de rôle ;
- rollback d’import ;
- intervention du super-administrateur dans une entité.

---

# 19. Configuration d’entité

| Action | ESM | ADM-E | SUPER |
|---|---:|---:|---:|
| Consulter les paramètres | Entité | Entité | Global |
| Modifier nom d’affichage, ville et contenus locaux | Entité fonctionnel | Entité | Global |
| Modifier les liens internes | Entité | Entité | Global |
| Modifier le présentateur et la vidéo d’accueil | Entité | Entité | Global |
| Modifier les modèles génériques locaux | Entité | Entité | Global |
| Modifier la charte graphique globale | — | — | Global uniquement |
| Ajouter un domaine e-mail autorisé | — | — | Global uniquement |
| Modifier les paramètres d’authentification | — | — | Global uniquement |
| Modifier les seuils de sécurité | — | — | Global uniquement |
| Renseigner les informations RGPD de l’entité | Entité fonctionnel | Entité | Global |

L’identité visuelle eXalt reste identique dans toutes les entités. Les entités ne peuvent pas modifier librement le logo, la typographie ou les couleurs principales du design system.

---

# 20. Rôles, responsabilités et comptes administrateurs

| Action | ESM | ADM-E | SUPER |
|---|---:|---:|---:|
| Affecter une responsabilité DSM | Entité | — | Global |
| Affecter une responsabilité ESM | Entité, sauf auto-attribution sensible | — | Global |
| Affecter ou remplacer un Booster | Entité | — | Global |
| Affecter un responsable de bureau | Entité | — | Global |
| Retirer une responsabilité Framework | Entité | — | Global |
| Créer un administrateur d’entité | — | — | Global |
| Retirer un administrateur d’entité | — | — | Global |
| Créer ou retirer un super-administrateur | — | — | Global |
| Consulter l’historique des rôles | Entité | Entité | Global |
| Révoquer les sessions après retrait de rôle | Automatique | Automatique | Automatique |

L’administrateur d’entité n’attribue ni ne retire les responsabilités DSM, ESM, Booster ou responsable de bureau. Ces opérations sont réservées à l’ESM et au super-administrateur.

### 20.1 Règles

- Toute modification de rôle est auditée.
- L’attribution d’un super-administrateur déclenche une alerte de sécurité.
- Aucune MFA ni réauthentification n’est prévue dans le MVP ou la V1.
- Les confirmations renforcées, le motif et l’audit compensent partiellement ce risque accepté.

---

# 21. Super-administration

Seul le rôle `SUPER` peut :

- créer une entité ;
- activer ou désactiver une entité ;
- nommer le premier administrateur de l’entité ;
- créer ou retirer un super-administrateur ;
- gérer les domaines e-mail globaux ;
- gérer les paramètres d’authentification ;
- gérer les modèles génériques eXalt ;
- intervenir dans toutes les entités ;
- consulter l’audit global ;
- exporter l’audit global ;
- effectuer une purge définitive ;
- gérer les comptes de service ;
- gérer les seuils de sécurité et paramètres globaux ;
- consulter les alertes globales et la supervision globale.

Toute intervention du super-administrateur dans une entité doit :

- être auditée ;
- comporter un motif lorsqu’elle modifie des données ;
- rester visible par l’administrateur de l’entité concernée dans son audit local ;
- déclencher une alerte pour les opérations les plus sensibles.

---

# 22. Comptes de service et scripts internes

Les comptes de service ne correspondent à aucun rôle humain.

Chaque compte de service possède des scopes explicites, par exemple :

```text
people:read
people:import
media:process
email:send
reports:generate
```

## 22.1 Règles obligatoires

- aucun compte personnel n’est utilisé par un script ;
- aucun compte de service ne reçoit automatiquement les droits de super-administrateur ;
- les scopes sont limités au besoin exact ;
- les jetons sont révocables et expirables ;
- chaque appel sensible est audité ;
- un compte de service est rattaché à une entité sauf besoin global documenté ;
- un script interne ne contourne jamais les règles d’intégrité métier ;
- aucune session manuelle d’employé ne peut être créée par un script en production.

---

# 23. Règles d’héritage et de résolution des conflits

## 23.1 Union des droits

Dans l’entité principale, les droits de plusieurs responsabilités se cumulent.

Exemple :

- une consultante est Booster du cercle Data et responsable du BDE ;
- elle peut gérer le contenu du cercle Data ;
- elle peut gérer le contenu du BDE ;
- elle ne peut pas gérer le cercle Forge ni le BDG ;
- elle conserve les droits de lecture générale du rôle `EMP`.

## 23.2 Restriction la plus forte

Une interdiction liée à la ressource ou à l’état prévaut sur le cumul des rôles.

Exemples :

- un cercle avec des membres actifs ne peut pas être archivé, même par une personne disposant du droit d’archivage ;
- une photographie ne peut pas être publiée sans autorisation ;
- un utilisateur archivé ne peut pas recevoir de magic link ;
- une opération inter-entités reste interdite à un administrateur local.

## 23.3 Changement d’entité

Le changement d’entité sélectionnée :

- ne modifie pas l’entité principale de la personne ;
- ne transfère pas ses responsabilités ;
- recharge les permissions ;
- annule les requêtes et caches associés à l’entité précédente ;
- doit être visible dans l’en-tête de l’application.

## 23.4 Historisation

Toutes les responsabilités importantes possèdent une date de début et une date de fin.

La suppression d’un rôle actif clôture la relation au lieu d’effacer l’historique.

---

# 24. Contrôles d’acceptation obligatoires

La matrice sera considérée correctement implémentée lorsque les tests démontreront notamment que :

1. un employé consulte toutes les entités mais ne modifie aucune autre entité ;
2. un DSM ne consulte les onboardings que de ses consultants ;
3. un DSM ne modifie pas un consultant rattaché à un autre DSM ;
4. un Booster ne modifie que son cercle et ses membres autorisés ;
5. un responsable de bureau ne modifie que son bureau ;
6. un ESM administre les données fonctionnelles de son entité ;
7. un administrateur d’entité n’accède pas aux autres entités ;
8. un super-administrateur accède à toutes les entités et ses interventions sont auditées ;
9. un nouvel arrivant ne modifie pas ses données organisationnelles ;
10. un collaborateur ne modifie plus sa fiche après validation ;
11. un profil archivé ne reçoit plus de magic link ;
12. un rôle clôturé ne continue pas à accorder des permissions ;
13. la sélection d’une autre entité ne conserve aucune permission locale ;
14. un cercle avec des membres actifs ne peut pas être archivé ;
15. une personne ne peut pas être Booster active dans plusieurs entités ;
16. un cercle ne peut pas avoir plusieurs Boosters actifs ;
17. la purge définitive est refusée à tous les rôles sauf `SUPER` ;
18. l’export d’audit est refusé à tous les rôles sauf `ADM-E` et `SUPER` ;
19. les exports de reporting respectent le même périmètre que l’écran ;
20. les actions interdites sont refusées côté API, même si la requête est construite manuellement.

La couverture automatisée des règles d’autorisation et d’isolation doit être complète.

---

# 25. Arbitrages validés par Jonathan

Les cinq arbitrages ont été validés le 25 juillet 2026.

## ARB-DROIT-001 — Réouverture d’une tâche après cinq minutes

Seuls l’ESM, l’administrateur d’entité et le super-administrateur peuvent réouvrir la tâche. Un motif et un audit sont obligatoires.

## ARB-DROIT-002 — Attribution des responsabilités

L’attribution et le retrait des responsabilités DSM, ESM, Booster et responsable de bureau sont réservés à l’ESM et au super-administrateur. L’administrateur d’entité n’en dispose pas.

## ARB-DROIT-003 — Restauration fonctionnelle par l’ESM

L’ESM peut restaurer dans son entité un profil, un contenu, un événement, un cercle ou un bureau. Les restaurations techniques, massives ou liées aux imports restent réservées à l’administrateur d’entité et au super-administrateur.

## ARB-DROIT-004 — Membres secondaires d’un cercle

Le Booster peut gérer l’appartenance secondaire à son cercle ainsi que les contenus et onboardings liés à ce cercle. Il ne peut pas modifier le cercle principal, le DSM, le client ou le statut d’un membre seulement secondaire.

## ARB-DROIT-005 — Modèles d’onboarding

- le DSM crée des modèles limités à ses consultants ;
- le Booster crée des modèles limités à son cercle ;
- l’ESM, l’administrateur d’entité et le super-administrateur créent des modèles transverses à l’entité ;
- le super-administrateur gère les modèles génériques globaux.

---

# 26. Décisions de droits consolidées

| ID | Décision |
|---|---|
| RIGHTS-001 | Toute permission est refusée par défaut si elle n’est pas explicitement accordée. |
| RIGHTS-002 | Une personne possède une seule entité principale active. |
| RIGHTS-003 | Les autres entités sont accessibles en lecture seule aux employés authentifiés. |
| RIGHTS-004 | Les responsabilités se cumulent dans l’entité principale. |
| RIGHTS-005 | Le DG reçoit automatiquement la responsabilité DSM dans son entité. |
| RIGHTS-006 | Le DSM est limité à ses consultants. |
| RIGHTS-007 | Le Booster est limité à son cercle. |
| RIGHTS-008 | Le responsable de bureau est limité à son bureau. |
| RIGHTS-009 | L’ESM dispose des pouvoirs fonctionnels transverses de son entité. |
| RIGHTS-010 | L’administrateur d’entité administre et supporte son entité uniquement. |
| RIGHTS-011 | Le super-administrateur possède les droits globaux et la purge définitive. |
| RIGHTS-012 | Les collaborateurs ne modifient plus leur profil après validation. |
| RIGHTS-013 | Le nouvel arrivant modifie uniquement les informations personnelles autorisées avant validation. |
| RIGHTS-014 | Les exports respectent toujours le périmètre de consultation. |
| RIGHTS-015 | Les permissions sont recalculées côté API pour chaque requête. |
| RIGHTS-016 | Les changements de rôle, archivages, restaurations et purges sont audités. |
| RIGHTS-017 | Une intervention globale du super-administrateur dans une entité exige une traçabilité renforcée. |
| RIGHTS-018 | Les comptes de service utilisent des scopes limités et ne remplacent pas un utilisateur humain. |
| RIGHTS-019 | La clôture d’une responsabilité révoque immédiatement les permissions associées. |
| RIGHTS-020 | Les contraintes métier peuvent interdire une action pourtant autorisée par le rôle. |
| RIGHTS-021 | Après cinq minutes, seules l’ESM, l’administrateur d’entité et le super-administrateur peuvent réouvrir une tâche. |
| RIGHTS-022 | L’administrateur d’entité ne peut pas attribuer les responsabilités Framework. |
| RIGHTS-023 | L’ESM peut effectuer les restaurations fonctionnelles de son entité. |
| RIGHTS-024 | Le Booster ne peut pas modifier les données hors cercle d’un membre secondaire. |
| RIGHTS-025 | Les modèles DSM et Booster restent limités à leur périmètre. |

---

# 27. Statut du livrable

Cette matrice a été validée par Jonathan le 25 juillet 2026. Elle constitue désormais une référence fonctionnelle verrouillée. Toute modification future devra faire l’objet d’une nouvelle décision explicite et d’un changement de version.

Elle sert d’entrée obligatoire pour :

1. le modèle de données complet ;
2. les diagrammes Mermaid ;
3. les règles d’autorisation FastAPI ;
4. les tests de permissions et d’isolation ;
5. la roadmap et le backlog de réalisation.
