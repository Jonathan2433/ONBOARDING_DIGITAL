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

import { libelleDuStatut } from '../affichage';
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
import {
  Alerte,
  Avatar,
  Badge,
  Bouton,
  Carte,
  CaseACocher,
  Picto,
  Progression,
} from '@onboarding/ui';

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
  nomDeLEntite,
  onEnregistre,
}: {
  readonly code: string;
  readonly appartenance: string;
  readonly fiche: FicheArrivee;
  //  La charte 6.7 ecrit la pastille « statut · entite » : le nom descend du
  //  cadre, qui l'a deja resolu, plutot que d'etre relu ici.
  readonly nomDeLEntite: string;
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

      {/*
        **L'APERCU DE LA FICHE — charte 6.7.** En-tete sur l'aplat de bleu de
        marque : pastille jaune « statut · entite », date d'arrivee, avatar a
        anneau jaune, nom, role. C'est la forme que la fiche prendra une fois
        publiee, montree a celui qui la remplit.

        **L'AVATAR PORTE LES INITIALES, ET CE N'EST PAS UN OUBLI** : la fiche
        d'arrivee ne sert pas de photo — la photo de profil est une autre
        ressource, avec sa propre autorisation (LOT 11 `T2`). L'inventer ici
        demanderait un appel de plus et une autorisation que cet ecran n'a pas
        resolue.
      */}
      <div className="onboarding-apercu">
        <div className="onboarding-apercu-entete">
          <p className="onboarding-apercu-pastille">
            {libelleDuStatut(fiche.statut) ?? fiche.statut ?? 'Statut à venir'} · {nomDeLEntite}
          </p>
          <p className="onboarding-apercu-date">Arrivée le {dateComplete(fiche.dateDArrivee)}</p>
          <Avatar
            anneau="var(--marque-jaune)"
            nom={`${fiche.nomPrefere ?? fiche.prenom} ${fiche.nom}`}
            taille={72}
          />
          <p className="onboarding-apercu-nom">
            {fiche.nomPrefere ?? fiche.prenom} {fiche.nom}
          </p>
          <p className="onboarding-apercu-role">{fiche.metier ?? 'Métier non renseigné'}</p>
        </div>
        {/*
          Le corps en tuiles — charte 6.7. **« J'attends d'eXalt » n'y figure
          pas** : aucun champ de ce nom n'existe dans le modele, et en inventer
          un sur la fiche de quelqu'un serait mettre des mots dans sa bouche.
          Ecart consigne pour `E7`.
        */}
        <dl className="onboarding-apercu-tuiles">
          <div className="onboarding-tuile onboarding-tuile-bleu">
            <dt>Cercle</dt>
            <dd>{fiche.cerclePrincipal?.nom ?? 'Non renseigné'}</dd>
          </div>
          <div className="onboarding-tuile onboarding-tuile-bleu">
            <dt>Mission</dt>
            <dd>{fiche.client ?? 'Non renseigné'}</dd>
          </div>
          <div className="onboarding-tuile onboarding-tuile-gris">
            <dt>Qui suis-je&nbsp;?</dt>
            <dd>{fiche.presentationCourte ?? 'Non renseigné'}</dd>
          </div>
          <div className="onboarding-tuile onboarding-tuile-jaune">
            <dt>Fun fact</dt>
            <dd>{fiche.funFact ?? 'Non renseigné'}</dd>
          </div>
          <div className="onboarding-tuile onboarding-tuile-gris">
            <dt>DSM</dt>
            <dd>{fiche.dsm ?? 'Non renseigné'}</dd>
          </div>
        </dl>
        {/* Le pied de la charte 6.7 : le logo, puis la signature de marque. */}
        <p className="onboarding-apercu-pied">
          <span aria-hidden="true" className="onboarding-apercu-logo" />
          pulse, make, learn
        </p>
      </div>

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
      ) : null}
    </Carte>
  );
}

/** Une tâche du parcours, avec ses actions `Soi` — matrice §8.1. */
/**
 * Le decoupage en etapes de la charte 6.7 — `E5`, arbitrage de Jonathan du
 * 02/11/2026.
 *
 * **CES QUATRE NOMS N'EXISTENT NULLE PART DANS LE CORPUS**, et la base ne
 * stocke qu'un nombre de jours par tache de modele (`due_offset_days`). Les
 * bornes ci-dessous sont donc une DECISION, pas une lecture : elles sont
 * ecrites ici en clair pour qu'on puisse les contredire, et `E7` les consigne
 * comme a confirmer avec Lea.
 *
 * **UNE REGLE, PAS UNE LISTE** : une tache tombe dans une etape par son
 * ecart a la date de reference du parcours, donc une tache nouvelle se range
 * sans que personne y pense (§7.27). Un ecart au-dela du mois a sa propre
 * etape plutot que d'etre silencieusement range dans « Mois 1 » — une tache
 * qu'on ne verrait nulle part serait pire qu'une etape de plus.
 */
