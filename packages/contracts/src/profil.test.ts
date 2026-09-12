/**
 * Le contrat de la fiche profil, cote TypeScript — LOT 5, `T4`.
 *
 * **LE VALIDATEUR DOIT DISTINGUER « ABSENT » DE « NUL ».** Un champ manquant est
 * une reponse malformee ; un champ a `null` est une donnee absente, ce qui est
 * legitime -- un consultant sans mission n'a pas de client. Les confondre ferait
 * passer une reponse tronquee pour un profil incomplet, et c'est exactement la
 * classe de defaut ou l'echec produit la meme observation que le succes.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminDePhotoOuNul,
  cheminProfil,
  CODES_PROFIL,
  CONTRAT_API,
  GABARIT_CHEMIN_PROFIL,
  validerLaFiche,
} from './index';

const UN_CERCLE = { code: 'tech', nom: 'Cercle Tech', jeton_de_couleur: 'bleu' };

const UNE_FICHE = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  //  §18.4 — servie depuis `T11` : sans elle, aucun ecran ne peut ecrire.
  version: 7,
  person_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  first_name: 'Ada',
  last_name: 'Lovelace',
  preferred_name: null,
  professional_category: 'consultant',
  arrival_date: '2026-01-15',
  short_bio: 'Ingenieure.',
  fun_fact: null,
  metier: 'Ingenieure logicielle',
  statut: 'mission',
  client: 'Client Alpha',
  dsm: 'Dominique Lesmanager',
  cercle_principal: UN_CERCLE,
  cercles_secondaires: [UN_CERCLE],
  responsabilites: [{ type: 'BOOSTER', cercle: 'Cercle Tech', bureau: null }],
  //  LOT 5, T5 : le MEME chemin que la liste annonce, valide par la MEME fonction.
  photo: '/api/v1/entities/bordeaux/people/0f8fad5b-d9cb-469f-a165-70867728950e/photo',
};

describe('le chemin', () => {
  it('est lu du manifeste et encode ses DEUX segments', () => {
    const declare = CONTRAT_API.endpoints.find((e) => e.cle === 'ficheDuProfil');
    expect(GABARIT_CHEMIN_PROFIL).toBe(declare?.chemin);
    expect(cheminProfil('bor deaux', 'a/b')).toBe('/api/v1/entities/bor%20deaux/people/a%2Fb');
  });

  it('leve sur un segment vide plutot que de viser la LISTE', () => {
    expect(() => cheminProfil('', 'x')).toThrow(TypeError);
    expect(() => cheminProfil('bordeaux', '')).toThrow(TypeError);
  });

  it('n’annonce AUCUN 403 — la matrice §5 ne distingue aucun role', () => {
    expect([...CODES_PROFIL].sort((a, b) => a - b)).toEqual([200, 401, 404]);
  });
});

describe('le validateur', () => {
  it('accepte une fiche complete et traduit vers le camelCase', () => {
    const fiche = validerLaFiche(UNE_FICHE);
    expect(fiche.prenom).toBe('Ada');
    expect(fiche.presentation).toBe('Ingenieure.');
    expect(fiche.funFact).toBeNull();
    expect(fiche.cerclePrincipal?.jetonDeCouleur).toBe('bleu');
    //  **LE TEMOIN DE `T10-8`** : un jeton PRESENT est servi tel quel. Le cas
    //  sans jeton est juste en dessous ; separes, aucun des deux ne prouverait
    //  la difference.
    expect(fiche.cerclesSecondaires).toHaveLength(1);
    expect(fiche.responsabilites[0]?.bureau).toBeNull();
  });

  it('accepte un cercle dont le JETON vaut `null`, et refuse un jeton mal type', () => {
    //  **`T10-8`.** `circle.color_token` est nullable au catalogue ; le typer
    //  en chaine faisait servir « None » par l'API.
    const fiche = validerLaFiche({
      ...UNE_FICHE,
      cercle_principal: { code: 'tech', nom: 'Cercle Tech', jeton_de_couleur: null },
    });
    expect(fiche.cerclePrincipal?.jetonDeCouleur).toBeNull();
    expect(fiche.cerclePrincipal?.nom).toBe('Cercle Tech');

    expect(() =>
      validerLaFiche({
        ...UNE_FICHE,
        cercle_principal: { code: 'tech', nom: 'Cercle Tech', jeton_de_couleur: 42 },
      }),
    ).toThrow(TypeError);
  });

  it('accepte un profil SANS aucune relation', () => {
    const fiche = validerLaFiche({
      ...UNE_FICHE,
      metier: null,
      statut: null,
      client: null,
      dsm: null,
      cercle_principal: null,
      cercles_secondaires: [],
      responsabilites: [],
    });
    expect(fiche.metier).toBeNull();
    expect(fiche.cerclePrincipal).toBeNull();
    expect(fiche.cerclesSecondaires).toEqual([]);
  });

  //  **« ABSENT » N'EST PAS « NUL »**, et chaque champ facultatif a son test.
  it.each(['preferred_name', 'short_bio', 'fun_fact', 'metier', 'statut', 'client', 'dsm'])(
    'refuse « %s » ABSENT, alors qu’il accepte « %s » a null',
    (champ) => {
      const ampute: Record<string, unknown> = { ...UNE_FICHE };
      delete ampute[champ];
      expect(() => validerLaFiche(ampute)).toThrow(TypeError);
      expect(() => validerLaFiche({ ...UNE_FICHE, [champ]: null })).not.toThrow();
    },
  );

  it('refuse une VERSION qui n’est pas un entier — §18.4', () => {
    //  La concurrence optimiste repose entierement dessus : une version
    //  flottante ou textuelle rendrait la comparaison suivante fausse SANS RIEN
    //  DIRE. Et son absence est refusee comme celle de n'importe quel champ
    //  exige : c'est le cas qui a coute le defaut `T11-6`, ou le client envoyait
    //  un corps sans version et recevait 422 de l'API.
    expect(() => validerLaFiche({ ...UNE_FICHE, version: '7' })).toThrow(TypeError);
    expect(() => validerLaFiche({ ...UNE_FICHE, version: 7.5 })).toThrow(TypeError);
    expect(() => validerLaFiche({ ...UNE_FICHE, version: null })).toThrow(TypeError);
  });

  it.each([
    'id',
    'version',
    'person_id',
    'first_name',
    'last_name',
    'professional_category',
    'arrival_date',
  ])('refuse « %s » absent — il est obligatoire', (champ) => {
    const ampute: Record<string, unknown> = { ...UNE_FICHE };
    delete ampute[champ];
    expect(() => validerLaFiche(ampute)).toThrow(TypeError);
  });

  it.each(['cercles_secondaires', 'responsabilites'])(
    'refuse « %s » absent — sinon une liste vide serait indistinguable',
    (champ) => {
      const ampute: Record<string, unknown> = { ...UNE_FICHE };
      delete ampute[champ];
      expect(() => validerLaFiche(ampute)).toThrow(TypeError);
    },
  );

  it('refuse un cercle principal qui n’est ni objet ni null', () => {
    expect(() => validerLaFiche({ ...UNE_FICHE, cercle_principal: 'tech' })).toThrow(TypeError);
  });

  it('refuse un non-objet', () => {
    expect(() => validerLaFiche(null)).toThrow(TypeError);
    expect(() => validerLaFiche([])).toThrow(TypeError);
  });
});

// ===========================================================================
//  LOT 5, T5 — la photo : LA MEME fonction que le trombinoscope
// ===========================================================================

describe('la photo de la fiche', () => {
  it('accepte le chemin, et `null`', () => {
    expect(validerLaFiche(UNE_FICHE).photo).toBe(UNE_FICHE.photo);
    expect(validerLaFiche({ ...UNE_FICHE, photo: null }).photo).toBeNull();
  });

  it('refuse le champ ABSENT — meme regle que dans la liste', () => {
    const ampute: Record<string, unknown> = { ...UNE_FICHE };
    delete ampute['photo'];
    expect(() => validerLaFiche(ampute)).toThrow(TypeError);
  });

  it('est validee par EXACTEMENT la meme fonction que la liste', () => {
    //  **LA PROPRIETE QUI COMPTE, ET LA SEULE FACON DE LA PROUVER.**
    //
    //  Deux validateurs qui accepteraient aujourd'hui les memes valeurs
    //  divergeraient au premier changement, et l'un accepterait alors ce que
    //  l'autre refuse -- sans qu'aucun test de l'un ou de l'autre ne le voie.
    //
    //  Comparer leurs verdicts sur un echantillon ne prouverait rien : deux
    //  implementations distinctes peuvent concorder sur tous les cas essayes.
    //  Ce qui se prouve est l'IDENTITE du message d'erreur, que seule une source
    //  partagee peut garantir a l'octet.
    const mauvais = 'miniatures/abc123.jpg';
    let messageFiche = '';
    let messageListe = '';
    try {
      validerLaFiche({ ...UNE_FICHE, photo: mauvais });
    } catch (erreur) {
      messageFiche = (erreur as Error).message;
    }
    try {
      cheminDePhotoOuNul({ photo: mauvais });
    } catch (erreur) {
      messageListe = (erreur as Error).message;
    }
    expect(messageFiche).not.toBe('');
    expect(messageFiche).toBe(messageListe);
  });
});
