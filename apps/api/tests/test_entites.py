"""Les quatre tables du modele §5, eprouvees sur PostgreSQL reel.

LOT 2, sous-etape `T2`, story `MVP-L02-US001`.

TOUTES LES ECRITURES PASSENT PAR DU SQL, PAS PAR L'ORM. Ce qui est eprouve ici,
ce sont les contraintes de la BASE : un test qui passerait par l'ORM prouverait
que l'ORM refuse, pas que la base refuse. Or `T11` ecrira des services, `T12` des
factories, et le LOT 9 un import CSV : autant de chemins d'ecriture qui ne
passeront pas tous par les memes objets Python.

CHAQUE REFUS A SON TEMOIN. Une contrainte qui refuserait TOUT donnerait la meme
observation qu'une contrainte juste, sur le seul test du refus.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.entities import STATUTS_ENTITE, StatutEntite
from app.modeles import metadonnees
from app.shared.database import moteur
from app.shared.modele import noms_de_contraintes_trop_longs

# ============================================================================
#  1. Unitaires — aucune base requise
# ============================================================================


def test_le_statut_porte_les_quatre_valeurs_du_modele() -> None:
    """§5.1 : `draft`, `active`, `suspended`, `archived`."""
    assert STATUTS_ENTITE == ("draft", "active", "suspended", "archived")
    assert [m.value for m in StatutEntite] == list(STATUTS_ENTITE)


def test_tous_les_modules_de_modeles_sont_importes() -> None:
    """`app/modeles.py` doit importer TOUS les modules de modeles du disque.

    Un module oublie ici serait invisible de `target_metadata`, et
    `alembic revision --autogenerate` proposerait de SUPPRIMER ses tables. Le
    controle compare le disque a ce que le point d'entree importe.
    """
    import pathlib

    from app import modeles as point_entree

    racine = pathlib.Path(point_entree.__file__).parent
    sur_le_disque = {
        chemin.parent.name
        for chemin in racine.rglob("modeles.py")
        if chemin.parent != racine and "__pycache__" not in chemin.parts
    }
    importes = {module.__name__.split(".")[-2] for module in point_entree.MODULES_DE_MODELES}
    assert sur_le_disque == importes, (
        f"modules de modeles sur le disque : {sorted(sur_le_disque)} ; "
        f"importes par app/modeles.py : {sorted(importes)}. "
        "Un module absent rendrait ses tables invisibles d'autogenerate."
    )


def test_aucun_nom_de_contrainte_ne_depasse_la_limite_postgresql() -> None:
    """Desormais NON creux : le modele declare quatre tables.

    A la sortie de `T1` ce test passait sur des metadonnees vides. Il porte
    maintenant sur des contraintes reelles.
    """
    assert metadonnees.tables, "les metadonnees sont vides : le test serait creux"
    assert noms_de_contraintes_trop_longs(metadonnees) == []


# ============================================================================
#  2. Integration — PostgreSQL REEL
# ============================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion dans une transaction TOUJOURS annulee.

    Les tables existent par migration : ce test ne les cree pas. Tout ce qu'il
    ecrit disparait a l'annulation, meme s'il echoue.
    """
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _creer_entite(
    connexion: Connection,
    code: str = "BORDEAUX",
    *,
    status: str = "draft",
    activee: bool = False,
) -> uuid.UUID:
    """Inserer une entite minimale et rendre son identifiant."""
    resultat = connexion.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', :status, 'Europe/Paris', "
            "CASE WHEN :activee THEN now() ELSE NULL END) RETURNING id"
        ),
        {
            "code": code,
            "nom": f"eXalt {code.title()}",
            "ville": code.title(),
            "status": status,
            "activee": activee,
        },
    )
    return resultat.scalar_one()  # type: ignore[no-any-return]


pytestmark_note = "chaque test d'integration porte son marqueur"


@pytest.mark.integration
def test_une_entite_minimale_se_cree(cx: Connection) -> None:
    """Le serveur renseigne l'identifiant, les horodatages et la version."""
    identifiant = _creer_entite(cx)
    ligne = cx.execute(
        text(
            "SELECT code, status, version, created_at, activated_at, archived_at "
            "FROM entity WHERE id = :id"
        ),
        {"id": identifiant},
    ).one()
    assert ligne.code == "BORDEAUX"
    assert ligne.status == "draft"
    assert ligne.version == 1
    assert ligne.created_at is not None
    assert ligne.activated_at is None
    assert ligne.archived_at is None


