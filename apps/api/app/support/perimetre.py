"""Qui consulte et qui traite un signalement — matrice §17, `T12`.

LOT 10, sous-étape `T12`, story `MVP-L10-US006`.

QUATRE LIGNES DU §17, PAS UNE GRILLE PAR ACTION

  Le §17 pose trois lignes de lecture/écriture après « Reporter un bug »
  (`T11`) :

      Consulter ses signalements             Soi  Soi  Soi  Soi  Entité  Global
      Consulter les signalements de l'entité   —  Lecture fonctionnelle  —  —  Entité  Global
      Modifier l'état d'un signalement         —   —   —   —  Entité  Global

  **AUCUNE DE CES TROIS LIGNES NE PORTE DE COLONNE `EMP`/`NEW`**, exactement
  comme « Reporter un bug » (voir l'en-tête d'`app/support/routes.py`) — mais
  le raisonnement qui s'y applique n'est PAS le même pour les trois :

    - « Consulter ses signalements » ne porte AUCUN tiret : les six rôles
      listés reçoivent tous quelque chose (`Soi` au plancher). Même motif que
      `PerimetreDuSuivi` (LOT 7, `T12`) : `Soi` est le PLANCHER UNIVERSEL de
      n'importe quelle session établie, pas une conséquence d'un rôle précis
      — cohérent avec « Reporter un bug », qui est déjà universel ;
    - « Modifier l'état d'un signalement » porte QUATRE tirets sur six : cette
      fois l'absence de colonne `EMP`/`NEW` se lit normalement, comme refus.

QO-092 EST RÉSOLUE PAR CE MODULE, PAS ARBITRÉE

  Le registre ouvrait `QO-092` : « le cahier ne dit pas si un signalement part
  vers Jonathan seul ou vers un canal eXalt plus large ». La matrice §17 —
  **verrouillée depuis le 25 juillet 2026**, « référence fonctionnelle » que
  seule une nouvelle décision explicite peut modifier — règle déjà la
  destination EN APPLICATION : `ADMINISTRATEUR_D_ENTITE` (dans son entité) ET
  `SUPER_ADMINISTRATEUR` (globalement), jamais « Jonathan seul » au sens
  propre — n'importe quel `ADM-E` d'une entité peut traiter les signalements
  de SA entité. Le cahier confirme par une phrase distincte, dans sa section
  « Support » : « visibilité du super-administrateur » — qui ne contredit pas
  la matrice, elle en nomme juste un cas. Aucun canal externe (e-mail, Teams,
  billetterie) n'est décrit nulle part pour les signalements — à la différence
  des alertes, qui nomment explicitement Uptime Kuma comme SOURCE externe
  (§21.2) — et ce lot ne pose aucune infrastructure asynchrone ou de
  notification (`async_job`, LOT 11). `QO-092` reste donc ouverte au registre
  pour son seul volet réellement indécidé — un canal de notification futur,
  hors périmètre de ce lot — mais ne bloque RIEN ici : l'implémentation ne
  dépend d'aucune réponse à ce volet, elle découle entièrement de la matrice.

« LECTURE FONCTIONNELLE » : LES CHAMPS TECHNIQUES, PAS UNE SECONDE FORME

  Le modèle §21.4 distingue déjà « saisie utilisateur »/« ajout automatique »
  (`description`/`reproduction_steps`/`page_path` contre
  `application_version`/`environment`/`browser_summary`/`correlation_token`)
  — et le backlog `US005` nomme lui-même ces derniers « contexte technique non
  sensible ». « Lecture fonctionnelle » pour l'`ESM` masque exactement ces
  quatre colonnes techniques, jamais les colonnes métier — même principe que
  `a_les_details_techniques` (`app.audit.perimetre`, `T8`), déclaré ICI
  séparément plutôt qu'importé : même coïncidence que `ROLES_D_EXPORT_DE_L_
  AUDIT` contre `ROLES_DES_DETAILS_TECHNIQUES` (`T9`) — deux lignes distinctes
  de deux matrices différentes (§16 contre §17), pas une identité conceptuelle
  à lier au silence.

  Qui voit SES PROPRES signalements (`Soi`) voit TOUJOURS les quatre colonnes
  techniques, y compris pour `DSM`/`BOOST`/`OFFICE` : ce sont des informations
  que son propre navigateur a transmises à sa propre demande, rien dans le
  corpus ne les lui masque, et `ESM`/`ADM-E`/`SUPER` ne sont jamais réduits à
  `Soi` ici (ils reçoivent toujours une portée au moins aussi large).
"""

from __future__ import annotations

import enum
from typing import Final

from app.permissions.services import RoleDeLaMatrice


class PerimetreDesSignalements(enum.Enum):
    """§17 : quatre portées, jamais une combinaison — la portée s'ajuste au
    rôle le plus large détenu, `SOI` étant le plancher universel (voir
    l'en-tête du module)."""

    GLOBAL = "global"
    ENTITE_COMPLETE = "entite_complete"
    ENTITE_FONCTIONNELLE = "entite_fonctionnelle"
    SOI = "soi"


#  §17 « Modifier l'état d'un signalement » : DSM/ESM/BOOST/OFFICE à tiret,
#  ADM-E « Entité », SUPER « Global » — la grille la plus étroite du module,
#  l'ESM n'y figurant pas malgré sa « Lecture fonctionnelle » sur la ligne du
#  dessus (deux lignes, deux grilles, même discipline que `T4`/`T5` du lot).
ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
)


def resoudre_le_perimetre_des_signalements(
    *, roles: frozenset[RoleDeLaMatrice]
) -> PerimetreDesSignalements:
    """§17 « Consulter ses signalements »/« Consulter les signalements de
    l'entité » : NEW/DSM/BOOST/OFFICE Soi, ESM Lecture fonctionnelle (Entité),
    ADM-E Entité (complète), SUPER Global (complet).

    Cette fonction ne résout JAMAIS un refus : elle dégrade toujours vers
    `SOI` en dernier recours, pour n'importe quelle session établie — même
    motif que `resoudre_le_perimetre_du_suivi` (LOT 7, `T12`).
    """
    if RoleDeLaMatrice.SUPER_ADMINISTRATEUR in roles:
        return PerimetreDesSignalements.GLOBAL
    if RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE in roles:
        return PerimetreDesSignalements.ENTITE_COMPLETE
    if RoleDeLaMatrice.ESM in roles:
        return PerimetreDesSignalements.ENTITE_FONCTIONNELLE
    return PerimetreDesSignalements.SOI


def a_la_lecture_complete(*, perimetre: PerimetreDesSignalements) -> bool:
    """Les quatre colonnes techniques sont-elles visibles pour ce périmètre ?

    Seule `ENTITE_FONCTIONNELLE` (l'`ESM`, lisant les signalements D'AUTRUI)
    les masque — voir l'en-tête du module pour `SOI`, qui les garde toujours.
    """
    return perimetre is not PerimetreDesSignalements.ENTITE_FONCTIONNELLE
