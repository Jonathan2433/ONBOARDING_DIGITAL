/**
 * Le contrat des liens internes — LOT 6, `T8`, `MVP-L06-US005`.
 *
 * LE TEST CENTRAL N'EST PAS UN REFUS
 *
 *   « Les URL sont validees » se satisfait tout seul quand `urlEstServable` rend
 *   `false` sur tout (§7.39). Chaque refus est donc apparie a un temoin qui ne
 *   differe QUE par la valeur en cause — le `s` de `https`, les deux barres
 *   obliques, le protocole.
 *
 * ET UNE ASYMETRIE QU'IL FAUT MESURER
 *
 *   L'API NORMALISE la casse du protocole avant d'ecrire. Une verification
 *   cliente qui comparerait la casse brute refuserait « HTTPS://… » que l'API
 *   ACCEPTE — un garde-fou a faux positifs, §7.25. Un test l'exige.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminCreationDeLien,
  cheminGestionDesLiens,
  cheminLiensInternes,
  cheminModificationDeLien,
  cheminOrdreDesLiens,
  CODES_LIENS_INTERNES,
  GABARIT_CHEMIN_LIENS_INTERNES,
  peutGererLesLiensInternes,
  PROTOCOLES_DE_LIEN_AUTORISES,
  ROLES_GESTION_DES_LIENS_INTERNES,
  TYPES_DE_LIEN_NOMMES,
  urlEstServable,
  validerLesLiensInternes,
  validerUnLienInterneServi,
} from './liens.js';

function lien(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'l1',
    libelle: 'Hub',
    url: 'https://hub.exemple.test/',
    type_de_lien: 'HUB',
    description: null,
    reference_d_icone: null,
    rang: 0,
    actif: true,
    version: 1,
    ...modifications,
  };
}

function charge(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  const liens = [lien()];
  return { liens, nombre_de_liens: liens.length, ...modifications };
}

describe('le chemin des liens internes', () => {
  it('vient du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_LIENS_INTERNES).toBe('/api/v1/entities/{code}/liens');
    expect(CODES_LIENS_INTERNES).toContain(200);
    expect(CODES_LIENS_INTERNES).toContain(401);
    expect(CODES_LIENS_INTERNES).toContain(404);
  });

  it('encode le code, et REFUSE une chaine vide', () => {
    expect(cheminLiensInternes('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/liens');
    expect(cheminLiensInternes('a/b')).toBe('/api/v1/entities/a%2Fb/liens');
    //  Sans la garde, le chemin obtenu designerait la LISTE des entites.
    expect(() => cheminLiensInternes('')).toThrow(TypeError);
  });
});

describe('les protocoles autorises — DEC-587, QO-120', () => {
  it('sont LUS DU MANIFESTE, jamais recopies ici', () => {
    expect([...PROTOCOLES_DE_LIEN_AUTORISES]).toEqual(['https']);
    expect(PROTOCOLES_DE_LIEN_AUTORISES).not.toContain('http');
  });

  it('nomme les QUATRE types du §15.3, dont l’OTHER que « autres » impose', () => {
    expect([...TYPES_DE_LIEN_NOMMES]).toEqual(['HUB', 'ACADEMY', 'SHAREPOINT', 'OTHER']);
  });
});

describe('urlEstServable — la TROISIEME barriere, pas la premiere', () => {
  it('accepte une adresse https complete, et la casse du protocole', () => {
    expect(urlEstServable('https://hub.exemple.test/')).toBe(true);
    expect(urlEstServable('https://hub.exemple.test/chemin?q=a#f')).toBe(true);
    //  **L'API NORMALISE LA CASSE ET ACCEPTE CECI.** Refuser ici serait un faux
    //  positif, et un garde-fou a faux positifs apprend a passer outre (§7.25).
    expect(urlEstServable('HTTPS://hub.exemple.test/')).toBe(true);
  });

  it('refuse http — et le temoin ne differe que par le « s »', () => {
    expect(urlEstServable('http://hub.exemple.test/')).toBe(false);
    expect(urlEstServable('https://hub.exemple.test/')).toBe(true);
  });

  it('refuse un protocole hostile — et le temoin porte la MEME charge', () => {
    expect(urlEstServable('javascript:alert(1)')).toBe(false);
    expect(urlEstServable('data:text/html,<script>alert(1)</script>')).toBe(false);
    expect(urlEstServable('vbscript:msgbox(1)')).toBe(false);
    //  Ce n'est PAS le texte « alert(1) » qui est refuse, c'est le protocole.
    expect(urlEstServable('https://exemple.test/alert(1)')).toBe(true);
  });

  it('EXIGE UN HOTE — une liste de protocoles ne suffit pas, c’est mesure', () => {
    //  Ces trois-la ont pour protocole « https » cote API : mesure du
    //  22/09/2026. Une verification qui s'arreterait au protocole les
    //  accepterait, et aucune n'adresse de ressource.
    expect(urlEstServable('https:alert(1)')).toBe(false);
    expect(urlEstServable('https:/hub.exemple.test')).toBe(false);
    expect(urlEstServable('https://')).toBe(false);
    expect(urlEstServable('https:///chemin')).toBe(false);
    //  LE TEMOIN — seul l'hote est ajoute.
    expect(urlEstServable('https://hub.exemple.test')).toBe(true);
  });

  it('refuse une adresse sans protocole, forme relative comprise', () => {
    expect(urlEstServable('hub.exemple.test')).toBe(false);
    expect(urlEstServable('//hub.exemple.test/')).toBe(false);
    expect(urlEstServable('')).toBe(false);
  });

  it('rend false plutot que de lever — une carte fautive n’emporte pas la page', () => {
    expect(() => urlEstServable('n’importe quoi : ! ?')).not.toThrow();
    expect(urlEstServable('n’importe quoi : ! ?')).toBe(false);
  });
});

describe('validerLesLiensInternes', () => {
  it('rend la liste, ses champs facultatifs a null et son compte', () => {
    const valide = validerLesLiensInternes(charge());
    expect(valide.nombreDeLiens).toBe(1);
    expect(valide.liens[0]?.libelle).toBe('Hub');
    expect(valide.liens[0]?.url).toBe('https://hub.exemple.test/');
    expect(valide.liens[0]?.description).toBeNull();
    expect(valide.liens[0]?.referenceDIcone).toBeNull();
    expect(valide.liens[0]?.actif).toBe(true);
  });

  it('accepte une entite SANS aucun lien — un etat legitime', () => {
    const vide = validerLesLiensInternes({ liens: [], nombre_de_liens: 0 });
    expect(vide.liens).toHaveLength(0);
    expect(vide.nombreDeLiens).toBe(0);
  });

  it('refuse un tableau ABSENT — ce n’est pas un tableau vide', () => {
    expect(() => validerLesLiensInternes({ nombre_de_liens: 0 })).toThrow(TypeError);
    expect(() => validerLesLiensInternes('liens')).toThrow(TypeError);
  });

  it('refuse un compte qui ne correspond PAS — deux sources, une grandeur', () => {
    expect(() => validerLesLiensInternes(charge({ nombre_de_liens: 7 }))).toThrow(
      /nombre_de_liens vaut 7 pour 1 lien/,
    );
  });

  it('refuse des rangs NON strictement croissants — l’ordre est TOTAL cote API', () => {
    const desordre = [lien({ identifiant: 'a', rang: 1 }), lien({ identifiant: 'b', rang: 0 })];
    expect(() =>
      validerLesLiensInternes({ liens: desordre, nombre_de_liens: desordre.length }),
    ).toThrow(/rangs non strictement croissants/);

    //  Deux rangs EGAUX sont refuses aussi : l'index unique partiel de `T1` les
    //  interdit, et les accepter ici masquerait une API qui aurait cesse de trier.
    const egaux = [lien({ identifiant: 'a', rang: 0 }), lien({ identifiant: 'b', rang: 0 })];
    expect(() => validerLesLiensInternes({ liens: egaux, nombre_de_liens: egaux.length })).toThrow(
      /rangs non strictement croissants/,
    );

    //  LE TEMOIN — croissants, ils passent.
    const ordonnes = [lien({ identifiant: 'a', rang: 0 }), lien({ identifiant: 'b', rang: 3 })];
    expect(
      validerLesLiensInternes({ liens: ordonnes, nombre_de_liens: ordonnes.length }).liens,
    ).toHaveLength(2);
  });

  it('refuse un champ manquant, et distingue l’ABSENCE de null', () => {
    expect(() => validerLesLiensInternes(charge({ liens: [lien({ url: undefined })] }))).toThrow(
      TypeError,
    );
    expect(() => validerLesLiensInternes(charge({ liens: [lien({ actif: 'oui' })] }))).toThrow(
      /actif/,
    );
    expect(() => validerLesLiensInternes(charge({ liens: [lien({ rang: 1.5 })] }))).toThrow(/rang/);
    //  `description` a `null` est LEGITIME : le §15.3 la declare facultative.
    expect(validerLesLiensInternes(charge()).liens[0]?.description).toBeNull();
    //  `description` absente est une reponse MALFORMEE.
    const sansDescription = lien();
    delete sansDescription['description'];
    expect(() => validerLesLiensInternes(charge({ liens: [sansDescription] }))).toThrow(TypeError);
  });

  it('ne NORMALISE pas l’URL servie — elle est rendue telle quelle', () => {
    //  L'API l'a deja normalisee a l'ecriture ; la retoucher ici donnerait DEUX
    //  endroits ou une meme adresse serait reecrite, et le second finirait par
    //  diverger (§7.27, `DEC-466`).
    const servi = validerLesLiensInternes(
      charge({ liens: [lien({ url: 'https://Hub.Exemple.TEST/Chemin' })] }),
    );
    expect(servi.liens[0]?.url).toBe('https://Hub.Exemple.TEST/Chemin');
  });
});

describe('la gestion des liens — T10, lue du manifeste depuis T8', () => {
  it('les roles sont les TROIS de la creation de contenu, declares separement', () => {
    expect([...ROLES_GESTION_DES_LIENS_INTERNES].sort()).toEqual(['ADM-E', 'ESM', 'SUPER']);
  });

  it.each(['EMP', 'NEW', 'DSM', 'BOOST', 'OFFICE'])('« %s » ne se le voit PAS proposer', (role) => {
    //  Le §19 n'a ni colonne DSM ni BOOST ni OFFICE — une ABSENCE de colonne,
    //  et c'est le §13 qui les met a tiret (T8).
    expect(peutGererLesLiensInternes([role])).toBe(false);
  });

  it('un ESM se le voit proposer', () => {
    expect(peutGererLesLiensInternes(['ESM'])).toBe(true);
  });

  it('les quatre chemins d’ecriture, encodes', () => {
    expect(cheminGestionDesLiens('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/liens/gestion');
    expect(cheminCreationDeLien('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/liens');
    expect(cheminOrdreDesLiens('BORDEAUX')).toBe('/api/v1/entities/BORDEAUX/liens/ordre');
    expect(cheminModificationDeLien('BORDEAUX', 'l1')).toBe('/api/v1/entities/BORDEAUX/liens/l1');
  });

  it('validerUnLienInterneServi valide un OBJET seul, meme forme qu’une entree de liste', () => {
    const servi = validerUnLienInterneServi(lien());
    expect(servi.identifiant).toBe('l1');
    expect(servi.actif).toBe(true);
  });
});
