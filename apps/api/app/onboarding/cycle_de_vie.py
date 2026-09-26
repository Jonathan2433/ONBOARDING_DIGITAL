"""Publier, archiver, restaurer une version de modele — matrice §9, modele §13.3, `T6`.

CE QUE `T5` LAISSAIT, ET CE QUE CE MODULE LIVRE

  `T5` a livre la creation d'un modele, d'une version brouillon et de sa liste
  de taches — son propre en-tete (`gabarits.py`) disait en toutes lettres :
  « Ni publication, ni archivage, ni restauration, ni duplication […] c'est
  `T6` ». Ce module ecrit les trois transitions qui restent sur `onboarding_
  template_version.state` : `draft --publier--> published`,
  `published --archiver--> retired`, `retired --restaurer--> published`.
  Aucune nouvelle table, aucune nouvelle colonne : le modele §13.3 declarait
  deja tout ce qu'il faut (`state`, `published_at`, `published_by_person_id`).

POURQUOI CE N'EST PAS DANS `gabarits.py`

  Meme separation que LOT 6 entre `content/ecriture.py` (creer, composer) et
  `content/cycle_de_vie.py` (publier, archiver, restaurer) : deux familles de
  controles distinctes, comme le decoupage du lot les separe deja en `T5`/`T6`.

LA RESTAURATION REND `published`, JAMAIS `draft` — ET C'EST UN CHOIX TRACE,
DELIBEREMENT DIFFERENT DE `restaurer_une_page` (LOT 6)

  `restaurer_une_page` ramene une page archivee en BROUILLON, pour trois
  raisons ecrites dans son en-tete : restaurer n'est pas publier, `RIGHTS-001`
  interdit qu'une ressource redevienne visible sans un geste de publication
  deliberee, et rien n'est perdu puisque la grille de restauration est INCLUSE
  dans celle de publication — qui restaure peut republier dans le geste
  suivant.

  **AUCUNE DE CES TROIS RAISONS NE TRANSPOSE ICI SANS DOMMAGE, ET LA PREMIERE
  LA CONTREDIT DIRECTEMENT.** Le modele §13.3 est sans equivoque : « Chaque
  publication cree une version IMMUABLE » — sans exception de cycle de vie.
  `definir_les_taches_de_la_version` (`T5`) encode deja cette garantie comme
  PERMANENTE : elle refuse d'ecrire des taches des que `state != 'draft'`,
  qu'il s'agisse de `published` OU de `retired`. Faire revenir une version
  DEJA PUBLIEE a `draft` rouvrirait cette meme garde a l'ecriture — une
  version qui a servi a instancier de vrais parcours (modele §13.5,
  `onboarding_instance.template_version_id`) deviendrait a nouveau modifiable.

  `onboarding_instance_task` (§13.6) n'en garderait pas moins un SNAPSHOT
  intact — aucune instance existante n'y perdrait rien techniquement — mais
  le CONTENU d'« la version 3 du modele X » cesserait de designer une chose
  stable dans le temps, ce que « immuable » veut dire au sens le plus simple.
  Restaurer REACTIVE donc la MEME version immuable pour de FUTURES
  affectations, sans jamais rouvrir son edition : `published_at` et
  `published_by_person_id` sont CONSERVES, la version A ETE publiee ce
  jour-la, restaurer n'est pas republier.

  Un temoin le prouve directement : `definir_les_taches_de_la_version` refuse
  TOUJOURS sur une version restauree, exactement comme sur une version
  fraichement publiee — la seule difference observable entre les deux est
  `published_at`, identique avant et apres le cycle archiver/restaurer.

CE QUI N'EST PAS ECRIT, ET POURQUOI

  Aucun motif, aucun acteur trace sur l'archivage ni la restauration : le
  modele §13.3 ne declare ni `archived_at`/`retired_at` ni `archived_by_
  person_id`/`restored_by_person_id` pour cette table — a la difference de
  `content_page` (LOT 6), qui les porte. Ecrire une colonne que le modele ne
  declare pas serait une invention (§6.5), et le §18.1 (motif obligatoire)
  n'enumere pas « archiver un modele d'onboarding » parmi ses cinq cas —
  meme raisonnement que `content/cycle_de_vie.py` pour l'archivage d'un
  contenu, et meme residu qu'`ECART-064`.

`ECART-066` RESOLU — VOIR `perimetre.py`

  Publier et archiver reutilisent `peut_gerer_un_modele_de_cette_portee` telle
  quelle (memes trois lignes a la meme grille que la creation, `T5`).
  Restaurer emploie une fonction SEPAREE, `peut_restaurer_une_version_de_
  modele` : DSM et BOOSTER y sont EXCLUS EN BLOC (jamais un sous-cas « son
  propre modele »), ESM les rejoint desormais aux memes conditions qu'`ADM-E`
  — arbitrage de Jonathan du 26/09/2026, question posee avant `T6` comme
  `ECART-066` le recommandait.

LA PRECONDITION D'ETAT EST DANS LE `WHERE`, PAS DANS UNE LECTURE PREALABLE

  A la difference de `definir_les_taches_de_la_version` (`T5`), qui lit
  `version.state` puis ecrit en deux temps, chaque transition ici porte sa
  precondition dans le MEME `UPDATE` — `WHERE id = :version AND state =
  :etat_attendu` — et verifie qu'une ligne a bien ete rendue. Aucune ligne
  rendue est TOUJOURS un `409 transition_de_version_invalide`, que la cause
  soit un etat de depart errone ou une course avec un autre acteur entre la
  lecture de la route (permis) et cette ecriture : meme parti que `content/
  cycle_de_vie.py` (LOT 6), plus sur que le motif du §7.0 sixieme
  proposition ne l'exigerait pour un controle, applique ici a une ecriture.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.onboarding.modeles import EtatDeLaVersionDuModele
from app.shared.errors import ErreurApplicative

CODE_TRANSITION_INVALIDE: Final = "transition_de_version_invalide"
MESSAGE_TRANSITION_INVALIDE: Final = (
    "Cette version n'est pas dans l'etat requis pour cette transition — modele §13.3."
)

_ETAT_DRAFT: Final[str] = EtatDeLaVersionDuModele.DRAFT.value
_ETAT_PUBLISHED: Final[str] = EtatDeLaVersionDuModele.PUBLISHED.value
_ETAT_RETIRED: Final[str] = EtatDeLaVersionDuModele.RETIRED.value


@dataclasses.dataclass(frozen=True, slots=True)
class VersionPubliee:
    """Ce qu'une publication a produit — modele §13.3."""

    id: uuid.UUID
    version_number: int
    state: str
    published_at: dt.datetime
    published_by_person_id: uuid.UUID


