"""Routes du magic link — la demande, et sa consommation.

LOT 3 : `T3` a pose la demande (`MVP-L03-US001`), `T4` la consommation
(`MVP-L03-US002`).

    POST {prefixe}/auth/magic-link                demander un lien
    POST {prefixe}/auth/magic-link/consommation   le consommer, UNE FOIS

LE CRITERE EST UNE EGALITE, PAS UN REFUS

  Backlog `US001` : « la reponse est **generique** ». Le §7 de la fiche du lot le
  nomme comme risque de securite : « la reponse anti-enumeration diverge par un
  detail -- un temps de reponse, un en-tete ».

  Cette route n'a donc **qu'un seul gabarit de reponse** pour toute entree
  recevable : meme code, meme corps, memes en-têtes. Ce n'est pas obtenu en
  comparant deux chemins de code, c'est obtenu en n'en ayant qu'un -- le service
  rend un motif, la route l'ignore sauf pour decider s'il y a un e-mail a
  envoyer. C'est le §7.2 de la passation applique a une regle de securite :
  quand une classe d'erreur resiste a la vigilance, change de forme plutot que de
  promettre de l'attention.

  **AUCUNE VALIDATION DE FORME SUR L'ADRESSE**, et c'est deliberé. Une adresse
  jugee mal formee produirait un 422 au corps different : un attaquant y lirait
  « cette adresse a une forme acceptable » puis « cette adresse existe ». Une
  saisie fantaisiste suit donc exactement le meme chemin qu'une adresse inconnue.
  Seule l'absence du champ, ou un corps trop long, donne un 422 -- et cela ne
  depend que de la requete, jamais du contenu de la base.

L'ENVOI A LIEU APRES LA REPONSE, ET C'EST LE MEME CRITERE

  Attendre l'aller-retour SMTP avant de repondre ferait durer la reponse plus
  longtemps pour une adresse connue. `BackgroundTasks` remet donc l'envoi apres
  l'emission de la reponse.

  **RESIDUEL NOMME, ET NON MASQUE** : ce n'est pas un temps de reponse constant.
  Le chemin d'une adresse connue fait davantage de requetes SQL que celui d'une
  adresse inconnue. Le residuel est de l'ordre de la milliseconde, contre des
  dizaines pour un aller-retour SMTP ; il n'est pas ferme, et `T8` -- la
  limitation de debit -- est la sous-etape qui reduira l'exploitabilite d'une
  mesure statistique. Le taire aurait ete le pire choix, §7.20.

UN ECHEC D'ENVOI NE DOIT JAMAIS CHANGER LA REPONSE

  Si l'exception d'envoi remontait, une adresse connue avec un SMTP en panne
  rendrait 500 quand une adresse inconnue rendrait 202 : **la panne deviendrait
  l'oracle d'enumeration**. La tache d'arriere-plan capture donc son echec et le
  journalise.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth.courriel import EchecDEnvoi, envoyer
from app.auth.csrf import (
    EN_TETE_JETON,
    CsrfRefuse,
    controler_l_origine,
    controler_le_jeton,
    jeton_pour,
    origine_attendue,
)
from app.auth.idempotence import (
    EN_TETE_CLE,
    CleInvalide,
    MemoireIndisponible,
    controler_la_cle,
    liberer,
    reserver,
)
from app.auth.jetons import empreinte_d_origine
from app.auth.services import (
    Demande,
    authentifier_un_administrateur,
    changer_le_mot_de_passe,
    consommer_un_magic_link,
    demander_un_magic_link,
)
from app.auth.sessions import (
    empreinte_de_session,
    lire_et_rafraichir,
    ouvrir_une_session,
    revoquer,
)
from app.configuration.settings import Parametres
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

journal = logging.getLogger("app.auth")

#  Le corps est une CONSTANTE. Le construire a partir de la demande, meme pour un
#  detail, ouvrirait la porte a une divergence.
MESSAGE_GENERIQUE = (
    "Si cette adresse correspond a un profil actif et autorise, "
    "un lien de connexion vient d'y etre envoye. Il est valable 15 minutes."
)

#  Borne de la saisie. 320 est la longueur de `person.email` : au-dela, aucune
#  adresse ne pourrait correspondre, et accepter un corps sans borne serait une
#  surface de deni de service. Le refus qui en decoule ne depend QUE de la
#  requete.
LONGUEUR_MAXIMALE_ADRESSE = 320

#  LOT 3, T4 — LE REFUS EST UNIQUE, ET C'EST UNE DERIVATION DECLAREE.
#
#  Jeton inconnu, expire, deja consomme, invalide par un lien plus recent : les
#  quatre rendent CE message et ce code. Le §3 de la fiche du lot enumere les
#  huit ecrans de `T11` et n'en prevoit **qu'UN** pour « lien expire **ou**
#  consomme » : l'API n'a pas a distinguer ce que l'interface ne distingue pas.
#
#  Et le message ne cite JAMAIS le jeton. Un message d'erreur finit dans un
#  journal, une capture d'ecran ou un ticket — cahier §28.2, et le critere de
#  `US002` dit « sans exposer le jeton ».
CODE_LIEN_REFUSE = "lien_invalide"
MESSAGE_LIEN_REFUSE = (
    "Ce lien de connexion n'est plus valable. Il a peut-etre expire, deja servi, "
    "ou ete remplace par une demande plus recente. Demandez-en un nouveau."
)

#  La borne du jeton presente. `oml_` plus 43 caracteres en fait 47 ; la borne
#  est large pour ne pas dependre de la taille de l'alea, et elle existe pour
#  refuser un corps sans limite.
LONGUEUR_MAXIMALE_JETON = 256

#  LOT 3, T5 — LA CONNEXION ADMINISTRATEUR A AUSSI UN SEUL GABARIT D'ECHEC.
#
#  Compte inconnu, mot de passe faux, compte verrouille, compte desactive, compte
#  sans mot de passe actif : les cinq rendent CE message et ce code. Meme parti
#  que `T3` et `T4`, et deux motifs :
#
#    - un refus qui dirait « ce compte est verrouille » confirmerait qu'une
#      adresse porte un compte administrateur, ce qui est la premiere moitie
#      d'une attaque ;
#    - un refus qui dirait « verrouille » apprendrait aussi a l'attaquant qu'il a
#      REUSSI a verrouiller le titulaire legitime, donc que son deni de service
#      fonctionne.
#
#  L'operateur, lui, lit la cause exacte dans `auth_event` — six motifs distincts.
CODE_CONNEXION_REFUSEE = "identifiants_refuses"
MESSAGE_CONNEXION_REFUSEE = (
    "Connexion impossible. Verifiez votre adresse et votre mot de passe. "
    "Apres plusieurs tentatives infructueuses, l'acces est suspendu quinze minutes."
)

#  **CE PLANCHER N'EST PAS DERIVE DU CORPUS, ET IL FAUT LE DIRE.**
#
#  Aucun document du projet n'ecrit de politique de mot de passe : le cahier §7.3
#  parle du STOCKAGE — « stocke de maniere securisee », « jamais en clair » — et
#  le §20.3 ne borne que `APP_SECRET_KEY`, qui est une cle machine. Le §8 de la
#  fiche du LOT 3 enumere quatre decisions a instruire, et **une politique de mot
#  de passe n'en fait pas partie** : personne ne l'avait vue.
#
#  Accepter un mot de passe d'un caractere serait pourtant contraire a tout le
#  reste du chapitre 7. Ce plancher est donc une **recommandation en attente
#  d'arbitrage**, `QO-118`, posee en UNE constante pour que la trancher soit une
#  ligne. Elle est declaree ici plutot que deguisee en decision : « une hypothese
#  deguisee en decision est pire qu'une case vide » (§6.5).
LONGUEUR_MINIMALE_MOT_DE_PASSE = 12

#  Borne haute : scrypt lit tout ce qu'on lui donne, et un corps sans limite est
#  une surface de deni de service — d'autant plus qu'un calcul coute 64 Mio.
LONGUEUR_MAXIMALE_MOT_DE_PASSE = 1024

#  LOT 3, T6 — LA SESSION A UN SEUL GABARIT DE REFUS, LUI AUSSI.
#
#  Jeton absent, jeton inconnu, session revoquee, duree absolue depassee,
#  inactivite depassee : les cinq rendent CE code et ce message. Les distinguer
#  apprendrait a un attaquant qu'un jeton a EXISTE, et lequel des deux delais
#  l'a emporte.
CODE_SESSION_REFUSEE = "session_invalide"
MESSAGE_SESSION_REFUSEE = (
    "Aucune session valide. Reconnectez-vous : une session expire apres sept jours "
    "sans activite, et trente jours au maximum."
)

#  LOT 3, T7 — LE REFUS CSRF A UN SEUL GABARIT, LUI AUSSI.
#
#  Origine etrangere, jeton absent, jeton invalide : les trois rendent CE code et
#  ce message. Distinguer « jeton absent » de « jeton invalide » dirait a un
#  attaquant s'il s'est approche, et le motif interne va a l'audit.
#
#  **403 ET NON 401.** Le §18.3 veut un format coherent ; le choix du code, lui,
#  porte du sens : 401 signifie « authentifie-toi », ce qui est faux ici -- une
#  session valide peut tres bien accompagner une requete CSRF refusee. 403 dit
#  « je sais qui tu es, et je refuse cette requete-la », ce qui est exact.
CODE_CSRF_REFUSE = "requete_refusee"
MESSAGE_CSRF_REFUSE = (
    "Cette requete a ete refusee par la protection contre les requetes forgees. "
    "Rechargez la page et recommencez."
)

CODE_IDEMPOTENCE_INVALIDE = "cle_idempotence_invalide"
CODE_MEMOIRE_INDISPONIBLE = "memoire_indisponible"
MESSAGE_MEMOIRE_INDISPONIBLE = (
    "La protection contre les doubles soumissions est momentanement indisponible. "
    "Reessayez dans un instant."
)

SUJET_DU_COURRIEL = "Votre lien de connexion eXalt Onboarding"

CORPS_DU_COURRIEL = """Bonjour,

