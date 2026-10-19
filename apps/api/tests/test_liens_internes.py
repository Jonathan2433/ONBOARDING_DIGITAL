"""La presentation de l'entite et les liens internes — LOT 6, `T8`, `MVP-L06-US005`.

LE CRITERE A DEUX MEMBRES, ET LE SECOND EST SATISFAIT PAR UNE API QUI N'ECRIT
RIEN

  « Presentation, Hub, Academy et SharePoint sont modifiables localement ; **les
  URL sont validees**. »

  **« Les URL sont validees » est parfaitement tenu par une route qui refuse
  TOUT.** C'est le §7.39, et c'est ce qui a coute la fusion de `T5` et `T6` au
  LOT 5. Chaque refus est donc apparie a un temoin qui ne differe QUE par la
  valeur en cause :

      refuse                          temoin qui ne differe que par...
      'http://hub.exemple.test/'      le `s`      -> 'https://hub.exemple.test/'
      'https:hub.exemple.test'        les `//`    -> 'https://hub.exemple.test'
      'javascript:alert(1)'           le protocole-> 'https://alert(1)'

  Sans ces temoins, un `valider_une_url` qui leverait sur tout laisserait les
  quinze refus verts — exactement le defaut `T2-3` du LOT 5, ou HUIT epreuves de
  refus passaient sur une route qui refusait les trois valeurs valides.

CE QUE LA MESURE A TROUVE, ET QUE LA PHRASE DU CORPUS NE DIT PAS

  Le §15.3 dit « une liste de protocoles autorises ». **Une liste de protocoles
  ne suffit pas**, et ces tests le mesurent : `https:alert(1)` a pour protocole
  `https`, donc une liste blanche l'accepte — et il n'adresse aucune ressource.
  C'est `url_sans_hote`, et c'est le seul refus qu'une lecture litterale de la
  phrase aurait omis.

CE QUE `T8` N'A PAS ECRIT, ET QUI EST DONC MESURE PLUTOT QU'AFFIRME

  La « presentation de l'entite » du §13 est une page `HOME`, que `T6` cree et
  ecrit. Deux tests exigent que la grille obtenue soit celle que le §13 nomme —
  les trois roles de portee entite, et rien pour une portee locale. **Ils
  echoueront si un lot ulterieur donne une portee locale a `HOME`**, ce qui est
  precisement leur objet (§7.32).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.content.ecriture import creer_une_page
from app.content.liens import (
    CODE_LIEN_INTROUVABLE,
    CODE_ORDRE_INCOMPLET,
    CODE_TYPE_DE_LIEN_REFUSE,
    CODE_URL_AMBIGUE,
    CODE_URL_ILLISIBLE,
    CODE_URL_NON_CHIFFREE,
    CODE_URL_PROTOCOLE_REFUSE,
    CODE_URL_SANS_HOTE,
    CODE_VERSION_OBSOLETE,
    CONTRAINTE_URL_HTTPS,
    PROTOCOLE_EN_CLAIR,
    PROTOCOLES_AUTORISES,
    creer_un_lien,
    lister_les_liens,
    modifier_un_lien,
    reordonner_les_liens,
    valider_un_type_de_lien,
    valider_une_url,
)
from app.content.modeles import TYPES_DE_LIEN, TypeDeLien
from app.content.perimetre import (
    PORTEES_LOCALES,
    ROLES_DE_CREATION,
    ROLES_DE_GESTION_DES_LIENS,
    ROLES_DE_PORTEE_ENTITE,
    TYPES_SANS_PORTEE_LOCALE,
    ActionEditoriale,
    resoudre_le_perimetre_editorial,
)
from app.content.routes import (
    DemandeDeCreationDeLien,
    DemandeDeModificationDeLien,
    DemandeDOrdreDesLiens,
    LienInterneServi,
    routeur_contenus,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L6T8"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)

RACINE = pathlib.Path(__file__).resolve().parents[3]
MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"
MIGRATION_0019 = "apps/api/alembic/versions/0019_protocole_des_liens_internes.py"


def _code(erreur: ErreurApplicative) -> str:
    return erreur.code


def _refus(url: str) -> str:
    """Le code de refus rendu par `valider_une_url`, ou l'echec du test."""
    with pytest.raises(ErreurApplicative) as capture:
        valider_une_url(url)
    return _code(capture.value)


# ============================================================================
#  1. `QO-120` — la liste de protocoles, et ce qu'elle ne suffit pas a tenir
# ============================================================================
def test_QO_120_la_liste_est_https_SEUL_et_le_message_la_DERIVE() -> None:
    """**`DEC-587` : `https` seul.** `QO-120` close, apres avoir bloque `T8`.

    Le §15.3 et le cahier §13 ecrivent « une liste de protocoles autorises » et
    **ne la donnent pas** — zero occurrence. La liste est donc DECLAREE, et le
    message d'erreur la **derive** : l'elargir ne peut pas laisser derriere lui un
    libelle qui annonce l'ancienne (§7.27).
    """
    from app.content.liens import MESSAGE_URL_PROTOCOLE_REFUSE

    assert frozenset({"https"}) == PROTOCOLES_AUTORISES
    for protocole in PROTOCOLES_AUTORISES:
        assert protocole in MESSAGE_URL_PROTOCOLE_REFUSE, (
            "le message doit enumerer ce qu'il autorise — sinon un refus n'apprend rien"
        )
    assert PROTOCOLE_EN_CLAIR not in PROTOCOLES_AUTORISES


def test_QO_120_le_corpus_ne_donne_AUCUN_protocole__la_mesure_qui_a_ouvert_la_question() -> None:
    """**ZERO OCCURRENCE, ET C'EST CE QUI REND LA DECISION NECESSAIRE.**

    Ce test n'eprouve pas du code : il eprouve la PREMISSE de `DEC-587`. Le jour
    ou un document de cadrage nommerait un protocole, il echouerait — et c'est
    exactement ce qu'on veut, parce que la decision devrait alors etre relue
    contre la source (§7.29, §7.41).
    """
    documents = (
        "docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md",
        "docs/architecture/MODELE_DONNEES_EXALT.md",
        "docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md",
        "docs/product/ROADMAP_MVP_V1_V2_EXALT.md",
        "docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md",
    )
    motif = re.compile(r"https?://|mailto:|javascript:|ftp://|data:|tel:", re.IGNORECASE)
    trouves: list[str] = []
    for chemin in documents:
        for ligne in (RACINE / chemin).read_text(encoding="utf-8").splitlines():
            trouves.extend(f"{chemin} : {t}" for t in motif.findall(ligne))
    assert trouves == [], "le corpus nomme desormais un protocole — relire `DEC-587`"


