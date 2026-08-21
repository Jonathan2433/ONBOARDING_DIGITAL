#!/usr/bin/env python3
"""Verifier l'isolation inter-entites du modele §2.5 et §25.3.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE

  Le critere de `US006` dit : « les contraintes SQL et services refusent les
  relations incoherentes ; les tests demontrent l'ABSENCE de fuite ».

  **Une absence ne se demontre pas en montrant qu'un cas est refuse.** Il faut
  enumerer les chemins par lesquels une fuite serait possible, COMPTER ceux qui
  sont fermes, et NOMMER ceux qui ne le sont pas. C'est la troisieme proposition
  du §7.0 de la passation, et c'est ce que `verifier-historisation.py` fait pour
  le §25.2.

  Les huit cles etrangeres composites existent depuis `T5`, `T7` et `T8`, chacune
  avec ses tests. Aucun controle ne disait combien de chemins avaient ete fermes.

LE PIEGE QUE MA PREMIERE MESURE A LAISSE PASSER

  J'ai d'abord enumere les CLES ETRANGERES et constate qu'aucune cle entre deux
  tables locales n'etait simple : toutes composites, donc zero fuite.

  **Une reference posee SANS cle etrangere aurait produit exactement la meme
  observation.** Le controle aurait annonce « zero chemin de fuite » sur un
  schema entierement perce. C'est la quatrieme proposition du §7.0 : un controle
  dont l'echec produirait la meme valeur que le succes ne prouve rien.

  Le controle examine donc les COLONNES, pas les contraintes : toute colonne en
  `_id` doit etre couverte par une cle etrangere, ou etre l'une des trois
  colonnes d'auteur du §3.1 -- qui sont nommees, comptees, et dont l'absence de
  cle est un choix trace dans `app/shared/modele.py`.

ET LE PIEGE DE `MATCH SIMPLE`, QUI EST `T8-1` TRANSPOSE

  PostgreSQL emploie `MATCH SIMPLE` par defaut : **une cle etrangere composite
  dont une colonne est nulle est satisfaite SANS aucune verification.** Une cle
  sur `(circle_id, entity_id)` ou `entity_id` serait nullable ne garantirait donc
  rien des lignes ou l'entite est nulle -- exactement le defaut `T8-1`, ou une
  cle d'exclusion contenant une colonne nullable ne contraignait rien.

  Le controle exige donc que `entity_id` soit `NOT NULL` a la source de toute cle
  composite. Les colonnes de PORTEE nullables -- `circle_id`, `office_id` -- sont
  legitimes : le §8.4 les veut absentes pour un `DSM`, et une contrainte de
  verification posee en `T8` les impose pour un `BOOSTER`. Elles sont rapportees.

LA NULLABILITE ATTENDUE EST DERIVEE DU MODELE, DANS LES DEUX SENS

  Le §2.5 pose que « toutes les tables propres a une entite portent un
  `entity_id` NON NUL », et trois sections declarent une exception : §5.4 pour un
  domaine global, §7.3 pour un alias global, §8.6 pour `SUPER_ADMIN`.

  Le controle LIT ces sections et exige la correspondance **dans les deux sens** :
  une colonne nullable que le modele ne declare pas telle est un echec, et une
  colonne `NOT NULL` que le modele declare nullable en est un autre. Recopier la
  liste des trois exceptions ici serait un `ECART-021` en puissance.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
MODELE = RACINE / "docs" / "architecture" / "MODELE_DONNEES_EXALT.md"

#  Renseigne par `main()` quand `--temoin` est passe : les memes arguments, sans lui.
ARGUMENTS_SANS_TEMOIN: list[str] = []

#  Les trois colonnes d'auteur du §3.1. Le modele les ecrit `uuid null` et ne
#  mentionne AUCUNE cle etrangere ; `app/shared/modele.py` trace les trois
#  motifs, dont l'ordre de creation du §28 et la purge RGPD du LOT 10. Elles ne
#  sont pas un chemin de fuite : `person` est GLOBALE (`ARB-DATA-001`), donc
#  toute personne est legitimement referencable depuis n'importe quelle entite.
COLONNES_D_AUTEUR = ("created_by_person_id", "updated_by_person_id", "archived_by_person_id")

#  NULLABILITE DECLAREE EN PROSE, ET NON DANS UN TABLEAU DE COLONNES.
#
#  Trois sections du modele ecrivent « `entity_id` | Nullable ... » dans leur
#  tableau de champs, et le controle les LIT. Le §10.5, lui, decrit
#  `service_account` par une liste a puces en prose : « une entite FACULTATIVE ».
#  La chaine `entity_id` n'y figure pas.
#
#  **CE RATTACHEMENT EST UNE INTERPRETATION, DECLAREE ICI ET NON DEDUITE.** C'est
#  le parti de `RELATIONS_ATTENDUES` dans `verifier-historisation.py`, et il est
#  prefere a un elargissement du motif sur du francais : une heuristique dans un
#  controle est un defaut -- lecon `T9-2`, confirmee par le §7.25.
#
#  Le controle EXIGE que chaque entree corresponde a une table du schema : une
#  entree devenue fausse echouerait au lieu d'etre ignoree.
NULLABILITE_DECLAREE_EN_PROSE: dict[str, str] = {
    "service_account": "§10.5 : une entite facultative",
}


#  LES TABLES GLOBALES SONT DERIVEES DU MODELE, PLUS RECOPIEES.
#
#  Ma premiere version portait quatre noms en dur -- `client`, `entity`, `person`,
#  `platform_setting`. `T2` du LOT 3 a ajoute **six** tables globales
#  d'authentification, et le controle a echoue en les declarant « inattendues ».
#  C'est `ECART-021`, et c'est la deuxieme fois en deux sous-etapes qu'une liste
#  recopiee de ma main vieillit au premier ajout -- la premiere etait
#  `verifier-images.py`.
#
#  LE CRITERE DERIVABLE : une table est legitimement globale si **la section du
#  modele qui la decrit ne mentionne PAS `entity_id`**. Si le modele lui en donne
#  un et que le schema n'en a pas, c'est un defaut reel. La source fait donc foi,
#  et un ajout futur n'exige plus de toucher ce fichier.


def sql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Executer une requete SQL dans le conteneur de base."""
    # S603 : l'entree vient du Makefile, jamais d'un tiers, et `shell=False` est
    # le motif du §7.2 -- aucun redecoupage des arguments n'a lieu.
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["POSTGRES_DB"],
            "-tAF|",
            "-c",
            requete,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return execution.returncode, (execution.stdout or execution.stderr).strip()


