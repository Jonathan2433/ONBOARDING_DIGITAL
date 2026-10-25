/**
 * Le reporting étendu — LOT 10, `T10` (API), `T15` (premier écran),
 * `MVP-L10-US003`.
 *
 * AUCUNE GRILLE DE RÔLES PROPRE : CELLE DU TABLEAU DE BORD EST RÉUTILISÉE
 *
 *   `app/reporting/lecture.py` importe littéralement `ROLES_DU_TABLEAU_DE_
 *   BORD`/`resoudre_le_perimetre_du_tableau_de_bord` (LOT 9, `T5`) — les
 *   quatre premières lignes du §15.1 portent la MÊME grille, pas une
 *   coïncidence. Ce module réutilise donc `ROLES_TABLEAU_DE_BORD`/
 *   `peutConsulterLeTableauDeBord` de `tableauDeBord.ts`, jamais une seconde
 *   déclaration qui pourrait diverger (§7.27).
 *
 * TROIS ROUTES, UNE SEULE SANS PAGINATION
 *
 *   Les indicateurs (compteurs/répartitions) ne paginent pas — ce sont des
 *   agrégats. Le détail onboarding et les profils incomplets paginent,
 *   cahier §18.2.
 */
import { endpoint } from './sante.js';
import { estObjet, exigerChaine } from './formes.js';

/** Les cinq filtres du cahier §15.1 — période, DSM, cercle, client. */
export interface FiltresDeReporting {
  readonly depuis?: string;
  readonly jusqua?: string;
  readonly dsm?: string;
  readonly cercle?: string;
  readonly client?: string;
}

//  **PAS DE `URLSearchParams` ICI** — voir `trombinoscope.ts` : ce paquet n'a
//  pas la bibliotheque DOM dans son `lib`.
function parametresDeFiltre(filtres: FiltresDeReporting): string[] {
  const parametres: string[] = [];
  if (filtres.depuis !== undefined) {
    parametres.push(`depuis=${encodeURIComponent(filtres.depuis)}`);
  }
  if (filtres.jusqua !== undefined) {
    parametres.push(`jusqua=${encodeURIComponent(filtres.jusqua)}`);
  }
  if (filtres.dsm !== undefined) {
    parametres.push(`dsm=${encodeURIComponent(filtres.dsm)}`);
  }
  if (filtres.cercle !== undefined) {
    parametres.push(`cercle=${encodeURIComponent(filtres.cercle)}`);
  }
  if (filtres.client !== undefined) {
    parametres.push(`client=${encodeURIComponent(filtres.client)}`);
  }
  return parametres;
}

export const GABARIT_CHEMIN_INDICATEURS: string = endpoint('indicateursDeReporting').chemin;
export const CODES_INDICATEURS: readonly number[] =
  endpoint('indicateursDeReporting').codesExploitables;
export const GABARIT_CHEMIN_DETAIL_ONBOARDING: string = endpoint(
  'detailOnboardingDuReporting',
).chemin;
export const CODES_DETAIL_ONBOARDING: readonly number[] = endpoint(
  'detailOnboardingDuReporting',
).codesExploitables;
export const GABARIT_CHEMIN_PROFILS_INCOMPLETS: string = endpoint(
  'profilsIncompletsEnDetail',
).chemin;
export const CODES_PROFILS_INCOMPLETS: readonly number[] = endpoint(
  'profilsIncompletsEnDetail',
).codesExploitables;

function cheminFiltre(gabarit: string, code: string, filtres: FiltresDeReporting): string {
  if (code === '') {
    throw new TypeError('code d’entité vide');
  }
  const parametres = parametresDeFiltre(filtres);
  const base = gabarit.replace('{code}', encodeURIComponent(code));
  return parametres.length === 0 ? base : `${base}?${parametres.join('&')}`;
}

export function cheminIndicateurs(code: string, filtres: FiltresDeReporting = {}): string {
  return cheminFiltre(GABARIT_CHEMIN_INDICATEURS, code, filtres);
}

function cheminFiltrePagine(
  gabarit: string,
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDeReporting,
): string {
  if (code === '') {
    throw new TypeError('code d’entité vide');
  }
  const parametres = [
    `page=${encodeURIComponent(String(page))}`,
    `taille=${encodeURIComponent(String(taille))}`,
    ...parametresDeFiltre(filtres),
  ];
  return `${gabarit.replace('{code}', encodeURIComponent(code))}?${parametres.join('&')}`;
}

export function cheminDetailOnboarding(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDeReporting = {},
): string {
  return cheminFiltrePagine(GABARIT_CHEMIN_DETAIL_ONBOARDING, code, page, taille, filtres);
}

export function cheminProfilsIncomplets(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDeReporting = {},
): string {
  return cheminFiltrePagine(GABARIT_CHEMIN_PROFILS_INCOMPLETS, code, page, taille, filtres);
}

export interface RepartitionParGroupe {
  readonly identifiant: string;
  readonly libelle: string;
  readonly profilsActifs: number;
}

export interface ProgressionAgregee {
  readonly tachesObligatoiresTotales: number;
  readonly tachesObligatoiresTerminees: number;
}

export interface Indicateurs {
  readonly onboardingsTermines: number;
  readonly progressionMoyenne: ProgressionAgregee;
  /** `null` si la population est vide — jamais `0` (§7.0 sixième proposition). */
  readonly dureeMoyenneJours: number | null;
  readonly arrivees30Jours: number;
  readonly repartitionParCercle: readonly RepartitionParGroupe[];
  readonly repartitionParClient: readonly RepartitionParGroupe[];
  readonly repartitionParDsm: readonly RepartitionParGroupe[];
}

