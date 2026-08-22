#!/usr/bin/env python3
"""Le verrouillage administrateur se declenche-t-il, et se relache-t-il ?

LOT 3, sous-etape `T5`, story `MVP-L03-US003`.

CE QUE CE CONTROLE PROUVE, ET POURQUOI IL EXISTE EN PLUS DES TESTS

  Les tests d'integration eprouvent le service au niveau ASGI, ou l'instant est
  **injecte** : c'est ce qui rend le relachement du verrou testable sans dormir
  quinze minutes. Mais ils n'eprouvent pas ce qu'un navigateur obtient.

  Ce controle interroge l'API REELLE, a travers Caddy en HTTPS, sur la stack qui
  tourne. Il verifie ce que les tests ne peuvent pas voir :

    - les cinq causes de refus rendent la MEME reponse — corps, code et en-tetes ;
    - le verrou se DECLENCHE reellement au cinquieme echec ;
    - `make admin-local` le LEVE, ce qui est la parade documentee du §7 de la
      fiche : « le verrouillage administrateur bloque Jonathan lui-meme » ;
    - aucun mot de passe ne figure dans les journaux du conteneur.

CE QU'IL NE PROUVE PAS, ET IL FAUT LE DIRE

  **Le relachement APRES QUINZE MINUTES n'est pas eprouve ici.** L'API lit
  l'horloge reelle : l'attendre couterait quinze minutes a chaque execution, ce
  qui est exactement ce que le §6 de la fiche interdit. La propriete est eprouvee
  par `test_le_verrouillage_se_RELACHE_apres_quinze_minutes`, ou l'instant est
  injecte, et **ce controle prouve l'autre moitie** : que le deverrouillage
  manuel fonctionne sur la stack reelle.

IL NETTOIE CE QU'IL CREE

  Le compte, la personne, les identifiants et les evenements. Un controle qui
  laisse un compte administrateur derriere lui laisse une porte ouverte -- et la
  lecon `T3-3` puis `T4-3` a coute deux fois : les residus font echouer
  l'execution suivante.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))
sys.path.insert(0, str(RACINE / "infra" / "scripts"))

from debit_partage import purger_les_compteurs_de_debit  # noqa: E402

CHEMIN_CONNEXION = "/api/v1/auth/connexion"
CHEMIN_MOT_DE_PASSE = "/api/v1/auth/mot-de-passe"

MARQUEUR = f"t5-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30

#  Les en-tetes dont la variation est legitime — meme liste fermee que pour le
#  magic link, et pour la meme raison : `X-Request-ID` DOIT varier (§28.1).
EN_TETES_VARIABLES = frozenset({"x-request-id", "date"})


def lire_env(chemin: str) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    for ligne in pathlib.Path(chemin).read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


def psql(compose: list[str], env: dict[str, str], requete: str) -> tuple[int, str]:
    """Requete avec le role de MIGRATION. Pas de shell — §7.2.

    **SUR LES `# noqa: S608` DES APPELANTS.** La seule valeur interpolee dans ces
    requetes est `adresse`, qui est construite ICI a partir de `MARQUEUR` —
    `uuid4` — et du domaine lu dans le fichier d'environnement. Aucune entree de
    tiers n'atteint ce SQL, et `psql` n'accepte pas de parametres lies : c'est le
    motif de cette forme, la meme que dans les trois autres scripts du depot.
    """
    execution = subprocess.run(  # noqa: S603
        [
            *compose,
            "exec",
            "-T",
            "--env",
            f"PGPASSWORD={env['POSTGRES_MIGRATIONS_PASSWORD']}",
            "db",
            "psql",
            "-U",
            env["POSTGRES_MIGRATIONS_USER"],
            "-d",
            env["POSTGRES_DB"],
            "-v",
            "ON_ERROR_STOP=1",
            "-tAF|",
            "-c",
            requete,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return execution.returncode, (execution.stdout + execution.stderr).strip()


class Reponse:
    """Une reponse reduite a ce que le critere compare."""

    def __init__(self, statut: int, corps: bytes, en_tetes: dict[str, str]) -> None:
        self.statut = statut
        self.corps = corps
        self.en_tetes = {nom.lower(): valeur for nom, valeur in en_tetes.items()}


def appeler(base: str, chemin: str, charge: dict[str, str], contexte: ssl.SSLContext) -> Reponse:
    """POST, et rendre la reponse MEME sur un code d'erreur.

    `urllib` leve sur un 4xx : laisser remonter l'exception rendrait les refus
    incomparables, or ce sont eux qu'on compare.
    """
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), dict(reponse.headers))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), dict(erreur.headers))


def _sans_correlation(corps: bytes) -> tuple[object, str | None]:
    """Le corps, prive de l'identifiant de correlation du §18.3."""
    try:
        charge = json.loads(corps)
    except json.JSONDecodeError:
        return corps, None
    if isinstance(charge, dict) and isinstance(charge.get("erreur"), dict):
        return charge, charge["erreur"].pop("identifiant_correlation", None)
    return charge, None


