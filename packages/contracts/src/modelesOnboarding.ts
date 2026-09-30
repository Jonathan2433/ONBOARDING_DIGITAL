/**
 * Le contrat des modeles d'onboarding et de leur cycle de vie — LOT 7, `T14`.
 *
 * Matrice §9, modele §13.2 a §13.4. `T5`/`T6` livraient les cinq routes
 * d'ecriture (creer un modele, une version, poser ses taches, publier,
 * archiver, restaurer) SANS module de contrat propre — « ecriture pure »,
 * meme parti que le catalogue de `T4`. `T14`, en construisant l'ecran
 * d'administration, en devient le premier consommateur : c'est donc ce
 * module qui les pose, en meme temps que la LECTURE (`consultationDesModelesOnboarding`)
 * qui n'existait pas avant lui — voir `app/onboarding/gabarits.py`.
 *
 * **CINQ REPONSES D'ECRITURE, CINQ FORMES DIFFERENTES, CINQ VALIDATEURS.**
 * Une reponse de creation porte `change_summary`, jamais `published_at` ; une
 * reponse de publication porte `published_at`/`published_by_person_id` NON
 * NULS ; une reponse d'archivage ne porte ni l'un ni l'autre ; une reponse de
 * restauration les porte NULLABLES (la version restauree GARDE sa publication
 * d'origine). Les fusionner en un type unique et laxiste masquerait ces
 * differences reelles — meme discipline que `DemandeDeCompletionDeFiche` et
 * `DemandeDeValidationDeFiche` (`ficheArrivee.ts`, `T3`), deux formes plutot
 * qu'une.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/** Le gabarit du chemin des modeles, lu du manifeste — `DEC-492`. */
export const GABARIT_CHEMIN_MODELES_ONBOARDING: string = endpoint(
  'consultationDesModelesOnboarding',
).chemin;

export const CODES_CONSULTATION_DES_MODELES: readonly number[] = endpoint(
  'consultationDesModelesOnboarding',
).codesExploitables;
export const CODES_CREATION_D_UN_MODELE: readonly number[] = endpoint(
  'creationDUnModeleOnboarding',
).codesExploitables;
export const CODES_CREATION_D_UNE_VERSION: readonly number[] = endpoint(
  'creationDUneVersionDeModele',
).codesExploitables;
export const CODES_DEFINITION_DES_TACHES: readonly number[] = endpoint(
  'definitionDesTachesDUneVersion',
).codesExploitables;
export const CODES_PUBLICATION_DE_VERSION: readonly number[] = endpoint(
  'publicationDUneVersionDeModele',
).codesExploitables;
export const CODES_ARCHIVAGE_DE_VERSION: readonly number[] = endpoint(
  'archivageDUneVersionDeModele',
).codesExploitables;
export const CODES_RESTAURATION_DE_VERSION: readonly number[] = endpoint(
  'restaurationDUneVersionDeModele',
).codesExploitables;

/**
 * Les roles qui RESTAURENT une version — matrice §9, `ECART-066` resolu.
 *
 * **DSM ET BOOST SONT EXCLUS EN BLOC**, contrairement aux autres gestes de
 * cette meme grille (`rolesAdministrationOnboarding` les inclut). Une
 * coincidence avec `rolesRestaurationDUnContenu`/`rolesCycleDeVie`, pas une
 * derivation — voir le manifeste. Sert a NE PAS PROPOSER un bouton
 * « Restaurer » qu'un DSM ou un Booster verrait de toute facon refuse (§7.21).
 */
export const ROLES_RESTAURATION_DES_MODELES_ONBOARDING: readonly string[] =
  CONTRAT_API.rolesRestaurationDesModelesOnboarding;

const GABARIT_CHEMIN_VERSIONS: string = endpoint('creationDUneVersionDeModele').chemin;
const GABARIT_CHEMIN_TACHES: string = endpoint('definitionDesTachesDUneVersion').chemin;
const GABARIT_CHEMIN_PUBLICATION: string = endpoint('publicationDUneVersionDeModele').chemin;
const GABARIT_CHEMIN_ARCHIVAGE: string = endpoint('archivageDUneVersionDeModele').chemin;
const GABARIT_CHEMIN_RESTAURATION: string = endpoint('restaurationDUneVersionDeModele').chemin;

