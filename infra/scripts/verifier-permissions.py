#!/usr/bin/env python3
"""Le changement d'entite recharge les permissions, et n'en transfere AUCUNE.

LOT 4, sous-etape `T8`, story `MVP-L04-US002`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI CHAQUE PREUVE DISCRIMINE

  Le cahier §23.3 et la matrice §23.3 posent cinq regles. La matrice §5.1 dit ce
  que deviennent les permissions, et la §23.1 ce qu'elles cumulent. Le decor est
  concu pour que **l'echec de chaque regle produise une observation DIFFERENTE du
  succes** -- §7.0, quatrieme proposition -- en DEUX appels seulement :

    entite A, principale       ESM actif            -> `ESM` attendu
                               ENTITY_ADMIN actif   -> `ADM-E` attendu
                               OFFICE_MANAGER CLOS  -> attendu ABSENT (§24.12)
                               DSM FUTUR            -> attendu ABSENT
    entite B, autre            ENTITY_ADMIN actif   -> attendu ABSENT (§5.1)

  Les quatre discriminations sont dans deux reponses. Un contrôle qui n'aurait
  pose qu'une entite et qu'un role actif aurait rendu la meme observation qu'un
  service qui ignore les periodes, qui ignore l'entite, ou qui cumule tout.

  **LE ROLE DE B EXISTE VRAIMENT EN BASE.** C'est ce qui fait la valeur du
  controle 4 : il ne prouve pas qu'un role absent est absent, il prouve qu'un
  role PRESENT ne s'applique pas. La difference est exactement celle que le §7.0
  nomme -- sans lui, l'observation serait la meme dans les deux cas.

UNE CONTRAINTE MESUREE A FERME LA CONCEPTION DU DECOR

  `ex_framework_responsibility_assignment_sans_portee` exclut sur
  `(person_id, responsibility_type, period)` **SANS `entity_id`** : une personne
  ne peut pas etre `ESM` dans deux entites a la fois. Le decor emploie donc
  `ENTITY_ADMIN` pour l'entite B, dont l'exclusion, elle, porte `entity_id`.

  Ce n'etait pas prevu : la premiere conception voulait « ESM dans A et ESM dans
  B ». La mesure l'a refusee avant la premiere execution.

LES REGLES 1 ET 2 SONT DES INTERDICTIONS D'ECRITURE, ET ON NE LES CROIT PAS

  « Ne modifie pas l'entite principale », « ne transfere pas ses
  responsabilites ». Depuis `DEC-545` le changement d'entite est une NAVIGATION,
  donc aucune ecriture n'existe -- mais le §7.32 dit quoi faire d'un etat que la
  conception rend impossible : **exiger qu'il le reste**. Les quatre tables de
  rattachement sont donc relevees AVANT et APRES le parcours complet, et
  comparees.

  **ET CE QUI CHANGE PAR CONCEPTION EST NOMME, PAS TU.** `user_session.
  last_activity_at` est reecrit a chaque lecture metier : `exiger_une_session`
  reutilise `lire_et_rafraichir`, le seul chemin de validation du projet, et
  `DEC-531` a examine puis accepte cette entorse. Le contrôle le RAPPORTE et
  exige que le changement porte sur cette colonne SEULEMENT. C'est le §7.20 :
  exiger ce qui est exigible, rapporter visiblement ce qui ne l'est pas.
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
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"
CHEMIN_PERMISSIONS = "/api/v1/entities/{code}/permissions"

MARQUEUR = f"t8l4-{os.urandom(6).hex()}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l4t8-egalite-des-refus"
EN_TETES_NON_COMPARABLES = frozenset({"date"})

#  Les tables qui portent le rattachement et les responsabilites. Les regles 1
#  et 2 du §23.3 portent sur elles, et sur aucune autre.
TABLES_DE_RATTACHEMENT = (
    "entity_membership",
    "framework_responsibility_assignment",
    "technical_role_assignment",
    "dsm_assignment",
)


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
        """Ce que l'appelant observe, hors horloge."""
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


