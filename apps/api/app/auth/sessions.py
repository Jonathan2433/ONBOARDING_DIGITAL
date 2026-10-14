"""Sessions utilisateur — modele §10.4, cahier §7.4.

LOT 3, sous-etape `T6`, story `MVP-L03-US004`.

RIEN N'EST INVENTE ICI, ET J'AI FAILLI LE FAIRE

  `.env.example` declare depuis le LOT 0, sous-etape S5 :

      SESSION_COOKIE_NAME=exalt_session
      SESSION_COOKIE_SAMESITE=lax
      SESSION_IDLE_DAYS=7
      SESSION_ABSOLUTE_DAYS=30

  **Le cahier §7.4 exige « cookie `HttpOnly`, `Secure` et `SameSite` » sans dire
  laquelle**, et j'allais deriver `lax` du couplage avec la protection CSRF que le
  meme §7.4 exige. La valeur etait deja tranchee, et le nom du cookie aussi.
  §9.0 de la passation : *verifie avant de batir dessus*.

DEUX EXPIRATIONS, ET UNE SEULE A UNE COLONNE

  `absolute_expires_at` est une COLONNE, bornee a 30 jours par la contrainte
  `duree_absolue_bornee` de la migration `0012`.

  **L'expiration par inactivite n'a PAS de colonne, et ce n'est pas un oubli** :
  `T2` du LOT 3 l'a pose — « elle se CALCULE sur `last_activity_at`. Poser une
  colonne `inactive_expires_at` la ferait diverger de sa source des la premiere
  mise a jour ». Le calcul est donc ici, et nulle part ailleurs.

LE RAFRAICHISSEMENT EST UNE COURSE, COMME L'USAGE UNIQUE ET LE COMPTEUR D'ECHECS

  Lire `last_activity_at`, decider, puis ecrire laisserait deux requetes
  concurrentes juger valide une session que l'une des deux vient de laisser
  expirer -- **une session expiree serait ravivee**. C'est la troisieme fois que
  ce patron sert dans ce lot : un seul `UPDATE ... RETURNING` dont la clause
  `WHERE` porte toutes les conditions, et dont le nombre de lignes affectees EST
  le verdict.

LA DECONNEXION REVOQUE, ELLE N'EFFACE PAS

  Le §10.4 declare `revoked_at` et `revoke_reason`. Supprimer la ligne perdrait
  l'information -- quand, et pourquoi -- et `T9` en aura besoin : « le depart
  revoque immediatement les sessions », et il faudra pouvoir distinguer une
  deconnexion volontaire d'une revocation administrative.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import secrets
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.audit.services import enregistrer_un_evenement
from app.auth.modeles import TypeEvenementAuth
from observabilite.masquage import PREFIXE_SESSION

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  256 bits d'alea, comme le jeton de magic link. Le prefixe `oss_` a ete
#  RESERVE en `T3` dans `observabilite.masquage`, avec son motif : sans prefixe,
#  aucun detecteur -- filtre de masquage, regle Gitleaks -- ne peut etre exact
#  plutot qu'heuristique, et une heuristique dans un controle de securite est un
#  defaut (§7.25).
OCTETS_D_ALEA = 32

#  Les motifs de refus. **AUCUN NE SORT DE L'API** : une reponse qui
#  distinguerait « session inconnue » de « session expiree » apprendrait a un
#  attaquant qu'un jeton a existe.
MOTIF_SESSION_VALIDE = "session_valide"
MOTIF_SESSION_ABSENTE = "session_absente"
MOTIF_SESSION_REFUSEE = "session_refusee"

#  Les motifs de revocation, portes par `revoke_reason` du §10.4. `T9` en
#  ajoutera au moins un -- « depart du collaborateur » -- et les distinguer est
#  precisement ce que cette colonne permet.
REVOCATION_DECONNEXION = "deconnexion"

#  LOT 3, `T9`. **DEUX RAISONS ET NON UNE, PARCE QUE LA DISTINCTION EST
#  EXPLOITABLE.** `T6` avait ecrit ici que « `T9` devra distinguer une
#  deconnexion volontaire d'une revocation administrative » : le §10.4 declare
#  `revoke_reason` justement pour cela, et un operateur qui lit `auth_event` doit
#  pouvoir dire si la personne s'est deconnectee ou si son depart l'a fait.
#
#  Le §7.4 nomme DEUX causes -- « lors d'un depart **ou retrait d'acces** ». Seule
#  la premiere est realisee par `T9` ; la seconde suppose un ecran de gestion des
#  roles, qui n'existe pas. Le nom est donc pose sans etre employe, plutot que de
#  faire passer un retrait d'acces pour un depart.
REVOCATION_DEPART = "depart"
REVOCATION_RETRAIT_D_ACCES = "retrait_d_acces"


@dataclasses.dataclass(frozen=True)
class Session:
    """Une session lue et rafraichie. `personne` est non nul si et seulement si
    la session est valide."""

    motif: str
    personne: uuid.UUID | None = None
    identifiant: uuid.UUID | None = None

    @property
    def valide(self) -> bool:
        return self.personne is not None


def engendrer_un_jeton_de_session() -> str:
    """Un jeton de session : prefixe `oss_`, puis 256 bits d'alea.

    `secrets` et non `random` : un jeton de session previsible est un
    contournement d'authentification, exactement comme un magic link previsible.
    """
    return f"{PREFIXE_SESSION}{secrets.token_urlsafe(OCTETS_D_ALEA)}"


def empreinte_de_session(jeton: str) -> str:
    """Empreinte SHA-256 hexadecimale — 64 caracteres.

    Le §25.1 pose `user_session(session_token_hash) UNIQUE`, et la colonne est
    bornee a 64 caracteres : `make secrets-check` s'en sert pour distinguer une
    empreinte de jeton d'un stockage en clair.
    """
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def ouvrir_une_session(
    connexion: Connection,
    *,
    personne: uuid.UUID,
    instant: dt.datetime,
    jours_absolus: int,
) -> tuple[str, uuid.UUID]:
    """Creer une session et rendre `(jeton en clair, identifiant)`.

    **LE JETON EN CLAIR N'EXISTE QU'ICI ET DANS LE COOKIE.** La base ne porte que
    son empreinte -- §10.4, `session_token_hash`.

    Args:
        jours_absolus: `SESSION_ABSOLUTE_DAYS`. La contrainte
            `duree_absolue_bornee` de la migration `0012` refuse au-dela de 30
            jours, et un garde-fou de demarrage refuse une valeur divergente.
    """
    jeton = engendrer_un_jeton_de_session()
    identifiant = connexion.execute(
        text(
            "INSERT INTO user_session "
            "(session_token_hash, person_id, last_activity_at, absolute_expires_at, "
            " created_at) "
            "VALUES (:empreinte, :personne, :instant_activite, :expire_a, :instant_creation) "
            "RETURNING id"
        ),
        {
            "empreinte": empreinte_de_session(jeton),
            "personne": personne,
            #  `last_activity_at >= created_at` est une contrainte de `T2` : les
            #  deux valent le meme instant a la creation, ce qui la satisfait.
            "instant_activite": instant,
            "expire_a": instant + dt.timedelta(days=jours_absolus),
            "instant_creation": instant,
        },
    ).scalar_one()
    return jeton, uuid.UUID(str(identifiant))


def revoquer_toutes_les_sessions(
    connexion: Connection,
    *,
    personne: uuid.UUID,
    instant: dt.datetime,
    raison: str,
    empreinte_origine: str | None = None,
) -> int:
    """Revoquer TOUTES les sessions actives d'une personne. Rend leur nombre.

    LOT 3, `T9`, story `MVP-L03-US006`.

    **UN SEUL `UPDATE … RETURNING`, ET C'EST LE MEME MOTIF QUE `revoquer`.**
    Lire les sessions puis les revoquer une a une laisserait une session ouverte
    entre la lecture et l'ecriture : elle survivrait au depart. La clause `WHERE`
    porte toutes les conditions, et les identifiants rendus sont exactement ceux
    qui ont ete revoques -- **pas ceux qu'on croyait devoir revoquer**.

    **UN EVENEMENT PAR SESSION, ET NON UN SEUL POUR LE LOT.** Le §10.6 declare
    « session revoquee » au singulier : l'audit doit pouvoir dire combien de
    sessions ont ete fermees et lesquelles. Un evenement global perdrait le
    compte, et `T12` auditera cet evenement.

    Elle n'efface rien : le §10.4 declare `revoked_at` et `revoke_reason`, donc la
    trace du **quand** et du **pourquoi** est ce qui est demande.

    Args:
        raison: `REVOCATION_DEPART` ou `REVOCATION_RETRAIT_D_ACCES`. Le defaut est
            volontairement absent : une revocation en masse sans motif serait
            illisible dans l'audit.
    """
    revoquees = connexion.execute(
        text(
            "UPDATE user_session SET revoked_at = :instant, revoke_reason = :raison "
            "WHERE person_id = :personne AND revoked_at IS NULL "
            "RETURNING id"
        ),
        {"instant": instant, "raison": raison, "personne": personne},
    ).fetchall()

    for ligne in revoquees:
        connexion.execute(
            text(
                "INSERT INTO auth_event "
                "(event_type, occurred_at, person_id, request_origin_hash, detail) "
                "VALUES (:type_evenement, :instant, :personne, :origine, :detail)"
            ),
            {
                "type_evenement": TypeEvenementAuth.SESSION_REVOKED.value,
                "instant": instant,
                "personne": personne,
                "origine": empreinte_origine,
                #  Le motif, jamais l'empreinte de session : le §28.2 ne veut pas
                #  d'empreinte de jeton dans un journal, et l'audit n'en a pas
                #  besoin pour dire ce qui s'est passe.
                "detail": raison,
            },
        )
        #  LOT 10, `T2` : une ligne `audit_event` PAR SESSION, meme motif que
        #  `auth_event` ci-dessus — `reason` porte `raison`, DEJA obligatoire
        #  dans la signature de cette fonction (§21.1 : « obligatoire pour
        #  actions sensibles »).
        enregistrer_un_evenement(
            connexion,
            instant=instant,
            action_code=TypeEvenementAuth.SESSION_REVOKED.value,
            resource_type="user_session",
            resource_reference=uuid.UUID(str(ligne[0])),
            summary=f"Revocation de session : {raison}",
            actor_person_id=personne,
            reason=raison,
        )
    return len(revoquees)


def lire_et_rafraichir(
    connexion: Connection,
    *,
    jeton: str | None,
    instant: dt.datetime,
    jours_d_inactivite: int,
) -> Session:
    """Valider une session ET rafraichir son activite, en UNE seule operation.

    **LE VERDICT EST LE NOMBRE DE LIGNES AFFECTEES.** Toutes les conditions sont
    dans la clause `WHERE` d'un unique `UPDATE` :

        revoked_at IS NULL                              -- non revoquee
        absolute_expires_at > :instant                  -- §10.4, 30 jours max
        last_activity_at > :instant - 7 jours           -- §10.4, inactivite

    Les evaluer dans un `SELECT` separe laisserait deux requetes concurrentes
    juger valide une session que l'une des deux vient de laisser expirer : **une
    session expiree serait ravivee**. Meme forme qu'en `T4` et `T5`.

    Args:
        jeton: le jeton lu dans le cookie, ou `None`. Un cookie absent n'est pas
            une erreur : c'est un visiteur non connecte.
        jours_d_inactivite: `SESSION_IDLE_DAYS`.
    """
    if not jeton:
        return Session(motif=MOTIF_SESSION_ABSENTE)

    ligne = connexion.execute(
        text(
            "UPDATE user_session SET last_activity_at = :instant_activite "
            "WHERE session_token_hash = :empreinte "
            "  AND revoked_at IS NULL "
            "  AND absolute_expires_at > :instant_absolu "
            "  AND last_activity_at > :borne_inactivite "
            "RETURNING person_id, id"
        ),
        {
            #  Des noms DISTINCTS pour chaque emploi de l'instant : un meme
            #  parametre lie a deux colonnes rend « inconsistent types deduced
            #  for parameter », et le message ne nomme ni la table ni la colonne.
            #  §7.25, et c'est la quatrieme fois que ce piege est evite ainsi.
            "instant_activite": instant,
            "instant_absolu": instant,
            "borne_inactivite": instant - dt.timedelta(days=jours_d_inactivite),
            "empreinte": empreinte_de_session(jeton),
        },
    ).one_or_none()

    if ligne is None:
        #  **UN SEUL MOTIF POUR QUATRE CAUSES** : jeton inconnu, session revoquee,
        #  duree absolue depassee, inactivite depassee. Les distinguer
        #  apprendrait a un attaquant qu'un jeton a existe, et lequel des deux
        #  delais l'a emporte.
        return Session(motif=MOTIF_SESSION_REFUSEE)

    return Session(
        motif=MOTIF_SESSION_VALIDE,
        personne=uuid.UUID(str(ligne[0])),
        identifiant=uuid.UUID(str(ligne[1])),
    )


def revoquer(
    connexion: Connection,
    *,
    jeton: str | None,
    instant: dt.datetime,
    raison: str = REVOCATION_DECONNEXION,
    empreinte_origine: str | None = None,
) -> bool:
    """Revoquer une session. Rend `True` si une session active l'a ete.

    **ELLE N'EFFACE PAS.** Le §10.4 declare `revoked_at` et `revoke_reason` :
    supprimer la ligne perdrait quand et pourquoi, et `T9` devra distinguer une
    deconnexion volontaire d'une revocation administrative.

    `revoked_at IS NULL` dans la clause `WHERE` rend l'operation IDEMPOTENTE : une
    seconde deconnexion ne reecrit pas la premiere raison, et ne trace pas un
    second evenement. Une deconnexion rejouee ne doit pas fabriquer une trace
    d'audit qui n'a pas eu lieu.
    """
    if not jeton:
        return False
    ligne = connexion.execute(
        text(
            "UPDATE user_session SET revoked_at = :instant_revocation, "
            "  revoke_reason = :raison "
            "WHERE session_token_hash = :empreinte AND revoked_at IS NULL "
            "RETURNING person_id, id"
        ),
        {
            "instant_revocation": instant,
            "raison": raison,
            "empreinte": empreinte_de_session(jeton),
        },
    ).one_or_none()
    if ligne is None:
        return False

    #  §10.6 : « session revoquee » est l'un des sept types d'evenement.
    connexion.execute(
        text(
            "INSERT INTO auth_event "
            "(event_type, occurred_at, person_id, request_origin_hash, detail) "
            "VALUES (:type_evenement, :survenu_a, :personne, :origine, :detail)"
        ),
        {
            "type_evenement": TypeEvenementAuth.SESSION_REVOKED.value,
            "survenu_a": instant,
            "personne": ligne[0],
            "origine": empreinte_origine,
            #  Le motif, jamais le jeton ni son empreinte : le §10.6 exclut les
            #  donnees sensibles, et une empreinte n'apporterait rien a un audit.
            "detail": raison,
        },
    )
    #  LOT 10, `T2` : une ligne `audit_event`, meme transaction, `resource_
    #  reference` porte l'identifiant de LA session — la meme requete l'a deja
    #  rendu, jamais une seconde lecture.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=TypeEvenementAuth.SESSION_REVOKED.value,
        resource_type="user_session",
        resource_reference=uuid.UUID(str(ligne[1])),
        summary=f"Revocation de session : {raison}",
        actor_person_id=uuid.UUID(str(ligne[0])),
        reason=raison,
    )
    return True
