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
import { PageRubrique } from './pages/PageRubrique';
import { PageDeconnexion } from './pages/PageDeconnexion';
import { PageEntite } from './pages/PageEntite';
import { PageLien } from './pages/PageLien';
import { PageLienEnvoye } from './pages/PageLienEnvoye';
import { PageNationale } from './pages/PageNationale';
import { Page403, Page404, PageErreur } from './pages/PagesErreur';
import { PageStatut } from './pages/PageStatut';
import { PageTrombinoscope } from './pages/PageTrombinoscope';
import { PageProfil } from './pages/PageProfil';
import { CHEMINS, RUBRIQUES } from './routes';

/**
 * Les rubriques dont la page est LIVREE — LOT 5, `T10`.
 *
 * **UNE TABLE, PAS UNE CHAINE DE `if`.** Cinq lots vont remplir cette liste ; une
 * condition par rubrique deviendrait illisible, et surtout `make cadre-check`
 * derive les routes de ce fichier -- une forme reguliere reste lisible pour lui.
 */
const PAGES_LIVREES: Readonly<Record<string, JSX.Element | undefined>> = {
  trombinoscope: <PageTrombinoscope />,
};

/**
 * Le suffixe de la fiche profil, DERIVE du chemin declare.
 *
 * `CHEMINS.profil` est absolu ; la route est imbriquee sous `CHEMINS.entite`,
 * donc React Router attend le suffixe RELATIF. Le deriver evite la troisieme
 * copie du meme chemin (§7.27).
 */
const SUFFIXE_PROFIL = CHEMINS.profil.replace(`${CHEMINS.entite}/`, '');
import './pages/auth.css';

export function App(): JSX.Element {
  return (
    <FrontiereErreur>
      <BrowserRouter>
        <Routes>
          {/*
            **LA RACINE EST LA PAGE NATIONALE DEPUIS `T6`.** Cahier §4.1, « une
            page nationale APRES AUTHENTIFICATION », et le diagramme du §8.1 qui
            la place juste apres la connexion. Arbitrage de Jonathan du
            23/08/2026 ; le detail du choix est au-dessus de `CHEMINS`.
          */}
          <Route path={CHEMINS.national} element={<PageNationale />} />
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
            {/*
              LES SIX ROUTES SONT ENGENDREES DEPUIS `RUBRIQUES` — LOT 4, `T4`.

              **Aucune liste recopiee.** Le menu se rend de la meme source, et
              `make cadre-check` confronte les deux : une rubrique ajoutee sans sa
              route, ou l'inverse, fait echouer le controle. §7.27.

              L'accueil est la route `index` -- son suffixe est vide -- et il porte
              sa propre page.

              **DEPUIS `T10` DU LOT 5, LE TROMBINOSCOPE PORTE LA SIENNE AUSSI**, et
              la correspondance est une TABLE plutot qu'une chaine de ternaires :
              chaque lot qui livre sa rubrique y ajoutera une ligne, et `T11` en
              ajoutera une pour le profil. Les rubriques sans page livree gardent
              `PageRubrique`, qui DIT quel lot l'apportera.
            */}
            {RUBRIQUES.map((rubrique) =>
              rubrique.suffixe === '' ? (
                <Route key={rubrique.cle} index element={<PageEntite />} />
              ) : (
                <Route
                  key={rubrique.cle}
                  path={rubrique.suffixe}
                  element={
                    PAGES_LIVREES[rubrique.cle] ?? (
                      <PageRubrique
                        cle={rubrique.cle}
                        libelle={rubrique.libelle}
                        lot={rubrique.lot}
                      />
                    )
                  }
                />
              ),
            )}
            {/*
              **LA FICHE PROFIL A L'ECRAN — la route existe, son contenu est `T11`.**
              « "Voir plus" ouvre le profil » est un critere de `US003`, donc de
              `T10` : le lien doit MENER quelque part. Un lien qui tombe sur le
              fourre-tout 404 est atteignable et inutile, et la navigation serait
              simulee plutot que prouvee -- c'est le motif de `PageRubrique`, pose
              au `T4` du LOT 4.
            */}
            <Route path={SUFFIXE_PROFIL} element={<PageProfil />} />
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
