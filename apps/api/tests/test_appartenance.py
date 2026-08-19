"""`entity_membership` — la regle centrale de `US002`, eprouvee sur PostgreSQL reel.

LOT 2, sous-etape `T4`, story `MVP-L02-US002`.

DEUX CONTRAINTES SE PARTAGENT LA REGLE, ET CE FICHIER PROUVE QU'AUCUNE NE SUFFIT.

  - l'index unique PARTIEL du §25.1 interdit deux appartenances OCCUPANTES
    simultanees, mais laisserait passer deux appartenances `departed` qui se
    chevauchent ;
  - la contrainte d'exclusion du §25.2 interdit tout chevauchement temporel, mais
    laisserait passer deux appartenances occupantes a des periodes DISJOINTES.

Deux tests montrent chacun ce que l'autre contrainte ne verrait pas. Sans eux, on
pourrait croire l'une redondante et la retirer.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.configuration.settings import Parametres
from app.modeles import metadonnees
from app.people import (
    CATEGORIES_PROFESSIONNELLES,
    ETATS_APPARTENANCE,
    ETATS_OCCUPANTS,
    VISIBILITES_PROFIL,
    EntityMembership,
)
from app.shared.database import fabrique_de_sessions, moteur

# ============================================================================
#  1. Unitaires
# ============================================================================


def test_les_quatre_etats_du_modele() -> None:
    """§6.2 : quatre valeurs. Le diagramme §24.1 en montre cinq — voir `ECART-030`."""
    assert ETATS_APPARTENANCE == ("future", "active", "departed", "archived")
    assert "anonymized" not in ETATS_APPARTENANCE, (
        "le §24.1 montre un etat `Anonymized`, mais le §6.2 ne le declare pas : "
        "l'anonymisation porte sur la PERSONNE, pas sur son appartenance. ECART-030."
    )


def test_les_etats_occupants_sont_ceux_de_l_index_partiel() -> None:
    """§25.1 : `WHERE membership_state IN ('future','active')`."""
    assert ETATS_OCCUPANTS == ("future", "active")


def test_les_categories_et_visibilites_du_modele() -> None:
    assert CATEGORIES_PROFESSIONNELLES == ("consultant", "dg")
    assert VISIBILITES_PROFIL == ("draft", "published", "hidden")


def test_l_appartenance_ne_DUPLIQUE_NI_le_nom_NI_l_email() -> None:
    """§6.1 : « le nom et l'e-mail ne sont pas dupliques dans les tables d'appartenance ».

    C'est une regle d'ABSENCE : elle ne se declare pas, elle se verifie. Sans ce
    controle, ajouter un `first_name` « pour eviter une jointure » passerait
    inapercu, et l'identite se retrouverait a deux endroits qui divergeraient.
    """
    colonnes = set(metadonnees.tables["entity_membership"].columns.keys())
    interdites = {"first_name", "last_name", "email", "email_normalized", "preferred_name"}
    fautives = colonnes & interdites
    assert not fautives, (
        f"colonnes d'identite dupliquees dans entity_membership : {sorted(fautives)}. "
        "Le §6.1 l'interdit : elles vivent dans `person`."
    )


# ============================================================================
#  2. Integration
# ============================================================================

JANVIER = dt.date(2026, 1, 1)
JUIN = dt.date(2026, 6, 1)
MARS = dt.date(2026, 3, 1)
DECEMBRE = dt.date(2026, 12, 1)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
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


def _entite(connexion: Connection, code: str = "BORDEAUX", statut: str = "active") -> uuid.UUID:
    """Inserer une entite minimale.

    UN PARAMETRE PAR COLONNE, et ce n'est pas du zele. Reutiliser `:code` pour
    `code` -- un `varchar(64)` -- et pour `display_name` -- un `text` -- fait
    echouer PostgreSQL sur « inconsistent types deduced for parameter $1 » : il ne
    peut pas deduire un type unique. Defaut rencontre le 19/08/2026, et il faisait
    echouer dix-huit tests d'un coup pour une cause qui n'etait pas dans le modele.
    """
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', :statut, 'Europe/Paris', "
            "CASE WHEN :statut_bis = 'draft' THEN NULL ELSE now() END) RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code, "statut": statut, "statut_bis": statut},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str = "jean.dupont@exalt-company.com") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    etat: str = "active",
    arrivee: dt.date = JANVIER,
    depart: dt.date | None = None,
    categorie: str = "consultant",
    visibilite: str = "draft",
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, :categorie, :visibilite) RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "arrivee": arrivee,
            "depart": depart,
            "etat": etat,
            "categorie": categorie,
            "visibilite": visibilite,
        },
    ).scalar_one()


@pytest.mark.integration
def test_une_appartenance_minimale_se_cree(cx: Connection) -> None:
    _appartenance(cx, _personne(cx), _entite(cx))
    ligne = cx.execute(
        text(
            "SELECT membership_state, professional_category, profile_visibility, version, "
            "period::text, profile_published_at FROM entity_membership"
        )
    ).one()
    assert ligne.membership_state == "active"
    assert ligne.professional_category == "consultant"
    assert ligne.profile_visibility == "draft"
    assert ligne.version == 1
    assert ligne.period == "[2026-01-01,)", "plage non bornee quand le depart est inconnu"
    assert ligne.profile_published_at is None


@pytest.mark.integration
def test_la_plage_generee_est_semi_ouverte(cx: Connection) -> None:
    _appartenance(cx, _personne(cx), _entite(cx), depart=JUIN)
    plage = cx.execute(text("SELECT period::text FROM entity_membership")).scalar_one()
    assert plage == "[2026-01-01,2026-06-01)", (
        "convention posee en `T1` : la fin d'une periode et le debut de la suivante "
        "peuvent porter le meme jour sans se chevaucher"
    )


# ----------------------------------------------------------------------------
#  LA REGLE CENTRALE : une seule appartenance occupante par personne
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_UNE_SEULE_appartenance_occupante_par_personne(cx: Connection) -> None:
    """§25.1 et §2.2. Le coeur de `US002`."""
    personne = _personne(cx)
    _appartenance(cx, personne, _entite(cx, "BORDEAUX"), etat="active", depart=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _appartenance(
            cx, personne, _entite(cx, "LILLE"), etat="future", arrivee=JUIN, depart=DECEMBRE
        )
    assert "uq_entity_membership_person_id_occupante" in str(echec.value), (
        "le refus doit venir de l'index partiel du §25.1, et non de la contrainte "
        "d'exclusion : les deux periodes sont ici DISJOINTES"
    )


@pytest.mark.integration
def test_une_appartenance_HISTORIQUE_coexiste_avec_une_active(cx: Connection) -> None:
    """Temoin : le §2.2 exige « plusieurs appartenances historiques, une seule active »."""
    personne = _personne(cx)
    _appartenance(cx, personne, _entite(cx, "LILLE"), etat="departed", arrivee=JANVIER, depart=JUIN)
    _appartenance(cx, personne, _entite(cx, "BORDEAUX"), etat="active", arrivee=JUIN)
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 2


@pytest.mark.integration
def test_deux_personnes_peuvent_etre_occupantes_en_meme_temps(cx: Connection) -> None:
    """Temoin : l'index porte sur la PERSONNE, pas sur la table."""
    entite = _entite(cx)
    _appartenance(cx, _personne(cx, "a@exalt.com"), entite)
    _appartenance(cx, _personne(cx, "b@exalt.com"), entite)
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 2


