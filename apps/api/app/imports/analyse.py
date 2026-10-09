"""Normaliser les e-mails, detecter les doublons, bloquer les lignes sans e-mail.

LOT 9, sous-etape `T7`, story `MVP-L09-US004` (2/2).

LE PERIMETRE DE CETTE SOUS-ETAPE, ARBITRE PAR JONATHAN AVANT TOUT CODE

  Le LOT 0 a produit un referentiel bien plus large que le seul e-mail —
  `docs/architecture/donnees/codes-erreurs-import.md` nomme 68 codes sur 12
  domaines (date, metier, mission/client, cercle, DSM, responsabilites...).
  Rien dans le decoupage valide du lot (`fiche-lot-9.md`) ne nomme de
  sous-etape pour CES AUTRES domaines : `T8` ne porte que les clients, `T9`
  importe transactionnellement. Pose a Jonathan avant d'ecrire une ligne :
  **T7 reste a la taille que son titre annonce** — e-mail et doublons de
  personne, rien d'autre. Les autres regles (date, metier, cercle, DSM...)
  ne sont PAS previsualisees ici ; elles ne seront verifiees qu'au moment de
  l'import reel (`T9`), en reutilisant les regles deja posees par la
  creation d'un collaborateur (`T2`, `app.people.creation`). Un futur agent
  qui lirait « previsualisation complete » au pied de la lettre devrait
  savoir que « complete » est borne a ce perimetre choisi, pas aux 68 codes.

CE QUE CE MODULE COUVRE, CODE PAR CODE (`codes-erreurs-import.md` §3.1, §5)

  - `E-EMAIL-001` : e-mail absent — bloquant, REJETE, aucune autre verification
    d'e-mail n'a de sens sur une valeur vide ;
  - `E-EMAIL-002` : format implausible — meme regle que la contrainte
    `email_normalise_plausible` deja posee en base (LOT 2) : pas d'espace,
    une arobase ailleurs qu'en premiere position. Jamais une regex plus
    stricte qui rejetterait en PREVISUALISATION ce que la base accepterait
    a l'ECRITURE (§7.37 : une meme valeur doit franchir la meme frontiere) ;
  - `E-EMAIL-003` : domaine non autorise — meme table, `allowed_email_domain`,
    que `app.auth.services._domaine_est_autorise`, mais une copie PROPRE a ce
    module (§7.27 : un partage a travers un soulignement serait un couplage) ;
  - `E-EMAIL-004` : doublon technique DANS LE FICHIER — `DEC-435` : la
    PREMIERE occurrence (ordre de `row_number`) est retenue, les suivantes
    sont seules rejetees ;
  - `D-PERSONNE-001` : l'e-mail correspond a une personne EXISTANTE en base
    avec au moins une appartenance `active` ;
  - `D-PERSONNE-002` : l'e-mail correspond a une personne EXISTANTE en base
    dont la SEULE appartenance connue est `archived` (confirmation explicite
    de reactivation, `T9`) ;
  - `D-PERSONNE-003` : homonymie EXACTE (nom et prenom, apres nettoyage et
    casse indifferente) entre deux lignes du MEME fichier portant des
    e-mails DIFFERENTS — verifiee UNIQUEMENT dans le fichier, jamais contre
    la base entiere (non demontre par le jeu d'exemple du LOT 0, qui ne
    montre que le cas intra-fichier ; une homonymie contre la base reste un
    residu non couvert, a instruire si le besoin se confirme).

UNE LIGNE PEUT PORTER PLUSIEURS PROBLEMES A LA FOIS, ET L'ETAT SUIT UNE
PRIORITE STRICTE

  Le jeu d'exemple du LOT 0 le montre explicitement : la ligne `Golf` porte a
  la fois `D-CLIENT-001` (hors perimetre ici) ET `D-PERSONNE-003`. L'etat
  final d'une ligne (modele §19.2) suit donc une priorite stricte sur les
  PROBLEMES EFFECTIVEMENT DETECTES par ce module : `E` (rejete) prevaut sur
  `D` (a confirmer) prevaut sur `W` (avertissement, aucun ici) prevaut sur
  rien (valide). Une ligne sans aucun probleme ICI reste `valid` — ce qui ne
  garantit PAS qu'elle passera les verifications non construites de `T9`.

POURQUOI LA DETECTION N'EST PAS PAYEE LIGNE PAR LIGNE

  Les deux requetes qui interrogent la base (domaine autorise, personne
  existante) sont posees UNE FOIS pour tout le lot, jamais une fois par
  ligne — meme discipline que `T2` du LOT 5 (« la liste ne paie pas une
  requete par ligne »). La deuxieme utilise `= ANY(:emails)` sur la liste
  des adresses normalisees CANDIDATES du lot entier.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.imports.correspondance import valeur_logique
from app.imports.modeles import EtatLigneImport, EtatLotImport
from app.people.modeles import normaliser_email

#  Les trois niveaux de `codes-erreurs-import.md` §1.1 — jamais une
#  enumeration inventee, ce sont les lettres litterales du document.
NIVEAU_ERREUR: Final = "E"
NIVEAU_DECISION: Final = "D"
NIVEAU_AVERTISSEMENT: Final = "W"

CODE_EMAIL_ABSENT: Final = "E-EMAIL-001"
CODE_EMAIL_FORMAT_INVALIDE: Final = "E-EMAIL-002"
CODE_EMAIL_DOMAINE_REFUSE: Final = "E-EMAIL-003"
CODE_EMAIL_DOUBLON_FICHIER: Final = "E-EMAIL-004"
CODE_PERSONNE_PROFIL_ACTIF: Final = "D-PERSONNE-001"
CODE_PERSONNE_PROFIL_ARCHIVE: Final = "D-PERSONNE-002"
CODE_PERSONNE_HOMONYME: Final = "D-PERSONNE-003"

#  Messages et resolutions REPRIS TELS QUELS de `codes-erreurs-import.md`,
#  §3.1 et §5 — jamais reformules, pour que le document et le code ne
#  divergent pas en silence (meme discipline que `app.content.liens` pour
#  les codes de refus d'URL).
_TEXTES: Final[dict[str, tuple[str, str]]] = {
    CODE_EMAIL_ABSENT: (
        "L'adresse e-mail professionnelle est absente. La ligne ne peut pas être importée.",
        "Renseigner l'adresse officielle. Règle non contournable : cahier §12.2.",
    ),
    CODE_EMAIL_FORMAT_INVALIDE: (
        "L'adresse e-mail n'a pas un format valide.",
        "Corriger l'adresse.",
    ),
    CODE_EMAIL_DOMAINE_REFUSE: (
        "Le domaine de l'adresse e-mail n'est pas autorisé.",
        "Utiliser une adresse d'un domaine autorisé, ou faire ajouter le domaine "
        "par le super-administrateur.",
    ),
    CODE_EMAIL_DOUBLON_FICHIER: (
        "Cette adresse e-mail apparaît sur plusieurs lignes du fichier.",
        "Conserver une seule ligne par personne. Une personne n'a qu'une "
        "appartenance principale active.",
    ),
    CODE_PERSONNE_PROFIL_ACTIF: (
        "Cette adresse e-mail correspond à un profil actif existant.",
        "Mettre à jour le profil existant, ou rejeter la ligne.",
    ),
    CODE_PERSONNE_PROFIL_ARCHIVE: (
        "Cette adresse e-mail correspond à un profil archivé.",
        "Confirmation explicite requise pour réactiver, sinon rejet.",
    ),
    CODE_PERSONNE_HOMONYME: (
        "Une autre personne porte les mêmes nom et prénom, avec une adresse différente.",
        "Confirmer qu'il s'agit de deux personnes distinctes, ou corriger.",
    ),
}

_NIVEAU_DU_CODE: Final[dict[str, str]] = {
    CODE_EMAIL_ABSENT: NIVEAU_ERREUR,
    CODE_EMAIL_FORMAT_INVALIDE: NIVEAU_ERREUR,
    CODE_EMAIL_DOMAINE_REFUSE: NIVEAU_ERREUR,
    CODE_EMAIL_DOUBLON_FICHIER: NIVEAU_ERREUR,
    CODE_PERSONNE_PROFIL_ACTIF: NIVEAU_DECISION,
    CODE_PERSONNE_PROFIL_ARCHIVE: NIVEAU_DECISION,
    CODE_PERSONNE_HOMONYME: NIVEAU_DECISION,
}

#  Priorite STRICTE d'un niveau vers l'etat de ligne du modele §19.2 — la
#  PREMIERE correspondance dans cet ordre l'emporte.
_PRIORITE_DES_NIVEAUX: Final[tuple[tuple[str, str], ...]] = (
    (NIVEAU_ERREUR, EtatLigneImport.REJECTED.value),
    (NIVEAU_DECISION, EtatLigneImport.NEEDS_DECISION.value),
    (NIVEAU_AVERTISSEMENT, EtatLigneImport.WARNING.value),
)


@dataclasses.dataclass(frozen=True, slots=True)
class Probleme:
    """Un probleme detecte sur une ligne — `import_row_issue`, modele §19.3."""

    code: str
    champ: str | None
    valeur_normalisee_sure: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class PrevisualisationProduite:
    """Ce que l'analyse de `T7` a produit — transition `analyzing -> preview_ready`."""

    state: str
    version: int
    total_rows: int
    valid_rows: int
    warning_rows: int
    needs_decision_rows: int
    rejected_rows: int


