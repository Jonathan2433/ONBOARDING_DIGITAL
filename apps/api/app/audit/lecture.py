"""Le journal d'audit en LECTURE, filtrable par perimetre — matrice §16, `T8`.

CE QUE `T8` LIVRE : `US001` ET `US002` CLOSES

  `T1` a pose les six tables, `T2` a `T7` ont cable l'ecriture sur la totalite
  des domaines metier. Aucune route de LECTURE n'existait avant celle-ci —
  `audit_event` etait une table ecrite, jamais interrogee. `T8` ferme donc les
  deux stories qui dependaient de cette lecture : `US001` (consulter un journal
  filtrable) et `US002` (sa politique de contenu et de conservation, prouvee
  PAR la lecture, jamais seulement par l'ecriture).

LES EVENEMENTS SANS ENTITE, ET L'ARBITRAGE QUI LES RESOUT

  **MESURE AVANT TOUT CODE, PAR GREP SUR LES SITES D'APPEL REELS DE `T2`** :
  les quatre ecritures d'authentification (`app/auth/services.py`,
  `sessions.py`, `comptes_de_service.py`) n'ecrivent JAMAIS `entity_id` — une
  connexion, une demande de magic link ou une revocation de session concernent
  une PERSONNE, jamais une entite. Un simple `WHERE entity_id = :entite`
  laisserait donc le journal d'une entite MUET sur les connexions de ses
  propres collaborateurs, alors que le cahier §10.11 les cite EN PREMIER parmi
  ce qui est audite.

  Arbitrage explicite de Jonathan (`AskUserQuestion`, reformule sans jargon) :
  le journal d'une entite retrouve ces evenements par l'entite ACTUELLE de
  l'acteur — son appartenance OCCUPANTE aujourd'hui (`ETATS_OCCUPANTS`,
  `app/people/modeles.py` : `future` et `active`), jamais celle qu'il avait au
  moment de l'evenement. Limite assumee et documentee : un collaborateur qui a
  change d'entite depuis voit ses connexions ANCIENNES dans sa NOUVELLE entite,
  pas celle ou elles ont eu lieu — aucune colonne ne capture ce contexte
  historique, et en ajouter une serait une migration que rien dans le corpus
  ne demande (§6.5). Meme mecanisme pour un compte de SERVICE (`service_account.
  entity_id`, nullable lui aussi) : un jeton technique scope a une entite reste
  retrouvable par elle, jamais par une entite qu'il n'a jamais servie.

LE PERIMETRE ETENDU DE BOOSTER/BUREAU, ET POURQUOI CHAQUE TYPE DE RESSOURCE
EST TRAITE SEPAREMENT

  Second arbitrage explicite de Jonathan : Booster et responsable de bureau
  voient AUSSI les evenements sur les ressources de leur perimetre, pas
  seulement sur les personnes — fidele au mot choisi par la matrice (`Cercle`/
  `Bureau`, jamais `Consultants` comme pour le DSM, voir `perimetre.py`).

  **CHAQUE RELATION A ETE MESUREE SUR LE SCHEMA REEL, PAS SUPPOSEE** — les
  21 valeurs de `resource_type` deja ecrites par `T2`-`T7` ont ete enumerees
  par grep, puis chacune confrontee a son modele SQLAlchemy pour savoir si elle
  porte une colonne (ou une relation) de rattachement a un cercle ou un bureau :

      DIRECT (une colonne sur la ligne elle-meme)
        circle, office                         — la ressource racine elle-meme
        content_page.circle_id / .office_id    — `app/content/modeles.py`
        framework_responsibility_assignment
          .circle_id / .office_id              — `app/organization/modeles.py`
        circle_membership.circle_id            — idem
        onboarding_template.scope_circle_id /
          .scope_person_id (DSM)               — `app/onboarding/modeles.py`

      UN SEUL SAUT (une table de jonction dediee)
        event -> event_circle_scope / event_office_scope / event_dsm_scope

      DEUX OU TROIS SAUTS (en remontant vers une appartenance)
        entity_membership -> circle_membership
        person -> entity_membership -> circle_membership
        onboarding_instance -> entity_membership -> circle_membership
        onboarding_instance_task -> onboarding_instance -> ...
        onboarding_template_version -> onboarding_template
        dsm_assignment -> consultant_membership_id -> circle_membership (Cercle
          seulement : un DSM n'a pas de cercle, voir CONSULTANTS ci-dessous)

      JAMAIS SCOPE PAR CERCLE NI BUREAU, MESURE PAR ABSENCE DE COLONNE
        entity, internal_link, import_batch, import_decision,
        onboarding_task_reference, technical_role_assignment, service_account,
        user_account, user_session, magic_link_request

  **UN BUREAU N'A AUCUNE TABLE D'APPARTENANCE** (`app/organization/bureaux.py`
  le dit explicitement, `ECART-059`/`DEC-576`) : le perimetre `BUREAU` ne porte
  donc NI `person` NI `entity_membership` NI `onboarding_*` — uniquement
  `office`, `content_page`, `event` et `framework_responsibility_assignment`,
  plus l'acteur (les un a trois responsables actifs du bureau). Beaucoup plus
  court que `CERCLE`, et c'est le schema qui l'impose, pas une economie.

  **`CONSULTANTS` (DSM) GARDE LA MEME ETENDUE QUE `CERCLE`, PAS SEULEMENT LES
  PERSONNES** : la mesure a trouve deux relations DIRECTES qu'une premiere
  lecture aurait manquees — `event_dsm_scope.dsm_person_id` (LOT 8, `T3`,
  `ECART-067`) et `onboarding_template.scope_person_id` quand `scope_type =
  'DSM'` (LOT 7, `T5`) — toutes deux deja posees pour des raisons sans rapport
  avec l'audit, et toutes deux signifient littéralement « ce DSM precis ».

  **L'ACTEUR EST TOUJOURS UNE CLAUSE A PART, ET ELLE COUVRE A ELLE SEULE TOUS
  LES EVENEMENTS SANS ENTITE DU PERIMETRE ETROIT** (magic link, connexion,
  session) : si un consultant/membre de cercle/responsable de bureau est
  l'ACTEUR d'un evenement, peu importe son `resource_type`, il entre dans le
  perimetre. C'est le MEME mecanisme que l'arbitrage sur `ENTITE`, applique a
  une echelle plus etroite.

DEUX REQUETES, PAGINATION IDENTIQUE AU SUIVI (LOT 7, `T12`)

  Meme discipline que `lister_les_taches_en_retard` : le total ET la page dans
  la MEME transaction, un ordre TOTAL (`occurred_at` DESC puis `id` DESC — le
  plus RECENT d'abord, lecture naturelle d'un journal, jamais l'ordre
  alphabetique d'un annuaire). Les trois tailles du cahier §18.2 sont
  REUTILISEES depuis `app.shared.pagination`.

LES « DETAILS TECHNIQUES » SONT MASQUES ICI, PAS A LA ROUTE

  `perimetre.py::a_les_details_techniques` dit QUI les voit ; cette fonction
  traduit ce booleen en `None` sur `resource_reference` et `correlation_token`
  pour qui n'y a pas droit — jamais une deuxieme forme de reponse, un seul
  schema dont deux champs sont parfois vides.

CE QUE CE MODULE NE FAIT PAS

  Aucune exclusion de contenu : §16.2/§21.1 l'exigent AU MOMENT DE L'ECRITURE
  (`T2`-`T7`), jamais ici — un filtre pose a la lecture masquerait un defaut
  d'ecriture au lieu de le faire echouer au bon endroit (meme discipline que
  `app/audit/services.py`, voir son en-tete). Aucun export (`T9`), aucun
  reporting agrege (`T10`).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import text

from app.audit.perimetre import PerimetreDAudit
from app.organization.modeles import TypeResponsabilite
from app.people.modeles import ETATS_OCCUPANTS
from app.shared.pagination import TAILLES_DE_PAGE

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

    from sqlalchemy.engine import Connection


@dataclasses.dataclass(frozen=True, slots=True)
class FiltresDAudit:
    """Les cinq axes de recherche du §16 « Rechercher et filtrer », tous
    facultatifs. Aucun n'est nomme precisement par la matrice ou le cahier —
    derives des colonnes reelles d'`audit_event`, generiquement, plutot que
    d'une liste d'axes que rien ne vient fixer (§6.4)."""

    depuis: dt.datetime | None = None
    jusqua: dt.datetime | None = None
    action_code: str | None = None
    resource_type: str | None = None
    acteur: uuid.UUID | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementDAudit:
    """Une ligne du journal — modele §21.1.

    `resource_reference` et `correlation_token` sont `None` pour qui n'a pas
    les « details techniques » (§16) — voir l'en-tete du module. Un champ
    `None` ici ne veut JAMAIS dire que la colonne est vide en base.
    """

    id: uuid.UUID
    occurred_at: dt.datetime
    action_code: str
    resource_type: str
    resource_reference: uuid.UUID | None
    summary: str
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    reason: str | None
    actor_person_id: uuid.UUID | None
    actor_service_account_id: uuid.UUID | None
    correlation_token: str | None
    retention_until: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class PageDuJournalDAudit:
    """Une page, et le total de la population — pas de la page."""

    evenements: list[EvenementDAudit]
    total: int


#  §8.4 : memes litterales que `app/organization/perimetre.py`/`bureaux.py` —
#  recopiees et non importees, motif SQL partage entre modules (§7.27, voir
#  l'en-tete de `app/onboarding/perimetre.py`).
_TYPE_BOOSTER: Final[str] = TypeResponsabilite.BOOSTER.value
_TYPE_RESPONSABLE_DE_BUREAU: Final[str] = TypeResponsabilite.OFFICE_MANAGER.value

#  ENTITE (ESM/ADM-E/SUPER) : aucune CTE, la clause porte directement sur `ae`
#  et sur l'entite consultee. Voir l'en-tete pour l'arbitrage sur les
#  evenements sans entite (authentification).
_CTE_ENTITE: Final[str] = ""
_CLAUSE_ENTITE: Final[str] = """
(
    ae.entity_id = :entite
    OR (
        ae.entity_id IS NULL
        AND EXISTS (
            SELECT 1 FROM entity_membership em_ent
            WHERE em_ent.person_id = ae.actor_person_id AND em_ent.entity_id = :entite
              AND em_ent.membership_state = ANY(:etats_occupants)
        )
    )
    OR (
        ae.entity_id IS NULL
        AND EXISTS (
            SELECT 1 FROM service_account sa_ent
            WHERE sa_ent.id = ae.actor_service_account_id AND sa_ent.entity_id = :entite
        )
    )
)
"""

#  CONSULTANTS (DSM) : voir l'en-tete pour la mesure complete des sept types de
#  ressource concernes — `person`, `entity_membership` (deux sauts via
#  `dsm_assignment`), `dsm_assignment` lui-meme, `event` (via `event_dsm_scope`,
#  LOT 8 `T3`), `onboarding_template`/`_version` (`scope_type='DSM'`, LOT 7
#  `T5`), `onboarding_instance`/`_task` (via l'appartenance du consultant).
_CTE_CONSULTANTS: Final[str] = """
WITH mes_consultants AS (
    SELECT em.id AS entity_membership_id, em.person_id AS person_id
    FROM dsm_assignment da
    JOIN entity_membership em
      ON em.id = da.consultant_membership_id AND em.entity_id = da.entity_id
    WHERE da.dsm_person_id = :acteur AND da.entity_id = :entite
      AND da.archived_at IS NULL AND da.period @> :instant
)
"""
_CLAUSE_CONSULTANTS: Final[str] = """
(
    ae.actor_person_id IN (SELECT person_id FROM mes_consultants)
    OR (ae.resource_type = 'person'
        AND ae.resource_reference IN (SELECT person_id FROM mes_consultants))
    OR (ae.resource_type = 'entity_membership'
        AND ae.resource_reference IN (SELECT entity_membership_id FROM mes_consultants))
    OR (ae.resource_type = 'dsm_assignment' AND EXISTS (
        SELECT 1 FROM dsm_assignment da_res
        WHERE da_res.id = ae.resource_reference AND da_res.dsm_person_id = :acteur
    ))
    OR (ae.resource_type = 'event' AND EXISTS (
        SELECT 1 FROM event_dsm_scope eds
        WHERE eds.event_id = ae.resource_reference AND eds.dsm_person_id = :acteur
    ))
    OR (ae.resource_type = 'onboarding_template' AND EXISTS (
        SELECT 1 FROM onboarding_template ot_cons
        WHERE ot_cons.id = ae.resource_reference
          AND ot_cons.scope_type = 'DSM' AND ot_cons.scope_person_id = :acteur
    ))
    OR (ae.resource_type = 'onboarding_template_version' AND EXISTS (
        SELECT 1 FROM onboarding_template_version otv_cons
        JOIN onboarding_template ot_cons2 ON ot_cons2.id = otv_cons.template_id
        WHERE otv_cons.id = ae.resource_reference
          AND ot_cons2.scope_type = 'DSM' AND ot_cons2.scope_person_id = :acteur
    ))
    OR (ae.resource_type = 'onboarding_instance' AND EXISTS (
        SELECT 1 FROM onboarding_instance oi_cons
        WHERE oi_cons.id = ae.resource_reference
          AND oi_cons.entity_membership_id IN (SELECT entity_membership_id FROM mes_consultants)
    ))
    OR (ae.resource_type = 'onboarding_instance_task' AND EXISTS (
        SELECT 1 FROM onboarding_instance_task oit_cons
        JOIN onboarding_instance oi_cons2 ON oi_cons2.id = oit_cons.onboarding_instance_id
        WHERE oit_cons.id = ae.resource_reference
          AND oi_cons2.entity_membership_id IN (SELECT entity_membership_id FROM mes_consultants)
    ))
)
"""

#  CERCLE (Booster) : voir l'en-tete — neuf types de ressource, la liste la
#  plus large des quatre perimetres, parce que le Booster est le seul role
#  local a agir sur une ressource organisationnelle (le cercle lui-meme), du
#  contenu ET des evenements, en plus des personnes.
_CTE_CERCLE: Final[str] = """
WITH mes_cercles AS (
    SELECT circle_id FROM framework_responsibility_assignment
    WHERE person_id = :acteur AND entity_id = :entite
      AND responsibility_type = :type_booster
      AND archived_at IS NULL AND period @> :instant
),
membres_du_cercle AS (
    SELECT em.id AS entity_membership_id, em.person_id AS person_id
    FROM circle_membership cm
    JOIN entity_membership em ON em.id = cm.entity_membership_id AND em.entity_id = cm.entity_id
    WHERE cm.entity_id = :entite AND cm.circle_id IN (SELECT circle_id FROM mes_cercles)
      AND cm.archived_at IS NULL AND cm.period @> :instant
)
"""
_CLAUSE_CERCLE: Final[str] = """
(
    ae.actor_person_id IN (SELECT person_id FROM membres_du_cercle)
    OR (ae.resource_type = 'circle'
        AND ae.resource_reference IN (SELECT circle_id FROM mes_cercles))
    OR (ae.resource_type = 'person'
        AND ae.resource_reference IN (SELECT person_id FROM membres_du_cercle))
    OR (ae.resource_type = 'entity_membership'
        AND ae.resource_reference IN (SELECT entity_membership_id FROM membres_du_cercle))
    OR (ae.resource_type = 'circle_membership' AND EXISTS (
        SELECT 1 FROM circle_membership cm_res
        WHERE cm_res.id = ae.resource_reference
          AND cm_res.circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'dsm_assignment' AND EXISTS (
        SELECT 1 FROM dsm_assignment da_cer
        JOIN circle_membership cm_cer
          ON cm_cer.entity_membership_id = da_cer.consultant_membership_id
         AND cm_cer.entity_id = da_cer.entity_id
        WHERE da_cer.id = ae.resource_reference
          AND cm_cer.circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'framework_responsibility_assignment' AND EXISTS (
        SELECT 1 FROM framework_responsibility_assignment fra_cer
        WHERE fra_cer.id = ae.resource_reference
          AND fra_cer.circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'content_page' AND EXISTS (
        SELECT 1 FROM content_page cp_cer
        WHERE cp_cer.id = ae.resource_reference
          AND cp_cer.circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'event' AND EXISTS (
        SELECT 1 FROM event_circle_scope ecs
        WHERE ecs.event_id = ae.resource_reference
          AND ecs.circle_id IN (SELECT circle_id FROM mes_cercles) AND ecs.archived_at IS NULL
    ))
    OR (ae.resource_type = 'onboarding_template' AND EXISTS (
        SELECT 1 FROM onboarding_template ot_cer
        WHERE ot_cer.id = ae.resource_reference
          AND ot_cer.scope_circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'onboarding_template_version' AND EXISTS (
        SELECT 1 FROM onboarding_template_version otv_cer
        JOIN onboarding_template ot_cer2 ON ot_cer2.id = otv_cer.template_id
        WHERE otv_cer.id = ae.resource_reference
          AND ot_cer2.scope_circle_id IN (SELECT circle_id FROM mes_cercles)
    ))
    OR (ae.resource_type = 'onboarding_instance' AND EXISTS (
        SELECT 1 FROM onboarding_instance oi_cer
        WHERE oi_cer.id = ae.resource_reference
          AND oi_cer.entity_membership_id IN (SELECT entity_membership_id FROM membres_du_cercle)
    ))
    OR (ae.resource_type = 'onboarding_instance_task' AND EXISTS (
        SELECT 1 FROM onboarding_instance_task oit_cer
        JOIN onboarding_instance oi_cer2 ON oi_cer2.id = oit_cer.onboarding_instance_id
        WHERE oit_cer.id = ae.resource_reference
          AND oi_cer2.entity_membership_id IN (SELECT entity_membership_id FROM membres_du_cercle)
    ))
)
"""

#  BUREAU (responsable de bureau) : voir l'en-tete — AUCUNE table d'appartenance
#  a un bureau n'existe (`ECART-059`/`DEC-576`), donc ni `person` ni
#  `entity_membership` ni `onboarding_*` ici, a la difference de `CERCLE`.
_CTE_BUREAU: Final[str] = """
WITH mes_bureaux AS (
    SELECT office_id FROM framework_responsibility_assignment
    WHERE person_id = :acteur AND entity_id = :entite
      AND responsibility_type = :type_responsable_de_bureau
      AND archived_at IS NULL AND period @> :instant
),
co_responsables AS (
    SELECT person_id FROM framework_responsibility_assignment
    WHERE entity_id = :entite AND office_id IN (SELECT office_id FROM mes_bureaux)
      AND responsibility_type = :type_responsable_de_bureau
      AND archived_at IS NULL AND period @> :instant
)
"""
_CLAUSE_BUREAU: Final[str] = """
(
    ae.actor_person_id IN (SELECT person_id FROM co_responsables)
    OR (ae.resource_type = 'office'
        AND ae.resource_reference IN (SELECT office_id FROM mes_bureaux))
    OR (ae.resource_type = 'framework_responsibility_assignment' AND EXISTS (
        SELECT 1 FROM framework_responsibility_assignment fra_bur
        WHERE fra_bur.id = ae.resource_reference
          AND fra_bur.office_id IN (SELECT office_id FROM mes_bureaux)
    ))
    OR (ae.resource_type = 'content_page' AND EXISTS (
        SELECT 1 FROM content_page cp_bur
        WHERE cp_bur.id = ae.resource_reference
          AND cp_bur.office_id IN (SELECT office_id FROM mes_bureaux)
    ))
    OR (ae.resource_type = 'event' AND EXISTS (
        SELECT 1 FROM event_office_scope eos
        WHERE eos.event_id = ae.resource_reference
          AND eos.office_id IN (SELECT office_id FROM mes_bureaux) AND eos.archived_at IS NULL
    ))
)
"""

_CTE_PAR_PERIMETRE: Final[Mapping[PerimetreDAudit, str]] = {
    PerimetreDAudit.ENTITE: _CTE_ENTITE,
    PerimetreDAudit.CONSULTANTS: _CTE_CONSULTANTS,
    PerimetreDAudit.CERCLE: _CTE_CERCLE,
    PerimetreDAudit.BUREAU: _CTE_BUREAU,
}
_CLAUSE_PAR_PERIMETRE: Final[Mapping[PerimetreDAudit, str]] = {
    PerimetreDAudit.ENTITE: _CLAUSE_ENTITE,
    PerimetreDAudit.CONSULTANTS: _CLAUSE_CONSULTANTS,
    PerimetreDAudit.CERCLE: _CLAUSE_CERCLE,
    PerimetreDAudit.BUREAU: _CLAUSE_BUREAU,
}


def _clause_de_filtres(filtres: FiltresDAudit) -> tuple[str, dict[str, object]]:
    """Les cinq axes de `FiltresDAudit`, assembles dynamiquement.

    **MEME DISCIPLINE QUE `app.people.trombinoscope._ou`** : une clause n'entre
    dans le texte SQL QUE si son axe est demande, jamais un `:parametre IS NULL
    OR ...` evalue a l'execution. Deux raisons, mesurees et non supposees :

    1. un parametre lie qui n'apparait QUE dans une comparaison `IS NULL` n'a
       aucun contexte de type pour PostgreSQL — `:depuis` apparaitrait comme
       deux occurrences, chacune compilee en un `$n` distinct (ce module ne
       reutilise jamais un numero), et celle de `IS NULL` resterait sans type
       inferable, risquant « could not determine data type of parameter » ;
    2. aucune valeur n'est interpolee : seule la PRESENCE d'une clause est
       dynamique, les valeurs passent toutes en parametres lies (§7.27, voir
       l'en-tete de `trombinoscope.py`).
    """
    membres: list[str] = []
    valeurs: dict[str, object] = {}
    if filtres.depuis is not None:
        membres.append("ae.occurred_at >= :depuis")
        valeurs["depuis"] = filtres.depuis
    if filtres.jusqua is not None:
        membres.append("ae.occurred_at < :jusqua")
        valeurs["jusqua"] = filtres.jusqua
    if filtres.action_code is not None:
        membres.append("ae.action_code = :action_code")
        valeurs["action_code"] = filtres.action_code
    if filtres.resource_type is not None:
        membres.append("ae.resource_type = :resource_type")
        valeurs["resource_type"] = filtres.resource_type
    if filtres.acteur is not None:
        membres.append("ae.actor_person_id = :acteur_filtre")
        valeurs["acteur_filtre"] = filtres.acteur
    if not membres:
        return "TRUE", valeurs
    return " AND ".join(membres), valeurs


_COLONNES: Final[str] = (
    "ae.id, ae.occurred_at, ae.action_code, ae.resource_type, ae.resource_reference, "
    "ae.summary, ae.old_values, ae.new_values, ae.reason, ae.actor_person_id, "
    "ae.actor_service_account_id, ae.correlation_token, ae.retention_until"
)


def lister_le_journal_d_audit(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDAudit,
    avec_details_techniques: bool,
    page: int,
    taille: int,
    instant: dt.datetime,
    filtres: FiltresDAudit | None = None,
) -> PageDuJournalDAudit:
    """La page demandee du journal d'audit dans la portee resolue, et le total.

    `perimetre` et `avec_details_techniques` sont DEJA RESOLUS par l'appelant
    (`app.audit.perimetre`) : ce module ne decide jamais QUI voit quoi, il
    traduit une decision deja prise — meme discipline que `lister_les_taches_
    en_retard` (LOT 7, `T12`).

    `instant` EST INJECTE, jamais `now()` dans la requete : les clauses
    `period @> :instant` des perimetres CERCLE/CONSULTANTS/BUREAU doivent
    pouvoir etre eprouvees a un instant choisi par un temoin, comme partout
    ailleurs dans ce lot depuis `T2` (§9.2 point 13 de `CLAUDE.md`).
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    filtres = filtres or FiltresDAudit()
    cte = _CTE_PAR_PERIMETRE[perimetre]
    clause_perimetre = _CLAUSE_PAR_PERIMETRE[perimetre]
    clause_filtres, valeurs_filtres = _clause_de_filtres(filtres)
    source = f"FROM audit_event ae WHERE ({clause_perimetre}) AND ({clause_filtres})"
    parametres: dict[str, object] = {
        "entite": entite,
        "acteur": acteur,
        "instant": instant,
        "etats_occupants": list(ETATS_OCCUPANTS),
        "type_booster": _TYPE_BOOSTER,
        "type_responsable_de_bureau": _TYPE_RESPONSABLE_DE_BUREAU,
        **valeurs_filtres,
    }

    total = int(connexion.execute(text(f"{cte} SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                f"{cte} SELECT {_COLONNES} {source} "
                "ORDER BY ae.occurred_at DESC, ae.id DESC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )

    return PageDuJournalDAudit(
        evenements=[_en_evenement(ligne, avec_details_techniques) for ligne in lignes],
        total=total,
    )


def _en_evenement(ligne: Any, avec_details_techniques: bool) -> EvenementDAudit:
    return EvenementDAudit(
        id=ligne["id"],
        occurred_at=ligne["occurred_at"],
        action_code=ligne["action_code"],
        resource_type=ligne["resource_type"],
        resource_reference=ligne["resource_reference"] if avec_details_techniques else None,
        summary=ligne["summary"],
        old_values=ligne["old_values"],
        new_values=ligne["new_values"],
        reason=ligne["reason"],
        actor_person_id=ligne["actor_person_id"],
        actor_service_account_id=ligne["actor_service_account_id"],
        correlation_token=ligne["correlation_token"] if avec_details_techniques else None,
        retention_until=ligne["retention_until"],
    )
