"""Qui peut LIRE, COMPLETER ou VALIDER la fiche d'arrivee — matrice §7, LOT 7.

CE QUE LA MATRICE DONNE, ET LA CELLULE QUI SURPREND

  §7, TROIS lignes rendent la MEME grille — « Consulter sa fiche non publiee »,
  « Consulter les informations preremplies » (`T2`) et « Completer photo,
  presentation et fun fact » (`T3`) :

      NEW      Soi
      DSM      —
      ESM      Support (Entite)
      BOOST    Support cercle (Cercle)
      OFFICE   —
      ADM-E    Support (Entite)
      SUPER    Support (Global)

  **`DSM` EST A TIRET ICI, ALORS QU'IL PORTE « CONSULTANTS » AILLEURS DANS LA
  MEME ANNEXE** — §8.1 « Consulter le parcours d'un collaborateur », §7
  « Modifier les informations organisationnelles ». Ce n'est pas une
  incoherence a corriger : la cellule de CETTE ligne, sur CETTE ressource, dit
  ce qu'elle dit. La confondre avec la ligne voisine accorderait un droit que
  la matrice refuse en toutes lettres — exactement le piege que le §2.1 de
  `fiche-lot-7.md` nomme pour `§8.1`.

  **`Support` N'EST NULLE PART DANS LA LEGENDE §4** — meme piege que `§7.45`/
  `§7.46` : un mot employe comme valeur, absent de la legende. Cherche partout
  dans le corpus (§7 lignes 186-187, `photo_authorization.source` du modele
  §12.2 : `self_service`/`admin_support`/`migration`), rien ne le definit
  formellement au-dela de la portee deja lisible — la MEME portee que `Entite`/
  `Cercle`/`Global` ailleurs sur la meme ligne, l'unique difference etant
  semantique : une assistance sur la fiche d'un AUTRE, jamais une portee plus
  large. Aucune regle supplementaire (motif, audit) n'est ecrite nulle part
  pour ce mot : en inventer une serait §6.5.

  **PARCE QUE LES TROIS LIGNES CONCORDENT, LE MEME CALCUL LES GOUVERNE TOUTES
  LES TROIS** — §7.27, une regle, pas trois copies qui divergeraient au premier
  ajout. `peut_completer_la_fiche_arrivee` appelle le meme helper prive que
  `peut_lire_la_fiche_arrivee`.

  **LA LIGNE « VALIDER ET PUBLIER » DIVERGE, ET C'EST LA SEULE.** `BOOST` y est
  a TIRET, alors qu'il porte « Support cercle » sur les deux lignes
  precedentes — un Booster peut aider a completer, jamais valider ni publier.
  `peut_valider_et_publier_la_fiche_arrivee` est donc une fonction SEPAREE, qui
  n'appelle PAS le helper des deux premieres lignes.

  **UNE QUATRIEME LIGNE EXISTE, « CORRIGER APRES PUBLICATION », ET SA GRILLE
  S'INVERSE SUR `NEW` ET `DSM` :**

      NEW      —          (pouvait completer AVANT publication, plus apres)
      DSM      Consultants (etait a tiret AVANT publication, plus apres)
      ESM      Entite
      BOOST    Cercle
      OFFICE   —
      ADM-E    Entite
      SUPER    Global

  Ce n'est pas une incoherence : avant publication, la fiche appartient encore
  au nouvel arrivant (`Soi`) et les responsables n'AIDENT que par exception
  (`Support`) ; apres publication, la fiche est un document officiel que seuls
  les responsables corrigent — le nouvel arrivant ne le peut plus (§6.2, « le
  collaborateur ne peut plus modifier directement son profil »), et le DSM, qui
  etait exclu de l'aide a la redaction, retrouve son droit habituel de
  correction sur ses consultants. `peut_corriger_la_fiche_arrivee_apres_publication`
  est une troisieme fonction separee, avec son propre controle DSM — le meme
  motif SQL que `app/permissions/perimetre.py::_RATTACHE_A_CE_DSM`, recopie ici
  plutot qu'importe : une dependance croisee vers un module prive d'un autre
  domaine serait pire qu'une petite requete repetee (§7.27).

`NEW` N'EST PAS UN ROLE DE `RoleDeLaMatrice`

  « Soi » n'est pas une portee organisationnelle, c'est une egalite entre
  l'acteur et la personne de la cible. Elle se vérifie donc AVANT toute
  resolution de role, sans avoir besoin d'interroger `resoudre_les_permissions`.

LE CATALOGUE DES TACHES — matrice §9, `T4`

  **CINQ DES SEPT LIGNES DU §9 PARTAGENT UNE SEULE GRILLE**, celle de « Creer
  une tache de reference » et « Reutiliser une tache de reference » :

      DSM      Consultants
      ESM      Entite
      BOOST    Cercle
      OFFICE   —
      ADM-E    Entite
      SUPER    Global

  Les deux lignes ecartees — « Consulter les modeles publies » (une grille
  plus large, sans objet pour le catalogue lui-meme) et « Restaurer une
  version » (`Conditionnel` pour ESM, `ECART-066`, hors perimetre de `T4`) —
  ne portent pas sur `onboarding_task_reference`.

  **`Consultants` ET `Cercle` NE PEUVENT PAS RESTREINDRE EN DECA DE L'ENTITE
  ICI, ET CE N'EST PAS UNE LECTURE LARGE — C'EST UNE LIMITE DE LA TABLE.**
  `onboarding_task_reference` (modele §13.1) ne porte QUE `entity_id`,
  nullable pour le global : ni `scope_circle_id` ni `scope_person_id`, a la
  difference d'`onboarding_template` (§13.2) qui les recevra a `T5`. Une tache
  de reference n'est rattachee a AUCUN cercle ni AUCUN DSM en particulier —
  contrairement a `arrival_profile`, ou `_MEMBRE_DU_CERCLE_DU_BOOSTER`
  verifie un rattachement REEL entre l'acteur et la CIBLE. Il n'y a ici
  aucune cible de cette nature : une tache de reference n'appartient a
  personne. Le DSM et le Booster recoivent donc, pour CETTE ressource
  precisement, la MEME portee que l'ESM et l'administrateur d'entite : LEUR
  entite. Ajouter une colonne pour distinguer plus finement serait une
  invention que le corpus ne demande pas (§6.5) ; refuser purement et
  simplement DSM/BOOST en serait une autre, tout aussi fausse — la matrice
  leur accorde un droit, elle ne dit simplement pas comment le reduire plus
  loin que l'entite pour cette table-la.

  **SEUL `SUPER` ATTEINT `Global`.** Aucune requete SQL n'est necessaire pour
  le distinguer : `resoudre_les_permissions` ajoute `SUPER_ADMINISTRATEUR`
  SANS condition d'entite (§5.1, l'exception globale), donc sa presence dans
  `roles` suffit — comme pour `peut_valider_et_publier_la_fiche_arrivee`.

LES MODELES ET LEURS VERSIONS — matrice §9, `T5`

  **ICI, CONTRAIREMENT AU CATALOGUE, `Consultants` ET `Cercle` NE SE REDUISENT
  PAS A L'ENTITE.** `onboarding_template` (modele §13.2) porte deux colonnes
  que `onboarding_task_reference` n'a pas : `scope_person_id` (le DSM, si
  `scope_type = 'DSM'`) et `scope_circle_id` (le cercle, si `scope_type =
  'CIRCLE'`). La limite qui collapsait le catalogue a l'entite au `T4`
  n'existe plus ici : un DSM cree un modele pour SES PROPRES consultants, un
  Booster pour SON PROPRE cercle — jamais pour un autre.

      Creer un modele / une nouvelle version / ajouter des taches
      DSM      Consultants   (scope_type=DSM, scope_person_id = LUI-MEME)
      ESM      Entite        (scope_type=ENTITY)
      BOOST    Cercle        (scope_type=CIRCLE, scope_circle_id = SON cercle)
      OFFICE   —
      ADM-E    Entite        (scope_type=ENTITY)
      SUPER    Global        (scope_type=GLOBAL)

  **TROIS DES QUATRE LIGNES DU §9 PARTAGENT CETTE MEME GRILLE** — « Creer un
  modele », « Creer une nouvelle version », « Ajouter ou reordonner des
  taches » — exactement le motif qui a factorise les lignes du catalogue en
  `T4` : une seule fonction, `peut_gerer_un_modele_de_cette_portee`, sert les
  trois, appliquee soit a la portee DECLAREE (creation), soit a la portee DEJA
  ECRITE du modele existant (version, taches).

  **`ESM`/`ADM-E`/`SUPER` NE SONT PAS BORNES A LEUR PROPRE SCOPE_TYPE**, et
  c'est le MEME parti que `ROLES_DE_PORTEE_ENTITE` dans
  `app/content/perimetre.py` (LOT 6) : un role de portee ENTITE gere aussi ce
  qu'un role LOCAL gererait, jamais l'inverse. Un ESM peut donc creer un
  modele `DSM` pour n'importe quel DSM ACTIF de son entite, ou `CIRCLE` pour
  n'importe quel cercle de son entite — le modele §13.2 l'exige d'ailleurs
  structurellement : « un scope DSM exige un DSM actif dans l'entite », « un
  scope CIRCLE exige un cercle de la meme entite » — DEUX RESIDUS NOMMES PAR
  `T1`, faute de cle composite sure (voir `modeles.py`), INSTRUITS ICI PAR LE
  SERVICE plutot que par la base : `peut_gerer_un_modele_de_cette_portee` lit
  `framework_responsibility_assignment`/`circle` et refuse en silence — UN
  SEUL gabarit de refus, `acces_refuse`, que la cause soit un role insuffisant
  ou une cible invalide (§2.5, meme discipline que `resoudre_le_perimetre_
  editorial`).

  **UN DSM OU UN BOOSTER, EUX, SONT BORNES A EUX-MEMES.** Un DSM sans role de
  portee ENTITE ne peut creer un modele `DSM` QUE pour `scope_person_id ==
  lui-meme` — §9.1 du corpus, « Un modele cree par un DSM doit etre destine a
  SES consultants ». Un Booster ne peut creer un modele `CIRCLE` QUE pour un
  cercle ou il est BOOSTER ACTIF — verifie sur `framework_responsibility_
  assignment`, jamais sur la seule appartenance a `roles` qui ne dit RIEN du
  cercle precis.

LA RESTAURATION D'UNE VERSION — matrice §9, `T6`, `ECART-066` RESOLU

  Publier et archiver une version REUTILISENT `peut_gerer_un_modele_de_cette_
  portee` tel quel — memes trois lignes a la meme grille que la creation.
  « Restaurer une version » est la SEULE ligne du §9 a une grille differente :

      DSM      —             (refuse, MEME sur SON PROPRE modele)
      ESM      Entite        (`Conditionnel` dans la matrice — RESOLU ci-dessous)
      BOOST    —             (refuse, MEME sur SON PROPRE cercle)
      OFFICE   —
      ADM-E    Entite
      SUPER    Global

  **`ECART-066` : LA MATRICE DISAIT `Conditionnel` POUR `ESM` SANS DIRE A
  QUOI.** `ARB-DROIT-003` definit la restauration fonctionnelle pour cinq
  ressources — profil, contenu, evenement, cercle, bureau — et ne nomme ni un
  modele d'onboarding ni un parcours. Question posee a Jonathan avant `T6`,
  comme le recommandait `docs/decisions/registre-ecarts.md` : arbitrage du
  26/09/2026, l'ESM restaure librement DANS SON ENTITE, meme regime que les
  cinq autres ressources d'`ARB-DROIT-003`.

  **`DSM`/`BOOST` RESTENT REFUSES EN BLOC, ET CE N'EST PAS UN OUBLI.** A la
  difference des trois autres lignes du §9, la matrice met `DSM` et `BOOST` a
  TIRET sur « Restaurer une version » — pas de sous-cas « son propre modele ».
  `peut_restaurer_une_version_de_modele` n'a donc PAS besoin de lire
  `framework_responsibility_assignment` ni `circle` : la portee du modele
  (`GLOBAL` ou non) et l'ensemble `roles` de l'acteur suffisent — aucune
  requete supplementaire, contrairement a `peut_gerer_un_modele_de_cette_
  portee`.

LE PARCOURS D'UN COLLABORATEUR — matrice §8.1, `T7`

  **`DSM` A ICI « CONSULTANTS » PLEIN, ET C'EST LA TROISIEME GRILLE DU
  MODULE.** Sur la fiche d'arrivee NON PUBLIEE (`T2`), `DSM` est a TIRET ; sur
  le parcours d'un collaborateur (§8.1), il porte le MEME droit qu'ESM/ADM-E/
  SUPER a l'echelle de SES consultants — piege n°1 de `fiche-lot-7.md` §2.1,
  ne pas confondre les lignes. `peut_lire_le_parcours_onboarding` et
  `peut_affecter_un_parcours_onboarding` reutilisent `_RATTACHE_A_CE_DSM` et
  `_MEMBRE_DU_CERCLE_DU_BOOSTER`, deja posees pour `T3` : meme regle de
  rattachement, jamais une troisieme requete (§7.27).

  **« AFFECTER » N'A PAS DE `Soi` : `NEW` EST A TIRET SUR CETTE LIGNE
  PRECISE**, contrairement a « Consulter son parcours ». Les deux fonctions
  partagent donc `_dans_le_perimetre_du_parcours`, et seule la lecture ajoute
  le raccourci `acteur == cible_personne` par-dessus.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.permissions.services import RoleDeLaMatrice

#  §8.4 : le type qui porte le cercle du Booster. Litteral, comme
#  `app/permissions/perimetre.py` le fait deja pour le meme type — une
#  dependance croisee vers un module prive d'un autre domaine serait pire
#  qu'une constante repetee (§7.27, l'un ou l'autre cout, jamais les deux).
_TYPE_BOOSTER: Final[str] = "BOOSTER"

#  §7 « Cercle » : un membre — principal OU secondaire — du cercle dont
#  l'acteur est Booster. Aucune ligne du §7 ne restreint au seul principal,
#  contrairement a la lecture ECRITE du §6.1 pour d'autres actions.
_MEMBRE_DU_CERCLE_DU_BOOSTER: Final[str] = """
SELECT 1
FROM framework_responsibility_assignment AS fra
JOIN circle_membership AS cm
  ON cm.circle_id = fra.circle_id AND cm.entity_id = fra.entity_id
