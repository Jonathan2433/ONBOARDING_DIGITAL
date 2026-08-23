#!/usr/bin/env python3
"""La page nationale ne propose-t-elle QUE des entites actives ?

LOT 4, sous-etape `T1`, story `MVP-L04-US001`.

CE QUE CE CONTROLE PROUVE QUE LES TESTS NE PROUVENT PAS

  Les tests d'integration montent l'application EN PROCESSUS. Ici la session est
  ouverte par une **vraie connexion a travers Caddy en HTTPS**, et la liste est
  lue par un **aller-retour HTTP reel** sur l'API du conteneur.

  C'est la distinction du §7.28 : « une entite filtree en base » et « une entite
  filtree POUR L'APPELANT » sont deux grandeurs differentes tant qu'on n'a pas
  interroge l'API qui tourne.

IL EXAMINE LES QUATRE ETATS, ET IL DIT COMBIEN

  `StatutEntite` en declare quatre. Le critere de la fiche n'en nomme que deux --
  `suspended` et `archived` -- ce sont des **exemples**. Le controle derive la
  liste de l'enumeration, cree une entite par etat, et **annonce le nombre
  d'etats examines** : si un lot ajoute un cinquieme statut, le compte change et
  le controle le dit. §7.0 troisieme proposition, et §7.34.

SES TEMOINS

  - **la connexion REUSSIT et pose un cookie** : sans ce temoin, un cookie casse
    donnerait la meme observation qu'un filtrage qui fonctionne -- une liste vide ;
  - **l'entite ACTIVE est rendue** : sans elle, les trois exclusions seraient
    satisfaites par une route qui ne rend jamais rien ;
  - **les deux refus sont COMPARES**, corps et en-tetes, correlation FIXEE. Fixer
    vaut mieux qu'exclure un champ : une exclusion laisse la porte ouverte a une
    difference cachee dans le champ exclu.
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
CHEMIN_ENTITES = "/api/v1/entities"

MARQUEUR = f"t1l4-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
CHAMPS_ATTENDUS = frozenset({"id", "code", "nom", "ville"})
CORRELATION_FIXE = "l4t1-egalite-des-refus"

#  **LE SEUL EN-TETE QUI NE PEUT PAS ETRE EGAL, ET IL EST NOMME EN SORTIE.**
#
#  Mon controle a d'abord echoue sur un livrable CONFORME : a travers Caddy, une
#  reponse HTTP reelle porte un en-tete `date`, qui change d'une requete a
#  l'autre. Le test en processus, lui, comparait tout sans exclusion -- le client
#  de test n'ajoute pas de `date`.
#
#  Trois reactions possibles, une seule est bonne (§7.20) : supprimer le controle
#  perdrait l'information ; le rabattre sur le seul corps ne prouverait plus rien
#  des en-tetes ; **lui faire dire le vrai** est ce qui est retenu. Il exige donc
#  l'egalite de tout le reste -- `x-request-id` compris, puisque la correlation
#  est fixee -- et il ANNONCE ce qu'il n'a pas compare.
#
#  L'horloge n'est pas un oracle : elle ne dit rien de l'existence d'un jeton.
EN_TETES_NON_COMPARABLES = frozenset({"date"})


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur_lue = ligne.partition("=")
            valeurs[cle.strip()] = valeur_lue.strip()
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
        self.en_tetes = {nom.lower(): v for nom, v in en_tetes}
        self.cookies_poses = [v for nom, v in en_tetes if nom.lower() == "set-cookie"]

    def json(self) -> object:
        try:
            return json.loads(self.corps)
        except ValueError:
            return None

    def signature(self) -> tuple[int, object, dict[str, str]]:
        """Ce que l'appelant observe, hors horloge — voir `EN_TETES_NON_COMPARABLES`."""
        comparables = {
            nom: v for nom, v in self.en_tetes.items() if nom not in EN_TETES_NON_COMPARABLES
        }
        return self.statut, self.json(), comparables


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
    from app.entities.modeles import STATUTS_ENTITE, StatutEntite

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
    print("  Portail national : les entites ACTIVES seulement — US001, cahier §8.3")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(
        f"    info     {len(STATUTS_ENTITE)} etats declares par le modele : "
        f"{', '.join(STATUTS_ENTITE)}"
    )

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not valeur(debut):
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = valeur(debut)

    #  Une entite PAR ETAT, la liste derivee de l'enumeration et non recopiee.
    inserts = "\n".join(
        #  S608 : les deux seules valeurs interpolees sont `MARQUEUR`, un `uuid4`
        #  de ce module, et `statut`, qui vient de `STATUTS_ENTITE` -- une
        #  enumeration du code, pas une entree. `psql` n'accepte pas de parametre
        #  lie dans un bloc `DO`, d'ou l'interpolation.
        f"      INSERT INTO entity (code, display_name, city, country_code, status, timezone) "  # noqa: S608
        f"VALUES ('{MARQUEUR}-{statut}', 'Entite {statut} {MARQUEUR}', 'Bordeaux', 'FR', "
        f"'{statut}', 'Europe/Paris');"
        for statut in STATUTS_ENTITE
    )
    decor = f"""
    DO $$
    DECLARE p uuid; c uuid;
    BEGIN
{inserts}
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'L4T1', 'active') RETURNING id INTO p;
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
    print(f"    ok       decor : {len(STATUTS_ENTITE)} entites, une par etat, + un admin local")

    try:
        # --- 1. sans cookie : la matrice met `ANON` a tiret
        controles += 1
        sans = appeler(
            arguments.base,
            CHEMIN_ENTITES,
            contexte,
            en_tetes={"X-Request-ID": CORRELATION_FIXE},
        )
        if sans.statut == 401:
            print("    ok       sans cookie : 401 — matrice §5, `ANON` est a tiret")
        else:
            echecs += 1
            print(f"    ECHEC    sans cookie : {sans.statut} au lieu de 401")

        # --- 2. TEMOIN : la connexion reussit et pose un cookie
        controles += 1
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        cookie = ""
        for pose in connexion.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                cookie = pose.split(";")[0]
        if connexion.statut == 200 and cookie:
            print("    ok       TEMOIN : la connexion reussit et pose un cookie de session")
        else:
            echecs += 1
            print(
                f"    ECHEC    TEMOIN : connexion {connexion.statut}, cookie "
                f"{'pose' if cookie else 'ABSENT'} — sans lui, une liste vide serait "
                f"indistinguable d'un filtrage correct"
            )
            raise RuntimeError("sans session, les controles suivants ne prouveraient rien")

        entetes_session = {"Cookie": cookie}

        # --- 3. avec cookie : 200
        controles += 1
        liste = appeler(arguments.base, CHEMIN_ENTITES, contexte, en_tetes=entetes_session)
        if liste.statut != 200:
            echecs += 1
            print(f"    ECHEC    avec cookie : {liste.statut} au lieu de 200")
            raise RuntimeError("la liste n'a pas repondu")
        charge = liste.json()
        if not isinstance(charge, dict) or not isinstance(charge.get("entites"), list):
            echecs += 1
            print(f"    ECHEC    la charge utile n'a pas la forme attendue : {liste.corps[:160]!r}")
            raise RuntimeError("forme inattendue")
        rendus = {e.get("code") for e in charge["entites"]}
        print(f"    ok       avec cookie : 200, {len(charge['entites'])} entite(s) rendue(s)")

        # --- 4. TEMOIN CENTRAL : l'active est rendue
        controles += 1
        if f"{MARQUEUR}-{StatutEntite.ACTIVE.value}" in rendus:
            print("    ok       TEMOIN : l'entite ACTIVE est rendue")
        else:
            echecs += 1
            print(
                "    ECHEC    TEMOIN : l'entite ACTIVE n'est PAS rendue — les exclusions "
                "ci-dessous ne prouveraient rien"
            )

        # --- 5. les etats NON ACTIFS sont absents, tous, derives de l'enumeration
        non_actifs = [s for s in STATUTS_ENTITE if s != StatutEntite.ACTIVE.value]
        for statut in non_actifs:
            controles += 1
            if f"{MARQUEUR}-{statut}" in rendus:
                echecs += 1
                print(f"    ECHEC    une entite `{statut}` est proposee sur la page nationale")
            else:
                print(f"    ok       aucune entite `{statut}` — cahier §8.3, « entite ACTIVE »")
        print(
            f"    info     {len(non_actifs)} etats non actifs examines, "
            f"non les 2 que la fiche nomme — §7.34"
        )

        # --- 6. exactement quatre champs
        controles += 1
        notre = next(
            (e for e in charge["entites"] if e.get("code") == f"{MARQUEUR}-active"),
            None,
        )
        if notre is not None and set(notre) == CHAMPS_ATTENDUS:
            print("    ok       exactement 4 champs : id, code, nom, ville — ni `status`, ni")
            print("             `timezone`, ni `country_code`")
        else:
            echecs += 1
            print(f"    ECHEC    champs rendus : {sorted(notre) if notre else 'entite absente'}")

        # --- 7. la reponse n'est pas mise en cache
        controles += 1
        if liste.en_tetes.get("cache-control") == "no-store":
            print("    ok       `Cache-Control: no-store` — Caddy est devant")
        else:
            echecs += 1
            print(f"    ECHEC    cache-control : {liste.en_tetes.get('cache-control')!r}")

        # --- 8. les deux refus sont IDENTIQUES, corps ET en-tetes
        controles += 1
        inconnu = appeler(
            arguments.base,
            CHEMIN_ENTITES,
            contexte,
            en_tetes={
                "X-Request-ID": CORRELATION_FIXE,
                "Cookie": f"{nom_cookie}=oss_{'0' * 43}",
            },
        )
        if sans.statut != 401 or inconnu.statut != 401:
            echecs += 1
            print(
                f"    ECHEC    l'egalite serait vide de sens : sans={sans.statut} "
                f"inconnu={inconnu.statut}, il faut 401 des deux cotes"
            )
        elif sans.signature() == inconnu.signature():
            print("    ok       cookie absent et jeton inconnu : reponses IDENTIQUES,")
            print("             statut, corps ET en-tetes, correlation FIXEE")
            print(
                f"             non compare : {', '.join(sorted(EN_TETES_NON_COMPARABLES))} "
                f"— l'horloge, qui ne dit rien de l'existence d'un jeton"
            )
        else:
            echecs += 1
            print("    ECHEC    les deux refus diffirent :")
            statut_a, corps_a, entetes_a = sans.signature()
            statut_b, corps_b, entetes_b = inconnu.signature()
            if statut_a != statut_b:
                print(f"             statut : {statut_a} != {statut_b}")
            if corps_a != corps_b:
                print(f"             corps  : {str(corps_a)[:130]}")
                print(f"                      {str(corps_b)[:130]}")
            #  **NOMMER L'EN-TETE FAUTIF, un par un.** Ma premiere version
            #  affichait les deux dictionnaires tronques a 110 caracteres : le
            #  message ne disait PAS lequel differait, et c'est le §7.18 -- la
            #  premiere correction a ecrire est celle qui te dira pourquoi.
            for nom in sorted(set(entetes_a) | set(entetes_b)):
                if entetes_a.get(nom) != entetes_b.get(nom):
                    print(
                        f"             en-tete `{nom}` : {entetes_a.get(nom)!r} "
                        f"!= {entetes_b.get(nom)!r}"
                    )

    except RuntimeError as arret:
        print(f"    info     arret : {arret}")
    finally:
        for gabarit in (
            "auth_event WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "user_session WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "admin_password_credential WHERE user_account_id IN "
            "(SELECT id FROM user_account WHERE person_id IN (SELECT id FROM person WHERE {ou}))",
            "user_account WHERE person_id IN (SELECT id FROM person WHERE {ou})",
            "person WHERE {ou}",
            "entity WHERE code LIKE '{prefixe}%'",
            #  Le refus SANS ACTEUR — un appel sans cookie — n'a ni personne ni
            #  compte de service : aucun filtre par identite ne l'attrape. §7.30.
            "auth_event WHERE person_id IS NULL AND service_account_id IS NULL "
            "  AND created_at >= {depuis}",
        ):
            litteraux = {
                "ou": f"email_normalized LIKE '{MARQUEUR}%'",
                "prefixe": MARQUEUR,
                "depuis": f"'{debut}'::timestamptz",
            }
            psql(compose, env, "DELETE FROM " + gabarit.format(**litteraux))  # noqa: S608
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles du portail national, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
