#!/usr/bin/env python3
"""Le trombinoscope pagine, servi A TRAVERS CADDY.

LOT 5, sous-etape `T2`, story `MVP-L05-US001`.

CE QUE CE CONTROLE PROUVE QUE LES TESTS NE PROUVENT PAS

  Les tests d'integration montent l'application EN PROCESSUS. Ici la session est
  ouverte par une **vraie connexion a travers Caddy en HTTPS**, et chaque page est
  lue par un **aller-retour HTTP reel** sur l'API du conteneur -- §7.28.

  Et il exige que le conteneur porte le code du depot : lance
  `make code-refresh && make code-check` avant, sinon il eprouve un autre
  artefact **en paraissant sain**.

LE CONTROLE QUI COMPTE LE PLUS EST LE TEMOIN DES TROIS TAILLES

  Ma premiere version de la route typait `taille` en `Literal[25, 50, 100]`.
  Un parametre d'URL arrive TOUJOURS en chaine, et Pydantic REFUSE « 25 » contre
  un `Literal` d'entiers : la route refusait donc **les trois tailles valides**
  des qu'elles etaient ecrites dans l'URL.

  **Les huit epreuves de refus passaient toutes** -- elles demandaient un refus,
  et elles l'obtenaient, pour la mauvaise raison. Seul le temoin qui exige que
  25, 50 et 100 SOIENT servies distingue les deux situations. C'est la troisieme
  proposition du §7.0, et c'est le defaut `T2-3`.

LA PAGINATION EST PROUVEE PAR RECOMPOSITION, PAS PAR COMPTAGE

  Compter 25 lignes sur une page ne prouve rien : un ordre non total rend le meme
  compte tout en repetant des lignes et en en sautant d'autres -- les deux
  observations sont identiques. Le controle parcourt donc TOUTES les pages,
  concatene, et exige que la concatenation porte chaque identifiant une fois et
  une seule. Le decor contient des HOMONYMES : sans le tri par cle primaire, ce
  controle echoue.

SES AUTRES TEMOINS

  - **la connexion REUSSIT et pose un cookie** : sans lui, un cookie casse
    donnerait la meme observation qu'un filtrage correct -- une liste vide ;
  - **une ligne publiee et active EST rendue** : sans elle, les cinq exclusions
    seraient satisfaites par une route qui ne rend jamais rien ;
  - **`departed` et `archived` gardent `published`**, et c'est ce qui rend
    l'epreuve discriminante : le §22.5 etape 5 « masquage du profil » n'est
    implemente nulle part, donc c'est l'etat REEL de la base apres un depart ;
  - **les deux refus 404 sont COMPARES**, corps et en-tetes, correlation FIXEE.

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
CHEMIN_UNE_ENTITE = "/api/v1/entities/{code}"

MARQUEUR = f"t2l5-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30
CORRELATION_FIXE = "l5t2-egalite-des-refus"

#  **LES HUIT CHAMPS D'UNE LIGNE, ET `photo` EST ARRIVE EN `T5`.**
#
#  Ce contrôle a échoué au moment où `T5` a ajouté le champ, sur un livrable
#  pourtant conforme. C'est son objet : « ni plus ni moins » rend toute addition
#  visible en revue. La bonne réaction est de mettre l'attendu à jour **parce que
#  l'addition est voulue** (`DEC-564`), non de comparer par inclusion.
CHAMPS_LIGNE = frozenset(
    {
        "id",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "professional_category",
        "arrival_date",
        "photo",
    }
)
CHAMPS_ENVELOPPE = frozenset({"collaborateurs", "page", "taille", "total", "pages"})

#  Soixante lignes : trois pages a 25, deux a 50, une a 100. Le volume est le
#  point -- une pagination ne se prouve pas sur trois lignes (§7.26).
VOLUME = 60

#  Les six lignes du decor d'exclusion. `departed` et `archived` gardent
#  `published` A DESSEIN : voir l'en-tete.
EXCLUSIONS: tuple[tuple[str, str, str], ...] = (
    #  **UN ACCENT DANS LE NOM, ET C'EST DELIBERE** : sans lui, une recherche qui
    #  ignorerait la casse mais PAS les accents rendrait la meme observation
    #  qu'une recherche correcte (LOT 5, `T3`).
    ("zzélodie", "active", "published"),
    ("zzvisible", "active", "published"),
    ("zzbrouillon", "active", "draft"),
    ("zzmasque", "active", "hidden"),
    ("zzfuture", "future", "published"),
    ("zzpartie", "departed", "published"),
    ("zzarchivee", "archived", "published"),
)

#  Le seul en-tete qui ne peut pas etre egal, et il est NOMME en sortie : a
#  travers Caddy, une reponse porte un `date` qui change d'une requete a
#  l'autre. Lui faire dire le vrai plutot que de l'affaiblir -- §7.20.
EN_TETES_NON_COMPARABLES = frozenset({"date"})


def listables() -> list[str]:
    """Les noms du decor que la route doit rendre — DERIVES, jamais recopies.

    Ajouter une ligne aux `EXCLUSIONS` sans toucher ici ferait echouer tous les
    comptes ; les deriver supprime la question (§7.27). C'est ce qui s'est passe
    quand `T3` a ajoute `zzelodie` : quatre controles ont echoue d'un coup.
    """
    return [
        nom for nom, etat, visibilite in EXCLUSIONS if (etat, visibilite) == ("active", "published")
    ]


def attendu_total() -> int:
    """Le volume plus les lignes listables du decor d'exclusions."""
    return VOLUME + len(listables())


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
    """Le bloc SQL du decor : une entite, un admin local, six exclusions, VOLUME lignes.

    S608 : les seules valeurs interpolees sont `MARQUEUR`, un `uuid4` de ce
    module, et les libelles d'etat, qui viennent de constantes de ce fichier.
    `psql` n'accepte pas de parametre lie dans un bloc `DO`.

    **LES HOMONYMES SONT VOLONTAIRES** : les `VOLUME` lignes se partagent sept
    noms de famille, si bien que le tri par nom et prenom ne suffit pas a les
    ordonner. Sans le troisieme critere -- la cle primaire -- la recomposition
    des pages echoue.
    """
    exclusions = "\n".join(
        f"      INSERT INTO person (email, email_normalized, first_name, last_name, "  # noqa: S608
        f"account_state) VALUES ('{marqueur}-{nom}@x.test', '{marqueur}-{nom}@x.test', "
        f"'Ada', '{nom}', 'active') RETURNING id INTO p;\n"
        f"      INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
        f"departure_date, membership_state, professional_category, profile_visibility) "
        f"VALUES (p, e, DATE '2026-01-15', "
        f"{'DATE ' + chr(39) + '2026-06-30' + chr(39) if etat == 'departed' else 'NULL'}, "
        f"'{etat}', 'consultant', '{visibilite}');"
        for nom, etat, visibilite in EXCLUSIONS
    )
    volume = "\n".join(
        f"      INSERT INTO person (email, email_normalized, first_name, last_name, "  # noqa: S608
        f"account_state) VALUES ('{marqueur}-v{rang:03d}@x.test', "
        f"'{marqueur}-v{rang:03d}@x.test', 'p{rang:03d}', 'nom{rang % 7:02d}', 'active') "
        f"RETURNING id INTO p;\n"
        f"      INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
        f"membership_state, professional_category, profile_visibility) "
        f"VALUES (p, e, DATE '2026-01-15', 'active', 'consultant', 'published');"
        for rang in range(VOLUME)
    )
    return f"""
    DO $$
    DECLARE p uuid; e uuid; c uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{code_entite}', 'Entite {marqueur}', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;

      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{adresse}', '{adresse}', 'Verif', 'L5T2', 'active') RETURNING id INTO p;
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte}', '{algo}', '{parametres_hachage}'::jsonb, now(), FALSE);

{exclusions}
{volume}
    END $$;
    """  # noqa: S608


