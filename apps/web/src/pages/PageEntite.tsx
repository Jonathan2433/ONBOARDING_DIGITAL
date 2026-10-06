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
 * LA PRESENTATION RESTE EDITABLE, ET C'EST UNE COMPOSITION DE DEUX REGIMES
 *
 *   Le rendu LECTURE (les blocs de `donnee.presentation`, visibles aux HUIT
 *   roles — matrice §5) et le panneau D'EDITION (`PanneauEditionDeContenu`,
 *   `T10` du LOT 6, deja gate par `peutEditerUnContenu`) coexistent : avant
 *   `T11`, un role SANS droit d'edition ne voyait STRICTEMENT RIEN de la
 *   presentation, le panneau rendant `null` pour lui. C'est exactement le
 *   trou que l'agregat comble — la matrice donne « Lecture » a tous, et
 *   `PanneauEditionDeContenu` n'a jamais porte que l'edition.
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
import { PanneauEditionDeContenu } from './PanneauEditionDeContenu';

import {
  type AccueilDEntite,
  peutGererLesLiensInternes,
  texteDuBloc,
  urlEstServable,
} from '@onboarding/contracts';
import { Alerte, Badge, Carrousel, Carte } from '@onboarding/ui';

/** Aucune borne n'est nommee par le corpus — voir l'en-tete. */
const NOMBRE_MONTRE = 5;

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'accueil'; readonly donnee: AccueilDEntite }
  | { readonly phase: 'erreur'; readonly statut: number };

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

  return (
    <div className="accueil">
      {/* 1. Presentation locale — cahier §8.4 */}
      <Carte titre="Presentation">
        {donnee.presentation === null ? (
          <Alerte urgence="information">Aucun contenu de presentation pour le moment.</Alerte>
        ) : (
          <div className="accueil-presentation-blocs">
            {donnee.presentation.blocs.map((bloc) => {
              const texte = texteDuBloc(bloc, 'texte');
              return texte === '' ? null : (
                <p key={bloc.identifiant} className="accueil-presentation-bloc">
                  {texte}
                </p>
              );
            })}
          </div>
        )}
        <PanneauEditionDeContenu
          cibleCorrespond={(page) => page.typeDePage === 'HOME' && page.slug === 'presentation'}
          codeEntite={entite.code}
          demandeDeCreation={{ type_de_page: 'HOME', titre: entite.nom, slug: 'presentation' }}
          roles={roles}
        />
      </Carte>

      {/* 2. Framework, cercles et bureaux — cahier §8.4 */}
      <Carte titre="Framework">
        <p className="accueil-framework-resume">
          {donnee.framework.cercles.length} cercle
          {donnee.framework.cercles.length > 1 ? 's' : ''}, {donnee.framework.bureaux.length} bureau
          {donnee.framework.bureaux.length > 1 ? 'x' : ''}, {nombreDeResponsabilitesPourvues}{' '}
          responsabilite{nombreDeResponsabilitesPourvues > 1 ? 's' : ''} pourvue
          {nombreDeResponsabilitesPourvues > 1 ? 's' : ''}.
        </p>
        <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
          Voir la page Framework
        </Link>
      </Carte>

      {/* 3. Personnes recemment arrivees — cahier §8.4 */}
      <Carte titre="Arrivees recentes">
        {donnee.arriveesRecentes.arrivees.length === 0 ? (
          <Alerte>Aucune arrivee recente pour le moment.</Alerte>
        ) : (
          <Carrousel libelle="Arrivees recentes">
            {donnee.arriveesRecentes.arrivees.slice(0, NOMBRE_MONTRE).map((arrivee) => (
              <li key={arrivee.appartenance} className="ui-carrousel__item accueil-arrivees-carte">
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
        )}
        {donnee.arriveesRecentes.total > NOMBRE_MONTRE ? (
          <Link className="app-lien" to={cheminDeRubrique(entite.code, 'trombinoscope')}>
            Voir le trombinoscope
          </Link>
        ) : null}
      </Carte>

      {/* 4. Evenements a venir — cahier §8.4 */}
      <Carte titre="Evenements a venir">
        {donnee.evenementsAVenir.evenements.length === 0 ? (
          <Alerte>Aucun evenement a venir pour le moment.</Alerte>
        ) : (
          <Carrousel libelle="Evenements a venir">
            {donnee.evenementsAVenir.evenements.slice(0, NOMBRE_MONTRE).map((evenement) => (
              <li
                key={evenement.identifiant}
                className="ui-carrousel__item accueil-evenements-carte"
              >
                <div className="accueil-evenements-entete">
                  <span className="accueil-evenements-titre">{evenement.titre}</span>
                  {evenement.etat === 'cancelled' ? <Badge ton="ko">Annule</Badge> : null}
                </div>
                <span className="accueil-evenements-horaire">
                  {plageDeLEvenement(evenement.commenceLe, evenement.finitLe)}
                </span>
              </li>
            ))}
          </Carrousel>
        )}
        <Link className="app-lien" to={cheminDeRubrique(entite.code, 'evenements')}>
          Voir tous les evenements
        </Link>
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
