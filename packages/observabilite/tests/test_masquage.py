"""Le masquage des valeurs sensibles.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT — cahier §28.2, litteral
    « Aucune donnee sensible, aucun secret, aucun jeton, aucun magic link
    complet, aucun CSV complet et aucun corps complet d'e-mail. »

DISCIPLINE
    Chaque interdiction du §28.2 a un test qui la met en defaut, ET un temoin
    qui verifie que le filtre laisse passer une valeur anodine. Un filtre qui
    masque tout serait aussi inutile qu'un filtre qui ne masque rien : c'est
    seulement l'ensemble des deux tests qui prouve qu'il discrimine.
"""

from __future__ import annotations

import pytest

from observabilite.masquage import (
    LONGUEUR_MAXIMALE_VALEUR,
    MASQUE,
    cle_est_sensible,
    masquer,
)

# ============================================================================
#  Barriere 1 — le nom de la cle
# ============================================================================


@pytest.mark.parametrize(
    "cle",
    [
        "password",
        "POSTGRES_PASSWORD",
        "mot_de_passe",
        "APP_SECRET_KEY",
        "access_token",
        "jeton_de_session",
        "Authorization",
        "cookie",
        "magic_link",
        "aws_private_key",
        "credential_client",
    ],
)
def test_une_cle_sensible_masque_la_valeur_sans_l_examiner(cle: str) -> None:
    """La barriere la plus fiable : elle ne depend pas de la forme de la valeur."""
    assert cle_est_sensible(cle)
    assert masquer("valeur-parfaitement-anodine", cle=cle) == MASQUE


@pytest.mark.parametrize(
    "cle",
    ["route", "duree_ms", "resultat", "service", "environnement", "nombre_arguments"],
)
def test_une_cle_anodine_laisse_passer_la_valeur(cle: str) -> None:
    """Temoin de la barriere 1. Sans lui, un filtre qui masque tout passerait."""
    assert not cle_est_sensible(cle)
    assert masquer("GET /api/v1/", cle=cle) == "GET /api/v1/"


# ============================================================================
#  Barriere 2 — la forme de la valeur, dans un champ au nom anodin
# ============================================================================


@pytest.mark.parametrize(
    ("libelle", "valeur"),
    [
        ("cle privee PEM", "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."),
        ("jeton GitHub", "ghp_" + "A" * 36),
        ("cle AWS", "AKIA" + "B" * 16),
        ("jeton JWT", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abcdefgh"),
        ("URL PostgreSQL", "postgresql://onboarding:motdepasse@db:5432/onboarding_dev"),
        ("URL Redis", "redis://:motdepasse@redis:6379/0"),
        ("en-tete Bearer", "Authorization: Bearer abcdefghijklmnop123456"),
        (
            "magic link complet",
            "https://app.onboarding.localhost/connexion?token=abc123def456",
        ),
    ],
)
def test_une_valeur_de_forme_sensible_est_masquee_meme_dans_un_champ_anodin(
    libelle: str, valeur: str
) -> None:
    """Un secret recopie dans un message d'erreur ne doit pas sortir.

    C'est le cas que la barriere 1 ne couvre pas : la cle s'appelle `message`.
    """
    assert masquer(valeur, cle="message") == MASQUE, libelle


@pytest.mark.parametrize(
    "valeur",
    [
        "requete servie",
        "GET /api/v1/personnes/{identifiant}",
        "https://app.onboarding.localhost/accueil",
        "postgresql://db:5432/onboarding_dev",
        "job traite",
        "utilisateur introuvable",
    ],
)
def test_une_valeur_anodine_traverse_le_filtre(valeur: str) -> None:
    """Temoin de la barriere 2.

    La quatrieme valeur mérite attention : c'est une URL PostgreSQL **sans
    identifiants**. Elle doit passer, sinon le filtre serait inutilisable pour
    journaliser une cible de connexion.
    """
    assert masquer(valeur, cle="message") == valeur


# ============================================================================
#  Barriere 3 — la troncature : ni CSV complet, ni corps d'e-mail complet
# ============================================================================


def test_une_valeur_trop_longue_est_tronquee() -> None:
    """Le §28.2 interdit le CSV complet et le corps d'e-mail complet.

    Aucun motif ne reconnait un CSV : la borne de longueur est la seule parade
    generique. Elle rend structurellement impossible de journaliser un fichier
    entier.
    """
    csv = "nom,prenom,email\n" + "\n".join(
        f"Nom{i},Prenom{i},p{i}@exalt-company.com" for i in range(200)
    )
    assert len(csv) > LONGUEUR_MAXIMALE_VALEUR
    resultat = masquer(csv, cle="contenu")
    assert len(resultat) < len(csv)
    assert "caracteres tronques" in resultat


def test_une_valeur_courte_n_est_pas_tronquee() -> None:
    """Temoin de la barriere 3."""
    court = "nom,prenom\nDupont,Jean"
    assert masquer(court, cle="extrait") == court


# ============================================================================
#  Parcours en profondeur
# ============================================================================


def test_un_secret_niche_dans_un_sous_objet_est_masque() -> None:
    """Un dictionnaire imbrique ne doit pas etre un angle mort."""
    donnees = {
        "route": "POST /api/v1/imports",
        "connexion": {
            "hote": "db",
            "password": "MotDePasseReel",
            "options": {"token": "jeton-secret"},
        },
        "etapes": ["preparation", "postgresql://u:p@db/x"],
    }
    resultat = masquer(donnees)
    assert resultat["route"] == "POST /api/v1/imports"
    assert resultat["connexion"]["hote"] == "db"
    assert resultat["connexion"]["password"] == MASQUE
    assert resultat["connexion"]["options"]["token"] == MASQUE
    assert resultat["etapes"][0] == "preparation"
    assert resultat["etapes"][1] == MASQUE


def test_les_valeurs_non_textuelles_traversent_le_filtre() -> None:
    """Masquer les entiers rendrait les journaux inutilisables.

    `duree_ms`, `statut_http` et `nombre_arguments` sont des entiers : les
    masquer priverait le journal de tout interet de diagnostic.
    """
    donnees = {"duree_ms": 42, "statut_http": 200, "reussi": True, "motif": None}
    assert masquer(donnees) == donnees


def test_aucune_valeur_secrete_ne_survit_a_un_aller_retour_complet() -> None:
    """Controle d'ensemble, avec temoin.

    Toutes les valeurs sensibles disparaissent, toutes les valeurs utiles
    subsistent. Le second `assert` est indispensable : sans lui, un filtre qui
    renverrait `{}` passerait le test.
    """
    secrets = [
        "MotDePasseTresSecret",
        "ghp_" + "C" * 36,
        "redis://:motdepasse@redis:6379/0",
    ]
    donnees = {
        "route": "GET /health/ready",
        "duree_ms": 3,
        "password": secrets[0],
        "message": f"echec avec {secrets[1]}",
        "url": secrets[2],
    }
    rendu = repr(masquer(donnees))
    for secret in secrets:
        assert secret not in rendu
    assert "GET /health/ready" in rendu
