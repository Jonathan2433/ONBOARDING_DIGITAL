"""Socle declaratif du modele : convention de nommage, champs communs, periodes.

LOT 2, sous-etape `T1`, story `MVP-L02-US008`.

CE QUE CES TESTS PROUVENT, ET POURQUOI ILS EXISTENT AVANT LA PREMIERE TABLE.
`T1` ne cree aucune table metier. Elle pose les briques dont les onze
sous-etapes suivantes se serviront : si une de ces briques est fausse, l'erreur
se retrouvera dans seize tables au lieu d'une. Les eprouver maintenant coute une
sous-etape ; les eprouver en `T12` couterait le lot.

UNE TABLE D'ESSAI, ET SA PROPRE `MetaData`. Les tests d'integration construisent
une table jetable a partir des mixins reels, mais dans une `MetaData` DISTINCTE
de celle de production. Sinon la table d'essai resterait declaree dans
`app.shared.modele.metadonnees`, et `alembic check` la reclamerait a chaque
execution -- un test qui casse le controle qu'il est cense servir.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.configuration.settings import Parametres
from app.shared.database import moteur
from app.shared.modele import (
    CONVENTION_DE_NOMMAGE,
    LIMITE_IDENTIFIANT_POSTGRESQL,
    ChampsCommuns,
    Periode,
    RessourceLocale,
    contrainte_enumeration,
    metadonnees,
    nom_exclusion,
    noms_de_contraintes_trop_longs,
    noms_exclusions_non_conformes,
)

# ============================================================================
#  1. Convention de nommage — tests unitaires, aucune base requise
# ============================================================================


def _table_temoin() -> tuple[MetaData, Table]:
    """Une table jetable portant un exemplaire de chaque type de contrainte."""
    essai = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)
    Table("parent", essai, Column("id", Integer, primary_key=True))
    table = Table(
        "enfant",
        essai,
        Column("id", Integer, primary_key=True),
        Column("code", String(10), nullable=False),
        Column("parent_id", Integer, ForeignKey("parent.id"), nullable=False),
        Column("quantite", Integer, nullable=False),
        UniqueConstraint("code"),
        CheckConstraint("quantite > 0", name="quantite_positive"),
        Index(None, "code", "quantite"),
    )
    return essai, table


def test_la_convention_produit_les_noms_attendus() -> None:
    """Chaque famille de contrainte recoit un nom deterministe et lisible."""
    _, table = _table_temoin()
    noms = {c.name for c in table.constraints} | {i.name for i in table.indexes}

    assert "pk_enfant" in noms
    assert "uq_enfant_code" in noms
    assert "ck_enfant_quantite_positive" in noms
    assert "fk_enfant_parent_id_parent" in noms
    assert "ix_enfant_code_quantite" in noms


def test_une_contrainte_de_verification_anonyme_est_refusee() -> None:
    """Une `CheckConstraint` sans `name` ne peut pas produire de DDL.

    Ce n'est pas une gene, c'est le garde-fou : la convention emploie
    `%(constraint_name)s`, donc une contrainte anonyme n'a pas de nom a
    interpoler. Une contrainte sans nom est une contrainte qu'un `downgrade()`
    ne peut pas supprimer.
    """
    essai = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)

    # Le refus arrive des la CONSTRUCTION de la table, et non a la compilation du
    # DDL : SQLAlchemy resout le nom au moment ou la contrainte est rattachee.
    # C'est mieux ainsi -- l'erreur tombe a l'import du module, donc a la
    # collecte des tests, et non au moment d'appliquer une migration.
    with pytest.raises(InvalidRequestError, match=r"explicitly named"):
        Table(
            "anonyme",
            essai,
            Column("id", Integer, primary_key=True),
            Column("quantite", Integer, nullable=False),
            CheckConstraint("quantite > 0"),  # volontairement sans name=
        )


# ============================================================================
#  2. Limite de 63 octets — et son temoin, sans lequel le test serait creux
# ============================================================================


def test_aucun_nom_de_contrainte_du_modele_ne_depasse_la_limite() -> None:
    """Les metadonnees de production ne portent aucun nom tronquable.

    ATTENTION : a la sortie de `T1` ce modele ne declare AUCUNE table, donc ce
    test passerait meme si la fonction etait cassee. C'est le test suivant qui
    lui donne sa valeur.
    """
    assert noms_de_contraintes_trop_longs() == []


def test_le_controle_de_longueur_DETECTE_un_nom_trop_long() -> None:
    """Temoin : la fonction sait echouer.

    Sans ce temoin, le test precedent ne prouverait rien tant que le modele est
    vide -- exactement le defaut `T5-6` du LOT 1, ou un controle annoncait « 7
    modules sur 7 » sans discriminer.
    """
    essai = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)
    nom_tres_long = "x" * (LIMITE_IDENTIFIANT_POSTGRESQL + 1)
    Table(
        "trop_long",
        essai,
        Column("id", Integer, primary_key=True),
        Column("quantite", Integer, nullable=False),
        CheckConstraint("quantite > 0", name=nom_tres_long),
    )
    trouves = noms_de_contraintes_trop_longs(essai)
    assert trouves, "le controle n'a rien detecte alors qu'un nom depasse la limite"
    assert all(longueur > LIMITE_IDENTIFIANT_POSTGRESQL for _, longueur in trouves)


# ============================================================================
#  3. Enumerations bornees par contrainte de verification
# ============================================================================


class SituationProfessionnelle(enum.StrEnum):
    """Les deux valeurs du modele §6.5. `ECART-012` porte sur une troisieme."""

    MISSION = "mission"
    INTERCONTRAT = "intercontrat"


def test_contrainte_enumeration_borne_aux_valeurs_declarees() -> None:
    contrainte = contrainte_enumeration("status", SituationProfessionnelle, "status_valide")
    expression = str(contrainte.sqltext)
    assert "'mission'" in expression
    assert "'intercontrat'" in expression
    assert contrainte.name == "status_valide"


def test_contrainte_enumeration_accepte_le_cas_nullable() -> None:
    contrainte = contrainte_enumeration(
        "status", SituationProfessionnelle, "status_valide", nullable=True
    )
    assert "IS NULL" in str(contrainte.sqltext)


def test_contrainte_enumeration_refuse_une_valeur_malformee() -> None:
    """Une valeur portant une apostrophe produirait du SQL malforme."""

    class Douteuse(enum.StrEnum):
        MAUVAISE = "n'importe quoi"

    with pytest.raises(ValueError, match="valeur enumeree refusee"):
        contrainte_enumeration("colonne", Douteuse, "peu_importe")


def test_contrainte_enumeration_refuse_une_enumeration_vide() -> None:
    class Vide(enum.StrEnum):
        pass

    with pytest.raises(ValueError, match="enumeration vide"):
        contrainte_enumeration("colonne", Vide, "peu_importe")


# ============================================================================
#  4. Integration : PostgreSQL REEL. Jamais SQLite — critere de sortie du lot.
# ============================================================================


class BaseDEssai(DeclarativeBase):
    """Base declarative jetable, isolee de celle de production."""

    metadata = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)


class AffectationDEssai(ChampsCommuns, RessourceLocale, Periode, BaseDEssai):
    """Table d'essai batie sur les mixins REELS du socle.

    Elle porte les trois familles que `T9` et `T10` devront combiner : les champs
    communs du §3.1, le rattachement a une entite, et une periode historisee avec
    sa contrainte d'exclusion.
    """

    __tablename__ = "essai_affectation"

    sujet_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        ExcludeConstraint(
            ("sujet_id", "="),
            ("period", "&&"),
            #  Prefixe par la table : c'est la collision de ce nom avec celui de
            #  `entity_membership`, en `T4`, qui a fait naitre la regle.
            name=nom_exclusion("essai_affectation", "sans_chevauchement"),
            using="gist",
        ),
        contrainte_enumeration("status", SituationProfessionnelle, "status_valide"),
    )


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def connexion(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion dans une transaction TOUJOURS annulee.

    La table d'essai est creee puis detruite a l'interieur de cette transaction :
    rien ne subsiste dans `onboarding_dev`, meme si un test echoue.
    """
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as cx:
        transaction = cx.begin()
        try:
            BaseDEssai.metadata.create_all(cx)
            yield cx
        finally:
            transaction.rollback()


