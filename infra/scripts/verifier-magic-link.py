#!/usr/bin/env python3
"""La reponse a une demande de magic link est-elle IDENTIQUE, connue ou non ?

LOT 3, sous-etape `T3`, story `MVP-L03-US001`.

LE CRITERE EST UNE EGALITE, PAS UN REFUS

  Backlog `US001` : « la reponse est **generique** ». Fiche du lot, §3 : « la
  reponse et le code HTTP sont identiques pour une adresse connue et inconnue --
  deux tests, et la comparaison porte sur le corps **et** l'en-tete ».

  Un controle qui se contenterait du code HTTP ne prouverait rien : deux reponses
  peuvent porter le meme 202 et des corps differents. **C'est la quatrieme
  proposition du §7.0** -- l'echec produirait la meme observation que le succes.

POURQUOI A TRAVERS CADDY, ET EN HTTPS

  C'est la reponse REELLE que voit un navigateur. Les tests d'integration
  eprouvent la meme egalite au niveau ASGI, ou l'on controle tout ; ici on
  eprouve ce que le mandataire livre, en-tetes ajoutes compris. Un mandataire qui
  ajouterait un en-tete sur un seul des deux chemins ne se verrait pas autrement.

DEUX EN-TETES VARIENT LEGITIMEMENT, ET ILS SONT NOMMES

  `X-Request-ID` est un identifiant de correlation : il DOIT differer d'une
  requete a l'autre, c'est son objet (cahier §28.1). `Date` porte la seconde
  courante. Les exclure est necessaire ; les exclure **sans les nommer** ne le
  serait pas, parce que la liste d'exclusion est exactement l'endroit ou une
  fuite pourrait se cacher.

  Le controle affiche donc la liste, exige qu'elle soit **exactement** celle-la,
  et refuse tout autre en-tete divergent.

ET IL PORTE SON TEMOIN

  Un comparateur qui ne saurait pas echouer ne prouverait rien. Le temoin lui
  soumet deux reponses REELLEMENT differentes -- la reponse generique et le 422
  d'un corps malforme -- et **exige qu'il signale la difference**. Sans lui, un
  comparateur casse rendrait « identiques » sur tout.

CE QU'IL NE PROUVE PAS, ET IL FAUT LE DIRE

  **Pas l'egalite des DUREES.** Le chemin d'une adresse connue fait quatre
  requetes SQL de plus, et l'envoi de l'e-mail a lieu apres la reponse
  precisement pour que l'aller-retour SMTP n'y entre pas. Le residuel est
  **mesure puis rapporte**, jamais affirme nul, et jamais exige : l'exiger
  produirait un controle intermittent, ce qui est pire qu'un residuel nomme.

  **ET LA FACON DE LE MESURER EST ELLE-MEME UNE LECON.** La premiere version
  comparait UNE requete a UNE autre et annoncait 95 ms contre 22 ms : un facteur
  quatre qui mesurait surtout l'ouverture du pool de connexions SQLAlchemy, payee
  par le premier appel. **Les deux nombres ne mesuraient pas la meme grandeur** --
  sixieme proposition du §7.0. La mesure est donc entrelacee, apres chauffe, et
  c'est la MEDIANE qui est rapportee : l'ecart tombe a moins d'une milliseconde.

  `T8` -- la limitation de debit -- est la sous-etape qui reduira
  l'exploitabilite d'une mesure statistique.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

#  Les deux en-tetes dont la variation est LEGITIME, et la liste est fermee.
EN_TETES_VARIABLES = frozenset({"x-request-id", "date"})

CHEMIN = "/api/v1/auth/magic-link"
CHEMIN_CONSOMMATION = "/api/v1/auth/magic-link/consommation"

#  Le `Caddyfile`, pour le garde-fou de `T4`. Voir `_journalisation_de_caddy`.
CADDYFILE = pathlib.Path(__file__).resolve().parents[1] / "caddy" / "Caddyfile"

#  Marqueur des lignes que ce controle cree, pour pouvoir les retirer ensuite
#  SANS toucher a autre chose. Un identifiant unique par execution : deux
#  executions concurrentes ne se marcheraient pas dessus.
MARQUEUR = f"t3-verif-{uuid.uuid4().hex[:12]}"

DELAI_HTTP = 15


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION — il possede les tables. Pas de shell, §7.2."""
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
    """Une reponse HTTP reduite a ce que le critere compare."""

    def __init__(
        self, statut: int, corps: bytes, en_tetes: dict[str, str], duree_ms: float
    ) -> None:
        self.statut = statut
        self.corps = corps
        #  Les noms d'en-tete HTTP sont insensibles a la casse : les comparer
        #  telle quelle ferait dependre le verdict d'un detail de transport.
        self.en_tetes = {nom.lower(): valeur for nom, valeur in en_tetes.items()}
        self.duree_ms = duree_ms