def lignes(sortie: str) -> list[list[str]]:
    return [ligne.split("|") for ligne in sortie.splitlines() if ligne.strip()]


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def defaut_du_modele_pour_entity_id() -> bool:
    """`entity_id` est-il NON NUL par defaut ? Lu dans le bloc des champs communs §3.1.

    **CE DEFAUT EST LA REGLE, ET UNE SECTION DE TABLE N'EN DECLARE QUE L'EXCEPTION.**
    C'est le defaut `T11-1` : ma premiere version cherchait `entity_id` dans la
    section de chaque table et echouait sur cinq tables conformes, dont
    `circle_membership` -- leur section ne le mentionne pas, parce qu'il vient des
    champs communs. Le controle exigeait une declaration que le modele n'a aucune
    raison de repeter dix-huit fois.
    """
    texte = MODELE.read_text(encoding="utf-8")
    debut = texte.index("## 3.1")
    #  Le titre suivant n'est PAS « ## 3.2 » : le §3.1 est suivi de « # 4. Carte
    #  des domaines ». Une borne recopiee est un `ECART-021` en puissance ; on
    #  cherche donc le prochain titre, quel qu'il soit.
    suivant = re.search(r"^#{1,3} ", texte[debut + 6 :], re.MULTILINE)
    fin = debut + 6 + suivant.start() if suivant else len(texte)
    bloc = texte[debut:fin]
    ligne = next(
        (ligne for ligne in bloc.splitlines() if ligne.strip().startswith("entity_id ")),
        None,
    )
    if ligne is None:
        message = "le §3.1 ne declare pas `entity_id` : la derivation du defaut est impossible"
        raise SystemExit(message)
    return "not null" in ligne.lower()


