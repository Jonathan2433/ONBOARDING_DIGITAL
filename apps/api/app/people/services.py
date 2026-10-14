"""Depart et archivage d'une appartenance — story `MVP-L03-US006`.

LOT 3, sous-etape `T9`.

TROIS SOURCES, TROIS LISTES DIFFERENTES — ET C'EST LE PREMIER TRAVAIL

  Le corpus attache la revocation a trois enonces qui ne disent pas la meme chose :

      cahier §7.4     « revocation immediate des sessions lors d'un depart ou
                        retrait d'acces »
      cahier §6.2     « l'archivage d'une appartenance revoque les acces et
                        cloture les relations actives »
      cahier §30.22   « le depart revoque immediatement les sessions ET ROLES »
      backlog US006   « l'archivage invalide sessions, INVITATIONS et futurs
                        magic links dans la meme action metier »
      RIGHTS-019      « la cloture d'une responsabilite revoque immediatement les
                        permissions associees »

  **`invitation` N'EXISTE PAS.** Zero occurrence dans le modele de donnees, zero
  dans la matrice. Le cahier ne le nomme que comme objet audite (§10.11),
  operation idempotente (§18.6, donc LOT 11 -- `DEC-532`) et tache planifiee
  d'expiration. Il n'y a rien a invalider, et en inventer une table serait §6.5.
  C'etait `ECART-035`, **CLOS par `T13` du LOT 9** (`DEC-648`) : relu contre les
  seize sous-etapes validees du lot, aucune ne pose d'objet « invitation » --
  `T12` nomme un administrateur par une simple affectation de role technique,
  jamais un objet de ce nom. `test_AUCUNE_TABLE_INVITATION_N_EXISTE_A_INVALIDER`
  (`tests/test_revocation.py`) rend la fermeture falsifiable : elle echouera le
  jour ou une table de ce nom existera, et c'est alors qu'il faudra ajouter ici
  la ligne de revocation que l'ecart promettait.

LA REVOCATION TIENT AU **DEPART**, ET NON AU SEUL ARCHIVAGE

  Le §24.1 est net : il n'existe **aucune** transition `Active --> Archived`. Le
  depart est `Active --> Departed` ; l'archivage est `Departed --> Archived`, une
  etape **ulterieure** que le cahier appelle « archivage fonctionnel ».

  Si la revocation ne tenait qu'a l'archivage -- la lettre de `US006` -- il
  existerait une fenetre entre le depart et l'archivage pendant laquelle un
  collaborateur parti **conserve une session active**. Le §7.4 et le §30.22
  ecrivent tous deux « immediatement », ce qui l'interdit.

  Les deux transitions revoquent donc, et la seconde est **idempotente** : elle ne
  trouve plus rien a revoquer et rend zero. Aucune des trois sources n'est
  contredite.

L'ORDRE EST IMPOSE PAR UN DECLENCHEUR, ET IL AURAIT CASSE EN PRODUCTION

  `fn_dg_implique_dsm_local` se declenche `BEFORE UPDATE` sur `entity_membership`
  des que `NEW.professional_category = 'dg'`, et exige une responsabilite DSM
  **active** dans la meme entite -- **sans regarder l'etat**.

  Clore la responsabilite AVANT de changer l'etat ferait donc **echouer le depart
  d'un DG**, avec un message parlant de categorie `dg` et non de revocation. Le
  changement d'etat vient donc en premier, et un test eprouve le depart d'un DG :
  sans lui, le defaut n'apparaitrait qu'au premier depart reel d'un DG.

  C'est la cinquieme idee du socle du LOT 2 -- un declencheur `BEFORE ROW` peut
  ombrager ce qui le suit -- appliquee a un ordre d'ecritures.

CE QUI EST RAPPORTE PLUTOT QUE DECIDE — §7.20

  Quatre situations ne se tranchent pas sans une regle que le corpus n'ecrit pas.
  Elles sont **comptees et rendues** a l'appelant, jamais traitees en silence :

    1. **les roles GLOBAUX.** `technical_role_assignment` accepte `entity_id`
       nul -- le §8.6 le prevoit pour `SUPER_ADMIN`. Quitter une entite ne retire
       pas un role global, et le retirer depasserait le §30.22 ;
    2. **les relations FUTURES.** Une relation dont `starts_at` est posterieur a
       l'instant ne peut pas etre close a cet instant : `ends_at < starts_at`
       rendrait la plage `period` invalide. Ce qu'il faut en faire -- annuler,
       decaler -- n'est ecrit nulle part ;
    3. **les consultants dont le partant est le DSM.** Leurs lignes
       `dsm_assignment` ne sont PAS closes : la responsabilite du partant l'est,
       donc **les permissions sont bien revoquees** (`RIGHTS-019`), et le lien
       historique est conserve. Mais le §30.4 exige qu'un consultant actif
       possede un DSM actif, et **designer le remplacant est une decision
       humaine** -- le §30.4 est d'ailleurs classe `PARTIEL` parce que cette
       existence « ne peut pas etre acquise en base ».
       **Consequence a connaitre :** le declencheur `dsm_responsabilite_active`
       refusera desormais toute modification de ces lignes jusqu'a la
       reaffectation. C'est bruyant, donc diagnosticable.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.auth.sessions import REVOCATION_DEPART, revoquer_toutes_les_sessions
from app.people.modeles import (
    ETATS_OCCUPANTS,
    TRANSITIONS_DU_CYCLE_DE_VIE,
    EtatAppartenance,
)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

# ===========================================================================
#
#  LES RELATIONS A CLORE, DECLAREES ET NON DEDUITES
#
#    Le §25.2 enumere SEPT relations historisees. `entity_membership` est celle
#    qu'on archive ; les six autres sont a clore.
#
#    **LE LIEN A SUIVRE EST UNE INTERPRETATION**, donc il est declare ici plutot
#    que devine : quatre relations pendent a l'appartenance, deux a la personne
#    dans une entite. Une heuristique sur les noms de colonne serait un defaut --
#    lecon `T9-2` du LOT 2, confirmee par le §7.25.
#
#    Et parce qu'une liste ecrite vieillit au premier ajout -- §7.27, quatre
#    occurrences dans ce lot -- `make revocation-check` **exige** que cette liste
#    corresponde exactement aux sept relations du §25.2 moins `entity_membership`.
#
# ===========================================================================

#  Relations qui pendent a l'APPARTENANCE elle-meme.
RELATIONS_DE_L_APPARTENANCE: Final[dict[str, str]] = {
    "membership_job_assignment": "entity_membership_id",
    "professional_status_assignment": "entity_membership_id",
    "circle_membership": "entity_membership_id",
    "dsm_assignment": "consultant_membership_id",
}

#  Relations qui pendent a la PERSONNE, bornees a l'entite quittee.
RELATIONS_DE_LA_PERSONNE: Final[tuple[str, ...]] = (
    "framework_responsibility_assignment",
    "technical_role_assignment",
)

#  Les etats « occupants » du §25.1. Employes pour ne rapporter que les
#  consultants encore en poste : un consultant lui-meme parti n'a pas besoin d'un
#  nouveau DSM.
ETATS_ENCORE_ACTIFS: Final[tuple[str, ...]] = (
    EtatAppartenance.ACTIVE.value,
    EtatAppartenance.FUTURE.value,
)

#  **LES TRANSITIONS QUE CE MODULE REALISE, DERIVEES ET NON RECOPIEES.**
#
#  Le §24.1 en compte quatre, declarees dans `app/people/modeles.py`. Celles que
#  ce module applique sont celles qui **quittent** l'occupation : c'est exactement
#  ce qui justifie la revocation, et `_appliquer` ne sait rien faire d'autre.
#
#  Le discriminant est donc l'etat d'ARRIVEE, jamais une liste ecrite a la main :
#  `T8` du LOT 5 a ajoute `Archived --> Active` a `TRANSITIONS_DU_CYCLE_DE_VIE`,
#  et cette constante l'a exclue **sans que personne y pense** -- ce qu'une
#  troisieme ligne recopiee n'aurait pas fait (§7.27). L'inverse,
#  `TRANSITIONS_QUI_RESTAURENT`, vit dans `app/people/archivage.py`.
TRANSITIONS_AUTORISEES: Final[frozenset[tuple[str, str]]] = frozenset(
    (depuis, vers) for depuis, vers in TRANSITIONS_DU_CYCLE_DE_VIE if vers not in ETATS_OCCUPANTS
)


class TransitionRefusee(ValueError):
    """La transition demandee n'est pas dans le §24.1, ou l'appartenance est absente.

    Le message nomme les deux etats, jamais l'identite de la personne : il finit
    dans un journal.
    """


@dataclass(frozen=True, slots=True)
class Revocation:
    """Ce que la transition a produit, et ce qu'elle a DELIBEREMENT laisse.

    Les quatre derniers champs sont des **rapports**, non des echecs : voir
    l'en-tete du module. Un appelant qui les ignore obtient un livrable conforme ;
    un appelant qui les lit peut prevenir un humain.
    """

    appartenance: uuid.UUID
    etat_precedent: str
    etat_nouveau: str
    sessions_revoquees: int
    liens_invalides: int
    relations_closes: dict[str, int] = field(default_factory=dict)
    #  --- ce qui est rapporte, jamais decide ---
    roles_globaux_conserves: int = 0
    relations_futures_conservees: dict[str, int] = field(default_factory=dict)
    consultants_sans_dsm: tuple[uuid.UUID, ...] = ()

    @property
    def a_des_reserves(self) -> bool:
        """Vrai des qu'une situation a ete rapportee plutot que traitee."""
        return bool(
            self.roles_globaux_conserves
            or self.relations_futures_conservees
            or self.consultants_sans_dsm
        )


