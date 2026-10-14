"""Structures partagees entre les modules d'analyse de l'import — LOT 9, `T9`.

POURQUOI CE MODULE EXISTE

  `Probleme` et les trois niveaux (`codes-erreurs-import.md` §1.1) etaient
  declares DANS `app.imports.analyse`. `T9` ajoute `app.imports.organisation`,
  qui produit aussi des `Probleme` et doit les rendre a `analyse.py` — lequel
  l'appelle deja (`app.imports.clients`). Les deux modules auraient donc
  importe l'un de l'autre. Un fait du modele (la forme d'un probleme, ses
  trois niveaux) se declare ici, dans un module SANS DEPENDANCE, pas dans le
  premier module qui en a eu besoin — meme parti que `app/shared/pagination.py`
  au LOT 6 (`T3`).
"""

from __future__ import annotations

import dataclasses
from typing import Final

#  Les trois niveaux de `codes-erreurs-import.md` §1.1 — jamais une
#  enumeration inventee, ce sont les lettres litterales du document.
NIVEAU_ERREUR: Final = "E"
NIVEAU_DECISION: Final = "D"
NIVEAU_AVERTISSEMENT: Final = "W"


@dataclasses.dataclass(frozen=True, slots=True)
class Probleme:
    """Un probleme detecte sur une ligne — `import_row_issue`, modele §19.3."""

    code: str
    champ: str | None
    valeur_normalisee_sure: str | None = None
