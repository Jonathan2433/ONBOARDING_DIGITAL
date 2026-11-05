/**
 * L'accueil d'une entite — LOT 4, `T2`/`T3` ; LOT 8, `T11` compose l'agregat,
 * `T12` ajoute les carrousels mobiles.
 *
 * `T12` : TROIS LISTES DEVIENNENT DES CARROUSELS — `US005` EST REPORTEE
 *
 *   Arrivees recentes, evenements a venir et liens internes passent de `<ul>`
 *   brutes a `<Carrousel>` (`@onboarding/ui`) : meme contenu, memes `<li>`,
 *   mais une piste qui defile sur mobile (cahier §13.3/§13.4, « carrousels
 *   manuels et accessibles ») et redevient une liste verticale a partir de
 *   768 px — aucune duplication de marquage, seul le CSS tranche.
 *
 *   Les liens internes n'avaient JAMAIS ete bornes par `NOMBRE_MONTRE` — la
 *   liste entiere s'affichait deja, sans "voir plus" — ce qui en fait, sur
 *   mobile, le candidat le plus sujet a un defilement vertical sans fin.
 *
 *   `US005` (« video d'accueil sur action ») est explicitement REPORTEE,
 *   arbitrage de Jonathan du 06/10/2026 : aucune convention de `payload_json`
 *   n'existe pour un bloc `VIDEO` — ni dans une seule fixture du depot — et
 *   `QO-121` reste ouverte. L'inventer maintenant serait §6.5 ; `CONT-026`
 *   confirme par ailleurs qu'aucune video reelle n'existera avant la V1.
 *
 * `T11` : LES CINQ SECTIONS DU CAHIER §8.4, DANS L'ORDRE, VIA L'AGREGAT DE `T8`
 *
 *   `T8` (LOT 8) a pose `GET …/accueil`, qui compose presentation, Framework,
 *   arrivees recentes, evenements a venir et liens internes en appelant
 *   directement les cinq services deja construits par leurs propres
 *   sous-etapes — jamais recopier leurs regles (§7.0, sixieme proposition).
 *   `T11` est le premier et SEUL ecran a consommer cet agregat : jusqu'ici,
 *   seule la presentation etait rendue (en EDITION), et les quatre autres
 *   sections n'etaient qu'un texte annoncant leur arrivee « progressive ».
 *
 *   Chaque section est une `<Carte titre="…">` — une region nommee du design
 *   system, jamais un `<h1>` : le cadre en porte deja un, une fois, pour
 *   toutes les pages internes (meme motif que l'en-tete historique de ce
 *   fichier).
 *
 * LA PRESENTATION EST EN LECTURE SEULE SUR L'ACCUEIL
 *
 *   Les blocs de `donnee.presentation` sont visibles aux huit roles de la
 *   matrice. Leur administration reste dans le back-office : afficher le
 *   formulaire editorial ici transformait l'accueil d'un ESM en ecran de
 *   gestion et repoussait le parcours d'onboarding et les evenements.
 *
 * LES BLOCS SE LISENT PAR `texteDuBloc(bloc, 'texte')`, PAS PAR INVENTION
 *
 *   `QO-121` reste ouverte : le corpus ne nomme AUCUNE clef de
 *   `payload_json`. `texte` n'est pas invente ici — c'est la clef que
 *   TOUTES les fixtures du depot emploient deja pour un contenu textuel
 *   (`test_ecriture_des_contenus.py`, `gestionDuContenu.test.ts`,
 *   `PanneauEditionDeContenu.test.tsx`), reprise plutot que devinee a
 *   nouveau. Un bloc sans cette clef ne rend rien — visible par son
 *   absence, jamais une chaine inventee a sa place.
 *
 * LE NOMBRE D'ELEMENTS MONTRES EST UN CHOIX DE CETTE SOUS-ETAPE, PAS INVENTE
 *
 *   Ni le cahier, ni la matrice, ni `T8` ne nomment de borne : `T8` le disait
 *   explicitement, « delibere, a T11/T12 ». Chaque section plafonne donc a
 *   `NOMBRE_MONTRE` et propose un lien vers l'ecran complet au-dela — la
 *   piste `T12` reste bornee a ce meme plafond, son carrousel n'etant pas
 *   un pagineur de plus.
 *
 * L'OUVERTURE EXTERNE EST EXPLICITE — `MVP-L08-US006` (2/2)
 *
 *   Le critere d'acceptation dit « indiquent clairement l'ouverture
 *   externe », sans imposer de mecanisme. Chaque lien servable s'ouvre dans
 *   un nouvel onglet (`target="_blank" rel="noopener noreferrer"`) et porte
 *   une mention TEXTUELLE visible, jamais une icone seule (meme discipline
 *   que `Badge`, WCAG 1.4.1). `urlEstServable` reste la TROISIEME barriere
 *   d'affichage (voir `liens.ts`) : un lien refuse s'affiche desactive et
 *   visible, jamais silencieusement absent.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { lireLAccueil } from '../api/accueil';
import { plageDeLEvenement } from '../affichage';
import {
  CHEMINS,
  cheminDeRubrique,
  cheminDuProfilALEcran,
  cheminGestionDesLiensALEcran,
} from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { dateComplete } from './PageProfil';

import {
  type AccueilDEntite,
  type EvenementDuClassement,
  type TitulaireFramework,
  peutGererLesLiensInternes,
  texteDuBloc,
  urlEstServable,
} from '@onboarding/contracts';
import { Alerte, Avatar, Badge, Carrousel, Carte, Pastille } from '@onboarding/ui';

/** Aucune borne n'est nommee par le corpus — voir l'en-tete. */
const NOMBRE_MONTRE = 5;

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'accueil'; readonly donnee: AccueilDEntite }
  | { readonly phase: 'erreur'; readonly statut: number };

