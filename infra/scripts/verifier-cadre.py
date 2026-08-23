#!/usr/bin/env python3
"""Le cadre applicatif, les trois layouts et les jetons — LOT 4, sous-etape `T3`.

POURQUOI CE CONTROLE EXISTE, ET IL EST NE D'UN DEFAUT REEL

  Le 23/08/2026, mesure sur l'application SERVIE : `auth.css`, posee en `T11` du
  LOT 3, emploie **21** proprietes personnalisees. **14 ne resolvaient RIEN** --
  les six espacements, les deux couleurs de marque, la police, deux rayons, trois
  tailles -- et les 7 autres ne resolvaient que par ACCIDENT, `styles.css`
  definissant les memes noms. Rien n'importait `jetons.css`.

  **`make ecrans-check` passait.** Il exigeait qu'aucune couleur LITTERALE ne soit
  ecrite dans la feuille -- la source -- jamais que les jetons RESOLVENT. Le succes
  du controle et la justesse de la page sont deux grandeurs differentes (§7.24).

CE QU'IL EXIGE, ET C'EST EXACT

  1. **toute `var(--x)` employee par une feuille CHARGEE est definie par une
     feuille CHARGEE.** Le graphe des imports est derive de `main.tsx`, `App.tsx`
     et des `@import` des feuilles -- pas suppose ;
  2. **chaque feuille du frontend est CLASSEE.** `verifier-ecrans.py` n'examinait
     qu'un chemin ecrit en dur : une feuille nouvelle lui echappait. Ici une
     feuille non classee fait ECHOUER le controle -- c'est le motif de
     `RELATIONS_ATTENDUES` du §7.27 : declarer, et exiger que cela corresponde ;
  3. **aucune largeur fixe en pixels** dans la feuille du cadre. Ce sont elles qui
     font deborder une page ;
  4. **les points de rupture appartiennent aux largeurs de recette** du cahier
     §13.4, relues dans `jetons.ts` ;
  5. **toute transition declaree est neutralisee** sous `prefers-reduced-motion` ;
  6. **toute route interne passe par le cadre.** La liste est DERIVEE de `App.tsx`
     -- c'est le second critere de sortie de `T3` -- et elle mordra a `T4`, quand
     six rubriques arriveront.

CE QU'IL NE MESURE PAS, ET IL LE DIT

  **Le debordement horizontal reel.** Le mesurer exige un moteur de rendu ; ni
  `jsdom` ni un analyseur CSS n'en ont un. Le cahier §17.1 nomme Playwright et le
  **LOT 12 le possede** -- « tests Playwright » y figure explicitement. L'anticiper
  serait faire le travail d'un lot posterieur.

  Ce controle etablit donc les conditions STRUCTURELLES de l'absence de
  debordement, et la mesure elle-meme est consignee au compte rendu de `T3`, faite
  dans un vrai navigateur aux cinq largeurs du §13.4 **et au-dela** -- le cahier
  ecrit « 1 920 px ET PLUS ».
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
WEB = RACINE / "apps" / "web" / "src"
UI = RACINE / "packages" / "ui" / "src"
ROUTES_APP = WEB / "App.tsx"
JETONS_TS = UI / "jetons.ts"
CADRE_CSS = WEB / "pages" / "application.css"

#  **LA CLASSIFICATION DES FEUILLES, DECLAREE ET EXIGEE.**
#
#  `jetons` definit des proprietes et n'en consomme aucune de l'exterieur.
#  `consommatrice` en consomme et doit toutes les voir resolues.
#  `heritee` est anterieure aux jetons et porte ses propres valeurs : c'est
#  `styles.css`, posee en `T5` du LOT 1, dont les 7 noms communs portent des
#  valeurs IDENTIQUES a celles des jetons -- mesure, donc la collision est benigne.
#  `hors-application` n'est pas chargee par le frontend : elle appartient au
#  paquet `ui` et attend son premier consommateur.
CLASSES = {
    "packages/ui/src/jetons.css": "jetons",
    "packages/ui/src/composants.css": "consommatrice",
    "apps/web/src/styles.css": "heritee",
    "apps/web/src/pages/auth.css": "consommatrice",
    "apps/web/src/pages/application.css": "consommatrice",
}

#  **LA FEUILLE DES COMPOSANTS ETAIT CLASSEE « hors-application », ET C'ETAIT UNE
#  SUPPOSITION QUE LA REALITE A DEMENTIE.**
#
#  Je l'avais classee ainsi en croyant qu'aucun code applicatif n'employait
#  `Bouton`, `Badge` ni `Carte`. Mesure : TROIS ecrans du LOT 3 importent `Bouton`,
#  qui rend `class="ex-bouton"` -- une classe que seule `composants.css` definit.
#  Le bouton rendait donc `border-radius: 0px` et le fond par defaut du navigateur.
#
#  La classification ne suffit donc pas : elle doit etre **derivee**. Si un module
#  du frontend importe quoi que ce soit de `@onboarding/ui`, la feuille des
#  composants DOIT etre chargee -- et le controle 9 l'exige, sans qu'aucune liste
#  n'ait a etre tenue a jour. C'est le §7.27 : une liste recopiee vieillit ; une
#  exigence derivee, non.
IMPORT_COMPOSANTS = "packages/ui/src/composants.css"


def sans_commentaires(source: str) -> str:
    return re.sub(r"/\*.*?\*/", "", source, flags=re.S)


def proprietes_definies(source: str) -> set[str]:
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", sans_commentaires(source)))


def proprietes_utilisees(source: str) -> set[str]:
    return set(re.findall(r"var\((--[a-z0-9-]+)", sans_commentaires(source)))


def feuilles_chargees() -> set[str]:
    """Les feuilles que le frontend charge REELLEMENT, derivees des imports.

    On lit `main.tsx` et tous les modules `.tsx`/`.ts` du frontend : un import de
    CSS dans un module charge la feuille des que le module l'est. Aucun module de
    ce frontend n'est charge paresseusement -- il n'y a ni `lazy` ni `import()`,
    ce que le controle verifie.
    """
    chargees: set[str] = set()
    for module in sorted(WEB.rglob("*.ts*")):
        if module.name.endswith(".test.ts") or module.name.endswith(".test.tsx"):
            continue
        source = module.read_text(encoding="utf-8")
        for cible in re.findall(r"import\s+'([^']+\.css)'", source):
            if cible.startswith("@onboarding/ui/"):
                chargees.add(f"packages/ui/src/{cible.split('/')[-1]}")
            else:
                resolue = (module.parent / cible).resolve()
                chargees.add(resolue.relative_to(RACINE).as_posix())
    return chargees


def largeurs_de_recette() -> list[int]:
    """Les largeurs du cahier §13.4, relues dans `jetons.ts` et non recopiees."""
    source = JETONS_TS.read_text(encoding="utf-8")
    bloc = re.search(r"LARGEURS_RECETTE\s*=\s*\[([^\]]+)\]", source)
    if bloc is None:
        return []
    return [int(v) for v in re.findall(r"\d+", bloc.group(1))]


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--temoin", action="store_true", help="eprouver le controle lui-meme")
    arguments = analyseur.parse_args()

    print()
    print("  Cadre applicatif, layouts et jetons — LOT 4 `T3`, cahier §13.4 et §14.2")

    echecs = 0
    controles = 0

    # ---------------------------------------------------------------- 1
    controles += 1
    toutes = sorted(
        p.relative_to(RACINE).as_posix() for p in [*WEB.rglob("*.css"), *UI.rglob("*.css")]
    )
    non_classees = [f for f in toutes if f not in CLASSES]
    inexistantes = [f for f in CLASSES if f not in toutes]
    if non_classees or inexistantes:
        echecs += 1
        print(f"    ECHEC    {len(toutes)} feuille(s) trouvee(s), classification incoherente")
        for f in non_classees:
            print(f"             NON CLASSEE : {f}")
        for f in inexistantes:
            print(f"             CLASSEE mais ABSENTE : {f}")
        print("             -> classe-la dans `CLASSES`. Une feuille qui echappe au")
        print("                controle est exactement le defaut que T3 a trouve.")
    else:
        print(f"    ok       les {len(toutes)} feuilles du frontend sont classees")

    # ---------------------------------------------------------------- 2
    controles += 1
    chargees = feuilles_chargees()
    definies: set[str] = set()
    for feuille in sorted(chargees):
        chemin = RACINE / feuille
        if chemin.exists():
            definies |= proprietes_definies(chemin.read_text(encoding="utf-8"))

    manquantes: dict[str, set[str]] = {}
    for feuille, classe in sorted(CLASSES.items()):
        if classe != "consommatrice" or feuille not in chargees:
            continue
        source = (RACINE / feuille).read_text(encoding="utf-8")
        absentes = proprietes_utilisees(source) - definies - proprietes_definies(source)
        if arguments.temoin and feuille.endswith("application.css"):
            absentes = {"--jeton-de-temoin-qui-n-existe-pas"}
        if absentes:
            manquantes[feuille] = absentes

    if manquantes:
        echecs += 1
        total = sum(len(v) for v in manquantes.values())
        print(f"    ECHEC    {total} propriete(s) employee(s) mais NON DEFINIE(S) par une")
        print("             feuille chargee :")
        for feuille, absentes in manquantes.items():
            print(f"             {feuille} : {sorted(absentes)}")
        print("             -> la page rendra les defauts du navigateur, SANS que rien")
        print("                n'echoue. C'est le defaut mesure le 23/08/2026 : 14")
        print("                proprietes de `auth.css` ne resolvaient rien.")
    else:
        consommatrices = [f for f, c in CLASSES.items() if c == "consommatrice" and f in chargees]
        print(
            f"    ok       {len(definies)} proprietes definies par les feuilles CHARGEES couvrent"
        )
        print(f"             les {len(consommatrices)} feuille(s) consommatrice(s) chargee(s)")

    # ---------------------------------------------------------------- 3
    controles += 1
    non_chargees = [f for f in toutes if f not in chargees]
    if non_chargees:
        print(f"    info     {len(non_chargees)} feuille(s) NON chargee(s) par le frontend :")
        for f in non_chargees:
            print(f"             {f} — classee « {CLASSES.get(f, '?')} »")
        print("             -> rapporte, non exige : `composants.css` attend son premier")
        print("                consommateur. Mais une feuille CONSOMMATRICE non chargee")
        print("                serait le defaut du 23/08/2026 qui revient.")
    fautives = [f for f in non_chargees if CLASSES.get(f) == "consommatrice"]
    if fautives:
        echecs += 1
        print(f"    ECHEC    feuille(s) consommatrice(s) NON chargee(s) : {fautives}")
    else:
        print("    ok       toute feuille consommatrice est effectivement chargee")

    # ---------------------------------------------------------------- 4
    controles += 1
    cadre = sans_commentaires(CADRE_CSS.read_text(encoding="utf-8"))
    largeurs_fixes = re.findall(r"\n\s*(?:min-)?width:\s*([0-9.]+)px", cadre)
    if largeurs_fixes:
        echecs += 1
        print(f"    ECHEC    largeur(s) fixe(s) en pixels dans le cadre : {largeurs_fixes}")
    else:
        print("    ok       aucune largeur fixe en pixels dans la feuille du cadre")

    # ---------------------------------------------------------------- 5
    controles += 1
    recette = largeurs_de_recette()
    ruptures = sorted({int(v) for v in re.findall(r"min-width:\s*(\d+)px\s*\)", cadre)})
    hors = [r for r in ruptures if r not in recette]
    if not recette:
        echecs += 1
        print("    ECHEC    `LARGEURS_RECETTE` illisible dans `jetons.ts`")
    elif hors:
        echecs += 1
        print(f"    ECHEC    point(s) de rupture hors des largeurs recettees : {hors}")
        print(f"             largeurs du cahier §13.4 : {recette}")
    else:
        print(f"    ok       {len(ruptures)} point(s) de rupture {ruptures}, tous dans les")
        print(f"             {len(recette)} largeurs recettees du cahier §13.4")

    # ---------------------------------------------------------------- 6
    controles += 1
    anime = set(re.findall(r"\n\s*(?:transition|animation):\s*[^;n]", cadre))
    bloc_reduit = re.search(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\s*\)\s*\{(.*?)\n\}", cadre, re.S
    )
    if not anime:
        print("    ok       aucune transition declaree : rien a neutraliser")
    elif bloc_reduit is None:
        echecs += 1
        print(f"    ECHEC    {len(anime)} transition(s) et AUCUN bloc `prefers-reduced-motion`")
    elif "transition: none" not in bloc_reduit.group(1):
        echecs += 1
        print("    ECHEC    le bloc `prefers-reduced-motion` ne neutralise aucune transition")
    else:
        print(f"    ok       {len(anime)} transition(s), neutralisee(s) sous")
        print("             `prefers-reduced-motion` — cahier §14.2")

    # ---------------------------------------------------------------- 7
    controles += 1
    app = ROUTES_APP.read_text(encoding="utf-8")
    if re.search(r"\blazy\b|\bimport\(", app):
        echecs += 1
        print("    ECHEC    chargement paresseux detecte : le graphe d'imports du controle 2")
        print("             ne serait plus exact, une feuille pouvant n'etre chargee que tard")
    else:
        print("    ok       aucun chargement paresseux : le graphe d'imports est complet")

    # ---------------------------------------------------------------- 8
    controles += 1
    #  Les routes internes sont DERIVEES de `App.tsx` : le bloc du cadre, et ce
    #  qu'il contient. Une route interne posee en dehors ferait echouer.
    bloc_cadre = re.search(
        r"<Route\s+path=\{CHEMINS\.entite\}\s+element=\{<CadreApplicatif\s*/>\}>(.*?)</Route>",
        app,
        re.S,
    )
    if arguments.temoin:
        bloc_cadre = None
    if bloc_cadre is None:
        echecs += 1
        print("    ECHEC    aucune route de mise en page `CadreApplicatif` sous `CHEMINS.entite`")
        print("             -> l'entite active ne serait pas visible « sur toutes les pages")
        print("                internes », ce que le §23.3 et la roadmap exigent")
    else:
        internes = re.findall(r"<Route\s+(index|path=\{[^}]+\})", bloc_cadre.group(1))
        print(f"    ok       {len(internes)} route(s) interne(s) sous le cadre, derivee(s) de")
        print("             `App.tsx` — toute page ajoutee dessous herite de l'en-tete")
        print("             par construction. Ce compte augmentera a `T4`.")

    # ---------------------------------------------------------------- 9
    controles += 1
    consommateurs = [
        m.relative_to(RACINE).as_posix()
        for m in sorted(WEB.rglob("*.ts*"))
        if not m.name.endswith((".test.ts", ".test.tsx"))
        and "from '@onboarding/ui'" in m.read_text(encoding="utf-8")
    ]
    if arguments.temoin:
        consommateurs = ["temoin/fabrique.tsx"]
        chargees = chargees - {IMPORT_COMPOSANTS}
    if consommateurs and IMPORT_COMPOSANTS not in chargees:
        echecs += 1
        print(f"    ECHEC    {len(consommateurs)} module(s) importent un composant de")
        print(f"             `@onboarding/ui`, et `{IMPORT_COMPOSANTS}` N'EST PAS chargee :")
        for m in consommateurs[:5]:
            print(f"             {m}")
        print("             -> les classes `ex-*` ne seraient definies par rien, et les")
        print("                composants rendraient en elements NUS du navigateur. C'est")
        print("                le defaut mesure le 23/08/2026 : `border-radius: 0px` sur")
        print("                les trois boutons des huit ecrans du LOT 3.")
    elif consommateurs:
        print(f"    ok       {len(consommateurs)} module(s) emploient un composant de")
        print("             `@onboarding/ui`, et sa feuille de classes EST chargee")
    else:
        print("    info     aucun module n'importe de composant : la feuille des classes")
        print("             n'est pas exigee. Elle le deviendra au premier emploi.")

    # ---------------------------------------------------------------- ce qui n'est pas mesure
    print()
    print("    info     NON MESURE ICI : le debordement horizontal reel.")
    print("             Il exige un moteur de rendu. Le cahier §17.1 nomme Playwright et")
    print("             le LOT 12 le possede. La mesure aux cinq largeurs du §13.4 — et")
    print("             AU-DELA, le cahier ecrivant « 1 920 px et plus » — est consignee")
    print("             au compte rendu de `T3`, faite dans un vrai navigateur.")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles du cadre applicatif, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
