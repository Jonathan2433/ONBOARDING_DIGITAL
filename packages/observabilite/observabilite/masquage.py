"""Masquage des valeurs sensibles avant journalisation.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT — cahier des charges §28.2, litteral
    « Aucune donnee sensible, aucun secret, aucun jeton, aucun magic link
    complet, aucun CSV complet et aucun corps complet d'e-mail. »

DEUX BARRIERES, ET C'EST DELIBERE

    Par le NOM de la cle    Tout champ dont le nom evoque un secret est masque,
                            quelle que soit sa valeur. C'est la barriere la
                            plus fiable : elle ne depend pas de la forme de la
                            valeur.
    Par la FORME de la      Un jeton, une cle, une URL de connexion ou un
    valeur                  magic link est masque meme s'il apparait dans un
                            champ au nom anodin — par exemple au milieu d'un
                            message d'erreur.

    Aucune des deux ne suffit seule. La premiere laisse passer un secret
    recopie dans `message` ; la seconde laisse passer un secret dont la forme
    n'est pas reconnaissable.

TROISIEME BARRIERE : LA TRONCATURE
    Le §28.2 interdit « aucun CSV complet et aucun corps complet d'e-mail ».
    Aucun motif ne reconnait un CSV : la parade est une borne de longueur.
    Toute valeur trop longue est tronquee, ce qui rend structurellement
    impossible de journaliser un fichier ou un corps de message entier.

CE QUE CE MODULE NE PROMET PAS
    Il ne devine pas un secret qui serait a la fois dans un champ au nom
    anodin, sans forme reconnaissable, et court. Un tel cas releve de la
    revue de code, pas d'un filtre. Le filtre reduit la surface, il ne la
    supprime pas.
"""

from __future__ import annotations

import re
from typing import Any

MASQUE = "***masque***"

# Longueur maximale d'une valeur journalisee. Au-dela, la valeur est tronquee :
# c'est la seule parade generique contre le CSV complet et le corps d'e-mail
# complet du §28.2.
LONGUEUR_MAXIMALE_VALEUR = 512

# ---------------------------------------------------------------------------
#  LES JETONS QUE CE PROJET PRODUIT — LOT 3, sous-etape `T3`
# ---------------------------------------------------------------------------
#
#  POURQUOI CES CONSTANTES SONT ICI, ET NON DANS `apps/api`
#
#    Elles ont TROIS consommateurs : ce filtre, le code qui engendre les jetons
#    (`app.auth.jetons`), et la regle Gitleaks de `.gitleaks.toml`. Le filtre ne
#    peut pas importer `apps/api` -- c'est `apps/api` qui depend de ce paquet, et
#    l'inverse serait un cycle.
#
#    Les poser ici donne **une seule source** aux deux consommateurs Python, et
#    c'est exactement le motif de `DEC-466` : deux filtres de masquage finissent
#    par diverger, et le jour ou l'un oublie un motif la fuite est silencieuse.
#    Le troisieme consommateur est du TOML, qui n'importe rien : un controle
#    confronte donc sa regle a ces constantes plutot que de faire confiance a la
#    copie -- §7.27.
#
#  POURQUOI UN PREFIXE, ET C'EST UNE MESURE DE SECURITE
#
#    Un jeton purement aleatoire n'a aucune forme reconnaissable, et un detecteur
#    reduit a « une longue chaine base64 » serait une heuristique : il refuserait
#    du texte legitime, donc il apprendrait a passer outre (§7.25). Le prefixe
#    rend le detecteur EXACT -- c'est le motif du motif `gh[pousr]_` ci-dessous
#    pour les jetons GitHub.
#
#  LA FAMILLE EST RESERVEE ICI POUR QUE `T6` ET `T10` NE L'INVENTENT PAS CHACUNE
#  DE SON COTE :
#
#      `oml_`   magic link          -- LOT 3, `T3`
#      `oss_`   jeton de session    -- LOT 3, `T6`, story `US004`
#      `ost_`   jeton de service    -- LOT 3, `T10`, story `US007`
PREFIXE_MAGIC_LINK = "oml_"
PREFIXE_SESSION = "oss_"
PREFIXE_JETON_DE_SERVICE = "ost_"

PREFIXES_DE_JETON = (PREFIXE_MAGIC_LINK, PREFIXE_SESSION, PREFIXE_JETON_DE_SERVICE)

# Borne INFERIEURE de la part aleatoire. Les jetons produits en portent 43 --
# `secrets.token_urlsafe(32)` -- et le detecteur est volontairement plus permissif
# : cale sur 43 exactement, il cesserait de voir le jeton le jour ou la taille de
# l'alea changerait, et ce jour-la la fuite serait SILENCIEUSE.
LONGUEUR_MINIMALE_D_ALEA = 40

