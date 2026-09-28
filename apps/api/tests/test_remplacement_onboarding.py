"""Remplacer le parcours au changement de statut — LOT 7, `T10`, `US007`.

matrice §8.1 « Remplacer le parcours apres changement de statut » / §8.2,
modele §6.5/§14.1/§24.2. `ECART-013` mis a l'epreuve pour de vrai (`US007`).

CE FICHIER APPELLE `modifier_les_donnees_organisationnelles` DIRECTEMENT,
JAMAIS PAR HTTP — meme parti que `test_ecriture_organisationnelle.py` (LOT 5,
`T7`). `T10` n'ajoute AUCUNE grille de permission propre (voir l'en-tete
d'`app/onboarding/instances.py`) : la garde deja exercee par l'ecrivain du
champ `STATUT` EST la garde de ce geste. Reexercer une permission ici
reviendrait a retester le LOT 5 / le `T7` de ce lot, deja fait ailleurs.

CE QUE CHAQUE TEST PROUVE, ET POURQUOI IL EST SEPARE DES AUTRES

  Chaque test isole UNE ligne du modele plutot que d'empiler les assertions
  dans un seul scenario — §7.39 : un critere qui melange plusieurs
  comportements laisse un `WHERE` faux passer inapercu si un seul des deux
  est reellement exerce.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator, Sequence
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.onboarding.cycle_de_vie import publier_une_version
from app.onboarding.gabarits import (
    NouvelleTacheDeVersion,
    creer_un_modele,
    creer_une_version,
    definir_les_taches_de_la_version,
)
from app.onboarding.instances import (
    CODE_AUCUN_MODELE_PUBLIE,
    Appartenance,
    affecter_un_parcours,
    lire_l_instance_active,
    lire_le_parcours,
)
from app.people.ecriture import modifier_les_donnees_organisationnelles
from app.permissions.perimetre import TOUS_LES_CHAMPS, ChampOrganisationnel, PerimetreDEcriture
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(days=400)
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


# ---------------------------------------------------------------------------
#  Le decor. Chaque aide est locale a ce fichier — meme discipline que
#  `test_ecriture_organisationnelle.py`.
# ---------------------------------------------------------------------------


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Sujet', 'T10L7', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'published') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": ANCRAGE.date()},
    ).scalar_one()


def _client(cx: Connection, nom: str, entite: uuid.UUID) -> uuid.UUID:
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affichage, 'active') RETURNING id"
        ),
        {"canonique": nom.lower(), "affichage": nom},
    ).scalar_one()
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    return client  # type: ignore[no-any-return]


def _statut_initial(
    cx: Connection, cible: uuid.UUID, entite: uuid.UUID, *, statut: str, client: uuid.UUID | None
) -> None:
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_membership_id, entity_id, "
            "status, client_id, starts_at) VALUES (:c, :e, :s, :cl, :debut)"
        ),
        {"c": cible, "e": entite, "s": statut, "cl": client, "debut": ANCRAGE},
    )


def _tache_de_reference(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO onboarding_task_reference (entity_id, code, title) "
                    "VALUES (:e, :c, :t) RETURNING id"
                ),
                {"e": entite, "c": code, "t": f"Titre {code}"},
            ).scalar_one()
        )
    )


def _modele_publie(
    cx: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    *,
    name: str,
    target_status: str,
    taches: Sequence[tuple[uuid.UUID, int, str | None]],
) -> uuid.UUID:
    """Un modele ENTITY publie pour `target_status` — les TROIS routes reelles
    du service (`T5`/`T6`), jamais une ecriture directe en base. `taches` :
    `(task_reference_id, due_offset_days, title_override)`."""
    modele = creer_un_modele(
        cx,
        entite=entite,
        name=name,
        target_status=target_status,
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
    )
    version = creer_une_version(cx, modele=modele.id, change_summary=None)
    definir_les_taches_de_la_version(
        cx,
        modele=modele,
        version=version,
        taches=tuple(
            NouvelleTacheDeVersion(
                task_reference_id=reference,
                required=True,
                due_offset_days=decalage,
                title_override=titre,
                description_override=None,
            )
            for reference, decalage, titre in taches
        ),
    )
    publiee = publier_une_version(cx, version=version.id, acteur=acteur, instant=ANCRAGE)
    return publiee.id


def _lire_instance(cx: Connection, instance: uuid.UUID) -> dict[str, Any]:
    return dict(
        cx.execute(
            text(
                "SELECT state, template_version_id, reference_date, replaced_by_instance_id "
                "FROM onboarding_instance WHERE id = :i"
            ),
            {"i": instance},
        )
        .mappings()
        .one()
    )


def _lire_taches(cx: Connection, instance: uuid.UUID) -> list[dict[str, Any]]:
    return [
        dict(ligne)
        for ligne in cx.execute(
            text(
                "SELECT id, task_reference_id, title_snapshot, required, due_at, state, "
                "completed_at, completed_by_person_id FROM onboarding_instance_task "
                "WHERE onboarding_instance_id = :i ORDER BY due_at"
            ),
            {"i": instance},
        ).mappings()
    ]


def _lire_evenements(cx: Connection, tache: uuid.UUID) -> list[dict[str, Any]]:
    return [
        dict(ligne)
        for ligne in cx.execute(
            text(
                "SELECT event_type, actor_person_id FROM onboarding_task_event "
                "WHERE onboarding_instance_task_id = :t ORDER BY occurred_at"
            ),
            {"t": tache},
        ).mappings()
    ]


def _statut_courant(cx: Connection, cible: uuid.UUID) -> dict[str, Any]:
    return dict(
        cx.execute(
            text(
                "SELECT status, client_id, ends_at FROM professional_status_assignment "
                "WHERE entity_membership_id = :c ORDER BY starts_at DESC LIMIT 1"
            ),
            {"c": cible},
        )
        .mappings()
        .one()
    )


def _tout() -> PerimetreDEcriture:
    return PerimetreDEcriture(champs=TOUS_LES_CHAMPS)


def _changer_le_statut(
    cx: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    nouveau_statut: str,
    instant: dt.datetime,
) -> Any:
    """Demande le SEUL champ `statut` — jamais `client`, dont la valeur reste
    absente de `demande` : c'est la cle qui compte pour `_ecrire_le_statut`
    (voir son docstring), pas la valeur ecrite. Un `intercontract` retire son
    client SANS qu'on le nomme (§30.5), deja eprouve au LOT 5 `T7`."""
    demande: dict[ChampOrganisationnel, Any] = {ChampOrganisationnel.STATUT: nouveau_statut}
    return modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande=demande,
        perimetre=_tout(),
        instant=instant,
    )


