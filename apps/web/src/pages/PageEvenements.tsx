/**
 * Les evenements a l'ecran — LOT 8, `T9`, story `MVP-L08-US003` (2/2).
 *
 * LE TEMOIN DE LA FICHE, MOT POUR MOT
 *
 *   « Onglets a venir/passes, badge annule, mobile et clavier. »
 *
 * LA FRONTIERE VIENT DE L'API, JAMAIS RECALCULEE ICI
 *
 *   `classement` est envoye a l'API a chaque appel ; c'est elle qui compare
 *   `ends_at` a un instant unique (`app/events/lecture.py`). Reclasser cote
 *   client exigerait une horloge et une regle dupliquees — §6.5, et la regle 5
 *   du projet : l'API est l'autorite finale.
 *
 * LES ONGLETS SONT DE VRAIS `<button>`, PAS UN COMPOSANT NOUVEAU
 *
 *   Aucune primitive d'onglets n'existe dans `packages/ui` — `index.ts` du
 *   paquet le dit explicitement : livrer un composant sans ecran qui l'emploie
 *   serait du code non eprouve. Le motif WAI-ARIA (`tablist`/`tab`/`tabpanel`)
 *   est pose ici, a la main, sur des `<button>` natifs : la reponse au clavier
 *   (Tab, Entree, Espace) est donc STRUCTURELLE, meme parti que
 *   `CarteRetournable` et `NavLink` ailleurs dans ce depot.
 *
 * LE CHANGEMENT D'ONGLET REINITIALISE LA PAGE
 *
 *   La page 2 des evenements passes n'a aucun sens pour les evenements a
 *   venir : changer d'onglet reclasse completement la population consultee.
 *
 * UN EVENEMENT ANNULE RESTE VISIBLE, AVEC UN BADGE — JAMAIS UNE COULEUR SEULE
 *
 *   Cahier §10.6 : « un evenement annule reste visible avec un badge "Annule" ».
 *   `Badge` exige un texte dans son type (WCAG 1.4.1) : aucune carte ne peut
 *   donc signaler une annulation par la seule couleur.
 *
 * LES DATES SE LISENT DANS LA CHAINE, JAMAIS PAR `Date`
 *
 *   Meme lecon que `PageProfil.tsx` : un accesseur local sur un `Date` construit
 *   depuis une chaine UTC peut rendre une heure ou un jour different de celui
 *   que l'API a servi. `dateComplete` est donc REPRISE d'ici plutot que
 *   recopiee (§7.27, deja le cas pour `PageAdministration.tsx` et
 *   `PageMonOnboarding.tsx`), et `heure` applique la meme methode : un segment
 *   lu a position fixe dans la chaine ISO.
 *
 * AUCUNE PAGE DE DETAIL N'EST CREEE ICI
 *
 *   Le diagramme du cahier §8.1 montre bien « Evenements --> Page evenement »,
 *   mais aucun document n'en donne le contenu ni la raison : chaque carte
 *   affiche deja titre, horaire, lieu et description. Construire un lien vers
 *   une adresse qu'aucune route ne sert serait exactement ce que `PageRubrique`
 *   evite depuis le LOT 4 — « un lien qui aboutit au fourre-tout 404 est
 *   atteignable et INUTILE ». `T10` (l'ecran de GESTION) aura besoin d'une
 *   cible propre pour editer ; la lecture n'en a pas besoin.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { lireLesEvenements } from '../api/evenements';
import { cheminGestionDesEvenementsALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { dateComplete } from './PageProfil';

import {
  CLASSEMENTS_D_EVENEMENTS,
  type ClassementEvenement,
  peutGererLesEvenements,
  type PageDesEvenements,
  TAILLE_PAR_DEFAUT,
} from '@onboarding/contracts';
import { Alerte, Badge } from '@onboarding/ui';

const TAILLE = TAILLE_PAR_DEFAUT;

const LIBELLES_DE_CLASSEMENT: Readonly<Record<ClassementEvenement, string>> = {
  a_venir: 'A venir',
  passes: 'Passes',
};

/** « 14:30 », lu a position fixe dans la chaine ISO — jamais par `Date`. */
function heure(iso: string): string {
  return iso.slice(11, 16);
}

