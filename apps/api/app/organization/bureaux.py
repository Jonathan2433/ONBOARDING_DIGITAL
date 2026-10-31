"""La page detaillee d'un bureau — LOT 6, `T4`, story `MVP-L06-US003`.

CE QUE LE CRITERE DEMANDE, MOT POUR MOT

  « **BDS, BDE et BDG sont configurables ; un a trois responsables actifs sont
  affiches.** »

  Le cahier §10.3 le redit du cote produit : la page Framework fournit « une vue
  synthetique sous forme de cartes **et des pages detaillees** » pour les
  responsabilites, les cercles et **les bureaux**. `T2` a servi les cartes et
  emet deja `chemin_du_bureau(...)` ; ce chemin ne menait nulle part. C'est
  cette sous-etape qui le sert.

LES TROIS BUREAUX SONT DES DONNEES, PAS UNE ENUMERATION

  « Bureaux initiaux : BDS ; BDE ; BDG. **Ils restent entierement
  configurables.** » Aucun de ces trois codes n'apparait donc dans ce module ni
  dans son test : le bureau est resolu **par son code en base**, et le decor
  emploie des codes qui ne sont aucun des trois. Un `grep` sur `BDS` dans
  `app/` doit rester vide, et c'est ce que `T11` prouvera a l'echelle en creant
  une entite neuve.

QUI LIT — LA MATRICE §5, ET NON L'ANNEXE A

  Le §5 donne « **Bureaux** | ANON — | EMP Lecture | NEW Lecture | DSM | ESM |
  BOOST | OFFICE | ADM-E | SUPER Lecture » : **huit roles authentifies, sans
  distinction**. Aucun role n'est examine ici, comme pour le Framework de `T2`
  et les cercles de `T3`.

  **Les tableaux §10.x de l'annexe A n'ont ni colonne `EMP` ni colonne `NEW`** :
  les lire seuls aurait exclu l'acteur que la story nomme -- « **Employe** :
  Consulter les pages des bureaux ». Ils reglent la MODIFICATION, pas la
  consultation.

LES RESPONSABLES NE SE PAGINENT PAS, ET C'EST LE RAISONNEMENT DE `T3` A L'ENVERS

  `T3` pagine les membres d'un cercle parce que le §18.2 -- intitule
  « Pagination », dans le chapitre **API**, ne nommant aucune ressource -- vaut
  pour toute **POPULATION**. Les membres d'un cercle en sont une : rien ne borne
  leur nombre.

  **Les responsables d'un bureau ne sont pas une population.** Le §8.4 les
  declare **bornes** : « un bureau possede entre un et trois responsables actifs
  lorsqu'il est publie ». Paginer un ensemble de trois elements au plus
  inventerait un parametre que le cahier ne demande pas, et le §6.5 l'interdit.

  **La consequence est que `responsables` est un tuple de longueur LIBRE**, et
  ce module n'ecrit nulle part que sa longueur vaut de 1 a 3. Voir ci-dessous :
  la borne n'est pas tenue.

LA BORNE DU §8.4 N'EST PAS TENUE EN BASE, ET CE MODULE NE DOIT PAS LA SUPPOSER

  **`DEC-583`, 15/09/2026.** « Entre un et trois » est un **comptage borne**, et
  aucune contrainte de ligne ni index ne sait l'exprimer : il demande un
  declencheur. `DEC-576` l'avait dit sans dire OU, et le §8 de `fiche-lot-6.md`
  l'attribuait a cette sous-etape.

  **Il va a `T7`, et c'est une mesure qui l'a tranche** : la borne ne mord
  « **lorsqu'il est publie** », or au 15/09/2026 **aucune route n'ecrit dans
  `content_page`** -- zero occurrence de `INSERT INTO content_page` et de
  `UPDATE content_page` dans `app/`. Un declencheur pose ici n'aurait donc
  **aucun ecrivain** pour l'exercer avant `T7` : son temoin positif -- publier
  un bureau conforme et voir la borne laisser passer -- vivrait dans une
  sous-etape ulterieure, ce que le §7.39 a appris a refuser au LOT 5 quand `T5`
  et `T6` ont du fusionner pour exactement cette raison.

  **Ce que cette sous-etape en fait, elle, est de ne pas mentir.** Son decor
  produit ce que la borne interdit -- un bureau **publie** a **ZERO**
  responsable, un autre a **QUATRE** -- et exige que la lecture les rende tels
  quels. Un service qui aurait suppose « au moins un » se serait effondre sur le
  premier, et un qui aurait tronque a trois aurait **menti** sur le second.

POURQUOI `publie` EST SERVI, ET CE QU'IL N'EST PAS

  **`DEC-576`** : un bureau est « publie » au sens du §8.4 quand sa
  `content_page` de type `OFFICE` est a l'etat `published`. La table `office`
  **ne porte aucun etat de publication** -- verifie sur le schema : `code`,
  `name`, `description`, `location_text`, `display_order`, les champs communs du
  §3.1 et `archived_at`, rien d'autre.

  Sans ce booleen, la reponse ne saurait pas distinguer un ZERO **legitime** --
  un bureau en brouillon n'a encore personne -- d'un zero qui **enfreint** le
  §8.4. C'est le minimum qui rend la borne lisible, et c'est tout ce qui est
  servi : **ce module ne rend aucun bloc**. Le rendu editorial est `T5`.

  `EXISTS` et non une jointure : l'unicite posee par `T1` porte sur
  `(entity_id, page_type, slug)`, si bien que plusieurs pages `OFFICE`
  coexistent legitimement dans une entite. « Au moins une page publiee » est la
  seule lecture qui ne suppose pas ce que le modele n'ecrit pas.

CE QUE CE MODULE NE REND PAS

  **Un bureau ARCHIVE n'est pas rendu**, et la route en fait un 404
  indistinguable des autres causes -- meme parti que `T3`, meme motif : le §10.2
  porte une ligne « Restaurer », donc une lecture d'archive viendra, avec sa
  **propre** route et sa propre grille de roles (§7.41).

  **Aucun membre.** Un bureau n'en a pas : `ECART-059` est clos par `DEC-576`
  avec la recommandation du registre suivie -- **aucune table d'appartenance a un
  bureau n'est creee**. Un bureau a des **responsables**, et rien d'autre.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.media.photo import CONDITIONS_DE_LA_MINIATURE, ETAT_AFFICHABLE, VARIANTE_DE_LISTE
from app.organization.framework import TitulaireAvecPhoto, chemin_du_bureau
from app.people.modeles import ETAT_LISTE, VISIBILITE_LISTEE

#  Le bureau lui-meme, et son etat de PUBLICATION au sens de `DEC-576`.
#
#  `location_text` est « Facultatif » au §8.3 : il est donc NULLABLE, et
#  `str(None)` y rendrait la chaine « None » exactement comme sur le jeton de
#  couleur d'un cercle pendant deux lots (defaut `T10-8`). Le decor porte le
#  COUPLE du §7.42 -- un bureau avec localisation, un bureau sans.
_BUREAU = text(
    """
    SELECT o.id, o.code, o.name, o.description, o.location_text,
           EXISTS (
               SELECT 1
                 FROM content_page AS cp
                WHERE cp.office_id = o.id
                  AND cp.entity_id = o.entity_id
                  AND cp.page_type = 'OFFICE'
                  AND cp.state = 'published'
                  AND cp.archived_at IS NULL
           )
      FROM office AS o
     WHERE o.entity_id = :entite
       AND o.code = :code_bureau
       AND o.archived_at IS NULL
    """
)

#  **LES MEMES CONDITIONS QUE LA CARTE DE `T2`**, et pour la meme raison qu'en
#  `T3` : une seconde ecriture des filtres divergerait au premier ajout (§7.27).
#  `period @> :instant` ecarte une periode close ou future -- une affectation
#  qui commence demain ne designe personne aujourd'hui.
#
#  **`responsibility_type = 'OFFICE_MANAGER'` EST REDONDANT AUJOURD'HUI, ET LE
#  TEMOIN L'A PROUVE.** Le retirer laisse les vingt-trois tests verts : la
#  contrainte `ck_framework_responsibility_assignment_portee_selon_le_type`
#  impose `office_id IS NULL` a tout `BOOSTER` et aux deux scopes de `DSM` et
#  `ESM`, si bien que `fr.office_id = :bureau` suffit a ecarter les autres types.
#
#  **Il est conserve parce qu'il dit l'intention de la requete**, et parce que la
#  carte de `T2` le porte -- deux lectures du meme fait qui divergeraient sinon.
#  Mais il n'est PAS ce qui protege, et c'est pourquoi la protection reelle est
#  un test qui exige que la base CONTINUE d'interdire cet etat, sur le nom de la
#  contrainte violee (§7.32). Defaut `T4-2`.
#
#  **L'ORDRE EST TOTAL, ET LA CLE PRIMAIRE EN EST LE DERNIER TERME.** Sans elle,
#  deux homonymes rendraient un ordre non deterministe d'un appel a l'autre.
#
#  **LA PHOTO D'UN RESPONSABLE, CHANTIER FRONT S12 (`DEC-673`).** `LEFT JOIN`
#  sur `entity_membership` : un responsable n'a pas TOUJOURS une appartenance
#  active et listee dans cette entite (le decor de test en cree sans) -- sans
#  elle, `em` est NULL et l'`EXISTS` rend faux, meme parti que le Booster d'un
#  cercle (`app.organization.cercles`). L'alias `em` est CELUI que
#  `CONDITIONS_DE_LA_MINIATURE` attend (voir `app.media.photo`).
_RESPONSABLES = text(
    f"""
    SELECT r.id, r.first_name, r.last_name, em.id,
           EXISTS (SELECT 1 {CONDITIONS_DE_LA_MINIATURE}) AS a_une_photo
      FROM framework_responsibility_assignment AS fr
      JOIN person AS r ON r.id = fr.person_id
      LEFT JOIN entity_membership AS em
             ON em.person_id = r.id
            AND em.entity_id = fr.entity_id
            AND em.archived_at IS NULL
            AND em.membership_state = :etat
            AND em.profile_visibility = :visibilite
     WHERE fr.office_id = :bureau
       AND fr.entity_id = :entite
       AND fr.responsibility_type = 'OFFICE_MANAGER'
       AND fr.archived_at IS NULL
       AND fr.period @> :instant
     ORDER BY r.last_name, r.first_name, fr.id
    """  # noqa: S608 — le seul fragment interpole est une constante de ce module
)


@dataclasses.dataclass(frozen=True, slots=True)
class BureauDetaille:
    """Un bureau, ses responsables ACTIFS, et son etat de publication.

    **`responsables` N'EST PAS BORNE PAR CE TYPE, ET C'EST DELIBERE.** Le §8.4
    veut « entre un et trois responsables actifs lorsqu'il est publie » ; aucune
    contrainte de base ne l'exprime, et le declencheur qui le fera est pose en
    `T7`, la ou la publication a un ecrivain (`DEC-583`). Ce type rend donc ce
    que la base contient : zero, un, ou quatre.
    """

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    #  §8.3 : « `location_text` | Facultatif ». NULLABLE, donc jamais `str(...)`.
    localisation: str | None
    responsables: tuple[TitulaireAvecPhoto, ...]
    #  `DEC-576` : porte par la page de contenu, jamais par la table `office`.
    publie: bool
    chemin_detaille: str

    @property
    def nombre_de_responsables(self) -> int:
        """Le compte reel, jamais le compte attendu.

        Il est expose parce que c'est la grandeur que le §8.4 borne, et un client
        qui voudrait signaler l'ecart n'a ainsi rien a recompter. **Il peut valoir
        zero, et il peut depasser trois** : voir le docstring du module.
        """
        return len(self.responsables)


def lire_le_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    code_entite: str,
    code_bureau: str,
    instant: dt.datetime | None = None,
) -> BureauDetaille | None:
    """Un bureau et ses responsables actifs, ou `None` s'il n'est pas rendable.

    **`None` COUVRE TROIS CAUSES A DESSEIN** : le code est inconnu, le bureau
    appartient a une AUTRE entite, ou il est archive. La route en fait un seul
    404 : distinguer apprendrait l'existence d'un bureau qu'on n'a pas a voir.

    **AUCUNE PAGINATION**, et ce n'est pas un oubli : les responsables sont un
    ensemble **borne** par le §8.4, non une population. Le §18.2 regit les
    populations, et paginer trois elements inventerait un parametre que le
    cahier ne demande pas (§6.5).
    """
    maintenant = instant if instant is not None else dt.datetime.now(dt.UTC)

    ligne = connexion.execute(_BUREAU, {"entite": entite, "code_bureau": code_bureau}).one_or_none()
    if ligne is None:
        return None

    responsables = tuple(
        TitulaireAvecPhoto(
            identifiant=r[0],
            prenom=str(r[1]),
            nom=str(r[2]),
            appartenance=r[3],
            a_une_photo=bool(r[4]),
        )
        for r in connexion.execute(
            _RESPONSABLES,
            {
                "bureau": ligne[0],
                "entite": entite,
                "instant": maintenant,
                "etat": ETAT_LISTE,
                "visibilite": VISIBILITE_LISTEE,
                "etat_media": ETAT_AFFICHABLE,
                "variante": VARIANTE_DE_LISTE,
            },
        )
    )

    return BureauDetaille(
        identifiant=ligne[0],
        code=str(ligne[1]),
        nom=str(ligne[2]),
        description=None if ligne[3] is None else str(ligne[3]),
        #  **LE GARDE DU DEFAUT `T10-8`**, ici sur `location_text`.
        localisation=None if ligne[4] is None else str(ligne[4]),
        responsables=responsables,
        publie=bool(ligne[5]),
        chemin_detaille=chemin_du_bureau(code_entite, str(ligne[1])),
    )
