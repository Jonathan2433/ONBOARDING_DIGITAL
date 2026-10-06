/**
 * Editer un evenement — LOT 8, `T10`, `MVP-L08-US004`.
 *
 * LA ROUTE QUE `T9` N'A DELIBEREMENT PAS CREEE
 *
 *   La lecture de `T9` n'avait besoin d'aucune page de detail : chaque carte
 *   affiche deja tout ce qu'elle a. Editer suppose en revanche une cible par
 *   IDENTIFIANT — c'est cette route, posee ici, pour la premiere fois.
 *
 * DEUX GRILLES DE ROLES, PAS UNE SEULE
 *
 *   `peutGererLesEvenements` (DSM/ESM/BOOST/OFFICE/ADM-E/SUPER) gouverne
 *   Modifier, Publier, Annuler, Archiver et la gestion des medias.
 *   `peutRestaurerUnEvenement` (ESM/ADM-E/SUPER) gouverne SEULE la
 *   restauration — `ARB-DROIT-003` exclut DSM/BOOST/OFFICE en bloc, meme
 *   s'ils portent l'archivage de l'evenement. Les fusionner proposerait un
 *   bouton que l'API refuserait (§7.21 de la passation).
 *
 * LE FRONTEND N'EST PAS L'AUTORITE
 *
 *   Un role suffisant pour `peutGererLesEvenements` peut recevoir un 403 :
 *   la portee LOCALE (son cercle, son bureau, ses consultants nommes dans
 *   `event_dsm_scope`) n'est resolue que par l'API. Cet ecran le rapporte
 *   tel quel — meme discipline que `PanneauEditionDeContenu.tsx`.
 *
 * `cercles`/`bureaux` : UNE LISTE DE CODES, SEPARES PAR DES VIRGULES
 *
 *   Aucun selecteur de cercle ou de bureau n'existe encore dans ce depot ; en
 *   livrer un sans un second ecran qui le reutilise serait du code non
 *   eprouve (meme principe que l'absence de primitive d'onglets, `T9`). Un
 *   champ texte restitue exactement les trois etats de l'API : vide (la
 *   liste se vide), un ou plusieurs codes (elle les remplace).
 *
 * LES MEDIAS : AUCUN TELEVERSEMENT, UN RATTACHEMENT SEUL
 *
 *   Meme principe que l'API (`app/events/ecriture.py`, `T6`) : le media doit
 *   deja exister, `ready`, dans cette entite (LOT 11). Cet ecran rattache par
 *   IDENTIFIANT — un champ que l'ecran ne peut pas encore remplir depuis une
 *   mediatheque, qui n'existe pas davantage.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import {
  annulerUnEvenement,
  archiverUnEvenement,
  gererLesMediasDUnEvenement,
  lireUnEvenementPourGestion,
  modifierUnEvenement,
  publierUnEvenement,
  restaurerUnEvenement,
} from '../api/evenements';
import { cheminGestionDesEvenementsALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { depuisDatetimeLocal, versDatetimeLocal } from './PageGestionDesEvenements';

import {
  peutGererLesEvenements,
  peutRestaurerUnEvenement,
  type EvenementPourGestion,
  type MediaDEvenement,
} from '@onboarding/contracts';
import { Alerte, Badge, Bouton } from '@onboarding/ui';

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

/** « CERCLE-A, CERCLE-B » -> `['CERCLE-A', 'CERCLE-B']` — les vides sont retires. */
function versListeDeCodes(valeur: string): readonly string[] {
  return valeur
    .split(',')
    .map((code) => code.trim())
    .filter((code) => code !== '');
}

function enTexteDeListe(codes: readonly string[]): string {
  return codes.join(', ');
}

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas cette action sur cet evenement.';
  }
  if (statut === 404) {
    return 'Cet evenement est introuvable, ou hors de votre perimetre.';
  }
  if (statut === 409) {
    return 'Cet evenement a change depuis votre derniere lecture. Rechargez avant de reessayer.';
  }
  if (statut === 422) {
    return 'La demande est invalide : verifiez les dates, les codes ou les medias nommes.';
  }
  return "L'action n'a pas pu aboutir. Reessayez dans un instant.";
}