@dataclasses.dataclass(frozen=True, slots=True)
class VersionArchivee:
    """Ce qu'un archivage a produit.

    Pas d'instant ni d'acteur : `onboarding_template_version` ne declare ni
    `archived_at` ni `archived_by_person_id` — voir l'en-tete du module.
    """

    id: uuid.UUID
    version_number: int
    state: str


@dataclasses.dataclass(frozen=True, slots=True)
class VersionRestauree:
    """Ce qu'une restauration a produit — la version revient en `published`,
    JAMAIS en `draft`. `published_at`/`published_by_person_id` sont CONSERVES :
    voir l'en-tete du module."""

    id: uuid.UUID
    version_number: int
    state: str
    published_at: dt.datetime | None
    published_by_person_id: uuid.UUID | None


_COLONNES_TRANSITION: Final = "id, version_number, state, published_at, published_by_person_id"

#  Seule cette transition ECRIT `published_at`/`published_by_person_id` — les
#  deux autres les laissent intacts, qu'elles les rendent (restauration) ou
#  non (archivage, qui n'en a pas besoin pour son propre resultat).
_PUBLIER_VERSION: Final = f"""
UPDATE onboarding_template_version
   SET state = :etat_publie, published_at = :instant, published_by_person_id = :acteur
 WHERE id = :version AND state = :etat_attendu
RETURNING {_COLONNES_TRANSITION}
"""  # noqa: S608