/** Le chemin des modeles d'une entite — liste (`GET`) et creation (`POST`). */
export function cheminModelesOnboarding(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource —
    //  meme raisonnement que `cheminCatalogueDeTaches`.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_MODELES_ONBOARDING.replace('{code}', encodeURIComponent(code));
}

function cheminAvecModele(gabarit: string, code: string, modele: string): string {
  if (code === '' || modele === '') {
    throw new TypeError('code d’entite ou identifiant de modele vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{template_id}', encodeURIComponent(modele));
}

export function cheminVersionsDeModele(code: string, modele: string): string {
  return cheminAvecModele(GABARIT_CHEMIN_VERSIONS, code, modele);
}

function cheminAvecModeleEtVersion(
  gabarit: string,
  code: string,
  modele: string,
  version: string,
): string {
  if (code === '' || modele === '' || version === '') {
    throw new TypeError('code d’entite, identifiant de modele ou de version vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{template_id}', encodeURIComponent(modele))
    .replace('{version_id}', encodeURIComponent(version));
}

export function cheminTachesDeVersion(code: string, modele: string, version: string): string {
  return cheminAvecModeleEtVersion(GABARIT_CHEMIN_TACHES, code, modele, version);
}

export function cheminPublicationDeVersion(code: string, modele: string, version: string): string {
  return cheminAvecModeleEtVersion(GABARIT_CHEMIN_PUBLICATION, code, modele, version);
}

export function cheminArchivageDeVersion(code: string, modele: string, version: string): string {
  return cheminAvecModeleEtVersion(GABARIT_CHEMIN_ARCHIVAGE, code, modele, version);
}

export function cheminRestaurationDeVersion(code: string, modele: string, version: string): string {
  return cheminAvecModeleEtVersion(GABARIT_CHEMIN_RESTAURATION, code, modele, version);
}

/** Le corps de `POST …/templates` — modele §13.2. */
export interface DemandeDeModeleOnboarding {
  readonly name: string;
  readonly target_status: 'mission' | 'intercontract';
  readonly portee: 'GLOBAL' | 'ENTITY' | 'DSM' | 'CIRCLE';
  readonly scope_person_id?: string;
  readonly scope_circle_id?: string;
}

/** Le corps de `POST …/versions` — modele §13.3, vide si aucun resume. */
export interface DemandeDeVersionDeModele {
  readonly change_summary?: string;
}

/** Une ligne de `PUT …/tasks` — modele §13.4. `display_order` n'y figure PAS :
 * il vaut l'INDEX de cette ligne dans le tableau envoye, jamais un rang saisi. */
export interface DemandeDeTacheDeVersion {
  readonly task_reference_id: string;
  readonly required: boolean;
  readonly due_offset_days: number;
  readonly title_override?: string;
  readonly description_override?: string;
}

export interface DemandeDesTachesDeVersion {
  readonly taches: readonly DemandeDeTacheDeVersion[];
}

interface ChampsDeBaseDuModele {
  readonly id: string;
  readonly entiteId: string | null;
  readonly nom: string;
  readonly statutCible: string;
  readonly portee: string;
  readonly scopePersonId: string | null;
  readonly scopeCircleId: string | null;
  readonly etat: string;
}

/** Un modele tel que rendu par la creation — sans ses versions, il n'en a aucune. */
export type ModeleOnboardingCree = ChampsDeBaseDuModele;

export interface VersionDeModeleOnboarding {
  readonly id: string;
  readonly modeleId: string;
  readonly numero: number;
  readonly etat: string;
  readonly resumeDuChangement: string | null;
}

/** Un modele avec ses versions — la LISTE, `T14`. */
export interface ModeleOnboardingAvecVersions extends ChampsDeBaseDuModele {
  readonly versions: readonly VersionDeModeleOnboarding[];
}

export interface PageDesModelesOnboarding {
  readonly modeles: readonly ModeleOnboardingAvecVersions[];
  readonly nombreDeModeles: number;
}

export interface TacheDeVersion {
  readonly id: string;
  readonly referenceDeLaTache: string;
  readonly ordre: number;
  readonly obligatoire: boolean;
  readonly echeanceEnJours: number;
  readonly titreDeRemplacement: string | null;
  readonly descriptionDeRemplacement: string | null;
}

export interface TachesDeVersion {
  readonly taches: readonly TacheDeVersion[];
  readonly nombreDeTaches: number;
}

export interface VersionPubliee {
  readonly id: string;
  readonly numero: number;
  readonly etat: string;
  readonly publieeLe: string;
  readonly publieeParPersonneId: string;
}

export interface VersionArchivee {
  readonly id: string;
  readonly numero: number;
  readonly etat: string;
}

export interface VersionRestauree {
  readonly id: string;
  readonly numero: number;
  readonly etat: string;
  readonly publieeLe: string | null;
  readonly publieeParPersonneId: string | null;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Meme discipline que `ficheArrivee.ts`.
    throw new TypeError(`modeles d’onboarding : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function exigerBooleen(source: Record<string, unknown>, champ: string): boolean {
  const valeur = source[champ];
  if (typeof valeur !== 'boolean') {
    throw new TypeError(`modeles d’onboarding : « ${champ} » absent ou non booleen`);
  }
  return valeur;
}

function exigerEntier(source: Record<string, unknown>, champ: string): number {
  const valeur = source[champ];
  if (typeof valeur !== 'number' || !Number.isInteger(valeur)) {
    throw new TypeError(`modeles d’onboarding : « ${champ} » absent ou non entier`);
  }
  return valeur;
}

function champsDeBaseDuModele(valeur: Record<string, unknown>): ChampsDeBaseDuModele {
  return {
    id: exigerChaine(valeur, 'id'),
    entiteId: chaineOuNul(valeur, 'entity_id'),
    nom: exigerChaine(valeur, 'name'),
    statutCible: exigerChaine(valeur, 'target_status'),
    portee: exigerChaine(valeur, 'scope_type'),
    scopePersonId: chaineOuNul(valeur, 'scope_person_id'),
    scopeCircleId: chaineOuNul(valeur, 'scope_circle_id'),
    etat: exigerChaine(valeur, 'state'),
  };
}

/** Valider ce que `POST …/templates` a rendu. */
export function validerUnModeleCree(valeur: unknown): ModeleOnboardingCree {
  if (!estObjet(valeur)) {
    throw new TypeError('modele d’onboarding : charge utile non objet');
  }
  return champsDeBaseDuModele(valeur);
}

function validerUneVersionImbriquee(valeur: unknown, rang: number): VersionDeModeleOnboarding {
  if (!estObjet(valeur)) {
    throw new TypeError(`modele d’onboarding : versions[${String(rang)}] non objet`);
  }
  return {
    id: exigerChaine(valeur, 'id'),
    modeleId: exigerChaine(valeur, 'template_id'),
    numero: exigerEntier(valeur, 'version_number'),
    etat: exigerChaine(valeur, 'state'),
    resumeDuChangement: chaineOuNul(valeur, 'change_summary'),
  };
}

function validerUnModeleAvecVersions(valeur: unknown, rang: number): ModeleOnboardingAvecVersions {
  if (!estObjet(valeur)) {
    throw new TypeError(`modeles d’onboarding : modeles[${String(rang)}] non objet`);
  }
  const brutVersions = valeur['versions'];
  if (!Array.isArray(brutVersions)) {
    throw new TypeError(`modeles d’onboarding : modeles[${String(rang)}].versions non tableau`);
  }
  return {
    ...champsDeBaseDuModele(valeur),
    versions: brutVersions.map((v, r) => validerUneVersionImbriquee(v, r)),
  };
}

/** Valider ce que `GET …/templates` a rendu — `T14`. */
export function validerLesModelesOnboarding(valeur: unknown): PageDesModelesOnboarding {
  if (!estObjet(valeur)) {
    throw new TypeError('modeles d’onboarding : charge utile non objet');
  }
  const brutListe = valeur['modeles'];
  if (!Array.isArray(brutListe)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Meme discipline que
    //  le catalogue de `T4`.
    throw new TypeError('modeles d’onboarding : « modeles » n’est pas un tableau');
  }
  const modeles = brutListe.map((brut, rang) => validerUnModeleAvecVersions(brut, rang));
  const nombre = exigerEntier(valeur, 'nombre_de_modeles');
  if (nombre !== modeles.length) {
    throw new TypeError(
      `modeles d’onboarding : nombre_de_modeles vaut ${String(nombre)} pour ` +
        `${String(modeles.length)} modele(s) rendu(s)`,
    );
  }
  return { modeles, nombreDeModeles: nombre };
}

/** Valider ce que `POST …/versions` a rendu. */
export function validerUneVersionCreee(valeur: unknown): VersionDeModeleOnboarding {
  if (!estObjet(valeur)) {
    throw new TypeError('version de modele : charge utile non objet');
  }
  return validerUneVersionImbriquee(valeur, 0);
}

/** Valider ce que `PUT …/tasks` a rendu. */
export function validerLesTachesDeVersion(valeur: unknown): TachesDeVersion {
  if (!estObjet(valeur)) {
    throw new TypeError('taches de version : charge utile non objet');
  }
  const brutListe = valeur['taches'];
  if (!Array.isArray(brutListe)) {
    throw new TypeError('taches de version : « taches » n’est pas un tableau');
  }
  const taches = brutListe.map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`taches de version : taches[${String(rang)}] non objet`);
    }
    return {
      id: exigerChaine(brut, 'id'),
      referenceDeLaTache: exigerChaine(brut, 'task_reference_id'),
      ordre: exigerEntier(brut, 'display_order'),
      obligatoire: exigerBooleen(brut, 'required'),
      echeanceEnJours: exigerEntier(brut, 'due_offset_days'),
      titreDeRemplacement: chaineOuNul(brut, 'title_override'),
      descriptionDeRemplacement: chaineOuNul(brut, 'description_override'),
    };
  });
  const nombre = exigerEntier(valeur, 'nombre_de_taches');
  if (nombre !== taches.length) {
    throw new TypeError(
      `taches de version : nombre_de_taches vaut ${String(nombre)} pour ` +
        `${String(taches.length)} tache(s) rendue(s)`,
    );
  }
  return { taches, nombreDeTaches: nombre };
}

/** Valider ce que `POST …/publication` a rendu. */
export function validerLaPublicationDeVersion(valeur: unknown): VersionPubliee {
  if (!estObjet(valeur)) {
    throw new TypeError('publication de version : charge utile non objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    numero: exigerEntier(valeur, 'version_number'),
    etat: exigerChaine(valeur, 'state'),
    publieeLe: exigerChaine(valeur, 'published_at'),
    publieeParPersonneId: exigerChaine(valeur, 'published_by_person_id'),
  };
}

/** Valider ce que `POST …/archivage` a rendu. */
export function validerLArchivageDeVersion(valeur: unknown): VersionArchivee {
  if (!estObjet(valeur)) {
    throw new TypeError('archivage de version : charge utile non objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    numero: exigerEntier(valeur, 'version_number'),
    etat: exigerChaine(valeur, 'state'),
  };
}

/** Valider ce que `POST …/restauration` a rendu. `state` revient a `published`,
 * JAMAIS a `draft` — modele §13.3, `ECART-066` resolu. */
export function validerLaRestaurationDeVersion(valeur: unknown): VersionRestauree {
  if (!estObjet(valeur)) {
    throw new TypeError('restauration de version : charge utile non objet');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    numero: exigerEntier(valeur, 'version_number'),
    etat: exigerChaine(valeur, 'state'),
    publieeLe: chaineOuNul(valeur, 'published_at'),
    publieeParPersonneId: chaineOuNul(valeur, 'published_by_person_id'),
  };
}
