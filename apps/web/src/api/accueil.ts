/**
 * Le client de l'accueil d'une entite — LOT 8, `T11`, `MVP-L08-US001` (2/2) et
 * `MVP-L08-US006` (2/2).
 *
 * MEME MONTAGE QUE `evenements.ts` : `lire<T>` pour l'unique GET de ce module,
 * `ReponseLue<T>` REPRISE de `profil.ts`, jamais redeclaree une troisieme fois
 * (`DEC-466`).
 */
import {
  type AccueilDEntite,
  cheminAccueil,
  EN_TETE_CORRELATION,
  validerLAccueil,
} from '@onboarding/contracts';

import type { ReponseLue } from './profil';

async function lire<T>(
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

/** L'accueil d'une entite — `GET /api/v1/entities/{code}/accueil`. */
export function lireLAccueil(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<AccueilDEntite>> {
  return lire(cheminAccueil(code), validerLAccueil, signal);
}
