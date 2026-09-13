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
