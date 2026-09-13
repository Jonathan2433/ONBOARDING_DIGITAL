/**
 * La carte retournable accessible — LOT 5, `T10`, story `MVP-L05-US003`.
 *
 * LE CRITERE EST « CLIC, TOUCHER ET CLAVIER », ET LA REPONSE EST STRUCTURELLE
 *
 *   La face est un `<button>`. Ce n'est pas un detail d'implementation : un
 *   bouton natif est actionne au **clic**, au **toucher** -- le navigateur en
 *   derive un `click` -- et au **clavier**, par Entree ET Espace, sans qu'aucun
 *   gestionnaire n'ait a le prevoir. Un `<div onClick>` avec `onKeyDown` couvre
 *   les memes cas **tant qu'on n'oublie rien** : Espace, le `role`, le
 *   `tabIndex`, l'etat annonce. C'est le §7.35 -- rendre la propriete
 *   structurelle plutot que la tester.
 *
 *   **Et c'est verifiable** : un test qui retire le bouton casse tout ; un test
 *   qui oublierait Espace sur un `<div>` ne casserait rien.
 *
 * LES DEUX FACES EXISTENT, ET CELLE QU'ON NE VOIT PAS EST `hidden`
 *
 *   `hidden` est l'attribut, non `display: none` en CSS : il retire la face du
 *   parcours de tabulation ET de l'arbre d'accessibilite, ce qu'une classe CSS ne
 *   fait pas. Un lecteur d'ecran qui lirait le verso cache annoncerait des
 *   informations que l'ecran ne montre pas.
 *
 *   `aria-expanded` porte l'etat sur le bouton : c'est le seul attribut qui dise
 *   « cette commande revele du contenu », et il est annonce a chaque bascule.
 *
 * « VOIR PLUS » EST UN LIEN, ET IL EST FRERE DU BOUTON, JAMAIS ENFANT
 *
 *   Le backlog l'exige — « "Voir plus" ouvre le profil ». Un lien **dans** un
 *   bouton est un imbriquement interactif invalide : le navigateur en fait ce
 *   qu'il veut, et le clavier n'atteint pas toujours les deux. Les deux sont donc
 *   freres dans un `<article>`, et tous deux atteignables au Tab.
 *
 * L'ALTERNATIVE `reduced-motion` SUIT LA CONVENTION DU DEPOT, ET C'EST DELIBERE
 *
 *   Le CSS anime, et `@media (prefers-reduced-motion: reduce)` NEUTRALISE la
 *   transition. C'est la forme que `application.css` et `styles.css` emploient
 *   deja, toutes deux depuis le LOT 1.
 *
 *   **J'ai d'abord ecrit l'inverse** -- n'animer que sous `no-preference`, ce qui
 *   fait echouer vers l'absence de mouvement quand la requete media n'est pas
 *   evaluee. C'est defendable dans l'absolu, et ce serait une TROISIEME forme
 *   dans un depot qui en applique deja une, partout. Deux regles pour une seule
 *   est ce que `DEC-466` et `ECART-022` nomment un defaut : la coherence vaut ici
 *   plus que la nuance, et le critere demande qu'une alternative EXISTE.
 */
import type { CSSProperties, JSX, ReactNode } from 'react';
import { useId, useState } from 'react';

export interface ProprietesCarteRetournable {
  /** Le contenu du recto — photo et identite, §10.1. */
  readonly recto: ReactNode;
  /** Le contenu du verso — les informations professionnelles principales, §10.1. */
  readonly verso: ReactNode;
  /**
   * Le nom accessible de la commande, qui doit nommer LA PERSONNE.
   *
   * « Retourner la carte » seul serait ambigu dans une grille de cent cartes :
   * un lecteur d'ecran qui parcourt les commandes en entendrait cent identiques.
   */
  readonly nomAccessible: string;
  /** Le lien « Voir plus », rendu tel quel. */
  readonly voirPlus: ReactNode;
  /** Une classe supplementaire sur l'article, pour la bordure de cercle. */
  readonly className?: string | undefined;
  /**
   * Un style supplementaire sur l'article — la couleur de cercle, §10.1.
   *
   * **`| undefined` EST EXPLICITE, ET `exactOptionalPropertyTypes` L'EXIGE.** Le
   * dépôt active cette option : `?:` seul signifie « la clé peut être absente »,
   * non « la valeur peut valoir `undefined` ». Passer `undefined` sans le
   * déclarer est donc une erreur de type — et c'est une bonne chose, parce que
   * les deux ne sont pas la même chose pour un composant qui étale ses propriétés.
   */
  readonly style?: CSSProperties | undefined;
}

export function CarteRetournable({
  recto,
  verso,
  nomAccessible,
  voirPlus,
  className,
  style,
}: ProprietesCarteRetournable): JSX.Element {
  const [retournee, setRetournee] = useState(false);
  const identifiantDesFaces = useId();

  return (
    <article
      className={
        className === undefined ? 'ui-carte-retournable' : `ui-carte-retournable ${className}`
      }
      style={style}
    >
      <button
        type="button"
        className="ui-carte-retournable__face"
        aria-expanded={retournee}
        aria-controls={identifiantDesFaces}
        aria-label={nomAccessible}
        onClick={() => {
          setRetournee((precedent) => !precedent);
        }}
      >
        {/*
          **`aria-label` PLUTOT QU'UN TEXTE HORS-ECRAN, ET LA MESURE L'A IMPOSE.**
          Ma premiere version ajoutait un `<span>` masque a l'oeil. Le nom
          accessible calcule devenait alors la CONCATENATION du span et de tout
          le recto : « Retourner la carte de Ada Lovelace pour voir ses
          informations professionnellesAda Lovelace » -- sans separateur, et
          repetant le nom.

          `aria-label` REMPLACE le contenu pour le nom de la commande : un
          lecteur d'ecran qui tabule entend une phrase, et le contenu du recto
          reste lisible en navigation par element.
        */}
        <span className="ui-carte-retournable__faces" id={identifiantDesFaces}>
          <span className="ui-carte-retournable__recto" hidden={retournee}>
            {recto}
          </span>
          <span className="ui-carte-retournable__verso" hidden={!retournee}>
            {verso}
          </span>
        </span>
      </button>
      <div className="ui-carte-retournable__pied">{voirPlus}</div>
    </article>
  );
}
