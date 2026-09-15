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
    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; c uuid; ce uuid; cs uuid; bu uuid; bp uuid;
            mp uuid; ms uuid; md uuid; ap uuid; a2 uuid; a3 uuid;
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
      VALUES (e, 'OFFICE', bp, 'Bureau publie', '{MARQUEUR}-pub', 'published');
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

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_d}', '{adresse_d}', 'Cle', 'Brouillon', 'active') RETURNING id INTO md;
      INSERT INTO entity_membership
        (entity_id, person_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (e, md, date '2026-01-01', 'active', 'consultant', 'draft') RETURNING id INTO a3;
      INSERT INTO circle_membership
        (entity_id, entity_membership_id, circle_id, membership_type, starts_at)
      VALUES (e, a3, ce, 'principal', now() - interval '1 day');
    END $$;
    """  # noqa: S608
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print(
        "    ok       decor : 1 entite active, 1 brouillon, 3 cercles, 3 bureaux "
        "dont UN publie a ZERO responsable et UN archive, 4 responsabilites dont "
        "UNE future, 3 membres dont UN en brouillon"
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
    print(f"  --> {controles} controles du Framework, des cercles et des bureaux, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