type ActionDeTransition = 'publication' | 'annulation' | 'archivage' | 'restauration';

type Etat =
  | { readonly phase: 'chargement' }
  | {
      readonly phase: 'evenement';
      readonly donnee: EvenementPourGestion;
      readonly titreDeTravail: string;
      readonly descriptionDeTravail: string;
      readonly commenceLeDeTravail: string;
      readonly finitLeDeTravail: string;
      readonly lieuDeTravail: string;
      readonly cerclesDeTravail: string;
      readonly bureauxDeTravail: string;
      readonly motifDAnnulation: string;
      readonly nouveauMedia: string;
      readonly nouveauRole: string;
      readonly mediasDeTravail: readonly MediaDEvenement[];
      readonly enregistrement: 'repos' | 'envoi';
    }
  | { readonly phase: 'erreur'; readonly statut: number };

function versEtatDeTravail(
  donnee: EvenementPourGestion,
  precedent?: Extract<Etat, { phase: 'evenement' }>,
): Etat {
  return {
    phase: 'evenement',
    donnee,
    titreDeTravail: donnee.titre,
    descriptionDeTravail: donnee.description ?? '',
    commenceLeDeTravail: versDatetimeLocal(donnee.commenceLe),
    finitLeDeTravail: versDatetimeLocal(donnee.finitLe),
    lieuDeTravail: donnee.lieu ?? '',
    cerclesDeTravail: enTexteDeListe(donnee.cercles),
    bureauxDeTravail: enTexteDeListe(donnee.bureaux),
    motifDAnnulation: precedent?.motifDAnnulation ?? '',
    nouveauMedia: '',
    nouveauRole: '',
    mediasDeTravail: donnee.medias,
    enregistrement: 'repos',
  };
}

