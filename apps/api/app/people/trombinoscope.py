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

LA RECHERCHE ET LES FILTRES — `T3`

  **L'AXE « ENTITE » EST LA ROUTE, PAS UN FILTRE.** Le cahier §9.3 etape 3 nomme
  six axes : « entite, metier, cercle, DSM, client ou statut ». Le trombinoscope
  est per-entite -- le §8.1 y fait atterrir depuis la page nationale, et `T2` a
  mis le code dans l'adresse (`DEC-545`). L'axe « entite » **est** ce code : y
  ajouter un parametre `entite=` sur une route deja bornee par `{code}` serait
  redondant au mieux, et une fuite inter-entites au pire, ce que le §25.3 existe
  pour empecher. **Cinq filtres de requete, donc, et le sixieme est le chemin.**

  **CINQ FILTRES, QUATRE TABLES** : `professional_status_assignment` porte
  `status` **et** `client_id`. Le client actif n'est pas une relation separee,
  c'est une colonne du statut -- mesure sur le schema reel.

  **`EXISTS` ET NON `JOIN`, ET CE N'EST PAS UN GOUT.** Une personne peut avoir un
  cercle principal **et plusieurs secondaires** (§8.2). Une jointure la rendrait
  autant de fois qu'elle a de cercles : le `total` serait faux, et la pagination
  repeterait des lignes. `EXISTS` dit exactement ce que le filtre veut dire --
  « au moins une affectation correspond » -- et ne multiplie rien.

  **LA PERIODE EST `period @> :instant`, JAMAIS `ends_at IS NULL`.** Une
  affectation **future** a elle aussi `ends_at` nul : la lecon est ecrite dans
  `app/organization/services.py`, et le §24.12 du cahier l'exige -- « un role
  cloture ne continue pas a accorder des permissions ». L'instant est **injecte**,
  jamais lu de l'horloge dans la requete.

  **LA RECHERCHE PORTE SUR PRENOM ET NOM, NORMALISES DES DEUX COTES.** Arbitrage
  du 26/08/2026 : les accents sont ignores -- « elodie » trouve « Élodie ». Ni
  l'e-mail ni le nom prefere ne sont cherches : le §26.1 ecrit « index de
  recherche sur **prenom et nom** », et les ajouter serait le §6.5.

  La normalisation est **une seule fonction SQL**, `fn_normaliser_pour_recherche`,
  appliquee a la colonne **et** au terme. Deux normalisations -- l'une en Python,
  l'autre en SQL -- divergeraient au premier caractere oublie, et la recherche
  rendrait silencieusement moins de resultats. Voir la migration `0015`.

CE QUE `T3` NE FAIT TOUJOURS PAS

  La ligne rendue ne porte **ni metier, ni statut affiches**. Les cinq relations
  servent a **filtrer**, pas a enrichir la reponse : le §10.1 veut un verso
  « informations professionnelles principales », et c'est `T10` qui l'affichera,
  avec ce que `T4` a defini pour la fiche.

  **LA PHOTO, ELLE, EST LA DEPUIS `T5`** : la ligne porte `a_une_photo`, un
  booleen issu d'un `EXISTS`, et la route en calcule le huitieme champ expose --
  voir `COLONNES_EXPOSEES` plus bas. Ce paragraphe disait « la photo attend `T5`
  et `T6` » jusqu'au 08/09/2026, alors que le commentaire de `COLONNES_EXPOSEES`
  disait deja l'inverse, vingt lignes plus loin. `ECART-054`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import text

from app.media.photo import (
    CONDITIONS_DE_LA_MINIATURE,
    ETAT_AFFICHABLE,
    VARIANTE_DE_LISTE,
)
from app.organization.modeles import TypeAppartenanceCercle
from app.people.modeles import ETAT_LISTE, VISIBILITE_LISTEE
from app.shared.pagination import TAILLES_DE_PAGE

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

    from sqlalchemy.engine import Connection


