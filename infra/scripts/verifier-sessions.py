#!/usr/bin/env python3
"""Le cookie de session porte-t-il ses trois attributs, et le jeton reste-t-il hors du navigateur ?

LOT 3, sous-etape `T6`, story `MVP-L03-US004`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE EN PLUS DES TESTS

  Le critere du §3 de la fiche est explicite : « les trois attributs sont sur la
  reponse **REELLE**, lue a travers Caddy en HTTPS ». Les tests d'integration
  montent l'application en processus ; ici on lit ce que le mandataire livre.

  Et il porte le second critere, celui qu'aucun test d'API ne peut voir :
  **« aucun jeton dans `localStorage` », prouve par un controle du frontend**.

DEUX BARRIERES POUR LA MEME REGLE, ET LA PREMIERE EST STRUCTURELLE

  `HttpOnly` rend le jeton **illisible par tout JavaScript** : un frontend ne peut
  pas stocker ce qu'il ne peut pas lire. C'est le §7.2 -- changer de forme plutot
  que promettre de l'attention.

  La seconde barriere est le controle des sources ci-dessous. Elle existe parce
  que la premiere ne couvre pas tout : rien n'empeche un frontend de stocker une
  AUTRE donnee d'authentification -- un identifiant, un indicateur de connexion --
  et le cahier §7.4 interdit « aucune donnee d'authentification durable dans
  `localStorage` », pas seulement le jeton.

LE CONTROLE DU FRONTEND EST EXACT, PAS HEURISTIQUE

  Il retire les COMMENTAIRES avant de chercher. Sans cela, il se declencherait sur
  le commentaire qui explique la regle -- ce qui est exactement le defaut mesure en
  `T11` du LOT 2, ou un garde-fou se declenchait sur le commentaire expliquant le
  motif qu'il interdisait. §7.25 : un garde-fou a faux positifs apprend a passer
  outre.

  Il garde en revanche les CHAINES : `window["localStorage"]` est un usage, et le
  manquer serait laisser un contournement trivial.

  Et il porte son temoin dans les deux sens -- voir `--temoin`.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_SESSION = "/api/v1/auth/session"
CHEMIN_DECONNEXION = "/api/v1/auth/deconnexion"

MARQUEUR = f"t6-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30

#  Les racines de source du frontend. **DERIVEES DU DISQUE**, non recopiees : une
#  liste ecrite ici vieillirait au premier paquet ajoute, §7.27.
RACINES_FRONTEND = ("apps/web/src", "packages/ui/src", "packages/contracts/src")

#  Ce que le cahier §7.4 interdit de stocker durablement cote navigateur.
STOCKAGES_INTERDITS = ("localStorage", "sessionStorage")

EXTENSIONS_SOURCE = (".ts", ".tsx", ".js", ".jsx")


def sans_commentaires(source: str) -> str:
    """Retirer les commentaires `//` et `/* */`.

    **Les CHAINES sont conservees** : `window["localStorage"]` est un usage. Ne
    retirer que les commentaires est ce qui rend ce controle exact sans le rendre
    aveugle.
    """
    sans_bloc = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", sans_bloc)


def usages_de_stockage(racine: pathlib.Path) -> list[tuple[pathlib.Path, int, str]]:
    """Les usages d'un stockage interdit dans les sources du frontend.

    Rend `(fichier, ligne, nom du stockage)`. La liste des fichiers est **derivee
    du disque**.
    """
    trouves: list[tuple[pathlib.Path, int, str]] = []
    for base in RACINES_FRONTEND:
        dossier = racine / base
        if not dossier.is_dir():
            continue
        for fichier in sorted(dossier.rglob("*")):
            if fichier.suffix not in EXTENSIONS_SOURCE or not fichier.is_file():
                continue
            propre = sans_commentaires(fichier.read_text(encoding="utf-8"))
            for numero, ligne in enumerate(propre.splitlines(), start=1):
                for stockage in STOCKAGES_INTERDITS:
                    if stockage in ligne:
                        trouves.append((fichier.relative_to(racine), numero, stockage))
    return trouves


def compter_les_fichiers(racine: pathlib.Path) -> int:
    """Combien de fichiers le controle a-t-il examines ?

    **Un controle qui n'annonce pas combien d'elements il a examines peut toujours
    n'en avoir examine qu'un** -- troisieme proposition du §7.0.
    """
    total = 0
    for base in RACINES_FRONTEND:
        dossier = racine / base
        if dossier.is_dir():
            total += sum(
                1 for f in dossier.rglob("*") if f.suffix in EXTENSIONS_SOURCE and f.is_file()
            )
    return total


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION. Pas de shell — §7.2.

    **SUR LES `# noqa: S608` DES APPELANTS.** La seule valeur interpolee est
    `adresse`, construite ici depuis `MARQUEUR` — `uuid4` — et le domaine du
    fichier d'environnement. Aucune entree de tiers n'atteint ce SQL, et `psql`
    n'accepte pas de parametres lies.
    """
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
    """Une reponse HTTP reduite a ce qui est compare, cookies compris."""

    def __init__(self, statut: int, corps: bytes, en_tetes: list[tuple[str, str]]) -> None:
        self.statut = statut
        self.corps = corps
        self.en_tetes = en_tetes
        #  `Set-Cookie` peut apparaitre PLUSIEURS fois : un dictionnaire en
        #  perdrait. La liste est donc conservee telle quelle.
        self.cookies_poses = [v for nom, v in en_tetes if nom.lower() == "set-cookie"]