# ===========================================================================
#  L'ancienne instance passe `replaced`, une nouvelle est active
# ===========================================================================


@pytest.mark.integration
def test_le_changement_de_statut_cloture_l_ancienne_instance_et_en_ouvre_une_nouvelle(
    cx: Connection,
) -> None:
    entite = _entite(cx, "T10-BASE")
    acteur = _personne(cx, "t10-base-a@exalt-company.com")
    personne = _personne(cx, "t10-base-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    client_mission = _client(cx, "T10-BASE-CLIENT", entite)
    _statut_initial(cx, cible, entite, statut="mission", client=client_mission)

    tache = _tache_de_reference(cx, entite, "T10-BASE-TACHE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-BASE-MISSION",
        target_status="mission",
        taches=[(tache, 3, None)],
    )
    version_intercontrat = _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-BASE-INTER",
        target_status="intercontract",
        taches=[(tache, 5, None)],
    )

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    ancienne_id = ancienne.instance.id

    instant_remplacement = ANCRAGE + 30 * JOUR
    _changer_le_statut(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        nouveau_statut="intercontract",
        instant=instant_remplacement,
    )

    ligne_ancienne = _lire_instance(cx, ancienne_id)
    assert ligne_ancienne["state"] == "replaced"
    assert ligne_ancienne["replaced_by_instance_id"] is not None

    nouvelle_id = uuid.UUID(str(ligne_ancienne["replaced_by_instance_id"]))
    ligne_nouvelle = _lire_instance(cx, nouvelle_id)
    assert ligne_nouvelle["state"] == "active"
    assert uuid.UUID(str(ligne_nouvelle["template_version_id"])) == version_intercontrat
    assert ligne_nouvelle["reference_date"] == instant_remplacement.date()

    active = lire_l_instance_active(cx, entite=entite, appartenance=cible)
    assert active is not None
    assert active.id == nouvelle_id, "une seule instance active — la nouvelle, pas l'ancienne"


