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
  cheminLiensInternes,
  CODES_LIENS_INTERNES,
  GABARIT_CHEMIN_LIENS_INTERNES,
  PROTOCOLES_DE_LIEN_AUTORISES,
  TYPES_DE_LIEN_NOMMES,
  urlEstServable,
  validerLesLiensInternes,
} from './liens.js';
export type { LienInterne, LiensInternes } from './liens.js';
