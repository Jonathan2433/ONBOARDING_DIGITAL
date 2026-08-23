/**
 * Racine applicative et routeur.
 *
 * LOT 1, `T5` pour la page de statut · LOT 3, `T11` pour les huit ecrans.
 *
 * LE ROUTEUR ARRIVE ICI, ET C'EST `DEC-456` QUI LE PERMET
 *
 *   `DEC-456` n'installait pas React Router « **faute d'usage avant le LOT 4** »,
 *   et son motif etait explicite : « installer cinq bibliotheques sans usage
 *   ajouterait une surface d'audit sans contrepartie ».
 *
 *   **`T11` cree cet usage une etape plus tot que prevu** : les huit ecrans
 *   d'authentification appartiennent au LOT 3. La condition de `DEC-456` est donc
 *   remplie, et le cahier §17.1 **nomme React Router** dans sa pile — ecrire un
 *   routeur maison serait ignorer ce qui EST decide, ce qui est le §6.5 a
 *   l'envers.
 *
 *   **Les quatre autres bibliotheques restent hors du depot**, et c'est le meme
 *   raisonnement applique honnetement : deux formulaires de deux champs n'ont pas
 *   d'usage pour React Hook Form ni Zod — l'API est de toute facon « l'autorite
 *   finale » sur la validation, regle 5 — trois mutations ponctuelles n'ont pas
 *   d'usage pour TanStack Query, et aucun composant complexe n'appelle Radix UI.
 *   Les installer serait exactement la surface d'audit sans contrepartie que
 *   `DEC-456` refuse.
 *
 * `BrowserRouter` ET NON `HashRouter`
 *
 *   Les liens de magic link sont des URL reelles, envoyees par courriel : une
 *   ancre `#` y serait fragile et n'atteindrait jamais le serveur. Le repli
 *   `try_files {path} /index.html` du `Caddyfile.execution` — pose en `T7`, qui
 *   l'anticipait — sert `index.html` pour toute adresse inconnue, ce qui est la
 *   condition pour qu'un lien profond fonctionne au **rechargement**.
 *
 * LA FRONTIERE D'ERREUR ENVELOPPE LE ROUTEUR, ET NON L'INVERSE
 *
 *   Une exception levee dans une page doit etre rattrapee **au-dessus** du routeur
 *   (cahier §17.4). L'inverse laisserait une page blanche sur l'ecran d'erreur
 *   lui-meme.
 */
import type { JSX } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router';

import { FrontiereErreur } from './FrontiereErreur';
import { Cadre } from './pages/Cadre';
import { PageConnexion } from './pages/PageConnexion';
import { PageConnexionAdministrateur } from './pages/PageConnexionAdministrateur';
import { CadreApplicatif } from './pages/CadreApplicatif';
import { PageDeconnexion } from './pages/PageDeconnexion';
import { PageEntite } from './pages/PageEntite';
import { PageLien } from './pages/PageLien';
import { PageLienEnvoye } from './pages/PageLienEnvoye';
import { Page403, Page404, PageErreur } from './pages/PagesErreur';
import { PageStatut } from './pages/PageStatut';
import { CHEMINS } from './routes';
import './pages/auth.css';

export function App(): JSX.Element {
  return (
    <FrontiereErreur>
      <BrowserRouter>
        <Routes>
          <Route path={CHEMINS.statut} element={<PageStatut />} />
          <Route path={CHEMINS.connexion} element={<PageConnexion />} />
          <Route path={CHEMINS.lienEnvoye} element={<PageLienEnvoye />} />
          <Route path={CHEMINS.lien} element={<PageLien />} />
          <Route path={CHEMINS.connexionAdministrateur} element={<PageConnexionAdministrateur />} />
          <Route path={CHEMINS.deconnexion} element={<PageDeconnexion />} />
          <Route path={CHEMINS.interdit} element={<Page403 />} />
          <Route path={CHEMINS.introuvable} element={<Page404 />} />
          <Route path={CHEMINS.erreur} element={<PageErreur />} />
          {/*
            LOT 4, `T2` puis `T3` — L'ENTITE CONSULTEE VIT DANS L'ADRESSE, ET LE
            CADRE LA PORTE.

            **C'est une route de MISE EN PAGE**, pas une page : `CadreApplicatif`
            resout l'entite, l'affiche dans l'en-tete, et rend ses enfants par
            `Outlet`. Toute page interne ajoutee dessous herite donc de
            l'en-tete **par construction** -- ce que le cahier §23.3 exige, « doit
            etre visible dans l'en-tete de l'application », et ce que le critere
            de sortie de la roadmap redit, « l'entite active est visible sur
            TOUTES les pages internes ».

            `T4` posera ses six rubriques ici, en enfants. Elles n'auront rien a
            faire pour afficher l'entite, et rien a oublier.
          */}
          <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
            <Route index element={<PageEntite />} />
          </Route>
          {/*
            **LE FOURRE-TOUT REND LA PAGE 404, ET NON UNE REDIRECTION.**
            Rediriger vers `/404` changerait l'URL et ferait perdre a
            l'utilisateur l'adresse qu'il avait suivie -- or c'est justement la
            seule information utile pour comprendre son erreur.
          */}
          <Route path="*" element={<Page404 />} />
        </Routes>
      </BrowserRouter>
    </FrontiereErreur>
  );
}

/**
 * Le cadre, reexporte pour que les tests des pages ne dependent pas d'un chemin
 * interne. Rien d'autre n'en a besoin.
 */
export { Cadre };
