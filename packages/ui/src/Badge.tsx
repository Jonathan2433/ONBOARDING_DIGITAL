/**
 * Badge — composant de base du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.3, 14.
 *
 * LE TEXTE PORTE L'INFORMATION, JAMAIS LA COULEUR SEULE
 *
 *   WCAG 2.2 critere 1.4.1 : « la couleur n'est pas utilisee comme le seul moyen
 *   visuel de transmettre une information ». Un badge vert qui signifierait
 *   « operationnel » sans le dire enfreindrait ce critere — et serait
 *   incomprehensible pour une personne daltonienne comme pour un lecteur d'ecran.
 *
 *   Le contenu textuel est donc OBLIGATOIRE dans le type, et le ton n'est qu'un
 *   renfort visuel. `composants.test.tsx` verifie que le texte est bien rendu,
 *   pour chaque ton.
 *
 *   C'est aussi la lecon que la page de statut de `T5` avait deja appliquee : ses
 *   cinq etats sont nommes en mots, pas seulement colores.
 */

import type { HTMLAttributes, ReactNode } from 'react';

/**
 * Les six tons de la charte 5 (`E3`, `DEC-682`), nommes par
 * ce qu'ils DISENT et non par une couleur : `mission`, `intercontrat`,
 * `enrichissement`, `booster`, `annule`, `info`. Chacun reutilise un couple
 * deja prouve AA par `jetons.test.ts` — aucune couleur nouvelle sauf `annule`,
 * dont le texte sourd a du etre mesure et ajoute (`TEINTES.grisSourd`, 4,55:1).
 *
 * `E6` (`DEC-684`) a retire les quatre tons historiques de `T10` (`neutre`,
 * `ok`, `ko`, `marque`) apres avoir traduit chaque emploi selon ce que son texte
 * DIT. Le defaut devient `info` : un badge sans intention metier plus precise ne
 * doit pas inventer une mission, un intercontrat ou une annulation.
 */
export type TonBadge =
  'mission' | 'intercontrat' | 'enrichissement' | 'booster' | 'annule' | 'info';

export interface ProprietesBadge extends Omit<HTMLAttributes<HTMLSpanElement>, 'className'> {
  /** Le libelle. Obligatoire : voir l'en-tete, WCAG 1.4.1. */
  readonly children: ReactNode;
  /** `info` par defaut. */
  readonly ton?: TonBadge;
}

export function Badge({ children, ton = 'info', ...reste }: ProprietesBadge): ReactNode {
  return (
    <span className="ex-badge" data-ton={ton} {...reste}>
      {children}
    </span>
  );
}