WHERE fra.person_id = :acteur AND fra.entity_id = :entite
  AND fra.responsibility_type = :type_booster
  AND fra.archived_at IS NULL AND fra.period @> :instant
  AND cm.entity_membership_id = :cible
  AND cm.archived_at IS NULL AND cm.period @> :instant
"""

_ROLES_ENTITE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §7 « Consultants » — le meme motif que `app/permissions/perimetre.py::
#  _RATTACHE_A_CE_DSM`, recopie et non importe (§7.27, voir l'en-tete).
_RATTACHE_A_CE_DSM: Final[str] = """
SELECT 1 FROM dsm_assignment
WHERE consultant_membership_id = :cible AND dsm_person_id = :acteur
  AND entity_id = :entite AND archived_at IS NULL
  AND period @> :instant
"""


def _dans_le_perimetre_personnel_non_publie(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """La grille commune a « Consulter » (x2) et « Completer » — §7, `T2`/`T3`.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est deja
    applique : hors de son entite principale une personne n'a que `EMP`, qui
    n'ouvre rien ici (§7 le met a tiret, comme `DSM` et `OFFICE`).
    """
    if acteur == cible_personne:
        return True
    if roles & _ROLES_ENTITE:
        return True
    if RoleDeLaMatrice.BOOSTER in roles:
        ligne = connexion.execute(
            text(_MEMBRE_DU_CERCLE_DU_BOOSTER),
            {
                "acteur": acteur,
                "entite": entite,
                "cible": cible_appartenance,
                "type_booster": _TYPE_BOOSTER,
                "instant": instant,
            },
        ).first()
        if ligne is not None:
            return True
    return False


def peut_lire_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il lire la fiche d'arrivee de `cible_appartenance` ? `T2`."""
    return _dans_le_perimetre_personnel_non_publie(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        cible_personne=cible_personne,
        roles=roles,
        instant=instant,
    )


