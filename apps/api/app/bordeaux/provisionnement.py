"""Provisionnement rejouable de la Beta eXalt Bordeaux.

Ce module est une commande d'exploitation : aucune route d'import n'est ajoutee
au produit. Le classeur et les photos restent hors du depot Git.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import mimetypes
import pathlib
import re
import unicodedata
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.bordeaux.donnees import (
    BOOSTERS_PAR_CERCLE,
    BUREAUX_DE_BORDEAUX,
    CERCLES_DE_BORDEAUX,
    CODE_ENTITE_BORDEAUX,
    DESCRIPTION_CLOTURE_DES_BUREAUX,
    DOMAINE_EXALT,
    NOM_ENTITE_BORDEAUX,
    RESPONSABILITES_DE_PRESENTATION,
    RESPONSABLES_PAR_BUREAU,
    EmployeBordeaux,
    PopulationBordeaux,
)
from app.bordeaux.parcours import (
    COURRIEL_DU_NOUVEL_ARRIVANT_DE_DEMONSTRATION,
    NOM_DU_MODELE_BORDEAUX,
    TACHES_DU_PARCOURS_BORDEAUX,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine

    from app.configuration.settings import Parametres


@dataclasses.dataclass(frozen=True, slots=True)
class RapportDeProvisionnement:
    employes: int
    cercles: int
    bureaux: int
    photos_installees: int
    photos_ignorees: int
    taches_onboarding: int
    parcours_affectes: int
    avertissements: tuple[str, ...]


PRESENTATION_DE_BORDEAUX = (
    "eXalt Bordeaux rassemble des profils complémentaires autour d'une culture collaborative, "
    "humaine et orientée terrain. Cette page sert de repère onboarding pour aider les nouveaux "
    "arrivants à comprendre l'organisation locale, identifier les bons interlocuteurs et "
    "découvrir les cercles d'expertise."
)

EVENEMENTS_DE_DEMONSTRATION: tuple[tuple[str, str, dt.datetime, dt.datetime, str | None], ...] = (
    (
        "Soirée Rosember 🎀",
        DESCRIPTION_CLOTURE_DES_BUREAUX,
        dt.datetime(2026, 11, 19, 18, 30, tzinfo=dt.UTC),
        dt.datetime(2026, 11, 19, 23, 0, tzinfo=dt.UTC),
        "Bordeaux",
    ),
    (
        "Soirée de fin d'année — Gala ✨",
        "Soirée de fin d'année sur le thème Gala. Dress code : tenue de gala.",
        dt.datetime(2026, 12, 9, 19, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 12, 9, 23, 59, tzinfo=dt.UTC),
        "K Baroque, Bordeaux",
    ),
    (
        "eXaltemps de mars",
        "Toute l'agence réunie pour faire le point, partager et célébrer. Date à confirmer.",
        dt.datetime(2027, 3, 18, 9, 0, tzinfo=dt.UTC),
        dt.datetime(2027, 3, 18, 18, 0, tzinfo=dt.UTC),
        "eXalt Bordeaux",
    ),
    (
        "eXaltemps de juin — 6 ans d'eXalt Bordeaux 🎂",
        "L'eXaltemps de juin fête les 6 ans d'eXalt Bordeaux ! Date à confirmer.",
        dt.datetime(2027, 6, 18, 9, 0, tzinfo=dt.UTC),
        dt.datetime(2027, 6, 18, 18, 0, tzinfo=dt.UTC),
        "eXalt Bordeaux",
    ),
)


def _identifiant(connexion: Connection, requete: str, parametres: dict[str, object]) -> uuid.UUID:
    return uuid.UUID(str(connexion.execute(text(requete), parametres).scalar_one()))


def _entite(connexion: Connection, instant: dt.datetime) -> uuid.UUID:
    return _identifiant(
        connexion,
        """
        INSERT INTO entity (code, display_name, city, country_code, status, timezone, activated_at)
        VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris', :instant)
        ON CONFLICT (code) DO UPDATE SET display_name=EXCLUDED.display_name, city='Bordeaux',
          country_code='FR', status='active', timezone='Europe/Paris', archived_at=NULL,
          updated_at=:instant
        RETURNING id
        """,
        {"code": CODE_ENTITE_BORDEAUX, "nom": NOM_ENTITE_BORDEAUX, "instant": instant},
    )


def _personne(connexion: Connection, *, employe: EmployeBordeaux) -> uuid.UUID:
    return _identifiant(
        connexion,
        """
        INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
        VALUES (:email, :email, :prenom, :nom, 'active')
        ON CONFLICT (email_normalized) DO UPDATE SET email=EXCLUDED.email,
          first_name=EXCLUDED.first_name, last_name=EXCLUDED.last_name, updated_at=now()
        RETURNING id
        """,
        {
            "email": employe.courriel,
            "prenom": employe.prenom,
            "nom": employe.nom,
        },
    )


def _appartenance(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    date_d_arrivee: dt.date | None,
    instant: dt.datetime,
) -> uuid.UUID:
    existante = connexion.execute(
        text(
            "SELECT id FROM entity_membership WHERE entity_id=:entite AND person_id=:personne "
            "AND membership_state IN ('active', 'future') ORDER BY created_at DESC LIMIT 1"
        ),
        {"entite": entite, "personne": personne},
    ).scalar_one_or_none()
    etat = "future" if date_d_arrivee is not None and date_d_arrivee > instant.date() else "active"
    if existante is not None:
        connexion.execute(
            text(
                "UPDATE entity_membership SET arrival_date=:arrivee, "
                "membership_started_on=COALESCE(membership_started_on, :debut), "
                "membership_state=:etat, professional_category='consultant', "
                "profile_visibility='published', "
                "profile_published_at=COALESCE(profile_published_at, :instant), "
                "archived_at=NULL, updated_at=:instant WHERE id=:id"
            ),
            {
                "id": existante,
                "arrivee": date_d_arrivee,
                "debut": date_d_arrivee or instant.date(),
                "etat": etat,
                "instant": instant,
            },
        )
        return uuid.UUID(str(existante))
    return _identifiant(
        connexion,
        """
        INSERT INTO entity_membership
          (entity_id, person_id, arrival_date, membership_started_on, membership_state,
           professional_category, profile_visibility, profile_published_at)
        VALUES (:entite, :personne, :arrivee, :debut, :etat, 'consultant', 'published', :instant)
        RETURNING id
        """,
        {
            "entite": entite,
            "personne": personne,
            "arrivee": date_d_arrivee,
            "debut": date_d_arrivee or instant.date(),
            "etat": etat,
            "instant": instant,
        },
    )


def _referentiels(
    connexion: Connection, *, entite: uuid.UUID
) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    cercles: dict[str, uuid.UUID] = {}
    for ordre, (code, nom, couleur) in enumerate(CERCLES_DE_BORDEAUX):
        cercles[code] = _identifiant(
            connexion,
            """
            INSERT INTO circle (entity_id, code, name, color_token, display_order)
            VALUES (:entite, :code, :nom, :couleur, :ordre)
            ON CONFLICT (entity_id, code) WHERE archived_at IS NULL DO UPDATE
              SET name=EXCLUDED.name, color_token=EXCLUDED.color_token,
                  display_order=EXCLUDED.display_order, updated_at=now()
            RETURNING id
            """,
            {"entite": entite, "code": code, "nom": nom, "couleur": couleur, "ordre": ordre},
        )
    bureaux: dict[str, uuid.UUID] = {}
    for ordre, (code, nom) in enumerate(BUREAUX_DE_BORDEAUX):
        bureaux[code] = _identifiant(
            connexion,
            """
            INSERT INTO office (entity_id, code, name, display_order)
            VALUES (:entite, :code, :nom, :ordre)
            ON CONFLICT (entity_id, code) WHERE archived_at IS NULL DO UPDATE
              SET name=EXCLUDED.name, display_order=EXCLUDED.display_order, updated_at=now()
            RETURNING id
            """,
            {"entite": entite, "code": code, "nom": nom, "ordre": ordre},
        )
    return cercles, bureaux


def _poser_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    cercle: uuid.UUID | None,
    debut: dt.datetime,
    instant: dt.datetime,
) -> None:
    active = (
        connexion.execute(
            text(
                "SELECT id, circle_id FROM circle_membership WHERE entity_membership_id=:membre "
                "AND membership_type='principal' AND ends_at IS NULL"
            ),
            {"membre": appartenance},
        )
        .mappings()
        .one_or_none()
    )
    if active is not None and (cercle is None or uuid.UUID(str(active["circle_id"])) != cercle):
        connexion.execute(
            text("UPDATE circle_membership SET ends_at=:instant, updated_at=:instant WHERE id=:id"),
            {"id": active["id"], "instant": instant},
        )
        active = None
        debut = instant
    if cercle is not None and active is None:
        connexion.execute(
            text(
                "INSERT INTO circle_membership "
                "(entity_id, entity_membership_id, circle_id, membership_type, starts_at) "
                "VALUES (:entite, :membre, :cercle, 'principal', :debut)"
            ),
            {"entite": entite, "membre": appartenance, "cercle": cercle, "debut": debut},
        )


def _poser_responsabilite(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_: str,
    acteur: uuid.UUID,
    instant: dt.datetime,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
) -> None:
    existe = connexion.execute(
        text(
            "SELECT 1 FROM framework_responsibility_assignment WHERE entity_id=:entite "
            "AND person_id=:personne AND responsibility_type=:type "
            "AND circle_id IS NOT DISTINCT FROM :cercle "
            "AND office_id IS NOT DISTINCT FROM :bureau AND ends_at IS NULL"
        ),
        {
            "entite": entite,
            "personne": personne,
            "type": type_,
            "cercle": cercle,
            "bureau": bureau,
        },
    ).first()
    if existe is None:
        connexion.execute(
            text(
                "INSERT INTO framework_responsibility_assignment "
                "(entity_id, person_id, responsibility_type, circle_id, office_id, "
                " assigned_by_person_id, assignment_reason, starts_at) "
                "VALUES (:entite, :personne, :type, :cercle, :bureau, :acteur, "
                " 'Provisionnement Beta Bordeaux', :instant)"
            ),
            {
                "entite": entite,
                "personne": personne,
                "type": type_,
                "cercle": cercle,
                "bureau": bureau,
                "acteur": acteur,
                "instant": instant,
            },
        )


def _poser_configuration(connexion: Connection, *, entite: uuid.UUID, instant: dt.datetime) -> None:
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, active, starts_at) "
            "SELECT CAST(:domaine AS varchar(255)), :entite, true, :instant WHERE NOT EXISTS ("
            "SELECT 1 FROM allowed_email_domain "
            "WHERE domain=CAST(:domaine AS varchar(255)) AND entity_id=:entite "
            "AND active AND ends_at IS NULL)"
        ),
        {"domaine": DOMAINE_EXALT, "entite": entite, "instant": instant},
    )
    connexion.execute(
        text(
            "INSERT INTO entity_setting (entity_id, key, value) "
            "VALUES (:entite, 'beta.presentation_responsibilities', CAST(:valeur AS jsonb)) "
            "ON CONFLICT (entity_id, key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()"
        ),
        {
            "entite": entite,
            "valeur": __import__("json").dumps(RESPONSABILITES_DE_PRESENTATION, ensure_ascii=False),
        },
    )
    connexion.execute(
        text(
            "INSERT INTO entity_setting (entity_id, key, value) "
            "VALUES (:entite, 'beta.direction_emails', CAST(:valeur AS jsonb)) "
            "ON CONFLICT (entity_id, key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()"
        ),
        {
            "entite": entite,
            "valeur": __import__("json").dumps(
                [
                    "julie.dumas@exalt-company.com",
                    "omar.lahjomri@exalt-company.com",
                    "mathea.dhalluin@exalt-company.com",
                ]
            ),
        },
    )


def _provisionner_l_accueil_bordeaux(
    connexion: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, instant: dt.datetime
) -> None:
    page = _identifiant(
        connexion,
        """
        INSERT INTO content_page
          (entity_id, page_type, title, slug, state, published_at,
           created_by_person_id, updated_by_person_id)
        VALUES (:entite, 'HOME', 'eXalt Bordeaux', 'presentation', 'published', :instant,
                :acteur, :acteur)
        ON CONFLICT (entity_id, page_type, slug) WHERE archived_at IS NULL DO UPDATE
          SET title=EXCLUDED.title, state='published',
              published_at=COALESCE(content_page.published_at, EXCLUDED.published_at),
              updated_at=:instant, updated_by_person_id=:acteur
        RETURNING id
        """,
        {"entite": entite, "acteur": acteur, "instant": instant},
    )
    bloc = connexion.execute(
        text(
            "SELECT id FROM content_block WHERE content_page_id=:page "
            "AND archived_at IS NULL ORDER BY display_order, id LIMIT 1"
        ),
        {"page": page},
    ).scalar_one_or_none()
    contenu = __import__("json").dumps({"texte": PRESENTATION_DE_BORDEAUX}, ensure_ascii=False)
    if bloc is None:
        connexion.execute(
            text(
                "INSERT INTO content_block "
                "(entity_id, content_page_id, block_type, display_order, payload_json, "
                "created_by_person_id, updated_by_person_id) "
                "VALUES (:entite, :page, 'RICH_TEXT', 0, CAST(:contenu AS jsonb), :acteur, :acteur)"
            ),
            {"entite": entite, "page": page, "contenu": contenu, "acteur": acteur},
        )
    else:
        connexion.execute(
            text(
                "UPDATE content_block SET block_type='RICH_TEXT', display_order=0, "
                "payload_json=CAST(:contenu AS jsonb), updated_at=:instant, "
                "updated_by_person_id=:acteur WHERE id=:bloc"
            ),
            {"bloc": bloc, "contenu": contenu, "instant": instant, "acteur": acteur},
        )

    for titre, description, debut, fin, lieu in EVENEMENTS_DE_DEMONSTRATION:
        evenement = connexion.execute(
            text(
                "SELECT id FROM event WHERE entity_id=:entite AND title=:titre "
                "AND archived_at IS NULL ORDER BY id LIMIT 1"
            ),
            {"entite": entite, "titre": titre},
        ).scalar_one_or_none()
        donnees = {
            "entite": entite,
            "titre": titre,
            "description": description,
            "debut": debut,
            "fin": fin,
            "lieu": lieu,
            "acteur": acteur,
            "instant": instant,
        }
        if evenement is None:
            connexion.execute(
                text(
                    "INSERT INTO event (entity_id, title, description, starts_at, ends_at, "
                    "location_text, state, created_by_person_id, updated_by_person_id) "
                    "VALUES (:entite, :titre, :description, :debut, :fin, :lieu, 'published', "
                    ":acteur, :acteur)"
                ),
                donnees,
            )
        else:
            connexion.execute(
                text(
                    "UPDATE event SET description=:description, starts_at=:debut, ends_at=:fin, "
                    "location_text=:lieu, state='published', updated_at=:instant, "
                    "updated_by_person_id=:acteur WHERE id=:evenement"
                ),
                {**donnees, "evenement": evenement},
            )


def _provisionner_le_parcours_bordeaux(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    personne: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> int:
    """Publier le modèle Bordeaux et l'affecter au profil de démonstration.

    Le provisionnement est rejouable : une version n'est créée que si sa
    composition diffère, et une instance n'est affectée qu'en l'absence de
    parcours actif. La date RH de Jonathan reste intacte ; seule la date de
    référence de cette instance de démonstration est ancrée à aujourd'hui.
    """
    from app.onboarding.catalogue import creer_une_tache_de_reference
    from app.onboarding.cycle_de_vie import publier_une_version
    from app.onboarding.gabarits import (
        NouvelleTacheDeVersion,
        creer_un_modele,
        creer_une_version,
        definir_les_taches_de_la_version,
        lire_un_modele,
    )
    from app.onboarding.instances import Appartenance, affecter_un_parcours

    references: dict[str, uuid.UUID] = {}
    for tache in TACHES_DU_PARCOURS_BORDEAUX:
        existante = connexion.execute(
            text(
                "SELECT id FROM onboarding_task_reference "
                "WHERE entity_id=:entite AND code=:code AND archived_at IS NULL"
            ),
            {"entite": entite, "code": tache.code},
        ).scalar_one_or_none()
        if existante is None:
            creee = creer_une_tache_de_reference(
                connexion,
                entite=entite,
                code=tache.code,
                title=tache.titre,
                description=tache.description,
                category=tache.categorie,
                acteur=acteur,
                instant=instant,
            )
            references[tache.code] = creee.id
        else:
            reference = uuid.UUID(str(existante))
            references[tache.code] = reference
            connexion.execute(
                text(
                    "UPDATE onboarding_task_reference SET title=:titre, "
                    "description=:description, category=:categorie, active=true, "
                    "updated_at=:instant WHERE id=:id"
                ),
                {
                    "id": reference,
                    "titre": tache.titre,
                    "description": tache.description,
                    "categorie": tache.categorie,
                    "instant": instant,
                },
            )

    modele_id_brut = connexion.execute(
        text(
            "SELECT id FROM onboarding_template WHERE entity_id=:entite AND name=:nom "
            "AND target_status='intercontract' AND scope_type='ENTITY' "
            "AND archived_at IS NULL ORDER BY created_at LIMIT 1"
        ),
        {"entite": entite, "nom": NOM_DU_MODELE_BORDEAUX},
    ).scalar_one_or_none()
    if modele_id_brut is None:
        modele = creer_un_modele(
            connexion,
            entite=entite,
            name=NOM_DU_MODELE_BORDEAUX,
            target_status="intercontract",
            scope_type="ENTITY",
            scope_person_id=None,
            scope_circle_id=None,
            acteur=acteur,
            instant=instant,
        )
    else:
        modele_id = uuid.UUID(str(modele_id_brut))
        modele_lu = lire_un_modele(connexion, entite=entite, modele=modele_id)
        if modele_lu is None:  # garde défensive : la requête ci-dessus fixe déjà l'entité
            raise RuntimeError("le modèle Bordeaux est devenu inaccessible")
        modele = modele_lu
    connexion.execute(
        text("UPDATE onboarding_template SET state='active', updated_at=:instant WHERE id=:id"),
        {"id": modele.id, "instant": instant},
    )

    version_publiee = connexion.execute(
        text(
            "SELECT id FROM onboarding_template_version "
            "WHERE template_id=:modele AND state='published' "
            "ORDER BY version_number DESC LIMIT 1"
        ),
        {"modele": modele.id},
    ).scalar_one_or_none()
    signature_attendue = tuple(
        (references[t.code], t.obligatoire, t.echeance_jours, None, None)
        for t in TACHES_DU_PARCOURS_BORDEAUX
    )
    signature_existante: tuple[tuple[object, ...], ...] = ()
    if version_publiee is not None:
        signature_existante = tuple(
            (
                uuid.UUID(str(ligne[0])),
                bool(ligne[1]),
                int(ligne[2]),
                ligne[3],
                ligne[4],
            )
            for ligne in connexion.execute(
                text(
                    "SELECT task_reference_id, required, due_offset_days, title_override, "
                    "description_override FROM onboarding_template_task "
                    "WHERE template_version_id=:version AND archived_at IS NULL "
                    "ORDER BY display_order"
                ),
                {"version": version_publiee},
            )
        )
    if signature_existante != signature_attendue:
        version = creer_une_version(
            connexion,
            modele=modele.id,
            entite_du_modele=entite,
            change_summary="Parcours Beta Bordeaux inspiré du prototype Intercontrat",
            acteur=acteur,
            instant=instant,
        )
        definir_les_taches_de_la_version(
            connexion,
            modele=modele,
            version=version,
            taches=tuple(
                NouvelleTacheDeVersion(
                    task_reference_id=references[tache.code],
                    required=tache.obligatoire,
                    due_offset_days=tache.echeance_jours,
                    title_override=None,
                    description_override=None,
                )
                for tache in TACHES_DU_PARCOURS_BORDEAUX
            ),
            acteur=acteur,
            instant=instant,
        )
        publier_une_version(
            connexion,
            version=version.id,
            entite_du_modele=entite,
            acteur=acteur,
            instant=instant,
        )

    connexion.execute(
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, state) "
            "VALUES (:entite, :appartenance, 'draft') "
            "ON CONFLICT (entity_membership_id) DO NOTHING"
        ),
        {"entite": entite, "appartenance": appartenance},
    )
    statut_actif = connexion.execute(
        text(
            "SELECT status FROM professional_status_assignment "
            "WHERE entity_id=:entite AND entity_membership_id=:appartenance "
            "AND archived_at IS NULL AND period @> :instant"
        ),
        {"entite": entite, "appartenance": appartenance, "instant": instant},
    ).scalar_one_or_none()
    if statut_actif is None:
        connexion.execute(
            text(
                "INSERT INTO professional_status_assignment "
                "(entity_id, entity_membership_id, status, reason, starts_at) "
                "VALUES (:entite, :appartenance, 'intercontract', :raison, :instant)"
            ),
            {
                "entite": entite,
                "appartenance": appartenance,
                "raison": "Démonstration Beta Bordeaux",
                "instant": instant,
            },
        )
        statut_actif = "intercontract"
    if statut_actif != "intercontract":
        return 0

    parcours_actif = connexion.execute(
        text(
            "SELECT 1 FROM onboarding_instance WHERE entity_id=:entite "
            "AND entity_membership_id=:appartenance AND state='active'"
        ),
        {"entite": entite, "appartenance": appartenance},
    ).first()
    if parcours_actif is not None:
        return 0
    affecter_un_parcours(
        connexion,
        entite=entite,
        appartenance=appartenance,
        cible=Appartenance(person_id=personne, arrival_date=instant.date()),
        acteur=acteur,
        instant=instant,
        motif="Démonstration Beta Bordeaux",
    )
    return 1


def _cle_nom(valeur: str) -> str:
    valeur = "".join(
        c for c in unicodedata.normalize("NFKD", valeur) if not unicodedata.combining(c)
    ).lower()
    return " ".join(re.findall(r"[a-z0-9]+", valeur))


def _photos_par_courriel(
    dossier: pathlib.Path, population: PopulationBordeaux
) -> tuple[dict[str, pathlib.Path], list[str]]:
    personnes = {_cle_nom(f"{e.prenom} {e.nom}"): e.courriel for e in population.employes}
    # Quelques noms ont evolue entre la prise de vue et l'extraction RH. Les
    # aliases restent explicites : aucune correspondance approximative ne doit
    # attribuer la photo d'un homonyme au mauvais profil.
    personnes.update(
        {
            "jeremy mear": "jeremie.mear@exalt-company.com",
            "mohammed ben thaier": "mohammed-sadeq.ben-thaier@exalt-company.com",
            "thuy y thanh le": "thuy-y-thanh.le@exalt-company.com",
            "y thanh le": "thuy-y-thanh.le@exalt-company.com",
            "yasmine sesanga": "yasmine.sesanga-morelet@exalt-company.com",
        }
    )
    resultat: dict[str, pathlib.Path] = {}
    avertissements: list[str] = []
    formats = {".jpg", ".jpeg", ".png", ".webp"}
    for chemin in sorted(dossier.iterdir()):
        if not chemin.is_file() or chemin.suffix.lower() not in formats:
            continue
        titre = re.sub(r"^\d+\s*-\s*", "", chemin.stem)
        titre = re.split(
            r"\s*-\s*(?=(?:cercle|p[oô]le|framework|direct(?:eur|rice)?|les|associ[eé]|en)\b)",
            titre,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        courriel = personnes.get(_cle_nom(titre))
        if courriel is None:
            continue
        if courriel in resultat:
            avertissements.append(
                f"plusieurs photos pour {courriel}, {resultat[courriel].name} conservee"
            )
            continue
        resultat[courriel] = chemin
    return resultat, avertissements


def _installer_les_photos(
    moteur: Engine,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    dossier: pathlib.Path,
    population: PopulationBordeaux,
    instant: dt.datetime,
) -> tuple[int, int, list[str]]:
    from app.media.autorisation import accorder_l_autorisation_photo
    from app.media.depot import deposer_une_photo
    from app.media.traitement import generer_les_variantes_depuis_la_charge

    photos, avertissements = _photos_par_courriel(dossier, population)
    installees = 0
    for courriel, chemin in photos.items():
        try:
            with moteur.begin() as connexion:
                cible = connexion.execute(
                    text(
                        "SELECT p.id FROM person p JOIN entity_membership em ON em.person_id=p.id "
                        "WHERE p.email_normalized=:email AND em.entity_id=:entite LIMIT 1"
                    ),
                    {"email": courriel, "entite": entite},
                ).scalar_one()
                deja = connexion.execute(
                    text(
                        "SELECT 1 FROM photo_authorization pa "
                        "JOIN media_asset ma ON ma.id=pa.media_asset_id "
                        "WHERE pa.person_id=:personne AND pa.withdrawn_at IS NULL "
                        "AND ma.entity_id=:entite "
                        "AND ma.state='ready' LIMIT 1"
                    ),
                    {"personne": cible, "entite": entite},
                ).first()
                if deja is not None:
                    continue
                contenu = chemin.read_bytes()
                mime = mimetypes.guess_type(chemin.name)[0] or "application/octet-stream"
                media = deposer_une_photo(
                    connexion,
                    parametres,
                    entite=entite,
                    acteur=acteur,
                    nom_de_fichier=chemin.name,
                    content_type=mime,
                    contenu=contenu,
                    instant=instant,
                )
                generer_les_variantes_depuis_la_charge(
                    connexion,
                    {"media_asset_id": str(media.id)},
                    instant=instant,
                    parametres=parametres,
                )
                etat = connexion.execute(
                    text("SELECT state FROM media_asset WHERE id=:id"), {"id": media.id}
                ).scalar_one()
                if etat != "ready":
                    avertissements.append(f"photo rejetee pour {courriel}: {chemin.name}")
                    continue
                accorder_l_autorisation_photo(
                    connexion,
                    entite=entite,
                    person_id=uuid.UUID(str(cible)),
                    media_asset_id=media.id,
                    source="migration",
                    acteur=acteur,
                    instant=instant,
                )
                installees += 1
        # Une photo invalide ne doit pas bloquer les 123 autres profils.
        except Exception as erreur:
            avertissements.append(
                f"photo ignoree pour {courriel} ({chemin.name}) : {type(erreur).__name__}"
            )
    return installees, len(population.employes) - installees, avertissements


def provisionner_bordeaux(
    moteur: Engine,
    population: PopulationBordeaux,
    *,
    parametres: Parametres | None = None,
    dossier_photos: pathlib.Path | None = None,
    instant: dt.datetime | None = None,
) -> RapportDeProvisionnement:
    maintenant = instant or dt.datetime.now(dt.UTC)
    personnes: dict[str, uuid.UUID] = {}
    appartenances: dict[str, uuid.UUID] = {}
    parcours_affectes = 0
    with moteur.begin() as connexion:
        entite = _entite(connexion, maintenant)
        cercles, bureaux = _referentiels(connexion, entite=entite)
        _poser_configuration(connexion, entite=entite, instant=maintenant)
        for employe in population.employes:
            personne = _personne(connexion, employe=employe)
            personnes[employe.courriel] = personne
            membre = _appartenance(
                connexion,
                entite=entite,
                personne=personne,
                date_d_arrivee=employe.date_d_arrivee,
                instant=maintenant,
            )
            appartenances[employe.courriel] = membre
            debut_date = employe.date_d_arrivee or maintenant.date()
            debut = dt.datetime.combine(debut_date, dt.time(), tzinfo=dt.UTC)
            _poser_cercle(
                connexion,
                entite=entite,
                appartenance=membre,
                cercle=cercles.get(employe.cercle or ""),
                debut=debut,
                instant=maintenant,
            )

        acteur = personnes["tess.gourlet@exalt-company.com"]
        _provisionner_l_accueil_bordeaux(
            connexion, entite=entite, acteur=acteur, instant=maintenant
        )
        for employe in population.employes:
            if employe.est_dsm:
                _poser_responsabilite(
                    connexion,
                    entite=entite,
                    personne=personnes[employe.courriel],
                    type_="DSM",
                    acteur=acteur,
                    instant=maintenant,
                )
            if employe.est_esm:
                _poser_responsabilite(
                    connexion,
                    entite=entite,
                    personne=personnes[employe.courriel],
                    type_="ESM",
                    acteur=acteur,
                    instant=maintenant,
                )
        for code, courriel in BOOSTERS_PAR_CERCLE.items():
            _poser_responsabilite(
                connexion,
                entite=entite,
                personne=personnes[courriel],
                type_="BOOSTER",
                cercle=cercles[code],
                acteur=acteur,
                instant=maintenant,
            )
        for code, titulaires in RESPONSABLES_PAR_BUREAU.items():
            for courriel in titulaires:
                _poser_responsabilite(
                    connexion,
                    entite=entite,
                    personne=personnes[courriel],
                    type_="OFFICE_MANAGER",
                    bureau=bureaux[code],
                    acteur=acteur,
                    instant=maintenant,
                )
        courriel_demo = COURRIEL_DU_NOUVEL_ARRIVANT_DE_DEMONSTRATION
        if courriel_demo in personnes:
            parcours_affectes = _provisionner_le_parcours_bordeaux(
                connexion,
                entite=entite,
                appartenance=appartenances[courriel_demo],
                personne=personnes[courriel_demo],
                acteur=acteur,
                instant=maintenant,
            )

    photos_installees = 0
    photos_ignorees = len(population.employes)
    avertissements = list(population.avertissements)
    if dossier_photos is not None:
        if parametres is None:
            raise ValueError("les parametres de stockage sont requis pour installer les photos")
        poses, ignorees, alertes = _installer_les_photos(
            moteur,
            parametres,
            entite=entite,
            acteur=personnes["tess.gourlet@exalt-company.com"],
            dossier=dossier_photos,
            population=population,
            instant=maintenant,
        )
        photos_installees, photos_ignorees = poses, ignorees
        avertissements.extend(alertes)
    return RapportDeProvisionnement(
        employes=len(population.employes),
        cercles=len(cercles),
        bureaux=len(bureaux),
        photos_installees=photos_installees,
        photos_ignorees=photos_ignorees,
        taches_onboarding=len(TACHES_DU_PARCOURS_BORDEAUX),
        parcours_affectes=parcours_affectes,
        avertissements=tuple(avertissements),
    )
