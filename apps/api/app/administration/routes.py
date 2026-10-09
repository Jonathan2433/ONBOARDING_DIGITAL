"""`GET /entities/{code}/administration/tableau-de-bord` — LOT 9, `T5`,
`MVP-L09-US001`.

Monté APRÈS l'accueil (`T8` du LOT 8), dont il réutilise la résolution
d'entité et le gabarit de 404 : un chemin distinct pour « code d'entité
inconnu » apprendrait qu'une entité existe sans être active.

Contrairement à l'accueil, cette route EXIGE un rôle — le §15.1 met `OFFICE`
et les rôles sans responsabilité (`EMP`) à tiret sur chacune de ses lignes.
Voir `app/administration/perimetre.py` pour la grille et son origine.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.administration.perimetre import (
    ROLES_DU_TABLEAU_DE_BORD,
    resoudre_le_perimetre_du_tableau_de_bord,
)
from app.administration.tableau_de_bord import (
    ImportEnEchec,
    TableauDeBord,
    lire_le_tableau_de_bord,
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
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = (
    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie absent, "
    "jeton inconnu, session revoquee, duree absolue depassee, inactivite depassee."
)


class ImportEnEchecRendu(BaseModel):
    """Un lot d'import récent portant au moins un problème — §10.8."""

    identifiant: uuid.UUID
    nom_du_fichier: str
    etat: str
    total_des_lignes: int
    lignes_rejetees: int
    cree_le: dt.datetime


class ReponseDuTableauDeBord(BaseModel):
    """Les six grandeurs du cahier §10.8, dans la portée de l'appelant.

    **TOUTES LES CLÉS SONT TOUJOURS PRÉSENTES**, `derniers_imports_en_echec`
    compris : une liste VIDE pour `DSM`/`BOOST` (refusés sur cette seule
    section) et une liste vide parce qu'aucun import ne pose problème
    donneraient la même observation — mais c'est le prix du §2.5, et aucune
    des deux ne doit jamais être un 403 partiel sur un agrégat qui répond 200.
    """

    profils_actifs: int
    arrivees_futures: int
    onboardings_actifs: int
    taches_en_retard: int
    profils_incomplets: int
    derniers_imports_en_echec: list[ImportEnEchecRendu]


def _import_en_reponse(echec: ImportEnEchec) -> ImportEnEchecRendu:
    return ImportEnEchecRendu(
        identifiant=echec.id,
        nom_du_fichier=echec.source_filename,
        etat=echec.state,
        total_des_lignes=echec.total_rows,
        lignes_rejetees=echec.rejected_rows,
        cree_le=echec.created_at,
    )


def _tableau_en_reponse(tableau: TableauDeBord) -> ReponseDuTableauDeBord:
    return ReponseDuTableauDeBord(
        profils_actifs=tableau.profils_actifs,
        arrivees_futures=tableau.arrivees_futures,
        onboardings_actifs=tableau.onboardings_actifs,
        taches_en_retard=tableau.taches_en_retard,
        profils_incomplets=tableau.profils_incomplets,
        derniers_imports_en_echec=[
            _import_en_reponse(e) for e in tableau.derniers_imports_en_echec
        ],
    )


def routeur_administration(parametres: Parametres) -> APIRouter:
    """Routeur du tableau de bord administratif, monté sous le préfixe versionné."""
    routeur = APIRouter(tags=["administration"])

    garde_du_tableau_de_bord = exiger_un_role_dans_l_entite(parametres, ROLES_DU_TABLEAU_DE_BORD)

    @routeur.get(
        "/entities/{code}/administration/tableau-de-bord",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuTableauDeBord,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun des cinq rôles du §15.1 dans cette entité."
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code d'entité inconnu, ou entité non active."
            },
        },
        summary="Consulter le tableau de bord administratif d'une entité",
        description=(
            "Cahier §10.8, matrice §15.1, `MVP-L09-US001`. Six grandeurs "
            "comptabilisées dans la portée de l'appelant : `ESM`/`ADM-E`/"
            "`SUPER` voient toute l'entité, `DSM` ses consultants, `BOOST` "
            "son cercle — `OFFICE` et les rôles sans responsabilité sont "
            "refusés, comme sur chaque ligne du §15.1.<br><br>"
            "**`profils incomplets`** : un profil ACTIF auquel il manque au "
            "moins une de ses quatre relations courantes — métier, cercle "
            "principal, DSM, statut professionnel — la même notion que "
            "`relations_a_redonner` après une restauration (LOT 5, "
            "`T8`).<br><br>"
            "**`derniers imports en échec`** : les cinq lots d'import les "
            "plus récents portant au moins un problème (`failed`, ou au "
            "moins une ligne rejetée) — visible seulement d'`ESM`/`ADM-E`/"
            "`SUPER`, liste vide pour `DSM`/`BOOST`."
        ),
    )
    def consulter_le_tableau_de_bord(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entité consultée",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_du_tableau_de_bord),  # noqa: B008
    ) -> ReponseDuTableauDeBord:
        """Le tableau de bord administratif — cahier §10.8."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  Résolues DANS cette transaction, pas reprises de la garde :
            #  celle-ci a résolu les siennes dans sa propre connexion et à
            #  son propre instant — même motif que `_resoudre_le_cycle`
            #  (`app.people.routes`) et `_agir` (`app.content.routes`).
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            roles = frozenset(permissions.roles)
            perimetre = resoudre_le_perimetre_du_tableau_de_bord(roles=roles)
            if perimetre is None:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            tableau = lire_le_tableau_de_bord(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=roles,
                perimetre=perimetre,
                instant=instant,
            )

        return _tableau_en_reponse(tableau)

    return routeur
