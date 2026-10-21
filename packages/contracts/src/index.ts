/**
 * Contrat API partage entre le frontend et l'API — point d'entree du paquet.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007.
 *
 * CE QUE CE PAQUET CONTIENT
 *
 *   Le contrat de ce que l'API expose AUJOURD'HUI : les trois endpoints de sante
 *   du cahier 18.7, la racine du prefixe versionne, la demande de magic link du
 *   LOT 3, le nom de l'en-tete de correlation, les formes de reponse et les
 *   fonctions qui les VALIDENT.
 *
 *   La source unique est `contrat-api.json`, lu par ce paquet ET par un controle
 *   Python qui verifie que le schema OpenAPI reellement servi le respecte. Une
 *   route ajoutee, retiree ou renommee sans mise a jour du manifeste fait donc
 *   echouer `make test-integration`.
 *
 * CE QU'IL CONTIENT DEPUIS LE LOT 4
 *
 *   La liste des entites du portail national — la PREMIERE forme metier du
 *   contrat. Le commentaire qui figurait ici disait « aucun type metier : le
 *   modele de donnees appartient au LOT 2, qui n'est pas ouvert ». Les LOTS 2 et
 *   3 sont faits, le LOT 4 est ouvert, et la page nationale est son premier
 *   ecran.
 *
 *   Ni `Collaborateur` ni `Cercle` ni `Parcours` pour autant : ils appartiennent
 *   aux LOTS 5, 6 et 7.
 */

export {
  CHEMIN_CHANGEMENT_MOT_DE_PASSE,
  CHEMIN_DECONNEXION,
  CHEMIN_CONNEXION_ADMINISTRATEUR,
  CHEMIN_CONSOMMATION_MAGIC_LINK,
  CHEMIN_DEMANDE_MAGIC_LINK,
  CHEMIN_LIVE,
  CHEMIN_READY,
  CHEMIN_SESSION,
  CHEMIN_VERSION,
  CODES_READY,
  CODES_VERSION,
  CONTRAT_API,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  endpoint,
  PREFIXE_VERSIONNE,
  validerEtatServices,
  validerVersion,
} from './sante.js';
export type {
  Dependance,
  EndpointContrat,
  EtatServices,
  StatutDependance,
  StatutGlobal,
  Version,
} from './sante.js';

//  LOT 4, T1 — la premiere forme METIER du contrat. `formes.ts` n'est PAS
//  reexporte : un consommateur qui validerait lui-meme ne passerait plus par les
//  validateurs du contrat, et le controle perdrait son objet.
export {
  CHEMIN_ENTITES,
  cheminEntite,
  cheminPermissions,
  CODES_ENTITE,
  CODES_ENTITES,
  CODES_PERMISSIONS,
  GABARIT_CHEMIN_ENTITE,
  GABARIT_CHEMIN_PERMISSIONS,
  ROLES_ADMINISTRATION,
  ROLES_ADMINISTRATION_ONBOARDING,
  validerLesEntites,
  validerLesPermissions,
  validerUneEntite,
} from './portail.js';
export type { EntiteDuPortail, PermissionsDeLEntite, ReponseDesEntites } from './portail.js';

//  LOT 5, T2 — le trombinoscope pagine. Meme montage : la frontiere
//  `snake_case` -> `camelCase` est ICI, en un seul endroit, et le validateur
//  n'est pas contournable puisque `formes.ts` n'est pas reexporte.
export {
  CODES_TROMBINOSCOPE,
  GABARIT_CHEMIN_TROMBINOSCOPE,
  LONGUEUR_MAXIMALE_RECHERCHE,
  STATUTS_PROFESSIONNELS,
  TAILLES_DE_PAGE,
  TAILLE_PAR_DEFAUT,
  cheminDePhotoOuNul,
  cheminTrombinoscope,
  validerLeTrombinoscope,
} from './trombinoscope.js';
export type {
  CercleDeLaListe,
  CollaborateurDuTrombinoscope,
  FiltresDuTrombinoscope,
  ReponseDuTrombinoscope,
} from './trombinoscope.js';

