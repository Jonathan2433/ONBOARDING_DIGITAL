"""L'historique organisationnel d'une appartenance — story `MVP-L05-US008`.

LOT 5, sous-etape `T9`.

CE QUE LE CRITERE INTERDIT EST CE QUI STRUCTURE CE MODULE

  « Les periodes DSM, client, cercle et responsabilites sont lisibles **sans
  exposer les audits techniques** ». La seconde moitie n'est pas une precaution
  a prendre a l'ecriture : c'est une propriete a rendre **structurelle**, au sens
  du §7.35 -- la perdre doit exiger de reecrire les requetes et les structures,
  non d'oublier un filtre.

  **AUCUNE REQUETE DE CE MODULE NE TOUCHE UNE TABLE D'AUDIT.** `auth_event` n'y
  parait pas, et le §28 `audit_event` n'existe pas encore -- LOT 12. Le §16.2 de
  la matrice enumere ce qu'aucun role ne peut consulter depuis l'audit : mots de
  passe, jetons de session, magic links complets, secrets, CSV complets, contenu
  brut des e-mails. **Aucun ne vit dans les tables lues ici**, et c'est la forme
  la plus forte de conformite : on ne filtre pas ce qu'on ne lit pas.

  **ET LES COLONNES TECHNIQUES DES TABLES LUES SONT ABSENTES DES STRUCTURES.**
  `created_at`, `updated_at`, `created_by_person_id`, `updated_by_person_id`,
  `version`, `archived_at` et `assigned_by_person_id` existent sur ces lignes ;
  aucune periode rendue n'a de champ qui puisse les porter. Un test le fige.

LE CORPUS NE DIT RIEN DES AFFECTATIONS PASSEES, ET LE MOT « PERTINENT » NON PLUS

  Mesure du 12/09/2026 : zero occurrence de « ancien DSM », « missions passees »
  ou « affectation precedente » dans les cinq documents de cadrage. Et
  « pertinent », le mot du titre de `US008`, ne parait que dans les **deux copies
  du critere lui-meme** -- exactement la forme d'`ECART-051`, ou « regles de
  visibilite » ne paraissait nulle part ailleurs.

  La grille vient donc de la ligne « **Audit** » du §5, seul endroit ou la
  matrice regle la consultation d'un historique, et elle refuse `EMP` et `NEW`.
  Elle est resolue dans `app/permissions/perimetre.py`, avec les deux autres.

CE QUI N'EST PAS ICI, ET QUI EST NOMME PLUTOT QU'OUBLIE

  1. **`technical_role_assignment`**, les roles `ENTITY_ADMIN` et `SUPER_ADMIN`
     du §8.6. Le backlog dit « responsabilites », et le §8.4 -- la table lue ici
     -- s'appelle « responsabilites **Framework** ». Le §8.6 est une autre table,
     d'une autre nature : qui administre la plateforme est un fait de securite,
     non d'organisation. L'y mettre serait le §6.5 ;
  2. **les periodes d'appartenance elles-memes**, `entity_membership`. Le §25.2
     l'historise, mais ce n'est pas une AFFECTATION : c'est la racine a laquelle
     les affectations pendent, et le backlog ne la nomme pas ;
  3. **aucune pagination.** Le §18.2 borne le trombinoscope parce qu'il rend une
     population ; ici la volumetrie est celle d'UNE personne. La poser
     « par precaution » ajouterait un parametre d'URL que rien ne demande -- et
     `T2` a montre qu'un parametre d'URL mal type refuse en silence les valeurs
     valides. A rouvrir le jour ou une fiche dense le demandera.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.permissions.perimetre import AccesAlHistorique, AxeHistorique

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection


@dataclasses.dataclass(frozen=True, slots=True)
class PeriodeDeMetier:
    """§6.4 — une affectation metier et sa periode."""

    metier: str
    debut: dt.datetime
    fin: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class PeriodeDeStatut:
    """§6.5 — le statut ET son client, qui sont UNE SEULE periode.

    Les separer en deux axes inventerait deux historiques la ou la base en porte
    un : `status` et `client_id` vivent sur la meme ligne, liees par une
    biconditionnelle -- une mission a un client, un `intercontract` n'en a pas.
    """

    statut: str
    client: str | None
    debut: dt.datetime
    fin: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class PeriodeDeCercle:
    """§8.2 — une appartenance a un cercle, avec son TYPE.

    `principal` et `secondary` sont rendus tous deux : le §8.2 autorise
    plusieurs cercles secondaires, et masquer le type rendrait l'historique
    illisible -- on ne saurait pas si deux periodes qui se chevauchent sont une
    anomalie ou la regle.
    """

    code: str
    nom: str
    type: str
    debut: dt.datetime
    fin: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class PeriodeDeDsm:
    """§8.5 — un rattachement DSM et sa periode."""

    dsm: str
    debut: dt.datetime
    fin: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class PeriodeDeResponsabilite:
    """§8.4 — une responsabilite Framework, et sa portee.

    `cercle` et `bureau` sont exclusifs, et la base l'exige : le §8.4 rend
    `circle_id` obligatoire pour `BOOSTER` et `office_id` pour `OFFICE_MANAGER`,
    les deux nuls sinon. Les rendre tous deux plutot qu'un champ « portee »
    unique evite d'inventer un vocabulaire que le modele n'a pas.
    """

    type: str
    cercle: str | None
    bureau: str | None
    debut: dt.datetime
    fin: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class HistoriqueOrganisationnel:
    """Les axes LUS, et eux seuls.

    **UN AXE NON AUTORISE EST `None`, ET NON UNE LISTE VIDE.** Les deux ne disent
    pas la meme chose : `[]` signifie « il n'y a rien a montrer », `None` signifie
    « ce n'est pas dans ton perimetre ». Les confondre ferait croire a un DSM que
    son consultant n'a jamais eu de responsabilite, ce qui est une affirmation
    fausse -- et le §7.21 dit qu'un champ qui ment apprend a ne pas le lire.

    **Ce n'est pas une fuite** : un axe absent l'est pour TOUTES les cibles de ce
    role, jamais selon la cible. On n'apprend rien de la personne consultee.
    """

    metier: list[PeriodeDeMetier] | None
    statut: list[PeriodeDeStatut] | None
    cercle: list[PeriodeDeCercle] | None
    dsm: list[PeriodeDeDsm] | None
    responsabilites: list[PeriodeDeResponsabilite] | None


#  **L'ORDRE EST TOTAL, ET C'EST LA LECON DE `T2`.** `starts_at` seul ne suffit
#  pas : deux affectations ouvertes le meme instant -- ce que rien n'interdit sur
#  des tables differentes, ni sur `circle_membership` ou plusieurs cercles
#  secondaires coexistent -- rendraient un ordre instable d'une execution a
#  l'autre. La cle primaire le rend total.
#
#  **DECROISSANT** : le plus recent d'abord. C'est l'ordre dans lequel un humain
#  lit un parcours, et celui que `T11` affichera sans avoir a retourner la liste.
#
#  **IL EST ECRIT CINQ FOIS, ET C'EST DELIBERE.** J'en avais fait un gabarit
#  interpole -- `"ORDER BY {alias}.starts_at DESC, {alias}.id"` -- et ruff a eu
#  raison de le refuser : interpoler dans une chaine SQL declenche `S608`, cinq
#  fois. **Et la factorisation ne factorisait RIEN** : l'alias differe a chaque
#  requete, donc aucune chaine n'etait partagee. Cinq `noqa` pour economiser zero
#  duplication auraient ete le pire des deux mondes -- le §7.25, un garde-fou
#  qu'on apprend a contourner. Les requetes sont donc des LITTERAUX, comme celles
#  de `ecriture.py`, et la regle ne s'y applique plus.

#  **AUCUNE COLONNE TECHNIQUE N'EST SELECTIONNEE**, et ce n'est pas un oubli
#  heureux : `created_by_person_id`, `updated_by_person_id`, `assigned_by_person_id`,
#  `version`, `created_at` et `updated_at` existent sur toutes ces lignes. Les
#  omettre ici ET n'avoir aucun champ qui puisse les porter dans les structures
#  ci-dessus rend la propriete structurelle (§7.35).
_METIER: Final[str] = """
SELECT jc.label, mja.starts_at, mja.ends_at
FROM membership_job_assignment AS mja
JOIN job_catalog AS jc ON jc.id = mja.job_catalog_id
WHERE mja.entity_membership_id = :cible AND mja.entity_id = :entite
  AND mja.archived_at IS NULL
