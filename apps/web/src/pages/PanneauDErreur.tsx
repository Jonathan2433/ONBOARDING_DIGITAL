/**
 * Ce que le §17.4 exige de tout écran d'erreur du portail — LOT 4, `T10`, puis `T11`.
 *
 * SEPT EXIGENCES, ET CE PANNEAU EN PORTE QUATRE
 *
 *   Le §17.4 liste : « pages 403, 404 et erreur générale ; error boundary React ;
 *   messages de champs ; notifications ; **possibilité de réessayer** ;
 *   **identifiant de corrélation copiable** ; **aucun écran blanc silencieux** ».
 *
 *   Ce panneau porte le **réessai**, la **corrélation copiable**, un **message
 *   toujours présent** — donc aucun écran blanc — et l'**annonce** du résultat de
 *   la copie. Les trois autres sont ailleurs : les pages 403/404/erreur dans
 *   `PagesErreur.tsx` (LOT 3, `T11`), l'error boundary dans `FrontiereErreur.tsx`
 *   (LOT 1), les messages de champs dans les formulaires d'authentification.
 *
 * `T11` L'A RÉÉCRIT SUR LE DESIGN SYSTEM, ET C'ÉTAIT UNE DUPLICATION QUE J'AVAIS FAITE
 *
 *   `T10` écrivait ici son propre `<button className="app-action">` alors que
 *   `packages/ui` porte un `Bouton` depuis `T10` du LOT 1 — mesuré : trois écrans
 *   d'authentification l'importaient, et le portail non. C'est exactement la
 *   classe du §7.27, et je l'avais commise une sous-étape avant de la corriger.
 *
 *   Les quatre composants employés ici le sont parce que **ce panneau en avait
 *   besoin**, non pour cocher une liste : `Bouton` pour les deux actions,
 *   `Alerte` pour le message, `Carte` pour le bloc de corrélation — que
 *   `PageStatut` rendait déjà en section titrée — et `Notification` pour le
 *   résultat de la copie, qui est un **résultat d'action** et non un état.
 */
import type { JSX } from 'react';

import { Alerte, Bouton, Carte, Notification } from '@onboarding/ui';

import { messageDeCopie, useCorrelationCopiable } from '../reseau';

export interface ProprietesPanneau {
  /** Le message, toujours présent : c'est ce qui interdit l'écran blanc. */
  readonly message: string;
  /** L'identifiant de corrélation, ou `null` si la requête n'a pas abouti. */
  readonly correlation?: string | null;
  /** Ce que fait le bouton de réessai. Absent = aucun bouton, et non un bouton inerte. */
  readonly onReessayer?: (() => void) | undefined;
  /** `alerte` pour une erreur, `information` pour un état attendu comme le hors connexion. */
  readonly urgence?: 'alerte' | 'information';
}

export function PanneauDErreur({
  message,
  correlation = null,
  onReessayer,
  urgence = 'alerte',
}: ProprietesPanneau): JSX.Element {
  const { etatCopie, copier } = useCorrelationCopiable();

  return (
    <div className="app-panneau-erreur" data-urgence={urgence}>
      {/*
        `alerte` interrompt la lecture, `information` non. Une erreur de
        chargement le merite ; une perte de connexion, que l'utilisateur constate
        deja par ailleurs, non. Le §14.2 veut l'information portee autrement que
        par la seule couleur : le message la porte en entier, et `Alerte` EXIGE
        son texte dans son type.
      */}
      <Alerte ton={urgence === 'alerte' ? 'erreur' : 'neutre'} urgence={urgence}>
        {message}
      </Alerte>

      {onReessayer === undefined ? null : (
        <p className="app-panneau-action">
          <Bouton onClick={onReessayer}>Reessayer</Bouton>
        </p>
      )}

      {correlation === null || correlation === '' ? null : (
        //  **`Carte` PARCE QUE C'EST UNE SECTION TITREE**, exactement ce que
        //  `PageStatut` rendait a la main depuis `T5` du LOT 1. Le titre est en
        //  `h2` : le cadre porte l'unique `<h1>` du document.
        <Carte titre="Identifiant de correlation" niveauTitre="h2">
          <p className="app-correlation-explication">
            A citer dans tout signalement : il relie cette reponse aux journaux de l&rsquo;API.
          </p>
          <p>
            {/*
              **SELECTIONNABLE A LA MAIN.** Le presse-papiers peut etre refuse par
              le navigateur ; la copie n'est donc jamais le seul moyen, et c'est
              pourquoi l'identifiant est rendu en clair dans un `<code>`.
            */}
            <code className="app-correlation-valeur">{correlation}</code>{' '}
            <Bouton
              variante="secondaire"
              onClick={() => {
                void copier(correlation);
              }}
            >
              Copier
            </Bouton>
          </p>
          {/*
            **`Notification` ET NON `Alerte`, ET LA DIFFERENCE EST STRUCTURELLE.**
            C'est le RESULTAT d'une action, pas l'etat de l'ecran : son conteneur
            doit donc etre present AVANT que son texte arrive, sans quoi
            l'annonce n'est pas fiable. `Notification` rend toujours le sien,
            meme vide -- ce qui est exactement le cas au premier rendu.
          */}
          <Notification
            message={messageDeCopie(etatCopie)}
            ton={etatCopie === 'impossible' ? 'echec' : 'succes'}
          />
        </Carte>
      )}
    </div>
  );
}