def test_UNE_LISTE_DE_PROTOCOLES_NE_SUFFIT_PAS__mesure_du_22_09_2026() -> None:
    """**LE CONSTAT LE PLUS UTILE DE `T8`, ET IL CONTREDIT LA LECTURE NAIVE.**

    Les trois adresses ci-dessous ont pour protocole `https`. Une validation qui
    s'arreterait a la « liste de protocoles autorises » du §15.3 les accepterait
    toutes les trois — et aucune n'adresse de ressource.

    Le temoin qui rend ce test non trivial est la QUATRIEME ligne : la meme
    adresse, avec un hote, passe.
    """
    assert _refus("https:alert(1)") == CODE_URL_SANS_HOTE
    assert _refus("https:/hub.exemple.test") == CODE_URL_SANS_HOTE
    assert _refus("https://") == CODE_URL_SANS_HOTE
    #  LE TEMOIN — seul l'hote est ajoute.
    assert valider_une_url("https://hub.exemple.test") == "https://hub.exemple.test"


def test_http_est_refuse_SOUS_SON_PROPRE_CODE__et_le_temoin_ne_differe_que_par_le_s() -> None:
    """**UN CONTROLE EXACT VAUT MIEUX QU'UN CONTROLE LARGE** (§7.25).

    `http` est la seule adresse qu'un auteur tape en croyant bien faire. Lui
    rendre « protocole inconnu » lui ferait chercher une faute de frappe la ou il
    manque un `s`.
    """
    assert _refus("http://hub.exemple.test/") == CODE_URL_NON_CHIFFREE
    assert _refus("HTTP://hub.exemple.test/") == CODE_URL_NON_CHIFFREE
    #  LE TEMOIN — un seul caractere separe les deux.
    assert valider_une_url("https://hub.exemple.test/") == "https://hub.exemple.test/"


def test_les_protocoles_DANGEREUX_sont_refuses__et_le_temoin_les_apparie() -> None:
    """Le critere 6 du lot — « aucun contenu arbitraire ne peut injecter du code ».

    Un `javascript:` place dans un `href` s'execute au clic. Ce refus est la
    moitie applicative de la garantie ; l'autre moitie est la contrainte
    `ck_internal_link_url_https`, que la migration `0019` pose et qu'un test
    d'integration eprouve par une insertion SQL directe.
    """
    for hostile in (
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "ftp://serveur/fichier",
        "mailto:contact@exemple.test",
    ):
        assert _refus(hostile) == CODE_URL_PROTOCOLE_REFUSE, hostile
    #  LE TEMOIN — la meme charge, derriere un protocole autorise et un hote :
    #  ce n'est PAS le texte « alert(1) » qui est refuse, c'est le protocole.
    assert valider_une_url("https://exemple.test/alert(1)") == "https://exemple.test/alert(1)"


def test_une_adresse_SANS_protocole_est_refusee__y_compris_la_forme_relative() -> None:
    """`//hote/chemin` herite du protocole de la page qui l'affiche.

    Le §15.3 veut une adresse validee « selon une liste de protocoles » : une
    adresse qui n'en porte aucun n'est pas validable, elle est indeterminee.
    """
    assert _refus("hub.exemple.test") == CODE_URL_ILLISIBLE
    assert _refus("//hub.exemple.test/") == CODE_URL_ILLISIBLE
    assert _refus(":sans-protocole") == CODE_URL_ILLISIBLE
    assert _refus("   ") == CODE_URL_ILLISIBLE


def test_url_AMBIGUE__le_protocole_TAPE_doit_etre_celui_qui_est_LU() -> None:
    """**MESURE DU 22/09/2026 : `urlsplit` RETIRE `\\t`, `\\r` ET `\\n` EN SILENCE.**

        'java\\nscript:alert(1)'  ->  scheme 'javascript'
        'java\\tscript:alert(1)'  ->  scheme 'javascript'

    Un controle qui lirait la chaine BRUTE verrait `java\\nscript` la ou le
    navigateur verra `javascript`. `url_ambigue` refuse toute divergence entre le
    segment tape et le protocole lu, **sans enumerer les caracteres en cause** :
    recopier la liste interne de CPython la ferait vieillir a la premiere version
    (§7.27), et ce test passerait toujours en ne prouvant plus rien.

    **LE TEMOIN EST UNE ACCEPTATION** : la casse, elle, est une difference
    legitime, et `HTTPS://` doit passer.
    """
    assert _refus("java\nscript:alert(1)") == CODE_URL_AMBIGUE
    assert _refus("java\tscript:alert(1)") == CODE_URL_AMBIGUE
    assert _refus("ht\rtps://hub.exemple.test/") == CODE_URL_AMBIGUE
    #  LE TEMOIN — la casse n'est PAS une ambiguite.
    assert valider_une_url("HTTPS://hub.exemple.test/") == "https://hub.exemple.test/"


def test_la_NORMALISATION_ne_touche_QUE_le_protocole() -> None:
    """Le chemin, la requete et le fragment sont rendus a l'octet pres.

    Un serveur peut y etre sensible a la casse : minusculiser l'adresse entiere
    casserait un lien SharePoint parfaitement valide. Seul le segment de
    protocole est normalise, parce que la contrainte `ck_internal_link_url_https`
    est stricte sur la casse — et que les deux etages doivent concorder.
    """
    assert (
        valider_une_url("HTTPS://Hub.Exemple.TEST/Accueil?Q=A#Fragment")
        == "https://Hub.Exemple.TEST/Accueil?Q=A#Fragment"
    )
    #  Les espaces de tete et de queue sont retires : `urlsplit` les laisse dans
    #  le CHEMIN, mesure du 22/09/2026 — « '  https://x/  ' » rend path='/  '.
    assert valider_une_url("  https://hub.exemple.test/  ") == "https://hub.exemple.test/"


def test_les_SIX_refus_portent_SIX_codes_DISTINCTS() -> None:
    """**SIX CAUSES, SIX CODES** — sans quoi un ecran ne saurait que dire.

    Le §18.3 exige un `code` exploitable. Six refus qui partageraient un code
    rendraient l'ecran muet la ou l'auteur a besoin d'un geste precis.
    """
    codes = {
        CODE_URL_ILLISIBLE,
        CODE_URL_AMBIGUE,
        CODE_URL_NON_CHIFFREE,
        CODE_URL_PROTOCOLE_REFUSE,
        CODE_URL_SANS_HOTE,
        CODE_TYPE_DE_LIEN_REFUSE,
    }
    assert len(codes) == 6


