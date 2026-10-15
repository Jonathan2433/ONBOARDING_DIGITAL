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
#  La MEME adresse que la fiche : le `GET` la lit, le `PATCH` de `T7` l'ecrit.
CHEMIN_ECRITURE = CHEMIN_PROFIL
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"
CHEMIN_SESSION = "/api/v1/auth/session"
EN_TETE_JETON = "X-CSRF-Token"
CHEMIN_PHOTO = "/api/v1/entities/{code}/people/{appartenance}/photo"
#  Les trois chemins de `T8`.
CHEMIN_ARCHIVAGE = "/api/v1/entities/{code}/people/{appartenance}/archivage"
CHEMIN_RESTAURATION = "/api/v1/entities/{code}/people/{appartenance}/restauration"
CHEMIN_FICHE_ARCHIVEE = "/api/v1/entities/{code}/people/{appartenance}/fiche-archivee"
#  Le chemin de `T9`.
CHEMIN_HISTORIQUE = "/api/v1/entities/{code}/people/{appartenance}/historique"

#  **AUCUN CONTROLE DE STACK SUR LA PAGE DE PROFIL, ET C'EST MESURE** — `T11`.
#
#  J'en avais ecrit un : la page servie en `text/html` avec le point de montage,
#  sur l'identifiant reel rendu par la liste. **Il ne pouvait pas echouer.** Le
#  repli SPA du `Caddyfile` sert `index.html` pour TOUT chemin, mesure le
#  12/09/2026 :
#
#      /entites/BORDEA00/trombinoscope/<uuid reel>   200 text/html racine=1
#      /entites/BORDEA00/trombinoscope/bidon         200 text/html racine=1
#      /chemin/qui/n/existe/pas/du/tout              200 text/html racine=1
#
#  L'echec aurait produit la MEME observation que le succes -- §7.0, quatrieme
#  proposition -- et le repli lui-meme est deja prouve par `make ecrans-check`.
#  Le supprimer vaut mieux que de le garder : un controle qui ne discrimine pas
#  apprend a lire « ok » sans le lire.
#
#  Ce que le rendu de cette page a de prouve est ailleurs : **156 tests `jsdom`**
#  cote `apps/web`. Une preuve dans un vrai navigateur demande un moteur de
#  rendu, que le cahier §17.1 nomme — Playwright — et que le **LOT 12** possede ;
#  `make cadre-check` porte deja la meme reserve pour la mesure aux cinq largeurs.

#  **DEUX CONTENUS DISTINCTS, ET C'EST CE QUI REND LE CRITERE MESURABLE.** Servir
#  l'original au lieu de la miniature donnerait un 200 et des octets dans les
#  deux cas : seule la comparaison du CONTENU discrimine.
OCTETS_MINIATURE = b"MINIATURE-DE-VERIFICATION-" + b"m" * 74
OCTETS_ORIGINAL = b"ORIGINAL-QUI-NE-DOIT-JAMAIS-SORTIR-" + b"o" * 4000

MARQUEUR = f"t4l5-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l5t4-egalite-des-refus"

