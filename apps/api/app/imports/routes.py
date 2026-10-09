"""`POST /entities/{code}/imports` — LOT 9, sous-etapes `T6`/`T7`, `MVP-L09-US004`.

QUI DEPOSE, ET POURQUOI LA GARDE EST VERIFIEE DEUX FOIS

  Matrice §14 « Charger un CSV » : `ESM`/`ADM-E` dans leur entite, `SUPER`
  partout, `DSM`/`BOOST`/`OFFICE` a tiret. `garde_du_depot_d_import` (la
  dependance FastAPI) rend un premier refus rapide ; `_resoudre_l_entite_et_
  verifier_le_role` REVERIFIE ensuite DANS LA TRANSACTION qui va ecrire —
  meme motif que `organization.routes._resoudre_l_entite_et_verifier_le_role`
  et `people.routes._resoudre_le_cycle` : la garde a resolu les siens dans sa
  propre connexion et a son propre instant, s'y fier ferait agir sur ce qui a
  ete autorise ailleurs.

CE QUE CETTE ROUTE NE SERT PAS

  Aucune lecture (lister les lots, consulter un lot) : le decoupage ne la
  demande qu'a partir de `T14` (premier et seul ecran du lot), exactement
  comme les routes de creation de `T2`/`T3` restees sans consommateur avant
  cette meme sous-etape. L'inventer ici serait le §6.5.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, File, Path, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.engine import Connection

from app.auth.dependances import SessionEtablie, proteger_du_csrf
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.imports.depot import (
    CODE_ENCODAGE_INVALIDE,
    CODE_FICHIER_VIDE,
    CODE_NOM_DE_FICHIER_INVALIDE,
    LotDepose,
    deposer_un_csv,
)
from app.imports.perimetre import ROLES_DE_DEPOT_DE_L_IMPORT
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = (
    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie absent, "
    "jeton inconnu, session revoquee, duree absolue depassee, inactivite depassee."
)


class ReponseDeDepotDImport(BaseModel):
    """Ce que le depot ET la previsualisation d'un CSV ont produit — modele §19.1.

    `etat` vaut `preview_ready` : cette route sert les TROIS premieres
    transitions du diagramme §24.4 dans le MEME appel (import synchrone,
    `DEC-462`) — depot (`T6`), puis normalisation des e-mails et detection
    des doublons (`T7`). Les quatre compteurs se reconcilient avec
    `total_lignes` (`criteres-qualite-import.md` §4), MAIS seulement pour ce
    que `T7` verifie effectivement : `lignes_valides` ne garantit pas qu'une
    ligne franchira les regles non encore previsualisees (date, metier,
    cercle, DSM...), verifiees seulement a l'import reel (`T9`).
    """

    identifiant: uuid.UUID
    nom_de_fichier: str
    empreinte_sha256: str
    etat: str
    total_lignes: int
    lignes_valides: int
    lignes_avec_avertissement: int
    lignes_a_confirmer: int
    lignes_rejetees: int
    version: int


def _lot_rendu(lot: LotDepose) -> ReponseDeDepotDImport:
    return ReponseDeDepotDImport(
        identifiant=lot.identifiant,
        nom_de_fichier=lot.source_filename,
        empreinte_sha256=lot.source_checksum_sha256,
        etat=lot.state,
        total_lignes=lot.total_rows,
        lignes_valides=lot.valid_rows,
        lignes_avec_avertissement=lot.warning_rows,
        lignes_a_confirmer=lot.needs_decision_rows,
        lignes_rejetees=lot.rejected_rows,
        version=lot.version,
    )


def routeur_imports(parametres: Parametres) -> APIRouter:
    """Routeur du depot d'import CSV, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["imports"])

    garde_du_depot_d_import = exiger_un_role_dans_l_entite(parametres, ROLES_DE_DEPOT_DE_L_IMPORT)

    def _resoudre_l_entite_et_verifier_le_role(
        connexion: Connection, *, code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> uuid.UUID:
        """L'entite active, ET les roles reverifies DANS cette transaction.

        **LA GARDE A RESOLU LES SIENS DANS SA PROPRE CONNEXION, A SON PROPRE
        INSTANT** : s'y fier ferait agir sur ce qui a ete autorise ailleurs —
        voir l'en-tete du module.
        """
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
        if not ROLES_DE_DEPOT_DE_L_IMPORT & set(permissions.roles):
            raise ErreurApplicative(
                code=CODE_ROLE_REFUSE, message=MESSAGE_ROLE_REFUSE, statut=status.HTTP_403_FORBIDDEN
            )
        return entite.id

    @routeur.post(
        "/entities/{code}/imports",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeDepotDImport,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun des trois roles du §14 dans cette entite, "
                    "ou le jeton anti-CSRF manque ou ne correspond pas."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code d'entite inconnu, ou entite non active."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    f"`{CODE_FICHIER_VIDE}` : fichier vide ou sans aucune ligne exploitable. "
                    f"`{CODE_ENCODAGE_INVALIDE}` : le contenu n'est pas du texte UTF-8. "
                    f"`{CODE_NOM_DE_FICHIER_INVALIDE}` : le nom du fichier est vide une "
                    "fois nettoye de tout chemin."
                )
            },
        },
        summary="Deposer un CSV et produire sa previsualisation",
        description=(
            "Matrice §14 « Charger un CSV | ESM Entite | ADM-E Entite | SUPER Global » — "
            "`DSM`, `BOOST` et `OFFICE` a tiret. Backlog `MVP-L09-US004`.<br><br>"
            "Depose le CSV dans MinIO (cle jamais fournie par le client), calcule son "
            "empreinte SHA-256, pose un `import_batch`, analyse CHAQUE ligne "
            "STRUCTURELLEMENT dans `import_row.raw_data` (`T6`), PUIS normalise l'e-mail "
            "(champ logique `F01`), detecte les doublons (technique dans le fichier, "
            "profil actif ou archive existant, homonymie) et bloque les lignes sans "
            "e-mail (`T7`). Aucune ecriture metier : ni `person`, ni `client`, ni "
            "`entity_membership`. Les autres regles du schema (date, metier, cercle, "
            "DSM...) ne sont PAS previsualisees ici — verifiees seulement a l'import "
            "reel, non encore construit."
        ),
    )
    def deposer_un_import(
        code: Annotated[
            str,
            Path(
                min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code` de l'entite"
            ),
        ],
        requete: Request,
        fichier: Annotated[UploadFile, File(description="Le CSV brut, depose tel quel.")],
        appelant: SessionEtablie = Depends(garde_du_depot_d_import),  # noqa: B008
    ) -> ReponseDeDepotDImport:
        """Deposer un CSV — cahier §9.5 (points 1 et 2), §19.1."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        #  Lu AVANT la transaction : un corps de requete illisible ne doit pas
        #  laisser une connexion ouverte en attente.
        contenu = fichier.file.read()

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_l_entite_et_verifier_le_role(
                connexion, code=code, appelant=appelant, instant=instant
            )
            lot = deposer_un_csv(
                connexion,
                parametres,
                entite=entite,
                acteur=appelant.personne,
                nom_de_fichier=fichier.filename or "import.csv",
                contenu=contenu,
                instant=instant,
            )
        return _lot_rendu(lot)

    return routeur