def enregistrer_un_depart(
    connexion: Connection,
    *,
    appartenance: uuid.UUID,
    instant: dt.datetime,
    date_de_depart: dt.date | None = None,
) -> Revocation:
    """`Active --> Departed` — et la revocation est **immediate**, §7.4 et §30.22.

    C'est ici que la revocation a lieu, non a l'archivage : entre les deux, une
    session active serait une session d'un collaborateur parti.

    Args:
        date_de_depart: posee si la colonne est nulle. La contrainte
            `ck_entity_membership_depart_date_si_departed` l'exige pour l'etat
            `departed` ; a defaut, la date de `instant` est employee.
    """
    return _appliquer(
        connexion,
        appartenance=appartenance,
        vers=EtatAppartenance.DEPARTED.value,
        instant=instant,
        date_de_depart=date_de_depart or instant.date(),
    )


def archiver_une_appartenance(
    connexion: Connection,
    *,
    appartenance: uuid.UUID,
    instant: dt.datetime,
) -> Revocation:
    """`Departed --> Archived` ou `Future --> Archived` — §6.2 et `US006`.

    **IDEMPOTENTE SUR CE QUI A DEJA ETE REVOQUE.** Venant apres un depart, elle ne
    trouve plus de session ni de lien actif et rend zero : c'est ce qui permet de
    satisfaire `US006` -- « l'archivage invalide … » -- sans creer la fenetre que
    le §7.4 interdit.

    Venant de `future` -- « arrivee annulee », §24.1 -- elle revoque pour de bon :
    aucun depart n'a eu lieu.
    """
    return _appliquer(
        connexion,
        appartenance=appartenance,
        vers=EtatAppartenance.ARCHIVED.value,
        instant=instant,
        date_de_depart=None,
    )


