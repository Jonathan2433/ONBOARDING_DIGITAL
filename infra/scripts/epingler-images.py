#!/usr/bin/env python3
"""Epingler l'environnement de recette sur la derniere publication reussie.

LOT 1, sous-etape T8, story MVP-L01-US002.

CE QUE CE SCRIPT FAIT, ET POURQUOI IL EXISTE

    `docker-compose.recette.yml` epingle les trois images publiees par empreinte
    de liste de manifestes. Une empreinte designe UN artefact, ce qui est
    exactement ce que « une meme version immuable fonctionne » demande — mais
    elle vieillit a chaque fusion sur `develop`.

    Ce script DERIVE les empreintes de la source plutot que de les transcrire, ce
    qu'exige la regle « generer plutot que transcrire » de la passation §6.4. La
    source est la tache `publier` du workflow, qui tient elle-meme ses valeurs du
    `--metadata-file` de buildx : personne n'invente rien le long de la chaine.

    L'INTERDIT DE T7-9 EST LA RAISON D'ETRE DE CE FICHIER. `T7` a ecrit dans un
    workflow une empreinte SHA-256 plausible mais jamais mesuree, sur un controle
    de securite. Aucune des propositions de la regle du lot ne l'attrape : le
    controle aurait « fonctionne ». La seule parade est de ne jamais avoir a
    ecrire une empreinte a la main — donc de la lire chez son producteur.

CE QU'IL N'EST PAS
    Ce n'est pas un moyen de changer DURABLEMENT l'artefact recette : il ecrit
    dans le fichier d'environnement local, qui n'est pas versionne. Figer un
    nouveau pointeur pour tout le monde reste un commit sur la surcouche, et
    c'est voulu — changer ce que l'on recette est un acte delibere, pas un effet
    de bord d'une commande.

PREREQUIS
    `gh` authentifie, avec la portee `repo` — celle du jeton de cette machine. La
    lecture des journaux d'execution n'exige PAS `read:packages` : c'est
    precisement ce qui permet de relever les empreintes sans que Jonathan ait a
    elargir son jeton.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
WORKFLOW = "images.yml"
BRANCHE = "develop"
SERVICES = ("api", "worker", "web")
REGISTRE = "ghcr.io/jonathan2433/onboarding-digital"

# Les lignes utiles du journal, reconnues PAR LEUR CONTENU et non par le libelle
# de l'etape qui les a produites.
#
# POURQUOI PAS PAR L'ETAPE — un defaut trouve juste apres la fusion de T8, sur la
# premiere execution reelle de ce script en conditions nominales.
#
#   `gh run view --log` prefixe chaque ligne de « <tache>\t<etape>\t<horodatage> »,
#   et la premiere version filtrait sur le nom de l'etape. Mesure du 29/07/2026 :
#   sur l'execution 30465685379, **TOUTES** les etapes du journal portent le
#   libelle littéral `UNKNOWN STEP` — GitHub n'avait pas encore associe les noms
#   d'etape aux lignes. Sur l'execution precedente, 30458611741, le nom apparait
#   20 fois. Le filtre trouvait donc zero ligne, et le script echouait sur un
#   journal qui contenait pourtant les trois empreintes, le compte et l'identite.
#
#   C'est la classe de T6-4 et T7-4 : un controle qui echoue pour une raison
#   ETRANGERE a ce qu'il mesure. Le libelle d'etape est une commodite d'affichage,
#   pas une donnee : ces trois motifs, eux, ne peuvent venir que de l'etape visee.
#
# DISCRIMINATION VERIFIEE. Le journal porte aussi des lignes de buildx de la forme
# `pushing manifest for …/api:sha-1060ad6@sha256:…` : elles ne correspondent PAS,
# le motif exigeant `api : sha256:` et non `api:sha-…@`. Il porte de meme l'echo du
# code source, `echo "  empreintes attendues : 3   relevees : ${relevees}"` : il ne
# correspond pas non plus, `${relevees}` n'etant pas une suite de chiffres.
# Et le filet de securite reste le meme : mon compte est confronte a celui que le
# PRODUCTEUR declare.
MOTIF_EMPREINTE = re.compile(
    r"\b(?P<service>api|worker|web)\s+:\s+(?P<empreinte>sha256:[0-9a-f]{64})"
)
MOTIF_RELEVEES = re.compile(
    r"empreintes attendues\s*:\s*(?P<attendues>\d+)\s+relevees\s*:\s*(?P<relevees>\d+)"
)
MOTIF_IDENTITE = re.compile(
    r"Identite attendue\s*:\s*version='(?P<version>[^']*)'\s+revision='(?P<revision>[^']*)'"
)


def lancer(*commande: str) -> tuple[int, str]:
    """Executer sans shell. `subprocess.run([...])` ne redecoupe rien.

    Le depot reside sous « ~/Library/Mobile Documents/ », dont le chemin contient
    une espace. Ce piege a produit QUATRE defauts sur ce projet, dont deux commis
    par un agent qui venait de le citer. Il n'existe pas ici : les arguments sont
    passes tels quels, et `returncode` ne peut pas etre celui d'un autre maillon.
    """
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # precisement ce qui rend ce script sur — voir l'en-tete.
    p = subprocess.run(  # noqa: S603
        list(commande), capture_output=True, text=True, cwd=RACINE
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def derniere_execution_reussie() -> str:
    code, sortie = lancer(
        "gh",
        "run",
        "list",
        "--workflow",
        WORKFLOW,
        "--branch",
        BRANCHE,
        "--status",
        "success",
        "--limit",
        "1",
        "--json",
        "databaseId,headSha,createdAt",
        "--jq",
        '.[0] | "\\(.databaseId) \\(.headSha) \\(.createdAt)"',
    )
    if code != 0 or not sortie:
        raise SystemExit(
            f"  ECHEC     aucune execution reussie de {WORKFLOW} sur {BRANCHE} (code {code})\n"
            f"            {sortie}"
        )
    return sortie


def relever(journal: str) -> tuple[dict[str, str], str, str]:
    """Extraire les trois empreintes et l'identite, en COMPTANT ce qui est trouve."""
    empreintes: dict[str, str] = {}
    attendues_declarees: int | None = None
    relevees_declarees: int | None = None
    version = revision = ""

    lignes = journal.split("\n")
    for ligne in lignes:
        # Le contenu utile suit le dernier horodatage ISO de la ligne.
        contenu = ligne.split("Z ", 1)[-1] if "Z " in ligne else ligne
        if (m := MOTIF_EMPREINTE.search(contenu)) and m.group("service") not in empreintes:
            empreintes[m.group("service")] = m.group("empreinte")
        if m := MOTIF_RELEVEES.search(contenu):
            attendues_declarees = int(m.group("attendues"))
            relevees_declarees = int(m.group("relevees"))
        if m := MOTIF_IDENTITE.search(contenu):
            version, revision = m.group("version"), m.group("revision")

    # DEUX COMPTES CONFRONTES, ET C'EST LE POINT. Le premier est ce que J'AI
    # trouve ; le second est ce que le PRODUCTEUR declare avoir publie. Les
    # comparer attrape le cas ou mon expression reguliere manquerait une ligne :
    # sans cela, « 2 empreintes relevees » ressemblerait a un succes partiel
    # plutot qu'a un detecteur incomplet.
    if attendues_declarees is None or relevees_declarees is None:
        # UN ECHEC QUI DIT POURQUOI. La premiere version se contentait de « pas de
        # compte annonce », ce qui laissait chercher du cote de la publication
        # alors que la cause etait dans la lecture du journal. C'est la lecon
        # T7-13 : la premiere correction a ecrire est celle qui te le dira.
        etapes = sorted({p[1] for x in lignes if len(p := x.split("\t")) >= 3})
        raise SystemExit(
            "  ECHEC     le journal ne porte pas la ligne de compte de la publication.\n"
            f"            journal lu : {len(lignes)} lignes, {len(empreintes)} empreinte(s) "
            f"reconnue(s) : {sorted(empreintes)}\n"
            f"            libelles d'etape vus : {etapes[:6]}\n"
            "            Si le journal est vide ou tronque, l'archivage GitHub peut etre en"
            " retard :\n"
            "            reessaie, ou lis l'execution a la main avec `gh run view <id> --log`."
        )
    if relevees_declarees != attendues_declarees:
        raise SystemExit(
            f"  ECHEC     la publication elle-meme n'a releve que {relevees_declarees}"
            f" empreintes sur {attendues_declarees}"
        )
    if len(empreintes) != attendues_declarees:
        raise SystemExit(
            f"  ECHEC     j'ai extrait {len(empreintes)} empreintes ({sorted(empreintes)}) "
            f"la ou la publication en declare {attendues_declarees}.\n"
            "            C'est mon extraction qui est en cause, pas la publication."
        )
    if sorted(empreintes) != sorted(SERVICES):
        raise SystemExit(f"  ECHEC     services inattendus : {sorted(empreintes)}")
    if not version or not revision:
        raise SystemExit("  ECHEC     identite du build introuvable dans le journal")
    return empreintes, version, revision


