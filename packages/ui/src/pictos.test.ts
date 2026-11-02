/**
 * Le controle de divergence entre `pictos.ts` et le catalogue officiel eXalt.
 *
 * Chantier design systeme v2 hors lot, etape `E2` (`DEC-681`).
 *
 * POURQUOI CE CONTROLE EXISTE
 *
 *   `pictos.ts` est une PROJECTION de `docs/design-systeme/handoff/pictos/
 *   exalt-icons.json`, exactement comme `jetons.css` est une projection de
 *   `jetons.ts`. Deux copies d'une meme valeur divergent — lecon `ECART-022` —
 *   et une icone corrigee en amont puis oubliee ici afficherait un dessin que
 *   plus personne ne reconnaitrait comme officiel.
 *
 * IL RE-EXTRAIT PLUTOT QUE DE REUTILISER LE GENERATEUR, ET C'EST DELIBERE
 *
 *   Le generateur est en Python, ce controle est en TypeScript, et les deux
 *   lisent le MEME balisage par des chemins independants. Reutiliser le
 *   generateur rendrait le controle aveugle a un defaut DU generateur : il
 *   confirmerait que la sortie est bien celle du code qui l'a produite, ce qui
 *   est vrai quoi qu'il arrive. Ce n'est pas une duplication au sens du §7.27,
 *   c'est la condition pour que la comparaison prouve quelque chose.
 *
 * IL COMPTE CE QU'IL EXAMINE, A TROIS NIVEAUX
 *
 *   Le nombre d'icones, le nombre de courbes par icone, et le nombre de balises
 *   `<path>` reellement vues dans le balisage source. Sans le troisieme, une
 *   expression reguliere qui raterait une balise — attributs dans un autre
 *   ordre, espace inattendu — rendrait moins de courbes des DEUX cotes et
 *   l'egalite tiendrait quand meme.
 */

import { describe, expect, it } from 'vitest';

import { CERCLES } from './jetons.js';
import { PICTOS } from './pictos.js';

//  `?raw` plutot que `node:fs` : le fichier arrive comme une chaine, sans
//  ajouter @types/node au projet. Meme parti que `jetons-css.test.ts`.
import CATALOGUE_BRUT from '../../../docs/design-systeme/handoff/pictos/exalt-icons.json?raw';
import SPEC from '../../../docs/design-systeme/handoff/DESIGN_SYSTEME.md?raw';

interface IconeOfficielle {
  readonly name: string;
  readonly viewBox: string;
  /** Du BALISAGE, pas une courbe : `<path d="...">`, parfois dans des `<g>`. */
  readonly path: string;
}

const CATALOGUE = JSON.parse(CATALOGUE_BRUT) as Record<string, IconeOfficielle>;

/** Le catalogue officiel, tel que mesure le 02/11/2026. */
const ICONES_OFFICIELLES = 382;

/**
 * Les cles que la spec NOMME, derivees et non recopiees.
 *
 * Un identifiant entre accents graves est une cle de picto si et seulement si
 * le catalogue officiel le connait. La regle est exacte — elle ne devine rien
 * sur la forme du nom — et elle ne vieillit pas : nommer un treizieme picto
 * dans `DESIGN_SYSTEME.md` le fait entrer dans cet ensemble sans que personne
 * y pense (§7.27).
 */
