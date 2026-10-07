/**
 * Le contrat de l'agrégat d'accueil — LOT 8, `T8` (API) puis `T11` (écran),
 * `MVP-L08-US001` (2/2) et `MVP-L08-US006` (2/2).
 *
 * LA LECTURE SEULE, COMME `evenements.ts` AVANT SON `T10`
 *
 *   `T8` a servi cette route sans poser de module de contrat : aucun écran ne
 *   la consommait encore (`presentation`/`framework`/`arrivees_recentes`/
 *   `evenements_a_venir`/`liens_internes` restaient cinq aller-retours
 *   séparés). `T11`, premier écran consommateur, pose donc ce module — même
 *   partage que les liens internes (LOT 6, `T8`/`T10`) et les événements (LOT
 *   8, `T2`/`T9`) : une sous-étape qui sert une lecture pose son module de
 *   contrat quand un écran en a besoin.
 *
 * CE MODULE NE REVALIDE RIEN QUE SES QUATRE VOISINS VALIDENT DÉJÀ
 *
 *   `framework`, `evenements_a_venir` et `liens_internes` ont EXACTEMENT la
 *   forme que `framework.ts`/`evenements.ts`/`liens.ts` valident déjà pour
 *   leurs propres routes — les réécrire ici serait une seconde source qui
 *   diverge au premier changement de l'une des trois (§7.0, sixième
 *   proposition). `validerLAccueil` délègue donc à
 *   `validerLaPageFramework`/`validerLaPageDesEvenements`/
 *   `validerLesLiensInternes`, et ne porte en propre que `presentation`
 *   (nullable, jamais validé ailleurs comme tel) et les arrivées récentes.
 *
 * `presentation` PEUT ÊTRE `null`, ET C'EST UN ÉTAT VALIDE
 *
 *   `lire_la_page_de_contenu` rend `None` quand aucune page `HOME`/
 *   `presentation` n'existe encore pour cette entité — `app/accueil/
 *   lecture.py` le dit explicitement. Le valider comme un objet lèverait sur
 *   une entité neuve, qui n'a simplement pas encore de texte de présentation.
 *
 * `ArriveeRecente` : LA PREMIÈRE FORME DE CONTRAT POUR CETTE RESSOURCE
 *
 *   `T7` a servi `GET …/arrivees-recentes` sans poser de module de contrat —
 *   aucun écran ne la consommait encore, même partage que ci-dessus. `T11`
 *   est donc le premier consommateur, et pose la forme ici plutôt que dans
 *   un module séparé : l'agrégat d'accueil est, à ce jour, son SEUL
 *   consommateur côté écran. Le vocabulaire des champs suit EXACTEMENT celui
 *   déjà établi par `ficheArrivee.ts`/`profil.ts`/`trombinoscope.ts` pour les
 *   mêmes colonnes (`first_name` → `prenom`, `preferred_name` → `nomPrefere`,
 *   `short_intro` → `presentationCourte`, `fun_fact` → `funFact`) — une
 *   traduction distincte pour les mêmes colonnes diviserait au premier
 *   changement (§7.27).
 *
 *   **NI MÉTIER, NI STATUT, NI CERCLE, NI PHOTO** : la réponse de l'API ne
 *   les porte pas (voir l'en-tête de `app/onboarding/arrivees_recentes.py`,
 *   `T7`) — la matrice met le DSM à tiret sur ces informations ailleurs, et
 *   les exposer ici serait une porte dérobée. Ce contrat ne les valide donc
 *   pas davantage : il n'y a rien à lire.
 *
 * `arrival_date` EST UNE DATE, PAS UN INSTANT — ET RESTE UNE CHAÎNE
 *
 *   Le modèle sert un `date` SQL (`YYYY-MM-DD`), pas un `datetime`. Même
 *   discipline que partout ailleurs dans ce dépôt : aucune conversion par
 *   `Date`, la chaîne se lit par segment de position fixe (`dateComplete`,
 *   repris de `PageProfil.tsx`, fonctionne sur les deux formats puisqu'il ne
 *   lit que les dix premiers caractères).
 *
 * CINQ CLÉS TOUJOURS PRÉSENTES, SEULE `presentation` NULLABLE
 *
 *   Même discipline que `ReponseDeLAccueil` côté API (§7.0, quatrième
 *   proposition) : une section absente et une section vide ne disent pas la
 *   même chose. Le validateur exige donc les cinq clés, sans jamais
 *   substituer une valeur par défaut à une clé manquante.
 */

import { estObjet, exigerChaine } from './formes.js';
import { type PageDeContenu, validerLaPageDeContenu } from './contenus.js';
import { type PageDesEvenements, validerLaPageDesEvenements } from './evenements.js';
import { type LiensInternes, validerLesLiensInternes } from './liens.js';
import { type PageFramework, validerLaPageFramework } from './framework.js';
import { endpoint } from './sante.js';
import { TAILLES_DE_PAGE } from './trombinoscope.js';

/** Le gabarit du chemin de l'accueil, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_ACCUEIL: string = endpoint('accueilDUneEntite').chemin;

/** Les codes exploitables. Pas de `403` : la matrice §5 n'examine aucun rôle. */
export const CODES_ACCUEIL: readonly number[] = endpoint('accueilDUneEntite').codesExploitables;