//  LOT 5, T4 — la fiche profil. La frontiere `snake_case` -> `camelCase` est ICI,
//  comme pour le trombinoscope, et le validateur n'est pas contournable.
export { cheminProfil, CODES_PROFIL, GABARIT_CHEMIN_PROFIL, validerLaFiche } from './profil.js';
//  LOT 5, T5 — `cheminDePhotoOuNul` est exportee depuis `trombinoscope.js`, ou
//  elle vit : la liste ET la fiche l'emploient, et une reexportation depuis
//  `profil.js` donnerait deux chemins vers une meme fonction.
export type { CercleDuProfil, FicheDuProfil, ResponsabiliteDuProfil } from './profil.js';

//  LOT 5, T11 — l'historique organisationnel, servi par l'API depuis `T9` et
//  qu'aucun ecran ne lisait. Le validateur porte la distinction que tout le
//  reste du dispositif a construite : `null` = hors perimetre, `[]` = rien a
//  montrer. L'absorber « pour simplifier l'ecran » ferait affirmer FAUX.
export {
  AXES_DE_L_HISTORIQUE,
  cheminHistorique,
  CODES_HISTORIQUE,
  GABARIT_CHEMIN_HISTORIQUE,
  validerLHistorique,
} from './historique.js';
export type {
  AxeDeLHistorique,
  HistoriqueOrganisationnel,
  PeriodeDeCercle,
  PeriodeDeDsm,
  PeriodeDeMetier,
  PeriodeDeResponsabilite,
  PeriodeDeStatut,
} from './historique.js';

//  LOT 5, T11 — le cycle de vie d'un profil : archiver, restaurer, et lire la
//  fiche d'un archive. L'API le sert depuis `T8`, sans consommateur. Les roles
//  sont LUS DU MANIFESTE et declares separement de `rolesAdministration`, qui
//  porte les memes trois valeurs pour une AUTRE raison : les fusionner ferait
//  suivre l'une quand la matrice change l'autre, en silence.
export {
  cheminArchivage,
  cheminFicheArchivee,
  cheminRestauration,
  CODES_ARCHIVAGE,
  CODES_FICHE_ARCHIVEE,
  CODES_RESTAURATION,
  GABARIT_CHEMIN_ARCHIVAGE,
  GABARIT_CHEMIN_FICHE_ARCHIVEE,
  GABARIT_CHEMIN_RESTAURATION,
  peutGererLeCycleDeVie,
  ROLES_DU_CYCLE_DE_VIE,
  validerLeResultat,
} from './cycleDeVie.js';
export type { ResultatDuCycleDeVie } from './cycleDeVie.js';

export const PACKAGE_NAME = '@onboarding/contracts';

//  LOT 6, T2 : la page Framework. TROIS familles, et le cahier §10.3 les nomme.
export {
  cheminFramework,
  CODES_FRAMEWORK,
  GABARIT_CHEMIN_FRAMEWORK,
  RESPONSABILITES_FRAMEWORK,
  validerLaPageFramework,
} from './framework.js';
export type {
  CarteDeBureau,
  CarteDeCercle,
  CarteDeResponsabilite,
  PageFramework,
  ResponsabiliteFramework,
  TitulaireFramework,
} from './framework.js';

//  LOT 6, T3 : la page detaillee d'un cercle. La couleur n'est jamais seule, et
//  c'est le TYPE qui le tient — §8.1 du modele, pas seulement la roadmap.
export {
  cheminCercle,
  CODES_CERCLE,
  GABARIT_CHEMIN_CERCLE,
  TYPES_D_APPARTENANCE_AU_CERCLE,
  validerLaPageDuCercle,
} from './cercles.js';
export type {
  MembreDuCercle,
  PageDuCercle,
  TitulaireDuCercle,
  TypeDAppartenanceAuCercle,
} from './cercles.js';

