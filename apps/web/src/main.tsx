/**
 * Point d'entree du frontend.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * L'element hote est cherche explicitement et son absence leve : monter dans le
 * vide produirait une page blanche silencieuse, precisement ce que le cahier
 * §17.4 interdit. Ici l'echec est bruyant et immediat.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

//  **LES JETONS SONT CHARGES ICI, ET ILS NE L'ETAIENT PAS.** LOT 4, `T3`.
//
//  `auth.css`, posee en `T11` du LOT 3, emploie 21 proprietes personnalisees.
//  MESURE du 23/08/2026 sur l'application servie : 14 d'entre elles ne
//  resolvaient RIEN -- les six espacements, les deux couleurs de marque, la
//  police, deux rayons et trois tailles -- et les 7 autres ne resolvaient que
//  par ACCIDENT, `styles.css` definissant les memes noms.
//
//  Les huit ecrans d'authentification rendaient donc leurs espacements, leurs
//  rayons et leur typographie avec les defauts du navigateur. **Et `make
//  ecrans-check` passait** : il exigeait qu'aucune couleur LITTERALE ne soit
//  ecrite dans la feuille -- la source -- jamais que les jetons RESOLVENT. Le
//  succes du controle et la justesse de la page sont deux grandeurs
//  differentes (§7.24).
//
//  L'import vient AVANT `styles.css`, et le choix est mesure : les 7 noms
//  communs portent des valeurs IDENTIQUES dans les deux feuilles, donc l'ordre
//  ne change rien aujourd'hui. Le declarer d'abord laisse neanmoins `styles.css`
//  -- propre a la page de statut -- prevaloir si elle diverge un jour, ce qui
//  est le sens voulu : une feuille locale surcharge un jeton global.
import '@onboarding/ui/jetons.css';
//  **ET LES CLASSES DES COMPOSANTS, QUI MANQUAIENT AUSSI.** Trois ecrans du
//  LOT 3 importent `Bouton` de `@onboarding/ui` ; ce composant rend
//  `class="ex-bouton"`, definie par `composants.css` -- et cette feuille n'etait
//  pas chargee davantage.
//
//  MESURE du 23/08/2026 sur l'application servie : le bouton « Recevoir un
//  lien » rendait `border-radius: 0px` et le fond par defaut du navigateur. Les
//  trois boutons des huit ecrans etaient des boutons NUS.
//
//  Et `packages/ui/src/index.ts` le disait, en toutes lettres : « Les styles sont
//  deux feuilles separees, A IMPORTER PAR L'APPLICATION », avec les deux lignes
//  ecrites. Le paquet documentait son emploi ; l'application ne l'a pas suivi, et
//  aucun controle ne regardait.
import '@onboarding/ui/composants.css';

import { App } from './App';
import './styles.css';

const hote = document.getElementById('racine');
if (hote === null) {
  throw new Error('element hote « racine » absent de index.html : rien a monter');
}

createRoot(hote).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
