"""Le reporting etendu — cahier §10.10, matrice §15.1, `T10`, `MVP-L10-US003`.

CE QUE `T10` LIVRE, ET EN QUOI C'EST DISTINCT DU TABLEAU DE BORD (LOT 9, `T5`)

  Le tableau de bord administratif (`app.administration.tableau_de_bord`) sert
  DEJA, sous la MEME grille de role (§15.1, ligne « Consulter les compteurs »),
  six grandeurs du cahier §10.8 : profils actifs, arrivees futures (SANS
  borne), onboardings actifs, taches en retard, profils incomplets (un
  COMPTE), derniers imports en echec. `T10` ne les reconstruit PAS — fiche
  §2 : « a verifier en construisant si des comptes se recoupent, jamais
  suppose ». Mesure : ils se recoupent EXACTEMENT sur ces six grandeurs, donc
  ce module ajoute UNIQUEMENT ce que le tableau de bord ne sert pas :

    - « onboardings termines » (§10.10) ;
    - « progression moyenne » et « progression par personne » (§10.10) ;
    - « duree moyenne » (§10.10) ;
    - « arrivees dans les 30 jours » (§10.10/§15.1) — une fenetre BORNEE,
      distincte des « arrivees futures » illimitees du tableau de bord ;
    - « profils incomplets » en DETAIL — une LISTE, la ou le tableau de bord
      ne rend qu'un compte ;
    - « repartitions par cercle, client et DSM » (§10.10).

  « Filtrer par periode, DSM, cercle, client » (§15.1) s'applique a TOUTES ces
  grandeurs : ce n'est pas une septieme ligne, c'est un axe transversal, meme
  lecture que les cinq filtres facultatifs d'`app.audit.lecture.FiltresDAudit`
  pour une raison identique (§6.4 : aucune liste d'axes n'est fixee ailleurs).

LA GRILLE DE ROLE N'EST PAS REDECLAREE — ELLE EST LA MEME LIGNE DU §15.1

  Contrairement a `T9` (`ROLES_D_EXPORT_DE_L_AUDIT`, une ligne DIFFERENTE du
  §16 qui ne fait QUE coincider aujourd'hui avec une autre), les quatre
  premieres lignes du §15.1 (« Consulter les compteurs », « le detail
  onboarding », « les profils incomplets », « les arrivees a 30 jours »)
  portent LITTERALEMENT la meme grille — DSM Consultants, ESM Entite, BOOST
  Cercle, OFFICE —, ADM-E Entite, SUPER Global — deja extraite en
  `ROLES_DU_TABLEAU_DE_BORD`/`PerimetreDuTableauDeBord` par le LOT 9 `T5`, dont
  le docstring cite deja §15.1 comme source. Ce module les REIMPORTE donc,
  plutot que de declarer une copie qui pourrait diverger de la MEME regle
  (§7.27 : une liste derivable ne se recopie pas).

CE QUE CE MODULE NE CONSTRUIT PAS, ET POURQUOI

  La sixieme ligne du §15.1, « Consulter les evenements » (seule a donner
  `Bureau` a OFFICE), n'apparait NI dans le cahier §10.10, NI dans les criteres
  d'acceptation litteraux de `MVP-L10-US003` (« Compteurs et tableaux
  respectent ESM, DSM, Booster, admin et superadmin ; aucun graphique ni
  export reporting au MVP » — OFFICE n'y est meme pas nomme). Une lecture
  plausible la rattache au calendrier d'evenements du LOT 8 (meme grille a six
  colonnes que « Archiver un evenement », §18, et que quatre lignes du §11),
  mais AUCUNE phrase du corpus ne relie explicitement cette ligne au
  reporting. Construire une route sur une inference, pas une decision, serait
  le §6.5 enfreint. Question ouverte au registre plutot qu'une invention —
  non bloquante pour cette sous-etape.

TROIS FORMULES DERIVEES, PAS NOMMEES LITTERALEMENT PAR LE CORPUS — DOCUMENTEES
ICI PLUTOT QUE DEVINEES EN SILENCE

  « Onboardings termines » : le modele §13.5 declare un etat `completed`,
  **jamais ecrit** (voir l'en-tete de `app.onboarding.instances` : « `T11`
  transitionne directement `active -> archived` »). Un parcours acheve est
  donc un `onboarding_instance` dont `state = 'archived'` ET `completed_at IS
  NOT NULL` — la seule colonne qui distingue un archivage par COMPLETION
  (`archiver_le_parcours_si_termine`/`archiver_un_parcours_termine`, qui POSE
  `completed_at`) d'un archivage par DEPART (`archiver_le_parcours_au_depart`,
  qui ne le pose JAMAIS — voir son propre docstring : « ce parcours n'a pas
  ete acheve, il a ete INTERROMPU »). Lecture directe du modele, pas une regle
  metier inventee.

  « Duree moyenne » : aucune formule n'est ecrite nulle part (cahier, modele,
  backlog) — seules les colonnes existent. Memes deux colonnes que ci-dessus
  rendent la seule grandeur calculable sans supposition : `completed_at -
  started_at`, sur la MEME population que « onboardings termines » (archives
  pour completion uniquement) — un parcours encore actif n'a pas de duree
  acheve, et un parcours interrompu par un depart n'a pas de `completed_at`
  pour la mesurer. `NULL` si la population est vide (aucune division par
  zero affichee comme un zero trompeur).

  « Progression moyenne » : le couple (`taches_obligatoires_totales`,
  `taches_obligatoires_terminees`) de `_progression_depuis_les_taches`
  (`app.onboarding.instances`, prive, non importe ici — meme discipline que
  `lister_les_taches_en_retard` vs ce module, chacun redeclare sa propre
  lecture SQL, §7.27) est SOMME sur la population des instances ACTIVES dans
  la portee — jamais un pourcentage stocke ni une moyenne de pourcentages
  individuels, meme philosophie que `Progression` elle-meme (LOT 7, `T7`) :
  « comptee a chaque appel, jamais stockee ». Restreinte aux instances
  `active`, meme population que « onboardings actifs » (tableau de bord) —
  une instance terminee est a 100 % par definition et diluerait la mesure
  sans rien dire de la progression EN COURS.

  « Repartitions par cercle, client et DSM » : appliquees a LA MEME population
  que « profils actifs » (tableau de bord) — `entity_membership.
  membership_state = 'active'` — groupee par cercle PRINCIPAL actif, par
  client de la situation professionnelle active, par DSM actif. Lecture
  litterale de l'item qui precede immediatement « repartitions » dans
  l'enumeration du §10.10.

  « Filtrer par periode » : borne `entity_membership.arrival_date`, dans
  TOUTES les requetes de ce module y compris celles qui portent sur
  `onboarding_instance` (jointes a `entity_membership` de toute facon) — une
  seule notion de « periode » plutot qu'une par requete, coherente avec
  « arrivees dans les 30 jours », seule autre notion temporelle du meme
  paragraphe du cahier.

DEUX REQUETES PAR GRANDEUR PAGINEE, MEME DISCIPLINE QUE LE SUIVI ET L'AUDIT

  Le total ET la page dans la MEME transaction, les trois tailles du cahier
  §18.2 reutilisees depuis `app.shared.pagination`, jamais redeclarees.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.administration.perimetre import PerimetreDuTableauDeBord
from app.shared.pagination import TAILLES_DE_PAGE

#  Meme litterale que `app.onboarding.perimetre`/`app.administration.
#  tableau_de_bord`/`app.audit.lecture` — recopiee et non importee, motif SQL
#  partage entre modules distincts (§7.27).
_TYPE_BOOSTER: Final[str] = "BOOSTER"

#  Une clause par portee, correlee a `em` (alias de `entity_membership`),
#  REDECLAREE a l'identique de `app.administration.tableau_de_bord` — meme
#  discipline que `suivi.py` vs `tableau_de_bord.py` : chaque module du
#  domaine declare sa propre lecture plutot que d'importer un prive (§7.27).
_CLAUSE_CONSULTANTS: Final[str] = """
EXISTS (
    SELECT 1 FROM dsm_assignment da
    WHERE da.consultant_membership_id = em.id AND da.dsm_person_id = :acteur
      AND da.entity_id = :entite AND da.archived_at IS NULL AND da.period @> :instant
)
"""

_CLAUSE_CERCLE: Final[str] = """
EXISTS (
    SELECT 1 FROM circle_membership cm
    JOIN framework_responsibility_assignment fra
      ON fra.circle_id = cm.circle_id AND fra.entity_id = cm.entity_id
    WHERE cm.entity_membership_id = em.id AND cm.archived_at IS NULL AND cm.period @> :instant
      AND fra.person_id = :acteur AND fra.entity_id = :entite
      AND fra.responsibility_type = :type_booster
      AND fra.archived_at IS NULL AND fra.period @> :instant
)
"""

_CLAUSES_PAR_PERIMETRE: Final[Mapping[PerimetreDuTableauDeBord, str]] = {
    PerimetreDuTableauDeBord.ENTITE: "TRUE",
    PerimetreDuTableauDeBord.CONSULTANTS: _CLAUSE_CONSULTANTS,
    PerimetreDuTableauDeBord.CERCLE: _CLAUSE_CERCLE,
}


@dataclasses.dataclass(frozen=True, slots=True)
class FiltresDeReporting:
    """L'axe transversal « Filtrer par periode, DSM, cercle, client » du
    §15.1, tous facultatifs — jamais une sixieme ligne separee."""

    depuis: dt.date | None = None
    jusqua: dt.date | None = None
    dsm: uuid.UUID | None = None
    cercle: uuid.UUID | None = None
    client: uuid.UUID | None = None


def _clause_de_filtres(filtres: FiltresDeReporting) -> tuple[str, dict[str, object]]:
    """Memes principes que `app.audit.lecture._clause_de_filtres` : une clause
    n'entre dans le texte SQL que si son axe est demande, aucune valeur
    interpolee (§7.27)."""
    membres: list[str] = []
    valeurs: dict[str, object] = {}
    if filtres.depuis is not None:
        membres.append("em.arrival_date >= :depuis")
        valeurs["depuis"] = filtres.depuis
    if filtres.jusqua is not None:
        membres.append("em.arrival_date <= :jusqua")
        valeurs["jusqua"] = filtres.jusqua
    if filtres.dsm is not None:
        membres.append(
            """
            EXISTS (
                SELECT 1 FROM dsm_assignment da_f
                WHERE da_f.consultant_membership_id = em.id AND da_f.dsm_person_id = :filtre_dsm
                  AND da_f.archived_at IS NULL AND da_f.period @> :instant
            )
            """
        )
        valeurs["filtre_dsm"] = filtres.dsm
    if filtres.cercle is not None:
        membres.append(
            """
            EXISTS (
                SELECT 1 FROM circle_membership cm_f
                WHERE cm_f.entity_membership_id = em.id AND cm_f.circle_id = :filtre_cercle
                  AND cm_f.archived_at IS NULL AND cm_f.period @> :instant
            )
            """
        )
        valeurs["filtre_cercle"] = filtres.cercle
    if filtres.client is not None:
        membres.append(
            """
            EXISTS (
                SELECT 1 FROM professional_status_assignment psa_f
                WHERE psa_f.entity_membership_id = em.id AND psa_f.client_id = :filtre_client
                  AND psa_f.ends_at IS NULL
            )
            """
        )
        valeurs["filtre_client"] = filtres.client
    if not membres:
        return "TRUE", valeurs
    return " AND ".join(membres), valeurs


def _parametres_de_base(
    *, entite: uuid.UUID, acteur: uuid.UUID, instant: dt.datetime, filtres: FiltresDeReporting
) -> tuple[str, dict[str, object]]:
    """La clause de filtres assemblee et les parametres COMMUNS a toute
    requete de ce module (entite/acteur/instant/type_booster), plus ceux des
    filtres eux-memes."""
    clause_filtres, valeurs_filtres = _clause_de_filtres(filtres)
    parametres: dict[str, object] = {
        "entite": entite,
        "acteur": acteur,
        "instant": instant,
        "type_booster": _TYPE_BOOSTER,
        **valeurs_filtres,
    }
    return clause_filtres, parametres


@dataclasses.dataclass(frozen=True, slots=True)
class RepartitionParGroupe:
    """Une ligne d'une des trois repartitions — §10.10."""

    id: uuid.UUID
    libelle: str
    profils_actifs: int


