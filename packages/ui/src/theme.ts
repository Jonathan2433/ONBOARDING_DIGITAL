/**
 * La bascule clair/sombre — chantier front hors lot, S9 (`DEC-672`/`DEC-673`).
 *
 * LE CLAIR EST TOUJOURS LE DEFAUT, ET C'EST UN ARBITRAGE EXPLICITE
 *
 *   `jetons.css` suivait `prefers-color-scheme` depuis le LOT 1 `T5` — un choix
 *   juste pour la seule page de statut de l'epoque, jamais reconsidere quand le
 *   chantier a etendu ces jetons a toute l'application metier. Mesure du
 *   27/10/2026 : un systeme regle en sombre faisait basculer le trombinoscope,
 *   le Framework et la page nationale, SANS AUCUN bouton pour revenir au clair
 *   — l'inverse du prototype et du site reel (`exalt-company.com`), qui n'ont
 *   ni l'un ni l'autre de variante sombre. Arbitrage de Jonathan du
 *   27/10/2026 : le clair est desormais TOUJOURS le theme de premiere visite,
 *   quelle que soit la preference systeme ; un bouton explicite
 *   (`BoutonBasculerTheme`, `apps/web`) permet de choisir le sombre.
 *
 * `data-theme` SUR `<html>`, JAMAIS UNE CLASSE
 *
 *   Un attribut nomme ce qu'il porte ; une classe (`.sombre`) se lirait comme
 *   un style parmi d'autres parmi ceux qu'un composant pourrait poser.
 *   `:root[data-theme='sombre']` (`jetons.css`) remplace desormais
 *   `@media (prefers-color-scheme: dark)`. L'ABSENCE d'attribut est le clair :
 *   `:root` porte deja ses valeurs, et poser `data-theme="clair"` serait une
 *   valeur qu'aucun CSS ne lit.
 *
 * `localStorage`, PAR APPAREIL — JAMAIS UN COMPTE NI UN COOKIE
 *
 *   Une preference d'affichage locale a l'appareil, jamais une donnee de
 *   compte : rien dans le corpus ne decide qu'elle doive survivre a un
 *   changement de machine, et inventer une route API pour la porter serait une
 *   colonne sans consommateur (§6.5). `localStorage` peut lever — navigation
 *   privee, stockage bloque, quota depasse — et CHAQUE acces est donc protege :
 *   une lecture ou une ecriture impossible degrade vers le comportement par
 *   defaut (clair), jamais une exception qui casserait la page.
 */

export type Theme = 'clair' | 'sombre';

/** La seule cle lue ou ecrite par ce module — une constante, jamais recopiee. */
export const CLE_DE_STOCKAGE_DU_THEME = 'onboarding-theme';

function stockageDisponible(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    //  Navigation privee de certains navigateurs, ou stockage desactive par
    //  une politique : `localStorage` leve a l'ACCES, pas seulement a l'usage.
    return null;
  }
}

/**
 * Le theme choisi sur CET appareil, ou `null` si rien n'a jamais ete choisi —
 * auquel cas l'appelant doit retenir `'clair'`, jamais deviner `'sombre'`.
 */
export function lireLeThemeStocke(): Theme | null {
  const stockage = stockageDisponible();
  if (stockage === null) {
    return null;
  }
  try {
    const valeur = stockage.getItem(CLE_DE_STOCKAGE_DU_THEME);
    return valeur === 'clair' || valeur === 'sombre' ? valeur : null;
  } catch {
    return null;
  }
}

/**
 * Applique le theme au document ET le memorise sur cet appareil.
 *
 * **NE LEVE JAMAIS.** Un bouton de preference d'affichage qui casserait la
 * page serait pire que l'absence de memorisation (§7.20 de la passation : une
 * barriere qui echoue doit degrader, jamais se faire passer pour une
 * affirmation qu'elle ne tient pas).
 */
export function appliquerLeTheme(theme: Theme): void {
  if (theme === 'sombre') {
    document.documentElement.setAttribute('data-theme', 'sombre');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  const stockage = stockageDisponible();
  if (stockage !== null) {
    try {
      stockage.setItem(CLE_DE_STOCKAGE_DU_THEME, theme);
    } catch {
      //  Stockage plein ou bloque a l'ECRITURE seule (quota depasse) : la
      //  preference ne survivra pas a un rechargement, mais la bascule reste
      //  effective pour la session en cours.
    }
  }
}
