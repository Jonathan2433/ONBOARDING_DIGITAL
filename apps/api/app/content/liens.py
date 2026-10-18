"""Les liens internes d'une entite — modele §15.3, annexe A §13 et §19. LOT 6, `T8`.

Story `MVP-L06-US005`, « gerer la presentation et les liens internes de
l'entite ». Critere : « Presentation, Hub, Academy et SharePoint sont modifiables
localement ; **les URL sont validees**. »

`QO-120` EST CLOSE ICI, ET ELLE ETAIT BLOQUANTE — `DEC-587`

  Le modele §15.3 et le cahier §13 ecrivent tous deux, mot pour mot, « les URL
  sont validees selon une **liste de protocoles autorises** », et **ni l'un ni
  l'autre ne la donne**. Mesure du 22/09/2026 sur les cinq documents de cadrage :

      motif recherche                                   occurrences
      « protocole »                                     2 — les deux phrases ci-dessus
      `https?://`, `mailto:`, `javascript:`, `ftp://`,
      `data:`, `tel:`                                   **0**

  Zero. Le corpus nomme l'exigence et ne fournit pas la liste.

  **LES DEUX ERREURS SONT SYMETRIQUES, ET C'EST LE §7.29.** Ne rien valider
  enfreint une phrase ecrite deux fois ; poser une liste **fermee** figerait une
  interpretation la ou la source ne tranche pas. La sortie est entre les deux :
  une liste **declaree, minimale et migrable d'une ligne**, dont le refus
  ENUMERE ce qu'il autorise -- si bien que l'elargir est un geste de trois
  caracteres et que personne ne peut ignorer ce qui est permis.

  Arbitrage de Jonathan du 19/09/2026, `DEC-587` : **`https` seul, et `http`
  refuse NOMMEMENT.** Les trois motifs, dans l'ordre de force :

    1. **les trois destinations que le critere nomme sont des SaaS d'entreprise**
       -- Hub, eXalt Academy, SharePoint -- et aucune ne se sert en clair ;
    2. **un lien en clair degrade la page qui le porte.** Le cahier exige HTTPS
       pour la plateforme (§«ouverture generale», §22.3, `MVP-L14-US002`) : y
       coudre des liens `http` ferait retomber en clair un parcours qui ne l'est
       nulle part ailleurs ;
    3. **`http` merite son PROPRE refus.** « Protocole inconnu » sur une adresse
       que l'auteur a tapee juste, a un `s` pres, est un message qui n'apprend
       rien. Un controle exact vaut mieux qu'un controle large (§7.25).

UNE LISTE BLANCHE DE PROTOCOLES NE SUFFIT PAS, ET C'EST MESURE

  C'est le constat le plus utile de cette sous-etape, parce qu'il contredit la
  lecture naive de la phrase du corpus. Mesure du 22/09/2026 sur `urlsplit` :

      entree                          scheme        netloc
      'https://hub.exalt.test/'       'https'       'hub.exalt.test'
      'https:alert(1)'                'https'       ''            <-- !
      'https:/hub.exalt.test'         'https'       ''            <-- !
      'https://'                      'https'       ''            <-- !

  **`https:alert(1)` PASSE UNE LISTE BLANCHE DE PROTOCOLES.** Un controle qui
  s'arreterait au schema accepterait donc une chaine qui n'adresse aucune
  ressource, et qu'un navigateur traite comme une reference relative. La
  validation exige donc **aussi un hote**, et c'est `url_sans_hote`.

  Deux autres mesures du meme jour commandent le code :

      'HTTPS://X'                 -> scheme 'https'       urlsplit MINUSCULISE
      'java\\nscript:alert(1)'     -> scheme 'javascript'  urlsplit RETIRE \\t \\r \\n
      'java\\tscript:alert(1)'     -> scheme 'javascript'  idem

  La premiere dit qu'une comparaison de schema doit se faire **apres** l'analyse,
  jamais sur la chaine brute -- sans quoi `HTTPS://` serait refuse. La seconde
  dit l'inverse pour la meme raison : l'analyseur **normalise** une chaine que
  l'auteur n'a pas tapee, et un controle qui lirait la chaine brute verrait
  `java\\nscript` la ou le navigateur verra `javascript`.

  D'ou `url_ambigue`, qui **n'est pas une liste de caracteres interdits** : elle
  exige que le segment de schema **tel qu'il est tape** soit, a la casse pres,
  exactement celui que l'analyseur a lu. Toute divergence est refusee sans
  chercher a savoir laquelle. Ecrire la liste `\\t \\r \\n` serait recopier un
  detail interne de CPython, qui vieillirait a la premiere version (§7.27).

LE CONTROLE EST A DEUX ETAGES, ET LES DEUX SONT NECESSAIRES

      la contrainte `ck_internal_link_url_https` (migration `0019`)
          le PLANCHER. Elle rend « aucune URL `javascript:` n'existe en base »
          STRUCTUREL et non promis (§7.35) : l'y ecrire exige de casser une
          migration, pas d'oublier un appel. Elle couvre ce que ce module ne
          couvre pas -- une insertion par SQL, une reprise du LOT 11, un import
          du LOT 9.

      `valider_une_url` (ce module)
          le REFUS EXACT. Elle distingue quatre causes la ou la contrainte n'en
          rend qu'une, et elle exige l'hote, que `LIKE 'https://%'` ne sait pas
          exiger. Elle est aussi appelable **hors HTTP**, et une fonction qui
          accepterait `mailto:` rendrait la regle du §15.3 dependante de son
          appelant (corollaire du §7.37).

  **`T1` AVAIT REFUSE LA CONTRAINTE, ET IL AVAIT RAISON A SA DATE.** Son
  commentaire dit « inventer la liste ici la figerait dans le schema ». Ce qui a
  change n'est pas l'argument, c'est que la liste n'est plus une invention :
  `DEC-587` la tranche. Et la figer coute exactement ce que coute le
  `contrainte_enumeration` de `page_type` -- une migration d'une ligne --, qui
  est precisement le motif pour lequel ce depot prefere une verification a un
  type `enum` natif.

LE RANG N'EST JAMAIS CHOISI PAR L'APPELANT, ET UNE MESURE L'EXIGE

  `T1` a pose `uq_internal_link_entity_ordre_non_archive`, unique et partiel sur
  `archived_at IS NULL`, en disant « meme motif que `content_block` ». Mesure du
  22/09/2026 sur la base reelle, deux liens aux rangs 900 et 901 :

      un seul UPDATE, echange direct   -> REFUSE (uq_internal_link_entity_ordre_non_archive)
      deux temps, decalage DERIVE      -> ACCEPTE (decalage = max + 1 = 902)

  **Un simple echange de deux liens est donc REFUSE par la base.** Une route qui
  aurait laisse l'appelant poser son rang aurait rendu la permutation de deux
  cartes impossible -- un trou fonctionnel sur un livrable conforme, et personne
  ne l'aurait vu avant l'ecran de `T10`.

  Deux consequences, et elles tiennent tout le dessin de ce module :

    1. **la creation AJOUTE EN QUEUE**, le rang valant `max + 1` lu dans la meme
       transaction. Aucun champ `rang` n'est offert : deux liens de meme rang
       sont **inexprimables** plutot que refuses (§7.35), exactement comme
       `display_order` vaut l'index de la liste chez `T6` ;
    2. **la reecriture d'ordre se fait EN DEUX TEMPS**, avec un decalage
       **derive** du maximum courant. Une constante magique -- `+ 1000` --
       serait fausse le jour ou une entite porte mille liens, et la contrainte
       `ordre_positif` interdit de passer par des rangs negatifs.

QUI PEUT QUOI — DEUX GRILLES, ET LES DEUX SOURCES CONCORDENT

  **C'est la QUATRIEME grille voisine de ce lot, et la premiere qui concorde.**
  `T6` avait trouve le §13 divergent du §6.1 dans les deux sens ; `T7` avait
  trouve la restauration plus etroite que l'archivage. Ici la confrontation, faite
  avant d'ecrire une ligne :

      LECTURE — matrice §5, la seule qui porte les HUIT roles authentifies

          « Presentation de l'entite »          ANON —, les huit **Lecture**
          « Liens Hub/Academy/SharePoint »      ANON —, les huit **Lecture**

        Les deux ressources de `T8` y sont **nommement citees**, et la grille est
        celle de `T5` : une session etablie, rien de plus. Lire la ligne
        « Consulter » du §13 a la place serait la faute de `T5` -- son tableau
        n'a ni colonne `EMP` ni colonne `NEW`, et une absence de colonne n'est
        pas une exclusion.

      GESTION — matrice §13 (six colonnes) et §19 (trois)

          §13 « Gerer les cartes Hub/Academy/SharePoint »
                                   DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global
          §13 « Modifier la presentation de l'entite »
                                   DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global
          §19 « Modifier les liens internes »
                                          ESM Entite                     ADM-E Entite  SUPER Global

        **Les trois lignes donnent le meme ensemble**, et le §19 ne contredit
        rien : son tableau n'a que trois colonnes -- ni `DSM`, ni `BOOST`, ni
        `OFFICE` --, ce qui est une absence de colonne et non une exclusion. Le
        §13, qui les porte, les met **a tiret**. Les deux lectures s'accordent
        donc sur `ESM`, `ADM-E` et `SUPER`, et **aucune n'accorde quoi que ce
        soit au Booster ni au responsable de bureau** : un lien appartient a
        l'entite, pas a un cercle ni a un bureau, et `internal_link` ne porte
        d'ailleurs ni `circle_id` ni `office_id`.

  **`Entite fonctionnel` DU §19 NE MORD PAS ICI.** La ligne « Modifier nom
  d'affichage, ville et contenus locaux » donne a l'`ESM` « Entite
  **fonctionnel** » -- une nuance qui porte sur `entity.display_name` et
  `entity.city`, que ce module n'ecrit pas. Sa ligne des liens internes, elle,
  dit « Entite » sans qualificatif.

CE QUE CE MODULE N'ECRIT PAS, ET OU CELA VIT DEJA

  **La « presentation de l'entite » n'a AUCUNE ligne de code dans `T8`**, et
  c'est un resultat, pas un manque. Le cahier la situe : « accueil d'une entite
  contenant **la presentation** et les acces au Framework », et « page d'accueil
  dans l'ordre valide : 1. **presentation de l'entite** ; 2. Framework ; [...]
  5. **liens internes** ». C'est donc une **page de contenu**, du type `HOME` du
  §15.1 -- et `T6` la cree, `T6` en ecrit les blocs, `T7` la publie.

  La verification qui compte n'est pas cette lecture mais la GRILLE : `HOME`
  appartient a `TYPES_SANS_PORTEE_LOCALE`, donc
  `resoudre_le_perimetre_editorial` le reserve deja a `ROLES_DE_PORTEE_ENTITE` --
  `ESM`, `ADM-E`, `SUPER` --, **exactement ce que le §13 ecrit sur la ligne
  « Modifier la presentation de l'entite »**. Deux tests le MESURENT plutot que
  ce paragraphe ne l'affirme : l'un que les trois roles l'obtiennent, l'autre
  qu'un Booster ne l'obtient pas sur une page `HOME`.

  **Le §5.3 nomme aussi « liens internes » parmi les cles d'`entity_setting`**, et
  ce n'est pas une seconde citerne. `entity_setting` est un magasin cle/valeur
  generique -- « chaque cle est validee par un schema connu » -- la ou §15.3
  donne une table DEDIEE avec `link_type`, `display_order`, `active` et ses
  contraintes. Y ecrire les liens perdrait tout ce que `T1` a pose. Le §5.3
  enumere des CATEGORIES de parametres locaux ; le §15.3 en implemente une.

IL N'Y A NI SUPPRESSION NI ARCHIVAGE DE LIEN, ET LE §15.3 DIT POURQUOI

  Il declare `active` **en plus** des champs communs du §3.1, qui portent deja
  `archived_at` -- et `T1` a refuse de les fondre : « on DESACTIVE un lien pour
  le retirer de l'affichage sans perdre sa definition, on l'ARCHIVE pour le
  sortir du jeu de donnees courant. »

  Retirer un lien de l'accueil est donc `actif = false`, et c'est le geste que
  le §15.3 prevoit. **L'archivage d'un lien n'est offert par aucune route**, et
  le taire serait pire que de le dire : aucune ligne du §13 ni du §19 ne nomme
  l'archivage d'un lien, et en inventer une serait le §6.5.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final
from urllib.parse import urlsplit

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.content.modeles import TYPES_DE_LIEN
from app.shared.errors import ErreurApplicative

#  **LA LISTE, ET ELLE EST LA SEULE DE TOUT LE DEPOT.** `DEC-587`, `QO-120`.
#  L'elargir est un geste de trois caracteres ici PLUS une migration d'une ligne
#  sur `internal_link_url_https` : les deux etages doivent bouger ensemble, et un
#  test exige qu'ils concordent -- sinon le service accepterait ce que la base
#  refuserait, en 500 au lieu de 422.
PROTOCOLES_AUTORISES: Final[frozenset[str]] = frozenset({"https"})

#  **REFUSE NOMMEMENT PLUTOT QUE SIMPLEMENT ABSENT**, et ce n'est pas un ornement :
#  `http` est la seule adresse qu'un auteur tape en croyant bien faire. Lui rendre
#  « protocole inconnu » lui ferait chercher une faute de frappe la ou il manque
#  un `s`. C'est le §7.25 -- un controle exact vaut mieux qu'un controle large.
PROTOCOLE_EN_CLAIR: Final = "http"

CODE_URL_ILLISIBLE: Final = "url_illisible"
MESSAGE_URL_ILLISIBLE: Final = (
    "Cette adresse ne porte aucun protocole. Une adresse complete commence par « https:// »."
)

CODE_URL_AMBIGUE: Final = "url_ambigue"
MESSAGE_URL_AMBIGUE: Final = (
    "Cette adresse porte des caracteres qui en changent la lecture. Retapez-la sans "
    "espace ni retour a la ligne."
)

CODE_URL_NON_CHIFFREE: Final = "url_non_chiffree"
MESSAGE_URL_NON_CHIFFREE: Final = (
    "Cette adresse n'est pas chiffree. Remplacez « http:// » par « https:// »."
)

CODE_URL_PROTOCOLE_REFUSE: Final = "url_protocole_refuse"
#  **LE MESSAGE DERIVE LA LISTE**, il ne la recopie pas : l'elargir ne peut pas
#  laisser derriere lui un message qui annonce l'ancienne (§7.27).
MESSAGE_URL_PROTOCOLE_REFUSE: Final = (
    "Ce protocole n'est pas autorise. Protocole(s) accepte(s) : "
    + ", ".join(sorted(PROTOCOLES_AUTORISES))
    + "."
)

CODE_URL_SANS_HOTE: Final = "url_sans_hote"
MESSAGE_URL_SANS_HOTE: Final = (
    "Cette adresse ne designe aucun serveur. Une adresse complete s'ecrit "
    "« https://serveur/chemin »."
)

CODE_TYPE_DE_LIEN_REFUSE: Final = "type_de_lien_refuse"
MESSAGE_TYPE_DE_LIEN_REFUSE: Final = (
    "Ce type de lien n'est pas autorise. Les types sont ceux du modele §15.3."
)

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "Ce lien a change depuis votre lecture. Rechargez-le avant de le modifier."
)

CODE_LIEN_INTROUVABLE: Final = "lien_introuvable"
MESSAGE_LIEN_INTROUVABLE: Final = "Ce lien interne n'existe pas dans cette entite."

CODE_ORDRE_INCOMPLET: Final = "ordre_incomplet"
MESSAGE_ORDRE_INCOMPLET: Final = (
    "La liste d'ordre doit nommer exactement une fois chacun des liens non archives "
    "de cette entite."
)

#  Le nom du declencheur de la migration `0019`. **C'est `diag.constraint_name`
#  qui discrimine**, jamais le texte du message : meme parti que `T6` et `T7`.
CONTRAINTE_URL_HTTPS: Final = "ck_internal_link_url_https"


@dataclasses.dataclass(frozen=True, slots=True)
class LienInterne:
    """Un lien tel qu'il est servi — modele §15.3, tous ses champs.

    **`actif` EST RENDU MEME PAR LA LECTURE PUBLIQUE, QUI NE SERT QUE DES
    ACTIFS.** Un champ constant a `true` parait inutile ; le taire obligerait
    l'ecran de gestion a lire une AUTRE structure, et deux structures pour une
    meme ressource divergent au premier ajout de colonne.
    """

    identifiant: uuid.UUID
    libelle: str
    url: str
    type_de_lien: str
    description: str | None
    reference_d_icone: str | None
    rang: int
    actif: bool
    version: int


#  **`archived_at IS NULL` PARTOUT, ET `active` SEULEMENT QUAND ON LE DEMANDE.**
#  Les deux colonnes ne disent pas la meme chose (§15.3, et le commentaire de
#  `T1`) : la lecture publique ne sert que les actifs, la lecture de gestion sert
#  les deux pour qu'un lien desactive puisse etre reactive. Sans elle, desactiver
#  serait un aller sans retour -- exactement le trou que la mesure de permutation
#  a evite sur les rangs.
_LIENS: Final = """
SELECT id, label, url, link_type, description, icon_reference, display_order, active, version
  FROM internal_link
 WHERE entity_id = :entite AND archived_at IS NULL
   {filtre_actif}
 ORDER BY display_order
