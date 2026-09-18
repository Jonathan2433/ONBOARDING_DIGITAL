"""Le rendu des blocs d'une page de contenu — LOT 6, `T5`, `MVP-L06-US004` (1 sur 3).

CE QUE LE CRITERE DEMANDE, ET CE QU'IL NE PEUT PAS PROUVER SEUL

  « Aucun HTML arbitraire ; les blocs autorises sont valides ; le perimetre suit
  la matrice. »

  **UN CRITERE QUI INTERDIT SE SATISFAIT TOUT SEUL QUAND RIEN N'EST RENDU** --
  §7.39, la lecon de `T5` du LOT 5. Une sous-etape qui poserait le refus sans
  servir un seul bloc pourrait cocher « aucun HTML arbitraire » en toute bonne
  foi et n'aurait rien prouve. Le temoin qui rend le critere non trivial est un
  bloc LEGITIME **rendu**, et c'est pourquoi le rendu et le refus sont la meme
  sous-etape.

QUI LIT, ET POURQUOI L'ANNEXE A §13 NE DOIT PAS ETRE LUE SEULE

  **Le §13 de l'annexe porte une ligne « Consulter » a SIX colonnes** -- DSM,
  ESM, BOOST, OFFICE, ADM-E, SUPER -- et **ni `EMP` ni `NEW`**. La lire seule
  ferait refuser le contenu a l'Employe, c'est-a-dire a l'acteur pour qui ce
  portail existe.

  **Ces tableaux n'ONT PAS ces deux colonnes**, et une absence de colonne n'est
  pas une exclusion : c'est le piege que `T2`, `T3` et `T4` ont tous les trois
  mesure. Le §5 est la matrice generale de CONSULTATION, et il accorde
  « Framework », « Cercles » et « Bureaux » aux HUIT roles authentifies. Le
  contenu d'une page de cercle se consulte comme le cercle.

  Cette route exige donc une session et rien de plus.

CE QUE `T5` VALIDE, ET CE QU'ELLE NE VALIDE PAS -- `DEC-584`

  Le §15.2 dit qu'un bloc porte « des champs structures ; un `payload_json`
  valide par type **lorsque necessaire** ». **Mesure du 15/09/2026 : le corpus
  ne nomme AUCUN de ces champs**, et ne dit pas davantage ce qui limite le
  « texte riche **limite** » -- zero occurrence dans les cinq documents de
  cadrage.

  En inventer un schema par type serait §6.5 -- *une hypothese deguisee en
  decision est pire qu'une case vide* -- et couterait, si le vocabulaire arrete
  par Lea differait, une migration ET un changement de contrat sur onze types.
  **`QO-121` porte donc la question**, et rien n'est bloque en attendant.

  **CE QUI EST VALIDE EST LA SEULE CHOSE QUE LE CORPUS ECRIT, ET IL L'ECRIT
  QUATRE FOIS** : « aucun HTML arbitraire n'est stocke ou execute », « aucun HTML
  arbitraire ni script n'est accepte ». Trois verbes, que le decoupage separe :

    stocke    `T1` -- aucune colonne ne peut porter du HTML libre
    execute   `T5` -- ci-dessous
    accepte   `T6` -- l'ecriture

COMMENT « AUCUN HTML EXECUTE » EST TENU : PAR LA STRUCTURE, PAS PAR UN FILTRE

  **Un filtre textuel serait une heuristique, donc un defaut** (§7.25). « `<` »
  est un caractere legitime dans « a < b », et chercher `<script` laisserait
  passer `<img onerror=…`. Un garde-fou a faux positifs apprend a passer outre,
  et un garde-fou a faux negatifs ment.

  **Ce qui est exact est structurel** : cette API sert des DONNEES. Le contenu
  d'un bloc voyage dans une valeur JSON, et la reponse ne porte **aucun champ
  de nature HTML** -- il n'existe pas de forme de cette reponse ou une chaine
  serait designee comme du balisage a interpreter. Le perdre exigerait de
  changer le type, pas de retirer un appel (§7.35).

  **Et un test le prouve dans les deux sens** : un bloc dont le payload contient
  `<script>` est servi **tel quel, comme une chaine**, et le contrat ne fournit
  aucun chemin qui le rendrait comme du balisage.

  Ce qui EST refuse ici, parce que c'est exact : un `payload_json` qui ne serait
  pas un **objet** JSON. Une donnee de bloc est un objet ; un scalaire ou un
  tableau ne peut pas porter des « champs structures », et le servir ferait
  deviner sa forme au client.

CE QUE CE MODULE NE REND PAS

  **Les pages en BROUILLON et ARCHIVEES ne sont pas rendues**, et la route en
  fait un 404 indistinguable des autres causes. `US006` -- « **previsualiser**
  puis publier » -- est une story a part, celle de `T7`, avec sa propre grille de
  roles : le §13 donne « Publier » et « Archiver » a une portee **Perimetre** la
  ou « Modifier » vaut **Entite**. Elargir cette route confondrait deux droits
  que la matrice separe (§7.41).

  **Aucune ecriture.** `T6` ecrit, `T7` publie, `T10` fait l'ecran.
"""

