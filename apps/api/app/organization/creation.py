"""Creer un cercle/bureau et attribuer un Booster/responsable de bureau — LOT 11, `T3`.

Hors backlog (`docs/operations/fiche-lot-11.md` §1.2) : a l'ouverture du LOT 11,
Jonathan a constate qu'aucune route ni aucun ecran de ce depot ne permet de
creer un cercle ou un bureau, ni d'attribuer un Booster ou un responsable de
bureau en dehors de l'import CSV (LOT 9). `app.organization.perimetre` le
disait deja, en toutes lettres, depuis `T4` du LOT 9 : « CE QUE CE MODULE NE
REGLE PAS […] la CREATION et la MODIFICATION DE STRUCTURE d'un cercle ou d'un
bureau ». Ce module le regle.

DEUX GRILLES DE ROLES, PAS UNE SEULE — MESURE DANS LA MATRICE, PAS SUPPOSE

  Le §10.2/§10.3 donnent a la CREATION la MEME grille qu'a l'archivage et la
  restauration (`ROLES_DE_CYCLE_DE_VIE_FRAMEWORK`, LOT 9 `T4`, reutilisee
  telle quelle — §7.27). Le §20 donne a l'ATTRIBUTION une grille SEPAREE,
  `ROLES_D_ATTRIBUTION_FRAMEWORK` : `ESM`/`SUPER` seulement, `ADM-E` exclu
  (« L'administrateur d'entite ne peut pas attribuer les responsabilites
  Framework », `ARB-DROIT-002`). Voir `app.organization.perimetre`.

ATTRIBUER LE BOOSTER, C'EST TOUJOURS REMPLACER

  `uq_framework_responsibility_booster_actif_par_cercle` (modele §8.4, §25.1)
  n'autorise qu'un seul Booster ACTIF par cercle : « Affecter OU REMPLACER le
  Booster » (§10.2, §20) n'est donc jamais une simple insertion — c'est fermer
  l'actif puis en ouvrir un nouveau, dans la MEME transaction, meme patron que
  `_ecrire_le_dsm`/`_ecrire_le_cercle` (`app.people.ecriture`, LOT 2). Demander
  la personne DEJA Booster active du cercle est un NO-OP — aucune periode
  d'une microseconde, meme discipline que `_ecrire_le_dsm`.

  **« Une personne ne peut pas etre Booster active dans plusieurs entites »**
  (§8.4, §2.5) est un declencheur (`fn_booster_une_seule_entite`, migration
  `0009`), jamais une verification applicative : une regle INTER-LIGNES
  qu'aucun index ne sait exprimer. Son refus est traduit au format du §18.3
  par le NOM de la contrainte (`CONSTRAINT = 'booster_une_seule_entite'`),
  jamais par le texte du message (§7.25).

ATTRIBUER UN RESPONSABLE DE BUREAU, C'EST AJOUTER — JAMAIS REMPLACER

  Le §10.3/§20 disent « Affecter LES responsables » (pluriel), et le modele
  autorise explicitement « un a trois » : aucune fermeture automatique d'un
  responsable existant. L'exclusion GiST partielle (`office_manager`, modele
  §25.2) refuse seulement un DOUBLON exact (meme personne, meme bureau,
  periodes qui se chevauchent) — traduite en 409 nomme, jamais laissee
  remonter brute.

  **LA BORNE « UN A TROIS » NE MORD PAS ICI, ET C'EST MESURE, PAS OUBLIE.**
  `DEC-583` (LOT 6 `T7`) pose le declencheur qui la tient sur `content_page`,
  a la PUBLICATION de la page de contenu du bureau — jamais sur
  `framework_responsibility_assignment` elle-meme. Aucune decision, aucune
  contrainte du corpus ne demande de la verifier a l'ATTRIBUTION : l'inventer
  ici serait le §6.5. Un bureau peut donc, temporairement et comme aujourd'hui,
  se retrouver a zero ou a plus de trois responsables tant qu'il n'est pas
  publie — exactement ce que `GET .../offices/{code}` rend deja sans le
  masquer (voir le docstring de `ReponseDuBureau`, `app.organization.routes`).

LE RETRAIT EST GENERIQUE AU TYPE, JAMAIS A LA RESSOURCE

  Le §20 ne porte qu'UNE ligne « Retirer une responsabilite Framework »,
  `ESM`/`SUPER`, pour tous les types. Ce module ne l'expose que pour `BOOSTER`
  et `OFFICE_MANAGER` — le perimetre nomme de `T3` (§1.2 de la fiche) — jamais
  pour `DSM`/`ESM`, qui resteraient une extension de scope non demandee.

LE MOTIF : COMME TOUTE ROUTE DEPUIS LOT 10 `T7`, JAMAIS DANS `assignment_reason`

  `ECART-064` (`DEC-661`) est deja clos : le motif du §18.1 voyage TOUJOURS
  dans `audit_event.reason`, jamais dans la colonne `assignment_reason` du
  modele, qui reste un residu nomme et non ecrit — meme discipline que
  `archive_reason` pour `app.organization.cycle_de_vie`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.entities.creation import CODE_PERSONNE_INTROUVABLE, MESSAGE_PERSONNE_INTROUVABLE
from app.organization.cycle_de_vie import CODE_CODE_DEJA_PRIS, MESSAGE_CODE_DEJA_PRIS
from app.organization.modeles import TypeResponsabilite
from app.shared.errors import ErreurApplicative

CODE_BOOSTER_ACTIF_AILLEURS: Final = "booster_actif_ailleurs"
MESSAGE_BOOSTER_ACTIF_AILLEURS: Final = (
    "cette personne est deja Booster actif dans une autre entite — modele §8.4"
)

CODE_DEJA_RESPONSABLE: Final = "deja_responsable_de_bureau"
MESSAGE_DEJA_RESPONSABLE: Final = (
    "cette personne est deja responsable actif de ce bureau — modele §25.2"
)

CODE_AFFECTATION_INTROUVABLE: Final = "affectation_introuvable"
MESSAGE_AFFECTATION_INTROUVABLE: Final = (
    "aucune affectation active de ce type ne correspond a cette ressource"
)

_PERSONNE_EXISTE: Final = text("SELECT 1 FROM person WHERE id = :personne")

_INSERER_LE_CERCLE: Final = text(
    "INSERT INTO circle (entity_id, code, name, color_token, description, display_order, "
    "created_by_person_id) "
    "VALUES (:entite, :code, :nom, :jeton, :description, :ordre, :acteur) "
    "RETURNING id, version"
)

_INSERER_LE_BUREAU: Final = text(
    "INSERT INTO office (entity_id, code, name, description, location_text, display_order, "
    "created_by_person_id) "
    "VALUES (:entite, :code, :nom, :description, :localisation, :ordre, :acteur) "
    "RETURNING id, version"
)

#  `FOR UPDATE` serialise deux attributions concurrentes du MEME cercle : la
#  seconde relit l'affectation fermee par la premiere plutot que de tenter
#  d'en fermer une qui n'existe deja plus.
_BOOSTER_ACTIF_DU_CERCLE: Final = text(
    """
    SELECT id, person_id FROM framework_responsibility_assignment
     WHERE circle_id = :cercle AND entity_id = :entite
       AND responsibility_type = 'BOOSTER' AND ends_at IS NULL
       FOR UPDATE
    """
)

_RESPONSABLE_ACTIF_DU_BUREAU: Final = text(
    """
    SELECT id FROM framework_responsibility_assignment
     WHERE office_id = :bureau AND entity_id = :entite AND person_id = :personne
       AND responsibility_type = 'OFFICE_MANAGER' AND ends_at IS NULL
     LIMIT 1
    """
)

_FERMER_LA_RESPONSABILITE: Final = text(
    """
    UPDATE framework_responsibility_assignment
       SET ends_at = :instant, updated_at = :instant, updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :affectation
    """
)

_ACCORDER_LA_RESPONSABILITE: Final = text(
    """
    INSERT INTO framework_responsibility_assignment
      (person_id, entity_id, responsibility_type, circle_id, office_id,
       assigned_by_person_id, starts_at, created_by_person_id)
    VALUES
      (:personne, :entite, :type, :cercle, :bureau, :acteur, :instant, :acteur)
    RETURNING id
    """
)

#  Une affectation ACTIVE, du bon type, de la bonne ressource ET de la bonne
#  entite — les quatre conditions evitent qu'un identifiant d'une autre
#  ressource ou deja ferme soit accepte en silence.
#  `FOR UPDATE` : un retrait concurrent du meme actif se serialise plutot que
#  de risquer deux fermetures de la meme ligne a des instants differents.
_AFFECTATION_BOOSTER_ACTIVE_DU_CERCLE: Final = text(
    """
    SELECT id FROM framework_responsibility_assignment
     WHERE circle_id = :cercle AND entity_id = :entite
       AND responsibility_type = 'BOOSTER' AND ends_at IS NULL
     LIMIT 1
       FOR UPDATE
    """
)

_AFFECTATION_RESPONSABLE_ACTIVE_DU_BUREAU: Final = text(
    """
    SELECT id FROM framework_responsibility_assignment
     WHERE id = :affectation AND office_id = :bureau AND entity_id = :entite
       AND responsibility_type = 'OFFICE_MANAGER' AND ends_at IS NULL
     LIMIT 1
       FOR UPDATE
    """
)


@dataclasses.dataclass(frozen=True, slots=True)
class CercleCree:
    """Ce que la creation d'un cercle a produit."""

    id: uuid.UUID
    code: str
    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class BureauCree:
    """Ce que la creation d'un bureau a produit."""

    id: uuid.UUID
    code: str
    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class BoosterAttribue:
    """Ce que l'attribution (ou le remplacement) du Booster a produit."""

    affectation: uuid.UUID
    remplace: bool