def peut_completer_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il completer photo/presentation/fun fact ? `T3`.

    MEME GRILLE QUE LA LECTURE — voir l'en-tete du module. `Support` et
    `Support cercle` couvrent EXACTEMENT `Entite` et `Cercle` : aucune regle
    supplementaire (motif, fenetre temporelle) n'est ecrite au corpus.
    """
    return _dans_le_perimetre_personnel_non_publie(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        cible_personne=cible_personne,
        roles=roles,
        instant=instant,
    )


def peut_valider_et_publier_la_fiche_arrivee(
    *,
    acteur: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
) -> bool:
    """L'acteur peut-il valider (et donc publier) la fiche ? `T3`.

    **LA SEULE DES TROIS LIGNES DU §7 OU `BOOST` EST A TIRET.** Un Booster
    peut aider un membre de son cercle a completer sa fiche ; il ne peut ni la
    valider ni la publier a sa place — §7, ligne « Valider et publier ».
    Aucune requete SQL n'est necessaire ici : ni `Soi` ni `Support` (Entite/
    Global) ne dependent du cercle de la cible.
    """
    if acteur == cible_personne:
        return True
    return bool(roles & _ROLES_ENTITE)


def peut_corriger_la_fiche_arrivee_apres_publication(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il corriger une fiche DEJA PUBLIEE ? `T3`, correctif.

    **`NEW` N'A PLUS CE DROIT** — `Soi` gouvernait la completion avant
    publication ; apres, c'est le §6.2 qui parle : « le collaborateur ne peut
    plus modifier directement son profil ». **`DSM` L'A RETROUVE** — a tiret
    avant publication, il porte `Consultants` sur cette ligne. Voir l'en-tete
    du module.
    """
    if acteur == cible_personne:
        return False
    if roles & _ROLES_ENTITE:
        return True
    if RoleDeLaMatrice.DSM in roles:
        rattache = connexion.execute(
            text(_RATTACHE_A_CE_DSM),
            {"acteur": acteur, "entite": entite, "cible": cible_appartenance, "instant": instant},
        ).first()
        if rattache is not None:
            return True
    if RoleDeLaMatrice.BOOSTER in roles:
        ligne = connexion.execute(
            text(_MEMBRE_DU_CERCLE_DU_BOOSTER),
            {
                "acteur": acteur,
                "entite": entite,
                "cible": cible_appartenance,
                "type_booster": _TYPE_BOOSTER,
                "instant": instant,
            },
        ).first()
        if ligne is not None:
            return True
    return False


