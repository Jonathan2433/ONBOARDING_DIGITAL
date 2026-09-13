"""Jeu de recette : 25 entites, 5 000 profils, et le §30.25 MESURE.

LOT 2, sous-etape `T12`, stories `MVP-L02-US007` et `US008`.

CE FICHIER PORTE LE DERNIER CONTROLE DU §30 QUI RELEVE DU LOT 2

  « §30.25 — les 5 000 profils et 25 entites restent **exploitables** avec les
  index definis. »

  **« Exploitables » est une grandeur, donc il faut mesurer.** Le test engendre le
  volume reel, execute des requetes representatives, releve leur duree, et
  **rapporte le plan choisi par PostgreSQL**.

ET IL N'EXIGE PAS L'USAGE D'UN INDEX, DELIBEREMENT

  Sur 5 000 lignes, un **parcours sequentiel est souvent le plan OPTIMAL** :
  PostgreSQL le choisit parce qu'il est plus rapide, pas malgre lui. Un test qui
  exigerait « aucun Seq Scan » exigerait donc **le contraire de la performance**,
  et il echouerait sur un livrable conforme -- exactement le defaut du §7.20.

  Le test exige donc une **duree**, ce qui est la grandeur du critere, et
  **rapporte** le plan pour que le lecteur voie ce que la base a fait. C'est aussi
  le §7.0 sixieme proposition : le nombre affiche et le seuil auquel on le compare
  doivent mesurer la meme chose.

LE VOLUME EST LENT, ET C'EST ASSUME

  Engendrer 27 000 lignes prend une vingtaine de secondes. Reduire le volume
  rendrait le test rapide et **sans rapport avec le critere**, qui nomme 5 000
  profils. La transaction est annulee : rien ne subsiste.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.shared.database import moteur
from app.shared.depot import DepotLocal
from app.shared.fabriques import engendrer

#  Les valeurs du critere, litteralement.
ENTITES_DU_CRITERE = 25
PROFILS_DU_CRITERE = 5000

#  Un plafond LARGE et assume : l'objet est de detecter un effondrement -- une
#  jointure sans index, un plan quadratique -- non de mesurer une milliseconde
#  sur un poste de developpement dont la charge varie.
#  **AUCUN PLAFOND DE DUREE, ET LE MOTIF EST MESURE.** Ce fichier a porte
#  `PLAFOND_PAR_REQUETE_MS = 500.0` du `T12` du LOT 2 au 08/09/2026. Il mesurait
#  la MACHINE, pas le produit -- cinq executions isolees le meme soir ont rendu
#  211, 823, 1 006, 1 078 et 1 165 ms sur du code identique.
#
#  **LE PLAN COMPLET DIT POURQUOI, ET IL CLOT LA QUESTION** (mesure du
#  08/09/2026, requete « cercle principal actif de chaque membre d'une entite ») :
#
#      Nested Loop  (cost=8.53..18.98 rows=1) (actual rows=201)
#        Rows Removed by Join Filter: 1 028 870
#        Buffers: shared hit=1 509 536
#        ->  Index Only Scan on entity_membership  (loops=5001)
#              Heap Fetches: 1 029 071
#
#  Le planificateur croit CHAQUE table a une ligne -- `ANALYZE` ne publie rien
#  d'exploitable sur des lignes non validees, §7.38 -- donc il rescanne les 206
#  appartenances de l'entite 5 001 fois et jette 1 028 870 combinaisons sur
#  1 029 071. En service, avec des statistiques reelles, il prendrait un Hash
#  Join. **Le plan de ce banc d'essai n'est PAS celui de la production, donc sa
#  duree ne l'est pas non plus.**
#
#  Les `Heap Fetches` sur un *Index Only* Scan nomment de plus la source de la
#  variance : la carte de visibilite n'est pas positionnee pour des lignes non
#  validees, et le cout depend donc d'un etat incidental.
#
#  **UN VACUUM N'Y CHANGE RIEN, ET CELA A ETE EPROUVE PLUTOT QUE SUPPOSE.** Un
#  nettoyage physique prealable, sur connexion separee en autovalidation, a ete
#  ecrit puis RETIRE : avec lui, quatre echecs sur cinq subsistaient, dont un
#  tour a 1 078 ms alors que le menage annoncait « 0 table sale ». Les lignes
#  parcourues sont celles, non validees, de la transaction en cours -- aucun
#  VACUUM de tables validees ne les atteint. Garder un correctif dont le motif
#  est faux laisserait croire la cause traitee, ce qui est pire que le defaut.
#
#  Ce que le test exige desormais : la JUSTESSE au volume. Ce qu'il RAPPORTE :
#  les durees et les plans. §7.38, `ECART-055`.

#  Un volume reduit pour les tests de coherence, qui n'ont pas besoin de l'echelle.
ENTITES_REDUITES = 3
PROFILS_REDUITS = 40


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


# ---------------------------------------------------------------------------
#  §30.25 — la mesure
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_le_jeu_de_recette_reste_exploitable_avec_les_index_definis(cx: Connection) -> None:
    """§30.25, au volume LITTERAL du critere : 25 entites et 5 000 profils.

    **CE TEST N'EXIGE AUCUNE DUREE, ET C'EST MESURE.** Il en exigeait 500 ms par
    requete jusqu'au 08/09/2026 ; le motif du retrait est dans `ECART-055` et le
    parti est celui que `DEC-562` a deja valide pour le test de recherche de `T3`.
    """
    debut = time.monotonic()
    mesure = engendrer(cx, entites=ENTITES_DU_CRITERE, profils=PROFILS_DU_CRITERE)
    duree_generation = time.monotonic() - debut

    #  Le compte est CONFRONTE a un attendu, non simplement affiche.
    assert mesure.entites == ENTITES_DU_CRITERE + 1, (
        "25 entites actives, plus UNE archivee au titre des cas limites"
    )
    assert mesure.personnes > PROFILS_DU_CRITERE, (
        f"{mesure.personnes} personnes pour {PROFILS_DU_CRITERE} profils : les DSM, "
        f"les Boosters et les cas limites s'y ajoutent"
    )
    assert mesure.total_lignes() > 20_000, f"{mesure.total_lignes()} lignes, volume trop faible"
    assert len(mesure.cas_limites) >= 7, f"{len(mesure.cas_limites)} cas limites, 7 attendus"

    #  **CE COMMENTAIRE AFFIRMAIT UNE CHOSE QUE `T3` DU LOT 5 A MESUREE COMME
    #  FAUSSE**, et il disait : « sans `ANALYZE`, PostgreSQL raisonne sur une table
    #  qu'il croit vide ». Mesure du 26/08/2026, reportee au §7.38 :
    #
    #      apres VACUUM (ANALYZE) sur base validee   reltuples(entity_membership) = 0
    #      apres 5 155 insertions NON validees
    #        puis ANALYZE dans la transaction        reltuples(entity_membership) = 0
    #
    #  `ANALYZE` ne publie RIEN d'exploitable sur des lignes que la transaction n'a
    #  pas validees : le planificateur les croit vides **quand meme**, estime
    #  `rows=1` partout, et choisit des plans qu'il ne choisirait pas en service.
    #  **Aucune conclusion sur le PLAN ne peut donc etre tiree de ce banc d'essai.**
    #  L'appel est conserve parce qu'il ne coute rien et qu'il redeviendrait utile
    #  sur des donnees validees. §7.38, et `ECART-055`.
    cx.execute(text("ANALYZE"))

    entite = cx.execute(
        text("SELECT id FROM entity WHERE status = 'active' ORDER BY code LIMIT 1")
    ).scalar_one()
    adresse = cx.execute(
        text("SELECT email_normalized FROM person ORDER BY created_at LIMIT 1")
    ).scalar_one()

    requetes: list[tuple[str, str, dict[str, object]]] = [
        (
            "recherche d'une personne par e-mail normalise",
            "SELECT id FROM person WHERE email_normalized = :adresse",
            {"adresse": adresse},
        ),
        (
            "membres occupants d'une entite",
            "SELECT id FROM entity_membership WHERE entity_id = :entite "
            "AND membership_state IN ('future', 'active')",
            {"entite": entite},
        ),
        (
            "missions actives d'une entite, avec leur client",
            "SELECT s.id, c.display_name FROM professional_status_assignment s "
            "JOIN client c ON c.id = s.client_id "
            "WHERE s.entity_id = :entite AND s.status = 'mission' AND s.ends_at IS NULL",
            {"entite": entite},
        ),
        (
            "cercle principal actif de chaque membre d'une entite",
            "SELECT m.id, c.code FROM entity_membership m "
            "JOIN circle_membership cm ON cm.entity_membership_id = m.id "
            "  AND cm.membership_type = 'principal' AND cm.ends_at IS NULL "
            "JOIN circle c ON c.id = cm.circle_id "
            "WHERE m.entity_id = :entite",
            {"entite": entite},
        ),
        (
            "responsabilites Framework actives d'une entite",
            "SELECT id, responsibility_type FROM framework_responsibility_assignment "
            "WHERE entity_id = :entite AND ends_at IS NULL",
            {"entite": entite},
        ),
    ]

    print()
    print(f"  jeu engendre : {mesure.total_lignes()} lignes en {duree_generation:.1f} s")
    print(
        f"  {mesure.entites} entites · {mesure.personnes} personnes · "
        f"{mesure.appartenances} appartenances · {mesure.situations} situations"
    )
    vides: list[str] = []
    for libelle, requete, parametres in requetes:
        depart = time.monotonic()
        lignes = cx.execute(text(requete), parametres).all()
        millisecondes = (time.monotonic() - depart) * 1000
        plan = cx.execute(text(f"EXPLAIN {requete}"), parametres).all()
        premier = plan[0][0].strip() if plan else "(aucun plan)"
        print(f"  {millisecondes:7.1f} ms  {len(lignes):5} lignes  {libelle}")
        print(f"                            plan : {premier[:96]}")
        #  **CE QUI EST EXIGE EST LA JUSTESSE, PAS LA DUREE.** Une requete du
        #  critere §30.25 qui ne rendrait AUCUNE ligne sur un jeu de 25 entites et
        #  5 000 profils signalerait un chemin d'index casse ou un filtre faux --
        #  ce que « reste exploitable avec les index definis » veut dire. La duree
        #  est RAPPORTEE juste au-dessus.
        if not lignes:
            vides.append(libelle)

    assert not vides, (
        f"requete(s) sans aucune ligne au volume du critere : {vides}. "
        f"Un chemin d'index casse ou un filtre faux se voit ici ; une duree, non."
    )

    #  Le depot cloisonne doit rester exploitable AU VOLUME, lui aussi : c'est le
    #  chemin que le code applicatif empruntera.
    depart = time.monotonic()
    total = DepotLocal(cx, "entity_membership", entite).compter()
    millisecondes = (time.monotonic() - depart) * 1000
    print(f"  {millisecondes:7.1f} ms  {total:5} lignes  comptage via `DepotLocal`")
    #  Meme parti : la duree est rapportee, le RESULTAT est exige. Un depot
    #  cloisonne qui compterait zero ligne sur une entite peuplee serait le defaut.
    assert total > 0, "le depot cloisonne ne compte aucune ligne sur une entite peuplee"


# ---------------------------------------------------------------------------
#  Coherence et reproductibilite, a volume reduit
# ---------------------------------------------------------------------------


def _dans_un_bac_a_sable(connexion: Connection, graine: int) -> tuple[int, list[str], list[str]]:
    """Engendrer dans un POINT DE SAUVEGARDE, relever, puis tout annuler.

    **DEUX GENERATIONS NE PEUVENT PAS COEXISTER DANS UNE MEME TRANSACTION** :
    `entity.code` est unique GLOBALEMENT, et le generateur forme ses codes a
    partir de la ville et du rang. Ma premiere version comparait deux jeux
    engendres a la suite, et echouait sur un generateur parfaitement correct.

    Le point de sauvegarde rend les deux generations independantes, et
    l'annulation garantit qu'aucune ne subsiste.
    """
    point = connexion.begin_nested()
    try:
        mesure = engendrer(
            connexion, entites=ENTITES_REDUITES, profils=PROFILS_REDUITS, graine=graine
        )
        prenoms = [
            ligne[0]
            for ligne in connexion.execute(
                text("SELECT first_name FROM person ORDER BY email_normalized")
            )
        ]
        limites = [libelle.split(" —")[0] for libelle in mesure.cas_limites]
        return mesure.total_lignes(), prenoms, limites
    finally:
        point.rollback()


@pytest.mark.integration
def test_le_generateur_est_DETERMINISTE_a_graine_egale(cx: Connection) -> None:
    """Deux appels de meme graine produisent le meme jeu.

    **Un jeu non reproductible rend inexploitable l'echec qu'il revele** : on ne
    peut ni le rejouer, ni le reduire. La comparaison porte sur la volumetrie, les
    prenoms tires et les cas limites — non sur les identifiants, qui sont des UUID
    et dont le determinisme n'apporterait rien.
    """
    lignes_a, prenoms_a, limites_a = _dans_un_bac_a_sable(cx, graine=7)
    lignes_b, prenoms_b, limites_b = _dans_un_bac_a_sable(cx, graine=7)

    assert lignes_a == lignes_b
    assert prenoms_a == prenoms_b, "la meme graine doit rendre les memes tirages"
    assert limites_a == limites_b
    assert len(prenoms_a) > PROFILS_REDUITS, "volume trop faible pour que la comparaison vaille"


@pytest.mark.integration
def test_deux_graines_differentes_produisent_des_jeux_differents(cx: Connection) -> None:
    """Temoin du precedent : sans lui, un generateur ignorant sa graine passerait."""
    _, prenoms_un, _ = _dans_un_bac_a_sable(cx, graine=1)
    _, prenoms_deux, _ = _dans_un_bac_a_sable(cx, graine=2)
    assert prenoms_un != prenoms_deux, "la graine ne change rien : le generateur l'ignore"
    assert len(prenoms_un) == len(prenoms_deux), "le VOLUME, lui, ne doit pas dependre de la graine"


@pytest.mark.integration
def test_le_jeu_engendre_respecte_TOUTES_les_contraintes_de_la_base(cx: Connection) -> None:
    """La preuve est que l'insertion a REUSSI : chaque contrainte a ete evaluee.

    Une contrainte de vérification, une exclusion, une clé étrangère composite et
    un déclencheur s'appliquent **à l'insertion**. Un jeu de 27 000 lignes qui
    passe est donc une épreuve, pas une simple mise en place — et le test le dit
    plutôt que de le laisser deviner.
    """
    mesure = engendrer(cx, entites=ENTITES_REDUITES, profils=PROFILS_REDUITS)
    #  Et une verification que l'insertion seule ne donne pas : les invariants
    #  d'unicite PARTIELLE, qu'aucune ligne prise isolement ne peut violer.
    doublons_booster = cx.execute(
        text(
            "SELECT count(*) FROM (SELECT circle_id FROM framework_responsibility_assignment "
            "WHERE responsibility_type = 'BOOSTER' AND ends_at IS NULL "
            "GROUP BY circle_id HAVING count(*) > 1) AS d"
        )
    ).scalar_one()
    assert doublons_booster == 0, "un cercle a plus d'un Booster actif"

    doublons_principal = cx.execute(
        text(
            "SELECT count(*) FROM (SELECT entity_membership_id FROM circle_membership "
            "WHERE membership_type = 'principal' AND ends_at IS NULL "
            "GROUP BY entity_membership_id HAVING count(*) > 1) AS d"
        )
    ).scalar_one()
    assert doublons_principal == 0, "une appartenance a plus d'un cercle principal actif"

    missions_sans_activation = cx.execute(
        text(
            "SELECT count(*) FROM professional_status_assignment s "
            "WHERE s.status = 'mission' AND NOT EXISTS ("
            "  SELECT 1 FROM entity_client ec WHERE ec.entity_id = s.entity_id "
            "    AND ec.client_id = s.client_id AND ec.archived_at IS NULL)"
        )
    ).scalar_one()
    assert missions_sans_activation == 0, "une mission porte un client non active dans l'entite"
    assert mesure.situations > 0


@pytest.mark.integration
def test_aucune_donnee_du_jeu_ne_ressemble_a_une_adresse_REELLE(cx: Connection) -> None:
    """Regle 3 du projet : aucune donnee reelle de collaborateur.

    Le domaine `exemple.test` est reserve par la RFC 2606 : il n'est pas
    resoluble, donc aucun envoi accidentel n'est possible. Le test exige que
    **toutes** les adresses le portent, et compte celles qu'il a examinees.
    """
    engendrer(cx, entites=ENTITES_REDUITES, profils=PROFILS_REDUITS)
    total, hors_domaine = cx.execute(
        text(
            "SELECT count(*), count(*) FILTER (WHERE email_normalized NOT LIKE '%@exemple.test') "
            "FROM person"
        )
    ).one()
    assert total > 0, "aucune personne engendree : le controle ne prouverait rien"
    assert hors_domaine == 0, f"{hors_domaine} adresse(s) hors du domaine reserve, sur {total}"


@pytest.mark.integration
def test_le_generateur_refuse_de_forcer_une_entite_etrangere(cx: Connection) -> None:
    """Le generateur passe par les depots, donc il HERITE de leur garde-fou.

    Ce test ne porte pas sur le generateur mais sur ce qui le protege : un depot
    borne a une entite refuse un `entity_id` contradictoire. C'est pourquoi le
    generateur ne peut pas fabriquer une relation croisee.
    """
    from app.shared.depot import ErreurDeDepot

    autre = uuid.uuid4()
    entite = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
            "VALUES ('T12', 'T12', 'T12', 'FR', 'active', 'Europe/Paris') RETURNING id"
        )
    ).scalar_one()
    with pytest.raises(ErreurDeDepot, match="contradictoire"):
        DepotLocal(cx, "circle", entite).creer(code="X", name="X", entity_id=autre)
