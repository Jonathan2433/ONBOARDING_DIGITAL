/**
 * Archiver et restaurer, a l'ecran — LOT 5, `T11`, story `MVP-L05-US007`.
 *
 * TROIS ETATS, ET LE PREMIER EST L'ABSENCE
 *
 *   Un appelant dont le role ne donne pas l'action **ne voit rien** : ni bouton
 *   grise, ni message « vous n'avez pas le droit ». Le §20.1 est le « refus par
 *   defaut », et un bouton desactive apprend qu'une action existe -- sur un
 *   profil dont on ne gere pas le cycle de vie, c'est une information de trop.
 *
 *   **LE FRONTEND N'EST PAS L'AUTORITE POUR AUTANT.** La matrice l'ecrit : « le
 *   frontend peut masquer ou afficher les ACTIONS pour ameliorer l'experience,
 *   mais l'API reste l'autorite finale ». Un appelant qui contournerait cet ecran
 *   recevrait `403` de `resoudre_le_cycle_de_vie`, et `make profil-check` le
 *   prouve avec un DSM qui ecrit dans son perimetre et se voit refuser
 *   l'archivage.
 *
 * LA CONFIRMATION EST UNE ETAPE, PAS UN `window.confirm`
 *
 *   `confirm()` bloque le fil, n'est pas stylable, et **`jsdom` ne l'implemente
 *   pas** : il faudrait le bouchonner pour le tester, donc le test ne prouverait
 *   que son propre bouchon -- §7.0, quatrieme proposition. La confirmation est
 *   donc un etat du composant, avec deux vrais boutons.
 *
 * CE QUE L'ARCHIVAGE FAIT, L'ECRAN LE DIT AVANT
 *
 *   `T8` l'a mesure : l'archivage **revoque les sessions** et **cloture cinq
 *   relations**, et la restauration **n'en rouvre aucune** -- rouvrir d'anciennes
 *   valeurs serait decider a nouveau (§23.4). L'annoncer avant le geste est ce
 *   qui rend la confirmation utile ; un « Etes-vous sur ? » ne dit rien.
 *
 * CHANTIER FRONT, S6 (`DEC-672`) : `CARTE`
 *
 *   Ce panneau partageait `.profil-bloc` avec les cinq autres sections de
 *   `PageProfil.tsx`, devenues chacune une `Carte` (`niveauTitre="h3"`, sous le
 *   `h2` de l'identite). Rester en arriere l'aurait laisse seul dans l'ancien
 *   habillage. `Carte` n'acceptant pas de `className`, la mise en page propre a
 *   ce panneau (`.profil-cycle`, l'espacement des actions) vit desormais sur un
 *   `<div>` a l'interieur de `Carte`, jamais sur la carte elle-meme.
 */
import type { JSX } from 'react';
import { useState } from 'react';

import { agirSurLeCycleDeVie, type ActionDuCycleDeVie } from '../api/cycleDeVie';

import { peutGererLeCycleDeVie, type ResultatDuCycleDeVie } from '@onboarding/contracts';
import { Alerte, Bouton, Carte } from '@onboarding/ui';

/** Ce que le panneau montre a un instant donne. */
type Etat =
  | { readonly phase: 'repos' }
  | { readonly phase: 'confirmation' }
  | { readonly phase: 'envoi' }
  | { readonly phase: 'fait'; readonly resultat: ResultatDuCycleDeVie }
  | { readonly phase: 'refus'; readonly statut: number };

export interface ProprietesPanneau {
  readonly codeEntite: string;
  readonly appartenance: string;
  /** `archived` quand le profil est archive : c'est ce qui choisit l'action. */
  readonly archive: boolean;
  /**
   * La version LUE, §18.4.
   *
   * **CELLE DE LA FICHE AFFICHEE, JAMAIS UNE RELECTURE.** Relire juste avant
   * d'agir ferait disparaitre la concurrence optimiste : on enverrait la version
   * d'un etat qu'on n'a pas montre.
   */
  readonly version: number;
  /** Les roles de l'appelant DANS CETTE ENTITE, ou `null` s'ils ne sont pas connus. */
  readonly roles: readonly string[] | null;
  /** Appele apres un succes, pour que la page recharge ce qu'elle affiche. */
  readonly surSucces: () => void;
}

/**
 * Ce que chaque action annonce AVANT d'etre confirmee.
 *
 * **LES DEUX TEXTES DISENT CE QUE `T8` A MESURE**, et non une formule de
 * politesse : l'archivage revoque et cloture, la restauration ne rouvre rien.
 */
const ANNONCES: Readonly<Record<ActionDuCycleDeVie, { titre: string; consequence: string }>> = {
  archivage: {
    titre: 'Archiver ce profil',
    consequence:
      'L’acces de cette personne est revoque immediatement, et ses affectations en cours sont ' +
      'cloturees — metier, statut, cercles, DSM et responsabilites. Le profil quitte le ' +
      'trombinoscope. Il reste restaurable.',
  },
  restauration: {
    titre: 'Restaurer ce profil',
    consequence:
      'Le profil redevient actif et reparait dans le trombinoscope. Ses anciennes affectations ' +
      'ne sont PAS rouvertes : elles seront nommees ci-dessous, a redonner a la main.',
  },
};

