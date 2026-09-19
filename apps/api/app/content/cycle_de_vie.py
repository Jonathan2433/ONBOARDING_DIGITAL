"""Publier, archiver, restaurer une page — annexe A §13 et §18. LOT 6, `T7`.

Story `MVP-L06-US006`, « previsualiser puis publier un contenu ».

CE QUE CE MODULE ECRIT, ET CE QUE `T6` REFUSAIT D'ECRIRE

  `T6` a livre la creation et l'ecriture du contenu, et son compte rendu dit en
  toutes lettres que **`state` et `published_at` ne sont jamais touches** -- un
  controle de stack le mesure apres deux ecritures sur une page publiee. Ce
  module est le seul ecrivain de ces deux colonnes, et c'est ce qui rend la
  frontiere entre « modifier » et « publier » verifiable plutot que promise.

LES TROIS TRANSITIONS, ET CE QUI LES BORNE

      draft      --  publier    -->  published      published_at recoit l'instant
      draft      --  archiver   -->  archived       archived_at, archived_by
      published  --  archiver   -->  archived       idem, published_at CONSERVE
      archived   --  restaurer  -->  draft          archived_at et archived_by effaces

  **IL N'Y A PAS DE `published --> draft`**, et ce n'est pas un oubli : le §13
  porte « Publier immediatement », « Archiver » et « Restaurer », et **aucune
  ligne de depublication**. En inventer une serait le §6.5. Retirer une page du
  public se fait donc en l'archivant, ce que le §18 nomme et graduate.

  **ET IL N'Y A PAS DE `published --> published`.** Republier une page deja
  publiee ecraserait `published_at`, donc **la date meme que `US006` demande
  d'identifier**. Le refus est porte par le perimetre -- `_actions_selon_l_etat`
  n'offre `PUBLIER` qu'a un brouillon -- et la route rend le 403 unique de
  `T6`, exactement comme `T8` du LOT 5 refuse d'archiver un profil deja archive.

CE QUE LA RESTAURATION REND, ET POURQUOI C'EST `draft`

  Le corpus ne le dit pas. Trois raisons concordantes font choisir le brouillon,
  et la plus forte n'est pas la prudence :

    1. **restaurer n'est pas publier**, et le §13 en fait deux lignes a deux
       grilles differentes. Rendre `published` ferait accomplir la seconde en
       demandant la premiere ;
    2. `RIGHTS-001` -- « toute permission est refusee par defaut si elle n'est
       pas explicitement accordee ». Une page redevenue visible sans que personne
       ne l'ait publiee est une publication que personne n'a decidee ;
    3. **rien n'est perdu** : la grille de restauration -- `ESM`, `ADM-E`,
       `SUPER` -- est INCLUSE dans celle de la publication, donc qui restaure
       peut republier dans le geste suivant, et ce geste laisse une trace.

  `published_at` est **conserve** a la restauration comme a l'archivage : la page
  A ETE publiee ce jour-la, et l'effacer detruirait un fait. `QO-122` porte la
  question a Lea, qui possede le vocabulaire produit ; elle n'est pas bloquante,
  la lecture retenue etant la restrictive.

CE QUE `US006` DEMANDE, ET CE QUE CE MODULE NE PEUT PAS TENIR

  Le critere est triple : « brouillon et publication sont distingues ; la version
  publiee est identifiable ; les modifications sont auditees. »

    1. **distingues** : `state` les separe, et la lecture de `T5` ne sert que le
       publie -- un brouillon rend le meme 404 qu'un slug inconnu ;
    2. **identifiable** : la reponse porte `version` et `publiee_le`. **Et une
       limite doit etre dite** : une ecriture de `T6` sur une page publiee
       incremente `version` sans changer `published_at`, si bien que le contenu
       servi change sans nouvelle publication. C'est la consequence directe de
       « Publier **immediatement** » et d'un modele ou la page porte UN contenu :
       un couple brouillon/publie exigerait une table de versions que le §15 ne
       declare pas. L'historique existe malgre tout, `T6` ARCHIVANT les blocs
       retires au lieu de les supprimer ;
    3. **auditees** : `audit_event` est le §21.1 du modele, et il appartient au
       **LOT 10**. Mesure du 19/09/2026 : aucune table d'audit metier n'existe --
       `auth_event` ne couvre que l'authentification. Ce module ecrit donc ce
       qu'il peut tracer sans elle, `updated_by_person_id` et
       `archived_by_person_id`, et **le critere reste partiellement ouvert**.
       L'issue `#151` ne se referme pas.

AUCUN MOTIF N'EST DEMANDE, ET LE §18.1 EN DONNE LA RAISON

  Il enumere les cinq cas ou un motif est obligatoire : purge definitive,
  revocation manuelle d'un acces actif, changement sensible de role, rollback
  d'import, intervention du super-administrateur dans une entite. **Archiver un
  contenu n'y est pas** -- c'est deja le raisonnement que `T6` a tenu pour
  l'archivage d'un bloc.

  **MAIS LE CINQUIEME CAS N'EST TENU NULLE PART DANS CE DEPOT**, et cela depasse
  `T7` : `archive_reason` et `assignment_reason` existent depuis le LOT 2 et
  **aucune ligne de code ne les ecrit** -- mesure du 19/09/2026, zero occurrence
  hors de leur declaration. Demander un motif ici seulement donnerait une regle
  appliquee a une route sur quarante. `ECART-064`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.sql.elements import TextClause

from app.content.ecriture import (
    CODE_SLUG_DEJA_PRIS,
    CODE_VERSION_OBSOLETE,
    MESSAGE_SLUG_DEJA_PRIS,
    MESSAGE_VERSION_OBSOLETE,
)
from app.content.modeles import EtatDePage
from app.shared.errors import ErreurApplicative

CODE_BORNE_DES_RESPONSABLES: Final = "borne_des_responsables"
MESSAGE_BORNE_DES_RESPONSABLES: Final = (
    "Un bureau publie compte entre un et trois responsables actifs — modele §8.4."
)

#  **LE NOM DU DECLENCHEUR EST LE DISCRIMINANT**, jamais le texte du message :
#  c'est `diag.constraint_name`, une donnee structuree du protocole PostgreSQL.
#  Meme parti que `_traduire_un_refus_de_la_base` de `T6`.
CONTRAINTE_BORNE_DES_RESPONSABLES: Final = "content_page_bureau_publie_borne_les_responsables"

#  §15.1. Deriver l'etat de l'enumeration plutot que d'ecrire la chaine : si le
#  modele renommait ses etats, ces constantes resteraient justes ou echoueraient
#  bruyamment, jamais silencieusement fausses (`DEC-544`).
ETAT_PUBLIE: Final[str] = EtatDePage.PUBLISHED.value
ETAT_ARCHIVE: Final[str] = EtatDePage.ARCHIVED.value
ETAT_APRES_RESTAURATION: Final[str] = EtatDePage.DRAFT.value


@dataclasses.dataclass(frozen=True, slots=True)
class PagePubliee:
    """Ce que la publication a produit — `US006`, « la version publiee est identifiable »."""

    version: int
    etat: str
    publiee_le: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class PageArchivee:
    """Ce que l'archivage a produit.

    `publiee_le` est RENDU bien que la page ne soit plus servie : une page
    archivee apres publication garde la date a laquelle elle a ete publiee, et
    c'est un fait, pas un residu. `None` pour une page archivee depuis le
    brouillon, ce qui distingue les deux histoires.
    """

    version: int
    etat: str
    archivee_le: dt.datetime
    publiee_le: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class PageRestauree:
    """Ce que la restauration a produit — la page revient en BROUILLON."""

    version: int
    etat: str
    publiee_le: dt.datetime | None


#  **CHAQUE LECTURE PORTE SA PROPRE PRECONDITION DANS SON `WHERE`, ET C'EST
#  L'IDIOME DE `T6`.** Le perimetre a deja refuse la transition illegale en 403 ;
#  ce filtre-ci couvre la fenetre entre cette resolution et l'ecriture. S'il ne
#  rend aucune ligne, c'est qu'un autre a agi entre-temps : le refus est donc un
#  `version_obsolete`, jamais un 403 -- le droit, lui, etait bien la.
#
#  `FOR UPDATE` verrouille la ligne jusqu'a la fin de la transaction : deux
#  publications simultanees se serialisent, et la seconde relit la version
#  incrementee par la premiere.
_PAGE_A_PUBLIER: Final = text(
    """
    SELECT version
      FROM content_page
     WHERE id = :page AND entity_id = :entite
       AND archived_at IS NULL AND state = :etat_attendu
       FOR UPDATE
    """
)

_PAGE_A_ARCHIVER: Final = text(
    """
    SELECT version
      FROM content_page
     WHERE id = :page AND entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

