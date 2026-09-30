/**
 * Le client de l'onboarding du nouvel arrivant — LOT 7, `T13`.
 *
 * TROIS LECTURES/ECRITURES, TOUTES BORNEES A « SOI » PAR L'API
 *
 *   La fiche d'arrivee (`T2`/`T3`), le parcours (`T7`) et les deux actions sur
 *   une tache (`T8`) partagent la MEME garde matrice §8.1 : `Soi` uniquement
 *   pour un nouvel arrivant sans role d'entite. Cet ecran n'appelle donc
 *   JAMAIS ces routes pour une appartenance autre que la SIENNE — resolue par
 *   `permissions.appartenance`, `T13` (voir `CadreApplicatif.tsx`).
 *
 * LES ECRITURES SUIVENT LE MEME MONTAGE QUE `gestionDuContenu.ts` (LOT 6, `T10`)
 *
 *   Jeton anti-CSRF lu au dernier instant, cle d'idempotence PAR TENTATIVE.
 *   `completerLaFiche`/`validerEtPublierLaFiche` recoivent une `version` FOURNIE
 *   par l'ecran, jamais par une relecture — la concurrence optimiste du §18.4.
 *   `terminerUneTache`/`annulerUneTache` n'ont pas de corps a valider cote API
 *   (aucun `Body` declare dans `routes.py`) : un objet vide suffit.
 *
 * AUCUNE FENETRE DE CINQ MINUTES N'EST CALCULEE ICI, ET C'EST DELIBERE
 *
 *   L'API est l'autorite finale (regle 5) : le bouton d'annulation est propose
 *   pour toute tache `completed`, et c'est le `409 delai_d_annulation_depasse`
 *   de l'API — jamais une horloge cote client — qui referme la fenetre. Un
 *   calcul client dupliquerait la regle du §8.3 et divergerait a la prochaine
 *   horloge desynchronisee (meme classe que `T8-4`/§7.33).
 */
import {
  cheminAnnulationDeTache,
  cheminCompletionDeTache,
  cheminDuParcours,
  cheminFicheArrivee,
  cheminValidationFicheArrivee,
  type CompletionDeFiche,
  type DemandeDeCompletionDeFiche,
  type DemandeDeValidationDeFiche,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type FicheArrivee,
  type Parcours,
  type TacheDuParcours,
  type ValidationDeFiche,
  validerLaCompletion,
  validerLaFicheArrivee,
  validerLaValidation,
  validerLeParcours,
  validerUneTacheDuParcours,
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
    //  Un corps illisible n'est pas un echec reseau : le statut est conserve.
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

async function ecrire<T>(
  chemin: string,
  methode: 'PATCH' | 'POST',
  corpsEnvoye: unknown,
  valider: (valeur: unknown) => T,
): Promise<ReponseLue<T>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const reponse = await fetch(chemin, {
    method: methode,
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      //  Une cle PAR TENTATIVE : rejouer la meme apres un echec ferait croire
      //  au serveur qu'il s'agit du meme geste (idempotence, §18.4).
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

/** `GET …/arrival-profile` — la fiche d'arrivee de l'appelant. */
export function lireLaFicheArrivee(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<FicheArrivee>> {
  return lire(cheminFicheArrivee(code, appartenance), validerLaFicheArrivee, signal);
}

/** `PATCH …/arrival-profile` — completer (brouillon) ou corriger (publiee). */
export function completerLaFiche(
  code: string,
  appartenance: string,
  demande: DemandeDeCompletionDeFiche,
): Promise<ReponseLue<CompletionDeFiche>> {
  return ecrire(cheminFicheArrivee(code, appartenance), 'PATCH', demande, validerLaCompletion);
}

/** `POST …/arrival-profile/validation` — valide ET publie dans le meme geste (§7.1). */
export function validerEtPublierLaFiche(
  code: string,
  appartenance: string,
  demande: DemandeDeValidationDeFiche,
): Promise<ReponseLue<ValidationDeFiche>> {
  return ecrire(
    cheminValidationFicheArrivee(code, appartenance),
    'POST',
    demande,
    validerLaValidation,
  );
}

/** `GET …/onboarding-parcours` — le parcours de l'appelant, `instance` `null` si aucun. */
export function lireLeParcours(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<Parcours>> {
  return lire(cheminDuParcours(code, appartenance), validerLeParcours, signal);
}

/** `POST …/taches/{tache}/completion` — marquer une tache comme terminee. */
export function terminerUneTache(
  code: string,
  appartenance: string,
  tache: string,
): Promise<ReponseLue<TacheDuParcours>> {
  return ecrire(
    cheminCompletionDeTache(code, appartenance, tache),
    'POST',
    {},
    validerUneTacheDuParcours,
  );
}

/** `POST …/taches/{tache}/annulation` — annuler une completion dans les cinq minutes. */
export function annulerUneTache(
  code: string,
  appartenance: string,
  tache: string,
): Promise<ReponseLue<TacheDuParcours>> {
  return ecrire(
    cheminAnnulationDeTache(code, appartenance, tache),
    'POST',
    {},
    validerUneTacheDuParcours,
  );
}
