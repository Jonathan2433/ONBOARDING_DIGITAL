#!/usr/bin/env python3
"""Composer un fichier d'environnement depuis le modele, un calque et des secrets.

LOT 1, sous-etape T8, story MVP-L01-US002.

POURQUOI CE SCRIPT EXISTE, ALORS QUE `make env` FAISAIT DEJA LE TRAVAIL

    `make env` etait une recette shell : `cp .env.example .env`, puis cinq
    substitutions `sed`. Elle fonctionnait pour UN environnement et une seule
    valeur en dur — `MINIO_ROOT_USER=onboarding-dev-admin`.

    T8 doit engendrer un SECOND fichier, avec une quinzaine de valeurs
    differentes. Trois raisons de ne pas etendre le shell :

    1. LE DELIMITEUR DE `sed`. La forme employee est `s|^NOM=.*|NOM=valeur|`.
       Une valeur contenant `|` casse la substitution, et une valeur contenant
       `&` est reinjectee par sed comme la chaine appariee. Nos valeurs de
       recette portent `//` et `:` — aujourd'hui sans danger, mais la prochaine
       ne le sera peut-etre pas, et l'echec serait SILENCIEUX.
    2. LA PORTABILITE. `sed -i ''` de BSD fait echouer GNU sed, ce qui a casse
       toute la tache « stack » de l'integration continue en T6 (defaut T6-1).
       Ce script ne modifie jamais en place : il ecrit un fichier complet.
    3. UN CALQUE MAL ORTHOGRAPHIE NE FAIT RIEN, EN SILENCE. `sed` sur un motif
       absent sort en 0 sans rien changer. Une variable `POSTGRES_DBB` dans le
       calque serait donc ignoree, et la recette partagerait la base du
       developpement — la separation 2 sur 7 perdue sans un mot. Ce script
       REFUSE de continuer si le calque nomme une variable absente du modele.

    C'est le motif de T7 §7.2 applique une fois de plus : quand une classe
    d'erreur resiste a la vigilance, on change d'outil.

CE QU'IL NE FAIT PAS
    Il ne modifie JAMAIS un fichier existant, comme `make env` avant lui : ces
    fichiers portent des secrets engendres, et les regenerer invaliderait les
    donnees deja chiffrees ou les volumes deja crees. La reconciliation d'un
    fichier existant avec le modele est le travail de `make env-check`, qui
    NOMME les manquantes sans jamais ecrire — ECART-022.

    Il n'imprime AUCUNE valeur de secret. Il annonce combien il en a engendres,
    et le controle est le nombre, jamais la valeur.
"""

from __future__ import annotations

import argparse
import re
import secrets
import string
import sys
from pathlib import Path

# `make env` engendrait « tr -dc 'A-Za-z0-9' | head -c 48 ». Meme alphabet et
# meme longueur, pour que les deux environnements soient comparables.
ALPHABET_SECRET = string.ascii_letters + string.digits
LONGUEUR_SECRET = 48

# Les quatre secrets engendres aleatoirement. `MINIO_ROOT_USER` est traite a
# part : c'est un identifiant lisible, pas un mot de passe.
SECRETS_ALEATOIRES = (
    "APP_SECRET_KEY",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_PASSWORD",
)

# Volontairement laissees en CHANGE_ME, et ce n'est pas un oubli : leurs valeurs
# ne sont pas encore decidees. L'API ne les declare pas, donc le garde-fou du
# cahier 20.3 sur les CHANGE_ME residuels ne les voit pas (DEC-464).
CHANGE_ME_ASSUMES = {
    "IMPORT_SOURCE_RETENTION_DAYS": "sa valeur releve de QO-100, bloquante, LOT 9",
    "UPTIME_KUMA_PUSH_URL": "supervision externe, LOT 13",
}

MOTIF_AFFECTATION = re.compile(r"^([A-Z_][A-Z0-9_]*)=")


def noms_declares(texte: str) -> list[str]:
    """Les noms de variables affectees, dans l'ordre du fichier."""
    return [m.group(1) for ligne in texte.split("\n") if (m := MOTIF_AFFECTATION.match(ligne))]


