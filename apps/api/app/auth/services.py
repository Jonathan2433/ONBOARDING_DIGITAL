"""Service de la demande de magic link — modele §10.3, cahier §7.2.

LOT 3, sous-etape `T3`, story `MVP-L03-US001`.

LES QUATRE CONDITIONS SONT ECRITES, AUCUNE N'EST INVENTEE

  Cahier §7.2, litteralement :

      « la personne doit deja exister dans PostgreSQL »
      « son appartenance doit etre active »
      « son adresse doit appartenir a un domaine autorise »
      « le domaine initial confirme est `@exalt-company.com` »

  Et modele §10.3, `person_id` : « Personne **active** existante ». Exister ne
  suffit donc pas : `person.account_state` doit valoir `active`.

  **UNE CINQUIEME CONDITION EST DERIVEE, ET ELLE EST DECLAREE ICI.** Le §10.1
  pose `user_account.state` a `active`, `locked` ou `disabled` sur un « compte
  permettant l'authentification ». Un compte `disabled` qui recevrait quand meme
  des liens rendrait cette colonne **sans effet** -- et `T5` s'en servira pour le
  verrouillage apres echecs, `T9` pour la revocation au depart.

  La lecture retenue, et son asymetrie est le point :

      le compte EXISTE et n'est pas `active`   ->  REFUS
      le compte N'EXISTE PAS                   ->  ce n'est PAS un refus

  Exiger l'existence serait exiger plus que le modele : `magic_link_request`
  reference `person_id`, **jamais** `user_account_id`, et aucun lot ne cree
  aujourd'hui de ligne `user_account`. La feature serait inutilisable, ce qui est
  le defaut du §7.20 -- un controle qui exige plus que le critere.

L'AUTORITE DES DOMAINES EST LA TABLE, PAS UNE VARIABLE

  Modele §5.4, colonne `active` : « **Controle l'usage lors de
  l'authentification** ». C'est litteral, et `T2` du LOT 2 avait deja pose cette
  lecture. `ALLOWED_EMAIL_DOMAINS` est la GRAINE dont `make domaines-provision`
  pose la ligne initiale ; elle n'autorise rien par elle-meme (`DEC-523`).

  Un domaine porte a la fois `active` et une periode `[starts_at, ends_at)` : le
  §5.4 demande les deux, et `T2` du LOT 2 a pose qu'ils ne se contredisent pas.
  Les DEUX sont donc exigees ici -- retenir la seule `active` laisserait un
  domaine expire autoriser une connexion.

  `entity_id` nullable veut dire « domaine global ». Un domaine LOCAL n'autorise
  que les membres de SON entite : c'est la lecture du §2.5, « refus par defaut »,
  et l'inverse ferait d'un domaine local un domaine global en silence.

L'INVALIDATION N'EST PAS UNE OPTION : LA BASE L'IMPOSE

  L'index partiel `uq_magic_link_request_person_id_actif` pose en `T2` refuse un
  second lien actif pour une meme personne. Le §10.3 decrit l'ACTION -- « le
  dernier lien invalide les precedents encore actifs » -- et l'index en porte
  l'INVARIANT. Un service qui insererait sans invalider verrait son insertion
  **refusee** : l'oubli est impossible, non improbable.

CE QUE CE SERVICE NE FAIT PAS

  - **il n'envoie pas l'e-mail.** Il rend le lien a son appelant, qui l'envoie
    APRES avoir repondu : voir `routes.py`, le motif est la duree de reponse ;
  - **il ne consomme aucun lien.** `T4`, story `US002` ;
  - **il ne limite aucun debit.** `T8`. Il renseigne `request_origin_hash`, dont
    `T8` aura besoin -- une colonne laissee nulle par `T3` serait inexploitable
    retroactivement.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.auth.jetons import empreinte_de_jeton, engendrer_jeton_magic_link
from app.auth.modeles import (
    MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    EtatCompte,
    TypeCompte,
    TypeEvenementAuth,
)
from app.auth.mots_de_passe import ALGORITHME, hacher, parametres_a_durcir, verifier
from app.people.modeles import EtatAppartenance, normaliser_email
from app.people.modeles import EtatCompte as EtatPersonne

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  Les motifs de sortie. **AUCUN NE SORT DE L'API** : ils vont a l'audit et au
#  journal, jamais dans la reponse -- une reponse qui distinguerait
#  `adresse_inconnue` de `appartenance_non_active` revelerait l'existence du
#  compte, ce que `US001` interdit.
MOTIF_LIEN_EMIS = "lien_emis"
MOTIF_ADRESSE_INCONNUE = "adresse_inconnue"
MOTIF_PERSONNE_NON_ACTIVE = "personne_non_active"
MOTIF_APPARTENANCE_NON_ACTIVE = "appartenance_non_active"
MOTIF_DOMAINE_NON_AUTORISE = "domaine_non_autorise"
MOTIF_COMPTE_NON_ACTIF = "compte_non_actif"

MOTIFS = (
    MOTIF_LIEN_EMIS,
    MOTIF_ADRESSE_INCONNUE,
    MOTIF_PERSONNE_NON_ACTIVE,
    MOTIF_APPARTENANCE_NON_ACTIVE,
    MOTIF_DOMAINE_NON_AUTORISE,
    MOTIF_COMPTE_NON_ACTIF,
)

#  Chemin de la page qui CONSOMME le lien. Il est ici, en un seul endroit, parce
#  que `T4` -- qui l'implemente -- et `T11` -- qui construit la page -- doivent
#  employer la meme valeur. Deux copies divergeraient, et le lien enverrait sur
#  une page absente.
#
#  DERIVATION : le cahier §7.1 enumere « connexion » parmi les pages publiques, et
#  le §3 de la fiche du lot enumere les huit ecrans dont « confirmation de
#  demande » et « lien expire ou consomme ». Le sous-chemin `/lien` distingue la
#  page qui consomme de la page qui demande. Aucun document ne l'ecrit : c'est
#  une derivation, declaree.
CHEMIN_DE_CONSOMMATION = "/connexion/lien"

#  Le NOM du parametre de requete. `journal.py` l'a anticipe des `T4` du LOT 1 --
#  « Un magic link du LOT 3 y passera : `?token=...` » -- et la barriere de
#  masquage de `packages/observabilite` porte deja `[?&](token|jeton|code|magic)=`.
#  Ce n'est donc pas un choix, c'est une anticipation ecrite.
PARAMETRE_DE_JETON = "token"


@dataclasses.dataclass(frozen=True)
class Demande:
    """Resultat interne d'une demande. **Ne sort jamais tel quel de l'API.**

    `lien` et `destinataire` sont non nuls **ensemble** ou nuls ensemble : soit un
    lien a ete emis et il y a quelqu'un a qui l'envoyer, soit rien n'a ete emis.
    """

    motif: str
    lien: str | None = None
    destinataire: str | None = None
    personne: uuid.UUID | None = None

    @property
    def un_lien_a_ete_emis(self) -> bool:
        return self.lien is not None


def _tracer(
    connexion: Connection,
    *,
    instant: dt.datetime,
    motif: str,
    personne: uuid.UUID | None,
    empreinte_origine: str | None,
) -> None:
    """Consigner la demande dans `auth_event` — modele §10.6, « magic link demande ».

    **L'evenement est ecrit dans TOUS les cas, y compris pour une adresse
    inconnue.** `auth_event.person_id` est nullable exactement pour cela : `T2` du
    LOT 3 l'a pose, « un echec sur une adresse inconnue doit pouvoir etre trace
    sans rattacher l'evenement a une personne inexistante ».

    **`detail` ne porte QUE le motif interne** -- jamais l'adresse demandee. Le
    §10.6 exclut les donnees sensibles, et consigner une adresse ABSENTE de la
    base creerait une donnee personnelle que la plateforme n'avait pas.

    Ne consigne pas non plus le jeton ni son empreinte : le §10.3 interdit « aucun
    lien complet dans les logs ou l'audit », et une empreinte n'apporterait rien
    a un audit -- `magic_link_request` la porte deja.

    Le type des sept est `MAGIC_LINK_REQUESTED` dans tous les cas : la demande a
    bien eu lieu. **Les six autres types du §10.6 relevent de `T12`**, qui porte
    l'audit complet et son controle d'exhaustivite.
    """
    connexion.execute(
        text(
            "INSERT INTO auth_event "
            "(event_type, occurred_at, person_id, request_origin_hash, detail) "
            "VALUES (:type_evenement, :survenu_a, :personne, :origine, :detail)"
        ),
        {
            "type_evenement": TypeEvenementAuth.MAGIC_LINK_REQUESTED.value,
            "survenu_a": instant,
            "personne": personne,
            "origine": empreinte_origine,
            "detail": motif,
        },
    )


def _domaine_de(adresse_normalisee: str) -> str:
    """Partie droite de l'arobase, ou chaine vide si l'adresse n'en a pas.

    La contrainte `email_normalise_plausible` garantit qu'une adresse EN BASE
    porte une arobase ailleurs qu'en premiere position. Cette fonction est
    neanmoins defensive : elle recoit aussi l'entree de l'appelant, qui n'est pas
    contrainte.
    """
    _, separateur, domaine = adresse_normalisee.partition("@")
    return domaine if separateur else ""


def _domaine_est_autorise(
    connexion: Connection, *, domaine: str, entite: uuid.UUID, instant: dt.datetime
) -> bool:
    """Le domaine autorise-t-il cette entite, a cet instant ?

    Trois exigences simultanees, et chacune vient du §5.4 :
      - `active`, « controle l'usage lors de l'authentification » ;
      - la periode `[starts_at, ends_at)` contient l'instant ;
      - le domaine est GLOBAL (`entity_id IS NULL`) ou celui de CETTE entite.
    """
    if not domaine:
        return False
    trouve = connexion.execute(
        text(
            "SELECT 1 FROM allowed_email_domain "
            "WHERE domain = :domaine AND active IS TRUE "
            "  AND period @> :instant_periode "
            "  AND (entity_id IS NULL OR entity_id = :entite) "
            "LIMIT 1"
        ),
        #  Deux noms de parametre DISTINCTS pour l'instant et pour l'entite, et
        #  `:instant_periode` n'est pas reutilise ailleurs dans cette requete :
        #  un meme parametre lie a deux colonnes de types differents rend
        #  « inconsistent types deduced for parameter », et le message ne nomme ni
        #  la table ni la colonne. Lecon `T11-*` du LOT 2, §7.25.
        {"domaine": domaine, "instant_periode": instant, "entite": entite},
    ).scalar_one_or_none()
    return trouve is not None


def _compte_bloquant(connexion: Connection, personne: uuid.UUID) -> str | None:
    """Etat du compte `EMPLOYEE_MAGIC_LINK` s'il existe et n'est PAS `active`.

    Rend `None` quand le compte est actif **ou quand il n'existe pas** : voir
    l'asymetrie declaree en tete de module.
    """
    etat = connexion.execute(
        text(
            "SELECT state FROM user_account "
            "WHERE person_id = :personne AND account_type = :type_compte "
            "LIMIT 1"
        ),
        {"personne": personne, "type_compte": TypeCompte.EMPLOYEE_MAGIC_LINK.value},
    ).scalar_one_or_none()
    if etat is None or etat == EtatCompte.ACTIVE.value:
        return None
    return str(etat)


def demander_un_magic_link(
    connexion: Connection,
    *,
    adresse: str,
    instant: dt.datetime,
    base_publique: str,
    empreinte_origine: str | None = None,
) -> Demande:
    """Instruire une demande de magic link, et tracer son resultat.

    **L'appelant ne doit RIEN deduire du motif rendu autre que « faut-il
    envoyer un e-mail ».** Toute autre exploitation le ferait diverger de la
    reponse generique.

    Args:
        connexion: connexion ouverte, dans une transaction que l'appelant valide.
        adresse: l'adresse telle que l'appelant l'a saisie. Aucune validation de
            forme : une adresse mal formee suit le meme chemin qu'une adresse
            inconnue, ce qui evite un second gabarit de reponse.
        instant: l'horodatage de la demande. **Injecte, jamais lu ici** : le
            §6 de la fiche l'exige, un test qui dormirait 15 minutes serait
            inutilisable en integration continue.
        base_publique: `PUBLIC_BASE_URL`, sans barre finale.
        empreinte_origine: valeur minimisee du §10.3, ou `None`.

    Returns:
        La `Demande`, dont `lien` vaut `None` quand rien ne doit etre envoye.
    """
    normalisee = normaliser_email(adresse)

    personne = connexion.execute(
        text(
            "SELECT id, email, account_state FROM person WHERE email_normalized = :adresse LIMIT 1"
        ),
        {"adresse": normalisee},
    ).one_or_none()

    if personne is None:
        _tracer(
            connexion,
            instant=instant,
            motif=MOTIF_ADRESSE_INCONNUE,
            personne=None,
            empreinte_origine=empreinte_origine,
        )
        return Demande(motif=MOTIF_ADRESSE_INCONNUE)

    identifiant, affichage, etat_personne = personne

    def refus(motif: str) -> Demande:
        _tracer(
            connexion,
            instant=instant,
            motif=motif,
            personne=identifiant,
            empreinte_origine=empreinte_origine,
        )
        return Demande(motif=motif, personne=identifiant)

    #  Modele §10.3 : « Personne ACTIVE existante ».
    if etat_personne != EtatPersonne.ACTIVE.value:
        return refus(MOTIF_PERSONNE_NON_ACTIVE)

    #  Cahier §7.2 : « son appartenance doit etre active ». `archived` est l'un
    #  des trois etats que ce filtre ecarte, et c'est le controle §30.11 du
    #  modele : « un profil archive ne recoit pas de magic link ».
    appartenance = connexion.execute(
        text(
            "SELECT entity_id FROM entity_membership "
            "WHERE person_id = :personne AND membership_state = :etat_appartenance "
            "LIMIT 1"
        ),
        {"personne": identifiant, "etat_appartenance": EtatAppartenance.ACTIVE.value},
    ).scalar_one_or_none()
    if appartenance is None:
        return refus(MOTIF_APPARTENANCE_NON_ACTIVE)

    #  Cahier §7.2 : « son adresse doit appartenir a un domaine autorise ».
    if not _domaine_est_autorise(
        connexion,
        domaine=_domaine_de(normalisee),
        entite=appartenance,
        instant=instant,
    ):
        return refus(MOTIF_DOMAINE_NON_AUTORISE)

    #  La cinquieme condition, derivee et declaree en tete de module.
    if _compte_bloquant(connexion, identifiant) is not None:
        return refus(MOTIF_COMPTE_NON_ACTIF)

    #  --- Emission -------------------------------------------------------
    #
    #  L'INVALIDATION VIENT D'ABORD, ET LA BASE L'EXIGE. L'index partiel refuse
    #  un second lien actif : sans cet `UPDATE`, l'`INSERT` suivant echouerait.
    connexion.execute(
        text(
            "UPDATE magic_link_request SET invalidated_at = :instant_invalidation "
            "WHERE person_id = :personne "
            "  AND used_at IS NULL AND invalidated_at IS NULL"
        ),
        {"instant_invalidation": instant, "personne": identifiant},
    )

    jeton = engendrer_jeton_magic_link()
    connexion.execute(
        text(
            "INSERT INTO magic_link_request "
            "(person_id, token_hash, requested_at, expires_at, request_origin_hash) "
            "VALUES (:personne, :empreinte, :demande_a, :expire_a, :origine)"
        ),
        {
            "personne": identifiant,
            "empreinte": empreinte_de_jeton(jeton),
            "demande_a": instant,
            #  EXACTEMENT quinze minutes : la contrainte
            #  `expiration_a_quinze_minutes` exige l'egalite, pas une borne.
            "expire_a": instant + dt.timedelta(minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK),
            "origine": empreinte_origine,
        },
    )

    _tracer(
        connexion,
        instant=instant,
        motif=MOTIF_LIEN_EMIS,
        personne=identifiant,
        empreinte_origine=empreinte_origine,
    )

    lien = f"{base_publique.rstrip('/')}{CHEMIN_DE_CONSOMMATION}?{PARAMETRE_DE_JETON}={jeton}"
    #  Le destinataire est `person.email`, la valeur d'AFFICHAGE du §6.1 -- la
    #  casse que la personne emploie pour elle-meme -- et non la forme
    #  normalisee, ni la saisie de l'appelant. Employer la saisie enverrait le
    #  lien a la casse fournie par le demandeur, qui n'est pas forcement la
    #  sienne.
    return Demande(
        motif=MOTIF_LIEN_EMIS, lien=lien, destinataire=str(affichage), personne=identifiant
    )


# ===========================================================================
#  LA CONSOMMATION — LOT 3, sous-etape `T4`, story `MVP-L03-US002`
# ===========================================================================
#
#  L'USAGE UNIQUE EST UNE COURSE, PAS UNE VERIFICATION
#
#    `T2` du LOT 3 l'avait annonce : « l'usage unique est une regle de PROCESSUS :
#    `used_at` ne se pose qu'une fois, ce qu'aucune contrainte de ligne
#    n'exprime ». C'est vrai, et cela ne dit pas encore comment le porter.
#
#    **Lire puis ecrire ne suffit PAS.** Deux requetes concurrentes portant le
#    meme jeton liraient toutes deux `used_at IS NULL`, et toutes deux
#    poursuivraient : le lien serait consomme DEUX fois, et le second usage
#    reussirait. Un lien de connexion rejouable est un contournement
#    d'authentification, pas un defaut de confort.
#
#    La consommation est donc un **compare-et-pose atomique** : un seul `UPDATE`
#    conditionnel, dont le nombre de lignes affectees EST le verdict.
#    PostgreSQL verrouille la ligne : la seconde transaction attend, puis ne
#    trouve plus de ligne a mettre a jour. **Un test l'eprouve sur deux
#    connexions reelles**, et sans lui cette propriete ne serait qu'une intention.
#
#  UN SEUL GABARIT D'ECHEC, ET C'EST UNE DERIVATION DECLAREE
#
#    Jeton inconnu, expire, deja consomme, invalide par un lien plus recent : les
#    quatre rendent le MEME refus. Ce n'est pas une precaution vague -- le §3 de
#    la fiche du lot enumere les huit ecrans de `T11`, et il en prevoit **UNE
#    SEULE** pour « lien expire **ou** consomme ». L'API n'a donc pas a
#    distinguer ce que l'interface ne distingue pas.
#
#  CE QUE LA CONSOMMATION NE FAIT PAS, ET IL FAUT LE LIRE DEUX FOIS
#
#    **ELLE N'AUTHENTIFIE PERSONNE.** Aucune session, aucun cookie, aucun jeton
#    rendu : `user_session` et les trois attributs de cookie du cahier §7.4
#    relevent de `T6`, story `US004`, dont les criteres sont ecrits. Cette
#    fonction etablit qu'un porteur de jeton valide EST une personne donnee, et
#    rend son identifiant a son appelant. **Rien de plus, et surtout rien qui
#    ressemble a un acces.**


@dataclasses.dataclass(frozen=True)
class Consommation:
    """Resultat d'une consommation. `personne` est non nul si et seulement si le
    jeton etait valide."""

    motif: str
    personne: uuid.UUID | None = None

    @property
    def reussie(self) -> bool:
        return self.personne is not None


MOTIF_CONSOMME = "lien_consomme"
MOTIF_LIEN_REFUSE = "lien_refuse"

MOTIFS_DE_CONSOMMATION = (MOTIF_CONSOMME, MOTIF_LIEN_REFUSE)


def consommer_un_magic_link(
    connexion: Connection,
    *,
    jeton: str,
    instant: dt.datetime,
    empreinte_origine: str | None = None,
) -> Consommation:
    """Consommer un magic link, une fois et une seule.

    **LE VERDICT EST LE NOMBRE DE LIGNES AFFECTEES PAR UN SEUL `UPDATE`.** Toutes
    les conditions -- existence, non-consommation, non-invalidation, non-expiration
    -- sont dans sa clause `WHERE`. Les evaluer avant, dans un `SELECT` separe,
    ouvrirait la fenetre de course que cette forme ferme.

    Args:
        connexion: connexion ouverte, dans une transaction que l'appelant valide.
        jeton: le jeton tel que le porteur le presente. Seule son empreinte
            touche la base.
        instant: l'horodatage de la tentative. **Injecte** : le §6 de la fiche
            l'exige, un test qui dormirait quinze minutes serait inutilisable en
            integration continue.
        empreinte_origine: valeur minimisee du §10.3, ou `None`.

    Returns:
        La `Consommation`. `personne` vaut `None` sur tout refus, sans jamais
        dire lequel des quatre cas s'est produit.
    """
    #  L'empreinte, jamais le jeton : le §10.3 ecrit « hash uniquement ».
    empreinte = empreinte_de_jeton(jeton)

    #  UN SEUL `UPDATE`, ET SA CLAUSE `WHERE` PORTE TOUTES LES CONDITIONS.
    #
    #    used_at IS NULL         -- usage unique, §10.3
    #    invalidated_at IS NULL  -- « le dernier lien invalide les precedents »
    #    expires_at > :instant   -- « 15 minutes apres emission »
    #
    #  `expires_at > instant` et non `>=` : a l'instant exact de l'expiration, le
    #  lien est expire. La borne est donc semi-ouverte, comme les plages du socle.
    personne = connexion.execute(
        text(
            "UPDATE magic_link_request SET used_at = :instant_usage "
            "WHERE token_hash = :empreinte "
            "  AND used_at IS NULL "
            "  AND invalidated_at IS NULL "
            "  AND expires_at > :instant_expiration "
            "RETURNING person_id"
        ),
        {
            #  DEUX NOMS DE PARAMETRE POUR LE MEME INSTANT, et ce n'est pas du
            #  zele : un parametre lie employe pour deux colonnes rend
            #  « inconsistent types deduced for parameter », et le message ne
            #  nomme ni la table ni la colonne. Lecon `T11` du LOT 2, §7.25.
            "instant_usage": instant,
            "instant_expiration": instant,
            "empreinte": empreinte,
        },
    ).scalar_one_or_none()

    if personne is None:
        #  **AUCUNE PERSONNE A RATTACHER, ET C'EST NORMAL** : un jeton inconnu
        #  n'en designe aucune. `auth_event.person_id` est nullable exactement
        #  pour ce cas, `T2` l'a pose.
        #
        #  Le type est `LOGIN_FAILURE` : le §10.6 declare « echec », et une
        #  tentative de consommation refusee EST un echec de connexion. Employer
        #  `MAGIC_LINK_USED` serait affirmer un usage qui n'a pas eu lieu.
        _tracer_consommation(
            connexion,
            instant=instant,
            type_evenement=TypeEvenementAuth.LOGIN_FAILURE,
            motif=MOTIF_LIEN_REFUSE,
            personne=None,
            empreinte_origine=empreinte_origine,
        )
        return Consommation(motif=MOTIF_LIEN_REFUSE)

    identifiant = uuid.UUID(str(personne))
    _tracer_consommation(
        connexion,
        instant=instant,
        type_evenement=TypeEvenementAuth.MAGIC_LINK_USED,
        motif=MOTIF_CONSOMME,
        personne=identifiant,
        empreinte_origine=empreinte_origine,
    )
    #  PAS de `LOGIN_SUCCESS` ici, et c'est une precision, pas un oubli : rien
    #  n'est encore connecte. `T6` cree la session, et c'est elle qui pourra
    #  legitimement tracer un succes de connexion.
    return Consommation(motif=MOTIF_CONSOMME, personne=identifiant)


def _tracer_consommation(
    connexion: Connection,
    *,
    instant: dt.datetime,
    type_evenement: TypeEvenementAuth,
    motif: str,
    personne: uuid.UUID | None,
    empreinte_origine: str | None,
) -> None:
    """Consigner une tentative de consommation — modele §10.6.

    **`detail` ne porte QUE le motif interne**, jamais le jeton ni son empreinte.
    Le §10.3 interdit « aucun lien complet dans les logs **ou l'audit** », et une
    empreinte n'apporterait rien : `magic_link_request` la porte deja.
    """
    connexion.execute(
        text(
            "INSERT INTO auth_event "
            "(event_type, occurred_at, person_id, request_origin_hash, detail) "
            "VALUES (:type_evenement, :survenu_a, :personne, :origine, :detail)"
        ),
        {
            "type_evenement": type_evenement.value,
            "survenu_a": instant,
            "personne": personne,
            "origine": empreinte_origine,
            "detail": motif,
        },
    )


# ===========================================================================
#  LE COMPTE ADMINISTRATEUR LOCAL — LOT 3, `T5`, story `MVP-L03-US003`
# ===========================================================================
#
#  LE VERROUILLAGE EST UNE COURSE, COMME L'USAGE UNIQUE DE `T4`
#
#    Lire `failed_login_count`, l'incrementer, puis decider laisserait trois
#    tentatives simultanees lire la meme valeur et n'en compter qu'une : le
#    compteur avancerait de 1 au lieu de 3, et le verrouillage n'arriverait
#    jamais. C'est exactement la classe de defaut que `T4` a mesuree, et la
#    parade est la meme -- **un seul `UPDATE ... RETURNING`**, dont la valeur
#    rendue est deja la valeur incrementee.
#
#  LES DEUX NOMBRES VIENNENT DE LA MEME PHRASE DU CAHIER, ET NE SONT PAS INVENTES
#
#    §20.2 : « **5 echecs administrateur en 15 minutes** : alerte ». Le cahier y
#    parle d'ALERTE ; le verrouillage du §7.5 et la colonne `locked_until` du
#    §10.1 n'ont **aucun** seuil ecrit, et aucune duree.
#
#    Les deux valeurs du verrou reutilisent donc les deux nombres deja ecrits,
#    plutot que d'en inventer : **5 echecs**, fenetre de **15 minutes**, verrou de
#    **15 minutes**. C'est le §6.5 -- reutiliser ce qui est ecrit vaut mieux
#    qu'inventer une valeur plausible.
#
#    **ET LE VERROU SE RELACHE SEUL**, ce qui est la parade au risque nomme au §7
#    de la fiche : « le verrouillage administrateur bloque Jonathan lui-meme ».
#    Aucun verrou definitif, donc aucune intervention obligatoire -- et
#    `make admin-local` deverrouille immediatement si besoin.
#
#  UN SEUL GABARIT D'ECHEC, ET C'EST LE MEME PARTI QUE `T3` ET `T4`
#
#    Compte inconnu, mot de passe faux, compte verrouille, compte desactive : les
#    quatre rendent le meme refus. L'operateur lit la cause dans `auth_event` ;
#    l'appelant, lui, n'apprend rien -- ni qu'une adresse porte un compte
#    administrateur, ni qu'il a reussi a le verrouiller.


#  §20.2, litteralement. Ces deux constantes ne sont pas configurables : les
#  rendre reglables inviterait a les abaisser, et le cahier les ecrit.
ECHECS_AVANT_VERROUILLAGE = 5
MINUTES_DE_FENETRE_D_ECHECS = 15
MINUTES_DE_VERROUILLAGE = 15

MOTIF_CONNEXION_REUSSIE = "connexion_reussie"
MOTIF_IDENTIFIANTS_REFUSES = "identifiants_refuses"
MOTIF_COMPTE_VERROUILLE = "compte_verrouille"
MOTIF_COMPTE_DESACTIVE = "compte_desactive"
MOTIF_AUCUN_COMPTE_ADMIN = "aucun_compte_admin"
MOTIF_AUCUN_MOT_DE_PASSE = "aucun_mot_de_passe_actif"

MOTIFS_DE_CONNEXION = (
    MOTIF_CONNEXION_REUSSIE,
    MOTIF_IDENTIFIANTS_REFUSES,
    MOTIF_COMPTE_VERROUILLE,
    MOTIF_COMPTE_DESACTIVE,
    MOTIF_AUCUN_COMPTE_ADMIN,
    MOTIF_AUCUN_MOT_DE_PASSE,
)


@dataclasses.dataclass(frozen=True)
class Connexion:
    """Resultat d'une tentative de connexion administrateur.

    `compte` est non nul si et seulement si la tentative a REUSSI.
    """

    motif: str
    compte: uuid.UUID | None = None
    personne: uuid.UUID | None = None
    #  §10.2 : « `must_change` ». L'appelant doit pouvoir imposer un changement
    #  immediat, et c'est la seule information que la reussite ajoute.
    changement_exige: bool = False
    #  Rendu pour information : `T6` s'en servira, et cela evite une seconde
    #  requete. Il ne sort JAMAIS de l'API.
    parametres_a_durcir: bool = False

    @property
    def reussie(self) -> bool:
        return self.compte is not None


def _compte_administrateur(
    connexion: Connection, adresse_normalisee: str
) -> tuple[uuid.UUID, uuid.UUID, str, int, dt.datetime | None] | None:
    """Le compte `ADMIN_LOCAL` d'une adresse, ou `None`.

    Une seule requete, jointe sur `person` : le compte est designe par une
    adresse, et `user_account` n'en porte pas -- le §6.1 interdit de la dupliquer.
    """
    ligne = connexion.execute(
        text(
            "SELECT u.id, u.person_id, u.state, u.failed_login_count, u.locked_until "
            "FROM user_account u JOIN person p ON p.id = u.person_id "
            "WHERE p.email_normalized = :adresse AND u.account_type = :type_compte "
            "LIMIT 1"
        ),
        {"adresse": adresse_normalisee, "type_compte": TypeCompte.ADMIN_LOCAL.value},
    ).one_or_none()
    if ligne is None:
        return None
    return (
        uuid.UUID(str(ligne[0])),
        uuid.UUID(str(ligne[1])),
        str(ligne[2]),
        int(ligne[3]),
        ligne[4],
    )


def _enregistrer_un_echec(
    connexion: Connection, compte: uuid.UUID, instant: dt.datetime
) -> tuple[int, bool]:
    """Compter l'echec et verrouiller si le seuil est atteint, EN UNE SEULE fois.

    **UN SEUL `UPDATE`, ET SA VALEUR RENDUE EST DEJA LA VALEUR INCREMENTEE.** Lire
    puis ecrire laisserait trois tentatives simultanees lire la meme valeur et
    n'en compter qu'une : le compteur avancerait de 1 au lieu de 3, et le verrou
    n'arriverait jamais. C'est la lecon de `T4`, transposee.

    La FENETRE est portee par le meme `UPDATE` : un compteur qui ne se remettrait
    jamais a zero finirait par verrouiller un administrateur pour cinq echecs
    etales sur six mois, ce qui n'est pas ce que « 5 echecs en 15 minutes » dit.
    `last_login_at` ne convient pas comme borne -- il marque les REUSSITES -- donc
    la fenetre s'appuie sur `updated_at`, qui est la date du dernier echec compte.

    Returns:
        `(compteur, verrouille)`.
    """
    ligne = connexion.execute(
        text(
            "UPDATE user_account SET "
            #  Hors fenetre, le compteur REPART A 1 : c'est ce nouvel echec.
            "  failed_login_count = CASE "
            "    WHEN updated_at < :debut_de_fenetre THEN 1 "
            "    ELSE failed_login_count + 1 END, "
            "  locked_until = CASE "
            "    WHEN (CASE WHEN updated_at < :debut_de_fenetre THEN 1 "
            "               ELSE failed_login_count + 1 END) >= :seuil "
            "    THEN :fin_de_verrou ELSE locked_until END, "
            "  updated_at = :instant_echec "
            "WHERE id = :compte "
            "RETURNING failed_login_count, locked_until"
        ),
        {
            "debut_de_fenetre": instant - dt.timedelta(minutes=MINUTES_DE_FENETRE_D_ECHECS),
            "seuil": ECHECS_AVANT_VERROUILLAGE,
            "fin_de_verrou": instant + dt.timedelta(minutes=MINUTES_DE_VERROUILLAGE),
            "instant_echec": instant,
            "compte": compte,
        },
    ).one()
    compteur = int(ligne[0])
    verrou = ligne[1]
    return compteur, verrou is not None and verrou > instant


def _reussite(connexion: Connection, compte: uuid.UUID, instant: dt.datetime) -> None:
    """Marquer la reussite : compteur a zero, verrou leve, derniere connexion.

    Remettre le compteur a zero n'est pas cosmetique : sans cela, quatre echecs
    suivis d'une reussite laisseraient le compte a un echec du verrou.
    """
    connexion.execute(
        text(
            "UPDATE user_account SET failed_login_count = 0, locked_until = NULL, "
            "  last_login_at = :instant_connexion, updated_at = :instant_maj "
            "WHERE id = :compte"
        ),
        {"instant_connexion": instant, "instant_maj": instant, "compte": compte},
    )


def authentifier_un_administrateur(
    connexion: Connection,
    *,
    adresse: str,
    mot_de_passe: str,
    instant: dt.datetime,
    empreinte_origine: str | None = None,
) -> Connexion:
    """Authentifier un compte `ADMIN_LOCAL`, et compter les echecs.

    **CETTE FONCTION N'OUVRE AUCUNE SESSION.** Elle etablit que le porteur des
    identifiants EST le titulaire du compte, et rend son identifiant. La session
    releve de `T6`, story `US004`.

    Args:
        connexion: connexion ouverte, transaction validee par l'appelant.
        adresse: l'adresse saisie. Aucune validation de forme, meme motif qu'en
            `T3` : un second gabarit de reponse serait un oracle.
        mot_de_passe: le mot de passe saisi. **Ne traverse que
            `app.auth.mots_de_passe`**, et n'est jamais journalise.
        instant: injecte. Le verrou et sa fenetre en dependent, et un test qui
            dormirait quinze minutes serait inutilisable.
        empreinte_origine: valeur minimisee du §10.3.
    """
    normalisee = normaliser_email(adresse)
    trouve = _compte_administrateur(connexion, normalisee)

    if trouve is None:
        #  **AUCUN COMPTE : ON NE COMPTE RIEN, ET IL N'Y A RIEN A COMPTER.** Le
        #  compteur vit sur `user_account` ; sans compte, il n'existe pas. La
        #  limitation par ORIGINE, qui couvre ce cas, releve de `T8`.
        _tracer_connexion(
            connexion,
            instant=instant,
            type_evenement=TypeEvenementAuth.LOGIN_FAILURE,
            motif=MOTIF_AUCUN_COMPTE_ADMIN,
            personne=None,
            compte=None,
            empreinte_origine=empreinte_origine,
        )
        return Connexion(motif=MOTIF_AUCUN_COMPTE_ADMIN)

    compte, personne, etat, _compteur, verrou = trouve

    def refus(motif: str, *, type_evenement: TypeEvenementAuth) -> Connexion:
        _tracer_connexion(
            connexion,
            instant=instant,
            type_evenement=type_evenement,
            motif=motif,
            personne=personne,
            compte=compte,
            empreinte_origine=empreinte_origine,
        )
        return Connexion(motif=motif, personne=personne)

    #  LE VERROU EST EXAMINE AVANT LE MOT DE PASSE, et l'ordre a un motif : un
    #  compte verrouille ne doit pas voir son compteur avancer a chaque tentative,
    #  sinon le verrou se prolongerait indefiniment sous une attaque -- ce qui
    #  transformerait le verrouillage en deni de service permanent contre le
    #  titulaire legitime.
    if verrou is not None and verrou > instant:
        return refus(MOTIF_COMPTE_VERROUILLE, type_evenement=TypeEvenementAuth.LOGIN_FAILURE)

    #  §10.1 : `state` vaut `active`, `locked` ou `disabled`. `disabled` est un
    #  refus definitif, que seul un administrateur leve.
    if etat != EtatCompte.ACTIVE.value:
        return refus(MOTIF_COMPTE_DESACTIVE, type_evenement=TypeEvenementAuth.LOGIN_FAILURE)

    identifiant = connexion.execute(
        text(
            "SELECT password_hash, algorithm, parameters, must_change "
            "FROM admin_password_credential "
            "WHERE user_account_id = :compte AND revoked_at IS NULL LIMIT 1"
        ),
        {"compte": compte},
    ).one_or_none()
    if identifiant is None:
        #  Le compte existe mais n'a aucun mot de passe actif. L'index partiel de
        #  `T2` garantit qu'il y en a **au plus** un ; il n'exige pas qu'il y en
        #  ait un.
        return refus(MOTIF_AUCUN_MOT_DE_PASSE, type_evenement=TypeEvenementAuth.LOGIN_FAILURE)

    empreinte, algorithme, parametres, changement_exige = identifiant
    if algorithme != ALGORITHME or not verifier(mot_de_passe, str(empreinte), dict(parametres)):
        #  **UN ALGORITHME INCONNU EST UN REFUS, PAS UNE ERREUR.** Le jour ou une
        #  empreinte portera un algorithme que ce code ne sait pas verifier, la
        #  connexion doit echouer proprement et l'audit le dire -- non lever une
        #  500 dont le message finirait dans un journal.
        compteur, verrouille = _enregistrer_un_echec(connexion, compte, instant)
        _tracer_connexion(
            connexion,
            instant=instant,
            type_evenement=TypeEvenementAuth.LOGIN_FAILURE,
            motif=MOTIF_IDENTIFIANTS_REFUSES,
            personne=personne,
            compte=compte,
            empreinte_origine=empreinte_origine,
        )
        if verrouille:
            #  §10.6 : « compte verrouille » est l'un des sept types. Il est
            #  trace SEPAREMENT de l'echec : ce sont deux faits distincts, et
            #  `T12` devra pouvoir compter les verrouillages sans compter les
            #  echecs.
            _tracer_connexion(
                connexion,
                instant=instant,
                type_evenement=TypeEvenementAuth.ACCOUNT_LOCKED,
                motif=f"{ECHECS_AVANT_VERROUILLAGE} echecs en "
                f"{MINUTES_DE_FENETRE_D_ECHECS} minutes",
                personne=personne,
                compte=compte,
                empreinte_origine=empreinte_origine,
            )
        _ = compteur
        return Connexion(motif=MOTIF_IDENTIFIANTS_REFUSES, personne=personne)

    _reussite(connexion, compte, instant)
    _tracer_connexion(
        connexion,
        instant=instant,
        type_evenement=TypeEvenementAuth.LOGIN_SUCCESS,
        motif=MOTIF_CONNEXION_REUSSIE,
        personne=personne,
        compte=compte,
        empreinte_origine=empreinte_origine,
    )
    return Connexion(
        motif=MOTIF_CONNEXION_REUSSIE,
        compte=compte,
        personne=personne,
        changement_exige=bool(changement_exige),
        parametres_a_durcir=parametres_a_durcir(dict(parametres)),
    )


def changer_le_mot_de_passe(
    connexion: Connection,
    *,
    compte: uuid.UUID,
    nouveau: str,
    instant: dt.datetime,
    empreinte_origine: str | None = None,
) -> None:
    """Revoquer l'identifiant actif et en poser un nouveau — modele §10.2.

    **L'ANCIEN EST REVOQUE, JAMAIS EFFACE**, et l'ordre est impose par l'index
    partiel de `T2` : `revoked_at IS NULL` doit rester unique par compte. Poser le
    nouveau avant de revoquer l'ancien ferait echouer l'insertion.

    « Aucun historique reversible » (§10.2) : la ligne revoquee ne garde que son
    empreinte, qui n'est pas reversible. Elle sert a savoir QUAND un mot de passe
    a change, ce que `changed_at` porte, et le §10.6 trace l'evenement.
    """
    connexion.execute(
        text(
            "UPDATE admin_password_credential SET revoked_at = :instant_revocation "
            "WHERE user_account_id = :compte AND revoked_at IS NULL"
        ),
        {"instant_revocation": instant, "compte": compte},
    )
    empreinte, parametres = hacher(nouveau)
    connexion.execute(
        text(
            "INSERT INTO admin_password_credential "
            "(user_account_id, password_hash, algorithm, parameters, changed_at, must_change) "
            "VALUES (:compte, :empreinte, :algorithme, :parametres, :change_a, FALSE)"
        ),
        {
            "compte": compte,
            "empreinte": empreinte,
            "algorithme": ALGORITHME,
            "parametres": json.dumps(parametres),
            "change_a": instant,
        },
    )
    personne = connexion.execute(
        text("SELECT person_id FROM user_account WHERE id = :compte"),
        {"compte": compte},
    ).scalar_one()
    _tracer_connexion(
        connexion,
        instant=instant,
        type_evenement=TypeEvenementAuth.ADMIN_PASSWORD_CHANGED,
        motif="mot_de_passe_change",
        personne=uuid.UUID(str(personne)),
        compte=compte,
        empreinte_origine=empreinte_origine,
    )


def _tracer_connexion(
    connexion: Connection,
    *,
    instant: dt.datetime,
    type_evenement: TypeEvenementAuth,
    motif: str,
    personne: uuid.UUID | None,
    compte: uuid.UUID | None,
    empreinte_origine: str | None,
) -> None:
    """Consigner un evenement de connexion — modele §10.6.

    **`detail` ne porte NI mot de passe, NI empreinte, NI adresse.** Le §10.6
    exclut les donnees sensibles, et le §28.2 interdit le secret sous toute forme.
    `user_account_id` est renseigne quand il est connu : c'est ce qui permettra a
    `T12` de compter les echecs PAR COMPTE.
    """
    connexion.execute(
        text(
            "INSERT INTO auth_event "
            "(event_type, occurred_at, person_id, user_account_id, request_origin_hash, detail) "
            "VALUES (:type_evenement, :survenu_a, :personne, :compte, :origine, :detail)"
        ),
        {
            "type_evenement": type_evenement.value,
            "survenu_a": instant,
            "personne": personne,
            "compte": compte,
            "origine": empreinte_origine,
            "detail": motif,
        },
    )