@dataclasses.dataclass(frozen=True, slots=True)
class ResponsableAttribue:
    """Ce que l'attribution d'un responsable de bureau a produit."""

    affectation: uuid.UUID


def _exiger_la_personne(connexion: Connection, personne: uuid.UUID) -> None:
    if connexion.execute(_PERSONNE_EXISTE, {"personne": personne}).first() is None:
        raise ErreurApplicative(
            code=CODE_PERSONNE_INTROUVABLE, message=MESSAGE_PERSONNE_INTROUVABLE, statut=422
        )


def creer_un_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    code: str,
    nom: str,
    jeton_de_couleur: str | None,
    description: str | None,
    ordre_d_affichage: int,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> CercleCree:
    """§10.2 « Creer un cercle | Entite ». Leve `409 code_deja_pris`."""
    try:
        ligne = connexion.execute(
            _INSERER_LE_CERCLE,
            {
                "entite": entite,
                "code": code,
                "nom": nom,
                "jeton": jeton_de_couleur,
                "description": description,
                "ordre": ordre_d_affichage,
                "acteur": acteur,
            },
        ).one()
    except IntegrityError as erreur:
        if isinstance(erreur.orig, erreurs_psycopg.UniqueViolation):
            raise ErreurApplicative(
                code=CODE_CODE_DEJA_PRIS, message=MESSAGE_CODE_DEJA_PRIS, statut=409
            ) from erreur
        raise

    cercle_id, version = uuid.UUID(str(ligne[0])), int(ligne[1])
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="cercle_cree",
        resource_type="circle",
        resource_reference=cercle_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation du cercle {code}",
        reason=motif,
    )
    return CercleCree(id=cercle_id, code=code, version=version)