@dataclasses.dataclass(frozen=True, slots=True)
class ProgressionAgregee:
    """Le couple somme sur la portee — jamais un pourcentage stocke, meme
    philosophie que `Progression` (LOT 7, `T7`)."""

    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


@dataclasses.dataclass(frozen=True, slots=True)
class IndicateursDeReporting:
    """Ce que le tableau de bord (LOT 9, `T5`) ne sert pas — voir l'en-tete."""

    onboardings_termines: int
    progression_moyenne: ProgressionAgregee
    duree_moyenne_jours: float | None
    arrivees_30_jours: int
    repartition_par_cercle: tuple[RepartitionParGroupe, ...]
    repartition_par_client: tuple[RepartitionParGroupe, ...]
    repartition_par_dsm: tuple[RepartitionParGroupe, ...]


_ONBOARDINGS_TERMINES_ET_DUREE: Final = """
SELECT
    count(*) FILTER (WHERE oi.state = 'archived' AND oi.completed_at IS NOT NULL) AS termines,
    avg(EXTRACT(EPOCH FROM (oi.completed_at - oi.started_at)) / 86400.0)
        FILTER (WHERE oi.state = 'archived' AND oi.completed_at IS NOT NULL) AS duree_jours
FROM onboarding_instance oi
JOIN entity_membership em ON em.id = oi.entity_membership_id AND em.entity_id = oi.entity_id
WHERE oi.entity_id = :entite AND ({perimetre}) AND ({filtres})
"""

