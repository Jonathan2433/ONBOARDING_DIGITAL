/**
 * Deposer et autoriser une photo de profil, a l'ecran — LOT 11, `T2`,
 * `MVP-L11-US004`/`US005`.
 *
 * LES DROITS VIENNENT DE L'API, PAS D'UN CALCUL LOCAL
 *
 *   Contrairement a `PanneauDuCycleDeVie`, qui derive son permis des `roles`
 *   deja connus du cadre, le permis d'une photo depend d'un etat que le
 *   frontend ne peut pas observer — la fiche d'arrivee est-elle publiee ? un
 *   Booster est-il rattache au cercle de CETTE cible ? `GET …/photo/droits`
 *   (commodite d'ecran cote API, `app/media/routes.py`) resout la question
 *   une fois, et ce panneau n'en refait jamais le calcul.
 *
 *   **RIEN N'EST RENDU TANT QUE LES DROITS NE SONT PAS ARRIVES, NI SI LES
 *   DEUX SONT REFUSES** — meme discipline que `PanneauDuCycleDeVie` : un
 *   panneau qui apparaitrait puis disparaitrait est pire qu'un panneau
 *   absent.
 *
 * LE DEPOT EST SUIVI PAR SONDAGE, FAUTE D'AUTRE MECANISME
 *
 *   Le traitement (verification du contenu reel, generation de la miniature)
 *   est ASYNCHRONE — `app.jobs`, LOT 11 `T1`. Aucune route ne pousse l'etat
 *   au client : `lireLEtatDUnMedia` est donc interroge toutes les 1,5 s tant
 *   que l'etat reste `pending`/`processing`, borne a 20 tentatives — passe ce
 *   delai, l'ecran dit d'actualiser plutot que de sonder indefiniment.
 *
 * ACCORDER N'EST JAMAIS AUTOMATIQUE APRES LE DEPOT, ET C'EST LA MATRICE
 *
 *   Matrice §6.1 : « Ajouter ou remplacer une photo » et « Enregistrer
 *   l'autorisation photo » sont DEUX lignes a DEUX grilles distinctes — un
 *   DSM peut deposer la photo de son consultant mais jamais l'autoriser.
 *   Le bouton d'autorisation n'apparait donc que si `droits.peutGererAutorisation`
 *   est vrai, independamment de qui a depose.
 */
import type { JSX } from 'react';
import { useEffect, useRef, useState } from 'react';

import {
  accorderLAutorisationDePhoto,
  deposerUnePhoto,
  lireLesDroitsDePhoto,
  lireLEtatDUnMedia,
  retirerLAutorisationDePhoto,
} from '../api/media';

import type { DroitsDePhoto } from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

const DELAI_DE_SONDAGE_MS = 1500;
const TENTATIVES_DE_SONDAGE_MAXIMALES = 20;

type PhaseDepot =
  | { readonly nom: 'repos' }
  | { readonly nom: 'envoi' }
  | { readonly nom: 'traitement'; readonly media: string }
  | { readonly nom: 'pret'; readonly media: string }
  | { readonly nom: 'rejete'; readonly code: string | null }
  | { readonly nom: 'autorisation_en_cours'; readonly media: string }
  | { readonly nom: 'autorise' }
  | { readonly nom: 'refus'; readonly statut: number };

export interface ProprietesPanneauPhoto {
  readonly codeEntite: string;
  readonly appartenance: string;
  /** Appele apres un octroi ou un retrait reussi, pour que la page recharge la miniature. */
  readonly surSucces: () => void;
}

const MESSAGES_DE_REJET: Readonly<Record<string, string>> = {
  contenu_illisible: 'Ce fichier n’est pas une image lisible.',
  format_non_autorise: 'Ce format d’image n’est pas accepte — utilisez JPEG, PNG ou WebP.',
};

function messageDeRefusDuDepot(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas de deposer cette photo.';
  }
  if (statut === 422) {
    return 'Ce fichier ne peut pas etre depose — verifiez sa taille (10 Mo maximum) et son type.';
  }
  return 'Le depot n’a pas pu aboutir. Reessayez dans un instant.';
}

