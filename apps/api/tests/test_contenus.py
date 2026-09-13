"""Les trois tables editoriales du §15 — LOT 6, `T1`.

CE QUE CE FICHIER PROUVE, ET CE QU'IL NE PEUT PAS PROUVER

  Il prouve ce que la BASE refuse : les quatre enumerations, l'isolation par cle
  composite, l'implication du §15.1 sur les portees, et les deux unicites
  derivees.

  **Il ne prouve PAS « aucun HTML arbitraire ».** Cette table n'a aucune colonne
  qui puisse porter du HTML libre -- c'est la seule part STRUCTURELLE de
  l'exigence -- mais la validation par type du `payload_json` appartient a `T5`,
  qui SERT des blocs. Un critere qui interdit quelque chose se satisfait tout
  seul quand rien n'est rendu : §7.39, et c'est ce qui a coute la fusion de `T5`
  et `T6` au LOT 5.

CHAQUE REFUS A SON TEMOIN

  Un test qui n'exigerait que l'echec serait satisfait par une table
  ininsertable. Chaque refus est donc double d'une insertion qui REUSSIT et qui
  ne differe que par LA valeur en cause.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.content import (
    ETATS_DE_PAGE,
    TYPES_DE_BLOC,
    TYPES_DE_LIEN,
    TYPES_DE_PAGE,
    EtatDePage,
    TypeDePage,
)
from app.modeles import metadonnees
from app.shared.database import moteur

MARQUEUR = "L6T1"


# ============================================================================
#  1. Ce que le corpus ECRIT, verifie sans base
# ============================================================================
def test_les_cinq_types_de_page_du_15_1_sont_declares() -> None:
    """§15.1 : « `HOME`, `FRAMEWORK`, `CIRCLE`, `OFFICE`, `LEGAL`, autre type controle »."""
    assert set(TYPES_DE_PAGE) == {"HOME", "FRAMEWORK", "CIRCLE", "OFFICE", "LEGAL"}


def test_les_trois_etats_de_page_du_15_1_sont_declares() -> None:
    assert set(ETATS_DE_PAGE) == {"draft", "published", "archived"}


def test_les_types_de_bloc_sont_l_UNION_des_deux_listes_du_corpus() -> None:
    """`DEC-577`. Cinq communs, trois propres au cahier, trois propres au modele.

    **CE TEST DIT D'OU VIENT CHAQUE TYPE**, parce que c'est la seule chose qui
    rende `QO-119` instruisible : le jour ou Lea repondra, celui qui fusionnera
    deux types saura lequel des deux documents le nommait.
    """
    communs = {"TITLE", "RICH_TEXT", "IMAGE", "VIDEO", "LIST"}
    cahier_seul = {"CARD", "LINK", "PRESENTATION"}
    modele_seul = {"LINK_CARD", "QUOTE", "CALL_TO_ACTION"}
    assert set(TYPES_DE_BLOC) == communs | cahier_seul | modele_seul
    #  ONZE, la lecture la plus large. `QO-119` peut la reduire a dix ou neuf ;
    #  elle ne peut pas l'elargir, les deux documents etant epuises.
    assert len(TYPES_DE_BLOC) == 11


def test_le_type_de_lien_porte_OTHER_parce_que_le_15_3_ecrit_AUTRES() -> None:
    """« Liens Hub, Academy, SharePoint **ou autres** ressources internes »."""
    assert set(TYPES_DE_LIEN) == {"HUB", "ACADEMY", "SHAREPOINT", "OTHER"}


def test_aucune_colonne_ne_peut_porter_du_HTML_libre() -> None:
    """La part STRUCTURELLE de « aucun HTML arbitraire » — cahier §10.7.

    Le §7.35 : quand une propriete ne peut pas etre observee par un controle,
    c'est la STRUCTURE qui la tient. Ici, aucune colonne ne s'appelle `html`,
    `body` ou `content` : le contenu voyage dans un document JSON dont `T5`
    connaitra la forme attendue par type.
    """
    interdits = {"html", "body", "content", "raw", "markup"}
    for nom in ("content_page", "content_block", "internal_link"):
        colonnes = {c.name for c in metadonnees.tables[nom].columns}
        assert not (colonnes & interdits), f"{nom} porte une colonne de contenu libre"


def test_content_block_porte_un_entity_id_que_le_15_2_n_ecrit_pas() -> None:
    """§25.3, qui est AUSSI le modele — voir l'en-tete du module.

    Sans `entity_id`, la cle etrangere vers `content_page` serait SIMPLE, et un
    bloc pourrait pointer la page d'une autre entite.
    """
    assert "entity_id" in metadonnees.tables["content_block"].columns
    composite = [
        fk
        for fk in metadonnees.tables["content_block"].foreign_key_constraints
        if len(fk.columns) == 2
    ]
    assert composite, "la cle vers content_page doit etre COMPOSITE"


# ============================================================================
#  2. Integration — ce que la base REFUSE, et son temoin a chaque fois
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
            #  **TROIS PARAMETRES DISTINCTS, ET CE N'EST PAS UN CONFORT.** Un
            #  parametre lie partage par `code` -- `character varying(64)` -- et
            #  par `display_name`/`city` -- `text` -- rend « inconsistent types
            #  deduced for parameter $1 », et le message ne nomme ni la table ni
            #  la colonne. §7.25, et je viens de le rejouer une quatrieme fois.
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
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


def _page(
    cx: Connection,
    entite: uuid.UUID,
    *,
    type_de_page: str = "HOME",
    slug: str = "accueil",
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    etat: str = "draft",
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO content_page (entity_id, page_type, slug, title, state, "
            "circle_id, office_id) VALUES (:e, :t, :slug, :titre, :et, :c, :b) RETURNING id"
        ),
        {
            "e": entite,
            "t": type_de_page,
            "slug": slug,
            "titre": slug,
            "et": etat,
            "c": cercle,
            "b": bureau,
        },
    ).scalar_one()


def _bloc(
    cx: Connection,
    entite: uuid.UUID,
    page: uuid.UUID,
    *,
    type_de_bloc: str = "TITLE",
    rang: int = 0,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO content_block (entity_id, content_page_id, block_type, display_order) "
            "VALUES (:e, :p, :t, :r) RETURNING id"
        ),
        {"e": entite, "p": page, "t": type_de_bloc, "r": rang},
    ).scalar_one()


# ---- les enumerations -------------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize("type_de_page", TYPES_DE_PAGE)
def test_TEMOIN_les_cinq_types_de_page_sont_acceptes(cx: Connection, type_de_page: str) -> None:
    """Sans ce temoin, une contrainte qui refuserait TOUT passerait les refus."""
    entite = _entite(cx, "TP")
    cercle = _cercle(cx, entite, "C1") if type_de_page == TypeDePage.CIRCLE else None
    bureau = _bureau(cx, entite, "B1") if type_de_page == TypeDePage.OFFICE else None
    page = _page(
        cx,
        entite,
        type_de_page=type_de_page,
        slug=type_de_page.lower(),
        cercle=cercle,
        bureau=bureau,
    )
    assert page is not None


@pytest.mark.integration
def test_un_type_de_page_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "TPX")
    with pytest.raises(IntegrityError, match="page_type_valide"):
        _page(cx, entite, type_de_page="BLOG")


@pytest.mark.integration
@pytest.mark.parametrize("type_de_bloc", TYPES_DE_BLOC)
def test_TEMOIN_les_onze_types_de_bloc_sont_acceptes(cx: Connection, type_de_bloc: str) -> None:
    entite = _entite(cx, "TB")
    page = _page(cx, entite)
    assert _bloc(cx, entite, page, type_de_bloc=type_de_bloc) is not None


@pytest.mark.integration
def test_un_type_de_bloc_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "TBX")
    page = _page(cx, entite)
    with pytest.raises(IntegrityError, match="block_type_valide"):
        _bloc(cx, entite, page, type_de_bloc="IFRAME")


@pytest.mark.integration
def test_un_etat_de_page_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "EX")
    with pytest.raises(IntegrityError, match="state_valide"):
        _page(cx, entite, etat="publie")


# ---- l'isolation par cle composite -----------------------------------------
@pytest.mark.integration
def test_TEMOIN_une_page_de_cercle_pointe_un_cercle_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "ISO1")
    cercle = _cercle(cx, entite, "DATA")
    assert _page(cx, entite, type_de_page="CIRCLE", slug="data", cercle=cercle) is not None


@pytest.mark.integration
def test_une_page_ne_peut_pas_pointer_le_cercle_d_une_AUTRE_entite(cx: Connection) -> None:
    """§25.3, et c'est tout l'objet de la cle COMPOSITE.

    Le decor ne differe du temoin que par l'ENTITE du cercle. Avec une cle
    simple, cette insertion reussirait et la fuite serait silencieuse.
    """
    ici = _entite(cx, "ISO2")
    ailleurs = _entite(cx, "ISO3")
    cercle_etranger = _cercle(cx, ailleurs, "DATA")
    with pytest.raises(IntegrityError, match="fk_content_page_circle"):
        _page(cx, ici, type_de_page="CIRCLE", slug="data", cercle=cercle_etranger)


@pytest.mark.integration
def test_TEMOIN_une_page_de_bureau_pointe_un_bureau_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "ISO6")
    bureau = _bureau(cx, entite, "BDS")
    assert _page(cx, entite, type_de_page="OFFICE", slug="bds", bureau=bureau) is not None


@pytest.mark.integration
def test_une_page_ne_peut_pas_pointer_le_bureau_d_une_AUTRE_entite(cx: Connection) -> None:
    """La TROISIEME cle composite de `T1`.

    Elle a ete ecrite parce que `test_les_cles_composites_sont_toutes_couvertes`
    a echoue : j'avais pose trois chemins et n'en eprouvais que deux. Ce
    garde-fou est de la meme classe que `TABLES_DECLAREES` -- il DOIT echouer a
    chaque cle nouvelle, c'est son objet.
    """
    ici = _entite(cx, "ISO7")
    ailleurs = _entite(cx, "ISO8")
    bureau_etranger = _bureau(cx, ailleurs, "BDS")
    with pytest.raises(IntegrityError, match="fk_content_page_office"):
        _page(cx, ici, type_de_page="OFFICE", slug="bds", bureau=bureau_etranger)


@pytest.mark.integration
def test_un_bloc_ne_peut_pas_pointer_la_page_d_une_AUTRE_entite(cx: Connection) -> None:
    ici = _entite(cx, "ISO4")
    ailleurs = _entite(cx, "ISO5")
    page_etrangere = _page(cx, ailleurs, slug="accueil")
    with pytest.raises(IntegrityError, match="fk_content_block_content_page"):
        _bloc(cx, ici, page_etrangere)


# ---- l'implication du §15.1, et ce qu'il n'interdit PAS ---------------------
@pytest.mark.integration
def test_une_page_de_cercle_SANS_cercle_est_refusee(cx: Connection) -> None:
    entite = _entite(cx, "IMP1")
    with pytest.raises(IntegrityError, match="circle_id_requis_pour_une_page_de_cercle"):
        _page(cx, entite, type_de_page="CIRCLE", slug="data")


@pytest.mark.integration
def test_une_page_de_bureau_SANS_bureau_est_refusee(cx: Connection) -> None:
    entite = _entite(cx, "IMP2")
    with pytest.raises(IntegrityError, match="office_id_requis_pour_une_page_de_bureau"):
        _page(cx, entite, type_de_page="OFFICE", slug="bds")


@pytest.mark.integration
def test_le_15_1_N_INTERDIT_PAS_un_circle_id_sur_une_page_qui_n_est_pas_de_cercle(
    cx: Connection,
) -> None:
    """**CE TEST EXISTE POUR FORCER UNE DECISION, PAS POUR CONSACRER UN USAGE.**

    Le §15.1 ecrit « requis pour une page de cercle » et n'ecrit AUCUNE
    interdiction ailleurs -- au contraire du §8.4, qui dit en toutes lettres que
    « `BOOSTER` exige `circle_id` et **interdit** `office_id` », et dont `T8` du
    LOT 2 a pose la contrainte exhaustive. Les deux sections sont du meme
    document : la ou le modele veut une interdiction, il l'ecrit.

    « Une permission du modele n'est pas une interdiction » -- §4.14. Si un lot
    ulterieur decide d'interdire, **ce test echouera**, et celui qui l'interdit
    saura qu'il decide au lieu de croire appliquer. C'est le §7.32 : un test est
    un meilleur vehicule qu'un commentaire.
    """
    entite = _entite(cx, "IMP3")
    cercle = _cercle(cx, entite, "DATA")
    assert _page(cx, entite, type_de_page="HOME", slug="accueil", cercle=cercle) is not None


@pytest.mark.integration
def test_le_15_1_NE_LIE_PAS_l_etat_publie_a_une_date_de_publication(cx: Connection) -> None:
    """Meme nature que le precedent : `published_at` est « Nullable », sans condition.

    C'est `T7` qui instruit la publication, et `US006` exige alors que « la
    version publiee soit identifiable ». Ce test echouera ce jour-la.
    """
    entite = _entite(cx, "PUB")
    page = _page(cx, entite, etat="published")
    date = cx.execute(
        text("SELECT published_at FROM content_page WHERE id = :i"), {"i": page}
    ).scalar_one()
    assert date is None


@pytest.mark.integration
def test_l_etat_par_defaut_est_BROUILLON(cx: Connection) -> None:
    """Critere de sortie n°1 du lot : « les contenus sont relus avant publication »."""
    entite = _entite(cx, "DEF")
    page = cx.execute(
        text(
            "INSERT INTO content_page (entity_id, page_type, slug, title) "
            "VALUES (:e, 'HOME', 'accueil', 'Accueil') RETURNING id"
        ),
        {"e": entite},
    ).scalar_one()
    etat = cx.execute(
        text("SELECT state FROM content_page WHERE id = :i"), {"i": page}
    ).scalar_one()
    assert etat == EtatDePage.DRAFT


# ---- les deux unicites derivees --------------------------------------------
@pytest.mark.integration
def test_deux_pages_de_meme_entite_meme_type_et_meme_slug_sont_refusees(cx: Connection) -> None:
    """§15.1 : « unique dans l'entite ET le type »."""
    entite = _entite(cx, "SLUG1")
    _page(cx, entite, type_de_page="LEGAL", slug="mentions")
    with pytest.raises(IntegrityError, match="uq_content_page_entity_type_slug_non_archive"):
        _page(cx, entite, type_de_page="LEGAL", slug="mentions")