def ecrire(fichier: Path, valeurs: dict[str, str]) -> None:
    """Mettre a jour ou ajouter les affectations, sans toucher au reste.

    Aucune substitution par expression reguliere : l'affectation est reconstruite,
    donc aucun caractere de la valeur n'a de sens special. Meme motif que
    `composer-env.py`.
    """
    lignes = fichier.read_text(encoding="utf-8").split("\n")
    restants = dict(valeurs)
    for i, ligne in enumerate(lignes):
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=", ligne)
        if m and m.group(1) in restants:
            lignes[i] = f"{m.group(1)}={restants.pop(m.group(1))}"
    if restants:
        lignes += ["", "# Epingle par `make images-pin`, derive de la publication ci-dessus."]
        lignes += [f"{k}={v}" for k, v in restants.items()]
    fichier.write_text("\n".join(lignes), encoding="utf-8")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--fichier-env", required=True)
    args = a.parse_args()

    cible = RACINE / args.fichier_env
    if not cible.is_file():
        raise SystemExit(
            f"  ECHEC     {args.fichier_env} absent : lancer `make env ENVIRONNEMENT=recette`"
        )

    print()
    print("  Epinglage de la recette sur la derniere publication reussie")
    print()
    identifiant, commit, date = derniere_execution_reussie().split()
    print(f"    info     execution {identifiant}, commit {commit[:7]}, {date}")

    code, journal = lancer("gh", "run", "view", identifiant, "--log")
    if code != 0:
        raise SystemExit(
            f"  ECHEC     lecture des journaux impossible (code {code})\n{journal[:400]}"
        )

    empreintes, version, revision = relever(journal)
    print(f"    ok       {len(empreintes)} empreintes relevees sur {len(SERVICES)} attendues")
    for service in SERVICES:
        print(f"               {service:7s} {empreintes[service]}")
    print(f"    ok       identite du build : version={version!r} revision={revision!r}")

    # La revision publiee doit correspondre au commit de l'execution. Sans ce
    # controle, une identite lue dans le journal d'une AUTRE etape passerait.
    if not commit.startswith(revision):
        raise SystemExit(
            f"  ECHEC     la revision publiee ({revision}) n'est pas un prefixe du commit "
            f"de l'execution ({commit[:12]}...)"
        )
    print("    ok       la revision est bien un prefixe du commit de l'execution")

    valeurs = {f"IMAGE_{s.upper()}": f"{REGISTRE}/{s}@{empreintes[s]}" for s in SERVICES}
    valeurs["APP_VERSION"] = version
    valeurs["APP_REVISION"] = revision
    ecrire(cible, valeurs)
    print()
    print(f"  --> {len(valeurs)} valeurs ecrites dans {args.fichier_env}")
    print("      Ce fichier n'est PAS versionne : l'epinglage durable reste un commit")
    print("      sur infra/compose/docker-compose.recette.yml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
