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

/** Les tons de `T10`. `neutre` par defaut. */
export type TonBadge = 'neutre' | 'ok' | 'ko' | 'marque';

export interface ProprietesBadge extends Omit<HTMLAttributes<HTMLSpanElement>, 'className'> {
  /** Le libelle. Obligatoire : voir l'en-tete, WCAG 1.4.1. */
  readonly children: ReactNode;
  /** `neutre` par defaut. */
  readonly ton?: TonBadge;
}

export function Badge({ children, ton = 'neutre', ...reste }: ProprietesBadge): ReactNode {
  return (
    <span className="ex-badge" data-ton={ton} {...reste}>
      {children}
    </span>
  );
}