const MOIS_COURTS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
] as const;

function typeDEvenement(evenement: EvenementDuClassement): string {
  const titre = evenement.titre.toLocaleLowerCase('fr');
  if (titre.includes('exaltemps')) return '⚡ eXaltemps';
  if (titre.includes('gala') || titre.includes("fin d'année")) return '✨ Soirée eXalt';
  return '🎉 Vie des bureaux';
}

function compteARebours(
  iso: string,
  maintenant: number,
): readonly [number, number, number, number] {
  const secondes = Math.max(0, Math.floor((Date.parse(iso) - maintenant) / 1000));
  const jours = Math.floor(secondes / 86_400);
  const heures = Math.floor((secondes % 86_400) / 3_600);
  const minutes = Math.floor((secondes % 3_600) / 60);
  return [jours, heures, minutes, secondes % 60];
}

function decalerLeMois(cle: string, delta: number): string {
  const [anneeBrute, moisBrut] = cle.split('-');
  const date = new Date(Date.UTC(Number(anneeBrute), Number(moisBrut) - 1 + delta, 1));
  return `${String(date.getUTCFullYear())}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

function TempsForts({
  evenements,
  codeEntite,
}: {
  evenements: readonly EvenementDuClassement[];
  codeEntite: string;
}): JSX.Element {
  const prochain = evenements[0] ?? null;
  const [maintenant, setMaintenant] = useState(() => Date.now());
  const [moisAffiche, setMoisAffiche] = useState(
    () => prochain?.commenceLe.slice(0, 7) ?? new Date().toISOString().slice(0, 7),
  );
  const [evenementSelectionne, setEvenementSelectionne] = useState<string | null>(
    prochain?.identifiant ?? null,
  );
  const aUnProchainEvenement = prochain !== null;

  useEffect(() => {
    if (!aUnProchainEvenement) return undefined;
    const minuteur = window.setInterval(() => {
      setMaintenant(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(minuteur);
    };
  }, [aUnProchainEvenement]);

  if (evenements.length === 0) {
    return (
      <Carte titre="Les moments à ne pas manquer">
        <Alerte>Aucun événement à venir pour le moment.</Alerte>
      </Carte>
    );
  }
  if (prochain === null) return <></>;
  const [jours, heures, minutes, secondes] = compteARebours(prochain.commenceLe, maintenant);
  const annee = Number(moisAffiche.slice(0, 4));
  const mois = Number(moisAffiche.slice(5, 7));
  const joursDansLeMois = new Date(Date.UTC(annee, mois, 0)).getUTCDate();
  const premierJour = (new Date(Date.UTC(annee, mois - 1, 1)).getUTCDay() + 6) % 7;
  const evenementsDuMois = evenements.filter(
    (evenement) => evenement.commenceLe.slice(0, 7) === moisAffiche,
  );
  const evenementParJour = new Map(
    evenementsDuMois.map((evenement) => [Number(evenement.commenceLe.slice(8, 10)), evenement]),
  );
  const moisDisponibles = evenements.map((evenement) => evenement.commenceLe.slice(0, 7)).sort();
  const premierMois = moisDisponibles[0] ?? moisAffiche;
  const dernierMois = moisDisponibles.at(-1) ?? moisAffiche;
  const selection =
    evenements.find((evenement) => evenement.identifiant === evenementSelectionne) ?? prochain;

  function afficherLeMois(cle: string): void {
    setMoisAffiche(cle);
    const premierDuMois = evenements.find((evenement) => evenement.commenceLe.slice(0, 7) === cle);
    if (premierDuMois !== undefined) setEvenementSelectionne(premierDuMois.identifiant);
  }

  return (
    <section className="temps-forts" aria-labelledby="temps-forts-titre">
      <header className="temps-forts-hero">
        <div>
          <span className="temps-forts-pastille">● ⚡ Nos temps forts</span>
          <h2 id="temps-forts-titre">Les moments à ne pas manquer</h2>
          <p>
            Prochain rendez-vous : <strong>{prochain.titre}</strong> —{' '}
            {plageDeLEvenement(prochain.commenceLe, prochain.finitLe)}
          </p>
        </div>
        <div className="temps-forts-compte" aria-label={`Compte à rebours avant ${prochain.titre}`}>
          <strong>Le compte à rebours est lancé</strong>
          <div>
            {[
              [jours, 'jours'],
              [heures, 'heures'],
              [minutes, 'min'],
              [secondes, 'sec'],
            ].map(([valeur, unite]) => (
              <span key={unite}>
                <b>{String(valeur).padStart(2, '0')}</b>
                <small>{unite}</small>
              </span>
            ))}
          </div>
        </div>
        <div className="temps-forts-defile" aria-hidden="true">
          <div className="temps-forts-defile-piste">
            {[false, true].map((estUneCopie) => (
              <div
                className="temps-forts-defile-groupe"
                data-copie={estUneCopie ? 'true' : 'false'}
                key={estUneCopie ? 'copie' : 'original'}
              >
                {evenements.map((evenement) => (
                  <span key={evenement.identifiant}>● {evenement.titre}</span>
                ))}
              </div>
            ))}
          </div>
        </div>
      </header>

      <h3 className="temps-forts-affiche">🎟️ À l&rsquo;affiche</h3>
      <div className="temps-forts-vedettes">
        {evenements.slice(0, 2).map((evenement, rang) => (
          <article className="temps-forts-vedette" key={evenement.identifiant}>
            {evenement.image === null ? (
              <div className={`temps-forts-poster temps-forts-poster-${String(rang + 1)}`}>
                <span>{evenement.titre}</span>
              </div>
            ) : (
              <img alt="" className="temps-forts-poster" src={evenement.image} />
            )}
            <div>
              <span className="temps-forts-type">{typeDEvenement(evenement)}</span>
              <h4>{evenement.titre}</h4>
              {evenement.etat === 'cancelled' ? <Badge ton="annule">Annulé</Badge> : null}
              <strong>{plageDeLEvenement(evenement.commenceLe, evenement.finitLe)}</strong>
              {evenement.lieu === null ? null : <p>📍 {evenement.lieu}</p>}
              {evenement.description === null ? null : <p>{evenement.description}</p>}
            </div>
          </article>
        ))}
      </div>

      <p className="temps-forts-explication">
        📅 Les dates entourées sont à bloquer dans ton agenda. Clique sur un événement pour le
        détail.
      </p>
      <div className="temps-forts-bas">
        <section className="temps-forts-calendrier" aria-label="Calendrier des temps forts">
          <header className="temps-forts-calendrier-entete">
            <button
              aria-label="Afficher le mois précédent"
              disabled={moisAffiche <= premierMois}
              onClick={() => {
                afficherLeMois(decalerLeMois(moisAffiche, -1));
              }}
              type="button"
            >
              ‹
            </button>
            <h3>
              {MOIS_COURTS[mois - 1]} {annee}
            </h3>
            <button
              aria-label="Afficher le mois suivant"
              disabled={moisAffiche >= dernierMois}
              onClick={() => {
                afficherLeMois(decalerLeMois(moisAffiche, 1));
              }}
              type="button"
            >
              ›
            </button>
          </header>
          <div className="temps-forts-semaine" aria-hidden="true">
            {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map((jour, rang) => (
              <span key={`${jour}-${String(rang)}`}>{jour}</span>
            ))}
          </div>
          <div className="temps-forts-jours">
            {Array.from({ length: premierJour }, (_, i) => (
              <span key={`vide-${String(i)}`} />
            ))}
            {Array.from({ length: joursDansLeMois }, (_, i) => i + 1).map((jour) => {
              const evenement = evenementParJour.get(jour);
              return evenement === undefined ? (
                <span key={jour}>{jour}</span>
              ) : (
                <button
                  aria-label={`${evenement.titre}, ${plageDeLEvenement(evenement.commenceLe, evenement.finitLe)}`}
                  aria-pressed={selection.identifiant === evenement.identifiant}
                  className="date-evenement"
                  key={jour}
                  onClick={() => {
                    setEvenementSelectionne(evenement.identifiant);
                  }}
                  type="button"
                >
                  {jour}
                </button>
              );
            })}
          </div>
          <article aria-live="polite" className="temps-forts-selection">
            <strong>{selection.titre}</strong>
            <span>{plageDeLEvenement(selection.commenceLe, selection.finitLe)}</span>
            {selection.lieu === null ? null : <span>📍 {selection.lieu}</span>}
            {selection.description === null ? null : <p>{selection.description}</p>}
          </article>
        </section>

        <section className="temps-forts-liste" aria-labelledby="prochains-rendez-vous">
          <h3 id="prochains-rendez-vous">🔥 Prochains rendez-vous</h3>
          <ul>
            {evenements.map((evenement) => (
              <li key={evenement.identifiant}>
                <span>{typeDEvenement(evenement)}</span>
                <strong>{evenement.titre}</strong>
                <small>{plageDeLEvenement(evenement.commenceLe, evenement.finitLe)}</small>
              </li>
            ))}
          </ul>
        </section>

        <aside className="temps-forts-infos">
          <div className="temps-forts-info-rose">
            <strong>⚡ C&rsquo;est quoi un eXaltemps ?</strong>
            <p>
              Les eXaltemps sont les temps forts de la vie eXalt : des moments où toute
              l&rsquo;agence se retrouve, pour partager, s&rsquo;aligner et célébrer ensemble.
            </p>
          </div>
          <div className="temps-forts-info-bleu">
            <strong>✅ Obligatoire pour les nouveaux</strong>
            <p>
              Journée d&rsquo;intégration nationale à Paris. La date te sera communiquée à ton
              arrivée.
            </p>
          </div>
        </aside>
      </div>
      <Link className="app-lien" to={cheminDeRubrique(codeEntite, 'evenements')}>
        Voir tous les événements
      </Link>
    </section>
  );
}

function MotDeLaDirection({
  titulaires,
}: {
  titulaires: readonly TitulaireFramework[];
}): JSX.Element {
  return (
    <section className="accueil-direction" aria-labelledby="accueil-direction-titre">
      <header>
        <div>
          <span>DIRECTION</span>
          <h2 id="accueil-direction-titre">Le mot de la direction</h2>
        </div>
        <p>Julie, Omar et Mathéa te souhaitent la bienvenue chez eXalt Bordeaux.</p>
      </header>
      <div className="accueil-direction-personnes">
        {titulaires.map((titulaire) => (
          <article key={titulaire.identifiant}>
            <div className="accueil-direction-identite">
              <Avatar
                nom={`${titulaire.prenom} ${titulaire.nom}`}
                taille={56}
                {...(titulaire.photo === null ? {} : { photo: titulaire.photo })}
              />
              <div>
                <strong>
                  {titulaire.prenom} {titulaire.nom}
                </strong>
                <span>Direction eXalt Bordeaux</span>
              </div>
            </div>
            <div className="accueil-direction-video">
              <span aria-hidden="true">▶</span>
              <strong>Vidéo {titulaire.prenom}</strong>
              <small>À ajouter depuis l&rsquo;administration</small>
            </div>
          </article>
        ))}
      </div>
      <div className="accueil-reperes">
        <article>
          <h3>Une agence locale</h3>
          <p>Une communauté bordelaise structurée autour des expertises et de la proximité.</p>
        </article>
        <article>
          <h3>Un repère onboarding</h3>
          <p>
            Un point d&rsquo;entrée simple pour comprendre qui fait quoi et vers qui se tourner.
          </p>
        </article>
        <article>
          <h3>Des équipes claires</h3>
          <p>
            DSM, cercles d&rsquo;expertise et Framework sont accessibles depuis cette interface.
          </p>
        </article>
        <article>
          <h3>🌟 Nos temps forts</h3>
          <p>
            eXaltemps, vie des bureaux, journée d&rsquo;intégration… Découvre les moments forts.
          </p>
          <a href="#temps-forts-titre">Découvrir →</a>
        </article>
      </div>
    </section>
  );
}

export function PageEntite(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const roles = permissions?.roles ?? null;
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    const abandon = new AbortController();
    void lireLAccueil(entite.code, abandon.signal).then(
      (reponse) => {
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'accueil', donnee: reponse.corps }
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
  }, [entite.code]);

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement de l&rsquo;accueil…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {etat.statut === 401
          ? 'Votre session a expire. Reconnectez-vous pour consulter l’accueil.'
          : "L'accueil n'a pas pu etre charge. Cela ne dit rien de son contenu : verifiez votre connexion, puis reessayez."}
      </Alerte>
    );
  }

  const { donnee } = etat;
  const peutGererLesLiens = roles !== null && peutGererLesLiensInternes(roles);
  const nombreDeResponsabilitesPourvues = donnee.framework.responsabilites.filter(
    (responsabilite) => responsabilite.titulaires.length > 0,
  ).length;
  const direction =
    donnee.framework.responsabilites.find(
      (responsabilite) => responsabilite.typeDeResponsabilite === 'DIRECTION',
    )?.titulaires ?? [];

  return (
    <div className="accueil">
      {/*
        **1. L'EN-TETE DE L'ENTITE — charte 6.2, `E5`.** Pastille, nom de
        l'entite, puis l'introduction. Le contenu lu est EXACTEMENT celui que
        `T11` du LOT 8 servait deja : seule sa presentation change.

        **LE TITRE EST UN `h2`, PAS LE `h1` QUE LA CHARTE ECRIT.** Le `h1` de
        chaque page interne appartient au cadre applicatif (`app-titre`, `T3` du
        LOT 4) et dit ou l'on se trouve. En poser un second ici donnerait DEUX
        `h1` a la meme page, ce que le §14.2 refuse — et le nom de l'entite est
        deja annonce par l'en-tete. Il garde en revanche la taille que la charte
        lui donne : c'est une question de rang, pas de corps.
      */}
      <section className="accueil-hero" aria-labelledby="accueil-hero-titre">
        <Pastille>Presentation de l&rsquo;entite</Pastille>
        <h2 className="accueil-hero-titre" id="accueil-hero-titre">
          {entite.nom}
        </h2>
        <div className="accueil-hero-intro">
          {donnee.presentation === null ? (
            <Alerte urgence="information">Aucun contenu de presentation pour le moment.</Alerte>
          ) : (
            donnee.presentation.blocs.map((bloc) => {
              const texte = texteDuBloc(bloc, 'texte');
              return texte === '' ? null : (
                <p key={bloc.identifiant} className="accueil-presentation-bloc">
                  {texte}
                </p>
              );
            })
          )}
        </div>
      </section>

      <MotDeLaDirection titulaires={direction} />

      {/*
        **2. LA GRILLE A DEUX COLONNES DE LA CHARTE 6.2, EN ATTENTE DE SON
        CONTENU.** Arbitrage explicite de Jonathan du 02/11/2026 : la video et
        les textes des tuiles sont prevus pour la V1, et l'emplacement est pose
        des maintenant plutot que laisse de cote.

        **CE QUI EST POSE DIT QU'IL EST VIDE, ET NE FAIT SEMBLANT DE RIEN.** Ni
        faux texte, ni image d'illustration : chaque pave nomme ce qu'il
        recevra. Un placeholder qui imiterait du contenu reel se retrouverait
        dans une demonstration client en passant pour un livrable.

        La video est reportee depuis le 25/09/2026 (`MVP-L08-US005`), et
        `QO-121` — ce qu'un bloc `VIDEO` porte dans ses donnees — reste ouverte :
        rien ici ne la tranche.

        **AUCUNE ANIMATION PULSEE SUR L'APPEL A L'ACTION**, la charte 6.2
        l'ecrit explicitement, et le §14.2 la refuserait de toute facon.
      */}
      <section className="accueil-onboarding" aria-labelledby="accueil-onboarding-titre">
        <div>
          <span>🚀 Tu viens d&rsquo;arriver chez eXalt Bordeaux ?</span>
          <h2 id="accueil-onboarding-titre">Découvre ton parcours d&rsquo;onboarding</h2>
          <p>
            Ta fiche d&rsquo;arrivée, ta checklist personnalisée (intercontrat ou mission) et tes
            réunions clés — tout est ici.
          </p>
        </div>
        <Link
          className="accueil-onboarding-action"
          to={cheminDeRubrique(entite.code, 'mon-onboarding')}
        >
          Commencer mon onboarding →
        </Link>
      </section>

      <TempsForts
        key={donnee.evenementsAVenir.evenements.map((evenement) => evenement.identifiant).join(':')}
        codeEntite={entite.code}
        evenements={donnee.evenementsAVenir.evenements}
      />

      {/* 2. Framework, cercles et bureaux — cahier §8.4. Chantier front, S4
         (`DEC-672`) : trois compteurs en `Badge`, plutot qu'une seule phrase
         prose — cahier §13.2, « badges ». */}
      <Carte titre="Framework">
        <div className="accueil-framework-compteurs">
          <Badge ton="info">
            {donnee.framework.cercles.length} cercle
            {donnee.framework.cercles.length > 1 ? 's' : ''}
          </Badge>
          <Badge ton="info">
            {donnee.framework.bureaux.length} bureau
            {donnee.framework.bureaux.length > 1 ? 'x' : ''}
          </Badge>
          <Badge ton="info">
            {nombreDeResponsabilitesPourvues} responsabilite
            {nombreDeResponsabilitesPourvues > 1 ? 's' : ''} pourvue
            {nombreDeResponsabilitesPourvues > 1 ? 's' : ''}
          </Badge>
        </div>
        <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
          Voir la page Framework
        </Link>
      </Carte>

      {/* 3. Personnes recemment arrivees — cahier §8.4. Le compteur en `Badge`
         n'apparait qu'avec le carrousel : la section vide porte deja son
         message dans l'Alerte, un badge « 0 » a cote serait redondant. */}
      <Carte titre="Arrivees recentes">
        {donnee.arriveesRecentes.arrivees.length === 0 ? (
          <Alerte>Aucune arrivee recente pour le moment.</Alerte>
        ) : (
          <>
            <p className="accueil-compteur">
              <Badge ton="info">
                {donnee.arriveesRecentes.total} arrivee
                {donnee.arriveesRecentes.total > 1 ? 's' : ''}
              </Badge>
            </p>
            <Carrousel libelle="Arrivees recentes">
              {donnee.arriveesRecentes.arrivees.slice(0, NOMBRE_MONTRE).map((arrivee) => (
                <li
                  key={arrivee.appartenance}
                  className="ui-carrousel__item accueil-arrivees-carte"
                >
                  <Link
                    className="app-lien"
                    to={cheminDuProfilALEcran(entite.code, arrivee.appartenance)}
                  >
                    {arrivee.nomPrefere ?? arrivee.prenom} {arrivee.nom}
                  </Link>
                  <span className="accueil-arrivees-date">
                    Arrive le {dateComplete(arrivee.dateArrivee)}
                  </span>
                </li>
              ))}
            </Carrousel>
          </>
        )}
        {donnee.arriveesRecentes.total > NOMBRE_MONTRE ? (
          <Link className="app-lien" to={cheminDeRubrique(entite.code, 'trombinoscope')}>
            Voir le trombinoscope
          </Link>
        ) : null}
      </Carte>

      {/* 5. Cartes vers le Hub, eXalt Academy et SharePoint — cahier §8.4, `MVP-L08-US006` (2/2) */}
      <Carte titre="Ressources internes">
        {donnee.liensInternes.liens.length === 0 ? (
          <Alerte>Aucune ressource interne configuree pour le moment.</Alerte>
        ) : (
          <Carrousel libelle="Ressources internes">
            {donnee.liensInternes.liens.map((lien) => {
              const servable = urlEstServable(lien.url);
              return (
                <li key={lien.identifiant} className="ui-carrousel__item accueil-liens-carte">
                  {servable ? (
                    <a
                      className="accueil-liens-lien"
                      href={lien.url}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      <span className="accueil-liens-libelle">{lien.libelle}</span>
                      <span className="accueil-liens-mention">Ouvre dans un nouvel onglet</span>
                    </a>
                  ) : (
                    <span className="accueil-liens-lien accueil-liens-lien-desactive">
                      <span className="accueil-liens-libelle">{lien.libelle}</span>
                      <span className="accueil-liens-mention">Adresse non affichable</span>
                    </span>
                  )}
                  {lien.description === null ? null : (
                    <p className="accueil-liens-description">{lien.description}</p>
                  )}
                </li>
              );
            })}
          </Carrousel>
        )}
        {peutGererLesLiens ? (
          <Link className="app-lien" to={cheminGestionDesLiensALEcran(entite.code)}>
            Gerer les liens internes
          </Link>
        ) : null}
      </Carte>

      <ul className="app-liens">
        <li>
          <Link className="app-lien" to={CHEMINS.statut}>
            Revenir a la liste des entites
          </Link>
        </li>
      </ul>
    </div>
  );
}
