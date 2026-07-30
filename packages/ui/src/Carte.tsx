/**
 * Carte — composant de base du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.2, 13.3, 14.
 *
 * « CARTES ARRONDIES, OMBRES DOUCES » — cahier 13.2, litteralement. Le rayon et
 * l'ombre viennent des jetons `--rayon-l` et `--ombre-douce`, pas d'un choix
 * local.
 *
 * POURQUOI UN TITRE FACULTATIF CHANGE LE BALISAGE
 *
 *   Avec un titre, la carte devient une `<section>` porteuse d'un `<h2>` et
 *   d'un `aria-labelledby` qui la relie a ce titre : elle apparait alors comme
 *   une region nommee dans la liste des reperes d'un lecteur d'ecran.
 *
 *   Sans titre, elle reste un `<div>`. Une `<section>` SANS nom accessible n'est
 *   pas annoncee comme un repere par la plupart des lecteurs d'ecran : la
 *   produire quand meme donnerait l'illusion d'une structure sans en fournir une.
 *   Le balisage suit donc ce qui est reellement disponible.
 *
 *   Le niveau du titre est reglable. Un composant qui imposerait `<h2>` casserait
 *   la hierarchie des titres — WCAG 1.3.1 — des qu'une carte serait imbriquee
 *   dans une section plus profonde.
 */

import { useId } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';

/** Niveaux autorises pour le titre. `h1` est exclu : il appartient a la page. */
export type NiveauTitre = 'h2' | 'h3' | 'h4';

export interface ProprietesCarte extends Omit<HTMLAttributes<HTMLElement>, 'className' | 'title'> {
  readonly children: ReactNode;
  /** Facultatif. S'il est fourni, la carte devient une region nommee. */
  readonly titre?: string;
  /** `h2` par defaut. Sans effet si `titre` est absent. */
  readonly niveauTitre?: NiveauTitre;
}

export function Carte({
  children,
  titre,
  niveauTitre = 'h2',
  ...reste
}: ProprietesCarte): ReactNode {
  // `useId` et non un compteur : deux cartes rendues cote a cote doivent porter
  // des identifiants distincts, y compris lors d'un rendu concurrent.
  const identifiantTitre = useId();

  if (titre === undefined) {
    return (
      <div className="ex-carte" {...reste}>
        {children}
      </div>
    );
  }

  const Titre = niveauTitre;
  return (
    <section className="ex-carte" aria-labelledby={identifiantTitre} {...reste}>
      <Titre className="ex-carte__titre" id={identifiantTitre}>
        {titre}
      </Titre>
      {children}
    </section>
  );
}
