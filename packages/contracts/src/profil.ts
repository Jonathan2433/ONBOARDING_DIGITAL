/**
 * Le contrat de la fiche profil — story `MVP-L05-US004`.
 *
 * LOT 5, sous-etape T4.
 *
 * AUCUN CHAMP N'EST MASQUE, ET LE VALIDATEUR NE DOIT PAS LAISSER CROIRE LE
 * CONTRAIRE
 *
 *   La matrice ne definit aucune visibilite par champ -- « regles de visibilite »
 *   ne parait que dans les deux copies du critere de `US004` lui-meme, et le seul
 *   « masquer » de la matrice porte sur les ACTIONS. Le §5 donne « Fiches
 *   collaborateur », « Statut mission/intercontrat » et « Client actif » en
 *   Lecture aux HUIT roles authentifies. `ECART-051`.
 *
 *   **Les champs facultatifs le sont donc parce que la DONNEE peut manquer, pas
 *   parce qu'un role ne la verrait pas.** Un consultant sans mission n'a pas de
 *   client ; un nouvel arrivant n'a pas encore de fun fact. Confondre les deux
 *   ferait ecrire un jour « ce champ est nul, donc l'appelant n'y a pas droit ».
 *
 * LA PHOTO EST ARRIVEE EN `T5`, ET C'EST UN CHEMIN
 *
 *   Le §10.2 la nomme en premier. `T4` n'en portait AUCUNE trace, volontairement :
 *   un champ qui aurait toujours valu `null` aurait laisse croire que le §12.2
 *   etait applique. `T5` et `T6` ont ete fusionnees (`DEC-564`), et le champ
 *   existe desormais.
 *
 *   **C'est un CHEMIN, jamais des octets** -- le §16.1 interdit Base64 -- et il
 *   est valide par `cheminDePhotoOuNul`, la MEME fonction que le trombinoscope.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';
import { cheminDePhotoOuNul } from './trombinoscope.js';

/** Le gabarit du chemin, lu du manifeste et non recopie. */
export const GABARIT_CHEMIN_PROFIL: string = endpoint('ficheDuProfil').chemin;

/** Les codes exploitables : 200, 401 et 404. Aucun 403 — la matrice §5 ne distingue aucun role. */
export const CODES_PROFIL: readonly number[] = endpoint('ficheDuProfil').codesExploitables;

/** Un cercle, principal ou secondaire — §10.2. */
export interface CercleDuProfil {
  readonly code: string;
  readonly nom: string;
  readonly jetonDeCouleur: string;
}

/**
 * Une responsabilite Framework et sa portee — §8.4.
 *
 * `cercle` et `bureau` s'excluent : un `BOOSTER` porte sur un cercle, un
 * `OFFICE_MANAGER` sur un bureau, un `DSM` ou un `ESM` sur ni l'un ni l'autre.
 * La base l'impose par contrainte de verification.
 */
export interface ResponsabiliteDuProfil {
  readonly type: string;
  readonly cercle: string | null;
  readonly bureau: string | null;
}

/** La fiche profil complete — les champs du §10.2, moins la photo. */
export interface FicheDuProfil {
  readonly id: string;
  readonly personneId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nomPrefere: string | null;
  readonly categorieProfessionnelle: string;
  readonly dateArrivee: string;
  readonly presentation: string | null;
  readonly funFact: string | null;
  readonly metier: string | null;
  readonly statut: string | null;
  readonly client: string | null;
  readonly dsm: string | null;
  readonly cerclePrincipal: CercleDuProfil | null;
  readonly cerclesSecondaires: readonly CercleDuProfil[];
  readonly responsabilites: readonly ResponsabiliteDuProfil[];
  /**
   * Le chemin de la miniature, ou `null` — LOT 5, `T5`.
   *
   * **LA MEME FONCTION QUE LE TROMBINOSCOPE**, et non une seconde copie : la
   * liste et la fiche annoncent le meme chemin, produit par le meme service
   * cote API. Deux validateurs divergeraient au premier changement, et l'un des
   * deux accepterait alors ce que l'autre refuse.
   */
  readonly photo: string | null;
}