def lire_calque(chemin: Path) -> dict[str, str]:
    """Les affectations d'un calque, commentaires et lignes vides ignores.

    Le decoupage est fait sur le PREMIER `=` seulement : une valeur peut en
    contenir. C'est le cas de PUBLIC_BASE_URL, qui porte une URL.
    """
    calque: dict[str, str] = {}
    for n, ligne in enumerate(chemin.read_text(encoding="utf-8").split("\n"), 1):
        depouillee = ligne.strip()
        if not depouillee or depouillee.startswith("#"):
            continue
        if not MOTIF_AFFECTATION.match(depouillee):
            raise SystemExit(f"{chemin}:{n} : ligne ni vide, ni commentaire, ni affectation")
        nom, _, valeur = depouillee.partition("=")
        if nom in calque:
            # Meme classe que le doublon APP_REVISION de ECART-022 : dans un
            # fichier de configuration, c'est la DERNIERE declaration qui gagne,
            # en silence, le jour ou les deux divergent.
            raise SystemExit(f"{chemin}:{n} : {nom} est declaree deux fois dans le calque")
        calque[nom] = valeur
    return calque


def composer(modele: Path, cible: Path, calque: Path | None, environnement: str) -> int:
    if cible.exists():
        print(f"  {cible} existe deja : inchange")
        print("  Pour verifier sa coherence avec le modele : make env-check")
        return 0

    texte = modele.read_text(encoding="utf-8")
    presents = set(noms_declares(texte))

    # Le calque d'abord, et sa VALIDATION avant toute ecriture.
    remplacements: dict[str, str] = {}
    if calque is not None:
        differences = lire_calque(calque)
        inconnues = sorted(n for n in differences if n not in presents)
        if inconnues:
            print(f"  ECHEC     le calque {calque} nomme des variables absentes du modele :")
            for n in inconnues:
                print(f"              {n}")
            print("            Une substitution sur un nom absent ne ferait RIEN, en silence,")
            print("            et la separation visee serait perdue sans un mot.")
            return 1
        remplacements.update(differences)
        print(
            f"  ok        calque {calque.name} : {len(differences)} variables, "
            "toutes connues du modele"
        )

    # Puis les secrets, qui ont le dernier mot : un calque versionne ne doit
    # jamais pouvoir fixer un secret.
    for nom in SECRETS_ALEATOIRES:
        if nom not in presents:
            print(f"  ECHEC     {nom} absente du modele : le secret n'aurait nulle part a aller")
            return 1
        remplacements[nom] = "".join(
            secrets.choice(ALPHABET_SECRET) for _ in range(LONGUEUR_SECRET)
        )
    remplacements["MINIO_ROOT_USER"] = f"onboarding-{environnement}-admin"

    # Reecriture ligne a ligne. Aucune expression reguliere de substitution :
    # on reconstruit l'affectation, donc aucun caractere de la valeur n'a de
    # sens special. C'est tout l'objet de ce script.
    lignes = texte.split("\n")
    appliquees: set[str] = set()
    for i, ligne in enumerate(lignes):
        m = MOTIF_AFFECTATION.match(ligne)
        if m is None:
            continue
        nom = m.group(1)
        if nom in remplacements:
            lignes[i] = f"{nom}={remplacements[nom]}"
            appliquees.add(nom)

    # COMPTER, ET CONFRONTER LE COMPTE A L'ATTENDU. Un ecart signifierait qu'une
    # variable presente dans `presents` n'a pas ete reecrite — donc que mon
    # detecteur de noms et ma reecriture ne voient pas les memes lignes.
    attendues = set(remplacements)
    if appliquees != attendues:
        manquantes = sorted(attendues - appliquees)
        print(f"  ECHEC     {len(appliquees)} substitutions appliquees, {len(attendues)} attendues")
        for n in manquantes:
            print(f"              non appliquee : {n}")
        return 1

    cible.write_text("\n".join(lignes), encoding="utf-8")
    print(f"  ok        {cible} cree depuis {modele.name}")
    print(f"  ok        {len(appliquees)} substitutions appliquees sur {len(attendues)} attendues")
    print(
        f"            dont {len(SECRETS_ALEATOIRES)} secrets engendres sur "
        f"{LONGUEUR_SECRET} caracteres, et MINIO_ROOT_USER lisible"
    )
    print("            AUCUNE valeur de secret n'est imprimee : le controle est le nombre")
    print()
    print("  RESTENT volontairement en CHANGE_ME, et ce n'est pas un oubli :")
    for nom, motif in CHANGE_ME_ASSUMES.items():
        print(f"    {nom:30s} -> {motif}")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--modele", required=True, type=Path)
    a.add_argument("--cible", required=True, type=Path)
    a.add_argument("--calque", type=Path, default=None)
    a.add_argument("--environnement", required=True)
    args = a.parse_args()

    if not args.modele.is_file():
        raise SystemExit(f"modele introuvable : {args.modele}")
    if args.calque is not None and not args.calque.is_file():
        raise SystemExit(f"calque introuvable : {args.calque}")
    return composer(args.modele, args.cible, args.calque, args.environnement)


if __name__ == "__main__":
    sys.exit(main())
