#!/usr/bin/env python3
"""Controles des images du projet — statiques, multiarchitecture, fonctionnels.

LOT 1, sous-etape T7, story MVP-L01-US006.

POURQUOI CE SCRIPT EST EN PYTHON ET NON EN SHELL
    Les deux pieges qui ont produit le plus de controles menteurs sur ce projet
    sont propres au shell :

      - le chemin du depot contient une espace — `~/Library/Mobile Documents/` —
        et toute expansion non citee casse la commande. Quatre occurrences :
        T2-3, T3-6, la passation §7.2, et une cinquieme le 29/07/2026 pendant
        cette sous-etape meme ;
      - le code de sortie d'un tuyau est celui du dernier maillon. Cinq
        occurrences : T0-1, T2-4, T3-6, T4-3, T5-5.

    `subprocess.run([...])` sans `shell=True` rend le premier IMPOSSIBLE : les
    arguments sont passes tels quels, aucune redecoupe n'a lieu. Et
    `resultat.returncode` rend le second impossible : il n'y a pas de tuyau dont
    on pourrait lire le mauvais code. Le remede n'est pas la vigilance, c'est le
    choix d'un outil ou le piege n'existe pas.

LA DISCIPLINE APPLIQUEE A CHAQUE CONTROLE, cinq questions
    1. peut-il echouer ?
    2. lit-on son code de sortie ?
    3. annonce-t-il combien d'elements il a examines, et le confronte-t-il a un
       attendu DERIVE de la source ?
    4. quelle valeur produirait l'ECHEC ? si elle est identique a celle du
       succes, le controle ne prouve rien — c'est le defaut T5-6 ;
    5. avant de corriger, qu'est-ce que le correctif casse ? — leçon T6-7.

    La quatrieme est la plus dure et elle a une reponse explicite ici : le
    controle des plateformes interroge aussi une PLATEFORME TEMOIN absente du
    manifeste, `linux/s390x`, et EXIGE que l'inspection echoue. Sans cela, un
    `docker image inspect --platform` qui reussirait pour n'importe quelle valeur
    donnerait exactement la meme observation qu'un manifeste correct.

USAGE
    verifier-images.py statique
    verifier-images.py manifeste <etiquette> [--metadonnees <fichier.json>]
    verifier-images.py registre  <reference@sha256:...>
    verifier-images.py taille    <etiquette> <service> <plafond_mio>
    verifier-images.py fonctionnel <service> <etiquette> --version V --revision R
                                   [--plateforme P] [--cible C]
    verifier-images.py environnement
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

# Les deux plateformes du cahier des charges 22.3, litteralement : « linux/arm64
# pour le Mac M5 » et « linux/amd64 pour un futur serveur x86 ».
PLATEFORMES_ATTENDUES = ("linux/amd64", "linux/arm64")

# Plateforme TEMOIN, volontairement absente de nos manifestes. Le controle exige
# que son inspection ECHOUE : c'est ce qui prouve que l'inspection discrimine.
PLATEFORME_TEMOIN = "linux/s390x"

# Correspondance plateforme -> ce que `uname -m` doit repondre DANS le
# conteneur. C'est la seule valeur qui ne peut pas etre produite par l'autre
# architecture : un controle qui se contenterait de « le conteneur a demarre »
# donnerait la meme observation sur les deux.
MACHINE_ATTENDUE = {"linux/amd64": "x86_64", "linux/arm64": "aarch64"}

SERVICES = ("api", "worker", "web")

# Les sept files du cahier des charges 16.4.
FILES_ATTENDUES = 7

# Image Redis du projet, epinglee par empreinte comme partout ailleurs. Elle sert
# au controle fonctionnel du worker : sans courtier joignable, « le worker
# fonctionne » ne serait qu'« il s'importe ».
IMAGE_REDIS = (
    "redis:8.4-alpine@sha256:bd4a0d37e7cd830117ffec9329052b4a1887afa060c265e1768f82b177ff6f43"
)

ETIQUETTES_OCI = (
    "org.opencontainers.image.title",
    "org.opencontainers.image.source",
    "org.opencontainers.image.version",
    "org.opencontainers.image.revision",
)


class Journal:
    """Compte les controles et retient le premier echec."""

    def __init__(self) -> None:
        self.examines = 0
        self.echecs = 0

    def ok(self, message: str) -> None:
        self.examines += 1
        print(f"    ok       {message}")

    def echec(self, message: str) -> None:
        self.examines += 1
        self.echecs += 1
        print(f"    ECHEC    {message}")

    def info(self, message: str) -> None:
        print(f"    info     {message}")

    def exiger(self, condition: bool, message: str) -> bool:
        if condition:
            self.ok(message)
        else:
            self.echec(message)
        return condition

    def conclure(self, sujet: str, attendus: int | None = None) -> int:
        print()
        if attendus is not None and self.examines != attendus:
            print(
                f"  controles attendus : {attendus}   executes : {self.examines}"
                "   -> ECHEC, le compte ne correspond pas"
            )
            return 1
        print(f"  controles executes : {self.examines}   echecs : {self.echecs}")
        if self.echecs:
            # Formule volontairement explicite : « ECHEC : <assertion positive> »
            # se lit comme une contradiction et fait hesiter le lecteur au pire
            # moment. On nomme ce qui n'est PAS verifie.
            print(f"  --> ECHEC — cette assertion n'est PAS verifiee : {sujet}")
            return 1
        print(f"  --> {sujet}")
        return 0


def lancer(*args: str) -> tuple[int, str]:
    """Executer une commande SANS shell. Rend (code de sortie, sortie fusionnee).

    Aucun tuyau, aucune redecoupe : les deux pieges historiques du projet sont
    structurellement absents.
    """
    # S603 : l'entree vient du Makefile et du workflow, jamais d'un tiers, et
    # `shell=False` est precisement ce qui rend ce script sur — voir l'en-tete.
    r = subprocess.run(list(args), capture_output=True, text=True)  # noqa: S603
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def suivis() -> list[str]:
    code, sortie = lancer("git", "-C", str(RACINE), "ls-files")
    if code != 0:
        raise SystemExit(f"git ls-files a echoue (code {code}) : {sortie}")
    return [ligne for ligne in sortie.split("\n") if ligne]


# ===========================================================================
#  1. Controles statiques — aucun Docker, donc executables dans la tache
#     « qualite » de l'integration continue, qui ne demarre aucun service.
# ===========================================================================

MOTIF_FROM = re.compile(r"^\s*FROM\s+(?P<ref>\S+)(?:\s+AS\s+(?P<alias>\S+))?", re.M | re.I)
MOTIF_IMAGE = re.compile(r"^\s*image:\s*(?P<ref>\S+)", re.M)
MOTIF_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)", re.M)
MOTIF_EMPREINTE_COMMIT = re.compile(r"@[0-9a-f]{40}$")


def references_images(journal: Journal) -> None:
    """Toute reference d'image externe est epinglee par empreinte, aucun `latest`.

    LE PIEGE QUE CE CONTROLE A DU APPRENDRE A EVITER
        Depuis T7, `apps/web/Dockerfile` compte quatre `FROM`, dont deux qui
        designent des ETAPES INTERNES — `FROM socle AS developpement`. Un
        detecteur naif les signalerait « sans empreinte » et le controle
        crierait au loup sur son propre livrable. Les alias declares par `AS`
        sont donc collectes d'abord, puis exclus.
    """
    print("  References d'image dans les fichiers suivis (DEC-443, cahier 23.3)")
    fichiers = [
        f
        for f in suivis()
        if Path(f).name.startswith("Dockerfile") or f.endswith((".yml", ".yaml"))
    ]
    alias: set[str] = set()
    brutes: list[tuple[str, str]] = []
    for f in fichiers:
        chemin = RACINE / f
        if not chemin.is_file():
            continue
        texte = chemin.read_text(encoding="utf-8")
        for m in MOTIF_FROM.finditer(texte):
            if m.group("alias"):
                alias.add(m.group("alias"))
            brutes.append((f, m.group("ref")))
        for m in MOTIF_IMAGE.finditer(texte):
            brutes.append((f, m.group("ref")))

    externes = [(f, r) for f, r in brutes if r not in alias]
    internes = len(brutes) - len(externes)
    journal.info(
        f"{len(fichiers)} fichiers examines, {len(brutes)} references trouvees, "
        f"dont {internes} etapes internes exclues ({', '.join(sorted(alias))})"
    )

    sans_empreinte = [(f, r) for f, r in externes if "@sha256:" not in r]
    avec_latest = [(f, r) for f, r in externes if "latest" in r]
    for f, r in externes:
        marque = "ok      " if "@sha256:" in r else "SANS    "
        print(f"      {marque} {f}  {r[:64]}")

    journal.exiger(
        len(externes) > 0,
        f"{len(externes)} references externes trouvees (0 signifierait un detecteur muet)",
    )
    journal.exiger(
        not sans_empreinte,
        f"toutes epinglees par @sha256 : {len(externes) - len(sans_empreinte)}/{len(externes)}",
    )
    journal.exiger(not avec_latest, f"aucune reference a `latest` : {len(avec_latest)} trouvee(s)")


def actions_epinglees(journal: Journal) -> None:
    """Chaque action GitHub est referencee par empreinte de commit (DEC-475)."""
    print()
    print("  Actions GitHub epinglees par empreinte de commit (DEC-475)")
    fichiers = [f for f in suivis() if f.startswith(".github/workflows/")]
    total = 0
    non_epinglees: list[tuple[str, str]] = []
    for f in fichiers:
        texte = (RACINE / f).read_text(encoding="utf-8")
        for m in MOTIF_USES.finditer(texte):
            ref = m.group("ref")
            total += 1
            if not MOTIF_EMPREINTE_COMMIT.search(ref):
                non_epinglees.append((f, ref))
    journal.info(f"{len(fichiers)} workflows examines, {total} `uses:` trouves")
    for f, r in non_epinglees:
        print(f"      NON EPINGLEE  {f}  {r}")
    journal.exiger(total > 0, f"{total} actions trouvees (0 signifierait un detecteur muet)")
    journal.exiger(
        not non_epinglees,
        f"toutes epinglees par empreinte de 40 hexadecimaux : {total - len(non_epinglees)}/{total}",
    )


# Deux motifs, et il en faut DEUX parce que `latest` peut se presenter sous deux
# formes tres differentes.
MOTIF_TAG_LATEST = re.compile(r":latest\b")
MOTIF_ETIQUETTES = re.compile(r"ETIQUETTES\s*[:=]\s*(?P<valeur>.*)")

# Le registre de publication, seul endroit ou `latest` est interdit. Les
# etiquettes LOCALES de Compose — `onboarding-dev-web:latest`, que Compose
# engendre pour toute image construite sans etiquette explicite — sont
# expressement tolerees par les conventions 4.1, « alias de commodite en
# developpement ». L'interdiction porte sur la PUBLICATION.
REGISTRE_PUBLICATION = "ghcr.io/jonathan2433/onboarding-digital"


def liste_contient_latest(ligne: str) -> bool:
    """La ligne assigne-t-elle une liste d'etiquettes contenant `latest` ?

    UNE SEULE implementation, employee par le controle ET par son temoin. La
    premiere version en avait deux, subtilement differentes : le temoin ne
    normalisait pas les guillemets et echouait donc sur sa propre chaine
    d'epreuve. Un temoin qui n'exerce pas le meme code que le controle ne prouve
    rien du controle — c'est le defaut T3-3, ou un test court-circuitait le point
    d'entree reel.
    """
    m = MOTIF_ETIQUETTES.search(ligne)
    if m is None:
        return False
    valeur = m.group("valeur").replace('"', " ").replace("'", " ")
    return "latest" in valeur.split()


def reference_publiee_latest(ligne: str) -> bool:
    """La ligne reference-t-elle `<registre de publication>/…:latest` ?"""
    if REGISTRE_PUBLICATION not in ligne:
        return False
    return bool(MOTIF_TAG_LATEST.search(ligne))


def etiquette_interdite_publiee(journal: Journal) -> None:
    """Aucun workflow ne publie l'etiquette `latest`.

    Les conventions 4.1 la tolerent comme alias de commodite en developpement et
    l'interdisent comme reference unique de deploiement. Le critere de la fiche 3
    pour T7 dit « aucune reference a `latest` seul ». Arbitrage de Jonathan :
    n'en publier AUCUNE. Une etiquette qui existe finit par etre employee, et
    aucun consommateur n'en a besoin.

    PREMIERE VERSION DE CE CONTROLE, ET POURQUOI ELLE ETAIT MAUVAISE
        Elle cherchait le mot `latest` n'importe ou dans un workflow. Elle a
        donc signale trois fois `runs-on: ubuntu-latest`, qui est un LABEL
        D'EXECUTEUR GitHub et n'a rien a voir avec une etiquette d'image. Un
        controle qui crie au loup sur son propre livrable finit desactive : c'est
        exactement le defaut T6-4, ou mon extracteur d'identifiants echouait pour
        une raison de mise en forme.

    LES DEUX FORMES REELLES, ET UN TEMOIN POSITIF POUR CHACUNE
        - une reference d'image `…:latest`, reconnue par le deux-points ;
        - une valeur d'etiquette nue dans la liste passee a `make images-push`,
          par exemple `ETIQUETTES: "sha-abc1234 develop latest"`.
        Les deux motifs sont eprouves sur des chaines synthetiques avant d'etre
        appliques : sans cela, « 0 occurrence » serait indistinguable d'une
        expression reguliere fausse — defaut T5-7.
    """
    print()
    print("  Etiquettes publiees — `latest` n'en fait pas partie (conventions 4.1)")

    # TEMOINS, dans les deux sens, sur le MEME code que le controle.
    journal.exiger(
        reference_publiee_latest(f"docker build -t {REGISTRE_PUBLICATION}/web:latest .")
        and not reference_publiee_latest("runs-on: ubuntu-latest")
        and not reference_publiee_latest("onboarding-dev-web:latest"),
        "TEMOIN : le detecteur trouve `<registre>/…:latest`, et ignore `ubuntu-latest` "
        "comme l'etiquette locale de Compose",
    )
    journal.exiger(
        liste_contient_latest('ETIQUETTES: "sha-abc1234 develop latest"')
        and liste_contient_latest("ETIQUETTES=develop latest")
        and not liste_contient_latest('ETIQUETTES: "sha-abc1234 develop"'),
        "TEMOIN : le detecteur trouve une etiquette `latest` nue dans une liste, "
        "et ne la trouve pas quand elle est absente",
    )

    fichiers = [f for f in suivis() if f.startswith(".github/workflows/")] + ["Makefile"]
    trouvees = 0
    lignes_examinees = 0
    for f in fichiers:
        for n, ligne in enumerate((RACINE / f).read_text(encoding="utf-8").split("\n"), 1):
            depouillee = ligne.split("#", 1)[0]
            lignes_examinees += 1
            if reference_publiee_latest(depouillee) or liste_contient_latest(depouillee):
                print(f"      TROUVEE  {f}:{n}  {ligne.strip()[:70]}")
                trouvees += 1
    journal.info(
        f"{len(fichiers)} fichiers ({', '.join(fichiers)}), {lignes_examinees} lignes examinees"
    )
    journal.exiger(
        trouvees == 0,
        f"aucune etiquette `latest` destinee a la PUBLICATION ({trouvees} trouvee(s))",
    )


def cible_de_construction_explicite(journal: Journal) -> None:
    """Toute surcouche qui construit `web` nomme sa cible explicitement.

    QUELLE VALEUR PRODUIRAIT L'ECHEC ? Sans `target`, Docker construit la
    DERNIERE etape du Dockerfile, soit `execution`. La stack demarrerait, la page
    s'afficherait, les huit services seraient sains — le rechargement a chaud
    aurait simplement disparu. L'echec est donc SILENCIEUX, et c'est exactement
    pour cela qu'il faut un controle.
    """
    print()
    print("  Cible de construction explicite pour `web` dans chaque surcouche (DEC-479)")
    cibles_connues = {"developpement", "execution"}
    surcouches = sorted(
        f for f in suivis() if re.match(r"infra/compose/docker-compose\.(?!base).*\.ya?ml$", f)
    )
    journal.info(f"{len(surcouches)} surcouche(s) trouvee(s) : {', '.join(surcouches) or 'aucune'}")
    journal.exiger(
        len(surcouches) > 0,
        f"{len(surcouches)} surcouche(s) examinee(s) (0 signifierait un detecteur muet)",
    )
    for f in surcouches:
        texte = (RACINE / f).read_text(encoding="utf-8")
        # Recherche volontairement simple et lisible : le bloc `web:` suivi d'un
        # `target:` dont la valeur est une cible connue du Dockerfile.
        bloc = re.search(r"^\s{2}web:\s*$(?P<corps>(?:\n(?:\s{4,}.*)?)*)", texte, re.M)
        if bloc is None:
            journal.echec(f"{f} : aucun service `web` trouve")
            continue
        m = re.search(r"^\s+target:\s*(?P<cible>\S+)\s*$", bloc.group("corps"), re.M)
        if m is None:
            journal.echec(f"{f} : le service `web` ne nomme AUCUNE cible de construction")
        elif m.group("cible") not in cibles_connues:
            journal.echec(f"{f} : cible `{m.group('cible')}` inconnue du Dockerfile")
        else:
            journal.ok(f"{f} : cible `{m.group('cible')}`")


def commande_statique() -> int:
    print()
    print("  Controles statiques des images — T7, MVP-L01-US006")
    print()
    journal = Journal()
    references_images(journal)
    actions_epinglees(journal)
    etiquette_interdite_publiee(journal)
    cible_de_construction_explicite(journal)
    return journal.conclure(
        "epinglage, etiquetage et selection de cible conformes",
    )


# ===========================================================================
#  2. Coherence de .env avec .env.example
#     `make env` est idempotent : il ne touche PAS un .env existant. Une
#     variable ajoutee a .env.example apres la premiere creation du .env n'y
#     arrive donc JAMAIS. Mesure du 29/07/2026 : APP_REVISION, LOG_MAX_SIZE et
#     LOG_MAX_FILES manquaient depuis T3 et T4. Consequence reelle : Compose
#     substituait une chaine VIDE a ${APP_REVISION}.
#     C'est ECART-022, et ce controle est la parade.
# ===========================================================================

MOTIF_AFFECTATION = re.compile(r"^([A-Z_][A-Z0-9_]*)=")


def noms_declares(chemin: Path) -> list[str]:
    return [
        m.group(1)
        for ligne in chemin.read_text(encoding="utf-8").split("\n")
        if (m := MOTIF_AFFECTATION.match(ligne))
    ]


def commande_environnement(nom_fichier: str = ".env") -> int:
    """Le fichier d'environnement demande declare-t-il toutes les variables du modele ?

    T8 — LE FICHIER EST DESORMAIS UN PARAMETRE, et il devait le devenir.
        Il y a deux environnements, donc deux fichiers : `.env` et `.env.recette`.
        Un controle qui n'aurait examine que le premier aurait laisse le second
        dériver exactement comme ECART-022 l'a montré — c'est-a-dire en silence,
        pendant deux sous-etapes. `make env-check` verifie les DEUX.
    """
    print()
    print(f"  Coherence de {nom_fichier} avec .env.example (ECART-022)")
    print()
    journal = Journal()
    exemple = RACINE / ".env.example"
    reel = RACINE / nom_fichier

    if not reel.is_file():
        journal.echec(f"{nom_fichier} absent : lancer `make env`")
        return journal.conclure(f"{nom_fichier} absent")

    noms_exemple = noms_declares(exemple)
    noms_reel = noms_declares(reel)
    largeur = max(len(".env.example"), len(nom_fichier))
    journal.info(
        f"{'.env.example'.ljust(largeur)} : {len(noms_exemple)} affectations, "
        f"{len(set(noms_exemple))} noms distincts"
    )
    journal.info(
        f"{nom_fichier.ljust(largeur)} : {len(noms_reel)} affectations, "
        f"{len(set(noms_reel))} noms distincts"
    )

    # AUCUN doublon dans le modele. Deux declarations d'une variable, c'est la
    # derniere qui gagne, en silence, le jour ou elles divergent.
    doublons = sorted({n for n in noms_exemple if noms_exemple.count(n) > 1})
    journal.exiger(
        not doublons,
        f"aucune variable declaree deux fois dans .env.example ({len(doublons)} : {doublons})",
    )

    manquantes = [n for n in dict.fromkeys(noms_exemple) if n not in noms_reel]
    for n in manquantes:
        print(f"      MANQUANTE dans {nom_fichier} : {n}")
    journal.exiger(
        not manquantes,
        f"toutes les variables du modele sont dans {nom_fichier} "
        f"({len(set(noms_exemple)) - len(manquantes)}/{len(set(noms_exemple))})",
    )
    if manquantes:
        print()
        print(f"      `make env` NE MET PAS A JOUR un {nom_fichier} existant : c'est voulu,")
        print("      il porte des secrets locaux. Ajoute les lignes manquantes a la main,")
        print("      en reprenant leur valeur de .env.example.")

    return journal.conclure(f"{nom_fichier} declare toutes les variables du modele")


# ===========================================================================
#  3. Manifeste multiarchitecture d'une etiquette LOCALE
# ===========================================================================


def plateformes_du_metadonnees(fichier: Path) -> list[str]:
    """Plateformes reellement construites, lues dans le --metadata-file de buildx.

    buildx depose une cle `buildx.build.provenance/<plateforme>` par plateforme
    construite : le compte et les NOMS viennent donc de la source, pas d'une
    valeur que j'aurais codee en dur.
    """
    donnees = json.loads(fichier.read_text(encoding="utf-8"))
    prefixe = "buildx.build.provenance/"
    return sorted(k[len(prefixe) :] for k in donnees if k.startswith(prefixe))


def commande_manifeste(etiquette: str, metadonnees: Path | None) -> int:
    print()
    print(f"  Manifeste multiarchitecture de `{etiquette}` (cahier 22.3)")
    print()
    journal = Journal()

    if metadonnees is not None:
        donnees = json.loads(metadonnees.read_text(encoding="utf-8"))
        descripteur = donnees.get("containerimage.descriptor") or {}
        type_media = descripteur.get("mediaType", "")
        empreinte = donnees.get("containerimage.digest", "")
        journal.info(f"empreinte de la liste de manifestes : {empreinte}")
        journal.info(f"mediaType : {type_media}")
        # UNE IMAGE SIMPLE ET UNE LISTE DE MANIFESTES SE RESSEMBLENT A
        # L'INSPECTION. C'est le mediaType qui les distingue : `index` ou
        # `manifest.list` pour une liste, `manifest` pour une image unique. Un
        # controle qui ne regarderait que « l'image existe » ne verrait pas la
        # difference — c'est la question 4 de la discipline.
        journal.exiger(
            "index" in type_media or "manifest.list" in type_media,
            f"le descripteur est une LISTE de manifestes et non une image unique ({type_media})",
        )
        construites = plateformes_du_metadonnees(metadonnees)
        journal.info(f"plateformes declarees par buildx : {construites}")
        journal.exiger(
            construites == sorted(PLATEFORMES_ATTENDUES),
            f"exactement {len(PLATEFORMES_ATTENDUES)} plateformes, "
            f"{sorted(PLATEFORMES_ATTENDUES)} — trouve {construites}",
        )

    # Chaque plateforme attendue doit etre inspectable...
    for plateforme in PLATEFORMES_ATTENDUES:
        code, sortie = lancer(
            "docker",
            "image",
            "inspect",
            "--platform",
            plateforme,
            etiquette,
            "--format",
            "{{.Os}}/{{.Architecture}}",
        )
        obtenue = sortie.strip().split("\n")[0] if code == 0 else sortie.strip()[:60]
        journal.exiger(
            code == 0 and obtenue == plateforme,
            f"variante {plateforme} presente et coherente (obtenu : {obtenue})",
        )

    # ... et la plateforme TEMOIN doit ECHOUER. Sans ce controle, une inspection
    # qui reussirait pour n'importe quelle valeur donnerait exactement la meme
    # observation qu'un manifeste correct.
    code, _ = lancer("docker", "image", "inspect", "--platform", PLATEFORME_TEMOIN, etiquette)
    journal.exiger(
        code != 0,
        f"TEMOIN : la plateforme absente {PLATEFORME_TEMOIN} est bien refusee "
        f"(code {code}, un 0 signifierait que l'inspection ne discrimine pas)",
    )

    # Utilisateur non privilegie et etiquettes OCI, POUR CHAQUE variante : une
    # seule des deux pourrait etre conforme.
    for plateforme in PLATEFORMES_ATTENDUES:
        code, sortie = lancer(
            "docker",
            "image",
            "inspect",
            "--platform",
            plateforme,
            etiquette,
            "--format",
            "{{json .Config}}",
        )
        if code != 0:
            journal.echec(f"{plateforme} : inspection de la configuration impossible")
            continue
        config = json.loads(sortie.strip().split("\n")[0])
        utilisateur = (config.get("User") or "").strip()
        journal.exiger(
            utilisateur not in ("", "root", "0"),
            f"{plateforme} : utilisateur non privilegie (`{utilisateur or 'root'}`, cahier 20.1)",
        )
        etiquettes = config.get("Labels") or {}
        absentes = [e for e in ETIQUETTES_OCI if not etiquettes.get(e)]
        journal.exiger(
            not absentes,
            f"{plateforme} : {len(ETIQUETTES_OCI) - len(absentes)}/{len(ETIQUETTES_OCI)} "
            f"etiquettes OCI renseignees" + (f" — absentes : {absentes}" if absentes else ""),
        )

    return journal.conclure(
        f"`{etiquette}` porte les {len(PLATEFORMES_ATTENDUES)} plateformes du cahier 22.3"
    )


# ===========================================================================
#  4. Manifeste d'une reference PUBLIEE dans un registre
# ===========================================================================


def commande_registre(reference: str) -> int:
    print()
    print(f"  Manifeste publie — {reference}")
    print()
    journal = Journal()
    code, sortie = lancer("docker", "buildx", "imagetools", "inspect", "--raw", reference)
    if code != 0:
        journal.echec(f"inspection du registre impossible (code {code}) : {sortie.strip()[:180]}")
        return journal.conclure("manifeste publie illisible")

    index = json.loads(sortie)
    type_media = index.get("mediaType", "")
    journal.exiger(
        "index" in type_media or "manifest.list" in type_media,
        f"le manifeste publie est une LISTE et non une image unique ({type_media})",
    )
    plateformes = []
    for m in index.get("manifests", []):
        p = m.get("platform") or {}
        if p.get("architecture") == "unknown" or p.get("os") == "unknown":
            # Les manifestes d'attestation de buildx portent `unknown/unknown` :
            # ce ne sont pas des variantes executables.
            continue
        plateformes.append(f"{p.get('os')}/{p.get('architecture')}")
    plateformes = sorted(set(plateformes))
    journal.info(f"plateformes publiees : {plateformes}")
    journal.exiger(
        plateformes == sorted(PLATEFORMES_ATTENDUES),
        f"exactement {sorted(PLATEFORMES_ATTENDUES)} — trouve {plateformes}",
    )
    return journal.conclure("le manifeste publie couvre les deux architectures")


# ===========================================================================
#  5. Taille — un plafond declare, et il ECHOUE au-dela
#     Controle demande par ROAD-RSK-030 : « faire echouer la construction si
#     l'image d'execution depasse un plafond declare. Un controle de taille qui
#     n'echoue pas ne sert a rien. »
# ===========================================================================


def taille_mio(etiquette: str, plateforme: str) -> tuple[int, int]:
    """Taille de CONTENU de la variante, en Mio. Rend (taille, nombre de couches).

    `.Size` d'une variante rend la taille de CONTENU — ce que le registre stocke
    et transfere — et non l'usage disque de l'arborescence depaquetee. Mesure du
    29/07/2026 sur l'image `api` arm64 : 115 Mo de contenu contre 473 Mo sur
    disque. Le Makefile explique pourquoi c'est la premiere qu'on plafonne : la
    seconde n'est pas comparable d'une plateforme a l'autre, seule la variante
    native etant depaquetee localement.
    """
    code, sortie = lancer(
        "docker",
        "image",
        "inspect",
        "--platform",
        plateforme,
        etiquette,
        "--format",
        "{{json .RootFS.Layers}}",
    )
    if code != 0:
        raise SystemExit(f"inspection impossible pour {etiquette} {plateforme} : {sortie[:160]}")
    couches = json.loads(sortie.strip().split("\n")[0]) or []
    code, sortie = lancer(
        "docker",
        "image",
        "inspect",
        "--platform",
        plateforme,
        etiquette,
        "--format",
        "{{.Size}}",
    )
    if code != 0:
        raise SystemExit(f"taille illisible pour {etiquette} {plateforme}")
    return round(int(sortie.strip().split("\n")[0]) / 1024 / 1024), len(couches)


def commande_taille(etiquette: str, service: str, plafond: int) -> int:
    print()
    print(
        f"  Taille de CONTENU de `{etiquette}` ({service}) — "
        f"plafond declare {plafond} Mio (ROAD-RSK-030)"
    )
    print("  Taille de contenu : ce que le registre stocke et transfere, non l'usage disque.")
    print()
    journal = Journal()
    for plateforme in PLATEFORMES_ATTENDUES:
        mesure, couches = taille_mio(etiquette, plateforme)
        if mesure <= plafond:
            ecart = f"marge {plafond - mesure} Mio"
        else:
            ecart = f"DEPASSEMENT de {mesure - plafond} Mio"
        journal.exiger(
            mesure <= plafond,
            f"{plateforme} : {mesure} Mio en {couches} couches, plafond {plafond} Mio ({ecart})",
        )
    return journal.conclure(f"`{service}` respecte son plafond de taille")


# ===========================================================================
#  6. Controle FONCTIONNEL — le critere dit « fonctionne », pas « est construite »
# ===========================================================================


def machine_dans_le_conteneur(
    etiquette: str, plateforme: str, commande: list[str]
) -> tuple[int, str]:
    return lancer("docker", "run", "--rm", "--platform", plateforme, etiquette, *commande)


def attendre_http(url: str, essais: int = 150, delai: float = 1.0) -> tuple[int | None, str]:
    """Interroger jusqu'a obtenir une reponse HTTP, code inclus meme sur 4xx/5xx.

    LE BUDGET EST GENEREUX PARCE QUE L'EMULATION EST LENTE, et il ne coute rien
    quand tout va vite : la boucle rend la main des la premiere reponse. Sous
    QEMU, le demarrage d'uvicorn prend un ordre de grandeur de plus qu'en natif.
    Un budget calibre sur le natif ferait echouer le controle pour une raison qui
    n'a rien a voir avec l'image — et le diagnostic couterait cher, l'echec
    ressemblant a « le conteneur ne repond pas ».
    """
    dernier = ""
    for _ in range(essais):
        try:
            # S310 : les URL sont construites ici, en http vers 127.0.0.1.
            with urllib.request.urlopen(url, timeout=3) as r:  # noqa: S310
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:  # 503 EST une reponse, pas une panne
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:  # transport pas encore pret
            dernier = f"{type(e).__name__}: {e}"
            time.sleep(delai)
    return None, dernier


# Les variables que l'API declare avec un defaut VIDE, et que le premier
# garde-fou du cahier 20.3 — « variable obligatoire absente ou vide » — exige
# donc renseignees. Elles ne portent ici que des valeurs de controle : l'API
# refuse de demarrer sans elles, mais n'a pas besoin qu'elles soient joignables
# pour servir `live` et `version`.
#
# **ELLES SONT DERIVEES DE `Parametres.OBLIGATOIRES`, ET NON RECOPIEES.** Ma
# version precedente en listait sept en dur. `T1` du LOT 3 en a ajoute QUATRE au
# titre du moindre privilege (`QO-116`, `DEC-520`), et cette liste ne les a pas
# recues : la publication de `353e570` a donc echoue avec un conteneur qui refusait
# de demarrer — **ce qui est exactement ce que le garde-fou doit faire**.
#
# C'est le §7.16 : `make images-verify` LANCE les conteneurs, et je ne l'avais pas
# rejoue. Et c'est `ECART-021` : une liste recopiee vieillit au premier ajout.
# Deriver de la source rend l'oubli impossible.
def _variables_obligatoires() -> tuple[str, ...]:
    """Les variables obligatoires, LUES dans `settings.py` — sans l'importer.

    **PAR `ast`, ET NON PAR UN IMPORT.** Ce script est invoque par `python3`, hors
    de l'environnement virtuel : `images-check` est dans `make check` et ne
    demande ni Docker ni dependance. Importer `Parametres` exigerait `pydantic`,
    et casserait donc `make check` — mesure du 20/08/2026,
    « ModuleNotFoundError: No module named 'pydantic' ».

    Lire l'arbre syntaxique n'exige rien, et une forme inattendue fait ECHOUER la
    lecture en la nommant, au lieu de rendre une liste vide qui passerait.
    """
    fichier = (
        Path(__file__).resolve().parents[2]
        / "apps"
        / "api"
        / "app"
        / "configuration"
        / "settings.py"
    )
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        cibles: list[ast.expr] = []
        if isinstance(noeud, ast.AnnAssign):
            cibles = [noeud.target]
        elif isinstance(noeud, ast.Assign):
            cibles = list(noeud.targets)
        else:
            continue
        if not any(isinstance(c, ast.Name) and c.id == "OBLIGATOIRES" for c in cibles):
            continue
        #  La forme est `Field(default=(...), exclude=True)` : on cherche le
        #  premier tuple entierement compose de chaines.
        for interne in ast.walk(noeud):
            if not isinstance(interne, ast.Tuple) or not interne.elts:
                continue
            valeurs = [
                element.value
                for element in interne.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if len(valeurs) == len(interne.elts):
                return tuple(valeurs)
    message = (
        f"`OBLIGATOIRES` introuvable ou de forme inattendue dans {fichier.name} : "
        f"la derivation des variables obligatoires est impossible"
    )
    raise SystemExit(message)


VARIABLES_DU_REFUS = _variables_obligatoires()

#  Une valeur de controle par variable obligatoire, plus les deux reglages que le
#  garde-fou du format de journal exige.
CONFIGURATION_MINIMALE = (
    "APP_ENV=development",
    "LOG_FORMAT=json",
    "POSTGRES_DB=verification_t7",
    *(
        f"{nom}=verification-sans-valeur-reelle"
        for nom in VARIABLES_DU_REFUS
        if nom != "POSTGRES_DB"
    ),
)


def refus_de_demarrer(journal: Journal, etiquette: str, plateforme: str) -> None:
    """L'image REFUSE de demarrer sans configuration, en nommant les variables.

    C'est le §20.3 du cahier — « refus de demarrer » — et jusqu'ici il n'etait
    eprouve que par des tests unitaires, sur l'arborescence du depot. Ce controle
    l'eprouve sur L'IMAGE, celle qui sera publiee et deployee.

    Ce controle est ne d'un defaut de ma propre sonde : elle ne fournissait que
    deux variables, l'API refusait de demarrer, et j'ai d'abord lu cela comme une
    panne de l'image. C'etait l'image qui avait raison.

    Il verifie aussi que le message NOMME la variable et JAMAIS sa valeur, ce que
    la politique de configuration §6 exige — un message de configuration finit
    dans un journal ou une capture d'ecran.
    """
    code, sortie = lancer(
        "docker",
        "run",
        "--rm",
        "--platform",
        plateforme,
        "--env",
        "APP_ENV=development",
        "--env",
        "LOG_FORMAT=json",
        etiquette,
    )
    journal.exiger(
        code != 0,
        f"{plateforme} : sans configuration, l'image REFUSE de demarrer (code {code}, cahier 20.3)",
    )
    nommees = [v for v in VARIABLES_DU_REFUS if v in sortie]
    journal.exiger(
        len(nommees) == len(VARIABLES_DU_REFUS),
        f"{plateforme} : le refus NOMME {len(nommees)} variables sur "
        f"{len(VARIABLES_DU_REFUS)} attendues",
    )
    # Aucune VALEUR ne doit fuir. On cherche les valeurs de controle qu'on
    # s'apprete a employer : si le message les recrachait, la politique §6 serait
    # enfreinte.
    fuites = [v for v in ("verification-sans-valeur-reelle", "verification_t7") if v in sortie]
    journal.exiger(
        not fuites,
        f"{plateforme} : le message ne divulgue aucune valeur ({len(fuites)} fuite(s))",
    )


class Attendus:
    """Version et revision que la CONSTRUCTION a declarees.

    POURQUOI ON COMPARE A UNE VALEUR ATTENDUE, ET NON A « DIFFERENT DU DEFAUT »
        La premiere version de ces controles exigeait que la version lue differe
        de `0.0.0-dev`. Mesure du 29/07/2026, execution 30442686377 : le controle
        a ECHOUE sur une image parfaitement correcte.

        Motif : `DEC-428` jalonne les versions sur les portes et les pose en TAGS.
        Sur une branche de travail comme sur `develop`, il n'existe donc AUCUNE
        version, et le workflow publie honnetement `0.0.0-dev`. La valeur injectee
        EST le defaut. « Different du defaut » etait donc une assertion qu'une
        situation legitime ne peut pas satisfaire — le defaut T5-6 pris a l'envers :
        un succes qui produit la meme observation qu'un echec.

        La revision, elle, est toujours significative : c'est l'empreinte du
        commit. C'est elle qui prouvait deja que le mecanisme fonctionne —
        `revision='b07f46c'`, et non `inconnue`.

        Comparer a l'attendu est **plus fort** que comparer au defaut : cela
        prouve que l'image porte LA version avec laquelle elle a ete construite,
        et non seulement UNE version non nulle.

        Les attendus sont OBLIGATOIRES. En leur absence le controle echoue, au
        lieu de se degrader en silence en une assertion plus faible.
    """

    def __init__(self, version: str | None, revision: str | None) -> None:
        self.version = version
        self.revision = revision

    def valides(self, journal: Journal) -> bool:
        if self.version and self.revision:
            return True
        journal.echec(
            "les valeurs ATTENDUES de version et de revision ne sont pas fournies : "
            "passer --version et --revision. Sans elles ce controle se degraderait "
            "en une assertion plus faible, en silence"
        )
        return False


def fonctionnel_api(
    journal: Journal, etiquette: str, plateforme: str, port: int, attendus: Attendus
) -> None:
    refus_de_demarrer(journal, etiquette, plateforme)

    nom = f"t7-verif-api-{plateforme.replace('/', '-')}"
    lancer("docker", "rm", "--force", nom)
    arguments = [
        "docker",
        "run",
        "--detach",
        "--name",
        nom,
        "--platform",
        plateforme,
        "--publish",
        f"127.0.0.1:{port}:8000",
    ]
    for variable in CONFIGURATION_MINIMALE:
        arguments += ["--env", variable]
    # AUCUNE dependance n'est JOIGNABLE, et c'est voulu : voir le controle
    # `ready` ci-dessous, dont c'est tout l'interet.
    code, sortie = lancer(*arguments, etiquette)
    if code != 0:
        journal.echec(f"{plateforme} : le conteneur api n'a pas demarre : {sortie.strip()[:160]}")
        return
    try:
        statut, corps = attendre_http(f"http://127.0.0.1:{port}/health/live")
        journal.exiger(
            statut == 200 and '"vivant"' in corps,
            f"{plateforme} : /health/live -> {statut} {corps.strip()[:60]}",
        )

        statut, corps = attendre_http(f"http://127.0.0.1:{port}/health/version")
        charge = json.loads(corps) if statut == 200 else {}
        journal.exiger(statut == 200, f"{plateforme} : /health/version -> {statut}")
        # LE CONTROLE DISCRIMINANT DE L'INJECTION : la valeur lue est-elle CELLE
        # que la construction a declaree ? Voir la classe `Attendus` pour le
        # motif — comparer au defaut echouait sur une image correcte.
        journal.exiger(
            charge.get("version") == attendus.version,
            f"{plateforme} : /health/version rend la version DE LA CONSTRUCTION "
            f"(lu {charge.get('version')!r}, attendu {attendus.version!r})",
        )
        journal.exiger(
            charge.get("revision") == attendus.revision,
            f"{plateforme} : /health/version rend la revision DE LA CONSTRUCTION "
            f"(lu {charge.get('revision')!r}, attendu {attendus.revision!r})",
        )

        # `ready` SANS dependances : 503 avec les trois dependances NOMMEES
        # indisponibles. C'est une preuve plus forte qu'un 200 — elle montre que
        # l'application est entierement montee et qu'elle sonde reellement. Un
        # conteneur qui aurait seulement demarre sans monter ses routes
        # repondrait 404, pas 503 avec cette charge utile.
        statut, corps = attendre_http(f"http://127.0.0.1:{port}/health/ready")
        try:
            deps = json.loads(corps).get("dependances", [])
        except Exception:
            deps = []
        indisponibles = [d.get("nom") for d in deps if d.get("statut") != "disponible"]
        journal.exiger(
            statut == 503 and len(indisponibles) == 3,
            f"{plateforme} : /health/ready -> {statut}, "
            f"{len(indisponibles)} dependances nommees indisponibles sur 3 attendues "
            f"({indisponibles})",
        )

        code, sortie = lancer("docker", "exec", nom, "uname", "-m")
        journal.exiger(
            code == 0 and sortie.strip() == MACHINE_ATTENDUE[plateforme],
            f"{plateforme} : `uname -m` DANS le conteneur -> {sortie.strip()!r}, "
            f"attendu {MACHINE_ATTENDUE[plateforme]!r}",
        )
    finally:
        lancer("docker", "rm", "--force", nom)


def fonctionnel_worker(
    journal: Journal, etiquette: str, plateforme: str, attendus: Attendus
) -> None:
    """Le worker « fonctionne » : il ping son courtier et declare ses 7 files.

    C'est le bar du healthcheck que le projet emploie deja depuis T3 —
    `courtier.client.ping()` — et non un simple import. Un Redis jetable est donc
    demarre : sans courtier joignable, « le worker fonctionne » ne voudrait dire
    que « le module s'importe ».
    """
    suffixe = plateforme.replace("/", "-")
    reseau = f"t7-verif-net-{suffixe}"
    nom_redis = f"t7-verif-redis-{suffixe}"
    lancer("docker", "rm", "--force", nom_redis)
    lancer("docker", "network", "rm", reseau)
    code, sortie = lancer("docker", "network", "create", reseau)
    if code != 0:
        journal.echec(f"{plateforme} : reseau jetable impossible : {sortie.strip()[:120]}")
        return
    try:
        code, sortie = lancer(
            "docker",
            "run",
            "--detach",
            "--name",
            nom_redis,
            "--platform",
            plateforme,
            "--network",
            reseau,
            "--network-alias",
            "redis",
            IMAGE_REDIS,
            "redis-server",
            "--requirepass",
            "verif-t7",
            # `--ignore-warnings ARM64-COW-BUG`, ET IL FAUT DIRE POURQUOI.
            #
            # Sous emulation QEMU, Redis detecte le bug copie-sur-ecriture connu
            # d'ARM64 et REFUSE DE DEMARRER, volontairement, pour ne pas
            # corrompre ses donnees a la prochaine sauvegarde d'arriere-plan.
            # Mesure du 29/07/2026, execution 30452743418 : « Your kernel has a
            # bug that could lead to data corruption during background save.
            # Redis will now exit to prevent data corruption », conteneur
            # `exited code=1`. Aucune attente n'y changeait rien : ce n'etait ni
            # un delai, ni notre image.
            #
            # POURQUOI C'EST ACCEPTABLE ICI, ET NULLE PART AILLEURS
            #   Ce Redis est un DOUBLE JETABLE. `--save ""` desactive toute
            #   sauvegarde, il ne porte aucune donnee, et il vit le temps d'un
            #   PING. L'avertissement porte sur une corruption de donnees ; il
            #   n'y a pas de donnee.
            #
            #   Le Redis du projet, lui, tourne NATIVEMENT sur le Mac `aarch64`
            #   et n'a jamais declenche cet avertissement. Ce drapeau n'a RIEN a
            #   faire dans `docker-compose.base.yml` : l'y porter transformerait
            #   un garde-fou contre la perte de donnees en nuisance silencieuse.
            #   C'est exactement la classe de correctif que `T6-7` a appris a
            #   mesurer avant d'appliquer.
            "--ignore-warnings",
            "ARM64-COW-BUG",
            "--save",
            "",
        )
        if code != 0:
            journal.echec(f"{plateforme} : Redis jetable n'a pas demarre : {sortie.strip()[:160]}")
            return

        # ATTENDRE QUE REDIS SOIT PRET, et compter l'attente.
        #
        # Sans cela, la sonde du worker interroge un courtier qui n'ecoute pas
        # encore. En natif Redis est pret avant que la sonde ne demarre, et le
        # defaut reste latent ; SOUS EMULATION QEMU il ne l'est pas. Mesure du
        # 29/07/2026, execution 30451127513 : `connect_check_health` a echoue sur
        # `linux/arm64` alors que la meme sonde passait sur `linux/amd64`.
        #
        # C'est la course que `depends_on: service_healthy` existe pour eviter, et
        # c'est la lecon de T6-2 dans un autre habit : ma sonde n'avait jamais
        # tourne qu'en natif, donc elle n'etait pas eprouvee.
        pret = 0
        for tentative in range(1, 121):
            code, sortie = lancer(
                "docker",
                "exec",
                nom_redis,
                "redis-cli",
                "-a",
                "verif-t7",
                "--no-auth-warning",
                "ping",
            )
            if code == 0 and "PONG" in sortie:
                pret = tentative
                break
            time.sleep(1.0)
        if not journal.exiger(
            pret > 0,
            f"{plateforme} : le Redis jetable repond PONG "
            f"({'apres ' + str(pret) + ' tentative(s)' if pret else 'JAMAIS en 120 s'})",
        ):
            # UN CONTROLE QUI ECHOUE DOIT DIRE POURQUOI, surtout quand la cause
            # est dans une dependance qu'il a LUI-MEME demarree. La premiere
            # version se contentait de « JAMAIS en 120 s » : impossible de
            # distinguer un Redis lent d'un Redis mort. C'est la lecon de `T7-1`,
            # ou un message masque avait envoye le diagnostic dans le fosse.
            code, sortie = lancer(
                "docker",
                "inspect",
                nom_redis,
                "--format",
                "{{.State.Status}} code={{.State.ExitCode}} oom={{.State.OOMKilled}}",
            )
            journal.info(f"etat du conteneur Redis : {sortie.strip()[:120]}")
            code, sortie = lancer("docker", "logs", "--tail", "20", nom_redis)
            for ligne in sortie.strip().split("\n")[-20:]:
                if ligne.strip():
                    print(f"      redis | {ligne.strip()[:140]}")
            return
        sonde = (
            "import os, platform;"
            "from worker.main import courtier, files_declarees;"
            "assert courtier.client.ping() is True;"
            "print(platform.machine(), os.environ.get('APP_VERSION'),"
            " os.environ.get('APP_REVISION'), len(files_declarees()))"
        )
        code, sortie = lancer(
            "docker",
            "run",
            "--rm",
            "--platform",
            plateforme,
            "--network",
            reseau,
            "--env",
            "REDIS_HOST=redis",
            "--env",
            "REDIS_PASSWORD=verif-t7",
            "--env",
            "APP_ENV=development",
            "--env",
            "LOG_FORMAT=json",
            etiquette,
            "python",
            "-c",
            sonde,
        )
        derniere = [ligne for ligne in sortie.strip().split("\n") if ligne.strip()]
        valeurs = derniere[-1].split() if derniere else []
        if code != 0 or len(valeurs) != 4:
            journal.echec(
                f"{plateforme} : la sonde du worker a echoue (code {code}) : "
                f"{sortie.strip()[-200:]}"
            )
            return
        machine, version, revision, files = valeurs
        journal.exiger(
            machine == MACHINE_ATTENDUE[plateforme],
            f"{plateforme} : `platform.machine()` -> {machine!r}, "
            f"attendu {MACHINE_ATTENDUE[plateforme]!r}",
        )
        journal.exiger(
            version == attendus.version,
            f"{plateforme} : APP_VERSION est celle DE LA CONSTRUCTION "
            f"(lu {version!r}, attendu {attendus.version!r})",
        )
        journal.exiger(
            revision == attendus.revision,
            f"{plateforme} : APP_REVISION est celle DE LA CONSTRUCTION "
            f"(lu {revision!r}, attendu {attendus.revision!r})",
        )
        journal.exiger(
            files == str(FILES_ATTENDUES),
            f"{plateforme} : {files} files declarees sur {FILES_ATTENDUES} (cahier 16.4), "
            f"et le ping du courtier Redis a REUSSI",
        )
    finally:
        lancer("docker", "rm", "--force", nom_redis)
        lancer("docker", "network", "rm", reseau)


MOTIF_CLIENT_VITE = re.compile(r"/@vite/client")


def fonctionnel_web(
    journal: Journal, etiquette: str, plateforme: str, port: int, *, cible: str
) -> None:
    """La page est servie, et le mode de service est DISCRIMINE.

    Controle propose par ROAD-RSK-031 pour T8, avance ici parce que T7 produit
    les deux cibles : la page servie en execution ne doit porter AUCUNE reference
    a `/@vite/client`. Et le compte sur la cible de DEVELOPPEMENT est le temoin
    positif : il prouve que le detecteur sait trouver le motif. Sans ce second
    compte, « 0 occurrence » serait indistinguable d'une expression reguliere
    fausse — c'est exactement le defaut T5-7.
    """
    nom = f"t7-verif-web-{cible}-{plateforme.replace('/', '-')}"
    lancer("docker", "rm", "--force", nom)
    code, sortie = lancer(
        "docker",
        "run",
        "--detach",
        "--name",
        nom,
        "--platform",
        plateforme,
        "--publish",
        f"127.0.0.1:{port}:5173",
        etiquette,
    )
    if code != 0:
        journal.echec(f"{plateforme} : le conteneur web n'a pas demarre : {sortie.strip()[:160]}")
        return
    try:
        statut, corps = attendre_http(f"http://127.0.0.1:{port}/")
        journal.exiger(
            statut == 200 and "<div id=" in corps,
            f"{plateforme} {cible} : GET / -> {statut}, {len(corps)} octets",
        )
        occurrences = len(MOTIF_CLIENT_VITE.findall(corps))
        if cible == "execution":
            journal.exiger(
                occurrences == 0,
                f"{plateforme} execution : {occurrences} reference(s) a /@vite/client, "
                f"0 attendue — c'est un artefact construit, pas un serveur de developpement",
            )
            journal.exiger(
                "/assets/" in corps,
                f"{plateforme} execution : la page reference bien /assets/, "
                f"donc un artefact empaquete par Vite",
            )
        else:
            journal.exiger(
                occurrences >= 1,
                f"TEMOIN POSITIF — {plateforme} developpement : {occurrences} reference(s) a "
                f"/@vite/client, >= 1 attendue. Le detecteur sait donc trouver le motif",
            )
        code, sortie = lancer("docker", "exec", nom, "uname", "-m")
        journal.exiger(
            code == 0 and sortie.strip() == MACHINE_ATTENDUE[plateforme],
            f"{plateforme} : `uname -m` DANS le conteneur -> {sortie.strip()!r}, "
            f"attendu {MACHINE_ATTENDUE[plateforme]!r}",
        )
    finally:
        lancer("docker", "rm", "--force", nom)


def commande_fonctionnel(
    service: str, etiquette: str, plateformes: list[str], cible: str, attendus: Attendus
) -> int:
    print()
    print(f"  Controle FONCTIONNEL de `{service}` — {etiquette}")
    print("  Le critere dit « fonctionne », pas « est construite » : les conteneurs sont LANCES.")
    print(f"  Identite attendue : version={attendus.version!r} revision={attendus.revision!r}")
    print()
    journal = Journal()
    # `web` ne porte pas d'identite lisible a l'execution : l'artefact statique
    # n'expose ni endpoint ni variable d'environnement. Ses etiquettes OCI sont
    # verifiees par la commande `manifeste`.
    if service in ("api", "worker") and not attendus.valides(journal):
        return journal.conclure(f"identite attendue de `{service}` non fournie")
    port = {"api": 18901, "web": 18902}.get(service, 0)
    for plateforme in plateformes:
        if service == "api":
            fonctionnel_api(journal, etiquette, plateforme, port, attendus)
            port += 1
        elif service == "worker":
            fonctionnel_worker(journal, etiquette, plateforme, attendus)
        elif service == "web":
            fonctionnel_web(journal, etiquette, plateforme, port, cible=cible)
            port += 1
        else:
            journal.echec(f"service inconnu : {service}")
    return journal.conclure(f"`{service}` fonctionne sur {', '.join(plateformes)}")


# ===========================================================================


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    commande = argv[1]
    if commande == "statique":
        return commande_statique()
    if commande == "environnement":
        fichier = ".env"
        if "--fichier" in argv:
            fichier = argv[argv.index("--fichier") + 1]
        return commande_environnement(fichier)
    if commande == "manifeste":
        metadonnees = None
        if "--metadonnees" in argv:
            metadonnees = Path(argv[argv.index("--metadonnees") + 1])
        return commande_manifeste(argv[2], metadonnees)
    if commande == "registre":
        return commande_registre(argv[2])
    if commande == "taille":
        return commande_taille(argv[2], argv[3], int(argv[4]))
    if commande == "fonctionnel":
        service, etiquette = argv[2], argv[3]
        cible = "execution"
        if "--cible" in argv:
            cible = argv[argv.index("--cible") + 1]
        plateformes = list(PLATEFORMES_ATTENDUES)
        if "--plateforme" in argv:
            plateformes = [argv[argv.index("--plateforme") + 1]]
        attendus = Attendus(
            argv[argv.index("--version") + 1] if "--version" in argv else None,
            argv[argv.index("--revision") + 1] if "--revision" in argv else None,
        )
        return commande_fonctionnel(service, etiquette, plateformes, cible, attendus)
    print(f"commande inconnue : {commande}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