Voici votre lien de connexion a eXalt Onboarding Digital :

{lien}

Ce lien est valable {minutes} minutes et ne peut servir qu'une seule fois.
Toute nouvelle demande annule le lien precedent.

Si vous n'avez pas demande ce lien, ignorez ce message : personne d'autre ne
peut s'en servir.

--
eXalt Onboarding Digital
"""


class DemandeDeMagicLink(BaseModel):
    """Corps de la demande. Un seul champ, et aucune validation de forme."""

    email: str = Field(max_length=LONGUEUR_MAXIMALE_ADRESSE)


class ReponseGenerique(BaseModel):
    """Reponse unique de la demande, quelle que soit l'issue reelle."""

    message: str


class ConnexionAdministrateur(BaseModel):
    """Corps d'une connexion administrateur.

    **AUCUNE VALIDATION DE FORME SUR L'ADRESSE**, meme motif qu'en `T3` : un 422
    sur une adresse jugee mal formee serait un premier oracle. Le mot de passe
    n'est borne que par le HAUT, et cette borne ne depend que de la requete.
    """

    email: str = Field(max_length=LONGUEUR_MAXIMALE_ADRESSE)
    mot_de_passe: str = Field(max_length=LONGUEUR_MAXIMALE_MOT_DE_PASSE)


