"""Brouillon, publication, archivage, restauration — LOT 6, `T7`, `MVP-L06-US006`.

LE CRITERE A TROIS MEMBRES, ET LE PREMIER EST SATISFAIT PAR UNE ROUTE QUI NE
PUBLIE RIEN

  « Brouillon et publication sont distingues ; la version publiee est
  identifiable ; les modifications sont auditees. »

  **« Distingues » est tenu par une API qui refuserait TOUTE publication** : les
  deux etats resteraient distincts, et rien ne serait prouve. C'est le §7.39.
  Le temoin qui rend le critere non trivial n'est donc pas un refus : c'est
  **une page publiee puis RELUE par la route de `T5`**, qui ne sert que le
  publie. Le couple complet est ici, et il ne differe que par la publication :

      avant publication   `lire_la_page_de_contenu` rend None   (brouillon)
      apres publication   elle rend la page et ses blocs

CE QUE LA SUITE PROUVE DE LA GRILLE, ET ELLE EST ASYMETRIQUE

      action      DSM  ESM         BOOST   OFFICE  ADM-E   SUPER
      Publier     —    Perimetre   Cercle  Bureau  Entite  Global
      Archiver    —    Perimetre   Cercle  Bureau  Entite  Global
      Restaurer   —    Conditio.   **—**   **—**   Entite  Global

  **Le Booster ARCHIVE la page de son cercle et ne la RESTAURE pas**, et trois
  sources concordantes le disent — matrice §13, matrice §18, cahier §10.1. Un
  test mesure les DEUX ensembles exacts sur la meme page, au meme instant, pour
  le meme acteur : seul l'etat de la page change.

LA BORNE DU §8.4, ET CE QU'ELLE NE GARANTIT PAS

  `DEC-583` a renvoye ici le declencheur du comptage borne. Il est pose, et son
  temoin positif est dans cette suite — publier un bureau a un, deux et trois
  responsables reussit ; a zero et a quatre, la base refuse.

  **MAIS IL GARANTIT « ON NE PUBLIE PAS UN BUREAU NON CONFORME », PAS « UN BUREAU
  PUBLIE EST CONFORME ».** Un test le MESURE plutot que de l'affirmer : apres une
  publication conforme, cloturer le seul responsable laisse un bureau publie a
  zero responsable. C'est exactement l'etat que le decor de `T4` fabrique, et
  c'est ce qui prouve que sa lecture tolerante reste NECESSAIRE.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.content.cycle_de_vie import (
    CODE_BORNE_DES_RESPONSABLES,
    ETAT_APRES_RESTAURATION,
    ETAT_ARCHIVE,
    ETAT_PUBLIE,
    archiver_une_page,
    publier_une_page,
    restaurer_une_page,
)
from app.content.ecriture import CODE_SLUG_DEJA_PRIS, CODE_VERSION_OBSOLETE, creer_une_page
from app.content.modeles import EtatDePage
from app.content.pages import lire_la_page_de_contenu
from app.content.perimetre import (
    ACTIONS_DES_PORTEES_LOCALES,
    ACTIONS_DES_ROLES_D_ENTITE,
    ROLES_D_ECRITURE_EDITORIALE,
    ROLES_DE_PORTEE_ENTITE,
    ROLES_DE_RESTAURATION,
    ActionEditoriale,
    _actions_selon_l_etat,
    resoudre_le_perimetre_editorial,
)
from app.content.routes import (
    DemandeDeTransition,
    ReponseDArchivageDUnContenu,
    ReponseDePublication,
    ReponseDeRestaurationDUnContenu,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L6T7"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)

#  **L'ANNEE PROCHAINE, ET LE DECLENCHEUR COMPARE A `now()`.** Une affectation
#  qui commence en 2027 a un `ends_at` nul comme une affectation courante :
#  seule la PLAGE les separe. C'est `ECART-056`, et le temoin ou seul l'instant
#  avance est celui qui a le plus servi au LOT 5.
PLUS_TARD = dt.datetime(2027, 6, 1, tzinfo=dt.UTC)


# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================
def test_la_grille_de_RESTAURATION_est_PLUS_ETROITE_que_celle_de_l_ecriture() -> None:
    """**TROIS SOURCES CONCORDANTES METTENT `BOOST` ET `OFFICE` A TIRET.**

    Matrice §13 « Restaurer », matrice §18 « Restaurer un contenu », cahier §10.1
    « Archiver/restaurer une page ». Reutiliser la grille d'ecriture aurait
    accorde la restauration a deux roles que les trois documents en excluent —
    exactement la faute que `T8` du LOT 5 a evitee sur le §6.1.
    """
    assert ROLES_DE_RESTAURATION < ROLES_D_ECRITURE_EDITORIALE, "strictement incluse"
    assert RoleDeLaMatrice.BOOSTER in ROLES_D_ECRITURE_EDITORIALE
    assert RoleDeLaMatrice.BOOSTER not in ROLES_DE_RESTAURATION
    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU in ROLES_D_ECRITURE_EDITORIALE
    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU not in ROLES_DE_RESTAURATION


def test_la_grille_de_RESTAURATION_coincide_AUJOURD_HUI_avec_celle_de_PORTEE_ENTITE() -> None:
    """**DEUX ENSEMBLES EGAUX POUR DEUX RAISONS DIFFERENTES, ET C'EST MESURE.**

    `ROLES_DE_PORTEE_ENTITE` vaut ces trois roles parce que le §13 n'a qu'une
    ligne de creation ; `ROLES_DE_RESTAURATION` les vaut parce que trois
    documents excluent les portees locales de la restauration. Les aliaser les
    ferait bouger ENSEMBLE le jour ou une seule des deux raisons change.

    Ce test echouera alors, et **c'est son objet** : forcer la decision au lieu
    de la prendre en silence. Un test est un meilleur vehicule qu'un commentaire
    (§7.32).
    """
    assert ROLES_DE_RESTAURATION == ROLES_DE_PORTEE_ENTITE


def test_une_ACTION_NOUVELLE_ne_s_accorde_PAS_d_office_a_une_portee_locale() -> None:
    """**L'UNION DOIT COUVRIR L'ENUMERATION, `CREER` EXCEPTE.**

    `ACTIONS_DES_PORTEES_LOCALES` est ecrit en EXTENSION, la ou
    `TYPES_SANS_PORTEE_LOCALE` l'est par SOUSTRACTION — et les deux partis sont
    justes pour la meme raison. Un TYPE DE PAGE nouveau doit tomber dans le
    regime le plus restrictif, donc par soustraction ; une ACTION nouvelle ne
    doit pas etre accordee d'office a un Booster, donc en extension.

    Ce test echoue au sixieme membre de l'enumeration, ce qui oblige a trancher.
    """
    couvertes = ACTIONS_DES_PORTEES_LOCALES | {ActionEditoriale.RESTAURER}
    assert couvertes == frozenset(ActionEditoriale) - {ActionEditoriale.CREER}
    assert ActionEditoriale.RESTAURER not in ACTIONS_DES_PORTEES_LOCALES
    assert ActionEditoriale.CREER not in ACTIONS_DES_ROLES_D_ENTITE, (
        "creer ne porte sur aucune page existante — `peut_creer_une_page` y repond"
    )


def test_la_MACHINE_A_ETATS_n_offre_AUCUNE_depublication() -> None:
    """**LE §13 N'A PAS DE LIGNE « DEPUBLIER », ET L'INVENTER SERAIT LE §6.5.**

    Trois lignes : « Publier immediatement », « Archiver », « Restaurer ». Une
    page publiee ne redevient donc pas un brouillon : on l'archive. Et publier
    n'est offert qu'a un BROUILLON — republier ecraserait `published_at`, soit
    la date meme que `US006` demande d'identifier.
    """
    brouillon = _actions_selon_l_etat(etat=EtatDePage.DRAFT.value, archivee=False)
    publiee = _actions_selon_l_etat(etat=EtatDePage.PUBLISHED.value, archivee=False)
    archivee = _actions_selon_l_etat(etat=EtatDePage.ARCHIVED.value, archivee=True)

    assert brouillon == {
        ActionEditoriale.MODIFIER,
        ActionEditoriale.PUBLIER,
        ActionEditoriale.ARCHIVER,
    }
    assert publiee == {ActionEditoriale.MODIFIER, ActionEditoriale.ARCHIVER}
    assert ActionEditoriale.PUBLIER not in publiee, "republier ecraserait la date de publication"
    assert archivee == {ActionEditoriale.RESTAURER}


def test_les_deux_DIVERGENCES_entre_state_et_archived_at_se_lisent_au_plus_RESTRICTIF() -> None:
    """**LE CORPUS NE LIE PAS CES DEUX COLONNES, ET LE DECOR DE `T4` LES DISSOCIE.**

    Le §15.1 declare `state` a trois valeurs dont `archived` ; le §3.1 declare
    `archived_at` sur toute table metier. Aucune contrainte ne les couple, et en
    poser une rendrait impossibles les deux cas que `T4` fabrique deliberement
    pour prouver que sa lecture de `publie` est exacte (§7.41).

    Les deux divergences se lisent donc, et dans le sens le plus restrictif.
    """
    #  `state = archived` SANS `archived_at` : pas archivee comme ressource.
    assert _actions_selon_l_etat(etat=EtatDePage.ARCHIVED.value, archivee=False) == {
        ActionEditoriale.MODIFIER,
        ActionEditoriale.ARCHIVER,
    }
    #  `state = published` AVEC `archived_at` : archivee, donc restaurable seule.
    assert _actions_selon_l_etat(etat=EtatDePage.PUBLISHED.value, archivee=True) == {
        ActionEditoriale.RESTAURER
    }


def test_la_DEMANDE_ne_porte_QUE_la_version() -> None:
    """**NI ETAT CIBLE, NI MOTIF, ET LES DEUX ABSENCES SONT RAISONNEES.**

    Un champ `etat` laisserait croire a une machine a etats pilotee par
    l'appelant : l'etat cible est porte par la ROUTE, si bien que les transitions
    que le §13 n'ecrit pas sont **inexprimables** plutot que refusees (§7.35).

    Un champ `motif` contredirait le §18.1, qui enumere cinq cas ou un motif est
    obligatoire — et archiver un contenu n'en est pas un.
    """
    assert set(DemandeDeTransition.model_fields) == {"version"}


def test_les_TROIS_REPONSES_rendent_l_etat_plutot_que_de_le_laisser_deduire() -> None:
    """Un appelant LIT l'etat obtenu, au lieu de le deduire de la documentation.

    C'est le meme parti que `ReponseDeCreationDePage.etat` de `T6` : une mesure
    plutot qu'une promesse.
    """
    for modele in (
        ReponseDePublication,
        ReponseDArchivageDUnContenu,
        ReponseDeRestaurationDUnContenu,
    ):
        assert "etat" in modele.model_fields, modele.__name__
    #  `publiee_le` survit a l'archivage ET a la restauration : la page A ETE
    #  publiee ce jour-la, et l'effacer detruirait un fait.
    assert "publiee_le" in ReponseDArchivageDUnContenu.model_fields
    assert "publiee_le" in ReponseDeRestaurationDUnContenu.model_fields


def test_les_TROIS_ETATS_sont_DERIVES_de_l_enumeration() -> None:
    """`DEC-544` — jamais une chaine ecrite en dur."""
    assert ETAT_PUBLIE == EtatDePage.PUBLISHED.value == "published"
    assert ETAT_ARCHIVE == EtatDePage.ARCHIVED.value == "archived"
    assert ETAT_APRES_RESTAURATION == EtatDePage.DRAFT.value == "draft"


MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def test_le_MANIFESTE_declare_la_grille_de_restauration_SEPAREMENT() -> None:
    """**TROISIEME GRILLE DECLAREE SEPAREMENT, ET LA PREUVE QU'ELLE EST DISTINCTE
    EST IMMEDIATE.**

    `rolesRestaurationDUnContenu` porte les memes trois roles que
    `rolesCycleDeVie` et que `rolesAdministration`. C'est encore une coincidence :
    le premier vient des lignes de restauration du §13, du §18 et du cahier
    §10.1, qui portent sur un CONTENU ; le deuxieme des lignes d'archivage du
    §6.1, qui portent sur un PROFIL ; le troisieme du §20.

    **ET ELLES NE SONT PAS LA MEME GRILLE**, ce qui se voit sans attendre qu'elles
    divergent : sur un CONTENU, `BOOST` et `OFFICE` **archivent** -- ce que le
    §6.1 leur refuse sur un profil -- et pourtant ils ne **restaurent** pas.

    Le manifeste est la source unique de `DEC-492`, lue par TypeScript et par
    Python, et l'egalite est exigee **dans les deux sens**.
    """
    manifeste = json.loads(
        (pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT).read_text(
            encoding="utf-8"
        )
    )
    codes = manifeste["rolesRestaurationDUnContenu"]
    assert codes, "le manifeste ne declare aucun role de restauration de contenu"
    #  La conversion ajoute une exigence utile : un code qui ne serait pas un role
    #  connu leve ICI, au lieu de rendre l'ecran inerte en silence.
    assert {RoleDeLaMatrice(code) for code in codes} == ROLES_DE_RESTAURATION

    #  **LES TROIS GRILLES RESTENT TROIS DECLARATIONS.** Fusionner deux cles
    #  ferait echouer ici, avant qu'un changement de l'une n'entraine l'autre.
    for cle in ("rolesAdministration", "rolesCycleDeVie", "rolesRestaurationDUnContenu"):
        assert cle in manifeste, cle


def test_le_MANIFESTE_porte_les_TROIS_chemins_du_cycle() -> None:
    """Les trois routes de `T7`, avec leurs codes exploitables.

    **`409` EST DANS LES TROIS**, et ce n'est pas decoratif : c'est la
    concurrence optimiste du §18.4, plus la borne du §8.4 a la publication et le
    slug repris a la restauration. Un ecran qui ne saurait pas qu'un 409 est
    possible traiterait un conflit legitime comme une panne.
    """
    manifeste = json.loads(
        (pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT).read_text(
            encoding="utf-8"
        )
    )
    par_cle = {e["cle"]: e for e in manifeste["endpoints"]}
    for cle, fin in (
        ("publicationDUnePageDeContenu", "publication"),
        ("archivageDUnePageDeContenu", "archivage"),
        ("restaurationDUnePageDeContenu", "restauration"),
    ):
        point = par_cle[cle]
        assert point["chemin"] == f"/api/v1/entities/{{code}}/pages/{{page}}/{fin}"
        assert point["methode"] == "post"
        assert 409 in point["codesExploitables"], cle


# ============================================================================
#  2. Integration
# ============================================================================
def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"{MARQUEUR}{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR}-{suffixe}@exemple.test".lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, :prenom, :nom, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "prenom": suffixe, "nom": MARQUEUR},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_de_responsabilite: str,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, office_id, "
            " assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :cercle, :bureau, :par, :debut) RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "type": type_de_responsabilite,
            "cercle": cercle,
            "bureau": bureau,
            "par": personne,
            "debut": debut,
        },
    ).scalar_one()


def _page(
    cx: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    *,
    type_de_page: str = "HOME",
    slug: str = "accueil",
    cercle: str | None = None,
    bureau: str | None = None,
) -> uuid.UUID:
    return creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page=type_de_page,
        titre=slug,
        slug=slug,
        code_de_cercle=cercle,
        code_de_bureau=bureau,
        instant=JANVIER,
    ).identifiant


def _etat_en_base(cx: Connection, page: uuid.UUID) -> tuple[str, object, object, int]:
    ligne = cx.execute(
        text("SELECT state, published_at, archived_at, version FROM content_page WHERE id = :p"),
        {"p": page},
    ).one()
    return str(ligne[0]), ligne[1], ligne[2], int(ligne[3])


def _perimetre(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    page: uuid.UUID,
    roles: set[RoleDeLaMatrice],
) -> frozenset[ActionEditoriale]:
    return resoudre_le_perimetre_editorial(
        cx,
        entite=entite,
        acteur=acteur,
        page=page,
        roles=frozenset(roles),
        instant=DEMAIN,
    ).actions


# ---------------------------------------------------------------- le temoin
@pytest.mark.integration
def test_LE_TEMOIN_publier_rend_la_page_SERVIE_par_la_lecture_de_T5(cx: Connection) -> None:
    """**LE COUPLE QUI REND LE CRITERE NON TRIVIAL, ET IL NE DIFFERE QUE PAR LA
    PUBLICATION.**

    « Brouillon et publication sont distingues » est satisfait par une API qui ne
    publie rien du tout. Ce qui le prouve est qu'une page devienne SERVIE — et
    c'est la route de `T5`, ecrite avant et sans rapport, qui rend le verdict.
    """
    entite = _entite(cx, "PUB")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="accueil")

    avant = lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="accueil")
    assert avant is None, "un BROUILLON n'est pas servi — c'est le 404 de `T5`"

    publiee = publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    assert publiee.etat == ETAT_PUBLIE
    assert publiee.publiee_le == DEMAIN
    assert publiee.version == 2, "publier est une ecriture — §18.4"

    apres = lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="accueil")
    assert apres is not None, "LE TEMOIN : la meme page, servie"
    assert apres.titre == "accueil"


@pytest.mark.integration
def test_publier_ecrit_state_ET_published_at_ET_l_auteur(cx: Connection) -> None:
    """`US006`, « la version publiee est identifiable » — la version ET la date."""
    entite = _entite(cx, "IDENT")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="ident")

    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    etat, publiee_le, archivee_le, version = _etat_en_base(cx, page)
    assert (etat, publiee_le, archivee_le, version) == (ETAT_PUBLIE, DEMAIN, None, 2)
    auteur = cx.execute(
        text("SELECT updated_by_person_id FROM content_page WHERE id = :p"), {"p": page}
    ).scalar_one()
    assert auteur == acteur, "la seule trace disponible tant qu'`audit_event` est au LOT 10"


@pytest.mark.integration
def test_REPUBLIER_est_refuse_par_le_perimetre_et_la_date_ne_bouge_PAS(cx: Connection) -> None:
    """**ECRASER `published_at` DETRUIRAIT LA DONNEE QUE `US006` DEMANDE.**

    Le refus est porte par l'etat, pas par le role : le meme ESM, la meme page,
    et la seule chose qui a change est qu'elle est deja publiee.
    """
    entite = _entite(cx, "REPUB")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="repub")
    roles = {RoleDeLaMatrice.ESM}

    assert ActionEditoriale.PUBLIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles=roles
    ), "TEMOIN AVANT : le brouillon est publiable"

    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    apres = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles)
    assert apres == {ActionEditoriale.MODIFIER, ActionEditoriale.ARCHIVER}
    assert ActionEditoriale.PUBLIER not in apres


@pytest.mark.integration
def test_archiver_ecrit_les_DEUX_colonnes_et_CONSERVE_la_date_de_publication(
    cx: Connection,
) -> None:
    """**`state` ET `archived_at` DANS LE MEME `UPDATE`** — ils ne peuvent pas diverger.

    Et `published_at` SURVIT : la page a ete publiee ce jour-la, et l'archiver
    n'efface pas ce fait.
    """
    entite = _entite(cx, "ARCH")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="arch")

    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    archivee = archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=2, instant=DEMAIN
    )

    assert archivee.etat == ETAT_ARCHIVE
    assert archivee.archivee_le == DEMAIN
    assert archivee.publiee_le == JANVIER, "la date de publication SURVIT a l'archivage"

    etat, publiee_le, archivee_le, _ = _etat_en_base(cx, page)
    assert etat == ETAT_ARCHIVE, "`state` est ecrit"
    assert archivee_le == DEMAIN, "`archived_at` aussi, dans le MEME UPDATE"
    assert publiee_le == JANVIER

    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="arch") is None


@pytest.mark.integration
def test_archiver_un_BROUILLON_rend_une_date_de_publication_NULLE(cx: Connection) -> None:
    """Deux histoires differentes, deux valeurs differentes — et `null` les separe."""
    entite = _entite(cx, "ARCHD")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="archd")

    archivee = archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    assert archivee.publiee_le is None, "elle n'a jamais ete publiee, et la reponse le DIT"


@pytest.mark.integration
def test_archiver_ecrit_l_ARCHIVEUR_et_laisse_le_motif_NUL(cx: Connection) -> None:
    """**AUCUN MOTIF, ET LE §18.1 EN DONNE LA RAISON.**

    Il enumere cinq cas ou un motif est obligatoire ; archiver un contenu n'y est
    pas. `archive_reason` reste donc nulle — et elle l'est dans TOUT ce depot,
    ce qui est mesure par `ECART-064` plutot que tu.
    """
    entite = _entite(cx, "MOTIF")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="motif")

    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    par, motif = cx.execute(
        text("SELECT archived_by_person_id, archive_reason FROM content_page WHERE id = :p"),
        {"p": page},
    ).one()
    assert par == acteur
    assert motif is None


@pytest.mark.integration
def test_LE_CYCLE_COMPLET_et_la_restauration_ne_REPUBLIE_PAS(cx: Connection) -> None:
    """**LE TEST LE PLUS UTILE DE LA SUITE : restaurer n'est pas publier.**

    Apres restauration la page est vivante — donc modifiable, publiable — et
    pourtant **toujours pas servie**. C'est `RIGHTS-001`, « toute permission est
    refusee par defaut si elle n'est pas explicitement accordee » : une page
    redevenue visible sans que personne ne l'ait publiee serait une publication
    que personne n'a decidee.

    Puis le second geste, explicite, la ressert. Sans ce dernier temoin, le
    refus mesure plus haut pourrait venir de n'importe quel defaut.
    """
    entite = _entite(cx, "CYCLE")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="cycle")

    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="cycle")

    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=2, instant=DEMAIN
    )
    restauree = restaurer_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=3, instant=DEMAIN
    )

    assert restauree.etat == ETAT_APRES_RESTAURATION == EtatDePage.DRAFT.value
    assert restauree.publiee_le == JANVIER, "la date de publication survit a la restauration"
    etat, _, archivee_le, version = _etat_en_base(cx, page)
    assert (etat, archivee_le, version) == (EtatDePage.DRAFT.value, None, 4)

    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="cycle") is None, (
        "RESTAUREE N'EST PAS PUBLIEE — c'est le point de tout ce test"
    )

    #  LE TEMOIN : le second geste, explicite, la ressert.
    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=4, instant=DEMAIN
    )
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="cycle")


@pytest.mark.integration
def test_le_BOOSTER_archive_la_page_de_SON_cercle_et_ne_la_RESTAURE_PAS(cx: Connection) -> None:
    """**LA GRILLE ASYMETRIQUE, MESUREE SUR LA MEME PAGE ET LE MEME ACTEUR.**

    Seul l'etat de la page change entre les deux relevees. Sans ce couple, le
    refus de restauration pourrait venir du cercle, de l'instant, ou du role.
    """
    entite = _entite(cx, "BOOST")
    acteur = _personne(cx, "boost")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C")
    _responsabilite(
        cx, entite=entite, personne=acteur, type_de_responsabilite="BOOSTER", cercle=cercle
    )
    page = _page(cx, entite, acteur, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")
    roles = {RoleDeLaMatrice.BOOSTER}

    avant = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles)
    assert avant == {
        ActionEditoriale.MODIFIER,
        ActionEditoriale.PUBLIER,
        ActionEditoriale.ARCHIVER,
    }, "il publie et il archive SA page — §13, cellule `Cercle`"

    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    apres = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles)
    assert apres == frozenset(), (
        "LA MEME PAGE, LE MEME ACTEUR : archivee, elle n'offre que `RESTAURER`, "
        "que sa portee locale ne porte pas — §13, §18 et cahier §10.1 concordent"
    )


@pytest.mark.integration
def test_l_ESM_RESTAURE_la_page_que_le_BOOSTER_a_archivee(cx: Connection) -> None:
    """**LE TEMOIN POSITIF DU REFUS PRECEDENT**, et il ne differe que par le ROLE.

    Sans lui, « le Booster ne restaure pas » serait satisfait par une
    restauration cassee pour tout le monde — c'est le §7.39, et c'est la faute
    que les huit refus du defaut `T2-3` du LOT 5 laissaient passer.
    """
    entite = _entite(cx, "ESMR")
    boosteur = _personne(cx, "b")
    esm = _personne(cx, "e")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C")
    _responsabilite(
        cx, entite=entite, personne=boosteur, type_de_responsabilite="BOOSTER", cercle=cercle
    )
    page = _page(cx, entite, boosteur, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")

    archiver_une_page(
        cx, entite=entite, page=page, acteur=boosteur, version_attendue=1, instant=DEMAIN
    )

    assert _perimetre(cx, entite=entite, acteur=esm, page=page, roles={RoleDeLaMatrice.ESM}) == {
        ActionEditoriale.RESTAURER
    }
    restauree = restaurer_une_page(
        cx, entite=entite, page=page, acteur=esm, version_attendue=2, instant=DEMAIN
    )
    assert restauree.etat == EtatDePage.DRAFT.value


@pytest.mark.integration
def test_le_responsable_de_BUREAU_publie_son_bureau_et_ne_le_RESTAURE_PAS(
    cx: Connection,
) -> None:
    """Le §13 donne `Bureau` a `OFFICE` sur « Publier » et « Archiver », tiret sur
    « Restaurer ». La symetrie avec le Booster est exigee, pas supposee."""
    entite = _entite(cx, "OFF")
    acteur = _personne(cx, "off")
    bureau = _bureau(cx, entite, f"{MARQUEUR}-B")
    _responsabilite(
        cx, entite=entite, personne=acteur, type_de_responsabilite="OFFICE_MANAGER", bureau=bureau
    )
    page = _page(cx, entite, acteur, type_de_page="OFFICE", slug="b", bureau=f"{MARQUEUR}-B")
    roles = {RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}

    assert ActionEditoriale.PUBLIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles=roles
    )
    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    assert _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles) == frozenset()


@pytest.mark.integration
def test_un_DSM_ne_PUBLIE_ni_n_ARCHIVE_rien_et_le_temoin_est_ESM_sur_la_MEME_page(
    cx: Connection,
) -> None:
    """**`ECART-063` TRANCHE : le §13 met le `DSM` a tiret, et le §18 lui donne
    « Perimetre ».**

    Le §3 definit son perimetre comme « ses **consultants** dans son entite »,
    donc un ensemble de personnes — et `content_page` ne porte aucune colonne qui
    rattache une page a un DSM. La cellule du §18 n'est pas implementable sans
    inventer un rattachement (§6.5), et le cahier §10.1 met lui aussi le DSM a
    tiret sur « Archiver/restaurer une page ».
    """
    entite = _entite(cx, "DSM")
    dsm = _personne(cx, "dsm")
    esm = _personne(cx, "esm")
    page = _page(cx, entite, esm, slug="dsm")

    assert (
        _perimetre(cx, entite=entite, acteur=dsm, page=page, roles={RoleDeLaMatrice.DSM})
        == frozenset()
    )
    #  LE TEMOIN, sur la MEME page et au MEME instant : seul le role change.
    assert ActionEditoriale.PUBLIER in _perimetre(
        cx, entite=entite, acteur=esm, page=page, roles={RoleDeLaMatrice.ESM}
    )


@pytest.mark.integration
def test_une_page_d_une_AUTRE_entite_est_refusee_MEME_au_SUPER_ADMINISTRATEUR(
    cx: Connection,
) -> None:
    """§25.3, le cloisonnement, et il ne s'ouvre pour personne."""
    entite = _entite(cx, "ICI")
    autre = _entite(cx, "LA")
    acteur = _personne(cx, "super")
    page = _page(cx, entite, acteur, slug="ici")
    roles = {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}

    assert ActionEditoriale.PUBLIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles=roles
    ), "TEMOIN : dans son entite, il publie"
    assert _perimetre(cx, entite=autre, acteur=acteur, page=page, roles=roles) == frozenset()


