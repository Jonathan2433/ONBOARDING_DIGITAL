/**
 * Gerer les evenements de l'entite, a l'ecran — LOT 8, `T10`, `MVP-L08-US004`.
 *
 * LE SOMMAIRE, TOUS ETATS — ET AUCUNE PORTEE LOCALE N'Y EST APPLIQUEE
 *
 *   `GET …/events/gestion` ne verifie qu'un role COARSE — meme parti que
 *   `/pages/gestion` (LOT 6, `T10`) et `/liens/gestion` (LOT 6, `T8`). Un
 *   Booster voit donc TOUS les evenements de son entite, memes ceux qu'il ne
 *   pourra pas ouvrir : la portee LOCALE n'est resolue que par
 *   `GET …/events/{evenement}/gestion`, qui refuse en 403 cote edition.
 *
 * LE FRONTEND N'EST PAS L'AUTORITE
 *
 *   `peutGererLesEvenements` sert a ne pas PROPOSER cet ecran a qui n'a AUCUN
 *   role de creation sur les evenements (§20.1, refus par defaut) — jamais a
 *   garantir qu'une action precise reussira. Un DSM createur seul (pas le DSM
 *   NOMME par `event_dsm_scope`) voit ce sommaire et peut creer, mais sera
 *   refuse en 403 en tentant de publier un evenement de portee Entite qu'il a
 *   simplement cree — exactement l'avertissement deja accepte pour un Booster
 *   sur une page de contenu (`PanneauEditionDeContenu.tsx`).
 *
 * AUCUN `Date` POUR LES CHAMPS DE DATE-HEURE, DANS AUCUN SENS
 *
 *   Meme motif que `dateComplete`/`heure` de `PageEvenements.tsx` : un `Date`
 *   construit depuis une chaine, puis lu par des accesseurs LOCAUX, peut
 *   rendre une heure ou un jour different de celui ecrit. La encore, le
 *   format `YYYY-MM-DDTHH:mm` d'un `<input type="datetime-local">` EST deja
 *   le prefixe exact d'une chaine ISO : `versDatetimeLocal` le decoupe, et
 *   `depuisDatetimeLocal` le recompose avec un decalage NUL explicite — jamais
 *   une conversion de fuseau, dans aucun des deux sens.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { creerUnEvenement, lireLesEvenementsPourGestion } from '../api/evenements';
import { cheminEditionEvenement } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import {
  peutGererLesEvenements,
  type DemandeDeCreationDEvenement,
  type EvenementDeGestion,
  type PorteeDeCreationEvenement,
} from '@onboarding/contracts';
import { Alerte, Badge, Bouton } from '@onboarding/ui';

/** « 2026-10-12T08:00 » depuis une chaine ISO — AUCUN `Date`, voir l'en-tete. */
export function versDatetimeLocal(iso: string): string {
  return iso.slice(0, 16);
}

/** L'inverse : un decalage NUL explicite, jamais recalcule — voir l'en-tete. */
export function depuisDatetimeLocal(local: string): string {
  return `${local}:00+00:00`;
}

const LIBELLES_D_ETAT: Readonly<Record<string, string>> = {
  draft: 'Brouillon',
  published: 'Publie',
  cancelled: 'Annule',
  archived: 'Archive',
};

const TONS_D_ETAT: Readonly<Record<string, 'neutre' | 'ok' | 'ko' | 'marque'>> = {
  draft: 'neutre',
  published: 'ok',
  cancelled: 'ko',
  archived: 'neutre',
};

const CHAMPS_VIDES = {
  titre: '',
  description: '',
  commence_le: '',
  finit_le: '',
  lieu: '',
  portee: 'entite' as PorteeDeCreationEvenement,
  cercle: '',
  bureau: '',
};

/**
 * `exactOptionalPropertyTypes` refuse `{ description: undefined }` : un champ
 * facultatif ABSENT n'est pas un champ present a `undefined` — meme garde que
 * `champsDeLien` dans `PageGestionDesLiens.tsx`.
 */
