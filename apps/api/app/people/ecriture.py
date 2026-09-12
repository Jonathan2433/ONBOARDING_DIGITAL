"""Ecrire les donnees organisationnelles — cahier §10.2, §18.4, §23.4. LOT 5 `T7`.

**LA PREMIERE ECRITURE METIER DU PROJET.** Mesure du 08/09/2026 : hors de
`app/auth/`, les onze routes du depot etaient toutes des `GET`.

CLORE PUIS OUVRIR, JAMAIS ECRASER

  §23.4 : « la suppression d'un role actif **CLOTURE** la relation au lieu
  d'effacer l'historique ». Quatre des six champs du §10.2 sont portes par des
  relations HISTORISEES du §25.2 -- metier, statut, client, DSM, cercle principal
  -- et une modification y ferme la periode courante a l'instant `T` puis en
  ouvre une nouvelle a partir de `T`.

  **CELA NE PEUT PAS DERAPER EN SILENCE, ET C'EST STRUCTUREL.** `period` est un
  `tstzrange(starts_at, ends_at)`, donc en bornes `[)` : fermer a `T` et ouvrir a
  `T` ne se chevauchent pas. Et chaque table porte une contrainte d'EXCLUSION
  `(cle WITH =, period WITH &&)` : toute ecriture qui chevaucherait est REFUSEE
  PAR LA BASE. Le critere de sortie n°6 du lot -- « les affectations
  structurantes ne sont jamais ecrasees » -- n'est donc pas une promesse de ce
  module, c'est une propriete du schema. Ce module ne peut que s'y conformer ou
  echouer bruyamment.

  Consequence a connaitre : si une periode FUTURE existe, `period @> :instant`
  n'en ferme aucune et l'insertion chevaucherait -- la base refuse, et ce module
  traduit ce refus en `409`. Un test l'exerce.

STATUT ET CLIENT SONT UNE SEULE PERIODE

  Ils vivent sur la meme ligne de `professional_status_assignment`, et un `CHECK`
  les lie par une BICONDITIONNELLE mesuree :
  `(status = 'mission') = (client_id IS NOT NULL)`. Le §30.5 est donc structurel
  dans les DEUX sens -- une mission sans client est refusee, un intercontrat avec
  client aussi.

  **Une demande qui ne porte QUE l'un des deux doit donc reporter la valeur
  COURANTE de l'autre** dans la ligne nouvelle. L'oublier ferait echouer la
  biconditionnelle sur une demande legitime.

LA CONCURRENCE OPTIMISTE EST ANCREE SUR `entity_membership.version`

  §18.4, litteralement : « les modifications sensibles utilisent une concurrence
  optimiste. Une version obsolete produit une reponse HTTP 409 **sans ecrasement
  silencieux** ».

  L'ancre est la version de l'appartenance, RACINE de l'agregat, et non celle de
  chaque table filles : une modification du metier et une modification du DSM
  faites en meme temps sur le meme profil doivent entrer en conflit, or elles ne
  touchent pas la meme ligne fille. Ancrer sur les filles laisserait passer deux
  editeurs qui se croient seuls.

`None` DE VALEUR N'EST PAS UN CHAMP ABSENT

  Un consultant en intercontrat n'a PAS de client : `client = null` est une
  valeur legitime, distincte de « je ne touche pas au client ». La demande porte
  donc les champs PRESENTS, et non un objet dont les absents valent `None`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any, Final

from fastapi import status
from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DataError, IntegrityError

from app.organization.modeles import TypeAppartenanceCercle
from app.people.modeles import SituationProfessionnelle
from app.permissions.perimetre import ChampOrganisationnel, PerimetreDEcriture
from app.shared.errors import ErreurApplicative

CODE_CHAMP_HORS_PERIMETRE: Final = "champ_hors_perimetre"
MESSAGE_CHAMP_HORS_PERIMETRE: Final = (
    "Votre perimetre ne vous permet pas de modifier ce champ pour ce collaborateur."
)

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "Ce profil a change depuis votre lecture. Rechargez-le avant de le modifier."
)

CODE_PERIODE_INCOMPATIBLE: Final = "periode_incompatible"
MESSAGE_PERIODE_INCOMPATIBLE: Final = (
    "Une affectation posterieure existe deja sur ce profil : la modification a ete refusee "
    "plutot que d'ecraser l'historique."
)

CODE_ETAT_INCOMPATIBLE: Final = "etat_incompatible"
MESSAGE_ETAT_INCOMPATIBLE: Final = "l'etat actuel des donnees ne permet pas cette operation"

CODE_VALEUR_REFUSEE: Final = "valeur_refusee"
MESSAGE_VALEUR_REFUSEE: Final = (
    "La combinaison demandee est refusee : un statut `mission` exige un client, "
    "un statut `intercontract` n'en accepte aucun."
)


@dataclasses.dataclass(frozen=True, slots=True)
class Modification:
    """Ce qui a REELLEMENT change, et la version nouvelle.

    **`champs` PORTE LES CHAMPS EFFECTIVEMENT ECRITS**, qui peuvent etre moins
    nombreux que ceux demandes : une demande qui redonne la valeur courante ne
    ferme aucune periode. Le distinguer permet a l'appelant de le dire, et
    empeche l'historique de se remplir de periodes d'une microseconde.
    """

    version: int
    champs: frozenset[ChampOrganisationnel]


#  L'appartenance et l'etat courant des quatre relations, en UNE requete. Les
#  `LEFT JOIN` sont surs : les contraintes d'exclusion interdisent deux lignes
#  actives sur la meme cle, ce que `T4` a deja mesure et fige par un test.
_ETAT_COURANT: Final[str] = """
SELECT em.version, em.arrival_date,
       mja.id AS metier_id, mja.job_catalog_id,
       ps.id AS statut_id, ps.status, ps.client_id,
       da.id AS dsm_id, da.dsm_person_id,
       cm.id AS cercle_id, cm.circle_id