//  LA PAGE DETAILLEE D'UN BUREAU — LOT 6, `T4`.
//  `RESPONSABLES_MINIMUM` et `RESPONSABLES_MAXIMUM` sont exportes pour qu'un
//  ecran puisse SIGNALER l'ecart au §8.4, jamais pour qu'un validateur l'impose :
//  la borne n'est pas tenue en base, et le declencheur qui la tiendra est en
//  `T7` (`DEC-583`). `respecteLaBorneDuHuitQuatre` porte cette question.
export {
  cheminBureau,
  CODES_BUREAU,
  GABARIT_CHEMIN_BUREAU,
  respecteLaBorneDuHuitQuatre,
  RESPONSABLES_MAXIMUM,
  RESPONSABLES_MINIMUM,
  validerLaPageDuBureau,
} from './bureaux.js';
export type { PageDuBureau, ResponsableDuBureau } from './bureaux.js';

//  LE RENDU DES BLOCS — LOT 6, `T5`.
//  `texteDuBloc` rend une `string` et rien d'autre : un ecran qui passe par elle
//  ne peut pas obtenir de balisage a interpreter, quelle que soit la donnee
//  stockee (§7.35). Les clefs du contenu ne sont pas contraintes — `QO-121`.
export {
  cheminPageDeContenu,
  CODES_PAGE_DE_CONTENU,
  GABARIT_CHEMIN_PAGE_DE_CONTENU,
  texteDuBloc,
  TYPES_DE_PAGE_NOMMES,
  validerLaPageDeContenu,
  validerUnBlocDeContenu,
} from './contenus.js';
export type { BlocDeContenu, PageDeContenu } from './contenus.js';

//  LES LIENS INTERNES — LOT 6, `T8`, `MVP-L06-US005`.
//  **LA LECTURE SEULE**, comme `T2` a `T5` : une sous-etape qui sert une lecture
//  pose son module de contrat, celles qui servent une ecriture ne le font pas —
//  `T6` et `T7` n'ont rien ajoute ici. Les ecrans de lecture sont `T9`.
//  `PROTOCOLES_DE_LIEN_AUTORISES` est LU DU MANIFESTE (`DEC-587`, `QO-120`) pour
//  qu'un formulaire puisse dire ce qui est accepte avant que l'API ne refuse ; il
//  ne decide rien, l'API restant l'autorite finale (matrice §2.6).
export {
  cheminCreationDeLien,
  cheminGestionDesLiens,
  cheminLiensInternes,
  cheminModificationDeLien,
  cheminOrdreDesLiens,
  CODES_CREATION_DE_LIEN,
  CODES_GESTION_DES_LIENS,
  CODES_LIENS_INTERNES,
  CODES_MODIFICATION_DE_LIEN,
  CODES_ORDRE_DES_LIENS,
  GABARIT_CHEMIN_CREATION_DE_LIEN,
  GABARIT_CHEMIN_GESTION_DES_LIENS,
  GABARIT_CHEMIN_LIENS_INTERNES,
  GABARIT_CHEMIN_MODIFICATION_DE_LIEN,
  GABARIT_CHEMIN_ORDRE_DES_LIENS,
  peutGererLesLiensInternes,
  PROTOCOLES_DE_LIEN_AUTORISES,
  ROLES_GESTION_DES_LIENS_INTERNES,
  TYPES_DE_LIEN_NOMMES,
  urlEstServable,
  validerLesLiensInternes,
  validerUnLienInterneServi,
} from './liens.js';
export type {
  DemandeDeChampsDeLien,
  DemandeDeCreationDeLien,
  DemandeDeModificationDeLien,
  DemandeDOrdreDesLiens,
  LienInterne,
  LiensInternes,
} from './liens.js';

