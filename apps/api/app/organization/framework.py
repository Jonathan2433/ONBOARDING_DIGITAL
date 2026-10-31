"""La page Framework en lecture — LOT 6, `T2`, story `MVP-L06-US001`.

CE QUE LE CAHIER DEMANDE, ET CE QU'IL NE DEMANDE PAS

  Le §10.3 : « La page Framework fournit une vue synthetique sous forme de
  **cartes** et des pages detaillees pour : les **responsabilites** ; les
  **cercles** ; les **bureaux**. » Trois familles, pas quatre.

  **LE BACKLOG ET LA ROADMAP ECRIVENT « categories et responsabilites », ET LE
  MOT « categories » N'EST NULLE PART AILLEURS.** Mesure du 13/09/2026 : il
  n'apparait que dans ces deux documents DERIVES et dans la copie qu'en fait
  l'annexe C. Le cahier §10.3, qui **prevaut**, n'en parle pas.

  La lecture qui reconcilie les deux est ecrite au §6.2 : « Responsabilites
  Framework : DSM ; ESM ; Booster ; responsable de bureau ». **Ce sont les
  categories.** Et l'annexe A §10.1 le confirme en donnant a DSM et ESM leurs
  propres pages -- « Modifier la page DSM », « Modifier la page ESM » -- tandis
  que Booster et responsable de bureau se rejoignent PAR les cercles et les
  bureaux. D'ou exactement les trois familles du §10.3.

QUI LIT — LA MATRICE §5, ET NON L'ANNEXE A

  Le §5 donne « Framework | ANON — | EMP Lecture | NEW Lecture | ... » : **huit
  roles authentifies, sans distinction**, et `ANON` refuse.

  **L'ANNEXE A §10.1 N'A NI COLONNE `EMP` NI COLONNE `NEW`.** La lire seule
  aurait exclu l'acteur que la story nomme -- « **Employe** : Decouvrir le
  Framework ». C'est la forme exacte du piege de la colonne `OFFICE` au LOT 5 :
  un tableau qui parait faire autorite, et dont l'ensemble de colonnes est plus
  etroit que la question.

  Aucun role n'est donc examine ici, exactement comme le trombinoscope de `T2`
  du LOT 5, dont la ligne du §5 est identique.

CE QUE CE MODULE NE LIT PAS, ET POURQUOI

  **Aucune table de contenu editorial.** `content_page` existe depuis `T1`, mais
  la synthese Framework est **structurelle** : elle vient de
  `framework_responsibility_assignment`, `circle` et `office`. Les blocs
  editoriaux des pages detaillees sont le sujet de `T5`, et les y melanger ferait
  dependre une vue d'organisation d'un contenu que personne n'a encore ecrit.

  **Aucune personne archivee ni partie.** Un titulaire n'est nomme que si sa
  responsabilite est **active a l'instant** -- le §8.4 historise, et une periode
  close ne designe plus personne aujourd'hui.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


class ResponsabiliteFramework(enum.StrEnum):
    """Les QUATRE du cahier §6.2, dans l'ordre du document.

    **L'ORDRE VIENT DE L'ENUMERATION, PAS D'UN `sorted()`.** C'est le §7.35 :
    une propriete qu'aucun test unique ne peut observer -- l'ordre d'iteration
    d'un ensemble ne varie qu'entre PROCESSUS -- doit etre tenue par la
    structure. Le perdre exigerait de supprimer la boucle.
    """

    DSM = "DSM"
    ESM = "ESM"
    BOOSTER = "BOOSTER"
    OFFICE_MANAGER = "OFFICE_MANAGER"


RESPONSABILITES_FRAMEWORK: tuple[str, ...] = tuple(m.value for m in ResponsabiliteFramework)

#  §10.1 de l'annexe A donne une page a DSM et a ESM -- « Modifier la page DSM »,
#  « Modifier la page ESM » -- et n'en donne AUCUNE a BOOSTER ni a
#  OFFICE_MANAGER, qui se rejoignent par les cercles et les bureaux.
#
#  **CE N'EST PAS UNE COMMODITE D'AFFICHAGE, C'EST CE QUE LE DOCUMENT ECRIT**, et
#  le confondre ferait promettre une page qui n'existe pour personne.
RESPONSABILITES_A_PAGE_PROPRE: frozenset[str] = frozenset(
    {ResponsabiliteFramework.DSM, ResponsabiliteFramework.ESM}
)


@dataclasses.dataclass(frozen=True, slots=True)
class TitulaireFramework:
    """Une personne portant une responsabilite ACTIVE a l'instant."""

    identifiant: uuid.UUID
    prenom: str
    nom: str


