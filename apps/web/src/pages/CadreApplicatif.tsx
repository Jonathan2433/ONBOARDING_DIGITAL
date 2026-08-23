/**
 * Le cadre applicatif — LOT 4, sous-etape `T3`, story `MVP-L04-US004`.
 *
 * IL EXISTE POUR QUE « L'ENTITE ACTIVE VISIBLE PARTOUT » SOIT STRUCTUREL
 *
 *   Le cahier §23.3 l'exige : le changement d'entite « **doit etre visible dans
 *   l'en-tete de l'application** ». Et le critere de sortie de la roadmap dit
 *   « l'entite active est visible sur **toutes** les pages internes ».
 *
 *   Deux facons de tenir cela : demander a chaque page d'afficher l'entite, ou la
 *   porter **une fois** dans un cadre que toutes les pages internes traversent. La
 *   premiere se tient par la discipline, la seconde par construction -- et c'est le
 *   §7.2, changer de forme plutot que promettre de l'attention. Le meme motif que
 *   `Cadre` pour les huit ecrans d'authentification en `T11` du LOT 3.
 *
 * IL RESOUT L'ENTITE, ET LES PAGES LA RECOIVENT
 *
 *   `T2` faisait resoudre l'entite par la page. Le cadre la resout desormais et la
 *   passe par `Outlet` : une seule requete pour l'en-tete **et** le contenu, au lieu
 *   de deux qui pourraient afficher deux entites differentes le temps d'un rendu.
 *
 * CE QU'IL NE PORTE PAS, ET CE N'EST PAS UN OUBLI
 *
 *   **Aucun `<nav>`, aucune barre inferieure.** La navigation principale est `T4`,
 *   la barre mobile `T5`. Poser un `<nav>` vide serait un **repere de page sans
 *   contenu** : un lecteur d'ecran l'annoncerait et n'y trouverait rien, ce qui est
 *   pire que son absence. Les emplacements sont documentes, pas prefabriques.
 *
 * LE LIEN D'EVITEMENT EST LA, ET IL SAUTE DEJA QUELQUE CHOSE
 *
 *   §14.2, « navigation integrale au clavier ». Il saute l'en-tete -- marque et
 *   entite -- et il deviendra indispensable quand `T4` y ajoutera six rubriques.
 *   Le poser maintenant evite qu'il soit oublie au moment ou il compte.
 *
 * PAS D'`aria-live` SUR L'ENTITE, ET C'EST UN CHOIX
 *
 *   Le §23.3 demande qu'elle soit **visible**, pas annoncee. Un `aria-live` sur un
 *   repere permanent parlerait aussi au premier chargement, ou l'utilisateur vient
 *   d'agir et sait ou il est. L'annonce d'un changement de route relevera de `T4`,
 *   qui introduit la navigation.
 */
import { type JSX, type ReactNode, useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useOutletContext, useParams } from 'react-router';

import type { EntiteDuPortail } from '@onboarding/contracts';

import { lireLEntite } from '../api/portail';
import { CHEMINS, cheminDeRubrique, RUBRIQUES } from '../routes';
import { BarreMobile } from './BarreMobile';
import { NavigationPrincipale } from './NavigationPrincipale';
import './application.css';

/** Ce que le cadre passe aux pages internes. */
export interface ContexteEntite {
  readonly entite: EntiteDuPortail;
}

/** À employer dans une page interne pour lire l'entité que le cadre a résolue. */
export function useEntiteConsultee(): ContexteEntite {
  return useOutletContext<ContexteEntite>();
}

