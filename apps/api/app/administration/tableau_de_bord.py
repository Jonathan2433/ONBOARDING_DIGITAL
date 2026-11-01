"""L'agrégat du tableau de bord administratif — cahier §10.8, `T5`.

LOT 9, sous-étape `T5`, story `MVP-L09-US001` — « Profils actifs, arrivées
futures, onboardings, retards, profils incomplets et derniers imports sont
comptabilisés dans son entité. »

MÊME PATRON QUE L'ACCUEIL (LOT 8, `T8`) : COMPOSER, JAMAIS RECOPIER

  Ce module appelle les services déjà construits par leurs propres
  sous-étapes — `app.onboarding.suivi.lister_les_taches_en_retard` pour les
  tâches en retard — plutôt que de réécrire leur règle de retard. Les
  quatre autres grandeurs (profils actifs, arrivées futures, onboardings
  actifs, profils incomplets) n'ont encore AUCUN service : ce module les
  pose, en réutilisant l'IDIOME de portée déjà établi par le suivi
  (`_CLAUSE_CONSULTANTS`/`_CLAUSE_CERCLE` corrélées à un alias `em` sur
  `entity_membership`) plutôt que de l'importer — les deux modules
  déclarent leur propre grille, même discipline que `content`/`events`/
  `onboarding`, qui ne se partagent jamais leurs constantes privées
  (§7.27 : un partage à travers un soulignement serait un couplage, pas une
  dérivation).

CE QUE « PROFIL INCOMPLET » VEUT DIRE, ET CE QUE LE CAHIER NE DIT PAS

  Le terme revient cinq fois dans le cahier (§10.8, §15.1 deux fois, LOT 9
  « Inclus », et le critère du backlog lui-même) sans jamais être défini.
  Mesuré avant d'écrire une ligne : aucune notion de complétude de fiche
  n'existe dans le dépôt. Posé en question à Jonathan le 09/10/2026, avant
  tout code : « un profil ACTIF est incomplet s'il lui manque au moins une
  de ses quatre relations organisationnelles courantes » — métier, cercle
  PRINCIPAL, DSM, statut professionnel. Ce n'était pas une invention : c'était
  EXACTEMENT ce que `Restauration.relations_a_redonner` (LOT 5, `T8`) mesurait
  déjà après une restauration, la seule notion de « ce qu'il manque à un
  profil » qui existait alors dans ce dépôt. Le CLIENT n'entre pas dans le
  calcul : il est CONDITIONNEL au statut (biconditionnelle
  `mission`/`intercontract`, `T2`/`T3`), donc son absence n'est pas en soi
  un manque.

  **DEPUIS `DEC-675` (LOT 11 `T5`), LE MÉTIER N'EST PLUS L'UNE DE CES
  RELATIONS** : le champ étant redevenu facultatif partout — « nous ne
  voulons plus gérer ce champ » — continuer de compter son absence comme un
  manque aurait contredit la décision. Reposé à Jonathan avant tout code
  (`AskUserQuestion`), qui a confirmé le retrait. **Un profil ACTIF est donc
  désormais incomplet s'il lui manque au moins une de ses TROIS relations
  organisationnelles restantes** — cercle PRINCIPAL, DSM, statut
  professionnel.

CE QUE « DERNIERS IMPORTS » MONTRE, ET POURQUOI CE N'EST PAS « TOUS »

  Le cahier le nomme DEUX FOIS, et les deux fois EN PRÉCISANT : §10.8 dit
  « derniers PROBLÈMES d'import CSV », et la section LOT 9 « Inclus » dit
  « dernières ERREURS d'import ». Seule la ligne abrégée de `fiche-lot-9.md`
  dit « derniers imports », sans le qualificatif — un raccourci, pas une
  troisième source. Les deux citations qui comptent concordent : ce module
  montre les lots d'import RÉCENTS QUI ONT UN PROBLÈME (`state = 'failed'`
  ou au moins une ligne rejetée), jamais la liste complète des imports
  réussis.

  Aucun nombre n'est donné pour « derniers » — comme pour les sections de
  l'accueil au LOT 8 (`app/accueil/lecture.py`, en-tête), qui avait résolu le
  même vide en réutilisant un nombre déjà établi plutôt que d'en inventer un
  troisième : `NOMBRE_MONTRE = 5` (LOT 8, `T11`) est repris ici, pour la
  même raison — un résumé de tableau de bord n'est pas une page paginée du
  §18.2, et `TAILLE_PAR_DEFAUT` (25) serait disproportionné pour un aperçu.

QUI VOIT LES IMPORTS, ET POURQUOI CE N'EST PAS LA MÊME GRILLE

  `ROLES_DE_LECTURE_DES_IMPORTS` (`ESM`, `ADM-E`, `SUPER` seulement) est plus
  ÉTROITE que `ROLES_DU_TABLEAU_DE_BORD` : un `DSM` ou un `BOOST` qui atteint
  la route voit les cinq autres compteurs mais une liste VIDE d'imports —
  rapporté structurellement, jamais tu (§7.20), jamais un 403 partiel sur un
  agrégat qui rend par ailleurs un 200.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.administration.perimetre import (
    ROLES_DE_LECTURE_DES_IMPORTS,
    PerimetreDuTableauDeBord,
)
from app.onboarding.perimetre import resoudre_le_perimetre_du_suivi
from app.onboarding.suivi import lister_les_taches_en_retard
from app.permissions.services import RoleDeLaMatrice
from app.shared.pagination import TAILLE_PAR_DEFAUT

#  LOT 8, `T11` : même nombre, même motif — un résumé de tableau de bord
#  n'est pas une page du §18.2, et `TAILLE_PAR_DEFAUT` y serait disproportionné.
NOMBRE_D_IMPORTS_MONTRES: Final = 5

#  Même littérale que `app.onboarding.perimetre._TYPE_BOOSTER` — recopiée et
#  non importée, motif SQL partagé entre deux modules distincts (§7.27).
_TYPE_BOOSTER: Final[str] = "BOOSTER"

#  Une clause par portée, corrélée à `em` (alias de `entity_membership`).
#  `ENTITE` n'a besoin d'aucune restriction : le filtre `entity_id = :entite`
#  de chaque requête suffit déjà.
_CLAUSE_CONSULTANTS: Final[str] = """
EXISTS (
    SELECT 1 FROM dsm_assignment da
    WHERE da.consultant_membership_id = em.id AND da.dsm_person_id = :acteur
      AND da.entity_id = :entite AND da.archived_at IS NULL AND da.period @> :instant
)
"""

_CLAUSE_CERCLE: Final[str] = """
EXISTS (
    SELECT 1 FROM circle_membership cm
    JOIN framework_responsibility_assignment fra
      ON fra.circle_id = cm.circle_id AND fra.entity_id = cm.entity_id
    WHERE cm.entity_membership_id = em.id AND cm.archived_at IS NULL AND cm.period @> :instant
      AND fra.person_id = :acteur AND fra.entity_id = :entite
      AND fra.responsibility_type = :type_booster
      AND fra.archived_at IS NULL AND fra.period @> :instant
)
"""

_CLAUSES_PAR_PERIMETRE: Final[Mapping[PerimetreDuTableauDeBord, str]] = {
    PerimetreDuTableauDeBord.ENTITE: "TRUE",
    PerimetreDuTableauDeBord.CONSULTANTS: _CLAUSE_CONSULTANTS,
    PerimetreDuTableauDeBord.CERCLE: _CLAUSE_CERCLE,
}

_COMPTER_PROFILS_ACTIFS: Final = """
SELECT count(*) FROM entity_membership em
WHERE em.entity_id = :entite AND em.membership_state = 'active' AND ({clause})
"""

_COMPTER_ARRIVEES_FUTURES: Final = """
SELECT count(*) FROM entity_membership em
WHERE em.entity_id = :entite AND em.membership_state = 'future' AND ({clause})
"""

_COMPTER_ONBOARDINGS_ACTIFS: Final = """
SELECT count(*)
  FROM onboarding_instance oi
  JOIN entity_membership em
    ON em.id = oi.entity_membership_id AND em.entity_id = oi.entity_id
 WHERE oi.entity_id = :entite AND oi.state = 'active' AND ({clause})
