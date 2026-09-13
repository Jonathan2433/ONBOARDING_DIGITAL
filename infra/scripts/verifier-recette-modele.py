#!/usr/bin/env python3
"""Classer les VINGT-CINQ controles de recette du modele §30.

LOT 2, sous-etape `T12`, stories `MVP-L02-US007` et `US008`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE

  Le §30 du modele enumere 25 controles et pose : « le modele sera accepte si les
  tests demontrent notamment que... ». **La plupart portent sur des tables que le
  LOT 2 ne cree pas** -- magic link, photos, onboarding, imports, jobs, audit,
  purge, exports.

  **Sous-traiter une partie de cette liste en silence serait le pire choix.** La
  porte `G2` se prononcera sur le modele : elle doit savoir exactement lesquels
  sont acquis, lesquels sont reportes et a quel lot, et lesquels sont
  INAPPLICABLES faute d'un champ que le modele ne declare pas.

  C'est le parti du §7.20 de la passation : **exiger ce qui est exigible,
  rapporter visiblement le reste, en le nommant.**

LA LISTE EST DERIVEE DU MODELE, JAMAIS RECOPIEE

  Le §30 est lu dans `MODELE_DONNEES_EXALT.md`, et **chaque element doit etre
  classe**. Un element nouveau ou reformule fait ECHOUER ce controle plutot que
  d'etre ignore -- meme mecanique que `verifier-historisation.py` pour le §25.2.

  Le rattachement d'un element a son statut est une INTERPRETATION : elle est
  declaree ci-dessous, avec le test qui la prouve quand elle est acquise. Et
  **l'existence de ce test est verifiee**, sinon le classement ne serait qu'une
  affirmation.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
MODELE = RACINE / "docs" / "architecture" / "MODELE_DONNEES_EXALT.md"
TESTS = RACINE / "apps" / "api" / "tests"

ACQUIS = "acquis"
PARTIEL = "partiel"
REPORTE = "reporte"
INAPPLICABLE = "inapplicable"


class Classement:
    """Statut d'un controle du §30, et ce qui le prouve ou l'ajourne."""

    def __init__(
        self,
        numero: int,
        statut: str,
        *,
        preuve: str = "",
        tests: tuple[str, ...] = (),
        residuel: str = "",
        lot: str = "",
    ) -> None:
        self.numero = numero
        self.statut = statut
        self.preuve = preuve
        self.tests = tests
        self.residuel = residuel
        self.lot = lot


#  Le rattachement, par NUMERO du §30. Les numeros sont stables : le modele est
#  immuable, et son integrite est prouvee par empreinte SHA-256.
CLASSEMENT: dict[int, Classement] = {
    1: Classement(
        1,
        ACQUIS,
        preuve="`T3` — unicite insensible a la casse sur `person.email_normalized` (`ECART-029`)",
        tests=("test_l_email_normalise_est_unique",),
    ),
    2: Classement(
        2,
        ACQUIS,
        preuve="`T4` — index partiel §25.1 ET exclusion §25.2, deux contraintes complementaires",
        tests=("test_UNE_SEULE_appartenance_occupante_par_personne",),
    ),
    3: Classement(
        3,
        ACQUIS,
        preuve="`T9` — les 7 relations du §25.2, COMPTEES par `make historisation-check`",
        tests=(
            "test_deux_appartenances_HISTORIQUES_qui_se_chevauchent_sont_refusees",
            "test_deux_periodes_de_cercle_PRINCIPAL_qui_se_chevauchent_sont_refusees",
            "test_deux_responsabilites_DSM_qui_se_chevauchent_sont_refusees",
        ),
    ),
    4: Classement(
        4,
        PARTIEL,
        preuve="`T8` — l'UNICITE est acquise : un seul DSM actif par consultant (exclusion)",
        tests=("test_un_consultant_a_un_SEUL_DSM_actif",),
        residuel=(
            "l'EXISTENCE ne l'est pas, et ne peut pas l'etre en base : l'appartenance doit "
            "exister AVANT qu'une affectation DSM ne la reference. Une contrainte a "
            "l'insertion serait circulaire. C'est une regle de PROCESSUS. **`T9` DU "
            "LOT 3 EN COUVRE LA MOITIE UTILE** : quand le DSM d'un consultant part, "
            "`enregistrer_un_depart` NOMME les consultants prives de DSM dans son "
            "resultat. Il ne peut pas designer le remplacant -- decision humaine -- "
            "mais il rend l'etat VISIBLE au lieu de le laisser silencieux. Le residuel "
            "n'est donc plus « rien ne le voit » mais « rien ne le corrige "
            "automatiquement ». **ET `T8` DU LOT 5 EN COUVRE LE SECOND CHEMIN** : une "
            "restauration remet une personne en `active` SANS DSM, et "
            "`restaurer_un_profil` le NOMME dans `relations_a_redonner` — mesure, non "
            "supposee, et seulement si la relation a REELLEMENT existe. Les deux "
            "facons d'atteindre l'etat que le §30.4 interdit sont donc visibles"
        ),
        lot="LOT 7, onboarding — ou un service anterieur",
    ),
    5: Classement(
        5,
        ACQUIS,
        preuve=(
            "`T5` pour l'interdiction — `client_selon_le_statut` impose `client_id IS NULL` "
            "sur `intercontract` — et `T10` pour l'exigence, sur `entity_client` NON ARCHIVEE"
        ),
        tests=(
            "test_une_mission_avec_un_client_NON_ACTIVE_est_refusee",
            "test_un_intercontract_reste_accepte_sans_client",
        ),
    ),
    6: Classement(
        6,
        ACQUIS,
        preuve="`T8` — index partiel du §25.1 sur `(circle_id)` restreint au Booster actif",
        tests=("test_un_cercle_a_un_SEUL_Booster_actif",),
    ),
    7: Classement(
        7,
        ACQUIS,
        preuve="`T8` — declencheur `booster_une_seule_entite`. Voir `ECART-032` sur la PORTEE",
        tests=("test_une_personne_ne_peut_PAS_etre_Booster_dans_DEUX_entites",),
    ),
    8: Classement(
        8,
        INAPPLICABLE,
        residuel=(
            "`ECART-031` — le §8.4 exige « un bureau PUBLIE », mais le §8.3 ne declare AUCUN "
            "etat de publication sur `office`. La condition n'a rien a quoi se rattacher. "
            "Et « entre un et trois » est un comptage borne, qu'aucune contrainte de ligne "
            "n'exprime : il faudra un declencheur le jour ou l'etat existera"
        ),
        lot="a instruire avant le LOT 6",
    ),
    9: Classement(
        9,
        ACQUIS,
        preuve="`T7` — exclusion PARTIELLE, restreinte au type `principal` (`DEC-511`)",
        tests=("test_deux_periodes_de_cercle_PRINCIPAL_qui_se_chevauchent_sont_refusees",),
    ),
    10: Classement(
        10,
        ACQUIS,
        preuve="`T7` — declencheur `circle_archivage_sans_membres_actifs`",
        tests=("test_archiver_un_cercle_a_MEMBRES_ACTIFS_est_refuse",),
    ),
    11: Classement(
        11,
        ACQUIS,
        preuve=(
            "LOT 3 `T3` — le service exige `entity_membership.membership_state = 'active'`, "
            "cahier §7.2. `archived` est l'un des trois etats que ce filtre ecarte, et la "
            "reponse reste IDENTIQUE a celle d'un profil actif : le refus ne se lit pas"
        ),
        tests=(
            "test_un_profil_ARCHIVE_ne_recoit_AUCUN_lien",
            "test_un_profil_ACTIF_recoit_un_lien",
            "test_la_reponse_est_IDENTIQUE_pour_un_profil_archive",
        ),
    ),
    #  **RECLASSE EN `T1` DU LOT 5, ET C'ETAIT UNE ERREUR DE CE SCRIPT.** Il
    #  rattachait ce controle au LOT 8, decrit comme « medias et autorisations de
    #  diffusion ». Or le LOT 8 de la roadmap est **« Evenements et accueil
    #  dynamique »**, et les seuls medias qu'il nomme sont ceux d'un evenement --
    #  « titre, description, lieu, debut, fin et medias ».
    #
    #  C'est le **LOT 5** qui inclut « photo facultative et avatar neutre » ET
    #  « gestion des autorisations de photo » dans ses *Inclus*, avec DEUX criteres
    #  de sortie qui en dependent et `MVP-L05-US005` en **`P0`**.
    #
    #  **Cause : le classement avait ete fait sur la seule lecture du MODELE**,
    #  dont le §16 « Medias » est generique, sans confronter a la ROADMAP qui
    #  repartit ces medias entre deux lots selon leur USAGE. §7.24 -- relire une
    #  regle ne suffit pas, il faut confronter les regles entre elles. `ECART-047`.
    #
    #  **IL ETAIT `REPORTE` AVEC POUR ECHEANCE « LOT 5 `T6` », ET `T6` N'EXISTE
    #  PLUS.** `DEC-564` l'a fusionnee dans `T5` le 06/09/2026, et `T5` a livre le
    #  service. L'echeance a survecu trois jours en nommant une sous-etape morte,
    #  et ce controle passait au vert : il exige que chaque contrôle soit CLASSE,
    #  pas que son echeance designe une sous-etape REELLE. §7.31, encore une fois --
    #  exact pour un mode de defaillance, aveugle a un autre.
    #
    #  **IL EST ACQUIS DEPUIS `T5`**, et les trois tests nommes couvrent les deux
    #  sens : le refus des cinq causes, le temoin positif, et le temoin TEMPOREL ou
    #  seul l'instant avance. `make profil-check` le prouve de plus sur les OCTETS.
    12: Classement(
        12,
        ACQUIS,
        preuve=(
            "LOT 5 `T5` — la resolution de la miniature exige une autorisation ACTIVE "
            "(§12.2), et `null` couvre CINQ causes indistinguables : pas d'autorisation, "
            "retiree, pas encore active, media non `ready`, aucune variante. "
            "`make profil-check` le prouve sur les OCTETS, et son controle 16 exerce "
            "l'autorisation RETIREE."
        ),
        tests=(
            "test_les_cinq_causes_donnent_TOUTES_un_avatar_neutre",
            "test_LE_TEMOIN_la_miniature_autorisee_est_resolue",
            "test_l_autorisation_FUTURE_devient_servable_le_jour_venu",
        ),
    ),
    13: Classement(13, REPORTE, lot="LOT 7 — instances d'onboarding"),
    14: Classement(14, REPORTE, lot="LOT 7 — taches d'onboarding. Voir aussi `ECART-013`"),
    15: Classement(15, REPORTE, lot="LOT 7 — reouverture d'une tache"),
    16: Classement(
        16,
        ACQUIS,
        preuve=(
            "`T11` — les 8 cles etrangeres COMPOSITES du §25.3, et `make isolation-check` "
            "prouve qu'aucune reference locale n'echappe au mecanisme"
        ),
        tests=(
            "test_les_cles_composites_sont_toutes_couvertes",
            "test_un_cercle_d_une_autre_entite_est_refuse",
        ),
    ),
    17: Classement(17, REPORTE, lot="LOT 9 — imports CSV"),
    18: Classement(18, REPORTE, lot="LOT 9 — imports CSV, lignes partiellement valides"),
    19: Classement(19, REPORTE, lot="LOT 10 — jobs et idempotence"),
    20: Classement(20, REPORTE, lot="LOT 12 — `audit_event` et atomicite"),
    21: Classement(21, REPORTE, lot="LOT 12 — purge RGPD"),
    22: Classement(
        22,
        ACQUIS,
        preuve=(
            "LOT 3 `T9` — la revocation tient au DEPART, non au seul archivage : le §24.1 "
            "n'a AUCUNE transition `Active --> Archived`, donc attendre l'archivage "
            "laisserait une fenetre pendant laquelle un partant garde une session, ce que "
            "le §7.4 et le §30.22 interdisent tous deux par le mot « immediatement ». Les "
            "sessions sont revoquees, les liens actifs invalides, et les SIX relations "
            "historisees du §25.2 autres que l'appartenance sont closes — dont les deux "
            "porteuses de roles, ce que « et roles » exige. `make revocation-check` mesure "
            "le 401 par un aller-retour HTTP reel a travers Caddy, et non par la lecture de "
            "`revoked_at` : l'ecriture et le refus sont deux grandeurs differentes"
        ),
        tests=(
            "test_LE_DEPART_revoque_les_sessions",
            "test_UNE_SESSION_REVOQUEE_NE_REPOND_PLUS_mesure_en_HTTP",
            "test_LE_DEPART_D_UN_DG_REUSSIT_malgre_le_declencheur",
            "test_LA_REVOCATION_EST_ATOMIQUE_avec_le_changement_d_etat",
            "test_L_ARCHIVAGE_est_IDEMPOTENT_apres_un_depart",
            "test_UNE_TRANSITION_HORS_24_1_est_REFUSEE",
        ),
    ),
    23: Classement(23, REPORTE, lot="LOT 12 — anonymisation et durees de conservation"),
    24: Classement(24, REPORTE, lot="LOT 11 — exports"),
    25: Classement(
        25,
        ACQUIS,
        preuve="`T12` — jeu de 25 entites et 5 000 profils engendre et MESURE",
        tests=("test_le_jeu_de_recette_reste_exploitable_avec_les_index_definis",),
    ),
}


def elements_du_modele() -> list[tuple[int, str]]:
    """Lire les elements numerotes du §30, dans le modele."""
    texte = MODELE.read_text(encoding="utf-8")
    debut = texte.index("# 30. Contrôles de recette du modèle")
    #  La borne est CHERCHEE, non recopiee : une borne en dur est un
    #  `ECART-021` en puissance, et `T11` en a fait l'experience sur le §3.1.
    suivant = re.search(r"^# \d+\. ", texte[debut + 10 :], re.MULTILINE)
    fin = debut + 10 + suivant.start() if suivant else len(texte)
    bloc = texte[debut:fin]
    return [
        (int(numero), libelle.strip().rstrip(".;"))
        for numero, libelle in re.findall(r"^\s*(\d+)\.\s+(.+?)$", bloc, re.MULTILINE)
    ]


def noms_de_tests() -> set[str]:
    """Tous les noms de fonctions de test du repertoire de tests."""
    noms: set[str] = set()
    for fichier in sorted(TESTS.glob("test_*.py")):
        noms |= set(
            re.findall(r"^def (test_\w+)", fichier.read_text(encoding="utf-8"), re.MULTILINE)
        )
    return noms


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    echecs = 0
    print()
    print("  Controles de recette du modele §30")

    elements = elements_du_modele()
    print(f"    info     {len(elements)} controles enumeres par le §30, LUS dans le modele")

    #  UN CONTROLE MUET DIRAIT « 0 element, tout est classe ».
    if len(elements) < 20:
        print(f"    ECHEC    {len(elements)} elements trouves, la lecture du §30 a echoue")
        return 1

    non_classes = [numero for numero, _ in elements if numero not in CLASSEMENT]
    for numero in non_classes:
        libelle = next(libelle for n, libelle in elements if n == numero)
        print(f"    ECHEC    §30.{numero} n'est pas classe : « {libelle} »")
        echecs += 1
    en_trop = sorted(set(CLASSEMENT) - {numero for numero, _ in elements})
    for numero in en_trop:
        print(f"    ECHEC    §30.{numero} est classe mais absent du modele")
        echecs += 1
    if not non_classes and not en_trop:
        print(f"    ok       les {len(elements)} controles sont classes, aucun en trop")

    tests_existants = noms_de_tests()
    print(f"    info     {len(tests_existants)} fonctions de test dans `apps/api/tests`")

    compteurs = {ACQUIS: 0, PARTIEL: 0, REPORTE: 0, INAPPLICABLE: 0}
    print()
    for numero, libelle in elements:
        classement = CLASSEMENT.get(numero)
        if classement is None:
            continue
        compteurs[classement.statut] += 1
        etiquette = {
            ACQUIS: "ACQUIS      ",
            PARTIEL: "PARTIEL     ",
            REPORTE: "reporte     ",
            INAPPLICABLE: "INAPPLICABLE",
        }[classement.statut]
        print(f"    {etiquette} §30.{numero:<2} {libelle}")
        if classement.preuve:
            print(f"                 preuve   : {classement.preuve}")
        if classement.residuel:
            print(f"                 residuel : {classement.residuel}")
        if classement.lot:
            print(f"                 echeance : {classement.lot}")
        #  UN CLASSEMENT « ACQUIS » SANS TEST EXISTANT NE SERAIT QU'UNE AFFIRMATION.
        for nom in classement.tests:
            if nom not in tests_existants:
                print(f"    ECHEC    §30.{numero} annonce le test `{nom}`, qui n'existe pas")
                echecs += 1
        if classement.statut in (ACQUIS, PARTIEL) and not classement.tests:
            print(f"    ECHEC    §30.{numero} est {classement.statut} sans nommer de test")
            echecs += 1

    print()
    print(
        f"    info     {compteurs[ACQUIS]} acquis · {compteurs[PARTIEL]} partiel · "
        f"{compteurs[REPORTE]} reportes · {compteurs[INAPPLICABLE]} inapplicable"
    )
    total = sum(compteurs.values())
    if total != len(elements):
        print(f"    ECHEC    {total} classements pour {len(elements)} elements")
        echecs += 1

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print(
        f"  --> les {len(elements)} controles du §30 sont classes, "
        f"et chaque acquis nomme un test qui EXISTE"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