def appeler(base: str, charge: bytes, contexte: ssl.SSLContext) -> Reponse:
    """La demande — conserve pour ne pas reecrire les appels de `T3`."""
    return _appeler(base, CHEMIN, charge, contexte)


def _appeler(base: str, chemin: str, charge: bytes, contexte: ssl.SSLContext) -> Reponse:
    """POST sur la route, et rendre la reponse MEME en cas de code d'erreur.

    `urllib` leve sur un 4xx. Un controle qui laisserait remonter l'exception ne
    pourrait pas comparer un 422 — or c'est precisement le temoin.
    """
    requete = urllib.request.Request(  # noqa: S310 — schema https impose par `base`
        f"{base}{chemin}",
        data=charge,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    debut = time.monotonic()
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            corps = reponse.read()
            duree = (time.monotonic() - debut) * 1000
            return Reponse(reponse.status, corps, dict(reponse.headers), duree)
    except urllib.error.HTTPError as erreur:
        corps = erreur.read()
        duree = (time.monotonic() - debut) * 1000
        return Reponse(erreur.code, corps, dict(erreur.headers), duree)


def _mailpit(
    env: dict[str, str],
    chemin: str,
    *,
    methode: str = "GET",
    charge: bytes | None = None,
) -> dict | None:
    """Interroger l'API de Mailpit sur la boucle locale. `None` si injoignable.

    Mailpit est publie sur `127.0.0.1` uniquement (`DEC-460`), en HTTP clair :
    c'est un outil de developpement, jamais expose. Le port est LU dans le fichier
    d'environnement, jamais ecrit en dur -- il differe entre developpement et
    recette.
    """
    port = env.get("MAILPIT_HOST_PORT", "8025")
    requete = urllib.request.Request(
        f"http://127.0.0.1:{port}{chemin}",
        data=charge,
        headers={"Content-Type": "application/json"} if charge else {},
        method=methode,
    )
    #  `None` SIGNIFIE « L'APPEL A ECHOUE », ET RIEN D'AUTRE.
    #
    #  Ma premiere version rendait aussi `None` quand la reponse n'etait pas du
    #  JSON -- et Mailpit repond `ok` en texte brut a un `DELETE`. La suppression
    #  reussissait donc, et le controle annoncait « 0 supprime(s) » : le succes
    #  produisait exactement l'observation de l'echec. Defaut `T3-5`.
    #
    #  Un corps illisible sur un appel qui a ABOUTI rend donc `{}`, non `None`.
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_HTTP) as reponse:  # noqa: S310
            brut = reponse.read()
    except (urllib.error.URLError, OSError):
        return None
    if not brut:
        return {}
    try:
        resultat: dict = json.loads(brut)
    except json.JSONDecodeError:
        return {}
    return resultat


def _journalisation_de_caddy() -> tuple[bool, list[str]]:
    """Caddy journalise-t-il les ACCES, et si oui, avec quel filtre ?

    **POURQUOI CE CONTROLE EXISTE, ET C'EST LE POINT LE PLUS SUBTIL DE `T4`.**

    Le lien de l'e-mail porte le jeton dans sa QUERY STRING -- c'est une page du
    frontend qu'il ouvre, et cette page est servie par Caddy. Mesure du
    21/08/2026 : **aucun jeton ne figure dans les journaux de Caddy**, sur 3 171
    lignes examinees.

    **Mais ce n'est pas une protection : c'est une absence.** Le bloc global
    `log { format json }` configure le journal PROPRE de Caddy -- API
    d'administration, TLS, demarrage. Les journaux d'ACCES exigent une directive
    `log` DANS un bloc de site, et il n'y en a aucune : 0 ligne
    « handled request » mesuree.

    Le jour ou quelqu'un en ajoutera une -- et le cahier §28 rend la chose
    plausible -- `request.uri` y portera le jeton, et **rien ne le signalerait**.
    C'est exactement le §7.23 : *un etat DORMANT ne se voit pas dans ce qui
    tourne.*

    Ce controle transforme donc l'absence accidentelle en absence GARDEE : il
    rapporte qu'il n'y a pas de journal d'acces, et il ECHOUE si un bloc de site
    en declare un sans filtrer la chaine de requete.

    Returns:
        `(journalise, anomalies)`. `journalise` dit si un bloc de site declare un
        journal d'acces ; `anomalies` nomme ceux qui ne filtrent pas le jeton.
    """
    if not CADDYFILE.is_file():
        return False, [f"Caddyfile introuvable : {CADDYFILE}"]
    lignes = CADDYFILE.read_text(encoding="utf-8").splitlines()

    #  Le bloc global de Caddy est celui qui s'ouvre sur une accolade SEULE. Une
    #  directive `log` a l'interieur configure le journal propre du serveur, pas
    #  les acces. On ne compte donc que les `log` situes APRES la fermeture du
    #  bloc global.
    profondeur = 0
    global_termine = False
    journaux_de_site: list[int] = []
    for numero, brute in enumerate(lignes, start=1):
        ligne = brute.split("#", 1)[0].strip()
        if not ligne:
            continue
        if profondeur == 0 and ligne == "{":
            profondeur = 1
            continue
        ouvre = ligne.count("{")
        ferme = ligne.count("}")
        if profondeur > 0 and re.match(r"^log\b", ligne) and global_termine:
            journaux_de_site.append(numero)
        profondeur += ouvre - ferme
        if profondeur <= 0:
            profondeur = 0
            global_termine = True

    if not journaux_de_site:
        return False, []

    #  Un journal d'acces existe : il DOIT filtrer la chaine de requete. Caddy
    #  sait le faire (`format filter` avec un `query` delete/replace). Le nommer
    #  ici plutot que de deviner : le contrôle exige la MENTION du filtre.
    texte = CADDYFILE.read_text(encoding="utf-8")
    if "query" not in texte or "filter" not in texte:
        return True, [
            f"un journal d'acces est declare (ligne(s) {journaux_de_site}) SANS "
            "filtre de chaine de requete : le jeton du magic link y figurerait"
        ]
    return True, []


