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
