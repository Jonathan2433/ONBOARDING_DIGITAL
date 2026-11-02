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
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';

import { STATUTS, couleurDuCercle, libelleDuStatut, texteDuCercle } from '../affichage';
import { type CriteresDeRecherche, listerLeTrombinoscope } from '../api/trombinoscope';
import { cheminDuProfilALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import {
  type CollaborateurDuTrombinoscope,
  TAILLE_PAR_DEFAUT,
  TAILLES_DE_PAGE,
} from '@onboarding/contracts';
import { Alerte, Avatar, CarteRetournable, Champ, Liste } from '@onboarding/ui';

/** §9.3 : « la recherche demarre apres environ 300 ms ». */
export const TEMPORISATION_DE_SAISIE_MS = 300;

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
  const [statut, setStatut] = useState('');
  const [taille, setTaille] = useState<number>(TAILLE_PAR_DEFAUT);
  const [page, setPage] = useState(1);
  const [resultat, setResultat] = useState<Resultat | null>(null);

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

  const criteres = useMemo(
    () => ({ page, taille, recherche, statut }),
    [page, taille, recherche, statut],
  );

  useEffect(() => {
    const abandon = new AbortController();
    void listerLeTrombinoscope(entite.code, criteres, abandon.signal).then(
      (reponse) => {
        setResultat({
          criteres,
          valeur:
            reponse.statut === 200 && reponse.corps !== null
              ? { phase: 'liste', page: reponse.corps }
              : { phase: 'erreur', statut: reponse.statut },
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
          **LES TROIS FILTRES PASSENT PAR `Champ` ET `Liste` — charte 6.3.**
          Les deux composants portent eux-memes leur `<label>` lie, leur
          `id` engendre et leur anneau de focus par `var(--anneau-focus)` : le
          `.trombi-champ` qu'ils remplacent avait le sien ecrit a la main,
          juste en theme clair et en echec en sombre depuis `S9`. Un defaut de
          moins a corriger a `E6`.

          **LE FILTRE « CERCLE » DE LA CHARTE N'EST PAS AJOUTE ICI** : l'API
          l'accepte (`cercle` est un parametre de `GET …/people`), mais le
          poser serait ajouter une FONCTION, et la consigne de `E5` est de ne
          changer que la presentation. Ecart consigne pour `E7`.
        */}
        <Champ
          libelle="Rechercher un collaborateur"
          onChange={(evenement) => {
            setSaisie(evenement.target.value);
          }}
          placeholder="Nom ou prenom"
          type="search"
          value={saisie}
        />

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

        <Liste
          libelle="Par page"
          onChange={(evenement) => {
            setTaille(Number(evenement.target.value));
            setPage(1);
          }}
          value={String(taille)}
        >
          {TAILLES_DE_PAGE.map((valeur) => (
            <option key={valeur} value={String(valeur)}>
              {valeur}
            </option>
          ))}
        </Liste>
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

      {etat?.phase === 'liste' && etat.page.pages > 1 ? (
        <nav aria-label="Pagination du trombinoscope" className="trombi-pagination">
          <button
            type="button"
            className="trombi-page"
            disabled={etat.page.page <= 1}
            onClick={() => {
              setPage((precedente) => Math.max(1, precedente - 1));
            }}
          >
            Page precedente
          </button>
          <span className="trombi-position">
            Page {etat.page.page} sur {etat.page.pages}
          </span>
          <button
            type="button"
            className="trombi-page"
            disabled={etat.page.page >= etat.page.pages}
            onClick={() => {
              setPage((precedente) => precedente + 1);
            }}
          >
            Page suivante
          </button>
        </nav>
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
  const couleur = couleurDuCercle(ligne.cercle?.jetonDeCouleur ?? null);
  const texte = texteDuCercle(ligne.cercle?.jetonDeCouleur ?? null);
  const libelleStatut = libelleDuStatut(ligne.statut);

  return (
    //  **LA CARTE NE PORTE PLUS `--carte-cercle`, ET C'EST LE FOND DE LA MESURE
    //  DE `E4`.** Cette variable y mettait la couleur du cercle en trait de
    //  2 px : exactement l'emploi qui faisait passer cinq surfaces sur huit
    //  sous 3:1. La couleur est desormais REMPLIE dans le bandeau, et la carte
    //  retombe sur le repli neutre que `composants.css` declare au `:root`.
    //  Une seule chose porte la couleur, et c'est celle qui peut la porter.
    <CarteRetournable
      nomAccessible={`Retourner la carte de ${nom} pour voir ses informations professionnelles`}
      recto={
        <>
          {/*
            **LE CERCLE DEVIENT UN BANDEAU REMPLI, ET C'EST LA CORRECTION QUE
            `E4` AVAIT MESUREE ET LAISSEE A `E5`.** Releve le 02/11/2026 dans un
            vrai navigateur : pose en trait d'accent de 4 px sur une carte
            claire, CINQ des huit surfaces de cercle passent sous 3:1 — `change`
            1,37, `data` 1,17, `shield` 1,19, `forge` 1,08, `it` 1,09 — et trois
            d'entre elles sont litteralement invisibles.

            La charte n'etait pas en faute : ses huit entrees sont des couples
            SURFACE + TEXTE faits pour etre REMPLIS, ou la paleur est justement
            ce qui rend le texte lisible. Le bandeau de 150 px de la charte 6.3
            est cet emploi-la, et le couple `surface`/`texte` y retrouve la
            mesure qui l'accompagne.

            **LA COULEUR N'EST TOUJOURS PAS SEULE** : le nom du cercle reste
            ecrit en toutes lettres sous le bandeau (§10.1), et sans cercle le
            bandeau retombe sur une surface neutre.
          */}
          <span
            className="trombi-bandeau"
            style={
              couleur === undefined
                ? undefined
                : ({ background: couleur, color: texte } as React.CSSProperties)
            }
          >
            {/*
              **L'AVATAR EST DESORMAIS CELUI DU DESIGN SYSTEM.** Il porte la
              meme regle qu'ailleurs : la photo quand elle est servable, les
              initiales sinon — les CINQ causes d'absence restant
              indistinguables a dessein (§21.2). Decoratif, parce que le nom
              est juste en dessous : l'annoncer le ferait entendre deux fois.
            */}
            <Avatar
              nom={nom}
              taille={84}
              {...(ligne.photo === null ? {} : { photo: ligne.photo })}
            />
          </span>
          <span className="trombi-infos">
            <span className="trombi-nom">{nom}</span>
            <span className="trombi-role">{ligne.metier ?? 'Metier non renseigne'}</span>
            <span className="trombi-cercle">
              {ligne.cercle === null ? 'Aucun cercle principal' : ligne.cercle.nom}
            </span>
          </span>
        </>
      }
      verso={
        <div className="trombi-verso">
          {/*
            **LE NOM EST AUSSI AU VERSO — charte 6.3.** Une seule face est dans
            le DOM a la fois : carte retournee, le recto porte `hidden`, et sans
            cette ligne la carte cesserait de dire QUI elle montre. C'est la
            raison d'etre de la charte sur ce point, pas une redite.
          */}
          <p className="trombi-verso-nom">{nom}</p>
          <dl className="trombi-verso-liste">
            <dt>Metier</dt>
            <dd>{ligne.metier ?? 'Non renseigne'}</dd>
            <dt>Statut</dt>
            {/*
            **PASTILLE BLANCHE POUR LE STATUT, JAUNE POUR LE CLIENT — charte
            6.3.** Le verso est un aplat de bleu fonce, et les tons semantiques
            de `Badge` (`mission`, `intercontrat`) sont des surfaces CLAIRES
            appariees a un texte fonce : les poser ici donnerait un couple que
            personne n'a mesure sur ce fond. Les deux pastilles de la charte
            sont, elles, appariees a ce bleu — ce sont les couples
            `--marque-jaune` et `--surface`/`--encre`, deja prouves.

            Le libelle porte l'information dans les deux cas ; la couleur ne
            fait que distinguer les deux lignes.
          */}
            <dd>
              {libelleStatut === null ? (
                'Non renseigne'
              ) : (
                <span className="trombi-pastille-statut">{libelleStatut}</span>
              )}
            </dd>
            <dt>Client</dt>
            <dd>
              {ligne.client === null ? (
                'Non renseigne'
              ) : (
                <span className="trombi-pastille-client">{ligne.client}</span>
              )}
            </dd>
            <dt>Cercle</dt>
            {/*
            **LE NOM DU CERCLE EN TOUTES LETTRES, ET C'EST LE §10.1** : la couleur
            ne remplit que le bandeau, elle ne transmet jamais seule l'information.
          */}
            <dd>{ligne.cercle === null ? 'Aucun cercle principal' : ligne.cercle.nom}</dd>
          </dl>
        </div>
      }
      voirPlus={
        <Link
          //  **`aria-label` PLUTOT QU'UN TEXTE HORS-ECRAN, ET LA MESURE L'A
          //  IMPOSE DEUX FOIS.** Un `<span>` masque a l'oeil produisait
          //  « Voir plussur Ada Lovelace » : le calcul du nom accessible
          //  concatene les noeuds de texte SANS separateur, et ni JSX ni une
          //  accolade n'y changent rien. Dans une grille de cent cartes, cent
          //  liens nommes « Voir plus » seraient indistinguables ; `aria-label`
          //  nomme la personne, sans toucher au texte visible.
          aria-label={`Voir plus sur ${nom}`}
          className="trombi-voir-plus"
          to={cheminDuProfilALEcran(codeEntite, ligne.id)}
        >
          Voir plus
        </Link>
      }
    />
  );
}
