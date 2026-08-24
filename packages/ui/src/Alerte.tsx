/**
 * Alerte — le retour systeme le plus employe du projet. LOT 4, `T11`.
 *
 * POURQUOI CELUI-LA, ET POURQUOI MAINTENANT
 *
 *   Le backlog `US007` nomme six familles : « boutons, menus, **alertes**,
 *   loaders, etats vides et notifications ». `T11` arrive apres les ecrans, et
 *   c'est delibere : les composants sont CONSOLIDES a partir de ce que `T3` a
 *   `T10` ont reellement eu besoin.
 *
 *   **La mesure a designe celui-ci.** `className="app-message"` apparait **onze
 *   fois** dans le frontend -- de loin le motif le plus repete -- avec a chaque
 *   fois le meme trio : un ton, un role, un texte. Onze exemplaires d'une meme
 *   regle divergent, et deux l'avaient deja fait : `T10` a trouve deux ecrans qui
 *   disaient la meme chose autrement.
 *
 * IL COUVRE TROIS FAMILLES DU BACKLOG, ET LE DIRE VAUT MIEUX QUE D'EN INVENTER TROIS
 *
 *   **alertes**, **loaders** et **etats vides** ne se distinguent pas par leur
 *   structure : ce sont tous un message avec un ton et un role. Ils se
 *   distinguent par le `role` ARIA, qui est precisement l'information utile :
 *
 *     `alert`   interrompt la lecture -- une erreur le merite
 *     `status`  n'interrompt pas -- un chargement, un etat vide
 *     aucun     un texte informatif que rien ne rend urgent
 *
 *   Livrer trois composants dont deux ne differeraient que par une constante
 *   serait la « surface sans contrepartie » que `DEC-456` refuse, et un lecteur
 *   aurait trois endroits a lire pour comprendre une seule regle.
 *
 * LE TON NE PORTE JAMAIS L'INFORMATION SEUL — WCAG 1.4.1, cahier §14.2
 *
 *   Le texte est **obligatoire dans le type**, exactement comme pour `Badge`. Une
 *   alerte qui ne serait que rouge est incomprehensible pour une personne
 *   daltonienne comme pour un lecteur d'ecran, et le ton n'est qu'un renfort.
 *
 * `aria-live` N'EST PAS AJOUTE, ET C'EST MESURE
 *
 *   `role="alert"` implique `aria-live="assertive"`, `role="status"` implique
 *   `aria-live="polite"` : les deux sont dans la specification ARIA. Les ecrire
 *   en plus est redondant, et une redondance qui peut diverger est un defaut --
 *   c'est la lecon du selecteur d'entite de `T8`, ou `aria-expanded` aurait
 *   double l'etat que `<details>` porte deja.
 *
 * L'ELEMENT EST UN `<p>`, ET LE ROLE NE LE CHANGE PAS
 *
 *   Un message est un paragraphe. Poser `role="alert"` sur un `<div>` marcherait
 *   aussi, mais un `<p>` reste lisible sans CSS ni ARIA -- c'est le principe de
 *   degradation qui a fait choisir `<details>` en `T5` et de vrais `<a>` en `T8`.
 */
import type { HTMLAttributes, ReactNode } from 'react';

/** Les tons d'alerte. `neutre` par defaut. */
export type TonAlerte = 'neutre' | 'succes' | 'erreur' | 'avertissement';

/**
 * L'urgence, qui determine le `role` ARIA.
 *
 * `aucune` ne pose AUCUN role : un texte informatif qui s'annoncerait a chaque
 * rendu serait du bruit, et le §14.2 ne demande pas d'annoncer ce que
 * l'utilisateur vient de provoquer lui-meme.
 */
export type UrgenceAlerte = 'alerte' | 'information' | 'aucune';

const ROLES: Record<UrgenceAlerte, string | undefined> = {
  alerte: 'alert',
  information: 'status',
  aucune: undefined,
};

export interface ProprietesAlerte extends Omit<
  HTMLAttributes<HTMLParagraphElement>,
  'className' | 'role'
> {
  /** Le texte. Obligatoire : voir l'en-tete, WCAG 1.4.1. */
  readonly children: ReactNode;
  /** `neutre` par defaut. */
  readonly ton?: TonAlerte;
  /** `aucune` par defaut : on n'annonce pas ce qui n'a rien d'urgent. */
  readonly urgence?: UrgenceAlerte;
}

export function Alerte({
  children,
  ton = 'neutre',
  urgence = 'aucune',
  ...reste
}: ProprietesAlerte): ReactNode {
  const role = ROLES[urgence];
  return (
    <p className="ex-alerte" data-ton={ton} {...(role === undefined ? {} : { role })} {...reste}>
      {children}
    </p>
  );
}
