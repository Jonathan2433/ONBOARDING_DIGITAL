"""Les trois tables de media et d'autorisation de photo — LOT 5, `T1`.

MODELE §16.1 `media_asset`, §16.2 `media_variant`, §12.2 `photo_authorization`.

TROIS TABLES SUR QUATRE, ET LA QUATRIEME EST NOMMEE

  Le modele en declare **quatre** : `media_asset`, `media_variant`,
  `media_usage` (§16.3) et `photo_authorization`. `media_usage` n'est PAS creee.

  Elle ne sert qu'a la **mediatheque V1** -- matrice §12.2 : « voir les usages »,
  « detecter les medias inutilises ». La creer maintenant serait une table SANS
  CONSOMMATEUR, ce que `T10` du LOT 1 refuse et que `DEC-537` a reapplique deux
  fois. `DEC-558` l'a arbitre a l'ouverture du lot.

  **Consequence a connaitre :** le §16.3 dit « une purge est interdite tant que
  des usages actifs existent ». Cette regle n'est donc PAS applicable, et la
  purge appartient de toute facon au LOT 12, reservee au super-administrateur.

CE QUE LE §25.4 RANGE HORS DE LA BASE, ET QU'IL NE FAUT PAS Y METTRE

  Le §25.4 enumere les regles « necessitant service ou trigger controle », et
  **« la publication d'une photo uniquement avec autorisation active » en fait
  partie**. Ce n'est donc pas un oubli si aucune contrainte ne la porte : c'est ce
  que le modele prescrit. Elle appartient au service, en `T6`, avec ses tests
  d'integration -- et le §25.4 le dit mot pour mot.

  Trois autres regles du §16.1 sont dans le meme cas, et pour la meme raison
  qu'au LOT 2 : **le modele decrit une ACTION, et seule l'IMPLICATION est
  applicable en base** :

    « aucun `object_key` fourni par le client »   c'est le contrat de la ROUTE
    « seuls les medias `ready` peuvent etre affiches »   c'est la LECTURE
    « verification du contenu reel obligatoire »   c'est le worker qui compare
                                                   `mime_declared` a `mime_detected`

UNE AMBIGUITE MESUREE : « PHOTO 10 Mo » CONTRE « IMAGE 20 Mo »

  Le §16.1 pose quatre bornes : « photo 10 Mo maximum ; image 20 Mo maximum ;
  video 1 Go et 20 minutes maximum ».

  **Or une photo EST une image.** La distinction n'est pas un `media_type` -- il
  n'en existe que trois, `image`, `video`, `document` -- mais un **usage**, et
  c'est `media_usage` qui le porterait avec son `usage_type = 'PROFILE_PHOTO'`.
  Cette table est reportee.

  **La base ne peut donc exprimer que ce qu'elle connait** : les bornes par
  `media_type`, soit 20 Mo pour une image et 1 Go / 20 min pour une video. La
  borne de 10 Mo propre a la photo de profil appartient au service, en `T5`, et
  elle est nommee ici pour qu'on ne la croie pas acquise.

POURQUOI `media_variant` PORTE UN `entity_id` QUE LE §16.2 N'ECRIT PAS

  Le §16.2 n'enumere pas ses champs sous forme de tableau : il dit « chaque
  variante porte : dimensions ; format ; taille ; checksum ; `object_key`
  propre ». Aucun `entity_id`.

  **Mais le §25.3 est aussi le modele**, et il prescrit : « pour empecher les
  references inter-entites accidentelles, les tables **locales** exposent un
  couple unique `(id, entity_id)` ». Une variante appartient a un `media_asset`,
  qui appartient a une entite : elle est donc locale **en substance**.

  Sans `entity_id`, la cle etrangere vers `media_asset` serait **simple**, et une
  variante pourrait pointer l'actif d'une AUTRE entite. C'est exactement ce que le
  §25.3 existe pour empecher, et `make isolation-check` le verifie sur les huit
  cles composites du LOT 2.

  **C'est le §7.24 :** deux sections du meme document, chacune defendable seule.
  Les confronter donne la reponse ; lire la seule §16.2 aurait produit une table
  sans garde-fou d'isolation.

ET POURQUOI `photo_authorization` N'EN PORTE PAS

  Elle lie une personne -- table **globale**, sans `entity_id` -- a un
  `media_asset`. Lui donner un `entity_id` ferait de l'autorisation une donnee
  d'entite, ce que le modele n'ecrit pas et que le sens contredit : c'est la
  personne qui autorise sa photo, et elle n'appartient qu'a une entite a la fois.

  `make isolation-check` la classera **globale**, et sa derivation le confirme :
  elle lit les sections du modele et n'y trouve aucun `entity_id`.

CE QUI N'EST PAS INVENTE, ET LA LIMITE QUE CELA POSE

  **Aucune unicite n'est posee sur `photo_authorization`.** On pourrait croire
  « au plus une autorisation active par personne » evident -- un profil n'a qu'une
  photo -- mais **le modele ne l'ecrit pas**, ni au §12.2, ni au §25.1, ni au
  §25.4. L'inventer serait la regle §6.5 enfreinte, et le §7.32 dit l'inverse :
  n'ecris pas de defense contre un etat que rien n'interdit.

  `T6` devra donc dire ce que le service fait de deux autorisations actives, et si
  le corpus reste muet, ouvrir une question au registre.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, RessourceLocale, contrainte_enumeration

#  **LES NOMS DE CONTRAINTE NE PORTENT PAS LEUR PREFIXE : LA CONVENTION L'AJOUTE.**
#  Ma premiere version ecrivait `name="ck_photo_authorization_retrait_apres_octroi"`,
#  et la convention de nommage du socle a produit
#  `ck_photo_authorization_ck_photo_authorization_retrait_apres_octroi` -- **66
#  caracteres, et PostgreSQL tronque a 63 EN SILENCE**.
#
#  C'est `noms_de_contraintes_trop_longs`, pose en `T1` du LOT 2, qui l'a dit. Un
#  garde-fou ecrit treize mois plus tot et qui attrape la faute d'aujourd'hui :
#  c'est exactement ce que le §7.0 troisieme proposition cherche a obtenir.


class EtatMedia(enum.StrEnum):
    """§16.1 : les SIX etats, et le §24.3 en donne la machine.

    `deleted` est **terminal** dans le diagramme du §24.3 : il n'en sort aucune
    transition, `Deleted --> [*]`. Un declencheur le rend irreversible, exactement
    comme `person.account_state = 'anonymized'` au LOT 2 -- et pour la meme
    raison : ce que la suppression a efface n'est plus la pour etre restaure.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"


