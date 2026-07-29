/**
 * Page de statut de la plateforme.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002. Element 2 de la demonstration
 * attendue du LOT 1 par la roadmap : « page web de statut ».
 *
 * FONDEMENT
 *   cahier §18.7   les deux endpoints consommes, `ready` et `version` ;
 *   cahier §17.2   « apres perte de connexion sur une page deja chargee,
 *                  l'utilisateur voit un etat explicite » ;
 *   cahier §17.4   possibilite de reessayer, identifiant de correlation
 *                  copiable, aucun ecran blanc silencieux ;
 *   cahier §14.2   information jamais portee uniquement par la couleur, focus
 *                  visible, navigation au clavier ;
 *   fiche §6       trois etats a eprouver : chargement, erreur, hors connexion.
 *
 * CE QUE CETTE PAGE N'EST PAS
 *   Ce n'est pas un ecran metier, et ce n'est pas un tableau de bord complet.
 *   Le LOT 4 possede la navigation et les ecrans ; ici il n'y a ni donnee de
 *   collaborateur, ni authentification, ni design system — `packages/ui` est
 *   vide jusqu'a `T10` et la charte graphique releve de `DEP-006`. La mise en
 *   forme est donc volontairement neutre : aucune couleur de marque inventee.
 *
 * CE QU'ELLE NE PEUT PAS MONTRER, ET LE DIT
 *   `/health/ready` sonde TROIS dependances : PostgreSQL, Redis et MinIO. Le
 *   worker, Mailpit et Caddy ne sont pas sondes par l'API. La page les nomme
 *   explicitement plutot que de laisser croire qu'elle couvre les huit services
 *   de la stack.
 */
import { useCallback, useEffect, useState } from 'react';
import type { JSX } from 'react';

import { ErreurSante, lireEtatServices, lireVersion } from '../api/sante';
import type { EtatServices, StatutDependance, Version } from '../api/sante';

/** Services de la stack que l'API ne sonde pas, et qui ne peuvent donc pas figurer. */
const NON_SONDES = ['le worker Dramatiq', 'Mailpit', 'Caddy'] as const;

type Vue =
  | { readonly nom: 'chargement' }
  | {
      readonly nom: 'charge';
      readonly services: EtatServices;
      readonly version: Version;
      readonly correlation: string | null;
    }
  | { readonly nom: 'erreur'; readonly message: string; readonly correlation: string | null };

type EtatCopie = 'inactif' | 'faite' | 'impossible';

