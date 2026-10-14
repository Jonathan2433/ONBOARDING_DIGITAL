/**
 * La création d'une entité depuis des modèles génériques — LOT 9, `T12` (API)
 * puis `T14` (écran), `MVP-L09-US007`.
 *
 * `SUPER` SEUL, ET CE N'EST PAS UNE GRILLE DE PLUSIEURS RÔLES
 *
 *   `_exiger_le_super_administrateur` (`app/entities/routes.py`) n'est pas un
 *   `frozenset[RoleDeLaMatrice]` comme les autres gardes de ce lot : c'est une
 *   fonction dédiée qui résout le rôle TECHNIQUE global `SUPER_ADMIN`, cahier
 *   §21. Une seule valeur ne justifie pas une clé de manifeste de plus — le
 *   littéral `'SUPER'` est le même que celui déjà employé partout dans ce
 *   dépôt (`RoleDeLaMatrice.SUPER_ADMINISTRATEUR = "SUPER"`), et le comporte-
 *   ment réel reste éprouvé par les tests Python de `T12` (`test_creation_
 *   entite.py`), pas par une confrontation de liste.
 *
 * L'ENTITÉ NAÎT VIERGE, ET LE PREMIER ADMINISTRATEUR EST UNE PERSONNE EXISTANTE
 *
 *   Double arbitrage de Jonathan (`T12`) : aucun contenu, aucune responsabilité
 *   Framework, aucun modèle d'onboarding n'est semé — l'onboarding « générique »
 *   vient déjà de la résolution `GLOBAL` (LOT 7). `premier_administrateur`
 *   désigne une personne DÉJÀ CONNUE (son identifiant), jamais une création en
 *   un seul geste : ce formulaire n'invente donc pas de second mini-formulaire
 *   de collaborateur — l'écran demande l'identifiant, obtenu par ailleurs
 *   (trombinoscope d'une autre entité, ou communiqué hors écran).
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

export const ROLE_SUPER_ADMINISTRATEUR = 'SUPER';

export function peutCreerUneEntite(roles: readonly string[] | null): boolean {
  return roles !== null && roles.includes(ROLE_SUPER_ADMINISTRATEUR);
}

export const CHEMIN_CREATION_D_ENTITE: string = endpoint('creationDUneEntite').chemin;
export const CODES_CREATION_D_ENTITE: readonly number[] =
  endpoint('creationDUneEntite').codesExploitables;

/** Le corps de `POST /entities` — `extra="forbid"` côté API, aucun champ de plus toléré. */
export interface DemandeDeCreationDEntite {
  readonly code: string;
  readonly nom: string;
  readonly ville: string;
  /** ISO 3166-1 alpha-2, deux lettres. */
  readonly pays: string;
  /** Fuseau IANA, ex. `Europe/Paris`. */
  readonly fuseau: string;
  readonly premier_administrateur: string;
}

export interface EntiteCreee {
  readonly id: string;
  readonly code: string;
  readonly version: number;
}

export function validerLEntiteCreee(valeur: unknown): EntiteCreee {
  if (!estObjet(valeur)) {
    throw new TypeError('entite creee : charge utile non objet');
  }
  const version = valeur['version'];
  if (typeof version !== 'number' || !Number.isInteger(version)) {
    throw new TypeError('champ « version » absent ou non entier');
  }
  return {
    id: exigerChaine(valeur, 'id'),
    code: exigerChaine(valeur, 'code'),
    version,
  };
}
