#!/usr/bin/env python3
"""Temoin de `verifier-documentation.py` : il DOIT savoir echouer.

**MOTIF.** `ECART-054` a montre que le controle de documentation etait exact pour
les six registres et **aveugle a la passation** -- `CLAUDE.md` annoncait 148
decisions quand le registre en declarait 149, et surtout `DEC-541` libre alors
que `DEC-565` etait en usage, soit une collision d'identifiant garantie. Le
controle a ete etendu ; ce temoin prouve que l'extension **mord**.

**IL NE TOUCHE JAMAIS LE DEPOT.** Les fichiers sont copies dans un repertoire
temporaire, et c'est la copie qu'on abime.

**SES MUTATIONS SONT DERIVEES, JAMAIS RECOPIEES, ET CE POINT A ETE PAYE.** La
premiere version de ce temoin portait les chaines exactes de `CLAUDE.md` -- « |
`DEC-nnn` | ... | **`DEC-566`** | » -- et elles ont vieilli **dans l'heure**, au
moment ou `ECART-054` et `DEC-566` ont ete ajoutes aux registres : quatre
epreuves sur six sont tombees en « 0 occurrence ». C'etait `ECART-021` **a
l'interieur du temoin ecrit pour `ECART-054`**, et c'est la demonstration la plus
courte possible du §7.27 : une liste recopiee vieillit au premier ajout, y
compris quand elle sert a prouver qu'on attrape le vieillissement.

Chaque mutation LIT donc le fichier et calcule sa propre substitution. Le temoin
ne peut plus vieillir : il n'affirme rien sur le contenu, il le derive.

**SEPT EPREUVES, ET LA DERNIERE EST UNE ABSENCE D'ECHEC.** Cinq defauts doivent
faire echouer le controle ; la sixieme verifie qu'un changement anodin ne le fait
PAS echouer. C'est la lecon du §7.40 -- « le temoin qui compte n'est pas un
echec, c'est une ABSENCE d'echec » : sans elle, un controle qui echouerait sur
tout passerait ce temoin haut la main, comme les huit refus du defaut `T2-3`.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

RACINE = Path(__file__).resolve().parents[2]
CONTROLE = RACINE / "infra/scripts/verifier-documentation.py"

#  Une mutation : elle recoit le texte courant et rend (ancien, nouveau), ou
#  leve si elle ne trouve pas sa cible. Elle ne porte AUCUNE chaine du corpus.
Mutation = Callable[[str], tuple[str, str]]


def charger() -> ModuleType:
    """Importer le controle comme un module, sans l'executer."""
    spec = importlib.util.spec_from_file_location("verificateur_documentation", CONTROLE)
    if spec is None or spec.loader is None:  # pragma: no cover
        message = f"controle illisible : {CONTROLE}"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preparer(vd: ModuleType, racine_temporaire: Path) -> None:
    """Copier la passation et les six registres, puis y pointer le module.

    **LA LISTE DES FICHIERS EST DERIVEE DE `SEQUENCES`**, comme le controle
    lui-meme : un septieme registre sera copie sans que personne y pense.
    """
    fichiers = ["CLAUDE.md", "docs/README.md"] + [chemin for _, chemin in vd.SEQUENCES]
    for relatif in fichiers:
        cible = racine_temporaire / relatif
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RACINE / relatif, cible)
    vd.RACINE = racine_temporaire
    vd.PASSATION = racine_temporaire / "CLAUDE.md"
    vd.INDEX = racine_temporaire / "docs/README.md"


def _unique(texte: str, motif: re.Pattern[str], quoi: str) -> re.Match[str]:
    """Exiger une correspondance UNIQUE, et le dire clairement sinon."""
    trouves = list(motif.finditer(texte))
    if len(trouves) != 1:
        message = f"{quoi} : {len(trouves)} correspondance(s), 1 attendue"
        raise RuntimeError(message)
    return trouves[0]


#  ---------------------------------------------------------------------------
#  Les mutations, toutes DERIVEES du texte qu'elles recoivent.
#  ---------------------------------------------------------------------------


def reculer_le_prochain(prefixe: str) -> Mutation:
    """Faire RECULER d'une unite le « prochain libre » du tableau de la passation.

    C'est le defaut reel de `ECART-054`, en plus petit : la passation annoncait
    `DEC-541` quand `DEC-565` etait en usage. Reculer d'une seule unite suffit a
    l'exercer, et se derive du fichier au lieu de figer un numero.
    """

    def muter(texte: str) -> tuple[str, str]:
        motif = re.compile(
            r"^\|\s*`"
            + re.escape(prefixe)
            + r"-nnn`\s*\|.*?\|\s*(\*{0,2}`?"
            + re.escape(prefixe)
            + r"-)(\d+)(`?\*{0,2})\s*\|",
            re.M,
        )
        trouve = _unique(texte, motif, f"ligne `{prefixe}-nnn` de la passation")
        avant, chiffres, apres = trouve.group(1), trouve.group(2), trouve.group(3)
        ancien = f"{avant}{chiffres}{apres}"
        recule = f"{int(chiffres) - 1:0{len(chiffres)}d}"
        return ancien, f"{avant}{recule}{apres}"

    return muter


