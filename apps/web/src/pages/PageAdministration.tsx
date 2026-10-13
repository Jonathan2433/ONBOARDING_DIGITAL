/**
 * « Administration » — les SEPT groupes du cahier §8.1/§10.8, LOT 9 `T14`.
 *
 * UNE SEULE RUBRIQUE, SEPT ONGLETS — « PREMIER ET SEUL ÉCRAN DU LOT »
 *
 *   `RUBRIQUES` (`routes.ts`) ne réserve toujours qu'UN chemin,
 *   `administration` (LOT 4, `T4`) — rien n'est ajouté ici. Les sept groupes
 *   Organisation/Onboarding/Contenu/Données/Pilotage/Configuration/
 *   Super-administration (cahier §8.1, §10.8) sont donc SEPT ONGLETS d'une
 *   seule page, motif WAI-ARIA `tablist`/`tab`/`tabpanel` — aucune primitive
 *   d'onglets n'existe dans `packages/ui` (mesuré, comme au LOT 8 `T9`), et en
 *   fabriquer une sans second écran consommateur serait du code non éprouvé.
 *
 * CETTE PAGE REMPLACE L'ANCIENNE `PageAdministration.tsx` MONOLITHIQUE (LOT 7 `T14`)
 *
 *   Le catalogue des tâches et les modèles d'onboarding, construits par le
 *   LOT 7, deviennent l'onglet « Onboarding » SANS AUCUNE RÈGLE CHANGÉE — voir
 *   `administration/SectionOnboarding.tsx`. Le suivi des tâches en retard
 *   rejoint « Pilotage », son groupe propre au cahier §10.8 (« rapports »).
 *
 * CHAQUE ONGLET SE GARDE LUI-MÊME, CET ÉCRAN NE DÉCIDE RIEN
 *
 *   `peutGererLOnboarding`, `peutEcrireSurUnCollaborateur`,
 *   `peutGererLeCycleDeVieDeLaStructure`, `peutConsulterLeTableauDeBord`,
 *   `peutDeposerUnImport`/`peutValiderLesRapprochements`, `peutCreerUneEntite`
 *   — sept raisons distinctes d'ouvrir la rubrique, jamais fusionnées (même
 *   discipline que `ROLES_ADMINISTRATION`/`ROLES_ADMINISTRATION_ONBOARDING`,
 *   LOT 7 `T14`). Un onglet sans aucun droit affiche un message, jamais un
 *   appel réseau — refus par défaut, §20.1.
 *
 * UN ONGLET NE CHARGE QUE LORSQU'IL EST ACTIF
 *
 *   Contrairement à l'ancienne page (catalogue + modèles + suivi chargés
 *   ENSEMBLE, parce qu'elle n'avait qu'une section), sept groupes chargés
 *   ensemble multiplieraient les appels pour des sections jamais regardées.
 *   Seul le panneau ACTIF est monté ; changer d'onglet démonte le précédent
 *   et monte le suivant, qui charge alors ses propres données — même parti
 *   que `PageEvenements` (LOT 8, `T9`) pour ses deux classements.
 */
import type { JSX } from 'react';
import { useState } from 'react';

import {
  peutCreerUneEntite,
  peutDeposerUnImport,
  peutEcrireSurUnCollaborateur,
  peutGererLeCycleDeVieDeLaStructure,
  peutValiderLesRapprochements,
} from '@onboarding/contracts';

import { SectionAVenir } from './administration/SectionAVenir';
import { SectionDonnees } from './administration/SectionDonnees';
import { peutGererLOnboarding, SectionOnboarding } from './administration/SectionOnboarding';
import { SectionOrganisation } from './administration/SectionOrganisation';
import { SectionPilotage } from './administration/SectionPilotage';
import { SectionSuperAdministration } from './administration/SectionSuperAdministration';
import { useEntiteConsultee } from './CadreApplicatif';

