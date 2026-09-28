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
import { CONTRAT_API, endpoint } from './sante.js';

/** Le chemin de la liste des entites, lu du manifeste et non recopie. */
export const CHEMIN_ENTITES: string = endpoint('entitesDuPortail').chemin;

/** Les codes exploitables : 200 et 401. Aucun 403 — la matrice ne distingue aucun role. */
export const CODES_ENTITES: readonly number[] = endpoint('entitesDuPortail').codesExploitables;

/** Le gabarit du chemin de resolution, tel que le manifeste le declare. */
export const GABARIT_CHEMIN_ENTITE: string = endpoint('entiteConsultee').chemin;

/** Les codes exploitables de la resolution : 200, 401 et 404. */
export const CODES_ENTITE: readonly number[] = endpoint('entiteConsultee').codesExploitables;

/**
 * Le chemin de l'entite consultee, pour un code donne.
 *
 * **LE CODE EST ENCODE, ET CE N'EST PAS UNE PRECAUTION DE STYLE.** `entity.code`
 * est une chaine libre de 64 caracteres -- le modele ne lui impose AUCUN motif,
 * mesure sur le schema. Un code contenant `/`, `?` ou `#` changerait le chemin
 * appele, et un code contenant `..` pourrait viser une autre route. Une
 * concatenation naive donnerait donc une requete differente de celle qu'on croit
 * emettre, ce qui est la classe de defaut du §7.0 quatrieme proposition.
 *
 * **ELLE LEVE SUR UN CODE VIDE** plutot que de rendre `/api/v1/entities/`, qui est
 * le chemin de la LISTE : un code vide rendrait 200 avec toutes les entites au
 * lieu d'un 404, donc un echec indistinguable d'un succes.
 */
export function cheminEntite(code: string): string {
  return gabaritPourCode(GABARIT_CHEMIN_ENTITE, code);
}

/** La garde et l'encodage, en UN SEUL exemplaire — deux copies divergeraient. */
function gabaritPourCode(gabarit: string, code: string): string {
  if (code === '') {
    throw new Error('code d entite vide : le chemin obtenu serait celui de la liste');
  }
  return gabarit.replace('{code}', encodeURIComponent(code));
}

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

/** Valider la charge utile de `GET /api/v1/entities/{code}`. Leve si la forme diverge. */
export function validerUneEntite(valeur: unknown): EntiteDuPortail {
  return validerEntite(valeur);
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

/** Le gabarit du chemin des permissions, lu du manifeste. */
export const GABARIT_CHEMIN_PERMISSIONS: string = endpoint('permissionsDeLEntite').chemin;

/** Les codes exploitables des permissions : 200, 401 et 404 — les memes que la resolution. */
export const CODES_PERMISSIONS: readonly number[] =
  endpoint('permissionsDeLEntite').codesExploitables;

/**
 * Le chemin des permissions de l'entite consultee.
 *
 * **MEME ENCODAGE, MEME LEVEE QUE `cheminEntite`, ET POUR UNE RAISON DE PLUS.**
 * Un code vide donnerait ici `/api/v1/entities//permissions`, que le routeur
 * n'apparie a rien : un 404 indistinguable de « cette entite n'existe pas ».
 *
 * Les deux fonctions partagent donc leur garde, et elle est ecrite une seule
 * fois : deux copies d'une meme regle divergent, c'est `DEC-466` et `ECART-022`.
 */
export function cheminPermissions(code: string): string {
  return gabaritPourCode(GABARIT_CHEMIN_PERMISSIONS, code);
}

/** Les codes de role du §3 de la matrice, tels que l'API les rend. */
export interface PermissionsDeLEntite {
  readonly entite: string;
  readonly code: string;
  readonly estEntitePrincipale: boolean;
  readonly roles: readonly string[];
  /**
   * L'appartenance OCCUPANTE de l'appelant DANS cette entite — LOT 7, `T13`.
   * `null` hors de l'entite principale, ou sans appartenance occupante.
   *
   * **C'EST LE SEUL MOYEN DONT DISPOSE L'ECRAN DU NOUVEL ARRIVANT** de savoir
   * quelle URL appeler pour SA propre fiche d'arrivee et SON propre parcours :
   * aucune route de l'onboarding n'accepte de cible implicite (matrice §7,
   * §8.1). Reutiliser cette reponse, deja appelee une fois par page par le
   * cadre applicatif, evite un aller-retour reseau de plus.
   */
  readonly appartenance: string | null;
}

/**
 * Valider la charge utile de `GET /api/v1/entities/{code}/permissions`.
 *
 * **`estEntitePrincipale` EST EXIGE, ET SON ABSENCE NE DOIT PAS VALOIR `false`.**
 * Un `valeur['est_entite_principale'] === true` rendrait `false` sur un champ
 * ABSENT, donc sur une reponse malformee -- et `false` est precisement la valeur
 * la plus restrictive, celle qui masque le plus d'actions. L'echec produirait
 * alors la meme observation qu'un succes legitime hors entite principale, ce que
 * le §7.0 quatrieme proposition interdit. Le type est donc verifie.
 *
 * **ET `roles` EXIGE LE TABLEAU.** Meme motif que `validerLesEntites` : une
 * reponse `{}` rendrait une liste vide, indistinguable d'un « aucun droit »
 * legitime.
 */
function appartenanceOuNulle(valeur: Record<string, unknown>): string | null {
  const brut = valeur['appartenance'];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Meme discipline que `ficheArrivee.ts` et
    //  `parcoursOnboarding.ts` : un champ manquant est une reponse malformee.
    throw new TypeError('champ « appartenance » ni chaine ni null');
  }
  return brut;
}

export function validerLesPermissions(valeur: unknown): PermissionsDeLEntite {
  if (!estObjet(valeur)) {
    throw new TypeError('permissions non objet');
  }
  const principale = valeur['est_entite_principale'];
  if (typeof principale !== 'boolean') {
    throw new TypeError('champ « est_entite_principale » absent ou non booleen');
  }
  const roles = valeur['roles'];
  if (!Array.isArray(roles)) {
    throw new TypeError('champ « roles » absent ou non tableau');
  }
  return {
    entite: exigerChaine(valeur, 'entite'),
    code: exigerChaine(valeur, 'code'),
    estEntitePrincipale: principale,
    roles: roles.map((role, rang) => {
      if (typeof role !== 'string') {
        throw new TypeError(`role ${String(rang)} non chaine`);
      }
      return role;
    }),
    appartenance: appartenanceOuNulle(valeur),
  };
}

/**
 * Les rôles qui ouvrent la rubrique « Administration » — LOT 4, `T9`.
 *
 * **LUS DU MANIFESTE, JAMAIS RECOPIÉS.** Le frontend masque, l'API refuse, et les
 * deux doivent parler de la **même** liste : deux copies divergeraient au premier
 * rôle ajouté (§7.27), et le manifeste est précisément la source unique que
 * TypeScript **et** Python lisent (`DEC-492`).
 *
 * Sa dérivation — le §20 de la matrice, trois colonnes et non deux — est écrite
 * dans le manifeste lui-même, à côté de la valeur.
 */
export const ROLES_ADMINISTRATION: readonly string[] = CONTRAT_API.rolesAdministration;