def test_le_TYPE_DE_LIEN_est_DERIVE_de_l_enumeration_du_15_3() -> None:
    """Les trois types que le critere nomme, plus l'`OTHER` que « autres » impose."""
    for membre in TypeDeLien:
        assert valider_un_type_de_lien(membre.value) == membre.value
    for nomme in ("HUB", "ACADEMY", "SHAREPOINT"):
        assert nomme in TYPES_DE_LIEN, "le critere de `US005` nomme cette destination"
    with pytest.raises(ErreurApplicative) as capture:
        valider_un_type_de_lien("INTRANET")
    assert _code(capture.value) == CODE_TYPE_DE_LIEN_REFUSE


def test_le_SERVICE_et_la_MIGRATION_portent_la_MEME_liste() -> None:
    """**DEUX ETAGES, UNE SEULE REGLE — ET UN TEST QUI LES CONFRONTE.**

    Si le service acceptait un protocole que la contrainte refuse, l'API rendrait
    **500** la ou elle doit rendre 422 : la traduction de
    `ck_internal_link_url_https` existe pour ce cas, et elle ne devrait jamais
    sortir. Deux copies d'une meme regle divergent au premier changement
    (`DEC-466`, `ECART-022`) ; celle-ci ne le peut plus en silence.
    """
    source = (RACINE / MIGRATION_0019).read_text(encoding="utf-8")
    assert f'NOM = "{CONTRAINTE_URL_HTTPS}"' in source, "le nom de contrainte a diverge"
    motif = re.search(r'^MOTIF = "(.+)"$', source, re.MULTILINE)
    assert motif is not None, "la migration ne declare plus son motif"
    #  Le motif `https://%` ne peut couvrir qu'un protocole, et la liste n'en
    #  porte qu'un : si elle en portait deux, ce test exigerait qu'on revoie la
    #  contrainte AVANT que l'API ne rende des 500.
    assert len(PROTOCOLES_AUTORISES) == 1
    assert motif.group(1) == f"{next(iter(PROTOCOLES_AUTORISES))}://%"


# ============================================================================
#  2. Qui peut quoi — §13 et §19, et la presentation de l'entite
# ============================================================================
def test_la_grille_des_LIENS_est_celle_du_13_ET_du_19__et_les_deux_CONCORDENT() -> None:
    """**QUATRIEME GRILLE VOISINE DU LOT, ET LA PREMIERE QUI CONCORDE.**

        §13 « Gerer les cartes Hub/Academy/SharePoint »
                 DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global
        §19 « Modifier les liens internes »
                        ESM Entite                     ADM-E Entite  SUPER Global

    Le §19 n'a que trois colonnes : une absence de colonne n'est pas une
    exclusion, et c'est le §13 qui met `DSM`, `BOOST` et `OFFICE` a tiret.
    """
    assert {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    } == ROLES_DE_GESTION_DES_LIENS
    for exclu in (
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
        RoleDeLaMatrice.EMPLOYE,
    ):
        assert exclu not in ROLES_DE_GESTION_DES_LIENS, exclu


def test_la_grille_des_LIENS_coincide_AUJOURD_HUI_avec_celle_de_CREATION() -> None:
    """**DEUX ENSEMBLES EGAUX POUR DEUX RAISONS DIFFERENTES**, comme chez `T7`.

    `ROLES_DE_CREATION` vaut ces trois roles parce que le §13 n'a qu'une ligne de
    creation de CONTENU ; `ROLES_DE_GESTION_DES_LIENS` les vaut parce que le §13
    et le §19 s'accordent sur les LIENS. Les aliaser les ferait bouger ENSEMBLE
    le jour ou une seule des deux raisons change.

    Ce test echouera alors, et **c'est son objet** : forcer la decision au lieu de
    la prendre en silence (§7.32).
    """
    assert ROLES_DE_GESTION_DES_LIENS == ROLES_DE_CREATION


def test_un_LIEN_n_a_AUCUNE_portee_locale__et_le_schema_le_dit() -> None:
    """**UN LIEN APPARTIENT A L'ENTITE**, et c'est structurel, pas doctrinal.

    `internal_link` ne porte ni `circle_id` ni `office_id` : un Booster n'aurait
    aucune ressource sur laquelle borner son droit, et lui en accorder un
    exigerait d'INVENTER un rattachement (§6.5). C'est le meme raisonnement qui
    ferme la cellule `DSM` de `ECART-063`.
    """
    from app.content.modeles import InternalLink

    colonnes = set(InternalLink.__table__.columns.keys())
    for portee in PORTEES_LOCALES.values():
        assert portee.colonne not in colonnes, (
            f"`internal_link` porte {portee.colonne} — la portee locale devient exprimable"
        )


def test_la_PRESENTATION_DE_L_ENTITE_n_exigeait_AUCUNE_grille_nouvelle() -> None:
    """**LE §13 LUI DONNE EXACTEMENT LA GRILLE DE `HOME`, ET C'EST UNE MESURE.**

        §13 « Modifier la presentation de l'entite »  — Entite — — Entite Global
        §13 « Creer un contenu general »              — Entite — — Entite Global

    La presentation est une page `HOME` — « l'accueil d'une entite contenant la
    presentation », cahier §26 — et `HOME` n'a pas d'entree dans `PORTEES_LOCALES`,
    donc il tombe par SOUSTRACTION dans `TYPES_SANS_PORTEE_LOCALE`, reserve aux
    roles de portee entite.

    **Ce test echouera si un lot ulterieur donne une portee locale a `HOME`**, et
    c'est son objet : la ligne du §13 devrait alors etre relue.
    """
    assert "HOME" in TYPES_SANS_PORTEE_LOCALE
    assert "HOME" not in PORTEES_LOCALES
    assert {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    } == ROLES_DE_PORTEE_ENTITE