#  Les DIX-HUIT champs de la fiche : les treize du §10.2, plus les deux
#  identifiants, la categorie professionnelle, les deux listes -- et `version`
#  depuis `T11`. **Declares et confrontes a la reponse servie** : un champ ajoute
#  sans etre voulu fait echouer -- et c'est ce qui s'est produit a `T5`, ou
#  `photo` est arrivee, puis a `T11` avec `version`, que le §18.4 exige dans le
#  corps des ecritures et qu'aucune lecture ne servait.
CHAMPS_FICHE = frozenset(
    {
        "id",
        "version",
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
    charge: dict[str, object] | None = None,
    en_tetes: dict[str, str] | None = None,
    methode: str | None = None,
) -> Reponse:
    """Un aller-retour HTTP. `methode` n'est explicite que pour `PATCH`.

    **`T7` DU LOT 5 A AJOUTE `methode`, ET SANS ELLE LE CONTROLE ETAIT MUET.**
    La deduction « charge => POST, sinon GET » couvrait les six routes des lots
    precedents ; la premiere ecriture METIER est un `PATCH`, et l'envoyer en
    `POST` aurait rendu **405** -- un refus, donc un test de refus vert pour la
    mauvaise raison. C'est le defaut `T2-3` en puissance.
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
    adresse_dsm: str,
    adresse_esm: str,
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
            ma uuid; es uuid; jp uuid; ci2 uuid;
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
      -- **UN SECOND CERCLE, SANS JETON DE COULEUR** — `color_token` est NULLABLE
      -- au catalogue. Il est le CAS du couple que le controle 6 bis mesure ; le
      -- premier, qui en porte un, en est le TEMOIN. Defaut `T10-8` : la fiche et
      -- la liste faisaient `str(color_token)`, donc `str(None)`, donc la chaine
      -- « None » -- un jeton d'apparence plausible qu'aucun ecran ne reconnait.
      INSERT INTO circle (entity_id, code, name, color_token, display_order)
      VALUES (e, '{marqueur}-cercle-2', 'Cercle sans couleur', NULL, 1) RETURNING id INTO ci2;
      INSERT INTO job_catalog (entity_id, code, label, display_order, active)
      VALUES (e, '{marqueur}-job', 'Ingenieure logicielle', 0, TRUE) RETURNING id INTO jc;
      INSERT INTO client (canonical_name, display_name, status)
      VALUES ('{marqueur}-client', 'Client Alpha', 'active') RETURNING id INTO cl;
      INSERT INTO entity_client (entity_id, client_id) VALUES (e, cl);

      -- Le DSM, sa responsabilite AVANT son affectation : la base l'exige.
      --
      -- **IL EST CONNECTABLE DEPUIS `T7`, ET SON ADRESSE EST SUR LE DOMAINE
      -- AUTORISE.** Elle etait en `@x.test`, qui ne peut pas se connecter :
      -- `ALLOWED_EMAIL_DOMAINS` filtre. Le motif de menage est `{{marqueur}}%`,
      -- donc insensible au domaine -- verifie avant de changer.
      --
      -- **L'APPELANT SANS ROLE N'EST PAS TOUCHE, ET C'EST LE POINT.** Le
      -- controle 5 prouve qu'AUCUN champ n'est masque a quelqu'un qui n'a « ni
      -- appartenance, ni responsabilite, ni role technique » -- `ECART-051`.
      -- Donner un role a cette personne-la aurait detruit ce temoin. `T7`
      -- ajoute donc un SECOND compte connectable au lieu d'en modifier un.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_dsm}', '{adresse_dsm}', 'Dominique', 'Lesmanager',
              'active') RETURNING id INTO dm;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (dm, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{algo}', '{parametres_hachage}'::jsonb, now(), FALSE);
      -- **SON APPARTENANCE EST NECESSAIRE, ET LE GARDE-FOU L'A DIT.** Sans
      -- elle, il n'a AUCUNE entite principale, et le §5.1 ne lui laisse que
      -- `EMP` : les cinq epreuves d'ecriture rendaient `acces_refuse`. Le refus
      -- etait JUSTE, c'est le decor qui etait incomplet -- et c'est exactement
      -- le genre de constat que seul un controle A TRAVERS L'API produit.
      --
      -- **`profile_visibility` A `draft`, ET C'EST DELIBERE** : le controle 2
      -- exige que la liste rende EXACTEMENT deux profils. Un DSM `published`
      -- en ferait trois et casserait un temoin de `T2`. `draft` lui donne son
      -- entite principale sans le faire entrer dans le trombinoscope.
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (dm, e, DATE '2025-01-01', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at, ends_at)
      VALUES (dm, e, 'DSM', dm, now() - INTERVAL '30 days', NULL);

      -- **UN TROISIEME COMPTE CONNECTABLE, POSE PAR `T8` : L'ESM.**
      --
      -- Le §6.1 reserve « Archiver un profil » a l'ESM, a l'administrateur
      -- d'entite et au super-administrateur -- `DSM` et `BOOST` sont A TIRET,
      -- alors que les deux peuvent MODIFIER. Aucun des deux comptes existants
      -- ne porte ce droit, et en donner un a l'un d'eux aurait detruit un
      -- temoin : celui de l'appelant sans role (controle 5, `ECART-051`) ou
      -- celui du DSM refuse hors de son perimetre (controle 20).
      --
      -- **AJOUTER PLUTOT QUE MODIFIER**, exactement comme `T7` l'a fait pour le
      -- DSM. Et `profile_visibility` a `draft` pour le meme motif : le controle
      -- 2 exige que la liste rende EXACTEMENT deux profils.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse_esm}', '{adresse_esm}', 'Esmeralda', 'Lentite',
              'active') RETURNING id INTO es;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (es, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{algo}', '{parametres_hachage}'::jsonb, now(), FALSE);
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (es, e, DATE '2025-01-01', 'active', 'consultant', 'draft');
      INSERT INTO framework_responsibility_assignment
        (person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at, ends_at)
      VALUES (es, e, 'ESM', es, now() - INTERVAL '30 days', NULL);

      -- Le profil COMPLET, avec ses six champs sensibles.
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{marqueur}-complete@x.test', '{marqueur}-complete@x.test', 'Ada', 'Complete',
              'active') RETURNING id INTO d;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date, membership_state,
        professional_category, profile_visibility, short_bio, fun_fact)
      VALUES (d, e, DATE '2026-01-15', 'active', 'consultant', 'published',
              'Ingenieure passionnee.', 'Joue du theorbe.') RETURNING id INTO m;
      -- **UN METIER PASSE, CLOS, POSE PAR `T9`.** Sans lui le decor n'a AUCUNE
      -- periode close avant l'archivage de `T8`, et « l'historique rend le
      -- PASSE » ne serait prouve par rien : toutes les periodes seraient
      -- ouvertes, ce qu'une requete sans historique rendrait aussi.
      INSERT INTO job_catalog (entity_id, code, label, display_order, active)
      VALUES (e, '{marqueur}-job-ancien', 'Developpeuse', 1, TRUE) RETURNING id INTO jp;
      INSERT INTO membership_job_assignment (entity_id, entity_membership_id, job_catalog_id,
        starts_at, ends_at)
      VALUES (e, m, jp, now() - INTERVAL '400 days', now() - INTERVAL '30 days');
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
      -- Le §8.2 autorise plusieurs cercles SECONDAIRES : celui-ci est legitime.
      INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id,
        membership_type, starts_at, ends_at)
      VALUES (e, m, ci2, 'secondary', now() - INTERVAL '30 days', NULL);
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
        #  LOT 10, `T2` : `audit_event.actor_person_id` reference aussi `person`.
        f"DELETE FROM audit_event WHERE actor_person_id IN (SELECT id FROM person WHERE email_normalized LIKE '{motif}')",  # noqa: S608,E501
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
        #  LOT 10, `T3` : `audit_event.entity_id` reference aussi `entity`.
        f"DELETE FROM audit_event WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE '{motif}')",  # noqa: S608,E501
        f"DELETE FROM entity WHERE code LIKE '{motif}'",  # noqa: S608
        "DELETE FROM auth_event WHERE person_id IS NULL AND service_account_id IS NULL "  # noqa: S608
        f"AND created_at >= '{debut}'",
        "DELETE FROM audit_event WHERE actor_person_id IS NULL "  # noqa: S608
        f"AND actor_service_account_id IS NULL AND occurred_at >= '{debut}'",
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
    #  Le DSM est un SECOND compte connectable, sur le meme domaine autorise.
    adresse_dsm = f"{MARQUEUR}-dsm@{domaine}"
    #  Le TROISIEME compte connectable, pose par `T8` : le seul a porter un droit
    #  d'archivage. Meme domaine autorise, meme motif de menage `{marqueur}%`.
    adresse_esm = f"{MARQUEUR}-esm@{domaine}"
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
    print("  Fiche profil, ecriture, cycle de vie et historique — US004, US006, US007, US008")
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
            adresse_dsm,
            adresse_esm,
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
    print(
        "    ok       decor : un profil COMPLET, un profil EXCLU, + un admin local, "
        "un DSM et un ESM"
    )

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

        # ---  3. LES QUATRE CHAMPS DU VERSO SONT RENSEIGNES — LOT 5, `T10` ----
        #
        #  **UN CONTROLE DE PRESENCE NE SUFFIRAIT PAS.** `trombinoscope-check`
        #  verifie que la ligne porte douze champs « ni plus ni moins » ; il
        #  passerait avec les quatre a `null`, ce qui est exactement ce que
        #  rendrait une requete d'enrichissement qui ne joindrait rien. C'est le
        #  §7.0 quatrieme proposition : l'echec produirait la meme observation que
        #  le succes.
        #
        #  Le decor donne a « Ada Complete » un metier, une mission avec client et
        #  un cercle principal : les quatre doivent donc etre RENSEIGNES, et le
        #  cercle porter ses trois sous-champs.
        controles += 1
        ligne_complete = next(
            (ligne for ligne in lignes if ligne.get("last_name") == "Complete"), {}
        )
        cercle_rendu = ligne_complete.get("cercle") or {}
        verso_renseigne = [
            champ
            for champ in ("metier", "statut", "client")
            if ligne_complete.get(champ) not in (None, "")
        ]
        if len(verso_renseigne) == 3 and set(cercle_rendu) == {"code", "nom", "jeton_de_couleur"}:
            print(
                "    ok       les 4 champs du VERSO sont RENSEIGNES — "
                f"metier « {ligne_complete['metier']} », statut « {ligne_complete['statut']} », "
                f"client « {ligne_complete['client']} », cercle « {cercle_rendu['nom']} » : "
                "§10.1, « le verso presente les informations professionnelles principales »"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    verso : renseignes {verso_renseigne}, "
                f"cercle {sorted(cercle_rendu) or 'absent'}"
            )

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

        # --- 6 bis. le JETON de couleur : un pose, un ABSENT -------------------
        #
        #  **LE COUPLE, ET AUCUNE DES DEUX MOITIES NE SUFFIT.** Le cercle
        #  principal porte « bleu », le secondaire n'a AUCUN jeton : les deux
        #  lignes ne different que par la colonne en cause. Sans le temoin, un
        #  code qui ne rendrait jamais de jeton passerait ; sans le cas,
        #  `str(None)` -- la chaine « None » du defaut `T10-8` -- resterait
        #  invisible, comme elle l'a ete sur 100 % des cercles du jeu de donnees.
        controles += 1
        secondaires = fiche.get("cercles_secondaires") or []
        sans_couleur = next(
            (c_ for c_ in secondaires if c_.get("nom") == "Cercle sans couleur"), {}
        )
        jetons_justes = (
            principal.get("jeton_de_couleur") == "bleu"
            and sans_couleur.get("nom") == "Cercle sans couleur"
            and "jeton_de_couleur" in sans_couleur
            and sans_couleur["jeton_de_couleur"] is None
        )
        #  **ET LA CHAINE EST CHERCHEE DANS LES OCTETS SERVIS**, pas dans l'objet
        #  decode : c'est la forme exacte que le defaut produisait sur le reseau.
        aucune_chaine_none = b'"None"' not in fiche_reponse.corps
        if jetons_justes and aucune_chaine_none:
            print(
                "    ok       jeton de couleur : « bleu » sur le principal, `null` sur le "
                "secondaire sans couleur — et la chaine « None » est ABSENTE des octets"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    jetons : principal {principal.get('jeton_de_couleur')!r}, "
                f"secondaire sans couleur {sans_couleur!r}, "
                f"chaine « None » absente : {aucune_chaine_none}"
            )

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

        # ==================================================================
        #  LOT 5, `T7` — L'ECRITURE DANS SON PERIMETRE, story `MVP-L05-US006`
        #
        #  **LE DECOR DE `T4` DONNE LE COUPLE APPARIE POUR RIEN**, et c'est
        #  pourquoi `T7` etend ce verificateur plutot que d'en ecrire un second
        #  (§7.27, comme `T5`) : « Ada Complete » est RATTACHEE au DSM, « Rosa
        #  Retiree » est active et NE L'EST PAS. Le refus et son temoin ne
        #  different donc que par le rattachement -- ce qu'un `WHERE` trop large
        #  ou trop etroit rendrait visible.
        # ==================================================================

        # --- 18. TEMOIN : le DSM se connecte et obtient son jeton CSRF --------
        controles += 1
        connexion_dsm = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse_dsm, "mot_de_passe": mot_de_passe},
        )
        jeton_dsm = ""
        for pose in connexion_dsm.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                jeton_dsm = pose.split("=", 1)[1].split(";", 1)[0]
        biscuit_dsm = {"Cookie": f"{nom_cookie}={jeton_dsm}"}
        session_dsm = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=biscuit_dsm)
        corps_session = session_dsm.json()
        csrf = corps_session.get("jeton_csrf", "") if isinstance(corps_session, dict) else ""
        if connexion_dsm.statut == 200 and jeton_dsm and csrf:
            print("    ok       TEMOIN : le DSM se connecte, et `GET /auth/session` rend son jeton")
        else:
            echecs += 1
            print(
                f"    ECHEC    connexion du DSM : {connexion_dsm.statut}, "
                f"cookie {'oui' if jeton_dsm else 'NON'}, jeton {'oui' if csrf else 'NON'}"
            )
        ecriture_dsm = {**biscuit_dsm, EN_TETE_JETON: csrf, "Origin": arguments.base}

        def periodes_de_metier(cible: str) -> list[str]:
            _, brut = psql(
                compose,
                env,
                "SELECT ends_at IS NULL FROM membership_job_assignment "  # noqa: S608
                f"WHERE entity_membership_id = '{cible}' ORDER BY starts_at",
            )
            return [ligne.strip() for ligne in brut.splitlines() if ligne.strip()]

        # --- 19. LE CRITERE : un DSM modifie SON consultant -------------------
        controles += 1
        avant = periodes_de_metier(appartenance)
        _, brut_metier = psql(
            compose,
            env,
            "SELECT id FROM job_catalog WHERE entity_id IN "  # noqa: S608
            f"(SELECT id FROM entity WHERE code = '{code_entite}') "
            f"AND code = '{MARQUEUR}-job'",
        )
        metier = valeur(brut_metier)
        _, brut_version = psql(
            compose,
            env,
            f"SELECT version FROM entity_membership WHERE id = '{appartenance}'",  # noqa: S608
        )
        version = int(valeur(brut_version) or 0)
        #  Le metier CHANGE : on repose le meme catalogue apres avoir CLOS la
        #  periode courante par une premiere ecriture. Plus simple et plus
        #  discriminant : on modifie la DATE D'ARRIVEE, qui est une colonne, puis
        #  on verifie que la version a monte -- et on modifie le METIER pour
        #  verifier la cloture-reouverture.
        ecrit = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": version, "date_d_arrivee": "2026-03-01"},
            en_tetes=ecriture_dsm,
            methode="PATCH",
        )
        corps_ecrit = ecrit.json()
        modifies = corps_ecrit.get("champs_modifies") if isinstance(corps_ecrit, dict) else None
        if ecrit.statut == 200 and modifies == ["date_d_arrivee"]:
            print(
                "    ok       LE CRITERE : un DSM modifie SON consultant — 200, et la reponse "
                "nomme le champ ecrit"
            )
        else:
            echecs += 1
            print(f"    ECHEC    ecriture du DSM : {ecrit.statut}, {str(corps_ecrit)[:160]}")

        # --- 20. LE REFUS APPARIE : le MEME DSM sur un consultant NON rattache -
        controles += 1
        refus_autre = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=retiree),
            contexte,
            charge={"version": 1, "date_d_arrivee": "2026-03-01"},
            en_tetes=ecriture_dsm,
            methode="PATCH",
        )
        corps_autre = refus_autre.json()
        code_autre = (
            corps_autre.get("erreur", {}).get("code") if isinstance(corps_autre, dict) else None
        )
        if refus_autre.statut == 403 and code_autre == "champ_hors_perimetre":
            print(
                "    ok       le MEME DSM est REFUSE sur un consultant non rattache — 403 "
                "`champ_hors_perimetre` (§6.2)"
            )
        else:
            echecs += 1
            print(f"    ECHEC    refus attendu : {refus_autre.statut}, {str(corps_autre)[:140]}")

        # --- 21. AUCUN ROLE D'ECRITURE : le garde-fou de role refuse ----------
        controles += 1
        session_sans_role = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=biscuit)
        corps_ssr = session_sans_role.json()
        csrf_sans_role = corps_ssr.get("jeton_csrf", "") if isinstance(corps_ssr, dict) else ""
        refus_role = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": 1, "date_d_arrivee": "2026-03-01"},
            en_tetes={**biscuit, EN_TETE_JETON: csrf_sans_role, "Origin": arguments.base},
            methode="PATCH",
        )
        corps_role = refus_role.json()
        code_role = (
            corps_role.get("erreur", {}).get("code") if isinstance(corps_role, dict) else None
        )
        if refus_role.statut == 403 and code_role == "acces_refuse":
            print(
                "    ok       sans role d'ecriture : 403 `acces_refuse` — c'est le cas d'`OFFICE`, "
                "dont la colonne du §6.1 est ENTIEREMENT a tiret"
            )
        else:
            echecs += 1
            print(f"    ECHEC    refus de role : {refus_role.statut}, {str(corps_role)[:140]}")

        # --- 22. sans session, l'ecriture refuse ------------------------------
        controles += 1
        anonyme = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": 1, "date_d_arrivee": "2026-03-01"},
            en_tetes={"Origin": arguments.base},
            methode="PATCH",
        )
        if anonyme.statut == 401:
            print("    ok       sans session : 401 — aucune ecriture n'est ouverte a `ANON`")
        else:
            echecs += 1
            print(f"    ECHEC    ecriture anonyme : {anonyme.statut}")

        # --- 23. sans jeton CSRF, l'ecriture refuse ---------------------------
        controles += 1
        sans_csrf = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": 1, "date_d_arrivee": "2026-03-01"},
            en_tetes={**biscuit_dsm, "Origin": arguments.base},
            methode="PATCH",
        )
        corps_csrf = sans_csrf.json()
        code_csrf = (
            corps_csrf.get("erreur", {}).get("code") if isinstance(corps_csrf, dict) else None
        )
        if sans_csrf.statut == 403 and code_csrf == "requete_refusee":
            print(
                "    ok       sans jeton CSRF : 403 `requete_refusee` — PREMIER emploi de la "
                "protection sur une route METIER, et la regle n'a pas ete recopiee"
            )
        else:
            echecs += 1
            print(f"    ECHEC    CSRF : {sans_csrf.statut}, {str(corps_csrf)[:140]}")

        # --- 24. une version OBSOLETE rend 409, et rien n'est ecrit -----------
        controles += 1
        etat_avant = periodes_de_metier(appartenance)
        obsolete = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": 1, "metier": metier},
            en_tetes=ecriture_dsm,
            methode="PATCH",
        )
        corps_obs = obsolete.json()
        code_obs = corps_obs.get("erreur", {}).get("code") if isinstance(corps_obs, dict) else None
        if (
            obsolete.statut == 409
            and code_obs == "version_obsolete"
            and periodes_de_metier(appartenance) == etat_avant
        ):
            print(
                "    ok       version OBSOLETE : 409 `version_obsolete`, et l'historique est "
                "INCHANGE — §18.4, « sans ecrasement silencieux »"
            )
        else:
            echecs += 1
            print(f"    ECHEC    version obsolete : {obsolete.statut}, {str(corps_obs)[:140]}")

        # --- 25. un champ INCONNU est refuse, jamais ignore -------------------
        controles += 1
        inconnu = appeler(
            arguments.base,
            CHEMIN_ECRITURE.format(code=code_entite, appartenance=appartenance),
            contexte,
            charge={"version": 2, "presentation_courte": "hors perimetre"},
            en_tetes=ecriture_dsm,
            methode="PATCH",
        )
        if inconnu.statut == 422:
            print(
                "    ok       champ INCONNU : 422 — `presentation_courte` est une AUTRE ligne du "
                "§6.1, et l'ignorer ferait croire la modification prise"
            )
        else:
            echecs += 1
            print(f"    ECHEC    champ inconnu : {inconnu.statut}, {str(inconnu.json())[:140]}")

        #  **ET LE TEMOIN QUI REND LE COUPLE NON TRIVIAL, EN BASE** : `avant` a
        #  ete releve avant toute ecriture, et le metier n'a PAS ete modifie ici
        #  -- le controle 24 l'a refuse sur une version obsolete. L'historique du
        #  metier doit donc etre strictement identique.
        controles += 1
        if periodes_de_metier(appartenance) == avant:
            print(
                "    ok       l'historique du metier est INTACT apres deux refus — aucune "
                "periode fantome n'a ete ouverte"
            )
        else:
            echecs += 1
            print("    ECHEC    l'historique du metier a bouge alors que tout a ete refuse")

        # ==================================================================
        #  LOT 5, `T8` — ARCHIVAGE ET RESTAURATION, story `MVP-L05-US007`
        #
        #  **CES CONTROLES VIENNENT EN DERNIER, ET CE N'EST PAS UN DETAIL.**
        #  Ils archivent le profil COMPLET, ce qui CLOT ses quatre relations et
        #  le retire de la liste. Les places plus haut, ils casseraient le
        #  controle 2 -- « exactement deux profils » -- et le temoin 26, qui
        #  exige un historique de metier INTACT.
        #
        #  **ET C'EST CE QUI LES REND FORTS** : ils relient l'archivage a la
        #  LISTE et a la FICHE, comme le controle 2 relie la fiche a la liste.
        #  Un archivage qui n'aurait change que `membership_state` passerait un
        #  controle de code HTTP ; il ne passe pas celui-ci.
        # ==================================================================

        def profils_listes() -> set[str]:
            corps_liste = appeler(arguments.base, liste, contexte, en_tetes=biscuit).json()
            lignes_liste = (
                corps_liste.get("collaborateurs", []) if isinstance(corps_liste, dict) else []
            )
            return {ligne["last_name"] for ligne in lignes_liste}

        def version_courante() -> int:
            _, brut_v = psql(
                compose,
                env,
                f"SELECT version FROM entity_membership WHERE id = '{appartenance}'",  # noqa: S608
            )
            return int(valeur(brut_v) or 0)

        def code_d_erreur(reponse: Reponse) -> str | None:
            corps_err = reponse.json()
            if not isinstance(corps_err, dict):
                return None
            erreur = corps_err.get("erreur")
            return erreur.get("code") if isinstance(erreur, dict) else None

        chemin_archivage = CHEMIN_ARCHIVAGE.format(code=code_entite, appartenance=appartenance)
        chemin_restauration = CHEMIN_RESTAURATION.format(
            code=code_entite, appartenance=appartenance
        )
        chemin_fiche_archivee = CHEMIN_FICHE_ARCHIVEE.format(
            code=code_entite, appartenance=appartenance
        )

        # --- 27. TEMOIN : l'ESM se connecte et obtient son jeton CSRF ---------
        controles += 1
        connexion_esm = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse_esm, "mot_de_passe": mot_de_passe},
        )
        jeton_esm = ""
        for pose in connexion_esm.cookies_poses:
            if pose.startswith(f"{nom_cookie}="):
                jeton_esm = pose.split("=", 1)[1].split(";", 1)[0]
        biscuit_esm = {"Cookie": f"{nom_cookie}={jeton_esm}"}
        session_esm = appeler(arguments.base, CHEMIN_SESSION, contexte, en_tetes=biscuit_esm)
        corps_esm = session_esm.json()
        csrf_esm = corps_esm.get("jeton_csrf", "") if isinstance(corps_esm, dict) else ""
        if connexion_esm.statut == 200 and jeton_esm and csrf_esm:
            print("    ok       TEMOIN : l'ESM se connecte, et `GET /auth/session` rend son jeton")
        else:
            echecs += 1
            print(
                f"    ECHEC    connexion de l'ESM : {connexion_esm.statut}, "
                f"cookie {'oui' if jeton_esm else 'NON'}, jeton {'oui' if csrf_esm else 'NON'}"
            )
            return 1
        cycle_esm = {**biscuit_esm, EN_TETE_JETON: csrf_esm, "Origin": arguments.base}

        # ==================================================================
        #  LOT 5, `T9` — L'HISTORIQUE ORGANISATIONNEL, story `MVP-L05-US008`
        #
        #  **CES CONTROLES VIENNENT AVANT CEUX DE `T8`, ET LA MESURE L'A IMPOSE.**
        #  Je les avais places apres, pour profiter des periodes que l'archivage
        #  clot. Resultat : le DSM du decor rendait **404** sur son propre
        #  consultant -- et il avait raison. L'archivage avait clos son
        #  `dsm_assignment`, la restauration ne l'a pas rouvert, donc il n'etait
        #  plus le DSM de personne. Le controle etait juste, l'ordre etait faux.
        #
        #  **C'est une consequence REELLE de `T8`, pas un artefact de decor** : un
        #  DSM perd l'acces a l'historique de son ancien consultant des que
        #  celui-ci est archive puis restaure sans reaffectation. `period @>
        #  instant` le veut, et le §6.2 aussi -- « SES consultants » se lit au
        #  present. C'est nomme au compte rendu.
        #
        #  Le decor porte donc un metier PASSE, clos, pose pour cette sous-etape :
        #  sans lui, aucune periode close n'existerait ici, et « l'historique rend
        #  le PASSE » ne serait prouve par rien.
        # ==================================================================

        chemin_historique = CHEMIN_HISTORIQUE.format(code=code_entite, appartenance=appartenance)

        # --- 28. LE CRITERE : l'ESM lit les CINQ axes -------------------------
        controles += 1
        histoire = appeler(arguments.base, chemin_historique, contexte, en_tetes=biscuit_esm)
        corps_h = histoire.json()
        h = corps_h if isinstance(corps_h, dict) else {}
        axes_attendus = {"metier", "statut", "cercle", "dsm", "responsabilites"}
        closes_lues = [
            p
            for axe in ("metier", "statut", "cercle", "dsm")
            for p in (h.get(axe) or [])
            if p.get("fin") is not None
        ]
        if (
            histoire.statut == 200
            and set(h) == axes_attendus
            and all(h.get(axe) is not None for axe in axes_attendus)
            and closes_lues
        ):
            print(
                f"    ok       LE CRITERE : l'ESM lit les {len(axes_attendus)} axes — et "
                f"{len(closes_lues)} periode(s) CLOSES y figurent : le PASSE est bien "
                "rendu, non les seules affectations courantes"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    historique de l'ESM : {histoire.statut}, axes {sorted(h)}, "
                f"{len(closes_lues)} periode(s) closes"
            )

        # --- 29. AUCUNE COLONNE TECHNIQUE dans les OCTETS SERVIS --------------
        #
        #  **CE CONTROLE PORTE SUR LA CHARGE UTILE, PAS SUR LES STRUCTURES.** Le
        #  test unitaire fige les champs des dataclasses ; celui-ci lit ce qui
        #  sort REELLEMENT de Caddy. Les deux sont necessaires : une structure
        #  propre servie par un serialiseur bavard rendrait quand meme les
        #  colonnes, et rien d'autre ne le dirait.
        controles += 1
        interdits = (
            "created_at",
            "updated_at",
            "created_by_person_id",
            "updated_by_person_id",
            "assigned_by_person_id",
            "archived_at",
            "version",
        )
        texte_servi = histoire.corps.decode("utf-8", "replace")
        trouves = [mot for mot in interdits if mot in texte_servi]
        if not trouves:
            print(
                f"    ok       AUCUNE des {len(interdits)} colonnes techniques ne parait dans "
                "les octets servis — « sans exposer les audits techniques », §16.2"
            )
        else:
            echecs += 1
            print(f"    ECHEC    colonnes techniques servies : {trouves}")

        # --- 30. le DSM lit SON consultant, SANS l'axe des responsabilites ----
        controles += 1
        histoire_dsm = appeler(arguments.base, chemin_historique, contexte, en_tetes=biscuit_dsm)
        corps_hd = histoire_dsm.json()
        hd = corps_hd if isinstance(corps_hd, dict) else {}
        if (
            histoire_dsm.statut == 200
            and set(hd) == axes_attendus
            and hd.get("responsabilites") is None
            and hd.get("dsm") is not None
        ):
            print(
                "    ok       le DSM lit SON consultant, et `responsabilites` vaut `null` — "
                "le §20 reserve l'historique des roles a l'ESM, l'ADM-E et le SUPER, et le "
                "§23.2 fait prevaloir la regle la plus etroite"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    historique du DSM : {histoire_dsm.statut}, axes {sorted(hd)}, "
                f"responsabilites={hd.get('responsabilites')!r}"
            )

        # --- 31. LE REFUS APPARIE : le MEME DSM sur un consultant non rattache -
        controles += 1
        histoire_autre = appeler(
            arguments.base,
            CHEMIN_HISTORIQUE.format(code=code_entite, appartenance=retiree),
            contexte,
            en_tetes=biscuit_dsm,
        )
        if histoire_autre.statut == 404:
            print(
                "    ok       LE REFUS APPARIE : le MEME DSM sur un consultant NON rattache — "
                "404, la meme forme qu'une appartenance inexistante : distinguer apprendrait "
                "de qui l'on n'est pas responsable"
            )
        else:
            echecs += 1
            print(f"    ECHEC    le DSM devrait etre refuse : {histoire_autre.statut}")

        # --- 32. sans role d'historique : 403, c'est le cas d'`EMP` -----------
        controles += 1
        histoire_sans_role = appeler(arguments.base, chemin_historique, contexte, en_tetes=biscuit)
        if histoire_sans_role.statut == 403:
            print(
                "    ok       sans role d'historique : 403 — la ligne « Audit » du §5 met "
                "`EMP` et `NEW` a TIRET, et le responsable de bureau n'obtient rien sur les "
                "profils (§6.2)"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    un appelant sans role devrait etre refuse : "
                f"{histoire_sans_role.statut}"
            )

        # --- 33. sans session : 401 ------------------------------------------
        controles += 1
        histoire_anonyme = appeler(arguments.base, chemin_historique, contexte)
        if histoire_anonyme.statut == 401:
            print("    ok       sans session : 401 — la matrice §5 refuse `ANON`")
        else:
            echecs += 1
            print(f"    ECHEC    historique sans session : {histoire_anonyme.statut}")

        # --- 34. sans session, l'archivage refuse -----------------------------
        controles += 1
        sans_session = appeler(
            arguments.base, chemin_archivage, contexte, charge={"version": version_courante()}
        )
        if sans_session.statut == 401:
            print("    ok       sans session : 401 — l'archivage n'est pas anonyme")
        else:
            echecs += 1
            print(f"    ECHEC    archivage sans session : {sans_session.statut}")

        # --- 35. sans jeton CSRF, l'archivage refuse --------------------------
        controles += 1
        sans_jeton = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": version_courante()},
            #  La session SEULE, sans en-tete de jeton : c'est exactement la
            #  requete qu'un formulaire d'un autre site produirait.
            en_tetes={**biscuit_esm, "Origin": arguments.base},
        )
        if sans_jeton.statut == 403:
            print(
                "    ok       sans jeton CSRF : 403 — la SECONDE ecriture metier du projet est "
                "protegee, et la regle n'est pas recopiee (`DEC-466`)"
            )
        else:
            echecs += 1
            print(f"    ECHEC    archivage sans jeton CSRF : {sans_jeton.statut}")

        # --- 36. LE REFUS APPARIE : le MEME DSM qui a ECRIT au 19 est REFUSE ---
        controles += 1
        refus_dsm = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": version_courante()},
            en_tetes=ecriture_dsm,
        )
        if refus_dsm.statut == 403:
            print(
                "    ok       LE REFUS APPARIE : le MEME DSM qui a ecrit au controle 19 est "
                "REFUSE a l'archivage — 403, le §6.1 le met a TIRET sur cette ligne"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    le DSM devrait etre refuse a l'archivage : {refus_dsm.statut}, "
                f"{str(refus_dsm.json())[:140]}"
            )

        # --- 37. LE CRITERE : l'ESM archive, et cela REVOQUE et CLOT ----------
        controles += 1
        listes_avant = profils_listes()
        archive = appeler(
            arguments.base,
            chemin_archivage,
            contexte,
            charge={"version": version_courante()},
            en_tetes=cycle_esm,
        )
        corps_archive = archive.json()
        detail = corps_archive if isinstance(corps_archive, dict) else {}
        closes = detail.get("relations_closes") or {}
        #  **LES CINQ RELATIONS DU DECOR, NOMMEES.** Un archivage qui n'aurait
        #  change que `membership_state` rendrait un dictionnaire VIDE, et le code
        #  HTTP serait exactement le meme.
        #
        #  **ET LA CINQUIEME EST CELLE QUE JE N'AVAIS PAS PREVUE : LE CONTROLE
        #  AVAIT RAISON.** J'en attendais quatre -- metier, statut, DSM, cercle,
        #  les relations de l'APPARTENANCE. Il en a rendu cinq, et la difference
        #  nommee etait `framework_responsibility_assignment` : « Ada Complete »
        #  porte une responsabilite `BOOSTER` dans le decor, et le service du
        #  `T9` du LOT 3 clot aussi les relations de la PERSONNE bornees a
        #  l'entite quittee. C'est la moitie « **et roles** » du §30.22, et ce
        #  contrat est meilleur que celui que j'avais ecrit.
        #
        #  **`technical_role_assignment` EN EST ABSENTE, ET C'EST MESURE** : le
        #  decor ne donne aucun role technique a ce profil. Cette liste est une
        #  INTERPRETATION du decor, non un etat derivable -- elle est donc
        #  declaree et confrontee au reel, comme `RELATIONS_ATTENDUES` de
        #  `verifier-historisation.py` (§7.27).
        attendues_closes = {
            "membership_job_assignment",
            "professional_status_assignment",
            "dsm_assignment",
            "circle_membership",
            "framework_responsibility_assignment",
        }
        if (
            archive.statut == 200
            and detail.get("etat_precedent") == "active"
            and detail.get("etat_nouveau") == "archived"
            and set(closes) == attendues_closes
        ):
            print(
                "    ok       LE CRITERE : l'ESM archive — 200, `active` -> `archived` en "
                f"passant par le depart, et les {len(attendues_closes)} relations du decor "
                "sont CLOSES, nommees table par table — dont la responsabilite BOOSTER, "
                "qui est la moitie « et roles » du §30.22"
            )
        else:
            echecs += 1
            #  **L'ECHEC NOMME LA DIFFERENCE, PAS LA CHARGE UTILE.** Un extrait
            #  tronque d'un dictionnaire cache precisement la cle qui manque :
            #  c'est le §7.18, la premiere correction a ecrire est celle qui dit
            #  pourquoi.
            print(
                f"    ECHEC    archivage par l'ESM : {archive.statut} "
                f"`{detail.get('etat_precedent')}` -> `{detail.get('etat_nouveau')}` ; "
                f"relations closes manquantes {sorted(attendues_closes - set(closes))}, "
                f"en trop {sorted(set(closes) - attendues_closes)}"
            )
            return 1

        # --- 38. l'archivage RETIRE de la liste ET de la fiche ordinaire ------
        controles += 1
        listes_apres = profils_listes()
        fiche_apres = appeler(
            arguments.base,
            CHEMIN_PROFIL.format(code=code_entite, appartenance=appartenance),
            contexte,
            en_tetes=biscuit,
        )
        if listes_avant - listes_apres == {"Complete"} and fiche_apres.statut == 404:
            print(
                f"    ok       l'archive DISPARAIT : la liste passe de {sorted(listes_avant)} a "
                f"{sorted(listes_apres)}, et sa fiche ordinaire rend 404"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    apres archivage : liste {sorted(listes_apres)}, "
                f"fiche {fiche_apres.statut}"
            )

        # --- 39. la fiche ARCHIVEE la sert, a l'ESM ---------------------------
        controles += 1
        fiche_archivee = appeler(
            arguments.base, chemin_fiche_archivee, contexte, en_tetes=biscuit_esm
        )
        corps_fa = fiche_archivee.json()
        fa = corps_fa if isinstance(corps_fa, dict) else {}
        if (
            fiche_archivee.statut == 200
            and fa.get("id") == appartenance
            and fa.get("photo") is None
        ):
            print(
                "    ok       « Consulter un profil archive » : 200 a l'ESM sur une route "
                "DISTINCTE, et AUCUN chemin de photo — il menerait a un 404 garanti"
            )
        else:
            echecs += 1
            print(f"    ECHEC    fiche archivee : {fiche_archivee.statut}, {str(fa)[:200]}")

        # --- 40. le MEME DSM est REFUSE sur la fiche archivee -----------------
        controles += 1
        fa_dsm = appeler(arguments.base, chemin_fiche_archivee, contexte, en_tetes=biscuit_dsm)
        if fa_dsm.statut == 403:
            print(
                "    ok       le MEME DSM est REFUSE sur la fiche archivee — 403 : le §6.1 "
                "separe « profil actif », ouverte aux huit roles, de « profil archive »"
            )
        else:
            echecs += 1
            print(f"    ECHEC    le DSM devrait etre refuse : {fa_dsm.statut}")

        # --- 41. la RESTAURATION la ramene, et NE ROUVRE RIEN -----------------
        controles += 1
        restauree = appeler(
            arguments.base,
            chemin_restauration,
            contexte,
            charge={"version": version_courante()},
            en_tetes=cycle_esm,
        )
        corps_r = restauree.json()
        r = corps_r if isinstance(corps_r, dict) else {}
        a_redonner = set(r.get("relations_a_redonner") or [])
        fiche_revenue = appeler(
            arguments.base,
            CHEMIN_PROFIL.format(code=code_entite, appartenance=appartenance),
            contexte,
            en_tetes=biscuit,
        )
        if (
            restauree.statut == 200
            and r.get("etat_precedent") == "archived"
            and r.get("etat_nouveau") == "active"
            #  **EXACTEMENT CE QUE L'ARCHIVAGE A CLOS, NI PLUS NI MOINS.** Les
            #  deux ensembles sont mesures par deux chemins differents -- le
            #  service de revocation compte ses `UPDATE`, le rapport interroge
            #  les periodes -- et `technical_role_assignment` n'est dans aucun
            #  des deux : ce profil n'a jamais porte de role technique, et on ne
            #  redonne pas ce qui n'a pas ete donne (§7.21).
            and a_redonner == set(closes)
            and profils_listes() == listes_avant
            and fiche_revenue.statut == 200
        ):
            print(
                "    ok       LE CRITERE : la restauration ramene dans la liste ET dans la "
                f"fiche — 200 — et NOMME les {len(a_redonner)} affectations restees closes"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    restauration : {restauree.statut}, a redonner {sorted(a_redonner)}, "
                f"liste {sorted(profils_listes())}, fiche {fiche_revenue.statut}"
            )

        # --- 42. l'archivage est REFUSE sur une appartenance deja archivee ----
        #
        #  **LE TEMOIN DE LA GRILLE D'ETAT, A TRAVERS L'API.** Il vient APRES la
        #  restauration a dessein : la cible est de nouveau `active`, donc c'est
        #  la RESTAURATION qui doit maintenant etre refusee. Le meme appelant, le
        #  meme jeton, la meme cible -- seul l'etat a change.
        controles += 1
        restaurer_deux_fois = appeler(
            arguments.base,
            chemin_restauration,
            contexte,
            charge={"version": version_courante()},
            en_tetes=cycle_esm,
        )
        if (
            restaurer_deux_fois.statut == 403
            and code_d_erreur(restaurer_deux_fois) == "action_hors_perimetre"
        ):
            print(
                "    ok       restaurer un profil ACTIF est refuse — 403 "
                "`action_hors_perimetre` : §23.2, l'etat prevaut sur le cumul des roles"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    seconde restauration : {restaurer_deux_fois.statut}, "
                f"{code_d_erreur(restaurer_deux_fois)}"
            )

        # --- 43. L'HISTORIQUE PORTE CE QUE L'ARCHIVAGE A CLOS -----------------
        #
        #  **LE SEUL CONTROLE QUI CROISE DEUX SOUS-ETAPES**, et il vaut mieux
        #  qu'un temoin : l'archivage du controle 37 a clos CINQ relations, la
        #  restauration ne les a pas rouvertes, et l'historique doit donc porter
        #  ces cloture-la. C'est la preuve qu'il lit l'etat REEL de la base, et
        #  non une vue figee au moment du decor.
        controles += 1
        histoire_apres = appeler(arguments.base, chemin_historique, contexte, en_tetes=biscuit_esm)
        corps_ha = histoire_apres.json()
        ha = corps_ha if isinstance(corps_ha, dict) else {}
        closes_apres = [
            p
            for axe in ("metier", "statut", "cercle", "dsm", "responsabilites")
            for p in (ha.get(axe) or [])
            if p.get("fin") is not None
        ]
        ouvertes_apres = [
            p
            for axe in ("metier", "statut", "cercle", "dsm", "responsabilites")
            for p in (ha.get(axe) or [])
            if p.get("fin") is None
        ]
        if (
            histoire_apres.statut == 200
            and len(closes_apres) > len(closes_lues)
            and not ouvertes_apres
        ):
            print(
                f"    ok       l'historique porte ce que l'archivage a CLOS : "
                f"{len(closes_lues)} periode(s) closes avant, {len(closes_apres)} apres, "
                "et PLUS AUCUNE ouverte — la restauration ne rouvre rien, et "
                "l'historique le montre"
            )
        else:
            echecs += 1
            print(
                f"    ECHEC    historique apres archivage : {histoire_apres.statut}, "
                f"{len(closes_apres)} closes (avant {len(closes_lues)}), "
                f"{len(ouvertes_apres)} encore ouvertes"
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
        "exactement la population du trombinoscope, sert la MINIATURE — jamais "
        "l'originale — un DSM n'ecrit QUE dans son perimetre, et il est REFUSE a "
        "l'archivage, que seul l'ESM mene : la liste et la fiche le suivent, puis "
        "la restauration les ramene sans rouvrir aucune affectation. Et "
        "l'historique rend les periodes CLOSES par cet archivage, sans une seule "
        "colonne technique, avec un axe de moins pour le DSM"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
