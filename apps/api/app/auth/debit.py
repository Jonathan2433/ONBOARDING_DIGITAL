"""Limitation de debit de l'authentification — cahier §20.1, §20.2.

LOT 3, sous-etape `T8`, stories `MVP-L03-US001` et `MVP-L03-US003`.

LE CAHIER DONNE LES SEUILS. LA FICHE DU LOT AFFIRMAIT LE CONTRAIRE

  Le §8 de `fiche-lot-3.md` annoncait « le cahier exige une limitation, **sans
  donner de seuil** », et invitait donc a en choisir. **C'est faux.** Le §20.2
  s'intitule « Seuils initiaux » et en enumere six, dont trois portent sur
  l'authentification. `.env.example` en porte cinq **depuis le LOT 0**, chacun
  avec son commentaire `[source] cahier 20.2`.

  Inventer une valeur ici aurait donc **contredit le cahier**, qui prevaut sur
  tout. C'est `ECART-034`, et c'est exactement l'avertissement du §9.0 de la
  passation : verifie avant de batir dessus, surtout quand un document t'annonce
  qu'il te reste une decision a prendre.

TROIS LIGNES DU §20.2, ET DEUX VERBES DIFFERENTS — LA DISTINCTION COMMANDE TOUT

      « 10 demandes de magic link par adresse et par heure : LIMITATION »
      « 5 echecs administrateur en 15 minutes : ALERTE »
      « 50 demandes depuis une meme origine en une heure : ALERTE »

  **Une seule des trois est une « limitation ».** Les deux autres sont des
  « alertes », et une alerte suppose `operational_alert` du modele §21.2 --
  table du **LOT 10**, « alertes operationnelles enregistrees » dans la roadmap.

  Ce module fait donc deux choses, et pas une troisieme :

      LIMITATION   la demande de lien par adresse -- 429, refus effectif
      DETECTION    l'origine, et les echecs administrateur -- journalisee au
                   niveau `WARNING`, avec un motif nomme
      PAS ICI      l'alerte elle-meme, qui exige `operational_alert` -- LOT 10

  Transformer une « alerte » en « limitation » aurait ete inventer une regle que
  le cahier n'ecrit pas -- et la consequence serait concrete : 50 requetes depuis
  une meme origine bloqueraient **tout un bureau derriere un partage
  d'adresse**. Le cahier a choisi le verbe « alerte » ; ce n'est pas a une
  sous-etape de le changer.

LA LIMITE NE DOIT PAS DEVENIR L'ORACLE QUE `T3` A FERME

  **C'est le piege principal de cette sous-etape.** Si le compteur ne portait que
  sur les adresses **connues** -- par exemple en comptant les lignes de
  `magic_link_request`, qui n'existent que pour un profil actif et autorise --
  alors une adresse inconnue ne serait **jamais** limitee, et une adresse connue
  le serait. Le 429 dirait « ce compte existe ».

  Le compteur porte donc sur **l'adresse normalisee, avant toute lecture de la
  base**. La onzieme demande rend 429 pour **n'importe quelle** adresse, connue
  ou non. Et ce n'est pas une lecture personnelle du cahier : le §20.1 enumere
  « limitation des requetes » et « reponses generiques pour les demandes de magic
  link » **dans la meme liste**.

  **Et cela reduit le residuel que `T3` avait nomme** : le chemin d'une adresse
  connue fait davantage de requetes SQL que celui d'une adresse inconnue, et le
  residuel de l'ordre de la milliseconde n'etait exploitable que
  statistiquement, donc par repetition. Dix demandes par heure et par adresse
  rendent cette repetition impraticable. La docstring de `routes.py` annoncait
  `T8` comme la sous-etape qui le ferait ; c'est fait.

L'ADRESSE N'ENTRE PAS EN CLAIR DANS REDIS

  `onboarding:debit:adresse:jean.dupont@exemple.fr` mettrait une donnee
  personnelle dans un magasin qui n'a **aucune politique de conservation** et
  dont le contenu est lisible par `redis-cli`. Le §10.3 minimise l'origine par
  `request_origin_hash` ; la meme logique s'applique a l'adresse, et le critere
  de la fiche le dit pour l'origine : « la valeur minimisee du §10.3 est
  employee, jamais une adresse IP brute ».

  Les deux dimensions emploient donc `empreinte_minimisee` -- HMAC, `jetons.py`.
  Un caractere de separation dans une adresse ne peut par ailleurs plus
  collisionner avec un autre espace de noms : une empreinte est hexadecimale.

C'EST UN COMPARE-ET-POSE, POUR LA CINQUIEME FOIS DANS CE LOT

  `INCR` rend la valeur **deja incrementee** : un seul aller-retour decide. Lire
  puis ecrire laisserait dix demandes simultanees lire « 0 » et se croire toutes
  les premieres -- le compteur avancerait de 1 au lieu de 10, et la limite
  n'arriverait jamais. Meme forme qu'en `T4`, `T5`, `T6` et `T7`.

  **ET LE DELAI D'EXPIRATION A DEUX FACONS DE MAL SE POSER, TOUTES DEUX
  MESURABLES :**

      INCR puis EXPIRE inconditionnel   la fenetre est repoussee a CHAQUE
                                        demande. Un attaquant qui envoie une
                                        requete par minute maintient la cle
                                        vivante indefiniment : l'adresse d'un
                                        collaborateur legitime reste bloquee
                                        **pour toujours**.

      INCR puis EXPIRE hors transaction si le processus meurt entre les deux, la
                                        cle survit SANS delai. L'adresse est
                                        bloquee definitivement, et rien ne le
                                        dit.

  La parade couvre les deux : **`INCR` et `EXPIRE … NX` dans une seule
  transaction** `MULTI`/`EXEC`. Atomique, donc pas de fenetre de mort ; `NX`,
  donc le delai est pose a la creation et **jamais repousse**.

LA FENETRE EST FIXE, ET LE RESIDUEL EST NOMME

  Une fenetre fixe d'une heure laisse passer jusqu'a **deux fois** le plafond a
  cheval sur une frontiere -- dix demandes a 10 h 59, dix a 11 h 01. Le §20.2
  ecrit « par heure », ce qu'une fenetre fixe satisfait litteralement, et une
  fenetre glissante exigerait de conserver l'horodatage de chaque demande, donc
  davantage de donnees sur une adresse. **Le dire vaut mieux que de laisser
  croire a une borne stricte.**

REDIS INJOIGNABLE : ON REFUSE, ET C'EST LE §20.1

  Le premier principe du §20.1 est « **refus par defaut** ». Si le compteur ne
  repond pas, la limite n'est pas applicable : laisser passer ferait d'une panne
  de Redis le moyen de desactiver la protection. L'appelant recoit donc une
  exception distincte et **tranche explicitement** -- il ne devine pas.

  Le cout est reel et assume : un Redis en panne empeche toute demande de lien.
  Il est deja rapporte -- `/health/ready` rend 503 avec le motif
  `redis indisponible` depuis `T3` du LOT 1 -- donc la panne est diagnosticable
  sans lire ce module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.auth.jetons import empreinte_minimisee

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

#  Prefixe de l'espace de noms Redis. Redis sert aussi de courtier Dramatiq
#  (§16.4) et porte les cles d'idempotence de `T7` : sans prefixe distinct, un
#  compteur de debit pourrait collisionner avec l'une ou l'autre.
PREFIXE_REDIS: Final = "onboarding:debit:"

#  Un delai court : ce comptage est sur le chemin d'une requete, et un Redis lent
#  ne doit pas la faire pendre.
DELAI_REDIS_SECONDES: Final = 2

# ===========================================================================
#
#  UN DELAI SEUL NE BORNE RIEN : redis-py REPREND DIX FOIS PAR DEFAUT
#
#    `socket_connect_timeout=2` avait l'air de borner l'attente. **Il ne la
#    bornait pas.** redis-py 8 applique par defaut `Retry(ExponentialBackoff(),
#    10)` sur une erreur de connexion : le delai s'applique a **chaque**
#    tentative, et le total mesure **4,06 s** sur un port ferme -- contre 0,003 s
#    avec la reprise bornee ci-dessous.
#
#    **LA CONSEQUENCE ETAIT REELLE, ET ELLE ETAIT DEUX FOIS GRAVE.** Sur le
#    chemin d'une requete, le « refus par defaut » du §20.1 ne vaut que s'il est
#    RAPIDE : quatre secondes par demande transforment une panne de Redis en
#    saturation de l'API, donc la protection en vecteur. Et dans la tache
#    « qualite » de l'integration continue, qui n'a **pas** de stack, la fixture
#    de purge des tests payait ce prix **deux fois par test** -- 613 tests, soit
#    plus de quatre-vingts minutes. La tache est restee bloquee, et c'est ce qui
#    a fait decouvrir le defaut.
#
#    **C'EST LA SIXIEME PROPOSITION DU §7.0, SOUS UN AUTRE JOUR** : un nombre
#    qu'on affiche comme une borne doit mesurer la grandeur qu'on croit borner.
#    Ici « delai de connexion » et « attente totale » sont deux grandeurs
#    differentes, d'un facteur dix.
#
#    Zero reprise, et non une : ce compteur est une protection, pas une donnee.
#    Reessayer une fois ne le rendrait pas plus juste, et le §20.1 tranche deja
#    ce qu'il faut faire quand il ne repond pas.
#
# ===========================================================================
REPRISES_REDIS: Final = 0

SECONDES_PAR_HEURE: Final = 3600

# ===========================================================================
#
#  LES TROIS SEUILS, RECOPIES DU §20.2 ET NON INVENTES
#
#    Chacun porte la phrase du cahier qui le produit. Le VERBE de cette phrase
#    decide de ce qui se passe au depassement, et c'est pour cela qu'il est cite.
#
#    Ces constantes ne sont PAS configurables, et c'est le meme parti que `T5`
#    pour le verrouillage : les rendre reglables par variable d'environnement
#    inviterait a les abaisser, alors que le cahier les ecrit. Leur destination
#    finale est `platform_setting` (modele §5.2, « seuils de securite »),
#    modifiable par le super-administrateur **seul** (matrice §19) et **auditee**
#    -- ce qui exige un ecran de reglages et `audit_log` du §21.1, donc les
#    LOTS 9 et 10. Voir `ECART-034`.
#
# ===========================================================================

#  « 10 demandes de magic link par adresse et par heure : LIMITATION »
DEMANDES_DE_LIEN_PAR_ADRESSE: Final = 10
FENETRE_DEMANDES_DE_LIEN: Final = SECONDES_PAR_HEURE

#  « 50 demandes depuis une meme origine en une heure : ALERTE »
#
#  **LECTURE DECLAREE.** Cette ligne du §20.2 n'ecrit pas « de magic link », la
#  precedente si. La lecture retenue est donc la plus large -- toute demande
#  d'authentification depuis cette origine -- et c'est aussi la plus utile : un
#  attaquant qui balaie mille adresses differentes ne fait avancer aucun compteur
#  par adresse, et seule cette dimension le voit.
DEMANDES_PAR_ORIGINE: Final = 50
FENETRE_DEMANDES_PAR_ORIGINE: Final = SECONDES_PAR_HEURE

#  « 5 echecs administrateur en 15 minutes : ALERTE »
#
#  **LES DEUX NOMBRES SONT DEJA EMPLOYES PAR `T5`**, pour le verrouillage de
#  compte -- meme derivation, meme phrase. Ce compteur-ci porte sur l'ADRESSE,
#  la ou celui de `T5` porte sur le COMPTE, et cette difference est la raison
#  d'etre de ce seuil : une adresse **sans** `user_account` n'a aucun compteur
#  d'echecs, donc peut etre sollicitee sans fin. Le verrou de `T5` ne la voit
#  pas.
ECHECS_ADMIN_PAR_ADRESSE: Final = 5
FENETRE_ECHECS_ADMIN: Final = 15 * 60


class CategorieDeCompteur:
    """Les dimensions comptees. Un nom par dimension, et pas un de plus.

    Les valeurs entrent dans une cle Redis : les declarer ici en fait la seule
    source, et un nom fantaisiste devient impossible.
    """

    DEMANDE_DE_LIEN: Final = "lien-par-adresse"
    ORIGINE: Final = "origine"
    ECHEC_ADMIN: Final = "echec-admin-par-adresse"


#  Motifs journalises au depassement. Ils nomment la dimension, **jamais la
#  valeur comptee** : une adresse dans un journal serait une donnee personnelle,
#  et le §28.2 l'interdit.
MOTIF_DEBIT_ADRESSE: Final = "debit_depasse_par_adresse"
MOTIF_DEBIT_ORIGINE: Final = "seuil_origine_atteint"
MOTIF_DEBIT_ECHECS_ADMIN: Final = "seuil_echecs_admin_atteint"


class CompteurIndisponible(RuntimeError):
    """Redis ne repond pas. **L'appelant tranche**, et ne devine pas.

    Le message nomme la classe de l'erreur, jamais l'URL de Redis -- qui porte
    un mot de passe.
    """


@dataclass(frozen=True, slots=True)
class Comptage:
    """Ce qu'un comptage rend : la valeur, le plafond, et le delai restant.

    `depasse` est calcule ici plutot que chez l'appelant : trois appelants qui
    ecriraient `valeur > plafond` finiraient par ne pas ecrire la meme
    comparaison, et un `>=` de trop deplacerait un seuil de un.
    """

    valeur: int
    plafond: int
    secondes_restantes: int

    @property
    def depasse(self) -> bool:
        """Vrai quand la demande courante franchit le plafond.

        **`>` ET NON `>=`.** Le plafond est un nombre d'evenements AUTORISES :
        « 10 demandes par heure » veut dire que la dixieme passe et que la
        onzieme est refusee. `INCR` rendant la valeur deja incrementee, la
        onzieme demande rend 11.
        """
        return self.valeur > self.plafond


def _client(parametres: Parametres) -> redis.Redis:
    return redis.Redis.from_url(
        parametres.url_redis(),
        socket_connect_timeout=DELAI_REDIS_SECONDES,
        socket_timeout=DELAI_REDIS_SECONDES,
        #  Voir le bloc de commentaire de `REPRISES_REDIS` : sans cela, le delai
        #  ci-dessus ne borne PAS l'attente.
        retry=Retry(NoBackoff(), REPRISES_REDIS),
    )


def compter(
    parametres: Parametres,
    *,
    categorie: str,
    valeur_minimisee: str,
    plafond: int,
    fenetre_secondes: int,
) -> Comptage:
    """Compter une occurrence et dire ou l'on en est dans la fenetre.

    **UN SEUL ALLER-RETOUR, ATOMIQUE.** `INCR` et `EXPIRE … NX` sont envoyes dans
    une transaction : la valeur rendue est deja incrementee, et le delai est pose
    a la creation sans jamais etre repousse. Voir l'en-tete du module pour les
    deux defauts que cela evite.

    Args:
        categorie: une valeur de `CategorieDeCompteur`. Elle cloisonne les
            dimensions : sans elle, une adresse et une origine partageraient un
            compteur.
        valeur_minimisee: l'empreinte HMAC de ce qui est compte. **Jamais la
            valeur en clair** -- voir l'en-tete du module.
        plafond: le seuil du §20.2.
        fenetre_secondes: la duree de la fenetre, du §20.2.

    Returns:
        Le comptage, qui sait dire s'il depasse.

    Raises:
        CompteurIndisponible: Redis ne repond pas. **On ne devine ni « sous le
            seuil » -- qui desactiverait la protection au premier incident -- ni
            « au-dessus » -- qui refuserait tout le monde sans le dire.**
    """
    cle = f"{PREFIXE_REDIS}{categorie}:{valeur_minimisee}"
    try:
        transaction = _client(parametres).pipeline(transaction=True)
        transaction.incr(cle)
        transaction.expire(cle, fenetre_secondes, nx=True)
        transaction.ttl(cle)
        resultats = transaction.execute()
    except (redis.RedisError, OSError) as erreur:
        message = f"compteur de debit injoignable ({type(erreur).__name__})"
        raise CompteurIndisponible(message) from None
    #  `TTL` rend -1 quand la cle n'a pas de delai et -2 quand elle n'existe
    #  plus. Ni l'un ni l'autre ne devrait arriver ici -- la transaction vient de
    #  poser les deux -- mais rendre un nombre negatif a l'appelant lui ferait
    #  calculer un `Retry-After` absurde. On borne a zero.
    return Comptage(
        valeur=int(resultats[0]),
        plafond=plafond,
        secondes_restantes=max(0, int(resultats[2])),
    )


def lire(
    parametres: Parametres,
    *,
    categorie: str,
    valeur_minimisee: str,
    plafond: int,
) -> Comptage:
    """Lire un compteur SANS l'incrementer.

    **POURQUOI UNE LECTURE SEULE EXISTE, ET POURQUOI ELLE N'EST PAS ATOMIQUE.**
    Le §20.2 compte des « echecs administrateur », non des tentatives : le
    compteur ne peut donc etre incremente qu'**apres** l'authentification, quand
    on sait qu'elle a echoue. Or le refus doit venir **avant** le travail en
    base -- c'est l'objet meme d'une limitation. Les deux moments sont donc
    distincts : on lit avant, on incremente apres.

    **LE RESIDUEL EST NOMME.** Cette lecture est un instantane : plusieurs
    tentatives simultanees peuvent lire la meme valeur et passer toutes les
    quatre. Le depassement possible est donc borne par la **concurrence**, non par
    le temps -- et il ne s'applique qu'aux adresses **sans** compte, celles avec
    un compte etant bornees exactement par le verrou de `T5`, dont l'`UPDATE …
    RETURNING` est atomique. Ce qui reste en jeu est du travail serveur, pas un
    acces.

    Une valeur absente rend un comptage a zero, avec un delai a zero : ni l'une
    ni l'autre ne depasse.
    """
    cle = f"{PREFIXE_REDIS}{categorie}:{valeur_minimisee}"
    try:
        client = _client(parametres)
        brut = client.get(cle)
        restant = client.ttl(cle)
    except (redis.RedisError, OSError) as erreur:
        message = f"compteur de debit injoignable ({type(erreur).__name__})"
        raise CompteurIndisponible(message) from None
    return Comptage(
        valeur=int(brut) if brut is not None else 0,
        plafond=plafond,
        secondes_restantes=max(0, int(restant)),
    )


def reinitialiser(parametres: Parametres, *, categorie: str, valeur_minimisee: str) -> None:
    """Effacer un compteur — appelee sur SUCCES d'une authentification.

    **ELLE EXISTE POUR LA COHERENCE AVEC `T5`, ET C'EST UN CRITERE
    D'EXPLOITATION.** `authentifier_un_administrateur` remet
    `failed_login_count` a zero quand la connexion reussit. Si le compteur Redis
    ne l'etait pas, un administrateur qui se trompe cinq fois puis reussit
    resterait refuse a sa connexion suivante pendant quinze minutes -- et le
    risque nomme au §7 de la fiche du lot est precisement « le verrouillage
    administrateur bloque Jonathan lui-meme ».

    Effacer sur succes ne donne rien a un attaquant : il faut le mot de passe
    pour reussir.

    Elle est silencieuse sur echec : la cle expirera d'elle-meme, et lever ici
    ferait echouer une connexion **reussie**.
    """
    try:
        _client(parametres).delete(f"{PREFIXE_REDIS}{categorie}:{valeur_minimisee}")
    except (redis.RedisError, OSError):
        return


def empreinte_pour_le_debit(valeur: str, cle: str, *, quoi: str) -> str:
    """Minimiser ce qui va servir de cle de compteur.

    Simple delegation, et elle existe pour une raison : **elle donne un seul
    point d'entree aux appelants du debit**, si bien qu'aucun n'est tente
    d'assembler une cle avec la valeur en clair. Le controle
    `make debit-check` verifie qu'aucune adresse ni aucune IP n'apparait dans
    les cles reellement posees dans Redis.
    """
    return empreinte_minimisee(valeur, cle, quoi=quoi)


def purger(parametres: Parametres, *, categorie: str) -> int:
    """Supprimer les compteurs d'une categorie. **Reservee aux tests et aux controles.**

    Elle existe parce qu'un controle de limitation doit pouvoir repartir d'un
    etat connu : sans elle, la deuxieme execution de `make debit-check` verrait
    les compteurs de la premiere et echouerait sur un livrable conforme -- le
    defaut `T4-3`, ou un nettoyage manquant a casse l'execution suivante.

    Elle ne touche **que** le prefixe de debit et une categorie nommee : elle ne
    peut pas effacer une file Dramatiq ni une cle d'idempotence.
    """
    client = _client(parametres)
    cles = list(client.scan_iter(match=f"{PREFIXE_REDIS}{categorie}:*", count=500))
    if not cles:
        return 0
    return int(client.delete(*cles))