export function PanneauPhoto({
  codeEntite,
  appartenance,
  surSucces,
}: ProprietesPanneauPhoto): JSX.Element | null {
  const [droits, setDroits] = useState<DroitsDePhoto | null>(null);
  const [phase, setPhase] = useState<PhaseDepot>({ nom: 'repos' });
  const [retrait, setRetrait] = useState<{ envoi: boolean; refus: number | null }>({
    envoi: false,
    refus: null,
  });
  //  **UNE REFERENCE, PAS UN ETAT** : la sequence de sondage doit lire la
  //  derniere valeur d'abandon sans redeclencher l'effet qui la lit — un
  //  `useState` pour ce seul usage provoquerait un second rendu inutile.
  const abandonne = useRef(false);

  useEffect(() => {
    abandonne.current = false;
    const abandon = new AbortController();
    void lireLesDroitsDePhoto(codeEntite, appartenance, abandon.signal).then((reponse) => {
      if (!abandon.signal.aborted) {
        setDroits(reponse.corps);
      }
    });
    return () => {
      abandonne.current = true;
      abandon.abort();
    };
  }, [codeEntite, appartenance]);

  async function sonder(media: string, tentative: number): Promise<void> {
    if (abandonne.current) {
      return;
    }
    const reponse = await lireLEtatDUnMedia(codeEntite, media);
    if (abandonne.current) {
      return;
    }
    if (reponse.corps === null) {
      //  Panne reseau ou refus inattendu : on ne boucle pas indefiniment sur
      //  une cause qu'on ne peut pas corriger en sondant davantage. §7.6.
      setPhase({ nom: 'refus', statut: reponse.statut });
      return;
    }
    const { etat, codeDeRejet } = reponse.corps;
    if (etat === 'ready') {
      setPhase({ nom: 'pret', media });
      return;
    }
    if (etat === 'rejected') {
      setPhase({ nom: 'rejete', code: codeDeRejet });
      return;
    }
    if (tentative >= TENTATIVES_DE_SONDAGE_MAXIMALES) {
      //  Toujours `pending`/`processing` apres vingt tentatives : le dire,
      //  jamais sonder pour toujours.
      setPhase({ nom: 'traitement', media });
      return;
    }
    setTimeout(() => {
      void sonder(media, tentative + 1);
    }, DELAI_DE_SONDAGE_MS);
  }

  async function deposer(fichier: File): Promise<void> {
    setPhase({ nom: 'envoi' });
    try {
      const reponse = await deposerUnePhoto(codeEntite, appartenance, fichier);
      if (reponse.statut === 201 && reponse.corps !== null) {
        setPhase({ nom: 'traitement', media: reponse.corps.identifiant });
        void sonder(reponse.corps.identifiant, 1);
      } else {
        setPhase({ nom: 'refus', statut: reponse.statut });
      }
    } catch {
      setPhase({ nom: 'refus', statut: 0 });
    }
  }

  async function autoriser(media: string): Promise<void> {
    setPhase({ nom: 'autorisation_en_cours', media });
    try {
      const reponse = await accorderLAutorisationDePhoto(codeEntite, appartenance, media);
      if (reponse.statut === 201 && reponse.corps !== null) {
        setPhase({ nom: 'autorise' });
        surSucces();
      } else {
        setPhase({ nom: 'refus', statut: reponse.statut });
      }
    } catch {
      setPhase({ nom: 'refus', statut: 0 });
    }
  }

  async function retirer(): Promise<void> {
    setRetrait({ envoi: true, refus: null });
    try {
      const reponse = await retirerLAutorisationDePhoto(codeEntite, appartenance);
      if (reponse.statut === 200) {
        setRetrait({ envoi: false, refus: null });
        surSucces();
      } else {
        setRetrait({ envoi: false, refus: reponse.statut });
      }
    } catch {
      setRetrait({ envoi: false, refus: 0 });
    }
  }

  //  **RIEN TANT QUE LES DROITS NE SONT PAS CONNUS, RIEN SI AUCUN DES DEUX
  //  N'EST ACCORDE** — meme discipline que `PanneauDuCycleDeVie`.
  if (droits === null || (!droits.peutDeposer && !droits.peutGererAutorisation)) {
    return null;
  }

  return (
    <div className="profil-photo-panneau">
      {droits.peutDeposer ? (
        <div className="profil-actions">
          <label className="profil-champ-fichier">
            Deposer une nouvelle photo
            <input
              accept="image/jpeg,image/png,image/webp"
              disabled={phase.nom === 'envoi' || phase.nom === 'traitement'}
              onChange={(e) => {
                const fichier = e.target.files?.[0];
                e.target.value = '';
                if (fichier !== undefined) {
                  void deposer(fichier);
                }
              }}
              type="file"
            />
          </label>
        </div>
      ) : null}

      {phase.nom === 'envoi' ? (
        <p className="profil-photo-statut" role="status">
          Depot en cours…
        </p>
      ) : phase.nom === 'traitement' ? (
        <p className="profil-photo-statut" role="status">
          Verification de la photo en cours… Actualisez dans un instant si le traitement se
          prolonge.
        </p>
      ) : phase.nom === 'rejete' ? (
        <Alerte ton="erreur" urgence="alerte">
          {phase.code !== null && phase.code in MESSAGES_DE_REJET
            ? MESSAGES_DE_REJET[phase.code]
            : 'Cette photo a ete refusee.'}
        </Alerte>
      ) : phase.nom === 'pret' && droits.peutGererAutorisation ? (
        <div className="profil-actions">
          <Alerte ton="avertissement" urgence="information">
            La photo est prete. Elle ne sera visible qu’une fois son affichage autorise.
          </Alerte>
          <Bouton
            onClick={() => {
              void autoriser(phase.media);
            }}
            type="button"
            variante="primaire"
          >
            Autoriser l’affichage
          </Bouton>
        </div>
      ) : phase.nom === 'autorisation_en_cours' ? (
        <p className="profil-photo-statut" role="status">
          Octroi de l’autorisation…
        </p>
      ) : phase.nom === 'autorise' ? (
        <Alerte ton="succes" urgence="alerte">
          La photo est desormais affichee.
        </Alerte>
      ) : phase.nom === 'refus' ? (
        <Alerte ton="erreur" urgence="alerte">
          {messageDeRefusDuDepot(phase.statut)}
        </Alerte>
      ) : null}

      {droits.peutGererAutorisation ? (
        <div className="profil-actions">
          <Bouton
            disabled={retrait.envoi}
            onClick={() => {
              void retirer();
            }}
            type="button"
            variante="secondaire"
          >
            {retrait.envoi ? 'Retrait…' : 'Retirer l’autorisation actuelle'}
          </Bouton>
          {retrait.refus === null ? null : (
            <Alerte ton="erreur" urgence="alerte">
              {retrait.refus === 403
                ? 'Votre role ne permet pas de retirer cette autorisation.'
                : 'Le retrait n’a pas pu aboutir. Reessayez dans un instant.'}
            </Alerte>
          )}
        </div>
      ) : null}
    </div>
  );
}
