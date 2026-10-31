/**
 * « Mon onboarding » — LOT 7, `T13`, écrans du nouvel arrivant.
 *
 * TROIS FONCTIONS, UNE SEULE PAGE — LE SUFFIXE `mon-onboarding` DÉCLARÉ AU LOT 4
 *
 *   `RUBRIQUES` ne réserve qu'UN chemin (`routes.ts`, `T4`). La fiche d'arrivée,
 *   le parcours et les tâches ne sont donc pas trois écrans distincts : c'est
 *   UNE page composée de deux sections, exactement comme `PageProfil` (LOT 5)
 *   compose la fiche et l'historique en un seul appel `Promise.all`.
 *
 * CETTE PAGE NE PREND JAMAIS D'APPARTENANCE EN PARAMÈTRE, ET C'EST LE POINT
 *
 *   Contrairement à `PageProfil` (`/trombinoscope/:appartenance`), il n'y a
 *   AUCUN `:appartenance` dans l'adresse : c'est toujours « la mienne ».
 *   `permissions.appartenance` (`T13`, extension de `GET …/permissions`) est
 *   le SEUL moyen dont dispose le frontend de la connaître — voir l'en-tête
 *   de `apps/api/app/permissions/routes.py`. Sans elle, aucune des routes de
 *   l'onboarding n'est appelable : toutes exigent un `entity_membership_id`
 *   explicite dans leur chemin (matrice §7, §8.1).
 *
 * AUCUNE FENÊTRE DE CINQ MINUTES N'EST CALCULÉE ICI
 *
 *   Le bouton « Annuler » est proposé pour toute tâche `completed` — c'est le
 *   409 de l'API qui referme la fenêtre, jamais une horloge côté client. Voir
 *   l'en-tête de `../api/onboarding.ts`.
 *
 * LE FRONTEND NE PROPOSE PAS UN DROIT QU'IL SAIT REFUSÉ
 *
 *   « Valider et publier » n'est proposé que si la fiche existe déjà et porte
 *   une présentation courte non vide, et seulement une fois les modifications
 *   locales enregistrées — pas parce que l'API l'exigerait autrement (elle
 *   refuserait de toute façon en 422/409), mais parce que proposer un bouton
 *   dont l'échec est déjà connu serait l'avertissement faux du §7.21.
 *
 * CHANTIER FRONT, S7 (`DEC-672`) : `CARTE`/`BADGE` — ET UN DÉFAUT LATENT
 * TROUVÉ EN MESURANT, PAS CONSTRUIT PAR CETTE SOUS-ÉTAPE
 *
 *   Mesuré avant tout code : `application.css` ne porte AUCUNE règle pour les
 *   classes `.onboarding-*` de ce fichier, depuis sa création au LOT 7 `T13`
 *   — cet écran rendait du HTML entièrement brut, sans mise en page ni
 *   habillage visuel d'aucune sorte. Les deux sections (fiche d'arrivée,
 *   parcours) deviennent des `<Carte titre="…">` — mêmes `h2` frères qu'avant
 *   (aucune hiérarchie de titre à préserver ici, contrairement à `PageProfil`
 *   en `S6` : ce fichier n'a jamais eu de titre englobant), donc aucun
 *   `niveauTitre` à fournir. L'état de la fiche et l'état d'une tâche
 *   deviennent des `Badge`, selon la MÊME convention à quatre tons
 *   (`neutre`/`ok`/`ko`/`marque`) déjà posée pour les événements
 *   (`PageGestionDesEvenements.tsx`/`PageEditionEvenement.tsx`, hors
 *   périmètre mais même idiome) plutôt qu'une nouvelle inventée ici. Le
 *   marqueur « Obligatoire » d'une tâche devient aussi un `Badge` — même
 *   parti que « Principal » sur un cercle (`S5`/`S6`) : une information qui
 *   n'apparaît que lorsqu'elle est vraie mérite le renfort visuel du design
 *   system, pas un `<span>` nu. La mise en page manquante (grilles de champs,
 *   listes, formulaire) reprend TEXTUELLEMENT les recettes CSS déjà posées
 *   ailleurs (`.profil-champs`, `.liens-formulaire`, `.evenements-carte`) —
 *   rien n'est inventé, §6.4.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  annulerUneTache,
  completerLaFiche,
  lireLaFicheArrivee,
  lireLeParcours,
  terminerUneTache,
  validerEtPublierLaFiche,
} from '../api/onboarding';
import { dateComplete } from './PageProfil';
import { useEntiteConsultee } from './CadreApplicatif';

import type { FicheArrivee, Parcours, TacheDuParcours } from '@onboarding/contracts';
import { Alerte, Badge, Bouton, Carte } from '@onboarding/ui';

/** Ce que la page a pu charger — même montage que `PageProfil` (LOT 5, `T11`). */
interface Chargement {
  readonly appartenance: string;
  readonly fiche: { readonly statut: number; readonly corps: FicheArrivee | null };
  readonly parcours: { readonly statut: number; readonly corps: Parcours | null };
}