def _email_plausible(adresse_normalisee: str) -> bool:
    """Meme regle que la contrainte `email_normalise_plausible` (LOT 2, `T2`).

    Reprise a l'identique pour que ce que la previsualisation accepte, la
    base l'accepte aussi a l'ecriture (`T9`) — §7.37 : une meme valeur doit
    franchir la meme frontiere de la meme facon.
    """
    if any(caractere.isspace() for caractere in adresse_normalisee):
        return False
    position = adresse_normalisee.find("@")
    return position > 0


def _domaine_de(adresse_normalisee: str) -> str:
    """Partie droite de l'arobase — copie PROPRE de `app.auth.services._domaine_de`."""
    _, separateur, domaine = adresse_normalisee.partition("@")
    return domaine if separateur else ""


_DOMAINE_AUTORISE: Final = text(
    """
    SELECT 1 FROM allowed_email_domain
     WHERE domain = :domaine AND active IS TRUE
       AND period @> :instant_periode
       AND (entity_id IS NULL OR entity_id = :entite)
     LIMIT 1
    """
)


def _domaine_est_autorise(
    connexion: Connection, *, domaine: str, entite: uuid.UUID, instant: dt.datetime
) -> bool:
    """Le domaine autorise-t-il cette entite, a cet instant — §5.4, copie PROPRE.

    Meme requete que `app.auth.services._domaine_est_autorise` : active,
    periode courante, domaine global ou propre a l'entite. Jamais importee
    (§7.27) — les deux domaines (authentification, imports) n'ont aucun
    rapport, et coupler les deux modules sur une regle identique aujourd'hui
    les ferait diverger en silence demain.
    """
    if not domaine:
        return False
    trouve = connexion.execute(
        _DOMAINE_AUTORISE,
        {"domaine": domaine, "instant_periode": instant, "entite": entite},
    ).scalar_one_or_none()
    return trouve is not None


