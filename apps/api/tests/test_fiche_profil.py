"""La fiche profil complete — story `MVP-L05-US004`.

LOT 5, sous-etape `T4`.

LE CRITERE NOMME UNE REGLE QUE LE CORPUS NE DEFINIT PAS

  « Chaque champ visible **ou** masque selon la matrice, les deux sens testes. »
  **La matrice ne definit aucune visibilite par CHAMP.** Mesure du 26/08/2026 :

    « regles de visibilite »    2 occurrences dans tout le corpus, et ce sont les
                                DEUX copies du critere de `US004` lui-meme
    « masquer » dans la
    matrice                     une phrase, sur les ACTIONS, pas sur les champs

  Les regles applicables sont celles du §5 : « Fiches collaborateur », « Statut
  mission/intercontrat » et « Client actif » sont **en Lecture pour les huit**
  roles authentifies. **Aucun champ n'est masque.** `ECART-051`.

  **CE FICHIER FIGE DONC L'ABSENCE**, plutot que d'inventer un masquage (§6.5).
  Le test des treize champs est ecrit pour un appelant `SUPER` **et** pour un
  employe sans aucune responsabilite : si un lot ulterieur veut masquer un champ,
  il devra casser ce test, donc le decider (§7.32).

CE QUE LA STRUCTURE PROUVE, ET QU'AUCUNE RELECTURE NE PROUVERAIT

  Les `LEFT JOIN` de la fiche ne peuvent pas multiplier les lignes **parce que des
  contraintes d'exclusion l'interdisent**. Un test les exige nommement : le jour
  ou l'une serait relachee, la fiche deviendrait fausse en silence, et celui qui
  la relache doit l'apprendre par un echec (§7.32).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import EtatAppartenance, SituationProfessionnelle
from app.people.profil import EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE, FicheProfil, lire_la_fiche
from app.shared.database import moteur

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

    from sqlalchemy.engine import Connection

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/entities/{code}/people/{appartenance}"
CHEMIN_LISTE = "/api/v1/entities/{code}/people"

ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
JOUR = dt.timedelta(days=1)

#  Les seize champs de la reponse : les treize du §10.2 moins la photo, plus les
#  deux identifiants et la categorie professionnelle. **Declares ici et confrontes
#  a la reponse servie** : un champ ajoute sans etre voulu fait echouer.
CHAMPS_ATTENDUS = frozenset(
    {
        "id",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "professional_category",
        "arrival_date",
        "short_bio",
        "fun_fact",
        "metier",
        "statut",
        "client",
        "dsm",
        "cercle_principal",
        "cercles_secondaires",
        "responsabilites",
    }
)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


# ===========================================================================
#  1. Sans base : ce que la structure declare
# ===========================================================================


def test_la_photo_n_est_dans_AUCUN_champ_de_la_fiche() -> None:
    """**LA PHOTO ATTEND `T5` ET `T6`, ET IL FAUT LE DIRE.**

    Le §10.2 la nomme en premier ; le §12.2 impose un avatar neutre sans
    autorisation active. Rien de tout cela n'existe encore, et un champ `photo`
    qui vaudrait toujours `null` laisserait croire que la regle est appliquee.
    """
    assert not any("photo" in champ for champ in CHAMPS_ATTENDUS)
    assert not any("avatar" in champ for champ in CHAMPS_ATTENDUS)


def test_les_quatre_exclusions_qui_rendent_la_jointure_sure_sont_declarees() -> None:
    """La liste est courte et nommee : elle doit correspondre au reel.

    Le test d'integration, plus bas, verifie qu'elles existent VRAIMENT en base.
    Celui-ci ne verifie que la declaration -- sans lui, un nom mal orthographie
    rendrait l'autre test silencieusement vide.
    """
    assert len(EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE) == 4
    assert all(nom.startswith("ex_") for nom in EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE)
    assert len(set(EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE)) == 4


# ===========================================================================
#  2. Le decor : un profil COMPLET, et un profil VIDE
# ===========================================================================


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, dict[str, Any]]]:
    """Une entite, un profil complet, un profil sans aucune relation, et un exclu.

    **LE PROFIL VIDE N'EST PAS UN LUXE** : sans lui, une fiche qui rendrait
    n'importe quoi pour les relations absentes passerait -- toutes les valeurs
    seraient renseignees, donc jamais confrontees a `null`.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t4l5{uuid.uuid4().hex[:10]}"
    code_entite = f"{marqueur}-e"

    with moteur(parametres).connect() as horloge:
        debut_temps = horloge.execute(text("SELECT now()")).scalar_one()

    reperes: dict[str, Any] = {}
    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": code_entite, "nom": f"Entite {marqueur}"},
        ).scalar_one()
        reperes["entite"] = entite

        for nom in ("principal", "second-a", "second-b"):
            reperes[f"cercle-{nom}"] = cx.execute(
                text(
                    "INSERT INTO circle (entity_id, code, name, color_token, display_order) "
                    "VALUES (:e, :code, :nom, 'bleu', 0) RETURNING id"
                ),
                {"e": entite, "code": f"{marqueur}-{nom}", "nom": f"Cercle {nom}"},
            ).scalar_one()

        reperes["bureau"] = cx.execute(
            text(
                "INSERT INTO office (entity_id, code, name, display_order) "
                "VALUES (:e, :code, :nom, 0) RETURNING id"
            ),
            {"e": entite, "code": f"{marqueur}-bureau", "nom": "Bureau des essais"},
        ).scalar_one()

        reperes["metier"] = cx.execute(
            text(
                "INSERT INTO job_catalog (entity_id, code, label, display_order, active) "
                "VALUES (:e, :code, :libelle, 0, TRUE) RETURNING id"
            ),
            {"e": entite, "code": f"{marqueur}-job", "libelle": "Ingenieure logicielle"},
        ).scalar_one()

        reperes["client"] = cx.execute(
            text(
                "INSERT INTO client (canonical_name, display_name, status) "
                "VALUES (:canon, :affiche, 'active') RETURNING id"
            ),
            {"canon": f"{marqueur}-client", "affiche": "Client Alpha"},
        ).scalar_one()
        cx.execute(
            text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
            {"e": entite, "c": reperes["client"]},
        )

        #  Le DSM, avec sa responsabilite AVANT son affectation — la base l'exige.
        reperes["dsm_personne"] = _personne(cx, marqueur, "Dominique", "Lesmanager")
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment "
                "(person_id, entity_id, responsibility_type, assigned_by_person_id, "
                "starts_at, ends_at) VALUES (:p, :e, :type, :p, :d, NULL)"
            ),
            {
                "p": reperes["dsm_personne"],
                "e": entite,
                "type": TypeResponsabilite.DSM.value,
                "d": ANCRAGE - 30 * JOUR,
            },
        )

        #  --- le profil COMPLET ---------------------------------------------
        complete = _personne(cx, marqueur, "Ada", "Complete")
        reperes["personne_complete"] = complete
        reperes["complete"] = _appartenance(
            cx, entite, complete, bio="Ingenieure passionnee.", fun="Joue du theorbe."
        )
        _relations_completes(cx, entite, reperes)

        #  --- le profil VIDE : aucune relation, ni bio ni fun fact ------------
        vide = _personne(cx, marqueur, "Zoe", "Vide")
        reperes["vide"] = _appartenance(cx, entite, vide, bio=None, fun=None)

        #  --- un profil NON LISTABLE : appartenance partie ---------------------
        parti = _personne(cx, marqueur, "Ivan", "Parti")
        reperes["parti"] = _appartenance(
            cx, entite, parti, bio=None, fun=None, etat=EtatAppartenance.DEPARTED.value
        )

    try:
        yield parametres, code_entite, reperes
    finally:
        _nettoyer(parametres, marqueur, debut_temps)


