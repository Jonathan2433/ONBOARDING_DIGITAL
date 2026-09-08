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


#  La ligne « Total » du tableau de TETE d'un registre. Les registres ont des
#  nombres de colonnes differents -- 2, 3 ou 4 -- donc le motif ne compte pas les
#  colonnes : il prend le PREMIER nombre qui suit le libelle, qui est l'effectif
#  dans les quatre cas mesures. Les autres colonnes sont des ventilations.
#
#  **`re.M` ET UN ANCRAGE EN DEBUT DE LIGNE** : « Total outillage » et
#  « Total mesure » existent ailleurs dans le registre des questions, et un motif
#  non ancre les attraperait. Mesure : 3 lignes « Total... » dans ce fichier, une
#  seule est le tableau de tete.
MOTIF_TOTAL_DE_REGISTRE = re.compile(
    r"^\|\s*\*\*Total\*\*\s*\|(?:\s*\|)*\s*\*\*(?P<total>\d+)\*\*\s*\|", re.M
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

    **ET UNE TROISIEME FORME, TROUVEE LE 07/09/2026 : LA DECLARATION BARREE.**

        Un identifiant CLOS est ecrit `| ~~`QO-072`~~ |` ou
        `## ~~`ROAD-RSK-032`~~ — CLOS en T10`. Les deux motifs exigeaient
        l'identifiant IMMEDIATEMENT apres le `|` ou le `#`, si bien que **toute
        declaration barree etait ignoree en silence** : 40 questions relevees
        pour 42 declarees, 33 risques pour 34.

        **C'etait un defaut DORMANT du controle de sequences**, pas seulement du
        controle de totaux : le jour ou l'identifiant le PLUS HAUT d'un registre
        serait clos et barre, le maximum releve baisserait, le marqueur
        « prochain identifiant libre » serait juge trop haut, et un numero
        pourrait etre REUTILISE. Aucun registre n'est dans ce cas aujourd'hui --
        c'est ce qui rendait le defaut invisible, et c'est exactement le §7.31 :
        exact pour la forme du jour, aveugle a une autre.

        `ECART-053`, et un temoin par forme est desormais exige plus bas.

    **Le barrage est OPTIONNEL et non alternatif** : `~?~?` accepterait un seul
    tilde, ce qui n'existe pas ; `(?:~~)?` exige la paire ou rien.
    """
    barre = r"(?:~~)?"
    en_ligne = re.compile(r"^\|\s*" + barre + r"`?" + re.escape(prefixe) + r"-0*(\d+)`?")
    en_titre = re.compile(r"^#{1,4}\s+" + barre + r"`?" + re.escape(prefixe) + r"-0*(\d+)`?")
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


def marqueurs_declares(texte: str, prefixe: str) -> list[tuple[int, int]]:
    """TOUS les « prochain identifiant libre » declares, avec leur ligne.

    LA PREMIERE VERSION FAISAIT UN `search`, DONC ELLE LISAIT LE PREMIER ET NE
    VOYAIT JAMAIS LES AUTRES. Elle etait exacte pour le mode de defaillance
    d'ECART-021 — un marqueur unique reste en arriere — et AVEUGLE a celui-ci :
    le registre des ecarts en portait DEUX, `ECART-048` en tete et `ECART-045`
    a la toute fin, trois de retard. Or la fin du fichier est l'endroit ou
    regarde naturellement qui cherche le prochain numero. C'est le §7.31 : un
    garde-fou peut etre exact pour un mode de defaillance et aveugle a un autre.

    Un seul marqueur par registre est EXIGE, et non pas seulement leur accord :
    deux marqueurs qui concordent aujourd'hui divergent le jour ou une
    sous-etape n'en met qu'un a jour, ce qui est exactement ce qui s'est passe.
    """
    motif = re.compile(
        r"[Pp]rochain identifiant libre\s*:?\s*\*{0,2}\s*`?" + re.escape(prefixe) + r"-0*(\d+)`?"
    )
    trouves: list[tuple[int, int]] = []
    for numero_de_ligne, ligne in enumerate(texte.splitlines(), start=1):
        for valeur in motif.findall(ligne):
            trouves.append((numero_de_ligne, int(valeur)))
    return trouves


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
        marqueurs = marqueurs_declares(texte, prefixe)
        du_registre = marqueurs[0][1] if marqueurs else None
        de_l_index = index_declare(index, prefixe)

        ecarts = []
        if len(marqueurs) > 1:
            ou = " ; ".join(f"ligne {ligne} -> {nommer(prefixe, v)}" for ligne, v in marqueurs)
            ecarts.append(f"{len(marqueurs)} marqueurs au lieu d'un seul ({ou})")
        elif du_registre != attendu:
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


MOTIF_LIGNE_TABLEAU = re.compile(r"^\|(?P<libelle>[^|]+)\|(?P<reste>.*)\|\s*$")
MOTIF_NOMBRE = re.compile(r"\*{0,2}(\d+)\*{0,2}")


def tableaux_chiffres(texte: str) -> list[list[tuple[str, list[int]]]]:
    """Les tableaux du document, chacun rendu comme sa liste de lignes chiffrees.

    LE DECOUPAGE PAR TABLEAU N'EST PAS UN DETAIL — c'est un defaut que ma
    premiere version de ce controle portait. Elle relevait toutes les lignes du
    document en une seule liste : le registre en comptant DEUX, celui de l'en-tete
    et celui de la section 6, la somme des lignes reprises valait 170 au lieu de
    85, et celle des lignes `DEC-4xx` 120 au lieu de 60. Le controle comparait
    donc la somme de DEUX tableaux au total d'UN SEUL.

    C'est exactement la sixieme proposition de la regle du lot, celle que T7 a
    payee : un controle qui compare deux nombres doit prouver qu'ils mesurent LA
    MEME GRANDEUR. Ici chaque tableau est verifie CONTRE LUI-MEME, et tous
    doivent l'etre — un seul tableau juste ne suffirait pas.
    """
    tableaux: list[list[tuple[str, list[int]]]] = []
    courant: list[tuple[str, list[int]]] = []
    for ligne in texte.splitlines():
        trouve = MOTIF_LIGNE_TABLEAU.match(ligne)
        if trouve is None:
            # Toute ligne qui n'est pas une ligne de tableau ferme le tableau
            # courant. Les separateurs `|---|` en font partie et sont ignores.
            if courant:
                tableaux.append(courant)
                courant = []
            continue
        libelle = trouve.group("libelle").strip()
        nombres = [
            int(m.group(1))
            for cellule in trouve.group("reste").split("|")
            if (m := MOTIF_NOMBRE.fullmatch(cellule.strip()))
        ]
        if libelle and nombres:
            courant.append((libelle, nombres))
    if courant:
        tableaux.append(courant)
    return tableaux


def controler_totaux_decisions() -> tuple[int, int]:
    """Les totaux annonces par le registre des decisions sont-ils DERIVES ?

    POURQUOI CE CONTROLE EXISTE — un defaut trouve en T8.

        Le registre porte DEUX tableaux de comptage, en tete et en section 6.
        Tous deux annoncaient 145 alors que le corps du registre comptait
        DEC-418 a DEC-482, soit 65 decisions de realisation, donc 85 + 65 = 150.
        L'ecart valait exactement les CINQ decisions de T7 : le corps avait ete
        complete, les tableaux de synthese non.

        C'est la classe de ECART-021 — un nombre affirme sans etre derive de sa
        source — et `docs-check` ne l'attrapait pas : il verifiait les marqueurs
        de « prochain identifiant libre » et les cinq empreintes, pas les totaux.
        La passation §1 est explicite : « Ne retablis aucun compte sans poser
        d'abord le controle qui le derive. » Le voici.

    CE QU'IL VERIFIE, ET TOUT EST DERIVE — aucune valeur n'est codee ici :

        1. le « Total repris » egale la somme des lignes qui le composent ;
        2. la somme des lignes `DEC-nnn` egale le nombre de decisions
           REELLEMENT declarees dans le corps du registre ;
        3. le « Total » egale « Total repris » plus cette somme ;
        4. dans le tableau de completude, « Attendu » egale « Present » partout.

        Le point 2 est celui qui aurait attrape le defaut : il confronte une
        synthese a la source qu'elle resume.
    """
    print()
    print("  Totaux du registre des decisions, derives de son corps (ECART-021)")
    chemin = RACINE / "docs/decisions/registre-decisions.md"
    texte = chemin.read_text(encoding="utf-8")
    fautes = 0
    controles = 0

    reelles = len(identifiants_en_usage(texte, "DEC"))
    tableaux = tableaux_chiffres(texte)
    # Seuls les tableaux de SYNTHESE nous concernent : ceux qui portent une ligne
    # « Total ». Les autres tableaux du registre listent les decisions elles-memes.
    syntheses = [t for t in tableaux if any(libelle.strip("* ") == "Total" for libelle, _ in t)]
    print(
        f"    info     {len(tableaux)} tableaux chiffres, dont {len(syntheses)} de synthese ; "
        f"{reelles} decisions `DEC-` declarees dans le corps"
    )
    # UN DETECTEUR MUET DIRAIT « 0 synthese, aucune incoherence ». On l'exclut.
    controles += 1
    if len(syntheses) < 2:
        print(f"    ECHEC    {len(syntheses)} tableau(x) de synthese trouve(s), 2 attendus")
        fautes += 1
        return controles, fautes
    print(f"    ok       {len(syntheses)} tableaux de synthese a verifier, chacun CONTRE LUI-MEME")

    motif_repris = re.compile(
        r"`(RIGHTS|DATA|ROAD|BACKLOG|ARB-\*|ARB-DROIT|ARB-DATA|ARB-ROAD|ARB-BACK)`"
    )
    #  `DEC-\d+` et NON `DEC-4\d\d`. Le motif d'origine ne voyait que la
    #  centaine 4, ce qui etait juste tant que la sequence n'avait pas franchi
    #  `DEC-499` -- elle l'a franchi le 18/08/2026 en `T1` du LOT 2. Le controle
    #  comptait alors 83 lignes pour 85 decisions declarees, et son message
    #  accusait le registre alors que le defaut etait dans le motif. C'est
    #  `ECART-024` a nouveau : un controle juste a sa date, faux quand le monde
    #  bouge autour de lui. Le mot « realisation » ne designe pas une centaine.
    motif_realisation = re.compile(r"`DEC-\d+")
    for rang, table in enumerate(syntheses, 1):
        somme_reprises = sum(n[0] for libelle, n in table if motif_repris.search(libelle))
        somme_realisation = sum(n[0] for libelle, n in table if motif_realisation.search(libelle))
        repris = [n[0] for libelle, n in table if libelle.startswith("**Total repris**")]
        total = next(n for libelle, n in table if libelle.strip("* ") == "Total")

        # 1. Le total repris, quand la table le declare, egale ses composantes.
        if repris:
            controles += 1
            if repris[0] != somme_reprises:
                print(
                    f"    ECHEC    synthese {rang} : « Total repris » annonce {repris[0]}, "
                    f"somme de ses composantes {somme_reprises}"
                )
                fautes += 1
            else:
                print(f"    ok       synthese {rang} : « Total repris » = {somme_reprises}")

        # 2. LE CONTROLE QUI MANQUAIT : la synthese contre la source qu'elle resume.
        controles += 1
        if somme_realisation != reelles:
            print(
                f"    ECHEC    synthese {rang} : ses lignes `DEC-nnn` totalisent "
                f"{somme_realisation}, le corps du registre en declare {reelles}"
            )
            print("             Une sous-etape a complete le corps sans reprendre la synthese.")
            fautes += 1
        else:
            print(
                f"    ok       synthese {rang} : lignes `DEC-nnn` = {somme_realisation}, "
                f"egal aux {reelles} decisions du corps"
            )

        # 3. Le total general de CETTE table.
        controles += 1
        attendu = somme_reprises + somme_realisation
        if total[0] != attendu:
            print(
                f"    ECHEC    synthese {rang} : « Total » annonce {total[0]} "
                f"au lieu de {attendu} = {somme_reprises} + {somme_realisation}"
            )
            fautes += 1
        else:
            print(
                f"    ok       synthese {rang} : « Total » = {attendu} "
                f"({somme_reprises} repris + {somme_realisation} de realisation)"
            )

        # 4. Quand la table porte deux colonnes chiffrees — « Attendu » et
        #    « Present » — elles doivent concorder ligne par ligne.
        divergentes = [(libelle, n) for libelle, n in table if len(n) >= 2 and n[0] != n[1]]
        deux_colonnes = [n for _, n in table if len(n) >= 2]
        if deux_colonnes:
            controles += 1
            if divergentes:
                for libelle, n in divergentes:
                    print(
                        f"    ECHEC    synthese {rang} : {libelle} attendu {n[0]}, present {n[1]}"
                    )
                fautes += 1
            else:
                print(
                    f"    ok       synthese {rang} : {len(deux_colonnes)} lignes a deux colonnes, "
                    "attendu egal a present partout"
                )

    return controles, fautes


#  **LES QUATRE AUTRES REGISTRES, ET POURQUOI CE CONTROLE MANQUAIT.**
#
#  `controler_totaux_decisions` ci-dessus derive les totaux du registre des
#  DECISIONS. Il a ete ecrit en `T8` du LOT 1 contre un defaut reel de ce
#  registre-la, et il est exact pour lui.
#
#  **Il est AVEUGLE aux cinq autres.** Mesure du 07/09/2026, a la mise a jour
#  documentaire de `T5` du LOT 5 :
#
#      registre des risques   34 declares (12 + 12 + 10 sections), total ANNONCE 33
#                             et le titre du §3 disait « 025 a 033 » alors qu'il
#                             va jusqu'a 034 -- `ROAD-RSK-034` a ete ajoute en
#                             `T8` du LOT 1 sans que ni le total ni le titre
#                             suivent
#      CLAUDE.md §1           « 40 questions (33 ouvertes) » quand le registre en
#                             declare 42 dont 10 closes, donc 32 ouvertes
#
#  **Et la cellule fautive de `CLAUDE.md` affirmait, dans la meme phrase, que
#  `make docs-check` DERIVE ces totaux.** C'est le §7.31 -- un garde-fou exact
#  pour un mode de defaillance et aveugle a un autre -- et le §7.11 dans la
#  meme ligne : verifie ce que la documentation affirme, meme quand c'est toi
#  qui l'ecris. `ECART-053`.
#
#  **LA LISTE DES REGISTRES EST DERIVEE, PAS RECOPIEE** : elle vient de
#  `SEQUENCES`, qui pilote deja `controler_sequences`. Un septieme registre
#  ajoute a `SEQUENCES` entrera donc ici sans que personne y pense -- c'est le
#  §7.27, et c'est ce qui empeche ce controle de vieillir comme le precedent.
def controler_totaux_des_registres() -> tuple[int, int]:
    """Chaque registre annonce-t-il le nombre d'entrees qu'il declare VRAIMENT ?

    Le tableau de tete de chaque registre porte une ligne « Total ». On la
    confronte au nombre d'identifiants que le corps declare -- la meme fonction
    `identifiants_en_usage` que `controler_sequences`, donc la meme definition de
    « declare » : une ligne de tableau OU un titre de section.

    **CE CONTROLE NE PORTE PAS SUR LE REGISTRE DES DECISIONS**, dont les deux
    tableaux de synthese ont une forme propre -- « Total repris » plus les lignes
    de realisation -- et leur propre controle, plus exigeant, juste au-dessus.

    **UN REGISTRE SANS LIGNE « Total » EST RAPPORTE, PAS IGNORE.** Le §7.20 :
    faire dire le vrai plutot que d'affaiblir. `inventaire-prototype.md` est dans
    ce cas -- il declare 29 contenus et n'annonce aucun total -- et le taire
    laisserait croire que les six registres sont couverts quand cinq le sont.
    """
    print()
    print("  Totaux des autres registres, derives de leur corps (ECART-021, ECART-053)")
    fautes = 0
    controles = 0
    sans_total: list[str] = []

    for prefixe, chemin_relatif in SEQUENCES:
        if prefixe == "DEC":
            continue  # son controle propre est juste au-dessus, et plus strict
        chemin = RACINE / chemin_relatif
        texte = chemin.read_text(encoding="utf-8")
        declares = len(identifiants_en_usage(texte, prefixe))

        annonce = MOTIF_TOTAL_DE_REGISTRE.search(texte)
        if annonce is None:
            sans_total.append(f"{prefixe} ({declares} declares)")
            continue

        controles += 1
        attendu = int(annonce.group("total"))
        ligne = texte[: annonce.start()].count("\n") + 1
        if attendu == declares:
            print(f"    ok       {prefixe:12} total {attendu} = {declares} identifiants declares")
        else:
            fautes += 1
            print(
                f"    ECHEC    {prefixe:12} le total annonce {attendu} a la ligne {ligne}, "
                f"mais le corps declare {declares} identifiant(s)"
            )

    #  **LE COMPTE DES CONTROLES EST CONFRONTE A UN ATTENDU DERIVE.** Sans cela,
    #  une expression reguliere qui ne matcherait plus rien annoncerait
    #  « 0 controle, 0 echec » et passerait au vert -- §7.0, troisieme
    #  proposition. L'attendu est le nombre de registres MOINS ceux qui n'ont
    #  pas de ligne « Total », lesquels sont nommes.
    attendu_controles = len(SEQUENCES) - 1 - len(sans_total)
    controles += 1
    if controles - 1 == attendu_controles:
        total_registres = len(SEQUENCES) - 1
        print(
            f"    ok       {attendu_controles} registre(s) sur {total_registres} portent un total"
        )
    else:
        fautes += 1
        print(f"    ECHEC    {controles - 1} total(aux) examine(s), {attendu_controles} attendu(s)")
    if sans_total:
        print(f"    info     sans ligne « Total », donc NON couverts : {', '.join(sans_total)}")

    return controles, fautes


def main() -> int:
    empreintes, fautes_empreintes = controler_empreintes()
    sequences, fautes_sequences = controler_sequences()
    totaux, fautes_totaux = controler_totaux_decisions()
    autres, fautes_autres = controler_totaux_des_registres()

    fautes = fautes_empreintes + fautes_sequences + fautes_totaux + fautes_autres
    print()
    if fautes:
        # stdout vide AVANT d'ecrire sur stderr : sans cela le verdict remonte
        # au-dessus du detail dans les journaux de CI, et on lit une conclusion
        # sans ses motifs.
        sys.stdout.flush()
        print(f"  ECHEC : {fautes} controle(s) non conformes", file=sys.stderr)
        return 1
    print(
        f"  --> {empreintes} documents immuables intacts, "
        f"{sequences} sequences d'identifiants coherentes et "
        f"{totaux + autres} controles de totaux derives"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
