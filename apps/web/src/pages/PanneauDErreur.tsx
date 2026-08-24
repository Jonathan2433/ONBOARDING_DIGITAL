/**
 * Ce que le §17.4 exige de tout écran d'erreur du portail — LOT 4, `T10`.
 *
 * SEPT EXIGENCES, ET CE PANNEAU EN PORTE QUATRE
 *
 *   Le §17.4 liste : « pages 403, 404 et erreur générale ; error boundary React ;
 *   messages de champs ; notifications ; **possibilité de réessayer** ;
 *   **identifiant de corrélation copiable** ; **aucun écran blanc silencieux** ».
 *
 *   Ce panneau porte le **réessai**, la **corrélation copiable**, un **message
 *   toujours présent** — donc aucun écran blanc — et l'annonce du résultat de la
 *   copie. Les trois autres sont ailleurs : les pages 403/404/erreur sont dans
 *   `PagesErreur.tsx` (LOT 3, `T11`), l'error boundary dans `FrontiereErreur.tsx`
 *   (LOT 1), et les messages de champs dans les formulaires d'authentification.
 *   **Les notifications relèvent de `T11`**, qui consolide le design system.
 *
 * LE RÉESSAI EST UN BOUTON QUI RÉESSAIE, PAS UNE PHRASE QUI LE SUGGÈRE
 *
 *   Avant `T10`, le portail écrivait « vérifiez votre connexion, puis réessayez »
 *   **sans rien pour réessayer** : l'utilisateur devait recharger la page, ce qui
 *   lui fait perdre son contexte. Une phrase qui demande une action que l'écran
 *   ne propose pas est de la même famille que l'avertissement faux du §7.21.
 *
 * LA CORRÉLATION N'EST AFFICHÉE QUE SI ELLE EXISTE
 *
 *   Un échec de transport ne porte **aucune** corrélation : la requête n'a pas
 *   atteint l'API. Afficher un champ vide, ou un tiret, apprendrait à
 *   l'utilisateur à citer une valeur qui ne relie à rien.
 */
import type { JSX } from 'react';

import { messageDeCopie, useCorrelationCopiable } from '../reseau';

export interface ProprietesPanneau {
  /** Le message, toujours présent : c'est ce qui interdit l'écran blanc. */
  readonly message: string;
  /** L'identifiant de corrélation, ou `null` si la requête n'a pas abouti. */
  readonly correlation?: string | null;
  /** Ce que fait le bouton de réessai. Absent = aucun bouton, et non un bouton inerte. */
  readonly onReessayer?: (() => void) | undefined;
  /** `alert` pour une erreur, `status` pour un état attendu comme le hors connexion. */
  readonly urgence?: 'alerte' | 'information';
}

export function PanneauDErreur({
  message,
  correlation = null,
  onReessayer,
  urgence = 'alerte',
}: ProprietesPanneau): JSX.Element {
  const { etatCopie, copier } = useCorrelationCopiable();
  const annonce = messageDeCopie(etatCopie);

  return (
    <div className="app-panneau-erreur" data-urgence={urgence}>
      {/*
        `alert` interrompt la lecture, `status` non. Une erreur de chargement le
        merite ; une perte de connexion, que l'utilisateur constate deja par
        ailleurs, non. Le §14.2 veut l'information portee autrement que par la
        seule couleur : le message la porte en entier.
      */}
      <p
        className="app-message"
        data-ton={urgence === 'alerte' ? 'erreur' : 'neutre'}
        role={urgence === 'alerte' ? 'alert' : 'status'}
      >
        {message}
      </p>

      {onReessayer === undefined ? null : (
        <p>
          <button type="button" className="app-action" onClick={onReessayer}>
            Reessayer
          </button>
        </p>
      )}

      {correlation === null || correlation === '' ? null : (
        <div className="app-correlation">
          <p className="app-correlation-explication">
            Identifiant de correlation, a citer dans tout signalement : il relie cette reponse aux
            journaux de l&rsquo;API.
          </p>
          <p>
            {/*
              **SELECTIONNABLE A LA MAIN.** Le presse-papiers peut etre refuse par
              le navigateur ; la copie n'est donc jamais le seul moyen, et c'est
              pourquoi l'identifiant est rendu en clair dans un `<code>`.
            */}
            <code className="app-correlation-valeur">{correlation}</code>{' '}
            <button
              type="button"
              className="app-action app-action-discrete"
              onClick={() => {
                void copier(correlation);
              }}
            >
              Copier
            </button>
          </p>
          {/*
            `aria-live` sur un conteneur TOUJOURS present, et non sur un element
            qui apparait : un `aria-live` ajoute au DOM en meme temps que son
            contenu n'est pas annonce de facon fiable.
          */}
          <p className="app-correlation-annonce" aria-live="polite">
            {annonce}
          </p>
        </div>
      )}
    </div>
  );
}
