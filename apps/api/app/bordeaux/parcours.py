"""Contenu du parcours de démonstration eXalt Bordeaux.

Les libellés proviennent du prototype historique. Les codes, eux, sont des
identifiants fonctionnels stables : ils ne reprennent volontairement pas la
numérotation ``ic_*`` du prototype afin de permettre une future réutilisation
dans d'autres modèles.
"""

from __future__ import annotations

import dataclasses
from typing import Final

COURRIEL_DU_NOUVEL_ARRIVANT_DE_DEMONSTRATION: Final = "jonathan.dupau@exalt-company.com"
NOM_DU_MODELE_BORDEAUX: Final = "Parcours Bordeaux — nouvel arrivant"


@dataclasses.dataclass(frozen=True, slots=True)
class TacheDuParcoursBordeaux:
    code: str
    titre: str
    description: str
    categorie: str
    echeance_jours: int
    obligatoire: bool = True


def _tache(
    code: str,
    titre: str,
    phase: str,
    echeance_jours: int,
) -> TacheDuParcoursBordeaux:
    return TacheDuParcoursBordeaux(
        code=code,
        titre=titre,
        description=phase,
        categorie=phase,
        echeance_jours=echeance_jours,
    )


TACHES_DU_PARCOURS_BORDEAUX: Final = (
    _tache(
        "MAIL_BIENVENUE",
        "Recevoir le mail de bienvenue avec les infos d'arrivée",
        "Avant l'arrivée (M-1)",
        -30,
    ),
    _tache(
        "IDENTIFIANTS_IT",
        "Créer tes identifiants informatiques",
        "Avant l'arrivée (M-1)",
        -30,
    ),
    _tache(
        "LISTE_DIFFUSION",
        "Être ajouté à la liste de diffusion eXalt",
        "Avant l'arrivée (M-1)",
        -30,
    ),
    _tache(
        "BOOND_INTERCONTRAT",
        "Être saisi dans Boond en tant qu'intercontrat",
        "Avant l'arrivée (M-1)",
        -30,
    ),
    _tache(
        "INVITATION_J1",
        "Recevoir l'invitation Outlook (petit-déj + déjeuner J1)",
        "Avant l'arrivée (M-1)",
        -30,
    ),
    _tache(
        "J1_MATERIEL_GOODIES",
        "9h45 — Remise du matériel informatique + goodies",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_PETIT_DEJEUNER",
        "10h00 — Petit-déj d'accueil + jeu mieux se connaître + photos",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_WELCOME_SESSION",
        "11h00 — Welcome session & Kick Off Intercontrat",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_RENCONTRE_DSM",
        "12h00 — Rencontre avec ton DSM",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_DEJEUNER_EQUIPE",
        "13h00 — Déjeuner avec l'équipe",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_KIT_NOUVEL_ARRIVANT",
        "14h00 — Kit du nouvel arrivant (2h)",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J1_VIDEOS_FRAMEWORK",
        "16h00 — Visionnage des vidéos Framework",
        "Jour 1 — Accueil & découverte",
        0,
    ),
    _tache(
        "J2_PRESENTATION_DSM",
        "10h00 — Présentation DSM (1h)",
        "Jour 2 — Approfondissement",
        1,
    ),
    _tache(
        "J2_POSTURE_CONSULTANT",
        "10h30 — Formation posture consultant + charte",
        "Jour 2 — Approfondissement",
        1,
    ),
    _tache(
        "J2_ENGLISH_TEA_TIME",
        "11h00 — English Tea Time",
        "Jour 2 — Approfondissement",
        1,
    ),
    _tache(
        "J2_AUTOFORMATION",
        "14h00 — Autoformation (3h)",
        "Jour 2 — Approfondissement",
        1,
    ),
    _tache(
        "J3_AUTOFORMATION_DSM",
        "9h30 — Autoformation / Présentation DSM",
        "Jour 3 — Framework & Pitch",
        2,
    ),
    _tache(
        "J3_PRESENTATION_DSM",
        "10h00 — Présentation DSM",
        "Jour 3 — Framework & Pitch",
        2,
    ),
    _tache(
        "J3_ATELIER_PITCH",
        "11h00 — Atelier Pitch",
        "Jour 3 — Framework & Pitch",
        2,
    ),
    _tache(
        "J3_FRAMEWORK_ESM",
        "14h00 — Présentation Framework (ESM)",
        "Jour 3 — Framework & Pitch",
        2,
    ),
    _tache(
        "J3_AUTOFORMATION_DSM_APRES_MIDI",
        "15h00 — Autoformation / Présentation DSM",
        "Jour 3 — Framework & Pitch",
        2,
    ),
    _tache(
        "J5_BILAN_DSM",
        "15h00 — Bilan de fin de semaine avec ton DSM",
        "Jour 5 — Bilan de semaine",
        4,
    ),
    _tache(
        "J5_PREMIERES_IMPRESSIONS",
        "Partager tes premières impressions",
        "Jour 5 — Bilan de semaine",
        4,
    ),
    _tache(
        "J5_QUESTIONS_BESOINS",
        "Identifier tes questions et besoins",
        "Jour 5 — Bilan de semaine",
        4,
    ),
    _tache(
        "RENCONTRE_BOOSTER_CERCLE",
        "Rencontrer le Booster de ton cercle",
        "Dans le premier mois",
        30,
    ),
    _tache(
        "M1_AFTERWORK_DSM",
        "Afterwork — mieux travailler avec ton DSM",
        "Dans le premier mois",
        30,
    ),
    _tache(
        "M1_INITIATIVE",
        "Rejoindre une initiative existante",
        "Dans le premier mois",
        30,
    ),
    _tache(
        "ACADEMY_CERCLE",
        "Formation eXalt Academy — parcours métier de ton cercle",
        "Dans le premier mois",
        30,
    ),
)
