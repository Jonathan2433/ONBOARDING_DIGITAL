/**
 * Le client du traitement des signalements — LOT 10, `T12`/`T15`, `US006`.
 *
 * MÊME MONTAGE QUE `organisation.ts` POUR L'ÉCRITURE
 *
 *   Jeton anti-CSRF lu au dernier instant via `GET /auth/session`, clé
 *   d'idempotence PAR TENTATIVE — rejouer la même après un échec ferait
 *   croire au serveur qu'il s'agit du même geste.
 */
import {
  cheminChangementDEtatSignalement,
  cheminHistoriqueSignalement,
  cheminSignalements,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type DemandeDeChangementDEtatSignalement,
  type EtatDeSignalement,
  type ReponseDeChangementDEtatSignalement,
  type ReponseDesSignalements,
  type ReponseDeLHistoriqueSignalement,
  validerLeChangementDEtatSignalement,
  validerLesSignalements,
  validerLHistoriqueSignalement,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';
import type { ReponseLue } from './profil';

export async function listerLesSignalements(
  code: string,
  page: number,
  taille: number,
  etat?: EtatDeSignalement,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesSignalements>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminSignalements(code, page, taille, etat), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);
  let corps: ReponseDesSignalements | null;
  try {
    corps = validerLesSignalements(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

export async function lireLHistoriqueDUnSignalement(
  code: string,
  signalement: string,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDeLHistoriqueSignalement>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminHistoriqueSignalement(code, signalement), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);
  let corps: ReponseDeLHistoriqueSignalement | null;
  try {
    corps = validerLHistoriqueSignalement(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

export async function changerLEtatDUnSignalement(
  code: string,
  signalement: string,
  demande: DemandeDeChangementDEtatSignalement,
): Promise<ReponseLue<ReponseDeChangementDEtatSignalement>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }
  const reponse = await fetch(cheminChangementDEtatSignalement(code, signalement), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    body: JSON.stringify(demande),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);
  let corps: ReponseDeChangementDEtatSignalement | null;
  try {
    corps = validerLeChangementDEtatSignalement(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}
