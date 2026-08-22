/**
 * Ecran 5 sur 8 — deconnexion. LOT 3, `T11`, story `US004`.
 *
 * ELLE EXIGE LE JETON ANTI-CSRF, ET IL FAUT DONC LE LIRE D'ABORD
 *
 *   `DEC-531` : la deconnexion est la **seule** ecriture du lot qui dispose d'une
 *   session, donc la seule qui exige un jeton. Ce jeton est delivre par
 *   `GET /auth/session`, et c'est pourquoi cette route ne l'exige pas elle-meme --
 *   l'exiger serait circulaire.
 *
 *   Cet ecran fait donc **deux appels** : lire la session pour obtenir le jeton,
 *   puis se deconnecter avec lui. Le jeton vit en memoire le temps du composant et
 *   n'est jamais stocke : interdit absolu du §9.5.
 *
 * LA DECONNEXION EST UN BOUTON, PAS UN EFFET DE MONTAGE
 *
 *   Une page qui deconnecterait a son affichage se declencherait sur un
 *   pre-chargement de lien, sur un rafraichissement, ou sur une visite
 *   accidentelle. Le §7.4 du cahier veut une deconnexion « effective », pas
 *   involontaire -- et c'est une ecriture, donc elle demande un geste.
 *
 * SANS SESSION, L'ECRAN NE DIT PAS « ERREUR »
 *
 *   `GET /auth/session` rend `401` quand aucune session n'existe. Ce n'est pas une
 *   panne : l'utilisateur est deja deconnecte, et le lui dire est la bonne
 *   reponse.
 */
import { useEffect, useState, type JSX } from 'react';
import { Link } from 'react-router';
import { Bouton } from '@onboarding/ui';

import { lireLaSession, seDeconnecter } from '../api/auth';
import { CHEMINS } from '../routes';
import { Cadre } from './Cadre';

type Etat = 'lecture' | 'ouverte' | 'aucune' | 'envoi' | 'terminee' | 'echec';

export function PageDeconnexion(): JSX.Element {
  const [etat, setEtat] = useState<Etat>('lecture');
  //  Le jeton anti-CSRF, en memoire seulement. Jamais dans `localStorage`.
  const [jetonCsrf, setJetonCsrf] = useState('');

  useEffect(() => {
    void lireLaSession().then(
      (reponse) => {
        if (reponse.statut === 200 && reponse.corps !== null) {
          setJetonCsrf(reponse.corps.jeton_csrf);
          setEtat('ouverte');
        } else {
          setEtat('aucune');
        }
      },
      () => setEtat('echec'),
    );
  }, []);

  async function partir(): Promise<void> {
    setEtat('envoi');
    try {
      const reponse = await seDeconnecter(jetonCsrf);
      setEtat(reponse.statut === 200 ? 'terminee' : 'echec');
    } catch {
      setEtat('echec');
    }
    //  Le jeton est efface des qu'il a servi : il est lie a une session qui
    //  n'existe plus.
    setJetonCsrf('');
  }

  const MESSAGES: Partial<Record<Etat, string>> = {
    lecture: 'Verification de votre session…',
    aucune: 'Aucune session ouverte : vous etes deja deconnecte.',
    terminee: 'Votre session est fermee. Elle ne repond plus, meme avec son ancien cookie.',
    echec: "La deconnexion n'a pas abouti. Reessayez dans un instant.",
  };

  return (
    <Cadre titre="Se deconnecter">
      {etat === 'ouverte' || etat === 'envoi' ? (
        <>
          <p className="auth-introduction">
            Fermer votre session la revoque cote serveur : le cookie ne sera plus accepte, meme
            conserve.
          </p>
          <Bouton
            type="button"
            variante="primaire"
            disabled={etat === 'envoi'}
            onClick={() => {
              void partir();
            }}
          >
            {etat === 'envoi' ? 'Deconnexion…' : 'Fermer ma session'}
          </Bouton>
        </>
      ) : null}

      <p
        className="auth-message"
        data-ton={etat === 'terminee' ? 'succes' : etat === 'echec' ? 'refus' : undefined}
        role="status"
        aria-live="polite"
      >
        {MESSAGES[etat] ?? ''}
      </p>

      <ul className="auth-liens">
        <li>
          <Link className="auth-lien" to={CHEMINS.connexion}>
            Se reconnecter
          </Link>
        </li>
      </ul>
    </Cadre>
  );
}