def _personne(cx: Connection, marqueur: str, prenom: str, nom: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, :p, :n, 'active') RETURNING id"
                ),
                {"a": f"{marqueur}-{nom}@exemple.test".lower(), "p": prenom, "n": nom},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    bio: str | None,
    fun: str | None,
    etat: str = EtatAppartenance.ACTIVE.value,
) -> uuid.UUID:
    depart = dt.date(2026, 6, 1) if etat == EtatAppartenance.DEPARTED.value else None
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "departure_date, membership_state, professional_category, "
                    "profile_visibility, short_bio, fun_fact) "
                    "VALUES (:p, :e, DATE '2026-01-15', :depart, :etat, 'consultant', "
                    "'published', :bio, :fun) RETURNING id"
                ),
                {
                    "p": personne,
                    "e": entite,
                    "depart": depart,
                    "etat": etat,
                    "bio": bio,
                    "fun": fun,
                },
            ).scalar_one()
        )
    )


def _relations_completes(cx: Connection, entite: uuid.UUID, r: dict[str, Any]) -> None:
    """Les cinq relations uniques, deux cercles secondaires, deux responsabilites."""
    debut = ANCRAGE - 30 * JOUR
    appartenance = r["complete"]
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
            "job_catalog_id, starts_at, ends_at) VALUES (:e, :m, :j, :d, NULL)"
        ),
        {"e": entite, "m": appartenance, "j": r["metier"], "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, client_id, starts_at, ends_at) VALUES (:e, :m, :s, :c, :d, NULL)"
        ),
        {
            "e": entite,
            "m": appartenance,
            "s": SituationProfessionnelle.MISSION.value,
            "c": r["client"],
            "d": debut,
        },
    )
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at, ends_at) VALUES (:e, :m, :p, :d, NULL)"
        ),
        {"e": entite, "m": appartenance, "p": r["dsm_personne"], "d": debut},
    )
    for cle, type_ in (
        ("cercle-principal", TypeAppartenanceCercle.PRINCIPAL.value),
        ("cercle-second-a", TypeAppartenanceCercle.SECONDARY.value),
        ("cercle-second-b", TypeAppartenanceCercle.SECONDARY.value),
    ):
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at, ends_at) VALUES (:e, :m, :c, :t, :d, NULL)"
            ),
            {"e": entite, "m": appartenance, "c": r[cle], "t": type_, "d": debut},
        )
    #  Deux responsabilites : un BOOSTER porte sur un CERCLE, un OFFICE_MANAGER
    #  sur un BUREAU. Le §8.4 l'impose, et la fiche doit rendre la bonne portee.
    for type_, cercle, bureau in (
        (TypeResponsabilite.BOOSTER.value, r["cercle-principal"], None),
        (TypeResponsabilite.OFFICE_MANAGER.value, None, r["bureau"]),
    ):
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, circle_id, office_id, assigned_by_person_id, "
                "starts_at, ends_at) VALUES (:p, :e, :t, :c, :o, :p, :d, NULL)"
            ),
            {
                "p": r["personne_complete"],
                "e": entite,
                "t": type_,
                "c": cercle,
                "o": bureau,
                "d": debut,
            },
        )


