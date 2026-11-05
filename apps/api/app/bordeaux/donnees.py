"""Lecture et normalisation de la population de la Beta Bordeaux.

Le fichier Excel est une source d'exploitation, pas une fonctionnalite du
produit. Ce module ne cree donc aucune route d'import : il lit le classeur
fourni uniquement depuis la commande de provisionnement hors ligne.

La lecture XLSX repose sur le format Open Packaging (ZIP + XML) et la
bibliotheque standard. L'API n'embarque ainsi ni moteur Excel ni dependance
d'import dans son processus web.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import pathlib
import posixpath
import re
import unicodedata
import zipfile
from collections import defaultdict
from importlib import resources
from typing import TypedDict, cast
from xml.etree import ElementTree

CODE_ENTITE_BORDEAUX = "BORDEAUX"
NOM_ENTITE_BORDEAUX = "eXalt Bordeaux"
DOMAINE_EXALT = "exalt-company.com"
FEUILLE_SOURCE = "export-filtre"
TAILLE_MAXIMALE_XML = 20 * 1024 * 1024

CERCLES_DE_BORDEAUX: tuple[tuple[str, str, str], ...] = (
    ("PRODUIT", "Produit", "produit"),
    ("PROJET", "Projet", "projet"),
    ("DESIGN", "Design", "design"),
    ("IT", "IT", "it"),
    ("FORGE", "Forge", "forge"),
    ("SHIELD", "Shield", "shield"),
    ("DATA", "Data", "data"),
)


class _DefinitionDeBureau(TypedDict):
    code: str
    nom: str


class _ConfigurationBordeaux(TypedDict):
    bureaux: list[_DefinitionDeBureau]


def _charger_la_configuration_bordeaux() -> _ConfigurationBordeaux:
    """Lire les donnees de demonstration sans les transformer en logique produit.

    Les codes des bureaux restent des donnees configurables. La ressource vit
    dans le paquet pour etre presente dans l'image d'execution, mais aucun
    module Python generique ne branche son comportement sur leur valeur.
    """
    contenu = resources.files("app.bordeaux").joinpath("configuration.json").read_text("utf-8")
    return cast(_ConfigurationBordeaux, json.loads(contenu))


_CONFIGURATION_BORDEAUX = _charger_la_configuration_bordeaux()
BUREAUX_DE_BORDEAUX: tuple[tuple[str, str], ...] = tuple(
    (bureau["code"], bureau["nom"]) for bureau in _CONFIGURATION_BORDEAUX["bureaux"]
)
_CODES_DE_BUREAU_PAR_NOM = {nom: code for code, nom in BUREAUX_DE_BORDEAUX}
_CODE_BUREAU_GAMING = _CODES_DE_BUREAU_PAR_NOM["Bureau du Gaming"]
_CODE_BUREAU_SPORTS = _CODES_DE_BUREAU_PAR_NOM["Bureau des sports"]
_CODE_BUREAU_EXALTEES = _CODES_DE_BUREAU_PAR_NOM["Bureau des eXaltées"]

_CERCLES_SOURCE: dict[str, str] = {
    "Cercle PRODUIT": "PRODUIT",
    "Cercle CHANGE": "PROJET",
    "Cercle PROJET": "PROJET",
    "Cercle DESIGN": "DESIGN",
    "Cercle IT": "IT",
    "Cercle FORGE": "FORGE",
    "Cercle SHIELD": "SHIELD",
    "Cercle DATA": "DATA",
}

_TYPES_SOURCE = {
    "Consultant",
    "Direction salarié",
    "Employee Sucess Manager",
    "Recrutement",
    "Digital Sales Manager",
}

_STATUTS_SOURCE: dict[str, str] = {
    "Mission": "mission",
    "Intercontrat": "intercontract",
}

_ESM_AJOUTES = frozenset({"lea.jouve-berniolles@exalt-company.com"})

# Les responsabilites de securite existantes restent les seules a porter des
# droits. Ces libelles servent a construire le decor Bordeaux et l'ecran de
# presentation ; ils ne sont jamais convertis en role technique.
RESPONSABILITES_DE_PRESENTATION: dict[str, tuple[str, ...]] = {
    "maeva.adisson@exalt-company.com": ("Booster Produit",),
    "pauline.jaillot@exalt-company.com": ("Responsable mentorat Produit",),
    "mathilde.sampre@exalt-company.com": (f"Responsable {_CODE_BUREAU_EXALTEES}",),
    "adeline.mory@exalt-company.com": ("Responsable mentorat Design",),
    "melissa.chakhari@exalt-company.com": ("Booster Design",),
    "celia.alves-audibert@exalt-company.com": (f"Responsable {_CODE_BUREAU_EXALTEES}",),
    "romain.boussot@exalt-company.com": ("Booster Projet",),
    "charles.vallais@exalt-company.com": (f"Responsable {_CODE_BUREAU_GAMING}",),
    "mariam.traore@exalt-company.com": ("Booster Think Agent",),
    "hadrien.berling@exalt-company.com": ("Booster Data",),
    "jonathan.dupau@exalt-company.com": (f"Responsable {_CODE_BUREAU_SPORTS}",),
    "romain.hoarau@exalt-company.com": (
        "Booster Shield",
        f"Responsable {_CODE_BUREAU_GAMING}",
    ),
    "mathieu.lagalle@exalt-company.com": ("Booster Forge",),
    "mohammed-sadeq.ben-thaier@exalt-company.com": ("Booster IT",),
    "lea.jouve-berniolles@exalt-company.com": ("ESM",),
    "tess.gourlet@exalt-company.com": ("ESM",),
}

BOOSTERS_PAR_CERCLE: dict[str, str] = {
    "PRODUIT": "maeva.adisson@exalt-company.com",
    "DESIGN": "melissa.chakhari@exalt-company.com",
    "PROJET": "romain.boussot@exalt-company.com",
    "DATA": "hadrien.berling@exalt-company.com",
    "SHIELD": "romain.hoarau@exalt-company.com",
    "FORGE": "mathieu.lagalle@exalt-company.com",
    "IT": "mohammed-sadeq.ben-thaier@exalt-company.com",
}

RESPONSABLES_PAR_BUREAU: dict[str, tuple[str, ...]] = {
    _CODE_BUREAU_GAMING: (
        "charles.vallais@exalt-company.com",
        "romain.hoarau@exalt-company.com",
    ),
    _CODE_BUREAU_SPORTS: ("jonathan.dupau@exalt-company.com",),
    _CODE_BUREAU_EXALTEES: (
        "mathilde.sampre@exalt-company.com",
        "celia.alves-audibert@exalt-company.com",
    ),
}

DESCRIPTION_CLOTURE_DES_BUREAUX = (
    "Clôture des bureaux "
    f"{_CODE_BUREAU_EXALTEES} • {_CODE_BUREAU_GAMING} • {_CODE_BUREAU_SPORTS} — "
    "ensemble, soyons solidaires."
)


class DonneesBordeauxInvalides(ValueError):
    """La source Bordeaux ne peut pas etre provisionnee sans intervention."""


@dataclasses.dataclass(frozen=True, slots=True)
class EmployeBordeaux:
    prenom: str
    nom: str
    courriel: str
    date_d_arrivee: dt.date | None
    type_source: str
    categorie_professionnelle: str
    statut_professionnel: str
    cercle: str | None
    responsabilites: tuple[str, ...]
    est_dsm: bool
    est_esm: bool


@dataclasses.dataclass(frozen=True, slots=True)
class PopulationBordeaux:
    employes: tuple[EmployeBordeaux, ...]
    avertissements: tuple[str, ...]


def _sans_accents(valeur: str) -> str:
    decomposee = unicodedata.normalize("NFKD", valeur)
    return "".join(c for c in decomposee if not unicodedata.combining(c))


def _segment_de_courriel(valeur: str) -> str:
    valeur = _sans_accents(valeur).lower().strip()
    valeur = valeur.replace("'", "").replace("\u2019", "")
    valeur = re.sub(r"\s+", "-", valeur)
    valeur = re.sub(r"[^a-z0-9-]", "-", valeur)
    valeur = re.sub(r"-+", "-", valeur).strip("-")
    if not valeur:
        raise DonneesBordeauxInvalides("un nom ou prenom ne permet pas de construire un courriel")
    return valeur


def construire_le_courriel(prenom: str, nom: str) -> str:
    """Construire l'adresse eXalt validee par Jonathan pour la Beta."""
    return f"{_segment_de_courriel(prenom)}.{_segment_de_courriel(nom)}@{DOMAINE_EXALT}"