_PAGE_A_RESTAURER: Final = text(
    """
    SELECT version
      FROM content_page
     WHERE id = :page AND entity_id = :entite AND archived_at IS NOT NULL
       FOR UPDATE
    """
)

#  **LES DEUX COLONNES DE L'ARCHIVAGE SONT ECRITES DANS LE MEME `UPDATE`**, et
#  c'est ce qui rend leur divergence inexprimable par l'API (§7.35) : les separer
#  exigerait de casser cette requete, pas d'oublier un appel.
_PUBLIER: Final = text(
    """
    UPDATE content_page
       SET state = :etat,
           published_at = :instant,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :page AND entity_id = :entite
    RETURNING version, state, published_at
    """
)

_ARCHIVER: Final = text(
    """
    UPDATE content_page
       SET state = :etat,
           archived_at = :instant,
           archived_by_person_id = :acteur,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :page AND entity_id = :entite
    RETURNING version, state, archived_at, published_at
    """
)

#  `published_at` n'est PAS efface : la page a ete publiee ce jour-la, et le fait
#  survit a son archivage comme a sa restauration. `archive_reason` non plus,
#  et pour une raison mesuree : personne ne l'ecrit (`ECART-064`).
_RESTAURER: Final = text(
    """
    UPDATE content_page
       SET state = :etat,
           archived_at = NULL,
           archived_by_person_id = NULL,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :page AND entity_id = :entite
    RETURNING version, state, published_at
    """
)


