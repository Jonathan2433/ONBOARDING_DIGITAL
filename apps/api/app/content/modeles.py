"""Les trois tables editoriales du modele §15.

LOT 6, sous-etape `T1`, stories `MVP-L06-US001` a `US007` -- toutes en dependent.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose `content_page`, `content_block` et `internal_link`, avec les
  contraintes que le modele ECRIT et celles que le §25.3 exige de toute table
  locale. Il ne pose **aucun service**, **aucune route**, **aucun rendu** : le
  refus de l'injection est prouve en `T5`, qui SERT des blocs -- un critere qui
  interdit quelque chose se satisfait tout seul quand rien n'est rendu (§7.39).

POURQUOI `content_block` PORTE UN `entity_id` QUE LE §15.2 N'ECRIT PAS

  Le §15.2 enumere ses champs : `content_page_id`, `block_type`,
  `display_order`, des champs structures, un `payload_json`. Aucun `entity_id`.

  **Mais le §25.3 est aussi le modele**, et il prescrit que les tables locales
  exposent un couple unique `(id, entity_id)` « pour empecher les references
  inter-entites accidentelles ». Un bloc appartient a une page, qui appartient a
  une entite : il est local **en substance**. Sans `entity_id`, la cle etrangere
  vers `content_page` serait **simple**, et un bloc pourrait pointer la page
  d'une AUTRE entite.

  C'est mot pour mot le raisonnement que `T1` du LOT 5 a ecrit pour
  `media_variant`, et c'est le §7.24 : deux sections du meme document, chacune
  defendable seule ; les confronter donne la reponse.

CE QUE LE MODELE N'ECRIT PAS, ET QUI RESTE DONC OUVERT

  1. **Les « champs structures » du §15.2 ne sont pas nommes.** Le modele dit
     « des champs structures ; un `payload_json` valide par type lorsque
     necessaire », et n'en nomme aucun. En inventer serait §6.5 : le contenu
     voyage dans `payload_json`, et c'est `T5` qui le valide **par type**.
  2. **La liste des protocoles d'URL autorises n'existe pas dans le corpus.**
     Le §15.3 et le cahier §13 ecrivent tous deux « Les URL sont validees selon
     une liste de protocoles autorises », et **ni l'un ni l'autre ne la donne** --
     zero occurrence mesuree le 13/09/2026. `QO-120` est ouverte, et c'est `T8`
     qui ecrit la validation. Cette table borne la forme, pas le protocole.
  3. **Le §15.1 ne lie PAS `state` a `published_at`.** Une page `published` sans
     date de publication n'est interdite nulle part. C'est `T7` qui instruit la
     publication, et `US006` exige alors que « la version publiee soit
     identifiable ».
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, RessourceLocale, contrainte_enumeration


class TypeDePage(enum.StrEnum):
    """§15.1 : « `HOME`, `FRAMEWORK`, `CIRCLE`, `OFFICE`, `LEGAL`, autre type controle ».

    **« CONTROLE » N'EST PAS « FERME », ET LES DEUX ERREURS SONT SYMETRIQUES.**
    La formule « autre type controle » a la meme forme que le « a prevoir
    **notamment** » du §25.1 et le « par exemple » du §22, dont le LOT 3 a montre
    qu'inventer un vocabulaire et fermer une liste ouverte sont deux fautes
    opposees. Les cinq valeurs nommees sont donc posees, et la contrainte de
    verification se modifie par une migration d'une ligne -- ce qui est
    exactement le motif de `contrainte_enumeration` contre un type `enum` natif.
    """

    HOME = "HOME"
    FRAMEWORK = "FRAMEWORK"
    CIRCLE = "CIRCLE"
    OFFICE = "OFFICE"
    LEGAL = "LEGAL"


TYPES_DE_PAGE: tuple[str, ...] = tuple(membre.value for membre in TypeDePage)


class EtatDePage(enum.StrEnum):
    """§15.1 : « `draft`, `published`, `archived` »."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


ETATS_DE_PAGE: tuple[str, ...] = tuple(membre.value for membre in EtatDePage)


