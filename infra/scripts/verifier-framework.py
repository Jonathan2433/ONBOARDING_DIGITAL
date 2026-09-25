"""La page Framework, eprouvee A TRAVERS CADDY avec une vraie session.

LOT 6, sous-etape `T2`, story `MVP-L06-US001`.

POURQUOI UN CONTROLE DE STACK EN PLUS DES TESTS

  Les tests de `test_framework.py` appellent le SERVICE. Ils ne disent rien du
  routage, de la session, du format de la reponse HTTP, ni de ce que le client
  recoit vraiment. **Un bouchon prouve ce qu'on a ecrit dans le bouchon** --
  §7.43, et deux defauts sont tombes ainsi en `T11` du LOT 5, au premier appel
  reel.

LE CONTROLE LE PLUS UTILE DE CE FICHIER N'EST PAS UN REFUS

  C'est la recherche de la chaine **« None »** dans les OCTETS servis. Le defaut
  `T10-8` a servi cette chaine sur 100 % des cercles pendant deux lots, et aucun
  controle de forme ne l'a vue : un jeton « None » est un jeton d'apparence
  parfaitement plausible. Le decor porte donc un cercle AVEC jeton et un cercle
  SANS, et les octets sont lus.
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
CHEMIN_FRAMEWORK = "/api/v1/entities/{code}/framework"
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"
CHEMIN_CERCLE = "/api/v1/entities/{code}/circles/{code_cercle}"
CHEMIN_BUREAU = "/api/v1/entities/{code}/offices/{code_bureau}"
CHEMIN_PAGE = "/api/v1/entities/{code}/pages/{type_de_page}/{slug}"
#  LOT 6, `T6` : l'ECRITURE. La creation adresse la collection, l'ecriture
#  adresse la page par son IDENTIFIANT -- elle porte d'abord sur des BROUILLONS,
#  que la lecture ne sert pas.
CHEMIN_CREATION = "/api/v1/entities/{code}/pages"
CHEMIN_CONTENU = "/api/v1/entities/{code}/pages/{page}/contenu"
CHEMIN_PUBLICATION = "/api/v1/entities/{code}/pages/{page}/publication"
CHEMIN_ARCHIVAGE = "/api/v1/entities/{code}/pages/{page}/archivage"
CHEMIN_RESTAURATION = "/api/v1/entities/{code}/pages/{page}/restauration"
#  `T10` — LA LECTURE POUR L'EDITEUR. Le trou que `T6` et `T7` n'avaient pas
#  comble : la lecture de `T5` (`CHEMIN_PAGE`) ne sert que le PUBLIE, sans
#  `version`. Ces deux routes servent TOUS les etats, avec elle.
CHEMIN_PAGES_GESTION = "/api/v1/entities/{code}/pages/gestion"
CHEMIN_PAGE_GESTION = "/api/v1/entities/{code}/pages/{page}/gestion"
#  `T8` — les liens internes. **DEUX LECTURES, ET C'EST VOULU** : l'accueil ne
#  sert que les liens ACTIFS, la gestion les sert tous. Un lien desactive qu'on
#  ne pourrait plus voir serait un lien qu'on ne pourrait plus reactiver.
CHEMIN_LIENS = "/api/v1/entities/{code}/liens"
CHEMIN_LIENS_GESTION = "/api/v1/entities/{code}/liens/gestion"
CHEMIN_ORDRE_DES_LIENS = "/api/v1/entities/{code}/liens/ordre"
CHEMIN_UN_LIEN = "/api/v1/entities/{code}/liens/{lien}"
CHEMIN_SESSION = "/api/v1/auth/session"
EN_TETE_JETON = "X-CSRF-Token"
#  La charge qui a coule des projets entiers. Elle est SERVIE, et c'est le
#  propos de `T5` : elle doit arriver comme une DONNEE, dans du JSON.
INJECTION = "<script>alert('xss')</script>"

MARQUEUR = f"t2l6-{uuid.uuid4().hex[:10]}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l6t2-egalite-des-refus"
#  Voir `verifier-entites.py` : a travers Caddy, `date` change d'une requete a
#  l'autre. Le controle exige l'egalite de tout le RESTE et annonce l'exclusion.
EN_TETES_NON_COMPARABLES = frozenset({"date"})

#  Les QUATRE responsabilites du cahier §6.2, et les DEUX qui ont une page
#  propre selon l'annexe A §10.1. **Derivees du module, jamais recopiees** : une
#  liste recopiee vieillit au premier ajout (§7.27).


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        depouillee = ligne.strip()
        if not depouillee or depouillee.startswith("#") or "=" not in depouillee:
            continue
        cle, _, brut = depouillee.partition("=")
        valeurs[cle.strip()] = brut.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    #  S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    #  le motif du §7.2 — aucun redecoupage des arguments n'a lieu.
    acheve = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            env.get("POSTGRES_USER", "onboarding_app"),
            "-d",
            env.get("POSTGRES_DB", "onboarding_dev"),
            "-At",
            "-c",
            requete,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return acheve.returncode, (acheve.stdout + acheve.stderr).strip()


def valeur(sortie: str) -> str:
    return sortie.splitlines()[0].strip() if sortie.strip() else ""


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
        comparables = {
            nom: v for nom, v in self.en_tetes.items() if nom not in EN_TETES_NON_COMPARABLES
        }
        return self.statut, self.json(), comparables


def appeler(
    base: str,
    chemin: str,
    contexte: ssl.SSLContext,
    *,
    charge: dict[str, object] | None = None,
    en_tetes: dict[str, str] | None = None,
    methode: str | None = None,
) -> Reponse:
    """Un aller-retour HTTP. `methode` n'est explicite que pour `PUT`.

    **`T6` A AJOUTE `methode`, POUR LE MEME MOTIF QUE `T7` DU LOT 5.** La
    deduction « charge => POST, sinon GET » couvrait les routes de lecture ;
    l'ecriture d'un contenu est un `PUT`, et l'envoyer en `POST` rendrait **405**
    -- un refus, donc un controle de refus vert pour la mauvaise raison.
    """
    entetes = {"Content-Type": "application/json"} if charge is not None else {}
    entetes.update(en_tetes or {})
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method=methode or ("POST" if charge is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_HTTP, context=contexte) as r:  # noqa: S310
            return Reponse(r.status, r.read(), list(r.headers.items()))
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
    from app.content.modeles import TYPES_DE_BLOC
    from app.organization.framework import (
        RESPONSABILITES_A_PAGE_PROPRE,
        RESPONSABILITES_FRAMEWORK,
    )
    from app.shared.pagination import TAILLES_DE_PAGE

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    adresse = f"{MARQUEUR}@{domaine}"
    #  Trois adresses de membres, distinctes de celle de l'administrateur.
    adresse_p = f"{MARQUEUR}-principale@{domaine}"
    adresse_s = f"{MARQUEUR}-secondaire@{domaine}"
    adresse_d = f"{MARQUEUR}-brouillon@{domaine}"
    #  **`T6` : UNE PERSONNE AVEC UN COMPTE ET AUCUNE RESPONSABILITE.** Sans
    #  elle, le refus de role ne serait prouve par rien a travers la pile : la
    #  personne du decor est ESM, Booster ET responsable de bureau.
    adresse_sans_droit = f"{MARQUEUR}-sansdroit@{domaine}"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    code_actif = f"{MARQUEUR}-ACT"
    code_brouillon = f"{MARQUEUR}-DRA"

    print()
    print("  Framework et cercles — US001 et US002, cahier §10.3 et §18.2")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(
        f"    info     {len(RESPONSABILITES_FRAMEWORK)} responsabilites du §6.2, "
        f"{len(RESPONSABILITES_A_PAGE_PROPRE)} avec page propre (§10.1)"
    )

    echecs = 0
    controles = 0
    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)

    #  S608 : les seules valeurs interpolees viennent de ce module — `MARQUEUR`
    #  est un `uuid4`. `psql` n'accepte pas de parametre lie dans un bloc `DO`.
    #  **PAS DE DOUBLEMENT D'ACCOLADES ICI.** Une valeur SUBSTITUEE dans une
    #  f-string est inseree telle quelle : seules les accolades LITTERALES du
    #  gabarit se doublent. Les doubler aurait produit du JSON invalide.
    injection = json.dumps({"texte": INJECTION})
    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; c uuid; ce uuid; cs uuid; bu uuid; bp uuid; pg uuid;
            mp uuid; ms uuid; md uuid; ap uuid; a2 uuid; a3 uuid; sd uuid; csd uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone, activated_at)
      VALUES ('{code_actif}', 'Entite {MARQUEUR}', 'Bordeaux', 'FR', 'active',
              'Europe/Paris', now()) RETURNING id INTO e;
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_brouillon}', 'Brouillon {MARQUEUR}', 'Lille', 'FR', 'draft', 'Europe/Paris');

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'L6T2', 'active') RETURNING id INTO p;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);

      -- **LE COUPLE DU §7.42** : un cercle AVEC jeton, un cercle SANS.
      INSERT INTO circle (entity_id, code, name, color_token, display_order)
      VALUES (e, '{MARQUEUR}-AVEC', 'Avec jeton', 'bleu', 1) RETURNING id INTO ce;
      INSERT INTO circle (entity_id, code, name, color_token, display_order)
      VALUES (e, '{MARQUEUR}-SANS', 'Sans jeton', NULL, 2) RETURNING id INTO cs;
      -- Un cercle ARCHIVE, qui ne doit pas paraitre.
      INSERT INTO circle (entity_id, code, name, display_order, archived_at)
      VALUES (e, '{MARQUEUR}-ARCH', 'Archive', 3, now());

      INSERT INTO office (entity_id, code, name, display_order)
      VALUES (e, '{MARQUEUR}-BDS', 'Bureau des sports', 1) RETURNING id INTO bu;

      -- **LE DECOR DE `T4`, ET IL PRODUIT CE QUE LE §8.4 INTERDIT.**
      --
      -- Un bureau PUBLIE a ZERO responsable. Aucune contrainte de base ne
      -- l'empeche -- « entre un et trois » est un comptage borne, et le
      -- declencheur qui le tiendra est en `T7` (`DEC-583`). Une lecture qui
      -- supposerait « au moins un » s'effondrerait ici, et personne ne l'aurait
      -- vu avec un decor a deux responsables.
      --
      -- Il porte AUSSI l'autre moitie du couple du §7.42 : `location_text` est
      -- « Facultatif » au §8.3, donc nullable, et le bureau ci-dessus n'en a pas.
      INSERT INTO office (entity_id, code, name, location_text, display_order)
      VALUES (e, '{MARQUEUR}-PUB', 'Bureau publie', 'Bordeaux, 2e etage', 2)
      RETURNING id INTO bp;
      -- **C'EST LA PAGE QUI PUBLIE, JAMAIS LA TABLE `office`** -- `DEC-576`.
      INSERT INTO content_page (entity_id, page_type, office_id, title, slug, state)
      VALUES (e, 'OFFICE', bp, 'Bureau publie', '{MARQUEUR}-pub', 'published')
      RETURNING id INTO pg;

      -- **LE DECOR DE `T5`.** Trois blocs sur la page publiee : deux legitimes
      -- dans un ordre a retablir, et un ARCHIVE qui ne doit pas paraitre.
      -- Le second porte du BALISAGE : il doit arriver comme une chaine JSON.
      INSERT INTO content_block
        (entity_id, content_page_id, block_type, display_order, payload_json)
      VALUES (e, pg, 'TITLE', 2, '{{"texte": "Le second"}}'::jsonb);
      INSERT INTO content_block
        (entity_id, content_page_id, block_type, display_order, payload_json)
      -- **GUILLEMET-DOLLAR, ET C'EST NECESSAIRE** : la charge contient des
      -- APOSTROPHES -- `alert('xss')` -- qui casseraient un litteral SQL
      -- ordinaire. Les doubler marcherait aussi, mais altererait la chaine
      -- que le controle cherchera ensuite dans les OCTETS servis.
      VALUES (e, pg, 'RICH_TEXT', 1, $json${injection}$json$::jsonb);
      INSERT INTO content_block
        (entity_id, content_page_id, block_type, display_order, payload_json, archived_at)
      VALUES (e, pg, 'QUOTE', 3, '{{"texte": "archive"}}'::jsonb, now());

      -- Une page en BROUILLON : elle doit rendre le MEME 404 qu'un slug inconnu,
      -- sans quoi `US006` -- previsualiser puis publier -- n'aurait plus de sens.
      INSERT INTO content_page (entity_id, page_type, title, slug, state)
      VALUES (e, 'HOME', 'Brouillon', '{MARQUEUR}-draft', 'draft');
      -- Un bureau ARCHIVE, qui doit rendre le MEME 404 qu'un code inconnu.
      INSERT INTO office (entity_id, code, name, display_order, archived_at)
      VALUES (e, '{MARQUEUR}-BARCH', 'Bureau archive', 3, now());

      -- Un ESM ACTIF, un Booster ACTIF sur le cercle AVEC jeton, et un
      -- responsable de bureau ACTIF. Le cercle SANS jeton n'a PAS de Booster :
      -- sans ce contraste, une jointure qui ne joint jamais passerait.
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (p, e, 'ESM', p, now() - interval '1 day');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id, starts_at)
      VALUES (p, e, 'BOOSTER', ce, p, now() - interval '1 day');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, office_id, assigned_by_person_id, starts_at)
      VALUES (p, e, 'OFFICE_MANAGER', bu, p, now() - interval '1 day');
      -- Un DSM FUTUR : il ne doit nommer personne aujourd'hui.
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at)
      VALUES (p, e, 'DSM', p, now() + interval '30 days');

      -- LES MEMBRES DU CERCLE `AVEC`, pour la page detaillee de `T3`.
      --
      -- TROIS PERSONNES, ET LA TROISIEME EST LE TEMOIN : deux appartenances
      -- `active` + `published`, l'une PRINCIPALE l'autre SECONDAIRE, et une
      -- troisieme dont le profil est `draft` et qui ne doit PAS paraitre. Sans
      -- elle, un filtre de visibilite absent donnerait la meme observation.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_p}', '{adresse_p}', 'Ada', 'Principale', 'active') RETURNING id INTO mp;
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, mp, date '2026-01-01', 'active', 'consultant', 'published') RETURNING id INTO ap;
      INSERT INTO circle_membership
        (entity_id, entity_membership_id, circle_id, membership_type, starts_at)
      VALUES (e, ap, ce, 'principal', now() - interval '1 day');

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_s}', '{adresse_s}', 'Bob', 'Secondaire', 'active') RETURNING id INTO ms;
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, ms, date '2026-01-01', 'active', 'consultant', 'published') RETURNING id INTO a2;
      INSERT INTO circle_membership
        (entity_id, entity_membership_id, circle_id, membership_type, starts_at)
      VALUES (e, a2, ce, 'secondary', now() - interval '1 day');

      -- **`T6` : UNE PERSONNE AVEC UN COMPTE ET AUCUNE RESPONSABILITE.** Elle
      -- se connecte comme les autres -- un temoin l'exige -- et n'a donc que
      -- `EMP` : le §13 ne lui donne aucune ecriture editoriale.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_sans_droit}', '{adresse_sans_droit}', 'Sans', 'Droit', 'active')
      RETURNING id INTO sd;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (sd, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO csd;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (csd, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_d}', '{adresse_d}', 'Cle', 'Brouillon', 'active') RETURNING id INTO md;
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, md, date '2026-01-01', 'active', 'consultant', 'draft') RETURNING id INTO a3;
      INSERT INTO circle_membership
        (entity_id, entity_membership_id, circle_id, membership_type, starts_at)
      VALUES (e, a3, ce, 'principal', now() - interval '1 day');
      -- **`T6` : LES DEUX ACTEURS ONT UNE APPARTENANCE, ET C'EST INDISPENSABLE.**
      --
      -- `resoudre_les_permissions` part de `entite_principale(personne)` : une
      -- personne SANS appartenance occupante ressort avec un ensemble de roles
      -- VIDE, quelles que soient ses responsabilites Framework. Le decor n'en
      -- posait aucune, si bien que l'ESM du decor -- qui porte pourtant une
      -- responsabilite `ESM` active -- recevait **403 `acces_refuse`** sur la
      -- creation. Defaut `T6-4`.
      --
      -- **AUCUN TEST UNITAIRE NE POUVAIT LE DIRE** : les trente-six tests de
      -- `T6` passent `roles` a la main, la pile les DERIVE. C'est le §7.43 --
      -- un bouchon prouve ce qu'on a ecrit dans le bouchon.
      --
      -- Celle de `sd` compte autant que celle de `p` : sans elle, son refus
      -- viendrait de l'absence d'appartenance et non de la grille du §13, et
      -- le controle prouverait autre chose que ce qu'il annonce.
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, p, date '2026-01-01', 'active', 'consultant', 'published');
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, sd, date '2026-01-01', 'active', 'consultant', 'published');
    END $$;
    """  # noqa: S608
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print(
        "    ok       decor : 1 entite active, 1 brouillon, 3 cercles, 3 bureaux "
        "dont UN publie a ZERO responsable et UN archive, 4 responsabilites dont "
        "UNE future, 5 appartenances dont UN profil en brouillon, et 1 compte "
        "SANS aucune responsabilite"
    )

    try:
        # --- 1. sans cookie : la matrice §5 met `ANON` a tiret
        controles += 1
        sans = appeler(
            arguments.base,
            CHEMIN_FRAMEWORK.format(code=code_actif),
            contexte,
            en_tetes={"X-Request-ID": CORRELATION_FIXE},
        )
        if sans.statut == 401:
            print("    ok       sans cookie : 401 — matrice §5, `ANON` est a tiret")
        else:
            echecs += 1
            print(f"    ECHEC    sans cookie : {sans.statut} au lieu de 401")

        # --- 2. TEMOIN : la connexion pose un cookie
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
            print("    ok       TEMOIN : la connexion reussit et pose un cookie")
        else:
            echecs += 1
            print(
                f"    ECHEC    TEMOIN : connexion {connexion.statut}, cookie "
                f"{'pose' if cookie else 'ABSENT'}"
            )
            raise RuntimeError("sans session, les controles suivants ne prouveraient rien")
        entetes = {"Cookie": cookie}

        # --- 3. la page est servie
        controles += 1
        page = appeler(
            arguments.base, CHEMIN_FRAMEWORK.format(code=code_actif), contexte, en_tetes=entetes
        )
        corps = page.json()
        if page.statut == 200 and isinstance(corps, dict):
            print("    ok       avec cookie : 200 et un objet JSON")
        else:
            echecs += 1
            print(f"    ECHEC    avec cookie : {page.statut}, corps {str(corps)[:120]}")
            raise RuntimeError("sans reponse exploitable, la suite ne prouverait rien")

        # --- 4. LES TROIS FAMILLES SONT PRESENTES
        controles += 1
        familles = {"responsabilites", "cercles", "bureaux"}
        manquantes = familles - set(corps)
        if not manquantes:
            print("    ok       les TROIS familles du §10.3 sont presentes")
        else:
            echecs += 1
            print(f"    ECHEC    famille(s) absente(s) : {sorted(manquantes)}")

        # --- 5. les QUATRE responsabilites, dans l'ordre du §6.2
        controles += 1
        rendues = tuple(r["type_de_responsabilite"] for r in corps.get("responsabilites", []))
        if rendues == RESPONSABILITES_FRAMEWORK:
            print(f"    ok       les {len(rendues)} responsabilites, dans l'ordre du §6.2")
        else:
            echecs += 1
            print(
                f"    ECHEC    responsabilites rendues {rendues}, attendu "
                f"{RESPONSABILITES_FRAMEWORK}"
            )

        # --- 6. DSM et ESM ont un chemin, BOOSTER et OFFICE_MANAGER `null`
        controles += 1
        chemins = {
            r["type_de_responsabilite"]: r["chemin_detaille"]
            for r in corps.get("responsabilites", [])
        }
        avec = {t for t, c in chemins.items() if c is not None}
        if avec == set(RESPONSABILITES_A_PAGE_PROPRE):
            print("    ok       seules DSM et ESM portent un chemin — annexe A §10.1")
        else:
            echecs += 1
            print(
                f"    ECHEC    chemins presents sur {sorted(avec)}, attendu "
                f"{sorted(RESPONSABILITES_A_PAGE_PROPRE)}"
            )

        # --- 7. LE COUPLE DE JETON, ET LA CHAINE « None » DANS LES OCTETS
        controles += 1
        par_code = {c["code"]: c for c in corps.get("cercles", [])}
        avec_jeton = par_code.get(f"{MARQUEUR}-AVEC", {}).get("jeton_de_couleur")
        sans_jeton = par_code.get(f"{MARQUEUR}-SANS", {})
        jeton_absent = "jeton_de_couleur" in sans_jeton and sans_jeton["jeton_de_couleur"] is None
        if avec_jeton == "bleu" and jeton_absent and b'"None"' not in page.corps:
            print(
                "    ok       jeton : « bleu » d'un cote, `null` de l'autre, et la "
                "chaine « None » est ABSENTE des octets — defaut `T10-8`"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    jeton : avec={avec_jeton!r}, sans_a_null={jeton_absent}, "
                f"« None » dans les octets = {b'"None"' in page.corps}"
            )

        # --- 8. le Booster ACTIF est nomme, et le cercle SANS n'en a pas
        controles += 1
        booster_avec = par_code.get(f"{MARQUEUR}-AVEC", {}).get("booster")
        booster_sans = par_code.get(f"{MARQUEUR}-SANS", {}).get("booster", "ABSENT")
        if isinstance(booster_avec, dict) and booster_sans is None:
            print(
                "    ok       Booster nomme sur un cercle, `null` sur l'autre — sans ce "
                "contraste, une jointure qui ne joint jamais passerait"
            )
        else:
            echecs += 1
            print(f"    ECHEC    booster avec={booster_avec!r}, sans={booster_sans!r}")

        # --- 9. le cercle ARCHIVE est exclu
        controles += 1
        if f"{MARQUEUR}-ARCH" not in par_code and len(par_code) == 2:
            print("    ok       le cercle archive est exclu — 2 cercles servis sur 3 poses")
        else:
            echecs += 1
            print(f"    ECHEC    cercles servis : {sorted(par_code)}")

        # --- 10. LA RESPONSABILITE FUTURE NE NOMME PERSONNE
        controles += 1
        titulaires_dsm = chemins and [
            r["titulaires"]
            for r in corps["responsabilites"]
            if r["type_de_responsabilite"] == "DSM"
        ]
        titulaires_esm = [
            r["titulaires"]
            for r in corps["responsabilites"]
            if r["type_de_responsabilite"] == "ESM"
        ]
        futur_vide = bool(titulaires_dsm) and titulaires_dsm[0] == []
        actif_plein = bool(titulaires_esm) and len(titulaires_esm[0]) == 1
        if futur_vide and actif_plein:
            print(
                "    ok       la responsabilite FUTURE ne nomme personne, l'ACTIVE si — "
                "le temoin qui rend l'exclusion non triviale"
            )
        else:
            echecs += 1
            print(f"    ECHEC    DSM futur={titulaires_dsm}, ESM actif={titulaires_esm}")

        # --- 11. les bureaux, leurs responsables, et l'archive EXCLU
        #
        #  **CE CONTROLE ATTENDAIT UN SEUL BUREAU JUSQU'AU 15/09/2026**, et c'est
        #  `T4` qui l'a rendu faux en ajoutant a ce decor un bureau PUBLIE a zero
        #  responsable et un bureau ARCHIVE. §7.21 : un controle ne devient pas
        #  faux tout seul, il le devient quand on change le monde autour de lui.
        #
        #  Il n'a pas ete affaibli mais RENDU PLUS EXACT (§7.20) : il exige
        #  desormais le couple — un bureau qui a un responsable, un qui n'en a
        #  aucun — et l'exclusion de l'archive.
        controles += 1
        bureaux = corps.get("bureaux", [])
        par_code = {b.get("code"): b for b in bureaux}
        avec = par_code.get(f"{MARQUEUR}-BDS", {})
        sans = par_code.get(f"{MARQUEUR}-PUB", {})
        if (
            len(bureaux) == 2
            and f"{MARQUEUR}-BARCH" not in par_code
            and len(avec.get("responsables", [])) == 1
            and sans.get("responsables") == []
        ):
            print("    ok       DEUX bureaux non archives : un AVEC responsable, un SANS —")
            print("             le couple, et l'archive est exclu de la synthese")
        else:
            echecs += 1
            print(f"    ECHEC    bureaux : {json.dumps(bureaux)[:220]}")

        # --- 12. un code INCONNU et une entite NON ACTIVE rendent le MEME 404
        controles += 1
        inconnu = appeler(
            arguments.base,
            #  S608 : faux positif. Ce `.format()` construit un CHEMIN D'URL, pas
            #  une requete SQL, et `MARQUEUR` est un `uuid4` de ce module.
            CHEMIN_FRAMEWORK.format(code=f"{MARQUEUR}-XXX"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        brouillon = appeler(
            arguments.base,
            CHEMIN_FRAMEWORK.format(code=code_brouillon),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if inconnu.statut == 404 and inconnu.signature() == brouillon.signature():
            print(
                "    ok       404 identique pour un code inconnu et une entite non "
                f"active — hors {sorted(EN_TETES_NON_COMPARABLES)}, non comparable"
            )
        else:
            echecs += 1
            egales = "egales" if inconnu.signature() == brouillon.signature() else "DIFFERENTES"
            print(
                f"    ECHEC    inconnu {inconnu.statut}, brouillon "
                f"{brouillon.statut}, signatures {egales}"
            )

        # --- 13. le 404 du Framework est celui de `GET /entities/{code}`
        controles += 1
        entite_404 = appeler(
            arguments.base,
            CHEMIN_UNE_ENTITE.format(code=f"{MARQUEUR}-XXX"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if inconnu.json() == entite_404.json():
            print("    ok       le 404 est le MEME que celui de `/entities/{code}`")
        else:
            echecs += 1
            print(
                f"    ECHEC    corps differents : {str(inconnu.json())[:90]} vs "
                f"{str(entite_404.json())[:90]}"
            )

        # =====================================================================
        #  `T3` — la page detaillee d'un cercle. MEME decor, MEME session, MEME
        #  menage : un second verificateur les aurait dupliques (§7.27).
        # =====================================================================

        # --- 14. la page du cercle AVEC jeton est servie
        controles += 1
        chemin_avec = CHEMIN_CERCLE.format(code=code_actif, code_cercle=f"{MARQUEUR}-AVEC")
        page_cercle = appeler(arguments.base, chemin_avec, contexte, en_tetes=entetes)
        corps_cercle = page_cercle.json()
        if page_cercle.statut == 200 and isinstance(corps_cercle, dict):
            print("    ok       page du cercle : 200 et un objet JSON")
        else:
            echecs += 1
            print(f"    ECHEC    page du cercle : {page_cercle.statut}")
            raise RuntimeError("sans page de cercle, les controles suivants ne prouvent rien")

        # --- 15. LE COUPLE DE JETON, ET « None » DANS LES OCTETS
        controles += 1
        chemin_sans = CHEMIN_CERCLE.format(code=code_actif, code_cercle=f"{MARQUEUR}-SANS")
        page_sans = appeler(arguments.base, chemin_sans, contexte, en_tetes=entetes)
        corps_sans = page_sans.json()
        jeton_avec = corps_cercle.get("jeton_de_couleur")
        nul_present = isinstance(corps_sans, dict) and "jeton_de_couleur" in corps_sans
        nul_vaut_nul = nul_present and corps_sans["jeton_de_couleur"] is None
        octets_propres = b'"None"' not in page_cercle.corps and b'"None"' not in page_sans.corps
        if jeton_avec == "bleu" and nul_vaut_nul and octets_propres:
            print("    ok       jeton : « bleu » d'un cote, `null` de l'autre, et la chaine")
            print("             « None » est ABSENTE des octets des DEUX pages — `T10-8`")
        else:
            echecs += 1
            print(
                f"    ECHEC    jeton : avec={jeton_avec!r}, sans_a_null={nul_vaut_nul}, "
                f"octets propres={octets_propres}"
            )

        # --- 16. LA COULEUR N'EST JAMAIS SEULE — §8.1 du modele
        controles += 1
        nom_sans = corps_sans.get("nom") if isinstance(corps_sans, dict) else None
        code_sans = corps_sans.get("code") if isinstance(corps_sans, dict) else None
        if nom_sans and code_sans:
            print("    ok       un cercle SANS couleur porte quand meme son code et son nom —")
            print("             §8.1 : « la couleur ne constitue jamais la seule information »")
        else:
            echecs += 1
            print(f"    ECHEC    cercle sans couleur : nom={nom_sans!r}, code={code_sans!r}")

        # --- 17. les membres : DEUX natures, et le BROUILLON exclu
        controles += 1
        membres = corps_cercle.get("membres", [])
        natures = {m.get("type_d_appartenance") for m in membres}
        noms = {m.get("nom") for m in membres}
        total = corps_cercle.get("total_des_membres")
        if total == 2 and natures == {"principal", "secondary"} and "Brouillon" not in noms:
            print("    ok       2 membres sur 3 poses : les DEUX natures du §8.2 rendues, et")
            print("             le profil `draft` EXCLU — sans ce troisieme, un filtre de")
            print("             visibilite absent donnerait la meme observation")
        else:
            echecs += 1
            print(
                f"    ECHEC    membres : total={total!r}, natures={sorted(natures)}, "
                f"noms={sorted(n for n in noms if n)}"
            )

        # --- 18. LES TROIS TAILLES DU §18.2 SONT SERVIES — le temoin de `T2-3`
        controles += 1
        servies = []
        for taille in TAILLES_DE_PAGE:
            r = appeler(
                arguments.base, f"{chemin_avec}?taille={taille}", contexte, en_tetes=entetes
            )
            charge = r.json()
            if r.statut == 200 and isinstance(charge, dict) and charge.get("taille") == taille:
                servies.append(taille)
        if servies == list(TAILLES_DE_PAGE):
            print(f"    ok       les TROIS tailles du §18.2 sont SERVIES : {servies}")
            print("             c'est le temoin qui a trouve `T2-3` — huit refus restaient")
            print("             verts alors que la route refusait les trois tailles valides")
        else:
            echecs += 1
            print(f"    ECHEC    tailles servies {servies}, attendu {list(TAILLES_DE_PAGE)}")

        # --- 19. une taille HORS du §18.2 est refusee, au format du §18.3
        controles += 1
        hors = appeler(arguments.base, f"{chemin_avec}?taille=30", contexte, en_tetes=entetes)
        if hors.statut == 422:
            print("    ok       taille hors du §18.2 : 422 — le TYPE la refuse, pas la route")
        else:
            echecs += 1
            print(f"    ECHEC    taille=30 : {hors.statut} au lieu de 422")

        # --- 20. un cercle ARCHIVE et un code INCONNU rendent le MEME 404
        controles += 1
        archive = appeler(
            arguments.base,
            CHEMIN_CERCLE.format(code=code_actif, code_cercle=f"{MARQUEUR}-ARCH"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        cercle_inconnu = appeler(
            arguments.base,
            CHEMIN_CERCLE.format(code=code_actif, code_cercle=f"{MARQUEUR}-XXX"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if archive.statut == 404 and archive.signature() == cercle_inconnu.signature():
            print("    ok       404 identique pour un cercle ARCHIVE et un code inconnu —")
            print("             distinguer apprendrait l'existence d'un cercle archive")
        else:
            echecs += 1
            print(f"    ECHEC    archive {archive.statut}, inconnu {cercle_inconnu.statut}")

        # --- 21. `pages` vaut AU MOINS 1 sur un cercle sans membre
        controles += 1
        pages_sans = corps_sans.get("pages") if isinstance(corps_sans, dict) else None
        total_sans = corps_sans.get("total_des_membres") if isinstance(corps_sans, dict) else None
        if total_sans == 0 and pages_sans == 1:
            print("    ok       `pages` vaut 1 sans aucun membre — `0` ne distinguerait pas")
            print("             « aucun membre » de « chargement »")
        else:
            echecs += 1
            print(f"    ECHEC    cercle sans membre : total={total_sans!r}, pages={pages_sans!r}")

        # =====================================================================
        #  `T4` — la page detaillee d'un bureau. MEME decor, MEME session, MEME
        #  menage : un second verificateur les aurait dupliques (§7.27), et il
        #  aurait fallu l'ajouter a `ci.yml` (§7.36).
        # =====================================================================

        # --- 22. la page du bureau AVEC responsable est servie
        controles += 1
        chemin_bureau = CHEMIN_BUREAU.format(code=code_actif, code_bureau=f"{MARQUEUR}-BDS")
        page_bureau = appeler(arguments.base, chemin_bureau, contexte, en_tetes=entetes)
        corps_bureau = page_bureau.json()
        if page_bureau.statut == 200 and isinstance(corps_bureau, dict):
            print("    ok       page du bureau : 200 et un objet JSON")
        else:
            echecs += 1
            print(f"    ECHEC    page du bureau : {page_bureau.statut}")
            raise RuntimeError("sans page de bureau, les controles suivants ne prouvent rien")

        # --- 23. UN BUREAU PUBLIE A ZERO RESPONSABLE EST SERVI TEL QUEL
        #
        #  **C'EST LE CONTROLE LE PLUS UTILE DE `T4`.** Le §8.4 veut « entre un
        #  et trois responsables actifs lorsqu'il est publie » ; aucune
        #  contrainte de base ne l'exprime, et le declencheur est en `T7`
        #  (`DEC-583`). Une lecture qui supposerait « au moins un » s'effondrerait
        #  ici — et le couple est indispensable : sans le bureau A responsable,
        #  une route qui ne rendrait JAMAIS personne passerait aussi.
        controles += 1
        chemin_pub = CHEMIN_BUREAU.format(code=code_actif, code_bureau=f"{MARQUEUR}-PUB")
        page_pub = appeler(arguments.base, chemin_pub, contexte, en_tetes=entetes)
        corps_pub = page_pub.json()
        zero = isinstance(corps_pub, dict) and corps_pub.get("responsables") == []
        publie = isinstance(corps_pub, dict) and corps_pub.get("publie") is True
        un_seul = len(corps_bureau.get("responsables", [])) == 1
        pas_publie = corps_bureau.get("publie") is False
        if page_pub.statut == 200 and zero and publie and un_seul and pas_publie:
            print("    ok       le COUPLE : un bureau PUBLIE a ZERO responsable — ce que le")
            print("             §8.4 interdit et que la base permet — et un bureau NON publie")
            print("             qui a son responsable. La lecture ne suppose pas la borne")
        else:
            echecs += 1
            avec_r = corps_bureau.get("responsables")
            print(f"    ECHEC    publie={corps_pub!r:.140} / avec={avec_r!r:.80}")

        # --- 24. `publie` VIENT DE LA PAGE DE CONTENU, ET LES DEUX SE DISTINGUENT
        #
        #  `DEC-576` : la table `office` ne porte aucun etat de publication. Les
        #  deux bureaux ne different QUE par l'existence d'une `content_page` de
        #  type `OFFICE` a l'etat `published`.
        controles += 1
        if publie and pas_publie:
            print("    ok       `publie` distingue les deux bureaux, et seule la PAGE de")
            print("             contenu les separe — `DEC-576`, apres `ECART-031`")
        else:
            echecs += 1
            print(
                f"    ECHEC    publie(PUB)={corps_pub.get('publie')!r}, "
                f"publie(BDS)={corps_bureau.get('publie')!r}"
            )

        # --- 25. LA LOCALISATION ABSENTE N'EST JAMAIS LA CHAINE « None »
        #
        #  Le §8.3 declare `location_text` « Facultatif ». La chaine est cherchee
        #  dans les OCTETS servis, pas dans la structure decodee : c'est ainsi que
        #  le defaut `T10-8` a ete trouve, et un jeton « None » est une valeur
        #  d'apparence parfaitement plausible.
        controles += 1
        lieu_present = isinstance(corps_bureau, dict) and "localisation" in corps_bureau
        lieu_nul = lieu_present and corps_bureau["localisation"] is None
        lieu_servi = isinstance(corps_pub, dict) and corps_pub.get("localisation") == (
            "Bordeaux, 2e etage"
        )
        octets_sains = b'"localisation":"None"' not in page_bureau.corps.replace(b", ", b",")
        if lieu_nul and lieu_servi and octets_sains:
            print("    ok       le COUPLE de localisation : `null` servi comme `null`, la")
            print("             valeur servie telle quelle, et « None » ABSENTE des octets")
        else:
            echecs += 1
            print(f"    ECHEC    nul={lieu_nul}, servi={lieu_servi}, octets={octets_sains}")

        # --- 26. LES DEUX GRANDEURS S'ACCORDENT — §7.0, sixieme proposition
        controles += 1
        accords = [
            isinstance(c, dict)
            and c.get("nombre_de_responsables") == len(c.get("responsables", []))
            for c in (corps_bureau, corps_pub)
        ]
        if all(accords):
            print("    ok       `nombre_de_responsables` vaut la longueur du tableau sur les")
            print("             DEUX bureaux, y compris celui a zero")
        else:
            echecs += 1
            print(f"    ECHEC    accords={accords}")

        # --- 27. LE CHEMIN SERVI EST CELUI QUE LA CARTE DU FRAMEWORK EMET
        #
        #  **SANS CE CONTROLE, LA CARTE POURRAIT POINTER DANS LE VIDE.** `T2` emet
        #  `chemin_detaille` sur chaque carte ; si la page detaillee en forgeait
        #  un autre, le lien serait mort et aucun test ne le dirait.
        controles += 1
        carte = par_code.get(f"{MARQUEUR}-BDS", {})
        if carte.get("chemin_detaille") == corps_bureau.get("chemin_detaille") != None:  # noqa: E711
            print("    ok       le chemin de la CARTE et celui de la PAGE sont le meme —")
            print(f"             {corps_bureau.get('chemin_detaille')}")
        else:
            echecs += 1
            print(
                f"    ECHEC    carte={carte.get('chemin_detaille')!r} vs "
                f"page={corps_bureau.get('chemin_detaille')!r}"
            )

        # --- 28. un bureau ARCHIVE et un code INCONNU rendent le MEME 404
        controles += 1
        bureau_inconnu = appeler(
            arguments.base,
            CHEMIN_BUREAU.format(code=code_actif, code_bureau=f"{MARQUEUR}-ZZZ"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        bureau_archive = appeler(
            arguments.base,
            CHEMIN_BUREAU.format(code=code_actif, code_bureau=f"{MARQUEUR}-BARCH"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if (
            bureau_archive.statut == 404
            and bureau_archive.signature() == bureau_inconnu.signature()
        ):
            print("    ok       404 identique pour un bureau ARCHIVE et un code inconnu —")
            print("             corps ET en-tetes, distinguer apprendrait son existence")
        else:
            echecs += 1
            print(f"    ECHEC    archive {bureau_archive.statut}, inconnu {bureau_inconnu.statut}")

        # --- 29. SANS COOKIE : la matrice §5 met `ANON` a tiret sur « Bureaux »
        controles += 1
        bureau_anonyme = appeler(arguments.base, chemin_bureau, contexte)
        if bureau_anonyme.statut == 401:
            print("    ok       sans session : 401 — le §5 refuse « Bureaux » a `ANON`")
        else:
            echecs += 1
            print(f"    ECHEC    sans session : {bureau_anonyme.statut}, 401 attendu")

        # =====================================================================
        #  `T5` — le rendu des blocs. MEME decor, MEME session, MEME menage.
        # =====================================================================

        # --- 30. LA PAGE PUBLIEE EST SERVIE, SES BLOCS DANS L'ORDRE
        #
        #  **LE TEMOIN POSITIF DU CRITERE NEGATIF.** « Aucun HTML arbitraire » se
        #  satisfait tout seul quand rien n'est rendu (§7.39) : c'est ce controle
        #  qui rend les suivants non triviaux.
        controles += 1
        chemin_page = CHEMIN_PAGE.format(
            code=code_actif, type_de_page="OFFICE", slug=f"{MARQUEUR}-pub"
        )
        page_contenu = appeler(arguments.base, chemin_page, contexte, en_tetes=entetes)
        corps_page = page_contenu.json()
        blocs = corps_page.get("blocs", []) if isinstance(corps_page, dict) else []
        rangs = [b.get("ordre") for b in blocs]
        if page_contenu.statut == 200 and rangs == [1, 2]:
            print("    ok       page de contenu : 200, DEUX blocs dans l'ordre 1, 2 —")
            print("             le troisieme est ARCHIVE et n'est pas rendu")
        else:
            echecs += 1
            print(f"    ECHEC    page de contenu : {page_contenu.statut}, rangs={rangs}")
            raise RuntimeError("sans page de contenu, les controles suivants ne prouvent rien")

        # --- 31. LE BALISAGE ARRIVE COMME UNE DONNEE, DANS DES OCTETS JSON
        #
        #  **C'EST LE CONTROLE LE PLUS UTILE DE `T5`, ET IL PORTE SUR LES OCTETS.**
        #  Le type de contenu est `application/json` et non `text/html` : aucun
        #  navigateur n'interpretera cette reponse comme un document. Et la charge
        #  s'y trouve TELLE QUELLE, ce qui prouve que rien n'a ete retire en
        #  silence -- un filtre qui aurait mange la chaine donnerait la meme
        #  observation qu'une absence d'injection.
        controles += 1
        type_servi = page_contenu.en_tetes.get("content-type", "")
        octets = page_contenu.corps
        premier = blocs[0].get("contenu", {}) if blocs else {}
        json_et_pas_html = type_servi.startswith("application/json")
        charge_intacte = premier.get("texte") == INJECTION
        dans_les_octets = INJECTION.encode("utf-8") in octets
        if json_et_pas_html and charge_intacte and dans_les_octets:
            print("    ok       le balisage arrive COMME UNE DONNEE : type de contenu")
            print(f"             `{type_servi.split(';')[0]}`, charge INTACTE dans les octets —")
            print("             rien n'est interprete, et rien n'est retire en silence")
        else:
            echecs += 1
            print(
                f"    ECHEC    type={type_servi!r}, intacte={charge_intacte}, "
                f"octets={dans_les_octets}"
            )

        # --- 32. `nombre_de_blocs` VAUT LA LONGUEUR DU TABLEAU
        controles += 1
        annonce = corps_page.get("nombre_de_blocs") if isinstance(corps_page, dict) else None
        if annonce == len(blocs) == 2:
            print("    ok       `nombre_de_blocs` vaut la longueur du tableau")
        else:
            echecs += 1
            print(f"    ECHEC    annonce={annonce!r}, rendus={len(blocs)}")

        # --- 33. UNE PAGE EN BROUILLON REND LE MEME 404 QU'UN SLUG INCONNU
        #
        #  Distinguer apprendrait l'existence du brouillon, et viderait `US006`
        #  -- « previsualiser puis publier » -- de son sens. C'est `T7`.
        controles += 1
        brouillon = appeler(
            arguments.base,
            CHEMIN_PAGE.format(code=code_actif, type_de_page="HOME", slug=f"{MARQUEUR}-draft"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        slug_inconnu = appeler(
            arguments.base,
            CHEMIN_PAGE.format(code=code_actif, type_de_page="HOME", slug=f"{MARQUEUR}-zzz"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if brouillon.statut == 404 and brouillon.signature() == slug_inconnu.signature():
            print("    ok       404 identique pour un BROUILLON et un slug inconnu —")
            print("             corps ET en-tetes ; `US006` garde son sens")
        else:
            echecs += 1
            print(f"    ECHEC    brouillon {brouillon.statut}, inconnu {slug_inconnu.statut}")

        # --- 34. UN TYPE DE PAGE INCONNU REND LE MEME 404
        controles += 1
        type_inconnu = appeler(
            arguments.base,
            CHEMIN_PAGE.format(code=code_actif, type_de_page="INEXISTANT", slug=f"{MARQUEUR}-pub"),
            contexte,
            en_tetes={**entetes, "X-Request-ID": CORRELATION_FIXE},
        )
        if type_inconnu.signature() == slug_inconnu.signature():
            print("    ok       un TYPE de page inconnu rend le meme 404 — le refuser en")
            print("             422 decrirait le schema a qui n'y a pas droit")
        else:
            echecs += 1
            print(f"    ECHEC    type inconnu : {type_inconnu.statut}")

        # --- 35. SANS COOKIE : le §5 refuse la ressource a `ANON`
        controles += 1
        page_anonyme = appeler(arguments.base, chemin_page, contexte)
        if page_anonyme.statut == 401:
            print("    ok       sans session : 401 — et l'annexe A §13, dont la ligne")
            print("             « Consulter » n'a ni `EMP` ni `NEW`, n'y change rien")
        else:
            echecs += 1
            print(f"    ECHEC    sans session : {page_anonyme.statut}, 401 attendu")

        # ==================================================================
        #
        #  `T6` — L'ECRITURE D'UN CONTENU DANS SON PERIMETRE, `MVP-L06-US004`
        #
        #    **UN BOUCHON PROUVE CE QU'ON A ECRIT DANS LE BOUCHON** (§7.43), et
        #    les trente-six tests de `T6` appellent le SERVICE. Ils ne disent
        #    rien du routage, de la session, du CSRF, du code HTTP ni des
        #    OCTETS. Ces controles-la font l'aller-retour REEL : creer, ecrire,
        #    publier, relire -- et la charge d'injection est cherchee dans les
        #    octets servis, comme `T5` le fait pour la lecture.
        #
        # ==================================================================

        # --- 36. SANS COOKIE, LA CREATION REND 401
        controles += 1
        creation_anonyme = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={"type_de_page": "HOME", "titre": "x", "slug": f"{MARQUEUR}-anon"},
        )
        if creation_anonyme.statut == 401:
            print("    ok       creation sans session : 401 — la matrice §5 met `ANON` a tiret")
        else:
            echecs += 1
            print(f"    ECHEC    creation sans session : {creation_anonyme.statut}")

        # --- 37. TEMOIN : `GET /auth/session` rend le jeton CSRF de l'ESM
        controles += 1
        session = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=entetes)
        corps_session = session.json()
        jeton_csrf = corps_session.get("jeton_csrf", "") if isinstance(corps_session, dict) else ""
        if session.statut == 200 and jeton_csrf:
            print("    ok       TEMOIN : la session de l'ESM rend un jeton CSRF")
        else:
            echecs += 1
            print(f"    ECHEC    session {session.statut}, jeton {'oui' if jeton_csrf else 'NON'}")
            raise RuntimeError("sans jeton CSRF, aucune ecriture ne prouverait quoi que ce soit")
        ecriture = {**entetes, EN_TETE_JETON: jeton_csrf, "Origin": arguments.base}

        # --- 38. SANS JETON CSRF, L'ECRITURE EST REFUSEE
        #
        #  La session est valide et le role suffisant : **seul le jeton manque**.
        #  Sans ce controle, la protection CSRF d'une route d'ecriture metier ne
        #  serait prouvee par rien -- aucun test unitaire ne peut l'observer.
        controles += 1
        sans_csrf = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={"type_de_page": "HOME", "titre": "x", "slug": f"{MARQUEUR}-csrf"},
            en_tetes={**entetes, "Origin": arguments.base},
        )
        corps_csrf = sans_csrf.json()
        code_csrf = (
            corps_csrf.get("erreur", {}).get("code") if isinstance(corps_csrf, dict) else None
        )
        if sans_csrf.statut == 403 and code_csrf == "requete_refusee":
            print("    ok       sans jeton CSRF : 403 `requete_refusee` — la session et le")
            print("             role suffisent pourtant ; SEUL le jeton manque")
        else:
            echecs += 1
            print(f"    ECHEC    sans jeton CSRF : {sans_csrf.statut}, {str(corps_csrf)[:140]}")

        # --- 39. LA CREATION REND 201, ET LA PAGE NAIT EN BROUILLON
        controles += 1
        slug_t6 = f"{MARQUEUR}-t6"
        creation = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={"type_de_page": "HOME", "titre": "Page de T6", "slug": slug_t6},
            en_tetes=ecriture,
        )
        corps_creation = creation.json()
        page_creee = corps_creation.get("identifiant") if isinstance(corps_creation, dict) else None
        etat_creee = corps_creation.get("etat") if isinstance(corps_creation, dict) else None
        if creation.statut == 201 and page_creee and etat_creee == "draft":
            print("    ok       creation : 201, et la page nait `draft` — le §13 separe")
            print("             « Modifier » (Entite) de « Publier » (PERIMETRE), `US006`")
        else:
            echecs += 1
            print(f"    ECHEC    creation : {creation.statut}, {str(corps_creation)[:160]}")
            raise RuntimeError("sans page creee, la suite ne prouverait rien")

        # --- 40. L'ECRITURE DU CONTENU REND 200, ET LES ORDRES SONT CEUX DU TABLEAU
        controles += 1
        chemin_contenu = CHEMIN_CONTENU.format(code=code_actif, page=page_creee)
        ecrit = appeler(
            arguments.base,
            chemin_contenu,
            contexte,
            charge={
                "version": 1,
                "titre": "Page de T6",
                "blocs": [
                    {"type_de_bloc": "TITLE", "contenu": {"texte": "Bienvenue"}},
                    {"type_de_bloc": "RICH_TEXT", "contenu": {"texte": INJECTION}},
                ],
            },
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_ecrit = ecrit.json()
        blocs_ecrits = corps_ecrit.get("blocs", []) if isinstance(corps_ecrit, dict) else []
        ordres = [b.get("ordre") for b in blocs_ecrits]
        if ecrit.statut == 200 and ordres == [0, 1] and corps_ecrit.get("version") == 2:
            print("    ok       ecriture : 200, ordres [0, 1] DERIVES du tableau, version a 2")
        else:
            echecs += 1
            print(f"    ECHEC    ecriture : {ecrit.statut}, {str(corps_ecrit)[:200]}")

        # --- 41. LA PAGE EN BROUILLON N'EST PAS SERVIE, MEME A SON AUTEUR
        controles += 1
        avant_publication = appeler(
            arguments.base,
            CHEMIN_PAGE.format(code=code_actif, type_de_page="HOME", slug=slug_t6),
            contexte,
            en_tetes=entetes,
        )
        if avant_publication.statut == 404:
            print("    ok       le brouillon n'est PAS servi, meme a qui vient de l'ecrire —")
            print("             le critere de sortie n°1 : relus AVANT publication")
        else:
            echecs += 1
            print(f"    ECHEC    brouillon servi : {avant_publication.statut}")

        # --- 42. **L'ALLER-RETOUR COMPLET, ET IL PORTE SUR LES OCTETS**
        #
        #  La publication est faite en SQL, parce que la route de publication est
        #  `T7` : ce controle prouve l'ECRITURE, pas la publication. Ce qu'il
        #  exige ensuite est ce que `T5` exige de la lecture -- type de contenu
        #  `application/json`, et la charge INTACTE dans les octets.
        #
        #  **Un filtre qui aurait mange la chaine donnerait la meme observation
        #  qu'une absence d'injection** : c'est pourquoi on la cherche dans les
        #  octets, et non « un 200 et des blocs ».
        controles += 1
        code_pub, sortie_pub = psql(
            compose,
            env,
            #  S608 : `page_creee` est un identifiant rendu par NOTRE API, jamais
            #  une entree de tiers. La publication passe par SQL parce que la
            #  route de publication est `T7` : ce controle prouve l'ECRITURE.
            "UPDATE content_page SET state = 'published', published_at = now() "  # noqa: S608
            f"WHERE id = '{page_creee}'",
        )
        apres = appeler(
            arguments.base,
            CHEMIN_PAGE.format(code=code_actif, type_de_page="HOME", slug=slug_t6),
            contexte,
            en_tetes=entetes,
        )
        corps_apres = apres.json()
        blocs_lus = corps_apres.get("blocs", []) if isinstance(corps_apres, dict) else []
        type_servi_t6 = apres.en_tetes.get("content-type", "")
        intacte = INJECTION.encode("utf-8") in apres.corps
        rendu_comme_donnee = (
            len(blocs_lus) == 2
            and blocs_lus[1].get("contenu", {}).get("texte") == INJECTION
            and type_servi_t6.startswith("application/json")
        )
        if code_pub == 0 and apres.statut == 200 and rendu_comme_donnee and intacte:
            print("    ok       ALLER-RETOUR REEL : ecrit par l'API, relu par l'API — la charge")
            print("             traverse INTACTE dans les octets, en `application/json`, et")
            print("             rien n'a ete retire en silence")
        else:
            echecs += 1
            print(
                f"    ECHEC    aller-retour : publication={code_pub} ({sortie_pub[:60]}), "
                f"lecture={apres.statut}, intacte={intacte}, type={type_servi_t6!r}"
            )

        # --- 43. UN SECOND PASSAGE ARCHIVE LES BLOCS RETIRES, ET LE DIT
        controles += 1
        reduit = appeler(
            arguments.base,
            chemin_contenu,
            contexte,
            charge={
                "version": 2,
                "titre": "Page de T6",
                "blocs": [{"type_de_bloc": "TITLE", "contenu": {"texte": "Seul"}}],
            },
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_reduit = reduit.json()
        archives = corps_reduit.get("blocs_archives") if isinstance(corps_reduit, dict) else None
        code_cpt, sortie_cpt = psql(
            compose,
            env,
            "SELECT count(*) FROM content_block "  # noqa: S608
            f"WHERE content_page_id = '{page_creee}'",
        )
        total_en_base = valeur(sortie_cpt)
        if reduit.statut == 200 and archives == 2 and total_en_base == "3":
            print("    ok       les blocs retires sont ARCHIVES et non SUPPRIMES (modele §2.4) :")
            print("             `blocs_archives` = 2, et 3 lignes SUBSISTENT en base")
        else:
            echecs += 1
            print(
                f"    ECHEC    archivage : {reduit.statut}, archives={archives}, "
                f"lignes en base={total_en_base!r} (code {code_cpt})"
            )

        # --- 44. L'ECRITURE NE TOUCHE NI `state` NI `published_at`
        #
        #  La page vient d'etre publiee, puis reecrite deux fois. Si `T6`
        #  touchait l'etat, le §13 serait enfreint dans un sens ou dans l'autre.
        controles += 1
        code_etat, sortie_etat = psql(
            compose,
            env,
            "SELECT state || '|' || (published_at IS NOT NULL)::text "  # noqa: S608
            f"FROM content_page WHERE id = '{page_creee}'",
        )
        etat_final = valeur(sortie_etat)
        if code_etat == 0 and etat_final == "published|true":
            print("    ok       apres DEUX ecritures, `state` et `published_at` sont INCHANGES —")
            print("             « Modifier » n'est pas « Publier », et ce n'est pas une promesse")
        else:
            echecs += 1
            print(f"    ECHEC    etat apres ecriture : {etat_final!r} (code {code_etat})")

        # --- 45. UN TYPE DE BLOC INCONNU REND 422, ET LA REPONSE ENUMERE LES TYPES
        controles += 1
        bloc_refuse = appeler(
            arguments.base,
            chemin_contenu,
            contexte,
            charge={
                "version": 3,
                "titre": "Page de T6",
                "blocs": [{"type_de_bloc": "IFRAME", "contenu": {}}],
            },
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_refus = bloc_refuse.json()
        erreur_refus = corps_refus.get("erreur", {}) if isinstance(corps_refus, dict) else {}
        types_annonces = (erreur_refus.get("details") or {}).get("types_autorises")
        if (
            bloc_refuse.statut == 422
            and erreur_refus.get("code") == "type_de_bloc_refuse"
            and types_annonces == list(TYPES_DE_BLOC)
        ):
            print(f"    ok       type de bloc inconnu : 422, et les {len(TYPES_DE_BLOC)} types")
            print("             autorises sont ENUMERES — un auteur doit savoir ce qu'il pose")
        else:
            echecs += 1
            print(f"    ECHEC    type de bloc : {bloc_refuse.statut}, {str(corps_refus)[:180]}")

        # --- 46. UNE VERSION OBSOLETE REND 409, ET RIEN N'EST ECRIT
        controles += 1
        obsolete = appeler(
            arguments.base,
            chemin_contenu,
            contexte,
            charge={
                "version": 1,
                "titre": "Ecrase",
                "blocs": [{"type_de_bloc": "TITLE", "contenu": {"texte": "ecrase"}}],
            },
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_obsolete = obsolete.json()
        code_obsolete = (
            corps_obsolete.get("erreur", {}).get("code")
            if isinstance(corps_obsolete, dict)
            else None
        )
        _, sortie_titre = psql(
            compose,
            env,
            f"SELECT title FROM content_page WHERE id = '{page_creee}'",  # noqa: S608
        )
        if obsolete.statut == 409 and code_obsolete == "version_obsolete":
            if valeur(sortie_titre) == "Page de T6":
                print("    ok       version obsolete : 409 `version_obsolete`, et le titre en")
                print("             base est INCHANGE — §18.4, « sans ecrasement silencieux »")
            else:
                echecs += 1
                print(f"    ECHEC    409 rendu mais le titre a change : {valeur(sortie_titre)!r}")
        else:
            echecs += 1
            print(f"    ECHEC    version obsolete : {obsolete.statut}, {str(corps_obsolete)[:160]}")

        # --- 47. TEMOIN : LA PERSONNE SANS RESPONSABILITE OUVRE BIEN UNE SESSION
        #
        #  Sans ce temoin, le 403 du controle suivant pourrait venir d'un echec
        #  d'authentification, et il paraitrait prouver une regle de role.
        controles += 1
        connexion_sd = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse_sans_droit, "mot_de_passe": mot_de_passe},
        )
        cookie_sd = ""
        for pose in connexion_sd.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                cookie_sd = pose.split(";")[0]
        session_sd = appeler(
            arguments.base, CHEMIN_SESSION, contexte, en_tetes={"Cookie": cookie_sd}
        )
        corps_sd = session_sd.json()
        csrf_sd = corps_sd.get("jeton_csrf", "") if isinstance(corps_sd, dict) else ""
        if connexion_sd.statut == 200 and cookie_sd and csrf_sd:
            print("    ok       TEMOIN : la personne SANS responsabilite se connecte et obtient")
            print("             son jeton — le refus qui suit ne viendra donc pas de la session")
        else:
            echecs += 1
            print(f"    ECHEC    connexion sans droit : {connexion_sd.statut}")
            raise RuntimeError("sans ce temoin, le refus de role ne prouverait rien")

        # --- 48. SANS AUCUNE RESPONSABILITE : 403 SUR LA CREATION ET SUR L'ECRITURE
        #
        #  Elle n'a que `EMP`, et les tableaux §10.x et §13 n'ont pas cette
        #  colonne : une absence de colonne n'est pas une exclusion, mais le §5
        #  ne lui donne que « Lecture ». C'est l'API qui refuse, pas l'ecran.
        controles += 1
        entetes_sd = {"Cookie": cookie_sd, EN_TETE_JETON: csrf_sd, "Origin": arguments.base}
        creation_sd = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={"type_de_page": "HOME", "titre": "x", "slug": f"{MARQUEUR}-sd"},
            en_tetes=entetes_sd,
        )
        ecriture_sd = appeler(
            arguments.base,
            chemin_contenu,
            contexte,
            charge={"version": 3, "titre": "x", "blocs": []},
            en_tetes=entetes_sd,
            methode="PUT",
        )
        corps_creation_sd = creation_sd.json()
        code_creation_sd = (
            corps_creation_sd.get("erreur", {}).get("code")
            if isinstance(corps_creation_sd, dict)
            else None
        )
        if (
            creation_sd.statut == 403
            and ecriture_sd.statut == 403
            and code_creation_sd == "acces_refuse"
        ):
            print("    ok       sans responsabilite : 403 `acces_refuse` sur la creation ET sur")
            print("             l'ecriture — l'API est l'autorite finale (§2.6)")
        else:
            echecs += 1
            print(
                f"    ECHEC    sans droit : creation={creation_sd.statut}, "
                f"ecriture={ecriture_sd.statut}, code={code_creation_sd!r}"
            )

        # --- 49. UNE PAGE D'UNE AUTRE ENTITE : 403, ET LE TEMOIN EST LA MEME PAGE
        #
        #  L'ESM du decor ecrit sa page (controle 40). La MEME page, adressee par
        #  le chemin d'une AUTRE entite, est refusee : le §5.1 dit que « les
        #  controles cote API utilisent l'entite de la RESSOURCE ».
        controles += 1
        ailleurs = appeler(
            arguments.base,
            CHEMIN_CONTENU.format(code=code_brouillon, page=page_creee),
            contexte,
            charge={"version": 3, "titre": "x", "blocs": []},
            en_tetes=ecriture,
            methode="PUT",
        )
        #  `code_brouillon` designe une entite NON ACTIVE : le 404 est celui de
        #  toutes les routes d'entite, et il precede la question du perimetre.
        if ailleurs.statut == 404:
            print("    ok       la MEME page par le chemin d'une entite non active : 404 —")
            print("             l'entite du chemin est resolue AVANT tout perimetre")
        else:
            echecs += 1
            print(f"    ECHEC    autre entite : {ailleurs.statut}")

        # ================================================================
        #  `T7` — brouillon, publication, archivage, restauration
        # ================================================================

        # --- 50. `T7` PART D'UNE PAGE NEUVE, ET C'EST UN DEFAUT QUI L'A APPRIS
        #
        #  **`T7-2` : LA PAGE DE `T6` EST DEJA PUBLIEE.** Le controle 44 la publie
        #  PAR SQL pour prouver que l'ecriture n'y touche pas -- la route de
        #  publication n'existait pas alors. Mes premiers controles la croyaient
        #  en brouillon, et ils ont echoue en disant « brouillon servi : 200 ».
        #
        #  Le remede n'est pas de defaire cet etat : c'est de partir d'une page
        #  que `T7` cree lui-meme. Un controle qui herite d'un etat qu'il n'a pas
        #  pose mesure le decor d'un autre (§9.0 — verifier avant de batir dessus).
        controles += 1
        slug_t7 = f"{MARQUEUR}-t7"
        creation_t7 = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={"type_de_page": "HOME", "titre": "Page de T7", "slug": slug_t7},
            en_tetes=ecriture,
        )
        corps_t7 = creation_t7.json()
        page_t7 = corps_t7.get("identifiant") if isinstance(corps_t7, dict) else None
        etat_t7 = corps_t7.get("etat") if isinstance(corps_t7, dict) else None
        if creation_t7.statut == 201 and page_t7 and etat_t7 == "draft":
            version = 1
            print("    ok       `T7` part d'une page NEUVE, en `draft` — jamais d'un etat pose")
            print("             par une autre sous-etape")
        else:
            echecs += 1
            print(f"    ECHEC    creation pour `T7` : {creation_t7.statut}, {str(corps_t7)[:160]}")
            raise RuntimeError("sans page neuve, le cycle ne prouverait rien")

        #  Le contenu, avec la charge d'injection : elle doit traverser la
        #  publication intacte, ce que le controle 53 mesure dans les OCTETS.
        ecrit_t7 = appeler(
            arguments.base,
            CHEMIN_CONTENU.format(code=code_actif, page=page_t7),
            contexte,
            charge={
                "version": 1,
                "titre": "Page de T7",
                "blocs": [{"type_de_bloc": "RICH_TEXT", "contenu": {"texte": INJECTION}}],
            },
            en_tetes=ecriture,
            methode="PUT",
        )
        if ecrit_t7.statut != 200:
            echecs += 1
            print(f"    ECHEC    contenu de la page de `T7` : {ecrit_t7.statut}")
        else:
            version = 2

        chemin_public = CHEMIN_PAGE.format(code=code_actif, type_de_page="HOME", slug=slug_t7)
        chemin_publication = CHEMIN_PUBLICATION.format(code=code_actif, page=page_t7)
        chemin_archivage = CHEMIN_ARCHIVAGE.format(code=code_actif, page=page_t7)
        chemin_restauration = CHEMIN_RESTAURATION.format(code=code_actif, page=page_t7)

        # --- 51. TEMOIN AVANT : LE BROUILLON N'EST PAS SERVI
        #
        #  Sans lui, le « elle est servie » du controle suivant ne prouverait pas
        #  que c'est la PUBLICATION qui l'a rendue visible.
        controles += 1
        avant = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        if avant.statut == 404:
            print("    ok       TEMOIN AVANT : le brouillon rend 404 — indistinguable d'un slug")
            print("             inconnu, ce que `US006` exige de « previsualiser PUIS publier »")
        else:
            echecs += 1
            print(f"    ECHEC    brouillon servi : {avant.statut} sur {chemin_public}")

        # --- 52. PUBLIER REND LA PAGE SERVIE — LE TEMOIN DE TOUTE LA SOUS-ETAPE
        #
        #  « Brouillon et publication sont distingues » est satisfait par une API
        #  qui ne publie RIEN (§7.39). Ce qui le prouve est que la MEME adresse,
        #  qui rendait 404 a la ligne precedente, serve desormais la page — et
        #  c'est la route de `T5`, ecrite avant et sans rapport, qui le dit.
        controles += 1
        publication = appeler(
            arguments.base,
            chemin_publication,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        corps_publication = publication.json()
        etat_publie = corps_publication.get("etat") if isinstance(corps_publication, dict) else None
        date_publication = (
            corps_publication.get("publiee_le") if isinstance(corps_publication, dict) else None
        )
        servie = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        if (
            publication.statut == 200
            and etat_publie == "published"
            and date_publication
            and servie.statut == 200
        ):
            version += 1
            print("    ok       publication : 200, etat `published`, date posee — ET LA MEME")
            print("             ADRESSE QUI RENDAIT 404 SERT MAINTENANT LA PAGE")
        else:
            echecs += 1
            print(
                f"    ECHEC    publication : {publication.statut}, "
                f"lecture publique : {servie.statut}, {str(corps_publication)[:140]}"
            )
            raise RuntimeError("sans publication, le reste du cycle ne prouverait rien")

        # --- 53. LA CHARGE D'INJECTION DE `T6` TRAVERSE LA PUBLICATION INTACTE
        #
        #  Elle a ete ECRITE par le controle 40 et SERVIE par le controle 43,
        #  mais jamais a travers une page PUBLIEE par l'API. C'est le verbe
        #  « accepte » de `T6` relu apres le geste de `T7`.
        controles += 1
        if INJECTION.encode("utf-8") in servie.corps:
            print("    ok       le balisage ecrit par `T6` est resservi OCTET POUR OCTET apres")
            print("             publication — conserve tel quel, jamais interprete (`DEC-584`)")
        else:
            echecs += 1
            print("    ECHEC    la charge n'est pas dans les octets servis apres publication")

        # --- 54. REPUBLIER EST REFUSE, ET LA DATE NE BOUGE PAS
        #
        #  Ecraser `published_at` detruirait la donnee meme que `US006` demande
        #  d'identifier. Le refus vient de l'ETAT, pas du role : le meme acteur,
        #  la meme page, et la seule chose qui a change est qu'elle est publiee.
        controles += 1
        republication = appeler(
            arguments.base,
            chemin_publication,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        code_date, sortie_date = psql(
            compose,
            env,
            f"SELECT published_at FROM content_page WHERE id = '{page_t7}'",  # noqa: S608
        )
        corps_republication = republication.json()
        code_republication = (
            corps_republication.get("erreur", {}).get("code")
            if isinstance(corps_republication, dict)
            else None
        )
        if (
            republication.statut == 403
            and code_republication == "contenu_hors_perimetre"
            and code_date == 0
            and valeur(sortie_date)
        ):
            print("    ok       republier : 403 `contenu_hors_perimetre`, et la date de")
            print("             publication est TOUJOURS en base — rien n'a ete ecrase")
        else:
            echecs += 1
            print(f"    ECHEC    republication : {republication.statut}, {code_republication!r}")

        # --- 55. ARCHIVER ECRIT LES DEUX COLONNES ET RETIRE LA PAGE DU PUBLIC
        controles += 1
        archivage = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        corps_archivage = archivage.json()
        apres_archivage = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        code_colonnes, sortie_colonnes = psql(
            compose,
            env,
            "SELECT state || '|' || (archived_at IS NOT NULL)::text || '|' || "  # noqa: S608
            f"(published_at IS NOT NULL)::text FROM content_page WHERE id = '{page_t7}'",
        )
        if (
            archivage.statut == 200
            and apres_archivage.statut == 404
            and code_colonnes == 0
            and valeur(sortie_colonnes) == "archived|true|true"
        ):
            version += 1
            print("    ok       archivage : `state` ET `archived_at` ecrits dans le MEME UPDATE,")
            print("             `published_at` CONSERVE, et la page quitte la lecture publique")
        else:
            echecs += 1
            print(
                f"    ECHEC    archivage : {archivage.statut}, public : "
                f"{apres_archivage.statut}, base : {valeur(sortie_colonnes)!r}, "
                f"{str(corps_archivage)[:120]}"
            )

        # --- 56. RESTAURER NE REPUBLIE PAS — LE CONTROLE LE PLUS UTILE DE `T7`
        #
        #  Apres restauration la page est VIVANTE, donc modifiable et publiable,
        #  et pourtant TOUJOURS PAS SERVIE. C'est `RIGHTS-001` : une page
        #  redevenue visible sans que personne ne l'ait publiee serait une
        #  publication que personne n'a decidee. Puis le second geste la ressert,
        #  sans quoi le refus mesure ici pourrait venir de n'importe quel defaut.
        controles += 1
        restauration = appeler(
            arguments.base,
            chemin_restauration,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        corps_restauration = restauration.json()
        etat_restaure = (
            corps_restauration.get("etat") if isinstance(corps_restauration, dict) else None
        )
        apres_restauration = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        if (
            restauration.statut == 200
            and etat_restaure == "draft"
            and apres_restauration.statut == 404
        ):
            version += 1
            print("    ok       restauration : 200, etat `draft`, ET LA PAGE N'EST TOUJOURS PAS")
            print("             SERVIE — restaurer n'est pas publier (§13, deux lignes)")
        else:
            echecs += 1
            print(
                f"    ECHEC    restauration : {restauration.statut}, etat={etat_restaure!r}, "
                f"public={apres_restauration.statut}"
            )

        # --- 57. LE TEMOIN DU CYCLE : LE SECOND GESTE LA RESSERT
        controles += 1
        republiee = appeler(
            arguments.base,
            chemin_publication,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        servie_a_nouveau = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        if republiee.statut == 200 and servie_a_nouveau.statut == 200:
            version += 1
            print("    ok       TEMOIN : republiee explicitement, la page est servie a nouveau —")
            print("             le cycle complet brouillon > publie > archive > brouillon > publie")
        else:
            echecs += 1
            print(
                f"    ECHEC    republication apres restauration : {republiee.statut}, "
                f"public : {servie_a_nouveau.statut}"
            )

        # --- 58. UNE VERSION OBSOLETE REFUSE L'ARCHIVAGE, ET N'ECRIT RIEN
        controles += 1
        archivage_obsolete = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": 1},
            en_tetes=ecriture,
        )
        code_etat_t7, sortie_etat_t7 = psql(
            compose,
            env,
            f"SELECT state FROM content_page WHERE id = '{page_t7}'",  # noqa: S608
        )
        corps_obsolete_t7 = archivage_obsolete.json()
        code_obsolete_t7 = (
            corps_obsolete_t7.get("erreur", {}).get("code")
            if isinstance(corps_obsolete_t7, dict)
            else None
        )
        if (
            archivage_obsolete.statut == 409
            and code_obsolete_t7 == "version_obsolete"
            and code_etat_t7 == 0
            and valeur(sortie_etat_t7) == "published"
        ):
            print("    ok       version obsolete a l'archivage : 409, et l'etat en base est")
            print("             INCHANGE — §18.4, « sans ecrasement silencieux »")
        else:
            echecs += 1
            print(
                f"    ECHEC    archivage obsolete : {archivage_obsolete.statut}, "
                f"{code_obsolete_t7!r}, etat={valeur(sortie_etat_t7)!r}"
            )

        # --- 59. LES TROIS ROUTES EXIGENT LE JETON CSRF, ET LES TROIS SONT VERIFIEES
        #
        #  **LES TROIS, ET PAS UNE.** Une garde posee sur deux routes sur trois
        #  est exactement le defaut qu'un controle portant sur une seule route
        #  laisserait passer -- §7.40, « un garde-fou ecrit contre UNE instance
        #  ne couvre pas la classe ».
        controles += 1
        sans_jeton = {**entetes, "Origin": arguments.base}
        refus_csrf = [
            appeler(
                arguments.base, chemin, contexte, charge={"version": version}, en_tetes=sans_jeton
            ).statut
            for chemin in (chemin_publication, chemin_archivage, chemin_restauration)
        ]
        if refus_csrf == [403, 403, 403]:
            print("    ok       sans jeton CSRF : 403 sur LES TROIS routes du cycle — la")
            print("             session et le role suffisent pourtant, SEUL le jeton manque")
        else:
            echecs += 1
            print(f"    ECHEC    CSRF sur les trois routes : {refus_csrf}")

        # --- 60. SANS RESPONSABILITE : 403 SUR LES TROIS ROUTES
        controles += 1
        refus_sd = [
            appeler(
                arguments.base, chemin, contexte, charge={"version": version}, en_tetes=entetes_sd
            ).statut
            for chemin in (chemin_publication, chemin_archivage, chemin_restauration)
        ]
        if refus_sd == [403, 403, 403]:
            print("    ok       sans responsabilite : 403 sur les trois — l'API est l'autorite")
            print("             finale (§2.6), et le temoin du controle 47 exclut la session")
        else:
            echecs += 1
            print(f"    ECHEC    sans droit sur les trois routes : {refus_sd}")

        # --- 61. LA BORNE DU §8.4 MORD A LA PUBLICATION — ET ELLE A SON TEMOIN
        #
        #  `DEC-583` a renvoye ici le declencheur du comptage borne, et c'est le
        #  SEUL geste du projet qui le fasse mordre. Un declencheur qui refuserait
        #  TOUTE publication passerait le refus ; seul le temoin positif, sur la
        #  MEME page et apres la seule addition d'un responsable, le distingue.
        controles += 1
        bureau_t7 = f"{MARQUEUR}-T7B"
        code_bureau_t7, sortie_bureau_t7 = psql(
            compose,
            env,
            "INSERT INTO office (entity_id, code, name, display_order) "  # noqa: S608
            f"SELECT id, '{bureau_t7}', 'Bureau T7', 9 FROM entity WHERE code = '{code_actif}'",
        )
        creation_bureau = appeler(
            arguments.base,
            CHEMIN_CREATION.format(code=code_actif),
            contexte,
            charge={
                "type_de_page": "OFFICE",
                "titre": "Bureau de T7",
                "slug": f"{MARQUEUR}-t7b",
                "bureau": bureau_t7,
            },
            en_tetes=ecriture,
        )
        corps_bureau = creation_bureau.json()
        page_bureau = corps_bureau.get("identifiant") if isinstance(corps_bureau, dict) else None
        if code_bureau_t7 or creation_bureau.statut != 201 or not page_bureau:
            echecs += 1
            print(
                f"    ECHEC    decor de la borne : office={sortie_bureau_t7[:80]}, "
                f"page={creation_bureau.statut}"
            )
        else:
            chemin_publication_bureau = CHEMIN_PUBLICATION.format(code=code_actif, page=page_bureau)
            sans_responsable = appeler(
                arguments.base,
                chemin_publication_bureau,
                contexte,
                charge={"version": 1},
                en_tetes=ecriture,
            )
            corps_borne = sans_responsable.json()
            code_borne = (
                corps_borne.get("erreur", {}).get("code") if isinstance(corps_borne, dict) else None
            )
            #  Un responsable ACTIF, et rien d'autre ne change.
            code_resp, sortie_resp = psql(
                compose,
                env,
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "  # noqa: S608
                "responsibility_type, office_id, assigned_by_person_id, starts_at) "
                "SELECT p.id, o.entity_id, 'OFFICE_MANAGER', o.id, p.id, now() - interval '1 day' "
                f"FROM office o, person p WHERE o.code = '{bureau_t7}' "
                f"AND p.email_normalized = '{adresse}' ",
            )
            avec_responsable = appeler(
                arguments.base,
                chemin_publication_bureau,
                contexte,
                charge={"version": 1},
                en_tetes=ecriture,
            )
            if (
                sans_responsable.statut == 409
                and code_borne == "borne_des_responsables"
                and code_resp == 0
                and avec_responsable.statut == 200
            ):
                print("    ok       borne du §8.4 : ZERO responsable -> 409")
                print("             `borne_des_responsables` ; UN responsable actif ajoute, et LA")
                print("             MEME publication passe — `DEC-583`, le declencheur `0018`")
            else:
                echecs += 1
                print(
                    f"    ECHEC    borne : sans={sans_responsable.statut}/{code_borne!r}, "
                    f"avec={avec_responsable.statut}, insert={sortie_resp[:80]}"
                )

        # ====================================================================
        #
        #  `T8` — LA PRESENTATION DE L'ENTITE ET LES LIENS INTERNES
        #         story `MVP-L06-US005`, `DEC-587`, `QO-120` close
        #
        # ====================================================================

        # --- 62. LE TEMOIN : LES TROIS DESTINATIONS DU CRITERE, CREEES PUIS SERVIES
        #
        #  « Presentation, Hub, Academy et SharePoint sont modifiables
        #  localement ; les URL sont validees » est PARFAITEMENT tenu par une API
        #  qui refuse tout (§7.39). Ce qui le prouve est que les trois
        #  destinations NOMMEES par le critere soient creees par l'API, puis
        #  rendues par la route de l'accueil — a travers Caddy, en HTTPS.
        controles += 1
        crees: list[str] = []
        statuts_creation: list[int] = []
        for libelle, type_de_lien, url in (
            ("Hub", "HUB", "https://hub.exemple.test/"),
            ("eXalt Academy", "ACADEMY", "https://academy.exemple.test/"),
            ("SharePoint", "SHAREPOINT", "https://sharepoint.exemple.test/bordeaux"),
        ):
            creation_lien = appeler(
                arguments.base,
                CHEMIN_LIENS.format(code=code_actif),
                contexte,
                charge={"libelle": libelle, "url": url, "type_de_lien": type_de_lien},
                en_tetes=ecriture,
            )
            statuts_creation.append(creation_lien.statut)
            corps_lien = creation_lien.json()
            if isinstance(corps_lien, dict) and corps_lien.get("identifiant"):
                crees.append(str(corps_lien["identifiant"]))
        accueil = appeler(
            arguments.base, CHEMIN_LIENS.format(code=code_actif), contexte, en_tetes=entetes
        )
        corps_accueil = accueil.json()
        liens_servis = corps_accueil.get("liens", []) if isinstance(corps_accueil, dict) else []
        libelles = [lien.get("libelle") for lien in liens_servis if isinstance(lien, dict)]
        rangs = [lien.get("rang") for lien in liens_servis if isinstance(lien, dict)]
        if (
            statuts_creation == [201, 201, 201]
            and accueil.statut == 200
            and libelles == ["Hub", "eXalt Academy", "SharePoint"]
            and rangs == [0, 1, 2]
        ):
            print("    ok       LE TEMOIN : Hub, eXalt Academy et SharePoint crees par l'API")
            print("             puis SERVIS par l'accueil, rangs 0-1-2 — ajoutes EN QUEUE, et")
            print("             AUCUN champ de rang n'est offert a l'appelant")
        else:
            echecs += 1
            print(
                f"    ECHEC    temoin des liens : creations={statuts_creation}, "
                f"accueil={accueil.statut}, libelles={libelles}, rangs={rangs}"
            )

        # --- 63. LES CINQ REFUS D'URL, CHACUN SOUS SON CODE — `QO-120`, `DEC-587`
        #
        #  **CINQ REFUS INDISTINGUABLES SERAIENT SATISFAITS PAR UNE ROUTE QUI
        #  REFUSE TOUT**, et c'est le defaut `T2-3` du LOT 5, ou HUIT epreuves de
        #  refus passaient sur une route qui refusait aussi les valeurs valides.
        #  Chaque refus porte donc SON code, et le controle 62 est leur temoin.
        controles += 1
        refus_url: list[tuple[int, object]] = []
        for url_fautive in (
            "hub.exemple.test",
            "java\nscript:alert(1)",
            "http://hub.exemple.test/",
            "javascript:alert(1)",
            "https:alert(1)",
        ):
            refus = appeler(
                arguments.base,
                CHEMIN_LIENS.format(code=code_actif),
                contexte,
                charge={"libelle": "fautif", "url": url_fautive, "type_de_lien": "OTHER"},
                en_tetes=ecriture,
            )
            corps_refus = refus.json()
            refus_url.append(
                (
                    refus.statut,
                    corps_refus.get("erreur", {}).get("code")
                    if isinstance(corps_refus, dict)
                    else None,
                )
            )
        attendu_url = [
            (422, "url_illisible"),
            (422, "url_ambigue"),
            (422, "url_non_chiffree"),
            (422, "url_protocole_refuse"),
            (422, "url_sans_hote"),
        ]
        code_compte_liens, sortie_compte_liens = psql(
            compose,
            env,
            "SELECT count(*) FROM internal_link WHERE entity_id IN "  # noqa: S608
            f"(SELECT id FROM entity WHERE code = '{code_actif}')",
        )
        if (
            refus_url == attendu_url
            and code_compte_liens == 0
            and valeur(sortie_compte_liens) == str(len(crees))
        ):
            print("    ok       les CINQ refus d'URL portent CINQ codes distincts, et AUCUN")
            print("             n'a ecrit — `url_illisible`, `url_ambigue`, `url_non_chiffree`,")
            print("             `url_protocole_refuse`, `url_sans_hote`. `QO-120`, `DEC-587`")
            print("             LE DERNIER EST CELUI QUE LA MESURE A TROUVE : `https:alert(1)`")
            print("             passe une liste blanche de PROTOCOLES et n'adresse rien")
        else:
            echecs += 1
            print(
                f"    ECHEC    refus d'URL : {refus_url}, attendu {attendu_url}, "
                f"liens en base={valeur(sortie_compte_liens)!r} pour {len(crees)} crees"
            )

        # --- 64. LA CONTRAINTE DE LA MIGRATION `0019` EST LE PLANCHER
        #
        #  Le service refuse plus tot et plus finement ; la contrainte couvre ce
        #  qu'il ne peut pas couvrir — une insertion SQL, une reprise du LOT 11,
        #  un import du LOT 9. Le couple est complet : le temoin `https://` passe
        #  par le MEME chemin SQL.
        controles += 1
        #  `S608` : l'interpolation ne porte que `code_actif`, une constante de ce
        #  script, et des litteraux ecrits ici. Le `noqa` va sur la DERNIERE
        #  PREMIERE ligne de la concatenation implicite — c'est la que ruff
        #  l'attribue, mesure du 22/09/2026 (et non la fermeture, comme pour
        #  une chaine triple-guillemets : les deux conventions different).
        insertion = (
            "INSERT INTO internal_link (entity_id, label, url, link_type, display_order, "  # noqa: S608
            "created_at, updated_at) SELECT id, 'brut', '{url}', 'OTHER', {rang}, now(), now() "
            f"FROM entity WHERE code = '{code_actif}'"
        )
        code_hostile, sortie_hostile = psql(
            compose, env, insertion.format(url="javascript:alert(1)", rang=90)
        )
        code_temoin_sql, sortie_temoin_sql = psql(
            compose, env, insertion.format(url="https://plancher.exemple.test/", rang=91)
        )
        if (
            code_hostile != 0
            and "ck_internal_link_url_https" in sortie_hostile
            and code_temoin_sql == 0
        ):
            print("    ok       la contrainte `ck_internal_link_url_https` refuse un")
            print("             `javascript:` insere EN SQL, et laisse passer un `https://` —")
            print("             « aucune URL hostile en base » est STRUCTUREL (§7.35, `0019`)")
        else:
            echecs += 1
            print(
                f"    ECHEC    plancher SQL : hostile={code_hostile}/{sortie_hostile[:120]}, "
                f"temoin={code_temoin_sql}/{sortie_temoin_sql[:80]}"
            )

        # --- 65. DESACTIVER RETIRE DE L'ACCUEIL, ET LA GESTION LE VOIT ENCORE
        #
        #  **LE COUPLE COMPLET**, sans quoi le champ `active` du §15.3 serait un
        #  aller sans retour. Les deux lectures sont interrogees au MEME instant,
        #  et seule l'audience change.
        controles += 1
        if len(crees) == 3:
            desactivation = appeler(
                arguments.base,
                CHEMIN_UN_LIEN.format(code=code_actif, lien=crees[1]),
                contexte,
                charge={
                    "version": 1,
                    "libelle": "eXalt Academy",
                    "url": "https://academy.exemple.test/",
                    "type_de_lien": "ACADEMY",
                    "actif": False,
                },
                en_tetes=ecriture,
                methode="PUT",
            )
            apres_accueil = appeler(
                arguments.base, CHEMIN_LIENS.format(code=code_actif), contexte, en_tetes=entetes
            )
            apres_gestion = appeler(
                arguments.base,
                CHEMIN_LIENS_GESTION.format(code=code_actif),
                contexte,
                en_tetes=entetes,
            )
            corps_a = apres_accueil.json()
            corps_g = apres_gestion.json()
            n_accueil = corps_a.get("nombre_de_liens") if isinstance(corps_a, dict) else None
            n_gestion = corps_g.get("nombre_de_liens") if isinstance(corps_g, dict) else None
            #  **LE PLANCHER SQL A POSE UN LIEN DE PLUS**, actif : la gestion en
            #  compte donc quatre et l'accueil trois. Les nombres sont DERIVES de
            #  ce qui a ete pose, jamais ecrits en dur (§7.27).
            attendus_gestion = len(crees) + (1 if code_temoin_sql == 0 else 0)
            if (
                desactivation.statut == 200
                and n_accueil == attendus_gestion - 1
                and n_gestion == attendus_gestion
            ):
                print("    ok       un lien DESACTIVE quitte l'accueil et reste en gestion —")
                print(f"             accueil {n_accueil}, gestion {n_gestion}. Le §15.3 declare")
                print("             `active` A COTE de `archived_at`, et `T1` a refuse de les")
                print("             fondre : on desactive pour cacher, on archive pour sortir")
            else:
                echecs += 1
                print(
                    f"    ECHEC    desactivation : {desactivation.statut}, accueil={n_accueil}, "
                    f"gestion={n_gestion}, attendus={attendus_gestion}"
                )
        else:
            echecs += 1
            print(f"    ECHEC    decor des liens incomplet : {len(crees)} cree(s) sur 3")

        # --- 66. REORDONNER ECHANGE DEUX LIENS — CE QU'UN SEUL `UPDATE` NE PEUT PAS
        #
        #  Mesure du 22/09/2026 : un echange de rangs en un seul ordre est REFUSE
        #  par `uq_internal_link_entity_ordre_non_archive`. La reecriture se fait
        #  donc en deux temps, avec un decalage DERIVE du maximum — et non du
        #  NOMBRE de liens, qui est le defaut `T8-1`.
        controles += 1
        gestion_avant = appeler(
            arguments.base,
            CHEMIN_LIENS_GESTION.format(code=code_actif),
            contexte,
            en_tetes=entetes,
        )
        corps_avant = gestion_avant.json()
        avant_ids = [
            str(servi["identifiant"])
            for servi in (corps_avant.get("liens", []) if isinstance(corps_avant, dict) else [])
            if isinstance(servi, dict)
        ]
        inverse = list(reversed(avant_ids))
        reordonnancement = appeler(
            arguments.base,
            CHEMIN_ORDRE_DES_LIENS.format(code=code_actif),
            contexte,
            charge={"ordre": inverse},
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_ordre = reordonnancement.json()
        obtenus = [
            str(servi["identifiant"])
            for servi in (corps_ordre.get("liens", []) if isinstance(corps_ordre, dict) else [])
            if isinstance(servi, dict)
        ]
        #  Une liste INCOMPLETE est refusee : c'est ce qui tient lieu de
        #  concurrence optimiste ici, la collection n'ayant pas de porteur de
        #  version.
        partielle = appeler(
            arguments.base,
            CHEMIN_ORDRE_DES_LIENS.format(code=code_actif),
            contexte,
            charge={"ordre": inverse[:1]},
            en_tetes=ecriture,
            methode="PUT",
        )
        corps_partielle = partielle.json()
        code_partielle = (
            corps_partielle.get("erreur", {}).get("code")
            if isinstance(corps_partielle, dict)
            else None
        )
        if (
            len(avant_ids) >= 2
            and reordonnancement.statut == 200
            and obtenus == inverse
            and partielle.statut == 422
            and code_partielle == "ordre_incomplet"
        ):
            print(f"    ok       les {len(avant_ids)} liens sont INVERSES en un geste — ce qu'un")
            print("             seul `UPDATE` ne peut pas faire, l'index unique partiel de `T1`")
            print("             le refusant (mesure). Et une liste PARTIELLE rend 422")
            print("             `ordre_incomplet` : c'est la concurrence optimiste de `T8`")
        else:
            echecs += 1
            print(
                f"    ECHEC    ordre : {reordonnancement.statut}, obtenus={obtenus}, "
                f"attendu={inverse}, partielle={partielle.statut}/{code_partielle!r}"
            )

        # --- 67. LES TROIS ECRITURES EXIGENT LE JETON CSRF, ET LA LECTURE NON
        #
        #  **LES TROIS, ET PAS UNE** — §7.40, « un garde-fou ecrit contre UNE
        #  instance ne couvre pas la classe ». Le temoin est la LECTURE : elle
        #  passe sans jeton, ce qui prouve que le 403 vient bien du jeton et non
        #  d'un refus general.
        controles += 1
        sans_jeton_liens = {**entetes, "Origin": arguments.base}
        refus_csrf_liens = [
            appeler(
                arguments.base,
                CHEMIN_LIENS.format(code=code_actif),
                contexte,
                charge={"libelle": "x", "url": "https://x.exemple.test/", "type_de_lien": "OTHER"},
                en_tetes=sans_jeton_liens,
            ).statut,
            appeler(
                arguments.base,
                CHEMIN_ORDRE_DES_LIENS.format(code=code_actif),
                contexte,
                charge={"ordre": avant_ids},
                en_tetes=sans_jeton_liens,
                methode="PUT",
            ).statut,
            appeler(
                arguments.base,
                CHEMIN_UN_LIEN.format(code=code_actif, lien=avant_ids[0] if avant_ids else "x"),
                contexte,
                charge={
                    "version": 1,
                    "libelle": "x",
                    "url": "https://x.exemple.test/",
                    "type_de_lien": "OTHER",
                },
                en_tetes=sans_jeton_liens,
                methode="PUT",
            ).statut,
        ]
        lecture_sans_jeton = appeler(
            arguments.base,
            CHEMIN_LIENS.format(code=code_actif),
            contexte,
            en_tetes=sans_jeton_liens,
        ).statut
        if refus_csrf_liens == [403, 403, 403] and lecture_sans_jeton == 200:
            print("    ok       sans jeton CSRF : 403 sur LES TROIS ecritures de liens, et la")
            print("             LECTURE passe — le refus vient du jeton, pas d'un blocage large")
        else:
            echecs += 1
            print(f"    ECHEC    CSRF des liens : {refus_csrf_liens}, lecture={lecture_sans_jeton}")

        # --- 68. SANS ROLE DE GESTION : LES ECRITURES SONT REFUSEES, LA LECTURE NON
        #
        #  **LA MATRICE §5 ACCORDE LA LECTURE AUX HUIT ROLES AUTHENTIFIES** — sa
        #  ligne « Liens Hub/Academy/SharePoint » — et le §13 comme le §19
        #  reservent l'ecriture a `ESM`, `ADM-E` et `SUPER`. Le couple prouve les
        #  DEUX moities : refuser la lecture aussi serait plus restrictif que le
        #  document, et c'est ce que le temoin distingue.
        controles += 1
        ecritures_sd = [
            appeler(
                arguments.base,
                CHEMIN_LIENS.format(code=code_actif),
                contexte,
                charge={"libelle": "x", "url": "https://x.exemple.test/", "type_de_lien": "OTHER"},
                en_tetes=entetes_sd,
            ).statut,
            appeler(
                arguments.base,
                CHEMIN_ORDRE_DES_LIENS.format(code=code_actif),
                contexte,
                charge={"ordre": avant_ids},
                en_tetes=entetes_sd,
                methode="PUT",
            ).statut,
            appeler(
                arguments.base,
                CHEMIN_LIENS_GESTION.format(code=code_actif),
                contexte,
                en_tetes=entetes_sd,
            ).statut,
        ]
        lecture_sd = appeler(
            arguments.base, CHEMIN_LIENS.format(code=code_actif), contexte, en_tetes=entetes_sd
        ).statut
        if ecritures_sd == [403, 403, 403] and lecture_sd == 200:
            print("    ok       sans role de gestion : 403 a la creation, a l'ordre ET a la")
            print("             liste de GESTION ; la lecture de l'accueil rend 200 — matrice")
            print("             §5 « Liens Hub/Academy/SharePoint », Lecture aux HUIT roles")
        else:
            echecs += 1
            print(f"    ECHEC    sans role : ecritures={ecritures_sd}, lecture={lecture_sd}")

        # ==================================================================
        #
        #  `T10` — LA LECTURE POUR L'EDITEUR
        #
        #    **UN TROU DEPUIS `T6`, PAS UN REPORT VOULU.** La lecture de `T5`
        #    (controle 41) ne sert que le PUBLIE, sans `version` : un editeur
        #    qui rechargeait son ecran en cours de redaction, ou revenait sur
        #    un brouillon jamais publie, n'avait alors AUCUNE route pour
        #    relire son propre travail. `page_t7` a deja traverse tout le
        #    cycle du §13 -- aucune page neuve n'est necessaire ici.
        #
        # ==================================================================

        # --- 69. SANS COOKIE, LES DEUX ROUTES RENDENT 401
        controles += 1
        sans_gestion = [
            appeler(arguments.base, CHEMIN_PAGES_GESTION.format(code=code_actif), contexte).statut,
            appeler(
                arguments.base,
                CHEMIN_PAGE_GESTION.format(code=code_actif, page=page_t7),
                contexte,
            ).statut,
        ]
        if sans_gestion == [401, 401]:
            print("    ok       sans cookie : 401 sur la liste ET sur le detail")
        else:
            echecs += 1
            print(f"    ECHEC    sans cookie : {sans_gestion}")

        # --- 70. LA LISTE REFLETE L'ETAT REEL — `page_t7` EST PUBLIEE, ET LE DIT
        controles += 1
        liste_gestion = appeler(
            arguments.base, CHEMIN_PAGES_GESTION.format(code=code_actif), contexte, en_tetes=entetes
        )
        corps_liste = liste_gestion.json()
        pages_listees = corps_liste.get("pages", []) if isinstance(corps_liste, dict) else []
        trouvee_t7 = next((p for p in pages_listees if p.get("identifiant") == page_t7), None)
        if (
            liste_gestion.statut == 200
            and trouvee_t7 is not None
            and trouvee_t7.get("etat") == "published"
            and trouvee_t7.get("version") == version
        ):
            print("    ok       la liste de gestion : 200, `page_t7` y figure `published`,")
            print(f"             version {version} — le meme couple que la base")
        else:
            echecs += 1
            print(f"    ECHEC    liste de gestion : {liste_gestion.statut}, trouvee={trouvee_t7!r}")

        # --- 71. LE DETAIL SERT LES OCTETS, INJECTION COMPRISE, AVEC LA VERSION
        controles += 1
        detail_gestion = appeler(
            arguments.base,
            CHEMIN_PAGE_GESTION.format(code=code_actif, page=page_t7),
            contexte,
            en_tetes=entetes,
        )
        octets_detail = detail_gestion.corps
        if (
            detail_gestion.statut == 200
            and INJECTION.encode("utf-8") in octets_detail
            and b'"version":%d' % version in octets_detail
        ):
            print(f"    ok       le detail : 200, `version` a {version} DANS LES OCTETS, et la")
            print("             charge d'injection de `T7` traverse intacte — memes octets que")
            print("             la lecture publique, plus ce qu'elle ne porte pas")
        else:
            echecs += 1
            print(f"    ECHEC    detail : {detail_gestion.statut}, {octets_detail[:200]!r}")

        # --- 72. LE COUPLE CENTRAL : ARCHIVEE, LA PAGE RESTE LISIBLE ICI —
        #         C'EST TOUTE LA RAISON D'ETRE DE CETTE SOUS-ETAPE
        #
        #  Sans ce controle, « sert tous les etats » serait une affirmation
        #  jamais mise a l'epreuve : le detail pourrait tout aussi bien ne
        #  servir que le publie, comme `T5`, et rien ici ne l'aurait vu.
        controles += 1
        archivage_t10 = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": version},
            en_tetes=ecriture,
        )
        if archivage_t10.statut == 200:
            version += 1
        apres_archivage_t10 = appeler(
            arguments.base,
            CHEMIN_PAGE_GESTION.format(code=code_actif, page=page_t7),
            contexte,
            en_tetes=entetes,
        )
        corps_apres = apres_archivage_t10.json()
        etat_apres = corps_apres.get("etat") if isinstance(corps_apres, dict) else None
        toujours_publique = appeler(arguments.base, chemin_public, contexte, en_tetes=entetes)
        if (
            archivage_t10.statut == 200
            and apres_archivage_t10.statut == 200
            and etat_apres == "archived"
            and toujours_publique.statut == 404
        ):
            print("    ok       ARCHIVEE, la page rend 404 en LECTURE PUBLIQUE et 200 `archived`")
            print("             ICI — un editeur retrouve une page archivee pour la restaurer,")
            print("             ce que la lecture de `T5` seule ne permettait pas")
        else:
            echecs += 1
            print(
                f"    ECHEC    archivage={archivage_t10.statut}, "
                f"detail={apres_archivage_t10.statut}/{etat_apres!r}, "
                f"public={toujours_publique.statut}"
            )

        # --- 73. SANS ROLE EDITORIAL : 403 SUR LES DEUX ROUTES
        controles += 1
        sans_role_gestion = [
            appeler(
                arguments.base,
                CHEMIN_PAGES_GESTION.format(code=code_actif),
                contexte,
                en_tetes=entetes_sd,
            ).statut,
            appeler(
                arguments.base,
                CHEMIN_PAGE_GESTION.format(code=code_actif, page=page_t7),
                contexte,
                en_tetes=entetes_sd,
            ).statut,
        ]
        if sans_role_gestion == [403, 403]:
            print("    ok       sans role editorial : 403 sur la liste ET sur le detail — la")
            print("             meme garde que l'ecriture, `garde_d_ecriture`")
        else:
            echecs += 1
            print(f"    ECHEC    sans role : {sans_role_gestion}")

        # --- 74. LA MEME PAGE PAR LE CHEMIN D'UNE AUTRE ENTITE : 404
        #
        #  Meme motif que le controle 49 : l'entite du CHEMIN est resolue
        #  avant tout perimetre, `code_brouillon` designant une entite non
        #  active.
        controles += 1
        ailleurs_t10 = appeler(
            arguments.base,
            CHEMIN_PAGE_GESTION.format(code=code_brouillon, page=page_t7),
            contexte,
            en_tetes=entetes,
        )
        if ailleurs_t10.statut == 404:
            print("    ok       la MEME page par le chemin d'une entite non active : 404 —")
            print("             meme motif que l'ecriture (controle 49)")
        else:
            echecs += 1
            print(f"    ECHEC    autre entite : {ailleurs_t10.statut}")

    finally:
        #  **LE MENAGE LIT SON CODE DE SORTIE, ET C'EST LE DEFAUT `T2-2`.**
        #
        #  Ma premiere version supprimait `user_session WHERE user_account_id IN
        #  (...)` -- une colonne qui **n'existe pas** sur cette table, qui est
        #  rattachee par `person_id`. Le `DELETE` a donc ERRE, et comme le code de
        #  retour n'etait pas lu, l'echec etait SILENCIEUX : trois personnes sont
        #  restees, et **neuf tests d'integration sans rapport ont echoue** --
        #  dont celui qui cherche une adresse REELLE dans le jeu de donnees, mon
        #  marqueur employant le domaine autorise.
        #
        #  C'est le §7.3 — un controle dont on ne lit pas le code de sortie ne
        #  prouve rien — et le §7.30, huitieme occurrence de la classe « un
        #  nettoyage incomplet fait echouer des tests sans rapport ».
        entites = f"SELECT id FROM entity WHERE code LIKE '{MARQUEUR}%'"  # noqa: S608
        personnes = f"SELECT id FROM person WHERE email LIKE '{MARQUEUR}%'"  # noqa: S608
        comptes = f"SELECT id FROM user_account WHERE person_id IN ({personnes})"  # noqa: S608
        #  L'ordre suit les dependances : ce qui REFERENCE avant ce qui est
        #  reference. `user_session` et `auth_event` pointent la PERSONNE
        #  directement, pas seulement son compte.
        residus = 0
        for gabarit in (
            f"framework_responsibility_assignment WHERE entity_id IN ({entites})",
            f"circle_membership WHERE entity_id IN ({entites})",
            f"entity_membership WHERE entity_id IN ({entites})",
            #  **`content_block` ET `content_page` AVANT `circle` ET `office`.**
            #  `content_page` porte `circle_id` ET `office_id` : supprimer le
            #  bureau d'abord rend « violates foreign key constraint ». L'ordre
            #  inverse a tenu tant qu'AUCUNE page ne pointait un bureau, et `T4`
            #  en a cree une -- defaut `T4-3`, classe §7.30, neuvieme occurrence.
            #  Et c'est le garde-fou pose apres `T2-2` qui l'a dit, en lisant les
            #  codes de sortie : sans lui l'echec aurait ete SILENCIEUX.
            f"content_block WHERE entity_id IN ({entites})",
            f"content_page WHERE entity_id IN ({entites})",
            #  `T8` : `internal_link` ne reference que l'entite, donc son rang
            #  dans cette liste est libre — mais l'OUBLIER laisserait des lignes
            #  qui feraient echouer des tests sans rapport (§7.30, dixieme
            #  occurrence de la classe). C'est la suppression de l'`entity` qui
            #  echouerait, en nommant `fk_internal_link_entity_id_entity`.
            f"internal_link WHERE entity_id IN ({entites})",
            f"circle WHERE entity_id IN ({entites})",
            f"office WHERE entity_id IN ({entites})",
            f"admin_password_credential WHERE user_account_id IN ({comptes})",
            f"user_session WHERE person_id IN ({personnes})",
            #  **`auth_event` AVANT `user_account`** : il reference les DEUX, la
            #  personne et son compte. L'ordre inverse rend
            #  « violates foreign key constraint fk_auth_event_user_account_id ».
            f"auth_event WHERE person_id IN ({personnes})",
            f"user_account WHERE person_id IN ({personnes})",
            f"person WHERE email LIKE '{MARQUEUR}%'",
            f"entity WHERE code LIKE '{MARQUEUR}%'",
        ):
            code_menage, sortie_menage = psql(compose, env, "DELETE FROM " + gabarit)  # noqa: S608
            if code_menage:
                residus += 1
                print(f"    ECHEC    nettoyage de `{gabarit.split()[0]}` : {sortie_menage[:160]}")
        if residus:
            echecs += residus
            print(
                f"    ECHEC    {residus} suppression(s) en echec — des lignes SUBSISTENT, et "
                "elles feront echouer des tests sans rapport (§7.30)"
            )
        else:
            #  **CE `ok` S'IMPRIMAIT MEME APRES UN ECHEC** — il annonçait « tout
            #  est retire » a la ligne suivant « des lignes SUBSISTENT ».
            #  Un avertissement faux apprend a ne plus le lire (§7.21).
            print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(
        f"  --> {controles} controles du Framework, des cercles, des bureaux et des "
        "contenus, 0 echec"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
