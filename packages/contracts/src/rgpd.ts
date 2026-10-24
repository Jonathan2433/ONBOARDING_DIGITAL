/**
 * Le suivi d'une demande de droit RGPD — LOT 10, `T14` (API), `T15` (premier
 * écran), `MVP-L10-US008`.
 *
 * UNE SEULE GRILLE, GARDE LECTURE ET ÉCRITURE CONFONDUES
 *
 *   `rolesTraitementDesDemandesRGPD` (ADM-E/SUPER) — aucune portée `Soi` ni
 *   `Limité` : le cahier §21.5 nomme un canal RGPD EXTERNE, jamais un
 *   self-service applicatif. Une seule garde protège les six routes.
 *
 * `enRetard` EST CALCULÉ PAR L'API, JAMAIS PAR CE MODULE
 *
 *   `due_at < instant ET state != closed` — ce module se contente de lire
 *   le booléen rendu, il ne le recalcule jamais côté client : l'instant de
 *   référence est celui du SERVEUR, pas l'horloge du navigateur.
 */
import { CONTRAT_API, endpoint } from './sante.js';
import { estObjet, exigerChaine } from './formes.js';

export const ROLES_TRAITEMENT_DES_DEMANDES_RGPD: readonly string[] =
  CONTRAT_API.rolesTraitementDesDemandesRGPD;

export function peutTraiterLesDemandesRGPD(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_TRAITEMENT_DES_DEMANDES_RGPD.includes(role));
}

/** Les quatre types du modèle §22.3. */
export const TYPES_DE_DEMANDE_RGPD = ['access', 'rectification', 'erasure', 'objection'] as const;
export type TypeDeDemandeRGPD = (typeof TYPES_DE_DEMANDE_RGPD)[number];

export const CHEMIN_DEMANDES_RGPD: string = endpoint('demandesRGPD').chemin;
export const CODES_RECEPTION_RGPD: readonly number[] = endpoint('demandesRGPD').codesExploitables;
export const CODES_DEMANDES_RGPD_EN_LISTE: readonly number[] =
  endpoint('demandesRGPDEnListe').codesExploitables;
export const GABARIT_CHEMIN_UNE_DEMANDE_RGPD: string = endpoint('uneDemandeRGPD').chemin;
export const CODES_UNE_DEMANDE_RGPD: readonly number[] =
  endpoint('uneDemandeRGPD').codesExploitables;
export const GABARIT_CHEMIN_HISTORIQUE_RGPD: string = endpoint('historiqueDUneDemandeRGPD').chemin;
export const CODES_HISTORIQUE_RGPD: readonly number[] = endpoint(
  'historiqueDUneDemandeRGPD',
).codesExploitables;
export const GABARIT_CHEMIN_VERIFICATION_IDENTITE_RGPD: string = endpoint(
  'verificationIdentiteDUneDemandeRGPD',
).chemin;
export const CODES_VERIFICATION_IDENTITE_RGPD: readonly number[] = endpoint(
  'verificationIdentiteDUneDemandeRGPD',
).codesExploitables;
export const GABARIT_CHEMIN_CLOTURE_RGPD: string = endpoint('clotureDUneDemandeRGPD').chemin;
export const CODES_CLOTURE_RGPD: readonly number[] =
  endpoint('clotureDUneDemandeRGPD').codesExploitables;

export function cheminDemandesRGPD(
  page: number,
  taille: number,
  etat?: string,
  typeDemande?: TypeDeDemandeRGPD,
): string {
  const parametres = [
    `page=${encodeURIComponent(String(page))}`,
    `taille=${encodeURIComponent(String(taille))}`,
  ];
  if (etat !== undefined) {
    parametres.push(`etat=${encodeURIComponent(etat)}`);
  }
  if (typeDemande !== undefined) {
    parametres.push(`type_demande=${encodeURIComponent(typeDemande)}`);
  }
  return `${CHEMIN_DEMANDES_RGPD}?${parametres.join('&')}`;
}

function cheminAvecDemande(gabarit: string, demande: string): string {
  if (demande === '') {
    throw new TypeError('identifiant de demande vide');
  }
  return gabarit.replace('{demande}', encodeURIComponent(demande));
}

export function cheminUneDemandeRGPD(demande: string): string {
  return cheminAvecDemande(GABARIT_CHEMIN_UNE_DEMANDE_RGPD, demande);
}
export function cheminHistoriqueRGPD(demande: string): string {
  return cheminAvecDemande(GABARIT_CHEMIN_HISTORIQUE_RGPD, demande);
}
export function cheminVerificationIdentiteRGPD(demande: string): string {
  return cheminAvecDemande(GABARIT_CHEMIN_VERIFICATION_IDENTITE_RGPD, demande);
}
export function cheminClotureRGPD(demande: string): string {
  return cheminAvecDemande(GABARIT_CHEMIN_CLOTURE_RGPD, demande);
}

/** Ce qu'un écran ENVOIE pour réceptionner une demande — `snake_case` voulu. */
export interface DemandeDeReceptionRGPD {
  readonly personne_concernee_id: string;
  readonly type_demande: TypeDeDemandeRGPD;
  readonly canal: string;
}