# ============================================================================
#  3. La forme des demandes et des routes
# ============================================================================
def test_les_DEMANDES_ne_portent_NI_RANG_NI_IDENTIFIANT_NI_CHAMP_HTML() -> None:
    """**LES ABSENCES SONT LE POINT**, comme chez `T6`.

    Pas de `rang` : il est derive — la creation ajoute en queue, la reecriture
    d'ordre vaut l'index de la liste. Un champ `rang` aurait rendu une permutation
    de deux liens IMPOSSIBLE, l'index unique partiel de `T1` refusant un echange
    en un seul `UPDATE` (mesure du 22/09/2026).

    Pas de `html`, `format` ni `rendu` : le critere 6 est tenu par ce qui
    n'existe pas, et non par un filtre — chercher `<script` serait une
    heuristique (§7.25).
    """
    champs_creation = set(DemandeDeCreationDeLien.model_fields)
    assert champs_creation == {
        "libelle",
        "url",
        "type_de_lien",
        "description",
        "reference_d_icone",
        "actif",
        #  LOT 10, `T7` : le motif conditionnel du §18.1 (`ECART-064`),
        #  obligatoire pour `SUPER` seulement.
        "motif",
    }
    #  La modification ajoute la version, et RIEN d'autre.
    assert set(DemandeDeModificationDeLien.model_fields) == champs_creation | {"version"}
    assert set(DemandeDOrdreDesLiens.model_fields) == {"ordre", "motif"}
    for interdit in ("rang", "identifiant", "html", "format", "rendu", "ordre"):
        assert interdit not in champs_creation, interdit


def test_la_CREATION_ne_porte_PAS_de_version_et_la_MODIFICATION_l_EXIGE() -> None:
    """§18.4 : la concurrence optimiste borne les modifications, pas les creations.

    **ET ELLE EST OBLIGATOIRE**, sans valeur par defaut — c'est le defaut `T11-6`
    du LOT 5, ou un bouchon rendait 200 sur un corps vide la ou l'API rend 422.
    """
    assert "version" not in DemandeDeCreationDeLien.model_fields
    assert DemandeDeModificationDeLien.model_fields["version"].is_required()


def test_la_REPONSE_rend_actif_et_version_plutot_que_de_les_laisser_deduire() -> None:
    """Une seule structure pour les deux audiences, et elle DIT son etat.

    `actif` vaut toujours `true` dans la lecture publique, qui ne sert que des
    actifs ; le taire obligerait l'ecran de gestion a lire une AUTRE structure,
    et deux structures pour une ressource divergent au premier ajout de colonne.
    """
    champs = set(LienInterneServi.model_fields)
    assert {"identifiant", "actif", "version", "rang", "url", "type_de_lien"} <= champs


def test_LIENS_ORDRE_est_declaree_AVANT_LIENS_IDENTIFIANT(
    parametres_de_la_stack: Parametres,
) -> None:
    """**L'ORDRE DE DECLARATION EST SIGNIFIANT, ET IL EST MESURE PLUTOT QUE PROMIS.**

    FastAPI retient la premiere route dont le MOTIF correspond. `/liens/{lien}`
    attraperait `/liens/ordre` et rendrait 422 sur la conversion en UUID, sans
    jamais passer la main. Inverser les deux declarations fait echouer ce test
    au lieu de casser un ecran (§7.35).
    """
    chemins = [
        route.path  # type: ignore[attr-defined]
        for route in routeur_contenus(parametres_de_la_stack).routes
    ]
    assert "/entities/{code}/liens/ordre" in chemins
    assert "/entities/{code}/liens/{lien}" in chemins
    assert chemins.index("/entities/{code}/liens/ordre") < chemins.index(
        "/entities/{code}/liens/{lien}"
    ), "`/liens/ordre` serait attrapee par `/liens/{lien}` et rendrait 422"


def test_le_MANIFESTE_porte_les_CINQ_chemins_des_liens_et_leur_grille() -> None:
    """Le manifeste est la source unique de `DEC-492`, lue par TypeScript ET Python.

    **`422` EST EXPLOITABLE SUR LES TROIS ECRITURES**, et ce n'est pas decoratif :
    un ecran qui ne saurait pas qu'un 422 porte `url_protocole_refuse` afficherait
    « une erreur est survenue » la ou l'auteur doit corriger un `s`.
    """
    manifeste = json.loads((RACINE / MANIFESTE_DU_CONTRAT).read_text(encoding="utf-8"))
    par_cle = {e["cle"]: e for e in manifeste["endpoints"]}

    attendus = {
        "liensInternesDUneEntite": ("get", "/api/v1/entities/{code}/liens"),
        "gestionDesLiensInternes": ("get", "/api/v1/entities/{code}/liens/gestion"),
        "creationDUnLienInterne": ("post", "/api/v1/entities/{code}/liens"),
        "ordreDesLiensInternes": ("put", "/api/v1/entities/{code}/liens/ordre"),
        "modificationDUnLienInterne": ("put", "/api/v1/entities/{code}/liens/{lien}"),
    }
    for cle, (methode, chemin) in attendus.items():
        point = par_cle[cle]
        assert point["methode"] == methode, cle
        assert point["chemin"] == chemin, cle

    for cle in ("creationDUnLienInterne", "ordreDesLiensInternes", "modificationDUnLienInterne"):
        assert 422 in par_cle[cle]["codesExploitables"], cle

    codes = manifeste["rolesGestionDesLiensInternes"]
    assert codes, "le manifeste ne declare aucun role de gestion des liens"
    assert {RoleDeLaMatrice(code) for code in codes} == ROLES_DE_GESTION_DES_LIENS

    #  **LA LISTE DE PROTOCOLES EST DANS LE MANIFESTE**, et derivee de la source :
    #  l'ecran doit pouvoir la dire AVANT que l'API ne refuse.
    assert set(manifeste["protocolesDeLienAutorises"]) == set(PROTOCOLES_AUTORISES)


# ============================================================================
#  4. Integration
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


def _poser(
    cx: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    libelle: str,
    *,
    url: str = "https://hub.exemple.test/",
    type_de_lien: str = "HUB",
    actif: bool = True,
) -> uuid.UUID:
    return creer_un_lien(
        cx,
        entite=entite,
        acteur=acteur,
        libelle=libelle,
        url=url,
        type_de_lien=type_de_lien,
        description=None,
        reference_d_icone=None,
        actif=actif,
        instant=JANVIER,
    ).identifiant


