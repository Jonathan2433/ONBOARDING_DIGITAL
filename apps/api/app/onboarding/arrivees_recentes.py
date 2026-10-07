"""Les arrivees recentes de l'accueil — LOT 8, `T7`, `MVP-L08-US002`.

CE QUE LE CAHIER DECIDE, ET CE QU'IL NE DECIDE PAS

  §10.5 : « La fiche peut etre publiee apres validation, y compris avant la
  date d'arrivee. Le nouvel arrivant apparait dans la section « Ils nous ont
  rejoints recemment » pendant un mois apres sa date d'arrivee. » Le backlog
  (`MVP-L08-US002`) le confirme : « Une fiche validee apparait IMMEDIATEMENT ;
  elle quitte automatiquement la section un mois apres la date d'arrivee. »

  **LA FENETRE DE VISIBILITE N'EST DONC PAS `[arrival_date, recent_until]`,
  C'EST `[published_at, recent_until]`.** Une fiche validee avant l'arrivee
  (etat `future` de l'appartenance) est deja publique — « apparait
  immediatement » le dit a la lettre, et le modele autorise explicitement la
  publication par anticipation. Filtrer sur `membership_state` restreint a
  `active` exclurait donc des fiches que le cahier veut montrees : c'est
  pourquoi ce module reutilise `ETATS_OCCUPANTS` (future ET active) de
  `lire_la_fiche_arrivee`, jamais `ETAT_LISTE` (active seul) du trombinoscope.

POURQUOI LA REPONSE NE PORTE NI METIER, NI STATUT, NI CERCLE, NI PHOTO

  La matrice §5 donne « Arrivees recentes » en Lecture aux HUIT roles
  authentifies, sans exception — y compris DSM, qui est pourtant a TIRET sur
  « Consulter les informations preremplies » (metier/statut/client/DSM/cercle,
  §7). Exposer ces champs ici donnerait a tout role une porte derobee vers une
  information que la matrice lui refuse explicitement ailleurs — l'inverse de
  §6.5 : une invention qui elargirait un droit plutot que d'en combler un vide.
  « Arrivees recentes » est donc une AUTRE ressource que la fiche complete : la
  « page web de presentation » du §10.5, dont le contenu DECIDE est identite,
  date d'arrivee, presentation courte et fun fact — rien d'organisationnel.

  **AUCUNE PHOTO NON PLUS, ET POUR LA MEME RAISON QUE `T2` DU LOT 7.**
  `arrival_profile.photo_media_id` existe au modele (§12.1) mais AUCUNE route
  du depot ne l'ecrit — mesure, zero occurrence hors de sa declaration et de
  son commentaire. Resoudre une colonne que rien ne remplit servirait un champ
  structurellement toujours `null`, un code mort qu'aucun test ne pourrait
  distinguer d'un defaut (§7.32). `resoudre_la_miniature` (LOT 5) reste borne a
  la population du trombinoscope pour la meme raison que `lire_la_fiche_arrivee`
  l'a laisse de cote : a reexaminer quand un ecran en aura reellement besoin
  (`T9` a `T12`).

L'ANCRE EST INJECTEE, COMME POUR LES EVENEMENTS (`T2`)

  `recent_until` est une colonne DATE, ecrite une fois a la publication (`T3`
  du LOT 7). La comparer a `instant.date()` — jamais a un `now()` cache dans le
  SQL — rend la frontiere controlable par un test : reculer `recent_until` en
  base, ou avancer l'instant fourni, fait disparaitre la ligne sans qu'aucune
  horloge ne soit mockee.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.onboarding.modeles import EtatFicheArrivee
from app.people.modeles import ETATS_OCCUPANTS, VISIBILITE_LISTEE
from app.shared.pagination import TAILLES_DE_PAGE

#  Derivee de l'enumeration, jamais un litteral. Voir `ETAT_LISTE` au meme titre
#  dans `app/people/modeles.py`.
ETAT_FICHE_PUBLIEE: Final[str] = EtatFicheArrivee.PUBLISHED.value


@dataclasses.dataclass(frozen=True, slots=True)
class ArriveeRecente:
    """Une ligne de la section « Ils nous ont rejoints recemment », §10.5."""

    entity_membership_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    arrival_date: dt.date
    short_intro: str | None
    fun_fact: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class PageDesArriveesRecentes:
    """Une page et le total de la population — pas de la page."""

    arrivees: list[ArriveeRecente]
    total: int


#  **UNE SEULE SOURCE POUR LE COMPTAGE ET LA PAGE.** Meme discipline que le
#  trombinoscope (`T2` du LOT 5) et les evenements (`T2` du LOT 8) : les deux
#  requetes doivent porter sur la MEME population, sans quoi le total afficherait
#  autre chose que ce que la page rend.
_SOURCE: Final[str] = """
FROM arrival_profile AS ap
JOIN entity_membership AS em ON em.id = ap.entity_membership_id AND em.entity_id = ap.entity_id
JOIN person AS p ON p.id = em.person_id
WHERE ap.entity_id = :entite
  AND ap.state = :etat_publie
  AND em.membership_state = ANY(:etats_occupants)
  AND em.profile_visibility = :visibilite_listee
  AND ap.recent_until >= :aujourdhui
"""


def lister_les_arrivees_recentes(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: int,
    taille: int,
    instant: dt.datetime,
) -> PageDesArriveesRecentes:
    """Lire une page des fiches publiees encore dans leur mois d'arrivee.

    `instant` est fourni par l'appelant et reutilise pour `aujourdhui` : aucun
    `now()` cache dans le SQL ne peut donc classer differemment le comptage et
    la page.
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    parametres: dict[str, object] = {
        "entite": entite,
        "etat_publie": ETAT_FICHE_PUBLIEE,
        "etats_occupants": list(ETATS_OCCUPANTS),
        "visibilite_listee": VISIBILITE_LISTEE,
        "aujourdhui": instant.date(),
    }
    total = int(connexion.execute(text(f"SELECT count(*) {_SOURCE}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                "SELECT em.id, em.person_id, p.first_name, p.last_name, p.preferred_name, "
                "em.arrival_date, ap.short_intro, ap.fun_fact "
                f"{_SOURCE} "
                #  L'ordre est TOTAL : `em.id` est cle primaire, et deux arrivees
                #  a la meme date ne sont pas rares. Le plus RECENT d'abord —
                #  c'est une mise en avant, pas un annuaire.
                "ORDER BY em.arrival_date DESC, em.id DESC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )
    return PageDesArriveesRecentes(arrivees=[_en_arrivee(ligne) for ligne in lignes], total=total)


def _en_arrivee(ligne: Any) -> ArriveeRecente:
    return ArriveeRecente(
        entity_membership_id=ligne["id"],
        person_id=ligne["person_id"],
        first_name=ligne["first_name"],
        last_name=ligne["last_name"],
        preferred_name=ligne["preferred_name"],
        arrival_date=ligne["arrival_date"],
        short_intro=ligne["short_intro"],
        fun_fact=ligne["fun_fact"],
    )
