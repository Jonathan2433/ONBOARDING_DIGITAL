/**
 * Le client du tableau de bord administratif — LOT 9, `T5`/`T14`, `US001`.
 *
 * UNE SEULE LECTURE, AUCUNE PORTEE CALCULEE ICI
 *
 *   `profils_incomplets`, les six grandeurs, les imports en echec filtres par
 *   role : tout vient de l'API, qui reste l'autorite finale (regle 5).
 */
import {
  cheminTableauDeBord,
  EN_TETE_CORRELATION,
  type TableauDeBord,
  validerLeTableauDeBord,
} from '@onboarding/contracts';

import type { ReponseLue } from './profil';

export async function lireLeTableauDeBord(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<TableauDeBord>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminTableauDeBord(code), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: TableauDeBord | null;
  try {
    corps = validerLeTableauDeBord(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}