#  §9 : « Creer une tache de reference » et « Reutiliser une tache de
#  reference » — voir l'en-tete du module pour le motif qui reduit
#  `Consultants`/`Cercle` a l'entite pour CETTE table precisement.
ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


def peut_creer_une_tache_de_reference_globale(*, roles: frozenset[RoleDeLaMatrice]) -> bool:
    """Seul `SUPER` atteint `Global` — §9, colonne SUPER de « Creer une tache
    de reference ». Les quatre autres roles s'arretent a `Entite` (ou
    `Consultants`/`Cercle`, voir l'en-tete), jamais au global.

    Aucune requete n'est necessaire : `SUPER_ADMINISTRATEUR` est deja une
    portee de plateforme, garantie par `technical_role_assignment` et ajoutee
    par `resoudre_les_permissions` sans condition d'entite.
    """
    return RoleDeLaMatrice.SUPER_ADMINISTRATEUR in roles


#  §9 : « Creer un modele », « Creer une nouvelle version », « Ajouter ou
#  reordonner des taches » — voir l'en-tete pour la grille et le motif.
ROLES_DE_GESTION_DES_MODELES: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Les roles dont la portee couvre l'ENTITE entiere sur les modeles — §9,
#  colonnes ESM/ADM-E/SUPER. Meme parti que `ROLES_DE_PORTEE_ENTITE` de
#  `app/content/perimetre.py` (LOT 6) : un role d'entite gere aussi ce qu'un
#  role LOCAL (DSM, Booster) gererait, jamais l'inverse.
_ROLES_DE_PORTEE_ENTITE_DES_MODELES: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §13.2 : « un scope DSM exige un DSM actif dans l'entite ». Meme forme que
#  `_RATTACHE_A_CE_DSM`, mais SANS cible : ici on demande seulement si
#  `:personne` EST un DSM actif, pas si un consultant precis lui est rattache.
_DSM_ACTIF_DANS_L_ENTITE: Final[str] = """
SELECT 1 FROM framework_responsibility_assignment
WHERE person_id = :personne AND entity_id = :entite
  AND responsibility_type = 'DSM'
  AND archived_at IS NULL AND period @> :instant
"""

