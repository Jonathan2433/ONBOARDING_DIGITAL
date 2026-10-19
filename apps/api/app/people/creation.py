"""Creer manuellement un collaborateur — matrice §6.1, cahier §10.2. LOT 9 `T2`.

**LA PREMIERE ECRITURE DU PROJET QUI CREE UNE PERSONNE.** Mesure avant d'ecrire
une ligne : `grep -rn "INSERT INTO person"` hors tests et hors
`app/shared/fabriques.py` (le generateur de donnees fictives, LOT 2 `T12`) ne
rend **aucune** occurrence. Toutes les routes existantes modifient, archivent
ou restaurent une personne/appartenance deja presente ; aucune n'en cree.

CE QUE CETTE SOUS-ETAPE CREE, DANS L'ORDRE, ET POURQUOI CET ORDRE

  Le cahier §10.2 nomme six « donnees organisationnelles » preremplies et
  verrouillees pour un nouvel arrivant : date d'arrivee, metier, statut, DSM,
  client, cercle principal. Les creer suppose six ecritures, dans un ordre que
  les declencheurs CONTRAIGNENT (`app/shared/fabriques.py`, meme discipline) :

    1. `person`                       — l'identite globale ;
    2. `entity_membership`            — l'appartenance, `membership_state`
                                         calcule depuis `arrival_date` ;
    3. `membership_job_assignment`    — le metier ;
    4. `circle_membership`            — le cercle principal ;
    5. `professional_status_assignment` — statut et client, une seule ligne ;
    6. `dsm_assignment`, SI DEMANDE   — le declencheur `dsm_responsabilite_
                                         active` exige que le DSM designe porte
                                         deja une responsabilite DSM active.

CE QUE CETTE SOUS-ETAPE NE CREE PAS, ET CE N'EST PAS UN OUBLI

  **`professional_category` vaut TOUJOURS `consultant`.** La categorie `dg`
  exige, par le declencheur `dg_implique_dsm_local`, qu'une responsabilite DSM
  existe DEJA pour la personne au moment ou `entity_membership.
  professional_category` devient `dg` — et le service qui satisfait cet
  invariant, `app.organization.services.attribuer_la_categorie_dg`, n'est
  expose par AUCUNE route a ce jour. L'exposer ici melangerait deux
  mecanismes distincts (creer une appartenance ; promouvoir une categorie) et
  anticiperait une route que personne n'a demandee. `professional_category`
  n'est donc PAS un champ de la demande : la rendre acceptable pour `dg` sans
  l'action qui satisfait son invariant produirait un refus de la base que rien
  n'expliquerait a l'appelant.

  **`profile_visibility` vaut toujours `draft`.** Aucune source ne nomme ce
  champ parmi les six « preremplis » ; c'est l'etat initial de toute fiche
  encore a completer, meme discipline que `T8` du LOT 3 pour un nouvel
  arrivant par magic link.

  **`account_state` vaut toujours `active`.** Un collaborateur cree par le
  back-office recoit un acces immediat ; `pending` n'a ni route ni ecran qui le
  consomme ailleurs dans ce depot.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status as statut_http
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.organization.modeles import TypeAppartenanceCercle
from app.people.ecriture import traduire_un_refus_de_la_base
from app.people.modeles import (
    CategorieProfessionnelle,
    EtatAppartenance,
    EtatCompte,
    SituationProfessionnelle,
    VisibiliteProfil,
    normaliser_email,
)
from app.shared.depot import DepotLocal
from app.shared.errors import ErreurApplicative

CODE_CLIENT_INCOHERENT: Final = "valeur_refusee"
MESSAGE_CLIENT_INCOHERENT: Final = (
    "Un statut `mission` exige un client, un statut `intercontract` n'en accepte aucun."
)

#  **LE MEME GABARIT QUE PARTOUT AILLEURS DEPUIS `T9` DU LOT 4**
#  (`CODE_ROLE_REFUSE` de `app/permissions/dependances.py`) : un role absent et
#  une proposition hors perimetre rendent le MEME refus, pour que le motif
#  exact ne sorte jamais (§2.5 du cahier, « refus par defaut »).
CODE_ACCES_REFUSE: Final = "acces_refuse"
MESSAGE_ACCES_REFUSE: Final = (
    "Cet acces a ete refuse. Verifiez le perimetre de creation demande et vos "
    "responsabilites actives."
)


@dataclasses.dataclass(frozen=True, slots=True)
class DemandeDAppartenance:
    """Les SIX champs organisationnels du §10.2, pour une appartenance a poser.

    Partagee entre `creer_un_collaborateur` (`T2`, une personne neuve) et
    `app.people.transfert.changer_d_entite` (`T3`, une personne EXISTANTE) :
    les deux posent la MEME appartenance, seule la provenance de `person_id`
    differe. Extraire ce sous-ensemble evite d'exiger email/nom/prenom d'un
    transfert, qui n'en a rien a faire.

    `client` est le seul champ parmi les six dont l'absence est legitime
    (`intercontract`), meme regle que `DemandeDeModification`. `dsm` est
    absent par defaut : tous les consultants n'en ont pas un
    (`app/shared/fabriques.py` n'en donne qu'a un sur trois).

    `job_catalog_id` ET `circle_id` sont devenus NULLABLES en `T9` (LOT 9) :
    l'import CSV peut legitimement produire une appartenance SANS metier (un
    profil `future`, pas encore actif — `membership_job_assignment.
    job_catalog_id` reste NOT NULL en base, donc la ligne n'est simplement PAS
    posee) et SANS cercle principal (une personne portant la responsabilite
    DSM, schema-csv-collaborateurs.md §5.5 : « un DSM peut ne pas avoir de
    cercle principal »). Le formulaire de `T2` continue d'exiger les deux a
    son propre niveau (son schema Pydantic les declare obligatoires) : cette
    largeur ne change rien a son comportement, elle sert UNIQUEMENT le second
    appelant.
    """

    arrival_date: dt.date
    job_catalog_id: uuid.UUID | None
    status: SituationProfessionnelle
    client_id: uuid.UUID | None
    dsm_person_id: uuid.UUID | None
    circle_id: uuid.UUID | None


@dataclasses.dataclass(frozen=True, slots=True)
class DemandeDeCollaborateur:
    """Une personne neuve et son appartenance — cahier §10.2. `T2`."""

    email: str
    first_name: str
    last_name: str
    preferred_name: str | None
    appartenance: DemandeDAppartenance


@dataclasses.dataclass(frozen=True, slots=True)
class CollaborateurCree:
    """L'identifiant d'appartenance nouvellement cree, et sa version initiale."""

    appartenance: uuid.UUID
    version: int


def valider_la_biconditionnelle_statut_client(demande: DemandeDAppartenance) -> None:
    """Refuser une demande incoherente, SANS connexion, avant tout ecrit.

    Pure et sans acces base : appelable AVANT de creer quoi que ce soit — en
    tete de `creer_un_collaborateur` (avant la personne) et en tete de
    `creer_l_appartenance` (avant l'appartenance), pour que ni l'un ni
    l'autre appelant ne laisse une ligne orpheline sur une demande refusee.
    """
    if (demande.status == SituationProfessionnelle.MISSION) != (demande.client_id is not None):
        raise ErreurApplicative(
            code=CODE_CLIENT_INCOHERENT,
            message=MESSAGE_CLIENT_INCOHERENT,
            statut=statut_http.HTTP_422_UNPROCESSABLE_CONTENT,
        )


def creer_l_appartenance(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    person_id: uuid.UUID,
    demande: DemandeDAppartenance,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> CollaborateurCree:
    """Poser l'appartenance et ses cinq relations, pour une personne EXISTANTE.

    Appelee par `creer_un_collaborateur` (`T2`) et par
    `app.people.transfert.changer_d_entite` (`T3`) — c'est la MEME ecriture
    dans les deux cas, seule la provenance de `person_id` differe.
    """
    valider_la_biconditionnelle_statut_client(demande)

    try:
        #  §6.2, litteralement : une appartenance dont l'arrivee n'est pas encore
        #  survenue est `future`, jamais `active` — `ETATS_OCCUPANTS` traite les
        #  deux de la meme facon en LECTURE, mais la colonne elle-meme doit
        #  porter la valeur exacte.
        etat_initial = (
            EtatAppartenance.ACTIVE.value
            if demande.arrival_date <= instant.date()
            else EtatAppartenance.FUTURE.value
        )

        appartenance = DepotLocal(connexion, "entity_membership", entite).creer(
            person_id=person_id,
            arrival_date=demande.arrival_date,
            membership_state=etat_initial,
            professional_category=CategorieProfessionnelle.CONSULTANT.value,
            profile_visibility=VisibiliteProfil.DRAFT.value,
            created_by_person_id=acteur,
        )

        debut = dt.datetime(
            demande.arrival_date.year,
            demande.arrival_date.month,
            demande.arrival_date.day,
            tzinfo=dt.UTC,
        )

        if demande.job_catalog_id is not None:
            DepotLocal(connexion, "membership_job_assignment", entite).creer(
                entity_membership_id=appartenance,
                job_catalog_id=demande.job_catalog_id,
                starts_at=debut,
                created_by_person_id=acteur,
            )

        if demande.circle_id is not None:
            DepotLocal(connexion, "circle_membership", entite).creer(
                entity_membership_id=appartenance,
                circle_id=demande.circle_id,
                membership_type=TypeAppartenanceCercle.PRINCIPAL.value,
                starts_at=debut,
                created_by_person_id=acteur,
            )

        DepotLocal(connexion, "professional_status_assignment", entite).creer(
            entity_membership_id=appartenance,
            status=demande.status.value,
            client_id=demande.client_id,
            starts_at=debut,
            created_by_person_id=acteur,
        )

        if demande.dsm_person_id is not None:
            DepotLocal(connexion, "dsm_assignment", entite).creer(
                consultant_membership_id=appartenance,
                dsm_person_id=demande.dsm_person_id,
                starts_at=debut,
                created_by_person_id=acteur,
            )
    except (IntegrityError, DataError) as erreur:
        raise traduire_un_refus_de_la_base(erreur) from erreur

    return CollaborateurCree(appartenance=appartenance, version=1)


def creer_un_collaborateur(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    demande: DemandeDeCollaborateur,
    instant: dt.datetime,
    motif: str | None = None,
) -> CollaborateurCree:
    """Creer la personne, puis son appartenance, dans UNE seule transaction.

    La biconditionnelle est validee ICI, AVANT la personne : sans cela, une
    demande incoherente laisserait une ligne `person` orpheline derriere un
    `422`, puisque `creer_l_appartenance` ne la revalide qu'ensuite.

    `motif` : le motif du §18.1 — obligatoire cote ROUTE quand `SUPER`
    autorise l'appel (`app.audit.motif`, `ECART-064`, LOT 10 `T7`), repris tel
    quel par l'import (`app.imports.execution`), qui appelle ce service aussi.
    """
    valider_la_biconditionnelle_statut_client(demande.appartenance)
    email_normalise = normaliser_email(demande.email)
    try:
        personne = connexion.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "preferred_name, account_state) "
                "VALUES (:email, :normalise, :prenom, :nom, :prefere, :etat) RETURNING id"
            ),
            {
                "email": demande.email,
                "normalise": email_normalise,
                "prenom": demande.first_name,
                "nom": demande.last_name,
                "prefere": demande.preferred_name,
                "etat": EtatCompte.ACTIVE.value,
            },
        ).scalar_one()
    except (IntegrityError, DataError) as erreur:
        raise traduire_un_refus_de_la_base(erreur) from erreur

    cree = creer_l_appartenance(
        connexion,
        entite=entite,
        person_id=personne,
        demande=demande.appartenance,
        acteur=acteur,
        instant=instant,
    )
    #  LOT 10, `T3` : UN SEUL `audit_event` POUR L'ACTION ENTIERE, PAS UN PAR
    #  TABLE ECRITE -- la personne et ses cinq relations (`creer_l_appartenance`)
    #  sont une seule action metier, « creer un collaborateur ». Aucune enum
    #  Python ne nomme cette action (a la difference de l'authentification,
    #  LOT 3) : `action_code` est donc un litteral, §7.27 n'ayant rien a reutiliser.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="collaborateur_cree",
        resource_type="person",
        resource_reference=personne,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation d'un collaborateur dans l'entite {entite}",
        reason=motif,
    )
    return cree
