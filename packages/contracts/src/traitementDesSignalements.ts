/**
 * Le traitement des signalements — LOT 10, `T12` (API), `T15` (premier
 * écran), `MVP-L10-US006`.
 *
 * DÉCLARÉ SÉPARÉMENT DE `signalement.ts`
 *
 *   `signalement.ts` (LOT 10, `T11`) porte la SEULE écriture ouverte à toute
 *   session — « Reporter un bug ». Ce module porte la LECTURE périmétrée,
 *   l'historique et le changement d'état, réservés à `ADM-E`/`SUPER`
 *   (`rolesTraitementDesSignalements`) — deux publics, deux modules, même
 *   discipline que `contenus.ts`/`gestionDuContenu.ts` au LOT 6.
 *
 * QUATRE CHAMPS TECHNIQUES, NULS SI LA LECTURE EST SEULEMENT FONCTIONNELLE
 *
 *   L'ESM lisant un signalement d'autrui (`ENTITE_FONCTIONNELLE`, matrice
 *   §17) reçoit `versionApplication`/`environnement`/`resumeNavigateur`/
 *   `jetonDeCorrelation` à `null` — jamais absents. `Soi` et `ENTITE_
 *   COMPLETE`/`GLOBAL` les reçoivent toujours renseignés.
 *
 * AUCUNE TRANSITION N'EST RESTREINTE CÔTÉ CONTRAT
 *
 *   Le modèle ne porte aucun diagramme d'état pour `bug_report` : les
 *   quatre états sont tous proposables depuis n'importe lequel. C'est
 *   l'API, jamais ce module, qui ferait foi si cela changeait.
 */
import { CONTRAT_API, endpoint } from './sante.js';
import { estObjet, exigerChaine } from './formes.js';

export const ROLES_TRAITEMENT_DES_SIGNALEMENTS: readonly string[] =
  CONTRAT_API.rolesTraitementDesSignalements;

export function peutTraiterLesSignalements(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_TRAITEMENT_DES_SIGNALEMENTS.includes(role));
}

/** Les quatre états du cahier §9.6 — `new`/`investigating`/`fixed`/`rejected`. */
export const ETATS_DE_SIGNALEMENT = ['new', 'investigating', 'fixed', 'rejected'] as const;
export type EtatDeSignalement = (typeof ETATS_DE_SIGNALEMENT)[number];

export const GABARIT_CHEMIN_SIGNALEMENTS: string = endpoint('signalements').chemin;
export const CODES_SIGNALEMENTS: readonly number[] = endpoint('signalements').codesExploitables;
export const GABARIT_CHEMIN_HISTORIQUE_SIGNALEMENT: string = endpoint(
  'historiqueDUnSignalement',
).chemin;
export const CODES_HISTORIQUE_SIGNALEMENT: readonly number[] = endpoint(
  'historiqueDUnSignalement',
).codesExploitables;
export const GABARIT_CHEMIN_CHANGEMENT_D_ETAT_SIGNALEMENT: string = endpoint(
  'changementDEtatDUnSignalement',
).chemin;
export const CODES_CHANGEMENT_D_ETAT_SIGNALEMENT: readonly number[] = endpoint(
  'changementDEtatDUnSignalement',
).codesExploitables;

export function cheminSignalements(
  code: string,
  page: number,
  taille: number,
  etat?: EtatDeSignalement,
): string {
  if (code === '') {
    throw new TypeError('code d’entité vide');
  }
  const parametres = [
    `page=${encodeURIComponent(String(page))}`,
    `taille=${encodeURIComponent(String(taille))}`,
  ];
  if (etat !== undefined) {
    parametres.push(`etat=${encodeURIComponent(etat)}`);
  }
  return `${GABARIT_CHEMIN_SIGNALEMENTS.replace('{code}', encodeURIComponent(code))}?${parametres.join('&')}`;
}

export function cheminHistoriqueSignalement(code: string, signalement: string): string {
  if (code === '' || signalement === '') {
    throw new TypeError('code d’entité ou identifiant de signalement vide');
  }
  return GABARIT_CHEMIN_HISTORIQUE_SIGNALEMENT.replace('{code}', encodeURIComponent(code)).replace(
    '{signalement}',
    encodeURIComponent(signalement),
  );
}

export function cheminChangementDEtatSignalement(code: string, signalement: string): string {
  if (code === '' || signalement === '') {
    throw new TypeError('code d’entité ou identifiant de signalement vide');
  }
  return GABARIT_CHEMIN_CHANGEMENT_D_ETAT_SIGNALEMENT.replace(
    '{code}',
    encodeURIComponent(code),
  ).replace('{signalement}', encodeURIComponent(signalement));
}