class ChangementDeMotDePasse(BaseModel):
    """Corps d'un changement de mot de passe.

    **L'ANCIEN MOT DE PASSE EST EXIGE**, et ce n'est pas un confort : sans session
    — elles relevent de `T6` — c'est la SEULE preuve que l'appelant est le
    titulaire. Une route qui changerait un mot de passe sur la seule adresse
    serait une prise de controle de compte.
    """

    email: str = Field(max_length=LONGUEUR_MAXIMALE_ADRESSE)
    mot_de_passe_actuel: str = Field(max_length=LONGUEUR_MAXIMALE_MOT_DE_PASSE)
    nouveau_mot_de_passe: str = Field(
        min_length=LONGUEUR_MINIMALE_MOT_DE_PASSE,
        max_length=LONGUEUR_MAXIMALE_MOT_DE_PASSE,
    )


class ReponseDeSession(BaseModel):
    """Etat de la session courante — LOT 3, `T6`.

    **ELLE NE PORTE PAS LE JETON**, et c'est le point : le jeton vit dans un
    cookie `HttpOnly`, donc hors d'atteinte de tout JavaScript. Le rendre ici le
    remettrait a portee du navigateur, et le critere du §7.4 — « aucune donnee
    d'authentification durable dans `localStorage` » — deviendrait impossible a
    tenir : un frontend qui recoit un jeton finit par le stocker.
    """

    personne: uuid.UUID
    #  LOT 3, T7 — LE JETON ANTI-CSRF EST RENDU ICI, ET C'EST SANS DANGER.
    #
    #  Il doit etre LISIBLE par le frontend : c'est son objet, et un cookie
    #  `HttpOnly` le rendrait inutilisable. Il n'ouvre aucun acces a lui seul --
    #  il ne vaut qu'accompagne du cookie de session, qui reste `HttpOnly`. C'est
    #  le patron du double envoi.
    #
    #  **IL EST RENDU PAR LA ROUTE DE SESSION, non par la connexion**, et le
    #  motif est pratique : un frontend recharge la page, perd sa variable, et
    #  doit pouvoir reobtenir le jeton sans se reconnecter.
    jeton_csrf: str


class ReponseDeConnexion(BaseModel):
    """Reponse d'une connexion administrateur REUSSIE.

    **ELLE NE PORTE AUCUN ACCES**, comme la consommation de `T4` : ni cookie, ni
    jeton. `T6` attachera la session. `changement_exige` porte `must_change` du
    §10.2 : c'est la seule information que la reussite ajoute, et l'ecran de `T11`
    s'en servira pour imposer le changement avant toute autre action.
    """

    message: str
    personne: uuid.UUID
    changement_exige: bool


class ConsommationDeMagicLink(BaseModel):
    """Corps de la consommation.

    **LE JETON VOYAGE DANS LE CORPS, JAMAIS DANS L'URL**, et c'est le choix
    structurant de `T4` :

      - une chaine de requete finit dans l'historique du navigateur, dans un
        en-tete `Referer`, et dans tout journal d'acces d'un mandataire ;
      - `DEC-469` interdit deja de journaliser la chaine de requete, et
        `journal.py` ne l'ecrit pas -- mais cela protege NOS journaux, pas ceux
        d'un mandataire ni l'historique d'un poste.

    Le lien de l'e-mail porte bien le jeton en query string : c'est une page du
    frontend qu'il ouvre, et c'est elle qui appelle cette route avec le jeton en
    corps. La fenetre d'exposition est ainsi bornee au navigateur du destinataire.
    """

    token: str = Field(max_length=LONGUEUR_MAXIMALE_JETON)


class ReponseDeConsommation(BaseModel):
    """Reponse d'une consommation REUSSIE.

    **ELLE NE PORTE AUCUN ACCES**, et le dire est le point. Ni cookie, ni jeton,
    ni identifiant de session : `user_session` et les trois attributs du cahier
    §7.4 relevent de `T6`, story `US004`. Un porteur de jeton valide a prouve son
    identite ; il n'a pas encore de session.
    """

    message: str
    #  L'identifiant de la personne authentifiee. Le porteur du jeton **est**
    #  cette personne : le lui rendre ne divulgue rien qu'il ne sache deja, et
    #  `T6` en aura besoin pour attacher la session.
    personne: uuid.UUID