//  L'ECRITURE EDITORIALE, LE CYCLE DE VIE D'UN CONTENU ET SA GESTION — LOT 6,
//  `T10`. `contenus.ts` reste T5/lecture seule ; ce module porte ce que `T6`,
//  `T7` et `T10` ont ajoute, dont les deux routes que `T10` a du poser pour
//  qu'un editeur puisse relire un BROUILLON avec sa `version`.
export {
  cheminArchivageDuContenu,
  cheminCreationDePage,
  cheminEcritureDuContenu,
  cheminPagesDeGestion,
  cheminPageDeGestion,
  cheminPublication,
  cheminRestaurationDuContenu,
  CODES_ARCHIVAGE_DU_CONTENU,
  CODES_CREATION_DE_PAGE,
  CODES_ECRITURE_DU_CONTENU,
  CODES_PAGES_DE_GESTION,
  CODES_PAGE_DE_GESTION,
  CODES_PUBLICATION,
  CODES_RESTAURATION_DU_CONTENU,
  GABARIT_CHEMIN_ARCHIVAGE_DU_CONTENU,
  GABARIT_CHEMIN_CREATION_DE_PAGE,
  GABARIT_CHEMIN_ECRITURE_DU_CONTENU,
  GABARIT_CHEMIN_PAGES_DE_GESTION,
  GABARIT_CHEMIN_PAGE_DE_GESTION,
  GABARIT_CHEMIN_PUBLICATION,
  GABARIT_CHEMIN_RESTAURATION_DU_CONTENU,
  peutCreerUnContenu,
  peutEditerUnContenu,
  peutRestaurerUnContenu,
  ROLES_CREATION_DE_CONTENU,
  ROLES_ECRITURE_EDITORIALE,
  ROLES_RESTAURATION_D_UN_CONTENU,
  validerLaPageCreee,
  validerLaPageDeContenuPourEdition,
  validerLaTransitionDeContenu,
  validerLEcritureDuContenu,
  validerLesPagesDeGestion,
} from './gestionDuContenu.js';
export type {
  BlocSoumis,
  ContenuEcrit,
  DemandeDeCreationDePage,
  DemandeDEcritureDuContenu,
  DemandeDeTransition,
  PageCreee,
  PageDeContenuPourEdition,
  PageDeGestion,
  ReponseDesPagesDeGestion,
  TransitionDeContenu,
} from './gestionDuContenu.js';

//  LA FICHE D'ARRIVEE — LECTURE (`T2`) ET ECRITURE (`T3`, consommees par
//  `T13`, premier ecran). `DemandeDe...` restent en `snake_case`, le format
//  que l'API attend — seules les REPONSES validees passent en `camelCase`.
export {
  cheminFicheArrivee,
  cheminValidationFicheArrivee,
  CODES_COMPLETION_FICHE_ARRIVEE,
  CODES_FICHE_ARRIVEE,
  CODES_VALIDATION_FICHE_ARRIVEE,
  GABARIT_CHEMIN_FICHE_ARRIVEE,
  GABARIT_CHEMIN_VALIDATION_FICHE_ARRIVEE,
  validerLaCompletion,
  validerLaFicheArrivee,
  validerLaValidation,
} from './ficheArrivee.js';
export type {
  CercleDeLaFicheArrivee,
  CompletionDeFiche,
  DemandeDeCompletionDeFiche,
  DemandeDeValidationDeFiche,
  FicheArrivee,
  ValidationDeFiche,
} from './ficheArrivee.js';

//  LE CATALOGUE DES TACHES EN LECTURE — LOT 7, `T4`, ferme `ECART-013`. Meme
//  partage : la CREATION, qui ECRIT, n'a pas de module de contrat propre.
export {
  cheminCatalogueDeTaches,
  CODES_CATALOGUE_DE_TACHES,
  GABARIT_CHEMIN_CATALOGUE_DE_TACHES,
  validerLeCatalogueDeTaches,
  validerUneTacheDeReference,
} from './catalogueDesTaches.js';
export type {
  CatalogueDeTaches,
  DemandeDeTacheDeReference,
  TacheDeReference,
} from './catalogueDesTaches.js';

//  LE PARCOURS D'ONBOARDING — LOT 7, `T7`. UN SEUL MODULE POUR DEUX VERBES :
//  affecter (`POST`) et consulter (`GET`) rendent la MEME forme. `T13` y
//  ajoute les DEUX actions `Soi` du §8.1 — terminer, annuler — qui rendent la
//  meme forme qu'une ligne de `taches`.
export {
  cheminAnnulationDeTache,
  cheminCompletionDeTache,
  cheminDuParcours,
  CODES_AFFECTATION_DU_PARCOURS,
  CODES_ANNULATION_DE_TACHE,
  CODES_COMPLETION_DE_TACHE,
  CODES_LECTURE_DU_PARCOURS,
  GABARIT_CHEMIN_ANNULATION_DE_TACHE,
  GABARIT_CHEMIN_COMPLETION_DE_TACHE,
  GABARIT_CHEMIN_PARCOURS,
  validerLeParcours,
  validerUneTacheDuParcours,
} from './parcoursOnboarding.js';
export type {
  InstanceDeParcours,
  Parcours,
  ProgressionDuParcours,
  TacheDuParcours,
} from './parcoursOnboarding.js';