# ----------------------------------------------------------------------------
#  Chevauchement temporel — et la preuve que les DEUX contraintes sont utiles
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_deux_appartenances_HISTORIQUES_qui_se_chevauchent_sont_refusees(cx: Connection) -> None:
    """Ce que l'index partiel NE verrait PAS.

    Les deux appartenances sont `departed`, donc hors du `WHERE` de l'index. Seule
    la contrainte d'exclusion les attrape. Ce test est ce qui prouve qu'elle n'est
    pas redondante.
    """
    personne = _personne(cx)
    _appartenance(cx, personne, _entite(cx, "LILLE"), etat="departed", arrivee=JANVIER, depart=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _appartenance(
            cx, personne, _entite(cx, "BORDEAUX"), etat="departed", arrivee=MARS, depart=DECEMBRE
        )
    assert "sans_chevauchement" in str(echec.value), (
        "le refus doit venir de la contrainte d'exclusion : les deux etats sont "
        "`departed`, donc hors du WHERE de l'index partiel"
    )


@pytest.mark.integration
def test_deux_appartenances_ADJACENTES_sont_acceptees(cx: Connection) -> None:
    """Temoin : une contrainte qui refuserait TOUTE succession passerait sans lui."""
    personne = _personne(cx)
    _appartenance(cx, personne, _entite(cx, "LILLE"), etat="departed", arrivee=JANVIER, depart=JUIN)
    _appartenance(
        cx, personne, _entite(cx, "BORDEAUX"), etat="departed", arrivee=JUIN, depart=DECEMBRE
    )
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 2


@pytest.mark.integration
def test_deux_personnes_peuvent_avoir_des_periodes_qui_se_chevauchent(cx: Connection) -> None:
    """Temoin : l'exclusion porte sur la PERSONNE."""
    _appartenance(
        cx,
        _personne(cx, "a@exalt.com"),
        _entite(cx, "BORDEAUX"),
        etat="departed",
        arrivee=JANVIER,
        depart=DECEMBRE,
    )
    _appartenance(
        cx,
        _personne(cx, "b@exalt.com"),
        _entite(cx, "LILLE"),
        etat="departed",
        arrivee=MARS,
        depart=JUIN,
    )
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 2


# ----------------------------------------------------------------------------
#  Dates et coherence d'etat
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_depart_avant_l_arrivee_est_refuse(cx: Connection) -> None:
    """§6.2 : `departure_date >= arrival_date`. Le refus arrive, mais PAS d'ou on croit.

    MESURE DU 19/08/2026, ET ELLE CORRIGE MON ATTENTE. J'attendais une violation
    de la contrainte `ck_entity_membership_depart_apres_arrivee`. PostgreSQL leve
    en realite une `DataException` : « range lower bound must be less than or
    equal to range upper bound ».

    POURQUOI. La colonne generee `period` est calculee AVANT que les contraintes de
    verification soient evaluees, et `daterange(juin, janvier)` est une valeur
    IMPOSSIBLE a construire. La contrainte n'est donc jamais atteinte : elle est
    OMBRAGEE par la colonne generee.

    ELLE EST NEANMOINS CONSERVEE, et pour deux raisons qui ne sont pas de la
    superstition : elle est ce que le §6.2 ecrit, et elle redeviendrait la seule
    barriere si la colonne generee etait un jour retiree ou rendue nullable. Une
    contrainte ombragee ne coute rien ; son absence couterait au premier
    changement.

    LE TEST PORTE DONC SUR LE MECANISME REEL, pas sur celui que j'esperais. Un
    test qui aurait exige le nom de la contrainte aurait echoue sur un livrable
    CONFORME -- c'est le §7.20 de la passation, et la bonne reaction est de faire
    dire le vrai au controle, pas de l'affaiblir.
    """
    with pytest.raises(DataError) as echec:
        _appartenance(cx, _personne(cx), _entite(cx), arrivee=JUIN, depart=JANVIER)
    assert "range lower bound must be less than or equal to range upper bound" in str(echec.value)


@pytest.mark.integration
def test_un_depart_le_MEME_jour_que_l_arrivee_est_accepte(cx: Connection) -> None:
    """Temoin : le §6.2 ecrit `departure_date >= arrival_date`, donc l'egalite passe."""
    _appartenance(cx, _personne(cx), _entite(cx), etat="departed", arrivee=JANVIER, depart=JANVIER)
    plage = cx.execute(text("SELECT period::text, isempty(period) FROM entity_membership")).one()
    assert plage[1] is True, (
        "une plage semi-ouverte de bornes egales est VIDE. Consequence a connaitre : "
        "une plage vide ne chevauche rien, donc l'exclusion ne la voit pas."
    )


@pytest.mark.integration
def test_l_etat_departed_exige_une_date_de_depart(cx: Connection) -> None:
    """DERIVEE du §24.1 : la transition y est libellee « depart ENREGISTRE »."""
    with pytest.raises(IntegrityError) as echec:
        _appartenance(cx, _personne(cx), _entite(cx), etat="departed", depart=None)
    assert "depart_date_si_departed" in str(echec.value)


@pytest.mark.integration
def test_l_etat_archived_n_exige_PAS_de_date_de_depart(cx: Connection) -> None:
    """Temoin : le §24.1 autorise `Future --> Archived`, « arrivee annulee ».

    Une arrivee annulee n'a jamais eu de depart. Exiger la date pour `archived`
    rendrait ce cas impossible.
    """
    _appartenance(cx, _personne(cx), _entite(cx), etat="archived", depart=None)
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 1


@pytest.mark.integration
def test_les_enumerations_refusent_une_valeur_hors_liste(cx: Connection) -> None:
    personne, entite = _personne(cx), _entite(cx)
    cas = (
        ({"etat": "parti"}, "membership_state_valide"),
        ({"categorie": "stagiaire"}, "professional_category_valide"),
        ({"visibilite": "public"}, "profile_visibility_valide"),
    )
    for argument, contrainte in cas:
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _appartenance(cx, personne, entite, **argument)  # type: ignore[arg-type]
        assert contrainte in str(echec.value), f"attendu {contrainte} pour {argument}"


@pytest.mark.integration
def test_toutes_les_valeurs_declarees_sont_acceptees(cx: Connection) -> None:
    """Temoin des trois enumerations : aucune ne refuse ce qu'elle declare."""
    entite = _entite(cx)
    total = 0
    for indice, etat in enumerate(ETATS_APPARTENANCE):
        _appartenance(
            cx,
            _personne(cx, f"etat{indice}@exalt.com"),
            entite,
            etat=etat,
            depart=JUIN if etat == "departed" else None,
        )
        total += 1
    for indice, categorie in enumerate(CATEGORIES_PROFESSIONNELLES):
        _appartenance(cx, _personne(cx, f"cat{indice}@exalt.com"), entite, categorie=categorie)
        total += 1
    for indice, visibilite in enumerate(VISIBILITES_PROFIL):
        _appartenance(cx, _personne(cx, f"vis{indice}@exalt.com"), entite, visibilite=visibilite)
        total += 1
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == total


# ----------------------------------------------------------------------------
#  Cles etrangeres, et la regle inter-tables heritee de `T2`
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_appartenance_exige_une_personne_ET_une_entite_existantes(cx: Connection) -> None:
    entite, personne = _entite(cx), _personne(cx)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _appartenance(cx, uuid.uuid4(), entite)
    assert "fk_entity_membership_person_id_person" in str(echec.value)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _appartenance(cx, personne, uuid.uuid4())
    assert "fk_entity_membership_entity_id_entity" in str(echec.value)


@pytest.mark.integration
def test_une_entite_ARCHIVEE_ne_recoit_plus_de_nouveaux_membres(cx: Connection) -> None:
    """§5.1, regle heritee de `T2`. INTER-TABLES, donc portee par declencheur."""
    entite = _entite(cx, "BORDEAUX", statut="archived")
    with pytest.raises(IntegrityError) as echec:
        _appartenance(cx, _personne(cx), entite)
    assert "une entite archivee ne recoit plus de nouveaux membres" in str(echec.value)


@pytest.mark.integration
def test_les_autres_statuts_d_entite_recoivent_des_membres(cx: Connection) -> None:
    """Temoin : le declencheur ne refuse pas toute insertion."""
    for indice, statut in enumerate(("draft", "active", "suspended")):
        _appartenance(
            cx, _personne(cx, f"s{indice}@exalt.com"), _entite(cx, f"ENTITE{indice}", statut)
        )
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 3


@pytest.mark.integration
def test_deplacer_une_appartenance_vers_une_entite_archivee_est_refuse(cx: Connection) -> None:
    """Second temoin : le declencheur couvre aussi la mise a jour de `entity_id`.

    Sans cela, la regle serait contournable en deux temps : creer l'appartenance
    dans une entite saine, puis la deplacer.
    """
    identifiant = _appartenance(cx, _personne(cx), _entite(cx, "BORDEAUX"))
    archivee = _entite(cx, "LILLE", statut="archived")
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text("UPDATE entity_membership SET entity_id = :e WHERE id = :i"),
            {"e": archivee, "i": identifiant},
        )
    assert "une entite archivee ne recoit plus de nouveaux membres" in str(echec.value)


