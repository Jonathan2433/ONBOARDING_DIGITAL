"""Protection CSRF des ecritures — cahier §7.4 et §20.1.

LOT 3, sous-etape `T7`, story `MVP-L03-US005`.

DEUX BARRIERES, PARCE QUE LES ECRITURES NE SONT PAS TOUTES DANS LA MEME SITUATION

  **Trois ecritures precedent toute session** : demander un lien, le consommer,
  se connecter en administrateur. Un jeton anti-CSRF suppose une session pour le
  delivrer -- elles ne peuvent donc pas en exiger un.

      barriere 1   l'en-tete `Origin`, sur TOUTES les ecritures
      barriere 2   un jeton, sur les ecritures qui ont une session

  La premiere suffit aux trois routes amont, et double la seconde ailleurs. Un
  navigateur pose `Origin` **lui-meme** sur toute requete non sûre, et **aucun
  script ne peut le falsifier** : c'est ce qui la rend efficace la ou un jeton
  est impossible.

  **RESIDUEL NOMME** : un appel hors navigateur -- `curl`, un script -- n'envoie
  pas d'`Origin`, et passe. C'est normal et non un trou : le CSRF est une attaque
  qui emploie le navigateur d'une victime, et un attaquant qui appelle l'API
  directement n'usurpe l'identite de personne. Ce qui protege ce cas est
  l'authentification, non le CSRF.

POURQUOI `SameSite=lax` NE SUFFIT PAS, ET C'EST LE §7.4 QUI LE DIT

  Le cahier §7.4 enumere « cookie `HttpOnly`, `Secure` et `SameSite` » **ET**
  « protection CSRF » dans la meme liste : les deux, pas l'un ou l'autre.

  `lax` bloque bien l'envoi du cookie sur une soumission de formulaire croisee en
  `POST`. Il le laisse passer sur une **navigation de haut niveau**, et il ne
  protege pas d'un sous-domaine compromis -- `SameSite` raisonne par SITE, non
  par origine. La verification d'`Origin`, elle, compare l'ORIGINE exacte.

LE JETON EST DERIVE DE LA SESSION, IL N'EST PAS STOCKE

  `HMAC(APP_SECRET_KEY, empreinte de la session)`. Trois consequences, et la
  troisieme est le motif :

    - **rien de nouveau en base** : le modele ne declare aucune table de jeton
      CSRF, et en inventer une serait ce que §6.5 interdit ;
    - **il est verifiable sans etat** : aucune lecture, aucune ecriture ;
    - **un jeton vole ne sert a rien sans le cookie**. C'est le patron du
      double envoi, et sa liaison a la session est ce qui le rend solide : un
      jeton d'une autre session ne correspond pas.

  Le jeton n'est **pas** dans un cookie `HttpOnly` -- il doit etre lisible par le
  frontend, c'est son objet. Il est rendu dans le CORPS des reponses de session,
  et c'est sans danger : il n'ouvre aucun acces a lui seul.
"""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlparse

#  L'en-tete que le frontend renvoie. `X-CSRF-Token` est le nom d'usage ; le
#  declarer ici en fait la seule source, lue par le contrat partage et par les
#  tests.
EN_TETE_JETON = "X-CSRF-Token"

#  Les methodes qui MODIFIENT. `GET`, `HEAD` et `OPTIONS` sont sûres au sens de
#  la norme HTTP : elles ne doivent rien changer, et exiger une protection sur
#  elles rendrait toute page inaccessible.
#
#  **`GET …/auth/session` ECRIT POURTANT** -- elle rafraichit `last_activity_at`.
#  Voir `routes.py` : c'est un residuel nomme, pas un oubli.
METHODES_A_PROTEGER = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfRefuse(Exception):
    """La requete ne satisfait pas la protection CSRF.

    Porte un motif INTERNE, destine a l'audit et au journal. **Il ne sort pas de
    l'API** : la reponse est generique, comme partout dans ce lot.
    """

    def __init__(self, motif: str) -> None:
        self.motif = motif
        super().__init__(motif)


MOTIF_ORIGINE_ABSENTE = "origine_absente"
MOTIF_ORIGINE_ETRANGERE = "origine_etrangere"
MOTIF_JETON_ABSENT = "jeton_csrf_absent"
MOTIF_JETON_INVALIDE = "jeton_csrf_invalide"