ETATS_MEDIA: tuple[str, ...] = tuple(membre.value for membre in EtatMedia)


class TypeMedia(enum.StrEnum):
    """§16.1 : « `image`, `video`, `document` si autorise ulterieurement ».

    Les trois sont declarees, et `document` porte sa reserve dans le modele
    lui-meme. La contrainte les admet toutes les trois : restreindre a deux serait
    exiger plus que le modele, ce que le §7.20 nomme un defaut.
    """

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


TYPES_MEDIA: tuple[str, ...] = tuple(membre.value for membre in TypeMedia)


class TypeVarianteMedia(enum.StrEnum):
    """§16.2 : les CINQ versions generees, dans l'ordre du document.

    « miniature trombinoscope ; carte ; pleine largeur ; apercu video ; format
    optimise ». Les noms suivent le document, traduits sans reformulation.
    """

    MINIATURE_TROMBINOSCOPE = "thumbnail"
    CARTE = "card"
    PLEINE_LARGEUR = "full_width"
    APERCU_VIDEO = "video_preview"
    FORMAT_OPTIMISE = "optimized"


TYPES_VARIANTE: tuple[str, ...] = tuple(membre.value for membre in TypeVarianteMedia)

#  §16.2 : « format ». Le modele ne dit PAS lesquels -- mesure le 24/08/2026 :
#  **zero occurrence** de `webp`, `avif`, `jpeg` ou `png` dans les cinq documents
#  de cadrage. La colonne est donc une chaine bornee, sans liste blanche : une
#  enumeration inventee ici bloquerait `T5`, qui doit encore decider et MESURER.
#  Le §8.2 de la fiche du lot nomme ce point comme non tranche.
FORMATS_VARIANTE: tuple[str, ...] = ()


class SourceAutorisationPhoto(enum.StrEnum):
    """§12.2 : « `self_service`, `admin_support`, `migration` », a la lettre."""

    SELF_SERVICE = "self_service"
    ADMIN_SUPPORT = "admin_support"
    MIGRATION = "migration"


SOURCES_AUTORISATION_PHOTO: tuple[str, ...] = tuple(
    membre.value for membre in SourceAutorisationPhoto
)

