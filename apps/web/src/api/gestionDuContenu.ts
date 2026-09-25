/**
 * Le client de l'edition d'un contenu — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * LES DEUX LECTURES QUI N'EXISTAIENT NULLE PART AVANT `T10`
 *
 *   `lireLesPagesDeGestion` et `lireUnePagePourGestion` appellent les deux
 *   routes que `T10` a du poser cote API : sans elles, un editeur qui recharge
 *   son ecran en cours de redaction n'avait aucun moyen de retrouver sa page ni
 *   sa `version`. Voir `apps/api/app/content/pages.py`.
 *
 * LES ECRITURES SUIVENT LE MEME MONTAGE QUE `cycleDeVie.ts` DU LOT 5
 *
 *   Jeton anti-CSRF lu au dernier instant, cle d'idempotence PAR TENTATIVE,
 *   `version` fournie par l'ecran — jamais par une relecture, qui ferait
 *   disparaitre la concurrence optimiste du §18.4.
 */
import {
  cheminArchivageDuContenu,
  cheminCreationDePage,
  cheminEcritureDuContenu,
  cheminPageDeGestion,
  cheminPagesDeGestion,
  cheminPublication,
  cheminRestaurationDuContenu,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type ContenuEcrit,
  type DemandeDeCreationDePage,
  type DemandeDEcritureDuContenu,
  type PageCreee,
  type PageDeContenuPourEdition,
  type ReponseDesPagesDeGestion,
  type TransitionDeContenu,
  validerLaPageCreee,
  validerLaPageDeContenuPourEdition,
  validerLaTransitionDeContenu,
  validerLEcritureDuContenu,
  validerLesPagesDeGestion,
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

/** `GET …/pages/gestion` — toutes les pages de l'entite, tous etats confondus. */
export async function lireLesPagesDeGestion(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDesPagesDeGestion>> {
  return lire(cheminPagesDeGestion(code), validerLesPagesDeGestion, signal);
}

/** `GET …/pages/{page}/gestion` — une page et ses blocs, tous etats, avec sa `version`. */
export async function lireUnePagePourGestion(
  code: string,
  page: string,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDeContenuPourEdition>> {
  return lire(cheminPageDeGestion(code, page), validerLaPageDeContenuPourEdition, signal);
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
      //  Une cle PAR TENTATIVE : rejouer la meme apres un echec ferait croire au
      //  serveur qu'il s'agit du meme geste (idempotence, §18.4).
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

/** `POST …/pages` — creer une page, toujours en BROUILLON (§13, « Creer un contenu general »). */
export async function creerUnePage(
  code: string,
  demande: DemandeDeCreationDePage,
): Promise<ReponseLue<PageCreee>> {
  return ecrire(cheminCreationDePage(code), 'POST', demande, validerLaPageCreee);
}

/**
 * `PUT …/pages/{page}/contenu` — remplacer le titre et la LISTE des blocs.
 *
 * **LA LISTE REMPLACE LA LISTE**, cote API (modele §2.4) : les blocs absents
 * sont archives. L'ecran doit donc toujours envoyer la liste COMPLETE qu'il
 * veut voir persister, jamais une liste partielle.
 */
export async function ecrireLeContenu(
  code: string,
  page: string,
  demande: DemandeDEcritureDuContenu,
): Promise<ReponseLue<ContenuEcrit>> {
  return ecrire(cheminEcritureDuContenu(code, page), 'PUT', demande, validerLEcritureDuContenu);
}

/** Les trois transitions du §13 — aucune ne prend d'autre champ que `version`. */
export type ActionSurLeContenu = 'publication' | 'archivage' | 'restauration';

const CHEMINS_DE_TRANSITION: Readonly<
  Record<ActionSurLeContenu, (c: string, p: string) => string>
> = {
  publication: cheminPublication,
  archivage: cheminArchivageDuContenu,
  restauration: cheminRestaurationDuContenu,
};

/** Publier, archiver ou restaurer une page — `POST …/{action}`. */
export async function agirSurLeContenu(
  action: ActionSurLeContenu,
  code: string,
  page: string,
  version: number,
): Promise<ReponseLue<TransitionDeContenu>> {
  return ecrire(
    CHEMINS_DE_TRANSITION[action](code, page),
    'POST',
    { version },
    validerLaTransitionDeContenu,
  );
}
