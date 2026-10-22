"""Réceptionner, vérifier, clôturer une demande de droit RGPD — `T14`.

LOT 10, sous-étape `T14`, story `MVP-L10-US008`.

DEUX ÉTATS SEULEMENT, VOCABULAIRE OUVERT — `data_subject_request.state` NE
PORTE AUCUNE CONTRAINTE `contrainte_enumeration` (voir `app/audit/modeles.py`,
qui dit explicitement : « ni le §22.3 ni aucune autre section n'en donne le
vocabulaire. Chaîne non vide »). Les deux valeurs ci-dessous (`ETAT_RECU`,
`ETAT_CLOS`) sont un choix de CE module, jamais imposé par une contrainte de
base — à la différence d'`operational_alert.state`, fermé par le modèle.

  Le backlog `US008` liste cinq preoccupations — réception, vérification
  d'identité, export structuré, actions, délais, clôture — mais UNE SEULE
  d'entre elles ferme le dossier (la clôture). Les autres sont des colonnes
  ou des actions ORTHOGONALES, jamais un état de plus (même lecture que
  « commentée » pour les alertes, `T13`) :

    - vérification d'identité     -> `identity_verified` (booléen), bascule
                                      par sa propre action, sans changer l'état ;
    - export structuré / actions  -> le texte libre `response`, écrit à la
                                      clôture (voir plus bas) ; les ACTIONS
                                      concrètes sur les données de la personne
                                      (rectification, effacement d'un champ...)
                                      réutilisent les routes DÉJÀ auditées des
                                      autres domaines (`T3`-`T7`) — ce module
                                      ne réécrit RIEN de ces écritures, il tient
                                      le DOSSIER qui les accompagne ;
    - délais                      -> `due_at`, calculé à la réception et jamais
                                      modifié, voir `DELAI_DE_REPONSE_RGPD`.

  Inventer des états intermédiaires (« en_cours », « en_verification »...) que
  rien ne nomme serait le défaut §6.5 — un diagramme que le corpus ne porte
  pas. Une seule transition existe : `ETAT_RECU` -> `ETAT_CLOS`.

`due_at` : LE DÉLAI D'UN MOIS N'EST PAS UNE RÈGLE MÉTIER À ARBITRER

  Le RGPD (article 12§3) fixe UN MOIS pour répondre à une demande de droit,
  extensible dans des cas complexes que ce lot ne construit pas (aucune
  mention dans le cahier §21.5). C'est un FAIT LÉGAL externe, pas une
  décision de Jonathan — même nature que la rétention d'un an de l'audit
  (`app.audit.services.DUREE_DE_RETENTION`), elle aussi un défaut documenté
  plutôt qu'une question posée.

« L'EXPORT STRUCTURÉ » EST UN TEXTE, JAMAIS UN FICHIER GÉNÉRÉ

  Le modèle §22.3 ne pose NI colonne média, NI référence d'objet pour
  `data_subject_request` — à la différence d'`export_request` (modèle
  §21.5, `T9`), qui en porte une. La seule colonne disponible pour consigner
  ce qui a été remis à la personne est `response` (texte libre), écrite à la
  clôture : construire un mécanisme de génération de fichier ici inventerait
  une infrastructure qu'aucune colonne ne prévoit (§6.5) — le responsable
  RGPD y résume ce qui a été transmis, hors ligne ou par un canal propre.

AUCUN MOTIF DUPLIQUÉ DANS `audit_event.reason`

  `response` est LA SEULE trace du contenu de la réponse — jamais recopiée
  dans `audit_event.reason`, même discipline que `alert_comment` pour les
  alertes (`T13`) : deux sources pour la même donnée divergeraient au premier
  correctif (§7.27).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any, Final

from fastapi import status
from sqlalchemy import text

from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CODE_DEMANDE_INTROUVABLE: Final = "demande_rgpd_introuvable"
MESSAGE_DEMANDE_INTROUVABLE: Final = "Aucune demande de droit ne correspond a cet identifiant."

CODE_PERSONNE_CONCERNEE_INTROUVABLE: Final = "personne_concernee_introuvable"
MESSAGE_PERSONNE_CONCERNEE_INTROUVABLE: Final = (
    "La personne designee comme personne concernee n'existe pas."
)

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "la version lue est perimee — cahier §18.4, aucun ecrasement silencieux"
)

CODE_TRANSITION_INVALIDE: Final = "transition_invalide"
MESSAGE_TRANSITION_INVALIDE: Final = "Cette demande est deja cloturee."

#  Vocabulaire OUVERT — voir l'en-tete du module.
ETAT_RECU: Final = "received"
ETAT_CLOS: Final = "closed"

#  RGPD, article 12§3 : un mois pour repondre — voir l'en-tete du module.
DELAI_DE_REPONSE_RGPD: Final = dt.timedelta(days=30)

_ACTION_CODE_DEMANDE_RECEPTIONNEE: Final = "demande_rgpd_receptionnee"
_ACTION_CODE_IDENTITE_VERIFIEE: Final = "demande_rgpd_identite_verifiee"
_ACTION_CODE_DEMANDE_CLOTUREE: Final = "demande_rgpd_cloturee"
_RESOURCE_TYPE_DEMANDE_RGPD: Final = "data_subject_request"


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDeDemandeRGPD:
    """Une ligne de `data_subject_request` — modèle §22.3."""

    id: uuid.UUID
    data_subject_person_id: uuid.UUID
    request_type: str
    channel: str
    received_at: dt.datetime
    identity_verified: bool
    responsible_person_id: uuid.UUID
    due_at: dt.datetime
    state: str
    response: str | None
    closed_at: dt.datetime | None
    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeDemandesRGPD:
    """Une page de demandes, et le total de la population."""

    demandes: list[LigneDeDemandeRGPD]
    total: int


@dataclasses.dataclass(frozen=True, slots=True)
class DemandeRGPDModifiee:
    """Ce qu'une transition (verification, cloture) a produit."""

    state: str
    identity_verified: bool
    version: int