"""

#  Le rang suivant, lu dans la MEME transaction que l'insertion. `-1 + 1 = 0`
#  donne le premier rang d'une entite vide, et la contrainte `ordre_positif` du
#  §25.1 est donc tenue sans cas particulier.
_RANG_SUIVANT: Final = text(
    """
    SELECT COALESCE(max(display_order), -1) + 1
      FROM internal_link
     WHERE entity_id = :entite AND archived_at IS NULL
    """
)

_INSERER_UN_LIEN: Final = text(
    """
    INSERT INTO internal_link
      (entity_id, label, url, link_type, description, icon_reference, display_order,
       active, created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :libelle, :url, :type_de_lien, :description, :icone, :rang,
       :actif, :acteur, :acteur, :instant, :instant)
    RETURNING id, version
    """
)

#  **LA VERSION EST LUE `FOR UPDATE`**, et le motif est celui de `T6` : sans le
#  verrou, deux modifications concurrentes liraient la meme version, la
#  trouveraient toutes deux a jour, et la seconde ecraserait la premiere --
#  « l'ecrasement silencieux » que le §18.4 nomme. C'est la LECTURE qui doit
#  verrouiller ; au moment ou l'on ecrit, le mal est fait.
_LIEN_A_MODIFIER: Final = text(
    """
    SELECT version, display_order
      FROM internal_link
     WHERE id = :lien AND entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