def reculer_le_compte(nom: str) -> Mutation:
    """Faire RECULER d'une unite le compte annonce dans la cellule « Registres »."""

    def muter(texte: str) -> tuple[str, str]:
        motif = re.compile(r"\*\*(\d+)\s+" + re.escape(nom) + r"\*\*")
        trouve = _unique(texte, motif, f"« **N {nom}** » de la passation")
        return trouve.group(0), f"**{int(trouve.group(1)) - 1} {nom}**"

    return muter


def renommer_le_mot(nom: str, remplacant: str) -> Mutation:
    """RENOMMER la cellule, pour prouver qu'un controle qui ne chercherait qu'un
    chiffre serait desarme en silence par un simple changement de libelle.
    """

    def muter(texte: str) -> tuple[str, str]:
        motif = re.compile(r"\*\*(\d+)\s+" + re.escape(nom) + r"\*\*")
        trouve = _unique(texte, motif, f"« **N {nom}** » de la passation")
        return trouve.group(0), f"**{trouve.group(1)} {remplacant}**"

    return muter


def doubler_la_ligne(prefixe: str) -> Mutation:
    """DOUBLER la ligne du tableau, pour prouver que l'unicite est exigee."""

    def muter(texte: str) -> tuple[str, str]:
        motif = re.compile(r"^\|\s*`" + re.escape(prefixe) + r"-nnn`\s*\|[^\n]*\|", re.M)
        trouve = _unique(texte, motif, f"ligne `{prefixe}-nnn` de la passation")
        return trouve.group(0), trouve.group(0) + "\n" + trouve.group(0)

    return muter


def reculer_le_total_du_registre(texte: str) -> tuple[str, str]:
    """Faire RECULER d'une unite le total du tableau de tete, forme « Total N ».

    C'est la forme que le motif d'origine ne voyait pas, si bien que le registre
    des ecarts etait rapporte comme non couvert et son total jamais confronte a
    son corps -- le trou par lequel « 52 ecarts » a survecu dans la passation.
    """
    motif = re.compile(r"^\|\s*\*{0,2}Total\s+(\d+)\*{0,2}\s*\|", re.M)
    trouve = _unique(texte, motif, "ligne « Total N » du registre")
    #  **ON RECONSTRUIT DEPUIS LA CORRESPONDANCE COMPLETE, PAS DEPUIS LES GROUPES.**
    #  La premiere version reassemblait « | » + groupe(1) + ... et perdait l'espace
    #  qui suit la barre, lequel n'appartenait a aucun groupe : la substitution
    #  rendait 0 occurrence, en silence. Le temoin l'a dit parce qu'il EXIGE
    #  l'unicite de sa propre mutation -- un temoin doit s'appliquer a lui-meme
    #  la discipline qu'il verifie.
    ancien = trouve.group(0)
    chiffres = trouve.group(1)
    nouveau = ancien.replace(chiffres, str(int(chiffres) - 1), 1)
    return ancien, nouveau


def barrer_une_declaration(prefixe: str) -> Mutation:
    """BARRER une declaration qui ne l'etait pas : le compte ne doit PAS changer.

    C'est l'epreuve la plus utile du lot, et c'est une ABSENCE d'echec. Avant
    `DEC-565`, le releve ignorait les declarations barrees : barrer une entree
    faisait BAISSER le compte, donc echouer le controle sur des donnees justes.
    """

    def muter(texte: str) -> tuple[str, str]:
        motif = re.compile(r"^\|\s*(`" + re.escape(prefixe) + r"-\d+`)\s*\|", re.M)
        trouves = list(motif.finditer(texte))
        if not trouves:
            message = f"aucune declaration `{prefixe}-nnn` en ligne de tableau"
            raise RuntimeError(message)
        premier = trouves[0]
        return premier.group(0), premier.group(0).replace(
            premier.group(1), f"~~{premier.group(1)}~~"
        )

    return muter


