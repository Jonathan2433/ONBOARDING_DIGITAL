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
import { PREFIXE_VERSIONNE, endpoint } from './sante.js';

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
/**
 * Le cercle PRINCIPAL d'une ligne, avec son jeton de couleur — LOT 5, `T10`.
 *
 * **LE NOM VOYAGE AVEC LE JETON, ET LE §10.1 L'EXIGE** : « la couleur du cercle
 * peut etre utilisee sur les bordures, arriere-plans legers et badges, mais
 * **jamais comme seul moyen de transmettre une information** ». Un ecran qui
 * n'aurait que le jeton ne pourrait pas respecter la regle, quoi qu'il fasse.
 */
export interface CercleDeLaListe {
  readonly code: string;
  readonly nom: string;
  /**
   * **LE JETON PEUT MANQUER, ET C'EST LE SCHEMA QUI LE DIT.** `circle.color_token`
   * est nullable au catalogue : un cercle sans couleur declaree est un etat
   * legitime, pas une anomalie. Le typer `string` a fait servir la chaine
   * « None » -- un jeton d'apparence plausible. Defaut `T10-8`.
   *
   * **L'ABSENCE RESTE REFUSEE** : `null` est une valeur, `undefined` une
   * divergence de contrat.
   */
  readonly jetonDeCouleur: string | null;
}

export interface CollaborateurDuTrombinoscope {
  readonly id: string;
  readonly personneId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nomPrefere: string | null;
  readonly categorieProfessionnelle: string;
  readonly dateArrivee: string;
  /** Le chemin de la miniature, ou `null` — voir `cheminDePhotoOuNul`. */
  readonly photo: string | null;
  /**
   * LES QUATRE CHAMPS DU VERSO — LOT 5, `T10`.
   *
   * Le §10.1 : « le **verso** presente les informations **professionnelles
   * principales** ». Tous facultatifs, et c'est le schema qui le dit : un nouvel
   * arrivant peut n'avoir ni metier, ni statut, ni cercle, et le client est nul
   * en `intercontract`. Les rendre obligatoires obligerait l'API a inventer.
   */
  readonly metier: string | null;
  readonly statut: string | null;
  readonly client: string | null;
  readonly cercle: CercleDeLaListe | null;
}

/**
 * Le chemin d'une miniature, ou `null` — LOT 5, `T5`.
 *
 * **UN CHEMIN, JAMAIS DES OCTETS.** Le §16.1 interdit Base64 en propre ; un
 * champ qui porterait l'image ferait grossir chaque ligne de plusieurs dizaines
 * de kilo-octets, et une page de cent lignes en paierait cent fois le prix.
 *
 * **ET IL N'EST PAS L'`object_key`.** Le validateur refuse toute valeur qui ne
 * commence pas par le prefixe versionne : une cle de stockage exposerait la
 * disposition du bucket, et le navigateur ne pourrait rien en faire.
 *
 * `null` couvre CINQ causes indistinguables — pas d'autorisation, retiree, pas
 * encore active, media non `ready`, aucune variante `thumbnail`. L'appelant
 * affiche alors l'avatar neutre du §21.2, et ne doit surtout pas essayer de
 * deviner laquelle : le §21.2 ne veut pas le dire.
 */
