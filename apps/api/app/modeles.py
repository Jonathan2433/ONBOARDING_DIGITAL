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

from app.audit import modeles as audit_modeles
from app.auth import modeles as auth_modeles
from app.clients import modeles as clients_modeles
from app.content import modeles as content_modeles
from app.entities import modeles as entities_modeles
from app.events import modeles as events_modeles
from app.imports import modeles as imports_modeles
from app.media import modeles as media_modeles
from app.onboarding import modeles as onboarding_modeles
from app.organization import modeles as organization_modeles
from app.people import modeles as people_modeles
from app.shared.modele import Base, metadonnees

#  Les modules sont references pour que les analyseurs ne les prennent pas pour
#  des imports inutilises. L'effet recherche est l'import lui-meme.
MODULES_DE_MODELES = (
    auth_modeles,
    entities_modeles,
    people_modeles,
    clients_modeles,
    organization_modeles,
    #  LOT 5, T1 : les trois tables de media et d autorisation de photo.
    media_modeles,
    #  LOT 6, T1 : les trois tables editoriales du §15.
    content_modeles,
    #  LOT 7, T1 : la fiche d'arrivee et les six tables d'onboarding.
    onboarding_modeles,
    #  LOT 8, T1 : les quatre tables evenementielles du §17.
    events_modeles,
    #  LOT 9, T1 : les quatre tables de l'import CSV du §19.
    imports_modeles,
    #  LOT 10, T1 : les six tables de l'audit, des alertes, du support et du RGPD.
    audit_modeles,
)

__all__ = ["MODULES_DE_MODELES", "Base", "metadonnees"]
