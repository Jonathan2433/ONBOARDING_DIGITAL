#!/usr/bin/env python3
"""Poser le domaine e-mail INITIAL du cahier §7.2 — `DEC-523`.

LOT 3, sous-etape `T3`.

POURQUOI CE SCRIPT EXISTE, ET CE QU'IL NE DECIDE PAS

  Le modele §5.4 pose que c'est `allowed_email_domain.active` qui « **controle
  l'usage lors de l'authentification** ». La table fait donc autorite, et
  `ALLOWED_EMAIL_DOMAINS` n'autorise rien par elle-meme.

  Mais la table nait VIDE. Sans premiere ligne, aucun collaborateur ne peut
  demander de lien -- y compris pour la demonstration de la porte `G3`, dont le
  point 1 est « demande d'un magic link pour une personne active ». Le cahier
  §7.2 nomme la valeur : « le domaine initial confirme est `@exalt-company.com` ».

  Ce script pose cette ligne, et **rien de plus**. Ajouter, retirer ou desactiver
  un domaine ensuite est une action d'administration -- la matrice §19 la reserve
  au global -- et elle appartient au back-office du LOT 9.

POURQUOI IL EST APPELE PAR `make migrate` ET NON PAR `make up`

  Il ecrit dans une table, donc il **exige une base migree**. `make up` appelle
  `minio-bucket` et `roles-provision` avant les services applicatifs, a un moment
  ou aucune migration n'a tourne : `allowed_email_domain` n'y existe pas
  necessairement.

  Le rattacher a `make migrate` le place juste apres l'etape qui CREE la table,
  et `make migrate` est dans la sequence de demarrage documentee. L'alternative
  -- un appel depuis `make up` qui « saute » quand la table manque -- aurait
  produit un succes silencieux, ce que le §7.0 interdit.

IL NE REACTIVE JAMAIS UN DOMAINE DESACTIVE, ET C'EST LE POINT LE PLUS IMPORTANT

  `active` est un interrupteur d'administration. Un script idempotent qui
  reposerait `active = true` a chaque `make migrate` **annulerait la decision d'un
  administrateur qui a coupe un domaine**, et le ferait en paraissant anodin.

  Il ne repose donc rien : il cree ce qui manque, et **rapporte** ce qui existe
  dans un etat autre que celui attendu. C'est le §7.20 -- exiger ce qui est
  exigible, rapporter visiblement le reste, en le nommant.

QUEL ROLE, ET POURQUOI

  Le role de MIGRATION. Il possede la table depuis `T1` du LOT 3, et
  l'approvisionnement d'une donnee de reference est un acte d'administration.
  Le role d'EXECUTION pourrait techniquement inserer -- il a `INSERT` -- mais
  l'API ne fait que LIRE cette table : lui faire porter l'ecriture ici brouillerait
  la frontiere que `QO-116` a etablie.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

#  Le §5.4 exige un domaine « normalise sans `@` », et la contrainte
#  `domain_normalise` de la migration `0003` le verifie en base. Ce motif est le
#  MEME, recopie ici a dessein : ce script doit refuser une valeur avant de
#  l'envoyer, pour que le message nomme la variable fautive plutot que de laisser
#  PostgreSQL parler d'une contrainte dont l'operateur ignore le nom.
MOTIF_DOMAINE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")

TABLE = "allowed_email_domain"


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Executer une requete avec le role de MIGRATION. Motif du §7.2 : pas de shell."""
    # S603 : entree du Makefile, jamais d'un tiers, et `shell=False`.
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "--env",
            f"PGPASSWORD={env['POSTGRES_MIGRATIONS_PASSWORD']}",
            "db",
            "psql",
            "-U",
            env["POSTGRES_MIGRATIONS_USER"],
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
    #  LES DEUX FLUX : `psql` envoie ses `NOTICE` sur stderr et ses resultats sur
    #  stdout. En retenir un seul ferait disparaitre soit le resultat, soit la
    #  cause de l'echec — correctif deja applique a `provisionner-roles.py`.
    return execution.returncode, (execution.stdout + execution.stderr).strip()


def citer(valeur: str) -> str:
    """Citer une chaine litterale SQL."""
    return "'" + valeur.replace("'", "''") + "'"