# Le motif est DERIVE des constantes ci-dessus, jamais recopie.
MOTIF_JETON_DU_PROJET = (
    r"\b(?:"
    + "|".join(re.escape(prefixe) for prefixe in PREFIXES_DE_JETON)
    + r")[A-Za-z0-9_-]{"
    + str(LONGUEUR_MINIMALE_D_ALEA)
    + r",}"
)

# --- Barriere 1 : le nom de la cle -------------------------------------------
#
# Recherche par sous-chaine, en minuscules, pour attraper aussi bien
# `password` que `POSTGRES_PASSWORD` ou `mot_de_passe`.
FRAGMENTS_DE_CLE_SENSIBLE = (
    "password",
    "passwd",
    "mot_de_passe",
    "secret",
    "token",
    "jeton",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "authorization",
    "auth",
    "cookie",
    "session",
    "magic",
    "credential",
    "identifiant_acces",
)

# --- Barriere 2 : la forme de la valeur --------------------------------------
MOTIFS_DE_VALEUR_SENSIBLE: tuple[re.Pattern[str], ...] = (
    # Cle privee au format PEM.
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    # Jeton GitHub.
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    # Cle d'acces AWS.
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Jeton JWT — trois segments encodes en base64url.
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"),
    # URL de connexion portant un mot de passe : postgresql://, redis://, amqp://...
    #
    # L'utilisateur est OPTIONNEL — `[^\s:/@]*` et non `+`. La premiere version
    # exigeait un nom d'utilisateur et laissait donc passer `redis://:motdepasse@`,
    # qui est EXACTEMENT le format produit par `Parametres.url_redis()` : le
    # secret le plus susceptible d'apparaitre dans ces journaux. Trou detecte par
    # le test `test_une_valeur_de_forme_sensible_est_masquee_meme_dans_un_champ_anodin`.
    re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]*:[^\s@]+@"),
    # En-tete Authorization complet.
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    # Magic link : une URL portant un parametre de jeton.
    re.compile(r"(?i)https?://\S*[?&](token|jeton|code|magic)=\S+"),
    # LES JETONS DE CE PROJET, par leur prefixe — LOT 3, `T3`.
    #
    # LE MOTIF D'URL CI-DESSUS NE SUFFISAIT PAS, ET C'EST LA LECON `T4-1`
    # REJOUEE. Il exige une URL complete : un jeton NU -- recopie dans un
    # message d'erreur, un argument de fonction, une trace -- passait a travers.
    # Or c'est la forme la plus probable dans ces journaux : `oml_...` sans son
    # URL. Un test enumere les formes que **ce projet** produit, pas des
    # exemples de documentation.
    re.compile(MOTIF_JETON_DU_PROJET),
)


def _valeur_est_sensible(texte: str) -> bool:
    return any(motif.search(texte) for motif in MOTIFS_DE_VALEUR_SENSIBLE)


def cle_est_sensible(cle: str) -> bool:
    """La cle evoque-t-elle un secret, quelle que soit sa valeur ?"""
    minuscule = cle.lower()
    return any(fragment in minuscule for fragment in FRAGMENTS_DE_CLE_SENSIBLE)


def masquer_texte(texte: str) -> str:
    """Masquer un texte s'il contient une valeur de forme sensible, puis le borner."""
    if _valeur_est_sensible(texte):
        return MASQUE
    if len(texte) > LONGUEUR_MAXIMALE_VALEUR:
        restant = len(texte) - LONGUEUR_MAXIMALE_VALEUR
        return f"{texte[:LONGUEUR_MAXIMALE_VALEUR]}…[{restant} caracteres tronques]"
    return texte


def masquer(valeur: Any, *, cle: str | None = None) -> Any:
    """Masquer recursivement une valeur destinee au journal.

    Les dictionnaires et les listes sont parcourus en profondeur : un secret
    niche dans un sous-objet est masque comme s'il etait au premier niveau.

    Args:
        valeur: la valeur a journaliser.
        cle: le nom du champ qui la porte, s'il est connu. Une cle sensible
            masque la valeur sans meme l'examiner.
    """
    if cle is not None and cle_est_sensible(cle):
        return MASQUE

    if isinstance(valeur, str):
        return masquer_texte(valeur)

    if isinstance(valeur, dict):
        return {
            str(sous_cle): masquer(sous_valeur, cle=str(sous_cle))
            for sous_cle, sous_valeur in valeur.items()
        }

    if isinstance(valeur, list | tuple):
        return [masquer(element) for element in valeur]

    # Les entiers, booleens et None ne portent pas de secret exploitable et
    # sont laisses tels quels : les masquer rendrait les journaux inutilisables.
    return valeur
