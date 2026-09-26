"""Completer, valider et publier la fiche d'arrivee — matrice §7, modele §12.1.

LOT 7, `T3` — `MVP-L07-US001` (2/2), `MVP-L07-US002`.

LA PUBLICATION EST AUTOMATIQUE A LA VALIDATION, PAS UN SECOND GESTE

  Matrice §7.1, a la lettre : « La fiche est publiee automatiquement lorsque
  le nouvel arrivant la valide. La validation ne necessite pas une
  approbation prealable d'un responsable. » Le modele §12.1 le confirme :
  `published_at` est une « Publication immediate apres validation ».

  Une seule ecriture fait donc passer `state` de `draft` a `published`
  directement, `validated_at` et `published_at` portant le MEME instant. Le
  modele declare bien un etat `validated` intermediaire (§12.1 : « draft,
  validated, published, archived »), mais AUCUNE regle du corpus ne produit
  un etat ou une fiche serait validee sans etre publiee — l'inventer serait
  une DEUXIEME regle non ecrite. Un test qui exigerait un second appel pour
  publier serait donc faux ici : §7.39 du LOT 6, un critere qui suppose un
  geste que le corpus ne demande pas.

`recent_until` EST CALCULE PAR POSTGRESQL, PAS PAR PYTHON

  « Un mois apres la date d'arrivee » (modele §12.1) est une arithmetique de
  CALENDRIER, pas une duree fixe — `arrival_date + INTERVAL '1 month'` gere
  nativement les fins de mois (31 aout -> 30 septembre) que `timedelta(days=30)`
  ne gererait pas, et le projet n'a aucune dependance de calendrier (`dateutil`
  absent de `pyproject.toml`). Le laisser a la base evite d'ajouter une
  dependance pour reproduire ce qu'elle sait deja faire, et evite une DEUXIEME
  implementation du calcul qui pourrait diverger (§7.27).

LA PHOTO N'EST PAS ECRITE ICI

  Aucune route d'upload ni d'autorisation de media n'existe encore dans ce
  depot — `photo_authorization` (LOT 5) n'a jamais eu de service d'ECRITURE,
  seulement sa declaration. Accepter `photo_media_id` en entree inventerait un
  chainon que rien ne construit encore (§6.5) : residu nomme, comme la lecture
  de `T2` l'a deja ete pour la miniature.

L'ECRITURE RESTE OUVERTE APRES PUBLICATION, MAIS PAS AU MEME MONDE

  **CORRECTIF, TROUVE JUSTE APRES LA FUSION DE `T3` : LE §7 PORTE UNE
  QUATRIEME LIGNE, « CORRIGER APRES PUBLICATION », QU'UNE PREMIERE LECTURE
  AVAIT MANQUEE.** Elle donne `DSM`/`ESM`/`BOOST`/`ADM-E`/`SUPER` — jamais
  `NEW`, jamais `OFFICE` — le droit de corriger une fiche deja publiee. Le
  §6.2 verrouille EXPLICITEMENT le nouvel arrivant apres validation :
  « Apres validation de la fiche d'arrivee, le collaborateur ne peut plus
  modifier directement son profil » — et c'est exactement, mot pour mot, ce
  que cette ligne du §7 redit pour les RESPONSABLES : eux le peuvent, lui non.

  Une fiche `archived` reste seule etat sans aucune ligne d'ecriture : ni
  `Completer`, ni `Corriger apres publication` ne s'y appliquent, et c'est le
  SEUL etat que cette fonction refuse desormais.

  **`entity_membership.short_bio`/`fun_fact` NE SONT PAS `arrival_profile.
  short_intro`/`fun_fact` : CE SONT DEUX CHAMPS DISTINCTS, ET LE SECOND N'A
  ENCORE AUCUNE ROUTE D'ECRITURE.** Le §6.1 porte trois lignes de plus —
  « Modifier ou retirer un fun fact », « Ajouter ou remplacer une photo »,
  « Modifier la courte presentation apres validation » — et `T7` du LOT 5 les
  a explicitement **reportees** (`compte-rendu-t7-lot-5.md` : « presentation
  courte, fun fact et cercles secondaires nommes comme reportes »), pas
  livrees. Autoriser cette route sur `published` ne comble PAS ce residu du
  LOT 5, hors perimetre de `T3` : elle continue de servir les seuls
  `arrival_profile.short_intro`/`fun_fact`, jamais `entity_membership.*`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Final

from fastapi import status
from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.shared.errors import ErreurApplicative

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "Cette fiche a change depuis votre lecture. Rechargez-la avant de la modifier."
)

CODE_ETAT_INCOMPATIBLE: Final = "fiche_arrivee_etat_incompatible"
MESSAGE_ETAT_INCOMPATIBLE_COMPLETION: Final = (
    "Cette fiche est archivee : elle ne peut plus etre modifiee par cette route."
)

_ETATS_MODIFIABLES: Final[frozenset[str]] = frozenset({"draft", "published"})
MESSAGE_ETAT_INCOMPATIBLE_VALIDATION: Final = (
    "Cette fiche n'est pas au brouillon, ou n'existe pas encore : rien a valider."
)

CODE_PRESENTATION_MANQUANTE: Final = "fiche_arrivee_presentation_manquante"
MESSAGE_PRESENTATION_MANQUANTE: Final = (
    "La presentation courte est obligatoire avant de valider la fiche — modele §12.1."
)

_CHAMPS_AUTORISES: Final[frozenset[str]] = frozenset({"short_intro", "fun_fact"})


@dataclasses.dataclass(frozen=True, slots=True)
class FicheArriveeEcrite:
    """Ce qu'une completion ou une validation rend : l'identite et la version."""

    id: uuid.UUID
    version: int
    state: str


@dataclasses.dataclass(frozen=True, slots=True)
class FicheArriveeValidee(FicheArriveeEcrite):
    """Une validation rend aussi les trois marqueurs qu'elle vient d'ecrire."""

    validated_at: dt.datetime
    published_at: dt.datetime
    recent_until: dt.date


_LIGNE_COURANTE: Final[str] = """
SELECT id, version, state, short_intro
FROM arrival_profile
WHERE entity_membership_id = :appartenance AND entity_id = :entite
FOR UPDATE
"""

_CREER: Final[str] = """
INSERT INTO arrival_profile
    (entity_id, entity_membership_id, short_intro, fun_fact, created_by_person_id)