FROM entity_membership em
LEFT JOIN membership_job_assignment mja
  ON mja.entity_membership_id = em.id AND mja.entity_id = em.entity_id
 AND mja.archived_at IS NULL AND mja.period @> :instant_mja
LEFT JOIN professional_status_assignment ps
  ON ps.entity_membership_id = em.id AND ps.entity_id = em.entity_id
 AND ps.archived_at IS NULL AND ps.period @> :instant_ps
LEFT JOIN dsm_assignment da
  ON da.consultant_membership_id = em.id AND da.entity_id = em.entity_id
 AND da.archived_at IS NULL AND da.period @> :instant_da
LEFT JOIN circle_membership cm
  ON cm.entity_membership_id = em.id AND cm.entity_id = em.entity_id
 AND cm.membership_type = :type_principal
 AND cm.archived_at IS NULL AND cm.period @> :instant_cm
WHERE em.id = :cible AND em.entity_id = :entite
FOR UPDATE OF em
"""

#  Fermer la periode COURANTE d'une relation. `period @> :instant` et non
#  `ends_at IS NULL` : une periode future ne doit PAS etre fermee ici -- la
#  fermer reecrirait un avenir decide ailleurs. Si rien n'est ferme et qu'une
#  periode future existe, l'insertion qui suit chevauchera et la BASE refusera.
_FERMER: Final[str] = """
UPDATE {table} SET ends_at = :instant,
                   updated_at = :instant,
                   updated_by_person_id = :acteur,
                   version = version + 1
