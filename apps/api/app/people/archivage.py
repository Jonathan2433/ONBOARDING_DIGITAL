"""Archiver et restaurer une appartenance, cote API — story `MVP-L05-US007`.

LOT 5, sous-etape `T8`.

CE QUI EXISTAIT DEJA, ET QU'IL NE FAUT PAS REECRIRE

  La moitie « l'archivage revoque et cloture » du critere est **livree depuis le
  `T9` du LOT 3**. `app/people/services.py` porte `enregistrer_un_depart` et
  `archiver_une_appartenance` : la revocation des sessions, l'invalidation des
  liens actifs, la cloture des SIX relations historisees du §25.2, et les quatre
  situations rapportees plutot que decidees. `make recette-modele-check` classe
  le §30.22 **`ACQUIS`** depuis lors.

  Ce module n'en refait rien. Il ajoute ce qui manquait, et rien de plus :

      1. la QUATRIEME transition du §24.1 -- `Archived --> Active`,
         « reactivation explicite autorisee » -- qui n'existait nulle part ;
      2. la concurrence optimiste du §18.4 sur ces deux actes ;
      3. la traduction des refus de la base au format du §18.3.

  Les ROUTES, elles, sont dans `app/people/routes.py`, et la grille de roles
  dans `app/permissions/perimetre.py`. Meme repartition que `T7`.

ARCHIVER QUELQU'UN D'ACTIF EST UN CHEMIN, PAS UNE TRANSITION

  Le §24.1 ne porte **aucune** transition `Active --> Archived`. Le §6.1, lui,
  ne porte qu'une seule action, « Archiver un profil ». Les deux se concilient
  sans rien inventer : l'action du §6.1 parcourt le chemin du §24.1, soit
  `Active --> Departed --> Archived`, soit `Future --> Archived` -- « arrivee
  annulee » -- soit `Departed --> Archived` seul.

  **ET LES DEUX ETAPES REVOQUENT, CE QUI REND L'ORDRE INOFFENSIF.** Le `T9` du
  LOT 3 l'avait etabli et mesure : la seconde est idempotente, elle ne trouve
  plus de session ni de lien actif et rend zero. Passer par `departed` ne cree
  donc aucune fenetre, et le §7.4 -- « revocation **immediate** » -- est tenu.

LA RESTAURATION NE ROUVRE RIEN, ET C'EST UN ARBITRAGE DE JONATHAN

  Decision du 10/09/2026. Le depart avait cloture metier, statut, client, DSM et
  cercle ; la restauration remet l'appartenance en `active` et **les laisse
  closes**. Trois motifs concordants :

    - le §23.4 dit « la suppression d'un role actif CLOTURE la relation au lieu
      d'effacer l'historique ». Rouvrir d'anciennes valeurs sur une periode
      neuve n'est pas restaurer un historique, c'est **decider a nouveau** ;
    - la quatrieme idee du socle du LOT 2 : « inventer un attributeur
      FABRIQUERAIT une trace d'audit fausse ». Un DSM reaffecte par la
      plateforme est un DSM que personne n'a designe ;
    - le corpus n'en dit rien. §6.5.

  **LA CONSEQUENCE EST RAPPORTEE, JAMAIS TAIE (§7.20).** Juste apres une
  restauration, la personne est active **sans metier ni DSM**, et le §30.4 veut
  qu'un consultant actif ait un DSM actif. `Restauration.relations_a_redonner`
  compte, relation par relation, ce qui n'a aucune periode courante -- c'est
  mesure au meme instant, pas suppose -- et l'appelant peut le dire a un humain.
  Le §30.4 est d'ailleurs classe `PARTIEL` pour exactement cette raison : « cette
  existence ne peut pas etre acquise en base ». Les redonner est l'affaire du
  `PATCH` de `T7`.

DEUX REFUS QUE LA BASE PRODUIT, ET QU'IL FAUT TRADUIRE SANS LES MASQUER

  Restaurer, c'est repasser dans un etat OCCUPANT et **desapposer la date de
  depart** -- sans quoi l'appartenance serait `active` avec une `period` deja
  close, ce qui se contredit. Deux contraintes peuvent alors refuser, et **elles
  ont raison** :

      uq_entity_membership_person_id_occupante   la personne occupe deja une
                                                 appartenance, ici ou ailleurs
      excl_..._sans_chevauchement                la periode redevenue ouverte
                                                 chevauche une appartenance
                                                 posterieure de la meme personne

  **C'est la base qui arbitre, et c'est voulu (§7.32).** Ecrire ces deux
  verifications en Python donnerait une seconde regle, qui divergerait le jour
  ou le §25.1 changerait -- et elle serait de toute facon sujette a la course
  que l'index, lui, ne laisse pas passer.

  Le refus rendu est un **409 sans cause nommee** : la cause porte sur une autre
  appartenance, donc possiblement une autre entite, que le §5.1 ne laisse pas
  lire a l'appelant. Elle est journalisee cote serveur -- meme parti que la
  miniature illisible de `T5`.

LOT 7 `T11` S'ACCROCHE ICI, AU DEPART, SANS DUPLIQUER LA REVOCATION

  Matrice §8.2 (onboarding) : « le depart d'un collaborateur archive le
  parcours ». `archiver_un_profil` appelle desormais `app.onboarding.
  instances.archiver_le_parcours_au_depart` juste apres `enregistrer_un_
  depart`, dans la MEME branche `depuis == ACTIVE` -- jamais a l'archivage
  fonctionnel qui suit, pour la meme raison que la revocation des sessions
  est deja ancree au depart et non a l'archivage (§7.4 ci-dessus). Le
  resultat est rapporte dans `Archivage.parcours_onboarding_archive`
  (`None` si aucun parcours actif n'existait), jamais tu -- meme discipline
  que les autres champs de rapport de ce module.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.onboarding.instances import archiver_le_parcours_au_depart
from app.people.ecriture import (
    CODE_VERSION_OBSOLETE,
    MESSAGE_VERSION_OBSOLETE,
    traduire_un_refus_de_la_base,
)
from app.people.modeles import (
    ETATS_OCCUPANTS,
    TRANSITIONS_DU_CYCLE_DE_VIE,
    EtatAppartenance,
)
from app.people.services import (
    RELATIONS_DE_L_APPARTENANCE,
    RELATIONS_DE_LA_PERSONNE,
    Revocation,
    archiver_une_appartenance,
    enregistrer_un_depart,
)
from app.permissions.perimetre import ActionDeCycleDeVie, PerimetreDuCycleDeVie
from app.shared.errors import ErreurApplicative

journal = logging.getLogger("app.people.archivage")

CODE_ACTION_HORS_PERIMETRE: Final = "action_hors_perimetre"
MESSAGE_ACTION_HORS_PERIMETRE: Final = (
    "cette action de cycle de vie n'est pas autorisee sur ce collaborateur"
)

#  **L'INVERSE DE `TRANSITIONS_AUTORISEES` DE `services.py`, ET DERIVE DE LA MEME
#  SOURCE.** Une transition restaure si et seulement si elle RAMENE dans
#  l'occupation. Les deux constantes partitionnent donc `TRANSITIONS_DU_CYCLE_DE_VIE`
#  sans qu'aucune des deux ne recopie une liste (§7.27).
TRANSITIONS_QUI_RESTAURENT: Final[frozenset[tuple[str, str]]] = frozenset(
    (depuis, vers) for depuis, vers in TRANSITIONS_DU_CYCLE_DE_VIE if vers in ETATS_OCCUPANTS
)


@dataclasses.dataclass(frozen=True, slots=True)
class Archivage:
    """Ce que l'archivage a produit — la version nouvelle, et le rapport du LOT 3.

    `revocations` porte UNE entree par transition reellement appliquee : deux
    quand la cible etait `active` -- le depart puis l'archivage -- une sinon. Les
    exposer separement plutot que sommees permet de lire que la seconde n'a
    **rien** trouve a revoquer, ce qui est la preuve que la premiere avait tout
    pris.
    """

    version: int
    etat_precedent: str
    revocations: tuple[Revocation, ...]
    parcours_onboarding_archive: uuid.UUID | None = None

    @property
    def sessions_revoquees(self) -> int:
        return sum(r.sessions_revoquees for r in self.revocations)

    @property
    def liens_invalides(self) -> int:
        return sum(r.liens_invalides for r in self.revocations)

    @property
    def relations_closes(self) -> dict[str, int]:
        """Le total par table, sur les deux transitions.

        Sommer plutot que garder la derniere : venant d'`active`, c'est le DEPART
        qui a tout clos et l'archivage rend zero. Ne rapporter que la seconde
        annoncerait « 0 relation close » sur un archivage qui en a clos cinq.
        """
        total: dict[str, int] = {}
        for revocation in self.revocations:
            for table, nombre in revocation.relations_closes.items():
                total[table] = total.get(table, 0) + nombre
        return total

    @property
    def relations_futures_conservees(self) -> dict[str, int]:
        """Le maximum par table, et non la somme.

        C'est un ETAT -- « il reste n relations futures » -- releve deux fois sur
        la meme population, non un flux. Les additionner compterait deux fois la
        meme ligne : sommer un etat est la classe §7.0 sixieme proposition, deux
        grandeurs qui ne mesurent pas la meme chose.
        """
        total: dict[str, int] = {}
        for revocation in self.revocations:
            for table, nombre in revocation.relations_futures_conservees.items():
                total[table] = max(total.get(table, 0), nombre)
        return total

    @property
    def consultants_sans_dsm(self) -> tuple[uuid.UUID, ...]:
        """L'union, dedoublonnee : les deux releves portent sur la meme population."""
        vus: dict[uuid.UUID, None] = {}
        for revocation in self.revocations:
            for consultant in revocation.consultants_sans_dsm:
                vus[consultant] = None
        return tuple(vus)

    @property
    def roles_globaux_conserves(self) -> int:
        """Le maximum, meme motif que les relations futures : c'est un etat."""
        return max((r.roles_globaux_conserves for r in self.revocations), default=0)

    @property
    def a_des_reserves(self) -> bool:
        return any(r.a_des_reserves for r in self.revocations)


