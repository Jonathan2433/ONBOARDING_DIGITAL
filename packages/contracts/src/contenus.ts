/**
 * Le contrat du rendu des blocs — LOT 6, `T5`, `MVP-L06-US004` (1 sur 3).
 *
 * CE MODULE EST L'ENDROIT OU « AUCUN HTML EXECUTE » SE TIENT COTE CLIENT
 *
 *   Le cahier §10.7 et le modele §15.2 l'ecrivent quatre fois : « aucun HTML
 *   arbitraire n'est stocke ou execute », « aucun HTML arbitraire ni script
 *   n'est accepte ».
 *
 *   **Ce contrat le tient par la STRUCTURE, pas par un filtre.** Le contenu d'un
 *   bloc est type `Readonly<Record<string, unknown>>` : une **donnee**. Il
 *   n'existe aucune valeur de ce type qui designerait une chaine comme du
 *   balisage a interpreter, et aucune fonction exportee ici ne rend du HTML.
 *
 *   **Un filtre textuel aurait ete une heuristique, donc un defaut** (§7.25) :
 *   `<` est legitime dans « a < b », et chercher `<script` laisserait passer
 *   `<img onerror=…`.
 *
 * `texteDuBloc` REND DU TEXTE, ET C'EST TOUT CE QU'ELLE PEUT RENDRE
 *
 *   Son type de retour est `string`. Un ecran qui l'emploie ne peut pas obtenir
 *   de balisage, quelle que soit la donnee stockee — c'est le §7.35 : rendre la
 *   propriete structurelle plutot que de la confier a un controle qu'on
 *   pourrait retirer.
 *
 * LES CLEFS DU CONTENU NE SONT PAS CONTRAINTES — `QO-121`
 *
 *   Le §15.2 dit « des champs structures ; un `payload_json` valide par type
 *   lorsque necessaire », et **le corpus n'en nomme aucun**. En inventer serait
 *   §6.5. `QO-121` porte la question a Lea, et rien n'est bloque en attendant :
 *   les ecrans de LECTURE fonctionnent sur une donnee opaque.
 */

import { estObjet, exigerChaine } from './formes.js';
import { endpoint } from './sante.js';

/** Le gabarit du chemin, lu du manifeste — `DEC-492`, source unique. */
export const GABARIT_CHEMIN_PAGE_DE_CONTENU: string = endpoint('pageDeContenu').chemin;

/** Les codes exploitables. */
export const CODES_PAGE_DE_CONTENU: readonly number[] = endpoint('pageDeContenu').codesExploitables;

/**
 * Les CINQ types de page du modele §15.1.
 *
 * Le §15.1 s'ouvre par « `HOME`, `FRAMEWORK`, `CIRCLE`, `OFFICE`, `LEGAL`,
 * **autre type controle** » : la liste est **controlee**, non **fermee**. Ce
 * tableau nomme donc ce que le modele nomme, et le validateur ne refuse PAS un
 * type qu'il ne connait pas — le fermer bloquerait un lot ulterieur, exactement
 * comme la liste blanche de scopes du LOT 3 (§7.29).
 */
export const TYPES_DE_PAGE_NOMMES = ['HOME', 'FRAMEWORK', 'CIRCLE', 'OFFICE', 'LEGAL'] as const;

/** Le chemin d'une page de contenu, ses TROIS segments encodes. */
export function cheminPageDeContenu(code: string, typeDePage: string, slug: string): string {
  if (code === '' || typeDePage === '' || slug === '') {
    //  Sans cette garde, le chemin obtenu designerait une AUTRE ressource.
    throw new TypeError('code d’entite, type de page ou slug vide');
  }
  return GABARIT_CHEMIN_PAGE_DE_CONTENU.replace('{code}', encodeURIComponent(code))
    .replace('{type_de_page}', encodeURIComponent(typeDePage))
    .replace('{slug}', encodeURIComponent(slug));
}

export interface BlocDeContenu {
  readonly identifiant: string;
  readonly typeDeBloc: string;
  readonly ordre: number;
  /** **UNE DONNEE, JAMAIS DU BALISAGE.** Voir l'en-tete du module. */
  readonly contenu: Readonly<Record<string, unknown>>;
}

export interface PageDeContenu {
  readonly identifiant: string;
  readonly typeDePage: string;
  readonly titre: string;
  readonly slug: string;
  /** §15.1 : nullable, et le modele ne le lie PAS a `state`. */
  readonly publieeLe: string | null;
  readonly blocs: readonly BlocDeContenu[];
  readonly nombreDeBlocs: number;
}

