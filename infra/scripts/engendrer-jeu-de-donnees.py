#!/usr/bin/env python3
"""Ensemencer la base avec le jeu fictif — story `MVP-L02-US007`.

LOT 2, sous-etape `T12`.

CE SCRIPT ECRIT POUR DE BON, ET IL S'EN PROTEGE

  Les tests engendrent le meme jeu dans une transaction **annulee**. Ce script,
  lui, **valide** : il sert a peupler une base de developpement pour travailler
  sur des ecrans au LOT 4, ou pour eprouver une requete au volume.

  **Il refuse de s'executer sur une base qui porte deja des personnes**, sauf
  `--forcer`. Un generateur idempotent serait un mensonge -- les codes d'entite et
  les adresses sont uniques, une seconde execution echouerait a mi-chemin en
  laissant la base a moitie peuplee. Refuser d'emblee vaut mieux qu'echouer au
  milieu.

  **Aucune donnee reelle** : les adresses portent `exemple.test`, domaine reserve
  par la RFC 2606, et les noms viennent d'un lexique de huit prenoms et huit noms.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))


def charger_env(chemin: str) -> None:
    """Poser les variables du fichier d'environnement AVANT d'importer les reglages.

    `Parametres` lit l'environnement a la construction, et les 11 garde-fous de
    demarrage du cahier §20.3 s'appliquent : une variable absente fait echouer
    l'import avec un message qui la nomme. Charger le fichier d'abord est donc
    obligatoire, et c'est la convention des autres scripts d'`infra/scripts`.

    `POSTGRES_HOST` est force a `127.0.0.1` : le script tourne sur l'HOTE, ou le
    nom de service Docker `db` ne se resout pas.
    """
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(), valeur.strip())
    os.environ["POSTGRES_HOST"] = "127.0.0.1"


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", default=str(RACINE / ".env"))
    analyseur.add_argument("--entites", type=int, default=25)
    analyseur.add_argument("--profils", type=int, default=5000)
    analyseur.add_argument("--graine", type=int, default=20260820)
    analyseur.add_argument(
        "--forcer",
        action="store_true",
        help="Ecrire meme si la base porte deja des personnes (une collision est probable)",
    )
    arguments = analyseur.parse_args()
    charger_env(arguments.env_file)

    #  Import APRES le chargement : `Parametres` lit l'environnement a la
    #  construction du module de reglages.
    from sqlalchemy import text

    from app.configuration.settings import Parametres
    from app.shared.database import moteur
    from app.shared.fabriques import engendrer

    parametres = Parametres()
    with moteur(parametres).connect() as connexion:
        #  LE SEUL `begin()` DU SCRIPT, ouvert AVANT la premiere lecture.
        #  SQLAlchemy 2 ouvre une transaction implicite des la premiere requete
        #  (« autobegin ») : lire d'abord puis appeler `begin()` leve
        #  `InvalidRequestError`. Le comptage se fait donc DANS la transaction, et
        #  elle est annulee si le refus s'applique.
        transaction = connexion.begin()
        deja = connexion.execute(text("SELECT count(*) FROM person")).scalar_one()
        if deja and not arguments.forcer:
            transaction.rollback()
            print(f"  REFUS : la base porte deja {deja} personne(s).")
            print("  Un second ensemencement collisionnerait sur les codes d'entite et les")
            print("  adresses, et laisserait la base a moitie peuplee. Employer `--forcer`")
            print("  en connaissance de cause, ou repartir d'une base migree vide.")
            return 1

        depart = time.monotonic()
        try:
            mesure = engendrer(
                connexion,
                entites=arguments.entites,
                profils=arguments.profils,
                graine=arguments.graine,
            )
        except Exception:
            transaction.rollback()
            print("  ECHEC : rien n'a ete ecrit, la transaction est annulee.")
            raise
        transaction.commit()
        duree = time.monotonic() - depart

    print()
    print("  ATTENTION : de nombreux tests d'integration comparent des comptes")
    print("  ABSOLUS — « assert count == 1 ». Semer la base de developpement et")
    print("  lancer la suite s'EXCLUENT. Pour revenir en arriere, employer")
    print("  `make migrate` sur une base recreee, ou tronquer les tables metier.")
    print(f"  Jeu fictif ecrit en {duree:.1f} s — graine {arguments.graine}")
    print(f"    {mesure.entites:>6} entites (dont 1 archivee au titre des cas limites)")
    print(f"    {mesure.personnes:>6} personnes    {mesure.appartenances:>6} appartenances")
    print(
        print(
            f"    {mesure.cercles:>6} cercles      "
            f"{mesure.appartenances_cercle:>6} appartenances de cercle"
        )
    )
    print(
        f"    {mesure.metiers:>6} metiers      {mesure.affectations_metier:>6} affectations metier"
    )
    print(f"    {mesure.clients:>6} clients      {mesure.activations:>6} activations locales")
    print(f"    {mesure.situations:>6} situations   {mesure.responsabilites:>6} responsabilites")
    print(f"    {mesure.bureaux:>6} bureaux      {mesure.affectations_dsm:>6} affectations DSM")
    print(f"    {mesure.total_lignes():>6} LIGNES AU TOTAL")
    print()
    print(f"  {len(mesure.cas_limites)} cas limites, chacun NOMME :")
    for limite in mesure.cas_limites:
        print(f"    - {limite}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
