/**
 * Carrousel — LOT 8, `T12`, cahier §13.3/§13.4 : « carrousels manuels et
 * accessibles sur mobile ». Premier ecran consommateur : `PageEntite.tsx`,
 * pour les trois sections de l'accueil qui ne plafonnent pas leur liste par
 * une mise en page verticale (arrivees recentes, evenements a venir, liens
 * internes — ce dernier n'etant meme pas borne par `NOMBRE_MONTRE`).
 *
 * MANUEL, ET C'EST STRUCTUREL, PAS UNE OPTION NON COCHEE
 *
 *   Le cahier l'exige explicitement (« manuels ») : aucune minuterie n'existe
 *   dans ce composant, et il ne peut donc pas en acquerir une par erreur — il
 *   n'y a simplement rien qui avance tout seul.
 *
 * LA PISTE EST UNE LISTE QUI DEFILE, PAS UN INDEX REACT
 *
 *   Pas de « diapositive active » en etat : la piste est un `<ul>` natif en
 *   defilement horizontal (CSS, `application.css`/`composants.css`), et les
 *   deux boutons avancent/reculent ce DEFILEMENT d'une largeur de piste —
 *   jamais un index qui demonterait et remonterait des elements. Un clavier
 *   qui tabule atteint donc chaque element dans l'ordre naturel du DOM,
 *   identique a une liste verticale : aucun piege de focus, aucun element
 *   qui disparaitrait du parcours entre deux rendus.
 *
 * SEUL LE MOBILE VOIT LES COMMANDES, MEME DISCIPLINE QUE LA BARRE DU §8.2
 *
 *   Au-dela de 768 px, le CSS repasse la piste en liste verticale et masque
 *   les boutons par `display: none` (LOT 4, `T5`) : pas de second jeu
 *   d'elements, donc aucun doublon dans l'ordre de tabulation — exactement
 *   le motif deja retenu pour la barre de navigation inferieure.
 *
 * LA TRANSITION SUIT `prefers-reduced-motion` EN CSS, PAS EN JAVASCRIPT
 *
 *   `scrollBy` est appele SANS `behavior` explicite : c'est `scroll-behavior`
 *   en CSS qui decide, et cette regle est neutralisee sous la preference
 *   reduite — meme forme que `CarteRetournable` et `application.css` depuis
 *   le LOT 1. Un second mecanisme en JavaScript serait une deuxieme regle
 *   pour la meme chose, ce que `DEC-466`/`ECART-022` nomment un defaut.
 *
 * LES BOUTONS S'EPUISENT AUX EXTREMITES
 *
 *   « Precedent » et « Suivant » se desactivent en butee, mesure sur
 *   `scrollLeft`/`scrollWidth`/`clientWidth` — un bouton actionnable qui ne
 *   ferait rien apprendrait a l'ignorer (§7.21 : un garde-fou qui ment est
 *   pire que son absence).
 *
 * PAS DE SECOND REPERE : `libelle` NOMME LA LISTE, JAMAIS UNE REGION
 *
 *   Ce composant est toujours imbrique dans une `<Carte titre="…">` (LOT 1,
 *   `T10`), qui EST DEJA une region nommee par ce meme titre. Envelopper la
 *   piste d'un second `role="region"` portant le MEME nom produirait deux
 *   reperes identiques dans la liste des reperes d'un lecteur d'ecran — et,
 *   mesure directement, une collision de requete : `getByRole('region', …)`
 *   en trouve alors DEUX. `libelle` nomme donc la LISTE elle-meme
 *   (`aria-label` sur le `<ul>`, role `list`, jamais `region`) et les deux
 *   boutons — jamais un conteneur de plus.
 */
import type { JSX, ReactNode, UIEvent } from 'react';
import { useEffect, useRef, useState } from 'react';

export interface ProprietesCarrousel {
  /** Nomme la region ET les deux commandes — plusieurs carrousels sur une
   * meme page ne doivent jamais partager un nom de bouton ambigu. */
  readonly libelle: string;
  /** Les elements de la piste. L'appelant fournit lui-meme chaque `<li>`. */
  readonly children: ReactNode;
}

function mesurerLaPosition(piste: HTMLUListElement): { auDebut: boolean; alaFin: boolean } {
  return {
    auDebut: piste.scrollLeft <= 0,
    alaFin: Math.ceil(piste.scrollLeft + piste.clientWidth) >= piste.scrollWidth,
  };
}

export function Carrousel({ libelle, children }: ProprietesCarrousel): JSX.Element {
  const refPiste = useRef<HTMLUListElement>(null);
  const [auDebut, setAuDebut] = useState(true);
  const [alaFin, setALaFin] = useState(true);

  useEffect(() => {
    const piste = refPiste.current;
    if (piste === null) {
      return undefined;
    }
    const recalculer = (): void => {
      const position = mesurerLaPosition(piste);
      setAuDebut(position.auDebut);
      setALaFin(position.alaFin);
    };
    recalculer();
    window.addEventListener('resize', recalculer);
    return () => {
      window.removeEventListener('resize', recalculer);
    };
  }, [children]);

  const gererLeDefilement = (evenement: UIEvent<HTMLUListElement>): void => {
    const position = mesurerLaPosition(evenement.currentTarget);
    setAuDebut(position.auDebut);
    setALaFin(position.alaFin);
  };

  const defiler = (sens: -1 | 1): void => {
    const piste = refPiste.current;
    if (piste === null) {
      return;
    }
    piste.scrollBy({ left: sens * piste.clientWidth });
  };

  return (
    <div className="ui-carrousel">
      <ul
        ref={refPiste}
        className="ui-carrousel__piste"
        aria-label={libelle}
        onScroll={gererLeDefilement}
      >
        {children}
      </ul>
      <div className="ui-carrousel__commandes">
        <button
          type="button"
          className="ui-carrousel__commande"
          onClick={() => {
            defiler(-1);
          }}
          disabled={auDebut}
          aria-label={`${libelle} : element precedent`}
        >
          <span aria-hidden="true">‹</span>
        </button>
        <button
          type="button"
          className="ui-carrousel__commande"
          onClick={() => {
            defiler(1);
          }}
          disabled={alaFin}
          aria-label={`${libelle} : element suivant`}
        >
          <span aria-hidden="true">›</span>
        </button>
      </div>
    </div>
  );
}
