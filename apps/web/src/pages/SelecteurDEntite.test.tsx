/**
 * Le selecteur d'entite — LOT 4, sous-etape `T8`, story `MVP-L04-US002`.
 *
 * CE FICHIER PROUVE QUATRE CHOSES, ET LA PREMIERE EST LA PLUS IMPORTANTE
 *
 *   1. **le changement d'entite est une NAVIGATION, donc des `<a href>`.** C'est
 *      ce qui rend les regles 1 et 2 du §23.3 vraies par construction -- « ne
 *      modifie pas l'entite principale », « ne transfere pas ses
 *      responsabilites ». Un `<button>` ou un `<select>` laisserait un endroit ou
 *      une ecriture pourrait s'installer plus tard sans que rien ne le dise ;
 *   2. **l'entite courante reste dans la liste et porte `aria-current`.** Sur
 *      l'ATTRIBUT, jamais sur une classe : une classe n'informerait qu'un oeil ;
 *   3. **rien ne s'affiche s'il n'y a rien a choisir.** Un repli vide serait un
 *      arret de tabulation pour un choix inexistant ;
 *   4. **le code est encode dans l'adresse produite.** `entity.code` est une
 *      chaine libre de 64 caracteres, sans motif impose par le modele.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { SelecteurDEntite } from './SelecteurDEntite';

afterEach(cleanup);

const BORDEAUX = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  code: 'bordeaux',
  nom: 'eXalt Bordeaux',
  ville: 'Bordeaux',
};
const LILLE = {
  id: '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d',
  code: 'lille',
  nom: 'eXalt Lille',
  ville: 'Lille',
};

function monter(courante: typeof BORDEAUX, entites: readonly (typeof BORDEAUX)[]): void {
  render(
    <MemoryRouter>
      <SelecteurDEntite courante={courante} entites={entites} />
    </MemoryRouter>,
  );
}

describe("changer d'entite est une navigation", () => {
  it('rend des LIENS, et aucun bouton ni champ de formulaire — §23.3 regles 1 et 2', () => {
    monter(BORDEAUX, [BORDEAUX, LILLE]);

    const liens = screen.getAllByRole('link');
    expect(liens.length).toBe(2);
    for (const lien of liens) {
      expect(lien.getAttribute('href')).toMatch(/^\/entites\//);
    }
    //  AUCUN element d'ecriture. C'est une exigence d'ABSENCE : elle ne se
    //  declare pas, elle se verifie -- sinon un `<button onClick>` ajoute plus
    //  tard passerait inapercu.
    expect(screen.queryAllByRole('button').length).toBe(0);
    expect(screen.queryAllByRole('combobox').length).toBe(0);
    expect(document.querySelectorAll('form,input,select').length).toBe(0);
  });

  it("marque l'entite courante avec aria-current, et une seule", () => {
    monter(BORDEAUX, [BORDEAUX, LILLE]);

    const marques = document.querySelectorAll('[aria-current]');
    expect(marques.length).toBe(1);
    expect(marques[0]?.getAttribute('aria-current')).toBe('true');
    expect(marques[0]?.textContent).toContain('eXalt Bordeaux');
  });

  it("n'affiche RIEN quand il n'y a qu'une entite — aucun arret de tabulation pour rien", () => {
    monter(BORDEAUX, [BORDEAUX]);

    expect(screen.queryAllByRole('link').length).toBe(0);
    expect(document.querySelector('details')).toBeNull();
  });

  it("emploie <details>/<summary>, donc l'etat replie est natif et annonce", () => {
    monter(BORDEAUX, [BORDEAUX, LILLE]);

    const repli = document.querySelector('details');
    expect(repli).not.toBeNull();
    expect(repli?.querySelector('summary')).not.toBeNull();
    //  AUCUN `aria-expanded` ecrit a la main : `<details>` porte son etat, et un
    //  attribut redondant divergerait de lui.
    expect(document.querySelectorAll('[aria-expanded]').length).toBe(0);
  });

  it('encode le code dans l adresse produite', () => {
    const etrange = { ...LILLE, code: 'a b/c?d#e', nom: 'Entite etrange' };
    monter(BORDEAUX, [BORDEAUX, etrange]);

    const liens = screen.getAllByRole('link').map((n) => n.getAttribute('href'));
    expect(liens).toContain('/entites/a%20b%2Fc%3Fd%23e');
    //  Le caractere brut ne doit PAS apparaitre : un `/` non encode changerait
    //  la route atteinte, et un `#` couperait le chemin.
    expect(liens.some((h) => h?.includes('a b/c'))).toBe(false);
  });
});
