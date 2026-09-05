"""Le trombinoscope en lecture — story `MVP-L05-US001`.

LOT 5, sous-etape `T2`.

QUI PEUT LIRE : LA MATRICE §5 NE DISTINGUE AUCUN ROLE

  Le tableau du §5 donne « Trombinoscope » a **`ANON` = tiret** et aux **huit**
  roles authentifies -- `EMP`, `NEW`, `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E`,
  `SUPER` -- tous a « Lecture ». Le cahier porte le meme tableau.

  Une session valide suffit donc, et son absence refuse. **`T2` n'emploie PAS
  `exiger_un_role_dans_l_entite`** : ajouter ici un controle de role exigerait
  plus que la matrice, ce qui est le defaut du §7.20 -- un controle qui echoue sur
  un livrable conforme. Le §5.1 n'y change rien : hors de son entite principale
  une personne n'a que `EMP`, et `EMP` a « Lecture » sur cette ressource.

CE QUI EST RENDU : QUATRE ETATS SONT EXCLUS, ET LES DEUX FILTRES SONT
NECESSAIRES

  Le §6.1 de la matrice distingue **deux** lignes :

      « Consulter un profil ACTIF »     coche pour les huit roles
      « Consulter un profil ARCHIVE »   ESM (entite, besoin fonctionnel),
                                        ADM-E (entite) et SUPER (global)

  Le trombinoscope est l'annuaire ouvert a tous : il porte la **premiere** ligne.
  La consultation d'un profil archive est un acte delibere -- « besoin
  fonctionnel » -- et elle appartient a `T8`, qui traite l'archivage et la
  restauration. La rendre ici obligerait a inventer un listage privilegie que le
  corpus ne decrit pas.

  Le modele declare pourtant **quatre** etats d'appartenance -- `future`,
  `active`, `departed`, `archived` -- et **trois** visibilites -- `draft`,
  `published`, `hidden`. Le §6.1 n'en nomme que deux. C'est la classe de
  `ECART-039` : le critere nomme des exemples, le modele declare la classe.

  **Le filtre porte donc sur DEUX colonnes, et aucune n'est redondante. C'est
  mesure, pas suppose :**

      si l'on ne filtrait que        `_appliquer` de `services.py` pose
      `profile_visibility`          `membership_state` et `departure_date`, ferme
                                    les relations et revoque les sessions -- il ne
                                    TOUCHE PAS `profile_visibility`. Le §22.5
                                    etape 5 « masquage du profil » n'est
                                    implemente NULLE PART : zero occurrence hors
                                    des modeles et des fabriques. Un partant
                                    resterait donc `published`, donc LISTE.

      si l'on ne filtrait que       un nouvel arrivant a une appartenance
      `membership_state`            `active` des sa date d'arrivee, et un profil
                                    `draft` jusqu'a validation de sa fiche
                                    (§10.2). Il serait liste avant d'exister
                                    publiquement.

  Un test fige les quatre exclusions **pour un appelant `SUPER`** : si un lot
  ulterieur veut un listage privilegie, il devra casser ce test, donc le decider.
  C'est le §7.32 -- un test est un meilleur vehicule qu'un commentaire.

L'ORDRE EST TOTAL, ET LA COLLATION EST MESUREE

  Jonathan a arbitre le 25/08/2026 : **nom, puis prenom**. C'est l'ordre d'un
  annuaire, celui ou l'on retrouve quelqu'un dont on connait le nom.

  Aucun document du corpus ne le donnait -- zero occurrence d'« alphabetique »,
  « ordre de tri » ou « trie » a propos du trombinoscope -- et il ne s'agit pas
  d'un gout : **une pagination sans ordre total repete des lignes et en saute
  d'autres.** `last_name` et `first_name` ne sont pas uniques ; le tri porte donc
  aussi sur `entity_membership.id`, cle primaire, ce qui rend l'ordre total.

  **Et le tri est bien FRANCAIS, prouve par une epreuve discriminante** et non par
  la lecture du fichier Compose : `pg_database.datlocprovider` vaut `i` et
  `datlocale` vaut `fr-FR` -- la colonne s'appelle `datlocale` depuis
  PostgreSQL 17, `daticulocale` n'existe plus -- et la base rend
  `cote < cote' < co^te < co^te'`, qui est l'ordre francais. `datcollate` affiche
  `en_US.utf8`, champ libc herite qu'une base ICU conserve sans l'employer : s'y
  fier aurait fait conclure a une collation anglaise.

LES TROIS TAILLES SONT UNE LISTE BLANCHE, ET C'EST UN ARBITRAGE

  Le cahier §18.2 dit « 25 elements par defaut ; options 25, 50 et 100 ;
  maximum 100 ». Deux lectures se defendaient -- la liste des trois est-elle le
  contrat de l'API, ou seulement ce que l'ecran propose ? Jonathan a tranche le
  25/08/2026 : **l'API n'accepte que les trois valeurs.** Une API stricte
  s'assouplit sans rien casser ; l'inverse casse ceux qui s'y etaient fies.

  La liste est donc **fermee ici**, et le refus est un **422 au format du §18.3** :
  `gerer_erreur_validation` traduit toute erreur de validation en `code`,
  `message`, `champ`, `details` et identifiant de correlation. Aucun code de refus
  n'est ecrit dans ce module.

CE QUE `T2` NE FAIT PAS, ET IL FAUT LE DIRE

  Le §10.1 veut un recto « photo et identite » et un verso « informations
  professionnelles principales ». Cette route rend l'**identite** et ce que
  `entity_membership` porte lui-meme ; elle ne joint ni le metier, ni le statut,
  ni le client, ni le DSM, ni les cercles.

  Ce n'est pas un oubli : ce sont exactement les **six axes de filtre** de `T3`,
  dont le critere de sortie est « aucun N+1, compte et non suppose ». Les joindre
  ici ferait le travail de `T3` sans son controle de performance. La photo, elle,
  attend `T5` -- ses variantes -- et `T6` -- son autorisation.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.people.modeles import EtatAppartenance, VisibiliteProfil

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection


#  Cahier §18.2, a la lettre : « options 25, 50 et 100 ; maximum 100 ».
#
#  **LE TYPE EST LA SOURCE, ET LE TUPLE EN EST DERIVE.** La route a besoin d'un
#  type qui fasse produire a FastAPI un 422 nommant les valeurs admises et qui
#  les documente dans OpenAPI ; le service a besoin d'un tuple pour verifier.
#  Ecrire les deux cote a cote donnerait DEUX listes a maintenir, et la premiere
#  sous-etape qui en changerait une oublierait l'autre (§7.27).
#
#  **ET CE TYPE EST UN `IntEnum`, PAS UN `Literal` — LE DEFAUT `T2-3` L'A PROUVE.**
#  Un parametre d'URL arrive TOUJOURS en chaine. Mesure du 25/08/2026 :
#
#      TypeAdapter(Literal[25, 50, 100]).validate_python("25")  ->  REFUSE
#      TypeAdapter(IntEnum(...)).validate_python("25")          ->  25
#
#  Avec un `Literal`, la route refusait donc **les trois tailles valides** des
#  qu'elles etaient ecrites dans l'URL, et n'acceptait plus que le defaut
#  implicite. **Mes huit tests de refus passaient tous** : ils demandaient un
#  refus, et ils l'obtenaient -- pour la mauvaise raison. Seul le TEMOIN, celui
#  qui exige que 25, 50 et 100 SOIENT servies, discrimine les deux situations.
#  C'est la troisieme proposition du §7.0 : un controle dont l'echec produit la
#  meme observation que le succes ne prouve rien.
#
#  La borne de 100 est le `max` du tuple, jamais une troisieme constante.
class TailleDePage(enum.IntEnum):
    """Les trois tailles de page du cahier §18.2, et elles seules."""

    VINGT_CINQ = 25
    CINQUANTE = 50
    CENT = 100


TAILLES_DE_PAGE: Final[tuple[int, ...]] = tuple(membre.value for membre in TailleDePage)
TAILLE_PAR_DEFAUT: Final[TailleDePage] = TailleDePage.VINGT_CINQ
TAILLE_MAXIMALE: Final[int] = max(TAILLES_DE_PAGE)

#  Les DEUX etats qui font qu'un profil est dans l'annuaire. Derives des
#  enumerations, jamais ecrits en litteral -- une liste recopiee vieillit au
#  premier ajout de valeur (§7.27).
ETAT_LISTE: Final[str] = EtatAppartenance.ACTIVE.value
VISIBILITE_LISTEE: Final[str] = VisibiliteProfil.PUBLISHED.value

#  Les colonnes exposees, en une seule source. Le controle de `T2` compare la
#  reponse servie a cette liste : une colonne ajoutee a la requete sans etre
#  ajoutee ici -- ou l'inverse -- fait echouer le test.
COLONNES_EXPOSEES: Final[tuple[str, ...]] = (
    "id",
    "person_id",
    "first_name",
    "last_name",
    "preferred_name",
    "professional_category",
    "arrival_date",
)

#  **UNE SEULE SOURCE POUR LE FILTRE, PARTAGEE PAR LES DEUX REQUETES.** Le
#  comptage et la page doivent porter sur la MEME population : deux clauses
#  recopiees donneraient un total qui ne correspond pas aux lignes rendues, et
#  l'ecart ne se verrait qu'a la derniere page. C'est la lecon de
#  `resoudre_une_entite_active`, poussee d'un cran -- la elles partageaient la
#  valeur, ici elles partagent la clause entiere.
_FILTRE: Final[str] = (
    "FROM entity_membership AS em JOIN person AS p ON p.id = em.person_id "
    "WHERE em.entity_id = :entite "
    "AND em.membership_state = :etat "
    "AND em.profile_visibility = :visibilite"
)


@dataclasses.dataclass(frozen=True, slots=True)
class CollaborateurListe:
    """Une ligne du trombinoscope.

    `preferred_name` est la seule valeur facultative -- mesure sur le schema
    reel : `first_name`, `last_name`, `arrival_date` et `professional_category`
    sont tous `NOT NULL`.
    """

    id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    professional_category: str
    arrival_date: dt.date


@dataclasses.dataclass(frozen=True, slots=True)
class PageDuTrombinoscope:
    """Une page, et le total de la population — pas de la page.

    Le total est necessaire : le §10.1 exige une « vue paginee », et une vue
    paginee doit pouvoir dire combien de pages elle a. Il est compte dans la
    MEME transaction que la page, sans quoi une insertion concurrente rendrait un
    total incoherent avec les lignes servies.
    """

    collaborateurs: list[CollaborateurListe]
    total: int


def _parametres(entite: uuid.UUID) -> dict[str, object]:
    """Les trois valeurs du filtre, en une seule construction."""
    return {"entite": entite, "etat": ETAT_LISTE, "visibilite": VISIBILITE_LISTEE}


def lister_le_trombinoscope(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: int,
    taille: int,
) -> PageDuTrombinoscope:
    """La page demandee du trombinoscope d'une entite, et le total.

    `page` est **1-indexee** : c'est le numero que l'ecran affiche, et une page 0
    n'a pas de sens pour un lecteur. La conversion en decalage est faite ici, une
    seule fois.

    Aucun filtre d'appelant : la matrice §5 donne « Lecture » aux huit roles
    authentifies, sans distinction. Le seul controle est l'existence d'une
    session, et il est porte par `exiger_une_session`.
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    parametres = _parametres(entite)
    total = int(connexion.execute(text(f"SELECT count(*) {_FILTRE}"), parametres).scalar_one())

    lignes = connexion.execute(
        text(
            "SELECT em.id, em.person_id, p.first_name, p.last_name, p.preferred_name, "
            f"em.professional_category, em.arrival_date {_FILTRE} "
            #  L'ordre est TOTAL : `em.id` est cle primaire. Voir l'en-tete.
            "ORDER BY p.last_name, p.first_name, em.id "
            "LIMIT :taille OFFSET :decalage"
        ),
        {**parametres, "taille": taille, "decalage": (page - 1) * taille},
    ).fetchall()

    return PageDuTrombinoscope(
        collaborateurs=[
            CollaborateurListe(
                id=uuid.UUID(str(ligne[0])),
                person_id=uuid.UUID(str(ligne[1])),
                first_name=str(ligne[2]),
                last_name=str(ligne[3]),
                preferred_name=None if ligne[4] is None else str(ligne[4]),
                professional_category=str(ligne[5]),
                arrival_date=ligne[6],
            )
            for ligne in lignes
        ],
        total=total,
    )