//  LES MODELES D'ONBOARDING ET LEUR CYCLE DE VIE — LOT 7, `T14`. Cinq routes
//  d'ECRITURE posees sans module de contrat par `T5`/`T6` ; `T14`, premier
//  ecran consommateur, pose la LECTURE ET les cinq formes d'ecriture ensemble.
export {
  cheminArchivageDeVersion,
  cheminModelesOnboarding,
  cheminPublicationDeVersion,
  cheminRestaurationDeVersion,
  cheminTachesDeVersion,
  cheminVersionsDeModele,
  CODES_ARCHIVAGE_DE_VERSION,
  CODES_CONSULTATION_DES_MODELES,
  CODES_CREATION_D_UN_MODELE,
  CODES_CREATION_D_UNE_VERSION,
  CODES_DEFINITION_DES_TACHES,
  CODES_PUBLICATION_DE_VERSION,
  CODES_RESTAURATION_DE_VERSION,
  GABARIT_CHEMIN_MODELES_ONBOARDING,
  ROLES_RESTAURATION_DES_MODELES_ONBOARDING,
  validerLArchivageDeVersion,
  validerLaPublicationDeVersion,
  validerLaRestaurationDeVersion,
  validerLesModelesOnboarding,
  validerLesTachesDeVersion,
  validerUneVersionCreee,
  validerUnModeleCree,
} from './modelesOnboarding.js';
export type {
  DemandeDeModeleOnboarding,
  DemandeDesTachesDeVersion,
  DemandeDeTacheDeVersion,
  DemandeDeVersionDeModele,
  ModeleOnboardingAvecVersions,
  ModeleOnboardingCree,
  PageDesModelesOnboarding,
  TacheDeVersion,
  TachesDeVersion,
  VersionArchivee,
  VersionDeModeleOnboarding,
  VersionPubliee,
  VersionRestauree,
} from './modelesOnboarding.js';

//  LE SUIVI DES TACHES EN RETARD PAR PERIMETRE — LOT 7, `T12`/`T14`. La forme
//  du manifeste attendait son premier ecran depuis `T12` — meme parti que le
//  catalogue de `T4`.
export {
  cheminSuiviOnboarding,
  CODES_SUIVI_ONBOARDING,
  GABARIT_CHEMIN_SUIVI_ONBOARDING,
  validerLeSuiviOnboarding,
} from './suiviOnboarding.js';
export type { PageDeSuiviOnboarding, TacheEnRetardDuSuivi } from './suiviOnboarding.js';

//  LES EVENEMENTS — LOT 8. LA LECTURE (`T2`, `T9`) ET LA GESTION (`T3` A
//  `T6`, exposee par `T10`). Meme partage que `liens.js` : une sous-etape qui
//  sert une lecture ou une ecriture pose son module de contrat quand un
//  ecran en a besoin — `T10` est le premier ecran a consommer les six
//  verbes d'ecriture et les deux lectures de gestion.
export {
  cheminAnnulationDEvenement,
  cheminArchivageDEvenement,
  cheminEvenement,
  cheminEvenements,
  cheminEvenementPourGestion,
  cheminEvenementsPourGestion,
  cheminMediasDEvenement,
  cheminPublicationDEvenement,
  cheminRestaurationDEvenement,
  CLASSEMENTS_D_EVENEMENTS,
  CODES_ANNULATION_D_EVENEMENT,
  CODES_ARCHIVAGE_D_EVENEMENT,
  CODES_CREATION_D_EVENEMENT,
  CODES_EVENEMENT_POUR_GESTION,
  CODES_EVENEMENTS,
  CODES_EVENEMENTS_POUR_GESTION,
  CODES_MEDIAS_D_EVENEMENT,
  CODES_MODIFICATION_D_EVENEMENT,
  CODES_PUBLICATION_D_EVENEMENT,
  CODES_RESTAURATION_D_EVENEMENT,
  GABARIT_CHEMIN_EVENEMENTS,
  peutGererLesEvenements,
  peutRestaurerUnEvenement,
  ROLES_GESTION_DES_EVENEMENTS,
  ROLES_RESTAURATION_D_UN_EVENEMENT,
  validerLaPageDesEvenements,
  validerLesEvenementsPourGestion,
  validerLesMediasDEvenement,
  validerLEvenementAnnule,
  validerLEvenementArchive,
  validerLEvenementCree,
  validerLEvenementEcrit,
  validerLEvenementPourGestion,
  validerLEvenementRestaure,
} from './evenements.js';
export type {
  ClassementEvenement,
  DemandeDAnnulationDEvenement,
  DemandeDeCreationDEvenement,
  DemandeDeGestionDesMediasDEvenement,
  DemandeDeModificationDEvenement,
  DemandeDePublicationDEvenement,
  DemandeDeTransitionDEvenement,
  EvenementAnnule,
  EvenementArchive,
  EvenementCree,
  EvenementDeGestion,
  EvenementDuClassement,
  EvenementEcrit,
  EvenementPourGestion,
  EvenementRestaure,
  EvenementsPourGestion,
  MediaDEvenement,
  MediasDEvenement,
  MediaSoumis,
  PageDesEvenements,
  PorteeDeCreationEvenement,
} from './evenements.js';