# ===========================================================================
#  `ECART-013` a l'epreuve : une tache commune COMPLETED est RETENUE
# ===========================================================================


@pytest.mark.integration
def test_une_tache_commune_terminee_est_retenue_et_ses_echeances_recalculees(
    cx: Connection,
) -> None:
    entite = _entite(cx, "T10-RETENUE")
    acteur = _personne(cx, "t10-retenue-a@exalt-company.com")
    completeur = _personne(cx, "t10-retenue-comp@exalt-company.com")
    personne = _personne(cx, "t10-retenue-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _statut_initial(
        cx, cible, entite, statut="mission", client=_client(cx, "T10-RETENUE-CL", entite)
    )

    commune = _tache_de_reference(cx, entite, "T10-RETENUE-COMMUNE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-RETENUE-MISSION",
        target_status="mission",
        taches=[(commune, 3, "Titre mission")],
    )
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-RETENUE-INTER",
        target_status="intercontract",
        taches=[(commune, 10, "Titre intercontrat")],
    )

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    tache_ancienne = ancienne.taches[0]
    instant_completion = ANCRAGE + 2 * JOUR
    cx.execute(
        text(
            "UPDATE onboarding_instance_task SET state = 'completed', completed_at = :i, "
            "completed_by_person_id = :p WHERE id = :t"
        ),
        {"i": instant_completion, "p": completeur, "t": tache_ancienne.id},
    )

    instant_remplacement = ANCRAGE + 30 * JOUR
    _changer_le_statut(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        nouveau_statut="intercontract",
        instant=instant_remplacement,
    )

    nouvelle_id = lire_l_instance_active(cx, entite=entite, appartenance=cible)
    assert nouvelle_id is not None
    taches_nouvelles = _lire_taches(cx, nouvelle_id.id)
    assert len(taches_nouvelles) == 1
    retenue = taches_nouvelles[0]
    assert retenue["state"] == "completed"
    assert retenue["completed_at"] == instant_completion, "la trace ORIGINALE est preservee"
    assert retenue["completed_by_person_id"] == completeur

    #  RECALCULEE depuis la NOUVELLE version : titre ET echeance, jamais copies.
    assert retenue["title_snapshot"] == "Titre intercontrat"
    assert retenue["due_at"] == dt.datetime.combine(
        instant_remplacement.date(), dt.time.min, tzinfo=dt.UTC
    ) + dt.timedelta(days=10)

    evenements = _lire_evenements(cx, uuid.UUID(str(retenue["id"])))
    assert [e["event_type"] for e in evenements] == ["RETAINED_ON_REPLACEMENT"]
    assert evenements[0]["actor_person_id"] == acteur


# ===========================================================================
#  Les taches EN COURS de l'ancienne (`todo`, `reopened`) deviennent `cancelled`
# ===========================================================================


