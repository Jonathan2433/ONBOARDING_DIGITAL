/**
 * Le client de la gestion des liens internes — LOT 6, `T10`, `MVP-L06-US005`.
 *
 * L'ACCUEIL EST `liens.ts` DE `T9` ; CE FICHIER EST SON PENDANT ECRITURE
 *
 *   Meme montage que `gestionDuContenu.ts` : jeton anti-CSRF lu au dernier
 *   instant, cle d'idempotence par tentative, `version` fournie par l'ecran
 *   pour la modification (§18.4). La creation n'en a pas besoin — elle ne peut
 *   pas entrer en conflit avec un etat qu'elle n'a pas encore lu.
 *
 * `lireLesLiensPourGestion` SERT LES DEUX ETATS, LA OU L'ACCUEIL NE SERT QUE
 * L'ACTIF
 *
 *   Sans cette route, desactiver un lien serait un aller sans retour : l'ecran
 *   d'edition doit pouvoir retrouver un lien INACTIF pour le reactiver.
 */
import {
  cheminCreationDeLien,
  cheminGestionDesLiens,
  cheminModificationDeLien,
  cheminOrdreDesLiens,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type DemandeDeCreationDeLien,
  type DemandeDeModificationDeLien,
  type DemandeDOrdreDesLiens,
  type LienInterne,
  type LiensInternes,
  validerLesLiensInternes,
  validerUnLienInterneServi,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';
import type { ReponseLue } from './profil';

/** `GET …/liens/gestion` — tous les liens, actifs ET inactifs. */
export async function lireLesLiensPourGestion(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<LiensInternes>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminGestionDesLiens(code), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: LiensInternes | null;
  try {
    corps = validerLesLiensInternes(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

async function ecrire<T>(
  chemin: string,
  methode: 'POST' | 'PUT',
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

/** `POST …/liens` — creer un lien. Ajoute EN QUEUE, jamais a un rang choisi. */
export async function creerUnLien(
  code: string,
  demande: DemandeDeCreationDeLien,
): Promise<ReponseLue<LienInterne>> {
  return ecrire(cheminCreationDeLien(code), 'POST', demande, validerUnLienInterneServi);
}

/** `PUT …/liens/{lien}` — modifier un lien. `version` obligatoire, §18.4. */
export async function modifierUnLien(
  code: string,
  lien: string,
  demande: DemandeDeModificationDeLien,
): Promise<ReponseLue<LienInterne>> {
  return ecrire(cheminModificationDeLien(code, lien), 'PUT', demande, validerUnLienInterneServi);
}

/**
 * `PUT …/liens/ordre` — reordonner. La liste COMPLETE des identifiants NON
 * archives, dans l'ordre voulu — c'est ce qui sert de verrou de concurrence,
 * l'API exigeant que chaque lien non archive y figure exactement une fois.
 */
export async function reordonnerLesLiens(
  code: string,
  demande: DemandeDOrdreDesLiens,
): Promise<ReponseLue<LiensInternes>> {
  return ecrire(cheminOrdreDesLiens(code), 'PUT', demande, validerLesLiensInternes);
}
