"""Le motif obligatoire d'une intervention du super-administrateur — ferme `ECART-064`.

LOT 10, sous-etape `T7`, stories `MVP-L10-US001`/`US002`.

CE QUE LE §18.1 EXIGE, ET CE QUE CE MODULE EN TRAITE

  Le cahier §18.1 enumere CINQ cas ou un motif est obligatoire : purge
  definitive, revocation manuelle d'un acces actif, changement sensible de
  role, rollback d'import, et **« intervention du super-administrateur dans
  une entite »**. `RIGHTS-017` le redit : « une intervention globale du
  super-administrateur dans une entite exige une tracabilite renforcee ».

  Seul ce DERNIER cas est traite ici. Les trois premiers (purge, revocation —
  deja un `raison` au LOT 3 `T2` —, changement sensible de role EN GENERAL)
  et le rollback d'import (qui n'existe pas) restent hors de ce module :
  l'exiger pour eux aussi serait une regle inventee, jamais demandee par
  Jonathan (§6.5 de la passation).

ARBITRAGE EXPLICITE DE JONATHAN, POSE AVANT TOUT CODE

  `ECART-064` avertissait lui-meme contre une regle posee sur « une route
  sur quarante » : son propre registre recommandait de mesurer D'ABORD
  combien de routes deja livrees un `SUPER` peut appeler dans une entite,
  avant de decider la largeur. Pose a Jonathan (`AskUserQuestion`,
  reformule sans jargon) : porte LARGE, retenue — le motif devient
  obligatoire partout ou `SUPER_ADMINISTRATEUR` autorise un appel deja
  cable a l'audit (`T2` a `T6`), pas seulement sur les routes nouvelles de
  `T7`.

  Second arbitrage, sur le MECANISME : **le role REELLEMENT UTILISE pour CET
  appel precis**, jamais seulement l'identite de la personne. `SUPER` n'a pas
  d'entite a lui — contrairement a `ESM`/`ADM-E`, qui agissent dans LEUR
  entite sans que cela soit « une intervention du super-administrateur » —
  si bien que toute action qu'il mene dans une entite particuliere compte,
  sans exception pour une eventuelle entite principale a lui.

OU CE MODULE EST APPELE, ET POURQUOI PAS DANS LE SERVICE GENERIQUE

  `app.audit.services.enregistrer_un_evenement` dit deja, dans son propre
  docstring : « `reason`... obligatoire pour les actions que le domaine
  appelant juge sensibles — ce service ne l'exige JAMAIS lui-meme, la regle
  appartient a chaque domaine cable ». Ce module EST cette regle,
  PARTAGEE par tous les domaines plutot que recopiee par chacun (§7.27) —
  mais il reste appele par CHAQUE route ou fonction de service, jamais par
  le service d'ecriture generique lui-meme, qui ne connait aucun role.

  Chaque ROUTE connait deja l'ensemble des roles qui ont autorise l'appel
  (`ROLES_X & set(permissions.roles)`, pose par `T9` du LOT 9 pour
  l'import et par l'equivalent de chaque domaine ailleurs) — c'est LA, et
  non une seconde requete a la base, que la verification a lieu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field

from app.permissions.services import RoleDeLaMatrice
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Set as AbstractSet

CODE_MOTIF_OBLIGATOIRE: Final = "motif_obligatoire"
MESSAGE_MOTIF_OBLIGATOIRE: Final = (
    "Un motif est obligatoire pour toute intervention du super-administrateur "
    "dans une entite (cahier §18.1, `RIGHTS-017`)."
)


class DemandeDeMotif(BaseModel):
    """Corps de requete PARTAGE pour les routes qui n'avaient aucun corps.

    Reutilise par TOUS les domaines cables a l'audit (§7.27) — une seule
    forme pour « le motif du §18.1, facultatif hors SUPER », plutot qu'une
    declaration locale par fichier de routes qui divergerait au premier
    correctif.
    """

    model_config = ConfigDict(extra="forbid")

    motif: str | None = Field(default=None, max_length=2000)


def motif_exige_pour_cet_appel(roles_autorisants: AbstractSet[RoleDeLaMatrice]) -> bool:
    """`SUPER_ADMINISTRATEUR` autorise-t-il CET appel precis ?

    `roles_autorisants` est l'intersection DEJA calculee par la route entre
    les roles exiges par la matrice et ceux que l'appelant porte — jamais
    l'ensemble COMPLET de ses roles, qui dirait seulement qui il EST, pas ce
    qui a autorise cette action precise (voir l'en-tete du module).
    """
    return RoleDeLaMatrice.SUPER_ADMINISTRATEUR in roles_autorisants


def exiger_un_motif_si_necessaire(
    roles_autorisants: AbstractSet[RoleDeLaMatrice], motif: str | None
) -> None:
    """Lever `422` si `SUPER` autorise cet appel et qu'aucun motif n'est fourni.

    Un motif vide ou tout en espaces ne compte pas comme fourni — memes
    discipline que `_nettoyer_le_nom_de_fichier` (`app.imports.depot`) : une
    chaine qui ne porte aucun caractere visible n'est pas une valeur.
    """
    if motif_exige_pour_cet_appel(roles_autorisants) and not (motif and motif.strip()):
        raise ErreurApplicative(
            code=CODE_MOTIF_OBLIGATOIRE,
            message=MESSAGE_MOTIF_OBLIGATOIRE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="motif",
        )
