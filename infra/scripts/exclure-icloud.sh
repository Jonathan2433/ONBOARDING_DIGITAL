#!/usr/bin/env bash
#
# Exclusion des dependances et des caches de la synchronisation iCloud.
#
# LOT 1, sous-etape T1, story MVP-L01-US001. Decision DEC-439.
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

set -uo pipefail

ATTRIBUT='com.apple.fileprovider.ignore#P'

REPERTOIRES=(
  node_modules
  apps/web/node_modules
  packages/ui/node_modules
  packages/contracts/node_modules
  .venv
  .ruff_cache
  .mypy_cache
  .pytest_cache
)

if [ "$(uname -s)" != "Darwin" ]; then
  echo "  exclusion iCloud sans objet hors macOS ($(uname -s))"
  exit 0
fi

racine="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$racine" || exit 1

marques=0
for repertoire in "${REPERTOIRES[@]}"; do
  mkdir -p "$repertoire" || continue
  if xattr -w "$ATTRIBUT" 1 "$repertoire" 2>/dev/null; then
    marques=$((marques + 1))
  else
    echo "  ECHEC de marquage : $repertoire" >&2
  fi
done

echo "  $marques/${#REPERTOIRES[@]} repertoires exclus de la synchronisation iCloud"