@dataclasses.dataclass(frozen=True, slots=True)
class TitulaireAvecPhoto:
    """Une personne portant une responsabilite ACTIVE, avec sa photo.

    Chantier front hors lot, `S12` (`DEC-673`). **Distincte de
    `TitulaireFramework`, et c'est delibere** : la synthese Framework (toutes les
    responsabilites de l'entite, DSM/ESM/ADM-E/Booster/bureau confondus) reste
    hors de la portee de `S12` — arbitrage de Jonathan (`AskUserQuestion`,
    29/10/2026). Ajouter la photo a `TitulaireFramework` directement l'aurait
    exposee partout d'un coup, y compris sur un ecran que personne n'a decide de
    changer — §7.27 dans l'autre sens, comme `.cercle-page`/`.trombi-page` :
    deux usages, deux types, rien qui les lie.

    Seuls le Booster d'un cercle (`CercleDetaille.booster`) et les responsables
    d'un bureau (`BureauDetaille.responsables`) l'emploient.

    `appartenance` est NULLABLE : un titulaire de responsabilite n'a pas
    TOUJOURS une appartenance ACTIVE et LISTEE dans cette entite au sens du
    trombinoscope (`ETAT_LISTE`/`VISIBILITE_LISTEE`, `app.people.modeles`) —
    sans elle, `resoudre_la_miniature` n'a rien a resoudre, et `a_une_photo`
    reste faux plutot que de lever.
    """

    identifiant: uuid.UUID
    prenom: str
    nom: str
    appartenance: uuid.UUID | None
    a_une_photo: bool


@dataclasses.dataclass(frozen=True, slots=True)
class CarteDeResponsabilite:
    """Une categorie de responsabilite et ceux qui la portent."""

    type_de_responsabilite: str
    titulaires: tuple[TitulaireFramework, ...]
    #  `None` quand la responsabilite n'a pas de page propre. **Ce n'est pas la
    #  meme chose qu'une chaine vide** : vide dirait « la page existe et son
    #  adresse est inconnue », `None` dit « il n'y en a pas ». §7.0, quatrieme
    #  proposition, et c'est la lecon `null` != `[]` de `T9` du LOT 5.
    chemin_detaille: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class CarteDeCercle:
    """Un cercle, tel que la synthese le montre."""

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    #  **NULLABLE, ET C'EST MESURE.** `circle.color_token` l'est au catalogue, et
    #  `str(None)` a servi la chaine « None » sur 100 % des cercles pendant deux
    #  lots -- defaut `T10-8`. Le type le dit, et le decor produit les DEUX cas.
    jeton_de_couleur: str | None
    booster: TitulaireFramework | None
    membres_actifs: int
    chemin_detaille: str


@dataclasses.dataclass(frozen=True, slots=True)
class CarteDeBureau:
    """Un bureau, tel que la synthese le montre."""

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    localisation: str | None
    responsables: tuple[TitulaireFramework, ...]
    chemin_detaille: str


@dataclasses.dataclass(frozen=True, slots=True)
class PageFramework:
    """Les TROIS familles du cahier §10.3."""

    responsabilites: tuple[CarteDeResponsabilite, ...]
    cercles: tuple[CarteDeCercle, ...]
    bureaux: tuple[CarteDeBureau, ...]