# ------------------------------------------- la concurrence optimiste, §18.4
@pytest.mark.parametrize(
    "acte",
    [publier_une_page, archiver_une_page],
    ids=["publier", "archiver"],
)
@pytest.mark.integration
def test_une_VERSION_OBSOLETE_refuse_et_N_ECRIT_RIEN(cx: Connection, acte: object) -> None:
    """§18.4, « sans ecrasement silencieux » — et l'etat est relu APRES le refus.

    Un 409 qui aurait deja ecrit serait pire qu'une absence de verrou : il
    laisserait croire que rien n'a bouge.
    """
    entite = _entite(cx, "VERS")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="vers")
    avant = _etat_en_base(cx, page)

    with pytest.raises(ErreurApplicative) as capture:
        acte(  # type: ignore[operator]
            cx, entite=entite, page=page, acteur=acteur, version_attendue=99, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE
    assert capture.value.details == {"version_actuelle": 1}
    assert _etat_en_base(cx, page) == avant, "RIEN n'a ete ecrit"


@pytest.mark.integration
def test_RESTAURER_une_page_VIVANTE_est_refuse_par_sa_propre_precondition(
    cx: Connection,
) -> None:
    """Chaque service porte sa precondition dans son `WHERE` — idiome de `T6`.

    Le perimetre a deja refuse en 403 ; ce filtre-ci couvre la fenetre entre la
    resolution et l'ecriture, et il rend un `version_obsolete` parce que le
    DROIT, lui, etait bien la.
    """
    entite = _entite(cx, "VIV")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="viv")

    with pytest.raises(ErreurApplicative) as capture:
        restaurer_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE


