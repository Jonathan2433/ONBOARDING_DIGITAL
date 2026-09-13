/**
 * Le contrat du cycle de vie — LOT 5, `T11`, story `MVP-L05-US007`.
 *
 * LE TEST LE PLUS UTILE N'EST PAS UN REFUS : C'EST QUE LES DEUX GRILLES RESTENT
 * DEUX DECLARATIONS
 *
 *   `rolesCycleDeVie` et `rolesAdministration` portent aujourd'hui les MEMES
 *   trois roles, pour deux raisons differentes -- le §6.1 pour l'un, le §20 pour
 *   l'autre. Un test qui verifierait leur EGALITE figerait la coincidence et
 *   ferait echouer le jour ou la matrice en change une seule, alors que ce serait
 *   le comportement JUSTE.
 *
 *   Ce qui est exige est donc qu'elles soient **declarees separement**, et que
 *   celle du cycle de vie corresponde au service -- ce qu'un test Python
 *   confronte de son cote, sur `ROLES_DU_CYCLE_DE_VIE` de `perimetre.py`.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminArchivage,
  cheminFicheArchivee,
  cheminRestauration,
  CODES_ARCHIVAGE,
  CODES_FICHE_ARCHIVEE,
  CODES_RESTAURATION,
  peutGererLeCycleDeVie,
  ROLES_DU_CYCLE_DE_VIE,
  validerLeResultat,
} from './cycleDeVie.js';
import { ROLES_ADMINISTRATION } from './portail.js';

//  **LES DEUX FORMES SONT CELLES QUE LA PILE A SERVIES, RELEVEES LE 12/09/2026.**
//  Les inventer symetriques est exactement ce qui a coute le defaut `T11-7` :
//  l'archivage ne porte PAS `relations_a_redonner`, et la restauration ne porte
//  ni `relations_closes` ni `sessions_revoquees`.
const UN_ARCHIVAGE = {
  version: 2,
  etat_precedent: 'active',
  etat_nouveau: 'archived',
  sessions_revoquees: 0,
  liens_invalides: 0,
  relations_closes: {
    membership_job_assignment: 1,
    professional_status_assignment: 1,
    circle_membership: 1,
  },
  consultants_sans_dsm: [],
  roles_globaux_conserves: 0,
  relations_futures_conservees: {},
};

const UNE_RESTAURATION = {
  version: 3,
  etat_precedent: 'archived',
  etat_nouveau: 'active',
  relations_a_redonner: [
    'membership_job_assignment',
    'professional_status_assignment',
    'circle_membership',
  ],
};

describe('les roles', () => {
  it('sont les TROIS lignes d’archivage du §6.1', () => {
    expect([...ROLES_DU_CYCLE_DE_VIE].sort()).toEqual(['ADM-E', 'ESM', 'SUPER']);
  });

  it('sont une declaration DISTINCTE de celle de l’administration', () => {
    //  **ON N'EXIGE PAS QU'ELLES DIFFERENT** — elles ne different pas aujourd'hui.
    //  On exige qu'elles soient deux sources : les fusionner ferait suivre l'une
    //  quand la matrice change l'autre, en silence.
    expect(ROLES_DU_CYCLE_DE_VIE).not.toBe(ROLES_ADMINISTRATION);
    expect(ROLES_DU_CYCLE_DE_VIE.length).toBeGreaterThan(0);
  });

  it.each([...ROLES_DU_CYCLE_DE_VIE])('« %s » peut se voir proposer les actions', (role) => {
    expect(peutGererLeCycleDeVie([role])).toBe(true);
  });

  it.each(['EMP', 'NEW', 'DSM', 'BOOST', 'OFFICE'])(
    '« %s » ne se les voit PAS proposer',
    (role) => {
      //  **`DSM` ET `BOOST` SONT LES DEUX QUI COMPTENT** : les deux MODIFIENT un
      //  profil, et le §6.1 les met a tiret sur l'archivage. `T8` l'a mesure --
      //  reutiliser la grille de l'ecriture aurait elargi un droit.
      expect(peutGererLeCycleDeVie([role])).toBe(false);
    },
  );

  it('un cumul suffit dès qu’UN role donne l’action — §23.1', () => {
    expect(peutGererLeCycleDeVie(['EMP', 'DSM', 'ESM'])).toBe(true);
    expect(peutGererLeCycleDeVie([])).toBe(false);
  });
});

describe('les codes exploitables', () => {
  it('les deux ACTIONS annoncent un 409, que la lecture n’a pas', () => {
    //  Le `409` dit « l'ETAT ne permet pas la transition » : archiver un archive,
    //  restaurer un actif. C'est le §23.2 — l'etat prevaut sur le cumul des
    //  roles — et c'est la seule difference de forme entre agir et lire.
    expect(CODES_ARCHIVAGE).toContain(409);
    expect(CODES_RESTAURATION).toContain(409);
    expect(CODES_FICHE_ARCHIVEE).not.toContain(409);
  });

  it('les trois annoncent le 403 ET le 404, deux refus distincts', () => {
    for (const codes of [CODES_ARCHIVAGE, CODES_RESTAURATION, CODES_FICHE_ARCHIVEE]) {
      expect(codes).toContain(403);
      expect(codes).toContain(404);
    }
  });
});

describe('les chemins', () => {
  it('encodent leurs DEUX segments, et se terminent par leur action', () => {
    expect(cheminArchivage('BORDEA 00', 'a/b')).toContain('BORDEA%2000');
    expect(cheminArchivage('x', 'a/b')).toContain('a%2Fb');
    expect(cheminArchivage('x', 'y').endsWith('/archivage')).toBe(true);
    expect(cheminRestauration('x', 'y').endsWith('/restauration')).toBe(true);
    expect(cheminFicheArchivee('x', 'y').endsWith('/fiche-archivee')).toBe(true);
  });

  it('refusent un segment vide — le chemin obtenu viserait une AUTRE cible', () => {
    //  Sur une ACTION, la conséquence est plus grave que sur une lecture : un
    //  segment vide ne rendrait pas une liste, il agirait ailleurs.
    for (const faire of [cheminArchivage, cheminRestauration, cheminFicheArchivee]) {
      expect(() => faire('', 'y')).toThrow(TypeError);
      expect(() => faire('x', '')).toThrow(TypeError);
    }
  });
});

describe('le validateur du resultat', () => {
  it('traduit un ARCHIVAGE, qui ne porte AUCUN `relations_a_redonner`', () => {
    //  **LE CAS QUI A COUTE `T11-7`.** Mon premier validateur exigeait ce champ
    //  sur les deux actions : un archivage reussi etait rejete, et l'ecran
    //  affichait « l'action n'a pas pu aboutir » sur un `200`. Aucun test
    //  bouchonne ne pouvait le dire -- la pile reelle, si.
    const r = validerLeResultat(UN_ARCHIVAGE, 'archivage');
    expect(r.version).toBe(2);
    expect(r.etatPrecedent).toBe('active');
    expect(r.etatNouveau).toBe('archived');
    expect(r.relationsARedonner).toEqual([]);
    expect(r.relationsCloses).toEqual({
      membership_job_assignment: 1,
      professional_status_assignment: 1,
      circle_membership: 1,
    });
    expect(r.sessionsRevoquees).toBe(0);
  });

  it('traduit une RESTAURATION, qui ne porte NI relations closes NI sessions', () => {
    const r = validerLeResultat(UNE_RESTAURATION, 'restauration');
    expect(r.relationsARedonner).toHaveLength(3);
    expect(r.relationsCloses).toEqual({});
    expect(r.sessionsRevoquees).toBe(0);
  });

  it('refuse une reponse d’ARCHIVAGE la ou l’on attend une RESTAURATION', () => {
    //  **C'EST POURQUOI L'ACTION EST UN ARGUMENT ET NON UNE DEVINETTE.** Un
    //  validateur qui deduirait la forme des champs presents accepterait l'une
    //  pour l'autre, et aucun test ne le dirait.
    expect(() => validerLeResultat(UN_ARCHIVAGE, 'restauration')).toThrow(TypeError);
    expect(() => validerLeResultat(UNE_RESTAURATION, 'archivage')).toThrow(TypeError);
  });

  it('refuse un tableau de relations ABSENT sur une restauration', () => {
    //  Le traduire en `[]` ferait afficher « rien a redonner » sur une reponse
    //  qui n'en disait rien — §7.0, quatrieme proposition.
    const sansRelations: Record<string, unknown> = { ...UNE_RESTAURATION };
    delete sansRelations['relations_a_redonner'];
    expect(() => validerLeResultat(sansRelations, 'restauration')).toThrow(TypeError);
  });

  it('refuse une version qui n’est pas un entier', () => {
    //  La concurrence optimiste du §18.4 repose dessus : une version flottante
    //  ou textuelle rendrait la comparaison suivante fausse sans rien dire.
    expect(() => validerLeResultat({ ...UN_ARCHIVAGE, version: '3' }, 'archivage')).toThrow(
      TypeError,
    );
    expect(() => validerLeResultat({ ...UN_ARCHIVAGE, version: 3.5 }, 'archivage')).toThrow(
      TypeError,
    );
  });

  it.each(['etat_precedent', 'etat_nouveau'])('refuse un resultat sans « %s »', (champ) => {
    //  Les DEUX etats : sans le precedent, l'ecran ne peut pas dire d'ou l'on
    //  vient, et `T8` a montre que le chemin compte — `Active` passe par
    //  `Departed`, le §24.1 n'ayant aucune transition directe.
    const partiel: Record<string, unknown> = { ...UN_ARCHIVAGE };
    delete partiel[champ];
    expect(() => validerLeResultat(partiel, 'archivage')).toThrow(TypeError);
  });

  it('refuse une relation qui n’est pas textuelle', () => {
    expect(() =>
      validerLeResultat({ ...UNE_RESTAURATION, relations_a_redonner: [42] }, 'restauration'),
    ).toThrow(TypeError);
  });

  it('refuse un compte de cloture qui n’est pas un entier', () => {
    expect(() =>
      validerLeResultat({ ...UN_ARCHIVAGE, relations_closes: { x: 'un' } }, 'archivage'),
    ).toThrow(TypeError);
  });
});
