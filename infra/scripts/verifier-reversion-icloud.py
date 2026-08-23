#!/usr/bin/env python3
"""Detecter une REVERSION silencieuse de fichiers par iCloud.

Ce controle existe a cause d'un incident du 22/08/2026, sous-etape T11 du LOT 3 :
quatre fichiers ont ete remis a une version ANTERIEURE sans aucune action de
session, avec le meme mtime a la seconde sur les quatre — signature d'une
reecriture en lot. `make icloud-verify` etait au vert : il ne cherchait que les
copies de conflit `* [0-9]`, exact pour ce mode de defaillance et AVEUGLE a
celui-ci (CLAUDE.md §7.31).

LA PREMIERE VERSION DE CE GARDE-FOU ETAIT UN FAUX POSITIF, et c'est pour cela
que ce fichier existe. Elle exigeait « arbre de HEAD identique a l'amont ET des
fichiers modifies » — or c'est l'etat NORMAL de toute sous-etape en cours de
travail : on n'a rien commite encore, et on a modifie des fichiers. Elle se
serait declenchee a chaque debut de sous-etape. Un garde-fou a faux positifs
apprend a passer outre, si bien que le jour ou il a raison il n'est plus lu
(CLAUDE.md §7.25).

CE QU'IL MESURE DESORMAIS, et c'est la signature REELLE de l'incident : le
contenu de travail d'un fichier suivi est-il EXACTEMENT egal a une version
anterieure de ce meme fichier dans l'historique ? Aucune edition humaine ne
produit a l'octet une version passee. Une reecriture iCloud, si.

Il RAPPORTE en plus les grappes de mtime — trois fichiers ou plus modifies dans
la meme seconde — parce que c'est ce qui distingue une reecriture EN LOT d'une
edition, et c'est corroborant, non decisif : un formateur produit la meme
grappe. La grappe est donc rapportee, jamais exigee.

Sortie 0 si aucune reversion, 1 sinon.
"""

from __future__ import annotations

import collections
import os
import shutil
import subprocess
import sys

COMMITS_REMONTES = 200
GIT = shutil.which("git") or "/usr/bin/git"


def git(*args: str) -> tuple[int, str]:
    """Un appel a git, sans shell.

    S603 : les arguments viennent de ce script seul, jamais d'un tiers, et
    `shell=False` est le motif du §7.2 -- aucun redecoupage n'a lieu, meme si un
    chemin porte une espace, ce qui est le cas de TOUT ce depot (§7.2).
    S607 est resolu et non tu : `shutil.which` donne le chemin complet, comme
    dans `test_integration.py`.
    """
    r = subprocess.run(  # noqa: S603
        [GIT, *args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return r.returncode, r.stdout.strip()


def fichiers_modifies() -> list[str]:
    """Les fichiers SUIVIS dont le contenu de travail differe de l'index ou de HEAD.

    On ne garde que les modifications de CONTENU : une suppression n'a pas de
    contenu a comparer, un ajout n'a pas de passe.
    """
    code, sortie = git("status", "--porcelain=v1", "--untracked-files=no", "-z")
    if code != 0:
        return []
    entrees = [e for e in sortie.split("\0") if e]
    chemins: list[str] = []
    for e in entrees:
        if len(e) < 4:
            continue
        etat, chemin = e[:2], e[3:]
        if "M" in etat and "D" not in etat and "A" not in etat and "R" not in etat:
            chemins.append(chemin)
    return chemins


def versions_anterieures(chemin: str) -> list[tuple[str, str]]:
    """(commit, empreinte du blob) pour ce chemin, du plus recent au plus ancien."""
    code, sortie = git("rev-list", f"-{COMMITS_REMONTES}", "HEAD", "--", chemin)
    if code != 0 or not sortie:
        return []
    versions: list[tuple[str, str]] = []
    for commit in sortie.splitlines():
        c, blob = git("rev-parse", f"{commit}:{chemin}")
        if c == 0 and blob:
            versions.append((commit, blob))
    return versions


def main() -> int:
    modifies = fichiers_modifies()
    if not modifies:
        print("  ok       aucun fichier suivi modifie : rien a comparer")
        return 0

    reversions: list[tuple[str, str, int]] = []
    for chemin in modifies:
        code, travail = git("hash-object", "--", chemin)
        if code != 0 or not travail:
            continue
        versions = versions_anterieures(chemin)
        if not versions:
            continue
        # versions[0] est la version de HEAD. Une egalite avec elle voudrait dire
        # « non modifie », ce que `git status` a deja exclu. On cherche donc une
        # egalite avec une version PLUS ANCIENNE.
        for rang, (commit, blob) in enumerate(versions[1:], start=1):
            if blob == travail:
                reversions.append((chemin, commit[:7], rang))
                break

    print(f"  {len(modifies)} fichier(s) suivi(s) modifie(s) examine(s)")

    if reversions:
        print(f"  REVERSION DETECTEE — {len(reversions)} fichier(s) :")
        for chemin, commit, rang in reversions:
            print(f"      {chemin}")
            print(
                f"        contenu identique a la version de {commit}, {rang} version(s) en arriere"
            )
        print("      -> aucune edition humaine ne reproduit une version passee a l'octet.")
        print("         Signature d'une reecriture iCloud. Voir ROAD-RSK-026 et §7.31.")
        print("         Si la reversion est VOULUE, commite-la : le controle porte sur")
        print("         l'arbre de travail, pas sur l'historique.")
    else:
        print("  ok       aucun contenu de travail egal a une version anterieure")

    # Corroborant, jamais decisif : une grappe de mtime identiques a la seconde.
    grappes: dict[int, list[str]] = collections.defaultdict(list)
    for chemin in modifies:
        try:
            grappes[int(os.path.getmtime(chemin))].append(chemin)
        except OSError:
            continue
    en_lot = {s: f for s, f in grappes.items() if len(f) >= 3}
    if en_lot:
        print(f"  info     {len(en_lot)} grappe(s) de mtime identiques a la seconde :")
        for seconde, fichiers in sorted(en_lot.items()):
            print(f"      {len(fichiers)} fichiers a l'horodatage {seconde} — reecriture EN LOT")
            for f in fichiers[:6]:
                print(f"        {f}")
        print("      -> corroborant, non decisif : un formateur produit la meme grappe.")
    else:
        print("  info     aucune grappe de mtime : les modifications sont espacees")

    return 1 if reversions else 0


if __name__ == "__main__":
    sys.exit(main())
