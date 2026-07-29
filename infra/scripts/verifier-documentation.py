#!/usr/bin/env python3
"""Controle de la documentation : integrite des documents immuables et coherence
des sequences d'identifiants.

LOT 1, sous-etape T6, story MVP-L01-US005.

POURQUOI CE CONTROLE EXISTE
    Deux recommandations du lot devenaient effectives en T6.

    ROAD-RSK-029 — un formateur peut reecrire les cinq documents de cadrage
    immuables. Mesure du 27/07/2026 : Prettier ajoutait 54 661 octets au seul
    cahier des charges, soit +21,7 %, et la preuve d'integrite SHA-256 de la
    porte G0 en aurait ete invalidee SANS QU'AUCUN CONTROLE NE LE SIGNALE, le
    contenu restant semantiquement identique. L'exclusion Markdown protege des
    outils d'aujourd'hui, pas de ceux de demain ; recalculer les empreintes est
    le seul garde-fou qui ne depende de la configuration d'aucun outil.

    ECART-021 — quatre nombres du corpus n'etaient pas derives de leur source.
    Le plus grave : le registre des decisions portait « prochain identifiant
    libre : DEC-451 » alors que DEC-469 etait en usage, soit 19 decisions de
    retard, donc une collision garantie pour qui s'y fierait. Ce controle
    compare le marqueur de chaque registre ET l'index de docs/README.md au
    MAXIMUM REELLEMENT EN USAGE, releve dans le registre lui-meme.

CE QU'IL NE COUVRE PAS, ET IL FAUT LE DIRE
    Les nombres cites en prose narrative — « 139 tests », « 33 330 lignes » —
    ne sont pas verifies. Ils changent a chaque commit, et un controle qui
    echouerait sur la description d'un document par lui-meme serait un controle
    qu'on finirait par desactiver. La parade retenue pour ceux-la reste
    humaine : les deriver de la source au moment de les ecrire.

CE QU'IL VERIFIE AUSSI, ET QUI COMPTE AUTANT
    Le nombre de controles executes est confronte au nombre attendu. Un
    controle qui n'annonce pas combien d'elements il a examines peut toujours
    n'en avoir examine qu'un — lecon des defauts T2-4 et T2-6.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

REFERENCE_EMPREINTES = RACINE / "docs/operations/integrite-et-conformite-documents.md"
INDEX = RACINE / "docs/README.md"

EMPREINTES_ATTENDUES = 5

# Une sequence d'identifiants : son prefixe, le registre qui fait foi, et le
# libelle sous lequel l'index de docs/README.md la designe.
SEQUENCES: tuple[tuple[str, str], ...] = (
    ("DEC", "docs/decisions/registre-decisions.md"),
    ("ECART", "docs/decisions/registre-ecarts.md"),
    ("QO", "docs/operations/registre-questions-ouvertes.md"),
    ("ROAD-RSK", "docs/operations/registre-risques.md"),
    ("DEP", "docs/operations/registre-dependances-externes.md"),
    ("CONT", "docs/product/contenus/inventaire-prototype.md"),
)


def identifiants_en_usage(texte: str, prefixe: str) -> set[int]:
    """Relever les identifiants qu'un registre DECLARE, et non ceux qu'il cite.

    Deux formes declaratives coexistent dans le corpus, et il a fallu les deux :
      - une ligne de tableau dont l'identifiant est en PREMIERE colonne, forme
        des decisions, des ecarts et des questions ;
      - un TITRE de section, forme des risques `ROAD-RSK-025` a `031`, dont
        chacun occupe une fiche entiere et non une ligne.

    Ne compter que la premiere forme faisait s'arreter les risques a 24 et
    produisait un echec de mise en forme, pas un echec de fond. Un controle qui
    echoue pour une raison cosmetique finit desactive, donc ne prouve rien.

    Les mentions en PROSE sont volontairement ignorees : la fiche de
    `ECART-021` cite `DEC-451`, et un releve naif la compterait comme un
    identifiant en usage. Un controle qui se laisse berner par sa propre
    documentation ne prouve rien non plus.
    """
    en_ligne = re.compile(r"^\|\s*`?" + re.escape(prefixe) + r"-0*(\d+)`?\s*\|")
    en_titre = re.compile(r"^#{1,4}\s+`?" + re.escape(prefixe) + r"-0*(\d+)`?")
    trouves: set[int] = set()
    for ligne in texte.splitlines():
        for motif in (en_ligne, en_titre):
            if trouve := motif.match(ligne):
                trouves.add(int(trouve.group(1)))
                break
    return trouves


def nommer(prefixe: str, numero: int) -> str:
    """Ecrire un identifiant sur trois chiffres, comme le fait le corpus."""
    return f"{prefixe}-{numero:03d}"


def marqueur_declare(texte: str, prefixe: str) -> int | None:
    """Lire le « prochain identifiant libre » declare par un registre."""
    motif = re.compile(
        r"[Pp]rochain identifiant libre\s*:?\s*\*{0,2}\s*`?" + re.escape(prefixe) + r"-0*(\d+)`?"
    )
    trouve = motif.search(texte)
    return int(trouve.group(1)) if trouve else None


def index_declare(texte: str, prefixe: str) -> int | None:
    """Lire le « prochain libre » que l'index de docs/README.md annonce."""
    motif = re.compile(
        r"^\|\s*`"
        + re.escape(prefixe)
        + r"-nnn`\s*\|.*?\|\s*`?"
        + re.escape(prefixe)
        + r"-0*(\d+)`?\s*\|",
        re.M,
    )
    trouve = motif.search(texte)
    return int(trouve.group(1)) if trouve else None