_PERSONNES_EXISTANTES: Final = text(
    """
    SELECT p.email_normalized AS email, em.membership_state AS etat
      FROM person p
      JOIN entity_membership em ON em.person_id = p.id
     WHERE p.email_normalized = ANY(:emails)
    """
)


def _etats_des_personnes_existantes(
    connexion: Connection, *, emails: list[str]
) -> dict[str, set[str]]:
    """Pour chaque e-mail CANDIDAT, l'ensemble des etats d'appartenance connus.

    **UNE SEULE REQUETE POUR TOUT LE LOT**, jamais une par ligne — voir
    l'en-tete du module. `= ANY('{}')` sur une liste vide ne serait pas
    fautif mais n'a aucune raison d'etre pose (meme garde que
    `people.trombinoscome` sur une page vide).
    """
    if not emails:
        return {}
    resultat: dict[str, set[str]] = {}
    for ligne in connexion.execute(_PERSONNES_EXISTANTES, {"emails": emails}):
        resultat.setdefault(ligne.email, set()).add(ligne.etat)
    return resultat


@dataclasses.dataclass(frozen=True, slots=True)
class _LigneBrute:
    identifiant: uuid.UUID
    row_number: int
    raw_data: dict[str, object]


_LIGNES_DU_LOT: Final = text(
    """
    SELECT id, row_number, raw_data FROM import_row
     WHERE import_batch_id = :lot
     ORDER BY row_number
    """
)

