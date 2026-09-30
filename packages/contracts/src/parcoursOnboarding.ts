/**
 * Le contrat du parcours d'onboarding — LOT 7, `T7`.
 *
 * Matrice §8.1, modele §13.5/§13.6. « Une sous-etape qui sert une LECTURE
 * pose son module de contrat » — meme partage que `ficheArrivee.ts` (`T2`) et
 * `liens.ts` (LOT 6, `T8`). **UN SEUL MODULE SERT LES DEUX VERBES** : affecter
 * (`POST`) renvoie EXACTEMENT la meme forme que consulter (`GET`), donc un
 * seul validateur les sert toutes les deux — deux cles de manifeste,
 * `affectationDUnParcours` et `lectureDuParcours`, un seul module de contrat.
 *
 * `instance`/`progression` PEUVENT VALOIR `null` ENSEMBLE : tant qu'aucun
 * parcours n'a ete affecte, GET rend les deux a `null`, `prochaineTache` a
 * `null` et `taches` a un tableau VIDE — jamais une erreur. Meme convention
 * que `id`/`version` de la fiche d'arrivee.
 *
 * **`prochaineTache` PEUT VALOIR `null` MEME AVEC UN `instance` NON NUL**, et
 * ce n'est PAS le meme cas que ci-dessus — voir l'en-tete de
 * `validerLeParcours` pour le defaut que cette distinction corrige (`T13`).
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin du parcours, lu du manifeste — `DEC-492`. */
export const GABARIT_CHEMIN_PARCOURS: string = endpoint('lectureDuParcours').chemin;

/** Les codes exploitables de la lecture. */
export const CODES_LECTURE_DU_PARCOURS: readonly number[] =
  endpoint('lectureDuParcours').codesExploitables;

/** Les codes exploitables de l'affectation. */
export const CODES_AFFECTATION_DU_PARCOURS: readonly number[] =
  endpoint('affectationDUnParcours').codesExploitables;

/**
 * Les gabarits et codes des DEUX actions de `T13` — matrice §8.1, `Soi` seul.
 *
 * **UN SEUL VALIDATEUR SERT LES DEUX**, `validerUneTacheDuParcours` : les deux
 * routes rendent EXACTEMENT la forme `ReponseDeTacheDuParcours`, deja validee
 * par `validerUneTache` (privee) pour chaque ligne du tableau `taches`. Une
 * seconde fonction publique qui recopierait ses champs divergerait au premier
 * ajout (§7.27) — elle est donc exportee sous ce nom, pas dupliquee.
 */
export const GABARIT_CHEMIN_COMPLETION_DE_TACHE: string = endpoint(
  'completionDUneTacheDOnboarding',
).chemin;
export const GABARIT_CHEMIN_ANNULATION_DE_TACHE: string = endpoint(
  'annulationDeLaCompletionDUneTache',
).chemin;
export const CODES_COMPLETION_DE_TACHE: readonly number[] = endpoint(
  'completionDUneTacheDOnboarding',
).codesExploitables;
export const CODES_ANNULATION_DE_TACHE: readonly number[] = endpoint(
  'annulationDeLaCompletionDUneTache',
).codesExploitables;

/** Le chemin d'une action sur une tache, ses TROIS segments encodes. */
function cheminDeLActionSurUneTache(
  gabarit: string,
  code: string,
  appartenance: string,
  tache: string,
): string {
  if (code === '' || appartenance === '' || tache === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource —
    //  meme raisonnement que `cheminDuParcours`.
    throw new TypeError('code d’entite, appartenance ou identifiant de tache vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{appartenance}', encodeURIComponent(appartenance))
    .replace('{tache}', encodeURIComponent(tache));
}

export function cheminCompletionDeTache(code: string, appartenance: string, tache: string): string {
  return cheminDeLActionSurUneTache(GABARIT_CHEMIN_COMPLETION_DE_TACHE, code, appartenance, tache);
}

export function cheminAnnulationDeTache(code: string, appartenance: string, tache: string): string {
  return cheminDeLActionSurUneTache(GABARIT_CHEMIN_ANNULATION_DE_TACHE, code, appartenance, tache);
}

/** Le chemin du parcours d'une appartenance, ses deux segments encodes. */
export function cheminDuParcours(code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource
    //  — meme raisonnement que `cheminFicheArrivee` (`T2`).
    throw new TypeError('code d’entite ou appartenance vide');
  }
  return GABARIT_CHEMIN_PARCOURS.replace('{code}', encodeURIComponent(code)).replace(
    '{appartenance}',
    encodeURIComponent(appartenance),
  );
}

export interface TacheDuParcours {
  readonly id: string;
  readonly referenceDeLaTache: string;
  readonly titre: string;
  readonly description: string | null;
  readonly obligatoire: boolean;
  readonly echeance: string;
  readonly etat: string;
  readonly termineeLe: string | null;
  readonly reouverteLe: string | null;
}

export interface InstanceDeParcours {
  readonly id: string;
  readonly versionDeModele: string;
  readonly dateDeReference: string;
  readonly etat: string;
  readonly demarreeLe: string;
  readonly termineeLe: string | null;
}

export interface ProgressionDuParcours {
  readonly tachesObligatoiresTotales: number;
  readonly tachesObligatoiresTerminees: number;
}