def origine_de_la_requete(requete: Request) -> str | None:
    """Origine a minimiser — modele §10.3, `request_origin_hash`.

    **POURQUOI PAS `request.client.host`, ET LA MESURE EST NETTE.** L'API n'est
    jointe que par Caddy (cahier §22.2, `DEC-460`) : `request.client.host` est donc
    l'adresse du conteneur Caddy, **la meme pour tout le monde**. Une valeur
    constante ne serait pas une origine : elle ferait de la limitation de `T8` un
    plafond global, et l'echec produirait exactement la meme observation que le
    succes -- quatrieme proposition du §7.0.

    **POURQUOI LE DERNIER ELEMENT DE `X-Forwarded-For`, ET NON LE PREMIER.** Caddy
    AJOUTE l'adresse de son pair a la fin de l'en-tete existant. Le premier
    element est donc fourni par le client et **forgeable a volonte** : s'en servir
    permettrait de contourner la limitation de debit en changeant d'en-tete a
    chaque requete. Le dernier est celui que notre mandataire a ecrit.

    LIMITE DE CONFIANCE, DITE : la valeur ne vaut que si l'API n'est joignable que
    par un mandataire de confiance. C'est le cas ici -- le service n'est pas
    publie sur l'hote. **`T8` doit reexaminer ce point**, et le LOT 13 aussi, ou
    un second mandataire pourrait s'intercaler.
    """
    transmise = requete.headers.get("x-forwarded-for")
    if transmise:
        elements = [element.strip() for element in transmise.split(",") if element.strip()]
        if elements:
            return elements[-1]
    return requete.client.host if requete.client else None


def _envoyer_le_lien(parametres: Parametres, demande: Demande) -> None:
    """Tache d'arriere-plan : remettre l'e-mail. **N'echoue jamais vers l'appelant.**"""
    if demande.lien is None or demande.destinataire is None:
        return
    try:
        envoyer(
            parametres,
            destinataire=demande.destinataire,
            sujet=SUJET_DU_COURRIEL,
            corps=CORPS_DU_COURRIEL.format(
                lien=demande.lien, minutes=parametres.MAGIC_LINK_TTL_MINUTES
            ),
        )
    except EchecDEnvoi as erreur:
        #  Le message de `EchecDEnvoi` ne porte ni destinataire, ni corps, ni
        #  lien : voir `courriel.py`. Il est donc journalisable tel quel.
        journal.error(
            "envoi du lien de connexion impossible",
            extra={"resultat": "echec", "code_erreur": str(erreur)},
        )


