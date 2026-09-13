/**
 * Le contrat du cycle de vie d'un profil — story `MVP-L05-US007`.
 *
 * LOT 5, sous-etape `T11`, seconde partie. L'API le sert depuis `T8` ; aucun
 * ecran ne l'appelait.
 *
 * LE FRONTEND N'EST PAS L'AUTORITE, ET LA MATRICE L'ECRIT
 *
 *   « Le frontend peut masquer ou afficher les **actions** pour ameliorer
 *   l'experience, mais l'API reste l'autorite finale. » `ROLES_DU_CYCLE_DE_VIE`
 *   sert donc a ne pas proposer un bouton dont on sait qu'il sera refuse -- il ne
 *   decide rien, et un appelant qui contournerait l'ecran serait refuse par
 *   `resoudre_le_cycle_de_vie`.
 *
 * TROIS ROLES, LES MEMES QUE L'ADMINISTRATION — ET C'EST UNE COINCIDENCE
 *
 *   `rolesAdministration` vient du §20 de la matrice, « Roles, responsabilites et
 *   comptes administrateurs ». Cette liste-ci vient des **trois lignes
 *   d'archivage du §6.1**, qui mettent `DSM` et `BOOST` a **tiret** alors que les
 *   deux MODIFIENT un profil -- le §6.2 le redit en mots, et `T8` l'a mesure :
 *   reutiliser la grille de l'ecriture aurait **elargi un droit**.
 *
 *   Les fusionner parce qu'elles coincident aujourd'hui ferait suivre l'une quand
 *   l'autre change, **en silence**. Elles sont deux cles du manifeste, et un test
 *   Python confronte celle-ci a `ROLES_DU_CYCLE_DE_VIE` de
 *   `app/permissions/perimetre.py`.
 *
 * DEUX ACTIONS, ET LEURS REFUS NE SE RESSEMBLENT PAS
 *
 *   `403` : le role ne donne pas l'action. `404` : quatre causes indistinguables
 *   a dessein, dont « hors de ton perimetre ». `409` : **l'etat** ne permet pas
 *   la transition -- archiver un profil deja archive, restaurer un profil actif.
 *   Le §23.2 le veut ainsi : une interdiction liee a la RESSOURCE prevaut sur le
 *   cumul des roles, si bien qu'un `SUPER` recoit `409` comme tout le monde.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/**
 * Les roles qui archivent et restaurent — §6.1, les trois lignes d'archivage.
 *
 * **LUE DU MANIFESTE, JAMAIS REECRITE.** C'est la parade de `DEC-492` : une
 * seconde liste en TypeScript et une premiere en Python divergeraient au premier
 * changement, et rien ne le dirait.
 */
export const ROLES_DU_CYCLE_DE_VIE: readonly string[] = CONTRAT_API.rolesCycleDeVie;

/** Le gabarit de chaque chemin, lu du manifeste. */
export const GABARIT_CHEMIN_ARCHIVAGE: string = endpoint('archivageDUnProfil').chemin;
export const GABARIT_CHEMIN_RESTAURATION: string = endpoint('restaurationDUnProfil').chemin;
export const GABARIT_CHEMIN_FICHE_ARCHIVEE: string = endpoint('ficheArchivee').chemin;

/** Les codes exploitables — le `409` est ce qui distingue ces deux actions d'une lecture. */
export const CODES_ARCHIVAGE: readonly number[] = endpoint('archivageDUnProfil').codesExploitables;
export const CODES_RESTAURATION: readonly number[] =
  endpoint('restaurationDUnProfil').codesExploitables;
export const CODES_FICHE_ARCHIVEE: readonly number[] = endpoint('ficheArchivee').codesExploitables;

/**
 * L'appelant peut-il se voir PROPOSER les actions du cycle de vie ?
 *
 * **« PROPOSER », ET NON « FAIRE ».** Rendre `true` n'accorde rien : l'API refuse
 * de son cote, et `make profil-check` le prouve avec un DSM qui ecrit dans son
 * perimetre et se voit refuser l'archivage.
 */
export function peutGererLeCycleDeVie(roles: readonly string[]): boolean {
  return roles.some((role) => ROLES_DU_CYCLE_DE_VIE.includes(role));
}

/** Le chemin d'une action, ses DEUX segments encodes. */
function chemin(gabarit: string, code: string, appartenance: string): string {
  if (code === '' || appartenance === '') {
    //  Sans cette garde, le chemin obtenu designerait une autre ressource —
    //  potentiellement une ACTION sur une autre cible.
    throw new TypeError('code d’entite ou identifiant d’appartenance vide');
  }
  return gabarit
    .replace('{code}', encodeURIComponent(code))
    .replace('{appartenance}', encodeURIComponent(appartenance));
}

export function cheminArchivage(code: string, appartenance: string): string {
  return chemin(GABARIT_CHEMIN_ARCHIVAGE, code, appartenance);
}

export function cheminRestauration(code: string, appartenance: string): string {
  return chemin(GABARIT_CHEMIN_RESTAURATION, code, appartenance);
}

export function cheminFicheArchivee(code: string, appartenance: string): string {
  return chemin(GABARIT_CHEMIN_FICHE_ARCHIVEE, code, appartenance);
}

