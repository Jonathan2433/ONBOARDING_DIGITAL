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
