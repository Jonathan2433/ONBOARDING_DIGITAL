/**
 * L'entite consultee — LOT 4, `T2`, story `MVP-L04-US001`.
 *
 * ELLE RESOUT L'ENTITE DEPUIS L'ADRESSE, ET C'EST TOUT CE QUE `T2` LIVRE
 *
 *   Le cadre applicatif, les cinq largeurs et l'entite « visible partout »
 *   appartiennent a `T3` ; la navigation a `T4` ; la liste nationale a `T6`. Cette
 *   page existe pour que le choix d'entite ait une adresse ou vivre, et pour
 *   prouver qu'il **survit a un rechargement**.
 *
 * QUATRE ETATS, ET LE QUATRIEME N'EST PAS UN LUXE
 *
 *   chargement · trouvee · introuvable · erreur reseau. Confondre le dernier avec
 *   « introuvable » dirait a l'utilisateur que l'entite n'existe pas alors que
 *   c'est sa connexion qui a lache -- c'est le critere de `T10`, « les erreurs
 *   reseau n'indiquent jamais a tort qu'une action est sauvegardee », applique a
 *   une lecture. `T10` reprendra ces etats dans une forme partagee.
 *
 * L'ABANDON EST EXIGE PAR LE §23.3
 *
 *   « Le changement d'entite selectionnee ... annule les requetes et caches
 *   associes a l'entite precedente. » Sans `AbortController`, une reponse lente
 *   pour l'entite quittee arriverait APRES celle de la nouvelle et l'ecraserait :
 *   l'ecran afficherait Bordeaux alors que l'adresse dit Paris. Le defaut
 *   n'apparait que sous latence, donc jamais en developpement local.
 *
 * UN 401 N'EST PAS TRAITE ICI, ET C'EST DELIBERE
 *
 *   Le cahier veut des « route guards **uniquement ergonomiques** » et des
 *   « controles d'autorisation **systematiques dans l'API** ». Traiter le 401 par
 *   une redirection depuis chaque page disperserait la regle ; `T9` la posera en un
 *   seul endroit. Ici un 401 tombe dans l'etat « erreur », qui ne pretend rien sur
 *   l'existence de l'entite.
 */
import { type JSX, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import type { EntiteDuPortail } from '@onboarding/contracts';

import { lireLEntite } from '../api/portail';
import { CHEMINS } from '../routes';
import { Cadre } from './Cadre';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'trouvee'; readonly entite: EntiteDuPortail }
  | { readonly phase: 'introuvable' }
  | { readonly phase: 'erreur' };

export function PageEntite(): JSX.Element {
  const { code } = useParams<{ code: string }>();
  const codeUtilisable = code !== undefined && code !== '';

  //  **L'ETAT PORTE LE CODE AUQUEL IL APPARTIENT, ET L'AFFICHAGE EN EST DERIVE.**
  //
  //  La forme naive -- un `setEtat({ phase: 'chargement' })` en tete d'effet a
  //  chaque changement de code -- est refusee par `react-hooks/set-state-in-effect`,
  //  et la regle a raison : un `setState` synchrone dans un effet declenche un
  //  second rendu en cascade. C'est le meme verrou qu'en `T11` du LOT 3, sur
  //  `PageLien`, et la parade est la meme : **deriver pendant le rendu** plutot que
  //  desactiver la regle.
  //
  //  Ici la derivation est aussi ce qui rend l'affichage JUSTE : tant que la
  //  donnee chargee n'appartient pas au code courant, on est en chargement. Sans
  //  ce couplage, une reponse de l'entite precedente resterait affichee sous la
  //  nouvelle adresse -- exactement ce que le §23.3 interdit.
  const [charge, setCharge] = useState<{ readonly code: string; readonly etat: Etat } | null>(null);
  const etat: Etat = !codeUtilisable
    ? { phase: 'introuvable' }
    : charge !== null && charge.code === code
      ? charge.etat
      : { phase: 'chargement' };

  useEffect(() => {
    if (!codeUtilisable) {
      return undefined;
    }
    //  **UN ABANDON PAR CODE, ET IL EST NETTOYE.** React remonte deux fois sous
    //  `StrictMode` : sans le retour de nettoyage, la premiere requete resterait
    //  en vol et pourrait ecraser la seconde.
    const abandon = new AbortController();
    const poser = (phase: Etat): void => setCharge({ code, etat: phase });
    void lireLEntite(code, abandon.signal).then(
      (reponse) => {
        if (reponse.statut === 200 && reponse.corps !== null) {
          poser({ phase: 'trouvee', entite: reponse.corps });
        } else if (reponse.statut === 404) {
          poser({ phase: 'introuvable' });
        } else {
          poser({ phase: 'erreur' });
        }
      },
      //  Un abandon leve, et ce n'est PAS une erreur a afficher : la page est en
      //  train d'etre remplacee. Confondre les deux ferait clignoter un message
      //  d'erreur a chaque changement d'entite.
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          poser({ phase: 'erreur' });
        }
        return cause;
      },
    );
    return () => abandon.abort();
  }, [code, codeUtilisable]);

  if (etat.phase === 'chargement') {
    return (
      <Cadre titre="Ouverture de l&rsquo;entite">
        <p className="auth-message" role="status" aria-live="polite">
          Chargement…
        </p>
      </Cadre>
    );
  }

  if (etat.phase === 'introuvable') {
    return (
      <Cadre
        titre="Entite introuvable"
        introduction="Cette entite n'existe pas ou n'est pas accessible."
      >
        <ul className="auth-liens">
          <li>
            <Link className="auth-lien" to={CHEMINS.statut}>
              Revenir a la liste des entites
            </Link>
          </li>
        </ul>
      </Cadre>
    );
  }

  if (etat.phase === 'erreur') {
    return (
      <Cadre titre="Chargement impossible">
        <p className="auth-message" data-ton="erreur" role="alert">
          L&rsquo;entite n&rsquo;a pas pu etre chargee. Cela ne dit rien de son existence : verifiez
          votre connexion, puis reessayez.
        </p>
      </Cadre>
    );
  }

  return (
    <Cadre titre={etat.entite.nom} introduction={etat.entite.ville}>
      {/*
        **L'ENTITE CONSULTEE EST AFFICHEE CLAIREMENT** — cahier §9.2, etape 4.
        `T3` la portera dans l'en-tete de toutes les pages internes, ce que le
        §23.3 exige ; ici elle est le titre de la seule page qui existe.
      */}
      <p className="auth-message" data-ton="succes" data-code-entite={etat.entite.code}>
        Vous consultez {etat.entite.nom}. Le choix vit dans l&rsquo;adresse : il survit a un
        rechargement et un lien partage ouvre la meme entite.
      </p>
      <ul className="auth-liens">
        <li>
          <Link className="auth-lien" to={CHEMINS.statut}>
            Revenir a la liste des entites
          </Link>
        </li>
      </ul>
    </Cadre>
  );
}