def creer_un_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    code: str,
    nom: str,
    description: str | None,
    localisation: str | None,
    ordre_d_affichage: int,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> BureauCree:
    """§10.3 « Creer un bureau | Entite ». Leve `409 code_deja_pris`."""
    try:
        ligne = connexion.execute(
            _INSERER_LE_BUREAU,
            {
                "entite": entite,
                "code": code,
                "nom": nom,
                "description": description,
                "localisation": localisation,
                "ordre": ordre_d_affichage,
                "acteur": acteur,
            },
        ).one()
    except IntegrityError as erreur:
        if isinstance(erreur.orig, erreurs_psycopg.UniqueViolation):
            raise ErreurApplicative(
                code=CODE_CODE_DEJA_PRIS, message=MESSAGE_CODE_DEJA_PRIS, statut=409
            ) from erreur
        raise

    bureau_id, version = uuid.UUID(str(ligne[0])), int(ligne[1])
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="bureau_cree",
        resource_type="office",
        resource_reference=bureau_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation du bureau {code}",
        reason=motif,
    )
    return BureauCree(id=bureau_id, code=code, version=version)


def attribuer_le_booster(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cercle: uuid.UUID,
    personne: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> BoosterAttribue:
    """§10.2/§20 « Affecter ou remplacer le Booster | Entite ».

    Toujours un remplacement — voir l'en-tete du module. Demander la personne
    DEJA Booster active du cercle est un NO-OP, meme forme que
    `_ecrire_le_cercle` (`app.people.ecriture`).
    """
    _exiger_la_personne(connexion, personne)

    actif = connexion.execute(
        _BOOSTER_ACTIF_DU_CERCLE, {"cercle": cercle, "entite": entite}
    ).one_or_none()
    if actif is not None and uuid.UUID(str(actif[1])) == personne:
        return BoosterAttribue(affectation=uuid.UUID(str(actif[0])), remplace=False)

    if actif is not None:
        connexion.execute(
            _FERMER_LA_RESPONSABILITE,
            {"affectation": actif[0], "instant": instant, "acteur": acteur},
        )

    try:
        nouvelle = connexion.execute(
            _ACCORDER_LA_RESPONSABILITE,
            {
                "personne": personne,
                "entite": entite,
                "type": TypeResponsabilite.BOOSTER.value,
                "cercle": cercle,
                "bureau": None,
                "acteur": acteur,
                "instant": instant,
            },
        ).one()
    except IntegrityError as erreur:
        diagnostic = getattr(erreur.orig, "diag", None)
        contrainte = str(getattr(diagnostic, "constraint_name", "") or "")
        if contrainte == "booster_une_seule_entite":
            raise ErreurApplicative(
                code=CODE_BOOSTER_ACTIF_AILLEURS,
                message=MESSAGE_BOOSTER_ACTIF_AILLEURS,
                statut=409,
            ) from erreur
        raise

    affectation_id = uuid.UUID(str(nouvelle[0]))
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="booster_attribue",
        resource_type="framework_responsibility_assignment",
        resource_reference=affectation_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Attribution du Booster d'un cercle",
        new_values={"cercle_id": str(cercle), "person_id": str(personne)},
        reason=motif,
    )
    return BoosterAttribue(affectation=affectation_id, remplace=actif is not None)


