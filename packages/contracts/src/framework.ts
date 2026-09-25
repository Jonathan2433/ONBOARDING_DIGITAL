/**
 * Le contrat de la page Framework — LOT 6, `T2`, story `MVP-L06-US001`.
 *
 * TROIS FAMILLES, ET LE CAHIER §10.3 LES NOMME
 *
 *   « La page Framework fournit une vue synthetique sous forme de cartes et des
 *   pages detaillees pour : les **responsabilites** ; les **cercles** ; les
 *   **bureaux**. » Pas quatre.
 *
 *   **LE BACKLOG ET LA ROADMAP ECRIVENT « categories et responsabilites », ET LE
 *   MOT « categories » N'EST NULLE PART AILLEURS** -- mesure du 13/09/2026 : il
 *   ne vit que dans ces deux documents DERIVES. Le cahier PREVAUT, et le §6.2
 *   reconcilie : les responsabilites Framework SONT les categories.
 *
 * `null` N'EST PAS UNE CHAINE VIDE, ET CE CONTRAT LE TIENT DEUX FOIS
 *
 *   `chemin_detaille` vaut `null` pour `BOOSTER` et `OFFICE_MANAGER`, qui n'ont
 *   pas de page propre -- l'annexe A §10.1 n'en donne qu'a `DSM` et `ESM`. Vide
 *   dirait « la page existe, son adresse est inconnue ».
 *
 *   `jeton_de_couleur` vaut `null` sur un cercle qui n'en porte pas. Le rendre
 *   en chaine donnerait « None » : defaut `T10-8`, servi sur 100 % des cercles
 *   pendant deux lots.
 *
 * LA COULEUR N'EST JAMAIS LA SEULE INFORMATION, ET C'EST STRUCTUREL
 *
 *   `code` et `nom` sont des `string` obligatoires, `jetonDeCouleur` est
 *   `string | null`. **Il n'existe aucune valeur de ce type ou le jeton serait
 *   present et le nom absent** : le critere de sortie n°4 du lot est tenu par la
 *   STRUCTURE et non par un controle qu'on pourrait retirer (§7.35).
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Les QUATRE responsabilites Framework du cahier §6.2, dans l'ordre du document. */
export const RESPONSABILITES_FRAMEWORK = ['DSM', 'ESM', 'BOOSTER', 'OFFICE_MANAGER'] as const;

export type ResponsabiliteFramework = (typeof RESPONSABILITES_FRAMEWORK)[number];

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_FRAMEWORK: string = endpoint('pageFramework').chemin;

/** Les codes exploitables. Pas de `403` : la matrice §5 n'examine aucun role. */
export const CODES_FRAMEWORK: readonly number[] = endpoint('pageFramework').codesExploitables;

/** Le chemin de la synthese d'une entite, son segment encode. */
export function cheminFramework(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu designerait la LISTE des entites.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_FRAMEWORK.replace('{code}', encodeURIComponent(code));
}

export interface TitulaireFramework {
  readonly identifiant: string;
  readonly prenom: string;
  readonly nom: string;
}

export interface CarteDeResponsabilite {
  readonly typeDeResponsabilite: string;
  readonly titulaires: readonly TitulaireFramework[];
  /** `null` pour `BOOSTER` et `OFFICE_MANAGER` : ils n'ont pas de page propre. */
  readonly cheminDetaille: string | null;
}

export interface CarteDeCercle {
  readonly identifiant: string;
  readonly code: string;
  readonly nom: string;
  readonly description: string | null;
  /** Nullable au catalogue. **Ne jamais l'employer comme index sans garde.** */
  readonly jetonDeCouleur: string | null;
  readonly booster: TitulaireFramework | null;
  readonly membresActifs: number;
  readonly cheminDetaille: string;
}

export interface CarteDeBureau {
  readonly identifiant: string;
  readonly code: string;
  readonly nom: string;
  readonly description: string | null;
  readonly localisation: string | null;
  readonly responsables: readonly TitulaireFramework[];
  readonly cheminDetaille: string;
}

export interface PageFramework {
  readonly responsabilites: readonly CarteDeResponsabilite[];
  readonly cercles: readonly CarteDeCercle[];
  readonly bureaux: readonly CarteDeBureau[];
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, ce qui est legitime.
    throw new TypeError(`framework : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`framework : « ${champ} » n’est pas un entier`);
  }
  return brut;
}

function titulaire(valeur: unknown, ou: string): TitulaireFramework {
  if (!estObjet(valeur)) {
    throw new TypeError(`framework : titulaire non objet dans ${ou}`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    prenom: exigerChaine(valeur, 'prenom'),
    nom: exigerChaine(valeur, 'nom'),
  };
}

function titulaireOuNul(valeur: unknown, ou: string): TitulaireFramework | null {
  return valeur === null ? null : titulaire(valeur, ou);
}

function tableau(source: Record<string, unknown>, champ: string): readonly unknown[] {
  const brut = source[champ];
  if (!Array.isArray(brut)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun titulaire » sur une reponse qui n'en disait rien.
    throw new TypeError(`framework : « ${champ} » n’est pas un tableau`);
  }
  return brut;
}

/**
 * Valider ce que `GET …/framework` a rendu.
 *
 * **LES TROIS FAMILLES SONT EXIGEES, MEME VIDES.** Une famille absente et une
 * famille vide donneraient la meme observation cote client alors qu'elles ne
 * disent pas la meme chose — §7.0, quatrieme proposition.
 */
export function validerLaPageFramework(valeur: unknown): PageFramework {
  if (!estObjet(valeur)) {
    throw new TypeError('framework : charge utile non objet');
  }

  const responsabilites = tableau(valeur, 'responsabilites').map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`framework : responsabilites[${String(rang)}] non objet`);
    }
    return {
      typeDeResponsabilite: exigerChaine(brut, 'type_de_responsabilite'),
      titulaires: tableau(brut, 'titulaires').map((t) => titulaire(t, 'responsabilites')),
      cheminDetaille: chaineOuNul(brut, 'chemin_detaille'),
    };
  });

  const cercles = tableau(valeur, 'cercles').map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`framework : cercles[${String(rang)}] non objet`);
    }
    return {
      identifiant: exigerChaine(brut, 'identifiant'),
      code: exigerChaine(brut, 'code'),
      nom: exigerChaine(brut, 'nom'),
      description: chaineOuNul(brut, 'description'),
      jetonDeCouleur: chaineOuNul(brut, 'jeton_de_couleur'),
      booster: titulaireOuNul(brut['booster'], 'cercles'),
      membresActifs: entier(brut, 'membres_actifs'),
      cheminDetaille: exigerChaine(brut, 'chemin_detaille'),
    };
  });

  const bureaux = tableau(valeur, 'bureaux').map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`framework : bureaux[${String(rang)}] non objet`);
    }
    return {
      identifiant: exigerChaine(brut, 'identifiant'),
      code: exigerChaine(brut, 'code'),
      nom: exigerChaine(brut, 'nom'),
      description: chaineOuNul(brut, 'description'),
      localisation: chaineOuNul(brut, 'localisation'),
      responsables: tableau(brut, 'responsables').map((r) => titulaire(r, 'bureaux')),
      cheminDetaille: exigerChaine(brut, 'chemin_detaille'),
    };
  });

  return { responsabilites, cercles, bureaux };
}
