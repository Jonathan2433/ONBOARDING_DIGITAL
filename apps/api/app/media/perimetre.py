"""Qui peut DEPOSER une photo, et qui peut en GERER l'autorisation — matrice §6.1/§7.

LOT 11, `T2`, stories `MVP-L11-US004`/`US005`.

DEUX LIGNES DU §6.1, DEUX PERMIS DIFFERENTS, ET AUCUN N'EST INVENTE ICI

  Le §6.1 porte deux lignes distinctes pour la photo d'un profil :

      « Ajouter ou remplacer une photo »
          EMP      —                    (plus de droit APRES validation, §6.2)
          NEW      Soi avant validation
          DSM      Consultants
          ESM      Entite
          BOOST    Cercle
          OFFICE   —
          ADM-E    Entite
          SUPER    Global

      « Enregistrer l'autorisation photo » / « Retirer l'autorisation photo »
          EMP      Soi lors de l'action
          NEW      Soi
          DSM      —
          ESM      Support
          BOOST    Support
          OFFICE   —
          ADM-E    Support
          SUPER    Support

  **LA PREMIERE LIGNE EST, MOT POUR MOT, LA MEME GRILLE QUE LES DEUX DEJA
  CODEES PAR LE LOT 7 POUR LA FICHE D'ARRIVEE** — `peut_completer_la_fiche_
  arrivee` (brouillon : `Soi`, `DSM` a tiret, `ESM`/`BOOST`/`ADM-E`/`SUPER` en
  soutien) et `peut_corriger_la_fiche_arrivee_apres_publication` (publiee :
  `NEW` perd le droit, `DSM` le retrouve en `Consultants`). Ce n'est pas une
  coincidence de forme : une photo EST un des trois champs que le §7
  « Completer »/« Corriger apres publication » couvre deja (« photo,
  presentation et fun fact »), simplement jamais ecrit faute de route
  d'upload — residu nomme par `app/onboarding/ecriture.py` (LOT 7, `T3`) et
  par le contrat (`completionDeLaFicheArrivee`). Recalculer cette grille ici
  serait une DEUXIEME copie qui diverge au premier ajout (§7.27) : `peut_
  deposer_une_photo` DISPATCHE donc sur les deux fonctions PUBLIQUES du
  module `app.onboarding.perimetre`, exactement comme `app/onboarding/
  routes.py::completer_la_fiche` le fait deja pour `short_intro`/`fun_fact`.

  **LA SECONDE LIGNE N'A PAS D'EQUIVALENT DEJA ECRIT**, et c'est une grille
  DIFFERENTE : `Soi` quel que soit l'etat de publication (y compris pour un
  EMP deja valide, ce que la premiere ligne refuse), `DSM` a tiret (jamais
  « Consultants », a aucun des deux etats), `ESM`/`BOOST`/`ADM-E`/`SUPER` en
  soutien SANS distinction avant/apres publication. `peut_gerer_l_
  autorisation_photo` la calcule donc elle-meme, en RECOPIANT — jamais en
  importanT — le motif prive `_MEMBRE_DU_CERCLE_DU_BOOSTER` d'`app.onboarding.
  perimetre` : meme discipline que ce module l'applique deja pour `_RATTACHE_
  A_CE_DSM` (recopie depuis `app.permissions.perimetre`), §7.27 — une
  dependance croisee vers un motif PRIVE d'un autre domaine serait pire qu'une
  petite requete repetee.

`Support` N'EST DEFINI NULLE PART DANS LA LEGENDE §4, ENCORE UNE FOIS

  Meme piege que `§7.45`/`§7.46`/le module `onboarding.perimetre` : chercher
  le mot dans tout le corpus montre qu'il denote exactement `Entite`/`Cercle`,
  la seule nuance etant semantique (une assistance sur la fiche d'un AUTRE).
  Aucune regle supplementaire (motif, audit, fenetre temporelle) n'est ecrite
  nulle part pour ce mot : en inventer une serait §6.5.

CE QUE LE MODELE LAISSAIT MUET, ET QUE CE LOT DOIT TRANCHER

  `app/media/modeles.py` (LOT 5, `T1`) note explicitement : « aucune unicite
  n'est posee sur `photo_authorization`... le service devra dire ce qu'il
  fait de deux autorisations actives ». C'est le decoupage de ce lot qui
  tranche enfin cette question, dans `app/media/autorisation.py` : voir son
  en-tete.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.onboarding.perimetre import (
    peut_completer_la_fiche_arrivee,
    peut_corriger_la_fiche_arrivee_apres_publication,
)
from app.permissions.services import RoleDeLaMatrice

#  Recopie de `app.onboarding.perimetre._TYPE_BOOSTER`/`_MEMBRE_DU_CERCLE_DU_
#  BOOSTER` — motif prive d'un autre domaine, §7.27 : voir l'en-tete du module.
_TYPE_BOOSTER: Final[str] = "BOOSTER"

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


def peut_deposer_une_photo(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
    fiche_publiee: bool,
) -> bool:
    """L'acteur peut-il deposer (ou remplacer) la photo de `cible_appartenance` ?

    `fiche_publiee` vient de la MEME lecture que la route (`FicheArrivee.
    state == "published"`), jamais recalcule ici — voir l'en-tete.
    """
    if not fiche_publiee:
        return peut_completer_la_fiche_arrivee(
            connexion,
            entite=entite,
            acteur=acteur,
            cible_appartenance=cible_appartenance,
            cible_personne=cible_personne,
            roles=roles,
            instant=instant,
        )
    return peut_corriger_la_fiche_arrivee_apres_publication(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        cible_personne=cible_personne,
        roles=roles,
        instant=instant,
    )


def peut_gerer_l_autorisation_photo(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il accorder ou retirer l'autorisation photo de la cible ?

    `Soi` TOUJOURS, quel que soit l'etat de publication de la fiche — a la
    difference du depot, cette ligne du §6.1 ne distingue pas avant/apres.
    `DSM` reste a TIRET aux deux etats, contrairement au depot ou il retrouve
    `Consultants` apres publication : les deux lignes different, voir l'en-tete.
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


def peut_consulter_l_etat_d_un_media(
    *, acteur: uuid.UUID, uploaded_by_person_id: uuid.UUID, roles: frozenset[RoleDeLaMatrice]
) -> bool:
    """L'acteur peut-il suivre l'avancement du traitement d'UN media precis ?

    Pure lecture de confort pour la session qui vient de deposer — jamais une
    liste des medias d'autrui. Qui l'a depose peut toujours suivre son propre
    depot ; un role de portee ENTITE le peut aussi, puisqu'il pourrait avoir
    depose pour le compte d'un collaborateur. Aucune nouvelle grille de la
    matrice n'est invoquee : c'est une commodite de l'ECRAN, pas une ligne du
    §6.1.
    """
    return acteur == uploaded_by_person_id or bool(roles & _ROLES_ENTITE)