from __future__ import annotations

import dataclasses
import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.content.modeles import EtatDePage

#  **L'ETAT SERVI EST DERIVE DE L'ENUMERATION, PAS ECRIT EN DUR** (`DEC-544`,
#  meme parti que le filtre `active` des entites) : si le §15.1 recevait un
#  quatrieme etat, cette constante resterait juste ou echouerait bruyamment.
ETAT_RENDU: str = EtatDePage.PUBLISHED.value

_PAGE = text(
    """
    SELECT cp.id, cp.page_type, cp.title, cp.slug, cp.published_at
      FROM content_page AS cp
     WHERE cp.entity_id = :entite
       AND cp.page_type = :type_de_page
       AND cp.slug = :slug
       AND cp.state = :etat
       AND cp.archived_at IS NULL
    """
)

#  **L'ORDRE EST TOTAL, ET LA CLE PRIMAIRE EN EST LE DERNIER TERME.** L'unicite
#  posee par `T1` porte sur `(content_page_id, display_order)` **non archive**,
#  si bien que deux blocs archives peuvent partager un rang : sans `b.id`, leur
#  ordre flotterait d'un appel a l'autre.
#
#  **`b.entity_id = :entite` EST REDONDANT AUJOURD'HUI, ET LE TEMOIN L'A DIT** :
#  le retirer laisse les vingt-deux tests verts. La cause est la cle etrangere
#  COMPOSITE du §25.3, relevee au catalogue --
#  `fk_content_block_content_page FOREIGN KEY (content_page_id, entity_id)
#  REFERENCES content_page(id, entity_id)` -- qui interdit qu'un bloc pointe la
#  page d'une AUTRE entite. `b.content_page_id = :page` suffit donc.
#
#  **Il est conserve**, parce que c'est l'idiome de cloisonnement de tout ce
#  depot et qu'une requete locale qui ne nommerait pas son entite se lirait comme
#  une requete globale. Mais il n'est PAS ce qui protege : ce qui protege est la
#  cle composite, et `make isolation-check` exige deja qu'elle existe. §7.32.
_BLOCS = text(
    """
    SELECT b.id, b.block_type, b.display_order, b.payload_json
      FROM content_block AS b
     WHERE b.content_page_id = :page
       AND b.entity_id = :entite
       AND b.archived_at IS NULL
     ORDER BY b.display_order, b.id
    """
)


@dataclasses.dataclass(frozen=True, slots=True)
class BlocRendu:
    """Un bloc, servi comme DONNEE.

    **`contenu` EST UN DICTIONNAIRE, JAMAIS UNE CHAINE DE BALISAGE.** C'est le
    type qui tient « aucun HTML execute » : il n'existe aucune valeur de cette
    forme ou un champ designerait du balisage a interpreter (§7.35). Ses clefs ne
    sont pas contraintes ici -- le corpus n'en nomme aucune, `QO-121`.
    """

    identifiant: uuid.UUID
    type_de_bloc: str
    ordre: int
    contenu: dict[str, object]


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeContenuRendue:
    """Une page PUBLIEE et ses blocs, dans l'ordre."""

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    publiee_le: str | None
    blocs: tuple[BlocRendu, ...]

    @property
    def nombre_de_blocs(self) -> int:
        return len(self.blocs)