# ------------------------- les preconditions du SERVICE, sans passer par la route
#
#  **CINQ FILTRES ETAIENT MUETS A LA PREMIERE CAMPAGNE DE TEMOINS, ET LES CINQ
#  ETAIENT DE VRAIS TROUS.** Les retirer un par un ne faisait tomber aucun test :
#  tous mes autres cas passent par `resoudre_le_perimetre_editorial`, qui refuse
#  deja la transition en 403 — si bien que la precondition du SERVICE n'etait
#  exercee par personne.
#
#  **CE N'EST PAS UNE REDONDANCE, ET LE MOTIF EST CELUI DE `T2` DU LOT 5** : ces
#  fonctions sont appelables hors HTTP — un export, un script de reprise, une
#  tache de maintenance — et une precondition qui ne vivrait que dans la route
#  rendrait la regle **dependante de son appelant**. Elles couvrent en outre la
#  fenetre entre la resolution du perimetre et l'ecriture, ou un autre acteur a
#  pu agir.
#
#  Les quatre tests ci-dessous court-circuitent donc le perimetre et appellent le
#  service directement. Ils sont ce qui rend les filtres non muets.
@pytest.mark.integration
def test_le_SERVICE_refuse_de_publier_une_page_ARCHIVEE(cx: Connection) -> None:
    """`_PAGE_A_PUBLIER` porte `archived_at IS NULL` — et c'est lui qui refuse."""
    entite = _entite(cx, "SPA")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="spa")
    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=2, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_le_SERVICE_refuse_de_publier_une_page_ARCHIVEE_RESTEE_EN_BROUILLON(
    cx: Connection,
) -> None:
    """**LE TEMOIN QUI REND `archived_at IS NULL` NON MUET, ET IL A FALLU LE
    CHERCHER.**

    La campagne de temoins a d'abord declare ce filtre muet : le retirer laisse
    `state = :etat_attendu`, et une page archivee PAR LE SERVICE porte
    `state = 'archived'`, donc le filtre d'etat suffisait deja.

    **Mais les deux colonnes peuvent diverger**, et pas par accident : `T7` a
    refuse de poser une contrainte qui les couplerait, parce que le corpus ne
    l'ecrit pas et que le decor de `T4` fabrique deliberement les deux
    divergences (§6.5, §7.41). Une page `draft` portant `archived_at` est donc un
    etat REEL de cette base — et sans ce filtre, elle serait publiable.

    C'est le §7.44 : un filtre muet n'est pas forcement redondant, il peut n'avoir
    aucun temoin. Ici il en manquait un, et le voici.
    """
    entite = _entite(cx, "DIVERG")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="diverg")

    #  L'etat divergent, pose comme la base le permet : archivee comme RESSOURCE,
    #  et restee `draft` comme ETAT editorial.
    cx.execute(
        text("UPDATE content_page SET archived_at = :instant WHERE id = :p"),
        {"instant": JANVIER, "p": page},
    )
    etat, _, archivee_le, _ = _etat_en_base(cx, page)
    assert (etat, archivee_le) == (EtatDePage.DRAFT.value, JANVIER), "l'etat divergent EXISTE"

    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE, (
        "`archived_at IS NULL` refuse, la ou le filtre d'etat aurait laisse passer"
    )