export function PageStatut(): JSX.Element {
  const [vue, setVue] = useState<Vue>({ nom: 'chargement' });
  const [tentative, setTentative] = useState(0);
  const [enLigne, setEnLigne] = useState<boolean>(() => navigator.onLine);
  const [copie, setCopie] = useState<EtatCopie>('inactif');

  // Perte et retour de connexion sur une page deja chargee (cahier §17.2).
  useEffect(() => {
    const passerEnLigne = (): void => {
      setEnLigne(true);
      // L'etat de chargement est pose ICI, dans le gestionnaire, et non dans
      // l'effet d'interrogation : un `setState` synchrone dans un corps
      // d'effet declenche un rendu en cascade, et `react-hooks` le refuse a
      // juste titre. Ce que l'effet affichait etait devenu obsolete a la
      // coupure ; c'est l'evenement qui le sait, pas l'effet.
      setVue({ nom: 'chargement' });
      setCopie('inactif');
    };
    const passerHorsLigne = (): void => {
      setEnLigne(false);
    };
    window.addEventListener('online', passerEnLigne);
    window.addEventListener('offline', passerHorsLigne);
    return () => {
      window.removeEventListener('online', passerEnLigne);
      window.removeEventListener('offline', passerHorsLigne);
    };
  }, []);

  useEffect(() => {
    // Hors connexion, interroger l'API ne produirait qu'une erreur de transport
    // indistinguable d'une panne serveur. L'etat affiche doit dire la verite.
    if (!enLigne) {
      return;
    }

    // Aucun `setState` synchrone ici : l'etat initial du composant est deja
    // `chargement`, et les deux seuls autres declencheurs de cet effet — le
    // bouton de nouvelle tentative et le retour du reseau — posent eux-memes
    // l'etat de chargement dans leur gestionnaire.
    let annule = false;

    void (async () => {
      try {
        // Les deux endpoints sont interroges en parallele : ils sont
        // independants, et la page n'a rien a afficher tant qu'il manque l'un
        // des deux.
        const [reponseServices, reponseVersion] = await Promise.all([
          lireEtatServices(),
          lireVersion(),
        ]);
        if (annule) {
          return;
        }
        setVue({
          nom: 'charge',
          services: reponseServices.charge,
          version: reponseVersion.charge,
          correlation: reponseServices.correlation,
        });
      } catch (cause) {
        if (annule) {
          return;
        }
        const echec =
          cause instanceof ErreurSante
            ? cause
            : new ErreurSante('erreur inattendue du navigateur', null);
        setVue({ nom: 'erreur', message: echec.message, correlation: echec.correlation });
      }
    })();

    return () => {
      annule = true;
    };
  }, [tentative, enLigne]);

  const reessayer = useCallback((): void => {
    setVue({ nom: 'chargement' });
    setCopie('inactif');
    setTentative((precedente) => precedente + 1);
  }, []);

  const copier = useCallback(async (texte: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(texte);
      setCopie('faite');
    } catch {
      // Le presse-papiers peut etre refuse par le navigateur. L'identifiant
      // reste selectionnable a la main : la copie n'est jamais le seul moyen.
      setCopie('impossible');
    }
  }, []);

  return (
    <main className="bloc">
      <h1>État de la plateforme</h1>
      <p className="sous-titre">
        eXalt Onboarding Digital — socle technique du LOT 1. Cette page lit l&rsquo;état réel de
        l&rsquo;API et de ses dépendances. Elle ne contient aucune donnée métier.
      </p>

      <div aria-live="polite" aria-busy={vue.nom === 'chargement'}>
        {!enLigne ? (
          <VueHorsConnexion />
        ) : vue.nom === 'chargement' ? (
          <VueChargement />
        ) : vue.nom === 'erreur' ? (
          <VueErreur message={vue.message} onReessayer={reessayer} />
        ) : (
          <VueCharge services={vue.services} version={vue.version} onReessayer={reessayer} />
        )}
      </div>

      {/* `charge` comme `erreur` portent une correlation : le narrowing suffit. */}
      {vue.nom !== 'chargement' && enLigne ? (
        <Correlation identifiant={vue.correlation} etatCopie={copie} onCopier={copier} />
      ) : null}

      <section className="note">
        <h2>Ce que cette page ne couvre pas</h2>
        <p>
          L&rsquo;API sonde trois dépendances. {phraseNonSondes()} ne sont pas sondés par{' '}
          <code>/health/ready</code> et n&rsquo;apparaissent donc pas ci-dessus : leur état se lit
          avec <code>make stack-check</code>.
        </p>
      </section>
    </main>
  );
}

// `Intl.ListFormat` plutot qu'un assemblage a la main : pas d'indexation a
// borner, et la conjonction reste correcte si la liste change de taille.
const ENUMERATION_FR = new Intl.ListFormat('fr', { style: 'long', type: 'conjunction' });

function phraseNonSondes(): string {
  // La majuscule initiale n'est pas cosmetique : cette enumeration ouvre une
  // phrase, apres un point. Constate en `T6` en lisant la page RENDUE dans un
  // navigateur — « L'API sonde trois dependances. le worker Dramatiq... ». Le
  // test de `T5` cherchait `toContain('worker Dramatiq')`, ce qui passe quelle
  // que soit la grammaire : un test insensible au defaut ne le trouve jamais.
  const liste = ENUMERATION_FR.format(NON_SONDES);
  return liste.charAt(0).toUpperCase() + liste.slice(1);
}

function VueChargement(): JSX.Element {
  return (
    <p className="etat-global" role="status">
      <span aria-hidden="true">◌</span> Interrogation de l&rsquo;API…
    </p>
  );
}

