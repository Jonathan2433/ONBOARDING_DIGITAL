#!/usr/bin/env python3
"""Une ecriture sans protection est-elle refusee, et une cle rejouee sans effet ?

LOT 3, sous-etape `T7`, story `MVP-L03-US005`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE EN PLUS DES TESTS

  Le critere du §3 de la fiche : « une ecriture sans jeton CSRF est **refusee**,
  avec temoin · une meme cle d'idempotence rejouee ne produit **qu'un** effet ».

  Les tests d'integration montent l'application en processus. Ici on interroge
  l'API REELLE a travers Caddy en HTTPS, et cela change quelque chose de precis :
  **`PUBLIC_BASE_URL` est la vraie**, celle du conteneur. Un test qui la surcharge
  ne prouve rien de la configuration deployee, et `T3` a montre que cette variable
  n'avait jamais ete exercee.

IL PORTE SES DEUX TEMOINS

  Une protection qui refuserait TOUT passerait tous les tests de refus. Les deux
  cas legitimes sont donc exiges :

    - la meme ecriture, depuis la BONNE origine, doit passer ;
    - deux demandes SANS cle doivent produire DEUX liens -- sinon l'assertion
      « une seule » du test d'idempotence serait vraie pour une raison etrangere.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
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

EN_TETE_JETON = "X-CSRF-Token"
EN_TETE_CLE = "Idempotency-Key"

MARQUEUR = f"t7-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION. Pas de shell — §7.2.

    **SUR LES `# noqa: S608`.** La seule valeur interpolee est `adresse`,
    construite ici depuis `MARQUEUR` (`uuid4`) et un domaine du fichier
    d'environnement. Aucune entree de tiers, et `psql` n'accepte pas de
    parametres lies.
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
    methode: str | None = None,
) -> Reponse:
    """Appeler l'API. Rend la reponse MEME sur un code d'erreur."""
    entetes = {"Content-Type": "application/json"} if charge is not None else {}
    entetes.update(en_tetes or {})
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method=methode or ("POST" if charge is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), list(reponse.headers.items()))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), list(erreur.headers.items()))


def _cookie(pose: list[str], nom: str) -> str | None:
    for entree in pose:
        trouve = re.match(rf"{re.escape(nom)}=([^;]+)", entree)
        if trouve:
            return trouve.group(1)
    return None


def _liens_en_base(compose: list[str], env: dict[str, str], adresse: str) -> tuple[int, int]:
    """`(total, actifs)` des liens de cette adresse."""
    code, sortie = psql(
        compose,
        env,
        "SELECT count(*), count(*) FILTER (WHERE m.used_at IS NULL "  # noqa: S608
        "  AND m.invalidated_at IS NULL) "
        "FROM magic_link_request m JOIN person p ON p.id = m.person_id "
        f"WHERE p.email_normalized = '{adresse}'",
    )
    if code or "|" not in sortie:
        return (-1, -1)
    total, actifs = sortie.strip().split("|")
    return int(total), int(actifs)


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
    print("  CSRF et idempotence — US005, cahier §7.4, §18.6, §20.1")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0

    from app.auth.mots_de_passe import ALGORITHME, hacher

    empreinte, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not debut.strip():
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = debut.splitlines()[0].strip()

    #  Le decor : une personne ACTIVE avec appartenance active — sinon aucun lien
    #  ne serait emis, et les controles d'idempotence passeraient pour la
    #  mauvaise raison — plus un compte administrateur pour la deconnexion.
    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; c uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}', 'Entite T7', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'T7', 'active') RETURNING id INTO p;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (p, e, current_date - 30, 'active', 'consultant', 'draft');
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
    END $$;
    """  # noqa: S608 — voir la justification en tete de `psql`
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor cree : 1 entite, 1 profil ACTIF, 1 compte ADMIN_LOCAL")

    ecritures = {
        CHEMIN_DEMANDE: {"email": adresse},
        CHEMIN_CONSOMMATION: {"token": "oml_" + "z" * 43},
        CHEMIN_CONNEXION: {"email": adresse, "mot_de_passe": mot_de_passe},
        CHEMIN_MOT_DE_PASSE: {
            "email": adresse,
            "mot_de_passe_actuel": mot_de_passe,
            "nouveau_mot_de_passe": "un-autre-mot-de-passe-valide",
        },
        CHEMIN_DECONNEXION: {},
    }

    try:
        #  --------------------------------------------------------------
        #  1. UNE ORIGINE ETRANGERE EST REFUSEE, SUR LES CINQ ECRITURES
        #  --------------------------------------------------------------
        controles += 1
        refusees = {
            chemin: appeler(
                arguments.base,
                chemin,
                contexte,
                charge=corps,
                en_tetes={"Origin": "https://mechant.example"},
            )
            for chemin, corps in ecritures.items()
        }
        mauvaises = [c for c, r in refusees.items() if r.statut != 403]
        if len(refusees) != 5:
            print(f"    ECHEC    {len(refusees)} ecritures exercees au lieu de 5")
            echecs += 1
        elif mauvaises:
            print("    ECHEC    ecriture(s) NON refusee(s) depuis une origine etrangere :")
            for chemin in mauvaises:
                print(f"             {chemin} -> {refusees[chemin].statut}")
            echecs += 1
        else:
            print("    ok       les 5 ecritures sont refusees (403) depuis une origine etrangere")

        #  Les trois causes de refus doivent etre indistinguables.
        controles += 1
        corps_distincts = set()
        for reponse in refusees.values():
            charge = json.loads(reponse.corps)
            charge.get("erreur", {}).pop("identifiant_correlation", None)
            corps_distincts.add(json.dumps(charge, sort_keys=True))
        if len(corps_distincts) != 1:
            print(f"    ECHEC    les refus CSRF sont distinguables : {corps_distincts}")
            echecs += 1
        else:
            print("    ok       un seul gabarit de refus, hors identifiant de correlation")

        #  --------------------------------------------------------------
        #  2. TEMOIN : les memes ecritures passent depuis la BONNE origine
        #  --------------------------------------------------------------
        controles += 1
        bonnes = {
            chemin: appeler(
                arguments.base,
                chemin,
                contexte,
                charge=ecritures[chemin],
                en_tetes={"Origin": arguments.base},
            )
            #  La deconnexion est exclue : elle exige un JETON des qu'une session
            #  existe, et c'est l'objet du controle 4. L'inclure ici la ferait
            #  echouer a juste titre — defaut mesure en `T7`.
            for chemin in (CHEMIN_DEMANDE, CHEMIN_CONSOMMATION, CHEMIN_CONNEXION)
        }
        refusees_a_tort = [c for c, r in bonnes.items() if r.statut == 403]
        if refusees_a_tort:
            print(
                f"    ECHEC    TEMOIN : refusees a tort depuis la bonne origine : {refusees_a_tort}"
            )
            echecs += 1
        else:
            print(
                f"    ok       TEMOIN — les {len(bonnes)} memes ecritures passent depuis "
                "la bonne origine"
            )

        #  --------------------------------------------------------------
        #  3. SANS EN-TETE `Origin` : accepte, et c'est declare
        #  --------------------------------------------------------------
        controles += 1
        nue = appeler(arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": adresse})
        if nue.statut == 403:
            print("    ECHEC    une requete SANS `Origin` est refusee — `curl` et les")
            print("             sondes casseraient, sans rien apporter")
            echecs += 1
        else:
            print(f"    ok       sans `Origin` : accepte ({nue.statut}) — choix declare,")
            print("             le CSRF est une attaque de NAVIGATEUR")

        #  --------------------------------------------------------------
        #  4. LA DECONNEXION EXIGE UN JETON QUAND UNE SESSION EXISTE
        #  --------------------------------------------------------------
        controles += 1
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
            en_tetes={"Origin": arguments.base},
        )
        cookie = _cookie(connexion.cookies_poses, nom_cookie)
        if connexion.statut != 200 or not cookie:
            print(f"    ECHEC    connexion impossible : {connexion.statut}")
            echecs += 1
        else:
            entetes_session = {"Origin": arguments.base, "Cookie": f"{nom_cookie}={cookie}"}
            sans_jeton = appeler(
                arguments.base, CHEMIN_DECONNEXION, contexte, charge={}, en_tetes=entetes_session
            )
            session = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=entetes_session)
            jeton = json.loads(session.corps).get("jeton_csrf") if session.statut == 200 else None
            avec_jeton = appeler(
                arguments.base,
                CHEMIN_DECONNEXION,
                contexte,
                charge={},
                en_tetes={**entetes_session, EN_TETE_JETON: jeton or ""},
            )
            apres = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=entetes_session)
            if sans_jeton.statut != 403:
                print(
                    "    ECHEC    la deconnexion passe SANS jeton alors qu'une session "
                    f"existe : {sans_jeton.statut}"
                )
                echecs += 1
            elif avec_jeton.statut != 200:
                print(f"    ECHEC    la deconnexion echoue AVEC le jeton : {avec_jeton.statut}")
                echecs += 1
            elif apres.statut != 401:
                print(f"    ECHEC    la session survit a la deconnexion : {apres.statut}")
                echecs += 1
            else:
                print("    ok       deconnexion — 403 sans jeton, 200 avec, session revoquee")

            #  Un jeton d'une AUTRE session doit etre refuse : c'est la liaison a
            #  la session qui rend le double envoi solide.
            controles += 1
            reconnexion = appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                contexte,
                charge={"email": adresse, "mot_de_passe": mot_de_passe},
                en_tetes={"Origin": arguments.base},
            )
            second_cookie = _cookie(reconnexion.cookies_poses, nom_cookie)
            etranger = appeler(
                arguments.base,
                CHEMIN_DECONNEXION,
                contexte,
                charge={},
                en_tetes={
                    "Origin": arguments.base,
                    "Cookie": f"{nom_cookie}={second_cookie}",
                    #  Le jeton de la session PRECEDENTE, deja revoquee.
                    EN_TETE_JETON: jeton or "",
                },
            )
            if etranger.statut != 403:
                print(f"    ECHEC    un jeton d'une AUTRE session est accepte : {etranger.statut}")
                echecs += 1
            else:
                print("    ok       un jeton d'une AUTRE session est refuse (403)")

        #  --------------------------------------------------------------
        #  5. L'IDEMPOTENCE : une meme cle ne produit qu'un effet
        #  --------------------------------------------------------------
        #  On repart d'une base propre pour cette adresse : les controles
        #  precedents ont pu emettre des liens.
        psql(
            compose,
            env,
            "DELETE FROM magic_link_request WHERE person_id IN "  # noqa: S608
            f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        )
        # LE COMPTEUR DE `T8` EST EFFACE AVEC LES LIGNES, ET C'EST UN CORRECTIF
        #
        #   Ce controle repart d'un etat connu en supprimant les liens en base. Il
        #   ne suffit plus : depuis `T8`, une onzieme demande sur la meme adresse
        #   est refusee par la limitation, et ce verificateur en fait une dizaine
        #   avant d'arriver ici. Les deux controles d'idempotence ont donc echoue
        #   sur un livrable conforme -- « 0 lien(s) au lieu de 1 » -- parce que le
        #   429 n'emet aucun lien. C'est le §7.21.
        #
        #   Un etat connu n'est plus seulement une table vide : c'est une table
        #   vide ET un compteur remis a zero. La limitation a son propre controle,
        #   `make debit-check`.
        purger_les_compteurs_de_debit(env)
        controles += 1
        cle = f"t7-{uuid.uuid4().hex}"
        entetes_cle = {"Origin": arguments.base, EN_TETE_CLE: cle}
        premiere = appeler(
            arguments.base,
            CHEMIN_DEMANDE,
            contexte,
            charge={"email": adresse},
            en_tetes=entetes_cle,
        )
        seconde = appeler(
            arguments.base,
            CHEMIN_DEMANDE,
            contexte,
            charge={"email": adresse},
            en_tetes=entetes_cle,
        )
        total, actifs = _liens_en_base(compose, env, adresse)
        if premiere.statut != 202 or seconde.statut != 202:
            print(f"    ECHEC    codes {premiere.statut} et {seconde.statut} au lieu de 202")
            echecs += 1
        elif premiere.corps != seconde.corps:
            print("    ECHEC    la seconde reponse differe de la premiere")
            echecs += 1
        elif (total, actifs) != (1, 1):
            print(f"    ECHEC    {total} lien(s) dont {actifs} actif(s) au lieu de 1 et 1")
            echecs += 1
        else:
            print("    ok       meme cle rejouee — 1 SEUL lien en base, meme reponse")

        #  --------------------------------------------------------------
        #  6. TEMOIN : SANS cle, deux demandes produisent DEUX liens
        #  --------------------------------------------------------------
        #  Sans ce temoin, l'assertion « un seul lien » serait vraie pour une
        #  raison etrangere a l'idempotence.
        psql(
            compose,
            env,
            "DELETE FROM magic_link_request WHERE person_id IN "  # noqa: S608
            f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        )
        # LE COMPTEUR DE `T8` EST EFFACE AVEC LES LIGNES, ET C'EST UN CORRECTIF
        #
        #   Ce controle repart d'un etat connu en supprimant les liens en base. Il
        #   ne suffit plus : depuis `T8`, une onzieme demande sur la meme adresse
        #   est refusee par la limitation, et ce verificateur en fait une dizaine
        #   avant d'arriver ici. Les deux controles d'idempotence ont donc echoue
        #   sur un livrable conforme -- « 0 lien(s) au lieu de 1 » -- parce que le
        #   429 n'emet aucun lien. C'est le §7.21.
        #
        #   Un etat connu n'est plus seulement une table vide : c'est une table
        #   vide ET un compteur remis a zero. La limitation a son propre controle,
        #   `make debit-check`.
        purger_les_compteurs_de_debit(env)
        controles += 1
        for _ in range(2):
            appeler(
                arguments.base,
                CHEMIN_DEMANDE,
                contexte,
                charge={"email": adresse},
                en_tetes={"Origin": arguments.base},
            )
        total, actifs = _liens_en_base(compose, env, adresse)
        if (total, actifs) != (2, 1):
            print(
                f"    ECHEC    TEMOIN : {total} lien(s) dont {actifs} actif(s) au lieu "
                "de 2 et 1 — le controle precedent ne prouve rien"
            )
            echecs += 1
        else:
            print("    ok       TEMOIN — sans cle, 2 liens dont 1 actif (§10.3)")

        #  --------------------------------------------------------------
        #  7. UNE CLE MALFORMEE REND 422
        #  --------------------------------------------------------------
        controles += 1
        malformee = appeler(
            arguments.base,
            CHEMIN_DEMANDE,
            contexte,
            charge={"email": adresse},
            en_tetes={"Origin": arguments.base, EN_TETE_CLE: "court"},
        )
        if malformee.statut != 422:
            print(f"    ECHEC    une cle malformee rend {malformee.statut} au lieu de 422")
            echecs += 1
        else:
            print("    ok       cle malformee — 422, ne depend QUE de la requete")

        #  --------------------------------------------------------------
        #  8. LA ROUTE DE SESSION N'EXIGE AUCUN JETON — residuel nomme
        #  --------------------------------------------------------------
        controles += 1
        reconnexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
            en_tetes={"Origin": arguments.base},
        )
        troisieme = _cookie(reconnexion.cookies_poses, nom_cookie)
        lecture = appeler(
            arguments.base,
            CHEMIN_SESSION,
            contexte,
            en_tetes={
                "Origin": "https://mechant.example",
                "Cookie": f"{nom_cookie}={troisieme}",
            },
        )
        if lecture.statut != 200:
            print(
                f"    ECHEC    la route de session refuse ({lecture.statut}) alors qu'elle "
                "ne doit exiger aucun jeton"
            )
            echecs += 1
        else:
            print("    ok       la route de session n'exige aucun jeton — RESIDUEL NOMME :")
            print("             elle ECRIT (elle rafraichit l'activite) mais c'est elle")
            print("             qui DELIVRE le jeton, donc l'exiger serait circulaire.")
            print("             A reexaminer au LOT 4. Voir `routes.py`.")

    finally:
        _nettoyer(compose, env, adresse, debut)

    print()
    print(f"  controles executes : {controles}   echecs : {echecs}")
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print("  --> les ecritures sont protegees, et une cle rejouee ne produit qu'un effet")
    return 0


