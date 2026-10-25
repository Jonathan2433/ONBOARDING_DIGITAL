"""Le manifeste declare-t-il les MEMES grilles de roles que le code ? — LOT 10, `T15`.

CE QUE CE FICHIER EPROUVE, ET POURQUOI IL EXISTE

  `T15` est le PREMIER ecran a consommer six grilles de roles posees par `T8`
  a `T14` sans jamais avoir eu de consommateur avant lui — meme situation que
  `test_contrat_roles_lot9.py` pour le back-office du LOT 9.

  Chaque grille est ici CONFRONTEE, DANS LES DEUX SENS, a la constante Python
  qu'elle doit refleter : le manifeste ne peut pas en declarer PLUS (un role
  qui ouvrirait un bouton que l'API refuse) ni MOINS (un role a qui on
  masquerait un bouton que l'API accorderait).
"""

from __future__ import annotations

import json
import pathlib

from app.audit.perimetre import (
    ROLES_D_EXPORT_DE_L_AUDIT,
    ROLES_DE_L_AUDIT,
    ROLES_DES_DETAILS_TECHNIQUES,
)
from app.permissions.services import RoleDeLaMatrice
from app.privacy.perimetre import ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD
from app.support.perimetre import ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS
from app.support.perimetre_alertes import ROLES_DE_TRAITEMENT_DES_ALERTES

MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def _manifeste() -> dict[str, object]:
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    return json.loads(chemin.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _declares(manifeste: dict[str, object], cle: str) -> set[RoleDeLaMatrice]:
    codes = manifeste[cle]
    assert codes, f"le manifeste ne declare aucun role pour « {cle} »"
    assert isinstance(codes, list)
    return {RoleDeLaMatrice(code) for code in codes}


def test_rolesDeLAudit_EST_LA_MEME_GRILLE_QUE_ROLES_DE_L_AUDIT() -> None:
    """`T8` — le journal d'audit en lecture, matrice §16. EMP/NEW/ANON a tiret."""
    assert _declares(_manifeste(), "rolesDeLAudit") == ROLES_DE_L_AUDIT


def test_rolesDetailsTechniquesDeLAudit_EST_LA_MEME_GRILLE_QUE_LE_SERVICE() -> None:
    """`T8` — masque `resource_reference`/`correlation_token` hors ADM-E/SUPER."""
    assert _declares(_manifeste(), "rolesDetailsTechniquesDeLAudit") == ROLES_DES_DETAILS_TECHNIQUES


def test_rolesExportDeLAudit_EST_LA_MEME_GRILLE_QUE_ROLES_D_EXPORT_DE_L_AUDIT() -> None:
    """`T9` — l'export CSV du journal.

    **DECLAREE SEPAREMENT DE `rolesDetailsTechniquesDeLAudit`** : les deux
    portent aujourd'hui les memes deux roles, et c'est une coincidence de
    cette matrice (deux lignes distinctes du §16), pas une identite
    conceptuelle — les fusionner ferait suivre l'une quand la matrice change
    l'autre, en silence (§7.27).
    """
    manifeste = _manifeste()
    assert _declares(manifeste, "rolesExportDeLAudit") == ROLES_D_EXPORT_DE_L_AUDIT
    assert "rolesDetailsTechniquesDeLAudit" in manifeste
    assert "rolesExportDeLAudit" in manifeste


def test_rolesTraitementDesSignalements_EST_LA_MEME_GRILLE_QUE_LE_SERVICE() -> None:
    """`T12` — modifier l'état d'un signalement, matrice §17.

    Deux rôles seulement : la LECTURE se dégrade jusqu'à `Soi` (aucun rôle
    refusé), mais cette grille-ci ne garde que l'écriture.
    """
    assert (
        _declares(_manifeste(), "rolesTraitementDesSignalements")
        == ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS
    )


def test_rolesTraitementDesAlertes_EST_LA_MEME_GRILLE_QUE_LE_SERVICE() -> None:
    """`T13` — acquitter, commenter, résoudre une alerte, matrice §17.

    L'ESM (périmètre `LIMITE`) lit mais n'écrit jamais : cette grille ne
    porte donc que `ADM-E`/`SUPER`, à la différence de la lecture qui admet
    aussi l'ESM.
    """
    assert _declares(_manifeste(), "rolesTraitementDesAlertes") == ROLES_DE_TRAITEMENT_DES_ALERTES


def test_rolesTraitementDesDemandesRGPD_EST_LA_MEME_GRILLE_QUE_LE_SERVICE() -> None:
    """`T14` — réceptionner, vérifier, clôturer une demande RGPD.

    Une seule grille, garde les six routes (lecture et écriture confondues) :
    aucun plancher `Soi` ni `Limité`.
    """
    assert (
        _declares(_manifeste(), "rolesTraitementDesDemandesRGPD")
        == ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD
    )
