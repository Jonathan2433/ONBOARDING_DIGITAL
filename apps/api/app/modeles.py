"""Point d'entree unique qui importe TOUS les modeles du projet.

LOT 2, sous-etape `T2`, story `MVP-L02-US001`.

POURQUOI CE MODULE EXISTE, ET CE QUI ARRIVE SANS LUI. Une table ne s'inscrit
dans `metadonnees` qu'au moment ou son module est IMPORTE. `alembic/env.py`
importe ce module et lui seul : sans cela, `target_metadata` serait vide alors
que la base porte des tables, et `alembic revision --autogenerate` proposerait
une migration de SUPPRESSION de tout le schema -- le danger que la docstring
d'`env.py` annonce depuis `T3` du LOT 1.

**Toute sous-etape qui ajoute un module de modeles doit l'ajouter ici.** Un
controle le verifie : `test_tous_les_modules_de_modeles_sont_importes` compare
les modules presents sur le disque a ceux que ce fichier importe.
"""

from __future__ import annotations

from app.entities import modeles as entities_modeles
from app.people import modeles as people_modeles
from app.shared.modele import Base, metadonnees

#  Les modules sont references pour que les analyseurs ne les prennent pas pour
#  des imports inutilises. L'effet recherche est l'import lui-meme.
MODULES_DE_MODELES = (entities_modeles, people_modeles)

__all__ = ["MODULES_DE_MODELES", "Base", "metadonnees"]