_PROGRESSION_MOYENNE: Final = """
SELECT
    coalesce(sum(CASE WHEN oit.required THEN 1 ELSE 0 END), 0) AS totales,
    coalesce(sum(CASE WHEN oit.required AND oit.state = 'completed' THEN 1 ELSE 0 END), 0)
        AS terminees
FROM onboarding_instance oi
JOIN entity_membership em ON em.id = oi.entity_membership_id AND em.entity_id = oi.entity_id
JOIN onboarding_instance_task oit
  ON oit.onboarding_instance_id = oi.id AND oit.entity_id = oi.entity_id
WHERE oi.entity_id = :entite AND oi.state = 'active' AND ({perimetre}) AND ({filtres})
"""

_ARRIVEES_30_JOURS: Final = """
SELECT count(*) FROM entity_membership em
WHERE em.entity_id = :entite AND em.membership_state = 'future'
  AND em.arrival_date >= :aujourd_hui AND em.arrival_date <= :borne_30_jours
  AND ({perimetre}) AND ({filtres})
"""

_REPARTITION_PAR_CERCLE: Final = """
SELECT c.id, c.name, count(*) AS profils_actifs
FROM entity_membership em
JOIN circle_membership cm ON cm.entity_membership_id = em.id AND cm.entity_id = em.entity_id
JOIN circle c ON c.id = cm.circle_id AND c.entity_id = em.entity_id
WHERE em.entity_id = :entite AND em.membership_state = 'active'
  AND cm.membership_type = 'principal' AND cm.ends_at IS NULL
  AND ({perimetre}) AND ({filtres})
GROUP BY c.id, c.name
ORDER BY c.name ASC, c.id ASC
"""

