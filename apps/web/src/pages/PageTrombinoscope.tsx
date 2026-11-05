/**
 * Le trombinoscope a l'ecran — LOT 5, `T10`, story `MVP-L05-US003`.
 *
 * LE CRITERE, ET CE QUI LE REND VRAI
 *
 *   « Le recto/verso fonctionne au clic, toucher et clavier ; une alternative
 *   reduced-motion existe ; "Voir plus" ouvre le profil. » Les trois premiers
 *   sont portes par `CarteRetournable`, dont la face est un `<button>` natif :
 *   voir son en-tete, la reponse y est STRUCTURELLE plutot que testee.
 *
 * LA TEMPORISATION DE SAISIE EST DE 300 ms, ET C'EST LE §9.3
 *
 *   `ECART-050` a etabli que ce delai est un delai d'ECRAN, non un budget de
 *   reponse : le §9.3 donne 300 ms de temporisation, le §25.2 donne 800 ms au
 *   P95. `T3` avait retire ce delai de son perimetre en le nommant ; il est ici.
 *
 *   **Sans lui, chaque frappe lancerait une requete.** Avec cinq mille profils,
 *   « Alexandra » en lancerait dix.
 *
 * DEUX FILTRES SUR SIX, ET C'EST MESURE PLUTOT QU'OUBLIE
 *
 *   L'API en accepte cinq depuis `T3`. Quatre prennent un **identifiant** --
 *   cercle, DSM, metier, client -- et **aucun endpoint ne sert ces listes** :
 *   mesure du 12/09/2026 sur les vingt-et-un chemins du manifeste, zero. Un ecran
 *   ne peut pas offrir un choix dont il ignore les options, et en fabriquer une
 *   liste depuis la page courante donnerait un filtre qui ne propose que ce qui
 *   est deja visible.
 *
 *   `statut` fait exception : son domaine est **ferme**, `mission` ou
 *   `intercontract`, §6.5 du modele. Les quatre autres arriveront avec les
 *   endpoints de reference — les cercles au **LOT 6**, le reste au **LOT 9**.
 *
 * LA COULEUR DU CERCLE N'EST JAMAIS SEULE, ET LE §10.1 L'EXIGE
 *
 *   « La couleur du cercle peut etre utilisee sur les bordures, arriere-plans
 *   legers et badges, mais **jamais comme seul moyen de transmettre une
 *   information**. » Le nom du cercle est donc ecrit en toutes lettres sur le
 *   verso, et la couleur ne fait que border la carte. Un test l'exige.
 *
 *   **UN JETON INCONNU NE DONNE AUCUNE COULEUR, ET SURTOUT PAS UNE INVENTEE.**
 *   Le design system dit, depuis `T10` du LOT 1 : « aucune couleur de cercle :
 *   c'est une notion metier du **LOT 6** ». Les quatre jetons de marque sont donc
 *   les seuls reconnus ; tout autre laisse la bordure neutre, et le nom du cercle
 *   reste lisible -- ce qui est exactement ce que le §10.1 protege.
 *
 * CHANTIER FRONT, S6 (`DEC-672`) : LE STATUT DEVIENT UN `BADGE`, ET `CARTERETOURNABLE`
 * EST VERIFIEE COMME LE BON VEHICULE
 *
 *   Le statut du verso etait du texte simple ; il rejoint le `Badge` que le
 *   PROFIL porte deja pour la meme donnee (LOT 5 `T11`) -- les deux ecrans disent
 *   desormais la meme chose de la meme facon.
 *
 *   **`CarteRetournable` N'EST PAS REMPLACEE PAR `Carte`, ET C'EST UNE VERIFICATION,
 *   PAS UN OUBLI.** `Carte` (`packages/ui`) n'accepte ni `className` ni `style`
 *   (`ProprietesCarte` les exclut explicitement) : elle ne pourrait pas porter la
 *   bordure de couleur du cercle (`--carte-cercle`, §10.1), et n'offre surtout
 *   aucun recto/verso -- la richesse que le critere de `MVP-L05-US003` exige
 *   (« le recto/verso fonctionne au clic, toucher et clavier »). `CarteRetournable`
 *   fournit deja les DEUX (`className`/`style` pour la couleur, `recto`/`verso`
 *   pour le retournement) sur un `<button>` natif -- la propriete STRUCTURELLE du
 *   §7.35 de la passation. C'est le bon vehicule, et aucune icone de bureau ni
 *   aucun dégradé ne s'y ajoute : rien dans le §13.2 ne s'applique a une carte
 *   dont le contenu entier est deja une photo et un nom.
 */
import type { JSX } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';

