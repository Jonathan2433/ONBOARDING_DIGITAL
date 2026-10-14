/**
 * Le contrat de l'écriture back-office sur un collaborateur — LOT 9, `T14`.
 *
 * TROIS GESTES, UN SEUL FICHIER — LA CRÉATION, LE CHANGEMENT D'ENTITÉ, LE TRANSFERT EN MASSE
 *
 *   `POST …/people` (`T2`), `POST …/people/{appartenance}/changement-d-entite` (`T3`)
 *   et `POST …/people/transferts-en-masse{,/apercu}` (`T11`) existent depuis le
 *   début du lot sans aucun écran consommateur — même situation que le
 *   catalogue des tâches au LOT 7 (`T4` pose, `T14` consomme). `T14` est le
 *   premier écran à les appeler, et pose donc leur SEUL module de contrat.
 *
 * `ROLES_ECRITURE` EST UNE GARDE DE ROUTE, PAS LE PÉRIMÈTRE FIN
 *
 *   Les cinq rôles ouvrent le FORMULAIRE ; la cible précise (un DSM crée pour
 *   lui-même, un Booster dans son cercle sans DSM) est résolue par
 *   `resoudre_l_autorisation_de_creation` côté API, jamais recalculée ici —
 *   règle 5, l'API est l'autorité finale. Ce module sert à ne pas proposer un
 *   formulaire à qui n'a AUCUN droit d'écriture nulle part.
 *
 * LE TRANSFERT EN MASSE RENVOIE LA MÊME FORME DE RÉSULTAT QUE LE TRANSFERT UNITAIRE,
 * ÉLÉMENT PAR ÉLÉMENT
 *
 *   `ElementDeTransfertEnMasse` porte EXACTEMENT le corps d'un changement
 *   d'entité unitaire, plus sa propre cible (`appartenance` remplace le
 *   paramètre de chemin de `T3`) — jamais une seconde forme de requête.
 *   `ResultatDeTransfert` porte les mêmes champs qu'un changement réussi,
 *   TOUS rendus facultatifs : un élément en échec ne porte que `succes: false`,
 *   `codeErreur` et `messageErreur` — les deux formes ne se devinent pas,
 *   §7.0 quatrième proposition, même leçon que `cycleDeVie.ts`.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/**
 * Les rôles qui ouvrent la création, le changement d'entité et le transfert
 * en masse d'un collaborateur — LUS DU MANIFESTE, JAMAIS RÉÉCRITS (`DEC-492`).
 */
export const ROLES_ECRITURE: readonly string[] = CONTRAT_API.rolesEcriture;

/** Le chemin de création d'un collaborateur, lu du manifeste. */
export const GABARIT_CHEMIN_CREATION_DE_COLLABORATEUR: string = endpoint(
  'creationDUnCollaborateur',
).chemin;
export const CODES_CREATION_DE_COLLABORATEUR: readonly number[] = endpoint(
  'creationDUnCollaborateur',
).codesExploitables;

/** Le gabarit du changement d'entité, ses DEUX segments. */
export const GABARIT_CHEMIN_CHANGEMENT_D_ENTITE: string = endpoint('changementDEntite').chemin;
export const CODES_CHANGEMENT_D_ENTITE: readonly number[] =
  endpoint('changementDEntite').codesExploitables;

export const GABARIT_CHEMIN_TRANSFERT_EN_MASSE: string = endpoint('transfertEnMasse').chemin;
export const CODES_TRANSFERT_EN_MASSE: readonly number[] =
  endpoint('transfertEnMasse').codesExploitables;

export const GABARIT_CHEMIN_APERCU_DU_TRANSFERT: string = endpoint(
  'previsualisationDuTransfertEnMasse',
).chemin;
export const CODES_APERCU_DU_TRANSFERT: readonly number[] = endpoint(
  'previsualisationDuTransfertEnMasse',
).codesExploitables;

export function peutEcrireSurUnCollaborateur(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_ECRITURE.includes(role));
}

export function cheminCreationDeCollaborateur(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_CREATION_DE_COLLABORATEUR.replace('{code}', encodeURIComponent(code));
}

