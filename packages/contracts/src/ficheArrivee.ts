/**
 * Le contrat de la fiche d'arrivee, en lecture — LOT 7, `T2`.
 *
 * Cahier §9.4, modele §12.1. « Une sous-etape qui sert une LECTURE pose son
 * module de contrat » — le meme partage que `liens.ts` (LOT 6, `T8`) : `T3`,
 * qui ECRIT, n'en ajoutera pas un second.
 *
 * `identifiant` ET `version` PEUVENT VALOIR `null` : aucune ligne
 * `arrival_profile` n'existe tant que `T3` ne l'a pas creee. Un ecran qui
 * recoit les deux `null` sait qu'il doit CREER, jamais mettre a jour.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin de la fiche d'arrivee, lu du manifeste — `DEC-492`. */
export const GABARIT_CHEMIN_FICHE_ARRIVEE: string = endpoint('ficheDArrivee').chemin;

/** Les codes exploitables de la lecture. */
export const CODES_FICHE_ARRIVEE: readonly number[] = endpoint('ficheDArrivee').codesExploitables;

/** Le chemin de la fiche d'arrivee d'une appartenance, ses deux segments encodes. */
export function cheminFicheArrivee(code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource —
    //  meme raisonnement que `cheminEntite` du LOT 4.
    throw new TypeError('code d’entite ou appartenance vide');
  }
  return GABARIT_CHEMIN_FICHE_ARRIVEE.replace('{code}', encodeURIComponent(code)).replace(
    '{appartenance}',
    encodeURIComponent(appartenance),
  );
}

export interface CercleDeLaFicheArrivee {
  readonly code: string;
  readonly nom: string;
  readonly jetonDeCouleur: string | null;
}

export interface FicheArrivee {
  /** `null` tant qu'aucune ligne `arrival_profile` n'existe. */
  readonly identifiant: string | null;
  readonly version: number | null;
  readonly etat: string;
  readonly appartenance: string;
  readonly personne: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nomPrefere: string | null;
  readonly dateDArrivee: string;
  readonly metier: string | null;
  readonly statut: string | null;
  readonly client: string | null;
  readonly dsm: string | null;
  readonly cerclePrincipal: CercleDeLaFicheArrivee | null;
  readonly presentationCourte: string | null;
  readonly funFact: string | null;
  readonly valideeLe: string | null;
  readonly publieeLe: string | null;
  readonly recenteJusquAu: string | null;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`fiche d’arrivee : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entierOuNul(source: Record<string, unknown>, champ: string): number | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`fiche d’arrivee : « ${champ} » ni entier ni null`);
  }
  return brut;
}

function cercleOuNul(source: Record<string, unknown>): CercleDeLaFicheArrivee | null {
  const brut = source['cercle_principal'];
  if (brut === null) {
    return null;
  }
  if (!estObjet(brut)) {
    throw new TypeError('fiche d’arrivee : « cercle_principal » ni objet ni null');
  }
  return {
    code: exigerChaine(brut, 'code'),
    nom: exigerChaine(brut, 'nom'),
    jetonDeCouleur: chaineOuNul(brut, 'jeton_de_couleur'),
  };
}

/** Valider ce que `GET …/arrival-profile` a rendu. */
export function validerLaFicheArrivee(valeur: unknown): FicheArrivee {
  if (!estObjet(valeur)) {
    throw new TypeError('fiche d’arrivee : charge utile non objet');
  }
  const identifiant = chaineOuNul(valeur, 'id');
  const version = entierOuNul(valeur, 'version');
  //  **LES DEUX SONT NULS ENSEMBLE, OU AUCUN DES DEUX.** Une reponse qui n'en
  //  rendrait qu'un serait malformee : voir l'en-tete du module.
  if ((identifiant === null) !== (version === null)) {
    throw new TypeError('fiche d’arrivee : « id » et « version » doivent etre nuls ensemble');
  }
  return {
    identifiant,
    version,
    etat: exigerChaine(valeur, 'state'),
    appartenance: exigerChaine(valeur, 'entity_membership_id'),
    personne: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'first_name'),
    nom: exigerChaine(valeur, 'last_name'),
    nomPrefere: chaineOuNul(valeur, 'preferred_name'),
    dateDArrivee: exigerChaine(valeur, 'arrival_date'),
    metier: chaineOuNul(valeur, 'metier'),
    statut: chaineOuNul(valeur, 'statut'),
    client: chaineOuNul(valeur, 'client'),
    dsm: chaineOuNul(valeur, 'dsm'),
    cerclePrincipal: cercleOuNul(valeur),
    presentationCourte: chaineOuNul(valeur, 'short_intro'),
    funFact: chaineOuNul(valeur, 'fun_fact'),
    valideeLe: chaineOuNul(valeur, 'validated_at'),
    publieeLe: chaineOuNul(valeur, 'published_at'),
    recenteJusquAu: chaineOuNul(valeur, 'recent_until'),
  };
}
