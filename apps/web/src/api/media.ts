/**
 * Le client du depot et de l'autorisation d'une photo de profil — LOT 11, `T2`.
 *
 * MEME MONTAGE QUE `imports.ts` (LOT 9) POUR LE MULTIPART
 *
 *   `deposerUnePhoto` est la DEUXIEME requete multipart du frontend, apres le
 *   depot d'un CSV — meme discipline : `Content-Type` n'est jamais fixe a la
 *   main, le navigateur pose `multipart/form-data; boundary=…` lui-meme.
 */
import {
  cheminAutorisationPhoto,
  cheminDepotDePhoto,
  cheminDroitsDePhoto,
  cheminEtatDUnMedia,
  cheminRetraitAutorisationPhoto,
  type Autorisation,
  type DepotDePhoto,
  type DroitsDePhoto,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type EtatDUnMedia,
  type Retrait,
  validerLAutorisation,
  validerLeDepotDePhoto,
  validerLeRetrait,
  validerLesDroitsDePhoto,
  validerLEtatDUnMedia,
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
 * `POST …/photo` — deposer (ou remplacer) une photo, `US004`.
 *
 * Rend `pending` : le contenu reel est verifie et la miniature generee de
 * facon ASYNCHRONE — `lireLEtatDUnMedia` pour suivre ce traitement.
 */
export async function deposerUnePhoto(
  code: string,
  appartenance: string,
  fichier: File,
): Promise<ReponseLue<DepotDePhoto>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const corpsEnvoye = new FormData();
  corpsEnvoye.append('fichier', fichier);

  const reponse = await fetch(cheminDepotDePhoto(code, appartenance), {
    method: 'POST',
    headers: {
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    body: corpsEnvoye,
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: DepotDePhoto | null;
  try {
    corps = validerLeDepotDePhoto(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** `GET …/photo/droits` — ce que l'appelant peut proposer sur CETTE appartenance. */
export function lireLesDroitsDePhoto(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<DroitsDePhoto>> {
  return lire(cheminDroitsDePhoto(code, appartenance), validerLesDroitsDePhoto, signal);
}

/** `GET …/media/{media}/etat` — suivre l'avancement d'un depot en cours. */
export function lireLEtatDUnMedia(
  code: string,
  media: string,
  signal?: AbortSignal,
): Promise<ReponseLue<EtatDUnMedia>> {
  return lire(cheminEtatDUnMedia(code, media), validerLEtatDUnMedia, signal);
}

/** `POST …/photo/autorisation` — accorder l'autorisation d'affichage, `US005`. */
export function accorderLAutorisationDePhoto(
  code: string,
  appartenance: string,
  mediaAssetId: string,
): Promise<ReponseLue<Autorisation>> {
  return ecrireJson(
    cheminAutorisationPhoto(code, appartenance),
    { media_asset_id: mediaAssetId },
    validerLAutorisation,
  );
}

/** `POST …/photo/autorisation/retrait` — retirer toute autorisation active, `US005`. */
export function retirerLAutorisationDePhoto(
  code: string,
  appartenance: string,
): Promise<ReponseLue<Retrait>> {
  return ecrireJson(cheminRetraitAutorisationPhoto(code, appartenance), {}, validerLeRetrait);
}
