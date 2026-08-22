#!/usr/bin/env python3
"""Le depart revoque-t-il immediatement, et la session cesse-t-elle de repondre ?

LOT 3, sous-etape `T9`, story `MVP-L03-US006`. Rend `§30.22` acquis.

CE QUE CE CONTROLE PROUVE QUE LES TESTS NE PROUVENT PAS

  Les tests d'integration montent l'application en processus et appellent le
  service directement. Ici la session est ouverte **par une vraie connexion
  administrateur a travers Caddy en HTTPS**, et sa mort est constatee par un
  **aller-retour HTTP reel** sur l'API du conteneur.

  La difference est celle du §7.28 : un controle statique ne dit rien de ce qui
  tourne. Une session revoquee en base et une session revoquee **pour l'API** sont
  deux grandeurs differentes tant qu'on n'a pas interroge l'API.

IL PORTE SES TEMOINS

  - **la session repond AVANT** le depart : sans ce temoin, un cookie casse
    donnerait la meme observation qu'une revocation qui fonctionne ;
  - **l'archivage qui suit ne trouve plus rien** : c'est ce qui prouve que la
    revocation tient au depart et non a l'archivage ;
  - **une transition hors du §24.1 est refusee** : sans elle, on pourrait archiver
    sans passer par le depart, et l'etat `departed` serait decoratif.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_SESSION = "/api/v1/auth/session"

MARQUEUR = f"t9-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30


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


def valeur(sortie: str) -> str:
    """La premiere ligne non vide. `psql` mele ses etiquettes au resultat — `T5-1`."""
    for ligne in sortie.splitlines():
        if ligne.strip():
            return ligne.strip()
    return ""


class Reponse:
    def __init__(self, statut: int, corps: bytes, en_tetes: list[tuple[str, str]]) -> None:
        self.statut = statut
        self.corps = corps
        self.cookies_poses = [v for nom, v in en_tetes if nom.lower() == "set-cookie"]


def appeler(
    base: str,
    chemin: str,
    contexte: ssl.SSLContext,
    *,
    charge: dict[str, str] | None = None,
    en_tetes: dict[str, str] | None = None,
) -> Reponse:
    entetes = {"Content-Type": "application/json"} if charge is not None else {}
    entetes.update(en_tetes or {})
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method="POST" if charge is not None else "GET",
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), list(reponse.headers.items()))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), list(erreur.headers.items()))


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--base", required=True)
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    from app.auth.mots_de_passe import ALGORITHME, hacher
    from app.auth.sessions import REVOCATION_DEPART

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    adresse = f"{MARQUEUR}@{domaine}"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Revocation au depart — US006, cahier §6.2, §7.4, §30.22")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not valeur(debut):
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = valeur(debut)

    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; m uuid; c uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}', 'Entite T9', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'T9', 'active') RETURNING id INTO p;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (p, e, current_date - 30, 'active', 'consultant', 'draft') RETURNING id INTO m;
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (p, e, 'ESM', p, now() - interval '10 days');
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
    END $$;
    """  # noqa: S608 — seul `MARQUEUR`, un `uuid4` de ce module, est interpole
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor : 1 entite, 1 appartenance ACTIVE, 1 responsabilite ESM,")
    print("             1 compte ADMIN_LOCAL")

    code, sortie = psql(
        compose,
        env,
        "SELECT m.id FROM entity_membership m JOIN person p ON p.id = m.person_id "  # noqa: S608
        f"WHERE p.email_normalized = '{adresse}'",
    )
    appartenance = valeur(sortie)
    if code or not appartenance:
        print(f"    ECHEC    appartenance introuvable : {sortie[:180]}")
        return 1

    try:
        #  --------------------------------------------------------------
        #  1. TEMOIN — la session repond AVANT le depart
        #  --------------------------------------------------------------
        controles += 1
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
            en_tetes={"Origin": arguments.base},
        )
        cookie = next(
            (
                c.split("=", 1)[1].split(";", 1)[0]
                for c in connexion.cookies_poses
                if nom_cookie in c
            ),
            None,
        )
        entetes_cookie = {"Cookie": f"{nom_cookie}={cookie}"}
        if connexion.statut != 200 or not cookie:
            etat_cookie = "pose" if cookie else "absent"
            print(f"    ECHEC    connexion {connexion.statut}, cookie {etat_cookie}")
            echecs += 1
        else:
            avant = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=entetes_cookie)
            if avant.statut != 200:
                print(f"    ECHEC    TEMOIN : la session rend {avant.statut} AVANT le depart")
                echecs += 1
            else:
                print("    ok       TEMOIN — la session repond (200) avant le depart")

        #  --------------------------------------------------------------
        #  2. UNE TRANSITION HORS DU §24.1 EST REFUSEE
        #  --------------------------------------------------------------
        controles += 1
        refus = _appliquer_en_python(RACINE, arguments.env_file, appartenance, "archiver")
        if "§24.1" not in refus:
            print(f"    ECHEC    `Active --> Archived` n'a pas ete refusee : {refus[:160]}")
            echecs += 1
        else:
            print("    ok       `Active --> Archived` refusee — le §24.1 n'a pas ce raccourci")

        #  --------------------------------------------------------------
        #  3. LE DEPART REVOQUE, ET LA SESSION NE REPOND PLUS
        #  --------------------------------------------------------------
        controles += 1
        rapport = _appliquer_en_python(RACINE, arguments.env_file, appartenance, "depart")
        if "sessions=1" not in rapport:
            print(f"    ECHEC    le depart n'a pas revoque 1 session : {rapport[:200]}")
            echecs += 1
        else:
            apres = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=entetes_cookie)
            if apres.statut != 401:
                print(f"    ECHEC    la session repond encore : {apres.statut} au lieu de 401")
                echecs += 1
            else:
                print("    ok       depart : 1 session revoquee, et l'API rend 401 — MESURE")

        #  --------------------------------------------------------------
        #  4. LA RESPONSABILITE EST CLOSE — §30.22, « et ROLES »
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE ends_at IS NULL), count(*) "  # noqa: S608
            "FROM framework_responsibility_assignment f "
            "JOIN person p ON p.id = f.person_id "
            f"WHERE p.email_normalized = '{adresse}'",
        )
        if code or "|" not in sortie:
            print(f"    ECHEC    lecture des responsabilites : {sortie[:180]}")
            echecs += 1
        else:
            ouvertes, total = (int(v) for v in valeur(sortie).split("|"))
            if total != 1 or ouvertes != 0:
                print(f"    ECHEC    {ouvertes} responsabilite(s) encore ouverte(s) sur {total}")
                echecs += 1
            else:
                print("    ok       la responsabilite ESM est close — §30.22, « et roles »")

        #  --------------------------------------------------------------
        #  5. L'AUDIT PORTE LA REVOCATION, AVEC SON MOTIF
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM auth_event e JOIN person p ON p.id = e.person_id "  # noqa: S608
            f"WHERE p.email_normalized = '{adresse}' AND e.event_type = 'SESSION_REVOKED' "
            f"  AND e.detail = '{REVOCATION_DEPART}'",
        )
        if code or valeur(sortie) != "1":
            print(f"    ECHEC    audit de la revocation : {sortie[:180]}")
            echecs += 1
        else:
            print(f"    ok       audit — 1 `SESSION_REVOKED` de motif `{REVOCATION_DEPART}`")

        #  --------------------------------------------------------------
        #  6. TEMOIN — L'ARCHIVAGE QUI SUIT NE TROUVE PLUS RIEN
        #  --------------------------------------------------------------
        controles += 1
        rapport = _appliquer_en_python(RACINE, arguments.env_file, appartenance, "archiver")
        if "sessions=0" not in rapport:
            print(f"    ECHEC    l'archivage a trouve des sessions a revoquer : {rapport[:200]}")
            print("             la revocation ne tenait donc PAS au depart")
            echecs += 1
        else:
            print("    ok       TEMOIN — l'archivage ne trouve plus rien : la revocation")
            print("             tient au DEPART, et non a l'archivage (§7.4, « immediatement »)")

    finally:
        for gabarit in (
            "auth_event WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "user_session WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "magic_link_request WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "admin_password_credential WHERE user_account_id IN "
            "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id WHERE p.{ou})",
            "user_account WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "framework_responsibility_assignment WHERE person_id IN "
            "(SELECT id FROM person WHERE {ou})",
            "entity_membership WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "person WHERE {ou}",
            "entity WHERE code = {code}",
            "auth_event WHERE person_id IS NULL AND created_at >= {depuis}",
        ):
            litteraux = {
                "ou": f"email_normalized LIKE '{MARQUEUR}%'",
                "code": f"'{MARQUEUR}'",
                "depuis": f"'{debut}'::timestamptz",
            }
            psql(compose, env, "DELETE FROM " + gabarit.format(**litteraux))  # noqa: S608
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles de revocation au depart, 0 echec")
    return 0


