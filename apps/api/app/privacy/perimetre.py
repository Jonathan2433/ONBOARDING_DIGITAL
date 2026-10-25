"""Qui traite une demande de droit RGPD — modele §22.3, `T14`.

LOT 10, sous-étape `T14`, story `MVP-L10-US008`.

AUCUNE LIGNE DE MATRICE NE NOMME CETTE RESSOURCE — RESOLU PAR ANALOGIE AVEC
LA LIGNE LA PLUS PROCHE, JAMAIS INVENTE

  Ni la matrice des rôles ni le cahier ne portent de section dédiée aux
  demandes de droit RGPD : le backlog nomme l'acteur de `MVP-L10-US008`
  « Responsable RGPD », un mot qui ne correspond à AUCUN des dix codes du §3
  de la matrice (`ANON`/`EMP`/`NEW`/`DSM`/`ESM`/`BOOST`/`OFFICE`/`ADM-E`/
  `SUPER`/`SERVICE`). Inventer un onzième rôle serait trancher une question
  d'organisation que personne n'a posée (§6.5 de la passation).

  La ligne la plus proche, et la SEULE qui porte sur une action RGPD
  touchant une personne précise, est le §18 de la matrice :

      Lancer l'anonymisation RGPD   —   —   —   —   Entité contrôlée   Global

  Cette ligne exclut `DSM`/`ESM`/`BOOST`/`OFFICE` EN BLOC, et ne donne RIEN
  à `ESM` — à la différence des alertes (`T13`), où l'`ESM` reçoit une
  lecture « Limitée fonctionnelle ». `data_subject_request` est le dossier
  qui PRÉCÈDE structurellement cette anonymisation (une demande d'effacement
  aboutie EST ce qui la déclenche, cahier §22.5) : le même périmètre
  s'applique au dossier qui la prépare, par la même lecture que `T9` a déjà
  appliquée pour l'export d'audit — une ligne de matrice qui dicte le rôle
  d'une action ADJACENTE, pas une invention.

  **AUCUN ARBITRAGE DE JONATHAN N'A ÉTÉ NÉCESSAIRE** : la ligne existe déjà,
  explicite, et exclut exactement les mêmes rôles que ceux qu'une gestion de
  dossier légal individuel exclurait par principe (DSM/Booster/responsable
  de bureau n'ont aucune vocation à connaître une demande RGPD visant un
  tiers qui n'est pas nécessairement dans leur périmètre).

RESSOURCE GLOBALE : `ADM-E` RÉSOLU N'IMPORTE OÙ, MÊME PATRON QUE `T13`

  `data_subject_request` NE PORTE AUCUN `entity_id` (modèle §22.3, voir
  l'en-tête d'`app/audit/modeles.py` — groupée avec `operational_alert`,
  `alert_comment` et `export_request` parmi les quatre tables globales du
  lot). La grille Entité/Global ne peut donc pas se lire comme un filtrage
  par entité : `ADM-E` est résolu DANS N'IMPORTE QUELLE entité, exactement
  le patron d'`app.support.perimetre_alertes` — désormais partagé via
  `app.permissions.services.est_administrateur_d_entite_quelque_part`
  (promue ici, premier et second appelants).

  **AUCUNE PORTÉE « SOI »** : une demande RGPD concerne une personne, mais
  ce n'est jamais un self-service — le cahier §21.5 nomme un « canal
  officiel RGPD », c'est-à-dire un canal EXTERNE (courrier, e-mail au
  contact RGPD), jamais un bouton dans l'application. Le dossier est
  réceptionné et tenu par le personnel habilité, pas par la personne
  concernée elle-même via une session applicative.

AUCUN MOTIF OBLIGATOIRE ICI, MÊME MOTIF QUE LES ALERTES

  Le §18.1/`RIGHTS-017` (`ECART-064`) exige un motif pour « une intervention
  du super-administrateur DANS UNE ENTITÉ ». `data_subject_request` ne porte
  structurellement aucune entité : la précondition textuelle ne peut jamais
  être remplie, et `app.audit.motif.exiger_un_motif_si_necessaire` n'est
  appelée par aucune route de ce module — même exemption qu'`app.support.
  perimetre_alertes` (`T13`).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from app.permissions.services import (
    RoleDeLaMatrice,
    est_administrateur_d_entite_quelque_part,
    est_super_administrateur,
)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  §18 « Lancer l'anonymisation RGPD » : seule ligne de matrice touchant une
#  action RGPD sur une personne precise — voir l'en-tete du module. Une seule
#  constante, jamais deux declarations qui pourraient diverger (§7.27).
ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
)


def resoudre_les_roles_pour_les_demandes_rgpd(
    connexion: Connection, *, personne: uuid.UUID, instant: dt.datetime
) -> frozenset[RoleDeLaMatrice]:
    """Les rôles de `personne` pertinents pour les demandes RGPD, TOUTES ENTITÉS confondues.

    Ressource globale (voir l'en-tête du module) : ni `resoudre_les_permissions`
    (qui exige une entité consultée) ni son résultat ne s'appliquent ici.
    """
    roles: set[RoleDeLaMatrice] = set()
    if est_super_administrateur(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.SUPER_ADMINISTRATEUR)
    if est_administrateur_d_entite_quelque_part(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE)
    return frozenset(roles)


def a_le_droit_de_traiter_les_demandes_rgpd(*, roles: frozenset[RoleDeLaMatrice]) -> bool:
    """`True` si ces rôles ouvrent le dossier des demandes RGPD — aucun plancher `Soi`."""
    return bool(roles & ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD)
