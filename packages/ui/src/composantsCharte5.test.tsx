/**
 * Les composants de la charte 5 — accessibilite, role, focus, clavier.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-681`).
 *
 * CE QUE CES TESTS CHERCHENT, ET CE QU'ILS NE CHERCHENT PAS
 *
 *   Ils interrogent le DOM par les ROLES et les NOMS ACCESSIBLES, jamais par
 *   les classes CSS : c'est ce qu'une technologie d'assistance voit, et c'est
 *   donc la seule chose dont la justesse compte. Une classe renommee ne doit
 *   pas faire echouer un test d'accessibilite, et une region qui perd son nom
 *   doit le faire.
 *
 *   Ils ne verifient AUCUNE apparence. jsdom n'applique pas de mise en page :
 *   une assertion sur une couleur ou une hauteur y mesurerait la valeur ecrite,
 *   pas celle qui s'affiche. Les couleurs sont prouvees par `jetons.test.ts`,
 *   qui les RECALCULE, et la feuille est prouvee par le controle des jetons.
 *
 * LE CLAVIER EST PROUVE PAR LA NATURE DE L'ELEMENT, ET C'EST DIT
 *
 *   Espace sur une case a cocher, les fleches dans une liste deroulante,
 *   Entree sur un bouton : rien de tout cela n'est implemente par ces
 *   composants, et jsdom ne le simule pas non plus. Ce que ces tests exigent,
 *   c'est que l'element RESTE NATIF — un `<input type="checkbox">`, un
 *   `<select>`, un `<button>` — parce que c'est de la nature de l'element que
 *   le comportement clavier decoule. Verifier la nature est exact ; simuler une
 *   touche que jsdom ne route pas serait un controle qui ne peut pas echouer.
 */

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { Avatar, initiales } from './Avatar.js';
import { CaseACocher } from './CaseACocher.js';
import { Champ } from './Champ.js';
import { Liste } from './Liste.js';
import { Pastille } from './Pastille.js';
import { Progression } from './Progression.js';

import CSS from './composants.css?raw';

afterEach(() => {
  cleanup();
});

describe('Pastille', () => {
  it('rend son libelle', () => {
    render(<Pastille>Presentation de l entite</Pastille>);
    expect(screen.getByText('Presentation de l entite')).toBeTruthy();
  });

  it("N'EST PAS UN TITRE, et c'est le point entier du composant", () => {
    //  Le temoin qui mord : un surtitre promu en `<h2>` s'insererait AVANT le
    //  `<h1>` de la page et casserait la hierarchie des titres (WCAG 1.3.1).
    //  Le temoin positif voisin prouve que la requete sait trouver un titre.
    render(
      <>
        <Pastille>Trombinoscope</Pastille>
        <h1>Les collaborateurs</h1>
      </>,
    );
    expect(screen.queryByRole('heading', { name: 'Trombinoscope' })).toBeNull();
    expect(screen.getByRole('heading', { name: 'Les collaborateurs' })).toBeTruthy();
  });
});

