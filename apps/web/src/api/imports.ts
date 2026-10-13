/**
 * Le client de l'import CSV, du dépôt au rapport — LOT 9, `T14`.
 *
 * LE DÉPÔT EST LA PREMIÈRE REQUÊTE MULTIPART DU FRONTEND
 *
 *   Zéro occurrence de `FormData` ailleurs dans `apps/web/src` avant ce
 *   fichier — mesuré. `Content-Type` n'est PAS fixé à la main : le navigateur
 *   pose `multipart/form-data; boundary=…` lui-même, et l'écraser casserait
 *   l'analyse du corps côté API.
 *
 * LE PARCOURS EST SÉQUENTIEL, PAS UN HISTORIQUE PARCOURABLE
 *
 *   Voir l'en-tête d'`imports.ts` du paquet de contrat : aucune route ne
 *   liste les lots d'une entité. L'identifiant du lot déposé est donc
 *   conservé par l'ÉCRAN (état React), jamais redérivé d'une liste.
 */
import {
  cheminDecision,
  cheminDepotDImport,
  cheminLancement,
  cheminListeDesClients,
  cheminRapport,
  cheminRejeu,
  type DecisionEnregistree,
  type DemandeDeDecision,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type LotDepose,
  type RapportDImport,
  type ReponseDeLancement,
  type ReponseDeRejeu,
  type ReponseDesClients,
  validerLaDecision,
  validerLeLancement,
  validerLeLotDepose,
  validerLeRapport,
  validerLeRejeu,
  validerLesClients,
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

async function ecrireJson<T>(
  chemin: string,
  corpsEnvoye: unknown,
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
    body: JSON.stringify(corpsEnvoye),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/**
 * `POST …/imports` — déposer un CSV, analyse sans écriture métier, `T6`/`T7`.
 *
 * **UN SEUL CHAMP DE FORMULAIRE, `fichier`** — mesuré sur
 * `apps/api/app/imports/routes.py`. Pas de `Content-Type` manuel : voir l'en-tête.
 */
export async function deposerUnImport(code: string, fichier: File): Promise<ReponseLue<LotDepose>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const corpsEnvoye = new FormData();
  corpsEnvoye.append('fichier', fichier);

  const reponse = await fetch(cheminDepotDImport(code), {
    method: 'POST',
    headers: {
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    body: corpsEnvoye,
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: LotDepose | null;
  try {
    corps = validerLeLotDepose(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** `GET …/clients` — le catalogue proposé au rapprochement, `T8`, ferme `ECART-060`. */
export function listerLesClients(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesClients>> {
  return lire(cheminListeDesClients(code), validerLesClients, signal);
}

/** `POST …/imports/{lot}/rows/{ligne}/decisions` — `T8`. */
export function enregistrerUneDecision(
  code: string,
  lot: string,
  ligne: string,
  demande: DemandeDeDecision,
): Promise<ReponseLue<DecisionEnregistree>> {
  return ecrireJson(cheminDecision(code, lot, ligne), demande, validerLaDecision);
}

/** `POST …/imports/{lot}/lancement` — l'import transactionnel réel, `T9`. */
export function lancerLImport(code: string, lot: string): Promise<ReponseLue<ReponseDeLancement>> {
  return ecrireJson(cheminLancement(code, lot), {}, validerLeLancement);
}

/** `POST …/imports/{lot}/rows/{ligne}/rejeu` — rejoue la ligne TELLE QUELLE, `T10`. */
export function rejouerUneLigne(
  code: string,
  lot: string,
  ligne: string,
): Promise<ReponseLue<ReponseDeRejeu>> {
  return ecrireJson(cheminRejeu(code, lot, ligne), {}, validerLeRejeu);
}

/** `GET …/imports/{lot}/rapport` — réconciliation fraîche, paginée, `T10`. */
export function consulterLeRapport(
  code: string,
  lot: string,
  page?: number,
  taille?: number,
  signal?: AbortSignal,
): Promise<ReponseLue<RapportDImport>> {
  return lire(cheminRapport(code, lot, page, taille), validerLeRapport, signal);
}
