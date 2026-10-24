/**
 * « Audit » — le journal d'audit filtrable et son export CSV, LOT 10,
 * `T8`/`T9` (API), `T15` (ce composant), `US001`/`US002`/`US004`.
 *
 * TROIS FILTRES SEULEMENT, PAS CINQ — `acteur` RESTE UN RÉSIDU NOMMÉ
 *
 *   L'API accepte aussi `acteur` (un identifiant de personne). Aucune route
 *   ne liste les personnes toutes entités confondues pour en faire un
 *   sélecteur — même limite que `premier_administrateur` dans
 *   `SectionOrganisation.tsx` (LOT 9, `T14`). Un champ texte UUID aurait été
 *   inutilisable sans connaître l'identifiant par cœur ; il est omis plutôt
 *   qu'ajouté sous une forme qui ne servirait à personne.
 *
 * LES DÉTAILS TECHNIQUES SONT UNE COLONNE, PAS UNE DEUXIÈME TABLE
 *
 *   `resourceReference`/`correlationToken` n'apparaissent que si
 *   `peutVoirLesDetailsTechniquesDeLAudit` — l'API les rend déjà à `null`
 *   pour qui n'y a pas droit, cet écran se contente d'afficher ce qu'il
 *   reçoit (règle 5).
 *
 * L'EXPORT DÉCLENCHE UN TÉLÉCHARGEMENT RÉEL, PAS UN APERÇU
 *
 *   `URL.createObjectURL` sur le `Blob` reçu, un lien éphémère cliqué par
 *   code, puis révoqué — aucun octet n'est conservé après le clic.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import { exporterLeJournalEnCSV, lireLeJournalDAudit } from '../../api/audit';
import {
  peutExporterLAudit,
  peutVoirLesDetailsTechniquesDeLAudit,
  TAILLE_PAR_DEFAUT,
  type EvenementDAudit,
  type FiltresDAudit,
  type ReponseDuJournalDAudit,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre rôle ne donne pas accès au journal d’audit de cette entité.';
  }
  if (statut === 404) {
    return 'Cette entité est introuvable.';
  }
  return 'Le journal n’a pas pu être chargé. Réessayez dans un instant.';
}

/**
 * Poser ou retirer un champ facultatif — jamais le mettre à `undefined`.
 *
 * `exactOptionalPropertyTypes` (base TS du dépôt) refuse `{ depuis:
 * undefined }` pour un champ `depuis?: string` : un champ optionnel ABSENT
 * et un champ optionnel VALANT `undefined` sont deux choses distinctes pour
 * le compilateur, même s'ils se comportent pareil à l'exécution.
 */
function sansLeChamp<T extends object, K extends keyof T>(objet: T, champ: K): T {
  const copie = { ...objet };
  delete copie[champ];
  return copie;
}

function FiltresDuJournal({
  filtres,
  onChange,
}: {
  readonly filtres: FiltresDAudit;
  readonly onChange: (filtres: FiltresDAudit) => void;
}): JSX.Element {
  return (
    <fieldset className="administration-filtres">
      <legend>Filtrer le journal</legend>
      <label className="administration-champ">
        Depuis
        <input
          onChange={(e) => {
            const valeur = e.target.value;
            onChange(
              valeur === '' ? sansLeChamp(filtres, 'depuis') : { ...filtres, depuis: valeur },
            );
          }}
          type="datetime-local"
          value={filtres.depuis?.slice(0, 16) ?? ''}
        />
      </label>
      <label className="administration-champ">
        Jusqu’à
        <input
          onChange={(e) => {
            const valeur = e.target.value;
            onChange(
              valeur === '' ? sansLeChamp(filtres, 'jusqua') : { ...filtres, jusqua: valeur },
            );
          }}
          type="datetime-local"
          value={filtres.jusqua?.slice(0, 16) ?? ''}
        />
      </label>
      <label className="administration-champ">
        Code d’action
        <input
          onChange={(e) => {
            const valeur = e.target.value;
            onChange(
              valeur === ''
                ? sansLeChamp(filtres, 'actionCode')
                : { ...filtres, actionCode: valeur },
            );
          }}
          type="text"
          value={filtres.actionCode ?? ''}
        />
      </label>
      <label className="administration-champ">
        Type de ressource
        <input
          onChange={(e) => {
            const valeur = e.target.value;
            onChange(
              valeur === ''
                ? sansLeChamp(filtres, 'resourceType')
                : { ...filtres, resourceType: valeur },
            );
          }}
          type="text"
          value={filtres.resourceType ?? ''}
        />
      </label>
    </fieldset>
  );
}

