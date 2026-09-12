"""La fiche profil complete — story `MVP-L05-US004`.

LOT 5, sous-etape `T4`.

CE QUE LA MATRICE MASQUE : RIEN, ET C'EST MESURE

  Le critere de `T4` dit « chaque champ visible **ou** masque selon la matrice ».
  **La matrice ne definit aucune visibilite par CHAMP.** Mesure du 26/08/2026 :

    « regles de visibilite »   2 occurrences dans tout le corpus, et ce sont
                               les DEUX copies du critere de `US004` lui-meme
    « masquer » dans la
    matrice                    une seule phrase, et elle porte sur les ACTIONS :
                               « le frontend peut masquer ou afficher les
                               ACTIONS [...] mais l'API reste l'autorite finale »

  Les regles applicables sont donc celles du **§5**, qui traite « Fiches
  collaborateur », « Statut mission/intercontrat » et « Client actif » comme
  **trois ressources distinctes** -- et donne « Lecture » aux **huit** roles
  authentifies sur chacune. Le §6.1 ajoute « Consulter un profil actif : coche
  pour les huit ». **Aucun champ n'est masque a un role authentifie.**

  Inventer un masquage serait le §6.5. **Un test FIGE donc l'absence** : si un lot
  ulterieur veut masquer un champ, il devra casser ce test, donc le decider
  (§7.32). `ECART-051`.

  Ce qui est reellement masque l'est ailleurs, et par d'autres regles :

    `ANON`               aucune session, aucun acces -- porte par
                         `exiger_une_session`
    l'etat du profil     `draft`, `hidden`, `departed`, `archived` : la meme
                         population que `T2`, et pour la meme raison
    la PHOTO             §12.2, `photo_authorization` : sans autorisation, avatar
                         neutre. C'est `T6`, et la fiche ne porte aujourd'hui
                         AUCUNE trace de photo

TREIZE CHAMPS, ET LEUR CARDINALITE EST PROUVEE PAR LE SCHEMA

  Le §10.2 en donne treize. Cinq relations sont **uniques a un instant donne**, et
  ce ne sont pas des suppositions : des contraintes d'EXCLUSION l'imposent.

    metier             `ex_membership_job_assignment_sans_chevauchement`
    statut et client   `ex_professional_status_assignment_sans_chevauchement`
    DSM                `ex_dsm_assignment_sans_chevauchement`
    cercle principal   `ex_circle_membership_principal_sans_chevauchement`

  **Une jointure ne peut donc pas multiplier les lignes**, et c'est le SCHEMA qui
  le garantit -- pas une relecture. Un test exige que ces quatre contraintes
  continuent d'exister : le jour ou l'une serait relachee, la requete de ce module
  deviendrait fausse **en silence**, et celui qui la relache doit le savoir
  (§7.32).

  Deux relations sont **multiples**, et leurs exclusions le disent aussi :
  `framework_responsibility_assignment` n'exclut le chevauchement que **par type**
  pour `DSM`/`ESM`, **par cercle** pour `BOOSTER` et **par bureau** pour
  `OFFICE_MANAGER` -- une personne peut donc cumuler. Et `circle_membership`
  n'unifie que le **principal** : les secondaires sont plusieurs (§8.2).

TROIS REQUETES, CONSTANTES, ET COMPTEES

  Une pour la fiche et ses cinq relations uniques ; une pour les cercles
  secondaires ; une pour les responsabilites. **Trois quel que soit le contenu**,
  et un test les compte en ecoutant le pilote -- c'est le critere « aucun N+1 »
  de `T3`, applique ici sans qu'il soit ecrit.

  Les joindre toutes en une seule requete multiplierait les lignes par le produit
  des deux relations multiples : trois cercles secondaires et deux
  responsabilites rendraient **six** lignes a recomposer en Python. Deux requetes
  de plus coutent moins que cette recomposition, et se comptent.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.people.modeles import (
    ETAT_LISTE,
    VISIBILITE_LISTEE,
    VISIBILITES_PROFIL,
    EtatAppartenance,
)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  Les quatre contraintes d'exclusion qui rendent la jointure sure. **DECLAREES
#  ET CONFRONTEES AU REEL** : un test exige qu'elles existent toutes, parce que
#  c'est d'elles que depend l'absence de multiplication (§7.27).
EXCLUSIONS_QUI_RENDENT_LA_JOINTURE_SURE: Final[tuple[str, ...]] = (
    "ex_membership_job_assignment_sans_chevauchement",
    "ex_professional_status_assignment_sans_chevauchement",
    "ex_dsm_assignment_sans_chevauchement",
    "ex_circle_membership_principal_sans_chevauchement",
)


@dataclasses.dataclass(frozen=True, slots=True)
class CercleDuProfil:
    """Un cercle, principal ou secondaire."""

    code: str
    nom: str
    #  **NULLABLE AU CATALOGUE** : `circle.color_token` rend `is_nullable = YES`.
    #  Ce defaut est celui de `T10-8`, et il est ne ICI, en `T4` : `T10` n'a fait
    #  que le recopier dans la liste. Corriger la seule instance que je venais
    #  d'ecrire aurait ete le §7.40 exactement -- une correction qui ne couvre que
    #  les fichiers sous la main.
    jeton_de_couleur: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class ResponsabiliteDuProfil:
    """Une responsabilite Framework et sa portee.

    **La portee est le cercle OU le bureau, jamais les deux** : le §8.4 le pose
    par une contrainte de verification -- `BOOSTER` exige un cercle, `OFFICE_MANAGER`
    un bureau, `DSM` et `ESM` ni l'un ni l'autre.
    """

    type: str
    cercle: str | None
    bureau: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class FicheProfil:
    """Les treize champs du §10.2, moins la photo, que la ROUTE resout a part.

    **« MOINS LA PHOTO » EST EXACT ICI, ET NE L'EST PAS DANS LA REPONSE.** Cette
    structure de domaine n'en porte aucune ; `_en_reponse` la recoit en argument
    et la joint. Le libelle disait « qui attend `T6` » -- une sous-etape que
    `DEC-564` a fusionnee dans `T5`, laquelle a livre la photo.
    """

    id: uuid.UUID
    #  **LA VERSION EST SERVIE DEPUIS `T11`, ET SANS ELLE AUCUN ECRAN NE PEUT
    #  ECRIRE.** Le §18.4 fait de `version` un champ OBLIGATOIRE du corps des
    #  trois ecritures -- `PATCH`, archivage, restauration -- et **aucun endpoint
    #  ne la servait** : mesure du 12/09/2026, zero occurrence dans la fiche comme
    #  dans le trombinoscope. `verifier-profil.py` la lisait en SQL DIRECT, ce
    #  qu'un navigateur ne peut pas faire. Le premier ecran qui a tente d'archiver
    #  a recu `422 Field required`. Defaut `T11-6`.
    version: int
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    professional_category: str
    arrival_date: dt.date
    short_bio: str | None
    fun_fact: str | None
    metier: str | None
    statut: str | None
    client: str | None
    dsm: str | None
    cercle_principal: CercleDuProfil | None
    cercles_secondaires: list[CercleDuProfil]
    responsabilites: list[ResponsabiliteDuProfil]


#  La fiche et ses CINQ relations uniques, en une requete. Les `LEFT JOIN` sont
#  surs parce que les exclusions ci-dessus interdisent deux lignes actives.
_FICHE: Final[str] = """
SELECT em.id, em.version, em.person_id, p.first_name, p.last_name, p.preferred_name,
       em.professional_category, em.arrival_date, em.short_bio, em.fun_fact,
       jc.label AS metier,
       ps.status AS statut,
       cl.display_name AS client,
       dp.first_name || ' ' || dp.last_name AS dsm,
       cp.code AS cercle_code, cp.name AS cercle_nom, cp.color_token AS cercle_couleur