@pytest.mark.integration
def test_le_code_d_entite_est_unique(cx: Connection) -> None:
    _creer_entite(cx, "BORDEAUX")
    with pytest.raises(IntegrityError) as echec:
        _creer_entite(cx, "BORDEAUX")
    assert "code_unique" in str(echec.value)


@pytest.mark.integration
def test_deux_codes_differents_sont_acceptes(cx: Connection) -> None:
    """Temoin du precedent : la contrainte ne refuse pas toute insertion."""
    _creer_entite(cx, "BORDEAUX")
    _creer_entite(cx, "LILLE")
    assert cx.execute(text("SELECT count(*) FROM entity")).scalar_one() == 2


@pytest.mark.integration
def test_un_statut_hors_liste_est_refuse(cx: Connection) -> None:
    with pytest.raises(IntegrityError) as echec:
        _creer_entite(cx, "BORDEAUX", status="ouverte")
    assert "status_valide" in str(echec.value)


@pytest.mark.integration
def test_les_quatre_statuts_du_modele_sont_acceptes(cx: Connection) -> None:
    """Temoin : les quatre valeurs du §5.1 passent toutes."""
    for indice, statut in enumerate(STATUTS_ENTITE):
        _creer_entite(cx, f"ENTITE{indice}", status=statut)
    assert cx.execute(text("SELECT count(*) FROM entity")).scalar_one() == len(STATUTS_ENTITE)


# ----------------------------------------------------------------------------
#  §5.1 : « `code` immuable apres activation » — la regle portee par declencheur
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_le_code_ne_peut_PAS_changer_apres_activation(cx: Connection) -> None:
    identifiant = _creer_entite(cx, "BORDEAUX", status="active", activee=True)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(text("UPDATE entity SET code = 'BDX' WHERE id = :id"), {"id": identifiant})
    assert "entity.code est immuable apres activation" in str(echec.value), (
        "le refus doit venir du declencheur, nomme, et pas d'une autre contrainte"
    )


@pytest.mark.integration
def test_le_code_PEUT_changer_avant_activation(cx: Connection) -> None:
    """Premier temoin : le declencheur ne refuse pas tout changement de code.

    Une entite en `draft`, jamais activee, doit pouvoir corriger son code.
    """
    identifiant = _creer_entite(cx, "BORDEAU", status="draft", activee=False)
    cx.execute(text("UPDATE entity SET code = 'BORDEAUX' WHERE id = :id"), {"id": identifiant})
    code = cx.execute(
        text("SELECT code FROM entity WHERE id = :id"), {"id": identifiant}
    ).scalar_one()
    assert code == "BORDEAUX"


@pytest.mark.integration
def test_les_autres_colonnes_restent_modifiables_apres_activation(cx: Connection) -> None:
    """Second temoin : le declencheur ne verrouille QUE `code`."""
    identifiant = _creer_entite(cx, "BORDEAUX", status="active", activee=True)
    cx.execute(
        text("UPDATE entity SET display_name = 'eXalt Bordeaux Metropole' WHERE id = :id"),
        {"id": identifiant},
    )
    nom = cx.execute(
        text("SELECT display_name FROM entity WHERE id = :id"), {"id": identifiant}
    ).scalar_one()
    assert nom == "eXalt Bordeaux Metropole"


@pytest.mark.integration
def test_l_archivage_ne_supprime_pas_l_historique(cx: Connection) -> None:
    """§2.4 et critere de `US001` : « l'archivage ne supprime pas l'historique »."""
    identifiant = _creer_entite(cx, "BORDEAUX", status="active", activee=True)
    cx.execute(
        text(
            "UPDATE entity SET status = 'archived', archived_at = now(), "
            "archive_reason = 'fermeture du site' WHERE id = :id"
        ),
        {"id": identifiant},
    )
    ligne = cx.execute(
        text(
            "SELECT code, display_name, status, archived_at, archive_reason, created_at "
            "FROM entity WHERE id = :id"
        ),
        {"id": identifiant},
    ).one()
    assert ligne.code == "BORDEAUX", "le code doit survivre a l'archivage"
    assert ligne.display_name == "eXalt Bordeaux"
    assert ligne.status == "archived"
    assert ligne.archived_at is not None
    assert ligne.archive_reason == "fermeture du site"
    assert ligne.created_at is not None