//  L'AGREGAT D'ACCUEIL — LOT 8, `T8` (API) puis `T11` (ecran), `MVP-L08-US001`
//  (2/2) et `MVP-L08-US006` (2/2). Premier module de contrat pour « arrivees
//  recentes » (`T7` n'en avait pose aucun, faute d'ecran consommateur) ; les
//  quatre autres sections delegient a `framework.ts`/`evenements.ts`/
//  `liens.ts`/`contenus.ts`, jamais revalidees une seconde fois ici.
export {
  cheminAccueil,
  CODES_ACCUEIL,
  GABARIT_CHEMIN_ACCUEIL,
  validerLaPageDesArriveesRecentes,
  validerLAccueil,
} from './accueil.js';
export type { AccueilDEntite, ArriveeRecente, PageDesArriveesRecentes } from './accueil.js';

//  LE CATALOGUE DES METIERS — LOT 9, `T14`, pose en construisant l'ecran :
//  aucune sous-etape anterieure ne servait cette liste.
export {
  cheminCatalogueDesMetiers,
  CODES_CATALOGUE_DES_METIERS,
  GABARIT_CHEMIN_CATALOGUE_DES_METIERS,
  validerLeCatalogueDesMetiers,
} from './catalogueDesMetiers.js';
export type { CatalogueDesMetiers, MetierDuCatalogue } from './catalogueDesMetiers.js';

//  LES ECRANS BACK-OFFICE — LOT 9, `T14`. Six modules, un par domaine deja
//  construit par `T2` a `T12` sans aucun ecran consommateur jusqu'ici — meme
//  partage que le catalogue de taches (LOT 7, `T4`/`T14`) et le suivi
//  d'onboarding : la ROUTE existe depuis sa sous-etape, le MODULE DE CONTRAT
//  depuis le premier ecran qui en a besoin.
export {
  cheminApercuDuTransfertEnMasse,
  cheminChangementDEntite,
  cheminCreationDeCollaborateur,
  cheminTransfertEnMasse,
  CODES_APERCU_DU_TRANSFERT,
  CODES_CHANGEMENT_D_ENTITE,
  CODES_CREATION_DE_COLLABORATEUR,
  CODES_TRANSFERT_EN_MASSE,
  GABARIT_CHEMIN_APERCU_DU_TRANSFERT,
  GABARIT_CHEMIN_CHANGEMENT_D_ENTITE,
  GABARIT_CHEMIN_CREATION_DE_COLLABORATEUR,
  GABARIT_CHEMIN_TRANSFERT_EN_MASSE,
  peutEcrireSurUnCollaborateur,
  ROLES_ECRITURE,
  validerLeChangementDEntite,
  validerLeCollaborateurCree,
  validerLeTransfertEnMasse,
} from './collaborateurs.js';
export type {
  ChangementDEntite,
  CollaborateurCree,
  DemandeDeChangementDEntite,
  DemandeDeCreationDeCollaborateur,
  DemandeDeTransfertEnMasse,
  ElementDeTransfertEnMasse,
  ReponseDeTransfertEnMasse,
  ResultatDeTransfert,
} from './collaborateurs.js';

