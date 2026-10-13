/**
 * Le client de l'écriture back-office sur un collaborateur — LOT 9, `T14`.
 *
 * TROIS GESTES, LE MEME MONTAGE QUE `administration.ts` ET `organisation.ts`
 *
 *   Jeton anti-CSRF lu au dernier instant via `GET /auth/session`, clé
 *   d'idempotence PAR TENTATIVE — rejouer la même après un échec ferait
 *   croire au serveur qu'il s'agit du même geste (§18.4).
 */
import {
  type CatalogueDesMetiers,
  cheminApercuDuTransfertEnMasse,
  cheminCatalogueDesMetiers,
  cheminChangementDEntite,
  cheminCreationDeCollaborateur,
  cheminTransfertEnMasse,
  type ChangementDEntite,
  type CollaborateurCree,
  type DemandeDeChangementDEntite,
  type DemandeDeCreationDeCollaborateur,
  type DemandeDeTransfertEnMasse,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type ReponseDeTransfertEnMasse,
  validerLeCatalogueDesMetiers,
  validerLeChangementDEntite,
  validerLeCollaborateurCree,
  validerLeTransfertEnMasse,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';
import type { ReponseLue } from './profil';

async function ecrire<T>(
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

/** `GET …/job-catalog` — les métiers actifs d'une entité, `T14`. */
export async function lireLeCatalogueDesMetiers(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<CatalogueDesMetiers>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminCatalogueDesMetiers(code), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: CatalogueDesMetiers | null;
  try {
    corps = validerLeCatalogueDesMetiers(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** `POST …/people` — créer un collaborateur et son appartenance, `T2`. */
export function creerUnCollaborateur(
  code: string,
  demande: DemandeDeCreationDeCollaborateur,
): Promise<ReponseLue<CollaborateurCree>> {
  return ecrire(cheminCreationDeCollaborateur(code), demande, validerLeCollaborateurCree);
}

/** `POST …/people/{appartenance}/changement-d-entite` — `T3`, ferme `US002`. */
export function changerDEntite(
  code: string,
  appartenance: string,
  demande: DemandeDeChangementDEntite,
): Promise<ReponseLue<ChangementDEntite>> {
  return ecrire(cheminChangementDEntite(code, appartenance), demande, validerLeChangementDEntite);
}

/** `POST …/people/transferts-en-masse/apercu` — `T11`, impact RÉEL dans un savepoint annulé. */
export function previsualiserLeTransfertEnMasse(
  code: string,
  demande: DemandeDeTransfertEnMasse,
): Promise<ReponseLue<ReponseDeTransfertEnMasse>> {
  return ecrire(cheminApercuDuTransfertEnMasse(code), demande, validerLeTransfertEnMasse);
}

/** `POST …/people/transferts-en-masse` — `T11`, exécution réelle, au plus 100 éléments. */
export function executerLeTransfertEnMasse(
  code: string,
  demande: DemandeDeTransfertEnMasse,
): Promise<ReponseLue<ReponseDeTransfertEnMasse>> {
  return ecrire(cheminTransfertEnMasse(code), demande, validerLeTransfertEnMasse);
}
