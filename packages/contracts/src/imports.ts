/**
 * Le contrat de l'import CSV, du dépôt au rapport — LOT 9, `T6` à `T10` (API)
 * puis `T14` (écran), `MVP-L09-US004`/`US005`/`US006`.
 *
 * CINQ GESTES, UN SEUL FICHIER — LE PARCOURS EST UN ASSISTANT, PAS UNE LISTE PARCOURABLE
 *
 *   Il n'existe AUCUNE route « lister les imports d'une entité » — mesuré sur
 *   `apps/api/app/imports/routes.py` : seules `GET …/clients` et
 *   `GET …/{lot}/rapport` lisent, et la seconde exige l'identifiant du lot déjà
 *   connu. L'écran ne peut donc PAS proposer un historique parcourable des
 *   imports passés ; le parcours est nécessairement SÉQUENTIEL dans la même
 *   session — déposer, décider les rapprochements, lancer, consulter le
 *   rapport, rejouer une ligne rejetée — et c'est un fait d'architecture
 *   constaté, pas une simplification choisie ici.
 *
 *   « Derniers imports en échec » du tableau de bord (`tableauDeBord.ts`)
 *   reste la SEULE vue agrégée sur des lots passés — un lien vers le rapport
 *   d'un lot EN ÉCHEC, jamais un navigateur d'historique général.
 *
 * DEUX GRILLES DE RÔLES, JAMAIS FUSIONNÉES
 *
 *   `ROLES_DEPOT_DE_L_IMPORT` (ESM/ADM-E/SUPER) gouverne déposer, lancer,
 *   rejouer. `ROLES_VALIDATION_DES_RAPPROCHEMENTS` (DSM/ESM/ADM-E/SUPER)
 *   gouverne consulter les clients et enregistrer une décision — un DSM peut
 *   décider dans son périmètre sans jamais pouvoir lancer un import.
 *
 * LE DÉPÔT EST UN FORMULAIRE MULTIPART, PAS DU JSON
 *
 *   `POST …/imports` attend un SEUL champ de formulaire, `fichier` — ce module
 *   déclare le chemin et la forme de réponse ; l'appel `FormData` lui-même
 *   vit dans le client HTTP de l'écran (`apps/web/src/api/imports.ts`), pas
 *   ici, puisqu'il dépend de `File`/`FormData`, absents de la `lib` de ce
 *   paquet (même motif que `URLSearchParams`, voir `trombinoscope.ts`).
 *
 * LES CINQ CATÉGORIES DE DÉCISION FERMENT LE MODÈLE, ET T8 N'EN EXERCE QUE DEUX
 *
 *   `person_merge`/`profile_reactivation` exigent une personne cible ;
 *   `client_alias_creation`/`canonical_client_selection` exigent un client
 *   cible ; `voluntary_rejection` n'exige rien. Les cinq sont déclarées ici
 *   parce que la route les accepte toutes structurellement — seules les deux
 *   catégories « client » sont proposées par l'écran de `T14`, les décisions
 *   `D-PERSONNE-*` restant sans résolution construite (résidu nommé, §9.3).
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

export const ROLES_DEPOT_DE_L_IMPORT: readonly string[] = CONTRAT_API.rolesDepotDeLImport;
export const ROLES_VALIDATION_DES_RAPPROCHEMENTS: readonly string[] =
  CONTRAT_API.rolesValidationDesRapprochements;

export function peutDeposerUnImport(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_DEPOT_DE_L_IMPORT.includes(role));
}

export function peutValiderLesRapprochements(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_VALIDATION_DES_RAPPROCHEMENTS.includes(role));
}

export const GABARIT_CHEMIN_DEPOT_D_IMPORT: string = endpoint('depotDUnImport').chemin;
export const CODES_DEPOT_D_IMPORT: readonly number[] = endpoint('depotDUnImport').codesExploitables;

export const GABARIT_CHEMIN_CLIENTS: string = endpoint('listeDesClients').chemin;
export const CODES_CLIENTS: readonly number[] = endpoint('listeDesClients').codesExploitables;

export const GABARIT_CHEMIN_DECISION: string = endpoint('enregistrerUneDecisionDImport').chemin;
export const CODES_DECISION: readonly number[] = endpoint(
  'enregistrerUneDecisionDImport',
).codesExploitables;

export const GABARIT_CHEMIN_LANCEMENT: string = endpoint('lancerLImport').chemin;
export const CODES_LANCEMENT: readonly number[] = endpoint('lancerLImport').codesExploitables;

export const GABARIT_CHEMIN_REJEU: string = endpoint('rejouerUneLigneDImport').chemin;
export const CODES_REJEU: readonly number[] = endpoint('rejouerUneLigneDImport').codesExploitables;

export const GABARIT_CHEMIN_RAPPORT: string = endpoint('consulterLeRapportDImport').chemin;
export const CODES_RAPPORT: readonly number[] = endpoint(
  'consulterLeRapportDImport',
).codesExploitables;

export function cheminDepotDImport(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_DEPOT_D_IMPORT.replace('{code}', encodeURIComponent(code));
}

export function cheminListeDesClients(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_CLIENTS.replace('{code}', encodeURIComponent(code));
}

function cheminSurUneLigne(gabarit: string, code: string, lot: string, ligne: string): string {
  if (code === '' || lot === '' || ligne === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource.
    throw new TypeError('code d’entite, identifiant de lot ou de ligne vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{lot}', encodeURIComponent(lot))
    .replace('{ligne}', encodeURIComponent(ligne));
}

export function cheminDecision(code: string, lot: string, ligne: string): string {
  return cheminSurUneLigne(GABARIT_CHEMIN_DECISION, code, lot, ligne);
}

export function cheminRejeu(code: string, lot: string, ligne: string): string {
  return cheminSurUneLigne(GABARIT_CHEMIN_REJEU, code, lot, ligne);
}

export function cheminLancement(code: string, lot: string): string {
  if (code === '' || lot === '') {
    throw new TypeError('code d’entite ou identifiant de lot vide');
  }
  return GABARIT_CHEMIN_LANCEMENT.replace('{code}', encodeURIComponent(code)).replace(
    '{lot}',
    encodeURIComponent(lot),
  );
}

export function cheminRapport(code: string, lot: string, page?: number, taille?: number): string {
  if (code === '' || lot === '') {
    throw new TypeError('code d’entite ou identifiant de lot vide');
  }
  const base = GABARIT_CHEMIN_RAPPORT.replace('{code}', encodeURIComponent(code)).replace(
    '{lot}',
    encodeURIComponent(lot),
  );
  //  **PAS DE `URLSearchParams` ICI** — meme motif que `cheminTrombinoscope`.
  const parametres: string[] = [];
  if (page !== undefined) {
    parametres.push(`page=${encodeURIComponent(String(page))}`);
  }
  if (taille !== undefined) {
    parametres.push(`taille=${encodeURIComponent(String(taille))}`);
  }
  return parametres.length === 0 ? base : `${base}?${parametres.join('&')}`;
}

/** Ce que `POST …/imports` rend — `T6`/`T7`, l'etat atteint `preview_ready` dans le MEME appel. */
export interface LotDepose {
  readonly identifiant: string;
  readonly nomDeFichier: string;
  readonly empreinteSha256: string;
  readonly etat: string;
  readonly totalLignes: number;
  readonly lignesValides: number;
  readonly lignesAvecAvertissement: number;
  readonly lignesAConfirmer: number;
  readonly lignesRejetees: number;
  readonly version: number;
}