/** Le chemin d'une fiche, ses DEUX segments encodes. */
export function cheminProfil(code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu serait celui de la LISTE.
    throw new TypeError('code d’entite ou identifiant d’appartenance vide');
  }
  return GABARIT_CHEMIN_PROFIL.replace('{code}', encodeURIComponent(code)).replace(
    '{appartenance}',
    encodeURIComponent(appartenance),
  );
}

function chaineOuNul(valeur: Record<string, unknown>, champ: string): string | null {
  const brut = valeur[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, ce qui est legitime.
    //  Les confondre ferait passer une reponse tronquee pour un profil incomplet.
    throw new TypeError(`champ « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function validerUnCercle(valeur: unknown, ou: string): CercleDuProfil {
  if (!estObjet(valeur)) {
    throw new TypeError(`cercle ${ou} non objet`);
  }
  return {
    code: exigerChaine(valeur, 'code'),
    nom: exigerChaine(valeur, 'nom'),
    jetonDeCouleur: exigerChaine(valeur, 'jeton_de_couleur'),
  };
}

function validerUneResponsabilite(valeur: unknown, rang: number): ResponsabiliteDuProfil {
  if (!estObjet(valeur)) {
    throw new TypeError(`responsabilite ${String(rang)} non objet`);
  }
  return {
    type: exigerChaine(valeur, 'type'),
    cercle: chaineOuNul(valeur, 'cercle'),
    bureau: chaineOuNul(valeur, 'bureau'),
  };
}

/**
 * Valider la charge utile de `GET /api/v1/entities/{code}/people/{appartenance}`.
 *
 * **LES DEUX TABLEAUX SONT EXIGES.** Une reponse sans `cerclesSecondaires`
 * rendrait autrement une liste vide, indistinguable d'un collaborateur qui n'a
 * legitimement aucun cercle secondaire — l'echec produirait la meme observation
 * que le succes (§7.0, quatrieme proposition).
 */
export function validerLaFiche(valeur: unknown): FicheDuProfil {
  if (!estObjet(valeur)) {
    throw new TypeError('fiche non objet');
  }
  const secondaires = valeur['cercles_secondaires'];
  if (!Array.isArray(secondaires)) {
    throw new TypeError('champ « cercles_secondaires » absent ou non tableau');
  }
  const responsabilites = valeur['responsabilites'];
  if (!Array.isArray(responsabilites)) {
    throw new TypeError('champ « responsabilites » absent ou non tableau');
  }
  const principal = valeur['cercle_principal'];
  if (principal !== null && !estObjet(principal)) {
    throw new TypeError('champ « cercle_principal » ni objet ni null');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    personneId: exigerChaine(valeur, 'person_id'),
    prenom: exigerChaine(valeur, 'first_name'),
    nom: exigerChaine(valeur, 'last_name'),
    nomPrefere: chaineOuNul(valeur, 'preferred_name'),
    categorieProfessionnelle: exigerChaine(valeur, 'professional_category'),
    dateArrivee: exigerChaine(valeur, 'arrival_date'),
    presentation: chaineOuNul(valeur, 'short_bio'),
    funFact: chaineOuNul(valeur, 'fun_fact'),
    metier: chaineOuNul(valeur, 'metier'),
    statut: chaineOuNul(valeur, 'statut'),
    client: chaineOuNul(valeur, 'client'),
    dsm: chaineOuNul(valeur, 'dsm'),
    cerclePrincipal: principal === null ? null : validerUnCercle(principal, 'principal'),
    cerclesSecondaires: secondaires.map((c, rang) => validerUnCercle(c, `secondaire ${rang}`)),
    responsabilites: responsabilites.map(validerUneResponsabilite),
    photo: cheminDePhotoOuNul(valeur),
  };
}
