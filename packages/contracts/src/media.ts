/**
 * Le depot et l'autorisation d'une photo de profil — LOT 11, `T2`.
 *
 * Modele §16.1/§16.2/§12.2, matrice §6.1, `MVP-L11-US004`/`US005`.
 *
 * CINQ ROUTES, AUCUNE NE PARTAGE SA FORME AVEC UNE AUTRE DU CONTRAT
 *
 *   Le depot rend `pending` (le traitement est ASYNCHRONE, voir `app.jobs`
 *   du LOT 11 `T1`) ; l'etat se consulte ensuite par son propre chemin,
 *   `GET …/media/{media}/etat`, puisqu'aucun identifiant de media n'est
 *   connu avant le premier appel. Les droits (`GET …/photo/droits`) sont une
 *   commodite d'ecran, pas une ligne de matrice : voir leur en-tete cote API
 *   (`app/media/routes.py`).
 *
 * LE DEPOT N'A PAS DE VALIDATEUR DE CORPS ENVOYE, ET C'EST DELIBERE
 *
 *   `deposerUnePhoto` (cote `apps/web`) construit un `FormData`, pas un objet
 *   JSON — meme discipline que `depotDUnImport` (LOT 9), qui ne declare pas
 *   non plus de forme de requete dans le manifeste : seule la REPONSE est
 *   validee ici.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

function cheminAppartenance(gabarit: string, code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource —
    //  meme raisonnement que `cheminEntite` (LOT 4) et `cheminFicheArrivee` (LOT 7).
    throw new TypeError('code d’entite ou appartenance vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{appartenance}', encodeURIComponent(appartenance));
}

function booleen(source: Record<string, unknown>, champ: string): boolean {
  const valeur = source[champ];
  if (typeof valeur !== 'boolean') {
    throw new TypeError(`photo : « ${champ} » absent ou non booleen`);
  }
  return valeur;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    throw new TypeError(`photo : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

// ---------------------------------------------------------------------------
//  `POST …/photo` — deposer (ou remplacer) une photo en quarantaine
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_PHOTO: string = endpoint('depotDUnePhoto').chemin;
export const CODES_DEPOT_DE_PHOTO: readonly number[] = endpoint('depotDUnePhoto').codesExploitables;

export function cheminDepotDePhoto(code: string, appartenance: string): string {
  return cheminAppartenance(GABARIT_CHEMIN_PHOTO, code, appartenance);
}

/** Ce que `POST …/photo` rend — le depot vient de commencer, pas encore `ready`. */
export interface DepotDePhoto {
  readonly identifiant: string;
  readonly etat: string;
}

export function validerLeDepotDePhoto(valeur: unknown): DepotDePhoto {
  if (!estObjet(valeur)) {
    throw new TypeError('depot de photo : charge utile non objet');
  }
  return { identifiant: exigerChaine(valeur, 'id'), etat: exigerChaine(valeur, 'state') };
}

// ---------------------------------------------------------------------------
//  `GET …/photo/droits` — ce que l'appelant peut proposer, pour CET ecran
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_DROITS_PHOTO: string = endpoint('droitsDePhoto').chemin;
export const CODES_DROITS_PHOTO: readonly number[] = endpoint('droitsDePhoto').codesExploitables;

export function cheminDroitsDePhoto(code: string, appartenance: string): string {
  return cheminAppartenance(GABARIT_CHEMIN_DROITS_PHOTO, code, appartenance);
}

export interface DroitsDePhoto {
  readonly peutDeposer: boolean;
  readonly peutGererAutorisation: boolean;
}

export function validerLesDroitsDePhoto(valeur: unknown): DroitsDePhoto {
  if (!estObjet(valeur)) {
    throw new TypeError('droits de photo : charge utile non objet');
  }
  return {
    peutDeposer: booleen(valeur, 'peut_deposer'),
    peutGererAutorisation: booleen(valeur, 'peut_gerer_autorisation'),
  };
}

// ---------------------------------------------------------------------------
//  `GET …/media/{media}/etat` — suivre l'avancement du traitement
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_ETAT_MEDIA: string = endpoint('etatDUnMedia').chemin;
export const CODES_ETAT_MEDIA: readonly number[] = endpoint('etatDUnMedia').codesExploitables;

export function cheminEtatDUnMedia(code: string, media: string): string {
  if (code === '' || media === '') {
    throw new TypeError('code d’entite ou media vide');
  }
  return GABARIT_CHEMIN_ETAT_MEDIA.replace('{code}', encodeURIComponent(code)).replace(
    '{media}',
    encodeURIComponent(media),
  );
}

/** `etat` vaut `pending`/`processing`/`ready`/`rejected` — modele §16.1. */
export interface EtatDUnMedia {
  readonly identifiant: string;
  readonly etat: string;
  readonly codeDeRejet: string | null;
}

export function validerLEtatDUnMedia(valeur: unknown): EtatDUnMedia {
  if (!estObjet(valeur)) {
    throw new TypeError('etat de media : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'id'),
    etat: exigerChaine(valeur, 'state'),
    codeDeRejet: chaineOuNul(valeur, 'rejection_code'),
  };
}

// ---------------------------------------------------------------------------
//  `POST …/photo/autorisation` — accorder l'autorisation d'affichage
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_AUTORISATION_PHOTO: string = endpoint('autorisationPhoto').chemin;
export const CODES_AUTORISATION_PHOTO: readonly number[] =
  endpoint('autorisationPhoto').codesExploitables;

export function cheminAutorisationPhoto(code: string, appartenance: string): string {
  return cheminAppartenance(GABARIT_CHEMIN_AUTORISATION_PHOTO, code, appartenance);
}

/** Le corps de `POST …/photo/autorisation` — reste en `snake_case`, voir l'en-tete. */
export interface DemandeDAutorisationDePhoto {
  readonly media_asset_id: string;
}

export interface Autorisation {
  readonly identifiant: string;
  readonly accordeeLe: string;
}

export function validerLAutorisation(valeur: unknown): Autorisation {
  if (!estObjet(valeur)) {
    throw new TypeError('autorisation de photo : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'id'),
    accordeeLe: exigerChaine(valeur, 'granted_at'),
  };
}

// ---------------------------------------------------------------------------
//  `POST …/photo/autorisation/retrait` — retirer toute autorisation active
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_RETRAIT_AUTORISATION_PHOTO: string = endpoint(
  'retraitAutorisationPhoto',
).chemin;
export const CODES_RETRAIT_AUTORISATION_PHOTO: readonly number[] = endpoint(
  'retraitAutorisationPhoto',
).codesExploitables;

export function cheminRetraitAutorisationPhoto(code: string, appartenance: string): string {
  return cheminAppartenance(GABARIT_CHEMIN_RETRAIT_AUTORISATION_PHOTO, code, appartenance);
}

export interface Retrait {
  readonly autorisationsRetirees: number;
}

export function validerLeRetrait(valeur: unknown): Retrait {
  if (!estObjet(valeur)) {
    throw new TypeError('retrait d’autorisation : charge utile non objet');
  }
  const brut = valeur['autorisations_retirees'];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError('retrait d’autorisation : « autorisations_retirees » absent ou non entier');
  }
  return { autorisationsRetirees: brut };
}