ORDER BY mja.starts_at DESC, mja.id
"""

_STATUT: Final[str] = """
SELECT ps.status, cl.display_name, ps.starts_at, ps.ends_at
FROM professional_status_assignment AS ps
LEFT JOIN client AS cl ON cl.id = ps.client_id
WHERE ps.entity_membership_id = :cible AND ps.entity_id = :entite
  AND ps.archived_at IS NULL
ORDER BY ps.starts_at DESC, ps.id
"""

_CERCLE: Final[str] = """
SELECT c.code, c.name, cm.membership_type, cm.starts_at, cm.ends_at
FROM circle_membership AS cm
JOIN circle AS c ON c.id = cm.circle_id
WHERE cm.entity_membership_id = :cible AND cm.entity_id = :entite
  AND cm.archived_at IS NULL
ORDER BY cm.starts_at DESC, cm.id
"""

_DSM: Final[str] = """
SELECT p.first_name || ' ' || p.last_name, da.starts_at, da.ends_at
FROM dsm_assignment AS da
JOIN person AS p ON p.id = da.dsm_person_id
WHERE da.consultant_membership_id = :cible AND da.entity_id = :entite
  AND da.archived_at IS NULL
ORDER BY da.starts_at DESC, da.id
"""

#  **LES RESPONSABILITES PENDENT A LA PERSONNE, PAS A L'APPARTENANCE**, et le
#  §8.4 l'ecrit : `person_id` et `entity_id`, jamais `entity_membership_id`. Les
#  lire par l'appartenance ne rendrait rien -- la colonne n'existe pas -- et les
#  lire sans borner l'entite sortirait du perimetre de la route.
_RESPONSABILITES: Final[str] = """
SELECT fra.responsibility_type, c.name, o.name, fra.starts_at, fra.ends_at
FROM framework_responsibility_assignment AS fra
LEFT JOIN circle AS c ON c.id = fra.circle_id
LEFT JOIN office AS o ON o.id = fra.office_id
WHERE fra.person_id = :personne AND fra.entity_id = :entite
  AND fra.archived_at IS NULL
