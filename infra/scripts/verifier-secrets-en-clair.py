#!/usr/bin/env python3
"""Aucun mot de passe ni jeton en clair dans une colonne — modele §10.2 et §10.3.

LOT 3, sous-etape `T2`.

CE QUE CE CONTROLE PROUVE

  Le §10.2 pose « aucun mot de passe brut ni historique reversible », et le §10.3
  « `token_hash` | **hash uniquement** ». La fiche du LOT 3 en fait un critere de
  `T2` : « aucun mot de passe ni jeton en clair dans une colonne, verifie par
  controle ».

  Le controle examine le CATALOGUE PostgreSQL, pas de la prose. Toute colonne dont
  le nom evoque un secret -- mot de passe, jeton, secret, empreinte de session --
  doit **se terminer par `_hash`**, ou figurer dans la liste des exceptions
  DECLAREES ci-dessous avec son motif.

POURQUOI UN CONTROLE SUR LES NOMS EST ICI EXACT, ET NON HEURISTIQUE

  La lecon `T12-2` du LOT 2 dit qu'un controle doit chercher un USAGE, pas un mot :
  le motif `sqlite` avait trouve seize occurrences de prose affirmant son
  exclusion. Ici, la source n'est pas de la prose mais le **catalogue** : un nom de
  colonne n'est pas un commentaire, c'est la declaration elle-meme. Une colonne
  nommee `password` **est** le defaut, pas une mention du defaut.

  Et le controle ne se contente pas du nom : il verifie aussi la LONGUEUR declaree
  des colonnes d'empreinte. Une empreinte SHA-256 en hexadecimal fait exactement
  64 caracteres ; une colonne `text` sans borne accueillerait n'importe quoi.

CE QU'IL NE PROUVE PAS, ET C'EST DIT

  Il n'inspecte AUCUNE donnee. Une colonne correctement nommee `token_hash` et
  correctement bornee pourrait recevoir une valeur en clair de 64 caracteres : ce
  serait un defaut de CODE, que `T4` devra couvrir par un test sur le service
  d'emission. Ce controle ferme la porte du SCHEMA, pas celle du code.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

#  Ce qu'un nom de colonne evoquant un secret contient.
MOTIF_SECRET = re.compile(r"password|token|secret|credential|passphrase", re.IGNORECASE)

#  Longueur exacte d'une empreinte SHA-256 en hexadecimal.
LONGUEUR_SHA256_HEXA = 64

#  EXCEPTIONS DECLAREES, avec leur motif. Une colonne qui evoque un secret sans
#  en porter un doit etre nommee ici, jamais toleree en silence.
#  DEUX FAMILLES D'EMPREINTES, ET LES CONFONDRE REND LE CONTROLE FAUX.
#
#  Une empreinte de JETON est un SHA-256 en hexadecimal : exactement 64
#  caracteres, et la borne est verifiable. Une empreinte de MOT DE PASSE ne l'est
#  pas : argon2 et bcrypt produisent une chaine de longueur VARIABLE qui embarque
#  son sel et ses parametres. Exiger 64 caracteres la rendrait impossible a
#  stocker -- le controle echouerait sur un livrable correct, §7.20.
#
#  Ce qui rend une empreinte de mot de passe verifiable, c'est ce que le §10.2
#  exige : les colonnes `algorithm` et `parameters` a cote d'elle. Sans elles,
#  aucune verification ne serait possible apres un changement d'algorithme. Le
#  controle exige donc leur PRESENCE, ce qui vaut mieux qu'une borne de longueur.
EMPREINTES_DE_MOT_DE_PASSE: dict[tuple[str, str], tuple[str, ...]] = {
    ("admin_password_credential", "password_hash"): ("algorithm", "parameters"),
}

EXCEPTIONS: dict[tuple[str, str], str] = {
    #  §8.1 : « `color_token` | Reference de couleur locale ». C'est un jeton de
    #  DESIGN, pas un secret : le motif se declenche sur le mot « token ». Faux
    #  positif nomme plutot que tolere -- §7.25.
    ("circle", "color_token"): "reference de couleur du design system, §8.1",
    #  `service_token` est le nom d'une TABLE, pas d'un secret : sa colonne
    #  d'identifiant technique le reprend.
    ("service_token", "id"): "identifiant technique de la table, pas un secret",
    ("service_token", "service_account_id"): "cle etrangere, pas un secret",
    #  Les colonnes d'auteur des champs communs §3.1, sur les tables dont le nom
    #  contient « credential » ou « token ».
    ("admin_password_credential", "id"): "identifiant technique",
    ("admin_password_credential", "user_account_id"): "cle etrangere",
    ("admin_password_credential", "algorithm"): "nom de l'algorithme, exige par le §10.2",
    ("admin_password_credential", "parameters"): "parametres de l'algorithme, exiges par le §10.2",
    ("admin_password_credential", "changed_at"): "horodatage",
    ("admin_password_credential", "must_change"): "drapeau, exige par le §10.2",
    ("admin_password_credential", "revoked_at"): "horodatage",
    ("service_token", "expires_at"): "horodatage",
    ("service_token", "revoked_at"): "horodatage",
    ("service_token", "scopes"): "liste de portees, exigee par le §10.5",
    ("service_token", "last_used_at"): "horodatage",
}


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    # S603 : entree du Makefile, jamais d'un tiers, et `shell=False` — §7.2.
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
    return execution.returncode, (execution.stdout + execution.stderr).strip()


REQUETE_COLONNES = (
    "SELECT table_name, column_name, data_type, "
    "coalesce(character_maximum_length::text, '-') "
    "FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name <> 'alembic_version' "
    "ORDER BY table_name, column_name"
)


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

    code, sortie = psql(compose, env, REQUETE_COLONNES)
    if code:
        print(f"    ECHEC    base injoignable : {sortie[:200]}")
        return 1
    colonnes = [ligne.split("|") for ligne in sortie.splitlines() if ligne.strip()]

    echecs = 0
    print()
    print("  Aucun secret en clair dans une colonne — modele §10.2 et §10.3")
    print(f"    info     {len(colonnes)} colonnes examinees dans le schema `public`")

    #  UN CONTROLE MUET DIRAIT « 0 colonne suspecte, tout va bien ».
    if len(colonnes) < 50:
        print(f"    ECHEC    {len(colonnes)} colonnes lues : la base semble vide")
        return 1

    suspectes = [
        (table, colonne, type_sql, longueur)
        for table, colonne, type_sql, longueur in colonnes
        if MOTIF_SECRET.search(colonne)
    ]
    print(f"    info     {len(suspectes)} colonne(s) dont le nom evoque un secret")

    empreintes_bornees = 0
    empreintes_de_mot_de_passe = 0
    noms_par_table: dict[str, set[str]] = {}
    for table, colonne, _type, _longueur in colonnes:
        noms_par_table.setdefault(table, set()).add(colonne)

    for table, colonne, type_sql, longueur in suspectes:
        if (table, colonne) in EXCEPTIONS:
            print(f"    ok       {table}.{colonne} — {EXCEPTIONS[(table, colonne)]}")
            continue
        #  Une empreinte de MOT DE PASSE : sa longueur est variable, ce sont ses
        #  colonnes d'accompagnement qui la rendent exploitable.
        if (table, colonne) in EMPREINTES_DE_MOT_DE_PASSE:
            requises = EMPREINTES_DE_MOT_DE_PASSE[(table, colonne)]
            manquantes = sorted(set(requises) - noms_par_table.get(table, set()))
            if manquantes:
                print(
                    f"    ECHEC    {table}.{colonne} : colonne(s) d'accompagnement "
                    f"absente(s) {manquantes} — le §10.2 les exige"
                )
                echecs += 1
            else:
                empreintes_de_mot_de_passe += 1
                print(
                    f"    ok       {table}.{colonne} — empreinte de mot de passe, "
                    f"accompagnee de {', '.join(requises)} (§10.2)"
                )
            continue
        if not colonne.endswith("_hash"):
            print(f"    ECHEC    {table}.{colonne} evoque un secret et ne finit pas par `_hash`")
            print("             Le §10.2 interdit tout mot de passe brut, le §10.3 exige")
            print("             « hash uniquement ». Renommer, ou declarer l'exception avec")
            print("             son motif dans `EXCEPTIONS`.")
            echecs += 1
            continue
        empreintes_bornees += 1
        #  Une empreinte SHA-256 en hexadecimal fait EXACTEMENT 64 caracteres.
        #  Une colonne `text` sans borne accueillerait n'importe quoi.
        if longueur != str(LONGUEUR_SHA256_HEXA):
            print(
                f"    ECHEC    {table}.{colonne} est `{type_sql}` de longueur {longueur}, "
                f"attendu {LONGUEUR_SHA256_HEXA}"
            )
            echecs += 1
        else:
            print(f"    ok       {table}.{colonne} — empreinte bornee a {longueur} caracteres")

    #  Les exceptions declarees doivent toutes correspondre a une colonne REELLE :
    #  une exception devenue fausse tolererait un jour une colonne homonyme.
    reelles = {(table, colonne) for table, colonne, _t, _l in colonnes}
    for cle in sorted(EXCEPTIONS):
        if cle not in reelles:
            print(f"    ECHEC    l'exception {cle[0]}.{cle[1]} ne correspond a aucune colonne")
            echecs += 1

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    #  DEUX COMPTEURS, ET NON UN TOTAL. Une empreinte bornee a 64 caracteres et
    #  une empreinte de mot de passe de longueur variable ne mesurent pas la meme
    #  grandeur : les additionner produirait un nombre qui ne veut rien dire.
    #  C'est la sixieme proposition du §7.0.
    print(
        f"  --> {len(suspectes)} colonne(s) evoquant un secret : "
        f"{empreintes_bornees} empreinte(s) de jeton bornee(s) a {LONGUEUR_SHA256_HEXA} "
        f"caracteres, {empreintes_de_mot_de_passe} empreinte(s) de mot de passe accompagnee(s) "
        f"de son algorithme, et {len(suspectes) - empreintes_bornees - empreintes_de_mot_de_passe} "
        f"exception(s) declaree(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