class TypeDeBloc(enum.StrEnum):
    """L'UNION des deux listes du corpus — `DEC-577`, et `QO-119` en tranchera le compte.

    **LE CAHIER §10.7 ET LE MODELE §15.2 DONNENT DEUX LISTES DIFFERENTES.**
    Mesure du 13/09/2026, en les confrontant :

      cinq communs   titre · texte · image · video · liste
      cahier seul    cartes · liens · blocs de presentation
      modele seul    carte de lien · citation · appel a l'action interne

    **L'UNION N'A PAS DE COMPTE UNIQUE**, et il vaut **neuf, dix ou onze** selon
    la facon dont « cartes » et « liens » du cahier s'apparient a « carte de
    lien » du modele -- un seul type, deux, ou trois. **Aucune des trois lectures
    n'est deductible des documents**, et c'est l'objet de `QO-119`.

    **ONZE SONT POSES, DONC LA LECTURE LA PLUS LARGE, ET LE MOTIF EST ASYMETRIQUE.**
    Poser onze puis en fusionner deux est une migration ; poser neuf puis
    distinguer ce que le cahier -- le document PREVALENT -- ecrit en deux puces
    separees exigerait de deviner laquelle. Fusionner maintenant detruirait une
    distinction que la source porte ; la garder ne detruit rien.
    """

    #  Nommes par les DEUX documents.
    TITLE = "TITLE"
    RICH_TEXT = "RICH_TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    LIST = "LIST"
    #  Nommes par le CAHIER §10.7 seul.
    CARD = "CARD"
    LINK = "LINK"
    PRESENTATION = "PRESENTATION"
    #  Nommes par le MODELE §15.2 seul.
    LINK_CARD = "LINK_CARD"
    QUOTE = "QUOTE"
    CALL_TO_ACTION = "CALL_TO_ACTION"


TYPES_DE_BLOC: tuple[str, ...] = tuple(membre.value for membre in TypeDeBloc)


class TypeDeLien(enum.StrEnum):
    """§15.3 : « Liens Hub, Academy, SharePoint ou **autres** ressources internes ».

    Les trois nommes, plus `OTHER` que le mot « autres » rend obligatoire : sans
    lui, la liste serait **fermee** la ou la source ne l'est pas.
    """

    HUB = "HUB"
    ACADEMY = "ACADEMY"
    SHAREPOINT = "SHAREPOINT"
    OTHER = "OTHER"


TYPES_DE_LIEN: tuple[str, ...] = tuple(membre.value for membre in TypeDeLien)


class ContentPage(ChampsCommuns, RessourceLocale, Base):
    """Une page typee — modele §15.1."""

    __tablename__ = "content_page"

    page_type: Mapped[str] = mapped_column(String(32), nullable=False)
    circle_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    office_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §25.3 : COMPOSITES. Une page de cercle ne peut pas pointer le cercle
        #  d'une autre entite, et c'est la cle qui l'empeche -- pas un service.
        ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name="fk_content_page_circle",
        ),
        ForeignKeyConstraint(
            ["office_id", "entity_id"],
            ["office.id", "office.entity_id"],
            name="fk_content_page_office",
        ),
        contrainte_enumeration("page_type", TypeDePage, "page_type_valide"),
        contrainte_enumeration("state", EtatDePage, "state_valide"),
        #  **L'IMPLICATION SEULE, ET C'EST DELIBERE.** Le §15.1 ecrit « requis
        #  pour une page de cercle » et « requis pour une page de bureau ». Il
        #  n'ecrit AUCUNE interdiction -- au contraire du §8.4, qui dit en toutes
        #  lettres que « `BOOSTER` exige `circle_id` et **interdit** `office_id` »,
        #  et dont `T8` du LOT 2 a pose la contrainte exhaustive.
        #
        #  Les deux sections sont du meme document, et leur difference de
        #  redaction est donc lisible : la ou le modele veut une interdiction, il
        #  l'ecrit. « Une permission du modele n'est pas une interdiction » --
        #  §4.14, troisieme idee du socle du LOT 2. Un refus est un echec dur,
        #  une permission se resserre plus tard.
        CheckConstraint(
            "page_type <> 'CIRCLE' OR circle_id IS NOT NULL",
            name="circle_id_requis_pour_une_page_de_cercle",
        ),
        CheckConstraint(
            "page_type <> 'OFFICE' OR office_id IS NOT NULL",
            name="office_id_requis_pour_une_page_de_bureau",
        ),
        #  §15.1 : « `slug` | Unique dans l'entite ET le type ». L'unicite porte
        #  donc sur le TRIPLET, jamais sur le slug seul.
        #
        #  Partielle sur `archived_at IS NULL`, comme les trois unicites de
        #  `job_catalog`, `circle` et `office` : sans cela, une page archivee
        #  reserverait son slug pour toujours.
        Index(
            "uq_content_page_entity_type_slug_non_archive",
            "entity_id",
            "page_type",
            "slug",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : la cible des cles composites de `content_block`.
        UniqueConstraint("id", "entity_id"),
    )


