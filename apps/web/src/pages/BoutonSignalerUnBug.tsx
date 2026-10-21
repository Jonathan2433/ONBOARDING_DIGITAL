/**
 * Le bouton « Reporter un bug » — LOT 10, `T11`, `MVP-L10-US005`, cahier
 * §9.6/§10.12.
 *
 * TROIS EMPLACEMENTS, UN SEUL COMPOSANT — jamais trois formulaires qui
 * divergeraient au premier changement (§7.27)
 *
 *   Le cahier §10.12 nomme le pied de page, les pages d'erreur et le menu
 *   mobile. Ce composant ne prend AUCUNE propriete liee a l'entite ou au
 *   role : la route qu'il appelle n'en a besoin d'aucune — voir l'en-tete
 *   d'`app/support/routes.py` — donc il se dépose tel quel n'importe où un
 *   utilisateur authentifié peut se trouver.
 *
 * `<details>` PLUTÔT QU'UNE MODALE, MÊME MOTIF QUE `BarreMobile`
 *
 *   Une vraie modale exige de gérer l'ouverture, la fermeture au clavier et
 *   le RETOUR du focus — exactement le terrain où naissent les pièges de
 *   focus que `T4` du LOT 4 a pris soin de rendre impossibles. `<details>`
 *   est nativement focusable, s'ouvre par `Entrée`/`Espace`, et aucun code
 *   ne touche au focus : changer de forme plutôt que promettre de
 *   l'attention (§7.2 de la passation).
 *
 * `chemin_de_page` VIENT DE `window.location.pathname`, JAMAIS DE `useLocation`
 *
 *   Ce composant est rendu aussi bien À L'INTÉRIEUR du routeur (le pied de
 *   page de `CadreApplicatif`, le menu mobile) qu'À L'EXTÉRIEUR d'aucune
 *   contrainte de contexte particulière — mais surtout, c'est la valeur que
 *   l'utilisateur voit RÉELLEMENT dans la barre d'adresse au moment du clic
 *   qui compte pour un signalement, pas une route interne au routeur.
 */
import { type FormEvent, type JSX, useState } from 'react';

import { Alerte, Bouton } from '@onboarding/ui';

import { signalerUnBug } from '../api/signalement';

type Etat = 'repos' | 'envoi' | 'envoye' | 'erreur' | 'session';

export function BoutonSignalerUnBug(): JSX.Element {
  const [etat, setEtat] = useState<Etat>('repos');
  const [description, setDescription] = useState('');
  const [etapes, setEtapes] = useState('');

  const soumettre = (evenement: FormEvent<HTMLFormElement>): void => {
    evenement.preventDefault();
    if (description.trim() === '') {
      return;
    }
    setEtat('envoi');
    void signalerUnBug({
      description,
      ...(etapes.trim() === '' ? {} : { etapes_de_reproduction: etapes }),
      chemin_de_page: window.location.pathname,
    }).then(
      (reponse) => {
        if (reponse.statut === 201) {
          setEtat('envoye');
          setDescription('');
          setEtapes('');
        } else if (reponse.statut === 401) {
          //  **UN MESSAGE DISTINCT, PAS UN ALIAS DE L'ECHEC RESEAU.** Les
          //  pages d'erreur sont atteignables SANS session (un 403/404 brut).
          //  Dire « reessayez » a quelqu'un de deconnecte serait
          //  l'avertissement faux du §7.21 de la passation : reessayer ne
          //  peut pas aboutir sans se reconnecter d'abord.
          setEtat('session');
        } else {
          setEtat('erreur');
        }
      },
      () => {
        setEtat('erreur');
      },
    );
  };

  return (
    <details className="app-signalement">
      <summary className="app-signalement-bouton">Reporter un bug</summary>
      <div className="app-signalement-panneau">
        {etat === 'envoye' ? (
          <Alerte ton="succes" urgence="information">
            Signalement envoyé. Merci de votre aide.
          </Alerte>
        ) : (
          <form
            onSubmit={soumettre}
            //  Reinitialise l'etat « erreur » d'un essai precedent des que
            //  l'utilisateur recommence a saisir — un message d'echec qui
            //  survivrait a une nouvelle tentative en cours serait faux.
            onChange={() => {
              setEtat((precedent) =>
                precedent === 'erreur' || precedent === 'session' ? 'repos' : precedent,
              );
            }}
          >
            <label htmlFor="signalement-description">
              Description du problème et de l&rsquo;action tentée
              <textarea
                id="signalement-description"
                onChange={(e) => {
                  setDescription(e.target.value);
                }}
                required
                value={description}
              />
            </label>
            <label htmlFor="signalement-etapes">
              Étapes de reproduction (facultatif)
              <textarea
                id="signalement-etapes"
                onChange={(e) => {
                  setEtapes(e.target.value);
                }}
                value={etapes}
              />
            </label>
            {etat === 'erreur' ? (
              <Alerte ton="erreur" urgence="alerte">
                L&rsquo;envoi a échoué. Vérifiez votre connexion et réessayez.
              </Alerte>
            ) : null}
            {etat === 'session' ? (
              <Alerte ton="avertissement" urgence="alerte">
                Vous devez être connecté pour signaler un bug.
              </Alerte>
            ) : null}
            <Bouton disabled={etat === 'envoi'} type="submit">
              {etat === 'envoi' ? 'Envoi…' : 'Envoyer'}
            </Bouton>
          </form>
        )}
      </div>
    </details>
  );
}
