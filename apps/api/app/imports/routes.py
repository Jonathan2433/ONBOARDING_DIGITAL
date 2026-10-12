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
from typing import TYPE_CHECKING, Annotated, Final, Literal

from fastapi import APIRouter, Depends, File, Path, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Connection

from app.auth.dependances import SessionEtablie, proteger_du_csrf
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.imports.clients import lister_les_clients
from app.imports.decisions import (
    CODE_CIBLE_INCONNUE,
    CODE_CIBLE_MANQUANTE,
    CODE_LIGNE_INTROUVABLE,
    CODE_PORTEE_DSM_REFUSEE,
    CODE_TYPE_INCOHERENT,
    ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS,
    enregistrer_une_decision,
)
from app.imports.depot import (
    CODE_ENCODAGE_INVALIDE,
    CODE_FICHIER_VIDE,
    CODE_NOM_DE_FICHIER_INVALIDE,
    LotDepose,
    deposer_un_csv,
)
from app.imports.execution import (
    CODE_ETAT_NON_LANCABLE,
    CODE_LOT_INTROUVABLE,
    RapportDeLancement,
    lancer_l_import,
)
from app.imports.perimetre import ROLES_DE_DEPOT_DE_L_IMPORT
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
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


class ClientRendu(BaseModel):
    """Un client du référentiel global, vu depuis une entité — ferme `ECART-060`."""

    identifiant: uuid.UUID
    nom_canonique: str
    nom_affiche: str
    actif_localement: bool


class ReponseDesClients(BaseModel):
    """Le référentiel global des clients actifs — `GET .../clients`."""

    clients: list[ClientRendu]


#  Les CINQ categories, LITTERALEMENT — modele §19.4, `TypeDeDecisionImport`.
#  Jamais `TYPES_DE_DECISION_IMPORT` directement : `Literal` exige des
#  valeurs STATIQUES, un tuple de module n'en est pas une pour le typeur.
TypeDeDecisionLitteral = Literal[
    "person_merge",
    "profile_reactivation",
    "client_alias_creation",
    "canonical_client_selection",
    "voluntary_rejection",
]


class DemandeDeDecision(BaseModel):
    """Enregistrer une décision humaine — modèle §19.4.

    **SEULS `client_alias_creation` ET `canonical_client_selection` SONT
    EXERCÉS PAR `T8`** : voir l'en-tête de `app.imports.decisions`.
    """

    model_config = ConfigDict(extra="forbid")

    decision_type: TypeDeDecisionLitteral
    target_person_id: uuid.UUID | None = None
    target_client_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ReponseDeDecision(BaseModel):
    """Ce que l'enregistrement d'une décision a produit."""

    identifiant: uuid.UUID
    decision_type: str


class ReponseDeLancement(BaseModel):
    """Ce que `lancer_l_import` a produit — `preview_ready -> completed`."""

    version: int
    etat: str
    lignes_importees: int
    lignes_mises_a_jour: int
    lignes_rejetees_a_l_import: int
    lignes_en_attente_de_decision: int


def _lancement_rendu(rapport: RapportDeLancement) -> ReponseDeLancement:
    return ReponseDeLancement(
        version=rapport.version,
        etat=rapport.etat,
        lignes_importees=rapport.lignes_importees,
        lignes_mises_a_jour=rapport.lignes_mises_a_jour,
        lignes_rejetees_a_l_import=rapport.lignes_rejetees_a_l_import,
        lignes_en_attente_de_decision=rapport.lignes_en_attente_de_decision,
    )


