"""Services transactionnels de l'organisation — modele §25.4.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`.

CE SERVICE REFERME LA BOUCLE DE `DEC-514`

  Le modele §8.4 ecrit : « un DG recoit **automatiquement** une responsabilite DSM
  dans la meme transaction que son attribution de categorie ». `T10` a pose
  l'IMPLICATION en base -- le declencheur `dg_implique_dsm_local` refuse une
  categorie `dg` sans responsabilite `DSM` active dans la meme entite -- et a
  laisse l'ACTION au service, pour un motif precis :

    `assigned_by_person_id` est `NOT NULL`, et **un declencheur ne sait pas qui
    attribue**. Inventer un attributeur -- la personne elle-meme, un identifiant
    technique -- fabriquerait une trace d'audit FAUSSE, ce qui est pire qu'une
    trace absente. La matrice §5.1 exige que les interventions sensibles soient
    auditees.

  Un service, lui, connait l'auteur : il le recoit. **Il SATISFAIT l'invariant du
  declencheur, il ne s'y substitue pas** -- si le service etait contourne, la base
  refuserait toujours. C'est la doctrine de `DEC-498`.

L'ORDRE N'EST PAS UN DETAIL

  Le declencheur s'execute a l'`INSERT` comme a l'`UPDATE` de
  `entity_membership`. La responsabilite `DSM` doit donc exister **AVANT** que la
  categorie ne devienne `dg`. Un service qui ferait l'inverse echouerait, et
  c'est precisement ce qu'il evite a son appelant d'avoir a savoir.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CATEGORIE_DIRECTION_GENERALE = "dg"
RESPONSABILITE_DSM = "DSM"

#  LOT 3, `T5` — LA DETTE QUE `T11` DU LOT 2 A LAISSEE, ET ELLE EST ACQUITTEE ICI.
#
#  Le §8.4 du modele exige que l'attributeur d'une categorie `dg` soit « ESM ou
#  super-administrateur ». `T11` avait pose l'attributeur en parametre OBLIGATOIRE
#  -- « un declencheur ne sait pas qui attribue, et inventer un attributeur
#  fabriquerait une trace d'audit FAUSSE » -- et laisse la verification du droit a
#  ce lot, « ou les roles d'administration existeront ».
#
#  LES DEUX DROITS NE VIVENT PAS DANS LA MEME TABLE, ET C'EST LE POINT :
#
#    ESM          responsabilite FRAMEWORK, `framework_responsibility_assignment`,
#                 **portee sur UNE entite** (§8.4). Un ESM de Bordeaux n'attribue
#                 donc rien a Lyon.
#    SUPER_ADMIN  role TECHNIQUE, `technical_role_assignment`, **global**, et le
#                 §8.6 impose `entity_id` NUL pour lui. La matrice §... le dit
#                 aussi : « le super-administrateur constitue la seule exception
#                 globale ».
#
#  Les confondre donnerait a un ESM une portee globale, ou refuserait au
#  super-administrateur ce que la matrice lui accorde partout.
RESPONSABILITE_ESM = "ESM"
ROLE_SUPER_ADMINISTRATEUR = "SUPER_ADMIN"


class ErreurDeService(RuntimeError):
    """Une regle metier que le service porte, et que la base ne peut pas porter seule."""


def responsabilite_dsm_active(
    connexion: Connection, *, entite: uuid.UUID, personne: uuid.UUID
) -> uuid.UUID | None:
    """Rendre l'identifiant de la responsabilite `DSM` active de la personne, dans CETTE entite.

    **ELLE FILTRAIT SUR `ends_at IS NULL` SEUL JUSQU'AU 09/09/2026, ET C'ETAIT UN
    DEFAUT LATENT** -- `ECART-056`, trouve en ouvrant `T7` du LOT 5, qui est la
    premiere ecriture metier et allait consommer ce predicat.

    Une affectation FUTURE, dont `starts_at` est a venir, a elle aussi un
    `ends_at` nul. Aucune contrainte ne l'interdit : mesure du 09/09/2026, les
    deux seuls `CHECK` de `framework_responsibility_assignment` portent sur le
    type et sur la portee, pas sur le temps.

    **LE SCENARIO D'ECHEC EST PRECIS.** `attribuer_la_categorie_dg` SAUTE la
    creation de la responsabilite quand cette fonction rend non-`None`. Une
    personne promue DG aujourd'hui, portant une responsabilite DSM programmee le
    mois prochain, n'obtenait donc AUCUNE responsabilite DSM active -- alors que
    le §8.4 l'exige -- et l'action rendait un succes.

    **ET LA FONCTION JUSTE EN DESSOUS DOCUMENTAIT DEJA POURQUOI** : dix lignes du
    docstring de `peut_attribuer_la_categorie_dg` expliquent que
    « `ends_at IS NULL` ne suffirait pas », et elle emploie `period @> :instant`.
    Deux fonctions voisines repondaient a la meme question differemment. C'etait
    la seule requete applicative du depot a filtrer ainsi -- tout le code des
    LOTS 4 et 5 emploie `period @> :instant`.

    **L'instant est releve ici et non passe en argument**, comme le fait
    `peut_attribuer_la_categorie_dg` juste en dessous : changer la signature
    aurait touche ses deux appelants pour un gain nul, et le §7.27 vaut aussi
    pour la coherence entre voisines.
    """
    return connexion.execute(
        text(
            "SELECT id FROM framework_responsibility_assignment "
            "WHERE person_id = :personne AND entity_id = :entite "
            "  AND responsibility_type = :type_responsabilite "
            "  AND archived_at IS NULL AND period @> :instant "
            "LIMIT 1"
        ),
        {
            "personne": personne,
            "entite": entite,
            "type_responsabilite": RESPONSABILITE_DSM,
            "instant": dt.datetime.now(tz=dt.UTC),
        },
    ).scalar_one_or_none()


def peut_attribuer_la_categorie_dg(
    connexion: Connection, *, entite: uuid.UUID, personne: uuid.UUID
) -> bool:
    """La personne peut-elle attribuer la categorie `dg` DANS cette entite ?

    §8.4 : « ESM ou super-administrateur ». Deux tables, deux portees, une seule
    question -- et **les periodes sont exigees dans les deux cas** : le §25.2 pose
    l'historisation de ces deux relations, et un role CLOTURE ne doit plus rien
    accorder. C'est litteralement le controle §24.12 du cahier, « un role cloture
    ne continue pas a accorder des permissions ».

    `ends_at IS NULL` **ne suffirait pas** : une affectation FUTURE, dont
    `starts_at` est a venir, a elle aussi `ends_at` nul. La colonne generee
    `period` porte la plage complete, et `@>` repond a la vraie question -- « ce
    droit est-il actif A CET INSTANT ».
    """
    return bool(
        connexion.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM framework_responsibility_assignment "
                "  WHERE person_id = :personne_esm AND entity_id = :entite "
                "    AND responsibility_type = :type_responsabilite "
                "    AND period @> :instant_esm"
                ") OR EXISTS ("
                "  SELECT 1 FROM technical_role_assignment "
                "  WHERE person_id = :personne_super AND role_type = :type_role "
                "    AND entity_id IS NULL "
                "    AND period @> :instant_super"
                ")"
            ),
            #  Des noms DISTINCTS pour chaque emploi : un meme parametre lie a
            #  deux colonnes rend « inconsistent types deduced for parameter »,
            #  et le message ne nomme ni la table ni la colonne. §7.25.
            {
                "personne_esm": personne,
                "personne_super": personne,
                "entite": entite,
                "type_responsabilite": RESPONSABILITE_ESM,
                "type_role": ROLE_SUPER_ADMINISTRATEUR,
                "instant_esm": dt.datetime.now(tz=dt.UTC),
                "instant_super": dt.datetime.now(tz=dt.UTC),
            },
        ).scalar_one()
    )


def attribuer_la_categorie_dg(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    attribue_par: uuid.UUID,
    debut: dt.datetime | None = None,
    motif: str | None = None,
) -> uuid.UUID:
    """Attribuer la categorie `dg` a une appartenance, en creant la responsabilite `DSM`.

    Rend l'identifiant de la responsabilite `DSM`, creee ou deja existante.

    `attribue_par` est **obligatoire** et n'a pas de defaut : c'est tout le motif
    pour lequel cette action est un service et non un declencheur.

    **SON DROIT EST DESORMAIS VERIFIE** — LOT 3, `T5`. Le §8.4 veut « ESM ou
    super-administrateur », et `peut_attribuer_la_categorie_dg` repond. La phrase
    « cette verification releve du LOT 3 » etait juste quand elle a ete ecrite en
    `T11` du LOT 2 ; elle ne l'est plus, et la corriger vaut mieux que de la
    laisser vieillir — §7.21.

    Raises:
        ErreurDeService: si l'attributeur n'a pas le droit, ou si l'appartenance
            est inconnue de cette entite.
    """
    #  LE DROIT EST VERIFIE AVANT TOUT, ET AVANT MEME DE LIRE L'APPARTENANCE.
    #
    #  L'ordre n'est pas cosmetique : lire la ressource d'abord permettrait de
    #  distinguer « appartenance inconnue » de « droit refuse », donc de sonder
    #  l'existence d'une appartenance sans avoir le droit d'y toucher. Le §2.5
    #  pose le refus par defaut.
    if not peut_attribuer_la_categorie_dg(connexion, entite=entite, personne=attribue_par):
        message = (
            f"la personne {attribue_par} n'est ni ESM de l'entite {entite} ni "
            "super-administrateur : le §8.4 lui refuse l'attribution de la categorie dg"
        )
        raise ErreurDeService(message)

    ligne = connexion.execute(
        text(
            "SELECT person_id, entity_id FROM entity_membership "
            "WHERE id = :appartenance AND entity_id = :entite"
        ),
        {"appartenance": appartenance, "entite": entite},
    ).one_or_none()
    if ligne is None:
        #  `None` couvre deux cas indistinguables a dessein : l'appartenance
        #  n'existe pas, ou elle est d'une AUTRE entite. Le §2.5 « refus par
        #  defaut » veut qu'on ne revele pas l'existence d'une ressource d'une
        #  autre entite -- meme raisonnement que `DepotLocal.obtenir`.
        message = f"appartenance {appartenance} inconnue dans l'entite {entite}"
        raise ErreurDeService(message)
    personne = ligne[0]

    existante = responsabilite_dsm_active(connexion, entite=entite, personne=personne)
    if existante is None:
        #  L'ORDRE EST IMPOSE PAR LE DECLENCHEUR : la responsabilite d'abord.
        existante = connexion.execute(
            text(
                "INSERT INTO framework_responsibility_assignment "
                "(person_id, entity_id, responsibility_type, assigned_by_person_id, "
                " starts_at, assignment_reason) "
                "VALUES (:personne, :entite, :type_responsabilite, :auteur, :debut, :motif) "
                "RETURNING id"
            ),
            {
                "personne": personne,
                "entite": entite,
                "type_responsabilite": RESPONSABILITE_DSM,
                "auteur": attribue_par,
                "debut": debut or dt.datetime.now(tz=dt.UTC),
                "motif": motif,
            },
        ).scalar_one()

    connexion.execute(
        text(
            "UPDATE entity_membership SET professional_category = :categorie, "
            "updated_by_person_id = :auteur, version = version + 1 "
            "WHERE id = :appartenance AND entity_id = :entite"
        ),
        {
            "categorie": CATEGORIE_DIRECTION_GENERALE,
            "auteur": attribue_par,
            "appartenance": appartenance,
            "entite": entite,
        },
    )
    return existante