/** Un client du catalogue, propose au rapprochement — `T8`, ferme `ECART-060` pour les clients. */
export interface ClientDuCatalogue {
  readonly identifiant: string;
  readonly nomCanonique: string;
  readonly nomAffiche: string;
  readonly actifLocalement: boolean;
}

export interface ReponseDesClients {
  readonly clients: readonly ClientDuCatalogue[];
}

/** Les cinq categories du modele §19.4 — T8/T14 n'en exercent que les deux « client ». */
export const TYPES_DE_DECISION = [
  'person_merge',
  'profile_reactivation',
  'client_alias_creation',
  'canonical_client_selection',
  'voluntary_rejection',
] as const;
export type TypeDeDecision = (typeof TYPES_DE_DECISION)[number];

/** Le corps de `POST …/rows/{ligne}/decisions` — RESTE en snake_case, le format attendu par l'API. */
export interface DemandeDeDecision {
  readonly decision_type: TypeDeDecision;
  readonly target_person_id?: string | null;
  readonly target_client_id?: string | null;
  readonly reason?: string | null;
}

export interface DecisionEnregistree {
  readonly identifiant: string;
  readonly decisionType: string;
}

export interface ReponseDeLancement {
  readonly version: number;
  readonly etat: string;
  readonly lignesImportees: number;
  readonly lignesMisesAJour: number;
  readonly lignesRejeteesALImport: number;
  readonly lignesEnAttenteDeDecision: number;
}

export interface ReponseDeRejeu {
  readonly etat: string;
  readonly codesDErreur: readonly string[];
}

export interface ProblemeDeLigne {
  readonly code: string;
  readonly champ: string | null;
  readonly message: string;
  readonly niveau: string;
}