#  **UNE BORNE SUR LE TERME CHERCHE, ET ELLE N'EST PAS COSMETIQUE.** Sans elle,
#  une requete peut porter un terme de plusieurs mega-octets, que la base
#  normalisera caractere par caractere sur CHAQUE ligne. Le §20.2 borne le debit ;
#  ceci borne le cout d'UNE requete. 128 caracteres depassent largement le plus
#  long nom compose du catalogue -- mesure : `first_name` et `last_name` sont des
#  `text`, sans borne en base, mais aucun nom reel n'approche cette longueur.
LONGUEUR_MAXIMALE_RECHERCHE: Final[int] = 128


#  Les colonnes exposees, en une seule source. Le controle de `T2` compare la
#  reponse servie a cette liste : une colonne ajoutee a la requete sans etre
#  ajoutee ici -- ou l'inverse -- fait echouer le test.
#
#  **`photo` EST LA HUITIEME, ET ELLE N'EST PAS UNE COLONNE SQL.** C'est le
#  chemin que la route calcule a partir d'`a_une_photo`, lequel est un `EXISTS`
#  et non une colonne de `entity_membership`. La liste decrit donc les champs de
#  la REPONSE, ce qu'elle a toujours fait -- `id` vient de `em.id`, `person_id`
#  de `em.person_id` -- et non les colonnes lues telles quelles.
#  **QUATRE CHAMPS DE PLUS DEPUIS `T10`, ET LE §10.1 LES EXIGE.** « Le recto
#  presente principalement la photo et l'identite. Le **verso** presente les
#  informations **professionnelles principales**. » Un ecran ne peut pas inventer
#  ce que l'API ne sert pas : sans eux, le verso de la carte ne porterait que la
#  categorie et la date d'arrivee, ce qui ne repond pas au critere.
#
#  **LE CERCLE VIENT AVEC SON JETON DE COULEUR, ET C'EST UNE EXIGENCE
#  D'ACCESSIBILITE.** Le §10.1 : « la couleur du cercle peut etre utilisee sur les
#  bordures, arriere-plans legers et badges, mais **jamais comme seul moyen de
#  transmettre une information** ». L'ecran a donc besoin du NOM autant que du
#  jeton -- servir le seul jeton rendrait la regle inapplicable.
COLONNES_EXPOSEES: Final[tuple[str, ...]] = (
    "id",
    "person_id",
    "first_name",
    "last_name",
    "preferred_name",
    "professional_category",
    "arrival_date",
    "photo",
    "metier",
    "statut",
    "client",
    "cercle",
)

#  **UNE SEULE SOURCE ET UNE SEULE CLAUSE, PARTAGEES PAR LES DEUX REQUETES.** Le
#  comptage et la page doivent porter sur la MEME population : deux clauses
#  recopiees donneraient un total qui ne correspond pas aux lignes rendues, et
#  l'ecart ne se verrait qu'a la derniere page. C'est la lecon de
#  `resoudre_une_entite_active`, poussee d'un cran -- la elles partageaient la
#  valeur, ici elles partagent la clause entiere.
_SOURCE: Final[str] = "FROM entity_membership AS em JOIN person AS p ON p.id = em.person_id"