describe('Avatar', () => {
  it('rend les initiales des deux premiers MOTS, jamais deux lettres du premier', () => {
    expect(initiales('Ada Lovelace')).toBe('AL');
    expect(initiales('Grace')).toBe('G');
    expect(initiales('  Jean  Pierre  Dupont ')).toBe('JP');
    expect(initiales('')).toBe('');
    expect(initiales('élise navarro')).toBe('ÉN');
  });

  it('decoratif par defaut : la photo ne redit pas le nom ecrit a cote', () => {
    const { container } = render(
      <>
        <Avatar nom="Ada Lovelace" photo="/media/ada.jpg" />
        <span>Ada Lovelace</span>
      </>,
    );
    const image = container.querySelector('img');
    expect(image?.getAttribute('alt')).toBe('');
    //  Une image a `alt=""` n'est pas dans l'arbre : aucun role `img`.
    expect(screen.queryByRole('img')).toBeNull();
    //  TEMOIN APPARIE : le nom reste lisible, il vient du texte voisin.
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
  });

  it('nomme quand on le demande, et seulement alors', () => {
    render(<Avatar nom="Ada Lovelace" photo="/media/ada.jpg" decoratif={false} />);
    expect(screen.getByRole('img', { name: 'Ada Lovelace' })).toBeTruthy();
  });

  it('sans photo, le repli en initiales suit la meme regle', () => {
    const { container, unmount } = render(<Avatar nom="Grace Hopper" />);
    expect(screen.getByText('GH')).toBeTruthy();
    //  **L'ATTRIBUT EST ASSERTE DIRECTEMENT, ET C'EST UNE MESURE.** La
    //  premiere version ne verifiait que l'absence de role `img` : un `<span>`
    //  n'en a aucun de toute facon, si bien que retirer `aria-hidden` laissait
    //  les 31 tests verts (temoin execute le 02/11/2026). Meme classe que le
    //  defaut trouve sur `Picto` en `E2`.
    const noeud = container.querySelector('.ex-avatar') as HTMLElement;
    expect(noeud.getAttribute('aria-hidden')).toBe('true');
    expect(screen.queryByRole('img')).toBeNull();
    unmount();

    render(<Avatar nom="Grace Hopper" decoratif={false} />);
    expect(screen.getByRole('img', { name: 'Grace Hopper' })).toBeTruthy();
  });

  it("TEMOIN DECISIF : les initiales decoratives n'entrent PAS dans le nom du bouton", () => {
    //  Ce que `aria-hidden` change reellement, la ou cela compte : un bouton de
    //  trombinoscope porte un avatar ET le nom ecrit. Sans le masquage, son nom
    //  accessible vaudrait « GHGrace Hopper » — les initiales collees au nom,
    //  la concatenation du calcul n'inserant pas d'espace entre deux contenus
    //  en ligne (meme mesure qu'avec `Picto` en `E2`).
    render(
      <button type="button">
        <Avatar nom="Grace Hopper" />
        Grace Hopper
      </button>,
    );
    expect(screen.getByRole('button', { name: 'Grace Hopper' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'GHGrace Hopper' })).toBeNull();
  });

  it("l'anneau est une variable, jamais une bordure ecrite en ligne", () => {
    //  La couleur du cercle voyage par `--avatar-anneau`, dont la feuille
    //  declare le repli. Sans ce repli, une carte sans cercle rendrait la
    //  valeur par defaut du navigateur SANS que rien n'echoue — c'est le
    //  defaut que `cadre-check` avait releve sur `--carte-cercle` en `S10`.
    const { container } = render(<Avatar nom="Ada Lovelace" anneau="#5853FF" />);
    const noeud = container.querySelector('.ex-avatar') as HTMLElement;
    expect(noeud.getAttribute('data-anneau')).toBe('oui');
    expect(noeud.style.getPropertyValue('--avatar-anneau')).toBe('#5853FF');
    expect(CSS).toContain('--avatar-anneau: var(--trait)');
  });

  it("sans anneau, aucune variable n'est posee", () => {
    const { container } = render(<Avatar nom="Ada Lovelace" />);
    const noeud = container.querySelector('.ex-avatar') as HTMLElement;
    expect(noeud.getAttribute('data-anneau')).toBe('non');
    expect(noeud.getAttribute('style')).toBeNull();
  });
});

