/**
 * Le contrat de la page detaillee d'un cercle — LOT 6, `T3`, `MVP-L06-US002`.
 *
 * LA COULEUR N'EST JAMAIS LA SEULE INFORMATION, ET LE MODELE L'EXIGE
 *
 *   Le §8.1 porte, parmi les contraintes de `circle` : « **la couleur ne
 *   constitue jamais la seule information visuelle** ». Ce n'est donc pas qu'un
 *   critere de sortie de la roadmap.
 *
 *   **Ce contrat le tient par la STRUCTURE** : `code` et `nom` sont des `string`
 *   obligatoires, `jetonDeCouleur` est `string | null`. Il n'existe aucune valeur
 *   de ce type ou le jeton serait present et le nom absent — §7.35, la propriete
 *   est portee par le type et non par un controle qu'on pourrait retirer.
 *
 * `jetonDeCouleur` EST NULLABLE, ET IL NE FAUT JAMAIS L'EMPLOYER COMME INDEX
 *
 *   `COULEURS_DE_CERCLE[null]` rend `undefined` exactement comme le chemin
 *   garde : aucun test d'ecran ne voit la difference. Ce qui le refuse est le
 *   TYPE — `TS2538: Type 'null' cannot be used as an index type`. Defaut
 *   `T10-8`, servi sur 100 % des cercles pendant deux lots.
 *
 * LA PAGINATION VIENT DU §18.2, ET ELLE NE SE RESTREINT PAS AU TROMBINOSCOPE
 *
 *   Le §18.2 s'intitule « Pagination », vit dans le chapitre API du cahier et ne
 *   nomme **aucune** ressource. Les trois tailles sont donc celles que
 *   `trombinoscope.ts` declare deja, et ce module les REUTILISE.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';
import { TAILLE_PAR_DEFAUT, TAILLES_DE_PAGE } from './trombinoscope.js';

/** Les deux natures d'appartenance a un cercle — modele §8.2. */
export const TYPES_D_APPARTENANCE_AU_CERCLE = ['principal', 'secondary'] as const;

export type TypeDAppartenanceAuCercle = (typeof TYPES_D_APPARTENANCE_AU_CERCLE)[number];

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_CERCLE: string = endpoint('pageDuCercle').chemin;

/** Les codes exploitables. Le `422` vient de `taille` et de `page`. */
export const CODES_CERCLE: readonly number[] = endpoint('pageDuCercle').codesExploitables;

/** Le chemin d'un cercle, ses DEUX segments encodes. */
export function cheminCercle(code: string, codeCercle: string): string {
  if (code === '' || codeCercle === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource — la
    //  liste des entites, ou la synthese Framework.
    throw new TypeError('code d’entite ou code de cercle vide');
  }
  return GABARIT_CHEMIN_CERCLE.replace('{code}', encodeURIComponent(code)).replace(
    '{code_cercle}',
    encodeURIComponent(codeCercle),
  );
}

export interface MembreDuCercle {
  readonly appartenance: string;
  readonly prenom: string;
  readonly nom: string;
  /** `principal` ou `secondary` — la distinction porte des droits, §8.2 et `ARB-DROIT-004`. */
  readonly typeDAppartenance: string;
}

export interface TitulaireDuCercle {
  readonly identifiant: string;
  readonly prenom: string;
  readonly nom: string;
}

export interface PageDuCercle {
  readonly identifiant: string;
  readonly code: string;
  readonly nom: string;
  readonly description: string | null;
  /** Nullable au catalogue. **Ne jamais l'employer comme index sans garde.** */
  readonly jetonDeCouleur: string | null;
  readonly booster: TitulaireDuCercle | null;
  readonly membres: readonly MembreDuCercle[];
  readonly totalDesMembres: number;
  readonly page: number;
  readonly taille: number;
  /** **Au moins 1, meme sans membre** : `0` ne distinguerait pas « aucun » de « chargement ». */
  readonly pages: number;
  readonly cheminDetaille: string;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, ce qui est legitime.
    throw new TypeError(`cercle : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`cercle : « ${champ} » n’est pas un entier`);
  }
  return brut;
}

function titulaire(valeur: unknown): TitulaireDuCercle | null {
  if (valeur === null) {
    return null;
  }
  if (!estObjet(valeur)) {
    throw new TypeError('cercle : « booster » ni objet ni null');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    prenom: exigerChaine(valeur, 'prenom'),
    nom: exigerChaine(valeur, 'nom'),
  };
}

/**
 * Valider ce que `GET …/circles/{code}` a rendu.
 *
 * **LA PAGINATION EST VERIFIEE CONTRE LE §18.2**, et non acceptee telle quelle :
 * une `taille` hors des trois valeurs est une reponse que l'API ne devrait pas
 * produire, et la laisser passer ferait afficher une page dont la borne n'est
 * plus celle du cahier.
 */
export function validerLaPageDuCercle(valeur: unknown): PageDuCercle {
  if (!estObjet(valeur)) {
    throw new TypeError('cercle : charge utile non objet');
  }

  const brutMembres = valeur['membres'];
  if (!Array.isArray(brutMembres)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun membre » sur une reponse qui n'en disait rien.
    throw new TypeError('cercle : « membres » n’est pas un tableau');
  }
  const membres = brutMembres.map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`cercle : membres[${String(rang)}] non objet`);
    }
    return {
      appartenance: exigerChaine(brut, 'appartenance'),
      prenom: exigerChaine(brut, 'prenom'),
      nom: exigerChaine(brut, 'nom'),
      typeDAppartenance: exigerChaine(brut, 'type_d_appartenance'),
    };
  });

  const taille = entier(valeur, 'taille');
  if (!TAILLES_DE_PAGE.includes(taille)) {
    throw new TypeError(`cercle : taille ${String(taille)} hors du §18.2`);
  }
  const pages = entier(valeur, 'pages');
  if (pages < 1) {
    //  Le service garantit au moins 1 ; l'exiger ici refuse une reponse qui
    //  aurait perdu cette garantie, plutot que de l'afficher.
    throw new TypeError(`cercle : pages vaut ${String(pages)}, au moins 1 attendu`);
  }

  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    code: exigerChaine(valeur, 'code'),
    nom: exigerChaine(valeur, 'nom'),
    description: chaineOuNul(valeur, 'description'),
    jetonDeCouleur: chaineOuNul(valeur, 'jeton_de_couleur'),
    booster: titulaire(valeur['booster']),
    membres,
    totalDesMembres: entier(valeur, 'total_des_membres'),
    page: entier(valeur, 'page'),
    taille,
    pages,
    cheminDetaille: exigerChaine(valeur, 'chemin_detaille'),
  };
}

/** La taille par defaut, reprise du §18.2 — une seule declaration. */
export { TAILLE_PAR_DEFAUT };