# ------------------------------------------------------------------ le temoin
@pytest.mark.integration
def test_LE_TEMOIN_les_TROIS_destinations_du_critere_sont_creees_PUIS_SERVIES(
    cx: Connection,
) -> None:
    """**LE COUPLE QUI REND LE CRITERE NON TRIVIAL.**

    « Presentation, Hub, Academy et SharePoint sont modifiables localement ; les
    URL sont validees » est parfaitement tenu par une API qui refuse tout. Ce qui
    le prouve est que les trois destinations NOMMEES par le critere soient
    creees, puis rendues par la lecture — la route de l'accueil, qui ne sait rien
    de l'ecriture.
    """
    entite = _entite(cx, "TEM")
    acteur = _personne(cx, "esm")

    for libelle, type_de_lien, url in (
        ("Hub", "HUB", "https://hub.exemple.test/"),
        ("eXalt Academy", "ACADEMY", "https://academy.exemple.test/"),
        ("SharePoint", "SHAREPOINT", "https://sharepoint.exemple.test/bordeaux"),
    ):
        _poser(cx, entite, acteur, libelle, url=url, type_de_lien=type_de_lien)

    servis = lister_les_liens(cx, entite=entite, inclure_les_inactifs=False)
    assert [lien.libelle for lien in servis] == ["Hub", "eXalt Academy", "SharePoint"]
    assert [lien.rang for lien in servis] == [0, 1, 2], "ajoutes EN QUEUE, dans l'ordre"
    assert [lien.type_de_lien for lien in servis] == ["HUB", "ACADEMY", "SHAREPOINT"]
    assert servis[2].url == "https://sharepoint.exemple.test/bordeaux"


@pytest.mark.integration
def test_le_rang_est_DERIVE_et_reprend_apres_une_DESACTIVATION(cx: Connection) -> None:
    """Le rang vaut `max + 1` parmi les NON ARCHIVES, actifs ou non.

    Un lien desactive garde son rang : le reutiliser heurterait l'index unique,
    qui est partiel sur `archived_at IS NULL` et non sur `active`.
    """
    entite = _entite(cx, "RANG")
    acteur = _personne(cx, "esm")

    premier = _poser(cx, entite, acteur, "Un")
    _poser(cx, entite, acteur, "Deux", actif=False)
    troisieme = _poser(cx, entite, acteur, "Trois")

    tous = lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)
    assert [lien.rang for lien in tous] == [0, 1, 2]
    assert tous[0].identifiant == premier
    assert tous[2].identifiant == troisieme
    #  L'accueil saute le rang 1 sans le combler : le rang est une position dans
    #  la liste complete, pas un index d'affichage.
    actifs = lister_les_liens(cx, entite=entite, inclure_les_inactifs=False)
    assert [lien.rang for lien in actifs] == [0, 2]


@pytest.mark.integration
def test_REORDONNER_echange_deux_liens__ce_qu_un_seul_UPDATE_NE_PEUT_PAS_FAIRE(
    cx: Connection,
) -> None:
    """**LE TEST QUI JUSTIFIE LES DEUX TEMPS**, et la mesure est a l'en-tete du module.

    Un echange de rangs en un seul `UPDATE` est REFUSE par
    `uq_internal_link_entity_ordre_non_archive` — mesure du 22/09/2026. Si la
    reecriture repassait a un seul ordre, ce test echouerait au lieu de laisser
    un ecran rendre 500.
    """
    entite = _entite(cx, "ORD")
    acteur = _personne(cx, "esm")
    a = _poser(cx, entite, acteur, "A")
    b = _poser(cx, entite, acteur, "B")

    apres = reordonner_les_liens(cx, entite=entite, acteur=acteur, ordre=(b, a), instant=DEMAIN)
    assert [lien.identifiant for lien in apres] == [b, a]
    assert [lien.rang for lien in apres] == [0, 1]
    assert [lien.libelle for lien in apres] == ["B", "A"]

    #  **LA PERMUTATION EST REELLE EN BASE**, pas seulement dans la valeur rendue.
    relus = lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)
    assert [lien.identifiant for lien in relus] == [b, a]


@pytest.mark.integration
def test_REORDONNER_refuse_une_liste_INCOMPLETE_ou_a_DOUBLON(cx: Connection) -> None:
    """**L'EXHAUSTIVITE TIENT LIEU DE CONCURRENCE OPTIMISTE ICI.**

    Une liste partielle laisserait des rangs indetermines. Et le doublon est le
    cas que `set(...) == set(...)` aurait laisse passer : deux rangs ecrits sur la
    meme ligne, un lien reste decale. La comparaison porte donc sur les
    MULTI-ENSEMBLES.
    """
    entite = _entite(cx, "INC")
    acteur = _personne(cx, "esm")
    a = _poser(cx, entite, acteur, "A")
    b = _poser(cx, entite, acteur, "B")

    for fautive in ((a,), (a, b, a), (a, b, uuid.uuid4())):
        with pytest.raises(ErreurApplicative) as capture:
            reordonner_les_liens(cx, entite=entite, acteur=acteur, ordre=fautive, instant=DEMAIN)
        assert _code(capture.value) == CODE_ORDRE_INCOMPLET, fautive

    #  LE TEMOIN — la liste exhaustive, elle, passe. Sans lui, un
    #  `reordonner_les_liens` qui refuserait TOUT laisserait les trois verts.
    assert reordonner_les_liens(cx, entite=entite, acteur=acteur, ordre=(b, a), instant=DEMAIN)


@pytest.mark.integration
def test_DESACTIVER_retire_de_l_accueil_SANS_perdre_le_lien__et_on_le_REACTIVE(
    cx: Connection,
) -> None:
    """**LE §15.3 DECLARE `active` A COTE DE `archived_at`, ET `T1` A REFUSE DE LES
    FONDRE.**

    Le couple complet est ici, et c'est ce qui rend le champ utile : desactive, le
    lien quitte l'accueil et RESTE visible en gestion ; reactive, il revient a sa
    place. Sans la seconde moitie, desactiver serait un aller sans retour.
    """
    entite = _entite(cx, "ACT")
    acteur = _personne(cx, "esm")
    lien = _poser(cx, entite, acteur, "Hub")

    def _modifier(*, actif: bool, version: int) -> int:
        return modifier_un_lien(
            cx,
            entite=entite,
            lien=lien,
            acteur=acteur,
            version_attendue=version,
            libelle="Hub",
            url="https://hub.exemple.test/",
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=actif,
            instant=DEMAIN,
        ).version

    assert len(lister_les_liens(cx, entite=entite, inclure_les_inactifs=False)) == 1

    version = _modifier(actif=False, version=1)
    assert lister_les_liens(cx, entite=entite, inclure_les_inactifs=False) == ()
    en_gestion = lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)
    assert len(en_gestion) == 1, "le lien EXISTE toujours — il n'est pas archive"
    assert en_gestion[0].actif is False

    #  LE RETOUR — le meme lien, le meme rang.
    _modifier(actif=True, version=version)
    revenu = lister_les_liens(cx, entite=entite, inclure_les_inactifs=False)
    assert len(revenu) == 1
    assert revenu[0].identifiant == lien
    assert revenu[0].rang == 0