#  **`display_order` EST ABSENT DE CET `UPDATE`, ET C'EST LE POINT.** Le rang
#  n'appartient pas a la definition d'un lien mais a l'ORDRE de la liste, que
#  `reordonner_les_liens` seule reecrit. Les confondre ferait d'une modification
#  de libelle une occasion de casser l'ordre.
_METTRE_A_JOUR_UN_LIEN: Final = text(
    """
    UPDATE internal_link
       SET label = :libelle,
           url = :url,
           link_type = :type_de_lien,
           description = :description,
           icon_reference = :icone,
           active = :actif,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :lien AND entity_id = :entite AND archived_at IS NULL
    RETURNING version
    """
)

#  Les identifiants non archives de l'entite, VERROUILLES. Le verrou couvre la
#  reecriture d'ordre entiere : sans lui, une creation concurrente s'inserirait
#  au rang `max + 1` que la phase 1 vient de liberer.
_IDENTIFIANTS_A_REORDONNER: Final = text(
    """
    SELECT id
      FROM internal_link
     WHERE entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

#  **PHASE 1 DE LA REECRITURE D'ORDRE, ET LE DECALAGE EST DERIVE *EN SQL*.**
#
#  Ajouter une meme constante a tous les rangs preserve leur distinction, donc
#  l'index unique tient pendant l'etat intermediaire -- a condition que la plage
#  d'arrivee ne rencontre ni les rangs encore en place, ni les rangs finaux.
#
#  **`len(ordre)` NE SUFFIT PAS, ET C'EST LE DEFAUT `T8-1`.** Il ne vaut que si
#  les rangs vivants sont `0..n-1` sans trou -- ce que l'archivage d'un lien
#  detruit, son rang restant pris. Mesure du 22/09/2026 :
#
#      vivants  archives  decalage = n      decalage = max + 1
#      [0,1,2]  []        [3,4,5]  ok       [3,4,5]  ok
#      [0,2]    [1]       [2,4]    **COLLISION** : 2 est encore pris
#      [0,3]    [1,2]     [2,5]    ok       [4,7]  ok
#
#  Le defaut est donc **NON DETERMINISTE** : il depend des rangs archives, et la
#  troisieme ligne passe. C'est ce qui le rend pire qu'un echec franc.
#
#  `max + 1` est toujours sur : les rangs decales valent tous plus que le maximum
#  vivant, donc plus que n'importe quel rang encore en place ; et `max >= n - 1`
#  pour n rangs distincts et positifs, donc `max + 1 >= n`, donc au-dessus de
#  tous les rangs finaux `0..n-1`. La contrainte `ordre_positif` est tenue elle
#  aussi, le decalage etant positif.
#
#  **IL EST DERIVE DANS LA REQUETE, ET NON PASSE EN PARAMETRE**, parce que c'est
#  la seule forme ou l'appelant ne peut pas se tromper (§7.35). La sous-requete
#  lit l'instantane d'AVANT l'ordre, donc une valeur stable.
#
#  Les lignes archivees ne sont ni lues ni decalees : l'index unique etant
#  PARTIEL sur `archived_at IS NULL`, elles n'y figurent pas et ne peuvent donc
#  entrer en collision avec rien.
_DECALER_LES_RANGS: Final = text(
    """
    UPDATE internal_link
       SET display_order = display_order + (
             SELECT max(display_order) + 1
               FROM internal_link
              WHERE entity_id = :entite AND archived_at IS NULL
           )
     WHERE entity_id = :entite AND archived_at IS NULL
    """
)

_POSER_LE_RANG: Final = text(
    """
    UPDATE internal_link
       SET display_order = :rang,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :lien AND entity_id = :entite AND archived_at IS NULL
    """
)


def valider_une_url(url: str) -> str:
    """Refuser tout ce qui n'est pas une adresse `https` complete — §15.3, `DEC-587`.

    Rend l'adresse **normalisee** : espaces de tete et de queue retires, et
    segment de protocole en minuscules. Rien d'autre n'est touche -- le chemin,
    la requete et le fragment sont rendus a l'octet pres, parce qu'un serveur peut
    y etre sensible a la casse.

    **LES CINQ REFUS SONT DISTINCTS, ET AUCUN N'EST DECORATIF** :

        url_illisible         aucun `:`, donc aucun protocole -- « hub.exalt.test »
        url_ambigue           le protocole tape et le protocole LU different
        url_non_chiffree      exactement `http`
        url_protocole_refuse  tout autre protocole hors de la liste
        url_sans_hote         protocole autorise, mais aucun serveur -- « https:x »

    Le dernier est celui que la mesure a trouve, et il est le seul qu'une lecture
    naive de « liste de protocoles autorises » aurait omis : voir l'en-tete.

    **AUCUN DE CES REFUS NE PARLE DU CONTENU DE LA PAGE VISEE.** Ce module valide
    une ADRESSE ; il n'ouvre aucune connexion, ne resout aucun nom, ne suit aucune
    redirection. Le faire serait un appel sortant depuis une requete d'ecriture,
    donc un vecteur de saturation -- et le §7.33 a mesure ce que coute une attente
    reseau sur un chemin de requete.
    """
    propre = url.strip()
    separateur = propre.find(":")
    if separateur <= 0:
        #  Ni `//hote/chemin` -- protocole relatif, que le §15.3 n'autorise pas --
        #  ni `hote/chemin`, qui n'adresse rien hors d'un navigateur deja pose sur
        #  une page. `:` en tete (`separateur == 0`) ne laisse aucun protocole.
        raise ErreurApplicative(
            code=CODE_URL_ILLISIBLE,
            message=MESSAGE_URL_ILLISIBLE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
        )

    decoupage = urlsplit(propre)
    protocole = decoupage.scheme

    #  **LE PROTOCOLE TAPE DOIT ETRE CELUI QUI A ETE LU**, a la casse pres.
    #  `urlsplit` retire silencieusement des caracteres de controle : mesure du
    #  22/09/2026, « java\\nscript: » et « java\\tscript: » rendent tous deux le
    #  protocole `javascript`. Comparer ici EVITE de recopier la liste interne de
    #  CPython, qui vieillirait a la premiere version (§7.27) -- et refuse toute
    #  divergence future sans avoir a la connaitre.
    if propre[:separateur].lower() != protocole:
        raise ErreurApplicative(
            code=CODE_URL_AMBIGUE,
            message=MESSAGE_URL_AMBIGUE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
        )

    if protocole == PROTOCOLE_EN_CLAIR:
        raise ErreurApplicative(
            code=CODE_URL_NON_CHIFFREE,
            message=MESSAGE_URL_NON_CHIFFREE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
        )

    if protocole not in PROTOCOLES_AUTORISES:
        raise ErreurApplicative(
            code=CODE_URL_PROTOCOLE_REFUSE,
            message=MESSAGE_URL_PROTOCOLE_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
            #  Le protocole refuse est RENDU : l'auteur doit pouvoir le
            #  reconnaitre, et il vient de sa propre saisie -- rien de sensible.
            details={"protocole": protocole},
        )

    if not decoupage.netloc:
        raise ErreurApplicative(
            code=CODE_URL_SANS_HOTE,
            message=MESSAGE_URL_SANS_HOTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
        )

    #  Seul le segment de protocole est minusculise. `propre[separateur:]` est
    #  rendu tel quel, et l'egalite verifiee ci-dessus garantit que la frontiere
    #  est exacte.
    return protocole + propre[separateur:]


def valider_un_type_de_lien(type_de_lien: str) -> str:
    """Refuser un type hors du §15.3 — `HUB`, `ACADEMY`, `SHAREPOINT`, `OTHER`.

    **LE PERIMETRE EST DERIVE DE L'ENUMERATION** (§7.27) : un cinquieme type y
    entrerait sans que personne y pense. La base porte la meme regle en
    `ck_internal_link_link_type_valide` ; ce refus-ci existe pour en faire un 422
    nomme plutot qu'un 500, et parce que ce module est appelable hors HTTP.
    """
    if type_de_lien not in TYPES_DE_LIEN:
        raise ErreurApplicative(
            code=CODE_TYPE_DE_LIEN_REFUSE,
            message=MESSAGE_TYPE_DE_LIEN_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="type_de_lien",
            details={"types_autorises": list(TYPES_DE_LIEN)},
        )
    return type_de_lien


def _lire(ligne: tuple[object, ...]) -> LienInterne:
    """Une ligne du `SELECT` commun, dans l'ordre de `_LIENS`."""
    return LienInterne(
        identifiant=ligne[0],  # type: ignore[arg-type]
        libelle=str(ligne[1]),
        url=str(ligne[2]),
        type_de_lien=str(ligne[3]),
        description=None if ligne[4] is None else str(ligne[4]),
        reference_d_icone=None if ligne[5] is None else str(ligne[5]),
        rang=int(ligne[6]),  # type: ignore[call-overload]
        actif=bool(ligne[7]),
        version=int(ligne[8]),  # type: ignore[call-overload]
    )


def lister_les_liens(
    connexion: Connection, *, entite: uuid.UUID, inclure_les_inactifs: bool
) -> tuple[LienInterne, ...]:
    """Les liens internes d'une entite, dans leur ordre d'affichage — §15.3.

    `inclure_les_inactifs` distingue les DEUX audiences, et chaque route n'en
    emploie qu'une : l'accueil ne sert que les actifs -- c'est la raison d'etre du
    champ `active` --, l'ecran de gestion voit les deux, sans quoi desactiver
    serait un aller sans retour.

    **L'ORDRE EST TOTAL**, l'index unique de `T1` interdisant deux rangs egaux
    parmi les non archives. Sans lui, `ORDER BY display_order` rendrait un ordre
    dependant du plan choisi -- c'est le defaut que `T2` du LOT 5 a corrige sur le
    trombinoscope, ou une ligne pouvait paraitre deux fois ou jamais.
    """
    filtre = "" if inclure_les_inactifs else "AND active"
    lignes = connexion.execute(
        text(_LIENS.format(filtre_actif=filtre)), {"entite": entite}
    ).fetchall()
    return tuple(_lire(tuple(ligne)) for ligne in lignes)


def _relire(connexion: Connection, *, entite: uuid.UUID, lien: uuid.UUID) -> LienInterne:
    """Relire un lien apres ecriture, par la MEME requete que la lecture.

    **RELU PLUTOT QU'ASSEMBLE A PARTIR DE LA DEMANDE**, et ce n'est pas un detour :
    un objet construit depuis ce que l'appelant a envoye affirmerait ce qu'on a
    voulu ecrire, pas ce que la base porte. `version` et `display_order` ne
    viennent d'ailleurs pas de la demande du tout.
    """
    ligne = connexion.execute(
        text(_LIENS.format(filtre_actif="AND id = :lien")), {"entite": entite, "lien": lien}
    ).one()
    return _lire(tuple(ligne))


def creer_un_lien(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    libelle: str,
    url: str,
    type_de_lien: str,
    description: str | None,
    reference_d_icone: str | None,
    actif: bool,
    instant: dt.datetime,
) -> LienInterne:
    """Creer un lien interne, EN QUEUE de liste — §13, §19, modele §15.3.

    L'appelant a deja prouve son role : ce module ne rejuge pas la grille. Il
    refuse en revanche ce qu'aucune grille ne couvre -- une URL hors liste, un
    type inconnu --, parce qu'il est appelable hors HTTP (corollaire du §7.37).

    **AUCUN PARAMETRE DE RANG**, et c'est la mesure de permutation qui l'exige :
    voir l'en-tete du module.
    """
    url_validee = valider_une_url(url)
    valider_un_type_de_lien(type_de_lien)

    rang = int(connexion.execute(_RANG_SUIVANT, {"entite": entite}).scalar_one())
    try:
        identifiant = connexion.execute(
            _INSERER_UN_LIEN,
            {
                "entite": entite,
                "libelle": libelle,
                "url": url_validee,
                "type_de_lien": type_de_lien,
                "description": description,
                "icone": reference_d_icone,
                "rang": rang,
                "actif": actif,
                "acteur": acteur,
                "instant": instant,
            },
        ).one()[0]
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur

    #  LOT 10, `T4` : aucune enum Python ne nomme les actions sur un lien
    #  interne (a la difference des pages, §7.27 n'a rien a reutiliser ici) --
    #  `action_code` est donc un litteral, meme discipline que `T3` pour les
    #  actions sans vocabulaire existant.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="lien_cree",
        resource_type="internal_link",
        resource_reference=identifiant,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation du lien interne « {libelle} »",
    )

    return _relire(connexion, entite=entite, lien=identifiant)