"""

#  Les TROIS relations organisationnelles courantes — voir l'en-tête du
#  module : le métier en est RETIRÉ depuis `DEC-675` (LOT 11 `T5`), les deux
#  autres restent exactement celles que `Restauration.relations_a_redonner`
#  (LOT 5, `T8`) mesure. Le CLIENT n'y entre pas : conditionnel au statut,
#  son absence seule n'est pas un manque (`T2`/`T3`).
_COMPTER_PROFILS_INCOMPLETS: Final = """
SELECT count(*) FROM entity_membership em
WHERE em.entity_id = :entite AND em.membership_state = 'active' AND ({clause})
  AND (
    NOT EXISTS (
        SELECT 1 FROM circle_membership cm
        WHERE cm.entity_membership_id = em.id AND cm.membership_type = 'principal'
          AND cm.ends_at IS NULL
    )
    OR NOT EXISTS (
        SELECT 1 FROM dsm_assignment da
        WHERE da.consultant_membership_id = em.id AND da.ends_at IS NULL
    )
    OR NOT EXISTS (
        SELECT 1 FROM professional_status_assignment psa
        WHERE psa.entity_membership_id = em.id AND psa.ends_at IS NULL
    )
  )
"""

_LISTER_LES_IMPORTS_EN_ECHEC: Final = text(
    """
    SELECT id, source_filename, state, total_rows, rejected_rows, created_at
      FROM import_batch
     WHERE entity_id = :entite AND (state = 'failed' OR rejected_rows > 0)
     ORDER BY created_at DESC, id DESC
     LIMIT :limite
    """
)


@dataclasses.dataclass(frozen=True, slots=True)
class ImportEnEchec:
    """Un lot d'import récent portant au moins un problème."""

    id: uuid.UUID
    source_filename: str
    state: str
    total_rows: int
    rejected_rows: int
    created_at: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class TableauDeBord:
    """Les six grandeurs du cahier §10.8, dans la portée résolue de l'acteur."""

    profils_actifs: int
    arrivees_futures: int
    onboardings_actifs: int
    taches_en_retard: int
    profils_incomplets: int
    derniers_imports_en_echec: tuple[ImportEnEchec, ...]