import { STATUTS, couleurDuCercle, texteDuCercle } from '../affichage';
import { lireLeFramework } from '../api/organisation';
import { type CriteresDeRecherche, listerLeTrombinoscope } from '../api/trombinoscope';
import { cheminDuProfilALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import { type CarteDeCercle, type CollaborateurDuTrombinoscope } from '@onboarding/contracts';
import { Alerte, Avatar, Bouton, Champ, Liste, Picto } from '@onboarding/ui';

/** §9.3 : « la recherche demarre apres environ 300 ms ». */
export const TEMPORISATION_DE_SAISIE_MS = 300;
const TAILLE_D_UN_LOT = 50;

function couleursMarquantesDuCercle(
  code: string | null,
  jeton: string | null,
): readonly [string | undefined, string | undefined] {
  const cle = code?.toLocaleLowerCase('fr') ?? null;
  if (cle === null) return ['var(--trombi-sans-cercle)', 'var(--trombi-sans-cercle-texte)'];
  if (['data', 'shield', 'forge', 'it'].includes(cle)) {
    return [`var(--trombi-cercle-${cle})`, `var(--trombi-cercle-${cle}-texte)`];
  }
  return [couleurDuCercle(jeton), texteDuCercle(jeton)];
}

//  **`STATUTS` ET LES COULEURS DE CERCLE ONT DEMENAGE EN `T11`**, dans
//  `../affichage`. Ils avaient UN consommateur quand `T10` les a poses ; la fiche
//  profil est le second, et une page qui en importe une autre casse le jour ou
//  celle-ci est renommee. Les recopier aurait ete pire -- §7.27.

/**
 * Le dernier resultat connu, et POUR QUELS criteres.
 *
 * **LE CHARGEMENT EST DERIVE, IL N'EST PAS UN ETAT POSE.** Ma premiere version
 * appelait `setEtat({ phase: 'chargement' })` au debut de l'effet, ce que la
 * regle React refuse : « Calling setState synchronously within an effect can
 * trigger cascading renders ». Elle a raison, et la correction est meilleure que
 * le contournement -- comparer les criteres du resultat a ceux demandes dit
 * exactement la meme chose, sans rendu supplementaire.
 *
 * **Et l'ecran y gagne** : les resultats precedents restent visibles pendant le
 * chargement du suivant, au lieu de disparaitre a chaque frappe. C'est ce qu'une
 * recherche a la volee doit faire.
 */
interface Resultat {
  readonly criteres: CriteresDeRecherche;
  readonly valeur:
    | { readonly phase: 'liste'; readonly page: ReponseChargee }
    | { readonly phase: 'erreur'; readonly statut: number };
}

interface ReponseChargee {
  readonly collaborateurs: readonly CollaborateurDuTrombinoscope[];
  readonly page: number;
  readonly total: number;
  readonly pages: number;
}

/** Le nom affiche : le nom prefere quand il existe, sinon le prenom. §10.2. */
export function nomAffiche(ligne: CollaborateurDuTrombinoscope): string {
  return `${ligne.nomPrefere ?? ligne.prenom} ${ligne.nom}`;
}

export function PageTrombinoscope(): JSX.Element {
  const { entite } = useEntiteConsultee();
  const [saisie, setSaisie] = useState('');
  const [recherche, setRecherche] = useState('');
  const [cercle, setCercle] = useState('');
  const [cercles, setCercles] = useState<readonly CarteDeCercle[] | null>(null);
  const [statut, setStatut] = useState('');
  const [page, setPage] = useState(1);
  const [resultat, setResultat] = useState<Resultat | null>(null);
  const sentinelle = useRef<HTMLButtonElement | null>(null);

  //  **LA TEMPORISATION DU §9.3.** Le nettoyage annule le minuteur precedent :
  //  sans lui, chaque frappe en armerait un de plus et ils se declencheraient
  //  tous, ce qui rendrait la temporisation decorative.
  useEffect(() => {
    const minuteur = setTimeout(() => {
      setRecherche(saisie);
      setPage(1);
    }, TEMPORISATION_DE_SAISIE_MS);
    return () => {
      clearTimeout(minuteur);
    };
  }, [saisie]);

  useEffect(() => {
    const abandon = new AbortController();
    void lireLeFramework(entite.code, abandon.signal).then(
      (reponse) => {
        setCercles(
          reponse.statut === 200 && reponse.corps !== null
            ? [...reponse.corps.cercles].sort((a, b) => a.nom.localeCompare(b.nom, 'fr'))
            : [],
        );
      },
      () => {
        if (!abandon.signal.aborted) setCercles([]);
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code]);

  const criteres = useMemo(
    () => ({ page, taille: TAILLE_D_UN_LOT, recherche, cercle, statut }),
    [page, recherche, cercle, statut],
  );

  useEffect(() => {
    const abandon = new AbortController();
    void listerLeTrombinoscope(entite.code, criteres, abandon.signal).then(
      (reponse) => {
        setResultat((precedent) => {
          if (reponse.statut !== 200 || reponse.corps === null) {
            return { criteres, valeur: { phase: 'erreur', statut: reponse.statut } };
          }
          const peutAjouter =
            criteres.page > 1 &&
            precedent?.valeur.phase === 'liste' &&
            precedent.criteres.recherche === criteres.recherche &&
            precedent.criteres.cercle === criteres.cercle &&
            precedent.criteres.statut === criteres.statut;
          let collaborateurs = reponse.corps.collaborateurs;
          if (peutAjouter && precedent?.valeur.phase === 'liste') {
            const existants = precedent.valeur.page.collaborateurs;
            collaborateurs = [
              ...existants,
              ...reponse.corps.collaborateurs.filter(
                (nouveau) => !existants.some((existant) => existant.id === nouveau.id),
              ),
            ];
          }
          return {
            criteres,
            valeur: {
              phase: 'liste',
              page: { ...reponse.corps, collaborateurs },
            },
          };
        });
      },
      (cause: unknown) => {
        //  Un abandon n'est pas une panne : la requete a ete remplacee, et
        //  afficher une erreur ferait clignoter l'ecran a chaque frappe.
        if (!abandon.signal.aborted) {
          setResultat({ criteres, valeur: { phase: 'erreur', statut: 0 } });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code, criteres]);

  //  `criteres` est memoise par identite : une comparaison de reference suffit,
  //  et elle est exacte -- deux objets de memes valeurs sont deux criteres
  //  differents seulement si `useMemo` les a recalcules, ce qu'il ne fait que
  //  quand une valeur a change.
  const enChargement = resultat === null || resultat.criteres !== criteres;
  const etat = resultat?.valeur ?? null;
  const peutChargerLaSuite =
    etat?.phase === 'liste' && etat.page.page < etat.page.pages && !enChargement;

  useEffect(() => {
    const cible = sentinelle.current;
    if (!peutChargerLaSuite || cible === null || typeof IntersectionObserver === 'undefined') {
      return undefined;
    }
    const observateur = new IntersectionObserver(
      (entrees) => {
        if (entrees.some((entree) => entree.isIntersecting)) {
          setPage((precedente) => precedente + 1);
        }
      },
      { rootMargin: '400px 0px' },
    );
    observateur.observe(cible);
    return () => {
      observateur.disconnect();
    };
  }, [peutChargerLaSuite]);

  return (
    <div className="trombi">
      <form
        className="trombi-criteres"
        onSubmit={(evenement) => {
          //  **LE FORMULAIRE NE SE SOUMET PAS, ET IL EXISTE QUAND MEME.** Entree
          //  dans un champ de recherche rechargerait la page ; le supprimer
          //  priverait les lecteurs d'ecran du groupement que `<form>` annonce.
          evenement.preventDefault();
        }}
        role="search"
      >
        {/*
          **LES FILTRES PASSENT PAR `Champ` ET `Liste` — charte 6.3.**
          Les deux composants portent eux-memes leur `<label>` lie, leur
          `id` engendre et leur anneau de focus par `var(--anneau-focus)` : le
          `.trombi-champ` qu'ils remplacent avait le sien ecrit a la main,
          juste en theme clair et en echec en sombre depuis `S9`. `E6` a retire
          cette regle devenue morte.

          La liste des cercles vient de la synthese Framework de l'entite :
          chaque option porte ainsi le vrai identifiant attendu par l'API, et
          jamais un code reconstruit dans le frontend.
        */}
        <div className="trombi-filtre trombi-filtre--recherche" data-actif={saisie !== ''}>
          <Picto nom="loupe" taille={24} />
          <Champ
            libelle="Rechercher un collaborateur"
            onChange={(evenement) => {
              setSaisie(evenement.target.value);
            }}
            placeholder="Nom ou prénom"
            type="search"
            value={saisie}
          />
        </div>

        <div className="trombi-filtre" data-actif={cercle !== ''}>
          <Liste
            disabled={cercles === null}
            libelle="Cercle"
            onChange={(evenement) => {
              setCercle(evenement.target.value);
              setPage(1);
            }}
            value={cercle}
          >
            <option value="">
              {cercles === null ? 'Chargement des cercles…' : 'Tous les cercles'}
            </option>
            {(cercles ?? []).map((choix) => (
              <option key={choix.identifiant} value={choix.identifiant}>
                {choix.nom}
              </option>
            ))}
          </Liste>
        </div>

        <div className="trombi-filtre" data-actif={statut !== ''}>
          <Liste
            libelle="Statut"
            onChange={(evenement) => {
              setStatut(evenement.target.value);
              setPage(1);
            }}
            value={statut}
          >
            <option value="">Tous les statuts</option>
            {STATUTS.map((choix) => (
              <option key={choix.valeur} value={choix.valeur}>
                {choix.libelle}
              </option>
            ))}
          </Liste>
        </div>

        {saisie !== '' || cercle !== '' || statut !== '' ? (
          <span className="trombi-effacer-filtres">
            <Bouton
              onClick={() => {
                setSaisie('');
                setRecherche('');
                setCercle('');
                setStatut('');
                setPage(1);
              }}
              taille="s"
              variante="discret"
            >
              Effacer les filtres
            </Bouton>
          </span>
        ) : null}
      </form>

      {/*
        **LE COMPTE EST ANNONCE AUX LECTEURS D'ECRAN, PAS SEULEMENT AFFICHE.**
        `aria-live="polite"` : la grille change sans que le focus bouge, et sans
        cette region le changement serait silencieux pour qui ne voit pas.
      */}
      <p aria-live="polite" className="trombi-compte">
        {enChargement ? 'Chargement du trombinoscope…' : null}
        {!enChargement && etat?.phase === 'liste'
          ? `${String(etat.page.total)} collaborateur${etat.page.total > 1 ? 's' : ''}`
          : null}
      </p>

      {etat?.phase === 'erreur' ? (
        <Alerte ton="erreur" urgence="alerte">
          {etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter le trombinoscope.'
            : "Le trombinoscope n'a pas pu etre charge. Cela ne dit rien des collaborateurs : verifiez votre connexion, puis reessayez."}
        </Alerte>
      ) : null}

      {etat?.phase === 'liste' && etat.page.collaborateurs.length === 0 ? (
        //  Un etat LEGITIME, pas une panne — et le dire autrement apprendrait
        //  quelque chose de faux.
        <Alerte>
          Aucun collaborateur ne correspond. Ce n&rsquo;est pas une erreur : essayez d&rsquo;elargir
          la recherche ou de retirer le filtre.
        </Alerte>
      ) : null}

      {etat?.phase === 'liste' && etat.page.collaborateurs.length > 0 ? (
        <ul className="trombi-grille">
          {etat.page.collaborateurs.map((ligne) => (
            <li key={ligne.id}>
              <CarteDuCollaborateur codeEntite={entite.code} ligne={ligne} />
            </li>
          ))}
        </ul>
      ) : null}

      {etat?.phase === 'liste' && etat.page.page < etat.page.pages ? (
        <div className="trombi-scroll-suite">
          <button
            className="trombi-charger-suite"
            disabled={enChargement}
            onClick={() => {
              setPage((precedente) => precedente + 1);
            }}
            ref={sentinelle}
            type="button"
          >
            {enChargement ? 'Chargement de la suite…' : 'Charger les collaborateurs suivants'}
          </button>
        </div>
      ) : null}
    </div>
  );
}

interface ProprietesCarte {
  readonly codeEntite: string;
  readonly ligne: CollaborateurDuTrombinoscope;
}

function CarteDuCollaborateur({ codeEntite, ligne }: ProprietesCarte): JSX.Element {
  const nom = nomAffiche(ligne);
  //  **DEUX ABSENCES DISTINCTES, ET LE MEME RENDU.** Pas de cercle, ou un cercle
  //  sans jeton declare : la bordure reste neutre dans les deux cas, et le NOM du
  //  cercle reste du texte sur le verso -- c'est le §10.1 qui l'exige.
  const [couleur, texte] = couleursMarquantesDuCercle(
    ligne.cercle?.code ?? null,
    ligne.cercle?.jetonDeCouleur ?? null,
  );
  return (
    <article aria-label={`Carte de ${nom}`} className="trombi-carte">
      <div className="trombi-carte-interieur">
        <div className="trombi-carte-face trombi-carte-recto">
          <span
            className="trombi-bandeau"
            style={
              couleur === undefined
                ? undefined
                : ({ background: couleur, color: texte } as React.CSSProperties)
            }
          >
            <Avatar
              nom={nom}
              taille={56}
              {...(ligne.photo === null ? {} : { photo: ligne.photo })}
            />
          </span>
          <span className="trombi-infos">
            <span className="trombi-nom">{nom}</span>
            <span className="trombi-cercle">
              {ligne.cercle === null ? 'Aucun cercle principal' : ligne.cercle.nom}
            </span>
          </span>
        </div>
        <div className="trombi-carte-face trombi-carte-verso">
          <div className="trombi-verso">
            <p className="trombi-verso-nom">{nom}</p>
            <dl className="trombi-verso-liste">
              <dt>Cercle</dt>
              <dd>{ligne.cercle === null ? 'Aucun cercle principal' : ligne.cercle.nom}</dd>
            </dl>
            <Link
              aria-label={`Voir plus sur ${nom}`}
              className="trombi-voir-plus trombi-voir-plus-verso"
              to={cheminDuProfilALEcran(codeEntite, ligne.id)}
            >
              Voir plus
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