def _en_ligne(ligne: Any) -> LigneDeDemandeRGPD:
    return LigneDeDemandeRGPD(
        id=ligne["id"],
        data_subject_person_id=ligne["data_subject_person_id"],
        request_type=ligne["request_type"],
        channel=ligne["channel"],
        received_at=ligne["received_at"],
        identity_verified=ligne["identity_verified"],
        responsible_person_id=ligne["responsible_person_id"],
        due_at=ligne["due_at"],
        state=ligne["state"],
        response=ligne["response"],
        closed_at=ligne["closed_at"],
        version=ligne["version"],
    )


_COLONNES: Final = (
    "id, data_subject_person_id, request_type, channel, received_at, "
    "identity_verified, responsible_person_id, due_at, state, response, "
    "closed_at, version"
)

_PERSONNE_EXISTE: Final = text("SELECT 1 FROM person WHERE id = :personne")

_INSERER_UNE_DEMANDE: Final = text(
    "INSERT INTO data_subject_request "  # noqa: S608
    "(data_subject_person_id, request_type, channel, received_at, identity_verified, "
    " responsible_person_id, due_at, state, "
    " created_at, created_by_person_id, updated_at, updated_by_person_id) "
    "VALUES (:personne_concernee, :type_demande, :canal, :instant, false, "
    " :responsable, :echeance, :etat_initial, "
    " :instant, :acteur, :instant, :acteur) "
    f"RETURNING {_COLONNES}"
)


