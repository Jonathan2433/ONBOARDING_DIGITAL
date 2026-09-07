"""La miniature de photo — story `MVP-L05-US005`, LOT 5 sous-etape `T5`.

LE CRITERE, ET CE QU'IL EXIGE VRAIMENT

  « **< 100 Ko mesure** · la photo **originale jamais servie** dans la liste. »

  Deux grandeurs, et **une seule des deux se prouve par un refus**. C'est le §7.0
  troisieme et quatrieme propositions, et il faut le dire avant d'ecrire une
  ligne :

    « originale jamais servie »   une route qui ne sert RIEN satisfait ce critere
                                  parfaitement. Il exige donc un **temoin** qui
                                  serve la miniature, sans quoi les refus ne
                                  prouvent rien -- exactement le defaut `T2-3`,
                                  ou HUIT refus restaient verts sur une route qui
                                  refusait TOUT
    « < 100 Ko mesure »           la borne est en base (`0016`), et un test la
                                  franchit **a l'octet exact** : 99 999 passe,
                                  100 000 est refuse. Un test a 50 Ko et 200 Ko
                                  passerait avec une borne posee n'importe ou
                                  entre les deux

LES CINQ CAUSES D'AVATAR NEUTRE, ET POURQUOI CHACUNE A SON TEMOIN

  `resoudre_la_miniature` rend `None` pour cinq causes, et les cinq donnent la
  meme observation cote client -- c'est voulu, §21.2. Mais **pour le test, cinq
  causes indistinguables sont un piege** : un `WHERE` faux refuserait tout, et les
  cinq refus resteraient verts.

  Chaque refus est donc apparie a un temoin qui ne differe que par **la** valeur
  en cause :

    pas d'autorisation           aucune ligne         <-> une ligne active
    autorisation retiree         `withdrawn_at` posee <-> `withdrawn_at` nulle
    autorisation FUTURE          `granted_at` a +1j   <-> `granted_at` a -1j
    media non `ready`            `pending`            <-> `ready`
    aucune variante `thumbnail`  une `medium` seule   <-> une `thumbnail`

  **LA TROISIEME EST CELLE QUI COMPTE.** `withdrawn_at IS NULL` seul l'aurait
  laissee passer : une autorisation datee du futur a elle aussi un retrait nul.
  C'est la lecon des periodes, §7.38, et sans ce test le defaut serait invisible.

CE QUE CETTE SOUS-ETAPE NE FAIT PAS, ET C'EST ECRIT DANS UN TEST

  Elle ne **fabrique** aucune miniature : `MVP-L11-US005` le fait, au LOT 11
  (« Generer miniatures et variantes sans doublon »). Mesure du 06/09/2026 :
  aucune bibliotheque de traitement d'image n'est installee. `T5` selectionne et
  sert ; la borne attend son producteur en base.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.media.modeles import EtatMedia, SourceAutorisationPhoto, TypeMedia, TypeVarianteMedia
from app.media.photo import (
    BORNE_MINIATURE_OCTETS,
    MIME_PAR_DEFAUT,
    PARAMETRES_DE_LA_MINIATURE,
    resoudre_la_miniature,
)
from app.people.modeles import ETAT_LISTE, EtatAppartenance, VisibiliteProfil
from app.people.routes import GABARIT_PHOTO, chemin_de_la_photo
from app.shared.database import moteur

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

    from sqlalchemy.engine import Connection

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_PHOTO = "/api/v1" + GABARIT_PHOTO
CHEMIN_FICHE = "/api/v1/entities/{code}/people/{appartenance}"
CHEMIN_LISTE = "/api/v1/entities/{code}/people"

#  **L'ANCRAGE EST RELEVE DU SERVEUR, ET NON ECRIT EN DUR. DEFAUT `T5-2`.**
#
#  Ma premiere version posait `ANCRAGE = 2026-06-15` et un octroi « futur » a
#  `ANCRAGE + 10 jours`, soit le 25/06/2026 -- **deja passe**. Les tests qui
#  appellent `resoudre_la_miniature` INJECTENT leur instant et passaient tous ;
#  ceux qui passent par la **route** lisent l'horloge reelle, et l'octroi n'y
#  etait plus futur du tout.
#
#  C'est le §7.0 sixieme proposition : « instant injecte » et « instant de
#  l'horloge » sont deux grandeurs, et un decor ancre sur la premiere ne prouve
#  rien de la seconde. C'est aussi le §7.21 -- une date en dur est juste le jour
#  ou on l'ecrit.
JOUR = dt.timedelta(days=1)
EMPREINTE = "a" * 64

#  La contrainte posee par la migration `0016`. **Le nom est ecrit ici et
#  confronte au reel** : sans cela, une contrainte renommee rendrait le test
#  silencieusement vide.
#  **LES AUTRES TYPES DE VARIANTE, DERIVES ET NON RECOPIES.** Ma premiere version
#  nommait `MOYENNE` et `GRANDE`, qui n'existent pas : le §16.2 en declare cinq,
#  et leurs noms sont ceux du document. Une liste ecrite de memoire est un
#  `ECART-021` en puissance -- §7.27.
AUTRES_VARIANTES: tuple[str, ...] = tuple(
    membre.value
    for membre in TypeVarianteMedia
    if membre is not TypeVarianteMedia.MINIATURE_TROMBINOSCOPE
)

CONTRAINTE_DE_BORNE = "ck_media_variant_miniature_sous_cent_ko"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


# ===========================================================================
#  1. Sans base : ce que la structure declare, et ce qu'elle REFUSE de porter
# ===========================================================================


def test_la_borne_est_celle_du_cahier_et_en_UNE_seule_source() -> None:
    """**100 Ko, et la meme valeur en base.**

    Le §25.3 dit « moins de 100 Ko ». La constante vaut 100 000 et non 102 400 :
    « Ko » designe ici le kilo-octet decimal, qui est la lecture la plus stricte
    -- 102 400 laisserait passer 2,4 Ko de plus que le cahier n'autorise.

    Un test d'integration, plus bas, verifie que la contrainte de la migration
    porte **exactement** cette valeur : deux copies d'un seuil divergent.
    """
    assert BORNE_MINIATURE_OCTETS == 100_000


def test_la_structure_servie_ne_porte_AUCUN_champ_de_l_original() -> None:
    """**L'ORIGINAL N'EST PAS OMIS PAR HASARD : IL EST ABSENT DE LA STRUCTURE.**

    C'est le §7.35 -- rendre la propriete structurelle plutot que de renforcer un
    controle. `MiniatureServie` porte trois champs, tous de la VARIANTE. Ajouter
    l'original exigerait d'ecrire un champ, donc de le decider.
    """
    from app.media.photo import MiniatureServie

    champs = {champ.name for champ in MiniatureServie.__dataclass_fields__.values()}
    assert champs == {"object_key", "size_bytes", "mime"}


def test_la_requete_ne_selectionne_JAMAIS_object_key_de_l_actif() -> None:
    """La preuve par le texte de la requete, et elle est necessaire.

    Le test precedent prouve que la structure ne peut pas le PORTER. Celui-ci
    prouve que la requete ne le LIT pas -- deux choses differentes : un
    `SELECT a.object_key` qu'on jetterait ensuite ferait quand meme voyager la
    valeur, et un journal de requetes lentes la montrerait.
    """
    from app.media.photo import _MINIATURE

    assert "a.object_key" not in _MINIATURE
    #  TEMOIN : la variante, elle, EST bien lue — sans quoi l'assertion ci-dessus
    #  serait satisfaite par une requete qui ne lit aucun `object_key` du tout.
    assert _MINIATURE.count("v.object_key") == 2


def test_le_chemin_de_la_photo_est_derive_du_gabarit_de_la_route() -> None:
    """**UNE SEULE SOURCE POUR LE CHEMIN**, et c'est mesurable.

    La liste et la fiche emettent ce chemin ; la route le declare. Deux copies
    divergeraient au premier renommage, et la liste emettrait alors un chemin qui
    rend 404 -- une regression qu'aucun test de la liste seule ne verrait.
    """
    appartenance = uuid.UUID("00000000-0000-4000-8000-000000000001")
    chemin = chemin_de_la_photo("/api/v1", "bordeaux", appartenance)
    assert chemin == f"/api/v1/entities/bordeaux/people/{appartenance}/photo"
    #  Le gabarit porte les deux parametres, et le chemin n'en garde aucun.
    assert "{code}" in GABARIT_PHOTO
    assert "{appartenance}" in GABARIT_PHOTO
    assert "{" not in chemin


def test_les_parametres_du_fragment_partage_sont_ceux_que_la_liste_fournit() -> None:
    """Le fragment de conditions est partage : ses parametres doivent l'etre aussi.

    Si la liste oubliait l'un des trois, la requete leverait **a l'execution** --
    pas a la lecture -- et sur une page quelconque du trombinoscope. Ce test le
    dit sans base de donnees.
    """
    from app.people import trombinoscope

    source = __import__("pathlib").Path(trombinoscope.__file__).read_text(encoding="utf-8")
    for nom in PARAMETRES_DE_LA_MINIATURE:
        assert f'"{nom}":' in source, f"la liste ne fournit pas le parametre {nom}"
    assert len(PARAMETRES_DE_LA_MINIATURE) == 3


def test_un_format_inconnu_tombe_sur_un_type_generique() -> None:
    """**LE FORMAT DES VARIANTES N'EST PAS TRANCHE, ET C'EST VOLONTAIRE** (§6.5).

    Le corpus ne nomme aucun format. Un format inconnu doit donc servir les
    octets avec un type generique plutot que lever : un octet servi vaut mieux
    qu'une page cassee, et c'est le LOT 11 qui tranchera.
    """
    from app.media.photo import _mime_de

    assert _mime_de("webp") == "image/webp"
    assert _mime_de("  JPEG ") == "image/jpeg"
    assert _mime_de("un-format-de-2029") == MIME_PAR_DEFAUT


# ===========================================================================
#  2. Le decor : un profil avec photo servable, et cinq profils qui n'en ont pas
# ===========================================================================


def _personne(cx: Connection, marqueur: str, nom: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, 'Photo', :n, 'active') RETURNING id"
                ),
                {"a": f"{marqueur}-{nom}@exemple.test".lower(), "n": nom},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatAppartenance.ACTIVE.value,
    visibilite: str = VisibiliteProfil.PUBLISHED.value,
) -> uuid.UUID:
    depart = dt.date(2026, 6, 1) if etat == EtatAppartenance.DEPARTED.value else None
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "departure_date, membership_state, professional_category, "
                    "profile_visibility) VALUES (:p, :e, DATE '2026-01-15', :depart, :etat, "
                    "'consultant', :vis) RETURNING id"
                ),
                {"p": personne, "e": entite, "depart": depart, "etat": etat, "vis": visibilite},
            ).scalar_one()
        )
    )


def _actif(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatMedia.READY.value,
    maintenant: dt.datetime,
) -> uuid.UUID:
    pret = maintenant - JOUR if etat == EtatMedia.READY.value else None
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, "
                    "media_type, original_filename, object_key, mime_declared, size_bytes, "
                    "checksum_sha256, ready_at) VALUES (:e, :p, :etat, :type_m, 'photo.jpg', "
                    ":cle, 'image/jpeg', 2000000, :emp, :pret) RETURNING id"
                ),
                {
                    "e": entite,
                    "p": personne,
                    "etat": etat,
                    "type_m": TypeMedia.IMAGE.value,
                    #  **DEUX MEGA-OCTETS, ET C'EST DELIBERE** : l'original est
                    #  vingt fois la borne de la miniature. Si une route le
                    #  servait, la taille le dirait.
                    "cle": f"{ORIGINAL}/{uuid.uuid4().hex}",
                    "emp": EMPREINTE,
                    "pret": pret,
                },
            ).scalar_one()
        )
    )


#  Deux prefixes DISTINCTS pour les cles d'objet : c'est ce qui permet a un test
#  d'affirmer « ce qui a ete servi n'est pas l'original », et non seulement
#  « quelque chose a ete servi ».
ORIGINAL = "originaux-de-test"
MINIATURE = "miniatures-de-test"


def _variante(
    cx: Connection,
    entite: uuid.UUID,
    actif: uuid.UUID,
    *,
    type_v: str = TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value,
    taille: int = 4096,
    format_: str = "jpeg",
) -> str:
    cle = f"{MINIATURE}/{uuid.uuid4().hex}"
    cx.execute(
        text(
            "INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, "
            "height, variant_format, size_bytes, checksum_sha256, object_key) "
            "VALUES (:e, :a, :t, 200, 200, :f, :taille, :emp, :cle)"
        ),
        {
            "e": entite,
            "a": actif,
            "t": type_v,
            "f": format_,
            "taille": taille,
            "emp": EMPREINTE,
            "cle": cle,
        },
    )
    return cle


def _autorisation(
    cx: Connection,
    personne: uuid.UUID,
    actif: uuid.UUID,
    *,
    octroi: dt.datetime,
    retrait: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, "
            "withdrawn_at, source) VALUES (:p, :m, :octroi, :retrait, :src)"
        ),
        {
            "p": personne,
            "m": actif,
            "octroi": octroi,
            "retrait": retrait,
            "src": SourceAutorisationPhoto.SELF_SERVICE.value,
        },
    )


#  Les six cas du decor. **LE PREMIER EST LE TEMOIN** : sans lui, les cinq refus
#  seraient satisfaits par une resolution qui ne rend jamais rien.
CAS_SERVABLE = "servable"
CAS_SANS_AUTORISATION = "sans-autorisation"
CAS_AUTORISATION_RETIREE = "retiree"
CAS_AUTORISATION_FUTURE = "future"
CAS_MEDIA_NON_PRET = "non-pret"
CAS_SANS_MINIATURE = "sans-miniature"

TOUS_LES_REFUS = (
    CAS_SANS_AUTORISATION,
    CAS_AUTORISATION_RETIREE,
    CAS_AUTORISATION_FUTURE,
    CAS_MEDIA_NON_PRET,
    CAS_SANS_MINIATURE,
)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, dict[str, Any]]]:
    """Une entite, six appartenances, et une septieme dans une AUTRE entite."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t5l5{uuid.uuid4().hex[:10]}"
    code_entite = f"{marqueur}-e"

    with moteur(parametres).connect() as horloge:
        debut_temps = horloge.execute(text("SELECT now()")).scalar_one()
    #  **L'HORLOGE DU SERVEUR**, la meme que celle des routes.
    maintenant = debut_temps

    r: dict[str, Any] = {"maintenant": maintenant}
    with moteur(parametres).begin() as cx:
        entite = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO entity (code, display_name, city, country_code, status, "
                        "timezone) VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', "
                        "'Europe/Paris') RETURNING id"
                    ),
                    {"code": code_entite, "nom": f"Entite {marqueur}"},
                ).scalar_one()
            )
        )
        r["entite"] = entite

        deposant = _personne(cx, marqueur, "Deposante")

        def poser(cas: str) -> uuid.UUID:
            personne = _personne(cx, marqueur, cas)
            appartenance = _appartenance(cx, entite, personne)
            r[f"personne-{cas}"] = personne
            r[cas] = appartenance
            return appartenance

        #  1. LE TEMOIN : tout est reuni.
        poser(CAS_SERVABLE)
        actif = _actif(cx, entite, deposant, maintenant=maintenant)
        r["cle-miniature"] = _variante(cx, entite, actif)
        r["actif-servable"] = actif
        _autorisation(cx, r[f"personne-{CAS_SERVABLE}"], actif, octroi=maintenant - JOUR)

        #  2. Aucune autorisation — l'actif et la variante existent pourtant.
        poser(CAS_SANS_AUTORISATION)
        a2 = _actif(cx, entite, deposant, maintenant=maintenant)
        _variante(cx, entite, a2)

        #  3. Autorisation RETIREE.
        poser(CAS_AUTORISATION_RETIREE)
        a3 = _actif(cx, entite, deposant, maintenant=maintenant)
        _variante(cx, entite, a3)
        _autorisation(
            cx,
            r[f"personne-{CAS_AUTORISATION_RETIREE}"],
            a3,
            octroi=maintenant - JOUR * 2,
            retrait=maintenant - JOUR,
        )

        #  4. Autorisation FUTURE — retrait nul, et c'est le piege.
        poser(CAS_AUTORISATION_FUTURE)
        a4 = _actif(cx, entite, deposant, maintenant=maintenant)
        _variante(cx, entite, a4)
        _autorisation(
            cx, r[f"personne-{CAS_AUTORISATION_FUTURE}"], a4, octroi=maintenant + JOUR * 30
        )

        #  5. Media non `ready`.
        poser(CAS_MEDIA_NON_PRET)
        a5 = _actif(cx, entite, deposant, etat=EtatMedia.PENDING.value, maintenant=maintenant)
        _variante(cx, entite, a5)
        _autorisation(cx, r[f"personne-{CAS_MEDIA_NON_PRET}"], a5, octroi=maintenant - JOUR)

        #  6. Aucune variante `thumbnail` : une `medium` seule.
        poser(CAS_SANS_MINIATURE)
        a6 = _actif(cx, entite, deposant, maintenant=maintenant)
        _variante(cx, entite, a6, type_v=AUTRES_VARIANTES[0])
        _autorisation(cx, r[f"personne-{CAS_SANS_MINIATURE}"], a6, octroi=maintenant - JOUR)

        #  7. Une AUTRE entite, dont la photo ne doit pas apparaitre ici.
        autre = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO entity (code, display_name, city, country_code, status, "
                        "timezone) VALUES (:code, :nom, 'Paris', 'FR', 'active', "
                        "'Europe/Paris') RETURNING id"
                    ),
                    {"code": f"{marqueur}-autre", "nom": f"Autre {marqueur}"},
                ).scalar_one()
            )
        )
        r["autre-entite"] = autre
        r["autre-code"] = f"{marqueur}-autre"

    yield parametres, code_entite, r
    _nettoyer(parametres, marqueur, debut_temps)


