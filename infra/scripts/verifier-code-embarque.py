#!/usr/bin/env python3
"""Verifier que le code applicatif VU PAR LE CONTENEUR est celui du depot.

LOT 2, sous-etape `T1`, story `MVP-L02-US008`.

POURQUOI CE CONTROLE EXISTE. `apps/api` n'est PAS monte en bind : le code est
cuit dans l'image au moment de la construction. Une migration ecrite sur l'hote
et non reconstruite est donc INVISIBLE du conteneur, et `alembic upgrade head`
repond « deja a jour » -- succes, code 0, aucune migration appliquee.

Le defaut s'est produit reellement le 18/08/2026 : la migration `0002` etait
ecrite, `make migrate` a rendu `0001 (head)` en sortant en 0. Rien ne signalait
l'ecart. C'est le meme mecanisme que le defaut `T5-2` du LOT 1, ou Caddy servait
une configuration perimee en etant `healthy`, et le remede est le meme : ne pas
croire le service, COMPARER ce qu'il voit a ce que porte l'hote.

CE QU'IL COMPARE. La liste des fichiers de migration et leurs empreintes
SHA-256, cote hote et cote conteneur. Une empreinte et non une date : un fichier
recopie par iCloud change de date sans changer de contenu, et l'inverse est vrai
aussi apres une reconstruction.

CE QU'IL NE COMPARE PAS, ET IL LE DIT. Il ne couvre que `alembic/versions` et
`app/`. Un ecart dans les dependances installees ne serait pas vu -- il faudrait
comparer les versions de paquets, ce qui releve d'un autre controle.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
# `apps/api/alembic` en entier, et non son seul sous-repertoire `versions` :
# `env.py` s'execute lui aussi dans le conteneur, et une modification de son
# `target_metadata` non reconstruite ferait mentir `alembic check`.
REPERTOIRES = ("apps/api/alembic", "apps/api/app")
DANS_LE_CONTENEUR = "/app"


def empreintes_hote() -> dict[str, str]:
    """Empreintes des fichiers `.py` du depot, chemins relatifs a la racine."""
    trouvees: dict[str, str] = {}
    for repertoire in REPERTOIRES:
        base = RACINE / repertoire
        if not base.is_dir():
            continue
        for chemin in sorted(base.rglob("*.py")):
            if "__pycache__" in chemin.parts:
                continue
            relatif = chemin.relative_to(RACINE).as_posix()
            trouvees[relatif] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    return trouvees


def empreintes_conteneur(compose: list[str], service: str) -> dict[str, str] | str:
    """Empreintes vues DANS le conteneur, ou un message d'echec.

    Le calcul est fait par Python dans le conteneur plutot que par `sha256sum` :
    l'image est fondee sur `python:slim`, et rien ne garantit la presence de
    `sha256sum` ni l'identite de son format de sortie.
    """
    programme = (
        "import hashlib,pathlib\n"
        f"racine=pathlib.Path({DANS_LE_CONTENEUR!r})\n"
        f"for rep in {REPERTOIRES!r}:\n"
        "    base=racine/rep\n"
        "    if not base.is_dir(): continue\n"
        "    for c in sorted(base.rglob('*.py')):\n"
        "        if '__pycache__' in c.parts: continue\n"
        "        e=hashlib.sha256(c.read_bytes()).hexdigest()\n"
        "        print(c.relative_to(racine).as_posix(), e)\n"
    )
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # le motif du §7.2 -- aucun redecoupage des arguments n'a lieu.
    execution = subprocess.run(  # noqa: S603
        [*compose, "exec", "-T", service, "python", "-c", programme],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if execution.returncode != 0:
        return f"code={execution.returncode} : {execution.stderr.strip()[:200]}"
    resultat: dict[str, str] = {}
    for ligne in execution.stdout.splitlines():
        morceaux = ligne.split()
        if len(morceaux) == 2:
            resultat[morceaux[0]] = morceaux[1]
    return resultat


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--service", default="api")
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]

    print()
    print("  Le code vu par le conteneur est-il celui du depot ?")

    hote = empreintes_hote()
    if not hote:
        print("  ECHEC     aucun fichier trouve sur l'hote : le controle ne peut rien prouver")
        return 1

    conteneur = empreintes_conteneur(compose, arguments.service)
    if isinstance(conteneur, str):
        print(f"  INDETERMINE  le conteneur {arguments.service} n'a pas repondu -- {conteneur}")
        print("               Ce n'est pas « tout va bien » : c'est « je n'ai pas pu mesurer ».")
        print("               Lancer `make up`, puis rejouer.")
        return 1

    print(f"    info     hote      : {len(hote)} fichier(s) .py")
    print(f"    info     conteneur : {len(conteneur)} fichier(s) .py")

    absents = sorted(set(hote) - set(conteneur))
    surnumeraires = sorted(set(conteneur) - set(hote))
    differents = sorted(c for c in set(hote) & set(conteneur) if hote[c] != conteneur[c])

    for chemin in absents:
        print(f"    ECHEC    ABSENT du conteneur      : {chemin}")
    for chemin in surnumeraires:
        print(f"    ECHEC    present en TROP           : {chemin}")
    for chemin in differents:
        print(f"    ECHEC    contenu DIFFERENT         : {chemin}")

    ecarts = len(absents) + len(surnumeraires) + len(differents)
    if ecarts:
        print()
        print(f"  ECHEC : {ecarts} ecart(s) entre le depot et le conteneur.")
        print("          `apps/api` n'est pas monte en bind : le code est cuit dans l'image.")
        print("          Remede : make code-refresh   (reconstruit et recree api et worker)")
        return 1

    print(f"    ok       les {len(hote)} fichiers sont identiques de part et d'autre")
    print()
    print(f"  --> le conteneur {arguments.service} execute bien le code du depot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