@pytest.mark.integration
def test_MODIFIER_refuse_une_VERSION_OBSOLETE__18_4(cx: Connection) -> None:
    """« Une version obsolete produit un 409 **sans ecrasement silencieux** ».

    Le temoin est la seconde moitie : avec la version rendue par la premiere
    ecriture, la meme demande passe. Sans lui, un `modifier_un_lien` qui
    refuserait toujours laisserait le refus vert.
    """
    entite = _entite(cx, "VER")
    acteur = _personne(cx, "esm")
    lien = _poser(cx, entite, acteur, "Hub")

    def _ecrire(version: int, libelle: str) -> int:
        return modifier_un_lien(
            cx,
            entite=entite,
            lien=lien,
            acteur=acteur,
            version_attendue=version,
            libelle=libelle,
            url="https://hub.exemple.test/",
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=True,
            instant=DEMAIN,
        ).version

    apres = _ecrire(1, "Hub renomme")
    assert apres == 2

    with pytest.raises(ErreurApplicative) as capture:
        _ecrire(1, "ecrasement")
    assert _code(capture.value) == CODE_VERSION_OBSOLETE
    assert capture.value.details == {"version_actuelle": 2}

    #  LE TEMOIN — la version a jour passe, et le libelle precedent a survecu.
    assert _ecrire(2, "Hub final") == 3
    assert lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)[0].libelle == "Hub final"


@pytest.mark.integration
def test_un_lien_d_une_AUTRE_ENTITE_rend_le_MEME_404_qu_un_lien_inexistant(
    cx: Connection,
) -> None:
    """**UN SEUL GABARIT POUR TROIS CAUSES** — §2.5, refus par defaut.

    Distinguer apprendrait l'existence d'un lien d'une entite ou l'appelant n'a
    rien prouve. Le couple est ici : le MEME identifiant passe dans son entite et
    echoue dans l'autre — seule l'entite change.
    """
    ici = _entite(cx, "ICI")
    ailleurs = _entite(cx, "AIL")
    acteur = _personne(cx, "esm")
    lien = _poser(cx, ici, acteur, "Hub")

    def _ecrire(entite: uuid.UUID) -> None:
        modifier_un_lien(
            cx,
            entite=entite,
            lien=lien,
            acteur=acteur,
            version_attendue=1,
            libelle="Hub",
            url="https://hub.exemple.test/",
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=True,
            instant=DEMAIN,
        )

    for absent in (ailleurs,):
        with pytest.raises(ErreurApplicative) as capture:
            _ecrire(absent)
        assert _code(capture.value) == CODE_LIEN_INTROUVABLE

    with pytest.raises(ErreurApplicative) as capture:
        modifier_un_lien(
            cx,
            entite=ici,
            lien=uuid.uuid4(),
            acteur=acteur,
            version_attendue=1,
            libelle="Hub",
            url="https://hub.exemple.test/",
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=True,
            instant=DEMAIN,
        )
    assert _code(capture.value) == CODE_LIEN_INTROUVABLE

    #  LE TEMOIN — dans SON entite, le meme lien se modifie.
    _ecrire(ici)


@pytest.mark.integration
def test_un_lien_ARCHIVE_n_est_NI_SERVI_NI_MODIFIABLE(cx: Connection) -> None:
    """**AUCUNE ROUTE N'ARCHIVE UN LIEN** — ni le §13 ni le §19 n'en portent la ligne.

    L'etat existe pourtant en base, via `archived_at` du §3.1, et un lot ulterieur
    ou une reprise pourrait le poser. Les deux lectures et l'ecriture l'excluent
    donc, et ce test le mesure sur une ligne archivee PAR SQL.
    """
    entite = _entite(cx, "ARC")
    acteur = _personne(cx, "esm")
    lien = _poser(cx, entite, acteur, "Hub")

    cx.execute(text("UPDATE internal_link SET archived_at = now() WHERE id = :l"), {"l": lien})

    assert lister_les_liens(cx, entite=entite, inclure_les_inactifs=False) == ()
    assert lister_les_liens(cx, entite=entite, inclure_les_inactifs=True) == ()
    with pytest.raises(ErreurApplicative) as capture:
        modifier_un_lien(
            cx,
            entite=entite,
            lien=lien,
            acteur=acteur,
            version_attendue=1,
            libelle="Hub",
            url="https://hub.exemple.test/",
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=True,
            instant=DEMAIN,
        )
    assert _code(capture.value) == CODE_LIEN_INTROUVABLE


@pytest.mark.integration
def test_la_CONTRAINTE_de_la_migration_0019_refuse_une_INSERTION_SQL_DIRECTE(
    cx: Connection,
) -> None:
    """**LE PLANCHER, ET IL COUVRE CE QUE LE SERVICE NE PEUT PAS COUVRIR.**

    Trois ecrivains futurs sont deja nommes au corpus et n'appellent pas
    `app.content.liens` : la reprise du prototype (`T11`), les modeles generiques
    du §19, les imports du LOT 9. Aucun ne peut plus ecrire `javascript:` dans
    `internal_link`, et c'est ce qui rend la garantie STRUCTURELLE (§7.35).

    Le couple est complet : le temoin `https://` passe par le MEME chemin SQL.
    """
    entite = _entite(cx, "SQL")

    def _inserer(url: str) -> None:
        cx.execute(
            text(
                "INSERT INTO internal_link (entity_id, label, url, link_type, display_order,"
                " created_at, updated_at) VALUES (:e, 'brut', :u, 'OTHER', :o, now(), now())"
            ),
            {"e": entite, "u": url, "o": 0 if url.startswith("https") else 99},
        )

    for hostile in ("javascript:alert(1)", "http://hub.exemple.test/", "HTTPS://hub.exemple.test/"):
        point = cx.begin_nested()
        with pytest.raises(IntegrityError) as capture:
            _inserer(hostile)
        nom = getattr(getattr(capture.value.orig, "diag", None), "constraint_name", None)
        assert nom == CONTRAINTE_URL_HTTPS, (hostile, nom)
        point.rollback()

    #  LE TEMOIN — la meme insertion, avec une adresse conforme.
    _inserer("https://hub.exemple.test/")
    assert len(lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)) == 1