def _sans_correlation(corps: bytes) -> tuple[object, str | None]:
    """Le corps d'erreur, prive de son identifiant de correlation.

    Rend `(corps_normalise, identifiant)`. Un corps illisible est rendu tel quel :
    le comparateur signalera alors une difference, ce qui est le bon comportement.
    """
    try:
        charge = json.loads(corps)
    except json.JSONDecodeError:
        return corps, None
    if isinstance(charge, dict) and isinstance(charge.get("erreur"), dict):
        identifiant = charge["erreur"].pop("identifiant_correlation", None)
        return charge, identifiant
    return charge, None


def _ecarts_de_refus(gauche: Reponse, droite: Reponse) -> list[str]:
    """Comparer deux refus, en neutralisant le SEUL champ qui doit varier.

    Et il exige que les deux identifiants de correlation soient **differents** :
    s'ils etaient egaux, la correlation du cahier §28.1 serait cassee, ce qui est
    un autre defaut -- et le neutraliser aurait alors masque celui-la.
    """
    ecarts: list[str] = []
    if gauche.statut != droite.statut:
        ecarts.append(f"code HTTP : {gauche.statut} contre {droite.statut}")
    corps_gauche, correlation_gauche = _sans_correlation(gauche.corps)
    corps_droite, correlation_droite = _sans_correlation(droite.corps)
    if corps_gauche != corps_droite:
        ecarts.append(f"corps hors correlation : {corps_gauche!r} contre {corps_droite!r}")
    if correlation_gauche is None or correlation_droite is None:
        ecarts.append("un corps ne porte pas d'identifiant de correlation (cahier §18.3)")
    elif correlation_gauche == correlation_droite:
        ecarts.append("les deux refus portent le MEME identifiant de correlation")
    for nom in sorted((set(gauche.en_tetes) | set(droite.en_tetes)) - EN_TETES_VARIABLES):
        if gauche.en_tetes.get(nom) != droite.en_tetes.get(nom):
            ecarts.append(f"en-tete {nom} differe")
    return ecarts


