/**
 * La page nationale — LOT 4, `T6`, story `MVP-L04-US001`, cahier §8.3.
 *
 * CE QUE LE §8.3 EXIGE, DANS SON ORDRE
 *
 *   « La page nationale presente : une **liste accessible** des entites ; une
 *   carte de France ; un acces a chaque entite **active**. Sur mobile, **la liste
 *   precede la carte**. »
 *
 *   **LA LISTE PRECEDE LA CARTE DANS LE DOM, PAS SEULEMENT A L'OEIL.** C'est le
 *   critere de sortie de `T6`, et la distinction est tout : un ordre obtenu par
 *   `order` en CSS satisferait l'oeil sur mobile et laisserait la carte AVANT la
 *   liste pour un lecteur d'ecran et pour la tabulation. L'ordre est donc celui du
 *   document, et un test l'exige.
 *
 *   `T7` posera la carte **apres** cette liste. L'emplacement est documente, pas
 *   prefabrique : une `<section>` vide serait un repere sans contenu.
 *
 * ELLE N'EMPLOIE PAS `CadreApplicatif`, ET C'EST STRUCTUREL
 *
 *   Le cadre resout une entite consultee et la porte dans son en-tete. Ici il n'y
 *   en a pas : on est AU-DESSUS de l'entite, on la choisit. Employer le cadre
 *   exigerait une entite pour afficher une page dont l'objet est de la choisir.
 *
 * SEULES LES ENTITES ACTIVES, ET C'EST L'API QUI LE TIENT
 *
 *   `GET /api/v1/entities` filtre sur `status = active` -- cahier §8.3, « un acces
 *   a chaque entite ACTIVE » -- et c'est la que le controle vit, prouve par
 *   `make entites-check`. Le frontend n'a rien a refiltrer : le refaire ici
 *   donnerait DEUX regles, et le jour ou l'une change l'autre mentirait.
 *
 * QUATRE ETATS, DONT DEUX QU'ON CONFOND FACILEMENT
 *
 *   chargement · liste · **aucune entite active** · erreur. « Aucune entite » est
 *   un etat LEGITIME -- une plateforme neuve -- et le confondre avec une panne
 *   dirait a l'utilisateur une chose fausse. C'est le meme parti qu'en `T2` pour
 *   « introuvable » contre « erreur ».
 */
import { type JSX, useEffect, useState } from 'react';
import { Link } from 'react-router';

import type { EntiteDuPortail } from '@onboarding/contracts';

import { listerLesEntites } from '../api/portail';
import { CarteDeFrance } from './CarteDeFrance';
import { cheminDeLEntite, CHEMINS } from '../routes';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'liste'; readonly entites: readonly EntiteDuPortail[] }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageNationale(): JSX.Element {
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    const abandon = new AbortController();
    void listerLesEntites(abandon.signal).then(
      (reponse) => {
        if (reponse.statut === 200 && reponse.corps !== null) {
          setEtat({ phase: 'liste', entites: reponse.corps.entites });
        } else {
          setEtat({ phase: 'erreur', statut: reponse.statut });
        }
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setEtat({ phase: 'erreur', statut: 0 });
        }
        return cause;
      },
    );
    return () => abandon.abort();
  }, []);

  return (
    <div className="app-cadre">
      <a className="app-evitement" href="#contenu">
        Aller au contenu
      </a>
      <header className="app-entete">
        <p className="app-marque">eXalt Onboarding</p>
      </header>
      {/*
        `tabIndex={-1}` : sans lui le lien d'evitement ferait defiler sans deplacer
        le focus, et le Tab suivant repartirait du debut. Mesure de `T4`,
        `ECART-043`.
      */}
      <main className="app-principal" id="contenu" tabIndex={-1}>
        <h1 className="app-titre">Choisir une entite</h1>

        {etat.phase === 'chargement' ? (
          <p className="app-message" role="status" aria-live="polite">
            Chargement des entites…
          </p>
        ) : null}

        {etat.phase === 'erreur' ? (
          <p className="app-message" data-ton="erreur" role="alert">
            {etat.statut === 401
              ? 'Votre session a expire. Reconnectez-vous pour choisir une entite.'
              : "La liste des entites n'a pas pu etre chargee. Cela ne dit rien de leur existence : verifiez votre connexion, puis reessayez."}
          </p>
        ) : null}

        {etat.phase === 'erreur' && etat.statut === 401 ? (
          <ul className="app-liens">
            <li>
              <Link className="app-lien" to={CHEMINS.connexion}>
                Se reconnecter
              </Link>
            </li>
          </ul>
        ) : null}

        {etat.phase === 'liste' && etat.entites.length === 0 ? (
          //  **UN ETAT LEGITIME, PAS UNE PANNE.** Le dire autrement apprendrait a
          //  l'utilisateur une chose fausse.
          <p className="app-message" data-ton="neutre">
            Aucune entite active pour le moment. Il n&rsquo;y a rien a choisir, et ce n&rsquo;est
            pas une erreur.
          </p>
        ) : null}

        {etat.phase === 'liste' && etat.entites.length > 0 ? (
          //  **LA LISTE, AVANT LA CARTE, DANS LE DOM.** `T7` posera la carte
          //  apres ce bloc. Une `<nav>` nommee : c'est un ensemble de liens de
          //  navigation, et le nommer permet de le distinguer des deux autres
          //  reperes que le cadre porte une fois l'entite choisie.
          <nav className="nat-liste" aria-label="Liste des entites">
            <ul className="nat-liste-items">
              {etat.entites.map((entite) => (
                <li key={entite.id}>
                  <Link className="nat-entite" to={cheminDeLEntite(entite.code)}>
                    <span className="nat-entite-nom">{entite.nom}</span>
                    <span className="nat-entite-ville">{entite.ville}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}

        {/*
          **LA CARTE VIENT APRES LA LISTE, DANS LE DOM.** §8.3, « sur mobile, la
          liste precede la carte ». `make cadre-check` l'exige et il exige aussi
          qu'aucune regle CSS ne les reordonne : un `order` satisferait l'oeil et
          laisserait la carte avant la liste pour un lecteur d'ecran.

          Elle n'est rendue que quand la liste existe : une carte decorative seule,
          sur un ecran d'erreur ou de chargement, n'apporterait rien et occuperait
          la place du message.
        */}
        {etat.phase === 'liste' && etat.entites.length > 0 ? <CarteDeFrance /> : null}
      </main>
    </div>
  );
}
