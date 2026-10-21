/**
 * Le client du signalement d'un bug — LOT 10, `T11`, `MVP-L10-US005`.
 *
 * AUCUNE CLE D'IDEMPOTENCE, ET C'EST MESURE PLUTOT QUE SUPPOSE
 *
 *   `gestionDesLiens.ts`/`gestionDuContenu.ts` en envoient une a chaque
 *   ecriture. `POST /bug-reports` ne la lit nulle part cote API (mesure :
 *   `app/support/routes.py` n'importe aucune aide d'idempotence, a la
 *   difference d'`app/auth/`, `app/people/` ou `app/onboarding/`). L'envoyer
 *   quand meme suggererait une garantie que le serveur ne tient pas — un
 *   double envoi reseau crée simplement deux signalements, ce qui est sans
 *   consequence pour cette ressource, a la difference d'un transfert en
 *   masse.
 */
import {
  CHEMIN_SIGNALEMENT,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  validerUnSignalement,
} from '@onboarding/contracts';
import type { DemandeDeSignalement, SignalementServi } from '@onboarding/contracts';

import { lireLaSession } from './auth';
import type { ReponseLue } from './profil';

/** `POST /bug-reports` — cahier §9.6/§10.12, ouvert a toute session. */
export async function signalerUnBug(
  demande: DemandeDeSignalement,
): Promise<ReponseLue<SignalementServi>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const reponse = await fetch(CHEMIN_SIGNALEMENT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
    },
    credentials: 'same-origin',
    body: JSON.stringify(demande),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: SignalementServi | null;
  try {
    corps = validerUnSignalement(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}