#  **UNE TROISIEME REQUETE, ET NON QUATRE JOINTURES DE PLUS SUR LA PAGE.**
#
#  La requete de page porte `ORDER BY p.last_name, p.first_name, em.id` puis
#  `LIMIT` : elle doit donc TRIER toute la population filtree avant de couper. Y
#  ajouter quatre `LEFT JOIN` ferait payer ces jointures sur l'ensemble trie --
#  cinq mille lignes au volume du quatrieme critere de sortie -- pour n'en garder
#  que vingt-cinq.
#
#  Celle-ci ne touche QUE les lignes rendues, bornees a cent par le §18.2. Le
#  nombre de requetes passe de deux a **trois**, et il reste borne : il ne depend
#  ni du nombre de lignes, ni du nombre de cercles. Ce n'est donc pas le N+1 que
#  le cinquieme critere de sortie interdit, et le test qui COMPTE les requetes le
#  fige a trois.
#
#  **LES `LEFT JOIN` SONT SURS, ET C'EST STRUCTUREL** : quatre contraintes
#  d'exclusion rendent metier, statut et cercle principal uniques a un instant
#  donne -- `T4` l'a mesure pour la fiche, et un test exige que ces contraintes
#  existent toujours. Sans elles, une seule ligne pourrait en rendre plusieurs.
_ENRICHISSEMENT: Final[str] = """
SELECT em.id,
       jc.label AS metier,
       ps.status AS statut,
       cl.display_name AS client,
       c.code AS cercle_code, c.name AS cercle_nom, c.color_token AS cercle_jeton
FROM entity_membership AS em
LEFT JOIN membership_job_assignment AS mja
       ON mja.entity_membership_id = em.id AND mja.entity_id = em.entity_id
      AND mja.archived_at IS NULL AND mja.period @> :instant_mja
LEFT JOIN job_catalog AS jc ON jc.id = mja.job_catalog_id
LEFT JOIN professional_status_assignment AS ps
       ON ps.entity_membership_id = em.id AND ps.entity_id = em.entity_id
      AND ps.archived_at IS NULL AND ps.period @> :instant_ps
LEFT JOIN client AS cl ON cl.id = ps.client_id
LEFT JOIN circle_membership AS cm
       ON cm.entity_membership_id = em.id AND cm.entity_id = em.entity_id
      AND cm.membership_type = :type_principal
      AND cm.archived_at IS NULL AND cm.period @> :instant_cm
LEFT JOIN circle AS c ON c.id = cm.circle_id
WHERE em.id = ANY(:identifiants)
"""


@dataclasses.dataclass(frozen=True, slots=True)
class CercleDeLaListe:
    """Le cercle PRINCIPAL d'une ligne, avec son jeton de couleur — §8.1 et §8.2.

    **LE NOM ET LE JETON VOYAGENT ENSEMBLE**, parce que le §10.1 interdit que la
    couleur soit le SEUL moyen de transmettre une information : un ecran qui
    n'aurait que le jeton ne pourrait pas respecter la regle.

    **Le cercle PRINCIPAL seul.** Le §8.2 autorise plusieurs cercles secondaires ;
    les joindre tous multiplierait les lignes de la page et fausserait la
    pagination -- c'est exactement ce que `T3` a mesure pour les filtres, et
    pourquoi ils emploient `EXISTS`.
    """

    code: str
    nom: str
    #  **`color_token` EST NULLABLE, ET LE CATALOGUE LE DIT** --
    #  `information_schema` rend `is_nullable = YES`. Le typer `str` obligeait a
    #  un `str(None)`, qui rend la chaine « None » : un jeton d'apparence
    #  parfaitement plausible, qu'aucun ecran ne reconnait et qu'aucun test ne
    #  voyait, parce que tous mes decors en posaient un. Defaut `T10-8`.
    jeton_de_couleur: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class InfosProfessionnelles:
    """Les quatre champs du verso, tous facultatifs.

    **UNE STRUCTURE PLUTOT QU'UN DICTIONNAIRE DEBALLE**, et `mypy` l'a exige :
    `**dict[str, object]` perd les types a l'appel, si bien qu'un champ mal nomme
    ou mal type ne serait dit par personne.
    """

    metier: str | None = None
    statut: str | None = None
    client: str | None = None
    cercle: CercleDeLaListe | None = None


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
    #  **UN BOOLEEN, PAS UNE CLE, ET C'EST LE POINT.** La liste doit savoir s'il
    #  faut emettre un chemin de photo ; elle n'a aucun besoin de la variante.
    #  Resoudre la variante ligne par ligne serait le N+1 que le critere de `T3`
    #  interdit, et joindre `photo_authorization` multiplierait les lignes -- le
    #  §12.2 n'impose aucune unicite, `T1` l'a mesure. Un `EXISTS` ne fait ni
    #  l'un ni l'autre.
    a_une_photo: bool

    #  **LES QUATRE DU VERSO, AJOUTES PAR `T10`.** Tous facultatifs, et c'est le
    #  schema qui le dit : un nouvel arrivant peut n'avoir ni metier, ni statut,
    #  ni cercle, et `client_id` est nul en `intercontract`. Les rendre
    #  obligatoires obligerait a inventer une valeur.
    metier: str | None = None
    statut: str | None = None
    client: str | None = None
    cercle: CercleDeLaListe | None = None


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


