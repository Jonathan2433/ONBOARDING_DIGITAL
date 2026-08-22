"""Fabriques de donnees fictives — story `MVP-L02-US007`.

LOT 2, sous-etape `T12`.

CE QUE CE GENERATEUR PRODUIT, ET CE QU'IL NE PRODUIT PAS

  Le critere de `US007` : « le generateur produit jusqu'a **25 entites** et
  **5 000 profils** avec **historiques coherents** et **cas limites** ».

  **Aucune donnee reelle de collaborateur n'est employee** — regle 3 du projet.
  Les noms sont formes par composition d'un petit lexique et d'un numero, et les
  adresses e-mail portent le domaine `exemple.test`, reserve par la RFC 2606
  precisement pour cet usage.

IL EST DETERMINISTE, ET CE N'EST PAS UN LUXE

  `random.Random(graine)` est employe partout, jamais le generateur global. Un
  jeu de donnees non reproductible rend **inexploitable** l'echec qu'il revele :
  on ne peut ni le rejouer, ni le reduire. Deux appels de meme graine produisent
  le meme jeu, et un test l'exige.

IL PASSE PAR LES DEPOTS DE `T11`, ET C'EST UN CHOIX

  `DepotLocal.creer` renseigne `entity_id` lui-meme. Un generateur ecrit en SQL
  direct pourrait fabriquer des relations croisees que la base refuserait, et le
  diagnostic sur 5 000 lignes serait penible. Les depots rendent l'erreur
  impossible plutot qu'improbable.

L'ORDRE EST CONTRAINT PAR QUATRE DECLENCHEURS, ET LES IGNORER FAIT ECHOUER

  - la responsabilite `DSM` **avant** la categorie `dg` (`dg_implique_dsm_local`) --
    c'est `attribuer_la_categorie_dg` qui s'en charge ;
  - l'activation locale du client **avant** une situation `mission`
    (`mission_client_actif_dans_l_entite`) ;
  - l'entite non archivee **avant** une appartenance
    (`entity_membership_entite_non_archivee`) ;
  - la responsabilite `DSM` du DSM **avant** une `dsm_assignment`
    (`dsm_responsabilite_active`).

ET UNE CONTRAINTE QUE SEULE LA MESURE REVELE

  `ex_entity_membership_sans_chevauchement` porte sur `(person_id, period)`
  **sans clause `WHERE`** : deux appartenances d'une meme personne ne peuvent pas
  se chevaucher, **meme dans deux entites differentes, meme archivees**. Une
  mobilite inter-entites doit donc etre **SEQUENTIELLE**, avec une
  `departure_date`. C'est le defaut `T11-6`, et il couterait beaucoup plus cher
  sur 5 000 lignes que sur un test.
"""

from __future__ import annotations

import datetime as dt
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.organization import attribuer_la_categorie_dg
from app.people import CATEGORIES_PROFESSIONNELLES, VISIBILITES_PROFIL
from app.shared.depot import DepotGlobal, DepotLocal

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  RFC 2606 : `.test` est reserve, jamais resoluble. Aucun risque d'envoi reel.
DOMAINE_FICTIF = "exemple.test"

VILLES = (
    "Bordeaux",
    "Lille",
    "Lyon",
    "Nantes",
    "Toulouse",
    "Rennes",
    "Strasbourg",
    "Montpellier",
)
PRENOMS = ("Alix", "Camille", "Dominique", "Eden", "Gabriel", "Louison", "Maxence", "Noa")
NOMS = ("Duval", "Marchand", "Leroy", "Fontaine", "Bertin", "Chevalier", "Rousseau", "Vidal")
CERCLES = (("TECH", "Technologie"), ("DATA", "Donnees"), ("CLOUD", "Cloud"), ("PROD", "Produit"))
METIERS = (("DEV", "Developpeur"), ("DATA", "Ingenieur donnees"), ("PO", "Product owner"))