@pytest.mark.integration
def test_les_taches_todo_et_reopened_de_l_ancienne_deviennent_cancelled(cx: Connection) -> None:
    entite = _entite(cx, "T10-ANNULE")
    acteur = _personne(cx, "t10-annule-a@exalt-company.com")
    personne = _personne(cx, "t10-annule-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _statut_initial(
        cx, cible, entite, statut="mission", client=_client(cx, "T10-ANNULE-CL", entite)
    )

    encore_todo = _tache_de_reference(cx, entite, "T10-ANNULE-TODO")
    deja_reouverte = _tache_de_reference(cx, entite, "T10-ANNULE-REOUVERTE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-ANNULE-MISSION",
        target_status="mission",
        taches=[(encore_todo, 3, None), (deja_reouverte, 4, None)],
    )
    #  Le modele intercontrat ne porte NI l'une ni l'autre : les deux taches
    #  n'ont donc aucune ligne dans la NOUVELLE instance, seulement un
    #  changement d'etat sur l'ANCIENNE.
    autre_tache = _tache_de_reference(cx, entite, "T10-ANNULE-AUTRE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-ANNULE-INTER",
        target_status="intercontract",
        taches=[(autre_tache, 3, None)],
    )

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    ancienne_id = ancienne.instance.id
    id_todo = next(t.id for t in ancienne.taches if t.task_reference_id == encore_todo)
    id_reouverte = next(t.id for t in ancienne.taches if t.task_reference_id == deja_reouverte)

    #  Cette tache a deja ete completee PUIS reouverte administrativement —
    #  `reopened` est le MEME etat « pas termine » que `todo`, voir l'en-tete
    #  du module.
    cx.execute(
        text(
            "UPDATE onboarding_instance_task SET state = 'reopened', "
            "completed_at = :completion, completed_by_person_id = :acteur, "
            "reopened_at = :reouverture, reopened_by_person_id = :acteur, "
            "reopen_reason = 'Erreur de saisie, motif de test.' WHERE id = :t"
        ),
        {
            "completion": ANCRAGE + 2 * JOUR,
            "reouverture": ANCRAGE + 3 * JOUR,
            "acteur": acteur,
            "t": id_reouverte,
        },
    )

    instant_remplacement = ANCRAGE + 30 * JOUR
    _changer_le_statut(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        nouveau_statut="intercontract",
        instant=instant_remplacement,
    )

    taches_ancienne = {uuid.UUID(str(t["id"])): t for t in _lire_taches(cx, ancienne_id)}
    assert taches_ancienne[id_todo]["state"] == "cancelled"
    assert taches_ancienne[id_reouverte]["state"] == "cancelled"

    for tache_id in (id_todo, id_reouverte):
        evenements = _lire_evenements(cx, tache_id)
        assert evenements[-1]["event_type"] == "CANCELLED_ON_REPLACEMENT"
        assert evenements[-1]["actor_person_id"] == acteur

    #  Ni l'une ni l'autre n'a de ligne dans la NOUVELLE instance : elles
    #  n'appartiennent pas a la version intercontrat.
    nouvelle = lire_l_instance_active(cx, entite=entite, appartenance=cible)
    assert nouvelle is not None
    references_nouvelles = {t["task_reference_id"] for t in _lire_taches(cx, nouvelle.id)}
    assert encore_todo not in references_nouvelles
    assert deja_reouverte not in references_nouvelles


# ===========================================================================
#  Un changement de CLIENT SEUL, meme statut, ne remplace RIEN
# ===========================================================================


@pytest.mark.integration
def test_un_changement_de_client_seul_meme_statut_ne_remplace_rien(cx: Connection) -> None:
    entite = _entite(cx, "T10-CLIENT")
    acteur = _personne(cx, "t10-client-a@exalt-company.com")
    personne = _personne(cx, "t10-client-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    ancien_client = _client(cx, "T10-CLIENT-A", entite)
    nouveau_client = _client(cx, "T10-CLIENT-B", entite)
    _statut_initial(cx, cible, entite, statut="mission", client=ancien_client)

    tache = _tache_de_reference(cx, entite, "T10-CLIENT-TACHE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-CLIENT-MISSION",
        target_status="mission",
        taches=[(tache, 3, None)],
    )

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    ancienne_id = ancienne.instance.id

    modification = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.CLIENT: nouveau_client},
        perimetre=_tout(),
        instant=ANCRAGE + 30 * JOUR,
    )
    assert modification.champs == {ChampOrganisationnel.CLIENT}

    ligne = _lire_instance(cx, ancienne_id)
    assert ligne["state"] == "active", "aucun remplacement pour un changement de client seul"
    assert ligne["replaced_by_instance_id"] is None
    assert _statut_courant(cx, cible)["client_id"] == nouveau_client


# ===========================================================================
#  Aucune instance active : le geste ne fait RIEN, jamais une erreur
# ===========================================================================


@pytest.mark.integration
def test_sans_instance_active_le_changement_de_statut_ne_fait_rien(cx: Connection) -> None:
    entite = _entite(cx, "T10-VIERGE")
    acteur = _personne(cx, "t10-vierge-a@exalt-company.com")
    personne = _personne(cx, "t10-vierge-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _statut_initial(
        cx, cible, entite, statut="mission", client=_client(cx, "T10-VIERGE-CL", entite)
    )
    #  AUCUN modele intercontrat n'est publie, et ce n'est pas un oubli : si
    #  le remplacement etait tente quand meme, ceci echouerait en 422.

    modification = _changer_le_statut(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        nouveau_statut="intercontract",
        instant=ANCRAGE + JOUR,
    )
    assert modification.champs == {ChampOrganisationnel.STATUT}
    assert lire_l_instance_active(cx, entite=entite, appartenance=cible) is None
    nombre_instances = cx.execute(
        text("SELECT count(*) FROM onboarding_instance WHERE entity_membership_id = :c"),
        {"c": cible},
    ).scalar_one()
    assert nombre_instances == 0