HORODATAGES = {
    "janvier": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    "juin": dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
    "mars": dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
    "decembre": dt.datetime(2026, 12, 1, tzinfo=dt.UTC),
}

pytestmark_integration = pytest.mark.integration


def _inserer(
    cx: Connection,
    sujet: uuid.UUID,
    debut: dt.datetime,
    fin: dt.datetime | None,
    status: str = "mission",
) -> None:
    cx.execute(
        text(
            "INSERT INTO essai_affectation (entity_id, sujet_id, starts_at, ends_at, status) "
            "VALUES (:entite, :sujet, :debut, :fin, :status)"
        ),
        {"entite": uuid.uuid4(), "sujet": sujet, "debut": debut, "fin": fin, "status": status},
    )


@pytest.mark.integration
def test_la_base_est_en_collation_francaise(parametres_de_la_stack: Parametres) -> None:
    """`QO-111` : la base sert bien ICU `fr-FR`, et le tri en decoule.

    DEUX TEMOINS, parce qu'un seul ne discriminerait pas. Le premier verifie que
    l'ordre par defaut EGALE l'ordre francais ; le second qu'il DIFFERE de
    l'ancien ordre `en_US.utf8`. Sans le second, le test passerait aussi sur une
    base restee en libc, puisque les deux collations trient a l'identique des
    prenoms simplement accentues -- mesure du 18/08/2026.
    """
    _exiger_postgresql(parametres_de_la_stack)
    noms = [
        "Jean-Pierre",
        "Jean Pierre",
        "Jeanne",
        "jean-paul",
        "Jeanpierre",
        "Le Gall",
        "Legall",
    ]

    with moteur(parametres_de_la_stack).connect() as cx:
        provider, locale = cx.execute(
            text(
                "SELECT datlocprovider::text, COALESCE(datlocale,'') "
                "FROM pg_database WHERE datname = current_database()"
            )
        ).one()
        assert provider == "i", f"fournisseur de collation attendu ICU, obtenu {provider!r}"
        assert locale == "fr-FR", f"locale attendue fr-FR, obtenue {locale!r}"

        # `unnest` avec un parametre LIE, et non une liste de valeurs interpolee
        # dans la requete. Le contenu vient d'ici et serait inoffensif, mais une
        # requete assemblee par concatenation est une habitude qui finit par
        # voyager vers du code qui, lui, recoit des entrees exterieures. Seule la
        # collation reste interpolee : ce n'est pas une valeur mais un
        # IDENTIFIANT, et PostgreSQL n'accepte pas de parametre a cette place.
        def ordonne(collation: str | None) -> list[str]:
            clause = "ORDER BY n" if collation is None else f'ORDER BY n COLLATE "{collation}"'
            # S608 : seule la collation est interpolee, et c'est un identifiant
            # choisi dans ce fichier, non une donnee. Voir le commentaire ci-dessus.
            requete = text(
                f"SELECT n FROM unnest(CAST(:noms AS text[])) AS t(n) {clause}"  # noqa: S608
            )
            return list(cx.execute(requete, {"noms": noms}).scalars().all())

        defaut = ordonne(None)
        francais = ordonne("fr-FR-x-icu")
        anglais = ordonne("en_US.utf8")

    assert defaut == francais, "l'ordre par defaut n'est pas l'ordre francais"
    assert defaut != anglais, (
        "l'ordre par defaut est identique a l'ordre en_US : le test ne discrimine pas, "
        "et la collation n'a probablement pas ete appliquee"
    )
    assert defaut.index("Jean-Pierre") < defaut.index("Jeanne"), (
        "un annuaire francais classe « Jean-Pierre » avant « Jeanne »"
    )