@pytest.mark.integration
def test_TOUT_ce_que_le_SERVICE_accepte_est_accepte_par_la_BASE(cx: Connection) -> None:
    """**LES DEUX ETAGES CONCORDENT, ET C'EST MESURE PLUTOT QUE PROMIS.**

    Si le service acceptait une adresse que la contrainte refuse, l'API rendrait
    500 la ou elle doit rendre 422. Ce test fait passer par l'ECRITURE REELLE
    toutes les formes que `valider_une_url` accepte, y compris celles qu'elle
    NORMALISE — c'est la casse du protocole qui est en jeu, la contrainte etant
    stricte.
    """
    entite = _entite(cx, "CONC")
    acteur = _personne(cx, "esm")
    acceptees = (
        "https://hub.exemple.test/",
        "HTTPS://hub.exemple.test/",
        "  https://hub.exemple.test/chemin?q=a#f  ",
        "https://hub.exemple.test:8443/Chemin/Avec/Casse",
    )
    for rang, url in enumerate(acceptees):
        identifiant = _poser(cx, entite, acteur, f"lien-{rang}", url=url)
        stocke = cx.execute(
            text("SELECT url FROM internal_link WHERE id = :l"), {"l": identifiant}
        ).scalar_one()
        assert str(stocke).startswith("https://"), (url, stocke)
        assert str(stocke) == valider_une_url(url)


@pytest.mark.integration
def test_la_PRESENTATION_DE_L_ENTITE_est_editable_par_les_TROIS_roles_et_par_EUX_SEULS(
    cx: Connection,
) -> None:
    """**LA LIGNE « MODIFIER LA PRESENTATION DE L'ENTITE » DU §13, MESUREE SUR UNE
    PAGE `HOME` REELLE.**

    `T8` n'a ecrit aucune ligne pour elle : `T6` la cree et l'ecrit, et `HOME`
    tombe par soustraction dans le regime des roles de portee entite. Ce test le
    MESURE — il echouerait si un lot ulterieur donnait une portee locale a `HOME`,
    ce qui est son objet (§7.32).
    """
    entite = _entite(cx, "PRES")
    acteur = _personne(cx, "esm")
    page = creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page="HOME",
        titre="Presentation de l'entite",
        slug="accueil",
        code_de_cercle=None,
        code_de_bureau=None,
        instant=JANVIER,
    ).identifiant

    def _actions(roles: set[RoleDeLaMatrice]) -> frozenset[ActionEditoriale]:
        return resoudre_le_perimetre_editorial(
            cx,
            entite=entite,
            acteur=acteur,
            page=page,
            roles=frozenset(roles),
            instant=DEMAIN,
        ).actions

    for accorde in ROLES_DE_PORTEE_ENTITE:
        assert ActionEditoriale.MODIFIER in _actions({accorde}), accorde

    #  **LES TROIS COLONNES A TIRET DU §13**, et le Booster est le cas qui compte :
    #  il modifie le contenu de SON cercle, jamais la presentation de l'entite.
    for refuse in (
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
        RoleDeLaMatrice.EMPLOYE,
    ):
        assert _actions({refuse}) == frozenset(), refuse


# ============================================================================
#  5. Les cinq trous que la CAMPAGNE DE TEMOINS a trouves
#
#     Campagne du 22/09/2026, `PYTHONDONTWRITEBYTECODE=1` (§7.44) : vingt-deux
#     filtres retires un par un. **Seize faisaient tomber un test, SIX etaient
#     muets** — et cinq des six etaient de vrais trous de couverture, tous de la
#     meme famille : aucun de mes cas ne mettait DEUX entites en presence, ni ne
#     faisait passer une valeur fautive par l'ECRITURE plutot que par la
#     fonction de validation appelee seule.
#
#     Le sixieme, `FOR UPDATE`, n'est pas un trou : voir le test qui le nomme.
# ============================================================================
@pytest.mark.integration
def test_la_LECTURE_est_cloisonnee__une_entite_ne_voit_JAMAIS_les_liens_d_une_autre(
    cx: Connection,
) -> None:
    """**TROU N°1 DE LA CAMPAGNE.** Retirer `entity_id = :entite` de la lecture ne
    faisait tomber AUCUN test : aucun de mes cas ne mettait deux entites en
    presence, si bien qu'un `WHERE` global rendait exactement la meme chose.

    Le §25.3 fait porter l'isolation aux colonnes et aux cles ; une requete locale
    qui ne nommerait pas son entite se lirait comme une requete globale — c'est
    tout le motif de `DepotLocal` du LOT 2.
    """
    ici = _entite(cx, "CL1")
    ailleurs = _entite(cx, "CL2")
    acteur = _personne(cx, "esm")
    _poser(cx, ici, acteur, "Hub d'ici")
    _poser(cx, ailleurs, acteur, "Hub d'ailleurs")
    _poser(cx, ailleurs, acteur, "Academy d'ailleurs", type_de_lien="ACADEMY")

    ici_vus = lister_les_liens(cx, entite=ici, inclure_les_inactifs=True)
    assert [lien.libelle for lien in ici_vus] == ["Hub d'ici"]
    assert [
        lien.libelle for lien in lister_les_liens(cx, entite=ailleurs, inclure_les_inactifs=True)
    ] == ["Hub d'ailleurs", "Academy d'ailleurs"]
    #  La lecture publique est cloisonnee de la meme facon.
    assert len(lister_les_liens(cx, entite=ici, inclure_les_inactifs=False)) == 1


@pytest.mark.integration
def test_le_RANG_repart_a_ZERO_dans_une_AUTRE_entite(cx: Connection) -> None:
    """**TROU N°2 DE LA CAMPAGNE.** Retirer `entity_id` du calcul du rang suivant ne
    faisait tomber aucun test : l'index unique etant PAR ENTITE, rien ne cassait —
    les rangs de la seconde entite auraient simplement commence a 3, ce qu'aucun
    de mes cas n'observait.

    C'est le §7.0, quatrieme proposition : l'echec aurait produit la meme
    observation que le succes partout ou une seule entite porte des liens.
    """
    premiere = _entite(cx, "RG1")
    seconde = _entite(cx, "RG2")
    acteur = _personne(cx, "esm")
    for libelle in ("A", "B", "C"):
        _poser(cx, premiere, acteur, libelle)

    _poser(cx, seconde, acteur, "Seul")
    dans_la_premiere = lister_les_liens(cx, entite=premiere, inclure_les_inactifs=True)
    assert [lien.rang for lien in dans_la_premiere] == [0, 1, 2]
    assert [
        lien.rang for lien in lister_les_liens(cx, entite=seconde, inclure_les_inactifs=True)
    ] == [0], "le rang est derive de l'entite, pas de la table"