@dataclasses.dataclass(frozen=True, slots=True)
class Filtres:
    """Les cinq axes de filtre du §9.3, plus la recherche. Tous facultatifs.

    Le sixieme axe du cahier -- « entite » -- n'est pas ici : c'est le `{code}` de
    la route. Voir l'en-tete de module.
    """

    recherche: str | None = None
    cercle: uuid.UUID | None = None
    dsm: uuid.UUID | None = None
    metier: uuid.UUID | None = None
    client: uuid.UUID | None = None
    statut: str | None = None

    def actifs(self) -> tuple[str, ...]:
        """Les noms des axes reellement demandes — pour que le controle COMPTE."""
        return tuple(
            champ.name
            for champ in dataclasses.fields(self)
            if getattr(self, champ.name) is not None
        )


#  Un axe -> la clause `EXISTS` qui l'exprime. **DECLAREE, ET CONFRONTEE AU REEL** :
#  un test exige que les cles de cette table soient EXACTEMENT les champs de
#  `Filtres` hors `recherche`. Un axe ajoute a l'un sans l'autre fait echouer
#  (§7.27).
#
#  Chaque clause porte `archived_at IS NULL` et `period @> :instant` : une
#  affectation archivee ou hors periode n'accorde rien (§24.12 du cahier).
_CLAUSES: Final[Mapping[str, str]] = {
    "cercle": (
        "EXISTS (SELECT 1 FROM circle_membership x "
        " WHERE x.entity_membership_id = em.id AND x.archived_at IS NULL "
        "   AND x.period @> :instant AND x.circle_id = :cercle)"
    ),
    "dsm": (
        "EXISTS (SELECT 1 FROM dsm_assignment x "
        " WHERE x.consultant_membership_id = em.id AND x.archived_at IS NULL "
        "   AND x.period @> :instant AND x.dsm_person_id = :dsm)"
    ),
    "metier": (
        "EXISTS (SELECT 1 FROM membership_job_assignment x "
        " WHERE x.entity_membership_id = em.id AND x.archived_at IS NULL "
        "   AND x.period @> :instant AND x.job_catalog_id = :metier)"
    ),
    #  `client` et `statut` interrogent la MEME table : le client actif est une
    #  colonne du statut professionnel, pas une relation separee.
    "client": (
        "EXISTS (SELECT 1 FROM professional_status_assignment x "
        " WHERE x.entity_membership_id = em.id AND x.archived_at IS NULL "
        "   AND x.period @> :instant AND x.client_id = :client)"
    ),
    "statut": (
        "EXISTS (SELECT 1 FROM professional_status_assignment x "
        " WHERE x.entity_membership_id = em.id AND x.archived_at IS NULL "
        "   AND x.period @> :instant AND x.status = :statut)"
    ),
}

#  La recherche : la MEME fonction des deux cotes, sinon ils ne se rencontrent
#  pas. Voir la migration `0015`.
_CLAUSE_RECHERCHE: Final[str] = (
    "fn_normaliser_pour_recherche(p.first_name || ' ' || p.last_name) "
    "LIKE '%' || fn_normaliser_pour_recherche(:recherche) || '%'"
)