const ETAPES: readonly {
  readonly cle: string;
  readonly libelle: string;
  readonly contient: (jours: number) => boolean;
}[] = [
  { cle: 'avant', libelle: 'Avant l’arrivée', contient: (jours) => jours < 0 },
  { cle: 'jour-1', libelle: 'Jour 1', contient: (jours) => jours === 0 },
  { cle: 'semaine-1', libelle: 'Semaine 1', contient: (jours) => jours > 0 && jours <= 7 },
  { cle: 'mois-1', libelle: 'Mois 1', contient: (jours) => jours > 7 && jours <= 30 },
  { cle: 'au-dela', libelle: 'Au-delà', contient: (jours) => jours > 30 },
];

/**
 * Le nombre de jours entiers entre deux dates ISO.
 *
 * **AUCUN ANALYSEUR DE DATE N'EST APPELE.** `Date.UTC` est une fonction
 * arithmetique sur des NOMBRES : elle ne lit aucune chaine et ne consulte
 * aucun fuseau. `new Date(iso)` ferait l'inverse, et decalerait le compte d'un
 * jour selon l'heure et le lieu de celui qui regarde.
 */
function joursEntre(reference: string, echeance: string): number {
  const jour = (iso: string): number =>
    Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
  return Math.round((jour(echeance) - jour(reference)) / 86_400_000);
}

/** L'etape d'une tache, ou la derniere si son ecart ne tombe dans aucune. */
function etapeDeLaTache(reference: string, echeance: string): string {
  const jours = joursEntre(reference, echeance);
  return (ETAPES.find((etape) => etape.contient(jours)) ?? ETAPES[ETAPES.length - 1])?.cle ?? '';
}

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
  const terminee = tache.etat === 'completed';
  return (
    <li className="onboarding-tache" data-terminee={terminee ? 'oui' : 'non'}>
      <div className="onboarding-tache-entete">
        {/*
          **LA CASE A COCHER EST LA COMMANDE, PLUS UN BOUTON — charte 6.7.**
          Cocher termine la tache, decocher annule la completion : ce sont les
          deux memes appels qu'avant, derriere un seul geste au lieu de deux
          boutons. La case est DESACTIVEE quand l'API refuserait l'action — une
          tache ni `todo`, ni `reopened`, ni `completed` n'est pas actionnable
          — plutot que de proposer un droit deja refuse.

          **LE LIBELLE DE LA CASE EST LE TITRE DE LA TACHE**, ce qui lui donne
          son nom accessible : sans lui, cent cases porteraient le meme nom.
        */}
        <CaseACocher
          checked={terminee}
          disabled={enCours || !(terminee || tache.etat === 'todo' || tache.etat === 'reopened')}
          libelle={tache.titre}
          onChange={() => {
            onAgir(tache.id, terminee ? 'annulation' : 'completion');
          }}
        />
        <Badge ton={TONS_D_ETAT_DE_LA_TACHE[tache.etat] ?? 'neutre'}>
          {LIBELLES_D_ETAT_DE_LA_TACHE[tache.etat] ?? tache.etat}
        </Badge>
        {tache.obligatoire ? <Badge ton="marque">Obligatoire</Badge> : null}
      </div>
      {tache.description === null ? null : (
        <p className="onboarding-tache-description">{tache.description}</p>
      )}
      <p className="onboarding-tache-echeance">Échéance : {dateComplete(tache.echeance)}</p>
      {enCours ? (
        <p className="onboarding-tache-envoi" role="status">
          Envoi…
        </p>
      ) : null}
    </li>
  );
}

