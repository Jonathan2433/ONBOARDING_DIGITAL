/**
 * Le journal d'audit en lecture et son export CSV — LOT 10, `T8`/`T9` (API),
 * `T15` (premier écran), `MVP-L10-US001`/`US002`/`US004`.
 *
 * TROIS GRILLES DE RÔLES, JAMAIS FUSIONNÉES
 *
 *   `rolesDeLAudit` (lecture générale, six rôles — EMP/NEW/ANON à tiret),
 *   `rolesDetailsTechniquesDeLAudit` (ADM-E/SUPER seuls — masque
 *   `resourceReference`/`correlationToken`) et `rolesExportDeLAudit`
 *   (ADM-E/SUPER aussi, mais une CONSTANTE SÉPARÉE côté API : deux lignes
 *   distinctes du §16, une coïncidence de valeurs, jamais une identité —
 *   voir `app/audit/perimetre.py`). Les fusionner ferait suivre l'une quand
 *   la matrice change l'autre, en silence (§7.27).
 *
 * L'EXPORT NE REND PAS DU JSON
 *
 *   `forme: "octets"` au manifeste : la réponse est un fichier CSV brut. Ce
 *   module ne porte donc AUCUN validateur pour l'export — rien à valider
 *   dans des octets — seulement son chemin, ses codes et sa grille. Le
 *   déclenchement du téléchargement (`Blob`, URL objet, clic simulé) vit
 *   côté `apps/web`, hors du contrat.
 */
import { CONTRAT_API, endpoint } from './sante.js';
import { estObjet, exigerChaine } from './formes.js';

export const ROLES_DE_L_AUDIT: readonly string[] = CONTRAT_API.rolesDeLAudit;
export const ROLES_DETAILS_TECHNIQUES_DE_L_AUDIT: readonly string[] =
  CONTRAT_API.rolesDetailsTechniquesDeLAudit;
export const ROLES_EXPORT_DE_L_AUDIT: readonly string[] = CONTRAT_API.rolesExportDeLAudit;

export function peutConsulterLAudit(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_DE_L_AUDIT.includes(role));
}

export function peutVoirLesDetailsTechniquesDeLAudit(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_DETAILS_TECHNIQUES_DE_L_AUDIT.includes(role));
}

export function peutExporterLAudit(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_EXPORT_DE_L_AUDIT.includes(role));
}

export const GABARIT_CHEMIN_JOURNAL_D_AUDIT: string = endpoint('journalDAudit').chemin;
export const CODES_JOURNAL_D_AUDIT: readonly number[] = endpoint('journalDAudit').codesExploitables;
export const GABARIT_CHEMIN_EXPORT_DU_JOURNAL: string = endpoint('exportDuJournalDAudit').chemin;
export const CODES_EXPORT_DU_JOURNAL: readonly number[] =
  endpoint('exportDuJournalDAudit').codesExploitables;

/** Les cinq filtres facultatifs, dérivés des colonnes réelles d'`audit_event`. */
export interface FiltresDAudit {
  readonly depuis?: string;
  readonly jusqua?: string;
  readonly actionCode?: string;
  readonly resourceType?: string;
  readonly acteur?: string;
}

//  **PAS DE `URLSearchParams` ICI** : ce paquet n'a pas la bibliotheque DOM
//  dans son `lib` (voir `trombinoscope.ts`) — un tableau de paires et
//  `encodeURIComponent` suffisent, et ne dependent d'aucun global
//  d'environnement.
function parametresDeFiltre(filtres: FiltresDAudit): string[] {
  const parametres: string[] = [];
  if (filtres.depuis !== undefined) {
    parametres.push(`depuis=${encodeURIComponent(filtres.depuis)}`);
  }
  if (filtres.jusqua !== undefined) {
    parametres.push(`jusqua=${encodeURIComponent(filtres.jusqua)}`);
  }
  if (filtres.actionCode !== undefined) {
    parametres.push(`action_code=${encodeURIComponent(filtres.actionCode)}`);
  }
  if (filtres.resourceType !== undefined) {
    parametres.push(`resource_type=${encodeURIComponent(filtres.resourceType)}`);
  }
  if (filtres.acteur !== undefined) {
    parametres.push(`acteur=${encodeURIComponent(filtres.acteur)}`);
  }
  return parametres;
}

