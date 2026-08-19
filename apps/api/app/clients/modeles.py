"""Clients globaux, activations locales et alias — modele §7.1 a §7.3.

LOT 2, sous-etape `T6`, story `MVP-L02-US003`.

FONDEMENT — modele §7.1 `client`, §7.2 `entity_client`, §7.3 `client_alias`,
arbitrages `DATA-004` « les clients sont globaux et actives par entite » et
`DATA-005` « les alias clients exigent une validation humaine », point 6 de
l'ordre du §28.

QUATRE LECTURES, POSEES PLUTOT QUE SUPPOSEES.

  1. **`canonical_name` EST LA FORME NORMALISEE**, et `display_name` la forme
     presentee -- exactement le couple `email_normalized` / `email` du §6.1. Le
     §7.1 ecrit « nom officiel UNIQUE SELON NORMALISATION », donc la lecon de
     `ECART-029` s'applique : la valeur STOCKEE doit deja etre normalisee, ce qui
     rend un index unique simple suffisant.

  2. **LA NORMALISATION EST VOLONTAIREMENT MINIMALE**, et c'est le §7.3 qui
     l'impose. Elle met en minuscules, retire les espaces de bordure et reduit
     les espaces internes a un seul. Elle ne touche NI aux accents, NI a la
     ponctuation, NI aux formes juridiques.

     **Motif, et il n'est pas esthetique :** retirer les traits d'union
     rapprocherait « Saint-Gobain » et « Saint Gobain » AUTOMATIQUEMENT. Or
     `DATA-005` exige une validation humaine des alias, et le §7.3 conclut
     qu'« aucune proposition de rapprochement n'ecrit directement dans cette
     table sans validation humaine ». **Une normalisation agressive serait
     precisement le rapprochement automatique que le modele interdit** -- elle
     le ferait en amont, sans meme laisser de trace dans `client_alias`.

  3. **LE §7.2 N'ENUMERE AUCUNE COLONNE.** Il donne trois capacites, et
     celles-ci disent ce qu'il faut : « partager le meme client entre plusieurs
     entites » exige un couple `(entity_id, client_id)` ; « ne pas afficher tous
     les clients partout » exige que l'absence de ligne soit signifiante, donc
     que la table soit une activation explicite ; « archiver LOCALEMENT une
     relation sans supprimer le client global » exige un `archived_at` local,
     qu'apporte `ChampsCommuns`.

  4. **`validated_at` ET `validated_by_person_id` SONT `NOT NULL`.** Le §7.3 les
     dit « obligatoire », et sa derniere phrase tranche l'ambiguite : « aucune
     proposition de rapprochement n'ecrit directement dans cette table sans
     validation humaine ». Une proposition en attente ne vit donc PAS ici -- elle
     vivra dans `import_decision`, §19.4, au LOT 9. Rendre ces colonnes nullables
     aurait ouvert la porte a exactement ce que le §7.3 interdit.

CE QUE CETTE SOUS-ETAPE ACQUITTE. `professional_status_assignment.client_id`
avait ete declaree en `T5` **sans cle etrangere**, `client` n'existant pas encore.
La migration `0007` l'ajoute : c'etait une dette explicite, ecrite dans l'en-tete
de `0006`.

UNE ABSENCE ASSUMEE, ET ELLE FAIT L'OBJET D'UNE QUESTION. Le modele ne pose
AUCUNE regle d'unicite sur `client_alias`, et le §25.1 ne la mentionne pas. Un
meme alias pourrait donc designer deux clients canoniques differents, ce qui
rendrait la recherche ambigue au LOT 9. **Mais la portee de l'unicite -- globale,
ou par entite, sachant que `entity_id` est nullable -- est un choix metier que
rien ne tranche.** `QO-117` est ouverte plutot qu'un index invente : `T5` a montre
ce que coute une derivation d'index qui n'etait pas dans le modele.

ET UNE REGLE PLANIFIEE, NON UNE QUESTION. « `mission` exige un client ACTIF POUR
L'ENTITE » (§6.5) porte sur `entity_client`, qui existe desormais. La regle est
inter-tables et reste a appliquer en **`T10`** -- « contraintes de roles et de
perimetres » de la fiche. Ce qui est applique des `T5` est la FORME : `client_id`
obligatoire en mission, nul en intercontrat.
"""

from __future__ import annotations

import datetime as dt
import enum
import re
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    RessourceLocale,
    contrainte_enumeration,
)

ESPACES_MULTIPLES = re.compile(r"\s+")