/**
 * Le texte d'un bloc, **comme texte**.
 *
 * **SON TYPE DE RETOUR EST `string`, ET C'EST TOUT L'INTERET.** Un ecran qui
 * passe par elle ne peut pas obtenir de balisage a interpreter, quelle que soit
 * la donnee stockee. C'est la propriete rendue structurelle (§7.35).
 *
 * `clef` est fournie par l'appelant parce que **le corpus ne nomme aucune clef**
 * (`QO-121`) : en figer une ici serait inventer ce qui n'est pas decide (§6.5).
 * La valeur absente ou non textuelle rend la chaine vide — un ecran affiche
 * alors un bloc vide, ce qui est visible, plutot que « undefined ».
 */
export function texteDuBloc(bloc: BlocDeContenu, clef: string): string {
  const valeur = bloc.contenu[clef];
  return typeof valeur === 'string' ? valeur : '';
}

function chaineOuNul(source: Record<string, unknown>, champ: string): string | null {
  const brut = source[champ];
  if (brut === null) {
    return null;
  }
  if (typeof brut !== 'string') {
    //  **L'ABSENCE N'EST PAS `null`.** Un champ manquant est une reponse
    //  malformee ; un champ a `null` est une donnee absente, legitime.
    throw new TypeError(`page de contenu : « ${champ} » ni chaine ni null`);
  }
  return brut;
}

/** Valider ce que `GET …/pages/{type}/{slug}` a rendu. */
export function validerLaPageDeContenu(valeur: unknown): PageDeContenu {
  if (!estObjet(valeur)) {
    throw new TypeError('page de contenu : charge utile non objet');
  }

  const brutBlocs = valeur['blocs'];
  if (!Array.isArray(brutBlocs)) {
    //  **UN TABLEAU ABSENT N'EST PAS UN TABLEAU VIDE.** Le traduire en `[]`
    //  ferait afficher « page vide » sur une reponse qui n'en disait rien — et
    //  une page reellement vide est un etat LEGITIME qu'il faut pouvoir
    //  distinguer.
    throw new TypeError('page de contenu : « blocs » n’est pas un tableau');
  }

  const blocs = brutBlocs.map((brut, rang) => {
    if (!estObjet(brut)) {
      throw new TypeError(`page de contenu : blocs[${String(rang)}] non objet`);
    }
    const contenu = brut['contenu'];
    if (!estObjet(contenu)) {
      //  Le §15.2 parle de « champs structures » : un scalaire ou un tableau ne
      //  peut pas les porter, et l'accepter ferait deviner sa forme a l'ecran.
      throw new TypeError(`page de contenu : blocs[${String(rang)}].contenu n’est pas un objet`);
    }
    const ordre = brut['ordre'];
    if (typeof ordre !== 'number' || !Number.isInteger(ordre)) {
      throw new TypeError(`page de contenu : blocs[${String(rang)}].ordre n’est pas un entier`);
    }
    return {
      identifiant: exigerChaine(brut, 'identifiant'),
      typeDeBloc: exigerChaine(brut, 'type_de_bloc'),
      ordre,
      contenu,
    };
  });

  const nombre = valeur['nombre_de_blocs'];
  if (typeof nombre !== 'number' || !Number.isInteger(nombre)) {
    throw new TypeError('page de contenu : « nombre_de_blocs » n’est pas un entier');
  }
  if (nombre !== blocs.length) {
    //  **DEUX SOURCES POUR UNE MEME GRANDEUR** — §7.0, sixieme proposition.
    throw new TypeError(
      `page de contenu : nombre_de_blocs vaut ${String(nombre)} pour ` +
        `${String(blocs.length)} bloc(s) rendus`,
    );
  }

  //  **L'ORDRE EST VERIFIE, PAS RETRIE.** Retrier ici masquerait une API qui
  //  aurait cesse de trier, et l'ecran afficherait des blocs dans le desordre le
  //  jour ou le contrat serait retire (§7.35).
  for (let i = 1; i < blocs.length; i += 1) {
    const precedent = blocs[i - 1];
    const courant = blocs[i];
    if (precedent !== undefined && courant !== undefined && courant.ordre < precedent.ordre) {
      throw new TypeError(
        `page de contenu : blocs non ordonnes — ${String(precedent.ordre)} ` +
          `precede ${String(courant.ordre)}`,
      );
    }
  }

  return {
    identifiant: exigerChaine(valeur, 'identifiant'),
    typeDePage: exigerChaine(valeur, 'type_de_page'),
    titre: exigerChaine(valeur, 'titre'),
    slug: exigerChaine(valeur, 'slug'),
    publieeLe: chaineOuNul(valeur, 'publiee_le'),
    blocs,
    nombreDeBlocs: nombre,
  };
}