def nettoyer(compose: list[str], env: dict[str, str], marqueur: str, debut: str) -> None:
    """L'ordre suit les cles etrangeres, et la borne temporelle attrape le reste."""
    for requete in (
        "DELETE FROM auth_event WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{marqueur}%')",
        "DELETE FROM user_session WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{marqueur}%')",
        "DELETE FROM admin_password_credential WHERE user_account_id IN "  # noqa: S608
        "(SELECT id FROM user_account WHERE person_id IN "
        f"(SELECT id FROM person WHERE email_normalized LIKE '{marqueur}%'))",
        "DELETE FROM user_account WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{marqueur}%')",
        #  AVANT `person` et AVANT `entity` : elle reference les deux.
        "DELETE FROM entity_membership WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized LIKE '{marqueur}%')",
        f"DELETE FROM person WHERE email_normalized LIKE '{marqueur}%'",  # noqa: S608
        f"DELETE FROM entity WHERE code LIKE '{marqueur}%'",  # noqa: S608
        #  Le refus sans acteur n'a ni personne ni compte de service : seule la
        #  borne temporelle l'attrape. §7.30.
        "DELETE FROM auth_event WHERE person_id IS NULL AND service_account_id IS NULL "  # noqa: S608
        f"AND created_at >= '{debut}'",
    ):
        psql(compose, env, requete)


