/**
 * Le bouton « Reporter un bug » — LOT 10, `T11`, `MVP-L10-US005`.
 *
 * CE FICHIER PROUVE QUATRE CHOSES
 *
 *   1. le formulaire est fermé par défaut, un `<details>` natif ;
 *   2. un envoi reussi affiche une confirmation et vide les champs ;
 *   3. un 401 affiche un message DISTINCT de l'echec reseau — §7.21, ne pas
 *      dire « reessayez » a quelqu'un de deconnecte ;
 *   4. `chemin_de_page` vient de `window.location.pathname`, jamais d'une
 *      prop — ce composant n'en recoit aucune, voir son en-tete.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { BoutonSignalerUnBug } from './BoutonSignalerUnBug';

afterEach(cleanup);

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function servir(reponseEcriture: { charge: unknown; statut: number }): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/bug-reports')) {
      return Promise.resolve(json(reponseEcriture.charge, reponseEcriture.statut));
    }
    throw new Error(`URL non attendue : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function ouvrirEtRemplir(description = 'Le bouton ne repond pas.'): void {
  fireEvent.click(screen.getByText('Reporter un bug'));
  fireEvent.change(screen.getByLabelText(/Description du problème/), {
    target: { value: description },
  });
}

describe('le bouton « Reporter un bug »', () => {
  it('est ferme par defaut — un `<details>` natif', () => {
    render(<BoutonSignalerUnBug />);
    const details = screen.getByText('Reporter un bug').closest('details');
    expect(details?.hasAttribute('open')).toBe(false);
  });

  it('envoie `chemin_de_page` depuis `window.location.pathname`, et confirme l’envoi', async () => {
    const appel = servir({
      charge: { identifiant: 's1', etat: 'new', cree_le: '2026-10-21T10:00:00+00:00' },
      statut: 201,
    });
    window.history.pushState({}, '', '/entites/bordeaux/framework');

    render(<BoutonSignalerUnBug />);
    ouvrirEtRemplir();
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));

    await waitFor(() => {
      expect(screen.getByText('Signalement envoyé. Merci de votre aide.')).toBeTruthy();
    });

    const appelEcriture = appel.mock.calls.find(([url]) =>
      (url as string).endsWith('/bug-reports'),
    );
    const corps = JSON.parse((appelEcriture?.[1] as RequestInit).body as string) as Record<
      string,
      unknown
    >;
    expect(corps['chemin_de_page']).toBe('/entites/bordeaux/framework');
    expect(corps['description']).toBe('Le bouton ne repond pas.');
    expect(corps).not.toHaveProperty('etapes_de_reproduction');
  });

  it('affiche un message DISTINCT sur un 401 — §7.21, jamais « reessayez »', async () => {
    servir({ charge: { erreur: { code: 'session_invalide', message: 'x' } }, statut: 401 });

    render(<BoutonSignalerUnBug />);
    ouvrirEtRemplir();
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));

    await waitFor(() => {
      expect(screen.getByText('Vous devez être connecté pour signaler un bug.')).toBeTruthy();
    });
    expect(screen.queryByText(/réessayez/)).toBeNull();
  });

  it('affiche l’echec reseau sur toute autre erreur', async () => {
    servir({ charge: { erreur: { code: 'validation_invalide', message: 'x' } }, statut: 422 });

    render(<BoutonSignalerUnBug />);
    ouvrirEtRemplir();
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));

    await waitFor(() => {
      expect(screen.getByText(/L’envoi a échoué/)).toBeTruthy();
    });
  });

  it('ne soumet rien quand la description est vide', () => {
    const appel = servir({ charge: {}, statut: 201 });
    render(<BoutonSignalerUnBug />);
    fireEvent.click(screen.getByText('Reporter un bug'));
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));
    expect(appel).not.toHaveBeenCalled();
  });
});
