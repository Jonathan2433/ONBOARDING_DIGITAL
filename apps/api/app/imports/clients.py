"""Rapprocher le client du CSV (`F13`) avec le référentiel — LOT 9, `T8`.

Story `MVP-L09-US005`, décision à venir.

LA RESSEMBLANCE N'EST PAS DÉTECTÉE — ARBITRAGE EXPLICITE DE JONATHAN

  `codes-erreurs-import.md` §1.2 nomme QUATRE situations pour `F13` : une
  correspondance exacte avec un client déjà activé dans l'entité (rattachement
  direct, aucun code), une correspondance exacte avec un client global pas
  encore activé localement (`W-CLIENT-001`), une « RESSEMBLANCE sans
  correspondance exacte » (`D-CLIENT-001`), et « aucune correspondance ni
  ressemblance » (`D-CLIENT-002`).

  **Aucun document ne dit COMMENT reconnaître une ressemblance** — quel
  algorithme, quel seuil — et aucun outil de recherche approximative n'est
  installé dans cette base (`pg_trgm`/`unaccent` étaient prévus pour le
  trombinoscope du LOT 5, jamais posés — mesuré, `0002_extensions.py` n'installe
  que `btree_gist`). Inventer un seuil ou une nouvelle extension PostgreSQL
  pour cette seule sous-étape aurait été exactement ce que le §6.5 interdit.

  Posé à Jonathan avant tout code : **aucune détection automatique de
  ressemblance.** Tout ce qui n'est pas une correspondance exacte — directe ou
  via un alias déjà validé par un humain — devient `D-CLIENT-002`, « client
  inconnu », et c'est un humain qui le recherche et le choisit via
  `GET .../clients`. `D-CLIENT-001` n'est donc JAMAIS produit par ce module :
  un code déclaré par le référentiel peut rester inatteint tant que son
  mécanisme déclencheur n'existe pas, plutôt que d'être simulé par une
  heuristique inventée.

CE QU'UN ALIAS DÉJÀ VALIDÉ RÉSOUT, ET POURQUOI C'EST UNE CORRESPONDANCE EXACTE

  `client_alias` (LOT 2, `T6`) porte `validated_by_person_id`/`validated_at`
  **NOT NULL** : une ligne n'y vit QUE si un humain l'a déjà validée (`DATA-005`,
  « aucune fusion automatique, les alias exigent une validation humaine »). Un
  nom qui correspond à un alias existant n'est donc PAS une ressemblance à
  confirmer une deuxième fois — c'est une correspondance déjà humainement
  tranchée, exactement au même titre que `canonical_name`. La priorité va à
  l'alias LOCAL à l'entité, puis à l'alias GLOBAL, puis au nom canonique —
  jamais l'inverse, qui ferait qu'un alias plus récent et plus spécifique à
  l'entité perde contre le nom d'origine.

CE QUE CE MODULE N'ÉCRIT JAMAIS

  Aucune ligne `entity_client` : « le client global est activé localement LORS
  DE L'IMPORT » (`codes-erreurs-import.md` §4, `W-CLIENT-001`) — c'est `T9`,
  l'import transactionnel, qui active. Ce module se contente de SIGNALER
  qu'une activation sera nécessaire.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

CODE_CLIENT_NON_ACTIVE_LOCALEMENT: Final = "W-CLIENT-001"
CODE_CLIENT_INCONNU: Final = "D-CLIENT-002"

MESSAGE_CLIENT_NON_ACTIVE_LOCALEMENT: Final = "Le client n'est pas encore activé dans cette entité."
RESOLUTION_CLIENT_NON_ACTIVE_LOCALEMENT: Final = (
    "Le client global est activé localement lors de l'import."
)

MESSAGE_CLIENT_INCONNU: Final = "Le client indiqué est inconnu du référentiel global."
RESOLUTION_CLIENT_INCONNU: Final = "Créer le client, ou corriger la valeur."


@dataclasses.dataclass(frozen=True, slots=True)
class ClientResolu:
    """Ce que la recherche a trouvé pour UN nom normalisé — ou rien."""

    client_id: uuid.UUID | None
    actif_localement: bool


@dataclasses.dataclass(frozen=True, slots=True)
class ClientDuCatalogue:
    """Un client du référentiel global, vu depuis UNE entité — ferme `ECART-060`.

    Le filtre « client » du trombinoscope (`T3` du LOT 5) accepte déjà un
    identifiant sans qu'aucune route ne serve la liste des valeurs
    possibles — c'est `ECART-060`. Cette liste est la même, qu'elle soit
    consommée par un filtre ou par la validation d'un rapprochement
    d'import : un client est un client, et `actif_localement` dit si une
    affectation à CETTE entité peut s'y rattacher directement.
    """

    identifiant: uuid.UUID
    nom_canonique: str
    nom_affiche: str
    actif_localement: bool


#  Priorité STRICTE, jamais l'inverse : alias LOCAL à l'entité, puis alias
#  GLOBAL, puis nom canonique. `DISTINCT ON` ne garde que la première ligne
#  par nom normalisé dans cet ordre.
_RESOUDRE_LES_CLIENTS: Final = text(
    """
    SELECT DISTINCT ON (nom_normalise) nom_normalise, client_id
      FROM (
        SELECT ca.alias_normalized AS nom_normalise, ca.client_id AS client_id, 0 AS priorite
          FROM client_alias ca
         WHERE ca.alias_normalized = ANY(:noms) AND ca.entity_id = :entite
        UNION ALL
        SELECT ca.alias_normalized AS nom_normalise, ca.client_id AS client_id, 1 AS priorite
          FROM client_alias ca
         WHERE ca.alias_normalized = ANY(:noms) AND ca.entity_id IS NULL
        UNION ALL
        SELECT c.canonical_name AS nom_normalise, c.id AS client_id, 2 AS priorite
          FROM client c
         WHERE c.canonical_name = ANY(:noms) AND c.status = 'active'
      ) candidats
     ORDER BY nom_normalise, priorite
    """
)

_CLIENTS_ACTIFS_LOCALEMENT: Final = text(
    """
    SELECT client_id FROM entity_client
     WHERE entity_id = :entite AND client_id = ANY(:ids) AND archived_at IS NULL
    """
)


def resoudre_les_clients(
    connexion: Connection, *, entite: uuid.UUID, noms_normalises: list[str]
) -> dict[str, ClientResolu]:
    """Pour chaque nom CANDIDAT du lot, ce que le référentiel en sait.

    **UNE SEULE PAIRE DE REQUÊTES POUR TOUT LE LOT**, jamais une par ligne —
    même discipline que `app.imports.analyse._etats_des_personnes_existantes`.
    """
    if not noms_normalises:
        return {}
    candidats = connexion.execute(
        _RESOUDRE_LES_CLIENTS, {"noms": noms_normalises, "entite": entite}
    ).all()
    identifiants = [ligne.client_id for ligne in candidats]
    actifs = set()
    if identifiants:
        actifs = {
            ligne.client_id
            for ligne in connexion.execute(
                _CLIENTS_ACTIFS_LOCALEMENT, {"entite": entite, "ids": identifiants}
            )
        }
    return {
        ligne.nom_normalise: ClientResolu(
            client_id=ligne.client_id, actif_localement=ligne.client_id in actifs
        )
        for ligne in candidats
    }


_LISTER_LES_CLIENTS: Final = text(
    """
    SELECT c.id, c.canonical_name, c.display_name,
           (ec.id IS NOT NULL AND ec.archived_at IS NULL) AS actif_localement
      FROM client c
      LEFT JOIN entity_client ec ON ec.client_id = c.id AND ec.entity_id = :entite
     WHERE c.status = 'active'
     ORDER BY c.canonical_name
    """
)


def lister_les_clients(
    connexion: Connection, *, entite: uuid.UUID
) -> tuple[ClientDuCatalogue, ...]:
    """Le référentiel global des clients actifs, vu depuis `entite` — ferme `ECART-060`.

    **AUCUN FILTRE SUR `entity_client`** : un client non encore activé
    localement doit rester VISIBLE ici, sans quoi un humain cherchant à
    rapprocher une ligne ne pourrait jamais choisir le client qui lui
    manque — précisément le cas `W-CLIENT-001`.
    """
    return tuple(
        ClientDuCatalogue(
            identifiant=ligne.id,
            nom_canonique=ligne.canonical_name,
            nom_affiche=ligne.display_name,
            actif_localement=ligne.actif_localement,
        )
        for ligne in connexion.execute(_LISTER_LES_CLIENTS, {"entite": entite})
    )