/**
 * LE TITRE DE LA PAGE, DERIVE DE `RUBRIQUES` — LOT 4, `T3` puis `T4`.
 *
 * `T3` posait une constante, « Accueil de l'entite », faute d'avoir des rubriques
 * a distinguer. `T4` en a six, donc le titre doit varier -- et le mecanisme est
 * choisi avec elles en main, comme `T3` l'annoncait.
 *
 * **DEUX OPTIONS ETAIENT MESUREES, ET C'EST LA SECONDE.** `handle` sur la route,
 * lu par `useMatches`, est la facon idiomatique -- et `useMatches` **exige un data
 * router**, « useMatches must be used within a data router », mesure de `T3`.
 * `App.tsx` emploie le routeur DECLARATIF, choisi en `T11` du LOT 3 pour que les
 * liens de magic link soient de vraies URL.
 *
 * `useLocation` n'a pas cette contrainte, et surtout **il n'ajoute aucune source
 * de verite** : le titre vient de `RUBRIQUES`, d'ou le menu se rend deja. Une
 * migration vers `createBrowserRouter` aurait permis `handle`, au prix de
 * dupliquer le libelle entre la route et le menu -- ce que `DEC-466` refuse.
 *
 * **LE SUFFIXE EST COMPARE, PAS LE CHEMIN ENTIER**, parce que le code de l'entite
 * varie. Et la comparaison porte sur le **dernier segment**, non sur une inclusion
 * de chaine : `/entites/framework-sud` contient « framework » sans etre la
 * rubrique Framework.
 */
function useTitreDeLaPage(defaut: string, code: string): string {
  const { pathname } = useLocation();
  for (const rubrique of RUBRIQUES) {
    if (pathname === cheminDeRubrique(code, rubrique.suffixe)) {
      return rubrique.titre;
    }
  }
  return defaut;
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'trouvee'; readonly entite: EntiteDuPortail }
  | { readonly phase: 'introuvable' }
  | { readonly phase: 'erreur' };

/** Le squelette, partage par les quatre etats — un seul `<main>`, un seul `<h1>`. */
function Squelette({
  titre,
  entite,
  navigation,
  barre,
  children,
}: {
  readonly titre: string;
  readonly entite?: EntiteDuPortail;
  //  **LA NAVIGATION EST FACULTATIVE, ET C'EST VOULU.** Les etats « introuvable »
  //  et « erreur » n'ont pas d'entite, donc aucun code a mettre dans les liens :
  //  un menu vers `/entites/undefined/...` serait pire qu'aucun menu.
  readonly navigation?: ReactNode;
  //  La barre mobile, meme raison : sans entite, ses liens n'auraient pas de code.
  readonly barre?: ReactNode;
  readonly children: ReactNode;
}): JSX.Element {
  return (
    <div className="app-cadre">
      <a className="app-evitement" href="#contenu">
        Aller au contenu
      </a>
      <header className="app-entete">
        <p className="app-marque">eXalt Onboarding</p>
        {entite === undefined ? null : (
          //  **L'ENTITE ACTIVE, VISIBLE PARTOUT** — cahier §23.3. Le nom et la
          //  ville sont deux elements distincts : l'information n'est portee ni
          //  par la seule couleur ni par la seule position (§14.2).
          <p className="app-entite" data-code-entite={entite.code}>
            <span className="app-entite-nom">{entite.nom}</span>
            <span className="app-entite-ville">{entite.ville}</span>
          </p>
        )}
      </header>
      {navigation}
      {/*
        **`tabIndex={-1}` N'EST PAS UN ORNEMENT : SANS LUI LE LIEN D'EVITEMENT NE
        SAUTE RIEN.** Mesure du 23/08/2026 dans un vrai navigateur : en activant
        le lien, le hash devient bien `#contenu` et la page defile -- mais le
        focus part sur `<body>`, parce qu'un `<main>` n'est pas focusable. Le
        Tab suivant repart donc du DEBUT du document, a travers le menu qu'on
        venait de sauter.

        Un lien d'evitement qui ne saute rien est PIRE que pas de lien : il
        consomme un arret de tabulation pour rien, et il apprend a ne pas s'en
        servir -- c'est le §7.21, un avertissement faux, dans un autre costume.

        `-1` et non `0` : la cible doit etre focusable PAR PROGRAMME sans entrer
        dans l'ordre de tabulation. Un `0` ajouterait un arret sur le contenu
        entier, ce que personne ne demande.

        **ET LE DEFAUT DATE DE `T3`, QUI A POSE CE LIEN.** Mon test verifiait que
        le `href` vaut `#contenu` et que le `<main>` porte cet `id`. Les deux
        etaient vrais, et le mecanisme ne fonctionnait pas : le succes du test et
        la justesse du livrable etaient deux grandeurs differentes (§7.0,
        quatrieme proposition).
      */}
      <main className="app-principal" id="contenu" tabIndex={-1}>
        <h1 className="app-titre">{titre}</h1>
        {children}
      </main>
      {/*
        **LA BARRE VIENT EN DERNIER DANS LE DOM, ET C'EST L'ORDRE VISUEL.** Elle
        est ancree en bas de l'ecran ; la mettre avant le contenu ferait diverger
        l'ordre de tabulation de l'ordre visuel, ce que le critere de `T4`
        interdit. Un utilisateur au clavier parcourt donc le contenu, puis la
        barre -- exactement ce que son oeil parcourt.
      */}
      {barre}
    </div>
  );
}