VALUES (:entite, :appartenance, :short_intro, :fun_fact, :acteur)
RETURNING id, version, state
"""


def completer_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int | None,
    champs: Mapping[str, str | None],
    instant: dt.datetime,
) -> FicheArriveeEcrite:
    """Creer la fiche (premiere completion), la modifier, ou la CORRIGER apres
    publication — matrice §7, lignes « Completer » et « Corriger apres
    publication ». Le PERMIS diverge selon l'etat (voir `perimetre.py`), pas
    cette fonction : elle sert les deux lignes parce que l'ECRITURE elle-meme
    — les memes deux champs, la meme concurrence optimiste — ne differe pas.

    `version_attendue` a `None` signifie « aucune ligne n'existe encore, d'apres
    ma derniere lecture » — exactement ce que `T2` rend. Une valeur presente
    exige la ligne et la version exactes, §18.4.

    `champs` ne porte que les cles REELLEMENT envoyees — l'appelant construit
    ce mapping depuis les champs presents du corps, jamais depuis ses valeurs
    par defaut, sans quoi une demande qui ne touche pas `fun_fact` l'effacerait.

    Refuse `archived` (et l'etat `validated` que la publication ne laisse
    jamais persister) : aucune ligne du §7 n'accorde de droit d'ecriture sur
    une fiche archivee, quel que soit le role.
    """
    assert frozenset(champs) <= _CHAMPS_AUTORISES  # noqa: S101 — construit par l'appelant, jamais l'utilisateur

    ligne = (
        connexion.execute(text(_LIGNE_COURANTE), {"appartenance": appartenance, "entite": entite})
        .mappings()
        .first()
    )

    if ligne is None:
        if version_attendue is not None:
            raise ErreurApplicative(
                code=CODE_VERSION_OBSOLETE,
                message=MESSAGE_VERSION_OBSOLETE,
                statut=status.HTTP_409_CONFLICT,
            )
        try:
            creee = (
                connexion.execute(
                    text(_CREER),
                    {
                        "entite": entite,
                        "appartenance": appartenance,
                        "short_intro": champs.get("short_intro"),
                        "fun_fact": champs.get("fun_fact"),
                        "acteur": acteur,
                    },
                )
                .mappings()
                .one()
            )
        except (IntegrityError, DataError) as erreur:
            raise _traduire_un_refus(erreur) from erreur
        return FicheArriveeEcrite(
            id=uuid.UUID(str(creee["id"])), version=int(creee["version"]), state=str(creee["state"])
        )

    if version_attendue is None or int(ligne["version"]) != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": int(ligne["version"])},
        )
    if str(ligne["state"]) not in _ETATS_MODIFIABLES:
        raise ErreurApplicative(
            code=CODE_ETAT_INCOMPATIBLE,
            message=MESSAGE_ETAT_INCOMPATIBLE_COMPLETION,
            statut=status.HTTP_409_CONFLICT,
        )

    ensembles = []
    parametres: dict[str, object] = {
        "ligne": ligne["id"],
        "acteur": acteur,
        "instant": instant,
    }
    if "short_intro" in champs:
        ensembles.append("short_intro = :short_intro")
        parametres["short_intro"] = champs["short_intro"]
    if "fun_fact" in champs:
        ensembles.append("fun_fact = :fun_fact")
        parametres["fun_fact"] = champs["fun_fact"]

    if not ensembles:
        #  Une demande sans effet ne fait pas monter la version — meme regle
        #  que `people/ecriture.py` : l'historique ne doit pas bouger pour rien.
        return FicheArriveeEcrite(
            id=uuid.UUID(str(ligne["id"])), version=int(ligne["version"]), state=str(ligne["state"])
        )

    #  `ensembles` ne contient que DEUX litteraux fixes de ce module — jamais
    #  une valeur de l'appelant — donc rien n'y est injectable ; le nom des
    #  colonnes n'est pas parametrable en SQL, d'ou la construction.
    requete = (
        "UPDATE arrival_profile SET "  # noqa: S608
        + ", ".join(ensembles)
        + ", version = version + 1, updated_at = :instant, updated_by_person_id = :acteur "
        "WHERE id = :ligne RETURNING id, version, state"
    )
    try:
        modifiee = connexion.execute(text(requete), parametres).mappings().one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus(erreur) from erreur
    return FicheArriveeEcrite(
        id=uuid.UUID(str(modifiee["id"])),
        version=int(modifiee["version"]),
        state=str(modifiee["state"]),
    )


_VALIDER: Final[str] = """
UPDATE arrival_profile
SET state = 'published',
    validated_at = :instant,
    published_at = :instant,
    recent_until = (:arrivee)::date + INTERVAL '1 month',
    version = version + 1,
    updated_at = :instant,
    updated_by_person_id = :acteur
