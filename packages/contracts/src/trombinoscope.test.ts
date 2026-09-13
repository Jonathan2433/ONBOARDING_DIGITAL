/**
 * Le contrat du trombinoscope, cote TypeScript — LOT 5, `T2`.
 *
 * CE QUE CES TESTS PROUVENT
 *
 *   Que le chemin est LU DU MANIFESTE et non recopie, et que le validateur
 *   REFUSE ce qui n'a pas la forme attendue. Un validateur qui accepterait tout
 *   donnerait la meme observation qu'un validateur correct sur une reponse
 *   valide -- §7.0, quatrieme proposition. Chaque refus a donc son test.
 *
 *   **ET LES QUATRE NOMBRES DE L'ENVELOPPE ONT CHACUN LE LEUR.** C'est la
 *   classe de defaut la plus insidieuse ici : un `total` absent qui vaudrait 0
 *   serait indistinguable d'un trombinoscope legitimement vide.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminTrombinoscope,
  CODES_TROMBINOSCOPE,
  CONTRAT_API,
  GABARIT_CHEMIN_TROMBINOSCOPE,
  LONGUEUR_MAXIMALE_RECHERCHE,
  STATUTS_PROFESSIONNELS,
  TAILLE_PAR_DEFAUT,
  TAILLES_DE_PAGE,
  validerLeTrombinoscope,
} from './index';

const UNE_LIGNE = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  person_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  first_name: 'Ada',
  last_name: 'Lovelace',
  preferred_name: null,
  professional_category: 'consultant',
  arrival_date: '2026-01-15',
  //  LOT 5, T5 : le chemin de la miniature. **Un CHEMIN, jamais des octets.**
  photo: '/api/v1/entities/bordeaux/people/0f8fad5b-d9cb-469f-a165-70867728950e/photo',
  //  LOT 5, T10 : les QUATRE champs du VERSO — §10.1, « le verso presente les
  //  informations professionnelles principales ».
  metier: 'Ingenieure logicielle',
  statut: 'mission',
  client: 'Client Alpha',
  cercle: { code: 'data', nom: 'Data', jeton_de_couleur: 'bleu' },
};

const UNE_PAGE = {
  collaborateurs: [UNE_LIGNE],
  page: 1,
  taille: 25,
  total: 1,
  pages: 1,
};

describe('le chemin', () => {
  it('est lu du manifeste, jamais recopie', () => {
    const declare = CONTRAT_API.endpoints.find((e) => e.cle === 'trombinoscopeDeLEntite');
    expect(GABARIT_CHEMIN_TROMBINOSCOPE).toBe(declare?.chemin);
    expect(GABARIT_CHEMIN_TROMBINOSCOPE).toContain('{code}');
  });

  it('n’annonce AUCUN 403 — la matrice §5 ne distingue aucun role', () => {
    expect([...CODES_TROMBINOSCOPE].sort((a, b) => a - b)).toEqual([200, 401, 404, 422]);
  });

  it('encode le code, sinon le chemin obtenu serait celui d’une autre ressource', () => {
    expect(cheminTrombinoscope('bor deaux/x')).toBe('/api/v1/entities/bor%20deaux%2Fx/people');
  });

  it('leve sur un code vide plutot que de viser la liste des entites', () => {
    expect(() => cheminTrombinoscope('')).toThrow(TypeError);
  });

  it('n’ajoute une chaine de requete que lorsqu’on lui donne des valeurs', () => {
    expect(cheminTrombinoscope('bordeaux')).toBe('/api/v1/entities/bordeaux/people');
    expect(cheminTrombinoscope('bordeaux', 2)).toBe('/api/v1/entities/bordeaux/people?page=2');
    expect(cheminTrombinoscope('bordeaux', 2, 50)).toBe(
      '/api/v1/entities/bordeaux/people?page=2&taille=50',
    );
    expect(cheminTrombinoscope('bordeaux', undefined, 100)).toBe(
      '/api/v1/entities/bordeaux/people?taille=100',
    );
  });
});

describe('les trois tailles', () => {
  it('sont celles du cahier §18.2, et le defaut en fait partie', () => {
    expect(TAILLES_DE_PAGE).toEqual([25, 50, 100]);
    expect(TAILLES_DE_PAGE).toContain(TAILLE_PAR_DEFAUT);
    expect(TAILLE_PAR_DEFAUT).toBe(25);
    expect(Math.max(...TAILLES_DE_PAGE)).toBe(100);
  });
});

describe('le validateur', () => {
  it('accepte une page bien formee et traduit vers le camelCase', () => {
    const page = validerLeTrombinoscope(UNE_PAGE);
    expect(page.collaborateurs[0]).toEqual({
      id: UNE_LIGNE.id,
      personneId: UNE_LIGNE.person_id,
      prenom: 'Ada',
      nom: 'Lovelace',
      nomPrefere: null,
      categorieProfessionnelle: 'consultant',
      dateArrivee: '2026-01-15',
      photo: UNE_LIGNE.photo,
      //  LOT 5, T10 — les quatre du verso, §10.1.
      metier: 'Ingenieure logicielle',
      statut: 'mission',
      client: 'Client Alpha',
      cercle: { code: 'data', nom: 'Data', jetonDeCouleur: 'bleu' },
    });
    expect(page.total).toBe(1);
  });

  it('accepte un nom prefere renseigne', () => {
    const page = validerLeTrombinoscope({
      ...UNE_PAGE,
      collaborateurs: [{ ...UNE_LIGNE, preferred_name: 'Ada L.' }],
    });
    expect(page.collaborateurs[0]?.nomPrefere).toBe('Ada L.');
  });

  it('refuse une reponse sans tableau — sinon elle vaudrait « aucun collaborateur »', () => {
    expect(() => validerLeTrombinoscope({})).toThrow(TypeError);
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: null })).toThrow(TypeError);
  });

  it('refuse un non-objet', () => {
    expect(() => validerLeTrombinoscope(null)).toThrow(TypeError);
    expect(() => validerLeTrombinoscope('texte')).toThrow(TypeError);
  });

  //  **CHACUN DES QUATRE NOMBRES A SON TEST**, parce que l'absence de l'un
  //  d'eux ne doit PAS valoir 0 : 0 est la valeur d'un trombinoscope vide, donc
  //  l'echec produirait la meme observation que le succes.
  it.each(['page', 'taille', 'total', 'pages'])('refuse « %s » absent', (champ) => {
    const ampute: Record<string, unknown> = { ...UNE_PAGE };
    delete ampute[champ];
    expect(() => validerLeTrombinoscope(ampute)).toThrow(TypeError);
  });

  it.each(['page', 'taille', 'total', 'pages'])('refuse « %s » non nombre', (champ) => {
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, [champ]: '1' })).toThrow(TypeError);
  });

  it.each([
    'id',
    'person_id',
    'first_name',
    'last_name',
    'professional_category',
    'arrival_date',
    //  LOT 5, T10. **L'ABSENCE EST REFUSEE AUTANT QUE LE MAUVAIS TYPE** : une
    //  cle manquante signifie que l'API ne sert pas ce champ, donc une AUTRE
    //  version du contrat. La traduire en `null` masquerait la divergence
    //  derriere une valeur parfaitement plausible.
    'metier',
    'statut',
    'client',
    'cercle',
  ])('refuse une ligne dont « %s » manque', (champ) => {
    const ligne: Record<string, unknown> = { ...UNE_LIGNE };
    delete ligne[champ];
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [ligne] })).toThrow(
      TypeError,
    );
  });

  //  ========================================================================
  //  LOT 5, T5 — la photo : un CHEMIN, ou `null`
  //  ========================================================================

  it('accepte `null` — l’appelant sert alors l’avatar neutre du §21.2', () => {
    const page = validerLeTrombinoscope({
      ...UNE_PAGE,
      collaborateurs: [{ ...UNE_LIGNE, photo: null }],
    });
    expect(page.collaborateurs[0]?.photo).toBeNull();
  });

  //  ========================================================================
  //  LOT 5, T10 — les quatre champs du verso
  //  ========================================================================

  it('accepte `null` sur les QUATRE champs du verso — un nouvel arrivant n’a rien', () => {
    //  **LE TEMOIN QUI ENCADRE LA FAMILLE DE REFUS CI-DESSUS.** Sans lui,
    //  l'exigence serait satisfaite par un validateur qui refuse tout : le
    //  defaut `T2-3`, ou huit refus restaient verts pour la mauvaise raison.
    const page = validerLeTrombinoscope({
      ...UNE_PAGE,
      collaborateurs: [{ ...UNE_LIGNE, metier: null, statut: null, client: null, cercle: null }],
    });
    const ligne = page.collaborateurs[0];
    expect(ligne?.metier).toBeNull();
    expect(ligne?.statut).toBeNull();
    expect(ligne?.client).toBeNull();
    expect(ligne?.cercle).toBeNull();
  });

  it('traduit le cercle vers le camelCase, ses TROIS champs ensemble', () => {
    const page = validerLeTrombinoscope(UNE_PAGE);
    expect(page.collaborateurs[0]?.cercle).toEqual({
      code: 'data',
      nom: 'Data',
      jetonDeCouleur: 'bleu',
    });
  });

  it('accepte un cercle dont le JETON vaut `null` — il est nullable au schema', () => {
    //  **`T10-8`.** `circle.color_token` rend `is_nullable = YES` au catalogue.
    //  Le contrat l'exigeait en chaine, si bien que l'API servait `str(None)`,
    //  donc la chaine « None » : un jeton d'apparence plausible qu'aucun ecran
    //  ne reconnait. Le NOM, lui, reste exige -- le §10.1 en depend.
    const cercle = { code: 'data', nom: 'Data', jeton_de_couleur: null };
    const page = validerLeTrombinoscope({
      ...UNE_PAGE,
      collaborateurs: [{ ...UNE_LIGNE, cercle }],
    });
    expect(page.collaborateurs[0]?.cercle).toEqual({
      code: 'data',
      nom: 'Data',
      jetonDeCouleur: null,
    });
  });

  it('refuse un jeton qui n’est NI chaine NI null', () => {
    //  Le temoin de la regle precedente : accepter `null` ne doit pas revenir a
    //  tout accepter.
    const cercle = { code: 'data', nom: 'Data', jeton_de_couleur: 42 };
    expect(() =>
      validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [{ ...UNE_LIGNE, cercle }] }),
    ).toThrow(TypeError);
  });

  it.each(['code', 'nom', 'jeton_de_couleur'])(
    'refuse un cercle dont « %s » manque — le §10.1 les veut ensemble',
    (champ) => {
      //  **L'ABSENCE N'EST PAS `null`**, et c'est ce que ce test fige pour le
      //  jeton depuis `T10-8` : `null` est une valeur que le schema autorise,
      //  une cle ABSENTE est une reponse d'une autre version de l'API.
      //  Le nom, lui, est exige en toute circonstance : sans lui, « jamais la
      //  couleur seule » serait inapplicable.
      const cercle: Record<string, unknown> = { ...UNE_LIGNE.cercle };
      delete cercle[champ];
      expect(() =>
        validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [{ ...UNE_LIGNE, cercle }] }),
      ).toThrow(TypeError);
    },
  );

  it('refuse une photo ABSENTE, alors qu’elle accepte `null`', () => {
    //  **L'ABSENCE N'EST PAS `null`**, et les deux temoins encadrent la regle :
    //  un champ manquant est une reponse malformee, un `null` est une photo non
    //  servable. Sans le second, l'exigence serait satisfaite par un validateur
    //  qui refuse tout.
    const ligne: Record<string, unknown> = { ...UNE_LIGNE };
    delete ligne['photo'];
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [ligne] })).toThrow(
      TypeError,
    );
  });

  it.each([42, true, {}, [], ['/api/v1/x']])('refuse une photo de type %s', (mauvais) => {
    expect(() =>
      validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [{ ...UNE_LIGNE, photo: mauvais }] }),
    ).toThrow(TypeError);
  });

  it('refuse une cle d’objet MinIO deguisee en photo', () => {
    //  **LE CONTROLE LE PLUS UTILE DE CE BLOC.** Si l'API rendait un jour
    //  l'`object_key` au lieu du chemin, tous les tests de type ci-dessus
    //  resteraient verts : c'est une chaine. Seul le prefixe discrimine, et le
    //  §16.1 veut que la disposition du stockage ne sorte jamais.
    for (const cle of ['miniatures/abc123.jpg', 'onboarding-dev-media/x.jpg', '']) {
      expect(() =>
        validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [{ ...UNE_LIGNE, photo: cle }] }),
      ).toThrow(TypeError);
    }
  });

  it('refuse une photo qui porterait les OCTETS en Base64', () => {
    //  Le §16.1 interdit Base64 en propre. Une donnee `data:` est une chaine, et
    //  seul le prefixe versionne la refuse.
    expect(() =>
      validerLeTrombinoscope({
        ...UNE_PAGE,
        collaborateurs: [{ ...UNE_LIGNE, photo: 'data:image/jpeg;base64,/9j/4AAQSkZJRg==' }],
      }),
    ).toThrow(TypeError);
  });

  it('refuse un « preferred_name » qui n’est ni chaine ni null', () => {
    expect(() =>
      validerLeTrombinoscope({
        ...UNE_PAGE,
        collaborateurs: [{ ...UNE_LIGNE, preferred_name: 42 }],
      }),
    ).toThrow(TypeError);
  });

  it('refuse une ligne non objet', () => {
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: ['x'] })).toThrow(TypeError);
  });
});

describe('les filtres — LOT 5, T3', () => {
  it('n’ajoute que les axes renseignes, dans un ordre STABLE', () => {
    expect(cheminTrombinoscope('bordeaux', undefined, undefined, { recherche: 'ada' })).toBe(
      '/api/v1/entities/bordeaux/people?recherche=ada',
    );
    //  Deux appels aux memes filtres doivent rendre la MEME adresse : sinon deux
    //  cles de cache designeraient la meme page.
    const filtres = { statut: 'mission', cercle: 'c-1', recherche: 'ada' };
    expect(cheminTrombinoscope('bordeaux', 1, 25, filtres)).toBe(
      cheminTrombinoscope('bordeaux', 1, 25, filtres),
    );
    expect(cheminTrombinoscope('bordeaux', 1, 25, filtres)).toBe(
      '/api/v1/entities/bordeaux/people?page=1&taille=25&recherche=ada&cercle=c-1&statut=mission',
    );
  });

  it('ecarte une chaine VIDE — « ?recherche= » chercherait le vide', () => {
    expect(cheminTrombinoscope('bordeaux', undefined, undefined, { recherche: '' })).toBe(
      '/api/v1/entities/bordeaux/people',
    );
  });

  it('encode les valeurs de filtre', () => {
    expect(cheminTrombinoscope('bordeaux', undefined, undefined, { recherche: 'a b&c=d' })).toBe(
      '/api/v1/entities/bordeaux/people?recherche=a%20b%26c%3Dd',
    );
  });

  it('declare les deux statuts et la borne du terme cherche', () => {
    expect(STATUTS_PROFESSIONNELS).toEqual(['mission', 'intercontract']);
    expect(LONGUEUR_MAXIMALE_RECHERCHE).toBe(128);
  });
});
