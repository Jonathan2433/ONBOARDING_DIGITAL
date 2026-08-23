/**
 * Le contrat du portail national, cote TypeScript — LOT 4, `T1`.
 *
 * CE QUE CES TESTS PROUVENT
 *
 *   Que le chemin est LU DU MANIFESTE et non recopie, et que le validateur
 *   REFUSE ce qui n'a pas la forme attendue. Un validateur qui accepterait tout
 *   donnerait la meme observation qu'un validateur correct sur une reponse
 *   valide -- c'est la quatrieme proposition du §7.0, et c'est pour cela que
 *   chaque refus a son test.
 */
import { describe, expect, it } from 'vitest';

import {
  CHEMIN_ENTITES,
  cheminEntite,
  CODES_ENTITE,
  CODES_ENTITES,
  CONTRAT_API,
  GABARIT_CHEMIN_ENTITE,
  PREFIXE_VERSIONNE,
  validerLesEntites,
  validerUneEntite,
} from './index';

const UNE_ENTITE = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  code: 'bordeaux',
  nom: 'eXalt Bordeaux',
  ville: 'Bordeaux',
};

describe('le chemin des entites', () => {
  it('est lu du manifeste, pas recopie', () => {
    const declare = CONTRAT_API.endpoints.find((e) => e.cle === 'entitesDuPortail');
    expect(declare).toBeDefined();
    expect(CHEMIN_ENTITES).toBe(declare?.chemin);
  });

  it('vit sous le prefixe versionne', () => {
    expect(CHEMIN_ENTITES.startsWith(PREFIXE_VERSIONNE)).toBe(true);
  });

  it('declare 200 et 401, et AUCUN 403', () => {
    //  Aucun 403 : la matrice §5 ne distingue aucun role sur cette ressource.
    //  Un 403 declare ici laisserait croire a un filtrage par role qui n'existe pas.
    expect([...CODES_ENTITES].sort((a, b) => a - b)).toEqual([200, 401]);
  });
});

describe('validerLesEntites', () => {
  it('accepte la forme attendue — LE TEMOIN CENTRAL', () => {
    //  Sans lui, tous les refus ci-dessous seraient satisfaits par un validateur
    //  qui leverait sur tout.
    const valide = validerLesEntites({ entites: [UNE_ENTITE] });
    expect(valide.entites).toHaveLength(1);
    expect(valide.entites[0]).toEqual(UNE_ENTITE);
  });

  it('accepte une liste VIDE', () => {
    //  Une plateforme sans entite active est un etat legitime, pas une erreur.
    expect(validerLesEntites({ entites: [] }).entites).toHaveLength(0);
  });

  it('refuse une reponse qui n est pas un objet', () => {
    expect(() => validerLesEntites([UNE_ENTITE])).toThrow(TypeError);
    expect(() => validerLesEntites(null)).toThrow(TypeError);
    expect(() => validerLesEntites('entites')).toThrow(TypeError);
  });

  it('refuse un objet SANS le champ entites', () => {
    //  **C'EST LE REFUS QUI COMPTE LE PLUS.** Sans lui, `{}` rendrait une liste
    //  vide, indistinguable d'un « aucune entite active » legitime : l'echec
    //  produirait exactement la meme observation que le succes.
    expect(() => validerLesEntites({})).toThrow(TypeError);
    expect(() => validerLesEntites({ entites: null })).toThrow(TypeError);
    expect(() => validerLesEntites({ entites: 'bordeaux' })).toThrow(TypeError);
  });

  it('refuse une entite a laquelle il manque un champ', () => {
    for (const champ of ['id', 'code', 'nom', 'ville']) {
      const tronquee: Record<string, unknown> = { ...UNE_ENTITE };
      delete tronquee[champ];
      expect(() => validerLesEntites({ entites: [tronquee] })).toThrow(TypeError);
    }
  });

  it('refuse un champ non textuel', () => {
    expect(() => validerLesEntites({ entites: [{ ...UNE_ENTITE, nom: 42 }] })).toThrow(TypeError);
    expect(() => validerLesEntites({ entites: [{ ...UNE_ENTITE, ville: null }] })).toThrow(
      TypeError,
    );
  });

  it('IGNORE un champ supplementaire plutot que de lever', () => {
    //  Le validateur PROJETTE : il rend les quatre champs qu'il connait. Lever
    //  sur un champ inconnu rendrait toute evolution de l'API cassante pour un
    //  frontend deja deploye, alors que l'inverse -- un champ manquant -- est
    //  bien une rupture et leve.
    const avecExtra = validerLesEntites({ entites: [{ ...UNE_ENTITE, statut: 'active' }] });
    expect(Object.keys(avecExtra.entites[0]!).sort()).toEqual(['code', 'id', 'nom', 'ville']);
  });
});

