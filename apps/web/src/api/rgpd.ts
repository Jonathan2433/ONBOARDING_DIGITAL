/**
 * Le client du suivi d'une demande de droit RGPD — LOT 10, `T14`/`T15`, `US008`.
 */
import {
  cheminClotureRGPD,
  cheminDemandesRGPD,
  cheminHistoriqueRGPD,
  cheminUneDemandeRGPD,
  cheminVerificationIdentiteRGPD,
  CHEMIN_DEMANDES_RGPD,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type DemandeDeClotureRGPD,
  type DemandeDeReceptionRGPD,
  type DemandeDeVerificationIdentiteRGPD,
  type LigneDeDemandeRGPD,
  type ReponseDesDemandesRGPD,
  type ReponseDeLHistoriqueRGPD,
  type ReponseDeTransitionRGPD,
  type TypeDeDemandeRGPD,
  validerLaTransitionRGPD,
  validerLesDemandesRGPD,
  validerLHistoriqueRGPD,
  validerUneDemandeRGPD,
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

export function listerLesDemandesRGPD(
  page: number,
  taille: number,
  etat?: string,
  typeDemande?: TypeDeDemandeRGPD,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesDemandesRGPD>> {
  return lire(cheminDemandesRGPD(page, taille, etat, typeDemande), validerLesDemandesRGPD, signal);
}

export function lireUneDemandeRGPD(
  demande: string,
  signal?: AbortSignal,
): Promise<ReponseLue<LigneDeDemandeRGPD>> {
  return lire(cheminUneDemandeRGPD(demande), validerUneDemandeRGPD, signal);
}

export function lireLHistoriqueDUneDemandeRGPD(
  demande: string,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDeLHistoriqueRGPD>> {
  return lire(cheminHistoriqueRGPD(demande), validerLHistoriqueRGPD, signal);
}

export function receptionnerUneDemandeRGPD(
  demande: DemandeDeReceptionRGPD,
): Promise<ReponseLue<LigneDeDemandeRGPD>> {
  return ecrire(CHEMIN_DEMANDES_RGPD, demande, validerUneDemandeRGPD);
}

export function verifierLIdentiteDUneDemandeRGPD(
  demande: string,
  corps: DemandeDeVerificationIdentiteRGPD,
): Promise<ReponseLue<ReponseDeTransitionRGPD>> {
  return ecrire(cheminVerificationIdentiteRGPD(demande), corps, validerLaTransitionRGPD);
}

export function cloturerUneDemandeRGPD(
  demande: string,
  corps: DemandeDeClotureRGPD,
): Promise<ReponseLue<ReponseDeTransitionRGPD>> {
  return ecrire(cheminClotureRGPD(demande), corps, validerLaTransitionRGPD);
}