def _nettoyer(parametres: Parametres, marqueur: str, debut: dt.datetime) -> None:
    """L'ordre suit les cles etrangeres.

    **UN ORDRE FAUTIF ANNULE LA TRANSACTION ENTIERE**, donc ne supprime RIEN --
    pas meme ce qui aurait pu l'etre -- et les residus font echouer des tests
    sans rapport. C'est la huitieme occurrence de la classe §7.30, et
    `make residu-check` est ce qui la nomme.
    """
    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM photo_authorization WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM media_variant WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM media_asset WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM person WHERE email_normalized LIKE :motif",
            "DELETE FROM entity WHERE code LIKE :motif",
            "DELETE FROM auth_event WHERE person_id IS NULL "
            "  AND service_account_id IS NULL AND created_at >= :debut",
        ):
            menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _session(parametres: Parametres, marqueur: str) -> str:
    with moteur(parametres).begin() as cx:
        personne = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO person (email, email_normalized, first_name, last_name, "
                        "account_state) VALUES (:a, :a, 'Appelant', 'T5', 'active') RETURNING id"
                    ),
                    {"a": f"{marqueur}-appelant@exemple.test"},
                ).scalar_one()
            )
        )
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _appeler(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


# ===========================================================================
#  3. LE TEMOIN, puis les cinq refus
# ===========================================================================


@pytest.mark.integration
def test_LE_TEMOIN_la_miniature_autorisee_est_resolue(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE TEMOIN CENTRAL. SANS LUI, LES CINQ REFUS NE PROUVENT RIEN.**

    C'est le defaut `T2-3` : huit refus restaient verts sur une route qui
    refusait TOUT. Ce test est celui qui discrimine.

    Et il verifie que ce qui est resolu est bien la MINIATURE : les deux
    prefixes de cle sont distincts a dessein, donc « ce n'est pas l'original »
    est une affirmation mesurable et non une esperance.
    """
    parametres, _, r = decor
    with moteur(parametres).begin() as cx:
        miniature = resoudre_la_miniature(
            cx, entite=r["entite"], appartenance=r[CAS_SERVABLE], instant=r["maintenant"]
        )

    assert miniature is not None, "le temoin doit etre servi"
    assert miniature.object_key == r["cle-miniature"]
    assert miniature.object_key.startswith(MINIATURE)
    assert not miniature.object_key.startswith(ORIGINAL)
    assert miniature.size_bytes == 4096
    assert miniature.mime == "image/jpeg"


@pytest.mark.integration
@pytest.mark.parametrize("cas", TOUS_LES_REFUS)
def test_les_cinq_causes_donnent_TOUTES_un_avatar_neutre(
    decor: tuple[Parametres, str, dict[str, Any]], cas: str
) -> None:
    """Cinq causes, une seule observation — §21.2.

    Chacune ne differe du temoin que par **la** valeur en cause : le decor pose
    partout l'actif et la variante, si bien qu'un refus ne peut venir que de la
    condition visee.
    """
    parametres, _, r = decor
    with moteur(parametres).begin() as cx:
        miniature = resoudre_la_miniature(
            cx, entite=r["entite"], appartenance=r[cas], instant=r["maintenant"]
        )
    assert miniature is None, f"{cas} ne doit rien servir"


@pytest.mark.integration
def test_l_autorisation_FUTURE_devient_servable_le_jour_venu(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE TEMOIN DU TROISIEME REFUS, ET C'EST LE PLUS UTILE DU FICHIER.**

    `withdrawn_at IS NULL` seul aurait laisse passer l'autorisation future : son
    retrait est nul lui aussi. Le refus mesure au test precedent pourrait donc
    venir d'un `WHERE` trop large ailleurs.

    Ici, **seul l'instant change** : la meme ligne, le meme actif, la meme
    variante, et la photo devient servable. C'est ce qui prouve que la borne
    porte bien sur `granted_at`.
    """
    parametres, _, r = decor
    with moteur(parametres).begin() as cx:
        avant = resoudre_la_miniature(
            cx,
            entite=r["entite"],
            appartenance=r[CAS_AUTORISATION_FUTURE],
            instant=r["maintenant"],
        )
        apres = resoudre_la_miniature(
            cx,
            entite=r["entite"],
            appartenance=r[CAS_AUTORISATION_FUTURE],
            instant=r["maintenant"] + JOUR * 31,
        )
    assert avant is None
    assert apres is not None, "l'octroi atteint rend la photo servable"


@pytest.mark.integration
def test_une_photo_d_une_AUTRE_entite_n_est_pas_servie(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """§25.3 : l'actif porte un `entity_id`, et l'isolation en depend.

    **LE PIEGE EST QUE LA PERSONNE, ELLE, EST LA MEME.** `photo_authorization`
    ne porte aucun `entity_id` -- mesure de `T1` -- donc une autorisation vaut
    pour la personne, pas pour l'entite. C'est l'actif qui doit etre filtre, et
    ce test le prouve : la meme personne, une photo dans l'autre entite, et rien
    n'est servi.
    """
    parametres, _, r = decor
    personne = r[f"personne-{CAS_SANS_AUTORISATION}"]
    with moteur(parametres).begin() as cx:
        #  La MEME personne recoit une photo autorisee, mais dans l'AUTRE entite.
        actif = _actif(cx, r["autre-entite"], personne, maintenant=r["maintenant"])
        _variante(cx, r["autre-entite"], actif)
        _autorisation(cx, personne, actif, octroi=r["maintenant"] - JOUR)

        miniature = resoudre_la_miniature(
            cx,
            entite=r["entite"],
            appartenance=r[CAS_SANS_AUTORISATION],
            instant=r["maintenant"],
        )
    assert miniature is None, "une photo d'une autre entite ne remonte pas ici"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("etat", "visibilite"),
    [
        (EtatAppartenance.DEPARTED.value, VisibiliteProfil.PUBLISHED.value),
        (EtatAppartenance.ACTIVE.value, VisibiliteProfil.DRAFT.value),
    ],
)
def test_un_profil_que_la_LISTE_exclut_ne_sert_pas_sa_photo(
    decor: tuple[Parametres, str, dict[str, Any]], etat: str, visibilite: str
) -> None:
    """**LA MEME POPULATION QUE LE TROMBINOSCOPE, ET C'EST LA REGLE PARTAGEE.**

    Servir la photo d'un profil que la liste exclut rendrait le filtre de la
    liste decoratif : l'identifiant d'appartenance suffirait a obtenir l'image
    d'un partant. Les deux filtres sont necessaires -- le §22.5 etape 5
    « masquage du profil » n'est implemente nulle part, donc un partant reste
    `published`.
    """
    parametres, _, r = decor
    deposant = r[f"personne-{CAS_SERVABLE}"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, f"{visibilite}-{etat}", "Exclu")
        appartenance = _appartenance(cx, r["entite"], personne, etat=etat, visibilite=visibilite)
        actif = _actif(cx, r["entite"], deposant, maintenant=r["maintenant"])
        _variante(cx, r["entite"], actif)
        _autorisation(cx, personne, actif, octroi=r["maintenant"] - JOUR)

        miniature = resoudre_la_miniature(
            cx, entite=r["entite"], appartenance=appartenance, instant=r["maintenant"]
        )

        #  Menage immediat : cette personne est hors du marqueur de la fixture.
        for requete in (
            "DELETE FROM photo_authorization WHERE person_id = :p",
            "DELETE FROM media_variant WHERE media_asset_id = :a",
            "DELETE FROM media_asset WHERE id = :a",
            "DELETE FROM entity_membership WHERE person_id = :p",
            "DELETE FROM person WHERE id = :p",
        ):
            cx.execute(text(requete), {"p": personne, "a": actif})

    assert miniature is None, f"{etat}/{visibilite} est hors de la liste, donc hors photo"


# ===========================================================================
#  4. La borne des 100 Ko, A L'OCTET
# ===========================================================================


@pytest.mark.integration
def test_la_borne_des_cent_kilo_octets_est_franchie_A_L_OCTET(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**99 999 PASSE, 100 000 EST REFUSE.**

    Un test a 50 Ko et 200 Ko passerait avec une borne posee **n'importe ou**
    entre les deux : il mesurerait qu'une borne existe, pas qu'elle est celle du
    cahier. C'est le §7.0 sixieme proposition -- deux nombres doivent mesurer la
    meme grandeur, et ici la grandeur est la valeur EXACTE du §25.3.
    """
    parametres, _, r = decor
    moteur_ = moteur(parametres)

    #  TEMOIN : un octet sous la borne passe.
    with moteur_.begin() as cx:
        actif = _actif(cx, r["entite"], r[f"personne-{CAS_SERVABLE}"], maintenant=r["maintenant"])
        _variante(
            cx,
            r["entite"],
            actif,
            type_v=AUTRES_VARIANTES[0],
            taille=BORNE_MINIATURE_OCTETS - 1,
        )
        _variante(cx, r["entite"], actif, taille=BORNE_MINIATURE_OCTETS - 1)
        cx.execute(text("DELETE FROM media_variant WHERE media_asset_id = :a"), {"a": actif})
        cx.execute(text("DELETE FROM media_asset WHERE id = :a"), {"a": actif})

    #  REFUS : la borne exacte est refusee, et la contrainte est NOMMEE.
    with pytest.raises(IntegrityError) as echec, moteur_.begin() as cx:
        actif = _actif(cx, r["entite"], r[f"personne-{CAS_SERVABLE}"], maintenant=r["maintenant"])
        _variante(cx, r["entite"], actif, taille=BORNE_MINIATURE_OCTETS)
    assert CONTRAINTE_DE_BORNE in str(echec.value)


@pytest.mark.integration
def test_la_borne_ne_porte_QUE_sur_la_miniature(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE TEMOIN DE LA BORNE, ET IL EST INDISPENSABLE.**

    Le §25.3 borne « la miniature trombinoscope ». Une contrainte qui bornerait
    les CINQ types de variante casserait le LOT 11, ou l'original et la variante
    `large` pesent bien davantage -- et rien ne le dirait avant ce lot-la.
    """
    parametres, _, r = decor
    with moteur(parametres).begin() as cx:
        actif = _actif(cx, r["entite"], r[f"personne-{CAS_SERVABLE}"], maintenant=r["maintenant"])
        for type_v in AUTRES_VARIANTES:
            _variante(cx, r["entite"], actif, type_v=type_v, taille=5_000_000)
        cx.execute(text("DELETE FROM media_variant WHERE media_asset_id = :a"), {"a": actif})
        cx.execute(text("DELETE FROM media_asset WHERE id = :a"), {"a": actif})


@pytest.mark.integration
def test_la_contrainte_de_la_migration_porte_EXACTEMENT_la_valeur_du_module(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """Deux copies d'un seuil divergent — §7.27.

    La valeur est lue **dans le catalogue**, pas dans le fichier de migration :
    ce qui compte est ce que la base applique, non ce qu'un fichier declare.
    """
    parametres, _, _ = decor
    with moteur(parametres).connect() as cx:
        definition = cx.execute(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :nom"),
            {"nom": CONTRAINTE_DE_BORNE},
        ).scalar_one()
    assert str(BORNE_MINIATURE_OCTETS) in definition
    assert "thumbnail" in definition


# ===========================================================================
#  5. Par les routes : la liste, la fiche, et les octets
# ===========================================================================


@pytest.mark.integration
def test_la_LISTE_annonce_le_chemin_de_photo_pour_le_temoin_et_null_pour_les_autres(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LA LISTE ET LA ROUTE PARTAGENT LEURS CONDITIONS, ET CA SE MESURE ICI.**

    Si les deux portaient leurs propres regles, la liste annoncerait un chemin
    que la route refuse -- une image cassee dans le trombinoscope, et aucun test
    de la liste seule ne le verrait.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN_LISTE.format(code=code) + "?taille=100",
        _session(parametres, code[:-2]),
    )
    assert reponse.status_code == 200, reponse.text
    par_id = {ligne["id"]: ligne for ligne in reponse.json()["collaborateurs"]}

    #  Le temoin porte le chemin, et c'est EXACTEMENT celui de la route.
    attendu = chemin_de_la_photo(parametres.API_PREFIX, code, r[CAS_SERVABLE])
    assert par_id[str(r[CAS_SERVABLE])]["photo"] == attendu

    #  Les cinq autres annoncent `null` — l'appelant sert l'avatar neutre.
    for cas in TOUS_LES_REFUS:
        assert par_id[str(r[cas])]["photo"] is None, cas

    #  **AUCUNE CLE D'OBJET DANS LA REPONSE**, ni de l'original ni de la variante.
    assert ORIGINAL not in reponse.text
    assert MINIATURE not in reponse.text


@pytest.mark.integration
def test_la_FICHE_annonce_le_meme_chemin_que_la_liste(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """Les deux reponses passent par la meme fonction : ce test le prouve.

    Et la fiche non plus ne porte aucune cle d'objet -- l'original pese deux
    mega-octets dans ce decor, sa fuite serait spectaculaire.
    """
    parametres, code, r = decor
    jeton = _session(parametres, code[:-2])
    fiche = _appeler(
        parametres, CHEMIN_FICHE.format(code=code, appartenance=r[CAS_SERVABLE]), jeton
    )
    assert fiche.status_code == 200, fiche.text
    assert fiche.json()["photo"] == chemin_de_la_photo(parametres.API_PREFIX, code, r[CAS_SERVABLE])
    assert ORIGINAL not in fiche.text
    assert MINIATURE not in fiche.text

    vide = _appeler(
        parametres,
        CHEMIN_FICHE.format(code=code, appartenance=r[CAS_AUTORISATION_RETIREE]),
        jeton,
    )
    assert vide.status_code == 200, vide.text
    assert vide.json()["photo"] is None


@pytest.mark.integration
def test_la_route_de_photo_EXIGE_une_session(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**AUCUN CONTOURNEMENT DE L'AUTHENTIFICATION**, y compris pour une image.

    Une image servie sans session serait une fuite de donnee personnelle
    accessible par simple URL, et le §5 met `ANON` a « — » sur tout le
    trombinoscope.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres, CHEMIN_PHOTO.format(code=code, appartenance=r[CAS_SERVABLE]), None
    )
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
@pytest.mark.parametrize("cas", TOUS_LES_REFUS)
def test_la_route_de_photo_rend_404_pour_les_cinq_causes(
    decor: tuple[Parametres, str, dict[str, Any]], cas: str
) -> None:
    """Le meme 404 que pour une entite inconnue, au format du §18.3."""
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN_PHOTO.format(code=code, appartenance=r[cas]),
        _session(parametres, code[:-2]),
    )
    assert reponse.status_code == 404, reponse.text
    corps = reponse.json()
    assert set(corps) == {"erreur"}, "le format du §18.3 imbrique sous `erreur`"
    assert corps["erreur"]["code"] == "entite_introuvable"


@pytest.mark.integration
def test_la_route_de_photo_rend_404_quand_l_objet_manque_du_STOCKAGE(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LA SIXIEME CAUSE, ET ELLE N'EST PAS EN BASE.**

    La variante existe, l'autorisation est active, le media est `ready` -- et
    l'objet n'a jamais ete deverse dans MinIO. C'est l'etat NORMAL de ce lot :
    `T5` ne fabrique aucune miniature, le LOT 11 le fera.

    La route doit donc rendre le meme 404 plutot qu'un 500, **et la cause doit
    partir au journal** : sans cela, une panne de MinIO produirait des avatars
    neutres en silence sur tout le trombinoscope. Defaut `T5-1`.
    """
    parametres, code, r = decor
    reponse = _appeler(
        parametres,
        CHEMIN_PHOTO.format(code=code, appartenance=r[CAS_SERVABLE]),
        _session(parametres, code[:-2]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "entite_introuvable"
    #  La cle d'objet ne fuit pas dans la reponse, meme en cas d'echec de lecture.
    assert MINIATURE not in reponse.text


@pytest.mark.integration
def test_la_cause_de_l_echec_de_lecture_part_au_JOURNAL(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE DEFAUT `T5-1` FIGE PAR UN TEST.**

    J'avais ecrit « la cause reste au journal » en commentaire, alors que
    `gerer_erreur_applicative` **ne journalise rien** -- mesure du 07/09/2026 sur
    `app/shared/errors.py`. Classe §7.11 : verifie ce que la documentation
    affirme, meme quand c'est toi qui l'ecris. Le remede a ete de rendre
    l'affirmation vraie, et ce test empeche qu'elle redevienne fausse.

    **ET LA CAPTURE PASSE PAR LE FLUX REEL, PAS PAR `caplog`.** Defaut `T5-3` :
    `creer_application` remplace les poignees de la racine par la sienne, si bien
    que `caplog` ne voyait **aucun** enregistrement -- le test echouait sur un
    livrable correct. La convention du projet, posee par `T4` du LOT 1, est de
    detourner le flux de la poignee racine : cela eprouve **en plus** le
    formateur JSON du §28.1 et les barrieres de masquage du §28.2, ce que
    `caplog` aurait contourne.
    """
    parametres, code, r = decor
    jeton = _session(parametres, code[:-2])
    application = creer_application(parametres)
    tampon = io.StringIO()
    racine = logging.getLogger()
    poignee = racine.handlers[0]
    flux_initial = poignee.stream  # type: ignore[attr-defined]
    poignee.stream = tampon  # type: ignore[attr-defined]
    try:
        with TestClient(application, base_url=ORIGINE_DE_TEST) as client:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
            reponse = client.get(CHEMIN_PHOTO.format(code=code, appartenance=r[CAS_SERVABLE]))
    finally:
        poignee.stream = flux_initial  # type: ignore[attr-defined]

    assert reponse.status_code == 404, reponse.text
    traces = [
        json.loads(ligne)
        for ligne in tampon.getvalue().splitlines()
        if ligne.strip().startswith("{")
    ]
    echecs = [t for t in traces if t.get("code_erreur") == "miniature_illisible"]
    assert echecs, f"l'echec de lecture doit etre journalise ; {len(traces)} traces vues"
    assert echecs[0]["resultat"] == "echec", "`DEC-468` : echec, et non refus"
    #  **LA CLE EST SOUS `contexte`, ET NON A LA RACINE. DEFAUT `T5-4`.**
    #  Le formateur du §28.1 emet **dix champs nommes** ; tout `extra=`
    #  supplementaire rejoint un sous-objet `contexte`, masque comme le reste
    #  (`packages/observabilite/observabilite/journalisation.py`). Ma premiere
    #  version la cherchait a la racine et echouait sur un livrable correct :
    #  c'est le §7.11 une seconde fois dans la meme sous-etape, sur du code que
    #  je n'avais pas ecrit cette fois.
    #
    #  La cle est au journal -- c'est la seule facon de retrouver l'objet -- et
    #  le §16.1 n'interdit qu'un `object_key` FOURNI par le client.
    assert echecs[0]["contexte"]["cle_objet"].startswith(MINIATURE)
    #  **ET LE CORRELATEUR EST LA** : sans lui, l'exploitant ne peut pas relier
    #  cette trace a la requete qui l'a produite (§28.1). Le champ s'appelle
    #  `identifiant_correlation` -- les dix champs du cahier sont nommes en
    #  francais, et j'avais d'abord ecrit le nom anglais.
    assert echecs[0].get("identifiant_correlation"), "§28.1 : la trace doit etre correlee"

    #  **ET C'EST LE CORRELATEUR QUI PORTE LA ROUTE, PAS CETTE TRACE.** Le champ
    #  `route` est renseigne par le journal de requete, non par un appel emis
    #  depuis un gestionnaire : sur ma trace il vaut `None`, et l'exiger aurait
    #  fait echouer un livrable correct (§7.20). Ce qui se prouve, et qui est ce
    #  dont l'exploitant a besoin, c'est que **les deux traces portent le meme
    #  identifiant** -- donc que l'echec de lecture est rattachable a la requete
    #  qui l'a produit, laquelle nomme la route.
    requetes = [
        trace
        for trace in traces
        if trace.get("identifiant_correlation") == echecs[0]["identifiant_correlation"]
        and trace.get("route")
    ]
    assert requetes, "la trace de requete doit partager l'identifiant de correlation"
    assert requetes[0]["route"].endswith("/photo")


@pytest.mark.integration
def test_la_route_de_photo_ne_sert_JAMAIS_l_original(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE CRITERE, PROUVE PAR LES OCTETS ET NON PAR RELECTURE.**

    L'objet de la MINIATURE est deverse dans MinIO, celui de l'ORIGINAL aussi,
    avec des contenus differents. La route sert les octets de la miniature, et
    **jamais** ceux de l'original -- c'est la seule forme de ce test qui
    discrimine : un test qui verifierait seulement « 200 et des octets »
    passerait si la route servait l'original.
    """
    parametres, code, r = decor
    boto3 = pytest.importorskip("boto3")
    from app.media.objets import client_s3

    client = client_s3(parametres)
    octets_miniature = b"MINIATURE-" + b"m" * 90
    with moteur(parametres).connect() as cx:
        cle_originale = cx.execute(
            text("SELECT object_key FROM media_asset WHERE id = :a"),
            {"a": r["actif-servable"]},
        ).scalar_one()

    try:
        client.put_object(  # type: ignore[attr-defined]
            Bucket=parametres.MINIO_BUCKET, Key=r["cle-miniature"], Body=octets_miniature
        )
        client.put_object(  # type: ignore[attr-defined]
            Bucket=parametres.MINIO_BUCKET, Key=cle_originale, Body=b"ORIGINAL-" + b"o" * 2000
        )
    except Exception as erreur:
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")

    try:
        reponse = _appeler(
            parametres,
            CHEMIN_PHOTO.format(code=code, appartenance=r[CAS_SERVABLE]),
            _session(parametres, code[:-2]),
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.content == octets_miniature
        assert not reponse.content.startswith(b"ORIGINAL")
        assert len(reponse.content) < BORNE_MINIATURE_OCTETS
        assert reponse.headers["content-type"].startswith("image/jpeg")
    finally:
        for cle in (r["cle-miniature"], cle_originale):
            client.delete_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]
    assert boto3 is not None


@pytest.mark.integration
def test_la_liste_ne_paie_pas_une_requete_par_ligne(
    decor: tuple[Parametres, str, dict[str, Any]],
) -> None:
    """**LE N+1 QUE LE CRITERE DE `T3` INTERDIT.**

    L'`EXISTS` de la photo est dans la requete de page : la liste doit rester a
    **deux** requetes quel que soit le nombre de lignes. Resoudre la variante
    ligne par ligne aurait donne 2 + n.
    """
    from app.people.trombinoscope import Filtres, lister_le_trombinoscope

    parametres, _, r = decor
    compte = 0

    from sqlalchemy import event

    moteur_ = moteur(parametres)

    def compter(*_args: object, **_kwargs: object) -> None:
        nonlocal compte
        compte += 1

    event.listen(moteur_, "before_cursor_execute", compter)
    try:
        with moteur_.begin() as cx:
            compte = 0
            page = lister_le_trombinoscope(
                cx,
                entite=r["entite"],
                page=1,
                taille=100,
                instant=r["maintenant"],
                filtres=Filtres(),
            )
    finally:
        event.remove(moteur_, "before_cursor_execute", compter)

    assert page.total >= 6, "le decor porte six appartenances"
    assert compte == 2, f"deux requetes attendues, {compte} observees"
    assert sum(1 for c in page.collaborateurs if c.a_une_photo) == 1


@pytest.mark.integration
def test_l_etat_de_liste_est_bien_celui_du_trombinoscope() -> None:
    """La regle partagee est DERIVEE, et non recopiee dans trois modules.

    `T5` a fait apparaitre un import circulaire entre le trombinoscope et la
    photo : le cycle disait que la regle n'appartenait a aucun des deux. Elle vit
    donc dans `app/people/modeles.py`, aux cotes d'`ETATS_OCCUPANTS`.
    """
    assert EtatAppartenance.ACTIVE.value == ETAT_LISTE
    assert VisibiliteProfil.PUBLISHED.value == "published"