def _date_excel(valeur: object) -> dt.date | None:
    if valeur is None or valeur == "":
        return None
    if isinstance(valeur, dt.datetime):
        return valeur.date()
    if isinstance(valeur, dt.date):
        return valeur
    try:
        numero = int(float(str(valeur)))
    except ValueError as erreur:
        raise DonneesBordeauxInvalides(f"date Excel illisible : {valeur!r}") from erreur
    return dt.date(1899, 12, 30) + dt.timedelta(days=numero)


def _nom_xml(cle: str) -> str:
    return f"{{http://schemas.openxmlformats.org/spreadsheetml/2006/main}}{cle}"


def _xml_sans_entite(archive: zipfile.ZipFile, chemin: str) -> ElementTree.Element:
    """Lire un petit XML Office apres avoir exclu DTD et entites externes.

    La source vient d'un utilisateur habilite, mais elle reste une entree. La
    borne decomprimee evite une bombe ZIP et le refus explicite des declarations
    retire la surface XXE avant l'analyse par la bibliotheque standard.
    """
    information = archive.getinfo(chemin)
    if information.file_size > TAILLE_MAXIMALE_XML:
        raise DonneesBordeauxInvalides(f"partie XML trop volumineuse : {chemin}")
    contenu = archive.read(chemin)
    if b"<!DOCTYPE" in contenu.upper() or b"<!ENTITY" in contenu.upper():
        raise DonneesBordeauxInvalides(f"declaration XML interdite : {chemin}")
    return ElementTree.fromstring(contenu)  # noqa: S314 -- DTD/ENTITY refuses ci-dessus