@pytest.mark.integration
def test_btree_gist_est_installee(parametres_de_la_stack: Parametres) -> None:
    """`QO-112` : l'unique extension du lot est bien la, et elle seule."""
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as cx:
        installees = set(
            cx.execute(text("SELECT extname FROM pg_extension WHERE extname <> 'plpgsql'"))
            .scalars()
            .all()
        )
    assert installees == {"btree_gist"}, (
        f"extensions installees inattendues : {sorted(installees)}. "
        "Une extension posee sans besoin nomme est de la surface d'attaque."
    )


@pytest.mark.integration
def test_la_periode_generee_est_semi_ouverte(connexion: Connection) -> None:
    """La colonne generee derive des bornes, et la borne haute est EXCLUE."""
    sujet = uuid.uuid4()
    _inserer(connexion, sujet, HORODATAGES["janvier"], HORODATAGES["juin"])
    plage = connexion.execute(text("SELECT period::text FROM essai_affectation")).scalar_one()
    assert plage.startswith("["), f"borne basse attendue incluse, obtenu {plage}"
    assert plage.endswith(")"), f"borne haute attendue exclue, obtenu {plage}"


@pytest.mark.integration
def test_une_periode_sans_fin_est_non_bornee(connexion: Connection) -> None:
    """`ends_at` a NULL represente une relation TOUJOURS active."""
    _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], None)
    plage = connexion.execute(text("SELECT period::text FROM essai_affectation")).scalar_one()
    assert plage.endswith(",)"), f"plage non bornee attendue, obtenu {plage}"