# ===========================================================================
#  Aucun modele publie pour le nouveau statut : 422, et TOUTE la transaction
#  est annulee — y compris le changement de statut lui-meme.
# ===========================================================================


@pytest.mark.integration
def test_l_absence_de_modele_publie_est_422_et_annule_toute_la_transaction(
    cx: Connection,
) -> None:
    entite = _entite(cx, "T10-422")
    acteur = _personne(cx, "t10-422-a@exalt-company.com")
    personne = _personne(cx, "t10-422-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    client_mission = _client(cx, "T10-422-CL", entite)
    _statut_initial(cx, cible, entite, statut="mission", client=client_mission)

    tache = _tache_de_reference(cx, entite, "T10-422-TACHE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-422-MISSION",
        target_status="mission",
        taches=[(tache, 3, None)],
    )
    #  AUCUN modele publie pour `intercontract` dans cette entite.

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    ancienne_id = ancienne.instance.id

    with pytest.raises(ErreurApplicative) as refus, cx.begin_nested():
        _changer_le_statut(
            cx,
            entite=entite,
            cible=cible,
            acteur=acteur,
            nouveau_statut="intercontract",
            instant=ANCRAGE + 30 * JOUR,
        )
    assert refus.value.code == CODE_AUCUN_MODELE_PUBLIE
    assert refus.value.statut == 422

    #  RIEN n'a subsiste de la transaction annulee : ni le changement de
    #  statut, ni la cloture de l'ancienne instance — cahier ligne 1057.
    courant = _statut_courant(cx, cible)
    assert courant["status"] == "mission", "le changement de statut est annule aussi"
    assert courant["ends_at"] is None
    ligne = _lire_instance(cx, ancienne_id)
    assert ligne["state"] == "active", "l'ancienne instance n'a PAS ete clôturee"
    assert ligne["replaced_by_instance_id"] is None


# ===========================================================================
#  Critere de sortie n°3 : la progression de la NOUVELLE instance reflete
#  IMMEDIATEMENT les taches retenues — jamais une valeur stockee.
# ===========================================================================


@pytest.mark.integration
def test_la_progression_de_la_nouvelle_instance_reflete_les_taches_retenues(
    cx: Connection,
) -> None:
    entite = _entite(cx, "T10-PROGRESSION")
    acteur = _personne(cx, "t10-progression-a@exalt-company.com")
    personne = _personne(cx, "t10-progression-c@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _statut_initial(
        cx, cible, entite, statut="mission", client=_client(cx, "T10-PROGRESSION-CL", entite)
    )

    commune = _tache_de_reference(cx, entite, "T10-PROGRESSION-COMMUNE")
    nouvelle_seulement = _tache_de_reference(cx, entite, "T10-PROGRESSION-NOUVELLE")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-PROGRESSION-MISSION",
        target_status="mission",
        taches=[(commune, 3, None)],
    )
    _modele_publie(
        cx,
        entite,
        acteur,
        name="T10-PROGRESSION-INTER",
        target_status="intercontract",
        taches=[(commune, 5, None), (nouvelle_seulement, 7, None)],
    )

    ancienne = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=cible,
        cible=Appartenance(person_id=personne, arrival_date=ANCRAGE.date()),
        acteur=acteur,
        instant=ANCRAGE + JOUR,
    )
    assert ancienne.instance is not None
    cx.execute(
        text(
            "UPDATE onboarding_instance_task SET state = 'completed', completed_at = :i, "
            "completed_by_person_id = :p WHERE id = :t"
        ),
        {"i": ANCRAGE + 2 * JOUR, "p": acteur, "t": ancienne.taches[0].id},
    )

    _changer_le_statut(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        nouveau_statut="intercontract",
        instant=ANCRAGE + 30 * JOUR,
    )

    parcours = lire_le_parcours(cx, entite=entite, appartenance=cible)
    assert parcours.instance is not None
    assert parcours.instance.state == "active"
    assert parcours.progression is not None
    assert parcours.progression.taches_obligatoires_totales == 2
    assert parcours.progression.taches_obligatoires_terminees == 1, (
        "la tache commune retenue compte IMMEDIATEMENT, sans recalcul stocke"
    )