def _colonne_de(reference: str) -> int:
    lettres = re.match(r"[A-Z]+", reference)
    if lettres is None:
        raise DonneesBordeauxInvalides(f"reference de cellule illisible : {reference!r}")
    resultat = 0
    for lettre in lettres.group(0):
        resultat = resultat * 26 + ord(lettre) - ord("A") + 1
    return resultat - 1


def _chaines_partagees(archive: zipfile.ZipFile) -> list[str]:
    try:
        racine = _xml_sans_entite(archive, "xl/sharedStrings.xml")
    except KeyError:
        return []
    chaines: list[str] = []
    for element in racine.findall(_nom_xml("si")):
        chaines.append("".join(t.text or "" for t in element.iter(_nom_xml("t"))))
    return chaines


def _chemin_de_la_feuille(archive: zipfile.ZipFile, nom: str) -> str:
    racine = _xml_sans_entite(archive, "xl/workbook.xml")
    relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    identifiant = next(
        (
            feuille.attrib[relation]
            for feuille in racine.iter(_nom_xml("sheet"))
            if feuille.attrib.get("name") == nom
        ),
        None,
    )
    if identifiant is None:
        raise DonneesBordeauxInvalides(f"feuille absente du classeur : {nom}")

    relations = _xml_sans_entite(archive, "xl/_rels/workbook.xml.rels")
    cible = next(
        (
            element.attrib["Target"]
            for element in relations
            if element.attrib.get("Id") == identifiant
        ),
        None,
    )
    if cible is None:
        raise DonneesBordeauxInvalides(f"relation de feuille absente : {nom}")
    return posixpath.normpath(posixpath.join("xl", cible.lstrip("/")))


def _valeur_de_cellule(cellule: ElementTree.Element, chaines: list[str]) -> object:
    type_cellule = cellule.attrib.get("t")
    valeur = cellule.find(_nom_xml("v"))
    if type_cellule == "inlineStr":
        texte = cellule.find(f"{_nom_xml('is')}/{_nom_xml('t')}")
        return None if texte is None else texte.text
    if valeur is None or valeur.text is None:
        return None
    if type_cellule == "s":
        return chaines[int(valeur.text)]
    if type_cellule == "str":
        return valeur.text
    try:
        return float(valeur.text)
    except ValueError:
        return valeur.text


def _lire_les_lignes_xlsx(chemin: pathlib.Path, feuille: str) -> list[list[object]]:
    with zipfile.ZipFile(chemin) as archive:
        chaines = _chaines_partagees(archive)
        racine = _xml_sans_entite(archive, _chemin_de_la_feuille(archive, feuille))
    lignes: list[list[object]] = []
    for ligne in racine.iter(_nom_xml("row")):
        cellules: dict[int, object] = {}
        for cellule in ligne.findall(_nom_xml("c")):
            cellules[_colonne_de(cellule.attrib["r"])] = _valeur_de_cellule(cellule, chaines)
        if cellules:
            lignes.append([cellules.get(i) for i in range(max(cellules) + 1)])
    return lignes


