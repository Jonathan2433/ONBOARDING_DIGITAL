"""Fiches d'arrivee et onboarding — modele §12.1 et §13.

LOT 7, sous-etape `T1`. Huit tables, dont aucune n'existait — mesure du
25/09/2026 sur le schema reel, 32 tables `alembic_version` comprise.
"""

from app.onboarding.modeles import (
    ETATS_DU_MODELE,
    ETATS_FICHE_ARRIVEE,
    ETATS_INSTANCE,
    ETATS_TACHE_INSTANCE,
    PORTEES_DU_MODELE,
    TYPES_EVENEMENT_TACHE,
    ArrivalProfile,
    EtatDuModele,
    EtatFicheArrivee,
    EtatInstance,
    EtatTacheInstance,
    OnboardingInstance,
    OnboardingInstanceTask,
    OnboardingTaskEvent,
    OnboardingTaskReference,
    OnboardingTemplate,
    OnboardingTemplateTask,
    OnboardingTemplateVersion,
    PorteeDuModele,
    TypeEvenementTache,
)

__all__ = [
    "ETATS_DU_MODELE",
    "ETATS_FICHE_ARRIVEE",
    "ETATS_INSTANCE",
    "ETATS_TACHE_INSTANCE",
    "PORTEES_DU_MODELE",
    "TYPES_EVENEMENT_TACHE",
    "ArrivalProfile",
    "EtatDuModele",
    "EtatFicheArrivee",
    "EtatInstance",
    "EtatTacheInstance",
    "OnboardingInstance",
    "OnboardingInstanceTask",
    "OnboardingTaskEvent",
    "OnboardingTaskReference",
    "OnboardingTemplate",
    "OnboardingTemplateTask",
    "OnboardingTemplateVersion",
    "PorteeDuModele",
    "TypeEvenementTache",
]
