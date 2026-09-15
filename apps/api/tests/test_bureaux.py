"""La page detaillee d'un bureau — LOT 6, `T4`, story `MVP-L06-US003`.

CE QUE CETTE SUITE EPROUVE, ET QUI EST L'INVERSE DE `T3`

  `T3` prouvait qu'un filtre EXCLUT ce qu'il doit exclure. Ici la propriete la
  plus delicate est qu'une lecture **N'INVENTE PAS UNE BORNE QUE LA BASE NE TIENT
  PAS**.

  Le §8.4 veut « un bureau possede entre un et trois responsables actifs
  lorsqu'il est publie ». Aucune contrainte de ligne ne l'exprime, et le
  declencheur qui le tiendra est pose en `T7` (`DEC-583`). Le decor produit donc
  **exactement ce que la borne interdit** :

    - un bureau **PUBLIE** a **ZERO** responsable ;
    - un bureau **PUBLIE** a **QUATRE** responsables.

  **Ces deux cas ne sont pas des curiosites : ils sont l'etat REEL de la base au
  15/09/2026**, et un service qui aurait suppose « au moins un » se serait
  effondre sur le premier, un qui aurait tronque a trois aurait **menti** sur le
  second. Aucun des deux echecs n'aurait ete visible avec un decor a deux
  responsables.

LE COUPLE DU §7.42, ICI SUR `location_text`

  Le §8.3 declare « `location_text` | **Facultatif** » : la colonne est nullable.
  Le decor porte donc un bureau **avec** localisation et un bureau **sans**, et
  la chaine « None » est cherchee — `str(None)` l'a servie sur 100 % des cercles
  pendant deux lots (defaut `T10-8`).

LES TROIS BUREAUX SONT DES DONNEES

  « Bureaux initiaux : BDS ; BDE ; BDG. Ils restent **entierement
  configurables**. » Aucun de ces codes n'apparait dans ce fichier, et un test
  **exige** qu'ils n'apparaissent nulle part dans `app/`.
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.organization.bureaux import BureauDetaille, lire_le_bureau
from app.organization.framework import chemin_du_bureau
from app.shared.database import moteur

MARQUEUR = "L6T4"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


# ============================================================================
#  1. Ce que le corpus ECRIT, verifie sans base
# ============================================================================
CODES_INITIAUX = frozenset({"BDS", "BDE", "BDG"})


def _codes_en_dur(source: str) -> list[str]:
    """Les codes de bureau initiaux ecrits en position EXECUTABLE, s'il y en a.

    **LE DISCRIMINANT N'EST PAS LE TEXTE, C'EST L'AST — ET J'AI PAYE POUR LE
    SAVOIR.** Ma premiere version cherchait `\bBDS\b` dans les lignes du
    fichier, et elle a echoue sur **cinq** citations du cahier en docstring,
    dont trois dans le module qu'elle etait censee proteger. C'est mot pour mot
    la premiere version du garde-fou du §7.25 — « elle se declenchait sur le
    **commentaire** expliquant le motif qu'elle interdit » — et un garde-fou a
    faux positifs apprend a passer outre.

    Ce que le critere « entierement configurables » interdit est un code qui se
    **comporte** differemment selon le bureau. Un littéral cite dans une prose
    ne se comporte pas. Deux proprietes de l'`ast` donnent l'exactitude
    gratuitement :

      - **les commentaires n'y figurent pas du tout** ;
      - **les docstrings sont identifiables**, ce sont les premieres expressions
        d'un module, d'une classe ou d'une fonction.

    Tout autre littéral de chaine est, lui, une valeur que le code manipule.
    """
    arbre = ast.parse(source)
    docstrings: set[int] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            corps = noeud.body
            if corps and isinstance(corps[0], ast.Expr):
                valeur = corps[0].value
                if isinstance(valeur, ast.Constant) and isinstance(valeur.value, str):
                    docstrings.add(id(valeur))

    return [
        f"ligne {n.lineno} : {n.value!r}"
        for n in ast.walk(arbre)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstrings
        and any(code in n.value for code in CODES_INITIAUX)
    ]


def test_le_garde_fou_des_codes_en_dur_SAIT_ECHOUER() -> None:
    """**Le temoin, et sans lui le test suivant ne prouverait rien.**

    Un controle qui ne cherche rien rend une liste vide sur tout — donc vert
    partout. Ces deux sources ne different que par la POSITION du littéral.
    """
    prose = '"""Bureaux initiaux : BDS ; BDE ; BDG, entierement configurables."""\n'
    logique = 'def f(code: str) -> bool:\n    """Bureaux : BDS, BDE."""\n    return code == "BDS"\n'

    assert _codes_en_dur(prose) == [], "une CITATION en docstring ne se comporte pas"
    assert _codes_en_dur(logique), "un littéral EXECUTABLE doit etre nomme"
    assert "'BDS'" in _codes_en_dur(logique)[0]


def test_aucun_code_de_bureau_initial_n_est_ecrit_en_dur_dans_le_code() -> None:
    """« Bureaux initiaux : BDS ; BDE ; BDG. Ils restent entierement configurables. »

    **C'est le premier membre du critere de `MVP-L06-US003`** — « BDS, BDE et BDG
    sont **configurables** » — et il se prouve par une ABSENCE, ce qui demande de
    dire ou l'on a cherche (§7.0, troisieme proposition).

    Le perimetre est **derive du disque** a chaque execution, jamais recopie
    (§7.27) : tout module de `apps/api/app/`. Le compte examine est affiche, et
    le garde-fou lui-meme a son temoin juste au-dessus.
    """
    racine = pathlib.Path(__file__).resolve().parents[1] / "app"
    modules = sorted(racine.rglob("*.py"))
    assert len(modules) > 30, f"perimetre suspect : {len(modules)} modules"

    fautifs = {
        str(m.relative_to(racine)): trouves
        for m in modules
        if (trouves := _codes_en_dur(m.read_text(encoding="utf-8")))
    }
    assert not fautifs, (
        f"{len(modules)} modules examines ; ces litteraux EXECUTABLES portent un code "
        f"de bureau initial, ce que « entierement configurables » interdit : {fautifs}"
    )


def test_le_chemin_detaille_est_celui_que_la_carte_de_T2_emet_deja() -> None:
    """**Le chemin ne doit pas etre reinvente ici.**

    `T2` emet `chemin_du_bureau(...)` sur chaque carte de bureau, et ce chemin ne
    menait nulle part avant `T4`. Si cette sous-etape en forgeait un autre, la
    carte de la page Framework pointerait vers une adresse morte **sans qu'aucun
    test ne le dise**. Ce test lie les deux.
    """
    assert chemin_du_bureau("BDX", "ZZZ") == "/entites/BDX/framework/bureaux/ZZZ"


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


def _entite(cx: Connection, suffixe: str) -> tuple[uuid.UUID, str]:
    code = f"{MARQUEUR}{suffixe}"
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        #  Un parametre PAR COLONNE — §7.25, defaut `T1-2`. `entity.code` est
        #  `varchar(64)` quand `display_name` et `city` sont `text` :
        #  `make parametres-check` refuse desormais le partage.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return identifiant, code


def _bureau(
    cx: Connection,
    entite: uuid.UUID,
    code: str,
    *,
    localisation: str | None = None,
    description: str | None = None,
    rang: int = 1,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, description, location_text, "
            "display_order) VALUES (:e, :code, :nom, :desc, :lieu, :rang) RETURNING id"
        ),
        {
            "e": entite,
            "code": code,
            "nom": code,
            "desc": description,
            "lieu": localisation,
            "rang": rang,
        },
    ).scalar_one()


def _personne(cx: Connection, nom: str, prenom: str = "Prenom") -> uuid.UUID:
    adresse = f"{MARQUEUR}-{nom}-{uuid.uuid4().hex[:6]}@exalt.test".lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, :prenom, :nom, 'active') RETURNING id"
        ),
        #  `email_normalized` EN MINUSCULES — contrainte du LOT 2, defaut `T2-1`.
        {"a": adresse, "b": adresse, "prenom": prenom, "nom": nom},
    ).scalar_one()


def _responsable(
    cx: Connection,
    entite: uuid.UUID,
    bureau: uuid.UUID | None,
    *,
    nom: str,
    prenom: str = "Prenom",
    type_de_responsabilite: str = "OFFICE_MANAGER",
    cercle: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
    archive: bool = False,
) -> uuid.UUID:
    """Une personne et son affectation Framework.

    `:p` sert `person_id` ET `assigned_by_person_id` : deux colonnes `uuid`,
    reutilisation parfaitement legitime — c'est l'un des partages que
    `make parametres-check` compte et laisse passer (§7.25).
    """
    personne = _personne(cx, nom, prenom)
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, office_id, assigned_by_person_id, "
            "starts_at, ends_at, archived_at) "
            "VALUES (:p, :e, :t, :c, :b, :p, :d, :f, :archive)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_de_responsabilite,
            "c": cercle,
            "b": bureau,
            "d": debut,
            "f": fin,
            "archive": JANVIER if archive else None,
        },
    )
    return personne


def _page(
    cx: Connection,
    entite: uuid.UUID,
    *,
    bureau: uuid.UUID | None = None,
    cercle: uuid.UUID | None = None,
    type_de_page: str = "OFFICE",
    etat: str = "published",
    archive: bool = False,
) -> None:
    """Une page de contenu — c'est ELLE qui porte la publication (`DEC-576`)."""
    slug = f"{MARQUEUR}-{uuid.uuid4().hex[:10]}"
    cx.execute(
        text(
            "INSERT INTO content_page (entity_id, page_type, circle_id, office_id, title, "
            "slug, state, archived_at) "
            "VALUES (:e, :type, :c, :b, :titre, :slug, :etat, :archive)"
        ),
        #  `title` est `text` et `slug` est `varchar(160)` : deux parametres.
        {
            "e": entite,
            "type": type_de_page,
            "c": cercle,
            "b": bureau,
            "titre": slug,
            "slug": slug,
            "etat": etat,
            "archive": JANVIER if archive else None,
        },
    )


