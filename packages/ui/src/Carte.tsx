/**
 * Carte — composant de base du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.2, 13.3, 14.
 *
 * « CARTES ARRONDIES, OMBRES DOUCES » — cahier 13.2. **L'OMBRE A DISPARU EN
 * `E1`** : la charte v2 est « flat » (1.1), `--ombre-douce` vaut `none`, et la
 * separation se fait par `1px solid var(--trait)`. Ecart avec le cahier 13.2
 * consigne a `DEC-682`.
 *
 * LA VARIANTE `interactive` — charte 5, `E3`
 *
 *   « Variante interactive : survol bordure bleue. » Elle ne change QUE
 *   l'apparence au survol et au focus : elle ne rend pas la carte cliquable et
 *   ne lui donne aucun role. Une carte qui PARAITRAIT actionnable sans l'etre
 *   serait pire que pas d'indice du tout — c'est a l'appelant de poser le lien
 *   ou le bouton reel a l'interieur, et le `:focus-within` de la feuille fait
 *   alors remonter le signal de focus jusqu'a la bordure.
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

/** `statique` par defaut. `interactive` n'ajoute qu'un signal visuel. */
export type VarianteCarte = 'statique' | 'interactive';

export interface ProprietesCarte extends Omit<HTMLAttributes<HTMLElement>, 'className' | 'title'> {
  readonly children: ReactNode;
  /** `statique` par defaut. Voir l'en-tete : ne rend PAS la carte cliquable. */
  readonly variante?: VarianteCarte;
  /**
   * Facultatif. S'il est fourni, la carte devient une region nommee.
   *
   * `ReactNode` et non `string` depuis le chantier front S13 (`DEC-673`) :
   * un titre peut porter un accent interne (ex. `.ex-carte__titre-chiffre`
   * sur un compteur) sans que le nom accessible change — `aria-labelledby`
   * calcule le nom a partir du CONTENU TEXTE de l'element reference, quel
   * que soit le balisage imbrique.
   */
  readonly titre?: ReactNode;
  /** `h2` par defaut. Sans effet si `titre` est absent. */
  readonly niveauTitre?: NiveauTitre;
}

export function Carte({
  children,
  titre,
  niveauTitre = 'h2',
  variante = 'statique',
  ...reste
}: ProprietesCarte): ReactNode {
  // `useId` et non un compteur : deux cartes rendues cote a cote doivent porter
  // des identifiants distincts, y compris lors d'un rendu concurrent.
  const identifiantTitre = useId();

  if (titre === undefined) {
    return (
      <div className="ex-carte" data-variante={variante} {...reste}>
        {children}
      </div>
    );
  }

  const Titre = niveauTitre;
  return (
    <section
      className="ex-carte"
      data-variante={variante}
      aria-labelledby={identifiantTitre}
      {...reste}
    >
      <Titre className="ex-carte__titre" id={identifiantTitre}>
        {titre}
      </Titre>
      {children}
    </section>
  );
}
