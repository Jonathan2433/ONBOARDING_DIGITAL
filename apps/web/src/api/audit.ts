/**
 * Le client du journal d'audit et de son export CSV — LOT 10, `T8`/`T9`/`T15`.
 *
 * L'EXPORT NE PASSE PAS PAR `appeler<T>` : IL NE REND PAS DU JSON
 *
 *   `POST /entities/{code}/audit/export` rend des octets (`forme: "octets"`
 *   au manifeste). `lireLeJournalDAudit` valide un corps JSON comme les
 *   autres clients ; `exporterLeJournalEnCSV` lit un `Blob` et ne le valide
 *   pas — rien à valider dans des octets.
 *
 * AUCUN JETON CSRF SUR L'EXPORT, ET CE N'EST PAS UN OUBLI
 *
 *   Mesuré dans `app/audit/routes.py` : ni `exporter_le_journal_d_audit_en_
 *   csv` ni `consulter_le_journal_d_audit` n'importent `proteger_du_csrf`,
 *   à la différence de `app/support/routes.py` et `app/privacy/routes.py`.
 *   Ce client reflète ce que l'API fait réellement, jamais ce qu'on
 *   pourrait supposer par symétrie avec les autres écritures du lot.
 */
import {
  cheminExportDuJournal,
  cheminJournalDAudit,
  EN_TETE_CORRELATION,
  type FiltresDAudit,
  type ReponseDuJournalDAudit,
  validerLeJournalDAudit,
} from '@onboarding/contracts';

import type { ReponseLue } from './profil';

export async function lireLeJournalDAudit(
  code: string,
  page: number,
  taille: number,
  filtres: FiltresDAudit = {},
  signal?: AbortSignal,
): Promise<ReponseLue<ReponseDuJournalDAudit>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(cheminJournalDAudit(code, page, taille, filtres), requete);
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: ReponseDuJournalDAudit | null;
  try {
    corps = validerLeJournalDAudit(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** Ce que l'export rend : le statut, et un `Blob` CSV si la demande a abouti. */
export interface ReponseDExport {
  readonly statut: number;
  readonly corps: Blob | null;
  readonly correlation: string | null;
}

export async function exporterLeJournalEnCSV(
  code: string,
  filtres: FiltresDAudit = {},
): Promise<ReponseDExport> {
  const reponse = await fetch(cheminExportDuJournal(code, filtres), {
    method: 'POST',
    credentials: 'same-origin',
  });
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);
  const corps = reponse.status === 200 ? await reponse.blob() : null;
  return { statut: reponse.status, corps, correlation };
}
