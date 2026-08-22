"""Jetons de connexion : engendrement, empreinte, et minimisation d'origine.

LOT 3, sous-etape `T3`, story `MVP-L03-US001`.

FONDEMENT — modele §10.3 : `token_hash` | « Hash uniquement ». Et cahier §7.2,
§28.2 : « aucun magic link complet » dans les journaux ou l'audit.

LE PREFIXE ET SON MOTIF VIENNENT DE `packages/observabilite`, PAS D'ICI

  **Le format d'un jeton a trois consommateurs** : ce module, qui l'engendre ; la
  barriere de masquage, qui doit le reconnaitre ; et la regle Gitleaks, qui doit
  refuser son commit. Le filtre de masquage ne peut pas importer `apps/api` --
  c'est `apps/api` qui depend de lui.

  Les constantes vivent donc dans `observabilite.masquage`, et ce module les
  importe. Une seule source, motif de `DEC-466` : deux definitions d'un meme
  format finissent par diverger, et ce jour-la la fuite est silencieuse.

  Le prefixe n'est PAS un secret et n'affaiblit rien : l'entropie est dans les
  256 bits qui le suivent, et un attaquant qui verrait un jeton n'apprendrait
  rien de plus en sachant qu'il en est un. Il rend en revanche les deux
  detecteurs **exacts** au lieu d'heuristiques -- §7.25.

POURQUOI UNE EMPREINTE SHA-256 SIMPLE, ET NON UN HMAC

  Un HMAC serait meilleur sur une valeur de faible entropie -- un mot de passe,
  un numero, une adresse -- parce qu'il empeche le rejeu d'une table
  precalculee. Un jeton de 256 bits tire par `secrets` n'est pas dans une table
  precalculee et ne peut pas y etre : il n'y a rien a deviner.

  Et un HMAC aurait un cout REEL : la cle qui le produit devient indispensable a
  la verification. Une rotation d'`APP_SECRET_KEY` rendrait **tous** les jetons
  actifs invalides sans que rien ne le dise, et le §10.2 impose de pouvoir
  changer d'algorithme sans casser les comptes existants. Le modele ecrit « hash
  uniquement » : c'est ce qui est fait.

  **`request_origin_hash` est le cas INVERSE, et c'est pour cela qu'il est
  traite differemment ci-dessous.**
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

#  `as` EXPLICITE : en mode strict, mypy refuse qu'un module reexporte un nom
#  importe sans le declarer. Le prefixe EST une part de l'interface publique de ce
#  module -- les tests et `app.auth` le lisent ici, pas dans le paquet
#  d'observabilite -- donc le reexport est voulu, et il est declare.
from observabilite.masquage import MOTIF_JETON_DU_PROJET
from observabilite.masquage import PREFIXE_MAGIC_LINK as PREFIXE_MAGIC_LINK

#  256 bits d'alea. `secrets.token_urlsafe(32)` rend 43 caracteres base64url,
#  soit plus que la borne `LONGUEUR_MINIMALE_D_ALEA` que les detecteurs exigent.
OCTETS_D_ALEA = 32

#  Le motif des jetons DE CE PROJET, reexporte pour que les tests de l'API n'aient
#  pas a connaitre son emplacement. Il couvre les trois prefixes de la famille --
#  `T6` et `T10` n'auront rien a y ajouter.
MOTIF_JETON_MAGIC_LINK = MOTIF_JETON_DU_PROJET

_MOTIF_COMPILE = re.compile(MOTIF_JETON_DU_PROJET)

#  Longueur d'un SHA-256 en hexadecimal. La colonne `token_hash` est bornee a
#  cette valeur exacte, et `make secrets-check` s'en sert pour distinguer une
#  empreinte de jeton d'un stockage en clair.
LONGUEUR_EMPREINTE = 64


def engendrer_jeton_magic_link() -> str:
    """Engendrer un jeton de connexion : prefixe, puis 256 bits d'alea.

    `secrets` et non `random` : `random` est un generateur pseudo-aleatoire
    reproductible, et un jeton de connexion previsible est un contournement
    d'authentification.
    """
    return f"{PREFIXE_MAGIC_LINK}{secrets.token_urlsafe(OCTETS_D_ALEA)}"


def ressemble_a_un_jeton_magic_link(texte: str) -> bool:
    """Le texte contient-il un jeton de ce projet ?

    Employee par les tests des barrieres de masquage : elles doivent recevoir
    **le format que ce projet produit**, non un exemple de documentation. C'est
    la lecon `T4-1` du LOT 1, ou le filtre laissait passer `redis://:mdp@` --
    precisement le format que `url_redis()` produit.
    """
    return _MOTIF_COMPILE.search(texte) is not None


def empreinte_de_jeton(jeton: str) -> str:
    """Empreinte SHA-256 hexadecimale d'un jeton — 64 caracteres.

    Le prefixe est INCLUS dans le calcul. L'exclure n'apporterait rien et
    creerait une seconde regle a retenir.
    """
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def empreinte_d_origine(origine: str, cle: str) -> str:
    """Valeur minimisee d'une origine de requete — modele §10.3.

    **ICI UN HMAC EST NECESSAIRE, ET C'EST L'INVERSE DU JETON.** Une adresse IPv4
    n'a que 32 bits : une empreinte SHA-256 simple se renverse en enumerant les
    4,3 milliards de valeurs possibles, ce qui est l'affaire de quelques minutes.
    Elle ne serait donc **pas** une valeur minimisee, seulement une valeur qui en
    a l'air -- exactement le genre de controle qui produit la meme observation en
    cas d'echec et de succes.

    La cle est `APP_SECRET_KEY`. Sa rotation rend les empreintes anterieures
    incomparables aux nouvelles, ce qui est acceptable ici et ne l'etait pas pour
    le jeton : cette valeur ne sert qu'a compter des demandes recentes -- la
    limitation de debit de `T8` -- non a authentifier quiconque.

    Args:
        origine: l'adresse de l'appelant, telle que le transport la donne.
        cle: `APP_SECRET_KEY`. Une cle vide leve, plutot que de produire une
            empreinte non salee qui aurait l'apparence d'une valeur minimisee.
    """
    return empreinte_minimisee(origine, cle, quoi="une adresse IP")


def empreinte_minimisee(valeur: str, cle: str, *, quoi: str) -> str:
    """Empreinte HMAC d'une valeur de FAIBLE entropie — le cas inverse du jeton.

    **LOT 3, `T8` L'EMPLOIE POUR LES COMPTEURS DE DEBIT, ET LE MOTIF EST LE MEME
    QU'AU §10.3.** Une adresse e-mail est devinable ; une adresse IPv4 n'a que 32
    bits. Une empreinte SHA-256 simple de l'une ou de l'autre se renverse par
    enumeration, et ne serait donc pas une valeur minimisee -- seulement une
    valeur qui en a l'air.

    **UNE SEULE IMPLEMENTATION, ET C'EST DELIBERE.** `empreinte_d_origine`
    delegue ici. Deux fonctions HMAC voisines finiraient par diverger -- une clé
    differente, un encodage different -- et ce jour-la deux compteurs censes
    porter sur la meme valeur compteraient separement, **en paraissant
    fonctionner**. C'est le motif de `DEC-466`, applique a l'interieur d'un
    module.

    Args:
        valeur: la donnee a minimiser. Elle n'est jamais journalisee.
        cle: `APP_SECRET_KEY`. Une cle vide leve, plutot que de produire une
            empreinte non salee qui aurait l'apparence d'une valeur minimisee.
        quoi: ce que la valeur represente, pour que le message d'erreur soit
            diagnosticable. **Jamais la valeur elle-meme** : un message d'erreur
            finit dans un journal.
    """
    if not cle:
        message = (
            f"empreinte_minimisee exige une cle non vide : sans elle, l'empreinte "
            f"de {quoi} est reversible par enumeration"
        )
        raise ValueError(message)
    return hmac.new(cle.encode("utf-8"), valeur.encode("utf-8"), hashlib.sha256).hexdigest()