@pytest.mark.integration
def test_le_SERVICE_refuse_de_publier_une_page_DEJA_PUBLIEE(cx: Connection) -> None:
    """`state = :etat_attendu` — republier ecraserait `published_at`.

    Le TEMOIN est dans le meme test : la premiere publication, elle, passe.
    """
    entite = _entite(cx, "SPP")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="spp")
    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=JANVIER
    )

    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=2, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE
    _, publiee_le, _, _ = _etat_en_base(cx, page)
    assert publiee_le == JANVIER, "la date de la PREMIERE publication n'a pas bouge"


@pytest.mark.integration
def test_le_SERVICE_refuse_une_page_d_une_AUTRE_entite(cx: Connection) -> None:
    """`entity_id = :entite` — le cloisonnement du §25.3, dans le service lui-meme.

    Sans ce filtre, une page serait publiable par le chemin d'une autre entite
    des lors que le perimetre aurait ete resolu ailleurs.
    """
    entite = _entite(cx, "SCI")
    autre = _entite(cx, "SLA")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="sci")

    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=autre, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE
    etat, _, _, version = _etat_en_base(cx, page)
    assert (etat, version) == (EtatDePage.DRAFT.value, 1), "la page de l'autre entite est intacte"


@pytest.mark.integration
def test_le_SERVICE_refuse_d_ARCHIVER_une_page_DEJA_ARCHIVEE(cx: Connection) -> None:
    """`_PAGE_A_ARCHIVER` porte `archived_at IS NULL` — archiver n'est pas idempotent.

    Le laisser passer ecraserait `archived_at` et `archived_by_person_id`, donc
    **qui** a archive et **quand** — la seule trace disponible tant qu'`audit_event`
    est au LOT 10.
    """
    entite = _entite(cx, "SAA")
    premier = _personne(cx, "un")
    second = _personne(cx, "deux")
    page = _page(cx, entite, premier, slug="saa")
    archiver_une_page(
        cx, entite=entite, page=page, acteur=premier, version_attendue=1, instant=JANVIER
    )

    with pytest.raises(ErreurApplicative) as capture:
        archiver_une_page(
            cx, entite=entite, page=page, acteur=second, version_attendue=2, instant=DEMAIN
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE
    par, quand = cx.execute(
        text("SELECT archived_by_person_id, archived_at FROM content_page WHERE id = :p"),
        {"p": page},
    ).one()
    assert (par, quand) == (premier, JANVIER), "le PREMIER archiveur et sa date sont intacts"


@pytest.mark.integration
def test_restaurer_ne_EFFACE_PAS_SEULEMENT_la_date_mais_AUSSI_l_archiveur(
    cx: Connection,
) -> None:
    """`archived_by_person_id = NULL` dans le MEME `UPDATE` que `archived_at`.

    Laisser l'archiveur sur une page vivante donnerait une trace qui affirme un
    fait faux : « archivee par X », sur une page qui ne l'est plus.
    """
    entite = _entite(cx, "RARCH")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="rarch")
    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    avant = cx.execute(
        text("SELECT archived_by_person_id FROM content_page WHERE id = :p"), {"p": page}
    ).scalar_one()
    assert avant == acteur, "TEMOIN : l'archiveur est bien pose"

    restaurer_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=2, instant=DEMAIN
    )
    par, quand = cx.execute(
        text("SELECT archived_by_person_id, archived_at FROM content_page WHERE id = :p"),
        {"p": page},
    ).one()
    assert (par, quand) == (None, None), "les DEUX colonnes sont effacees ensemble"


