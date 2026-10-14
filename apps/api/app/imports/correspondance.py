"""Le profil de correspondance PROVISOIRE des en-tetes — `DEC-434`, `QO-110` ouverte.

LOT 9, sous-etape `T7`, story `MVP-L09-US004` (2/2).

POURQUOI UN PROFIL, ET POURQUOI CELUI-LA PRECISEMENT

  Le schema du CSV (`docs/architecture/donnees/schema-csv-collaborateurs.md`
  §3, `DEC-434`) decouple deux choses : des CHAMPS LOGIQUES stables `F01` a
  `F19`, et un « profil de correspondance versionne » qui associe les
  en-tetes REELLES du fichier a ces champs. La nomenclature des en-tetes
  reste ouverte (`QO-110`) — aucun document ne fixe la langue ni l'intitule
  des colonnes du fichier reel.

  Ce module ne resout PAS `QO-110` : il reprend TEL QUEL le « profil
  provisoire » deja produit au LOT 0 pour le jeu d'exemple fictif
  (`docs/architecture/donnees/exemples/collaborateurs-exemple-fictif.csv`,
  `exemples/README.md` §2 : « Ce profil provisoire existe uniquement pour
  rendre le schema demontrable. Il ne prejuge ni de la langue ni de
  l'intitule des colonnes definitives. »). C'est la SEULE nomenclature non
  normative mais deja officiellement produite — en inventer une autre aurait
  ete une seconde invention, moins justifiee que de reutiliser celle qui
  existe deja (§6.5).

  Quand `QO-110` se resoudra, et quand un vrai mecanisme de profil VERSIONNE
  par lot existera (pose avec le lot d'import, pas une constante du code),
  ce module sera celui qui change — en un seul endroit, puisque `T7` a T10
  lisent tous `valeur_logique` plutot que de relire `raw_data` directement.
"""

from __future__ import annotations

from typing import Final

#  Ordre F01-F19, cahier §19 et schema-csv-collaborateurs.md §5. Chaque valeur
#  est la cle litterale du dictionnaire `import_row.raw_data` tel que lu par
#  `app.imports.depot` sur le jeu d'exemple fictif du LOT 0 — PROVISOIRE,
#  sans aucune valeur normative (`QO-110`).
PROFIL_DE_CORRESPONDANCE_PROVISOIRE: Final[dict[str, str]] = {
    "F01": "email",
    "F02": "nom",
    "F03": "prenom",
    "F04": "nom_usage",
    "F05": "entite",
    "F06": "date_arrivee",
    "F07": "date_depart",
    "F08": "categorie_professionnelle",
    "F09": "presentation_courte",
    "F10": "fun_fact",
    "F11": "metier",
    "F12": "situation",
    "F13": "client",
    "F14": "cercle_principal",
    "F15": "cercles_secondaires",
    "F16": "email_dsm",
    "F17": "responsabilites_framework",
    "F18": "roles_techniques",
    "F19": "autorisation_photo",
}


def valeur_logique(ligne: dict[str, object], code: str) -> str | None:
    """La valeur BRUTE d'un champ logique (`F01`...`F19`) dans une ligne, ou `None`.

    `None` couvre deux cas indistingables ICI, et c'est voulu a ce niveau :
    l'en-tete est absente de la ligne (colonne manquante, `T6`) OU la valeur
    est une chaine vide une fois nettoyee des espaces de bordure. Les DEUX
    valent « rien renseigne » pour un champ logique — distinguer « colonne
    absente » de « colonne vide » est une question de PROFIL DE
    CORRESPONDANCE (`E-STRUCT-005`), hors perimetre de `T7`.
    """
    en_tete = PROFIL_DE_CORRESPONDANCE_PROVISOIRE[code]
    valeur = ligne.get(en_tete)
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None