describe('Champ', () => {
  it('relie son libelle a la saisie par un vrai <label for>', () => {
    render(<Champ libelle="Adresse e-mail" />);
    const saisie = screen.getByLabelText('Adresse e-mail');
    expect(saisie.tagName).toBe('INPUT');
  });

  it('prend le focus, et reste dans l ordre de tabulation', () => {
    render(<Champ libelle="Recherche" />);
    const saisie = screen.getByLabelText('Recherche');
    (saisie as HTMLInputElement).focus();
    expect(document.activeElement).toBe(saisie);
    expect(saisie.getAttribute('tabindex')).toBeNull();
  });

  it("relie l'aide au champ, et pas seulement a cote de lui", () => {
    render(<Champ libelle="Mot de passe" aide="Douze caracteres au moins." />);
    const saisie = screen.getByLabelText('Mot de passe');
    const decrit = saisie.getAttribute('aria-describedby');
    expect(decrit).not.toBeNull();
    const aide = document.getElementById(decrit as string);
    expect(aide?.textContent).toBe('Douze caracteres au moins.');
  });

  it('une erreur pose aria-invalid ET un message : jamais la couleur seule', () => {
    render(<Champ libelle="Adresse" erreur="Cette adresse est inconnue." />);
    const saisie = screen.getByLabelText('Adresse');
    expect(saisie.getAttribute('aria-invalid')).toBe('true');
    expect(screen.getByText('Cette adresse est inconnue.')).toBeTruthy();
  });

  it("CUMULE l'aide et l'erreur, au lieu de perdre l'aide quand elle sert le plus", () => {
    render(<Champ libelle="Adresse" aide="Votre e-mail eXalt." erreur="Inconnue." />);
    const saisie = screen.getByLabelText('Adresse');
    const identifiants = (saisie.getAttribute('aria-describedby') ?? '').split(' ');
    expect(identifiants).toHaveLength(2);
    const textes = identifiants.map((id) => document.getElementById(id)?.textContent);
    expect(textes).toEqual(['Votre e-mail eXalt.', 'Inconnue.']);
  });

  it('sans aide ni erreur, ne pose AUCUN aria-describedby vide', () => {
    //  `aria-describedby=""` pointe vers rien et fait annoncer une description
    //  absente par certains lecteurs : mieux vaut ne pas poser l'attribut.
    render(<Champ libelle="Nom" />);
    expect(screen.getByLabelText('Nom').getAttribute('aria-describedby')).toBeNull();
    expect(screen.getByLabelText('Nom').getAttribute('aria-invalid')).toBeNull();
  });

  it('donne un identifiant DISTINCT a deux champs rendus cote a cote', () => {
    render(
      <>
        <Champ libelle="Prenom" />
        <Champ libelle="Nom" />
      </>,
    );
    const a = screen.getByLabelText('Prenom').id;
    const b = screen.getByLabelText('Nom').id;
    expect(a).not.toBe('');
    expect(a).not.toBe(b);
  });
});

describe('Liste', () => {
  it('relie son libelle au <select> et rend ses options', () => {
    render(
      <Liste libelle="Cercle">
        <option value="produit">Produit</option>
        <option value="data">Data</option>
      </Liste>,
    );
    const liste = screen.getByLabelText('Cercle');
    //  LA NATURE EST LA PREUVE DU CLAVIER : fleches, recherche par frappe et
    //  rendu natif sur mobile viennent de `<select>`, pas de notre code.
    expect(liste.tagName).toBe('SELECT');
    expect(screen.getByRole('option', { name: 'Produit' })).toBeTruthy();
  });

  it('change de valeur, et le changement remonte', () => {
    render(
      <Liste libelle="Cercle" defaultValue="produit">
        <option value="produit">Produit</option>
        <option value="data">Data</option>
      </Liste>,
    );
    const liste = screen.getByLabelText('Cercle') as HTMLSelectElement;
    fireEvent.change(liste, { target: { value: 'data' } });
    expect(liste.value).toBe('data');
  });
});