export interface LigneDuRapport {
  readonly identifiant: string;
  readonly numero: number;
  readonly etat: string;
  readonly codesDErreur: readonly string[];
  readonly problemes: readonly ProblemeDeLigne[];
}

/** La reconciliation du cahier §9.5 point 8 — une lecture FRAICHE, jamais un cache. */
export interface Reconciliation {
  readonly totalLignes: number;
  readonly creations: number;
  readonly misesAJour: number;
  readonly rejets: number;
  readonly enAttenteDeDecision: number;
  readonly enCours: number;
}

export interface RapportDImport {
  readonly etatDuLot: string;
  readonly nomDeFichier: string;
  readonly empreinteSha256: string;
  readonly delimiteur: string | null;
  readonly encodage: string;
  readonly profilDeCorrespondance: string;
  readonly deposePar: string;
  readonly approuvePar: string | null;
  readonly compteursDePrevisualisation: Readonly<Record<string, number>>;
  readonly reconciliation: Reconciliation;
  readonly lignes: readonly LigneDuRapport[];
  readonly totalDesLignes: number;
  readonly page: number;
  readonly taille: number;
  readonly pages: number;
}

function exigerEntier(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non entier`);
  }
  return brut;
}

function exigerTableauDeChaines(valeur: Record<string, unknown>, champ: string): readonly string[] {
  const brut = valeur[champ];
  if (!Array.isArray(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non tableau`);
  }
  return brut.map((v, rang) => {
    if (typeof v !== 'string') {
      throw new TypeError(`${champ}[${String(rang)}] non textuel`);
    }
    return v;
  });
}

