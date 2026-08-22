/**
 * Ecran 3 sur 8 — lien expire ou deja consomme. LOT 3, `T11`, story `US002`.
 *
 * CET ECRAN EST UN ETAT, PAS UNE ADRESSE — ET C'EST LE CORPUS QUI LE VEUT
 *
 *   Le lien de l'e-mail ouvre CETTE page avec le jeton en chaine de requete ;
 *   elle appelle l'API avec le jeton **en corps**, et **c'est son echec qui est
 *   l'ecran** que le corpus enumere. Compter les ecrans en routes en donnerait
 *   sept ou neuf.
 *
 * LE JETON EST RETIRE DE LA BARRE D'ADRESSE, ET CE N'EST PAS COSMETIQUE
 *
 *   `history.replaceState` efface la chaine de requete des l'extraction. Sans
 *   cela, le jeton reste dans l'historique du navigateur, dans le titre de
 *   l'onglet partage, et part dans l'en-tete `Referer` de toute ressource
 *   chargee ensuite. Le §7.2 du cahier interdit le jeton en clair « dans le
 *   frontend » ; le laisser dans l'URL le mettrait dans dix endroits.
 *
 *   **`replaceState` et non `pushState`** : `pushState` laisserait l'URL avec le
 *   jeton dans l'historique, ce qui est exactement ce qu'on retire.
 *
 * UN SEUL GABARIT DE REFUS POUR QUATRE CAUSES
 *
 *   L'API rend `400` pour un jeton inconnu, expire, deja consomme, ou invalide
 *   par une demande plus recente -- `T4`, et c'est ce qui a **dicte** l'existence
 *   d'un seul ecran ici. Cette page ne les distingue donc pas : elle n'en a pas
 *   le moyen, et c'est voulu.
 *
 * LE SUCCES N'ACCORDE AUCUN ACCES VISIBLE, ET C'EST NORMAL
 *
 *   `200` pose le cookie de session. Le portail est le **LOT 4** : il n'existe
 *   aucune page vers laquelle rediriger. L'ecran dit donc que la connexion est
 *   etablie, sans promettre une destination qui n'existe pas.
 */
import { useEffect, useRef, useState, type JSX } from 'react';
import { Link } from 'react-router';

import { consommerUnLien } from '../api/auth';
import { CHEMINS } from '../routes';
import { Cadre } from './Cadre';

type Etat = 'consommation' | 'connecte' | 'refuse';

const MESSAGE_REFUS =
  'Ce lien ne fonctionne pas. Il est peut-etre expire, deja utilise, ou remplace ' +
  "par une demande plus recente. Demandez-en un nouveau, c'est immediat.";

/**
 * Lire le jeton de la chaine de requete. **LECTURE PURE, aucun effet.**
 *
 * Separee de l'effacement, et **c'est le linter qui l'a imposee** :
 * `react-hooks/set-state-in-effect` refusait un `setState` synchrone dans un
 * effet, ce qui a oblige a deriver l'etat initial pendant le rendu. Or on ne peut
 * deriver pendant le rendu qu'a partir d'une lecture **pure** -- un
 * `replaceState` la-dedans serait un effet de bord au rendu.
 *
 * **La regle avait raison**, et le decoupage qu'elle impose est meilleur : une
 * lecture pure et un effet de bord ne devaient pas etre la meme fonction.
 */
export function lireLeJeton(fenetre: Window): string {
  return new URLSearchParams(fenetre.location.search).get('token') ?? '';
}

/**
 * Effacer le jeton de la barre d'adresse. **EFFET DE BORD, dans un effet.**
 *
 * Exportee pour etre eprouvee seule : la manipulation d'historique est difficile a
 * observer depuis un rendu, et un comportement de securite qu'on ne peut pas
 * tester n'est pas un comportement de securite.
 */
export function effacerLeJetonDeLUrl(fenetre: Window): void {
  fenetre.history.replaceState(null, '', fenetre.location.pathname);
}

export function PageLien(): JSX.Element {
  //  **LE JETON EST LU PENDANT LE RENDU, ET L'ETAT INITIAL EN DERIVE.** Un lien
  //  sans jeton est refuse d'emblee, sans passer par un etat « consommation » qui
  //  ne consomme rien -- et sans `setState` synchrone dans un effet.
  const [jeton] = useState(() => lireLeJeton(window));
  const [etat, setEtat] = useState<Etat>(jeton === '' ? 'refuse' : 'consommation');
  //  **UNE SEULE CONSOMMATION, MEME SOUS `StrictMode`.** React monte deux fois en
  //  developpement : sans ce garde, le second appel consommerait un jeton deja
  //  utilise et l'ecran de refus s'afficherait sur un lien parfaitement valide.
  const dejaTente = useRef(false);

  useEffect(() => {
    if (jeton === '' || dejaTente.current) {
      return;
    }
    dejaTente.current = true;
    effacerLeJetonDeLUrl(window);
    void consommerUnLien(jeton).then(
      (reponse) => setEtat(reponse.statut === 200 ? 'connecte' : 'refuse'),
      () => setEtat('refuse'),
    );
  }, [jeton]);

  if (etat === 'consommation') {
    return (
      <Cadre titre="Connexion en cours">
        <p className="auth-message" role="status" aria-live="polite">
          Verification du lien…
        </p>
      </Cadre>
    );
  }

  if (etat === 'connecte') {
    return (
      <Cadre titre="Vous etes connecte">
        <p className="auth-message" data-ton="succes" role="status" aria-live="polite">
          Votre session est ouverte. Le portail arrive dans une prochaine version ; en attendant,
          aucune page ne vous attend ici.
        </p>
        <ul className="auth-liens">
          <li>
            <Link className="auth-lien" to={CHEMINS.deconnexion}>
              Se deconnecter
            </Link>
          </li>
        </ul>
      </Cadre>
    );
  }

  return (
    <Cadre titre="Ce lien n'est plus valable">
      <p className="auth-message" data-ton="refus" role="status" aria-live="polite">
        {MESSAGE_REFUS}
      </p>
      <ul className="auth-liens">
        <li>
          <Link className="auth-lien" to={CHEMINS.connexion}>
            Demander un nouveau lien
          </Link>
        </li>
      </ul>
    </Cadre>
  );
}
