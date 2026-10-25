/**
 * « Support » — signalements, alertes opérationnelles et demandes RGPD, LOT
 * 10 `T12`/`T13`/`T14` (API), `T15` (ce composant), `US006`/`US007`/`US008`.
 *
 * ARBITRAGE DE JONATHAN (`AskUserQuestion`, 22/10/2026) : TROIS SUJETS, UN
 * SEUL ONGLET
 *
 *   Le cahier traite audit (§10.11), reporting (§10.10) et support (§10.12)
 *   comme trois sujets distincts, mais aucun des sept groupes du §10.8 ne
 *   nomme « support » — reporting étendu a rejoint « Pilotage », qui le
 *   portait déjà (`T5`/`T10`, même grille, §7.27) ; audit et support, qui ne
 *   correspondent à AUCUN des sept groupes, reçoivent chacun un onglet de
 *   plus. Les demandes RGPD rejoignent ce même onglet plutôt qu'un
 *   quatrième : aucune ligne de matrice ne les nomme « support » à la
 *   lettre, mais aucun groupe existant ne leur correspond mieux — même
 *   motif que `T14` a résolu RGPD par analogie avec §18, pas par une
 *   correspondance littérale.
 *
 * TROIS GARDES, TROIS DEGRÉS D'OUVERTURE DIFFÉRENTS
 *
 *   Signalements : la LECTURE se dégrade jusqu'à `Soi` (aucun rôle refusé) ;
 *   l'ÉCRITURE (changer l'état) exige `peutTraiterLesSignalements` (ADM-E/
 *   SUPER). Alertes : la lecture elle-même refuse DSM/BOOST/OFFICE/EMP — ce
 *   composant le reflète en dérivant la visibilité de LECTURE depuis
 *   `peutTraiterLesAlertes` ∪ `ESM` (le périmètre `LIMITE` de l'API, qui
 *   n'a pas de grille statique propre à exposer — voir `app/support/
 *   perimetre_alertes.py`). RGPD : une seule grille garde tout, lecture et
 *   écriture confondues, aucun plancher `Soi`.
 *
 *   L'onglet lui-même reste visible à TOUTE session établie (`() => true`,
 *   même parti que « Pilotage ») : masquer l'onglet entier à qui n'a que la
 *   lecture de ses propres signalements le priverait de la seule chose que
 *   la matrice lui accorde.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  acquitterUneAlerte,
  commenterUneAlerte,
  lireLesCommentairesDUneAlerte,
  listerLesAlertes,
  resoudreUneAlerte,
} from '../../api/alertes';
import {
  cloturerUneDemandeRGPD,
  listerLesDemandesRGPD,
  receptionnerUneDemandeRGPD,
  verifierLIdentiteDUneDemandeRGPD,
} from '../../api/rgpd';
import {
  changerLEtatDUnSignalement,
  listerLesSignalements,
} from '../../api/traitementDesSignalements';
import {
  ETATS_DE_SIGNALEMENT,
  peutLireLesAlertes,
  peutTraiterLesAlertes,
  peutTraiterLesDemandesRGPD,
  peutTraiterLesSignalements,
  TAILLE_PAR_DEFAUT,
  TYPES_DE_DEMANDE_RGPD,
  type CommentaireDAlerte,
  type EtatDeSignalement,
  type LigneDAlerte,
  type LigneDeDemandeRGPD,
  type LigneDeSignalement,
  type TypeDeDemandeRGPD,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre rôle ne permet pas cette action.';
  }
  if (statut === 404) {
    return 'Cette cible est introuvable, ou hors de votre périmètre.';
  }
  if (statut === 409) {
    return 'Cette ressource a changé d’état depuis votre dernière lecture. Rechargez.';
  }
  if (statut === 422) {
    return 'La demande n’est pas valide — un motif est peut-être requis.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

// ---------------------------------------------------------------------------
//  Signalements
// ---------------------------------------------------------------------------

function PanneauSignalements({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const peutTraiter = peutTraiterLesSignalements(roles);
  const [charge, setCharge] = useState<{
    readonly statut: number;
    readonly corps: readonly LigneDeSignalement[] | null;
  } | null>(null);
  const [selection, setSelection] = useState<LigneDeSignalement | null>(null);
  const [nouvelEtat, setNouvelEtat] = useState<EtatDeSignalement>('investigating');
  const [commentaire, setCommentaire] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    const abandon = new AbortController();
    void listerLesSignalements(code, 1, TAILLE_PAR_DEFAUT, undefined, abandon.signal).then(
      (reponse) => {
        setCharge({ statut: reponse.statut, corps: reponse.corps?.signalements ?? null });
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setCharge({ statut: 0, corps: null });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [code]);

  async function soumettre(): Promise<void> {
    if (selection === null) {
      return;
    }
    setEnCours(true);
    setErreur(null);
    const reponse = await changerLEtatDUnSignalement(code, selection.identifiant, {
      nouvel_etat: nouvelEtat,
      version: selection.version,
      ...(commentaire === '' ? {} : { commentaire }),
    });
    setEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setSelection(null);
    setCommentaire('');
    const relecture = await listerLesSignalements(code, 1, TAILLE_PAR_DEFAUT);
    setCharge({ statut: relecture.statut, corps: relecture.corps?.signalements ?? null });
  }

  if (charge === null) {
    return (
      <p className="administration-chargement" role="status">
        Chargement des signalements…
      </p>
    );
  }
  if (charge.statut !== 200 || charge.corps === null) {
    return (
      <Alerte ton={charge.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {messageDeRefus(charge.statut)}
      </Alerte>
    );
  }

  return (
    <section
      aria-labelledby="administration-signalements-titre"
      className="administration-support-panneau"
    >
      <h4 id="administration-signalements-titre">Signalements</h4>
      {charge.corps.length === 0 ? (
        <p>Aucun signalement.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">État</th>
              <th scope="col">Description</th>
              <th scope="col">Page</th>
              <th scope="col">Créé le</th>
              {peutTraiter ? <th scope="col">Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {charge.corps.map((s) => (
              <tr key={s.identifiant}>
                <td>{s.etat}</td>
                <td>{s.description}</td>
                <td>{s.cheminDePage}</td>
                <td>{s.creeLe}</td>
                {peutTraiter ? (
                  <td>
                    <Bouton
                      onClick={() => {
                        setSelection(s);
                        setNouvelEtat('investigating');
                      }}
                      type="button"
                      variante="secondaire"
                    >
                      Changer l’état
                    </Bouton>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selection === null ? null : (
        <form
          className="administration-formulaire-signalement"
          onSubmit={(e) => {
            e.preventDefault();
            void soumettre();
          }}
        >
          <p>Signalement sélectionné : {selection.description}</p>
          <label className="administration-champ">
            Nouvel état
            <select
              onChange={(e) => {
                setNouvelEtat(e.target.value as EtatDeSignalement);
              }}
              value={nouvelEtat}
            >
              {ETATS_DE_SIGNALEMENT.map((etat) => (
                <option key={etat} value={etat}>
                  {etat}
                </option>
              ))}
            </select>
          </label>
          <label className="administration-champ">
            Commentaire (motif obligatoire pour le super-administrateur)
            <textarea
              onChange={(e) => {
                setCommentaire(e.target.value);
              }}
              value={commentaire}
            />
          </label>
          {erreur === null ? null : (
            <Alerte ton="erreur" urgence="alerte">
              {erreur}
            </Alerte>
          )}
          <Bouton disabled={enCours} type="submit">
            {enCours ? 'Envoi…' : 'Valider'}
          </Bouton>
          <Bouton
            onClick={() => {
              setSelection(null);
            }}
            type="button"
            variante="secondaire"
          >
            Annuler
          </Bouton>
        </form>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
//  Alertes
// ---------------------------------------------------------------------------

function PanneauAlertes({
  roles,
}: {
  readonly roles: readonly string[] | null;
}): JSX.Element | null {
  const peutLire = peutLireLesAlertes(roles);
  const peutTraiter = peutTraiterLesAlertes(roles);
  const [charge, setCharge] = useState<{
    readonly statut: number;
    readonly corps: readonly LigneDAlerte[] | null;
  } | null>(null);
  const [selection, setSelection] = useState<LigneDAlerte | null>(null);
  const [commentaires, setCommentaires] = useState<readonly CommentaireDAlerte[]>([]);
  const [nouveauCommentaire, setNouveauCommentaire] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (!peutLire) {
      return;
    }
    const abandon = new AbortController();
    void listerLesAlertes(1, TAILLE_PAR_DEFAUT, undefined, abandon.signal).then(
      (reponse) => {
        setCharge({ statut: reponse.statut, corps: reponse.corps?.alertes ?? null });
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setCharge({ statut: 0, corps: null });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [peutLire]);

  async function rafraichir(): Promise<void> {
    const reponse = await listerLesAlertes(1, TAILLE_PAR_DEFAUT);
    setCharge({ statut: reponse.statut, corps: reponse.corps?.alertes ?? null });
  }

  async function selectionner(alerte: LigneDAlerte): Promise<void> {
    setSelection(alerte);
    setErreur(null);
    const reponse = await lireLesCommentairesDUneAlerte(alerte.identifiant);
    setCommentaires(reponse.corps?.commentaires ?? []);
  }

  async function acquitter(): Promise<void> {
    if (selection === null) {
      return;
    }
    setEnCours(true);
    const reponse = await acquitterUneAlerte(selection.identifiant, { version: selection.version });
    setEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setSelection(null);
    await rafraichir();
  }

  async function resoudre(): Promise<void> {
    if (selection === null) {
      return;
    }
    setEnCours(true);
    const reponse = await resoudreUneAlerte(selection.identifiant, {
      version: selection.version,
      ...(nouveauCommentaire === '' ? {} : { commentaire: nouveauCommentaire }),
    });
    setEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setSelection(null);
    setNouveauCommentaire('');
    await rafraichir();
  }

  async function commenter(): Promise<void> {
    if (selection === null || nouveauCommentaire === '') {
      return;
    }
    setEnCours(true);
    const reponse = await commenterUneAlerte(selection.identifiant, {
      contenu: nouveauCommentaire,
    });
    setEnCours(false);
    if (reponse.statut !== 201 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setNouveauCommentaire('');
    const relue = await lireLesCommentairesDUneAlerte(selection.identifiant);
    setCommentaires(relue.corps?.commentaires ?? []);
  }

  if (!peutLire) {
    return null;
  }
  if (charge === null) {
    return (
      <p className="administration-chargement" role="status">
        Chargement des alertes…
      </p>
    );
  }
  if (charge.statut !== 200 || charge.corps === null) {
    return (
      <Alerte ton={charge.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {messageDeRefus(charge.statut)}
      </Alerte>
    );
  }

  return (
    <section
      aria-labelledby="administration-alertes-titre"
      className="administration-support-panneau"
    >
      <h4 id="administration-alertes-titre">Alertes opérationnelles</h4>
      {charge.corps.length === 0 ? (
        <p>Aucune alerte.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Gravité</th>
              <th scope="col">État</th>
              <th scope="col">Ouverte le</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {charge.corps.map((a) => (
              <tr key={a.identifiant}>
                <td>{a.gravite}</td>
                <td>{a.etat}</td>
                <td>{a.ouverteLe}</td>
                <td>
                  <Bouton
                    onClick={() => {
                      void selectionner(a);
                    }}
                    type="button"
                    variante="secondaire"
                  >
                    Ouvrir
                  </Bouton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selection === null ? null : (
        <div className="administration-detail-alerte">
          <p>
            Alerte « {selection.identifiant} » — état {selection.etat}
          </p>
          <ul>
            {commentaires.map((c) => (
              <li key={c.identifiant}>
                {c.contenu} — {c.creeLe}
              </li>
            ))}
          </ul>
          <label className="administration-champ">
            Commentaire
            <textarea
              onChange={(e) => {
                setNouveauCommentaire(e.target.value);
              }}
              value={nouveauCommentaire}
            />
          </label>
          {erreur === null ? null : (
            <Alerte ton="erreur" urgence="alerte">
              {erreur}
            </Alerte>
          )}
          {peutTraiter ? (
            <>
              <Bouton
                disabled={enCours || selection.etat !== 'open'}
                onClick={() => {
                  void acquitter();
                }}
                type="button"
              >
                Acquitter
              </Bouton>
              <Bouton
                disabled={enCours}
                onClick={() => {
                  void commenter();
                }}
                type="button"
                variante="secondaire"
              >
                Commenter
              </Bouton>
              <Bouton
                disabled={enCours || selection.etat === 'resolved'}
                onClick={() => {
                  void resoudre();
                }}
                type="button"
              >
                Résoudre
              </Bouton>
            </>
          ) : null}
          <Bouton
            onClick={() => {
              setSelection(null);
            }}
            type="button"
            variante="secondaire"
          >
            Fermer
          </Bouton>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
//  Demandes RGPD
// ---------------------------------------------------------------------------

function PanneauRGPD({ roles }: { readonly roles: readonly string[] | null }): JSX.Element | null {
  const peutTraiter = peutTraiterLesDemandesRGPD(roles);
  const [charge, setCharge] = useState<{
    readonly statut: number;
    readonly corps: readonly LigneDeDemandeRGPD[] | null;
  } | null>(null);
  const [personneConcernee, setPersonneConcernee] = useState('');
  const [typeDemande, setTypeDemande] = useState<TypeDeDemandeRGPD>('access');
  const [canal, setCanal] = useState('');
  const [selection, setSelection] = useState<LigneDeDemandeRGPD | null>(null);
  const [reponseDeCloture, setReponseDeCloture] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  async function rafraichir(): Promise<void> {
    const reponse = await listerLesDemandesRGPD(1, TAILLE_PAR_DEFAUT);
    setCharge({ statut: reponse.statut, corps: reponse.corps?.demandes ?? null });
  }

  useEffect(() => {
    if (!peutTraiter) {
      return;
    }
    const abandon = new AbortController();
    void listerLesDemandesRGPD(1, TAILLE_PAR_DEFAUT, undefined, undefined, abandon.signal).then(
      (reponse) => {
        setCharge({ statut: reponse.statut, corps: reponse.corps?.demandes ?? null });
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setCharge({ statut: 0, corps: null });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [peutTraiter]);

  async function receptionner(): Promise<void> {
    if (personneConcernee === '' || canal === '') {
      return;
    }
    setEnCours(true);
    setErreur(null);
    const reponse = await receptionnerUneDemandeRGPD({
      personne_concernee_id: personneConcernee,
      type_demande: typeDemande,
      canal,
    });
    setEnCours(false);
    if (reponse.statut !== 201 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setPersonneConcernee('');
    setCanal('');
    await rafraichir();
  }

  async function verifierIdentite(): Promise<void> {
    if (selection === null) {
      return;
    }
    setEnCours(true);
    const reponse = await verifierLIdentiteDUneDemandeRGPD(selection.identifiant, {
      version: selection.version,
    });
    setEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setSelection({ ...selection, identiteVerifiee: true, version: reponse.corps.version });
    await rafraichir();
  }

  async function cloturer(): Promise<void> {
    if (selection === null || reponseDeCloture === '') {
      return;
    }
    setEnCours(true);
    const reponse = await cloturerUneDemandeRGPD(selection.identifiant, {
      version: selection.version,
      reponse: reponseDeCloture,
    });
    setEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreur(messageDeRefus(reponse.statut));
      return;
    }
    setSelection(null);
    setReponseDeCloture('');
    await rafraichir();
  }

  if (!peutTraiter) {
    return null;
  }

  return (
    <section aria-labelledby="administration-rgpd-titre" className="administration-support-panneau">
      <h4 id="administration-rgpd-titre">Demandes de droit RGPD</h4>
      <form
        className="administration-formulaire-rgpd"
        onSubmit={(e) => {
          e.preventDefault();
          void receptionner();
        }}
      >
        <label className="administration-champ">
          Identifiant de la personne concernée
          <input
            onChange={(e) => {
              setPersonneConcernee(e.target.value);
            }}
            type="text"
            value={personneConcernee}
          />
        </label>
        <label className="administration-champ">
          Type de demande
          <select
            onChange={(e) => {
              setTypeDemande(e.target.value as TypeDeDemandeRGPD);
            }}
            value={typeDemande}
          >
            {TYPES_DE_DEMANDE_RGPD.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="administration-champ">
          Canal
          <input
            onChange={(e) => {
              setCanal(e.target.value);
            }}
            type="text"
            value={canal}
          />
        </label>
        <Bouton disabled={enCours} type="submit">
          Réceptionner
        </Bouton>
      </form>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {charge === null ? (
        <p className="administration-chargement" role="status">
          Chargement des demandes…
        </p>
      ) : charge.statut !== 200 || charge.corps === null ? (
        <Alerte ton={charge.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {messageDeRefus(charge.statut)}
        </Alerte>
      ) : charge.corps.length === 0 ? (
        <p>Aucune demande.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Type</th>
              <th scope="col">État</th>
              <th scope="col">Échéance</th>
              <th scope="col">En retard</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {charge.corps.map((d) => (
              <tr key={d.identifiant}>
                <td>{d.typeDemande}</td>
                <td>{d.etat}</td>
                <td>{d.echeance}</td>
                <td>{d.enRetard ? 'oui' : 'non'}</td>
                <td>
                  <Bouton
                    onClick={() => {
                      setSelection(d);
                      setErreur(null);
                    }}
                    type="button"
                    variante="secondaire"
                  >
                    Ouvrir
                  </Bouton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selection === null ? null : (
        <div className="administration-detail-rgpd">
          <p>
            Demande « {selection.identifiant} » — identité{' '}
            {selection.identiteVerifiee ? 'vérifiée' : 'non vérifiée'}
          </p>
          <Bouton
            disabled={enCours || selection.identiteVerifiee}
            onClick={() => {
              void verifierIdentite();
            }}
            type="button"
          >
            Vérifier l’identité
          </Bouton>
          {selection.etat === 'closed' ? null : (
            <>
              <label className="administration-champ">
                Réponse de clôture
                <textarea
                  onChange={(e) => {
                    setReponseDeCloture(e.target.value);
                  }}
                  value={reponseDeCloture}
                />
              </label>
              <Bouton
                disabled={enCours}
                onClick={() => {
                  void cloturer();
                }}
                type="button"
              >
                Clôturer
              </Bouton>
            </>
          )}
          <Bouton
            onClick={() => {
              setSelection(null);
            }}
            type="button"
            variante="secondaire"
          >
            Fermer
          </Bouton>
        </div>
      )}
    </section>
  );
}

export function SectionSupport({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  return (
    <div className="administration-support">
      <PanneauSignalements code={code} roles={roles} />
      <PanneauAlertes roles={roles} />
      <PanneauRGPD roles={roles} />
    </div>
  );
}
