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
 * LES ONGLETS SONT DESORMAIS `Onglets` (`@onboarding/ui`), SUR RADIX
 *
 *   Chantier front hors lot, sous-etape S2 (`DEC-672`). Le motif WAI-ARIA
 *   (`tablist`/`tab`/`tabpanel`) fabrique a la main sur deux `<button>`
 *   natifs est remplace par la primitive posee en S1 — meme contrat
 *   accessible, plus `ArrowLeft`/`ArrowRight` qu'aucune des deux copies
 *   manuelles du depot ne rendait (mesure avant S1). `activationMode="manual"`
 *   (pose dans `Onglets.tsx`) : parcourir les deux classements a la fleche ne
 *   relance aucun appel reseau tant que rien ne confirme l'intention.
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
 *   que l'API a servi. `plageDeLEvenement` applique la meme methode — des
 *   segments lus a position fixe dans la chaine ISO — et vit desormais dans
 *   `../affichage` : `T11` du LOT 8 en est le second consommateur (l'accueil),
 *   et une seconde copie aurait divergee au premier ajout (§7.27).
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
 *
 * CHANTIER FRONT, S7 (`DEC-672`) : `CARTE` GENERALISEE AU PANNEAU, PAS DE
 * `CARROUSEL` ICI
 *
 *   Mesure avant construction : `Badge` sur l'etat annule existe deja depuis
 *   le LOT 8 `T9`, et `.evenements-carte` (CSS) est DEJA identique, trait
 *   pour trait, a `.accueil-evenements-carte` que `T12` du LOT 8 a posee pour
 *   le carrousel de la page entite — aucune divergence a corriger. Ce qui
 *   manquait etait `Carte` elle-meme : le panneau de chaque onglet reste un
 *   `<div>` nu. `Carrousel` (LOT 8, `T12`) ne s'applique PAS ici — il est
 *   reserve a une liste RESUMEE et bornee (`NOMBRE_MONTRE`, avec un lien
 *   « voir plus »), jamais a l'ecran de liste COMPLETE qui porte sa propre
 *   pagination serveur : en faire un carrousel casserait la pagination par
 *   page (`donnees.pages`) en la remplacant par un defilement continu que
 *   l'API ne sait pas servir. La « coherence » demandee est donc visuelle,
 *   pas structurelle : le panneau devient une `Carte` SANS titre (un
 *   `<div className="ex-carte">`, jamais une region) — le tour de carte que
 *   `S3`-`S6` appliquent partout ailleurs — sans dupliquer le nom de
 *   l'onglet actif, deja porte par le `tabpanel` de `Onglets`.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { plageDeLEvenement } from '../affichage';
import { lireLesEvenements } from '../api/evenements';
import { cheminGestionDesEvenementsALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import {
  CLASSEMENTS_D_EVENEMENTS,
  type ClassementEvenement,
  peutGererLesEvenements,
  type PageDesEvenements,
  TAILLE_PAR_DEFAUT,
} from '@onboarding/contracts';
import { Alerte, Badge, Carte, Onglets } from '@onboarding/ui';

const TAILLE = TAILLE_PAR_DEFAUT;

const LIBELLES_DE_CLASSEMENT: Readonly<Record<ClassementEvenement, string>> = {
  a_venir: 'A venir',
  passes: 'Passes',
};

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

  //  **LE CHANGEMENT D'ONGLET REINITIALISE LA PAGE** — voir l'en-tete.
  const surChangementDeClassement = (valeur: string): void => {
    setClassement(valeur as ClassementEvenement);
    setPage(1);
  };

  const onglets = CLASSEMENTS_D_EVENEMENTS.map((valeur) => ({
    valeur,
    libelle: LIBELLES_DE_CLASSEMENT[valeur],
  }));

  if (etat.phase === 'chargement') {
    return (
      <div className="evenements">
        <Onglets
          libelleDeLaListe="Classement des evenements"
          onChangerDOnglet={surChangementDeClassement}
          onglets={onglets}
          valeurActive={classement}
        >
          <Carte>
            <Alerte urgence="information">Chargement des evenements…</Alerte>
          </Carte>
        </Onglets>
      </div>
    );
  }

  if (etat.phase === 'erreur') {
    return (
      <div className="evenements">
        <Onglets
          libelleDeLaListe="Classement des evenements"
          onChangerDOnglet={surChangementDeClassement}
          onglets={onglets}
          valeurActive={classement}
        >
          <Carte>
            <Alerte ton="erreur" urgence="alerte">
              {etat.statut === 401
                ? 'Votre session a expire. Reconnectez-vous pour consulter les evenements.'
                : "Les evenements n'ont pas pu etre charges. Cela ne dit rien de leur contenu : verifiez votre connexion, puis reessayez."}
            </Alerte>
          </Carte>
        </Onglets>
      </div>
    );
  }

  const donnees = etat.page;

  return (
    <div className="evenements">
      {peutGerer ? (
        <p>
          <Link className="app-lien" to={cheminGestionDesEvenementsALEcran(entite.code)}>
            Gerer les evenements
          </Link>
        </p>
      ) : null}
      <Onglets
        libelleDeLaListe="Classement des evenements"
        onChangerDOnglet={surChangementDeClassement}
        onglets={onglets}
        valeurActive={classement}
      >
        <Carte>
          <div className="evenements-panneau">
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
        </Carte>
      </Onglets>
    </div>
  );
}
