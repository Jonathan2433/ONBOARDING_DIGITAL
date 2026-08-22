#!/usr/bin/env python3
"""Un jeton hors scope est-il refuse, l'expiration est-elle effective, l'appel audite ?

LOT 3, sous-etape `T10`, story `MVP-L03-US007`.

CE QUE CE CONTROLE PROUVE QUE LES TESTS NE PROUVENT PAS

  Il passe par **`make compte-de-service`**, donc par le script de
  provisionnement reel, et il lit le jeton **sur sa sortie** -- comme un exploitant
  le ferait. Les tests appellent le service directement ; ici la chaine entiere est
  exercee, y compris le fait que **le jeton n'est affiche qu'une fois**.

  Et il lit `SERVICE_TOKEN_MAX_DAYS` **dans le conteneur**, pas dans le `.env` de
  la machine : `T7` a montre qu'une variable qui ne traverse pas la frontiere de
  processus produit un echec dont le message ne nomme pas la cause.

IL PORTE SES TEMOINS

  - **le jeton legitime avec le bon scope passe** : sans ce temoin, un mecanisme qui
    refuserait tout passerait tous les refus ;
  - **le script REFUSE une duree au-dela du plafond** au lieu de l'ecreter ;
  - **le script REFUSE un proprietaire technique inconnu** au lieu de creer une
    personne.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

MARQUEUR = f"t10-verif-{uuid.uuid4().hex[:12]}"


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
    for ligne in sortie.splitlines():
        if ligne.strip():
            return ligne.strip()
    return ""


def provisionner(*arguments: str) -> tuple[int, str]:
    """Appeler `provisionner-compte-de-service.py`. Rend `(code, sortie)`."""
    execution = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(RACINE / "infra" / "scripts" / "provisionner-compte-de-service.py"),
            *arguments,
        ],
        capture_output=True,
        text=True,
        cwd=RACINE,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return execution.returncode, (execution.stdout + execution.stderr)


def jeton_de(sortie: str) -> str | None:
    """Extraire le jeton de la sortie du script. Il n'y figure QU'UNE FOIS."""
    trouves = re.findall(r"\bost_[A-Za-z0-9_-]{20,}\b", sortie)
    return trouves[0] if len(trouves) == 1 else None


def authentifier(jeton: str, scope: str, decalage_jours: int = 0) -> str:
    """Appeler le service dans un sous-processus, et rendre son motif.

    **Un sous-processus, comme en `T9`** : il recoit le fichier d'environnement
    complet, exactement comme l'API. L'instant est **injecte**, ce qui permet
    d'eprouver l'expiration sans attendre quatre-vingt-dix jours.
    """
    programme = (
        "import datetime as dt, sys\n"
        "sys.path.insert(0, 'apps/api')\n"
        "sys.path.insert(0, 'apps/api/tests')\n"
        "from conftest import lire_env_du_depot, VARIABLES_MINIMALES, HOTE_LOCAL\n"
        "from app.configuration.settings import Parametres\n"
        "from app.shared.database import moteur\n"
        "from app.auth.comptes_de_service import authentifier_un_jeton\n"
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
        "quand = dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=int(sys.argv[3]))\n"
        "with moteur(P).begin() as cx:\n"
        "    r = authentifier_un_jeton(cx, jeton=sys.argv[1], instant=quand, "
        "scope_requis=sys.argv[2])\n"
        "print(f'reussie={r.reussie} motif={r.motif}')\n"
    )
    execution = subprocess.run(  # noqa: S603
        [sys.executable, "-c", programme, jeton, scope, str(decalage_jours)],
        capture_output=True,
        text=True,
        cwd=RACINE,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return (execution.stdout + execution.stderr).strip()


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

    from app.auth.scopes import SCOPES_DU_CAHIER

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    proprietaire = f"{MARQUEUR}@{domaine}"

    print()
    print("  Comptes de service et scopes — US007, cahier §22, modele §10.5")
    print(f"    info     marqueur : {MARQUEUR}")
    print(f"    info     scopes du §22 : {', '.join(SCOPES_DU_CAHIER)}")

    echecs = 0
    controles = 0

    #  --------------------------------------------------------------
    #  0. LE PLAFOND EST-IL CELUI DU CONTENEUR ?
    #  --------------------------------------------------------------
    controles += 1
    lecture = subprocess.run(  # noqa: S603
        [*compose, "exec", "-T", "api", "printenv", "SERVICE_TOKEN_MAX_DAYS"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    plafond_conteneur = lecture.stdout.strip()
    if plafond_conteneur != env.get("SERVICE_TOKEN_MAX_DAYS", "").strip():
        print(
            f"    ECHEC    le conteneur voit `SERVICE_TOKEN_MAX_DAYS={plafond_conteneur!r}` "
            f"et le fichier {env.get('SERVICE_TOKEN_MAX_DAYS')!r} : la variable ne traverse "
            "pas la frontiere de processus"
        )
        echecs += 1
    else:
        print(f"    ok       le conteneur voit SERVICE_TOKEN_MAX_DAYS={plafond_conteneur}")
    plafond = int(plafond_conteneur or "90")

    #  L'instant de depart, pour attraper les evenements SANS ACTEUR — un jeton mal
    #  forme ou inconnu n'en designe aucun, donc aucun filtre par identite ne les
    #  atteint. Sixieme occurrence de cette lecon dans le lot.
    code, debut = psql(compose, env, "SELECT now()")
    if code or not valeur(debut):
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = valeur(debut)

    code, sortie = psql(
        compose,
        env,
        "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "  # noqa: S608
        f"VALUES ('{proprietaire}', '{proprietaire}', 'Verif', 'T10', 'active')",
    )
    if code:
        print(f"    ECHEC    proprietaire technique impossible : {sortie[:200]}")
        return 1
    print("    ok       proprietaire technique cree")

    try:
        #  --------------------------------------------------------------
        #  1. TEMOIN — LE SCRIPT REFUSE UN PROPRIETAIRE INCONNU
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = provisionner(
            "--nom",
            f"{MARQUEUR}-fantome",
            "--proprietaire",
            f"personne-qui-n-existe-pas@{domaine}",
            "--scopes",
            "people:read",
        )
        if code == 0 or "introuvable" not in sortie:
            print(f"    ECHEC    un proprietaire inconnu a ete accepte : code={code}")
            echecs += 1
        else:
            print("    ok       TEMOIN — proprietaire inconnu REFUSE, aucune personne creee")

        #  --------------------------------------------------------------
        #  2. LE SCRIPT REFUSE UNE DUREE AU-DELA DU PLAFOND
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = provisionner(
            "--nom",
            f"{MARQUEUR}-trop-long",
            "--proprietaire",
            proprietaire,
            "--scopes",
            "people:read",
            "--jours",
            str(plafond + 1),
        )
        if code == 0 or "depasse le plafond" not in sortie:
            print(f"    ECHEC    une duree de {plafond + 1} jours a ete acceptee : code={code}")
            echecs += 1
        else:
            print(f"    ok       duree de {plafond + 1} jours REFUSEE — aucune ecretation")

        #  --------------------------------------------------------------
        #  3. UN SCOPE MAL FORME EST REFUSE
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = provisionner(
            "--nom",
            f"{MARQUEUR}-mauvais-scope",
            "--proprietaire",
            proprietaire,
            "--scopes",
            "People Read",
        )
        if code == 0 or "scope invalide" not in sortie:
            print(f"    ECHEC    un scope mal forme a ete accepte : code={code}")
            echecs += 1
        else:
            print("    ok       scope mal forme REFUSE")

        #  --------------------------------------------------------------
        #  4. LE JETON EST CREE, ET IL N'APPARAIT QU'UNE FOIS
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = provisionner(
            "--nom",
            MARQUEUR,
            "--proprietaire",
            proprietaire,
            "--scopes",
            "people:read,email:send",
            "--jours",
            "30",
        )
        jeton = jeton_de(sortie)
        if code != 0 or jeton is None:
            print(f"    ECHEC    creation du jeton : code={code}, jeton unique={jeton is not None}")
            print(f"             {sortie[-300:]}")
            echecs += 1
            return 1
        print(f"    ok       jeton cree, affiche UNE seule fois ({len(jeton)} caracteres)")

        #  --------------------------------------------------------------
        #  5. TEMOIN — LE BON SCOPE PASSE
        #  --------------------------------------------------------------
        controles += 1
        verdict = authentifier(jeton, "people:read")
        if "reussie=True" not in verdict:
            print(f"    ECHEC    TEMOIN : le bon scope ne passe pas — {verdict[-200:]}")
            echecs += 1
        else:
            print("    ok       TEMOIN — le jeton legitime passe avec `people:read`")

        #  --------------------------------------------------------------
        #  6. UN JETON HORS SCOPE EST REFUSE
        #  --------------------------------------------------------------
        controles += 1
        verdict = authentifier(jeton, "people:import")
        if "reussie=False" not in verdict or "scope_manquant" not in verdict:
            print(f"    ECHEC    un jeton hors scope a passe — {verdict[-200:]}")
            echecs += 1
        else:
            print("    ok       jeton HORS SCOPE refuse (`scope_manquant`)")

        #  --------------------------------------------------------------
        #  7. L'EXPIRATION EST EFFECTIVE — TEMPS INJECTE
        #  --------------------------------------------------------------
        controles += 1
        verdict = authentifier(jeton, "people:read", decalage_jours=31)
        if "reussie=False" not in verdict:
            print(f"    ECHEC    un jeton perime a passe — {verdict[-200:]}")
            echecs += 1
        else:
            print("    ok       expiration effective a J+31 — le temps est INJECTE")

        #  --------------------------------------------------------------
        #  8. CHAQUE APPEL EST AUDITE, ET `last_used_at` SUIT
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*), count(*) FILTER (WHERE e.event_type = 'LOGIN_SUCCESS') "  # noqa: S608
            "FROM auth_event e JOIN service_account s ON s.id = e.service_account_id "
            f"WHERE s.name = '{MARQUEUR}'",
        )
        if code or "|" not in sortie:
            print(f"    ECHEC    lecture de l'audit : {sortie[:200]}")
            echecs += 1
        else:
            total, succes = (int(v) for v in valeur(sortie).split("|"))
            #  Trois appels : temoin (succes), hors scope (echec), perime (echec).
            if (total, succes) != (3, 1):
                print(f"    ECHEC    {total} evenement(s) dont {succes} succes, attendu 3 et 1")
                echecs += 1
            else:
                print("    ok       3 appels, 3 evenements, 1 succes — `service_account_id` porte")

        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE t.last_used_at IS NOT NULL), "  # noqa: S608
            "count(*) FILTER (WHERE t.token_hash ~ '^[0-9a-f]{64}$') "
            "FROM service_token t JOIN service_account s ON s.id = t.service_account_id "
            f"WHERE s.name = '{MARQUEUR}'",
        )
        if code or valeur(sortie) != "1|1":
            print(f"    ECHEC    `last_used_at` ou l'empreinte : {sortie[:200]}")
            echecs += 1
        else:
            print("    ok       `last_used_at` pose, et `token_hash` est une empreinte SHA-256")

        #  --------------------------------------------------------------
        #  10. LE JETON N'EST PAS DANS LE JOURNAL DU CONTENEUR
        #  --------------------------------------------------------------
        controles += 1
        journal = subprocess.run(  # noqa: S603
            [*compose, "logs", "--since", "10m", "api"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte = journal.stdout + journal.stderr
        if jeton in texte or jeton[len("ost_") :] in texte:
            print("    ECHEC    LE JETON FIGURE DANS LE JOURNAL DU CONTENEUR")
            echecs += 1
        else:
            print("    ok       aucun jeton dans le journal de `api`")

    finally:
        for gabarit in (
            "auth_event WHERE service_account_id IN "
            "(SELECT id FROM service_account WHERE name LIKE {motif})",
            "auth_event WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "service_token WHERE service_account_id IN "
            "(SELECT id FROM service_account WHERE name LIKE {motif})",
            "service_account WHERE name LIKE {motif}",
            "person WHERE {ou}",
            "auth_event WHERE person_id IS NULL AND service_account_id IS NULL "
            "  AND created_at >= {depuis}",
        ):
            litteraux = {
                "motif": f"'{MARQUEUR}%'",
                "ou": f"email_normalized LIKE '{MARQUEUR}%'",
                "depuis": f"'{debut}'::timestamptz",
            }
            psql(compose, env, "DELETE FROM " + gabarit.format(**litteraux))  # noqa: S608
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles de comptes de service, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