def differences(gauche: Reponse, droite: Reponse) -> list[str]:
    """Tout ce qui distingue deux reponses, hors en-tetes legitimement variables."""
    ecarts: list[str] = []
    if gauche.statut != droite.statut:
        ecarts.append(f"code HTTP : {gauche.statut} contre {droite.statut}")
    if gauche.corps != droite.corps:
        ecarts.append(f"corps : {len(gauche.corps)} octets contre {len(droite.corps)}")
    noms = set(gauche.en_tetes) | set(droite.en_tetes)
    for nom in sorted(noms - EN_TETES_VARIABLES):
        if gauche.en_tetes.get(nom) != droite.en_tetes.get(nom):
            ecarts.append(
                f"en-tete {nom} : {gauche.en_tetes.get(nom)!r} contre {droite.en_tetes.get(nom)!r}"
            )
    return ecarts


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--base", required=True, help="origine HTTPS servie par Caddy")
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    if not domaines:
        print("  ECHEC     ALLOWED_EMAIL_DOMAINS ne declare aucun domaine")
        return 1
    domaine = domaines[0]

    #  L'autorite interne de Caddy n'est pas dans le magasin de Python. Le
    #  controle ne doit PAS dependre d'une action humaine (approbation dans le
    #  trousseau) : meme parti que `curl -k` ailleurs dans ce depot.
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    connue = f"{MARQUEUR}.connue@{domaine}"
    inconnue = f"{MARQUEUR}.inconnue@{domaine}"
    archivee = f"{MARQUEUR}.archivee@{domaine}"

    print()
    print("  Reponse generique a la demande de magic link — US001, cahier §7.2")
    print(f"    info     origine {arguments.base}, domaine {domaine}")
    print(f"    info     marqueur des lignes creees : {MARQUEUR}")

    echecs = 0
    controles = 0

    #  ------------------------------------------------------------------
    #  Le decor : une entite, une personne ACTIVE avec appartenance active,
    #  et une seconde personne dont l'appartenance est ARCHIVEE (§30.11).
    #  ------------------------------------------------------------------
    decor = f"""
    DO $$
    DECLARE
      e uuid; p1 uuid; p2 uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}', 'Entite de verification T3', 'Bordeaux', 'FR', 'active',
              'Europe/Paris')
      RETURNING id INTO e;

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{connue}', '{connue}', 'Verif', 'Connue', 'active')
      RETURNING id INTO p1;

      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (p1, e, current_date, 'active', 'consultant', 'draft');

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{archivee}', '{archivee}', 'Verif', 'Archivee', 'active')
      RETURNING id INTO p2;

      INSERT INTO entity_membership
        (person_id, entity_id, arrival_date, membership_state, professional_category,
         profile_visibility)
      VALUES (p2, e, current_date, 'archived', 'consultant', 'draft');
    END $$;
    """  # noqa: S608 — voir la justification en tete de `psql`
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:300]}")
        return 1
    print("    ok       decor cree : 1 entite, 1 profil ACTIF, 1 profil ARCHIVE")

    #  Le domaine doit etre autorise, sinon le cas « connue » serait refuse et le
    #  controle passerait pour la mauvaise raison — les deux reponses seraient
    #  identiques sans qu'aucun lien n'ait ete emis.
    code, sortie = psql(
        compose,
        env,
        f"SELECT count(*) FROM allowed_email_domain "  # noqa: S608
        f"WHERE domain = '{domaine}' AND active IS TRUE AND period @> now()",
    )
    if code or sortie.strip() == "0":
        print(f"    ECHEC    aucun domaine `{domaine}` actif — lance `make domaines-provision`")
        _nettoyer(compose, env)
        return 1
    print(f"    ok       domaine `{domaine}` actif en base")

    try:
        #  --------------------------------------------------------------
        #  1. L'EGALITE, sur le corps ET les en-tetes
        #  --------------------------------------------------------------
        r_connue = appeler(arguments.base, json.dumps({"email": connue}).encode("utf-8"), contexte)
        r_inconnue = appeler(
            arguments.base, json.dumps({"email": inconnue}).encode("utf-8"), contexte
        )
        r_archivee = appeler(
            arguments.base, json.dumps({"email": archivee}).encode("utf-8"), contexte
        )

        controles += 1
        ecarts = differences(r_connue, r_inconnue)
        if ecarts:
            print("    ECHEC    adresse CONNUE et adresse INCONNUE : reponses differentes")
            for ecart in ecarts:
                print(f"             {ecart}")
            echecs += 1
        else:
            print(
                f"    ok       connue == inconnue — code {r_connue.statut}, "
                f"{len(r_connue.corps)} octets, "
                f"{len(set(r_connue.en_tetes) - EN_TETES_VARIABLES)} en-tetes compares"
            )

        controles += 1
        ecarts = differences(r_connue, r_archivee)
        if ecarts:
            print("    ECHEC    §30.11 — profil ARCHIVE : reponse differente d'un profil actif")
            for ecart in ecarts:
                print(f"             {ecart}")
            echecs += 1
        else:
            print("    ok       connue == archivee — §30.11 sans divergence de reponse")

        #  La liste d'exclusion est EXIGEE, pas supposee : si un jour un autre
        #  en-tete variait, il faudrait l'ajouter sciemment, pas le decouvrir.
        controles += 1
        varies = {
            nom
            for nom in set(r_connue.en_tetes) | set(r_inconnue.en_tetes)
            if r_connue.en_tetes.get(nom) != r_inconnue.en_tetes.get(nom)
        }
        if varies != EN_TETES_VARIABLES & varies or not varies <= EN_TETES_VARIABLES:
            print(f"    ECHEC    en-tetes variables inattendus : {sorted(varies)}")
            echecs += 1
        else:
            print(f"    ok       en-tetes exclus de la comparaison : {sorted(varies)}")
            print("             X-Request-ID DOIT varier (cahier §28.1) ; Date porte la seconde")

        #  --------------------------------------------------------------
        #  2. LE TEMOIN : le comparateur sait-il ECHOUER ?
        #  --------------------------------------------------------------
        controles += 1
        r_malformee = appeler(arguments.base, b'{"pas_le_champ_attendu": 1}', contexte)
        ecarts_temoin = differences(r_connue, r_malformee)
        if not ecarts_temoin:
            print("    ECHEC    TEMOIN : le comparateur ne voit pas deux reponses differentes")
            print("             il ne prouve donc rien de l'egalite qu'il annonce")
            echecs += 1
        else:
            print(
                f"    ok       TEMOIN — {len(ecarts_temoin)} difference(s) detectee(s) "
                f"face a un corps malforme ({r_malformee.statut})"
            )

        #  --------------------------------------------------------------
        #  3. L'EFFET REEL : un lien pour la connue, aucun pour les autres
        #  --------------------------------------------------------------
        #  Sans ce controle, les trois reponses pourraient etre identiques
        #  parce que RIEN ne se passe jamais — l'egalite serait vraie et
        #  inutile. C'est la quatrieme proposition du §7.0.
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT p.email_normalized, count(m.id) FROM person p "  # noqa: S608
            "LEFT JOIN magic_link_request m ON m.person_id = p.id "
            "  AND m.used_at IS NULL AND m.invalidated_at IS NULL "
            f"WHERE p.email_normalized LIKE '{MARQUEUR}%' "
            "GROUP BY p.email_normalized ORDER BY 1",
        )
        comptes = {
            ligne.split("|")[0]: int(ligne.split("|")[1])
            for ligne in sortie.splitlines()
            if "|" in ligne
        }
        attendu = {connue: 1, archivee: 0}
        if code or comptes != attendu:
            print(f"    ECHEC    liens actifs : {comptes} au lieu de {attendu}")
            echecs += 1
        else:
            print("    ok       1 lien actif pour le profil ACTIF, 0 pour le profil ARCHIVE")

        #  --------------------------------------------------------------
        #  4. L'INVALIDATION : une seconde demande n'en laisse qu'UN actif
        #  --------------------------------------------------------------
        controles += 1
        appeler(arguments.base, json.dumps({"email": connue}).encode("utf-8"), contexte)
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE m.used_at IS NULL AND m.invalidated_at IS NULL), "  # noqa: S608
            "       count(*) "
            "FROM magic_link_request m JOIN person p ON p.id = m.person_id "
            f"WHERE p.email_normalized = '{connue}'",
        )
        if code or sortie.strip() != "1|2":
            print(f"    ECHEC    apres une seconde demande : attendu `1|2`, obtenu {sortie!r}")
            echecs += 1
        else:
            print("    ok       seconde demande — 2 liens en base, 1 SEUL actif (§10.3)")

        #  --------------------------------------------------------------
        #  5. L'AUDIT : chaque demande est tracee, l'inconnue comprise
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE person_id IS NULL), count(*) FROM auth_event "
            "WHERE event_type = 'MAGIC_LINK_REQUESTED' "
            "  AND occurred_at > now() - interval '5 minutes'",
        )
        if code or not sortie.strip():
            print(f"    ECHEC    lecture de auth_event : {sortie[:180]}")
            echecs += 1
        else:
            sans_personne, total = (int(v) for v in sortie.strip().split("|"))
            if total < 4 or sans_personne < 1:
                print(
                    f"    ECHEC    audit : {total} evenement(s), dont {sans_personne} "
                    "sans personne — attendu au moins 4 dont 1"
                )
                echecs += 1
            else:
                print(
                    f"    ok       audit — {total} evenements MAGIC_LINK_REQUESTED, "
                    f"dont {sans_personne} sans personne (adresse inconnue)"
                )

        #  --------------------------------------------------------------
        #  6. AUCUN JETON EN CLAIR EN BASE
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM magic_link_request "
            "WHERE token_hash LIKE 'oml\\_%' OR length(token_hash) <> 64 "
            "   OR token_hash !~ '^[0-9a-f]{64}$'",
        )
        if code or sortie.strip() != "0":
            print(f"    ECHEC    empreintes non conformes en base : {sortie!r}")
            echecs += 1
        else:
            print("    ok       toutes les empreintes sont 64 hexadecimaux, aucun jeton en clair")

        #  --------------------------------------------------------------
        #  7. AUCUN LIEN COMPLET DANS LES JOURNAUX DU CONTENEUR
        #  --------------------------------------------------------------
        controles += 1
        journaux = subprocess.run(  # noqa: S603
            [*compose, "logs", "--no-log-prefix", "--tail", "400", "api"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte = journaux.stdout + journaux.stderr
        if "oml_" in texte:
            print("    ECHEC    un jeton `oml_` figure dans les journaux du conteneur api")
            echecs += 1
        else:
            print(
                f"    ok       aucun `oml_` dans les {len(texte.splitlines())} dernieres "
                "lignes de journal de api"
            )

        #  --------------------------------------------------------------
        #  8. MAILPIT CAPTE LE MESSAGE — critere litteral de `US001`
        #  --------------------------------------------------------------
        #
        #  LE CONTROLE DECISIF N'EST PAS « UN E-MAIL EST ARRIVE ».  C'est que le
        #  jeton PORTE PAR L'E-MAIL corresponde a une ligne de la base : sans lui,
        #  un service qui enverrait un lien sans l'enregistrer -- ou l'inverse --
        #  donnerait exactement la meme observation. Quatrieme proposition du §7.0.
        controles += 1
        recus = _mailpit(env, f"/api/v1/search?query={urllib.parse.quote(f'to:{connue}')}")
        absents = _mailpit(env, f"/api/v1/search?query={urllib.parse.quote(f'to:{inconnue}')}")
        if recus is None or absents is None:
            print("    ECHEC    Mailpit injoignable — son API ne repond pas")
            echecs += 1
        elif absents.get("messages_count", 0) != 0:
            print(
                f"    ECHEC    Mailpit porte {absents['messages_count']} message(s) pour "
                "l'adresse INCONNUE — c'est une fuite d'existence par le canal e-mail"
            )
            echecs += 1
        elif not recus.get("messages"):
            print("    ECHEC    Mailpit n'a recu AUCUN message pour l'adresse connue")
            echecs += 1
        else:
            identifiant = recus["messages"][0]["ID"]
            message = _mailpit(env, f"/api/v1/message/{identifiant}")
            corps = (message or {}).get("Text", "")
            trouves = re.findall(r"oml_[A-Za-z0-9_-]{40,}", corps)
            if len(trouves) != 1:
                print(f"    ECHEC    {len(trouves)} jeton(s) dans le corps, attendu 1")
                echecs += 1
            else:
                empreinte = hashlib.sha256(trouves[0].encode("utf-8")).hexdigest()
                code, sortie = psql(
                    compose,
                    env,
                    "SELECT count(*) FROM magic_link_request m JOIN person p "  # noqa: S608
                    f"ON p.id = m.person_id WHERE p.email_normalized = '{connue}' "
                    f"  AND m.token_hash = '{empreinte}'",
                )
                if code or sortie.strip() != "1":
                    print(
                        "    ECHEC    le jeton de l'e-mail ne correspond a AUCUNE ligne "
                        f"de `magic_link_request` (obtenu {sortie!r})"
                    )
                    echecs += 1
                else:
                    #  Le jeton n'est PAS affiche : le §28.2 l'interdit, et un
                    #  controle qui le journaliserait creerait la fuite qu'il
                    #  cherche a prevenir.
                    print(
                        "    ok       Mailpit — 1 message pour la connue, 0 pour "
                        "l'inconnue ; le jeton de l'e-mail correspond a la ligne en base"
                    )
                if arguments.base.rstrip("/") not in corps:
                    print(
                        f"    ECHEC    le lien ne porte pas l'origine servie "
                        f"({arguments.base}) — PUBLIC_BASE_URL est faux"
                    )
                    echecs += 1
                else:
                    print(f"    ok       le lien pointe sur {arguments.base}/connexion/lien")

        #  --------------------------------------------------------------
        #  9. LA CONSOMMATION — LOT 3, T4, story US002
        #  --------------------------------------------------------------
        #
        #  Le jeton employe ici est celui que MAILPIT a livre : c'est le seul qui
        #  prouve la chaine complete. Un jeton lu en base ne dirait rien de
        #  l'e-mail, et un jeton engendre par ce script ne dirait rien du tout.
        controles += 1
        recus = _mailpit(env, f"/api/v1/search?query={urllib.parse.quote(f'to:{connue}')}")
        jeton_livre = None
        if recus and recus.get("messages"):
            message = _mailpit(env, f"/api/v1/message/{recus['messages'][0]['ID']}")
            trouves = re.findall(r"oml_[A-Za-z0-9_-]{40,}", (message or {}).get("Text", ""))
            jeton_livre = trouves[0] if trouves else None

        if jeton_livre is None:
            print("    ECHEC    aucun jeton exploitable dans l'e-mail : rien a consommer")
            echecs += 1
        else:
            premiere = _appeler(
                arguments.base,
                CHEMIN_CONSOMMATION,
                json.dumps({"token": jeton_livre}).encode("utf-8"),
                contexte,
            )
            seconde = _appeler(
                arguments.base,
                CHEMIN_CONSOMMATION,
                json.dumps({"token": jeton_livre}).encode("utf-8"),
                contexte,
            )
            inconnu = _appeler(
                arguments.base,
                CHEMIN_CONSOMMATION,
                json.dumps({"token": "oml_" + "z" * 43}).encode("utf-8"),
                contexte,
            )
            if premiere.statut != 200:
                print(
                    f"    ECHEC    le lien livre par Mailpit est refuse : "
                    f"{premiere.statut} {premiere.corps[:120]!r}"
                )
                echecs += 1
            elif seconde.statut == 200:
                print("    ECHEC    UN SECOND USAGE A REUSSI — le lien est rejouable")
                echecs += 1
            else:
                print(
                    f"    ok       consommation — 1er usage {premiere.statut}, "
                    f"2e usage {seconde.statut}, jeton inconnu {inconnu.statut}"
                )

            #  LE REFUS EST-IL LE MEME pour « deja consomme » et « inconnu » ?
            #  Le §3 de la fiche ne prevoit qu'UN ecran pour ces cas.
            #
            #  **LE CORPS D'ERREUR PORTE L'IDENTIFIANT DE CORRELATION**, cahier
            #  §18.3, et il DOIT differer d'une requete a l'autre. Ma premiere
            #  version comparait les corps bruts et signalait « 289 octets contre
            #  289 » : meme longueur, contenu different. Le neutraliser est
            #  necessaire ; le neutraliser SANS LE NOMMER ne le serait pas -- c'est
            #  exactement le raisonnement des en-tetes variables ci-dessus.
            controles += 1
            ecarts = _ecarts_de_refus(seconde, inconnu)
            if ecarts:
                print("    ECHEC    « deja consomme » et « inconnu » sont DISTINGUABLES")
                for ecart in ecarts:
                    print(f"             {ecart}")
                echecs += 1
            else:
                print(
                    "    ok       « deja consomme » == « jeton inconnu » — un seul "
                    f"gabarit de refus, code {seconde.statut}, hors identifiant de "
                    "correlation"
                )

            #  LE JETON NE DOIT PAS FIGURER DANS LA REPONSE DE REFUS.
            controles += 1
            if jeton_livre.encode("utf-8") in seconde.corps:
                print("    ECHEC    le refus RECOPIE le jeton dans son corps")
                echecs += 1
            else:
                print("    ok       le refus ne cite ni le jeton ni son empreinte")

        #  --------------------------------------------------------------
        #  10. LES JOURNAUX DE CADDY — une absence, GARDEE
        #  --------------------------------------------------------------
        controles += 1
        journalise, anomalies = _journalisation_de_caddy()
        if anomalies:
            for anomalie in anomalies:
                print(f"    ECHEC    {anomalie}")
            echecs += 1
        elif journalise:
            print("    ok       Caddy journalise les acces, et la chaine de requete est filtree")
        else:
            #  RAPPORTE, non affirme comme une protection. §7.20.
            print("    ok       aucun journal d'acces declare dans un bloc de site Caddy")
            print("             LE JETON N'Y FIGURE DONC PAS — mais c'est une ABSENCE,")
            print("             pas une protection : le bloc global `log` configure le")
            print("             journal PROPRE de Caddy, pas les acces. Ce controle")
            print("             ECHOUERA le jour ou un bloc de site en declarera un")
            print("             sans filtrer la chaine de requete. §7.23.")

        controles += 1
        journaux_caddy = subprocess.run(  # noqa: S603
            [*compose, "logs", "--no-log-prefix", "--tail", "600", "caddy"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte_caddy = journaux_caddy.stdout + journaux_caddy.stderr
        if "oml_" in texte_caddy:
            print("    ECHEC    un jeton `oml_` figure dans les journaux de Caddy")
            echecs += 1
        else:
            print(
                f"    ok       aucun `oml_` dans les {len(texte_caddy.splitlines())} "
                "dernieres lignes de journal de caddy"
            )

        #  --------------------------------------------------------------
        #  11. LES DUREES — MESUREES ET RAPPORTEES, JAMAIS EXIGEES
        #  --------------------------------------------------------------
        #
        #  LA PREMIERE VERSION DE CETTE MESURE NE VALAIT RIEN, ET C'EST LA
        #  SIXIEME PROPOSITION DU §7.0 : elle comparait UNE requete a UNE autre,
        #  et la premiere payait l'ouverture du pool de connexions SQLAlchemy.
        #  Elle annoncait 95 ms contre 22 ms, soit un facteur quatre qui mesurait
        #  surtout l'ordre des appels. **Les deux nombres ne mesuraient pas la
        #  meme grandeur.**
        #
        #  La mesure est donc ENTRELACEE -- connue, inconnue, connue, inconnue --
        #  apres un tour de chauffe jete, et c'est la MEDIANE qui est rapportee.
        #  Une mediane sur des tours entrelaces elimine a la fois la chauffe et
        #  une derive lente de la machine.
        for _ in range(2):
            appeler(arguments.base, json.dumps({"email": connue}).encode("utf-8"), contexte)
            appeler(arguments.base, json.dumps({"email": inconnue}).encode("utf-8"), contexte)

        tours = 9
        durees: dict[str, list[float]] = {"connue": [], "inconnue": []}
        for _ in range(tours):
            durees["connue"].append(
                appeler(
                    arguments.base, json.dumps({"email": connue}).encode("utf-8"), contexte
                ).duree_ms
            )
            durees["inconnue"].append(
                appeler(
                    arguments.base, json.dumps({"email": inconnue}).encode("utf-8"), contexte
                ).duree_ms
            )

        def mediane(valeurs: list[float]) -> float:
            triees = sorted(valeurs)
            return triees[len(triees) // 2]

        m_connue = mediane(durees["connue"])
        m_inconnue = mediane(durees["inconnue"])
        ecart = m_connue - m_inconnue
        print()
        print(f"    info     durees, MEDIANE de {tours} tours entrelaces apres chauffe :")
        print(
            f"             connue {m_connue:.1f} ms "
            f"(min {min(durees['connue']):.1f}, max {max(durees['connue']):.1f}) · "
            f"inconnue {m_inconnue:.1f} ms "
            f"(min {min(durees['inconnue']):.1f}, max {max(durees['inconnue']):.1f})"
        )
        print(f"             ecart median : {ecart:+.1f} ms")
        print("             l'envoi SMTP a lieu APRES la reponse : il n'entre pas")
        print("             dans ces durees. Le residuel est le surcout des requetes")
        print("             SQL du chemin connu — 4 requetes de plus.")
        print("             CE RESIDUEL N'EST PAS FERME. Il n'est pas exige nul ici :")
        print("             l'exiger produirait un controle intermittent, ce qui est")
        print("             pire qu'un residuel nomme. A reexaminer en `T8`.")

    finally:
        _nettoyer(compose, env)

    print()
    print(f"  controles executes : {controles}   echecs : {echecs}")
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print("  --> la reponse est identique — corps, code et en-tetes — connue ou non")
    return 0


def _nettoyer(compose: list[str], env: dict[str, str]) -> None:
    """Retirer TOUT ce que ce controle a cree, et rien d'autre.

    L'ordre suit les cles etrangeres. Le filtre est le marqueur unique de cette
    execution : aucune ligne du jeu de recette ni du travail de quiconque n'est
    touchee.
    """
    etapes = (
        f"DELETE FROM auth_event WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{MARQUEUR}%')",
        f"DELETE FROM magic_link_request WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{MARQUEUR}%')",
        f"DELETE FROM entity_membership WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{MARQUEUR}%')",
        f"DELETE FROM person WHERE email_normalized LIKE '{MARQUEUR}%'",  # noqa: S608
        f"DELETE FROM entity WHERE code = '{MARQUEUR}'",  # noqa: S608
        #  Les evenements SANS personne — adresse inconnue en `T3`, jeton
        #  inconnu en `T4` — ne peuvent pas etre rattaches au marqueur : ils n'ont
        #  ni personne, ni adresse.
        #
        #  **CETTE REQUETE NOMMAIT `MAGIC_LINK_REQUESTED`, ET ELLE A VIEILLI AU
        #  PREMIER AJOUT.** `T4` ecrit des `LOGIN_FAILURE` sans personne, que ce
        #  filtre ne voyait pas : deux lignes restaient a chaque execution, et
        #  c'est `T5` qui l'a mesure. §7.27 -- une liste nommee dans un controle
        #  vieillit des qu'on y ajoute quelque chose. Le type n'est donc plus
        #  nomme : seule la borne temporelle delimite, et elle ne vieillit pas.
        "DELETE FROM auth_event WHERE person_id IS NULL "
        "  AND occurred_at > now() - interval '5 minutes'",
    )
    restes = 0
    for requete in etapes:
        code, sortie = psql(compose, env, requete)
        if code:
            restes += 1
            print(f"    SIGNALE  nettoyage incomplet : {sortie[:160]}")

    #  Les messages de Mailpit aussi : laisser derriere soi des e-mails portant un
    #  jeton serait laisser en clair le secret dont ce controle verifie l'absence
    #  ailleurs.
    #
    #  MA PREMIERE VERSION EN SUPPRIMAIT ZERO, ET ANNONCAIT « 0 supprime(s) ».
    #  Elle appelait `DELETE /api/v1/message/<id>`, qui n'existe pas : Mailpit
    #  attend `DELETE /api/v1/messages` avec les identifiants EN CORPS. Chaque
    #  appel rendait 404, la fonction rendait `None`, et le compte restait a zero
    #  -- indistinguable de « il n'y avait rien a supprimer ». Defaut `T3-5`, et
    #  c'est la quatrieme proposition du §7.0 dans un nettoyage.
    trouves = _mailpit(env, f"/api/v1/search?query={urllib.parse.quote(f'to:{MARQUEUR}')}")
    a_supprimer = [message["ID"] for message in (trouves or {}).get("messages", [])]
    supprimes = 0
    if a_supprimer:
        reponse = _mailpit(
            env,
            "/api/v1/messages",
            methode="DELETE",
            charge=json.dumps({"IDs": a_supprimer}).encode("utf-8"),
        )
        supprimes = len(a_supprimer) if reponse is not None else 0

    #  LE COMPTE EST CONFRONTE A CE QUI A ETE TROUVE : « 0 supprime » ne doit pas
    #  pouvoir signifier deux choses.
    if a_supprimer and supprimes != len(a_supprimer):
        print(
            f"    SIGNALE  {len(a_supprimer)} message(s) Mailpit trouve(s), "
            f"{supprimes} supprime(s) — des jetons subsistent dans Mailpit"
        )
        restes += 1
    if not restes:
        print(
            f"    ok       nettoyage — lignes `{MARQUEUR}` retirees, "
            f"{supprimes} message(s) Mailpit supprime(s) sur {len(a_supprimer)} trouve(s)"
        )


if __name__ == "__main__":
    sys.exit(main())