export function cheminChangementDEntite(code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource.
    throw new TypeError('code d’entite ou identifiant d’appartenance vide');
  }
  return GABARIT_CHEMIN_CHANGEMENT_D_ENTITE.replace('{code}', encodeURIComponent(code)).replace(
    '{appartenance}',
    encodeURIComponent(appartenance),
  );
}

export function cheminTransfertEnMasse(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_TRANSFERT_EN_MASSE.replace('{code}', encodeURIComponent(code));
}

export function cheminApercuDuTransfertEnMasse(code: string): string {
  if (code === '') {
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_APERCU_DU_TRANSFERT.replace('{code}', encodeURIComponent(code));
}

/**
 * Le corps de `POST …/people` — `T2`. Les champs RESTENT en snake_case, le
 * format que l'API attend ; seules les RÉPONSES validées passent en camelCase
 * (voir l'en-tête de `index.ts`).
 *
 * `professional_category` N'EST PAS UN CHAMP : elle vaut TOUJOURS `consultant`
 * côté service, la catégorie `dg` exigeant un geste séparé non exposé par
 * cette route (`attribuer_la_categorie_dg`).
 */
export interface DemandeDeCreationDeCollaborateur {
  readonly email: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nom_prefere?: string;
  readonly date_d_arrivee: string;
  readonly metier: string;
  readonly statut: 'mission' | 'intercontract';
  readonly client?: string | null;
  readonly dsm?: string | null;
  readonly cercle_principal: string;
}

/** Ce que `POST …/people` rend — `T2`. */
export interface CollaborateurCree {
  readonly appartenance: string;
  readonly version: number;
}

/**
 * Le corps commun au changement d'entité unitaire (`T3`) et à CHAQUE élément
 * du transfert en masse (`T11`) — c'est le MÊME geste, répété.
 */
export interface DemandeDeChangementDEntite {
  readonly version: number;
  readonly entite_destination: string;
  readonly date_d_arrivee: string;
  readonly metier: string;
  readonly statut: 'mission' | 'intercontract';
  readonly client?: string | null;
  readonly dsm?: string | null;
  readonly cercle_principal: string;
}

/** Un élément du transfert en masse — la cible remplace le paramètre de chemin de `T3`. */
export interface ElementDeTransfertEnMasse extends DemandeDeChangementDEntite {
  readonly appartenance: string;
}

/** Le corps de `POST …/people/transferts-en-masse{,/apercu}` — au plus 100 éléments. */
export interface DemandeDeTransfertEnMasse {
  readonly elements: readonly ElementDeTransfertEnMasse[];
}

/** Ce qu'un changement d'entité (réussi) rend — `T3`, et chaque élément réussi du transfert. */
export interface ChangementDEntite {
  readonly nouvelleAppartenance: string;
  readonly version: number;
  readonly etatPrecedent: string;
  readonly sessionsRevoquees: number;
  readonly liensInvalides: number;
  readonly relationsClosees: Readonly<Record<string, number>>;
  readonly parcoursOnboardingArchive: string | null;
}

/** Un résultat du transfert en masse, réussi OU en échec — jamais les deux formes devinées. */
export interface ResultatDeTransfert {
  readonly appartenance: string;
  readonly succes: boolean;
  readonly nouvelleAppartenance: string | null;
  readonly version: number | null;
  readonly etatPrecedent: string | null;
  readonly sessionsRevoquees: number | null;
  readonly liensInvalides: number | null;
  readonly relationsClosees: Readonly<Record<string, number>> | null;
  readonly parcoursOnboardingArchive: string | null;
  readonly codeErreur: string | null;
  readonly messageErreur: string | null;
}

export interface ReponseDeTransfertEnMasse {
  readonly resultats: readonly ResultatDeTransfert[];
  readonly total: number;
  readonly reussites: number;
  readonly echecs: number;
}

function exigerEntier(valeur: Record<string, unknown>, champ: string): number {
  const brut = valeur[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`champ « ${champ} » absent ou non entier`);
  }
  return brut;
}

