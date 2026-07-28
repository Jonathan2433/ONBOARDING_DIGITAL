#!/usr/bin/env sh
#
# Preuve que les volumes de donnees survivent a un arret et a un redemarrage.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
# Critere litteral du backlog : « les volumes survivent au redemarrage ».
#
# COMMENT LA PREUVE EST CONSTRUITE
#
#   Le script releve, pour chacun des cinq services a etat, une empreinte qui
#   ne peut pas etre identique par hasard apres une recreation du volume :
#
#     db       system_identifier de PostgreSQL. Il est tire au sort a l'initdb.
#              Un volume recree en produirait un autre. AUCUNE TABLE N'EST
#              CREEE : le LOT 1 n'a droit qu'a la migration 0001_initial, et
#              elle appartient a T3.
#     redis    une cle temoin ecrite avec l'horodatage de la capture.
#     minio    un objet temoin depose dans le bucket.
#     mailpit  le nombre de messages stockes, plus l'empreinte du fichier de
#              base de donnees.
#     caddy    empreinte de la racine de l'autorite de certification interne.
#              La perdre obligerait a reapprouver la racine dans le trousseau
#              macOS, ce qui demande le mot de passe de Jonathan.
#
# USAGE
#   verifier-persistance.sh capture  <.env> <compose.yml>...
#   verifier-persistance.sh compare  <.env> <compose.yml>...
#
#   La capture ecrit son releve dans un fichier temporaire hors du depot ;
#   la comparaison relit ce releve et echoue a la premiere divergence.

set -u

RELEVE="${TMPDIR:-/tmp}/onboarding-persistance.txt"

if [ "$#" -lt 3 ]; then
  echo "  usage : verifier-persistance.sh capture|compare <.env> <compose.yml>..." >&2
  exit 2
fi

mode="$1"
env_file="$2"
shift 2

# Assemblage des options -f SANS eval.
#
# La premiere version de cette fonction employait `eval`, qui re-analysait les
# arguments de commande : un `sh -c '...'` y perdait ses quotes et se faisait
# decouper en mots. Le script mourait sans message.
#
# Ici, $COMPOSE_FILES est volontairement NON cite — le decoupage en mots est
# l'effet recherche — tandis que $env_file, qui contient une espace parce que
# le depot vit sous ~/Library/Mobile Documents/, est cite, et "$@" reste
# intact. Un chemin Compose contenant une espace casserait ce montage : le
# script refuse alors de continuer plutot que de se tromper en silence.
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

# --- Relevé des cinq empreintes ------------------------------------------------

releve_db() {
  dc exec -T db sh -c \
    'psql -qtAX -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT system_identifier FROM pg_control_system();"' \
    2>/dev/null | tr -d ' \r\n'
}

releve_redis() {
  dc exec -T redis sh -c \
    'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning GET onboarding:persistance:temoin' \
    2>/dev/null | tr -d ' \r\n'
}

releve_minio() {
  dc exec -T minio sh -c \
    'mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null \
     && mc cat "local/$MINIO_BUCKET/persistance-temoin.txt"' \
    2>/dev/null | tr -d ' \r\n'
}

# Le nombre de messages ET l'identifiant du plus recent.
#
# La premiere version ne relevait que le debut de la reponse JSON, qui valait
# {"total":0,...} sur une instance vide. Un volume EFFACE aurait rendu la meme
# valeur, et la comparaison aurait conclu « identique » : un controle
# incapable d'echouer. La capture depose donc un message reel et refuse de
# continuer si le total reste a zero.
releve_mailpit() {
  dc exec -T mailpit sh -c \
    'wget -qO- "http://127.0.0.1:8025/api/v1/messages?limit=1" 2>/dev/null' \
    2>/dev/null \
    | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
msgs = d.get("messages") or []
print("total=%s;id=%s" % (d.get("total", "?"), msgs[0].get("ID", "-") if msgs else "-"))
'
}

releve_caddy() {
  dc exec -T caddy sh -c \
    'sha256sum /data/caddy/pki/authorities/local/root.crt 2>/dev/null | cut -c1-64' \
    2>/dev/null | tr -d ' \r\n'
}

# --- Capture -------------------------------------------------------------------

if [ "$mode" = "capture" ]; then
  marque="temoin-$(date -u +%Y%m%dT%H%M%SZ)"

  # Redis : une cle temoin. Le BGREWRITEAOF force l'ecriture immediate du
  # journal, sinon l'arret pourrait precéder la persistance.
  dc exec -T redis sh -c \
    "redis-cli -a \"\$REDIS_PASSWORD\" --no-auth-warning SET onboarding:persistance:temoin $marque >/dev/null \
     && redis-cli -a \"\$REDIS_PASSWORD\" --no-auth-warning BGREWRITEAOF >/dev/null" \
    2>/dev/null || { echo "  ECHEC d'ecriture du temoin Redis" >&2; exit 1; }

  # MinIO : un objet temoin dans le bucket.
  dc exec -T minio sh -c \
    "mc alias set local http://127.0.0.1:9000 \"\$MINIO_ROOT_USER\" \"\$MINIO_ROOT_PASSWORD\" >/dev/null \
     && echo $marque | mc pipe \"local/\$MINIO_BUCKET/persistance-temoin.txt\" >/dev/null" \
    2>/dev/null || { echo "  ECHEC d'ecriture du temoin MinIO" >&2; exit 1; }

  # Mailpit : un message reel, depose par SMTP depuis le conteneur api. Deux
  # effets : le total cesse d'etre nul, donc la comparaison peut echouer ; et
  # l'on prouve au passage que api joint mailpit sur le reseau interne.
  # smtplib appartient a la bibliotheque standard : aucune dependance ajoutee.
  dc exec -T api python -c "