#  LES VALEURS SONT IMPORTEES, JAMAIS REDECLAREES. Ma premiere version en avait
#  invente trois -- `fonction_support`, `stagiaire`, `alternant` -- alors que le
#  §6.2 n'en declare que DEUX : `consultant` et `dg`. La contrainte de
#  verification les a refusees immediatement, mais une liste recopiee qui se
#  trouverait valide aujourd'hui divergerait demain : c'est `ECART-021`, et la
#  parade est l'import.
#
#  `dg` est ECARTEE de la boucle de masse, et ce n'est pas un oubli : le
#  declencheur `dg_implique_dsm_local` exige une responsabilite `DSM` prealable,
#  donc elle ne s'attribue que par `attribuer_la_categorie_dg`. Elle figure aux
#  cas limites.
CATEGORIES_DE_MASSE = tuple(
    categorie for categorie in CATEGORIES_PROFESSIONNELLES if categorie != "dg"
)


@dataclass
class Volumetrie:
    """Ce que le generateur a produit, par table. Rendu pour etre CONFRONTE."""

    entites: int = 0
    personnes: int = 0
    appartenances: int = 0
    clients: int = 0
    activations: int = 0
    cercles: int = 0
    bureaux: int = 0
    appartenances_cercle: int = 0
    metiers: int = 0
    affectations_metier: int = 0
    situations: int = 0
    responsabilites: int = 0
    affectations_dsm: int = 0
    cas_limites: list[str] = field(default_factory=list)

    def total_lignes(self) -> int:
        return (
            self.entites
            + self.personnes
            + self.appartenances
            + self.clients
            + self.activations
            + self.cercles
            + self.bureaux
            + self.appartenances_cercle
            + self.metiers
            + self.affectations_metier
            + self.situations
            + self.responsabilites
            + self.affectations_dsm
        )


class Compteur:
    """Un numero unique par personne, monotone.

    **CE COMPTEUR CORRIGE UN DEFAUT QUE SEULE L'ECHELLE REVELE, ET IL S'EST
    PRODUIT.** Ma premiere version calculait l'indice du Booster comme
    `800_000 + rang`, une valeur IDENTIQUE d'une entite a l'autre : a trois
    entites les prenoms tires au hasard suffisaient a eviter la collision, mais
    a vingt-cinq entites et quatre cercles -- cent tirages sur soixante-quatre
    combinaisons -- `email_normalized_unique` a ete violee au premier essai a
    l'echelle : « maxence.leroy800251@exemple.test already exists ».

    C'est le §7.16 sous une autre forme : **ce qui n'a jamais tourne a
    l'ECHELLE n'est pas eprouve.** Trente profils passaient ; cinq mille non.
    """

    def __init__(self) -> None:
        self._valeur = 0

    def suivant(self) -> int:
        self._valeur += 1
        return self._valeur


def _personne(
    connexion: Connection, tirage: random.Random, compteur: Compteur
) -> tuple[uuid.UUID, str]:
    numero = compteur.suivant()
    prenom = tirage.choice(PRENOMS)
    nom = tirage.choice(NOMS)
    adresse = f"{prenom.lower()}.{nom.lower()}{numero}@{DOMAINE_FICTIF}"
    identifiant = connexion.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:courriel, :normalise, :prenom, :nom, 'active') RETURNING id"
        ),
        {
            "courriel": adresse,
            "normalise": adresse.lower(),
            "prenom": prenom,
            "nom": nom,
        },
    ).scalar_one()
    return identifiant, adresse


