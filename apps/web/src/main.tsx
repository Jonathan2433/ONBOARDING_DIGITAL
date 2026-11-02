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

import { appliquerLeTheme, lireLeThemeStocke } from '@onboarding/ui';

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
//  **CE PARAGRAPHE A ETE FAUX PENDANT TOUT LE CHANTIER `E1` A `E3`, ET C'EST
//  NOUS QUI L'AVONS RENDU FAUX.** Il disait : « les 7 noms communs portent des
//  valeurs IDENTIQUES dans les deux feuilles, donc l'ordre ne change rien
//  aujourd'hui », et il concluait qu'on laissait deliberement `styles.css`
//  prevaloir « si elle diverge un jour ».
//
//  Elle a diverge le 01/11/2026, quand `E1` a refondu les neutres de la charte,
//  et personne ne l'a vu : mesure du 02/11/2026 sur le CSS BATI, cinq des sept
//  noms differaient en theme CLAIR -- le theme de premiere visite depuis `S9` --
//  et c'est bien la feuille d'ecran qui gagnait. L'application affichait la
//  palette v1 pendant que `jetons.test.ts` mesurait la v2. §7.21 de la
//  passation : un contrôle juste hier peut etre faux aujourd'hui.
//
//  Depuis `E4`, `styles.css` NE DECLARE PLUS AUCUN JETON — elle les emploie
//  seulement — et `make ecrans-check` refuse qu'une feuille d'ecran en
//  redeclare un. L'ordre des deux imports n'a donc plus de consequence, et ce
//  n'est plus une promesse mais une propriete que le controle tient.
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

//  **LA PREFERENCE DE THEME EST APPLIQUEE ICI, UNE FOIS, AVANT TOUT RENDU —
//  chantier front hors lot, S9 (`DEC-672`/`DEC-673`).** `BoutonBasculerTheme`
//  n'est monte que sur DEUX pages (`CadreApplicatif`, `PageNationale`) : sans
//  cette ligne, un chargement direct de `/statut`, d'une page d'erreur ou d'un
//  ecran de connexion ne lirait JAMAIS `localStorage`, et un choix « sombre »
//  fait ailleurs semblerait s'etre perdu sur CES pages precises — memorise
//  par appareil doit vouloir dire sur TOUTE page, pas seulement celles qui
//  portent le bouton.
appliquerLeTheme(lireLeThemeStocke() ?? 'clair');

const hote = document.getElementById('racine');
if (hote === null) {
  throw new Error('element hote « racine » absent de index.html : rien a monter');
}

createRoot(hote).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