describe('Progression', () => {
  it('porte un role, un nom, et LES TROIS valeurs', () => {
    render(<Progression libelle="Progression du parcours" faites={3} total={7} />);
    const barre = screen.getByRole('progressbar', { name: 'Progression du parcours' });
    expect(barre.getAttribute('aria-valuemin')).toBe('0');
    expect(barre.getAttribute('aria-valuemax')).toBe('7');
    expect(barre.getAttribute('aria-valuenow')).toBe('3');
  });

  it("annonce « 3 sur 7 » plutot qu'un pourcentage", () => {
    render(<Progression libelle="Parcours" faites={3} total={7} />);
    expect(screen.getByRole('progressbar').getAttribute('aria-valuetext')).toBe('3 sur 7');
  });

  it('BORNE une valeur incoherente au lieu de la rendre telle quelle', () => {
    const { unmount } = render(<Progression libelle="Parcours" faites={12} total={7} />);
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('7');
    unmount();

    render(<Progression libelle="Parcours" faites={-3} total={7} />);
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0');
  });

  it('un parcours SANS tache est plein, pas vide', () => {
    //  Zero sur zero n'est pas 0 % : c'est « rien a faire ». Une barre vide
    //  ferait croire a un parcours entierement en attente.
    const { container } = render(<Progression libelle="Parcours" faites={0} total={0} />);
    const remplissage = container.querySelector('.ex-progression__remplissage') as HTMLElement;
    //  `100.00%` ecrit par le composant, `100%` relu : jsdom normalise la
    //  valeur serialisee. La precision reste utile pour les tiers (33.33%).
    expect(remplissage.style.inlineSize).toBe('100%');
    expect(screen.getByRole('progressbar').getAttribute('aria-valuetext')).toBe('0 sur 0');
  });

  it('la largeur suit la part reellement faite', () => {
    const { container } = render(<Progression libelle="Parcours" faites={1} total={4} />);
    const remplissage = container.querySelector('.ex-progression__remplissage') as HTMLElement;
    expect(remplissage.style.inlineSize).toBe('25%');
  });
});

describe('CaseACocher', () => {
  it('est une case NATIVE reliee a son libelle', () => {
    render(<CaseACocher libelle="Rencontrer son DSM" />);
    const case_ = screen.getByRole('checkbox', { name: 'Rencontrer son DSM' });
    //  LA NATURE EST LA PREUVE DU CLAVIER : Espace, Tab et l'annonce de l'etat
    //  viennent de l'element natif. jsdom ne route pas Espace ; exiger la
    //  nature est exact, simuler la touche ne prouverait rien.
    expect(case_.tagName).toBe('INPUT');
    expect(case_.getAttribute('type')).toBe('checkbox');
  });

  it('prend le focus et bascule', () => {
    render(<CaseACocher libelle="Lire le livret" />);
    const case_ = screen.getByRole('checkbox', { name: 'Lire le livret' }) as HTMLInputElement;
    case_.focus();
    expect(document.activeElement).toBe(case_);
    expect(case_.checked).toBe(false);
    fireEvent.click(case_);
    expect(case_.checked).toBe(true);
  });

  it('cliquer le LIBELLE coche aussi : la cible ne se limite pas aux 20px', () => {
    render(<CaseACocher libelle="Rendre son materiel" />);
    fireEvent.click(screen.getByText('Rendre son materiel'));
    expect((screen.getByRole('checkbox') as HTMLInputElement).checked).toBe(true);
  });

  it('desactivee, elle le dit a l arbre et sort de la tabulation', () => {
    render(<CaseACocher libelle="Tache verrouillee" disabled />);
    const case_ = screen.getByRole('checkbox', { name: 'Tache verrouillee' }) as HTMLInputElement;
    expect(case_.disabled).toBe(true);

    //  **CE TEST N'ESSAIE PAS DE CLIQUER, ET C'EST UNE MESURE, PAS UN RENONCEMENT.**
    //  `fireEvent.click` distribue l'evenement DIRECTEMENT sur le noeud : il
    //  court-circuite la garde que le navigateur applique a un element
    //  desactive, si bien qu'un clic synthetique coche la case meme desactivee
    //  (verifie, 02/11/2026). Une assertion « elle ne bascule pas » mesurerait
    //  donc jsdom, pas le composant. Ce qui est exact — et ce que le navigateur
    //  honore reellement — est l'attribut lui-meme, plus le fait que l'element
    //  quitte l'ordre de tabulation.
    case_.focus();
    expect(document.activeElement).not.toBe(case_);
  });
});

