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
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
WEB = RACINE / "apps" / "web" / "src"
UI = RACINE / "packages" / "ui" / "src"
ROUTES_APP = WEB / "App.tsx"
JETONS_TS = UI / "jetons.ts"
CADRE_CSS = WEB / "pages" / "application.css"
ROUTES_TS = WEB / "routes.ts"
NAVIGATION = WEB / "pages" / "NavigationPrincipale.tsx"
BARRE = WEB / "pages" / "BarreMobile.tsx"
NATIONALE = WEB / "pages" / "PageNationale.tsx"
CARTE = WEB / "pages" / "CarteDeFrance.tsx"
SELECTEUR = WEB / "pages" / "SelecteurDEntite.tsx"
MANIFESTE = RACINE / "packages" / "contracts" / "src" / "contrat-api.json"

#  Les formes d'ECRITURE interdites au selecteur d'entite. Nommees UNE FOIS : la
#  premiere version les ecrivait dans la comprehension ET dans le message, donc
#  deux exemplaires qui auraient diverge au premier ajout (§7.27).
MOTIFS_D_ECRITURE = ("<button", "<select", "<form", "<input", "onChange", "onClick")
CAHIER = RACINE / "docs" / "product" / "CAHIER_DES_CHARGES_EXALT_BORDEAUX.md"

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


def sans_commentaires_tsx(source: str) -> str:
    """Le TSX sans ses commentaires — blocs, lignes, et accolades JSX.

    **CE HELPER EXISTE PARCE QUE DEUX DE MES CONTROLES SE SONT DECLENCHES SUR
    LEURS PROPRES COMMENTAIRES.** Le docstring de `CarteDeFrance.tsx` explique
    qu'elle ne doit contenir « ni `<a>`, ni `<button>` » et « pas de `role="img"`,
    pas de `<title>` » : mes motifs y ont trouve exactement ce qu'ils
    interdisaient, et ont signale un livrable conforme.

    **C'est le defaut `T11` du LOT 2 a l'identique**, et `verifier-ecrans.py`
    l'avait deja resolu -- il retire les commentaires CSS avant de chercher. La
    correction n'avait pas ete portee ici : §7.34, une instance corrigee n'est pas
    la classe corrigee, et c'est la troisieme fois que cette classe revient.

    L'ordre compte : les blocs d'abord, puis les accolades JSX, puis les lignes.
    Une ligne `//` a l'interieur d'un bloc `/* */` doit disparaitre avec le bloc.
    """
    sans = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    sans = re.sub(r"\{\s*/\*.*?\*/\s*\}", "", sans, flags=re.S)
    return re.sub(r"^\s*//.*$", "", sans, flags=re.M)


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