ORDER BY fra.starts_at DESC, fra.id
"""

#  La personne de l'appartenance, et l'isolation par le couple `(id, entity_id)`
#  du §25.3. Une seule requete de plus, et elle est necessaire : les
#  responsabilites se lisent par `person_id`.
_PERSONNE: Final[str] = """
SELECT person_id FROM entity_membership
WHERE id = :cible AND entity_id = :entite AND archived_at IS NULL
"""


def lire_l_historique(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acces: AccesAlHistorique,
    instant: dt.datetime,
) -> HistoriqueOrganisationnel | None:
    """L'historique de `cible`, borne aux axes de `acces`. `None` si introuvable.

    **AUCUN AXE N'EST LU SI SON DROIT MANQUE**, et non « lu puis filtre » : le
    §2.5 « refus par defaut » veut qu'on ne travaille pas sur ce qu'on n'a pas le
    droit de voir, et une requete qu'on n'emet pas ne peut pas fuir par un
    journal de base lente.

    **LE NOMBRE DE REQUETES EST BORNE PAR LE NOMBRE D'AXES**, jamais par le
    nombre de periodes : cinq axes, donc au plus six requetes -- c'est le
    cinquieme critere de sortie du lot, « aucune requete N+1 critique », et il se
    COMPTE (§7.0, troisieme proposition). Un test le compte.

    Args:
        instant: non employe pour filtrer -- un historique se lit en entier -- mais
            exige pour que la signature ne mente pas le jour ou une borne de
            conservation apparaitra (§16.1 : « les journaux d'audit sont conserves
            un an », qui ne porte PAS sur ces tables).
    """
    _ = instant
    ligne = connexion.execute(text(_PERSONNE), {"cible": cible, "entite": entite}).first()
    if ligne is None:
        return None
    personne = uuid.UUID(str(ligne[0]))
    parametres = {"cible": cible, "entite": entite}

    metier = (
        [
            PeriodeDeMetier(metier=str(r[0]), debut=r[1], fin=r[2])
            for r in connexion.execute(text(_METIER), parametres)
        ]
        if AxeHistorique.METIER in acces.axes
        else None
    )
    statut = (
        [
            PeriodeDeStatut(
                statut=str(r[0]), client=None if r[1] is None else str(r[1]), debut=r[2], fin=r[3]
            )
            for r in connexion.execute(text(_STATUT), parametres)
        ]
        if AxeHistorique.STATUT in acces.axes
        else None
    )
    cercle = (
        [
            PeriodeDeCercle(code=str(r[0]), nom=str(r[1]), type=str(r[2]), debut=r[3], fin=r[4])
            for r in connexion.execute(text(_CERCLE), parametres)
        ]
        if AxeHistorique.CERCLE in acces.axes
        else None
    )
    dsm = (
        [
            PeriodeDeDsm(dsm=str(r[0]), debut=r[1], fin=r[2])
            for r in connexion.execute(text(_DSM), parametres)
        ]
        if AxeHistorique.DSM in acces.axes
        else None
    )
    responsabilites = (
        [
            PeriodeDeResponsabilite(
                type=str(r[0]),
                cercle=None if r[1] is None else str(r[1]),
                bureau=None if r[2] is None else str(r[2]),
                debut=r[3],
                fin=r[4],
            )
            for r in connexion.execute(
                text(_RESPONSABILITES), {"personne": personne, "entite": entite}
            )
        ]
        if AxeHistorique.RESPONSABILITES in acces.axes
        else None
    )
    return HistoriqueOrganisationnel(
        metier=metier,
        statut=statut,
        cercle=cercle,
        dsm=dsm,
        responsabilites=responsabilites,
    )
