"""La route du journal d'audit — matrice §16, `T8`, `US001`/`US002`.

La derivation complete — qui peut lire, dans quel perimetre, ce qui est masque
et pourquoi — est dans l'en-tete d'`app/audit/perimetre.py` et d'`app/audit/
lecture.py`. Ce module ne porte que ce qui releve de HTTP.

POURQUOI LE ROLE EST REVERIFIE DANS LE CORPS, PAS PAR LA DEPENDANCE COARSE

  `exiger_un_role_dans_l_entite` (LOT 4, `T9`) refuserait deja `EMP`/`NEW`, mais
  elle ne rend PAS les roles resolus a la route — qui en a besoin pour choisir
  le perimetre. Memes motifs que `_resoudre_l_entite_et_verifier_le_role`
  (`app.organization.routes`) et `_resoudre_le_cycle` (`app.people.routes`) :
  une SEULE resolution, dans la transaction de la route, dont le resultat sert
  ET la garde ET le perimetre — jamais deux appels a `resoudre_les_permissions`
  qui pourraient diverger d'un instant a l'autre.

LE REFUS D'UNE TAILLE OU D'UNE PAGE HORS BORNE EST UN 422 QUE JE N'ECRIS PAS

  Meme discipline que le trombinoscope et le suivi onboarding : `taille` est
  typee `TailleDePage`, `page` porte `ge=1`, et `gerer_erreur_validation`
  traduit tout refus au format du §18.3.

`action_code`/`resource_type` BORNES A 64 CARACTERES, ET CE N'EST PAS ARBITRAIRE

  C'est la largeur REELLE des colonnes (`String(64)`, `app/audit/modeles.py`) —
  aucune valeur plus longue ne pourrait jamais correspondre, borner le
  parametre de recherche a la largeur de la colonne qu'il interroge.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel
from sqlalchemy.engine import Connection

from app.audit.lecture import FiltresDAudit, lister_le_journal_d_audit
from app.audit.perimetre import (
    ROLES_DE_L_AUDIT,
    a_les_details_techniques,
    resoudre_le_perimetre_de_l_audit,
)
from app.auth.dependances import SessionEtablie, exiger_une_session
from app.configuration.settings import Parametres
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.permissions.dependances import CODE_ROLE_REFUSE, MESSAGE_ROLE_REFUSE
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

#  Largeur reelle d'`audit_event.action_code`/`.resource_type` — voir l'en-tete.
_LONGUEUR_MAXIMALE_CODE_D_AUDIT = 64


class EvenementDAuditRendu(BaseModel):
    """Une ligne du journal — modele §21.1.

    `resource_reference` et `correlation_token` sont `null` pour qui n'a pas
    les « details techniques » (§16, voir `app/audit/perimetre.py`) — jamais
    une absence de colonne, un masquage selon le role de l'appelant.
    """

    id: uuid.UUID
    occurred_at: dt.datetime
    action_code: str
    resource_type: str
    resource_reference: uuid.UUID | None
    summary: str
    old_values: dict[str, object] | None
    new_values: dict[str, object] | None
    reason: str | None
    actor_person_id: uuid.UUID | None
    actor_service_account_id: uuid.UUID | None
    correlation_token: str | None
    retention_until: dt.datetime


class ReponseDuJournalDAudit(BaseModel):
    """Une page du journal, et de quoi savoir ou l'on est — meme forme que
    `ReponseDuSuivi` (LOT 7, `T12`)."""

    evenements: list[EvenementDAuditRendu]
    page: int
    taille: int
    total: int
    pages: int


def routeur_audit(parametres: Parametres) -> APIRouter:
    """Routeur du journal d'audit, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["audit"])

    def _resoudre_l_entite_et_les_roles(
        connexion: Connection, *, code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> tuple[uuid.UUID, frozenset[RoleDeLaMatrice]]:
        """L'entite active, ET les roles — ou un refus 403/404.

        **UNE SEULE RESOLUTION, REUTILISEE POUR LA GARDE, LE PERIMETRE ET LES
        DETAILS TECHNIQUES** — meme motif que `_resoudre_l_entite_et_verifier_
        le_role` (`app.organization.routes`) : un second appel a `resoudre_les_
        permissions` pourrait tomber sur un instant different et diverger du
        premier, en silence.
        """
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
        roles = frozenset(permissions.roles)
        if not ROLES_DE_L_AUDIT & roles:
            raise ErreurApplicative(
                code=CODE_ROLE_REFUSE, message=MESSAGE_ROLE_REFUSE, statut=status.HTTP_403_FORBIDDEN
            )
        return entite.id, roles

    @routeur.get(
        "/entities/{code}/audit",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuJournalDAudit,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun des six roles du §16 dans cette entite."
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, `page` inferieure "
                    "a 1, ou un filtre de recherche hors de ses bornes."
                )
            },
        },
        summary="Consulter le journal d'audit filtrable par perimetre",
        description=(
            "Matrice §16, `T8`, `US001`/`US002`. DSM Consultants, ESM/ADM-E/SUPER "
            "Entite, Booster Cercle, responsable de bureau Bureau — chaque perimetre "
            "etendu aux autres ressources qui lui sont rattachees, pas seulement aux "
            "personnes (arbitrage de Jonathan). `resource_reference`/`correlation_token` "
            "sont masques pour qui n'a pas les details techniques (ADM-E/SUPER seuls)."
        ),
    )
    def consulter_le_journal_d_audit(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[
            int,
            Query(ge=1, description="Numero de page, 1-indexee comme celui que l'ecran affiche"),
        ] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
        depuis: Annotated[
            dt.datetime | None,
            Query(description="Occurrences a partir de cet instant (inclus), le cas echeant"),
        ] = None,
        jusqua: Annotated[
            dt.datetime | None,
            Query(description="Occurrences avant cet instant (exclu), le cas echeant"),
        ] = None,
        action_code: Annotated[
            str | None,
            Query(
                min_length=1,
                max_length=_LONGUEUR_MAXIMALE_CODE_D_AUDIT,
                description="Code d'action exact (`audit_event.action_code`)",
            ),
        ] = None,
        resource_type: Annotated[
            str | None,
            Query(
                min_length=1,
                max_length=_LONGUEUR_MAXIMALE_CODE_D_AUDIT,
                description="Type de ressource exact (`audit_event.resource_type`)",
            ),
        ] = None,
        acteur: Annotated[
            uuid.UUID | None, Query(description="Identifiant de la personne auteure de l'action")
        ] = None,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDuJournalDAudit:
        """Consulter le journal d'audit — matrice §16, `T8`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, roles = _resoudre_l_entite_et_les_roles(
                connexion, code=code, appelant=appelant, instant=instant
            )
            perimetre = resoudre_le_perimetre_de_l_audit(roles=roles)
            avec_details_techniques = a_les_details_techniques(roles=roles)
            resultat = lister_le_journal_d_audit(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
                avec_details_techniques=avec_details_techniques,
                page=page,
                taille=int(taille),
                instant=instant,
                filtres=FiltresDAudit(
                    depuis=depuis,
                    jusqua=jusqua,
                    action_code=action_code,
                    resource_type=resource_type,
                    acteur=acteur,
                ),
            )

        pages = -(-resultat.total // int(taille))
        return ReponseDuJournalDAudit(
            evenements=[
                EvenementDAuditRendu(
                    id=evenement.id,
                    occurred_at=evenement.occurred_at,
                    action_code=evenement.action_code,
                    resource_type=evenement.resource_type,
                    resource_reference=evenement.resource_reference,
                    summary=evenement.summary,
                    old_values=evenement.old_values,
                    new_values=evenement.new_values,
                    reason=evenement.reason,
                    actor_person_id=evenement.actor_person_id,
                    actor_service_account_id=evenement.actor_service_account_id,
                    correlation_token=evenement.correlation_token,
                    retention_until=evenement.retention_until,
                )
                for evenement in resultat.evenements
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    return routeur
