/**
 * Les composants de base, eprouves comme un utilisateur les rencontre.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 14 — WCAG 2.2 AA.
 *
 * CE QUE CES TESTS VERIFIENT, ET CE QU'ILS NE PEUVENT PAS VERIFIER
 *
 *   Ils verifient le CONTRAT ACCESSIBLE de chaque composant : role, nom
 *   accessible, activation au clavier, etat annonce, relation entre une region et
 *   son titre. Ce sont les proprietes qu'un lecteur d'ecran expose, et Testing
 *   Library interroge le DOM par ces roles plutot que par des classes CSS — donc
 *   par le meme chemin qu'une technologie d'assistance.
 *
 *   Ils NE verifient PAS le rendu visuel : jsdom n'applique aucune feuille de
 *   style. Le contraste est donc verifie sur les JETONS, par `jetons.test.ts`, et
 *   la coherence entre jetons et CSS par `jetons-css.test.ts`. Il faut le dire
 *   plutot que de laisser croire que ces tests prouvent l'apparence.
 */

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Badge } from './Badge.js';
import { Bouton } from './Bouton.js';
import { Carte } from './Carte.js';
// `?raw` de Vite plutot que `node:fs` : le contenu arrive comme une chaine, sans
// ajouter @types/node au projet. C'est Vite qui lit le disque, et Vitest emploie
// la meme chaine de transformation. Meme motif qu'en T5 pour `types: vite/client`.
import CSS from './composants.css?raw';

// NETTOYAGE EXPLICITE, comme `apps/web/src/FrontiereErreur.test.tsx` depuis `T5`.
//
// Le nettoyage automatique de Testing Library ne s'installe que si Vitest tourne
// avec `globals: true` ; nos deux configurations ne l'activent pas. Sans ce
// `afterEach`, le DOM s'accumule d'un test au suivant, et `getByRole('button')`
// echoue en « Found multiple elements » — mesure du 30/07/2026, 7 tests en echec.
// L'echec etait donc du a l'echafaudage, pas aux composants.
afterEach(() => {
  cleanup();
});

describe('Bouton', () => {
  it('expose un role de bouton et son libelle comme nom accessible', () => {
    render(<Bouton>Relancer la sonde</Bouton>);
    expect(screen.getByRole('button', { name: 'Relancer la sonde' })).toBeTruthy();
  });

  // LE PIEGE DE HTML, ET IL EST SILENCIEUX. Le defaut de `<button>` dans un
  // formulaire est `submit` : un bouton « Annuler » soumettrait le formulaire.
  it('vaut `type="button"` par defaut, et non `submit`', () => {
    render(<Bouton>Annuler</Bouton>);
    expect(screen.getByRole('button').getAttribute('type')).toBe('button');
  });

  it('laisse demander `submit` explicitement', () => {
    render(<Bouton type="submit">Envoyer</Bouton>);
    expect(screen.getByRole('button').getAttribute('type')).toBe('submit');
  });

  it('porte la variante demandee, et `primaire` par defaut', () => {
    const { unmount } = render(<Bouton>Defaut</Bouton>);
    expect(screen.getByRole('button').dataset.variante).toBe('primaire');
    unmount();
    render(<Bouton variante="secondaire">Secondaire</Bouton>);
    expect(screen.getByRole('button').dataset.variante).toBe('secondaire');
  });

  it('est activable, et transmet le clic', () => {
    const clic = vi.fn();
    render(<Bouton onClick={clic}>Agir</Bouton>);
    screen.getByRole('button').click();
    expect(clic).toHaveBeenCalledTimes(1);
  });

  // L'ETAT DESACTIVE EST ANNONCE, pas seulement grise. WCAG 1.4.1.
  it('annonce son etat desactive et ne declenche plus rien', () => {
    const clic = vi.fn();
    render(
      <Bouton disabled onClick={clic}>
        Indisponible
      </Bouton>,
    );
    const bouton = screen.getByRole('button', { name: 'Indisponible' });
    expect((bouton as HTMLButtonElement).disabled).toBe(true);
    bouton.click();
    expect(clic).not.toHaveBeenCalled();
  });
});