_INSERER_UN_PROBLEME: Final = text(
    """
    INSERT INTO import_row_issue
      (entity_id, import_row_id, code, field, message, level,
       normalized_value_safe, resolution)
    VALUES
      (:entite, :ligne, :code, :champ, :message, :niveau,
       :valeur_normalisee_sure, :resolution)
    """
)

_FIXER_LA_LIGNE: Final = text(
    """
    UPDATE import_row
       SET state = :etat,
           normalized_data = CAST(:donnees_normalisees AS jsonb),
           error_codes = CAST(:codes AS jsonb),
           updated_at = :instant
     WHERE id = :ligne
    """
)

#  **QUATRE COMPTEURS DANS LE MEME `UPDATE` QUE L'ETAT** — §7.35 : ils ne
#  peuvent pas diverger par cette API.
_FIXER_LE_RESULTAT_DE_LA_PREVISUALISATION: Final = text(
    """
    UPDATE import_batch
       SET state = :etat_final,
           valid_rows = :valides,
           warning_rows = :avertissements,
           needs_decision_rows = :a_confirmer,
           rejected_rows = :rejetees,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :lot AND entity_id = :entite
    RETURNING version, state
    """
)


def _etat_depuis_les_problemes(problemes: list[Probleme]) -> str:
    niveaux = {_NIVEAU_DU_CODE[p.code] for p in problemes}
    for niveau, etat in _PRIORITE_DES_NIVEAUX:
        if niveau in niveaux:
            return etat
    return EtatLigneImport.VALID.value