function demandeDeCreation(champs: typeof CHAMPS_VIDES): DemandeDeCreationDEvenement {
  return {
    titre: champs.titre,
    ...(champs.description === '' ? {} : { description: champs.description }),
    commence_le: depuisDatetimeLocal(champs.commence_le),
    finit_le: depuisDatetimeLocal(champs.finit_le),
    ...(champs.lieu === '' ? {} : { lieu: champs.lieu }),
    portee: champs.portee,
    ...(champs.portee === 'cercle' && champs.cercle !== '' ? { cercle: champs.cercle } : {}),
    ...(champs.portee === 'bureau' && champs.bureau !== '' ? { bureau: champs.bureau } : {}),
  };
}

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas cette portee de creation dans cette entite.';
  }
  if (statut === 422) {
    return 'La demande est invalide : verifiez les dates, le cercle ou le bureau nomme.';
  }
  return "L'action n'a pas pu aboutir. Reessayez dans un instant.";
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'liste'; readonly evenements: readonly EvenementDeGestion[] }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageGestionDesEvenements(): JSX.Element | null {
  const { entite, permissions } = useEntiteConsultee();
  const codeEntite = entite.code;
  const roles = permissions?.roles ?? null;
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });
  const [formulaireOuvert, setFormulaireOuvert] = useState(false);
  const [nouveau, setNouveau] = useState(CHAMPS_VIDES);
  const [erreurEnvoi, setErreurEnvoi] = useState<string | null>(null);

  useEffect(() => {
    //  **N'APPELLE MEME PAS LA ROUTE SANS ROLE DE CREATION** — meme discipline
    //  que `PanneauEditionDeContenu.tsx` : la route est gardee cote API, et un
    //  appel sans ce role serait refuse a coup sur.
    if (roles === null || !peutGererLesEvenements(roles)) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLesEvenementsPourGestion(codeEntite, abandon.signal).then(
      (reponse) => {
        if (abandon.signal.aborted) {
          return;
        }
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'liste', evenements: reponse.corps.evenements }
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
  }, [codeEntite, roles]);

  if (roles === null) {
    return null;
  }
  if (!peutGererLesEvenements(roles)) {
    //  **REFUS PAR DEFAUT, §20.1.** Cet ecran n'est propose a personne d'autre.
    return (
      <Alerte urgence="information">
        Vous n&rsquo;avez pas de droit de gestion des evenements.
      </Alerte>
    );
  }

  async function recharger(): Promise<void> {
    const reponse = await lireLesEvenementsPourGestion(codeEntite);
    if (reponse.statut === 200 && reponse.corps !== null) {
      setEtat({ phase: 'liste', evenements: reponse.corps.evenements });
    } else {
      setEtat({ phase: 'erreur', statut: reponse.statut });
    }
  }

  async function creer(): Promise<void> {
    setErreurEnvoi(null);
    if (nouveau.titre === '' || nouveau.commence_le === '' || nouveau.finit_le === '') {
      setErreurEnvoi('Le titre et les deux dates sont obligatoires.');
      return;
    }
    const resultat = await creerUnEvenement(codeEntite, demandeDeCreation(nouveau));
    if (resultat.statut === 201) {
      setNouveau(CHAMPS_VIDES);
      setFormulaireOuvert(false);
      await recharger();
    } else {
      setErreurEnvoi(messageDeRefus(resultat.statut));
    }
  }

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement des evenements…</Alerte>;
  }
  if (etat.phase === 'erreur') {
    return (
      <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {messageDeRefus(etat.statut)}
      </Alerte>
    );
  }

  const evenements = etat.evenements;

  return (
    <section className="evenements-gestion">
      {erreurEnvoi === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreurEnvoi}
        </Alerte>
      )}

      {evenements.length === 0 ? (
        <Alerte urgence="information">Aucun evenement pour le moment.</Alerte>
      ) : (
        <ul className="evenements-gestion-liste">
          {evenements.map((evenement) => (
            <li key={evenement.identifiant} className="evenements-gestion-ligne">
              <div className="evenements-gestion-details">
                <Link
                  className="app-lien evenements-gestion-titre"
                  to={cheminEditionEvenement(codeEntite, evenement.identifiant)}
                >
                  {evenement.titre}
                </Link>
                <span className="evenements-gestion-dates">
                  {versDatetimeLocal(evenement.commenceLe).replace('T', ' a ')}
                </span>
              </div>
              <Badge ton={TONS_D_ETAT[evenement.etat] ?? 'neutre'}>
                {LIBELLES_D_ETAT[evenement.etat] ?? evenement.etat}
              </Badge>
            </li>
          ))}
        </ul>
      )}

      {formulaireOuvert ? (
        <form
          className="evenements-gestion-formulaire"
          onSubmit={(evenement) => {
            evenement.preventDefault();
            void creer();
          }}
        >
          <label htmlFor="evenement-titre">
            Titre
            <input
              id="evenement-titre"
              onChange={(e) => {
                setNouveau({ ...nouveau, titre: e.target.value });
              }}
              required
              type="text"
              value={nouveau.titre}
            />
          </label>
          <label htmlFor="evenement-description">
            Description (facultatif)
            <input
              id="evenement-description"
              onChange={(e) => {
                setNouveau({ ...nouveau, description: e.target.value });
              }}
              type="text"
              value={nouveau.description}
            />
          </label>
          <label htmlFor="evenement-commence-le">
            Debut
            <input
              id="evenement-commence-le"
              onChange={(e) => {
                setNouveau({ ...nouveau, commence_le: e.target.value });
              }}
              required
              type="datetime-local"
              value={nouveau.commence_le}
            />
          </label>
          <label htmlFor="evenement-finit-le">
            Fin
            <input
              id="evenement-finit-le"
              onChange={(e) => {
                setNouveau({ ...nouveau, finit_le: e.target.value });
              }}
              required
              type="datetime-local"
              value={nouveau.finit_le}
            />
          </label>
          <label htmlFor="evenement-lieu">
            Lieu (facultatif)
            <input
              id="evenement-lieu"
              onChange={(e) => {
                setNouveau({ ...nouveau, lieu: e.target.value });
              }}
              type="text"
              value={nouveau.lieu}
            />
          </label>
          <label htmlFor="evenement-portee">
            Portee
            <select
              id="evenement-portee"
              onChange={(e) => {
                setNouveau({ ...nouveau, portee: e.target.value as PorteeDeCreationEvenement });
              }}
              value={nouveau.portee}
            >
              <option value="entite">Entite</option>
              <option value="cercle">Un cercle</option>
              <option value="bureau">Un bureau</option>
              <option value="consultants">Mes consultants (DSM)</option>
            </select>
          </label>
          {nouveau.portee === 'cercle' ? (
            <label htmlFor="evenement-cercle">
              Code du cercle
              <input
                id="evenement-cercle"
                onChange={(e) => {
                  setNouveau({ ...nouveau, cercle: e.target.value });
                }}
                required
                type="text"
                value={nouveau.cercle}
              />
            </label>
          ) : null}
          {nouveau.portee === 'bureau' ? (
            <label htmlFor="evenement-bureau">
              Code du bureau
              <input
                id="evenement-bureau"
                onChange={(e) => {
                  setNouveau({ ...nouveau, bureau: e.target.value });
                }}
                required
                type="text"
                value={nouveau.bureau}
              />
            </label>
          ) : null}
          <div className="evenements-gestion-formulaire-actions">
            <Bouton type="submit" variante="primaire">
              Creer l&rsquo;evenement
            </Bouton>
            <Bouton
              onClick={() => {
                setFormulaireOuvert(false);
                setNouveau(CHAMPS_VIDES);
              }}
              type="button"
              variante="secondaire"
            >
              Annuler
            </Bouton>
          </div>
        </form>
      ) : (
        <Bouton
          onClick={() => {
            setFormulaireOuvert(true);
          }}
          type="button"
          variante="secondaire"
        >
          Nouvel evenement
        </Bouton>
      )}
    </section>
  );
}
