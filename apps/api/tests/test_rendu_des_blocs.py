"""Le rendu des blocs d'une page de contenu — LOT 6, `T5`, `MVP-L06-US004` (1 sur 3).

LE CRITERE EST NEGATIF, DONC IL LUI FAUT UN TEMOIN POSITIF

  « Aucun HTML arbitraire » est satisfait par une route qui ne rend **rien**.
  C'est le §7.39, et c'est ce qui a fait fusionner `T5` et `T6` du LOT 5. Chaque
  refus de cette suite est donc apparie a un temoin qui ne differe que par LA
  valeur en cause, et le plus utile n'est pas un refus : c'est **un bloc
  legitime rendu**.

CE QUE LA SUITE PROUVE DU BALISAGE, ET COMMENT

  **Pas par un filtre.** Chercher `<script` serait une heuristique -- donc un
  defaut (§7.25) -- et laisserait passer `<img onerror=…` tout en criant au loup
  sur « a < b ».

  Ce qui est prouve est **structurel** : un payload contenant `<script>` est
  servi **comme une chaine dans un objet JSON**, et la reponse ne porte aucun
  champ de nature HTML. Le perdre exigerait de changer le type.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.content.modeles import TYPES_DE_BLOC, EtatDePage, TypeDeBloc
from app.content.pages import (
    ETAT_RENDU,
    PageDeContenuRendue,
    PayloadNonObjet,
    lire_la_page_de_contenu,
)
from app.content.routes import BlocDeContenuRendu, ReponseDeLaPageDeContenu
from app.shared.database import moteur

MARQUEUR = "L6T5"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

#  La charge qui a coule des projets entiers. Elle est servie **telle quelle**,
#  comme une chaine : ce n'est pas une faute, c'est la preuve que l'API sert des
#  donnees. Ce qui serait fautif, c'est qu'un champ de la reponse la designe
#  comme du balisage a interpreter.
INJECTION = "<script>alert('xss')</script>"


# ============================================================================
#  1. Ce que la STRUCTURE tient, verifie sans base
# ============================================================================
def test_aucun_champ_de_la_reponse_n_est_de_nature_HTML() -> None:
    """**C'EST LE TYPE QUI TIENT « AUCUN HTML EXECUTE », PAS UN CONTROLE.**

    §7.35 : quand une propriete ne peut pas etre observee par un test de
    comportement, on la rend **structurelle** — la perdre doit exiger de casser
    le type, pas de retirer un appel.

    Le perimetre est **derive des champs du modele**, jamais listé de memoire
    (§7.27) : si quelqu'un ajoutait un champ `html` ou `contenu_rendu`, ce test
    echouerait sans qu'on ait pensé a le mettre a jour.
    """
    suspects = {"html", "raw", "brut", "markup", "balisage", "rendu", "innerhtml", "dangerously"}

    for modele in (ReponseDeLaPageDeContenu, BlocDeContenuRendu):
        for nom in modele.model_fields:
            minuscule = nom.lower()
            assert not any(s in minuscule for s in suspects), (
                f"{modele.__name__}.{nom} porte un nom de nature HTML ; "
                "le cahier §10.7 veut « aucun HTML arbitraire stocke ou execute »"
            )

    #  Et le contenu d'un bloc est un OBJET, jamais une chaine : une chaine
    #  serait ce qu'un client serait tente d'injecter telle quelle.
    assert BlocDeContenuRendu.model_fields["contenu"].annotation == dict[str, object]


def test_l_etat_rendu_est_DERIVE_de_l_enumeration_et_non_ecrit_en_dur() -> None:
    """`DEC-544`, même parti que le filtre `active` des entités.

    Si le §15.1 recevait un quatrième état, cette constante resterait juste ou
    échouerait bruyamment — jamais silencieusement fausse.
    """
    assert ETAT_RENDU == EtatDePage.PUBLISHED.value == "published"


def test_les_ONZE_types_de_bloc_de_DEC_577_sont_declares() -> None:
    """L'union des deux listes du corpus — `DEC-577`, et `QO-119` en tranchera le compte."""
    assert len(TYPES_DE_BLOC) == 11
    assert set(TYPES_DE_BLOC) == {m.value for m in TypeDeBloc}


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
        #  Un parametre PAR COLONNE — §7.25, defaut `T1-2`.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _page(
    cx: Connection,
    entite: uuid.UUID,
    slug: str,
    *,
    type_de_page: str = "HOME",
    etat: str = "published",
    archive: bool = False,
    publiee_le: dt.datetime | None = JANVIER,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO content_page (entity_id, page_type, title, slug, state, published_at, "
            "archived_at) VALUES (:e, :type, :titre, :slug, :etat, :publiee, :archive) "
            "RETURNING id"
        ),
        #  `title` est `text` et `slug` est `varchar(160)` : deux parametres.
        {
            "e": entite,
            "type": type_de_page,
            "titre": slug,
            "slug": slug,
            "etat": etat,
            "publiee": publiee_le,
            "archive": JANVIER if archive else None,
        },
    ).scalar_one()