def analyser_le_lot(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lot: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> PrevisualisationProduite:
    """Normaliser les e-mails, detecter les doublons — `analyzing -> preview_ready`.

    Appelee par `app.imports.depot.deposer_un_csv`, DANS LA MEME transaction
    que le depot : l'import reste synchrone (`DEC-462`), et `T6`/`T7`
    servent ensemble les DEUX premieres transitions du diagramme §24.4 en un
    seul appel HTTP.
    """
    lignes = [
        _LigneBrute(identifiant=ligne.id, row_number=ligne.row_number, raw_data=ligne.raw_data)
        for ligne in connexion.execute(_LIGNES_DU_LOT, {"lot": lot})
    ]

    problemes: dict[uuid.UUID, list[Probleme]] = {ligne.identifiant: [] for ligne in lignes}
    emails: dict[uuid.UUID, str | None] = {}

    #  1. E-EMAIL-001/002/003 — independamment les unes des autres, une seule
    #     par ligne a ce stade : une adresse invalide ou hors domaine n'a pas
    #     de forme normalisee exploitable pour les etapes suivantes.
    for ligne in lignes:
        brut = valeur_logique(ligne.raw_data, "F01")
        if brut is None:
            problemes[ligne.identifiant].append(Probleme(CODE_EMAIL_ABSENT, "F01"))
            emails[ligne.identifiant] = None
            continue
        normalise = normaliser_email(brut)
        if not _email_plausible(normalise):
            problemes[ligne.identifiant].append(Probleme(CODE_EMAIL_FORMAT_INVALIDE, "F01"))
            emails[ligne.identifiant] = None
            continue
        if not _domaine_est_autorise(
            connexion, domaine=_domaine_de(normalise), entite=entite, instant=instant
        ):
            problemes[ligne.identifiant].append(Probleme(CODE_EMAIL_DOMAINE_REFUSE, "F01"))
            emails[ligne.identifiant] = None
            continue
        emails[ligne.identifiant] = normalise

    #  2. E-EMAIL-004 — DEC-435 : la PREMIERE occurrence (ordre de
    #     `row_number`, deja l'ordre de `lignes`) est retenue.
    vues: dict[str, uuid.UUID] = {}
    for ligne in lignes:
        candidat = emails.get(ligne.identifiant)
        if candidat is None:
            continue
        if candidat in vues:
            problemes[ligne.identifiant].append(
                Probleme(CODE_EMAIL_DOUBLON_FICHIER, "F01", candidat)
            )
            emails[ligne.identifiant] = None
        else:
            vues[candidat] = ligne.identifiant

    #  3. D-PERSONNE-001/002 — UNE SEULE requete pour tout le lot.
    candidats = sorted({e for e in emails.values() if e is not None})
    etats_connus = _etats_des_personnes_existantes(connexion, emails=candidats)
    for ligne in lignes:
        email_existant = emails.get(ligne.identifiant)
        if email_existant is None:
            continue
        etats = etats_connus.get(email_existant)
        if not etats:
            continue
        if "active" in etats:
            problemes[ligne.identifiant].append(
                Probleme(CODE_PERSONNE_PROFIL_ACTIF, "F01", email_existant)
            )
        elif "archived" in etats:
            problemes[ligne.identifiant].append(
                Probleme(CODE_PERSONNE_PROFIL_ARCHIVE, "F01", email_existant)
            )
        #  `future` seul ou `departed` seul : aucun des deux codes ne les
        #  nomme (`codes-erreurs-import.md` §5) — residu non invente (§6.5).

    #  4. D-PERSONNE-003 — homonymie DANS LE FICHIER seulement (§ en-tete).
    groupes: dict[tuple[str, str], list[uuid.UUID]] = {}
    for ligne in lignes:
        nom = valeur_logique(ligne.raw_data, "F02")
        prenom = valeur_logique(ligne.raw_data, "F03")
        if nom is None or prenom is None:
            continue
        cle = (nom.casefold(), prenom.casefold())
        groupes.setdefault(cle, []).append(ligne.identifiant)
    for identifiants in groupes.values():
        valides = [i for i in identifiants if emails.get(i) is not None]
        distincts = {emails[i] for i in valides}
        if len(valides) >= 2 and len(distincts) >= 2:
            for identifiant in valides:
                problemes[identifiant].append(Probleme(CODE_PERSONNE_HOMONYME, None))

    #  5. Ecriture — une ligne a la fois (meme idiome que
    #     `app.content.ecriture`), l'etat derive des problemes collectes.
    comptes = {
        EtatLigneImport.VALID.value: 0,
        EtatLigneImport.WARNING.value: 0,
        EtatLigneImport.NEEDS_DECISION.value: 0,
        EtatLigneImport.REJECTED.value: 0,
    }
    for ligne in lignes:
        liste = problemes[ligne.identifiant]
        etat = _etat_depuis_les_problemes(liste)
        comptes[etat] += 1
        for probleme in liste:
            message, resolution = _TEXTES[probleme.code]
            connexion.execute(
                _INSERER_UN_PROBLEME,
                {
                    "entite": entite,
                    "ligne": ligne.identifiant,
                    "code": probleme.code,
                    "champ": probleme.champ,
                    "message": message,
                    "niveau": _NIVEAU_DU_CODE[probleme.code],
                    "valeur_normalisee_sure": probleme.valeur_normalisee_sure,
                    "resolution": resolution,
                },
            )
        donnees_normalisees = (
            {"F01": emails[ligne.identifiant]} if emails.get(ligne.identifiant) else None
        )
        connexion.execute(
            _FIXER_LA_LIGNE,
            {
                "ligne": ligne.identifiant,
                "etat": etat,
                "donnees_normalisees": json.dumps(donnees_normalisees),
                "codes": json.dumps([p.code for p in liste]),
                "instant": instant,
            },
        )

    resultat = connexion.execute(
        _FIXER_LE_RESULTAT_DE_LA_PREVISUALISATION,
        {
            "etat_final": EtatLotImport.PREVIEW_READY.value,
            "valides": comptes[EtatLigneImport.VALID.value],
            "avertissements": comptes[EtatLigneImport.WARNING.value],
            "a_confirmer": comptes[EtatLigneImport.NEEDS_DECISION.value],
            "rejetees": comptes[EtatLigneImport.REJECTED.value],
            "instant": instant,
            "acteur": acteur,
            "lot": lot,
            "entite": entite,
        },
    ).one()

    return PrevisualisationProduite(
        state=resultat.state,
        version=resultat.version,
        total_rows=len(lignes),
        valid_rows=comptes[EtatLigneImport.VALID.value],
        warning_rows=comptes[EtatLigneImport.WARNING.value],
        needs_decision_rows=comptes[EtatLigneImport.NEEDS_DECISION.value],
        rejected_rows=comptes[EtatLigneImport.REJECTED.value],
    )
