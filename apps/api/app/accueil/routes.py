"""`GET /entities/{code}/accueil` — LOT 8, `T8`, `MVP-L08-US001` (1/2),
`MVP-L08-US006` (1/2).

Monté APRÈS les événements (`T2`), dont il réutilise la résolution d'entité et
le gabarit de 404 — un chemin distinct pour « code d'entité inconnu »
apprendrait qu'une entité existe sans être active, exactement le défaut que ce
projet refuse depuis le LOT 4.

Aucune garde de rôle au-delà d'une session établie : la matrice §5 donne
« Lecture » aux huit rôles authentifiés pour les six ressources composées ici
(accueil, présentation, Framework, arrivées récentes, événements, liens),
sans distinction. Voir `app/accueil/lecture.py` pour la composition des cinq
sections et pourquoi aucune de leurs règles n'est recopiée ici.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.accueil.lecture import AccueilDEntite, lire_l_accueil
from app.auth.dependances import exiger_une_session
from app.content.liens import LienInterne
from app.content.pages import PageDeContenuRendue
from app.content.routes import (
    BlocDeContenuRendu,
    LienInterneServi,
    ReponseDeLaPageDeContenu,
    ReponseDesLiensInternes,
)
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.events.lecture import ClassementEvenement
from app.events.routes import EvenementRendu, ReponseDesEvenements
from app.onboarding.routes import ArriveeRecenteRendue, ReponseDesArriveesRecentes
from app.organization.framework import PageFramework, TitulaireFramework
from app.organization.routes import (
    BureauRendu,
    CercleRendu,
    ReponseDuFramework,
    ResponsabiliteRendue,
    TitulaireRendu,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres
    from app.events.lecture import PageDEvenements
    from app.onboarding.arrivees_recentes import PageDesArriveesRecentes
    from app.organization.framework import CarteDeBureau, CarteDeCercle, CarteDeResponsabilite


class ReponseDeLAccueil(BaseModel):
    """Les cinq sections de l'accueil, dans l'ordre du cahier §8.4 — `T8`.

    **LES CINQ CLÉS SONT TOUJOURS PRÉSENTES**, même vides — seule
    `presentation` peut valoir `null` (aucune page créée). Une section absente
    et une section vide donneraient la même observation côté client alors
    qu'elles ne disent pas la même chose (§7.0, quatrième proposition), exactement
    le motif déjà tenu par `ReponseDuFramework`.
    """

    presentation: ReponseDeLaPageDeContenu | None
    framework: ReponseDuFramework
    arrivees_recentes: ReponseDesArriveesRecentes
    evenements_a_venir: ReponseDesEvenements
    liens_internes: ReponseDesLiensInternes


def _presentation_en_reponse(page: PageDeContenuRendue | None) -> ReponseDeLaPageDeContenu | None:
    if page is None:
        return None
    return ReponseDeLaPageDeContenu(
        identifiant=page.identifiant,
        type_de_page=page.type_de_page,
        titre=page.titre,
        slug=page.slug,
        publiee_le=page.publiee_le,
        blocs=[
            BlocDeContenuRendu(
                identifiant=b.identifiant,
                type_de_bloc=b.type_de_bloc,
                ordre=b.ordre,
                contenu=b.contenu,
            )
            for b in page.blocs
        ],
        nombre_de_blocs=page.nombre_de_blocs,
    )


def _titulaire(titulaire: TitulaireFramework) -> TitulaireRendu:
    return TitulaireRendu(
        identifiant=titulaire.identifiant, prenom=titulaire.prenom, nom=titulaire.nom
    )


def _responsabilite(carte: CarteDeResponsabilite) -> ResponsabiliteRendue:
    return ResponsabiliteRendue(
        type_de_responsabilite=carte.type_de_responsabilite,
        titulaires=[_titulaire(t) for t in carte.titulaires],
        chemin_detaille=carte.chemin_detaille,
    )


def _cercle(carte: CarteDeCercle) -> CercleRendu:
    return CercleRendu(
        identifiant=carte.identifiant,
        code=carte.code,
        nom=carte.nom,
        description=carte.description,
        jeton_de_couleur=carte.jeton_de_couleur,
        booster=None if carte.booster is None else _titulaire(carte.booster),
        membres_actifs=carte.membres_actifs,
        chemin_detaille=carte.chemin_detaille,
    )


def _bureau(carte: CarteDeBureau) -> BureauRendu:
    return BureauRendu(
        identifiant=carte.identifiant,
        code=carte.code,
        nom=carte.nom,
        description=carte.description,
        localisation=carte.localisation,
        responsables=[_titulaire(r) for r in carte.responsables],
        chemin_detaille=carte.chemin_detaille,
    )


def _framework_en_reponse(framework: PageFramework) -> ReponseDuFramework:
    return ReponseDuFramework(
        responsabilites=[_responsabilite(r) for r in framework.responsabilites],
        cercles=[_cercle(c) for c in framework.cercles],
        bureaux=[_bureau(b) for b in framework.bureaux],
    )


def _arrivees_en_reponse(resultat: PageDesArriveesRecentes) -> ReponseDesArriveesRecentes:
    taille = int(TAILLE_PAR_DEFAUT)
    pages = -(-resultat.total // taille)
    return ReponseDesArriveesRecentes(
        arrivees=[
            ArriveeRecenteRendue(
                appartenance=a.entity_membership_id,
                person_id=a.person_id,
                first_name=a.first_name,
                last_name=a.last_name,
                preferred_name=a.preferred_name,
                arrival_date=a.arrival_date,
                short_intro=a.short_intro,
                fun_fact=a.fun_fact,
            )
            for a in resultat.arrivees
        ],
        page=1,
        taille=taille,
        total=resultat.total,
        pages=pages,
    )


def _evenements_en_reponse(resultat: PageDEvenements) -> ReponseDesEvenements:
    taille = int(TAILLE_PAR_DEFAUT)
    pages = -(-resultat.total // taille)
    return ReponseDesEvenements(
        classement=ClassementEvenement.A_VENIR,
        evenements=[
            EvenementRendu(
                identifiant=e.id,
                titre=e.title,
                description=e.description,
                commence_le=e.starts_at,
                finit_le=e.ends_at,
                lieu=e.location_text,
                etat=e.state,
                annule_le=e.cancelled_at,
                motif_d_annulation=e.cancellation_reason,
            )
            for e in resultat.evenements
        ],
        page=1,
        taille=taille,
        total=resultat.total,
        pages=pages,
    )


def _lien_en_reponse(lien: LienInterne) -> LienInterneServi:
    return LienInterneServi(
        identifiant=lien.identifiant,
        libelle=lien.libelle,
        url=lien.url,
        type_de_lien=lien.type_de_lien,
        description=lien.description,
        reference_d_icone=lien.reference_d_icone,
        rang=lien.rang,
        actif=lien.actif,
        version=lien.version,
    )


def _liens_en_reponse(liens: tuple[LienInterne, ...]) -> ReponseDesLiensInternes:
    rendus = [_lien_en_reponse(lien) for lien in liens]
    return ReponseDesLiensInternes(liens=rendus, nombre_de_liens=len(rendus))


def _accueil_en_reponse(accueil: AccueilDEntite) -> ReponseDeLAccueil:
    return ReponseDeLAccueil(
        presentation=_presentation_en_reponse(accueil.presentation),
        framework=_framework_en_reponse(accueil.framework),
        arrivees_recentes=_arrivees_en_reponse(accueil.arrivees_recentes),
        evenements_a_venir=_evenements_en_reponse(accueil.evenements_a_venir),
        liens_internes=_liens_en_reponse(accueil.liens_internes),
    )


def routeur_accueil(parametres: Parametres) -> APIRouter:
    """Routeur de l'agrégat d'accueil, monté sous le préfixe versionné."""
    routeur = APIRouter(tags=["accueil"])

    @routeur.get(
        "/entities/{code}/accueil",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLAccueil,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {"description": "Entité inconnue ou non active."},
        },
        summary="Consulter l'accueil d'une entité, dans l'ordre validé",
        description=(
            "Cahier §8.4, matrice §5, `T8`, `MVP-L08-US001` (1/2) et "
            "`MVP-L08-US006` (1/2). Compose les cinq sections déjà construites "
            "par leurs propres sous-étapes, dans l'ordre : présentation, "
            "Framework, arrivées récentes, événements à venir, liens internes. "
            "`presentation` vaut `null` si aucune page n'a encore été créée. "
            "Les deux sections paginées (arrivées, événements) rendent leur "
            "première page à la taille par défaut du cahier §18.2 ; `total` "
            "dit s'il y a davantage à montrer ailleurs."
        ),
    )
    def consulter_l_accueil(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entité consultée",
            ),
        ],
    ) -> ReponseDeLAccueil:
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            accueil = lire_l_accueil(connexion, entite=entite.id, code_entite=code, instant=instant)

        return _accueil_en_reponse(accueil)

    return routeur
