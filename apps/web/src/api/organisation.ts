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
  cheminBureau,
  cheminCercle,
  cheminFramework,
  EN_TETE_CORRELATION,
  type PageDuBureau,
  type PageDuCercle,
  type PageFramework,
  validerLaPageDuBureau,
  validerLaPageDuCercle,
  validerLaPageFramework,
} from '@onboarding/contracts';

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
