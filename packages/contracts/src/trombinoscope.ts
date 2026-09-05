/**
 * Le contrat du trombinoscope — story `MVP-L05-US001`.
 *
 * LOT 5, sous-etape T2.
 *
 * LE JSON EST EN `snake_case`, LA FORME TS EN `camelCase`, ET C'EST DELIBERE
 *
 *   L'API sert les noms de colonnes tels que le modele les porte -- `first_name`,
 *   `arrival_date` -- et ce module les traduit. C'est le montage pose par `T8` du
 *   LOT 4 pour `est_entite_principale` : la frontiere est ici, en un seul
 *   endroit, plutot que dans chaque composant qui lit la reponse.
 *
 * LE VALIDATEUR N'EST PAS UN ORNEMENT
 *
 *   Les types TypeScript disparaissent a la compilation. Un `fetch` qui recoit
 *   autre chose produirait un `undefined` loin de la cause.
 *
 *   **ET IL EXIGE LES QUATRE NOMBRES DE L'ENVELOPPE, SANS DEFAUT.** Un
 *   `Number(valeur['total']) || 0` rendrait **0** sur un champ absent, donc sur
 *   une reponse malformee -- et 0 est exactement ce que rend un trombinoscope
 *   legitimement vide. L'echec produirait la meme observation que le succes, ce
 *   que le §7.0 quatrieme proposition interdit. Chaque nombre est donc verifie.
 *
 * `preferredName` EST LA SEULE VALEUR FACULTATIVE, ET C'EST MESURE
 *
 *   Sur le schema reel, `first_name`, `last_name`, `arrival_date` et
 *   `professional_category` sont tous `NOT NULL` ; `preferred_name` est la seule
 *   colonne nullable des sept. La forme le dit, plutot que de tout rendre
 *   facultatif « au cas ou » -- ce qui obligerait chaque appelant a se defendre
 *   contre des absences impossibles (§7.32).
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin, lu du manifeste et non recopie. */
export const GABARIT_CHEMIN_TROMBINOSCOPE: string = endpoint('trombinoscopeDeLEntite').chemin;

/** Les codes exploitables : 200, 401, 404 et 422. Aucun 403 — la matrice §5 ne distingue aucun role. */
export const CODES_TROMBINOSCOPE: readonly number[] =
  endpoint('trombinoscopeDeLEntite').codesExploitables;

/**
 * Les trois tailles de page du cahier §18.2, et elles seules.
 *
 * **ECRITES ICI PARCE QUE LE MANIFESTE NE PORTE PAS DE PARAMETRES DE REQUETE**,
 * et le dire vaut mieux que de laisser croire qu'elles sont derivees. L'API les
 * refuse toutes les autres : c'est elle l'autorite, et cette liste ne sert qu'a
 * ce que l'ecran ne PROPOSE que des valeurs valides.
 */
export const TAILLES_DE_PAGE: readonly number[] = [25, 50, 100];

/** La taille servie lorsque l'appelant n'en demande aucune — cahier §18.2. */
export const TAILLE_PAR_DEFAUT = 25;

/** Une ligne du trombinoscope. */
export interface CollaborateurDuTrombinoscope {
  readonly id: string;
  readonly personneId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nomPrefere: string | null;
  readonly categorieProfessionnelle: string;
  readonly dateArrivee: string;
}

/** Une page du trombinoscope, et de quoi savoir ou l'on est. */
export interface ReponseDuTrombinoscope {
  readonly collaborateurs: readonly CollaborateurDuTrombinoscope[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

/** Le chemin d'une entite, son code ENCODE — meme motif que `cheminEntite`. */
export function cheminTrombinoscope(code: string, page?: number, taille?: number): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource.
    throw new TypeError('code d’entite vide');
  }
  const base = GABARIT_CHEMIN_TROMBINOSCOPE.replace('{code}', encodeURIComponent(code));
  //  **PAS DE `URLSearchParams` ICI, ET CE N'EST PAS UN GOUT.** Ce paquet est lu
  //  par le navigateur, par Vitest et par un controle Python ; il ne doit
  //  dependre d'aucun global d'environnement. `tsc` l'a dit avant moi :
  //  « Cannot find name 'URLSearchParams' », la bibliotheque DOM n'etant pas
  //  dans son `lib`. `encodeURIComponent` est du langage.
  const parametres: string[] = [];
  if (page !== undefined) {
    parametres.push(`page=${encodeURIComponent(String(page))}`);
  }
  if (taille !== undefined) {
    parametres.push(`taille=${encodeURIComponent(String(taille))}`);
  }
  return parametres.length === 0 ? base : `${base}?${parametres.join('&')}`;
}

function exigerNombre(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isFinite(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non nombre`);
  }
  return brut;
}

function validerUnCollaborateur(valeur: unknown, rang: number): CollaborateurDuTrombinoscope {
  if (!estObjet(valeur)) {
    throw new TypeError(`collaborateur ${String(rang)} non objet`);
  }
  const prefere = valeur['preferred_name'];
  if (prefere !== null && typeof prefere !== 'string') {
    throw new TypeError(`collaborateur ${String(rang)} : « preferred_name » ni chaine ni null`);
  }
  return {
    id: exigerChaine(valeur, 'id'),
    personneId: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'first_name'),
    nom: exigerChaine(valeur, 'last_name'),
    nomPrefere: prefere,
    categorieProfessionnelle: exigerChaine(valeur, 'professional_category'),
    dateArrivee: exigerChaine(valeur, 'arrival_date'),
  };
}

/**
 * Valider la charge utile de `GET /api/v1/entities/{code}/people`.
 *
 * **LE TABLEAU EST EXIGE.** Une reponse `{}` rendrait autrement une liste vide,
 * indistinguable d'une entite legitimement sans collaborateur publie.
 */
export function validerLeTrombinoscope(valeur: unknown): ReponseDuTrombinoscope {
  if (!estObjet(valeur)) {
    throw new TypeError('trombinoscope non objet');
  }
  const lignes = valeur['collaborateurs'];
  if (!Array.isArray(lignes)) {
    throw new TypeError('champ « collaborateurs » absent ou non tableau');
  }
  return {
    collaborateurs: lignes.map(validerUnCollaborateur),
    page: exigerNombre(valeur, 'page'),
    taille: exigerNombre(valeur, 'taille'),
    total: exigerNombre(valeur, 'total'),
    pages: exigerNombre(valeur, 'pages'),
  };
}