/** La section parcours — progression comptée, jamais stockée (critère n°3 du lot). */
function SectionParcours({
  code,
  appartenance,
  parcours,
  statut,
  onAgi,
}: {
  readonly code: string;
  readonly appartenance: string;
  readonly parcours: Parcours;
  //  Le statut professionnel, qui vit sur la FICHE et non sur le parcours : la
  //  charte 6.7 l'affiche dans le bandeau, « Parcours · En mission ».
  readonly statut: string | null;
  readonly onAgi: () => void;
}): JSX.Element {
  const [etapeActive, poserEtapeActive] = useState<string | null>(null);
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
  const reference = parcours.instance.dateDeReference;

  //  **LES ETAPES MONTREES SONT CELLES QUI PORTENT UNE TACHE**, derivees des
  //  echeances reelles : une pastille qui ouvrirait un panneau vide ne dirait
  //  rien, et le parcours de chaque entite n'a pas les memes jalons.
  const etapesPeuplees = ETAPES.filter((etape) =>
    parcours.taches.some((tache) => etapeDeLaTache(reference, tache.echeance) === etape.cle),
  );
  //  `null` veut dire « toutes » : c'est l'etat de depart, et il reste
  //  atteignable — sans quoi on ne pourrait plus voir le parcours entier.
  const tachesMontrees =
    etapeActive === null
      ? parcours.taches
      : parcours.taches.filter(
          (tache) => etapeDeLaTache(reference, tache.echeance) === etapeActive,
        );

  const pourcentage =
    progression === null || progression.tachesObligatoiresTotales === 0
      ? null
      : Math.round(
          (progression.tachesObligatoiresTerminees / progression.tachesObligatoiresTotales) * 100,
        );

  return (
    <>
      {/*
        **LE BANDEAU DE PARCOURS — charte 6.7.** Aplat de bleu de marque,
        pictogramme `profil-valide`, et le statut professionnel a cote du mot
        « Parcours ».

        **LE BOUTON « CHANGER » DE LA CHARTE N'EST PAS POSE**, sur arbitrage
        explicite de Jonathan du 02/11/2026 : changer son propre statut n'est
        pas un droit que la matrice §6.1 accorde a `Soi` — c'est le DSM ou
        l'entite qui le fait. Proposer un geste que l'API refuserait est
        exactement ce que ce depot s'interdit partout ailleurs.
      */}
      <section className="onboarding-bandeau" aria-labelledby="onboarding-bandeau-titre">
        <Picto nom="profil-valide" taille={32} />
        <h2 className="onboarding-bandeau-titre" id="onboarding-bandeau-titre">
          Parcours
          {statut === null ? null : <> · {libelleDuStatut(statut) ?? statut}</>}
        </h2>
      </section>

      <Carte titre="Ma checklist">
        {progression === null ? null : (
          <div className="onboarding-compte">
            <p className="onboarding-compte-texte" role="status">
              {progression.tachesObligatoiresTerminees} / {progression.tachesObligatoiresTotales}{' '}
              tâches obligatoires terminées
            </p>
            {pourcentage === null ? null : (
              <span aria-hidden="true" className="onboarding-compte-pourcentage">
                {pourcentage}%
              </span>
            )}
            {/*
              **`Progression` COMPTE, IL NE STOCKE RIEN** — critere n°3 du
              LOT 7. Son libelle porte l'information pour qui ne voit pas la
              piste, et le gros chiffre a cote est donc `aria-hidden` : sans
              cela, le meme nombre serait annonce deux fois.
            */}
            <Progression
              faites={progression.tachesObligatoiresTerminees}
              libelle="Progression de vos tâches obligatoires"
              total={progression.tachesObligatoiresTotales}
            />
          </div>
        )}

        {/*
          **LE SELECTEUR D'ETAPES — charte 6.7.** Des boutons, donc atteignables
          au clavier par construction. `aria-pressed` porte l'etat : la pastille
          bleue ne le dit pas toute seule (§14.2).
        */}
        {etapesPeuplees.length === 0 ? null : (
          <div className="onboarding-etapes" role="group" aria-label="Étapes du parcours">
            <button
              aria-pressed={etapeActive === null}
              className="onboarding-etape"
              onClick={() => {
                poserEtapeActive(null);
              }}
              type="button"
            >
              Toutes
            </button>
            {etapesPeuplees.map((etape) => (
              <button
                aria-pressed={etapeActive === etape.cle}
                className="onboarding-etape"
                key={etape.cle}
                onClick={() => {
                  poserEtapeActive(etape.cle);
                }}
                type="button"
              >
                {etape.libelle}
              </button>
            ))}
          </div>
        )}

        {erreur === null ? null : (
          <Alerte ton="erreur" urgence="alerte">
            {erreur.message}
          </Alerte>
        )}
        {tachesMontrees.length === 0 ? (
          <p>Aucune tâche pour le moment.</p>
        ) : (
          <ul className="onboarding-liste-des-taches">
            {tachesMontrees.map((tache) => (
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

        {/*
          **LA LIGNE « REUNION CLE » DE LA CHARTE 6.7, EN ATTENTE.** Aucune
          reunion n'existe dans le modele : ni le parcours ni la fiche n'en
          portent. L'emplacement est pose avec son contenu annonce, comme a
          l'accueil et au bloc Vision — arbitrage de Jonathan du 02/11/2026.

          **LE BOUTON EST INERTE ET LE DIT.** Second arbitrage du meme jour :
          le cahier reporte Teams en V1 et la liste des interdits du MVP le
          nomme. `disabled` plutot qu'un clic sans effet, et la mention « a
          venir » juste a cote — un bouton qui ne reagit pas sans rien dire
          serait lu comme une panne.
        */}
        <div className="onboarding-reunion">
          <span className="onboarding-reunion-titre">Réunion clé</span>
          <Badge ton="info">À venir</Badge>
          <p className="onboarding-reunion-texte">
            Vos rendez-vous d’intégration prendront place ici, avec leur horaire.
          </p>
          <Bouton disabled taille="s" type="button" variante="discret">
            Caler dans Teams
          </Bouton>
        </div>
      </Carte>
    </>
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
        nomDeLEntite={entite.nom}
        onEnregistre={recharger}
      />
      {parcours.statut === 200 && parcours.corps !== null ? (
        <SectionParcours
          code={entite.code}
          appartenance={appartenance}
          parcours={parcours.corps}
          statut={fiche.corps.statut}
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