def noms(charge: object) -> list[str]:
    if not isinstance(charge, dict):
        return []
    lignes = charge.get("collaborateurs")
    return [ligne["last_name"] for ligne in lignes] if isinstance(lignes, list) else []


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
    from app.people.trombinoscope import TAILLE_PAR_DEFAUT, TAILLES_DE_PAGE

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
    print("  Trombinoscope pagine — US001, cahier §10.1 et §18.2")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(f"    info     tailles du cahier §18.2 : {', '.join(str(t) for t in TAILLES_DE_PAGE)}")
    print(f"    info     {VOLUME} lignes publiees + {len(EXCLUSIONS)} lignes d'etats varies")

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
    print(f"    ok       decor pose : {VOLUME + len(EXCLUSIONS)} appartenances, + un admin local")

    try:
        chemin = CHEMIN_TROMBINOSCOPE.format(code=code_entite)

        # --- 1. sans cookie : la matrice §5 met `ANON` a tiret ---------------
        controles += 1
        sans = appeler(
            arguments.base, chemin, contexte, en_tetes={"X-Request-ID": CORRELATION_FIXE}
        )
        if sans.statut == 401:
            print("    ok       sans session : 401 — la matrice §5 refuse `ANON`")
        else:
            echecs += 1
            print(f"    ECHEC    sans session : {sans.statut}, 401 attendu")

        # --- 2. TEMOIN : la connexion reussit et pose un cookie --------------
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
            print("    ok       TEMOIN : la connexion reussit et pose un cookie de session")
        else:
            echecs += 1
            pose = "oui" if jeton else "NON"
            print(f"    ECHEC    connexion : {connexion.statut}, cookie {pose}")
            print("             sans cookie, une liste vide serait indistinguable d'un filtrage")
            return 1
        biscuit = {"Cookie": f"{nom_cookie}={jeton}"}

        # --- 3. TEMOIN CENTRAL : une ligne publiee et active EST rendue ------
        #
        #  **IL PORTE SUR TOUTES LES PAGES, ET LA PREMIERE VERSION NE REGARDAIT
        #  QUE LA PREMIERE.** Le decor trie `zzvisible` en dernier -- c'est le
        #  point du volume -- si bien qu'elle est en page 3 sur 3. Mon controle
        #  echouait donc sur un livrable CONFORME : il exigeait plus que le
        #  critere, en confondant « est rendue » et « est en tete ». §7.20.
        controles += 1
        page1 = appeler(arguments.base, chemin, contexte, en_tetes=biscuit)
        charge = page1.json()
        toutes = _tous_les_noms(arguments.base, chemin, contexte, biscuit)
        if page1.statut == 200 and "zzvisible" in toutes:
            print("    ok       TEMOIN CENTRAL : la ligne `active` + `published` est rendue")
        else:
            echecs += 1
            print(f"    ECHEC    la ligne visible manque : {page1.statut}, {sorted(toutes)[:5]}")

        # --- 4. l'enveloppe et les lignes portent EXACTEMENT leurs champs ----
        controles += 1
        if isinstance(charge, dict) and set(charge) == CHAMPS_ENVELOPPE:
            lignes = charge.get("collaborateurs") or []
            if lignes and set(lignes[0]) == CHAMPS_LIGNE:
                print(
                    f"    ok       enveloppe {len(CHAMPS_ENVELOPPE)} champs, "
                    f"ligne {len(CHAMPS_LIGNE)} champs — ni plus ni moins"
                )
            else:
                echecs += 1
                print(f"    ECHEC    champs de ligne : {sorted(lignes[0]) if lignes else 'aucune'}")
        else:
            echecs += 1
            vu = sorted(charge) if isinstance(charge, dict) else charge
            print(f"    ECHEC    enveloppe : {vu}")

        # --- 5. la taille par defaut est celle du cahier ---------------------
        controles += 1
        if isinstance(charge, dict) and charge.get("taille") == TAILLE_PAR_DEFAUT:
            print(f"    ok       taille par defaut servie : {TAILLE_PAR_DEFAUT} — cahier §18.2")
        else:
            echecs += 1
            attendu = TAILLE_PAR_DEFAUT
            obtenu = charge.get("taille") if isinstance(charge, dict) else None
            print(f"    ECHEC    taille par defaut : {obtenu}, {attendu} attendue")

        # --- 6. les CINQ exclusions ------------------------------------------
        controles += 1
        attendus = set(listables())
        indesirables = sorted(
            nom for nom, _e, _v in EXCLUSIONS if nom not in attendus and nom in toutes
        )
        if not indesirables:
            print(
                f"    ok       les {len(EXCLUSIONS) - len(attendus)} etats non listables sont "
                "ABSENTS — dont `departed` et `archived`, qui sont RESTES `published`"
            )
        else:
            echecs += 1
            print(f"    ECHEC    lignes rendues a tort : {indesirables}")

        # --- 7. LE TEMOIN DES TROIS TAILLES, celui qui a trouve `T2-3` -------
        for taille in TAILLES_DE_PAGE:
            controles += 1
            reponse = appeler(
                arguments.base, f"{chemin}?taille={taille}", contexte, en_tetes=biscuit
            )
            corps = reponse.json()
            servies = len(corps.get("collaborateurs", [])) if isinstance(corps, dict) else -1
            attendu = min(taille, attendu_total())
            if reponse.statut == 200 and servies == attendu:
                print(f"    ok       taille={taille} servie : {servies} ligne(s)")
            else:
                echecs += 1
                print(
                    f"    ECHEC    taille={taille} : statut {reponse.statut}, "
                    f"{servies} ligne(s), {attendu} attendue(s) — c'est le defaut `T2-3`"
                )

        # --- 8. la liste blanche refuse tout le reste, au format du §18.3 ----
        for taille in (0, 1, 24, 26, 37, 99, 101, 1000):
            controles += 1
            reponse = appeler(
                arguments.base, f"{chemin}?taille={taille}", contexte, en_tetes=biscuit
            )
            corps = reponse.json()
            erreur = corps.get("erreur", {}) if isinstance(corps, dict) else {}
            conforme = (
                reponse.statut == 422
                and erreur.get("code") == "validation_invalide"
                and erreur.get("champ") == "query.taille"
                and erreur.get("identifiant_correlation")
            )
            if conforme:
                print(f"    ok       taille={taille} refusee, format du §18.3")
            else:
                echecs += 1
                print(f"    ECHEC    taille={taille} : {reponse.statut}, {str(corps)[:110]}")

        # --- 9. page=0 refusee ----------------------------------------------
        controles += 1
        zero = appeler(arguments.base, f"{chemin}?page=0", contexte, en_tetes=biscuit)
        corps = zero.json()
        champ = corps.get("erreur", {}).get("champ") if isinstance(corps, dict) else None
        if zero.statut == 422 and champ == "query.page":
            print("    ok       page=0 refusee : la pagination est 1-indexee")
        else:
            echecs += 1
            print(f"    ECHEC    page=0 : {zero.statut}, champ {champ}")

        # --- 10. RECOMPOSITION : ni repetition ni saut, pour les trois tailles
        for taille in TAILLES_DE_PAGE:
            controles += 1
            vus: list[str] = []
            total = 0
            pages = 1
            page = 1
            while page <= pages:
                reponse = appeler(
                    arguments.base,
                    f"{chemin}?page={page}&taille={taille}",
                    contexte,
                    en_tetes=biscuit,
                )
                corps = reponse.json()
                if not isinstance(corps, dict):
                    break
                total = int(corps.get("total", 0))
                pages = int(corps.get("pages", 0))
                vus += [ligne["id"] for ligne in corps.get("collaborateurs", [])]
                page += 1
            if len(vus) == total == len(set(vus)) == attendu_total():
                print(
                    f"    ok       taille={taille} : {pages} page(s) recomposent "
                    f"{total} lignes, chacune UNE fois"
                )
            else:
                echecs += 1
                print(
                    f"    ECHEC    taille={taille} : {len(vus)} vues, "
                    f"{len(set(vus))} distinctes, total {total} — "
                    "un ordre non total repete ou saute"
                )

        # --- 11. l'ordre est nom puis prenom, et LA BASE EST LA REFERENCE ----
        #
        #  **NE PAS RETRIER EN PYTHON.** Ma premiere version comparait l'ordre
        #  rendu a `sorted()`, qui trie par OCTETS : « zzelodie » avec accent y
        #  passe APRES « zzvisible », alors que la collation ICU `fr-FR` de la
        #  base la classe AVANT. Deux collations, donc deux grandeurs differentes
        #  (§7.0 sixieme proposition) -- et le controle echouait sur un livrable
        #  conforme des que le decor a porte un accent.
        #
        #  La reference est donc l'ordre que PostgreSQL produit lui-meme. Ce n'est
        #  PAS circulaire : la route pourrait n'avoir aucun `ORDER BY`, ou trier
        #  par prenom, et les deux listes differeraient.
        controles += 1
        ordre = [
            f"{nom}|{prenom}"
            for nom, prenom in _premiers_noms(arguments.base, chemin, contexte, biscuit)
        ]
        code_ordre, brut = psql(
            compose,
            env,
            "SELECT p.last_name || '|' || p.first_name "  # noqa: S608
            "FROM entity_membership em JOIN person p ON p.id = em.person_id "
            "WHERE em.entity_id = (SELECT id FROM entity WHERE code = "
            f"'{code_entite}') "
            "AND em.membership_state = 'active' AND em.profile_visibility = 'published' "
            "ORDER BY p.last_name, p.first_name, em.id LIMIT 100",
        )
        reference = [ligne.strip() for ligne in brut.splitlines() if ligne.strip()]
        if code_ordre == 0 and ordre and ordre == reference:
            print(
                f"    ok       ordre nom puis prenom : {len(ordre)} lignes IDENTIQUES a "
                "l'ordre que PostgreSQL produit (collation ICU fr-FR)"
            )
        else:
            echecs += 1
            print(f"    ECHEC    ordre divergent — API {ordre[:3]} contre base {reference[:3]}")

        # --- 12. T3 : la recherche IGNORE les accents, dans les deux sens ----
        for terme, attendu in (
            ("zzelodie", "zzélodie"),
            ("zzélodie", "zzélodie"),
            ("ZZELODIE", "zzélodie"),
            ("zzvisible", "zzvisible"),
        ):
            controles += 1
            #  **LE TERME EST PERCENT-ENCODE**, et ce n'est pas un detail : `urllib`
            #  encode la ligne de requete en ASCII et LEVE sur un accent brut --
            #  « 'ascii' codec can't encode character '\xe9' ». Un navigateur
            #  encode de lui-meme ; mon controle ne le faisait pas, et il
            #  n'eprouvait donc pas le decodage cote API. C'est le meme geste que
            #  `encodeURIComponent` dans `cheminTrombinoscope`.
            corps = appeler(
                arguments.base,
                f"{chemin}?recherche={urllib.parse.quote(terme)}",
                contexte,
                en_tetes=biscuit,
            ).json()
            rendus = noms(corps)
            if rendus == [attendu]:
                print(f"    ok       recherche « {terme} » -> {attendu}")
            else:
                echecs += 1
                print(f"    ECHEC    recherche « {terme} » : {rendus}, [{attendu}] attendu")

        # --- 13. T3 : un terme absent rend une liste VIDE, pas une erreur ----
        controles += 1
        absent = appeler(
            arguments.base, f"{chemin}?recherche=zzzz-nexiste-pas", contexte, en_tetes=biscuit
        )
        corps = absent.json()
        vide = isinstance(corps, dict) and corps.get("total") == 0 and corps.get("pages") == 0
        if absent.statut == 200 and vide:
            print("    ok       un terme absent rend 200 avec total 0 — pas une erreur")
        else:
            echecs += 1
            print(f"    ECHEC    terme absent : {absent.statut}, {str(corps)[:110]}")

        # --- 14. T3 : les filtres mal formes sont refuses au format du §18.3 --
        for axe in ("cercle", "dsm", "metier", "client"):
            controles += 1
            refus = appeler(
                arguments.base, f"{chemin}?{axe}=pas-un-uuid", contexte, en_tetes=biscuit
            )
            corps = refus.json()
            erreur = corps.get("erreur", {}) if isinstance(corps, dict) else {}
            if refus.statut == 422 and erreur.get("champ") == f"query.{axe}":
                print(f"    ok       {axe}=pas-un-uuid refuse, champ nomme")
            else:
                echecs += 1
                print(f"    ECHEC    {axe} mal forme : {refus.statut}, {str(corps)[:100]}")

        # --- 15. T3 : les DEUX statuts valides passent, les autres non -------
        #  **PAS `valeur` COMME NOM DE BOUCLE** : ce module porte une FONCTION
        #  `valeur()`, et une variable locale du meme nom la masque dans TOUTE la
        #  fonction -- Python decide de la portee a la compilation. L'echec
        #  surgissait alors ligne 343, cent lignes AVANT ce code, sur un
        #  `valeur(debut)` devenu inatteignable.
        for statut_demande, attendu_statut in (
            ("mission", 200),
            ("intercontract", 200),
            ("employe", 422),
            ("MISSION", 422),
        ):
            controles += 1
            reponse = appeler(
                arguments.base, f"{chemin}?statut={statut_demande}", contexte, en_tetes=biscuit
            )
            if reponse.statut == attendu_statut:
                print(f"    ok       statut={statut_demande} -> {attendu_statut}")
            else:
                echecs += 1
                print(
                    f"    ECHEC    statut={statut_demande} : {reponse.statut}, "
                    f"{attendu_statut} attendu — les DEUX valides doivent PASSER, "
                    "sinon un type qui refuse tout passerait ce controle"
                )

        # --- 16. T3 : un terme trop long est refuse, la borne EXACTE passe ---
        for longueur, attendu_statut in ((128, 200), (129, 422)):
            controles += 1
            reponse = appeler(
                arguments.base,
                f"{chemin}?recherche={'a' * longueur}",
                contexte,
                en_tetes=biscuit,
            )
            if reponse.statut == attendu_statut:
                print(f"    ok       terme de {longueur} caracteres -> {attendu_statut}")
            else:
                echecs += 1
                print(f"    ECHEC    terme de {longueur} : {reponse.statut}")

        # --- 17. le 404 est IDENTIQUE a celui de la route d'entite ----------
        controles += 1
        inconnu = f"{MARQUEUR}-inexistant"
        a = appeler(
            arguments.base,
            CHEMIN_TROMBINOSCOPE.format(code=inconnu),
            contexte,
            en_tetes={**biscuit, "X-Request-ID": CORRELATION_FIXE},
        )
        b = appeler(
            arguments.base,
            CHEMIN_UNE_ENTITE.format(code=inconnu),
            contexte,
            en_tetes={**biscuit, "X-Request-ID": CORRELATION_FIXE},
        )
        if a.statut == b.statut == 404 and a.signature() == b.signature():
            print("    ok       404 identique a celui de `/entities/{code}`, corps ET en-tetes")
            print(
                f"             non compare : {', '.join(sorted(EN_TETES_NON_COMPARABLES))} — "
                "l'horloge n'est pas un oracle"
            )
        else:
            echecs += 1
            print(f"    ECHEC    404 divergents : {a.statut}/{b.statut}")
    finally:
        nettoyer(compose, env, MARQUEUR, debut)

    print()
    print(f"    controles executes : {controles}   echecs : {echecs}")
    if echecs:
        return 1
    print(
        "  --> le trombinoscope est pagine, ordonne, et il ne rend QUE des profils "
        "publies d'appartenances actives"
    )
    return 0


def _tous_les_noms(
    base: str, chemin: str, contexte: ssl.SSLContext, biscuit: dict[str, str]
) -> set[str]:
    """Tous les noms de famille rendus, toutes pages confondues."""
    vus: set[str] = set()
    page, pages = 1, 1
    while page <= pages:
        corps = appeler(base, f"{chemin}?page={page}&taille=100", contexte, en_tetes=biscuit).json()
        if not isinstance(corps, dict):
            break
        pages = int(corps.get("pages", 0))
        vus |= set(noms(corps))
        page += 1
    return vus


def _premiers_noms(
    base: str, chemin: str, contexte: ssl.SSLContext, biscuit: dict[str, str]
) -> list[tuple[str, str]]:
    """Les couples (nom, prenom) de la premiere page de 100, dans l'ordre servi."""
    corps = appeler(base, f"{chemin}?taille=100", contexte, en_tetes=biscuit).json()
    if not isinstance(corps, dict):
        return []
    return [(ligne["last_name"], ligne["first_name"]) for ligne in corps.get("collaborateurs", [])]


if __name__ == "__main__":
    sys.exit(main())
