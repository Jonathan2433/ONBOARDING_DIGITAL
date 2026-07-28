#!/usr/bin/env sh
#
# Verification des publications de ports de la stack locale.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
# Exigence : cahier des charges 22.2 — PostgreSQL, Redis, MinIO et Mailpit ne
# sont jamais exposes publiquement.
#
# POURQUOI UN SCRIPT ET NON QUELQUES LIGNES DE MAKEFILE
#
#   La premiere version de ce controle etait ecrite en shell dans le Makefile.
#   Elle decoupait la colonne PORTS de `docker ps` et n'examinait que la
#   PREMIERE publication de chaque conteneur : sur les sept publications de la
#   stack, elle en voyait cinq, et concluait « aucune exposition » sans avoir
#   regarde les deux ports de MinIO. Un controle qui sous-couvre est un
#   controle menteur.
#
# CE QUE CE CONTROLE VERIFIE
#
#   1. Toutes les publications DECLAREES dans la configuration Compose assemblee
#      sont liees a 127.0.0.1 ;
#   2. toutes les publications REELLES du moteur Docker le sont aussi ;
#   3. les deux nombres CONCORDENT. Sans ce troisieme point, un controle
#      pourrait porter sur un sous-ensemble et paraitre concluant.
#
#   Le script echoue si l'une des trois conditions n'est pas remplie.
#
# Usage : verifier-ports.sh <chemin du .env> <fichier compose>...

set -u

if [ "$#" -lt 2 ]; then
  echo "  usage : verifier-ports.sh <.env> <compose.yml>..." >&2
  exit 2
fi

env_file="$1"
shift

# Assemblage des options -f SANS eval : $COMPOSE_FILES est volontairement non
# cite, le decoupage en mots etant l'effet recherche, tandis que $env_file est
# cite parce qu'il contient une espace — le depot vit sous
# ~/Library/Mobile Documents/. Un chemin Compose avec une espace casserait ce
# montage : le script refuse alors de continuer.
COMPOSE_FILES=""
for f in "$@"; do
  case "$f" in
    *" "*) echo "  ECHEC : le chemin Compose « $f » contient une espace" >&2; exit 2 ;;
  esac
  COMPOSE_FILES="$COMPOSE_FILES -f $f"
done

# shellcheck disable=SC2086
config=$(docker compose --env-file "$env_file" $COMPOSE_FILES config --format json 2>&1) || {
  echo "  ECHEC de lecture de la configuration Compose :" >&2
  echo "$config" | head -3 >&2
  exit 1
}

projet=$(printf '%s' "$config" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))')

runtime=$(docker ps --filter "label=com.docker.compose.project=$projet" --format '{{.Names}}' \
  | while IFS= read -r nom; do
      docker inspect --format \
        '{{range $p, $b := .NetworkSettings.Ports}}{{range $b}}{{$.Name}} {{.HostIp}} {{.HostPort}} {{$p}}
{{end}}{{end}}' "$nom"
    done | grep -v '^$')

printf '%s' "$config" | CONFIG_PROJET="$projet" RUNTIME="$runtime" python3 -c '
import json, os, sys

config = json.load(sys.stdin)
attendu = "127.0.0.1"

declarees = []
for service, corps in sorted(config.get("services", {}).items()):
    for p in corps.get("ports", []):
        declarees.append((service, p.get("host_ip", "0.0.0.0"), str(p.get("published"))))

reelles = []
for ligne in os.environ.get("RUNTIME", "").strip().split("\n"):
    if not ligne.strip():
        continue
    morceaux = ligne.split()
    if len(morceaux) >= 4:
        reelles.append((morceaux[0].lstrip("/"), morceaux[1], morceaux[2]))

fautes = 0

print("  DECLARE dans la configuration Compose")
for service, ip, port in declarees:
    ok = ip == attendu
    fautes += not ok
    print("    %s %-9s %s:%s" % ("ok     " if ok else "EXPOSE ", service, ip, port))

print("  REEL dans le moteur Docker")
for nom, ip, port in sorted(reelles):
    # Docker liste separement IPv4 et IPv6 ; ::1 est aussi la boucle locale.
    ok = ip in (attendu, "::1")
    fautes += not ok
    print("    %s %-28s %s:%s" % ("ok     " if ok else "EXPOSE ", nom, ip, port))

# IPv6 mis a part, les deux vues doivent porter le meme nombre de publications.
reelles_v4 = [r for r in reelles if ":" not in r[1]]
print()
print("  declarees : %d   reelles IPv4 : %d" % (len(declarees), len(reelles_v4)))

if not declarees:
    print("  ECHEC : aucune publication declaree, le controle ne prouverait rien")
    sys.exit(1)
if len(declarees) != len(reelles_v4):
    print("  ECHEC : les deux vues ne concordent pas, le controle porterait sur un sous-ensemble")
    sys.exit(1)
if fautes:
    print("  ECHEC : %d publication(s) hors de la boucle locale (cahier 22.2)" % fautes)
    sys.exit(1)

print("  --> %d publications, toutes limitees a la boucle locale (cahier 22.2)" % len(declarees))
'
