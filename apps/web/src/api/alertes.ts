/**
 * Le client du cycle des alertes opérationnelles — LOT 10, `T13`/`T15`, `US007`.
 *
 * SIX ROUTES, TOUTES PLATES : AUCUN CODE D'ENTITÉ
 *
 *   `operational_alert` est une ressource globale (modèle §21.2) — voir
 *   l'en-tête d'`alertes.ts` au paquet de contrat.
 */
import {
  cheminAcquittementDAlerte,
  cheminAlertes,
  cheminCommentairesDAlerte,
  cheminResolutionDAlerte,
  cheminUneAlerte,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type DemandeDAcquittementDAlerte,
  type DemandeDeCommentaireDAlerte,
  type DemandeDeResolutionDAlerte,
  type EtatDAlerte,
  type LigneDAlerte,
  type ReponseDeCommentaireAjoute,
  type ReponseDesAlertes,
  type ReponseDesCommentairesDAlerte,
  type ReponseDeTransitionDAlerte,
  validerLeCommentaireAjoute,
  validerLesAlertes,
  validerLesCommentairesDAlerte,
  validerLaTransitionDAlerte,
  validerUneAlerte,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';
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

async function ecrire<T>(
  chemin: string,
  corps: object,
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
    body: JSON.stringify(corps),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);
  let valide: T | null;
  try {
    valide = valider(await reponse.json());
  } catch {
    valide = null;
  }
  return { statut: reponse.status, corps: valide, correlation };
}

export function listerLesAlertes(
  page: number,
  taille: number,
  etat?: EtatDAlerte,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesAlertes>> {
  return lire(cheminAlertes(page, taille, etat), validerLesAlertes, signal);
}

export function lireUneAlerte(
  alerte: string,
  signal?: AbortSignal,
): Promise<ReponseLue<LigneDAlerte>> {
  return lire(cheminUneAlerte(alerte), validerUneAlerte, signal);
}

export function lireLesCommentairesDUneAlerte(
  alerte: string,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesCommentairesDAlerte>> {
  return lire(cheminCommentairesDAlerte(alerte), validerLesCommentairesDAlerte, signal);
}

export function acquitterUneAlerte(
  alerte: string,
  demande: DemandeDAcquittementDAlerte,
): Promise<ReponseLue<ReponseDeTransitionDAlerte>> {
  return ecrire(cheminAcquittementDAlerte(alerte), demande, validerLaTransitionDAlerte);
}

export function commenterUneAlerte(
  alerte: string,
  demande: DemandeDeCommentaireDAlerte,
): Promise<ReponseLue<ReponseDeCommentaireAjoute>> {
  return ecrire(cheminCommentairesDAlerte(alerte), demande, validerLeCommentaireAjoute);
}

export function resoudreUneAlerte(
  alerte: string,
  demande: DemandeDeResolutionDAlerte,
): Promise<ReponseLue<ReponseDeTransitionDAlerte>> {
  return ecrire(cheminResolutionDAlerte(alerte), demande, validerLaTransitionDAlerte);
}