def _enregistrements(chemin: pathlib.Path) -> list[dict[str, object]]:
    lignes = _lire_les_lignes_xlsx(chemin, FEUILLE_SOURCE)
    if not lignes:
        raise DonneesBordeauxInvalides("la feuille source est vide")
    entetes = [str(v) if v is not None else "" for v in lignes[0]]
    attendues = ("Arrivée", "Nom", "Prénom", "Type", "Statut", "Cercle", "Entité")
    if tuple(entetes) != attendues:
        raise DonneesBordeauxInvalides(
            f"entetes inattendues : {tuple(entetes)!r}, attendu {attendues!r}"
        )
    return [dict(zip(entetes, ligne, strict=False)) for ligne in lignes[1:]]


def _consolider(
    enregistrements: list[dict[str, object]], *, verifier_responsabilites: bool = True
) -> PopulationBordeaux:
    par_courriel: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for ligne in enregistrements:
        prenom = str(ligne.get("Prénom") or "").strip()
        nom = str(ligne.get("Nom") or "").strip()
        par_courriel[construire_le_courriel(prenom, nom)].append(ligne)

    avertissements: list[str] = []
    employes: list[EmployeBordeaux] = []
    for courriel, lignes in sorted(par_courriel.items()):
        reference = lignes[0]
        identite = (str(reference["Prénom"]).strip(), str(reference["Nom"]).strip())
        champs_stables = ("Prénom", "Nom", "Type", "Statut", "Cercle", "Entité")
        for ligne in lignes[1:]:
            divergences = [
                champ for champ in champs_stables if ligne.get(champ) != reference.get(champ)
            ]
            if divergences:
                raise DonneesBordeauxInvalides(
                    f"doublon contradictoire pour {courriel}, champs : {', '.join(divergences)}"
                )
        dates = {_date_excel(ligne.get("Arrivée")) for ligne in lignes}
        date_d_arrivee = dates.pop() if len(dates) == 1 else None
        if len(lignes) > 1:
            detail = "date conservee" if date_d_arrivee is not None else "date laissee vide"
            avertissements.append(f"{courriel} : {len(lignes)} lignes fusionnees, {detail}")

        type_source = str(reference["Type"])
        statut_source = str(reference["Statut"])
        entite_source = str(reference["Entité"])
        if type_source not in _TYPES_SOURCE:
            raise DonneesBordeauxInvalides(f"type inconnu pour {courriel} : {type_source!r}")
        if statut_source not in _STATUTS_SOURCE:
            raise DonneesBordeauxInvalides(f"statut inconnu pour {courriel} : {statut_source!r}")
        if entite_source != "EXALT Bordeaux":
            raise DonneesBordeauxInvalides(f"entite inattendue pour {courriel} : {entite_source!r}")

        cercle_source = reference.get("Cercle")
        cercle = _CERCLES_SOURCE.get(str(cercle_source)) if cercle_source is not None else None
        employes.append(
            EmployeBordeaux(
                prenom=identite[0],
                nom=identite[1],
                courriel=courriel,
                date_d_arrivee=date_d_arrivee,
                type_source=type_source,
                categorie_professionnelle=(
                    "dg" if type_source == "Direction salarié" else "consultant"
                ),
                statut_professionnel=_STATUTS_SOURCE[statut_source],
                cercle=cercle,
                responsabilites=RESPONSABILITES_DE_PRESENTATION.get(courriel, ()),
                est_dsm=type_source == "Digital Sales Manager",
                est_esm=(type_source == "Employee Sucess Manager" or courriel in _ESM_AJOUTES),
            )
        )

    if verifier_responsabilites:
        courriels_attendus = set(RESPONSABILITES_DE_PRESENTATION)
        courriels_trouves = {employe.courriel for employe in employes}
        absents = sorted(courriels_attendus - courriels_trouves)
        if absents:
            raise DonneesBordeauxInvalides(
                "responsabilites fournies pour des personnes absentes : " + ", ".join(absents)
            )
    return PopulationBordeaux(tuple(employes), tuple(avertissements))


def lire_la_population_bordeaux(chemin: str | pathlib.Path) -> PopulationBordeaux:
    source = pathlib.Path(chemin)
    if not source.is_file():
        raise DonneesBordeauxInvalides(f"classeur introuvable : {source}")
    return _consolider(_enregistrements(source))