/** « 12 octobre 2026, 08:00 - 09:30 », ou la forme etendue si les jours different. */
function plageDeLEvenement(commenceLe: string, finitLe: string): string {
  const memeJour = commenceLe.slice(0, 10) === finitLe.slice(0, 10);
  return memeJour
    ? `${dateComplete(commenceLe)}, ${heure(commenceLe)} - ${heure(finitLe)}`
    : `Du ${dateComplete(commenceLe)} ${heure(commenceLe)} au ${dateComplete(finitLe)} ${heure(finitLe)}`;
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'page'; readonly page: PageDesEvenements }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageEvenements(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const roles = permissions?.roles ?? null;
  //  **REFUS PAR DEFAUT, §20.1** — pas de lien pour une action que l'API
  //  refuserait. `T10` : la portee LOCALE reste resolue par l'API seule, ce
  //  predicat ne fait que ne pas PROPOSER un lien inutile.
  const peutGerer = roles !== null && peutGererLesEvenements(roles);
  const [classement, setClassement] = useState<ClassementEvenement>('a_venir');
  const [page, setPage] = useState(1);
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    const abandon = new AbortController();
    void lireLesEvenements(entite.code, classement, page, TAILLE, abandon.signal).then(
      (reponse) => {
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'page', page: reponse.corps }
            : { phase: 'erreur', statut: reponse.statut },
        );
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setEtat({ phase: 'erreur', statut: 0 });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code, classement, page]);

  const idDuPanneau = 'evenements-panneau';

  const onglets = (
    <div role="tablist" aria-label="Classement des evenements" className="evenements-onglets">
      {CLASSEMENTS_D_EVENEMENTS.map((valeur) => (
        <button
          key={valeur}
          type="button"
          role="tab"
          id={`evenements-onglet-${valeur}`}
          aria-selected={classement === valeur}
          aria-controls={idDuPanneau}
          className="evenements-onglet"
          data-selectionne={classement === valeur}
          onClick={() => {
            //  **LE CHANGEMENT D'ONGLET REINITIALISE LA PAGE** — voir l'en-tete.
            setClassement(valeur);
            setPage(1);
          }}
        >
          {LIBELLES_DE_CLASSEMENT[valeur]}
        </button>
      ))}
    </div>
  );

  if (etat.phase === 'chargement') {
    return (
      <div className="evenements">
        {onglets}
        <Alerte urgence="information">Chargement des evenements…</Alerte>
      </div>
    );
  }

  if (etat.phase === 'erreur') {
    return (
      <div className="evenements">
        {onglets}
        <Alerte ton="erreur" urgence="alerte">
          {etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter les evenements.'
            : "Les evenements n'ont pas pu etre charges. Cela ne dit rien de leur contenu : verifiez votre connexion, puis reessayez."}
        </Alerte>
      </div>
    );
  }

  const donnees = etat.page;

  return (
    <div className="evenements">
      {onglets}
      {peutGerer ? (
        <p>
          <Link className="app-lien" to={cheminGestionDesEvenementsALEcran(entite.code)}>
            Gerer les evenements
          </Link>
        </p>
      ) : null}
      <div
        role="tabpanel"
        id={idDuPanneau}
        aria-labelledby={`evenements-onglet-${classement}`}
        className="evenements-panneau"
      >
        {donnees.evenements.length === 0 ? (
          <Alerte>
            {classement === 'a_venir'
              ? 'Aucun evenement a venir pour le moment.'
              : 'Aucun evenement passe.'}
          </Alerte>
        ) : (
          <ul className="evenements-liste">
            {donnees.evenements.map((evenement) => (
              <li key={evenement.identifiant} className="evenements-carte">
                <div className="evenements-carte-entete">
                  <h2 className="evenements-titre">{evenement.titre}</h2>
                  {evenement.etat === 'cancelled' ? <Badge ton="ko">Annule</Badge> : null}
                </div>
                <p className="evenements-horaire">
                  {plageDeLEvenement(evenement.commenceLe, evenement.finitLe)}
                </p>
                {evenement.lieu === null ? null : (
                  <p className="evenements-lieu">{evenement.lieu}</p>
                )}
                {evenement.description === null ? null : (
                  <p className="evenements-description">{evenement.description}</p>
                )}
              </li>
            ))}
          </ul>
        )}

        {donnees.pages > 1 ? (
          <nav aria-label="Pagination des evenements" className="evenements-pagination">
            <button
              type="button"
              className="evenements-page"
              disabled={donnees.page <= 1}
              onClick={() => {
                setPage((precedente) => Math.max(1, precedente - 1));
              }}
            >
              Page precedente
            </button>
            <span className="evenements-position">
              Page {donnees.page} sur {donnees.pages}
            </span>
            <button
              type="button"
              className="evenements-page"
              disabled={donnees.page >= donnees.pages}
              onClick={() => {
                setPage((precedente) => precedente + 1);
              }}
            >
              Page suivante
            </button>
          </nav>
        ) : null}
      </div>
    </div>
  );
}
