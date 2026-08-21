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
 * CE QU'IL NE CONTIENT PAS, ET CE N'EST PAS UN OUBLI
 *
 *   Aucun type metier : ni `Collaborateur`, ni `Cercle`, ni `Parcours`. Le modele
 *   de donnees appartient au LOT 2, qui n'est pas ouvert.
 */

export {
  CHEMIN_DEMANDE_MAGIC_LINK,
  CHEMIN_LIVE,
  CHEMIN_READY,
  CHEMIN_VERSION,
  CODES_READY,
  CODES_VERSION,
  CONTRAT_API,
  EN_TETE_CORRELATION,
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

export const PACKAGE_NAME = '@onboarding/contracts';
