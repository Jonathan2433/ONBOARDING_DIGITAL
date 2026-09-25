#!/usr/bin/env python3
"""Preparer, verifier ou retirer le decor fictif de la demonstration client.

Le generateur du LOT 2 fournit la volumetrie. Ce script ne le remplace pas : il
transforme huit profils publies de Bordeaux en personnages stables et lisibles,
pose les quatre jetons de cercle deja compris par le frontend, puis verifie les
invariants dont depend le conducteur de demonstration.

Toutes les adresses restent dans ``exemple.test``. Le mode ``reinitialiser`` est
volontairement borne au fichier ``.env`` de developpement et exige une
confirmation explicite, car il vide les tables applicatives de la base locale.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

CODE_ENTITE = "BORDEA00"
ADRESSE_ADMIN = "demo.client@exemple.test"


@dataclass(frozen=True)
class Persona:
    prenom: str
    nom: str
    presentation: str
    anecdote: str

    @property
    def adresse(self) -> str:
        return f"demo.{self.prenom.lower()}.{self.nom.lower()}@exemple.test"


PERSONAS = (
    Persona(
        "Alice",
        "Martin",
        "Consultante produit, Alice transforme les besoins complexes en parcours simples.",
        "Elle tient un carnet de bonnes idees glanees pendant ses voyages en train.",
    ),
    Persona(
        "Bastien",
        "Moreau",
        "Ingenieur data, Bastien aime rendre les indicateurs utiles et comprehensibles.",
        "Il sait reconnaitre un morceau de jazz en moins de dix secondes.",
    ),
    Persona(
        "Chloe",
        "Bernard",
        "Developpeuse cloud, Chloe accompagne les equipes vers des plateformes fiables.",
        "Elle organise des randonnees dont le parcours finit toujours pres d'une boulangerie.",
    ),
    Persona(
        "David",
        "Robert",
        "Consultant en mission, David facilite la collaboration entre produit et technique.",
        "Il collectionne les cartes de metro des villes qu'il visite.",
    ),
    Persona(
        "Emma",
        "Petit",
        "Product owner, Emma anime les ateliers et fait avancer les decisions collectives.",
        "Elle prepare un quiz musical pour chaque evenement d'equipe.",
    ),
    Persona(
        "Farid",
        "Durand",
        "Ingenieur donnees, Farid construit des produits data robustes et accessibles.",
        "Il cuisine un plat different chaque vendredi soir.",
    ),
    Persona(
        "Gabrielle",
        "Leroux",
        "Developpeuse, Gabrielle partage volontiers ses pratiques et ses retours d'experience.",
        "Elle restaure de vieux appareils photo argentiques.",
    ),
    Persona(
        "Hugo",
        "Roux",
        "Consultant produit, Hugo aide les equipes a prioriser avec des objectifs mesurables.",
        "Il connait toutes les pistes cyclables autour de Bordeaux.",
    ),
)

COULEURS = {"TECH": "bleu", "DATA": "rose", "CLOUD": "bleu-fonce", "PROD": "jaune"}


def charger_env(chemin: pathlib.Path) -> None:
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(), valeur.strip())
    os.environ["POSTGRES_HOST"] = "127.0.0.1"


def parametres_et_moteurs() -> tuple[object, object]:
    from app.configuration.settings import Parametres
    from app.shared.database import moteur, moteur_migrations

    parametres = Parametres()
    return moteur(parametres), moteur_migrations(parametres)


def preparer_identite_administrateur(connexion: Connection) -> None:
    """Poser l'identite metier fictive avant l'amorcage du compte administrateur.

    `admin-local` refuse, a raison, d'inventer une personne : une commande
    d'exploitation ne doit pas devenir une source d'identites metier. Le decor
    de demonstration, lui, EST la source explicite de cette identite fictive.
    Elle doit donc etre creee ici avant que `demo-init` appelle `admin-local`.
    """
    connexion.execute(
        text(
            "INSERT INTO person "
            "(email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:adresse, :adresse, 'Demo', 'Client', 'active') "
            "ON CONFLICT (email_normalized) DO UPDATE SET "
            "account_state='active', archived_at=NULL, updated_at=now()"
        ),
        {"adresse": ADRESSE_ADMIN},
    )
    connexion.execute(
        text(
            "INSERT INTO technical_role_assignment "
            "(person_id, entity_id, role_type, starts_at) "
            "SELECT id, NULL, 'SUPER_ADMIN', now() FROM person "
            "WHERE email_normalized=:adresse AND NOT EXISTS ("
            "SELECT 1 FROM technical_role_assignment tra "
            "WHERE tra.person_id=person.id AND tra.role_type='SUPER_ADMIN' "
            "AND tra.ends_at IS NULL AND tra.archived_at IS NULL)"
        ),
        {"adresse": ADRESSE_ADMIN},
    )


def enrichir() -> int:
    moteur_execution, _ = parametres_et_moteurs()
    with moteur_execution.begin() as connexion:
        preparer_identite_administrateur(connexion)
        lignes = (
            connexion.execute(
                text(
                    "SELECT em.id AS appartenance_id, p.id AS personne_id "
                    "FROM entity_membership em "
                    "JOIN entity e ON e.id = em.entity_id "
                    "JOIN person p ON p.id = em.person_id "
                    "WHERE e.code = :code AND em.membership_state = 'active' "
                    "AND em.profile_visibility = 'published' AND p.account_state = 'active' "
                    "ORDER BY p.email_normalized LIMIT :nombre"
                ),
                {"code": CODE_ENTITE, "nombre": len(PERSONAS)},
            )
            .mappings()
            .all()
        )
        if len(lignes) != len(PERSONAS):
            print(
                f"  ECHEC    {len(lignes)} profils publiés disponibles dans {CODE_ENTITE}, "
                f"{len(PERSONAS)} attendus"
            )
            return 1

        for ligne, persona in zip(lignes, PERSONAS, strict=True):
            connexion.execute(
                text(
                    "UPDATE person SET email=:adresse, email_normalized=:adresse, "
                    "first_name=:prenom, last_name=:nom, updated_at=now() WHERE id=:id"
                ),
                {
                    "adresse": persona.adresse,
                    "prenom": persona.prenom,
                    "nom": persona.nom,
                    "id": ligne["personne_id"],
                },
            )
            connexion.execute(
                text(
                    "UPDATE entity_membership SET short_bio=:presentation, fun_fact=:anecdote, "
                    "profile_published_at=COALESCE(profile_published_at, now()), "
                    "updated_at=now() WHERE id=:id"
                ),
                {
                    "presentation": persona.presentation,
                    "anecdote": persona.anecdote,
                    "id": ligne["appartenance_id"],
                },
            )

        for code, couleur in COULEURS.items():
            connexion.execute(
                text(
                    "UPDATE circle SET color_token=:couleur, updated_at=now() "
                    "WHERE entity_id=(SELECT id FROM entity WHERE code=:entite) AND code=:code"
                ),
                {"couleur": couleur, "entite": CODE_ENTITE, "code": code},
            )

        noms_clients = ("Atlas", "Horizon", "Boreal")
        clients = connexion.execute(
            text("SELECT id FROM client WHERE status='active' ORDER BY canonical_name LIMIT 3")
        ).scalars()
        for identifiant, nom in zip(clients, noms_clients, strict=True):
            connexion.execute(
                text(
                    "UPDATE client SET canonical_name=:canonique, display_name=:affiche, "
                    "updated_at=now() WHERE id=:id"
                ),
                {
                    "canonique": f"client fictif {nom.lower()}",
                    "affiche": f"Client Fictif {nom}",
                    "id": identifiant,
                },
            )

    print(f"  ok       {len(PERSONAS)} personas fictifs poses dans {CODE_ENTITE}")
    print(f"  ok       {len(COULEURS)} couleurs de cercle issues des jetons existants")
    print(f"  ok       identite administrateur fictive posee : {ADRESSE_ADMIN}")
    return 0


def verifier() -> int:
    moteur_execution, _ = parametres_et_moteurs()
    erreurs: list[str] = []
    with moteur_execution.connect() as connexion:
        entite = connexion.execute(
            text("SELECT count(*) FROM entity WHERE code=:code AND status='active'"),
            {"code": CODE_ENTITE},
        ).scalar_one()
        if entite != 1:
            erreurs.append(f"entite active {CODE_ENTITE} absente")

        for persona in PERSONAS:
            compte = connexion.execute(
                text(
                    "SELECT count(*) FROM person p JOIN entity_membership em ON em.person_id=p.id "
                    "JOIN entity e ON e.id=em.entity_id WHERE p.email_normalized=:adresse "
                    "AND e.code=:code AND em.membership_state='active' "
                    "AND em.profile_visibility='published' AND em.short_bio IS NOT NULL "
                    "AND em.fun_fact IS NOT NULL"
                ),
                {"adresse": persona.adresse, "code": CODE_ENTITE},
            ).scalar_one()
            if compte != 1:
                erreurs.append(f"persona incomplet ou absent : {persona.adresse}")

        couleurs = dict(
            connexion.execute(
                text(
                    "SELECT c.code, c.color_token FROM circle c JOIN entity e ON e.id=c.entity_id "
                    "WHERE e.code=:code"
                ),
                {"code": CODE_ENTITE},
            ).all()
        )
        if any(couleurs.get(code) != couleur for code, couleur in COULEURS.items()):
            erreurs.append("jetons de couleur des cercles incomplets")

        interdites = connexion.execute(
            text(
                "SELECT count(*) FROM person WHERE email_normalized LIKE 'demo.%' "
                "AND email_normalized NOT LIKE '%@exemple.test'"
            )
        ).scalar_one()
        if interdites:
            erreurs.append(f"{interdites} adresse(s) demo hors du domaine reserve exemple.test")

        administrateur = connexion.execute(
            text(
                "SELECT count(*) FROM person p JOIN user_account ua ON ua.person_id=p.id "
                "JOIN technical_role_assignment tra ON tra.person_id=p.id "
                "WHERE p.email_normalized=:adresse AND ua.state='active' "
                "AND tra.role_type='SUPER_ADMIN' AND tra.ends_at IS NULL "
                "AND tra.archived_at IS NULL"
            ),
            {"adresse": ADRESSE_ADMIN},
        ).scalar_one()
        if administrateur != 1:
            erreurs.append(f"compte ou role SUPER_ADMIN absent : {ADRESSE_ADMIN}")

    if erreurs:
        for erreur in erreurs:
            print(f"  ECHEC    {erreur}")
        return 1
    print(f"  ok       {CODE_ENTITE} et les {len(PERSONAS)} personas sont prets")
    print(f"  ok       compte administrateur actif avec role SUPER_ADMIN : {ADRESSE_ADMIN}")
    print("  ok       toutes les adresses demo utilisent exemple.test")
    print("  ok       les quatre cercles portent un jeton compris par le frontend")
    return 0


def reinitialiser(confirmation: str | None) -> int:
    if confirmation != "EFFACER-LA-DEMO":
        print("  REFUS    passer --confirmation EFFACER-LA-DEMO pour vider la base locale")
        return 1
    _, moteur_admin = parametres_et_moteurs()
    with moteur_admin.begin() as connexion:
        tables = [
            table
            for table in inspect(connexion).get_table_names(schema="public")
            if table != "alembic_version"
        ]
        if tables:
            noms = ", ".join(f'"{table.replace(chr(34), chr(34) * 2)}"' for table in tables)
            connexion.execute(text(f"TRUNCATE TABLE {noms} RESTART IDENTITY CASCADE"))
    print(f"  ok       {len(tables)} tables applicatives videes ; migrations conservees")
    return 0


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("action", choices=("enrichir", "verifier", "reinitialiser"))
    analyseur.add_argument("--env-file", default=str(RACINE / ".env"))
    analyseur.add_argument("--confirmation")
    arguments = analyseur.parse_args()
    chemin_env = pathlib.Path(arguments.env_file).resolve()
    if chemin_env != (RACINE / ".env").resolve():
        print("  REFUS    la demonstration client est reservee a .env (developpement local)")
        return 1
    charger_env(chemin_env)
    if arguments.action == "enrichir":
        return enrichir()
    if arguments.action == "verifier":
        return verifier()
    return reinitialiser(arguments.confirmation)


if __name__ == "__main__":
    sys.exit(main())
