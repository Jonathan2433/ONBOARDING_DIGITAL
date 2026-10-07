"""L'agrégat de l'accueil d'une entité — LOT 8, `T8`, `MVP-L08-US001` (1/2),
`MVP-L08-US006` (1/2).

CINQ SECTIONS, DANS L'ORDRE DU CAHIER §8.4 — ET AUCUNE REGLE N'Y EST RECOPIEE

  §8.4 : « 1. présentation locale […] ; 2. Framework […] ; 3. personnes
  récemment arrivées ; 4. événements à venir ; 5. cartes vers le Hub, eXalt
  Academy et SharePoint. » Ce module ne fait qu'APPELER les cinq services déjà
  construits par leurs sous-étapes respectives — jamais réécrire leur SQL, leur
  filtre d'état, ou leur garde de rôle :

    1. présentation   `app.content.pages.lire_la_page_de_contenu`      (LOT 6)
    2. Framework      `app.organization.framework.lire_la_page_framework` (LOT 6)
    3. arrivées       `app.onboarding.arrivees_recentes.lister_les_arrivees_recentes` (T7)
    4. événements     `app.events.lecture.lister_les_evenements`        (T2)
    5. liens internes `app.content.liens.lister_les_liens`              (LOT 6)

  Chacun de ces cinq porte DÉJÀ sa propre population et ses propres filtres
  d'état (page publiée, lien actif, affectation active à l'instant, etc.) —
  les réécrire ici serait la classe `ECART-021`/`§7.27` : une seconde source
  qui diverge au premier changement de l'une des cinq sous-étapes sources.

LA MATRICE §5 DONNE « LECTURE » AUX HUIT RÔLES POUR LES SIX RESSOURCES
(ACCUEIL, PRÉSENTATION, FRAMEWORK, ÉVÉNEMENTS, ARRIVÉES RÉCENTES, LIENS)

  Aucune des cinq n'a un régime plus restrictif que les autres — mesuré ligne
  par ligne (§5, lignes 140-151 de la matrice). La garde de la route est donc
  une simple session établie, exactement comme chacun des cinq services
  qu'elle compose ; il n'y a RIEN à réconcilier entre leurs permissions.

LA PRÉSENTATION PEUT ÊTRE ABSENTE, ET CE N'EST PAS UNE ERREUR

  `lire_la_page_de_contenu` rend `None` si aucune page `HOME`/`presentation`
  n'existe encore pour cette entité (brouillon, jamais créée, etc.) — l'accueil
  d'une entité neuve n'a pas encore de texte de présentation, et §6.1 du LOT 6
  dit qu'une page sans contenu est un état valide, pas une absence de page.
  `AccueilDEntite.presentation` est donc `None`-able ; les quatre autres
  sections ne le sont jamais — elles rendent au pire une liste vide.

  `TYPE_DE_PAGE_PRESENTATION`/`SLUG_DE_LA_PRESENTATION` ne sont PAS une
  invention de cette sous-étape : c'est la convention posée par l'écran
  `PageEntite.tsx` (LOT 6, `T10`), qui crée et retrouve TOUJOURS la page de
  présentation d'une entité par le couple `(type_de_page="HOME",
  slug="presentation")` — `cibleCorrespond`/`demandeDeCreation` dans ce
  fichier. Réutiliser ce couple ici, plutôt que d'en inventer un autre, c'est
  la règle §6.5.

AUCUNE PAGINATION CONFIGURABLE : LE CAHIER NE DONNE AUCUN NOMBRE, ET LE
DÉCOUPAGE RÉSERVE LE « CARROUSEL » À `T11`/`T12`

  Ni le cahier, ni la matrice, ni la fiche de lot ne nomment un nombre
  d'éléments à afficher par section sur l'accueil — mesuré, zéro occurrence
  d'un chiffre associé à « arrivées récentes » ou « événements » dans ce
  contexte. Inventer une borne ici serait le §6.5 ; en ouvrir une question
  bloquerait `T8` pour un choix de PRÉSENTATION, que le découpage attribue
  explicitement à `T11` (accueil desktop) et `T12` (carrousels mobiles).

  Ce module appelle donc les deux services paginés (arrivées, événements) avec
  la première page et la taille PAR DÉFAUT du cahier §18.2 (`25`, déjà décidée
  — pas inventée pour l'occasion) ; `total` reste dans la réponse pour qu'un
  écran futur sache s'il y a davantage à montrer ailleurs.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from sqlalchemy.engine import Connection

from app.content.liens import LienInterne, lister_les_liens
from app.content.pages import PageDeContenuRendue, lire_la_page_de_contenu
from app.events.lecture import ClassementEvenement, PageDEvenements, lister_les_evenements
from app.onboarding.arrivees_recentes import PageDesArriveesRecentes, lister_les_arrivees_recentes
from app.organization.framework import PageFramework, lire_la_page_framework
from app.shared.pagination import TAILLE_PAR_DEFAUT

#  Convention posée par `PageEntite.tsx` (LOT 6, `T10`) — voir l'en-tête.
TYPE_DE_PAGE_PRESENTATION: Final[str] = "HOME"
SLUG_DE_LA_PRESENTATION: Final[str] = "presentation"


@dataclasses.dataclass(frozen=True, slots=True)
class AccueilDEntite:
    """Les cinq sections de l'accueil, dans l'ordre du cahier §8.4."""

    presentation: PageDeContenuRendue | None
    framework: PageFramework
    arrivees_recentes: PageDesArriveesRecentes
    evenements_a_venir: PageDEvenements
    liens_internes: tuple[LienInterne, ...]


def lire_l_accueil(
    connexion: Connection, *, entite: uuid.UUID, code_entite: str, instant: dt.datetime
) -> AccueilDEntite:
    """Composer les cinq sections de l'accueil d'une entité, au même instant.

    Le MÊME `instant` alimente Framework, les arrivées récentes et les
    événements à venir : deux appels à `now()` dans un seul agrégat pourraient
    classer différemment deux sections qui partagent pourtant la même notion
    de « maintenant ».
    """
    return AccueilDEntite(
        presentation=lire_la_page_de_contenu(
            connexion,
            entite=entite,
            type_de_page=TYPE_DE_PAGE_PRESENTATION,
            slug=SLUG_DE_LA_PRESENTATION,
        ),
        framework=lire_la_page_framework(
            connexion, entite=entite, code_entite=code_entite, instant=instant
        ),
        arrivees_recentes=lister_les_arrivees_recentes(
            connexion, entite=entite, page=1, taille=int(TAILLE_PAR_DEFAUT), instant=instant
        ),
        evenements_a_venir=lister_les_evenements(
            connexion,
            entite=entite,
            classement=ClassementEvenement.A_VENIR,
            page=1,
            taille=int(TAILLE_PAR_DEFAUT),
            instant=instant,
        ),
        liens_internes=lister_les_liens(connexion, entite=entite, inclure_les_inactifs=False),
    )