def _bloc(
    cx: Connection,
    entite: uuid.UUID,
    page: uuid.UUID,
    *,
    ordre: int,
    type_de_bloc: str = "RICH_TEXT",
    contenu: str = '{"texte": "bonjour"}',
    archive: bool = False,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO content_block (entity_id, content_page_id, block_type, display_order, "
            "payload_json, archived_at) VALUES (:e, :p, :type, :ordre, CAST(:charge AS jsonb), "
            ":archive) RETURNING id"
        ),
        {
            "e": entite,
            "p": page,
            "type": type_de_bloc,
            "ordre": ordre,
            "charge": contenu,
            "archive": JANVIER if archive else None,
        },
    ).scalar_one()


def _lire(
    cx: Connection, entite: uuid.UUID, slug: str, *, type_de_page: str = "HOME"
) -> PageDeContenuRendue | None:
    return lire_la_page_de_contenu(cx, entite=entite, type_de_page=type_de_page, slug=slug)


# ----------------------------------------------------------------------------
#  2.1 LE TEMOIN POSITIF — celui qui rend le critere negatif non trivial
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_un_bloc_LEGITIME_est_RENDU(cx: Connection) -> None:
    """**SANS CE TEST, « aucun HTML arbitraire » SERAIT SATISFAIT PAR UNE ROUTE QUI
    NE REND RIEN** — §7.39, la leçon qui a fait fusionner `T5` et `T6` du LOT 5."""
    entite = _entite(cx, "OK")
    page = _page(cx, entite, "accueil")
    _bloc(cx, entite, page, ordre=1, type_de_bloc="TITLE", contenu='{"texte": "Bienvenue"}')

    lu = _lire(cx, entite, "accueil")

    assert lu is not None
    assert lu.nombre_de_blocs == 1
    assert lu.blocs[0].type_de_bloc == "TITLE"
    assert lu.blocs[0].contenu == {"texte": "Bienvenue"}
    assert lu.titre == "accueil"
    assert lu.slug == "accueil"
    assert lu.identifiant == page


@pytest.mark.integration
def test_les_ONZE_types_de_bloc_sont_tous_servis(cx: Connection) -> None:
    """Le périmètre est **dérivé de l'énumération**, jamais listé (§7.27).

    Un douzième type entrerait ici sans que personne y pense — et s'il n'était
    pas servable, ce test le dirait.
    """
    entite = _entite(cx, "TYPES")
    page = _page(cx, entite, "tous-les-types")
    for rang, type_de_bloc in enumerate(TYPES_DE_BLOC, start=1):
        _bloc(cx, entite, page, ordre=rang, type_de_bloc=type_de_bloc)

    lu = _lire(cx, entite, "tous-les-types")

    assert lu is not None
    assert [b.type_de_bloc for b in lu.blocs] == list(TYPES_DE_BLOC)
    assert lu.nombre_de_blocs == len(TYPES_DE_BLOC) == 11


# ----------------------------------------------------------------------------
#  2.2 L'INJECTION — servie comme DONNEE, ce qui est le propos de la sous-etape
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_du_balisage_dans_le_payload_est_servi_COMME_UNE_CHAINE(cx: Connection) -> None:
    """**LE TEST CENTRAL DE `T5`.**

    Le balisage arrive **intact, comme une chaine dans un objet**. Ce n'est pas
    un defaut : c'est la preuve que cette API sert des DONNEES. Un client qui
    l'afficherait comme du texte — ce que fait tout moteur de rendu par defaut —
    verra les caracteres `<script>`, pas un script.

    Ce qui serait fautif serait qu'un champ de la reponse **designe** cette
    chaine comme du balisage a interpreter, et le test structurel du §1 l'exige.
    """
    entite = _entite(cx, "XSS")
    page = _page(cx, entite, "injection")
    _bloc(
        cx,
        entite,
        page,
        ordre=1,
        contenu='{"texte": "<script>alert(\'xss\')</script>"}',
    )

    lu = _lire(cx, entite, "injection")

    assert lu is not None
    valeur = lu.blocs[0].contenu["texte"]
    assert isinstance(valeur, str), "le balisage arrive comme une CHAINE, pas comme une structure"
    assert valeur == INJECTION, "il arrive INTACT — rien n'est retire en silence"