WHERE id = :ligne
"""


def _valeur_presente(
    demande: Mapping[ChampOrganisationnel, Any], champ: ChampOrganisationnel
) -> bool:
    return champ in demande


def _fermer(
    connexion: Connection, table: str, ligne: uuid.UUID, acteur: uuid.UUID, instant: dt.datetime
) -> None:
    #  Le nom de table vient d'un LITTERAL de ce module, jamais d'un appelant :
    #  les quatre valeurs sont ecrites en clair dans les fonctions ci-dessous.
    #
    #  **AUCUNE SUPPRESSION DE REGLE ICI, ET C'EST MESURE.** J'avais pose une
    #  directive d'exemption pour `S608` par precaution ; `ruff` a repondu
    #  `RUF100 unused` -- la regle ne tire pas sur ce gabarit. Une suppression
    #  qu'on n'a pas verifiee necessaire apprend a en poser d'autres, et le jour
    #  ou `S608` tirerait vraiment ailleurs, personne ne saurait laquelle est
    #  justifiee.
    #
    #  Et la premiere redaction de ce commentaire ECRIVAIT la directive en clair
    #  pour l'expliquer : `ruff` l'a lue comme une directive et a rendu
    #  « Invalid directive ». C'est le defaut de `T11` du LOT 2 -- un garde-fou
    #  qui se declenche sur le commentaire enoncant sa propre regle -- pour la
    #  quatrieme fois dans ce projet. On nomme la regle, on ne l'ecrit pas.
    connexion.execute(
        text(_FERMER.format(table=table)),
        {"ligne": ligne, "acteur": acteur, "instant": instant},
    )


def modifier_les_donnees_organisationnelles(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    demande: Mapping[ChampOrganisationnel, Any],
    perimetre: PerimetreDEcriture,
    instant: dt.datetime,
) -> Modification:
    """Ecrire les champs demandes, en closant puis ouvrant les periodes.

    Leve `ErreurApplicative` avec le format du §18.3 : `403` hors perimetre,
    `409` version obsolete ou periode incompatible, `422` valeur refusee.
    """
    #  1. LE PERIMETRE D'ABORD. Un champ hors perimetre est refuse AVANT toute
    #     lecture d'etat : le §2.5 « refus par defaut » ne veut pas qu'on
    #     travaille sur une ressource qu'on n'a pas le droit de modifier.
    hors = frozenset(demande) - perimetre.champs
    if hors:
        raise ErreurApplicative(
            code=CODE_CHAMP_HORS_PERIMETRE,
            message=MESSAGE_CHAMP_HORS_PERIMETRE,
            statut=status.HTTP_403_FORBIDDEN,
            #  Les champs refuses sont NOMMES : ce n'est pas une fuite, l'appelant
            #  vient de les envoyer. Taire lesquels l'obligerait a deviner.
            details={"champs": sorted(c.value for c in hors)},
        )

    etat = (
        connexion.execute(
            text(_ETAT_COURANT),
            {
                "cible": cible,
                "entite": entite,
                "type_principal": TypeAppartenanceCercle.PRINCIPAL.value,
                "instant_mja": instant,
                "instant_ps": instant,
                "instant_da": instant,
                "instant_cm": instant,
            },
        )
        .mappings()
        .first()
    )
    if etat is None:
        #  Le perimetre a deja exige une appartenance occupante de cette entite :
        #  arriver ici veut dire qu'elle a disparu entre les deux, ce que
        #  `FOR UPDATE` rend tres improbable. Un `409` le dit sans inventer.
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
        )

    #  2. LA CONCURRENCE OPTIMISTE. §18.4 : « sans ecrasement silencieux ».
    if etat["version"] != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": etat["version"]},
        )

    ecrits: set[ChampOrganisationnel] = set()
    try:
        ecrits |= _ecrire_la_date(
            connexion, etat, demande, cible=cible, acteur=acteur, instant=instant
        )
        ecrits |= _ecrire_le_metier(
            connexion, etat, demande, entite=entite, cible=cible, acteur=acteur, instant=instant
        )
        ecrits |= _ecrire_le_statut(
            connexion, etat, demande, entite=entite, cible=cible, acteur=acteur, instant=instant
        )
        ecrits |= _ecrire_le_dsm(
            connexion, etat, demande, entite=entite, cible=cible, acteur=acteur, instant=instant
        )
        ecrits |= _ecrire_le_cercle(
            connexion, etat, demande, entite=entite, cible=cible, acteur=acteur, instant=instant
        )
    except (IntegrityError, DataError) as erreur:
        #  **LES DEUX, ET NON `DatabaseError`.** Ce dernier couvre aussi
        #  `OperationalError` -- une panne de connexion -- qu'il ne faut
        #  surtout pas traduire en refus metier : elle deviendrait un `422`
        #  silencieux au lieu d'une alerte.
        raise traduire_un_refus_de_la_base(erreur) from erreur

    #  3. LA VERSION DE LA RACINE MONTE DES QU'UN CHAMP A CHANGE, et pas avant :
    #     une demande sans effet ne doit pas faire echouer la prochaine.
    version = int(etat["version"])
    if ecrits:
        version = int(
            connexion.execute(
                text(
                    "UPDATE entity_membership "
                    "SET version = version + 1, updated_at = :instant, "
                    "    updated_by_person_id = :acteur "
                    "WHERE id = :cible AND entity_id = :entite RETURNING version"
                ),
                {"cible": cible, "entite": entite, "acteur": acteur, "instant": instant},
            ).scalar_one()
        )
    return Modification(version=version, champs=frozenset(ecrits))


def traduire_un_refus_de_la_base(erreur: IntegrityError | DataError) -> ErreurApplicative:
    """Traduire un refus de la BASE en refus du §18.3, sans le masquer.

    **DEUX REFUS DISTINCTS, DEUX CODES DISTINCTS**, et le discriminant est le
    type d'exception de psycopg, jamais le texte du message -- un message est
    localise et change de version en version.
    """
    cause = erreur.orig
    if isinstance(cause, erreurs_psycopg.ExclusionViolation):
        return ErreurApplicative(
            code=CODE_PERIODE_INCOMPATIBLE,
            message=MESSAGE_PERIODE_INCOMPATIBLE,
            statut=status.HTTP_409_CONFLICT,
        )
    if isinstance(cause, erreurs_psycopg.CheckViolation):
        return ErreurApplicative(
            code=CODE_VALEUR_REFUSEE,
            message=MESSAGE_VALEUR_REFUSEE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    #  **TROISIEME REFUS, AJOUTE PAR `T8` DU LOT 5.** `T7` n'en rencontrait
    #  aucun : les cinq relations qu'il ecrit sont gardees par des EXCLUSIONS.
    #  La restauration, elle, repose sur deux index UNIQUES -- une seule
    #  appartenance occupante par personne (§25.1), et le couple `(id, entity_id)`
    #  du §25.3 -- et sans cette branche un refus legitime de la base sortait en
    #  **500**. Le message ne nomme PAS la cause : elle porterait sur une AUTRE
    #  entite, ce que le §5.1 ne laisse pas lire. La cause reste au journal de
    #  l'appelant, qui la connait.
    if isinstance(cause, erreurs_psycopg.UniqueViolation):
        return ErreurApplicative(
            code=CODE_ETAT_INCOMPATIBLE,
            message=MESSAGE_ETAT_INCOMPATIBLE,
            statut=status.HTTP_409_CONFLICT,
        )
    #  **QUATRIEME REFUS, ET C'ETAIT UN 500 DEPUIS `T7`.** Une colonne GENEREE
    #  peut refuser une valeur **avant** toute contrainte : `period` est
    #  `daterange(arrival_date, departure_date)`, et une arrivee posterieure au
    #  depart rend « range lower bound must be less than or equal to range upper
    #  bound » -- une `DataException`, donc un `DataError` de SQLAlchemy, que
    #  `except IntegrityError` NE VOIT PAS.
    #
    #  Mesure du 10/09/2026 : le `PATCH` de `T7` sortait en **500** sur une
    #  `date_d_arrivee` posterieure a une `departure_date` existante -- un etat
    #  atteignable, `depart_date_si_departed` ne contraignant que `departed`.
    #  C'est `T8` qui l'a trouve, en cherchant pourquoi son propre refus de date
    #  n'etait pas traduit. `ECART-058`.
    #
    #  `422` et non `409` : c'est la VALEUR envoyee qui est refusee, comme pour
    #  une `CheckViolation`, et non un conflit avec un etat concurrent.
    if isinstance(cause, erreurs_psycopg.DataException):
        return ErreurApplicative(
            code=CODE_VALEUR_REFUSEE,
            message=MESSAGE_VALEUR_REFUSEE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    raise erreur


def _ecrire_la_date(
    connexion: Connection,
    etat: RowMapping,
    demande: Mapping[ChampOrganisationnel, Any],
    *,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> frozenset[ChampOrganisationnel]:
    """La date d'arrivee est une COLONNE, pas une relation historisee.

    Le §10.2 la range avec les cinq autres, mais le §25.2 ne l'historise pas :
    elle vit sur `entity_membership`. Une modification est donc un `UPDATE`, et
    l'historique de la date d'arrivee n'existe pas -- ce que le corpus n'exige
    nulle part.
    """
    champ = ChampOrganisationnel.DATE_D_ARRIVEE
    if not _valeur_presente(demande, champ) or demande[champ] == etat["arrival_date"]:
        return frozenset()
    connexion.execute(
        text(
            "UPDATE entity_membership SET arrival_date = :valeur, updated_at = :instant, "
            "updated_by_person_id = :acteur WHERE id = :cible"
        ),
        {"valeur": demande[champ], "cible": cible, "acteur": acteur, "instant": instant},
    )
    return frozenset({champ})


def _ecrire_le_metier(
    connexion: Connection,
    etat: RowMapping,
    demande: Mapping[ChampOrganisationnel, Any],
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> frozenset[ChampOrganisationnel]:
    champ = ChampOrganisationnel.METIER
    if not _valeur_presente(demande, champ) or demande[champ] == etat["job_catalog_id"]:
        return frozenset()
    if etat["metier_id"] is not None:
        _fermer(connexion, "membership_job_assignment", etat["metier_id"], acteur, instant)
    connexion.execute(
        text(
            "INSERT INTO membership_job_assignment "
            "(entity_membership_id, entity_id, job_catalog_id, starts_at, created_by_person_id) "
            "VALUES (:cible, :entite, :valeur, :instant, :acteur)"
        ),
        {
            "cible": cible,
            "entite": entite,
            "valeur": demande[champ],
            "instant": instant,
            "acteur": acteur,
        },
    )
    return frozenset({champ})


def _ecrire_le_statut(
    connexion: Connection,
    etat: RowMapping,
    demande: Mapping[ChampOrganisationnel, Any],
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> frozenset[ChampOrganisationnel]:
    """Statut et client : UNE seule periode, donc un seul cloture-ouvre.

    **LA VALEUR NON DEMANDEE EST REPORTEE, ET C'EST NECESSAIRE.** Le `CHECK`
    `(status = 'mission') = (client_id IS NOT NULL)` lie les deux : une demande
    qui ne porte que le client doit ecrire la ligne nouvelle avec le statut
    COURANT, sinon la biconditionnelle refuse une demande legitime.
    """
    demandes = {ChampOrganisationnel.STATUT, ChampOrganisationnel.CLIENT} & frozenset(demande)
    if not demandes:
        return frozenset()

    statut = demande.get(ChampOrganisationnel.STATUT, etat["status"])
    client = demande.get(ChampOrganisationnel.CLIENT, etat["client_id"])
    #  **UN INTERCONTRAT PERD SON CLIENT, ET LE DIRE VAUT MIEUX QUE DE LE
    #  REFUSER.** Passer de `mission` a `intercontract` sans nommer le client
    #  laisserait le client courant reporte, et le `CHECK` refuserait -- alors que
    #  la demande est parfaitement claire. Le §30.5 dit qu'un intercontrat n'a pas
    #  de client : c'est une consequence du statut, pas une saisie de l'appelant.
    if statut == SituationProfessionnelle.INTERCONTRACT.value:
        client = None
    if statut == etat["status"] and client == etat["client_id"]:
        return frozenset()

    if etat["statut_id"] is not None:
        _fermer(connexion, "professional_status_assignment", etat["statut_id"], acteur, instant)
    connexion.execute(
        text(
            "INSERT INTO professional_status_assignment "
            "(entity_membership_id, entity_id, status, client_id, starts_at, created_by_person_id) "
            "VALUES (:cible, :entite, :statut, :client, :instant, :acteur)"
        ),
        {
            "cible": cible,
            "entite": entite,
            "statut": statut,
            "client": client,
            "instant": instant,
            "acteur": acteur,
        },
    )
    return frozenset(demandes)


def _ecrire_le_dsm(
    connexion: Connection,
    etat: RowMapping,
    demande: Mapping[ChampOrganisationnel, Any],
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> frozenset[ChampOrganisationnel]:
    champ = ChampOrganisationnel.DSM
    if not _valeur_presente(demande, champ) or demande[champ] == etat["dsm_person_id"]:
        return frozenset()
    if etat["dsm_id"] is not None:
        _fermer(connexion, "dsm_assignment", etat["dsm_id"], acteur, instant)
    connexion.execute(
        text(
            "INSERT INTO dsm_assignment "
            "(consultant_membership_id, entity_id, dsm_person_id, starts_at, created_by_person_id) "
            "VALUES (:cible, :entite, :valeur, :instant, :acteur)"
        ),
        {
            "cible": cible,
            "entite": entite,
            "valeur": demande[champ],
            "instant": instant,
            "acteur": acteur,
        },
    )
    return frozenset({champ})


def _ecrire_le_cercle(
    connexion: Connection,
    etat: RowMapping,
    demande: Mapping[ChampOrganisationnel, Any],
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> frozenset[ChampOrganisationnel]:
    """Le cercle PRINCIPAL seulement : les secondaires sont une autre ligne du §6.1."""
    champ = ChampOrganisationnel.CERCLE_PRINCIPAL
    if not _valeur_presente(demande, champ) or demande[champ] == etat["circle_id"]:
        return frozenset()
    if etat["cercle_id"] is not None:
        _fermer(connexion, "circle_membership", etat["cercle_id"], acteur, instant)
    connexion.execute(
        text(
            "INSERT INTO circle_membership "
            "(entity_membership_id, entity_id, circle_id, membership_type, starts_at, "
            " created_by_person_id) "
            "VALUES (:cible, :entite, :valeur, :type_principal, :instant, :acteur)"
        ),
        {
            "cible": cible,
            "entite": entite,
            "valeur": demande[champ],
            "type_principal": TypeAppartenanceCercle.PRINCIPAL.value,
            "instant": instant,
            "acteur": acteur,
        },
    )
    return frozenset({champ})
