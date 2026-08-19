#!/usr/bin/env python3
"""Verifier l'historisation des SEPT relations du modele §25.2.

LOT 2, sous-etape `T9`, story `MVP-L02-US004`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE

  La fiche du LOT 2 assigne a `T9` trois preuves : « les 7 relations sont
  COMPTEES », « tout chevauchement est rejete par la BASE, pas seulement par le
  service », et « toute modification cloture la periode precedente ».

  Les sous-etapes `T4` a `T8` ont pose une contrainte d'exclusion par relation, et
  chacune a son test. **Mais aucun controle ne disait combien de relations avaient
  ete couvertes.** Sept contraintes posees une par une dans cinq sous-etapes
  differentes, c'est exactement la situation ou l'on croit avoir tout fait.

  C'est la troisieme proposition du §7.0 de la passation : « un controle qui
  n'annonce pas combien d'elements il a examines peut toujours n'en avoir examine
  qu'un ». La parade est de COMPTER et de confronter le compte a un attendu.

LA LISTE DES SEPT EST DERIVEE DU MODELE, JAMAIS RECOPIEE

  Le §25.2 enumere ses relations dans une liste a puces. Ce script la LIT dans
  `MODELE_DONNEES_EXALT.md` et en tire le compte attendu. Recopier « 7 » ici
  serait un `ECART-021` en puissance -- un nombre affirme sans etre derive de sa
  source.

  Le rattachement d'un libelle de relation a une TABLE est, lui, une
  interpretation : elle est declaree ci-dessous, et le controle exige que **chaque
  libelle du modele soit rattache**. Un libelle nouveau ferait donc echouer le
  controle au lieu d'etre ignore.

ET UN SECOND CONTROLE, NE D'UN DEFAUT DE `T8`

  Une cle de contrainte d'exclusion qui contient une colonne NULLABLE ne contraint
  RIEN sur les lignes ou cette colonne est nulle : l'operateur `=` ne rapproche
  jamais deux NULL. En `T8`, une exclusion incluant `circle_id` -- nul pour un
  `DSM` -- existait sans rien garantir sur trois types sur quatre.

  Le controle exige donc que toute colonne nullable figurant dans une cle
  d'exclusion soit exclue par la clause `WHERE` de cette exclusion. C'est
  verifiable mecaniquement, et cela vaut mieux qu'une promesse d'attention.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
MODELE = RACINE / "docs" / "architecture" / "MODELE_DONNEES_EXALT.md"

#  Rattachement d'un libelle du §25.2 a la table qui le porte. C'est une
#  INTERPRETATION, declaree ici et non deduite : « cercle principal » ne nomme pas
#  `circle_membership`, et « responsabilites Framework » ne nomme pas
#  `framework_responsibility_assignment`. Le controle exige que chaque libelle du
#  modele apparaisse dans cette table de correspondance.
RELATIONS_ATTENDUES: dict[str, str] = {
    "appartenance à une entité": "entity_membership",
    "métier": "membership_job_assignment",
    "statut professionnel": "professional_status_assignment",
    "DSM": "dsm_assignment",
    "cercle principal": "circle_membership",
    "responsabilités Framework": "framework_responsibility_assignment",
    "rôles techniques": "technical_role_assignment",
}


def libelles_du_modele() -> list[str]:
    """Les libelles de relation enumeres par le §25.2, lus dans le modele."""
    texte = MODELE.read_text(encoding="utf-8")
    debut = texte.index("## 25.2 Contraintes temporelles")
    fin = texte.index("## 25.3", debut)
    section = texte[debut:fin]
    apres = section.index("Relations concernées :")
    return [
        ligne.strip().lstrip("- ").rstrip(" ;.")
        for ligne in section[apres:].splitlines()
        if ligne.strip().startswith("- ")
    ]


def sql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Executer une requete SQL dans le conteneur de base."""
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # le motif du §7.2 -- aucun redecoupage des arguments n'a lieu.
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
            "-tAF|",
            "-c",
            requete,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return execution.returncode, (execution.stdout or execution.stderr).strip()


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


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

    # ------------------------------------------------------------------
    #  1. Le compte attendu, DERIVE du modele
    # ------------------------------------------------------------------
    print()
    print("  Historisation des relations du modele §25.2")
    libelles = libelles_du_modele()
    print(f"    info     {len(libelles)} relation(s) enumeree(s) par le §25.2, lues dans le modele")
    for libelle in libelles:
        print(f"               - {libelle}")

    non_rattaches = [libelle for libelle in libelles if libelle not in RELATIONS_ATTENDUES]
    if non_rattaches:
        for libelle in non_rattaches:
            print(f"    ECHEC    libelle du modele non rattache a une table : {libelle!r}")
        print("             Ajouter le rattachement dans RELATIONS_ATTENDUES, ou dire")
        print("             explicitement pourquoi cette relation n'est pas historisee.")
        echecs += 1
    else:
        print(f"    ok       les {len(libelles)} libelles sont tous rattaches a une table")

    surnumeraires = [libelle for libelle in RELATIONS_ATTENDUES if libelle not in libelles]
    if surnumeraires:
        for libelle in surnumeraires:
            print(f"    ECHEC    rattachement sans libelle correspondant au §25.2 : {libelle!r}")
        echecs += 1

    # ------------------------------------------------------------------
    #  2. Chaque relation porte-t-elle une exclusion EN BASE ?
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
        "FROM pg_constraint WHERE contype = 'x' ORDER BY 1, 2;",
    )
    if code != 0:
        print(f"    INDETERMINE  la base n'a pas repondu -- {sortie[:160]}")
        print("                 Ce n'est pas « tout va bien » : lancer `make up`, puis rejouer.")
        return 1

    exclusions: dict[str, list[tuple[str, str]]] = {}
    for ligne in sortie.splitlines():
        morceaux = ligne.split("|", 2)
        if len(morceaux) == 3:
            exclusions.setdefault(morceaux[0], []).append((morceaux[1], morceaux[2]))

    print()
    print(
        f"    info     {sum(len(v) for v in exclusions.values())} contrainte(s) d'exclusion "
        f"en base, sur {len(exclusions)} table(s)"
    )

    couvertes = 0
    for libelle, table in RELATIONS_ATTENDUES.items():
        posees = exclusions.get(table, [])
        if not posees:
            print(f"    ECHEC    {libelle} ({table}) : AUCUNE contrainte d'exclusion")
            echecs += 1
            continue
        couvertes += 1
        detail = ", ".join(nom for nom, _ in posees)
        print(f"    ok       {libelle:34} -> {len(posees)} exclusion(s) : {detail}")

    if couvertes == len(RELATIONS_ATTENDUES):
        print(f"    ok       les {couvertes} relations du §25.2 sont couvertes EN BASE")
    else:
        print(f"    ECHEC    {couvertes} relation(s) couverte(s) sur {len(RELATIONS_ATTENDUES)}")
        echecs += 1

    # ------------------------------------------------------------------
    #  3. Aucune colonne NULLABLE dans une cle d'exclusion sans clause `WHERE`
    #     qui l'exclue — defaut `T8-1`
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT c.conrelid::regclass::text, c.conname, a.attname, "
        "pg_get_constraintdef(c.oid) "
        "FROM pg_constraint c "
        "JOIN unnest(c.conkey) AS k(attnum) ON true "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum "
        "WHERE c.contype = 'x' AND NOT a.attnotnull ORDER BY 1, 2, 3;",
    )
    if code != 0:
        print(f"    INDETERMINE  requete des colonnes nullables en echec -- {sortie[:120]}")
        return 1

    print()
    print("    Colonnes NULLABLES dans une cle d'exclusion (defaut `T8-1`)")
    nullables = [ligne.split("|", 3) for ligne in sortie.splitlines() if ligne.strip()]
    if not nullables:
        print("    ok       aucune colonne nullable dans aucune cle d'exclusion")
    else:
        for table, contrainte, colonne, definition in nullables:
            #  EXIGENCE EXACTE, ET NON HEURISTIQUE. La clause `WHERE` de
            #  l'exclusion doit contenir explicitement `<colonne> IS NOT NULL`.
            #
            #  Ma premiere version tolerait toute clause mentionnant
            #  `responsibility_type`, au motif que la contrainte
            #  `portee_selon_le_type` garantissait la non-nullite. **C'etait une
            #  heuristique dans un controle**, et elle aurait accepte n'importe
            #  quelle exclusion restreinte par ce type, meme sans garantie.
            #
            #  Et le fond est meilleur ainsi : une contrainte dont la justesse
            #  depend d'une AUTRE contrainte est fragile. La rendre autoportante
            #  coute une redondance, et se verifie mecaniquement.
            motif_where = re.search(r"WHERE \((.*)\)\s*$", definition)
            clause = motif_where.group(1) if motif_where else ""
            protegee = f"{colonne} IS NOT NULL" in clause
            if protegee:
                print(
                    f"    ok       {table}.{colonne} dans {contrainte} : "
                    f"protegee par la clause WHERE"
                )
            else:
                print(
                    f"    ECHEC    {table}.{colonne} dans {contrainte} : NULLABLE et "
                    f"non exclue par un `IS NOT NULL` explicite"
                )
                print("             Une cle d'exclusion contenant une colonne nullable ne")
                print("             contraint RIEN sur les lignes ou elle est nulle : `=` ne")
                print("             rapproche jamais deux NULL. Defaut `T8-1`.")
                echecs += 1

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print(
        f"  --> les {len(libelles)} relations du §25.2 sont historisees en base, "
        f"et aucune cle d'exclusion ne repose sur une colonne nullable non exclue"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