def lire_le_tableau_de_bord(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    perimetre: PerimetreDuTableauDeBord,
    instant: dt.datetime,
) -> TableauDeBord:
    """Les six compteurs du cahier §10.8, dans la portée déjà résolue.

    `perimetre` est résolu par l'appelant (`resoudre_le_perimetre_du_tableau_
    de_bord`), même discipline que `lister_les_taches_en_retard` : ce module
    ne décide jamais qui voit quoi, il traduit une décision déjà prise.
    """
    clause = _CLAUSES_PAR_PERIMETRE[perimetre]
    parametres: dict[str, object] = {
        "entite": entite,
        "acteur": acteur,
        "instant": instant,
        "type_booster": _TYPE_BOOSTER,
    }

    profils_actifs = int(
        connexion.execute(
            text(_COMPTER_PROFILS_ACTIFS.format(clause=clause)), parametres
        ).scalar_one()
    )
    arrivees_futures = int(
        connexion.execute(
            text(_COMPTER_ARRIVEES_FUTURES.format(clause=clause)), parametres
        ).scalar_one()
    )
    onboardings_actifs = int(
        connexion.execute(
            text(_COMPTER_ONBOARDINGS_ACTIFS.format(clause=clause)), parametres
        ).scalar_one()
    )
    profils_incomplets = int(
        connexion.execute(
            text(_COMPTER_PROFILS_INCOMPLETS.format(clause=clause)), parametres
        ).scalar_one()
    )

    #  Réutilisation DIRECTE du service du suivi (LOT 7, `T12`) : sa propre
    #  portée, résolue séparément — elle peut différer de la nôtre (pas de
    #  `Soi` ici, voir l'en-tête de `administration/perimetre.py`), et c'est
    #  voulu. Seul `.total` nous intéresse ; la page elle-même ne sert à rien
    #  sur un agrégat, mais la relire éviterait une seconde requête divergente.
    #  Ne rend JAMAIS `None` — elle dégrade toujours vers `SOI` en dernier
    #  recours (voir son propre docstring). Inatteignable ici en pratique
    #  dans la branche `SOI` : la route n'admet que des rôles qui tombent
    #  tous dans `ENTITE`/`CONSULTANTS`/`CERCLE`.
    perimetre_du_suivi = resoudre_le_perimetre_du_suivi(roles=roles)
    taches_en_retard = lister_les_taches_en_retard(
        connexion,
        entite=entite,
        acteur=acteur,
        perimetre=perimetre_du_suivi,
        page=1,
        taille=int(TAILLE_PAR_DEFAUT),
        instant=instant,
    ).total

    imports_en_echec: tuple[ImportEnEchec, ...] = ()
    if roles & ROLES_DE_LECTURE_DES_IMPORTS:
        lignes = connexion.execute(
            _LISTER_LES_IMPORTS_EN_ECHEC,
            {"entite": entite, "limite": NOMBRE_D_IMPORTS_MONTRES},
        ).all()
        imports_en_echec = tuple(
            ImportEnEchec(
                id=ligne[0],
                source_filename=ligne[1],
                state=ligne[2],
                total_rows=ligne[3],
                rejected_rows=ligne[4],
                created_at=ligne[5],
            )
            for ligne in lignes
        )

    return TableauDeBord(
        profils_actifs=profils_actifs,
        arrivees_futures=arrivees_futures,
        onboardings_actifs=onboardings_actifs,
        taches_en_retard=taches_en_retard,
        profils_incomplets=profils_incomplets,
        derniers_imports_en_echec=imports_en_echec,
    )