#  ---------------------------------------------------------------------------
#  Les requetes. Une par famille, et jamais une jointure qui les melange : trois
#  cardinalites differentes dans une seule requete produiraient un produit
#  cartesien qu'il faudrait ensuite defaire en Python.
#  ---------------------------------------------------------------------------

#  `period @> :instant` emploie la colonne GENEREE du §25.2, bornes `[)`. Ecrire
#  `starts_at <= :instant AND (ends_at IS NULL OR ends_at > :instant)` dirait la
#  meme chose et n'emploierait PAS l'index gist qui existe pour cela.
_RESPONSABILITES = text(
    """
    SELECT f.responsibility_type, p.id, p.first_name, p.last_name
    FROM framework_responsibility_assignment AS f
    JOIN person AS p ON p.id = f.person_id
    WHERE f.entity_id = :entite
      AND f.archived_at IS NULL
      AND f.period @> :instant
    ORDER BY f.responsibility_type, p.last_name, p.first_name, p.id
    """
)

_CERCLES = text(
    """
    SELECT c.id, c.code, c.name, c.description, c.color_token,
           b.id, b.first_name, b.last_name,
           (SELECT count(*)
              FROM circle_membership AS m
             WHERE m.circle_id = c.id
               AND m.archived_at IS NULL
               AND m.period @> :instant) AS membres
      FROM circle AS c
      LEFT JOIN framework_responsibility_assignment AS fr
             ON fr.circle_id = c.id
            AND fr.entity_id = c.entity_id
            AND fr.responsibility_type = 'BOOSTER'
            AND fr.archived_at IS NULL
            AND fr.period @> :instant
      LEFT JOIN person AS b ON b.id = fr.person_id
     WHERE c.entity_id = :entite
       AND c.archived_at IS NULL
     ORDER BY c.display_order, c.code
    """
)

_BUREAUX = text(
    """
    SELECT o.id, o.code, o.name, o.description, o.location_text,
           r.id, r.first_name, r.last_name
      FROM office AS o
      LEFT JOIN framework_responsibility_assignment AS fr
             ON fr.office_id = o.id
            AND fr.entity_id = o.entity_id
            AND fr.responsibility_type = 'OFFICE_MANAGER'
            AND fr.archived_at IS NULL
            AND fr.period @> :instant
      LEFT JOIN person AS r ON r.id = fr.person_id
     WHERE o.entity_id = :entite
       AND o.archived_at IS NULL
     ORDER BY o.display_order, o.code, r.last_name, r.first_name
    """
)


def _titulaire(identifiant: Any, prenom: Any, nom: Any) -> TitulaireFramework:
    return TitulaireFramework(identifiant=identifiant, prenom=str(prenom), nom=str(nom))


