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

`T5` AJOUTE LA PHOTO ICI, ET NE DUPLIQUE PAS CE HARNAIS

  La miniature est un CHAMP de la fiche et un CHAMP de la liste : son critere --
  « l'originale jamais servie **dans la liste** » -- porte sur les deux. Ecrire
  un second verificateur aurait duplique le decor, la connexion et le menage,
  donc trois sources a maintenir pour une seule regle (§7.27).

  **ET IL PROUVE CE QU'AUCUN TEST NE PROUVE : LES OCTETS.** Deux objets sont
  deverses dans MinIO -- la miniature et l'original, avec des contenus
  differents -- et le controle exige que la route rende **exactement** ceux de la
  miniature. Un controle qui se contenterait de « 200 et des octets » passerait
  si la route servait l'original.

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
import ast
import base64
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


def borne_du_module() -> int:
    """`BORNE_MINIATURE_OCTETS` lue par `ast`, sans importer le module.

    **PAR `ast` ET NON PAR `import`** : `app.media.photo` importe SQLAlchemy, que
    ce script n'a pas -- il est invoque par `python3` hors environnement virtuel.
    C'est exactement le piege mesure en `T1` du LOT 3 sur `verifier-images.py`
    (§7.27), et la parade est la meme.

    Et c'est ce qui evite de RECOPIER 100 000 ici : une seconde copie du seuil
    divergerait de celle du module au premier changement.
    """
    source = (RACINE / "apps" / "api" / "app" / "media" / "photo.py").read_text(encoding="utf-8")
    for noeud in ast.walk(ast.parse(source)):
        cible = getattr(noeud, "target", None)
        if (
            isinstance(noeud, ast.AnnAssign)
            and isinstance(cible, ast.Name)
            and cible.id == "BORNE_MINIATURE_OCTETS"
            and isinstance(noeud.value, ast.Constant)
        ):
            return int(noeud.value.value)
    message = "BORNE_MINIATURE_OCTETS introuvable dans app/media/photo.py"
    raise SystemExit(message)


BORNE_MINIATURE_OCTETS = borne_du_module()

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_TROMBINOSCOPE = "/api/v1/entities/{code}/people"
CHEMIN_PROFIL = "/api/v1/entities/{code}/people/{appartenance}"
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"
CHEMIN_PHOTO = "/api/v1/entities/{code}/people/{appartenance}/photo"

#  **DEUX CONTENUS DISTINCTS, ET C'EST CE QUI REND LE CRITERE MESURABLE.** Servir
#  l'original au lieu de la miniature donnerait un 200 et des octets dans les
#  deux cas : seule la comparaison du CONTENU discrimine.
OCTETS_MINIATURE = b"MINIATURE-DE-VERIFICATION-" + b"m" * 74
OCTETS_ORIGINAL = b"ORIGINAL-QUI-NE-DOIT-JAMAIS-SORTIR-" + b"o" * 4000

MARQUEUR = f"t4l5-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l5t4-egalite-des-refus"

#  Les DIX-SEPT champs de la fiche : les treize du §10.2, plus les deux
#  identifiants, la categorie professionnelle et les deux listes. **Declares et
#  confrontes a la reponse servie** : un champ ajoute sans etre voulu fait
#  echouer -- et c'est ce qui s'est produit a `T5`, ou `photo` est arrivee.
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
        "photo",
    }
)