class ContentBlock(ChampsCommuns, RessourceLocale, Base):
    """Un bloc d'une page — modele §15.2.

    `entity_id` n'est pas au §15.2 mais au §25.3 : voir l'en-tete du module.
    """

    __tablename__ = "content_block"

    content_page_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #  §15.2 : « un `payload_json` valide par type lorsque necessaire ». C'est
    #  `T5` qui valide PAR TYPE ; cette colonne borne la forme, pas le contenu.
    #
    #  **AUCUNE COLONNE DE CE MODULE NE PEUT PORTER DU HTML LIBRE**, et c'est la
    #  seule part de « aucun HTML arbitraire » qui soit structurelle : il n'y a
    #  pas de colonne `html`, pas de colonne `body`, rien qu'un document JSON
    #  dont `T5` connaitra la forme attendue pour chaque type.
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  **LA CLE EST COMPOSITE, ET C'EST TOUT L'OBJET DE L'`entity_id`.**
        ForeignKeyConstraint(
            ["content_page_id", "entity_id"],
            ["content_page.id", "content_page.entity_id"],
            name="fk_content_block_content_page",
        ),
        contrainte_enumeration("block_type", TypeDeBloc, "block_type_valide"),
        CheckConstraint("display_order >= 0", name="ordre_positif"),
        #  **UN ORDRE TOTAL, ET IL EST DERIVE D'UNE LECON MESUREE.** Deux blocs
        #  de meme rang sur une meme page rendraient l'affichage non
        #  deterministe : c'est exactement ce que `T2` du LOT 5 a du corriger sur
        #  le trombinoscope, ou une ligne pouvait paraitre deux fois ou jamais
        #  selon le plan choisi. Le §25.1 s'ouvrant par « a prevoir
        #  **notamment** », ajouter une unicite DERIVEE d'une regle ecrite est ce
        #  que `T2` du LOT 3 a fait quatre fois.
        Index(
            "uq_content_block_page_ordre_non_archive",
            "content_page_id",
            "display_order",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites d'un lot ulterieur, s'il en vient.
        UniqueConstraint("id", "entity_id"),
    )


class InternalLink(ChampsCommuns, RessourceLocale, Base):
    """Un lien vers une ressource interne — modele §15.3."""

    __tablename__ = "internal_link"

    label: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    link_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #  §15.3 nomme `active` EN PLUS des champs communs du §3.1, qui portent deja
    #  `archived_at`. Les deux ne disent pas la meme chose : on DESACTIVE un lien
    #  pour le retirer de l'affichage sans perdre sa definition, on l'ARCHIVE
    #  pour le sortir du jeu de donnees courant. Fondre les deux ferait
    #  disparaitre une distinction que la source ecrit.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        contrainte_enumeration("link_type", TypeDeLien, "link_type_valide"),
        CheckConstraint("display_order >= 0", name="ordre_positif"),
        #  **CETTE CONTRAINTE BORNE LA FORME, PAS LE PROTOCOLE**, et la nuance
        #  est le §6.5. Le §15.3 et le cahier §13 ecrivent tous deux « Les URL
        #  sont validees selon une liste de protocoles autorises » et **ne la
        #  donnent nulle part** -- zero occurrence, mesuree le 13/09/2026.
        #  Inventer la liste ici la figerait dans le schema. `QO-120` est
        #  ouverte, et `T8` ecrira la validation quand elle aura sa reponse.
        CheckConstraint("length(btrim(url)) > 0", name="url_non_vide"),
        #  **`T8` A POSE LE PROTOCOLE, ET L'ARGUMENT CI-DESSUS TIENT TOUJOURS.**
        #  Ce qui a change n'est pas le raisonnement -- ne pas inventer une liste
        #  que le corpus ne donne pas -- c'est que `DEC-587` la TRANCHE : `https`
        #  seul, `http` refuse nommement, `QO-120` close. Une fois la liste
        #  decidee, la figer coute une migration d'une ligne, exactement comme
        #  `contrainte_enumeration`, et cela rend « aucune URL `javascript:`
        #  n'existe en base » STRUCTUREL plutot que promis (§7.35) : trois
        #  ecrivains futurs sont deja nommes au corpus -- la reprise du prototype
        #  (`T11`), les modeles generiques du §19, les imports du LOT 9 -- et
        #  aucun n'appelle `app.content.liens`.
        #
        #  **ELLE NE SAIT PAS EXIGER UN HOTE**, et c'est pourquoi le service
        #  valide AUSSI : `https:///chemin` passe ce motif sans designer aucun
        #  serveur. La contrainte est le plancher, `valider_une_url` le refus
        #  exact -- et un test confronte les deux listes (migration `0019`).
        CheckConstraint("url LIKE 'https://%'", name="url_https"),
        CheckConstraint("length(btrim(label)) > 0", name="label_non_vide"),
        #  §25.1 « notamment » : deux liens de meme rang dans une entite
        #  rendraient l'ordre d'affichage non deterministe -- meme motif que
        #  `content_block`.
        Index(
            "uq_internal_link_entity_ordre_non_archive",
            "entity_id",
            "display_order",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites d'un lot ulterieur, s'il en vient.
        UniqueConstraint("id", "entity_id"),
    )