function messageDeRefusDeLaFiche(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 409) {
    return (
      'Votre fiche a changé depuis votre dernière lecture, ou n’accepte plus de ' +
      'modification. Rechargez la page avant de réessayer.'
    );
  }
  if (statut === 422) {
    return 'La présentation courte est obligatoire avant de valider et publier.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

function messageDeRefusDeLaTache(action: 'completion' | 'annulation', statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 409 && action === 'completion') {
    return 'Cette tâche n’est plus « à faire » — elle a déjà été terminée, réouverte ou annulée.';
  }
  if (statut === 409 && action === 'annulation') {
    //  **DEUX CAUSES POSSIBLES, UN SEUL MESSAGE** : `transition_de_tache_invalide`
    //  (la tâche n'est pas `completed`) et `delai_d_annulation_depasse` (plus de
    //  cinq minutes). Le client ne lit que le code HTTP, jamais le corps d'erreur
    //  — même convention que `messageDeRefus` de `PanneauEditionDeContenu.tsx`.
    return (
      'L’annulation n’est plus possible : soit la tâche n’est plus terminée, soit le ' +
      'délai de cinq minutes est dépassé — seuls l’ESM, l’administrateur d’entité ou le ' +
      'super-administrateur peuvent corriger cela après ce délai.'
    );
  }
  if (statut === 404) {
    return 'Cette tâche n’existe plus dans votre parcours actuel.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

const LIBELLES_D_ETAT_DE_LA_FICHE: Readonly<Record<string, string>> = {
  draft: 'Brouillon',
  published: 'Publiée',
  archived: 'Archivée',
};

//  Chantier front, S7 (`DEC-672`) : meme convention a quatre tons que
//  `PageGestionDesEvenements.tsx`/`PageEditionEvenement.tsx` (`TONS_D_ETAT`),
//  jamais une nouvelle inventee pour cet ecran.
const TONS_D_ETAT_DE_LA_FICHE: Readonly<Record<string, 'neutre' | 'ok' | 'ko' | 'marque'>> = {
  draft: 'neutre',
  published: 'ok',
  archived: 'neutre',
};

const LIBELLES_D_ETAT_DE_LA_TACHE: Readonly<Record<string, string>> = {
  todo: 'À faire',
  completed: 'Terminée',
  reopened: 'Réouverte',
  cancelled: 'Annulée',
};

const TONS_D_ETAT_DE_LA_TACHE: Readonly<Record<string, 'neutre' | 'ok' | 'ko' | 'marque'>> = {
  todo: 'neutre',
  completed: 'ok',
  reopened: 'marque',
  cancelled: 'ko',
};

/** La section fiche d'arrivée — complétion, validation et publication. */
function SectionFiche({
  code,
  appartenance,
  fiche,
  onEnregistre,
}: {
  readonly code: string;
  readonly appartenance: string;
  readonly fiche: FicheArrivee;
  readonly onEnregistre: () => void;
}): JSX.Element {
  const [presentationDeTravail, setPresentationDeTravail] = useState(
    fiche.presentationCourte ?? '',
  );
  const [funFactDeTravail, setFunFactDeTravail] = useState(fiche.funFact ?? '');
  const [enregistrement, setEnregistrement] = useState<'repos' | 'envoi'>('repos');
  const [erreur, setErreur] = useState<string | null>(null);

  //  §6.2 : apres publication, le nouvel arrivant PERD le droit de modifier
  //  directement son profil. Aucune route n'accepterait l'ecriture (matrice
  //  §7, « Corriger apres publication » est a TIRET pour `NEW`) : proposer les
  //  champs quand meme serait l'avertissement faux du §7.21.
  const modifiable = fiche.etat === 'draft';
  const aModifie =
    modifiable &&
    (presentationDeTravail !== (fiche.presentationCourte ?? '') ||
      funFactDeTravail !== (fiche.funFact ?? ''));
  const presentationVide = presentationDeTravail.trim() === '';

  async function enregistrer(): Promise<void> {
    setEnregistrement('envoi');
    setErreur(null);
    const resultat = await completerLaFiche(code, appartenance, {
      version: fiche.version,
      short_intro: presentationDeTravail,
      //  **`exactOptionalPropertyTypes` REFUSE `fun_fact: undefined`** — la cle
      //  est donc OMISE plutot que posee a `undefined`, jamais une valeur
      //  vide envoyee au serveur comme si elle avait ete SAISIE puis effacee.
      ...(funFactDeTravail === '' ? {} : { fun_fact: funFactDeTravail }),
    });
    setEnregistrement('repos');
    if (resultat.statut === 200 && resultat.corps !== null) {
      onEnregistre();
    } else {
      setErreur(messageDeRefusDeLaFiche(resultat.statut));
    }
  }

  async function validerEtPublier(): Promise<void> {
    //  **GARDE DEFENSIVE, JAMAIS ATTEINTE** : le bouton n'est propose que si
    //  `fiche.identifiant !== null`, et la fiche d'arrivee garantit `id` et
    //  `version` nuls ENSEMBLE (voir `ficheArrivee.ts`) — donc `version` est
    //  forcement pose ici. TypeScript ne relie pas les deux champs entre eux.
    if (fiche.version === null) {
      return;
    }
    setEnregistrement('envoi');
    setErreur(null);
    const resultat = await validerEtPublierLaFiche(code, appartenance, { version: fiche.version });
    setEnregistrement('repos');
    if (resultat.statut === 200 && resultat.corps !== null) {
      onEnregistre();
    } else {
      setErreur(messageDeRefusDeLaFiche(resultat.statut));
    }
  }

  //  **AUCUNE ligne d'ecriture au §7 pour l'etat `archived`** — meme motif que
  //  la fiche publiee, mais RIEN n'est propose du tout, pas meme la lecture
  //  des champs en clair : la ligne n'existe deja plus pour personne.
  const peutValider = fiche.identifiant !== null && !presentationVide && !aModifie;

  return (
    <Carte titre="Ma fiche d’arrivée">
      <p className="onboarding-fiche-etat">
        État :{' '}
        <Badge ton={TONS_D_ETAT_DE_LA_FICHE[fiche.etat] ?? 'neutre'}>
          {LIBELLES_D_ETAT_DE_LA_FICHE[fiche.etat] ?? fiche.etat}
        </Badge>
      </p>

      <dl className="onboarding-fiche-organisation">
        <dt>Date d&rsquo;arrivée</dt>
        <dd>{dateComplete(fiche.dateDArrivee)}</dd>
        <dt>Métier</dt>
        <dd>{fiche.metier ?? 'Non renseigné'}</dd>
        <dt>Statut</dt>
        <dd>{fiche.statut ?? 'Non renseigné'}</dd>
        <dt>Client</dt>
        <dd>{fiche.client ?? 'Non renseigné'}</dd>
        <dt>DSM</dt>
        <dd>{fiche.dsm ?? 'Non renseigné'}</dd>
        <dt>Cercle principal</dt>
        <dd>{fiche.cerclePrincipal?.nom ?? 'Non renseigné'}</dd>
      </dl>

      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}

      {modifiable ? (
        <>
          <label className="onboarding-champ" htmlFor="onboarding-presentation">
            Présentation courte (obligatoire avant de valider)
            <textarea
              id="onboarding-presentation"
              onChange={(evenement) => {
                setPresentationDeTravail(evenement.target.value);
              }}
              value={presentationDeTravail}
            />
          </label>
          <label className="onboarding-champ" htmlFor="onboarding-fun-fact">
            Fun fact (facultatif)
            <input
              id="onboarding-fun-fact"
              onChange={(evenement) => {
                setFunFactDeTravail(evenement.target.value);
              }}
              type="text"
              value={funFactDeTravail}
            />
          </label>
          <div className="onboarding-fiche-actions">
            <Bouton
              disabled={!aModifie || enregistrement === 'envoi'}
              onClick={() => {
                void enregistrer();
              }}
              type="button"
              variante="secondaire"
            >
              {enregistrement === 'envoi' ? 'Enregistrement…' : 'Enregistrer'}
            </Bouton>
            <Bouton
              disabled={!peutValider || enregistrement === 'envoi'}
              onClick={() => {
                void validerEtPublier();
              }}
              type="button"
              variante="primaire"
            >
              Valider et publier
            </Bouton>
          </div>
        </>
      ) : fiche.etat === 'published' ? (
        <dl className="onboarding-fiche-lecture">
          <dt>Présentation courte</dt>
          <dd>{fiche.presentationCourte ?? 'Non renseigné'}</dd>
          <dt>Fun fact</dt>
          <dd>{fiche.funFact ?? 'Non renseigné'}</dd>
        </dl>
      ) : null}
    </Carte>
  );
}

/** Une tâche du parcours, avec ses actions `Soi` — matrice §8.1. */
function LigneDeTache({
  tache,
  actionEnCours,
  onAgir,
}: {
  readonly tache: TacheDuParcours;
  readonly actionEnCours: string | null;
  readonly onAgir: (tache: string, action: 'completion' | 'annulation') => void;
}): JSX.Element {
  const enCours = actionEnCours === tache.id;
  return (
    <li className="onboarding-tache">
      <div className="onboarding-tache-entete">
        <span className="onboarding-tache-titre">{tache.titre}</span>
        <Badge ton={TONS_D_ETAT_DE_LA_TACHE[tache.etat] ?? 'neutre'}>
          {LIBELLES_D_ETAT_DE_LA_TACHE[tache.etat] ?? tache.etat}
        </Badge>
        {tache.obligatoire ? <Badge ton="marque">Obligatoire</Badge> : null}
      </div>
      {tache.description === null ? null : (
        <p className="onboarding-tache-description">{tache.description}</p>
      )}
      <p className="onboarding-tache-echeance">Échéance : {dateComplete(tache.echeance)}</p>
      {tache.etat === 'todo' || tache.etat === 'reopened' ? (
        <Bouton
          disabled={enCours}
          onClick={() => {
            onAgir(tache.id, 'completion');
          }}
          type="button"
          variante="primaire"
        >
          {enCours ? 'Envoi…' : 'Marquer comme terminée'}
        </Bouton>
      ) : null}
      {tache.etat === 'completed' ? (
        <Bouton
          disabled={enCours}
          onClick={() => {
            onAgir(tache.id, 'annulation');
          }}
          type="button"
          variante="secondaire"
        >
          {enCours ? 'Envoi…' : 'Annuler'}
        </Bouton>
      ) : null}
    </li>
  );
}

/** La section parcours — progression comptée, jamais stockée (critère n°3 du lot). */
function SectionParcours({
  code,
  appartenance,
  parcours,
  onAgi,
}: {
  readonly code: string;
  readonly appartenance: string;
  readonly parcours: Parcours;
  readonly onAgi: () => void;
}): JSX.Element {
  const [actionEnCours, setActionEnCours] = useState<string | null>(null);
  const [erreur, setErreur] = useState<{ readonly tache: string; readonly message: string } | null>(
    null,
  );

  async function agir(tache: string, action: 'completion' | 'annulation'): Promise<void> {
    setActionEnCours(tache);
    setErreur(null);
    const resultat =
      action === 'completion'
        ? await terminerUneTache(code, appartenance, tache)
        : await annulerUneTache(code, appartenance, tache);
    setActionEnCours(null);
    if (resultat.statut === 200 && resultat.corps !== null) {
      onAgi();
    } else {
      setErreur({ tache, message: messageDeRefusDeLaTache(action, resultat.statut) });
    }
  }

  if (parcours.instance === null) {
    return (
      <Carte titre="Mon parcours">
        <Alerte urgence="information">Aucun parcours ne vous a encore été affecté.</Alerte>
      </Carte>
    );
  }

  const progression = parcours.progression;

  return (
    <Carte titre="Mon parcours">
      {progression === null ? null : (
        <p className="onboarding-progression" role="status">
          {progression.tachesObligatoiresTerminees} / {progression.tachesObligatoiresTotales} tâches
          obligatoires terminées
        </p>
      )}
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur.message}
        </Alerte>
      )}
      {parcours.taches.length === 0 ? (
        <p>Aucune tâche pour le moment.</p>
      ) : (
        <ul className="onboarding-liste-des-taches">
          {parcours.taches.map((tache) => (
            <LigneDeTache
              key={tache.id}
              tache={tache}
              actionEnCours={actionEnCours}
              onAgir={(t, a) => {
                void agir(t, a);
              }}
            />
          ))}
        </ul>
      )}
    </Carte>
  );
}