def _exiger_la_version(
    connexion: Connection,
    requete: TextClause,
    parametres: dict[str, object],
    *,
    attendue: int,
) -> None:
    """Le verrou optimiste du cahier §18.4, « sans ecrasement silencieux ».

    **DEUX CAUSES, UN SEUL CODE, ET C'EST EXACT.** Aucune ligne rendue signifie
    que la page a quitte l'etat attendu ; une version differente, qu'elle a ete
    ecrite. Les deux disent la meme chose a l'appelant -- « votre lecture est
    perimee, rechargez » -- et les distinguer apprendrait l'etat courant a qui
    vient de perdre la course.

    `details` porte la version courante quand elle existe : un client qui
    recharge sait alors ou il en est, ce que `T6` fait deja.
    """
    ligne = connexion.execute(requete, parametres).one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
        )
    if ligne[0] != attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
            details={"version_actuelle": ligne[0]},
        )


def publier_une_page(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
) -> PagePubliee:
    """§13, « Publier immediatement » — un BROUILLON devient `published`.

    **LE DECLENCHEUR DU §8.4 PEUT REFUSER ICI, ET C'EST LE POINT** : publier la
    page d'un bureau qui n'a pas entre un et trois responsables actifs est le
    seul geste du projet qui fasse mordre cette borne (`DEC-583`).
    """
    _exiger_la_version(
        connexion,
        _PAGE_A_PUBLIER,
        {"page": page, "entite": entite, "etat_attendu": EtatDePage.DRAFT.value},
        attendue=version_attendue,
    )
    try:
        ligne = connexion.execute(
            _PUBLIER,
            {
                "page": page,
                "entite": entite,
                "etat": ETAT_PUBLIE,
                "instant": instant,
                "acteur": acteur,
            },
        ).one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur
    return PagePubliee(version=ligne[0], etat=str(ligne[1]), publiee_le=ligne[2])


