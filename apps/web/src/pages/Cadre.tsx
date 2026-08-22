/**
 * Cadre commun aux huit ecrans — LOT 3, sous-etape `T11`.
 *
 * POURQUOI UN CADRE PLUTOT QUE HUIT EN-TETES RECOPIES
 *
 *   Huit copies d'un en-tete divergent, et le jour ou l'une oublie le `<main>` le
 *   lecteur d'ecran perd son point de repere sans que rien n'echoue. Le cadre
 *   porte donc les reperes une fois : `<header>`, `<main>`, un seul `<h1>`.
 *
 * LE TITRE EST UN `<h1>`, ET IL EST UNIQUE PAR PAGE
 *
 *   `jsx-a11y` ne verifie pas l'unicite d'un `<h1>` -- c'est une regle de document,
 *   pas de JSX -- donc c'est le cadre qui la garantit par construction : les pages
 *   passent un `titre`, elles n'ecrivent pas de balise de titre.
 *
 * AUCUNE COULEUR ECRITE ICI
 *
 *   Critere de la sous-etape : « aucune couleur hors des jetons de
 *   `packages/ui` ». Toutes les valeurs viennent de `jetons.css` par variable
 *   CSS, et un controle relit les feuilles pour l'exiger.
 */
import type { JSX, ReactNode } from 'react';

export interface ProprietesCadre {
  readonly titre: string;
  /** Texte d'introduction, rendu sous le titre. Facultatif. */
  readonly introduction?: string;
  readonly children: ReactNode;
}

export function Cadre({ titre, introduction, children }: ProprietesCadre): JSX.Element {
  return (
    <div className="auth-cadre">
      <header className="auth-entete">
        <p className="auth-marque">eXalt Onboarding</p>
      </header>
      <main className="auth-principal">
        <h1 className="auth-titre">{titre}</h1>
        {introduction === undefined ? null : <p className="auth-introduction">{introduction}</p>}
        {children}
      </main>
    </div>
  );
}
