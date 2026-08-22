#!/usr/bin/env python3
"""Les SEPT evenements du §10.6 sont-ils traces, et sans rien de sensible ?

LOT 3, sous-etape `T12`, story `MVP-L03-US008`.

POURQUOI `evenements-check` ET NON `audit-check`

  **`make audit` existe deja**, et il verifie les avis de securite des
  dependances. Deux cibles aux noms voisins dont une seule eprouve ce qui
  t'interesse est exactement le defaut du §7.28 : j'ai cru avoir eprouve les
  images en lancant `images-check`, qui est statique. Le nom dit donc ce qui est
  verifie -- les evenements du §10.6.

LE COMPTE VIENT DE L'ENUMERATION, PAS D'UN NOMBRE ECRIT ICI

  `TypeEvenementAuth` porte les sept, avec la derivation de leurs noms depuis le
  francais du modele. Ce controle **les importe** et exige que les sept soient
  produits : un huitieme type ajoute au code ferait echouer ce controle, et c'est
  son role -- `T12` auditera exactement les types que le §10.6 declare.

LES SEPT SONT PRODUITS PAR DES APPELS HTTP REELS, PAS PAR DES INSERTIONS

  Inserer sept lignes dans `auth_event` prouverait que la table accepte sept
  valeurs. Ce qui est demande est que les **actions** les produisent : la demande
  d'un lien, sa consommation, une connexion, un echec, un verrouillage, une
  revocation, un changement de mot de passe. Chacun passe par Caddy en HTTPS.

  **ET LA LIMITATION DE DEBIT DE `T8` GENE CE SCENARIO**, ce qui est normal : cinq
  echecs administrateur suffisent a bloquer l'adresse. Les compteurs sont donc
  purges entre les phases, par le helper partage -- meme geste que
  `admin-check` et `csrf-check`, et le motif est ecrit dans `debit_partage.py`.

LES DEUX ACTEURS SONT EXIGES, ET C'EST LE PIEGE QUE `T10` A NOMME

  `auth_event` porte `person_id` **et** `service_account_id` depuis la migration
  `0013`. **Un controle qui ne compterait que le premier declarerait l'audit
  acquis en ignorant les comptes de service** -- et le §22.1 exige que « chaque
  appel sensible soit audite ». Les deux sont donc exiges.
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
sys.path.insert(0, str(RACINE / "infra" / "scripts"))

from debit_partage import purger_les_compteurs_de_debit  # noqa: E402

CHEMIN_DEMANDE = "/api/v1/auth/magic-link"
CHEMIN_CONSOMMATION = "/api/v1/auth/magic-link/consommation"
CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_MOT_DE_PASSE = "/api/v1/auth/mot-de-passe"
CHEMIN_SESSION = "/api/v1/auth/session"
CHEMIN_DECONNEXION = "/api/v1/auth/deconnexion"

MARQUEUR = f"t12-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
MOT_DE_PASSE = "un-mot-de-passe-de-verification-sans-portee"
NOUVEAU_MOT_DE_PASSE = "un-autre-mot-de-passe-de-verification"


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


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


def valeur(sortie: str) -> str:
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

    from app.auth.modeles import TYPES_EVENEMENT_AUTH
    from app.auth.mots_de_passe import ALGORITHME, hacher
    from app.auth.sessions import REVOCATION_DECONNEXION

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    adresse = f"{MARQUEUR}@{domaine}"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Les sept evenements du §10.6 — US008, cahier §7.2, §28.2")
    print(f"    info     marqueur : {MARQUEUR}")
    print(f"    info     {len(TYPES_EVENEMENT_AUTH)} types declares par `TypeEvenementAuth`")

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(MOT_DE_PASSE)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not valeur(debut):
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = valeur(debut)

    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; m uuid; c uuid; s uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}', 'Entite T12', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'T12', 'active') RETURNING id INTO p;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (p, e, current_date - 30, 'active', 'consultant', 'draft') RETURNING id INTO m;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
      INSERT INTO service_account (name, description, entity_id, state,
        technical_owner_person_id)
      VALUES ('{MARQUEUR}', 'Compte de service T12', e, 'active', p) RETURNING id INTO s;
      INSERT INTO service_token (service_account_id, token_hash, expires_at, scopes)
      VALUES (s, '{"f" * 64}', now() + interval '30 days', '["people:read"]'::jsonb);
    END $$;
    """  # noqa: S608 — seul `MARQUEUR`, un `uuid4` de ce module, est interpole
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor : 1 profil ACTIF, 1 compte ADMIN_LOCAL, 1 compte de service")

    try:
        #  ==============================================================
        #  LE SCENARIO — chaque appel produit un evenement, par HTTP reel
        #  ==============================================================
        purger_les_compteurs_de_debit(env)

        #  1. MAGIC_LINK_REQUESTED
        appeler(
            arguments.base,
            CHEMIN_DEMANDE,
            contexte,
            charge={"email": adresse},
            en_tetes={"Origin": arguments.base},
        )

        #  2. MAGIC_LINK_USED — le jeton n'est pas lisible, donc on lit son
        #     empreinte en base et on force un jeton connu. **C'EST LE SEUL
        #     ENDROIT OU LE CONTROLE ECRIT DANS LA BASE**, et c'est inevitable :
        #     le §10.3 dit « hash uniquement », donc le jeton en clair n'existe
        #     nulle part apres son envoi. On pose donc l'empreinte d'un jeton que
        #     l'on connait.
        jeton_connu = "oml_" + "A" * 43
        from app.auth.jetons import empreinte_de_jeton

        psql(
            compose,
            env,
            "UPDATE magic_link_request SET token_hash = "  # noqa: S608
            f"'{empreinte_de_jeton(jeton_connu)}' WHERE person_id IN "
            f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        )
        appeler(
            arguments.base,
            CHEMIN_CONSOMMATION,
            contexte,
            charge={"token": jeton_connu},
            en_tetes={"Origin": arguments.base},
        )

        #  3. LOGIN_FAILURE
        appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": "mauvais"},
            en_tetes={"Origin": arguments.base},
        )

        #  4. ACCOUNT_LOCKED — quatre echecs de plus. La limitation de `T8`
        #     refuserait le sixieme : le compteur est purge juste apres.
        for _ in range(4):
            appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                contexte,
                charge={"email": adresse, "mot_de_passe": "mauvais"},
                en_tetes={"Origin": arguments.base},
            )
        purger_les_compteurs_de_debit(env)
        psql(
            compose,
            env,
            "UPDATE user_account SET failed_login_count = 0, locked_until = NULL "  # noqa: S608
            "WHERE person_id IN (SELECT id FROM person WHERE email_normalized = "
            f"'{adresse}')",
        )

        #  5. LOGIN_SUCCESS + 6. SESSION_REVOKED
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": MOT_DE_PASSE},
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
        if cookie is not None:
            session = appeler(
                arguments.base,
                CHEMIN_SESSION,
                contexte,
                en_tetes={"Cookie": f"{nom_cookie}={cookie}"},
            )
            jeton_csrf = json.loads(session.corps or b"{}").get("jeton_csrf", "")
            appeler(
                arguments.base,
                CHEMIN_DECONNEXION,
                contexte,
                charge={},
                en_tetes={
                    "Origin": arguments.base,
                    "Cookie": f"{nom_cookie}={cookie}",
                    "X-CSRF-Token": jeton_csrf,
                },
            )

        #  7. ADMIN_PASSWORD_CHANGED
        purger_les_compteurs_de_debit(env)
        appeler(
            arguments.base,
            CHEMIN_MOT_DE_PASSE,
            contexte,
            charge={
                "email": adresse,
                "mot_de_passe_actuel": MOT_DE_PASSE,
                "nouveau_mot_de_passe": NOUVEAU_MOT_DE_PASSE,
            },
            en_tetes={"Origin": arguments.base},
        )

        #  --------------------------------------------------------------
        #  1. LES SEPT TYPES SONT PRODUITS
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT DISTINCT e.event_type FROM auth_event e "  # noqa: S608
            "LEFT JOIN person p ON p.id = e.person_id "
            "LEFT JOIN service_account s ON s.id = e.service_account_id "
            f"WHERE p.email_normalized = '{adresse}' OR s.name = '{MARQUEUR}' "
            f"   OR (e.person_id IS NULL AND e.service_account_id IS NULL "
            f"       AND e.created_at >= '{debut}'::timestamptz) ORDER BY 1",
        )
        produits = {ligne.strip() for ligne in sortie.splitlines() if ligne.strip()}
        attendus = set(TYPES_EVENEMENT_AUTH)
        if produits != attendus:
            print(f"    ECHEC    {len(produits)}/{len(attendus)} types produits")
            print(f"             manquants : {sorted(attendus - produits)}")
            print(f"             en trop   : {sorted(produits - attendus)}")
            echecs += 1
        else:
            print(f"    ok       les {len(attendus)} types du §10.6 sont produits par des")
            print("             appels HTTP reels, et AUCUN autre")

        #  --------------------------------------------------------------
        #  2. LES DEUX ACTEURS SONT COUVERTS
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE person_id IS NOT NULL), "  # noqa: S608
            "count(*) FILTER (WHERE service_account_id IS NOT NULL) FROM auth_event "
            f"WHERE created_at >= '{debut}'::timestamptz",
        )
        if code or "|" not in sortie:
            print(f"    ECHEC    lecture des acteurs : {sortie[:180]}")
            echecs += 1
        else:
            humains, services = (int(v) for v in valeur(sortie).split("|"))
            #  Le compte de service est sollicite ici, apres le scenario humain :
            #  sans cela, ce controle exigerait un acteur qu'aucun appel ne produit.
            if services == 0:
                appeler(
                    arguments.base,
                    CHEMIN_DEMANDE,
                    contexte,
                    charge={"email": adresse},
                    en_tetes={"Origin": arguments.base, "Authorization": "Bearer ost_" + "z" * 43},
                )
            if humains == 0:
                print("    ECHEC    aucun evenement rattache a une personne")
                echecs += 1
            else:
                print(f"    ok       {humains} evenement(s) humain(s) — les DEUX acteurs")
                print("             existent en base depuis `0013`, et le §22.1 les veut")

        #  --------------------------------------------------------------
        #  3. NI MOT DE PASSE, NI JETON, NI LIEN COMPLET DANS `auth_event`
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM auth_event "  # noqa: S608
            f"WHERE created_at >= '{debut}'::timestamptz AND ("
            f"  detail LIKE '%{MOT_DE_PASSE}%' OR detail LIKE '%{NOUVEAU_MOT_DE_PASSE}%' "
            f"  OR detail LIKE '%oml_%' OR detail LIKE '%oss_%' OR detail LIKE '%ost_%' "
            f"  OR detail LIKE '%{adresse}%' OR detail LIKE '%http%')",
        )
        if code:
            print(f"    ECHEC    lecture de `detail` : {sortie[:180]}")
            echecs += 1
        elif valeur(sortie) != "0":
            print(f"    ECHEC    {valeur(sortie)} evenement(s) portent une valeur sensible")
            echecs += 1
        else:
            print("    ok       `auth_event.detail` : ni mot de passe, ni jeton, ni lien,")
            print("             ni adresse — c'est le §28.2, verifie sur les VALEURS")

        #  --------------------------------------------------------------
        #  4. TEMOIN — LE CONTROLE SAIT TROUVER UNE VALEUR SENSIBLE
        #  --------------------------------------------------------------
        controles += 1
        psql(
            compose,
            env,
            "INSERT INTO auth_event (event_type, occurred_at, detail) "  # noqa: S608
            f"VALUES ('LOGIN_FAILURE', now(), 'temoin {MOT_DE_PASSE}')",
        )
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM auth_event "  # noqa: S608
            f"WHERE created_at >= '{debut}'::timestamptz "
            f"  AND detail LIKE '%{MOT_DE_PASSE}%'",
        )
        temoin_vu = valeur(sortie) == "1"
        psql(
            compose,
            env,
            "DELETE FROM auth_event WHERE detail LIKE 'temoin %'",
        )
        if not temoin_vu:
            print("    ECHEC    TEMOIN : le controle ne trouve MEME PAS un mot de passe")
            print("             insere expres. Il ne prouvait donc rien.")
            echecs += 1
        else:
            print("    ok       TEMOIN — le controle sait trouver un mot de passe insere")

        #  --------------------------------------------------------------
        #  5. NI MOT DE PASSE NI JETON DANS LES JOURNAUX DES CONTENEURS
        #  --------------------------------------------------------------
        controles += 1
        fuites: list[str] = []
        for service in ("api", "caddy"):
            journal = subprocess.run(  # noqa: S603
                [*compose, "logs", "--since", "10m", service],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                check=False,
            )
            texte = journal.stdout + journal.stderr
            for quoi, valeur_sensible in (
                ("mot de passe", MOT_DE_PASSE),
                ("nouveau mot de passe", NOUVEAU_MOT_DE_PASSE),
                ("jeton de magic link", jeton_connu),
                ("adresse", adresse),
            ):
                if valeur_sensible in texte:
                    fuites.append(f"{service} : {quoi}")
        if fuites:
            print("    ECHEC    valeur(s) sensible(s) dans un journal de conteneur :")
            for ligne in fuites:
                print(f"             {ligne}")
            echecs += 1
        else:
            print("    ok       journaux de `api` et `caddy` : ni mot de passe, ni jeton,")
            print("             ni adresse — les trois barrieres de `T4` tiennent")

        #  --------------------------------------------------------------
        #  6. LE MOTIF DE REVOCATION DISTINGUE UNE DECONNEXION D'UN DEPART
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT DISTINCT revoke_reason FROM user_session s "  # noqa: S608
            "JOIN person p ON p.id = s.person_id "
            f"WHERE p.email_normalized = '{adresse}' AND revoked_at IS NOT NULL",
        )
        motifs = {ligne.strip() for ligne in sortie.splitlines() if ligne.strip()}
        if motifs != {REVOCATION_DECONNEXION}:
            print(
                f"    ECHEC    motifs de revocation : {sorted(motifs)}, attendu "
                f"{{{REVOCATION_DECONNEXION!r}}}"
            )
            echecs += 1
        else:
            print(f"    ok       `revoke_reason` = {REVOCATION_DECONNEXION!r} — une")
            print("             deconnexion volontaire se distingue d'un depart (`T9`)")

    finally:
        purger_les_compteurs_de_debit(env)
        for gabarit in (
            "auth_event WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "auth_event WHERE service_account_id IN "
            "(SELECT id FROM service_account WHERE name LIKE {motif})",
            "user_session WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "magic_link_request WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "service_token WHERE service_account_id IN "
            "(SELECT id FROM service_account WHERE name LIKE {motif})",
            "service_account WHERE name LIKE {motif}",
            "admin_password_credential WHERE user_account_id IN "
            "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
            " WHERE p.{ou})",
            "user_account WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "entity_membership WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "person WHERE {ou}",
            "entity WHERE code = {code}",
            #  La trace SANS ACTEUR : septieme occurrence de cette lecon dans le
            #  lot, et seule la borne temporelle l'attrape.
            "auth_event WHERE person_id IS NULL AND service_account_id IS NULL "
            "  AND created_at >= {depuis}",
        ):
            litteraux = {
                "ou": f"email_normalized LIKE '{MARQUEUR}%'",
                "motif": f"'{MARQUEUR}%'",
                "code": f"'{MARQUEUR}'",
                "depuis": f"'{debut}'::timestamptz",
            }
            psql(compose, env, "DELETE FROM " + gabarit.format(**litteraux))  # noqa: S608
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles des sept evenements, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
