"""Hachage et verification du mot de passe administrateur — modele §10.2.

LOT 3, sous-etape `T5`, story `MVP-L03-US003`.

FONDEMENT — cahier §7.3 : « mot de passe stocke de maniere securisee », et
« aucun mot de passe ne doit etre integre au code, present dans le frontend,
stocke en clair, ou enregistre dans les logs ». Modele §10.2 : `password_hash`,
`algorithm`, `parameters`, « aucun mot de passe brut ni historique reversible ».

POURQUOI SCRYPT, ET LE CHOIX EST TRACE

  **Aucun document du corpus ne nomme d'algorithme** -- c'est le §8 de la fiche du
  LOT 3 qui l'annonce comme decision a instruire, et elle a ete tranchee par
  Jonathan le 21/08/2026 (`DEC-526`).

  `hashlib.scrypt` est dans la BIBLIOTHEQUE STANDARD : aucune dependance ajoutee,
  et les images publiees ne changent pas. Mesure du 21/08/2026 **dans le
  conteneur** `python:3.12-slim` : `hasattr(hashlib, 'scrypt')` vaut `True`.

  **Residuel nomme, non masque** : les recommandations publiques placent argon2id
  en premier et scrypt en second. Le §10.2 exige `algorithm` et `parameters` **en
  colonnes** precisement pour qu'un changement reste possible sans casser les
  comptes existants -- et `verifier()` sait relire n'importe quel jeu de
  parametres deja stocke. Un passage a argon2id serait donc un rehachage a la
  prochaine connexion, non une migration destructive.

LES PARAMETRES SONT MESURES, PAS RECOPIES D'UN BILLET DE BLOG

  | N     | duree (conteneur) | memoire par calcul |
  |-------|-------------------|--------------------|
  | 2^15  |  ~65 ms           |  32 Mio            |
  | 2^16  | ~130 ms           |  64 Mio            |
  | 2^17  | ~260 ms           | 128 Mio            |

  **`N = 2^16` est retenu a cause de la MEMOIRE, pas de la duree.** Le service
  `api` a une limite de 1 024 Mio (`DEC-440`) : a 128 Mio par calcul, **huit
  connexions simultanees suffiraient a la saturer**, ce qui transformerait la page
  de connexion en levier de deni de service. A 64 Mio, il en faudrait seize, et la
  limitation de debit de `T8` couvrira ce residuel.

CE MODULE NE JOURNALISE RIEN, JAMAIS

  Pas un `logger`, pas un `print`, aucune exception portant une valeur. Un mot de
  passe qui traverse ce module ne doit laisser aucune trace ailleurs qu'en base,
  sous forme d'empreinte. C'est la seule facon de tenir le §7.3 : les barrieres de
  masquage de `packages/observabilite` sont la seconde ligne, pas la premiere.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any, Final

#  Le nom stocke dans `admin_password_credential.algorithm`. Il est LU a la
#  verification : c'est lui qui dira, le jour d'un changement, avec quel
#  algorithme une empreinte donnee a ete produite.
ALGORITHME: Final = "scrypt"

#  Les parametres, mesures ci-dessus. Ils sont stockes AVEC l'empreinte : les
#  relire depuis la base plutot que depuis ce fichier est ce qui permet de les
#  durcir sans invalider les comptes deja crees.
PARAMETRES_PAR_DEFAUT: Final[dict[str, int]] = {
    #  `n` doit etre une puissance de deux : scrypt le refuse sinon.
    "n": 2**16,
    "r": 8,
    "p": 1,
    #  16 octets de sel, tire par `secrets`. Un sel par empreinte : deux comptes
    #  portant le meme mot de passe ont des empreintes differentes, ce qui
    #  interdit de les rapprocher.
    "longueur_sel": 16,
    #  64 octets de sortie. Plus long que necessaire pour comparer, et sans coup :
    #  scrypt derive la longueur demandee a la fin.
    "longueur_cle": 64,
}

#  Borne de memoire passee a OpenSSL. scrypt consomme `128 * n * r` octets ; la
#  marge de 20 % evite un refus pour un depassement de quelques kilo-octets.
_MARGE_MEMOIRE = 1.2


class ParametresInvalides(ValueError):
    """Les parametres stockes ne permettent pas de verifier une empreinte.

    **Le message ne porte NI le mot de passe, NI l'empreinte, NI le sel** — il
    nomme le parametre fautif et rien d'autre.
    """


def _memoire_maximale(parametres: dict[str, Any]) -> int:
    return int(128 * int(parametres["n"]) * int(parametres["r"]) * _MARGE_MEMOIRE)


def _controler(parametres: dict[str, Any]) -> None:
    """Refuser des parametres inexploitables, en NOMMANT lequel manque.

    Sans ce controle, une ligne dont `parameters` aurait ete tronquee produirait
    un `KeyError` nu, dont le message ne dirait pas qu'il s'agit d'une empreinte
    de mot de passe.
    """
    for nom in ("n", "r", "p", "longueur_sel", "longueur_cle"):
        if nom not in parametres:
            message = f"parametre scrypt absent : {nom}"
            raise ParametresInvalides(message)
    n = int(parametres["n"])
    if n < 2 or n & (n - 1):
        message = "parametre scrypt invalide : n doit etre une puissance de deux >= 2"
        raise ParametresInvalides(message)


def _deriver(mot_de_passe: str, sel: bytes, parametres: dict[str, Any]) -> bytes:
    return hashlib.scrypt(
        mot_de_passe.encode("utf-8"),
        salt=sel,
        n=int(parametres["n"]),
        r=int(parametres["r"]),
        p=int(parametres["p"]),
        dklen=int(parametres["longueur_cle"]),
        maxmem=_memoire_maximale(parametres),
    )


def hacher(
    mot_de_passe: str, parametres: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    """Hacher un mot de passe. Rend `(empreinte, parametres a stocker)`.

    L'empreinte est `base64url(sel) + '$' + base64url(cle)`. Le sel est DANS
    l'empreinte, comme le fait argon2 : il n'est pas secret, et l'en separer
    demanderait une colonne de plus que le §10.2 ne declare pas.

    **La longueur n'est PAS bornee a 64 caracteres**, contrairement aux empreintes
    de jeton. `make secrets-check` le sait depuis `T2` : une empreinte de mot de
    passe est de longueur variable, et ce qui la rend verifiable est la presence
    des colonnes `algorithm` et `parameters`.
    """
    effectifs = dict(parametres or PARAMETRES_PAR_DEFAUT)
    _controler(effectifs)
    sel = secrets.token_bytes(int(effectifs["longueur_sel"]))
    cle = _deriver(mot_de_passe, sel, effectifs)
    empreinte = f"{_encoder(sel)}${_encoder(cle)}"
    return empreinte, effectifs


def verifier(mot_de_passe: str, empreinte: str, parametres: dict[str, Any]) -> bool:
    """Le mot de passe correspond-il a l'empreinte, sous CES parametres ?

    **LA COMPARAISON EST A TEMPS CONSTANT.** Un `==` sur des octets s'arrete au
    premier caractere different : la duree de la comparaison renseignerait alors
    sur le nombre d'octets corrects, ce qui permet de reconstruire une empreinte
    octet par octet. `hmac.compare_digest` ne s'arrete pas.

    Les parametres viennent de la BASE, jamais de ce module : c'est ce qui permet
    de verifier une empreinte produite avec d'anciens parametres, donc de les
    durcir sans invalider les comptes.

    Rend `False` -- et ne leve pas -- sur une empreinte malformee : une valeur
    corrompue en base ne doit pas produire une erreur 500 dont le message
    finirait dans un journal.
    """
    _controler(parametres)
    sel_encode, separateur, cle_encodee = empreinte.partition("$")
    if not separateur:
        return False
    try:
        sel = _decoder(sel_encode)
        attendue = _decoder(cle_encodee)
    except (ValueError, TypeError):
        return False
    if not sel or not attendue:
        return False
    return hmac.compare_digest(_deriver(mot_de_passe, sel, parametres), attendue)


def parametres_a_durcir(parametres: dict[str, Any]) -> bool:
    """Les parametres stockes sont-ils plus faibles que ceux d'aujourd'hui ?

    Employee au moment d'une connexion REUSSIE : c'est le seul instant ou le mot
    de passe en clair est disponible, donc le seul ou un rehachage est possible.
    **`T5` ne rehache pas** -- elle rend seulement l'information -- parce que
    rehacher suppose d'ecrire pendant une lecture, ce qui merite sa propre
    decision. La fonction existe pour que le jour du changement d'algorithme, la
    question soit deja posee au bon endroit.
    """
    try:
        _controler(parametres)
    except ParametresInvalides:
        return True
    return int(parametres.get("n", 0)) < int(PARAMETRES_PAR_DEFAUT["n"])


def _encoder(brut: bytes) -> str:
    return base64.urlsafe_b64encode(brut).decode("ascii").rstrip("=")


def _decoder(encode: str) -> bytes:
    rembourrage = "=" * (-len(encode) % 4)
    return base64.urlsafe_b64decode(encode + rembourrage)
