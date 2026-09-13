#!/usr/bin/env python3
"""Exiger qu'AUCUN fichier source du disque ne soit ignore par git.

Ce controle existe a cause d'un incident du 24/08/2026, sous-etape T1 du LOT 5.
Le module `apps/api/app/media/` a ete ecrit, teste, et `make check` est sorti en
0 -- puis `git add -A` ne l'a PAS ajoute. La ligne 60 de `.gitignore` portait
`media/`, un motif ecrit au LOT 0 contre les MEDIAS DEPOSES localement, et qui
vaut a toute profondeur : il attrapait le module source du meme nom.

C'est exactement la classe du §7.34 -- un motif ecrit contre un exemple ne
couvre que cet exemple, et decrit l'incident, pas sa classe. Le motif de LA
etait `* [0-9]`, ecrit contre une copie de REPERTOIRE et aveugle aux FICHIERS.
Celui-ci etait `media/`, ecrit contre un repertoire de DONNEES et aveugle au
fait qu'un MODULE peut porter le meme nom.

CE QUE CE CONTROLE MESURE, et pourquoi c'est la bonne grandeur : tout fichier
present sur le disque, portant une extension de source, et qu'un
`git check-ignore` refuserait de suivre. La liste des fichiers est DERIVEE du
disque a chaque execution -- elle ne peut pas vieillir (§7.27).

CE QU'IL NE MESURE PAS, et il faut le dire : deux marqueurs de la liste
d'exclusion, `dist` et `build`, sont des noms qu'un module source POURRAIT
porter. Un module ainsi nomme resterait invisible a ce controle. Le residuel est
NOMME dans la sortie plutot que tu (§7.20) -- et il est etroit, la convention du
depot etant qu'un module porte un nom de domaine metier, jamais un nom d'etape
de construction.

Sortie 0 si aucun fichier source n'est ignore, 1 sinon.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

GIT = shutil.which("git") or "/usr/bin/git"

# Repertoires dans lesquels on ne DESCEND pas : dependances tierces, caches et
# artefacts de construction. Un nom de cette liste ne peut pas etre un module
# source -- SAUF `dist` et `build`, residuel nomme dans le docstring et dans la
# sortie. Une entree morte est inoffensive : elle ne supprime rien. Une entree
# MANQUANTE produit du bruit, donc se signale d'elle-meme des la premiere
# execution -- la liste est auto-corrigeante dans le sens sur.
MARQUEURS = frozenset(
    {
        ".git",
        "node_modules",
        "site-packages",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        ".vite",
        ".pnpm-store",
        ".yarn",
        "htmlcov",
        "coverage",
        "playwright-report",
        "test-results",
        ".claude",
        ".idea",
        ".vscode",
        "dist",
        "build",
    }
)

# Les deux marqueurs qui pourraient AUSSI nommer un module. Rapportes a chaque
# execution : un residuel tu se transforme en confiance mal placee.
MARQUEURS_AMBIGUS = ("dist", "build")

EXTENSIONS = frozenset(
    {".py", ".ts", ".tsx", ".css", ".sql", ".sh", ".md", ".json", ".yml", ".yaml", ".toml", ".html"}
)

# Les DEUX seuls fichiers source que ce depot ignore volontairement, chacun avec
# son motif ecrit. Ils sont DECLARES et CONFRONTES au reel : ce controle echoue
# aussi si l'un cesse d'etre ignore, parce qu'une exception morte avalerait
# silencieusement la reapparition du cas qu'elle couvrait (§7.22).
EXCEPTIONS = {
    "AGENTS.md": "lien symbolique vers CLAUDE.md, non versionne par construction",
    "docs/prototype/V1.html": "prototype historique, 2,83 Mo dont 2,64 de Base64 (DEC-473, §7.13)",
}

# Chemin du temoin : sous le `logs/` de la racine, qui est ignore. Le temoin
# ECRIT un vrai fichier source a un vrai chemin ignore -- un temoin qui
# n'exerce pas le controle ne prouve rien de ce controle (§7.25).
TEMOIN = "logs/temoin-sources.py"


def racine_du_depot() -> str:
    """Le sommet de l'arbre de travail, pour que le controle soit lancable de partout."""
    r = subprocess.run(  # noqa: S603
        [GIT, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


def sources_du_disque(racine: str) -> tuple[list[str], dict[str, int]]:
    """Tous les fichiers source presents, et ce que chaque marqueur a ecarte.

    S603 : les arguments viennent de ce script seul, et `shell=False` est le motif
    du §7.2 -- ce depot vit sous un chemin qui porte une espace.
    """
    trouves: list[str] = []
    ecartes: dict[str, int] = dict.fromkeys(MARQUEURS, 0)
    for dossier, sous_dossiers, fichiers in os.walk(racine):
        retenus = []
        for sous in sous_dossiers:
            if sous in MARQUEURS:
                ecartes[sous] += 1
            elif sous.endswith(".egg-info"):
                pass
            else:
                retenus.append(sous)
        sous_dossiers[:] = retenus
        for fichier in fichiers:
            if os.path.splitext(fichier)[1] in EXTENSIONS:
                chemin = os.path.relpath(os.path.join(dossier, fichier), racine)
                trouves.append(chemin)
    return sorted(trouves), ecartes


def ignores_par_git(racine: str, chemins: list[str]) -> set[str]:
    """Ceux que git refuserait de suivre. Un seul appel, entrees separees par NUL."""
    if not chemins:
        return set()
    r = subprocess.run(  # noqa: S603
        [GIT, "-C", racine, "check-ignore", "--stdin", "-z"],
        input="\0".join(chemins),
        capture_output=True,
        text=True,
    )
    # check-ignore sort en 1 quand AUCUN chemin n'est ignore : ce n'est pas une
    # erreur. Seul un code superieur a 1 en est une (§7.3).
    if r.returncode > 1:
        print(f"  ECHEC    git check-ignore a echoue : {r.stderr.strip()}")
        sys.exit(1)
    return {c for c in r.stdout.split("\0") if c}


def analyser(racine: str) -> int:
    """Le controle lui-meme. Rend le nombre de defauts."""
    sources, ecartes = sources_du_disque(racine)
    ignores = ignores_par_git(racine, sources)

    print(f"  info     {len(sources)} fichier(s) source examine(s) sur le disque")
    actifs = {m: n for m, n in ecartes.items() if n}
    if actifs:
        detail = ", ".join(f"{m} x{n}" for m, n in sorted(actifs.items()))
        print(f"  info     marqueurs ayant ecarte un repertoire : {detail}")
    ambigus = [m for m in MARQUEURS_AMBIGUS if ecartes.get(m)]
    if ambigus:
        print(
            f"  RESIDUEL {', '.join(ambigus)} : nom d'artefact QUI POURRAIT AUSSI etre un module. "
            "Un module ainsi nomme echapperait a ce controle."
        )

    defauts = 0

    fautifs = sorted(ignores - set(EXCEPTIONS))
    if fautifs:
        defauts += len(fautifs)
        print(f"  ECHEC    {len(fautifs)} fichier(s) source IGNORE(S) par git :")
        for chemin in fautifs:
            motif = subprocess.run(  # noqa: S603
                [GIT, "-C", racine, "check-ignore", "-v", chemin],
                capture_output=True,
                text=True,
            ).stdout.strip()
            print(f"      {chemin}")
            print(f"        ignore par -> {motif or 'motif indetermine'}")
        print("      -> un motif de .gitignore attrape du code source. Ancre-le ou restreins-le.")
    else:
        print(f"  OK       aucun fichier source ignore, hors les {len(EXCEPTIONS)} exceptions")

    for chemin, motif in sorted(EXCEPTIONS.items()):
        existe = os.path.exists(os.path.join(racine, chemin))
        if not existe:
            print(f"  info     exception absente du disque : {chemin}")
        elif chemin in ignores:
            print(f"  OK       exception toujours ignoree : {chemin} — {motif}")
        else:
            defauts += 1
            print(f"  ECHEC    exception MORTE : {chemin} n'est plus ignore — {motif}")
            print("      -> une exception morte avalerait la reapparition du cas (§7.22).")

    return defauts


def temoin(racine: str) -> int:
    """Eprouver le controle DANS LES DEUX SENS.

    Sans le fichier temoin il doit passer ; avec un vrai fichier source a un vrai
    chemin ignore il doit ECHOUER en le nommant. Un temoin qui ne verifie qu'un
    code de sortie non nul ne dit pas que le controle a vu la BONNE chose (§7.25).
    """
    print("==> Temoin negatif du controle des sources suivies")
    print()
    print("  --- sens 1 : sans temoin, le controle doit PASSER")
    if analyser(racine) != 0:
        print()
        print("  ECHEC    l'arbre porte deja un defaut : le temoin ne prouverait rien.")
        return 1

    chemin = os.path.join(racine, TEMOIN)
    dossier = os.path.dirname(chemin)
    dossier_cree = not os.path.isdir(dossier)
    print()
    print(f"  --- sens 2 : avec {TEMOIN}, le controle doit ECHOUER en le nommant")
    try:
        os.makedirs(dossier, exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write("# temoin de verifier-sources-suivies.py\n")
        if TEMOIN not in ignores_par_git(racine, [TEMOIN]):
            print(f"  ECHEC    {TEMOIN} n'est PAS ignore : le temoin n'exerce pas le controle.")
            return 1
        sources, _ = sources_du_disque(racine)
        if TEMOIN not in sources:
            print(f"  ECHEC    {TEMOIN} n'est pas RAMASSE par le balayage du disque.")
            return 1
        defauts = analyser(racine)
    finally:
        if os.path.exists(chemin):
            os.remove(chemin)
        if dossier_cree and os.path.isdir(dossier) and not os.listdir(dossier):
            os.rmdir(dossier)

    if defauts != 1:
        print()
        print(f"  ECHEC    le controle a rendu {defauts} defaut(s), un seul etait attendu.")
        return 1

    print()
    print("  OK       le controle a vu le temoin, et lui seul. Il sait echouer.")
    return 0


def main() -> int:
    racine = racine_du_depot()
    if "--temoin" in sys.argv[1:]:
        return temoin(racine)
    print("==> Aucun fichier source ne doit etre ignore par git")
    print()
    defauts = analyser(racine)
    print()
    if defauts:
        print(f"  {defauts} defaut(s). Voir CLAUDE.md §7.34.")
        return 1
    print("  Controle des sources suivies : OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