def lire_la_page_framework(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    code_entite: str,
    instant: dt.datetime | None = None,
) -> PageFramework:
    """Les trois familles de cartes d'une entite, a un instant.

    **`instant` EST UN ARGUMENT ET NON UN `now()` ENFOUI.** Une responsabilite
    FUTURE ne designe personne aujourd'hui, et une periode close non plus : sans
    instant explicite, aucun test ne pourrait faire avancer le temps pour le
    prouver. C'est le temoin qui a le plus servi en `T5` du LOT 5 -- celui ou
    seul l'instant bouge.
    """
    maintenant = instant if instant is not None else dt.datetime.now(dt.UTC)
    liaison = {"entite": entite, "instant": maintenant}

    #  --- famille 1 : les responsabilites ---
    par_type: dict[str, list[TitulaireFramework]] = {t: [] for t in RESPONSABILITES_FRAMEWORK}
    for type_de_responsabilite, identifiant, prenom, nom in connexion.execute(
        _RESPONSABILITES, liaison
    ):
        #  Un type inconnu ne peut pas arriver -- la contrainte de verification de
        #  `T8` du LOT 2 le refuse -- mais le `setdefault` evite qu'un ajout futur
        #  fasse disparaitre des titulaires EN SILENCE.
        par_type.setdefault(str(type_de_responsabilite), []).append(
            _titulaire(identifiant, prenom, nom)
        )

    responsabilites = tuple(
        CarteDeResponsabilite(
            type_de_responsabilite=nom_du_type,
            titulaires=tuple(par_type.get(nom_du_type, ())),
            chemin_detaille=(
                chemin_de_la_responsabilite(code_entite, nom_du_type)
                if nom_du_type in RESPONSABILITES_A_PAGE_PROPRE
                else None
            ),
        )
        #  L'ordre vient de l'ENUMERATION : voir sa docstring.
        for nom_du_type in RESPONSABILITES_FRAMEWORK
    )

    #  --- famille 2 : les cercles ---
    cercles = tuple(
        CarteDeCercle(
            identifiant=ligne[0],
            code=str(ligne[1]),
            nom=str(ligne[2]),
            description=None if ligne[3] is None else str(ligne[3]),
            #  **LE GARDE DU DEFAUT `T10-8`.** `str(None)` rendrait « None ».
            jeton_de_couleur=None if ligne[4] is None else str(ligne[4]),
            booster=None if ligne[5] is None else _titulaire(ligne[5], ligne[6], ligne[7]),
            membres_actifs=int(ligne[8]),
            chemin_detaille=chemin_du_cercle(code_entite, str(ligne[1])),
        )
        for ligne in connexion.execute(_CERCLES, liaison)
    )

    #  --- famille 3 : les bureaux ---
    #  Un bureau porte de UN a TROIS responsables (§8.4), donc la requete rend
    #  plusieurs lignes par bureau : elles sont regroupees en conservant l'ordre
    #  rendu par le SQL, qui est total.
    bureaux_par_code: dict[str, dict[str, Any]] = {}
    for ligne in connexion.execute(_BUREAUX, liaison):
        code_bureau = str(ligne[1])
        bureau = bureaux_par_code.setdefault(
            code_bureau,
            {
                "identifiant": ligne[0],
                "code": code_bureau,
                "nom": str(ligne[2]),
                "description": None if ligne[3] is None else str(ligne[3]),
                "localisation": None if ligne[4] is None else str(ligne[4]),
                "responsables": [],
            },
        )
        if ligne[5] is not None:
            bureau["responsables"].append(_titulaire(ligne[5], ligne[6], ligne[7]))

    bureaux = tuple(
        CarteDeBureau(
            identifiant=b["identifiant"],
            code=b["code"],
            nom=b["nom"],
            description=b["description"],
            localisation=b["localisation"],
            responsables=tuple(b["responsables"]),
            chemin_detaille=chemin_du_bureau(code_entite, b["code"]),
        )
        for b in bureaux_par_code.values()
    )

    return PageFramework(responsabilites=responsabilites, cercles=cercles, bureaux=bureaux)


#  ---------------------------------------------------------------------------
#  Les chemins des pages detaillees — le critere d'acceptation dit « les cartes
#  MENENT aux pages detaillees », donc chaque carte porte son adresse.
#
#  **CE SONT DES CHEMINS D'ECRAN, PAS D'API**, et ils sont construits ici parce
#  que c'est ici qu'on sait a quoi une carte mene. Les ecrans qui les serviront
#  sont `T9` ; que la cible n'existe pas encore ne rend pas l'adresse fausse.
#  ---------------------------------------------------------------------------
def chemin_de_la_responsabilite(code_entite: str, type_de_responsabilite: str) -> str:
    return f"/entites/{code_entite}/framework/responsabilites/{type_de_responsabilite.lower()}"


def chemin_du_cercle(code_entite: str, code_cercle: str) -> str:
    return f"/entites/{code_entite}/framework/cercles/{code_cercle}"


def chemin_du_bureau(code_entite: str, code_bureau: str) -> str:
    return f"/entites/{code_entite}/framework/bureaux/{code_bureau}"
