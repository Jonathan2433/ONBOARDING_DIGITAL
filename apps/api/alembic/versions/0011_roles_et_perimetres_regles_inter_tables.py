"""Roles et perimetres : les regles inter-tables, par declencheurs defensifs.

LOT 2, sous-etape `T10`, story `MVP-L02-US005`.
Revision : 0011
Revision precedente : 0010

FONDEMENT — modele §6.5, §8.2, §8.4, §25.4. Backlog, critere d'acceptation de
`MVP-L02-US005`.

**DEUX DES TROIS CRITERES DE `US005` ETAIENT DEJA ACQUIS**, et le verifier avant
de refaire etait la premiere chose a faire :

  « un seul Booster actif par cercle »        acquis en `T8`, index partiel du
                                             §25.1
  « aucune responsabilite active dans         acquis en `T8`, declencheur
    plusieurs entites »                       `booster_une_seule_entite`
  « **DG implique DSM local** »               objet de cette migration

UN ECART ENTRE LE BACKLOG ET LE MODELE, ET LA LECTURE RETENUE

  Le backlog ecrit « aucune responsabilite METIER active dans plusieurs
  entites » -- sans restriction de type. Le modele §8.4 et le §25.4 ecrivent tous
  deux la regle pour le seul **BOOSTER** : « une personne Booster dans une seule
  entite mais eventuellement plusieurs cercles de cette entite ».

  **Le modele prevaut sur le detail.** La regle de preseance de `docs/README.md`
  §3 pose que « les annexes validees precisent les regles detaillees », et la
  colonne du backlog est titree « criteres d'acceptation **SYNTHETIQUES** ».
  Etendre l'interdiction a `DSM`, `ESM` et `OFFICE_MANAGER` serait inventer une
  regle que le modele n'ecrit pas. Voir `ECART-032`.

« DG IMPLIQUE DSM LOCAL » : UNE IMPLICATION APPLIQUEE, UNE ACTION LAISSEE

  Le modele §8.4 decrit une ACTION : « un DG recoit AUTOMATIQUEMENT une
  responsabilite DSM dans la meme transaction que son attribution de categorie ».
  Le backlog decrit une IMPLICATION : « DG implique DSM local ».

  **L'action n'est pas realisable par un declencheur**, et le motif est concret :
  `framework_responsibility_assignment.assigned_by_person_id` est `NOT NULL`, et
  un declencheur ne sait pas QUI attribue. Inventer un attributeur -- la personne
  elle-meme, par exemple -- fabriquerait une trace d'audit fausse, ce qui est pire
  qu'une trace absente.

  **L'implication, elle, est verifiable.** Le declencheur `dg_implique_dsm_local`
  REFUSE une categorie `dg` sans responsabilite `DSM` active dans la meme entite.
  C'est un « trigger DEFENSIF » au sens exact du §25.4, et il garantit l'invariant
  quelle que soit la facon dont le service le satisfait.

  **La creation automatique reste a faire**, en `T11` ou au LOT 3, et elle
  satisfera cet invariant plutot que de s'y substituer.

« `mission` EXIGE UN CLIENT ACTIF POUR L'ENTITE » (§6.5)

  Notee en `T5`, ou `client` n'existait pas, puis en `T6`, ou `entity_client` est
  arrive. Le declencheur `mission_client_actif_dans_l_entite` l'applique enfin.

  **« ACTIF POUR L'ENTITE » se lit sur `entity_client`, pas sur `client.status`.**
  Le §7.2 permet explicitement « d'archiver LOCALEMENT une relation sans supprimer
  le client global » : un client globalement archive mais localement actif est un
  etat que le modele autorise. Le declencheur verifie donc l'activation LOCALE, et
  **ne verifie pas** le statut global -- l'ajouter serait exiger plus que le §6.5.

  Le pendant « `intercontract` interdit un client actif » est deja acquis : la
  contrainte `client_selon_le_statut` de `T5` impose `client_id IS NULL` pour
  `intercontract`, et une absence de client est a fortiori une absence de client
  actif.

CE QUI N'EST PAS ICI, ET POURQUOI

  « Le Booster d'un cercle secondaire ne modifie pas le cercle principal, le DSM,
  le client ou le statut » (§8.2) est une regle de NON-EFFET. Elle ne s'exprime
  pas par une contrainte -- il n'y a rien a refuser -- et se prouve en montrant
  que RIEN n'a change. Un test s'en charge, comme en `T6` pour les alias.

RETOUR ARRIERE. La descente supprime les declencheurs et leurs fonctions, dans
l'ordre miroir de la montee.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    #  « DG implique DSM local » — l'IMPLICATION, appliquee defensivement.
    #  L'ACTION du §8.4 reste au service : voir l'en-tete du fichier.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE FUNCTION fn_dg_implique_dsm_local() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.professional_category = 'dg' THEN
                PERFORM 1
                FROM framework_responsibility_assignment
                WHERE person_id = NEW.person_id
                  AND responsibility_type = 'DSM'
                  AND entity_id = NEW.entity_id
                  AND ends_at IS NULL
                FOR SHARE;

                IF NOT FOUND THEN
                    RAISE EXCEPTION
                        'entity_membership : une categorie dg exige une responsabilite '
                        'DSM active dans la meme entite (personne %, entite %)',
                        NEW.person_id, NEW.entity_id
                        USING ERRCODE = 'check_violation',
                              CONSTRAINT = 'dg_implique_dsm_local';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER dg_implique_dsm_local
        BEFORE INSERT OR UPDATE OF professional_category, person_id, entity_id
        ON entity_membership
        FOR EACH ROW EXECUTE FUNCTION fn_dg_implique_dsm_local();
    """)

    # ------------------------------------------------------------------
    #  §6.5 : « `mission` exige un client ACTIF POUR L'ENTITE ». Notee en
    #  `T5` puis `T6`, appliquee ici.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE FUNCTION fn_mission_client_actif() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            -- `AND NEW.client_id IS NOT NULL`, et le motif est un defaut mesure.
            --
            -- Sans cette condition, le declencheur se reveillait aussi quand
            -- `client_id` etait NUL sur une mission -- cas que la contrainte
            -- `client_selon_le_statut` de `T5` exprime deja, et bien mieux. Le
            -- declencheur se plaignait alors d'un « client non active dans cette
            -- entite » pour un client qui n'existait pas, ce qui envoie le lecteur
            -- chercher au mauvais endroit.
            --
            -- **Chaque regle doit etre rapportee par la contrainte qui l'exprime.**
            IF NEW.status = 'mission' AND NEW.client_id IS NOT NULL THEN
                PERFORM 1
                FROM entity_client
                WHERE entity_id = NEW.entity_id
                  AND client_id = NEW.client_id
                  AND archived_at IS NULL
                FOR SHARE;

                IF NOT FOUND THEN
                    RAISE EXCEPTION
                        'professional_status_assignment : une mission exige un client '
                        'active dans cette entite (client %, entite %)',
                        NEW.client_id, NEW.entity_id
                        USING ERRCODE = 'check_violation',
                              CONSTRAINT = 'mission_client_actif_dans_l_entite';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER mission_client_actif_dans_l_entite
        BEFORE INSERT OR UPDATE OF status, client_id, entity_id
        ON professional_status_assignment
        FOR EACH ROW EXECUTE FUNCTION fn_mission_client_actif();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS mission_client_actif_dans_l_entite "
        "ON professional_status_assignment"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_mission_client_actif()")
    op.execute("DROP TRIGGER IF EXISTS dg_implique_dsm_local ON entity_membership")
    op.execute("DROP FUNCTION IF EXISTS fn_dg_implique_dsm_local()")