def retirer_le_booster(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cercle: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> uuid.UUID:
    """§20 « Retirer une responsabilite Framework | Entite ». Leve `409` si aucun actif.

    Rend l'identifiant de l'affectation fermee — jamais `None` : une route qui
    agit rend toujours ce qu'elle a produit, meme discipline que le reste du
    module.
    """
    actif = connexion.execute(
        _AFFECTATION_BOOSTER_ACTIVE_DU_CERCLE, {"cercle": cercle, "entite": entite}
    ).one_or_none()
    if actif is None:
        raise ErreurApplicative(
            code=CODE_AFFECTATION_INTROUVABLE,
            message=MESSAGE_AFFECTATION_INTROUVABLE,
            statut=409,
        )
    affectation_id = uuid.UUID(str(actif[0]))
    connexion.execute(
        _FERMER_LA_RESPONSABILITE,
        {"affectation": affectation_id, "instant": instant, "acteur": acteur},
    )
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="booster_retire",
        resource_type="framework_responsibility_assignment",
        resource_reference=affectation_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Retrait du Booster d'un cercle",
        reason=motif,
    )
    return affectation_id


def attribuer_un_responsable_de_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    bureau: uuid.UUID,
    personne: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> ResponsableAttribue:
    """§10.3/§20 « Affecter les responsables | Entite ». Ajoute, ne remplace jamais.

    La borne « un a trois » ne mord pas ici — voir l'en-tete du module,
    `DEC-583`.
    """
    _exiger_la_personne(connexion, personne)

    if (
        connexion.execute(
            _RESPONSABLE_ACTIF_DU_BUREAU, {"bureau": bureau, "entite": entite, "personne": personne}
        ).first()
        is not None
    ):
        raise ErreurApplicative(
            code=CODE_DEJA_RESPONSABLE, message=MESSAGE_DEJA_RESPONSABLE, statut=409
        )

    try:
        nouvelle = connexion.execute(
            _ACCORDER_LA_RESPONSABILITE,
            {
                "personne": personne,
                "entite": entite,
                "type": TypeResponsabilite.OFFICE_MANAGER.value,
                "cercle": None,
                "bureau": bureau,
                "acteur": acteur,
                "instant": instant,
            },
        ).one()
    except IntegrityError as erreur:
        #  Course avec un appel concurrent sur la MEME paire personne/bureau :
        #  la verification ci-dessus ne l'a pas vue, l'exclusion GiST si.
        if isinstance(erreur.orig, erreurs_psycopg.ExclusionViolation):
            raise ErreurApplicative(
                code=CODE_DEJA_RESPONSABLE, message=MESSAGE_DEJA_RESPONSABLE, statut=409
            ) from erreur
        raise

    affectation_id = uuid.UUID(str(nouvelle[0]))
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="responsable_de_bureau_attribue",
        resource_type="framework_responsibility_assignment",
        resource_reference=affectation_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Attribution d'un responsable de bureau",
        new_values={"bureau_id": str(bureau), "person_id": str(personne)},
        reason=motif,
    )
    return ResponsableAttribue(affectation=affectation_id)


