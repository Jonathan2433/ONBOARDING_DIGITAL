/**
 * Frontiere d'erreur React.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * FONDEMENT — cahier des charges §17.4 : « error boundary React » et
 * « aucun ecran blanc silencieux ». Sans cette frontiere, une exception levee
 * pendant le rendu demonte l'arbre et laisse une page vide : l'utilisateur ne
 * distingue plus une panne d'un chargement interminable.
 *
 * C'est une classe et non une fonction : React n'expose `componentDidCatch` et
 * `getDerivedStateFromError` qu'aux composants de classe. Aucune bibliotheque
 * tierce n'est ajoutee pour l'eviter — `DEC-456` n'installe que ce qui sert.
 */
import { Component } from 'react';
import type { ErrorInfo, JSX, ReactNode } from 'react';

interface Proprietes {
  readonly children: ReactNode;
}

interface Etat {
  readonly nomErreur: string | null;
}

export class FrontiereErreur extends Component<Proprietes, Etat> {
  constructor(proprietes: Proprietes) {
    super(proprietes);
    this.state = { nomErreur: null };
  }

  static getDerivedStateFromError(erreur: unknown): Etat {
    const nom = erreur instanceof Error ? erreur.name : 'Error';
    return { nomErreur: nom };
  }

  override componentDidCatch(erreur: unknown, informations: ErrorInfo): void {
    // Le TYPE de l'exception et la pile de composants, jamais le message.
    // Meme discipline que `DEC-469` cote serveur : un message d'exception peut
    // transporter une valeur, la pile de composants non.
    const nom = erreur instanceof Error ? erreur.name : 'Error';
    console.error('rendu interrompu', nom, informations.componentStack);
  }

  override render(): ReactNode {
    const { nomErreur } = this.state;
    if (nomErreur === null) {
      return this.props.children;
    }
    return this.replier(nomErreur);
  }

  private replier(nomErreur: string): JSX.Element {
    return (
      <main className="bloc">
        <h1>L&rsquo;affichage s&rsquo;est interrompu</h1>
        <p role="alert">
          Une erreur inattendue a interrompu le rendu de la page. Le type de l&rsquo;erreur est{' '}
          <code>{nomErreur}</code>.
        </p>
        <p>
          Rien n&rsquo;a ete enregistre. Recharger la page est sans risque : cette page ne fait que
          lire l&rsquo;etat de la plateforme.
        </p>
        <button
          type="button"
          className="action"
          onClick={() => {
            window.location.reload();
          }}
        >
          Recharger la page
        </button>
      </main>
    );
  }
}
