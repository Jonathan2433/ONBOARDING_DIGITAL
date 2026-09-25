/**
 * Le contrat de l'ecriture editoriale — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * CE MODULE PORTE CE QUE `T6`, `T7` ET `T10` LUI-MEME ONT AJOUTE
 *
 *   `contenus.ts` reste T5/lecture seule (le PUBLIE, sans `version`). Celui-ci
 *   porte la creation, l'ecriture des blocs, le cycle de vie, et les DEUX routes
 *   de gestion que `T10` a du poser — `pages/gestion` et `pages/{page}/gestion` —
 *   parce qu'aucune route existante ne servait un BROUILLON avec sa `version`.
 *   Voir `apps/api/app/content/pages.py`, section « LA LECTURE POUR L'EDITEUR ».
 *
 * DEUX GRILLES DE ROLES, ET UNE TROISIEME DEJA DANS LE MANIFESTE DEPUIS `T7`
 *
 *   `rolesCreationDeContenu` (§13, une seule ligne, sans BOOST ni OFFICE) et
 *   `rolesEcritureEditoriale` (strictement plus large : elle y ajoute les deux
 *   roles de portee locale). Confondre les deux accorderait a tort un droit de
 *   creation a un Booster, ou lui retirerait celui de modifier son cercle.
 *
 *   `rolesRestaurationDUnContenu` existait deja dans le manifeste depuis `T7`,
 *   en anticipation d'un ecran qui n'existait pas encore — c'est celui-ci.
 *
 * LE FRONTEND N'EST PAS L'AUTORITE
 *
 *   Comme partout ailleurs : ces listes servent a ne pas PROPOSER une action que
 *   l'API refuserait. La portee LOCALE — le Booster de SON cercle, pas de tous
 *   les cercles — n'est resolue que par l'API, et aucune cle de manifeste ne
 *   peut l'exprimer : un role suffisant peut donc recevoir un 403
 *   `contenu_hors_perimetre` malgre un bouton visible, et l'ecran doit le lire.
 */

import { validerUnBlocDeContenu, type BlocDeContenu } from './contenus.js';
import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

// ---------------------------------------------------------------------------
//  Roles — lus du manifeste, jamais reecrits (`DEC-492`)
// ---------------------------------------------------------------------------

export const ROLES_CREATION_DE_CONTENU: readonly string[] = CONTRAT_API.rolesCreationDeContenu;
export const ROLES_ECRITURE_EDITORIALE: readonly string[] = CONTRAT_API.rolesEcritureEditoriale;
export const ROLES_RESTAURATION_D_UN_CONTENU: readonly string[] =
  CONTRAT_API.rolesRestaurationDUnContenu;

/** L'appelant peut-il se voir PROPOSER de creer une page ? Ne decide rien. */
export function peutCreerUnContenu(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_CREATION_DE_CONTENU.includes(role));
}

/** L'appelant peut-il se voir PROPOSER de modifier/publier/archiver une page ? */
export function peutEditerUnContenu(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_ECRITURE_EDITORIALE.includes(role));
}

/** L'appelant peut-il se voir PROPOSER de restaurer une page archivee ? */
export function peutRestaurerUnContenu(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_RESTAURATION_D_UN_CONTENU.includes(role));
}

// ---------------------------------------------------------------------------
//  Chemins — lus du manifeste
// ---------------------------------------------------------------------------

export const GABARIT_CHEMIN_CREATION_DE_PAGE: string = endpoint('creationDUnePageDeContenu').chemin;
export const GABARIT_CHEMIN_ECRITURE_DU_CONTENU: string = endpoint(
  'ecritureDuContenuDUnePage',
).chemin;
export const GABARIT_CHEMIN_PUBLICATION: string = endpoint('publicationDUnePageDeContenu').chemin;
export const GABARIT_CHEMIN_ARCHIVAGE_DU_CONTENU: string = endpoint(
  'archivageDUnePageDeContenu',
).chemin;
export const GABARIT_CHEMIN_RESTAURATION_DU_CONTENU: string = endpoint(
  'restaurationDUnePageDeContenu',
).chemin;
export const GABARIT_CHEMIN_PAGES_DE_GESTION: string = endpoint('pagesDeLEntitePourGestion').chemin;
export const GABARIT_CHEMIN_PAGE_DE_GESTION: string = endpoint('pageDeContenuPourGestion').chemin;

