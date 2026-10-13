/**
 * Le catalogue des métiers d'une entité — LOT 9, `T14`.
 *
 * POSÉ EN CONSTRUISANT L'ÉCRAN BACK-OFFICE, PAS PAR UNE SOUS-ÉTAPE ANTÉRIEURE
 *
 *   `job_catalog_id` est un champ obligatoire de la création d'un
 *   collaborateur (`T2`) et du changement d'entité (`T3`) depuis l'ouverture
 *   du lot, et AUCUNE route ne servait sa liste — mesuré sur les 85 chemins
 *   du manifeste avant `T14`. `trombinoscope.ts` le nommait déjà en 2024 :
 *   « les métiers … arriveront avec le back-office du LOT 9 ». Même motif
 *   exact que `GET …/templates`, posée par `T14` du LOT 7 en construisant son
 *   propre écran.
 *
 * SEULS LES MÉTIERS ACTIFS ET NON ARCHIVÉS SONT RENDUS
 *
 *   Un métier retiré du catalogue ne doit pas être PROPOSABLE à une nouvelle
 *   création ou un nouveau changement d'entité — il reste lisible par son
 *   identifiant pour les lignes qui le portent déjà, ce que cette route ne
 *   sert pas.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

export const GABARIT_CHEMIN_CATALOGUE_DES_METIERS: string = endpoint('catalogueDesMetiers').chemin;
export const CODES_CATALOGUE_DES_METIERS: readonly number[] =
  endpoint('catalogueDesMetiers').codesExploitables;

export function cheminCatalogueDesMetiers(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_CATALOGUE_DES_METIERS.replace('{code}', encodeURIComponent(code));
}

export interface MetierDuCatalogue {
  readonly identifiant: string;
  readonly code: string;
  readonly label: string;
}

export interface CatalogueDesMetiers {
  readonly metiers: readonly MetierDuCatalogue[];
}

function validerUnMetier(valeur: unknown, rang: number): MetierDuCatalogue {
  if (!estObjet(valeur)) {
    throw new TypeError(`metiers[${String(rang)}] : charge utile non objet`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    code: exigerChaine(valeur, 'code'),
    label: exigerChaine(valeur, 'label'),
  };
}

export function validerLeCatalogueDesMetiers(valeur: unknown): CatalogueDesMetiers {
  if (!estObjet(valeur)) {
    throw new TypeError('catalogue des metiers : charge utile non objet');
  }
  const metiers = valeur['metiers'];
  if (!Array.isArray(metiers)) {
    throw new TypeError('champ « metiers » absent ou non tableau');
  }
  return { metiers: metiers.map((m, rang) => validerUnMetier(m, rang)) };
}
