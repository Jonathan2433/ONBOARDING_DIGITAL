/**
 * Le contrat du catalogue des taches de reference — LOT 7, `T4`, `ECART-013`.
 *
 * `nombre_de_taches` DOIT EGALER LA TAILLE DU TABLEAU — §7.0, sixieme
 * proposition : deux sources pour une meme grandeur, exactement comme
 * `nombre_de_liens` en `T8` du LOT 6.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminCatalogueDeTaches,
  CODES_CATALOGUE_DE_TACHES,
  GABARIT_CHEMIN_CATALOGUE_DE_TACHES,
  validerLeCatalogueDeTaches,
} from './catalogueDesTaches.js';

function tache(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 't1',
    entity_id: 'e1',
    code: 'badge-acces',
    title: 'Demander un badge d’acces',
    description: null,
    category: 'Materiel',
    active: true,
    ...modifications,
  };
}

describe('le chemin du catalogue de taches', () => {
  it('vient du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_CATALOGUE_DE_TACHES).toBe(
      '/api/v1/entities/{code}/onboarding/task-references',
    );
    expect(CODES_CATALOGUE_DE_TACHES).toContain(200);
    expect(CODES_CATALOGUE_DE_TACHES).toContain(403);
    expect(CODES_CATALOGUE_DE_TACHES).toContain(404);
  });

  it('encode son segment', () => {
    expect(cheminCatalogueDeTaches('a b')).toBe(
      '/api/v1/entities/a%20b/onboarding/task-references',
    );
  });

  it('refuse un code vide', () => {
    expect(() => cheminCatalogueDeTaches('')).toThrow(TypeError);
  });
});

describe('validerLeCatalogueDeTaches', () => {
  it('accepte une liste avec une tache d’entite', () => {
    const catalogue = validerLeCatalogueDeTaches({
      taches: [tache()],
      nombre_de_taches: 1,
    });
    expect(catalogue.nombreDeTaches).toBe(1);
    expect(catalogue.taches[0]).toEqual({
      identifiant: 't1',
      entiteId: 'e1',
      code: 'badge-acces',
      titre: 'Demander un badge d’acces',
      description: null,
      categorie: 'Materiel',
      active: true,
    });
  });

  it('accepte entiteId NUL — une tache GLOBALE, modele §13.1', () => {
    const catalogue = validerLeCatalogueDeTaches({
      taches: [tache({ entity_id: null, code: 'global-badge' })],
      nombre_de_taches: 1,
    });
    expect(catalogue.taches[0]?.entiteId).toBeNull();
  });

  it('accepte un catalogue VIDE — un etat legitime, pas une absence', () => {
    const catalogue = validerLeCatalogueDeTaches({ taches: [], nombre_de_taches: 0 });
    expect(catalogue.taches).toEqual([]);
    expect(catalogue.nombreDeTaches).toBe(0);
  });

  it('refuse un compte qui ne correspond PAS au nombre de taches rendues', () => {
    expect(() => validerLeCatalogueDeTaches({ taches: [tache()], nombre_de_taches: 2 })).toThrow(
      TypeError,
    );
  });

  it('refuse une charge utile non objet', () => {
    expect(() => validerLeCatalogueDeTaches(null)).toThrow(TypeError);
    expect(() => validerLeCatalogueDeTaches([])).toThrow(TypeError);
  });

  it('refuse « taches » absent d’un tableau — un tableau absent n’est pas un tableau vide', () => {
    expect(() => validerLeCatalogueDeTaches({ nombre_de_taches: 0 })).toThrow(TypeError);
  });

  it('refuse un champ textuel obligatoire absent', () => {
    const sansCode = tache();
    delete sansCode['code'];
    expect(() => validerLeCatalogueDeTaches({ taches: [sansCode], nombre_de_taches: 1 })).toThrow(
      TypeError,
    );
  });

  it('refuse un « active » non booleen', () => {
    expect(() =>
      validerLeCatalogueDeTaches({
        taches: [tache({ active: 'oui' })],
        nombre_de_taches: 1,
      }),
    ).toThrow(TypeError);
  });
});