export interface LigneDeSignalement {
  readonly identifiant: string;
  readonly etat: string;
  readonly description: string;
  readonly etapesDeReproduction: string | null;
  readonly cheminDePage: string;
  readonly entiteId: string;
  readonly rapporteurId: string;
  readonly creeLe: string;
  readonly version: number;
  readonly versionApplication: string | null;
  readonly environnement: string | null;
  readonly resumeNavigateur: string | null;
  readonly jetonDeCorrelation: string | null;
}

export interface ReponseDesSignalements {
  readonly signalements: readonly LigneDeSignalement[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

export interface EvenementDHistoriqueSignalement {
  readonly survenuLe: string;
  readonly ancienEtat: string | null;
  readonly nouvelEtat: string | null;
  readonly commentaire: string | null;
  readonly acteurId: string | null;
}

export interface ReponseDeLHistoriqueSignalement {
  readonly evenements: readonly EvenementDHistoriqueSignalement[];
}

/** Ce qu'un écran ENVOIE — `snake_case` voulu, c'est ce que l'API attend. */
export interface DemandeDeChangementDEtatSignalement {
  readonly nouvel_etat: EtatDeSignalement;
  readonly version: number;
  readonly commentaire?: string;
}

export interface ReponseDeChangementDEtatSignalement {
  readonly etat: string;
  readonly version: number;
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

function validerUneLigneDeSignalement(valeur: unknown, rang: number): LigneDeSignalement {
  if (!estObjet(valeur)) {
    throw new TypeError(`signalements : signalements[${String(rang)}] non objet`);
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    etat: exigerChaine(valeur, 'etat'),
    description: exigerChaine(valeur, 'description'),
    etapesDeReproduction: chaineOuNulle(valeur, 'etapes_de_reproduction'),
    cheminDePage: exigerChaine(valeur, 'chemin_de_page'),
    entiteId: exigerChaine(valeur, 'entite_id'),
    rapporteurId: exigerChaine(valeur, 'rapporteur_id'),
    creeLe: exigerChaine(valeur, 'cree_le'),
    version: entier(valeur, 'version'),
    versionApplication: chaineOuNulle(valeur, 'version_application'),
    environnement: chaineOuNulle(valeur, 'environnement'),
    resumeNavigateur: chaineOuNulle(valeur, 'resume_navigateur'),
    jetonDeCorrelation: chaineOuNulle(valeur, 'jeton_de_correlation'),
  };
}

export function validerLesSignalements(valeur: unknown): ReponseDesSignalements {
  if (!estObjet(valeur)) {
    throw new TypeError('signalements : charge utile non objet');
  }
  const brut = valeur['signalements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('signalements : « signalements » n’est pas un tableau');
  }
  return {
    signalements: brut.map((s, rang) => validerUneLigneDeSignalement(s, rang)),
    page: entier(valeur, 'page'),
    taille: entier(valeur, 'taille'),
    total: entier(valeur, 'total'),
    pages: entier(valeur, 'pages'),
  };
}

function validerUnEvenementDHistoriqueSignalement(
  valeur: unknown,
  rang: number,
): EvenementDHistoriqueSignalement {
  if (!estObjet(valeur)) {
    throw new TypeError(`historique : evenements[${String(rang)}] non objet`);
  }
  return {
    survenuLe: exigerChaine(valeur, 'survenu_le'),
    ancienEtat: chaineOuNulle(valeur, 'ancien_etat'),
    nouvelEtat: chaineOuNulle(valeur, 'nouvel_etat'),
    commentaire: chaineOuNulle(valeur, 'commentaire'),
    acteurId: chaineOuNulle(valeur, 'acteur_id'),
  };
}

export function validerLHistoriqueSignalement(valeur: unknown): ReponseDeLHistoriqueSignalement {
  if (!estObjet(valeur)) {
    throw new TypeError('historique : charge utile non objet');
  }
  const brut = valeur['evenements'];
  if (!Array.isArray(brut)) {
    throw new TypeError('historique : « evenements » n’est pas un tableau');
  }
  return { evenements: brut.map((e, rang) => validerUnEvenementDHistoriqueSignalement(e, rang)) };
}

export function validerLeChangementDEtatSignalement(
  valeur: unknown,
): ReponseDeChangementDEtatSignalement {
  if (!estObjet(valeur)) {
    throw new TypeError('changement d’état : charge utile non objet');
  }
  return { etat: exigerChaine(valeur, 'etat'), version: entier(valeur, 'version') };
}
