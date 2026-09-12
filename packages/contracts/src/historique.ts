/**
 * Le contrat de l'historique organisationnel — story `MVP-L05-US008`.
 *
 * LOT 5, sous-etape `T11`. L'API le sert depuis `T9` ; aucun ecran ne le lisait.
 *
 * `null` N'EST PAS `[]`, ET C'EST LA SEULE CHOSE QUI COMPTE DANS CE FICHIER
 *
 *   `[]` dit « rien a montrer ». `null` dit « hors de ton perimetre ». Les
 *   confondre ferait croire a un DSM que son consultant n'a **jamais** porte de
 *   responsabilite -- une affirmation FAUSSE, produite par un validateur trop
 *   accommodant.
 *
 *   Un validateur qui traduirait `null` en `[]` « pour simplifier l'ecran »
 *   detruirait donc la distinction que `T9` a construite en base, dans le service
 *   et dans la route. C'est exactement le §7.0 quatrieme proposition : les deux
 *   etats produiraient la meme observation a l'ecran, et l'un des deux serait un
 *   mensonge.
 *
 *   **LA CLE RESTE PRESENTE**, a `null` plutot qu'absente -- meme discipline que
 *   les cinq champs du format d'erreur du §18.3, et que `chaineOuNul` dans le
 *   contrat du trombinoscope : `null` est une valeur, `undefined` une divergence
 *   de contrat.
 *
 * CINQ AXES, ET `statut` PORTE LE CLIENT
 *
 *   Le §6.5 du modele met `status` et `client_id` sur la MEME ligne, liees par
 *   une biconditionnelle. Une mission et son client sont **une** periode ; les
 *   separer en deux axes inventerait deux historiques la ou la base en porte un.
 *
 * LES DATES SONT DES CHAINES, ET ON NE LES CONVERTIT PAS ICI
 *
 *   L'API sert de l'ISO 8601 en UTC. Un `new Date()` dans le validateur
 *   introduirait le fuseau du navigateur **dans le contrat**, si bien qu'une
 *   periode close le 1er janvier a 00:00 UTC deviendrait le 31 decembre a Paris.
 *   La conversion appartient a l'ECRAN, qui sait dans quel fuseau il affiche.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin, lu du manifeste et non recopie. */
export const GABARIT_CHEMIN_HISTORIQUE: string = endpoint('historiqueOrganisationnel').chemin;

/** Les codes exploitables du manifeste — 200, 401, 403, 404, 422. */
export const CODES_HISTORIQUE: readonly number[] = endpoint(
  'historiqueOrganisationnel',
).codesExploitables;

/**
 * Les CINQ axes, dans l'ordre ou la route les declare.
 *
 * **DERIVEE ET NON RECOPIEE COTE ECRAN** : elle pilote la validation, le rendu et
 * les tests. Une seconde liste vieillirait au premier axe ajoute -- §7.27.
 */
export const AXES_DE_L_HISTORIQUE = [
  'metier',
  'statut',
  'cercle',
  'dsm',
  'responsabilites',
] as const;

/** Le nom d'un axe. */
export type AxeDeLHistorique = (typeof AXES_DE_L_HISTORIQUE)[number];

/** Ce que toute periode porte : un debut, et une fin qui peut manquer. */
interface Bornes {
  /** ISO 8601, UTC. Jamais converti ici — voir l'en-tete. */
  readonly debut: string;
  /** `null` = periode COURANTE, pas periode sans fin connue. */
  readonly fin: string | null;
}

/** Une periode de metier. */
export interface PeriodeDeMetier extends Bornes {
  readonly metier: string;
}

/** Une periode de situation professionnelle, AVEC son client. */
export interface PeriodeDeStatut extends Bornes {
  readonly statut: string;
  /** Nul en intercontrat, et c'est la biconditionnelle du §6.5 du modele. */
  readonly client: string | null;
}

/** Une appartenance a un cercle, principale ou secondaire. */
export interface PeriodeDeCercle extends Bornes {
  readonly code: string;
  readonly nom: string;
  readonly type: string;
}

/** Une periode pendant laquelle une personne a ete le DSM de la cible. */
export interface PeriodeDeDsm extends Bornes {
  readonly dsm: string;
}

/** Une responsabilite Framework et sa portee — §8.4, `cercle` et `bureau` s'excluent. */
export interface PeriodeDeResponsabilite extends Bornes {
  readonly type: string;
  readonly cercle: string | null;
  readonly bureau: string | null;
}

/**
 * L'historique complet — chaque axe est une liste, OU `null`.
 *
 * L'axe des responsabilites est le plus souvent celui qui vaut `null` : le §20 de
 * la matrice porte une ligne a part, « Consulter l'historique des roles », qui ne
 * le donne qu'a l'ESM, l'ADM-E et le SUPER. Le §23.2 tranche le conflit avec le
 * §5 -- une interdiction liee a la RESSOURCE prevaut sur le cumul des roles.
 */