@pytest.mark.integration
def test_le_code_d_une_entite_archivee_reste_reserve(cx: Connection) -> None:
    """L'unicite du §25.1 n'est PAS partielle : le code reste pris.

    C'est un choix trace : reattribuer le code d'une entite archivee rendrait
    ambigus tous les journaux d'audit qui le citent.
    """
    identifiant = _creer_entite(cx, "BORDEAUX", status="active", activee=True)
    cx.execute(
        text("UPDATE entity SET status = 'archived', archived_at = now() WHERE id = :id"),
        {"id": identifiant},
    )
    with pytest.raises(IntegrityError) as echec:
        _creer_entite(cx, "BORDEAUX")
    assert "code_unique" in str(echec.value)


# ----------------------------------------------------------------------------
#  §5.2 et §5.3 : parametres globaux et locaux
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_parametre_global_est_unique_par_cle(cx: Connection) -> None:
    cx.execute(
        text("INSERT INTO platform_setting (key, value) VALUES ('session.duree_minutes', '60')")
    )
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text("INSERT INTO platform_setting (key, value) VALUES ('session.duree_minutes', '90')")
        )
    assert "key_unique" in str(echec.value)


@pytest.mark.integration
def test_une_cle_de_parametre_malformee_est_refusee(cx: Connection) -> None:
    for mauvaise in ("Session.Duree", "session duree", "session..duree", ".session", "session."):
        #  `begin_nested` pose un POINT DE SAUVEGARDE : l'echec annule la seule
        #  insertion fautive et laisse la transaction utilisable pour le tour
        #  suivant. Un `rollback()` suivi d'un `begin()` manuel detachait la
        #  transaction de la connexion -- SQLAlchemy le signalait par un
        #  avertissement, et la boucle ne prouvait plus rien apres le premier tour.
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            cx.execute(
                text("INSERT INTO platform_setting (key, value) VALUES (:cle, '1')"),
                {"cle": mauvaise},
            )
        assert "key_forme_valide" in str(echec.value), (
            f"attendu un refus de forme pour {mauvaise!r}"
        )


@pytest.mark.integration
def test_les_cles_bien_formees_sont_acceptees(cx: Connection) -> None:
    """Temoin : la contrainte de forme ne refuse pas tout."""
    for bonne in ("identite", "session.duree_minutes", "onboarding.parcours.mission"):
        cx.execute(
            text("INSERT INTO platform_setting (key, value) VALUES (:cle, '1')"), {"cle": bonne}
        )
    assert cx.execute(text("SELECT count(*) FROM platform_setting")).scalar_one() == 3


@pytest.mark.integration
def test_un_parametre_local_exige_une_entite_EXISTANTE(cx: Connection) -> None:
    """Cahier §22.2 : « une relation VERIFIABLE vers une entite »."""
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO entity_setting (entity_id, key, value) "
                "VALUES (:id, 'accueil', '\"x\"')"
            ),
            {"id": uuid.uuid4()},
        )
    assert "fk_entity_setting_entity_id_entity" in str(echec.value)


@pytest.mark.integration
def test_un_parametre_local_sur_une_entite_reelle_est_accepte(cx: Connection) -> None:
    """Temoin du precedent."""
    identifiant = _creer_entite(cx)
    cx.execute(
        text(
            "INSERT INTO entity_setting (entity_id, key, value) "
            "VALUES (:id, 'accueil', '\"Bienvenue\"')"
        ),
        {"id": identifiant},
    )
    assert cx.execute(text("SELECT count(*) FROM entity_setting")).scalar_one() == 1


