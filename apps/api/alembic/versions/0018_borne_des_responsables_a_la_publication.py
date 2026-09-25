"""La borne du §8.4 mord a la PUBLICATION d'une page de bureau — LOT 6, `T7`.

Story `MVP-L06-US006`, decision `DEC-583` : « le declencheur du comptage borne
"un a trois responsables actifs" est pose en `T7`, et non en `T4` ».

CE QUE LE MODELE DEMANDE, ET OU LA REGLE MORD

  §8.4, contraintes de `framework_responsibility_assignment` : « un bureau
  possede entre un et trois responsables actifs **lorsqu'il est publie** ». Et
  `DEC-576` a tranche ce que « publie » veut dire : un bureau est publie quand
  sa `content_page` de type `OFFICE` est a l'etat `published`, la table `office`
  ne portant aucun etat de publication (`ECART-031`).

  La regle est donc INTER-TABLES et elle porte sur un COMPTAGE : aucune
  contrainte de ligne ne l'exprime, d'ou un declencheur -- exactement comme
  `circle_archivage_sans_membres_actifs` de la migration `0008`, qui porte le
  « impossible d'archiver un cercle avec des membres actifs » du §23.2.

POURQUOI `BEFORE UPDATE OF state` ET NON `INSERT OR UPDATE`

  **C'EST L'IDIOME DEJA POSE PAR LE LOT 2, ET IL GARDE LA TRANSITION, PAS L'ETAT
  PERMANENT.** `circle_archivage_sans_membres_actifs` est declare `BEFORE UPDATE
  OF archived_at ON circle` : un `INSERT` de cercle deja archive avec des membres
  ne le declenche pas. Le meme choix est fait ici, et il a deux consequences
  qu'il faut nommer plutot que taire (§7.20) :

    1. **l'API ne peut pas contourner le declencheur** : `T6` cree toute page
       dans l'etat `draft` -- `ETAT_A_LA_CREATION` est derive de l'enumeration,
       et un test l'exige -- donc **toute** publication passe par un `UPDATE` de
       `state`. Il n'existe aucun chemin applicatif qui insere `published` ;
    2. **un `INSERT` direct en SQL le contourne**, comme pour `circle`. C'est le
       residuel, il est identique a celui que le LOT 2 a accepte, et c'est ce qui
       laisse au decor de `T4` ses deux cas non conformes.

  **ET C'EST PRECISEMENT POURQUOI LA LECTURE DE `T4` DOIT RESTER TOLERANTE.** Ce
  declencheur garantit « on ne PUBLIE pas un bureau non conforme ». Il ne
  garantit PAS « un bureau publie est toujours conforme » : les responsables
  peuvent etre clotures ou ajoutes APRES la publication, et rien dans ce lot
  n'ecrit dans `framework_responsibility_assignment` -- l'affectation des
  responsables est le §20 et `ARB-DROIT-002`, reserves a l'ESM et au
  super-administrateur, et aucune route ne la sert.

  Les deux etats que `DEC-583` fait produire au decor de `T4` -- un bureau publie
  a **zero** responsable, un autre a **quatre** -- restent donc ATTEIGNABLES, par
  le chemin que la realite emprunte : publier conforme, puis changer les
  affectations. Le declencheur et la tolerance de la lecture ne se contredisent
  pas, **ils se completent**.

POURQUOI DEUX REQUETES LA OU UNE SUFFIRAIT

  `SELECT count(*) ... FOR SHARE` est REFUSE par PostgreSQL -- « FOR SHARE is not
  allowed with aggregate functions », mesure du 19/08/2026 consignee dans la
  migration `0008`. Le verrou et le comptage sont donc separes : un `PERFORM`
  qui verrouille les lignes concernees, puis un `count(*)` qui les compte. Sans
  le verrou, une transaction concurrente pourrait cloturer le dernier
  responsable entre le comptage et la validation.

Revision ID: 0018
Revises: 0017
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#  Les deux bornes du §8.4, ecrites une fois. Les repeter dans le message et
#  dans le test ferait deux sources pour une meme grandeur (§7.0, sixieme
#  proposition) : le message les INTERPOLE.
BORNE_BASSE = 1
BORNE_HAUTE = 3

NOM = "content_page_bureau_publie_borne_les_responsables"


def upgrade() -> None:
    #  **`noqa: S608` JUSTIFIE, ET LE MOTIF DE L'INTERPOLATION EST EXACT.** Rien
    #  d'externe n'entre dans cette chaine : `NOM`, `BORNE_BASSE` et `BORNE_HAUTE`
    #  sont trois constantes de ce module, et une migration est figee des qu'elle
    #  est appliquee. Ce que l'interpolation empeche est plus utile qu'elle ne
    #  coute : le MESSAGE et la COMPARAISON portent les memes deux nombres. Les
    #  ecrire deux fois ferait deux sources pour une seule grandeur, et le jour ou
    #  l'une changerait, le message MENTIRAIT sur la borne qu'il vient
    #  d'appliquer -- §7.0, sixieme proposition.
    op.execute(f"""
        CREATE FUNCTION fn_{NOM}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            actifs integer;
        BEGIN
            -- La borne ne mord QUE sur la transition vers `published` d'une page
            -- de bureau non archivee. Une page archivee ne publie pas le bureau
            -- (`DEC-576`), et un autre `page_type` ne le publie pas non plus.
            IF NEW.page_type = 'OFFICE'
               AND NEW.state = 'published'
               AND NEW.archived_at IS NULL
               AND (OLD.state IS DISTINCT FROM 'published' OR OLD.archived_at IS NOT NULL)
            THEN
                -- `PERFORM ... FOR SHARE` puis `count(*)` : PostgreSQL refuse
                -- `FOR SHARE` avec une fonction d'agregation. Voir l'en-tete.
                PERFORM 1
                FROM framework_responsibility_assignment
                WHERE office_id = NEW.office_id
                  AND responsibility_type = 'OFFICE_MANAGER'
                  AND archived_at IS NULL
                  AND period @> now()
                FOR SHARE;

                -- `period @> now()` et JAMAIS `ends_at IS NULL` : une affectation
                -- FUTURE a elle aussi un `ends_at` nul, et la compter comme
                -- active publierait un bureau que personne ne dirige encore.
                -- C'est `ECART-056`, et le temoin ou seul l'instant avance est
                -- celui qui a le plus servi au LOT 5.
                SELECT count(*) INTO actifs
                FROM framework_responsibility_assignment
                WHERE office_id = NEW.office_id
                  AND responsibility_type = 'OFFICE_MANAGER'
                  AND archived_at IS NULL
                  AND period @> now();

                IF actifs < {BORNE_BASSE} OR actifs > {BORNE_HAUTE} THEN
                    RAISE EXCEPTION
                        'content_page : un bureau publie compte entre {BORNE_BASSE} et '
                        '{BORNE_HAUTE} responsables actifs (bureau %, responsables actifs %)',
                        NEW.office_id, actifs
                        USING ERRCODE = 'check_violation',
                              CONSTRAINT = '{NOM}';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)  # noqa: S608
    #  `BEFORE UPDATE OF state` : le declencheur ne s'arme que lorsque `state`
    #  figure dans les colonnes de l'`UPDATE`. Une ecriture de contenu (`T6`),
    #  qui ne touche que `title`, `updated_at` et `version`, ne l'atteint jamais.
    op.execute(f"""
        CREATE TRIGGER {NOM}
        BEFORE UPDATE OF state ON content_page
        FOR EACH ROW EXECUTE FUNCTION fn_{NOM}();
    """)


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {NOM} ON content_page")
    op.execute(f"DROP FUNCTION IF EXISTS fn_{NOM}()")
