"""Changer un collaborateur d'entite — cahier §11.1, §16.3. LOT 9, `T3`.

CE QUE LE CORPUS DIT, ET CE QU'IL NE DIT PAS

  Le §11.1 : « le changement d'entite cloture l'ancienne appartenance et les
  responsabilites incompatibles ». Le §16.3 le nomme parmi les operations
  ATOMIQUES, aux cotes du depart et du changement de statut. **Rien de plus
  n'est ecrit nulle part** — ni une procedure pas a pas, ni un motif de
  transfert, ni si la nouvelle appartenance doit etre immediate ou future.

  Deux points ont ete arbitres par Jonathan le 08/10/2026, avant tout code :
    1. le meme moteur que le depart (`enregistrer_un_depart`) est reutilise,
       donc TOUTES les sessions et liens magiques de la personne sont
       revoques — pas seulement sur l'entite quittee ;
    2. la fermeture de l'ancienne appartenance et la creation de la nouvelle
       sont UNE SEULE transaction, jamais deux gestes separes.

POURQUOI `ARCHIVER_UN_PROFIL` N'EST PAS REUTILISE TEL QUEL

  Ce module compose les MEMES primitives que lui (`enregistrer_un_depart`,
  `archiver_une_appartenance`, `archiver_le_parcours_au_depart`), dans le
  MEME ordre, mais SANS son controle de perimetre : `archiver_un_profil`
  exige `ROLES_DU_CYCLE_DE_VIE` (ESM/ADM-E/SUPER seuls), alors que le §6.1
  donne au changement d'entite le MEME perimetre qu'a la creation
  (`MEME PERIMETRE QUE T2`, fiche-lot-9.md) — DSM et Booster y entrent, dans
  leur portee restreinte. Appeler `archiver_un_profil` aurait donc refuse a
  un DSM un transfert qu'il a par ailleurs le droit de faire.

L'ANCIENNE APPARTENANCE VA JUSQU'A `archived`, PAS SEULEMENT `departed`

  Un transfert n'est pas une situation en suspens : au contraire d'un vrai
  depart, ou `departed` reste une etape avant un geste humain delibere
  (`T8` du LOT 5), ici la nouvelle appartenance existe DEJA a la fin du
  meme appel. La laisser en `departed` creerait un residu qu'il faudrait
  archiver separement, sans raison. Le chemin complet du §24.1 est donc
  parcouru, exactement comme `archiver_un_profil` le fait pour un profil
  qui part : `Active --> Departed --> Archived`, ou `Future --> Archived`
  seul.

UN TROISIEME POINT, TROUVE EN ECRIVANT LES TESTS, PAS ANTICIPE PAR LA FICHE

  `ex_entity_membership_sans_chevauchement` (§25.2) ne porte AUCUNE clause
  `WHERE` : deux periodes d'une MEME personne ne se chevauchent jamais,
  meme archivees, meme entre deux entites differentes — « une personne
  n'a pas ete dans deux entites en meme temps, meme dans le passe ».
  Annuler une arrivee `future` (`archiver_une_appartenance`) NE POSE PAS
  `departure_date` (§24.1, « arrivee annulee » n'est pas un depart,
  `test_l_archivage_d_une_arrivee_FUTURE_n_enregistre_AUCUN_depart`, LOT 5
  `T8`) : sa periode reste `[arrival_date, )`, NON BORNEE, pour toujours.

  Transferer une personne `future` creerait donc TOUJOURS un chevauchement
  avec sa propre ancienne periode non bornee — quelle que soit la date
  choisie dans l'entite de destination, puisque deux plages non bornees
  se recoupent necessairement. Arbitrage de Jonathan du 08/10/2026 : **UNE
  arrivee annulee DANS LE CADRE D'UN TRANSFERT libere la date** — son
  `departure_date` est pose a `arrival_date`, ce qui rend sa periode VIDE
  (`[x, x)`), donc inerte pour l'exclusion. **Seulement dans ce cadre** :
  l'annulation SEULE (`archiver_un_profil`, hors transfert) n'est PAS
  modifiee, et son temoin du LOT 5 continue de prouver `departure_date IS
  NULL` pour ce chemin-la, inchange.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.onboarding.instances import archiver_le_parcours_au_depart
from app.people.creation import (
    CollaborateurCree,
    DemandeDAppartenance,
    creer_l_appartenance,
    valider_la_biconditionnelle_statut_client,
)
from app.people.ecriture import (
    CODE_ETAT_INCOMPATIBLE,
    CODE_VERSION_OBSOLETE,
    MESSAGE_ETAT_INCOMPATIBLE,
    MESSAGE_VERSION_OBSOLETE,
    traduire_un_refus_de_la_base,
)
from app.people.modeles import ETATS_OCCUPANTS, EtatAppartenance
from app.people.services import Revocation, archiver_une_appartenance, enregistrer_un_depart
from app.shared.errors import ErreurApplicative

_ETAT_SOUS_VERROU: Final[str] = """
SELECT membership_state, version, person_id FROM entity_membership
WHERE id = :cible AND entity_id = :entite
FOR UPDATE
"""

#  Ne libere la date QUE pour CE module : `archiver_une_appartenance` (LOT 5,
#  partagee avec `archiver_un_profil`) ne doit jamais ecrire `departure_date`
#  pour une arrivee `future` hors de ce cadre — voir l'en-tete du module.
_LIBERER_LA_PERIODE_ANNULEE: Final[str] = """
UPDATE entity_membership SET departure_date = arrival_date WHERE id = :cible
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Transfert:
    """Ce que le changement d'entite a produit, des deux cotes.

    `revocations` porte UNE entree par transition reellement appliquee sur
    l'ANCIENNE appartenance — deux quand elle etait `active` (le depart puis
    l'archivage), une seule depuis `future` — meme convention que
    `Archivage.revocations` (LOT 5, `T8`) et pour le meme motif : la seconde
    entree, quand elle existe, ne trouve plus rien a revoquer, ce qui PROUVE
    que la premiere avait deja tout pris.
    """

    nouvelle_appartenance: uuid.UUID
    version: int
    etat_precedent: str
    revocations: tuple[Revocation, ...]
    parcours_onboarding_archive: uuid.UUID | None

    #  Memes agregats que `Archivage` (LOT 5, `T8`), pour la meme raison :
    #  venant d'`active`, c'est le DEPART qui clot tout, l'archivage qui suit
    #  rend zero — sommer le dit, garder la derniere masquerait le depart.
    @property
    def sessions_revoquees(self) -> int:
        return sum(r.sessions_revoquees for r in self.revocations)

    @property
    def liens_invalides(self) -> int:
        return sum(r.liens_invalides for r in self.revocations)

    @property
    def relations_closes(self) -> dict[str, int]:
        total: dict[str, int] = {}
        for revocation in self.revocations:
            for table, nombre in revocation.relations_closes.items():
                total[table] = total.get(table, 0) + nombre
        return total


