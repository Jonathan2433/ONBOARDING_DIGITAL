/**
 * Le client des evenements — LOT 8. La lecture (`T9`, `MVP-L08-US003` 2/2) et
 * la gestion (`T10`, `MVP-L08-US004`).
 *
 * MEME MONTAGE QUE `administration.ts` ET `gestionDuContenu.ts` : `lire<T>`
 * pour les GET, `ecrire<T>` pour POST/PUT — jeton anti-CSRF lu au dernier
 * instant via `lireLaSession()`, cle d'idempotence PAR TENTATIVE. `ReponseLue<T>`
 * est REPRISE de `profil.ts`, pas redeclaree une troisieme fois.
 *
 * `classement`, `page` ET `taille` SONT TOUJOURS ENVOYES EXPLICITEMENT
 *
 *   Meme raisonnement que `lireLeCercle` : l'ecran connait deja sa valeur
 *   courante — l'onglet selectionne, la page affichee — et l'envoyer
 *   explicitement laisse la reponse la confirmer plutot que de dependre d'un
 *   defaut cote API que l'ecran ne verrait jamais changer. `classement` est de
 *   toute facon obligatoire : la route repond `422` sans lui.
 *
 * AUCUNE PORTEE N'EST CALCULEE ICI
 *
 *   Un DSM ne voit que ses propres consultants, un Booster que son cercle :
 *   c'est l'API qui le decide (`resoudre_le_perimetre_de_l_evenement`), jamais
 *   ce client — regle 5, l'API est l'autorite finale. Un bouton visible ici
 *   peut recevoir un 403 ; cet ecran le rapporte tel quel.
 */
import {
  type ClassementEvenement,
  cheminAnnulationDEvenement,
  cheminArchivageDEvenement,
  cheminEvenement,
  cheminEvenements,
  cheminEvenementPourGestion,
  cheminEvenementsPourGestion,
  cheminMediasDEvenement,
  cheminPublicationDEvenement,
  cheminRestaurationDEvenement,
  type DemandeDAnnulationDEvenement,
  type DemandeDeCreationDEvenement,
  type DemandeDeGestionDesMediasDEvenement,
  type DemandeDeModificationDEvenement,
  type DemandeDePublicationDEvenement,
  type DemandeDeTransitionDEvenement,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type EvenementAnnule,
  type EvenementArchive,
  type EvenementCree,
  type EvenementEcrit,
  type EvenementPourGestion,
  type EvenementRestaure,
  type EvenementsPourGestion,
  type MediasDEvenement,
  type PageDesEvenements,
  validerLaPageDesEvenements,
  validerLesEvenementsPourGestion,
  validerLesMediasDEvenement,
  validerLEvenementAnnule,
  validerLEvenementArchive,
  validerLEvenementCree,
  validerLEvenementEcrit,
  validerLEvenementPourGestion,
  validerLEvenementRestaure,
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
  //  L'en-tete AVANT le corps : le corps peut lever, et la correlation est
  //  justement ce qu'on veut montrer quand quelque chose casse.
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

/** Une page d'evenements — `GET /entities/{code}/events`, les deux onglets du §10.6. */
export function lireLesEvenements(
  code: string,
  classement: ClassementEvenement,
  page: number,
  taille: number,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDesEvenements>> {
  const parametres = new URLSearchParams({
    classement,
    page: String(page),
    taille: String(taille),
  });
  return lire(
    `${cheminEvenements(code)}?${parametres.toString()}`,
    validerLaPageDesEvenements,
    signal,
  );
}

/** `GET …/events/gestion` — tous les evenements de l'entite, tous etats. */
export function lireLesEvenementsPourGestion(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<EvenementsPourGestion>> {
  return lire(cheminEvenementsPourGestion(code), validerLesEvenementsPourGestion, signal);
}

/** `GET …/events/{evenement}/gestion` — un evenement et ses rattachements, avec sa `version`. */
export function lireUnEvenementPourGestion(
  code: string,
  evenement: string,
  signal?: AbortSignal,
): Promise<ReponseLue<EvenementPourGestion>> {
  return lire(cheminEvenementPourGestion(code, evenement), validerLEvenementPourGestion, signal);
}

/** `POST …/events` — matrice §11 « Creer », en BROUILLON. */
export function creerUnEvenement(
  code: string,
  demande: DemandeDeCreationDEvenement,
): Promise<ReponseLue<EvenementCree>> {
  return ecrire(cheminEvenements(code), 'POST', demande, validerLEvenementCree);
}

/** `PUT …/events/{evenement}` — matrice §11 « Modifier ». */
export function modifierUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDeModificationDEvenement,
): Promise<ReponseLue<EvenementEcrit>> {
  return ecrire(cheminEvenement(code, evenement), 'PUT', demande, validerLEvenementEcrit);
}

/** `POST …/events/{evenement}/publication` — matrice §11 « Publier », immediate. */
export function publierUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDePublicationDEvenement,
): Promise<ReponseLue<EvenementEcrit>> {
  return ecrire(
    cheminPublicationDEvenement(code, evenement),
    'POST',
    demande,
    validerLEvenementEcrit,
  );
}

/** `POST …/events/{evenement}/annulation` — matrice §11 « Annuler ». */
export function annulerUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDAnnulationDEvenement,
): Promise<ReponseLue<EvenementAnnule>> {
  return ecrire(
    cheminAnnulationDEvenement(code, evenement),
    'POST',
    demande,
    validerLEvenementAnnule,
  );
}

/** `POST …/events/{evenement}/archivage` — matrice §11 « Archiver ». */
export function archiverUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDeTransitionDEvenement,
): Promise<ReponseLue<EvenementArchive>> {
  return ecrire(
    cheminArchivageDEvenement(code, evenement),
    'POST',
    demande,
    validerLEvenementArchive,
  );
}

/** `POST …/events/{evenement}/restauration` — matrice §11 « Restaurer », revient en `draft`. */
export function restaurerUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDeTransitionDEvenement,
): Promise<ReponseLue<EvenementRestaure>> {
  return ecrire(
    cheminRestaurationDEvenement(code, evenement),
    'POST',
    demande,
    validerLEvenementRestaure,
  );
}

/** `PUT …/events/{evenement}/medias` — la liste REMPLACE la liste complete. */
export function gererLesMediasDUnEvenement(
  code: string,
  evenement: string,
  demande: DemandeDeGestionDesMediasDEvenement,
): Promise<ReponseLue<MediasDEvenement>> {
  return ecrire(
    cheminMediasDEvenement(code, evenement),
    'PUT',
    demande,
    validerLesMediasDEvenement,
  );
}
