#!/usr/bin/env python3
"""Provisionner la Beta Bordeaux depuis le classeur et, facultativement, les photos."""

from __future__ import annotations

import argparse
import contextlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))


def _charger_env(chemin: pathlib.Path) -> None:
    if chemin.is_file():
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.lstrip().startswith("#"):
                cle, _, valeur = ligne.partition("=")
                os.environ.setdefault(cle.strip(), valeur.strip())

    # Cette commande tourne sur l'hote, tandis que les valeurs du fichier
    # `.env` visent le reseau Docker interne (`db`, `minio`).
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    os.environ["MINIO_ENDPOINT"] = f"127.0.0.1:{os.environ.get('MINIO_HOST_PORT', '9000')}"


@contextlib.contextmanager
def _photos_compatibles(dossier: pathlib.Path | None) -> Iterator[pathlib.Path | None]:
    """Convertir les RAW Sony fournis pour la Beta sans modifier leur dossier."""
    if dossier is None or not any(dossier.glob("*.[Aa][Rr][Ww]")):
        yield dossier
        return
    convertisseur = shutil.which("sips")
    if convertisseur is None:
        print("AVERTISSEMENT: conversion .ARW indisponible ; ces photos seront ignorees")
        yield dossier
        return

    with tempfile.TemporaryDirectory(prefix="exalt-bordeaux-photos-") as temporaire:
        destination = pathlib.Path(temporaire)
        for source in dossier.iterdir():
            if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                (destination / source.name).symlink_to(source)
            elif source.suffix.lower() == ".arw":
                cible = destination / f"{source.stem}.jpg"
                subprocess.run(  # noqa: S603 -- executable resolu par shutil.which, arguments fixes
                    [
                        convertisseur,
                        "-Z",
                        "1200",
                        "-s",
                        "format",
                        "jpeg",
                        "-s",
                        "formatOptions",
                        "82",
                        str(source),
                        "--out",
                        str(cible),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
        yield destination


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--classeur", type=pathlib.Path, required=True)
    analyseur.add_argument("--photos", type=pathlib.Path)
    analyseur.add_argument("--env", type=pathlib.Path, default=RACINE / ".env")
    arguments = analyseur.parse_args()
    _charger_env(arguments.env)

    from app.bordeaux.donnees import lire_la_population_bordeaux
    from app.bordeaux.provisionnement import provisionner_bordeaux
    from app.configuration.settings import Parametres
    from app.shared.database import moteur

    parametres = Parametres()
    with _photos_compatibles(arguments.photos) as photos:
        rapport = provisionner_bordeaux(
            moteur(parametres),
            lire_la_population_bordeaux(arguments.classeur),
            parametres=parametres,
            dossier_photos=photos,
        )
    print(
        f"Bordeaux provisionne : {rapport.employes} personnes, {rapport.cercles} cercles, "
        f"{rapport.bureaux} bureaux, {rapport.photos_installees} photos, "
        f"{rapport.taches_onboarding} taches d'onboarding, "
        f"{rapport.parcours_affectes} parcours affecte(s)."
    )
    for avertissement in rapport.avertissements:
        print(f"AVERTISSEMENT: {avertissement}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