def _nettoyer(parametres: Parametres, marqueur: str, debut: dt.datetime) -> None:
    """L'ordre suit les cles etrangeres ; la borne temporelle attrape le reste."""
    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM framework_responsibility_assignment WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM membership_job_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM professional_status_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM entity_client WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM office WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM job_catalog WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM client WHERE canonical_name LIKE :motif",
            "DELETE FROM person WHERE email_normalized LIKE :motif",
            "DELETE FROM entity WHERE code LIKE :motif",
            "DELETE FROM auth_event WHERE person_id IS NULL "
            "  AND service_account_id IS NULL AND created_at >= :debut",
        ):
            menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _session(parametres: Parametres, marqueur: str, suffixe: str = "") -> str:
    adresse = f"{marqueur}{suffixe}-appelant@exemple.test"
    with moteur(parametres).begin() as cx:
        personne = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO person (email, email_normalized, first_name, last_name, "
                        "account_state) VALUES (:a, :a, 'Appelant', 'T4', 'active') RETURNING id"
                    ),
                    {"a": adresse},
                ).scalar_one()
            )
        )
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _appeler(
    parametres: Parametres, chemin: str, jeton: str | None, entetes: dict[str, str] | None = None
) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin, headers=entetes or {})


# ===========================================================================
#  3. Les treize champs, et l'ABSENCE de masquage
# ===========================================================================


@pytest.mark.integration
def test_la_fiche_rend_les_champs_du_10_2(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE TEMOIN CENTRAL.** Sans lui, toute exclusion serait satisfaite par une
    route qui ne rend jamais rien.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=code, appartenance=r["complete"]),
        _session(parametres, code[:-2]),
    )
    assert reponse.status_code == 200, reponse.text
    fiche = reponse.json()

    assert set(fiche) == CHAMPS_ATTENDUS, "ni plus ni moins que les champs voulus"
    assert fiche["first_name"] == "Ada"
    assert fiche["last_name"] == "Complete"
    assert fiche["metier"] == "Ingenieure logicielle"
    assert fiche["statut"] == SituationProfessionnelle.MISSION.value
    assert fiche["client"] == "Client Alpha"
    assert fiche["dsm"] == "Dominique Lesmanager"
    assert fiche["short_bio"] == "Ingenieure passionnee."
    assert fiche["fun_fact"] == "Joue du theorbe."
    assert fiche["arrival_date"] == "2026-01-15"

    assert fiche["cercle_principal"]["nom"] == "Cercle principal"
    assert [c["nom"] for c in fiche["cercles_secondaires"]] == [
        "Cercle second-a",
        "Cercle second-b",
    ]

    #  **LA PORTEE DE CHAQUE RESPONSABILITE, ET C'EST LE §8.4** : un BOOSTER porte
    #  sur un cercle, un OFFICE_MANAGER sur un bureau, jamais les deux.
    par_type = {r_["type"]: r_ for r_ in fiche["responsabilites"]}
    assert set(par_type) == {
        TypeResponsabilite.BOOSTER.value,
        TypeResponsabilite.OFFICE_MANAGER.value,
    }
    assert par_type[TypeResponsabilite.BOOSTER.value]["cercle"] == "Cercle principal"
    assert par_type[TypeResponsabilite.BOOSTER.value]["bureau"] is None
    assert par_type[TypeResponsabilite.OFFICE_MANAGER.value]["bureau"] == "Bureau des essais"
    assert par_type[TypeResponsabilite.OFFICE_MANAGER.value]["cercle"] is None


