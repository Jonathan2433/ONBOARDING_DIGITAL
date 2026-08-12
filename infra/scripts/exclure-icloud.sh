#!/usr/bin/env sh
#
# Exclusion des dependances et des caches de la synchronisation iCloud.
#
# LOT 1, sous-etapes T1 et T2, story MVP-L01-US001. Decisions DEC-439, DEC-453.
#
# POURQUOI CE SCRIPT PLUTOT QU'UNE SIMPLE CIBLE DU MAKEFILE
#
#   Mesure du 27/07/2026 : `pnpm install` SUPPRIME et RECREE les repertoires
#   node_modules, ce qui efface l'attribut etendu pose precedemment. `uv`, lui,
#   reutilise le .venv existant et le preserve. Une cible de Makefile ne
#   protegerait donc que les installations lancees par `make` ; un
#   `pnpm install` direct rouvrirait silencieusement le risque ROAD-RSK-026.
#
#   Ce script est donc appele a deux endroits : par `make icloud-exclude`, et
#   par le `postinstall` de package.json, que pnpm execute apres CHAQUE
#   installation.
#
# POURQUOI DU sh POSIX ET NON DU bash
#
#   Le `postinstall` s'execute aussi a l'interieur des images Docker. L'image
#   node:24-alpine ne fournit PAS bash. Un script bash y ferait echouer
#   `pnpm install`, donc la construction de l'image web. Ce fichier n'emploie
#   ni tableau, ni BASH_SOURCE, ni aucune autre extension de bash.
#
# PORTEE
#
#   Ne fait rien hors macOS : l'attribut n'a de sens que pour le fournisseur
#   de fichiers iCloud. Le script sort en 0 pour ne pas casser une
#   installation en conteneur Linux ou en integration continue.
#
# CE QUI EST PROUVE, ET CE QUI NE L'EST PAS
#
#   Prouve : l'attribut est pose et relu, et un repertoire non marque est
#   correctement detecte comme tel (`make icloud-verify`).
#   Non prouve localement : le respect effectif de l'attribut par iCloud.
#   C'est une convention documentee par Apple pour le File Provider, dont
#   aucun outil disponible sur cette machine ne permet de verifier l'effet.
#   `brctl` ne couvre pas les chemins CloudDocs et renvoie 0 sur erreur.
#   L'attribut n'est PAS durable : voir l'incident du 27/07 en ROAD-RSK-026.

set -u

ATTRIBUT='com.apple.fileprovider.ignore#P'

if [ "$(uname -s)" != "Darwin" ]; then
  echo "  exclusion iCloud sans objet hors macOS ($(uname -s))"
  exit 0
fi

# $0 et non BASH_SOURCE : POSIX sh ne connait pas BASH_SOURCE.
racine=$(cd "$(dirname "$0")/../.." && pwd) || exit 1
cd "$racine" || exit 1

marques=0
total=0

# Liste en document en ligne, parcourue par `while read` : en zsh comme en sh,
# une variable non citee n'est pas garantie decoupee en mots. Une boucle
# explicite ne peut pas se tromper sur le nombre d'elements.
while IFS= read -r repertoire; do
  [ -z "$repertoire" ] && continue
  total=$((total + 1))
  mkdir -p "$repertoire" || continue
  if xattr -w "$ATTRIBUT" 1 "$repertoire" 2>/dev/null; then
    marques=$((marques + 1))
  else
    echo "  ECHEC de marquage : $repertoire" >&2
  fi
done <<'EOF'
node_modules
apps/web/node_modules
packages/ui/node_modules
packages/contracts/node_modules
.venv
.ruff_cache
.mypy_cache
.pytest_cache
EOF

echo "  $marques/$total repertoires exclus de la synchronisation iCloud"