@pytest.mark.integration
def test_MODIFIER_valide_l_URL__et_pas_seulement_la_CREATION(cx: Connection) -> None:
    """**TROU N°3 DE LA CAMPAGNE, ET LE PLUS SERIEUX.**

    Retirer `valider_une_url` de la MODIFICATION ne faisait tomber aucun test :
    tous mes cas d'URL fautive passaient par `valider_une_url` appelee seule, ou
    par la creation. Un lien cree conforme pouvait donc etre **reecrit** en
    `javascript:` sans qu'aucun test ne le voie.

    C'est exactement le §7.39 : la validation « existe », et c'est le second
    chemin d'ecriture qui ne l'exerce pas.

    **Le refus de la base l'aurait attrape en 500**, pas en 422 : la traduction
    de `ck_internal_link_url_https` est un filet, pas la regle.
    """
    entite = _entite(cx, "MURL")
    acteur = _personne(cx, "esm")
    lien = _poser(cx, entite, acteur, "Hub")

    def _ecrire(url: str) -> None:
        modifier_un_lien(
            cx,
            entite=entite,
            lien=lien,
            acteur=acteur,
            version_attendue=1,
            libelle="Hub",
            url=url,
            type_de_lien="HUB",
            description=None,
            reference_d_icone=None,
            actif=True,
            instant=DEMAIN,
        )

    for fautive, attendu in (
        ("javascript:alert(1)", CODE_URL_PROTOCOLE_REFUSE),
        ("http://hub.exemple.test/", CODE_URL_NON_CHIFFREE),
        ("https:alert(1)", CODE_URL_SANS_HOTE),
    ):
        with pytest.raises(ErreurApplicative) as capture:
            _ecrire(fautive)
        assert _code(capture.value) == attendu, fautive

    #  LE TEMOIN — et il prouve en plus qu'aucun des trois refus n'a ecrit :
    #  la version est toujours 1.
    _ecrire("https://hub.exemple.test/modifie")
    relu = lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)[0]
    assert relu.url == "https://hub.exemple.test/modifie"
    assert relu.version == 2, "les trois refus n'ont RIEN ecrit"


@pytest.mark.integration
def test_un_TYPE_inconnu_rend_422_a_l_ECRITURE__et_non_le_500_de_la_base(
    cx: Connection,
) -> None:
    """**TROU N°4 DE LA CAMPAGNE.** Retirer `valider_un_type_de_lien` de la creation
    ne faisait tomber aucun test : mon seul cas appelait la fonction **seule**.

    Or la base porte la meme regle en `ck_internal_link_link_type_valide`, et
    `_traduire_un_refus_de_la_base` ne la traduit pas — elle REMONTE, donc 500.
    Le service existe pour en faire un 422 nomme, et parce qu'il est appelable
    hors HTTP (corollaire du §7.37).
    """
    entite = _entite(cx, "TYP")
    acteur = _personne(cx, "esm")

    with pytest.raises(ErreurApplicative) as capture:
        _poser(cx, entite, acteur, "Intranet", type_de_lien="INTRANET")
    assert _code(capture.value) == CODE_TYPE_DE_LIEN_REFUSE
    assert capture.value.statut == 422, "un 500 accuserait l'appelant a tort"

    #  LE TEMOIN — les quatre types du §15.3 passent par le MEME chemin.
    for rang, type_de_lien in enumerate(TYPES_DE_LIEN):
        _poser(cx, entite, acteur, f"lien-{rang}", type_de_lien=type_de_lien)
    assert len(lister_les_liens(cx, entite=entite, inclure_les_inactifs=True)) == len(TYPES_DE_LIEN)


@pytest.mark.integration
def test_REORDONNER_IGNORE_les_liens_ARCHIVES(cx: Connection) -> None:
    """**TROU N°5 DE LA CAMPAGNE.** Retirer `archived_at IS NULL` de la lecture des
    identifiants a reordonner ne faisait tomber aucun test : aucun de mes cas
    d'ordre ne portait de lien archive.

    Sans ce filtre, une liste parfaitement legitime deviendrait **incomplete** —
    l'archive manquerait a l'appel — et le decalage de phase 1 toucherait une
    ligne que plus personne ne sert. Un refus sur un livrable conforme, §7.20.
    """
    entite = _entite(cx, "ARCO")
    acteur = _personne(cx, "esm")
    a = _poser(cx, entite, acteur, "A")
    disparu = _poser(cx, entite, acteur, "Disparu")
    b = _poser(cx, entite, acteur, "B")
    rang_archive = cx.execute(
        text("UPDATE internal_link SET archived_at = now() WHERE id = :l RETURNING display_order"),
        {"l": disparu},
    ).scalar_one()

    apres = reordonner_les_liens(cx, entite=entite, acteur=acteur, ordre=(b, a), instant=DEMAIN)
    assert [lien.identifiant for lien in apres] == [b, a]
    assert [lien.rang for lien in apres] == [0, 1]

    #  **LE LIEN ARCHIVE N'A PAS BOUGE**, et c'est ce que la phase 1 aurait fait
    #  si elle l'avait pris : son rang est celui qu'il portait avant.
    assert (
        cx.execute(
            text("SELECT display_order FROM internal_link WHERE id = :l"), {"l": disparu}
        ).scalar_one()
        == rang_archive
    )


def test_le_FOR_UPDATE_n_est_PAS_OBSERVABLE__et_le_dire_vaut_mieux_que_le_taire() -> None:
    """**LE SIXIEME FILTRE MUET, ET IL N'EST PAS UN TROU DE COUVERTURE.**

    Retirer `FOR UPDATE` de `_LIEN_A_MODIFIER` ne fait tomber aucun test, et
    **aucun test sequentiel ne le pourrait** : un verrou ne se manifeste que
    lorsque deux transactions se rencontrent. Son absence produit exactement la
    meme observation que sa presence tant qu'une seule connexion ecrit — §7.0,
    quatrieme proposition, appliquee a une propriete que le banc d'essai ne peut
    pas mesurer.

    **Renforcer le test ne servirait a rien ; ce qui sert est de le DIRE** (§7.35,
    dernier corollaire, et §7.42 : la ou aucun controle ne voit la propriete,
    c'est la structure qui la tient, et il faut le dire plutot que de laisser
    croire qu'un test la prouve).

    Ce test-ci exige donc la seule chose qui soit observable : que la clause
    reste ECRITE dans la requete. La retirer ferait echouer ici, ce qui oblige a
    relire le §18.4 au lieu de la perdre en silence.
    """
    from app.content.liens import _LIEN_A_MODIFIER

    assert "FOR UPDATE" in str(_LIEN_A_MODIFIER), (
        "sans le verrou, deux modifications concurrentes lisent la MEME version, "
        "la trouvent toutes deux a jour, et la seconde ecrase la premiere — "
        "« l'ecrasement silencieux » du §18.4"
    )
