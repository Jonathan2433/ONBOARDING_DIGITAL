/**
 * Client des routes d'authentification — LOT 3, sous-etape `T11`.
 *
 * LES CHEMINS VIENNENT DU CONTRAT PARTAGE, JAMAIS D'UNE CHAINE ECRITE ICI
 *
 *   `@onboarding/contracts` est la source unique, lue par TypeScript **et** par un
 *   controle Python qui verifie que le schema OpenAPI la respecte (`DEC-492`).
 *   Ecrire `/api/v1/auth/magic-link` ici creerait une seconde source, qui
 *   vieillirait au premier changement de prefixe.
 *
 * AUCUN JETON N'EST CONSERVE, NULLE PART
 *
 *   Interdit absolu du §9.5 : « aucun jeton dans `localStorage` ». Le cookie de
 *   session est `HttpOnly` (`T6`), donc le navigateur l'envoie seul et ce code ne
 *   le lit **jamais**. Le jeton anti-CSRF, lui, vit en memoire le temps d'un
 *   rendu : il est relu a chaque fois par `GET /auth/session`, ce qui est
 *   precisement pourquoi cette route ne l'exige pas elle-meme (`DEC-531`).
 *
 *   `make sessions-check` verifie cette absence **sur les sources**, en retirant
 *   les commentaires et en gardant les chaines.
 *
 * `credentials: 'same-origin'` ET NON `'include'`
 *
 *   `DEC-470` : la page et l'API partagent une seule origine, mandatee par Caddy.
 *   `'include'` enverrait les cookies a une origine tierce si l'URL changeait un
 *   jour ; `'same-origin'` ne le fera jamais. C'est le defaut de `fetch`, et le
 *   nommer vaut mieux que de s'y fier.
 */
import {
  CHEMIN_CONNEXION_ADMINISTRATEUR,
  CHEMIN_CONSOMMATION_MAGIC_LINK,
  CHEMIN_DECONNEXION,
  CHEMIN_DEMANDE_MAGIC_LINK,
  CHEMIN_SESSION,
  EN_TETE_JETON_CSRF,
} from '@onboarding/contracts';

/** Ce qu'une reponse d'API porte, une fois lue. */
export interface Reponse<T> {
  readonly statut: number;
  readonly corps: T | null;
}

export interface ReponseGenerique {
  readonly message: string;
}

export interface ReponseDeConsommation {
  readonly message: string;
  readonly personne?: string;
}

export interface ReponseDeSession {
  readonly personne: string;
  readonly jeton_csrf: string;
}

async function appeler<T>(
  chemin: string,
  options: { methode?: string; corps?: unknown; jetonCsrf?: string } = {},
): Promise<Reponse<T>> {
  const enTetes: Record<string, string> = {};
  if (options.corps !== undefined) {
    enTetes['Content-Type'] = 'application/json';
  }
  if (options.jetonCsrf !== undefined) {
    enTetes[EN_TETE_JETON_CSRF] = options.jetonCsrf;
  }

  //  `exactOptionalPropertyTypes` est actif : `body: undefined` n'est PAS la meme
  //  chose qu'une propriete absente, et `RequestInit` n'accepte que la seconde.
  //  Le reglage strict a raison -- un `undefined` explicite dit « pas de corps »
  //  la ou l'absence dit « ne t'en occupe pas », et `fetch` distingue les deux.
  const requete: RequestInit = {
    method: options.methode ?? (options.corps === undefined ? 'GET' : 'POST'),
    headers: enTetes,
    credentials: 'same-origin',
  };
  if (options.corps !== undefined) {
    requete.body = JSON.stringify(options.corps);
  }

  const reponse = await fetch(chemin, requete);

  //  UN CORPS ILLISIBLE N'EST PAS UNE ERREUR RESEAU, et les confondre jetterait
  //  le diagnostic. Le code HTTP reste rendu ; c'est l'appelant qui decide.
  let corps: T | null;
  try {
    corps = (await reponse.json()) as T;
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps };
}

export function demanderUnLien(email: string): Promise<Reponse<ReponseGenerique>> {
  return appeler<ReponseGenerique>(CHEMIN_DEMANDE_MAGIC_LINK, { corps: { email } });
}

/**
 * Consommer un lien. **LE JETON VOYAGE DANS LE CORPS, JAMAIS DANS L'URL.**
 *
 * Le lien de l'e-mail le porte bien en chaine de requete -- c'est le seul moyen
 * de le transmettre par courriel -- mais cette page ne le **retransmet** jamais
 * ainsi : une chaine de requete finit dans l'historique du navigateur, dans un
 * en-tete `Referer` et dans tout journal d'acces de mandataire.
 */
export function consommerUnLien(token: string): Promise<Reponse<ReponseDeConsommation>> {
  return appeler<ReponseDeConsommation>(CHEMIN_CONSOMMATION_MAGIC_LINK, { corps: { token } });
}

export function connecterUnAdministrateur(
  email: string,
  motDePasse: string,
): Promise<Reponse<ReponseGenerique>> {
  return appeler<ReponseGenerique>(CHEMIN_CONNEXION_ADMINISTRATEUR, {
    corps: { email, mot_de_passe: motDePasse },
  });
}

export function lireLaSession(): Promise<Reponse<ReponseDeSession>> {
  return appeler<ReponseDeSession>(CHEMIN_SESSION);
}

/**
 * Se deconnecter. **Elle exige le jeton anti-CSRF**, `DEC-531`.
 *
 * C'est la seule ecriture du lot qui en exige un, parce que c'est la seule qui
 * dispose d'une session. Sans lui, l'API rend 403 — et c'est voulu.
 */
export function seDeconnecter(jetonCsrf: string): Promise<Reponse<ReponseGenerique>> {
  return appeler<ReponseGenerique>(CHEMIN_DECONNEXION, { corps: {}, jetonCsrf });
}
