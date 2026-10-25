/**
 * Le cycle des alertes opérationnelles — LOT 10, `T13` (API), `T15` (premier
 * écran), `MVP-L10-US007`.
 *
 * AUCUN PLANCHER `SOI` : LA GRILLE PEUT RENDRE AUCUN DROIT
 *
 *   À la différence des signalements, `rolesTraitementDesAlertes` (ADM-E/
 *   SUPER) garde LA LECTURE AUTANT QUE L'ÉCRITURE — un ESM lit (périmètre
 *   `LIMITE`, masqué) mais n'écrit jamais : aucune des trois routes
 *   d'écriture n'admet l'ESM, confirmé en lisant `app/support/routes.py`
 *   plutôt que supposé. Ce module ne déclare donc PAS de grille de lecture
 *   séparée — la lecture reste ouverte à `peutTraiterLesAlertes` ∪ ESM, et
 *   c'est l'API qui tranche réellement (règle 5).
 *
 * TROIS ÉTATS SEULEMENT, « COMMENTÉE » N'EN EST PAS UN QUATRIÈME
 *
 *   `source`/`fingerprint` sont nuls pour `LIMITE` (ESM) — ce module les
 *   type `string | null`, jamais absents.
 */
import { CONTRAT_API, endpoint } from './sante.js';
import { estObjet, exigerChaine } from './formes.js';

export const ROLES_TRAITEMENT_DES_ALERTES: readonly string[] =
  CONTRAT_API.rolesTraitementDesAlertes;

export function peutTraiterLesAlertes(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_TRAITEMENT_DES_ALERTES.includes(role));
}

/**
 * La LECTURE, elle, reste ouverte à `peutTraiterLesAlertes` ∪ `ESM` (périmètre
 * `LIMITE` de l'API, `app/support/perimetre_alertes.py`) — aucune grille
 * statique ne la nomme, l'écriture seule distinguant les deux. Exportée ici
 * plutôt que laissée au composant appelant : le littéral `ESM` doit vivre
 * dans le contrat, jamais dans `apps/web` (`DEC-492`, `make cadre-check`).
 */
export function peutLireLesAlertes(roles: readonly string[] | null): boolean {
  return roles !== null && (peutTraiterLesAlertes(roles) || roles.includes('ESM'));
}

/** Les trois états réels — cahier §27.5. */
export const ETATS_D_ALERTE = ['open', 'acknowledged', 'resolved'] as const;
export type EtatDAlerte = (typeof ETATS_D_ALERTE)[number];

export const GABARIT_CHEMIN_ALERTES: string = endpoint('alertes').chemin;
export const CODES_ALERTES: readonly number[] = endpoint('alertes').codesExploitables;
export const GABARIT_CHEMIN_UNE_ALERTE: string = endpoint('uneAlerte').chemin;
export const CODES_UNE_ALERTE: readonly number[] = endpoint('uneAlerte').codesExploitables;
export const GABARIT_CHEMIN_COMMENTAIRES_D_ALERTE: string =
  endpoint('commentairesDUneAlerte').chemin;
export const CODES_COMMENTAIRES_D_ALERTE: readonly number[] =
  endpoint('commentairesDUneAlerte').codesExploitables;
export const GABARIT_CHEMIN_ACQUITTEMENT_D_ALERTE: string =
  endpoint('acquittementDUneAlerte').chemin;
export const CODES_ACQUITTEMENT_D_ALERTE: readonly number[] =
  endpoint('acquittementDUneAlerte').codesExploitables;
export const GABARIT_CHEMIN_RESOLUTION_D_ALERTE: string = endpoint('resolutionDUneAlerte').chemin;
export const CODES_RESOLUTION_D_ALERTE: readonly number[] =
  endpoint('resolutionDUneAlerte').codesExploitables;

export function cheminAlertes(page: number, taille: number, etat?: EtatDAlerte): string {
  const parametres = [
    `page=${encodeURIComponent(String(page))}`,
    `taille=${encodeURIComponent(String(taille))}`,
  ];
  if (etat !== undefined) {
    parametres.push(`etat=${encodeURIComponent(etat)}`);
  }
  return `${GABARIT_CHEMIN_ALERTES}?${parametres.join('&')}`;
}

function cheminAvecAlerte(gabarit: string, alerte: string): string {
  if (alerte === '') {
    throw new TypeError('identifiant d’alerte vide');
  }
  return gabarit.replace('{alerte}', encodeURIComponent(alerte));
}

export function cheminUneAlerte(alerte: string): string {
  return cheminAvecAlerte(GABARIT_CHEMIN_UNE_ALERTE, alerte);
}
export function cheminCommentairesDAlerte(alerte: string): string {
  return cheminAvecAlerte(GABARIT_CHEMIN_COMMENTAIRES_D_ALERTE, alerte);
}
export function cheminAcquittementDAlerte(alerte: string): string {
  return cheminAvecAlerte(GABARIT_CHEMIN_ACQUITTEMENT_D_ALERTE, alerte);
}
export function cheminResolutionDAlerte(alerte: string): string {
  return cheminAvecAlerte(GABARIT_CHEMIN_RESOLUTION_D_ALERTE, alerte);
}