#  Les profils que la liste doit rendre. **`Retiree` EST listable** : son
#  appartenance est active et son profil publie ; seule son AUTORISATION de photo
#  est retiree. `Parti` en est exclu par son etat d'appartenance.
PROFILS_LISTABLES = frozenset({"Complete", "Retiree"})

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
    cle_miniature: str,
    cle_originale: str,
) -> str:
    """Une entite, un admin local, un profil COMPLET, un profil EXCLU.

    S608 : les seules valeurs interpolees sont `MARQUEUR`, un `uuid4` de ce
    module, et le code d'entite qui en derive. `psql` n'accepte pas de parametre
    lie dans un bloc `DO`.

    **LE PROFIL COMPLET PORTE LES SIX CHAMPS SENSIBLES**, sans quoi l'epreuve
    d'absence de masquage ne prouverait rien : un champ nul est indistinguable
    d'un champ masque.
    """
    #  **LES DEUX TAILLES SONT DERIVEES DE LA BORNE DU MODULE**, jamais ecrites :
    #  la miniature juste sous, l'original vingt fois au-dessus. Si la borne
    #  changeait, ce decor suivrait.
    taille_miniature = BORNE_MINIATURE_OCTETS - 1
    taille_originale = BORNE_MINIATURE_OCTETS * 20
    return f"""
    DO $$
    DECLARE p uuid; e uuid; c uuid; m uuid; cl uuid; jc uuid; ci uuid; d uuid; dm uuid;
            ma uuid;
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

      -- LA PHOTO du profil complet : l'actif, sa MINIATURE, son ORIGINAL, et
      -- une autorisation ACTIVE. Les deux cles d'objet sont distinctes et
      -- deversees dans MinIO par l'appelant.
      INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type,
        original_filename, object_key, mime_declared, size_bytes, checksum_sha256, ready_at)
      VALUES (e, d, 'ready', 'image', 'photo.jpg', '{cle_originale}', 'image/jpeg',
              {taille_originale}, repeat('a', 64), now() - INTERVAL '1 day')
      RETURNING id INTO ma;
      INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, height,
        variant_format, size_bytes, checksum_sha256, object_key)
      VALUES (e, ma, 'thumbnail', 200, 200, 'jpeg', {taille_miniature}, repeat('b', 64),
              '{cle_miniature}');
      INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, source)
      VALUES (d, ma, now() - INTERVAL '1 day', 'self_service');

      -- Un profil EXCLU de la liste : appartenance partie, profil RESTE publie.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-parti@x.test', '{marqueur}-parti@x.test', 'Ivan', 'Parti', 'active')
      RETURNING id INTO d;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date,
        membership_state, professional_category, profile_visibility)
      VALUES (d, e, DATE '2026-01-15', DATE '2026-06-01', 'departed', 'consultant', 'published')
      RETURNING id INTO m;

      -- **ET UN QUATRIEME PROFIL : PHOTO DEPOSEE, AUTORISATION RETIREE.** Sans
      -- lui, « pas de photo » et « autorisation retiree » seraient
      -- indistinguables : le premier n'a rien en base, le second a tout SAUF le
      -- droit. C'est le temoin qui prouve que le filtre porte sur le retrait.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-retire@x.test', '{marqueur}-retire@x.test', 'Rosa', 'Retiree',
              'active') RETURNING id INTO d;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date, membership_state,
        professional_category, profile_visibility)
      VALUES (d, e, DATE '2026-02-01', 'active', 'consultant', 'published') RETURNING id INTO m;
      INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type,
        original_filename, object_key, mime_declared, size_bytes, checksum_sha256, ready_at)
      VALUES (e, d, 'ready', 'image', 'photo.jpg', '{marqueur}/retire-original', 'image/jpeg',
              123456, repeat('c', 64), now() - INTERVAL '1 day') RETURNING id INTO ma;
      INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, height,
        variant_format, size_bytes, checksum_sha256, object_key)
      VALUES (e, ma, 'thumbnail', 200, 200, 'jpeg', 4096, repeat('d', 64),
              '{marqueur}/retire-thumb');
      INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, withdrawn_at,
        source) VALUES (d, ma, now() - INTERVAL '2 days', now() - INTERVAL '1 day',
                        'self_service');
    END $$;
    """  # noqa: S608


def mc(compose: list[str], commande: str) -> tuple[int, str]:
    """Une commande `mc` DANS le conteneur MinIO.

    **`mc` ET NON `boto3`** : le controle de stack ne doit rien exiger de
    l'environnement Python de la machine, et `mc` est deja l'outil que
    `make minio-bucket` emploie. L'alias vise la boucle locale du conteneur.
    """
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