export interface LigneDeDemandeRGPD {
  readonly identifiant: string;
  readonly personneConcerneeId: string;
  readonly typeDemande: string;
  readonly canal: string;
  readonly recueLe: string;
  readonly identiteVerifiee: boolean;
  readonly responsableId: string;
  readonly echeance: string;
  /** Calculé par l'API — voir l'en-tête du fichier. */
  readonly enRetard: boolean;
  readonly etat: string;
  readonly reponse: string | null;
  readonly clotureeLe: string | null;
  readonly version: number;
}

export interface ReponseDesDemandesRGPD {
  readonly demandes: readonly LigneDeDemandeRGPD[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

export interface EvenementDHistoriqueRGPD {
  readonly survenuLe: string;
  readonly anciennesValeurs: Readonly<Record<string, unknown>> | null;
  readonly nouvellesValeurs: Readonly<Record<string, unknown>> | null;
  readonly acteurId: string | null;
}

export interface ReponseDeLHistoriqueRGPD {
  readonly evenements: readonly EvenementDHistoriqueRGPD[];
}

export interface DemandeDeVerificationIdentiteRGPD {
  readonly version: number;
}
export interface DemandeDeClotureRGPD {
  readonly version: number;
  readonly reponse: string;
}

export interface ReponseDeTransitionRGPD {
  readonly etat: string;
  readonly identiteVerifiee: boolean;
  readonly version: number;
}

function chaineOuNulle(source: Record<string, unknown>, champ: string): string | null {
  const valeur = source[champ];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'string') {
    throw new TypeError(`« ${champ} » ni chaine ni null`);
  }
  return valeur;
}

function objetOuNul(
  source: Record<string, unknown>,
  champ: string,
): Record<string, unknown> | null {
  const valeur = source[champ];
  if (valeur === null) {
    return null;
  }
  if (!estObjet(valeur)) {
    throw new TypeError(`« ${champ} » ni objet ni null`);
  }
  return valeur;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const valeur = source[champ];
  if (typeof valeur !== 'number' || !Number.isInteger(valeur)) {
    throw new TypeError(`« ${champ} » absent ou non entier`);
  }
  return valeur;
}

function booleen(source: Record<string, unknown>, champ: string): boolean {
  const valeur = source[champ];
  if (typeof valeur !== 'boolean') {
    throw new TypeError(`« ${champ} » absent ou non booléen`);
  }
  return valeur;
}

export function validerUneDemandeRGPD(valeur: unknown): LigneDeDemandeRGPD {
  if (!estObjet(valeur)) {
    throw new TypeError('demande RGPD : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    personneConcerneeId: exigerChaine(valeur, 'personne_concernee_id'),
    typeDemande: exigerChaine(valeur, 'type_demande'),
    canal: exigerChaine(valeur, 'canal'),
    recueLe: exigerChaine(valeur, 'recue_le'),
    identiteVerifiee: booleen(valeur, 'identite_verifiee'),
    responsableId: exigerChaine(valeur, 'responsable_id'),
    echeance: exigerChaine(valeur, 'echeance'),
    enRetard: booleen(valeur, 'en_retard'),
    etat: exigerChaine(valeur, 'etat'),
    reponse: chaineOuNulle(valeur, 'reponse'),
    clotureeLe: chaineOuNulle(valeur, 'cloturee_le'),
    version: entier(valeur, 'version'),
  };
}

export function validerLesDemandesRGPD(valeur: unknown): ReponseDesDemandesRGPD {
  if (!estObjet(valeur)) {
    throw new TypeError('demandes RGPD : charge utile non objet');
  }
  const brut = valeur['demandes'];
  if (!Array.isArray(brut)) {
    throw new TypeError('demandes RGPD : « demandes » n’est pas un tableau');
  }
  return {
    demandes: brut.map((d) => validerUneDemandeRGPD(d)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}

function validerUnEvenementDHistoriqueRGPD(
  valeur: unknown,
  rang: number,
): EvenementDHistoriqueRGPD {
  if (!estObjet(valeur)) {
    throw new TypeError(`historique RGPD : evenements[${String(rang)}] non objet`);
  }
  return {
    survenuLe: exigerChaine(valeur, 'survenu_le'),
    anciennesValeurs: objetOuNul(valeur, 'anciennes_valeurs'),
    nouvellesValeurs: objetOuNul(valeur, 'nouvelles_valeurs'),
    acteurId: chaineOuNulle(valeur, 'acteur_id'),
  };
}

export function validerLHistoriqueRGPD(valeur: unknown): ReponseDeLHistoriqueRGPD {
  if (!estObjet(valeur)) {
    throw new TypeError('historique RGPD : charge utile non objet');
  }
  const brut = valeur['evenements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('historique RGPD : « evenements » n’est pas un tableau');
  }
  return { evenements: brut.map((e, rang) => validerUnEvenementDHistoriqueRGPD(e, rang)) };
}

export function validerLaTransitionRGPD(valeur: unknown): ReponseDeTransitionRGPD {
  if (!estObjet(valeur)) {
    throw new TypeError('transition RGPD : charge utile non objet');
  }
  return {
    etat: exigerChaine(valeur, 'etat'),
    identiteVerifiee: booleen(valeur, 'identite_verifiee'),
    version: entier(valeur, 'version'),
  };
}