_REPARTITION_PAR_CLIENT: Final = """
SELECT cl.id, cl.display_name, count(*) AS profils_actifs
FROM entity_membership em
JOIN professional_status_assignment psa
  ON psa.entity_membership_id = em.id AND psa.entity_id = em.entity_id
JOIN client cl ON cl.id = psa.client_id
WHERE em.entity_id = :entite AND em.membership_state = 'active'
  AND psa.ends_at IS NULL AND psa.client_id IS NOT NULL
  AND ({perimetre}) AND ({filtres})
GROUP BY cl.id, cl.display_name
ORDER BY cl.display_name ASC, cl.id ASC
"""

_REPARTITION_PAR_DSM: Final = """
SELECT p.id, p.first_name, p.last_name, count(*) AS profils_actifs
FROM entity_membership em
JOIN dsm_assignment da ON da.consultant_membership_id = em.id AND da.entity_id = em.entity_id
JOIN person p ON p.id = da.dsm_person_id
WHERE em.entity_id = :entite AND em.membership_state = 'active'
  AND da.archived_at IS NULL AND da.period @> :instant
  AND ({perimetre}) AND ({filtres})
GROUP BY p.id, p.first_name, p.last_name
ORDER BY p.last_name ASC, p.first_name ASC, p.id ASC
"""