def _lire(
    cx: Connection,
    entite: uuid.UUID,
    code_entite: str,
    code_bureau: str,
    *,
    instant: dt.datetime = JUIN,
) -> BureauDetaille | None:
    return lire_le_bureau(
        cx,
        entite=entite,
        code_entite=code_entite,
        code_bureau=code_bureau,
        instant=instant,
    )


# ----------------------------------------------------------------------------
#  2.1 LA BORNE DU §8.4 N'EST PAS TENUE, ET LA LECTURE NE DOIT PAS LA SUPPOSER
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_un_bureau_PUBLIE_a_ZERO_responsable_est_rendu_tel_quel(cx: Connection) -> None:
    """**Ce que le §8.4 interdit, et que la base permet.**

    Un service qui aurait suppose « au moins un » se serait effondre ici. La
    lecture rend `0`, et elle dit que le bureau est **publie** — c'est ce couple
    qui permet a un client de signaler l'ecart.
    """
    entite, code = _entite(cx, "ZERO")
    bureau = _bureau(cx, entite, "VIDE")
    _page(cx, entite, bureau=bureau)

    lu = _lire(cx, entite, code, "VIDE")

    assert lu is not None
    assert lu.responsables == ()
    assert lu.nombre_de_responsables == 0
    assert lu.publie is True, "la page de contenu est `published` : le bureau EST publie"