export interface Parcours {
  /** `null` tant qu'aucune instance n'a ete affectee. */
  readonly instance: InstanceDeParcours | null;
  readonly progression: ProgressionDuParcours | null;
  readonly prochaineTache: TacheDuParcours | null;
  readonly taches: readonly TacheDuParcours[];
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Meme discipline que `ficheArrivee.ts`.
    throw new TypeError(`parcours : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function exigerBooleen(source: Record<string, unknown>, champ: string): boolean {
  const valeur = source[champ];
  if (typeof valeur !== 'boolean') {
    throw new TypeError(`parcours : « ${champ} » absent ou non booleen`);
  }
  return valeur;
}

function exigerEntier(source: Record<string, unknown>, champ: string): number {
  const valeur = source[champ];
  if (typeof valeur !== 'number' || !Number.isInteger(valeur)) {
    throw new TypeError(`parcours : « ${champ} » absent ou non entier`);
  }
  return valeur;
}

function validerUneTache(valeur: unknown): TacheDuParcours {
  if (!estObjet(valeur)) {
    throw new TypeError('parcours : une tache n’est pas un objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    referenceDeLaTache: exigerChaine(valeur, 'task_reference_id'),
    titre: exigerChaine(valeur, 'title_snapshot'),
    description: chaineOuNul(valeur, 'description_snapshot'),
    obligatoire: exigerBooleen(valeur, 'required'),
    echeance: exigerChaine(valeur, 'due_at'),
    etat: exigerChaine(valeur, 'state'),
    termineeLe: chaineOuNul(valeur, 'completed_at'),
    reouverteLe: chaineOuNul(valeur, 'reopened_at'),
  };
}

/**
 * Valider ce que `POST …/completion` et `POST …/annulation` rendent — `T13`.
 *
 * **MEME FORME QU'UNE LIGNE DE `taches`**, exportee sous son propre nom plutot
 * que de laisser un consommateur importer une fonction privee. Voir l'en-tete
 * de `GABARIT_CHEMIN_COMPLETION_DE_TACHE`.
 */
export function validerUneTacheDuParcours(valeur: unknown): TacheDuParcours {
  return validerUneTache(valeur);
}

function validerLInstance(valeur: unknown): InstanceDeParcours {
  if (!estObjet(valeur)) {
    throw new TypeError('parcours : « instance » n’est pas un objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    versionDeModele: exigerChaine(valeur, 'template_version_id'),
    dateDeReference: exigerChaine(valeur, 'reference_date'),
    etat: exigerChaine(valeur, 'state'),
    demarreeLe: exigerChaine(valeur, 'started_at'),
    termineeLe: chaineOuNul(valeur, 'completed_at'),
  };
}

function validerLaProgression(valeur: unknown): ProgressionDuParcours {
  if (!estObjet(valeur)) {
    throw new TypeError('parcours : « progression » n’est pas un objet');
  }
  return {
    tachesObligatoiresTotales: exigerEntier(valeur, 'taches_obligatoires_totales'),
    tachesObligatoiresTerminees: exigerEntier(valeur, 'taches_obligatoires_terminees'),
  };
}

/**
 * Valider ce que `GET`/`POST …/onboarding-parcours` ont rendu.
 *
 * **DEFAUT TROUVE ET CORRIGE A `T13`, DANS UN CODE ECRIT A `T7`.** Cette
 * fonction exigeait que `instance`, `progression` ET `prochaine_tache` soient
 * NULS ENSEMBLE, ou AUCUN DES TROIS. C'est FAUX pour `prochaine_tache` :
 * `_prochaine_tache` (`app/onboarding/instances.py`) rend `None` des que
 * PLUS AUCUNE tache n'est `todo`/`reopened` — completees ou annulees, y
 * compris quand l'instance reste `active` (une version sans AUCUNE tache
 * obligatoire, dont toutes les taches facultatives sont terminees, n'est
 * jamais archivee automatiquement : `T11` n'archive que sur la DERNIERE
 * tache OBLIGATOIRE). Un parcours reel dans cet etat faisait LEVER ce
 * validateur, et l'ecran du nouvel arrivant (`T13`) aurait recu `corps: null`
 * sur un `200` parfaitement legitime — silencieusement, comme `T11-7` du LOT
 * 5. `instance` et `progression` restent nuls ENSEMBLE (`lire_le_parcours` ne
 * calcule jamais l'un sans l'autre) ; `prochaine_tache` est verifie a part.
 */
export function validerLeParcours(valeur: unknown): Parcours {
  if (!estObjet(valeur)) {
    throw new TypeError('parcours : charge utile non objet');
  }
  const instanceBrute = valeur['instance'];
  const progressionBrute = valeur['progression'];
  const prochaineTacheBrute = valeur['prochaine_tache'];
  if ((instanceBrute === null) !== (progressionBrute === null)) {
    throw new TypeError('parcours : « instance » et « progression » doivent etre nuls ENSEMBLE');
  }
  //  **AUCUN parcours affecte -> AUCUNE prochaine tache.** `_AUCUN_PARCOURS`
  //  (backend) force les trois a `null` dans ce cas precis ; c'est le SEUL
  //  sens dans lequel `prochaine_tache` est contraint par les deux autres.
  if (instanceBrute === null && prochaineTacheBrute !== null) {
    throw new TypeError('parcours : « prochaine_tache » doit etre nul si aucun parcours affecte');
  }
  const taches = valeur['taches'];
  if (!Array.isArray(taches)) {
    throw new TypeError('parcours : « taches » n’est pas un tableau');
  }
  return {
    instance: instanceBrute === null ? null : validerLInstance(instanceBrute),
    progression: progressionBrute === null ? null : validerLaProgression(progressionBrute),
    prochaineTache: prochaineTacheBrute === null ? null : validerUneTache(prochaineTacheBrute),
    taches: taches.map(validerUneTache),
  };
}
