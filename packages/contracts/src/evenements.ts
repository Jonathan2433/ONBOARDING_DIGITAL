/**
 * Le contrat de la lecture des evenements — LOT 8, `T2` (API) puis `T9` (ecran),
 * story `MVP-L08-US003`.
 *
 * LA LECTURE SEULE, COMME `liens.ts` AVANT SON `T10`
 *
 *   `T2` a `T8` ont servi cette route et six verbes d'ecriture sans poser de
 *   module de contrat : aucun ecran ne la consommait encore. `T9`, premier
 *   ecran consommateur, pose donc la LECTURE — meme partage que le catalogue
 *   des taches (LOT 7, `T4`/`T14`) et les liens internes (LOT 6, `T8`/`T10`) :
 *   une sous-etape qui sert une lecture pose son module quand un ecran en a
 *   besoin, celles qui servent une ecriture seule ne le font pas.
 *
 * LA FRONTIERE EST UNIQUE, ET CE MODULE NE LA RECALCULE PAS
 *
 *   `a_venir` et `passes` sont les DEUX classements du cahier §10.6 : la
 *   frontiere — `ends_at` compare a un instant unique — est tranchee par
 *   `lister_les_evenements` (`apps/api/app/events/lecture.py`), jamais ici. Le
 *   client envoie le classement voulu, l'API y repond ; rien ne reclasse un
 *   evenement cote navigateur.
 *
 * UN EVENEMENT ANNULE RESTE SERVI, ET C'EST STRUCTUREL
 *
 *   `etat` reste une CHAINE, jamais un type ferme : seuls `published` et
 *   `cancelled` sont servis par cette route (un brouillon ou une archive sont
 *   absents, filtres par l'API), mais fermer le type ici figerait un futur
 *   troisieme etat public que l'API pourrait un jour exposer — meme motif que
 *   `TYPES_DE_LIEN_NOMMES` dans `liens.ts`.
 *
 * LES DATES RESTENT DES CHAINES ISO, JAMAIS DES `Date`
 *
 *   Meme parti que `ficheArrivee.ts` : l'API sert de l'ISO 8601, et `new Date()`
 *   suivi d'un accesseur LOCAL (`getHours()`, `getMonth()`...) reinterprete la
 *   valeur dans le fuseau de la machine qui l'affiche. Le validateur rend donc
 *   des `string`, et l'ecran lit les segments qu'il lui faut directement dans
 *   la chaine (meme methode que `dateComplete` dans `PageProfil.tsx`).
 *
 * `pages` PEUT VALOIR ZERO, ET C'EST DIFFERENT DU CERCLE
 *
 *   `PageDuCercle.pages` vaut toujours au moins 1 : un cercle existe meme sans
 *   membre. Une entite SANS AUCUN evenement d'un classement donne a un total
 *   de zero, et `-(-0 // taille)` rend zero cote API — l'exiger a 1 ici
 *   refuserait une reponse parfaitement legitime. Le validateur confronte donc
 *   `pages` a `total` et `taille` par le calcul, jamais a une borne fixe.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';
import { TAILLES_DE_PAGE } from './trombinoscope.js';

/** Les deux onglets du cahier §10.6 — jamais des etats stockes, voir `lecture.py`. */
export const CLASSEMENTS_D_EVENEMENTS = ['a_venir', 'passes'] as const;

export type ClassementEvenement = (typeof CLASSEMENTS_D_EVENEMENTS)[number];

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_EVENEMENTS: string = endpoint('lectureDesEvenements').chemin;

/** Les codes exploitables. Le `422` vient de `classement`, `taille` et `page`. */
export const CODES_EVENEMENTS: readonly number[] =
  endpoint('lectureDesEvenements').codesExploitables;

/** Le chemin des evenements d'une entite, son segment encode. */
export function cheminEvenements(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_EVENEMENTS.replace('{code}', encodeURIComponent(code));
}