@pytest.mark.integration
def test_AUCUN_champ_n_est_masque_a_un_employe_SANS_responsabilite(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**CE TEST FIGE UNE ABSENCE, ET C'EST SON OBJET** (§7.32).

    Le critere de `T4` dit « chaque champ visible **ou** masque selon la
    matrice ». La matrice ne definit **aucune** visibilite par champ : « regles de
    visibilite » ne parait que dans les deux copies du critere de `US004`
    lui-meme, et le seul « masquer » de la matrice porte sur les **actions**. Le
    §5 donne « Fiches collaborateur », « Statut mission/intercontrat » et « Client
    actif » en **Lecture aux huit** roles.

    L'appelant de ce test n'a **aucune** responsabilite, **aucune** appartenance
    dans l'entite, **aucun** role technique : c'est le cas le plus depourvu qu'une
    session puisse porter. Il voit **tout**.

    Si un lot ulterieur veut masquer un champ, il devra casser ce test, donc le
    decider. `ECART-051`.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=code, appartenance=r["complete"]),
        _session(parametres, code[:-2], "-nu"),
    )
    assert reponse.status_code == 200, reponse.text
    fiche = reponse.json()

    #  Chaque champ SENSIBLE du §10.2 est renseigne et lisible.
    for champ in ("metier", "statut", "client", "dsm", "short_bio", "fun_fact"):
        assert fiche[champ] is not None, (
            f"« {champ} » est masque a un employe sans responsabilite — or la matrice "
            f"ne definit aucune visibilite par champ (ECART-051)"
        )
    assert fiche["cercle_principal"] is not None
    assert len(fiche["cercles_secondaires"]) == 2
    assert len(fiche["responsabilites"]) == 2


@pytest.mark.integration
def test_un_profil_SANS_relation_rend_des_valeurs_nulles_et_des_listes_vides(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**SANS CE CAS, UNE FICHE QUI RENDRAIT N'IMPORTE QUOI PASSERAIT.**

    Le profil complet a toutes ses relations : aucune valeur n'y est confrontee a
    `null`. Celui-ci n'en a aucune.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=code, appartenance=r["vide"]),
        _session(parametres, code[:-2], "-vide"),
    )
    assert reponse.status_code == 200, reponse.text
    fiche = reponse.json()
    assert set(fiche) == CHAMPS_ATTENDUS
    assert fiche["last_name"] == "Vide"
    for champ in ("metier", "statut", "client", "dsm", "short_bio", "fun_fact", "cercle_principal"):
        assert fiche[champ] is None, f"« {champ} » devrait etre nul"
    assert fiche["cercles_secondaires"] == []
    assert fiche["responsabilites"] == []
    #  Les champs OBLIGATOIRES restent renseignes.
    assert fiche["first_name"] and fiche["arrival_date"] and fiche["professional_category"]


# ===========================================================================
#  4. La population, les refus, et le nombre de requetes
# ===========================================================================