@dataclasses.dataclass(frozen=True, slots=True)
class Restauration:
    """Ce que la restauration a produit, et ce qu'elle a DELIBEREMENT laisse clos.

    `relations_a_redonner` est un **rapport**, non un echec : voir l'en-tete du
    module. Un appelant qui l'ignore obtient un livrable conforme ; un appelant
    qui le lit peut prevenir un humain qu'il reste un metier et un DSM a poser.
    """

    version: int
    etat_precedent: str
    relations_a_redonner: tuple[str, ...]


#  L'etat et la version, sous verrou. `FOR UPDATE` sur la RACINE de l'agregat :
#  le meme parti que `T7`, si bien qu'un archivage et une modification
#  organisationnelle concurrents se sequencent au lieu de s'ecraser.
_ETAT_SOUS_VERROU: Final[str] = """
SELECT membership_state, version, person_id FROM entity_membership
WHERE id = :cible AND entity_id = :entite AND archived_at IS NULL
FOR UPDATE
"""

#  **LA DATE DE DEPART EST DESAPPOSEE, ET LE MOTIF EST STRUCTUREL.** `period` est
#  `GENERATED ALWAYS AS daterange(arrival_date, departure_date)` : la garder
#  rendrait une appartenance `active` dont la periode est deja close, que le
#  §24.1 ne decrit pas et que les lectures en `period @> :instant` -- `T3`, `T4`,
#  `T7` -- exclueraient en paraissant justes.
_RESTAURER: Final[str] = """
UPDATE entity_membership
SET membership_state = :vers,
    departure_date = NULL,
    version = version + 1,
    updated_at = :instant,
    updated_by_person_id = :acteur
WHERE id = :cible AND entity_id = :entite
RETURNING version
"""