describe("le chemin de l'entite consultee — LOT 4, T2", () => {
  it('est lu du manifeste, pas recopie', () => {
    const declare = CONTRAT_API.endpoints.find((e) => e.cle === 'entiteConsultee');
    expect(declare).toBeDefined();
    expect(GABARIT_CHEMIN_ENTITE).toBe(declare?.chemin);
    expect(GABARIT_CHEMIN_ENTITE).toContain('{code}');
  });

  it('declare 200, 401 et 404 — et AUCUN 403', () => {
    //  Pas de 403 : la matrice §5 ne distingue aucun role. Et 404 couvre DEUX
    //  causes -- code inconnu, entite non active -- ce qui est le point : pour
    //  l'appelant, une entite `draft` n'est pas interdite, elle n'existe pas.
    expect([...CODES_ENTITE].sort((a, b) => a - b)).toEqual([200, 401, 404]);
  });

  it('substitue le code et vit sous le prefixe versionne', () => {
    expect(cheminEntite('bordeaux')).toBe(`${PREFIXE_VERSIONNE}/entities/bordeaux`);
    expect(cheminEntite('bordeaux').startsWith(PREFIXE_VERSIONNE)).toBe(true);
  });

  it('ENCODE le code, et ce n est pas une precaution de style', () => {
    //  `entity.code` est une chaine libre de 64 caracteres : le modele ne lui
    //  impose AUCUN motif, mesure sur le schema. Un `/` non encode appellerait une
    //  autre route ; un `..` pourrait en viser une troisieme.
    expect(cheminEntite('bord/eaux')).toBe(`${PREFIXE_VERSIONNE}/entities/bord%2Feaux`);
    expect(cheminEntite('a?b#c')).toBe(`${PREFIXE_VERSIONNE}/entities/a%3Fb%23c`);
    expect(cheminEntite('..')).not.toContain('/../');
  });

  it('LEVE sur un code vide plutot que de rendre le chemin de la LISTE', () => {
    //  Sans ce refus, `cheminEntite('')` rendrait `/api/v1/entities/`, que l'API
    //  sert comme la liste : un 200 avec TOUTES les entites au lieu d'un 404.
    //  L'echec produirait exactement la meme observation qu'un succes.
    expect(() => cheminEntite('')).toThrow(/vide/);
  });

  it('validerUneEntite accepte la forme attendue et refuse le reste', () => {
    const entite = {
      id: '0f8fad5b-d9cb-469f-a165-70867728950e',
      code: 'bordeaux',
      nom: 'eXalt Bordeaux',
      ville: 'Bordeaux',
    };
    expect(validerUneEntite(entite)).toEqual(entite);
    expect(() => validerUneEntite(null)).toThrow(TypeError);
    expect(() => validerUneEntite({ erreur: { code: 'entite_introuvable' } })).toThrow(TypeError);
    for (const champ of ['id', 'code', 'nom', 'ville']) {
      const tronquee: Record<string, unknown> = { ...entite };
      delete tronquee[champ];
      expect(() => validerUneEntite(tronquee)).toThrow(TypeError);
    }
  });
});
