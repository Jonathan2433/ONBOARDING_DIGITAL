"""Les six taches planifiees du §20.3 — `T4`.

CHAQUE FONCTION REND LE NOMBRE D'ELEMENTS TRAITES, JAMAIS `None`

  C'est ce nombre que l'orchestrateur ecrit dans
  `scheduled_task_run.items_processed` — la preuve qu'une execution n'est pas
  un succes creux.

AUCUNE FONCTION N'OUVRE SA PROPRE TRANSACTION

  Meme discipline que tout le reste du depot (`app.audit.services`,
  `app.imports.execution`) : la connexion arrive deja ouverte, dans la
  savepoint que l'orchestrateur a posee pour cette tache.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.audit.modeles import SeveriteAlerte
from app.audit.services import enregistrer_un_evenement
from app.media.objets import ObjetNonSupprime, supprimer_l_objet
from app.support.traitement_alertes import lever_une_alerte

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

#  Delai de grace avant suppression definitive d'un media rejete, reste bloque
#  en traitement, ou orphelin — arbitrage explicite de Jonathan, 31/10/2026 :
#  meme regle pour les trois categories (§7 de la fiche).
DELAI_NETTOYAGE_MEDIAS = dt.timedelta(days=7)

#  Jeton d'identite depose par l'anonymisation — jamais vide, les colonnes
#  `first_name`/`last_name` de `person` etant `Text NOT NULL`.
JETON_ANONYMISATION = "Anonymisé"
#  Placeholder non vide pour `arrival_profile.short_intro`, dont la contrainte
#  `short_intro_requis_hors_brouillon` refuse une chaine vide hors brouillon.
PLACEHOLDER_INTRODUCTION = "Anonymisé"


# ===========================================================================
#  1. Expiration des liens et des sessions — hygiene, aucune regle de securite
#     nouvelle : `expires_at`/`absolute_expires_at`/l'inactivite a 7 jours
#     sont deja les bornes reelles depuis le LOT 3.
# ===========================================================================

_EXPIRER_LES_LIENS_MAGIQUES = text(
    "UPDATE magic_link_request SET invalidated_at = :instant, updated_at = :instant "
    "WHERE used_at IS NULL AND invalidated_at IS NULL AND expires_at <= :instant"
)

_EXPIRER_LES_SESSIONS = text(
    "UPDATE user_session SET revoked_at = :instant, updated_at = :instant "
    "WHERE revoked_at IS NULL AND ("
    "  absolute_expires_at <= :instant"
    "  OR last_activity_at <= :instant - INTERVAL '7 days'"
    ")"
)

_EXPIRER_LES_JETONS_DE_SERVICE = text(
    "UPDATE service_token SET revoked_at = :instant, updated_at = :instant "
    "WHERE revoked_at IS NULL AND expires_at <= :instant"
)


def expirer_les_liens_et_sessions(
    connexion: Connection, *, instant: dt.datetime, parametres: Parametres
) -> int:
    """Marquer invalides/revoques les liens, sessions et jetons deja perimes.

    N'ALTERE AUCUNE REGLE DE SECURITE : un lien/une session/un jeton deja
    perime est deja refuse a l'usage (LOT 3) — cette tache ne fait que rendre
    cet etat COHERENT dans les colonnes de fin de vie, pour que toute lecture
    administrative (listes, comptes) le voie sans recalculer.

    `parametres` n'est pas utilise — signature uniforme avec les cinq autres
    taches, voir `app.scheduling.orchestrateur`.
    """
    nombre = 0
    nombre += connexion.execute(_EXPIRER_LES_LIENS_MAGIQUES, {"instant": instant}).rowcount
    nombre += connexion.execute(_EXPIRER_LES_SESSIONS, {"instant": instant}).rowcount
    nombre += connexion.execute(_EXPIRER_LES_JETONS_DE_SERVICE, {"instant": instant}).rowcount
    return nombre


# ===========================================================================
#  2. Evenements passes — arbitrage explicite de Jonathan, 31/10/2026 : le
#     classement passe/a venir se calcule deja a la lecture (LOT 8), rien de
#     plus a construire. Cette tache confirme seulement son execution.
# ===========================================================================


def confirmer_les_evenements_passes(
    connexion: Connection,
    *,
    instant: dt.datetime,
    parametres: Parametres,
) -> int:
    """Rien a ecrire : §20.3 nomme cette tache, le LOT 8 fait deja le travail.

    Aucun argument n'est utilise — la fonction porte la MEME signature que les
    cinq autres, pour un dispatch uniforme dans
    `app.scheduling.orchestrateur.EXECUTER_LA_TACHE`.
    """
    return 0


# ===========================================================================
#  3. Anonymisation apres depart — modele §22.5, cahier §21.3.
# ===========================================================================

_PERSONNES_ELIGIBLES = text(
    "SELECT DISTINCT em.person_id "
    "FROM entity_membership em "
    "JOIN person p ON p.id = em.person_id "
    "WHERE em.membership_state = 'archived' "
    "  AND em.departure_date IS NOT NULL "
    "  AND em.departure_date <= (CAST(:instant AS date) - (:mois * INTERVAL '1 month')) "
    "  AND p.account_state <> 'anonymized'"
)

_ANONYMISER_LA_PERSONNE = text(
    "UPDATE person SET "
    "first_name = :jeton, last_name = :jeton, preferred_name = NULL, "
    "email = :email, email_normalized = :email, "
    "account_state = 'anonymized', anonymized_at = :instant, updated_at = :instant "
    "WHERE id = :personne AND account_state <> 'anonymized'"
)

_VIDER_LES_APPARTENANCES = text(
    "UPDATE entity_membership SET short_bio = NULL, fun_fact = NULL, updated_at = :instant "
    "WHERE person_id = :personne"
)

_VIDER_LES_FICHES_D_ARRIVEE = text(
    "UPDATE arrival_profile SET "
    "short_intro = CASE WHEN short_intro IS NOT NULL THEN :placeholder ELSE NULL END, "
    "fun_fact = NULL, photo_media_id = NULL, updated_at = :instant "
    "WHERE entity_membership_id IN ("
    "  SELECT id FROM entity_membership WHERE person_id = :personne"
    ")"
)

_RETIRER_LES_AUTORISATIONS_PHOTO = text(
    "UPDATE photo_authorization SET withdrawn_at = :instant, updated_at = :instant "
    "WHERE person_id = :personne AND withdrawn_at IS NULL"
)


def _email_anonymise(personne: uuid.UUID) -> str:
    """Une adresse synthetique, UNIQUE, qui satisfait les contraintes du §6.1.

    `email_normalized` exige : minuscules, aucune espace, un `@` qui n'est pas
    en premiere position. `personne.hex` est deja en minuscules.
    """
    return f"anonymise+{personne.hex}@anonymise.invalid"


def anonymiser_apres_depart(
    connexion: Connection, *, instant: dt.datetime, parametres: Parametres
) -> int:
    """Anonymiser toute personne partie depuis plus de `DEPARTURE_ARCHIVE_MONTHS`.

    **NE TOUCHE JAMAIS AUX MEDIAS DIRECTEMENT** : elle SEVRE les references
    (`arrival_profile.photo_media_id`, `photo_authorization.withdrawn_at`) —
    c'est `nettoyer_les_medias` (tache 6), executee au MEME cycle juste apres,
    qui constate l'absence de reference et engage le delai de 7 jours avant
    suppression definitive. Deux taches, une seule responsabilite chacune
    (§7.27 : ne pas dupliquer une suppression de media a deux endroits).

    **CE QUI N'EST PAS ANONYMISE, NOMME EXPLICITEMENT** : les responsabilites
    Framework, l'historique d'audit, et les instances d'onboarding — le §22.5
    dit « preserver uniquement les agregats necessaires », et ces tables
    portent deja la trace structurelle (compteurs, journal) sans qu'aucune
    n'expose plus l'identite de la personne une fois `person` anonymisee :
    elles referencent un `person_id` qui ne pointe plus vers un nom lisible.
    """
    lignes = connexion.execute(
        _PERSONNES_ELIGIBLES,
        {"instant": instant, "mois": parametres.DEPARTURE_ARCHIVE_MONTHS},
    ).all()
    nombre = 0
    for ligne in lignes:
        personne = ligne.person_id
        resultat = connexion.execute(
            _ANONYMISER_LA_PERSONNE,
            {
                "personne": personne,
                "jeton": JETON_ANONYMISATION,
                "email": _email_anonymise(personne),
                "instant": instant,
            },
        )
        if resultat.rowcount == 0:
            #  Deja anonymisee entre la lecture et l'ecriture (course rare) :
            #  pas une erreur, rien de plus a faire pour cette personne.
            continue
        connexion.execute(_VIDER_LES_APPARTENANCES, {"personne": personne, "instant": instant})
        connexion.execute(
            _VIDER_LES_FICHES_D_ARRIVEE,
            {"personne": personne, "instant": instant, "placeholder": PLACEHOLDER_INTRODUCTION},
        )
        connexion.execute(
            _RETIRER_LES_AUTORISATIONS_PHOTO, {"personne": personne, "instant": instant}
        )
        enregistrer_un_evenement(
            connexion,
            instant=instant,
            action_code="personne_anonymisee_automatiquement",
            resource_type="person",
            resource_reference=personne,
            summary="Anonymisation automatique apres depart (§22.5)",
        )
        nombre += 1
    return nombre


# ===========================================================================
#  4. Purge de l'audit a un an — `audit_event.retention_until`, deja calcule
#     a l'ecriture (LOT 10, `T2`). Cette tache ne recalcule rien : elle
#     applique la borne deja posee.
# ===========================================================================

_PURGER_L_AUDIT = text("DELETE FROM audit_event WHERE retention_until <= :instant")


def purger_l_audit(connexion: Connection, *, instant: dt.datetime, parametres: Parametres) -> int:
    """Supprimer les lignes `audit_event` dont la retention est echue.

    `parametres` n'est pas utilise : `retention_until` est deja calculee a
    l'ecriture (LOT 10, `T2`, `DUREE_DE_RETENTION`) — cette tache applique la
    borne deja posee, elle ne lit pas `AUDIT_RETENTION_DAYS` une seconde fois.
    """
    return connexion.execute(_PURGER_L_AUDIT, {"instant": instant}).rowcount


# ===========================================================================
#  5. Detection des jobs bloques — cahier §27.4, deux seuils distincts.
# ===========================================================================

_JOBS_EN_RETARD_DE_DEMARRAGE = text(
    "SELECT id, job_type FROM async_job "
    "WHERE state = 'queued' AND created_at <= :instant - (:minutes * INTERVAL '1 minute')"
)

_JOBS_SANS_PROGRESSION = text(
    "SELECT id, job_type FROM async_job "
    "WHERE state = 'running' "
    "  AND last_heartbeat_at IS NOT NULL "
    "  AND last_heartbeat_at <= :instant - (:minutes * INTERVAL '1 minute')"
)

_SOURCE_ALERTE_JOBS = "jobs_planifies"


def detecter_les_jobs_bloques(
    connexion: Connection, *, instant: dt.datetime, parametres: Parametres
) -> int:
    """Lever une alerte operationnelle pour chaque job en retard ou bloque.

    REUTILISE `lever_une_alerte` (LOT 10, `T13`) TEL QUEL : aucune seconde
    voie d'alerte n'est inventee ici. `lever_une_alerte` est deja un NO-OP si
    l'alerte de cette empreinte est deja `open` — rejouer cette tache toutes
    les cinq minutes ne cree donc jamais de doublon (§7.39 : la paire
    negatif/positif de ce temoin vit dans les tests du service lui-meme,
    reutilise plutot que reprouvee ici).
    """
    nombre = 0
    for ligne in connexion.execute(
        _JOBS_EN_RETARD_DE_DEMARRAGE,
        {"instant": instant, "minutes": parametres.WORKER_ABSENT_ALERT_MINUTES},
    ).all():
        lever_une_alerte(
            connexion,
            severity=SeveriteAlerte.ERROR.value,
            source=_SOURCE_ALERTE_JOBS,
            fingerprint=f"job-sans-worker:{ligne.id}",
            instant=instant,
        )
        nombre += 1
    for ligne in connexion.execute(
        _JOBS_SANS_PROGRESSION,
        {"instant": instant, "minutes": parametres.JOB_STALLED_ALERT_MINUTES},
    ).all():
        lever_une_alerte(
            connexion,
            severity=SeveriteAlerte.ERROR.value,
            source=_SOURCE_ALERTE_JOBS,
            fingerprint=f"job-bloque:{ligne.id}",
            instant=instant,
        )
        nombre += 1
    return nombre


# ===========================================================================
#  6. Nettoyage des medias — US007. Delai unique de 7 jours pour les trois
#     categories (arbitrage explicite de Jonathan, 31/10/2026).
# ===========================================================================

#  Categorie A : jamais devenus `ready` (rejetes, ou restes bloques en plein
#  depot) — la fenetre se compte depuis `created_at`, la seule date connue.
_MEDIAS_JAMAIS_PRETS_EXPIRES = text(
    "SELECT id, object_key FROM media_asset "
    "WHERE state IN ('pending', 'processing', 'rejected') "
    "  AND created_at <= :instant - :delai"
)

#  Categorie B, etape 1 : un media `ready` sans AUCUNE reference active devient
#  candidat — archive IMMEDIATEMENT (reutilise `archived_at`, deja consomme en
#  lecture par `app.media.photo`, jamais invente ici), pour dater le debut du
#  delai de grace.
_MEDIAS_READY_SANS_REFERENCE = text(
    "SELECT id FROM media_asset a "
    "WHERE a.state = 'ready' AND a.archived_at IS NULL "
    "  AND NOT EXISTS (SELECT 1 FROM event_media em WHERE em.media_asset_id = a.id) "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM photo_authorization pa "
    "    WHERE pa.media_asset_id = a.id AND pa.withdrawn_at IS NULL"
    "  ) "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM arrival_profile ap WHERE ap.photo_media_id = a.id"
    "  )"
)

_ARCHIVER_COMME_ORPHELIN = text(
    "UPDATE media_asset SET "
    "archived_at = :instant, archive_reason = :motif, updated_at = :instant "
    "WHERE id = :media"
)

#  Categorie B, etape 2 : un media deja archive-orphelin depuis plus de 7
#  jours, et TOUJOURS sans reference au moment de la suppression — la
#  verification est REFAITE, jamais supposee acquise depuis l'archivage.
_MEDIAS_ORPHELINS_EXPIRES = text(
    "SELECT id, object_key FROM media_asset a "
    "WHERE a.state = 'ready' "
    "  AND a.archived_at IS NOT NULL "
    "  AND a.archived_at <= :instant - :delai "
    "  AND NOT EXISTS (SELECT 1 FROM event_media em WHERE em.media_asset_id = a.id) "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM photo_authorization pa "
    "    WHERE pa.media_asset_id = a.id AND pa.withdrawn_at IS NULL"
    "  ) "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM arrival_profile ap WHERE ap.photo_media_id = a.id"
    "  )"
)

_VARIANTES_DU_MEDIA = text("SELECT id, object_key FROM media_variant WHERE media_asset_id = :media")

_SUPPRIMER_LES_VARIANTES = text("DELETE FROM media_variant WHERE media_asset_id = :media")

_MARQUER_SUPPRIME = text(
    "UPDATE media_asset SET state = 'deleted', updated_at = :instant WHERE id = :media"
)

_MOTIF_ORPHELIN = "orphelin : plus aucune reference active, detecte automatiquement"


def _supprimer_definitivement(
    connexion: Connection, parametres: Parametres, *, media: uuid.UUID, object_key: str
) -> None:
    """Supprimer les objets MinIO (actif + variantes), puis marquer la ligne.

    `ObjetNonSupprime` n'est PAS rattrapee ici : un media dont l'objet ne peut
    pas etre supprime ne doit pas etre marque `deleted`, sous peine de perdre
    la trace de son `object_key` pour une tentative future. L'echec remonte,
    l'orchestrateur le consigne dans `scheduled_task_run.error_message`, et le
    prochain cycle retentera CE media precisement (il reste visible aux deux
    requetes ci-dessus tant qu'il n'est pas `deleted`).
    """
    for variante in connexion.execute(_VARIANTES_DU_MEDIA, {"media": media}).all():
        supprimer_l_objet(parametres, variante.object_key)
    connexion.execute(_SUPPRIMER_LES_VARIANTES, {"media": media})
    supprimer_l_objet(parametres, object_key)


def nettoyer_les_medias(
    connexion: Connection, *, instant: dt.datetime, parametres: Parametres
) -> int:
    """Nettoyer les medias rejetes, temporaires et orphelins — US007."""
    nombre = 0

    for ligne in connexion.execute(
        _MEDIAS_JAMAIS_PRETS_EXPIRES, {"instant": instant, "delai": DELAI_NETTOYAGE_MEDIAS}
    ).all():
        _supprimer_definitivement(
            connexion, parametres, media=ligne.id, object_key=ligne.object_key
        )
        connexion.execute(_MARQUER_SUPPRIME, {"media": ligne.id, "instant": instant})
        enregistrer_un_evenement(
            connexion,
            instant=instant,
            action_code="media_nettoye_automatiquement",
            resource_type="media_asset",
            resource_reference=ligne.id,
            summary="Suppression automatique d'un media jamais devenu affichable",
        )
        nombre += 1

    for ligne in connexion.execute(_MEDIAS_READY_SANS_REFERENCE, {}).all():
        connexion.execute(
            _ARCHIVER_COMME_ORPHELIN,
            {"media": ligne.id, "instant": instant, "motif": _MOTIF_ORPHELIN},
        )
        nombre += 1

    for ligne in connexion.execute(
        _MEDIAS_ORPHELINS_EXPIRES, {"instant": instant, "delai": DELAI_NETTOYAGE_MEDIAS}
    ).all():
        _supprimer_definitivement(
            connexion, parametres, media=ligne.id, object_key=ligne.object_key
        )
        connexion.execute(_MARQUER_SUPPRIME, {"media": ligne.id, "instant": instant})
        enregistrer_un_evenement(
            connexion,
            instant=instant,
            action_code="media_nettoye_automatiquement",
            resource_type="media_asset",
            resource_reference=ligne.id,
            summary="Suppression automatique d'un media orphelin",
        )
        nombre += 1

    return nombre


#  Le vocabulaire fige, pour qu'un appel de `ObjetNonSupprime` au niveau de
#  l'orchestrateur ne soit jamais confondu avec une autre erreur -- voir
#  `app.scheduling.orchestrateur`.
__all__ = [
    "ObjetNonSupprime",
    "anonymiser_apres_depart",
    "confirmer_les_evenements_passes",
    "detecter_les_jobs_bloques",
    "expirer_les_liens_et_sessions",
    "nettoyer_les_medias",
    "purger_l_audit",
]