@pytest.mark.integration
def test_un_profil_NON_LISTABLE_rend_le_MEME_404_qu_une_entite_inconnue(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**QUATRE CAUSES, UNE SEULE REPONSE**, corps ET en-tetes, correlation FIXEE.

    Un refus distinct pour « cette appartenance existe mais son profil est
    masque » apprendrait l'existence de la personne. La comparaison porte sur la
    signature entiere, la correlation etant **fixee** plutot qu'un champ exclu.
    """
    parametres, code, r = decor
    jeton = _session(parametres, code[:-2], "-404")
    entetes = {"X-Request-ID": "l5t4-egalite-des-refus"}

    parti = _appeler(parametres, CHEMIN.format(code=code, appartenance=r["parti"]), jeton, entetes)
    inexistant = _appeler(
        parametres, CHEMIN.format(code=code, appartenance=uuid.uuid4()), jeton, entetes
    )
    entite_inconnue = _appeler(
        parametres,
        CHEMIN.format(code=f"{code}-nexiste-pas", appartenance=r["complete"]),
        jeton,
        entetes,
    )

    assert parti.status_code == inexistant.status_code == entite_inconnue.status_code == 404
    assert parti.json() == inexistant.json() == entite_inconnue.json()
    interessants = {"content-type", "x-request-id"}
    signatures = [
        {n.lower(): v for n, v in r_.headers.items() if n.lower() in interessants}
        for r_ in (parti, inexistant, entite_inconnue)
    ]
    assert signatures[0] == signatures[1] == signatures[2]


@pytest.mark.integration
def test_une_appartenance_d_une_AUTRE_entite_est_introuvable(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """§25.3 : l'isolation ne tient pas au hasard du chemin.

    L'appartenance existe et son profil est publie ; seule l'entite du chemin
    differe. Sans le filtre `entity_id`, la fiche serait servie.
    """
    parametres, code, r = decor
    autre = f"{code}-bis"
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Lyon', 'FR', 'active', 'Europe/Paris')"
            ),
            {"code": autre, "nom": f"Autre {code}"},
        )
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=autre, appartenance=r["complete"]),
        _session(parametres, code[:-2], "-autre"),
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_sans_session_la_fiche_refuse(decor: tuple[Parametres, str, dict[str, Any]]) -> None:
    """La matrice §5 met `ANON` a tiret.

    **CE TEST PROUVE AUSSI QUE `Annotated` NE PIEGE PAS ICI** : le piege mesure en
    `T1` du LOT 4 rendait **422** avec `loc: ["query", ...]`, FastAPI ne voyant pas
    la dependance. Un 401 le refute.
    """
    parametres, code, r = decor
    reponse = _appeler(parametres, CHEMIN.format(code=code, appartenance=r["complete"]), None)
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
def test_un_identifiant_d_appartenance_mal_forme_est_refuse(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """Le parametre est type `uuid.UUID` : le refus porte le format du §18.3."""
    parametres, code, _r = decor
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=code, appartenance="pas-un-uuid"),
        _session(parametres, code[:-2], "-mal"),
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["champ"] == "path.appartenance"


@pytest.mark.integration
def test_la_fiche_tient_en_TROIS_requetes_quel_que_soit_son_contenu(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**COMPTE, PAS SUPPOSE** — le critere de `T3`, applique ici.

    Trois requetes : la fiche et ses cinq relations uniques, les cercles
    secondaires, les responsabilites. Le profil COMPLET en a sept au total et le
    profil VIDE aucune : si le nombre dependait du contenu, la difference se
    verrait ici et nulle part ailleurs.
    """
    from test_recherche_et_filtres import Compteur

    parametres, _code, r = decor
    with moteur(parametres).connect() as cx:
        for cle in ("complete", "vide"):
            with Compteur(cx) as compteur:
                fiche = lire_la_fiche(cx, entite=r["entite"], appartenance=r[cle], instant=ANCRAGE)
            assert isinstance(fiche, FicheProfil)
            assert len(compteur.requetes) == 3, (
                f"« {cle} » : {len(compteur.requetes)} requetes, 3 attendues"
            )


@pytest.mark.integration
def test_les_QUATRE_exclusions_existent_VRAIMENT_en_base(
    parametres_de_la_stack: Parametres,
) -> None:
    """**CE QUI REND LES `LEFT JOIN` SURS EST LE SCHEMA, PAS UNE RELECTURE.**

    Metier, statut, DSM et cercle principal sont uniques a un instant donne parce
    que ces exclusions interdisent le chevauchement des periodes. Si l'une etait
    relachee, la fiche multiplierait ses lignes **en silence** -- et celui qui la
    relache doit l'apprendre par un echec, non par un commentaire (§7.32).
    """
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as cx:
        presentes = {
            str(nom)
            for (nom,) in cx.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'x'"))
        }
    manquantes = sorted(set(EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE) - presentes)
    assert not manquantes, (
        f"exclusion(s) disparue(s) : {manquantes}. La fiche profil joint ces relations "
        f"en supposant qu'une seule est active a la fois — sans l'exclusion, elle "
        f"multiplierait ses lignes sans que rien ne le signale."
    )