#  **UNE SEULE VALEUR A TROIS SENS, ET C'EST CE QUI REND LE RAPPORT EXACT.**
#
#  `bool_or` sur zero ligne rend **NULL**, sur des lignes toutes passees **FALSE**,
#  et **TRUE** des qu'une periode couvre l'instant. Les trois cas sont exactement
#  ceux qu'il faut distinguer :
#
#      NULL   la relation n'a JAMAIS existe        -> rien a redonner
#      FALSE  elle a existe et n'existe plus       -> A REDONNER
#      TRUE   une periode courante existe          -> rien a redonner
#
#  **Le cas NULL est la raison de cette forme, et il a ete mesure.** Une premiere
#  version rapportait « pas de periode courante », donc elle nommait
#  `technical_role_assignment` sur un profil qui n'en a JAMAIS eu -- un
#  avertissement faux, que le §7.21 nomme pire qu'une absence d'avertissement :
#  il apprend a ne pas lire le champ. On ne redonne pas ce qui n'a pas ete donne.
#
#  `period @> :instant` et non `ends_at IS NULL` : une relation FUTURE a elle
#  aussi un `ends_at` nul, et la compter comme presente laisserait croire qu'il
#  n'y a rien a redonner alors que la personne est sans metier aujourd'hui. C'est
#  le piege d'`ECART-056`, dans un troisieme module.
_RELATION_A_REDONNER: Final[str] = """
SELECT bool_or(period @> :instant) FROM {table}
WHERE {lien} = :cible AND archived_at IS NULL
"""

