"""Jetons de comptes de service — cahier §22, modele §10.5, story `MVP-L03-US007`.

LOT 3, sous-etape `T10`.

LA DUREE MAXIMALE EST TRANCHEE, ET C'ETAIT `QO-072`

  Le cahier §7.4 dit « La duree maximale des jetons reste **a arbitrer avant leur
  creation** », et le §29 du cahier ouvre la question sous le numero **`QO-072`** --
  « Duree maximale des jetons de comptes de service | Jonathan / securite | LOT 3,
  story `MVP-L03-US007` ». Son echeance etait donc cette sous-etape.

  **Arbitrage de Jonathan du 22/08/2026 : 90 jours.** Le motif, dans ses termes :
  redonner une cle au script quatre fois par an, contre une cle fuitee qui cesse de
  fonctionner au bout de trois mois. `QO-072` est **close**, et la valeur reste
  **configurable** -- le §10.5 l'exige -- par `SERVICE_TOKEN_MAX_DAYS`.

  **LE PLAFOND EST UN PLAFOND, PAS UN DEFAUT.** Un jeton peut vivre moins ; il ne
  peut pas vivre plus. Demander davantage leve, plutot que d'ecreter en silence :
  un appelant qui croit avoir obtenu un an et qui en a quatre-vingt-dix jours se
  fera surprendre en production.

UN SEUL `UPDATE ... RETURNING`, SIXIEME OCCURRENCE DU PATRON

  L'authentification pose `last_used_at` **et** verifie la validite en une seule
  operation. Lire puis ecrire laisserait deux appels simultanes passer la lecture
  avant que l'un n'ecrive -- et surtout, cela separerait la verification de sa
  trace : le §10.5 declare « la derniere utilisation », et le critere de `US007`
  dit « **chaque appel** est audite ». Une trace posee dans un second temps peut
  manquer.

  Meme forme qu'en `T4`, `T5`, `T6`, `T7` et `T8`. Le patron est celui du lot.

L'ETAT DU COMPTE EST VERIFIE **APRES**, ET C'EST DELIBERE

  Un jeton vivant d'un compte **desactive** met tout de meme `last_used_at` a jour,
  puis est refuse. Mettre l'etat dans la clause `WHERE` aurait ete plus court, et
  aurait **perdu la trace** : un compte desactive qu'on continue de solliciter est
  exactement ce qu'un operateur veut voir. Le refus, lui, est identique a celui
  d'un jeton inconnu -- un seul gabarit vers l'extérieur, le motif reste interne.

LES DEUX TYPES D'EVENEMENT SONT CEUX QUI EXISTENT

  `LOGIN_SUCCESS` et `LOGIN_FAILURE`, portes par `auth_event.service_account_id` --
  la colonne que la migration `0013` ajoute parce que le diagramme §11 la declare
  (`ECART-037`). **Aucun huitieme type d'evenement** : le §10.6 en declare sept, et
  `T12` auditera exactement ces sept.

  Un jeton **inconnu** produit un evenement sans acteur -- ni personne, ni compte.
  C'est le meme cas qu'un magic link demande pour une adresse inconnue, et la
  contrainte `ck_auth_event_un_seul_acteur` le permet expressement.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.auth.jetons import OCTETS_D_ALEA, empreinte_de_jeton
from app.auth.modeles import EtatCompteDeService, TypeEvenementAuth
from app.auth.scopes import controler_les_scopes, couvre

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

from observabilite.masquage import PREFIXE_JETON_DE_SERVICE

#  Motifs internes. Ils sont **journalises et audites, jamais rendus** : les
#  distinguer vers l'exterieur dirait a un appelant s'il s'est approche.
MOTIF_JETON_ACCEPTE: Final = "jeton_de_service_accepte"
MOTIF_JETON_INCONNU: Final = "jeton_de_service_inconnu"
#  **CE MOTIF EST UN CORRECTIF, ET C'EST MON PROPRE CONTROLE QUI L'A TROUVE.**
#  Ma premiere version ne distinguait pas un jeton INCONNU d'un jeton EXISTANT mais
#  perime ou revoque : les deux rendaient `MOTIF_JETON_INCONNU`, sans acteur. Le
#  controle `make service-check` a compte deux evenements attribues au lieu de
#  trois, et il avait raison de le dire -- avec un critere qui exige que « chaque
#  appel soit audite », un refus anonyme n'audite rien d'utile. Un operateur veut
#  voir QUEL compte s'obstine avec une cle morte.
MOTIF_JETON_PERIME_OU_REVOQUE: Final = "jeton_de_service_perime_ou_revoque"
MOTIF_JETON_MAL_FORME: Final = "jeton_de_service_mal_forme"
MOTIF_COMPTE_DESACTIVE: Final = "compte_de_service_desactive"
MOTIF_SCOPE_MANQUANT: Final = "scope_manquant"


class DureeRefusee(ValueError):
    """La duree demandee depasse le plafond. **On leve, on n'ecrete pas.**

    Ecreter en silence ferait qu'un appelant croirait avoir obtenu un an et
    decouvrirait quatre-vingt-dix jours en production.
    """


@dataclass(frozen=True, slots=True)
class Authentification:
    """Le verdict, et ce que l'appelant peut en faire.

    `compte` vaut `None` sur tout refus, **y compris** quand le jeton est valide
    mais que le scope manque : rendre le compte sur un refus inviterait a s'en
    servir.
    """

    reussie: bool
    motif: str
    compte: uuid.UUID | None = None
    scopes: tuple[str, ...] = ()


def engendrer_un_jeton_de_service() -> str:
    """Prefixe `ost_`, puis 256 bits d'alea — meme forme que les deux autres jetons.

    `secrets` et non `random`. Le prefixe vient de `observabilite.masquage`, source
    unique : les trois barrieres de masquage et la regle Gitleaks le connaissent
    deja, et `T10` n'a rien a y ajouter.
    """
    return f"{PREFIXE_JETON_DE_SERVICE}{secrets.token_urlsafe(OCTETS_D_ALEA)}"


def creer_un_jeton(
    connexion: Connection,
    *,
    compte: uuid.UUID,
    scopes: list[str] | tuple[str, ...],
    instant: dt.datetime,
    jours: int,
    jours_maximum: int,
) -> tuple[str, uuid.UUID]:
    """Creer un jeton et rendre `(jeton en clair, identifiant)`.

    **LE JETON EN CLAIR N'EST RENDU QU'ICI, ET UNE SEULE FOIS.** La base ne porte
    que son empreinte -- le §10.5 dit « un hash du jeton ». Le perdre oblige a en
    creer un autre, et c'est voulu.

    Args:
        jours: duree demandee.
        jours_maximum: le plafond, `SERVICE_TOKEN_MAX_DAYS`. Passe explicitement
            plutot que lu ici : ce module ne connait pas `Parametres`, et un
            service qui lit sa propre configuration est intestable.

    Raises:
        DureeRefusee: si `jours` depasse le plafond, ou n'est pas positif.
        ScopeInvalide: si les scopes ne respectent pas la forme du §22.
    """
    if jours <= 0:
        message = f"duree refusee : {jours} jour(s). Une duree nulle ou negative n'a pas de sens"
        raise DureeRefusee(message)
    if jours > jours_maximum:
        message = (
            f"duree refusee : {jours} jours depasse le plafond de {jours_maximum} "
            f"(`QO-072`, arbitrage du 22/08/2026). La duree n'est PAS ecretee en silence"
        )
        raise DureeRefusee(message)

    valides = controler_les_scopes(list(scopes))
    jeton = engendrer_un_jeton_de_service()
    identifiant = connexion.execute(
        text(
            "INSERT INTO service_token "
            "(service_account_id, token_hash, expires_at, scopes) "
            "VALUES (:compte, :empreinte, :expire, CAST(:scopes AS jsonb)) RETURNING id"
        ),
        {
            "compte": compte,
            "empreinte": empreinte_de_jeton(jeton),
            "expire": instant + dt.timedelta(days=jours),
            #  `json.dumps` sur un tuple rendrait un tableau JSON, ce que la
            #  contrainte `ck_service_token_scopes_est_un_tableau` exige.
            "scopes": _en_tableau_json(valides),
        },
    ).scalar_one()
    return jeton, uuid.UUID(str(identifiant))


def authentifier_un_jeton(
    connexion: Connection,
    *,
    jeton: str,
    instant: dt.datetime,
    scope_requis: str,
    empreinte_origine: str | None = None,
) -> Authentification:
    """Authentifier un jeton de service et exiger un scope.

    Cinq refus possibles, **un seul gabarit vers l'exterieur** : forme invalide,
    jeton inconnu, jeton perime ou revoque, compte desactive, scope manquant. Le
    motif reste interne et part dans `auth_event` -- et les deux derniers cas y
    portent le compte, pour qu'un operateur voie QUI s'obstine.
    """
    #  --- 1. La forme, avant toute requete -------------------------------
    #
    #  Un texte qui n'est pas un jeton de ce projet ne merite pas un aller-retour
    #  en base. Et cela borne la surface : `token_hash` est unique, donc une
    #  requete par valeur arbitraire serait une sonde gratuite.
    if not jeton.startswith(PREFIXE_JETON_DE_SERVICE):
        return _refuser(connexion, MOTIF_JETON_MAL_FORME, instant, empreinte_origine)

    #  --- 2. UN SEUL `UPDATE ... RETURNING` ------------------------------
    ligne = connexion.execute(
        text(
            "UPDATE service_token SET last_used_at = :instant "
            "WHERE token_hash = :empreinte "
            "  AND revoked_at IS NULL "
            "  AND expires_at > :instant_expiration "
            "RETURNING service_account_id, scopes"
        ),
        {
            #  DEUX NOMS POUR LE MEME INSTANT : un parametre lie employe pour deux
            #  colonnes rend « inconsistent types deduced for parameter » sans
            #  nommer la colonne. Defauts `T4-2`, `T8-3`, et six fabriques en `T11`
            #  du LOT 2.
            "instant": instant,
            "instant_expiration": instant,
            "empreinte": empreinte_de_jeton(jeton),
        },
    ).one_or_none()
    if ligne is None:
        #  **UNE SECONDE LECTURE, SUR LE SEUL CHEMIN DE REFUS.** Sans elle, le refus
        #  d'un jeton perime ou revoque n'est attribue a aucun compte, et l'audit
        #  perd ce qu'il a de plus utile. Elle ne coute rien sur le chemin normal.
        #
        #  **ET ELLE NE FUITE RIEN** : le motif reste interne, l'appelant recoit le
        #  meme refus dans les deux cas, et un jeton inconnu ne devient pas
        #  distinguable d'un jeton mort vu de l'exterieur.
        connu = connexion.execute(
            text("SELECT service_account_id FROM service_token WHERE token_hash = :empreinte"),
            {"empreinte": empreinte_de_jeton(jeton)},
        ).scalar_one_or_none()
        if connu is None:
            return _refuser(connexion, MOTIF_JETON_INCONNU, instant, empreinte_origine)
        return _refuser(
            connexion,
            MOTIF_JETON_PERIME_OU_REVOQUE,
            instant,
            empreinte_origine,
            compte=uuid.UUID(str(connu)),
        )

    compte = uuid.UUID(str(ligne[0]))
    scopes = controler_les_scopes(ligne[1])

    #  --- 3. L'etat du compte, APRES la trace ----------------------------
    etat = connexion.execute(
        text("SELECT state FROM service_account WHERE id = :compte"),
        {"compte": compte},
    ).scalar_one()
    if etat != EtatCompteDeService.ACTIVE.value:
        return _refuser(
            connexion, MOTIF_COMPTE_DESACTIVE, instant, empreinte_origine, compte=compte
        )

    #  --- 4. Le scope ----------------------------------------------------
    if not couvre(scopes, scope_requis):
        return _refuser(connexion, MOTIF_SCOPE_MANQUANT, instant, empreinte_origine, compte=compte)

    _tracer(
        connexion,
        TypeEvenementAuth.LOGIN_SUCCESS,
        MOTIF_JETON_ACCEPTE,
        instant,
        empreinte_origine,
        compte=compte,
    )
    return Authentification(reussie=True, motif=MOTIF_JETON_ACCEPTE, compte=compte, scopes=scopes)


def revoquer_un_jeton(
    connexion: Connection, *, identifiant: uuid.UUID, instant: dt.datetime
) -> bool:
    """Revoquer un jeton. Rend `True` si un jeton actif l'a ete.

    **IDEMPOTENTE**, comme `revoquer` de `T6` : revoquer deux fois n'est pas une
    erreur, et la seconde fois ne deplace pas `revoked_at` -- sans quoi la date
    perdrait son sens.
    """
    return (
        connexion.execute(
            text(
                "UPDATE service_token SET revoked_at = :instant "
                "WHERE id = :identifiant AND revoked_at IS NULL"
            ),
            {"instant": instant, "identifiant": identifiant},
        ).rowcount
        > 0
    )


def _en_tableau_json(scopes: tuple[str, ...]) -> str:
    """Serialiser la liste en tableau JSON, ce que la contrainte de la table exige.

    `ck_service_token_scopes_est_un_tableau` verifie `jsonb_typeof(scopes) =
    'array'` : un scope unique passe en chaine serait refuse, et c'est bien.
    """
    return json.dumps(list(scopes))


def _refuser(
    connexion: Connection,
    motif: str,
    instant: dt.datetime,
    empreinte_origine: str | None,
    *,
    compte: uuid.UUID | None = None,
) -> Authentification:
    _tracer(
        connexion,
        TypeEvenementAuth.LOGIN_FAILURE,
        motif,
        instant,
        empreinte_origine,
        compte=compte,
    )
    return Authentification(reussie=False, motif=motif)


def _tracer(
    connexion: Connection,
    type_evenement: TypeEvenementAuth,
    motif: str,
    instant: dt.datetime,
    empreinte_origine: str | None,
    *,
    compte: uuid.UUID | None,
) -> None:
    """Un evenement par appel — le §10.5 veut « la derniere utilisation », le §22.1
    « chaque appel sensible audite ».

    `detail` porte le motif, **jamais le jeton ni son empreinte** : le §28.2 ne veut
    aucun jeton dans un journal, et une empreinte de jeton en est un identifiant.
    """
    connexion.execute(
        text(
            "INSERT INTO auth_event "
            "(event_type, occurred_at, service_account_id, request_origin_hash, detail) "
            "VALUES (:type_evenement, :instant, :compte, :origine, :detail)"
        ),
        {
            "type_evenement": type_evenement.value,
            "instant": instant,
            "compte": compte,
            "origine": empreinte_origine,
            "detail": motif,
        },
    )
