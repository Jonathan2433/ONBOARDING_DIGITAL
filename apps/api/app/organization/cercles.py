"""La page detaillee d'un cercle — LOT 6, `T3`, story `MVP-L06-US002`.

CE QUE LE CRITERE DEMANDE, MOT POUR MOT

  « Les huit cercles initiaux sont configurables ; **couleur, description,
  membres et Booster** sont affiches **sans reposer uniquement sur la couleur**. »

LA COULEUR N'EST JAMAIS SEULE, ET C'EST LE MODELE QUI L'EXIGE

  Le §8.1 porte, parmi les contraintes de `circle` : « **la couleur ne constitue
  jamais la seule information visuelle** ». Ce n'est donc pas qu'un critere de
  sortie de la roadmap : c'est une regle du modele.

  **Elle est tenue par la STRUCTURE et non par un controle.** `code` et `nom` sont
  des champs obligatoires, `jeton_de_couleur` est `str | None` : il n'existe
  aucune valeur de ce type ou le jeton serait present et le nom absent. §7.35.

QUI LIT — LA MATRICE §5, ET NON L'ANNEXE A

  Le §5 donne « Cercles | ANON — | EMP Lecture | NEW Lecture | ... » : **huit
  roles authentifies, sans distinction**. Aucun role n'est examine ici, comme
  pour le Framework de `T2`. **L'annexe A §10.2 n'a ni colonne `EMP` ni colonne
  `NEW`** : la lire seule aurait exclu l'acteur que la story nomme.

LES MEMBRES SONT PAGINES, ET LE §18.2 NE SE RESTREINT PAS AU TROMBINOSCOPE

  Il s'intitule « Pagination », vit dans le chapitre **API** du cahier, et ne
  nomme **aucune** ressource : « 25 par defaut ; options 25, 50 et 100 ; maximum
  100 ». Une page de cercle rend une POPULATION, donc elle se pagine.

  Les tailles viennent de `app/shared/pagination.py` -- **une seule declaration
  pour tout le projet**, deplacee la le 14/09/2026 precisement parce que `T3` en
  est le second consommateur et que `organization` ne peut pas importer `people`.

LA VISIBILITE EST REUTILISEE, JAMAIS REDECLAREE

  `ETAT_LISTE` et `VISIBILITE_LISTEE` vivent dans `app/people/modeles.py` avec
  leur motif : le §22.5 etape 5 « masquage du profil » n'est implemente nulle
  part, donc un partant reste `published` ; et un nouvel arrivant est `active` des
  son arrivee avec un profil `draft`. **Les deux filtres sont necessaires.**
  En ecrire une copie ici les ferait diverger au premier ajout -- §7.27.

CE QUE CE MODULE NE REND PAS

  **Un cercle ARCHIVE n'est pas rendu**, et la route en fait un 404 indistinguable
  des autres causes. Le §10.2 porte bien une ligne « Restaurer un cercle », donc
  une lecture d'archive viendra -- et elle aura sa **propre** route avec sa propre
  grille de roles, comme `fiche-archivee` au LOT 5 `T8`. Elargir celle-ci
  confondrait deux droits que la matrice separe (§7.41).

  **Aucun contenu editorial.** `content_page` existe depuis `T1`, mais cette page
  est structurelle. Les blocs sont le sujet de `T5`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import math
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.media.photo import CONDITIONS_DE_LA_MINIATURE, ETAT_AFFICHABLE, VARIANTE_DE_LISTE
from app.organization.framework import TitulaireAvecPhoto, chemin_du_cercle
from app.people.modeles import ETAT_LISTE, VISIBILITE_LISTEE
from app.shared.pagination import TAILLES_DE_PAGE


@dataclasses.dataclass(frozen=True, slots=True)
class MembreDuCercle:
    """Une personne membre du cercle, a l'instant de l'appel.

    `type_d_appartenance` vaut `principal` ou `secondary` -- §8.2, et la
    distinction n'est pas decorative : `ARB-DROIT-004` donne au Booster la
    gestion de l'appartenance **secondaire** et lui refuse le cercle principal,
    le DSM, le client et le statut d'un membre seulement secondaire.

    `a_une_photo` — chantier front hors lot, `S12` (`DEC-673`) : le MEME
    `EXISTS` que le trombinoscope (`CONDITIONS_DE_LA_MINIATURE`), jamais une
    seconde regle qui pourrait diverger — §7.27. `appartenance` est deja
    exactement l'`entity_membership.id` qu'attend `resoudre_la_miniature`.
    """

    appartenance: uuid.UUID
    prenom: str
    nom: str
    type_d_appartenance: str
    a_une_photo: bool


@dataclasses.dataclass(frozen=True, slots=True)
class CercleDetaille:
    """Un cercle et une PAGE de ses membres."""

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    #  **NULLABLE AU CATALOGUE.** `str(None)` rendrait la chaine « None », servie
    #  sur 100 % des cercles pendant deux lots -- defaut `T10-8`.
    jeton_de_couleur: str | None
    booster: TitulaireAvecPhoto | None
    membres: tuple[MembreDuCercle, ...]
    total_des_membres: int
    page: int
    taille: int
    chemin_detaille: str

    @property
    def pages(self) -> int:
        """Le nombre de pages, jamais inferieur a 1.

        Une population vide rend **une** page vide et non zero : un client qui
        lirait `pages == 0` ne saurait pas s'il doit afficher « aucun membre » ou
        « chargement ». C'est le parti du trombinoscope de `T2` du LOT 5.
        """
        return max(1, math.ceil(self.total_des_membres / self.taille))


#  Le cercle lui-meme, avec son Booster ACTIF. `LEFT JOIN` sur la
#  responsabilite : un cercle sans Booster est parfaitement legitime, et un
#  `INNER JOIN` le ferait disparaitre -- ce qui donnerait un 404 la ou la
#  ressource existe.
#
#  **LA PHOTO DU BOOSTER, CHANTIER FRONT S12 (`DEC-673`).** `LEFT JOIN` sur
#  `entity_membership` aussi : un Booster n'a pas TOUJOURS une appartenance
#  active et listee dans cette entite (le decor de `T3` en cree sans, et rien
#  dans le modele ne l'interdit) -- sans elle, `em` est NULL et l'`EXISTS` rend
#  faux, exactement comme pour un titulaire sans aucune photo. L'alias `em` est
#  CELUI que `CONDITIONS_DE_LA_MINIATURE` attend (voir `app.media.photo`).
_CERCLE = text(
    f"""
    SELECT c.id, c.code, c.name, c.description, c.color_token,
           b.id, b.first_name, b.last_name, em.id,
           EXISTS (SELECT 1 {CONDITIONS_DE_LA_MINIATURE}) AS booster_a_une_photo
      FROM circle AS c
      LEFT JOIN framework_responsibility_assignment AS fr
             ON fr.circle_id = c.id
            AND fr.entity_id = c.entity_id
            AND fr.responsibility_type = 'BOOSTER'
            AND fr.archived_at IS NULL
            AND fr.period @> :instant
      LEFT JOIN person AS b ON b.id = fr.person_id
      LEFT JOIN entity_membership AS em
             ON em.person_id = b.id
            AND em.entity_id = c.entity_id
            AND em.archived_at IS NULL
            AND em.membership_state = :etat
            AND em.profile_visibility = :visibilite
     WHERE c.entity_id = :entite
       AND c.code = :code_cercle
       AND c.archived_at IS NULL
    """  # noqa: S608 — le seul fragment interpole est une constante de ce module
)

#  **LES DEUX FILTRES DE VISIBILITE SONT CEUX DU TROMBINOSCOPE**, lus de
#  `app/people/modeles.py`. Les reecrire ici en dur les ferait diverger.
_CONDITIONS_DES_MEMBRES = """
      FROM circle_membership AS cm
      JOIN entity_membership AS em
        ON em.id = cm.entity_membership_id
       AND em.entity_id = cm.entity_id
      JOIN person AS p ON p.id = em.person_id
     WHERE cm.circle_id = :cercle
       AND cm.entity_id = :entite
       AND cm.archived_at IS NULL
       AND cm.period @> :instant
       AND em.archived_at IS NULL
       AND em.membership_state = :etat
       AND em.profile_visibility = :visibilite