def domaines_de(brut: str) -> tuple[str, ...]:
    """Lire la graine, comme `Parametres.domaines_initiaux()`.

    Le `@` eventuel est retire : le cahier §7.2 ecrit `@exalt-company.com` et le
    §5.4 exige la forme sans arobase. Refuser la graphie du cahier serait refuser
    la valeur que l'operateur recopie.
    """
    return tuple(
        domaine
        for domaine in (element.strip().lower().lstrip("@") for element in brut.split(","))
        if domaine
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

    manquantes = [
        nom
        for nom in (
            "POSTGRES_DB",
            "POSTGRES_MIGRATIONS_USER",
            "POSTGRES_MIGRATIONS_PASSWORD",
            "ALLOWED_EMAIL_DOMAINS",
        )
        if not env.get(nom)
    ]
    if manquantes:
        print(f"  ECHEC     variable(s) absente(s) du fichier d'environnement : {manquantes}")
        print("            `make env-check` les nomme.")
        return 1

    print()
    print("  Domaine e-mail initial — cahier §7.2, modele §5.4, DEC-523")

    #  LA TABLE DOIT EXISTER, ET SON ABSENCE EST UN ECHEC, PAS UN SAUT.
    code, sortie = psql(
        compose,
        env,
        f"SELECT to_regclass({citer('public.' + TABLE)}) IS NOT NULL",
    )
    if code:
        print(f"    ECHEC    base injoignable avec le role de migration : {sortie[:180]}")
        return 1
    if sortie.strip() != "t":
        print(f"    ECHEC    la table `{TABLE}` n'existe pas — la base n'est pas migree")
        print("             lance `make migrate`, puis relance cette cible")
        return 1

    domaines = domaines_de(env["ALLOWED_EMAIL_DOMAINS"])
    if not domaines:
        print("    ECHEC    ALLOWED_EMAIL_DOMAINS ne declare aucun domaine exploitable")
        return 1

    echecs = 0
    crees = 0
    existants = 0
    signales = 0

    for domaine in domaines:
        if not MOTIF_DOMAINE.match(domaine):
            print(f"    ECHEC    ALLOWED_EMAIL_DOMAINS : {domaine!r} n'est pas un domaine")
            print("             forme attendue : minuscules, un point au moins, sans `@`")
            echecs += 1
            continue

        #  On cherche la ligne GLOBALE, `entity_id IS NULL` : c'est celle que le
        #  cahier §7.2 decrit, « le domaine initial ». Une ligne LOCALE du meme
        #  domaine n'autorise que son entite, et ne remplace donc pas celle-ci.
        #  S608 : `citer()` echappe, et le domaine a ete valide contre
        #  `MOTIF_DOMAINE` ci-dessus.
        requete = (
            f"SELECT active, (period @> now()) FROM {TABLE} "  # noqa: S608
            f"WHERE domain = {citer(domaine)} AND entity_id IS NULL LIMIT 1"
        )
        code, sortie = psql(compose, env, requete)
        if code:
            print(f"    ECHEC    lecture de {domaine} : {sortie[:180]}")
            echecs += 1
            continue

        if sortie.strip():
            actif, dans_la_periode = (champ == "t" for champ in sortie.strip().split("|"))
            if actif and dans_la_periode:
                print(f"    ok       {domaine} — ligne globale ACTIVE, deja en place")
                existants += 1
            else:
                #  RAPPORTE, JAMAIS REPOSE. Voir l'en-tete : reactiver
                #  annulerait la decision d'un administrateur.
                etat = "desactivee" if not actif else "hors de sa periode de validite"
                print(f"    SIGNALE  {domaine} — la ligne globale existe mais est {etat}")
                print("             AUCUNE connexion n'est possible sur ce domaine")
                print(
                    "             ce script ne la reactive PAS : c'est une decision"
                    " d'administration"
                )
                signales += 1
            continue

        #  S608 : meme justification que ci-dessus.
        insertion = (
            f"INSERT INTO {TABLE} (domain, entity_id, active, starts_at) "  # noqa: S608
            f"VALUES ({citer(domaine)}, NULL, TRUE, now())"
        )
        code, sortie = psql(compose, env, insertion)
        if code:
            print(f"    ECHEC    insertion de {domaine} : {sortie[:180]}")
            echecs += 1
            continue
        print(f"    ok       {domaine} — ligne globale CREEE, active a compter de maintenant")
        crees += 1

    print()
    print(
        f"    info     {len(domaines)} domaine(s) de la graine : "
        f"{crees} cree(s) · {existants} deja actif(s) · {signales} signale(s)"
    )
    #  LE COMPTE EST CONFRONTE A UN ATTENDU : sans cela, ce script pourrait
    #  n'avoir traite qu'un domaine sur trois et le dire « ok ». §7.0, troisieme
    #  proposition.
    if crees + existants + signales + echecs != len(domaines):
        print("    ECHEC    tous les domaines de la graine n'ont pas ete traites")
        echecs += 1

    print()
    if echecs:
        print(f"  ECHEC : {echecs} domaine(s) non approvisionnes")
        return 1
    if signales:
        print("  --> approvisionnement termine. UN DOMAINE AU MOINS EST INUTILISABLE,")
        print("      voir les lignes SIGNALE ci-dessus. Ce n'est pas un echec de ce")
        print("      script : c'est un etat que seule une administration peut changer.")
        return 0
    print(f"  --> les {len(domaines)} domaine(s) de la graine sont actifs et dans leur periode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