def ecarts(gauche: Reponse, droite: Reponse) -> list[str]:
    """Ce qui distingue deux refus, hors ce qui DOIT varier."""
    trouves: list[str] = []
    if gauche.statut != droite.statut:
        trouves.append(f"code HTTP {gauche.statut} contre {droite.statut}")
    corps_g, correlation_g = _sans_correlation(gauche.corps)
    corps_d, correlation_d = _sans_correlation(droite.corps)
    if corps_g != corps_d:
        trouves.append(f"corps hors correlation : {corps_g!r} contre {corps_d!r}")
    if correlation_g is None or correlation_d is None:
        trouves.append("un corps ne porte pas d'identifiant de correlation (§18.3)")
    elif correlation_g == correlation_d:
        trouves.append("les deux refus portent le MEME identifiant de correlation")
    for nom in sorted((set(gauche.en_tetes) | set(droite.en_tetes)) - EN_TETES_VARIABLES):
        if gauche.en_tetes.get(nom) != droite.en_tetes.get(nom):
            trouves.append(f"en-tete {nom} differe")
    return trouves


def _provisionner(env_file: str, compose_nus: list[str], adresse: str) -> str | None:
    """Lancer `provisionner-administrateur.py` et EXTRAIRE le mot de passe affiche.

    Le mot de passe n'existe qu'a cet instant : il n'est ni en base, ni dans un
    fichier. L'extraire de la sortie est le seul moyen de l'employer -- et c'est
    precisement ce que fait un operateur.
    """
    execution = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(RACINE / "infra" / "scripts" / "provisionner-administrateur.py"),
            "--env-file",
            env_file,
            "--adresse",
            adresse,
            *compose_nus,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if execution.returncode:
        print(f"    ECHEC    provisionnement : {execution.stdout[-300:]}")
        return None
    trouve = re.search(r"mot de passe : (\S+)", execution.stdout)
    return trouve.group(1) if trouve else None


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--env-file", required=True)
    analyseur.add_argument("--base", required=True)
    analyseur.add_argument("fichiers_compose", nargs="+")
    arguments = analyseur.parse_args()

    compose = ["docker", "compose", "--env-file", os.path.abspath(arguments.env_file)]
    for fichier in arguments.fichiers_compose:
        if " " in fichier:
            print(f"  ECHEC     chemin Compose contenant une espace : {fichier!r}")
            return 1
        compose += ["-f", fichier]
    env = lire_env(arguments.env_file)

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    adresse = f"{MARQUEUR}@{domaine}"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Connexion administrateur locale — US003, cahier §7.3, modele §10.1")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")

    echecs = 0
    controles = 0

    #  L'INSTANT DE DEPART, pour pouvoir retirer les evenements SANS personne.
    code, debut = psql(compose, env, "SELECT now()")
    if code or not debut.strip():
        print(f"    ECHEC    lecture de l'horloge de la base : {debut[:180]}")
        return 1
    debut = debut.splitlines()[0].strip()

    code, sortie = psql(
        compose,
        env,
        "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "  # noqa: S608
        f"VALUES ('{adresse}', '{adresse}', 'Verif', 'T5', 'active')",
    )
    if code:
        print(f"    ECHEC    creation de la personne : {sortie[:200]}")
        return 1
    print("    ok       personne de verification creee")

    try:
        mot_de_passe = _provisionner(
            os.path.abspath(arguments.env_file), arguments.fichiers_compose, adresse
        )
        if not mot_de_passe:
            print("    ECHEC    aucun mot de passe extrait de la sortie du provisionnement")
            return 1
        print(f"    ok       compte provisionne, mot de passe de {len(mot_de_passe)} caracteres")

        #  --------------------------------------------------------------
        #  1. LE BON MOT DE PASSE PASSE, ET `must_change` EST REMONTE
        #  --------------------------------------------------------------
        controles += 1
        reussie = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            {"email": adresse, "mot_de_passe": mot_de_passe},
            contexte,
        )
        if reussie.statut != 200:
            print(f"    ECHEC    le bon mot de passe est refuse : {reussie.statut}")
            echecs += 1
        elif json.loads(reussie.corps).get("changement_exige") is not True:
            print("    ECHEC    `changement_exige` n'est pas vrai sur un compte amorce")
            echecs += 1
        else:
            print("    ok       bon mot de passe accepte, `changement_exige` = true (§10.2)")

        #  --------------------------------------------------------------
        #  2. LES REFUS SONT INDISTINGUABLES
        #  --------------------------------------------------------------
        controles += 1
        refus = {
            "adresse_inconnue": appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                {"email": f"jamais-vu-{uuid.uuid4().hex[:8]}@{domaine}", "mot_de_passe": "x" * 20},
                contexte,
            ),
            "mot_de_passe_faux": appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                {"email": adresse, "mot_de_passe": "un-mot-de-passe-qui-n-est-pas-le-bon"},
                contexte,
            ),
            "adresse_fantaisiste": appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                {"email": "pas-une-adresse", "mot_de_passe": "x" * 20},
                contexte,
            ),
        }
        #  LA REFERENCE EST EXCLUE DE LA COMPARAISON, ET C'EST UN CORRECTIF.
        #
        #  Ma premiere version comparait chaque refus a `adresse_inconnue`, **y
        #  compris celui-la** : le comparateur exige que les identifiants de
        #  correlation DIFFERENT — a juste titre — et une reponse comparee a
        #  elle-meme porte forcement le meme. Le controle signalait donc une
        #  divergence sur un livrable conforme. Defaut `T5-4`, et c'est le §7.20 :
        #  un controle qui echoue sur du code correct doit etre rendu exact, non
        #  affaibli.
        reference = refus["adresse_inconnue"]
        divergents = [
            f"{nom} : {ecarts(reference, reponse)}"
            for nom, reponse in refus.items()
            if nom != "adresse_inconnue" and ecarts(reference, reponse)
        ]
        if divergents:
            print("    ECHEC    les refus sont DISTINGUABLES")
            for divergent in divergents:
                print(f"             {divergent}")
            echecs += 1
        else:
            #  LE COMPTE EST CONFRONTE A UN ATTENDU : sans cela, une boucle
            #  vide passerait pour un succes. §7.0, troisieme proposition.
            compares = len(refus) - 1
            print(
                f"    ok       {len(refus)} causes de refus indistinguables "
                f"({compares} comparaisons) — code {reference.statut}, hors correlation"
            )
            if compares < 2:
                print("    ECHEC    moins de deux comparaisons : ce controle ne prouve rien")
                echecs += 1

        #  --------------------------------------------------------------
        #  3. LE TEMOIN : le comparateur sait-il ECHOUER ?
        #  --------------------------------------------------------------
        controles += 1
        if not ecarts(refus["mot_de_passe_faux"], reussie):
            print("    ECHEC    TEMOIN : le comparateur ne distingue pas un refus d'un succes")
            echecs += 1
        else:
            print("    ok       TEMOIN — le comparateur distingue un refus d'un succes")

        #  --------------------------------------------------------------
        #  4. LE VERROU SE DECLENCHE
        #  --------------------------------------------------------------
        from app.auth.services import ECHECS_AVANT_VERROUILLAGE

        controles += 1
        for _ in range(ECHECS_AVANT_VERROUILLAGE):
            appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                {"email": adresse, "mot_de_passe": "un-mot-de-passe-qui-n-est-pas-le-bon"},
                contexte,
            )
        # ==============================================================
        #
        #  LE COMPTEUR DE `T8` EST EFFACE AVANT CHAQUE ASSERTION SUR
        #  `/auth/connexion`, ET C'EST UN CORRECTIF DE `T8`
        #
        #    Ce verificateur pousse deliberement un compte jusqu'au
        #    verrouillage : cinq echecs, puis une tentative avec le BON mot de
        #    passe. Depuis `T8`, cette sixieme requete est refusee par la
        #    limitation par adresse -- **429 au lieu de 400** -- et trois
        #    controles ont echoue sur un livrable conforme. C'est le §7.21.
        #
        #    **ET LE PREMIER DES TROIS PASSAIT POUR LA MAUVAISE RAISON.** Il
        #    n'exigeait que « pas 200 » ; un 429 le satisfaisait, et il annoncait
        #    « verrou declenche » alors que c'etait la limitation qui avait parle.
        #    Il exige desormais le code du refus de `T5`.
        #
        #    Effacer est le bon geste et non un contournement : ce controle porte
        #    sur le VERROU de `T5`, qui a ses propres seuils en base, et la
        #    limitation de `T8` a son propre controle -- `make debit-check`. Le
        #    verrou obtenu reste reel, produit par cinq vrais echecs.
        #
        # ==============================================================
        purger_les_compteurs_de_debit(env)
        verrouille = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            {"email": adresse, "mot_de_passe": mot_de_passe},
            contexte,
        )
        if verrouille.statut != 400:
            print(
                f"    ECHEC    apres {ECHECS_AVANT_VERROUILLAGE} echecs, le BON mot de passe "
                f"rend {verrouille.statut} au lieu de 400. Un 200 dirait que le verrou ne s'est "
                "pas declenche ; un 429 dirait que c'est la limitation de `T8` qui a parle, "
                "et non le verrou que ce controle doit prouver"
            )
            echecs += 1
        else:
            print(
                f"    ok       verrou declenche apres {ECHECS_AVANT_VERROUILLAGE} echecs — "
                "le bon mot de passe rend 400, le refus de `T5`"
            )

        #  Et le verrou ne se LIT PAS dans la reponse : meme forme qu'un autre refus.
        controles += 1
        if ecarts(verrouille, refus["adresse_inconnue"]):
            print("    ECHEC    le refus « verrouille » se DISTINGUE d'un refus ordinaire")
            print("             un attaquant apprendrait qu'il a REUSSI a verrouiller")
            echecs += 1
        else:
            print("    ok       le verrou ne se lit pas dans la reponse")

        #  --------------------------------------------------------------
        #  5. L'AUDIT PORTE LE VERROUILLAGE
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT e.event_type, count(*) FROM auth_event e "  # noqa: S608
            "JOIN person p ON p.id = e.person_id "
            f"WHERE p.email_normalized = '{adresse}' GROUP BY 1 ORDER BY 1",
        )
        types = {
            ligne.split("|")[0]: int(ligne.split("|")[1])
            for ligne in sortie.splitlines()
            if "|" in ligne
        }
        attendus = {"LOGIN_SUCCESS", "LOGIN_FAILURE", "ACCOUNT_LOCKED"}
        if code or not attendus <= set(types):
            print(f"    ECHEC    audit incomplet : {types}, attendus {sorted(attendus)}")
            echecs += 1
        else:
            print(f"    ok       audit — {types}")

        #  --------------------------------------------------------------
        #  6. `make admin-local` LEVE LE VERROU — la parade du §7 de la fiche
        #  --------------------------------------------------------------
        controles += 1
        _provisionner(os.path.abspath(arguments.env_file), arguments.fichiers_compose, adresse)
        purger_les_compteurs_de_debit(env)  # voir le bloc du controle 4
        deverrouille = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            {"email": adresse, "mot_de_passe": mot_de_passe},
            contexte,
        )
        if deverrouille.statut != 200:
            print(
                "    ECHEC    apres `make admin-local`, le compte reste verrouille : "
                f"{deverrouille.statut}"
            )
            echecs += 1
        else:
            print("    ok       `make admin-local` LEVE le verrou, et ne touche pas")
            print("             au mot de passe — la parade du §7 de la fiche fonctionne")

        #  --------------------------------------------------------------
        #  7. LE CHANGEMENT DE MOT DE PASSE
        #  --------------------------------------------------------------
        controles += 1
        purger_les_compteurs_de_debit(env)  # voir le bloc du controle 4
        nouveau = secrets.token_urlsafe(24)
        change = appeler(
            arguments.base,
            CHEMIN_MOT_DE_PASSE,
            {
                "email": adresse,
                "mot_de_passe_actuel": mot_de_passe,
                "nouveau_mot_de_passe": nouveau,
            },
            contexte,
        )
        apres = appeler(
            arguments.base, CHEMIN_CONNEXION, {"email": adresse, "mot_de_passe": nouveau}, contexte
        )
        ancien = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            {"email": adresse, "mot_de_passe": mot_de_passe},
            contexte,
        )
        if change.statut != 200 or apres.statut != 200 or ancien.statut == 200:
            print(
                f"    ECHEC    changement {change.statut}, nouveau {apres.statut}, "
                f"ancien {ancien.statut} — attendu 200/200/refus"
            )
            echecs += 1
        else:
            print("    ok       mot de passe change — le nouveau passe, l'ancien non")
            #  Et `must_change` est retombe : le changement a eu lieu.
            if json.loads(apres.corps).get("changement_exige") is not False:
                print("    ECHEC    `changement_exige` reste vrai apres le changement")
                echecs += 1
            else:
                print("    ok       `changement_exige` est retombe a false")

        #  --------------------------------------------------------------
        #  8. AUCUN MOT DE PASSE DANS LES JOURNAUX NI EN BASE
        #  --------------------------------------------------------------
        controles += 1
        journaux = subprocess.run(  # noqa: S603
            [*compose, "logs", "--no-log-prefix", "--tail", "600", "api"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte = journaux.stdout + journaux.stderr
        fuites = [
            nom
            for nom, valeur in (("provisoire", mot_de_passe), ("nouveau", nouveau))
            if valeur in texte
        ]
        if fuites:
            print(f"    ECHEC    mot(s) de passe dans les journaux de api : {fuites}")
            echecs += 1
        else:
            print(
                f"    ok       aucun mot de passe dans les {len(texte.splitlines())} "
                "dernieres lignes de journal de api"
            )

        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*) FROM admin_password_credential c "  # noqa: S608
            "JOIN user_account u ON u.id = c.user_account_id "
            "JOIN person p ON p.id = u.person_id "
            f"WHERE p.email_normalized = '{adresse}' "
            f"  AND (c.password_hash LIKE '%{mot_de_passe}%' "
            f"       OR c.password_hash LIKE '%{nouveau}%')",
        )
        if code or sortie.strip() != "0":
            print(f"    ECHEC    un mot de passe figure EN CLAIR en base : {sortie!r}")
            echecs += 1
        else:
            print("    ok       aucun mot de passe en clair en base — empreintes seules")

    finally:
        _nettoyer(compose, env, adresse, debut)

    print()
    print(f"  controles executes : {controles}   echecs : {echecs}")
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes")
        return 1
    print("  --> le verrouillage se declenche, `make admin-local` le leve, et les")
    print("      refus sont indistinguables")
    return 0


