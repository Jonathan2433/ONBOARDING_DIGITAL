#!/usr/bin/env python3
"""Extraire les pictogrammes officiels eXalt en module TypeScript local.

Chantier design systeme v2 hors lot, etape `E2` (`DEC-682`). Charte 4 :
« extraire les SVG necessaires de `pictos/exalt-icons.json` en composants
locaux, rendus en `currentColor`, taille >= 24px ».

POURQUOI UN GENERATEUR, ET POURQUOI SON RESULTAT EST QUAND MEME VERSIONNE

  Le fichier officiel pese 1,2 Mo et porte **382** pictogrammes. En embarquer la
  totalite dans le paquet ferait voyager jusqu'au navigateur trois cent soixante-
  dix icones que personne n'affiche ; les recopier a la main en ferait vieillir
  la fidelite des la premiere correction amont. Le §6.4 de la passation tranche :
  « pour tout volume, engendre depuis la source par script au lieu de recopier ».

  Le resultat est **commite** malgre tout, exactement comme `jetons.css` l'est a
  cote de `jetons.ts` : une source engendree a la construction serait absente du
  depot, donc illisible en relecture, et un consommateur devrait la produire
  avant de l'importer. La garantie vient d'ailleurs — `pictos.test.ts` relit ce
  meme JSON et **echoue** si le module commite s'en ecarte. Ce n'est pas une
  seconde source, c'est une projection verifiee (lecon `ECART-022`).

LE PERIMETRE EST DERIVE DE LA SPEC, JAMAIS RECOPIE

  Les douze cles ne sont ecrites nulle part dans ce script. Elles sont l'
  INTERSECTION entre les identifiants que `DESIGN_SYSTEME.md` cite entre accents
  graves et les cles reelles du fichier d'icones. Un identifiant est donc une
  cle de picto si et seulement si le catalogue officiel le connait : la regle est
  exacte, pas heuristique (§7.25), et elle ne vieillit pas — nommer un treizieme
  picto dans la spec suffit a l'inclure, sans que personne y pense (§7.27).

  Mesure du 02/11/2026 : 97 identifiants entre accents graves, 382 cles
  officielles, **12** a l'intersection — et les douze sont bien ceux des
  tableaux 4, 6.2, 6.5, 6.7 et 7. Zero faux positif, zero manquant.

CE QUE LE SCRIPT REFUSE DE FAIRE EN SILENCE

  Le champ `path` du JSON est du balisage, pas une liste de courbes : il porte
  parfois des `<g>` d'export Illustrator, et `bouclier-valide` porte meme un
  `id="HWIJHu.tif"` — un nom de calque. Un `id` duplique a chaque rendu d'une
  meme icone est un defaut de DOM, et un `<g>` qui porterait un `transform`
  deplacerait le dessin : l'aplatir sans le dire casserait l'icone.

  Le script **mesure avant d'aplatir**. Il refuse, en nommant l'icone et
  l'attribut, des qu'un element non-`path` porte autre chose qu'un `id`, des
  qu'un `path` porte autre chose qu'un `d`, ou des qu'une reference interne
  (`url(#...)`, `<use>`, `xlink`) rendrait l'`id` signifiant. Il ne reste alors
  que des chaines `d`, et c'est cette forme qui part dans le module : le composant
  n'a **aucun** balisage a injecter, donc aucun `dangerouslySetInnerHTML` a
  ecrire (§7.35 — rendre la propriete structurelle plutot que la surveiller).

EMPLOI

    python3 infra/scripts/engendrer-pictos.py     # engendre, puis formate

IL N'A PAS DE MODE « VERIFIER », ET C'EST DELIBERE

  Un drapeau qui se contenterait de constater que le module existe serait un
  controle qui ne peut pas echouer (§7.0, premiere proposition) : pire qu'aucun
  controle, parce qu'il donnerait l'impression d'en etre un. La divergence est
  prouvee par `packages/ui/src/pictos.test.ts`, qui relit le catalogue officiel
  par un chemin INDEPENDANT de ce script et compare les valeurs — pas le texte
  formate. Il tourne dans `make test-frontend`, donc dans la porte.

  Le script est en revanche IDEMPOTENT apres `make format` : il invoque Prettier
  lui-meme, si bien que le relancer sur un depot propre ne produit aucun diff.
  C'est la lecon d'`E1`, ou les courbes de Bezier de `jetons.ts` ont du etre
  alignees sur la forme normalisee par Prettier pour que le controle de
  divergence survive a chaque `make format` — mesure du 02/11/2026, verifiee.
"""

from __future__ import annotations

