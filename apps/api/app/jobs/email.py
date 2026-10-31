"""L'interface fournisseur d'e-mails — `T1`, story `MVP-L11-US003`.

UNE INTERFACE, PAS UNE REECRITURE DE L'ENVOI SMTP

  `app.auth.courriel` envoie deja des e-mails par SMTP depuis le LOT 3, et
  Mailpit y est deja exclusif en developpement et en recette (`DEC-...`,
  cahier §16.5, garde-fou de production au §20.3). Reecrire une seconde fois
  l'ouverture de connexion SMTP serait dupliquer une construction deja posee
  et deja eprouvee (§7.27 de la passation). `FournisseurSMTP` ci-dessous
  l'appelle donc TEL QUEL, etendu d'un corps HTML facultatif (voir
  `app/auth/courriel.py`).

  « Mailpit est EXCLUSIF en recette » (critere de `US003`) est deja une
  garantie STRUCTURELLE : `Parametres.verifier_pour_production` (LOT 1, `T3`)
  refuse deja de demarrer avec `EMAIL_PROVIDER=mailpit` hors developpement.
  Ce module n'ajoute aucun second garde-fou qui pourrait diverger du premier.

POURQUOI UNE INTERFACE (`Protocol`) PLUTOT QU'UN APPEL DIRECT

  `US003` demande explicitement une « interface fournisseur ». Un seul
  fournisseur concret existe aujourd'hui (SMTP/Mailpit) ; le `Protocol` est ce
  qui permettra d'en substituer un second (un fournisseur transactionnel
  tiers, par exemple) sans toucher a `app.jobs.outbox`, qui ne connait que
  l'interface.

`envoyer_depuis_la_charge` EST CE QUE L'OUTBOX APPELLE, ET RIEN D'AUTRE

  Elle lit un `payload_json` deja valide par le modele JSONB et reconstruit
  l'appel au fournisseur — c'est la frontiere entre « un message technique
  generique » (`outbox_message`) et « un e-mail precis » (le fournisseur).
"""

from __future__ import annotations

from typing import Any, Protocol

from app.auth.courriel import EchecDEnvoi, envoyer
from app.configuration.settings import Parametres, parametres_en_cache

__all__ = ["EchecDEnvoi", "FournisseurDEmail", "FournisseurSMTP", "envoyer_depuis_la_charge"]


class FournisseurDEmail(Protocol):
    """Ce que `US003` appelle « une interface fournisseur »."""

    def envoyer(
        self, *, destinataire: str, sujet: str, corps_texte: str, corps_html: str | None = None
    ) -> None:
        """Remettre un e-mail. Leve `EchecDEnvoi` si la remise echoue."""
        ...


class FournisseurSMTP:
    """Le seul fournisseur concret de `T1` : SMTP, Mailpit exclusif hors production."""

    def __init__(self, parametres: Parametres) -> None:
        self._parametres = parametres

    def envoyer(
        self, *, destinataire: str, sujet: str, corps_texte: str, corps_html: str | None = None
    ) -> None:
        envoyer(
            self._parametres,
            destinataire=destinataire,
            sujet=sujet,
            corps=corps_texte,
            corps_html=corps_html,
        )


def obtenir_le_fournisseur(parametres: Parametres | None = None) -> FournisseurDEmail:
    """Le fournisseur configure. Un seul existe a `T1` : `FournisseurSMTP`."""
    return FournisseurSMTP(parametres if parametres is not None else parametres_en_cache())


def envoyer_depuis_la_charge(
    payload: dict[str, Any], *, fournisseur: FournisseurDEmail | None = None
) -> None:
    """Envoyer l'e-mail decrit par la charge d'un message `outbox_message(topic='email')`.

    La charge porte `destinataire`, `sujet`, `corps_texte` et, facultativement,
    `corps_html` — exactement les champs de `FournisseurDEmail.envoyer`, aucune
    traduction intermediaire qui pourrait diverger.
    """
    fournisseur_effectif = fournisseur if fournisseur is not None else obtenir_le_fournisseur()
    fournisseur_effectif.envoyer(
        destinataire=payload["destinataire"],
        sujet=payload["sujet"],
        corps_texte=payload["corps_texte"],
        corps_html=payload.get("corps_html"),
    )
