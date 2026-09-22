/**
 * Le contrat des liens internes d'une entite — story `MVP-L06-US005`.
 *
 * LOT 6, sous-etape `T8`. Cahier §26 : « page d'accueil dans l'ordre valide :
 * 1. presentation de l'entite ; 2. Framework ; 3. arrivees recentes ;
 * 4. prochains evenements ; **5. liens internes** ».
 *
 * CE QUE CE MODULE PORTE, ET CE QU'IL NE PORTE PAS
 *
 *   La **lecture** seule — le chemin de l'accueil, ses codes, la forme servie et
 *   le validateur. C'est le partage que le lot suit depuis `T2` : une sous-etape
 *   qui sert une LECTURE pose son module de contrat, celles qui servent une
 *   ECRITURE ne le font pas (`T6` et `T7` n'ont rien ajoute ici). Les ecrans de
 *   lecture sont `T9`, ceux d'edition `T10`.
 *
 * QUI LIT : LA MATRICE §5, ET ELLE NOMME CETTE RESSOURCE
 *
 *   Sa ligne « Liens Hub/Academy/SharePoint » donne `—` a `ANON` et **Lecture**
 *   aux HUIT roles authentifies. Aucun role n'est donc examine, exactement comme
 *   le Framework et le trombinoscope — et lire a sa place la ligne « Consulter »
 *   de l'annexe A §13, dont le tableau n'a ni colonne `EMP` ni colonne `NEW`,
 *   refuserait la ressource a l'Employe, pour qui ce portail existe.
 *
 *   **AUCUNE LISTE DE ROLES N'EST DONC EXPORTEE ICI.** Celle de la GESTION —
 *   `ESM`, `ADM-E`, `SUPER` — vit au manifeste sous
 *   `rolesGestionDesLiensInternes`, et l'ecran d'edition de `T10` l'y lira. En
 *   exporter une dont la lecture n'a pas besoin laisserait croire que la lecture
 *   en depend.
 *
 * SEULS LES LIENS ACTIFS SONT SERVIS, ET `actif` EST QUAND MEME RENDU
 *
 *   Le modele §15.3 declare `active` **a cote** de `archived_at`, et `T1` a
 *   refuse de les fondre : on DESACTIVE un lien pour le retirer de l'affichage
 *   sans perdre sa definition, on l'ARCHIVE pour le sortir du jeu de donnees.
 *   L'accueil ne sert que les actifs ; la gestion — `…/liens/gestion` — sert les
 *   deux, faute de quoi desactiver serait un aller sans retour.
 *
 *   `actif` vaut donc toujours `true` pour cette route. Le taire obligerait
 *   l'ecran d'edition a lire une AUTRE structure, et deux structures pour une
 *   meme ressource divergent au premier ajout de colonne.
 *
 * LES URL SONT VALIDEES PAR L'API, ET LE FRONTEND N'EN EST PAS L'AUTORITE
 *
 *   `DEC-587`, `QO-120` close : `https` seul, `http` refuse sous son propre code.
 *   `PROTOCOLES_DE_LIEN_AUTORISES` est lu du manifeste pour qu'un formulaire
 *   puisse le DIRE avant que l'API ne refuse — il ne decide rien, et un appelant
 *   qui contournerait l'ecran serait refuse par `valider_une_url`, puis par la
 *   contrainte `ck_internal_link_url_https` de la migration `0019`.
 *
 *   **`urlEstServable` EXISTE POUR L'AFFICHAGE, ET NON POUR LA SECURITE.** Un
 *   ecran qui poserait une URL dans un `href` sans rien exiger dependrait
 *   entierement de la base ; celle-ci a deux etages de garde, mais une reprise du
 *   LOT 11 ou un import du LOT 9 restent des ecrivains. La verification cote
 *   client est donc une TROISIEME barriere, et le dire vaut mieux que de laisser
 *   croire qu'elle est la premiere.
 */

import { estObjet, exigerChaine } from './formes.js';
import { CONTRAT_API, endpoint } from './sante.js';

/** Le gabarit du chemin de l'accueil, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_LIENS_INTERNES: string = endpoint('liensInternesDUneEntite').chemin;

/** Les codes exploitables de la lecture. */
export const CODES_LIENS_INTERNES: readonly number[] =
  endpoint('liensInternesDUneEntite').codesExploitables;

/**
 * Les protocoles que l'API accepte — `DEC-587`, `QO-120`.
 *
 * **LUS DU MANIFESTE, JAMAIS RECOPIES.** Le modele §15.3 et le cahier §13
 * exigent « une liste de protocoles autorises » sans la donner ; la liste vit
 * donc en UN endroit, et l'elargir ne peut pas laisser derriere elle un
 * formulaire qui annonce l'ancienne (§7.27).
 */
export const PROTOCOLES_DE_LIEN_AUTORISES: readonly string[] =
  CONTRAT_API.protocolesDeLienAutorises;

/**
 * Les QUATRE types du modele §15.3.
 *
 * Le §15.3 dit « liens Hub, Academy, SharePoint ou **autres** ressources
 * internes » : `OTHER` n'est pas un ajout, c'est ce que le mot « autres » rend
 * obligatoire. Ce tableau NOMME ce que le modele nomme, et le validateur ne
 * refuse PAS un type inconnu — le fermer bloquerait un lot ulterieur, exactement
 * comme la liste blanche de scopes du LOT 3 (§7.29).
 */
export const TYPES_DE_LIEN_NOMMES = ['HUB', 'ACADEMY', 'SHAREPOINT', 'OTHER'] as const;

/** Le chemin des liens internes d'une entite, son segment encode. */
export function cheminLiensInternes(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu serait celui d'une AUTRE ressource —
    //  meme raisonnement que `cheminEntite` de `T2` du LOT 4.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_LIENS_INTERNES.replace('{code}', encodeURIComponent(code));
}

