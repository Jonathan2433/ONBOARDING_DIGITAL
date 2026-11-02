/**
 * Les clients Framework, cercle et bureau — LOT 6, `T9`, stories `MVP-L06-US001`
 * a `US003`.
 *
 * TROIS FONCTIONS, ET NON UNE SEULE PARAMETREE
 *
 *   Les trois routes n'ont ni le meme gabarit de chemin, ni la meme forme de
 *   reponse, ni les memes parametres de requete : le cercle pagine, le bureau
 *   non, le Framework n'a aucun parametre. Une fonction unique masquerait ces
 *   differences derriere une signature qui devrait toutes les prevoir. Meme
 *   parti que `trombinoscope.ts` et `profil.ts`, un fichier par ressource.
 *
 * CHAQUE FONCTION VALIDE CE QU'ELLE RECOIT
 *
 *   Les types TypeScript disparaissent a la compilation. `validerLaPageFramework`,
 *   `validerLaPageDuCercle` et `validerLaPageDuBureau` vivent dans
 *   `@onboarding/contracts`, source unique lue par TypeScript **et** par le test
 *   Python qui confronte le manifeste au schema servi (`DEC-492`).
 *
 * LE SIGNAL D'ABANDON EST PORTE PAR LES TROIS
 *
 *   Le §23.3 l'exige deja pour le changement d'entite : les trois appels d'une
 *   page qui se demonte ne doivent pas ecrire un etat apres coup.
 */