@pytest.mark.integration
def test_un_bureau_PUBLIE_a_QUATRE_responsables_les_rend_TOUS_LES_QUATRE(
    cx: Connection,
) -> None:
    """**Ce que le §8.4 interdit dans l'autre sens, et que la base permet.**

    Un service qui aurait tronque a trois aurait **menti** — et le mensonge
    aurait ete invisible avec un decor a deux responsables.
    """
    entite, code = _entite(cx, "QUATRE")
    bureau = _bureau(cx, entite, "TROP")
    _page(cx, entite, bureau=bureau)
    for nom in ("Aa", "Bb", "Cc", "Dd"):
        _responsable(cx, entite, bureau, nom=nom)

    lu = _lire(cx, entite, code, "TROP")

    assert lu is not None
    assert lu.nombre_de_responsables == 4, "quatre en base, quatre rendus"
    assert [r.nom for r in lu.responsables] == ["Aa", "Bb", "Cc", "Dd"]


@pytest.mark.integration
def test_un_bureau_NON_publie_a_zero_responsable_est_legitime(cx: Connection) -> None:
    """**Le temoin qui rend le test precedent non trivial.**

    Zero responsable sur un bureau **non publie** n'enfreint rien : la borne du
    §8.4 ne mord « **lorsqu'il est publie** ». Sans ce temoin, on ne saurait pas
    si `publie` discrimine quoi que ce soit.
    """
    entite, code = _entite(cx, "BROUILLON")
    _bureau(cx, entite, "NEUF")

    lu = _lire(cx, entite, code, "NEUF")

    assert lu is not None
    assert lu.nombre_de_responsables == 0
    assert lu.publie is False, "aucune page de contenu : le bureau n'est pas publie"


