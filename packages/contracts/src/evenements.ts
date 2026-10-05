/**
 * Le contrat de la lecture des evenements — LOT 8, `T2` (API) puis `T9` (ecran),
 * story `MVP-L08-US003`.
 *
 * LA LECTURE SEULE, COMME `liens.ts` AVANT SON `T10`
 *
 *   `T2` a `T8` ont servi cette route et six verbes d'ecriture sans poser de
 *   module de contrat : aucun ecran ne la consommait encore. `T9`, premier
 *   ecran consommateur, pose donc la LECTURE — meme partage que le catalogue
 *   des taches (LOT 7, `T4`/`T14`) et les liens internes (LOT 6, `T8`/`T10`) :
 *   une sous-etape qui sert une lecture pose son module quand un ecran en a
 *   besoin, celles qui servent une ecriture seule ne le font pas.
 *
 * LA FRONTIERE EST UNIQUE, ET CE MODULE NE LA RECALCULE PAS
 *
 *   `a_venir` et `passes` sont les DEUX classements du cahier §10.6 : la
 *   frontiere — `ends_at` compare a un instant unique — est tranchee par
 *   `lister_les_evenements` (`apps/api/app/events/lecture.py`), jamais ici. Le
 *   client envoie le classement voulu, l'API y repond ; rien ne reclasse un
 *   evenement cote navigateur.
 *
 * UN EVENEMENT ANNULE RESTE SERVI, ET C'EST STRUCTUREL
 *
 *   `etat` reste une CHAINE, jamais un type ferme : seuls `published` et
 *   `cancelled` sont servis par cette route (un brouillon ou une archive sont
 *   absents, filtres par l'API), mais fermer le type ici figerait un futur
 *   troisieme etat public que l'API pourrait un jour exposer — meme motif que
 *   `TYPES_DE_LIEN_NOMMES` dans `liens.ts`.
 *
 * LES DATES RESTENT DES CHAINES ISO, JAMAIS DES `Date`
 *
 *   Meme parti que `ficheArrivee.ts` : l'API sert de l'ISO 8601, et `new Date()`
 *   suivi d'un accesseur LOCAL (`getHours()`, `getMonth()`...) reinterprete la
 *   valeur dans le fuseau de la machine qui l'affiche. Le validateur rend donc
 *   des `string`, et l'ecran lit les segments qu'il lui faut directement dans
 *   la chaine (meme methode que `dateComplete` dans `PageProfil.tsx`).
 *
 * `pages` PEUT VALOIR ZERO, ET C'EST DIFFERENT DU CERCLE
 *
 *   `PageDuCercle.pages` vaut toujours au moins 1 : un cercle existe meme sans
 *   membre. Une entite SANS AUCUN evenement d'un classement donne a un total
 *   de zero, et `-(-0 // taille)` rend zero cote API — l'exiger a 1 ici
 *   refuserait une reponse parfaitement legitime. Le validateur confronte donc
 *   `pages` a `total` et `taille` par le calcul, jamais a une borne fixe.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';
import { TAILLES_DE_PAGE } from './trombinoscope.js';

/** Les deux onglets du cahier §10.6 — jamais des etats stockes, voir `lecture.py`. */
export const CLASSEMENTS_D_EVENEMENTS = ['a_venir', 'passes'] as const;

export type ClassementEvenement = (typeof CLASSEMENTS_D_EVENEMENTS)[number];

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_EVENEMENTS: string = endpoint('lectureDesEvenements').chemin;

/** Les codes exploitables. Le `422` vient de `classement`, `taille` et `page`. */
export const CODES_EVENEMENTS: readonly number[] =
  endpoint('lectureDesEvenements').codesExploitables;

/** Le chemin des evenements d'une entite, son segment encode. */
export function cheminEvenements(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_EVENEMENTS.replace('{code}', encodeURIComponent(code));
}

export interface EvenementDuClassement {
  readonly identifiant: string;
  readonly titre: string;
  readonly description: string | null;
  /** ISO 8601 — ne JAMAIS passer par `Date`, voir l'en-tete. */
  readonly commenceLe: string;
  /** ISO 8601 — idem. */
  readonly finitLe: string;
  readonly lieu: string | null;
  /** `published` ou `cancelled` — chaine volontairement ouverte, voir l'en-tete. */
  readonly etat: string;
  readonly annuleLe: string | null;
  readonly motifDAnnulation: string | null;
}

export interface PageDesEvenements {
  readonly classement: ClassementEvenement;
  readonly evenements: readonly EvenementDuClassement[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`evenements : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string, ou: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`evenements : ${ou}« ${champ} » n’est pas un entier`);
  }
  return brut;
}

function classementValide(valeur: unknown): ClassementEvenement {
  if (valeur !== 'a_venir' && valeur !== 'passes') {
    throw new TypeError(`evenements : classement « ${String(valeur)} » inconnu`);
  }
  return valeur;
}

function evenementDuClassement(brut: unknown, rang: number): EvenementDuClassement {
  if (!estObjet(brut)) {
    throw new TypeError(`evenements : evenements[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(brut, 'identifiant'),
    titre: exigerChaine(brut, 'titre'),
    description: chaineOuNul(brut, 'description'),
    commenceLe: exigerChaine(brut, 'commence_le'),
    finitLe: exigerChaine(brut, 'finit_le'),
    lieu: chaineOuNul(brut, 'lieu'),
    etat: exigerChaine(brut, 'etat'),
    annuleLe: chaineOuNul(brut, 'annule_le'),
    motifDAnnulation: chaineOuNul(brut, 'motif_d_annulation'),
  };
}

/**
 * Valider ce que `GET …/events` a rendu.
 *
 * **`pages` EST CONFRONTE A `total` ET `taille` PAR LE CALCUL**, jamais a une
 * borne fixe — voir l'en-tete, c'est different du cercle. Deux sources pour
 * une meme grandeur doivent coincider, §7.0 sixieme proposition.
 */
export function validerLaPageDesEvenements(valeur: unknown): PageDesEvenements {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }

  const brutEvenements = valeur['evenements'];
  if (!Array.isArray(brutEvenements)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun evenement » sur une reponse qui n'en disait rien.
    throw new TypeError('evenements : « evenements » n’est pas un tableau');
  }
  const evenements = brutEvenements.map((brut, rang) => evenementDuClassement(brut, rang));

  const taille = entier(valeur, 'taille', '');
  if (!TAILLES_DE_PAGE.includes(taille)) {
    throw new TypeError(`evenements : taille ${String(taille)} hors du §18.2`);
  }
  const total = entier(valeur, 'total', '');
  const pages = entier(valeur, 'pages', '');
  const attendu = total === 0 ? 0 : Math.ceil(total / taille);
  if (pages !== attendu) {
    throw new TypeError(
      `evenements : pages vaut ${String(pages)} pour un total de ${String(total)} ` +
        `a ${String(taille)} par page (${String(attendu)} attendu)`,
    );
  }

  return {
    classement: classementValide(valeur['classement']),
    evenements,
    page: entier(valeur, 'page', ''),
    taille,
    total,
    pages,
  };
}
