/**
 * Le client du reporting étendu — LOT 10, `T10`/`T15`, `MVP-L10-US003`.
 *
 * TROIS LECTURES, TROIS FORMES — AUCUNE FACTORISATION FORCÉE
 *
 *   Les indicateurs ne paginent pas, les deux détails paginent : même parti
 *   que `organisation.ts` (Framework/cercle/bureau), une fonction par route
 *   plutôt qu'une signature unique qui devrait prévoir ce que les trois ne
 *   partagent pas.
 */
import {
  cheminDetailOnboarding,
  cheminIndicateurs,
  cheminProfilsIncomplets,
  EN_TETE_CORRELATION,
  type FiltresDeReporting,
  type Indicateurs,
  type ReponseDesProfilsIncomplets,
  type ReponseDuDetailOnboarding,
  validerLeDetailOnboarding,
  validerLesIndicateurs,
  validerLesProfilsIncomplets,
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
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

export function lireLesIndicateurs(
  code: string,
  filtres: FiltresDeReporting = {},
  signal?: AbortSignal,
): Promise<ReponseLue<Indicateurs>> {
  return appeler(cheminIndicateurs(code, filtres), validerLesIndicateurs, signal);
}

export function lireLeDetailOnboardingDuReporting(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDeReporting = {},
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDuDetailOnboarding>> {
  return appeler(
    cheminDetailOnboarding(code, page, taille, filtres),
    validerLeDetailOnboarding,
    signal,
  );
}

export function lireLesProfilsIncomplets(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDeReporting = {},
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesProfilsIncomplets>> {
  return appeler(
    cheminProfilsIncomplets(code, page, taille, filtres),
    validerLesProfilsIncomplets,
    signal,
  );
}
