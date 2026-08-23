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
  CODES_ENTITE,
  CODES_ENTITES,
  GABARIT_CHEMIN_ENTITE,
  validerLesEntites,
  validerUneEntite,
} from './portail.js';
export type { EntiteDuPortail, ReponseDesEntites } from './portail.js';

export const PACKAGE_NAME = '@onboarding/contracts';