def modifier_un_lien(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lien: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    libelle: str,
    url: str,
    type_de_lien: str,
    description: str | None,
    reference_d_icone: str | None,
    actif: bool,
    instant: dt.datetime,
) -> LienInterne:
    """Remplacer la definition d'un lien — §19 « Modifier les liens internes ».

    **`actif` EST UN CHAMP DE CETTE ROUTE, ET C'EST LA SEULE FACON DE RETIRER UN
    LIEN.** Le §15.3 declare `active` a cote de `archived_at` ; `T1` a refuse de
    les fondre. Aucune ligne du §13 ni du §19 ne nomme l'archivage d'un lien, et
    en inventer une serait le §6.5.

    **LE RANG N'EST PAS TOUCHE** : il appartient a l'ordre de la liste, que
    `reordonner_les_liens` seule reecrit.
    """
    url_validee = valider_une_url(url)
    valider_un_type_de_lien(type_de_lien)

    etat = connexion.execute(_LIEN_A_MODIFIER, {"lien": lien, "entite": entite}).one_or_none()
    if etat is None:
        #  Le lien n'existe pas, il appartient a une autre entite, ou il a ete
        #  archive. **UN SEUL GABARIT POUR LES TROIS** : le §2.5 pose le refus par
        #  defaut, et distinguer apprendrait l'existence d'un lien d'une autre
        #  entite. L'appelant a prouve un role dans CETTE entite, pas ailleurs.
        raise ErreurApplicative(
            code=CODE_LIEN_INTROUVABLE,
            message=MESSAGE_LIEN_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )

    if int(etat[0]) != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": int(etat[0])},
        )

    try:
        connexion.execute(
            _METTRE_A_JOUR_UN_LIEN,
            {
                "lien": lien,
                "entite": entite,
                "libelle": libelle,
                "url": url_validee,
                "type_de_lien": type_de_lien,
                "description": description,
                "icone": reference_d_icone,
                "actif": actif,
                "acteur": acteur,
                "instant": instant,
            },
        ).one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur

    #  LOT 10, `T4` : meme litteral que `creer_un_lien`, action symetrique.
    #  `actif` est porte dans `new_values` : c'est le SEUL moyen de retirer un
    #  lien (§19), donc la seule trace qui distingue une modification ordinaire
    #  d'un retrait.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="lien_modifie",
        resource_type="internal_link",
        resource_reference=lien,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Modification du lien interne « {libelle} »",
        new_values={"libelle": libelle, "url": url_validee, "actif": actif},
    )

    return _relire(connexion, entite=entite, lien=lien)