/** Le message d'un refus. Chaque code dit une chose differente, et l'ecran le respecte. */
function messageDeRefus(statut: number, action: ActionDuCycleDeVie): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas cette action sur ce profil.';
  }
  if (statut === 409) {
    //  **L'ETAT, PAS LE ROLE** — §23.2 : une interdiction liee a la ressource
    //  prevaut sur le cumul des roles, si bien qu'un super-administrateur recoit
    //  ce refus comme tout le monde.
    return action === 'archivage'
      ? 'Ce profil n’est pas dans un etat qui permet l’archivage. Il est peut-etre deja archive.'
      : 'Ce profil n’est pas dans un etat qui permet la restauration. Il est peut-etre deja actif.';
  }
  if (statut === 404) {
    return 'Ce profil est introuvable, ou il n’est pas dans votre perimetre.';
  }
  return 'L’action n’a pas pu aboutir. Reessayez dans un instant.';
}

export function PanneauDuCycleDeVie({
  codeEntite,
  appartenance,
  archive,
  version,
  roles,
  surSucces,
}: ProprietesPanneau): JSX.Element | null {
  const [etat, setEtat] = useState<Etat>({ phase: 'repos' });
  const action: ActionDuCycleDeVie = archive ? 'restauration' : 'archivage';
  const annonce = ANNONCES[action];

  //  **RIEN N'EST RENDU QUAND LE ROLE NE DONNE PAS L'ACTION.** `roles` a `null`
  //  signifie « pas encore connus » : ne rien montrer est alors le bon defaut,
  //  et non un bouton qui apparaitrait puis disparaitrait.
  if (roles === null || !peutGererLeCycleDeVie(roles)) {
    return null;
  }

  async function agir(): Promise<void> {
    setEtat({ phase: 'envoi' });
    try {
      const reponse = await agirSurLeCycleDeVie(action, codeEntite, appartenance, version);
      if (reponse.statut === 200 && reponse.corps !== null) {
        setEtat({ phase: 'fait', resultat: reponse.corps });
        surSucces();
      } else {
        setEtat({ phase: 'refus', statut: reponse.statut });
      }
    } catch {
      //  Une panne reseau n'est pas un refus : les confondre ferait douter d'un
      //  droit alors que le service ne repond pas. §7.6.
      setEtat({ phase: 'refus', statut: 0 });
    }
  }

  return (
    <Carte niveauTitre="h3" titre="Cycle de vie">
      <div className="profil-cycle">
        {etat.phase === 'fait' ? (
          <Alerte ton="succes" urgence="alerte">
            <p>
              {`Profil ${etat.resultat.etatPrecedent} → ${etat.resultat.etatNouveau}, `}
              {`version ${String(etat.resultat.version)}.`}
            </p>
            {etat.resultat.relationsARedonner.length === 0 ? null : (
              <>
                {/*
                **CE QUI RESTE A FAIRE A LA MAIN, NOMME.** `T8` a arbitre que la
                restauration ne rouvre rien ; taire ce qui manque laisserait un
                profil actif sans DSM ni cercle, sans que personne le sache.
              */}
                <p>Affectations NON rouvertes, a redonner a la main :</p>
                <ul className="profil-relations">
                  {etat.resultat.relationsARedonner.map((nom) => (
                    <li key={nom}>{nom}</li>
                  ))}
                </ul>
              </>
            )}
            {Object.keys(etat.resultat.relationsCloses).length === 0 ? null : (
              <>
                {/*
                **CE QUE L'ARCHIVAGE A REELLEMENT CLOS, PAR TABLE.** L'annoncer
                avant le geste est une promesse ; le montrer apres est une
                mesure -- et c'est ce que `T8` produit, table par table.
              */}
                <p>
                  {`Affectations cloturees, et ${String(etat.resultat.sessionsRevoquees)} session(s) revoquee(s) :`}
                </p>
                <ul className="profil-relations">
                  {Object.entries(etat.resultat.relationsCloses).map(([table, compte]) => (
                    <li key={table}>{`${table} — ${String(compte)}`}</li>
                  ))}
                </ul>
              </>
            )}
          </Alerte>
        ) : etat.phase === 'refus' ? (
          <>
            <Alerte ton="erreur" urgence="alerte">
              {messageDeRefus(etat.statut, action)}
            </Alerte>
            <Bouton
              onClick={() => {
                setEtat({ phase: 'repos' });
              }}
              type="button"
              variante="secondaire"
            >
              Fermer
            </Bouton>
          </>
        ) : etat.phase === 'confirmation' || etat.phase === 'envoi' ? (
          <>
            <Alerte ton="avertissement" urgence="information">
              {annonce.consequence}
            </Alerte>
            <div className="profil-actions">
              <Bouton
                disabled={etat.phase === 'envoi'}
                onClick={() => {
                  void agir();
                }}
                type="button"
                variante="primaire"
              >
                {etat.phase === 'envoi'
                  ? 'En cours…'
                  : `Confirmer : ${annonce.titre.toLowerCase()}`}
              </Bouton>
              <Bouton
                disabled={etat.phase === 'envoi'}
                onClick={() => {
                  setEtat({ phase: 'repos' });
                }}
                type="button"
                variante="secondaire"
              >
                Annuler
              </Bouton>
            </div>
          </>
        ) : (
          <Bouton
            onClick={() => {
              setEtat({ phase: 'confirmation' });
            }}
            type="button"
            variante="secondaire"
          >
            {annonce.titre}
          </Bouton>
        )}
      </div>
    </Carte>
  );
}