def controler_empreintes() -> tuple[int, int]:
    """Recalculer les empreintes SHA-256 des documents immuables."""
    print("  Integrite des documents immuables (ROAD-RSK-029)")
    reference = REFERENCE_EMPREINTES.read_text(encoding="utf-8")
    attendues = dict(
        re.findall(r"`?([A-Za-z0-9_./-]+\.md)`?[^\n]*?`?\b([0-9a-f]{64})\b", reference)
    )
    examines = 0
    fautes = 0
    for chemin, empreinte in sorted(attendues.items()):
        fichier = RACINE / chemin
        examines += 1
        if not fichier.is_file():
            print(f"    ECHEC    {chemin} : fichier absent")
            fautes += 1
            continue
        reelle = hashlib.sha256(fichier.read_bytes()).hexdigest()
        if reelle == empreinte:
            print(f"    ok       {chemin}")
        else:
            print(f"    ECHEC    {chemin}")
            print(f"               attendue {empreinte}")
            print(f"               obtenue  {reelle}")
            fautes += 1

    print(f"\n    documents attendus : {EMPREINTES_ATTENDUES}   examines : {examines}")
    if examines != EMPREINTES_ATTENDUES:
        print(
            f"    ECHEC : {examines} empreinte(s) de reference trouvees sur "
            f"{EMPREINTES_ATTENDUES} attendues",
            file=sys.stderr,
        )
        fautes += 1
    return examines, fautes


def controler_sequences() -> tuple[int, int]:
    """Confronter les marqueurs d'identifiant libre au maximum en usage."""
    print("\n  Coherence des sequences d'identifiants (ECART-021)")
    index = INDEX.read_text(encoding="utf-8")
    examines = 0
    fautes = 0
    for prefixe, chemin in SEQUENCES:
        examines += 1
        texte = (RACINE / chemin).read_text(encoding="utf-8")
        en_usage = identifiants_en_usage(texte, prefixe)
        if not en_usage:
            print(f"    ECHEC    {prefixe:9s} aucun identifiant releve dans {chemin}")
            fautes += 1
            continue

        attendu = max(en_usage) + 1
        du_registre = marqueur_declare(texte, prefixe)
        de_l_index = index_declare(index, prefixe)

        ecarts = []
        if du_registre != attendu:
            annonce = nommer(prefixe, du_registre) if du_registre else "rien"
            ecarts.append(f"le registre annonce {annonce}")
        if de_l_index != attendu:
            annonce = nommer(prefixe, de_l_index) if de_l_index else "rien"
            ecarts.append(f"l'index annonce {annonce}")

        if ecarts:
            print(
                f"    ECHEC    {prefixe:9s} maximum en usage {nommer(prefixe, max(en_usage))}, "
                f"donc prochain libre {nommer(prefixe, attendu)} — " + " ; ".join(ecarts)
            )
            fautes += 1
        else:
            print(
                f"    ok       {prefixe:9s} {len(en_usage)} en usage, maximum "
                f"{nommer(prefixe, max(en_usage))}, prochain libre {nommer(prefixe, attendu)}"
            )

    print(f"\n    sequences attendues : {len(SEQUENCES)}   examinees : {examines}")
    if examines != len(SEQUENCES):
        print(
            f"    ECHEC : {examines} sequence(s) examinees sur {len(SEQUENCES)} attendues",
            file=sys.stderr,
        )
        fautes += 1
    return examines, fautes


def main() -> int:
    empreintes, fautes_empreintes = controler_empreintes()
    sequences, fautes_sequences = controler_sequences()

    fautes = fautes_empreintes + fautes_sequences
    print()
    if fautes:
        # stdout vide AVANT d'ecrire sur stderr : sans cela le verdict remonte
        # au-dessus du detail dans les journaux de CI, et on lit une conclusion
        # sans ses motifs.
        sys.stdout.flush()
        print(f"  ECHEC : {fautes} controle(s) non conformes", file=sys.stderr)
        return 1
    print(
        f"  --> {empreintes} documents immuables intacts et "
        f"{sequences} sequences d'identifiants coherentes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