def routeur_authentification(parametres: Parametres) -> APIRouter:
    """Routeur de l'authentification, monte sous le prefixe versionne."""
    routeur = APIRouter(prefix="/auth", tags=["authentification"])

    @routeur.post(
        "/magic-link",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=ReponseGenerique,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Requete refusee par la protection contre les requetes forgees. "
                    "UNE SEULE forme pour trois causes : origine etrangere, jeton "
                    "absent, jeton invalide — les distinguer dirait a un attaquant "
                    "s'il s'est approche."
                )
            },
        },
        summary="Demander un lien de connexion",
        description=(
            "La reponse est identique que l'adresse existe ou non : le code, le corps "
            "et les en-tetes ne permettent pas de conclure a l'existence d'un compte."
        ),
    )
    def demander(
        corps: DemandeDeMagicLink,
        requete: Request,
        reponse: Response,
        taches: BackgroundTasks,
    ) -> ReponseGenerique:
        """Instruire la demande, puis rendre la reponse generique."""
        #  `no-store` : un lien de connexion ne doit pas etre servi depuis un
        #  cache, et l'en-tete est le MEME dans tous les cas -- il ne peut donc
        #  rien reveler.
        reponse.headers["Cache-Control"] = "no-store"
        #  LOT 3, T7 — route AMONT : l'origine seule, aucun jeton possible.
        _proteger_du_csrf(parametres, requete)
        #  **LA SEULE ROUTE DU LOT OU L'IDEMPOTENCE CHANGE QUELQUE CHOSE.** Un
        #  double clic envoie deux e-mails ET invalide le premier lien : l'effet
        #  double est visible par l'utilisateur, qui recoit deux messages dont un
        #  seul fonctionne.
        cle_reservee = _reserver_l_idempotence(parametres, requete, route="demande-magic-link")
        if cle_reservee == "":
            #  Cle deja vue : on rend la MEME reponse, sans reemettre. C'est le
            #  sens d'idempotent — et la reponse est de toute facon generique.
            return ReponseGenerique(message=MESSAGE_GENERIQUE)

        origine = origine_de_la_requete(requete)
        empreinte = (
            empreinte_d_origine(origine, parametres.APP_SECRET_KEY)
            if origine and parametres.APP_SECRET_KEY
            else None
        )

        #  UNE SEULE TRANSACTION. L'invalidation du lien precedent, l'insertion du
        #  nouveau et l'evenement d'audit sont indissociables : un lien insere
        #  sans son evenement serait un acces non trace.
        with moteur(parametres).begin() as connexion:
            demande = demander_un_magic_link(
                connexion,
                adresse=corps.email,
                instant=dt.datetime.now(tz=dt.UTC),
                base_publique=parametres.PUBLIC_BASE_URL,
                empreinte_origine=empreinte,
            )

        #  L'envoi vient APRES la reponse. Voir l'en-tete du module.
        if demande.un_lien_a_ete_emis:
            taches.add_task(_envoyer_le_lien, parametres, demande)
        elif cle_reservee:
            #  **AUCUN LIEN N'A ETE EMIS : LA CLE EST LIBEREE.** La garder
            #  bloquerait six heures une demande qui n'a rien produit — par
            #  exemple parce que le profil venait d'etre active entre-temps. Une
            #  cle reservee sur un non-effet est une porte fermee sur rien.
            liberer(parametres, route="demande-magic-link", cle=cle_reservee)

        #  Le motif ne sort pas. Il est deja dans `auth_event`, et le journal de
        #  requete du §28.1 ne porte que la route, la duree et le resultat.
        return ReponseGenerique(message=MESSAGE_GENERIQUE)

    @routeur.post(
        "/magic-link/consommation",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeConsommation,
        #  LE 400 EST DECLARE, ET CE N'EST PAS COSMETIQUE. FastAPI ne documente
        #  spontanement que le code de succes et le 422 de validation : un refus
        #  que le contrat annonce exploitable et que le schema ignore est
        #  exactement le defaut que `T10` du LOT 1 avait trouve sur le 503 de
        #  `/health/ready`. `test_contrat.py` a echoue ici avant que ce bloc
        #  n'existe, et c'est son role.
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "description": (
                    "Lien refuse. UNE SEULE forme pour quatre causes : jeton inconnu, "
                    "expire, deja consomme, ou invalide par une demande plus recente."
                )
            },
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Requete refusee par la protection contre les requetes forgees. "
                    "UNE SEULE forme pour trois causes : origine etrangere, jeton "
                    "absent, jeton invalide — les distinguer dirait a un attaquant "
                    "s'il s'est approche."
                )
            },
        },
        summary="Consommer un lien de connexion",
        description=(
            "Consomme le lien UNE FOIS. Un second usage, un lien expire, un lien "
            "invalide par une demande plus recente et un jeton inconnu rendent tous "
            "le MEME refus. La reponse ne porte AUCUN acces : la session releve de "
            "`T6`."
        ),
    )
    def consommer(
        corps: ConsommationDeMagicLink, requete: Request, reponse: Response
    ) -> ReponseDeConsommation:
        """Consommer le lien, et refuser tout ce qui n'est pas exactement valide."""
        #  `no-store` : une reponse de connexion ne doit jamais etre servie
        #  depuis un cache, ni conservee par un intermediaire.
        reponse.headers["Cache-Control"] = "no-store"
        #  LOT 3, T7 — route AMONT : l'origine seule. Un jeton anti-CSRF
        #  suppose une session pour le delivrer, et ces routes la precedent.
        #  Le changement de mot de passe exige de plus le mot de passe ACTUEL,
        #  ce qui est une preuve plus forte qu'un jeton.
        _proteger_du_csrf(parametres, requete)

        origine = origine_de_la_requete(requete)
        empreinte = (
            empreinte_d_origine(origine, parametres.APP_SECRET_KEY)
            if origine and parametres.APP_SECRET_KEY
            else None
        )

        #  UNE SEULE TRANSACTION : la pose de `used_at` et l'evenement d'audit
        #  sont indissociables. Un lien consomme sans trace serait un acces non
        #  journalise.
        instant = dt.datetime.now(tz=dt.UTC)
        jeton_de_session: str | None = None
        with moteur(parametres).begin() as connexion:
            consommation = consommer_un_magic_link(
                connexion,
                jeton=corps.token,
                instant=instant,
                empreinte_origine=empreinte,
            )
            if consommation.personne is not None:
                #  LOT 3, T6 — LA SESSION NAIT DANS LA MEME TRANSACTION que la
                #  consommation. Les separer laisserait un lien consomme sans
                #  session : le porteur aurait brule son jeton pour rien, et
                #  l'usage unique lui interdirait de recommencer.
                jeton_de_session, _ = ouvrir_une_session(
                    connexion,
                    personne=consommation.personne,
                    instant=instant,
                    jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
                )

        if consommation.personne is None:
            #  **LE MESSAGE NE CITE PAS LE JETON, ET LE `champ` NON PLUS.** Le
            #  format du §18.3 porte un `champ` : y mettre `token` nommerait le
            #  champ fautif sans jamais en donner la valeur, ce qui est utile au
            #  client et inoffensif.
            raise ErreurApplicative(
                code=CODE_LIEN_REFUSE,
                message=MESSAGE_LIEN_REFUSE,
                statut=status.HTTP_400_BAD_REQUEST,
                champ="token",
            )

        assert jeton_de_session is not None  # noqa: S101 — garanti par la branche ci-dessus
        _poser_le_cookie_de_session(parametres, reponse, jeton_de_session)
        return ReponseDeConsommation(
            message="Lien accepte. Vous etes connecte.",
            personne=consommation.personne,
        )

    @routeur.post(
        "/connexion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeConnexion,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "description": (
                    "Connexion refusee. UNE SEULE forme pour cinq causes : compte "
                    "inconnu, mot de passe faux, compte verrouille, compte desactive, "
                    "compte sans mot de passe actif."
                )
            },
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Requete refusee par la protection contre les requetes forgees. "
                    "UNE SEULE forme pour trois causes : origine etrangere, jeton "
                    "absent, jeton invalide — les distinguer dirait a un attaquant "
                    "s'il s'est approche."
                )
            },
        },
        summary="Se connecter avec un compte administrateur local",
        description=(
            "Cinq causes de refus rendent la MEME reponse : un refus qui les "
            "distinguerait revelerait qu'une adresse porte un compte administrateur, "
            "et qu'un verrouillage a reussi. La reponse ne porte AUCUN acces : la "
            "session releve de `T6`."
        ),
    )
    def connexion(
        corps: ConnexionAdministrateur, requete: Request, reponse: Response
    ) -> ReponseDeConnexion:
        """Authentifier un compte administrateur local — cahier §7.3."""
        reponse.headers["Cache-Control"] = "no-store"
        #  LOT 3, T7 — route AMONT : l'origine seule. Un jeton anti-CSRF
        #  suppose une session pour le delivrer, et ces routes la precedent.
        #  Le changement de mot de passe exige de plus le mot de passe ACTUEL,
        #  ce qui est une preuve plus forte qu'un jeton.
        _proteger_du_csrf(parametres, requete)
        empreinte = _empreinte_d_origine(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        jeton_de_session: str | None = None
        with moteur(parametres).begin() as connexion_bd:
            resultat = authentifier_un_administrateur(
                connexion_bd,
                adresse=corps.email,
                mot_de_passe=corps.mot_de_passe,
                instant=instant,
                empreinte_origine=empreinte,
            )
            if resultat.personne is not None and resultat.reussie:
                #  MEME TRANSACTION que l'authentification : un `last_login_at`
                #  pose sans session dirait qu'une connexion a eu lieu alors
                #  qu'aucun acces n'a ete accorde.
                jeton_de_session, _ = ouvrir_une_session(
                    connexion_bd,
                    personne=resultat.personne,
                    instant=instant,
                    jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
                )

        if resultat.personne is None or not resultat.reussie:
            #  **LE MESSAGE NE CITE NI L'ADRESSE NI LE MOTIF INTERNE.** Le motif
            #  est deja dans `auth_event`, ou l'operateur le lit.
            raise ErreurApplicative(
                code=CODE_CONNEXION_REFUSEE,
                message=MESSAGE_CONNEXION_REFUSEE,
                statut=status.HTTP_400_BAD_REQUEST,
            )

        assert jeton_de_session is not None  # noqa: S101 — garanti par la branche ci-dessus
        _poser_le_cookie_de_session(parametres, reponse, jeton_de_session)
        return ReponseDeConnexion(
            message="Identifiants acceptes.",
            personne=resultat.personne,
            changement_exige=resultat.changement_exige,
        )

    @routeur.post(
        "/mot-de-passe",
        status_code=status.HTTP_200_OK,
        response_model=ReponseGenerique,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "description": "Identifiants actuels refuses. Meme forme que la connexion."
            },
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Requete refusee par la protection contre les requetes forgees. "
                    "UNE SEULE forme pour trois causes : origine etrangere, jeton "
                    "absent, jeton invalide — les distinguer dirait a un attaquant "
                    "s'il s'est approche."
                )
            },
        },
        summary="Changer le mot de passe d'un compte administrateur local",
        description=(
            "Exige le mot de passe ACTUEL : sans session — elles relevent de `T6` — "
            "c'est la seule preuve que l'appelant est le titulaire. Le changement est "
            "audite, et l'ancien identifiant est revoque, jamais efface."
        ),
    )
    def changer_mot_de_passe(
        corps: ChangementDeMotDePasse, requete: Request, reponse: Response
    ) -> ReponseGenerique:
        """Changer le mot de passe apres re-authentification — modele §10.2."""
        reponse.headers["Cache-Control"] = "no-store"
        #  LOT 3, T7 — route AMONT : l'origine seule. Un jeton anti-CSRF
        #  suppose une session pour le delivrer, et ces routes la precedent.
        #  Le changement de mot de passe exige de plus le mot de passe ACTUEL,
        #  ce qui est une preuve plus forte qu'un jeton.
        _proteger_du_csrf(parametres, requete)
        empreinte = _empreinte_d_origine(parametres, requete)
        instant = dt.datetime.now(tz=dt.UTC)

        #  UNE SEULE TRANSACTION : la re-authentification, la revocation de
        #  l'ancien identifiant, la pose du nouveau et l'audit sont
        #  indissociables. Un mot de passe change sans trace serait une prise de
        #  controle non journalisee.
        with moteur(parametres).begin() as connexion_bd:
            resultat = authentifier_un_administrateur(
                connexion_bd,
                adresse=corps.email,
                mot_de_passe=corps.mot_de_passe_actuel,
                instant=instant,
                empreinte_origine=empreinte,
            )
            if resultat.compte is None:
                #  **LE MEME REFUS QUE LA CONNEXION**, et le meme code : un
                #  changement refuse ne doit pas se distinguer d'une connexion
                #  refusee, sinon cette route deviendrait l'oracle que l'autre
                #  n'est pas.
                raise ErreurApplicative(
                    code=CODE_CONNEXION_REFUSEE,
                    message=MESSAGE_CONNEXION_REFUSEE,
                    statut=status.HTTP_400_BAD_REQUEST,
                )
            changer_le_mot_de_passe(
                connexion_bd,
                compte=resultat.compte,
                nouveau=corps.nouveau_mot_de_passe,
                instant=instant,
                empreinte_origine=empreinte,
            )

        return ReponseGenerique(message="Mot de passe modifie.")

    @routeur.get(
        "/session",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeSession,
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": (
                    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie "
                    "absent, jeton inconnu, session revoquee, duree absolue depassee, "
                    "inactivite depassee."
                )
            }
        },
        summary="Lire la session courante",
        description=(
            "Valide le cookie ET rafraichit l'activite, en une seule operation atomique. "
            "Ne rend JAMAIS le jeton : il vit dans un cookie `HttpOnly`, hors d'atteinte "
            "de tout JavaScript."
        ),
    )
    def session_courante(requete: Request, reponse: Response) -> ReponseDeSession:
        """Lire et rafraichir la session — cahier §7.4, modele §10.4."""
        reponse.headers["Cache-Control"] = "no-store"
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)

        with moteur(parametres).begin() as connexion:
            etat = lire_et_rafraichir(
                connexion,
                jeton=jeton,
                instant=dt.datetime.now(tz=dt.UTC),
                jours_d_inactivite=parametres.SESSION_IDLE_DAYS,
            )

        if etat.personne is None:
            raise ErreurApplicative(
                code=CODE_SESSION_REFUSEE,
                message=MESSAGE_SESSION_REFUSEE,
                statut=status.HTTP_401_UNAUTHORIZED,
            )
        #  **CETTE ROUTE N'EXIGE AUCUN JETON, ET C'EST UN RESIDUEL NOMME.**
        #
        #  Elle ECRIT pourtant -- elle rafraichit `last_activity_at`. Trois
        #  raisons de ne pas la proteger par un jeton, et la premiere suffit :
        #
        #    1. **elle DELIVRE le jeton.** L'exiger d'elle serait circulaire : un
        #       frontend qui vient de recharger n'en a pas encore ;
        #    2. son effet porte sur la session de l'appelant lui-meme. Un site
        #       tiers qui la declencherait ne ferait que prolonger la session de
        #       sa victime — aucun gain ;
        #    3. c'est un `GET`, et `T7` protege les methodes qui modifient. Le
        #       fait qu'un `GET` ecrive est une entorse assumee du §7.4, et
        #       `T6` l'avait deja nommee.
        #
        #  **A REEXAMINER AU LOT 4**, quand des routes metier existeront : si le
        #  rafraichissement passe sur chaque requete, ce point disparait.
        assert jeton is not None  # noqa: S101 — garanti par la validation ci-dessus
        return ReponseDeSession(
            personne=etat.personne,
            jeton_csrf=jeton_pour(empreinte_de_session(jeton), parametres.APP_SECRET_KEY),
        )

    @routeur.post(
        "/deconnexion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseGenerique,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Requete refusee par la protection contre les requetes forgees. "
                    "UNE SEULE forme pour trois causes : origine etrangere, jeton "
                    "absent, jeton invalide — les distinguer dirait a un attaquant "
                    "s'il s'est approche."
                )
            },
        },
        summary="Se deconnecter",
        description=(
            "Revoque la session et retire le cookie. **Toujours 200**, meme sans session "
            "valide : un 404 ou un 401 apprendrait qu'un jeton a existe, et une "
            "deconnexion n'a de toute facon rien a refuser."
        ),
    )
    def deconnexion(requete: Request, reponse: Response) -> ReponseGenerique:
        """Revoquer la session courante — modele §10.4, `revoked_at`."""
        reponse.headers["Cache-Control"] = "no-store"
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        #  LOT 3, T7 — **LA SEULE ECRITURE DU LOT QUI EXIGE UN JETON**, parce
        #  qu'elle est la seule a disposer d'une session pour en deriver un.
        #
        #  Un site tiers qui deconnecte un utilisateur est une nuisance reelle,
        #  et elle est facile : `SameSite=lax` ne bloque pas tout. Le jeton la
        #  ferme.
        #
        #  **SANS COOKIE, AUCUN JETON N'EST EXIGE** : il n'y aurait rien a
        #  proteger, et exiger un jeton ferait echouer une deconnexion qui doit
        #  rendre 200 en toute circonstance.
        _proteger_du_csrf(parametres, requete, jeton_de_session=jeton if jeton else None)
        empreinte = _empreinte_d_origine(parametres, requete)

        with moteur(parametres).begin() as connexion:
            revoquer(
                connexion,
                jeton=jeton,
                instant=dt.datetime.now(tz=dt.UTC),
                empreinte_origine=empreinte,
            )

        #  **LE COOKIE EST RETIRE DANS TOUS LES CAS**, et la reponse est toujours
        #  la meme. Que la session ait existe ou non n'est pas l'affaire de
        #  l'appelant : il voulait se deconnecter, il l'est.
        _retirer_le_cookie_de_session(parametres, reponse)
        return ReponseGenerique(message="Vous etes deconnecte.")

    return routeur