function VueHorsConnexion(): JSX.Element {
  return (
    <section>
      <p className="etat-global etat-global--ko" role="status">
        <span aria-hidden="true">▲</span> Vous êtes hors connexion
      </p>
      <p>
        Le navigateur signale une absence de réseau. L&rsquo;état affiché avant la coupure
        n&rsquo;est plus fiable et n&rsquo;est donc plus montré. Aucune action n&rsquo;a été
        enregistrée. L&rsquo;interrogation reprendra d&rsquo;elle-même au retour du réseau.
      </p>
    </section>
  );
}

function VueErreur({
  message,
  onReessayer,
}: {
  readonly message: string;
  readonly onReessayer: () => void;
}): JSX.Element {
  return (
    <section>
      <p className="etat-global etat-global--ko" role="alert">
        <span aria-hidden="true">▲</span> L&rsquo;état de la plateforme n&rsquo;a pas pu être lu
      </p>
      <p>
        Motif rapporté : <strong>{message}</strong>.
      </p>
      <button type="button" className="action" onClick={onReessayer}>
        Réessayer
      </button>
    </section>
  );
}

function VueCharge({
  services,
  version,
  onReessayer,
}: {
  readonly services: EtatServices;
  readonly version: Version;
  readonly onReessayer: () => void;
}): JSX.Element {
  const pret = services.statut === 'pret';
  return (
    <section>
      <p
        className={pret ? 'etat-global etat-global--ok' : 'etat-global etat-global--ko'}
        role="status"
      >
        <span aria-hidden="true">{pret ? '●' : '▲'}</span>{' '}
        {pret ? 'Plateforme prête' : 'Plateforme dégradée'}
      </p>

      <table>
        <caption>Dépendances sondées par l&rsquo;API</caption>
        <thead>
          <tr>
            <th scope="col">Dépendance</th>
            <th scope="col">État</th>
            <th scope="col">Latence</th>
            <th scope="col">Motif</th>
          </tr>
        </thead>
        <tbody>
          {services.dependances.map((dependance) => (
            <tr key={dependance.nom}>
              <th scope="row">{dependance.nom}</th>
              <td>
                <Pastille statut={dependance.statut} />
              </td>
              <td>{dependance.duree_ms} ms</td>
              <td>{dependance.motif ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Version déployée</h2>
      <dl>
        <dt>Version</dt>
        <dd>{version.version}</dd>
        <dt>Révision</dt>
        <dd>{version.revision}</dd>
        <dt>Environnement</dt>
        <dd>{version.environnement}</dd>
      </dl>

      <button type="button" className="action" onClick={onReessayer}>
        Rafraîchir
      </button>
    </section>
  );
}

function Pastille({ statut }: { readonly statut: StatutDependance }): JSX.Element {
  const disponible = statut === 'disponible';
  // L'information n'est JAMAIS portee par la seule couleur (cahier §14.2) :
  // le libelle est explicite et le symbole differe par sa FORME, pas seulement
  // par sa teinte.
  return (
    <span className={disponible ? 'etat etat--ok' : 'etat etat--ko'}>
      <span aria-hidden="true">{disponible ? '●' : '▲'}</span> {statut}
    </span>
  );
}

function Correlation({
  identifiant,
  etatCopie,
  onCopier,
}: {
  readonly identifiant: string | null;
  readonly etatCopie: EtatCopie;
  readonly onCopier: (texte: string) => Promise<void>;
}): JSX.Element | null {
  if (identifiant === null) {
    return null;
  }
  return (
    <section className="note">
      <h2>Identifiant de corrélation</h2>
      <p>
        À citer dans tout signalement : il relie cette réponse aux journaux de l&rsquo;API.
        {/* Selectionnable a la main : la copie automatique n'est pas le seul moyen. */}
      </p>
      <p>
        <code>{identifiant}</code>{' '}
        <button
          type="button"
          className="action action--discrete"
          onClick={() => {
            void onCopier(identifiant);
          }}
        >
          Copier
        </button>
      </p>
      <p aria-live="polite">
        {etatCopie === 'faite'
          ? 'Identifiant copié dans le presse-papiers.'
          : etatCopie === 'impossible'
            ? 'Copie refusée par le navigateur : sélectionnez l’identifiant à la main.'
            : ''}
      </p>
    </section>
  );
}