@pytest.mark.integration
def test_TEMOIN_le_meme_slug_est_accepte_sur_un_AUTRE_type(cx: Connection) -> None:
    """L'unicite porte sur le TRIPLET. Sans ce temoin, une unicite sur le seul
    slug donnerait la meme observation que la bonne."""
    entite = _entite(cx, "SLUG2")
    _page(cx, entite, type_de_page="LEGAL", slug="mentions")
    assert _page(cx, entite, type_de_page="HOME", slug="mentions") is not None


@pytest.mark.integration
def test_TEMOIN_le_meme_slug_est_accepte_dans_une_AUTRE_entite(cx: Connection) -> None:
    ici = _entite(cx, "SLUG3")
    ailleurs = _entite(cx, "SLUG4")
    _page(cx, ici, type_de_page="LEGAL", slug="mentions")
    assert _page(cx, ailleurs, type_de_page="LEGAL", slug="mentions") is not None


@pytest.mark.integration
def test_deux_blocs_de_meme_rang_sur_une_meme_page_sont_refuses(cx: Connection) -> None:
    """L'ordre doit etre TOTAL : deux blocs de meme rang rendraient l'affichage
    non deterministe, defaut que `T2` du LOT 5 a corrige sur le trombinoscope."""
    entite = _entite(cx, "ORD1")
    page = _page(cx, entite)
    _bloc(cx, entite, page, rang=0)
    with pytest.raises(IntegrityError, match="uq_content_block_page_ordre_non_archive"):
        _bloc(cx, entite, page, rang=0)


