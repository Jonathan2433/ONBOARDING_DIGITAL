"""`entity_membership` — le profil d'une personne dans une entite.

LOT 2, sous-etape `T4`, story `MVP-L02-US002`.
Revision : 0005
Revision precedente : 0004

FONDEMENT — modele §6.2, principe §2.2, etats §24.1, contraintes §25.1 a §25.3,
point 4 de l'ordre du §28.

**C'EST LA TABLE QUI PORTE LA REGLE CENTRALE DE `US002`** : une seule
appartenance active ou future par personne.

DEUX CONTRAINTES SE PARTAGENT CETTE REGLE, ET ELLES NE DISENT PAS LA MEME CHOSE

  `uq_entity_membership_person_id_occupante`  Index unique PARTIEL du §25.1,
                                              `WHERE membership_state IN
                                              ('future','active')`. Il interdit
                                              DEUX appartenances occupantes
                                              simultanees. Les appartenances
                                              `departed` et `archived` en sont
                                              exclues, ce qui permet l'historique
                                              du §2.2 : « plusieurs appartenances
                                              historiques, une seule active ».

  `ex_entity_membership_...`                  Contrainte d'exclusion du §25.2,
                                              SANS clause `WHERE`. Le §6.2 ecrit
                                              « pas de chevauchement temporel
                                              entre deux appartenances » sans
                                              restriction d'etat : deux
                                              appartenances HISTORIQUES ne
                                              doivent pas se chevaucher non plus,
                                              une personne n'ayant pas ete dans
                                              deux entites en meme temps, meme
                                              dans le passe.

  L'index seul laisserait passer deux appartenances `departed` qui se
  chevauchent ; l'exclusion seule laisserait passer deux appartenances occupantes
  a des periodes disjointes. Les deux sont necessaires, et chacune a son temoin.

UN `daterange` ET NON UN `tstzrange`. Le §6.2 declare `arrival_date` et
`departure_date` en `date`. Le mixin `Periode` du socle produit un `tstzrange` :
il ne s'applique donc PAS ici, et la plage generee est un `daterange`. La
convention semi-ouverte de `T1` est conservee -- `[arrivee, depart)` -- pour que
la fin d'une appartenance et le debut de la suivante puissent porter le meme jour.

CE QU'`autogenerate` A SU ECRIRE, ET CE QU'IL N'A PAS PU

  Il a rendu l'index partiel AVEC sa clause `WHERE`, et la contrainte
  d'exclusion. **Cela rectifie une affirmation trop large de `DEC-500`**, qui
  annoncait qu'il ne les ecrivait pas : il les rend fidelement, des lors qu'elles
  sont declarees dans les metadonnees.

  Il ne peut en revanche pas inventer ce qui n'est pas dans les metadonnees : les
  DECLENCHEURS. Celui ci-dessous est ecrit a la main, comme ceux de `0003` et
  `0004`.

LE DECLENCHEUR PORTE UNE REGLE INTER-TABLES, ET C'EST POURQUOI IL EN FAUT UN

  Le §5.1 pose qu'« une entite archivee ne recoit plus de nouveaux membres ».
  Cette regle interroge une AUTRE table : aucune contrainte de verification ne
  peut le faire, elles ne voient que la ligne en cours. C'est le cas type du
  §25.4, et le meme parti que `DEC-502` -- la couche de services n'arrive qu'en
  `T11`, sept sous-etapes plus loin.

  Il se declenche a l'INSERTION **et** a la mise a jour de `entity_id` :
  deplacer une appartenance existante vers une entite archivee serait aussi la
  faire « recevoir un nouveau membre ».

UNE REGLE DU §6.2 QUI N'EST PAS DE CETTE SOUS-ETAPE : « l'archivage d'une
appartenance revoque les acces et cloture les relations actives ». Les relations
en question -- metier, statut, cercle, DSM, responsabilites -- n'existent pas
encore. Sous-etapes `T5` a `T9`.

UN DEFAUT DE NOMMAGE, TROUVE PAR LA TABLE D'ESSAI DE `T1`

  La contrainte d'exclusion s'appelait d'abord `sans_chevauchement`, sans prefixe.
  La table jetable des tests du socle en portait deja une du meme nom, et la
  seconde creation a echoue : « relation "sans_chevauchement" already exists ».

  **PostgreSQL implemente une exclusion par un INDEX, et les noms d'index sont
  uniques a l'echelle du SCHEMA**, pas par table -- a la difference des noms de
  contraintes. Or la convention de nommage de SQLAlchemy n'a **aucune cle** pour
  les exclusions : le `name=` est pris tel quel.

  Le §25.2 prevoit des exclusions sur SEPT relations. Sans regle, la collision se
  reproduirait six fois, et chaque fois **a la creation de la table**, donc dans
  une migration. La regle `ex_<table>_<objet>` est posee dans
  `app/shared/modele.py`, avec un controle et son temoin.

RETOUR ARRIERE. La descente supprime le declencheur et sa fonction AVANT la
table, pour la meme raison qu'en `0003` et `0004`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "entity_membership",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("arrival_date", sa.Date(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column(
            "period",
            postgresql.DATERANGE(),
            sa.Computed("daterange(arrival_date, departure_date)", persisted=True),
            nullable=False,
        ),
        sa.Column("membership_state", sa.String(length=16), nullable=False),
        sa.Column("professional_category", sa.String(length=32), nullable=False),
        sa.Column("short_bio", sa.Text(), nullable=True),
        sa.Column("fun_fact", sa.Text(), nullable=True),
        sa.Column("profile_visibility", sa.String(length=16), nullable=False),
        sa.Column("profile_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.column("person_id"), "="),
            (sa.column("period"), "&&"),
            using="gist",
            name="ex_entity_membership_sans_chevauchement",
        ),
        sa.CheckConstraint(
            "membership_state <> 'departed' OR departure_date IS NOT NULL",
            name=op.f("ck_entity_membership_depart_date_si_departed"),
        ),
        sa.CheckConstraint(
            "membership_state IN ('future', 'active', 'departed', 'archived')",
            name=op.f("ck_entity_membership_membership_state_valide"),
        ),
        sa.CheckConstraint(
            "professional_category IN ('consultant', 'dg')",
            name=op.f("ck_entity_membership_professional_category_valide"),
        ),
        sa.CheckConstraint(
            "profile_visibility IN ('draft', 'published', 'hidden')",
            name=op.f("ck_entity_membership_profile_visibility_valide"),
        ),
        sa.CheckConstraint(
            "departure_date IS NULL OR departure_date >= arrival_date",
            name=op.f("ck_entity_membership_depart_apres_arrivee"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_entity_membership_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name=op.f("fk_entity_membership_person_id_person")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_membership")),
        sa.UniqueConstraint("id", "entity_id", name="id_entite_unique"),
    )
    op.create_index(
        op.f("ix_entity_membership_entity_id"), "entity_membership", ["entity_id"], unique=False
    )
    op.create_index(
        "ix_entity_membership_entity_id_membership_state",
        "entity_membership",
        ["entity_id", "membership_state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_membership_person_id"), "entity_membership", ["person_id"], unique=False
    )
    op.create_index(
        "uq_entity_membership_person_id_occupante",
        "entity_membership",
        ["person_id"],
        unique=True,
        postgresql_where=sa.text("membership_state IN ('future', 'active')"),
    )
    # ### end Alembic commands ###

    # ------------------------------------------------------------------
    #  §5.1 : « une entite archivee ne recoit plus de nouveaux membres ».
    #  Regle INTER-TABLES : voir l'en-tete du fichier.
    #
    #  `BEFORE INSERT OR UPDATE OF entity_id` : deplacer une appartenance
    #  existante vers une entite archivee serait aussi la faire recevoir un
    #  nouveau membre.
    #
    #  La lecture de `entity` est faite avec `FOR SHARE` : sans elle, une
    #  transaction concurrente pourrait archiver l'entite entre notre
    #  lecture et notre insertion, et la regle serait contournee par une
    #  simple course. `FOR SHARE` bloque cet archivage jusqu'a la fin de
    #  notre transaction.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE FUNCTION fn_entity_membership_entite_non_archivee() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            etat text;
        BEGIN
            SELECT status INTO etat FROM entity WHERE id = NEW.entity_id FOR SHARE;
            IF etat = 'archived' THEN
                RAISE EXCEPTION
                    'entity_membership : une entite archivee ne recoit plus de '
                    'nouveaux membres (entite %)', NEW.entity_id
                    USING ERRCODE = 'check_violation',
                          CONSTRAINT = 'entity_membership_entite_non_archivee';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER entity_membership_entite_non_archivee
        BEFORE INSERT OR UPDATE OF entity_id ON entity_membership
        FOR EACH ROW EXECUTE FUNCTION fn_entity_membership_entite_non_archivee();
    """)


def downgrade() -> None:
    #  Le declencheur et sa fonction d'abord : voir l'en-tete du fichier.
    op.execute("DROP TRIGGER IF EXISTS entity_membership_entite_non_archivee ON entity_membership")
    op.execute("DROP FUNCTION IF EXISTS fn_entity_membership_entite_non_archivee()")

    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "uq_entity_membership_person_id_occupante",
        table_name="entity_membership",
        postgresql_where=sa.text("membership_state IN ('future', 'active')"),
    )
    op.drop_index(op.f("ix_entity_membership_person_id"), table_name="entity_membership")
    op.drop_index("ix_entity_membership_entity_id_membership_state", table_name="entity_membership")
    op.drop_index(op.f("ix_entity_membership_entity_id"), table_name="entity_membership")
    op.drop_table("entity_membership")
    # ### end Alembic commands ###