@pytest.mark.integration
def test_restaurer_est_REFUSE_si_le_slug_a_ete_REPRIS_pendant_l_archivage(
    cx: Connection,
) -> None:
    """**L'ARCHIVAGE LIBERE LE SLUG, ET C'EST L'INDEX PARTIEL DE `T1` QUI LE FAIT.**

    `uq_content_page_entity_type_slug_non_archive ... WHERE archived_at IS NULL`.
    La consequence est mesuree, pas supposee : une page neuve reprend le slug, et
    c'est la RESTAURATION qui se trouve refusee — jamais l'archivage.
    """
    entite = _entite(cx, "SLUG")
    acteur = _personne(cx, "esm")
    ancienne = _page(cx, entite, acteur, slug="partage")

    archiver_une_page(
        cx, entite=entite, page=ancienne, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    #  LE TEMOIN : le slug est bien LIBERE, sinon cette creation echouerait.
    _page(cx, entite, acteur, slug="partage")

    with pytest.raises(ErreurApplicative) as capture:
        restaurer_une_page(
            cx, entite=entite, page=ancienne, acteur=acteur, version_attendue=2, instant=DEMAIN
        )
    assert capture.value.code == CODE_SLUG_DEJA_PRIS


# --------------------------------------- la borne du §8.4, declencheur `0018`
def _bureau_publiable(
    cx: Connection, suffixe: str, responsables: int
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    entite = _entite(cx, suffixe)
    acteur = _personne(cx, f"{suffixe}-esm")
    bureau = _bureau(cx, entite, f"{MARQUEUR}-B")
    for rang in range(responsables):
        personne = _personne(cx, f"{suffixe}-r{rang}")
        _responsabilite(
            cx,
            entite=entite,
            personne=personne,
            type_de_responsabilite="OFFICE_MANAGER",
            bureau=bureau,
        )
    page = _page(cx, entite, acteur, type_de_page="OFFICE", slug="b", bureau=f"{MARQUEUR}-B")
    return entite, acteur, page


@pytest.mark.parametrize("responsables", [1, 2, 3], ids=["un", "deux", "trois"])
@pytest.mark.integration
def test_LE_TEMOIN_un_bureau_a_un_deux_ou_trois_responsables_SE_PUBLIE(
    cx: Connection, responsables: int
) -> None:
    """**LE TEMOIN POSITIF DE LA BORNE, ET IL PORTE SUR LES TROIS VALEURS.**

    Un declencheur qui refuserait TOUT satisferait les deux refus ci-dessous. Et
    le temoin devait porter sur les trois valeurs, pas sur une : c'est la lecon
    du defaut `T2-3` du LOT 5, ou huit refus restaient verts parce que la route
    refusait les trois tailles valides.
    """
    entite, acteur, page = _bureau_publiable(cx, f"B{responsables}", responsables)
    publiee = publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    assert publiee.etat == ETAT_PUBLIE


@pytest.mark.parametrize("responsables", [0, 4], ids=["zero", "quatre"])
@pytest.mark.integration
def test_un_bureau_HORS_BORNE_ne_se_publie_PAS(cx: Connection, responsables: int) -> None:
    """Modele §8.4, « entre un et trois responsables actifs lorsqu'il est publie ».

    **C'est le SEUL geste du projet qui fasse mordre cette borne** — `DEC-583`.
    """
    entite, acteur, page = _bureau_publiable(cx, f"H{responsables}", responsables)
    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
        )
    assert capture.value.code == CODE_BORNE_DES_RESPONSABLES


@pytest.mark.integration
def test_une_responsabilite_FUTURE_ne_compte_PAS_dans_la_borne(cx: Connection) -> None:
    """**`period @> now()`, JAMAIS `ends_at IS NULL`** — `ECART-056`.

    Une affectation qui commence l'an prochain a elle aussi un `ends_at` nul. La
    compter comme active publierait un bureau que personne ne dirige encore.
    """
    entite = _entite(cx, "FUT")
    acteur = _personne(cx, "fut-esm")
    bureau = _bureau(cx, entite, f"{MARQUEUR}-B")
    futur = _personne(cx, "fut-r")
    _responsabilite(
        cx,
        entite=entite,
        personne=futur,
        type_de_responsabilite="OFFICE_MANAGER",
        bureau=bureau,
        debut=PLUS_TARD,
    )
    page = _page(cx, entite, acteur, type_de_page="OFFICE", slug="b", bureau=f"{MARQUEUR}-B")

    with pytest.raises(ErreurApplicative) as capture:
        publier_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
        )
    assert capture.value.code == CODE_BORNE_DES_RESPONSABLES


