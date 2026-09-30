#!/usr/bin/env python3
"""Le catalogue, les modeles et le suivi de l'onboarding, sur la pile REELLE.

LOT 7, sous-etape `T14`, stories `MVP-L07-US003` et `US008`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI PYTEST NE LE PROUVE PAS DEJA

  `test_modeles_onboarding.py` (48 tests) eprouve chaque regle de la matrice §9
  via `TestClient` — la meme application Python, en memoire. Ce controle-ci
  passe par CADDY, en HTTPS, sur les conteneurs REELLEMENT en marche : c'est la
  seule maniere de prouver que le mandatement (`DEC-470`), le conteneur `api`
  a jour (`make code-refresh`) et les cookies `Secure`/`SameSite` du LOT 3 sont
  tous en jeu en meme temps — §7.28, une cible statique ne prouve rien de ce
  qu'un conteneur sert reellement.

  **`T13` avait explicitement DIFFERE ce script**, decision de Jonathan :
  combiner sa preuve avec celle de `T14` plutot que d'en ecrire deux
  d'affilee. Il couvre donc les DEUX ecrans de la rubrique « Administration »
  — mais pas « Mon onboarding » (`T13`), deja prouvee par un aller-retour reel
  au navigateur (§7.43) dans son propre compte rendu.

L'ASYMETRIE DSM/ESM EST LE TEMOIN CENTRAL

  Le §9 dit qu'un DSM ne gere que SES modeles, un ESM tous ceux de l'entite.
  Un controle qui ne poserait qu'un role verrait la meme reponse — vide, ou
  pleine — quel que soit le defaut. Ce script pose donc les DEUX roles, dans
  la MEME entite, et prouve que chacun voit un ensemble DIFFERENT — §7.0,
  quatrieme proposition.

LE CYCLE DE VIE COMPLET EST EXERCE UNE FOIS, EN VRAI, PAS SIMULE

  Creer -> composer les taches -> publier -> archiver -> restaurer. Chaque
  transition change le code HTTP attendu de la suivante (`draft` publie,
  `published` archive, `retired` restaure) — un service qui resterait bloque
  sur un etat produirait un ECHEC visible a l'etape suivante, jamais un succes
  muet.

LA RESTAURATION EST REFUSEE A UN DSM, MEME SUR SON PROPRE MODELE

  `ECART-066` resolu : DSM et BOOSTER sont exclus EN BLOC de cette seule ligne
  du §9, contrairement aux cinq autres gestes de la meme grille ou ils gerent
  LEUR PROPRE modele. Le decor cree donc explicitement ce cas — DSM proprietaire
  ET version archivee — pour que le refus ne soit pas confondu avec un refus
  d'acces plus large.
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

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_MODELES = "/api/v1/entities/{code}/onboarding/templates"
CHEMIN_VERSIONS = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions"
CHEMIN_TACHES = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/tasks"
CHEMIN_PUBLICATION = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/publication"
)
CHEMIN_ARCHIVAGE = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/archivage"
)
CHEMIN_RESTAURATION = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/restauration"
)
CHEMIN_CATALOGUE = "/api/v1/entities/{code}/onboarding/task-references"
CHEMIN_SUIVI = "/api/v1/entities/{code}/onboarding-suivi/taches-en-retard"

MARQUEUR = f"t14l7-{os.urandom(6).hex()}"
DELAI_HTTP = 30


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


class Reponse:
    def __init__(self, statut: int, corps: bytes, en_tetes: list[tuple[str, str]]) -> None:
        self.statut = statut
        self.corps = corps
        self.cookies_poses = [v for nom, v in en_tetes if nom.lower() == "set-cookie"]

    def json(self) -> object:
        try:
            return json.loads(self.corps)
        except ValueError:
            return None


def appeler(
    base: str,
    chemin: str,
    contexte: ssl.SSLContext,
    *,
    methode: str = "GET",
    charge: dict[str, object] | None = None,
    en_tetes: dict[str, str] | None = None,
) -> Reponse:
    entetes = {"Content-Type": "application/json"} if charge is not None else {}
    entetes.update(en_tetes or {})
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method=methode,
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

    from app.auth.csrf import EN_TETE_JETON, jeton_pour
    from app.auth.mots_de_passe import ALGORITHME, hacher
    from app.auth.sessions import empreinte_de_session

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")
    code_entite = f"{MARQUEUR}-a"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Administration de l'onboarding : catalogue, modeles, cycle de vie, suivi")
    print("    (matrice §8.1, §9 · backlog `MVP-L07-US003`, `US008` · LOT 7, T14)")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)

    def personne_avec_mot_de_passe(nom: str, courriel: str) -> str:
        #  Seuls le marqueur, l'adresse deja composee et l'empreinte CALCULEE
        #  sont interpoles ci-dessous, jamais une entree non validee.
        return f"""
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{courriel}', '{courriel}', '{nom}', 'T14L7', 'active') RETURNING id INTO {nom};
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES ({nom}, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c_{nom};
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c_{nom}, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
        """  # noqa: S608

    #  DSM et BOOSTER : rattaches a l'entite, mais leur droit sur les modeles
    #  vient de la responsabilite Framework, jamais du compte administrateur.
    decor = f"""
    DO $$
    DECLARE
      a uuid; bureau uuid; cercle uuid;
      dsm uuid; c_dsm uuid;
      esm uuid; c_esm uuid;
      booster uuid; c_booster uuid;
      office uuid; c_office uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_entite}', 'Entite {MARQUEUR}', 'Bordeaux', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO a;
      INSERT INTO circle (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-cercle', '{MARQUEUR}-cercle', 0) RETURNING id INTO cercle;
      INSERT INTO office (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-bureau', '{MARQUEUR}-bureau', 0) RETURNING id INTO bureau;

      {personne_avec_mot_de_passe("dsm", f"{MARQUEUR}-dsm@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (dsm, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (dsm, a, 'DSM', dsm, now() - interval '1 day');

      {personne_avec_mot_de_passe("esm", f"{MARQUEUR}-esm@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (esm, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (esm, a, 'ESM', esm, now() - interval '1 day');

      {personne_avec_mot_de_passe("booster", f"{MARQUEUR}-booster@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (booster, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id, starts_at)
      VALUES (booster, a, 'BOOSTER', cercle, booster, now() - interval '1 day');

      {personne_avec_mot_de_passe("office", f"{MARQUEUR}-office@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (office, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, office_id, assigned_by_person_id, starts_at)
      VALUES (office, a, 'OFFICE_MANAGER', bureau, office, now() - interval '1 day');
    END $$;
    """  # noqa: S608 — seuls `MARQUEUR`/`domaine` et des empreintes calculees sont interpoles
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:400]}")
        return 1
    print("    ok       decor : 1 entite, 1 cercle, 1 bureau, DSM/ESM/BOOSTER/OFFICE")

    def session_de(adresse: str) -> str:
        reponse = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            methode="POST",
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        for pose in reponse.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                return pose.split(";")[0]
        return ""

    cookie_dsm = session_de(f"{MARQUEUR}-dsm@{domaine}")
    cookie_esm = session_de(f"{MARQUEUR}-esm@{domaine}")
    cookie_booster = session_de(f"{MARQUEUR}-booster@{domaine}")
    cookie_office = session_de(f"{MARQUEUR}-office@{domaine}")
    if not all([cookie_dsm, cookie_esm, cookie_booster, cookie_office]):
        print("    ECHEC    au moins une session n'a pas ete etablie — rien n'est prouvable")
        return 1
    print("    ok       TEMOIN : les quatre connexions posent un cookie de session")

    def get(cookie: str, chemin: str) -> Reponse:
        return appeler(arguments.base, chemin, contexte, en_tetes={"Cookie": cookie})

    def ecrire(
        cookie: str, chemin: str, corps: dict[str, object], *, methode: str = "POST"
    ) -> Reponse:
        #  Double soumission (DEC-531) : le jeton CSRF derive du jeton de
        #  session BRUT, jamais du cookie entier — meme montage que
        #  `_appeler_ecriture` de `test_modeles_onboarding.py`.
        jeton_brut = cookie.split("=", 1)[1] if "=" in cookie else cookie
        jeton_csrf = jeton_pour(empreinte_de_session(jeton_brut), env["APP_SECRET_KEY"])
        return appeler(
            arguments.base,
            chemin,
            contexte,
            methode=methode,
            charge=corps,
            en_tetes={"Cookie": cookie, EN_TETE_JETON: jeton_csrf, "Origin": arguments.base},
        )

    def poster(cookie: str, chemin: str, corps: dict[str, object]) -> Reponse:
        return ecrire(cookie, chemin, corps, methode="POST")

    def mettre(cookie: str, chemin: str, corps: dict[str, object]) -> Reponse:
        return ecrire(cookie, chemin, corps, methode="PUT")

    try:
        # --- 1. avant tout modele : DSM et BOOSTER voient une liste VIDE, pas un refus
        controles += 1
        vide_dsm = get(cookie_dsm, CHEMIN_MODELES.format(code=code_entite))
        if vide_dsm.statut != 200 or vide_dsm.json() != {"modeles": [], "nombre_de_modeles": 0}:
            echecs += 1
            print(f"    ECHEC    DSM sans modele : {vide_dsm.statut} {vide_dsm.json()!r}")
        else:
            print("    ok       DSM sans modele : liste VIDE, jamais un refus (§9)")

        # --- 2. le DSM cree SON modele (portee DSM)
        controles += 1
        _, sortie_dsm_id = psql(
            compose,
            env,
            f"SELECT id FROM person WHERE email = '{MARQUEUR}-dsm@{domaine}'",  # noqa: S608
        )
        dsm_id = sortie_dsm_id.strip()
        modele_dsm = poster(
            cookie_dsm,
            CHEMIN_MODELES.format(code=code_entite),
            {
                "name": f"{MARQUEUR}-modele-dsm",
                "target_status": "mission",
                "portee": "DSM",
                "scope_person_id": dsm_id,
            },
        )
        if modele_dsm.statut != 201:
            echecs += 1
            print(
                f"    ECHEC    creation du modele DSM : {modele_dsm.statut} {modele_dsm.json()!r}"
            )
        else:
            print("    ok       le DSM cree son propre modele — 201")
        modele_dsm_corps = modele_dsm.json()
        modele_dsm_id = modele_dsm_corps["id"] if isinstance(modele_dsm_corps, dict) else None

        # --- 3. l'ESM cree un modele d'ENTITE
        controles += 1
        modele_esm = poster(
            cookie_esm,
            CHEMIN_MODELES.format(code=code_entite),
            {"name": f"{MARQUEUR}-modele-esm", "target_status": "mission", "portee": "ENTITY"},
        )
        if modele_esm.statut != 201:
            echecs += 1
            print(
                f"    ECHEC    creation du modele ESM : {modele_esm.statut} {modele_esm.json()!r}"
            )
        else:
            print("    ok       l'ESM cree un modele d'entite — 201")
        modele_esm_corps = modele_esm.json()
        modele_esm_id = modele_esm_corps["id"] if isinstance(modele_esm_corps, dict) else None

        # --- 4. L'ASYMETRIE, LE TEMOIN CENTRAL : le DSM ne voit QUE le sien
        controles += 1
        liste_dsm = get(cookie_dsm, CHEMIN_MODELES.format(code=code_entite))
        noms_dsm = (
            {m["name"] for m in liste_dsm.json()["modeles"]}
            if liste_dsm.statut == 200 and isinstance(liste_dsm.json(), dict)
            else set()
        )
        if noms_dsm != {f"{MARQUEUR}-modele-dsm"}:
            echecs += 1
            print(f"    ECHEC    le DSM voit {noms_dsm!r}, attendu SEULEMENT son propre modele")
        else:
            print("    ok       TEMOIN D'ASYMETRIE : le DSM ne voit QUE son propre modele")

        # --- 5. l'ESM, lui, voit les DEUX (portee d'entite, meme parti que LOT 6)
        controles += 1
        liste_esm = get(cookie_esm, CHEMIN_MODELES.format(code=code_entite))
        noms_esm = (
            {m["name"] for m in liste_esm.json()["modeles"]}
            if liste_esm.statut == 200 and isinstance(liste_esm.json(), dict)
            else set()
        )
        if noms_esm != {f"{MARQUEUR}-modele-dsm", f"{MARQUEUR}-modele-esm"}:
            echecs += 1
            print(f"    ECHEC    l'ESM voit {noms_esm!r}, attendu LES DEUX modeles")
        else:
            print("    ok       TEMOIN D'ASYMETRIE : l'ESM voit LES DEUX modeles de l'entite")

        # --- 6. OFFICE est a TIRET partout sur cette ligne — 403, jamais 200 vide
        controles += 1
        refus_office = get(cookie_office, CHEMIN_MODELES.format(code=code_entite))
        if refus_office.statut != 403:
            echecs += 1
            print(f"    ECHEC    OFFICE sur les modeles : {refus_office.statut}, attendu 403")
        else:
            print("    ok       OFFICE est refuse (403) sur les modeles — §9, a tiret partout")

        # --- 7. le catalogue, cree par l'ESM
        controles += 1
        tache = poster(
            cookie_esm,
            CHEMIN_CATALOGUE.format(code=code_entite),
            {"code": f"{MARQUEUR}-tache", "title": f"Tache {MARQUEUR}", "portee": "ENTITE"},
        )
        if tache.statut != 201:
            echecs += 1
            print(
                f"    ECHEC    creation de la tache de reference : {tache.statut} {tache.json()!r}"
            )
        else:
            print("    ok       creation d'une tache de reference — 201")
        tache_id = (
            tache.json()["id"] if tache.statut == 201 and isinstance(tache.json(), dict) else None
        )

        # --- 8. LE CYCLE DE VIE COMPLET, SUR LE MODELE DE L'ESM
        version_ = poster(
            cookie_esm, CHEMIN_VERSIONS.format(code=code_entite, modele=modele_esm_id), {}
        )
        controles += 1
        if version_.statut != 201:
            echecs += 1
            print(f"    ECHEC    creation de version : {version_.statut} {version_.json()!r}")
        else:
            print("    ok       creation de version brouillon — 201")
        version_id = (
            version_.json()["id"]
            if version_.statut == 201 and isinstance(version_.json(), dict)
            else None
        )

        controles += 1
        taches = mettre(
            cookie_esm,
            CHEMIN_TACHES.format(code=code_entite, modele=modele_esm_id, version=version_id),
            {"taches": [{"task_reference_id": tache_id, "required": True, "due_offset_days": 7}]},
        )
        if taches.statut != 200:
            echecs += 1
            print(f"    ECHEC    composition des taches : {taches.statut} {taches.json()!r}")
        else:
            print("    ok       composition des taches de la version — 200")

        controles += 1
        publication = poster(
            cookie_esm,
            CHEMIN_PUBLICATION.format(code=code_entite, modele=modele_esm_id, version=version_id),
            {},
        )
        if publication.statut != 200:
            echecs += 1
            print(f"    ECHEC    publication : {publication.statut} {publication.json()!r}")
        else:
            print("    ok       publication de la version (draft -> published) — 200")

        controles += 1
        archivage = poster(
            cookie_esm,
            CHEMIN_ARCHIVAGE.format(code=code_entite, modele=modele_esm_id, version=version_id),
            {},
        )
        if archivage.statut != 200:
            echecs += 1
            print(f"    ECHEC    archivage : {archivage.statut} {archivage.json()!r}")
        else:
            print("    ok       archivage de la version (published -> retired) — 200")

        controles += 1
        restauration_esm = poster(
            cookie_esm,
            CHEMIN_RESTAURATION.format(code=code_entite, modele=modele_esm_id, version=version_id),
            {},
        )
        if restauration_esm.statut != 200:
            echecs += 1
            print(f"    ECHEC    restauration par l'ESM : {restauration_esm.statut}")
        else:
            print("    ok       restauration de la version par l'ESM (retired -> published) — 200")

        # --- 9. ECART-066 : le DSM, LUI, est refuse a la restauration de SON PROPRE modele
        version_dsm = poster(
            cookie_dsm, CHEMIN_VERSIONS.format(code=code_entite, modele=modele_dsm_id), {}
        )
        version_dsm_id = (
            version_dsm.json()["id"]
            if version_dsm.statut == 201 and isinstance(version_dsm.json(), dict)
            else None
        )
        poster(
            cookie_dsm,
            CHEMIN_PUBLICATION.format(
                code=code_entite, modele=modele_dsm_id, version=version_dsm_id
            ),
            {},
        )
        poster(
            cookie_dsm,
            CHEMIN_ARCHIVAGE.format(code=code_entite, modele=modele_dsm_id, version=version_dsm_id),
            {},
        )
        controles += 1
        restauration_dsm = poster(
            cookie_dsm,
            CHEMIN_RESTAURATION.format(
                code=code_entite, modele=modele_dsm_id, version=version_dsm_id
            ),
            {},
        )
        if restauration_dsm.statut != 403:
            echecs += 1
            print(
                f"    ECHEC    le DSM restaure SON PROPRE modele : {restauration_dsm.statut}, "
                "attendu 403 (ECART-066, exclu EN BLOC)"
            )
        else:
            print(
                "    ok       ECART-066 : le DSM est refuse (403) meme en restaurant SON propre "
                "modele — exclu EN BLOC, pas un sous-cas"
            )

        # --- 10. le suivi ne refuse JAMAIS personne, meme OFFICE
        controles += 1
        suivi_office = get(
            cookie_office, CHEMIN_SUIVI.format(code=code_entite) + "?page=1&taille=25"
        )
        if suivi_office.statut != 200:
            echecs += 1
            print(f"    ECHEC    OFFICE sur le suivi : {suivi_office.statut}, attendu 200")
        else:
            print("    ok       OFFICE consulte le suivi (200) — aucun role n'y est refuse (§8.1)")

    finally:
        _, sortie_menage = psql(
            compose,
            env,
            f"""
            DO $$
            DECLARE ids uuid[];
            BEGIN
              SELECT array_agg(id) INTO ids FROM person WHERE email LIKE '{MARQUEUR}%';
              DELETE FROM onboarding_template_task WHERE template_version_id IN (
                SELECT id FROM onboarding_template_version WHERE template_id IN (
                  SELECT id FROM onboarding_template WHERE name LIKE '{MARQUEUR}%'));
              DELETE FROM onboarding_template_version WHERE template_id IN (
                SELECT id FROM onboarding_template WHERE name LIKE '{MARQUEUR}%');
              DELETE FROM onboarding_template WHERE name LIKE '{MARQUEUR}%';
              DELETE FROM onboarding_task_reference WHERE code LIKE '{MARQUEUR}%';
              DELETE FROM framework_responsibility_assignment WHERE person_id = ANY(ids);
              DELETE FROM admin_password_credential WHERE user_account_id IN (
                SELECT id FROM user_account WHERE person_id = ANY(ids));
              DELETE FROM auth_event WHERE person_id = ANY(ids);
              DELETE FROM user_session WHERE person_id = ANY(ids);
              DELETE FROM user_account WHERE person_id = ANY(ids);
              DELETE FROM entity_membership WHERE person_id = ANY(ids);
              DELETE FROM person WHERE id = ANY(ids);
              DELETE FROM office WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM circle WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM entity WHERE code LIKE '{MARQUEUR}%';
            END $$;
            """,  # noqa: S608
        )
        print(f"    info     menage : {sortie_menage[:200] or 'DO'}")

    print()
    print(f"  --> {controles} controles, {echecs} echec(s)")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