def _appliquer(
    connexion: Connection,
    *,
    appartenance: uuid.UUID,
    vers: str,
    instant: dt.datetime,
    date_de_depart: dt.date | None,
) -> Revocation:
    """Le coeur, commun aux deux transitions. **UNE SEULE TRANSACTION.**

    La transaction est celle de l'appelant, et c'est le critere : « la revocation
    est **atomique** avec l'archivage ». Une revocation validee sans le changement
    d'etat laisserait une personne active sans acces ; un changement d'etat valide
    sans la revocation laisserait un partant connecte.
    """
    ligne = connexion.execute(
        text(
            "SELECT person_id, entity_id, membership_state, professional_category "
            "FROM entity_membership WHERE id = :appartenance FOR UPDATE"
        ),
        {"appartenance": appartenance},
    ).one_or_none()
    if ligne is None:
        message = "appartenance introuvable"
        raise TransitionRefusee(message)

    personne, entite, depuis, _categorie = ligne
    if (depuis, vers) not in TRANSITIONS_AUTORISEES:
        message = f"transition refusee par le §24.1 : {depuis} -> {vers}"
        raise TransitionRefusee(message)

    #  --- 1. L'ETAT D'ABORD, ET L'ORDRE EST IMPOSE ------------------------
    #
    #  `fn_dg_implique_dsm_local` exige une responsabilite DSM active des que la
    #  categorie vaut `dg`, sans regarder l'etat. Clore les roles avant cet
    #  `UPDATE` ferait echouer le depart d'un DG. Voir l'en-tete du module.
    connexion.execute(
        text(
            "UPDATE entity_membership "
            "SET membership_state = :vers, "
            "    departure_date = COALESCE(departure_date, :depart) "
            "WHERE id = :appartenance"
        ),
        {"vers": vers, "depart": date_de_depart, "appartenance": appartenance},
    )

    #  --- 2. Les relations de l'appartenance -----------------------------
    closes: dict[str, int] = {}
    futures: dict[str, int] = {}
    for table, lien in RELATIONS_DE_L_APPARTENANCE.items():
        closes[table], futures[table] = _clore(
            connexion,
            table=table,
            filtre=f"{lien} = :cible",
            parametres={"cible": appartenance},
            instant=instant,
        )

    #  --- 3. Les roles de la personne, DANS CETTE ENTITE seulement -------
    for table in RELATIONS_DE_LA_PERSONNE:
        closes[table], futures[table] = _clore(
            connexion,
            table=table,
            filtre="person_id = :personne AND entity_id = :entite",
            parametres={"personne": personne, "entite": entite},
            instant=instant,
        )

    #  Les roles globaux sont RAPPORTES, jamais retires : le §8.6 rend
    #  `entity_id` nullable pour `SUPER_ADMIN`, et quitter une entite ne retire
    #  pas un role global.
    globaux = int(
        connexion.execute(
            text(
                "SELECT count(*) FROM technical_role_assignment "
                "WHERE person_id = :personne AND entity_id IS NULL "
                "  AND (ends_at IS NULL OR ends_at > :instant)"
            ),
            {"personne": personne, "instant": instant},
        ).scalar_one()
    )

    #  --- 4. Les acces ----------------------------------------------------
    #
    #  **AUCUNE GARDE « ENCORE ACTIF AILLEURS », ET C'EST UN CORRECTIF MESURE.**
    #
    #    J'en avais ecrit une : ne pas revoquer les sessions si la personne garde
    #    une appartenance active ou future dans une autre entite. **Cet etat est
    #    impossible.** `uq_entity_membership_person_id_occupante` est un index
    #    unique PARTIEL sur `person_id` seul, restreint aux etats `future` et
    #    `active` -- §25.1, « une seule appartenance active ou future par
    #    personne ». Une personne qui quitte son appartenance occupante n'en a
    #    donc aucune autre.
    #
    #    La garde etait du code mort, et un champ de rapport qui ne peut jamais
    #    etre vrai est une fausse promesse : il apprend a ne pas le lire. Il est
    #    retire, et **remplace par un test qui prouve l'invariant en base** --
    #    si un lot ulterieur relachait cet index pour autoriser l'appartenance
    #    multi-entites, ce test echouerait, et celui qui le relache saurait qu'il
    #    doit relire cette revocation. C'est le §7.21 pris a l'endroit : ne pas
    #    ecrire une defense contre un etat que la base interdit, mais **exiger
    #    qu'elle continue de l'interdire.**
    sessions = revoquer_toutes_les_sessions(
        connexion, personne=personne, instant=instant, raison=REVOCATION_DEPART
    )
    #  Les liens ACTIFS seulement : un lien deja consomme est une trace, et
    #  l'invalider apres coup reecrirait l'histoire.
    liens = int(
        connexion.execute(
            text(
                "UPDATE magic_link_request SET invalidated_at = :instant "
                "WHERE person_id = :personne "
                "  AND used_at IS NULL AND invalidated_at IS NULL "
                "RETURNING id"
            ),
            {"instant": instant, "personne": personne},
        ).rowcount
    )

    #  --- 5. Les consultants orphelins de DSM, RAPPORTES -----------------
    orphelins = tuple(
        uuid.UUID(str(r[0]))
        for r in connexion.execute(
            text(
                "SELECT DISTINCT m.person_id FROM dsm_assignment d "
                "JOIN entity_membership m ON m.id = d.consultant_membership_id "
                "WHERE d.dsm_person_id = :personne "
                "  AND (d.ends_at IS NULL OR d.ends_at > :instant) "
                "  AND m.membership_state = ANY(:etats)"
            ),
            {"personne": personne, "instant": instant, "etats": list(ETATS_ENCORE_ACTIFS)},
        )
    )

    return Revocation(
        appartenance=appartenance,
        etat_precedent=depuis,
        etat_nouveau=vers,
        sessions_revoquees=sessions,
        liens_invalides=liens,
        relations_closes={t: n for t, n in closes.items() if n},
        roles_globaux_conserves=globaux,
        relations_futures_conservees={t: n for t, n in futures.items() if n},
        consultants_sans_dsm=orphelins,
    )