@pytest.mark.integration
def test_la_borne_ne_mord_PAS_sur_un_AUTRE_type_de_page(cx: Connection) -> None:
    """Le discriminant du declencheur est `page_type = 'OFFICE'`.

    Sans ce test, un declencheur qui refuserait toute publication passerait les
    deux refus ci-dessus — §7.0, quatrieme proposition.
    """
    entite = _entite(cx, "AUTRE")
    acteur = _personne(cx, "autre-esm")
    _bureau(cx, entite, f"{MARQUEUR}-B")
    page = _page(cx, entite, acteur, type_de_page="HOME", slug="accueil")

    publiee = publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    assert publiee.etat == ETAT_PUBLIE


@pytest.mark.integration
def test_LA_BORNE_NE_GARANTIT_PAS_qu_un_bureau_publie_RESTE_conforme(cx: Connection) -> None:
    """**CE QUE LE DECLENCHEUR NE FAIT PAS, MESURE PLUTOT QU'AFFIRME (§7.20).**

    Il garde la TRANSITION vers `published`, comme
    `circle_archivage_sans_membres_actifs` garde celle vers `archived` depuis le
    LOT 2. Il ne garde pas l'etat permanent : cloturer le seul responsable APRES
    la publication laisse un bureau publie a zero responsable.

    **C'EST PRECISEMENT L'ETAT QUE LE DECOR DE `T4` FABRIQUE**, et ce test prouve
    que sa lecture tolerante reste NECESSAIRE — le declencheur ne la rend pas
    obsolete, il explique pourquoi elle existe. `ARB-DROIT-002` reserve
    l'affectation des responsables a l'ESM et au super-administrateur, et **aucune
    route du LOT 6 ne l'ecrit** : garder cet autre cote appartient au lot qui la
    servira.
    """
    entite, acteur, page = _bureau_publiable(cx, "RESTE", 1)
    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    cx.execute(
        text(
            "UPDATE framework_responsibility_assignment SET ends_at = now() "
            "WHERE entity_id = :e AND responsibility_type = 'OFFICE_MANAGER'"
        ),
        {"e": entite},
    )

    actifs = cx.execute(
        text(
            "SELECT count(*) FROM framework_responsibility_assignment "
            "WHERE entity_id = :e AND responsibility_type = 'OFFICE_MANAGER' "
            "  AND archived_at IS NULL AND period @> now()"
        ),
        {"e": entite},
    ).scalar_one()
    etat, _, _, _ = _etat_en_base(cx, page)
    assert (etat, actifs) == (ETAT_PUBLIE, 0), (
        "un bureau PUBLIE a ZERO responsable est ATTEIGNABLE — la lecture de `T4` "
        "doit continuer de le rendre tel quel"
    )