function clesCiteesParLaSpec(): readonly string[] {
  const cites = new Set(
    [...SPEC.matchAll(/`([^`\n]+)`/g)].map((correspondance) => correspondance[1] ?? ''),
  );
  return [...cites].filter((jeton) => jeton in CATALOGUE).sort((a, b) => a.localeCompare(b));
}

/** Les `d` d'un balisage, dans l'ordre, re-extraits independamment du generateur. */
function courbesDuBalisage(balisage: string): readonly string[] {
  return [...balisage.matchAll(/<path\b[^>]*\sd="([^"]*)"/g)].map((c) => c[1] ?? '');
}

/**
 * Les huit du tableau de la charte 4, DERIVES de la table `CERCLES`.
 *
 * **`E2` LES AVAIT ECRITS A LA MAIN ICI, ET C'ETAIT JUSTE A SA DATE** : aucune
 * table ne les portait encore, et le commentaire ci-dessous annoncait deja
 * « ce que la table `CERCLES` de `E4` devra associer ». Depuis que `E4` les
 * porte, une seconde liste divergerait au premier cercle ajoute — §7.27, la
 * classe d'erreur la plus frequente du projet.
 *
 * La liste INDEPENDANTE n'a pas disparu pour autant, elle a change de place :
 * `cercles.test.ts` extrait les huit pictos du tableau markdown de la charte
 * et les confronte a `CERCLES`. C'est la charte qui fait foi, pas une copie.
 */
const PICTOS_DE_CERCLE = Object.values(CERCLES).map((cercle) => cercle.picto);

/** Les quatre que les ecrans nomment : 6.2, 6.5, 6.7 et 7. */
const PICTOS_D_ECRAN = ['feu-d-artifice', 'organigramme', 'profil-valide', 'loupe'] as const;

describe('pictos.ts est une projection fidele du catalogue officiel', () => {
  it('lit bien le catalogue officiel, et il porte 382 icones', () => {
    expect(Object.keys(CATALOGUE)).toHaveLength(ICONES_OFFICIELLES);
  });

  it('retient EXACTEMENT les pictogrammes que la spec nomme, ni plus ni moins', () => {
    const attendues = clesCiteesParLaSpec();

    //  Le compte est annonce : si l'intersection tombait a zero — une spec
    //  deplacee, un format d'accents graves change — les deux listes seraient
    //  vides et l'egalite tiendrait sans rien prouver (§7.0, 3e proposition).
    expect(attendues).toHaveLength(12);
    expect(Object.keys(PICTOS).sort((a, b) => a.localeCompare(b))).toEqual(attendues);
  });

  it('porte les huit pictos que la table des cercles nomme', () => {
    //  CE QUE LA TABLE `CERCLES` ASSOCIE DEPUIS `E4`. Le test precedent dit
    //  qu'on suit la spec ; celui-ci dit que les huit pictos REELLEMENT employes
    //  par les cercles sont bien dans ce module — c'est le sens utile, puisque
    //  c'est `CERCLES` qui les nommera a l'ecran.
    expect(PICTOS_DE_CERCLE).toHaveLength(8);
    for (const cle of PICTOS_DE_CERCLE) {
      expect(Object.keys(PICTOS)).toContain(cle);
    }
  });

  it('porte les quatre pictos que les ecrans nomment hors du tableau des cercles', () => {
    //  Tuile « Vie eXalt » (6.2), bloc Vision (6.5), bandeau de parcours (6.7),
    //  etat vide (7).
    expect(PICTOS_D_ECRAN).toHaveLength(4);
    for (const cle of PICTOS_D_ECRAN) {
      expect(Object.keys(PICTOS)).toContain(cle);
    }
  });

  it("ne porte RIEN D'AUTRE que ces deux familles", () => {
    //  La cloture : sans elle, les deux tests precedents seraient satisfaits
    //  par un module qui porterait aussi trois cents icones inutiles. 8 + 4 = 12,
    //  et le compte derive de la spec vaut 12 : les trois nombres se tiennent.
    const classees = [...PICTOS_DE_CERCLE, ...PICTOS_D_ECRAN].sort((a, b) => a.localeCompare(b));
    expect(Object.keys(PICTOS).sort((a, b) => a.localeCompare(b))).toEqual(classees);
  });

  it.each(Object.keys(PICTOS))('%s : nom, viewBox et courbes identiques a la source', (cle) => {
    const local = PICTOS[cle as keyof typeof PICTOS];
    const officielle = CATALOGUE[cle];
    expect(officielle).toBeDefined();

    expect(local.nom).toBe(officielle?.name);
    expect(local.viewBox).toBe(officielle?.viewBox);

    const courbes = courbesDuBalisage(officielle?.path ?? '');

    //  Le troisieme compte : autant de courbes relevees que de balises <path>
    //  presentes. Une balise ratee par l'expression reguliere ne peut pas se
    //  cacher derriere une egalite des deux listes.
    const balises = (officielle?.path.match(/<path\b/g) ?? []).length;
    expect(courbes).toHaveLength(balises);
    expect(balises).toBeGreaterThan(0);

    expect(local.chemins).toEqual(courbes);
  });

  it('ne porte AUCUN balisage, seulement des courbes', () => {
    //  La propriete qui dispense `Picto` de `dangerouslySetInnerHTML` : si le
    //  module ne sait porter que des `d`, il n'y a rien a desinfecter. Un `<`
    //  n'a aucune raison d'exister dans un attribut de chemin SVG.
    const courbes = Object.values(PICTOS).flatMap((picto) => [...picto.chemins]);
    expect(courbes.length).toBe(88);
    expect(courbes.filter((d) => d.includes('<') || d.includes('"'))).toEqual([]);
  });

  it("ne porte aucune couleur : c'est ce qui rend `currentColor` possible", () => {
    //  Mesure, pas supposition. Un `fill` ou un `style` dans le balisage source
    //  survivrait au `fill="currentColor"` du `<svg>` — le picto garderait sa
    //  couleur d'origine sur une surface de cercle, et le couple surface/texte
    //  mesure par `jetons.test.ts` ne vaudrait plus rien pour lui.
    const balisages = Object.keys(PICTOS).map((cle) => CATALOGUE[cle]?.path ?? '');
    expect(balisages).toHaveLength(12);
    for (const balisage of balisages) {
      expect(balisage).not.toMatch(/\s(fill|stroke|style|class|transform|opacity)\s*=/);
    }
  });

  it("ne porte aucune reference interne : c'est ce qui rend l'aplatissement sur", () => {
    //  `bouclier-valide` porte dans la source un `id="HWIJHu.tif"` — un nom de
    //  calque Illustrator. Le generateur l'aplatit. Ce serait destructeur si
    //  quelque chose s'y referait ; ce test exige que rien ne s'y refere, et il
    //  echouera le jour ou une icone ajoutee emploiera un `clipPath` ou un
    //  `<use>`. Un `id` duplique a chaque rendu est par ailleurs un defaut de
    //  DOM, ce qui est la seconde raison de le retirer.
    const balisages = Object.keys(PICTOS).map((cle) => CATALOGUE[cle]?.path ?? '');
    expect(balisages).toHaveLength(12);
    for (const balisage of balisages) {
      expect(balisage).not.toMatch(/url\(#|<use\b|xlink/);
    }
  });
});