export function CadreApplicatif(): JSX.Element {
  const { code } = useParams<{ code: string }>();
  const codeUtilisable = code !== undefined && code !== '';

  //  **L'ETAT PORTE LE CODE AUQUEL IL APPARTIENT**, et l'affichage en est derive.
  //  Motif etabli en `T2` : un `setState` synchrone dans un effet est refuse par
  //  `react-hooks/set-state-in-effect`, et le couplage etat/code est aussi ce qui
  //  empeche une reponse de l'entite precedente de rester affichee (§23.3).
  //  **APPELE AVANT TOUT RETOUR ANTICIPE.** `react-hooks/rules-of-hooks` refuse un
  //  hook place apres un retour conditionnel, et il a raison : l'ordre des appels
  //  doit etre le meme a chaque rendu. Lecon de `T3`, deja payee deux fois.
  const titreDeLaPage = useTitreDeLaPage("Accueil de l'entite", code ?? '');
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
      <Squelette titre="Ouverture de l&rsquo;entite">
        <p className="app-message" role="status" aria-live="polite">
          Chargement…
        </p>
      </Squelette>
    );
  }

  if (etat.phase === 'introuvable') {
    return (
      <Squelette titre="Entite introuvable">
        <p className="app-message" data-ton="neutre">
          Cette entite n&rsquo;existe pas ou n&rsquo;est pas accessible.
        </p>
        <ul className="app-liens">
          <li>
            <Link className="app-lien" to={CHEMINS.statut}>
              Revenir a la liste des entites
            </Link>
          </li>
        </ul>
      </Squelette>
    );
  }

  if (etat.phase === 'erreur') {
    return (
      <Squelette titre="Chargement impossible">
        <p className="app-message" data-ton="erreur" role="alert">
          L&rsquo;entite n&rsquo;a pas pu etre chargee. Cela ne dit rien de son existence : verifiez
          votre connexion, puis reessayez.
        </p>
      </Squelette>
    );
  }

  //  **LE `<h1>` NE REPETE PAS LE NOM DE L'ENTITE.** Mesure a l'ecran en `T3` :
  //  avec le nom en titre, il apparaissait DEUX fois -- une fois dans l'en-tete,
  //  une fois en `<h1>` -- et un lecteur d'ecran l'entendait deux fois.
  return (
    <Squelette
      titre={titreDeLaPage}
      entite={etat.entite}
      navigation={<NavigationPrincipale code={etat.entite.code} />}
      barre={<BarreMobile code={etat.entite.code} />}
    >
      <Outlet context={{ entite: etat.entite } satisfies ContexteEntite} />
    </Squelette>
  );
}