def receptionner_une_demande(
    connexion: Connection,
    *,
    data_subject_person_id: uuid.UUID,
    request_type: str,
    channel: str,
    responsible_person_id: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> LigneDeDemandeRGPD:
    """Réceptionner une demande de droit — §21.5, matrice §18 (voir `app/privacy/perimetre.py`).

    `due_at` est calculée ICI, depuis le MÊME `instant` que `received_at` —
    jamais un `now()` second, même leçon que `creer_un_jeton` (§7.0 sixième
    proposition de la passation).
    """
    if connexion.execute(_PERSONNE_EXISTE, {"personne": data_subject_person_id}).first() is None:
        raise ErreurApplicative(
            code=CODE_PERSONNE_CONCERNEE_INTROUVABLE,
            message=MESSAGE_PERSONNE_CONCERNEE_INTROUVABLE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    ligne = (
        connexion.execute(
            _INSERER_UNE_DEMANDE,
            {
                "personne_concernee": data_subject_person_id,
                "type_demande": request_type,
                "canal": channel,
                "instant": instant,
                "responsable": responsible_person_id,
                "echeance": instant + DELAI_DE_REPONSE_RGPD,
                "etat_initial": ETAT_RECU,
                "acteur": acteur,
            },
        )
        .mappings()
        .one()
    )
    resultat = _en_ligne(ligne)
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_DEMANDE_RECEPTIONNEE,
        resource_type=_RESOURCE_TYPE_DEMANDE_RGPD,
        resource_reference=resultat.id,
        actor_person_id=acteur,
        summary="Reception d'une demande de droit RGPD",
        new_values={"request_type": request_type, "state": ETAT_RECU},
    )
    return resultat


def lister_les_demandes(
    connexion: Connection,
    *,
    filtre_etat: str | None,
    filtre_type: str | None,
    page: int,
    taille: int,
) -> PageDeDemandesRGPD:
    """La page demandee de demandes RGPD, et le total — ressource GLOBALE."""
    source = "FROM data_subject_request"
    conditions: list[str] = []
    parametres: dict[str, object] = {}
    if filtre_etat is not None:
        conditions.append("state = :etat")
        parametres["etat"] = filtre_etat
    if filtre_type is not None:
        conditions.append("request_type = :type_demande")
        parametres["type_demande"] = filtre_type
    if conditions:
        source += " WHERE " + " AND ".join(conditions)

    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                f"SELECT {_COLONNES} {source} "
                "ORDER BY received_at DESC, id ASC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )
    return PageDeDemandesRGPD(demandes=[_en_ligne(ligne) for ligne in lignes], total=total)


_DEMANDE_PAR_ID: Final = text(
    f"SELECT {_COLONNES} FROM data_subject_request WHERE id = :demande"  # noqa: S608
)


def lire_une_demande(connexion: Connection, *, demande: uuid.UUID) -> LigneDeDemandeRGPD:
    """Une demande precise — 404 si elle n'existe pas."""
    ligne = connexion.execute(_DEMANDE_PAR_ID, {"demande": demande}).mappings().one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_DEMANDE_INTROUVABLE,
            message=MESSAGE_DEMANDE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    return _en_ligne(ligne)


_HISTORIQUE_D_UNE_DEMANDE: Final = text(
    "SELECT occurred_at, old_values, new_values, actor_person_id FROM audit_event "
    "WHERE resource_type = :type_ressource AND resource_reference = :demande "
    "ORDER BY occurred_at DESC, id ASC"
)


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementDHistoriqueRGPD:
    """Une ligne de l'historique — `audit_event` de cette demande."""

    occurred_at: dt.datetime
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    actor_person_id: uuid.UUID | None


def lire_l_historique_d_une_demande(
    connexion: Connection, *, demande: uuid.UUID
) -> list[EvenementDHistoriqueRGPD]:
    """L'historique complet d'une demande — la suite de ses `audit_event`.

    **AUCUNE VERIFICATION D'EXISTENCE ICI** : l'appelant doit avoir deja
    appele `lire_une_demande` — meme separation que `lire_l_historique_d_un_
    signalement`/`signalement_visible` (`T12`).
    """
    lignes = (
        connexion.execute(
            _HISTORIQUE_D_UNE_DEMANDE,
            {"type_ressource": _RESOURCE_TYPE_DEMANDE_RGPD, "demande": demande},
        )
        .mappings()
        .all()
    )
    return [
        EvenementDHistoriqueRGPD(
            occurred_at=ligne["occurred_at"],
            old_values=ligne["old_values"],
            new_values=ligne["new_values"],
            actor_person_id=ligne["actor_person_id"],
        )
        for ligne in lignes
    ]


_DEMANDE_POUR_TRANSITION: Final = text(
    "SELECT state, identity_verified, version FROM data_subject_request "
    "WHERE id = :demande FOR UPDATE"
)

_VERIFIER_L_IDENTITE: Final = text(
    "UPDATE data_subject_request "
    "SET identity_verified = true, updated_at = :instant, updated_by_person_id = :acteur, "
    "    version = version + 1 "
    "WHERE id = :demande "
    "RETURNING state, identity_verified, version"
)

_CLOTURER: Final = text(
    "UPDATE data_subject_request "
    "SET state = 'closed', response = :reponse, closed_at = :instant, "
    "    updated_at = :instant, updated_by_person_id = :acteur, version = version + 1 "
    "WHERE id = :demande "
    "RETURNING state, identity_verified, version"
)


def _lire_pour_transition(
    connexion: Connection, *, demande: uuid.UUID, version_attendue: int
) -> tuple[str, bool]:
    ligne = connexion.execute(_DEMANDE_POUR_TRANSITION, {"demande": demande}).one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_DEMANDE_INTROUVABLE,
            message=MESSAGE_DEMANDE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    etat_actuel, identite_verifiee, version_actuelle = ligne
    if version_actuelle != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
            details={"version_actuelle": version_actuelle},
        )
    return str(etat_actuel), bool(identite_verifiee)


