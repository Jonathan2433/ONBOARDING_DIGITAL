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
 * Les tons.
 *
 * **LES SIX PREMIERS SONT CEUX DE LA CHARTE 5** (`E3`, `DEC-681`), nommes par
 * ce qu'ils DISENT et non par une couleur : `mission`, `intercontrat`,
 * `enrichissement`, `booster`, `annule`, `info`. Chacun reutilise un couple
 * deja prouve AA par `jetons.test.ts` — aucune couleur nouvelle sauf `annule`,
 * dont le texte sourd a du etre mesure et ajoute (`TEINTES.grisSourd`, 4,55:1).
 *
 * **LES QUATRE SUIVANTS SONT CEUX DE `T10`, ET ILS SURVIVENT A DESSEIN.** Vingt-
 * deux `<Badge>` vivent dans `apps/web` — onze en `marque`, deux en `ko`, un en
 * `neutre`, huit au defaut — et leur traduction vers le vocabulaire de la charte
 * depend de ce que chaque ecran veut DIRE : le `marque` du trombinoscope porte
 * un nom de cercle, pas une mission. Les retirer ici ferait echouer la
 * compilation de huit ecrans et forcerait a deviner ces traductions dans la
 * meme etape que la construction des composants. `E5` les migre un par un,
 * `E6` retire ce qui reste. Une etape a la fois.
 */
export type TonBadge =
  | 'mission'
  | 'intercontrat'
  | 'enrichissement'
  | 'booster'
  | 'annule'
  | 'info'
  | 'neutre'
  | 'ok'
  | 'ko'
  | 'marque';

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