FROM entity_membership AS em
JOIN person AS p ON p.id = em.person_id
LEFT JOIN membership_job_assignment AS mja
       ON mja.entity_membership_id = em.id AND mja.archived_at IS NULL
      AND mja.period @> :instant
LEFT JOIN job_catalog AS jc ON jc.id = mja.job_catalog_id
LEFT JOIN professional_status_assignment AS ps
       ON ps.entity_membership_id = em.id AND ps.archived_at IS NULL
      AND ps.period @> :instant
LEFT JOIN client AS cl ON cl.id = ps.client_id
LEFT JOIN dsm_assignment AS da
       ON da.consultant_membership_id = em.id AND da.archived_at IS NULL
      AND da.period @> :instant
LEFT JOIN person AS dp ON dp.id = da.dsm_person_id
LEFT JOIN circle_membership AS cm
       ON cm.entity_membership_id = em.id AND cm.archived_at IS NULL
      AND cm.period @> :instant AND cm.membership_type = 'principal'
LEFT JOIN circle AS cp ON cp.id = cm.circle_id
WHERE em.id = :appartenance AND em.entity_id = :entite
  AND em.membership_state = ANY(:etats) AND em.profile_visibility = ANY(:visibilites)
"""

_SECONDAIRES: Final[str] = """
SELECT c.code, c.name, c.color_token
FROM circle_membership AS cm JOIN circle AS c ON c.id = cm.circle_id
WHERE cm.entity_membership_id = :appartenance AND cm.archived_at IS NULL
  AND cm.period @> :instant AND cm.membership_type = 'secondary'