def engendrer(
    connexion: Connection,
    *,
    entites: int = 3,
    profils: int = 30,
    graine: int = 20260820,
) -> Volumetrie:
    """Engendrer un jeu fictif coherent, et rendre sa volumetrie MESUREE.

    `entites` et `profils` sont des plafonds au sens du critere — « jusqu'a » —
    et le nombre de profils est reparti sur les entites.
    """
    tirage = random.Random(graine)  # noqa: S311 — donnees fictives, non cryptographique
    compteur = Compteur()
    mesure = Volumetrie()
    #  `DepotGlobal` sur `person` valide la table a la construction, et REFUSERAIT
    #  une table locale : c'est le garde-fou de `T11`, exerce ici sur le chemin
    #  reel plutot que dans un test seul.
    DepotGlobal(connexion, "person")

    #  1. Les entites, et un catalogue par entite.
    identifiants_d_entites: list[uuid.UUID] = []
    cercles_par_entite: dict[uuid.UUID, list[uuid.UUID]] = {}
    metiers_par_entite: dict[uuid.UUID, list[uuid.UUID]] = {}
    for numero in range(entites):
        ville = VILLES[numero % len(VILLES)]
        code = f"{ville.upper()[:6]}{numero:02d}"
        entite = connexion.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, "
                "timezone, activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', "
                "'Europe/Paris', now()) RETURNING id"
            ),
            {"code": code, "nom": f"eXalt {ville} {numero}", "ville": ville},
        ).scalar_one()
        identifiants_d_entites.append(entite)
        mesure.entites += 1

        depot_cercles = DepotLocal(connexion, "circle", entite)
        cercles_par_entite[entite] = [
            depot_cercles.creer(code=code_cercle, name=nom_cercle)
            for code_cercle, nom_cercle in CERCLES
        ]
        mesure.cercles += len(CERCLES)

        depot_bureaux = DepotLocal(connexion, "office", entite)
        depot_bureaux.creer(code="SIEGE", name=f"Siege {ville}")
        mesure.bureaux += 1

        depot_metiers = DepotLocal(connexion, "job_catalog", entite)
        metiers_par_entite[entite] = [
            depot_metiers.creer(code=code_metier, label=libelle) for code_metier, libelle in METIERS
        ]
        mesure.metiers += len(METIERS)

    #  2. Les clients GLOBAUX, actives localement.
    clients: list[uuid.UUID] = []
    for numero in range(max(2, entites)):
        nom = f"client fictif {numero}"
        clients.append(
            connexion.execute(
                text(
                    "INSERT INTO client (canonical_name, display_name, status) "
                    "VALUES (:canonique, :affiche, 'active') RETURNING id"
                ),
                {"canonique": nom, "affiche": nom.title()},
            ).scalar_one()
        )
        mesure.clients += 1
    for entite in identifiants_d_entites:
        depot_activations = DepotLocal(connexion, "entity_client", entite)
        for client in clients:
            depot_activations.creer(client_id=client)
            mesure.activations += 1

    #  3. Un DSM habilite par entite — il doit exister AVANT toute affectation.
    dsm_par_entite: dict[uuid.UUID, uuid.UUID] = {}
    esm_par_entite: dict[uuid.UUID, uuid.UUID] = {}
    for entite in identifiants_d_entites:
        personne, _ = _personne(connexion, tirage, compteur)
        mesure.personnes += 1
        depot_appartenances = DepotLocal(connexion, "entity_membership", entite)
        depot_appartenances.creer(
            person_id=personne,
            arrival_date=dt.date(2024, 1, 1),
            membership_state="active",
            professional_category="consultant",
            profile_visibility="published",
        )
        mesure.appartenances += 1
        DepotLocal(connexion, "framework_responsibility_assignment", entite).creer(
            person_id=personne,
            responsibility_type="DSM",
            assigned_by_person_id=personne,
            starts_at=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
        )
        mesure.responsabilites += 1
        dsm_par_entite[entite] = personne

        #  UN ESM PAR ENTITE — AJOUTE AU LOT 3, `T5`, ET LE JEU EN MANQUAIT.
        #
        #  La matrice fait de l'ESM le « responsable fonctionnel de l'entite »,
        #  et le §8.4 exige qu'un attributeur de categorie `dg` soit « ESM ou
        #  super-administrateur ». Le jeu de recette n'en creait AUCUN : il
        #  attribuait la categorie `dg` par un DSM, ce que `T5` refuse desormais.
        #
        #  **Le jeu de recette a donc revele une lacune de lui-meme**, et la
        #  corriger le rend plus fidele au modele, non seulement conforme au
        #  nouveau controle : une entite sans responsable fonctionnel n'existe
        #  pas dans la matrice.
        esm, _ = _personne(connexion, tirage, compteur)
        mesure.personnes += 1
        DepotLocal(connexion, "entity_membership", entite).creer(
            person_id=esm,
            arrival_date=dt.date(2024, 1, 1),
            membership_state="active",
            professional_category="consultant",
            profile_visibility="published",
        )
        mesure.appartenances += 1
        DepotLocal(connexion, "framework_responsibility_assignment", entite).creer(
            person_id=esm,
            responsibility_type="ESM",
            assigned_by_person_id=esm,
            starts_at=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
        )
        mesure.responsabilites += 1
        esm_par_entite[entite] = esm

    #  4. Un Booster par cercle — le §25.1 en interdit deux, et une personne ne
    #     peut pas etre Booster dans deux entites (declencheur de `T8`).
    for entite in identifiants_d_entites:
        depot_responsabilites = DepotLocal(connexion, "framework_responsibility_assignment", entite)
        for cercle in cercles_par_entite[entite]:
            personne, _ = _personne(connexion, tirage, compteur)
            mesure.personnes += 1
            DepotLocal(connexion, "entity_membership", entite).creer(
                person_id=personne,
                arrival_date=dt.date(2024, 6, 1),
                membership_state="active",
                professional_category="consultant",
                profile_visibility="published",
            )
            mesure.appartenances += 1
            depot_responsabilites.creer(
                person_id=personne,
                responsibility_type="BOOSTER",
                circle_id=cercle,
                assigned_by_person_id=dsm_par_entite[entite],
                starts_at=dt.datetime(2024, 6, 1, tzinfo=dt.UTC),
            )
            mesure.responsabilites += 1

    #  5. Les profils, repartis sur les entites.
    for indice in range(profils):
        entite = identifiants_d_entites[indice % len(identifiants_d_entites)]
        personne, _ = _personne(connexion, tirage, compteur)
        mesure.personnes += 1
        arrivee = dt.date(2025, 1, 1) + dt.timedelta(days=indice % 300)
        appartenance = DepotLocal(connexion, "entity_membership", entite).creer(
            person_id=personne,
            arrival_date=arrivee,
            membership_state="active",
            professional_category=CATEGORIES_DE_MASSE[indice % len(CATEGORIES_DE_MASSE)],
            profile_visibility=VISIBILITES_PROFIL[indice % len(VISIBILITES_PROFIL)],
        )
        mesure.appartenances += 1

        debut = dt.datetime(arrivee.year, arrivee.month, arrivee.day, tzinfo=dt.UTC)
        DepotLocal(connexion, "membership_job_assignment", entite).creer(
            entity_membership_id=appartenance,
            job_catalog_id=tirage.choice(metiers_par_entite[entite]),
            starts_at=debut,
        )
        mesure.affectations_metier += 1

        DepotLocal(connexion, "circle_membership", entite).creer(
            entity_membership_id=appartenance,
            circle_id=tirage.choice(cercles_par_entite[entite]),
            membership_type="principal",
            starts_at=debut,
        )
        mesure.appartenances_cercle += 1

        #  Une situation sur deux est une `mission` — le client doit etre ACTIVE
        #  dans l'entite, ce que l'etape 2 a fait.
        depot_situations = DepotLocal(connexion, "professional_status_assignment", entite)
        if indice % 2:
            depot_situations.creer(
                entity_membership_id=appartenance,
                status="mission",
                client_id=tirage.choice(clients),
                starts_at=debut,
            )
        else:
            depot_situations.creer(
                entity_membership_id=appartenance,
                status="intercontract",
                starts_at=debut,
            )
        mesure.situations += 1

        #  Un consultant sur trois recoit un DSM.
        if indice % 3 == 0:
            DepotLocal(connexion, "dsm_assignment", entite).creer(
                consultant_membership_id=appartenance,
                dsm_person_id=dsm_par_entite[entite],
                starts_at=debut,
            )
            mesure.affectations_dsm += 1

    #  6. LES CAS LIMITES, nommes un par un — le critere les exige.
    mesure.cas_limites = _engendrer_les_cas_limites(
        connexion,
        tirage=tirage,
        compteur=compteur,
        entites=identifiants_d_entites,
        clients=clients,
        dsm_par_entite=dsm_par_entite,
        esm_par_entite=esm_par_entite,
        cercles_par_entite=cercles_par_entite,
        mesure=mesure,
    )
    return mesure


