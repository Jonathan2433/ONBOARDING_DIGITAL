/**
 * Le contrat de la page detaillee d'un bureau — LOT 6, `T4`, `MVP-L06-US003`.
 *
 * LA BORNE DU §8.4 EST RAPPORTEE, JAMAIS EXIGEE — ET C'EST LE POINT DELICAT
 *
 *   Le §8.4 veut « un bureau possede entre un et trois responsables actifs
 *   **lorsqu'il est publie** ». Aucune contrainte de base ne l'exprime : c'est un
 *   comptage borne, et le declencheur qui le tiendra est pose en `T7`, la ou la
 *   publication a un ecrivain (`DEC-583`).
 *
 *   **Ce validateur ne refuse donc NI zero NI quatre.** Refuser ferait lever une
 *   exception sur une reponse que l'API produit legitimement aujourd'hui, et
 *   l'ecran afficherait une erreur la ou il doit afficher un bureau mal
 *   configure. C'est le parti du §7.20 : *exiger ce qui est exigible, rapporter
 *   visiblement ce qui ne l'est pas*.
 *
 *   Ce qu'il EXIGE, en revanche, c'est que les deux grandeurs s'accordent :
 *   `nombreDeResponsables` doit valoir la longueur du tableau. Deux sources pour
 *   une meme quantite divergent (§7.0, sixieme proposition), et c'est la seule
 *   incoherence qu'un client ne pourrait pas rattraper seul.
 *
 * AUCUNE PAGINATION, ET CE N'EST PAS UN OUBLI
 *
 *   `cercles.ts` pagine parce que le §18.2 — intitule « Pagination », dans le
 *   chapitre API, ne nommant aucune ressource — regit les **populations**. Les
 *   responsables d'un bureau n'en sont pas une : le §8.4 les declare bornes.
 *   Paginer trois elements au plus inventerait un parametre que le cahier ne
 *   demande pas (§6.5).
 *
 * `publie` VIENT DE LA PAGE DE CONTENU, JAMAIS DE LA TABLE `office`
 *
 *   `DEC-576`, apres `ECART-031` : la table `office` ne porte **aucun** etat de
 *   publication. Sans ce booleen, un ecran ne saurait pas distinguer un zero
 *   **legitime** — un bureau en brouillon n'a encore personne — d'un zero qui
 *   **enfreint** le §8.4.
 *
 * `localisation` EST NULLABLE, ET C'EST LE §8.3 QUI LE DIT
 *
 *   « `location_text` | **Facultatif** ». Le type est donc `string | null`, et
 *   jamais `string` : un `String(x)` sur l'absence rendrait « null » ou
 *   « undefined » a l'ecran — la version JavaScript du defaut `T10-8`.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';
import { cheminDePhotoOuNul } from './trombinoscope.js';

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_BUREAU: string = endpoint('pageDuBureau').chemin;

/** Les codes exploitables. Pas de `422` : cette route n'a aucun parametre de requete. */
export const CODES_BUREAU: readonly number[] = endpoint('pageDuBureau').codesExploitables;

/**
 * Les bornes que le §8.4 ecrit, **rapportees et non exigees**.
 *
 * Elles sont exportees pour qu'un ecran puisse signaler l'ecart — c'est
 * exactement l'usage prevu — et **non** pour qu'un validateur les impose.
 */
export const RESPONSABLES_MINIMUM = 1;
export const RESPONSABLES_MAXIMUM = 3;

/** Le chemin d'un bureau, ses DEUX segments encodes. */
export function cheminBureau(code: string, codeBureau: string): string {
  if (code === '' || codeBureau === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource — la
    //  liste des entites, ou la synthese Framework.
    throw new TypeError('code d’entite ou code de bureau vide');
  }
  return GABARIT_CHEMIN_BUREAU.replace('{code}', encodeURIComponent(code)).replace(
    '{code_bureau}',
    encodeURIComponent(codeBureau),
  );
}

export interface ResponsableDuBureau {
  readonly identifiant: string;
  readonly prenom: string;
  readonly nom: string;
  /** Chantier front hors lot, `S12` (`DEC-673`). Voir `cheminDePhotoOuNul`. */
  readonly photo: string | null;
}