export interface EvenementDuClassement {
  readonly identifiant: string;
  readonly titre: string;
  readonly description: string | null;
  /** ISO 8601 — ne JAMAIS passer par `Date`, voir l'en-tete. */
  readonly commenceLe: string;
  /** ISO 8601 — idem. */
  readonly finitLe: string;
  readonly lieu: string | null;
  /** `published` ou `cancelled` — chaine volontairement ouverte, voir l'en-tete. */
  readonly etat: string;
  readonly annuleLe: string | null;
  readonly motifDAnnulation: string | null;
}

export interface PageDesEvenements {
  readonly classement: ClassementEvenement;
  readonly evenements: readonly EvenementDuClassement[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`evenements : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string, ou: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`evenements : ${ou}« ${champ} » n’est pas un entier`);
  }
  return brut;
}

function classementValide(valeur: unknown): ClassementEvenement {
  if (valeur !== 'a_venir' && valeur !== 'passes') {
    throw new TypeError(`evenements : classement « ${String(valeur)} » inconnu`);
  }
  return valeur;
}

function evenementDuClassement(brut: unknown, rang: number): EvenementDuClassement {
  if (!estObjet(brut)) {
    throw new TypeError(`evenements : evenements[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(brut, 'identifiant'),
    titre: exigerChaine(brut, 'titre'),
    description: chaineOuNul(brut, 'description'),
    commenceLe: exigerChaine(brut, 'commence_le'),
    finitLe: exigerChaine(brut, 'finit_le'),
    lieu: chaineOuNul(brut, 'lieu'),
    etat: exigerChaine(brut, 'etat'),
    annuleLe: chaineOuNul(brut, 'annule_le'),
    motifDAnnulation: chaineOuNul(brut, 'motif_d_annulation'),
  };
}

/**
 * Valider ce que `GET …/events` a rendu.
 *
 * **`pages` EST CONFRONTE A `total` ET `taille` PAR LE CALCUL**, jamais a une
 * borne fixe — voir l'en-tete, c'est different du cercle. Deux sources pour
 * une meme grandeur doivent coincider, §7.0 sixieme proposition.
 */
export function validerLaPageDesEvenements(valeur: unknown): PageDesEvenements {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }

  const brutEvenements = valeur['evenements'];
  if (!Array.isArray(brutEvenements)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun evenement » sur une reponse qui n'en disait rien.
    throw new TypeError('evenements : « evenements » n’est pas un tableau');
  }
  const evenements = brutEvenements.map((brut, rang) => evenementDuClassement(brut, rang));

  const taille = entier(valeur, 'taille', '');
  if (!TAILLES_DE_PAGE.includes(taille)) {
    throw new TypeError(`evenements : taille ${String(taille)} hors du §18.2`);
  }
  const total = entier(valeur, 'total', '');
  const pages = entier(valeur, 'pages', '');
  const attendu = total === 0 ? 0 : Math.ceil(total / taille);
  if (pages !== attendu) {
    throw new TypeError(
      `evenements : pages vaut ${String(pages)} pour un total de ${String(total)} ` +
        `a ${String(taille)} par page (${String(attendu)} attendu)`,
    );
  }

  return {
    classement: classementValide(valeur['classement']),
    evenements,
    page: entier(valeur, 'page', ''),
    taille,
    total,
    pages,
  };
}

// =============================================================================
//
//  LA GESTION DES EVENEMENTS — LOT 8, `T10`
//
//    Jusqu'ici, ce module ne portait que la LECTURE (`T2`, consommee par `T9`).
//    `T10`, l'ecran de gestion, AJOUTE la creation, la modification, la
//    publication, l'annulation, l'archivage, la restauration et le
//    rattachement des medias — meme partage que `liens.ts` a son `T10` : la
//    gestion vit dans le module de la ressource qu'elle gere, pas dans un
//    second fichier.
//
//    DEUX LECTURES DE PLUS, POSEES PAR `T10` COTE API — `GET …/events/gestion`
//    (tous les evenements, tous etats) et `GET …/events/{evenement}/gestion`
//    (un evenement et ses rattachements, avec sa `version`) — parce que la
//    lecture de `T2` ne sert que `published`/`cancelled` et ne porte jamais de
//    `version` : un ecran de gestion ne peut ni retrouver un brouillon ou un
//    archive, ni ecrire avec la concurrence optimiste du §18.4, sans elles.
//
// =============================================================================

