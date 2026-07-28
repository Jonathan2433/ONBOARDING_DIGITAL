/**
 * Tests du client des endpoints de sante.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * Les charges utiles employees ici sont celles que produit REELLEMENT
 * `apps/api/app/health/routes.py`, relevees sur la stack en marche — pas des
 * exemples de documentation. C'est cette methode qui a mis au jour le trou de
 * securite `T4-1` : un test ecrit a partir du code qu'il protege trouve ce
 * qu'une relecture ne voit pas.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  CHEMIN_READY,
  CHEMIN_VERSION,
  EN_TETE_CORRELATION,
  ErreurSante,
  lireEtatServices,
  lireVersion,
} from './sante';

const CORRELATION = '6a66ca32-40be-4717-83ff-7f8942ea1f8b';

/** Charge utile reelle de `/health/ready` quand tout va bien. */
const READY_NOMINAL = {
  statut: 'pret',
  dependances: [
    { nom: 'postgresql', statut: 'disponible', duree_ms: 0, motif: null },
    { nom: 'redis', statut: 'disponible', duree_ms: 2, motif: null },
    { nom: 'minio', statut: 'disponible', duree_ms: 7, motif: null },
  ],
};

/** Charge utile reelle d'un 503 : Redis arrete, les deux autres tiennent. */
const READY_DEGRADE = {
  statut: 'indisponible',
  dependances: [
    { nom: 'postgresql', statut: 'disponible', duree_ms: 1, motif: null },
    { nom: 'redis', statut: 'indisponible', duree_ms: 3, motif: 'ConnectionError' },
    { nom: 'minio', statut: 'disponible', duree_ms: 5, motif: null },
  ],
};

const VERSION_REELLE = {
  version: '0.0.0-dev',
  revision: 'inconnue',
  environnement: 'development',
};

function reponse(
  charge: unknown,
  statut: number,
  correlation: string | null = CORRELATION,
): Response {
  const entetes = new Headers({ 'Content-Type': 'application/json' });
  if (correlation !== null) {
    entetes.set(EN_TETE_CORRELATION, correlation);
  }
  return new Response(JSON.stringify(charge), { status: statut, headers: entetes });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('chemins interroges', () => {
  // Garde-fou de non-regression sur DEC-465 : les endpoints de sante sont HORS
  // du prefixe versionne. Les prefixer par megarde produirait un 404 que rien
  // ne distinguerait d'une API mal deployee.
  it('ne prefixe pas les endpoints de sante par le contrat versionne', () => {
    expect(CHEMIN_READY).toBe('/health/ready');
    expect(CHEMIN_VERSION).toBe('/health/version');
    expect(CHEMIN_READY.startsWith('/api/v1')).toBe(false);
    expect(CHEMIN_VERSION.startsWith('/api/v1')).toBe(false);
  });
});

describe('lireEtatServices', () => {
  it('lit un 200 et rend les trois dependances', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse(READY_NOMINAL, 200)));

    const { charge, correlation } = await lireEtatServices();

    expect(charge.statut).toBe('pret');
    expect(charge.dependances).toHaveLength(3);
    expect(charge.dependances.map((d) => d.nom)).toEqual(['postgresql', 'redis', 'minio']);
    expect(correlation).toBe(CORRELATION);
  });

  // LE test qui compte : un 503 porte le diagnostic, il ne doit pas etre jete.
  it('lit un 503 comme un etat degrade exploitable, sans lever', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse(READY_DEGRADE, 503)));

    const { charge } = await lireEtatServices();

    expect(charge.statut).toBe('indisponible');
    const redis = charge.dependances.find((d) => d.nom === 'redis');
    expect(redis?.statut).toBe('indisponible');
    expect(redis?.motif).toBe('ConnectionError');
    // Temoin : les dependances saines restent lisibles dans le meme 503.
    expect(charge.dependances.find((d) => d.nom === 'postgresql')?.statut).toBe('disponible');
  });

  it('leve sur un code inexploitable, en conservant la correlation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse({ detail: 'boom' }, 500)));

    await expect(lireEtatServices()).rejects.toMatchObject({
      name: 'ErreurSante',
      correlation: CORRELATION,
    });
  });

  it('leve sans correlation quand le transport echoue', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const echec = await lireEtatServices().catch((cause: unknown) => cause);

    expect(echec).toBeInstanceOf(ErreurSante);
    expect((echec as ErreurSante).correlation).toBeNull();
    expect((echec as ErreurSante).message).toContain('injoignable');
  });

  it('leve sur une forme de reponse inattendue', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse({ statut: 'douteux' }, 200)));

    await expect(lireEtatServices()).rejects.toThrow(/inattendue/);
  });

  it('leve sur un corps qui n’est pas du JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>502</html>', { status: 200 })),
    );

    await expect(lireEtatServices()).rejects.toThrow(/illisible/);
  });

  it('tolere l’absence de l’en-tete de correlation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse(READY_NOMINAL, 200, null)));

    const { charge, correlation } = await lireEtatServices();

    expect(correlation).toBeNull();
    expect(charge.statut).toBe('pret');
  });
});

describe('lireVersion', () => {
  it('rend version, revision et environnement', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse(VERSION_REELLE, 200)));

    const { charge } = await lireVersion();

    expect(charge).toEqual(VERSION_REELLE);
  });

  // Temoin de discrimination : 503 est exploitable pour `ready`, il ne l'est
  // pas pour `version`. Un client qui accepterait 503 partout afficherait une
  // version qu'il n'a pas lue.
  it('refuse un 503, contrairement a ready', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse(VERSION_REELLE, 503)));

    await expect(lireVersion()).rejects.toThrow(/503/);
  });

  it('leve quand un champ obligatoire manque', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reponse({ version: '1.0.0' }, 200)));

    await expect(lireVersion()).rejects.toThrow(/revision/);
  });
});