#  §16.1, bornes exprimables en base. La borne « photo 10 Mo » n'y est PAS : voir
#  l'en-tete du module -- une photo est un USAGE, pas un `media_type`.
TAILLE_MAXIMALE_IMAGE_OCTETS = 20 * 1024 * 1024
TAILLE_MAXIMALE_VIDEO_OCTETS = 1024 * 1024 * 1024
DUREE_MAXIMALE_VIDEO_SECONDES = 20 * 60


class MediaAsset(ChampsCommuns, RessourceLocale, Base):
    """Un media televerse — modele §16.1.

    `entity_id` vient de `RessourceLocale` : le §16.1 l'ecrit « entite
    proprietaire », donc obligatoire.
    """

    __tablename__ = "media_asset"

    uploaded_by_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    state: Mapped[str] = mapped_column(String(32), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)

    #  §16.1 : « valeur d'affichage nettoyee ». Le nettoyage est un geste de
    #  service ; la base ne borne que la longueur.
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)

    #  §16.1 : « nom genere cote serveur », et la premiere contrainte du §16.1 dit
    #  « aucun `object_key` fourni par le client ». C'est le contrat de la ROUTE,
    #  non une regle de ligne : la base ne peut pas savoir qui a propose la valeur.
    object_key: Mapped[str] = mapped_column(Text, nullable=False)

    mime_declared: Mapped[str] = mapped_column(String(255), nullable=False)
    #  Nullable : le MIME REEL n'est connu qu'apres l'analyse du worker, donc pas
    #  a l'insertion en `pending`. Les confondre rendrait la table ininsertable.
    mime_detected: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #  `BigInteger` : 1 Go depasse la borne d'un `integer` signe a 2,1 Go de peu,
    #  mais le §16.1 autorise la video a 1 Go et rien n'interdit d'elever la borne
    #  plus tard. Un `integer` serait un plafond cache.
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    #  SHA-256 en hexadecimal : 64 caracteres exactement. Le §25.1 l'indexe avec
    #  `entity_id`.
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    #  §16.1 : « images et videos ». Nullable, un document n'en a pas.
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #  §16.1 : « videos ».
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #  §16.1 : « nullable » pour les deux, ecrit explicitement.
    rejection_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ready_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["uploaded_by_person_id"], ["person.id"]),
        contrainte_enumeration("state", EtatMedia, "media_asset_state_valide"),
        contrainte_enumeration("media_type", TypeMedia, "media_asset_media_type_valide"),
        #  §16.1, bornes par `media_type`. Ecrites en une seule contrainte plutot
        #  qu'en trois : une taille valide doit l'etre POUR SON TYPE, et trois
        #  contraintes independantes laisseraient passer une video de 20 Mo
        #  declaree `image`... ce qui est d'ailleurs licite. La forme disjonctive
        #  dit exactement la regle du document, sans l'elargir.
        CheckConstraint(
            "size_bytes > 0 AND ("
            f"  (media_type = 'image' AND size_bytes <= {TAILLE_MAXIMALE_IMAGE_OCTETS})"
            f"  OR (media_type = 'video' AND size_bytes <= {TAILLE_MAXIMALE_VIDEO_OCTETS})"
            "  OR media_type = 'document'"
            ")",
            name="taille_selon_le_type",
        ),
        #  §16.1 : « video 1 Go et 20 minutes maximum ». La duree ne concerne que
        #  la video, et elle est nullable ailleurs.
        CheckConstraint(
            "duration_seconds IS NULL OR ("
            f"  duration_seconds > 0 AND duration_seconds <= {DUREE_MAXIMALE_VIDEO_SECONDES}"
            ")",
            name="duree_bornee",
        ),
        #  §16.1 : `rejection_code` « nullable ». Sa correlation avec l'etat
        #  `rejected` n'est PAS ecrite, et l'inventer serait le §6.5 -- mais
        #  l'IMPLICATION inverse l'est, par le diagramme du §24.3 : seul
        #  `Processing --> Rejected` mene a cet etat, donc un code de rejet sur un
        #  media `ready` n'a aucun sens. C'est cette implication qui est posee.
        CheckConstraint(
            "rejection_code IS NULL OR state IN ('rejected', 'deleted')",
            name="rejet_seulement_si_rejete",
        ),
        #  §24.3 : `ready_at` ne peut precede aucun etat qui n'a pas atteint
        #  `Ready`. Le diagramme fait passer par `Ready` avant `Archived`, donc
        #  les deux le portent.
        CheckConstraint(
            "ready_at IS NULL OR state IN ('ready', 'archived', 'deleted')",
            name="ready_at_selon_l_etat",
        ),
        #  §25.1, LITTERALEMENT : `media_asset(entity_id, checksum_sha256) INDEX`.
        #  **INDEX, ET NON UNIQUE.** Le document ecrit `INDEX` la ou il ecrit
        #  `UNIQUE` treize fois ailleurs dans la meme liste : la distinction est
        #  deliberee. Deux entites peuvent televerser le meme fichier, et meme une
        #  seule entite peut le faire deux fois -- pour deux usages differents.
        Index("ix_media_asset_entity_id_checksum", "entity_id", "checksum_sha256"),
        #  §25.3 : cible des cles composites de `media_variant`.
        UniqueConstraint("id", "entity_id"),
    )