#  §8.4 : une responsabilite BOOSTER active de l'acteur, sur CE cercle precis
#  — jamais « l'acteur est Booster quelque part », qui autoriserait n'importe
#  quel cercle de l'entite au nom d'un role tenu ailleurs.
_BOOSTER_ACTIF_DE_CE_CERCLE: Final[str] = """
SELECT 1 FROM framework_responsibility_assignment
WHERE person_id = :acteur AND entity_id = :entite
  AND responsibility_type = :type_booster AND circle_id = :cercle
  AND archived_at IS NULL AND period @> :instant
"""

#  §13.2 : « un scope CIRCLE exige un cercle de la MEME entite ». Residuel
#  nomme par `T1` (`modeles.py`) faute de cle composite sure : instruit ici,
#  par le service, plutot qu'en base.
_CERCLE_DE_CETTE_ENTITE: Final[str] = """
SELECT 1 FROM circle WHERE id = :cercle AND entity_id = :entite
"""


def peut_gerer_un_modele_de_cette_portee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    portee: str,
    scope_person_id: uuid.UUID | None,
    scope_circle_id: uuid.UUID | None,
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il gerer (creer, versionner, composer) un modele de cette
    portee — §9, trois lignes a la meme grille (voir l'en-tete du module).

    `portee`/`scope_person_id`/`scope_circle_id` sont soit CEUX D'UN MODELE A
    CREER (declares par l'appelant), soit CEUX D'UN MODELE EXISTANT (lus en
    base avant de creer une version ou d'y composer des taches) : la fonction
    ne fait aucune difference entre les deux, exactement comme
    `resoudre_le_perimetre_editorial` ne distingue pas la page qu'il lit de la
    portee qu'elle porte deja.

    **UN SEUL BOOLEEN, JAMAIS UN MOTIF** — §2.5, refus par defaut : que la
    cause soit un role insuffisant, un DSM inactif ou un cercle d'une autre
    entite, l'appelant recoit le meme refus.
    """
    if portee == "GLOBAL":
        return RoleDeLaMatrice.SUPER_ADMINISTRATEUR in roles

    portee_entite = bool(roles & _ROLES_DE_PORTEE_ENTITE_DES_MODELES)

    if portee == "ENTITY":
        return portee_entite

    if portee == "DSM":
        if scope_person_id is None:
            return False
        if portee_entite:
            ligne = connexion.execute(
                text(_DSM_ACTIF_DANS_L_ENTITE),
                {"personne": scope_person_id, "entite": entite, "instant": instant},
            ).first()
            return ligne is not None
        if RoleDeLaMatrice.DSM not in roles:
            return False
        #  §9.1 : « destine a SES consultants » — jamais a un autre DSM, meme
        #  actif. Aucune requete necessaire : `roles` porte deja `DSM` pour
        #  CET acteur, dans CETTE entite (§5.1).
        return scope_person_id == acteur

    if portee == "CIRCLE":
        if scope_circle_id is None:
            return False
        if portee_entite:
            ligne = connexion.execute(
                text(_CERCLE_DE_CETTE_ENTITE), {"cercle": scope_circle_id, "entite": entite}
            ).first()
            return ligne is not None
        if RoleDeLaMatrice.BOOSTER not in roles:
            return False
        ligne = connexion.execute(
            text(_BOOSTER_ACTIF_DE_CE_CERCLE),
            {
                "acteur": acteur,
                "entite": entite,
                "type_booster": _TYPE_BOOSTER,
                "cercle": scope_circle_id,
                "instant": instant,
            },
        ).first()
        return ligne is not None

    return False


#  §9 « Restaurer une version », la garde COARSE de la route : DSM et BOOSTER
#  y sont a TIRET, jamais Conditionnel ni un sous-cas — ils sont donc EXCLUS de
#  ce role-set, contrairement a `ROLES_DE_GESTION_DES_MODELES`. Alias plutot que
#  litterale recopiee : memes trois roles que `_ROLES_DE_PORTEE_ENTITE_DES_
#  MODELES`, et une divergence future serait immediatement visible (§7.27).
ROLES_DE_RESTAURATION_DES_MODELES: Final[frozenset[RoleDeLaMatrice]] = (
    _ROLES_DE_PORTEE_ENTITE_DES_MODELES
)


def peut_restaurer_une_version_de_modele(*, portee: str, roles: frozenset[RoleDeLaMatrice]) -> bool:
    """`ECART-066` resolu : l'ESM restaure librement dans son entite, meme
    regime qu'`ADM-E`/`SUPER` — voir l'en-tete du module.

    **AUCUNE REQUETE** : DSM et BOOSTER etant refuses EN BLOC sur cette ligne
    precise (jamais bornes a « leur propre » modele), il n'y a rien a verifier
    au-dela de la portee et de l'ensemble de roles deja resolu.
    """
    if portee == "GLOBAL":
        return RoleDeLaMatrice.SUPER_ADMINISTRATEUR in roles
    return bool(roles & ROLES_DE_RESTAURATION_DES_MODELES)


#  §8.1 « Consulter le parcours d'un collaborateur » et « Affecter un
#  parcours » — memes trois roles rattachement-dependants que la fiche
#  d'arrivee (T2/T3), MAIS `DSM` y a « Consultants » PLEIN, jamais a tiret :
#  troisieme grille du module, distincte des deux precedentes. Voir `T7`.
ROLES_DU_PARCOURS_ONBOARDING: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


def _dans_le_perimetre_du_parcours(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """Entite (ESM/ADM-E/SUPER), DSM RATTACHE, ou Booster RATTACHE — §8.1.

    Reutilise `_RATTACHE_A_CE_DSM` et `_MEMBRE_DU_CERCLE_DU_BOOSTER`, deja
    posees par `T3` pour « Corriger apres publication » : la MEME regle de
    rattachement, jamais une troisieme requete (§7.27).
    """
    if roles & _ROLES_ENTITE:
        return True
    if RoleDeLaMatrice.DSM in roles:
        rattache = connexion.execute(
            text(_RATTACHE_A_CE_DSM),
            {"acteur": acteur, "entite": entite, "cible": cible_appartenance, "instant": instant},
        ).first()
        if rattache is not None:
            return True
    if RoleDeLaMatrice.BOOSTER in roles:
        ligne = connexion.execute(
            text(_MEMBRE_DU_CERCLE_DU_BOOSTER),
            {
                "acteur": acteur,
                "entite": entite,
                "cible": cible_appartenance,
                "type_booster": _TYPE_BOOSTER,
                "instant": instant,
            },
        ).first()
        if ligne is not None:
            return True
    return False


def peut_lire_le_parcours_onboarding(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """§8.1 « Consulter son parcours » (`Soi`) + « ... d'un collaborateur »."""
    if acteur == cible_personne:
        return True
    return _dans_le_perimetre_du_parcours(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        roles=roles,
        instant=instant,
    )


def peut_affecter_un_parcours_onboarding(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """§8.1 « Affecter un parcours » — PAS de `Soi` : `NEW` y est a tiret,
    contrairement a la consultation."""
    return _dans_le_perimetre_du_parcours(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        roles=roles,
        instant=instant,
    )
