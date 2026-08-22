#!/usr/bin/env python3
"""Les limites de debit produisent-elles les resultats attendus ?

LOT 3, sous-etape `T8`, stories `MVP-L03-US001` et `MVP-L03-US003`.

LE CRITERE EST LITTERAL, ET IL A DEUX MOITIES

  §3 de la fiche : « les limites **produisent les resultats attendus** — critere
  de sortie litteral · la valeur minimisee `request_origin_hash` du §10.3 est
  employee, jamais une adresse IP brute ».

  Ce controle prouve les deux, et il le fait sur l'API REELLE a travers Caddy en
  HTTPS : les tests d'integration montent l'application en processus et
  surchargent `PUBLIC_BASE_URL`, donc ils ne disent rien de la configuration
  deployee.

IL PORTE TROIS TEMOINS, ET SANS EUX IL NE PROUVERAIT RIEN

  1. **les dix premieres demandes passent.** Sans ce temoin, une route cassee --
     qui refuserait tout -- donnerait la meme observation qu'une limite qui
     fonctionne ;
  2. **la surveillance d'origine ne refuse JAMAIS.** Le §20.2 ecrit
     « limitation » pour l'adresse et « alerte » pour l'origine : confondre les
     deux verbes bloquerait tout un bureau derriere un partage d'adresse ;
  3. **un succes efface le compteur d'echecs.** Sans quoi un administrateur qui
     se trompe puis reussit resterait refuse quinze minutes -- le risque nomme
     au §7 de la fiche du lot.

ET IL COMPARE LES DEUX REFUS, PARCE QUE LA LIMITE POURRAIT DEVENIR UN ORACLE

  Si le 429 n'arrivait que pour une adresse connue, il dirait « ce compte
  existe » -- l'oracle que `T3` a ferme. Les deux refus sont donc compares
  **corps ET en-tetes**, et les deux doivent d'abord ETRE des 429 : comparer sans
  cela ferait passer le controle sur deux 202 identiques. Ce n'est pas une
  precaution theorique, c'est un defaut que le temoin negatif a trouve dans la
  premiere version des tests de cette sous-etape.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "apps" / "api"))
sys.path.insert(0, str(RACINE / "infra" / "scripts"))

from debit_partage import purger_les_compteurs_de_debit  # noqa: E402

CHEMIN_DEMANDE = "/api/v1/auth/magic-link"
CHEMIN_CONNEXION = "/api/v1/auth/connexion"

MARQUEUR = f"t8-verif-{uuid.uuid4().hex[:12]}"
DELAI_HTTP = 30

#  Les memes que `T3` : ceux qui varient d'une reponse a l'autre sans rien dire
#  du contenu de la base.
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

    **SUR LES `# noqa: S608`.** La seule valeur interpolee est `adresse`,
    construite ici depuis `MARQUEUR` (`uuid4`) et un domaine du fichier
    d'environnement. Aucune entree de tiers, et `psql` n'accepte pas de
    parametres lies.
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
    def __init__(self, statut: int, corps: bytes, en_tetes: list[tuple[str, str]]) -> None:
        self.statut = statut
        self.corps = corps
        self.en_tetes = {nom.lower(): valeur for nom, valeur in en_tetes}

    def signature(self) -> tuple[int, object, dict[str, str]]:
        """Ce qui doit etre IDENTIQUE entre deux refus.

        L'identifiant de correlation est neutralise : il varie par construction,
        et c'est le §18.3 qui l'exige.
        """
        try:
            corps: object = json.loads(self.corps or b"{}")
        except json.JSONDecodeError:
            corps = self.corps.decode("utf-8", "replace")
        if isinstance(corps, dict) and isinstance(corps.get("erreur"), dict):
            corps = {**corps, "erreur": {**corps["erreur"], "identifiant_correlation": "IGNORE"}}
        return self.statut, corps, self.en_tetes


def appeler(
    base: str,
    chemin: str,
    contexte: ssl.SSLContext,
    *,
    charge: dict[str, str] | None = None,
    en_tetes: dict[str, str] | None = None,
) -> Reponse:
    """Appeler l'API. Rend la reponse MEME sur un code d'erreur."""
    entetes = {"Content-Type": "application/json"} if charge is not None else {}
    entetes.update(en_tetes or {})
    requete = urllib.request.Request(  # noqa: S310 — https impose par `base`
        f"{base}{chemin}",
        data=json.dumps(charge).encode("utf-8") if charge is not None else None,
        headers=entetes,
        method="POST" if charge is not None else "GET",
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            requete, timeout=DELAI_HTTP, context=contexte
        ) as reponse:
            return Reponse(reponse.status, reponse.read(), list(reponse.headers.items()))
    except urllib.error.HTTPError as erreur:
        return Reponse(erreur.code, erreur.read(), list(erreur.headers.items()))


def _client_redis(env: dict[str, str]):  # noqa: ANN202 — le type vient de `redis`
    import redis

    return redis.Redis(
        host="127.0.0.1",
        port=int(env.get("REDIS_HOST_PORT", "6379")),
        password=env.get("REDIS_PASSWORD") or None,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def _cles_de_debit(env: dict[str, str], prefixe: str) -> list[str]:
    client = _client_redis(env)
    return [
        c.decode("utf-8") if isinstance(c, bytes) else str(c)
        for c in client.scan_iter(match=f"{prefixe}*", count=500)
    ]


def _purger(env: dict[str, str], prefixe: str) -> int:
    """Deleguer au helper PARTAGE — une seule implementation.

    `verifier-csrf.py` et `verifier-connexion-admin.py` en ont besoin aussi
    depuis `T8`, et trois copies d'une purge finiraient par diverger sur le
    prefixe. Voir l'en-tete de `debit_partage.py`.
    """
    del prefixe  # le helper le tient de `app.auth.debit`, source unique
    return purger_les_compteurs_de_debit(env)


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

    #  **LES SEUILS ET LE PREFIXE SONT IMPORTES, JAMAIS RECOPIES.** Une liste
    #  recopiee vieillit au premier changement — §7.27, trois occurrences dans ce
    #  lot.
    from app.auth.debit import (
        DEMANDES_DE_LIEN_PAR_ADRESSE,
        DEMANDES_PAR_ORIGINE,
        ECHECS_ADMIN_PAR_ADRESSE,
        PREFIXE_REDIS,
    )
    from app.auth.mots_de_passe import ALGORITHME, hacher

    domaines = [
        d.strip().lower().lstrip("@")
        for d in env.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
        if d.strip()
    ]
    domaine = domaines[0] if domaines else "exalt-company.com"
    connue = f"{MARQUEUR}.connue@{domaine}"
    inconnue = f"{MARQUEUR}.inconnue@{domaine}"
    mot_de_passe = "un-mot-de-passe-de-verification-sans-portee"

    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE

    print()
    print("  Limitation de debit — US001 et US003, cahier §20.1, §20.2")
    print(f"    info     origine {arguments.base}")
    print(f"    info     marqueur : {MARQUEUR}")
    print(
        f"    info     seuils du §20.2 : {DEMANDES_DE_LIEN_PAR_ADRESSE} liens/adresse/h, "
        f"{DEMANDES_PAR_ORIGINE} demandes/origine/h, {ECHECS_ADMIN_PAR_ADRESSE} echecs admin"
    )

    echecs = 0
    controles = 0

    empreinte_mdp, parametres_hachage = hacher(mot_de_passe)
    code, debut = psql(compose, env, "SELECT now()")
    if code or not debut.strip():
        print(f"    ECHEC    horloge de la base : {debut[:180]}")
        return 1
    debut = debut.splitlines()[0].strip()

    decor = f"""
    DO $$
    DECLARE e uuid; p uuid; c uuid;
    BEGIN
      INSERT INTO entity (code, display_name, city, country_code, status, timezone)
      VALUES ('{MARQUEUR}', 'Entite T8', 'Bordeaux', 'FR', 'active', 'Europe/Paris')
      RETURNING id INTO e;
      INSERT INTO person (email, email_normalized, first_name, last_name, account_state)
      VALUES ('{connue}', '{connue}', 'Verif', 'T8', 'active') RETURNING id INTO p;
      INSERT INTO entity_membership (person_id, entity_id, arrival_date,
        membership_state, professional_category, profile_visibility)
      VALUES (p, e, current_date - 30, 'active', 'consultant', 'draft');
      INSERT INTO user_account (person_id, account_type, state, failed_login_count)
      VALUES (p, 'ADMIN_LOCAL', 'active', 0) RETURNING id INTO c;
      INSERT INTO admin_password_credential
        (user_account_id, password_hash, algorithm, parameters, changed_at, must_change)
      VALUES (c, '{empreinte_mdp}', '{ALGORITHME}',
              '{json.dumps(parametres_hachage)}'::jsonb, now(), FALSE);
    END $$;
    """  # noqa: S608 — voir la justification en tete de `psql`
    code, sortie = psql(compose, env, decor)
    if code:
        print(f"    ECHEC    decor impossible : {sortie[:250]}")
        return 1
    print("    ok       decor cree : 1 entite, 1 profil ACTIF, 1 compte ADMIN_LOCAL")

    #  **PURGE AVANT, ET PAS SEULEMENT APRES.** Une execution interrompue
    #  laisserait des compteurs, et la suivante echouerait sur un livrable
    #  conforme — defaut `T4-3`.
    try:
        efface = _purger(env, PREFIXE_REDIS)
    except Exception as erreur:  # la cause doit etre LUE, jamais masquee — §7.6
        print(f"    ECHEC    Redis injoignable sur 127.0.0.1 : {type(erreur).__name__}")
        return 1
    print(f"    ok       compteurs purges avant l'epreuve : {efface}")

    try:
        #  --------------------------------------------------------------
        #  1. LES DIX PREMIERES PASSENT — LE TEMOIN, ET IL VIENT D'ABORD
        #  --------------------------------------------------------------
        controles += 1
        passees = [
            appeler(arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": connue}).statut
            for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE)
        ]
        if set(passees) != {202}:
            print(f"    ECHEC    les {DEMANDES_DE_LIEN_PAR_ADRESSE} premieres : {passees}")
            echecs += 1
        else:
            print(
                f"    ok       TEMOIN — les {DEMANDES_DE_LIEN_PAR_ADRESSE} premieres demandes "
                "passent (202)"
            )

        #  --------------------------------------------------------------
        #  2. LA ONZIEME EST REFUSEE — ADRESSE CONNUE
        #  --------------------------------------------------------------
        controles += 1
        refus_connue = appeler(arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": connue})
        if refus_connue.statut != 429:
            print(
                f"    ECHEC    demande {DEMANDES_DE_LIEN_PAR_ADRESSE + 1} : "
                f"{refus_connue.statut} au lieu de 429"
            )
            echecs += 1
        else:
            corps = json.loads(refus_connue.corps)
            attente = corps["erreur"]["details"]["secondes_avant_reprise"]
            print(f"    ok       adresse CONNUE : 429, reprise dans {attente} s")

        #  --------------------------------------------------------------
        #  3. ET AUSSI POUR UNE ADRESSE INCONNUE — LE PIEGE DE `T8`
        #  --------------------------------------------------------------
        controles += 1
        for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
            appeler(arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": inconnue})
        refus_inconnue = appeler(
            arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": inconnue}
        )
        if refus_inconnue.statut != 429:
            print(
                f"    ECHEC    adresse INCONNUE : {refus_inconnue.statut} au lieu de 429. "
                "Une limite qui ne vaut que pour les adresses connues DIT qu'elles existent"
            )
            echecs += 1
        else:
            print("    ok       adresse INCONNUE : 429 — l'oracle de `T3` reste ferme")

        #  --------------------------------------------------------------
        #  4. LES DEUX REFUS SONT IDENTIQUES — CORPS ET EN-TETES
        #  --------------------------------------------------------------
        controles += 1
        gauche, droite = refus_connue.signature(), refus_inconnue.signature()
        ecarts: list[str] = []
        if gauche[0] != 429 or droite[0] != 429:
            #  Comparer deux 202 identiques ferait passer ce controle sans qu'il
            #  prouve rien. §7.0, proposition 4.
            ecarts.append(f"les deux refus ne sont pas des 429 : {gauche[0]} et {droite[0]}")
        if gauche[1] != droite[1]:
            ecarts.append(f"corps {gauche[1]!r} != {droite[1]!r}")
        for nom in sorted((set(gauche[2]) | set(droite[2])) - EN_TETES_VARIABLES):
            if gauche[2].get(nom) != droite[2].get(nom):
                ecarts.append(f"en-tete {nom} : {gauche[2].get(nom)!r} != {droite[2].get(nom)!r}")
        if ecarts:
            print("    ECHEC    la limitation revele l'existence du compte :")
            for ecart in ecarts:
                print(f"             {ecart}")
            echecs += 1
        else:
            print("    ok       les deux refus sont IDENTIQUES : corps et en-tetes")

        #  --------------------------------------------------------------
        #  5. VARIER LA CASSE NE CONTOURNE PAS
        #  --------------------------------------------------------------
        controles += 1
        majuscules = appeler(
            arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": inconnue.upper()}
        )
        if majuscules.statut != 429:
            print(
                f"    ECHEC    la meme adresse en majuscules : {majuscules.statut}. "
                "L'adresse n'est pas normalisee avant d'etre comptee"
            )
            echecs += 1
        else:
            print("    ok       la casse ne contourne pas la limite (429)")

        #  --------------------------------------------------------------
        #  6. TEMOIN — LA SURVEILLANCE D'ORIGINE NE REFUSE JAMAIS
        #  --------------------------------------------------------------
        controles += 1
        codes = {
            appeler(
                arguments.base,
                CHEMIN_DEMANDE,
                contexte,
                charge={"email": f"o{rang}.{inconnue}"},
            ).statut
            for rang in range(DEMANDES_PAR_ORIGINE + 1)
        }
        if codes != {202}:
            print(
                f"    ECHEC    la surveillance d'origine a REFUSE : {sorted(codes)}. "
                "Le §20.2 ecrit « alerte », non « limitation »"
            )
            echecs += 1
        else:
            print(
                f"    ok       TEMOIN — {DEMANDES_PAR_ORIGINE + 1} demandes depuis la meme "
                "origine, AUCUNE refusee"
            )

        #  --------------------------------------------------------------
        #  7. LA CONNEXION ADMIN EST REFUSEE AU SIXIEME ECHEC, DES DEUX COTES
        #  --------------------------------------------------------------
        controles += 1
        verdicts = {}
        for adresse in (connue, inconnue):
            avant = [
                appeler(
                    arguments.base,
                    CHEMIN_CONNEXION,
                    contexte,
                    charge={"email": adresse, "mot_de_passe": "mauvais-mot-de-passe-de-verif"},
                ).statut
                for _ in range(ECHECS_ADMIN_PAR_ADRESSE)
            ]
            apres = appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                contexte,
                charge={"email": adresse, "mot_de_passe": "mauvais-mot-de-passe-de-verif"},
            ).statut
            verdicts[adresse] = (set(avant), apres)
        mauvais = {a: v for a, v in verdicts.items() if v != ({400}, 429)}
        if mauvais:
            print(
                "    ECHEC    le compteur d'echecs administrateur ne produit pas 400x5 puis 429 :"
            )
            for adresse, verdict in mauvais.items():
                print(f"             {'connue' if adresse == connue else 'inconnue'} -> {verdict}")
            echecs += 1
        else:
            print(
                f"    ok       {ECHECS_ADMIN_PAR_ADRESSE} echecs puis 429, adresse connue ET "
                "inconnue — meme code, donc aucun oracle"
            )

        #  --------------------------------------------------------------
        #  8. TEMOIN — UN SUCCES EFFACE LE COMPTEUR
        #  --------------------------------------------------------------
        controles += 1
        _purger(env, PREFIXE_REDIS)
        #  **LE VERROU DE `T5` EST LEVE ICI, ET C'EST UN CORRECTIF.** Le controle
        #  precedent a produit six echecs, donc `T5` a VERROUILLE le compte pour
        #  quinze minutes -- son mecanisme, deja eprouve par `make admin-check`.
        #  Sans cette remise a zero, la connexion legitime de ce temoin rendait
        #  400, et le temoin n'exerçait pas ce qu'il croyait : il echouait pour
        #  une raison etrangere au compteur Redis qu'il doit prouver.
        psql(
            compose,
            env,
            "UPDATE user_account SET failed_login_count = 0, "  # noqa: S608
            "  locked_until = NULL "
            "WHERE person_id IN (SELECT id FROM person WHERE email_normalized "
            f"LIKE '{MARQUEUR}%')",
        )
        for _ in range(ECHECS_ADMIN_PAR_ADRESSE - 1):
            appeler(
                arguments.base,
                CHEMIN_CONNEXION,
                contexte,
                charge={"email": connue, "mot_de_passe": "mauvais-mot-de-passe-de-verif"},
            )
        reussie = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": connue, "mot_de_passe": mot_de_passe},
        )
        suivant = appeler(
            arguments.base,
            CHEMIN_CONNEXION,
            contexte,
            charge={"email": connue, "mot_de_passe": "mauvais-mot-de-passe-de-verif"},
        )
        if reussie.statut != 200:
            print(
                f"    ECHEC    la connexion legitime a rendu {reussie.statut} : le temoin "
                "n'exerce pas ce qu'il croit"
            )
            echecs += 1
        elif suivant.statut != 400:
            print(
                f"    ECHEC    apres un succes, l'echec suivant rend {suivant.statut} au lieu "
                "de 400 : le compteur n'a pas ete efface, et un administrateur qui se trompe "
                "puis reussit resterait bloque"
            )
            echecs += 1
        else:
            print("    ok       TEMOIN — un succes efface le compteur (200 puis 400, non 429)")

        #  --------------------------------------------------------------
        #  9. AUCUNE CLE REDIS NE PORTE UNE ADRESSE NI UNE IP
        #  --------------------------------------------------------------
        controles += 1
        cles = _cles_de_debit(env, PREFIXE_REDIS)
        fautives = [
            c
            for c in cles
            if "@" in c
            or re.search(r"\d{1,3}(\.\d{1,3}){3}", c)
            or not re.fullmatch(rf"{re.escape(PREFIXE_REDIS)}[a-z-]+:[0-9a-f]{{64}}", c)
        ]
        if not cles:
            print("    ECHEC    aucune cle de debit posee : le controle ne prouverait rien")
            echecs += 1
        elif fautives:
            print(f"    ECHEC    {len(fautives)} cle(s) portent une valeur en clair :")
            for cle in fautives[:5]:
                print(f"             {cle}")
            echecs += 1
        else:
            print(
                f"    ok       {len(cles)} cles examinees, toutes en empreinte HMAC — "
                "ni adresse ni IP en clair"
            )

        #  --------------------------------------------------------------
        #  10. LE DELAI EST POSE, ET IL N'EST PAS REPOUSSE
        #  --------------------------------------------------------------
        controles += 1
        client = _client_redis(env)
        delais = {c: int(client.ttl(c)) for c in cles}
        sans_delai = [c for c, d in delais.items() if d <= 0]
        if not delais:
            #  **UN CONTROLE DOIT RAPPORTER, JAMAIS PLANTER.** Ma premiere version
            #  faisait `next(iter(delais))` sans garde : quand le controle 9 avait
            #  deja constate qu'aucune cle n'existait, celui-ci levait
            #  `StopIteration` et les trois controles suivants n'etaient jamais
            #  executes. Une trace Python n'est pas un diagnostic.
            print("    ECHEC    aucune cle a examiner : le delai n'est pas verifiable")
            echecs += 1
        elif sans_delai:
            print(
                f"    ECHEC    {len(sans_delai)} cle(s) SANS delai : l'adresse serait bloquee "
                "definitivement"
            )
            for cle in sans_delai[:3]:
                print(f"             {cle} -> ttl={delais[cle]}")
            echecs += 1
        else:
            avant_delai = delais[next(iter(delais))]
            cle_temoin = next(iter(delais))
            appeler(arguments.base, CHEMIN_DEMANDE, contexte, charge={"email": inconnue})
            apres_delai = int(client.ttl(cle_temoin))
            if apres_delai > avant_delai:
                print(
                    f"    ECHEC    le delai a ete REPOUSSE : {avant_delai} -> {apres_delai}. "
                    "Un attaquant maintiendrait la cle vivante indefiniment"
                )
                echecs += 1
            else:
                print(
                    f"    ok       {len(delais)} cles ont un delai, et il ne recule pas "
                    f"({avant_delai} -> {apres_delai} s)"
                )

        #  --------------------------------------------------------------
        #  11. `request_origin_hash` EST RENSEIGNEE, ET CE N'EST PAS UNE IP
        #  --------------------------------------------------------------
        controles += 1
        code, sortie = psql(
            compose,
            env,
            "SELECT count(*), "  # noqa: S608 — seule `debut` est interpolee, lue de `psql`
            "  count(*) FILTER (WHERE request_origin_hash IS NULL), "
            "  count(*) FILTER (WHERE request_origin_hash ~ "
            "    '^[0-9a-f]{64}$') "
            "FROM auth_event WHERE occurred_at >= "
            f"'{debut}'::timestamptz",
        )
        if code or "|" not in sortie:
            print(f"    ECHEC    lecture d'`auth_event` : {sortie[:180]}")
            echecs += 1
        else:
            total, nulles, empreintes = (int(v) for v in sortie.splitlines()[0].split("|"))
            if total == 0:
                print("    ECHEC    aucun evenement produit : le controle ne prouverait rien")
                echecs += 1
            elif nulles or empreintes != total:
                print(
                    f"    ECHEC    {total} evenements : {nulles} sans origine, "
                    f"{total - empreintes} qui ne sont pas des empreintes de 64 hexadecimaux"
                )
                echecs += 1
            else:
                print(
                    f"    ok       {total} evenements, tous avec `request_origin_hash` en "
                    "empreinte — jamais une IP brute (§10.3)"
                )

        #  --------------------------------------------------------------
        #  12. LE JOURNAL DU CONTENEUR NE PORTE NI ADRESSE NI EMPREINTE
        #  --------------------------------------------------------------
        controles += 1
        journal = subprocess.run(  # noqa: S603
            [*compose, "logs", "--since", "10m", "api"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        texte = journal.stdout + journal.stderr
        fuites = []
        if MARQUEUR in texte:
            fuites.append("le marqueur de l'adresse figure dans le journal")
        for cle in cles:
            if cle.split(":")[-1] in texte:
                fuites.append("une empreinte de compteur figure dans le journal")
                break
        motifs_attendus = ("debit_depasse_par_adresse", "seuil_origine_atteint")
        vus = [m for m in motifs_attendus if m in texte]
        if fuites:
            print("    ECHEC    " + " ; ".join(fuites))
            echecs += 1
        elif not vus:
            print(
                "    ECHEC    aucun motif de depassement dans le journal : soit le journal "
                "n'est pas lu, soit rien n'a ete journalise. Un controle qui n'observe rien "
                "ne prouve rien"
            )
            echecs += 1
        else:
            print(
                f"    ok       journal : {len(vus)}/{len(motifs_attendus)} motifs presents "
                f"({', '.join(vus)}), aucune adresse ni empreinte"
            )

    finally:
        _purger(env, PREFIXE_REDIS)
        _nettoyer(compose, env, MARQUEUR, debut)

    print()
    if echecs:
        print(f"  ECHEC : {echecs} controle(s) non conformes sur {controles}")
        return 1
    print(f"  --> {controles} controles de limitation de debit, 0 echec")
    return 0


def _nettoyer(compose: list[str], env: dict[str, str], marqueur: str, debut: str) -> None:
    """Retirer le decor ET ce que les routes ont ecrit.

    **AUCUN TYPE D'EVENEMENT N'EST NOMME**, et c'est la lecon `T5-6` : nommer
    `MAGIC_LINK_REQUESTED` a fait vieillir `magic-link-check` des que `T4` a
    ajoute `LOGIN_FAILURE`. Une trace sans personne echappe a tout nettoyage par
    identite ; seule la borne temporelle l'attrape, et elle ne vieillit pas.
    """
    #  **UN SEUL POINT D'INTERPOLATION**, et c'est la raison de cette forme.
    #  Neuf f-strings auraient exige neuf exemptions `S608`, et une exemption par
    #  ligne finit par ne plus etre lue -- c'est le §7.25 applique a un linter.
    #  Ici le gabarit est litteral, et la substitution a lieu en un endroit.
    par_identite = (
        "auth_event WHERE person_id IN (SELECT id FROM person WHERE {ou})",
        "user_session WHERE person_id IN (SELECT id FROM person WHERE {ou})",
        "magic_link_request WHERE person_id IN (SELECT id FROM person WHERE {ou})",
        "admin_password_credential WHERE user_account_id IN "
        "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
        " WHERE p.{ou})",
        "user_account WHERE person_id IN (SELECT id FROM person WHERE {ou})",
        "entity_membership WHERE person_id IN (SELECT id FROM person WHERE {ou})",
        "person WHERE {ou}",
        "entity WHERE code = {code}",
        #  La trace d'un refus SANS personne n'a pas d'identite : seule la borne
        #  temporelle l'attrape.
        "auth_event WHERE person_id IS NULL AND occurred_at >= {depuis}",
    )
    litteraux = {
        "ou": f"email_normalized LIKE '{marqueur}%'",
        "code": f"'{marqueur}'",
        "depuis": f"'{debut}'::timestamptz",
    }
    for gabarit in par_identite:
        psql(compose, env, "DELETE FROM " + gabarit.format(**litteraux))  # noqa: S608


if __name__ == "__main__":
    sys.exit(main())