def _clore(
    connexion: Connection,
    *,
    table: str,
    filtre: str,
    parametres: dict[str, object],
    instant: dt.datetime,
) -> tuple[int, int]:
    """Clore les periodes actives d'une relation. Rend `(closes, futures laissees)`.

    **`starts_at <= :instant` EST INDISPENSABLE.** `period` est
    `GENERATED ALWAYS AS tstzrange(starts_at, ends_at)` : poser `ends_at` avant
    `starts_at` produirait une plage dont la borne basse depasse la haute, et
    PostgreSQL refuserait la ligne. Une relation qui n'a pas commence est donc
    **comptee et laissee**, parce que ce qu'il faut en faire n'est ecrit nulle
    part -- §6.5.
    """
    closes = connexion.execute(
        text(
            f"UPDATE {table} SET ends_at = :instant "  # noqa: S608
            f"WHERE {filtre} "
            "  AND starts_at <= :instant "
            "  AND (ends_at IS NULL OR ends_at > :instant)"
        ),
        {**parametres, "instant": instant},
    ).rowcount
    futures = connexion.execute(
        text(
            f"SELECT count(*) FROM {table} "  # noqa: S608
            f"WHERE {filtre} AND starts_at > :instant"
        ),
        {**parametres, "instant": instant},
    ).scalar_one()
    return int(closes), int(futures)