/**
 * Ce qu'une action rend.
 *
 * **LES DEUX REPONSES N'ONT PAS LA MEME FORME, ET C'EST MESURE.** Ma premiere
 * version en inventait une commune : le validateur exigeait
 * `relations_a_redonner` sur les deux, or **l'archivage ne le porte pas**. Un
 * archivage reussi etait donc rejete par le validateur, et l'ecran affichait
 * « l'action n'a pas pu aboutir » sur un `200`. Defaut `T11-7`, trouve sur la
 * pile reelle -- aucun test bouchonne ne pouvait le dire.
 *
 * Mesure du 12/09/2026, sur la pile :
 *
 *     archivage     version, etat_precedent, etat_nouveau, sessions_revoquees,
 *                   liens_invalides, relations_closes, consultants_sans_dsm,
 *                   roles_globaux_conserves, relations_futures_conservees
 *     restauration  version, etat_precedent, etat_nouveau, relations_a_redonner
 *
 * **TROIS CHAMPS SONT COMMUNS, ET LE RESTE DEPEND DE L'ACTION.** Le validateur
 * prend donc l'action en argument plutot que de deviner : deviner reviendrait a
 * accepter une reponse d'archivage a la place d'une restauration, ce qu'aucun
 * test n'attraperait.
 */
export interface ResultatDuCycleDeVie {
  readonly version: number;
  readonly etatPrecedent: string;
  readonly etatNouveau: string;
  /**
   * **RESTAURATION SEULEMENT** : ce que `T8` a delibere de NE PAS rouvrir.
   *
   * Rouvrir d'anciennes valeurs serait **decider a nouveau** (§23.4) et
   * fabriquerait une trace d'audit fausse. La restauration NOMME donc ce qui
   * manque. Vide sur un archivage, qui ne laisse rien a redonner.
   */
  readonly relationsARedonner: readonly string[];
  /**
   * **ARCHIVAGE SEULEMENT** : ce qui a ete CLOS, par table et par nombre.
   *
   * L'annoncer avant le geste est une promesse ; le montrer apres est une
   * mesure. Vide sur une restauration.
   */
  readonly relationsCloses: Readonly<Record<string, number>>;
  /** **ARCHIVAGE SEULEMENT** : le nombre de sessions revoquees. `0` ailleurs. */
  readonly sessionsRevoquees: number;
}

/** Les comptes par table, refuses des qu'une valeur n'est pas un entier. */
function comptesParTable(valeur: unknown, cle: string): Readonly<Record<string, number>> {
  if (!estObjet(valeur)) {
    throw new TypeError(`cycle de vie : « ${cle} » n’est pas un objet`);
  }
  const comptes: Record<string, number> = {};
  for (const [table, compte] of Object.entries(valeur)) {
    if (typeof compte !== 'number' || !Number.isInteger(compte)) {
      throw new TypeError(`cycle de vie : ${cle}.${table} n’est pas un entier`);
    }
    comptes[table] = compte;
  }
  return comptes;
}

/**
 * Valider ce qu'une action du cycle de vie a rendu.
 *
 * **L'ACTION EST UN ARGUMENT, ET NON UNE DEVINETTE.** Les deux reponses ne
 * portent pas les memes champs : deviner reviendrait a accepter une reponse
 * d'archivage la ou l'on attend une restauration, ce qu'aucun test
 * n'attraperait. Defaut `T11-7`.
 *
 * **LES TROIS CHAMPS COMMUNS SONT EXIGES**, et les deux etats parce que c'est ce
 * qui rend le resultat lisible : sans le precedent, l'ecran ne peut pas dire
 * « de `active` a `archived` », et `T8` a montre que le chemin compte -- `Active`
 * passe par `Departed`, le §24.1 n'ayant aucune transition directe.
 */
export function validerLeResultat(
  valeur: unknown,
  action: 'archivage' | 'restauration',
): ResultatDuCycleDeVie {
  if (!estObjet(valeur)) {
    throw new TypeError('cycle de vie : charge utile non objet');
  }
  const version = valeur['version'];
  if (typeof version !== 'number' || !Number.isInteger(version)) {
    throw new TypeError('cycle de vie : « version » n’est pas un entier');
  }

  let relationsARedonner: readonly string[] = [];
  let relationsCloses: Readonly<Record<string, number>> = {};
  let sessionsRevoquees = 0;

  if (action === 'restauration') {
    const relations = valeur['relations_a_redonner'];
    if (!Array.isArray(relations)) {
      //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
      //  ferait afficher « rien a redonner » sur une reponse qui n'en disait
      //  rien — §7.0, quatrieme proposition.
      throw new TypeError('cycle de vie : « relations_a_redonner » n’est pas un tableau');
    }
    relationsARedonner = relations.map((nom, rang) => {
      if (typeof nom !== 'string') {
        throw new TypeError(`cycle de vie : relations_a_redonner[${String(rang)}] non textuel`);
      }
      return nom;
    });
  } else {
    relationsCloses = comptesParTable(valeur['relations_closes'], 'relations_closes');
    const sessions = valeur['sessions_revoquees'];
    if (typeof sessions !== 'number' || !Number.isInteger(sessions)) {
      throw new TypeError('cycle de vie : « sessions_revoquees » n’est pas un entier');
    }
    sessionsRevoquees = sessions;
  }

  return {
    version,
    etatPrecedent: exigerChaine(valeur, 'etat_precedent'),
    etatNouveau: exigerChaine(valeur, 'etat_nouveau'),
    relationsARedonner,
    relationsCloses,
    sessionsRevoquees,
  };
}
