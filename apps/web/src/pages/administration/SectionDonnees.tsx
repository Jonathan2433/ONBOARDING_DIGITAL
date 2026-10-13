/**
 * « Données » — l'import CSV complet, du dépôt au rapport. LOT 9, `T6` à
 * `T10` (API) puis `T14` (écran), `US004`/`US005`/`US006`.
 *
 * UN ASSISTANT SÉQUENTIEL, PAS UN HISTORIQUE PARCOURABLE
 *
 *   Voir l'en-tête du module de contrat `imports.ts` : aucune route ne liste
 *   les lots d'une entité. L'identifiant du lot déposé vit dans l'ÉTAT DE CET
 *   ÉCRAN, du dépôt jusqu'au rapport — le quitter perd la référence, et c'est
 *   un fait d'architecture, pas une simplification de cet écran.
 *
 * LE RAPPORT SERT AUSSI PENDANT LA PRÉVISUALISATION, ET C'EST MESURÉ
 *
 *   `consulter_le_rapport` (`app/imports/rapport.py`) ne vérifie AUCUN état
 *   du lot — il rend la réconciliation et les lignes telles qu'elles sont À
 *   L'INSTANT de l'appel, que le lot soit encore `preview_ready` ou déjà
 *   `completed`. Cet écran l'appelle donc aux DEUX moments : pour choisir les
 *   rapprochements de clients avant de lancer, puis pour lire le résultat
 *   final après.
 *
 * LES DÉCISIONS « PERSONNE » RESTENT UN IDENTIFIANT SAISI
 *
 *   `person_merge`/`profile_reactivation` exigent un `target_person_id`, et
 *   aucune route ne liste les profils actifs/archivés TOUS CRITÈRES
 *   confondus pour les proposer dans un sélecteur — seul le trombinoscope
 *   existe, borné à une recherche. `T8` n'exerçait déjà que les deux
 *   catégories « client » ; cet écran les propose avec un sélecteur
 *   (`listerLesClients`), et les deux catégories « personne » avec un
 *   identifiant saisi — résidu nommé, §9.3.
 */
import type { JSX } from 'react';
import { useState } from 'react';