export function cheminDePhotoOuNul(valeur: Record<string, unknown>): string | null {
  const brut = valeur['photo'];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`**, meme distinction qu'ailleurs : un champ
    //  manquant est une reponse malformee, un `null` est une photo non servable.
    throw new TypeError('champ « photo » ni chaine ni null');
  }
  if (!brut.startsWith(PREFIXE_VERSIONNE)) {
    throw new TypeError(`champ « photo » hors du prefixe versionne : ${brut}`);
  }
  return brut;
}

/** Une page du trombinoscope, et de quoi savoir ou l'on est. */
export interface ReponseDuTrombinoscope {
  readonly collaborateurs: readonly CollaborateurDuTrombinoscope[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

/**
 * Les cinq axes de filtre du cahier §9.3 — LOT 5, `T3`.
 *
 * **LE SIXIEME AXE DU CAHIER — « entite » — N'EST PAS ICI**, et ce n'est pas un
 * oubli : c'est le `code` de la route. Le trombinoscope est per-entite, et
 * ajouter un parametre `entite=` sur une adresse deja bornee par `{code}` serait
 * redondant au mieux, une fuite inter-entites au pire.
 */
export interface FiltresDuTrombinoscope {
  readonly recherche?: string;
  readonly cercle?: string;
  readonly dsm?: string;
  readonly metier?: string;
  readonly client?: string;
  readonly statut?: string;
}

/**
 * Les deux statuts professionnels du cahier §9.3.
 *
 * **ECRITS ICI PARCE QUE LE MANIFESTE NE PORTE PAS DE PARAMETRES DE REQUETE**, et
 * le dire vaut mieux que de laisser croire qu'ils sont derives. L'API refuse
 * toute autre valeur : c'est elle l'autorite, et cette liste ne sert qu'a ce que
 * l'ecran ne PROPOSE que des valeurs valides.
 */
export const STATUTS_PROFESSIONNELS: readonly string[] = ['mission', 'intercontract'];

/** La borne du terme cherche, telle que l'API la refuse au-dela. */
export const LONGUEUR_MAXIMALE_RECHERCHE = 128;

/** Le chemin d'une entite, son code ENCODE — meme motif que `cheminEntite`. */
export function cheminTrombinoscope(
  code: string,
  page?: number,
  taille?: number,
  filtres?: FiltresDuTrombinoscope,
): string {
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
  //  **L'ORDRE DES AXES EST CELUI DE L'INTERFACE, ET IL EST STABLE.** Deux appels
  //  aux memes filtres doivent rendre la MEME adresse : sinon deux cles de cache
  //  differentes designeraient la meme page, et le §23.3 quatrieme regle —
  //  « annule les requetes et caches associes » — deviendrait inapplicable.
  for (const axe of ['recherche', 'cercle', 'dsm', 'metier', 'client', 'statut'] as const) {
    const valeur = filtres?.[axe];
    //  Une chaine VIDE est ecartee : `?recherche=` demanderait a l'API de
    //  chercher le vide, qui correspond a tout le monde.
    if (valeur !== undefined && valeur !== '') {
      parametres.push(`${axe}=${encodeURIComponent(valeur)}`);
    }
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
    photo: cheminDePhotoOuNul(valeur),
    metier: chaineOuNul(valeur, 'metier', rang),
    statut: chaineOuNul(valeur, 'statut', rang),
    client: chaineOuNul(valeur, 'client', rang),
    cercle: cercleOuNul(valeur, rang),
  };
}

/**
 * Une chaine, `null`, ou une erreur — jamais `undefined`.
 *
 * **`undefined` EST REFUSE AUTANT QUE 42.** Une cle absente signifie que l'API ne
 * sert pas ce champ, ce qui est une reponse d'une AUTRE version : l'accepter en la
 * traduisant en `null` masquerait une divergence de contrat derriere une valeur
 * parfaitement plausible -- le §7.0 quatrieme proposition, l'echec produirait la
 * meme observation que le succes.
 */
function chaineOuNul(source: Record<string, unknown>, cle: string, rang: number): string | null {
  const valeur = source[cle];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'string') {
    throw new TypeError(`collaborateur ${String(rang)} : « ${cle} » ni chaine ni null`);
  }
  return valeur;
}

/** Le cercle principal, ou `null`. Ses TROIS champs sont exiges ensemble. */
function cercleOuNul(source: Record<string, unknown>, rang: number): CercleDeLaListe | null {
  const valeur = source['cercle'];
  if (valeur === null) {
    return null;
  }
  if (!estObjet(valeur)) {
    throw new TypeError(`collaborateur ${String(rang)} : « cercle » ni objet ni null`);
  }
  //  **LES TROIS CLES SONT EXIGEES ENSEMBLE, MAIS LE JETON PEUT VALOIR `null`.**
  //  Le §10.1 veut que le NOM voyage toujours -- sans lui, « jamais la couleur
  //  seule » serait inapplicable. Le jeton, lui, est nullable au schema : une
  //  carte sans bordure coloree reste parfaitement lisible.
  return {
    code: exigerChaine(valeur, 'code'),
    nom: exigerChaine(valeur, 'nom'),
    jetonDeCouleur: chaineOuNul(valeur, 'jeton_de_couleur', rang),
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