@pytest.mark.integration
def test_le_nombre_rendu_est_DERIVE_du_tuple_et_non_compte_a_part(cx: Connection) -> None:
    """Deux sources pour une meme grandeur divergent (§7.0, sixieme proposition)."""
    entite, code = _entite(cx, "DERIVE")
    bureau = _bureau(cx, entite, "UN")
    _responsable(cx, entite, bureau, nom="Seul")

    lu = _lire(cx, entite, code, "UN")

    assert lu is not None
    assert lu.nombre_de_responsables == len(lu.responsables) == 1


# ----------------------------------------------------------------------------
#  2.2 `publie` VIENT DE LA PAGE DE CONTENU — chaque cause a son temoin
# ----------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize(
    ("etat", "archive", "type_de_page", "attendu", "motif"),
    [
        ("published", False, "OFFICE", True, "le cas nominal — le TEMOIN POSITIF"),
        ("draft", False, "OFFICE", False, "une page en brouillon ne publie pas"),
        ("archived", False, "OFFICE", False, "une page archivee ne publie pas"),
        ("published", True, "OFFICE", False, "une page publiee PUIS archivee ne publie plus"),
        ("published", False, "HOME", False, "une page d'un AUTRE type ne publie pas le bureau"),
    ],
)
def test_publie_discrimine_l_etat_le_type_et_l_archivage_de_la_page(
    cx: Connection,
    etat: str,
    archive: bool,
    type_de_page: str,
    attendu: bool,
    motif: str,
) -> None:
    """**Quatre refus et UN temoin positif, et le temoin est indispensable.**

    Sans lui, un `EXISTS` qui ne trouverait jamais rien rendrait `False` partout
    et les quatre refus resteraient verts — exactement les huit refus du defaut
    `T2-3`.

    Chaque ligne ne differe de la premiere que par **LA valeur en cause**.
    """
    entite, code = _entite(cx, f"PUB{type_de_page}{etat}{int(archive)}")
    bureau = _bureau(cx, entite, "CIBLE")
    #  Une page `HOME` ne peut pas porter d'`office_id` : la contrainte
    #  `office_id_requis_pour_une_page_de_bureau` est une IMPLICATION et n'interdit
    #  rien ailleurs, mais rattacher la page au bureau ferait du type le SEUL
    #  discriminant, ce qui est precisement ce qu'on veut eprouver.
    _page(
        cx,
        entite,
        bureau=bureau,
        type_de_page=type_de_page,
        etat=etat,
        archive=archive,
    )

    lu = _lire(cx, entite, code, "CIBLE")

    assert lu is not None
    assert lu.publie is attendu, motif


@pytest.mark.integration
def test_la_page_publiee_d_un_AUTRE_bureau_ne_publie_pas_celui_ci(cx: Connection) -> None:
    """Le rattachement se fait par `office_id`, et il est verifie."""
    entite, code = _entite(cx, "AUTREBUR")
    cible = _bureau(cx, entite, "CIBLE")
    voisin = _bureau(cx, entite, "VOISIN", rang=2)
    _page(cx, entite, bureau=voisin)

    lu = _lire(cx, entite, code, "CIBLE")
    voisin_lu = _lire(cx, entite, code, "VOISIN")

    assert lu is not None
    assert voisin_lu is not None
    assert lu.publie is False, "la page est celle du voisin"
    assert voisin_lu.publie is True, "le temoin : le voisin, lui, EST publie"
    assert cible != voisin


# ----------------------------------------------------------------------------
#  2.3 QUI EST RESPONSABLE — chaque exclusion appariee a son temoin
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_une_affectation_ARCHIVEE_ne_designe_personne(cx: Connection) -> None:
    entite, code = _entite(cx, "ARCH")
    bureau = _bureau(cx, entite, "B")
    _responsable(cx, entite, bureau, nom="Archive", archive=True)
    _responsable(cx, entite, bureau, nom="Vivant")

    lu = _lire(cx, entite, code, "B")

    assert lu is not None
    assert [r.nom for r in lu.responsables] == ["Vivant"]


