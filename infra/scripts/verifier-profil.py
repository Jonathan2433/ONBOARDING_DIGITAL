#!/usr/bin/env python3
"""La fiche profil complete, servie A TRAVERS CADDY.

LOT 5, sous-etape `T4`, story `MVP-L05-US004`.

CE QUE CE CONTROLE PROUVE QUE LES TESTS NE PROUVENT PAS

  Les tests d'integration montent l'application EN PROCESSUS. Ici la session est
  ouverte par une **vraie connexion a travers Caddy en HTTPS**, et la fiche est
  lue par un **aller-retour HTTP reel** -- §7.28. Il EXIGE que le conteneur porte
  le code du depot : lance `make code-refresh && make code-check` d'abord.

SON CONTROLE LE PLUS UTILE RELIE LA FICHE A LA LISTE

  Le trombinoscope de `T2` exclut quatre etats. Si la fiche etait accessible pour
  un profil que la liste refuse, le filtre de la liste serait **decoratif** -- et
  aucun test de la liste seule ne le verrait.

  Le controle prend donc **l'identifiant que la LISTE rend**, verifie que sa fiche
  est servie, puis prend un profil exclu et verifie que sa fiche est refusee.

L'ABSENCE DE MASQUAGE EST EPROUVEE, PAS SUPPOSEE

  La matrice ne definit **aucune** visibilite par champ -- `ECART-051`. Le
  controle appelle avec un compte qui n'a **aucune appartenance dans l'entite,
  aucune responsabilite, aucun role technique**, et exige que les six champs
  sensibles du §10.2 soient **tous renseignes**. Si un lot ulterieur en masque un,
  ce controle le dira.

Sortie 0 si tous les controles passent, 1 sinon.
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
import urllib.parse
import urllib.request
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_TROMBINOSCOPE = "/api/v1/entities/{code}/people"
CHEMIN_PROFIL = "/api/v1/entities/{code}/people/{appartenance}"
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"

MARQUEUR = f"t4l5-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l5t4-egalite-des-refus"

#  Les SEIZE champs de la fiche : les treize du §10.2 moins la photo, plus les
#  deux identifiants et la categorie professionnelle. **Declares et confrontes a
#  la reponse servie** : un champ ajoute sans etre voulu fait echouer.
CHAMPS_FICHE = frozenset(
    {
        "id",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "professional_category",
        "arrival_date",
        "short_bio",
        "fun_fact",
        "metier",
        "statut",
        "client",
        "dsm",
        "cercle_principal",
        "cercles_secondaires",
        "responsabilites",
    }
)

#  Les champs SENSIBLES du §10.2 : ceux qu'un masquage viserait s'il existait.
CHAMPS_SENSIBLES = ("metier", "statut", "client", "dsm", "short_bio", "fun_fact")

#  Le seul en-tete qui ne peut pas etre egal, et il est NOMME en sortie : a
#  travers Caddy, une reponse porte un `date` qui change d'une requete a
#  l'autre. Lui faire dire le vrai plutot que de l'affaiblir -- §7.20.
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
    """La premiere ligne non vide. `psql` mele ses etiquettes au resultat."""
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


def poser_le_decor(
    marqueur: str,
    code_entite: str,
    adresse: str,
    empreinte: str,
    algo: str,
    parametres_hachage: str,
) -> str:
    """Une entite, un admin local, un profil COMPLET, un profil EXCLU.

    S608 : les seules valeurs interpolees sont `MARQUEUR`, un `uuid4` de ce
    module, et le code d'entite qui en derive. `psql` n'accepte pas de parametre
    lie dans un bloc `DO`.

    **LE PROFIL COMPLET PORTE LES SIX CHAMPS SENSIBLES**, sans quoi l'epreuve
    d'absence de masquage ne prouverait rien : un champ nul est indistinguable
    d'un champ masque.
    """
    return f"""
    DO $$
    DECLARE p uuid; e uuid; c uuid; m uuid; cl uuid; jc uuid; ci uuid; d uuid; dm uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_entite}', 'Entite {marqueur}', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'L5T4', 'active') RETURNING id INTO p;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{algo}', '{parametres_hachage}'::jsonb, now(), FALSE);

      INSERT INTO circle (entity_id, code, name, color_token, display_order)
      VALUES (e, '{marqueur}-cercle', 'Cercle des essais', 'bleu', 0) RETURNING id INTO ci;
      INSERT INTO job_catalog (entity_id, code, label, display_order, active)
      VALUES (e, '{marqueur}-job', 'Ingenieure logicielle', 0, TRUE) RETURNING id INTO jc;
      INSERT INTO client (canonical_name, display_name, status)
      VALUES ('{marqueur}-client', 'Client Alpha', 'active') RETURNING id INTO cl;
      INSERT INTO entity_client (entity_id, client_id) VALUES (e, cl);

      -- Le DSM, sa responsabilite AVANT son affectation : la base l'exige.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-dsm@x.test', '{marqueur}-dsm@x.test', 'Dominique', 'Lesmanager',
              'active') RETURNING id INTO dm;
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at, ends_at)
      VALUES (dm, e, 'DSM', dm, now() - INTERVAL '30 days', NULL);

      -- Le profil COMPLET, avec ses six champs sensibles.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-complete@x.test', '{marqueur}-complete@x.test', 'Ada', 'Complete',
              'active') RETURNING id INTO d;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date, membership_state,
        professional_category, profile_visibility, short_bio, fun_fact)
      VALUES (d, e, DATE '2026-01-15', 'active', 'consultant', 'published',
              'Ingenieure passionnee.', 'Joue du theorbe.') RETURNING id INTO m;
      INSERT INTO membership_job_assignment (entity_id, entity_membership_id, job_catalog_id,
        starts_at, ends_at) VALUES (e, m, jc, now() - INTERVAL '30 days', NULL);
      INSERT INTO professional_status_assignment (entity_id, entity_membership_id, status,
        client_id, starts_at, ends_at)
      VALUES (e, m, 'mission', cl, now() - INTERVAL '30 days', NULL);
      INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id,
        starts_at, ends_at) VALUES (e, m, dm, now() - INTERVAL '30 days', NULL);
      INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id,
        membership_type, starts_at, ends_at)
      VALUES (e, m, ci, 'principal', now() - INTERVAL '30 days', NULL);
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id,
         starts_at, ends_at)
      VALUES (d, e, 'BOOSTER', ci, d, now() - INTERVAL '30 days', NULL);

      -- Un profil EXCLU de la liste : appartenance partie, profil RESTE publie.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-parti@x.test', '{marqueur}-parti@x.test', 'Ivan', 'Parti', 'active')
      RETURNING id INTO d;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date,
        membership_state, professional_category, profile_visibility)
      VALUES (d, e, DATE '2026-01-15', DATE '2026-06-01', 'departed', 'consultant', 'published');
    END $$;
    """  # noqa: S608


def nettoyer(compose: list[str], env: dict[str, str], marqueur: str, debut: str) -> None:
    """L'ordre suit les cles etrangeres ; la borne temporelle attrape le reste."""
    motif = f"{marqueur}%"
    for requete in (
        f"DELETE FROM auth_event WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM user_session WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM admin_password_credential WHERE user_account_id IN (SELECT id FROM user_account WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}'))",  # noqa: S608,E501
        f"DELETE FROM user_account WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM framework_responsibility_assignment WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM dsm_assignment WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM circle_membership WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM membership_job_assignment WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM professional_status_assignment WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM entity_membership WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM entity_client WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608
        f"DELETE FROM job_catalog WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM client WHERE canonical_name LIKE '{motif}'",  # noqa: S608
        f"DELETE FROM person WHERE email_normalized LIKE '{motif}'",  # noqa: S608
        f"DELETE FROM entity WHERE code LIKE '{motif}'",  # noqa: S608
        "DELETE FROM auth_event WHERE person_id IS NULL AND service_account_id IS NULL "  # noqa: S608
        f"AND created_at >= '{debut}'",
    ):
        psql(compose, env, requete)


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

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    adresse = f"{MARQUEUR}@{domaine}"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")
    code_entite = f"{MARQUEUR}-e"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Fiche profil complete — US004, cahier §10.2")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(
        f"    info     {len(CHAMPS_FICHE)} champs attendus, dont {len(CHAMPS_SENSIBLES)} sensibles"
    )

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not valeur(debut):
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = valeur(debut)

    code, sortie = psql(
        compose,
        env,
        poser_le_decor(
            MARQUEUR,
            code_entite,
            adresse,
            empreinte_mdp,
            ALGORITHME,
            json.dumps(parametres_hachage),
        ),
    )
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor : un profil COMPLET, un profil EXCLU, + un admin local")

    try:
        liste = CHEMIN_TROMBINOSCOPE.format(code=code_entite)

        # --- 1. TEMOIN : la connexion reussit et pose un cookie ---------------
        controles += 1
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        jeton = ""
        for pose in connexion.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                jeton = pose.split("=", 1)[1].split(";", 1)[0]
        if connexion.statut == 200 and jeton:
            print("    ok       TEMOIN : la connexion reussit et pose un cookie")
        else:
            echecs += 1
            print(
                f"    ECHEC    connexion : {connexion.statut}, cookie {'oui' if jeton else 'NON'}"
            )
            return 1
        biscuit = {"Cookie": f"{nom_cookie}={jeton}"}

        # --- 2. LE LIEN AVEC LA LISTE : l'identifiant vient du trombinoscope --
        controles += 1
        corps = appeler(arguments.base, liste, contexte, en_tetes=biscuit).json()
        lignes = corps.get("collaborateurs", []) if isinstance(corps, dict) else []
        rendus = {ligne["last_name"]: ligne["id"] for ligne in lignes}
        if set(rendus) == {"Complete"}:
            print(
                "    ok       la liste rend EXACTEMENT le profil listable — le parti en est absent"
            )
        else:
            echecs += 1
            print(f"    ECHEC    la liste rend {sorted(rendus)}, ['Complete'] attendu")
            return 1
        appartenance = rendus["Complete"]

        # --- 3. la fiche de cet identifiant EST servie ------------------------
        controles += 1
        chemin = CHEMIN_PROFIL.format(code=code_entite, appartenance=appartenance)
        fiche_reponse = appeler(arguments.base, chemin, contexte, en_tetes=biscuit)
        fiche = fiche_reponse.json()
        if fiche_reponse.statut == 200 and isinstance(fiche, dict):
            print("    ok       la fiche de l'identifiant rendu par la LISTE est servie")
        else:
            echecs += 1
            print(f"    ECHEC    fiche : {fiche_reponse.statut}, {str(fiche)[:120]}")
            return 1

        # --- 4. les champs, ni plus ni moins ---------------------------------
        controles += 1
        if set(fiche) == CHAMPS_FICHE:
            print(f"    ok       {len(CHAMPS_FICHE)} champs servis, ni plus ni moins")
        else:
            echecs += 1
            manque = sorted(CHAMPS_FICHE - set(fiche))
            en_trop = sorted(set(fiche) - CHAMPS_FICHE)
            print(f"    ECHEC    champs : manquants {manque}, en trop {en_trop}")

        # --- 5. AUCUN champ sensible n'est masque ----------------------------
        controles += 1
        nuls = [champ for champ in CHAMPS_SENSIBLES if fiche.get(champ) is None]
        if not nuls:
            print(
                f"    ok       les {len(CHAMPS_SENSIBLES)} champs sensibles sont TOUS "
                "renseignes — la matrice ne masque aucun champ (ECART-051)"
            )
        else:
            echecs += 1
            print(f"    ECHEC    champ(s) sensible(s) nul(s) : {nuls}")

        # --- 6. les relations multiples et leur portee ------------------------
        controles += 1
        principal = fiche.get("cercle_principal") or {}
        responsabilites = fiche.get("responsabilites") or []
        portee_juste = (
            len(responsabilites) == 1
            and responsabilites[0].get("type") == "BOOSTER"
            and responsabilites[0].get("cercle") == "Cercle des essais"
            and responsabilites[0].get("bureau") is None
        )
        if principal.get("nom") == "Cercle des essais" and portee_juste:
            print("    ok       cercle principal et responsabilite BOOSTER portee sur le CERCLE")
        else:
            echecs += 1
            print(f"    ECHEC    principal {principal}, responsabilites {responsabilites}")

        # --- 7. le profil EXCLU de la liste est INTROUVABLE -------------------
        controles += 1
        code_sql, brut = psql(
            compose,
            env,
            "SELECT em.id FROM entity_membership em JOIN person p ON p.id = em.person_id "  # noqa: S608
            f"WHERE p.email_normalized = '{MARQUEUR}-parti@x.test'",
        )
        exclu = valeur(brut)
        if code_sql or not exclu:
            echecs += 1
            print(f"    ECHEC    identifiant du profil exclu introuvable : {brut[:120]}")
        else:
            refus = appeler(
                arguments.base,
                CHEMIN_PROFIL.format(code=code_entite, appartenance=exclu),
                contexte,
                en_tetes={**biscuit, "X-Request-ID": CORRELATION_FIXE},
            )
            inconnu = appeler(
                arguments.base,
                CHEMIN_PROFIL.format(code=code_entite, appartenance=uuid.uuid4()),
                contexte,
                en_tetes={**biscuit, "X-Request-ID": CORRELATION_FIXE},
            )
            if refus.statut == inconnu.statut == 404 and refus.signature() == inconnu.signature():
                print(
                    "    ok       le profil EXCLU de la liste rend le MEME 404 qu'un "
                    "identifiant inconnu — corps ET en-tetes"
                )
                print(f"             non compare : {', '.join(sorted(EN_TETES_NON_COMPARABLES))}")
            else:
                echecs += 1
                print(f"    ECHEC    refus divergents : {refus.statut}/{inconnu.statut}")

        # --- 8. une AUTRE entite ne sert pas cette fiche -----------------------
        controles += 1
        autre = f"{MARQUEUR}-bis"
        psql(
            compose,
            env,
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "  # noqa: S608
            f"VALUES ('{autre}', 'Autre {MARQUEUR}', 'Lyon', 'FR', 'active', 'Europe/Paris')",
        )
        ailleurs = appeler(
            arguments.base,
            CHEMIN_PROFIL.format(code=autre, appartenance=appartenance),
            contexte,
            en_tetes=biscuit,
        )
        if ailleurs.statut == 404:
            print("    ok       la meme appartenance est INTROUVABLE sous une autre entite")
        else:
            echecs += 1
            print(f"    ECHEC    isolation : {ailleurs.statut}, 404 attendu")

        # --- 9. sans session, la fiche refuse ---------------------------------
        controles += 1
        sans = appeler(arguments.base, chemin, contexte)
        if sans.statut == 401:
            print("    ok       sans session : 401 — la matrice §5 refuse `ANON`")
        else:
            echecs += 1
            print(f"    ECHEC    sans session : {sans.statut}, 401 attendu")

        # --- 10. un identifiant mal forme est refuse au format du §18.3 --------
        controles += 1
        mal = appeler(
            arguments.base,
            CHEMIN_PROFIL.format(code=code_entite, appartenance="pas-un-uuid"),
            contexte,
            en_tetes=biscuit,
        )
        corps_mal = mal.json()
        erreur = corps_mal.get("erreur", {}) if isinstance(corps_mal, dict) else {}
        if mal.statut == 422 and erreur.get("champ") == "path.appartenance":
            print("    ok       identifiant mal forme refuse, champ nomme, format du §18.3")
        else:
            echecs += 1
            print(f"    ECHEC    identifiant mal forme : {mal.statut}, {str(corps_mal)[:110]}")
    finally:
        nettoyer(compose, env, MARQUEUR, debut)

    print()
    print(f"    controles executes : {controles}   echecs : {echecs}")
    if echecs:
        return 1
    print(
        "  --> la fiche profil sert les champs du §10.2, n'en masque aucun, et suit "
        "exactement la population du trombinoscope"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