/** Le chemin de l'accueil d'une entité, son segment encodé. */
export function cheminAccueil(code: string): string {
  if (code === '') {
    //  Sans cette garde, le chemin obtenu designerait la LISTE des entites.
    throw new TypeError('code d’entite vide');
  }
  return GABARIT_CHEMIN_ACCUEIL.replace('{code}', encodeURIComponent(code));
}

export interface ArriveeRecente {
  readonly appartenance: string;
  readonly personneId: string;
  readonly prenom: string;
  readonly nom: string;
  readonly nomPrefere: string | null;
  /** `YYYY-MM-DD` — une DATE, jamais un instant. Voir l'en-tete du module. */
  readonly dateArrivee: string;
  readonly presentationCourte: string | null;
  readonly funFact: string | null;
}

export interface PageDesArriveesRecentes {
  readonly arrivees: readonly ArriveeRecente[];
  readonly page: number;
  readonly taille: number;
  readonly total: number;
  readonly pages: number;
}

export interface AccueilDEntite {
  /** `null` si aucune page HOME/presentation n'existe encore — etat valide. */
  readonly presentation: PageDeContenu | null;
  readonly framework: PageFramework;
  readonly arriveesRecentes: PageDesArriveesRecentes;
  readonly evenementsAVenir: PageDesEvenements;
  readonly liensInternes: LiensInternes;
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`accueil : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

function entier(source: Record<string, unknown>, champ: string, ou: string): number {
  const brut = source[champ];
  if (typeof brut !== 'number' || !Number.isInteger(brut)) {
    throw new TypeError(`accueil : ${ou}« ${champ} » n’est pas un entier`);
  }
  return brut;
}

function arriveeRecente(brut: unknown, rang: number): ArriveeRecente {
  if (!estObjet(brut)) {
    throw new TypeError(`accueil : arrivees[${String(rang)}] non objet`);
  }
  return {
    appartenance: exigerChaine(brut, 'appartenance'),
    personneId: exigerChaine(brut, 'person_id'),
    prenom: exigerChaine(brut, 'first_name'),
    nom: exigerChaine(brut, 'last_name'),
    nomPrefere: chaineOuNul(brut, 'preferred_name'),
    dateArrivee: exigerChaine(brut, 'arrival_date'),
    presentationCourte: chaineOuNul(brut, 'short_intro'),
    funFact: chaineOuNul(brut, 'fun_fact'),
  };
}

/**
 * Valider ce que la section `arrivees_recentes` de l'accueil porte.
 *
 * **MEME DISCIPLINE QUE `validerLaPageDesEvenements`** : `pages` est confronte
 * a `total` et `taille` PAR LE CALCUL, jamais a une borne fixe — une entite
 * neuve sans aucune arrivee recente a un total legitime de zero (§7.0,
 * sixieme proposition).
 */
export function validerLaPageDesArriveesRecentes(valeur: unknown): PageDesArriveesRecentes {
  if (!estObjet(valeur)) {
    throw new TypeError('accueil : charge utile non objet');
  }

  const brutArrivees = valeur['arrivees'];
  if (!Array.isArray(brutArrivees)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « personne » sur une reponse qui n'en disait rien.
    throw new TypeError('accueil : « arrivees » n’est pas un tableau');
  }
  const arrivees = brutArrivees.map((brut, rang) => arriveeRecente(brut, rang));

  const taille = entier(valeur, 'taille', '');
  if (!TAILLES_DE_PAGE.includes(taille)) {
    throw new TypeError(`accueil : taille ${String(taille)} hors du §18.2`);
  }
  const total = entier(valeur, 'total', '');
  const pages = entier(valeur, 'pages', '');
  const attendu = total === 0 ? 0 : Math.ceil(total / taille);
  if (pages !== attendu) {
    throw new TypeError(
      `accueil : pages vaut ${String(pages)} pour un total de ${String(total)} ` +
        `a ${String(taille)} par page (${String(attendu)} attendu)`,
    );
  }

  return { arrivees, page: entier(valeur, 'page', ''), taille, total, pages };
}

/**
 * Valider ce que `GET …/accueil` a rendu — les CINQ sections, dans l'ordre du
 * cahier §8.4. Seule `presentation` peut valoir `null` ; les quatre autres
 * sont EXIGEES, meme vides (§7.0, quatrieme proposition).
 */
export function validerLAccueil(valeur: unknown): AccueilDEntite {
  if (!estObjet(valeur)) {
    throw new TypeError('accueil : charge utile non objet');
  }
  const brutPresentation = valeur['presentation'];
  if (brutPresentation !== null && !estObjet(brutPresentation)) {
    throw new TypeError('accueil : « presentation » ni objet ni null');
  }
  return {
    presentation: brutPresentation === null ? null : validerLaPageDeContenu(brutPresentation),
    framework: validerLaPageFramework(valeur['framework']),
    arriveesRecentes: validerLaPageDesArriveesRecentes(valeur['arrivees_recentes']),
    evenementsAVenir: validerLaPageDesEvenements(valeur['evenements_a_venir']),
    liensInternes: validerLesLiensInternes(valeur['liens_internes']),
  };
}