export interface PageDuBureau {
  readonly identifiant: string;
  readonly code: string;
  readonly nom: string;
  readonly description: string | null;
  /** §8.3 : « Facultatif ». Jamais `string` seul. */
  readonly localisation: string | null;
  /** **Non borne par ce type** : zero et plus de trois sont des reponses reelles. */
  readonly responsables: readonly ResponsableDuBureau[];
  readonly nombreDeResponsables: number;
  /** `DEC-576` : porte par la page de contenu de type `OFFICE`. */
  readonly publie: boolean;
  readonly cheminDetaille: string;
}

/**
 * Le bureau respecte-t-il la borne du §8.4 ?
 *
 * **Une QUESTION, et non une exigence.** Elle ne vaut que pour un bureau
 * **publie** — « lorsqu'il est publie » — si bien qu'un bureau en brouillon a
 * zero responsable rend `true` : il n'enfreint rien.
 *
 * C'est la forme que le §7.20 recommande pour un residuel : *rapporter
 * visiblement ce qui n'est pas exigible*, plutot que de le taire ou de le
 * refuser.
 */
export function respecteLaBorneDuHuitQuatre(bureau: PageDuBureau): boolean {
  if (!bureau.publie) {
    return true;
  }
  return (
    bureau.nombreDeResponsables >= RESPONSABLES_MINIMUM &&
    bureau.nombreDeResponsables <= RESPONSABLES_MAXIMUM
  );
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, ce qui est legitime.
    throw new TypeError(`bureau : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

/**
 * Valider ce que `GET …/offices/{code}` a rendu.
 *
 * **CE VALIDATEUR NE REFUSE NI ZERO NI QUATRE RESPONSABLES.** Voir l'en-tete du
 * module : la borne du §8.4 n'est pas tenue en base, et refuser ferait echouer
 * l'ecran sur une reponse que l'API produit legitimement.
 */
export function validerLaPageDuBureau(valeur: unknown): PageDuBureau {
  if (!estObjet(valeur)) {
    throw new TypeError('bureau : charge utile non objet');
  }

  const brutResponsables = valeur['responsables'];
  if (!Array.isArray(brutResponsables)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun responsable » sur une reponse qui n'en disait
    //  rien — et ici la difference compte doublement, puisque zero responsable
    //  est justement l'anomalie que le §8.4 vise.
    throw new TypeError('bureau : « responsables » n’est pas un tableau');
  }
  const responsables = brutResponsables.map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`bureau : responsables[${String(rang)}] non objet`);
    }
    return {
      identifiant: exigerChaine(brut, 'identifiant'),
      prenom: exigerChaine(brut, 'prenom'),
      nom: exigerChaine(brut, 'nom'),
      photo: cheminDePhotoOuNul(brut),
    };
  });

  const nombre = valeur['nombre_de_responsables'];
  if (typeof nombre !== 'number' || !Number.isInteger(nombre)) {
    throw new TypeError('bureau : « nombre_de_responsables » n’est pas un entier');
  }
  if (nombre !== responsables.length) {
    //  **DEUX SOURCES POUR UNE MEME GRANDEUR** — §7.0, sixieme proposition.
    //  C'est la seule incoherence qu'un client ne pourrait pas rattraper seul :
    //  il afficherait « 3 responsables » au-dessus d'une liste de deux.
    throw new TypeError(
      `bureau : nombre_de_responsables vaut ${String(nombre)} pour ` +
        `${String(responsables.length)} responsable(s) rendus`,
    );
  }

  const publie = valeur['publie'];
  if (typeof publie !== 'boolean') {
    //  Pas de coercition : `undefined` serait tombe sur `false`, et un bureau
    //  publie aurait paru brouillon — donc conforme au §8.4 quoi qu'il arrive.
    throw new TypeError('bureau : « publie » n’est pas un booleen');
  }

  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    code: exigerChaine(valeur, 'code'),
    nom: exigerChaine(valeur, 'nom'),
    description: chaineOuNul(valeur, 'description'),
    localisation: chaineOuNul(valeur, 'localisation'),
    responsables,
    nombreDeResponsables: nombre,
    publie,
    cheminDetaille: exigerChaine(valeur, 'chemin_detaille'),
  };
}