@pytest.mark.integration
def test_seul_l_INSTANT_avance_et_le_responsable_apparait_puis_disparait(
    cx: Connection,
) -> None:
    """**Le temoin le plus discriminant de la suite.**

    La meme ligne, la meme personne, le meme bureau : **seul l'instant change**.
    Un filtre de periode trop large ou absent donnerait le meme resultat aux
    trois instants, et aucun autre test ne le dirait.
    """
    entite, code = _entite(cx, "INSTANT")
    bureau = _bureau(cx, entite, "B")
    #  Une affectation qui court de juin a decembre.
    _responsable(cx, entite, bureau, nom="Futur", debut=JUIN, fin=DECEMBRE)

    avant = _lire(cx, entite, code, "B", instant=JANVIER)
    pendant = _lire(cx, entite, code, "B", instant=dt.datetime(2026, 8, 1, tzinfo=dt.UTC))
    apres = _lire(cx, entite, code, "B", instant=dt.datetime(2027, 1, 1, tzinfo=dt.UTC))

    assert avant is not None and pendant is not None and apres is not None
    assert avant.nombre_de_responsables == 0, "une affectation FUTURE ne designe personne"
    assert [r.nom for r in pendant.responsables] == ["Futur"], "le TEMOIN : elle est active"
    assert apres.nombre_de_responsables == 0, "une affectation CLOSE ne designe personne"


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


@pytest.mark.integration
def test_la_base_INTERDIT_TOUJOURS_un_BOOSTER_porteur_d_un_office_id(cx: Connection) -> None:
    """**C'EST CE TEST QUI PROTEGE, ET NON LE FILTRE SUR LE TYPE. §7.32.**

    Le filtre `responsibility_type = 'OFFICE_MANAGER'` de la requete est
    **redondant** : mesure du 15/09/2026, le retirer laisse les vingt-trois tests
    verts, parce que `ck_framework_responsibility_assignment_portee_selon_le_type`
    impose `office_id IS NULL` a tout `BOOSTER`. Mon test precedent affirmait le
    contraire -- « le type est un discriminant reel » -- et c'etait faux
    (defaut `T4-2`).

    Ce qui rend la requete correcte est donc une contrainte d'une AUTRE table, et
    le §7.32 dit quoi faire de cette situation : ne pas garder une defense contre
    un etat impossible, mais **exiger que la base continue de l'interdire**, sur
    le NOM de la contrainte. Si un lot ulterieur la relachait, ce test echouerait
    -- et celui qui la relache saurait qu'il doit relire cette lecture.
    """
    entite, _ = _entite(cx, "CONTRAINTE")
    bureau = _bureau(cx, entite, "B")
    cercle = _cercle(cx, entite, "CERCLE")
    personne = _personne(cx, "Tricheur")

    with pytest.raises(IntegrityError) as leve:
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, circle_id, office_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'BOOSTER', :c, :b, :p, :d)"
            ),
            {"p": personne, "e": entite, "c": cercle, "b": bureau, "d": JANVIER},
        )

    #  **LE NOM, ET NON UN CODE D'ERREUR.** Une violation quelconque donnerait la
    #  meme observation qu'un `IntegrityError` d'une autre cause.
    assert "ck_framework_responsibility_assignment_portee_selon_le_type" in str(leve.value)


@pytest.mark.integration
def test_un_BOOSTER_n_apparait_pas_parmi_les_responsables_du_bureau(cx: Connection) -> None:
    """Le fait observable, dont le test precedent donne la CAUSE reelle.

    Un Booster n'apparait pas ici, et ce n'est pas le filtre sur le type qui
    l'ecarte : c'est que son `office_id` est **nul par contrainte**, donc
    `fr.office_id = :bureau` ne le rencontre jamais.
    """
    entite, code = _entite(cx, "TYPE")
    bureau = _bureau(cx, entite, "B")
    cercle = _cercle(cx, entite, "CERCLE")
    _responsable(cx, entite, None, nom="Booster", type_de_responsabilite="BOOSTER", cercle=cercle)
    _responsable(cx, entite, bureau, nom="Bureau")

    lu = _lire(cx, entite, code, "B")

    assert lu is not None
    assert [r.nom for r in lu.responsables] == ["Bureau"]


@pytest.mark.integration
def test_le_responsable_d_un_AUTRE_bureau_n_apparait_pas(cx: Connection) -> None:
    entite, code = _entite(cx, "AUTREB")
    cible = _bureau(cx, entite, "CIBLE")
    voisin = _bureau(cx, entite, "VOISIN", rang=2)
    _responsable(cx, entite, voisin, nom="Voisin")
    _responsable(cx, entite, cible, nom="Cible")

    lu = _lire(cx, entite, code, "CIBLE")

    assert lu is not None
    assert [r.nom for r in lu.responsables] == ["Cible"]


