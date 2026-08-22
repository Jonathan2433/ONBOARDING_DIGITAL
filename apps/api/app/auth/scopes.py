"""Scopes des comptes de service — cahier §22, story `MVP-L03-US007`.

LOT 3, sous-etape `T10`.

LE CAHIER EN ENUMERE CINQ, ET LA FICHE DU LOT DISAIT LE CONTRAIRE

  Le §8 de `fiche-lot-3.md` annoncait « **Liste des scopes** — aucun document n'en
  enumere ». Le §22 en donne **cinq** :

      people:read
      people:import
      media:process
      email:send
      reports:generate

  C'est `ECART-036`, et c'est exactement la classe de `ECART-034` que `T8` a
  ouverte : un document derive qui affirme qu'une decision reste a prendre alors
  que sa source l'a prise. **Verifie avant de demander.**

MAIS LA LISTE N'EST PAS FERMEE, ET LES DEUX MOTS QUI LE DISENT SONT « PAR EXEMPLE »

  « Chaque compte de service possede des scopes explicites, **par exemple** : … ».
  C'est la meme forme que le §25.1 du modele -- « a prevoir **notamment** » -- ou le
  LOT 2 a pose quatre unicites de plus, chacune **derivee** d'une regle ecrite.

  **CONSEQUENCE SUR LA VALIDATION, ET ELLE EST DECISIVE.** Une liste blanche fermee
  contredirait « par exemple » et bloquerait le LOT 9 -- qui creera ses propres
  scopes d'import -- et le LOT 11 -- media et exports. La validation porte donc sur
  la **FORME**, et les cinq du cahier sont declares comme le vocabulaire **connu**,
  confronte au cahier par un test.

  **ET LE MODE D'ECHEC D'UN SCOPE INCONNU EST BRUYANT, NON SILENCIEUX.** Une faute
  de frappe -- `people:raed` -- produit un scope que rien n'accorde : l'appel qui
  l'exige est **refuse**. C'est un echec de type « refus par defaut », §20.1, et
  non un droit accorde par erreur. Une liste blanche fermee aurait attrape la
  faute plus tot ; elle aurait aussi refuse un scope legitime du LOT 9. Entre les
  deux, le cahier a tranche par « par exemple ».

LA FORME EST DERIVEE DES CINQ EXEMPLES, PAS INVENTEE

      domaine:action     minuscules, chiffres et tirets bas
                         un seul `:`, aucun espace

  Les cinq exemples la respectent tous, et c'est la seule regle que le cahier
  laisse deduire. Rien de plus n'est exige : `RIGHTS-018` dit « scopes limites »,
  ce qui parle de leur PORTEE, non de leur orthographe.
"""

from __future__ import annotations

import re
from typing import Final

#  Les cinq du §22, dans l'ordre du cahier. **Un test les relit dans le cahier** :
#  une liste recopiee vieillit au premier ajout -- §7.27, cinq occurrences dans ce
#  lot.
SCOPES_DU_CAHIER: Final[tuple[str, ...]] = (
    "people:read",
    "people:import",
    "media:process",
    "email:send",
    "reports:generate",
)

#  `domaine:action`. Derivee des cinq exemples, non inventee.
MOTIF_SCOPE: Final = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")

#  Borne haute du nombre de scopes d'un jeton. `RIGHTS-018` dit « scopes limites au
#  besoin exact » : une valeur sans borne laisserait poser un jeton portant mille
#  scopes, ce qui est l'inverse de l'intention. Le nombre est genereux -- quatre
#  fois les cinq du cahier -- pour ne pas brider les lots suivants.
SCOPES_MAXIMUM_PAR_JETON: Final = 20


class ScopeInvalide(ValueError):
    """Un scope ne respecte pas la forme, ou la liste est inexploitable.

    Le message nomme **la contrainte et la valeur fautive** : contrairement a un
    jeton ou a une adresse, un scope n'est pas une donnee personnelle, et le
    diagnostic vaut plus que la discretion.
    """


def controler_les_scopes(scopes: object) -> tuple[str, ...]:
    """Valider une liste de scopes et la rendre normalisee.

    **UNE LISTE VIDE EST REFUSEE**, et ce n'est pas du zele : un jeton sans scope
    n'accorde rien, donc il ne sert a rien -- mais il **existe**, et un operateur
    qui le voit croira qu'il fonctionne. Le §20.1 dit « refus par defaut » ; un
    jeton inutile est un piege, pas une securite.

    **LES DOUBLONS SONT REFUSES, PAS DEDUPLIQUES.** Dedupliquer ferait qu'une liste
    fautive serait acceptee en silence, et le §7.25 dit qu'un controle exact vaut
    mieux qu'un controle large.

    Args:
        scopes: ce que l'appelant fournit. Le type est `object` a dessein : la
            valeur peut venir d'un `jsonb`, donc de la base, donc de n'importe
            quoi. La verifier ici est le seul endroit ou elle passe.

    Returns:
        Les scopes, dans l'ordre fourni, en tuple immuable.

    Raises:
        ScopeInvalide: forme invalide, liste vide, doublon, ou trop de scopes.
    """
    if not isinstance(scopes, list | tuple):
        message = f"scopes : une liste est attendue, recu {type(scopes).__name__}"
        raise ScopeInvalide(message)
    if not scopes:
        message = (
            "scopes : la liste est vide. Un jeton sans scope n'accorde rien, et un "
            "operateur qui le voit croira qu'il fonctionne"
        )
        raise ScopeInvalide(message)
    if len(scopes) > SCOPES_MAXIMUM_PAR_JETON:
        message = f"scopes : {len(scopes)} depasse le maximum de {SCOPES_MAXIMUM_PAR_JETON}"
        raise ScopeInvalide(message)

    vus: list[str] = []
    for scope in scopes:
        if not isinstance(scope, str) or not MOTIF_SCOPE.match(scope):
            message = (
                f"scope invalide : {scope!r}. Forme attendue `domaine:action`, en "
                "minuscules, chiffres et tirets bas"
            )
            raise ScopeInvalide(message)
        if scope in vus:
            message = f"scope en double : {scope!r}. Une liste fautive n'est pas nettoyee"
            raise ScopeInvalide(message)
        vus.append(scope)
    return tuple(vus)


def couvre(accordes: tuple[str, ...], requis: str) -> bool:
    """Le scope requis est-il accorde ? **Egalite exacte, aucune hierarchie.**

    **AUCUN JOKER, AUCUN PREFIXE, ET C'EST UN CHOIX.** Il serait tentant de faire
    que `people:*` couvre `people:read`, ou que `people:import` implique
    `people:read`. Le cahier n'ecrit **aucune** hierarchie, et en inventer une
    accorderait des droits que personne n'a accordes -- exactement ce que
    `RIGHTS-018` interdit : « scopes limites au besoin exact ».

    Le jour ou une hierarchie sera decidee, elle se posera ici, et ce
    commentaire dira qu'elle n'existait pas avant.
    """
    return requis in accordes
