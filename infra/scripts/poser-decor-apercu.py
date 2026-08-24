#!/usr/bin/env python3
"""Poser — ou retirer — un decor FICTIF pour regarder le portail dans un navigateur.

LOT 4, apres `T7`. Ce script n'est PAS un controle : il n'affirme rien, il prepare.

POURQUOI IL EXISTE

  Voir le portail exige trois choses qu'aucune commande ne donnait ensemble : un
  conteneur `web` qui porte le code du depot -- il n'a AUCUN montage, le code y est
  cuit, `ECART-042` -- au moins une entite ACTIVE, et une session.

  `make apercu` fait les trois et imprime l'adresse et le mot de passe.

CE QU'IL POSE, ET IL EST TOUJOURS FICTIF

  Deux entites et un compte administrateur local, tous marques `apercu-`. Aucune
  donnee reelle de collaborateur : c'est l'interdit absolu du §2 de la passation.
  `make apercu-fin` retire tout ce qui porte le marqueur.

  **Le mot de passe est imprime sur la sortie standard**, jamais ecrit dans un
  fichier ni journalise. `make admin-local` fait de meme depuis `DEC-527`.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
MARQUEUR = "apercu-"
ENTITES = (
    ("apercu-bordeaux", "eXalt Bordeaux", "Bordeaux"),
    ("apercu-lille", "eXalt Lille", "Lille"),
)


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION. Pas de shell — §7.2."""
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


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--retirer", action="store_true")
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)
    adresse = f"{MARQUEUR}demo@exalt-company.com"

    if arguments.retirer:
        for gabarit in (
            "auth_event WHERE person_id IN"
            "  (SELECT id FROM person WHERE email_normalized LIKE '{m}%')",
            "user_session WHERE person_id IN"
            "  (SELECT id FROM person WHERE email_normalized LIKE '{m}%')",
            "admin_password_credential WHERE user_account_id IN (SELECT id FROM user_account"
            "  WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{m}%'))",
            "user_account WHERE person_id IN"
            "  (SELECT id FROM person WHERE email_normalized LIKE '{m}%')",
            "entity_membership WHERE person_id IN"
            "  (SELECT id FROM person WHERE email_normalized LIKE '{m}%')",
            "person WHERE email_normalized LIKE '{m}%'",
            "entity WHERE code LIKE '{m}%'",
        ):
            psql(compose, env, "DELETE FROM " + gabarit.format(m=MARQUEUR))  # noqa: S608
        print()
        print(f"  ok       tout ce qui portait « {MARQUEUR} » est retire")
        return 0

    valeurs = ", ".join(
        f"('{code}', '{nom}', '{ville}', 'FR', 'active', 'Europe/Paris')"
        for code, nom, ville in ENTITES
    )
    code, sortie = psql(
        compose,
        env,
        "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "  # noqa: S608
        f"VALUES {valeurs} ON CONFLICT (code) DO NOTHING; "
        "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
        f"VALUES ('{adresse}', '{adresse}', 'Apercu', 'Demo', 'active') "
        "ON CONFLICT (email_normalized) DO NOTHING;",
    )
    if code:
        print(f"  ECHEC    decor impossible : {sortie[:250]}")
        return 1

    #  **`REINITIALISER=1` EST TOUJOURS PASSE, ET C'EST UN DEFAUT CORRIGE.**
    #  `make admin-local` est idempotent : au SECOND appel il ne recree rien, donc
    #  il n'imprime plus aucun mot de passe -- et `make apercu` cessait de repondre
    #  a la seule question qu'il existe pour repondre, « comment j'entre ».
    #
    #  Mesure du 24/08/2026 : premier appel, un mot de passe ; second appel,
    #  « (voir `make admin-local` ci-dessus) », une note que personne ne peut
    #  suivre. C'est le §7.21 -- un message qu'on ne peut pas actionner apprend a
    #  ne pas lire l'outil.
    #
    #  Reinitialiser est sans risque ICI et nulle part ailleurs : le compte porte
    #  le prefixe `apercu-`, il est cree par ce script, et `make apercu-fin` le
    #  supprime. Ce n'est pas une reinitialisation d'un compte reel.
    make = shutil.which("make") or "/usr/bin/make"
    admin = subprocess.run(  # noqa: S603
        [make, "admin-local", f"ADRESSE={adresse}", "REINITIALISER=1"],
        capture_output=True,
        text=True,
        cwd=RACINE,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    mot_de_passe = ""
    for ligne in (admin.stdout + admin.stderr).splitlines():
        if "mot de passe :" in ligne:
            mot_de_passe = ligne.split("mot de passe :")[1].strip()
    #  **L'ABSENCE DE MOT DE PASSE EST UN ECHEC, PAS UNE NOTE.** Un apercu dans
    #  lequel on ne peut pas entrer ne sert a rien : mieux vaut le dire fort que
    #  d'imprimer un chemin d'acces incomplet en sortant en 0.
    if not mot_de_passe:
        print()
        print("  ECHEC    aucun mot de passe obtenu de `make admin-local` :")
        for ligne in (admin.stdout + admin.stderr).splitlines()[-6:]:
            print(f"           {ligne}")
        print("           -> sans lui, l'apercu est inutilisable. Le decor reste pose ;")
        print("              `make apercu-fin` le retire.")
        return 1

    hote = env.get("CADDY_SITE_APP", "app.onboarding.localhost")
    port = env.get("CADDY_HTTPS_HOST_PORT", "443")
    base = f"https://{hote}" if port == "443" else f"https://{hote}:{port}"

    print()
    print("  Apercu du portail — decor FICTIF, marque « apercu- »")
    print(f"    ok       {len(ENTITES)} entites actives posees")
    print(f"    ok       compte administrateur local : {adresse}")
    print()
    print("  ┌─ POUR REGARDER ───────────────────────────────────────────────")
    print(f"  │  1. ouvre        {base}/connexion/administrateur")
    print(f"  │  2. adresse      {adresse}")
    print(f"  │  3. mot de passe {mot_de_passe}")
    print(f"  │  4. puis         {base}/   ← la page nationale")
    print("  │")
    print("  │  Safari, Chrome et Edge acceptent le certificat local ; Firefox")
    print("  │  non, il gere son propre magasin (§5.6).")
    print("  │")
    print(f"  │  Autres adresses :  {base}/statut          l'etat des services")
    print(f"  │                     {base}/connexion       le magic link")
    print("  └───────────────────────────────────────────────────────────────")
    print()
    print("  APRES CHAQUE MODIFICATION DU FRONTEND : relance `make apercu`.")
    print("  Le conteneur `web` n'a AUCUN montage -- le code y est cuit dans")
    print("  l'image -- donc il n'y a PAS de rechargement a chaud aujourd'hui.")
    print()
    print("  ┌─ ET UNE CHOSE A SAVOIR AVANT DE LANCER LES TESTS ─────────────")
    print("  │  `make check` ECHOUERA tant que ce decor est en place.")
    print("  │")
    print("  │  Ce n'est pas un defaut : les tests d'integration du LOT 2 comptent")
    print("  │  `person` et `entity` EN ABSOLU, dans une transaction en rollback --")
    print("  │  ce qui ne vaut que sur une base propre. L'apercu, lui, doit COMMITER")
    print("  │  ses lignes pour que le navigateur les voie. Les deux ne peuvent donc")
    print("  │  pas coexister, et c'est le meme mecanisme que le defaut `T2-2`.")
    print("  │")
    print("  │  Avant `make check` :  make apercu-fin")
    print("  └───────────────────────────────────────────────────────────────")
    print()
    print("  Pour tout retirer :  make apercu-fin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