export interface HistoriqueOrganisationnel {
  readonly metier: readonly PeriodeDeMetier[] | null;
  readonly statut: readonly PeriodeDeStatut[] | null;
  readonly cercle: readonly PeriodeDeCercle[] | null;
  readonly dsm: readonly PeriodeDeDsm[] | null;
  readonly responsabilites: readonly PeriodeDeResponsabilite[] | null;
}

/** Le chemin d'un historique, ses DEUX segments encodes. */
export function cheminHistorique(code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource.
    throw new TypeError('code d’entite ou identifiant d’appartenance vide');
  }
  return GABARIT_CHEMIN_HISTORIQUE.replace('{code}', encodeURIComponent(code)).replace(
    '{appartenance}',
    encodeURIComponent(appartenance),
  );
}

/** Une date ISO, ou `null`, ou une erreur — jamais `undefined`. */
function dateOuNulle(source: Record<string, unknown>, cle: string, ou: string): string | null {
  const valeur = source[cle];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'string') {
    throw new TypeError(`${ou} : « ${cle} » ni chaine ni null`);
  }
  return valeur;
}

/** Une chaine, ou `null`, ou une erreur — jamais `undefined`. */
function chaineOuNulle(source: Record<string, unknown>, cle: string, ou: string): string | null {
  const valeur = source[cle];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'string') {
    throw new TypeError(`${ou} : « ${cle} » ni chaine ni null`);
  }
  return valeur;
}

/** Les bornes, communes aux cinq axes. `debut` est EXIGE : une periode sans debut n'en est pas une. */
function bornes(source: Record<string, unknown>, ou: string): Bornes {
  return { debut: exigerChaine(source, 'debut'), fin: dateOuNulle(source, 'fin', ou) };
}

/**
 * Un axe : une liste de periodes, ou `null`.
 *
 * **LE `null` TRAVERSE, IL N'EST PAS ABSORBE.** C'est la raison d'etre du
 * fichier, et le test qui l'exige est le plus important de sa suite.
 */
function axeOuNul<T>(
  source: Record<string, unknown>,
  cle: AxeDeLHistorique,
  lire: (periode: Record<string, unknown>, ou: string) => T,
): readonly T[] | null {
  const valeur = source[cle];
  if (valeur === null) {
    return null;
  }
  if (!Array.isArray(valeur)) {
    //  **L'ABSENCE EST REFUSEE AUTANT QU'UN NOMBRE.** Une cle manquante signifie
    //  que l'API ne sert pas cet axe : c'est une reponse d'une AUTRE version, et
    //  la traduire en `null` la ferait passer pour un refus de perimetre.
    throw new TypeError(`historique : l’axe « ${cle} » n’est ni un tableau ni null`);
  }
  return valeur.map((periode, rang) => {
    if (!estObjet(periode)) {
      throw new TypeError(`historique : ${cle}[${String(rang)}] n’est pas un objet`);
    }
    return lire(periode, `${cle}[${String(rang)}]`);
  });
}

/**
 * Valider la charge utile de `GET …/people/{appartenance}/historique`.
 *
 * **LES CINQ CLES SONT EXIGEES**, et le controle ne s'arrete pas au premier axe
 * reconnu : un historique a qui il manquerait `dsm` serait rendu avec un axe de
 * moins **sans que rien ne le dise**, et l'ecran afficherait « aucune periode »
 * la ou la reponse n'en portait aucune trace.
 */
export function validerLHistorique(valeur: unknown): HistoriqueOrganisationnel {
  if (!estObjet(valeur)) {
    throw new TypeError('historique : charge utile non objet');
  }
  const manquants = AXES_DE_L_HISTORIQUE.filter((axe) => !(axe in valeur));
  if (manquants.length > 0) {
    throw new TypeError(`historique : axe(s) absent(s) — ${manquants.join(', ')}`);
  }
  return {
    metier: axeOuNul(valeur, 'metier', (p, ou) => ({
      metier: exigerChaine(p, 'metier'),
      ...bornes(p, ou),
    })),
    statut: axeOuNul(valeur, 'statut', (p, ou) => ({
      statut: exigerChaine(p, 'statut'),
      client: chaineOuNulle(p, 'client', ou),
      ...bornes(p, ou),
    })),
    cercle: axeOuNul(valeur, 'cercle', (p, ou) => ({
      code: exigerChaine(p, 'code'),
      nom: exigerChaine(p, 'nom'),
      type: exigerChaine(p, 'type'),
      ...bornes(p, ou),
    })),
    dsm: axeOuNul(valeur, 'dsm', (p, ou) => ({ dsm: exigerChaine(p, 'dsm'), ...bornes(p, ou) })),
    responsabilites: axeOuNul(valeur, 'responsabilites', (p, ou) => ({
      type: exigerChaine(p, 'type'),
      cercle: chaineOuNulle(p, 'cercle', ou),
      bureau: chaineOuNulle(p, 'bureau', ou),
      ...bornes(p, ou),
    })),
  };
}