def roles_de(reponse: Reponse) -> list[str] | None:
    corps = reponse.json()
    if not isinstance(corps, dict) or not isinstance(corps.get("roles"), list):
        return None
    return [str(r) for r in corps["roles"]]


def empreinte_des_rattachements(compose: list[str], env: dict[str, str]) -> str | None:
    """Une empreinte des QUATRE tables du §23.3, lignes triees.

    `md5` d'un agregat trie, et non un simple `count(*)` : une ligne modifiee
    sans changement de nombre donnerait la meme observation qu'un etat intact.
    """
    unions = " UNION ALL ".join(
        f"SELECT '{table}'||':'||id::text||':'||md5(t.*::text) AS l FROM {table} t"  # noqa: S608
        for table in TABLES_DE_RATTACHEMENT
    )
    code, sortie = psql(
        compose,
        env,
        f"SELECT md5(string_agg(l, '|' ORDER BY l)) FROM ({unions}) x",  # noqa: S608
    )
    return None if code else valeur(sortie)


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
    from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
    from app.people.modeles import CategorieProfessionnelle, EtatAppartenance, VisibiliteProfil
    from app.permissions.services import (
        CORRESPONDANCE_RESPONSABILITES,
        CORRESPONDANCE_ROLES_TECHNIQUES,
        RoleDeLaMatrice,
    )

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    sujet = f"{MARQUEUR}@{domaine}"
    super_admin = f"{MARQUEUR}-super@{domaine}"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"
    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    #  Les attendus sont DERIVES des correspondances du service, jamais ecrits en
    #  litteral : si un type de responsabilite etait ajoute et mal appareille,
    #  cette derivation le porterait et le controle changerait de verdict. §7.27.
    role_esm = CORRESPONDANCE_RESPONSABILITES[TypeResponsabilite.ESM.value].value
    role_office = CORRESPONDANCE_RESPONSABILITES[TypeResponsabilite.OFFICE_MANAGER.value].value
    role_dsm = CORRESPONDANCE_RESPONSABILITES[TypeResponsabilite.DSM.value].value
    role_admin_entite = CORRESPONDANCE_ROLES_TECHNIQUES[TypeRoleTechnique.ENTITY_ADMIN.value].value
    role_super = CORRESPONDANCE_ROLES_TECHNIQUES[TypeRoleTechnique.SUPER_ADMIN.value].value
    role_employe = RoleDeLaMatrice.EMPLOYE.value

    #  L'ORDRE ATTENDU EST DERIVE DE L'ENUMERATION, pas trie ni ecrit a la main.
    #  `RoleDeLaMatrice` suit le tableau du §3 de la matrice, et c'est cet ordre
    #  que la reponse doit porter. Une liste triee alphabetiquement serait une
    #  SECONDE definition de l'ordre, qui divergerait au premier role ajoute.
    def dans_l_ordre(codes: set[str]) -> list[str]:
        return [membre.value for membre in RoleDeLaMatrice if membre.value in codes]

    attendus_dans_a = dans_l_ordre({role_employe, role_esm, role_admin_entite})
    attendus_dans_b = dans_l_ordre({role_employe})

    print()
    print("  Changement d'entite : les permissions rechargees, aucune transferee")
    print("    (cahier §23.3 · matrice §5.1, §23.1, §23.3 · backlog `MVP-L04-US002`)")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(f"    info     attendu dans l'entite PRINCIPALE : {attendus_dans_a}")
    print(f"    info     attendu dans une AUTRE entite    : {attendus_dans_b}")

    echecs = 0
    controles = 0
    #  DEUX VALEURS QUE J'AVAIS INVENTEES. `profile_visibility` a ete ecrite
    #  `'entity'` a la premiere version, et la base a REFUSE le decor --
    #  `ck_entity_membership_profile_visibility_valide`. Le §6.2 declare
    #  `draft`, `published`, `hidden`. Les deux sont desormais DERIVEES de leur
    #  enumeration, comme le filtre `= active` de `T1` l'est de `StatutEntite`.
    categorie = CategorieProfessionnelle.CONSULTANT.value
    visibilite = VisibiliteProfil.DRAFT.value

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)
    empreinte_avant = empreinte_des_rattachements(compose, env)
    if empreinte_avant is None:
        print("    ECHEC    empreinte des rattachements illisible AVANT le decor")
        return 1

    decor = f"""
    DO $$
    DECLARE a uuid; b uuid; bureau uuid; p uuid; s uuid; c uuid; cs uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}-a', 'Entite A {MARQUEUR}', 'Bordeaux', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO a;
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}-b', 'Entite B {MARQUEUR}', 'Lille', 'FR', 'active',
              'Europe/Paris') RETURNING id INTO b;
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}-d', 'Entite D {MARQUEUR}', 'Nantes', 'FR', 'draft',
              'Europe/Paris');
      INSERT INTO office (code, name, display_order, entity_id)
      VALUES ('{MARQUEUR}-bde', 'BDE {MARQUEUR}', 1, a) RETURNING id INTO bureau;

      --  LE SUJET : rattache a A, donc A est son entite PRINCIPALE.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{sujet}', '{sujet}', 'Sujet', 'L4T8', 'active') RETURNING id INTO p;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (p, a, now() - interval '30 days', '{EtatAppartenance.ACTIVE.value}',
              '{categorie}', '{visibilite}');

      --  DANS A : deux droits ACTIFS, un CLOS, un FUTUR.
      --  `assigned_by_person_id` est NOT NULL -- le §8.4 exige un attributeur, et
      --  `CLAUDE.md` §4.14 rappelle qu'en inventer un « fabriquerait une trace
      --  d'audit fausse ». Ici le decor est ENTIEREMENT fictif et marque, donc le
      --  sujet est son propre attributeur : aucune trace reelle n'est fabriquee, et
      --  le nettoyage supprime la ligne avec le reste.
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at, ends_at)
      VALUES (p, a, '{TypeResponsabilite.ESM.value}', p, now() - interval '1 day', NULL);
      INSERT INTO technical_role_assignment
        (person_id, entity_id, role_type, starts_at, ends_at)
      VALUES (p, a, '{TypeRoleTechnique.ENTITY_ADMIN.value}', now() - interval '1 day', NULL);
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, office_id, assigned_by_person_id,
         starts_at, ends_at)
      VALUES (p, a, '{TypeResponsabilite.OFFICE_MANAGER.value}', bureau, p,
              now() - interval '10 days', now() - interval '5 days');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at, ends_at)
      VALUES (p, a, '{TypeResponsabilite.DSM.value}', p, now() + interval '10 days', NULL);

      --  DANS B : un droit ACTIF, qui NE DOIT PAS s'appliquer (§5.1). Il EXISTE,
      --  et c'est ce qui donne sa valeur au controle : sans lui, l'absence de
      --  `ADM-E` dans B serait indistinguable d'une absence de donnee.
      INSERT INTO technical_role_assignment
        (person_id, entity_id, role_type, starts_at, ends_at)
      VALUES (p, b, '{TypeRoleTechnique.ENTITY_ADMIN.value}', now() - interval '1 day', NULL);

      --  LE SUPER-ADMINISTRATEUR : rattache a B, donc A n'est PAS son entite
      --  principale -- et son role doit s'y appliquer quand meme (§5.1).
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{super_admin}', '{super_admin}', 'Super', 'L4T8', 'active') RETURNING id INTO s;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (s, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO cs;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (cs, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (s, b, now() - interval '30 days', '{EtatAppartenance.ACTIVE.value}',
              '{categorie}', '{visibilite}');
      INSERT INTO technical_role_assignment
        (person_id, entity_id, role_type, starts_at, ends_at)
      VALUES (s, NULL, '{TypeRoleTechnique.SUPER_ADMIN.value}', now() - interval '1 day', NULL);
    END $$;
    """  # noqa: S608 — seuls `MARQUEUR` et des enumerations du code sont interpoles
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:400]}")
        return 1
    print("    ok       decor : 3 entites, 1 bureau, 2 personnes, 6 droits")

    empreinte_decor = empreinte_des_rattachements(compose, env)
    if empreinte_decor is None:
        print("    ECHEC    empreinte des rattachements illisible APRES le decor")
        return 1
    if empreinte_decor == empreinte_avant:
        #  TEMOIN DE L'EMPREINTE ELLE-MEME. Si elle ne bougeait pas apres huit
        #  insertions, le controle 12 ne prouverait rien : une empreinte
        #  constante rendrait la meme observation qu'une base intacte. §7.0.
        print("    ECHEC    l'empreinte n'a PAS bouge apres le decor — elle ne mesure rien")
        return 1
    print("    ok       TEMOIN : l'empreinte des 4 tables a bouge avec le decor")

    def permissions(cookie: str, code_entite: str) -> Reponse:
        return appeler(
            arguments.base,
            CHEMIN_PERMISSIONS.format(code=code_entite),
            contexte,
            en_tetes={"Cookie": cookie},
        )

    def session_de(adresse: str) -> str:
        reponse = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        for pose in reponse.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                return pose.split(";")[0]
        return ""

    try:
        # --- 1. sans cookie : la matrice met `ANON` a tiret
        controles += 1
        sans = appeler(
            arguments.base,
            CHEMIN_PERMISSIONS.format(code=f"{MARQUEUR}-a"),
            contexte,
            en_tetes={"X-Request-ID": CORRELATION_FIXE},
        )
        if sans.statut == 401:
            print("    ok       sans cookie : 401 — matrice §5, `ANON` est a tiret")
        else:
            echecs += 1
            print(f"    ECHEC    sans cookie : {sans.statut} au lieu de 401")

        # --- 2. TEMOIN : la connexion du sujet reussit
        controles += 1
        cookie_sujet = session_de(sujet)
        if cookie_sujet:
            print("    ok       TEMOIN : la connexion du sujet pose un cookie de session")
        else:
            echecs += 1
            print(
                "    ECHEC    TEMOIN : pas de cookie — les controles suivants ne prouveraient rien"
            )
            raise RuntimeError("sans session, rien n'est prouvable")

        # --- 3. dans l'entite PRINCIPALE : l'union du §23.1
        controles += 1
        dans_a = permissions(cookie_sujet, f"{MARQUEUR}-a")
        corps_a = dans_a.json()
        roles_a = roles_de(dans_a)
        if dans_a.statut == 200 and roles_a == attendus_dans_a:
            print(
                f"    ok       entite PRINCIPALE : {roles_a} — l'union du §23.1, "
                f"`EMP` + les deux droits actifs"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    entite PRINCIPALE : {dans_a.statut}, roles {roles_a} "
                f"au lieu de {attendus_dans_a}"
            )

        # --- 4. `est_entite_principale` le dit
        controles += 1
        if isinstance(corps_a, dict) and corps_a.get("est_entite_principale") is True:
            print("    ok       entite PRINCIPALE : `est_entite_principale` vaut vrai")
        else:
            echecs += 1
            print(f"    ECHEC    `est_entite_principale` : {corps_a!r}")

        # --- 5. le role CLOTURE n'accorde rien — controle §24.12 du cahier
        controles += 1
        if roles_a is not None and role_office not in roles_a:
            print(
                f"    ok       role CLOTURE : `{role_office}` absent — controle §24.12, "
                f"« un role cloture ne continue pas a accorder des permissions »"
            )
        else:
            echecs += 1
            print(f"    ECHEC    role CLOTURE : `{role_office}` accorde alors qu'il est clos")

        # --- 6. l'affectation FUTURE n'accorde rien — le piege de `ends_at IS NULL`
        controles += 1
        if roles_a is not None and role_dsm not in roles_a:
            print(
                f"    ok       affectation FUTURE : `{role_dsm}` absent — `ends_at IS NULL` "
                f"n'aurait PAS suffi, elle a `ends_at` nul elle aussi"
            )
        else:
            echecs += 1
            print(f"    ECHEC    affectation FUTURE : `{role_dsm}` accorde avant son debut")

        # --- 7. le droit local de B EXISTE en base
        controles += 1
        code_compte, compte = psql(
            compose,
            env,
            #  Seul `MARQUEUR`, un tirage de ce module, est interpole.
            "SELECT count(*) FROM technical_role_assignment t "  # noqa: S608
            "JOIN entity e ON e.id = t.entity_id "
            "JOIN person p ON p.id = t.person_id "
            f"WHERE e.code = '{MARQUEUR}-b' AND p.email_normalized = '{sujet}' "
            "AND t.period @> now()",
        )
        if not code_compte and valeur(compte) == "1":
            print(
                "    ok       le droit local de B EXISTE et est ACTIF en base — "
                "sans lui, le controle suivant ne prouverait rien"
            )
        else:
            echecs += 1
            print(f"    ECHEC    droit local de B introuvable : {compte[:120]}")

        # --- 8. dans une AUTRE entite : `EMP` SEULEMENT — le coeur du §5.1
        controles += 1
        dans_b = permissions(cookie_sujet, f"{MARQUEUR}-b")
        corps_b = dans_b.json()
        roles_b = roles_de(dans_b)
        if dans_b.statut == 200 and roles_b == attendus_dans_b:
            print(
                f"    ok       AUTRE entite : {roles_b} EXACTEMENT — §5.1, "
                f"« elle possede uniquement les droits `EMP` », et `{role_admin_entite}` "
                f"ne s'applique PAS alors qu'il existe"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    AUTRE entite : {dans_b.statut}, roles {roles_b} "
                f"au lieu de {attendus_dans_b} — une permission locale a ete TRANSFEREE"
            )

        # --- 9. et `est_entite_principale` vaut faux
        controles += 1
        if isinstance(corps_b, dict) and corps_b.get("est_entite_principale") is False:
            print("    ok       AUTRE entite : `est_entite_principale` vaut faux")
        else:
            echecs += 1
            print(f"    ECHEC    `est_entite_principale` : {corps_b!r}")

        # --- 10. le super-administrateur s'applique HORS de son entite principale
        controles += 1
        cookie_super = session_de(super_admin)
        if not cookie_super:
            echecs += 1
            print("    ECHEC    TEMOIN : le super-administrateur n'a pas de session")
            raise RuntimeError("sans sa session, l'exception globale n'est pas verifiable")
        super_dans_a = permissions(cookie_super, f"{MARQUEUR}-a")
        roles_super_a = roles_de(super_dans_a)
        corps_super_a = super_dans_a.json()
        hors_principale = (
            isinstance(corps_super_a, dict) and corps_super_a.get("est_entite_principale") is False
        )
        if roles_super_a is not None and role_super in roles_super_a and hors_principale:
            print(
                f"    ok       exception GLOBALE : `{role_super}` s'applique dans une entite "
                f"qui n'est PAS la sienne — §5.1, « la seule exception globale »"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    exception globale : roles {roles_super_a}, "
                f"principale={not hors_principale}"
            )

        # --- 11. et dans son entite principale aussi
        controles += 1
        super_dans_b = permissions(cookie_super, f"{MARQUEUR}-b")
        roles_super_b = roles_de(super_dans_b)
        if roles_super_b is not None and role_super in roles_super_b:
            print(f"    ok       exception GLOBALE : `{role_super}` s'applique aussi chez lui")
        else:
            echecs += 1
            print(f"    ECHEC    exception globale dans son entite : {roles_super_b}")

        # --- 12. l'entite non ACTIVE rend le MEME 404 que `GET /entities/{code}`
        controles += 1
        brouillon = f"{MARQUEUR}-d"
        #  **LA CORRELATION EST EPINGLEE, PAS EXCLUE.** Premiere version : je
        #  comparais les deux signatures telles quelles, et le controle a echoue
        #  sur un livrable CONFORME -- l'identifiant de correlation est engendre
        #  PAR REQUETE, et le cahier §17.4 exige qu'il le soit pour qu'un
        #  utilisateur puisse le citer dans un signalement. Mon controle exigeait
        #  donc plus que le critere, ce qui est le defaut du §7.20.
        #
        #  Deux remedes possibles : EXCLURE le champ des deux cotes, ou EPINGLER
        #  la correlation en l'envoyant. Le second est retenu, parce que le
        #  premier rendrait le controle aveugle a la DISPARITION du champ --
        #  l'echec produirait alors la meme observation que le succes (§7.0). En
        #  epinglant, la comparaison reste TOTALE : corps entier et en-tetes.
        #
        #  Et c'est la parade que `verifier-entites.py` employait deja : sa
        #  constante `CORRELATION_FIXE` existe pour cette raison exacte.
        entetes_404 = {"Cookie": cookie_sujet, "X-Request-ID": CORRELATION_FIXE}
        p404 = appeler(
            arguments.base,
            CHEMIN_PERMISSIONS.format(code=brouillon),
            contexte,
            en_tetes=entetes_404,
        )
        e404 = appeler(
            arguments.base,
            CHEMIN_UNE_ENTITE.format(code=brouillon),
            contexte,
            en_tetes=entetes_404,
        )
        correlation_rendue = p404.en_tetes.get("x-request-id") == CORRELATION_FIXE
        if p404.statut == 404 and correlation_rendue and p404.signature() == e404.signature():
            print(
                "    ok       entite `draft` : 404, et la signature est IDENTIQUE a celle de "
                "`GET /entities/{code}` — corps ET en-tetes comparables"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    404 divergent : permissions {p404.statut}, entite "
                f"{e404.statut} ; correlation epinglee "
                f"{'rendue' if correlation_rendue else 'IGNOREE'} ; signatures "
                f"{'egales' if p404.signature() == e404.signature() else 'DIFFERENTES'}"
            )

        # --- 13. l'ordre des roles est TOTAL : deux appels, un corps identique
        controles += 1
        #  **CE CONTROLE A ETE REECRIT DEUX FOIS, ET LA SECONDE FOIS C'EST LE
        #  LIVRABLE QUI A CHANGE.** Premiere version : il ne comparait que deux
        #  appels entre eux, et les controles 3 et 8 RETRIAIENT la reponse avant
        #  de la comparer -- l'ordre n'etait donc exige nulle part. Mesure du
        #  24/08/2026 : le `sorted` retire du service, les quinze controles
        #  passaient TROIS FOIS sur trois.
        #
        #  Seconde version : exiger que la reponse soit triee. **Toujours vert
        #  avec le defaut**, parce que l'iteration du `set` de ce decor coincide
        #  avec l'ordre alphabetique. Et la renforcer davantage etait impossible :
        #  deux ensembles egaux s'iterent identiquement en CPython, et l'ordre ne
        #  varie qu'entre PROCESSUS -- ce qu'aucune execution unique n'observe.
        #
        #  **La conclusion a porte sur le code, pas sur le controle** : l'ordre
        #  vient desormais de l'iteration de `RoleDeLaMatrice`, donc le perdre
        #  exigerait de supprimer la boucle. Ce controle verifie la conformite a
        #  cet ordre, et c'est une exigence que l'on peut tenir.
        rejeu = permissions(cookie_sujet, f"{MARQUEUR}-a")
        ordonne = roles_a is not None and roles_a == dans_l_ordre(set(roles_a))
        if rejeu.statut == 200 and rejeu.corps == dans_a.corps and ordonne:
            print(
                "    ok       ordre : celui du tableau §3 de la matrice, DERIVE de "
                "l'enumeration — et deux appels rendent le meme corps octet a octet"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    ordre : conforme a l'enumeration={ordonne}, rejeu "
                f"{'identique' if rejeu.corps == dans_a.corps else 'DIFFERENT'} — "
                f"{dans_a.corps[:100]!r}"
            )

        # --- 14. regles 1 et 2 du §23.3 : AUCUNE ecriture de rattachement
        controles += 1
        empreinte_apres = empreinte_des_rattachements(compose, env)
        if empreinte_apres is not None and empreinte_apres == empreinte_decor:
            print(
                f"    ok       regles 1 et 2 : les {len(TABLES_DE_RATTACHEMENT)} tables de "
                f"rattachement sont INCHANGEES apres 6 lectures et 2 changements d'entite"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    une table de rattachement a CHANGE : {empreinte_decor} "
                f"-> {empreinte_apres}"
            )

        # --- 15. ce qui change PAR CONCEPTION est nomme, pas tu
        controles += 1
        code_activite, activite = psql(
            compose,
            env,
            #  Seul `MARQUEUR` est interpole.
            "SELECT count(*) FROM user_session s JOIN person p ON p.id = s.person_id "  # noqa: S608
            f"WHERE p.email_normalized IN ('{sujet}', '{super_admin}') "
            "AND s.last_activity_at > s.created_at",
        )
        if not code_activite and valeur(activite) != "0":
            print(
                f"    ok       et ce qui change PAR CONCEPTION est nomme : "
                f"{valeur(activite)} session(s) ont vu `last_activity_at` avancer. "
                f"`exiger_une_session` reutilise `lire_et_rafraichir`, seul chemin de "
                f"validation du projet — entorse examinee et acceptee par `DEC-531`"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    `last_activity_at` n'a PAS avance : {activite[:120]} — "
                f"le rafraichissement de session n'a donc pas eu lieu, contrairement a "
                f"ce que `DEC-531` decrit"
            )

    except RuntimeError as arret:
        print(f"    info     arret : {arret}")
    finally:
        nettoyage = f"""
        DO $$
        DECLARE ids uuid[];
        BEGIN
          SELECT array_agg(id) INTO ids FROM person
           WHERE email_normalized LIKE '{MARQUEUR}%';
          IF ids IS NOT NULL THEN
            DELETE FROM auth_event WHERE person_id = ANY(ids);
            DELETE FROM audit_event WHERE actor_person_id = ANY(ids);
            DELETE FROM user_session WHERE person_id = ANY(ids);
            DELETE FROM admin_password_credential
             WHERE user_account_id IN (SELECT id FROM user_account WHERE person_id = ANY(ids));
            DELETE FROM user_account WHERE person_id = ANY(ids);
            DELETE FROM technical_role_assignment WHERE person_id = ANY(ids);
            DELETE FROM framework_responsibility_assignment WHERE person_id = ANY(ids);
            DELETE FROM entity_membership WHERE person_id = ANY(ids);
            DELETE FROM person WHERE id = ANY(ids);
          END IF;
          DELETE FROM office WHERE code LIKE '{MARQUEUR}%';
          DELETE FROM entity WHERE code LIKE '{MARQUEUR}%';
        END $$;
        """  # noqa: S608 — seul `MARQUEUR` est interpole
        #  L'ORDRE COMPTE, ET LE NETTOYAGE EST UNE SEULE TRANSACTION. Un ordre
        #  fautif la fait echouer, et son echec l'ANNULE ENTIEREMENT : rien n'est
        #  supprime, pas meme ce qui aurait pu l'etre. C'est le defaut `T2-2`, et
        #  ses 23 tests du LOT 2 en echec avec des messages qui ne nommaient pas
        #  la cause. `make residu-check` est ce qui le dirait.
        code_nettoyage, sortie_nettoyage = psql(compose, env, nettoyage)
        if code_nettoyage:
            print(f"    ECHEC    nettoyage incomplet : {sortie_nettoyage[:250]}")
            echecs += 1
        else:
            residu = empreinte_des_rattachements(compose, env)
            if residu == empreinte_avant:
                print("    ok       nettoyage : l'empreinte est REVENUE a son etat d'avant")
            else:
                print(f"    ECHEC    residu : empreinte {residu} au lieu de {empreinte_avant}")
                echecs += 1

    print()
    print(f"    controles attendus : 15   executes : {controles}   echecs : {echecs}")
    if controles != 15:
        print(f"    ECHEC    {controles} controles executes au lieu de 15 — un chemin a saute")
        return 1
    if echecs:
        print(f"  --> {echecs} echec(s)")
        return 1
    print("  --> le changement d'entite recharge les permissions, et n'en transfere aucune")
    return 0


if __name__ == "__main__":
    sys.exit(main())