function chaineOuNulle(valeur: Record<string, unknown>, champ: string): string | null {
  const brut = valeur[champ];
  if (brut === null || brut === undefined) {
    return null;
  }
  if (typeof brut !== 'string') {
    throw new TypeError(`champ « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function comptesParCle(valeur: unknown, cle: string): Readonly<Record<string, number>> {
  if (!estObjet(valeur)) {
    throw new TypeError(`« ${cle} » n’est pas un objet`);
  }
  const comptes: Record<string, number> = {};
  for (const [nom, compte] of Object.entries(valeur)) {
    if (typeof compte !== 'number' || !Number.isInteger(compte)) {
      throw new TypeError(`${cle}.${nom} n’est pas un entier`);
    }
    comptes[nom] = compte;
  }
  return comptes;
}

export function validerLeLotDepose(valeur: unknown): LotDepose {
  if (!estObjet(valeur)) {
    throw new TypeError('lot depose : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    nomDeFichier: exigerChaine(valeur, 'nom_de_fichier'),
    empreinteSha256: exigerChaine(valeur, 'empreinte_sha256'),
    etat: exigerChaine(valeur, 'etat'),
    totalLignes: exigerEntier(valeur, 'total_lignes'),
    lignesValides: exigerEntier(valeur, 'lignes_valides'),
    lignesAvecAvertissement: exigerEntier(valeur, 'lignes_avec_avertissement'),
    lignesAConfirmer: exigerEntier(valeur, 'lignes_a_confirmer'),
    lignesRejetees: exigerEntier(valeur, 'lignes_rejetees'),
    version: exigerEntier(valeur, 'version'),
  };
}

function validerUnClient(valeur: unknown, rang: number): ClientDuCatalogue {
  if (!estObjet(valeur)) {
    throw new TypeError(`clients[${String(rang)}] : charge utile non objet`);
  }
  const actif = valeur['actif_localement'];
  if (typeof actif !== 'boolean') {
    throw new TypeError(`clients[${String(rang)}].actif_localement absent ou non booleen`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    nomCanonique: exigerChaine(valeur, 'nom_canonique'),
    nomAffiche: exigerChaine(valeur, 'nom_affiche'),
    actifLocalement: actif,
  };
}

/** Valider `GET …/clients` — AUCUNE pagination, AUCUNE enveloppe page/total. */
export function validerLesClients(valeur: unknown): ReponseDesClients {
  if (!estObjet(valeur)) {
    throw new TypeError('clients : charge utile non objet');
  }
  const clients = valeur['clients'];
  if (!Array.isArray(clients)) {
    throw new TypeError('champ « clients » absent ou non tableau');
  }
  return { clients: clients.map((c, rang) => validerUnClient(c, rang)) };
}

export function validerLaDecision(valeur: unknown): DecisionEnregistree {
  if (!estObjet(valeur)) {
    throw new TypeError('decision : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    decisionType: exigerChaine(valeur, 'decision_type'),
  };
}

export function validerLeLancement(valeur: unknown): ReponseDeLancement {
  if (!estObjet(valeur)) {
    throw new TypeError('lancement : charge utile non objet');
  }
  return {
    version: exigerEntier(valeur, 'version'),
    etat: exigerChaine(valeur, 'etat'),
    lignesImportees: exigerEntier(valeur, 'lignes_importees'),
    lignesMisesAJour: exigerEntier(valeur, 'lignes_mises_a_jour'),
    lignesRejeteesALImport: exigerEntier(valeur, 'lignes_rejetees_a_l_import'),
    lignesEnAttenteDeDecision: exigerEntier(valeur, 'lignes_en_attente_de_decision'),
  };
}

export function validerLeRejeu(valeur: unknown): ReponseDeRejeu {
  if (!estObjet(valeur)) {
    throw new TypeError('rejeu : charge utile non objet');
  }
  return {
    etat: exigerChaine(valeur, 'etat'),
    codesDErreur: exigerTableauDeChaines(valeur, 'codes_derreur'),
  };
}

function validerUnProbleme(valeur: unknown, rang: number): ProblemeDeLigne {
  if (!estObjet(valeur)) {
    throw new TypeError(`problemes[${String(rang)}] : charge utile non objet`);
  }
  return {
    code: exigerChaine(valeur, 'code'),
    champ: chaineOuNulle(valeur, 'champ'),
    message: exigerChaine(valeur, 'message'),
    niveau: exigerChaine(valeur, 'niveau'),
  };
}

function validerUneLigneDuRapport(valeur: unknown, rang: number): LigneDuRapport {
  if (!estObjet(valeur)) {
    throw new TypeError(`lignes[${String(rang)}] : charge utile non objet`);
  }
  const problemes = valeur['problemes'];
  if (!Array.isArray(problemes)) {
    throw new TypeError(`lignes[${String(rang)}].problemes absent ou non tableau`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    numero: exigerEntier(valeur, 'numero'),
    etat: exigerChaine(valeur, 'etat'),
    codesDErreur: exigerTableauDeChaines(valeur, 'codes_derreur'),
    problemes: problemes.map((p, r) => validerUnProbleme(p, r)),
  };
}

function validerLaReconciliation(valeur: unknown): Reconciliation {
  if (!estObjet(valeur)) {
    throw new TypeError('reconciliation : charge utile non objet');
  }
  return {
    totalLignes: exigerEntier(valeur, 'total_lignes'),
    creations: exigerEntier(valeur, 'creations'),
    misesAJour: exigerEntier(valeur, 'mises_a_jour'),
    rejets: exigerEntier(valeur, 'rejets'),
    enAttenteDeDecision: exigerEntier(valeur, 'en_attente_de_decision'),
    enCours: exigerEntier(valeur, 'en_cours'),
  };
}

/**
 * Valider `GET …/rapport` — la reconciliation la plus riche du lot.
 *
 * **AUCUNE LIGNE REJETEE N'EST MASQUEE** (critere de sortie 5 du lot) : le
 * validateur exige le tableau `lignes` en entier, jamais une troncature
 * silencieuse qui laisserait croire a un rapport exhaustif.
 */
export function validerLeRapport(valeur: unknown): RapportDImport {
  if (!estObjet(valeur)) {
    throw new TypeError('rapport : charge utile non objet');
  }
  const lignes = valeur['lignes'];
  if (!Array.isArray(lignes)) {
    throw new TypeError('champ « lignes » absent ou non tableau');
  }
  return {
    etatDuLot: exigerChaine(valeur, 'etat_du_lot'),
    nomDeFichier: exigerChaine(valeur, 'nom_de_fichier'),
    empreinteSha256: exigerChaine(valeur, 'empreinte_sha256'),
    delimiteur: chaineOuNulle(valeur, 'delimiteur'),
    encodage: exigerChaine(valeur, 'encodage'),
    profilDeCorrespondance: exigerChaine(valeur, 'profil_de_correspondance'),
    deposePar: exigerChaine(valeur, 'depose_par'),
    approuvePar: chaineOuNulle(valeur, 'approuve_par'),
    compteursDePrevisualisation: comptesParCle(
      valeur['compteurs_de_previsualisation'],
      'compteurs_de_previsualisation',
    ),
    reconciliation: validerLaReconciliation(valeur['reconciliation']),
    lignes: lignes.map((l, rang) => validerUneLigneDuRapport(l, rang)),
    totalDesLignes: exigerEntier(valeur, 'total_des_lignes'),
    page: exigerEntier(valeur, 'page'),
    taille: exigerEntier(valeur, 'taille'),
    pages: exigerEntier(valeur, 'pages'),
  };
}
