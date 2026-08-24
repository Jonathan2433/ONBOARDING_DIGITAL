/**
 * Le client du portail national — LOT 4, `T1` et `T2`.
 *
 * IL VALIDE CE QU'IL RECOIT, IL NE SE FIE PAS AUX TYPES
 *
 *   Les types TypeScript disparaissent a la compilation. Un `fetch` qui recevrait
 *   autre chose que la forme attendue produirait un `undefined` quelque part dans
 *   le rendu, loin de la cause. `validerLesEntites` et `validerUneEntite` viennent
 *   du paquet de contrat, qui est la source unique -- meme motif que
 *   `validerEtatServices` en `T5` du LOT 1.
 *
 * IL PORTE UN SIGNAL D'ABANDON, ET LE §23.3 L'EXIGE
 *
 *   « Le changement d'entite selectionnee ... annule les requetes et caches
 *   associes a l'entite precedente. » Sans abandon, une reponse lente pour
 *   l'entite quittee arriverait APRES celle de la nouvelle et l'ecraserait :
 *   l'ecran afficherait Bordeaux alors que l'adresse dit Paris. **Le defaut
 *   n'apparait que sous latence**, donc jamais en developpement local -- c'est
 *   exactement le genre de defaut que le §7.16 decrit, ce qui n'a jamais tourne
 *   ailleurs n'est pas eprouve.
 */
import {
  CHEMIN_ENTITES,
  cheminEntite,
  cheminPermissions,
  type EntiteDuPortail,
  type PermissionsDeLEntite,
  type ReponseDesEntites,
  validerLesEntites,
  validerLesPermissions,
  validerUneEntite,
} from '@onboarding/contracts';

/** Ce qu'un appel du portail rend, une fois lu. */
export interface ReponseDuPortail<T> {
  readonly statut: number;
  readonly corps: T | null;
}

async function appeler<T>(
  chemin: string,
  valider: (valeur: unknown) => T,
  signal?: AbortSignal,
): Promise<ReponseDuPortail<T>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(chemin, requete);

  //  UN CORPS ABSENT OU D'UNE AUTRE FORME N'EST PAS UNE ERREUR RESEAU : le code
  //  HTTP reste rendu, et c'est l'appelant qui decide. Un 404 n'a pas de charge
  //  utile a valider, et le confondre avec une panne jetterait le diagnostic.
  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps };
}

/** Les entites actives du portail national — `GET /api/v1/entities`. */
export function listerLesEntites(
  signal?: AbortSignal,
): Promise<ReponseDuPortail<ReponseDesEntites>> {
  return appeler(CHEMIN_ENTITES, validerLesEntites, signal);
}

/**
 * L'entite consultee, resolue par son code — `GET /api/v1/entities/{code}`.
 *
 * **404 COUVRE DEUX CAS**, et l'API ne les distingue pas : le code est inconnu, ou
 * l'entite existe sans etre active. Le frontend n'a donc rien a en deduire.
 */
export function lireLEntite(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseDuPortail<EntiteDuPortail>> {
  return appeler(cheminEntite(code), validerUneEntite, signal);
}

/**
 * Les droits de l'appelant dans l'entite consultee — LOT 4, `T8`.
 *
 * **C'EST LA TROISIEME REGLE DU §23.3 QUI EXISTE PAR CET APPEL** : « recharge les
 * permissions ». Sans lui, le frontend n'aurait rien a recharger, et la regle
 * serait une intention sans porteur.
 *
 * **LE SIGNAL EST LE MEME QUE CELUI DE L'ENTITE, ET CE N'EST PAS UN DETAIL.** Les
 * deux appels d'un meme changement d'entite doivent etre abandonnes ENSEMBLE :
 * un abandon partiel laisserait arriver les permissions de l'entite quittee sur
 * l'entite nouvelle, ce qui est precisement ce que la quatrieme regle interdit --
 * et l'ecran afficherait des droits qui ne sont pas ceux du contexte.
 */
export function lireLesPermissions(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseDuPortail<PermissionsDeLEntite>> {
  return appeler(cheminPermissions(code), validerLesPermissions, signal);
}
