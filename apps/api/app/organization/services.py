"""Services transactionnels de l'organisation — modele §25.4.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`.

CE SERVICE REFERME LA BOUCLE DE `DEC-514`

  Le modele §8.4 ecrit : « un DG recoit **automatiquement** une responsabilite DSM
  dans la meme transaction que son attribution de categorie ». `T10` a pose
  l'IMPLICATION en base -- le declencheur `dg_implique_dsm_local` refuse une
  categorie `dg` sans responsabilite `DSM` active dans la meme entite -- et a
  laisse l'ACTION au service, pour un motif precis :

    `assigned_by_person_id` est `NOT NULL`, et **un declencheur ne sait pas qui
    attribue**. Inventer un attributeur -- la personne elle-meme, un identifiant
    technique -- fabriquerait une trace d'audit FAUSSE, ce qui est pire qu'une
    trace absente. La matrice §5.1 exige que les interventions sensibles soient
    auditees.

  Un service, lui, connait l'auteur : il le recoit. **Il SATISFAIT l'invariant du
  declencheur, il ne s'y substitue pas** -- si le service etait contourne, la base
  refuserait toujours. C'est la doctrine de `DEC-498`.

L'ORDRE N'EST PAS UN DETAIL

  Le declencheur s'execute a l'`INSERT` comme a l'`UPDATE` de
  `entity_membership`. La responsabilite `DSM` doit donc exister **AVANT** que la
  categorie ne devienne `dg`. Un service qui ferait l'inverse echouerait, et
  c'est precisement ce qu'il evite a son appelant d'avoir a savoir.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CATEGORIE_DIRECTION_GENERALE = "dg"
RESPONSABILITE_DSM = "DSM"


class ErreurDeService(RuntimeError):
    """Une regle metier que le service porte, et que la base ne peut pas porter seule."""


def responsabilite_dsm_active(
    connexion: Connection, *, entite: uuid.UUID, personne: uuid.UUID
) -> uuid.UUID | None:
    """Rendre l'identifiant de la responsabilite `DSM` active de la personne, dans CETTE entite."""
    return connexion.execute(
        text(
            "SELECT id FROM framework_responsibility_assignment "
            "WHERE person_id = :personne AND entity_id = :entite "
            "  AND responsibility_type = :type_responsabilite AND ends_at IS NULL "
            "LIMIT 1"
        ),
        {
            "personne": personne,
            "entite": entite,
            "type_responsabilite": RESPONSABILITE_DSM,
        },
    ).scalar_one_or_none()


def attribuer_la_categorie_dg(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    attribue_par: uuid.UUID,
    debut: dt.datetime | None = None,
    motif: str | None = None,
) -> uuid.UUID:
    """Attribuer la categorie `dg` a une appartenance, en creant la responsabilite `DSM`.

    Rend l'identifiant de la responsabilite `DSM`, creee ou deja existante.

    `attribue_par` est **obligatoire** et n'a pas de defaut : c'est tout le motif
    pour lequel cette action est un service et non un declencheur. La matrice §8.4
    veut « ESM ou super-administrateur » ; **cette verification releve du LOT 3**,
    la base n'ayant aucune notion de l'appelant, et `QO-116` porte le sujet
    voisin du moindre privilege.
    """
    ligne = connexion.execute(
        text(
            "SELECT person_id, entity_id FROM entity_membership "
            "WHERE id = :appartenance AND entity_id = :entite"
        ),
        {"appartenance": appartenance, "entite": entite},
    ).one_or_none()
    if ligne is None:
        #  `None` couvre deux cas indistinguables a dessein : l'appartenance
        #  n'existe pas, ou elle est d'une AUTRE entite. Le §2.5 « refus par
        #  defaut » veut qu'on ne revele pas l'existence d'une ressource d'une
        #  autre entite -- meme raisonnement que `DepotLocal.obtenir`.
        message = f"appartenance {appartenance} inconnue dans l'entite {entite}"
        raise ErreurDeService(message)
    personne = ligne[0]

    existante = responsabilite_dsm_active(connexion, entite=entite, personne=personne)
    if existante is None:
        #  L'ORDRE EST IMPOSE PAR LE DECLENCHEUR : la responsabilite d'abord.
        existante = connexion.execute(
            text(
                "INSERT INTO framework_responsibility_assignment "
                "(person_id, entity_id, responsibility_type, assigned_by_person_id, "
                " starts_at, assignment_reason) "
                "VALUES (:personne, :entite, :type_responsabilite, :auteur, :debut, :motif) "
                "RETURNING id"
            ),
            {
                "personne": personne,
                "entite": entite,
                "type_responsabilite": RESPONSABILITE_DSM,
                "auteur": attribue_par,
                "debut": debut or dt.datetime.now(tz=dt.UTC),
                "motif": motif,
            },
        ).scalar_one()

    connexion.execute(
        text(
            "UPDATE entity_membership SET professional_category = :categorie, "
            "updated_by_person_id = :auteur, version = version + 1 "
            "WHERE id = :appartenance AND entity_id = :entite"
        ),
        {
            "categorie": CATEGORIE_DIRECTION_GENERALE,
            "auteur": attribue_par,
            "appartenance": appartenance,
            "entite": entite,
        },
    )
    return existante