import argparse
import html.parser
import json
import pathlib
import shutil
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
HANDOFF = RACINE / "docs" / "design-systeme" / "handoff"
SOURCE_ICONES = HANDOFF / "pictos" / "exalt-icons.json"
SOURCE_SPEC = HANDOFF / "DESIGN_SYSTEME.md"
CIBLE = RACINE / "packages" / "ui" / "src" / "pictos.ts"

#  Les seuls attributs qu'on accepte de PERDRE en aplatissant. `id` y figure
#  parce qu'aucune reference interne ne l'emploie -- ce que le script verifie
#  lui-meme ci-dessous plutot que de s'en remettre a cette note.
ATTRIBUTS_JETABLES = frozenset({"id"})

#  Marqueurs d'une reference interne. Leur presence rendrait un `id` signifiant,
#  donc l'aplatissement destructeur.
MARQUEURS_DE_REFERENCE = ("url(#", "<use", "xlink")


class ErreurDExtraction(RuntimeError):
    """Le balisage source porte quelque chose que l'aplatissement perdrait."""


class CollecteurDeChemins(html.parser.HTMLParser):
    """Releve les `d` des `<path>` dans l'ordre du document, et rien d'autre."""

    def __init__(self, icone: str) -> None:
        super().__init__(convert_charrefs=True)
        self.icone = icone
        self.chemins: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        noms = {nom for nom, _ in attrs}
        if tag == "path":
            if noms != {"d"}:
                raise ErreurDExtraction(
                    f"{self.icone} : <path> porte {sorted(noms)} et non le seul « d ». "
                    "Un attribut de dessin (fill, opacity, transform...) survivrait "
                    "au currentColor ou serait perdu : traite-le explicitement."
                )
            valeur = dict(attrs)["d"]
            if not valeur:
                raise ErreurDExtraction(f"{self.icone} : un <path> a un « d » vide.")
            self.chemins.append(valeur)
            return

        inattendus = noms - ATTRIBUTS_JETABLES
        if inattendus:
            raise ErreurDExtraction(
                f"{self.icone} : <{tag}> porte {sorted(inattendus)}. "
                "Aplatir cet element perdrait cet attribut — donc le dessin."
            )


def cles_citees_par_la_spec(spec: str, catalogue: dict[str, object]) -> list[str]:
    """Les cles de picto que la spec nomme, DERIVEES et non recopiees."""
    import re

    cites = set(re.findall(r"`([^`\n]+)`", spec))
    return sorted(cites & set(catalogue))


def extraire(icone: str, definition: dict[str, str]) -> dict[str, object]:
    balisage = definition["path"]
    for marqueur in MARQUEURS_DE_REFERENCE:
        if marqueur in balisage:
            raise ErreurDExtraction(
                f"{icone} : le balisage porte « {marqueur} ». Une reference interne "
                "rend les identifiants signifiants : l'aplatissement les perdrait."
            )

    collecteur = CollecteurDeChemins(icone)
    collecteur.feed(balisage)
    collecteur.close()
    if not collecteur.chemins:
        raise ErreurDExtraction(f"{icone} : aucun <path> releve.")

    return {
        "nom": definition["name"],
        "viewBox": definition["viewBox"],
        "chemins": collecteur.chemins,
    }


def litteral(valeur: str) -> str:
    """Un litteral de chaine TypeScript. `ensure_ascii=False` : le catalogue est
    francais et le depot est en UTF-8 — `\\u00e9` dans un fichier commite se relit
    mal. Prettier reecrit ensuite les guillemets en apostrophes."""
    return json.dumps(valeur, ensure_ascii=False)


