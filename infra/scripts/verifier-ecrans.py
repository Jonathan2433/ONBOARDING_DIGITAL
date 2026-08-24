#!/usr/bin/env python3
"""Les huit ecrans existent-ils, sont-ils servis, et respectent-ils les jetons ?

LOT 3, sous-etape `T11`.

LE COMPTE EST DERIVE DU CAHIER, PAS RECOPIE

  Le cahier et la roadmap donnent la meme liste, en **six puces** dont la derniere
  nomme **trois** pages : 5 + 3 = **huit**. Ce controle relit le document et exige
  que `routes.ts` corresponde -- une liste recopiee vieillit au premier ajout,
  §7.27, six occurrences dans ce lot.

CE QUE « SERVIES A TRAVERS CADDY » EXIGE, ET LE PIEGE QU'IL CACHE

  Une application a page unique ne sert pas huit fichiers : elle sert **le meme
  `index.html`** pour huit adresses, et c'est le routeur qui choisit. Le risque
  n'est donc pas que la page manque, c'est que **le repli n'existe pas** : sans
  `try_files`, un rechargement sur `/connexion/administrateur` rend 404 alors que
  l'application sait afficher la page.

  Ce repli a ete pose en `T7` du LOT 1, qui l'anticipait -- mais **il n'avait
  jamais eu de chemin a replier**. C'est le §7.16 : ce qui n'a jamais tourné
  n'est pas eprouvé. Ce controle est la premiere chose qui l'exerce.

  **ET IL DISTINGUE LES DEUX CIBLES**, parce que `T9` du LOT 1 a montre qu'un
  controle juste du serveur Vite peut etre faux de l'artefact bati. Le type MIME
  fait foi, jamais le code : Vite rend **200 + `index.html`** pour tout chemin
  inconnu (§7.10), donc un 200 seul ne prouverait rien.

DEUX INTERDITS, VERIFIES SUR LES SOURCES

  « aucune couleur hors des jetons de `packages/ui` » et « aucun jeton dans
  `localStorage` ». Les deux se lisent dans les fichiers, et **les commentaires
  sont retires avant l'examen** : le commentaire de tete de `auth.css` cite un
  hexadecimal pour expliquer pourquoi on ne l'ecrit pas, et un controle qui ne les
  retirerait pas se declencherait sur la phrase qui enonce la regle. C'est le
  defaut de `T11` du LOT 2, evite ici.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import ssl
import sys
import urllib.error
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parents[2]
CAHIER = RACINE / "docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md"
ROUTES = RACINE / "apps/web/src/routes.ts"
FEUILLE = RACINE / "apps/web/src/pages/auth.css"
PAGES = RACINE / "apps/web/src/pages"

DELAI_HTTP = 30


#  Les sources des ecrans, examinees pour les deux interdits. La liste est
#  DERIVEE du repertoire, non recopiee : un ecran ajoute y entre seul.
def sources_des_ecrans() -> list[pathlib.Path]:
    return sorted(
        chemin
        for chemin in PAGES.glob("*.tsx")
        if not chemin.name.endswith(".test.tsx") and chemin.name != "PageStatut.tsx"
    )


def sans_commentaires_css(source: str) -> str:
    return re.sub(r"/\*[\s\S]*?\*/", " ", source)


def sans_commentaires_ts(source: str) -> str:
    return re.sub(r"//[^\n]*", " ", re.sub(r"/\*[\s\S]*?\*/", " ", source))


def puces_du_cahier() -> list[str]:
    """Les six puces de « Interfaces incluses » du LOT 3, lues dans le cahier."""
    texte = CAHIER.read_text(encoding="utf-8")
    debut = texte.index("- page de connexion ;")
    section = texte[debut : texte.index("\n\n", debut)]
    return [ligne.strip().lstrip("- ").rstrip(" ;.") for ligne in section.splitlines()]


def libelles_declares() -> list[str]:
    r"""Les `libelleCorpus` du bloc `ECRANS`, et **eux seuls**.

    Pas d'import : ce script tourne sous `python3`, et `routes.ts` est du
    TypeScript. Une lecture textuelle suffit, et elle ne demande aucun outil.

    **CETTE EXTRACTION LISAIT TOUT LE FICHIER, ET `T4` DU LOT 4 L'A CASSEE.**
    `RUBRIQUES` porte six `libelleCorpus` de plus -- les rubriques du menu du
    §8.2 -- si bien que ce controle en comptait **14** au lieu de 8 et cherchait
    « Framework » dans la liste des huit ecrans du §17.5.

    Le plus instructif est que **la meme correction avait deja ete faite juste en
    dessous** : `chemins_declares` est bornee au bloc `CHEMINS` depuis qu'elle a
    attrape des `libelleCorpus` en croyant lire des URL. La correction avait ete
    appliquee a **une instance, pas a la classe** -- c'est exactement le §7.34, un
    motif ecrit contre un exemple ne couvre que cet exemple.
    """
    source = ROUTES.read_text(encoding="utf-8")
    debut = source.index("export const ECRANS")
    bloc = source[debut : source.index("] as const;", debut)]
    return re.findall(r"libelleCorpus:\s*'([^']+)'", bloc)


def chemins_declares() -> list[str]:
    r"""Les valeurs de `CHEMINS`, et **elles seules**.

    **UNE PREMIERE VERSION LISAIT TROP LARGE, ET C'EST LE CONTROLE QUI L'A DIT.**
    Le motif `^\s+\w+: '(...)',$` attrapait aussi les `libelleCorpus` de `ECRANS`,
    si bien que « page de connexion » devenait un chemin d'URL. L'extraction est
    donc **bornee au bloc `CHEMINS`** : une lecture textuelle doit dire d'ou elle
    lit, sinon elle lit tout -- §7.27.
    """
    source = ROUTES.read_text(encoding="utf-8")
    debut = source.index("export const CHEMINS = {")
    bloc = source[debut : source.index("} as const;", debut)]
    return re.findall(r"^\s+\w+: '([^']+)',$", bloc, re.MULTILINE)


def appeler(base: str, chemin: str, contexte: ssl.SSLContext) -> tuple[int, str, bytes]:
    """Appeler une adresse. **Une erreur de transport NOMME le chemin.**

    Ma premiere version laissait remonter l'exception : une trace `urllib` de vingt
    lignes disait « nodename nor servname provided » sans dire **quel** chemin
    l'avait produite -- et c'etait justement le diagnostic. C'est le §7.18 : la
    premiere correction a ecrire est celle qui te dira pourquoi.
    """
    requete = urllib.request.Request(f"{base}{chemin}")  # noqa: S310 — https impose
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return reponse.status, reponse.headers.get("Content-Type", ""), reponse.read()
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.headers.get("Content-Type", ""), erreur.read()
    except urllib.error.URLError as erreur:
        return 0, f"transport: {erreur.reason}", b""


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--base", required=True)
    arguments = analyseur.parse_args()

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Les huit ecrans d'authentification — LOT 3, `T11`")
    print(f"    info     origine {arguments.base}")

    echecs = 0
    controles = 0

    #  --------------------------------------------------------------
    #  1. LE COMPTE EST DERIVE DU CAHIER
    #  --------------------------------------------------------------
    controles += 1
    puces = puces_du_cahier()
    declares = libelles_declares()
    #  La derniere puce nomme trois pages : « pages `403`, `404` et erreur
    #  generale ». Les cinq premieres en nomment une chacune. 5 + 3 = 8.
    attendu = (len(puces) - 1) + 3
    if len(puces) != 6 or attendu != 8 or len(declares) != 8:
        print(
            f"    ECHEC    {len(puces)} puces au cahier, {attendu} ecrans attendus, "
            f"{len(declares)} declares dans `routes.ts`"
        )
        echecs += 1
    else:
        print(f"    ok       {len(puces)} puces au cahier -> {attendu} ecrans, 8 declares")

    controles += 1
    section = "\n".join(puces)
    manquants = [libelle for libelle in declares if libelle not in section]
    if manquants:
        print("    ECHEC    libelle(s) declare(s) absent(s) du cahier, mot pour mot :")
        for libelle in manquants:
            print(f"             {libelle!r}")
        echecs += 1
    else:
        print("    ok       les 8 libelles figurent LITTERALEMENT dans le cahier")

    #  --------------------------------------------------------------
    #  2. AUCUNE COULEUR LITTERALE, COMMENTAIRES RETIRES
    #  --------------------------------------------------------------
    controles += 1
    motif_couleur = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
    feuille = sans_commentaires_css(FEUILLE.read_text(encoding="utf-8"))
    trouvees = motif_couleur.findall(feuille)
    #  TEMOIN — le motif SAIT trouver une couleur. Sans lui, un motif casse
    #  rendrait toujours une liste vide, et l'absence prouverait l'absence de
    #  controle plutot que l'absence de couleur. §7.0, quatrieme proposition.
    temoin = motif_couleur.findall(sans_commentaires_css(".x { color: #abcdef; }"))
    if trouvees:
        print(
            f"    ECHEC    {len(trouvees)} couleur(s) litterale(s) dans auth.css : {trouvees[:4]}"
        )
        echecs += 1
    elif not temoin:
        print("    ECHEC    TEMOIN : le motif ne trouve meme pas une couleur evidente")
        echecs += 1
    else:
        variables = len(re.findall(r"var\(--[a-z0-9-]+\)", feuille))
        print(f"    ok       0 couleur litterale, {variables} references aux jetons — temoin OK")

    #  --------------------------------------------------------------
    #  3. AUCUN STOCKAGE NAVIGATEUR DANS LES SOURCES DES ECRANS
    #  --------------------------------------------------------------
    controles += 1
    interdits = ("localStorage", "sessionStorage", "document.cookie")
    fautifs: list[str] = []
    sources = sources_des_ecrans()
    for chemin in sources:
        depouille = sans_commentaires_ts(chemin.read_text(encoding="utf-8"))
        fautifs += [f"{chemin.name} -> {mot}" for mot in interdits if mot in depouille]
    if not sources:
        print("    ECHEC    aucune source d'ecran trouvee : le controle ne prouverait rien")
        echecs += 1
    elif fautifs:
        print(f"    ECHEC    stockage navigateur employe : {fautifs}")
        echecs += 1
    else:
        print(f"    ok       {len(sources)} sources examinees, aucun stockage navigateur")

    #  --------------------------------------------------------------
    #  4. LES HUIT CHEMINS SONT SERVIS — ET LE TYPE MIME FAIT FOI
    #  --------------------------------------------------------------
    controles += 1
    #  **LES CHEMINS PARAMETRES SONT ECARTES, ET LE CONTROLE LE DIT.**
    #
    #  `T2` du LOT 4 a ajoute `/entites/:code`. Ce n'est pas une adresse : c'est un
    #  gabarit de React Router, et le `:` en est la grammaire -- pas une
    #  heuristique sur du texte. Le tirer litteralement rendrait 200 par le repli
    #  SPA, donc un `ok` obtenu pour une raison qui n'a rien a voir avec le
    #  critere : exactement le defaut du §7.0 quatrieme proposition.
    #
    #  Le vrai chemin d'une entite est eprouve par `make entites-check`, qui
    #  dispose d'un code REEL. Ici on **rapporte** ce qu'on n'a pas verifie, comme
    #  le §7.20 l'exige -- taire une exclusion laisserait croire davantage que ce
    #  qui est vrai.
    tous = [chemin for chemin in chemins_declares() if chemin != "/"]
    a_verifier = [chemin for chemin in tous if ":" not in chemin]
    parametres_ecartes = [chemin for chemin in tous if ":" in chemin]
    if parametres_ecartes:
        print(
            f"    info     {len(parametres_ecartes)} chemin(s) parametre(s) ecarte(s) : "
            f"{', '.join(parametres_ecartes)}"
        )
        print("             ce ne sont pas des adresses. `make entites-check` les eprouve")
        print("             avec un code reel.")
    mauvais: list[str] = []
    for chemin in a_verifier:
        statut, type_mime, corps = appeler(arguments.base, chemin, contexte)
        if statut != 200 or "text/html" not in type_mime or b'id="racine"' not in corps:
            mauvais.append(f"{chemin} -> {statut} {type_mime!r}")
    if len(a_verifier) < 8:
        print(f"    ECHEC    {len(a_verifier)} chemins a verifier, attendu au moins 8")
        echecs += 1
    elif mauvais:
        print("    ECHEC    chemin(s) NON servi(s) — le repli `try_files` manque ?")
        for ligne in mauvais:
            print(f"             {ligne}")
        echecs += 1
    else:
        print(f"    ok       {len(a_verifier)} chemins servis en `text/html` avec le point")
        print("             de montage — le repli SPA du `Caddyfile` est EXERCE")

    #  --------------------------------------------------------------
    #  5. UN LIEN PROFOND AVEC CHAINE DE REQUETE EST SERVI AUSSI
    #  --------------------------------------------------------------
    controles += 1
    statut, type_mime, _ = appeler(
        arguments.base, "/connexion/lien?token=oml_valeur_de_controle", contexte
    )
    if statut != 200 or "text/html" not in type_mime:
        print(f"    ECHEC    lien profond avec jeton : {statut} {type_mime!r}")
        echecs += 1
    else:
        print("    ok       le lien de l'e-mail est servi, chaine de requete comprise")

    #  --------------------------------------------------------------
    #  6. UN CHEMIN INCONNU N'EST PAS SERVI PAR L'API
    #  --------------------------------------------------------------
    controles += 1
    statut, type_mime, _ = appeler(arguments.base, "/api/v1/chemin-qui-n-existe-pas", contexte)
    if "text/html" in type_mime:
        print(
            f"    ECHEC    `/api/*` a recu l'artefact statique ({statut}, {type_mime!r}) : "
            "le repli SPA deborde sur l'API, ce que `DEC-470` interdit"
        )
        echecs += 1
    else:
        print(f"    ok       `/api/*` reste a l'API ({statut}, {type_mime.split(';')[0]})")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles des huit ecrans, 0 echec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
