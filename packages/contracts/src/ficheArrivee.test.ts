/**
 * Le contrat de la fiche d'arrivee — LOT 7, `T2`, `MVP-L07-US001`.
 *
 * `id` ET `version` NULS ENSEMBLE, OU AUCUN DES DEUX — c'est ce que le
 * validateur exige, et c'est le seul point structurel propre a ce contrat :
 * le reste suit exactement `validerLaFiche` de `profil.ts` (LOT 5).
 */

import { describe, expect, it } from 'vitest';

import {
  cheminFicheArrivee,
  CODES_FICHE_ARRIVEE,
  GABARIT_CHEMIN_FICHE_ARRIVEE,
  validerLaFicheArrivee,
} from './ficheArrivee.js';

function fiche(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'a1',
    version: 1,
    state: 'draft',
    entity_membership_id: 'm1',
    person_id: 'p1',
    first_name: 'Ada',
    last_name: 'Lovelace',
    preferred_name: null,
    arrival_date: '2026-10-01',
    metier: 'Consultante',
    statut: 'mission',
    client: 'Client A',
    dsm: 'Jean Dupont',
    cercle_principal: { code: 'DATA', nom: 'Data', jeton_de_couleur: '#5853FF' },
    short_intro: null,
    fun_fact: null,
    validated_at: null,
    published_at: null,
    recent_until: null,
    ...modifications,
  };
}

describe('le chemin de la fiche d’arrivee', () => {
  it('vient du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_FICHE_ARRIVEE).toBe(
      '/api/v1/entities/{code}/people/{appartenance}/arrival-profile',
    );
    expect(CODES_FICHE_ARRIVEE).toContain(200);
    expect(CODES_FICHE_ARRIVEE).toContain(403);
    expect(CODES_FICHE_ARRIVEE).toContain(404);
  });

  it('encode ses deux segments', () => {
    expect(cheminFicheArrivee('BORDEA00', 'a b')).toBe(
      '/api/v1/entities/BORDEA00/people/a%20b/arrival-profile',
    );
  });

  it('refuse un code ou une appartenance vide', () => {
    expect(() => cheminFicheArrivee('', 'a1')).toThrow(TypeError);
    expect(() => cheminFicheArrivee('BORDEA00', '')).toThrow(TypeError);
  });
});

describe('validerLaFicheArrivee', () => {
  it('accepte une fiche complete, deja creee', () => {
    const validee = validerLaFicheArrivee(fiche());
    expect(validee.identifiant).toBe('a1');
    expect(validee.version).toBe(1);
    expect(validee.cerclePrincipal).toEqual({
      code: 'DATA',
      nom: 'Data',
      jetonDeCouleur: '#5853FF',
    });
  });

  it('accepte id et version NULS ENSEMBLE — aucune ligne arrival_profile encore', () => {
    const validee = validerLaFicheArrivee(
      fiche({ id: null, version: null, cercle_principal: null }),
    );
    expect(validee.identifiant).toBeNull();
    expect(validee.version).toBeNull();
    expect(validee.cerclePrincipal).toBeNull();
  });

  it('refuse id nul et version non nulle — les deux doivent etre nuls ENSEMBLE', () => {
    expect(() => validerLaFicheArrivee(fiche({ id: null }))).toThrow(TypeError);
  });

  it('refuse version nulle et id non nul', () => {
    expect(() => validerLaFicheArrivee(fiche({ version: null }))).toThrow(TypeError);
  });

  it('refuse une charge utile non objet', () => {
    expect(() => validerLaFicheArrivee(null)).toThrow(TypeError);
    expect(() => validerLaFicheArrivee([fiche()])).toThrow(TypeError);
  });

  it('refuse un champ textuel obligatoire absent', () => {
    const sansPrenom = fiche();
    delete sansPrenom['first_name'];
    expect(() => validerLaFicheArrivee(sansPrenom)).toThrow(TypeError);
  });
});