def _nettoyer(compose: list[str], env: dict[str, str], adresse: str, debut: str) -> None:
    """Retirer TOUT ce que ce controle a cree, dans l'ordre des cles etrangeres.

    **LA DERNIERE ETAPE EST CELLE QU'ON OUBLIE, ET C'EST LA TROISIEME FOIS.** Les
    refus sur une adresse INCONNUE ecrivent un `auth_event` dont `person_id` est
    nul -- c'est voulu, `T2` l'a pose pour cela -- et **aucun filtre par identite
    ne peut les atteindre**. Ma premiere version en laissait quatre par execution.

    Meme defaut qu'en `T3-3` et `T4-5`. La parade est une borne sur `created_at`,
    non sur `occurred_at` : ce dernier porte l'instant que l'API a lu, mais dans
    les tests il porte un instant INJECTE, et la borne serait alors fausse.
    """
    etapes = (
        "DELETE FROM auth_event WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        #  `user_session` A ETE AJOUTEE PAR `T6` : la route de connexion cree
        #  desormais une session, et la cle etrangere bloque la suppression de la
        #  personne. Ce nettoyage etait complet quand `T5` l'a ecrit. §7.21, et
        #  c'est le quatrieme nettoyage touche par cet ajout.
        "DELETE FROM user_session WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        "DELETE FROM admin_password_credential WHERE user_account_id IN "  # noqa: S608
        "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
        f" WHERE p.email_normalized = '{adresse}')",
        "DELETE FROM user_account WHERE person_id IN "  # noqa: S608
        f"(SELECT id FROM person WHERE email_normalized = '{adresse}')",
        f"DELETE FROM person WHERE email_normalized = '{adresse}'",  # noqa: S608
        #  Les evenements SANS personne, bornes a cette execution.
        f"DELETE FROM auth_event WHERE person_id IS NULL   AND created_at >= '{debut}'",  # noqa: S608
    )
    restes = 0
    for requete in etapes:
        code, sortie = psql(compose, env, requete)
        if code:
            restes += 1
            print(f"    SIGNALE  nettoyage incomplet : {sortie[:160]}")
    if not restes:
        print(f"    ok       nettoyage — tout ce qui portait `{MARQUEUR}` est retire")


if __name__ == "__main__":
    sys.exit(main())