@pytest.mark.integration
def test_le_chevauchement_est_REFUSE_par_la_base(connexion: Connection) -> None:
    """Le coeur de l'arbitrage du 18/08/2026 : la BASE refuse, pas seulement le service."""
    sujet = uuid.uuid4()
    _inserer(connexion, sujet, HORODATAGES["janvier"], HORODATAGES["juin"])
    with pytest.raises(IntegrityError) as echec:
        _inserer(connexion, sujet, HORODATAGES["mars"], HORODATAGES["decembre"])
    assert "sans_chevauchement" in str(echec.value), (
        "le refus doit venir de la contrainte d'exclusion nommee, "
        "pas d'une autre contrainte qui aurait produit le meme echec"
    )


@pytest.mark.integration
def test_deux_periodes_ADJACENTES_sont_acceptees(connexion: Connection) -> None:
    """Temoin du precedent : sans lui, une contrainte qui refuse TOUT passerait.

    La fin d'une periode et le debut de la suivante portent le meme instant. Une
    plage fermee des deux cotes les declarerait en chevauchement ; la plage
    semi-ouverte les accepte, et c'est ce qu'une succession historique demande.
    """
    sujet = uuid.uuid4()
    _inserer(connexion, sujet, HORODATAGES["janvier"], HORODATAGES["juin"])
    _inserer(connexion, sujet, HORODATAGES["juin"], HORODATAGES["decembre"])
    total = connexion.execute(text("SELECT count(*) FROM essai_affectation")).scalar_one()
    assert total == 2, f"deux periodes adjacentes attendues, {total} en base"


@pytest.mark.integration
def test_deux_sujets_differents_peuvent_se_chevaucher(connexion: Connection) -> None:
    """Second temoin : la contrainte porte bien sur le SUJET, pas sur la table."""
    _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], HORODATAGES["juin"])
    _inserer(connexion, uuid.uuid4(), HORODATAGES["mars"], HORODATAGES["decembre"])
    total = connexion.execute(text("SELECT count(*) FROM essai_affectation")).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_la_contrainte_enumeree_refuse_une_valeur_hors_liste(connexion: Connection) -> None:
    with pytest.raises(IntegrityError) as echec:
        _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], None, status="direction_generale")
    assert "status_valide" in str(echec.value)


