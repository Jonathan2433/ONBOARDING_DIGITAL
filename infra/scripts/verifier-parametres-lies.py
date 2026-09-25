"""Un parametre lie ne doit pas etre partage par deux colonnes de types DIFFERENTS.

Pose le 14/09/2026, hors numerotation des sous-etapes, apres que la classe a
coute QUATRE diagnostics : `T4-2` et `T8-3` du LOT 2, les six fabriques du meme
lot, et `T1-2` du LOT 6, il y a deux jours.

CE QUE LE SYMPTOME DONNE, ET POURQUOI IL COUTE CHER

    psycopg.errors.AmbiguousParameter: inconsistent types deduced for parameter $1
    DETAIL:  character varying versus text

  **Le message ne nomme ni la table ni la colonne.** En `T1-2` il a fait echouer
  39 tests sur 46, et il a fallu lire un plan d'erreur pour trouver que `:c`
  servait `entity.code` -- `character varying(64)` -- et `display_name`, `text`.

POURQUOI LES DEUX TENTATIVES PRECEDENTES ONT ECHOUE — §7.25

  Elles cherchaient le defaut dans le TEXTE :

    - la premiere se declenchait sur le COMMENTAIRE expliquant le motif ;
    - la seconde sur `:p` employe pour `person_id` ET `assigned_by_person_id` --
      deux colonnes `uuid`, reutilisation parfaitement LEGITIME.

  **Le discriminant n'est pas dans le texte source : c'est le TYPE de colonne.**
  Le §7.25 le mesure : `person.email` et `email_normalized` sont tous deux
  `character varying(320)` et se partagent sans peine ; `entity.code` et
  `display_name` non. Ce controle lit donc le type, jamais le texte.

D'OU VIENNENT LES TYPES, ET POURQUOI PAS DU CATALOGUE

  Des **metadonnees SQLAlchemy**, c'est-a-dire de la declaration dont le schema
  est construit. Deux benefices, et le second est le vrai :

    1. aucune base n'est requise, donc le controle tourne dans la tache
       « qualite » de la CI et dans `make check` -- le moment ou il faut le
       savoir est la PULL REQUEST ;
    2. `make migrations-check` prouve deja que le schema obtenu egale ces
       metadonnees. Lire le catalogue serait donc lire la meme verite, une
       dependance de plus.

OU CE CONTROLE S'ARRETE, ET C'EST DIT PLUTOT QUE TU

  Il resout une colonne **positionnellement**, ce qui n'est exact que sur deux
  formes :

    INSERT INTO t (a, b, c) VALUES (:x, :y, :z)     colonnes et parametres alignes
    UPDATE t SET a = :x, b = :y                     colonne nommee a gauche

  **Il ne traite PAS les `WHERE a = :x` d'une requete a jointures** : resoudre
  `a` vers sa table y demanderait de savoir quelle table la porte, donc une
  HEURISTIQUE -- et une heuristique dans un controle est un defaut (§7.25, lecon
  `T9-2`). Les QUATRE occurrences historiques etaient toutes des `INSERT`, ce qui
  est aussi la forme ou le partage est le plus tentant : on ecrit un decor.

  **Il ignore les SQL construits en f-string**, dont il ne peut pas connaitre le
  contenu, et il les COMPTE en sortie : un residuel tu est pire qu'un residuel
  nomme (§7.20).
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))

#  Les repertoires balayes. La liste est courte et DELIBEREE : ce sont les deux
#  seuls endroits de ce depot ou du SQL est ecrit a la main.
REPERTOIRES = ("apps/api", "infra/scripts")

#  `INSERT INTO <table> (<colonnes>) VALUES (<valeurs>)`. Le `re.S` couvre les
#  requetes sur plusieurs lignes, et `[^)]*` s'arrete a la premiere parenthese
#  fermante -- suffisant parce qu'une liste de colonnes n'en contient jamais.
INSERTION = re.compile(
    r"INSERT\s+INTO\s+([a-z_][a-z0-9_]*)\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\)",
    re.I | re.S,
)
#  `UPDATE <table> SET <col> = :<p>[, <col> = :<p>]*`
MISE_A_JOUR = re.compile(
    r"UPDATE\s+([a-z_][a-z0-9_]*)\s+SET\s+(.*?)(?:\bWHERE\b|\bRETURNING\b|$)", re.I | re.S
)
AFFECTATION = re.compile(r"([a-z_][a-z0-9_]*)\s*=\s*:([a-z_][a-z0-9_]*)", re.I)
PARAMETRE = re.compile(r"^:([a-z_][a-z0-9_]*)$", re.I)


def sql_de_ce_module(chemin: pathlib.Path) -> tuple[list[str], int]:
    """Les chaines passees a `text(...)`, plus le compte de celles qu'on IGNORE.

    Une f-string est un `JoinedStr` : son contenu depend de l'execution, et le
    controle ne peut rien en dire. Elle est comptee, pas devinee.
    """
    try:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    except SyntaxError:
        return [], 0
    requetes: list[str] = []
    ignorees = 0
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        nom = noeud.func.id if isinstance(noeud.func, ast.Name) else None
        if nom != "text" or not noeud.args:
            continue
        premier = noeud.args[0]
        if isinstance(premier, ast.Constant) and isinstance(premier.value, str):
            requetes.append(premier.value)
        else:
            ignorees += 1
    return requetes, ignorees


def liaisons(requete: str) -> dict[str, set[tuple[str, str]]]:
    """Parametre lie -> ensemble des (table, colonne) qu'il alimente."""
    trouvees: dict[str, set[tuple[str, str]]] = {}

    for table, colonnes_brutes, valeurs_brutes in INSERTION.findall(requete):
        colonnes = [c.strip() for c in colonnes_brutes.split(",") if c.strip()]
        valeurs = [v.strip() for v in valeurs_brutes.split(",")]
        #  **L'ALIGNEMENT POSITIONNEL EST LA CONDITION DE L'EXACTITUDE.** Des
        #  longueurs differentes veulent dire qu'une valeur contenait une virgule
        #  -- un appel de fonction, un litteral compose. On ne devine pas.
        if len(colonnes) != len(valeurs):
            continue
        for colonne, valeur in zip(colonnes, valeurs, strict=True):
            correspondance = PARAMETRE.match(valeur)
            if correspondance and "." not in colonne:
                trouvees.setdefault(correspondance.group(1), set()).add(
                    (table.lower(), colonne.lower())
                )

    for table, affectations in MISE_A_JOUR.findall(requete):
        for colonne, parametre in AFFECTATION.findall(affectations):
            trouvees.setdefault(parametre, set()).add((table.lower(), colonne.lower()))

    return trouvees


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--temoin",
        action="store_true",
        help="eprouver le controle sur un defaut FABRIQUE, sans toucher au depot",
    )
    arguments = analyseur.parse_args()

    from sqlalchemy.dialects import postgresql

    from app.modeles import metadonnees

    #  **LE TYPE EST COMPILE POUR POSTGRESQL, PAS RENDU GENERIQUEMENT.** C'est
    #  PostgreSQL qui produit « inconsistent types deduced », donc c'est SON
    #  vocabulaire qui fait foi. Mesure du 14/09/2026 : `Uuid` rend `CHAR(32)`
    #  en generique et `UUID` en PostgreSQL. Comparer deux rendus generiques
    #  aurait donne le bon verdict ici, et ce n'est pas une raison : le §7.0
    #  sixieme proposition demande que les deux nombres compares mesurent la
    #  MEME grandeur, et la grandeur en cause est le type que le serveur voit.
    dialecte = postgresql.dialect()
    types: dict[tuple[str, str], str] = {
        (nom_table, colonne.name): colonne.type.compile(dialect=dialecte)
        for nom_table, table in metadonnees.tables.items()
        for colonne in table.columns
    }

    print()
    print("  Parametres lies : un parametre ne sert pas deux types differents — §7.25")
    print(f"    info     {len(metadonnees.tables)} tables, {len(types)} colonnes typees")

    if arguments.temoin:
        return temoin(types)

    fichiers = sorted(
        chemin
        for repertoire in REPERTOIRES
        for chemin in (RACINE / repertoire).rglob("*.py")
        if ".venv" not in chemin.parts and "__pycache__" not in chemin.parts
    )

    requetes_lues = 0
    ignorees = 0
    partages_legitimes = 0
    inconnues: set[tuple[str, str]] = set()
    fautes: list[str] = []

    for chemin in fichiers:
        requetes, ignorees_ici = sql_de_ce_module(chemin)
        ignorees += ignorees_ici
        for requete in requetes:
            requetes_lues += 1
            for parametre, cibles in liaisons(requete).items():
                if len(cibles) < 2:
                    continue
                #  Une colonne que les metadonnees ne connaissent pas n'est pas une
                #  faute : c'est une table d'essai, ou un alias. Comptee, pas devinee.
                connues = {c for c in cibles if c in types}
                inconnues |= cibles - connues
                if len(connues) < 2:
                    continue
                observes = {types[c] for c in connues}
                if len(observes) == 1:
                    partages_legitimes += 1
                    continue
                detail = ", ".join(f"{t}.{c} {types[(t, c)]}" for t, c in sorted(connues))
                fautes.append(f"{chemin.relative_to(RACINE)} : « :{parametre} » sert {detail}")

    print(f"    info     {len(fichiers)} fichiers, {requetes_lues} requetes `text(...)` lues")
    print(f"    ok       {partages_legitimes} partage(s) LEGITIME(S) — memes types, rien a dire")
    if ignorees:
        print(f"    info     {ignorees} SQL en f-string IGNORE(S) : leur contenu depend de")
        print("             l'execution, et deviner serait une heuristique (§7.25)")
    if inconnues:
        print(
            f"    info     {len(inconnues)} colonne(s) hors metadonnees — tables d'essai ou alias"
        )

    print()
    if fautes:
        for faute in fautes:
            print(f"  ECHEC    {faute}")
        print()
        print(f"  ECHEC : {len(fautes)} parametre(s) partage(s) entre types DIFFERENTS.")
        print("           PostgreSQL rendra « inconsistent types deduced for parameter »")
        print("           SANS nommer la colonne. Un parametre par colonne.")
        return 1
    print("  --> aucun parametre lie ne sert deux types differents")
    return 0


