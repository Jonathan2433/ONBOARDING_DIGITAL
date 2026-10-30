"""Schema de l'audit, des alertes, du support et du RGPD — LOT 10, `T1`, modele §21/§22.3.

Prouve l'arbitrage pose avant tout code : l'ecriture d'audit reste SYNCHRONE
(`ARB-DATA-005`, `§30.20`). `async_job` existe desormais — LOT 11, `T1` —
mais cela ne retrofite PAS `export_request.job_id`, que le LOT 10 a
explicitement retiree (defaut trouve par `make isolation-check`, documente en
tete de `app/audit/modeles.py`) : l'export CSV de l'audit (`T9`) reste
synchrone, et rien dans ce lot n'a jamais eu besoin de cette colonne.
"""

from __future__ import annotations

from app.audit import (
    ETATS_ALERTE,
    ETATS_SIGNALEMENT,
    SEVERITES_ALERTE,
    TYPES_DE_DEMANDE_RGPD,
)
from app.modeles import metadonnees


def test_les_six_tables_du_lot_existent() -> None:
    for table in (
        "audit_event",
        "operational_alert",
        "alert_comment",
        "bug_report",
        "export_request",
        "data_subject_request",
    ):
        assert table in metadonnees.tables


def test_l_export_de_l_audit_n_a_jamais_eu_besoin_de_job_id() -> None:
    """`async_job` existe depuis LOT 11 `T1` ; `export_request` n'a jamais porte `job_id`.

    Les deux faits sont INDEPENDANTS : l'export CSV de l'audit (`T9`) est
    synchrone par construction (voir `app/audit/export.py`), pas parce que
    `async_job` manquait.
    """

    assert "async_job" in metadonnees.tables
    assert "job_id" not in metadonnees.tables["export_request"].columns


def test_audit_event_n_a_ni_resource_id_ni_correlation_id() -> None:
    """Defaut trouve par `make isolation-check`, corrige avant commit.

    `resource_id` et `correlation_id` auraient ete lus comme des references
    sans cle etrangere. Renommes `resource_reference`/`correlation_token`,
    aucune des deux formes `_id` ne doit reapparaitre.
    """

    colonnes = metadonnees.tables["audit_event"].columns
    assert "resource_id" not in colonnes
    assert "correlation_id" not in colonnes
    assert "resource_reference" in colonnes
    assert "correlation_token" in colonnes


def test_bug_report_n_a_pas_de_correlation_id() -> None:
    colonnes = metadonnees.tables["bug_report"].columns
    assert "correlation_id" not in colonnes
    assert "correlation_token" in colonnes


def test_les_enumerations_fermees_correspondent_au_modele() -> None:
    assert set(SEVERITES_ALERTE) == {"INFO", "WARNING", "ERROR", "CRITICAL"}
    assert set(ETATS_ALERTE) == {"open", "acknowledged", "resolved"}
    assert set(ETATS_SIGNALEMENT) == {"new", "investigating", "fixed", "rejected"}
    assert set(TYPES_DE_DEMANDE_RGPD) == {"access", "rectification", "erasure", "objection"}


def test_audit_event_entity_id_est_nullable_les_cinq_autres_tables_n_en_ont_pas() -> None:
    """§21.1 : evenement global. Les quatre autres tables globales n'en portent aucun."""

    assert metadonnees.tables["audit_event"].columns["entity_id"].nullable is True
    for table in (
        "operational_alert",
        "alert_comment",
        "export_request",
        "data_subject_request",
    ):
        assert "entity_id" not in metadonnees.tables[table].columns
    #  SEULE table locale de ce module : `entity_id` NOT NULL.
    assert metadonnees.tables["bug_report"].columns["entity_id"].nullable is False