@pytest.mark.integration
def test_la_contrainte_enumeree_accepte_les_valeurs_declarees(connexion: Connection) -> None:
    """Temoin : la contrainte ne refuse pas tout."""
    for status in SituationProfessionnelle:
        _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], None, status=status.value)
    total = connexion.execute(text("SELECT count(*) FROM essai_affectation")).scalar_one()
    assert total == len(list(SituationProfessionnelle))


@pytest.mark.integration
def test_l_identifiant_est_engendre_par_le_SERVEUR(connexion: Connection) -> None:
    """`gen_random_uuid()` couvre les ecritures qui ne passent pas par l'ORM.

    L'insertion ci-dessus ne fournit AUCUN `id` : si le defaut serveur manquait,
    l'insertion echouerait sur une cle primaire nulle. Le test prouve donc le
    defaut serveur et non le defaut Python.
    """
    _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], None)
    identifiant = connexion.execute(text("SELECT id FROM essai_affectation")).scalar_one()
    assert isinstance(identifiant, uuid.UUID)


@pytest.mark.integration
def test_les_horodatages_communs_sont_renseignes_par_le_serveur(connexion: Connection) -> None:
    """`created_at` et `updated_at` ne sont pas fournis par l'insertion."""
    _inserer(connexion, uuid.uuid4(), HORODATAGES["janvier"], None)
    cree, modifie, version = connexion.execute(
        text("SELECT created_at, updated_at, version FROM essai_affectation")
    ).one()
    assert cree is not None
    assert modifie is not None
    assert version == 1, "le §3.1 pose `version integer not null default 1`"


#  LISTE ECRITE EN DUR, ET C'EST DELIBERE. Ne la remplace pas par une derivation
#  des metadonnees : le test comparerait alors les metadonnees a elles-memes et ne
#  prouverait plus rien. Son objet est d'exiger qu'une table NOUVELLE soit
#  inscrite ici, donc DECIDEE. Chaque sous-etape qui ajoute une table met cette
#  liste a jour dans la meme pull request que sa migration.
TABLES_DECLAREES = {
    # LOT 2, T2 — modele §5.1 a §5.4
    "entity",
    "platform_setting",
    "entity_setting",
    "allowed_email_domain",
    # LOT 2, T3 — modele §6.1
    "person",
    # LOT 2, T4 — modele §6.2
    "entity_membership",
    # LOT 2, T5 — modele §6.3 a §6.5
    "job_catalog",
    "membership_job_assignment",
    "professional_status_assignment",
}


def test_aucune_contrainte_d_exclusion_n_est_mal_nommee() -> None:
    """Les noms d'index etant uniques a l'echelle du SCHEMA, le prefixe est obligatoire.

    Le §25.2 prevoit des exclusions sur SEPT relations. Sans ce controle, la
    collision qui a fait naitre la regle en `T4` se reproduirait six fois, et
    chaque fois a la CREATION de la table -- donc dans une migration.
    """
    assert noms_exclusions_non_conformes() == []


def test_le_controle_de_nommage_des_exclusions_DETECTE_un_nom_nu() -> None:
    """Temoin : sans lui, le test precedent passerait meme si la regle etait cassee."""
    essai = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)
    Table(
        "essai_nu",
        essai,
        Column("id", Integer, primary_key=True),
        Column("sujet", Integer, nullable=False),
        Column("periode", TSTZRANGE, nullable=False),
        ExcludeConstraint(("sujet", "="), ("periode", "&&"), name="nom_nu", using="gist"),
    )
    fautives = noms_exclusions_non_conformes(essai)
    assert fautives == [("essai_nu", "nom_nu")]


def test_le_modele_declare_exactement_les_tables_attendues() -> None:
    """Garde-fou de perimetre : ces tables, et AUCUNE autre.

    Ce test echouera a chaque sous-etape qui ajoute une table, et c'est sa
    fonction. Une table qui apparaitrait sans que ce test soit mis a jour serait
    une table creee sans decision.
    """
    assert set(metadonnees.tables) == TABLES_DECLAREES, (
        f"tables declarees : {sorted(metadonnees.tables)}. "
        "Toute table nouvelle doit etre ajoutee a TABLES_DECLAREES ET a une migration."
    )
