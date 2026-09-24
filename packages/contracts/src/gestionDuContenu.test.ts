/**
 * L'ecriture editoriale, le cycle de vie d'un contenu et sa gestion — LOT 6,
 * `T10`, `MVP-L06-US004` (3/3).
 *
 * LE TEST LE PLUS UTILE N'EST PAS UN REFUS : C'EST QUE LES DEUX GRILLES
 * D'ECRITURE RESTENT DEUX DECLARATIONS, ET QUE L'UNE INCLUT STRICTEMENT L'AUTRE
 *
 *   `rolesCreationDeContenu` (§13, une seule ligne) et `rolesEcritureEditoriale`
 *   (la meme, UNIE aux deux roles de portee locale) ne sont pas interchangeables :
 *   un Booster peut modifier la page de son cercle sans pouvoir en creer une.
 *   Confondre les deux cles accorderait ou retirerait un droit a tort — c'est
 *   exactement ce que le test Python miroir, cote API, exige aussi.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminArchivageDuContenu,
  cheminCreationDePage,
  cheminEcritureDuContenu,
  cheminPageDeGestion,
  cheminPagesDeGestion,
  cheminPublication,
  cheminRestaurationDuContenu,
  peutCreerUnContenu,
  peutEditerUnContenu,
  peutRestaurerUnContenu,
  ROLES_CREATION_DE_CONTENU,
  ROLES_ECRITURE_EDITORIALE,
  ROLES_RESTAURATION_D_UN_CONTENU,
  validerLaPageCreee,
  validerLaPageDeContenuPourEdition,
  validerLaTransitionDeContenu,
  validerLEcritureDuContenu,
  validerLesPagesDeGestion,
} from './gestionDuContenu.js';

describe('les deux grilles d’ecriture', () => {
  it('la creation est les TROIS roles de portee entite, sans BOOST ni OFFICE', () => {
    expect([...ROLES_CREATION_DE_CONTENU].sort()).toEqual(['ADM-E', 'ESM', 'SUPER']);
  });

  it('l’ecriture editoriale INCLUT STRICTEMENT la creation', () => {
    for (const role of ROLES_CREATION_DE_CONTENU) {
      expect(ROLES_ECRITURE_EDITORIALE).toContain(role);
    }
    expect(ROLES_ECRITURE_EDITORIALE).toContain('BOOST');
    expect(ROLES_ECRITURE_EDITORIALE).toContain('OFFICE');
    expect(ROLES_ECRITURE_EDITORIALE.length).toBeGreaterThan(ROLES_CREATION_DE_CONTENU.length);
  });

  it('un Booster peut se voir PROPOSER d’ecrire, jamais de creer', () => {
    expect(peutCreerUnContenu(['BOOST'])).toBe(false);
    expect(peutEditerUnContenu(['BOOST'])).toBe(true);
  });

  it.each(['EMP', 'NEW', 'DSM'])('« %s » ne se voit RIEN proposer', (role) => {
    expect(peutCreerUnContenu([role])).toBe(false);
    expect(peutEditerUnContenu([role])).toBe(false);
  });

  it('la restauration est une declaration DISTINCTE, non alias, des deux autres', () => {
    expect(ROLES_RESTAURATION_D_UN_CONTENU).not.toBe(ROLES_CREATION_DE_CONTENU);
    expect(ROLES_RESTAURATION_D_UN_CONTENU).not.toBe(ROLES_ECRITURE_EDITORIALE);
    //  Un Booster archive la page de son cercle et ne la restaure pas — §13, §18,
    //  cahier §10.1, trois sources concordantes (T7).
    expect(peutRestaurerUnContenu(['BOOST'])).toBe(false);
    expect(peutEditerUnContenu(['BOOST'])).toBe(true);
  });
});

describe('les chemins, lus du manifeste', () => {
  it('la creation et l’ecriture encodent le code et l’identifiant de page', () => {
    expect(cheminCreationDePage('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/pages');
    expect(cheminEcritureDuContenu('BORDEAUX', 'p1')).toBe(
      '/api/v1/entities/BORDEAUX/pages/p1/contenu',
    );
  });

  it('les trois transitions ont chacune leur propre chemin', () => {
    expect(cheminPublication('BORDEAUX', 'p1')).toBe(
      '/api/v1/entities/BORDEAUX/pages/p1/publication',
    );
    expect(cheminArchivageDuContenu('BORDEAUX', 'p1')).toBe(
      '/api/v1/entities/BORDEAUX/pages/p1/archivage',
    );
    expect(cheminRestaurationDuContenu('BORDEAUX', 'p1')).toBe(
      '/api/v1/entities/BORDEAUX/pages/p1/restauration',
    );
  });

  it('les deux routes de gestion — le trou comble par T10', () => {
    expect(cheminPagesDeGestion('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/pages/gestion');
    expect(cheminPageDeGestion('BORDEAUX', 'p1')).toBe(
      '/api/v1/entities/BORDEAUX/pages/p1/gestion',
    );
  });

  it('refusent un code ou un identifiant vide', () => {
    expect(() => cheminCreationDePage('')).toThrow(TypeError);
    expect(() => cheminEcritureDuContenu('BORDEAUX', '')).toThrow(TypeError);
    expect(() => cheminPageDeGestion('', 'p1')).toThrow(TypeError);
  });
});

describe('la lecture pour l’editeur', () => {
  function pageDeGestion(modifications: Record<string, unknown> = {}): Record<string, unknown> {
    return {
      identifiant: 'p1',
      type_de_page: 'CIRCLE',
      titre: 'Mon cercle',
      slug: 'mon-cercle',
      etat: 'draft',
      version: 1,
      circle_id: 'c1',
      office_id: null,
      ...modifications,
    };
  }

  it('valide la liste, tous etats confondus', () => {
    const valeur = { pages: [pageDeGestion(), pageDeGestion({ identifiant: 'p2' })] };
    const resultat = validerLesPagesDeGestion(valeur);
    expect(resultat.pages).toHaveLength(2);
    expect(resultat.pages[0]?.circleId).toBe('c1');
    expect(resultat.pages[0]?.officeId).toBeNull();
  });

  it('un tableau ABSENT n’est pas un tableau vide — leve plutot que de le supposer', () => {
    expect(() => validerLesPagesDeGestion({})).toThrow(TypeError);
  });

  it('la page pour edition PORTE version et etat, que T5 ne porte pas', () => {
    const valeur = {
      identifiant: 'p1',
      type_de_page: 'HOME',
      titre: 'Accueil',
      slug: 'accueil',
      etat: 'draft',
      version: 3,
      publiee_le: null,
      blocs: [{ identifiant: 'b1', type_de_bloc: 'TITLE', ordre: 0, contenu: { texte: 'Salut' } }],
      nombre_de_blocs: 1,
    };
    const resultat = validerLaPageDeContenuPourEdition(valeur);
    expect(resultat.version).toBe(3);
    expect(resultat.etat).toBe('draft');
    expect(resultat.blocs).toHaveLength(1);
  });
});

describe('la creation et l’ecriture', () => {
  it('valide la page creee, toujours en BROUILLON', () => {
    const resultat = validerLaPageCreee({
      identifiant: 'p1',
      type_de_page: 'HOME',
      titre: 'Accueil',
      slug: 'accueil',
      etat: 'draft',
      version: 1,
    });
    expect(resultat.etat).toBe('draft');
    expect(resultat.version).toBe(1);
  });

  it('valide l’ecriture, avec le compte des blocs ARCHIVES', () => {
    const resultat = validerLEcritureDuContenu({
      version: 2,
      blocs: [],
      nombre_de_blocs: 0,
      blocs_archives: 3,
    });
    expect(resultat.blocsArchives).toBe(3);
    expect(resultat.blocs).toHaveLength(0);
  });
});

describe('la transition, UNE forme pour les TROIS actions', () => {
  it('la publication et la restauration ne portent pas archivee_le', () => {
    const resultat = validerLaTransitionDeContenu({
      version: 2,
      etat: 'published',
      publiee_le: '2026-09-24T00:00:00Z',
    });
    expect(resultat.archiveeLe).toBeNull();
    expect(resultat.publieeLe).toBe('2026-09-24T00:00:00Z');
  });

  it('l’archivage porte les DEUX dates, l’une pouvant etre null', () => {
    const resultat = validerLaTransitionDeContenu({
      version: 3,
      etat: 'archived',
      archivee_le: '2026-09-24T00:00:00Z',
      publiee_le: null,
    });
    expect(resultat.archiveeLe).toBe('2026-09-24T00:00:00Z');
    expect(resultat.publieeLe).toBeNull();
  });
});