#  Chaque epreuve : son nom, le fichier a abimer, la mutation, le controle a
#  lancer, s'il doit ECHOUER, et un fragment que la sortie doit contenir.
#
#  **LE FRAGMENT ATTENDU N'EST PAS UN LUXE.** Un temoin qui se contenterait d'un
#  code non nul ne prouverait pas que le controle a echoue POUR LA BONNE RAISON :
#  c'est la lecon de `T11` du LOT 2, et celle des huit refus de `T2-3`.
EPREUVES: tuple[tuple[str, str, Mutation, str, bool, str], ...] = (
    (
        "le prochain `DEC` de la passation RECULE d'une unite (le defaut de ECART-054)",
        "CLAUDE.md",
        reculer_le_prochain("DEC"),
        "controler_la_passation",
        True,
        "COLLISION",
    ),
    (
        "le compte de decisions de la passation RECULE d'une unite",
        "CLAUDE.md",
        reculer_le_compte("décisions"),
        "controler_la_passation",
        True,
        "le registre en declare",
    ),
    (
        "la cellule est RENOMMEE : le mot « écarts » disparait",
        "CLAUDE.md",
        renommer_le_mot("écarts", "divergences"),
        "controler_la_passation",
        True,
        "0 occurrence(s) au lieu d'une seule",
    ),
    (
        "la ligne `QO-nnn` du tableau §4.14 est DOUBLEE",
        "CLAUDE.md",
        doubler_la_ligne("QO"),
        "controler_la_passation",
        True,
        "2 ligne(s) `QO-nnn` au lieu d'une seule",
    ),
    (
        "le total du registre des ecarts RECULE (forme « Total N », invisible avant)",
        "docs/decisions/registre-ecarts.md",
        reculer_le_total_du_registre,
        "controler_totaux_des_registres",
        True,
        "le total annonce",
    ),
    (
        "un risque est BARRE, ce qui ne doit RIEN changer au compte",
        "docs/operations/registre-risques.md",
        barrer_une_declaration("ROAD-RSK"),
        "controler_la_passation",
        False,
        "risques, comme le registre",
    ),
)


def executer(vd: ModuleType, quoi: str) -> tuple[int, str]:
    """Lancer un controle et rendre (fautes, sortie)."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        _, fautes = getattr(vd, quoi)()
    return fautes, tampon.getvalue()


def main() -> int:
    vd = charger()
    print("  Temoin du controle de documentation (ECART-054)")
    fautes_du_temoin = 0

    #  D'abord la reference : sur des copies INTACTES, tout doit passer. Sans
    #  elle, un temoin dont toutes les epreuves echouent ne dirait pas si c'est
    #  le controle qui est cassé ou le corpus.
    with tempfile.TemporaryDirectory() as brouillon:
        preparer(vd, Path(brouillon))
        for quoi in ("controler_la_passation", "controler_totaux_des_registres"):
            fautes, _ = executer(vd, quoi)
            if fautes:
                fautes_du_temoin += 1
                print(
                    f"    ECHEC    reference : {quoi} rend {fautes} faute(s) sur un corpus INTACT"
                )
            else:
                print(f"    ok       reference : {quoi} passe sur un corpus intact")

    for nom, relatif, mutation, quoi, doit_echouer, fragment in EPREUVES:
        with tempfile.TemporaryDirectory() as brouillon:
            racine = Path(brouillon)
            preparer(vd, racine)
            chemin = racine / relatif
            texte = chemin.read_text(encoding="utf-8")
            try:
                ancien, nouveau = mutation(texte)
            except RuntimeError as erreur:
                fautes_du_temoin += 1
                print(f"    ECHEC    {nom} — mutation impossible : {erreur}")
                continue
            if texte.count(ancien) != 1:
                fautes_du_temoin += 1
                print(
                    f"    ECHEC    {nom} — la mutation derivee n'est pas unique "
                    f"({texte.count(ancien)} occurrence(s))"
                )
                continue
            chemin.write_text(texte.replace(ancien, nouveau), encoding="utf-8")
            fautes, sortie = executer(vd, quoi)

            if (fautes > 0) != doit_echouer:
                fautes_du_temoin += 1
                attendu = "echouer" if doit_echouer else "PASSER"
                print(
                    f"    ECHEC    {nom} — le controle devait {attendu}, il rend {fautes} faute(s)"
                )
            elif fragment not in sortie:
                fautes_du_temoin += 1
                print(f"    ECHEC    {nom} — sortie sans « {fragment} »")
            else:
                verdict = "echoue" if doit_echouer else "passe, et c'est l'attendu"
                print(f"    ok       {nom} — {verdict}")

    attendues = len(EPREUVES)
    print(f"\n    epreuves attendues : {attendues}   executees : {attendues}")
    if fautes_du_temoin:
        sys.stdout.flush()
        print(f"  ECHEC : {fautes_du_temoin} epreuve(s) du temoin non conformes", file=sys.stderr)
        return 1
    print(f"  --> le controle de documentation sait echouer, sur {attendues} defauts distincts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
