#!/usr/bin/env python3
"""Approvisionner les deux roles du moindre privilege — `QO-116`, `DEC-518`.

LOT 3, sous-etape `T1`.

POURQUOI CE N'EST PAS UNE MIGRATION

  Un role PostgreSQL est un objet de CLUSTER, non de schema, et `CREATE ROLE`
  exige le superutilisateur. Une migration executee par le role de migration ne
  pourrait donc pas creer ce role : la dependance serait circulaire.

  Ce script emploie le compte que cree `initdb` -- le seul superutilisateur --
  et c'est son **unique usage legitime** desormais. `make privileges-check`
  detecte toute autre utilisation.

POURQUOI TROIS COMPTES ET NON DEUX

  Le cahier §20.1 pose le moindre privilege. `initdb` cree un superutilisateur
  proprietaire du cluster, et **rien ne peut l'empecher d'exister** : pretendre le
  contraire serait pire que le nommer. Ce qui change, c'est que l'APPLICATION ne
  l'emploie plus.

CE QUE `ALTER DEFAULT PRIVILEGES` EVITE, ET C'EST LE POINT LE PLUS SUBTIL

  Une table creee par une migration FUTURE n'existe pas au moment ou l'on accorde
  les droits. Sans privileges par defaut, chaque migration devrait accorder
  elle-meme ses droits au role d'execution -- et **le jour ou l'une l'oublie,
  l'application echoue a l'execution avec « permission denied », alors que la
  migration a REUSSI**. Le defaut se manifesterait donc loin de sa cause.

  `ALTER DEFAULT PRIVILEGES FOR ROLE migrations` accorde d'avance. Un test
  l'eprouve en creant une table apres l'approvisionnement.

IL EST IDEMPOTENT, ET CELA SE VERIFIE

  Il est appele par `make up` a chaque demarrage, apres que la base est saine et
  **avant** que l'API ne demarre -- meme place que la creation du bucket MinIO,
  et meme motif que `DEC-477`. Deux executions de suite doivent produire le meme
  etat, et le script le RAPPORTE : il dit ce qu'il a cree et ce qui existait deja.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

#  Les droits du role d'execution. `SELECT, INSERT, UPDATE, DELETE` : des LIGNES,
#  jamais des tables. Ni `TRUNCATE` -- qui est un DDL deguise et contourne les
#  declencheurs `ON DELETE` -- ni `REFERENCES`, ni `TRIGGER`.
DROITS_DML = "SELECT, INSERT, UPDATE, DELETE"


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Executer une requete avec le SUPERUTILISATEUR. Motif du §7.2 : pas de shell."""
    # S603 : entree du Makefile, jamais d'un tiers, et `shell=False`.
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            env["POSTGRES_USER"],
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
    #  LES DEUX FLUX, ET C'EST UN CORRECTIF. `psql` envoie ses `NOTICE` sur
    #  stderr et ses resultats sur stdout : `stdout or stderr` en perdait un des
    #  deux selon les cas, et le compte d'objets transferes s'affichait
    #  « non rapporte » alors que le transfert avait bien eu lieu.
    return execution.returncode, (execution.stdout + execution.stderr).strip()


def citer(valeur: str) -> str:
    """Citer une chaine litterale SQL. Les mots de passe passent par ici."""
    return "'" + valeur.replace("'", "''") + "'"


