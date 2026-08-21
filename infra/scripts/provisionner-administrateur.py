#!/usr/bin/env python3
"""Creer ou DEVERROUILLER un compte administrateur local — `DEC-527`.

LOT 3, sous-etape `T5`.

DEUX BESOINS, UNE SEULE CIBLE, ET C'EST DELIBERE

  **L'amorcage.** `user_account` nait vide : sans premiere ligne, personne ne peut
  se connecter en administrateur, et la demonstration de la porte `G3` — dont le
  point 7 est « verrouillage apres echecs administrateur repetes » — n'aurait rien
  a exercer. C'est le meme probleme que le domaine initial de `T3`.

  **Le deverrouillage.** Le §7 de la fiche du LOT 3 nomme le risque : « le
  verrouillage administrateur bloque Jonathan lui-meme », avec pour parade
  « prevoir et **documenter** le deverrouillage local, et l'eprouver ». Le verrou
  se relache seul au bout de quinze minutes ; cette cible le leve **tout de
  suite**, ce qui evite d'attendre quand on est presse.

  Les reunir evite une seconde cible qui partagerait 90 % de son code — deux
  copies divergent, `DEC-466`.

LE MOT DE PASSE EST ENGENDRE, AFFICHE UNE FOIS, ET JAMAIS ECRIT

  **Il n'est ni lu dans un fichier, ni passe en argument, ni demande a
  l'operateur.** Trois raisons :

    - un mot de passe en argument finit dans l'historique du shell et dans la
      liste des processus ;
    - un mot de passe dans un fichier finit versionne un jour ;
    - et le §7.14 du projet interdit de saisir un identifiant a la place de
      Jonathan.

  Il est donc tire par `secrets`, affiche **une seule fois**, et le compte est
  cree avec `must_change = true` : la premiere connexion imposera un changement.
  C'est `must_change` du §10.2 qui sert enfin a quelque chose.

IL NE TOUCHE JAMAIS A UN MOT DE PASSE EXISTANT

  Sur un compte qui existe deja, il **deverrouille** — `locked_until` a nul,
  compteur a zero — et **ne repose aucun mot de passe**. Reposer un mot de passe
  a chaque execution serait une porte derobee : quiconque peut lancer `make`
  pourrait prendre la main sur le compte.

  Pour repartir d'un mot de passe neuf, `--reinitialiser` le dit explicitement.
  C'est le meme parti que `provisionner-domaines.py`, qui ne reactive jamais un
  domaine coupe.

QUEL ROLE, ET POURQUOI

  Le role de MIGRATION. Il possede les tables, et creer un compte administrateur
  est un acte d'administration. Le role d'EXECUTION pourrait techniquement
  inserer, mais lui confier l'amorcage brouillerait la frontiere de `QO-116`.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

#  Le motif d'une adresse acceptable ici. Il est PLUS STRICT que la contrainte de
#  la base — laquelle tolere ce qu'un import du LOT 9 pourrait rencontrer — parce
#  qu'une adresse tapee a la main dans une commande d'amorcage doit etre refusee
#  avant d'atteindre PostgreSQL, avec un message qui nomme le probleme.
MOTIF_ADRESSE = re.compile(r"^[^@\s]+@[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9-]+)+$")

#  Longueur du mot de passe engendre. 32 caracteres `token_urlsafe` valent
#  environ 190 bits : il n'est pas destine a etre retenu, seulement a servir une
#  fois avant le changement impose.
OCTETS_DU_MOT_DE_PASSE = 24


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION. Motif du §7.2 : pas de shell.

    **SUR LES `# noqa: S608` DES APPELANTS.** Les requetes de ce script sont
    assemblees par interpolation, et chacune passe par `citer()`, qui echappe les
    apostrophes. Les seules valeurs qui viennent de l'exterieur sont l'adresse —
    validee contre `MOTIF_ADRESSE` avant tout usage — et des UUID lus dans la base
    elle-meme. `psql` n'accepte pas de parametres lies, ce qui est le motif de
    cette forme ; c'est la meme que `provisionner-roles.py` et
    `provisionner-domaines.py`.
    """
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