def retirer_un_responsable_de_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    bureau: uuid.UUID,
    affectation: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
    motif: str | None = None,
) -> uuid.UUID:
    """§20 « Retirer une responsabilite Framework | Entite ».

    `affectation` doit designer une ligne `OFFICE_MANAGER` ACTIVE de CE bureau
    et de CETTE entite — une affectation d'un autre bureau, d'un autre type,
    deja fermee ou inconnue rend la MEME erreur (§2.5, refus par defaut).

    Rend l'identifiant de l'affectation fermee, par symetrie avec
    `retirer_le_booster`.
    """
    trouvee = connexion.execute(
        _AFFECTATION_RESPONSABLE_ACTIVE_DU_BUREAU,
        {"affectation": affectation, "bureau": bureau, "entite": entite},
    ).one_or_none()
    if trouvee is None:
        raise ErreurApplicative(
            code=CODE_AFFECTATION_INTROUVABLE,
            message=MESSAGE_AFFECTATION_INTROUVABLE,
            statut=409,
        )
    connexion.execute(
        _FERMER_LA_RESPONSABILITE,
        {"affectation": affectation, "instant": instant, "acteur": acteur},
    )
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="responsable_de_bureau_retire",
        resource_type="framework_responsibility_assignment",
        resource_reference=affectation,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Retrait d'un responsable de bureau",
        reason=motif,
    )
    return affectation