def _poser_le_cookie_de_session(parametres: Parametres, reponse: Response, jeton: str) -> None:
    """Poser le cookie de session — cahier §7.4, les trois attributs.

    **`HttpOnly` EST CE QUI REND LE CRITERE DU §7.4 TENABLE.** « Aucune donnee
    d'authentification durable dans `localStorage` » ne se tient pas par
    discipline de developpement : un jeton qu'aucun JavaScript ne peut lire ne
    peut pas etre stocke par mégarde. La regle devient structurelle, ce qui est le
    parti du §7.2 -- changer de forme plutot que promettre de l'attention.

    `max_age` VAUT LA DUREE ABSOLUE, ET C'EST UN CHOIX. Sans lui, le cookie
    mourrait a la fermeture du navigateur -- ce qui contredirait « expiration
    apres SEPT JOURS d'inactivite », une regle qui suppose que la session survit a
    un redemarrage. Le serveur reste l'autorite : un cookie encore present mais
    dont la session a expire est refuse.

    `path="/"` parce que le mandatement de `DEC-470` sert la page et l'API sur la
    MEME origine : un cookie borne a `/api` ne serait pas envoye par les pages.
    """
    reponse.set_cookie(
        key=parametres.SESSION_COOKIE_NAME,
        value=jeton,
        max_age=parametres.SESSION_ABSOLUTE_DAYS * 24 * 3600,
        path="/",
        httponly=True,
        secure=parametres.SESSION_COOKIE_SECURE,
        samesite=parametres.SESSION_COOKIE_SAMESITE,
    )


