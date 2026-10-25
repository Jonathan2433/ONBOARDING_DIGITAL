/**
 * Le contrat du signalement d'un bug — story `MVP-L10-US005`.
 *
 * LOT 10, sous-etape `T11`. Cahier §9.6/§10.12, matrice §17 « Reporter un bug ».
 *
 * AUCUN CODE D'ENTITE DANS LE CHEMIN, ET C'EST DELIBERE
 *
 *   Toutes les autres routes d'ecriture du depot portent `{code}` : celle-ci
 *   est la premiere a ne pas en avoir. Le cahier §9.6 cite en demonstration
 *   « creation d'un signalement depuis une page d'erreur », et une page
 *   d'erreur du fourre-tout (`/n'importe-quoi`) n'a structurellement AUCUNE
 *   entite dans son adresse. L'API resout toujours l'entite PRINCIPALE du
 *   rapporteur — voir `app/support/routes.py` pour le raisonnement complet et
 *   sa limite documentee (une entite ETRANGERE consultee n'est jamais
 *   attachee). Ce module n'a donc aucune fonction `cheminSignalement(code)` a
 *   parametrer : le chemin est une CONSTANTE.
 *
 * TROIS CHAMPS SEULEMENT SONT ENVOYES
 *
 *   `application_version`, `environment` et `browser_summary` sont ajoutes
 *   AUTOMATIQUEMENT par le serveur (modele §21.4, cahier §10.12) — jamais
 *   soumis par l'ecran, qui n'a donc rien a lire de `sante.ts` pour les
 *   renseigner.
 */
import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le chemin du signalement — une CONSTANTE, voir l'en-tete. */
export const CHEMIN_SIGNALEMENT: string = endpoint('signalerUnBug').chemin;

/** Les codes qu'il faut savoir exploiter. */
export const CODES_SIGNALEMENT: readonly number[] = endpoint('signalerUnBug').codesExploitables;

/** Ce qu'un ecran ENVOIE — `snake_case` voulu, c'est ce que l'API attend. */
export interface DemandeDeSignalement {
  readonly description: string;
  readonly etapes_de_reproduction?: string;
  readonly chemin_de_page: string;
}

/** Ce que l'API rend apres creation. */
export interface SignalementServi {
  readonly identifiant: string;
  readonly etat: string;
  readonly creeLe: string;
}

export function validerUnSignalement(valeur: unknown): SignalementServi {
  if (!estObjet(valeur)) {
    throw new TypeError('signalement : charge utile non objet');
  }
  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    etat: exigerChaine(valeur, 'etat'),
    creeLe: exigerChaine(valeur, 'cree_le'),
  };
}
