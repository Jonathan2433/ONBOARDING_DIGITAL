#!/usr/bin/env python3
"""Deux conteneurs de cette machine reclament-ils le meme port de l'hote ?

LOT 1, correctif posterieur a la porte `G1`. Cahier des charges 22.2 — « ports
distincts » ; `DEC-460` — publications limitees a `127.0.0.1`.

POURQUOI CE CONTROLE EXISTE, ET IL EST NE D'UN DEFAUT REEL

    En `T8`, la bande de ports de la recette a ete choisie apres avoir mesure que
    `8080`, `8443`, `15432`, `16379`, `18025`, `19000` et `19001` etaient LIBRES.
    La mesure employait `lsof -nP -iTCP -sTCP:LISTEN` : elle regardait ce qui
    ECOUTAIT.

    Le 12/08/2026, `docker compose -p observatoire-ecom-studio start` a echoue :

        Bind for 127.0.0.1:8080 failed: port is already allocated

    Le projet tiers DECLARE `127.0.0.1:8080` depuis toujours. Il etait simplement
    ARRETE au moment de ma mesure — et un conteneur arrete declare ses ports sans
    en occuper aucun. **La mesure etait juste a sa date ; la METHODE etait
    incomplete.**

    Ce controle mesure donc ce que les conteneurs DECLARENT, arretes compris.
    C'est la seule vue qui reponde a la question posee : « ce port sera-t-il
    disponible quand ce projet demarrera ? »

    La meme mesure a d'ailleurs revele un second conflit, celui-la anterieur au
    projet : `5432`, entre `onboarding-dev` et `ticket_master`, arrete depuis
    quatre semaines et donc jamais manifeste.

CE QU'IL EXIGE, ET CE QU'IL RAPPORTE SANS EXIGER — le parti de `DEC-482`

    Il ECHOUE sur une collision entre DEUX DE NOS ENVIRONNEMENTS : celle-la est
    de notre ressort, elle enfreint la septieme separation du cahier 22.2, et
    elle doit bloquer.

    Il RAPPORTE VISIBLEMENT une collision avec un projet ETRANGER, sans echouer :
    nous ne maitrisons pas les ports d'un projet tiers, et faire echouer
    `make up` pour cette raison le rendrait inutilisable. Mais le taire
    reviendrait a laisser l'operateur decouvrir le probleme au demarrage, avec un
    message de Docker qui ne nomme pas le coupable.

    Un controle qui exige plus que ce qu'il maitrise finit desactive : c'est la
    lecon du §7.20 de la passation, nee de l'isolement reseau en `T8`.

QUAND IL NE PEUT PAS MESURER, IL LE DIT

    Si le demon Docker ne repond pas, il sort en 0 en annoncant qu'il n'a rien
    pu mesurer, plutot que de conclure « aucune collision ». C'est la lecon du
    §7.21 : dire « indetermine » plutot que trancher.

POURQUOI EN PYTHON
    `subprocess.run([...])` sans shell ne redecoupe aucun argument. Le depot vit
    sous « ~/Library/Mobile Documents/ », dont le chemin porte une espace, et ce
    piege a produit CINQ defauts sur ce projet — dont trois dans la seule session
    du 12/08/2026, apres avoir ete cite. La parade n'est pas la vigilance, c'est
    le choix d'un outil ou l'erreur n'existe pas.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
COMPOSE_DIR = RACINE / "infra" / "compose"

MOTIF_PROJET = re.compile(r"^COMPOSE_PROJECT_NAME=(.+)$", re.M)


def lancer(*commande: str) -> tuple[int, str]:
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # precisement ce qui rend ce script sur — voir l'en-tete.
    p = subprocess.run(  # noqa: S603
        list(commande), capture_output=True, text=True, cwd=RACINE
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def nos_projets() -> set[str]:
    """Les noms de projet Compose QUI SONT LES NOTRES, derives du disque.

    Ils sont lus dans les fichiers d'environnement, pas devines a partir d'un
    prefixe : un projet nomme `onboarding-autre-chose` par quelqu'un d'autre ne
    doit pas etre pris pour un des notres, et un renommage de nos environnements
    ne doit pas rendre ce controle muet.

    La liste des environnements vient elle-meme des surcouches Compose presentes,
    comme le `Makefile` le fait pour valider `ENVIRONNEMENT`.
    """
    projets: set[str] = set()
    for surcouche in sorted(COMPOSE_DIR.glob("docker-compose.*.yml")):
        nom = surcouche.name.removeprefix("docker-compose.").removesuffix(".yml")
        if nom == "base":
            continue
        suffixe = "" if nom == "dev" else f".{nom}"
        fichier = RACINE / f".env{suffixe}"
        if not fichier.is_file():
            continue
        trouve = MOTIF_PROJET.search(fichier.read_text(encoding="utf-8"))
        if trouve:
            projets.add(trouve.group(1).strip())
    return projets


def ports_de_nos_environnements() -> dict[int, set[tuple[str, str]]]:
    """Les ports que NOS environnements declarent, SANS QU'AUCUN CONTENEUR EXISTE.

    POURQUOI CETTE SOURCE EN PLUS DES CONTENEURS, et c'est le point qui rend ce
    controle utile plutot que seulement informatif.

        Ma premiere version ne lisait que les conteneurs existants. Mesure du
        12/08/2026 : `make down-recette` SUPPRIME les conteneurs — ce n'est pas un
        arret, c'est un retrait. Un environnement arrete ne declare donc plus
        rien, et le controle devenait aveugle a lui.

        Consequence : il n'aurait PAS attrape le defaut qui l'a fait naitre. Au
        moment ou j'ai choisi la bande de ports de la recette en `T8`, aucun
        conteneur de recette n'existait encore.

        `docker compose config` rend la configuration ASSEMBLEE sans rien
        demarrer : c'est la seule vue qui reponde a « quel port ce projet
        reclamera-t-il quand il demarrera ? »
    """
    par_port: dict[int, set[tuple[str, str]]] = defaultdict(set)
    for surcouche in sorted(COMPOSE_DIR.glob("docker-compose.*.yml")):
        nom = surcouche.name.removeprefix("docker-compose.").removesuffix(".yml")
        if nom == "base":
            continue
        suffixe = "" if nom == "dev" else f".{nom}"
        fichier_env = RACINE / f".env{suffixe}"
        if not fichier_env.is_file():
            continue
        code, sortie = lancer(
            "docker",
            "compose",
            "--env-file",
            str(fichier_env),
            "-f",
            str(COMPOSE_DIR / "docker-compose.base.yml"),
            "-f",
            str(surcouche),
            "config",
            "--format",
            "json",
        )
        if code != 0:
            continue
        assemblee = json.loads(sortie)
        projet = assemblee.get("name", nom)
        for service, definition in (assemblee.get("services") or {}).items():
            for publication in definition.get("ports") or []:
                publie = publication.get("published")
                if publie:
                    par_port[int(publie)].add((projet, f"{service} (declare)"))
    return par_port


def declarations() -> dict[int, set[tuple[str, str]]]:
    """Les ports d'hote DECLARES par tous les conteneurs, ARRETES COMPRIS.

    C'est le coeur du controle. `docker ps` sans `-a` ne verrait que les
    conteneurs en marche, et manquerait donc exactement le cas qui a produit le
    defaut : un projet arrete qui reclamera son port au prochain demarrage.
    """
    code, sortie = lancer("docker", "ps", "-a", "-q")
    if code != 0:
        raise RuntimeError(sortie)
    identifiants = [x for x in sortie.split("\n") if x]
    par_port: dict[int, set[tuple[str, str]]] = defaultdict(set)
    for cid in identifiants:
        code, brut = lancer("docker", "inspect", cid)
        if code != 0:
            continue
        details = json.loads(brut)[0]
        nom = details.get("Name", "").lstrip("/")
        projet = (details.get("Config", {}).get("Labels") or {}).get(
            "com.docker.compose.project", "(hors compose)"
        )
        liaisons = (details.get("HostConfig", {}) or {}).get("PortBindings") or {}
        for interne, cibles in liaisons.items():
            for cible in cibles or []:
                port = cible.get("HostPort")
                if port:
                    par_port[int(port)].add((projet, f"{nom} ({interne})"))
    return par_port


def main() -> int:
    print()
    print("  Collisions de ports d'hote, conteneurs ARRETES COMPRIS")

    try:
        par_port = declarations()
    except RuntimeError as cause:
        # INDETERMINE, et on le dit. Conclure « aucune collision » sans avoir pu
        # mesurer serait un controle menteur.
        print("    info     le demon Docker ne repond pas : RIEN N'A PU ETRE MESURE")
        print(f"             {str(cause)[:120]}")
        print("             Ce controle ne conclut donc PAS a l'absence de collision.")
        return 0

    notres = nos_projets()

    # LES DEUX SOURCES SONT FUSIONNEES, et il en faut deux :
    #   - les conteneurs existants couvrent les projets ETRANGERS, dont nous ne
    #     connaissons aucun fichier ;
    #   - la configuration assemblee couvre NOS environnements meme quand aucun
    #     conteneur n'existe, ce qui est le cas apres un `down`.
    # Sans la seconde, le controle serait aveugle a un environnement arrete —
    # donc au defaut meme qui l'a fait naitre.
    depuis_compose = ports_de_nos_environnements()
    for port, proprietaires in depuis_compose.items():
        par_port[port].update(proprietaires)

    projets_assembles = {p for v in depuis_compose.values() for p, _ in v}
    print(f"    info     nos projets, derives du disque : {sorted(notres) or 'aucun'}")
    print(f"    info     {len(par_port)} ports declares, deux sources confrontees :")
    print("               conteneurs existants, arretes compris")
    print(
        f"               configuration assemblee de {len(projets_assembles)} de nos environnements"
    )

    # UN DETECTEUR MUET DIRAIT « aucune collision » SUR UNE MACHINE VIDE.
    if not par_port:
        print("    info     aucun port declare nulle part : rien a comparer")
        return 0
    if not notres:
        print("    info     aucun fichier d'environnement lisible : nos projets sont inconnus")
        print("             Ce controle ne peut pas distinguer les notres des etrangers.")
        return 0

    internes: list[str] = []
    etrangeres: list[str] = []
    for port in sorted(par_port):
        proprietaires = par_port[port]
        projets = {p for p, _ in proprietaires}
        if len(projets) < 2:
            continue
        nos_impliques = projets & notres
        detail = ", ".join(f"{p}/{c}" for p, c in sorted(proprietaires))
        if len(nos_impliques) >= 2:
            internes.append(f"{port} — {detail}")
        elif nos_impliques:
            etrangeres.append(f"{port} — {detail}")

    # 1. CE QUI EST DE NOTRE RESSORT : deux de nos environnements sur le meme
    #    port enfreignent la septieme separation du cahier 22.2. Cela bloque.
    if internes:
        print(f"    ECHEC    {len(internes)} collision(s) ENTRE NOS PROPRES ENVIRONNEMENTS :")
        for ligne in internes:
            print(f"               {ligne}")
        print("             Le cahier 22.2 exige des ports DISTINCTS entre environnements.")
        print("             Corrige la bande de ports de l'un des deux.")
        return 1
    print("    ok       aucune collision entre nos propres environnements")

    # 2. CE QUE NOUS NE MAITRISONS PAS : rapporte visiblement, sans echouer.
    if etrangeres:
        print(f"    RESIDUEL {len(etrangeres)} collision(s) avec un projet ETRANGER a ce depot :")
        for ligne in etrangeres:
            print(f"               {ligne}")
        print("             Les deux ne pourront pas tourner en meme temps : le second a")
        print("             demarrer echouera sur « port is already allocated ».")
        print("             Ce n'est PAS un echec ici — nous ne maitrisons pas les ports")
        print("             d'un projet tiers — mais il faut le savoir avant de le")
        print("             decouvrir au demarrage, ou Docker ne nomme pas le coupable.")
        print("             Remede immediat : arreter l'un des deux.")
    else:
        print("    ok       aucune collision avec un projet etranger")

    return 0


if __name__ == "__main__":
    sys.exit(main())
