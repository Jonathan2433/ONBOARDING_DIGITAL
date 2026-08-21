"""Envoi de l'e-mail de connexion.

LOT 3, sous-etape `T3`, story `MVP-L03-US001`.

FONDEMENT — cahier §16.5 : Mailpit est **exclusif** en developpement et en
recette, et aucun contournement n'est autorise. Le garde-fou de production du
§20.3 refuse deja de demarrer avec `EMAIL_PROVIDER=mailpit`.

AUCUNE DEPENDANCE AJOUTEE

  `smtplib` et `email.message` sont dans la bibliotheque standard. Le LOT 1 s'est
  tenu a zero dependance ajoutee en `T10` ; il n'y a aucune raison d'en ajouter
  une pour envoyer un message texte a un serveur local.

CE MODULE NE JOURNALISE JAMAIS LE CORPS, ET C'EST LA REGLE QUI LE STRUCTURE

  Le corps contient le magic link complet. Le cahier §28.2 l'interdit dans les
  journaux, et `DEC-469` interdit deja la chaine de requete. Les messages
  d'erreur de ce module ne portent donc **que** le nom de l'hote SMTP et la
  classe de l'echec -- jamais l'adresse du destinataire, jamais le corps, jamais
  le lien.

  Les barrieres de `packages/observabilite` sont la seconde ligne, pas la
  premiere : elles rattrapent ce qui aurait fui malgre cette regle.

L'ENVOI A LIEU APRES LA REPONSE, ET C'EST UN CHOIX DE SECURITE

  Voir `routes.py`. Si l'API attendait la fin de l'aller-retour SMTP avant de
  repondre, la duree de reponse differerait entre une adresse connue et une
  adresse inconnue -- et ce delai revelerait l'existence du compte, que
  `US001` a precisement pour objet de ne pas reveler.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.configuration.settings import Parametres

journal = logging.getLogger("app.courriel")

#  Un envoi qui ne repond pas doit echouer, pas suspendre le processus. La valeur
#  est genereuse pour un serveur local et courte au regard d'une requete HTTP.
DELAI_SMTP_SECONDES = 10


class EchecDEnvoi(RuntimeError):
    """L'e-mail n'a pas pu etre remis au serveur SMTP.

    **Le message ne porte ni destinataire, ni corps, ni lien.** Une exception
    finit dans un journal, un ticket ou une capture d'ecran.
    """


def _message(parametres: Parametres, *, destinataire: str, sujet: str, corps: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{parametres.SMTP_FROM_NAME} <{parametres.SMTP_FROM_ADDRESS}>"
    message["To"] = destinataire
    message["Subject"] = sujet
    #  Un magic link ne doit pas etre indexe ni prefetche par un client de
    #  messagerie qui suivrait les liens : ces deux en-tetes sont la demande
    #  standard de ne pas le faire. Ils ne garantissent rien -- un client peut
    #  les ignorer -- et c'est pourquoi l'usage unique de `T4` reste la vraie
    #  protection.
    message["X-Auto-Response-Suppress"] = "All"
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(corps)
    return message


def envoyer(parametres: Parametres, *, destinataire: str, sujet: str, corps: str) -> None:
    """Remettre un message au serveur SMTP configure.

    Raises:
        EchecDEnvoi: si le serveur est injoignable ou refuse le message. Le
            message de l'exception ne contient aucune donnee du courriel.
    """
    message = _message(parametres, destinataire=destinataire, sujet=sujet, corps=corps)
    try:
        with smtplib.SMTP(
            parametres.SMTP_HOST, parametres.SMTP_PORT, timeout=DELAI_SMTP_SECONDES
        ) as serveur:
            if parametres.SMTP_USE_TLS:
                serveur.starttls()
            if parametres.SMTP_USER:
                serveur.login(parametres.SMTP_USER, parametres.SMTP_PASSWORD)
            serveur.send_message(message)
    except (OSError, smtplib.SMTPException) as erreur:
        #  Le type de l'erreur, jamais son texte : un `SMTPRecipientsRefused`
        #  porte l'adresse du destinataire dans sa representation.
        detail = (
            f"remise SMTP impossible vers {parametres.SMTP_HOST}:{parametres.SMTP_PORT} "
            f"({type(erreur).__name__})"
        )
        raise EchecDEnvoi(detail) from None

    #  Aucune trace du destinataire ni du sujet : le §28.2 exclut la donnee
    #  identifiante des journaux, et le sujet d'un e-mail de connexion dirait a
    #  lui seul qu'une adresse donnee existe.
    journal.info("courriel remis au serveur SMTP", extra={"resultat": "succes"})