function TableDuJournal({
  journal,
  detailsTechniques,
}: {
  readonly journal: ReponseDuJournalDAudit;
  readonly detailsTechniques: boolean;
}): JSX.Element {
  if (journal.evenements.length === 0) {
    return <p>Aucun événement ne correspond à ces filtres.</p>;
  }
  return (
    <table className="administration-tableau-du-journal">
      <thead>
        <tr>
          <th scope="col">Survenu le</th>
          <th scope="col">Action</th>
          <th scope="col">Ressource</th>
          <th scope="col">Résumé</th>
          {detailsTechniques ? <th scope="col">Référence / corrélation</th> : null}
        </tr>
      </thead>
      <tbody>
        {journal.evenements.map((e: EvenementDAudit) => (
          <tr key={e.id}>
            <td>{e.occurredAt}</td>
            <td>{e.actionCode}</td>
            <td>{e.resourceType}</td>
            <td>{e.summary}</td>
            {detailsTechniques ? (
              <td>
                {e.resourceReference ?? '—'} / {e.correlationToken ?? '—'}
              </td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SectionAudit({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const detailsTechniques = peutVoirLesDetailsTechniquesDeLAudit(roles);
  const export_ = peutExporterLAudit(roles);
  const [filtres, setFiltres] = useState<FiltresDAudit>({});
  const [page, setPage] = useState(1);
  const [charge, setCharge] = useState<{
    readonly statut: number;
    readonly corps: ReponseDuJournalDAudit | null;
  } | null>(null);
  const [exportEnCours, setExportEnCours] = useState(false);
  const [erreurExport, setErreurExport] = useState<string | null>(null);

  useEffect(() => {
    const abandon = new AbortController();
    void lireLeJournalDAudit(code, page, TAILLE_PAR_DEFAUT, filtres, abandon.signal).then(
      (reponse) => {
        setCharge({ statut: reponse.statut, corps: reponse.corps });
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
  }, [code, filtres, page]);

  async function exporter(): Promise<void> {
    setExportEnCours(true);
    setErreurExport(null);
    const reponse = await exporterLeJournalEnCSV(code, filtres);
    setExportEnCours(false);
    if (reponse.statut !== 200 || reponse.corps === null) {
      setErreurExport(messageDeRefus(reponse.statut));
      return;
    }
    const url = URL.createObjectURL(reponse.corps);
    const lien = document.createElement('a');
    lien.href = url;
    lien.download = `audit-${code}.csv`;
    lien.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="administration-audit">
      <h3>Journal d’audit</h3>
      <FiltresDuJournal
        filtres={filtres}
        onChange={(f) => {
          setPage(1);
          setFiltres(f);
        }}
      />
      {export_ ? (
        <Bouton
          disabled={exportEnCours}
          onClick={() => {
            void exporter();
          }}
          type="button"
          variante="secondaire"
        >
          {exportEnCours ? 'Export en cours…' : 'Exporter en CSV'}
        </Bouton>
      ) : null}
      {erreurExport === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreurExport}
        </Alerte>
      )}
      {charge === null ? (
        <p className="administration-chargement" role="status">
          Chargement du journal…
        </p>
      ) : charge.statut === 200 && charge.corps !== null ? (
        <>
          <TableDuJournal detailsTechniques={detailsTechniques} journal={charge.corps} />
          {charge.corps.pages > 1 ? (
            <div className="administration-pagination" role="navigation">
              <Bouton
                disabled={page <= 1}
                onClick={() => {
                  setPage(page - 1);
                }}
                type="button"
                variante="secondaire"
              >
                Page précédente
              </Bouton>
              <span>
                Page {charge.corps.page} / {charge.corps.pages}
              </span>
              <Bouton
                disabled={page >= charge.corps.pages}
                onClick={() => {
                  setPage(page + 1);
                }}
                type="button"
                variante="secondaire"
              >
                Page suivante
              </Bouton>
            </div>
          ) : null}
        </>
      ) : (
        <Alerte ton={charge.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {messageDeRefus(charge.statut)}
        </Alerte>
      )}
    </div>
  );
}