def _retirer_le_cookie_de_session(parametres: Parametres, reponse: Response) -> None:
    """Retirer le cookie — avec les MEMES attributs que la pose.

    Un navigateur n'efface un cookie que si `path`, `secure` et `samesite`
    concordent : les omettre laisserait le cookie en place, et la deconnexion
    paraitrait reussie. La session est revoquee cote serveur de toute facon --
    c'est elle qui fait autorite -- mais un cookie residuel serait un jeton mort
    qui traine.
    """
    reponse.delete_cookie(
        key=parametres.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=parametres.SESSION_COOKIE_SECURE,
        samesite=parametres.SESSION_COOKIE_SAMESITE,
    )


def _proteger_du_csrf(
    parametres: Parametres, requete: Request, *, jeton_de_session: str | None = None
) -> None:
    """Appliquer les barrieres CSRF a une ecriture — cahier §7.4, §20.1.

    **DEUX BARRIERES, ET LEUR PORTEE DIFFERE.** L'origine est controlee sur
    TOUTES les ecritures ; le jeton seulement quand une session existe, parce
    qu'un jeton suppose une session pour le delivrer.

    Args:
        jeton_de_session: le jeton du cookie, si cette route en exige un. `None`
            signifie « route amont » : seule l'origine est controlee.

    Raises:
        ErreurApplicative: 403, avec le meme gabarit pour les trois causes.
    """
    try:
        controler_l_origine(
            origine=requete.headers.get("origin"),
            attendue=origine_attendue(parametres.PUBLIC_BASE_URL),
        )
        if jeton_de_session is not None:
            controler_le_jeton(
                presente=requete.headers.get(EN_TETE_JETON),
                empreinte_de_session=empreinte_de_session(jeton_de_session),
                cle=parametres.APP_SECRET_KEY,
            )
    except CsrfRefuse as refus:
        #  Le motif interne est journalise, jamais rendu : distinguer les causes
        #  dirait a un attaquant s'il s'est approche.
        journal.warning(
            "requete refusee par la protection CSRF",
            extra={"resultat": "refus", "code_erreur": refus.motif},
        )
        raise ErreurApplicative(
            code=CODE_CSRF_REFUSE,
            message=MESSAGE_CSRF_REFUSE,
            statut=status.HTTP_403_FORBIDDEN,
        ) from None