#  La meme chose pour les relations qui pendent a la PERSONNE. Le
#  `entity_id = :entite` est indispensable : un role GLOBAL -- `entity_id` nul,
#  §8.6 -- n'a jamais ete clos par le depart, donc il n'y a rien a y redonner, et
#  l'omettre le ferait paraitre manquant alors qu'il est intact.
_RELATION_DE_LA_PERSONNE_A_REDONNER: Final[str] = """
SELECT bool_or(period @> :instant) FROM {table}
WHERE person_id = :personne AND entity_id = :entite AND archived_at IS NULL
"""


def _exiger_l_action(perimetre: PerimetreDuCycleDeVie, action: ActionDeCycleDeVie) -> None:
    """Le perimetre d'abord, avant toute lecture d'etat — §2.5, « refus par defaut ».

    Le meme ordre que `T7` : on ne travaille pas sur une ressource qu'on n'a pas
    le droit de toucher, et l'action refusee est NOMMEE -- l'appelant vient de la
    demander, la taire l'obligerait a deviner.
    """
    if action in perimetre.actions:
        return
    raise ErreurApplicative(
        code=CODE_ACTION_HORS_PERIMETRE,
        message=MESSAGE_ACTION_HORS_PERIMETRE,
        statut=status.HTTP_403_FORBIDDEN,
        details={"action": action.value},
    )


def _lire_sous_verrou(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    version_attendue: int,
) -> tuple[str, uuid.UUID]:
    """Rendre l'etat courant et la personne, apres avoir exige la version du §18.4."""
    ligne = connexion.execute(text(_ETAT_SOUS_VERROU), {"cible": cible, "entite": entite}).first()
    if ligne is None:
        #  Le perimetre a deja exige une appartenance de cette entite : arriver
        #  ici veut dire qu'elle a disparu entre les deux appels. Un `409` le dit
        #  sans rien inventer -- meme parti que `T7`.
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
        )
    etat, version, personne = str(ligne[0]), int(ligne[1]), uuid.UUID(str(ligne[2]))
    if version != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": version},
        )
    return etat, personne


def archiver_un_profil(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    perimetre: PerimetreDuCycleDeVie,
    instant: dt.datetime,
    date_de_depart: dt.date | None = None,
) -> Archivage:
    """« Archiver un profil » du §6.1 — le chemin du §24.1 jusqu'a `archived`.

    Args:
        date_de_depart: la « date de depart » que le §2.1 range dans
            `entity_membership`. Facultative : a defaut, le jour de `instant`.
            Elle n'est posee que si la colonne est nulle, et la contrainte
            `depart_apres_arrivee` refuse une date anterieure a l'arrivee -- un
            `422` au format du §18.3.

    Leve `ErreurApplicative` : `403` hors perimetre, `409` version obsolete,
    `422` date refusee.
    """
    _exiger_l_action(perimetre, ActionDeCycleDeVie.ARCHIVER)
    depuis, _personne = _lire_sous_verrou(
        connexion, entite=entite, cible=cible, version_attendue=version_attendue
    )

    revocations: list[Revocation] = []
    parcours_archive: uuid.UUID | None = None
    try:
        #  **LE DEPART D'ABORD, ET SEULEMENT S'IL Y A LIEU.** `future` et
        #  `departed` vont droit a `archived` ; le §24.1 n'a pas d'autre chemin,
        #  et forcer un depart depuis `future` daterait une sortie qui n'a jamais
        #  eu lieu -- l'« arrivee annulee » du diagramme n'est pas un depart.
        if depuis == EtatAppartenance.ACTIVE.value:
            revocations.append(
                enregistrer_un_depart(
                    connexion,
                    appartenance=cible,
                    instant=instant,
                    date_de_depart=date_de_depart,
                )
            )
            #  LOT 7 `T11` : le parcours d'onboarding actif, s'il en existe un,
            #  est archive AU DEPART lui-meme — jamais a l'archivage
            #  fonctionnel ci-dessous — pour la meme raison que la revocation
            #  y est deja ancree (§7.4). Voir l'en-tete du module.
            parcours_archive = archiver_le_parcours_au_depart(
                connexion, entite=entite, appartenance=cible
            )
        revocations.append(
            archiver_une_appartenance(connexion, appartenance=cible, instant=instant)
        )
    except (IntegrityError, DataError) as erreur:
        raise traduire_un_refus_de_la_base(erreur) from erreur

    #  La version de la RACINE monte : le service du LOT 3 ecrit en SQL direct et
    #  ne la touche pas, et sans cela deux archivages concurrents passeraient tous
    #  les deux le controle du §18.4.
    version = int(
        connexion.execute(
            text(
                "UPDATE entity_membership SET version = version + 1, "
                "    updated_at = :instant, updated_by_person_id = :acteur "
                "WHERE id = :cible AND entity_id = :entite RETURNING version"
            ),
            {"cible": cible, "entite": entite, "acteur": acteur, "instant": instant},
        ).scalar_one()
    )
    return Archivage(
        version=version,
        etat_precedent=depuis,
        revocations=tuple(revocations),
        parcours_onboarding_archive=parcours_archive,
    )