def _lire_sous_verrou(
    connexion: Connection, *, entite_source: uuid.UUID, cible: uuid.UUID, version_attendue: int
) -> tuple[str, uuid.UUID]:
    """Rendre l'etat courant et la personne, apres avoir exige la version du §18.4."""
    ligne = connexion.execute(
        text(_ETAT_SOUS_VERROU), {"cible": cible, "entite": entite_source}
    ).first()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=409,
        )
    etat, version, personne = str(ligne[0]), int(ligne[1]), uuid.UUID(str(ligne[2]))
    if version != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=409,
            details={"version_actuelle": version},
        )
    return etat, personne


def changer_d_entite(
    connexion: Connection,
    *,
    entite_source: uuid.UUID,
    entite_destination: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    demande: DemandeDAppartenance,
    instant: dt.datetime,
) -> Transfert:
    """Fermer l'ancienne appartenance et en ouvrir une nouvelle — UNE transaction.

    Leve `ErreurApplicative` : `409` version obsolete ou etat non occupant,
    `422` valeur refusee (biconditionnelle, ou refus traduit de la base).

    **LA GRILLE D'ETAT D'ABORD** — `409` pour une cible deja `departed` ou
    `archived` : on ne transfere pas une appartenance qui n'occupe plus rien,
    meme discipline que `_CIBLE_MODIFIABLE` (LOT 5 `T7`).
    """
    valider_la_biconditionnelle_statut_client(demande)

    etat, personne = _lire_sous_verrou(
        connexion, entite_source=entite_source, cible=cible, version_attendue=version_attendue
    )
    if etat not in ETATS_OCCUPANTS:
        raise ErreurApplicative(
            code=CODE_ETAT_INCOMPATIBLE,
            message=MESSAGE_ETAT_INCOMPATIBLE,
            statut=409,
        )

    try:
        #  **LE DEPART D'ABORD, ET SEULEMENT S'IL Y A LIEU** — meme branchement
        #  qu'`archiver_un_profil` : `future` va DIRECTEMENT a `archived`
        #  (« arrivee annulee », aucun depart n'a eu lieu) ; `active` passe par
        #  `departed`, et SEUL ce chemin archive un parcours d'onboarding actif.
        revocations: list[Revocation] = []
        parcours_archive: uuid.UUID | None = None
        if etat == EtatAppartenance.ACTIVE.value:
            revocations.append(
                enregistrer_un_depart(connexion, appartenance=cible, instant=instant)
            )
            parcours_archive = archiver_le_parcours_au_depart(
                connexion, entite=entite_source, appartenance=cible
            )
        revocations.append(
            archiver_une_appartenance(connexion, appartenance=cible, instant=instant)
        )
        if etat == EtatAppartenance.FUTURE.value:
            #  Arbitrage de Jonathan du 08/10/2026 : periode VIDEE, dans le
            #  cadre du transfert SEUL. Voir l'en-tete du module.
            connexion.execute(text(_LIBERER_LA_PERIODE_ANNULEE), {"cible": cible})

        cree: CollaborateurCree = creer_l_appartenance(
            connexion,
            entite=entite_destination,
            person_id=personne,
            demande=demande,
            acteur=acteur,
            instant=instant,
        )
    except (IntegrityError, DataError) as erreur:
        raise traduire_un_refus_de_la_base(erreur) from erreur

    #  LOT 10, `T3` : UN SEUL `audit_event` — « transfert », pas « depart » +
    #  « arrivee » separes, meme discipline que `creer_un_collaborateur`. Les
    #  deux entites sont les seules valeurs qu'un transfert fait varier, donc
    #  les seules portees par `old_values`/`new_values` : stringifiees, car
    #  `jsonb` ne sait pas serialiser un `uuid.UUID`.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="collaborateur_transfere",
        resource_type="entity_membership",
        resource_reference=cree.appartenance,
        entity_id=entite_destination,
        actor_person_id=acteur,
        summary=f"Changement d'entite : {entite_source} -> {entite_destination}",
        old_values={"entite": str(entite_source)},
        new_values={"entite": str(entite_destination)},
    )
    return Transfert(
        nouvelle_appartenance=cree.appartenance,
        version=cree.version,
        etat_precedent=etat,
        revocations=tuple(revocations),
        parcours_onboarding_archive=parcours_archive,
    )