def deverser(compose: list[str], bucket: str, cle: str, octets: bytes) -> tuple[int, str]:
    """Deverser des octets dans MinIO, sans fichier temporaire sur l'hote.

    Le contenu passe par `base64`, present dans l'image MinIO -- contrairement a
    `grep`, absent, et c'est la lecon du §7.10. Verifie avant emploi.
    """
    encode = base64.b64encode(octets).decode("ascii")
    return mc(compose, f"echo '{encode}' | base64 -d | mc pipe local/{bucket}/{cle}")


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
        f"DELETE FROM photo_authorization WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM media_variant WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM media_asset WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
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
    bucket = env["MINIO_BUCKET"]
    cle_miniature = f"{MARQUEUR}/miniature.jpg"
    cle_originale = f"{MARQUEUR}/originale.jpg"

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
            cle_miniature,
            cle_originale,
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
        #  **LES DEUX PROFILS LISTABLES, ET LE PARTI ABSENT.** `Retiree` est
        #  listable -- appartenance active, profil publie -- et sa photo n'est
        #  PAS servable : c'est le temoin qui separe « hors de la liste » de
        #  « sans photo », deux causes qu'un decor a un seul profil confondrait.
        if set(rendus) == PROFILS_LISTABLES:
            print(
                f"    ok       la liste rend EXACTEMENT les {len(PROFILS_LISTABLES)} profils "
                "listables — le parti en est absent"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    la liste rend {sorted(rendus)}, {sorted(PROFILS_LISTABLES)} attendu"
            )
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
        # ==================================================================
        #  T5 — LA MINIATURE : le chemin, les OCTETS, et jamais l'original
        # ==================================================================

        # --- 11. les deux objets sont deverses dans MinIO ---------------------
        controles += 1
        code_mc, sortie_mc = deverser(compose, bucket, cle_miniature, OCTETS_MINIATURE)
        code_mc2, sortie_mc2 = deverser(compose, bucket, cle_originale, OCTETS_ORIGINAL)
        if code_mc or code_mc2:
            echecs += 1
            print(f"    ECHEC    depot MinIO : {sortie_mc[:120]} | {sortie_mc2[:120]}")
            return 1
        print(
            f"    ok       MinIO : miniature {len(OCTETS_MINIATURE)} o, "
            f"original {len(OCTETS_ORIGINAL)} o — contenus DISTINCTS"
        )

        # --- 12. la LISTE annonce le chemin de photo, et AUCUNE cle d'objet ----
        controles += 1
        liste_reponse = appeler(arguments.base, liste, contexte, en_tetes=biscuit)
        corps_liste = liste_reponse.json()
        lignes_photo = (
            corps_liste.get("collaborateurs", []) if isinstance(corps_liste, dict) else []
        )
        par_nom = {ligne["last_name"]: ligne for ligne in lignes_photo}
        chemin_attendu = CHEMIN_PHOTO.format(code=code_entite, appartenance=appartenance)
        brut_liste = liste_reponse.corps.decode("utf-8", "replace")
        annonce_juste = par_nom.get("Complete", {}).get("photo") == chemin_attendu
        retiree_nulle = par_nom.get("Retiree", {}).get("photo") is None
        sans_cle = cle_miniature not in brut_liste and cle_originale not in brut_liste
        if annonce_juste and retiree_nulle and sans_cle:
            print(
                "    ok       la LISTE annonce le chemin pour le profil autorise, `null` "
                "pour l'autorisation RETIREE, et AUCUNE cle d'objet"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    liste : chemin {annonce_juste}, retiree nulle {retiree_nulle}, "
                f"sans cle {sans_cle}"
            )

        # --- 13. la FICHE annonce le MEME chemin ------------------------------
        controles += 1
        if fiche.get("photo") == chemin_attendu:
            print("    ok       la FICHE annonce le MEME chemin que la liste — une source")
        else:
            echecs += 1
            print(f"    ECHEC    fiche.photo = {fiche.get('photo')!r}, {chemin_attendu!r} attendu")

        # --- 14. LE CONTROLE CENTRAL : les octets sont ceux de la MINIATURE ----
        controles += 1
        image = appeler(arguments.base, chemin_attendu, contexte, en_tetes=biscuit)
        type_juste = image.en_tetes.get("content-type", "").startswith("image/jpeg")
        if (
            image.statut == 200
            and image.corps == OCTETS_MINIATURE
            and image.corps != OCTETS_ORIGINAL
            and type_juste
        ):
            print(
                f"    ok       les octets servis sont EXACTEMENT ceux de la miniature "
                f"({len(image.corps)} o < {BORNE_MINIATURE_OCTETS}), type "
                f"{image.en_tetes.get('content-type')}"
            )
        else:
            echecs += 1
            debut_recu = image.corps[:40]
            print(
                f"    ECHEC    photo : {image.statut}, {len(image.corps)} o, "
                f"debut {debut_recu!r}, type {image.en_tetes.get('content-type')!r}"
            )

        # --- 15. l'ORIGINAL n'est joignable par AUCUN chemin de l'API ----------
        controles += 1
        #  **L'ORIGINAL EST DANS LE BUCKET**, prouve au controle 11 : le seul
        #  point ouvert est de savoir si l'API le sert. Deux tentatives, et
        #  aucune ne doit rendre ses octets.
        tentatives = [
            f"/api/v1/entities/{code_entite}/media/{cle_originale}",
            f"{chemin_attendu}?variante=original",
        ]
        fuites = []
        for tentative in tentatives:
            essai = appeler(arguments.base, tentative, contexte, en_tetes=biscuit)
            if essai.corps == OCTETS_ORIGINAL:
                fuites.append(tentative)
        if not fuites:
            print(
                f"    ok       l'original ({len(OCTETS_ORIGINAL)} o) n'est rendu par aucune "
                f"des {len(tentatives)} tentatives — dont un parametre `?variante=original`"
            )
        else:
            echecs += 1
            print(f"    ECHEC    l'original a fuite par : {fuites}")

        # --- 16. l'autorisation RETIREE rend 404, comme un profil sans photo ---
        controles += 1
        code_sql, brut = psql(
            compose,
            env,
            "SELECT em.id FROM entity_membership em JOIN person p ON p.id = em.person_id "  # noqa: S608
            f"WHERE p.email_normalized = '{MARQUEUR}-retire@x.test'",
        )
        retiree = valeur(brut)
        if code_sql or not retiree:
            echecs += 1
            print(f"    ECHEC    identifiant du profil a autorisation retiree : {brut[:120]}")
        else:
            refus_photo = appeler(
                arguments.base,
                CHEMIN_PHOTO.format(code=code_entite, appartenance=retiree),
                contexte,
                en_tetes={**biscuit, "X-Request-ID": CORRELATION_FIXE},
            )
            corps_refus = refus_photo.json()
            forme = corps_refus.get("erreur", {}) if isinstance(corps_refus, dict) else {}
            if refus_photo.statut == 404 and forme.get("code") == "entite_introuvable":
                print(
                    "    ok       autorisation RETIREE : 404 au format du §18.3 — le §12.2 "
                    "exige une autorisation ACTIVE, et l'appelant sert l'avatar neutre"
                )
            else:
                echecs += 1
                print(f"    ECHEC    retrait : {refus_photo.statut}, {str(corps_refus)[:110]}")

        # --- 17. sans session, la photo refuse --------------------------------
        controles += 1
        photo_anonyme = appeler(arguments.base, chemin_attendu, contexte)
        if photo_anonyme.statut == 401 and photo_anonyme.corps != OCTETS_MINIATURE:
            print("    ok       sans session : 401, et AUCUN octet — la matrice §5 refuse `ANON`")
        else:
            echecs += 1
            print(
                f"    ECHEC    photo sans session : {photo_anonyme.statut}, "
                f"{len(photo_anonyme.corps)} o"
            )
    finally:
        mc(compose, f"mc rm --force local/{bucket}/{cle_miniature} >/dev/null 2>&1 || true")
        mc(compose, f"mc rm --force local/{bucket}/{cle_originale} >/dev/null 2>&1 || true")
        nettoyer(compose, env, MARQUEUR, debut)

    print()
    print(f"    controles executes : {controles}   echecs : {echecs}")
    if echecs:
        return 1
    print(
        "  --> la fiche profil sert les champs du §10.2, n'en masque aucun, suit "
        "exactement la population du trombinoscope, et sert la MINIATURE — jamais "
        "l'originale"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
