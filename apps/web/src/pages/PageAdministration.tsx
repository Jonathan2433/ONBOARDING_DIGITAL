/**
 * « Administration » — les SEPT groupes du cahier §8.1/§10.8 (LOT 9 `T14`),
 * plus DEUX onglets propres au LOT 10 (`T15`) : « Audit » et « Support ».
 *
 * UNE SEULE RUBRIQUE, NEUF ONGLETS DÉSORMAIS
 *
 *   `RUBRIQUES` (`routes.ts`) ne réserve toujours qu'UN chemin,
 *   `administration` (LOT 4, `T4`). Les sept groupes du cahier §8.1/§10.8
 *   (Organisation/Onboarding/Contenu/Données/Pilotage/Configuration/
 *   Super-administration) restent dans leur ORDRE d'origine. « Audit » et
 *   « Support » sont ajoutés APRÈS : le cahier les traite comme deux
 *   sujets séparés (§10.11/§10.12), jamais comme un huitième ou neuvième
 *   groupe officiel — les insérer dans la liste fixe aurait prétendu qu'ils
 *   en faisaient partie depuis toujours. Le reporting étendu (`US003`), lui,
 *   REJOINT « Pilotage » plutôt que d'ouvrir un troisième onglet :
 *   `app/reporting/lecture.py` réutilise LITTÉRALEMENT la grille du tableau
 *   de bord (`T5`/`T10`), même règle et même emplacement — voir l'en-tête
 *   de `SectionPilotage.tsx`. Arbitrage de Jonathan (`AskUserQuestion`,
 *   22/10/2026) : deux onglets de plus, jamais neuf fusionnés en un.
 *
 * LES ONGLETS SONT DESORMAIS `Onglets` (`@onboarding/ui`), SUR RADIX
 *
 *   Chantier front hors lot, sous-étape S2 (`DEC-672`). Le motif ARIA
 *   `tablist`/`tab`/`tabpanel` fabriqué à la main (neuf `<button>`, un seul
 *   `role="tabpanel"`) est remplacé par la primitive posée en S1 — même
 *   contrat accessible, plus la navigation au clavier (`ArrowLeft`/
 *   `ArrowRight`) qu'aucune des deux copies manuelles du dépôt ne rendait.
 *   `activationMode="manual"` (posé dans `Onglets.tsx`) : parcourir les neuf
 *   groupes à la flèche ne déclenche aucun appel réseau, seule une
 *   confirmation (clic, Entrée, Espace) active réellement un onglet — sans
 *   ce choix, une simple navigation au clavier monterait neuf sections,
 *   chacune appelant sa propre route.
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
 *   `peutDeposerUnImport`/`peutValiderLesRapprochements`, `peutCreerUneEntite`,
 *   `peutConsulterLAudit` — huit raisons distinctes d'ouvrir la rubrique,
 *   jamais fusionnées (même discipline que `ROLES_ADMINISTRATION`/
 *   `ROLES_ADMINISTRATION_ONBOARDING`, LOT 7 `T14`). « Support » reste
 *   visible à TOUTE session établie, comme « Pilotage » : la lecture de ses
 *   propres signalements se dégrade jusqu'à `Soi`, sans aucun rôle refusé —
 *   masquer l'onglet entier priverait certains rôles de la seule chose que
 *   la matrice leur accorde. Un onglet sans aucun droit affiche un message,
 *   jamais un appel réseau — refus par défaut, §20.1.
 *
 * UN ONGLET NE CHARGE QUE LORSQU'IL EST ACTIF
 *
 *   Contrairement à l'ancienne page (catalogue + modèles + suivi chargés
 *   ENSEMBLE, parce qu'elle n'avait qu'une section), neuf groupes chargés
 *   ensemble multiplieraient les appels pour des sections jamais regardées.
 *   Seul le panneau ACTIF est monté ; changer d'onglet démonte le précédent
 *   et monte le suivant, qui charge alors ses propres données — même parti
 *   que `PageEvenements` (LOT 8, `T9`) pour ses deux classements.
 */
