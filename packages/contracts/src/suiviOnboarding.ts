/**
 * Le contrat du suivi des taches en retard par perimetre — LOT 7, `T12`/`T14`.
 *
 * Matrice §8.1 « Consulter les taches en retard », US008. `T12` avait posee la
 * FORME au manifeste (`PageDeSuiviOnboarding`) sans module de contrat propre —
 * aucun ecran ne la consommait encore, meme parti que `CatalogueDeTaches` a
 * `T4`. `T14`, en construisant l'ecran d'administration, en devient le premier
 * consommateur.
 *
 * **AUCUN ROLE N'EST REFUSE SUR CETTE ROUTE** : la portee se degrade jusqu'a
 * `Soi`, disponible a n'importe qui sur SES PROPRES taches — y compris `OFFICE`
 * et un employe nu. C'est pourquoi cette route n'entre PAS dans le calcul de
 * visibilite de la rubrique « Administration » (voir `rolesAdministrationOnboarding`
 * au manifeste) : l'inclure rendrait le menu visible a tout le monde.
 *
 * Pagination du cahier §18.2, memes trois tailles que le trombinoscope — voir
 * `cercles.ts` pour le meme raisonnement, non restreint a une ressource.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin, lu du manifeste — `DEC-492`. */
export const GABARIT_CHEMIN_SUIVI_ONBOARDING: string = endpoint('suiviDesTachesEnRetard').chemin;

/** Les codes exploitables. Le `422` vient de `taille` et de `page`. */
export const CODES_SUIVI_ONBOARDING: readonly number[] =
  endpoint('suiviDesTachesEnRetard').codesExploitables;

/** Le chemin du suivi d'une entite, son segment encode. */
export function cheminSuiviOnboarding(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_SUIVI_ONBOARDING.replace('{code}', encodeURIComponent(code));
}

export interface TacheEnRetardDuSuivi {
  readonly id: string;
  readonly titre: string;
  readonly echeance: string;
  readonly etat: string;
  readonly instanceId: string;
  readonly appartenanceId: string;
  readonly personneId: string;
  readonly prenom: string;
  readonly nom: string;
}

export interface PageDeSuiviOnboarding {
  readonly taches: readonly TacheEnRetardDuSuivi[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  /** **Au moins 1, meme sans tache** : `0` ne distinguerait pas « aucune » de « chargement ». */
  readonly pages: number;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`suivi de l’onboarding : « ${champ} » n’est pas un entier`);
  }
  return brut;
}

function validerUneTacheEnRetard(valeur: unknown, rang: number): TacheEnRetardDuSuivi {
  if (!estObjet(valeur)) {
    throw new TypeError(`suivi de l’onboarding : taches[${String(rang)}] non objet`);
  }
  return {
    id: exigerChaine(valeur, 'id'),
    titre: exigerChaine(valeur, 'title_snapshot'),
    echeance: exigerChaine(valeur, 'due_at'),
    etat: exigerChaine(valeur, 'state'),
    instanceId: exigerChaine(valeur, 'instance_id'),
    appartenanceId: exigerChaine(valeur, 'appartenance_id'),
    personneId: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'first_name'),
    nom: exigerChaine(valeur, 'last_name'),
  };
}

/** Valider ce que `GET …/onboarding-suivi/taches-en-retard` a rendu. */
export function validerLeSuiviOnboarding(valeur: unknown): PageDeSuiviOnboarding {
  if (!estObjet(valeur)) {
    throw new TypeError('suivi de l’onboarding : charge utile non objet');
  }
  const brutListe = valeur['taches'];
  if (!Array.isArray(brutListe)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Meme discipline que
    //  le catalogue de `T4` et le parcours de `T7`.
    throw new TypeError('suivi de l’onboarding : « taches » n’est pas un tableau');
  }
  return {
    taches: brutListe.map((brut, rang) => validerUneTacheEnRetard(brut, rang)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}