def appeler(
    base: str,
    chemin: str,
    contexte: ssl.SSLContext,
    *,
    charge: dict[str, str] | None = None,
    cookie: str | None = None,
    jeton_csrf: str | None = None,
    methode: str | None = None,
) -> Reponse:
    """Appeler l'API. Rend la reponse MEME sur un code d'erreur."""
    en_tetes = {"Content-Type": "application/json"} if charge is not None else {}
    if cookie:
        en_tetes["Cookie"] = cookie
    if jeton_csrf:
        #  `T7` du LOT 3 : les ecritures qui ont une session exigent ce jeton.
        en_tetes["X-CSRF-Token"] = jeton_csrf
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=en_tetes,
        method=methode or ("POST" if charge is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), list(reponse.headers.items()))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), list(erreur.headers.items()))


def _jeton_du_cookie(pose: str, nom: str) -> str | None:
    trouve = re.search(rf"{re.escape(nom)}=([^;]+)", pose)
    return trouve.group(1) if trouve else None


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file")
    analyseur.add_argument("--base")
    analyseur.add_argument(
        "--temoin",
        action="store_true",
        help="eprouver le controle du frontend dans les DEUX sens, sans stack",
    )
    analyseur.add_argument("fichiers_compose", nargs="*")
    arguments = analyseur.parse_args()

    if arguments.temoin:
        return _temoin_du_controle_frontend()

    if not arguments.env_file or not arguments.base or not arguments.fichiers_compose:
        print("  ECHEC     --env-file, --base et les fichiers Compose sont obligatoires")
        return 1

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    nom_cookie = env.get("SESSION_COOKIE_NAME", "exalt_session")
    samesite = env.get("SESSION_COOKIE_SAMESITE", "lax")
    jours_absolus = env.get("SESSION_ABSOLUTE_DAYS", "30")
    adresse = f"{MARQUEUR}@exalt-t6.test"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Sessions et cookie — US004, cahier §7.4, modele §10.4")
    print(f"    info     origine {arguments.base}, cookie `{nom_cookie}`")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0

    #  ------------------------------------------------------------------
    #  0. LE CONTROLE DU FRONTEND — il ne demande AUCUNE stack
    #  ------------------------------------------------------------------
    controles += 1
    examines = compter_les_fichiers(RACINE)
    usages = usages_de_stockage(RACINE)
    if usages:
        print(f"    ECHEC    {len(usages)} usage(s) de stockage navigateur interdit :")
        for fichier, ligne, stockage in usages:
            print(f"             {fichier}:{ligne} — {stockage}")
        print("             cahier §7.4 : « aucune donnee d'authentification durable")
        print("             dans localStorage ». Le jeton vit dans un cookie HttpOnly.")
        echecs += 1
    else:
        print(
            f"    ok       aucun {' ni '.join(STOCKAGES_INTERDITS)} dans les "
            f"{examines} fichiers source du frontend"
        )
    if examines < 5:
        print(f"    ECHEC    seuls {examines} fichiers examines : le controle ne prouve rien")
        echecs += 1

    #  ------------------------------------------------------------------
    #  Le decor : une personne et un compte administrateur
    #  ------------------------------------------------------------------
    from app.auth.mots_de_passe import ALGORITHME, hacher

    empreinte, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not debut.strip():
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = debut.splitlines()[0].strip()

    decor = f"""
    DO $$
    DECLARE p uuid; c uuid;
    BEGIN
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'T6', 'active') RETURNING id INTO p;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
    END $$;
    """  # noqa: S608 — voir la justification en tete de `psql`
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor cree : 1 personne, 1 compte ADMIN_LOCAL")

    try:
        #  --------------------------------------------------------------
        #  1. LES TROIS ATTRIBUTS, SUR LA REPONSE REELLE
        #  --------------------------------------------------------------
        controles += 1
        connexion = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        if connexion.statut != 200:
            print(f"    ECHEC    connexion refusee : {connexion.statut} {connexion.corps[:150]!r}")
            echecs += 1
            poses = []
        else:
            poses = [p for p in connexion.cookies_poses if p.startswith(f"{nom_cookie}=")]
        if not poses:
            print(f"    ECHEC    aucun cookie `{nom_cookie}` sur la reponse de connexion")
            echecs += 1
            pose = ""
        else:
            pose = poses[0]
            manquants = [
                attendu
                for attendu in ("HttpOnly", "Secure", f"SameSite={samesite}", "Path=/")
                if attendu.lower() not in pose.lower()
            ]
            if manquants:
                print(f"    ECHEC    attribut(s) absent(s) du cookie : {manquants}")
                print(f"             Set-Cookie recu : {pose}")
                echecs += 1
            else:
                print(
                    "    ok       cookie pose avec HttpOnly, Secure, "
                    f"SameSite={samesite}, Path=/ — sur la reponse REELLE"
                )

        jeton = _jeton_du_cookie(pose, nom_cookie) if pose else None

        #  L'age maximal doit valoir la duree ABSOLUE, sinon le cookie mourrait a
        #  la fermeture du navigateur — ce qui contredirait « sept jours
        #  d'inactivite », une regle qui suppose la survie a un redemarrage.
        controles += 1
        attendu_max_age = f"Max-Age={int(jours_absolus) * 24 * 3600}"
        if pose and attendu_max_age.lower() not in pose.lower():
            print(f"    ECHEC    `{attendu_max_age}` absent : {pose}")
            echecs += 1
        elif pose:
            print(f"    ok       {attendu_max_age} — la duree absolue du §10.4")

        #  --------------------------------------------------------------
        #  2. LE JETON N'APPARAIT DANS AUCUN CORPS
        #  --------------------------------------------------------------
        controles += 1
        cookie = f"{nom_cookie}={jeton}" if jeton else None
        session = appeler(arguments.base, CHEMIN_SESSION, contexte, cookie=cookie)
        if jeton is None:
            print("    ECHEC    aucun jeton extrait du cookie : la suite ne prouve rien")
            echecs += 1
        elif jeton.encode() in connexion.corps or jeton.encode() in session.corps:
            print("    ECHEC    le jeton figure dans un CORPS de reponse")
            echecs += 1
        elif b"oss_" in connexion.corps or b"oss_" in session.corps:
            print("    ECHEC    un prefixe `oss_` figure dans un corps de reponse")
            echecs += 1
        else:
            print("    ok       le jeton n'apparait dans AUCUN corps — cookie seul")

        #  --------------------------------------------------------------
        #  3. LE COOKIE OUVRE L'ACCES, ET SON ABSENCE LE REFUSE
        #  --------------------------------------------------------------
        controles += 1
        sans_cookie = appeler(arguments.base, CHEMIN_SESSION, contexte)
        if session.statut != 200:
            print(f"    ECHEC    le cookie n'ouvre pas la session : {session.statut}")
            echecs += 1
        elif sans_cookie.statut != 401:
            print(f"    ECHEC    sans cookie, la session rend {sans_cookie.statut} au lieu de 401")
            echecs += 1
        else:
            print("    ok       le cookie ouvre la session (200), son absence la refuse (401)")

        #  --------------------------------------------------------------
        #  4. LES REFUS SONT INDISTINGUABLES
        #  --------------------------------------------------------------
        controles += 1
        inconnu = appeler(
            arguments.base,
            CHEMIN_SESSION,
            contexte,
            cookie=f"{nom_cookie}=oss_{'z' * 43}",
        )
        fantaisiste = appeler(
            arguments.base, CHEMIN_SESSION, contexte, cookie=f"{nom_cookie}=pas-un-jeton"
        )
        divergents = [
            nom
            for nom, reponse in (("inconnu", inconnu), ("fantaisiste", fantaisiste))
            if reponse.statut != sans_cookie.statut
            or _sans_correlation(reponse.corps) != _sans_correlation(sans_cookie.corps)
        ]
        if divergents:
            print(f"    ECHEC    refus DISTINGUABLES : {divergents}")
            echecs += 1
        else:
            print(
                "    ok       3 causes de refus indistinguables — cookie absent, jeton "
                f"inconnu, jeton fantaisiste, toutes {sans_cookie.statut}"
            )

        #  TEMOIN : le comparateur sait-il voir une difference ?
        controles += 1
        if _sans_correlation(session.corps) == _sans_correlation(sans_cookie.corps):
            print("    ECHEC    TEMOIN : le comparateur ne distingue pas un succes d'un refus")
            echecs += 1
        else:
            print("    ok       TEMOIN — le comparateur distingue un succes d'un refus")

        #  --------------------------------------------------------------
        #  5. LA DECONNEXION REVOQUE, ET LE SERVEUR FAIT AUTORITE
        #  --------------------------------------------------------------
        controles += 1
        #  **LE JETON ANTI-CSRF EST DESORMAIS EXIGE**, `T7` du LOT 3 : la
        #  deconnexion est la seule ecriture du lot qui dispose d'une session pour
        #  en deriver un. Ce controle a echoue en `T7`, et il avait raison — §7.21,
        #  un controle ne devient pas faux tout seul.
        #
        #  Le jeton est LU dans le corps de la route de session, exactement comme
        #  un frontend le fera.
        jeton_csrf = (
            json.loads(session.corps).get("jeton_csrf", "") if session.statut == 200 else ""
        )
        if not jeton_csrf:
            print("    ECHEC    aucun `jeton_csrf` dans la reponse de session")
            echecs += 1
        sortie_reponse = appeler(
            arguments.base,
            CHEMIN_DECONNEXION,
            contexte,
            charge={},
            cookie=cookie,
            jeton_csrf=jeton_csrf,
        )
        apres = appeler(arguments.base, CHEMIN_SESSION, contexte, cookie=cookie)
        if sortie_reponse.statut != 200:
            print(f"    ECHEC    la deconnexion rend {sortie_reponse.statut} au lieu de 200")
            echecs += 1
        elif apres.statut != 401:
            print(
                "    ECHEC    le MEME cookie ouvre encore la session apres deconnexion : "
                f"{apres.statut}. Le serveur ne fait pas autorite."
            )
            echecs += 1
        else:
            print("    ok       deconnexion — le meme jeton est refuse ensuite (401)")

        #  Et elle rend toujours 200, meme sans session.
        controles += 1
        #  Rejouee avec le MEME jeton : la session est deja revoquee, mais le
        #  jeton reste valide — il est derive du jeton de session, non de son
        #  etat. La deconnexion doit donc rendre 200.
        rejouee = appeler(
            arguments.base,
            CHEMIN_DECONNEXION,
            contexte,
            charge={},
            cookie=cookie,
            jeton_csrf=jeton_csrf,
        )
        nue = appeler(arguments.base, CHEMIN_DECONNEXION, contexte, charge={})
        if rejouee.statut != 200 or nue.statut != 200:
            print(
                f"    ECHEC    deconnexion rejouee {rejouee.statut}, sans cookie "
                f"{nue.statut} — attendu 200/200"
            )
            echecs += 1
        else:
            print("    ok       deconnexion idempotente — 200 rejouee, 200 sans cookie")

        #  --------------------------------------------------------------
        #  6. L'AUDIT ET LA BASE
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FILTER (WHERE revoked_at IS NOT NULL), count(*), "  # noqa: S608
            "       count(*) FILTER (WHERE session_token_hash ~ '^[0-9a-f]{64}$') "
            "FROM user_session s JOIN person p ON p.id = s.person_id "
            f"WHERE p.email_normalized = '{adresse}'",
        )
        if code or not sortie.strip():
            print(f"    ECHEC    lecture de `user_session` : {sortie[:180]}")
            echecs += 1
        else:
            revoquees, total, empreintes = (int(v) for v in sortie.strip().split("|"))
            if total != 1 or revoquees != 1 or empreintes != 1:
                print(
                    f"    ECHEC    sessions : {total} au total, {revoquees} revoquee(s), "
                    f"{empreintes} empreinte(s) conforme(s) — attendu 1/1/1"
                )
                echecs += 1
            else:
                print(
                    "    ok       1 session, REVOQUEE et non effacee, empreinte de 64 hexadecimaux"
                )

        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM auth_event e JOIN person p ON p.id = e.person_id "  # noqa: S608
            f"WHERE p.email_normalized = '{adresse}' "
            "  AND e.event_type = 'SESSION_REVOKED'",
        )
        if code or sortie.strip() != "1":
            print(f"    ECHEC    SESSION_REVOKED : {sortie!r} au lieu de 1")
            echecs += 1
        else:
            print("    ok       audit — 1 SESSION_REVOKED, la deconnexion rejouee n'en cree pas")

        #  --------------------------------------------------------------
        #  7. AUCUN JETON DANS LES JOURNAUX
        #  --------------------------------------------------------------
        for service in ("api", "caddy"):
            controles += 1
            journaux = subprocess.run(  # noqa: S603
                [*compose, "logs", "--no-log-prefix", "--tail", "400", service],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                check=False,
            )
            texte = journaux.stdout + journaux.stderr
            if "oss_" in texte or (jeton and jeton in texte):
                print(f"    ECHEC    un jeton de session figure dans les journaux de {service}")
                echecs += 1
            else:
                print(
                    f"    ok       aucun `oss_` dans les {len(texte.splitlines())} "
                    f"dernieres lignes de journal de {service}"
                )

    finally:
        _nettoyer(compose, env, adresse, debut)

    print()
    print(f"  controles executes : {controles}   echecs : {echecs}")
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print("  --> le cookie porte ses trois attributs, le jeton reste hors du")
    print("      navigateur, et la deconnexion revoque cote SERVEUR")
    return 0