/** `relations_closes` : un compte par table, refusé dès qu'une valeur n'est pas un entier. */
function comptesParTable(valeur: unknown, cle: string): Readonly<Record<string, number>> {
  if (!estObjet(valeur)) {
    throw new TypeError(`« ${cle} » n’est pas un objet`);
  }
  const comptes: Record<string, number> = {};
  for (const [table, compte] of Object.entries(valeur)) {
    if (typeof compte !== 'number' || !Number.isInteger(compte)) {
      throw new TypeError(`${cle}.${table} n’est pas un entier`);
    }
    comptes[table] = compte;
  }
  return comptes;
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

/** Valider ce que `POST …/people` a rendu. */
export function validerLeCollaborateurCree(valeur: unknown): CollaborateurCree {
  if (!estObjet(valeur)) {
    throw new TypeError('collaborateur cree : charge utile non objet');
  }
  return {
    appartenance: exigerChaine(valeur, 'appartenance'),
    version: exigerEntier(valeur, 'version'),
  };
}

/** Valider ce qu'un changement d'entite (unitaire, toujours reussi) a rendu. */
export function validerLeChangementDEntite(valeur: unknown): ChangementDEntite {
  if (!estObjet(valeur)) {
    throw new TypeError('changement d’entite : charge utile non objet');
  }
  return {
    nouvelleAppartenance: exigerChaine(valeur, 'nouvelle_appartenance'),
    version: exigerEntier(valeur, 'version'),
    etatPrecedent: exigerChaine(valeur, 'etat_precedent'),
    sessionsRevoquees: exigerEntier(valeur, 'sessions_revoquees'),
    liensInvalides: exigerEntier(valeur, 'liens_invalides'),
    relationsClosees: comptesParTable(valeur['relations_closes'], 'relations_closes'),
    parcoursOnboardingArchive: chaineOuNulle(valeur, 'parcours_onboarding_archive'),
  };
}

function validerUnResultatDeTransfert(valeur: unknown, rang: number): ResultatDeTransfert {
  if (!estObjet(valeur)) {
    throw new TypeError(`resultats[${String(rang)}] : charge utile non objet`);
  }
  const succes = valeur['succes'];
  if (typeof succes !== 'boolean') {
    throw new TypeError(`resultats[${String(rang)}].succes absent ou non booleen`);
  }
  const entierOuNul = (champ: string): number | null => {
    const brut = valeur[champ];
    if (brut === null || brut === undefined) {
      return null;
    }
    if (typeof brut !== 'number' || !Number.isInteger(brut)) {
      throw new TypeError(`resultats[${String(rang)}].${champ} ni entier ni null`);
    }
    return brut;
  };
  return {
    appartenance: exigerChaine(valeur, 'appartenance'),
    succes,
    nouvelleAppartenance: chaineOuNulle(valeur, 'nouvelle_appartenance'),
    version: entierOuNul('version'),
    etatPrecedent: chaineOuNulle(valeur, 'etat_precedent'),
    sessionsRevoquees: entierOuNul('sessions_revoquees'),
    liensInvalides: entierOuNul('liens_invalides'),
    relationsClosees:
      valeur['relations_closes'] === null || valeur['relations_closes'] === undefined
        ? null
        : comptesParTable(
            valeur['relations_closes'],
            `resultats[${String(rang)}].relations_closes`,
          ),
    parcoursOnboardingArchive: chaineOuNulle(valeur, 'parcours_onboarding_archive'),
    codeErreur: chaineOuNulle(valeur, 'code_erreur'),
    messageErreur: chaineOuNulle(valeur, 'message_erreur'),
  };
}

/** Valider ce que le transfert en masse (execution OU apercu) a rendu. */
export function validerLeTransfertEnMasse(valeur: unknown): ReponseDeTransfertEnMasse {
  if (!estObjet(valeur)) {
    throw new TypeError('transfert en masse : charge utile non objet');
  }
  const resultats = valeur['resultats'];
  if (!Array.isArray(resultats)) {
    throw new TypeError('champ « resultats » absent ou non tableau');
  }
  return {
    resultats: resultats.map((r, rang) => validerUnResultatDeTransfert(r, rang)),
    total: exigerEntier(valeur, 'total'),
    reussites: exigerEntier(valeur, 'reussites'),
    echecs: exigerEntier(valeur, 'echecs'),
  };
}