export function PageMonOnboarding(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const [charge, setCharge] = useState<Chargement | null>(null);
  const [rechargements, setRechargements] = useState(0);
  const appartenance = permissions?.appartenance ?? null;

  useEffect(() => {
    if (appartenance === null) {
      return undefined;
    }
    const cible = appartenance;
    const abandon = new AbortController();

    //  **LES DEUX APPELS PARTENT ENSEMBLE** — meme motif que `PageProfil`
    //  (LOT 5, `T11`) : la fiche et le parcours ne se commandent pas l'un
    //  l'autre, et les attendre en sequence retarderait le premier pour rien.
    async function charger(): Promise<Chargement> {
      const [fiche, parcours] = await Promise.all([
        lireLaFicheArrivee(entite.code, cible, abandon.signal),
        lireLeParcours(entite.code, cible, abandon.signal),
      ]);
      return {
        appartenance: cible,
        fiche: { statut: fiche.statut, corps: fiche.corps },
        parcours: { statut: parcours.statut, corps: parcours.corps },
      };
    }

    void charger().then(setCharge, (cause: unknown) => {
      if (!abandon.signal.aborted) {
        setCharge({
          appartenance: cible,
          fiche: { statut: 0, corps: null },
          parcours: { statut: 0, corps: null },
        });
      }
      return cause;
    });
    return () => {
      abandon.abort();
    };
  }, [entite.code, appartenance, rechargements]);

  //  **REFUS PAR DEFAUT, §20.1.** Cette page n'existe que sous la rubrique
  //  « Mon onboarding », deja masquee sans parcours actif — mais une adresse
  //  tapee a la main l'atteint quand meme (§2.6 : le frontend masque, l'API
  //  reste l'autorite), et `permissions` peut aussi n'etre pas encore arrivee.
  if (permissions === null) {
    return (
      <p className="onboarding-chargement" role="status">
        Chargement de vos droits…
      </p>
    );
  }
  if (appartenance === null) {
    return (
      <Alerte urgence="information">
        Aucun onboarding ne vous est rattaché dans {entite.nom}.
      </Alerte>
    );
  }

  if (charge === null || charge.appartenance !== appartenance) {
    return (
      <p className="onboarding-chargement" role="status">
        Chargement de votre onboarding…
      </p>
    );
  }

  const { fiche, parcours } = charge;
  if (fiche.statut !== 200 || fiche.corps === null) {
    return (
      <Alerte ton={fiche.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {fiche.statut === 401
          ? 'Votre session a expiré. Reconnectez-vous pour consulter votre onboarding.'
          : 'Votre fiche d’arrivée n’a pas pu être chargée. Réessayez dans un instant.'}
      </Alerte>
    );
  }

  function recharger(): void {
    setRechargements((precedent) => precedent + 1);
  }

  return (
    <div className="onboarding-page">
      <SectionFiche
        //  **LA CLE EST LA VERSION, PAS L'IDENTIFIANT.** Un enregistrement
        //  reussi change `fiche.version` ; remonter le composant avec une cle
        //  neuve repart des VRAIES valeurs enregistrees comme etat initial,
        //  sans `setState` synchrone dans un effet (`react-hooks/
        //  set-state-in-effect`) — meme parade que `PageProfil` : « le
        //  chargement est derive, il n'est pas un etat pose ».
        key={fiche.corps.version ?? 'brouillon'}
        code={entite.code}
        appartenance={appartenance}
        fiche={fiche.corps}
        onEnregistre={recharger}
      />
      {parcours.statut === 200 && parcours.corps !== null ? (
        <SectionParcours
          code={entite.code}
          appartenance={appartenance}
          parcours={parcours.corps}
          onAgi={recharger}
        />
      ) : (
        <Carte titre="Mon parcours">
          <Alerte ton={parcours.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
            {parcours.statut === 401
              ? 'Votre session a expiré. Reconnectez-vous pour consulter votre parcours.'
              : 'Votre parcours n’a pas pu être chargé. Réessayez dans un instant.'}
          </Alerte>
        </Carte>
      )}
    </div>
  );
}
