#!/usr/bin/env sh
#
# Interrogation des trois endpoints de sante du cahier §18.7.
#
# LOT 1, sous-etape T3, story MVP-L01-US003.
#
# CE QUE CE SCRIPT PROUVE
#   Que les trois endpoints repondent, avec le code attendu, et que la reponse
#   porte bien ce qu'elle doit porter. Il lit le CODE HTTP et le CONTENU, pas
#   seulement le fait que la requete aboutit.
#
# CE QU'IL VERIFIE AUSSI, ET QUI COMPTE AUTANT
#   Que le nombre d'endpoints interroges correspond au nombre attendu. Un
#   controle qui n'annonce pas combien d'elements il a examines peut toujours
#   n'en avoir examine qu'un — c'est la lecon des defauts T2-4 et T2-6.
#
# Usage : verifier-sante.sh <chemin du .env> <fichier compose>...

set -u

if [ "$#" -lt 2 ]; then
  echo "  usage : verifier-sante.sh <.env> <compose.yml>..." >&2
  exit 2
fi

env_file="$1"
shift

COMPOSE_FILES=""
for f in "$@"; do
  case "$f" in
    *" "*) echo "  ECHEC : le chemin Compose « $f » contient une espace" >&2; exit 2 ;;
  esac
  COMPOSE_FILES="$COMPOSE_FILES -f $f"
done

dc() {
  # shellcheck disable=SC2086
  docker compose --env-file "$env_file" $COMPOSE_FILES "$@"
}

# Les requetes partent DE L'INTERIEUR du conteneur api : le service n'est pas
# publie sur l'hote, seul Caddy le joint (cahier §22.2). urllib et non curl,
# absent de l'image python:slim.
interroger() {
  chemin="$1"
  dc exec -T api python -c "
import json, sys, urllib.error, urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000$chemin', timeout=8)
    code, corps = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    code, corps = e.code, e.read().decode()
except Exception as e:
    print('0|' + type(e).__name__); sys.exit(0)
print(str(code) + '|' + json.dumps(json.loads(corps), ensure_ascii=False))
" 2>/dev/null
}

attendus=3
examines=0
fautes=0

echo "  Endpoints de sante (cahier §18.7)"

# --- /health/live -------------------------------------------------------------
resultat=$(interroger /health/live)
examines=$((examines + 1))
code=${resultat%%|*}
corps=${resultat#*|}
if [ "$code" = "200" ] && echo "$corps" | grep -q '"vivant"'; then
  echo "    ok       /health/live      HTTP $code  $corps"
else
  echo "    ECHEC    /health/live      HTTP $code  $corps"
  fautes=$((fautes + 1))
fi

# --- /health/ready -----------------------------------------------------------
resultat=$(interroger /health/ready)
examines=$((examines + 1))
code=${resultat%%|*}
corps=${resultat#*|}
# Le nombre de dependances sondees est verifie : un `ready` qui n'en sonderait
# qu'une repondrait 200 tout en ne prouvant presque rien.
nb_dependances=$(echo "$corps" | tr ',' '\n' | grep -c '"nom"')
if [ "$code" = "200" ] && [ "$nb_dependances" = "3" ]; then
  echo "    ok       /health/ready     HTTP $code  $nb_dependances dependances sondees"
  echo "$corps" | tr '{' '\n' | grep '"nom"' | sed 's/^/               /'
else
  echo "    ECHEC    /health/ready     HTTP $code  $nb_dependances dependances  $corps"
  fautes=$((fautes + 1))
fi

# --- /health/version ---------------------------------------------------------
resultat=$(interroger /health/version)
examines=$((examines + 1))
code=${resultat%%|*}
corps=${resultat#*|}
if [ "$code" = "200" ] && echo "$corps" | grep -q '"version"'; then
  echo "    ok       /health/version   HTTP $code  $corps"
else
  echo "    ECHEC    /health/version   HTTP $code  $corps"
  fautes=$((fautes + 1))
fi

echo
echo "  endpoints attendus : $attendus   interroges : $examines"

if [ "$examines" -ne "$attendus" ]; then
  echo "  ECHEC : $examines endpoint(s) interroges sur $attendus attendus" >&2
  exit 1
fi
if [ "$fautes" -ne 0 ]; then
  echo "  ECHEC : $fautes endpoint(s) non conformes" >&2
  exit 1
fi
echo "  --> les $attendus endpoints de sante repondent conformement au cahier §18.7"
