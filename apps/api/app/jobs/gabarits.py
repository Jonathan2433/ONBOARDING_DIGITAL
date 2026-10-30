"""Le registre des gabarits d'e-mail VERSIONNES — `T1`, story `MVP-L11-US003`.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  La roadmap et le cahier ecrivent, mot pour mot, « les templates texte/HTML
  sont versionnes » parmi les criteres de `US003`. Ce module pose le
  MECANISME — un registre nomme, chaque entree portant sa propre version — et
  RIEN DE PLUS.

  **Aucun gabarit metier n'est enregistre ici.** Aucune story de ce lot ne
  nomme un contenu d'e-mail concret a envoyer : en enregistrer un maintenant
  serait inventer un texte que personne n'a decide (§6.5 de la passation).
  Le registre est vide a la sortie de `T1`, et c'est un residu NOMME : la
  premiere sous-etape future qui a besoin d'envoyer un e-mail reel y
  enregistre son gabarit, versionne des sa premiere ligne.

  Le mecanisme est neanmoins EPROUVE par les tests de ce module, qui
  enregistrent un gabarit JETABLE propre au test — jamais une donnee qui
  survivrait a la suite.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Final


@dataclasses.dataclass(frozen=True, slots=True)
class GabaritDEmail:
    """Un gabarit nomme et VERSIONNE — le texte et, facultativement, le HTML."""

    nom: str
    version: str
    sujet: str
    corps_texte: Callable[..., str]
    corps_html: Callable[..., str] | None = None


_GABARITS: Final[dict[str, GabaritDEmail]] = {}


def enregistrer(gabarit: GabaritDEmail) -> None:
    """Enregistrer un gabarit sous son nom. Un nom deja pris est une erreur.

    Un gabarit ne se MODIFIE jamais en place : une nouvelle version porte un
    nouveau `gabarit.version`, et le code qui l'emploie choisit explicitement
    lequel — jamais un remplacement silencieux de ce qu'un appelant croyait
    deja envoyer.
    """
    if gabarit.nom in _GABARITS:
        message = f"le gabarit {gabarit.nom!r} est deja enregistre"
        raise ValueError(message)
    _GABARITS[gabarit.nom] = gabarit


def obtenir(nom: str) -> GabaritDEmail:
    """Lire un gabarit par son nom. Leve `KeyError` si aucun ne porte ce nom."""
    return _GABARITS[nom]