def archiver_une_page(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
) -> PageArchivee:
    """§13 « Archiver » et §18 « Archiver un contenu dans son perimetre ».

    Un brouillon comme une page publiee peuvent etre archives : le §13 n'a
    qu'une ligne d'archivage, sans condition d'etat, et le §18 non plus.

    **L'ARCHIVAGE LIBERE LE SLUG**, et c'est l'index partiel de `T1` qui le fait
    -- `uq_content_page_entity_type_slug_non_archive ... WHERE archived_at IS
    NULL`. Consequence assumee et mesuree par un test : une page neuve peut
    reprendre le slug d'une page archivee, et c'est la restauration qui s'en
    trouvera refusee, non l'archivage.
    """
    _exiger_la_version(
        connexion,
        _PAGE_A_ARCHIVER,
        {"page": page, "entite": entite},
        attendue=version_attendue,
    )
    ligne = connexion.execute(
        _ARCHIVER,
        {
            "page": page,
            "entite": entite,
            "etat": ETAT_ARCHIVE,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()
    return PageArchivee(
        version=ligne[0], etat=str(ligne[1]), archivee_le=ligne[2], publiee_le=ligne[3]
    )


def restaurer_une_page(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
) -> PageRestauree:
    """§18 « Restaurer un contenu | Entite, restauration fonctionnelle ».

    **UN REFUS DE LA BASE EST ATTENDU ICI, ET IL A RAISON.** L'index unique du
    §15.1 etant partiel sur `archived_at IS NULL`, une page archivee ne reserve
    plus son slug : si une autre page l'a pris depuis, la restauration le
    reprendrait en double. La base refuse, et le 409 nomme le slug -- le
    restaurer en silence sur un slug modifie inventerait une donnee.
    """
    _exiger_la_version(
        connexion,
        _PAGE_A_RESTAURER,
        {"page": page, "entite": entite},
        attendue=version_attendue,
    )
    try:
        ligne = connexion.execute(
            _RESTAURER,
            {
                "page": page,
                "entite": entite,
                "etat": ETAT_APRES_RESTAURATION,
                "instant": instant,
                "acteur": acteur,
            },
        ).one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur
    return PageRestauree(version=ligne[0], etat=str(ligne[1]), publiee_le=ligne[2])


def _traduire_un_refus_de_la_base(erreur: IntegrityError | DataError) -> ErreurApplicative:
    """Traduire un refus du schema en reponse du §18.3.

    Deux contraintes sont reconnues, et **elles se ressemblent a l'oeil nu alors
    qu'elles n'ont rien a voir** : l'une est un index unique, l'autre un
    declencheur. Seul `diag.constraint_name` les separe, et le declencheur porte
    son nom grace au `USING CONSTRAINT = ...` de sa migration -- sans lui,
    PostgreSQL ne remplirait pas ce champ et le refus serait indiscernable d'un
    defaut interne.

    **CE QUI N'EST PAS RECONNU REMONTE.** Un 500 bruyant vaut mieux qu'un 409 qui
    accuserait l'appelant d'une faute qu'il n'a pas commise (§7.20).
    """
    cause = erreur.orig
    diagnostic = getattr(cause, "diag", None)
    contrainte = str(getattr(diagnostic, "constraint_name", "") or "")

    if contrainte == CONTRAINTE_BORNE_DES_RESPONSABLES:
        return ErreurApplicative(
            code=CODE_BORNE_DES_RESPONSABLES,
            message=MESSAGE_BORNE_DES_RESPONSABLES,
            statut=status.HTTP_409_CONFLICT,
        )
    if contrainte == "uq_content_page_entity_type_slug_non_archive":
        return ErreurApplicative(
            code=CODE_SLUG_DEJA_PRIS,
            message=MESSAGE_SLUG_DEJA_PRIS,
            statut=status.HTTP_409_CONFLICT,
            champ="slug",
        )
    raise erreur