def _ou(filtres: Filtres, instant: dt.datetime) -> tuple[str, str, dict[str, object]]:
    """DEUX clauses `WHERE` et leurs parametres, assemblees ensemble.

    **La separation n'est pas cosmetique** : la premiere porte sur
    `entity_membership` seul et entre donc dans la CTE, qui borne le travail a
    l'entite ; la seconde a besoin des colonnes de `person` et ne peut s'appliquer
    qu'apres la jointure. Les melanger obligerait a joindre `person` a l'interieur
    de la CTE, ce qui rendrait la materialisation inutile.

    **AUCUNE VALEUR N'EST INTERPOLEE.** Seule la PRESENCE d'une clause est
    dynamique ; les valeurs passent toutes en parametres lies. C'est ce qui rend
    l'assemblage sur -- et c'est pourquoi les clauses sont des constantes de ce
    module et non des chaines construites a l'appel.
    """
    membres = [
        "em.entity_id = :entite",
        "em.membership_state = :etat",
        "em.profile_visibility = :visibilite",
    ]
    valeurs: dict[str, object] = {
        "entite": None,
        "etat": ETAT_LISTE,
        "visibilite": VISIBILITE_LISTEE,
    }
    personne = ""
    if filtres.recherche is not None:
        personne = _CLAUSE_RECHERCHE
        valeurs["recherche"] = filtres.recherche
    besoin_d_instant = False
    for axe, clause in _CLAUSES.items():
        valeur = getattr(filtres, axe)
        if valeur is not None:
            membres.append(clause)
            valeurs[axe] = valeur
            besoin_d_instant = True
    if besoin_d_instant:
        valeurs["instant"] = instant
    return " AND ".join(membres), personne, valeurs


