/**
 * Le controle de fidelite entre la table `CERCLES` et le tableau de la charte 4.
 *
 * Chantier design systeme v2 hors lot, etape `E4` (`DEC-682`).
 *
 * POURQUOI CE CONTROLE EXISTE
 *
 *   `CERCLES` est une TRANSCRIPTION d'un tableau markdown. Une transcription se
 *   relit, et une relecture confirme ce qu'on croit — c'est la lecon du §7.40 de
 *   la passation : « une relecture confirme ce qu'on croit ; une derivation le
 *   contredit ». Ce fichier DERIVE les huit lignes de `DESIGN_SYSTEME.md` et
 *   confronte le resultat a la table, dans les DEUX sens.
 *
 *   Il ne protege donc pas seulement d'une faute de frappe : il fait entrer un
 *   neuvieme cercle ajoute a la charte sans que personne y pense (§7.27), parce
 *   qu'un tableau a neuf lignes et une table a huit cles ne concordent plus.
 *
 * CE QU'IL DERIVE, ET CE QU'IL DECLARE
 *
 *   La SURFACE est derivee : « marque-bleu-fonce » designe `MARQUE.bleuFonce`
 *   par une regle — premier segment, puis le reste en camel — jamais par une
 *   liste de huit correspondances qui vieillirait au premier ajout.
 *
 *   Le TEXTE est DECLARE, et c'est assume : la charte ecrit « blanc », « encre »
 *   et « titre », trois mots francais qu'aucune table de ce code ne porte. Trois
 *   entrees, nommees avec leur motif, et le §7.27 l'autorise pourvu qu'on EXIGE
 *   qu'elles correspondent au reel — ce que fait chaque assertion ci-dessous.
 *
 *   **ET CES TROIS VALEURS SONT DES LITTERAUX, PAS DES `var()`.** « titre »
 *   renvoie a `THEMES.clair.titre` fige, jamais a `--titre` qui BASCULE : c'est
 *   le defaut que `E1` a trouve dans le `jetons.css` fourni, ou six cercles sur
 *   huit tombaient sous AA en theme sombre. Comparer au theme clair est donc le
 *   bon geste, et `jetons.test.ts` mesure separement les deux themes.
 *
 * IL COMPTE CE QU'IL EXAMINE
 *
 *   Un analyseur qui ne reconnaitrait aucune ligne rendrait un ensemble vide, et
 *   « chaque ligne de la charte correspond » tiendrait sans rien prouver (§7.0,
 *   troisieme proposition). Le nombre de lignes est donc exige, et un temoin
 *   prouve que l'analyseur sait lire un tableau qu'on lui fabrique.
 */

import { describe, expect, it } from 'vitest';

import { contraste } from './contraste.js';
import { CERCLES, MARQUE, TEINTES, THEMES } from './jetons.js';
import type { DefinitionDeCercle } from './jetons.js';
import { PICTOS } from './pictos.js';

//  `?raw` plutot que `node:fs` : meme parti que `pictos.test.ts` et
//  `jetons-css.test.ts`, aucun @types/node a ajouter au projet.
import SPEC from '../../../docs/design-systeme/handoff/DESIGN_SYSTEME.md?raw';
import CSS from './jetons.css?raw';

interface LigneDeLaCharte {
  readonly nom: string;
  readonly surface: string;
  readonly texte: string;
  readonly picto: string;
}

/**
 * Les lignes du tableau de la section 4, extraites du markdown.
 *
 * La section est bornee par ses deux titres — `## 4.` jusqu'au suivant — pour
 * qu'un tableau a quatre colonnes situe ailleurs dans la charte ne vienne pas
 * s'y melanger. L'en-tete et le separateur sont ecartes par leur CONTENU
 * (« Cercle », tirets), jamais par leur rang : une ligne de plus ou de moins
 * avant le tableau deplacerait un rang, pas un contenu.
 */