export {
  cheminArchivageDUnBureau,
  cheminArchivageDUnCercle,
  cheminRestaurationDUnBureau,
  cheminRestaurationDUnCercle,
  CODES_ARCHIVAGE_DU_BUREAU,
  CODES_ARCHIVAGE_DU_CERCLE,
  CODES_RESTAURATION_DU_BUREAU,
  CODES_RESTAURATION_DU_CERCLE,
  GABARIT_CHEMIN_ARCHIVAGE_DU_BUREAU,
  GABARIT_CHEMIN_ARCHIVAGE_DU_CERCLE,
  GABARIT_CHEMIN_RESTAURATION_DU_BUREAU,
  GABARIT_CHEMIN_RESTAURATION_DU_CERCLE,
  peutGererLeCycleDeVieDeLaStructure,
  ROLES_CYCLE_DE_VIE_FRAMEWORK,
  validerLArchivageDeStructure,
  validerLaRestaurationDeStructure,
} from './organisationCycleDeVie.js';
export type {
  DemandeDeTransitionDeStructure,
  ResultatDArchivageDeStructure,
  ResultatDeRestaurationDeStructure,
} from './organisationCycleDeVie.js';

export {
  cheminTableauDeBord,
  CODES_TABLEAU_DE_BORD,
  GABARIT_CHEMIN_TABLEAU_DE_BORD,
  peutConsulterLeTableauDeBord,
  ROLES_TABLEAU_DE_BORD,
  validerLeTableauDeBord,
} from './tableauDeBord.js';
export type { ImportEnEchec, TableauDeBord } from './tableauDeBord.js';

export {
  CHEMIN_CREATION_D_ENTITE,
  CODES_CREATION_D_ENTITE,
  peutCreerUneEntite,
  ROLE_SUPER_ADMINISTRATEUR,
  validerLEntiteCreee,
} from './creationDEntite.js';
export type { DemandeDeCreationDEntite, EntiteCreee } from './creationDEntite.js';

export {
  cheminDecision,
  cheminDepotDImport,
  cheminLancement,
  cheminListeDesClients,
  cheminRapport,
  cheminRejeu,
  CODES_CLIENTS,
  CODES_DECISION,
  CODES_DEPOT_D_IMPORT,
  CODES_LANCEMENT,
  CODES_RAPPORT,
  CODES_REJEU,
  GABARIT_CHEMIN_CLIENTS,
  GABARIT_CHEMIN_DECISION,
  GABARIT_CHEMIN_DEPOT_D_IMPORT,
  GABARIT_CHEMIN_LANCEMENT,
  GABARIT_CHEMIN_RAPPORT,
  GABARIT_CHEMIN_REJEU,
  peutDeposerUnImport,
  peutValiderLesRapprochements,
  ROLES_DEPOT_DE_L_IMPORT,
  ROLES_VALIDATION_DES_RAPPROCHEMENTS,
  TYPES_DE_DECISION,
  validerLaDecision,
  validerLeLancement,
  validerLeLotDepose,
  validerLeRapport,
  validerLeRejeu,
  validerLesClients,
} from './imports.js';
export type {
  ClientDuCatalogue,
  DecisionEnregistree,
  DemandeDeDecision,
  LigneDuRapport,
  LotDepose,
  ProblemeDeLigne,
  Reconciliation,
  RapportDImport,
  ReponseDeLancement,
  ReponseDeRejeu,
  ReponseDesClients,
  TypeDeDecision,
} from './imports.js';

//  LE SIGNALEMENT D'UN BUG — LOT 10, `T11`, `MVP-L10-US005`. Aucun code
//  d'entite dans le chemin -- voir l'en-tete de `signalement.ts`.
export { CHEMIN_SIGNALEMENT, CODES_SIGNALEMENT, validerUnSignalement } from './signalement.js';
export type { DemandeDeSignalement, SignalementServi } from './signalement.js';