export interface MediaDEvenement {
  readonly media: string;
  readonly role: string;
  readonly ordre: number;
}

function mediaDEvenement(brut: unknown, rang: number): MediaDEvenement {
  if (!estObjet(brut)) {
    throw new TypeError(`evenements : medias[${String(rang)}] non objet`);
  }
  return {
    media: exigerChaine(brut, 'media'),
    role: exigerChaine(brut, 'role'),
    ordre: entier(brut, 'ordre', `medias[${String(rang)}] `),
  };
}

function tableauDeChaines(source: Record<string, unknown>, champ: string): readonly string[] {
  const brut = source[champ];
  if (!Array.isArray(brut) || !brut.every((element) => typeof element === 'string')) {
    throw new TypeError(`evenements : « ${champ} » n’est pas un tableau de chaines`);
  }
  return brut;
}

// -----------------------------------------------------------------------------
//  La lecture pour la gestion — tous etats, `version` comprise.
// -----------------------------------------------------------------------------

export interface EvenementDeGestion {
  readonly identifiant: string;
  readonly titre: string;
  readonly etat: string;
  readonly commenceLe: string;
  readonly finitLe: string;
  readonly version: number;
}

export interface EvenementsPourGestion {
  readonly evenements: readonly EvenementDeGestion[];
}

