"""Les routes du reporting etendu — matrice §15.1, `T10`, `MVP-L10-US003`.

Montees apres le tableau de bord administratif (LOT 9, `T5`), dont elles
reutilisent LA MEME grille de role et LE MEME perimetre — voir l'en-tete
d'`app/reporting/lecture.py` pour la derivation complete (ce qui est ajoute,
ce qui est deliberement laisse de cote).

ROLE RE-RESOLU DANS LE CORPS, PAS LA DEPENDANCE COARSE

  Meme motif que `consulter_le_tableau_de_bord` (`app.administration.routes`)
  et `consulter_le_journal_d_audit` (`app.audit.routes`) : la dependance ne
  rend pas les roles resolus, necessaires pour choisir le perimetre — une
  SEULE resolution fraiche, dans la transaction de la route.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from app.administration.perimetre import (
    ROLES_DU_TABLEAU_DE_BORD,
    PerimetreDuTableauDeBord,
    resoudre_le_perimetre_du_tableau_de_bord,
)
from app.auth.dependances import SessionEtablie
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import resoudre_les_permissions
from app.reporting.lecture import (
    FiltresDeReporting,
    IndicateursDeReporting,
    OnboardingDuDetail,
    ProfilIncomplet,
    lire_les_indicateurs,
    lister_le_detail_onboarding,
    lister_les_profils_incomplets,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

_DESCRIPTION_401: Final = "Aucune session valide."
_DESCRIPTION_403: Final = "`acces_refuse` : aucun des cinq roles du §15.1 dans cette entite."
_DESCRIPTION_404: Final = "Code d'entite inconnu, ou entite non active."
_DESCRIPTION_FILTRES = (
    "Filtrer par periode (`depuis`/`jusqua`, bornant `arrival_date`), par DSM, "
    "par cercle ou par client — §15.1, axe transversal, jamais une escalade "
    "au-dela du perimetre deja resolu."
)


class RepartitionParGroupeRendue(BaseModel):
    """Une ligne d'une des trois repartitions — §10.10."""

    identifiant: uuid.UUID
    libelle: str
    profils_actifs: int


class ProgressionAgregeeRendue(BaseModel):
    """Le couple somme sur la portee — jamais un pourcentage, voir l'en-tete
    d'`app/reporting/lecture.py`."""

    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


class ReponseDesIndicateurs(BaseModel):
    """Ce que le tableau de bord (LOT 9, `T5`) ne sert pas — voir l'en-tete
    d'`app/reporting/lecture.py`."""

    onboardings_termines: int
    progression_moyenne: ProgressionAgregeeRendue
    duree_moyenne_jours: float | None
    arrivees_30_jours: int
    repartition_par_cercle: list[RepartitionParGroupeRendue]
    repartition_par_client: list[RepartitionParGroupeRendue]
    repartition_par_dsm: list[RepartitionParGroupeRendue]


class OnboardingDuDetailRendu(BaseModel):
    """Une ligne de « Consulter le detail onboarding » — §15.1."""

    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    prenom: str
    nom: str
    date_de_reference: dt.date
    debute_le: dt.datetime
    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


class ReponseDuDetailOnboarding(BaseModel):
    """Une page, meme forme que `ReponseDuSuivi`/`ReponseDuJournalDAudit`."""

    elements: list[OnboardingDuDetailRendu]
    page: int
    taille: int
    total: int
    pages: int


class ProfilIncompletRendu(BaseModel):
    """Une ligne de « Consulter les profils incomplets » — §15.1, le DETAIL."""

    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    prenom: str
    nom: str
    metier_manquant: bool
    cercle_principal_manquant: bool
    dsm_manquant: bool
    statut_manquant: bool


class ReponseDesProfilsIncomplets(BaseModel):
    """Une page, meme forme que les autres pages du module."""

    elements: list[ProfilIncompletRendu]
    page: int
    taille: int
    total: int
    pages: int