@pytest.mark.integration
def test_TEMOIN_le_meme_rang_est_accepte_sur_une_AUTRE_page(cx: Connection) -> None:
    entite = _entite(cx, "ORD2")
    page_a = _page(cx, entite, slug="a", type_de_page="HOME")
    page_b = _page(cx, entite, slug="b", type_de_page="LEGAL")
    _bloc(cx, entite, page_a, rang=0)
    assert _bloc(cx, entite, page_b, rang=0) is not None


# ---- `internal_link` --------------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize("type_de_lien", TYPES_DE_LIEN)
def test_TEMOIN_les_quatre_types_de_lien_sont_acceptes(cx: Connection, type_de_lien: str) -> None:
    entite = _entite(cx, "LK")
    identifiant = cx.execute(
        text(
            "INSERT INTO internal_link (entity_id, label, url, link_type, display_order) "
            "VALUES (:e, 'Hub', 'https://hub.exalt.test', :t, 0) RETURNING id"
        ),
        {"e": entite, "t": type_de_lien},
    ).scalar_one()
    assert identifiant is not None


@pytest.mark.integration
@pytest.mark.parametrize(
    ("colonne", "valeur", "contrainte"),
    [("url", "   ", "url_non_vide"), ("label", "", "label_non_vide")],
)
def test_un_lien_a_URL_ou_LIBELLE_vide_est_refuse(
    cx: Connection, colonne: str, valeur: str, contrainte: str
) -> None:
    """La contrainte borne la FORME. **Le PROTOCOLE n'est pas borne ici** : le
    corpus dit deux fois « une liste de protocoles autorises » et ne la donne
    jamais -- `QO-120`, et c'est `T8` qui ecrira la validation."""
    entite = _entite(cx, "LKX")
    valeurs = {"e": entite, "label": "Hub", "url": "https://hub.exalt.test"}
    valeurs[colonne] = valeur
    with pytest.raises(IntegrityError, match=contrainte):
        cx.execute(
            text(
                "INSERT INTO internal_link (entity_id, label, url, link_type, display_order) "
                "VALUES (:e, :label, :url, 'HUB', 0)"
            ),
            valeurs,
        )


