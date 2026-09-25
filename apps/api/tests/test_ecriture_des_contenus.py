"""L'ecriture d'un contenu dans son perimetre — LOT 6, `T6`, `MVP-L06-US004` (2 sur 3).

LE CRITERE A TROIS MEMBRES, ET DEUX SONT NEGATIFS

  « Aucun HTML arbitraire ; les blocs autorises sont **valides** ; le perimetre
  suit la matrice. »

  **« Aucun HTML arbitraire » est satisfait par une route qui n'accepte RIEN**, et
  « le perimetre suit la matrice » par une route qui refuse TOUT LE MONDE. C'est
  le §7.39, et c'est ce qui a fait fusionner `T5` et `T6` du LOT 5. Chaque refus
  de cette suite est donc apparie a un temoin qui ne differe que par LA valeur en
  cause, et le plus utile n'est pas un refus : c'est **un contenu legitime
  ecrit**, relu par la route de `T5`.

CE QUE LA SUITE PROUVE DE LA GRILLE, ET POURQUOI ELLE EST NEUVE

  **La grille de l'ecriture du LOT 5 ne se reemploie pas, et elle differe dans
  les DEUX sens** :

      `ROLES_D_ECRITURE`  (§6.1)   DSM  ESM  BOOST  ADM-E  SUPER
      ici                 (§13)         ESM  BOOST  ADM-E  SUPER  **+ OFFICE**

  Le `DSM` porte cinq champs d'ecriture au §6.1 et **rien** au §13 ; `OFFICE` est
  a tiret sur tout le §6.1 et porte ici le contenu de **son** bureau. Reutiliser
  l'une aurait donc a la fois accorde et retire un droit.

  Et le couple decisif est celui ou **seul l'instant avance** : la meme
  responsabilite, la meme page, et un droit qui n'existe pas encore.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.content.cycle_de_vie import archiver_une_page, publier_une_page
from app.content.ecriture import (
    CODE_RATTACHEMENT_REQUIS,
    CODE_RESSOURCE_INTROUVABLE,
    CODE_SLUG_DEJA_PRIS,
    CODE_SLUG_NON_ADRESSABLE,
    CODE_TYPE_DE_BLOC_REFUSE,
    CODE_TYPE_DE_PAGE_REFUSE,
    CODE_VERSION_OBSOLETE,
    ETAT_A_LA_CREATION,
    BlocDemande,
    creer_une_page,
    remplacer_le_contenu,
)
from app.content.modeles import TYPES_DE_BLOC, TYPES_DE_PAGE, EtatDePage, TypeDePage
from app.content.pages import (
    lire_la_page_de_contenu,
    lire_une_page_pour_edition,
    lister_les_pages_de_l_entite,
)
from app.content.perimetre import (
    PORTEES_LOCALES,
    ROLES_D_ECRITURE_EDITORIALE,
    ROLES_DE_CREATION,
    TYPES_SANS_PORTEE_LOCALE,
    ActionEditoriale,
    peut_creer_une_page,
    resoudre_le_perimetre_editorial,
)
from app.content.routes import BlocSoumis, DemandeDeCreationDePage, DemandeDEcritureDuContenu
from app.permissions.perimetre import ROLES_D_ECRITURE, ROLES_DU_CYCLE_DE_VIE
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L6T6"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)

#  La charge qui a coule des projets entiers. Elle est ACCEPTEE, stockee telle
#  quelle, et resservie telle quelle : c'est le propos de `T6`, et ce n'est pas
#  un defaut. Ce qui serait fautif serait qu'un champ la designe comme du
#  balisage a interpreter, ou qu'elle soit mangee en silence.
INJECTION = "<script>alert('xss')</script>"


# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================
def test_aucun_champ_de_la_DEMANDE_n_est_de_nature_HTML() -> None:
    """**C'EST LE TYPE QUI TIENT « AUCUN HTML ACCEPTE », PAS UN FILTRE.**

    `T5` a pose ce test sur la REPONSE ; il le faut aussi sur la DEMANDE, sinon
    « aucun HTML **accepte** » ne serait tenu par rien : une reponse sans champ
    HTML n'empeche pas une demande d'en porter un.

    Le perimetre est **derive des champs du modele** (§7.27) : si quelqu'un
    ajoutait `html`, `format_rendu` ou `dangerously_set`, ce test echouerait sans
    qu'on ait pense a le mettre a jour.
    """
    suspects = {"html", "raw", "brut", "markup", "balisage", "rendu", "innerhtml", "dangerously"}

    for modele in (BlocSoumis, DemandeDEcritureDuContenu, DemandeDeCreationDePage):
        for nom in modele.model_fields:
            minuscule = nom.lower()
            assert not any(s in minuscule for s in suspects), (
                f"{modele.__name__}.{nom} porte un nom de nature HTML ; "
                "le modele §15.2 veut « aucun HTML arbitraire ni script n'est accepte »"
            )

    #  Et le contenu soumis est un OBJET, jamais une chaine : une chaine serait
    #  ce qu'un client serait tente d'injecter telle quelle.
    assert BlocSoumis.model_fields["contenu"].annotation == dict[str, object]


def test_la_demande_de_creation_ne_porte_NI_etat_NI_date_de_publication() -> None:
    """**LE §13 SEPARE « MODIFIER » DE « PUBLIER », ET LE TYPE LE REND STRUCTUREL.**

    L'ESM a « Entite » pour modifier et **« Perimetre »** pour publier : deux
    mots differents, donc deux droits. Une demande qui porterait un etat
    permettrait de publier par la porte de la creation, et viderait le critere de
    sortie n°1 — « les contenus sont relus **avant** publication ».

    §7.35 : le perdre exigerait d'ajouter un champ, pas de retirer un controle.
    """
    champs = set(DemandeDeCreationDePage.model_fields) | set(DemandeDEcritureDuContenu.model_fields)
    for interdit in ("etat", "state", "publiee_le", "published_at", "publication"):
        assert interdit not in champs, (
            f"`{interdit}` permettrait de publier par la porte de la modification"
        )


def test_un_bloc_soumis_ne_porte_NI_ordre_NI_identifiant() -> None:
    """**L'ORDRE EST L'INDEX DE LA LISTE, ET C'EST STRUCTUREL.**

    Un `display_order` libre laisserait exprimer deux blocs de meme rang, que
    l'index unique de `T1` refuserait ensuite en **500**. Ici le cas n'est pas
    refuse : il est **inexprimable**.
    """
    assert set(BlocSoumis.model_fields) == {"type_de_bloc", "contenu"}


def test_la_grille_editoriale_N_EST_PAS_celle_du_LOT_5_et_differe_dans_les_DEUX_sens() -> None:
    """**LE PIEGE CENTRAL DE `T6`, ET C'EST UNE MESURE, PAS UNE AFFIRMATION.**

    Le §13 met `DSM` a tiret sur ses trois lignes de modification, alors que le
    §6.1 lui donne cinq champs ; et il donne a `OFFICE` le contenu de son bureau,
    alors que sa colonne du §6.1 est entierement a tiret.

    Reutiliser `ROLES_D_ECRITURE` aurait donc **accorde** un droit au DSM et
    **retire** le sien au responsable de bureau.
    """
    assert RoleDeLaMatrice.DSM in ROLES_D_ECRITURE
    assert RoleDeLaMatrice.DSM not in ROLES_D_ECRITURE_EDITORIALE

    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU not in ROLES_D_ECRITURE
    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU in ROLES_D_ECRITURE_EDITORIALE

    #  Et elle n'est pas davantage celle du cycle de vie de `T8` du LOT 5.
    assert ROLES_D_ECRITURE_EDITORIALE != ROLES_DU_CYCLE_DE_VIE
    assert ROLES_D_ECRITURE_EDITORIALE != ROLES_D_ECRITURE

    #  `EMP` et `NEW` n'ecrivent aucun contenu : les tableaux §10.x et §13 n'ont
    #  pas ces colonnes, et le §5 ne leur donne que « Lecture ».
    assert RoleDeLaMatrice.EMPLOYE not in ROLES_D_ECRITURE_EDITORIALE


def test_CREER_n_est_pas_MODIFIER_et_la_creation_est_plus_etroite() -> None:
    """§13 : une seule ligne de creation, « Creer un contenu general ».

    Elle ne porte ni `BOOST` ni `OFFICE`, quand les deux lignes de modification
    leur donnent une portee locale. Le Booster **modifie** le contenu de son
    cercle sans pouvoir **creer** sa page — comme le §10.2 lui refuse « Creer un
    cercle ».
    """
    assert ROLES_DE_CREATION < ROLES_D_ECRITURE_EDITORIALE
    assert not peut_creer_une_page(frozenset({RoleDeLaMatrice.BOOSTER}))
    assert not peut_creer_une_page(frozenset({RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}))
    assert not peut_creer_une_page(frozenset({RoleDeLaMatrice.DSM}))
    assert not peut_creer_une_page(frozenset({RoleDeLaMatrice.EMPLOYE}))
    #  Les TEMOINS : sans eux, une fonction qui rendrait toujours `False`
    #  passerait les quatre refus ci-dessus.
    for role in (
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    ):
        assert peut_creer_une_page(frozenset({role}))


def test_les_types_sans_portee_locale_sont_DERIVES_par_soustraction() -> None:
    """**UN SIXIEME TYPE TOMBERAIT DANS LE REGIME LE PLUS RESTRICTIF**, et c'est le sens.

    Le §15.1 dit « autre type controle » : la liste n'est pas fermee. L'ecrire en
    dur ferait l'inverse au premier ajout — un type neuf n'appartiendrait a
    aucune des deux familles, et le perimetre serait alors indefini (§7.27).
    """
    assert {
        TypeDePage.HOME.value,
        TypeDePage.FRAMEWORK.value,
        TypeDePage.LEGAL.value,
    } == TYPES_SANS_PORTEE_LOCALE
    assert TYPES_SANS_PORTEE_LOCALE | set(PORTEES_LOCALES) == set(TYPES_DE_PAGE)
    assert not TYPES_SANS_PORTEE_LOCALE & set(PORTEES_LOCALES)


def test_les_colonnes_des_portees_locales_EXISTENT_sur_le_modele() -> None:
    """**LA TABLE EST DECLAREE, DONC ELLE DOIT CORRESPONDRE AU REEL** (§7.27).

    `PORTEES_LOCALES` nomme les colonnes `circle_id` et `office_id` dans du SQL
    interpole. Une faute de frappe y serait une erreur d'execution sur une route
    d'ecriture ; ici elle est une erreur de collecte.
    """
    from app.content.modeles import ContentPage

    colonnes = set(ContentPage.__table__.columns.keys())
    for type_de_page, portee in PORTEES_LOCALES.items():
        assert type_de_page in TYPES_DE_PAGE
        assert portee.colonne in colonnes, f"{portee.colonne} n'existe pas sur `content_page`"


def test_l_etat_a_la_creation_est_DERIVE_de_l_enumeration() -> None:
    """`DEC-544`, meme parti que `ETAT_RENDU` de `T5` — jamais ecrit en dur."""
    assert ETAT_A_LA_CREATION == EtatDePage.DRAFT.value == "draft"


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
        #  Un parametre PAR COLONNE — §7.25, defaut `T1-2`, et `make
        #  parametres-check` le refuse depuis `DEC-580`.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    #  **`email_normalized` EN MINUSCULES, ET C'EST LA BASE QUI L'EXIGE** :
    #  `ck_person_email_normalise_en_minuscules`, posee au LOT 2. Mon marqueur
    #  etant en capitales, les vingt-cinq tests d'integration echouaient au
    #  DECOR -- defaut `T6-1`. L'echec etait bruyant et nommait la contrainte,
    #  ce qui est la seule bonne nouvelle : un decor qui refuse de se poser ne
    #  laisse pas croire qu'il a teste quelque chose.
    adresse = f"{MARQUEUR}-{suffixe}@exemple.test".lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, :prenom, :nom, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "prenom": suffixe, "nom": MARQUEUR},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str, ordre: int = 1) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, :ordre) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "ordre": ordre},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str, ordre: int = 1) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, :ordre) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "ordre": ordre},
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
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, office_id, "
            " assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :cercle, :bureau, :par, :debut)"
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
    )


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


#  **`T7` A ELARGI CE QUE CETTE FONCTION REND, ET LES ASSERTIONS ONT SUIVI.**
#  Quand `T6` les a ecrites, `resoudre_le_perimetre_editorial` ne pouvait rendre
#  que `MODIFIER` : comparer l'ensemble ENTIER etait alors la forme la plus
#  exacte. `T7` lui fait rendre aussi `PUBLIER`, `ARCHIVER` et `RESTAURER` selon
#  l'etat de la page, si bien que l'egalite stricte mesurerait desormais une
#  grandeur que ces tests-ci ne visent pas.
#
#  Ce qu'ils prouvent est INCHANGE -- la grille de roles et de portees du §13 sur
#  le verbe MODIFIER -- et ils le prouvent toujours : `MODIFIER in perimetre` pour
#  un droit, `== frozenset()` pour un refus, et **les onze refus n'ont pas
#  bouge**. **L'exactitude sur les ensembles COMPLETS est portee par les tests de
#  `T7`**, ou elle est le sujet : c'est la, et pas ici, qu'un Booster doit se voir
#  refuser `RESTAURER` tout en gardant `ARCHIVER`.
def _perimetre(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    page: uuid.UUID,
    roles: set[RoleDeLaMatrice],
    instant: dt.datetime = DEMAIN,
) -> frozenset[ActionEditoriale]:
    return resoudre_le_perimetre_editorial(
        cx,
        entite=entite,
        acteur=acteur,
        page=page,
        roles=frozenset(roles),
        instant=instant,
    ).actions


def _blocs(cx: Connection, page: uuid.UUID) -> list[dict[str, Any]]:
    return [
        dict(ligne)
        for ligne in cx.execute(
            text(
                "SELECT block_type, display_order, payload_json, archived_at "
                "FROM content_block WHERE content_page_id = :p "
                "ORDER BY archived_at NULLS FIRST, display_order"
            ),
            {"p": page},
        ).mappings()
    ]


# ----------------------------------------------------------------------------
#  2.1 LE TEMOIN POSITIF — celui qui rend les criteres negatifs non triviaux
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_un_contenu_LEGITIME_est_ECRIT_puis_RELU_par_la_route_de_T5(cx: Connection) -> None:
    """**SANS CE TEST, « aucun HTML accepte » SERAIT SATISFAIT PAR UNE ROUTE QUI
    N'ACCEPTE RIEN** — §7.39.

    Et il fait plus qu'ecrire : il **relit par le service de `T5`**, ce qui
    prouve l'aller-retour complet. Un test qui relirait ses propres structures ne
    dirait rien de ce qui est reellement en base.
    """
    entite = _entite(cx, "OK")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="accueil")

    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="Bienvenue",
        blocs=(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "Bienvenue"}),
            BlocDemande(type_de_bloc="RICH_TEXT", contenu={"texte": "Chez eXalt"}),
        ),
        instant=DEMAIN,
    )

    assert ecrit.version == 2
    assert [b.ordre for b in ecrit.blocs] == [0, 1]
    assert ecrit.blocs_archives == 0

    #  La page nait `draft` : la route de `T5` ne sert que le publie, donc elle
    #  ne la rend PAS encore. C'est le critere de sortie n°1 du lot.
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="accueil") is None

    cx.execute(
        text("UPDATE content_page SET state = :etat WHERE id = :p"),
        {"etat": EtatDePage.PUBLISHED.value, "p": page},
    )
    lu = lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="accueil")

    assert lu is not None
    assert lu.titre == "Bienvenue"
    assert lu.nombre_de_blocs == 2
    assert [(b.type_de_bloc, b.contenu) for b in lu.blocs] == [
        ("TITLE", {"texte": "Bienvenue"}),
        ("RICH_TEXT", {"texte": "Chez eXalt"}),
    ]


@pytest.mark.integration
def test_les_ONZE_types_de_bloc_sont_tous_ACCEPTES(cx: Connection) -> None:
    """**LE TEMOIN QUI REND LE REFUS NON TRIVIAL** — §7.37.

    Une famille de controles qui n'exige que des refus est satisfaite par une
    route qui refuse TOUT : c'est le defaut `T2-3` du LOT 5, ou huit refus
    restaient verts alors que les trois valeurs valides etaient refusees aussi.

    Le perimetre est **derive de l'enumeration** : un douzieme type y entrerait
    sans que personne y pense.
    """
    entite = _entite(cx, "TYPES")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="tous-les-types")

    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="Tous les types",
        blocs=tuple(BlocDemande(type_de_bloc=t, contenu={}) for t in TYPES_DE_BLOC),
        instant=DEMAIN,
    )

    assert [b.type_de_bloc for b in ecrit.blocs] == list(TYPES_DE_BLOC)
    assert len(ecrit.blocs) == len(TYPES_DE_BLOC) == 11


# ----------------------------------------------------------------------------
#  2.2 LE VERBE « ACCEPTE » — du balisage entre comme DONNEE
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_du_balisage_est_ACCEPTE_stocke_et_resservi_INTACT(cx: Connection) -> None:
    """**LE TEST CENTRAL DE `T6`, ET IL PROUVE L'ABSENCE DE FILTRE.**

    Le balisage traverse **intact**. Ce n'est pas un defaut : c'est la preuve que
    cette API accepte des DONNEES. Un filtre qui aurait mange la chaine donnerait
    la meme observation qu'une absence d'injection — §7.0, quatrieme proposition,
    et c'est exactement le raisonnement de `T5` sur les octets servis.

    Ce qui serait fautif serait qu'un champ **designe** cette chaine comme du
    balisage a interpreter, et le test structurel du §1 l'exige des DEUX cotes.
    """
    entite = _entite(cx, "XSS")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="injection")

    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre=INJECTION,
        blocs=(BlocDemande(type_de_bloc="RICH_TEXT", contenu={"texte": INJECTION}),),
        instant=DEMAIN,
    )

    #  Lu depuis la BASE, pas depuis la structure rendue : un test qui relirait
    #  ce qu'il vient de construire ne dirait rien de ce qui est stocke.
    stocke = _blocs(cx, page)
    assert stocke[0]["payload_json"] == {"texte": INJECTION}
    assert stocke[0]["payload_json"]["texte"] == INJECTION

    titre = cx.execute(
        text("SELECT title FROM content_page WHERE id = :p"), {"p": page}
    ).scalar_one()
    assert titre == INJECTION


@pytest.mark.integration
def test_un_type_de_bloc_INCONNU_est_refuse_et_la_reponse_NOMME_le_rang(cx: Connection) -> None:
    """« Les blocs autorises sont **valides** » — le second membre du critere.

    Le refus vient du SERVICE et non de la contrainte : `block_type_valide`
    refuserait aussi, mais en `IntegrityError`, donc en **500**. Un auteur a
    droit a un 422 qui nomme le bloc fautif.
    """
    entite = _entite(cx, "BLOC")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="bloc-inconnu")

    with pytest.raises(ErreurApplicative) as capture:
        remplacer_le_contenu(
            cx,
            entite=entite,
            page=page,
            acteur=acteur,
            version_attendue=1,
            titre="x",
            blocs=(
                BlocDemande(type_de_bloc="TITLE", contenu={}),
                BlocDemande(type_de_bloc="IFRAME", contenu={}),
            ),
            instant=DEMAIN,
        )

    assert capture.value.code == CODE_TYPE_DE_BLOC_REFUSE
    assert capture.value.statut == 422
    assert capture.value.champ == "blocs[1].type_de_bloc"
    assert capture.value.details == {"types_autorises": list(TYPES_DE_BLOC)}

    #  **RIEN N'A ETE ECRIT**, et c'est le point : la validation precede
    #  l'archivage, donc un refus ne vide pas la page.
    assert _blocs(cx, page) == []


@pytest.mark.integration
def test_le_refus_d_un_type_de_bloc_precede_l_ARCHIVAGE_des_blocs_existants(
    cx: Connection,
) -> None:
    """**UN REFUS NE DOIT PAS VIDER LA PAGE**, et l'ordre des operations le tient.

    Sans ce test, une validation placee apres l'`UPDATE` d'archivage laisserait
    une page **vide** apres un 422 — un contenu detruit par une faute de frappe,
    et la reponse dirait pourtant « refuse ».
    """
    entite = _entite(cx, "ORDRE")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="ordre")
    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="x",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "garde-moi"}),),
        instant=DEMAIN,
    )

    with pytest.raises(ErreurApplicative):
        remplacer_le_contenu(
            cx,
            entite=entite,
            page=page,
            acteur=acteur,
            version_attendue=2,
            titre="x",
            blocs=(BlocDemande(type_de_bloc="PAS_UN_TYPE", contenu={}),),
            instant=DEMAIN,
        )

    vivants = [b for b in _blocs(cx, page) if b["archived_at"] is None]
    assert len(vivants) == 1
    assert vivants[0]["payload_json"] == {"texte": "garde-moi"}


# ----------------------------------------------------------------------------
#  2.3 LE PERIMETRE — la matrice §13, et le couple ou SEUL L'INSTANT avance
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_un_BOOSTER_ecrit_la_page_de_SON_cercle_et_PAS_celle_d_un_autre(cx: Connection) -> None:
    """§13 « Modifier un contenu de cercle | BOOST **Cercle** ».

    Le refus et le temoin ne different que par **le cercle de la page** : meme
    acteur, meme role, meme entite, meme instant. Sans le temoin, un `WHERE` faux
    refuserait tout et passerait quand meme.
    """
    entite = _entite(cx, "BOOST")
    acteur = _personne(cx, "boost")
    sien = _cercle(cx, entite, f"{MARQUEUR}-SIEN", 1)
    autre = _cercle(cx, entite, f"{MARQUEUR}-AUTRE", 2)
    _responsabilite(
        cx, entite=entite, personne=acteur, type_de_responsabilite="BOOSTER", cercle=sien
    )

    page_sienne = _page(
        cx, entite, acteur, type_de_page="CIRCLE", slug="sien", cercle=f"{MARQUEUR}-SIEN"
    )
    page_autre = _page(
        cx, entite, acteur, type_de_page="CIRCLE", slug="autre", cercle=f"{MARQUEUR}-AUTRE"
    )
    assert autre is not None

    roles = {RoleDeLaMatrice.BOOSTER}
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page_sienne, roles=roles
    )
    assert _perimetre(cx, entite=entite, acteur=acteur, page=page_autre, roles=roles) == frozenset()


@pytest.mark.integration
def test_une_responsabilite_FUTURE_n_accorde_RIEN_et_SEUL_l_instant_change(cx: Connection) -> None:
    """**LE TEMOIN LE PLUS UTILE DE LA SOUS-ETAPE**, et c'est celui de `T5` du LOT 5.

    La meme ligne, le meme cercle, la meme page, le meme acteur : **seul
    l'instant avance**, et le droit apparait. Sans lui, le refus mesure pourrait
    venir de n'importe quel filtre trop large.

    Il exerce `period @> :instant`. Une responsabilite future a elle aussi un
    `ends_at` nul : la lire en `ends_at IS NULL` accorderait un droit qui n'existe
    pas encore — `ECART-056`.
    """
    entite = _entite(cx, "FUTUR")
    acteur = _personne(cx, "boost")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C")
    debut = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
    _responsabilite(
        cx,
        entite=entite,
        personne=acteur,
        type_de_responsabilite="BOOSTER",
        cercle=cercle,
        debut=debut,
    )
    page = _page(cx, entite, acteur, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")
    roles = {RoleDeLaMatrice.BOOSTER}

    avant = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles, instant=DEMAIN)
    apres = _perimetre(
        cx,
        entite=entite,
        acteur=acteur,
        page=page,
        roles=roles,
        instant=debut + dt.timedelta(days=1),
    )

    assert avant == frozenset()
    assert ActionEditoriale.MODIFIER in apres


@pytest.mark.integration
def test_un_responsable_de_BUREAU_ecrit_SON_bureau_et_PAS_une_page_de_cercle(
    cx: Connection,
) -> None:
    """§13 « Modifier un contenu de bureau | OFFICE **Bureau** », et §10.3
    « Modifier la structure du bureau | OFFICE **Bureau, contenu uniquement** ».

    La restriction « contenu uniquement » ne mord pas ici : `T6` n'ecrit que du
    contenu — le titre d'une page et ses blocs — jamais le `code`, le `name` ni
    le `display_order` de la table `office`, qui sont sa structure.
    """
    entite = _entite(cx, "OFFICE")
    acteur = _personne(cx, "office")
    bureau = _bureau(cx, entite, f"{MARQUEUR}-BDS")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-CER")
    assert cercle is not None
    _responsabilite(
        cx,
        entite=entite,
        personne=acteur,
        type_de_responsabilite="OFFICE_MANAGER",
        bureau=bureau,
    )

    page_bureau = _page(
        cx, entite, acteur, type_de_page="OFFICE", slug="bds", bureau=f"{MARQUEUR}-BDS"
    )
    page_cercle = _page(
        cx, entite, acteur, type_de_page="CIRCLE", slug="cer", cercle=f"{MARQUEUR}-CER"
    )

    roles = {RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page_bureau, roles=roles
    )
    #  **LE CROISEMENT EST LE POINT** : un responsable de bureau n'ecrit pas une
    #  page de cercle, et un Booster n'ecrit pas une page de bureau. Sans lui,
    #  une portee locale indexee par role et non par TYPE passerait.
    assert (
        _perimetre(cx, entite=entite, acteur=acteur, page=page_cercle, roles=roles) == frozenset()
    )


@pytest.mark.integration
def test_un_DSM_n_ecrit_AUCUN_contenu_et_le_temoin_est_ESM_sur_la_MEME_page(
    cx: Connection,
) -> None:
    """**LA COLONNE `DSM` DU §13 EST A TIRET SUR SES TROIS LIGNES DE MODIFICATION**,
    alors que le §6.1 lui donne cinq champs d'ecriture sur une PERSONNE.

    Le temoin porte sur la **meme page**, et ne differe que par le role : sans
    lui, un refus general donnerait la meme observation.
    """
    entite = _entite(cx, "DSM")
    acteur = _personne(cx, "dsm")
    page = _page(cx, entite, acteur, slug="general")

    assert (
        _perimetre(cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.DSM})
        == frozenset()
    )
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.ESM}
    )


@pytest.mark.integration
def test_un_BOOSTER_n_ecrit_PAS_une_page_generale_meme_dans_SON_entite(cx: Connection) -> None:
    """Les types **sans portee locale** — `HOME`, `FRAMEWORK`, `LEGAL`.

    Le §13 ne donne au Booster que « Modifier un contenu **de cercle** ». Une
    page generale n'est le contenu d'aucun cercle, et la lui ouvrir elargirait sa
    portee a l'entite entiere.
    """
    entite = _entite(cx, "GEN")
    acteur = _personne(cx, "boost")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C")
    _responsabilite(
        cx, entite=entite, personne=acteur, type_de_responsabilite="BOOSTER", cercle=cercle
    )
    roles = {RoleDeLaMatrice.BOOSTER}

    for type_de_page in sorted(TYPES_SANS_PORTEE_LOCALE):
        page = _page(
            cx, entite, acteur, type_de_page=type_de_page, slug=f"gen-{type_de_page.lower()}"
        )
        assert (
            _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles) == frozenset()
        ), type_de_page

    #  TEMOIN : le meme Booster ecrit bien la page de SON cercle.
    sienne = _page(cx, entite, acteur, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=sienne, roles=roles
    )


@pytest.mark.integration
def test_une_page_d_une_AUTRE_entite_est_refusee_MEME_au_SUPER_ADMINISTRATEUR(
    cx: Connection,
) -> None:
    """§25.3 : le couple `(id, entity_id)` porte l'isolation.

    `SUPER` a « Global » au §13, et cela ne veut pas dire « toutes les entites
    depuis n'importe quel chemin » : le §5.1 dit que « les controles cote API
    utilisent l'entite de la RESSOURCE ».
    """
    une = _entite(cx, "UNE")
    autre = _entite(cx, "DEUX")
    acteur = _personne(cx, "super")
    page = _page(cx, autre, acteur, slug="ailleurs")

    assert (
        _perimetre(
            cx,
            entite=une,
            acteur=acteur,
            page=page,
            roles={RoleDeLaMatrice.SUPER_ADMINISTRATEUR},
        )
        == frozenset()
    )
    #  TEMOIN : la meme page, resolue dans SON entite.
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=autre, acteur=acteur, page=page, roles={RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
    )


@pytest.mark.integration
def test_une_page_ARCHIVEE_est_refusee_MEME_au_SUPER_ADMINISTRATEUR(cx: Connection) -> None:
    """§23.2 : « une interdiction liee a la ressource ou a l'etat prevaut sur le
    cumul des roles ».

    On ne **modifie** pas une page archivee, on la **restaure** — et « Restaurer »
    est une autre ligne du §13, a une autre grille : « ESM **Conditionnel** ».

    **`T7` A LIVRE CETTE AUTRE LIGNE, ET CE TEST EN EST DEVENU PLUS FORT.** Quand
    `T6` l'a ecrit, le perimetre d'une page archivee etait VIDE, et c'est ce qu'il
    exigeait. Il exige desormais l'ensemble EXACT `{RESTAURER}` : la page n'est
    toujours pas modifiable — la moitie que `T6` prouvait — et l'unique action
    qu'elle offre est nommee. Un ensemble vide serait aujourd'hui un defaut.
    """
    entite = _entite(cx, "ARCH")
    acteur = _personne(cx, "super")
    page = _page(cx, entite, acteur, slug="archivee")
    roles = {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}

    #  TEMOIN AVANT : elle est modifiable tant qu'elle n'est pas archivee. Sans
    #  lui, le refus mesure ensuite pourrait venir d'autre chose.
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles=roles
    )

    cx.execute(
        text("UPDATE content_page SET archived_at = :instant WHERE id = :p"),
        {"instant": DEMAIN, "p": page},
    )

    apres = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles=roles)
    assert ActionEditoriale.MODIFIER not in apres, "une page archivee ne se modifie pas"
    assert apres == {ActionEditoriale.RESTAURER}, (
        "et elle n'offre QUE la restauration — §18, `ARB-DROIT-003`"
    )


@pytest.mark.integration
def test_une_page_en_BROUILLON_est_MODIFIABLE_et_c_est_tout_le_propos(cx: Connection) -> None:
    """**L'ECRITURE SERT L'AUTEUR, LA LECTURE SERT LE PUBLIC.**

    `T5` ne sert que le `published` ; exiger le meme etat ici rendrait la route
    inutilisable pour ce qu'elle sert — on edite precisement un brouillon. La
    difference est deliberee, et elle est mesuree ici.
    """
    entite = _entite(cx, "DRAFT")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="brouillon")

    etat = cx.execute(
        text("SELECT state FROM content_page WHERE id = :p"), {"p": page}
    ).scalar_one()
    assert etat == EtatDePage.DRAFT.value

    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.ESM}
    )


# ----------------------------------------------------------------------------
#  2.4 L'ECRITURE — archivage, ordre, version
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_les_blocs_retires_sont_ARCHIVES_et_non_SUPPRIMES(cx: Connection) -> None:
    """Modele §2.4 : « Les ressources metier sont archivees par `archived_at` ».

    La suppression physique y est reservee aux donnees temporaires, aux purges
    RGPD et aux operations du super-administrateur. Un bloc retire n'est aucun
    des trois.
    """
    entite = _entite(cx, "ARCHIVE")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="remplacement")

    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="v1",
        blocs=(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "a"}),
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "b"}),
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "c"}),
        ),
        instant=DEMAIN,
    )
    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=2,
        titre="v2",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "seul"}),),
        instant=DEMAIN,
    )

    assert ecrit.blocs_archives == 3
    tous = _blocs(cx, page)
    #  **RIEN N'A DISPARU** : quatre lignes en base, une vivante et trois archivees.
    assert len(tous) == 4
    vivants = [b for b in tous if b["archived_at"] is None]
    archives = [b for b in tous if b["archived_at"] is not None]
    assert len(vivants) == 1
    assert len(archives) == 3
    assert vivants[0]["payload_json"] == {"texte": "seul"}

    #  L'auteur de l'archivage est trace : §3.1, `archived_by_person_id`.
    auteurs = (
        cx.execute(
            text(
                "SELECT DISTINCT archived_by_person_id FROM content_block "
                "WHERE content_page_id = :p AND archived_at IS NOT NULL"
            ),
            {"p": page},
        )
        .scalars()
        .all()
    )
    assert auteurs == [acteur]


@pytest.mark.integration
def test_l_ordre_d_affichage_est_l_ordre_du_TABLEAU(cx: Connection) -> None:
    """`display_order` vaut l'index, et la relecture le confirme.

    Deux blocs de meme rang sont **inexprimables** : c'est §7.35, la propriete
    rendue structurelle plutot que confiee a un controle qu'on pourrait retirer.
    """
    entite = _entite(cx, "ORD")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="ordonnee")

    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="x",
        blocs=tuple(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": lettre}) for lettre in "abcde"
        ),
        instant=DEMAIN,
    )

    vivants = [b for b in _blocs(cx, page) if b["archived_at"] is None]
    assert [b["display_order"] for b in vivants] == [0, 1, 2, 3, 4]
    assert [b["payload_json"]["texte"] for b in vivants] == list("abcde")


@pytest.mark.integration
def test_un_remplacement_qui_REORDONNE_ne_viole_pas_l_unicite_de_rang(cx: Connection) -> None:
    """**L'ARCHIVAGE PRECEDE L'INSERTION, DANS LA MEME TRANSACTION.**

    L'index `uq_content_block_page_ordre_non_archive` est partiel sur
    `archived_at IS NULL` : sans l'`UPDATE` d'abord, la reinsertion au rang 0
    entrerait en collision avec l'ancien bloc de rang 0 et rendrait un 500.
    """
    entite = _entite(cx, "REORD")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="reordonnee")

    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="x",
        blocs=(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "haut"}),
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "bas"}),
        ),
        instant=DEMAIN,
    )
    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=2,
        titre="x",
        blocs=(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "bas"}),
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "haut"}),
        ),
        instant=DEMAIN,
    )

    vivants = [b for b in _blocs(cx, page) if b["archived_at"] is None]
    assert [b["payload_json"]["texte"] for b in vivants] == ["bas", "haut"]


@pytest.mark.integration
def test_une_version_OBSOLETE_rend_409_sans_rien_ecrire(cx: Connection) -> None:
    """§18.4 : « une version obsolete produit un 409 **sans ecrasement silencieux** »."""
    entite = _entite(cx, "VERSION")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="version")
    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="v1",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "original"}),),
        instant=DEMAIN,
    )

    with pytest.raises(ErreurApplicative) as capture:
        remplacer_le_contenu(
            cx,
            entite=entite,
            page=page,
            acteur=acteur,
            version_attendue=1,
            titre="ecrasement",
            blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "ecrase"}),),
            instant=DEMAIN,
        )

    assert capture.value.code == CODE_VERSION_OBSOLETE
    assert capture.value.statut == 409
    assert capture.value.details == {"version_actuelle": 2}

    #  **RIEN N'A BOUGE** : ni le titre, ni les blocs.
    titre = cx.execute(
        text("SELECT title FROM content_page WHERE id = :p"), {"p": page}
    ).scalar_one()
    assert titre == "v1"
    vivants = [b for b in _blocs(cx, page) if b["archived_at"] is None]
    assert [b["payload_json"]["texte"] for b in vivants] == ["original"]


@pytest.mark.integration
def test_l_ecriture_NE_TOUCHE_NI_l_etat_NI_la_date_de_publication(cx: Connection) -> None:
    """**LE §13 SEPARE « MODIFIER » DE « PUBLIER », ET C'EST MESURE SUR LA BASE.**

    Modifier le contenu d'une page **publiee** ne doit pas la depublier, et
    modifier un brouillon ne doit pas le publier. Les deux sens comptent.
    """
    entite = _entite(cx, "ETAT")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="etat")
    cx.execute(
        text("UPDATE content_page SET state = :etat, published_at = :quand WHERE id = :p"),
        {"etat": EtatDePage.PUBLISHED.value, "quand": JANVIER, "p": page},
    )

    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="corrige",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "corrige"}),),
        instant=DEMAIN,
    )

    ligne = cx.execute(
        text("SELECT state, published_at FROM content_page WHERE id = :p"), {"p": page}
    ).one()
    assert ligne[0] == EtatDePage.PUBLISHED.value
    assert ligne[1] == JANVIER


@pytest.mark.integration
def test_une_liste_VIDE_de_blocs_est_legitime(cx: Connection) -> None:
    """Une page sans bloc existe — `T5` la rend avec un tableau vide.

    Refuser le vide obligerait a passer par une suppression de page pour vider un
    contenu, ce qu'aucune ligne du corpus ne demande.
    """
    entite = _entite(cx, "VIDE")
    acteur = _personne(cx, "esm")
    page = _page(cx, entite, acteur, slug="vide")
    remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="x",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={}),),
        instant=DEMAIN,
    )

    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=2,
        titre="x",
        blocs=(),
        instant=DEMAIN,
    )

    assert ecrit.blocs == ()
    assert ecrit.blocs_archives == 1
    assert [b for b in _blocs(cx, page) if b["archived_at"] is None] == []


# ----------------------------------------------------------------------------
#  2.5 LA CREATION — le brouillon, le rattachement, le slug
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_une_page_NAIT_en_brouillon_sans_date_de_publication(cx: Connection) -> None:
    """Critere de sortie n°1 : « l'etat `draft` est le defaut, et la publication
    est un geste distinct »."""
    entite = _entite(cx, "NAIT")
    acteur = _personne(cx, "esm")
    creee = creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page="HOME",
        titre="Accueil",
        slug="accueil",
        code_de_cercle=None,
        code_de_bureau=None,
        instant=JANVIER,
    )

    assert creee.etat == EtatDePage.DRAFT.value
    assert creee.version == 1
    ligne = cx.execute(
        text("SELECT state, published_at, created_by_person_id FROM content_page WHERE id = :p"),
        {"p": creee.identifiant},
    ).one()
    assert ligne[0] == EtatDePage.DRAFT.value
    assert ligne[1] is None
    assert ligne[2] == acteur


@pytest.mark.integration
def test_une_page_de_CERCLE_exige_son_cercle_et_le_TEMOIN_ne_differe_que_par_lui(
    cx: Connection,
) -> None:
    """Modele §15.1 : « `circle_id` | Requis pour une page de cercle ».

    Le 422 vient du service, pas de la contrainte `CHECK`, qui rendrait un 500.
    """
    entite = _entite(cx, "RATT")
    acteur = _personne(cx, "esm")
    _cercle(cx, entite, f"{MARQUEUR}-C")

    with pytest.raises(ErreurApplicative) as capture:
        creer_une_page(
            cx,
            entite=entite,
            acteur=acteur,
            type_de_page="CIRCLE",
            titre="x",
            slug="sans-cercle",
            code_de_cercle=None,
            code_de_bureau=None,
            instant=JANVIER,
        )
    assert capture.value.code == CODE_RATTACHEMENT_REQUIS
    assert capture.value.champ == "cercle"

    #  TEMOIN : la meme demande, avec le cercle.
    creee = creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page="CIRCLE",
        titre="x",
        slug="avec-cercle",
        code_de_cercle=f"{MARQUEUR}-C",
        code_de_bureau=None,
        instant=JANVIER,
    )
    assert creee.type_de_page == "CIRCLE"


@pytest.mark.integration
def test_un_cercle_d_une_AUTRE_entite_n_est_pas_resolu(cx: Connection) -> None:
    """Le cercle est resolu **dans l'entite**, jamais par son code seul.

    Sans ce filtre, une page de Bordeaux pourrait se rattacher au cercle de
    Lille, et la cle etrangere composite du §25.3 rendrait un 500 au lieu d'un
    422 — ou pire, deux entites pourraient partager un code.
    """
    une = _entite(cx, "ICI")
    autre = _entite(cx, "LA")
    acteur = _personne(cx, "esm")
    _cercle(cx, autre, f"{MARQUEUR}-AILLEURS")

    with pytest.raises(ErreurApplicative) as capture:
        creer_une_page(
            cx,
            entite=une,
            acteur=acteur,
            type_de_page="CIRCLE",
            titre="x",
            slug="vol",
            code_de_cercle=f"{MARQUEUR}-AILLEURS",
            code_de_bureau=None,
            instant=JANVIER,
        )
    assert capture.value.code == CODE_RESSOURCE_INTROUVABLE

    #  TEMOIN : le meme code, resolu depuis SON entite.
    creee = creer_une_page(
        cx,
        entite=autre,
        acteur=acteur,
        type_de_page="CIRCLE",
        titre="x",
        slug="legitime",
        code_de_cercle=f"{MARQUEUR}-AILLEURS",
        code_de_bureau=None,
        instant=JANVIER,
    )
    assert creee.slug == "legitime"


@pytest.mark.integration
def test_un_slug_DEJA_PRIS_rend_409_et_le_MEME_slug_passe_sur_un_AUTRE_type(
    cx: Connection,
) -> None:
    """§15.1 : « `slug` | Unique dans l'entite **ET le type** ».

    Le temoin est ce qui rend le refus exact : une unicite posee sur le slug seul
    refuserait aussi le second cas, et les deux observations se ressembleraient.

    **LE POINT DE SAUVEGARDE N'EST PAS UN ORNEMENT, ET C'EST LE DEFAUT `T6-2`.**
    C'est le SEUL refus de cette suite que la **base** produise ; les onze autres
    viennent d'une validation du service, en amont de tout `INSERT`. Or un refus
    de la base **avorte la transaction** — « current transaction is aborted,
    commands ignored until end of transaction block » — si bien que le temoin qui
    suit devenait **inatteignable**, et que le test echouait sur une ligne qui
    n'avait rien a se reprocher.

    La route, elle, n'a pas ce probleme : l'`ErreurApplicative` remonte hors du
    `with moteur(...).begin()`, donc rien ne continue apres. C'est un piege de
    TEST, et il faut savoir le distinguer d'un defaut du livrable.
    """
    entite = _entite(cx, "SLUG")
    acteur = _personne(cx, "esm")
    _page(cx, entite, acteur, type_de_page="HOME", slug="presentation")

    point = cx.begin_nested()
    with pytest.raises(ErreurApplicative) as capture:
        creer_une_page(
            cx,
            entite=entite,
            acteur=acteur,
            type_de_page="HOME",
            titre="x",
            slug="presentation",
            code_de_cercle=None,
            code_de_bureau=None,
            instant=JANVIER,
        )
    assert capture.value.code == CODE_SLUG_DEJA_PRIS
    assert capture.value.statut == 409
    point.rollback()

    #  TEMOIN : le MEME slug, un AUTRE type — le §15.1 l'autorise.
    creee = creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page="LEGAL",
        titre="x",
        slug="presentation",
        code_de_cercle=None,
        code_de_bureau=None,
        instant=JANVIER,
    )
    assert creee.type_de_page == "LEGAL"


@pytest.mark.integration
def test_un_slug_PORTANT_UNE_BARRE_OBLIQUE_est_refuse_ET_la_raison_est_MESUREE(
    cx: Connection,
) -> None:
    """**LE REFUS EST DERIVE DE L'ADRESSAGE, PAS D'UN FORMAT INVENTE.**

    Le corpus ne donne aucun format de slug, et en inventer un serait le §6.5.
    Mais `T5` adresse la page par `…/pages/{type}/{slug}`, et un parametre de
    chemin FastAPI ne capture pas la barre oblique.

    **Ce test MESURE la consequence plutot que de l'affirmer** : une page dont le
    slug en contient une est invisible a la lecture par le chemin qui la
    designe — donc creable et jamais servable.
    """
    entite = _entite(cx, "BARRE")
    acteur = _personne(cx, "esm")

    with pytest.raises(ErreurApplicative) as capture:
        creer_une_page(
            cx,
            entite=entite,
            acteur=acteur,
            type_de_page="HOME",
            titre="x",
            slug="a/b",
            code_de_cercle=None,
            code_de_bureau=None,
            instant=JANVIER,
        )
    assert capture.value.code == CODE_SLUG_NON_ADRESSABLE

    #  **LA MESURE QUI JUSTIFIE LE REFUS.** On pose la page en contournant le
    #  service, on la publie, et on montre que le service de lecture ne la trouve
    #  PAS sous le seul segment que la route peut transmettre.
    cx.execute(
        text(
            "INSERT INTO content_page (entity_id, page_type, title, slug, state) "
            "VALUES (:e, 'HOME', :titre, :slug, 'published')"
        ),
        {"e": entite, "titre": "coupee", "slug": "a/b"},
    )
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="a") is None
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="b") is None
    #  TEMOIN : sous son slug entier, elle existe bien — ce n'est donc pas la
    #  page qui manque, c'est le chemin qui ne peut pas la nommer.
    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="a/b") is not None


@pytest.mark.integration
def test_un_type_de_page_INCONNU_est_refuse_en_422_et_non_en_500(cx: Connection) -> None:
    """Le perimetre est **derive** de `TYPES_DE_PAGE` : un sixieme type y
    entrerait sans que personne y pense."""
    entite = _entite(cx, "TYPEPAGE")
    acteur = _personne(cx, "esm")

    with pytest.raises(ErreurApplicative) as capture:
        creer_une_page(
            cx,
            entite=entite,
            acteur=acteur,
            type_de_page="BLOG",
            titre="x",
            slug="blog",
            code_de_cercle=None,
            code_de_bureau=None,
            instant=JANVIER,
        )
    assert capture.value.code == CODE_TYPE_DE_PAGE_REFUSE
    assert capture.value.statut == 422
    assert capture.value.details == {"types_autorises": list(TYPES_DE_PAGE)}


# ----------------------------------------------------------------------------
#  2.6 LES TEMOINS QUE LA CAMPAGNE A RECLAMES
#
#    **QUATRE FILTRES NE FAISAIENT TOMBER AUCUN TEST**, mesure du 18/09/2026 en
#    les retirant un par un. Deux etaient de vrais trous de couverture -- ils
#    sont couverts ci-dessous -- et deux sont REDONDANTS, tenus par une
#    contrainte du schema : la mesure est au §2.7, et le module le dit.
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_la_responsabilite_d_UNE_AUTRE_PERSONNE_n_accorde_RIEN(cx: Connection) -> None:
    """**`person_id = :acteur`, ET C'EST UN TROU QUE LA CAMPAGNE DE TEMOINS A DIT.**

    Sans ce filtre, la responsabilite de **n'importe qui** sur ce cercle
    accorderait le droit a n'importe quel porteur du role `BOOSTER` — par exemple
    au Booster d'un autre cercle, qui porte bien ce role.

    Le refus et le temoin ne different que par **l'acteur** : meme page, meme
    cercle, meme role, meme instant.
    """
    entite = _entite(cx, "ACTEUR")
    titulaire = _personne(cx, "titulaire")
    autre = _personne(cx, "autre")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C", 1)
    #  L'autre est Booster d'un AUTRE cercle : il porte donc reellement le role,
    #  ce qui est la situation qui rend le filtre necessaire.
    ailleurs = _cercle(cx, entite, f"{MARQUEUR}-D", 2)
    _responsabilite(
        cx, entite=entite, personne=titulaire, type_de_responsabilite="BOOSTER", cercle=cercle
    )
    _responsabilite(
        cx, entite=entite, personne=autre, type_de_responsabilite="BOOSTER", cercle=ailleurs
    )
    page = _page(cx, entite, titulaire, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")
    roles = {RoleDeLaMatrice.BOOSTER}

    assert _perimetre(cx, entite=entite, acteur=autre, page=page, roles=roles) == frozenset()
    #  TEMOIN : le titulaire, sur la MEME page.
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=titulaire, page=page, roles=roles
    )


@pytest.mark.integration
def test_une_responsabilite_REELLE_n_accorde_RIEN_si_le_ROLE_n_est_pas_dans_le_perimetre(
    cx: Connection,
) -> None:
    """**LE §5.1, ET C'EST LE SECOND TROU QUE LA CAMPAGNE A DIT.**

    « Lorsqu'une personne consulte une entite differente de son entite
    principale, elle possede uniquement les droits `EMP` ; ses responsabilites
    DSM, ESM, Booster, responsable de bureau ou administrateur d'entite **ne
    s'appliquent pas**. »

    `resoudre_les_permissions` applique deja cette regle, et rend `EMP` seul.
    **Sans le test `portee.role not in roles`, ce module irait chercher la
    responsabilite en base et la trouverait** — il rendrait donc le droit que le
    §5.1 vient de retirer, en contournant la seule regle qui le porte.

    Le refus et le temoin ne different que par **les roles resolus** : meme
    acteur, meme responsabilite en base, meme page, meme instant.
    """
    entite = _entite(cx, "PORTEE")
    acteur = _personne(cx, "boost")
    cercle = _cercle(cx, entite, f"{MARQUEUR}-C")
    _responsabilite(
        cx, entite=entite, personne=acteur, type_de_responsabilite="BOOSTER", cercle=cercle
    )
    page = _page(cx, entite, acteur, type_de_page="CIRCLE", slug="c", cercle=f"{MARQUEUR}-C")

    #  Ce que le §5.1 laisse a une personne hors de son entite principale.
    assert (
        _perimetre(cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.EMPLOYE})
        == frozenset()
    )
    #  TEMOIN : la MEME responsabilite, dans son entite principale.
    assert ActionEditoriale.MODIFIER in _perimetre(
        cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.BOOSTER}
    )


# ----------------------------------------------------------------------------
#  2.7 CE QUI PROTEGE VRAIMENT — les deux filtres REDONDANTS, et ce qui les tient
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_deux_filtres_du_module_sont_REDONDANTS_et_la_BASE_est_ce_qui_protege(
    cx: Connection,
) -> None:
    """**TROISIEME OCCURRENCE DE LA CLASSE `T4-2` / `T5-1`, ET C'EST LA LECON.**

    La campagne de temoins du 18/09/2026 a dit que `responsibility_type` et
    `entity_id` de `_RESPONSABILITE_SUR_LA_RESSOURCE` ne font tomber **aucun**
    test. Mesure au catalogue, et ce ne sont pas des trous de couverture :

      `ck_..._portee_selon_le_type`   un `circle_id` non nul IMPLIQUE `BOOSTER`,
                                     un `office_id` non nul IMPLIQUE
                                     `OFFICE_MANAGER` -- une biconditionnelle
                                     stricte. Filtrer sur la colonne suffit donc
                                     a fixer le type.
      `fk_..._circle` / `_office`    COMPOSITES `(circle_id, entity_id)` : une
                                     responsabilite qui pointe le cercle C a
                                     forcement l'entite de C, et la page aussi.

    **Les deux filtres sont CONSERVES** — c'est l'idiome de cloisonnement de tout
    ce depot, et une requete locale qui ne nommerait pas son entite se lirait
    comme une requete globale — **mais ils ne sont pas ce qui protege**.

    **CE TEST EXIGE DONC QUE LA BASE CONTINUE DE L'INTERDIRE** (§7.32) : si un
    lot ulterieur relachait l'une des deux contraintes, il echouerait, et celui
    qui la relache saurait qu'il doit relire ce module.
    """
    contraintes = set(
        cx.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'framework_responsibility_assignment'::regclass"
            )
        ).scalars()
    )
    assert "ck_framework_responsibility_assignment_portee_selon_le_type" in contraintes
    assert "fk_framework_responsibility_circle" in contraintes
    assert "fk_framework_responsibility_office" in contraintes

    composite = cx.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'fk_framework_responsibility_circle'"
        )
    ).scalar_one()
    assert "(circle_id, entity_id)" in composite
    assert "circle(id, entity_id)" in composite


# ============================================================================
#  9. Le manifeste, T10 -- un trou depuis T6, ferme par DEC-492
# ============================================================================
MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def test_le_MANIFESTE_expose_ENFIN_les_deux_grilles_d_ecriture() -> None:
    """**LA DISCIPLINE `DEC-492` N'AVAIT PAS ETE SUIVIE ICI, ET C'EST UN TROU,
    PAS UN REPORT.**

    `rolesRestaurationDUnContenu` (`T7`) et `rolesGestionDesLiensInternes`
    (`T8`) sont exposees dans le manifeste des leur sous-etape, en anticipation
    d'un ecran qui n'existait pas encore -- c'est la doctrine de `DEC-492` :
    une seule source, lue par TypeScript ET par Python. `T6` ne l'avait pas
    fait pour SES DEUX grilles, et `T10` n'avait donc aucun moyen cote client
    de savoir qui peut creer une page ou en modifier les blocs.

    **LES DEUX CLES NE SONT PAS EQUIVALENTES, ET LE TEST LE PROUVE SUR LA MEME
    ASSERTION.** `rolesCreationDeContenu` vaut `ROLES_DE_CREATION` -- la ligne
    UNIQUE de creation du §13, sans `BOOST` ni `OFFICE`. `rolesEcritureEditoriale`
    vaut `ROLES_D_ECRITURE_EDITORIALE`, strictement PLUS LARGE : elle y ajoute
    les deux roles de portee locale, parce qu'un Booster ne peut pas CREER une
    page mais peut MODIFIER celle de son cercle. Confondre les deux cles aurait
    soit retire un droit de modification a un Booster, soit accorde a tort un
    droit de creation.
    """
    manifeste = json.loads(
        (pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT).read_text(
            encoding="utf-8"
        )
    )

    codes_creation = manifeste["rolesCreationDeContenu"]
    assert codes_creation, "le manifeste ne declare aucun role de creation de contenu"
    assert {RoleDeLaMatrice(code) for code in codes_creation} == ROLES_DE_CREATION

    codes_ecriture = manifeste["rolesEcritureEditoriale"]
    assert codes_ecriture, "le manifeste ne declare aucun role d'ecriture editoriale"
    assert {RoleDeLaMatrice(code) for code in codes_ecriture} == ROLES_D_ECRITURE_EDITORIALE

    #  La difference elle-meme est ce que l'ecran doit lire pour distinguer
    #  "je peux creer" de "je peux seulement modifier ce qui existe deja".
    assert ROLES_DE_CREATION < ROLES_D_ECRITURE_EDITORIALE, "strictement incluse"

    #  **DEUX CLES DISTINCTES, JAMAIS FUSIONNEES** -- meme motif que les
    #  grilles voisines du lot (§7.32) : les confondre ferait bouger la
    #  creation quand seule la portee locale change, en silence.
    assert "rolesCreationDeContenu" in manifeste
    assert "rolesEcritureEditoriale" in manifeste
    assert manifeste["rolesCreationDeContenu"] != manifeste["rolesEcritureEditoriale"]


# ============================================================================
#  10. La lecture pour l'editeur — T10, le trou comble de la section 9
# ============================================================================
@pytest.mark.integration
def test_la_LISTE_rend_les_TROIS_etats_et_ISOLE_l_entite(cx: Connection) -> None:
    """**SANS CE TEST, LA LISTE POURRAIT NE SERVIR QUE LE PUBLIE**, exactement le
    defaut que cette route existe pour corriger. Elle doit rendre un brouillon,
    un publie ET un archive de la MEME entite -- et RIEN d'une AUTRE.
    """
    entite = _entite(cx, "L1")
    autre_entite = _entite(cx, "L2")
    acteur = _personne(cx, "auteur")

    brouillon = _page(cx, entite, acteur, type_de_page="HOME", slug="brouillon")
    a_publier = _page(cx, entite, acteur, type_de_page="LEGAL", slug="a-publier")
    publier_une_page(
        cx, entite=entite, page=a_publier, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    a_archiver = _page(cx, entite, acteur, type_de_page="LEGAL", slug="a-archiver")
    archiver_une_page(
        cx, entite=entite, page=a_archiver, acteur=acteur, version_attendue=1, instant=DEMAIN
    )
    _page(cx, autre_entite, _personne(cx, "ailleurs"), type_de_page="HOME", slug="brouillon")

    pages = {p.identifiant: p for p in lister_les_pages_de_l_entite(cx, entite=entite)}

    assert len(pages) == 3, "les trois pages de CETTE entite, et pas une de plus"
    assert pages[brouillon].etat == EtatDePage.DRAFT.value
    assert pages[a_publier].etat == EtatDePage.PUBLISHED.value
    assert pages[a_archiver].etat == EtatDePage.ARCHIVED.value
    #  L'isolement n'est pas verifie par un compte : une page de l'AUTRE entite
    #  qui porterait le meme identifiant serait un accident statistique. Il est
    #  verifie en verifiant qu'aucun identifiant de l'autre entite n'apparait.
    autres = {p.identifiant for p in lister_les_pages_de_l_entite(cx, entite=autre_entite)}
    assert not (autres & pages.keys()), "aucune page ne doit apparaitre dans les deux listes"


@pytest.mark.integration
def test_la_LISTE_porte_circle_id_et_office_id_pour_que_l_ecran_s_y_retrouve(
    cx: Connection,
) -> None:
    """C'est ce que l'ecran confronte a l'identifiant du cercle deja consulte —
    sans cette colonne, aucun moyen de savoir QUELLE page est celle d'un cercle.
    """
    entite = _entite(cx, "L3")
    acteur = _personne(cx, "auteur")
    cercle = _cercle(cx, entite, "C1")
    page = _page(cx, entite, acteur, type_de_page="CIRCLE", slug="mon-cercle", cercle="C1")

    pages = {p.identifiant: p for p in lister_les_pages_de_l_entite(cx, entite=entite)}

    assert pages[page].circle_id == cercle
    assert pages[page].office_id is None


@pytest.mark.integration
def test_la_LECTURE_D_EDITION_sert_le_BROUILLON_que_T5_refuse(cx: Connection) -> None:
    """**LE COUPLE QUI PROUVE LA RAISON D'ETRE DE CETTE ROUTE.** La meme page,
    au meme instant : `lire_la_page_de_contenu` (T5) la refuse parce qu'elle
    n'est pas publiee ; `lire_une_page_pour_edition` (T10) la sert, PARCE
    qu'elle ne l'est pas encore — c'est l'ecran d'edition qui en a besoin.
    """
    entite = _entite(cx, "L4")
    acteur = _personne(cx, "auteur")
    page = _page(cx, entite, acteur, type_de_page="HOME", slug="en-cours")

    assert lire_la_page_de_contenu(cx, entite=entite, type_de_page="HOME", slug="en-cours") is None

    pour_edition = lire_une_page_pour_edition(cx, entite=entite, page=page)
    assert pour_edition is not None
    assert pour_edition.etat == EtatDePage.DRAFT.value
    assert pour_edition.version == 1
    assert pour_edition.blocs == ()


@pytest.mark.integration
def test_la_LECTURE_D_EDITION_sert_AUSSI_l_ARCHIVE(cx: Connection) -> None:
    """Sans quoi retrouver une page archivee pour la restaurer serait impossible
    — exactement le second motif du docstring de la route.
    """
    entite = _entite(cx, "L5")
    acteur = _personne(cx, "auteur")
    page = _page(cx, entite, acteur, type_de_page="LEGAL", slug="ancienne")
    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    pour_edition = lire_une_page_pour_edition(cx, entite=entite, page=page)
    assert pour_edition is not None
    assert pour_edition.etat == EtatDePage.ARCHIVED.value


@pytest.mark.integration
def test_la_LECTURE_D_EDITION_rend_None_pour_une_page_d_une_AUTRE_entite(cx: Connection) -> None:
    """La cle composite `(id, entity_id)` du §25.3 rend ce filtre aussi sur
    qu'une jointure explicite — meme garantie que la lecture publique de `T5`.
    """
    entite = _entite(cx, "L6")
    autre_entite = _entite(cx, "L7")
    acteur = _personne(cx, "auteur")
    page = _page(cx, entite, acteur, type_de_page="HOME", slug="accueil")

    assert lire_une_page_pour_edition(cx, entite=autre_entite, page=page) is None


@pytest.mark.integration
def test_la_VERSION_lue_pour_edition_PERMET_une_ecriture_qui_S_APPUIE_dessus(
    cx: Connection,
) -> None:
    """**LE ROND-POINT COMPLET, ET C'EST LE CRITERE REEL DE LA ROUTE** : un
    editeur qui recharge doit pouvoir relire SA version, puis ecrire avec elle
    sans jamais tomber sur `version_obsolete`.
    """
    entite = _entite(cx, "L8")
    acteur = _personne(cx, "auteur")
    page = _page(cx, entite, acteur, type_de_page="HOME", slug="accueil")

    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="Premier jet",
        blocs=(BlocDemande(type_de_bloc="TITLE", contenu={"texte": "Bonjour"}),),
        instant=DEMAIN,
    )
    assert ecrit.version == 2

    pour_edition = lire_une_page_pour_edition(cx, entite=entite, page=page)
    assert pour_edition is not None
    assert pour_edition.version == 2, "la lecture d'edition doit refleter le dernier ecrit"
    assert len(pour_edition.blocs) == 1

    #  La version RELUE reussit ; l'ANCIENNE, elle, doit toujours echouer —
    #  sans quoi cette route inviterait a un ecrasement silencieux (§18.4).
    reecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=pour_edition.version,
        titre="Second jet",
        blocs=(),
        instant=DEMAIN,
    )
    assert reecrit.version == 3

    with pytest.raises(ErreurApplicative) as erreur:
        remplacer_le_contenu(
            cx,
            entite=entite,
            page=page,
            acteur=acteur,
            version_attendue=1,
            titre="Ecrasement tente",
            blocs=(),
            instant=DEMAIN,
        )
    assert erreur.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_le_PERIMETRE_d_une_page_ARCHIVEE_n_est_PAS_l_ensemble_vide(cx: Connection) -> None:
    """**REGRESSION MESUREE EN STACK, PAS EN UNITAIRE.** `make framework-check`

    a fait tomber ce defaut au premier passage reel : la route `T10` refusait
    `ActionEditoriale.MODIFIER not in perimetre.actions`, et
    `_actions_selon_l_etat` ne rend jamais `MODIFIER` sur une page ARCHIVEE --
    seulement `RESTAURER`. La route qui existe precisement pour retrouver une
    page archivee la refusait donc systematiquement, 403, a qui avait pourtant
    tous les droits.

    **LE TEST EXACT N'EST PAS "MODIFIER EST ABSENT" -- CE SERAIT LE SYMPTOME.**
    Il est que l'ensemble n'est PAS VIDE : c'est `not perimetre.actions` que la
    route doit tester, jamais l'absence d'une action precise.
    """
    entite = _entite(cx, "L9")
    acteur = _personne(cx, "auteur")
    page = _page(cx, entite, acteur, type_de_page="LEGAL", slug="archivee-t10")
    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=DEMAIN
    )

    perimetre = _perimetre(cx, entite=entite, acteur=acteur, page=page, roles={RoleDeLaMatrice.ESM})

    assert perimetre == frozenset({ActionEditoriale.RESTAURER})
    assert perimetre, "l'ensemble n'est PAS vide : la route de gestion doit donc servir cette page"
    assert ActionEditoriale.MODIFIER not in perimetre