import {
  cheminArchivageDUnBureau,
  cheminArchivageDUnCercle,
  cheminAttributionDUnResponsable,
  cheminAttributionDuBooster,
  cheminBureau,
  cheminCercle,
  cheminCreationDUnBureau,
  cheminCreationDUnCercle,
  cheminDuRetraitDUnResponsable,
  cheminFramework,
  cheminRestaurationDUnBureau,
  cheminRestaurationDUnCercle,
  cheminRetraitDuBooster,
  type DemandeDAttributionDeResponsabilite,
  type DemandeDeCreationDeBureau,
  type DemandeDeCreationDeCercle,
  type DemandeDeRetraitFramework,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type PageDuBureau,
  type PageDuCercle,
  type PageFramework,
  type ResultatDArchivageDeStructure,
  type ResultatDAttributionDUnResponsable,
  type ResultatDAttributionDuBooster,
  type ResultatDeCreationDeStructure,
  type ResultatDeRestaurationDeStructure,
  type ResultatDeRetraitFramework,
  validerLArchivageDeStructure,
  validerLAttributionDUnResponsable,
  validerLAttributionDuBooster,
  validerLaCreationDeStructure,
  validerLaPageDuBureau,
  validerLaPageDuCercle,
  validerLaPageFramework,
  validerLaRestaurationDeStructure,
  validerLeRetraitFramework,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';

/** Ce qu'un appel rend, une fois lu — la meme forme pour les trois ressources. */
export interface ReponseLue<T> {
  readonly statut: number;
  readonly corps: T | null;
  readonly correlation: string | null;
}

async function appeler<T>(
  chemin: string,
  valider: (valeur: unknown) => T,
  signal?: AbortSignal,
): Promise<ReponseLue<T>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(chemin, requete);
  //  L'en-tete AVANT le corps : le corps peut lever, et la correlation est
  //  justement ce qu'on veut montrer quand quelque chose casse.
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** La synthese Framework d'une entite — `GET /entities/{code}/framework`. */
export async function lireLeFramework(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<PageFramework>> {
  return appeler(cheminFramework(code), validerLaPageFramework, signal);
}

/**
 * Une page de cercle — `GET /entities/{code}/circles/{code_cercle}`.
 *
 * Les criteres de pagination sont TOUJOURS envoyes, contrairement au
 * trombinoscope ou une recherche vide n'est pas un filtre : ici `page` et
 * `taille` ont un defaut cote API, mais l'ecran connait deja sa valeur
 * courante et gagne a l'envoyer explicitement — la reponse la confirme.
 */
export async function lireLeCercle(
  code: string,
  codeCercle: string,
  page: number,
  taille: number,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDuCercle>> {
  const parametres = new URLSearchParams({ page: String(page), taille: String(taille) });
  return appeler(
    `${cheminCercle(code, codeCercle)}?${parametres.toString()}`,
    validerLaPageDuCercle,
    signal,
  );
}

/** Une page de bureau — `GET /entities/{code}/offices/{code_bureau}`. Aucune pagination, §18.2. */
export async function lireLeBureau(
  code: string,
  codeBureau: string,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDuBureau>> {
  return appeler(cheminBureau(code, codeBureau), validerLaPageDuBureau, signal);
}

/**
 * Archiver ou restaurer un cercle ou un bureau — LOT 9, `T4`/`T14`.
 *
 * **MEME MONTAGE QUE `administration.ts`** : jeton anti-CSRF lu au dernier
 * instant via `GET /auth/session`, cle d'idempotence PAR TENTATIVE — rejouer
 * la meme apres un echec ferait croire au serveur qu'il s'agit du meme geste.
 *
 * **LE CORPS NE PORTE QU'UNE `version`** (§18.1 : aucun motif pour ces deux
 * ressources). L'identifiant de la cible (`circle_id`/`office_id`) est deja
 * expose par `GET …/framework` (`carte.identifiant`), donc jamais redemande.
 */
async function ecrireUneTransitionDeStructure<T>(
  chemin: string,
  version: number,
  valider: (valeur: unknown) => T,
): Promise<ReponseLue<T>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const reponse = await fetch(chemin, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    body: JSON.stringify({ version }),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

export function archiverUnCercle(
  code: string,
  circleId: string,
  version: number,
): Promise<ReponseLue<ResultatDArchivageDeStructure>> {
  return ecrireUneTransitionDeStructure(
    cheminArchivageDUnCercle(code, circleId),
    version,
    validerLArchivageDeStructure,
  );
}

export function restaurerUnCercle(
  code: string,
  circleId: string,
  version: number,
): Promise<ReponseLue<ResultatDeRestaurationDeStructure>> {
  return ecrireUneTransitionDeStructure(
    cheminRestaurationDUnCercle(code, circleId),
    version,
    validerLaRestaurationDeStructure,
  );
}

export function archiverUnBureau(
  code: string,
  officeId: string,
  version: number,
): Promise<ReponseLue<ResultatDArchivageDeStructure>> {
  return ecrireUneTransitionDeStructure(
    cheminArchivageDUnBureau(code, officeId),
    version,
    validerLArchivageDeStructure,
  );
}

export function restaurerUnBureau(
  code: string,
  officeId: string,
  version: number,
): Promise<ReponseLue<ResultatDeRestaurationDeStructure>> {
  return ecrireUneTransitionDeStructure(
    cheminRestaurationDUnBureau(code, officeId),
    version,
    validerLaRestaurationDeStructure,
  );
}

/**
 * Créer un cercle/bureau, attribuer le Booster/un responsable de bureau,
 * retirer l'un des deux — LOT 11, `T3`, hors backlog.
 *
 * **MEME MONTAGE QUE `collaborateurs.ts`** : un corps ARBITRAIRE, contrairement
 * à `ecrireUneTransitionDeStructure` ci-dessus qui n'envoie qu'une `version` —
 * ces six routes n'ont ni verrou optimiste ni forme de corps commune.
 */
async function ecrireDansLaStructure<T>(
  chemin: string,
  corpsEnvoye: unknown,
  valider: (valeur: unknown) => T,
): Promise<ReponseLue<T>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const reponse = await fetch(chemin, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    body: JSON.stringify(corpsEnvoye),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** `POST /entities/{code}/circles` — matrice §10.2. */
export function creerUnCercle(
  code: string,
  demande: DemandeDeCreationDeCercle,
): Promise<ReponseLue<ResultatDeCreationDeStructure>> {
  return ecrireDansLaStructure(
    cheminCreationDUnCercle(code),
    demande,
    validerLaCreationDeStructure,
  );
}

/** `POST /entities/{code}/offices` — matrice §10.3. */
export function creerUnBureau(
  code: string,
  demande: DemandeDeCreationDeBureau,
): Promise<ReponseLue<ResultatDeCreationDeStructure>> {
  return ecrireDansLaStructure(
    cheminCreationDUnBureau(code),
    demande,
    validerLaCreationDeStructure,
  );
}

/** `POST …/circles/{circle_id}/booster` — matrice §10.2/§20, TOUJOURS un remplacement. */
export function attribuerLeBooster(
  code: string,
  circleId: string,
  demande: DemandeDAttributionDeResponsabilite,
): Promise<ReponseLue<ResultatDAttributionDuBooster>> {
  return ecrireDansLaStructure(
    cheminAttributionDuBooster(code, circleId),
    demande,
    validerLAttributionDuBooster,
  );
}

/** `POST …/circles/{circle_id}/booster/retrait` — matrice §20. */
export function retirerLeBooster(
  code: string,
  circleId: string,
  demande: DemandeDeRetraitFramework,
): Promise<ReponseLue<ResultatDeRetraitFramework>> {
  return ecrireDansLaStructure(
    cheminRetraitDuBooster(code, circleId),
    demande,
    validerLeRetraitFramework,
  );
}

/** `POST …/offices/{office_id}/responsables` — matrice §10.3/§20, AJOUTE sans remplacer. */
export function attribuerUnResponsableDeBureau(
  code: string,
  officeId: string,
  demande: DemandeDAttributionDeResponsabilite,
): Promise<ReponseLue<ResultatDAttributionDUnResponsable>> {
  return ecrireDansLaStructure(
    cheminAttributionDUnResponsable(code, officeId),
    demande,
    validerLAttributionDUnResponsable,
  );
}

/** `POST …/offices/{office_id}/responsables/{affectation_id}/retrait` — matrice §20. */
export function retirerUnResponsableDeBureau(
  code: string,
  officeId: string,
  affectationId: string,
  demande: DemandeDeRetraitFramework,
): Promise<ReponseLue<ResultatDeRetraitFramework>> {
  return ecrireDansLaStructure(
    cheminDuRetraitDUnResponsable(code, officeId, affectationId),
    demande,
    validerLeRetraitFramework,
  );
}
