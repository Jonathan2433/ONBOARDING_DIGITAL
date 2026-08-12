/**
 * Le contrat des endpoints de sante — types et constantes partages.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 18.7, 28.1.
 *
 * D'OU VIENNENT CES DECLARATIONS
 *
 *   Les types etaient dans `apps/web/src/api/sante.ts` depuis `T5`, ou ils
 *   avaient ete ecrits pour la page de statut. Ils y etaient justes, mais ils
 *   n'etaient PAS partages : le jour ou un second consommateur en aurait eu
 *   besoin, il les aurait recopies — et c'est ainsi qu'un contrat se dedouble.
 *   Le critere de la story dit « generation/partage des contrats » : le partage,
 *   c'est ce deplacement.
 *
 *   Les chemins, les codes exploitables et le nom de l'en-tete ne sont pas
 *   redeclares ici : ils sont LUS dans `contrat-api.json`, que le controle Python
 *   confronte au schema OpenAPI reellement servi. Une seule source, deux
 *   langages, et un controle qui echoue en cas de divergence.
 *
 * CE QUI RESTE DANS `apps/web`
 *
 *   La logique de `fetch`, la gestion du transport et la classe d'erreur. Elles
 *   sont propres au navigateur et n'ont rien a partager avec un autre
 *   consommateur — un client Python, par exemple, n'en voudrait pas.
 *
 * AUCUN TYPE METIER ICI. Ni `Collaborateur`, ni `Cercle`, ni `Parcours`. Le
 * modele de donnees appartient au LOT 2, qui n'est pas ouvert.
 */

import contrat from './contrat-api.json' with { type: 'json' };

/** Une entree du manifeste. */
export interface EndpointContrat {
  readonly cle: string;
  readonly chemin: string;
  readonly methode: string;
  readonly codesExploitables: readonly number[];
  readonly forme: string;
}

/** Le manifeste, tel qu'il est declare. */
export const CONTRAT_API = contrat;

/** L'en-tete de correlation, cahier 28.1. */
export const EN_TETE_CORRELATION: string = contrat.enTeteCorrelation;

/** Le prefixe des chemins METIER. Les endpoints de sante en sont exclus (DEC-465). */
export const PREFIXE_VERSIONNE: string = contrat.prefixeVersionne;

/**
 * Retrouver une entree du contrat par sa cle.
 *
 * Elle LEVE si la cle est inconnue, plutot que de rendre `undefined` : un chemin
 * `undefined` passe a `fetch` produirait une requete vers l'URL courante, donc un
 * 200 sur la page elle-meme — une erreur silencieuse au lieu d'un echec.
 */
export function endpoint(cle: string): EndpointContrat {
  const trouve = contrat.endpoints.find((e) => e.cle === cle);
  if (trouve === undefined) {
    const connues = contrat.endpoints.map((e) => e.cle).join(', ');
    throw new Error(`endpoint inconnu : ${cle}. Cles declarees : ${connues}`);
  }
  return trouve as EndpointContrat;
}

/** Les chemins d'exploitation, lus du manifeste et non recopies. */
export const CHEMIN_LIVE: string = endpoint('live').chemin;
export const CHEMIN_READY: string = endpoint('ready').chemin;
export const CHEMIN_VERSION: string = endpoint('version').chemin;

/** Les codes qu'il faut savoir exploiter, et non traiter comme des erreurs. */
export const CODES_READY: readonly number[] = endpoint('ready').codesExploitables;
export const CODES_VERSION: readonly number[] = endpoint('version').codesExploitables;

// ---------------------------------------------------------------------------
//  Les formes de reponse
// ---------------------------------------------------------------------------

export type StatutDependance = 'disponible' | 'indisponible';
export type StatutGlobal = 'pret' | 'indisponible';

export interface Dependance {
  readonly nom: string;
  readonly statut: StatutDependance;
  readonly duree_ms: number;
  readonly motif: string | null;
}

export interface EtatServices {
  readonly statut: StatutGlobal;
  readonly dependances: readonly Dependance[];
}

export interface Version {
  readonly version: string;
  readonly revision: string;
  readonly environnement: string;
}

// ---------------------------------------------------------------------------
//  La validation des charges utiles
//
//  ELLE FAIT PARTIE DU CONTRAT, et c'est pourquoi elle est ici et non dans le
//  frontend. Un type TypeScript disparait a la compilation : il ne verifie rien
//  de ce qui arrive du reseau. La forme n'est donc reellement partagee que si la
//  fonction qui la CONTROLE l'est aussi.
//
//  Validation manuelle et non Zod : `DEC-456` n'installe pas Zod avant le LOT 4,
//  faute d'usage, et deux formes de reponse ne le justifient pas.
// ---------------------------------------------------------------------------

function estObjet(valeur: unknown): valeur is Record<string, unknown> {
  return typeof valeur === 'object' && valeur !== null && !Array.isArray(valeur);
}

function exigerChaine(source: Record<string, unknown>, cle: string): string {
  const valeur = source[cle];
  if (typeof valeur !== 'string') {
    throw new TypeError(`champ « ${cle} » absent ou non textuel`);
  }
  return valeur;
}

function validerDependance(valeur: unknown): Dependance {
  if (!estObjet(valeur)) {
    throw new TypeError('dependance non objet');
  }
  const statut = exigerChaine(valeur, 'statut');
  if (statut !== 'disponible' && statut !== 'indisponible') {
    throw new TypeError(`statut de dependance inattendu : ${statut}`);
  }
  const duree = valeur['duree_ms'];
  if (typeof duree !== 'number') {
    throw new TypeError('champ « duree_ms » absent ou non numerique');
  }
  const motif = valeur['motif'];
  if (motif !== null && typeof motif !== 'string') {
    throw new TypeError('champ « motif » ni nul ni textuel');
  }
  return { nom: exigerChaine(valeur, 'nom'), statut, duree_ms: duree, motif };
}

/** Valider la charge utile de `/health/ready`. Leve si la forme diverge. */
export function validerEtatServices(valeur: unknown): EtatServices {
  if (!estObjet(valeur)) {
    throw new TypeError('reponse non objet');
  }
  const statut = exigerChaine(valeur, 'statut');
  if (statut !== 'pret' && statut !== 'indisponible') {
    throw new TypeError(`statut global inattendu : ${statut}`);
  }
  const dependances = valeur['dependances'];
  if (!Array.isArray(dependances)) {
    throw new TypeError('champ « dependances » absent ou non tableau');
  }
  return { statut, dependances: dependances.map(validerDependance) };
}

/** Valider la charge utile de `/health/version`. Leve si la forme diverge. */
export function validerVersion(valeur: unknown): Version {
  if (!estObjet(valeur)) {
    throw new TypeError('reponse non objet');
  }
  return {
    version: exigerChaine(valeur, 'version'),
    revision: exigerChaine(valeur, 'revision'),
    environnement: exigerChaine(valeur, 'environnement'),
  };
}