@pytest.mark.integration
def test_un_payload_qui_n_est_PAS_UN_OBJET_est_refuse_VISIBLEMENT(cx: Connection) -> None:
    """**Refusé, jamais réparé en silence — §7.20.**

    Envelopper la valeur dans un objet inventerait une clef ; ignorer le bloc le
    ferait disparaitre d'une page sans que personne le sache. L'exception nomme
    le bloc **et** le type obtenu.
    """
    entite = _entite(cx, "SCALAIRE")
    page = _page(cx, entite, "scalaire")
    fautif = _bloc(cx, entite, page, ordre=1, contenu='"une chaine nue"')

    with pytest.raises(PayloadNonObjet) as leve:
        _lire(cx, entite, "scalaire")

    assert leve.value.bloc == fautif
    assert leve.value.obtenu == "str"
    assert str(fautif) in str(leve.value)


@pytest.mark.integration
def test_le_TEMOIN_du_refus_precedent_un_objet_passe(cx: Connection) -> None:
    """Sans lui, une lecture qui refuserait TOUT donnerait la meme observation."""
    entite = _entite(cx, "OBJET")
    page = _page(cx, entite, "objet")
    _bloc(cx, entite, page, ordre=1, contenu='{"cle": "valeur"}')

    lu = _lire(cx, entite, "objet")

    assert lu is not None
    assert lu.blocs[0].contenu == {"cle": "valeur"}


# ----------------------------------------------------------------------------
#  2.3 L'ETAT DE LA PAGE — le brouillon ne se distingue pas de l'inexistant
# ----------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize(
    ("etat", "archive", "rendue", "motif"),
    [
        ("published", False, True, "le TEMOIN POSITIF — sans lui les trois refus ne prouvent rien"),
        ("draft", False, False, "un BROUILLON ne se distingue pas d'une page inexistante"),
        ("archived", False, False, "une page archivee non plus"),
        ("published", True, False, "une page publiee PUIS archivee non plus"),
    ],
)
def test_seules_les_pages_PUBLIEES_sont_rendues(
    cx: Connection, etat: str, archive: bool, rendue: bool, motif: str
) -> None:
    """Chaque ligne ne differe de la premiere que par **LA** valeur en cause.

    Le brouillon est le cas qui compte : `US006` — « **previsualiser** puis
    publier » — est la story de `T7`, avec sa propre grille de roles. Servir un
    brouillon ici la viderait de son sens.
    """
    entite = _entite(cx, f"ETAT{etat}{int(archive)}")
    _page(cx, entite, "page", etat=etat, archive=archive)

    lu = _lire(cx, entite, "page")

    assert (lu is not None) is rendue, motif


@pytest.mark.integration
def test_une_page_SANS_AUCUN_BLOC_est_une_page_valide(cx: Connection) -> None:
    """**`None` ET « zero bloc » SONT DEUX ETATS DIFFERENTS.**

    Les confondre empecherait l'editeur de distinguer « cette page n'existe
    pas » de « cette page n'a pas encore de contenu ».
    """
    entite = _entite(cx, "VIDE")
    _page(cx, entite, "vide")

    lu = _lire(cx, entite, "vide")

    assert lu is not None
    assert lu.blocs == ()
    assert lu.nombre_de_blocs == 0


@pytest.mark.integration
def test_la_date_de_publication_absente_n_est_JAMAIS_la_chaine_None(cx: Connection) -> None:
    """Le §15.1 dit `published_at` **nullable**, et ne le lie PAS a `state`.

    Une page `published` sans date n'est interdite nulle part — `T1` l'a relevé.
    Le couple du §7.42 : une page avec date, une page sans.
    """
    entite = _entite(cx, "DATE")
    _page(cx, entite, "avec-date", publiee_le=JANVIER)
    _page(cx, entite, "sans-date", publiee_le=None)

    avec = _lire(cx, entite, "avec-date")
    sans = _lire(cx, entite, "sans-date")

    assert avec is not None and sans is not None
    assert avec.publiee_le is not None and avec.publiee_le.startswith("2026-01-01")
    assert sans.publiee_le is None
    assert sans.publiee_le != "None"


