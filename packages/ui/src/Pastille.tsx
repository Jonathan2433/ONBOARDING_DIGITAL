/**
 * Pastille — le surtitre de rubrique de la charte 5.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-681`).
 *
 * CE QU'ELLE EST, ET CE QU'ELLE N'EST PAS
 *
 *   « Surtitre de rubrique : fond jaune, texte titre, 13px bold, padding 6x16.
 *   Une seule par vue, au-dessus du h1. » Elle NOMME la rubrique ou l'on se
 *   trouve — « Presentation de l'entite », « Trombinoscope » — juste avant le
 *   titre de la page.
 *
 *   **CE N'EST PAS UN TITRE, ET ELLE N'EN PREND PAS LE ROLE.** Lui donner un
 *   niveau de titre insererait un `<h1>`/`<h2>` de plus avant le vrai titre de
 *   page et casserait la hierarchie (WCAG 1.3.1). C'est un paragraphe : lu dans
 *   l'ordre, juste avant le `<h1>`, ce qui est exactement sa place a l'ecran.
 *
 *   **« UNE SEULE PAR VUE » EST UNE REGLE D'EMPLOI, PAS UNE REGLE DE COMPOSANT.**
 *   Rien ici ne peut l'imposer — un composant ne sait pas combien de fois il est
 *   rendu dans la page. L'ecrire ici plutot que de faire semblant de la tenir.
 *
 * LE COUPLE EST DEJA MESURE
 *
 *   Jaune de marque sur texte `--titre` : 7,7:1, le couple `MARQUE.jaune` prouve
 *   par `jetons.test.ts`. Le texte est le LITTERAL apparie, jamais `var(--titre)`
 *   — le jaune ne bascule pas avec le theme, donc son texte ne le doit pas non
 *   plus (voir l'en-tete de `jetons.ts`).
 */

import type { HTMLAttributes, ReactNode } from 'react';

export interface ProprietesPastille extends Omit<
  HTMLAttributes<HTMLParagraphElement>,
  'className'
> {
  /** Le nom de la rubrique. Obligatoire : une pastille vide n'informe de rien. */
  readonly children: ReactNode;
}

export function Pastille({ children, ...reste }: ProprietesPastille): ReactNode {
  return (
    <p className="ex-pastille" {...reste}>
      {children}
    </p>
  );
}