def reordonner_les_liens(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    ordre: tuple[uuid.UUID, ...],
    instant: dt.datetime,
) -> tuple[LienInterne, ...]:
    """Reecrire l'ordre d'affichage — modele §15.3, `display_order`.

    **LE RANG VAUT L'INDEX DE LA LISTE SOUMISE**, jamais une valeur envoyee : deux
    liens de meme rang sont donc **inexprimables** plutot que refuses (§7.35),
    exactement comme les blocs de `T6`.

    **LA LISTE DOIT ETRE EXHAUSTIVE**, et c'est ce que `ordre_incomplet` exige :
    exactement une fois chacun des liens non archives de l'entite. Une liste
    partielle laisserait des rangs indetermines -- ou, pire, une permutation
    partielle qui violerait l'index unique en rendant un 500 la ou l'appelant a
    simplement oublie un lien.

    **DEUX TEMPS, ET LE DECALAGE EST DERIVE EN SQL.** Mesure du 22/09/2026 : un
    echange en un seul `UPDATE` est REFUSE par
    `uq_internal_link_entity_ordre_non_archive`. Le decalage vaut `max + 1` sur
    les rangs vivants, et surement pas leur NOMBRE -- voir `_DECALER_LES_RANGS`,
    defaut `T8-1`, que l'archivage d'un lien fait mordre.
    """
    existants = tuple(
        ligne[0] for ligne in connexion.execute(_IDENTIFIANTS_A_REORDONNER, {"entite": entite})
    )
    #  **LA COMPARAISON PORTE SUR LES MULTI-ENSEMBLES, PAS SUR LES ENSEMBLES.**
    #  `set(ordre) == set(existants)` serait satisfait par une liste qui nomme
    #  deux fois le meme lien et en omet un autre : deux rangs seraient alors
    #  ecrits sur la meme ligne, et un lien garderait son rang decale.
    if sorted(map(str, ordre)) != sorted(map(str, existants)):
        raise ErreurApplicative(
            code=CODE_ORDRE_INCOMPLET,
            message=MESSAGE_ORDRE_INCOMPLET,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="ordre",
            details={"attendus": len(existants), "recus": len(ordre)},
        )

    if not ordre:
        #  Rien a reordonner. Le `UPDATE` de decalage serait un ordre sur zero
        #  ligne, donc sans effet -- mais le dire ici evite de laisser croire que
        #  la boucle qui suit a travaille.
        return ()

    connexion.execute(_DECALER_LES_RANGS, {"entite": entite})
    for rang, lien in enumerate(ordre):
        connexion.execute(
            _POSER_LE_RANG,
            {
                "lien": lien,
                "entite": entite,
                "rang": rang,
                "acteur": acteur,
                "instant": instant,
            },
        )

    #  LOT 10, `T4` : UN SEUL `audit_event` pour l'appel entier -- « reordonner
    #  les liens » est UNE action metier sur l'ensemble des liens vivants de
    #  l'entite, jamais un evenement par lien deplace. `resource_reference`
    #  reste absent : aucun lien unique ne porte cette action, qui touche
    #  l'entite entiere.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="liens_reordonnes",
        resource_type="internal_link",
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Reordonnancement de {len(ordre)} lien(s) interne(s)",
        new_values={"ordre": [str(identifiant) for identifiant in ordre]},
    )

    return lister_les_liens(connexion, entite=entite, inclure_les_inactifs=True)


