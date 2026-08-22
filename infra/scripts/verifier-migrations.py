#!/usr/bin/env python3
"""Prouver qu'une base VIDE se construit uniquement par migrations, et qu'elles se rejouent.

LOT 2, sous-etape `T12`, story `MVP-L02-US008`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE

  Le critere de `US008` : « une base vide est construite **uniquement** par
  migrations ; les migrations sont testees sur PostgreSQL **reel** ».

  **Chaque sous-etape a eprouve SA migration a la main** -- montee, descente,
  remontee. Aucun controle n'eprouvait la CHAINE ENTIERE sur une base neuve, et
  aucun ne comparait le schema obtenu a celui qui tourne. Onze migrations posees
  une par une dans onze sous-etapes, c'est exactement la situation ou l'on croit
  avoir tout fait -- meme raisonnement que `verifier-historisation.py`.

CE QU'IL FAIT, ET DANS QUEL ORDRE

  1. il cree une base JETABLE, vide ;
  2. il y applique `alembic upgrade head` ;
  3. il COMPARE le schema obtenu a celui de la base courante -- tables, colonnes,
     contraintes, index, declencheurs. **C'est la comparaison qui prouve le
     critere** : sans elle, on saurait que la chaine s'applique, pas qu'elle
     produit le bon schema ;
  4. il redescend a `base` et exige qu'il ne reste AUCUNE table metier ;
  5. il remonte a `head` et exige le MEME schema qu'a l'etape 3 ;
  6. il supprime la base jetable, meme en cas d'echec.

  L'etape 4 est celle qui trouve les `downgrade()` fautifs : `T5` en avait un qui
  renommait avant de supprimer, donc collisionnait.

ET UN CONTROLE QUE LA FICHE EXIGE EXPLICITEMENT

  « Aucune dependance a SQLite n'existe pour les tests d'integration » est un
  critere de sortie du lot, pas une preference : un index partiel, une contrainte
  d'exclusion et une cle etrangere composite **n'existent pas** en SQLite, donc un
  test qui passerait dessus ne prouverait rien. La fiche ajoute : « et un controle
  devra le verifier, plutot que de compter sur la vigilance ».
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
BASE_JETABLE = "onboarding_migrations_temoin"

#  Les fichiers ou une dependance SQLite se glisserait. `pyproject.toml` pour une
#  dependance declaree, les sources pour un import ou une URL.
RACINES_A_BALAYER = ("apps", "packages", "infra", "pyproject.toml", "Makefile")

#  LE MOTIF CHERCHE UN USAGE, PAS LE MOT — et c'est un correctif. Ma premiere
#  version cherchait `sqlite` sans distinction, et a trouve **16 occurrences,
#  toutes de la PROSE affirmant son exclusion** : « execution sur PostgreSQL reel,
#  jamais SQLite ». Le controle echouait donc sur un depot exemplaire, et il
#  aurait appris a passer outre — c'est le §7.25 de la passation, ecrit le jour
#  meme, rejoue dans le contrôle suivant.
#
#  Les trois formes qui constituent un usage reel :
#    - un import du module ;
#    - une URL de connexion ;
#    - une dependance declaree dans `pyproject.toml` ou un lock.
MOTIFS_D_USAGE_SQLITE = (
    re.compile(r"^\s*(?:import|from)\s+(?:a?)sqlite3?\b", re.MULTILINE),
    re.compile(r"sqlite(?:\+\w+)?://"),
    re.compile(r'^\s*["\x27]?(?:a?)sqlite\w*["\x27]?\s*(?:=|>=|==)', re.MULTILINE),
)


def executer(commande: list[str]) -> tuple[int, str]:
    """Lancer une commande, arguments passes TELS QUELS — motif du §7.2."""
    # S603 : aucune entree de tiers, et `shell=False` empeche toute redecoupe.
    execution = subprocess.run(  # noqa: S603
        commande,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
        cwd=RACINE,
    )
    return execution.returncode, (execution.stdout + execution.stderr).strip()


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], base: str, requete: str) -> tuple[int, str]:
    return executer(
        [
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            env["POSTGRES_USER"],
            "-d",
            base,
            "-tAF|",
            "-c",
            requete,
        ]
    )


def alembic(compose: list[str], base: str, *arguments: str) -> tuple[int, str]:
    return executer(
        [
            *compose,
            "exec",
            "-T",
            "-e",
            f"POSTGRES_DB={base}",
            "--workdir",
            "/app/apps/api",
            "api",
            "alembic",
            *arguments,
        ]
    )


#  La signature d'un schema : ce qui doit etre IDENTIQUE de part et d'autre.
#  Les noms d'index, de contraintes et de declencheurs y sont, parce que c'est
#  precisement ce qu'un `downgrade()` fautif ou une migration oubliee ferait
#  diverger.
REQUETES_DE_SIGNATURE: dict[str, str] = {
    "colonnes": (
        "SELECT table_name || '.' || column_name || ':' || data_type || ':' || is_nullable "
        "FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name <> 'alembic_version' ORDER BY 1"
    ),
    "contraintes": (
        "SELECT conrelid::regclass::text || ':' || conname || ':' || contype::text "
        "FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
        "WHERE n.nspname='public' ORDER BY 1"
    ),
    "index": (
        "SELECT tablename || ':' || indexname FROM pg_indexes "
        "WHERE schemaname='public' AND tablename <> 'alembic_version' ORDER BY 1"
    ),
    "declencheurs": (
        "SELECT tgrelid::regclass::text || ':' || tgname FROM pg_trigger "
        "WHERE NOT tgisinternal ORDER BY 1"
    ),
    "fonctions": (
        "SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname='public' ORDER BY 1"
    ),
}


def signature(compose: list[str], env: dict[str, str], base: str) -> dict[str, list[str]]:
    resultat: dict[str, list[str]] = {}
    for nom, requete in REQUETES_DE_SIGNATURE.items():
        code, sortie = psql(compose, env, base, requete)
        if code:
            message = f"lecture de la signature « {nom} » impossible sur {base} : {sortie[:200]}"
            raise SystemExit(message)
        resultat[nom] = [ligne for ligne in sortie.splitlines() if ligne.strip()]
    return resultat


def verifier_absence_de_sqlite() -> tuple[int, int]:
    """Rendre (occurrences, fichiers examines). La fiche exige ce controle."""
    occurrences = 0
    examines = 0
    for racine in RACINES_A_BALAYER:
        chemin = RACINE / racine
        fichiers = [chemin] if chemin.is_file() else sorted(chemin.rglob("*"))
        for fichier in fichiers:
            if not fichier.is_file() or fichier.suffix not in (
                ".py",
                ".toml",
                ".yml",
                ".yaml",
                ".json",
                ".cfg",
                ".ini",
                "",
            ):
                continue
            if any(part in {".venv", "node_modules", "__pycache__"} for part in fichier.parts):
                continue
            try:
                texte = fichier.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            examines += 1
            for motif in MOTIFS_D_USAGE_SQLITE:
                trouve = motif.findall(texte)
                if trouve:
                    print(
                        f"    ECHEC    {fichier.relative_to(RACINE)} : "
                        f"{len(trouve)} usage(s) reel(s) de SQLite"
                    )
                    occurrences += len(trouve)
    return occurrences, examines


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

    echecs = 0
    print()
    print("  Migrations : une base VIDE, construite uniquement par migrations")

    # ------------------------------------------------------------------
    #  0. Aucune dependance SQLite — critere de sortie du lot
    # ------------------------------------------------------------------
    occurrences, examines = verifier_absence_de_sqlite()
    if occurrences:
        print(f"    ECHEC    {occurrences} occurrence(s) de « sqlite » dans {examines} fichiers")
        print("             Un index partiel, une exclusion et une cle composite N'EXISTENT")
        print("             PAS en SQLite : un test qui passerait dessus ne prouverait rien.")
        echecs += 1
    else:
        print(f"    ok       aucune trace de SQLite, {examines} fichiers examines")

    # ------------------------------------------------------------------
    #  1. La base jetable
    # ------------------------------------------------------------------
    psql(compose, env, env["POSTGRES_DB"], f'DROP DATABASE IF EXISTS "{BASE_JETABLE}"')
    #  PROPRIETAIRE : le role de migration — meme motif que dans
    #  `test_integration.py`. Alembic se connecte avec ce role depuis le LOT 3.
    code, sortie = psql(
        compose,
        env,
        env["POSTGRES_DB"],
        f'CREATE DATABASE "{BASE_JETABLE}" OWNER "{env["POSTGRES_MIGRATIONS_USER"]}"',
    )
    if code:
        print(f"    ECHEC    creation de la base jetable impossible : {sortie[:200]}")
        return 1
    print(f"    ok       base jetable « {BASE_JETABLE} » creee, VIDE")

    try:
        code, sortie = psql(
            compose,
            env,
            BASE_JETABLE,
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'",
        )
        depart = sortie.strip()
        if depart != "0":
            print(f"    ECHEC    la base jetable porte deja {depart} table(s)")
            echecs += 1
        else:
            print("    ok       0 table au depart — le point de comparaison est propre")

        # --------------------------------------------------------------
        #  2. La montee
        # --------------------------------------------------------------
        code, sortie = alembic(compose, BASE_JETABLE, "upgrade", "head")
        if code:
            print(f"    ECHEC    `alembic upgrade head` en code {code}")
            print("             " + (sortie.splitlines()[-1][:180] if sortie else ""))
            return 1

        #  LE COMPTE EST LU EN BASE, NON DANS LE JOURNAL. Ma premiere version
        #  comptait les lignes « Running upgrade » de la sortie — or `alembic`
        #  n'en produit AUCUNE dans ce conteneur, si bien que le controle
        #  annoncait « 0 revision appliquee » alors que **19 tables venaient
        #  d'etre creees**. Je comparais un nombre de lignes de journal a un
        #  nombre de revisions : sixieme proposition du §7.0.
        fichiers_de_revision = sorted(
            (RACINE / "apps" / "api" / "alembic" / "versions").glob("0*.py")
        )
        _, tete_neuve = psql(compose, env, BASE_JETABLE, "SELECT version_num FROM alembic_version")
        _, tete_courante = psql(
            compose, env, env["POSTGRES_DB"], "SELECT version_num FROM alembic_version"
        )
        print(
            f"    info     {len(fichiers_de_revision)} fichier(s) de revision sur disque, "
            f"tete appliquee « {tete_neuve.strip()} »"
        )
        if len(fichiers_de_revision) < 2:
            print(f"    ECHEC    {len(fichiers_de_revision)} revision(s) : chaine trop courte")
            echecs += 1
        if tete_neuve.strip() != tete_courante.strip():
            print(
                f"    ECHEC    la base jetable est en « {tete_neuve.strip()} », "
                f"la courante en « {tete_courante.strip()} »"
            )
            echecs += 1
        else:
            print(f"    ok       meme tete de migration des deux cotes : {tete_neuve.strip()}")

        # --------------------------------------------------------------
        #  3. LA COMPARAISON — c'est elle qui prouve le critere
        # --------------------------------------------------------------
        neuve = signature(compose, env, BASE_JETABLE)
        courante = signature(compose, env, env["POSTGRES_DB"])
        for nom in REQUETES_DE_SIGNATURE:
            manquants = sorted(set(courante[nom]) - set(neuve[nom]))
            en_trop = sorted(set(neuve[nom]) - set(courante[nom]))
            if manquants or en_trop:
                print(f"    ECHEC    {nom} : {len(manquants)} manquant(s), {len(en_trop)} en trop")
                for element in (manquants + en_trop)[:6]:
                    print(f"               {element}")
                echecs += 1
            else:
                print(
                    f"    ok       {nom} : {len(neuve[nom])} elements IDENTIQUES de part et d'autre"
                )

        #  UN CONTROLE MUET DIRAIT « 0 element, tout est identique ».
        if len(neuve["colonnes"]) < 100:
            print(f"    ECHEC    {len(neuve['colonnes'])} colonnes : la lecture a echoue")
            echecs += 1

        # --------------------------------------------------------------
        #  4. La descente complete
        # --------------------------------------------------------------
        code, sortie = alembic(compose, BASE_JETABLE, "downgrade", "base")
        if code:
            print(f"    ECHEC    `alembic downgrade base` en code {code}")
            print("             " + (sortie.splitlines()[-1][:180] if sortie else ""))
            echecs += 1
        else:
            code, restantes = psql(
                compose,
                env,
                BASE_JETABLE,
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' "
                "AND table_name <> 'alembic_version'",
            )
            if restantes.strip() != "0":
                print(f"    ECHEC    {restantes.strip()} table(s) metier survivent a la descente")
                echecs += 1
            else:
                print("    ok       `alembic downgrade base` ne laisse AUCUNE table metier")

        # --------------------------------------------------------------
        #  5. La remontee — le meme schema, ou rien n'est prouve
        # --------------------------------------------------------------
        code, sortie = alembic(compose, BASE_JETABLE, "upgrade", "head")
        if code:
            print(f"    ECHEC    remontee en code {code}")
            echecs += 1
        else:
            rejouee = signature(compose, env, BASE_JETABLE)
            divergences = [nom for nom in REQUETES_DE_SIGNATURE if rejouee[nom] != neuve[nom]]
            if divergences:
                print(f"    ECHEC    la remontee diverge sur : {divergences}")
                echecs += 1
            else:
                print("    ok       la remontee rend une signature IDENTIQUE — la chaine se rejoue")
    finally:
        psql(compose, env, env["POSTGRES_DB"], f'DROP DATABASE IF EXISTS "{BASE_JETABLE}"')
        print(f"    info     base jetable « {BASE_JETABLE} » supprimee")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print(
        "  --> une base vide se construit uniquement par migrations, la chaine se rejoue, "
        "et le schema obtenu est IDENTIQUE a celui qui tourne"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