ORDER BY c.display_order, c.code
"""

#  Les responsabilites portent sur la PERSONNE et l'ENTITE, non sur
#  l'appartenance : le §8.4 les attache ainsi, et une personne peut en avoir dans
#  l'entite sans que cela tienne a une appartenance particuliere.
_RESPONSABILITES: Final[str] = """
SELECT fra.responsibility_type, c.name AS cercle, o.name AS bureau
FROM framework_responsibility_assignment AS fra
LEFT JOIN circle AS c ON c.id = fra.circle_id
LEFT JOIN office AS o ON o.id = fra.office_id
WHERE fra.person_id = :personne AND fra.entity_id = :entite
  AND fra.archived_at IS NULL AND fra.period @> :instant
ORDER BY fra.responsibility_type, c.name, o.name
"""


#  **LA POPULATION DES ARCHIVES, DERIVEE ET NON ECRITE.**
#
#  L'etat vient de l'enumeration ; les visibilites sont **les trois**, et cette
#  ouverture est motivee : l'archivage ne touche pas `profile_visibility`, si bien
#  qu'un archive peut etre `draft`, `published` ou `hidden`. Filtrer sur la
#  visibilite ferait echouer un acte que le §6.1 autorise, pour une raison que le
#  corpus n'ecrit nulle part -- et un controle qui refuse du legitime apprend a
#  passer outre (§7.25).
ETATS_ARCHIVES: Final[tuple[str, ...]] = (EtatAppartenance.ARCHIVED.value,)
TOUTES_LES_VISIBILITES: Final[tuple[str, ...]] = VISIBILITES_PROFIL


def lire_la_fiche(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    instant: dt.datetime,
    etats: tuple[str, ...] = (ETAT_LISTE,),
    visibilites: tuple[str, ...] = (VISIBILITE_LISTEE,),
) -> FicheProfil | None:
    """La fiche complete d'une appartenance, ou `None`.

    **`None` COUVRE TROIS CAS, ET C'EST VOULU** : l'appartenance n'existe pas,
    elle appartient a une AUTRE entite, ou son profil n'est pas listable. Les
    trois rendent le meme refus -- distinguer apprendrait qu'un brouillon existe,
    exactement comme pour les entites en `T2` du LOT 4.

    **LE FILTRE DE POPULATION EST CELUI DE `T2` PAR DEFAUT**, et il doit le
    rester pour cette route : une fiche accessible directement alors que la liste
    l'exclut rendrait le filtre de la liste decoratif.

    **`T8` DU LOT 5 EN A OUVERT UN SECOND, ET C'EST UN PARAMETRE, PAS UNE COPIE.**
    Le §6.1 donne « Consulter un profil archive » a l'ESM, a l'administrateur
    d'entite et au super-administrateur : c'est une AUTRE population, servie par
    une AUTRE route, avec sa propre grille de roles. Un second exemplaire de cette
    requete aurait diverge au premier champ ajoute -- `DEC-466`, et `T5` l'a paye
    sur les conditions de la miniature. Voir `lire_la_fiche_archivee`.

    Args:
        etats: les etats d'appartenance admissibles. `= ANY(:etats)` et non une
            egalite : c'est ce qui permet la seconde population sans composer de
            SQL, donc sans qu'un chemin de code puisse construire un `WHERE`.
        visibilites: les visibilites admissibles, meme motif.
    """
    parametres = {
        "appartenance": appartenance,
        "entite": entite,
        "etats": list(etats),
        "visibilites": list(visibilites),
        "instant": instant,
    }
    ligne = connexion.execute(text(_FICHE), parametres).one_or_none()
    if ligne is None:
        return None

    secondaires = [
        CercleDuProfil(code=str(c), nom=str(n), jeton_de_couleur=None if j is None else str(j))
        for c, n, j in connexion.execute(
            text(_SECONDAIRES), {"appartenance": appartenance, "instant": instant}
        )
    ]
    responsabilites = [
        ResponsabiliteDuProfil(
            type=str(t),
            cercle=None if c is None else str(c),
            bureau=None if b is None else str(b),
        )
        for t, c, b in connexion.execute(
            text(_RESPONSABILITES),
            {"personne": ligne.person_id, "entite": entite, "instant": instant},
        )
    ]

    principal = (
        None
        if ligne.cercle_code is None
        else CercleDuProfil(
            code=str(ligne.cercle_code),
            nom=str(ligne.cercle_nom),
            jeton_de_couleur=(None if ligne.cercle_couleur is None else str(ligne.cercle_couleur)),
        )
    )
    return FicheProfil(
        id=uuid.UUID(str(ligne.id)),
        version=int(ligne.version),
        person_id=uuid.UUID(str(ligne.person_id)),
        first_name=str(ligne.first_name),
        last_name=str(ligne.last_name),
        preferred_name=None if ligne.preferred_name is None else str(ligne.preferred_name),
        professional_category=str(ligne.professional_category),
        arrival_date=ligne.arrival_date,
        short_bio=None if ligne.short_bio is None else str(ligne.short_bio),
        fun_fact=None if ligne.fun_fact is None else str(ligne.fun_fact),
        metier=None if ligne.metier is None else str(ligne.metier),
        statut=None if ligne.statut is None else str(ligne.statut),
        client=None if ligne.client is None else str(ligne.client),
        dsm=None if ligne.dsm is None else str(ligne.dsm),
        cercle_principal=principal,
        cercles_secondaires=secondaires,
        responsabilites=responsabilites,
    )


def lire_la_fiche_archivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    instant: dt.datetime,
) -> FicheProfil | None:
    """La fiche d'un profil ARCHIVE — « Consulter un profil archive », §6.1.

    LOT 5, sous-etape `T8`.

    **UNE ROUTE DISTINCTE, ET NON UN ASSOUPLISSEMENT DE `lire_la_fiche`.** Le
    §6.1 traite « Consulter un profil actif » -- les huit roles -- et « Consulter
    un profil archive » -- trois roles, « besoin fonctionnel » -- comme deux
    lignes differentes. Elargir la premiere aurait fusionne deux droits que le
    document separe, et **casse le test qui fige le 404 d'un profil exclu**, dont
    c'est precisement le role.

    `None` couvre les memes trois cas que `lire_la_fiche`, plus un quatrieme :
    l'appartenance existe et n'est PAS archivee. Le refus est identique, et c'est
    voulu -- le §2.5 « refus par defaut ».
    """
    return lire_la_fiche(
        connexion,
        entite=entite,
        appartenance=appartenance,
        instant=instant,
        etats=ETATS_ARCHIVES,
        visibilites=TOUTES_LES_VISIBILITES,
    )