def verifier_l_identite(
    connexion: Connection,
    *,
    demande: uuid.UUID,
    version_attendue: int,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> DemandeRGPDModifiee:
    """Marquer l'identite du demandeur comme verifiee — §21.5.

    AUCUNE precondition d'etat : verifiable avant ou apres la cloture (une
    verification tardive reste une trace utile). **IDEMPOTENT** : si deja
    verifiee, aucune ecriture, aucun evenement de plus — meme motif que le
    no-op de `lever_une_alerte` sur une alerte deja `open` (`T13`).
    """
    etat_actuel, deja_verifiee = _lire_pour_transition(
        connexion, demande=demande, version_attendue=version_attendue
    )
    if deja_verifiee:
        return DemandeRGPDModifiee(
            state=etat_actuel, identity_verified=True, version=version_attendue
        )
    resultat = connexion.execute(
        _VERIFIER_L_IDENTITE, {"demande": demande, "instant": instant, "acteur": acteur}
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_IDENTITE_VERIFIEE,
        resource_type=_RESOURCE_TYPE_DEMANDE_RGPD,
        resource_reference=demande,
        actor_person_id=acteur,
        summary="Verification d'identite d'une demande de droit RGPD",
        old_values={"identity_verified": False},
        new_values={"identity_verified": True},
    )
    return DemandeRGPDModifiee(
        state=resultat.state, identity_verified=resultat.identity_verified, version=resultat.version
    )


def cloturer_une_demande(
    connexion: Connection,
    *,
    demande: uuid.UUID,
    version_attendue: int,
    reponse: str,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> DemandeRGPDModifiee:
    """Cloturer une demande de droit — §21.5 « cloture tracable ».

    `reponse` resume ce qui a ete transmis/fait (« export structure » du
    backlog) — voir l'en-tete du module : jamais un fichier genere, jamais
    duplique dans `audit_event.reason`. Valide SEULEMENT depuis `ETAT_RECU` :
    une demande deja cloturee refuse en 409 (aucune reouverture, le corpus
    n'en nomme aucune).
    """
    etat_actuel, _identite_verifiee = _lire_pour_transition(
        connexion, demande=demande, version_attendue=version_attendue
    )
    if etat_actuel == ETAT_CLOS:
        raise ErreurApplicative(
            code=CODE_TRANSITION_INVALIDE,
            message=MESSAGE_TRANSITION_INVALIDE,
            statut=status.HTTP_409_CONFLICT,
            champ="etat",
        )
    resultat = connexion.execute(
        _CLOTURER, {"demande": demande, "reponse": reponse, "instant": instant, "acteur": acteur}
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_DEMANDE_CLOTUREE,
        resource_type=_RESOURCE_TYPE_DEMANDE_RGPD,
        resource_reference=demande,
        actor_person_id=acteur,
        summary="Cloture d'une demande de droit RGPD",
        old_values={"state": etat_actuel},
        new_values={"state": ETAT_CLOS},
    )
    return DemandeRGPDModifiee(
        state=resultat.state, identity_verified=resultat.identity_verified, version=resultat.version
    )
