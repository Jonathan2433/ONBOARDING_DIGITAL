/**
 * Notification — le retour TEMPORAIRE que le §17.4 exige. LOT 4, `T11`.
 *
 * ELLE MANQUAIT, ET C'EST LA SEULE DES SIX FAMILLES QUI N'EXISTAIT NULLE PART
 *
 *   Le §17.4 du cahier liste « ... messages de champs ; **notifications** ;
 *   possibilite de reessayer ... », et le backlog `US007` la nomme aussi. Les
 *   cinq autres familles etaient deja dans les ecrans sous une forme ou une
 *   autre ; celle-la, non.
 *
 * CE QUI LA DISTINGUE D'UNE `Alerte`, ET CE N'EST PAS COSMETIQUE
 *
 *   Une alerte decrit **l'etat de l'ecran** : elle reste tant que l'etat dure.
 *   Une notification decrit **le resultat d'une action** : elle apparait apres le
 *   geste, et elle n'a plus de sens ensuite.
 *
 *   Consequence sur le balisage, et c'est ce qui compte : le conteneur d'une
 *   notification doit etre **present avant** que son contenu arrive. Un
 *   `aria-live` ajoute au DOM en meme temps que son texte **n'est pas annonce de
 *   facon fiable** -- les lecteurs d'ecran observent les mutations d'une region
 *   deja connue. C'est pourquoi ce composant rend **toujours** son conteneur,
 *   meme vide.
 *
 *   Une `Alerte` n'a pas ce probleme : elle apparait avec son etat, et son role
 *   est lu au moment ou elle entre.
 *
 * ELLE N'EST JAMAIS `alert`, ET C'EST UN CHOIX
 *
 *   `role="status"` seulement. Une notification de succes qui interromprait la
 *   lecture serait plus genante qu'utile ; et une notification d'echec qui doit
 *   interrompre n'est pas une notification, c'est une alerte -- elle decrit alors
 *   un etat, pas un resultat.
 *
 * AUCUNE DISPARITION AUTOMATIQUE, ET LE MOTIF EST D'ACCESSIBILITE
 *
 *   Un message qui s'effacerait apres quelques secondes est inaccessible a qui
 *   lit lentement, et WCAG 2.2.1 demande de pouvoir prolonger toute limite de
 *   temps. Le §17.3 parle de « notifications **temporaires** » -- temporaire veut
 *   dire liee a l'action, pas minutee. C'est donc l'appelant qui decide quand
 *   elle disparait, et il le fait en changeant son etat.
 */
import type { HTMLAttributes, ReactNode } from 'react';

/** Les tons de notification. `neutre` par defaut. */
export type TonNotification = 'neutre' | 'succes' | 'echec';

export interface ProprietesNotification extends Omit<
  HTMLAttributes<HTMLParagraphElement>,
  'className' | 'role' | 'children'
> {
  /**
   * Le message, ou la chaine vide quand il n'y a rien a annoncer.
   *
   * **UNE CHAINE ET NON `ReactNode`**, contrairement a `Alerte` : une region
   * `aria-live` annonce du TEXTE, et y placer des elements rendrait l'annonce
   * imprevisible. Et la chaine vide est une valeur legitime -- c'est l'etat
   * « rien a annoncer », qui doit garder le conteneur present.
   */
  readonly message: string;
  /** `neutre` par defaut. */
  readonly ton?: TonNotification;
}

export function Notification({
  message,
  ton = 'neutre',
  ...reste
}: ProprietesNotification): ReactNode {
  return (
    //  **LE CONTENEUR EST TOUJOURS RENDU**, meme quand `message` est vide : voir
    //  l'en-tete. Le rendre conditionnellement casserait l'annonce.
    <p
      className="ex-notification"
      data-ton={ton}
      data-vide={message === '' ? 'oui' : 'non'}
      role="status"
      {...reste}
    >
      {message}
    </p>
  );
}
