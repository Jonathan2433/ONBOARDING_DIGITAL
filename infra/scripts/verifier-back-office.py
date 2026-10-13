#!/usr/bin/env python3
"""Le back-office, sur la pile REELLE — LOT 9, sous-etape `T15`.

Critere de sortie 6 de la fiche (§1.2) : « l'isolation multi-entites est
testee pendant l'import — temoin d'isolation dedie, a T15 ». Decoupage
valide (§3) : « Controle de pile reelle, asymetrie de roles, isolation
multi-entites pendant l'import — pattern T13/T14 des LOTS 7/8 ».

CE QUE CE CONTROLE PROUVE, ET POURQUOI PYTEST NE LE PROUVE PAS DEJA

  Les suites pytest de `T1` a `T14` eprouvent chaque regle via `TestClient`,
  la meme application Python, en memoire. Ce controle-ci passe par CADDY, en
  HTTPS, sur les conteneurs REELLEMENT en marche — la seule maniere de
  prouver que le mandatement (`DEC-470`), le conteneur `api` a jour
  (`make code-refresh`) et les cookies `Secure`/`SameSite` du LOT 3 sont tous
  en jeu en meme temps (§7.28).

PARTIE A — L'ASYMETRIE DE ROLES SUR LES ECRANS DE `T14`

  Le temoin central : le tableau de bord (`T5`) vu par un DSM (portee
  « Consultants ») et par l'ESM (portee « Entite »), DANS LA MEME ENTITE,
  sur les MEMES donnees — `profils_actifs` doit differer, sans quoi la
  portee serait decorative (§7.0, quatrieme proposition). Trois paires de
  temoins supplementaires, chacune posant un role REFUSE a cote d'un role
  ACCEPTE sur la MEME action, pour que l'echec produise une observation
  differente du succes : le depot d'import (ESM accepte, DSM et OFFICE
  refuses), la creation d'entite (SUPER seul, ESM refuse), et le catalogue
  des metiers (T14, AUCUN role distingue — tout appelant authentifie voit
  200, y compris OFFICE, refuse partout ailleurs dans ce script).

PARTIE B — L'ISOLATION MULTI-ENTITES PENDANT L'IMPORT (critere 6)

  Toutes les requetes SQL d'`app.imports.rapport`/`execution` filtrent deja
  par `entity_id = :entite` avant de regarder le lot ou la ligne (isolation
  par construction, meme discipline que les cles composites du LOT 2) — mais
  AUCUN temoin ne le prouvait sur la pile reelle avant ce script. Le lot
  depose par l'ESM de l'entite A est vise par l'ESM de l'entite B, sur les
  TROIS routes scopees par lot : rapport, lancement, rejeu. Chacune est
  appelee sous CHAQUE entite, avec les MEMES identifiants de lot et de
  ligne — seule l'entite de l'appelant change — et chaque paire produit DEUX
  observations categoriquement differentes :

    rapport    A : 200             B : 404 lot_introuvable
    lancement  A : 200 (complete)  B : 404 lot_introuvable (PAS 409 : la
                                        meme requete, sur le MEME lot deja
                                        complete, refuse pour une raison
                                        DIFFERENTE selon l'entite — la preuve
                                        que l'isolation porte sur l'entite,
                                        pas seulement sur l'etat)
    rejeu      A : 409 rejeu_hors_portee (lot ET ligne trouves, mais la
                                        ligne porte une anomalie d'e-mail,
                                        hors de la portee du rejeu)
               B : 404 lot_introuvable (le MEME lot, la MEME ligne,
                                        introuvables depuis une AUTRE entite)

  Le couple 409/404 sur le rejeu est le temoin le plus discriminant : il
  prouve que le refus de B n'est pas un simple role insuffisant (ce serait
  un 403, identique pour toute entite) ni un etat de lot (ce serait un 409,
  comme pour A) mais bien une ABSENCE structurelle du lot dans le perimetre
  de B.

LA LIGNE REJETEE EST CONSTRUITE DELIBEREMENT, PAS UN ACCIDENT DE DECOR

  Un CSV a une seule ligne, sans e-mail (`E-EMAIL-001`), suffit a produire
  un lot `preview_ready` puis `completed` sans construire le referentiel
  complet (metier, cercle, DSM...) que `T9` valide — ce script n'a besoin
  QUE de l'isolation des routes, jamais de reussir une creation de profil.
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
CHEMIN_JOB_CATALOG = "/api/v1/entities/{code}/job-catalog"
CHEMIN_TABLEAU_DE_BORD = "/api/v1/entities/{code}/administration/tableau-de-bord"
CHEMIN_IMPORTS = "/api/v1/entities/{code}/imports"
CHEMIN_RAPPORT = "/api/v1/entities/{code}/imports/{lot}/rapport"
CHEMIN_LANCEMENT = "/api/v1/entities/{code}/imports/{lot}/lancement"
CHEMIN_REJEU = "/api/v1/entities/{code}/imports/{lot}/rows/{ligne}/rejeu"
CHEMIN_ENTITES = "/api/v1/entities"

MARQUEUR = f"t15l9{uuid.uuid4().hex[:10]}"
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


def mc(compose: list[str], commande: str) -> tuple[int, str]:
    """Une commande `mc` DANS le conteneur MinIO — jamais `boto3` (§7.2, `verifier-profil.py`)."""
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "minio",
            "sh",
            "-c",
            'mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" '
            f'"$MINIO_ROOT_PASSWORD" >/dev/null && {commande}',
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


def _requeter(
    base: str, chemin: str, contexte: ssl.SSLContext, requete: urllib.request.Request
) -> Reponse:
    try:
        with urllib.request.urlopen(  # noqa: S310 — https impose par `base`
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), list(reponse.headers.items()))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), list(erreur.headers.items()))


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
    requete = urllib.request.Request(  # noqa: S310
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method=methode,
    )
    return _requeter(base, chemin, contexte, requete)


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
    from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")
    code_a = f"{MARQUEUR}-a"
    code_b = f"{MARQUEUR}-b"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Back-office : asymetrie de roles et isolation multi-entites pendant l'import")
    print("    (fiche LOT 9 §1.2 critere 6, §3 decoupage · LOT 9, T15)")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0
    lot_id: str | None = None

    def constater(condition: bool, libelle_succes: str, libelle_echec: str) -> None:
        nonlocal echecs, controles
        controles += 1
        if condition:
            print(f"    ok       {libelle_succes}")
        else:
            echecs += 1
            print(f"    ECHEC    {libelle_echec}")

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)

    def personne_avec_mot_de_passe(nom: str, courriel: str) -> str:
        #  Seuls le marqueur, l'adresse deja composee et l'empreinte CALCULEE
        #  sont interpoles ci-dessous, jamais une entree non validee.
        return f"""
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{courriel}', '{courriel}', '{nom}', 'T15L9', 'active') RETURNING id INTO {nom};
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES ({nom}, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c_{nom};
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c_{nom}, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
        """  # noqa: S608

    #  DEUX entites : A porte le decor complet (ESM/DSM/OFFICE, deux profils
    #  « employes » distinguant la portee du DSM), B ne porte qu'un ESM —
    #  juste assez pour prouver l'isolation DEPUIS une autre entite reelle.
    decor = f"""
    DO $$
    DECLARE
      a uuid; b uuid; bureau uuid;
      esm_a uuid; c_esm_a uuid;
      dsm_a uuid; c_dsm_a uuid;
      office_a uuid; c_office_a uuid;
      consultant uuid; em_consultant uuid;
      autre uuid;
      esm_b uuid; c_esm_b uuid;
      super_ uuid; c_super_ uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_a}', 'Entite A {MARQUEUR}', 'Bordeaux', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO a;
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_b}', 'Entite B {MARQUEUR}', 'Nantes', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO b;
      INSERT INTO office (entity_id, code, name, display_order)
      VALUES (a, '{MARQUEUR}-bureau', '{MARQUEUR}-bureau', 0) RETURNING id INTO bureau;

      {personne_avec_mot_de_passe("esm_a", f"{MARQUEUR}-esm-a@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (esm_a, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (esm_a, a, '{TypeResponsabilite.ESM.value}', esm_a, now() - interval '1 day');

      {personne_avec_mot_de_passe("dsm_a", f"{MARQUEUR}-dsm-a@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (dsm_a, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (dsm_a, a, '{TypeResponsabilite.DSM.value}', dsm_a, now() - interval '1 day');

      {personne_avec_mot_de_passe("office_a", f"{MARQUEUR}-office-a@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (office_a, a, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, office_id, assigned_by_person_id, starts_at)
      VALUES (office_a, a, '{TypeResponsabilite.OFFICE_MANAGER.value}', bureau, office_a,
              now() - interval '1 day');

      --  LE CONSULTANT DU DSM : seul profil que la portee « Consultants »
      --  doit compter — `dsm_assignment` le lie explicitement a `dsm_a`.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{MARQUEUR}-consultant@{domaine}', '{MARQUEUR}-consultant@{domaine}',
              'Consultant', 'T15L9', 'active') RETURNING id INTO consultant;
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (consultant, a, now() - interval '20 days', 'active', 'consultant', 'draft')
      RETURNING id INTO em_consultant;
      INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, starts_at)
      VALUES (a, em_consultant, dsm_a, now() - interval '10 days');

      --  UN AUTRE PROFIL ACTIF, SANS AUCUN LIEN AU DSM : l'ESM (portee
      --  Entite) doit le voir, le DSM (portee Consultants) ne doit PAS.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{MARQUEUR}-autre@{domaine}', '{MARQUEUR}-autre@{domaine}',
              'Autre', 'T15L9', 'active') RETURNING id INTO autre;
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (autre, a, now() - interval '15 days', 'active', 'consultant', 'draft');

      {personne_avec_mot_de_passe("esm_b", f"{MARQUEUR}-esm-b@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (esm_b, b, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (esm_b, b, '{TypeResponsabilite.ESM.value}', esm_b, now() - interval '1 day');

      --  LE SUPER-ADMINISTRATEUR : role technique GLOBAL, `entity_id` NUL —
      --  seul role qui ne vit DANS aucune des deux entites (§5.1 du LOT 4).
      {personne_avec_mot_de_passe("super_", f"{MARQUEUR}-super@{domaine}")}
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (super_, b, now() - interval '30 days', 'active', 'consultant', 'draft');
      INSERT INTO technical_role_assignment
        (person_id, entity_id, role_type, starts_at, ends_at)
      VALUES (super_, NULL, '{TypeRoleTechnique.SUPER_ADMIN.value}', now() - interval '1 day',
              NULL);
    END $$;
    """  # noqa: S608 — seuls `MARQUEUR`/`domaine` et des empreintes calculees sont interpoles
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:400]}")
        return 1
    print(
        "    ok       decor : 2 entites, 1 bureau, 6 personnes (ESM x2, DSM, OFFICE, SUPER, 2 EMP)"
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

    cookie_esm_a = session_de(f"{MARQUEUR}-esm-a@{domaine}")
    cookie_dsm_a = session_de(f"{MARQUEUR}-dsm-a@{domaine}")
    cookie_office_a = session_de(f"{MARQUEUR}-office-a@{domaine}")
    cookie_esm_b = session_de(f"{MARQUEUR}-esm-b@{domaine}")
    cookie_super = session_de(f"{MARQUEUR}-super@{domaine}")
    if not all([cookie_esm_a, cookie_dsm_a, cookie_office_a, cookie_esm_b, cookie_super]):
        print("    ECHEC    au moins une session n'a pas ete etablie — rien n'est prouvable")
        return 1
    print("    ok       TEMOIN : les cinq connexions posent un cookie de session")

    def get(cookie: str, chemin: str) -> Reponse:
        return appeler(arguments.base, chemin, contexte, en_tetes={"Cookie": cookie})

    def _entetes_ecriture(cookie: str) -> dict[str, str]:
        #  Double soumission (DEC-531) : le jeton CSRF derive du jeton de
        #  session BRUT, jamais du cookie entier.
        jeton_brut = cookie.split("=", 1)[1] if "=" in cookie else cookie
        jeton_csrf = jeton_pour(empreinte_de_session(jeton_brut), env["APP_SECRET_KEY"])
        return {"Cookie": cookie, EN_TETE_JETON: jeton_csrf, "Origin": arguments.base}

    def poster(cookie: str, chemin: str, corps: dict[str, object]) -> Reponse:
        return appeler(
            arguments.base,
            chemin,
            contexte,
            methode="POST",
            charge=corps,
            en_tetes=_entetes_ecriture(cookie),
        )

    def deposer_csv(cookie: str, chemin: str, nom_fichier: str, contenu: bytes) -> Reponse:
        """`POST .../imports` exige un corps `multipart/form-data` — un champ `fichier`."""
        frontiere = f"----{uuid.uuid4().hex}"
        corps = (
            f"--{frontiere}\r\n"
            f'Content-Disposition: form-data; name="fichier"; filename="{nom_fichier}"\r\n'
            "Content-Type: text/csv\r\n\r\n"
        ).encode()
        corps += contenu
        corps += f"\r\n--{frontiere}--\r\n".encode()
        entetes = _entetes_ecriture(cookie)
        entetes["Content-Type"] = f"multipart/form-data; boundary={frontiere}"
        requete = urllib.request.Request(  # noqa: S310
            f"{arguments.base}{chemin}", data=corps, headers=entetes, method="POST"
        )
        return _requeter(arguments.base, chemin, contexte, requete)

    try:
        # ====================================================================
        #  PARTIE A — ASYMETRIE DE ROLES SUR LES ECRANS BACK-OFFICE (`T14`)
        # ====================================================================

        # --- 1. le catalogue des metiers (T14, route nouvelle) : AUCUN role
        #     n'est distingue — meme OFFICE, refuse partout ailleurs ici, voit 200.
        reponse = get(cookie_office_a, CHEMIN_JOB_CATALOG.format(code=code_a))
        constater(
            reponse.statut == 200,
            "catalogue des metiers (T14) : OFFICE voit 200 — aucun role distingue",
            f"catalogue des metiers : OFFICE a recu {reponse.statut}, attendu 200",
        )

        # --- 2 et 3. LE TEMOIN CENTRAL : le tableau de bord, DEUX PORTEES
        #     differentes sur la MEME entite, les MEMES donnees.
        tableau_dsm = get(cookie_dsm_a, CHEMIN_TABLEAU_DE_BORD.format(code=code_a))
        tableau_esm = get(cookie_esm_a, CHEMIN_TABLEAU_DE_BORD.format(code=code_a))
        profils_dsm = (
            tableau_dsm.json().get("profils_actifs")
            if tableau_dsm.statut == 200 and isinstance(tableau_dsm.json(), dict)
            else None
        )
        profils_esm = (
            tableau_esm.json().get("profils_actifs")
            if tableau_esm.statut == 200 and isinstance(tableau_esm.json(), dict)
            else None
        )
        constater(
            profils_dsm == 1,
            f"tableau de bord, portee DSM (Consultants) : profils_actifs = {profils_dsm!r}, "
            "attendu 1 (son seul consultant)",
            f"tableau de bord, portee DSM : profils_actifs = {profils_dsm!r}, attendu 1",
        )
        constater(
            profils_esm == 5,
            f"TEMOIN D'ASYMETRIE : tableau de bord, portee ESM (Entite) : profils_actifs = "
            f"{profils_esm!r}, attendu 5 (toute l'entite) — DIFFERENT de la portee DSM",
            f"tableau de bord, portee ESM : profils_actifs = {profils_esm!r}, attendu 5",
        )
        reponse_office_tdb = get(cookie_office_a, CHEMIN_TABLEAU_DE_BORD.format(code=code_a))
        constater(
            reponse_office_tdb.statut == 403,
            "tableau de bord : OFFICE refuse (403) — a tiret partout sur le §15.1",
            f"tableau de bord : OFFICE a recu {reponse_office_tdb.statut}, attendu 403",
        )

        # --- 4. le depot d'import (matrice §14 « Charger un CSV ») : ESM
        #     accepte, DSM et OFFICE refuses — meme action, trois reponses.
        contenu_csv = b"email;nom;prenom\r\n;Test;Isolation\r\n"
        refus_dsm = deposer_csv(
            cookie_dsm_a, CHEMIN_IMPORTS.format(code=code_a), "isolation.csv", contenu_csv
        )
        constater(
            refus_dsm.statut == 403,
            "depot d'import : DSM refuse (403) — a tiret, matrice §14",
            f"depot d'import : DSM a recu {refus_dsm.statut}, attendu 403",
        )
        refus_office = deposer_csv(
            cookie_office_a, CHEMIN_IMPORTS.format(code=code_a), "isolation.csv", contenu_csv
        )
        constater(
            refus_office.statut == 403,
            "depot d'import : OFFICE refuse (403) — a tiret, matrice §14",
            f"depot d'import : OFFICE a recu {refus_office.statut}, attendu 403",
        )
        depot = deposer_csv(
            cookie_esm_a, CHEMIN_IMPORTS.format(code=code_a), "isolation.csv", contenu_csv
        )
        constater(
            depot.statut == 201,
            "depot d'import : ESM accepte (201) — meme action que DSM/OFFICE ci-dessus",
            f"depot d'import : ESM a recu {depot.statut}, attendu 201 ({depot.json()!r})",
        )
        depot_corps = depot.json()
        lot_id = depot_corps.get("identifiant") if isinstance(depot_corps, dict) else None
        if lot_id is None:
            print("    ECHEC    aucun lot depose — la partie B (isolation) est irrealisable")
            return 1

        # --- 5. la creation d'entite (cahier §21) : SUPER seul, un LITTERAL,
        #     jamais une grille — l'ESM, pourtant largement outille ailleurs, refuse.
        id_esm_a = _id_personne(compose, env, f"{MARQUEUR}-esm-a@{domaine}")
        refus_creation = poster(
            cookie_esm_a,
            CHEMIN_ENTITES,
            {
                "code": f"{MARQUEUR}-refusee",
                "nom": f"Entite refusee {MARQUEUR}",
                "ville": "Lyon",
                "pays": "FR",
                "fuseau": "Europe/Paris",
                "premier_administrateur": str(id_esm_a),
            },
        )
        constater(
            refus_creation.statut == 403,
            "creation d'entite : ESM refuse (403) — SUPER seul, jamais une grille de plus",
            f"creation d'entite : ESM a recu {refus_creation.statut}, attendu 403",
        )
        creation = poster(
            cookie_super,
            CHEMIN_ENTITES,
            {
                "code": f"{MARQUEUR}-creee",
                "nom": f"Entite creee {MARQUEUR}",
                "ville": "Lyon",
                "pays": "FR",
                "fuseau": "Europe/Paris",
                "premier_administrateur": str(id_esm_a),
            },
        )
        constater(
            creation.statut == 201,
            "creation d'entite : SUPER accepte (201) — meme action que l'ESM refuse ci-dessus",
            f"creation d'entite : SUPER a recu {creation.statut}, attendu 201 "
            f"({creation.json()!r})",
        )

        # ====================================================================
        #  PARTIE B — ISOLATION MULTI-ENTITES PENDANT L'IMPORT (critere 6)
        # ====================================================================

        chemin_rapport_a = CHEMIN_RAPPORT.format(code=code_a, lot=lot_id)
        chemin_rapport_b = CHEMIN_RAPPORT.format(code=code_b, lot=lot_id)
        chemin_lancement_a = CHEMIN_LANCEMENT.format(code=code_a, lot=lot_id)
        chemin_lancement_b = CHEMIN_LANCEMENT.format(code=code_b, lot=lot_id)

        # --- 6. le MEME lot, vu depuis l'AUTRE entite : 404, jamais 403.
        rapport_b_avant = get(cookie_esm_b, chemin_rapport_b)
        constater(
            rapport_b_avant.statut == 404,
            "ISOLATION : le rapport du lot de A est INTROUVABLE (404) depuis B",
            f"rapport du lot depuis B : {rapport_b_avant.statut}, attendu 404 (isolation rompue)",
        )

        # --- 7. le MEME lot, vu depuis SA PROPRE entite : 200 — temoin positif,
        #     sans lequel le refus de B serait indistinguable d'une route cassee.
        rapport_a = get(cookie_esm_a, chemin_rapport_a)
        constater(
            rapport_a.statut == 200,
            "le rapport du lot de A est accessible (200) depuis A — temoin positif",
            f"rapport du lot depuis A : {rapport_a.statut}, attendu 200",
        )
        rapport_a_corps = rapport_a.json()
        lignes_du_rapport = (
            rapport_a_corps.get("lignes") if isinstance(rapport_a_corps, dict) else None
        )
        ligne_id = (
            lignes_du_rapport[0]["identifiant"]
            if isinstance(lignes_du_rapport, list) and lignes_du_rapport
            else None
        )

        # --- 8. lancer l'import DEPUIS B : 404, le lot n'existe pas dans B.
        lancement_b_refuse = poster(cookie_esm_b, chemin_lancement_b, {})
        constater(
            lancement_b_refuse.statut == 404,
            "ISOLATION : lancer le lot de A DEPUIS B est refuse (404)",
            f"lancement depuis B : {lancement_b_refuse.statut}, attendu 404",
        )

        # --- 9. lancer l'import DEPUIS A : 200 — le lot transitionne vers
        #     `completed` (sa seule ligne reste rejetee, E-EMAIL-001).
        lancement_a = poster(cookie_esm_a, chemin_lancement_a, {})
        constater(
            lancement_a.statut == 200,
            "lancement du lot DEPUIS A : 200 (preview_ready -> completed) — temoin positif",
            f"lancement depuis A : {lancement_a.statut}, attendu 200 ({lancement_a.json()!r})",
        )

        # --- 10. LE TEMOIN LE PLUS DISCRIMINANT : relancer DEPUIS B, main-
        #     tenant que le lot est `completed` dans A. Un refus fonde sur
        #     L'ETAT rendrait 409 (comme pour A ci-dessous) — B rend ENCORE
        #     404, preuve que le refus porte sur L'ENTITE, pas sur l'etat.
        relancement_b = poster(cookie_esm_b, chemin_lancement_b, {})
        constater(
            relancement_b.statut == 404,
            "ISOLATION : le MEME lot, desormais `completed`, reste 404 depuis B "
            "(jamais 409 — l'isolation porte sur l'entite, pas sur l'etat)",
            f"relancement depuis B : {relancement_b.statut}, attendu 404",
        )

        if ligne_id is None:
            echecs += 1
            controles += 1
            print("    ECHEC    aucune ligne dans le rapport — le rejeu est irrealisable")
        else:
            chemin_rejeu_a = CHEMIN_REJEU.format(code=code_a, lot=lot_id, ligne=ligne_id)
            chemin_rejeu_b = CHEMIN_REJEU.format(code=code_b, lot=lot_id, ligne=ligne_id)

            # --- 11. rejouer la ligne DEPUIS A : lot ET ligne trouves, mais
            #     `E-EMAIL-001` est HORS DE PORTEE du rejeu — 409, pas 404.
            rejeu_a = poster(cookie_esm_a, chemin_rejeu_a, {})
            constater(
                rejeu_a.statut == 409,
                "rejeu DEPUIS A : 409 rejeu_hors_portee — lot ET ligne trouves, anomalie "
                "d'e-mail hors de portee (temoin positif, pas une isolation)",
                f"rejeu depuis A : {rejeu_a.statut}, attendu 409",
            )

            # --- 12. la MEME ligne, le MEME lot, rejoues DEPUIS B : 404 — le
            #     couple 409 (A) / 404 (B) sur des identifiants IDENTIQUES est
            #     la preuve la plus directe que seule l'entite discrimine.
            rejeu_b = poster(cookie_esm_b, chemin_rejeu_b, {})
            constater(
                rejeu_b.statut == 404,
                "ISOLATION : la MEME ligne, le MEME lot, sont INTROUVABLES (404) depuis B "
                "— contraste avec le 409 obtenu depuis A sur les MEMES identifiants",
                f"rejeu depuis B : {rejeu_b.statut}, attendu 404",
            )

    finally:
        #  MinIO d'abord : la cle depend de l'entite A, encore en base ici.
        code_retour, sortie_id_entite_a = psql(
            compose,
            env,
            f"SELECT id FROM entity WHERE code = '{code_a}'",  # noqa: S608
        )
        id_entite_a = sortie_id_entite_a.strip() if code_retour == 0 else ""
        if id_entite_a and lot_id:
            mc(
                compose,
                f"mc rm local/{env.get('MINIO_BUCKET', '')}/imports/{id_entite_a}/{lot_id}.csv",
            )
        _, sortie_menage = psql(
            compose,
            env,
            f"""
            DO $$
            DECLARE ids uuid[];
            BEGIN
              SELECT array_agg(id) INTO ids FROM person WHERE email LIKE '{MARQUEUR}%';
              DELETE FROM import_decision WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM import_row_issue WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM import_row WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM import_batch WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM dsm_assignment WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM framework_responsibility_assignment WHERE person_id = ANY(ids);
              DELETE FROM technical_role_assignment WHERE person_id = ANY(ids);
              DELETE FROM admin_password_credential WHERE user_account_id IN (
                SELECT id FROM user_account WHERE person_id = ANY(ids));
              DELETE FROM auth_event WHERE person_id = ANY(ids);
              DELETE FROM user_session WHERE person_id = ANY(ids);
              DELETE FROM user_account WHERE person_id = ANY(ids);
              DELETE FROM entity_membership WHERE person_id = ANY(ids);
              DELETE FROM person WHERE id = ANY(ids);
              DELETE FROM office WHERE entity_id IN (
                SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%');
              DELETE FROM entity WHERE code LIKE '{MARQUEUR}%';
            END $$;
            """,  # noqa: S608
        )
        print(f"    info     menage : {sortie_menage[:200] or 'DO'}")

    print()
    print(f"  --> {controles} controles, {echecs} echec(s)")
    return 1 if echecs else 0


def _id_personne(compose: list[str], env: dict[str, str], email: str) -> str:
    _, sortie = psql(
        compose,
        env,
        f"SELECT id FROM person WHERE email = '{email}'",  # noqa: S608
    )
    return sortie.strip()


if __name__ == "__main__":
    raise SystemExit(main())