def _reserver_l_idempotence(parametres: Parametres, requete: Request, *, route: str) -> str | None:
    """Reserver la cle d'idempotence si le client en fournit une.

    Rend la cle reservee -- que l'appelant devra `liberer` si son effet echoue --
    ou `None` si aucun en-tete n'a ete fourni.

    **L'EN-TETE EST OPTIONNEL, ET C'EST DECLARE.** Le §18.6 enumere six operations
    a rendre idempotentes, et aucune n'est une route de ce lot : exiger la cle ici
    serait exiger plus que le cahier. Le critere de `US005` porte sur ce qui se
    passe **quand une cle est fournie**, et c'est ce qui est garanti.

    Raises:
        ErreurApplicative: 422 sur une cle malformee -- cela ne depend que de la
            requete ; 503 si la memoire est injoignable, parce qu'on ne devine
            pas : deviner « premiere fois » laisserait passer un doublon, deviner
            « deja vue » refuserait une operation legitime.
    """
    cle = requete.headers.get(EN_TETE_CLE)
    if not cle:
        return None
    try:
        controler_la_cle(cle)
    except CleInvalide as invalide:
        raise ErreurApplicative(
            code=CODE_IDEMPOTENCE_INVALIDE,
            message=str(invalide),
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ=EN_TETE_CLE,
        ) from None
    try:
        premiere = reserver(parametres, route=route, cle=cle)
    except MemoireIndisponible:
        raise ErreurApplicative(
            code=CODE_MEMOIRE_INDISPONIBLE,
            message=MESSAGE_MEMOIRE_INDISPONIBLE,
            statut=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from None
    if not premiere:
        #  **LA CLE A DEJA SERVI : ON NE REFAIT RIEN.** L'appelant remonte sa
        #  reponse habituelle, ce qui est le sens d'idempotent -- un second appel
        #  rend le meme resultat sans produire un second effet. Rendre une erreur
        #  serait plus simple et faux : le client, qui a peut-etre perdu la
        #  premiere reponse, doit pouvoir la reobtenir.
        return ""
    return cle


def _empreinte_d_origine(parametres: Parametres, requete: Request) -> str | None:
    """Empreinte minimisee de l'origine, ou `None` — modele §10.3.

    Extraite en fonction pour que les quatre routes du lot emploient exactement la
    meme regle. Trois copies auraient divergé, et `T8` s'appuiera dessus.
    """
    origine = origine_de_la_requete(requete)
    if not origine or not parametres.APP_SECRET_KEY:
        return None
    return empreinte_d_origine(origine, parametres.APP_SECRET_KEY)


def compter_les_liens_actifs(parametres: Parametres, adresse_normalisee: str) -> int:
    """Nombre de liens actifs d'une personne, par son adresse normalisee.

    Fonction de DIAGNOSTIC, employee par les tests et par
    `make magic-link-check`. Elle ne rend aucune empreinte et aucun jeton.
    """
    with moteur(parametres).connect() as connexion:
        return int(
            connexion.execute(
                text(
                    "SELECT count(*) FROM magic_link_request m "
                    "JOIN person p ON p.id = m.person_id "
                    "WHERE p.email_normalized = :adresse "
                    "  AND m.used_at IS NULL AND m.invalidated_at IS NULL"
                ),
                {"adresse": adresse_normalisee},
            ).scalar_one()
        )
