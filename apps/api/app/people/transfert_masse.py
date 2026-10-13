"""Changer plusieurs collaborateurs d'entite en une seule operation controlee.

LOT 9, `T11`, `MVP-L09-US003`. Cahier §10.8 (« changements unitaires et en
masse »), §18.6 (idempotence exigee pour les « operations en masse »).

CE QUE LE CORPUS NE DIT PAS, ET CE QUI A ETE ARBITRE PAR JONATHAN

  Ni le cahier ni la matrice ne nomment QUELLE action doit exister en version
  « plusieurs a la fois » — seulement qu'il en existe une. La creation en
  masse est deja servie par l'import CSV (`T6` a `T10`) ; arbitrage du
  12/10/2026 (`AskUserQuestion`, reformule sans jargon) : **seul le
  changement d'entite** (`T3`, `changer_d_entite`) recoit une variante en
  masse dans cette sous-etape — c'est la seule action structurante que `T2`/
  `T3` ont construite et qui n'a pas deja de forme groupee.

POURQUOI AUCUNE LOGIQUE METIER N'EST DUPLIQUEE ICI — §7.27

  Ce module REJOUE exactement ce que la route unitaire de `T3` fait — resoudre
  l'entite de destination, verifier LA MEME permission
  (`resoudre_l_autorisation_de_creation`, « meme perimetre que la creation »),
  puis appeler `changer_d_entite` — pour chaque element, dans son PROPRE
  savepoint. Aucune regle de permission, de biconditionnelle ou de transition
  n'est reecrite : les reecrire divergerait de l'original au premier reglage
  change (§7.27), et seule la BOUCLE et l'ISOLATION par element sont neuves —
  le meme motif que `app.imports.execution` (`T9`) pour isoler un refus d'un
  element du reste du lot.

COMMENT « LA PREVISUALISATION INDIQUE L'IMPACT » EST SERVIE, SANS RIEN
INVENTER DE PLUS QUE CE QUI EXISTE DEJA

  `mode="apercu"` execute EXACTEMENT le meme chemin que `mode="execution"` —
  memes verifications, memes ecritures passees a la base — a l'interieur
  d'un `connexion.begin_nested()` systematiquement ANNULE a la fin, succes ou
  echec. L'« impact » rendu (sessions revoquees, liens invalides, relations
  closes) est donc le resultat REEL de l'execution, jamais une estimation
  separee qui pourrait diverger du chemin reellement emprunte a l'execution.

COMMENT L'IDEMPOTENCE DU §18.6 EST SATISFAITE SANS MECANISME NOUVEAU

  `changer_d_entite` refuse DEJA, en `409` (`CODE_ETAT_INCOMPATIBLE`), toute
  cible qui n'est plus `active` ni `future` — precisement l'etat d'une
  appartenance DEJA transferee par un appel precedent. Rejouer le MEME lot
  de transferts est donc sans danger : chaque element deja traite est refuse
  explicitement avec ce code, aucun n'est rejoue ni ecrase en silence
  (§18.4). Aucun jeton d'idempotence n'est introduit : l'etat de la cible EST
  le jeton, et il est deja verrouille (`FOR UPDATE`) par `_lire_sous_verrou`.

CE QUE CE MODULE NE FAIT JAMAIS

  Aucune ecriture d'audit : `archive_reason`/`assignment_reason` et
  `audit_event` restent hors du perimetre de ce lot (`ECART-064`, LOT 10).
  Le critere d'acceptation de `US003` nomme « auditees », mais le decoupage
  valide de la fiche (`fiche-lot-9.md`) a deja reduit l'enonce de `T11` a
  « previsualisation d'impact, idempotence, erreurs partielles explicites »
  — sans le mot « auditees » — et c'est cette portee, deja arretee avant
  cette sous-etape, qui est suivie ici plutot qu'une relecture du backlog.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Final, Literal

from sqlalchemy.engine import Connection

from app.entities.routes import CODE_ENTITE_INTROUVABLE, MESSAGE_ENTITE_INTROUVABLE
from app.entities.services import resoudre_une_entite_active
from app.people.creation import CODE_ACCES_REFUSE, MESSAGE_ACCES_REFUSE, DemandeDAppartenance
from app.people.transfert import Transfert, changer_d_entite
from app.permissions.perimetre import PropositionDeCreation, resoudre_l_autorisation_de_creation
from app.permissions.services import resoudre_les_permissions
from app.shared.errors import ErreurApplicative

#  **BORNE TECHNIQUE, PAS UNE REGLE METIER.** Rien dans le corpus ne nomme de
#  taille de lot : la valeur protege la transaction unique du `POST` d'une
#  taille non bornee, meme discipline que les tailles de page du §18.2 pour
#  la lecture — mais ici c'est une sauvegarde d'ingenierie, pas un nombre
#  decide par Jonathan. A ajuster sans question s'il se revele trop etroit.
TAILLE_MAXIMALE_DU_LOT: Final = 100

Mode = Literal["apercu", "execution"]


@dataclasses.dataclass(frozen=True, slots=True)
class ElementDuTransfertEnMasse:
    """Un transfert demande, dans le MEME format que l'unitaire (`T3`).

    `circle_id`/`dsm_person_id` sont PORTES A PART de `demande` — et non lus
    depuis `demande.circle_id`/`demande.dsm_person_id` — parce que
    `DemandeDAppartenance` les declare NULLABLES pour d'autres appelants
    (`T9`, un DSM sans cercle), alors qu'un element de transfert les exige
    TOUJOURS (meme champ requis que `DemandeDeChangementDEntite.
    cercle_principal`, `T3`). Deux porteurs du meme fait, jamais une
    coercition qui ferait perdre au type verificateur ce que la route a deja
    garanti.
    """

    appartenance: uuid.UUID
    entite_destination_code: str
    version_attendue: int
    circle_id: uuid.UUID
    dsm_person_id: uuid.UUID | None
    demande: DemandeDAppartenance


@dataclasses.dataclass(frozen=True, slots=True)
class ResultatDUnTransfert:
    """Le sort d'UN element — jamais une exception qui emporterait les autres.

    `succes=False` porte le MEME `code`/`message`/`details` qu'une
    `ErreurApplicative` unitaire aurait leves — aucune seconde forme de
    refus (§18.3), seulement rapportee au lieu d'etre levee.
    """

    appartenance: uuid.UUID
    succes: bool
    transfert: Transfert | None
    code_erreur: str | None
    message_erreur: str | None
    details_erreur: dict[str, object] | None


def executer_le_transfert_en_masse(
    connexion: Connection,
    *,
    entite_source: uuid.UUID,
    acteur: uuid.UUID,
    elements: Sequence[ElementDuTransfertEnMasse],
    instant: dt.datetime,
    mode: Mode,
) -> tuple[ResultatDUnTransfert, ...]:
    """Appliquer `changer_d_entite` a chaque element, un SAVEPOINT par element.

    Pour chaque element : resoudre l'entite de destination (`404` rapporte si
    absente ou non active), verifier LA MEME permission que la creation sur
    CETTE destination et CETTE proposition (`403` rapporte sinon), puis
    appeler `changer_d_entite`. Toute `ErreurApplicative` — la sienne ou celle
    levee ici — est RAPPORTEE sur l'element, jamais propagee : c'est
    precisement ce que « erreurs partielles explicites » exige.

    En `mode="apercu"`, CHAQUE savepoint est annule a la fin, succes ou
    echec : rien n'est jamais ecrit par cet appel. En `mode="execution"`,
    un succes est LIBERE (donc ecrit dans la transaction englobante de la
    route), un echec est annule — le motif exact de `app.imports.execution`,
    `T9`.
    """
    resultats: list[ResultatDUnTransfert] = []
    for element in elements:
        point = connexion.begin_nested()
        try:
            entite_destination = resoudre_une_entite_active(
                connexion, element.entite_destination_code
            )
            if entite_destination is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=404,
                )
            permissions = resoudre_les_permissions(
                connexion, acteur, entite_destination.id, instant
            )
            autorise = resoudre_l_autorisation_de_creation(
                connexion,
                entite=entite_destination.id,
                acteur=acteur,
                roles=frozenset(permissions.roles),
                proposition=PropositionDeCreation(
                    circle_id=element.circle_id,
                    dsm_person_id=element.dsm_person_id,
                ),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=403,
                )
            transfert = changer_d_entite(
                connexion,
                entite_source=entite_source,
                entite_destination=entite_destination.id,
                cible=element.appartenance,
                acteur=acteur,
                version_attendue=element.version_attendue,
                demande=element.demande,
                instant=instant,
            )
        except ErreurApplicative as erreur:
            point.rollback()
            resultats.append(
                ResultatDUnTransfert(
                    appartenance=element.appartenance,
                    succes=False,
                    transfert=None,
                    code_erreur=erreur.code,
                    message_erreur=erreur.message,
                    details_erreur=erreur.details,
                )
            )
            continue
        #  **APERCU : TOUJOURS ANNULE, MEME EN SUCCES.** C'est ce qui rend la
        #  previsualisation sans effet — jamais une ecriture « provisoire ».
        if mode == "apercu":
            point.rollback()
        else:
            point.commit()
        resultats.append(
            ResultatDUnTransfert(
                appartenance=element.appartenance,
                succes=True,
                transfert=transfert,
                code_erreur=None,
                message_erreur=None,
                details_erreur=None,
            )
        )
    return tuple(resultats)