import smtplib, os
from email.message import EmailMessage
m = EmailMessage()
m['From'] = 'no-reply@exalt-company.com'
m['To'] = 'temoin@exalt-company.com'
m['Subject'] = 'Temoin de persistance $marque'
m.set_content('Message temoin de la sous-etape T2. Aucune donnee personnelle.')
with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']), timeout=10) as s:
    s.send_message(m)
" >/dev/null 2>&1 || { echo "  ECHEC d'envoi du temoin Mailpit" >&2; exit 1; }

  {
    echo "db=$(releve_db)"
    echo "redis=$(releve_redis)"
    echo "minio=$(releve_minio)"
    echo "mailpit=$(releve_mailpit)"
    echo "caddy=$(releve_caddy)"
  } > "$RELEVE"

  echo "  releve avant redemarrage :"
  vides=0
  while IFS='=' read -r cle valeur; do
    if [ -z "$valeur" ]; then
      printf '    %-9s VIDE — le controle ne prouverait rien\n' "$cle"
      vides=$((vides + 1))
    else
      printf '    %-9s %s\n' "$cle" "$(printf '%s' "$valeur" | cut -c1-46)"
    fi
  done < "$RELEVE"

  # Temoin positif du controle lui-meme : une empreinte vide signifierait que
  # la comparaison ulterieure comparerait du vide a du vide et « reussirait ».
  if [ "$vides" -ne 0 ]; then
    echo "  ECHEC : $vides empreinte(s) vide(s). Le controle serait incapable d'echouer." >&2
    exit 1
  fi

  # Meme exigence pour Mailpit : un total nul serait indistinguable d'un volume
  # efface. Si le message temoin n'est pas arrive, le controle ne prouve rien.
  if grep -q '^mailpit=total=0;' "$RELEVE"; then
    echo "  ECHEC : Mailpit ne contient aucun message. Un volume efface donnerait" >&2
    echo "          la meme valeur : le controle serait incapable d'echouer." >&2
    exit 1
  fi

  echo "  5/5 empreintes relevees, aucune vide, Mailpit non vide"
  exit 0
fi

# --- Comparaison ---------------------------------------------------------------

if [ "$mode" = "compare" ]; then
  [ -f "$RELEVE" ] || { echo "  ECHEC : aucun releve. Lancer d'abord la capture." >&2; exit 1; }

  divergences=0
  examines=0
  attendus=$(grep -c '^[a-z]*=' "$RELEVE")

  echo "  comparaison apres redemarrage :"

  # LECTURE SUR LE DESCRIPTEUR 3, ET NON SUR L'ENTREE STANDARD.
  #
  # La premiere version lisait le releve sur stdin. Les `docker compose exec`
  # appeles dans la boucle consommaient cette meme entree et avalaient le
  # reste du fichier : le controle n'examinait que la PREMIERE ligne, puis
  # annoncait « les 5 volumes ont survecu ». Il affirmait cinq en ayant
  # verifie un. Le compteur `examines` ci-dessous rend cette erreur
  # impossible a repeter en silence.
  while IFS='=' read -r cle avant <&3; do
    case "$cle" in
      db)      apres=$(releve_db      </dev/null) ;;
      redis)   apres=$(releve_redis   </dev/null) ;;
      minio)   apres=$(releve_minio   </dev/null) ;;
      mailpit) apres=$(releve_mailpit </dev/null) ;;
      caddy)   apres=$(releve_caddy   </dev/null) ;;
      *)       continue ;;
    esac
    examines=$((examines + 1))
    if [ -z "$apres" ]; then
      printf '    %-9s PERDU — empreinte introuvable apres redemarrage\n' "$cle"
      divergences=$((divergences + 1))
    elif [ "$avant" = "$apres" ]; then
      printf '    %-9s identique\n' "$cle"
    else
      printf '    %-9s DIVERGENTE\n      avant : %s\n      apres : %s\n' "$cle" "$avant" "$apres"
      divergences=$((divergences + 1))
    fi
  done 3< "$RELEVE"

  echo
  echo "  empreintes relevees : $attendus   comparees : $examines"

  if [ "$examines" -ne "$attendus" ]; then
    echo "  ECHEC : le controle n'a compare que $examines empreinte(s) sur $attendus." >&2
    echo "          Il porterait sur un sous-ensemble et ne prouverait rien." >&2
    exit 1
  fi
  if [ "$divergences" -ne 0 ]; then
    echo "  ECHEC : $divergences volume(s) n'ont pas survecu au redemarrage" >&2
    exit 1
  fi
  echo "  --> les $examines volumes a etat ont survecu au redemarrage"
  exit 0
fi

echo "  mode inconnu : $mode" >&2
exit 2
