/**
 * Créer un cercle/bureau et attribuer le Booster/un responsable de bureau —
 * LOT 11, `T3`, hors backlog (`fiche-lot-11.md` §1.2).
 *
 * DEUX GRILLES, PAS UNE SEULE
 *
 *   La CRÉATION réutilise `ROLES_CYCLE_DE_VIE_FRAMEWORK`
 *   (`organisationCycleDeVie.ts`, ESM/ADM-E/SUPER) — le §10.2/§10.3 lui donne
 *   la MÊME grille qu'à l'archivage et la restauration. L'ATTRIBUTION (et le
 *   retrait) du Booster ou d'un responsable de bureau porte une grille
 *   SÉPARÉE, `rolesAttributionFramework` — `ADM-E` EXCLU (§20,
 *   `ARB-DROIT-002` : « l'administrateur d'entité ne peut pas attribuer les
 *   responsabilités Framework »).
 *
 * ATTRIBUER LE BOOSTER, C'EST TOUJOURS REMPLACER ; UN RESPONSABLE DE BUREAU,
 * C'EST TOUJOURS AJOUTER
 *
 *   Voir l'en-tête d'`app/organization/creation.py`. `remplace` dans
 *   `ResultatDAttributionDuBooster` dit à l'écran si un Booster précédent
 *   vient d'être évincé — utile pour le message de confirmation, jamais pour
 *   une décision de permission.
 *
 * LE RETRAIT PARTAGE LA MÊME FORME DE RÉPONSE POUR LES DEUX RESSOURCES
 *
 *   `{affectation}` seul — l'identifiant de la ligne `framework_
 *   responsibility_assignment` désormais fermée. Une seule interface,
 *   `ResultatDeRetraitFramework`, pour les deux routes.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/** Les rôles qui attribuent ou retirent le Booster/un responsable de bureau — ESM/SUPER, `ADM-E` exclu. */
export const ROLES_ATTRIBUTION_FRAMEWORK: readonly string[] = CONTRAT_API.rolesAttributionFramework;

export function peutAttribuerUneResponsabiliteFramework(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_ATTRIBUTION_FRAMEWORK.includes(role));
}

export const GABARIT_CHEMIN_CREATION_DE_CERCLE: string = endpoint('creationDUnCercle').chemin;
export const CODES_CREATION_DE_CERCLE: readonly number[] =
  endpoint('creationDUnCercle').codesExploitables;

export const GABARIT_CHEMIN_CREATION_DE_BUREAU: string = endpoint('creationDUnBureau').chemin;
export const CODES_CREATION_DE_BUREAU: readonly number[] =
  endpoint('creationDUnBureau').codesExploitables;

export const GABARIT_CHEMIN_ATTRIBUTION_DU_BOOSTER: string = endpoint(
  'attributionDuBoosterDUnCercle',
).chemin;
export const CODES_ATTRIBUTION_DU_BOOSTER: readonly number[] = endpoint(
  'attributionDuBoosterDUnCercle',
).codesExploitables;

export const GABARIT_CHEMIN_RETRAIT_DU_BOOSTER: string = endpoint(
  'retraitDuBoosterDUnCercle',
).chemin;
export const CODES_RETRAIT_DU_BOOSTER: readonly number[] = endpoint(
  'retraitDuBoosterDUnCercle',
).codesExploitables;

export const GABARIT_CHEMIN_ATTRIBUTION_D_UN_RESPONSABLE: string = endpoint(
  'attributionDUnResponsableDeBureau',
).chemin;
export const CODES_ATTRIBUTION_D_UN_RESPONSABLE: readonly number[] = endpoint(
  'attributionDUnResponsableDeBureau',
).codesExploitables;

export const GABARIT_CHEMIN_RETRAIT_D_UN_RESPONSABLE: string = endpoint(
  'retraitDUnResponsableDeBureau',
).chemin;
export const CODES_RETRAIT_D_UN_RESPONSABLE: readonly number[] = endpoint(
  'retraitDUnResponsableDeBureau',
).codesExploitables;

function cheminDEntite(gabarit: string, code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return gabarit.replace('{code}', encodeURIComponent(code));
}

export function cheminCreationDUnCercle(code: string): string {
  return cheminDEntite(GABARIT_CHEMIN_CREATION_DE_CERCLE, code);
}

export function cheminCreationDUnBureau(code: string): string {
  return cheminDEntite(GABARIT_CHEMIN_CREATION_DE_BUREAU, code);
}

