/**
 * Le client des écrans d'administration de l'onboarding — LOT 7, `T14`.
 *
 * TROIS DOMAINES, UN SEUL FICHIER — LE CATALOGUE, LES MODÈLES, LE SUIVI
 *
 *   Les cinq routes d'écriture des modèles (créer un modèle, une version,
 *   poser ses tâches, publier, archiver, restaurer) existaient depuis `T5`/
 *   `T6` sans jamais avoir été appelées par un écran. La lecture du catalogue
 *   (`T4`) et le suivi (`T12`) non plus. `T14` en est le premier consommateur
 *   pour les trois, et la liste des modèles (`GET …/templates`) est une route
 *   NOUVELLE, posée en construisant cet écran — voir l'en-tête de
 *   `app/onboarding/gabarits.py`.
 *
 * MÊME MONTAGE QUE `onboarding.ts` (`T13`) ET `gestionDuContenu.ts` (LOT 6, `T10`)
 *
 *   Jeton anti-CSRF lu au dernier instant, clé d'idempotence PAR TENTATIVE.
 *   `PUT …/tasks` accepte la liste ENTIÈRE, qui remplace la précédente —
 *   jamais un ajout ou une suppression ligne à ligne.
 *
 * AUCUNE PORTÉE N'EST CALCULÉE ICI
 *
 *   Un DSM ne voit que ses propres modèles, un Booster ceux de son cercle :
 *   c'est l'API qui le décide (`peut_gerer_un_modele_de_cette_portee`), jamais
 *   ce client — règle 5, l'API est l'autorité finale.
 */
import {
  cheminArchivageDeVersion,
  cheminCatalogueDeTaches,
  cheminModelesOnboarding,
  cheminPublicationDeVersion,
  cheminRestaurationDeVersion,
  cheminSuiviOnboarding,
  cheminTachesDeVersion,
  cheminVersionsDeModele,
  type CatalogueDeTaches,
  type DemandeDeModeleOnboarding,
  type DemandeDesTachesDeVersion,
  type DemandeDeTacheDeReference,
  type DemandeDeVersionDeModele,
  EN_TETE_CLE_IDEMPOTENCE,
  EN_TETE_CORRELATION,
  EN_TETE_JETON_CSRF,
  type ModeleOnboardingCree,
  type PageDesModelesOnboarding,
  type PageDeSuiviOnboarding,
  type TachesDeVersion,
  type TacheDeReference,
  validerLArchivageDeVersion,
  validerLaPublicationDeVersion,
  validerLaRestaurationDeVersion,
  validerLeCatalogueDeTaches,
  validerLesModelesOnboarding,
  validerLesTachesDeVersion,
  validerLeSuiviOnboarding,
  validerUneTacheDeReference,
  validerUneVersionCreee,
  validerUnModeleCree,
  type VersionArchivee,
  type VersionDeModeleOnboarding,
  type VersionPubliee,
  type VersionRestauree,
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

/** `GET …/task-references` — le catalogue reutilisable dans cette entite. */
export function lireLeCatalogueDeTaches(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<CatalogueDeTaches>> {
  return lire(cheminCatalogueDeTaches(code), validerLeCatalogueDeTaches, signal);
}

/** `POST …/task-references` — matrice §9, ferme `ECART-013`. */
export function creerUneTacheDeReference(
  code: string,
  demande: DemandeDeTacheDeReference,
): Promise<ReponseLue<TacheDeReference>> {
  return ecrire(cheminCatalogueDeTaches(code), 'POST', demande, validerUneTacheDeReference);
}

/** `GET …/templates` — les modeles GERES par l'appelant, avec leurs versions. */
export function lireLesModelesOnboarding(
  code: string,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDesModelesOnboarding>> {
  return lire(cheminModelesOnboarding(code), validerLesModelesOnboarding, signal);
}

/** `POST …/templates` — le conteneur seul, matrice §9 « Creer un modele ». */
export function creerUnModeleOnboarding(
  code: string,
  demande: DemandeDeModeleOnboarding,
): Promise<ReponseLue<ModeleOnboardingCree>> {
  return ecrire(cheminModelesOnboarding(code), 'POST', demande, validerUnModeleCree);
}

/** `POST …/templates/{modele}/versions` — une nouvelle version brouillon. */
export function creerUneVersionDeModele(
  code: string,
  modele: string,
  demande: DemandeDeVersionDeModele,
): Promise<ReponseLue<VersionDeModeleOnboarding>> {
  return ecrire(cheminVersionsDeModele(code, modele), 'POST', demande, validerUneVersionCreee);
}

/** `PUT …/versions/{version}/tasks` — la liste ENTIERE, qui remplace la precedente. */
export function definirLesTachesDeVersion(
  code: string,
  modele: string,
  version: string,
  demande: DemandeDesTachesDeVersion,
): Promise<ReponseLue<TachesDeVersion>> {
  return ecrire(
    cheminTachesDeVersion(code, modele, version),
    'PUT',
    demande,
    validerLesTachesDeVersion,
  );
}

/** `POST …/versions/{version}/publication` — `draft` devient `published`. */
export function publierUneVersionDeModele(
  code: string,
  modele: string,
  version: string,
): Promise<ReponseLue<VersionPubliee>> {
  return ecrire(
    cheminPublicationDeVersion(code, modele, version),
    'POST',
    {},
    validerLaPublicationDeVersion,
  );
}

/** `POST …/versions/{version}/archivage` — `published` devient `retired`. */
export function archiverUneVersionDeModele(
  code: string,
  modele: string,
  version: string,
): Promise<ReponseLue<VersionArchivee>> {
  return ecrire(
    cheminArchivageDeVersion(code, modele, version),
    'POST',
    {},
    validerLArchivageDeVersion,
  );
}

/** `POST …/versions/{version}/restauration` — `retired` redevient `published`. */
export function restaurerUneVersionDeModele(
  code: string,
  modele: string,
  version: string,
): Promise<ReponseLue<VersionRestauree>> {
  return ecrire(
    cheminRestaurationDeVersion(code, modele, version),
    'POST',
    {},
    validerLaRestaurationDeVersion,
  );
}

/** `GET …/onboarding-suivi/taches-en-retard` — pagination du cahier §18.2. */
export function lireLeSuiviOnboarding(
  code: string,
  page: number,
  taille: number,
  signal?: AbortSignal,
): Promise<ReponseLue<PageDeSuiviOnboarding>> {
  const parametres = new URLSearchParams({ page: String(page), taille: String(taille) });
  return lire(
    `${cheminSuiviOnboarding(code)}?${parametres.toString()}`,
    validerLeSuiviOnboarding,
    signal,
  );
}