def _engendrer_les_cas_limites(
    connexion: Connection,
    *,
    tirage: random.Random,
    compteur: Compteur,
    entites: list[uuid.UUID],
    clients: list[uuid.UUID],
    dsm_par_entite: dict[uuid.UUID, uuid.UUID],
    esm_par_entite: dict[uuid.UUID, uuid.UUID],
    cercles_par_entite: dict[uuid.UUID, list[uuid.UUID]],
    mesure: Volumetrie,
) -> list[str]:
    """Les cas limites que le critere de `US007` exige, chacun NOMME."""
    limites: list[str] = []
    premiere = entites[0]

    #  (a) Une MOBILITE inter-entites, obligatoirement SEQUENTIELLE.
    if len(entites) >= 2:
        personne, _ = _personne(connexion, tirage, compteur)
        mesure.personnes += 1
        DepotLocal(connexion, "entity_membership", premiere).creer(
            person_id=personne,
            arrival_date=dt.date(2023, 1, 1),
            departure_date=dt.date(2023, 12, 31),
            membership_state="archived",
            professional_category="consultant",
            profile_visibility="draft",
        )
        DepotLocal(connexion, "entity_membership", entites[1]).creer(
            person_id=personne,
            arrival_date=dt.date(2024, 1, 1),
            membership_state="active",
            professional_category="consultant",
            profile_visibility="published",
        )
        mesure.appartenances += 2
        limites.append(
            "mobilite inter-entites SEQUENTIELLE — `ex_entity_membership_sans_chevauchement` "
            "n'a pas de clause `WHERE`, donc deux appartenances d'une personne ne peuvent "
            "jamais se chevaucher, meme dans deux entites"
        )

    #  (b) Une direction generale, qui EXIGE une responsabilite DSM locale.
    personne, _ = _personne(connexion, tirage, compteur)
    mesure.personnes += 1
    appartenance = DepotLocal(connexion, "entity_membership", premiere).creer(
        person_id=personne,
        arrival_date=dt.date(2024, 2, 1),
        membership_state="active",
        professional_category="consultant",
        profile_visibility="published",
    )
    mesure.appartenances += 1
    attribuer_la_categorie_dg(
        connexion,
        entite=premiere,
        appartenance=appartenance,
        #  L'ATTRIBUTEUR EST L'ESM, non le DSM. Le §8.4 l'exige depuis `T5` du
        #  LOT 3, et un DSM y est desormais refuse -- avec raison : le DSM
        #  encadre des consultants, il n'administre pas les categories.
        attribue_par=esm_par_entite[premiere],
        motif="jeu de recette",
    )
    mesure.responsabilites += 1
    limites.append(
        "une categorie `dg`, creee par `attribuer_la_categorie_dg` — le declencheur "
        "`dg_implique_dsm_local` la refuserait sans responsabilite `DSM` prealable"
    )

    #  (c) Un client GLOBALEMENT archive mais LOCALEMENT actif — §7.2.
    client_archive = connexion.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affiche, 'archived') RETURNING id"
        ),
        {"canonique": "client fictif archive", "affiche": "Client Fictif Archive"},
    ).scalar_one()
    mesure.clients += 1
    DepotLocal(connexion, "entity_client", premiere).creer(client_id=client_archive)
    mesure.activations += 1
    limites.append(
        "un client GLOBALEMENT archive mais LOCALEMENT actif — le §7.2 l'autorise, "
        "et c'est pourquoi le declencheur de `T10` lit `entity_client`, non `client.status`"
    )

    #  (d) Une activation locale ARCHIVEE, alors que le client est actif.
    if len(entites) >= 2:
        connexion.execute(
            text(
                "INSERT INTO entity_client (entity_id, client_id, archived_at) "
                "VALUES (:entite, :client, now())"
            ),
            {"entite": entites[1], "client": client_archive},
        )
        mesure.activations += 1
        limites.append("une activation locale ARCHIVEE, le client restant actif globalement")

    #  (e) Un cercle SECONDAIRE en plus du principal — le §8.2 les autorise.
    personne, _ = _personne(connexion, tirage, compteur)
    mesure.personnes += 1
    appartenance = DepotLocal(connexion, "entity_membership", premiere).creer(
        person_id=personne,
        arrival_date=dt.date(2024, 3, 1),
        membership_state="active",
        professional_category="consultant",
        profile_visibility="published",
    )
    mesure.appartenances += 1
    depot_cercles = DepotLocal(connexion, "circle_membership", premiere)
    for rang, type_appartenance in enumerate(("principal", "secondary", "secondary")):
        depot_cercles.creer(
            entity_membership_id=appartenance,
            circle_id=cercles_par_entite[premiere][rang],
            membership_type=type_appartenance,
            starts_at=dt.datetime(2024, 3, 1, tzinfo=dt.UTC),
        )
        mesure.appartenances_cercle += 1
    limites.append(
        "UN cercle principal et DEUX cercles secondaires actifs — le §8.2 les autorise "
        "explicitement, et une exclusion sans clause `WHERE` les aurait interdits"
    )

    #  (f) Une succession de situations professionnelles, sans chevauchement.
    personne, _ = _personne(connexion, tirage, compteur)
    mesure.personnes += 1
    appartenance = DepotLocal(connexion, "entity_membership", premiere).creer(
        person_id=personne,
        arrival_date=dt.date(2024, 4, 1),
        membership_state="active",
        professional_category="consultant",
        profile_visibility="published",
    )
    mesure.appartenances += 1
    depot_situations = DepotLocal(connexion, "professional_status_assignment", premiere)
    depot_situations.creer(
        entity_membership_id=appartenance,
        status="intercontract",
        starts_at=dt.datetime(2024, 4, 1, tzinfo=dt.UTC),
        ends_at=dt.datetime(2024, 6, 1, tzinfo=dt.UTC),
    )
    depot_situations.creer(
        entity_membership_id=appartenance,
        status="mission",
        client_id=clients[0],
        starts_at=dt.datetime(2024, 6, 1, tzinfo=dt.UTC),
    )
    mesure.situations += 2
    limites.append(
        "une SUCCESSION de situations, `intercontract` puis `mission`, aux periodes "
        "jointives — les plages sont semi-ouvertes `[a,b)`, donc elles ne se chevauchent pas"
    )

    #  (g) Une entite ARCHIVEE, sans appartenance — le declencheur en interdirait une.
    connexion.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "archived_at) VALUES (:code, :nom, :ville, 'FR', 'archived', 'Europe/Paris', now())"
        ),
        {"code": "ARCHIVE0", "nom": "eXalt Archive", "ville": "Nulle part"},
    )
    mesure.entites += 1
    #  LE LIBELLE NE PORTE PAS L'IDENTIFIANT, et c'est un correctif : ma premiere
    #  version y interpolait l'UUID de l'entite, ce qui rendait la liste des cas
    #  limites NON COMPARABLE d'une execution a l'autre et faisait echouer le test
    #  de determinisme. **Un libelle descriptif n'a pas a porter une valeur
    #  aleatoire** : le code `ARCHIVE0` suffit a la retrouver.
    limites.append(
        "une entite ARCHIVEE, de code `ARCHIVE0`, sans appartenance — "
        "`entity_membership_entite_non_archivee` en refuserait une"
    )
    return limites