_ARCHIVER_VERSION: Final = """
UPDATE onboarding_template_version
   SET state = :etat_retire
 WHERE id = :version AND state = :etat_attendu
RETURNING id, version_number, state
"""

_RESTAURER_VERSION: Final = f"""
UPDATE onboarding_template_version
   SET state = :etat_publie
 WHERE id = :version AND state = :etat_attendu
RETURNING {_COLONNES_TRANSITION}
"""  # noqa: S608


def _refuser_si_aucune_ligne(ligne: Any) -> Any:
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_TRANSITION_INVALIDE,
            message=MESSAGE_TRANSITION_INVALIDE,
            statut=status.HTTP_409_CONFLICT,
        )
    return ligne


def publier_une_version(
    connexion: Connection, *, version: uuid.UUID, acteur: uuid.UUID, instant: dt.datetime
) -> VersionPubliee:
    """Matrice §9 « Publier une version » — `draft` devient `published`.

    Seul un brouillon peut etre publie : aucune republication, aucune
    publication d'une version deja retiree — le §9 n'a qu'UNE ligne
    « Publier », jamais de transition inverse.
    """
    ligne = _refuser_si_aucune_ligne(
        connexion.execute(
            text(_PUBLIER_VERSION),
            {
                "version": version,
                "acteur": acteur,
                "instant": instant,
                "etat_publie": _ETAT_PUBLISHED,
                "etat_attendu": _ETAT_DRAFT,
            },
        )
        .mappings()
        .one_or_none()
    )
    return VersionPubliee(
        id=uuid.UUID(str(ligne["id"])),
        version_number=int(ligne["version_number"]),
        state=str(ligne["state"]),
        published_at=ligne["published_at"],
        published_by_person_id=uuid.UUID(str(ligne["published_by_person_id"])),
    )


def archiver_une_version(connexion: Connection, *, version: uuid.UUID) -> VersionArchivee:
    """Matrice §9 « Archiver une version » — `published` devient `retired`.

    Pas d'archivage direct depuis `draft` : un brouillon n'a jamais ete
    « en circulation », rien ne le distingue alors de le laisser en brouillon
    — le §9 ne nomme aucune transition `draft --> retired`, et en inventer
    une serait §6.5.
    """
    ligne = _refuser_si_aucune_ligne(
        connexion.execute(
            text(_ARCHIVER_VERSION),
            {"version": version, "etat_retire": _ETAT_RETIRED, "etat_attendu": _ETAT_PUBLISHED},
        ).one_or_none()
    )
    return VersionArchivee(
        id=uuid.UUID(str(ligne[0])), version_number=int(ligne[1]), state=str(ligne[2])
    )


def restaurer_une_version(connexion: Connection, *, version: uuid.UUID) -> VersionRestauree:
    """Matrice §9 « Restaurer une version » — `retired` redevient `published`.

    **ET NON `draft`** — voir l'en-tete du module, le choix le plus important
    de cette sous-etape. `published_at`/`published_by_person_id` d'ORIGINE
    sont rendus intacts : cette transition ne les ecrit pas, elle les lit
    seulement.
    """
    ligne = _refuser_si_aucune_ligne(
        connexion.execute(
            text(_RESTAURER_VERSION),
            {"version": version, "etat_publie": _ETAT_PUBLISHED, "etat_attendu": _ETAT_RETIRED},
        )
        .mappings()
        .one_or_none()
    )
    return VersionRestauree(
        id=uuid.UUID(str(ligne["id"])),
        version_number=int(ligne["version_number"]),
        state=str(ligne["state"]),
        published_at=ligne["published_at"],
        published_by_person_id=(
            None
            if ligne["published_by_person_id"] is None
            else uuid.UUID(str(ligne["published_by_person_id"]))
        ),
    )
