"""Valider les champs organisationnels restants — LOT 9, `T9`, `MVP-L09-US006` (1/2).

CE QUE `T7` AVAIT EXPLICITEMENT RENVOYE ICI

  `app.imports.analyse` (en-tete, `T7`) : « Les autres regles (date, metier,
  cercle, DSM...) ne sont PAS previsualisees ici ; elles ne seront verifiees
  qu'au moment de l'import reel (`T9`), en reutilisant les regles deja posees
  par la creation d'un collaborateur (`T2`, `app.people.creation`). » Arbitrage
  de Jonathan du 09/10/2026, reconduit avant tout code de `T9` : TOUT le
  referentiel restant est construit dans cette seule sous-etape plutot que
  d'ouvrir un ecart sur ~40 codes — risque assume, une sous-etape nettement
  plus grosse que les precedentes.

  Ce module couvre `codes-erreurs-import.md` §3.2 a §3.12 et §4 (hormis les
  codes deja produits par `app.imports.analyse` — e-mail — et par
  `app.imports.clients` — `F13`) : identite (`F02`/`F03`), entite (`F05`),
  dates (`F06`/`F07`), categorie (`F08`), metier (`F11`), situation (`F12`),
  cercles (`F14`/`F15`), DSM (`F16`), responsabilites Framework (`F17`),
  roles techniques (`F18`), autorisation photo (`F19`).

APPELE DEUX FOIS, PAR CONCEPTION, ET C'EST VOULU

  `app.imports.analyse.analyser_le_lot` l'appelle une fois a la previsualisation
  (`preview_ready`, aucune ecriture). `app.imports.execution.lancer_l_import`
  l'appelle A NOUVEAU, A L'INSTANT REEL DE L'IMPORT, avant d'ecrire quoi que ce
  soit : un metier ou un cercle cree ENTRE LES DEUX passera desormais ; un
  cercle archive ENTRE LES DEUX ne passera plus plus. **Aucun resultat n'est mis
  en cache entre les deux appels** — un cache serait exactement la classe
  d'erreur du §7.21 (« un controle juste hier peut etre faux aujourd'hui »)
  appliquee a une donnee plutot qu'a un controle.

POURQUOI `D-METIER-001`/`D-CERCLE-001`/`D-BUREAU-001` NE PASSENT JAMAIS PAR
`import_decision`

  Le modele §19.4 FERME `TypeDeDecisionImport` a CINQ categories (`T1`), aucune
  ne nommant une creation de metier, de cercle ou de bureau — contrairement au
  rapprochement client, qui a DEUX categories dediees parce qu'un nom peut
  RESSEMBLER a plusieurs candidats (ambiguite reelle a trancher). Un code de
  metier, de cercle ou de bureau est une correspondance EXACTE ou rien : la
  decision attendue par `codes-erreurs-import.md` §5 (« creer l'entree au
  catalogue, ou corriger la valeur ») est TOUJOURS hors-ligne (un ecran
  d'administration, ou une correction du CSV suivie d'un nouveau depot) —
  jamais un geste de ce module. Ajouter un sixieme type exigerait une migration
  que le decoupage ne nomme pas pour `T9`. La ligne reste `needs_decision`
  jusqu'a ce que l'entree existe — la formule de reconciliation du §4 de
  `criteres-qualite-import.md` (`total = creations + mises_a_jour + rejets +
  en_attente_de_decision`) le PREVOIT explicitement : une ligne en attente
  apres un passage d'import n'est pas une anomalie.

CE QUE CE MODULE SIMPLIFIE, ET POURQUOI C'EST DIT

  `E-RESP-007` (plusieurs Boosters du meme cercle) n'est detecte qu'ENTRE LES
  LIGNES DU FICHIER. Un conflit entre une ligne du fichier et un Booster DEJA
  actif en base sur ce cercle (personne differente) n'est PAS produit comme
  `E-RESP-007` ici : il sera refuse par la contrainte d'unicite
  `uq_framework_responsibility_booster_actif_par_cercle` au moment de
  l'ecriture, traduite par `traduire_un_refus_de_la_base` — la base arbitre,
  §7.32. Batir la requete croisee aurait exige de connaitre la personne CIBLE
  de chaque ligne (resolue par `app.imports.analyse`, un autre module) avant
  meme de savoir si la ligne sera importee.

  `E-CERCLE-005`/`E-DSM-004` (cercle ou DSM d'une AUTRE entite) ne sont jamais
  produits : la recherche est elle-meme bornee a `entite` (`WHERE entity_id =
  :entite`), donc un code d'une autre entite ne resout tout simplement pas —
  meme observation que `E-CERCLE-002`/`E-DSM-002`. Les codes restent declares
  (`codes-erreurs-import.md` les exige), simplement jamais emis par CE module.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final, Literal

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.imports.correspondance import valeur_logique
from app.imports.structures import (
    NIVEAU_AVERTISSEMENT,
    NIVEAU_DECISION,
    NIVEAU_ERREUR,
    Probleme,
)
from app.organization.modeles import TypeResponsabilite
from app.people.modeles import (
    CategorieProfessionnelle,
    SituationProfessionnelle,
    normaliser_email,
)

#  ===========================================================================
#  Identite — F02, F03
#  ===========================================================================

CODE_IDENT_NOM_ABSENT: Final = "E-IDENT-001"
CODE_IDENT_PRENOM_ABSENT: Final = "E-IDENT-002"
CODE_IDENT_LONGUEUR: Final = "E-IDENT-003"

#  ===========================================================================
#  Entite — F05
#  ===========================================================================

CODE_ENTITE_ABSENTE: Final = "E-ENTITE-001"
CODE_ENTITE_INCONNUE: Final = "E-ENTITE-002"
CODE_ENTITE_ARCHIVEE: Final = "E-ENTITE-003"

#  ===========================================================================
#  Dates — F06, F07
#  ===========================================================================

CODE_DATE_ARRIVEE_ABSENTE: Final = "E-DATE-001"
CODE_DATE_ARRIVEE_FORMAT: Final = "E-DATE-002"
CODE_DATE_DEPART_FORMAT: Final = "E-DATE-003"
CODE_DATE_DEPART_AVANT_ARRIVEE: Final = "E-DATE-004"
CODE_DATE_ARRIVEE_FUTURE: Final = "W-DATE-001"
CODE_DATE_ARRIVEE_ANCIENNE: Final = "W-DATE-002"
CODE_DEPART_PASSE: Final = "W-DEPART-001"

#  ===========================================================================
#  Categorie professionnelle — F08
#  ===========================================================================

CODE_CATEGORIE_ABSENTE: Final = "E-CAT-001"
CODE_CATEGORIE_INVALIDE: Final = "E-CAT-002"

#  ===========================================================================
#  Metier — F11
#  ===========================================================================

CODE_METIER_ABSENT: Final = "E-METIER-001"
CODE_METIER_INCONNU_DU_CATALOGUE: Final = "D-METIER-001"

#  ===========================================================================
#  Presentation — F09 (avertissement seul, aucune liste controlee)
#  ===========================================================================

CODE_PRESENTATION_ABSENTE: Final = "W-PRESENTATION-001"
CODE_NOM_D_USAGE_IGNORE: Final = "W-USAGE-001"
CODE_NOM_EN_MAJUSCULES: Final = "W-CASSE-001"

#  ===========================================================================
#  Situation professionnelle — F12, F13 (F13 lui-meme reste a `app.imports.clients`)
#  ===========================================================================

CODE_SITUATION_ABSENTE: Final = "E-SIT-001"
CODE_SITUATION_INVALIDE: Final = "E-SIT-002"
CODE_MISSION_SANS_CLIENT: Final = "E-SIT-003"
CODE_INTERCONTRAT_AVEC_CLIENT: Final = "E-SIT-004"

#  codes-erreurs-import.md §3.7, LITTERALEMENT : la valeur CSV est en
#  FRANCAIS, contrairement a `SituationProfessionnelle.INTERCONTRACT` (modele
#  §6.5, anglais). Les deux vocabulaires ne coincident que sur `mission`.
VALEUR_CSV_INTERCONTRAT: Final = "intercontrat"

#  ===========================================================================
#  Cercles — F14, F15
#  ===========================================================================

CODE_CERCLE_PRINCIPAL_ABSENT: Final = "E-CERCLE-001"
CODE_CERCLE_PRINCIPAL_INCONNU: Final = "E-CERCLE-002"
CODE_CERCLE_SECONDAIRE_INCONNU: Final = "E-CERCLE-003"
CODE_CERCLE_PRINCIPAL_EN_SECONDAIRE: Final = "E-CERCLE-004"
#  `E-CERCLE-005` : declare, jamais emis par ce module — voir l'en-tete.
CODE_CERCLE_AUTRE_ENTITE: Final = "E-CERCLE-005"
CODE_CERCLE_PRINCIPAL_ABSENT_DSM: Final = "W-CERCLE-001"

#  ===========================================================================
#  DSM — F16
#  ===========================================================================

CODE_DSM_ABSENT: Final = "E-DSM-001"
CODE_DSM_INTROUVABLE: Final = "E-DSM-002"
CODE_DSM_SANS_RESPONSABILITE: Final = "E-DSM-003"
#  `E-DSM-004` : declare, jamais emis par ce module — voir l'en-tete.
CODE_DSM_AUTRE_ENTITE: Final = "E-DSM-004"
CODE_DSM_AUTO_REFERENCE: Final = "E-DSM-005"

#  ===========================================================================
#  Responsabilites Framework — F17
#  ===========================================================================

CODE_RESP_NON_RECONNUE: Final = "E-RESP-001"
CODE_RESP_BOOSTER_SANS_CERCLE: Final = "E-RESP-002"
CODE_RESP_OFFICE_MANAGER_SANS_BUREAU: Final = "E-RESP-003"
CODE_RESP_SCOPE_INTERDIT: Final = "E-RESP-004"
CODE_RESP_CERCLE_INCONNU: Final = "E-RESP-005"
CODE_RESP_BUREAU_INCONNU: Final = "E-RESP-006"
CODE_RESP_BOOSTER_CONFLIT: Final = "E-RESP-007"
CODE_RESP_BOOSTER_AUTRE_ENTITE: Final = "E-RESP-008"
CODE_RESP_BUREAU_TROP_DE_RESPONSABLES: Final = "E-RESP-009"

#  ===========================================================================
#  Roles techniques — F18
#  ===========================================================================

CODE_ROLE_NON_RECONNU: Final = "E-ROLE-001"
CODE_ROLE_SUPER_ADMIN_REFUSE: Final = "E-ROLE-002"

#  ===========================================================================
#  Autorisation photo — F19
#  ===========================================================================

CODE_PHOTO_INVALIDE: Final = "E-PHOTO-001"
CODE_PHOTO_INCONNUE: Final = "W-PHOTO-001"

_LONGUEUR_MAXIMALE_IDENTITE: Final = 100
_SEUIL_ANCIENNETE_ANS: Final = 20

#  codes-erreurs-import.md §5.8 : trois valeurs controlees, defaut `inconnu`.
VALEURS_PHOTO: Final[frozenset[str]] = frozenset({"oui", "non", "inconnu"})

#  schema-csv-collaborateurs.md §5.7 : SEUL `ENTITY_ADMIN` est accepte a
#  l'import. `SUPER_ADMIN` est un code RECONNU mais explicitement REFUSE
#  (`E-ROLE-002`), distinct d'un code non reconnu (`E-ROLE-001`).
ROLE_TECHNIQUE_ACCEPTE_A_L_IMPORT: Final = "ENTITY_ADMIN"
ROLE_TECHNIQUE_REFUSE_A_L_IMPORT: Final = "SUPER_ADMIN"

#  Textes REPRIS TELS QUELS de `codes-erreurs-import.md` — jamais reformules
#  (meme discipline que `app.imports.analyse`).
TEXTES_ORGANISATION: Final[dict[str, tuple[str, str]]] = {
    CODE_IDENT_NOM_ABSENT: ("Le nom est absent.", "Renseigner le nom."),
    CODE_IDENT_PRENOM_ABSENT: ("Le prénom est absent.", "Renseigner le prénom."),
    CODE_IDENT_LONGUEUR: (
        "Le nom ou le prénom dépasse la longueur autorisée.",
        "Raccourcir à 100 caractères au maximum.",
    ),
    CODE_ENTITE_ABSENTE: ("L'entité est absente.", "Renseigner le code de l'entité."),
    CODE_ENTITE_INCONNUE: (
        "L'entité indiquée est inconnue.",
        "Utiliser un code d'entité existant, ou faire créer l'entité par le super-administrateur.",
    ),
    CODE_ENTITE_ARCHIVEE: (
        "L'entité indiquée est archivée et ne peut plus recevoir de nouveaux membres.",
        "Choisir une entité active.",
    ),
    CODE_DATE_ARRIVEE_ABSENTE: (
        "La date d'arrivée est absente.",
        "Renseigner la date d'arrivée au format AAAA-MM-JJ.",
    ),
    CODE_DATE_ARRIVEE_FORMAT: (
        "La date d'arrivée n'est pas au format attendu AAAA-MM-JJ.",
        "Corriger le format. Attention aux dates converties par le tableur.",
    ),
    CODE_DATE_DEPART_FORMAT: (
        "La date de départ n'est pas au format attendu AAAA-MM-JJ.",
        "Corriger le format.",
    ),
    CODE_DATE_DEPART_AVANT_ARRIVEE: (
        "La date de départ est antérieure à la date d'arrivée.",
        "Corriger l'une des deux dates.",
    ),
    CODE_DATE_ARRIVEE_FUTURE: (
        "La date d'arrivée est dans le futur.",
        "Le profil est créé en état `future`. Il apparaîtra en arrivée à venir.",
    ),
    CODE_DATE_ARRIVEE_ANCIENNE: (
        "La date d'arrivée est antérieure de plus de vingt ans.",
        "Importé tel quel. À vérifier : conversion de date par le tableur probable.",
    ),
    CODE_DEPART_PASSE: (
        "La date de départ est déjà passée.",
        "Le profil est importé puis archivé, sans accès.",
    ),
    CODE_CATEGORIE_ABSENTE: (
        "La catégorie professionnelle est absente.",
        "Renseigner `consultant` ou `dg`.",
    ),
    CODE_CATEGORIE_INVALIDE: (
        "La catégorie professionnelle indiquée n'est pas reconnue.",
        "Utiliser une valeur de la liste contrôlée. Attention : un métier ou une "
        "responsabilité n'est pas une catégorie professionnelle.",
    ),
    CODE_METIER_ABSENT: (
        "Le métier est absent alors que le profil est actif.",
        "Renseigner le métier.",
    ),
    CODE_METIER_INCONNU_DU_CATALOGUE: (
        "Le métier indiqué est absent du catalogue de l'entité.",
        "Créer l'entrée au catalogue, ou corriger la valeur.",
    ),
    CODE_PRESENTATION_ABSENTE: (
        "La présentation courte est absente.",
        "Le profil est importé et compté comme incomplet. Le collaborateur la "
        "renseignera lors de sa fiche d'arrivée.",
    ),
    CODE_NOM_D_USAGE_IGNORE: ("Le nom d'usage est identique au nom.", "La valeur est ignorée."),
    CODE_NOM_EN_MAJUSCULES: (
        "Le nom est intégralement en majuscules.",
        "Importé tel quel. Aucune normalisation automatique n'est appliquée à un nom de personne.",
    ),
    CODE_SITUATION_ABSENTE: (
        "La situation professionnelle est absente.",
        "Renseigner `mission` ou `intercontrat`.",
    ),
    CODE_SITUATION_INVALIDE: (
        "La situation professionnelle indiquée n'est pas reconnue.",
        "Utiliser une valeur de la liste contrôlée.",
    ),
    CODE_MISSION_SANS_CLIENT: (
        "La situation est `mission` mais aucun client n'est renseigné.",
        "Renseigner le client, ou corriger la situation en `intercontrat`. "
        "Critère de qualité du cahier §12.6.",
    ),
    CODE_INTERCONTRAT_AVEC_CLIENT: (
        "La situation est `intercontrat` mais un client est renseigné.",
        "Vider le client, ou corriger la situation en `mission`. Critère de "
        "qualité du cahier §12.6.",
    ),
    CODE_CERCLE_PRINCIPAL_ABSENT: (
        "Le cercle principal est absent.",
        "Renseigner le cercle principal. Seule exception : une personne portant "
        "la responsabilité DSM peut ne pas en avoir.",
    ),
    CODE_CERCLE_PRINCIPAL_INCONNU: (
        "Le cercle principal indiqué est inconnu dans cette entité.",
        "Utiliser un code de cercle existant.",
    ),
    CODE_CERCLE_SECONDAIRE_INCONNU: (
        "Un cercle secondaire indiqué est inconnu dans cette entité.",
        "Corriger ou retirer la valeur.",
    ),
    CODE_CERCLE_PRINCIPAL_EN_SECONDAIRE: (
        "Le cercle principal est également listé en cercle secondaire.",
        "Retirer la valeur en doublon. Une même personne ne peut pas avoir deux "
        "relations actives identiques au même cercle.",
    ),
    CODE_CERCLE_AUTRE_ENTITE: (
        "Un cercle indiqué appartient à une autre entité.",
        "Corriger la valeur. Aucune relation croisée entre entités n'est autorisée.",
    ),
    CODE_CERCLE_PRINCIPAL_ABSENT_DSM: (
        "Le cercle principal est absent, mais la personne porte la responsabilité DSM.",
        "Accepté : un DSM peut ne pas avoir de cercle principal.",
    ),
    CODE_DSM_ABSENT: (
        "Le consultant est actif mais aucun DSM n'est renseigné.",
        "Renseigner l'adresse e-mail du DSM. Critère de qualité du cahier §12.6.",
    ),
    CODE_DSM_INTROUVABLE: (
        "L'adresse e-mail du DSM ne correspond à aucune personne du fichier ni de la base.",
        "Corriger l'adresse, ou ajouter la ligne du DSM au fichier.",
    ),
    CODE_DSM_SANS_RESPONSABILITE: (
        "La personne désignée comme DSM ne porte pas de responsabilité DSM active.",
        "Ajouter `DSM` à ses responsabilités Framework, ou désigner un autre DSM.",
    ),
    CODE_DSM_AUTRE_ENTITE: (
        "La personne désignée comme DSM appartient à une autre entité.",
        "Désigner un DSM de la même entité.",
    ),
    CODE_DSM_AUTO_REFERENCE: (
        "La personne est désignée comme son propre DSM.",
        "Corriger la référence.",
    ),
    CODE_RESP_NON_RECONNUE: (
        "Une responsabilité indiquée n'est pas reconnue.",
        "Utiliser `DSM`, `ESM`, `BOOSTER:<cercle>` ou `OFFICE_MANAGER:<bureau>`.",
    ),
    CODE_RESP_BOOSTER_SANS_CERCLE: (
        "La responsabilité `BOOSTER` est indiquée sans cercle.",
        "Préciser le cercle, par exemple `BOOSTER:DATA`.",
    ),
    CODE_RESP_OFFICE_MANAGER_SANS_BUREAU: (
        "La responsabilité `OFFICE_MANAGER` est indiquée sans bureau.",
        #  Le document source ecrit litteralement `OFFICE_MANAGER:BDE` ici —
        #  mais `BDE` est un code de bureau INITIAL (§8.3 du cahier), et
        #  `test_aucun_code_de_bureau_initial_n_est_ecrit_en_dur_dans_le_code`
        #  (LOT 6, `T4`) interdit sa presence en position EXECUTABLE dans
        #  `app/` : « entierement configurables » ne tolere aucune exception,
        #  pas meme un exemple. Le placeholder remplace la seule occurrence
        #  qui divergeait de ce garde-fou, sans rien changer au SENS du texte.
        "Préciser le bureau, par exemple `OFFICE_MANAGER:<code_bureau>`.",
    ),
    CODE_RESP_SCOPE_INTERDIT: (
        "Un scope est indiqué pour `DSM` ou `ESM`, qui n'en acceptent pas.",
        "Retirer le scope.",
    ),
    CODE_RESP_CERCLE_INCONNU: (
        "Le cercle indiqué pour `BOOSTER` est inconnu dans cette entité.",
        "Corriger le code du cercle.",
    ),
    CODE_RESP_BUREAU_INCONNU: (
        "Le bureau indiqué pour `OFFICE_MANAGER` est inconnu dans cette entité.",
        "Corriger le code du bureau.",
    ),
    CODE_RESP_BOOSTER_CONFLIT: (
        "Plusieurs personnes sont désignées Booster du même cercle.",
        "Ne conserver qu'un seul Booster actif par cercle. Critère de qualité du cahier §12.6.",
    ),
    CODE_RESP_BOOSTER_AUTRE_ENTITE: (
        "La personne est désignée Booster dans plusieurs entités.",
        "Une personne ne peut pas être Booster active dans plusieurs entités.",
    ),
    CODE_RESP_BUREAU_TROP_DE_RESPONSABLES: (
        "Le bureau compte plus de trois responsables actifs.",
        "Un bureau publié en compte entre un et trois.",
    ),
    CODE_ROLE_NON_RECONNU: (
        "Un rôle technique indiqué n'est pas reconnu.",
        "Seul `ENTITY_ADMIN` est accepté à l'import.",
    ),
    CODE_ROLE_SUPER_ADMIN_REFUSE: (
        "Le rôle `SUPER_ADMIN` ne peut pas être attribué par import.",
        "Retirer la valeur. L'attribution se fait depuis la super-administration, "
        "avec audit et alerte de sécurité.",
    ),
    CODE_PHOTO_INVALIDE: (
        "La valeur d'autorisation de photographie n'est pas reconnue.",
        "Utiliser `oui`, `non` ou `inconnu`, ou laisser le champ vide.",
    ),
    CODE_PHOTO_INCONNUE: (
        "L'autorisation de photographie est inconnue.",
        "Aucune photo n'est publiée, l'avatar neutre est utilisé.",
    ),
}

NIVEAU_DU_CODE_ORGANISATION: Final[dict[str, str]] = {
    CODE_IDENT_NOM_ABSENT: NIVEAU_ERREUR,
    CODE_IDENT_PRENOM_ABSENT: NIVEAU_ERREUR,
    CODE_IDENT_LONGUEUR: NIVEAU_ERREUR,
    CODE_ENTITE_ABSENTE: NIVEAU_ERREUR,
    CODE_ENTITE_INCONNUE: NIVEAU_ERREUR,
    CODE_ENTITE_ARCHIVEE: NIVEAU_ERREUR,
    CODE_DATE_ARRIVEE_ABSENTE: NIVEAU_ERREUR,
    CODE_DATE_ARRIVEE_FORMAT: NIVEAU_ERREUR,
    CODE_DATE_DEPART_FORMAT: NIVEAU_ERREUR,
    CODE_DATE_DEPART_AVANT_ARRIVEE: NIVEAU_ERREUR,
    CODE_DATE_ARRIVEE_FUTURE: NIVEAU_AVERTISSEMENT,
    CODE_DATE_ARRIVEE_ANCIENNE: NIVEAU_AVERTISSEMENT,
    CODE_DEPART_PASSE: NIVEAU_AVERTISSEMENT,
    CODE_CATEGORIE_ABSENTE: NIVEAU_ERREUR,
    CODE_CATEGORIE_INVALIDE: NIVEAU_ERREUR,
    CODE_METIER_ABSENT: NIVEAU_ERREUR,
    CODE_METIER_INCONNU_DU_CATALOGUE: NIVEAU_DECISION,
    CODE_PRESENTATION_ABSENTE: NIVEAU_AVERTISSEMENT,
    CODE_NOM_D_USAGE_IGNORE: NIVEAU_AVERTISSEMENT,
    CODE_NOM_EN_MAJUSCULES: NIVEAU_AVERTISSEMENT,
    CODE_SITUATION_ABSENTE: NIVEAU_ERREUR,
    CODE_SITUATION_INVALIDE: NIVEAU_ERREUR,
    CODE_MISSION_SANS_CLIENT: NIVEAU_ERREUR,
    CODE_INTERCONTRAT_AVEC_CLIENT: NIVEAU_ERREUR,
    CODE_CERCLE_PRINCIPAL_ABSENT: NIVEAU_ERREUR,
    CODE_CERCLE_PRINCIPAL_INCONNU: NIVEAU_ERREUR,
    CODE_CERCLE_SECONDAIRE_INCONNU: NIVEAU_ERREUR,
    CODE_CERCLE_PRINCIPAL_EN_SECONDAIRE: NIVEAU_ERREUR,
    CODE_CERCLE_AUTRE_ENTITE: NIVEAU_ERREUR,
    CODE_CERCLE_PRINCIPAL_ABSENT_DSM: NIVEAU_AVERTISSEMENT,
    CODE_DSM_ABSENT: NIVEAU_ERREUR,
    CODE_DSM_INTROUVABLE: NIVEAU_ERREUR,
    CODE_DSM_SANS_RESPONSABILITE: NIVEAU_ERREUR,
    CODE_DSM_AUTRE_ENTITE: NIVEAU_ERREUR,
    CODE_DSM_AUTO_REFERENCE: NIVEAU_ERREUR,
    CODE_RESP_NON_RECONNUE: NIVEAU_ERREUR,
    CODE_RESP_BOOSTER_SANS_CERCLE: NIVEAU_ERREUR,
    CODE_RESP_OFFICE_MANAGER_SANS_BUREAU: NIVEAU_ERREUR,
    CODE_RESP_SCOPE_INTERDIT: NIVEAU_ERREUR,
    CODE_RESP_CERCLE_INCONNU: NIVEAU_ERREUR,
    CODE_RESP_BUREAU_INCONNU: NIVEAU_ERREUR,
    CODE_RESP_BOOSTER_CONFLIT: NIVEAU_ERREUR,
    CODE_RESP_BOOSTER_AUTRE_ENTITE: NIVEAU_ERREUR,
    CODE_RESP_BUREAU_TROP_DE_RESPONSABLES: NIVEAU_ERREUR,
    CODE_ROLE_NON_RECONNU: NIVEAU_ERREUR,
    CODE_ROLE_SUPER_ADMIN_REFUSE: NIVEAU_ERREUR,
    CODE_PHOTO_INVALIDE: NIVEAU_ERREUR,
    CODE_PHOTO_INCONNUE: NIVEAU_AVERTISSEMENT,
}


@dataclasses.dataclass(frozen=True, slots=True)
class ResponsabiliteDemandee:
    """Un token `F17` reconnu et resolu — `type_responsabilite` en MAJUSCULES (§8.4)."""

    type_responsabilite: str
    circle_id: uuid.UUID | None
    office_id: uuid.UUID | None


@dataclasses.dataclass(frozen=True, slots=True)
class ResolutionOrganisationnelle:
    """Ce que ce module sait d'une ligne, resolu ou non.

    Un champ `None` (ou un tuple vide) veut dire « non resolu » — a cause d'un
    probleme PORTE DANS `problemes`, jamais une absence muette. `app.imports.
    execution` ne doit lire ces champs que pour une ligne dont l'etat derive
    (via `app.imports.analyse._etat_depuis_les_problemes`) est importable.
    """

    problemes: tuple[Probleme, ...]
    nom: str | None
    prenom: str | None
    nom_usage: str | None
    entite_cible: uuid.UUID | None
    arrival_date: dt.date | None
    departure_date: dt.date | None
    categorie: str | None
    presentation_courte: str | None
    fun_fact: str | None
    job_catalog_id: uuid.UUID | None
    situation: str | None
    cercle_principal_id: uuid.UUID | None
    cercles_secondaires_ids: tuple[uuid.UUID, ...]
    dsm_email_normalise: str | None
    responsabilites: tuple[ResponsabiliteDemandee, ...]
    roles_techniques: tuple[str, ...]
    photo_autorisation: str


def _parse_date_iso(valeur: str) -> dt.date | Literal["invalide"]:
    try:
        return dt.date.fromisoformat(valeur)
    except ValueError:
        return "invalide"


#  ===========================================================================
#  Resolutions par lot — UNE requete chacune, jamais une par ligne (§7.27)
#  ===========================================================================

_ENTITES_PAR_CODE: Final = text("SELECT id, code, status FROM entity WHERE code = ANY(:codes)")

_METIERS_PAR_CODE: Final = text(
    """
    SELECT id, code FROM job_catalog
     WHERE entity_id = :entite AND code = ANY(:codes)
       AND archived_at IS NULL AND active IS TRUE
    """
)

_CERCLES_PAR_CODE: Final = text(
    "SELECT id, code FROM circle WHERE entity_id = :entite AND code = ANY(:codes) "
    "AND archived_at IS NULL"
)

_BUREAUX_PAR_CODE: Final = text(
    "SELECT id, code FROM office WHERE entity_id = :entite AND code = ANY(:codes) "
    "AND archived_at IS NULL"
)

_DSM_ACTIFS_PAR_EMAIL: Final = text(
    """
    SELECT p.email_normalized AS email, p.id AS personne
      FROM person p
      JOIN framework_responsibility_assignment fra ON fra.person_id = p.id
     WHERE fra.entity_id = :entite AND fra.responsibility_type = 'DSM'
       AND fra.archived_at IS NULL AND fra.period @> :instant
       AND p.email_normalized = ANY(:emails)
    """
)

_BOOSTER_DANS_UNE_AUTRE_ENTITE: Final = text(
    """
    SELECT p.email_normalized AS email
      FROM person p
      JOIN framework_responsibility_assignment fra ON fra.person_id = p.id
     WHERE fra.responsibility_type = 'BOOSTER' AND fra.archived_at IS NULL
       AND fra.period @> :instant AND fra.entity_id != :entite
       AND p.email_normalized = ANY(:emails)
    """
)

_BUREAUX_OCCUPATION: Final = text(
    """
    SELECT o.id AS bureau,
           count(fra.id) FILTER (
               WHERE fra.responsibility_type = 'OFFICE_MANAGER'
                 AND fra.archived_at IS NULL AND fra.period @> :instant
           ) AS actifs,
           EXISTS (
               SELECT 1 FROM content_page cp
                WHERE cp.office_id = o.id AND cp.entity_id = o.entity_id
                  AND cp.page_type = 'OFFICE' AND cp.state = 'published'
                  AND cp.archived_at IS NULL
           ) AS publie
      FROM office o
      LEFT JOIN framework_responsibility_assignment fra ON fra.office_id = o.id
     WHERE o.entity_id = :entite AND o.id = ANY(:bureaux)
     GROUP BY o.id
    """
)


def _resoudre_par_code(
    connexion: Connection, requete: Any, *, entite: uuid.UUID | None, codes: list[str]
) -> dict[str, uuid.UUID]:
    if not codes:
        return {}
    parametres: dict[str, Any] = {"codes": codes}
    if entite is not None:
        parametres["entite"] = entite
    return {ligne.code: ligne.id for ligne in connexion.execute(requete, parametres)}


@dataclasses.dataclass(frozen=True, slots=True)
class _EntiteResolue:
    identifiant: uuid.UUID
    actif: bool


def _resoudre_les_entites(connexion: Connection, *, codes: list[str]) -> dict[str, _EntiteResolue]:
    if not codes:
        return {}
    return {
        ligne.code: _EntiteResolue(identifiant=ligne.id, actif=ligne.status == "active")
        for ligne in connexion.execute(_ENTITES_PAR_CODE, {"codes": codes})
    }


def _parser_les_responsabilites(brut: str) -> list[tuple[str, str | None]]:
    """Scinde `F17` sur `|`, puis chaque token sur le PREMIER `:` — schema-csv §5.6."""
    tokens: list[tuple[str, str | None]] = []
    for morceau in brut.split("|"):
        morceau = morceau.strip()
        if not morceau:
            continue
        type_brut, _, scope_brut = morceau.partition(":")
        scope = scope_brut.strip() or None
        tokens.append((type_brut.strip(), scope))
    return tokens


def valider_les_champs_organisationnels(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lignes: list[tuple[uuid.UUID, dict[str, object]]],
    instant: dt.datetime,
) -> dict[uuid.UUID, ResolutionOrganisationnelle]:
    """Resoudre et valider `F02`..`F19` (hors `F01`, `F13`) — appelable deux fois, voir l'en-tete.

    `lignes` : `(identifiant, raw_data)`, meme ordre que `app.imports.analyse`.
    """
    problemes: dict[uuid.UUID, list[Probleme]] = {identifiant: [] for identifiant, _ in lignes}

    #  --- Lecture brute, une fois par ligne, aucune requete encore ---
    bruts: dict[uuid.UUID, dict[str, str | None]] = {}
    for identifiant, raw in lignes:
        bruts[identifiant] = {
            code: valeur_logique(raw, code)
            for code in (
                "F02",
                "F03",
                "F04",
                "F05",
                "F06",
                "F07",
                "F08",
                "F09",
                "F10",
                "F11",
                "F12",
                "F14",
                "F15",
                "F16",
                "F17",
                "F18",
                "F19",
            )
        }

    #  --- Resolutions par lot ---
    #  Champs extraits dans des variables NOMMEES avant chaque filtre : un
    #  `dict[str, str | None]` n'est pas un `TypedDict`, et mypy ne retreint
    #  pas `b["F05"]` repete apres un test sur la meme expression — seule une
    #  variable simple l'est (meme contrainte que dans la boucle principale).
    #  F17 : parse D'ABORD, car `BOOSTER:<cercle>` alimente la MEME
    #  resolution de codes de cercle que F14/F15 — un cercle vise UNIQUEMENT
    #  par un Booster ne doit pas rester absent de `cercles` (defaut trouve
    #  et corrige avant commit : `E-RESP-005` sur un cercle qui existe
    #  pourtant, faute d'avoir ete inclus dans le lot resolu).
    responsabilites_brutes: dict[uuid.UUID, list[tuple[str, str | None]]] = {}
    for identifiant_b, b in bruts.items():
        f17_b = b["F17"]
        responsabilites_brutes[identifiant_b] = _parser_les_responsabilites(f17_b) if f17_b else []

    codes_entite_vus: set[str] = set()
    codes_metier_vus: set[str] = set()
    codes_cercle: set[str] = set()
    for b in bruts.values():
        f05_b, f11_b, f14_b, f15_b = b["F05"], b["F11"], b["F14"], b["F15"]
        if f05_b:
            codes_entite_vus.add(f05_b)
        if f11_b:
            codes_metier_vus.add(f11_b)
        if f14_b:
            codes_cercle.add(f14_b)
        if f15_b:
            codes_cercle.update(c.strip() for c in f15_b.split("|") if c.strip())
    for tokens in responsabilites_brutes.values():
        for type_brut, scope in tokens:
            if type_brut == TypeResponsabilite.BOOSTER.value and scope:
                codes_cercle.add(scope)
    entites = _resoudre_les_entites(connexion, codes=sorted(codes_entite_vus))
    metiers = _resoudre_par_code(
        connexion, _METIERS_PAR_CODE, entite=entite, codes=sorted(codes_metier_vus)
    )
    cercles = _resoudre_par_code(
        connexion, _CERCLES_PAR_CODE, entite=entite, codes=sorted(codes_cercle)
    )

    codes_bureau = sorted(
        {
            scope
            for tokens in responsabilites_brutes.values()
            for type_brut, scope in tokens
            if type_brut == TypeResponsabilite.OFFICE_MANAGER.value and scope
        }
    )
    bureaux = _resoudre_par_code(connexion, _BUREAUX_PAR_CODE, entite=entite, codes=codes_bureau)

    #  F01 est deja normalise par `app.imports.analyse`, mais ce module est
    #  appele INDEPENDAMMENT (deux fois) : il derive sa propre normalisation,
    #  cout negligeable, pour ne dependre d'aucun etat intermediaire d'un autre
    #  module (§7.27).
    emails_normalises: dict[uuid.UUID, str | None] = {}
    for identifiant, raw in lignes:
        f01_brut = valeur_logique(raw, "F01")
        emails_normalises[identifiant] = normaliser_email(f01_brut) if f01_brut else None

    #  Qui, dans CE fichier, recevra une responsabilite DSM (F08=dg ou F17
    #  contient DSM) ? Necessaire pour F16 (designer un DSM « present dans le
    #  fichier ») ET pour W-CERCLE-001 (cercle principal absent toleré pour un
    #  DSM).
    sera_dsm_dans_le_fichier: dict[uuid.UUID, bool] = {}
    for identifiant, b in bruts.items():
        categorie_brute = b["F08"]
        est_dg = categorie_brute == CategorieProfessionnelle.DG.value
        porte_dsm = any(
            type_brut == TypeResponsabilite.DSM.value
            for type_brut, _ in responsabilites_brutes[identifiant]
        )
        sera_dsm_dans_le_fichier[identifiant] = est_dg or porte_dsm

    candidats_dsm_fichier: dict[str, uuid.UUID] = {}
    for identifiant, email in emails_normalises.items():
        if email and sera_dsm_dans_le_fichier[identifiant]:
            candidats_dsm_fichier.setdefault(email, identifiant)

    emails_pour_dsm_vus: set[str] = set()
    for b in bruts.values():
        f16_b = b["F16"]
        if f16_b:
            emails_pour_dsm_vus.add(normaliser_email(f16_b))
    emails_pour_dsm = sorted(emails_pour_dsm_vus)
    dsm_actifs_en_base = {
        ligne.email: ligne.personne
        for ligne in (
            connexion.execute(
                _DSM_ACTIFS_PAR_EMAIL,
                {"entite": entite, "instant": instant, "emails": emails_pour_dsm},
            )
            if emails_pour_dsm
            else []
        )
    }

    #  E-RESP-008 : la personne (EXISTANTE, par e-mail) est-elle deja Booster
    #  active ailleurs ?
    emails_pour_booster_externe = sorted(
        {
            email
            for identifiant, email in emails_normalises.items()
            if email
            and any(
                t == TypeResponsabilite.BOOSTER.value
                for t, _ in responsabilites_brutes[identifiant]
            )
        }
    )
    boosters_ailleurs = {
        ligne.email
        for ligne in (
            connexion.execute(
                _BOOSTER_DANS_UNE_AUTRE_ENTITE,
                {"entite": entite, "instant": instant, "emails": emails_pour_booster_externe},
            )
            if emails_pour_booster_externe
            else []
        )
    }

    #  E-RESP-007 : conflits DE FICHIER, un cercle vise par plusieurs lignes.
    boosters_par_cercle: dict[str, list[uuid.UUID]] = {}
    for identifiant, tokens in responsabilites_brutes.items():
        for type_brut, scope in tokens:
            if type_brut == TypeResponsabilite.BOOSTER.value and scope and scope in cercles:
                boosters_par_cercle.setdefault(scope, []).append(identifiant)
    cercles_en_conflit = {code for code, ids in boosters_par_cercle.items() if len(ids) > 1}

    #  E-RESP-009 : occupation des bureaux VISES par ce fichier.
    bureaux_vises: dict[str, list[uuid.UUID]] = {}
    for identifiant, tokens in responsabilites_brutes.items():
        for type_brut, scope in tokens:
            if type_brut == TypeResponsabilite.OFFICE_MANAGER.value and scope and scope in bureaux:
                bureaux_vises.setdefault(scope, []).append(identifiant)
    occupation_bureaux = {
        ligne.bureau: (int(ligne.actifs), bool(ligne.publie))
        for ligne in (
            connexion.execute(
                _BUREAUX_OCCUPATION,
                {
                    "entite": entite,
                    "instant": instant,
                    "bureaux": [bureaux[c] for c in bureaux_vises],
                },
            )
            if bureaux_vises
            else []
        )
    }
    bureaux_satures = {
        code
        for code, ids in bureaux_vises.items()
        if bureaux[code] in occupation_bureaux
        and occupation_bureaux[bureaux[code]][1]
        and occupation_bureaux[bureaux[code]][0] + len(ids) > 3
    }

    resultats: dict[uuid.UUID, ResolutionOrganisationnelle] = {}
    for identifiant, raw in lignes:
        b = bruts[identifiant]
        p: list[Probleme] = problemes[identifiant]
        #  Champs locaux, EXTRAITS UNE FOIS : `b["F06"]` repete n'est pas
        #  retreci par mypy apres un `is None` (un `dict[str, str | None]`
        #  n'est pas un `TypedDict`) — une variable locale, si.
        f05, f06, f07, f08 = b["F05"], b["F06"], b["F07"], b["F08"]
        f09, f10, f11, f12 = b["F09"], b["F10"], b["F11"], b["F12"]
        f14, f15, f16, f18, f19 = b["F14"], b["F15"], b["F16"], b["F18"], b["F19"]

        #  --- Identite ---
        nom, prenom = b["F02"], b["F03"]
        if nom is None:
            p.append(Probleme(CODE_IDENT_NOM_ABSENT, "F02"))
        elif len(nom) > _LONGUEUR_MAXIMALE_IDENTITE:
            p.append(Probleme(CODE_IDENT_LONGUEUR, "F02"))
        elif nom.isupper():
            p.append(Probleme(CODE_NOM_EN_MAJUSCULES, "F02"))
        if prenom is None:
            p.append(Probleme(CODE_IDENT_PRENOM_ABSENT, "F03"))
        elif len(prenom) > _LONGUEUR_MAXIMALE_IDENTITE:
            p.append(Probleme(CODE_IDENT_LONGUEUR, "F03"))
        nom_usage = b["F04"]
        if nom_usage is not None and nom is not None and nom_usage == nom:
            p.append(Probleme(CODE_NOM_D_USAGE_IGNORE, "F04"))
            nom_usage = None

        #  --- Entite ---
        entite_cible: uuid.UUID | None = None
        if f05 is None:
            p.append(Probleme(CODE_ENTITE_ABSENTE, "F05"))
        else:
            resolue = entites.get(f05)
            #  Le lot est deja BORNE a `entite` (route par entite) : un code
            #  qui resout une AUTRE entite n'est pas utilisable pour CE lot.
            if resolue is None or resolue.identifiant != entite:
                p.append(Probleme(CODE_ENTITE_INCONNUE, "F05"))
            elif not resolue.actif:
                p.append(Probleme(CODE_ENTITE_ARCHIVEE, "F05"))
            else:
                entite_cible = resolue.identifiant

        #  --- Dates ---
        arrival_date: dt.date | None = None
        departure_date: dt.date | None = None
        depart_passe = False
        if f06 is None:
            p.append(Probleme(CODE_DATE_ARRIVEE_ABSENTE, "F06"))
        else:
            parsee_arrivee = _parse_date_iso(f06)
            if parsee_arrivee == "invalide":
                p.append(Probleme(CODE_DATE_ARRIVEE_FORMAT, "F06"))
            else:
                arrival_date = parsee_arrivee
                seuil_ancien = instant.date() - dt.timedelta(days=365 * _SEUIL_ANCIENNETE_ANS)
                if arrival_date > instant.date():
                    p.append(Probleme(CODE_DATE_ARRIVEE_FUTURE, "F06"))
                elif arrival_date <= seuil_ancien:
                    p.append(Probleme(CODE_DATE_ARRIVEE_ANCIENNE, "F06"))
        if f07 is not None:
            parsee_depart = _parse_date_iso(f07)
            if parsee_depart == "invalide":
                p.append(Probleme(CODE_DATE_DEPART_FORMAT, "F07"))
            elif arrival_date is not None and parsee_depart < arrival_date:
                p.append(Probleme(CODE_DATE_DEPART_AVANT_ARRIVEE, "F07"))
            else:
                departure_date = parsee_depart
                if departure_date <= instant.date():
                    p.append(Probleme(CODE_DEPART_PASSE, "F07"))
                    depart_passe = True

        #  --- Categorie professionnelle ---
        categorie: str | None = None
        if f08 is None:
            p.append(Probleme(CODE_CATEGORIE_ABSENTE, "F08"))
        elif f08 not in (
            CategorieProfessionnelle.CONSULTANT.value,
            CategorieProfessionnelle.DG.value,
        ):
            p.append(Probleme(CODE_CATEGORIE_INVALIDE, "F08"))
        else:
            categorie = f08

        #  --- Presentation / fun fact : simple passage, un seul avertissement ---
        presentation_courte = f09
        fun_fact = f10
        profil_sera_actif = (
            arrival_date is not None and not depart_passe and arrival_date <= instant.date()
        )
        if presentation_courte is None:
            p.append(Probleme(CODE_PRESENTATION_ABSENTE, "F09"))

        #  --- Metier ---
        job_catalog_id: uuid.UUID | None = None
        if f11 is None:
            if profil_sera_actif:
                p.append(Probleme(CODE_METIER_ABSENT, "F11"))
        else:
            job_catalog_id = metiers.get(f11)
            if job_catalog_id is None:
                p.append(Probleme(CODE_METIER_INCONNU_DU_CATALOGUE, "F11", f11))

        #  --- Situation (F13/client resolu par `app.imports.clients`) ---
        #  **DEFAUT TROUVE ET CORRIGE AVANT COMMIT** : le CSV ecrit
        #  `intercontrat` (francais, litteralement cite par codes-erreurs-
        #  import.md §3.7), la base `intercontract` (anglais, modele §6.5,
        #  DEC-499). Les deux vocabulaires NE COINCIDENT PAS sur cette seule
        #  valeur — `mission` est identique dans les deux. Le CSV est traduit
        #  ICI, une seule fois, vers l'enum interne.
        situation: str | None = None
        client_renseigne = valeur_logique(raw, "F13") is not None
        if f12 is None:
            p.append(Probleme(CODE_SITUATION_ABSENTE, "F12"))
        elif f12 not in (SituationProfessionnelle.MISSION.value, VALEUR_CSV_INTERCONTRAT):
            p.append(Probleme(CODE_SITUATION_INVALIDE, "F12"))
        else:
            situation = (
                SituationProfessionnelle.INTERCONTRACT.value
                if f12 == VALEUR_CSV_INTERCONTRAT
                else f12
            )
            if situation == SituationProfessionnelle.MISSION.value and not client_renseigne:
                p.append(Probleme(CODE_MISSION_SANS_CLIENT, "F13"))
            if situation == SituationProfessionnelle.INTERCONTRACT.value and client_renseigne:
                p.append(Probleme(CODE_INTERCONTRAT_AVEC_CLIENT, "F13"))

        #  --- Cercles ---
        cercle_principal_id: uuid.UUID | None = None
        cercles_secondaires_ids: list[uuid.UUID] = []
        est_ou_sera_dsm = sera_dsm_dans_le_fichier[identifiant]
        if f14 is None:
            if est_ou_sera_dsm:
                p.append(Probleme(CODE_CERCLE_PRINCIPAL_ABSENT_DSM, "F14"))
            else:
                p.append(Probleme(CODE_CERCLE_PRINCIPAL_ABSENT, "F14"))
        else:
            cercle_principal_id = cercles.get(f14)
            if cercle_principal_id is None:
                p.append(Probleme(CODE_CERCLE_PRINCIPAL_INCONNU, "F14"))
        if f15:
            for code_secondaire in (c.strip() for c in f15.split("|") if c.strip()):
                if f14 is not None and code_secondaire == f14:
                    p.append(Probleme(CODE_CERCLE_PRINCIPAL_EN_SECONDAIRE, "F15"))
                    continue
                resolu = cercles.get(code_secondaire)
                if resolu is None:
                    p.append(Probleme(CODE_CERCLE_SECONDAIRE_INCONNU, "F15"))
                else:
                    cercles_secondaires_ids.append(resolu)

        #  --- DSM ---
        #  **DEFAUT TROUVE ET CORRIGE AVANT COMMIT** : schema-csv-
        #  collaborateurs.md §5.5 ecrit litteralement « Obligatoire pour un
        #  CONSULTANT actif », et codes-erreurs-import.md §3.9 : « le
        #  CONSULTANT est actif ». Un `dg` ne porte pas cette obligation — il
        #  recoit sa PROPRE responsabilite DSM (`RIGHTS-005`), il n'en SUIT
        #  pas une autre. Sans cette restriction, tout `dg` actif sans DSM
        #  explicite serait rejete a tort.
        dsm_email_normalise: str | None = None
        if f16 is None:
            if profil_sera_actif and categorie == CategorieProfessionnelle.CONSULTANT.value:
                p.append(Probleme(CODE_DSM_ABSENT, "F16"))
        else:
            cible = normaliser_email(f16)
            propre_email = emails_normalises.get(identifiant)
            if propre_email is not None and cible == propre_email:
                p.append(Probleme(CODE_DSM_AUTO_REFERENCE, "F16"))
            elif cible in dsm_actifs_en_base or (
                cible in candidats_dsm_fichier and candidats_dsm_fichier[cible] != identifiant
            ):
                dsm_email_normalise = cible
            else:
                #  Present nulle part : soit l'adresse ne designe personne
                #  (E-DSM-002), soit elle designe quelqu'un sans responsabilite
                #  DSM active (E-DSM-003). Les deux sont indiscernables sans
                #  une recherche de personne supplementaire, hors perimetre
                #  d'un email qui ne resout ni en base ni dans le fichier.
                existe_sans_dsm = cible not in dsm_actifs_en_base and any(
                    e == cible for e in emails_normalises.values()
                )
                if existe_sans_dsm:
                    p.append(Probleme(CODE_DSM_SANS_RESPONSABILITE, "F16"))
                else:
                    p.append(Probleme(CODE_DSM_INTROUVABLE, "F16"))

        #  --- Responsabilites Framework ---
        responsabilites: list[ResponsabiliteDemandee] = []
        for type_brut, scope in responsabilites_brutes[identifiant]:
            if type_brut not in (
                TypeResponsabilite.DSM.value,
                TypeResponsabilite.ESM.value,
                TypeResponsabilite.BOOSTER.value,
                TypeResponsabilite.OFFICE_MANAGER.value,
            ):
                p.append(Probleme(CODE_RESP_NON_RECONNUE, "F17", type_brut))
                continue
            if type_brut in (TypeResponsabilite.DSM.value, TypeResponsabilite.ESM.value):
                if scope is not None:
                    p.append(Probleme(CODE_RESP_SCOPE_INTERDIT, "F17"))
                    continue
                responsabilites.append(ResponsabiliteDemandee(type_brut, None, None))
                continue
            if type_brut == TypeResponsabilite.BOOSTER.value:
                if scope is None:
                    p.append(Probleme(CODE_RESP_BOOSTER_SANS_CERCLE, "F17"))
                    continue
                if scope in cercles_en_conflit:
                    p.append(Probleme(CODE_RESP_BOOSTER_CONFLIT, "F17", scope))
                    continue
                cercle_id = cercles.get(scope)
                if cercle_id is None:
                    p.append(Probleme(CODE_RESP_CERCLE_INCONNU, "F17"))
                    continue
                email_propre = emails_normalises.get(identifiant)
                if email_propre is not None and email_propre in boosters_ailleurs:
                    p.append(Probleme(CODE_RESP_BOOSTER_AUTRE_ENTITE, "F17"))
                    continue
                responsabilites.append(ResponsabiliteDemandee(type_brut, cercle_id, None))
                continue
            #  OFFICE_MANAGER
            if scope is None:
                p.append(Probleme(CODE_RESP_OFFICE_MANAGER_SANS_BUREAU, "F17"))
                continue
            if scope in bureaux_satures:
                p.append(Probleme(CODE_RESP_BUREAU_TROP_DE_RESPONSABLES, "F17", scope))
                continue
            bureau_id = bureaux.get(scope)
            if bureau_id is None:
                p.append(Probleme(CODE_RESP_BUREAU_INCONNU, "F17"))
                continue
            responsabilites.append(ResponsabiliteDemandee(type_brut, None, bureau_id))

        #  --- Roles techniques ---
        roles_techniques: list[str] = []
        if f18:
            for role_brut in (r.strip() for r in f18.split("|") if r.strip()):
                if role_brut == ROLE_TECHNIQUE_REFUSE_A_L_IMPORT:
                    p.append(Probleme(CODE_ROLE_SUPER_ADMIN_REFUSE, "F18"))
                elif role_brut != ROLE_TECHNIQUE_ACCEPTE_A_L_IMPORT:
                    p.append(Probleme(CODE_ROLE_NON_RECONNU, "F18"))
                else:
                    roles_techniques.append(role_brut)

        #  --- Autorisation photo ---
        photo_autorisation = "inconnu"
        if f19 is not None:
            if f19 not in VALEURS_PHOTO:
                p.append(Probleme(CODE_PHOTO_INVALIDE, "F19"))
            else:
                photo_autorisation = f19
        if photo_autorisation == "inconnu":
            p.append(Probleme(CODE_PHOTO_INCONNUE, "F19"))

        resultats[identifiant] = ResolutionOrganisationnelle(
            problemes=tuple(p),
            nom=nom,
            prenom=prenom,
            nom_usage=nom_usage,
            entite_cible=entite_cible,
            arrival_date=arrival_date,
            departure_date=departure_date,
            categorie=categorie,
            presentation_courte=presentation_courte,
            fun_fact=fun_fact,
            job_catalog_id=job_catalog_id,
            situation=situation,
            cercle_principal_id=cercle_principal_id,
            cercles_secondaires_ids=tuple(cercles_secondaires_ids),
            dsm_email_normalise=dsm_email_normalise,
            responsabilites=tuple(responsabilites),
            roles_techniques=tuple(roles_techniques),
            photo_autorisation=photo_autorisation,
        )

    return resultats