def _traduire_un_refus_de_la_base(erreur: IntegrityError | DataError) -> ErreurApplicative:
    """Traduire un refus du schema en reponse du §18.3.

    **LE DISCRIMINANT EST LE NOM DE LA CONTRAINTE**, une donnee **structuree** du
    protocole PostgreSQL -- `diag.constraint_name` -- et non le texte du message,
    qui est localise et change de version en version. Meme parti que `T6` et `T7`.

    **UNE SEULE CONTRAINTE EST TRADUITE, ET SA TRADUCTION NE DEVRAIT JAMAIS
    SORTIR.** `ck_internal_link_url_https` est le PLANCHER pose par la migration
    `0019` ; `valider_une_url` refuse la meme chose plus tot, et plus finement. Si
    ce chemin sortait, ce serait que les deux etages ont diverge -- un test exige
    qu'ils concordent, et le 422 rendu ici vaut mieux qu'un 500.

    **CE QUI N'EST PAS RECONNU REMONTE**, et c'est voulu : une violation de
    `uq_internal_link_entity_ordre_non_archive` signalerait un defaut de CE module,
    le rang etant derive et jamais recu. Un 500 bruyant vaut mieux qu'un 422 qui
    accuserait l'appelant a tort (§7.20).
    """
    diagnostic = getattr(erreur.orig, "diag", None)
    contrainte = str(getattr(diagnostic, "constraint_name", "") or "")

    if contrainte == CONTRAINTE_URL_HTTPS:
        return ErreurApplicative(
            code=CODE_URL_PROTOCOLE_REFUSE,
            message=MESSAGE_URL_PROTOCOLE_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="url",
        )
    raise erreur
