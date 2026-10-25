/**
 * Onglets — composant de base du design system, sur primitive Radix.
 *
 * Chantier front hors lot, sous-etape S1 (`DEC-672`, 25/10/2026). Cahier des
 * charges 13.3, qui nomme explicitement Radix UI comme base des primitives
 * accessibles du design system.
 *
 * POURQUOI RADIX ICI, ET PAS UNE QUATRIEME COPIE A LA MAIN
 *
 *   Deux ecrans de ce depot refabriquent deja le meme motif ARIA
 *   `tablist`/`tab`/`tabpanel` a la main — `PageAdministration.tsx` (LOT 9
 *   `T14`, etendu au LOT 10 `T15`) et `PageEvenements.tsx` (LOT 8 `T9`) —
 *   chacun avec sa propre copie, et AUCUN des deux ne gere `ArrowLeft`/
 *   `ArrowRight` (mesure avant d'ecrire ce fichier). `@radix-ui/react-tabs`
 *   fournit cette navigation nativement, avec le focus « roving » standard des
 *   WAI-ARIA Authoring Practices, et pose lui-meme `role`, `aria-selected`,
 *   `aria-controls` et l'etat `data-state` — ce composant n'a donc RIEN de
 *   cela a reecrire, seulement le style.
 *
 *   La migration des deux ecrans existants est une sous-etape SEPAREE (S2) :
 *   ce fichier ne livre que la primitive et sa preuve isolee, jamais un ecran.
 *
 * ACTIVATION MANUELLE, PAS AUTOMATIQUE — ET CE N'EST PAS LE DEFAUT DE RADIX
 *
 *   Par defaut, Radix ACTIVE un onglet des que les fleches lui donnent le
 *   focus (mode « automatique » des WAI-ARIA Authoring Practices, adapte a un
 *   contenu leger). Ici, activer un onglet declenche le montage d'une section
 *   qui appelle sa propre route — exactement le cas que les APG nomment pour
 *   recommander le mode « manuel » : le focus se deplace librement au clavier,
 *   et seuls Entree/Espace (ou un clic) activent reellement l'onglet survole.
 *   Sans ce choix, parcourir les neuf onglets de `PageAdministration.tsx` a la
 *   fleche declencherait neuf appels reseau pour une seule intention de
 *   lecture.
 *
 * UN SEUL PANNEAU EST RENDU, PAS UN PAR ONGLET
 *
 *   Radix autorise un `Tabs.Content` par valeur possible, tous presents dans
 *   le DOM et bascules par l'attribut `hidden`. Les deux ecrans consommateurs
 *   montent un composant REACT DIFFERENT par onglet, et chacun declenche son
 *   propre appel reseau a l'affichage — les monter tous simultanement
 *   multiplierait les requetes pour un gain visuel nul, l'utilisateur n'en
 *   voyant qu'un a la fois. Ce composant ne recoit donc que le contenu de
 *   l'onglet ACTIF, dans un seul `Tabs.Content` : le contrat ARIA (role
 *   `tabpanel`, `aria-labelledby`) reste exact, Radix le posant sur
 *   l'element qu'il recoit, qu'il y en ait un ou neuf dans l'arbre a un
 *   instant donne.
 */

import type { ReactNode } from 'react';

import * as PrimitiveOnglets from '@radix-ui/react-tabs';

/** Un onglet : sa valeur (identifiant stable) et son libelle visible. */
export interface DefinitionDOnglet {
  readonly valeur: string;
  readonly libelle: string;
}

export interface ProprietesOnglets {
  /** Nom accessible de la liste d'onglets. WCAG 1.3.1 : jamais facultatif. */
  readonly libelleDeLaListe: string;
  readonly onglets: readonly DefinitionDOnglet[];
  readonly valeurActive: string;
  readonly onChangerDOnglet: (valeur: string) => void;
  /** Le contenu du SEUL onglet actif — voir l'en-tete. */
  readonly children: ReactNode;
}

export function Onglets({
  libelleDeLaListe,
  onglets,
  valeurActive,
  onChangerDOnglet,
  children,
}: ProprietesOnglets): ReactNode {
  return (
    <PrimitiveOnglets.Root
      activationMode="manual"
      className="ui-onglets"
      onValueChange={onChangerDOnglet}
      value={valeurActive}
    >
      <PrimitiveOnglets.List aria-label={libelleDeLaListe} className="ui-onglets__liste">
        {onglets.map((o) => (
          <PrimitiveOnglets.Trigger className="ui-onglets__onglet" key={o.valeur} value={o.valeur}>
            {o.libelle}
          </PrimitiveOnglets.Trigger>
        ))}
      </PrimitiveOnglets.List>
      <PrimitiveOnglets.Content className="ui-onglets__panneau" value={valeurActive}>
        {children}
      </PrimitiveOnglets.Content>
    </PrimitiveOnglets.Root>
  );
}