WHERE id = :ligne
RETURNING id, version, state, validated_at, published_at, recent_until
"""


def valider_et_publier_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    arrival_date: dt.date,
    instant: dt.datetime,
) -> FicheArriveeValidee:
    """Valider ET publier en un seul geste — matrice §7.1, modele §12.1.

    Leve `ErreurApplicative` : `409` version obsolete ou etat incompatible
    (pas de brouillon a valider), `422` presentation manquante.
    """
    ligne = (
        connexion.execute(text(_LIGNE_COURANTE), {"appartenance": appartenance, "entite": entite})
        .mappings()
        .first()
    )

    if ligne is None or str(ligne["state"]) != "draft":
        raise ErreurApplicative(
            code=CODE_ETAT_INCOMPATIBLE,
            message=MESSAGE_ETAT_INCOMPATIBLE_VALIDATION,
            statut=status.HTTP_409_CONFLICT,
        )
    if int(ligne["version"]) != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": int(ligne["version"])},
        )
    presentation = ligne["short_intro"]
    if presentation is None or len(str(presentation).strip()) == 0:
        raise ErreurApplicative(
            code=CODE_PRESENTATION_MANQUANTE,
            message=MESSAGE_PRESENTATION_MANQUANTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        validee = (
            connexion.execute(
                text(_VALIDER),
                {
                    "ligne": ligne["id"],
                    "acteur": acteur,
                    "instant": instant,
                    "arrivee": arrival_date,
                },
            )
            .mappings()
            .one()
        )
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus(erreur) from erreur

    return FicheArriveeValidee(
        id=uuid.UUID(str(validee["id"])),
        version=int(validee["version"]),
        state=str(validee["state"]),
        validated_at=validee["validated_at"],
        published_at=validee["published_at"],
        recent_until=validee["recent_until"],
    )


def _traduire_un_refus(erreur: IntegrityError | DataError) -> ErreurApplicative:
    """Traduire un refus de la BASE plutot que de le laisser sortir en `500`.

    Discriminant sur le TYPE d'exception psycopg, jamais sur le message —
    §7.25/§7.37, un message est localise et change de version en version.
    """
    cause = erreur.orig
    if isinstance(cause, erreurs_psycopg.CheckViolation):
        return ErreurApplicative(
            code=CODE_PRESENTATION_MANQUANTE,
            message=MESSAGE_PRESENTATION_MANQUANTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if isinstance(cause, erreurs_psycopg.UniqueViolation):
        return ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
        )
    raise erreur
