/**
 * Le contrat du catalogue des taches de reference, en lecture — LOT 7, `T4`.
 *
 * Matrice §9, modele §13.1, ferme `ECART-013`. « Une sous-etape qui sert une
 * LECTURE pose son module de contrat » — le meme partage que `ficheArrivee.ts`
 * (`T2`) et `liens.ts` (LOT 6, `T8`) : la CREATION, qui ECRIT, n'en ajoute pas
 * un second — voir sa description au manifeste, `creationDUneTacheDeReference`.
 *
 * `entiteId` PEUT VALOIR `null` : une tache GLOBALE (modele §13.1) est
 * reutilisable par TOUTE entite, pas seulement celle du chemin consulte.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin du catalogue, lu du manifeste — `DEC-492`. */
export const GABARIT_CHEMIN_CATALOGUE_DE_TACHES: string = endpoint(
  'catalogueDesTachesOnboarding',
).chemin;

/** Les codes exploitables de la lecture. */
export const CODES_CATALOGUE_DE_TACHES: readonly number[] = endpoint(
  'catalogueDesTachesOnboarding',
).codesExploitables;

/** Le chemin du catalogue d'une entite, son segment encode. */
export function cheminCatalogueDeTaches(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource —
    //  meme raisonnement que `cheminEntite` du LOT 4.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_CATALOGUE_DE_TACHES.replace('{code}', encodeURIComponent(code));
}

export interface TacheDeReference {
  readonly identifiant: string;
  /** `null` : une tache GLOBALE, reutilisable par toute entite — modele §13.1. */
  readonly entiteId: string | null;
  readonly code: string;
  readonly titre: string;
  readonly description: string | null;
  readonly categorie: string | null;
  readonly active: boolean;
}

export interface CatalogueDeTaches {
  readonly taches: readonly TacheDeReference[];
  readonly nombreDeTaches: number;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`catalogue de taches : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string, ou: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`catalogue de taches : ${ou}« ${champ} » n’est pas un entier`);
  }
  return brut;
}

function validerUneTache(brut: unknown, rang: number): TacheDeReference {
  if (!estObjet(brut)) {
    throw new TypeError(`catalogue de taches : taches[${String(rang)}] non objet`);
  }
  const active = brut['active'];
  if (typeof active !== 'boolean') {
    throw new TypeError(
      `catalogue de taches : taches[${String(rang)}].active n’est pas un booleen`,
    );
  }
  return {
    identifiant: exigerChaine(brut, 'id'),
    entiteId: chaineOuNul(brut, 'entity_id'),
    code: exigerChaine(brut, 'code'),
    titre: exigerChaine(brut, 'title'),
    description: chaineOuNul(brut, 'description'),
    categorie: chaineOuNul(brut, 'category'),
    active,
  };
}

/** Valider ce que `GET …/onboarding/task-references` a rendu. */
export function validerLeCatalogueDeTaches(valeur: unknown): CatalogueDeTaches {
  if (!estObjet(valeur)) {
    throw new TypeError('catalogue de taches : charge utile non objet');
  }

  const brutListe = valeur['taches'];
  if (!Array.isArray(brutListe)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucune tache » sur une reponse qui n'en disait rien —
    //  et un catalogue vide est un etat LEGITIME qu'il faut pouvoir distinguer.
    throw new TypeError('catalogue de taches : « taches » n’est pas un tableau');
  }

  const taches = brutListe.map((brut, rang) => validerUneTache(brut, rang));

  const nombre = entier(valeur, 'nombre_de_taches', '');
  if (nombre !== taches.length) {
    //  **DEUX SOURCES POUR UNE MEME GRANDEUR** — §7.0, sixieme proposition.
    throw new TypeError(
      `catalogue de taches : nombre_de_taches vaut ${String(nombre)} pour ` +
        `${String(taches.length)} tache(s) rendue(s)`,
    );
  }

  return { taches, nombreDeTaches: nombre };
}