/** Le chemin du journal d'une entité, paginé et filtré. */
export function cheminJournalDAudit(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDAudit = {},
): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource.
    throw new TypeError('code d’entité vide');
  }
  const parametres = [
    `page=${encodeURIComponent(String(page))}`,
    `taille=${encodeURIComponent(String(taille))}`,
    ...parametresDeFiltre(filtres),
  ];
  return `${GABARIT_CHEMIN_JOURNAL_D_AUDIT.replace('{code}', encodeURIComponent(code))}?${parametres.join('&')}`;
}

/** Le chemin de l'export CSV d'une entité, mêmes filtres, jamais de pagination. */
export function cheminExportDuJournal(code: string, filtres: FiltresDAudit = {}): string {
  if (code === '') {
    throw new TypeError('code d’entité vide');
  }
  const parametres = parametresDeFiltre(filtres);
  const base = GABARIT_CHEMIN_EXPORT_DU_JOURNAL.replace('{code}', encodeURIComponent(code));
  return parametres.length === 0 ? base : `${base}?${parametres.join('&')}`;
}

export interface EvenementDAudit {
  readonly id: string;
  readonly occurredAt: string;
  readonly actionCode: string;
  readonly resourceType: string;
  /** `null` si le rôle n'a pas les détails techniques — jamais absent. */
  readonly resourceReference: string | null;
  readonly summary: string;
  readonly oldValues: Readonly<Record<string, unknown>> | null;
  readonly newValues: Readonly<Record<string, unknown>> | null;
  readonly reason: string | null;
  readonly actorPersonId: string | null;
  readonly actorServiceAccountId: string | null;
  /** `null` si le rôle n'a pas les détails techniques — jamais absent. */
  readonly correlationToken: string | null;
  readonly retentionUntil: string;
}

export interface ReponseDuJournalDAudit {
  readonly evenements: readonly EvenementDAudit[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
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

function objetOuNul(
  source: Record<string, unknown>,
  champ: string,
): Record<string, unknown> | null {
  const valeur = source[champ];
  if (valeur === null) {
    return null;
  }
  if (!estObjet(valeur)) {
    throw new TypeError(`« ${champ} » ni objet ni null`);
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

function validerUnEvenementDAudit(valeur: unknown, rang: number): EvenementDAudit {
  if (!estObjet(valeur)) {
    throw new TypeError(`journal d’audit : evenements[${String(rang)}] non objet`);
  }
  return {
    id: exigerChaine(valeur, 'id'),
    occurredAt: exigerChaine(valeur, 'occurred_at'),
    actionCode: exigerChaine(valeur, 'action_code'),
    resourceType: exigerChaine(valeur, 'resource_type'),
    resourceReference: chaineOuNulle(valeur, 'resource_reference'),
    summary: exigerChaine(valeur, 'summary'),
    oldValues: objetOuNul(valeur, 'old_values'),
    newValues: objetOuNul(valeur, 'new_values'),
    reason: chaineOuNulle(valeur, 'reason'),
    actorPersonId: chaineOuNulle(valeur, 'actor_person_id'),
    actorServiceAccountId: chaineOuNulle(valeur, 'actor_service_account_id'),
    correlationToken: chaineOuNulle(valeur, 'correlation_token'),
    retentionUntil: exigerChaine(valeur, 'retention_until'),
  };
}

export function validerLeJournalDAudit(valeur: unknown): ReponseDuJournalDAudit {
  if (!estObjet(valeur)) {
    throw new TypeError('journal d’audit : charge utile non objet');
  }
  const brut = valeur['evenements'];
  if (!Array.isArray(brut)) {
    //  Un tableau absent n'est pas un tableau vide — meme discipline que le
    //  suivi de l'onboarding et le catalogue des taches.
    throw new TypeError('journal d’audit : « evenements » n’est pas un tableau');
  }
  return {
    evenements: brut.map((e, rang) => validerUnEvenementDAudit(e, rang)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}