def _indicateurs_en_reponse(indicateurs: IndicateursDeReporting) -> ReponseDesIndicateurs:
    return ReponseDesIndicateurs(
        onboardings_termines=indicateurs.onboardings_termines,
        progression_moyenne=ProgressionAgregeeRendue(
            taches_obligatoires_totales=indicateurs.progression_moyenne.taches_obligatoires_totales,
            taches_obligatoires_terminees=(
                indicateurs.progression_moyenne.taches_obligatoires_terminees
            ),
        ),
        duree_moyenne_jours=indicateurs.duree_moyenne_jours,
        arrivees_30_jours=indicateurs.arrivees_30_jours,
        repartition_par_cercle=[
            RepartitionParGroupeRendue(
                identifiant=g.id, libelle=g.libelle, profils_actifs=g.profils_actifs
            )
            for g in indicateurs.repartition_par_cercle
        ],
        repartition_par_client=[
            RepartitionParGroupeRendue(
                identifiant=g.id, libelle=g.libelle, profils_actifs=g.profils_actifs
            )
            for g in indicateurs.repartition_par_client
        ],
        repartition_par_dsm=[
            RepartitionParGroupeRendue(
                identifiant=g.id, libelle=g.libelle, profils_actifs=g.profils_actifs
            )
            for g in indicateurs.repartition_par_dsm
        ],
    )


def _detail_en_reponse(detail: OnboardingDuDetail) -> OnboardingDuDetailRendu:
    return OnboardingDuDetailRendu(
        appartenance_id=detail.appartenance_id,
        person_id=detail.person_id,
        prenom=detail.first_name,
        nom=detail.last_name,
        date_de_reference=detail.reference_date,
        debute_le=detail.started_at,
        taches_obligatoires_totales=detail.taches_obligatoires_totales,
        taches_obligatoires_terminees=detail.taches_obligatoires_terminees,
    )


def _profil_incomplet_en_reponse(profil: ProfilIncomplet) -> ProfilIncompletRendu:
    return ProfilIncompletRendu(
        appartenance_id=profil.appartenance_id,
        person_id=profil.person_id,
        prenom=profil.first_name,
        nom=profil.last_name,
        metier_manquant=profil.metier_manquant,
        cercle_principal_manquant=profil.cercle_principal_manquant,
        dsm_manquant=profil.dsm_manquant,
        statut_manquant=profil.statut_manquant,
    )


