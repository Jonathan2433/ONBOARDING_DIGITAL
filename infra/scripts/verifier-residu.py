#!/usr/bin/env python3
"""La suite d'integration laisse-t-elle quelque chose derriere elle ?

LOT 3, sous-etape `T12`.

POURQUOI CE CONTROLE EXISTE : SEPT OCCURRENCES DE LA MEME LECON

  Une seule classe de defaut s'est rejouee **sept fois** dans ce lot :

      `T3-3`   18 lignes `auth_event` residuelles ont fait echouer 2 tests de `T2`
      `T4-3`   un nettoyage supprime par une reecriture -> execution suivante cassee
      `T4-5`   les `LOGIN_FAILURE` sans personne echappaient au nettoyage
      `T5-5`   idem, dans un autre fichier
      `T6-2`   cinq nettoyages anterieurs a `user_session` -> 10 tests casses
      `T9`     six defauts de decor, tous trouves par la base
      `T10-2`  13 evenements sans acteur, **une sous-etape apres avoir ecrit la lecon**

  **La septieme est celle qui decide.** J'avais ecrit, dans le compte rendu de
  `T9` : « la trace d'un refus sans acteur echappe a tout nettoyage par
  identite ». Je l'ai recommise en `T10`. Le §7.2 dit quoi faire dans ce cas :
  **quand une classe d'erreur resiste a la vigilance, change d'outil au lieu de
  promettre d'etre plus attentif.** Une huitieme promesse ne vaudrait rien.

LA MESURE EST EXACTE, PAS HEURISTIQUE

  Il serait tentant de chercher des marqueurs -- `t3api`, `%.test`, `t12-verif-`.
  Ce serait une **liste** qui vieillit au premier marqueur ajoute, et une
  **heuristique** dans un controle est un defaut : lecon `T9-2`, confirmee par le
  §7.25.

  Ce controle compare donc un **avant** et un **apres** : il compte les lignes de
  chaque table metier, lance la suite d'integration, recompte, et exige l'egalite
  **table par table**. Aucune liste de marqueurs, aucune hypothese sur ce qui est
  « du test » -- et il fonctionne aussi bien sur une base vide que sur le jeu de
  recette de 27 936 lignes.

  **LA LISTE DES TABLES EST DERIVEE DU CATALOGUE**, non ecrite : une table
  ajoutee par un lot futur y entre seule.

IL REMPLACE `make test-integration` DANS LA CI, IL NE S'Y AJOUTE PAS

  Lancer la suite deux fois doublerait cinquante secondes pour rien. La CI appelle
  donc ce controle **a la place**, et son code de sortie porte les deux verdicts :
  les tests **et** le residu.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]

#  Les tables que ce controle NE compte pas, et pourquoi.
#
#    `alembic_version`   metadonnee de migration, une seule ligne par definition
#    `platform_setting`  reglages globaux, poses par provisionnement
#    `allowed_email_domain`  pose par `make domaines-provision`, appele par
#                            `make migrate` : sa presence est un ETAT VOULU
#
#  Aucune autre exception : un test qui laisse une ligne ailleurs doit echouer.
TABLES_HORS_COMPTE = frozenset({"alembic_version", "platform_setting", "allowed_email_domain"})


def compter(compose: list[str], env: dict[str, str]) -> dict[str, int]:
    """Compter les lignes de chaque table metier. **La liste vient du catalogue.**"""
    requete = (
        "SELECT string_agg(format('SELECT %L AS t, count(*) AS n FROM %I', "
        "  tablename, tablename), ' UNION ALL ') FROM pg_tables "
        "WHERE schemaname = 'public'"
    )
    code, sortie = psql(compose, env, requete)
    if code or not sortie.strip():
        message = f"catalogue illisible : {sortie[:200]}"
        raise RuntimeError(message)
    code, sortie = psql(compose, env, sortie.strip().splitlines()[0])
    if code:
        message = f"comptage impossible : {sortie[:200]}"
        raise RuntimeError(message)
    comptes: dict[str, int] = {}
    for ligne in sortie.splitlines():
        if "|" not in ligne:
            continue
        table, nombre = ligne.strip().split("|")
        if table not in TABLES_HORS_COMPTE:
            comptes[table] = int(nombre)
    return comptes


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
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
    return execution.returncode, (execution.stdout + execution.stderr).strip()


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


#  Une trace d'authentification SANS ACTEUR : ni personne, ni compte utilisateur,
#  ni compte de service. C'est la signature d'un REFUS, et le §7.32 dit pourquoi
#  aucun nettoyage ne peut l'atteindre : il n'y a pas d'identite par laquelle la
#  supprimer.
#  La requete est un LITTERAL, sans interpolation : `compter()` fait de meme, et
#  cela evite d'avoir a desarmer S608 par un `noqa` sur une requete qui n'a de
#  toute facon aucune entree variable.
_COMPTER_LES_TRACES_SANS_ACTEUR = (
    "SELECT count(*) FROM auth_event "
    "WHERE person_id IS NULL AND user_account_id IS NULL AND service_account_id IS NULL;"
)

#  LOT 10, `T2` : `audit_event` recoit desormais la MEME classe de trace
#  structurelle, pour la MEME raison — chacun des quatre sites cables sur
#  l'authentification ecrit AUSSI une ligne `audit_event` sur un refus sans
#  acteur (adresse de magic link inconnue, jeton de service inconnu).
_COMPTER_LES_TRACES_AUDIT_SANS_ACTEUR = (
    "SELECT count(*) FROM audit_event "
    "WHERE actor_person_id IS NULL AND actor_service_account_id IS NULL;"
)


def ventiler(compose: list[str], env: dict[str, str], comptes: dict[str, int]) -> int:
    """Nommer le residu PREALABLE table par table, et rendre ce qu'il reste d'inexplique.

    **POURQUOI CETTE FONCTION EXISTE.** Ce controle annoncait « N ligne(s) avant »
    et rien d'autre, et le §7.30 de la passation en concluait : « sur une base
    propre il vaut 0, et toute autre valeur est un residu a nommer avant de le
    supprimer ». Mesure du 08/09/2026 : il valait **7**, et la passation ne
    donnait aucun moyen de savoir ou. Un nombre qu'on ne peut pas ventiler
    n'apprend rien -- et il apprend a ne plus le lire, ce qui est le §7.21.

    **CE QUI EST STRUCTUREL EST DIT STRUCTUREL, ET SEULEMENT CELA.** Les traces
    sans acteur d'`auth_event` sont produites par nos propres controles de stack :
    `verifier-magic-link.py` et `verifier-connexion-admin.py` demandent
    DELIBEREMENT un lien pour une adresse inconnue, pour prouver que la reponse
    est identique connue ou non (§22.5). Chacune ecrit un refus que le §12.2
    interdit de rattacher a quiconque -- l'y rattacher revelerait l'existence de
    l'adresse. Il n'existe donc aucun nettoyage possible, et exiger zero
    exigerait de renoncer a la preuve.

    **MAIS L'EXEMPTION EST MESUREE, PAS ACCORDEE A LA TABLE.** Exclure
    `auth_event` en bloc masquerait un vrai residu : une trace PORTANT un acteur,
    laissee par un test qui n'a pas nettoye. Le discriminant est donc la colonne,
    jamais le nom de la table -- c'est la lecon du §7.25, ou le discriminant
    n'etait pas dans le texte source mais dans le TYPE de colonne.
    """
    peuplees = {table: n for table, n in comptes.items() if n > 0}
    if not peuplees:
        print("    ok       aucun residu prealable : les tables comptees sont vides")
        return 0

    structurelles_par_table: dict[str, int] = {}
    for table, requete in (
        ("auth_event", _COMPTER_LES_TRACES_SANS_ACTEUR),
        ("audit_event", _COMPTER_LES_TRACES_AUDIT_SANS_ACTEUR),
    ):
        if not peuplees.get(table):
            continue
        code, sortie = psql(compose, env, requete)
        if code == 0 and sortie.strip().isdigit():
            structurelles_par_table[table] = int(sortie.strip())
        else:
            print(f"    info     {table} : ventilation illisible ({sortie[:80]})")

    print("    info     residu prealable, table par table :")
    for table, nombre in sorted(peuplees.items()):
        detail = ""
        if structurelles_par_table.get(table):
            detail = f"  dont {structurelles_par_table[table]} SANS ACTEUR, donc structurelle(s)"
        print(f"               {table:34s} {nombre:6d}{detail}")

    structurelles = sum(structurelles_par_table.values())
    inexplique = sum(peuplees.values()) - structurelles
    if structurelles:
        print(
            f"    info     les {structurelles} trace(s) sans acteur (`auth_event`/`audit_event`) "
            "sont des REFUS,"
        )
        print("             ecrits par `magic-link-check` et `admin-check` qui demandent")
        print("             un lien pour une adresse INCONNUE afin de prouver que la reponse")
        print("             est identique (§22.5). Le §12.2 interdit de les rattacher a")
        print("             quiconque : aucun nettoyage par identite ne peut les atteindre,")
        print("             et exiger zero exigerait de renoncer a la preuve. §7.32")
    if inexplique:
        print(f"    info     {inexplique} ligne(s) qu'aucune cause structurelle n'explique —")
        print("             a NOMMER avant de supprimer, et non l'inverse : elles peuvent")
        print("             etre du jeu de recette, ou un vrai residu de test. §7.30")
    return inexplique


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

    print()
    print("  Residu de la suite d'integration — LOT 3, `T12`")

    avant = compter(compose, env)
    print(f"    info     {len(avant)} tables comptees, {sum(avant.values())} ligne(s) avant")
    ventiler(compose, env, avant)
    #  **VIDER LE TAMPON AVANT DE LANCER PYTEST, SINON LE JOURNAL EST ILLISIBLE.**
    #  Nos `print` sont tamponnes des que la sortie n'est pas un terminal -- en CI,
    #  elle ne l'est jamais -- tandis que le sous-processus ecrit DIRECTEMENT sur le
    #  meme descripteur. Sans ce vidage, la ventilation apparait APRES les points de
    #  pytest, donc apres ce qu'elle est censee expliquer. Mesure du 08/09/2026 :
    #  redirige vers un fichier, l'en-tete arrivait en fin de journal.
    sys.stdout.flush()

    #  **`sys.executable -m pytest` ET NON `uv run pytest`.** Un chemin partiel --
    #  `uv` -- depend du `PATH`, et le §5.1 rappelle que `uv` n'y est PAS par defaut
    #  sur cette machine. `sys.executable` est l'interpreteur qui execute ce script,
    #  donc celui de l'environnement virtuel : il ne peut pas se tromper de Python,
    #  et il n'y a aucun chemin a resoudre.
    execution = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "integration"],
        cwd=RACINE,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    tests_verts = execution.returncode == 0
    print(
        f"    {'ok      ' if tests_verts else 'ECHEC   '} suite d'integration : "
        f"code {execution.returncode}"
    )

    apres = compter(compose, env)
    ecarts = {
        table: (avant.get(table, 0), nombre)
        for table, nombre in apres.items()
        if nombre != avant.get(table, 0)
    }

    print()
    if ecarts:
        print(f"  ECHEC : {len(ecarts)} table(s) ont change de compte — RESIDU")
        for table, (avant_n, apres_n) in sorted(ecarts.items()):
            print(f"      {table:38s} {avant_n} -> {apres_n}  ({apres_n - avant_n:+d})")
        print()
        print("      Un nettoyage de test est incomplet. Trois causes ont produit les")
        print("      sept occurrences de ce lot :")
        print("        - une table AJOUTEE par une sous-etape recente, absente des")
        print("          nettoyages ecrits avant elle, dont la cle etrangere bloque")
        print("          la suppression et fait tout echouer en silence ;")
        print("        - une trace SANS ACTEUR — ni personne, ni compte de service —")
        print("          qui echappe a tout nettoyage par identite : seule une borne")
        print("          temporelle l'attrape ;")
        print("        - un test qui VALIDE sa transaction et dont le nettoyage a ete")
        print("          perdu dans une reecriture.")
        return 1
    if not tests_verts:
        print("  ECHEC : la suite d'integration a echoue (aucun residu, cependant)")
        return 1
    print(f"  --> {len(apres)} tables comptees, aucun residu, et la suite est verte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
