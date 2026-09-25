/**
 * Le contrat de la page Framework — LOT 6, `T2`.
 *
 * **LA FORME EST CELLE QUE LA PILE A SERVIE, RELEVEE LE 13/09/2026.** Un bouchon
 * prouve ce qu'on a ecrit dans le bouchon, jamais ce que l'API fait -- §7.43,
 * et deux defauts sont tombes ainsi en `T11` du LOT 5.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminFramework,
  CODES_FRAMEWORK,
  RESPONSABILITES_FRAMEWORK,
  validerLaPageFramework,
} from './framework.js';

const UNE_PAGE = {
  responsabilites: [
    {
      type_de_responsabilite: 'DSM',
      titulaires: [{ identifiant: 'a1', prenom: 'Lea', nom: 'Martin' }],
      chemin_detaille: '/entites/BORDEA00/framework/responsabilites/dsm',
    },
    //  BOOSTER n'a PAS de page propre : l'annexe A §10.1 n'en donne qu'a DSM et ESM.
    { type_de_responsabilite: 'BOOSTER', titulaires: [], chemin_detaille: null },
  ],
  cercles: [
    {
      identifiant: 'c1',
      code: 'DATA',
      nom: 'Data',
      description: 'Le cercle Data',
      jeton_de_couleur: 'bleu',
      booster: { identifiant: 'a1', prenom: 'Lea', nom: 'Martin' },
      membres_actifs: 12,
      chemin_detaille: '/entites/BORDEA00/framework/cercles/DATA',
    },
    //  **LE COUPLE DU §7.42** : un cercle SANS jeton. `color_token` est nullable
    //  au catalogue, et `str(None)` a servi « None » sur 100 % des cercles.
    {
      identifiant: 'c2',
      code: 'FORGE',
      nom: 'Forge',
      description: null,
      jeton_de_couleur: null,
      booster: null,
      membres_actifs: 0,
      chemin_detaille: '/entites/BORDEA00/framework/cercles/FORGE',
    },
  ],
  bureaux: [
    {
      identifiant: 'b1',
      code: 'BDS',
      nom: 'Bureau des sports',
      description: null,
      localisation: 'Bordeaux',
      responsables: [{ identifiant: 'a2', prenom: 'Tess', nom: 'Durand' }],
      chemin_detaille: '/entites/BORDEA00/framework/bureaux/BDS',
    },
  ],
};

describe('les responsabilites', () => {
  it('sont les QUATRE du cahier §6.2', () => {
    expect([...RESPONSABILITES_FRAMEWORK]).toEqual(['DSM', 'ESM', 'BOOSTER', 'OFFICE_MANAGER']);
  });
});

describe('les codes exploitables', () => {
  it('n’annoncent AUCUN 403, et c’est le point', () => {
    //  La matrice §5 accorde la Lecture aux HUIT roles sans distinction : il n'y
    //  a aucun role a refuser. Un 403 declare ici promettrait une distinction
    //  que la route ne fait pas.
    expect(CODES_FRAMEWORK).not.toContain(403);
    expect(CODES_FRAMEWORK).toContain(401);
    expect(CODES_FRAMEWORK).toContain(404);
  });
});

describe('le chemin', () => {
  it('encode son segment et refuse un code vide', () => {
    expect(cheminFramework('BORDEA 00')).toContain('BORDEA%2000');
    expect(cheminFramework('x').endsWith('/framework')).toBe(true);
    //  Un code vide rendrait le chemin de la LISTE des entites.
    expect(() => cheminFramework('')).toThrow(TypeError);
  });
});

describe('le validateur', () => {
  it('traduit les trois familles', () => {
    const p = validerLaPageFramework(UNE_PAGE);
    expect(p.responsabilites).toHaveLength(2);
    expect(p.cercles).toHaveLength(2);
    expect(p.bureaux).toHaveLength(1);
    expect(p.responsabilites[0]?.titulaires[0]?.nom).toBe('Martin');
    expect(p.bureaux[0]?.responsables).toHaveLength(1);
  });

  it('distingue un chemin ABSENT de page d’un chemin vide', () => {
    const p = validerLaPageFramework(UNE_PAGE);
    expect(p.responsabilites[0]?.cheminDetaille).toBe(
      '/entites/BORDEA00/framework/responsabilites/dsm',
    );
    //  `null` dit « il n'y a pas de page ». `''` dirait « elle existe et son
    //  adresse est inconnue ».
    expect(p.responsabilites[1]?.cheminDetaille).toBeNull();
  });

  it('rend `null` — et NON la chaine « None » — sur un cercle sans jeton', () => {
    //  **LE CAS QUI A COUTE `T10-8`**, servi sur 100 % des cercles pendant deux
    //  lots. Le couple est dans le decor : un cercle avec jeton, un sans.
    const p = validerLaPageFramework(UNE_PAGE);
    expect(p.cercles[0]?.jetonDeCouleur).toBe('bleu');
    expect(p.cercles[1]?.jetonDeCouleur).toBeNull();
    expect(p.cercles[1]?.jetonDeCouleur).not.toBe('None');
  });

  it('garantit qu’un cercle a TOUJOURS un nom, meme sans couleur', () => {
    //  Le critere de sortie n°4 : la couleur n'est jamais l'unique information.
    //  Ce test ne porte pas sur un affichage mais sur la STRUCTURE du contrat.
    const p = validerLaPageFramework(UNE_PAGE);
    for (const cercle of p.cercles) {
      expect(cercle.nom.length).toBeGreaterThan(0);
      expect(cercle.code.length).toBeGreaterThan(0);
    }
  });

  it.each(['responsabilites', 'cercles', 'bureaux'])('refuse une page sans « %s »', (famille) => {
    //  Une famille ABSENTE n'est pas une famille VIDE : les confondre ferait
    //  afficher « aucun cercle » sur une reponse tronquee.
    const partielle: Record<string, unknown> = { ...UNE_PAGE };
    delete partielle[famille];
    expect(() => validerLaPageFramework(partielle)).toThrow(TypeError);
  });

  it('refuse un `membres_actifs` qui n’est pas un entier', () => {
    const casse = {
      ...UNE_PAGE,
      cercles: [{ ...UNE_PAGE.cercles[0], membres_actifs: '12' }],
    };
    expect(() => validerLaPageFramework(casse)).toThrow(TypeError);
  });

  it('refuse un jeton de couleur ABSENT, la ou `null` est accepte', () => {
    //  **LE TEMOIN QUI REND LE PRECEDENT NON TRIVIAL.** Un validateur qui
    //  traduirait l'absence en `null` passerait les deux, et une reponse
    //  tronquee ressemblerait a un cercle sans couleur.
    const sansJeton: Record<string, unknown> = { ...UNE_PAGE.cercles[0] };
    delete sansJeton['jeton_de_couleur'];
    expect(() => validerLaPageFramework({ ...UNE_PAGE, cercles: [sansJeton] })).toThrow(TypeError);
  });
});
