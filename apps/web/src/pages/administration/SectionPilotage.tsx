/**
 * « Pilotage » — le tableau de bord administratif (`US001`, LOT 9 `T5`), le
 * suivi des tâches en retard (LOT 7 `T12`), LOT 9 `T14`, et le reporting
 * étendu (`US003`, LOT 10 `T10`/`T15`).
 *
 * LE SUIVI EST DÉPLACÉ ICI, SANS AUCUNE RÈGLE CHANGÉE
 *
 *   Il vivait, non gardé, dans l'ancienne page unique d'administration (LOT 7
 *   `T14`) : « AUCUN RÔLE N'EST REFUSÉ, la portée se dégrade jusqu'à `Soi` ».
 *   Ce groupe « Pilotage » (cahier §10.8 : rapports) est son emplacement
 *   naturel, aux côtés du tableau de bord — mais la portée, la pagination et
 *   le filtrage restent EXACTEMENT ceux de `T12` du LOT 7, inchangés.
 *
 * LE REPORTING ÉTENDU REJOINT CE MÊME ONGLET, PAS UN ONGLET DE PLUS
 *
 *   `app/reporting/lecture.py` réutilise LITTÉRALEMENT `ROLES_DU_TABLEAU_DE_
 *   BORD` (LOT 9 `T5`) : les quatre premières lignes du §15.1 portent la
 *   MÊME grille que le tableau de bord — ce n'est pas une coïncidence comme
 *   pour l'audit (§7.27), c'est la même règle, donc le même emplacement.
 *   `peutConsulterLeTableauDeBord` garde donc aussi cette troisième section,
 *   jamais une seconde fonction qui redirait la même chose.
 *
 * TROIS SECTIONS, TROIS GARDES INDÉPENDANTES
 *
 *   `ROLES_TABLEAU_DE_BORD`/reporting (OFFICE exclu) et le suivi (aucun rôle
 *   exclu, dégradé à `Soi`) ne coïncident pas — chaque section se garde pour
 *   sa propre raison (§7.0 : ne jamais fusionner deux grilles qui coïncident
 *   par coïncidence).
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import { lireLeSuiviOnboarding } from '../../api/administration';
import { lireLesIndicateurs } from '../../api/reporting';
import { lireLeTableauDeBord } from '../../api/tableauDeBord';
import {
  peutConsulterLeTableauDeBord,
  TAILLE_PAR_DEFAUT,
  type Indicateurs,
  type PageDeSuiviOnboarding,
  type TableauDeBord,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

import { dateComplete } from '../PageProfil';

const LIBELLES_DES_GRANDEURS: ReadonlyArray<{
  readonly cle: keyof Pick<
    TableauDeBord,
    | 'profilsActifs'
    | 'arriveesFutures'
    | 'onboardingsActifs'
    | 'tachesEnRetard'
    | 'profilsIncomplets'
  >;
  readonly libelle: string;
}> = [
  { cle: 'profilsActifs', libelle: 'Profils actifs' },
  { cle: 'arriveesFutures', libelle: 'Arrivées futures' },
  { cle: 'onboardingsActifs', libelle: 'Onboardings actifs' },
  { cle: 'tachesEnRetard', libelle: 'Tâches en retard' },
  { cle: 'profilsIncomplets', libelle: 'Profils incomplets' },
];

/** Les six grandeurs du cahier §10.8 — `US001`. */
function SectionTableauDeBord({ tableau }: { readonly tableau: TableauDeBord }): JSX.Element {
  return (
    <section
      className="administration-tableau-de-bord"
      aria-labelledby="administration-tableau-de-bord-titre"
    >
      <h3 id="administration-tableau-de-bord-titre">Tableau de bord</h3>
      <dl className="administration-grandeurs">
        {LIBELLES_DES_GRANDEURS.map(({ cle, libelle }) => (
          <div className="administration-grandeur" key={cle}>
            <dt>{libelle}</dt>
            <dd>{tableau[cle]}</dd>
          </div>
        ))}
      </dl>
      <h4>Derniers imports en échec</h4>
      {tableau.derniersImportsEnEchec.length === 0 ? (
        <p>Aucun import en échec récemment.</p>
      ) : (
        <ul className="administration-imports-en-echec">
          {tableau.derniersImportsEnEchec.map((imp) => (
            <li key={imp.identifiant}>
              <strong>{imp.nomDuFichier}</strong> — {imp.etat} ({imp.lignesRejetees}/
              {imp.totalDesLignes} ligne(s) rejetée(s)), déposé le {dateComplete(imp.creeLe)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Les sept grandeurs du cahier §10.10 que `T5` ne sert pas déjà — `US003`. */
function SectionReportingEtendu({
  indicateurs,
}: {
  readonly indicateurs: Indicateurs;
}): JSX.Element {
  return (
    <section
      className="administration-reporting-etendu"
      aria-labelledby="administration-reporting-etendu-titre"
    >
      <h3 id="administration-reporting-etendu-titre">Reporting étendu</h3>
      <dl className="administration-grandeurs">
        <div className="administration-grandeur">
          <dt>Onboardings terminés</dt>
          <dd>{indicateurs.onboardingsTermines}</dd>
        </div>
        <div className="administration-grandeur">
          <dt>Progression moyenne</dt>
          <dd>
            {indicateurs.progressionMoyenne.tachesObligatoiresTerminees} /{' '}
            {indicateurs.progressionMoyenne.tachesObligatoiresTotales} tâche(s) obligatoire(s)
          </dd>
        </div>
        <div className="administration-grandeur">
          <dt>Durée moyenne</dt>
          <dd>
            {indicateurs.dureeMoyenneJours === null
              ? '—'
              : `${indicateurs.dureeMoyenneJours.toFixed(1)} jour(s)`}
          </dd>
        </div>
        <div className="administration-grandeur">
          <dt>Arrivées dans les 30 jours</dt>
          <dd>{indicateurs.arrivees30Jours}</dd>
        </div>
      </dl>
      {(
        [
          ['Par cercle', indicateurs.repartitionParCercle],
          ['Par client', indicateurs.repartitionParClient],
          ['Par DSM', indicateurs.repartitionParDsm],
        ] as const
      ).map(([titre, repartition]) => (
        <div className="administration-repartition" key={titre}>
          <h4>{titre}</h4>
          {repartition.length === 0 ? (
            <p>Aucune donnée.</p>
          ) : (
            <ul>
              {repartition.map((r) => (
                <li key={r.identifiant}>
                  {r.libelle} — {r.profilsActifs} profil(s) actif(s)
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </section>
  );
}

function SectionSuivi({
  suivi,
  page,
  onChangerDePage,
}: {
  readonly suivi: PageDeSuiviOnboarding;
  readonly page: number;
  readonly onChangerDePage: (page: number) => void;
}): JSX.Element {
  return (
    <section className="administration-suivi" aria-labelledby="administration-suivi-titre">
      <h3 id="administration-suivi-titre">Suivi des tâches en retard</h3>
      {suivi.taches.length === 0 ? (
        <p>Aucune tâche en retard dans votre périmètre.</p>
      ) : (
        <table className="administration-tableau-du-suivi">
          <thead>
            <tr>
              <th scope="col">Collaborateur</th>
              <th scope="col">Tâche</th>
              <th scope="col">Échéance</th>
              <th scope="col">État</th>
            </tr>
          </thead>
          <tbody>
            {suivi.taches.map((tache) => (
              <tr key={tache.id}>
                <td>
                  {tache.prenom} {tache.nom}
                </td>
                <td>{tache.titre}</td>
                <td>{dateComplete(tache.echeance)}</td>
                <td>{tache.etat}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {suivi.pages > 1 ? (
        <div className="administration-pagination" role="navigation">
          <Bouton
            disabled={page <= 1}
            onClick={() => {
              onChangerDePage(page - 1);
            }}
            type="button"
            variante="secondaire"
          >
            Page précédente
          </Bouton>
          <span>
            Page {suivi.page} / {suivi.pages}
          </span>
          <Bouton
            disabled={page >= suivi.pages}
            onClick={() => {
              onChangerDePage(page + 1);
            }}
            type="button"
            variante="secondaire"
          >
            Page suivante
          </Bouton>
        </div>
      ) : null}
    </section>
  );
}

interface Chargement {
  readonly tableau: { readonly statut: number; readonly corps: TableauDeBord | null } | null;
  readonly reporting: { readonly statut: number; readonly corps: Indicateurs | null } | null;
  readonly suivi: { readonly statut: number; readonly corps: PageDeSuiviOnboarding | null };
}

export function SectionPilotage({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const voitLeTableauDeBord = peutConsulterLeTableauDeBord(roles);
  const [charge, setCharge] = useState<Chargement | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const abandon = new AbortController();

    async function charger(): Promise<Chargement> {
      const [tableau, reporting, suivi] = await Promise.all([
        voitLeTableauDeBord ? lireLeTableauDeBord(code, abandon.signal) : Promise.resolve(null),
        voitLeTableauDeBord ? lireLesIndicateurs(code, {}, abandon.signal) : Promise.resolve(null),
        lireLeSuiviOnboarding(code, page, TAILLE_PAR_DEFAUT, abandon.signal),
      ]);
      return {
        tableau: tableau === null ? null : { statut: tableau.statut, corps: tableau.corps },
        reporting: reporting === null ? null : { statut: reporting.statut, corps: reporting.corps },
        suivi: { statut: suivi.statut, corps: suivi.corps },
      };
    }

    void charger().then(setCharge, (cause: unknown) => {
      if (!abandon.signal.aborted) {
        setCharge({
          tableau: voitLeTableauDeBord ? { statut: 0, corps: null } : null,
          reporting: voitLeTableauDeBord ? { statut: 0, corps: null } : null,
          suivi: { statut: 0, corps: null },
        });
      }
      return cause;
    });
    return () => {
      abandon.abort();
    };
  }, [code, voitLeTableauDeBord, page]);

  if (charge === null) {
    return (
      <p className="administration-chargement" role="status">
        Chargement du pilotage…
      </p>
    );
  }

  const { tableau, reporting, suivi } = charge;

  return (
    <div className="administration-pilotage">
      {!voitLeTableauDeBord ? null : tableau !== null &&
        tableau.statut === 200 &&
        tableau.corps !== null ? (
        <SectionTableauDeBord tableau={tableau.corps} />
      ) : (
        <Alerte ton={tableau?.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          Le tableau de bord n’a pas pu être chargé. Réessayez dans un instant.
        </Alerte>
      )}
      {!voitLeTableauDeBord ? null : reporting !== null &&
        reporting.statut === 200 &&
        reporting.corps !== null ? (
        <SectionReportingEtendu indicateurs={reporting.corps} />
      ) : (
        <Alerte ton={reporting?.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          Le reporting étendu n’a pas pu être chargé. Réessayez dans un instant.
        </Alerte>
      )}
      {suivi.statut === 200 && suivi.corps !== null ? (
        <SectionSuivi onChangerDePage={setPage} page={page} suivi={suivi.corps} />
      ) : (
        <Alerte ton={suivi.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          Le suivi des tâches en retard n’a pas pu être chargé. Réessayez dans un instant.
        </Alerte>
      )}
    </div>
  );
}
