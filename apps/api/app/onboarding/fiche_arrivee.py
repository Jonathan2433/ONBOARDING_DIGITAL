"""La fiche d'arrivee en lecture — cahier §9.4, modele §12.1 — LOT 7, `T2`.

CE QUE CETTE SOUS-ETAPE SERT, ET CE QU'ELLE NE SERT PAS

  Elle sert les donnees ORGANISATIONNELLES preremplies — arrivee, metier,
  statut, DSM, client, cercle principal — et les champs PROPRES a la fiche —
  etat, presentation courte, fun fact — dans leur etat COURANT. Elle n'ecrit
  rien : la validation et la publication sont `T3`.

  **AUCUNE PHOTO N'EST SERVIE ICI.** `resoudre_la_miniature` (LOT 5) est bornee
  a la population du trombinoscope — `membership_state = 'active'`,
  `profile_visibility = 'published'` — par une egalite, pas un `= ANY(...)`.
  Or la population de la fiche d'arrivee inclut `future` : l'etendre sans
  besoin ecrit serait une invention (§6.5). A reexaminer quand un ecran en aura
  reellement besoin.

POURQUOI LES DONNEES ORGANISATIONNELLES SONT REUTILISEES, PAS RECALCULEES

  `app/people/profil.py::lire_la_fiche` resout DEJA metier, statut, client, DSM
  et cercle principal par cinq `LEFT JOIN` surs — quatre contraintes
  d'EXCLUSION le garantissent, et un test les exige. Recrire cette requete
  serait une DEUXIEME source qui diverge au premier ajout (§7.27) : `T2` du
  LOT 7 appelle `lire_la_fiche` avec une POPULATION plus large —
  `ETATS_OCCUPANTS` (future ET active) au lieu du seul `active`, et les TROIS
  visibilites au lieu de la seule `published` — exactement le parametre que
  `T8` du LOT 5 a deja ouvert pour `lire_la_fiche_archivee`. Une troisieme
  population, pas une troisieme requete.

  Elle rend donc aussi `cercles_secondaires` et `responsabilites`, inutiles
  ici : DEUX requetes de plus qu'un module dedie n'en aurait besoin, contre une
  DEUXIEME requete organisationnelle qui divergerait de la premiere a coup sur.
  Le cout mesure est constant, pas proportionnel a une population.

CE QUE `arrival_profile` NE PORTE PAS ENCORE N'EST PAS UNE ERREUR

  Rien ne cree la ligne `arrival_profile` avant `T3` : la lecture rend donc des
  valeurs par DEFAUT — `state='draft'`, le reste `None` — sans RIEN ecrire.
  Une lecture qui ecrit serait un effet de bord qu'aucun corpus ne demande, et
  `id`/`version` valant `None` dit au client qu'il n'y a encore rien a
  modifier : `T3` cree la ligne, il ne la met pas a jour.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.people.modeles import ETATS_OCCUPANTS, VISIBILITES_PROFIL
from app.people.profil import CercleDuProfil, FicheProfil, lire_la_fiche


@dataclasses.dataclass(frozen=True, slots=True)
class FicheArrivee:
    """La fiche d'arrivee complete — donnees organisationnelles et champs propres."""

    entity_membership_id: uuid.UUID
    #  `None` : aucune ligne `arrival_profile` n'existe encore. Voir l'en-tete.
    id: uuid.UUID | None
    version: int | None
    state: str
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    arrival_date: dt.date
    metier: str | None
    statut: str | None
    client: str | None
    dsm: str | None
    cercle_principal: CercleDuProfil | None
    short_intro: str | None
    fun_fact: str | None
    validated_at: dt.datetime | None
    published_at: dt.datetime | None
    recent_until: dt.date | None


#  La ligne `arrival_profile`, si elle existe. Bornee aux colonnes que CETTE
#  sous-etape sert — ni `photo_media_id` (voir l'en-tete), ni `archived_at` et
#  consorts, que `T3` et au-dela liront.
_FICHE_ARRIVEE: Final[str] = """
SELECT id, version, state, short_intro, fun_fact, validated_at, published_at, recent_until
FROM arrival_profile
WHERE entity_membership_id = :appartenance AND entity_id = :entite
"""


def lire_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    instant: dt.datetime,
) -> FicheArrivee | None:
    """La fiche d'arrivee d'une appartenance, ou `None`.

    **`None` COUVRE TROIS CAUSES**, la meme forme que `lire_la_fiche` : l'
    appartenance n'existe pas, elle appartient a une AUTRE entite, ou elle
    n'est dans AUCUN etat occupant — un depart ou une archive n'a plus de
    fiche d'arrivee a consulter, la sienne ou celle d'un autre.
    """
    profil: FicheProfil | None = lire_la_fiche(
        connexion,
        entite=entite,
        appartenance=appartenance,
        instant=instant,
        etats=ETATS_OCCUPANTS,
        visibilites=VISIBILITES_PROFIL,
    )
    if profil is None:
        return None

    ligne = connexion.execute(
        text(_FICHE_ARRIVEE), {"appartenance": appartenance, "entite": entite}
    ).one_or_none()

    return FicheArrivee(
        entity_membership_id=profil.id,
        id=None if ligne is None else uuid.UUID(str(ligne.id)),
        version=None if ligne is None else int(ligne.version),
        state="draft" if ligne is None else str(ligne.state),
        person_id=profil.person_id,
        first_name=profil.first_name,
        last_name=profil.last_name,
        preferred_name=profil.preferred_name,
        arrival_date=profil.arrival_date,
        metier=profil.metier,
        statut=profil.statut,
        client=profil.client,
        dsm=profil.dsm,
        cercle_principal=profil.cercle_principal,
        short_intro=None
        if ligne is None
        else (None if ligne.short_intro is None else str(ligne.short_intro)),
        fun_fact=None
        if ligne is None
        else (None if ligne.fun_fact is None else str(ligne.fun_fact)),
        validated_at=None if ligne is None else ligne.validated_at,
        published_at=None if ligne is None else ligne.published_at,
        recent_until=None if ligne is None else ligne.recent_until,
    )