def lire_les_indicateurs(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDuTableauDeBord,
    instant: dt.datetime,
    filtres: FiltresDeReporting | None = None,
) -> IndicateursDeReporting:
    """Les grandeurs scalaires et les trois repartitions, dans la portee
    deja resolue — voir l'en-tete du module pour chaque formule."""
    clause_filtres, parametres = _parametres_de_base(
        entite=entite, acteur=acteur, instant=instant, filtres=filtres or FiltresDeReporting()
    )
    clause_perimetre = _CLAUSES_PAR_PERIMETRE[perimetre]

    requete_termines_duree = text(
        _ONBOARDINGS_TERMINES_ET_DUREE.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    ligne = connexion.execute(requete_termines_duree, parametres).one()
    onboardings_termines = int(ligne.termines)
    duree_moyenne_jours = float(ligne.duree_jours) if ligne.duree_jours is not None else None

    requete_progression = text(
        _PROGRESSION_MOYENNE.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    ligne_progression = connexion.execute(requete_progression, parametres).one()
    progression_moyenne = ProgressionAgregee(
        taches_obligatoires_totales=int(ligne_progression.totales),
        taches_obligatoires_terminees=int(ligne_progression.terminees),
    )

    aujourd_hui = instant.date()
    requete_arrivees = text(
        _ARRIVEES_30_JOURS.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    arrivees_30_jours = int(
        connexion.execute(
            requete_arrivees,
            {
                **parametres,
                "aujourd_hui": aujourd_hui,
                "borne_30_jours": aujourd_hui + dt.timedelta(days=30),
            },
        ).scalar_one()
    )

    requete_cercle = text(
        _REPARTITION_PAR_CERCLE.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    repartition_par_cercle = tuple(
        RepartitionParGroupe(
            id=ligne.id, libelle=ligne.name, profils_actifs=int(ligne.profils_actifs)
        )
        for ligne in connexion.execute(requete_cercle, parametres).all()
    )
    requete_client = text(
        _REPARTITION_PAR_CLIENT.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    repartition_par_client = tuple(
        RepartitionParGroupe(
            id=ligne.id, libelle=ligne.display_name, profils_actifs=int(ligne.profils_actifs)
        )
        for ligne in connexion.execute(requete_client, parametres).all()
    )
    requete_dsm = text(
        _REPARTITION_PAR_DSM.format(perimetre=clause_perimetre, filtres=clause_filtres)
    )
    repartition_par_dsm = tuple(
        RepartitionParGroupe(
            id=ligne.id,
            libelle=f"{ligne.first_name} {ligne.last_name}",
            profils_actifs=int(ligne.profils_actifs),
        )
        for ligne in connexion.execute(requete_dsm, parametres).all()
    )

    return IndicateursDeReporting(
        onboardings_termines=onboardings_termines,
        progression_moyenne=progression_moyenne,
        duree_moyenne_jours=duree_moyenne_jours,
        arrivees_30_jours=arrivees_30_jours,
        repartition_par_cercle=repartition_par_cercle,
        repartition_par_client=repartition_par_client,
        repartition_par_dsm=repartition_par_dsm,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class OnboardingDuDetail:
    """Une ligne de « Consulter le detail onboarding » — §15.1, la progression
    PAR PERSONNE du §10.10, sur une instance ACTIVE (voir l'en-tete)."""

    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    reference_date: dt.date
    started_at: dt.datetime
    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeDetailOnboarding:
    """Une page, et le total de la population — pas de la page."""

    elements: list[OnboardingDuDetail]
    total: int


#  FROM/JOIN/WHERE assembles EN UN SEUL BLOC : la jointure LATERAL doit
#  precede le WHERE en SQL, jamais le suivre — §7.0, sixieme proposition,
#  appliquee a la FORME de la requete plutot qu'a une grandeur mesuree.
_DETAIL_ONBOARDING_SOURCE: Final = """
FROM onboarding_instance oi
JOIN entity_membership em ON em.id = oi.entity_membership_id AND em.entity_id = oi.entity_id
JOIN person p ON p.id = em.person_id
LEFT JOIN LATERAL (
    SELECT sum(CASE WHEN oit.required THEN 1 ELSE 0 END) AS totales,
           sum(CASE WHEN oit.required AND oit.state = 'completed' THEN 1 ELSE 0 END) AS terminees
    FROM onboarding_instance_task oit
    WHERE oit.onboarding_instance_id = oi.id AND oit.entity_id = oi.entity_id
) prog ON TRUE
WHERE oi.entity_id = :entite AND oi.state = 'active' AND ({perimetre}) AND ({filtres})
"""

_SELECT_DETAIL_ONBOARDING: Final = """
SELECT em.id AS appartenance_id, p.id AS person_id, p.first_name, p.last_name,
       oi.reference_date, oi.started_at,
       coalesce(prog.totales, 0) AS taches_obligatoires_totales,
       coalesce(prog.terminees, 0) AS taches_obligatoires_terminees
{source}
ORDER BY p.last_name ASC, p.first_name ASC, em.id ASC
LIMIT :taille OFFSET :decalage
"""

_COMPTER_DETAIL_ONBOARDING: Final = "SELECT count(*) {source}"


def lister_le_detail_onboarding(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDuTableauDeBord,
    page: int,
    taille: int,
    instant: dt.datetime,
    filtres: FiltresDeReporting | None = None,
) -> PageDeDetailOnboarding:
    """La page demandee du detail onboarding — « Consulter le detail
    onboarding » du §15.1 — dans la portee deja resolue, et le total."""
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    clause_filtres, parametres = _parametres_de_base(
        entite=entite, acteur=acteur, instant=instant, filtres=filtres or FiltresDeReporting()
    )
    clause_perimetre = _CLAUSES_PAR_PERIMETRE[perimetre]
    source = _DETAIL_ONBOARDING_SOURCE.format(perimetre=clause_perimetre, filtres=clause_filtres)

    requete_compte = text(_COMPTER_DETAIL_ONBOARDING.format(source=source))
    total = int(connexion.execute(requete_compte, parametres).scalar_one())

    requete_page = text(_SELECT_DETAIL_ONBOARDING.format(source=source))
    lignes = (
        connexion.execute(
            requete_page, {**parametres, "taille": taille, "decalage": (page - 1) * taille}
        )
        .mappings()
        .all()
    )

    return PageDeDetailOnboarding(
        elements=[_en_detail_onboarding(ligne) for ligne in lignes], total=total
    )


def _en_detail_onboarding(ligne: Any) -> OnboardingDuDetail:
    return OnboardingDuDetail(
        appartenance_id=ligne["appartenance_id"],
        person_id=ligne["person_id"],
        first_name=ligne["first_name"],
        last_name=ligne["last_name"],
        reference_date=ligne["reference_date"],
        started_at=ligne["started_at"],
        taches_obligatoires_totales=int(ligne["taches_obligatoires_totales"]),
        taches_obligatoires_terminees=int(ligne["taches_obligatoires_terminees"]),
    )


@dataclasses.dataclass(frozen=True, slots=True)
class ProfilIncomplet:
    """Une ligne de « Consulter les profils incomplets » — §15.1, le DETAIL
    que le tableau de bord (LOT 9, `T5`) ne rend qu'en compte.

    Les quatre booleens reprennent EXACTEMENT la regle de
    `app.administration.tableau_de_bord._COMPTER_PROFILS_INCOMPLETS` — un
    profil actif y est compte des qu'au moins un des quatre vaut `True`."""

    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    metier_manquant: bool
    cercle_principal_manquant: bool
    dsm_manquant: bool
    statut_manquant: bool


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeProfilsIncomplets:
    """Une page, et le total de la population — pas de la page."""

    elements: list[ProfilIncomplet]
    total: int


#  Les QUATRE relations organisationnelles courantes — copie LITTERALE de la
#  regle de `app.administration.tableau_de_bord` (§7.27 : meme regle, redite
#  pour un DETAIL plutot qu'un compte, jamais une seconde definition).
_QUATRE_RELATIONS_MANQUANTES: Final = """
(
    NOT EXISTS (
        SELECT 1 FROM membership_job_assignment mja
        WHERE mja.entity_membership_id = em.id AND mja.ends_at IS NULL
    )
    OR NOT EXISTS (
        SELECT 1 FROM circle_membership cm
        WHERE cm.entity_membership_id = em.id AND cm.membership_type = 'principal'
          AND cm.ends_at IS NULL
    )
    OR NOT EXISTS (
        SELECT 1 FROM dsm_assignment da
        WHERE da.consultant_membership_id = em.id AND da.ends_at IS NULL
    )
    OR NOT EXISTS (
        SELECT 1 FROM professional_status_assignment psa
        WHERE psa.entity_membership_id = em.id AND psa.ends_at IS NULL
    )
)
"""

_PROFILS_INCOMPLETS_SOURCE: Final = f"""
FROM entity_membership em
JOIN person p ON p.id = em.person_id
WHERE em.entity_id = :entite AND em.membership_state = 'active'
  AND ({{perimetre}}) AND ({{filtres}})
  AND {_QUATRE_RELATIONS_MANQUANTES}
"""

_SELECT_PROFILS_INCOMPLETS: Final = """
SELECT em.id AS appartenance_id, p.id AS person_id, p.first_name, p.last_name,
    NOT EXISTS (
        SELECT 1 FROM membership_job_assignment mja
        WHERE mja.entity_membership_id = em.id AND mja.ends_at IS NULL
    ) AS metier_manquant,
    NOT EXISTS (
        SELECT 1 FROM circle_membership cm
        WHERE cm.entity_membership_id = em.id AND cm.membership_type = 'principal'
          AND cm.ends_at IS NULL
    ) AS cercle_principal_manquant,
    NOT EXISTS (
        SELECT 1 FROM dsm_assignment da
        WHERE da.consultant_membership_id = em.id AND da.ends_at IS NULL
    ) AS dsm_manquant,
    NOT EXISTS (
        SELECT 1 FROM professional_status_assignment psa
        WHERE psa.entity_membership_id = em.id AND psa.ends_at IS NULL
    ) AS statut_manquant
{source}
ORDER BY p.last_name ASC, p.first_name ASC, em.id ASC
LIMIT :taille OFFSET :decalage
"""

_COMPTER_PROFILS_INCOMPLETS_DETAIL: Final = "SELECT count(*) {source}"


def lister_les_profils_incomplets(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDuTableauDeBord,
    page: int,
    taille: int,
    instant: dt.datetime,
    filtres: FiltresDeReporting | None = None,
) -> PageDeProfilsIncomplets:
    """La page demandee des profils incomplets — « Consulter les profils
    incomplets » du §15.1 — dans la portee deja resolue, et le total."""
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    clause_filtres, parametres = _parametres_de_base(
        entite=entite, acteur=acteur, instant=instant, filtres=filtres or FiltresDeReporting()
    )
    clause_perimetre = _CLAUSES_PAR_PERIMETRE[perimetre]
    source = _PROFILS_INCOMPLETS_SOURCE.format(perimetre=clause_perimetre, filtres=clause_filtres)

    requete_compte = text(_COMPTER_PROFILS_INCOMPLETS_DETAIL.format(source=source))
    total = int(connexion.execute(requete_compte, parametres).scalar_one())

    requete_page = text(_SELECT_PROFILS_INCOMPLETS.format(source=source))
    lignes = (
        connexion.execute(
            requete_page, {**parametres, "taille": taille, "decalage": (page - 1) * taille}
        )
        .mappings()
        .all()
    )

    return PageDeProfilsIncomplets(
        elements=[_en_profil_incomplet(ligne) for ligne in lignes], total=total
    )


def _en_profil_incomplet(ligne: Any) -> ProfilIncomplet:
    return ProfilIncomplet(
        appartenance_id=ligne["appartenance_id"],
        person_id=ligne["person_id"],
        first_name=ligne["first_name"],
        last_name=ligne["last_name"],
        metier_manquant=bool(ligne["metier_manquant"]),
        cercle_principal_manquant=bool(ligne["cercle_principal_manquant"]),
        dsm_manquant=bool(ligne["dsm_manquant"]),
        statut_manquant=bool(ligne["statut_manquant"]),
    )
