#!/usr/bin/env python3
"""Creer un compte de service et lui delivrer un jeton — cahier §22.

LOT 3, sous-etape `T10`, story `MVP-L03-US007`.

CE QUE CE SCRIPT NE FAIT PAS, ET C'EST DELIBERE

  **Il ne cree AUCUNE personne.** Le §10.5 exige un « proprietaire technique », et
  la colonne `technical_owner_person_id` est `NOT NULL` : le compte de service est
  rattache a un humain responsable. Creer cette personne au passage fabriquerait
  un collaborateur qui n'existe pas -- meme motif que
  `provisionner-administrateur.py`, qui refuse pour la meme raison.

  **Il ne reutilise JAMAIS un jeton existant.** Le §10.5 dit « un hash du jeton » :
  la base ne porte pas le jeton en clair, donc il est impossible de le re-afficher.
  Chaque execution en cree un **nouveau**, et les precedents restent valides
  jusqu'a leur expiration ou leur revocation -- ce qui est le comportement voulu :
  on renouvelle avant de retirer l'ancien, sinon le script tombe en panne.

  **Il n'accorde jamais `SUPER_ADMIN`.** Le §22.1 l'interdit explicitement : « aucun
  compte de service ne recoit automatiquement les droits de super-administrateur ».
  Ce script ne touche pas `technical_role_assignment`.

LE JETON EST AFFICHE UNE FOIS, ET UNE SEULE

  Comme le mot de passe de `make admin-local`. Le perdre oblige a en creer un
  autre, et c'est le prix d'un stockage par empreinte.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))
sys.path.insert(0, str(RACINE / "apps" / "api" / "tests"))


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--nom", required=True, help="nom du compte de service, unique")
    analyseur.add_argument(
        "--proprietaire", required=True, help="adresse du proprietaire technique, DEJA en base"
    )
    analyseur.add_argument(
        "--scopes", required=True, help="scopes separes par une virgule, cahier §22"
    )
    analyseur.add_argument("--jours", type=int, default=None, help="duree, plafond par defaut")
    analyseur.add_argument("--entite", default=None, help="code d'entite, ou rien pour global")
    arguments = analyseur.parse_args()

    from conftest import HOTE_LOCAL, VARIABLES_MINIMALES, lire_env_du_depot
    from sqlalchemy import text

    from app.auth.comptes_de_service import DureeRefusee, creer_un_jeton
    from app.auth.scopes import ScopeInvalide, controler_les_scopes
    from app.configuration.settings import Parametres
    from app.shared.database import moteur

    env = lire_env_du_depot()
    valeurs = dict(VARIABLES_MINIMALES)
    for nom in (
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_MIGRATIONS_USER",
        "POSTGRES_MIGRATIONS_PASSWORD",
        "POSTGRES_RUNTIME_USER",
        "POSTGRES_RUNTIME_PASSWORD",
        "REDIS_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "MINIO_BUCKET",
        "APP_SECRET_KEY",
        "SERVICE_TOKEN_MAX_DAYS",
    ):
        if nom in env:
            valeurs[nom] = env[nom]
    parametres = Parametres(
        **valeurs,
        POSTGRES_HOST=HOTE_LOCAL,
        POSTGRES_PORT=int(env.get("POSTGRES_HOST_PORT", "5432")),
        REDIS_HOST=HOTE_LOCAL,
        REDIS_PORT=int(env.get("REDIS_HOST_PORT", "6379")),
        MINIO_ENDPOINT=f"{HOTE_LOCAL}:{env.get('MINIO_HOST_PORT', '9000')}",
    )
    plafond = parametres.SERVICE_TOKEN_MAX_DAYS
    jours = arguments.jours if arguments.jours is not None else plafond

    print()
    print("  Compte de service — cahier §22, story MVP-L03-US007")
    print(f"    info     plafond de duree : {plafond} jours (QO-072, arbitrage du 22/08/2026)")

    try:
        scopes = controler_les_scopes([s.strip() for s in arguments.scopes.split(",") if s.strip()])
    except ScopeInvalide as erreur:
        print(f"    ECHEC    {erreur}")
        return 1
    print(f"    ok       {len(scopes)} scope(s) valides : {', '.join(scopes)}")

    instant = dt.datetime.now(tz=dt.UTC)
    with moteur(parametres).begin() as connexion:
        proprietaire = connexion.execute(
            text("SELECT id FROM person WHERE email_normalized = :adresse"),
            {"adresse": arguments.proprietaire.strip().lower()},
        ).scalar_one_or_none()
        if proprietaire is None:
            print(f"    ECHEC    proprietaire technique introuvable : {arguments.proprietaire}")
            print("             Ce script ne CREE aucune personne — voir son en-tete.")
            return 1

        entite = None
        if arguments.entite:
            entite = connexion.execute(
                text("SELECT id FROM entity WHERE code = :code"),
                {"code": arguments.entite},
            ).scalar_one_or_none()
            if entite is None:
                print(f"    ECHEC    entite introuvable : {arguments.entite}")
                return 1

        compte = connexion.execute(
            text("SELECT id FROM service_account WHERE name = :nom"),
            {"nom": arguments.nom},
        ).scalar_one_or_none()
        if compte is None:
            compte = connexion.execute(
                text(
                    "INSERT INTO service_account "
                    "(name, description, entity_id, state, technical_owner_person_id) "
                    "VALUES (:nom, :description, :entite, 'active', :proprietaire) RETURNING id"
                ),
                {
                    "nom": arguments.nom,
                    "description": f"Compte de service {arguments.nom}",
                    "entite": entite,
                    "proprietaire": proprietaire,
                },
            ).scalar_one()
            print(f"    ok       compte cree : {arguments.nom}")
        else:
            #  **AUCUNE MODIFICATION D'UN COMPTE EXISTANT.** Changer son entite ou
            #  son proprietaire au passage serait une elevation silencieuse.
            print(f"    ok       compte existant reutilise : {arguments.nom}")

        try:
            jeton, identifiant = creer_un_jeton(
                connexion,
                compte=uuid.UUID(str(compte)),
                scopes=scopes,
                instant=instant,
                jours=jours,
                jours_maximum=plafond,
            )
        except (DureeRefusee, ScopeInvalide) as erreur:
            print(f"    ECHEC    {erreur}")
            return 1

    print(f"    ok       jeton cree, identifiant {identifiant}")
    print(f"    ok       expire le {(instant + dt.timedelta(days=jours)).date().isoformat()}")
    print()
    print("  ATTENTION — LE JETON N'EST AFFICHE QU'UNE FOIS. La base n'en porte que")
    print("  l'empreinte (§10.5, « un hash du jeton ») : le perdre oblige a en creer")
    print("  un autre. Ne le colle NI dans Git, NI dans un message de commit.")
    print()
    print(f"    {jeton}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