describe('le focus est le MEME partout, et il vient du jeton', () => {
  const CSS_NU = CSS.replace(/\/\*[\s\S]*?\*\//g, '');

  it('chaque regle :focus-visible emploie var(--anneau-focus)', () => {
    //  AVANT `E3`, cinq regles ecrivaient `3px solid var(--marque-bleu)` a la
    //  main. Elles etaient justes en theme clair et EN ECHEC en sombre (2,91:1,
    //  sous les 3:1 de WCAG 1.4.11) depuis que `S9` a ajoute ce theme — §7.21 :
    //  un controle juste hier peut etre faux aujourd'hui, et c'est nous qui
    //  l'avons rendu faux. Le jeton les corrige toutes d'un coup.
    //  LE CONTROLE PORTE SUR LES REGLES QUI DESSINENT UN `outline`, PAS SUR
    //  TOUTES CELLES QUI REAGISSENT AU FOCUS. Sa premiere version refusait
    //  `… :focus-visible { border-color: var(--titre); }` — la bordure bleue
    //  de 1,5px que la charte 5 demande EN PLUS de l'anneau — c'est-a-dire du
    //  code conforme. Un garde-fou a faux positifs apprend a passer outre
    //  (§7.25) : il discrimine donc sur ce qu'il vise vraiment.
    const regles = CSS_NU.match(/:focus-visible[^{]*\{[^}]*\}/g) ?? [];
    const avecAnneau = regles.filter((regle) => /\boutline\s*:/.test(regle));
    expect(avecAnneau.length, `regles de focus relevees : ${regles.length}`).toBeGreaterThanOrEqual(
      7,
    );
    const sansJeton = avecAnneau.filter((regle) => !regle.includes('var(--anneau-focus)'));
    expect(sansJeton, `anneaux ecrits a la main : ${JSON.stringify(sansJeton)}`).toEqual([]);
  });

  it("aucune regle ne supprime l'anneau", () => {
    //  `outline: none` sur un element interactif est la facon la plus courante
    //  de casser la navigation au clavier (WCAG 2.4.7).
    expect(CSS_NU).not.toMatch(/outline:\s*(none|0)\b/);
  });
});

describe('les bascules du theme sombre sont DANS la feuille, pas seulement mesurees', () => {
  const CSS_NU = CSS.replace(/\/\*[\s\S]*?\*\//g, '');

  /** Les regles d'une portee `:root[data-theme='sombre']`, telles quelles. */
  const reglesSombres = CSS_NU.match(/:root\[data-theme='sombre'\][^{]*\{[^}]*\}/g) ?? [];

  it('declare les trois bascules que la mesure a rendues obligatoires', () => {
    //  **AUCUN TEST DE RENDU NE PEUT VOIR CES TROIS REGLES.** jsdom n'applique
    //  pas de media query ni de cascade de theme : un developpeur qui les
    //  retirerait ne casserait rien, et le defaut ne se verrait que dans un
    //  navigateur reel, en theme sombre, au clavier. §7.35 — quand aucun
    //  controle de comportement ne peut voir la propriete, on la rend
    //  observable autrement : ici, en lisant la feuille.
    //
    //  Les trois valent 2,91:1 en theme sombre avec `--marque-bleu`, sous le
    //  seuil de 3:1 (et sous 4,5 pour le texte du bouton discret). `--titre` y
    //  rend 7,44:1. Mesure du 02/11/2026, prouvee par `jetons.test.ts`.
    const attendues = [
      ".ex-bouton[data-variante='discret']",
      '.ex-champ__saisie:focus-visible',
      '.ex-progression__remplissage',
    ];
    expect(attendues).toHaveLength(3);
    for (const selecteur of attendues) {
      const regle = reglesSombres.find((r) => r.includes(selecteur));
      expect(regle, `aucune bascule sombre pour ${selecteur}`).toBeDefined();
      expect(regle as string, `${selecteur} ne bascule pas sur --titre`).toContain('var(--titre)');
    }
  });

  it('et le jeton lui-meme bascule, dans `jetons.css`', () => {
    //  Le quatrieme site est l'anneau de focus, qui n'est pas dans cette
    //  feuille : il est redeclare dans `jetons.css`, ou le controle de
    //  divergence le compare au module TypeScript.
    expect(CSS_NU).not.toMatch(/outline:\s*3px solid var\(--marque-bleu\)/);
  });
});

describe('le mouvement est neutralise partout ou il est introduit — charte 1.7', () => {
  const CSS_NU = CSS.replace(/\/\*[\s\S]*?\*\//g, '');

  it('chaque selecteur qui anime figure dans un bloc `prefers-reduced-motion`', () => {
    //  UN CONTROLE EXACT PLUTOT QU'UNE PROMESSE. La charte 1.7 veut le
    //  mouvement NEUTRALISE, pas raccourci. Oublier un selecteur dans le bloc
    //  de neutralisation ne casse aucun test de rendu — jsdom n'evalue pas les
    //  media queries — et ne se verrait que sur la machine de quelqu'un qui a
    //  demande moins de mouvement.
    const blocsReduits =
      CSS_NU.match(/@media[^{]*prefers-reduced-motion[^{]*\{[\s\S]*?\n\}/g) ?? [];
    expect(blocsReduits.length, 'aucun bloc de mouvement reduit').toBeGreaterThanOrEqual(1);
    const neutralise = blocsReduits.join('\n');

    //  Les selecteurs qui declarent une transition, HORS de ces blocs.
    const horsBlocs = blocsReduits.reduce((reste, bloc) => reste.replace(bloc, ''), CSS_NU);
    const animants = [...horsBlocs.matchAll(/([^{}]+)\{([^}]*transition\s*:[^}]*)\}/g)].map((c) =>
      (c[1] ?? '').trim(),
    );

    expect(animants.length, 'aucune transition relevee hors des blocs reduits').toBeGreaterThan(0);

    //  **LA COMPARAISON EST EXACTE, PAS PAR SOUS-CHAINE, ET C'EST UNE MESURE.**
    //  La premiere version cherchait le selecteur dans le TEXTE du bloc de
    //  neutralisation. Elle ne mordait pas : retirer `.ex-bouton` du groupe
    //  neutralise laissait passer, parce que `.ex-bouton:active:not(:disabled)`
    //  — une autre regle du meme bloc — contient `.ex-bouton` comme sous-chaine.
    //  Temoin execute le 02/11/2026 : 31 tests verts sur un defaut reel. Le
    //  controle compare desormais des selecteurs ENTIERS.
    //  L'enveloppe `@media … {` est retiree AVANT de relever les regles : sans
    //  cela, la premiere capture vaut `@media (prefers-reduced-motion: reduce)`
    //  et les vrais selecteurs sont avales par le corps.
    const contenu = neutralise.replace(/@media[^{]*\{/g, '');
    const neutralises = new Set(
      [...contenu.matchAll(/([^{}]+)\{[^{}]*\}/g)].flatMap((c) =>
        (c[1] ?? '').split(',').map((partie) => partie.trim()),
      ),
    );

    const oublies = animants.filter((selecteurs) =>
      //  Un selecteur groupe (`a,\n b`) est couvert des que CHACUNE de ses
      //  parties l'est : c'est la partie qui porte la transition.
      selecteurs
        .split(',')
        .map((partie) => partie.trim())
        .some((partie) => partie !== '' && !neutralises.has(partie)),
    );
    expect(oublies, `selecteurs animes sans neutralisation : ${JSON.stringify(oublies)}`).toEqual(
      [],
    );
  });
});
