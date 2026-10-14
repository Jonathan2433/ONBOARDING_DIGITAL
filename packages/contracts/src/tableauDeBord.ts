/**
 * Le tableau de bord administratif — LOT 9, `T5` (API) puis `T14` (écran),
 * `MVP-L09-US001`.
 *
 * SIX GRANDEURS, PAS CINQ — LE CAHIER §10.8 LE DIT, PAS L'ABRÉGÉ DE LA FICHE
 *
 *   Profils actifs, arrivées futures, onboardings actifs, tâches en retard,
 *   profils incomplets, derniers imports en échec — deux comptes distincts là
 *   où un résumé en fusionnait deux (« onboardings actifs » et « tâches en
 *   retard »).
 *
 * « PROFIL INCOMPLET » EST ARBITRÉ, PAS DÉFINI PAR LE CAHIER
 *
 *   Un profil actif à qui il manque métier, cercle principal, DSM ou statut —
 *   la même notion que `relations_a_redonner` après une restauration (LOT 5,
 *   `T8`), jamais une invention nouvelle (arbitrage de Jonathan).
 *
 * « DERNIERS IMPORTS EN ÉCHEC » EST TOUJOURS UN TABLEAU, JAMAIS `null`
 *
 *   L'API filtre elle-même PAR RÔLE : un DSM ou un Booster reçoivent une liste
 *   VIDE, jamais un 403 partiel sur un agrégat qui rend 200 — ce module ne
 *   recalcule donc AUCUN second rôle pour cette seule section, l'affichage
 *   suit ce qu'il reçoit (règle 5, l'API est l'autorité finale).
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/** Les rôles qui ouvrent le tableau de bord — §15.1 « Reporting et exports ». OFFICE à tiret. */
export const ROLES_TABLEAU_DE_BORD: readonly string[] = CONTRAT_API.rolesTableauDeBord;

export function peutConsulterLeTableauDeBord(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_TABLEAU_DE_BORD.includes(role));
}

export const GABARIT_CHEMIN_TABLEAU_DE_BORD: string = endpoint('tableauDeBordAdministratif').chemin;
export const CODES_TABLEAU_DE_BORD: readonly number[] = endpoint(
  'tableauDeBordAdministratif',
).codesExploitables;

export function cheminTableauDeBord(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_TABLEAU_DE_BORD.replace('{code}', encodeURIComponent(code));
}

/** Un lot d'import récent EN ÉCHEC — `failed`, ou des lignes rejetées. */
export interface ImportEnEchec {
  readonly identifiant: string;
  readonly nomDuFichier: string;
  readonly etat: string;
  readonly totalDesLignes: number;
  readonly lignesRejetees: number;
  readonly creeLe: string;
}

export interface TableauDeBord {
  readonly profilsActifs: number;
  readonly arriveesFutures: number;
  readonly onboardingsActifs: number;
  readonly tachesEnRetard: number;
  readonly profilsIncomplets: number;
  /** TOUJOURS un tableau — vide pour DSM/BOOST, jamais `null`. */
  readonly derniersImportsEnEchec: readonly ImportEnEchec[];
}

function exigerEntier(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non entier`);
  }
  return brut;
}

function validerUnImportEnEchec(valeur: unknown, rang: number): ImportEnEchec {
  if (!estObjet(valeur)) {
    throw new TypeError(`derniers_imports_en_echec[${String(rang)}] : charge utile non objet`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    nomDuFichier: exigerChaine(valeur, 'nom_du_fichier'),
    etat: exigerChaine(valeur, 'etat'),
    totalDesLignes: exigerEntier(valeur, 'total_des_lignes'),
    lignesRejetees: exigerEntier(valeur, 'lignes_rejetees'),
    creeLe: exigerChaine(valeur, 'cree_le'),
  };
}

/**
 * Valider la charge utile de `GET …/administration/tableau-de-bord`.
 *
 * **`derniers_imports_en_echec` EXIGE LE TABLEAU, JAMAIS UN DÉFAUT `[]`.** Une
 * reponse malformee rendrait sinon silencieusement « aucun import en echec »,
 * indistinguable d'un etat legitime — §7.0 quatrieme proposition.
 */
export function validerLeTableauDeBord(valeur: unknown): TableauDeBord {
  if (!estObjet(valeur)) {
    throw new TypeError('tableau de bord : charge utile non objet');
  }
  const imports = valeur['derniers_imports_en_echec'];
  if (!Array.isArray(imports)) {
    throw new TypeError('champ « derniers_imports_en_echec » absent ou non tableau');
  }
  return {
    profilsActifs: exigerEntier(valeur, 'profils_actifs'),
    arriveesFutures: exigerEntier(valeur, 'arrivees_futures'),
    onboardingsActifs: exigerEntier(valeur, 'onboardings_actifs'),
    tachesEnRetard: exigerEntier(valeur, 'taches_en_retard'),
    profilsIncomplets: exigerEntier(valeur, 'profils_incomplets'),
    derniersImportsEnEchec: imports.map((i, rang) => validerUnImportEnEchec(i, rang)),
  };
}
