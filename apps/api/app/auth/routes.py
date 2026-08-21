"""Route de la demande de magic link — `POST {prefixe}/auth/magic-link`.

LOT 3, sous-etape `T3`, story `MVP-L03-US001`.

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

from fastapi import APIRouter, BackgroundTasks, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth.courriel import EchecDEnvoi, envoyer
from app.auth.jetons import empreinte_d_origine
from app.auth.services import Demande, demander_un_magic_link
from app.configuration.settings import Parametres
from app.shared.database import moteur

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
    """Reponse unique de la route, quelle que soit l'issue reelle."""

    message: str


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

        #  Le motif ne sort pas. Il est deja dans `auth_event`, et le journal de
        #  requete du §28.1 ne porte que la route, la duree et le resultat.
        return ReponseGenerique(message=MESSAGE_GENERIQUE)

    return routeur


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
