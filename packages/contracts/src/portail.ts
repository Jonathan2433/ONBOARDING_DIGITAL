/**
 * Le contrat du portail national — story `MVP-L04-US001`.
 *
 * LOT 4, sous-etape T1.
 *
 * LA PREMIERE FORME METIER DU CONTRAT. `sante.ts` disait « AUCUN TYPE METIER
 * ICI. Ni `Collaborateur`, ni `Cercle`, ni `Parcours`. Le modele de donnees
 * appartient au LOT 2, qui n'est pas ouvert. » Le LOT 4 est ouvert, et la page
 * nationale est son premier ecran : cette forme arrive ici, dans son propre
 * module, et non dans un fichier nomme « sante ».
 *
 * QUATRE CHAMPS, ET LES ABSENCES SONT MOTIVEES
 *
 *   `status` est absent parce que toute entite rendue est `active` : le champ
 *   serait constant, et un champ constant apprend a ne pas le lire. `timezone` et
 *   `country_code` sont absents faute de consommateur au LOT 4. Le detail est
 *   dans `apps/api/app/entities/services.py`.
 *
 * LE VALIDATEUR N'EST PAS UN ORNEMENT
 *
 *   Les types TypeScript disparaissent a la compilation : un `fetch` qui recoit
 *   autre chose que la forme attendue produirait un `undefined` quelque part dans
 *   le rendu, loin de la cause. C'est le motif de `validerEtatServices` en `T5`
 *   du LOT 1, et il vaut a plus forte raison pour une liste.
 *
 *   **IL EXIGE LE TABLEAU, ET REFUSE UN OBJET SANS `entites`.** Une reponse
 *   `{}` rendrait autrement une liste vide, indistinguable d'un « aucune entite
 *   active » legitime -- exactement la classe de defaut ou l'echec produit la
 *   meme observation que le succes (§7.0, quatrieme proposition).
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le chemin de la liste des entites, lu du manifeste et non recopie. */
export const CHEMIN_ENTITES: string = endpoint('entitesDuPortail').chemin;

/** Les codes exploitables : 200 et 401. Aucun 403 — la matrice ne distingue aucun role. */
export const CODES_ENTITES: readonly number[] = endpoint('entitesDuPortail').codesExploitables;

/** Une entite du portail national. */
export interface EntiteDuPortail {
  readonly id: string;
  readonly code: string;
  readonly nom: string;
  readonly ville: string;
}

/** La reponse de `GET /api/v1/entities`. */
export interface ReponseDesEntites {
  readonly entites: readonly EntiteDuPortail[];
}

function validerEntite(valeur: unknown): EntiteDuPortail {
  if (!estObjet(valeur)) {
    throw new TypeError('entite non objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    code: exigerChaine(valeur, 'code'),
    nom: exigerChaine(valeur, 'nom'),
    ville: exigerChaine(valeur, 'ville'),
  };
}

/** Valider la charge utile de `GET /api/v1/entities`. Leve si la forme diverge. */
export function validerLesEntites(valeur: unknown): ReponseDesEntites {
  if (!estObjet(valeur)) {
    throw new TypeError('reponse non objet');
  }
  const entites = valeur['entites'];
  if (!Array.isArray(entites)) {
    throw new TypeError('champ « entites » absent ou non tableau');
  }
  return { entites: entites.map(validerEntite) };
}