def _nettoyer(compose: list[str], env: dict[str, str], adresse: str, debut: str) -> None:
    """Retirer TOUT ce que ce controle a cree, dans l'ordre des cles etrangeres.

    La liste comprend `user_session` -- ajoutee par `T6` -- et
    `entity_membership`. **Ecrire un nettoyage complet est plus difficile qu'il
    n'y parait** : cinq nettoyages ont ete corriges en `T6` pour l'avoir oubliee.
    """
    etapes = (
        "DELETE FROM auth_event WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        #  LOT 10, `T2` : `audit_event.actor_person_id` reference aussi `person`.
        "DELETE FROM audit_event WHERE actor_person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM user_session WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM magic_link_request WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM admin_password_credential WHERE user_account_id IN "  # noqa: S608
        "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
        f" WHERE p.email_normalized = '{adresse}')",
        "DELETE FROM user_account WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM entity_membership WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        f"DELETE FROM person WHERE email_normalized = '{adresse}'",  # noqa: S608
        #  LOT 10, `T3` : `audit_event.entity_id` reference aussi `entity` --
        #  les ecritures sur les personnes/l'organisation portent desormais
        #  l'entite, jamais seulement l'acteur.
        f"DELETE FROM audit_event WHERE entity_id IN "  # noqa: S608
        f"(SELECT id FROM entity WHERE code = '{MARQUEUR}')",
        f"DELETE FROM entity WHERE code = '{MARQUEUR}'",  # noqa: S608
        f"DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= '{debut}'",  # noqa: S608
        f"DELETE FROM audit_event WHERE actor_person_id IS NULL AND created_at >= '{debut}'",  # noqa: S608
    )
    restes = 0
    for requete in etapes:
        code, sortie = psql(compose, env, requete)
        if code:
            restes += 1
            print(f"    SIGNALE  nettoyage incomplet : {sortie[:160]}")
    if not restes:
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")


if __name__ == "__main__":
    sys.exit(main())
