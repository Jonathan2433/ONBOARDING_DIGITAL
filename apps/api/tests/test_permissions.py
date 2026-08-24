"""Les permissions de l'entite consultee — matrice §5.1, §23.1 et §23.3.

LOT 4, sous-etape `T8`, story `MVP-L04-US002`.

CE QUE CE FICHIER PROUVE QUE `make permissions-check` NE PEUT PAS PROUVER

  Le controle de stack exerce la route a travers Caddy, avec l'horloge REELLE. Il
  ne peut donc constater qu'une chose sur une periode close : « ce role
  n'accorde rien MAINTENANT ». Or cette observation a **deux** causes possibles,
  et elles sont indistinguables de l'exterieur :

    (a) la periode est consultee, et l'instant est hors d'elle -- le bon cas ;
    (b) ce type de role n'est jamais appareille, donc jamais accorde -- un bug.

  Ici l'instant est un ARGUMENT. Le test decisif est donc celui qui resout les
  permissions **a un instant SITUE DANS la periode close** et exige que le role
  APPARAISSE. Sans lui, l'absence prouverait la mauvaise chose.

  C'est le §7.0, quatrieme proposition : demander quelle valeur produirait
  l'echec. Et c'est la meme raison qui fait exister le temoin de `T11` du LOT 2.

ET TROIS TESTS N'EXERCENT PAS NOTRE CODE, MAIS LE SOCLE

  Le §5.1 aurait pu demander du code defensif. La base l'interdit deja, et le
  §7.32 dit quoi faire : ne pas ecrire la defense, exiger que l'interdiction
  demeure. Les trois derniers tests portent sur le NOM de la contrainte violee --
  si un lot ulterieur la relachait, celui qui le fait saurait qu'il doit relire
  `app/permissions/services.py`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.modeles import metadonnees
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.services import (
    CORRESPONDANCE_RESPONSABILITES,
    CORRESPONDANCE_ROLES_TECHNIQUES,
    RoleDeLaMatrice,
    entite_principale,
    resoudre_les_permissions,
)
from app.shared.database import moteur

# ============================================================================
#  1. Unitaires — les correspondances et l'ordre
# ============================================================================


def test_les_sept_codes_du_paragraphe_3_de_la_matrice() -> None:
    """§3 : dix types, dont sept qu'une session de personne peut porter.

    `ANON` est l'absence de session, `SERVICE` porte un jeton et non une session,
    `NEW` suppose une fiche d'arrivee ou un onboarding -- ni l'un ni l'autre
    n'existe dans le schema, ils appartiennent aux LOTS 7 et 8. Les deduire
    d'autre chose serait une invention, §6.5.
    """
    assert [membre.value for membre in RoleDeLaMatrice] == [
        "EMP",
        "DSM",
        "ESM",
        "BOOST",
        "OFFICE",
        "ADM-E",
        "SUPER",
    ]
    absents = {"ANON", "NEW", "SERVICE"}
    assert not absents & {membre.value for membre in RoleDeLaMatrice}


def test_la_correspondance_des_responsabilites_couvre_TOUTE_l_enumeration() -> None:
    """§7.27 : une liste declaree doit etre exigee de correspondre au reel.

    La correspondance est une INTERPRETATION -- ni la matrice ni le modele ne
    portent l'appariement des deux vocabulaires. Elle est donc declaree, et ce
    test la fait echouer au premier type de responsabilite ajoute sans
    appariement. C'est son objet, exactement comme `TABLES_DECLAREES` du LOT 2.
    """
    declares = {membre.value for membre in TypeResponsabilite}
    assert set(CORRESPONDANCE_RESPONSABILITES) == declares, (
        f"types non appareilles : {sorted(declares - set(CORRESPONDANCE_RESPONSABILITES))} ; "
        f"appariements orphelins : {sorted(set(CORRESPONDANCE_RESPONSABILITES) - declares)}"
    )


def test_la_correspondance_des_roles_techniques_couvre_TOUTE_l_enumeration() -> None:
    declares = {membre.value for membre in TypeRoleTechnique}
    assert set(CORRESPONDANCE_ROLES_TECHNIQUES) == declares


def test_les_deux_correspondances_sont_INJECTIVES_et_disjointes() -> None:
    """Deux types du modele qui rendraient le meme code de matrice les confondraient.

    Et un code present dans les deux correspondances serait accorde par deux
    chemins : la branche 2 du service l'ajouterait deux fois sans qu'on le voie,
    l'ensemble absorbant le doublon.
    """
    responsabilites = list(CORRESPONDANCE_RESPONSABILITES.values())
    techniques = list(CORRESPONDANCE_ROLES_TECHNIQUES.values())
    assert len(set(responsabilites)) == len(responsabilites)
    assert len(set(techniques)) == len(techniques)
    assert not set(responsabilites) & set(techniques)
    assert RoleDeLaMatrice.EMPLOYE not in set(responsabilites) | set(techniques), (
        "`EMP` n'est accorde par aucune table de role : il vient de l'appartenance."
    )


def test_l_entite_id_d_une_responsabilite_est_OBLIGATOIRE() -> None:
    """« Aucune permission locale n'est transferee » est structurel, pas defensif.

    Une responsabilite sans entite ne peut pas exister : c'est ce qui rend la
    regle 2 du §23.3 vraie par le schema, et non par une precaution de notre
    code. Si cette colonne devenait nullable, la branche 2 du service
    accorderait des droits sans portee.
    """
    colonne = metadonnees.tables["framework_responsibility_assignment"].c.entity_id
    assert not colonne.nullable


# ============================================================================
#  2. Integration
# ============================================================================

#  Les instants sont RELATIFS a un ancrage fixe, jamais a `now()`. Un test qui
#  lirait l'horloge changerait de sens le jour ou une borne le croiserait.
ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
JOUR = dt.timedelta(days=1)


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


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', "
            "now()) RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Sujet', 'L4T8', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    arrivee: dt.date | None = None,
    depart: dt.date | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "VALUES (:personne, :entite, :arrivee, :depart, 'active', 'consultant', 'draft')"
        ),
        {
            "personne": personne,
            "entite": entite,
            "arrivee": arrivee or (ANCRAGE - 30 * JOUR).date(),
            "depart": depart,
        },
    )


def _responsabilite(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_responsabilite: str,
    debut: dt.datetime,
    fin: dt.datetime | None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at, ends_at) "
            "VALUES (:personne, :entite, :type_resp, :attributeur, :debut, :fin)"
        ),
        {
            "personne": personne,
            "entite": entite,
            "type_resp": type_responsabilite,
            #  Le sujet est son propre attributeur : le decor est fictif et
            #  annule par le rollback, donc aucune trace d'audit reelle n'est
            #  fabriquee -- ce que `CLAUDE.md` §4.14 interdit.
            "attributeur": personne,
            "debut": debut,
            "fin": fin,
        },
    )


def _role_technique(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID | None,
    type_role: str,
    debut: dt.datetime,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, "
            "starts_at, ends_at) VALUES (:personne, :entite, :type_role, :debut, NULL)"
        ),
        {"personne": personne, "entite": entite, "type_role": type_role, "debut": debut},
    )


@pytest.mark.integration
def test_dans_l_entite_principale_les_droits_se_CUMULENT(cx: Connection) -> None:
    """§23.1 : « dans l'entite principale, les droits de plusieurs responsabilites se cumulent »."""
    a = _entite(cx, "T8-CUMUL-A")
    p = _personne(cx, "t8-cumul@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value, ANCRAGE - JOUR, None)
    _responsabilite(cx, p, a, TypeResponsabilite.DSM.value, ANCRAGE - JOUR, None)
    _role_technique(cx, p, a, TypeRoleTechnique.ENTITY_ADMIN.value, ANCRAGE - JOUR)

    resolues = resoudre_les_permissions(cx, p, a, ANCRAGE)

    assert resolues.est_entite_principale is True
    assert resolues.roles == (
        RoleDeLaMatrice.EMPLOYE,
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
    ), "l'ordre est celui du tableau §3 de la matrice, porte par l'enumeration"


@pytest.mark.integration
def test_hors_de_l_entite_principale_EMP_SEULEMENT(cx: Connection) -> None:
    """§5.1 : « elle possede uniquement les droits `EMP` ».

    LE DROIT DE L'AUTRE ENTITE EXISTE VRAIMENT, et c'est tout l'interet : sans
    lui, l'absence de `ADM-E` serait indistinguable d'une absence de donnee.
    """
    a = _entite(cx, "T8-HORS-A")
    b = _entite(cx, "T8-HORS-B")
    p = _personne(cx, "t8-hors@exalt-company.com")
    _appartenance(cx, p, a)
    _role_technique(cx, p, b, TypeRoleTechnique.ENTITY_ADMIN.value, ANCRAGE - JOUR)

    #  TEMOIN : dans A, le meme role accorderait bien `ADM-E`.
    _role_technique(cx, p, a, TypeRoleTechnique.ENTITY_ADMIN.value, ANCRAGE - JOUR)
    assert (
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE in resoudre_les_permissions(cx, p, a, ANCRAGE).roles
    )

    dans_b = resoudre_les_permissions(cx, p, b, ANCRAGE)

    assert dans_b.est_entite_principale is False
    assert dans_b.roles == (RoleDeLaMatrice.EMPLOYE,), (
        "une permission locale a ete TRANSFEREE : le §5.1 l'interdit, et le role "
        "de B est bien present en base"
    )


@pytest.mark.integration
def test_un_role_CLOTURE_n_accorde_rien_APRES_sa_fin(cx: Connection) -> None:
    """Controle §24.12 du cahier : « un role cloture ne continue pas a accorder »."""
    a = _entite(cx, "T8-CLOS-A")
    p = _personne(cx, "t8-clos@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value, ANCRAGE - 10 * JOUR, ANCRAGE - 5 * JOUR)

    assert resoudre_les_permissions(cx, p, a, ANCRAGE).roles == (RoleDeLaMatrice.EMPLOYE,)


@pytest.mark.integration
def test_LE_MEME_role_cloture_accorde_bien_DANS_sa_periode(cx: Connection) -> None:
    """LE TEMOIN DECISIF, ET IL N'EXISTE QUE PARCE QUE L'INSTANT EST UN ARGUMENT.

    Le test precedent constate une ABSENCE. Deux causes la produisent : la periode
    est consultee et l'instant est dehors -- le bon cas -- ou bien `ESM` n'est
    jamais appareille, donc jamais accorde. Les deux donnent exactement la meme
    observation.

    Celui-ci resout au MEME decor, a un instant SITUE DANS la periode close, et
    exige que le role APPARAISSE. C'est la seule facon de distinguer les deux.
    """
    a = _entite(cx, "T8-DEDANS-A")
    p = _personne(cx, "t8-dedans@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value, ANCRAGE - 10 * JOUR, ANCRAGE - 5 * JOUR)

    dedans = resoudre_les_permissions(cx, p, a, ANCRAGE - 7 * JOUR)

    assert RoleDeLaMatrice.ESM in dedans.roles, (
        "le role n'est accorde a AUCUN instant : l'absence du test precedent ne "
        "prouvait donc pas que la periode est consultee"
    )


@pytest.mark.integration
def test_une_affectation_FUTURE_n_accorde_rien_et_ends_at_nul_ne_suffirait_pas(
    cx: Connection,
) -> None:
    """`ends_at IS NULL` est vrai d'une affectation future : la plage seule tranche.

    Le meme decor, deux instants : avant le debut, rien ; apres, le role. Un
    service qui filtrerait sur `ends_at IS NULL` passerait le second test et
    echouerait au premier — ce qui est exactement ce que la mesure du 24/08/2026
    a montre quand le defaut a ete injecte pour de vrai.
    """
    a = _entite(cx, "T8-FUTUR-A")
    p = _personne(cx, "t8-futur@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.DSM.value, ANCRAGE + 10 * JOUR, None)

    assert resoudre_les_permissions(cx, p, a, ANCRAGE).roles == (RoleDeLaMatrice.EMPLOYE,)
    assert RoleDeLaMatrice.DSM in resoudre_les_permissions(cx, p, a, ANCRAGE + 11 * JOUR).roles


@pytest.mark.integration
def test_le_super_administrateur_s_applique_PARTOUT(cx: Connection) -> None:
    """§5.1 : « le super-administrateur constitue la seule exception globale »."""
    a = _entite(cx, "T8-SUPER-A")
    b = _entite(cx, "T8-SUPER-B")
    p = _personne(cx, "t8-super@exalt-company.com")
    _appartenance(cx, p, a)
    _role_technique(cx, p, None, TypeRoleTechnique.SUPER_ADMIN.value, ANCRAGE - JOUR)

    chez_lui = resoudre_les_permissions(cx, p, a, ANCRAGE)
    ailleurs = resoudre_les_permissions(cx, p, b, ANCRAGE)

    assert RoleDeLaMatrice.SUPER_ADMINISTRATEUR in chez_lui.roles
    assert RoleDeLaMatrice.SUPER_ADMINISTRATEUR in ailleurs.roles
    assert ailleurs.est_entite_principale is False


@pytest.mark.integration
def test_sans_appartenance_occupante_l_ensemble_est_VIDE(cx: Connection) -> None:
    """`EMP` vient de l'appartenance, et le §3 la nomme : « collaborateur ACTIF ».

    Ce n'est pas un cas d'erreur : le §7.32 interdit d'inventer une defense
    contre un etat que rien n'interdit. Une personne archivee est dans cet etat.
    """
    a = _entite(cx, "T8-VIDE-A")
    p = _personne(cx, "t8-vide@exalt-company.com")

    resolues = resoudre_les_permissions(cx, p, a, ANCRAGE)

    assert entite_principale(cx, p) is None
    assert resolues.roles == ()
    assert resolues.est_entite_principale is False


# ============================================================================
#  3. Le socle doit CONTINUER d'interdire — §7.32
# ============================================================================


@pytest.mark.integration
def test_la_base_interdit_TOUJOURS_un_super_admin_rattache_a_une_entite(cx: Connection) -> None:
    """`ck_technical_role_assignment_portee_selon_le_role`.

    C'est cette contrainte qui fait de « la seule exception globale » un fait de
    schema. Si elle etait relachee, `SUPER` pourrait etre local, et la branche 1
    du service — qui exige `entity_id IS NULL` — cesserait de le voir.
    """
    a = _entite(cx, "T8-SOCLE-A")
    p = _personne(cx, "t8-socle@exalt-company.com")

    with pytest.raises(IntegrityError) as leve:
        _role_technique(cx, p, a, TypeRoleTechnique.SUPER_ADMIN.value, ANCRAGE - JOUR)

    assert "ck_technical_role_assignment_portee_selon_le_role" in str(leve.value)


@pytest.mark.integration
def test_la_base_interdit_TOUJOURS_deux_appartenances_occupantes(cx: Connection) -> None:
    """`uq_entity_membership_person_id_occupante`.

    C'est elle qui rend l'entite principale UNIQUE par construction. Si elle
    etait relachee, `entite_principale` leverait sur `scalar_one_or_none` et la
    route rendrait 500 — donc celui qui la relache doit relire ce module.

    **LES PERIODES SONT DISJOINTES, ET C'EST LE POINT.** La premiere version de
    ce test donnait la meme date d'arrivee aux deux appartenances : c'est
    `ex_entity_membership_sans_chevauchement` qui se declenchait, et l'index
    unique n'etait jamais atteint — donc le test ne prouvait rien de LUI.
    C'est le §7.25, seconde lecon : « un temoin qui n'exerce pas un controle ne
    prouve rien de ce controle ». `test_appartenance.py` du LOT 2 le dit
    d'ailleurs en tete : deux contraintes se partagent la regle, et chacune
    attrape ce que l'autre laisserait passer.
    """
    a = _entite(cx, "T8-DEUX-A")
    b = _entite(cx, "T8-DEUX-B")
    p = _personne(cx, "t8-deux@exalt-company.com")
    _appartenance(cx, p, a, arrivee=dt.date(2026, 1, 1), depart=dt.date(2026, 3, 1))

    with pytest.raises(IntegrityError) as leve:
        _appartenance(cx, p, b, arrivee=dt.date(2026, 6, 1))

    assert "uq_entity_membership_person_id_occupante" in str(leve.value), (
        f"contrainte attendue absente du message : {leve.value}"
    )