function cheminDeRessource(
  gabarit: string,
  parametreCible: '{circle_id}' | '{office_id}',
  code: string,
  identifiant: string,
): string {
  if (code === '' || identifiant === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource.
    throw new TypeError('code d’entite ou identifiant de ressource vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace(parametreCible, encodeURIComponent(identifiant));
}

export function cheminAttributionDuBooster(code: string, circleId: string): string {
  return cheminDeRessource(GABARIT_CHEMIN_ATTRIBUTION_DU_BOOSTER, '{circle_id}', code, circleId);
}

export function cheminRetraitDuBooster(code: string, circleId: string): string {
  return cheminDeRessource(GABARIT_CHEMIN_RETRAIT_DU_BOOSTER, '{circle_id}', code, circleId);
}

export function cheminAttributionDUnResponsable(code: string, officeId: string): string {
  return cheminDeRessource(
    GABARIT_CHEMIN_ATTRIBUTION_D_UN_RESPONSABLE,
    '{office_id}',
    code,
    officeId,
  );
}

function cheminRetraitDUnResponsable(
  gabarit: string,
  code: string,
  officeId: string,
  affectationId: string,
): string {
  if (code === '' || officeId === '' || affectationId === '') {
    throw new TypeError('code d’entite ou identifiant de ressource vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{office_id}', encodeURIComponent(officeId))
    .replace('{affectation_id}', encodeURIComponent(affectationId));
}

export function cheminDuRetraitDUnResponsable(
  code: string,
  officeId: string,
  affectationId: string,
): string {
  return cheminRetraitDUnResponsable(
    GABARIT_CHEMIN_RETRAIT_D_UN_RESPONSABLE,
    code,
    officeId,
    affectationId,
  );
}

/**
 * Le corps commun de création — un motif facultatif, obligatoire côté API
 * pour `SUPER` (§18.1).
 *
 * **CHAMPS EN `snake_case`, COMME `DemandeDeCreationDeCollaborateur`
 * (`collaborateurs.ts`)** : ces interfaces sont sérialisées TELLES QUELLES
 * par `JSON.stringify`, et l'API les lit par ces noms exacts — aucune
 * conversion `camelCase` → `snake_case` n'existe dans ce dépôt pour un corps
 * de requête.
 */
export interface DemandeDeCreationDeCercle {
  readonly code: string;
  readonly nom: string;
  readonly jeton_de_couleur?: string | null;
  readonly description?: string | null;
  readonly ordre_d_affichage?: number;
  readonly motif?: string | null;
}

export interface DemandeDeCreationDeBureau {
  readonly code: string;
  readonly nom: string;
  readonly description?: string | null;
  readonly localisation?: string | null;
  readonly ordre_d_affichage?: number;
  readonly motif?: string | null;
}

export interface DemandeDAttributionDeResponsabilite {
  readonly person_id: string;
  readonly motif?: string | null;
}

export interface DemandeDeRetraitFramework {
  readonly motif?: string | null;
}

export interface ResultatDeCreationDeStructure {
  readonly identifiant: string;
  readonly code: string;
  readonly version: number;
}

export interface ResultatDAttributionDuBooster {
  readonly affectation: string;
  readonly remplace: boolean;
}

export interface ResultatDAttributionDUnResponsable {
  readonly affectation: string;
}

export interface ResultatDeRetraitFramework {
  readonly affectation: string;
}

function exigerEntier(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non entier`);
  }
  return brut;
}

function exigerBooleen(valeur: Record<string, unknown>, champ: string): boolean {
  const brut = valeur[champ];
  if (typeof brut !== 'boolean') {
    throw new TypeError(`champ « ${champ} » absent ou non booleen`);
  }
  return brut;
}

export function validerLaCreationDeStructure(valeur: unknown): ResultatDeCreationDeStructure {
  if (!estObjet(valeur)) {
    throw new TypeError('creation de structure : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    code: exigerChaine(valeur, 'code'),
    version: exigerEntier(valeur, 'version'),
  };
}

export function validerLAttributionDuBooster(valeur: unknown): ResultatDAttributionDuBooster {
  if (!estObjet(valeur)) {
    throw new TypeError('attribution du Booster : charge utile non objet');
  }
  return {
    affectation: exigerChaine(valeur, 'affectation'),
    remplace: exigerBooleen(valeur, 'remplace'),
  };
}

export function validerLAttributionDUnResponsable(
  valeur: unknown,
): ResultatDAttributionDUnResponsable {
  if (!estObjet(valeur)) {
    throw new TypeError('attribution d’un responsable de bureau : charge utile non objet');
  }
  return { affectation: exigerChaine(valeur, 'affectation') };
}

export function validerLeRetraitFramework(valeur: unknown): ResultatDeRetraitFramework {
  if (!estObjet(valeur)) {
    throw new TypeError('retrait d’une responsabilite Framework : charge utile non objet');
  }
  return { affectation: exigerChaine(valeur, 'affectation') };
}