type CleDeGroupe =
  | 'organisation'
  | 'onboarding'
  | 'contenu'
  | 'donnees'
  | 'pilotage'
  | 'configuration'
  | 'super-administration';

interface Groupe {
  readonly cle: CleDeGroupe;
  /** La formulation du cahier §10.8/§8.1. */
  readonly libelle: string;
  readonly visible: (roles: readonly string[] | null) => boolean;
}

/**
 * Les SEPT groupes, dans l'ordre du cahier §8.1/§10.8 — jamais réordonnés.
 *
 * `visible` DÉCIDE DE L'ONGLET, PAS DE SON CONTENU : un onglet « visible »
 * peut encore afficher un message de refus pour UNE PARTIE de son contenu
 * (ex. Organisation : écriture ET cycle de vie de structure sont deux droits
 * distincts, `SectionOrganisation` l'arbitre en interne).
 */
const GROUPES: readonly Groupe[] = [
  {
    cle: 'organisation',
    libelle: 'Organisation',
    visible: (r) => peutEcrireSurUnCollaborateur(r) || peutGererLeCycleDeVieDeLaStructure(r),
  },
  { cle: 'onboarding', libelle: 'Onboarding', visible: peutGererLOnboarding },
  { cle: 'contenu', libelle: 'Contenu', visible: () => true },
  {
    cle: 'donnees',
    libelle: 'Données',
    visible: (r) => peutDeposerUnImport(r) || peutValiderLesRapprochements(r),
  },
  { cle: 'pilotage', libelle: 'Pilotage', visible: () => true },
  { cle: 'configuration', libelle: 'Configuration', visible: () => true },
  { cle: 'super-administration', libelle: 'Super-administration', visible: peutCreerUneEntite },
];

export function PageAdministration(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const roles = permissions?.roles ?? null;
  const [groupeActif, setGroupeActif] = useState<CleDeGroupe>('organisation');

  if (permissions === null) {
    return (
      <p className="administration-chargement" role="status">
        Chargement de vos droits…
      </p>
    );
  }

  const idDuPanneau = 'administration-panneau';
  const groupesVisibles = GROUPES.filter((g) => g.visible(roles));
  const actif = groupesVisibles.some((g) => g.cle === groupeActif)
    ? groupeActif
    : (groupesVisibles[0]?.cle ?? null);

  return (
    <div className="administration-page">
      <div
        aria-label="Groupes de l’administration"
        className="administration-onglets"
        role="tablist"
      >
        {groupesVisibles.map((g) => (
          <button
            aria-controls={idDuPanneau}
            aria-selected={actif === g.cle}
            className="administration-onglet"
            data-selectionne={actif === g.cle}
            id={`administration-onglet-${g.cle}`}
            key={g.cle}
            onClick={() => {
              setGroupeActif(g.cle);
            }}
            role="tab"
            type="button"
          >
            {g.libelle}
          </button>
        ))}
      </div>
      {actif === null ? (
        <p>Votre rôle ne porte aucun droit d’administration dans cette entité.</p>
      ) : (
        <div
          aria-labelledby={`administration-onglet-${actif}`}
          className="administration-panneau"
          id={idDuPanneau}
          role="tabpanel"
        >
          {actif === 'organisation' ? (
            <SectionOrganisation code={entite.code} roles={roles} />
          ) : actif === 'onboarding' ? (
            <SectionOnboarding code={entite.code} roles={roles} />
          ) : actif === 'contenu' ? (
            <SectionAVenir groupe="Contenu" />
          ) : actif === 'donnees' ? (
            <SectionDonnees code={entite.code} roles={roles} />
          ) : actif === 'pilotage' ? (
            <SectionPilotage code={entite.code} roles={roles} />
          ) : actif === 'configuration' ? (
            <SectionAVenir groupe="Configuration" />
          ) : (
            <SectionSuperAdministration roles={roles} />
          )}
        </div>
      )}
    </div>
  );
}
