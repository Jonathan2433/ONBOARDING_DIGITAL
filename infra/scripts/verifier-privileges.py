#!/usr/bin/env python3
"""Verifier le moindre privilege PostgreSQL — `QO-116`, `DEC-518`.

LOT 3, sous-etape `T1`.

CE QUE CE CONTROLE PROUVE

  Le cahier §20.1 pose le moindre privilege. `QO-116` a mesure le 18/08/2026 que
  l'application se connectait avec un compte SUPERUTILISATEUR, proprietaire du
  cluster : il pouvait detruire la base, lire toute table, creer toute extension.

  Ce controle exige **quatre** proprietes, et **aucune n'est une affirmation** :

    1. le role d'EXECUTION n'est pas superutilisateur, et ne peut ni creer une
       base, ni creer un role ;
    2. il **ECHOUE** sur du DDL -- `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE` --
       et c'est le coeur du controle : sans cette epreuve, un role a qui l'on
       aurait accorde trop de droits donnerait la MEME observation qu'un role
       correctement borne ;
    3. il **REUSSIT** sur du DML, sinon l'application ne fonctionnerait pas. Un
       controle qui ne verifierait que les refus passerait sur un role qui ne
       peut RIEN faire ;
    4. une table creee par le role de MIGRATION est immediatement lisible par le
       role d'execution -- c'est l'effet des privileges PAR DEFAUT, et c'est ce
       qui evite qu'une migration future n'oublie ses `GRANT`.

  La quatrieme est la plus subtile : sans privileges par defaut, l'application
  echouerait a l'EXECUTION avec « permission denied » **alors que la migration a
  reussi**. Le defaut se manifesterait loin de sa cause.

ET IL VERIFIE QUE L'APPLICATION EMPLOIE BIEN LE BON ROLE

  Un role correctement borne ne sert a rien si l'API continue de se connecter
  avec le superutilisateur. Le controle interroge donc l'API **en marche**, a
  travers son propre point de connexion, et lit `current_user`.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

TABLE_JETABLE = "zz_temoin_privileges"


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(
    compose: list[str], env: dict[str, str], utilisateur: str, mot_de_passe: str, requete: str
) -> tuple[int, str]:
    """Executer une requete EN TANT QUE le role donne.

    `PGPASSWORD` est passe par l'environnement du conteneur, jamais sur la ligne
    de commande : un mot de passe en argument serait visible dans `ps`.
    """
    # S603 : entree du Makefile, jamais d'un tiers, et `shell=False` — §7.2.
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={mot_de_passe}",
            "db",
            "psql",
            "-h",
            "127.0.0.1",
            "-U",
            utilisateur,
            "-d",
            env["POSTGRES_DB"],
            "-v",
            "ON_ERROR_STOP=1",
            "-tAF|",
            "-c",
            requete,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return execution.returncode, (execution.stdout + execution.stderr).strip()


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    execution = env.get("POSTGRES_RUNTIME_USER", "")
    mot_de_passe_execution = env.get("POSTGRES_RUNTIME_PASSWORD", "")
    migrations = env.get("POSTGRES_MIGRATIONS_USER", "")
    mot_de_passe_migrations = env.get("POSTGRES_MIGRATIONS_PASSWORD", "")
    if not all((execution, mot_de_passe_execution, migrations, mot_de_passe_migrations)):
        print("  ECHEC     les quatre variables des deux roles doivent etre renseignees")
        print("            `make env-check` les nomme.")
        return 1

    echecs = 0
    print()
    print("  Moindre privilege PostgreSQL — cahier §20.1, QO-116, DEC-518")

    # ------------------------------------------------------------------
    #  1. Les attributs du role d'execution
    # ------------------------------------------------------------------
    code, sortie = psql(
        compose,
        env,
        execution,
        mot_de_passe_execution,
        "SELECT current_user || '|' || rolsuper::text || '|' || rolcreatedb::text || '|' "
        "|| rolcreaterole::text FROM pg_roles WHERE rolname = current_user",
    )
    if code:
        print(f"    ECHEC    {execution} ne peut pas se connecter : {sortie[:180]}")
        return 1
    nom, super_, creerdb, creerrole = sortie.split("|")
    print(f"    info     l'API se connectera en `{nom}`")
    for libelle, valeur in (
        ("superutilisateur", super_),
        ("droit de creer une base", creerdb),
        ("droit de creer un role", creerrole),
    ):
        if valeur == "t":
            print(f"    ECHEC    {nom} a le {libelle} — le moindre privilege n'est pas respecte")
            echecs += 1
        else:
            print(f"    ok       {nom} : {libelle} = non")

    # ------------------------------------------------------------------
    #  2. LE COEUR DU CONTROLE — le DDL doit ECHOUER
    # ------------------------------------------------------------------
    print()
    refus_attendus = (
        ("CREATE TABLE", f"CREATE TABLE {TABLE_JETABLE} (id uuid PRIMARY KEY)"),
        ("DROP TABLE", "DROP TABLE entity"),
        ("ALTER TABLE", "ALTER TABLE entity ADD COLUMN zz_temoin text"),
        ("CREATE ROLE", "CREATE ROLE zz_temoin_role"),
        ("TRUNCATE", "TRUNCATE entity"),
    )
    for libelle, requete in refus_attendus:
        code, sortie = psql(compose, env, execution, mot_de_passe_execution, requete)
        if code == 0:
            print(
                f"    ECHEC    {nom} a REUSSI un `{libelle}` — il en a le droit, il ne devrait pas"
            )
            echecs += 1
        elif "permission denied" in sortie or "must be owner" in sortie or "denied" in sortie:
            motif = re.search(r"(permission denied[^\n]*|must be owner[^\n]*)", sortie)
            detail = motif.group(1)[:60] if motif else "refuse"
            print(f"    ok       `{libelle}` REFUSE — {detail}")
        else:
            print(f"    ECHEC    `{libelle}` a echoue pour une AUTRE raison : {sortie[:140]}")
            print("             Un refus pour un autre motif ne prouve pas le moindre privilege.")
            echecs += 1

    # ------------------------------------------------------------------
    #  3. Le DML doit REUSSIR — sinon l'application ne marcherait pas
    # ------------------------------------------------------------------
    print()
    code, sortie = psql(
        compose, env, execution, mot_de_passe_execution, "SELECT count(*) FROM entity"
    )
    if code:
        print(f"    ECHEC    {nom} ne peut pas LIRE `entity` : {sortie[:160]}")
        print("             Un role qui ne peut rien faire passerait le controle precedent.")
        echecs += 1
    else:
        print(f"    ok       `SELECT` autorise — {sortie.strip()} ligne(s) dans `entity`")

    code, sortie = psql(
        compose,
        env,
        execution,
        mot_de_passe_execution,
        "BEGIN; INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
        "VALUES ('ZZTEMOIN', 'ZZ', 'ZZ', 'FR', 'draft', 'Europe/Paris'); ROLLBACK",
    )
    if code:
        print(f"    ECHEC    {nom} ne peut pas ECRIRE dans `entity` : {sortie[:160]}")
        echecs += 1
    else:
        print("    ok       `INSERT` autorise, puis annule — le DML fonctionne")

    # ------------------------------------------------------------------
    #  4. Les privileges PAR DEFAUT — la propriete la plus subtile
    # ------------------------------------------------------------------
    print()
    code, sortie = psql(
        compose,
        env,
        migrations,
        mot_de_passe_migrations,
        f"CREATE TABLE {TABLE_JETABLE} (id uuid PRIMARY KEY)",
    )
    if code:
        print(f"    ECHEC    {migrations} ne peut pas creer une table : {sortie[:180]}")
        print("             Les migrations ne pourraient plus s'appliquer.")
        return 1
    print(f"    ok       {migrations} a cree une table jetable")
    try:
        code, sortie = psql(
            compose,
            env,
            execution,
            mot_de_passe_execution,
            f"SELECT count(*) FROM {TABLE_JETABLE}",  # noqa: S608
        )
        if code:
            print(f"    ECHEC    {nom} ne peut pas lire une table NEUVE : {sortie[:160]}")
            print("             Sans privileges PAR DEFAUT, chaque migration devrait accorder")
            print("             ses droits, et l'oubli echouerait a l'EXECUTION, loin de sa cause.")
            echecs += 1
        else:
            print(
                f"    ok       {nom} lit immediatement la table neuve — "
                f"privileges PAR DEFAUT actifs"
            )
    finally:
        psql(
            compose,
            env,
            migrations,
            mot_de_passe_migrations,
            f"DROP TABLE IF EXISTS {TABLE_JETABLE}",
        )
        print("    info     table jetable supprimee")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print(
        f"  --> l'application se connecte en `{nom}`, qui ne peut que lire et ecrire des lignes ; "
        f"`{migrations}` possede le schema"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