MOTIFS_CSRF = (
    MOTIF_ORIGINE_ABSENTE,
    MOTIF_ORIGINE_ETRANGERE,
    MOTIF_JETON_ABSENT,
    MOTIF_JETON_INVALIDE,
)


def origine_attendue(base_publique: str) -> str:
    """L'origine servie, reduite a `schema://hote[:port]`.

    `PUBLIC_BASE_URL` peut porter un chemin ou une barre finale ; un navigateur
    n'envoie jamais qu'une origine. Les comparer telles quelles echouerait sur un
    detail de configuration -- et `T3` a montre que cette variable n'avait jamais
    ete exercee.
    """
    analysee = urlparse(base_publique)
    if not analysee.scheme or not analysee.netloc:
        return ""
    return f"{analysee.scheme}://{analysee.netloc}"


def controler_l_origine(*, origine: str | None, attendue: str) -> None:
    """Refuser une ecriture dont l'origine n'est pas la notre.

    Args:
        origine: l'en-tete `Origin` de la requete, ou `None`.
        attendue: le retour de `origine_attendue`.

    Raises:
        CsrfRefuse: si l'origine est presente et etrangere.

    **UNE ORIGINE ABSENTE N'EST PAS REFUSEE, ET C'EST UN CHOIX DECLARE.** Un
    navigateur pose `Origin` sur toute requete non sûre ; son absence signale un
    appel hors navigateur, ou l'un des rares clients anciens qui l'omettent. La
    refuser casserait `curl`, les tests d'exploitation et les sondes -- et
    n'apporterait rien : le CSRF est une attaque de navigateur, et un appelant
    sans navigateur n'usurpe l'identite de personne.

    **Ce qui protege le cas d'un appel direct est l'AUTHENTIFICATION**, non le
    CSRF, et c'est pourquoi la seconde barriere -- le jeton lie a la session --
    existe pour les routes qui en ont une.
    """
    if origine is None or origine == "":
        return
    if not attendue:
        #  Sans origine attendue exploitable, on ne peut RIEN affirmer. Refuser
        #  serait plus sûr, mais rendrait l'API inutilisable sur une
        #  configuration incomplete sans dire pourquoi : le garde-fou de
        #  `PUBLIC_BASE_URL` est ailleurs, et c'est lui qui doit parler.
        return
    if origine.rstrip("/") != attendue:
        raise CsrfRefuse(MOTIF_ORIGINE_ETRANGERE)


def jeton_pour(empreinte_de_session: str, cle: str) -> str:
    """Le jeton anti-CSRF d'une session — `HMAC(cle, empreinte)`.

    **DERIVE, PAS STOCKE.** Aucune table, aucune lecture, aucune ecriture. Et il
    est lie a UNE session : presente sur une autre, il ne correspond pas.

    Args:
        empreinte_de_session: l'empreinte SHA-256 du jeton de session, **jamais
            le jeton lui-meme** -- un jeton de session ne doit pas servir
            d'entree a une valeur destinee au frontend.
        cle: `APP_SECRET_KEY`.
    """
    if not cle:
        message = (
            "jeton_pour exige une cle non vide : sans elle, un jeton CSRF serait "
            "calculable par quiconque"
        )
        raise ValueError(message)
    return hmac.new(
        cle.encode("utf-8"), empreinte_de_session.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def controler_le_jeton(*, presente: str | None, empreinte_de_session: str, cle: str) -> None:
    """Refuser une ecriture dont le jeton ne correspond pas a la session.

    Raises:
        CsrfRefuse: jeton absent, ou ne correspondant pas.

    **LA COMPARAISON EST A TEMPS CONSTANT.** Un `==` s'arreterait au premier
    caractere different, et sa duree renseignerait sur le nombre de caracteres
    corrects -- ce qui permet de reconstruire le jeton. Meme motif qu'en `T5`
    pour l'empreinte de mot de passe.
    """
    if not presente:
        raise CsrfRefuse(MOTIF_JETON_ABSENT)
    attendu = jeton_pour(empreinte_de_session, cle)
    if not hmac.compare_digest(presente, attendu):
        raise CsrfRefuse(MOTIF_JETON_INVALIDE)