def restaurer_un_profil(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    perimetre: PerimetreDuCycleDeVie,
    instant: dt.datetime,
) -> Restauration:
    """« Reactiver un profil archive » du §6.1 — `Archived --> Active` du §24.1.

    **ELLE NE ROUVRE AUCUNE RELATION**, et elle DIT lesquelles manquent : voir
    l'en-tete du module.

    Leve `ErreurApplicative` : `403` hors perimetre, `409` version obsolete ou
    etat incompatible.
    """
    _exiger_l_action(perimetre, ActionDeCycleDeVie.RESTAURER)
    depuis, personne = _lire_sous_verrou(
        connexion, entite=entite, cible=cible, version_attendue=version_attendue
    )

    vers = EtatAppartenance.ACTIVE.value
    if (depuis, vers) not in TRANSITIONS_QUI_RESTAURENT:
        #  Inatteignable par la route -- le perimetre a deja exige un etat
        #  restaurable -- et le garder n'est pas une defense contre un etat que
        #  la base interdit (§7.32) : ce module est appelable hors HTTP, comme le
        #  service de taille de page de `T2` l'est (§7.37). La grille et le
        #  service ne doivent pas se faire mutuellement confiance.
        raise ErreurApplicative(
            code=CODE_ACTION_HORS_PERIMETRE,
            message=MESSAGE_ACTION_HORS_PERIMETRE,
            statut=status.HTTP_403_FORBIDDEN,
            details={"action": ActionDeCycleDeVie.RESTAURER.value},
        )

    try:
        version = int(
            connexion.execute(
                text(_RESTAURER),
                {
                    "vers": vers,
                    "cible": cible,
                    "entite": entite,
                    "acteur": acteur,
                    "instant": instant,
                },
            ).scalar_one()
        )
    except (IntegrityError, DataError) as erreur:
        refus = traduire_un_refus_de_la_base(erreur)
        #  **LA CAUSE RESTE AU JOURNAL, ET ELLE Y EST ECRITE ICI MEME.** La
        #  reponse ne peut pas la nommer -- elle porterait sur une appartenance
        #  d'une autre entite (§5.1) -- mais sans trace serveur une restauration
        #  refusee serait indiagnosticable. `resultat: refus`, `DEC-468` :
        #  l'appelant n'a rien casse, la base a refuse.
        journal.warning(
            "restauration refusee par une contrainte de la base",
            extra={
                "resultat": "refus",
                "code_erreur": refus.code,
                "appartenance": str(cible),
                "contrainte": getattr(getattr(erreur.orig, "diag", None), "constraint_name", None),
            },
        )
        raise refus from erreur

    #  **LES SIX RELATIONS DU §25.2 AUTRES QUE L'APPARTENANCE, ET NON QUATRE.**
    #
    #  Ma premiere version ne sondait que les quatre qui pendent a
    #  l'appartenance. `make profil-check` a nomme la difference : le depart clot
    #  AUSSI les relations de la PERSONNE bornees a l'entite -- c'est la moitie
    #  « et roles » du §30.22, et `RIGHTS-019` dit que clore une responsabilite
    #  « revoque immediatement les permissions associees ».
    #
    #  **Une personne restauree n'a donc plus ses responsabilites**, et ne pas le
    #  dire aurait tu la moitie la plus sensible du rapport : un ESM qui restaure
    #  un Booster doit savoir que le cercle n'a plus de Booster.
    manquantes = tuple(
        table
        for table, lien in RELATIONS_DE_L_APPARTENANCE.items()
        if connexion.execute(
            text(_RELATION_A_REDONNER.format(table=table, lien=lien)),
            {"cible": cible, "instant": instant},
        ).scalar_one()
        is False
    ) + tuple(
        table
        for table in RELATIONS_DE_LA_PERSONNE
        if connexion.execute(
            text(_RELATION_DE_LA_PERSONNE_A_REDONNER.format(table=table)),
            {"personne": personne, "entite": entite, "instant": instant},
        ).scalar_one()
        is False
    )
    return Restauration(version=version, etat_precedent=depuis, relations_a_redonner=manquantes)
