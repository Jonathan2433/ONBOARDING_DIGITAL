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
import { type JSX, type ReactNode, useCallback, useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useOutletContext, useParams } from 'react-router';

import type { EntiteDuPortail, PermissionsDeLEntite } from '@onboarding/contracts';

import { lireLEntite, lireLesPermissions, listerLesEntites } from '../api/portail';
import { useEtatDeConnexion } from '../reseau';
import { CHEMINS, cheminDeRubrique, droitsDeNavigation, RUBRIQUES } from '../routes';
import { BarreMobile } from './BarreMobile';
import { NavigationPrincipale } from './NavigationPrincipale';
import { PanneauDErreur } from './PanneauDErreur';
import { SelecteurDEntite } from './SelecteurDEntite';
import './application.css';

/**
 * Ce que le cadre passe aux pages internes.
 *
 * **`permissions` PEUT ETRE `null`, ET C'EST UNE INFORMATION.** L'entite est
 * resolue avant l'affichage -- sans elle, il n'y a pas de page. Les permissions,
 * elles, peuvent manquer alors que la page est utilisable : l'appel a echoue, ou
 * il n'est pas encore revenu. Rendre un objet vide a la place ferait passer
 * « je ne sais pas » pour « aucun droit », et `T9` masquerait des rubriques sur
 * une ignorance. Le `null` oblige l'appelant a traiter le cas.
 */