def routeur_imports(parametres: Parametres) -> APIRouter:
    """Routeur du depot d'import CSV, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["imports"])

    garde_du_depot_d_import = exiger_un_role_dans_l_entite(parametres, ROLES_DE_DEPOT_DE_L_IMPORT)
    garde_de_validation_des_rapprochements = exiger_un_role_dans_l_entite(
        parametres, ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS
    )

    def _resoudre_l_entite_et_verifier_le_role(
        connexion: Connection, *, code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> tuple[uuid.UUID, frozenset[RoleDeLaMatrice]]:
        """L'entite active, ET les roles reverifies DANS cette transaction.

        **LA GARDE A RESOLU LES SIENS DANS SA PROPRE CONNEXION, A SON PROPRE
        INSTANT** : s'y fier ferait agir sur ce qui a ete autorise ailleurs —
        voir l'en-tete du module.

        Rend aussi les roles (pas seulement l'entite) depuis `T9` :
        `lancer_l_import` en a besoin pour resoudre le perimetre de cycle de
        vie d'une reactivation — meme motif que `_resoudre_l_entite_et_les_
        roles_de_validation` ci-dessous.
        """
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
        roles = ROLES_DE_DEPOT_DE_L_IMPORT & set(permissions.roles)
        if not roles:
            raise ErreurApplicative(
                code=CODE_ROLE_REFUSE, message=MESSAGE_ROLE_REFUSE, statut=status.HTTP_403_FORBIDDEN
            )
        return entite.id, frozenset(roles)

    def _resoudre_l_entite_et_les_roles_de_validation(
        connexion: Connection, *, code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> tuple[uuid.UUID, frozenset[RoleDeLaMatrice]]:
        """L'entite active ET les roles de VALIDATION, reverifies ici — meme motif.

        Rend les roles (pas seulement un booleen) : `enregistrer_une_decision`
        resserre ENCORE pour le DSM seul, selon la ligne visee — §14.
        """
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
        roles = ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS & set(permissions.roles)
        if not roles:
            raise ErreurApplicative(
                code=CODE_ROLE_REFUSE, message=MESSAGE_ROLE_REFUSE, statut=status.HTTP_403_FORBIDDEN
            )
        return entite.id, frozenset(roles)

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
            entite, _roles = _resoudre_l_entite_et_verifier_le_role(
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

    @routeur.get(
        "/entities/{code}/clients",
        dependencies=[Depends(garde_de_validation_des_rapprochements)],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesClients,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun des quatre roles du §14 dans cette entite."
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code d'entite inconnu, ou entite non active."
            },
        },
        summary="Le référentiel global des clients, vu depuis une entité",
        description=(
            "Ferme `ECART-060` pour les clients : le trombinoscope (LOT 5, `T3`) "
            "accepte déjà un filtre `client` sans qu'aucune route n'en serve la "
            "liste. `actif_localement` dit si une affectation à cette entité peut "
            "s'y rattacher directement, ou si elle exigerait une activation "
            "locale (`W-CLIENT-001`). Matrice §14 « Valider les rapprochements "
            "clients » : `DSM`/`ESM`/`ADM-E`/`SUPER`, `BOOST`/`OFFICE` à tiret."
        ),
    )
    def lister_les_clients_route(
        code: Annotated[
            str,
            Path(
                min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code` de l'entite"
            ),
        ],
    ) -> ReponseDesClients:
        """Le référentiel global des clients actifs — ferme `ECART-060`."""
        with moteur(parametres).connect() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            clients = lister_les_clients(connexion, entite=entite.id)
        return ReponseDesClients(
            clients=[
                ClientRendu(
                    identifiant=c.identifiant,
                    nom_canonique=c.nom_canonique,
                    nom_affiche=c.nom_affiche,
                    actif_localement=c.actif_localement,
                )
                for c in clients
            ]
        )

    @routeur.post(
        "/entities/{code}/imports/{lot}/rows/{ligne}/decisions",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeDecision,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    f"`{CODE_ROLE_REFUSE}` : aucun des quatre roles du §14 dans cette entite. "
                    f"`{CODE_PORTEE_DSM_REFUSEE}` : un DSM sans role plus large dont le `F16` "
                    "de la ligne ne le designe pas — hors de son perimetre."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Code d'entite inconnu, entite non active, lot ou ligne inconnus. "
                    f"`{CODE_LIGNE_INTROUVABLE}` : la ligne n'attend aucune decision. "
                    f"`{CODE_CIBLE_INCONNUE}` : la personne ou le client cible n'existe pas."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    f"`{CODE_TYPE_INCOHERENT}` : ce type de décision ne correspond à aucun "
                    "problème actuellement signalé sur cette ligne."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": f"`{CODE_CIBLE_MANQUANTE}` : ce type de décision exige une cible."
            },
        },
        summary="Enregistrer une décision humaine sur une ligne à confirmer",
        description=(
            "Matrice §14 « Valider les rapprochements clients » et modèle §19.4. "
            "Backlog `MVP-L09-US005`.<br><br>"
            "**N'IMPORTE RIEN** : `import_row.state` reste `needs_decision` — "
            "l'import réel (`T9`) relira cette décision. Seule exception : "
            "`client_alias_creation` crée immédiatement la ligne `client_alias` "
            "correspondante (modèle §7.3, `validated_by_person_id` déjà requis).<br><br>"
            "**Seuls `client_alias_creation` et `canonical_client_selection` sont "
            "exercés par `T8`** — les trois autres types existent structurellement "
            "pour `T7` (`D-PERSONNE-001`/`002`) et un usage futur."
        ),
    )
    def enregistrer_une_decision_route(
        code: Annotated[
            str,
            Path(
                min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code` de l'entite"
            ),
        ],
        lot: Annotated[uuid.UUID, Path(description="L'identifiant du lot d'import")],
        ligne: Annotated[uuid.UUID, Path(description="L'identifiant de la ligne")],
        demande: DemandeDeDecision,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_de_validation_des_rapprochements),  # noqa: B008
    ) -> ReponseDeDecision:
        """Enregistrer une décision humaine — matrice §14, modèle §19.4."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite, roles = _resoudre_l_entite_et_les_roles_de_validation(
                connexion, code=code, appelant=appelant, instant=instant
            )
            decision = enregistrer_une_decision(
                connexion,
                entite=entite,
                lot=lot,
                ligne=ligne,
                acteur=appelant.personne,
                roles=roles,
                type_de_decision=demande.decision_type,
                personne_cible=demande.target_person_id,
                client_cible=demande.target_client_id,
                motif=demande.reason,
                instant=instant,
            )
        return ReponseDeDecision(
            identifiant=decision.identifiant, decision_type=decision.decision_type
        )

    @routeur.post(
        "/entities/{code}/imports/{lot}/lancement",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLancement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun des trois roles du §14 « Lancer l'import » "
                    "dans cette entite — DSM, Booster et bureau exclus, meme grille que "
                    "« Charger un CSV »."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Code d'entite inconnu, entite non active, ou "
                    f"`{CODE_LOT_INTROUVABLE}` : ce lot n'existe pas dans cette entite."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": f"`{CODE_ETAT_NON_LANCABLE}` : le lot n'est pas en previsualisation."
            },
        },
        summary="Lancer l'import transactionnel des lignes previsualisees",
        description=(
            "Matrice §14 « Lancer l'import | ESM Entite | ADM-E Entite | SUPER Global » — "
            "meme grille que « Charger un CSV » (`DSM`/`BOOST`/`OFFICE` a tiret). "
            "Backlog `MVP-L09-US006` (1/2).<br><br>"
            "`preview_ready -> importing -> completed`, diagramme §24.4, dans le MEME "
            "appel synchrone (`DEC-462`). Chaque ligne `valid`/`warning`, ou "
            "`needs_decision` dont une decision enregistree resout le code, est creee "
            "ou mise a jour (fusion par e-mail, reactivation d'un profil archive avec "
            "confirmation explicite) dans son PROPRE savepoint — un refus de la base "
            "sur une ligne n'affecte aucune autre. Les champs non encore verifies par "
            "`T7`/`T8` (dates, metier, cercles, DSM, responsabilites Framework, roles "
            "techniques, autorisation photo) sont valides A CET INSTANT, pas en cache."
        ),
    )
    def lancer_l_import_route(
        code: Annotated[
            str,
            Path(
                min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code` de l'entite"
            ),
        ],
        lot: Annotated[uuid.UUID, Path(description="L'identifiant du lot d'import")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_depot_d_import),  # noqa: B008
    ) -> ReponseDeLancement:
        """Lancer l'import — matrice §14, diagramme §24.4."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite, roles = _resoudre_l_entite_et_verifier_le_role(
                connexion, code=code, appelant=appelant, instant=instant
            )
            rapport = lancer_l_import(
                connexion,
                entite=entite,
                lot=lot,
                acteur=appelant.personne,
                roles=roles,
                instant=instant,
            )
        return _lancement_rendu(rapport)

    return routeur