export interface LienInterne {
  readonly identifiant: string;
  readonly libelle: string;
  readonly url: string;
  readonly typeDeLien: string;
  /** §15.3 : facultative. */
  readonly description: string | null;
  /** §15.3 : facultative, et **le corpus n'en donne aucun vocabulaire**. */
  readonly referenceDIcone: string | null;
  readonly rang: number;
  readonly actif: boolean;
  readonly version: number;
}

export interface LiensInternes {
  readonly liens: readonly LienInterne[];
  readonly nombreDeLiens: number;
}

/**
 * Cette URL peut-elle etre posee dans un `href` ?
 *
 * **TROISIEME BARRIERE, ET NON LA PREMIERE** — voir l'en-tete. La liste vient du
 * manifeste ; la casse du protocole est ramenee en minuscules, exactement comme
 * le fait l'API avant d'ecrire. **Sans cela, cette fonction refuserait
 * « HTTPS://… » que l'API ACCEPTE**, et un garde-fou a faux positifs apprend a
 * passer outre (§7.25).
 *
 * Rend `false` plutot que de lever : une URL qu'un ecran refuse d'ouvrir doit
 * s'afficher **desactivee et visible**, pas faire tomber la page entiere. Une
 * exception ici ferait disparaitre les quatre liens valides a cause du
 * cinquieme.
 */
export function urlEstServable(url: string): boolean {
  //  **AUCUN `new URL(...)`, ET LE MOTIF N'EST PAS LA CONFIGURATION.** Ce paquet
  //  est compile sans la bibliotheque DOM, et l'y ajouter pour une verification
  //  ferait entrer le navigateur entier dans un contrat que l'API lit aussi.
  //  Surtout, `new URL(...)` NORMALISE — il accepterait « https:/x » en le
  //  reecrivant — la ou l'API refuse ce que l'auteur n'a pas tape exactement
  //  (`url_ambigue`). Une comparaison LITTERALE suit donc la meme regle que la
  //  contrainte `ck_internal_link_url_https` de la migration `0019`.
  const separateur = url.indexOf('://');
  if (separateur <= 0) {
    //  Ni « https:alert(1) », ni « //hote/chemin », ni « hote/chemin ». Mesure
    //  du 22/09/2026 cote API : « https:alert(1) » a bien pour protocole
    //  « https » — **une liste de protocoles ne suffit pas**, l'hote est exige.
    return false;
  }
  const protocole = url.slice(0, separateur).toLowerCase();
  //  L'hote va des deux barres obliques au premier `/`, `?` ou `#`.
  const apres = url.slice(separateur + 3);
  const hote = apres.split(/[/?#]/, 1)[0] ?? '';
  return PROTOCOLES_DE_LIEN_AUTORISES.includes(protocole) && hote !== '';
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`liens internes : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string, ou: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`liens internes : ${ou}« ${champ} » n’est pas un entier`);
  }
  return brut;
}

/** Valider ce que `GET …/liens` a rendu. */
export function validerLesLiensInternes(valeur: unknown): LiensInternes {
  if (!estObjet(valeur)) {
    throw new TypeError('liens internes : charge utile non objet');
  }

  const brutListe = valeur['liens'];
  if (!Array.isArray(brutListe)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « aucun lien » sur une reponse qui n'en disait rien — et
    //  une entite sans lien est un etat LEGITIME qu'il faut pouvoir distinguer.
    throw new TypeError('liens internes : « liens » n’est pas un tableau');
  }

  const liens = brutListe.map((brut, rang): LienInterne => {
    if (!estObjet(brut)) {
      throw new TypeError(`liens internes : liens[${String(rang)}] non objet`);
    }
    const actif = brut['actif'];
    if (typeof actif !== 'boolean') {
      throw new TypeError(`liens internes : liens[${String(rang)}].actif n’est pas un booleen`);
    }
    return {
      identifiant: exigerChaine(brut, 'identifiant'),
      libelle: exigerChaine(brut, 'libelle'),
      url: exigerChaine(brut, 'url'),
      typeDeLien: exigerChaine(brut, 'type_de_lien'),
      description: chaineOuNul(brut, 'description'),
      referenceDIcone: chaineOuNul(brut, 'reference_d_icone'),
      rang: entier(brut, 'rang', `liens[${String(rang)}].`),
      actif,
      version: entier(brut, 'version', `liens[${String(rang)}].`),
    };
  });

  const nombre = entier(valeur, 'nombre_de_liens', '');
  if (nombre !== liens.length) {
    //  **DEUX SOURCES POUR UNE MEME GRANDEUR** — §7.0, sixieme proposition.
    throw new TypeError(
      `liens internes : nombre_de_liens vaut ${String(nombre)} pour ` +
        `${String(liens.length)} lien(s) rendus`,
    );
  }

  //  **L'ORDRE EST VERIFIE, PAS RETRIE.** Retrier ici masquerait une API qui
  //  aurait cesse de trier, et l'accueil afficherait les cartes dans le desordre
  //  le jour ou le contrat serait retire (§7.35). L'ordre est TOTAL du cote de
  //  l'API, l'index unique partiel de `T1` interdisant deux rangs egaux.
  for (let i = 1; i < liens.length; i += 1) {
    const precedent = liens[i - 1];
    const courant = liens[i];
    if (precedent !== undefined && courant !== undefined && courant.rang <= precedent.rang) {
      throw new TypeError(
        `liens internes : rangs non strictement croissants — ${String(precedent.rang)} ` +
          `precede ${String(courant.rang)}`,
      );
    }
  }

  return { liens, nombreDeLiens: nombre };
}