def citer(valeur: str) -> str:
    return "'" + valeur.replace("'", "''") + "'"


def valeur(sortie: str) -> str:
    """La PREMIERE ligne non vide d'une sortie `psql`.

    **CE N'EST PAS DU ZELE : SANS ELLE, UN `RETURNING id` EST INEXPLOITABLE.**
    `psql()` fusionne `stdout` et `stderr` a dessein -- en retenir un seul ferait
    disparaitre soit le resultat, soit la cause d'un echec, correctif deja
    applique a `provisionner-roles.py`. Mais la contrepartie est qu'un
    `INSERT ... RETURNING` rend deux lignes : l'identifiant, puis le tag
    `INSERT 0 1`.

    Ma premiere version passait les deux a la requete suivante, qui repondait
    « invalid input syntax for type uuid ». Mesure du 21/08/2026 sur la stack
    reelle -- le defaut n'existait pas dans les scripts precedents, aucun
    n'employant `RETURNING`.
    """
    for ligne in sortie.splitlines():
        if ligne.strip():
            return ligne.strip()
    return ""


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--adresse", required=True, help="adresse du compte administrateur")
    analyseur.add_argument(
        "--reinitialiser",
        action="store_true",
        help="reposer un mot de passe NEUF sur un compte existant. Explicite a dessein.",
    )
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    #  L'import est ICI, apres l'analyse des arguments : il exige les dependances
    #  de l'API, et `--help` doit fonctionner sans elles.
    from app.auth.mots_de_passe import ALGORITHME, hacher

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    manquantes = [
        nom
        for nom in ("POSTGRES_DB", "POSTGRES_MIGRATIONS_USER", "POSTGRES_MIGRATIONS_PASSWORD")
        if not env.get(nom)
    ]
    if manquantes:
        print(f"  ECHEC     variable(s) absente(s) : {manquantes}")
        return 1

    adresse = arguments.adresse.strip().lower()
    if not MOTIF_ADRESSE.match(adresse):
        print(f"  ECHEC     adresse invalide : {adresse!r}")
        print("            attendu : quelquechose@un-domaine.tld")
        return 1

    print()
    print("  Compte administrateur local — cahier §7.3, modele §10.1 et §10.2, DEC-527")

    code, sortie = psql(compose, env, "SELECT to_regclass('public.user_account') IS NOT NULL")
    if code:
        print(f"    ECHEC    base injoignable : {sortie[:180]}")
        return 1
    if sortie.strip() != "t":
        print("    ECHEC    la table `user_account` n'existe pas — lance `make migrate`")
        return 1

    #  --- La personne : elle DOIT exister, et on ne la cree PAS -------------
    #
    #  `user_account.person_id` est `NOT NULL` avec cle etrangere. Creer la
    #  personne ici serait fabriquer une identite metier depuis une commande
    #  d'exploitation, ce qui appartient au LOT 5 puis a l'import du LOT 9.
    code, personne = psql(
        compose,
        env,
        f"SELECT id FROM person WHERE email_normalized = {citer(adresse)}",  # noqa: S608
    )
    if code:
        print(f"    ECHEC    lecture de `person` : {personne[:180]}")
        return 1
    if not valeur(personne):
        print(f"    ECHEC    aucune personne ne porte l'adresse {adresse}")
        print("             ce script ne CREE PAS de personne : une identite metier vient")
        print("             du LOT 5 ou de l'import du LOT 9, jamais d'une commande")
        print("             d'exploitation. Cree la personne, puis relance.")
        return 1
    personne = valeur(personne)
    print(f"    ok       personne trouvee pour {adresse}")

    #  --- Le compte ---------------------------------------------------------
    code, compte = psql(
        compose,
        env,
        f"SELECT id, state, failed_login_count, locked_until IS NOT NULL "  # noqa: S608
        f"FROM user_account WHERE person_id = {citer(personne)}::uuid "
        f"  AND account_type = 'ADMIN_LOCAL'",
    )
    if code:
        print(f"    ECHEC    lecture de `user_account` : {compte[:180]}")
        return 1

    existe = bool(valeur(compte))
    if existe:
        identifiant, etat, echecs, verrouille = valeur(compte).split("|")
        print(
            f"    ok       compte ADMIN_LOCAL existant — etat {etat}, "
            f"{echecs} echec(s), verrouille : {'oui' if verrouille == 't' else 'non'}"
        )
        #  DEVERROUILLAGE : compteur a zero, verrou leve, etat remis a `active`.
        code, sortie = psql(
            compose,
            env,
            "UPDATE user_account SET failed_login_count = 0, locked_until = NULL, "  # noqa: S608
            f"  state = 'active' WHERE id = {citer(identifiant)}::uuid",
        )
        if code:
            print(f"    ECHEC    deverrouillage : {sortie[:180]}")
            return 1
        print("    ok       DEVERROUILLE — compteur a zero, verrou leve, etat `active`")
    else:
        code, identifiant = psql(
            compose,
            env,
            "INSERT INTO user_account "  # noqa: S608
            "(person_id, account_type, state, failed_login_count) "
            f"VALUES ({citer(personne)}::uuid, 'ADMIN_LOCAL', 'active', 0) RETURNING id",
        )
        if code or not valeur(identifiant):
            print(f"    ECHEC    creation du compte : {identifiant[:180]}")
            return 1
        identifiant = valeur(identifiant)
        print("    ok       compte ADMIN_LOCAL CREE")

    #  --- Le mot de passe ---------------------------------------------------
    code, actif = psql(
        compose,
        env,
        "SELECT count(*) FROM admin_password_credential "  # noqa: S608
        f"WHERE user_account_id = {citer(identifiant)}::uuid AND revoked_at IS NULL",
    )
    if code:
        print(f"    ECHEC    lecture des identifiants : {actif[:180]}")
        return 1
    a_un_mot_de_passe = valeur(actif) != "0"

    if a_un_mot_de_passe and not arguments.reinitialiser:
        #  **ON NE TOUCHE PAS A UN MOT DE PASSE EXISTANT.** Le reposer a chaque
        #  execution serait une porte derobee.
        print("    ok       un mot de passe actif existe — il n'est PAS touche")
        print("             pour en poser un neuf : --reinitialiser, explicitement")
        print()
        print("  --> compte pret. Deverrouille, mot de passe inchange.")
        return 0

    mot_de_passe = secrets.token_urlsafe(OCTETS_DU_MOT_DE_PASSE)
    empreinte, parametres = hacher(mot_de_passe)
    #  L'ancien est REVOQUE avant que le nouveau ne soit pose : l'index partiel de
    #  `T2` exige qu'au plus un soit actif, et l'ordre inverse echouerait.
    code, sortie = psql(
        compose,
        env,
        "UPDATE admin_password_credential SET revoked_at = now() "  # noqa: S608
        f"WHERE user_account_id = {citer(identifiant)}::uuid AND revoked_at IS NULL",
    )
    if code:
        print(f"    ECHEC    revocation de l'ancien identifiant : {sortie[:180]}")
        return 1
    code, sortie = psql(
        compose,
        env,
        "INSERT INTO admin_password_credential "  # noqa: S608
        "(user_account_id, password_hash, algorithm, parameters, changed_at, must_change) "
        f"VALUES ({citer(identifiant)}::uuid, {citer(empreinte)}, {citer(ALGORITHME)}, "
        f"        {citer(json.dumps(parametres))}::jsonb, now(), TRUE)",
    )
    if code:
        print(f"    ECHEC    pose du mot de passe : {sortie[:180]}")
        return 1

    print(f"    ok       mot de passe pose — algorithme {ALGORITHME}, must_change = true")
    print()
    print("  ┌─ MOT DE PASSE PROVISOIRE, AFFICHE UNE SEULE FOIS ──────────────────")
    print(f"  │  adresse      : {adresse}")
    print(f"  │  mot de passe : {mot_de_passe}")
    print("  └────────────────────────────────────────────────────────────────────")
    print()
    print("  Il n'est NULLE PART ailleurs : ni fichier, ni journal, ni base — seule")
    print("  son empreinte est stockee. `must_change` est a vrai : la premiere")
    print("  connexion exigera un changement.")
    print()
    print("  --> compte pret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