export interface OnboardingDuDetail {
  readonly appartenanceId: string;
  readonly personId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly dateDeReference: string;
  readonly debuteLe: string;
  readonly tachesObligatoiresTotales: number;
  readonly tachesObligatoiresTerminees: number;
}

export interface ReponseDuDetailOnboarding {
  readonly elements: readonly OnboardingDuDetail[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

export interface ProfilIncomplet {
  readonly appartenanceId: string;
  readonly personId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly metierManquant: boolean;
  readonly cerclePrincipalManquant: boolean;
  readonly dsmManquant: boolean;
  readonly statutManquant: boolean;
}

export interface ReponseDesProfilsIncomplets {
  readonly elements: readonly ProfilIncomplet[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const valeur = source[champ];
  if (typeof valeur !== 'number' || !Number.isInteger(valeur)) {
    throw new TypeError(`« ${champ} » absent ou non entier`);
  }
  return valeur;
}

function nombreOuNul(source: Record<string, unknown>, champ: string): number | null {
  const valeur = source[champ];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'number') {
    throw new TypeError(`« ${champ} » ni nombre ni null`);
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

function validerUneRepartition(valeur: unknown, champ: string, rang: number): RepartitionParGroupe {
  if (!estObjet(valeur)) {
    throw new TypeError(`indicateurs : ${champ}[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    libelle: exigerChaine(valeur, 'libelle'),
    profilsActifs: entier(valeur, 'profils_actifs'),
  };
}

function tableauDeRepartitions(
  valeur: Record<string, unknown>,
  champ: string,
): readonly RepartitionParGroupe[] {
  const brut = valeur[champ];
  if (!Array.isArray(brut)) {
    throw new TypeError(`indicateurs : « ${champ} » n’est pas un tableau`);
  }
  return brut.map((v, rang) => validerUneRepartition(v, champ, rang));
}

export function validerLesIndicateurs(valeur: unknown): Indicateurs {
  if (!estObjet(valeur)) {
    throw new TypeError('indicateurs : charge utile non objet');
  }
  const progression = valeur['progression_moyenne'];
  if (!estObjet(progression)) {
    throw new TypeError('indicateurs : « progression_moyenne » non objet');
  }
  return {
    onboardingsTermines: entier(valeur, 'onboardings_termines'),
    progressionMoyenne: {
      tachesObligatoiresTotales: entier(progression, 'taches_obligatoires_totales'),
      tachesObligatoiresTerminees: entier(progression, 'taches_obligatoires_terminees'),
    },
    dureeMoyenneJours: nombreOuNul(valeur, 'duree_moyenne_jours'),
    arrivees30Jours: entier(valeur, 'arrivees_30_jours'),
    repartitionParCercle: tableauDeRepartitions(valeur, 'repartition_par_cercle'),
    repartitionParClient: tableauDeRepartitions(valeur, 'repartition_par_client'),
    repartitionParDsm: tableauDeRepartitions(valeur, 'repartition_par_dsm'),
  };
}

function validerUnOnboardingDuDetail(valeur: unknown, rang: number): OnboardingDuDetail {
  if (!estObjet(valeur)) {
    throw new TypeError(`détail onboarding : elements[${String(rang)}] non objet`);
  }
  return {
    appartenanceId: exigerChaine(valeur, 'appartenance_id'),
    personId: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'prenom'),
    nom: exigerChaine(valeur, 'nom'),
    dateDeReference: exigerChaine(valeur, 'date_de_reference'),
    debuteLe: exigerChaine(valeur, 'debute_le'),
    tachesObligatoiresTotales: entier(valeur, 'taches_obligatoires_totales'),
    tachesObligatoiresTerminees: entier(valeur, 'taches_obligatoires_terminees'),
  };
}

export function validerLeDetailOnboarding(valeur: unknown): ReponseDuDetailOnboarding {
  if (!estObjet(valeur)) {
    throw new TypeError('détail onboarding : charge utile non objet');
  }
  const brut = valeur['elements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('détail onboarding : « elements » n’est pas un tableau');
  }
  return {
    elements: brut.map((e, rang) => validerUnOnboardingDuDetail(e, rang)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}

function validerUnProfilIncomplet(valeur: unknown, rang: number): ProfilIncomplet {
  if (!estObjet(valeur)) {
    throw new TypeError(`profils incomplets : elements[${String(rang)}] non objet`);
  }
  return {
    appartenanceId: exigerChaine(valeur, 'appartenance_id'),
    personId: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'prenom'),
    nom: exigerChaine(valeur, 'nom'),
    metierManquant: booleen(valeur, 'metier_manquant'),
    cerclePrincipalManquant: booleen(valeur, 'cercle_principal_manquant'),
    dsmManquant: booleen(valeur, 'dsm_manquant'),
    statutManquant: booleen(valeur, 'statut_manquant'),
  };
}

export function validerLesProfilsIncomplets(valeur: unknown): ReponseDesProfilsIncomplets {
  if (!estObjet(valeur)) {
    throw new TypeError('profils incomplets : charge utile non objet');
  }
  const brut = valeur['elements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('profils incomplets : « elements » n’est pas un tableau');
  }
  return {
    elements: brut.map((e, rang) => validerUnProfilIncomplet(e, rang)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}