# ----------------------------------------------------------------------------
#  2.4 L'ORDRE, L'ARCHIVAGE DES BLOCS, ET LE CLOISONNEMENT
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_les_blocs_sortent_dans_leur_ORDRE_D_AFFICHAGE(cx: Connection) -> None:
    entite = _entite(cx, "ORDRE")
    page = _page(cx, entite, "ordre")
    for rang in (3, 1, 2):
        _bloc(cx, entite, page, ordre=rang, contenu=f'{{"rang": {rang}}}')

    lu = _lire(cx, entite, "ordre")

    assert lu is not None
    assert [b.ordre for b in lu.blocs] == [1, 2, 3]


@pytest.mark.integration
def test_l_ordre_est_TOTAL_meme_entre_blocs_ARCHIVES_de_meme_rang(cx: Connection) -> None:
    """L'unicite de `T1` porte sur `(content_page_id, display_order)` **non
    archive** : deux blocs archives PEUVENT partager un rang. Sans `b.id` en
    dernier terme, leur ordre flotterait — et ils sont exclus, mais la requete
    doit rester deterministe si un lot ulterieur les rendait."""
    entite = _entite(cx, "TOTAL")
    page = _page(cx, entite, "total")
    _bloc(cx, entite, page, ordre=1, contenu='{"n": 1}')
    _bloc(cx, entite, page, ordre=1, contenu='{"n": 2}', archive=True)
    _bloc(cx, entite, page, ordre=1, contenu='{"n": 3}', archive=True)

    premier = _lire(cx, entite, "total")
    second = _lire(cx, entite, "total")

    assert premier is not None and second is not None
    assert premier.nombre_de_blocs == 1, "les deux archives sont exclus"
    assert [b.contenu for b in premier.blocs] == [b.contenu for b in second.blocs]


@pytest.mark.integration
def test_un_bloc_ARCHIVE_n_est_pas_rendu_et_le_TEMOIN_l_est(cx: Connection) -> None:
    entite = _entite(cx, "BARCH")
    page = _page(cx, entite, "barch")
    _bloc(cx, entite, page, ordre=1, contenu='{"etat": "vivant"}')
    _bloc(cx, entite, page, ordre=2, contenu='{"etat": "archive"}', archive=True)

    lu = _lire(cx, entite, "barch")

    assert lu is not None
    assert [b.contenu["etat"] for b in lu.blocs] == ["vivant"]


@pytest.mark.integration
def test_le_slug_est_unique_par_TYPE_et_les_deux_pages_coexistent(cx: Connection) -> None:
    """§15.1 : « `slug` | Unique dans l'entite **ET le type** ».

    C'est pourquoi l'adresse porte les deux : par le slug seul, ces deux pages
    seraient indistinguables.
    """
    entite = _entite(cx, "SLUG")
    _page(cx, entite, "partage", type_de_page="HOME")
    _page(cx, entite, "partage", type_de_page="LEGAL")

    accueil = _lire(cx, entite, "partage", type_de_page="HOME")
    legal = _lire(cx, entite, "partage", type_de_page="LEGAL")

    assert accueil is not None and legal is not None
    assert accueil.identifiant != legal.identifiant
    assert accueil.type_de_page == "HOME"
    assert legal.type_de_page == "LEGAL"


@pytest.mark.integration
def test_la_page_d_une_AUTRE_entite_rend_None(cx: Connection) -> None:
    """Le cloisonnement du §25.3, eprouve sur le MEME slug."""
    premiere = _entite(cx, "ENT1")
    seconde = _entite(cx, "ENT2")
    _page(cx, seconde, "commune")

    assert _lire(cx, seconde, "commune") is not None, "le TEMOIN"
    assert _lire(cx, premiere, "commune") is None


@pytest.mark.integration
def test_un_slug_inconnu_rend_None(cx: Connection) -> None:
    entite = _entite(cx, "INCONNU")
    _page(cx, entite, "existe")

    assert _lire(cx, entite, "existe") is not None, "le TEMOIN"
    assert _lire(cx, entite, "absente") is None


@pytest.mark.integration
def test_les_blocs_d_une_AUTRE_page_ne_sont_pas_melanges(cx: Connection) -> None:
    entite = _entite(cx, "MELANGE")
    une = _page(cx, entite, "une")
    autre = _page(cx, entite, "autre")
    _bloc(cx, entite, une, ordre=1, contenu='{"page": "une"}')
    _bloc(cx, entite, autre, ordre=1, contenu='{"page": "autre"}')

    lu = _lire(cx, entite, "une")

    assert lu is not None
    assert [b.contenu["page"] for b in lu.blocs] == ["une"]