import {
  deposerUnImport,
  listerLesClients,
  enregistrerUneDecision,
  lancerLImport,
  rejouerUneLigne,
  consulterLeRapport,
} from '../../api/imports';
import {
  peutDeposerUnImport,
  peutValiderLesRapprochements,
  TYPES_DE_DECISION,
  type ClientDuCatalogue,
  type LotDepose,
  type RapportDImport,
  type TypeDeDecision,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre rôle ne permet pas cette action.';
  }
  if (statut === 409) {
    return 'Cette ligne ou ce lot a changé d’état. Rechargez le rapport.';
  }
  if (statut === 422) {
    return 'La demande n’est pas valide.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

const LIBELLES_DE_DECISION: Readonly<Record<TypeDeDecision, string>> = {
  person_merge: 'Fusionner avec un profil existant',
  profile_reactivation: 'Réactiver un profil archivé',
  client_alias_creation: 'Créer un alias vers ce client',
  canonical_client_selection: 'Sélectionner ce client canonique',
  voluntary_rejection: 'Rejeter volontairement cette ligne',
};

function DecisionSurUneLigne({
  code,
  lot,
  ligne,
  clients,
  onDecide,
}: {
  readonly code: string;
  readonly lot: string;
  readonly ligne: string;
  readonly clients: readonly ClientDuCatalogue[];
  readonly onDecide: () => void;
}): JSX.Element {
  const [type, setType] = useState<TypeDeDecision>('canonical_client_selection');
  const [targetClient, setTargetClient] = useState('');
  const [targetPersonne, setTargetPersonne] = useState('');
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const exigeClient = type === 'client_alias_creation' || type === 'canonical_client_selection';
  const exigePersonne = type === 'person_merge' || type === 'profile_reactivation';
  const pretAEnvoyer =
    (!exigeClient || targetClient !== '') && (!exigePersonne || targetPersonne !== '');

  async function decider(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await enregistrerUneDecision(code, lot, ligne, {
      decision_type: type,
      target_client_id: exigeClient ? targetClient : null,
      target_person_id: exigePersonne ? targetPersonne : null,
    });
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      onDecide();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <div className="administration-decision-de-ligne">
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      <label className="administration-champ">
        Décision
        <select
          onChange={(e) => {
            setType(e.target.value as TypeDeDecision);
          }}
          value={type}
        >
          {TYPES_DE_DECISION.map((t) => (
            <option key={t} value={t}>
              {LIBELLES_DE_DECISION[t]}
            </option>
          ))}
        </select>
      </label>
      {!exigeClient ? null : (
        <label className="administration-champ">
          Client
          <select
            onChange={(e) => {
              setTargetClient(e.target.value);
            }}
            value={targetClient}
          >
            <option value="">— choisir —</option>
            {clients.map((c) => (
              <option key={c.identifiant} value={c.identifiant}>
                {c.nomAffiche}
                {c.actifLocalement ? '' : ' (pas encore activé localement)'}
              </option>
            ))}
          </select>
        </label>
      )}
      {!exigePersonne ? null : (
        <label className="administration-champ">
          Identifiant (UUID) de la personne
          <input
            onChange={(e) => {
              setTargetPersonne(e.target.value);
            }}
            type="text"
            value={targetPersonne}
          />
        </label>
      )}
      <Bouton
        disabled={envoi || !pretAEnvoyer}
        onClick={() => {
          void decider();
        }}
        type="button"
        variante="primaire"
      >
        {envoi ? 'Envoi…' : 'Enregistrer la décision'}
      </Bouton>
    </div>
  );
}

function TableauDuRapport({
  code,
  lot,
  rapport,
  clients,
  onChange,
}: {
  readonly code: string;
  readonly lot: string;
  readonly rapport: RapportDImport;
  readonly clients: readonly ClientDuCatalogue[];
  readonly onChange: () => void;
}): JSX.Element {
  const [enRejeu, setEnRejeu] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  async function rejouer(ligne: string): Promise<void> {
    setEnRejeu(ligne);
    setErreur(null);
    const resultat = await rejouerUneLigne(code, lot, ligne);
    setEnRejeu(null);
    if (resultat.statut === 200 && resultat.corps !== null) {
      onChange();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <div className="administration-rapport">
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      <dl className="administration-grandeurs">
        <div className="administration-grandeur">
          <dt>Créations</dt>
          <dd>{rapport.reconciliation.creations}</dd>
        </div>
        <div className="administration-grandeur">
          <dt>Mises à jour</dt>
          <dd>{rapport.reconciliation.misesAJour}</dd>
        </div>
        <div className="administration-grandeur">
          <dt>Rejets</dt>
          <dd>{rapport.reconciliation.rejets}</dd>
        </div>
        <div className="administration-grandeur">
          <dt>En attente de décision</dt>
          <dd>{rapport.reconciliation.enAttenteDeDecision}</dd>
        </div>
        <div className="administration-grandeur">
          <dt>En cours</dt>
          <dd>{rapport.reconciliation.enCours}</dd>
        </div>
      </dl>
      <table className="administration-lignes-du-rapport">
        <thead>
          <tr>
            <th scope="col">Ligne</th>
            <th scope="col">État</th>
            <th scope="col">Problèmes</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {rapport.lignes.map((ligne) => (
            <tr key={ligne.identifiant}>
              <td>{ligne.numero}</td>
              <td>{ligne.etat}</td>
              <td>
                {ligne.problemes.length === 0 ? (
                  '—'
                ) : (
                  <ul>
                    {ligne.problemes.map((p) => (
                      //  Aucun identifiant propre à un problème : la paire
                      //  (code, champ) est unique au sein d'une même ligne —
                      //  deux occurrences du même code portent des champs
                      //  différents (modèle §19.3).
                      <li key={`${p.code}-${p.champ ?? ''}`}>
                        <strong>{p.code}</strong> — {p.message}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
              <td>
                {ligne.etat === 'needs_decision' ? (
                  <DecisionSurUneLigne
                    clients={clients}
                    code={code}
                    ligne={ligne.identifiant}
                    lot={lot}
                    onDecide={onChange}
                  />
                ) : ligne.etat === 'rejected' ? (
                  <Bouton
                    disabled={enRejeu === ligne.identifiant}
                    onClick={() => {
                      void rejouer(ligne.identifiant);
                    }}
                    type="button"
                    variante="secondaire"
                  >
                    {enRejeu === ligne.identifiant ? 'Envoi…' : 'Rejouer cette ligne'}
                  </Bouton>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type EtapeDeLImport =
  | { readonly phase: 'depot' }
  | { readonly phase: 'analyse'; readonly lot: LotDepose }
  | { readonly phase: 'rapport'; readonly lot: LotDepose; readonly rapport: RapportDImport };

function SectionDepotEtValidation({ code }: { readonly code: string }): JSX.Element {
  const [etape, setEtape] = useState<EtapeDeLImport>({ phase: 'depot' });
  const [fichier, setFichier] = useState<File | null>(null);
  const [clients, setClients] = useState<readonly ClientDuCatalogue[]>([]);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function deposer(): Promise<void> {
    if (fichier === null) {
      return;
    }
    setEnvoi(true);
    setErreur(null);
    const [depot, listeDesClients] = await Promise.all([
      deposerUnImport(code, fichier),
      listerLesClients(code),
    ]);
    setEnvoi(false);
    if (depot.statut === 201 && depot.corps !== null) {
      setEtape({ phase: 'analyse', lot: depot.corps });
      if (listeDesClients.statut === 200 && listeDesClients.corps !== null) {
        setClients(listeDesClients.corps.clients);
      }
      await rafraichirLeRapport(depot.corps);
    } else {
      setErreur(messageDeRefus(depot.statut));
    }
  }

  async function rafraichirLeRapport(lot: LotDepose): Promise<void> {
    const rapport = await consulterLeRapport(code, lot.identifiant, 1, 100);
    if (rapport.statut === 200 && rapport.corps !== null) {
      setEtape({ phase: 'rapport', lot, rapport: rapport.corps });
    }
  }

  async function lancer(lot: LotDepose): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await lancerLImport(code, lot.identifiant);
    setEnvoi(false);
    if (resultat.statut === 200 && resultat.corps !== null) {
      await rafraichirLeRapport(lot);
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <section
      className="administration-depot-d-import"
      aria-labelledby="administration-depot-d-import-titre"
    >
      <h4 id="administration-depot-d-import-titre">Importer un CSV</h4>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {etape.phase === 'depot' ? (
        <div className="administration-champs">
          <label className="administration-champ">
            Fichier CSV
            <input
              accept=".csv,text/csv"
              onChange={(e) => {
                setFichier(e.target.files?.[0] ?? null);
              }}
              type="file"
            />
          </label>
          <Bouton
            disabled={envoi || fichier === null}
            onClick={() => {
              void deposer();
            }}
            type="button"
            variante="primaire"
          >
            {envoi ? 'Dépôt…' : 'Déposer et analyser'}
          </Bouton>
        </div>
      ) : (
        <>
          <p>
            Lot <strong>{etape.lot.nomDeFichier}</strong> — état {etape.lot.etat},{' '}
            {etape.lot.totalLignes} ligne(s), {etape.lot.lignesRejetees} rejetée(s),{' '}
            {etape.lot.lignesAConfirmer} à confirmer.
          </p>
          {etape.phase === 'rapport' ? (
            <>
              <TableauDuRapport
                clients={clients}
                code={code}
                lot={etape.lot.identifiant}
                onChange={() => {
                  void rafraichirLeRapport(etape.lot);
                }}
                rapport={etape.rapport}
              />
              {etape.lot.etat === 'completed' ? null : (
                <Bouton
                  disabled={envoi}
                  onClick={() => {
                    void lancer(etape.lot);
                  }}
                  type="button"
                  variante="primaire"
                >
                  {envoi ? 'Envoi…' : 'Lancer l’import'}
                </Bouton>
              )}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

export function SectionDonnees({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const peutDeposer = peutDeposerUnImport(roles);
  const peutValider = peutValiderLesRapprochements(roles);

  if (!peutDeposer && !peutValider) {
    return <p>Votre rôle ne porte aucun droit sur l’import de données.</p>;
  }

  return (
    <div className="administration-donnees">
      {peutDeposer ? (
        <SectionDepotEtValidation code={code} />
      ) : (
        <p>
          Votre rôle valide des rapprochements de clients dans votre périmètre, mais ne peut ni
          déposer ni lancer un import.
        </p>
      )}
    </div>
  );
}