"""

_COMPTE_DES_MEMBRES = text("SELECT count(*)" + _CONDITIONS_DES_MEMBRES)

#  **L'ORDRE EST TOTAL, ET LA CLE PRIMAIRE EN EST LE DERNIER TERME.** Sans elle,
#  deux homonymes rendraient un ordre non deterministe entre deux pages : une
#  ligne pourrait paraitre deux fois ou jamais. Defaut corrige en `T2` du LOT 5.
#
#  **`a_une_photo`, CHANTIER FRONT S12 (`DEC-673`).** Le MEME `EXISTS` que le
#  trombinoscope, `em` deja alias ici par `_CONDITIONS_DES_MEMBRES` -- une
#  seconde requete par ligne serait le N+1 que le critere de `T3` interdit
#  (voir l'en-tete de `CONDITIONS_DE_LA_MINIATURE`, `app.media.photo`).
_MEMBRES = text(
    "SELECT em.id, p.first_name, p.last_name, cm.membership_type, "
    f"EXISTS (SELECT 1 {CONDITIONS_DE_LA_MINIATURE}) AS a_une_photo"
    + _CONDITIONS_DES_MEMBRES
    + " ORDER BY p.last_name, p.first_name, em.id LIMIT :limite OFFSET :decalage"
)


def lire_le_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    code_entite: str,
    code_cercle: str,
    page: int = 1,
    taille: int = 25,
    instant: dt.datetime | None = None,
) -> CercleDetaille | None:
    """Un cercle et une page de ses membres, ou `None` s'il n'est pas rendable.

    **`None` COUVRE TROIS CAUSES A DESSEIN** : le code est inconnu, le cercle
    appartient a une AUTRE entite, ou il est archive. La route en fait un seul
    404 : distinguer apprendrait l'existence d'un cercle qu'on n'a pas a voir.

    **LA TAILLE EST VERIFIEE ICI AUSSI, ET CE N'EST PAS UNE REDONDANCE.** Ce
    service est appelable hors HTTP -- un export, un script -- et une fonction qui
    accepterait 10 000 rendrait la borne du cahier **dependante de son
    appelant**. La route, elle, la refuse par le TYPE, et le format du §18.3 est
    produit par le gestionnaire de validation. Lecon `T2-3` du LOT 5.
    """
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)

    maintenant = instant if instant is not None else dt.datetime.now(dt.UTC)

    #  Les parametres de `CONDITIONS_DE_LA_MINIATURE`, chantier front S12.
    photo_liaison: dict[str, Any] = {"etat_media": ETAT_AFFICHABLE, "variante": VARIANTE_DE_LISTE}

    ligne = connexion.execute(
        _CERCLE,
        {
            "entite": entite,
            "code_cercle": code_cercle,
            "instant": maintenant,
            "etat": ETAT_LISTE,
            "visibilite": VISIBILITE_LISTEE,
            **photo_liaison,
        },
    ).one_or_none()
    if ligne is None:
        return None

    liaison: dict[str, Any] = {
        "cercle": ligne[0],
        "entite": entite,
        "instant": maintenant,
        "etat": ETAT_LISTE,
        "visibilite": VISIBILITE_LISTEE,
        **photo_liaison,
    }
    total = int(connexion.execute(_COMPTE_DES_MEMBRES, liaison).scalar_one())
    membres = tuple(
        MembreDuCercle(
            appartenance=m[0],
            prenom=str(m[1]),
            nom=str(m[2]),
            type_d_appartenance=str(m[3]),
            a_une_photo=bool(m[4]),
        )
        for m in connexion.execute(
            _MEMBRES, {**liaison, "limite": taille, "decalage": (page - 1) * taille}
        )
    )

    return CercleDetaille(
        identifiant=ligne[0],
        code=str(ligne[1]),
        nom=str(ligne[2]),
        description=None if ligne[3] is None else str(ligne[3]),
        #  **LE GARDE DU DEFAUT `T10-8`.**
        jeton_de_couleur=None if ligne[4] is None else str(ligne[4]),
        booster=(
            None
            if ligne[5] is None
            else TitulaireAvecPhoto(
                identifiant=ligne[5],
                prenom=str(ligne[6]),
                nom=str(ligne[7]),
                appartenance=ligne[8],
                a_une_photo=bool(ligne[9]),
            )
        ),
        membres=membres,
        total_des_membres=total,
        page=page,
        taille=taille,
        chemin_detaille=chemin_du_cercle(code_entite, str(ligne[1])),
    )
