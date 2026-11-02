/**
 * Progression — l'avancement d'un parcours.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-682`), charte 5 et 6.7.
 *
 * `role="progressbar"` ET SES TROIS VALEURS, JAMAIS DEUX
 *
 *   `aria-valuenow` seul ne dit rien : un lecteur d'ecran a besoin des bornes
 *   pour en tirer un pourcentage. `aria-valuemin` et `aria-valuemax` sont donc
 *   toujours poses. Et la barre porte un NOM — sans lui, elle s'annonce
 *   « barre de progression » sans dire de quoi (WCAG 1.3.1, 4.1.2).
 *
 * LE POURCENTAGE N'EST PAS CALCULE ICI, ET C'EST VOLONTAIRE
 *
 *   L'API sert un couple (taches obligatoires totales / terminees) et jamais un
 *   pourcentage stocke — c'est la discipline posee par `Progression` au LOT 7
 *   `T7`. Ce composant prend donc le meme couple et le rend tel quel aux
 *   technologies d'assistance : « 3 sur 7 » est plus utile que « 43 % », et la
 *   largeur visuelle reste le seul endroit ou un pourcentage apparait.
 *
 *   `aria-valuetext` porte la forme lisible. Sans lui, « 3 » sur une echelle de
 *   0 a 7 s'annonce « 43 % » — exact mais moins parlant que « 3 sur 7 ».
 *
 * UN APLAT, JAMAIS UN DEGRADE, ET UN BLEU QUI BASCULE
 *
 *   La charte 5 ecrit « remplissage aplat bleu (pas de degrade bleu->rose) » :
 *   le degrade de la V1 est interdit par la charte 1.1 comme par `E1`.
 *
 *   **LE REMPLISSAGE CHANGE DE BLEU EN THEME SOMBRE.** Mesure du 02/11/2026 :
 *   `--marque-bleu` sur la piste `--fond-doux` rend 4,70:1 en clair mais
 *   **2,91:1** en sombre, sous les 3:1 qu'exige WCAG 1.4.11 pour une partie de
 *   graphique porteuse de sens. `--titre` y rend 7,44:1. Meme regle que l'anneau
 *   de focus et que le bouton discret.
 *
 *   **ET LA PISTE PORTE UNE BORDURE, pour une seconde raison mesuree** : en
 *   theme sombre `--fond-doux` et `--surface` valent la MEME couleur (#27272A),
 *   si bien qu'une piste posee sur une carte y serait invisible. La bordure
 *   `1px solid var(--trait)` est la separation que la charte 1.1 prescrit
 *   partout ailleurs ; elle rend la piste visible dans les deux themes.
 */

import { useId } from 'react';
import type { ReactNode } from 'react';

export interface ProprietesProgression {
  /** Ce qui est fait. Borne a `[0, total]`. */
  readonly faites: number;
  /** Le total. Zero est admis : un parcours peut n'avoir aucune tache. */
  readonly total: number;
  /** Le nom de la barre. Obligatoire : voir l'en-tete. */
  readonly libelle: string;
}

export function Progression({ faites, total, libelle }: ProprietesProgression): ReactNode {
  const identifiant = useId();

  //  BORNAGE EXPLICITE. Une valeur hors bornes — un decompte faux, un total
  //  remis a zero avant les taches — produirait une largeur negative ou
  //  superieure a 100 %, et un `aria-valuenow` incoherent. On borne plutot que
  //  de faire confiance a l'appelant.
  const maximum = Math.max(0, total);
  const valeur = Math.min(Math.max(0, faites), maximum);
  //  `total === 0` : zero sur zero n'est pas 0 %, c'est « rien a faire ». La
  //  barre est alors pleine, ce qui est la lecture utile — le parcours n'a
  //  aucune tache en attente.
  const part = maximum === 0 ? 1 : valeur / maximum;

  return (
    <div className="ex-progression">
      <span className="ex-progression__libelle" id={identifiant}>
        {libelle}
      </span>
      <div
        className="ex-progression__piste"
        role="progressbar"
        aria-labelledby={identifiant}
        aria-valuemin={0}
        aria-valuemax={maximum}
        aria-valuenow={valeur}
        aria-valuetext={`${valeur} sur ${maximum}`}
      >
        <div
          className="ex-progression__remplissage"
          style={{ inlineSize: `${(part * 100).toFixed(2)}%` }}
        />
      </div>
    </div>
  );
}
