/**
 * Le client du cycle de vie d'un profil — LOT 5, `T11`, story `MVP-L05-US007`.
 *
 * DEUX ECRITURES, ET CE SONT LES PREMIERES DE CE PROJET HORS AUTHENTIFICATION
 *
 *   Elles exigent donc ce que `T7` a etabli pour les ecritures metier : le
 *   **jeton anti-CSRF**, obtenu dans le corps de `GET …/auth/session`, renvoye
 *   dans `EN_TETE_JETON_CSRF`. Sans lui l'API rend `403`, et c'est voulu
 *   (`DEC-531`).
 *
 * LA CLE D'IDEMPOTENCE EST FOURNIE, ET ELLE N'EST PAS DECORATIVE
 *
 *   Le §18.4 la rend optionnelle ; un **double clic** sur un bouton d'archivage
 *   la rend utile. Fournie, une meme cle rejouee ne produit qu'un effet -- et
 *   c'est exactement le mode de defaillance d'un bouton qui agit.
 *
 *   Elle est engendree par `crypto.randomUUID()`, present dans tout navigateur
 *   qui sert cette application en HTTPS. **Une cle PAR TENTATIVE, jamais par
 *   montage du composant** : rejouer la meme cle apres un echec ferait croire au
 *   serveur qu'il s'agit du meme geste.
 *
 * LA VERSION VOYAGE DANS LE CORPS, ET ELLE EST OBLIGATOIRE
 *
 *   §18.4, concurrence optimiste : l'API compare la version envoyee a celle
 *   qu'elle porte, et rend `409` si elles different -- quelqu'un d'autre a
 *   modifie le profil entre la lecture et le geste.
 *
 *   **ELLE VIENT DE LA FICHE QUE L'ECRAN AFFICHE**, et non d'une relecture :
 *   relire juste avant d'agir ferait disparaitre la protection, puisqu'on
 *   enverrait alors la version d'un etat qu'on n'a pas montre a l'utilisateur.
 *
 * LE JETON EST LU JUSTE AVANT L'ACTION, JAMAIS GARDE
 *
 *   Une session revoquee entre le chargement de la page et le clic rendrait un
 *   jeton perime, et le refus serait attribue a l'action plutot qu'a la session.
 *   Le lire a l'instant du geste rend le `401` exact.
 */
import {
  cheminArchivage,
  cheminFicheArchivee,
  cheminRestauration,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type FicheDuProfil,
  type ResultatDuCycleDeVie,
  validerLaFiche,
  validerLeResultat,
} from '@onboarding/contracts';

import { lireLaSession } from './auth';
import type { ReponseLue } from './profil';

/** L'action demandee. Deux valeurs, et le type interdit d'en inventer une troisieme. */
export type ActionDuCycleDeVie = 'archivage' | 'restauration';

const CHEMINS: Readonly<Record<ActionDuCycleDeVie, (c: string, a: string) => string>> = {
  archivage: cheminArchivage,
  restauration: cheminRestauration,
};

/**
 * Archiver ou restaurer — `POST …/{action}`.
 *
 * **LE `401` DU JETON EST RENDU TEL QUEL, SANS APPELER L'ACTION.** Si la session
 * n'est plus valable, l'action ne partirait de toute facon pas : la tenter
 * produirait un second `401`, et le journal en porterait deux pour un geste.
 */
export async function agirSurLeCycleDeVie(
  action: ActionDuCycleDeVie,
  code: string,
  appartenance: string,
  version: number,
): Promise<ReponseLue<ResultatDuCycleDeVie>> {
  const session = await lireLaSession();
  if (session.statut !== 200 || session.corps === null) {
    return { statut: session.statut, corps: null, correlation: null };
  }

  const reponse = await fetch(CHEMINS[action](code, appartenance), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_JETON_CSRF]: session.corps.jeton_csrf,
      //  Une cle PAR TENTATIVE : rejouer la meme apres un echec ferait croire au
      //  serveur qu'il s'agit du meme geste.
      [EN_TETE_CLE_IDEMPOTENCE]: globalThis.crypto.randomUUID(),
    },
    credentials: 'same-origin',
    //  **`version` EST OBLIGATOIRE, ET L'OUBLIER REND `422`.** Mon premier
    //  client envoyait `{}` : les tests le passaient, parce qu'un `fetch`
    //  bouchonne rend 200 quel que soit le corps. Seule la pile reelle l'a dit.
    //  Defaut `T11-6`.
    body: JSON.stringify({ version }),
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: ResultatDuCycleDeVie | null;
  try {
    corps = validerLeResultat(await reponse.json(), action);
  } catch {
    //  Un corps illisible n'est pas un echec reseau : le statut est conserve, et
    //  c'est lui que l'ecran lit pour distinguer 403, 404 et 409.
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/**
 * La fiche d'un profil ARCHIVE — `GET …/fiche-archivee`.
 *
 * **UNE SECONDE ROUTE POUR UNE SECONDE POPULATION**, et c'est le parti de `T8` :
 * le §6.1 donne « consulter un profil **actif** » aux huit roles et « consulter
 * un profil **archive** » a trois. Elargir la premiere aurait confondu deux
 * droits que le document separe (§7.41).
 */
export async function lireLaFicheArchivee(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<FicheDuProfil>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminFicheArchivee(code, appartenance), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: FicheDuProfil | null;
  try {
    corps = validerLaFiche(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}
