/**
 * Le client des evenements consultes — LOT 8, `T9`, story `MVP-L08-US003` (2/2).
 *
 * MEME MONTAGE QUE `organisation.ts` ET `profil.ts` : le validateur du contrat
 * fait foi, le signal d'abandon est porte de bout en bout. `ReponseLue<T>` est
 * REPRISE de `profil.ts`, pas redeclaree une troisieme fois.
 *
 * `classement`, `page` ET `taille` SONT TOUJOURS ENVOYES EXPLICITEMENT
 *
 *   Meme raisonnement que `lireLeCercle` : l'ecran connait deja sa valeur
 *   courante — l'onglet selectionne, la page affichee — et l'envoyer
 *   explicitement laisse la reponse la confirmer plutot que de dependre d'un
 *   defaut cote API que l'ecran ne verrait jamais changer. `classement` est de
 *   toute facon obligatoire : la route repond `422` sans lui.
 */
import {
  type ClassementEvenement,
  cheminEvenements,
  EN_TETE_CORRELATION,
  type PageDesEvenements,
  validerLaPageDesEvenements,
} from '@onboarding/contracts';

import type { ReponseLue } from './profil';

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

/** Une page d'evenements — `GET /entities/{code}/events`, les deux onglets du §10.6. */
export function lireLesEvenements(
  code: string,
  classement: ClassementEvenement,
  page: number,
  taille: number,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDesEvenements>> {
  const parametres = new URLSearchParams({
    classement,
    page: String(page),
    taille: String(taille),
  });
  return appeler(
    `${cheminEvenements(code)}?${parametres.toString()}`,
    validerLaPageDesEvenements,
    signal,
  );
}