export interface LigneDAlerte {
  readonly identifiant: string;
  readonly gravite: string;
  /** `null` si le périmètre est `LIMITE` (ESM) — jamais absent. */
  readonly source: string | null;
  readonly etat: string;
  readonly assigneA: string | null;
  readonly ouverteLe: string;
  readonly acquitteeLe: string | null;
  readonly resolueLe: string | null;
  /** `null` si le périmètre est `LIMITE` (ESM) — jamais absent. */
  readonly empreinte: string | null;
  readonly version: number;
}

export interface ReponseDesAlertes {
  readonly alertes: readonly LigneDAlerte[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

export interface CommentaireDAlerte {
  readonly identifiant: string;
  readonly contenu: string;
  readonly creeLe: string;
  readonly auteurId: string | null;
}

export interface ReponseDesCommentairesDAlerte {
  readonly commentaires: readonly CommentaireDAlerte[];
}

export interface DemandeDAcquittementDAlerte {
  readonly version: number;
}
export interface DemandeDeCommentaireDAlerte {
  readonly contenu: string;
}
export interface DemandeDeResolutionDAlerte {
  readonly version: number;
  readonly commentaire?: string;
}

export interface ReponseDeTransitionDAlerte {
  readonly etat: string;
  readonly version: number;
}
export interface ReponseDeCommentaireAjoute {
  readonly identifiant: string;
  readonly creeLe: string;
}

function chaineOuNulle(source: Record<string, unknown>, champ: string): string | null {
  const valeur = source[champ];
  if (valeur === null) {
    return null;
  }
  if (typeof valeur !== 'string') {
    throw new TypeError(`« ${champ} » ni chaine ni null`);
  }
  return valeur;
}

function entier(source: Record<string, unknown>, champ: string): number {
  const valeur = source[champ];
  if (typeof valeur !== 'number' || !Number.isInteger(valeur)) {
    throw new TypeError(`« ${champ} » absent ou non entier`);
  }
  return valeur;
}

export function validerUneAlerte(valeur: unknown): LigneDAlerte {
  if (!estObjet(valeur)) {
    throw new TypeError('alerte : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    gravite: exigerChaine(valeur, 'gravite'),
    source: chaineOuNulle(valeur, 'source'),
    etat: exigerChaine(valeur, 'etat'),
    assigneA: chaineOuNulle(valeur, 'assigne_a'),
    ouverteLe: exigerChaine(valeur, 'ouverte_le'),
    acquitteeLe: chaineOuNulle(valeur, 'acquittee_le'),
    resolueLe: chaineOuNulle(valeur, 'resolue_le'),
    empreinte: chaineOuNulle(valeur, 'empreinte'),
    version: entier(valeur, 'version'),
  };
}

export function validerLesAlertes(valeur: unknown): ReponseDesAlertes {
  if (!estObjet(valeur)) {
    throw new TypeError('alertes : charge utile non objet');
  }
  const brut = valeur['alertes'];
  if (!Array.isArray(brut)) {
    throw new TypeError('alertes : « alertes » n’est pas un tableau');
  }
  return {
    alertes: brut.map((a) => validerUneAlerte(a)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}

function validerUnCommentaireDAlerte(valeur: unknown, rang: number): CommentaireDAlerte {
  if (!estObjet(valeur)) {
    throw new TypeError(`commentaires : commentaires[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    contenu: exigerChaine(valeur, 'contenu'),
    creeLe: exigerChaine(valeur, 'cree_le'),
    auteurId: chaineOuNulle(valeur, 'auteur_id'),
  };
}

export function validerLesCommentairesDAlerte(valeur: unknown): ReponseDesCommentairesDAlerte {
  if (!estObjet(valeur)) {
    throw new TypeError('commentaires : charge utile non objet');
  }
  const brut = valeur['commentaires'];
  if (!Array.isArray(brut)) {
    throw new TypeError('commentaires : « commentaires » n’est pas un tableau');
  }
  return { commentaires: brut.map((c, rang) => validerUnCommentaireDAlerte(c, rang)) };
}

export function validerLaTransitionDAlerte(valeur: unknown): ReponseDeTransitionDAlerte {
  if (!estObjet(valeur)) {
    throw new TypeError('transition d’alerte : charge utile non objet');
  }
  return { etat: exigerChaine(valeur, 'etat'), version: entier(valeur, 'version') };
}

export function validerLeCommentaireAjoute(valeur: unknown): ReponseDeCommentaireAjoute {
  if (!estObjet(valeur)) {
    throw new TypeError('commentaire ajouté : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    creeLe: exigerChaine(valeur, 'cree_le'),
  };
}