class StatutClient(enum.StrEnum):
    """§7.1 : « `status` | `active` ou `archived` ».

    Deux valeurs seulement, la ou `entity.status` en a quatre : un client n'a pas
    de cycle de vie de mise en service, il existe ou il est archive.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"


STATUTS_CLIENT: tuple[str, ...] = tuple(membre.value for membre in StatutClient)


def normaliser_nom_client(valeur: str) -> str:
    """Forme normalisee d'un nom de client : minuscules, espaces reduits.

    C'est la SEULE normalisation appliquee, et son etroitesse est imposee par le
    modele lui-meme. Voir la lecture 2 en tete de module : toute normalisation
    plus poussee -- retrait des traits d'union, des accents, des formes juridiques
    -- rapprocherait des clients distincts AUTOMATIQUEMENT, ce que `DATA-005` et
    le §7.3 interdisent. Les rapprochements passent par `client_alias`, avec
    validation humaine.
    """
    return ESPACES_MULTIPLES.sub(" ", valeur.strip()).lower()


class Client(ChampsCommuns, Base):
    """Referentiel GLOBAL des clients — modele §7.1, arbitrage `DATA-004`.

    Global, donc **pas de `entity_id`** : le mixin `RessourceLocale` ne s'applique
    pas. C'est `entity_client` qui porte le rattachement local.
    """

    __tablename__ = "client"

    canonical_name: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        #  « Nom officiel UNIQUE selon normalisation », §7.1. L'index simple
        #  suffit parce que la contrainte suivante interdit d'y ecrire une forme
        #  non normalisee -- c'est la voie retenue en `T3` pour `ECART-029`.
        UniqueConstraint("canonical_name"),
        CheckConstraint(
            "canonical_name = lower(canonical_name)",
            name="canonical_name_en_minuscules",
        ),
        #  Ni espace de bordure, ni espace double. `btrim` et la recherche d'un
        #  double espace sont les deux seules parts verifiables de la
        #  normalisation minimale.
        CheckConstraint(
            "canonical_name = btrim(canonical_name) AND canonical_name NOT LIKE '%  %'",
            name="canonical_name_espaces_reduits",
        ),
        CheckConstraint("canonical_name <> ''", name="canonical_name_non_vide"),
        contrainte_enumeration("status", StatutClient, "status_valide"),
    )


class EntityClient(ChampsCommuns, RessourceLocale, Base):
    """Active un client global dans une entite — modele §7.2.

    Colonnes DERIVEES des trois capacites du §7.2 : voir la lecture 3 en tete de
    module.

    **L'ABSENCE DE LIGNE EST SIGNIFIANTE.** « Ne pas afficher tous les clients
    partout » veut dire qu'un client global n'est visible dans une entite que si
    cette table le declare. Aucune colonne ne dit « visible » : c'est l'existence
    de la ligne qui le dit, et son `archived_at` qui la revoque LOCALEMENT sans
    toucher au client global.
    """

    __tablename__ = "entity_client"

    client_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["client_id"], ["client.id"]),
        #  Une activation par couple. Unicite NON partielle : reactiver un client
        #  archive localement doit reutiliser la meme ligne, pas en creer une
        #  seconde -- sinon l'historique local se dedoublerait et « archiver
        #  localement sans supprimer le global » perdrait son sens.
        UniqueConstraint("entity_id", "client_id"),
    )


class ClientAlias(ChampsCommuns, Base):
    """Alias d'un client, valide par un humain — modele §7.3, arbitrage `DATA-005`.

    `entity_id` est declaree A LA MAIN et NULLABLE : le §7.3 ecrit « nullable si
    alias global ». Le mixin `RessourceLocale` la poserait `NOT NULL`, comme pour
    `allowed_email_domain` en `T2`.

    `validated_at` et `validated_by_person_id` sont `NOT NULL` : voir la lecture 4
    en tete de module. Une proposition en attente ne vit pas ici.
    """

    __tablename__ = "client_alias"

    alias_normalized: Mapped[str] = mapped_column(String(256), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    validated_by_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    validated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["client_id"], ["client.id"]),
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["validated_by_person_id"], ["person.id"]),
        #  Meme normalisation que `client.canonical_name` : un alias se compare a
        #  des noms canoniques, et deux normalisations differentes rendraient la
        #  comparaison fausse.
        CheckConstraint(
            "alias_normalized = lower(alias_normalized)",
            name="alias_normalized_en_minuscules",
        ),
        CheckConstraint(
            "alias_normalized = btrim(alias_normalized) AND alias_normalized NOT LIKE '%  %'",
            name="alias_normalized_espaces_reduits",
        ),
        CheckConstraint("alias_normalized <> ''", name="alias_normalized_non_vide"),
        #  AUCUNE contrainte d'unicite : voir l'absence assumee en tete de module,
        #  et `QO-117`.
        Index("ix_client_alias_alias_normalized", "alias_normalized"),
    )