describe('Badge', () => {
  it.each(['neutre', 'ok', 'ko', 'marque'] as const)(
    'rend son texte pour le ton %s : la couleur ne porte jamais seule l information',
    (ton) => {
      render(<Badge ton={ton}>Operationnel</Badge>);
      // On cherche le TEXTE, pas la classe : c'est ce qu'un lecteur d'ecran lit.
      expect(screen.getByText('Operationnel').dataset.ton).toBe(ton);
    },
  );

  it('vaut le ton `neutre` par defaut', () => {
    render(<Badge>Inconnu</Badge>);
    expect(screen.getByText('Inconnu').dataset.ton).toBe('neutre');
  });
});

describe('Carte', () => {
  it('sans titre, reste un simple conteneur et n annonce AUCUNE region', () => {
    render(<Carte>Contenu nu</Carte>);
    expect(screen.getByText('Contenu nu')).toBeTruthy();
    // Une `<section>` sans nom accessible n'est pas un repere : ne pas en
    // produire est plus honnete que d'en produire une muette.
    expect(screen.queryByRole('region')).toBeNull();
  });

  it('avec un titre, devient une region NOMMEE par ce titre', () => {
    render(<Carte titre="Etat des dependances">Trois sondes</Carte>);
    const region = screen.getByRole('region', { name: 'Etat des dependances' });
    expect(region).toBeTruthy();
    expect(region.textContent).toContain('Trois sondes');
  });

  it('rend le titre au niveau demande, et `h2` par defaut', () => {
    const { unmount } = render(<Carte titre="Defaut">x</Carte>);
    expect(screen.getByRole('heading', { level: 2, name: 'Defaut' })).toBeTruthy();
    unmount();
    render(
      <Carte titre="Imbriquee" niveauTitre="h3">
        x
      </Carte>,
    );
    expect(screen.getByRole('heading', { level: 3, name: 'Imbriquee' })).toBeTruthy();
  });

  it('donne un identifiant DISTINCT a chaque titre, meme rendues cote a cote', () => {
    render(
      <>
        <Carte titre="Premiere">a</Carte>
        <Carte titre="Seconde">b</Carte>
      </>,
    );
    const a = screen.getByRole('heading', { name: 'Premiere' }).id;
    const b = screen.getByRole('heading', { name: 'Seconde' }).id;
    expect(a).not.toBe('');
    expect(a).not.toBe(b);
  });
});

describe('la feuille des composants ne contourne pas les jetons', () => {
  // SANS CE CONTROLE, une couleur ecrite en dur dans composants.css echapperait
  // au controle de contraste — qui ne lit que les jetons — et la palette validee
  // ne serait plus celle qui s'affiche.
  it('ne declare aucune couleur en dur : tout passe par var(--…)', () => {
    const enDur = CSS.replace(/\/\*[\s\S]*?\*\//g, '').match(
      /#[0-9a-fA-F]{3,8}\b|\brgba?\((?![^)]*var\()/g,
    );
    expect(enDur, `couleurs ecrites en dur : ${JSON.stringify(enDur)}`).toBeNull();
  });

  it('emploie effectivement les jetons, et pas seulement zero couleur en dur', () => {
    // Un fichier vide passerait le controle precedent. Celui-ci l'empeche.
    const usages = CSS.match(/var\(--[a-z0-9-]+\)/g) ?? [];
    expect(usages.length).toBeGreaterThan(20);
  });

  // WCAG 2.4.7 : le focus doit rester visible. Une regle qui l'annulerait —
  // `outline: none` sans remplacement — passerait tous les tests de composant.
  it('garde un focus visible et ne l annule jamais', () => {
    expect(CSS).toContain(':focus-visible');
    expect(CSS).not.toMatch(/outline\s*:\s*(none|0)\s*;/);
  });
});