import type { JSX } from 'react';
import { useState } from 'react';

import {
  peutConsulterLAudit,
  peutCreerUneEntite,
  peutDeposerUnImport,
  peutEcrireSurUnCollaborateur,
  peutGererLeCycleDeVieDeLaStructure,
  peutValiderLesRapprochements,
} from '@onboarding/contracts';
import { Onglets } from '@onboarding/ui';

import { SectionAudit } from './administration/SectionAudit';
import { SectionAVenir } from './administration/SectionAVenir';
import { SectionDonnees } from './administration/SectionDonnees';
import { peutGererLOnboarding, SectionOnboarding } from './administration/SectionOnboarding';
import { SectionOrganisation } from './administration/SectionOrganisation';
import { SectionPilotage } from './administration/SectionPilotage';
import { SectionSuperAdministration } from './administration/SectionSuperAdministration';
import { SectionSupport } from './administration/SectionSupport';
import { useEntiteConsultee } from './CadreApplicatif';

//  **DEUX ONGLETS DE PLUS, AJOUTES EN FIN DE LISTE — LOT 10, `T15`.** Le
//  cahier §10.8 n'en nomme que sept ; « Audit » et « Support » sont deux
//  sujets que le cahier traite SEPAREMENT (§10.11/§10.12), jamais comme un
//  huitieme ou neuvieme groupe officiel. Les ajouter APRES les sept plutot
//  que de les y meler dit honnetement qu'ils ne proviennent pas de la meme
//  liste. Le reporting etendu (`US003`), lui, REJOINT « Pilotage » — voir
//  l'en-tete de `SectionPilotage.tsx`. Arbitrage de Jonathan (`AskUserQuestion`,
//  22/10/2026).
type CleDeGroupe =
  | 'organisation'
  | 'onboarding'
  | 'contenu'
  | 'donnees'
  | 'pilotage'
  | 'configuration'
  | 'super-administration'
  | 'audit'
  | 'support';

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
  //  LOT 10, `T15` — deux onglets de plus, voir l'en-tete du fichier.
  { cle: 'audit', libelle: 'Audit', visible: peutConsulterLAudit },
  //  « Support » reste visible a TOUTE session, comme « Pilotage » : la
  //  lecture de ses propres signalements se degrade jusqu'a `Soi`, sans
  //  aucun role refuse.
  { cle: 'support', libelle: 'Support', visible: () => true },
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

  const groupesVisibles = GROUPES.filter((g) => g.visible(roles));
  const actif = groupesVisibles.some((g) => g.cle === groupeActif)
    ? groupeActif
    : (groupesVisibles[0]?.cle ?? null);

  //  `actif === null` exige `groupesVisibles` vide — inatteignable en
  //  pratique (Pilotage/Contenu/Configuration/Support sont visibles à
  //  TOUTE session), mais `Onglets` exige une `valeurActive` non nulle : la
  //  branche défensive reste, sans tablist vide à sa place.
  return (
    <div className="administration-page">
      {actif === null ? (
        <p>Votre rôle ne porte aucun droit d’administration dans cette entité.</p>
      ) : (
        <Onglets
          libelleDeLaListe="Groupes de l’administration"
          onChangerDOnglet={(valeur) => {
            setGroupeActif(valeur as CleDeGroupe);
          }}
          onglets={groupesVisibles.map((g) => ({ valeur: g.cle, libelle: g.libelle }))}
          valeurActive={actif}
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
          ) : actif === 'super-administration' ? (
            <SectionSuperAdministration roles={roles} />
          ) : actif === 'audit' ? (
            <SectionAudit code={entite.code} roles={roles} />
          ) : (
            <SectionSupport code={entite.code} roles={roles} />
          )}
        </Onglets>
      )}
    </div>
  );
}
