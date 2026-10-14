/**
 * Le cycle de vie d'un cercle ou d'un bureau — LOT 9, `T4` (API) puis `T14` (écran).
 *
 * `ARB-DROIT-003` NOMME CINQ RESSOURCES, DONT DEUX N'AVAIENT AUCUN MÉCANISME
 *
 *   Profil (LOT 5), contenu et événement (LOT 6/8) avaient déjà archivage ET
 *   restauration. Cercle et bureau n'avaient AUCUN DES DEUX, un trou nommé par
 *   `T3` du LOT 6 et comblé seulement ici, treize sous-étapes plus tard. `T4`
 *   pose les quatre routes, `T14` les consomme pour la première fois.
 *
 * UNE SEULE GRILLE, LES DEUX RESSOURCES, LES DEUX ACTIONS
 *
 *   `ROLES_CYCLE_DE_VIE_FRAMEWORK` (ESM/ADM-E/SUPER) gouverne l'archivage ET la
 *   restauration du cercle ET du bureau — contrairement au profil (LOT 5), où
 *   `T8` avait mesuré une asymétrie, ici le §10.2/§10.3 ne la porte pas.
 *   **DÉCLARÉE SÉPARÉMENT de `ROLES_DU_CYCLE_DE_VIE`** (le profil) : les deux
 *   portent aujourd'hui les mêmes trois rôles, et c'est une coïncidence, pas
 *   une dérivation (§7.27) — les fusionner ferait suivre l'une quand la
 *   matrice change l'autre, en silence.
 *
 * LES DEUX RÉPONSES ONT LA MÊME FORME, ET C'EST MESURÉ
 *
 *   `{version, archive_le}` pour l'archivage, `{version}` seul pour la
 *   restauration — contrairement au cycle de vie du profil (`cycleDeVie.ts`),
 *   qui porte des champs riches (sessions révoquées, relations closes). Ici,
 *   archiver un cercle ou un bureau ne touche NI session NI lien : ce ne sont
 *   pas des ressources qu'on occupe, `archiver_un_profil` seul le fait.
 *
 * `circle_id`/`office_id` SONT DES UUID, DÉJÀ EXPOSÉS PAR LE FRAMEWORK
 *
 *   `GET …/framework` (`framework.ts`) rend déjà `identifiant` sur chaque carte
 *   de cercle et de bureau — RIEN à ajouter côté lecture pour obtenir la cible
 *   de ces quatre routes.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/** Les rôles qui archivent et restaurent un cercle ou un bureau — ESM/ADM-E/SUPER. */
export const ROLES_CYCLE_DE_VIE_FRAMEWORK: readonly string[] = CONTRAT_API.rolesCycleDeVieFramework;

export function peutGererLeCycleDeVieDeLaStructure(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_CYCLE_DE_VIE_FRAMEWORK.includes(role));
}

export const GABARIT_CHEMIN_ARCHIVAGE_DU_CERCLE: string = endpoint('archivageDUnCercle').chemin;
export const CODES_ARCHIVAGE_DU_CERCLE: readonly number[] =
  endpoint('archivageDUnCercle').codesExploitables;

export const GABARIT_CHEMIN_RESTAURATION_DU_CERCLE: string =
  endpoint('restaurationDUnCercle').chemin;
export const CODES_RESTAURATION_DU_CERCLE: readonly number[] =
  endpoint('restaurationDUnCercle').codesExploitables;

export const GABARIT_CHEMIN_ARCHIVAGE_DU_BUREAU: string = endpoint('archivageDUnBureau').chemin;
export const CODES_ARCHIVAGE_DU_BUREAU: readonly number[] =
  endpoint('archivageDUnBureau').codesExploitables;

export const GABARIT_CHEMIN_RESTAURATION_DU_BUREAU: string =
  endpoint('restaurationDUnBureau').chemin;
export const CODES_RESTAURATION_DU_BUREAU: readonly number[] =
  endpoint('restaurationDUnBureau').codesExploitables;

function cheminDeTransitionDeStructure(
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

export function cheminArchivageDUnCercle(code: string, circleId: string): string {
  return cheminDeTransitionDeStructure(
    GABARIT_CHEMIN_ARCHIVAGE_DU_CERCLE,
    '{circle_id}',
    code,
    circleId,
  );
}

export function cheminRestaurationDUnCercle(code: string, circleId: string): string {
  return cheminDeTransitionDeStructure(
    GABARIT_CHEMIN_RESTAURATION_DU_CERCLE,
    '{circle_id}',
    code,
    circleId,
  );
}

export function cheminArchivageDUnBureau(code: string, officeId: string): string {
  return cheminDeTransitionDeStructure(
    GABARIT_CHEMIN_ARCHIVAGE_DU_BUREAU,
    '{office_id}',
    code,
    officeId,
  );
}

export function cheminRestaurationDUnBureau(code: string, officeId: string): string {
  return cheminDeTransitionDeStructure(
    GABARIT_CHEMIN_RESTAURATION_DU_BUREAU,
    '{office_id}',
    code,
    officeId,
  );
}

/** Le corps des quatre routes — UN SEUL champ, aucun motif (absent des cinq cas du §18.1). */
export interface DemandeDeTransitionDeStructure {
  readonly version: number;
}

export interface ResultatDArchivageDeStructure {
  readonly version: number;
  readonly archiveLe: string;
}

export interface ResultatDeRestaurationDeStructure {
  readonly version: number;
}

function exigerEntier(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non entier`);
  }
  return brut;
}

export function validerLArchivageDeStructure(valeur: unknown): ResultatDArchivageDeStructure {
  if (!estObjet(valeur)) {
    throw new TypeError('archivage de structure : charge utile non objet');
  }
  return {
    version: exigerEntier(valeur, 'version'),
    archiveLe: exigerChaine(valeur, 'archive_le'),
  };
}

export function validerLaRestaurationDeStructure(
  valeur: unknown,
): ResultatDeRestaurationDeStructure {
  if (!estObjet(valeur)) {
    throw new TypeError('restauration de structure : charge utile non objet');
  }
  return { version: exigerEntier(valeur, 'version') };
}