@pytest.mark.integration
def test_le_couple_id_entity_id_est_unique(cx: Connection) -> None:
    """§25.3 : la cible des cles etrangeres composites de `T5` a `T8`.

    **LE NOM A CHANGE EN `T5`, ET LE MOTIF VAUT D'ETRE SU.** `T4` avait nomme
    cette contrainte `id_entite_unique`, explicitement. `T5` a voulu la meme sur
    `job_catalog` : « relation "id_entite_unique" already exists ».

    Une contrainte UNIQUE est implementee par un INDEX, et **les noms d'index sont
    uniques a l'echelle du SCHEMA**. Le `name=` explicite avait de plus ecrase la
    convention, qui prefixe deja par la table. La migration `0006` renomme donc la
    contrainte, et le nom attendu est desormais celui de la convention.
    """
    contraintes = set(
        cx.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'entity_membership'::regclass AND contype = 'u'"
            )
        )
        .scalars()
        .all()
    )
    assert "uq_entity_membership_id_entity_id" in contraintes, (
        "sans ce couple unique, les tables de `T5` a `T8` ne pourraient pas garantir "
        "par cle etrangere composite qu'elles referencent une appartenance de LEUR entite"
    )


# ----------------------------------------------------------------------------
#  §6.2 : « `version` | entier | Concurrence optimiste »
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_le_verrou_optimiste_refuse_une_mise_a_jour_perimee(
    parametres_de_la_stack: Parametres,
) -> None:
    """La seule table ou le modele demande explicitement le verrou optimiste.

    LE SEUL TEST DE CE FICHIER QUI PASSE PAR L'ORM, et c'est necessaire : le verrou
    optimiste EST un comportement de l'ORM. Il ajoute `WHERE version = <lu>` a
    chaque `UPDATE` et incremente la colonne ; si aucune ligne n'est touchee, c'est
    qu'un autre a ecrit entre-temps, et `StaleDataError` est levee au lieu
    d'ecraser silencieusement.

    LE SCENARIO EST CELUI D'UNE VRAIE CONCURRENCE : deux sessions lisent la meme
    appartenance, la premiere ecrit, la seconde ecrit ensuite sur une version qui
    n'existe plus.
    """
    _exiger_postgresql(parametres_de_la_stack)
    fabrique = fabrique_de_sessions(parametres_de_la_stack)

    #  Mise en place dans sa propre session, validee : les deux sessions
    #  concurrentes doivent voir la meme ligne.
    with fabrique() as preparation:
        entite = preparation.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
                "activated_at) VALUES ('VERROU', 'Verrou', 'Verrou', 'FR', 'active', "
                "'Europe/Paris', now()) RETURNING id"
            )
        ).scalar_one()
        personne = preparation.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES ('verrou@exalt.com', 'verrou@exalt.com', 'V', 'V', "
                "'active') RETURNING id"
            )
        ).scalar_one()
        appartenance = preparation.execute(
            text(
                "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                "membership_state, professional_category, profile_visibility) "
                "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
            ),
            {"p": personne, "e": entite},
        ).scalar_one()
        preparation.commit()

    try:
        with fabrique() as premiere, fabrique() as seconde:
            vue_par_la_premiere = premiere.get(EntityMembership, appartenance)
            vue_par_la_seconde = seconde.get(EntityMembership, appartenance)
            assert vue_par_la_premiere is not None
            assert vue_par_la_seconde is not None
            assert vue_par_la_premiere.version == vue_par_la_seconde.version == 1

            vue_par_la_premiere.short_bio = "ecrit par la premiere"
            premiere.commit()
            assert vue_par_la_premiere.version == 2, "le verrou incremente la version"

            vue_par_la_seconde.short_bio = "ecrit par la seconde"
            with pytest.raises(StaleDataError):
                seconde.commit()
    finally:
        #  Nettoyage explicite : cette mise en place a ete VALIDEE, donc aucune
        #  annulation de transaction ne l'emportera.
        with fabrique() as menage:
            menage.execute(text("DELETE FROM entity_membership WHERE id = :i"), {"i": appartenance})
            menage.execute(text("DELETE FROM person WHERE id = :i"), {"i": personne})
            menage.execute(text("DELETE FROM entity WHERE id = :i"), {"i": entite})
            menage.commit()