function lignesDeLaCharte(markdown: string): readonly LigneDeLaCharte[] {
  const section = /^##\s*4\.[^\n]*\n([\s\S]*?)(?=^##\s)/m.exec(markdown)?.[1] ?? '';
  const lignes: LigneDeLaCharte[] = [];
  for (const brute of section.split('\n')) {
    const cellules = brute
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim());
    if (!brute.trim().startsWith('|') || cellules.length !== 4) {
      continue;
    }
    const [nom = '', surface = '', texte = '', picto = ''] = cellules;
    if (nom === 'Cercle' || /^-+$/.test(nom)) {
      continue;
    }
    lignes.push({ nom, surface, texte, picto: picto.replace(/`/g, '') });
  }
  return lignes;
}

/** `marque-bleu-fonce` → la surface de `MARQUE.bleuFonce`. Une regle, pas une liste. */
function surfaceNommee(mot: string): string | undefined {
  const segments = mot.split('-');
  const table = segments[0] === 'marque' ? MARQUE : segments[0] === 'teinte' ? TEINTES : undefined;
  if (table === undefined) {
    return undefined;
  }
  const cle = segments
    .slice(1)
    .map((s, rang) => (rang === 0 ? s : s.charAt(0).toUpperCase() + s.slice(1)))
    .join('');
  return (table as Record<string, { surface: string }>)[cle]?.surface;
}

/**
 * Les trois mots de la colonne « Texte », traduits en valeurs LITTERALES.
 *
 * `encre` et `titre` prennent la valeur du theme CLAIR et s'y figent : le texte
 * d'un cercle ne bascule jamais, puisque sa surface ne bascule pas.
 */
const TEXTES_DE_LA_CHARTE: Readonly<Record<string, string>> = {
  blanc: '#FFFFFF',
  encre: THEMES.clair.encre,
  titre: THEMES.clair.titre,
};

const LIGNES = lignesDeLaCharte(SPEC);

describe('CERCLES est une transcription fidele du tableau de la charte 4', () => {
  it('lit bien le tableau de la section 4, et il porte huit lignes', () => {
    //  SANS CE COMPTE, un analyseur casse rendrait zero ligne et toutes les
    //  boucles ci-dessous passeraient a vide.
    expect(LIGNES).toHaveLength(8);
    expect(LIGNES[0]?.nom).toBe('Produit');
    expect(LIGNES[7]?.nom).toBe('IT');
  });

  it("TEMOIN : l'analyseur sait lire un tableau, et ecarte en-tete et separateur", () => {
    const faux = lignesDeLaCharte(
      [
        '## 4. Essai',
        '',
        '| Cercle | Surface | Texte | Picto |',
        '|---|---|---|---|',
        '| Zz | marque-bleu | blanc | `fusee` |',
        '',
        '## 5. Suite',
      ].join('\n'),
    );
    expect(faux).toEqual([{ nom: 'Zz', surface: 'marque-bleu', texte: 'blanc', picto: 'fusee' }]);
  });

  it('TEMOIN : un tableau situe hors de la section 4 est ignore', () => {
    expect(lignesDeLaCharte('## 3. Ailleurs\n| Zz | a | b | `c` |\n\n## 5. Suite')).toHaveLength(0);
  });

  //  LA CLE EST LE NOM EN MINUSCULES, ET C'EST CE QUI FAIT ENTRER UN NEUVIEME
  //  CERCLE SANS DECISION. `IT` donne `it`, `Produit` donne `produit`.
  it('porte une cle par ligne de la charte, et cette cle est le nom en minuscules', () => {
    for (const ligne of LIGNES) {
      const cle = ligne.nom.toLowerCase();
      expect(Object.keys(CERCLES), `${ligne.nom} n a pas de cle ${cle}`).toContain(cle);
    }
  });

  it('ne porte AUCUNE cle que la charte ne nomme pas', () => {
    const attendues = LIGNES.map((l) => l.nom.toLowerCase());
    expect(Object.keys(CERCLES)).toEqual(attendues);
  });

  it.each(LIGNES.map((l) => [l.nom, l] as const))(
    '%s : nom, surface, texte et picto sont ceux de la charte',
    (_nom, ligne) => {
      const cercle: DefinitionDeCercle | undefined = (
        CERCLES as Readonly<Record<string, DefinitionDeCercle>>
      )[ligne.nom.toLowerCase()];
      expect(cercle).toBeDefined();
      expect(cercle?.nom).toBe(ligne.nom);

      const surface = surfaceNommee(ligne.surface);
      expect(surface, `la charte nomme une surface inconnue : ${ligne.surface}`).toBeDefined();
      expect(cercle?.surface).toBe(surface);

      const texte = TEXTES_DE_LA_CHARTE[ligne.texte];
      expect(texte, `la charte nomme un texte inconnu : ${ligne.texte}`).toBeDefined();
      expect(cercle?.texte).toBe(texte);

      expect(cercle?.picto).toBe(ligne.picto);
    },
  );

  it('ne nomme que des pictogrammes que le catalogue officiel porte', () => {
    //  Double emploi volontaire avec le type `ClePicto` : le type refuse a la
    //  COMPILATION, ce test refuse a l'EXECUTION — et c'est lui qui mordrait si
    //  `pictos.ts` perdait une icone que la charte nomme encore.
    for (const ligne of LIGNES) {
      expect(Object.keys(PICTOS), `${ligne.nom} : ${ligne.picto}`).toContain(ligne.picto);
    }
  });

  it('donne un pictogramme DISTINCT a chaque cercle', () => {
    //  Deux cercles partagent volontiers une surface ; ils ne partagent jamais
    //  un dessin. C'est cette propriete qui interdit d'indexer la table par la
    //  couleur, et donc qui a decide de la cle (voir l'en-tete de `jetons.ts`).
    const pictos = Object.values(CERCLES).map((c) => c.picto);
    expect(new Set(pictos).size).toBe(pictos.length);
  });

  it('donne un nom DISTINCT a chaque cercle', () => {
    const noms = Object.values(CERCLES).map((c) => c.nom);
    expect(new Set(noms).size).toBe(noms.length);
  });
});

/**
 * L'ADRESSE CSS DE CHAQUE CERCLE EXISTE — le controle que `E4` a rendu necessaire.
 *
 * `couleurDuCercle` (`apps/web`) ne rend plus une valeur prise dans une table
 * locale : elle rend `var(--cercle-<jeton>)`, un nom CONSTRUIT a partir de la
 * cle. Tant que les huit noms etaient ecrits a la main des deux cotes, la
 * correspondance se voyait ; construite, elle ne se voit plus.
 *
 * `jetons-css.test.ts` exige deja que les seize variables portent les bonnes
 * VALEURS, mais il les nomme une par une : un neuvieme cercle ajoute a la charte
 * y serait absent, et l'ecran demanderait alors une variable qui n'existe pas —
 * sans aucune erreur, juste une bordure qui disparait. Ce controle-ci est DERIVE
 * de `CERCLES`, donc il couvre le neuvieme sans que personne y pense (§7.27).
 */
describe('chaque cercle a son adresse dans la feuille de jetons', () => {
  it('declare --cercle-<cle> et --cercle-<cle>-texte pour les huit', () => {
    for (const cle of Object.keys(CERCLES)) {
      expect(CSS, `--cercle-${cle} manque`).toContain(`--cercle-${cle}:`);
      expect(CSS, `--cercle-${cle}-texte manque`).toContain(`--cercle-${cle}-texte:`);
    }
  });

  it('TEMOIN : le controle sait voir une adresse absente', () => {
    //  Sans lui, un `toContain` toujours vrai — par exemple si `CSS` arrivait
    //  vide — passerait pour une preuve. §7.0, quatrieme proposition.
    expect(CSS).not.toContain('--cercle-inexistant:');
    expect(CSS.length).toBeGreaterThan(1000);
  });
});

/**
 * UNE COULEUR DE CERCLE NE PEUT PAS ETRE UN SIMPLE TRAIT D'ACCENT — mesure du
 * 02/11/2026, faite dans un vrai navigateur sur la page Framework reelle.
 *
 * Les ecrans du chantier front (`S5`, `S10`) posent la couleur du cercle en
 * BORDURE de carte, quatre pixels sur une surface claire. Releve sur la page
 * servie : `produit` rend 5,13 et `projet` 10,50, mais **CINQ des huit** passent
 * sous 3:1 — `change` 1,37, `data` 1,17, `shield` 1,19, `forge` 1,08, `it` 1,09.
 * Trois d'entre elles sont litteralement invisibles.
 *
 * **CE N'EST PAS UN DEFAUT DE LA CHARTE, C'EST UN EMPLOI QUI NE LUI CORRESPOND
 * PAS.** Sa section 4 donne des couples SURFACE + TEXTE : quatre teintes pales
 * portant un texte sombre, faites pour etre REMPLIES — une pastille, une tuile —
 * ou leur paleur est precisement ce qui rend le texte lisible. Etirees en ligne
 * de quatre pixels, elles ne portent plus rien.
 *
 * Aucune regle d'accessibilite n'est enfreinte : le nom du cercle est toujours
 * du texte (modele 10.1), et WCAG 1.4.11 ne vise pas un ornement. Mais la moitie
 * de la palette ne porte alors aucun signal, ce qui est le contraire de ce que la
 * charte cherche.
 *
 * **LA CORRECTION APPARTIENT A `E5`**, qui applique les motifs de la section 6 :
 * c'est la que le cercle doit devenir une pastille remplie plutot qu'un filet.
 * Ce test ne l'impose pas — il n'a pas a decider d'un ecran — il FIGE la mesure
 * pour qu'elle ne se perde pas, et il tombera si la palette change, obligeant a
 * la refaire plutot qu'a la supposer.
 */
describe('la palette des cercles n est pas faite pour un trait d accent', () => {
  const SEUIL_NON_TEXTUEL = 3;

  it('compte CINQ cercles sur huit sous 3:1 posés en trait sur une carte claire', () => {
    const faibles = Object.entries(CERCLES)
      .filter(([, c]) => contraste(c.surface, THEMES.clair.surface) < SEUIL_NON_TEXTUEL)
      .map(([cle]) => cle);
    expect(faibles).toEqual(['change', 'data', 'shield', 'forge', 'it']);
  });

  it('TEMOIN : les trois autres passent, donc la mesure DISCRIMINE', () => {
    //  Sans lui, une formule cassee rendant toujours 1 ferait dire « cinq
    //  faibles » a une palette entierement opaque. §7.0, quatrieme proposition.
    for (const cle of ['produit', 'projet', 'design'] as const) {
      expect(
        contraste(CERCLES[cle].surface, THEMES.clair.surface),
        `${cle} devrait etre visible en trait`,
      ).toBeGreaterThanOrEqual(SEUIL_NON_TEXTUEL);
    }
  });

  it('REMPLIES, en revanche, les huit portent leur texte — c est leur emploi', () => {
    //  La contrepartie positive : ce qui echoue en trait reussit en surface.
    //  `jetons.test.ts` le mesure deja couple par couple ; ici on dit que les
    //  DEUX faits coexistent, ce qui est l'argument de `E5`.
    for (const [cle, c] of Object.entries(CERCLES)) {
      expect(contraste(c.surface, c.texte), `${cle} rempli`).toBeGreaterThanOrEqual(c.seuil);
    }
  });
});