function evenementDeGestion(brut: unknown, rang: number): EvenementDeGestion {
  if (!estObjet(brut)) {
    throw new TypeError(`evenements : evenements[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(brut, 'identifiant'),
    titre: exigerChaine(brut, 'titre'),
    etat: exigerChaine(brut, 'etat'),
    commenceLe: exigerChaine(brut, 'commence_le'),
    finitLe: exigerChaine(brut, 'finit_le'),
    version: entier(brut, 'version', `evenements[${String(rang)}] `),
  };
}

/** Valider ce que `GET …/events/gestion` a rendu — tous etats, aucune pagination. */
export function validerLesEvenementsPourGestion(valeur: unknown): EvenementsPourGestion {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  const brut = valeur['evenements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('evenements : « evenements » n’est pas un tableau');
  }
  return { evenements: brut.map((element, rang) => evenementDeGestion(element, rang)) };
}

export interface EvenementPourGestion {
  readonly identifiant: string;
  readonly titre: string;
  readonly description: string | null;
  readonly commenceLe: string;
  readonly finitLe: string;
  readonly lieu: string | null;
  readonly etat: string;
  readonly version: number;
  readonly annuleLe: string | null;
  readonly motifDAnnulation: string | null;
  readonly archiveLe: string | null;
  readonly cercles: readonly string[];
  readonly bureaux: readonly string[];
  readonly medias: readonly MediaDEvenement[];
}

/**
 * Valider ce que `GET …/events/{evenement}/gestion` a rendu.
 *
 * Porte `version`, `cercles`, `bureaux` et `medias` — ce que la lecture
 * publique de `T2` ne porte jamais — et peut valoir un BROUILLON ou un
 * ARCHIVE, ce qu'elle refuse.
 */
export function validerLEvenementPourGestion(valeur: unknown): EvenementPourGestion {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  const brutMedias = valeur['medias'];
  if (!Array.isArray(brutMedias)) {
    throw new TypeError('evenements : « medias » n’est pas un tableau');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    titre: exigerChaine(valeur, 'titre'),
    description: chaineOuNul(valeur, 'description'),
    commenceLe: exigerChaine(valeur, 'commence_le'),
    finitLe: exigerChaine(valeur, 'finit_le'),
    lieu: chaineOuNul(valeur, 'lieu'),
    etat: exigerChaine(valeur, 'etat'),
    version: entier(valeur, 'version', ''),
    annuleLe: chaineOuNul(valeur, 'annule_le'),
    motifDAnnulation: chaineOuNul(valeur, 'motif_d_annulation'),
    archiveLe: chaineOuNul(valeur, 'archive_le'),
    cercles: tableauDeChaines(valeur, 'cercles'),
    bureaux: tableauDeChaines(valeur, 'bureaux'),
    medias: brutMedias.map((element, rang) => mediaDEvenement(element, rang)),
  };
}

// -----------------------------------------------------------------------------
//  Ce que chaque ecriture REND — une forme par verbe, comme l'API les distingue.
// -----------------------------------------------------------------------------

export type PorteeDeCreationEvenement = 'entite' | 'cercle' | 'bureau' | 'consultants';

function porteeDeCreationValide(valeur: unknown): PorteeDeCreationEvenement {
  if (
    valeur !== 'entite' &&
    valeur !== 'cercle' &&
    valeur !== 'bureau' &&
    valeur !== 'consultants'
  ) {
    throw new TypeError(`evenements : portee « ${String(valeur)} » inconnue`);
  }
  return valeur;
}

export interface EvenementCree {
  readonly identifiant: string;
  readonly titre: string;
  readonly description: string | null;
  readonly commenceLe: string;
  readonly finitLe: string;
  readonly lieu: string | null;
  readonly etat: string;
  readonly version: number;
  readonly portee: PorteeDeCreationEvenement;
}

export function validerLEvenementCree(valeur: unknown): EvenementCree {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    titre: exigerChaine(valeur, 'titre'),
    description: chaineOuNul(valeur, 'description'),
    commenceLe: exigerChaine(valeur, 'commence_le'),
    finitLe: exigerChaine(valeur, 'finit_le'),
    lieu: chaineOuNul(valeur, 'lieu'),
    etat: exigerChaine(valeur, 'etat'),
    version: entier(valeur, 'version', ''),
    portee: porteeDeCreationValide(valeur['portee']),
  };
}

/** Ce que modifier et publier rendent tous deux — meme forme, deux verbes. */
export interface EvenementEcrit {
  readonly identifiant: string;
  readonly titre: string;
  readonly description: string | null;
  readonly commenceLe: string;
  readonly finitLe: string;
  readonly lieu: string | null;
  readonly etat: string;
  readonly version: number;
}

export function validerLEvenementEcrit(valeur: unknown): EvenementEcrit {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    titre: exigerChaine(valeur, 'titre'),
    description: chaineOuNul(valeur, 'description'),
    commenceLe: exigerChaine(valeur, 'commence_le'),
    finitLe: exigerChaine(valeur, 'finit_le'),
    lieu: chaineOuNul(valeur, 'lieu'),
    etat: exigerChaine(valeur, 'etat'),
    version: entier(valeur, 'version', ''),
  };
}

export interface EvenementAnnule {
  readonly version: number;
  readonly etat: string;
  readonly annuleLe: string;
  readonly motifDAnnulation: string | null;
}

export function validerLEvenementAnnule(valeur: unknown): EvenementAnnule {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  return {
    version: entier(valeur, 'version', ''),
    etat: exigerChaine(valeur, 'etat'),
    annuleLe: exigerChaine(valeur, 'annule_le'),
    motifDAnnulation: chaineOuNul(valeur, 'motif_d_annulation'),
  };
}

export interface EvenementArchive {
  readonly version: number;
  readonly etat: string;
  readonly archiveLe: string;
}

export function validerLEvenementArchive(valeur: unknown): EvenementArchive {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  return {
    version: entier(valeur, 'version', ''),
    etat: exigerChaine(valeur, 'etat'),
    archiveLe: exigerChaine(valeur, 'archive_le'),
  };
}

/** L'evenement revient TOUJOURS en `draft` — restaurer n'est pas publier. */
export interface EvenementRestaure {
  readonly version: number;
  readonly etat: string;
}

export function validerLEvenementRestaure(valeur: unknown): EvenementRestaure {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  return {
    version: entier(valeur, 'version', ''),
    etat: exigerChaine(valeur, 'etat'),
  };
}

export interface MediasDEvenement {
  readonly version: number;
  readonly medias: readonly MediaDEvenement[];
}

export function validerLesMediasDEvenement(valeur: unknown): MediasDEvenement {
  if (!estObjet(valeur)) {
    throw new TypeError('evenements : charge utile non objet');
  }
  const brut = valeur['medias'];
  if (!Array.isArray(brut)) {
    throw new TypeError('evenements : « medias » n’est pas un tableau');
  }
  return {
    version: entier(valeur, 'version', ''),
    medias: brut.map((element, rang) => mediaDEvenement(element, rang)),
  };
}

// -----------------------------------------------------------------------------
//  Ce qu'un ecran ENVOIE — `snake_case` voulu, c'est ce que l'API attend (voir
//  la note de `gestionDuContenu.ts`). Jamais validees : elles ne reviennent pas
//  du reseau.
// -----------------------------------------------------------------------------

export interface DemandeDeCreationDEvenement {
  readonly titre: string;
  readonly description?: string;
  readonly commence_le: string;
  readonly finit_le: string;
  readonly lieu?: string;
  readonly portee: PorteeDeCreationEvenement;
  readonly cercle?: string;
  readonly bureau?: string;
}

/**
 * `cercles`/`bureaux` ABSENTS (pas envoyes) signifie « ne pas toucher cette
 * dimension » ; un tableau VIDE la vide — meme distinction qu'a l'API, jamais
 * recalculee ici.
 */
export interface DemandeDeModificationDEvenement {
  readonly titre: string;
  readonly description?: string;
  readonly commence_le: string;
  readonly finit_le: string;
  readonly lieu?: string;
  readonly version: number;
  readonly cercles?: readonly string[];
  readonly bureaux?: readonly string[];
}

export interface DemandeDePublicationDEvenement {
  readonly version: number;
}

export interface DemandeDAnnulationDEvenement {
  readonly version: number;
  readonly motif?: string;
}

/** Archiver ou restaurer — aucun motif, meme forme pour les deux verbes. */
export interface DemandeDeTransitionDEvenement {
  readonly version: number;
}

export interface MediaSoumis {
  readonly media: string;
  readonly role: string;
}

/** La liste REMPLACE la liste complete, dans l'ordre fourni — `[]` la vide. */
export interface DemandeDeGestionDesMediasDEvenement {
  readonly version: number;
  readonly medias: readonly MediaSoumis[];
}

// -----------------------------------------------------------------------------
//  Chemins et codes de chaque verbe — un gabarit par cle de manifeste,
//  `DEC-492`.
// -----------------------------------------------------------------------------

export const GABARIT_CHEMIN_MODIFICATION_D_EVENEMENT: string = endpoint(
  'modificationDUnEvenement',
).chemin;
export const GABARIT_CHEMIN_PUBLICATION_D_EVENEMENT: string =
  endpoint('publicationDUnEvenement').chemin;
export const GABARIT_CHEMIN_ANNULATION_D_EVENEMENT: string =
  endpoint('annulationDUnEvenement').chemin;
export const GABARIT_CHEMIN_ARCHIVAGE_D_EVENEMENT: string =
  endpoint('archivageDUnEvenement').chemin;
export const GABARIT_CHEMIN_RESTAURATION_D_EVENEMENT: string = endpoint(
  'restaurationDUnEvenement',
).chemin;
export const GABARIT_CHEMIN_MEDIAS_D_EVENEMENT: string = endpoint(
  'gestionDesMediasDUnEvenement',
).chemin;
export const GABARIT_CHEMIN_EVENEMENTS_POUR_GESTION: string = endpoint(
  'listeDesEvenementsPourGestion',
).chemin;
export const GABARIT_CHEMIN_EVENEMENT_POUR_GESTION: string = endpoint(
  'lectureDUnEvenementPourGestion',
).chemin;

export const CODES_CREATION_D_EVENEMENT: readonly number[] =
  endpoint('creationDUnEvenement').codesExploitables;
export const CODES_MODIFICATION_D_EVENEMENT: readonly number[] = endpoint(
  'modificationDUnEvenement',
).codesExploitables;
export const CODES_PUBLICATION_D_EVENEMENT: readonly number[] =
  endpoint('publicationDUnEvenement').codesExploitables;
export const CODES_ANNULATION_D_EVENEMENT: readonly number[] =
  endpoint('annulationDUnEvenement').codesExploitables;
export const CODES_ARCHIVAGE_D_EVENEMENT: readonly number[] =
  endpoint('archivageDUnEvenement').codesExploitables;
export const CODES_RESTAURATION_D_EVENEMENT: readonly number[] = endpoint(
  'restaurationDUnEvenement',
).codesExploitables;
export const CODES_MEDIAS_D_EVENEMENT: readonly number[] = endpoint(
  'gestionDesMediasDUnEvenement',
).codesExploitables;
export const CODES_EVENEMENTS_POUR_GESTION: readonly number[] = endpoint(
  'listeDesEvenementsPourGestion',
).codesExploitables;
export const CODES_EVENEMENT_POUR_GESTION: readonly number[] = endpoint(
  'lectureDUnEvenementPourGestion',
).codesExploitables;

function cheminAvecEvenement(gabarit: string, code: string, evenement: string): string {
  if (code === '' || evenement === '') {
    throw new TypeError('code d’entite ou identifiant d’evenement vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{evenement}', encodeURIComponent(evenement));
}

export function cheminEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_MODIFICATION_D_EVENEMENT, code, evenement);
}

export function cheminPublicationDEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_PUBLICATION_D_EVENEMENT, code, evenement);
}

export function cheminAnnulationDEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_ANNULATION_D_EVENEMENT, code, evenement);
}

export function cheminArchivageDEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_ARCHIVAGE_D_EVENEMENT, code, evenement);
}

export function cheminRestaurationDEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_RESTAURATION_D_EVENEMENT, code, evenement);
}

export function cheminMediasDEvenement(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_MEDIAS_D_EVENEMENT, code, evenement);
}

export function cheminEvenementsPourGestion(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_EVENEMENTS_POUR_GESTION.replace('{code}', encodeURIComponent(code));
}

export function cheminEvenementPourGestion(code: string, evenement: string): string {
  return cheminAvecEvenement(GABARIT_CHEMIN_EVENEMENT_POUR_GESTION, code, evenement);
}

// -----------------------------------------------------------------------------
//  Les roles — LUS DU MANIFESTE, jamais redeclares. `rolesGestionDesEvenements`
//  (DSM/ESM/BOOST/OFFICE/ADM-E/SUPER) est plus LARGE que
//  `rolesRestaurationDUnEvenement` (ESM/ADM-E/SUPER) : DSM/BOOST/OFFICE
//  creent, modifient, publient, annulent, archivent et gerent des medias,
//  mais ne RESTAURENT jamais — `ARB-DROIT-003`. Les fusionner proposerait un
//  bouton « Restaurer » que l'API refuserait (§7.21 de la passation).
//
//  **LE FRONTEND N'EST PAS L'AUTORITE.** Un role present dans
//  `rolesGestionDesEvenements` peut recevoir un 403 malgre un bouton visible
//  — le DSM createur seul (pas le DSM NOMME par `event_dsm_scope`) en est
//  l'exemple vivant, et aucune cle de manifeste ne peut l'exprimer. Cette
//  liste sert a ne pas proposer un bouton a qui n'a AUCUN role sur les
//  evenements, rien de plus.
// -----------------------------------------------------------------------------

export const ROLES_GESTION_DES_EVENEMENTS: readonly string[] =
  CONTRAT_API.rolesGestionDesEvenements;
export const ROLES_RESTAURATION_D_UN_EVENEMENT: readonly string[] =
  CONTRAT_API.rolesRestaurationDUnEvenement;

/** L'appelant peut-il se voir PROPOSER de gerer les evenements ? Ne decide rien. */
export function peutGererLesEvenements(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_GESTION_DES_EVENEMENTS.includes(role));
}

/** L'appelant peut-il se voir PROPOSER de restaurer un evenement archive ? */
export function peutRestaurerUnEvenement(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_RESTAURATION_D_UN_EVENEMENT.includes(role));
}