@pytest.mark.integration
def test_un_lien_DESACTIVE_reste_distinct_d_un_lien_ARCHIVE(cx: Connection) -> None:
    """§15.3 nomme `active` EN PLUS des champs communs du §3.1, qui portent deja
    `archived_at`. Fondre les deux ferait disparaitre une distinction ecrite."""
    entite = _entite(cx, "LKA")
    colonnes = {c.name for c in metadonnees.tables["internal_link"].columns}
    assert {"active", "archived_at"} <= colonnes
    identifiant = cx.execute(
        text(
            "INSERT INTO internal_link (entity_id, label, url, link_type, display_order, active) "
            "VALUES (:e, 'Hub', 'https://hub.exalt.test', 'HUB', 0, false) RETURNING id"
        ),
        {"e": entite},
    ).scalar_one()
    ligne = cx.execute(
        text("SELECT active, archived_at FROM internal_link WHERE id = :i"), {"i": identifiant}
    ).one()
    assert ligne.active is False
    assert ligne.archived_at is None


# ---- le garde-fou que `T1` a trouve en engendrant sa migration --------------
@pytest.mark.integration
def test_l_index_de_recherche_du_LOT_5_EXISTE_TOUJOURS(cx: Connection) -> None:
    """**CE TEST NAIT D'UN INCIDENT EVITE, ET IL EST LE VRAI LIVRABLE DE CE FICHIER.**

    `alembic revision --autogenerate` a propose, dans la migration `0017` :

        op.drop_index(op.f('ix_person_recherche_nom'), table_name='person')

    C'est l'index de la recherche du trombinoscope, pose en SQL brut par la
    migration `0015`. Autogenerate ne sait pas reconcilier un index sur
    EXPRESSION : il le voit en base, absent des metadonnees, et conclut a la
    suppression. Le livrer aurait supprime la recherche du LOT 5 **en silence**,
    dans une migration dont le titre ne parle que de contenus editoriaux.

    Mesure du 13/09/2026 : l'index n'etait declare dans AUCUN module de `app/`,
    et AUCUN test n'exigeait son existence. Le piege etait donc debout pour
    toutes les sous-etapes suivantes -- §7.31, un garde-fou exact pour un mode de
    defaillance et aveugle a un autre.

    Un test est un meilleur vehicule qu'un commentaire (§7.32) : celui-ci
    NOMMERA l'index le jour ou quelqu'un le fera disparaitre.
    """
    present = cx.execute(
        text("SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :n"),
        {"n": "ix_person_recherche_nom"},
    ).scalar_one_or_none()
    assert present == 1, (
        "ix_person_recherche_nom a disparu. Une migration l'a-t-elle supprime ? "
        "`alembic --autogenerate` le propose a CHAQUE fois : voir la migration 0017."
    )