def identifiant(nom: str) -> str:
    """Citer un IDENTIFIANT SQL — un nom de role. Motif verifie en amont."""
    return '"' + nom.replace('"', '""') + '"'


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

    manquantes = [
        nom
        for nom in (
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "POSTGRES_MIGRATIONS_USER",
            "POSTGRES_MIGRATIONS_PASSWORD",
            "POSTGRES_RUNTIME_USER",
            "POSTGRES_RUNTIME_PASSWORD",
        )
        if not env.get(nom)
    ]
    if manquantes:
        print(f"  ECHEC     variable(s) absente(s) du fichier d'environnement : {manquantes}")
        print("            `make env` les engendre ; `make env-check` les nomme.")
        return 1

    base = env["POSTGRES_DB"]
    superutilisateur = env["POSTGRES_USER"]
    migrations = env["POSTGRES_MIGRATIONS_USER"]
    execution = env["POSTGRES_RUNTIME_USER"]

    #  Un nom de role est interpole dans du SQL : un nom fantaisiste doit echouer
    #  ICI, avec un message clair, plutot que de produire du SQL malforme.
    import re

    motif = re.compile(r"^[a-z][a-z0-9_]*$")
    for nom in (migrations, execution):
        if not motif.match(nom):
            print(f"  ECHEC     nom de role invalide : {nom!r} — attendu `[a-z][a-z0-9_]*`")
            return 1
    if len({superutilisateur, migrations, execution}) != 3:
        print("  ECHEC     les trois comptes doivent avoir des noms DISTINCTS")
        print(
            f"            superutilisateur={superutilisateur} "
            f"migrations={migrations} execution={execution}"
        )
        return 1

    print()
    print("  Moindre privilege PostgreSQL — QO-116, DEC-518")

    #  ------------------------------------------------------------------
    #  1. Les deux roles, creation idempotente
    #  ------------------------------------------------------------------
    for nom, mot_de_passe in (
        (migrations, env["POSTGRES_MIGRATIONS_PASSWORD"]),
        (execution, env["POSTGRES_RUNTIME_PASSWORD"]),
    ):
        #  S608 : `citer()` echappe la valeur, et le nom du role a ete valide
        #  contre `^[a-z][a-z0-9_]*$` en amont. Aucune entree de tiers ici.
        requete_existence = f"SELECT 1 FROM pg_roles WHERE rolname = {citer(nom)}"  # noqa: S608
        code, sortie = psql(compose, env, requete_existence)
        existait = sortie.strip() == "1"
        verbe = "ALTER" if existait else "CREATE"
        #  Le mot de passe est REPOSE a chaque execution : le fichier
        #  d'environnement fait foi, et un mot de passe divergent entre le
        #  fichier et la base produirait un echec d'authentification dont la
        #  cause serait invisible.
        code, sortie = psql(
            compose,
            env,
            f"{verbe} ROLE {identifiant(nom)} LOGIN PASSWORD {citer(mot_de_passe)} "
            f"NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT",
        )
        if code:
            print(f"    ECHEC    {verbe} ROLE {nom} : {sortie[:180]}")
            return 1
        etat = "existait deja, mot de passe repose" if existait else "CREE"
        print(f"    ok       role {nom} — {etat}")

    #  ------------------------------------------------------------------
    #  2. Les droits du role de MIGRATION
    #  ------------------------------------------------------------------
    #  `CREATE ON DATABASE` est ce qui autorise `CREATE EXTENSION` d'une
    #  extension DE CONFIANCE. Mesure du 20/08/2026 : `btree_gist` est
    #  `trusted = t` sur PostgreSQL 17.7, donc installable sans superutilisateur
    #  par un role ayant ce droit. Sans lui, la migration `0002` echouerait.
    etapes_migrations = (
        f"GRANT CONNECT, CREATE ON DATABASE {identifiant(base)} TO {identifiant(migrations)}",
        f"GRANT USAGE, CREATE ON SCHEMA public TO {identifiant(migrations)}",
    )
    for requete in etapes_migrations:
        code, sortie = psql(compose, env, requete)
        if code:
            print(f"    ECHEC    {requete[:60]}… : {sortie[:160]}")
            return 1
    print(f"    ok       {migrations} : CONNECT et CREATE sur la base et sur le schema")

    #  ------------------------------------------------------------------
    #  3. Le transfert de PROPRIETE — explicite et FILTRE
    #  ------------------------------------------------------------------
    #  Les tables et fonctions existantes appartiennent au SUPERUTILISATEUR :
    #  c'est lui qui les a creees avant le LOT 3. Un role qui ne possede pas une
    #  table ne peut ni l'ALTER ni la DROP, donc la migration suivante echouerait.
    #
    #  `REASSIGN OWNED BY` ETAIT LA PREMIERE VERSION, ET ELLE A ECHOUE :
    #  « cannot reassign ownership of objects owned by role X because they are
    #  required by the database system ». Diagnostic avant correction, et la
    #  mesure du 20/08/2026 a donne la cause en deux nombres :
    #
    #    196 fonctions dans `public`, dont **188 appartiennent a `btree_gist`**
    #    et **8 seulement sont les notres**.
    #
    #  Une extension n'a PAS d'`ALTER ... OWNER TO` : ses fonctions sont des
    #  membres, et leur propriete suit celle de l'extension. `REASSIGN OWNED`
    #  butait donc sur elles, et sur la propriete de la BASE elle-meme.
    #
    #  Le transfert est donc explicite, filtre sur `pg_depend.deptype = 'e'`, et
    #  il COMPTE ce qu'il a transfere. Residuel nomme : l'extension et la base
    #  restent au superutilisateur, ce qui est sans consequence -- le role de
    #  migration a `CREATE ON DATABASE` explicitement, ce qui suffit a
    #  `CREATE EXTENSION IF NOT EXISTS`.
    #  S608 est neutralise sur l'affectation ci-dessous : les trois
    #  interpolations passent par `citer()`, les deux noms de role ont ete valides
    #  contre `^[a-z][a-z0-9_]*$` en amont, et le `format()` interne emploie `%I`,
    #  l'echappement d'identifiant de PostgreSQL.
    #
    #  DEUX PIEGES RENCONTRES EN ECRIVANT CETTE ANNOTATION, ET LES DEUX SONT LE
    #  §7.25 : une directive placee apres l'ouverture d'une chaine multiligne se
    #  retrouve DANS le SQL, qui devient invalide -- mesure : echec de syntaxe au
    #  transfert. Et une directive CITEE dans un commentaire est lue comme une
    #  directive : l'expliquer en la nommant produisait un avertissement de
    #  l'outil lui-meme. Elle n'est donc pas citee ici.
    transfert: str = f"""
    DO $$
    DECLARE
        objet record;
        tables_transferees integer := 0;
        fonctions_transferees integer := 0;
    BEGIN
        FOR objet IN
            SELECT c.oid::regclass AS nom
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
              AND pg_get_userbyid(c.relowner) = {citer(superutilisateur)}
        LOOP
            EXECUTE format('ALTER TABLE %s OWNER TO %I', objet.nom, {citer(migrations)});
            tables_transferees := tables_transferees + 1;
        END LOOP;

        FOR objet IN
            SELECT p.oid::regprocedure AS nom
            FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND pg_get_userbyid(p.proowner) = {citer(superutilisateur)}
              AND NOT EXISTS (
                  SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e'
              )
        LOOP
            EXECUTE format('ALTER FUNCTION %s OWNER TO %I', objet.nom, {citer(migrations)});
            fonctions_transferees := fonctions_transferees + 1;
        END LOOP;

        RAISE NOTICE 'tables=% fonctions=%', tables_transferees, fonctions_transferees;
    END $$;
    """  # noqa: S608
    code, sortie = psql(compose, env, transfert)
    if code:
        print(f"    ECHEC    transfert de propriete : {sortie[:220]}")
        return 1
    detail = next(
        (ligne for ligne in sortie.splitlines() if "tables=" in ligne), "(compte non rapporte)"
    )
    print(
        f"    ok       propriete transferee a {migrations} — {detail.split('NOTICE:')[-1].strip()}"
    )

    #  ------------------------------------------------------------------
    #  4. Les droits du role d'EXECUTION
    #  ------------------------------------------------------------------
    etapes_execution = (
        f"GRANT CONNECT ON DATABASE {identifiant(base)} TO {identifiant(execution)}",
        f"GRANT USAGE ON SCHEMA public TO {identifiant(execution)}",
        f"GRANT {DROITS_DML} ON ALL TABLES IN SCHEMA public TO {identifiant(execution)}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {identifiant(execution)}",
    )
    for requete in etapes_execution:
        code, sortie = psql(compose, env, requete)
        if code:
            print(f"    ECHEC    {requete[:60]}… : {sortie[:160]}")
            return 1
    print(f"    ok       {execution} : CONNECT, USAGE, et {DROITS_DML} sur les tables existantes")

    #  ------------------------------------------------------------------
    #  5. Les privileges PAR DEFAUT — pour les tables qui n'existent pas encore
    #  ------------------------------------------------------------------
    defauts = (
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {identifiant(migrations)} IN SCHEMA public "
        f"GRANT {DROITS_DML} ON TABLES TO {identifiant(execution)}",
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {identifiant(migrations)} IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {identifiant(execution)}",
    )
    for requete in defauts:
        code, sortie = psql(compose, env, requete)
        if code:
            print(f"    ECHEC    ALTER DEFAULT PRIVILEGES : {sortie[:160]}")
            return 1
    print(f"    ok       privileges PAR DEFAUT : toute table creee par {migrations} sera lisible")

    #  ------------------------------------------------------------------
    #  6. CE QUE LE SCRIPT A REELLEMENT PRODUIT — mesure, non supposition
    #  ------------------------------------------------------------------
    print()
    mesures = (
        (
            "proprietaire de la base",
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()",
        ),
        (
            "proprietaires des tables",
            "SELECT tableowner || ' (' || count(*) || ')' FROM pg_tables "
            "WHERE schemaname='public' GROUP BY tableowner",
        ),
        (
            "proprietaires des fonctions",
            #  `GROUP BY 1` porte sur la colonne de SORTIE, qui contient
            #  `count(*)` : PostgreSQL le refuse. On groupe sur l'EXPRESSION.
            #  Et les membres d'extension sont distingues : 188 des 196
            #  fonctions appartiennent a `btree_gist`, et leur propriete ne
            #  peut pas changer independamment.
            "SELECT pg_get_userbyid(p.proowner) || ' (' || count(*) || ')' || "
            "CASE WHEN bool_and(d.objid IS NOT NULL) THEN ' [extension]' ELSE '' END "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "LEFT JOIN pg_depend d ON d.objid = p.oid AND d.deptype = 'e' "
            "WHERE n.nspname = 'public' "
            "GROUP BY pg_get_userbyid(p.proowner), (d.objid IS NOT NULL)",
        ),
        (
            "roles pouvant se connecter",
            "SELECT string_agg(rolname || CASE WHEN rolsuper THEN ' [SUPER]' ELSE '' END, "
            "', ' ORDER BY rolname) FROM pg_roles "
            "WHERE rolcanlogin AND rolname NOT LIKE 'pg\\_%'",
        ),
    )
    for libelle, requete in mesures:
        code, sortie = psql(compose, env, requete)
        valeur = sortie.replace("\n", " · ") if code == 0 else f"illisible : {sortie[:80]}"
        print(f"    info     {libelle:28} : {valeur}")

    print()
    print(
        f"  --> {migrations} possede le schema et peut le modifier ; "
        f"{execution} ne peut que lire et ecrire des lignes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
