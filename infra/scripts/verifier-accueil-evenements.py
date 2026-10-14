#!/usr/bin/env python3
"""Les evenements et l'accueil, sur la pile REELLE — LOT 8, `T13`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI PYTEST NE LE PROUVE PAS DEJA

  `test_evenements.py` et `test_accueil.py` eprouvent chaque regle de la
  matrice §11 et du cahier §8.4 via `TestClient` — la meme application
  Python, en memoire. Ce controle-ci passe par CADDY, en HTTPS, sur les
  conteneurs REELLEMENT en marche : c'est la seule maniere de prouver que le
  mandatement (`DEC-470`), le conteneur `api` a jour (`make code-refresh`) et
  les cookies `Secure`/`SameSite` du LOT 3 sont tous en jeu en meme temps —
  §7.28, une cible statique ne prouve rien de ce qu'un conteneur sert
  reellement. Meme motif exactement que `verifier-administration-
  onboarding.py` (LOT 7, `T14`) pour l'onboarding.

LE TEMOIN CENTRAL : LA GRILLE A DEUX VISAGES DU DSM

  Le §11 donne au DSM DEUX grilles distinctes pour le MEME evenement selon ce
  qu'il demande : « Modifier » accepte « cree OU rattache a son perimetre »,
  mais « Publier », « Annuler », « Archiver » et « Gerer les medias »
  n'acceptent QUE « Perimetre » — ses consultants nommes
  (`event_dsm_scope`), jamais la seule qualite de createur. Un controle qui
  ne poserait qu'UN evenement DSM verrait une seule grille et ne pourrait pas
  distinguer les deux — §7.0, quatrieme proposition. Ce script pose donc
  DEUX evenements DSM : l'un cree en portee `entite` (createur seul, jamais
  nomme), l'autre en portee `consultants` (nomme par construction), et prouve
  que le premier n'ouvre que Modifier quand le second ouvre tout le reste.

L'ASYMETRIE ENTRE DEUX PORTEURS DU MEME ROLE — LE TEMOIN DE `T3`

  Le compte rendu de `T3` nomme explicitement ce temoin dans sa preuve
  d'origine : deux Boosters, deux cercles distincts, et le second refuse sur
  le cercle du premier — a la creation ET a l'ecriture ensuite. Un controle
  a un seul Booster ne verrait jamais cette classe de refus.

`ARB-DROIT-003` EST EPROUVE DANS LE SENS DU REFUS, DEUX FOIS

  Un evenement archive n'offre plus que `RESTAURER`, et seulement aux roles
  de portee Entite — DSM et BOOST en sont exclus EN BLOC, meme sur
  l'evenement dont ils sont respectivement le createur et le Booster
  rattache. Ce script le prouve sur les DEUX evenements qu'il a lui-meme
  archives (celui du Booster, celui du DSM nomme), pas seulement sur l'un
  des deux — meme discipline que `verifier-administration-onboarding.py`
  pour `ECART-066`.

LE CLASSEMENT TEMPOREL EST EPROUVE SUR L'HORLOGE REELLE DU CONTENEUR

  Un evenement cree avec `finit_le` deja passe, publie, doit apparaitre dans
  `classement=passes` et jamais dans `a_venir` ; l'inverse pour un evenement a
  venir. Annuler l'evenement a venir ne le retire PAS de la consultation — le
  badge « Annule » reste visible, cahier §10.6 — et archiver l'evenement passe
  le retire, lui, de la consultation publique.

L'ACCUEIL COMPOSE, ET LA FENETRE DES ARRIVEES RECENTES EST LA FENETRE REELLE

  `GET …/accueil` est ouvert a HUIT roles sans garde, `EMP` compris — ce
  script ne pose donc aucune session de role pour le lire. Son temoin le
  plus utile reprend la lecon de `T7` : une appartenance `future` dont la
  fiche est deja publiee apparait IMMEDIATEMENT dans les arrivees recentes,
  avant meme sa date d'arrivee — et une fiche publiee mais dont
  `recent_until` est deja depasse en est absente. Les DEUX cas sont poses,
  jamais un seul : un filtre trop large accepterait le second, un filtre
  trop etroit rejetterait le premier, et aucun des deux defauts ne serait vu
  par l'autre temoin seul.
"""

from __future__ import annotations