def lire_rubriques() -> list[dict[str, str]]:
    """Les rubriques declarees dans `routes.ts`, lues et non supposees.

    Lecture textuelle bornee au bloc `RUBRIQUES` : hors de ce bloc, `routes.ts`
    porte aussi `ECRANS`, dont les entrees ont la meme forme. C'est la lecon de
    `chemins_declares` dans `verifier-ecrans.py` -- une extraction doit dire d'ou
    elle lit, sinon elle lit tout.
    """
    source = ROUTES_TS.read_text(encoding="utf-8")
    try:
        debut = source.index("export const RUBRIQUES")
        fin = source.index("] as const;", debut)
    except ValueError:
        return []
    bloc = source[debut:fin]
    rubriques: list[dict[str, str]] = []
    for entree in re.findall(r"\{(.*?)\}", bloc, re.S):
        cle = re.search(r"cle:\s*'([^']+)'", entree)
        libelle = re.search(r"libelleCorpus:\s*'([^']+)'", entree)
        condition = re.search(r"condition:\s*'([^']+)'", entree)
        if cle and libelle:
            rubriques.append(
                {
                    "cle": cle.group(1),
                    "libelleCorpus": libelle.group(1),
                    "condition": condition.group(1) if condition else "",
                }
            )
    return rubriques


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
    #  **CE CONTROLE A DIT « ok » EN AYANT MESURE ZERO ROUTE, ET C'ETAIT MON
    #  DEFAUT.** Sa premiere version comptait les `<Route>` litteraux du bloc du
    #  cadre ; `T4` les engendre depuis `RUBRIQUES` par `.map()`, si bien que le
    #  motif ne trouvait plus rien -- et le controle annoncait « 0 route(s)
    #  interne(s) » suivi de `ok`. C'est le §7.0 troisieme proposition dans sa
    #  forme la plus crue : un compte affiche n'est un controle que s'il est
    #  CONFRONTE a un attendu.
    controles += 1
    bloc_cadre = re.search(
        r"<Route\s+path=\{CHEMINS\.entite\}\s+element=\{<CadreApplicatif\s*/>\}>(.*?)\n\s*</Route>",
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
    elif "RUBRIQUES.map" not in bloc_cadre.group(1):
        echecs += 1
        print("    ECHEC    les routes internes ne sont pas ENGENDREES depuis `RUBRIQUES`")
        print("             -> une liste litterale de routes divergerait du menu, qui se")
        print("                rend de `RUBRIQUES`. §7.27, et c'est deux sources pour un")
        print("                meme etat.")
    else:
        print("    ok       les routes internes sont ENGENDREES depuis `RUBRIQUES` :")
        print("             le menu et le routeur ne peuvent pas diverger")

    # ---------------------------------------------------------------- 8 bis
    controles += 1
    rubriques = lire_rubriques()
    if len(rubriques) < 1:
        echecs += 1
        print("    ECHEC    `RUBRIQUES` est vide ou illisible dans `routes.ts`")
        print("             -> le menu et les routes internes seraient tous deux vides,")
        print("                et le controle precedent passerait en ayant mesure ZERO.")
    else:
        conditionnelles = [r for r in rubriques if r["condition"]]
        print(f"    ok       {len(rubriques)} rubriques declarees, dont")
        print(
            f"             {len(conditionnelles)} conditionnelle(s) : "
            f"{', '.join(r['cle'] for r in conditionnelles)}"
        )

    # ---------------------------------------------------------------- 8 ter
    controles += 1
    cahier = CAHIER.read_text(encoding="utf-8")
    absents = [r["libelleCorpus"] for r in rubriques if r["libelleCorpus"] not in cahier]
    if arguments.temoin:
        absents = ["libelle-temoin-absent-du-cahier"]
    if absents:
        echecs += 1
        print(
            f"    ECHEC    {len(absents)} libelle(s) introuvable(s) MOT POUR MOT dans le cahier :"
        )
        for libelle in absents:
            print(f"             « {libelle} »")
        print("             -> une reformulation qui « veut dire la meme chose » n'est pas")
        print("                le corpus. §8.2, et c'est le parti de `ECRANS` en `T11`.")
    else:
        print(f"    ok       les {len(rubriques)} libelles sont dans le cahier §8.2, MOT POUR MOT")

    # ---------------------------------------------------------------- 8 quater
    controles += 1
    #  **AUCUN `tabindex` POSITIF NULLE PART.** Il sortirait l'element de l'ordre
    #  du document et ferait sauter le focus -- « l'ordre de tabulation suit
    #  l'ordre visuel » deviendrait faux, et c'est le critere de sortie de `T4`.
    positifs: list[str] = []
    for module in sorted(WEB.rglob("*.tsx")):
        if module.name.endswith(".test.tsx"):
            continue
        for valeur in re.findall(
            r"tabIndex=\{?\s*[\"']?([0-9]+)", module.read_text(encoding="utf-8")
        ):
            if int(valeur) > 0:
                positifs.append(f"{module.relative_to(RACINE).as_posix()} : tabIndex={valeur}")
    if positifs:
        echecs += 1
        print(f"    ECHEC    {len(positifs)} `tabIndex` positif(s) : l'ordre de tabulation")
        print("             ne suivrait plus l'ordre visuel")
        for p in positifs:
            print(f"             {p}")
    else:
        print("    ok       aucun `tabIndex` positif : l'ordre de tabulation est celui du")
        print("             document, donc l'ordre visuel")

    # ---------------------------------------------------------------- 8 quinquies
    controles += 1
    #  L'etat « page courante » doit etre selectionne par `aria-current` dans la
    #  feuille, et non par une classe : sinon l'etat VISUEL et l'etat ANNONCE
    #  viennent de deux sources et peuvent diverger.
    if "aria-current" not in cadre:
        echecs += 1
        print("    ECHEC    la feuille ne selectionne pas sur `aria-current` : l'etat visuel")
        print("             de la rubrique courante et l'etat annonce viendraient de deux")
        print("             sources differentes")
    else:
        nav = NAVIGATION.read_text(encoding="utf-8") if NAVIGATION.exists() else ""
        if "NavLink" not in nav:
            echecs += 1
            print("    ECHEC    la navigation n'emploie pas `NavLink` : `aria-current` devrait")
            print("             alors etre pose a la main, ce qui le figerait")
        else:
            print("    ok       l'etat courant vient de `aria-current`, pose par `NavLink` et")
            print("             selectionne par la feuille — une seule source")

    # ---------------------------------------------------------------- 8 sexies
    controles += 1
    #  **LE LIEN D'EVITEMENT NE SAUTE RIEN SI SA CIBLE N'EST PAS FOCUSABLE.**
    #  Mesure du 23/08/2026 dans un vrai navigateur : sans `tabIndex={-1}` sur le
    #  `<main>`, activer le lien fait defiler la page et met le focus sur `<body>`
    #  -- le Tab suivant repart donc du DEBUT du document, a travers le menu qu'on
    #  venait de sauter. Le `href` et l'`id` correspondaient pourtant : le succes
    #  du test et la justesse du livrable etaient deux grandeurs differentes.
    cadre_source = (WEB / "pages" / "CadreApplicatif.tsx").read_text(encoding="utf-8")
    a_le_lien = 'className="app-evitement"' in cadre_source
    cible_focusable = re.search(r'id="contenu"[^>]*tabIndex=\{-1\}', cadre_source) is not None
    if arguments.temoin:
        cible_focusable = False
    if a_le_lien and not cible_focusable:
        echecs += 1
        print("    ECHEC    le lien d'evitement existe et sa cible n'est PAS focusable")
        print('             (`tabIndex={-1}` absent du `<main id="contenu">`)')
        print("             -> il ferait defiler sans deplacer le focus, et le Tab suivant")
        print("                repartirait du debut du document. Un lien d'evitement qui ne")
        print("                saute rien est PIRE que pas de lien : il consomme un arret")
        print("                de tabulation pour rien et apprend a ne pas s'en servir.")
    elif a_le_lien:
        print("    ok       le lien d'evitement a une cible FOCUSABLE — `tabIndex={-1}` sur")
        print("             le `<main>`, donc le focus s'y deplace vraiment")
    else:
        print("    info     aucun lien d'evitement : rien a exiger de sa cible")

    # ---------------------------------------------------------------- 8 septies
    controles += 1
    #  **LES DEUX REPERES DE NAVIGATION NE COEXISTENT JAMAIS.** Le §8.2 reserve la
    #  barre inferieure au mobile. Deux reperes visibles en meme temps donneraient
    #  deux fois les memes liens dans l'ordre de tabulation, et un lecteur d'ecran
    #  annoncerait deux navigations pour une seule page.
    #
    #  La verification porte sur les DEUX sens : le menu du haut cache par defaut
    #  et montre au-dela de 768 px, la barre montree par defaut et cachee au-dela.
    #  Un seul des deux suffirait a laisser les deux visibles quelque part.
    bloc_tablette = re.search(r"@media \(min-width: 768px\) \{(.*?)\n\}", cadre, re.S)
    menu_cache_par_defaut = re.search(r"\.app-navigation \{[^}]*display:\s*none", cadre) is not None
    menu_montre_a_768 = (
        bloc_tablette is not None
        and re.search(r"\.app-navigation \{[^}]*display:\s*block", bloc_tablette.group(1))
        is not None
    )
    barre_cachee_a_768 = (
        bloc_tablette is not None
        and re.search(r"\.app-barre \{[^}]*display:\s*none", bloc_tablette.group(1)) is not None
    )
    if arguments.temoin:
        barre_cachee_a_768 = False
    manques = [
        nom
        for nom, present in (
            ("le menu du haut cache par defaut", menu_cache_par_defaut),
            ("le menu du haut montre a partir de 768 px", menu_montre_a_768),
            ("la barre cachee a partir de 768 px", barre_cachee_a_768),
        )
        if not present
    ]
    if manques:
        echecs += 1
        print(f"    ECHEC    {len(manques)} regle(s) manquante(s) pour que les DEUX reperes")
        print("             de navigation ne coexistent jamais :")
        for m in manques:
            print(f"             {m}")
    else:
        print("    ok       les deux reperes de navigation ne coexistent JAMAIS : menu du")
        print("             haut a partir de 768 px, barre en dessous — verifie dans les")
        print("             DEUX sens")

    # ---------------------------------------------------------------- 8 octies
    controles += 1
    #  **LE NOMBRE DE CELLULES DE LA BARRE EST BORNE PAR UNE MESURE.** A 320 px,
    #  quatre cellules de 80 px logent les quatre libelles inconditionnels -- dont
    #  « Trombinoscope » sur deux lignes -- et six cellules de 53 px mettraient
    #  « Mon onboarding » sur TROIS lignes. Mesure du 23/08/2026, police reelle.
    #
    #  Le jour ou une rubrique INCONDITIONNELLE serait ajoutee, ce controle le
    #  dira : c'est le seul endroit ou la mesure devient une exigence.
    source_barre = BARRE.read_text(encoding="utf-8") if BARRE.exists() else ""
    borne = re.search(r"CELLULES_MAXIMUM_A_320\s*=\s*(\d+)", source_barre)
    inconditionnelles = [r for r in rubriques if not r["condition"]]
    if not source_barre:
        print("    info     aucune barre mobile : rien a borner")
    elif borne is None:
        echecs += 1
        print("    ECHEC    `CELLULES_MAXIMUM_A_320` introuvable dans `BarreMobile.tsx`")
    elif len(inconditionnelles) > int(borne.group(1)):
        echecs += 1
        print(
            f"    ECHEC    {len(inconditionnelles)} rubriques inconditionnelles pour "
            f"{borne.group(1)} cellules mesurees a 320 px"
        )
        print("             -> a 320 px, un libelle passerait sur trois lignes. Soit la")
        print("                rubrique rejoint « Plus », soit la mesure est refaite.")
    else:
        print(
            f"    ok       {len(inconditionnelles)} rubriques dans la barre pour "
            f"{borne.group(1)} cellules mesurees a 320 px"
        )

    # ---------------------------------------------------------------- 8 nonies
    #  **TOUT REPLI DU CADRE EST UN `<details>` SANS GESTION DE FOCUS.** Un bouton
    #  et son panneau exigeraient de gerer l'ouverture, `Escape` et le RETOUR du
    #  focus -- le terrain meme ou naissent les pieges de focus. §7.2.
    #
    #  **LA LISTE DES REPLIS EST DERIVEE, PAS ECRITE.** La premiere version de ce
    #  controle ne portait que sur `BarreMobile.tsx`, parce que « Plus » etait le
    #  seul repli du jour. `T8` en a ajoute un second -- le selecteur d'entite --
    #  et une exigence ecrite contre UN exemple ne couvre que cet exemple (§7.34).
    #  Tout module du frontend qui emploie `<details>` est donc examine, et le
    #  controle ANNONCE combien il en a trouve.
    replis = {
        module: source
        for module in sorted(WEB.rglob("*.tsx"))
        if not module.name.endswith(".test.tsx")
        for source in [module.read_text(encoding="utf-8")]
        if "<details" in source
    }
    controles += 1
    if not replis:
        print("    info     aucun `<details>` dans le frontend : rien a exiger d'un repli")
    else:
        fautifs = []
        if arguments.temoin:
            fautifs.append("Temoin.tsx : `<details>` SANS `<summary>`")
        for module, source in replis.items():
            nom = module.name
            if "<summary" not in source:
                fautifs.append(f"{nom} : `<details>` sans `<summary>`")
            elif re.search(r"\.focus\(\)|useRef|addEventListener", sans_commentaires_tsx(source)):
                fautifs.append(f"{nom} : manipule le focus ou ecoute des evenements")
        if fautifs:
            echecs += 1
            print(f"    ECHEC    {len(fautifs)} repli(s) fautif(s) sur {len(replis)} :")
            for faute in fautifs:
                print(f"             {faute}")
            print("             -> il faudrait gerer le focus a la main, et c'est la que")
            print("                naissent les pieges que `<details>` rend impossibles")
        else:
            print(
                f"    ok       les {len(replis)} repli(s) sont des `<details>`/`<summary>` et "
                f"AUCUN code n'y touche au focus : aucun piege n'est possible"
            )
            print(f"             modules examines : {', '.join(m.name for m in replis)}")

    # -------------------------------------------------------------- 8 undecies
    controles += 1
    #  **CHANGER D'ENTITE EST UNE NAVIGATION, DONC DES LIENS ET RIEN D'AUTRE.**
    #  `DEC-545` : l'entite consultee vit dans l'adresse. Les regles 1 et 2 du
    #  §23.3 -- « ne modifie pas l'entite principale », « ne transfere pas ses
    #  responsabilites » -- sont alors tenues par CONSTRUCTION : il n'y a aucune
    #  ecriture, donc aucun endroit ou l'une des deux pourrait s'installer plus
    #  tard. Un `<button onClick>` ou un `<select onChange>` ouvrirait cet endroit,
    #  et le livrable resterait fonctionnel -- l'echec serait donc invisible.
    #
    #  C'est une exigence d'ABSENCE : elle ne se declare pas, elle se verifie.
    if not SELECTEUR.exists():
        echecs += 1
        print(f"    ECHEC    {SELECTEUR.name} absent : le changement d'entite n'a pas de porteur")
    else:
        source_selecteur = sans_commentaires_tsx(SELECTEUR.read_text(encoding="utf-8"))
        interdits = [motif for motif in MOTIFS_D_ECRITURE if motif in source_selecteur]
        if arguments.temoin:
            interdits = ["<select-de-temoin"]
        if interdits:
            echecs += 1
            print(
                f"    ECHEC    le selecteur d'entite porte de l'ECRITURE, donc il n'est "
                f"pas une simple NAVIGATION : {interdits}"
            )
            print("             -> `DEC-545` en fait une NAVIGATION ; un gestionnaire d'evenement")
            print("                ouvrirait l'endroit ou les regles 1 et 2 du §23.3 pourraient")
            print("                etre enfreintes sans que rien ne le signale")
        elif "<Link" not in source_selecteur:
            echecs += 1
            print("    ECHEC    le selecteur d'entite ne rend aucun `<Link>`")
        else:
            print("    ok       le changement d'entite est une NAVIGATION : des `<Link>`, et")
            print(f"             AUCUN des {len(MOTIFS_D_ECRITURE)} motifs d'ecriture cherches")

    # ------------------------------------------------------------ 8 terdecies
    controles += 1
    #  **UN SEUL ENDROIT DECIDE SI UNE RUBRIQUE EST VISIBLE.** `T4` avait ecrit le
    #  predicat DEUX fois -- dans `NavigationPrincipale.tsx` et dans
    #  `BarreMobile.tsx` -- sous la forme de deux `if` sur la cle de la rubrique.
    #  `T9` l'a extrait dans `routes.ts`, et ce controle empeche qu'il se duplique
    #  a nouveau : deux copies divergent, et l'utilisateur verrait « Administration »
    #  dans le menu et pas dans la barre (§7.27, `DEC-466`).
    #
    #  **LES CLES SONT DERIVEES DE `RUBRIQUES`, PAS ECRITES.** Une liste litterale
    #  ici serait exactement le defaut que le controle interdit.
    cles_conditionnelles = [r["cle"] for r in lire_rubriques() if r.get("condition")]
    fautifs_predicat = []
    if arguments.temoin:
        fautifs_predicat.append("Temoin.tsx compare la cle `administration`")
    for module in sorted(WEB.rglob("*.tsx")):
        if module.name.endswith(".test.tsx") or module.name == "PageRubrique.tsx":
            continue
        source = sans_commentaires_tsx(module.read_text(encoding="utf-8"))
        for cle in cles_conditionnelles:
            if f"=== '{cle}'" in source or f'=== "{cle}"' in source:
                fautifs_predicat.append(f"{module.name} compare la cle `{cle}`")
    if not cles_conditionnelles:
        echecs += 1
        print("    ECHEC    aucune rubrique conditionnelle : le controle ne prouverait rien")
    elif fautifs_predicat:
        echecs += 1
        print(f"    ECHEC    le predicat de visibilite est DUPLIQUE : {fautifs_predicat}")
        print("             -> `rubriqueEstVisible` de `routes.ts` est le seul endroit ou")
        print("                cette decision se prend ; deux copies divergeraient")
    else:
        print(
            f"    ok       le predicat de visibilite est UNIQUE : aucun composant ne compare "
            f"les {len(cles_conditionnelles)} cles conditionnelles"
        )

    # -------------------------------------------------------- 8 quaterdecies
    controles += 1
    #  **LES ROLES D'ADMINISTRATION NE SONT PAS ECRITS DANS LE FRONTEND.** Ils
    #  viennent du manifeste du contrat, lu par TypeScript ET par Python
    #  (`DEC-492`) : le frontend masque, l'API refuse, et les deux doivent parler
    #  de la MEME liste. Une liste litterale cote client divergerait au premier
    #  role ajoute, et le masquage cesserait de correspondre au refus.
    #
    #  Les codes cherches sont DERIVES du manifeste, jamais recopies ici.
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    codes_administration = manifeste.get("rolesAdministration", [])
    litteraux = []
    if arguments.temoin:
        litteraux.append("Temoin.tsx ecrit `ADM-E` en litteral")
    for module in sorted(WEB.rglob("*.ts*")):
        if module.name.endswith((".test.ts", ".test.tsx")):
            continue
        source = sans_commentaires_tsx(module.read_text(encoding="utf-8"))
        for code in codes_administration:
            if f"'{code}'" in source or f'"{code}"' in source:
                litteraux.append(f"{module.name} ecrit `{code}` en litteral")
    if not codes_administration:
        echecs += 1
        print("    ECHEC    le manifeste ne declare aucun `rolesAdministration`")
    elif litteraux:
        echecs += 1
        print(f"    ECHEC    des roles sont ECRITS dans le frontend : {litteraux}")
        print("             -> ils doivent venir du manifeste, source unique de TS ET Python")
    else:
        print(
            f"    ok       les {len(codes_administration)} roles d'administration viennent du "
            f"MANIFESTE, aucun litteral dans le frontend"
        )

    # ------------------------------------------------------------ 8 quindecies
    controles += 1
    #  **AUCUN ETAT DE SUCCES N'EST ATTEIGNABLE DEPUIS UN `catch`.** C'est le
    #  §17.2 du cahier, mot pour mot : « aucune action n'est declaree enregistree
    #  SANS CONFIRMATION DE L'API ». Et c'est le critere de sortie de `T10` : « un
    #  `fetch` qui echoue APRES L'ENVOI n'affiche JAMAIS "sauvegarde" ».
    #
    #  **LA MESURE EST EXACTE, PAS HEURISTIQUE, ET C'EST ELLE QUI FAIT LE
    #  CONTROLE.** On ne cherche pas des mots dans des messages -- ce serait une
    #  heuristique, donc un defaut (§7.25). On confronte DEUX ensembles derives du
    #  code :
    #
    #    les etats qui rendent `data-ton='succes'`, lus de l'expression du ton ;
    #    les etats affectes DANS un bloc `catch`, lus des corps de `catch`.
    #
    #  Leur intersection doit etre VIDE. Un succes atteignable depuis un `catch`
    #  est litteralement une action declaree aboutie sans reponse de l'API.
    #
    #  **ET LE CONTROLE EXIGE D'AVOIR TROUVE LES DEUX ENSEMBLES.** Un fichier ou
    #  l'extraction ne trouverait rien passerait sinon en silence -- l'echec
    #  produirait la meme observation que le succes (§7.0). Il ANNONCE donc combien
    #  d'ecrans portent un `catch`, et combien portent un etat de succes.
    ecrans_avec_catch = 0
    ecrans_avec_succes = 0
    fautifs_succes = []
    for module in sorted(WEB.rglob("*.tsx")):
        if module.name.endswith(".test.tsx"):
            continue
        source = sans_commentaires_tsx(module.read_text(encoding="utf-8"))
        etats_de_succes = set(re.findall(r"===\s*'([^']+)'\s*\?\s*'succes'", source))
        etats_dans_catch = set()
        for bloc in re.findall(r"\bcatch\b[^{]*\{(.*?)\n\s{4}\}", source, flags=re.S):
            etats_dans_catch |= set(re.findall(r"set[A-Z]\w*\(\s*'([^']+)'", bloc))
        if etats_dans_catch:
            ecrans_avec_catch += 1
        if etats_de_succes:
            ecrans_avec_succes += 1
        fautifs = etats_de_succes & etats_dans_catch
        if fautifs:
            fautifs_succes.append(f"{module.name} : {sorted(fautifs)}")
    if arguments.temoin:
        fautifs_succes.append("Temoin.tsx : ['confirme'] atteignable depuis un `catch`")
    if fautifs_succes:
        echecs += 1
        print(
            f"    ECHEC    un etat de SUCCES est atteignable depuis un `catch` : {fautifs_succes}"
        )
        print("             -> §17.2, « aucune action n'est declaree enregistree SANS")
        print("                confirmation de l'API ». Une panne de transport deviendrait")
        print("                un « sauvegarde » que rien ne justifie")
    elif ecrans_avec_succes == 0 or ecrans_avec_catch == 0:
        echecs += 1
        print(
            f"    ECHEC    l'extraction n'a rien trouve : {ecrans_avec_succes} ecran(s) a etat "
            f"de succes, {ecrans_avec_catch} avec `catch`. Le controle ne prouverait rien"
        )
    else:
        print(
            f"    ok       aucun etat de SUCCES n'est atteignable depuis un `catch` — "
            f"{ecrans_avec_succes} ecran(s) a etat de succes, {ecrans_avec_catch} avec `catch`"
        )

    # --------------------------------------------------------- 8 sexdecies
    controles += 1
    #  **CHAQUE COMPOSANT EXPORTE EST TESTE ET EMPLOYE.** C'est le critere de
    #  sortie de `T11`, mot pour mot : « chaque composant livre est EMPLOYE par un
    #  ecran de ce lot ». Et c'est ce que `T10` du LOT 1 a etabli : livrer un
    #  composant sans ecran qui l'emploie, c'est livrer du code non eprouve.
    #
    #  **LA LISTE EST DERIVEE DE `index.ts`, PAS ECRITE.** Une liste litterale ici
    #  vieillirait au premier composant ajoute -- §7.27 -- et c'est precisement le
    #  cas que le controle doit attraper.
    #
    #  **LA MESURE A TROUVE DEUX ORPHELINS AVANT MEME D'ETRE UN CONTROLE** :
    #  `Badge` et `Carte`, livres en `T10` du LOT 1, n'etaient importes par AUCUN
    #  ecran. Trois seulement l'etaient -- `Bouton`, par les ecrans
    #  d'authentification. Le controle existe pour que cela ne se reproduise pas.
    source_index = (UI / "index.ts").read_text(encoding="utf-8")
    composants = sorted(
        set(re.findall(r"^export \{ ([A-Z][A-Za-z]*) \} from '\./", source_index, flags=re.M))
    )
    tests_ui = " ".join(
        chemin.read_text(encoding="utf-8") for chemin in sorted(UI.glob("*.test.tsx"))
    )
    #  Les imports du frontend, et non le simple mot : `Carte` apparaissait dans
    #  `CarteDeFrance.tsx` sans y etre importe, ce qui aurait rendu le controle
    #  aveugle a l'orphelin qu'il devait trouver.
    imports_frontend = ""
    for module in sorted(WEB.rglob("*.ts*")):
        if module.name.endswith((".test.ts", ".test.tsx")):
            continue
        source = module.read_text(encoding="utf-8")
        for bloc in re.findall(r"import \{([^}]*)\} from '@onboarding/ui'", source, flags=re.S):
            imports_frontend += bloc + ","
    non_testes = [c for c in composants if f"<{c}" not in tests_ui]
    non_employes = [c for c in composants if not re.search(rf"\b{c}\b", imports_frontend)]
    if arguments.temoin:
        non_employes.append("Temoin")
    if not composants:
        echecs += 1
        print("    ECHEC    aucun composant exporte trouve : le controle ne prouverait rien")
    elif non_testes or non_employes:
        echecs += 1
        print(f"    ECHEC    sur {len(composants)} composant(s) exporte(s) :")
        if non_testes:
            print(f"             NON TESTES  : {non_testes}")
        if non_employes:
            print(f"             NON EMPLOYES par un ecran : {non_employes}")
            print("             -> critere de `T11` : « chaque composant livre est EMPLOYE")
            print("                par un ecran de ce lot ». Sinon c'est du code non eprouve")
    else:
        print(
            f"    ok       les {len(composants)} composants exportes sont TESTES et EMPLOYES : "
            f"{', '.join(composants)}"
        )

    # ---------------------------------------------------------------- 8 decies
    controles += 1
    #  **TOUT ELEMENT INTERACTIF DU CADRE A UNE REGLE `:focus-visible` AVEC UN
    #  CONTOUR.** §14.2, « focus visible ».
    #
    #  Ce controle existe parce que la mesure au clavier n'est pas toujours
    #  possible : le volet du navigateur a cesse de delivrer les evenements clavier
    #  deux fois pendant `T5`. Une exigence statique EXACTE vaut mieux qu'une
    #  mesure qu'on ne peut pas rejouer -- et elle tourne a chaque pull request,
    #  ce qu'une mesure manuelle ne fait pas.
    #
    #  **LA LISTE EST DERIVEE DU TSX, PAS DU NOMMAGE, ET C'EST UNE CORRECTION.**
    #
    #  Ma premiere version cherchait les classes de la feuille contenant `-lien` ou
    #  `-evitement`. Elle a signale `.app-liens` -- le `<ul>` CONTENEUR, qui n'est
    #  pas focusable -- soit un FAUX POSITIF des sa premiere execution. Un
    #  garde-fou a faux positifs apprend a passer outre, si bien que le jour ou il
    #  a raison il n'est plus lu : §7.25.
    #
    #  La derivation exacte passe par le TYPE D'ELEMENT, qui est ce qui determine
    #  la focusabilite : `<a>`, `<Link>`, `<NavLink>`, `<button>` et `<summary>`
    #  sont focusables, un `<ul>` non. Le nommage ne le dit pas ; le TSX si.
    interactives_par_element: set[str] = set()
    for module in sorted(WEB.rglob("*.tsx")):
        if module.name.endswith(".test.tsx"):
            continue
        #  **LES COMMENTAIRES SONT RETIRES AVANT L'EXAMEN, ET C'EST LA TROISIEME
        #  FOIS QUE CETTE CLASSE SE REJOUE.** `T7` l'avait corrigee pour deux
        #  autres controles de ce meme fichier ; celui-ci lisait encore la source
        #  brute. Mesure du 24/08/2026 : le docstring de `PanneauDErreur.tsx`
        #  raconte que `T10` ecrivait `<button className="app-action">` -- pour
        #  expliquer qu'il ne le fait PLUS -- et le controle a exige une regle
        #  `:focus-visible` pour une classe que plus aucun element ne porte.
        #
        #  Un garde-fou qui refuse du code correct apprend a passer outre, §7.25.
        #  Et §7.34 : une instance corrigee n'est pas la classe corrigee.
        source_tsx = sans_commentaires_tsx(module.read_text(encoding="utf-8"))
        interactives_par_element |= set(
            re.findall(
                r"<(?:a|Link|NavLink|button|summary)\s[^>]*className=\"(app-[a-z-]+)\"",
                source_tsx,
            )
        )
    interactives = sorted(interactives_par_element)
    sans_focus = [
        classe
        for classe in interactives
        if not re.search(rf"\.{classe}:focus-visible\s*\{{[^}}]*outline:", cadre)
    ]
    if arguments.temoin:
        sans_focus = ["app-temoin-sans-focus"]
    if len(interactives) < 3:
        echecs += 1
        print(f"    ECHEC    {len(interactives)} classe(s) interactive(s) trouvee(s), au moins 3")
        print("             attendues -- la derivation par nommage ne marche plus")
    elif sans_focus:
        echecs += 1
        print(f"    ECHEC    {len(sans_focus)} classe(s) interactive(s) SANS `:focus-visible`")
        print("             portant un `outline` :")
        for classe in sans_focus:
            print(f"             .{classe}")
        print("             -> un utilisateur au clavier ne saurait pas ou il est. §14.2.")
    else:
        print(f"    ok       les {len(interactives)} classes interactives ont une regle")
        print("             `:focus-visible` avec un `outline` — §14.2, focus visible")

    # ---------------------------------------------------------------- 8 undecies
    controles += 1
    #  **LA LISTE PRECEDE LA CARTE DANS LE DOM, PAS SEULEMENT A L'OEIL.**
    #
    #  §8.3 : « Sur mobile, la liste precede la carte. » Un ordre obtenu par
    #  `order` en CSS satisferait le regard et laisserait la carte AVANT la liste
    #  pour un lecteur d'ecran et pour la tabulation : l'echec produirait la meme
    #  observation que le succes sur une capture d'ecran.
    #
    #  Le controle porte donc sur la SOURCE, et il exige les deux choses : que la
    #  feuille ne reordonne pas la liste, et que la carte -- quand `T7` l'apportera
    #  -- vienne apres elle dans le JSX. **Il mordra a `T7`**, et en attendant il
    #  rapporte que la carte est absente plutot que de se taire.
    #  Meme traitement : les commentaires de la page citent `nat-liste` et
    #  `<CarteDeFrance`, et les compter comme du code fausserait leurs positions.
    source_nat = (
        sans_commentaires_tsx(NATIONALE.read_text(encoding="utf-8")) if NATIONALE.exists() else ""
    )
    if not source_nat:
        print("    info     aucune page nationale : rien a ordonner")
    else:
        i_liste = source_nat.find('className="nat-liste"')
        #  **LE MARQUEUR EST L'USAGE DU COMPOSANT, PAS SA CLASSE CSS.**
        #
        #  Ma premiere version cherchait `className="nat-carte"` dans
        #  `PageNationale.tsx`. `T7` a mis la carte dans son propre composant :
        #  la page ne porte plus que `<CarteDeFrance />`, le motif ne trouvait
        #  plus rien, et le controle annoncait « la carte n'existe pas encore »
        #  SUIVI DE `ok` -- alors qu'elle existait. Meme classe qu'a `T4`, ou il
        #  disait `ok` en ayant compte zero route : un controle dont la condition
        #  ne decrit plus la realite ne mesure plus rien.
        #
        #  L'ordre se decide LA OU LES DEUX SONT ECRITS, c'est-a-dire dans la
        #  page : c'est donc l'usage du composant qu'il faut situer.
        i_carte = source_nat.find("<CarteDeFrance")
        reordonne = re.search(r"\.nat-liste[^{]*\{[^}]*order:", cadre) is not None
        if arguments.temoin:
            i_liste, i_carte = 999, 1
        if i_liste < 0:
            echecs += 1
            print("    ECHEC    la page nationale ne porte pas de liste `nat-liste`")
            print("             -> le §8.3 exige « une liste accessible des entites »")
        elif i_carte >= 0 and i_carte < i_liste:
            echecs += 1
            print("    ECHEC    la carte precede la liste DANS LE DOM")
            print("             -> le §8.3 exige l'inverse, et un lecteur d'ecran suit le")
            print("                document, pas la mise en page")
        elif reordonne:
            echecs += 1
            print("    ECHEC    la feuille reordonne `.nat-liste` par `order`")
            print("             -> l'oeil serait satisfait, la tabulation non")
        elif i_carte < 0:
            print("    ok       la liste est la, et la carte n'est pas encore posee : l'ordre")
            print("             sera exige des que `<CarteDeFrance />` apparaitra")
        else:
            print("    ok       la liste PRECEDE la carte dans le DOM, et aucune regle CSS")
            print("             ne les reordonne — §8.3")

    # ---------------------------------------------------------------- 8 duodecies
    controles += 1
    #  **LA CARTE EST DECORATIVE, ET C'EST LE CRITERE DE SORTIE DE `T7`** : « la
    #  carte est decorative au sens de l'accessibilite : elle n'est pas le seul
    #  moyen d'atteindre une entite ».
    #
    #  Trois exigences, et la troisieme est celle que le prototype invite a
    #  enfreindre : il posait un BOUTON sur son image. Un element interactif dans
    #  un sous-arbre `aria-hidden` est atteignable au clavier SANS etre annonce --
    #  pire qu'un bouton absent.
    #  **LES COMMENTAIRES SONT RETIRES AVANT L'EXAMEN.** Sans cela, le docstring
    #  de la carte -- qui explique qu'elle ne doit porter ni `<a>` ni `<button>`,
    #  ni `role="img"` ni `<title>` -- ferait echouer le controle sur un livrable
    #  parfaitement conforme. §7.25, et c'est arrive.
    source_carte = (
        sans_commentaires_tsx(CARTE.read_text(encoding="utf-8")) if CARTE.exists() else ""
    )
    if not source_carte:
        print("    info     aucune carte : rien a exiger d'elle")
    else:
        manques_carte = []
        if 'aria-hidden="true"' not in source_carte:
            manques_carte.append('`aria-hidden="true"` sur le dessin')
        if 'focusable="false"' not in source_carte:
            manques_carte.append('`focusable="false"` — un `<svg>` peut etre focusable')
        if re.search(r"<(?:a|button|Link|NavLink|summary|input)\b", source_carte):
            manques_carte.append("aucun element interactif ne doit y figurer")
        if re.search(r"role=\"img\"|<title>", source_carte):
            manques_carte.append('ni `role="img"` ni `<title>` : elle n\'informe pas')
        if arguments.temoin:
            manques_carte = ["temoin"]
        if manques_carte:
            echecs += 1
            print(f"    ECHEC    {len(manques_carte)} exigence(s) manquante(s) pour que la carte")
            print("             soit DECORATIVE :")
            for m in manques_carte:
                print(f"             {m}")
        else:
            print('    ok       la carte est decorative : `aria-hidden`, `focusable="false"`,')
            print('             aucun element interactif, ni `role="img"` ni `<title>`')

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
