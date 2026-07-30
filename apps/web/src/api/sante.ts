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

// LE CONTRAT VIENT DESORMAIS DU PAQUET PARTAGE — T10, story MVP-L01-US007.
//
// Chemins, codes exploitables, formes de reponse et fonctions de validation
// etaient declares ICI depuis `T5`. Ils y etaient justes, mais ils n'etaient pas
// PARTAGES : le jour ou un second consommateur en aurait eu besoin, il les aurait
// recopies, et c'est ainsi qu'un contrat se dedouble. Ils vivent maintenant dans
// `@onboarding/contracts`, dont la source unique est un manifeste JSON que le
// controle Python confronte au schema OpenAPI reellement servi.
//
// CE QUI RESTE ICI : le transport. `fetch`, les en-tetes, la classe d'erreur —
// tout ce qui est propre au navigateur et qu'un autre consommateur ne voudrait pas.
//
// La reexportation preserve les imports existants : `PageStatut` et les tests de
// `T5` importent ces noms depuis ce module, et rien ne justifie de les reecrire.
export {
  CHEMIN_READY,
  CHEMIN_VERSION,
  EN_TETE_CORRELATION,
  validerEtatServices,
  validerVersion,
} from '@onboarding/contracts';
export type {
  Dependance,
  EtatServices,
  StatutDependance,
  StatutGlobal,
  Version,
} from '@onboarding/contracts';

import {
  CHEMIN_READY,
  CHEMIN_VERSION,
  CODES_READY,
  CODES_VERSION,
  EN_TETE_CORRELATION,
  validerEtatServices,
  validerVersion,
} from '@onboarding/contracts';
import type { EtatServices, Version } from '@onboarding/contracts';

/** Charge utile et identifiant de correlation de la reponse qui l'a portee. */
export interface Reponse<T> {
  readonly charge: T;
  readonly correlation: string | null;
}

/**
 * Echec d'interrogation de l'API.
 *
 * Porte l'identifiant de correlation quand la reponse en avait un : c'est lui
 * que l'utilisateur cite dans un signalement (cahier 17.4).
 */
export class ErreurSante extends Error {
  readonly correlation: string | null;

  constructor(message: string, correlation: string | null) {
    super(message);
    this.name = 'ErreurSante';
    this.correlation = correlation;
  }
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
  return interroger(CHEMIN_READY, CODES_READY, validerEtatServices);
}

/** Lire la version deployee. Seul 200 est exploitable. */
export function lireVersion(): Promise<Reponse<Version>> {
  return interroger(CHEMIN_VERSION, CODES_VERSION, validerVersion);
}