@pytest.mark.integration
def test_l_ordre_des_responsables_est_TOTAL(cx: Connection) -> None:
    """Deux homonymes exigent un dernier terme : sans lui, l'ordre flotte."""
    entite, code = _entite(cx, "ORDRE")
    bureau = _bureau(cx, entite, "B")
    _responsable(cx, entite, bureau, nom="Meme", prenom="Zoe")
    _responsable(cx, entite, bureau, nom="Meme", prenom="Alice")
    _responsable(cx, entite, bureau, nom="Aaa", prenom="Yves")

    premier = _lire(cx, entite, code, "B")
    second = _lire(cx, entite, code, "B")

    assert premier is not None and second is not None
    assert [(r.nom, r.prenom) for r in premier.responsables] == [
        ("Aaa", "Yves"),
        ("Meme", "Alice"),
        ("Meme", "Zoe"),
    ]
    #  Compare les reponses TELLES QU'ELLES SONT, sans retrier — un `sorted()`
    #  des deux cotes serait aveugle a l'ordre (§7.35).
    assert premier.responsables == second.responsables


# ----------------------------------------------------------------------------
#  2.4 LE COUPLE DU §7.42 — `location_text` est FACULTATIF au §8.3
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_la_localisation_absente_n_est_JAMAIS_la_chaine_None(cx: Connection) -> None:
    """**Le couple du §7.42, et la chaine est cherchee.**

    `str(None)` rend « None » — un texte de localisation parfaitement plausible,
    servi sur 100 % des cercles pendant deux lots (defaut `T10-8`). Ni moitie du
    couple ne suffit : sans le temoin, un code qui ne rendrait **jamais** de
    localisation passerait ; sans le cas, `str(None)` reste invisible.
    """
    entite, code = _entite(cx, "LIEU")
    _bureau(cx, entite, "AVEC", localisation="Bordeaux, 2e etage")
    _bureau(cx, entite, "SANS", rang=2)

    avec = _lire(cx, entite, code, "AVEC")
    sans = _lire(cx, entite, code, "SANS")

    assert avec is not None and sans is not None
    assert avec.localisation == "Bordeaux, 2e etage", "le TEMOIN : la valeur est servie"
    assert sans.localisation is None
    assert sans.localisation != "None"


@pytest.mark.integration
def test_la_description_absente_n_est_JAMAIS_la_chaine_None(cx: Connection) -> None:
    """Meme couple sur `description`, que le §8.3 declare « Contenu »."""
    entite, code = _entite(cx, "DESC")
    _bureau(cx, entite, "AVEC", description="Le bureau qui organise les tournois")
    _bureau(cx, entite, "SANS", rang=2)

    avec = _lire(cx, entite, code, "AVEC")
    sans = _lire(cx, entite, code, "SANS")

    assert avec is not None and sans is not None
    assert avec.description == "Le bureau qui organise les tournois"
    assert sans.description is None


# ----------------------------------------------------------------------------
#  2.5 LES TROIS CAUSES DE `None`, ET LE TEMOIN QUI LES REND NON TRIVIALES
# ----------------------------------------------------------------------------
@pytest.mark.integration
def test_un_code_inconnu_rend_None(cx: Connection) -> None:
    entite, code = _entite(cx, "INCONNU")
    _bureau(cx, entite, "EXISTE")

    assert _lire(cx, entite, code, "EXISTE") is not None, "le TEMOIN"
    assert _lire(cx, entite, code, "ABSENT") is None


@pytest.mark.integration
def test_un_bureau_ARCHIVE_rend_None(cx: Connection) -> None:
    """Le §10.2 porte « Restaurer », donc une lecture d'archive viendra — avec sa
    PROPRE route et sa propre grille de roles (§7.41)."""
    entite, code = _entite(cx, "ARCHIVE")
    bureau = _bureau(cx, entite, "MORT")
    _bureau(cx, entite, "VIF", rang=2)
    cx.execute(
        text("UPDATE office SET archived_at = :quand WHERE id = :id"),
        {"quand": JANVIER, "id": bureau},
    )

    assert _lire(cx, entite, code, "VIF") is not None, "le TEMOIN"
    assert _lire(cx, entite, code, "MORT") is None


@pytest.mark.integration
def test_le_bureau_d_une_AUTRE_entite_rend_None(cx: Connection) -> None:
    """Le cloisonnement du §25.3, eprouve sur le MEME code de bureau."""
    premiere, code_premiere = _entite(cx, "ENT1")
    seconde, code_seconde = _entite(cx, "ENT2")
    _bureau(cx, seconde, "PARTAGE")

    assert _lire(cx, seconde, code_seconde, "PARTAGE") is not None, "le TEMOIN"
    assert _lire(cx, premiere, code_premiere, "PARTAGE") is None