class MediaVariant(ChampsCommuns, RessourceLocale, Base):
    """Une version generee d'un media — modele §16.2.

    `entity_id` n'est pas au §16.2 mais au §25.3 : voir l'en-tete du module.
    """

    __tablename__ = "media_variant"

    media_asset_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False)

    #  §16.2 : « dimensions ; format ; taille ; checksum ; `object_key` propre ».
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    variant_format: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  **LA CLE EST COMPOSITE, ET C'EST TOUT L'OBJET DE L'`entity_id`.** Une
        #  variante ne peut pas pointer l'actif d'une autre entite : §25.3, et
        #  `make isolation-check` l'exige de toute reference locale.
        ForeignKeyConstraint(
            ["media_asset_id", "entity_id"],
            ["media_asset.id", "media_asset.entity_id"],
            name="fk_media_variant_media_asset",
        ),
        contrainte_enumeration(
            "variant_type", TypeVarianteMedia, "media_variant_variant_type_valide"
        ),
        CheckConstraint("width > 0 AND height > 0", name="dimensions_positives"),
        CheckConstraint("size_bytes > 0", name="taille_positive"),
        #  **UNE SEULE VARIANTE PAR TYPE ET PAR ACTIF, ET C'EST DERIVE.** Le §16.2
        #  intitule sa liste « Versions generees » et en donne CINQ, nommees. Deux
        #  miniatures du meme actif seraient deux reponses a une meme question, et
        #  la lecture n'aurait aucun moyen de choisir.
        #
        #  Le §25.1 s'ouvre par « a prevoir **notamment** » : ajouter une unicite
        #  derivee d'une regle ecrite est ce que `T2` du LOT 3 a fait quatre fois.
        #  `archived_at IS NULL` suit le motif des trois unicites de `job_catalog`,
        #  `circle` et `office`.
        Index(
            "uq_media_variant_asset_type_non_archive",
            "media_asset_id",
            "variant_type",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites d'un lot ulterieur, s'il en vient.
        UniqueConstraint("id", "entity_id"),
    )


class PhotoAuthorization(ChampsCommuns, Base):
    """L'autorisation explicite d'une photo — modele §12.2.

    **TABLE GLOBALE**, sans `entity_id` : voir l'en-tete du module.
    """

    __tablename__ = "photo_authorization"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    media_asset_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    #  §12.2 : « autorisation explicite ». NON NULL, et c'est le sens du mot
    #  « explicite » : une ligne sans instant d'octroi ne serait pas une
    #  autorisation, elle serait une intention.
    granted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #  §12.2 : « retrait eventuel ». Nullable, et c'est ce qui distingue une
    #  autorisation ACTIVE d'une autorisation retiree.
    withdrawn_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False)

    #  §12.2 : « reference minimale, **sans document sensible inutile** ». La base
    #  ne peut pas verifier la sensibilite d'un contenu ; elle borne la longueur,
    #  ce qui decourage d'y coller autre chose qu'une reference. Et `make
    #  secrets-check` verifie qu'aucune colonne ne peut porter un secret en clair.
    evidence_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        #  **CLE SIMPLE, ET NON COMPOSITE.** `photo_authorization` n'a pas
        #  d'`entity_id` -- voir l'en-tete -- donc rien a apparier. C'est aussi ce
        #  qui la rend globale au sens de `make isolation-check`.
        ForeignKeyConstraint(["media_asset_id"], ["media_asset.id"]),
        contrainte_enumeration(
            "source", SourceAutorisationPhoto, "photo_authorization_source_valide"
        ),
        #  Un retrait ne peut pas preceder l'octroi. `>=` et non `>` : un octroi
        #  et un retrait dans la meme transaction portent le meme `now()`.
        CheckConstraint(
            "withdrawn_at IS NULL OR withdrawn_at >= granted_at",
            name="retrait_apres_octroi",
        ),
    )