def _appliquer_en_python(
    racine: pathlib.Path, env_file: str, appartenance: str, action: str
) -> str:
    """Appeler le service dans un sous-processus, avec le role d'EXECUTION.

    **POURQUOI UN SOUS-PROCESSUS ET NON UN IMPORT.** Ce script tourne sous
    `uv run`, donc il POURRAIT importer le service. Mais il doit alors construire
    `Parametres`, ce qui exige les onze variables du `.env` -- et `T7` a montre
    qu'une variable qui ne traverse pas la frontiere de processus produit un echec
    dont le message ne nomme pas la cause. Le sous-processus recoit le fichier
    d'environnement complet, exactement comme l'API.
    """
    programme = (
        "import datetime as dt, os, sys, uuid\n"
        "sys.path.insert(0, 'apps/api')\n"
        "sys.path.insert(0, 'apps/api/tests')\n"
        "from conftest import lire_env_du_depot, VARIABLES_MINIMALES, HOTE_LOCAL\n"
        "from app.configuration.settings import Parametres\n"
        "from app.shared.database import moteur\n"
        "from app.people.services import (enregistrer_un_depart, "
        "archiver_une_appartenance, TransitionRefusee)\n"
        "env = lire_env_du_depot(); v = dict(VARIABLES_MINIMALES)\n"
        "for n in ('POSTGRES_DB','POSTGRES_USER','POSTGRES_PASSWORD',"
        "'POSTGRES_MIGRATIONS_USER','POSTGRES_MIGRATIONS_PASSWORD',"
        "'POSTGRES_RUNTIME_USER','POSTGRES_RUNTIME_PASSWORD','REDIS_PASSWORD',"
        "'MINIO_ROOT_USER','MINIO_ROOT_PASSWORD','MINIO_BUCKET','APP_SECRET_KEY'):\n"
        "    if n in env: v[n] = env[n]\n"
        "P = Parametres(**v, POSTGRES_HOST=HOTE_LOCAL, "
        "POSTGRES_PORT=int(env.get('POSTGRES_HOST_PORT','5432')), REDIS_HOST=HOTE_LOCAL, "
        "REDIS_PORT=int(env.get('REDIS_HOST_PORT','6379')), "
        "MINIO_ENDPOINT=HOTE_LOCAL+':9000')\n"
        "fn = enregistrer_un_depart if sys.argv[2] == 'depart' else archiver_une_appartenance\n"
        "try:\n"
        "    with moteur(P).begin() as cx:\n"
        "        r = fn(cx, appartenance=uuid.UUID(sys.argv[1]), "
        "instant=dt.datetime.now(tz=dt.UTC))\n"
        "    print(f'sessions={r.sessions_revoquees} liens={r.liens_invalides} "
        "closes={r.relations_closes} reserves={r.a_des_reserves}')\n"
        "except TransitionRefusee as erreur:\n"
        "    print(f'REFUS: {erreur}')\n"
    )
    execution = subprocess.run(  # noqa: S603
        [sys.executable, "-c", programme, appartenance, action],
        capture_output=True,
        text=True,
        cwd=racine,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    del env_file
    return (execution.stdout + execution.stderr).strip()


if __name__ == "__main__":
    sys.exit(main())
