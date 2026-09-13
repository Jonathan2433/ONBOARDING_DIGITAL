"""Les trois tables de media et d'autorisation de photo — LOT 5, `T1`.

CE QUE CE FICHIER PROUVE, ET CE QU'IL NE PEUT PAS PROUVER

  Il prouve ce que la BASE refuse : les enumerations, les bornes de taille et de
  duree, l'isolation par cle composite, l'unicite derivee du §16.2, et le
  caractere terminal de `deleted`.

  **Il ne prouve PAS « une photo ne peut pas etre publiee sans autorisation
  active »**, et ce n'est pas un oubli : le §25.4 du modele range cette regle
  parmi celles « necessitant service ou trigger controle ». Elle appartient a
  `T6`, avec ses propres tests d'integration, et `make recette-modele-check`
  garde le §30.12 en `REPORTE` jusque-la.

CHAQUE REFUS A SON TEMOIN

  Un test qui n'exigerait que l'echec serait satisfait par une table
  ininsertable. Chaque refus est donc double d'une insertion qui REUSSIT, au
  voisinage immediat de la borne quand il y en a une.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.media import (
    ETATS_MEDIA,
    SOURCES_AUTORISATION_PHOTO,
    TYPES_MEDIA,
    EtatMedia,
    SourceAutorisationPhoto,
    TypeMedia,
    TypeVarianteMedia,
)
from app.media.modeles import (
    DUREE_MAXIMALE_VIDEO_SECONDES,
    TAILLE_MAXIMALE_IMAGE_OCTETS,
    TAILLE_MAXIMALE_VIDEO_OCTETS,
)
from app.modeles import metadonnees
from app.shared.database import moteur

ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
EMPREINTE = "a" * 64

# ============================================================================
#  1. Unitaires — les enumerations suivent le modele A LA LETTRE
# ============================================================================


def test_les_six_etats_du_paragraphe_16_1() -> None:
    """§16.1 : « `pending`, `processing`, `ready`, `rejected`, `archived`, `deleted` »."""
    assert ETATS_MEDIA == ("pending", "processing", "ready", "rejected", "archived", "deleted")


def test_les_trois_types_du_paragraphe_16_1() -> None:
    """§16.1 : « `image`, `video`, `document` si autorise ulterieurement ».

    **Les TROIS sont admises.** `document` porte sa reserve dans le modele
    lui-meme ; en restreindre la contrainte a deux exigerait plus que le modele,
    ce que le §7.20 nomme un defaut.
    """
    assert TYPES_MEDIA == ("image", "video", "document")


def test_les_trois_sources_du_paragraphe_12_2() -> None:
    """§12.2 : « `self_service`, `admin_support`, `migration` »."""
    assert SOURCES_AUTORISATION_PHOTO == ("self_service", "admin_support", "migration")


def test_les_cinq_variantes_du_paragraphe_16_2() -> None:
    """§16.2 : « miniature trombinoscope ; carte ; pleine largeur ; apercu video ;
    format optimise ».

    **Cinq, et le compte est le point du test.** Une sixieme variante ajoutee sans
    decision passerait autrement inapercue.
    """
    assert len(tuple(TypeVarianteMedia)) == 5


def test_media_usage_n_est_PAS_creee_et_c_est_delibere() -> None:
    """§16.3 declare `media_usage`. Elle n'existe pas, et `DEC-558` l'a arbitre.

    Elle ne sert qu'a la mediatheque **V1** — matrice §12.2, « voir les usages »,
    « detecter les medias inutilises » — donc elle serait une table SANS
    CONSOMMATEUR, ce que `DEC-537` refuse.

    **Ce test existe pour que sa creation soit une DECISION**, pas un effet de
    bord. Le lot qui la voudra devra le retirer, et saura pourquoi il existait.
    """
    assert "media_usage" not in metadonnees.tables


def test_media_variant_porte_un_entity_id_que_le_16_2_n_ecrit_pas() -> None:
    """§25.3 : « les tables locales exposent un couple unique `(id, entity_id)` ».

    Le §16.2 n'enumere pas `entity_id`. Le §25.3, lui, prescrit le motif pour
    toute table **locale** — et une variante appartient a un actif qui appartient
    a une entite. **Sans cette colonne, la cle vers `media_asset` serait SIMPLE**,
    et une variante pourrait pointer l'actif d'une autre entite.

    §7.24 : deux sections du meme document, et c'est en les confrontant qu'on
    obtient la reponse.
    """
    colonnes = metadonnees.tables["media_variant"].c
    assert "entity_id" in colonnes
    assert not colonnes["entity_id"].nullable
    #  Et la cle est bien COMPOSITE : deux colonnes, pas une.
    composites = [
        fk
        for fk in metadonnees.tables["media_variant"].foreign_key_constraints
        if fk.name == "fk_media_variant_media_asset"
    ]
    assert len(composites) == 1
    assert len(composites[0].columns) == 2


def test_photo_authorization_est_GLOBALE_et_n_a_pas_d_entity_id() -> None:
    """Elle lie une personne — table globale — a un `media_asset`.

    Lui donner un `entity_id` ferait de l'autorisation une donnee d'entite, ce que
    le §12.2 n'ecrit pas et que le sens contredit : c'est la personne qui autorise
    sa photo. `make isolation-check` la classera globale, sa derivation lisant les
    sections du modele.
    """
    assert "entity_id" not in metadonnees.tables["photo_authorization"].c


def test_aucune_unicite_sur_photo_authorization_et_ce_n_est_pas_un_oubli() -> None:
    """« Au plus une autorisation active par personne » n'est ecrit NULLE PART.

    Ni au §12.2, ni au §25.1, ni au §25.4. L'inventer serait la regle §6.5
    enfreinte, et le §7.32 dit l'inverse : n'ecris pas de defense contre un etat
    que rien n'interdit.

    **Ce test fige l'absence pour que `T6` la traite explicitement** — soit en
    posant la regle au service, soit en ouvrant une question au registre.
    """
    table = metadonnees.tables["photo_authorization"]
    uniques = [c for c in table.constraints if c.__class__.__name__ == "UniqueConstraint"]
    index_uniques = [i for i in table.indexes if i.unique]
    assert uniques == []
    assert index_uniques == []


# ============================================================================
#  2. Integration — ce que la base REFUSE, et son temoin a chaque fois
# ============================================================================

MARQUEUR = "L5T1"


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


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Media', 'L5T1', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()


def _actif(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatMedia.PENDING.value,
    type_media: str = TypeMedia.IMAGE.value,
    taille: int = 1024,
    duree: int | None = None,
    code_rejet: str | None = None,
    pret_a: dt.datetime | None = None,
    empreinte: str = EMPREINTE,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256, "
            "duration_seconds, rejection_code, ready_at) "
            "VALUES (:entite, :personne, :etat, :type_media, 'photo.jpg', :cle, 'image/jpeg', "
            ":taille, :empreinte, :duree, :rejet, :pret) RETURNING id"
        ),
        {
            "entite": entite,
            "personne": personne,
            "etat": etat,
            "type_media": type_media,
            #  Une cle d'objet par insertion : deux actifs du meme decor ne
            #  doivent pas se confondre dans un diagnostic.
            "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            "taille": taille,
            "empreinte": empreinte,
            "duree": duree,
            "rejet": code_rejet,
            "pret": pret_a,
        },
    ).scalar_one()


@pytest.mark.integration
def test_une_image_de_20_Mo_passe_et_un_octet_de_plus_est_REFUSE(cx: Connection) -> None:
    """§16.1 : « image 20 Mo maximum ». La borne est testee DES DEUX COTES.

    Un test qui n'exigerait que le refus serait satisfait par une contrainte qui
    refuse tout. La valeur exacte de la borne est celle du modele, et elle est
    **derivee** de la constante, jamais recopiee.
    """
    a = _entite(cx, f"{MARQUEUR}-IMG")
    p = _personne(cx, "l5t1-img@exalt-company.com")

    #  TEMOIN : la borne exacte passe.
    assert _actif(cx, a, p, taille=TAILLE_MAXIMALE_IMAGE_OCTETS) is not None

    with pytest.raises(IntegrityError) as leve:
        _actif(cx, a, p, taille=TAILLE_MAXIMALE_IMAGE_OCTETS + 1)
    assert "ck_media_asset_taille_selon_le_type" in str(leve.value)


@pytest.mark.integration
def test_une_video_va_jusqu_a_1_Go_la_ou_une_image_s_arrete_a_20_Mo(cx: Connection) -> None:
    """La borne depend du TYPE, et c'est ce que la contrainte disjonctive dit.

    **Ce test discrimine ce qu'une borne unique ne dirait pas** : la meme taille
    est acceptee en `video` et refusee en `image`.
    """
    a = _entite(cx, f"{MARQUEUR}-VID")
    p = _personne(cx, "l5t1-vid@exalt-company.com")
    taille = TAILLE_MAXIMALE_IMAGE_OCTETS + 1

    assert _actif(cx, a, p, type_media=TypeMedia.VIDEO.value, taille=taille) is not None

    with pytest.raises(IntegrityError):
        _actif(cx, a, p, type_media=TypeMedia.IMAGE.value, taille=taille)


@pytest.mark.integration
def test_une_video_de_plus_de_1_Go_est_refusee(cx: Connection) -> None:
    """§16.1 : « video 1 Go [...] maximum »."""
    a = _entite(cx, f"{MARQUEUR}-VID2")
    p = _personne(cx, "l5t1-vid2@exalt-company.com")

    assert (
        _actif(cx, a, p, type_media=TypeMedia.VIDEO.value, taille=TAILLE_MAXIMALE_VIDEO_OCTETS)
        is not None
    )
    with pytest.raises(IntegrityError) as leve:
        _actif(cx, a, p, type_media=TypeMedia.VIDEO.value, taille=TAILLE_MAXIMALE_VIDEO_OCTETS + 1)
    assert "ck_media_asset_taille_selon_le_type" in str(leve.value)


@pytest.mark.integration
def test_une_duree_de_plus_de_20_minutes_est_refusee(cx: Connection) -> None:
    """§16.1 : « video 1 Go et **20 minutes** maximum »."""
    a = _entite(cx, f"{MARQUEUR}-DUR")
    p = _personne(cx, "l5t1-dur@exalt-company.com")

    assert (
        _actif(
            cx,
            a,
            p,
            type_media=TypeMedia.VIDEO.value,
            duree=DUREE_MAXIMALE_VIDEO_SECONDES,
        )
        is not None
    )
    with pytest.raises(IntegrityError) as leve:
        _actif(
            cx,
            a,
            p,
            type_media=TypeMedia.VIDEO.value,
            duree=DUREE_MAXIMALE_VIDEO_SECONDES + 1,
        )
    assert "ck_media_asset_duree_bornee" in str(leve.value)


@pytest.mark.integration
def test_un_code_de_rejet_sur_un_media_READY_est_refuse(cx: Connection) -> None:
    """§24.3 : seul `Processing --> Rejected` mene a cet etat.

    Un code de rejet sur un media `ready` n'a donc aucun sens. **C'est
    l'IMPLICATION qui est posee, non l'obligation inverse** : le §16.1 ecrit
    `rejection_code` « nullable » sans dire qu'un rejet en exige un, et l'inventer
    serait le §6.5.
    """
    a = _entite(cx, f"{MARQUEUR}-REJ")
    p = _personne(cx, "l5t1-rej@exalt-company.com")

    #  TEMOIN : le meme code sur un media REJETE passe.
    assert _actif(cx, a, p, etat=EtatMedia.REJECTED.value, code_rejet="MIME_INVALIDE") is not None

    with pytest.raises(IntegrityError) as leve:
        _actif(cx, a, p, etat=EtatMedia.READY.value, code_rejet="MIME_INVALIDE", pret_a=ANCRAGE)
    assert "ck_media_asset_rejet_seulement_si_rejete" in str(leve.value)


@pytest.mark.integration
def test_un_ready_at_sur_un_media_PENDING_est_refuse(cx: Connection) -> None:
    """§24.3 : le diagramme fait passer par `Ready` avant `Archived`.

    Un instant de mise a disposition sur un media qui n'a jamais ete pret serait
    une date sans evenement.
    """
    a = _entite(cx, f"{MARQUEUR}-RDY")
    p = _personne(cx, "l5t1-rdy@exalt-company.com")

    assert _actif(cx, a, p, etat=EtatMedia.READY.value, pret_a=ANCRAGE) is not None

    with pytest.raises(IntegrityError) as leve:
        _actif(cx, a, p, etat=EtatMedia.PENDING.value, pret_a=ANCRAGE)
    assert "ck_media_asset_ready_at_selon_l_etat" in str(leve.value)


@pytest.mark.integration
def test_un_media_SUPPRIME_ne_peut_pas_etre_restaure(cx: Connection) -> None:
    """§24.3 : `Deleted --> [*]`, aucune transition n'en sort.

    Meme motif que `person.account_state = 'anonymized'` au LOT 2 : ce que la
    suppression a efface n'est plus la pour etre restaure. **Un `CHECK` ne peut pas
    l'exprimer** — il ne voit pas l'ancienne valeur — d'ou le declencheur.
    """
    a = _entite(cx, f"{MARQUEUR}-DEL")
    p = _personne(cx, "l5t1-del@exalt-company.com")
    actif = _actif(cx, a, p, etat=EtatMedia.DELETED.value)

    with pytest.raises(IntegrityError) as leve:
        cx.execute(
            text("UPDATE media_asset SET state = :etat WHERE id = :id"),
            {"etat": EtatMedia.ARCHIVED.value, "id": actif},
        )
    assert "media_asset_suppression_terminale" in str(leve.value)


@pytest.mark.integration
def test_les_autres_transitions_d_etat_restent_permises(cx: Connection) -> None:
    """TEMOIN : le declencheur ne verrouille QUE la sortie de `deleted`.

    Sans lui, un declencheur qui refuserait tout changement d'etat passerait le
    test precedent — l'echec produirait la meme observation que le succes (§7.0).
    """
    a = _entite(cx, f"{MARQUEUR}-TRANS")
    p = _personne(cx, "l5t1-trans@exalt-company.com")
    actif = _actif(cx, a, p, etat=EtatMedia.READY.value, pret_a=ANCRAGE)

    #  §24.3 : `Ready --> Archived`, puis `Archived --> Ready`, les deux ecrites.
    for etat in (EtatMedia.ARCHIVED.value, EtatMedia.READY.value, EtatMedia.DELETED.value):
        cx.execute(
            text("UPDATE media_asset SET state = :etat WHERE id = :id"),
            {"etat": etat, "id": actif},
        )
    lu = cx.execute(
        text("SELECT state FROM media_asset WHERE id = :id"), {"id": actif}
    ).scalar_one()
    assert lu == EtatMedia.DELETED.value


@pytest.mark.integration
def test_une_variante_ne_peut_pas_pointer_l_actif_d_une_AUTRE_entite(cx: Connection) -> None:
    """§25.3, et c'est la raison d'etre de l'`entity_id` de `media_variant`.

    Sans lui, la cle serait simple et cette insertion passerait. **Le temoin
    montre que la MEME insertion, dans la bonne entite, reussit** — sans quoi
    l'echec serait indistinguable d'une table ininsertable.
    """
    a = _entite(cx, f"{MARQUEUR}-ISO-A")
    b = _entite(cx, f"{MARQUEUR}-ISO-B")
    p = _personne(cx, "l5t1-iso@exalt-company.com")
    actif = _actif(cx, a, p, etat=EtatMedia.READY.value, pret_a=ANCRAGE)

    #  **LE TYPE DIFFERE ENTRE LE TEMOIN ET LE REFUS, ET C'EST INDISPENSABLE.**
    #  Premiere version : le meme `thumbnail` des deux cotes. C'est
    #  `uq_media_variant_asset_type_non_archive` qui se declenchait, PAS la cle
    #  composite -- l'unicite ne porte pas `entity_id`, donc elle voit le doublon
    #  d'abord. Le test echouait en nommant la mauvaise contrainte.
    #
    #  §7.25, seconde lecon : « un temoin qui n'exerce pas un controle ne prouve
    #  rien de ce controle ». Meme situation qu'au LOT 2, ou deux contraintes se
    #  partagent une regle et ou la premiere masque la seconde.
    def variante(entite: uuid.UUID, type_v: str) -> None:
        cx.execute(
            text(
                "INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, "
                "height, variant_format, size_bytes, checksum_sha256, object_key) "
                "VALUES (:entite, :actif, :type_v, 200, 200, 'jpeg', 4096, :empreinte, :cle)"
            ),
            {
                "entite": entite,
                "actif": actif,
                "type_v": type_v,
                "empreinte": EMPREINTE,
                "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            },
        )

    #  TEMOIN : dans SON entite, la variante passe.
    variante(a, TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value)

    with pytest.raises(IntegrityError) as leve:
        variante(b, TypeVarianteMedia.CARTE.value)
    assert "fk_media_variant_media_asset" in str(leve.value)


@pytest.mark.integration
def test_une_seule_variante_par_type_et_par_actif(cx: Connection) -> None:
    """Unicite DERIVEE du §16.2 : « Versions generees », cinq, nommees.

    Deux miniatures du meme actif seraient deux reponses a une meme question, et
    la lecture n'aurait aucun moyen de choisir. **Le temoin est un AUTRE type**,
    qui doit passer : sans lui, l'unicite pourrait porter sur le seul actif.
    """
    a = _entite(cx, f"{MARQUEUR}-UNIQ")
    p = _personne(cx, "l5t1-uniq@exalt-company.com")
    actif = _actif(cx, a, p, etat=EtatMedia.READY.value, pret_a=ANCRAGE)

    def variante(type_v: str) -> None:
        cx.execute(
            text(
                "INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, "
                "height, variant_format, size_bytes, checksum_sha256, object_key) "
                "VALUES (:entite, :actif, :type_v, 200, 200, 'jpeg', 4096, :empreinte, :cle)"
            ),
            {
                "entite": a,
                "actif": actif,
                "type_v": type_v,
                "empreinte": EMPREINTE,
                "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            },
        )

    variante(TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value)
    #  TEMOIN : un AUTRE type passe, donc l'unicite porte bien sur le couple.
    variante(TypeVarianteMedia.CARTE.value)

    with pytest.raises(IntegrityError) as leve:
        variante(TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value)
    assert "uq_media_variant_asset_type_non_archive" in str(leve.value)


@pytest.mark.integration
def test_deux_entites_peuvent_televerser_le_MEME_fichier(cx: Connection) -> None:
    """§25.1 ecrit `media_asset(entity_id, checksum_sha256) INDEX`, pas `UNIQUE`.

    **La distinction est deliberee** : le document ecrit `UNIQUE` treize fois dans
    la meme liste. Deux entites peuvent televerser le meme fichier, et meme une
    seule peut le faire deux fois — pour deux usages differents.

    Ce test fige la NON-unicite, pour qu'un lot ulterieur qui voudrait la poser
    doive le decider.
    """
    a = _entite(cx, f"{MARQUEUR}-DUP-A")
    b = _entite(cx, f"{MARQUEUR}-DUP-B")
    p = _personne(cx, "l5t1-dup@exalt-company.com")

    assert _actif(cx, a, p) is not None
    assert _actif(cx, b, p) is not None
    #  Et deux fois dans la MEME entite.
    assert _actif(cx, a, p) is not None


@pytest.mark.integration
def test_un_retrait_anterieur_a_l_octroi_est_refuse(cx: Connection) -> None:
    """Un retrait ne peut pas preceder l'autorisation qu'il retire.

    `>=` et non `>` : un octroi et un retrait dans la meme transaction portent le
    meme `now()`, et le temoin l'exige.
    """
    a = _entite(cx, f"{MARQUEUR}-AUT")
    p = _personne(cx, "l5t1-aut@exalt-company.com")
    actif = _actif(cx, a, p, etat=EtatMedia.READY.value, pret_a=ANCRAGE)

    def autorisation(retrait: dt.datetime | None) -> None:
        cx.execute(
            text(
                "INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, "
                "withdrawn_at, source) VALUES (:p, :m, :octroi, :retrait, :source)"
            ),
            {
                "p": p,
                "m": actif,
                "octroi": ANCRAGE,
                "retrait": retrait,
                "source": SourceAutorisationPhoto.SELF_SERVICE.value,
            },
        )

    #  TEMOINS : aucun retrait, puis un retrait SIMULTANE, puis un retrait apres.
    autorisation(None)
    autorisation(ANCRAGE)
    autorisation(ANCRAGE + dt.timedelta(days=1))

    with pytest.raises(IntegrityError) as leve:
        autorisation(ANCRAGE - dt.timedelta(seconds=1))
    assert "ck_photo_authorization_retrait_apres_octroi" in str(leve.value)
