#!/usr/bin/env python3
"""Prouver les SEPT separations du cahier des charges 22.2 entre dev et recette.

LOT 1, sous-etape T8, story MVP-L01-US002.

LE CRITERE, ET OU IL SE COMPTE

    Cahier 22.2, litteralement, sept tirets : « projet Docker distinct ; base
    PostgreSQL distincte ; bucket MinIO distinct ; volumes distincts ; secrets
    distincts ; reseau distinct ; ports distincts. »

    La fiche du lot 3 n'en enumere que SIX — « projet Docker distinct » y manque.
    C'est ECART-023, exactement la classe de ECART-018, ou la fiche annoncait
    « 8 controles de CI » la ou le cahier en enumere 11. Les sept sont donc
    comptees sur le cahier, et ce script les compte lui-meme : il annonce
    « 7 separations attendues, N verifiees » et echoue si les deux nombres
    diffèrent.

CE QUI DISTINGUE CE CONTROLE D'UNE LECTURE DE .env

    Comparer `POSTGRES_DB` dans deux fichiers ne prouve rien : une variable
    declaree n'est pas une base servie, et le defaut T7-8 a montre qu'une
    variable peut ne jamais atteindre le conteneur. Chaque separation est donc
    lue sur l'etat REEL — etiquette des conteneurs en marche, `current_database()`
    dans l'instance, contenu des MinIO, volumes et reseaux du moteur, publications
    reelles.

    Trois separations demandent mieux qu'une comparaison de noms, parce que des
    noms differents n'y prouvent pas la separation :

      - la BASE : le controle exige que chaque instance SERVE la base declaree, et
        que celle de l'autre environnement y soit ABSENTE ;
      - le BUCKET : de meme, celui de dev doit etre ABSENT du MinIO de recette, et
        reciproquement. Deux noms distincts dans deux services qui partageraient un
        volume donneraient la meme observation ;
      - le RESEAU : deux noms de reseau ne disent rien du routage, et la mesure a
        DEMENTI ce que j'attendais. Voir le commentaire de `separation_reseau` :
        publier un port perce l'isolement inter-reseaux de Docker, ce qui est
        mesure sur un meme conteneur. Le controle exige donc l'isolement la ou
        Docker le fournit — noms, sous-reseaux, DNS, ports NON publies — RAPPORTE
        visiblement les ports publies qui restent joignables, et EXIGE la barriere
        qui rend ce residuel acceptable : le secret de la recette ne doit pas
        ouvrir la base de dev. `ROAD-RSK-034`.

POURQUOI LES DEUX ENVIRONNEMENTS DOIVENT TOURNER EN MEME TEMPS

    Les essais de routage l'exigent : si la stack de dev est arretee, un echec de
    connexion ne prouve plus l'isolement, seulement l'absence de la cible. Chaque
    essai negatif est donc accompagne d'un temoin positif sur le meme type de
    port — sans lui, une sonde muette produirait la meme observation qu'un
    isolement effectif, ce qui est le defaut T5-6.

    DEC-440 n'autorise qu'un environnement a la fois en exploitation courante.
    Cette mesure est une EXCEPTION bornee et annoncee, et c'est aussi celle que
    QO-085 reclame depuis T2 : le dimensionnement de deux stacks simultanees. Le
    script mesure donc la memoire des deux et l'imprime.

POURQUOI CE SCRIPT EST EN PYTHON
    `subprocess.run([...])` sans shell ne redecoupe aucun argument, et
    `returncode` ne peut pas etre celui d'un autre maillon. Le depot vit sous
    « ~/Library/Mobile Documents/ », dont le chemin porte une espace : ce piege a
    produit quatre defauts sur ce projet, dont deux commis apres l'avoir cite. La
    parade retenue en T7 n'est pas la vigilance, c'est le choix d'un outil ou
    l'erreur n'existe pas.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
COMPOSE_DIR = RACINE / "infra" / "compose"

# Les deux environnements compares, et leur fichier d'environnement.
ENVIRONNEMENTS = {"dev": ".env", "recette": ".env.recette"}

SERVICES_ATTENDUS = 8
VOLUMES_ATTENDUS = 6
PUBLICATIONS_ATTENDUES = 7
SEPARATIONS_ATTENDUES = 7

# Les cinq valeurs sensibles. Elles ne sont JAMAIS imprimees : le controle est
# qu'elles diffèrent, jamais ce qu'elles valent.
SECRETS = (
    "APP_SECRET_KEY",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_PASSWORD",
    "MINIO_ROOT_USER",
)


# ===========================================================================
#  Journal — compter, et confronter le compte a un attendu
# ===========================================================================


class Journal:
    """Un controle qui n'annonce pas combien d'elements il a examines peut
    toujours n'en avoir examine qu'un. Lecon des defauts T2-4 et T2-6."""

    def __init__(self) -> None:
        self.executes = 0
        self.echecs = 0
        self.separations_verifiees = 0

    def info(self, message: str) -> None:
        print(f"    info     {message}")

    def ok(self, message: str) -> None:
        print(f"    ok       {message}")

    def echec(self, message: str) -> None:
        print(f"    ECHEC    {message}")

    def exiger(self, condition: bool, message: str) -> bool:
        self.executes += 1
        if condition:
            self.ok(message)
            return True
        self.echecs += 1
        self.echec(f"cette assertion n'est PAS verifiee : {message}")
        return False

    def separation(self, numero: int, titre: str) -> None:
        print()
        print(f"  SEPARATION {numero} sur {SEPARATIONS_ATTENDUES} — {titre}")
        self.separations_verifiees += 1

    def conclure(self, resume: str) -> int:
        print()
        print(f"  controles executes : {self.executes}   echecs : {self.echecs}")
        print(
            f"  separations attendues : {SEPARATIONS_ATTENDUES}   "
            f"verifiees : {self.separations_verifiees}"
        )
        if self.separations_verifiees != SEPARATIONS_ATTENDUES:
            self.echecs += 1
            print("  ECHEC : toutes les separations du cahier 22.2 n'ont pas ete examinees")
        if self.echecs:
            print(f"  --> ECHEC — {resume}")
            return 1
        print(f"  --> {resume}")
        return 0


def lancer(*commande: str) -> tuple[int, str]:
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # precisement ce qui rend ce script sur — voir l'en-tete.
    p = subprocess.run(  # noqa: S603
        list(commande), capture_output=True, text=True, cwd=RACINE
    )
    return p.returncode, (p.stdout + p.stderr).strip()


# ===========================================================================
#  Lecture de l'etat reel
# ===========================================================================


def affectations(fichier: Path) -> dict[str, str]:
    motif = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")
    valeurs: dict[str, str] = {}
    for ligne in fichier.read_text(encoding="utf-8").split("\n"):
        if m := motif.match(ligne):
            valeurs[m.group(1)] = m.group(2)
    return valeurs


def configuration_assemblee(environnement: str) -> dict:
    """La configuration Compose REELLEMENT assemblee, base plus surcouche.

    C'est la seule vue qui tienne compte de la substitution : les valeurs par
    defaut inscrites dans le YAML peuvent etre remplacees par le fichier
    d'environnement, et un controle statique ne le verrait pas.
    """
    code, sortie = lancer(
        "docker",
        "compose",
        "--env-file",
        str(RACINE / ENVIRONNEMENTS[environnement]),
        "-f",
        str(COMPOSE_DIR / "docker-compose.base.yml"),
        "-f",
        str(COMPOSE_DIR / f"docker-compose.{environnement}.yml"),
        "config",
        "--format",
        "json",
    )
    if code != 0:
        raise SystemExit(
            f"  ECHEC     `docker compose config` de {environnement} (code {code})\n{sortie[:500]}"
        )
    return json.loads(sortie)


def conteneurs(projet: str) -> dict[str, dict]:
    """Les conteneurs en marche du projet, indexes par nom de service."""
    code, sortie = lancer(
        "docker",
        "ps",
        "--filter",
        f"label=com.docker.compose.project={projet}",
        "--format",
        "{{.ID}}",
    )
    if code != 0 or not sortie:
        return {}
    resultat: dict[str, dict] = {}
    for cid in sortie.split("\n"):
        c, brut = lancer("docker", "inspect", cid)
        if c != 0:
            continue
        d = json.loads(brut)[0]
        service = d["Config"]["Labels"].get("com.docker.compose.service", cid)
        resultat[service] = d
    return resultat


def dans_conteneur(cid: str, *commande: str) -> tuple[int, str]:
    return lancer("docker", "exec", cid, *commande)


# ===========================================================================
#  Les sept separations
# ===========================================================================


def separation_projet(j: Journal, etat: dict) -> None:
    j.separation(1, "projet Docker distinct (celle que la fiche omettait)")
    projets = {}
    for env, e in etat.items():
        declare = e["config"]["name"]
        etiquettes = {
            d["Config"]["Labels"].get("com.docker.compose.project")
            for d in e["conteneurs"].values()
        }
        j.info(f"{env:8s} : declare {declare!r}, etiquette des conteneurs {sorted(etiquettes)}")
        j.exiger(
            etiquettes == {declare},
            f"{env} : les {len(e['conteneurs'])} conteneurs portent tous le projet declare",
        )
        projets[env] = declare
    j.exiger(
        projets["dev"] != projets["recette"],
        f"les deux projets Docker diffèrent : {projets['dev']!r} contre {projets['recette']!r}",
    )


def separation_base(j: Journal, etat: dict) -> None:
    j.separation(2, "base PostgreSQL distincte")
    # COMME POUR LE BUCKET, DEUX NOMS DIFFERENTS NE SUFFISENT PAS. Le controle
    # etablit deux choses : que chaque instance SERT la base declaree — donc
    # qu'elle existe vraiment, ce qu'une variable ne dit pas (defaut T7-8) — et
    # que la base de l'autre environnement y est ABSENTE.
    #
    # `-d` est indispensable, et son absence etait un defaut de ma premiere
    # version : sans lui, psql cherche une base homonyme de l'utilisateur, ici
    # `onboarding_app`, qui n'existe pas. Le controle aurait echoue pour une
    # raison entierement etrangere a la separation qu'il pretend mesurer.
    bases = {env: e["env"]["POSTGRES_DB"] for env, e in etat.items()}
    j.exiger(
        bases["dev"] != bases["recette"],
        f"les deux bases declarees diffèrent : {bases['dev']!r} contre {bases['recette']!r}",
    )
    presence: dict[tuple[str, str], bool] = {}
    for env, e in etat.items():
        cid = e["conteneurs"]["db"]["Id"]
        utilisateur = e["env"]["POSTGRES_USER"]
        code, sortie = dans_conteneur(
            cid, "psql", "-U", utilisateur, "-d", bases[env], "-tAc", "select current_database()"
        )
        servie = sortie.strip().split("\n")[-1] if code == 0 else ""
        j.info(f"{env:8s} : current_database() = {servie!r}")
        j.exiger(
            code == 0 and servie == bases[env],
            f"{env} : l'instance SERT bien la base declaree {bases[env]!r}",
        )
        code, sortie = dans_conteneur(
            cid,
            "psql",
            "-U",
            utilisateur,
            "-d",
            bases[env],
            "-tAc",
            "select datname from pg_database where not datistemplate",
        )
        presentes = (
            {ligne.strip() for ligne in sortie.split("\n") if ligne.strip()} if code == 0 else set()
        )
        j.exiger(code == 0, f"{env} : la liste des bases de l'instance est lisible")
        for cible_env, base in bases.items():
            presence[(env, cible_env)] = base in presentes
            attendu = env == cible_env
            j.info(
                f"{env:8s} : base {base!r} {'PRESENTE' if base in presentes else 'absente':9s}"
                f" (attendu : {'presente' if attendu else 'absente'})"
            )
    j.exiger(
        not presence[("dev", "recette")] and not presence[("recette", "dev")],
        "aucune instance ne porte la base de l'autre : les donnees sont bien separees",
    )


def separation_bucket(j: Journal, etat: dict) -> None:
    j.separation(3, "bucket MinIO distinct")
    # POURQUOI LA PRESENCE NE SUFFIT PAS. Deux noms differents dans deux services
    # qui partageraient un volume donneraient la meme observation. Le controle
    # exige donc que chaque bucket soit ABSENT de l'autre MinIO.
    seaux = {env: e["env"]["MINIO_BUCKET"] for env, e in etat.items()}
    j.exiger(
        seaux["dev"] != seaux["recette"],
        f"les deux buckets declares diffèrent : {seaux['dev']!r} contre {seaux['recette']!r}",
    )
    presence: dict[tuple[str, str], bool] = {}
    for env, e in etat.items():
        cid = e["conteneurs"]["minio"]["Id"]
        code, _ = dans_conteneur(
            cid,
            "mc",
            "alias",
            "set",
            "local",
            "http://127.0.0.1:9000",
            e["env"]["MINIO_ROOT_USER"],
            e["env"]["MINIO_ROOT_PASSWORD"],
        )
        j.exiger(code == 0, f"{env} : le client mc s'authentifie sur son propre MinIO")
        for cible_env, seau in seaux.items():
            c, _ = dans_conteneur(cid, "mc", "stat", f"local/{seau}")
            presence[(env, cible_env)] = c == 0
            attendu = env == cible_env
            j.info(
                f"{env:8s} : bucket {seau!r} {'PRESENT' if c == 0 else 'absent':8s}"
                f" (attendu : {'present' if attendu else 'absent'})"
            )
    j.exiger(
        presence[("dev", "dev")] and presence[("recette", "recette")],
        "chaque MinIO porte SON bucket (sinon la sonde serait muette)",
    )
    j.exiger(
        not presence[("dev", "recette")] and not presence[("recette", "dev")],
        "aucun MinIO ne voit le bucket de l'autre : les stockages sont bien separes",
    )


def separation_volumes(j: Journal, etat: dict) -> None:
    j.separation(4, "volumes distincts")
    ensembles = {}
    for env, e in etat.items():
        code, sortie = lancer(
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={e['config']['name']}",
            "--format",
            "{{.Name}}",
        )
        noms = set(sortie.split("\n")) if code == 0 and sortie else set()
        ensembles[env] = noms
        j.info(f"{env:8s} : {len(noms)} volumes — {sorted(noms)}")
        j.exiger(
            len(noms) == VOLUMES_ATTENDUS,
            f"{env} : {len(noms)} volumes trouves sur {VOLUMES_ATTENDUS} attendus",
        )
    commun = ensembles["dev"] & ensembles["recette"]
    j.exiger(
        not commun, f"aucun volume partage entre les deux environnements ({len(commun)} commun)"
    )


def separation_secrets(j: Journal, etat: dict) -> None:
    j.separation(5, "secrets distincts")
    # AUCUNE VALEUR N'EST IMPRIMEE. Le controle est qu'elles diffèrent.
    differents = 0
    for nom in SECRETS:
        a = etat["dev"]["env"].get(nom, "")
        b = etat["recette"]["env"].get(nom, "")
        renseignes = (
            bool(a) and bool(b) and not a.startswith("CHANGE_ME") and not b.startswith("CHANGE_ME")
        )
        distinct = a != b
        differents += distinct and renseignes
        j.info(f"{nom:22s} : renseigne des deux cotes={renseignes}, distinct={distinct}")
    j.exiger(
        differents == len(SECRETS),
        f"{differents} secrets renseignes ET distincts sur {len(SECRETS)} attendus",
    )
    # Et ils doivent etre distincts dans le CONTENEUR, pas seulement dans le
    # fichier : c'est la valeur transmise qui protege, pas celle declaree.
    lus = {}
    for env, e in etat.items():
        cid = e["conteneurs"]["api"]["Id"]
        code, sortie = dans_conteneur(
            cid, "python", "-c", "import os;print(os.environ.get('POSTGRES_PASSWORD',''))"
        )
        lus[env] = sortie.strip() if code == 0 else ""
        j.exiger(bool(lus[env]), f"{env} : le conteneur api porte bien un mot de passe PostgreSQL")
    j.exiger(
        lus["dev"] != lus["recette"],
        "le secret REELLEMENT transmis aux conteneurs diffère entre les deux environnements",
    )


SONDE_TCP = (
    "import socket,sys\n"
    "s=socket.socket(); s.settimeout(4)\n"
    "try:\n"
    "    s.connect((sys.argv[1], int(sys.argv[2]))); print('JOIGNABLE')\n"
    "except Exception as e:\n"
    "    print('INJOIGNABLE', type(e).__name__)\n"
)


def adresse(conteneur: dict) -> str:
    reseaux = conteneur["NetworkSettings"]["Networks"]
    return next(iter(reseaux.values()))["IPAddress"]


def separation_reseau(j: Journal, etat: dict) -> None:
    j.separation(6, "reseau distinct — et ce que l'isolement couvre VRAIMENT")
    # ------------------------------------------------------------------------
    #  CE QUE LE CAHIER 22.2 DEMANDE, ET CE QU'IL NE DEMANDE PAS
    #
    #  Il demande un « reseau distinct ». Il ne dit pas « reseaux mutuellement
    #  inatteignables ». Ma premiere version de ce controle exigeait la seconde
    #  chose, et elle a ECHOUE — sur un livrable conforme.
    #
    #  LE DIAGNOSTIC A ETE FAIT AVANT TOUTE CORRECTION, et il a produit un
    #  constat que le critere ne visait pas : PUBLIER UN PORT PERCE L'ISOLEMENT
    #  INTER-RESEAUX DE DOCKER. Mesure du 29/07/2026, sur le MEME conteneur, ce
    #  qui elimine toute cause propre a un service :
    #
    #      dev mailpit 172.20.0.4:8025  PUBLIE      -> JOIGNABLE depuis la recette
    #      dev mailpit 172.20.0.4:1025  non publie  -> TimeoutError
    #
    #  Docker insere pour chaque port publie une regle ACCEPT dans la chaine
    #  FORWARD, et elle precede les regles DOCKER-ISOLATION qui rejettent le
    #  trafic entre reseaux. Le paquet est donc accepte avant que l'isolement
    #  n'ait la parole. Confirme de bout en bout : depuis la recette, une
    #  connexion a la base de dev aboutit et `current_database()` rend
    #  `onboarding_dev`.
    #
    #  CE QUI PROTEGE REELLEMENT, ET C'EST MESURE : les secrets distincts. Avec
    #  le mot de passe de la recette, la meme connexion est REFUSEE en
    #  « password authentication failed ». Le controle l'exige donc explicitement.
    #
    #  Ce controle affirme donc ce qui est requis et vrai, EXIGE l'isolement la
    #  ou Docker le fournit, et RAPPORTE VISIBLEMENT le residuel plutot que de
    #  le taire — c'est le parti de DEC-482 pour Trivy. Le taire aurait produit
    #  un « 7 separations prouvees » qui aurait laisse croire davantage que ce
    #  qui est vrai. `ROAD-RSK-034` le consigne.
    # ------------------------------------------------------------------------
    reseaux, sous_reseaux = {}, {}
    for env, e in etat.items():
        declares = {n: d.get("name") for n, d in e["config"]["networks"].items()}
        reseaux[env] = set(declares.values())
        code, sortie = lancer(
            "docker",
            "network",
            "inspect",
            next(iter(declares.values())),
            "--format",
            "{{range .IPAM.Config}}{{.Subnet}}{{end}}",
        )
        sous_reseaux[env] = sortie.strip() if code == 0 else ""
        j.info(f"{env:8s} : reseau {list(declares.values())}, sous-reseau {sous_reseaux[env]}")
    j.exiger(
        not (reseaux["dev"] & reseaux["recette"]),
        f"noms de reseau distincts : {sorted(reseaux['dev'])} contre {sorted(reseaux['recette'])}",
    )
    j.exiger(
        bool(sous_reseaux["dev"]) and sous_reseaux["dev"] != sous_reseaux["recette"],
        f"sous-reseaux distincts : {sous_reseaux['dev']} contre {sous_reseaux['recette']}",
    )

    api_recette = etat["recette"]["conteneurs"]["api"]["Id"]

    # 1. ISOLEMENT DU NOM. Le DNS du reseau de recette ne doit pas resoudre un
    #    conteneur de dev.
    code, sortie = dans_conteneur(
        api_recette, "python", "-c", SONDE_TCP, "onboarding-dev-db-1", "5432"
    )
    j.exiger(
        code == 0 and "INJOIGNABLE" in sortie,
        f"le nom d'un conteneur de dev n'est pas resolu depuis la recette ({sortie.strip()})",
    )

    # 2. ISOLEMENT DU ROUTAGE, LA OU DOCKER LE FOURNIT : un port NON publie de
    #    l'autre environnement. Avec son temoin positif sur le MEME type de port
    #    dans son PROPRE reseau — sans lui, une sonde muette produirait la meme
    #    observation qu'un isolement effectif.
    web_recette = adresse(etat["recette"]["conteneurs"]["web"])
    code, sortie = dans_conteneur(api_recette, "python", "-c", SONDE_TCP, web_recette, "5173")
    j.exiger(
        code == 0 and "JOIGNABLE" in sortie,
        f"TEMOIN POSITIF : un port non publie de SON reseau est joignable ({sortie.strip()})",
    )
    web_dev = adresse(etat["dev"]["conteneurs"]["web"])
    code, sortie = dans_conteneur(api_recette, "python", "-c", SONDE_TCP, web_dev, "5173")
    j.exiger(
        code == 0 and "INJOIGNABLE" in sortie,
        f"un port NON publie de dev est injoignable depuis la recette ({sortie.strip()})",
    )

    # 3. LE RESIDUEL, MESURE ET NOMME — non bloquant, mais jamais tu.
    perces = []
    for service, d in etat["dev"]["conteneurs"].items():
        for interne, liaisons in (d["NetworkSettings"]["Ports"] or {}).items():
            if not liaisons:
                continue
            port = interne.split("/")[0]
            code, sortie = dans_conteneur(api_recette, "python", "-c", SONDE_TCP, adresse(d), port)
            if code == 0 and "JOIGNABLE" in sortie and "INJOIGNABLE" not in sortie:
                perces.append(f"{service}:{port}")
    print(f"    RESIDUEL {len(perces)} ports PUBLIES de dev restent joignables depuis la recette :")
    print(f"               {', '.join(perces) if perces else 'aucun'}")
    print("               Cause : la regle ACCEPT que Docker installe pour un port publie")
    print("               precede ses regles DOCKER-ISOLATION. Le cahier 22.2 exige un reseau")
    print("               distinct, ce qui est acquis ; il n'exige pas l'inatteignabilite.")
    print("               Consigne en ROAD-RSK-034, residuel a reevaluer avant le LOT 13.")

    # 4. LA BARRIERE EFFECTIVE, EXIGEE : le secret de la recette ne doit PAS
    #    ouvrir la base de dev. C'est ce qui rend le residuel acceptable, donc
    #    cela doit etre un controle et non une affirmation.
    db_dev = adresse(etat["dev"]["conteneurs"]["db"])
    sonde_auth = (
        "import os,sys,psycopg\n"
        "try:\n"
        "    psycopg.connect(host=sys.argv[1], port=5432, dbname=sys.argv[2],\n"
        "        user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],\n"
        "        connect_timeout=5).close()\n"
        "    print('OUVERTE')\n"
        "except Exception as e:\n"
        "    print('REFUSEE', type(e).__name__)\n"
    )
    code, sortie = dans_conteneur(
        api_recette, "python", "-c", sonde_auth, db_dev, etat["dev"]["env"]["POSTGRES_DB"]
    )
    j.exiger(
        code == 0 and "REFUSEE" in sortie,
        f"le secret de la RECETTE n'ouvre PAS la base de dev ({sortie.strip()}) "
        "— c'est la barriere qui rend le residuel acceptable",
    )


def separation_ports(j: Journal, etat: dict) -> None:
    j.separation(7, "ports distincts")
    ensembles = {}
    for env, e in etat.items():
        publies: set[str] = set()
        hors_boucle: list[str] = []
        for service, d in e["conteneurs"].items():
            # Le port INTERNE ne nous interesse pas : la separation porte sur les
            # ports de l'HOTE, seuls susceptibles d'entrer en collision.
            for liaisons in (d["NetworkSettings"]["Ports"] or {}).values():
                for liaison in liaisons or []:
                    publies.add(liaison["HostPort"])
                    if liaison["HostIp"] not in ("127.0.0.1", "::1"):
                        hors_boucle.append(f"{service} {liaison['HostIp']}:{liaison['HostPort']}")
        ensembles[env] = publies
        j.info(f"{env:8s} : {len(publies)} publications — {sorted(publies, key=int)}")
        j.exiger(
            len(publies) == PUBLICATIONS_ATTENDUES,
            f"{env} : {len(publies)} publications sur {PUBLICATIONS_ATTENDUES} attendues",
        )
        j.exiger(
            not hors_boucle,
            f"{env} : aucune publication hors de la boucle locale ({len(hors_boucle)} trouvee)",
        )
    commun = ensembles["dev"] & ensembles["recette"]
    j.exiger(not commun, f"aucun port partage entre les deux environnements ({sorted(commun)})")


# ===========================================================================
#  Au-dela des sept : l'artefact reellement en execution
# ===========================================================================


def artefact_en_execution(j: Journal, etat: dict) -> None:
    print()
    print("  AU-DELA DES SEPT — la recette execute-t-elle bien l'artefact PUBLIE ?")
    # Le fichier de base declare `build:` : si l'image tiree manquait, Compose
    # aurait CONSTRUIT et la recette exercerait un artefact local en paraissant
    # saine. `--no-build` l'empeche, mais un controle vaut mieux qu'un drapeau.
    e = etat["recette"]
    for service in ("api", "worker", "web"):
        demandee = e["config"]["services"][service]["image"]
        d = e["conteneurs"][service]
        code, brut = lancer("docker", "image", "inspect", d["Image"])
        j.exiger(code == 0, f"{service} : l'image du conteneur est inspectable")
        if code != 0:
            continue
        empreintes = json.loads(brut)[0].get("RepoDigests", [])
        attendue = demandee.split("@")[-1] if "@" in demandee else ""
        trouvee = any(attendue and attendue in r for r in empreintes)
        j.info(f"{service:7s} : demandee {demandee.split('/')[-1][:40]}")
        j.exiger(
            trouvee,
            f"{service} : le conteneur tourne sur l'empreinte DEMANDEE, "
            "pas sur une construction locale",
        )

    # L'IDENTITE RAPPORTEE CONTRE L'IDENTITE GRAVEE — les deux cotes derives.
    # Mesure de T8 : une surcouche a valeur nulle ne retire PAS la valeur heritee,
    # donc le fichier d'environnement ECRASE l'ENV grave dans l'image. Si les deux
    # divergent, /health/version mentirait sur l'artefact en execution.
    for service in ("api", "worker"):
        d = etat["recette"]["conteneurs"][service]
        code, brut = lancer("docker", "image", "inspect", d["Image"])
        if code != 0:
            continue
        gravees = {}
        for entree in json.loads(brut)[0]["Config"].get("Env", []):
            nom, _, valeur = entree.partition("=")
            if nom in ("APP_VERSION", "APP_REVISION"):
                gravees[nom] = valeur
        rapportees = {}
        for nom in ("APP_VERSION", "APP_REVISION"):
            c, s = dans_conteneur(
                d["Id"], "python", "-c", f"import os;print(os.environ.get({nom!r},''))"
            )
            rapportees[nom] = s.strip() if c == 0 else ""
        j.info(f"{service:7s} : grave {gravees}, transmis {rapportees}")
        j.exiger(
            bool(gravees) and gravees == rapportees,
            f"{service} : l'identite TRANSMISE est celle GRAVEE dans l'image publiee",
        )


def memoire(j: Journal, etat: dict) -> None:
    """La mesure que QO-085 reclame depuis T2 : deux stacks simultanees."""
    print()
    print("  QO-085 — memoire des DEUX stacks simultanees")
    total = 0.0
    for env, e in etat.items():
        ids = [d["Id"] for d in e["conteneurs"].values()]
        if not ids:
            continue
        code, sortie = lancer("docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", *ids)
        if code != 0:
            j.echec(f"{env} : docker stats a echoue")
            continue
        mio = 0.0
        for ligne in sortie.split("\n"):
            valeur = ligne.split("/")[0].strip()
            nombre = float(re.sub(r"[^0-9.]", "", valeur) or 0)
            if "GiB" in valeur:
                nombre *= 1024
            elif "KiB" in valeur:
                nombre /= 1024
            mio += nombre
        total += mio
        j.info(f"{env:8s} : {len(ids)} services, {mio:.1f} Mio")
    j.info(f"TOTAL des deux environnements : {total:.1f} Mio")
    # 7,75 Gio alloues a Docker, mesure de T0 (QO-086, close).
    budget = 7.75 * 1024
    j.info(f"budget Docker : {budget:.0f} Mio, soit {100 * total / budget:.1f} % employes")
    j.exiger(
        total < budget,
        f"les deux stacks tiennent dans le budget alloue ({total:.1f} < {budget:.0f} Mio)",
    )
    print("      A DIRE SANS AMBIGUITE : mesurer la simultaneite ne l'autorise pas.")
    print("      DEC-440 n'admet qu'un environnement a la fois en exploitation, et T8")
    print("      prouve la SEPARATION par demarrages successifs. Les limites declarees")
    print("      sont des PLAFONDS, non des reservations : 12 288 Mio pour deux stacks")
    print("      depasseraient le budget s'ils etaient reserves, ce qu'ils ne sont pas.")


# ===========================================================================


# ===========================================================================
#  Conformite propre a la recette : architecture native, cible `execution`,
#  Mailpit exclusif.
# ===========================================================================


def architecture_native(j: Journal, etat: dict) -> None:
    print()
    print("  ARCHITECTURE — la reserve de la fiche 3.1, levee ou non")
    # T7 n'a prouve `arm64` NATIVEMENT que sur une liste de manifestes construite
    # localement, jamais sur l'image publiee : le jeton n'avait pas read:packages.
    # La recette tire l'image publiee SUR CE MAC, donc en aarch64 natif. La preuve
    # est de lire DANS le conteneur une valeur que l'autre architecture ne pourrait
    # pas produire — « le conteneur a demarre » donnerait la meme observation sur
    # les deux et ne prouverait rien (c'est la methode de T7).
    code, hote = lancer("uname", "-m")
    j.info(f"architecture de l'hote : {hote.strip()}")
    j.exiger(hote.strip() == "arm64", "l'hote est bien un Apple Silicon")
    lues = 0
    for service in ("api", "worker", "web"):
        cid = etat["recette"]["conteneurs"][service]["Id"]
        code, sortie = dans_conteneur(cid, "uname", "-m")
        valeur = sortie.strip()
        lues += code == 0 and valeur == "aarch64"
        j.info(f"{service:7s} : uname -m dans le conteneur = {valeur!r}")
    j.exiger(
        lues == 3,
        f"{lues}/3 conteneurs de l'image PUBLIEE tournent nativement en aarch64",
    )


def cible_execution(j: Journal, etat: dict) -> None:
    print()
    print("  CIBLE `execution` — l'image publiee ne sert PAS le serveur de developpement")
    # DISCRIMINANT DANS LES DEUX SENS. « 0 occurrence de /@vite/client » seul ne
    # prouverait rien : une page vide, une erreur de mandatement ou une sonde
    # muette donneraient la meme valeur. Le temoin est donc la MEME sonde sur le
    # developpement, qui doit en trouver UNE. C'est la methode de T7.
    origines = {
        "recette": f"https://{etat['recette']['env']['CADDY_SITE_APP']}"
        f":{etat['recette']['env']['CADDY_HTTPS_HOST_PORT']}",
        "dev": f"https://{etat['dev']['env']['CADDY_SITE_APP']}",
    }
    comptes = {}
    for env, origine in origines.items():
        # -k : la racine de l'autorite interne de la RECETTE n'est pas approuvee
        # dans le trousseau, et un controle ne doit pas dependre d'une action
        # humaine. Le certificat presente est bien celui de Caddy.
        code, corps = lancer("curl", "-k", "-sS", "--max-time", "15", origine + "/")
        j.exiger(code == 0, f"{env:8s} : la page repond a travers Caddy ({origine})")
        comptes[env] = corps.count("/@vite/client")
        a_des_assets = "/assets/" in corps
        j.info(
            f"{env:8s} : {comptes[env]} occurrence(s) de /@vite/client, "
            f"/assets/ {'present' if a_des_assets else 'ABSENT'}, {len(corps)} octets"
        )
        if env == "recette":
            j.exiger(a_des_assets, "recette : la page reference un artefact bati (/assets/)")
    j.exiger(comptes["recette"] == 0, "recette : AUCUN serveur de developpement Vite")
    j.exiger(
        comptes["dev"] >= 1,
        f"TEMOIN : la MEME sonde en trouve {comptes['dev']} sur dev — elle n'est pas muette",
    )


def mailpit_exclusif(j: Journal, etat: dict) -> None:
    print()
    print("  MAILPIT — ce que le LOT 1 peut prouver, et ce qui appartient aux LOTS 11 et 13")
    # OU EST LA SOURCE. Le cahier 16.5 dit « Mailpit en developpement ET RECETTE » :
    # c'est cela, l'exigence du LOT 1. La formule « Mailpit est EXCLUSIF en
    # recette » est celle de MVP-L11-US003, donc du LOT 11, et « aucun e-mail reel
    # ne part de la recette » est un critere de sortie du LOT 13. La fiche du lot
    # importe ces deux formules dans T8 ; on prouve ici ce qui est prouvable.
    for env, e in etat.items():
        j.exiger(
            e["env"]["EMAIL_PROVIDER"] == "mailpit",
            f"{env:8s} : EMAIL_PROVIDER={e['env']['EMAIL_PROVIDER']!r}, aucun fournisseur reel",
        )
        j.exiger(
            e["env"]["SMTP_HOST"] == "mailpit",
            f"{env:8s} : SMTP_HOST={e['env']['SMTP_HOST']!r}, resolu dans SON propre reseau",
        )

    def total(port: str) -> int | None:
        code, corps = lancer(
            "curl", "-sS", "--max-time", "10", f"http://127.0.0.1:{port}/api/v1/messages?limit=1"
        )
        if code != 0:
            return None
        try:
            return int(json.loads(corps)["messages_count"])
        except (json.JSONDecodeError, KeyError, TypeError):
            try:
                return int(json.loads(corps)["total"])
            except Exception:
                return None

    ports = {env: e["env"]["MAILPIT_HOST_PORT"] for env, e in etat.items()}
    avant = {env: total(p) for env, p in ports.items()}
    j.info(f"totaux avant envoi : {avant}")
    j.exiger(
        all(v is not None for v in avant.values()),
        "les deux interfaces Mailpit repondent et annoncent un total",
    )

    envoi = (
        "import smtplib, email.message\n"
        "m = email.message.EmailMessage()\n"
        "m['From'] = 'no-reply@exalt-company.com'\n"
        "m['To'] = 'controle-t8@exemple.invalid'\n"
        "m['Subject'] = 'T8 controle de separation Mailpit'\n"
        "m.set_content('Message de controle, aucune donnee reelle.')\n"
        "with smtplib.SMTP('mailpit', 1025, timeout=10) as s:\n"
        "    s.send_message(m)\n"
        "print('ENVOYE')\n"
    )
    cid = etat["recette"]["conteneurs"]["api"]["Id"]
    code, sortie = dans_conteneur(cid, "python", "-c", envoi)
    j.exiger(code == 0 and "ENVOYE" in sortie, "un e-mail part du conteneur api de la RECETTE")

    apres = {env: total(p) for env, p in ports.items()}
    j.info(f"totaux apres envoi  : {apres}")
    # LECON T2-5 : un total qui reste a zero serait indistinguable d'un volume
    # efface. On refuse de conclure si la recette n'a rien recu.
    j.exiger(
        apres["recette"] is not None and apres["recette"] > 0,
        f"le Mailpit de la RECETTE porte {apres['recette']} message(s) — un 0 ne prouverait rien",
    )
    j.exiger(
        apres["recette"] == (avant["recette"] or 0) + 1,
        f"le total de la recette a augmente de exactement 1 "
        f"({avant['recette']} -> {apres['recette']})",
    )
    j.exiger(
        apres["dev"] == avant["dev"],
        f"le total de DEV n'a PAS bouge ({avant['dev']} -> {apres['dev']}) : "
        "les captures d'e-mails sont bien separees",
    )
    print("      NON COUVERT PAR LE LOT 1, et il faut le dire : l'absence de sortie reelle")
    print("      au sens du critere de sortie du LOT 13, et la story MVP-L11-US003. Ce qui")
    print("      est prouve ici : aucun fournisseur reel n'est configure, et l'e-mail emis")
    print("      par la recette reste dans SA capture sans toucher celle du developpement.")


# ===========================================================================


def main() -> int:
    print()
    print("  Les SEPT separations du cahier des charges 22.2 — dev contre recette")
    print()
    j = Journal()

    etat: dict[str, dict] = {}
    for env, fichier in ENVIRONNEMENTS.items():
        chemin = RACINE / fichier
        if not chemin.is_file():
            raise SystemExit(
                f"  ECHEC     {fichier} absent : lancer `make env ENVIRONNEMENT={env}`"
            )
        config = configuration_assemblee(env)
        actifs = conteneurs(config["name"])
        if len(actifs) != SERVICES_ATTENDUS:
            raise SystemExit(
                f"  ECHEC     {env} : {len(actifs)} services en marche sur {SERVICES_ATTENDUS}.\n"
                f"            Ce controle compare deux etats REELS : les deux stacks doivent\n"
                f"            tourner. Lancer `make up ENVIRONNEMENT={env}`."
            )
        etat[env] = {"config": config, "conteneurs": actifs, "env": affectations(chemin)}
        j.info(f"{env:8s} : projet {config['name']!r}, {len(actifs)} services en marche")

    separation_projet(j, etat)
    separation_base(j, etat)
    separation_bucket(j, etat)
    separation_volumes(j, etat)
    separation_secrets(j, etat)
    separation_reseau(j, etat)
    separation_ports(j, etat)
    artefact_en_execution(j, etat)
    architecture_native(j, etat)
    cible_execution(j, etat)
    mailpit_exclusif(j, etat)
    memoire(j, etat)

    return j.conclure("les sept separations du cahier 22.2 sont prouvees sur l'etat reel")


if __name__ == "__main__":
    sys.exit(main())