def routeur_reporting(parametres: Parametres) -> APIRouter:
    """Routeur du reporting etendu, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["reporting"])

    garde = exiger_un_role_dans_l_entite(parametres, ROLES_DU_TABLEAU_DE_BORD)

    def _resoudre_le_perimetre(
        code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> tuple[uuid.UUID, PerimetreDuTableauDeBord]:
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            roles = frozenset(permissions.roles)
            perimetre = resoudre_le_perimetre_du_tableau_de_bord(roles=roles)
            if perimetre is None:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
        return entite.id, perimetre

    @routeur.get(
        "/entities/{code}/reporting",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesIndicateurs,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": _DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {"description": _DESCRIPTION_403},
            status.HTTP_404_NOT_FOUND: {"description": _DESCRIPTION_404},
        },
        summary="Consulter les compteurs et repartitions du reporting etendu",
        description=(
            "Cahier §10.10, matrice §15.1, `MVP-L10-US003`. Distinct du tableau "
            "de bord administratif (LOT 9, `T5`) : onboardings termines, "
            "progression moyenne, duree moyenne, arrivees dans les 30 jours, "
            "repartitions par cercle/client/DSM. " + _DESCRIPTION_FILTRES
        ),
    )
    def consulter_les_indicateurs(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entite",
            ),
        ],
        depuis: Annotated[
            dt.date | None, Query(description="Arrivees a partir de cette date (incluse)")
        ] = None,
        jusqua: Annotated[
            dt.date | None, Query(description="Arrivees jusqu'a cette date (incluse)")
        ] = None,
        dsm: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce DSM précis")
        ] = None,
        cercle: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce cercle précis")
        ] = None,
        client: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce client précis")
        ] = None,
        appelant: SessionEtablie = Depends(garde),  # noqa: B008
    ) -> ReponseDesIndicateurs:
        """Les compteurs et repartitions du reporting etendu — cahier §10.10."""
        instant = dt.datetime.now(tz=dt.UTC)
        entite_id, perimetre = _resoudre_le_perimetre(code, appelant, instant)
        with moteur(parametres).begin() as connexion:
            indicateurs = lire_les_indicateurs(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
                instant=instant,
                filtres=FiltresDeReporting(
                    depuis=depuis, jusqua=jusqua, dsm=dsm, cercle=cercle, client=client
                ),
            )
        return _indicateurs_en_reponse(indicateurs)

    @routeur.get(
        "/entities/{code}/reporting/onboarding",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuDetailOnboarding,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": _DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {"description": _DESCRIPTION_403},
            status.HTTP_404_NOT_FOUND: {"description": _DESCRIPTION_404},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, `page` inferieure a 1."
                )
            },
        },
        summary="Consulter le detail onboarding — progression par personne",
        description=(
            "Cahier §10.10, matrice §15.1 « Consulter le detail onboarding ». "
            "Instances `active` uniquement — une instance terminee est a 100 % "
            "par definition. " + _DESCRIPTION_FILTRES
        ),
    )
    def consulter_le_detail_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entite",
            ),
        ],
        page: Annotated[int, Query(ge=1, description="Numero de page, 1-indexee")] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2"),
        ] = TAILLE_PAR_DEFAUT,
        depuis: Annotated[
            dt.date | None, Query(description="Arrivees a partir de cette date")
        ] = None,
        jusqua: Annotated[dt.date | None, Query(description="Arrivees jusqu'a cette date")] = None,
        dsm: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce DSM précis")
        ] = None,
        cercle: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce cercle précis")
        ] = None,
        client: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce client précis")
        ] = None,
        appelant: SessionEtablie = Depends(garde),  # noqa: B008
    ) -> ReponseDuDetailOnboarding:
        """Le detail onboarding, paginE — cahier §18.2."""
        instant = dt.datetime.now(tz=dt.UTC)
        entite_id, perimetre = _resoudre_le_perimetre(code, appelant, instant)
        with moteur(parametres).begin() as connexion:
            resultat = lister_le_detail_onboarding(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
                page=page,
                taille=int(taille),
                instant=instant,
                filtres=FiltresDeReporting(
                    depuis=depuis, jusqua=jusqua, dsm=dsm, cercle=cercle, client=client
                ),
            )
        pages = -(-resultat.total // int(taille))
        return ReponseDuDetailOnboarding(
            elements=[_detail_en_reponse(d) for d in resultat.elements],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    @routeur.get(
        "/entities/{code}/reporting/profils-incomplets",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesProfilsIncomplets,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": _DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {"description": _DESCRIPTION_403},
            status.HTTP_404_NOT_FOUND: {"description": _DESCRIPTION_404},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, `page` inferieure a 1."
                )
            },
        },
        summary="Consulter les profils incomplets en detail",
        description=(
            "Cahier §10.10, matrice §15.1 « Consulter les profils incomplets ». "
            "Un profil ACTIF auquel il manque au moins une de ses quatre "
            "relations organisationnelles courantes — metier, cercle principal, "
            "DSM, statut professionnel — meme regle que le tableau de bord "
            "(LOT 9, `T5`), ici en LISTE plutot qu'en compte. " + _DESCRIPTION_FILTRES
        ),
    )
    def consulter_les_profils_incomplets(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entite",
            ),
        ],
        page: Annotated[int, Query(ge=1, description="Numero de page, 1-indexee")] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2"),
        ] = TAILLE_PAR_DEFAUT,
        depuis: Annotated[
            dt.date | None, Query(description="Arrivees a partir de cette date")
        ] = None,
        jusqua: Annotated[dt.date | None, Query(description="Arrivees jusqu'a cette date")] = None,
        dsm: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce DSM précis")
        ] = None,
        cercle: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce cercle précis")
        ] = None,
        client: Annotated[
            uuid.UUID | None, Query(description="Restreint la portée à ce client précis")
        ] = None,
        appelant: SessionEtablie = Depends(garde),  # noqa: B008
    ) -> ReponseDesProfilsIncomplets:
        """Les profils incomplets, en detail et paginEs — cahier §18.2."""
        instant = dt.datetime.now(tz=dt.UTC)
        entite_id, perimetre = _resoudre_le_perimetre(code, appelant, instant)
        with moteur(parametres).begin() as connexion:
            resultat = lister_les_profils_incomplets(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
                page=page,
                taille=int(taille),
                instant=instant,
                filtres=FiltresDeReporting(
                    depuis=depuis, jusqua=jusqua, dsm=dsm, cercle=cercle, client=client
                ),
            )
        pages = -(-resultat.total // int(taille))
        return ReponseDesProfilsIncomplets(
            elements=[_profil_incomplet_en_reponse(p) for p in resultat.elements],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    return routeur