export function PageEditionEvenement(): JSX.Element | null {
  const { entite, permissions } = useEntiteConsultee();
  const codeEntite = entite.code;
  const { evenement } = useParams<{ evenement: string }>();
  const roles = permissions?.roles ?? null;
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    if (evenement === undefined || roles === null || !peutGererLesEvenements(roles)) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireUnEvenementPourGestion(codeEntite, evenement, abandon.signal).then(
      (reponse) => {
        if (abandon.signal.aborted) {
          return;
        }
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? versEtatDeTravail(reponse.corps)
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
  }, [codeEntite, evenement, roles]);

  const retour = (
    <p>
      <Link className="app-lien" to={cheminGestionDesEvenementsALEcran(codeEntite)}>
        Retour aux evenements
      </Link>
    </p>
  );

  if (roles === null) {
    return null;
  }
  if (!peutGererLesEvenements(roles)) {
    return (
      <Alerte urgence="information">
        Vous n&rsquo;avez pas de droit de gestion des evenements.
      </Alerte>
    );
  }
  if (evenement === undefined) {
    return (
      <>
        <Alerte ton="erreur" urgence="alerte">
          Cet evenement est introuvable.
        </Alerte>
        {retour}
      </>
    );
  }
  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement de l&rsquo;evenement…</Alerte>;
  }
  if (etat.phase === 'erreur') {
    return (
      <>
        <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {messageDeRefus(etat.statut)}
        </Alerte>
        {retour}
      </>
    );
  }

  const {
    donnee,
    titreDeTravail,
    descriptionDeTravail,
    commenceLeDeTravail,
    finitLeDeTravail,
    lieuDeTravail,
    cerclesDeTravail,
    bureauxDeTravail,
    motifDAnnulation,
    nouveauMedia,
    nouveauRole,
    mediasDeTravail,
    enregistrement,
  } = etat;

  const peutModifier = peutGererLesEvenements(roles);
  const peutRestaurer = peutRestaurerUnEvenement(roles);

  async function recharger(): Promise<void> {
    if (evenement === undefined) {
      return;
    }
    const reponse = await lireUnEvenementPourGestion(codeEntite, evenement);
    setEtat(
      reponse.statut === 200 && reponse.corps !== null
        ? versEtatDeTravail(reponse.corps, etat.phase === 'evenement' ? etat : undefined)
        : { phase: 'erreur', statut: reponse.statut },
    );
  }

  async function enregistrer(): Promise<void> {
    if (evenement === undefined) {
      return;
    }
    //  **UN OBJET COMPLET, JAMAIS `{ ...etat, ... }`** : `etat` est declare par
    //  hoisting pour cette fonction, et TypeScript n'y retient pas le
    //  retrecissement du type fait plus haut (meme motif que les fonctions
    //  imbriquees de `PanneauEditionDeContenu.tsx`).
    setEtat({
      phase: 'evenement',
      donnee,
      titreDeTravail,
      descriptionDeTravail,
      commenceLeDeTravail,
      finitLeDeTravail,
      lieuDeTravail,
      cerclesDeTravail,
      bureauxDeTravail,
      motifDAnnulation,
      nouveauMedia,
      nouveauRole,
      mediasDeTravail,
      enregistrement: 'envoi',
    });
    const resultat = await modifierUnEvenement(codeEntite, evenement, {
      titre: titreDeTravail,
      ...(descriptionDeTravail === '' ? {} : { description: descriptionDeTravail }),
      commence_le: depuisDatetimeLocal(commenceLeDeTravail),
      finit_le: depuisDatetimeLocal(finitLeDeTravail),
      ...(lieuDeTravail === '' ? {} : { lieu: lieuDeTravail }),
      version: donnee.version,
      cercles: versListeDeCodes(cerclesDeTravail),
      bureaux: versListeDeCodes(bureauxDeTravail),
    });
    if (resultat.statut === 200) {
      await recharger();
    } else {
      setEtat({ phase: 'erreur', statut: resultat.statut });
    }
  }

  async function agir(action: ActionDeTransition): Promise<void> {
    if (evenement === undefined) {
      return;
    }
    const resultat =
      action === 'publication'
        ? await publierUnEvenement(codeEntite, evenement, { version: donnee.version })
        : action === 'annulation'
          ? await annulerUnEvenement(codeEntite, evenement, {
              version: donnee.version,
              ...(motifDAnnulation === '' ? {} : { motif: motifDAnnulation }),
            })
          : action === 'archivage'
            ? await archiverUnEvenement(codeEntite, evenement, { version: donnee.version })
            : await restaurerUnEvenement(codeEntite, evenement, { version: donnee.version });
    if (resultat.statut === 200) {
      await recharger();
    } else {
      setEtat({ phase: 'erreur', statut: resultat.statut });
    }
  }

  function deplacerMedia(rang: number, delta: 1 | -1): void {
    const cible = rang + delta;
    if (cible < 0 || cible >= mediasDeTravail.length) {
      return;
    }
    const copie = [...mediasDeTravail];
    const media = copie[rang];
    const autre = copie[cible];
    if (media === undefined || autre === undefined) {
      return;
    }
    copie[rang] = autre;
    copie[cible] = media;
    setEtat({
      phase: 'evenement',
      donnee,
      titreDeTravail,
      descriptionDeTravail,
      commenceLeDeTravail,
      finitLeDeTravail,
      lieuDeTravail,
      cerclesDeTravail,
      bureauxDeTravail,
      motifDAnnulation,
      nouveauMedia,
      nouveauRole,
      mediasDeTravail: copie,
      enregistrement,
    });
  }

  function retirerMedia(rang: number): void {
    setEtat({
      phase: 'evenement',
      donnee,
      titreDeTravail,
      descriptionDeTravail,
      commenceLeDeTravail,
      finitLeDeTravail,
      lieuDeTravail,
      cerclesDeTravail,
      bureauxDeTravail,
      motifDAnnulation,
      nouveauMedia,
      nouveauRole,
      mediasDeTravail: mediasDeTravail.filter((_, i) => i !== rang),
      enregistrement,
    });
  }

  function ajouterMedia(): void {
    if (nouveauMedia === '' || nouveauRole === '') {
      return;
    }
    setEtat({
      phase: 'evenement',
      donnee,
      titreDeTravail,
      descriptionDeTravail,
      commenceLeDeTravail,
      finitLeDeTravail,
      lieuDeTravail,
      cerclesDeTravail,
      bureauxDeTravail,
      motifDAnnulation,
      mediasDeTravail: [
        ...mediasDeTravail,
        { media: nouveauMedia, role: nouveauRole, ordre: mediasDeTravail.length },
      ],
      nouveauMedia: '',
      nouveauRole: '',
      enregistrement,
    });
  }

  async function enregistrerLesMedias(): Promise<void> {
    if (evenement === undefined) {
      return;
    }
    const resultat = await gererLesMediasDUnEvenement(codeEntite, evenement, {
      version: donnee.version,
      medias: mediasDeTravail.map((m) => ({ media: m.media, role: m.role })),
    });
    if (resultat.statut === 200) {
      await recharger();
    } else {
      setEtat({ phase: 'erreur', statut: resultat.statut });
    }
  }

  return (
    <section className="edition-panneau">
      <h2>{donnee.titre}</h2>
      <p className="edition-etat">
        Etat :{' '}
        <Badge ton={TONS_D_ETAT[donnee.etat] ?? 'neutre'}>
          {LIBELLES_D_ETAT[donnee.etat] ?? donnee.etat}
        </Badge>
        {' — version '}
        {donnee.version}
      </p>
      {donnee.etat === 'cancelled' && donnee.motifDAnnulation !== null ? (
        <p>Motif d&rsquo;annulation : {donnee.motifDAnnulation}</p>
      ) : null}

      {donnee.etat !== 'archived' && peutModifier ? (
        <>
          <label className="edition-champ" htmlFor="evenement-edition-titre">
            Titre
            <input
              id="evenement-edition-titre"
              onChange={(e) => {
                setEtat({ ...etat, titreDeTravail: e.target.value });
              }}
              type="text"
              value={titreDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-description">
            Description
            <input
              id="evenement-edition-description"
              onChange={(e) => {
                setEtat({ ...etat, descriptionDeTravail: e.target.value });
              }}
              type="text"
              value={descriptionDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-commence-le">
            Debut
            <input
              id="evenement-edition-commence-le"
              onChange={(e) => {
                setEtat({ ...etat, commenceLeDeTravail: e.target.value });
              }}
              type="datetime-local"
              value={commenceLeDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-finit-le">
            Fin
            <input
              id="evenement-edition-finit-le"
              onChange={(e) => {
                setEtat({ ...etat, finitLeDeTravail: e.target.value });
              }}
              type="datetime-local"
              value={finitLeDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-lieu">
            Lieu
            <input
              id="evenement-edition-lieu"
              onChange={(e) => {
                setEtat({ ...etat, lieuDeTravail: e.target.value });
              }}
              type="text"
              value={lieuDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-cercles">
            Cercles rattaches (codes separes par des virgules)
            <input
              id="evenement-edition-cercles"
              onChange={(e) => {
                setEtat({ ...etat, cerclesDeTravail: e.target.value });
              }}
              type="text"
              value={cerclesDeTravail}
            />
          </label>
          <label className="edition-champ" htmlFor="evenement-edition-bureaux">
            Bureaux rattaches (codes separes par des virgules)
            <input
              id="evenement-edition-bureaux"
              onChange={(e) => {
                setEtat({ ...etat, bureauxDeTravail: e.target.value });
              }}
              type="text"
              value={bureauxDeTravail}
            />
          </label>
          <Bouton
            disabled={enregistrement === 'envoi'}
            onClick={() => {
              void enregistrer();
            }}
            type="button"
            variante="primaire"
          >
            {enregistrement === 'envoi' ? 'Enregistrement…' : 'Enregistrer'}
          </Bouton>
        </>
      ) : null}

      <div className="edition-cycle-de-vie">
        {donnee.etat === 'draft' && peutModifier ? (
          <Bouton
            onClick={() => {
              void agir('publication');
            }}
            type="button"
            variante="secondaire"
          >
            Publier
          </Bouton>
        ) : null}
        {donnee.etat === 'published' && peutModifier ? (
          <Bouton
            onClick={() => {
              void agir('annulation');
            }}
            type="button"
            variante="secondaire"
          >
            Annuler
          </Bouton>
        ) : null}
        {donnee.etat !== 'archived' && peutModifier ? (
          <Bouton
            onClick={() => {
              void agir('archivage');
            }}
            type="button"
            variante="secondaire"
          >
            Archiver
          </Bouton>
        ) : null}
        {donnee.etat === 'archived' && peutRestaurer ? (
          <Bouton
            onClick={() => {
              void agir('restauration');
            }}
            type="button"
            variante="secondaire"
          >
            Restaurer
          </Bouton>
        ) : null}
      </div>
      {donnee.etat === 'published' && peutModifier ? (
        <label className="edition-champ" htmlFor="evenement-edition-motif">
          Motif d&rsquo;annulation (facultatif, pour « Annuler »)
          <input
            id="evenement-edition-motif"
            onChange={(e) => {
              setEtat({ ...etat, motifDAnnulation: e.target.value });
            }}
            type="text"
            value={motifDAnnulation}
          />
        </label>
      ) : null}

      {donnee.etat !== 'archived' && peutModifier ? (
        <div className="evenements-edition-medias">
          <h3>Medias ({mediasDeTravail.length})</h3>
          {mediasDeTravail.length === 0 ? (
            <p>Aucun media rattache.</p>
          ) : (
            <ol className="evenements-edition-liste-medias">
              {mediasDeTravail.map((media, rang) => (
                <li key={media.media} className="evenements-edition-media">
                  <span>
                    {media.role} — {media.media}
                  </span>
                  <div className="evenements-edition-media-actions">
                    <button
                      disabled={rang === 0}
                      onClick={() => {
                        deplacerMedia(rang, -1);
                      }}
                      type="button"
                    >
                      Monter
                    </button>
                    <button
                      disabled={rang === mediasDeTravail.length - 1}
                      onClick={() => {
                        deplacerMedia(rang, 1);
                      }}
                      type="button"
                    >
                      Descendre
                    </button>
                    <button
                      onClick={() => {
                        retirerMedia(rang);
                      }}
                      type="button"
                    >
                      Retirer
                    </button>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <label htmlFor="evenement-nouveau-media">
            Identifiant du media (deja televerse, `ready`)
            <input
              id="evenement-nouveau-media"
              onChange={(e) => {
                setEtat({ ...etat, nouveauMedia: e.target.value });
              }}
              type="text"
              value={nouveauMedia}
            />
          </label>
          <label htmlFor="evenement-nouveau-role">
            Role d&rsquo;affichage
            <input
              id="evenement-nouveau-role"
              onChange={(e) => {
                setEtat({ ...etat, nouveauRole: e.target.value });
              }}
              type="text"
              value={nouveauRole}
            />
          </label>
          <Bouton
            onClick={() => {
              ajouterMedia();
            }}
            type="button"
            variante="secondaire"
          >
            Ajouter a la liste
          </Bouton>
          <Bouton
            onClick={() => {
              void enregistrerLesMedias();
            }}
            type="button"
            variante="primaire"
          >
            Enregistrer les medias
          </Bouton>
        </div>
      ) : null}

      {retour}
    </section>
  );
}