def lister_le_trombinoscope(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: int,
    taille: int,
    instant: dt.datetime,
    filtres: Filtres | None = None,
) -> PageDuTrombinoscope:
    """La page demandee du trombinoscope d'une entite, et le total.

    `page` est **1-indexee** : c'est le numero que l'ecran affiche, et une page 0
    n'a pas de sens pour un lecteur. La conversion en decalage est faite ici, une
    seule fois.

    Aucun filtre d'appelant : la matrice §5 donne « Lecture » aux huit roles
    authentifies, sans distinction. Le seul controle est l'existence d'une
    session, et il est porte par `exiger_une_session`.

    **DEUX REQUETES, QUOI QU'IL ARRIVE.** Le comptage et la page, et rien de plus :
    aucune boucle n'interroge la base par ligne. C'est ce que le critere de `T3`
    appelle « aucun N+1, **compte** et non suppose », et un test le compte
    reellement, en ecoutant le pilote.

    **`instant` EST INJECTE.** Les cinq filtres portent sur des relations
    historisees, et `now()` dans la requete rendrait le resultat impossible a
    eprouver sur une affectation future ou close.
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    ou_membres, ou_personne, parametres = _ou(filtres or Filtres(), instant)
    parametres["entite"] = entite
    #  **UNE SEULE CLAUSE, ET PAS DE CTE.** J'ai essaye une CTE `MATERIALIZED`
    #  pour borner le travail a l'entite, croyant corriger un plan degrade. Elle
    #  n'a rien corrige -- le plan degrade rejetait toujours 45 879 lignes -- et
    #  le motif etait faux : le planificateur estime `rows=1` parce qu'il ne VOIT
    #  PAS les lignes non validees du banc d'essai, ce qui n'arrive pas en
    #  service. Le changement a ete retire, comme les statistiques etendues avant
    #  lui : garder un correctif dont le motif est faux ET l'effet nul laisse
    #  croire qu'une cause est traitee.
    ou = " AND ".join(clause for clause in (ou_membres, ou_personne) if clause)
    source = f"{_SOURCE} WHERE {ou}"

    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = connexion.execute(
        text(
            "SELECT em.id, em.person_id, p.first_name, p.last_name, p.preferred_name, "
            "em.professional_category, em.arrival_date, "
            #  **L'`EXISTS` EST DANS LA REQUETE DE PAGE, PAS DANS LE COMPTAGE** :
            #  le total ne depend pas de la photo, et l'y ajouter ferait payer a
            #  chaque comptage un travail dont il n'a que faire.
            f"EXISTS (SELECT 1 {CONDITIONS_DE_LA_MINIATURE}) AS a_une_photo "
            f"{source} "
            #  L'ordre est TOTAL : `em.id` est cle primaire. Voir l'en-tete.
            "ORDER BY p.last_name, p.first_name, em.id "
            "LIMIT :taille OFFSET :decalage"
        ),
        {
            **parametres,
            "taille": taille,
            "decalage": (page - 1) * taille,
            #  Les trois parametres que `CONDITIONS_DE_LA_MINIATURE` exige. Un
            #  test verifie que cette liste et celle du module `photo` concordent.
            "etat_media": ETAT_AFFICHABLE,
            "variante": VARIANTE_DE_LISTE,
            "instant": instant,
        },
    ).fetchall()

    #  **AUCUNE TROISIEME REQUETE SUR UNE PAGE VIDE.** Un `= ANY('{}')` ne rendrait
    #  rien et couterait un aller-retour : une entite sans collaborateur listable
    #  est un etat legitime, pas un cas d'erreur.
    identifiants = [ligne[0] for ligne in lignes]
    professionnel = (
        {
            enrichie[0]: enrichie
            for enrichie in connexion.execute(
                text(_ENRICHISSEMENT),
                {
                    "identifiants": identifiants,
                    "type_principal": TypeAppartenanceCercle.PRINCIPAL.value,
                    "instant_mja": instant,
                    "instant_ps": instant,
                    "instant_cm": instant,
                },
            )
        }
        if identifiants
        else {}
    )

    return PageDuTrombinoscope(
        collaborateurs=[_en_ligne(ligne, professionnel.get(ligne[0])) for ligne in lignes],
        total=total,
    )


def _en_ligne(ligne: Any, enrichie: Any | None) -> CollaborateurListe:
    """Une ligne de page, enrichie de son verso.

    **UN SEUL APPEL A `_professionnel` PAR LIGNE.** Ma premiere version l'appelait
    QUATRE fois -- une par champ -- ce qui reconstruisait la structure a chaque
    fois. Sans consequence mesurable a cent lignes, et sans excuse : une fonction
    appelee pour son resultat se lit une fois.
    """
    infos = _professionnel(enrichie)
    return CollaborateurListe(
        id=uuid.UUID(str(ligne[0])),
        person_id=uuid.UUID(str(ligne[1])),
        first_name=str(ligne[2]),
        last_name=str(ligne[3]),
        preferred_name=None if ligne[4] is None else str(ligne[4]),
        professional_category=str(ligne[5]),
        arrival_date=ligne[6],
        a_une_photo=bool(ligne[7]),
        metier=infos.metier,
        statut=infos.statut,
        client=infos.client,
        cercle=infos.cercle,
    )


def _professionnel(enrichie: Any | None) -> InfosProfessionnelles:
    """Les quatre champs du verso, ou des `None` si la ligne n'a rien.

    **UNE LIGNE ABSENTE ET UNE LIGNE SANS AFFECTATION DONNENT LE MEME RESULTAT**,
    et c'est voulu : l'enrichissement porte sur les identifiants de la page, donc
    une absence ne peut venir que d'une course -- la ligne a disparu entre les
    deux requetes -- et un nouvel arrivant sans metier rend exactement les memes
    `None`. Distinguer les deux n'aurait aucun consommateur (§7.32).
    """
    if enrichie is None:
        return InfosProfessionnelles()
    return InfosProfessionnelles(
        metier=None if enrichie[1] is None else str(enrichie[1]),
        statut=None if enrichie[2] is None else str(enrichie[2]),
        client=None if enrichie[3] is None else str(enrichie[3]),
        cercle=None
        if enrichie[4] is None
        else CercleDeLaListe(
            code=str(enrichie[4]),
            nom=str(enrichie[5]),
            #  **LE CINQUIEME GARDE, CELUI QUE J'AVAIS OUBLIE.** Les quatre
            #  au-dessus sont ecrits ; celui-ci est IMBRIQUE dans la construction
            #  du cercle, et c'est ce qui l'a fait manquer.
            jeton_de_couleur=None if enrichie[6] is None else str(enrichie[6]),
        ),
    )
