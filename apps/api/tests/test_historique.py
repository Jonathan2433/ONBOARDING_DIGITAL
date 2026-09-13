"""L'historique organisationnel — LOT 5, `T9`, story `MVP-L05-US008`.

CE QUE CE FICHIER EPROUVE

  La GRILLE de la ligne « Audit » du §5, qui refuse `EMP` et `NEW` ;
  l'AXE DES RESPONSABILITES, plus ferme que les autres (§20 et §23.2) ;
  l'ABSENCE de grille d'etat, qui est une difference DELIBEREE avec `T7` et `T8` ;
  la DISTINCTION entre `None` -- hors perimetre -- et `[]` -- rien a montrer ;
  l'ABSENCE STRUCTURELLE de toute colonne technique ;
  et le NOMBRE de requetes, qui est le cinquieme critere de sortie du lot.

CHAQUE REFUS EST APPARIE, ET LE TEMOIN NE DIFFERE QUE PAR LA VALEUR EN CAUSE

  §7.39, et le defaut `T2-3` : une famille de refus indistinguables est satisfaite
  par une grille qui refuse TOUT. Les refus de ce fichier sont donc apparies :

    - le DSM d'un autre consultant / **le meme DSM sur SON consultant** ;
    - le Booster d'un membre SECONDAIRE / **le meme Booster sur un principal** ;
    - le responsable de bureau / le meme decor avec un ESM ;
    - et, pour l'axe des responsabilites, **un DSM qui obtient les quatre autres
      axes** : sans ce temoin, son `None` pourrait venir d'un refus global.

L'ABSENCE DE GRILLE D'ETAT EST PROUVEE PAR COMPARAISON, NON AFFIRMEE

  Un profil `archived` est lisible ici, et `resoudre_le_perimetre` le refuse sur
  le MEME decor. Les deux appels sont dans le meme test : c'est la seule
  observation qui distingue « j'ai oublie la grille d'etat » de « je ne dois pas
  en avoir ».
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import event, text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.historique import (
    HistoriqueOrganisationnel,
    PeriodeDeCercle,
    PeriodeDeDsm,
    PeriodeDeMetier,
    PeriodeDeResponsabilite,
    PeriodeDeStatut,
    lire_l_historique,
)
from app.people.modeles import SituationProfessionnelle
from app.permissions.perimetre import (
    AXES_ORGANISATIONNELS,
    ROLES_DE_L_HISTORIQUE,
    ROLES_DE_L_HISTORIQUE_DES_ROLES,
    AccesAlHistorique,
    AxeHistorique,
    resoudre_l_acces_a_l_historique,
    resoudre_le_perimetre,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur

ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
JOUR = dt.timedelta(days=1)

#  **LES COLONNES QU'AUCUNE PERIODE RENDUE NE DOIT PORTER.** Elles existent
#  toutes sur les lignes lues ; le critere dit « sans exposer les audits
#  techniques », et la parade est STRUCTURELLE (§7.35).
COLONNES_TECHNIQUES = frozenset(
    {
        "created_at",
        "updated_at",
        "created_by_person_id",
        "updated_by_person_id",
        "assigned_by_person_id",
        "version",
        "archived_at",
        "id",
    }
)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


class Compteur:
    """Compte les requetes REELLEMENT envoyees au pilote.

    **C'EST LE MOT DU CRITERE.** « Aucune requete N+1 critique » se demontre par
    un COMPTE, jamais par la lecture du code. Repris de `T3`, avec son piege :
    le branchement est dans `__enter__`, sans quoi l'ecouteur fuit sur un moteur
    **partage**.
    """

    def __init__(self, connexion: Connection) -> None:
        self.requetes: list[str] = []
        self._moteur = connexion.engine

    def __enter__(self) -> Compteur:
        event.listen(self._moteur, "before_cursor_execute", self._noter)
        return self

    def _noter(self, *args: Any, **kwargs: Any) -> None:
        _ = kwargs
        self.requetes.append(str(args[2]))

    def __exit__(self, *args: object) -> None:
        _ = args
        event.remove(self._moteur, "before_cursor_execute", self._noter)


# ---------------------------------------------------------------------------
#  Le decor. Local a ce fichier, comme ceux de `T7` et `T8`.
# ---------------------------------------------------------------------------


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        #  Un parametre PAR COLONNE : `entity.code` est `varchar(64)`, les deux
        #  autres sont `text`. §7.25.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Sujet', 'L5T9', 'active') RETURNING id"
        ),
        #  MINUSCULES : `ck_person_email_normalise_en_minuscules`. Defaut `T8-2`.
        {"affichage": adresse.lower(), "normalise": adresse.lower()},
    ).scalar_one()


def _appartenance(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID, *, etat: str = "active"
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, 'consultant', 'published') RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "arrivee": (ANCRAGE - 300 * JOUR).date(),
            #  `ck_entity_membership_depart_date_si_departed` ne vaut que pour
            #  `departed`. Defaut `T8-2`.
            "depart": (ANCRAGE - JOUR).date() if etat == "departed" else None,
            "etat": etat,
        },
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO office (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _metier(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_resp: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime | None = None,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, office_id, assigned_by_person_id, starts_at, ends_at) "
            "VALUES (:p, :e, :t, :c, :b, :p, :debut, :fin)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_resp,
            "c": cercle,
            "b": bureau,
            "debut": debut or ANCRAGE - 30 * JOUR,
            "fin": fin,
        },
    )


def _affecter_le_metier(
    cx: Connection,
    cible: uuid.UUID,
    metier: uuid.UUID,
    entite: uuid.UUID,
    *,
    debut: dt.datetime,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at, ends_at) VALUES (:c, :e, :m, :debut, :fin)"
        ),
        {"c": cible, "e": entite, "m": metier, "debut": debut, "fin": fin},
    )


def _statut(
    cx: Connection,
    cible: uuid.UUID,
    entite: uuid.UUID,
    *,
    statut: str,
    client: uuid.UUID | None,
    debut: dt.datetime,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_membership_id, entity_id, "
            "status, client_id, starts_at, ends_at) VALUES (:c, :e, :s, :cl, :debut, :fin)"
        ),
        {"c": cible, "e": entite, "s": statut, "cl": client, "debut": debut, "fin": fin},
    )


def _client(cx: Connection, nom: str, entite: uuid.UUID) -> uuid.UUID:
    """Un client ET sa liaison a l'entite : un declencheur l'exige pour une mission."""
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            #  `ck_client_canonical_name_en_minuscules`.
            "VALUES (:canonique, :affichage, 'active') RETURNING id"
        ),
        {"canonique": nom.lower(), "affichage": nom},
    ).scalar_one()
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    return client  # type: ignore[no-any-return]


def _rattacher_au_dsm(
    cx: Connection,
    cible: uuid.UUID,
    dsm: uuid.UUID,
    entite: uuid.UUID,
    *,
    debut: dt.datetime,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (consultant_membership_id, entity_id, dsm_person_id, "
            "starts_at, ends_at) VALUES (:c, :e, :d, :debut, :fin)"
        ),
        {"c": cible, "e": entite, "d": dsm, "debut": debut, "fin": fin},
    )


def _membre_de_cercle(
    cx: Connection,
    cible: uuid.UUID,
    cercle: uuid.UUID,
    entite: uuid.UUID,
    *,
    type_appartenance: str = "principal",
    debut: dt.datetime | None = None,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at, ends_at) VALUES (:c, :e, :cercle, :type, :debut, :fin)"
        ),
        {
            "c": cible,
            "e": entite,
            "cercle": cercle,
            "type": type_appartenance,
            "debut": debut or ANCRAGE - 30 * JOUR,
            "fin": fin,
        },
    )


def _acces(
    cx: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible: uuid.UUID,
    roles: set[RoleDeLaMatrice],
    instant: dt.datetime = ANCRAGE,
) -> AccesAlHistorique:
    return resoudre_l_acces_a_l_historique(
        cx, entite=entite, acteur=acteur, cible=cible, roles=frozenset(roles), instant=instant
    )


def _tout_lire(cx: Connection, entite: uuid.UUID, cible: uuid.UUID) -> HistoriqueOrganisationnel:
    historique = lire_l_historique(
        cx,
        entite=entite,
        cible=cible,
        acces=AccesAlHistorique(axes=frozenset(AxeHistorique)),
        instant=ANCRAGE,
    )
    assert historique is not None
    return historique


# ---------------------------------------------------------------------------
#  1. La grille de rôles — matrice §5 « Audit » et §20
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_LES_ROLES_de_l_historique_excluent_EMP_et_OFFICE() -> None:
    """La ligne « Audit » du §5 met `EMP`, `NEW` — et `ANON` — a TIRET.

    **`OFFICE` EN EST EXCLU POUR UN AUTRE MOTIF, ET IL EST ECRIT** : le §6.2 dit
    qu'un responsable de bureau « n'obtient aucun droit general sur les profils du
    seul fait de sa responsabilite de bureau », et **aucune table ne rattache un
    collaborateur a un bureau** — `office_id` n'existe que sur
    `framework_responsibility_assignment`, pour `OFFICE_MANAGER`. `ECART-059`.

    **UNE EGALITE, PAS UNE INCLUSION** : un test qui verifierait « l'ESM est
    dedans » passerait sur une grille qui contient les huit roles.
    """
    attendus = {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
    assert attendus == ROLES_DE_L_HISTORIQUE
    #  **LES ABSENTS DE L'ENUMERATION, NOMMES.** `RoleDeLaMatrice` ne porte que
    #  les SEPT roles qu'une session de PERSONNE peut porter : `NEW` et `SERVICE`
    #  en sont absents par construction, et `ANON` est l'absence de session. Le
    #  refus d'`EMP` et du responsable de bureau, lui, est une DECISION de cette
    #  sous-etape, et c'est celle-la qu'il faut figer — par une EGALITE, sans quoi
    #  une grille qui refuserait un role de plus passerait aussi.
    absents = {RoleDeLaMatrice.EMPLOYE, RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}
    assert absents == set(RoleDeLaMatrice) - ROLES_DE_L_HISTORIQUE


@pytest.mark.integration
def test_l_AXE_DES_RESPONSABILITES_est_le_seul_hors_du_lot_organisationnel() -> None:
    """§20 : « Consulter l'historique des roles | ESM | ADM-E | SUPER ».

    **`AXES_ORGANISATIONNELS` EST DEFINI PAR SOUSTRACTION**, jamais par une liste
    recopiee : un sixieme axe ajoute a l'enumeration y entrerait sans que personne
    y pense (§7.27). Ce test exige que la soustraction porte bien sur UN axe.
    """
    assert set(AxeHistorique) - {AxeHistorique.RESPONSABILITES} == AXES_ORGANISATIONNELS
    assert len(AXES_ORGANISATIONNELS) == len(AxeHistorique) - 1
    assert {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    } == ROLES_DE_L_HISTORIQUE_DES_ROLES


@pytest.mark.integration
@pytest.mark.parametrize(
    "role",
    [
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    ],
)
def test_les_trois_roles_d_entite_obtiennent_TOUS_les_axes(
    cx: Connection, role: RoleDeLaMatrice
) -> None:
    """Le temoin POSITIF de toute la famille de refus qui suit."""
    entite = _entite(cx, f"T9-OK-{role.value}")
    acteur = _personne(cx, f"t9-ok-{role.value}-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, f"t9-ok-{role.value}@exalt-company.com"), entite)
    assert _acces(cx, entite, acteur, cible, {role}).axes == frozenset(AxeHistorique)


@pytest.mark.integration
@pytest.mark.parametrize(
    "role",
    [RoleDeLaMatrice.EMPLOYE, RoleDeLaMatrice.RESPONSABLE_DE_BUREAU],
)
def test_EMP_et_OFFICE_n_obtiennent_AUCUN_axe(cx: Connection, role: RoleDeLaMatrice) -> None:
    """Le refus, apparie au temoin ci-dessus : meme decor, seul le role change."""
    entite = _entite(cx, f"T9-KO-{role.value}")
    acteur = _personne(cx, f"t9-ko-{role.value}-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, f"t9-ko-{role.value}@exalt-company.com"), entite)
    assert _acces(cx, entite, acteur, cible, {role}).axes == frozenset()


@pytest.mark.integration
def test_le_responsable_de_BUREAU_n_obtient_rien_MEME_avec_sa_responsabilite(
    cx: Connection,
) -> None:
    """**LE TEMOIN QUI REND LE REFUS PRECEDENT NON TRIVIAL.**

    Le refus ci-dessus pourrait venir d'un decor ou l'acteur n'a rien du tout.
    Ici il porte une responsabilite `OFFICE_MANAGER` REELLE, sur un bureau REEL,
    et il n'obtient toujours aucun axe — parce que la cible n'est rattachee a
    aucun bureau, et qu'aucune table ne le permettrait. `ECART-059`.

    Le TEMOIN inverse est dans le meme test : un `ESM` sur la meme cible obtient
    les cinq axes, donc le decor est bon.
    """
    entite = _entite(cx, "T9-BUREAU")
    bureau = _bureau(cx, entite, "T9B")
    acteur = _personne(cx, "t9-bureau-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    _responsabilite(cx, acteur, entite, TypeResponsabilite.OFFICE_MANAGER.value, bureau=bureau)
    cible = _appartenance(cx, _personne(cx, "t9-bureau-c@exalt-company.com"), entite)

    assert _acces(cx, entite, acteur, cible, {RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}).axes == (
        frozenset()
    )
    #  Le TEMOIN : la seule chose qui change est le role.
    assert _acces(cx, entite, acteur, cible, {RoleDeLaMatrice.ESM}).axes == frozenset(AxeHistorique)


@pytest.mark.integration
def test_un_DSM_obtient_les_axes_ORGANISATIONNELS_mais_PAS_les_responsabilites(
    cx: Connection,
) -> None:
    """§5 « Audit | DSM | Consultants » **et** §20, qui ne lui donne pas les roles.

    **LE §23.2 TRANCHE LE CONFLIT** : « une interdiction liee a la RESSOURCE
    prevaut sur le cumul des roles ». Les deux lignes de la matrice se
    contredisent sur cet axe, et la plus etroite gagne.

    **ET LE TEMOIN EST DANS LE MEME TEST** : le DSM obtient les QUATRE autres
    axes. Sans lui, son `None` sur les responsabilites pourrait venir d'un refus
    global — exactement le defaut `T2-3`.
    """
    entite = _entite(cx, "T9-DSM")
    dsm = _personne(cx, "t9-dsm-a@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value)
    cible = _appartenance(cx, _personne(cx, "t9-dsm-c@exalt-company.com"), entite)
    _rattacher_au_dsm(cx, cible, dsm, entite, debut=ANCRAGE - 10 * JOUR)

    axes = _acces(cx, entite, dsm, cible, {RoleDeLaMatrice.DSM}).axes
    assert axes == AXES_ORGANISATIONNELS
    assert AxeHistorique.RESPONSABILITES not in axes
    #  Le TEMOIN POSITIF, dans le meme test : quatre axes obtenus.
    assert AxeHistorique.DSM in axes
    assert len(axes) == 4


@pytest.mark.integration
def test_le_MEME_DSM_n_obtient_RIEN_sur_un_consultant_non_rattache(cx: Connection) -> None:
    """§6.2, transpose a la lecture : la portee du DSM est « ses consultants ».

    **LE REFUS EST APPARIE AU TEST PRECEDENT** : meme role, meme entite, meme
    forme de decor. La seule difference est le rattachement `dsm_assignment`.
    """
    entite = _entite(cx, "T9-DSM-AUTRE")
    dsm = _personne(cx, "t9-dsm-autre-a@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value)
    autre = _appartenance(cx, _personne(cx, "t9-dsm-autre-c@exalt-company.com"), entite)

    assert _acces(cx, entite, dsm, autre, {RoleDeLaMatrice.DSM}).axes == frozenset()


@pytest.mark.integration
def test_un_rattachement_DSM_FUTUR_n_accorde_RIEN_et_seul_l_instant_change(
    cx: Connection,
) -> None:
    """**LE TEMOIN LE PLUS UTILE DU FICHIER : SEUL L'INSTANT AVANCE.**

    `period @> :instant` et non `ends_at IS NULL` — une affectation FUTURE a elle
    aussi un `ends_at` nul. La meme ligne, le meme acteur, la meme cible : l'acces
    passe de vide a quatre axes quand l'instant franchit `starts_at`. Sans lui, le
    refus mesure pourrait venir de n'importe quel filtre trop large.
    """
    entite = _entite(cx, "T9-DSM-FUTUR")
    dsm = _personne(cx, "t9-dsm-futur-a@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE - 60 * JOUR)
    cible = _appartenance(cx, _personne(cx, "t9-dsm-futur-c@exalt-company.com"), entite)
    _rattacher_au_dsm(cx, cible, dsm, entite, debut=ANCRAGE + 10 * JOUR)

    roles = {RoleDeLaMatrice.DSM}
    assert _acces(cx, entite, dsm, cible, roles).axes == frozenset()
    assert _acces(cx, entite, dsm, cible, roles, ANCRAGE + 20 * JOUR).axes == (
        AXES_ORGANISATIONNELS
    )


@pytest.mark.integration
def test_un_BOOSTER_obtient_les_axes_sur_un_membre_PRINCIPAL_et_rien_sur_un_SECONDAIRE(
    cx: Connection,
) -> None:
    """Le meme predicat que `T7`, et la meme lecture du §6.2.

    « Pour un membre SECONDAIRE, ses actions doivent rester limitees aux donnees
    du cercle » — or l'historique des missions et des clients d'une personne n'est
    pas une donnee du cercle. Elargir donnerait a un Booster la suite des clients
    de quelqu'un dont son cercle n'est que le second.

    **Les deux cas sont dans le meme test, et ne different QUE par le type
    d'appartenance au cercle.**
    """
    entite = _entite(cx, "T9-BOOST")
    cercle = _cercle(cx, entite, "T9C")
    booster = _personne(cx, "t9-boost-a@exalt-company.com")
    _appartenance(cx, booster, entite)
    _responsabilite(cx, booster, entite, TypeResponsabilite.BOOSTER.value, cercle=cercle)

    principal = _appartenance(cx, _personne(cx, "t9-boost-p@exalt-company.com"), entite)
    _membre_de_cercle(cx, principal, cercle, entite)
    secondaire = _appartenance(cx, _personne(cx, "t9-boost-s@exalt-company.com"), entite)
    _membre_de_cercle(
        cx, secondaire, cercle, entite, type_appartenance=TypeAppartenanceCercle.SECONDARY.value
    )

    roles = {RoleDeLaMatrice.BOOSTER}
    assert _acces(cx, entite, booster, principal, roles).axes == AXES_ORGANISATIONNELS
    assert _acces(cx, entite, booster, secondaire, roles).axes == frozenset()


@pytest.mark.integration
def test_une_cible_d_une_AUTRE_entite_n_accorde_RIEN(cx: Connection) -> None:
    """§25.3 : le couple `(id, entity_id)` porte l'isolation, pas un filtre d'entite."""
    ici, ailleurs = _entite(cx, "T9-ICI"), _entite(cx, "T9-AILLEURS")
    acteur = _personne(cx, "t9-iso-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t9-iso-c@exalt-company.com"), ailleurs)
    assert _acces(cx, ici, acteur, cible, {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}).axes == (
        frozenset()
    )


# ---------------------------------------------------------------------------
#  2. L'absence de grille d'état — une différence DÉLIBÉRÉE avec `T7` et `T8`
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("etat", ["active", "future", "departed", "archived"])
def test_l_historique_est_lisible_QUEL_QUE_SOIT_l_etat(cx: Connection, etat: str) -> None:
    """**IL N'Y A PAS DE GRILLE D'ETAT ICI, ET C'EST DELIBERE.**

    `resoudre_le_perimetre` exige une appartenance occupante parce qu'on ne
    modifie pas un profil archive ; `resoudre_le_cycle_de_vie` exige un etat
    precis parce que chaque action en depend. **Lire un historique n'a aucune de
    ces raisons** — un profil parti a justement l'historique le plus interessant.
    """
    entite = _entite(cx, f"T9-ETAT-{etat}")
    acteur = _personne(cx, f"t9-etat-{etat}-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, f"t9-etat-{etat}@exalt-company.com"), entite, etat=etat)
    axes = _acces(cx, entite, acteur, cible, {RoleDeLaMatrice.ESM}).axes
    assert axes == frozenset(AxeHistorique)


@pytest.mark.integration
def test_un_ARCHIVE_est_LISIBLE_ici_et_REFUSE_a_l_ecriture_sur_le_MEME_decor(
    cx: Connection,
) -> None:
    """**LA PREUVE QUE L'ABSENCE DE GRILLE D'ETAT EST UN CHOIX, NON UN OUBLI.**

    Les deux resolutions sont appelees dans le meme test, sur la meme cible, au
    meme instant, avec le meme role le plus large. C'est la seule observation qui
    distingue « j'ai oublie la grille d'etat » de « je ne dois pas en avoir » —
    et si un lot ulterieur ajoutait une grille d'etat ici, ce test tomberait.
    """
    entite = _entite(cx, "T9-ARCHIVE")
    acteur = _personne(cx, "t9-archive-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    cible = _appartenance(
        cx, _personne(cx, "t9-archive-c@exalt-company.com"), entite, etat="archived"
    )
    roles = frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR})

    assert _acces(cx, entite, acteur, cible, set(roles)).axes == frozenset(AxeHistorique)
    #  Le MEME decor, refuse a l'ecriture — `T7`, et c'est juste.
    ecriture = resoudre_le_perimetre(
        cx, entite=entite, acteur=acteur, cible=cible, roles=roles, instant=ANCRAGE
    )
    assert ecriture.champs == frozenset()


# ---------------------------------------------------------------------------
#  3. Les lectures — périodes, ordre, et `None` contre `[]`
# ---------------------------------------------------------------------------


def _profil_avec_un_parcours(cx: Connection, entite: uuid.UUID) -> uuid.UUID:
    """Deux metiers, deux statuts dont une mission, deux cercles, deux DSM.

    **DEUX PERIODES PAR AXE, ET LA PREMIERE EST CLOSE** : un axe a une seule
    periode ouverte ne prouverait pas que l'historique rend le PASSE, ce qui est
    tout l'objet de la sous-etape.
    """
    personne = _personne(cx, "t9-parcours@exalt-company.com")
    cible = _appartenance(cx, personne, entite)

    _affecter_le_metier(
        cx,
        cible,
        _metier(cx, entite, "T9M-ancien"),
        entite,
        debut=ANCRAGE - 200 * JOUR,
        fin=ANCRAGE - 100 * JOUR,
    )
    _affecter_le_metier(
        cx, cible, _metier(cx, entite, "T9M-actuel"), entite, debut=ANCRAGE - 100 * JOUR
    )

    client = _client(cx, "T9-Client", entite)
    _statut(
        cx,
        cible,
        entite,
        statut=SituationProfessionnelle.MISSION.value,
        client=client,
        debut=ANCRAGE - 200 * JOUR,
        fin=ANCRAGE - 50 * JOUR,
    )
    _statut(
        cx,
        cible,
        entite,
        statut=SituationProfessionnelle.INTERCONTRACT.value,
        client=None,
        debut=ANCRAGE - 50 * JOUR,
    )

    cercle = _cercle(cx, entite, "T9C-parcours")
    _membre_de_cercle(
        cx, cible, cercle, entite, debut=ANCRAGE - 200 * JOUR, fin=ANCRAGE - 20 * JOUR
    )
    _membre_de_cercle(
        cx,
        cible,
        _cercle(cx, entite, "T9C-second"),
        entite,
        type_appartenance=TypeAppartenanceCercle.SECONDARY.value,
        debut=ANCRAGE - 20 * JOUR,
    )

    for suffixe, debut, fin in (
        ("ancien", ANCRAGE - 200 * JOUR, ANCRAGE - 80 * JOUR),
        ("actuel", ANCRAGE - 80 * JOUR, None),
    ):
        dsm = _personne(cx, f"t9-parcours-dsm-{suffixe}@exalt-company.com")
        _appartenance(cx, dsm, entite)
        _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE - 250 * JOUR)
        _rattacher_au_dsm(cx, cible, dsm, entite, debut=debut, fin=fin)

    _responsabilite(
        cx,
        personne,
        entite,
        TypeResponsabilite.BOOSTER.value,
        cercle=cercle,
        debut=ANCRAGE - 150 * JOUR,
        fin=ANCRAGE - 10 * JOUR,
    )
    return cible


@pytest.mark.integration
def test_LE_CRITERE_les_periodes_des_CINQ_axes_sont_lisibles(cx: Connection) -> None:
    """« Les periodes DSM, client, cercle et responsabilites sont lisibles ».

    **ET LE METIER AVEC**, arbitrage de Jonathan du 12/09/2026 : la roadmap
    inclut « historique des **affectations** », le backlog omet le metier sans
    l'exclure, et une omission n'est pas une exclusion.
    """
    entite = _entite(cx, "T9-PARCOURS")
    cible = _profil_avec_un_parcours(cx, entite)
    historique = _tout_lire(cx, entite, cible)

    assert historique.metier is not None
    assert [p.metier for p in historique.metier] == ["T9M-actuel", "T9M-ancien"]
    assert historique.statut is not None
    assert [(p.statut, p.client) for p in historique.statut] == [
        ("intercontract", None),
        ("mission", "T9-Client"),
    ]
    assert historique.cercle is not None
    assert [(p.code, p.type) for p in historique.cercle] == [
        ("T9C-second", "secondary"),
        ("T9C-parcours", "principal"),
    ]
    assert historique.dsm is not None
    assert len(historique.dsm) == 2
    assert historique.responsabilites is not None
    assert [(p.type, p.cercle, p.bureau) for p in historique.responsabilites] == [
        ("BOOSTER", "T9C-parcours", None)
    ]


@pytest.mark.integration
def test_l_ORDRE_est_le_plus_recent_d_abord_et_la_periode_courante_a_une_FIN_nulle(
    cx: Connection,
) -> None:
    """`ORDER BY starts_at DESC, id` — total, et decroissant.

    **`fin is None` DISTINGUE LA PERIODE COURANTE**, et c'est la seule chose qui
    la distingue : le service ne rend aucun champ « courant », qui serait
    derivable et donc contredisible (§7.32).
    """
    entite = _entite(cx, "T9-ORDRE")
    cible = _profil_avec_un_parcours(cx, entite)
    historique = _tout_lire(cx, entite, cible)

    assert historique.metier is not None
    debuts = [p.debut for p in historique.metier]
    assert debuts == sorted(debuts, reverse=True)
    assert historique.metier[0].fin is None
    assert historique.metier[-1].fin is not None


@pytest.mark.integration
def test_un_axe_HORS_PERIMETRE_vaut_None_et_un_axe_VIDE_vaut_une_liste(
    cx: Connection,
) -> None:
    """**`None` ET `[]` NE DISENT PAS LA MEME CHOSE, ET LES DEUX SONT EPROUVES ICI.**

    `[]` signifie « il n'y a rien a montrer » ; `None` signifie « ce n'est pas
    dans ton perimetre ». Les confondre ferait croire a un DSM que son consultant
    n'a jamais porte de responsabilite — une affirmation FAUSSE.

    Le decor donne au meme profil une responsabilite REELLE et **aucun** metier :
    un seul appel suffit donc a observer les deux formes.
    """
    entite = _entite(cx, "T9-NONE")
    personne = _personne(cx, "t9-none@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _responsabilite(cx, personne, entite, TypeResponsabilite.ESM.value)

    historique = lire_l_historique(
        cx,
        entite=entite,
        cible=cible,
        acces=AccesAlHistorique(axes=AXES_ORGANISATIONNELS),
        instant=ANCRAGE,
    )
    assert historique is not None
    #  Hors perimetre : `None`, alors qu'une responsabilite EXISTE en base.
    assert historique.responsabilites is None
    #  Dans le perimetre, mais rien a montrer : une liste VIDE.
    assert historique.metier == []


@pytest.mark.integration
def test_AUCUNE_COLONNE_TECHNIQUE_n_est_exposee_et_c_est_STRUCTUREL(cx: Connection) -> None:
    """« sans exposer les audits techniques » — §7.35, rendu structurel.

    **CE TEST PORTE SUR LES CHAMPS DES STRUCTURES, PAS SUR UNE REPONSE.** Une
    reponse peut ne rien contenir de technique par hasard — un decor ou la colonne
    est nulle. **Une structure qui n'a pas le champ ne peut pas le porter**, et le
    perdre exigerait de la reecrire.

    Les colonnes cherchees existent TOUTES sur les lignes lues : le test serait
    vide de sens si elles n'existaient pas, et une requete le verifie.
    """
    for structure in (
        PeriodeDeMetier,
        PeriodeDeStatut,
        PeriodeDeCercle,
        PeriodeDeDsm,
        PeriodeDeResponsabilite,
    ):
        champs = set(structure.__dataclass_fields__)
        interdits = champs & COLONNES_TECHNIQUES
        assert not interdits, f"{structure.__name__} porte {sorted(interdits)}"

    #  **LE TEMOIN : ces colonnes existent bel et bien**, sans quoi l'assertion
    #  ci-dessus serait satisfaite par n'importe quoi.
    presentes = {
        str(r[0])
        for r in cx.execute(
            text(
                "SELECT DISTINCT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = ANY(:tables)"
            ),
            {
                "tables": [
                    "membership_job_assignment",
                    "professional_status_assignment",
                    "circle_membership",
                    "dsm_assignment",
                    "framework_responsibility_assignment",
                ]
            },
        )
    }
    assert presentes >= COLONNES_TECHNIQUES, sorted(COLONNES_TECHNIQUES - presentes)


@pytest.mark.integration
def test_le_nombre_de_REQUETES_est_borne_par_les_AXES_jamais_par_les_periodes(
    cx: Connection,
) -> None:
    """Cinquieme critere de sortie du lot : « aucune requete N+1 critique ».

    **IL SE COMPTE, IL NE SE SUPPOSE PAS** (§7.0, troisieme proposition). Le decor
    porte NEUF periodes reparties sur cinq axes ; le compte attendu est de SIX
    requetes — une par axe, plus celle qui lit la personne — et il ne doit pas
    bouger quand le nombre de periodes change.
    """
    entite = _entite(cx, "T9-N1")
    cible = _profil_avec_un_parcours(cx, entite)

    with Compteur(cx) as compteur:
        historique = _tout_lire(cx, entite, cible)
    periodes = sum(
        len(axe or [])
        for axe in (
            historique.metier,
            historique.statut,
            historique.cercle,
            historique.dsm,
            historique.responsabilites,
        )
    )
    assert periodes >= 9, periodes
    assert len(compteur.requetes) == 6, (
        f"{len(compteur.requetes)} requetes pour {periodes} periodes, 6 attendues"
    )

    #  **LE TEMOIN QUI REND LE COMPTE NON TRIVIAL** : trois axes seulement, donc
    #  QUATRE requetes. Un service qui emettrait ses cinq requetes puis filtrerait
    #  rendrait six dans les deux cas.
    with Compteur(cx) as restreint:
        lire_l_historique(
            cx,
            entite=entite,
            cible=cible,
            acces=AccesAlHistorique(
                axes=frozenset({AxeHistorique.METIER, AxeHistorique.DSM, AxeHistorique.CERCLE})
            ),
            instant=ANCRAGE,
        )
    assert len(restreint.requetes) == 4, len(restreint.requetes)


@pytest.mark.integration
def test_une_cible_inexistante_rend_None(cx: Connection) -> None:
    """Le service ne suppose pas que la resolution d'acces l'a precede."""
    entite = _entite(cx, "T9-ABSENT")
    assert (
        lire_l_historique(
            cx,
            entite=entite,
            cible=uuid.uuid4(),
            acces=AccesAlHistorique(axes=frozenset(AxeHistorique)),
            instant=ANCRAGE,
        )
        is None
    )