export interface ContexteEntite {
  readonly entite: EntiteDuPortail;
  readonly permissions: PermissionsDeLEntite | null;
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
  //  **401 EST UN ETAT DISTINCT, ET CE N'EST PAS UN RAFFINEMENT.** Defaut vu au
  //  navigateur le 24/08/2026 : ma session avait expire, l'API rendait 401, et le
  //  cadre affichait « L'entite n'a pas pu etre chargee. Cela ne dit rien de son
  //  existence » -- une phrase FAUSSE. L'utilisateur n'a pas un probleme de
  //  chargement, il est deconnecte, et le remede n'est pas « reessayer » mais
  //  « se reconnecter ».
  //
  //  C'est la meme classe que `T8-4` : le message etait plausible, et seul
  //  l'ecran l'a montre faux.
  | { readonly phase: 'session' }
  | { readonly phase: 'erreur' };

/**
 * L'etat du cadre pour UN code d'entite.
 *
 * **LES DEUX ENRICHISSEMENTS VIVENT A COTE DE LA PHASE, PAS DEDANS, ET C'EST UN
 * DEFAUT MESURE QUI L'A IMPOSE.** La premiere version de `T8` les portait dans
 * la variante `trouvee`, si bien qu'une reponse de permissions arrivee AVANT
 * celle de l'entite ne trouvait pas d'etat `trouvee` ou se poser : elle etait
 * perdue definitivement.
 *
 * **Ce n'est pas un cas theorique, il a ete VU dans un navigateur** le
 * 24/08/2026 : l'API rendait bien `est_entite_principale: false`, et la mention
 * du §5.1 n'apparaissait pas. Le journal reseau montrait deux appels de
 * permissions -- un abandonne, un a 200 -- et le second revenait avant l'entite.
 *
 * **Et mes tests ne l'attrapaient pas**, parce qu'un `fetch` bouchonne resout
 * dans l'ordre de creation des promesses : l'entite gagnait toujours. C'est le
 * §7.16 -- ce qui n'a jamais tourne ailleurs n'est pas eprouve -- et le §7.24,
 * le succes d'un test et la justesse du livrable sont deux grandeurs
 * differentes. Un test qui fixe l'ordre INVERSE a ete ajoute.
 */
interface Charge {
  readonly code: string;
  readonly etat: Etat;
  readonly autres: readonly EntiteDuPortail[];
  readonly permissions: PermissionsDeLEntite | null;
  /**
   * L'identifiant de corrélation de la réponse d'entité — §17.4, `T10`.
   *
   * **CELLE DE L'ENTITE, ET NON LA DERNIERE VUE.** Les trois appels en portent
   * chacun une ; montrer la plus récente donnerait à l'utilisateur un identifiant
   * qui ne relie pas à l'échec qu'il constate. C'est l'appel dont l'échec ferme
   * l'écran qui compte.
   */
  readonly correlation: string | null;
}

/** Le squelette, partage par les quatre etats — un seul `<main>`, un seul `<h1>`. */
function Squelette({
  titre,
  entite,
  selecteur,
  consultationSeule,
  navigation,
  barre,
  children,
}: {
  readonly titre: string;
  readonly entite?: EntiteDuPortail;
  //  Le selecteur d'entite. Facultatif comme la navigation, et pour la meme
  //  raison : sans entite resolue, il n'a pas d'entite courante a marquer.
  readonly selecteur?: ReactNode;
  //  **`undefined` N'EST PAS `false`.** `undefined` veut dire « les droits ne sont
  //  pas connus », `false` veut dire « vous etes dans votre entite principale ».
  //  Les confondre afficherait la mention du §5.1 sur une ignorance, ou la
  //  masquerait alors qu'elle s'applique.
  //  `| undefined` EXPLICITE : `exactOptionalPropertyTypes` est actif, et il
  //  distingue « propriete absente » de « propriete a `undefined` ». Ici les
  //  trois etats sont voulus, donc le type doit les porter tous les trois.
  readonly consultationSeule?: boolean | undefined;
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
        {selecteur}
        {consultationSeule === true ? (
          //  **LA FORMULATION VIENT DU §4 DE LA MATRICE, PAS DE MOI.** Sa legende
          //  definit `Lecture` : « Consultation uniquement, sans modification ».
          //  Et ce qu'elle dit est la consequence du §5.1 -- « aucune action de
          //  creation, modification, publication, archivage, restauration ou
          //  export n'est proposee » -- donc l'utilisateur doit savoir POURQUOI
          //  les actions manqueront, sans quoi il les croira cassees.
          //
          //  `role="status"` et non `alert` : ce n'est pas une erreur, c'est un
          //  contexte. Un `alert` interromprait la lecture a chaque changement.
          <p className="app-consultation" role="status" data-consultation="seule">
            Consultation uniquement, sans modification&nbsp;: cette entite n&rsquo;est pas votre
            entite principale.
          </p>
        ) : null}
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
  const [charge, setCharge] = useState<Charge | null>(null);
  //  **LE COMPTEUR DE TENTATIVES EST DANS LES DEPENDANCES DE L'EFFET**, et c'est
  //  ce qui fait qu'un bouton peut vraiment reessayer : incrementer relance
  //  l'effet, donc les trois appels, avec un signal neuf. Meme mecanisme que
  //  `PageStatut` depuis `T5` du LOT 1.
  const [tentative, setTentative] = useState(0);
  //  **UN SEUL TEST DE CODE, ET TOUT EN DERIVE.** Une charge qui n'appartient
  //  plus au code demande n'est pas seulement obsolete pour la phase : elle l'est
  //  aussi pour la liste et les droits. Les lire separement laisserait passer les
  //  droits de l'entite quittee -- ce que le §23.3 interdit.
  const courante: Charge | null = charge !== null && charge.code === code ? charge : null;

  //  **LE RETOUR DE CONNEXION RELANCE, ET C'EST LE §17.2.** « Apres perte de
  //  connexion sur une page deja chargee, l'utilisateur voit un etat explicite » --
  //  et ce que l'ecran affichait est devenu obsolete a la coupure.
  const reessayer = useCallback((): void => {
    setCharge(null);
    setTentative((precedente) => precedente + 1);
  }, []);
  const enLigne = useEtatDeConnexion(reessayer);
  const etat: Etat = !codeUtilisable
    ? { phase: 'introuvable' }
    : (courante?.etat ?? { phase: 'chargement' });

  useEffect(() => {
    if (!codeUtilisable) {
      return undefined;
    }
    const abandon = new AbortController();
    //  **CHAQUE MISE A JOUR EST UNE FUSION, JAMAIS UN REMPLACEMENT.** Les trois
    //  appels avancent independamment, dans un ordre que RIEN ne garantit. La
    //  fonction de fusion part de la charge du MEME code s'il y en a une, et
    //  d'une charge vide sinon : les droits peuvent donc arriver AVANT l'entite
    //  sans etre perdus.
    //
    //  **CE N'EST PAS UNE PRECAUTION, C'EST UN DEFAUT VU AU NAVIGATEUR** le
    //  24/08/2026. La premiere version portait la liste et les droits DANS la
    //  variante `trouvee`, et ne les y ecrivait que si cette variante existait
    //  deja. L'API rendait `est_entite_principale: false`, et la mention du §5.1
    //  n'apparaissait pas : le journal reseau montrait deux appels de permissions
    //  -- un abandonne, un a 200 -- dont le second revenait avant l'entite.
    //
    //  Et mes tests ne l'attrapaient pas : un `fetch` bouchonne resout dans
    //  l'ordre de creation des promesses, si bien que l'entite gagnait toujours.
    //  §7.24 -- le succes d'un test et la justesse du livrable sont deux
    //  grandeurs differentes.
    //  **CE QUI DISCRIMINE N'EST PAS LE CODE DANS L'ETAT, C'EST L'EFFET COURANT,
    //  ET IL A FALLU DEUX ESSAIS POUR LE VOIR.**
    //
    //  Essai 1 -- repartir d'une charge vide quand le code de l'etat differe :
    //  une reponse tardive de Bordeaux ECRASAIT l'etat de Lille par un
    //  `{ code: 'bordeaux', phase: 'chargement' }`, et l'en-tete perdait l'entite.
    //
    //  Essai 2 -- ignorer toute reponse dont le code differe de celui de l'etat :
    //  la PREMIERE reponse du nouvel effet est dans ce cas elle aussi -- l'etat
    //  porte encore Bordeaux quand Lille repond -- donc Lille etait ignoree, et
    //  l'ecran restait bloque sur « Chargement ».
    //
    //  Les deux essais confondaient deux situations que le code seul ne separe
    //  pas. Le nettoyage de l'effet, lui, les separe exactement : un effet
    //  nettoye est PAR DEFINITION supersede. `obsolete` est donc pose par le
    //  nettoyage, et chaque reponse le consulte.
    //
    //  Les deux essais ont ete trouves par le temoin de latence de
    //  `CadreApplicatif.test.tsx`, chacun avec un message different -- « perdait
    //  eXalt Lille », puis un delai d'attente. Un temoin qui attrape les
    //  regressions de deux correctifs successifs vaut ce qu'il a coute.
    let obsolete = false;
    const fusionner = (apport: Partial<Omit<Charge, 'code'>>): void => {
      if (obsolete) {
        return;
      }
      setCharge((precedent) => {
        const base: Charge =
          precedent !== null && precedent.code === code
            ? precedent
            : {
                code,
                etat: { phase: 'chargement' },
                autres: [],
                permissions: null,
                correlation: null,
              };
        return { ...base, ...apport, code };
      });
    };
    const poser = (phase: Etat): void => fusionner({ etat: phase });
    //  **LES TROIS APPELS PARTAGENT UN SEUL SIGNAL, ET C'EST LA QUATRIEME REGLE
    //  DU §23.3.** « Annule les requetes et caches associes a l'entite
    //  precedente » -- au pluriel. Un signal par appel laisserait abandonner l'un
    //  et pas l'autre, si bien que les permissions de l'entite quittee
    //  arriveraient sur l'entite nouvelle. Le defaut n'apparaitrait que SOUS
    //  LATENCE, donc jamais en local (§7.16).
    //
    //  **ET `Promise.all` N'EST PAS EMPLOYE, DELIBEREMENT.** Il ferait attendre
    //  l'affichage de l'entite -- que le §23.3 exige dans l'en-tete -- que la
    //  liste et les droits soient revenus.
    void lireLEntite(code, abandon.signal).then(
      (reponse) => {
        const suite: Partial<Omit<Charge, 'code'>> = { correlation: reponse.correlation };
        if (reponse.statut === 200 && reponse.corps !== null) {
          fusionner({ ...suite, etat: { phase: 'trouvee', entite: reponse.corps } });
        } else if (reponse.statut === 404) {
          fusionner({ ...suite, etat: { phase: 'introuvable' } });
        } else if (reponse.statut === 401) {
          fusionner({ ...suite, etat: { phase: 'session' } });
        } else {
          fusionner({ ...suite, etat: { phase: 'erreur' } });
        }
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          poser({ phase: 'erreur' });
        }
        return cause;
      },
    );
    //  **`fusionner` PORTE LE CODE, DONC UNE REPONSE LENTE NE PEUT PAS MIGRER.**
    //  Une liste lente pour Bordeaux ne s'appliquera pas a Paris : la charge
    //  fusionnee porte toujours le code de l'effet qui l'a demandee, et le rendu
    //  ne lit que la charge dont le code correspond a l'adresse. L'abandon reduit
    //  la fenetre, il ne la ferme pas -- un `fetch` resolu n'est plus annulable.
    void listerLesEntites(abandon.signal).then(
      (reponse) => {
        if (reponse.statut === 200 && reponse.corps !== null) {
          fusionner({ autres: reponse.corps.entites });
        }
      },
      (cause: unknown) => cause,
    );
    void lireLesPermissions(code, abandon.signal).then(
      (reponse) => {
        if (reponse.statut === 200 && reponse.corps !== null) {
          fusionner({ permissions: reponse.corps });
        }
      },
      (cause: unknown) => cause,
    );
    return () => {
      obsolete = true;
      abandon.abort();
    };
  }, [code, codeUtilisable, tentative]);

  //  **LE HORS CONNEXION PASSE AVANT TOUT LE RESTE, ET C'EST DELIBERE.** Sans
  //  reseau, « chargement » tournerait indefiniment et « erreur » dirait que
  //  l'entite n'a pas pu etre chargee -- vrai, mais inutile : la cause est connue
  //  et l'utilisateur ne peut rien faire d'autre qu'attendre. Le §17.2 veut « un
  //  etat EXPLICITE ».
  //
  //  **ET C'EST UN ETAT DISTINCT DE L'ERREUR, PAS UN ALIAS.** `navigator.onLine`
  //  ne dit pas « le service repond » : un navigateur derriere un portail captif
  //  rend `true`. Les confondre dirait de verifier sa connexion alors que c'est
  //  l'API qui est tombee -- §7.6, ne masque pas une cause que tu vas interpreter.
  if (!enLigne) {
    return (
      <Squelette titre="Hors connexion">
        <PanneauDErreur
          urgence="information"
          message={
            "La connexion reseau est perdue. Ce que cet ecran affiche date d'avant la coupure : " +
            'rien de nouveau ne peut etre charge, et aucune action ne peut aboutir. ' +
            'Le chargement reprend de lui-meme au retour de la connexion.'
          }
        />
      </Squelette>
    );
  }

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

  if (etat.phase === 'session') {
    return (
      <Squelette titre="Session expiree">
        {/*
          **AUCUNE REDIRECTION, ET C'EST LA REGLE DEJA POSEE.** `DEC-537` a
          tranche pour le fourre-tout 404 : « rend la page sans rediriger », parce
          que changer l'URL ferait perdre a l'utilisateur l'adresse qu'il suivait.
          Ici c'est la meme chose et cela compte davantage : l'adresse porte
          l'entite qu'il consultait, et il voudra y revenir apres s'etre
          reconnecte.

          **ET AUCUN BOUTON DE REESSAI.** Reessayer ne peut pas aboutir sans
          nouvelle session : le proposer serait l'avertissement faux du §7.21.
        */}
        <p className="app-message" data-ton="neutre" role="status">
          Votre session a expire ou a ete revoquee. Reconnectez-vous pour continuer ; cette adresse
          vous ramenera a la meme entite.
        </p>
        <ul className="app-liens">
          <li>
            <Link className="app-lien" to={CHEMINS.connexion}>
              Se reconnecter
            </Link>
          </li>
        </ul>
      </Squelette>
    );
  }

  if (etat.phase === 'erreur') {
    return (
      <Squelette titre="Chargement impossible">
        {/*
          **AVANT `T10`, CE MESSAGE DISAIT « puis reessayez » SANS RIEN POUR
          REESSAYER.** L'utilisateur devait recharger la page, ce qui lui fait
          perdre son contexte. Une phrase qui demande une action que l'ecran ne
          propose pas est de la famille de l'avertissement faux du §7.21.
        */}
        <PanneauDErreur
          message={
            "L'entite n'a pas pu etre chargee. Cela ne dit rien de son existence : " +
            'le service a peut-etre refuse la demande, ou la reponse n a pas abouti.'
          }
          correlation={courante?.correlation ?? null}
          onReessayer={reessayer}
        />
      </Squelette>
    );
  }

  //  **LE FRONTEND NE REAPPLIQUE PAS LE §5.1.** L'API a deja reduit les roles a
  //  `EMP` hors de l'entite principale, donc ceux qu'on recoit sont deja ceux qui
  //  s'appliquent. Refaire le calcul ici donnerait deux implementations d'une
  //  meme regle -- et la regle 5 du projet dit que l'API est l'autorite finale,
  //  pas la copie.
  const droits = droitsDeNavigation(courante?.permissions?.roles ?? null);

  //  **LE `<h1>` NE REPETE PAS LE NOM DE L'ENTITE.** Mesure a l'ecran en `T3` :
  //  avec le nom en titre, il apparaissait DEUX fois -- une fois dans l'en-tete,
  //  une fois en `<h1>` -- et un lecteur d'ecran l'entendait deux fois.
  return (
    <Squelette
      titre={titreDeLaPage}
      entite={etat.entite}
      selecteur={<SelecteurDEntite courante={etat.entite} entites={courante?.autres ?? []} />}
      //  `undefined` tant que les droits ne sont pas revenus — voir le type.
      consultationSeule={
        courante?.permissions == null ? undefined : !courante.permissions.estEntitePrincipale
      }
      //  **LES DROITS SONT DERIVES DES ROLES QUE L'API A RENDUS, ET UNE SEULE
      //  FOIS.** Les deux reperes de navigation -- le menu et la barre -- doivent
      //  montrer la MEME chose : les calculer separement donnerait deux verites
      //  possibles, et un utilisateur verrait « Administration » dans l'un et pas
      //  dans l'autre. Meme motif que le predicat unique de `routes.ts`.
      navigation={<NavigationPrincipale code={etat.entite.code} {...droits} />}
      barre={<BarreMobile code={etat.entite.code} {...droits} />}
    >
      <Outlet
        context={
          {
            entite: etat.entite,
            permissions: courante?.permissions ?? null,
          } satisfies ContexteEntite
        }
      />
    </Squelette>
  );
}