import argparse
import datetime as dt
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
CHEMIN_EVENEMENTS = "/api/v1/entities/{code}/events"
CHEMIN_EVENEMENT = "/api/v1/entities/{code}/events/{evenement}"
CHEMIN_PUBLICATION = "/api/v1/entities/{code}/events/{evenement}/publication"
CHEMIN_ANNULATION = "/api/v1/entities/{code}/events/{evenement}/annulation"
CHEMIN_ARCHIVAGE = "/api/v1/entities/{code}/events/{evenement}/archivage"
CHEMIN_RESTAURATION = "/api/v1/entities/{code}/events/{evenement}/restauration"
CHEMIN_ACCUEIL = "/api/v1/entities/{code}/accueil"
CHEMIN_ARRIVEES_RECENTES = "/api/v1/entities/{code}/arrivees-recentes"

MARQUEUR = f"t13l8-{os.urandom(6).hex()}"
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
    print("  Evenements et accueil : permissions, cycle de vie, classement temporel")
    print("    (matrice §11, cahier §8.4/§10.5/§10.6 · LOT 8, T13)")
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
      VALUES ('{courriel}', '{courriel}', '{nom}', 'T13L8', 'active') RETURNING id INTO {nom};
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES ({nom}, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c_{nom};
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c_{nom}, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
        """  # noqa: S608

    #  BOOSTER1/cercle_a, BOOSTER2/cercle_b (asymetrie entre deux porteurs du
    #  meme role, temoin d'origine de `T3`) ; OFFICE/bureau (completude de la
    #  grille de creation) ; DSM, ESM (portee Entite) ; EMP, sans aucune
    #  responsabilite (refus de base).
    decor = f"""
    DO $$
    DECLARE
      a uuid; cercle_a uuid; cercle_b uuid; bureau uuid;
      emp uuid; c_emp uuid;
      dsm uuid; c_dsm uuid;
      esm uuid; c_esm uuid;
      booster1 uuid; c_booster1 uuid;
      booster2 uuid; c_booster2 uuid;
      office uuid; c_office uuid;
      arrivant_visible uuid; arrivant_invisible uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_entite}', 'Entite {MARQUEUR}', 'Bordeaux', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO a;
      INSERT INTO circle (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-cercle-a', '{MARQUEUR}-cercle-a', 0) RETURNING id INTO cercle_a;
      INSERT INTO circle (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-cercle-b', '{MARQUEUR}-cercle-b', 1) RETURNING id INTO cercle_b;
      INSERT INTO office (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-bureau', '{MARQUEUR}-bureau', 0) RETURNING id INTO bureau;

      {personne_avec_mot_de_passe("emp", f"{MARQUEUR}-emp@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (emp, a, now() - interval '30 days', 'active', 'consultant', 'draft');

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

      {personne_avec_mot_de_passe("booster1", f"{MARQUEUR}-booster1@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (booster1, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id, starts_at)
      VALUES (booster1, a, 'BOOSTER', cercle_a, booster1, now() - interval '1 day');

      {personne_avec_mot_de_passe("booster2", f"{MARQUEUR}-booster2@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (booster2, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id, starts_at)
      VALUES (booster2, a, 'BOOSTER', cercle_b, booster2, now() - interval '1 day');

      {personne_avec_mot_de_passe("office", f"{MARQUEUR}-office@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (office, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, office_id, assigned_by_person_id, starts_at)
      VALUES (office, a, 'OFFICE_MANAGER', bureau, office, now() - interval '1 day');

      --  Temoin positif : appartenance FUTURE, fiche DEJA publiee -- visible
      --  IMMEDIATEMENT (cahier §10.5), avant meme la date d'arrivee.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{MARQUEUR}-visible@{domaine}', '{MARQUEUR}-visible@{domaine}',
              'Arrivant', 'Visible', 'active') RETURNING id INTO arrivant_visible;
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (arrivant_visible, a, current_date + interval '5 days', 'future', 'consultant',
              'published') RETURNING id INTO c_emp;
      INSERT INTO arrival_profile
        (entity_id, entity_membership_id, state, short_intro, fun_fact, published_at,
         recent_until)
      VALUES (a, c_emp, 'published', 'Bientot parmi nous', 'Aime le velo',
              now(), current_date + interval '25 days');

      --  Temoin negatif : fiche publiee mais `recent_until` DEJA DEPASSE --
      --  absente, meme etat `published`, meme visibilite.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{MARQUEUR}-invisible@{domaine}', '{MARQUEUR}-invisible@{domaine}',
              'Arrivant', 'Invisible', 'active') RETURNING id INTO arrivant_invisible;
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (arrivant_invisible, a, current_date - interval '60 days', 'active', 'consultant',
              'published') RETURNING id INTO c_dsm;
      INSERT INTO arrival_profile
        (entity_id, entity_membership_id, state, short_intro, fun_fact, published_at,
         recent_until)
      VALUES (a, c_dsm, 'published', 'Arrive il y a longtemps', 'Aime la course',
              now() - interval '59 days', current_date - interval '1 days');

      INSERT INTO internal_link (entity_id, label, url, link_type, display_order,
        created_at, updated_at)
      VALUES (a, '{MARQUEUR}-lien', 'https://{MARQUEUR}.exemple.test/', 'OTHER', 0, now(), now());
    END $$;
    """  # noqa: S608 — seuls `MARQUEUR`/`domaine` et des empreintes calculees sont interpoles
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:400]}")
        return 1
    print(
        "    ok       decor : 1 entite, 2 cercles, 1 bureau, EMP/DSM/ESM/BOOSTER x2/OFFICE, "
        "2 arrivees (visible/invisible), 1 lien interne"
    )

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

    cookie_emp = session_de(f"{MARQUEUR}-emp@{domaine}")
    cookie_dsm = session_de(f"{MARQUEUR}-dsm@{domaine}")
    cookie_esm = session_de(f"{MARQUEUR}-esm@{domaine}")
    cookie_booster1 = session_de(f"{MARQUEUR}-booster1@{domaine}")
    cookie_booster2 = session_de(f"{MARQUEUR}-booster2@{domaine}")
    cookie_office = session_de(f"{MARQUEUR}-office@{domaine}")
    if not all(
        [cookie_emp, cookie_dsm, cookie_esm, cookie_booster1, cookie_booster2, cookie_office]
    ):
        print("    ECHEC    au moins une session n'a pas ete etablie — rien n'est prouvable")
        return 1
    print("    ok       TEMOIN : les six connexions posent un cookie de session")

    def get(cookie: str, chemin: str) -> Reponse:
        return appeler(arguments.base, chemin, contexte, en_tetes={"Cookie": cookie})

    def ecrire(
        cookie: str, chemin: str, corps: dict[str, object], *, methode: str = "POST"
    ) -> Reponse:
        #  Double soumission (DEC-531) : le jeton CSRF derive du jeton de
        #  session BRUT, jamais du cookie entier.
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

    def controler(*, condition: bool, succes: str, echec: str) -> None:
        nonlocal controles, echecs
        controles += 1
        if condition:
            print(f"    ok       {succes}")
        else:
            echecs += 1
            print(f"    ECHEC    {echec}")

    maintenant = dt.datetime.now(tz=dt.UTC)
    chemin_events = CHEMIN_EVENEMENTS.format(code=code_entite)

    try:
        # --- 1. EMP n'a aucune portee de creation
        refus_emp = poster(
            cookie_emp,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-refus-emp",
                "commence_le": (maintenant + dt.timedelta(days=1)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=1, hours=2)).isoformat(),
                "portee": "entite",
            },
        )
        controler(
            condition=refus_emp.statut == 403,
            succes="EMP est refuse (403) a la creation — aucune portee du §11",
            echec=f"EMP a la creation : {refus_emp.statut}, attendu 403",
        )

        # --- 2. ESM cree (portee Entite)
        event_esm = poster(
            cookie_esm,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-esm",
                "commence_le": (maintenant + dt.timedelta(days=10)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=10, hours=2)).isoformat(),
                "portee": "entite",
            },
        )
        controler(
            condition=event_esm.statut == 201,
            succes="l'ESM cree un evenement de portee Entite — 201",
            echec=f"creation ESM : {event_esm.statut} {event_esm.json()!r}",
        )
        # --- 3. DSM cree en portee Entite — createur, mais JAMAIS nomme
        event_dsm_entite = poster(
            cookie_dsm,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-dsm-entite",
                "commence_le": (maintenant + dt.timedelta(days=11)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=11, hours=2)).isoformat(),
                "portee": "entite",
            },
        )
        controler(
            condition=event_dsm_entite.statut == 201,
            succes="le DSM cree un evenement de portee Entite (createur seul) — 201",
            echec=f"creation DSM/entite : {event_dsm_entite.statut} {event_dsm_entite.json()!r}",
        )
        corps_dsm_entite = event_dsm_entite.json()
        id_dsm_entite = (
            corps_dsm_entite["identifiant"] if isinstance(corps_dsm_entite, dict) else None
        )
        version_dsm_entite = (
            corps_dsm_entite["version"] if isinstance(corps_dsm_entite, dict) else None
        )

        # --- 4. DSM cree en portee Consultants — nomme par construction (ECART-067)
        event_dsm_consultants = poster(
            cookie_dsm,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-dsm-consultants",
                "commence_le": (maintenant + dt.timedelta(days=12)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=12, hours=2)).isoformat(),
                "portee": "consultants",
            },
        )
        controler(
            condition=event_dsm_consultants.statut == 201,
            succes="le DSM cree un evenement de portee Consultants (nomme) — 201 (ECART-067)",
            echec=(
                f"creation DSM/consultants : {event_dsm_consultants.statut} "
                f"{event_dsm_consultants.json()!r}"
            ),
        )
        corps_dsm_consultants = event_dsm_consultants.json()
        id_dsm_consultants = (
            corps_dsm_consultants["identifiant"]
            if isinstance(corps_dsm_consultants, dict)
            else None
        )
        version_dsm_consultants = (
            corps_dsm_consultants["version"] if isinstance(corps_dsm_consultants, dict) else None
        )

        # --- 5. BOOSTER1 cree sur SON cercle
        event_booster_a = poster(
            cookie_booster1,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-booster-a",
                "commence_le": (maintenant + dt.timedelta(days=13)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=13, hours=2)).isoformat(),
                "portee": "cercle",
                "cercle": f"{MARQUEUR}-cercle-a",
            },
        )
        controler(
            condition=event_booster_a.statut == 201,
            succes="BOOSTER1 cree un evenement sur SON cercle — 201",
            echec=f"creation BOOSTER1 : {event_booster_a.statut} {event_booster_a.json()!r}",
        )
        corps_booster_a = event_booster_a.json()
        id_booster_a = corps_booster_a["identifiant"] if isinstance(corps_booster_a, dict) else None
        version_booster_a = (
            corps_booster_a["version"] if isinstance(corps_booster_a, dict) else None
        )

        # --- 6. BOOSTER2 refuse sur le cercle de BOOSTER1 — asymetrie, temoin de T3
        refus_booster2_creation = poster(
            cookie_booster2,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-refus-booster2",
                "commence_le": (maintenant + dt.timedelta(days=14)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=14, hours=2)).isoformat(),
                "portee": "cercle",
                "cercle": f"{MARQUEUR}-cercle-a",
            },
        )
        controler(
            condition=refus_booster2_creation.statut == 403,
            succes=(
                "BOOSTER2 est refuse (403) sur le cercle de BOOSTER1 — asymetrie entre "
                "deux porteurs du meme role (temoin de T3)"
            ),
            echec=f"creation BOOSTER2/cercle-a : {refus_booster2_creation.statut}, attendu 403",
        )

        # --- 7. OFFICE cree sur son bureau — completude de la grille de creation
        event_office = poster(
            cookie_office,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-office",
                "commence_le": (maintenant + dt.timedelta(days=15)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=15, hours=2)).isoformat(),
                "portee": "bureau",
                "bureau": f"{MARQUEUR}-bureau",
            },
        )
        controler(
            condition=event_office.statut == 201,
            succes="OFFICE cree un evenement sur son bureau — 201",
            echec=f"creation OFFICE : {event_office.statut} {event_office.json()!r}",
        )

        # --- 8. LE TEMOIN CENTRAL : le DSM createur-seul est REFUSE a Publier
        refus_dsm_publier = poster(
            cookie_dsm,
            CHEMIN_PUBLICATION.format(code=code_entite, evenement=id_dsm_entite),
            {"version": version_dsm_entite},
        )
        controler(
            condition=refus_dsm_publier.statut == 403,
            succes=(
                "TEMOIN CENTRAL : le DSM createur-seul est refuse (403) a Publier — "
                "« Perimetre » exige d'etre NOMME, jamais seulement createur (§7.45)"
            ),
            echec=f"DSM Publier (createur seul) : {refus_dsm_publier.statut}, attendu 403",
        )

        # --- 9. LE MEME DSM, LE MEME EVENEMENT : Modifier est ouvert (« cree OU rattache »)
        modif_dsm = mettre(
            cookie_dsm,
            CHEMIN_EVENEMENT.format(code=code_entite, evenement=id_dsm_entite),
            {
                "titre": f"{MARQUEUR}-dsm-entite-modifie",
                "commence_le": (maintenant + dt.timedelta(days=11)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=11, hours=2)).isoformat(),
                "version": version_dsm_entite,
            },
        )
        controler(
            condition=modif_dsm.statut == 200,
            succes=(
                "le MEME DSM, le MEME evenement : Modifier est ouvert (200) — "
                "« cree OU rattache », DEUX GRILLES pour un seul role"
            ),
            echec=f"DSM Modifier (createur seul) : {modif_dsm.statut}, attendu 200",
        )

        # --- 10. le DSM nomme (portee Consultants), lui, PUBLIE
        publie_dsm_consultants = poster(
            cookie_dsm,
            CHEMIN_PUBLICATION.format(code=code_entite, evenement=id_dsm_consultants),
            {"version": version_dsm_consultants},
        )
        controler(
            condition=publie_dsm_consultants.statut == 200,
            succes="le DSM NOMME (consultants) publie son evenement — 200",
            echec=(
                f"DSM Publier (nomme) : {publie_dsm_consultants.statut} "
                f"{publie_dsm_consultants.json()!r}"
            ),
        )
        corps_publie_dsm = publie_dsm_consultants.json()
        version_dsm_consultants = (
            corps_publie_dsm["version"] if isinstance(corps_publie_dsm, dict) else None
        )

        # --- 11. BOOSTER2 refuse en ECRITURE sur l'evenement du cercle de BOOSTER1
        refus_modif_b2 = mettre(
            cookie_booster2,
            CHEMIN_EVENEMENT.format(code=code_entite, evenement=id_booster_a),
            {
                "titre": f"{MARQUEUR}-booster-a-pirate",
                "commence_le": (maintenant + dt.timedelta(days=13)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=13, hours=2)).isoformat(),
                "version": version_booster_a,
            },
        )
        controler(
            condition=refus_modif_b2.statut == 403,
            succes="BOOSTER2 est refuse (403) en ECRITURE sur l'evenement du cercle de BOOSTER1",
            echec=f"BOOSTER2 Modifier (hors cercle) : {refus_modif_b2.statut}, attendu 403",
        )

        # --- 12. BOOSTER1 modifie, publie, annule, archive SON evenement
        modif_booster1 = mettre(
            cookie_booster1,
            CHEMIN_EVENEMENT.format(code=code_entite, evenement=id_booster_a),
            {
                "titre": f"{MARQUEUR}-booster-a",
                "commence_le": (maintenant + dt.timedelta(days=13)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=13, hours=2)).isoformat(),
                "version": version_booster_a,
            },
        )
        controler(
            condition=modif_booster1.statut == 200,
            succes="BOOSTER1 modifie son propre evenement — 200",
            echec=f"BOOSTER1 Modifier : {modif_booster1.statut} {modif_booster1.json()!r}",
        )
        version_booster_a = (
            modif_booster1.json()["version"] if modif_booster1.statut == 200 else version_booster_a
        )

        publie_booster1 = poster(
            cookie_booster1,
            CHEMIN_PUBLICATION.format(code=code_entite, evenement=id_booster_a),
            {"version": version_booster_a},
        )
        controler(
            condition=publie_booster1.statut == 200,
            succes="BOOSTER1 publie son propre evenement — 200 (draft -> published)",
            echec=f"BOOSTER1 Publier : {publie_booster1.statut} {publie_booster1.json()!r}",
        )
        version_booster_a = (
            publie_booster1.json()["version"]
            if publie_booster1.statut == 200
            else version_booster_a
        )

        annule_booster1 = poster(
            cookie_booster1,
            CHEMIN_ANNULATION.format(code=code_entite, evenement=id_booster_a),
            {"version": version_booster_a, "motif": f"{MARQUEUR}-motif"},
        )
        controler(
            condition=(
                annule_booster1.statut == 200
                and isinstance(annule_booster1.json(), dict)
                and annule_booster1.json().get("etat") == "cancelled"
            ),
            succes=(
                "BOOSTER1 annule son propre evenement — 200 (published -> cancelled), "
                "reste visible avec son badge"
            ),
            echec=f"BOOSTER1 Annuler : {annule_booster1.statut} {annule_booster1.json()!r}",
        )
        version_booster_a = (
            annule_booster1.json()["version"]
            if annule_booster1.statut == 200
            else version_booster_a
        )

        archive_booster1 = poster(
            cookie_booster1,
            CHEMIN_ARCHIVAGE.format(code=code_entite, evenement=id_booster_a),
            {"version": version_booster_a},
        )
        controler(
            condition=archive_booster1.statut == 200,
            succes="BOOSTER1 archive son propre evenement annule — 200 (cancelled -> archived)",
            echec=f"BOOSTER1 Archiver : {archive_booster1.statut} {archive_booster1.json()!r}",
        )
        version_booster_a = (
            archive_booster1.json()["version"]
            if archive_booster1.statut == 200
            else version_booster_a
        )

        # --- 13. ARB-DROIT-003, premier sens : BOOST est EXCLU EN BLOC de la restauration
        refus_restauration_booster1 = poster(
            cookie_booster1,
            CHEMIN_RESTAURATION.format(code=code_entite, evenement=id_booster_a),
            {"version": version_booster_a},
        )
        controler(
            condition=refus_restauration_booster1.statut == 403,
            succes=(
                "ARB-DROIT-003 : BOOSTER1 est refuse (403) en restaurant SON PROPRE "
                "evenement — exclu EN BLOC, pas un sous-cas de son propre perimetre"
            ),
            echec=f"BOOSTER1 Restaurer : {refus_restauration_booster1.statut}, attendu 403",
        )

        # --- 14. l'ESM, lui, restaure librement n'importe quel evenement de l'entite
        restauration_esm_booster_a = poster(
            cookie_esm,
            CHEMIN_RESTAURATION.format(code=code_entite, evenement=id_booster_a),
            {"version": version_booster_a},
        )
        controler(
            condition=(
                restauration_esm_booster_a.statut == 200
                and isinstance(restauration_esm_booster_a.json(), dict)
                and restauration_esm_booster_a.json().get("etat") == "draft"
            ),
            succes=(
                "l'ESM restaure librement l'evenement du Booster — 200, etat 'draft' "
                "(jamais l'etat anterieur a l'archivage)"
            ),
            echec=(
                f"ESM Restaurer (evenement Booster) : {restauration_esm_booster_a.statut} "
                f"{restauration_esm_booster_a.json()!r}"
            ),
        )

        # --- 15. le DSM nomme ARCHIVE son propre evenement publie (Perimetre couvre Archiver)
        archive_dsm = poster(
            cookie_dsm,
            CHEMIN_ARCHIVAGE.format(code=code_entite, evenement=id_dsm_consultants),
            {"version": version_dsm_consultants},
        )
        controler(
            condition=archive_dsm.statut == 200,
            succes="le DSM nomme archive son propre evenement — 200 (Perimetre couvre Archiver)",
            echec=f"DSM Archiver (nomme) : {archive_dsm.statut} {archive_dsm.json()!r}",
        )
        version_dsm_consultants = (
            archive_dsm.json()["version"] if archive_dsm.statut == 200 else version_dsm_consultants
        )

        # --- 16. ARB-DROIT-003, second sens : le MEME refus pour le DSM, meme NOMME
        refus_restauration_dsm = poster(
            cookie_dsm,
            CHEMIN_RESTAURATION.format(code=code_entite, evenement=id_dsm_consultants),
            {"version": version_dsm_consultants},
        )
        controler(
            condition=refus_restauration_dsm.statut == 403,
            succes=(
                "ARB-DROIT-003 : le DSM NOMME par sa propre portee est AUSSI refuse (403) "
                "en restaurant — meme exclusion EN BLOC que BOOSTER1, pas une consequence "
                "d'etre simplement 'non nomme'"
            ),
            echec=f"DSM Restaurer (nomme) : {refus_restauration_dsm.statut}, attendu 403",
        )

        restauration_esm_dsm = poster(
            cookie_esm,
            CHEMIN_RESTAURATION.format(code=code_entite, evenement=id_dsm_consultants),
            {"version": version_dsm_consultants},
        )
        controler(
            condition=(
                restauration_esm_dsm.statut == 200
                and isinstance(restauration_esm_dsm.json(), dict)
                and restauration_esm_dsm.json().get("etat") == "draft"
            ),
            succes="l'ESM restaure librement l'evenement du DSM — 200, etat 'draft'",
            echec=(
                f"ESM Restaurer (evenement DSM) : {restauration_esm_dsm.statut} "
                f"{restauration_esm_dsm.json()!r}"
            ),
        )

        # --- 17. LE CLASSEMENT TEMPOREL, SUR L'HORLOGE REELLE
        event_passe = poster(
            cookie_esm,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-passe",
                "commence_le": (maintenant - dt.timedelta(days=2)).isoformat(),
                "finit_le": (maintenant - dt.timedelta(days=1)).isoformat(),
                "portee": "entite",
            },
        )
        id_passe = (
            event_passe.json()["identifiant"]
            if event_passe.statut == 201 and isinstance(event_passe.json(), dict)
            else None
        )
        version_passe = (
            event_passe.json()["version"]
            if event_passe.statut == 201 and isinstance(event_passe.json(), dict)
            else None
        )
        publie_passe = poster(
            cookie_esm,
            CHEMIN_PUBLICATION.format(code=code_entite, evenement=id_passe),
            {"version": version_passe},
        )
        version_passe = (
            publie_passe.json()["version"] if publie_passe.statut == 200 else version_passe
        )

        event_a_venir = poster(
            cookie_esm,
            chemin_events,
            {
                "titre": f"{MARQUEUR}-a-venir",
                "commence_le": (maintenant + dt.timedelta(days=1)).isoformat(),
                "finit_le": (maintenant + dt.timedelta(days=2)).isoformat(),
                "portee": "entite",
            },
        )
        id_a_venir = (
            event_a_venir.json()["identifiant"]
            if event_a_venir.statut == 201 and isinstance(event_a_venir.json(), dict)
            else None
        )
        version_a_venir = (
            event_a_venir.json()["version"]
            if event_a_venir.statut == 201 and isinstance(event_a_venir.json(), dict)
            else None
        )
        publie_a_venir = poster(
            cookie_esm,
            CHEMIN_PUBLICATION.format(code=code_entite, evenement=id_a_venir),
            {"version": version_a_venir},
        )
        version_a_venir = (
            publie_a_venir.json()["version"] if publie_a_venir.statut == 200 else version_a_venir
        )

        liste_passes = get(cookie_esm, f"{chemin_events}?classement=passes&taille=100")
        titres_passes = (
            {e["titre"] for e in liste_passes.json()["evenements"]}
            if liste_passes.statut == 200 and isinstance(liste_passes.json(), dict)
            else set()
        )
        controler(
            condition=(
                f"{MARQUEUR}-passe" in titres_passes and f"{MARQUEUR}-a-venir" not in titres_passes
            ),
            succes="classement=passes : l'evenement termine y est, celui a venir n'y est pas",
            echec=f"classement=passes : {titres_passes!r}",
        )

        liste_a_venir = get(cookie_esm, f"{chemin_events}?classement=a_venir&taille=100")
        titres_a_venir = (
            {e["titre"] for e in liste_a_venir.json()["evenements"]}
            if liste_a_venir.statut == 200 and isinstance(liste_a_venir.json(), dict)
            else set()
        )
        controler(
            condition=(
                f"{MARQUEUR}-a-venir" in titres_a_venir
                and f"{MARQUEUR}-passe" not in titres_a_venir
            ),
            succes="classement=a_venir : l'evenement a venir y est, celui termine n'y est pas",
            echec=f"classement=a_venir : {titres_a_venir!r}",
        )

        # --- 18. annuler NE RETIRE PAS de la consultation — badge, jamais une absence
        annule_a_venir = poster(
            cookie_esm,
            CHEMIN_ANNULATION.format(code=code_entite, evenement=id_a_venir),
            {"version": version_a_venir},
        )
        version_a_venir = (
            annule_a_venir.json()["version"] if annule_a_venir.statut == 200 else version_a_venir
        )
        liste_a_venir_apres_annulation = get(
            cookie_esm, f"{chemin_events}?classement=a_venir&taille=100"
        )
        evenement_annule_rendu = next(
            (
                e
                for e in (
                    liste_a_venir_apres_annulation.json().get("evenements", [])
                    if isinstance(liste_a_venir_apres_annulation.json(), dict)
                    else []
                )
                if e.get("titre") == f"{MARQUEUR}-a-venir"
            ),
            None,
        )
        controler(
            condition=(
                evenement_annule_rendu is not None
                and evenement_annule_rendu.get("etat") == "cancelled"
            ),
            succes="l'evenement annule RESTE visible dans 'a_venir', avec etat 'cancelled'",
            echec=f"evenement annule introuvable ou mal etate : {evenement_annule_rendu!r}",
        )

        # --- 19. archiver RETIRE de la consultation publique — a_venir/passes
        archive_passe = poster(
            cookie_esm,
            CHEMIN_ARCHIVAGE.format(code=code_entite, evenement=id_passe),
            {"version": version_passe},
        )
        liste_passes_apres_archivage = get(
            cookie_esm, f"{chemin_events}?classement=passes&taille=100"
        )
        titres_passes_apres = (
            {e["titre"] for e in liste_passes_apres_archivage.json()["evenements"]}
            if liste_passes_apres_archivage.statut == 200
            and isinstance(liste_passes_apres_archivage.json(), dict)
            else {"<echec de lecture>"}
        )
        controler(
            condition=(
                archive_passe.statut == 200 and f"{MARQUEUR}-passe" not in titres_passes_apres
            ),
            succes="archiver retire de 'passes', jamais fait par l'annulation seule",
            echec=f"archivage : {archive_passe.statut} ; present : {titres_passes_apres!r}",
        )

        # --- 20. L'ACCUEIL COMPOSE, LU PAR EMP — aucune garde de role au-dela de la session
        accueil = get(cookie_emp, CHEMIN_ACCUEIL.format(code=code_entite))
        corps_accueil = accueil.json() if accueil.statut == 200 else None
        controler(
            condition=(
                isinstance(corps_accueil, dict)
                and set(corps_accueil.keys())
                >= {
                    "presentation",
                    "framework",
                    "arrivees_recentes",
                    "evenements_a_venir",
                    "liens_internes",
                }
                and corps_accueil["presentation"] is None
            ),
            succes=(
                "EMP consulte l'accueil (200) — les cinq sections sont presentes, "
                "'presentation' est null (aucune page creee)"
            ),
            echec=f"accueil EMP : {accueil.statut} {corps_accueil!r}",
        )

        titres_accueil = (
            {e["titre"] for e in corps_accueil["evenements_a_venir"]["evenements"]}
            if isinstance(corps_accueil, dict)
            else set()
        )
        controler(
            condition=(
                f"{MARQUEUR}-a-venir" in titres_accueil
                and f"{MARQUEUR}-dsm-entite-modifie" not in titres_accueil
                and f"{MARQUEUR}-passe" not in titres_accueil
            ),
            succes=(
                "l'accueil compose l'evenement publie-et-annule (visible), jamais le "
                "brouillon DSM ni l'evenement archive"
            ),
            echec=f"evenements_a_venir de l'accueil : {titres_accueil!r}",
        )

        libelles_liens = (
            {lien["libelle"] for lien in corps_accueil["liens_internes"]["liens"]}
            if isinstance(corps_accueil, dict)
            else set()
        )
        controler(
            condition=f"{MARQUEUR}-lien" in libelles_liens,
            succes="l'accueil compose le lien interne pose en decor",
            echec=f"liens_internes de l'accueil : {libelles_liens!r}",
        )

        # --- 21. ARRIVEES RECENTES : la fenetre REELLE, pas la seule qualite d'etat
        arrivees_accueil = (
            {a["last_name"] for a in corps_accueil["arrivees_recentes"]["arrivees"]}
            if isinstance(corps_accueil, dict)
            else set()
        )
        controler(
            condition=("Visible" in arrivees_accueil and "Invisible" not in arrivees_accueil),
            succes=(
                "l'accueil montre l'arrivee FUTURE deja publiee IMMEDIATEMENT (cahier §10.5), "
                "et PAS celle dont 'recent_until' est deja depasse"
            ),
            echec=f"arrivees_recentes de l'accueil : {arrivees_accueil!r}",
        )

        arrivees_route = get(
            cookie_emp, f"{CHEMIN_ARRIVEES_RECENTES.format(code=code_entite)}?taille=100"
        )
        noms_arrivees_route = (
            {a["last_name"] for a in arrivees_route.json()["arrivees"]}
            if arrivees_route.statut == 200 and isinstance(arrivees_route.json(), dict)
            else set()
        )
        controler(
            condition=("Visible" in noms_arrivees_route and "Invisible" not in noms_arrivees_route),
            succes="la route dediee '/arrivees-recentes' rend la MEME fenetre que l'accueil",
            echec=f"'/arrivees-recentes' : {noms_arrivees_route!r}",
        )

    finally:
        _, sortie_menage = psql(
            compose,
            env,
            f"""
            DO $$
            DECLARE ids uuid[];
            BEGIN
              SELECT array_agg(id) INTO ids FROM person WHERE email LIKE '{MARQUEUR}%';
              DELETE FROM event_dsm_scope WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM event_circle_scope WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM event_office_scope WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM event WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM internal_link WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM arrival_profile WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM framework_responsibility_assignment WHERE person_id = ANY(ids);
              DELETE FROM entity_membership WHERE person_id = ANY(ids);
              DELETE FROM admin_password_credential WHERE user_account_id IN (
                SELECT id FROM user_account WHERE person_id = ANY(ids));
              DELETE FROM auth_event WHERE person_id = ANY(ids);
              DELETE FROM audit_event WHERE actor_person_id = ANY(ids);
              DELETE FROM user_session WHERE person_id = ANY(ids);
              DELETE FROM user_account WHERE person_id = ANY(ids);
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