def exceptions_declarees_par_le_modele() -> dict[str, str]:
    """Les tables dont la SECTION declare `entity_id` nullable, avec la citation.

    Lu dans le modele, jamais recopie. Trois sections le font a ce jour -- §5.4
    pour un domaine global, §7.3 pour un alias global, §8.6 pour `SUPER_ADMIN` --
    et le controle n'en connait pas le nombre a l'avance.
    """
    texte = MODELE.read_text(encoding="utf-8")
    resultat: dict[str, str] = {}
    #  UN TITRE PEUT NOMMER PLUSIEURS TABLES, et le §10.5 le fait : «
    #  `service_account` et `service_token` ». Ma premiere version exigeait un
    #  titre a UN seul nom, si bien que `service_account.entity_id` -- nullable
    #  parce que le §10.5 dit « une entite FACULTATIVE » -- etait signale comme
    #  une nullabilite non declaree. Le controle echouait sur un livrable
    #  conforme : §7.20.
    sections = list(re.finditer(r"^## \d+\.\d+ (.+)$", texte, re.MULTILINE))
    for indice, section in enumerate(sections):
        tables = re.findall(r"`([a-z_]+)`", section.group(1))
        if not tables:
            continue
        fin = sections[indice + 1].start() if indice + 1 < len(sections) else len(texte)
        corps = texte[section.end() : fin]
        for ligne in corps.splitlines():
            if "entity_id" not in ligne:
                continue
            if not re.search(r"\bnullable\b|\bnuls?\b|\bfacultative?\b", ligne, re.IGNORECASE):
                continue
            #  Le libelle ne dit pas TOUJOURS de quelle table il s'agit quand le
            #  titre en nomme plusieurs. On rattache a toutes celles du titre :
            #  une exception de trop serait rapportee comme « table absente du
            #  schema », donc visible, jamais silencieuse.
            for table in tables:
                resultat[table] = ligne.strip().strip("|").strip()
    return resultat


def tables_globales_selon_le_modele() -> set[str]:
    """Les tables dont la SECTION du modele ne mentionne aucun `entity_id`.

    C'est le critere derivable de « legitimement globale ». Une table absente du
    modele n'y figure pas : le controle la signalera separement.
    """
    texte = MODELE.read_text(encoding="utf-8")
    sections = list(re.finditer(r"^## \d+\.\d+ (.+)$", texte, re.MULTILINE))
    globales: set[str] = set()
    for indice, section in enumerate(sections):
        tables = re.findall(r"`([a-z_]+)`", section.group(1))
        if not tables:
            continue
        fin = sections[indice + 1].start() if indice + 1 < len(sections) else len(texte)
        if "entity_id" not in texte[section.end() : fin]:
            globales |= set(tables)
    return globales


DEFAUTS_DU_TEMOIN = (
    #  (fragment attendu dans la sortie, ce que le defaut represente)
    ("reference NUE, aucune cle etrangere", "une reference posee sans cle etrangere"),
    ("SIMPLE entre deux tables locales", "une cle non composite entre deux tables locales"),
    ("`entity_id` NULLABLE a la source", "une cle composite rendue inerte par `MATCH SIMPLE`"),
    ("le modele le veut non nul", "un `entity_id` nullable que le modele ne declare pas"),
)