def temoin(types: dict[tuple[str, str], str]) -> int:
    """Eprouver le controle sur des requetes FABRIQUEES, dans les DEUX sens.

    **CE TEMOIN NOMME CE QU'IL ATTEND, ET NON UN SIMPLE CODE NON NUL.** §7.25,
    seconde lecon : sa premiere version d'un temoin comparable ne portait qu'une
    cle etrangere simple, si bien que le controle qu'elle devait eprouver
    n'etait JAMAIS atteint. Un temoin qui n'exerce pas un controle ne prouve
    rien de ce controle.
    """
    echecs = 0

    #  1. LE DEFAUT REEL DE `T1-2`, a la lettre : `code` est varchar(64),
    #     `display_name` et `city` sont text.
    fautif = (
        "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
        "VALUES (:c, :c, :c, 'FR', 'active', 'Europe/Paris')"
    )
    cibles = liaisons(fautif).get("c", set())
    observes = {types[c] for c in cibles if c in types}
    if len(cibles) == 3 and len(observes) > 1:
        print(f"    ok       DEFAUT vu : « :c » sert 3 colonnes, {len(observes)} types distincts")
        print(f"             {' / '.join(sorted(observes))}")
    else:
        echecs += 1
        print(f"    ECHEC    le defaut de `T1-2` N'EST PAS vu : cibles={sorted(cibles)}")

    #  2. LE PARTAGE LEGITIME que la seconde tentative du §7.25 refusait a tort :
    #     `person_id` et `assigned_by_person_id` sont tous deux `uuid`.
    legitime = (
        "INSERT INTO framework_responsibility_assignment "
        "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
        "VALUES (:p, :e, :t, :p, :d)"
    )
    cibles = liaisons(legitime).get("p", set())
    observes = {types[c] for c in cibles if c in types}
    if len(cibles) == 2 and len(observes) == 1:
        print("    ok       PARTAGE LEGITIME accepte : `person_id` et")
        print(f"             `assigned_by_person_id`, tous deux {observes.pop()}")
    else:
        echecs += 1
        print(f"    ECHEC    le partage legitime est refuse a tort : {sorted(cibles)}")

    #  3. LE COMMENTAIRE qui faisait echouer la PREMIERE tentative du §7.25. Il
    #     n'est pas du SQL, donc `text(...)` ne le voit pas -- mais un controle
    #     textuel, lui, s'y declenchait. Le temoin le prouve.
    commentaire = "#  un parametre lie partage par deux colonnes rend :c et :c ambigus"
    if not liaisons(commentaire):
        print("    ok       un COMMENTAIRE ne declenche rien — la premiere tentative")
        print("             du §7.25 s'y declenchait")
    else:
        echecs += 1
        print("    ECHEC    un commentaire declenche le controle")

    #  4. L'ALIGNEMENT POSITIONNEL : des longueurs differentes ne sont pas devinees.
    desaligne = "INSERT INTO entity (code, display_name) VALUES (coalesce(:a, 'x'), :a)"
    if not liaisons(desaligne).get("a"):
        print("    ok       une valeur COMPOSEE n'est pas alignee de force")
    else:
        echecs += 1
        print("    ECHEC    une valeur composee a ete alignee positionnellement")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} temoin(s) sur 4 ne prouvent pas ce qu'ils doivent")
        return 1
    print("  --> 4 temoins : le controle mord sur le defaut, et se tait sur le legitime")
    return 0


if __name__ == "__main__":
    sys.exit(main())