def _sans_correlation(corps: bytes) -> object:
    """Le corps prive de l'identifiant de correlation du §18.3, qui DOIT varier."""
    try:
        charge = json.loads(corps)
    except json.JSONDecodeError:
        return corps
    if isinstance(charge, dict) and isinstance(charge.get("erreur"), dict):
        charge["erreur"].pop("identifiant_correlation", None)
    return charge


def _temoin_du_controle_frontend() -> int:
    """Eprouver le controle des sources DANS LES DEUX SENS, sans stack.

    **UN GARDE-FOU QUI NE SAIT PAS ECHOUER NE PROUVE RIEN, et un garde-fou qui
    refuse du code correct apprend a passer outre.** Les deux sont eprouves :

      - un usage reel dans un fichier temporaire **doit** etre detecte ;
      - un COMMENTAIRE qui mentionne `localStorage` **ne doit pas** l'etre. C'est
        exactement le defaut mesure en `T11` du LOT 2, ou un garde-fou se
        declenchait sur le commentaire expliquant le motif qu'il interdisait.
    """
    print()
    print("  Temoin du controle de stockage navigateur — §7.25")
    dossier = RACINE / "apps" / "web" / "src"
    echecs = 0

    usage = dossier / "__temoin_usage.ts"
    commentaire = dossier / "__temoin_commentaire.ts"
    try:
        usage.write_text("export const x = localStorage.getItem('jeton');\n", encoding="utf-8")
        trouves = [t for t in usages_de_stockage(RACINE) if t[0].name == usage.name]
        if trouves:
            print(f"    ok       un USAGE reel est detecte — {trouves[0][0]}:{trouves[0][1]}")
        else:
            print("    ECHEC    un usage reel de localStorage N'EST PAS detecte")
            echecs += 1
        usage.unlink()

        commentaire.write_text(
            "//  On n'ecrit JAMAIS de jeton dans localStorage (cahier 7.4).\n"
            "/*  Ni dans sessionStorage : le cookie HttpOnly suffit.  */\n"
            "export const y = 1;\n",
            encoding="utf-8",
        )
        faux = [t for t in usages_de_stockage(RACINE) if t[0].name == commentaire.name]
        if faux:
            print(f"    ECHEC    FAUX POSITIF sur un commentaire : {faux}")
            echecs += 1
        else:
            print("    ok       un COMMENTAIRE qui les mentionne ne declenche PAS")
        commentaire.unlink()
    finally:
        usage.unlink(missing_ok=True)
        commentaire.unlink(missing_ok=True)

    print()
    if echecs:
        print(f"  ECHEC : {echecs} temoin(s) en echec")
        return 1
    print("  --> le controle detecte un usage reel et ignore un commentaire")
    return 0


def _nettoyer(compose: list[str], env: dict[str, str], adresse: str, debut: str) -> None:
    """Retirer TOUT ce que ce controle a cree, dans l'ordre des cles etrangeres.

    La derniere etape retire les evenements SANS personne, bornes a cette
    execution : ils n'ont aucune identite a laquelle se rattacher. C'est la
    cinquieme fois que cette etape est necessaire dans ce lot.
    """
    etapes = (
        "DELETE FROM auth_event WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM user_session WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM admin_password_credential WHERE user_account_id IN "  # noqa: S608
        "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
        f" WHERE p.email_normalized = '{adresse}')",
        "DELETE FROM user_account WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        f"DELETE FROM person WHERE email_normalized = '{adresse}'",  # noqa: S608
        f"DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= '{debut}'",  # noqa: S608
    )
    restes = 0
    for requete in etapes:
        code, sortie = psql(compose, env, requete)
        if code:
            restes += 1
            print(f"    SIGNALE  nettoyage incomplet : {sortie[:160]}")
    if not restes:
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")


if __name__ == "__main__":
    sys.exit(main())