class PayloadNonObjet(ValueError):
    """Un `payload_json` qui n'est pas un objet JSON.

    **REFUSE VISIBLEMENT PLUTOT QUE CORRIGE EN SILENCE** (§7.20). Reparer en
    enveloppant la valeur dans un objet inventerait une clef ; l'ignorer ferait
    disparaitre un bloc d'une page sans que personne le sache. La seule reponse
    honnete est de dire quel bloc, et de laisser l'appelant trancher.
    """

    def __init__(self, bloc: uuid.UUID, obtenu: str) -> None:
        super().__init__(
            f"le bloc {bloc} porte un `payload_json` de type {obtenu} ; "
            "un objet JSON est attendu — le §15.2 parle de « champs structures »"
        )
        self.bloc = bloc
        self.obtenu = obtenu


def lire_la_page_de_contenu(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    type_de_page: str,
    slug: str,
) -> PageDeContenuRendue | None:
    """Une page PUBLIEE et ses blocs, ou `None` si elle n'est pas rendable.

    **`None` COUVRE QUATRE CAUSES A DESSEIN** : le couple type/slug est inconnu,
    la page appartient a une AUTRE entite, elle est en **brouillon**, ou elle est
    archivee. La route en fait un seul 404 : distinguer apprendrait l'existence
    d'un brouillon qu'on n'a pas a voir, ce qui viderait `US006` de son sens.

    **UNE PAGE SANS AUCUN BLOC EST UNE PAGE VALIDE**, et elle rend un tuple vide.
    Rendre `None` confondrait « cette page n'existe pas » et « cette page n'a pas
    encore de contenu », deux etats que l'editeur doit distinguer.
    """
    ligne = connexion.execute(
        _PAGE,
        {"entite": entite, "type_de_page": type_de_page, "slug": slug, "etat": ETAT_RENDU},
    ).one_or_none()
    if ligne is None:
        return None

    blocs: list[BlocRendu] = []
    for b in connexion.execute(_BLOCS, {"page": ligne[0], "entite": entite}):
        charge = b[3]
        if not isinstance(charge, dict):
            raise PayloadNonObjet(b[0], type(charge).__name__)
        blocs.append(
            BlocRendu(
                identifiant=b[0],
                type_de_bloc=str(b[1]),
                ordre=int(b[2]),
                #  **PAS DE `dict(charge)` ICI, ET C'EST MESURE.** J'avais ecrit
                #  une copie « pour ne pas partager la valeur du pilote », avec
                #  un test qui pretendait le prouver. Le temoin dit que ni l'un
                #  ni l'autre ne tient : psycopg construit un objet NEUF par
                #  ligne lue, le retirer laisse les vingt-deux tests verts, et
                #  `mypy --strict` ne l'exige pas davantage. C'etait une defense
                #  contre un etat qu'aucun controle ne peut observer -- §7.32,
                #  et le test qui l'accompagnait etait une fausse preuve.
                contenu=charge,
            )
        )

    publiee = ligne[4]
    return PageDeContenuRendue(
        identifiant=ligne[0],
        type_de_page=str(ligne[1]),
        titre=str(ligne[2]),
        slug=str(ligne[3]),
        #  **NULLABLE AU §15.1, ET LE MODELE NE LIE PAS `state` A `published_at`.**
        #  Une page `published` sans date n'est interdite nulle part -- `T1` l'a
        #  releve. `str(None)` rendrait la chaine « None » (defaut `T10-8`).
        publiee_le=None if publiee is None else publiee.isoformat(),
        blocs=tuple(blocs),
    )