def rendre_le_module(pictos: dict[str, dict[str, object]]) -> str:
    entetes = f"""/**
 * Les pictogrammes officiels eXalt employes par l'application.
 *
 * Chantier design systeme v2 hors lot, etape `E2` (`DEC-682`). Charte 4, 6 et 7.
 *
 * **FICHIER ENGENDRE — NE LE MODIFIE PAS A LA MAIN.**
 *
 *   Source : `docs/design-systeme/handoff/pictos/exalt-icons.json`, {len(CATALOGUE)}
 *   pictogrammes officiels. Generateur : `infra/scripts/engendrer-pictos.py`.
 *   Controle de divergence : `pictos.test.ts`, qui relit le JSON officiel et
 *   echoue si une courbe, un `viewBox` ou un nom s'en ecarte.
 *
 * POURQUOI {len(pictos)} ET PAS {len(CATALOGUE)}
 *
 *   La charte 5 exige que tout composant soit employe par au moins un ecran ;
 *   la meme regle vaut pour une icone. Les {len(pictos)} retenues sont celles que
 *   `DESIGN_SYSTEME.md` NOMME — tableau des huit cercles (4), tuile « Vie
 *   eXalt » (6.2), bloc Vision (6.5), bandeau de parcours (6.7), etat vide (7).
 *
 *   Le perimetre est DERIVE de la spec, pas recopie : le generateur intersecte
 *   les identifiants qu'elle cite entre accents graves avec les cles reelles du
 *   catalogue. Nommer un treizieme picto dans la spec suffit a l'inclure.
 *
 * POURQUOI DES CHAINES `d` ET NON DU BALISAGE
 *
 *   Un champ qui porterait du SVG obligerait le composant a l'injecter par
 *   `dangerouslySetInnerHTML`. Ici le type ne sait porter que des courbes : le
 *   balisage ne peut pas passer, et il n'y a donc rien a surveiller (§7.35).
 *   Les `<g>` d'export Illustrator et l'`id` de calque de `bouclier-valide` ont
 *   ete aplatis APRES mesure — le generateur refuse de le faire des qu'un de ces
 *   elements porte autre chose qu'un `id`, ou qu'une reference interne l'emploie.
 *
 * AUCUNE COULEUR N'EST ECRITE ICI, ET C'EST LA CHARTE 4
 *
 *   Les `<path>` du catalogue ne portent aucun `fill` — mesure du 02/11/2026,
 *   le generateur l'exige. La couleur vient donc du `currentColor` pose par
 *   `Picto`, donc de la couleur de texte du contexte : un picto sur une surface
 *   de cercle prend le texte apparie de ce cercle, sans qu'aucun couple ne soit
 *   redeclare ici.
 */

/** Un pictogramme : son nom lisible, sa boite, et ses courbes. */
export interface DefinitionDePicto {{
  /** Le nom officiel, tel que le catalogue eXalt l'ecrit. */
  readonly nom: string;
  /** La boite du dessin. Chaque icone a la sienne, rarement carree. */
  readonly viewBox: string;
  /** Les attributs `d`, dans l'ordre du document. Jamais du balisage. */
  readonly chemins: readonly string[];
}}

export const PICTOS = {{
"""

    corps: list[str] = []
    for cle in sorted(pictos):
        p = pictos[cle]
        chemins = "".join(f"      {litteral(d)},\n" for d in p["chemins"])  # type: ignore[union-attr]
        corps.append(
            f"  {litteral(cle)}: {{\n"
            f"    nom: {litteral(p['nom'])},\n"
            f"    viewBox: {litteral(p['viewBox'])},\n"
            f"    chemins: [\n{chemins}    ],\n"
            f"  }},\n"
        )

    pied = """} as const satisfies Record<string, DefinitionDePicto>;

/** Les cles reellement disponibles. Un nom inconnu ne compile pas. */
export type ClePicto = keyof typeof PICTOS;
"""
    return entetes + "".join(corps) + pied


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    spec = SOURCE_SPEC.read_text(encoding="utf-8")
    cles = cles_citees_par_la_spec(spec, CATALOGUE)
    if not cles:
        print("ECHEC : la spec ne nomme aucune cle du catalogue officiel.", file=sys.stderr)
        return 1

    try:
        pictos = {cle: extraire(cle, CATALOGUE[cle]) for cle in cles}
    except ErreurDExtraction as erreur:
        print(f"ECHEC : {erreur}", file=sys.stderr)
        return 1

    CIBLE.write_text(rendre_le_module(pictos), encoding="utf-8")
    #  `pnpm` est RESOLU, pas suppose present : un chemin absolu ecrit en dur
    #  figerait le script sur une machine, et un nom nu laisserait l'erreur
    #  « No such file or directory » sans dire laquelle (§7.6, §7.18).
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        print(
            "ECHEC : `pnpm` est introuvable dans le PATH. Le module a ete ecrit mais "
            "pas formate ; `make format` le reprendra.",
            file=sys.stderr,
        )
        return 1

    #  S603 : aucune entree de tiers ne traverse cet appel — la seule valeur
    #  variable est un chemin calcule ici meme — et `shell=False` empeche toute
    #  redecoupe des arguments (§7.2).
    subprocess.run(  # noqa: S603
        [pnpm, "exec", "prettier", "--write", str(CIBLE.relative_to(RACINE))],
        cwd=RACINE,
        check=True,
    )
    total = sum(len(p["chemins"]) for p in pictos.values())  # type: ignore[arg-type]
    print(f"{CIBLE.relative_to(RACINE)} : {len(cles)} pictogrammes, {total} courbes.")
    print(f"Derives de la spec : {', '.join(cles)}")
    return 0


CATALOGUE: dict[str, dict[str, str]] = json.loads(SOURCE_ICONES.read_text(encoding="utf-8"))

if __name__ == "__main__":
    raise SystemExit(main())
