/**
 * Les deux mécanismes que le cahier §17.2 et §17.4 exigent de tout écran — LOT 4, `T10`.
 *
 * POURQUOI DES CROCHETS PARTAGÉS ET NON UN COMPOSANT
 *
 *   `PageStatut` porte ces deux mécanismes depuis `T5` du LOT 1, et le portail en
 *   a besoin depuis `T10`. Extraire un **composant** aurait imposé un balisage
 *   commun -- or les deux écrans n'ont pas la même feuille : `PageStatut` emploie
 *   les classes neutres de `styles.css`, écrites avant que `packages/ui` existe,
 *   et le portail emploie les jetons du design system. Les faire converger est le
 *   travail de `T11`, qui consolide « les composants du design system que ces
 *   écrans emploient ».
 *
 *   **Ce qui divergerait en silence, c'est la LOGIQUE** : le nettoyage des
 *   écouteurs, la remise à zéro de l'état de copie, le repli quand le
 *   presse-papiers est refusé. Elle est donc extraite, en un seul exemplaire, et
 *   le balisage reste propre à chaque écran.
 *
 * CE QUE LE CAHIER EXIGE, MOT POUR MOT
 *
 *   §17.2 : « Après perte de connexion sur une page déjà chargée, l'utilisateur
 *   voit un état explicite et **aucune action n'est déclarée enregistrée sans
 *   confirmation de l'API**. »
 *
 *   §17.4 : « possibilité de réessayer ; identifiant de corrélation **copiable** ;
 *   aucun écran blanc silencieux. »
 *
 *   **`copiable`, et non « affiché ».** La fiche du LOT 4 écrit « l'identifiant de
 *   corrélation est affiché » ; le cahier prévaut et demande davantage. C'est la
 *   classe de `ECART-023` — une fiche moins exigeante que sa source.
 */
import { useCallback, useEffect, useState } from 'react';

/** L'état de la dernière tentative de copie. */
export type EtatCopie = 'inactif' | 'faite' | 'impossible';

/**
 * La connexion réseau, telle que la page la voit APRÈS son chargement.
 *
 * **`navigator.onLine` SEUL NE SUFFIRAIT PAS.** Il donne l'état à l'instant du
 * rendu ; le §17.2 parle d'une perte de connexion « sur une page **déjà
 * chargée** », donc d'un changement. Ce sont les événements `online` et `offline`
 * qui le portent.
 *
 * **Et il ne dit pas « le service répond ».** Un navigateur en ligne derrière un
 * portail captif rend `true`. C'est pourquoi l'état hors connexion et l'état
 * d'erreur restent **deux états distincts** : les confondre dirait à
 * l'utilisateur de vérifier sa connexion alors que c'est l'API qui est tombée.
 */
export function useEtatDeConnexion(auRetour?: () => void): boolean {
  const [enLigne, setEnLigne] = useState<boolean>(() => navigator.onLine);

  useEffect(() => {
    const passerEnLigne = (): void => {
      setEnLigne(true);
      //  **L'ACTION DE RETOUR EST APPELÉE ICI, DANS LE GESTIONNAIRE.** Un
      //  `setState` synchrone dans un corps d'effet déclenche un rendu en
      //  cascade, et `react-hooks/set-state-in-effect` le refuse à juste titre.
      //  Ce que l'écran affichait est devenu obsolète à la coupure ; c'est
      //  l'événement qui le sait, pas l'effet.
      auRetour?.();
    };
    const passerHorsLigne = (): void => setEnLigne(false);
    window.addEventListener('online', passerEnLigne);
    window.addEventListener('offline', passerHorsLigne);
    return () => {
      window.removeEventListener('online', passerEnLigne);
      window.removeEventListener('offline', passerHorsLigne);
    };
  }, [auRetour]);

  return enLigne;
}

/**
 * L'identifiant de corrélation, copiable — §17.4.
 *
 * **LA COPIE N'EST JAMAIS LE SEUL MOYEN.** Le presse-papiers peut être refusé par
 * le navigateur, et il l'est dans certains contextes non sécurisés. L'état
 * `impossible` existe pour le dire, et l'identifiant reste **sélectionnable à la
 * main** dans le balisage de chaque écran. Un bouton qui échouerait en silence
 * serait pire que pas de bouton — c'est le §7.21, un avertissement faux.
 */
export function useCorrelationCopiable(): {
  readonly etatCopie: EtatCopie;
  readonly copier: (texte: string) => Promise<void>;
  readonly reinitialiser: () => void;
} {
  const [etatCopie, setEtatCopie] = useState<EtatCopie>('inactif');

  const copier = useCallback(async (texte: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(texte);
      setEtatCopie('faite');
    } catch {
      setEtatCopie('impossible');
    }
  }, []);

  const reinitialiser = useCallback(() => setEtatCopie('inactif'), []);

  return { etatCopie, copier, reinitialiser };
}

/**
 * Le message qui accompagne l'état de copie, ou la chaîne vide.
 *
 * **EXTRAIT POUR QUE LES DEUX ÉCRANS DISENT LA MÊME CHOSE.** Deux formulations
 * du même échec apprendraient à l'utilisateur que le comportement diffère selon
 * la page, alors que la cause est la même.
 */
export function messageDeCopie(etat: EtatCopie): string {
  //  **LA FORMULATION EST CELLE QUE `PageStatut` PORTAIT DEJA**, accents compris.
  //  Deux tests de `T5` du LOT 1 l'epinglent, et ils ont raison : c'est un texte
  //  VU par l'utilisateur. En profiter pour la reecrire aurait casse deux tests
  //  pour un gain nul -- et un texte d'interface s'ecrit en francais accentue,
  //  contrairement aux commentaires de ce depot.
  if (etat === 'faite') {
    return 'Identifiant copié dans le presse-papiers.';
  }
  if (etat === 'impossible') {
    return 'Copie refusée par le navigateur : sélectionnez l’identifiant à la main.';
  }
  return '';
}