@pytest.mark.integration
def test_la_meme_cle_locale_existe_dans_DEUX_entites(cx: Connection) -> None:
    """C'est le sens meme d'un parametre LOCAL : l'unicite porte sur le couple."""
    bordeaux = _creer_entite(cx, "BORDEAUX")
    lille = _creer_entite(cx, "LILLE")
    for entite in (bordeaux, lille):
        cx.execute(
            text(
                "INSERT INTO entity_setting (entity_id, key, value) "
                "VALUES (:id, 'accueil', '\"x\"')"
            ),
            {"id": entite},
        )
    assert cx.execute(text("SELECT count(*) FROM entity_setting")).scalar_one() == 2

    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO entity_setting (entity_id, key, value) "
                "VALUES (:id, 'accueil', '\"y\"')"
            ),
            {"id": bordeaux},
        )
    assert "entite_cle_unique" in str(echec.value)


@pytest.mark.integration
def test_un_parametre_local_surcharge_le_global_sans_le_supprimer(cx: Connection) -> None:
    """Les deux tables coexistent : la resolution de la surcharge est applicative.

    Ce test prouve seulement que la base ACCEPTE la meme cle des deux cotes. Quel
    niveau l'emporte est une regle de service, et aucun service n'existe avant
    `T11` : le dire plutot que de laisser croire que la base tranche.
    """
    identifiant = _creer_entite(cx)
    cx.execute(text("INSERT INTO platform_setting (key, value) VALUES ('accueil', '\"global\"')"))
    cx.execute(
        text(
            "INSERT INTO entity_setting (entity_id, key, value) "
            "VALUES (:id, 'accueil', '\"local\"')"
        ),
        {"id": identifiant},
    )
    global_, local = cx.execute(
        text(
            "SELECT (SELECT value #>> '{}' FROM platform_setting WHERE key = 'accueil'), "
            "(SELECT value #>> '{}' FROM entity_setting WHERE key = 'accueil')"
        )
    ).one()
    assert global_ == "global"
    assert local == "local"


# ----------------------------------------------------------------------------
#  §5.4 : domaines e-mail autorises
# ----------------------------------------------------------------------------


def _inserer_domaine(connexion: Connection, domain: str, entite: uuid.UUID | None = None) -> None:
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
            "VALUES (:domain, :entite, now())"
        ),
        {"domain": domain, "entite": entite},
    )


@pytest.mark.integration
def test_un_domaine_GLOBAL_a_une_entite_nulle(cx: Connection) -> None:
    """§5.4 : « nullable pour un domaine global ». C'est le point de la table."""
    _inserer_domaine(cx, "exalt-company.com", None)
    ligne = cx.execute(
        text("SELECT entity_id, active, period::text FROM allowed_email_domain")
    ).one()
    assert ligne.entity_id is None
    assert ligne.active is True, "`active` doit valoir true par defaut serveur"
    assert ligne.period.endswith(",)"), "une periode sans fin est non bornee"


@pytest.mark.integration
def test_un_domaine_LOCAL_exige_une_entite_existante(cx: Connection) -> None:
    """La cle etrangere nullable n'exige rien sur NULL, mais tout sur une valeur."""
    with pytest.raises(IntegrityError) as echec:
        _inserer_domaine(cx, "exalt-bordeaux.com", uuid.uuid4())
    assert "fk_allowed_email_domain_entity_id_entity" in str(echec.value)


@pytest.mark.integration
def test_un_domaine_local_sur_une_entite_reelle_est_accepte(cx: Connection) -> None:
    """Temoin du precedent."""
    _inserer_domaine(cx, "exalt-bordeaux.com", _creer_entite(cx))
    assert cx.execute(text("SELECT count(*) FROM allowed_email_domain")).scalar_one() == 1


@pytest.mark.integration
def test_un_domaine_non_normalise_est_refuse(cx: Connection) -> None:
    """§5.4 : « normalise sans `@` »."""
    for mauvais in (
        "@exalt-company.com",
        "EXALT-COMPANY.COM",
        "exalt company.com",
        "exalt-company",
        "-exalt.com",
        "exalt-.com",
    ):
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _inserer_domaine(cx, mauvais, None)
        assert "domain_normalise" in str(echec.value), f"attendu un refus pour {mauvais!r}"


@pytest.mark.integration
def test_les_domaines_normalises_sont_acceptes(cx: Connection) -> None:
    """Temoin : la contrainte ne refuse pas tout."""
    for bon in ("exalt-company.com", "exalt.fr", "mail.exalt-company.co.uk"):
        _inserer_domaine(cx, bon, None)
    assert cx.execute(text("SELECT count(*) FROM allowed_email_domain")).scalar_one() == 3
