/**
 * Le contrat de l'historique — LOT 5, `T11`, story `MVP-L05-US008`.
 *
 * LE TEST QUI COMPTE EST UN COUPLE, PAS UN REFUS
 *
 *   `null` dit « hors de ton perimetre », `[]` dit « rien a montrer ». Un
 *   validateur qui absorberait l'un dans l'autre passerait **tous** les tests de
 *   refus qu'on pourrait ecrire : il faut les deux cas cote a cote, ne differant
 *   que par la valeur en cause, pour que la difference soit prouvee.
 *
 *   C'est le §7.39 -- un critere negatif se satisfait tout seul -- et le defaut
 *   `T10-8`, ou trois decors posaient toujours la meme valeur.
 */
import { describe, expect, it } from 'vitest';

import {
  AXES_DE_L_HISTORIQUE,
  cheminHistorique,
  CODES_HISTORIQUE,
  validerLHistorique,
} from './historique.js';

const UN_HISTORIQUE = {
  metier: [{ metier: 'Ingenieure logicielle', debut: '2025-06-25T00:00:00Z', fin: null }],
  statut: [
    {
      statut: 'mission',
      client: 'Client Alpha',
      debut: '2025-06-25T00:00:00Z',
      fin: '2026-01-01T00:00:00Z',
    },
    { statut: 'intercontract', client: null, debut: '2026-01-01T00:00:00Z', fin: null },
  ],
  cercle: [
    {
      code: 'DATA',
      nom: 'Donnees',
      type: 'principal',
      debut: '2025-06-25T00:00:00Z',
      fin: null,
    },
  ],
  dsm: [{ dsm: 'Dominique Lesmanager', debut: '2025-06-25T00:00:00Z', fin: null }],
  responsabilites: [
    {
      type: 'BOOSTER',
      cercle: 'Donnees',
      bureau: null,
      debut: '2025-09-01T00:00:00Z',
      fin: null,
    },
  ],
};

describe('le manifeste', () => {
  it('donne les CINQ axes, et ils sont la source unique', () => {
    expect([...AXES_DE_L_HISTORIQUE]).toEqual([
      'metier',
      'statut',
      'cercle',
      'dsm',
      'responsabilites',
    ]);
  });

  it('annonce un 403 ET un 404 — deux refus que l’ecran doit distinguer', () => {
    //  Le `403` dit « pas le droit de lire d'historique » ; le `404` couvre
    //  QUATRE causes indistinguables a dessein, dont « hors de ton perimetre ».
    expect([...CODES_HISTORIQUE].sort((a, b) => a - b)).toEqual([200, 401, 403, 404, 422]);
  });
});

describe('le validateur', () => {
  it('accepte un historique complet et rend les cinq axes — LE TEMOIN', () => {
    const h = validerLHistorique(UN_HISTORIQUE);
    expect(h.metier).toHaveLength(1);
    expect(h.statut).toHaveLength(2);
    expect(h.cercle?.[0]?.nom).toBe('Donnees');
    expect(h.dsm?.[0]?.dsm).toBe('Dominique Lesmanager');
    expect(h.responsabilites?.[0]?.type).toBe('BOOSTER');
  });

  //  ======================================================================
  //  LE COUPLE : `null` n'est pas `[]`
  //  ======================================================================

  it('laisse passer `null` sur un axe HORS PERIMETRE', () => {
    //  Le cas du DSM : le §20 reserve l'historique des ROLES a l'ESM, l'ADM-E et
    //  le SUPER, et le §23.2 fait prevaloir cette interdiction sur le cumul.
    const h = validerLHistorique({ ...UN_HISTORIQUE, responsabilites: null });
    expect(h.responsabilites).toBeNull();
    //  Et les quatre autres axes ne sont pas touches.
    expect(h.metier).toHaveLength(1);
  });

  it('laisse passer `[]` sur un axe VIDE, et ce n’est PAS la meme chose', () => {
    //  **SANS CE SECOND TEST, LE PREMIER NE PROUVE RIEN.** Un validateur qui
    //  rendrait `null` pour tout axe non renseigne passerait celui du dessus.
    const h = validerLHistorique({ ...UN_HISTORIQUE, responsabilites: [] });
    expect(h.responsabilites).toEqual([]);
    expect(h.responsabilites).not.toBeNull();
  });

  it.each([...AXES_DE_L_HISTORIQUE])('refuse un historique dont l’axe « %s » est ABSENT', (axe) => {
    //  **L'ABSENCE N'EST NI `null` NI `[]`** : elle dit que l'API ne sert pas cet
    //  axe, donc qu'on parle a une autre version. La traduire en `null` la ferait
    //  passer pour un refus de perimetre -- une erreur d'un genre tout autre.
    const charge: Record<string, unknown> = { ...UN_HISTORIQUE };
    delete charge[axe];
    expect(() => validerLHistorique(charge)).toThrow(TypeError);
  });

  it('refuse un axe qui n’est ni tableau ni null', () => {
    expect(() => validerLHistorique({ ...UN_HISTORIQUE, dsm: 'aucun' })).toThrow(TypeError);
  });

  //  ======================================================================
  //  Les periodes
  //  ======================================================================

  it('`statut` porte SON client, et le nul de l’intercontrat est accepte', () => {
    //  Le §6.5 du modele met `status` et `client_id` sur la MEME ligne : une
    //  mission et son client sont UNE periode, pas deux axes.
    const h = validerLHistorique(UN_HISTORIQUE);
    expect(h.statut?.[0]?.client).toBe('Client Alpha');
    expect(h.statut?.[1]?.client).toBeNull();
    expect(h.statut?.[1]?.statut).toBe('intercontract');
  });

  it('`fin: null` est une periode COURANTE, et `fin` datee une periode close', () => {
    const h = validerLHistorique(UN_HISTORIQUE);
    expect(h.statut?.[0]?.fin).toBe('2026-01-01T00:00:00Z');
    expect(h.statut?.[1]?.fin).toBeNull();
  });

  it('refuse une periode SANS debut — une periode sans debut n’en est pas une', () => {
    const sansDebut = [{ metier: 'X', fin: null }];
    expect(() => validerLHistorique({ ...UN_HISTORIQUE, metier: sansDebut })).toThrow(TypeError);
  });

  it('refuse une periode qui n’est pas un objet', () => {
    expect(() => validerLHistorique({ ...UN_HISTORIQUE, metier: ['Ingenieure'] })).toThrow(
      TypeError,
    );
  });

  it('NE CONVERTIT PAS les dates — la chaine ISO traverse telle quelle', () => {
    //  Un `new Date()` ici introduirait le fuseau du navigateur DANS le contrat :
    //  une periode close le 1er janvier a 00:00 UTC deviendrait le 31 decembre a
    //  Paris. La conversion appartient a l'ecran, qui sait dans quel fuseau il
    //  affiche.
    const h = validerLHistorique(UN_HISTORIQUE);
    expect(h.metier?.[0]?.debut).toBe('2025-06-25T00:00:00Z');
    expect(typeof h.metier?.[0]?.debut).toBe('string');
  });
});

describe('le chemin', () => {
  it('encode ses DEUX segments', () => {
    const chemin = cheminHistorique('BORDEA 00', 'a/b');
    expect(chemin).toContain('BORDEA%2000');
    expect(chemin).toContain('a%2Fb');
    expect(chemin.endsWith('/historique')).toBe(true);
  });

  it('refuse un segment vide — le chemin obtenu designerait une AUTRE ressource', () => {
    expect(() => cheminHistorique('', 'x')).toThrow(TypeError);
    expect(() => cheminHistorique('x', '')).toThrow(TypeError);
  });
});