export const CODES_CREATION_DE_PAGE: readonly number[] = endpoint(
  'creationDUnePageDeContenu',
).codesExploitables;
export const CODES_ECRITURE_DU_CONTENU: readonly number[] = endpoint(
  'ecritureDuContenuDUnePage',
).codesExploitables;
export const CODES_PUBLICATION: readonly number[] = endpoint(
  'publicationDUnePageDeContenu',
).codesExploitables;
export const CODES_ARCHIVAGE_DU_CONTENU: readonly number[] = endpoint(
  'archivageDUnePageDeContenu',
).codesExploitables;
export const CODES_RESTAURATION_DU_CONTENU: readonly number[] = endpoint(
  'restaurationDUnePageDeContenu',
).codesExploitables;
export const CODES_PAGES_DE_GESTION: readonly number[] = endpoint(
  'pagesDeLEntitePourGestion',
).codesExploitables;
export const CODES_PAGE_DE_GESTION: readonly number[] = endpoint(
  'pageDeContenuPourGestion',
).codesExploitables;

function cheminAvecCode(gabarit: string, code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return gabarit.replace('{code}', encodeURIComponent(code));
}

function cheminAvecPage(gabarit: string, code: string, page: string): string {
  if (code === '' || page === '') {
    throw new TypeError('code d’entite ou identifiant de page vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{page}', encodeURIComponent(page));
}

export function cheminCreationDePage(code: string): string {
  return cheminAvecCode(GABARIT_CHEMIN_CREATION_DE_PAGE, code);
}
export function cheminEcritureDuContenu(code: string, page: string): string {
  return cheminAvecPage(GABARIT_CHEMIN_ECRITURE_DU_CONTENU, code, page);
}
export function cheminPublication(code: string, page: string): string {
  return cheminAvecPage(GABARIT_CHEMIN_PUBLICATION, code, page);
}
export function cheminArchivageDuContenu(code: string, page: string): string {
  return cheminAvecPage(GABARIT_CHEMIN_ARCHIVAGE_DU_CONTENU, code, page);
}
export function cheminRestaurationDuContenu(code: string, page: string): string {
  return cheminAvecPage(GABARIT_CHEMIN_RESTAURATION_DU_CONTENU, code, page);
}
export function cheminPagesDeGestion(code: string): string {
  return cheminAvecCode(GABARIT_CHEMIN_PAGES_DE_GESTION, code);
}
export function cheminPageDeGestion(code: string, page: string): string {
  return cheminAvecPage(GABARIT_CHEMIN_PAGE_DE_GESTION, code, page);
}

// ---------------------------------------------------------------------------
//  Formes de REPONSE, et leurs validateurs
// ---------------------------------------------------------------------------

export interface PageDeGestion {
  readonly identifiant: string;
  readonly typeDePage: string;
  readonly titre: string;
  readonly slug: string;
  readonly etat: string;
  readonly version: number;
  readonly circleId: string | null;
  readonly officeId: string | null;
}

export interface ReponseDesPagesDeGestion {
  readonly pages: readonly PageDeGestion[];
}

export interface PageDeContenuPourEdition {
  readonly identifiant: string;
  readonly typeDePage: string;
  readonly titre: string;
  readonly slug: string;
  readonly etat: string;
  readonly version: number;
  readonly publieeLe: string | null;
  readonly blocs: readonly BlocDeContenu[];
  readonly nombreDeBlocs: number;
}

export interface PageCreee {
  readonly identifiant: string;
  readonly typeDePage: string;
  readonly titre: string;
  readonly slug: string;
  readonly etat: string;
  readonly version: number;
}

export interface ContenuEcrit {
  readonly version: number;
  readonly blocs: readonly BlocDeContenu[];
  readonly nombreDeBlocs: number;
  readonly blocsArchives: number;
}

export interface TransitionDeContenu {
  readonly version: number;
  readonly etat: string;
  readonly publieeLe: string | null;
  /** Present seulement sur la reponse d'archivage. */
  readonly archiveeLe: string | null;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    throw new TypeError(`« ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entierOuLeve(source: Record<string, unknown>, champ: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`« ${champ} » n’est pas un entier`);
  }
  return brut;
}

function idPageOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null || brut === undefined) {
    return null;
  }
  if (typeof brut !== 'string') {
    throw new TypeError(`« ${champ} » ni chaine ni null`);
  }
  return brut;
}

function validerUnePageDeGestion(brut: unknown): PageDeGestion {
  if (!estObjet(brut)) {
    throw new TypeError('page de gestion : non objet');
  }
  return {
    identifiant: exigerChaine(brut, 'identifiant'),
    typeDePage: exigerChaine(brut, 'type_de_page'),
    titre: exigerChaine(brut, 'titre'),
    slug: exigerChaine(brut, 'slug'),
    etat: exigerChaine(brut, 'etat'),
    version: entierOuLeve(brut, 'version'),
    circleId: idPageOuNul(brut, 'circle_id'),
    officeId: idPageOuNul(brut, 'office_id'),
  };
}

/** Valider ce que `GET …/pages/gestion` a rendu. */
export function validerLesPagesDeGestion(valeur: unknown): ReponseDesPagesDeGestion {
  if (!estObjet(valeur)) {
    throw new TypeError('pages de gestion : charge utile non objet');
  }
  const brutPages = valeur['pages'];
  if (!Array.isArray(brutPages)) {
    throw new TypeError('pages de gestion : « pages » n’est pas un tableau');
  }
  return { pages: brutPages.map((p) => validerUnePageDeGestion(p)) };
}

/** Valider ce que `GET …/pages/{page}/gestion` a rendu. */
export function validerLaPageDeContenuPourEdition(valeur: unknown): PageDeContenuPourEdition {
  if (!estObjet(valeur)) {
    throw new TypeError('page pour edition : charge utile non objet');
  }
  const brutBlocs = valeur['blocs'];
  if (!Array.isArray(brutBlocs)) {
    throw new TypeError('page pour edition : « blocs » n’est pas un tableau');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    typeDePage: exigerChaine(valeur, 'type_de_page'),
    titre: exigerChaine(valeur, 'titre'),
    slug: exigerChaine(valeur, 'slug'),
    etat: exigerChaine(valeur, 'etat'),
    version: entierOuLeve(valeur, 'version'),
    publieeLe: chaineOuNul(valeur, 'publiee_le'),
    blocs: brutBlocs.map((b, rang) => validerUnBlocDeContenu(b, rang)),
    nombreDeBlocs: entierOuLeve(valeur, 'nombre_de_blocs'),
  };
}

/** Valider ce que `POST …/pages` a rendu. */
export function validerLaPageCreee(valeur: unknown): PageCreee {
  if (!estObjet(valeur)) {
    throw new TypeError('page creee : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    typeDePage: exigerChaine(valeur, 'type_de_page'),
    titre: exigerChaine(valeur, 'titre'),
    slug: exigerChaine(valeur, 'slug'),
    etat: exigerChaine(valeur, 'etat'),
    version: entierOuLeve(valeur, 'version'),
  };
}

/** Valider ce que `PUT …/contenu` a rendu. */
export function validerLEcritureDuContenu(valeur: unknown): ContenuEcrit {
  if (!estObjet(valeur)) {
    throw new TypeError('ecriture du contenu : charge utile non objet');
  }
  const brutBlocs = valeur['blocs'];
  if (!Array.isArray(brutBlocs)) {
    throw new TypeError('ecriture du contenu : « blocs » n’est pas un tableau');
  }
  return {
    version: entierOuLeve(valeur, 'version'),
    blocs: brutBlocs.map((b, rang) => validerUnBlocDeContenu(b, rang)),
    nombreDeBlocs: entierOuLeve(valeur, 'nombre_de_blocs'),
    blocsArchives: entierOuLeve(valeur, 'blocs_archives'),
  };
}

/**
 * Valider ce qu'une transition (publication, archivage, restauration) a rendu.
 *
 * **UNE FORME UNIQUE POUR LES TROIS**, `archiveeLe` etant `null` hors
 * archivage : les trois reponses de l'API partagent `version`/`etat`/
 * `publiee_le`, et seule celle de l'archivage ajoute `archivee_le`. Un
 * validateur par action recopierait deux fois la meme lecture (§7.27).
 */
export function validerLaTransitionDeContenu(valeur: unknown): TransitionDeContenu {
  if (!estObjet(valeur)) {
    throw new TypeError('transition de contenu : charge utile non objet');
  }
  return {
    version: entierOuLeve(valeur, 'version'),
    etat: exigerChaine(valeur, 'etat'),
    publieeLe: 'publiee_le' in valeur ? chaineOuNul(valeur, 'publiee_le') : null,
    archiveeLe: 'archivee_le' in valeur ? chaineOuNul(valeur, 'archivee_le') : null,
  };
}

// ---------------------------------------------------------------------------
//  Formes de DEMANDE — ce que l'ecran ENVOIE, jamais validees puisqu'elles ne
//  reviennent pas du reseau. Les clefs `snake_case` sont voulues : c'est ce que
//  l'API attend, et une conversion ici serait un troisieme endroit ou la
//  frontiere pourrait diverger (`DEC-466`).
// ---------------------------------------------------------------------------

export interface BlocSoumis {
  readonly type_de_bloc: string;
  readonly contenu: Readonly<Record<string, unknown>>;
}

export interface DemandeDeCreationDePage {
  readonly type_de_page: string;
  readonly titre: string;
  readonly slug: string;
  readonly cercle?: string;
  readonly bureau?: string;
}

export interface DemandeDEcritureDuContenu {
  readonly version: number;
  readonly titre: string;
  readonly blocs: readonly BlocSoumis[];
}

export interface DemandeDeTransition {
  readonly version: number;
}