def eprouver_le_temoin(compose: list[str], env: dict[str, str]) -> int:
    """Creer deux tables jetables portant QUATRE defauts, et exiger que le controle echoue.

    **UN CONTROLE QUI NE PEUT PAS ECHOUER NE PROUVE RIEN** -- §7.0 de la passation.
    Et il ne suffit pas d'exiger un code de sortie non nul : le controle pourrait
    echouer pour une raison etrangere -- base injoignable, requete fautive -- et
    l'observation serait la meme. Le temoin exige donc que **chacun des quatre
    messages attendus** apparaisse, nommement.

    Le temoin se relance lui-meme sans `--temoin`, en sous-processus, pour eprouver
    la chaine entiere plutot qu'une fonction interne.
    """
    #  `zz_` pour que l'ordre alphabetique les mette en fin de rapport.
    creation = (
        "CREATE TABLE zz_temoin_cible (id uuid PRIMARY KEY, entity_id uuid NULL, "
        "  CONSTRAINT uq_zz_temoin_cible_id_entity_id UNIQUE (id, entity_id));"
        "CREATE TABLE zz_temoin_source (id uuid PRIMARY KEY, entity_id uuid NULL, "
        "  cible_id uuid NOT NULL, autre_cible_id uuid NOT NULL, orpheline_id uuid NULL, "
        "  CONSTRAINT fk_zz_simple FOREIGN KEY (cible_id) REFERENCES zz_temoin_cible (id), "
        #  LA CLE COMPOSITE EST INDISPENSABLE AU TEMOIN, et sa premiere version
        #  l'a oubliee : avec une seule cle SIMPLE, le controle la refusait au
        #  titre de « non composite » et **le controle `MATCH SIMPLE` n'etait
        #  JAMAIS exercé**. Un temoin qui n'exerce pas un controle ne prouve rien
        #  de ce controle -- et c'est le temoin lui-meme qui l'a dit.
        "  CONSTRAINT fk_zz_composite FOREIGN KEY (autre_cible_id, entity_id) "
        "    REFERENCES zz_temoin_cible (id, entity_id));"
    )
    code, sortie = sql(compose, env, creation)
    if code:
        print(f"  ECHEC     creation du temoin impossible : {sortie[:200]}")
        return 1

    try:
        #  S603 : arguments passes tels quels, `shell=False` — motif du §7.2.
        #  S603 : arguments passes tels quels, `shell=False` — motif du §7.2.
        rejeu = subprocess.run(  # noqa: S603
            [sys.executable, __file__, *ARGUMENTS_SANS_TEMOIN],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte = rejeu.stdout + rejeu.stderr
        print()
        print("  TEMOIN NEGATIF — deux tables jetables portant quatre defauts")
        manquants = 0
        if rejeu.returncode == 0:
            print("    ECHEC    le controle est sorti en 0 sur un schema DELIBEREMENT perce")
            manquants += 1
        else:
            print(f"    ok       le controle est sorti en {rejeu.returncode}, comme attendu")
        for fragment, description in DEFAUTS_DU_TEMOIN:
            if fragment in texte:
                print(f"    ok       detecte : {description}")
            else:
                print(f"    ECHEC    NON detecte : {description}")
                print(f"             fragment attendu absent : {fragment!r}")
                manquants += 1
        print()
        if manquants:
            print(f"  ECHEC : le temoin n'a pas prouve {manquants} discrimination(s)")
            return 1
        print(
            f"  --> le controle sait echouer sur les {len(DEFAUTS_DU_TEMOIN)} defauts, "
            f"et il les NOMME"
        )
        return 0
    finally:
        code, sortie = sql(
            compose, env, "DROP TABLE IF EXISTS zz_temoin_source, zz_temoin_cible CASCADE"
        )
        etat = "supprimees" if code == 0 else f"NON SUPPRIMEES : {sortie[:120]}"
        print(f"    info     tables jetables {etat}")


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument(
        "--temoin",
        action="store_true",
        help="Creer une table jetable portant les trois defauts, et EXIGER que le controle echoue",
    )
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    if arguments.temoin:
        global ARGUMENTS_SANS_TEMOIN
        ARGUMENTS_SANS_TEMOIN = [argument for argument in sys.argv[1:] if argument != "--temoin"]
        return eprouver_le_temoin(compose, env)

    echecs = 0
    print()
    print("  Isolation inter-entites — modele §2.5 et §25.3")

    # ------------------------------------------------------------------
    #  0. Les tables locales, DEDUITES de la presence d'`entity_id`
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT table_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema='public' AND column_name='entity_id' ORDER BY table_name",
    )
    if code:
        print(f"    ECHEC    base injoignable : {sortie[:200]}")
        return 1
    locales = {table: (nul == "YES") for table, nul in lignes(sortie)}

    code, sortie = sql(
        compose,
        env,
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
        "AND table_type='BASE TABLE' AND table_name <> 'alembic_version' ORDER BY table_name",
    )
    toutes = [ligne[0] for ligne in lignes(sortie)]
    globales = sorted(set(toutes) - set(locales))
    print(
        f"    info     {len(toutes)} tables metier : {len(locales)} LOCALES, "
        f"{len(globales)} globales"
    )
    print(f"               globales : {', '.join(globales)}")

    #  Un controle muet dirait « 0 table locale, aucune fuite ».
    if not locales:
        print("    ECHEC    aucune table locale trouvee — le controle ne prouverait rien")
        return 1

    #  Une table globale est LEGITIME si sa section du modele ne mentionne aucun
    #  `entity_id`. Le critere est derive, donc il ne vieillit pas.
    globales_du_modele = tables_globales_selon_le_modele()
    non_justifiees = sorted(set(globales) - globales_du_modele)
    if non_justifiees:
        for table in non_justifiees:
            print(f"    ECHEC    {table} n'a pas d'`entity_id`, et le modele lui en donne un")
            print("             Une table sans `entity_id` echappe a toute cle composite :")
            print("             son caractere global doit etre un CHOIX, pas un oubli.")
        echecs += len(non_justifiees)
    else:
        print(
            f"    ok       les {len(globales)} tables globales le sont selon le modele "
            f"— critere DERIVE, non recopie"
        )

    # ------------------------------------------------------------------
    #  1. La nullabilite d'`entity_id` correspond au modele, DANS LES DEUX SENS
    # ------------------------------------------------------------------
    non_nul_par_defaut = defaut_du_modele_pour_entity_id()
    exceptions = exceptions_declarees_par_le_modele()
    #  Les exceptions ecrites en PROSE, declarees en tete de ce fichier. Une
    #  entree qui ne correspondrait a aucune table du schema est un echec : le
    #  rattachement aurait vieilli.
    for table_declaree, citation in NULLABILITE_DECLAREE_EN_PROSE.items():
        if table_declaree not in locales:
            print(
                f"    ECHEC    {table_declaree} est declaree nullable en prose, "
                f"mais absente du schema"
            )
            echecs += 1
            continue
        exceptions[table_declaree] = citation
    print()
    mot = "NON NUL" if non_nul_par_defaut else "nullable"
    print(f"    info     defaut du §3.1 pour `entity_id` : {mot} — DERIVE du modele")
    print(f"    info     {len(exceptions)} section(s) declarent une EXCEPTION :")
    for table, citation in sorted(exceptions.items()):
        print(f"               {table} : « {citation} »")

    #  UNE EXCEPTION SUR UNE TABLE ABSENTE N'EST PAS UN ECHEC, ET C'EST MESURE.
    #  Le modele decrit les 60+ tables de tous les lots ; le LOT 2 n'en cree que
    #  seize. Quatre exceptions portent sur des tables des LOTS 4 a 12 --
    #  `async_job`, `audit_event`, `onboarding_task_reference`,
    #  `onboarding_template`. Exiger leur presence serait exiger plus que le
    #  critere, ce qui est le defaut du §7.20.
    #
    #  ET L'INQUIETUDE LEGITIME -- « et si c'etait une table du LOT 2 qu'on a
    #  oubliee ? » -- est deja couverte AILLEURS : `test_socle_modele.py` porte la
    #  liste `TABLES_DECLAREES` et echoue si le schema ne la reproduit pas. Un
    #  controle qui redirait la meme chose ajouterait une surface, pas une preuve.
    a_venir = sorted(set(exceptions) - set(locales))
    if a_venir:
        print(
            f"    info     {len(a_venir)} exception(s) portent sur des tables de lots "
            f"ULTERIEURS, non creees :"
        )
        print(f"               {', '.join(a_venir)}")
        print("               La couverture des tables du LOT 2 est tenue par")
        print("               `TABLES_DECLAREES` dans `test_socle_modele.py`.")

    ecarts_nullabilite = 0
    for table in sorted(locales):
        attendu_nullable = table in exceptions or not non_nul_par_defaut
        if locales[table] != attendu_nullable:
            reel = "NULLABLE" if locales[table] else "NOT NULL"
            voulu = "nullable" if attendu_nullable else "non nul"
            source = f"§ de {table}" if table in exceptions else "defaut §3.1"
            print(
                f"    ECHEC    {table}.entity_id est {reel}, le modele le veut {voulu} ({source})"
            )
            echecs += 1
            ecarts_nullabilite += 1
    if not ecarts_nullabilite:
        print(
            f"    ok       les {len(locales)} tables locales ont la nullabilite "
            f"que le modele veut, exceptions comprises"
        )

    # ------------------------------------------------------------------
    #  2. Toute reference est DECLAREE — le piege de ma premiere mesure
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        r"SELECT table_name, column_name FROM information_schema.columns "
        r"WHERE table_schema='public' AND column_name LIKE '%\_id' "
        r"AND table_name <> 'alembic_version' ORDER BY table_name, column_name",
    )
    colonnes = [(t, c) for t, c in lignes(sortie) if c != "id"]
    code, sortie = sql(
        compose,
        env,
        "SELECT c.conrelid::regclass::text, a.attname FROM pg_constraint c "
        "JOIN unnest(c.conkey) AS k(att) ON true "
        "JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.att "
        "WHERE c.contype='f'",
    )
    couvertes = {(t, c) for t, c in lignes(sortie)}
    nues = [(t, c) for t, c in colonnes if (t, c) not in couvertes]
    auteur = [(t, c) for t, c in nues if c in COLONNES_D_AUTEUR]
    fuites_nues = [(t, c) for t, c in nues if c not in COLONNES_D_AUTEUR]

    print()
    print(
        f"    info     {len(colonnes)} colonnes `_id` examinees, "
        f"{len(colonnes) - len(nues)} couvertes par une cle etrangere"
    )
    print(
        f"    ok       {len(auteur)} colonnes d'auteur du §3.1 sans cle "
        f"etrangere — CHOIX TRACE, hors perimetre"
    )
    print(
        f"               ({', '.join(sorted(COLONNES_D_AUTEUR))} — "
        f"`person` est GLOBALE, `ARB-DATA-001`)"
    )
    if fuites_nues:
        for table, colonne in fuites_nues:
            print(f"    ECHEC    {table}.{colonne} : reference NUE, aucune cle etrangere")
            print("             Une reference sans cle etrangere donne la meme observation")
            print("             qu'un schema sans fuite. C'est le piege de ma premiere mesure.")
            echecs += 1
    else:
        print("    ok       aucune reference nue : toute colonne `_id` est declaree ou classee")

    # ------------------------------------------------------------------
    #  3. Toute cle entre deux tables LOCALES est COMPOSITE
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT c.conname, c.conrelid::regclass::text, c.confrelid::regclass::text, "
        "(SELECT string_agg(a.attname, ',' ORDER BY x.ord) "
        "   FROM unnest(c.conkey) WITH ORDINALITY AS x(att,ord) "
        "   JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=x.att), "
        "(SELECT string_agg(a.attname, ',' ORDER BY x.ord) "
        "   FROM unnest(c.confkey) WITH ORDINALITY AS x(att,ord) "
        "   JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=x.att), "
        "c.confmatchtype "
        "FROM pg_constraint c WHERE c.contype='f' ORDER BY 2, 1",
    )
    cles = lignes(sortie)
    composites: list[list[str]] = []
    vers_globale: list[list[str]] = []
    print()
    print(f"    info     {len(cles)} cles etrangeres au total")
    for nom, source, cible, cols, rcols, _match in cles:
        colonnes_source = cols.split(",")
        if cible == "entity":
            continue  # le rattachement a l'entite elle-meme, non une reference locale
        if source in locales and cible in locales:
            if "entity_id" not in colonnes_source:
                print(
                    f"    ECHEC    {source} -> {cible} ({cols}) : SIMPLE entre deux tables locales"
                )
                print(
                    "             Le §2.5 exige que les deux ressources soient de la meme entite."
                )
                echecs += 1
            else:
                composites.append([nom, source, cible, cols, rcols])
        elif cible in globales:
            vers_globale.append([nom, source, cible, cols])

    print(f"    ok       {len(composites)} cles COMPOSITES entre deux tables locales, 0 simple")
    for _nom, source, cible, cols, rcols in composites:
        print(f"               {source} -> {cible} ({cols}) references ({rcols})")

    # ------------------------------------------------------------------
    #  4. `entity_id` est NOT NULL a la source — le piege `MATCH SIMPLE`
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT c.relname || '.' || a.attname FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname='public' AND a.attnum > 0 AND NOT a.attisdropped AND NOT a.attnotnull",
    )
    nullables_en_base = {ligne[0] for ligne in lignes(sortie)}
    print()
    portees_nullables: list[str] = []
    for _nom, source, cible, cols, _rcols in composites:
        if f"{source}.entity_id" in nullables_en_base:
            print(f"    ECHEC    {source} -> {cible} : `entity_id` NULLABLE a la source")
            print("             `MATCH SIMPLE` satisfait une cle composite SANS verification")
            print("             des qu'une de ses colonnes est nulle. Defaut `T8-1` transpose.")
            echecs += 1
        for colonne in cols.split(","):
            if colonne != "entity_id" and f"{source}.{colonne}" in nullables_en_base:
                portees_nullables.append(f"{source}.{colonne} -> {cible}")
    print(
        f"    ok       les {len(composites)} cles composites ont `entity_id` NOT NULL a la source"
    )
    if portees_nullables:
        print(
            f"    info     {len(portees_nullables)} colonne(s) de PORTEE "
            f"nullable, et c'est legitime :"
        )
        for element in portees_nullables:
            print(f"               {element} — absente pour un `DSM`/`ESM` (§8.4), imposee par")
            print("               une contrainte de verification pour `BOOSTER`/`OFFICE_MANAGER`")

    # ------------------------------------------------------------------
    #  5. La cible de chaque cle composite expose le couple `(id, entity_id)`
    # ------------------------------------------------------------------
    code, sortie = sql(
        compose,
        env,
        "SELECT DISTINCT c.conrelid::regclass::text FROM pg_constraint c "
        "WHERE c.contype IN ('u','p') AND array_length(c.conkey,1)=2 "
        "AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.conrelid "
        "  AND a.attnum=ANY(c.conkey) AND a.attname='id') "
        "AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.conrelid "
        "  AND a.attnum=ANY(c.conkey) AND a.attname='entity_id')",
    )
    avec_couple = {ligne[0] for ligne in lignes(sortie)}
    cibles = sorted({cible for _n, _s, cible, _c, _r in composites})
    print()
    print(
        f"    info     {len(avec_couple)} table(s) exposent le couple unique "
        f"`(id, entity_id)` du §25.3"
    )
    print(f"               {', '.join(sorted(avec_couple)) or 'aucune'}")
    for cible in cibles:
        if cible not in avec_couple:
            print(
                f"    ECHEC    {cible} est cible d'une cle composite sans exposer le couple unique"
            )
            echecs += 1
    if not [c for c in cibles if c not in avec_couple]:
        print(f"    ok       les {len(cibles)} cibles de cle composite exposent toutes le couple")
    sans_couple = sorted(set(locales) - avec_couple)
    print(
        f"    info     {len(sans_couple)} table(s) locales SANS le couple, "
        f"et ce n'est pas un manque :"
    )
    print("               `id` etant cle primaire, un couple `(id, entity_id)` ne peut JAMAIS")
    print("               rien refuser — aucun test ne pourrait le faire echouer. Il n'existe")
    print("               que pour etre REFERENCABLE. Le controle l'exige des qu'une table")
    print("               devient cible d'une cle composite, ce qui rend la regle vivante.")

    # ------------------------------------------------------------------
    #  6. Ce qui n'est PAS couvert, nomme visiblement (§7.20)
    # ------------------------------------------------------------------
    print()
    print(
        f"    info     {len(vers_globale)} cle(s) vers une table GLOBALE — une cle composite y est"
    )
    print("               impossible par construction, la cible ne portant pas d'`entity_id`")
    for _nom, source, cible, cols in vers_globale:
        print(f"               {source}.{cols} -> {cible}")

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print(
        f"  --> {len(locales)} tables locales, {len(composites)} cles composites, "
        f"0 reference nue, 0 cle simple entre deux tables locales"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
