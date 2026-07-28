/**
 * Client des endpoints de sante de l'API.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * FONDEMENT — cahier des charges §18.7 : `/health/live`, `/health/ready`,
 * `/health/version`.
 *
 * POURQUOI CES CHEMINS NE SONT PAS PREFIXES PAR /api/v1
 *     `DEC-465` place les endpoints de sante HORS du prefixe versionne : ils
 *     relevent de l'exploitation, et l'adresse que sonde un orchestrateur ne
 *     doit pas bouger avec les versions de l'API. La variable
 *     `VITE_API_BASE_URL` vaut `/api/v1` et n'a donc RIEN a faire ici. Un test
 *     dedie l'eprouve, parce que prefixer ces chemins par megarde produirait un
 *     404 que rien ne distinguerait d'une API mal deployee.
 *
 * POURQUOI 503 N'EST PAS UNE ERREUR
 *     `/health/ready` repond 503 quand une dependance manque, mais avec
 *     EXACTEMENT la meme forme JSON qu'un 200 : `statut` et le detail des
 *     dependances. Le lire comme une erreur reseau reviendrait a jeter le
 *     diagnostic au moment ou il devient utile. Un 503 est donc un etat
 *     DEGRADE exploitable ; seuls les autres codes et l'echec du transport
 *     sont des erreurs.
 *
 * POURQUOI UNE VALIDATION MANUELLE ET PAS ZOD
 *     `DEC-456` : Zod n'est pas installe avant le LOT 4, faute d'usage. La
 *     charge utile venant du reseau est `unknown` : elle est verifiee ici a la
 *     main, ce qui reste modeste pour deux formes de reponse.
 */

/** En-tete portant l'identifiant de correlation, cote API comme cote worker. */
export const EN_TETE_CORRELATION = 'X-Request-ID';

/** Chemins d'exploitation. Volontairement hors de `VITE_API_BASE_URL`. */
export const CHEMIN_READY = '/health/ready';
export const CHEMIN_VERSION = '/health/version';

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

/** Charge utile et identifiant de correlation de la reponse qui l'a portee. */
export interface Reponse<T> {
  readonly charge: T;
  readonly correlation: string | null;
}

/**
 * Echec d'interrogation de l'API.
 *
 * Porte l'identifiant de correlation quand la reponse en avait un : c'est lui
 * que l'utilisateur cite dans un signalement (cahier §17.4).
 */
export class ErreurSante extends Error {
  readonly correlation: string | null;

  constructor(message: string, correlation: string | null) {
    super(message);
    this.name = 'ErreurSante';
    this.correlation = correlation;
  }
}

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

function validerEtatServices(valeur: unknown): EtatServices {
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

function validerVersion(valeur: unknown): Version {
  if (!estObjet(valeur)) {
    throw new TypeError('reponse non objet');
  }
  return {
    version: exigerChaine(valeur, 'version'),
    revision: exigerChaine(valeur, 'revision'),
    environnement: exigerChaine(valeur, 'environnement'),
  };
}

async function interroger<T>(
  chemin: string,
  codesExploitables: readonly number[],
  valider: (valeur: unknown) => T,
): Promise<Reponse<T>> {
  let reponse: Response;
  try {
    reponse = await fetch(chemin, { headers: { Accept: 'application/json' } });
  } catch {
    // L'echec du transport ne porte aucune correlation : la requete n'a pas
    // atteint l'API, il n'y a donc aucune trace a citer.
    throw new ErreurSante("l'API est injoignable", null);
  }

  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  if (!codesExploitables.includes(reponse.status)) {
    throw new ErreurSante(`l'API a repondu ${String(reponse.status)}`, correlation);
  }

  let brut: unknown;
  try {
    brut = await reponse.json();
  } catch {
    throw new ErreurSante("la reponse de l'API est illisible", correlation);
  }

  try {
    return { charge: valider(brut), correlation };
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : 'forme inattendue';
    throw new ErreurSante(`la reponse de l'API est inattendue : ${detail}`, correlation);
  }
}

/**
 * Lire l'etat reel des dependances sondees par l'API.
 *
 * 200 et 503 sont tous deux exploitables : c'est le champ `statut` de la charge
 * utile qui dit si la plateforme est prete ou degradee.
 */
export function lireEtatServices(): Promise<Reponse<EtatServices>> {
  return interroger(CHEMIN_READY, [200, 503], validerEtatServices);
}

/** Lire la version deployee. Seul 200 est exploitable. */
export function lireVersion(): Promise<Reponse<Version>> {
  return interroger(CHEMIN_VERSION, [200], validerVersion);
}
