#!/usr/bin/env sh
#
# Controle de la page de statut, telle qu'un navigateur la voit.
#
# LOT 1, sous-etape T5, story MVP-L01-US002.
#
# POURQUOI LES REQUETES PARTENT DE L'HOTE
#   Contrairement a verifier-sante.sh, qui interroge l'API depuis l'interieur du
#   conteneur, ce controle passe par Caddy en HTTPS sur app.onboarding.localhost
#   — le chemin exact d'un navigateur. C'est le seul moyen d'eprouver le
#   mandatement de DEC-470 : une requete interne au conteneur ne traverserait
#   pas Caddy et ne prouverait donc rien du montage.
#
# POURQUOI `curl -k`
#   La racine de l'autorite interne de Caddy n'est pas approuvee dans le
#   trousseau macOS ; c'est une action de Jonathan, elle demande son mot de
#   passe. Le certificat presente est bien celui de Caddy. Le script signale a
#   titre INFORMATIF si le mode strict passe, sans en faire un echec : sinon ce
#   controle dependrait d'une action humaine et non du livrable.
#
# CE QU'IL VERIFIE AUSSI, ET QUI COMPTE AUTANT
#   Le nombre de controles executes est confronte au nombre attendu. Un controle
#   qui n'annonce pas combien d'elements il a examines peut toujours n'en avoir
#   examine qu'un — lecon des defauts T2-4 et T2-6.
#
# Usage : verifier-page-statut.sh [origine]

set -u

BASE="${1:-https://app.onboarding.localhost}"

corps=$(mktemp) || exit 2
# shellcheck disable=SC2064
trap "rm -f '$corps'" EXIT

# Imprime le code HTTP, ou 000 si le transport a echoue. Le code de sortie de
# curl est lu DIRECTEMENT, jamais a travers un tuyau : c'est le piege qui a
# produit quatre controles menteurs dans ce lot.
requete() {
  chemin="$1"
  sortie=$(curl -k -s -S --max-time 10 -o "$corps" -w '%{http_code}' "$BASE$chemin" 2>/dev/null)
  statut=$?
  if [ "$statut" -ne 0 ]; then
    echo "000"
  else
    echo "$sortie"
  fi
}

attendus=6
examines=0
fautes=0

verdict() {
  libelle="$1"
  conforme="$2"
  detail="$3"
  examines=$((examines + 1))
  if [ "$conforme" = "oui" ]; then
    echo "    ok       $libelle  $detail"
  else
    echo "    ECHEC    $libelle  $detail"
    fautes=$((fautes + 1))
  fi
}

echo "  Page de statut, vue depuis $BASE"

# --- 1. La page repond et porte bien l'application -----------------------------
code=$(requete /)
if [ "$code" = "200" ] && grep -q 'id="racine"' "$corps" && grep -q '/src/main.tsx' "$corps"; then
  verdict "GET /                       " oui "HTTP $code  index.html avec la racine React"
else
  verdict "GET /                       " non "HTTP $code  racine React introuvable"
fi

# --- 2. Vite transforme reellement le module d'entree --------------------------
# Un `index.html` servi ne prouve pas que le module TypeScript est compile. Si
# la transformation echouait, la page resterait blanche — precisement ce que le
# cahier §17.4 interdit.
type_mime=$(curl -k -s -S --max-time 10 -o "$corps" -w '%{content_type}' "$BASE/src/main.tsx" 2>/dev/null)
statut_mime=$?
if [ "$statut_mime" -eq 0 ] && echo "$type_mime" | grep -q 'javascript'; then
  verdict "GET /src/main.tsx           " oui "type $type_mime  module transforme par Vite"
else
  verdict "GET /src/main.tsx           " non "type ${type_mime:-aucun}  transformation absente"
fi

# --- 3. Meme origine : /health/ready est bien mandate vers l'API ---------------
# C'est LE controle du montage DEC-470. Sans lui, la page appellerait Vite et
# recevrait un 404 indistinguable d'une API en panne.
code=$(requete /health/ready)
nb=$(tr ',' '\n' < "$corps" | grep -c '"nom"')
if { [ "$code" = "200" ] || [ "$code" = "503" ]; } && [ "$nb" = "3" ]; then
  verdict "GET /health/ready          " oui "HTTP $code  $nb dependances, mandate vers l'API"
else
  verdict "GET /health/ready          " non "HTTP $code  $nb dependances au lieu de 3"
fi

# --- 4. Meme origine : /health/version ----------------------------------------
code=$(requete /health/version)
if [ "$code" = "200" ] && grep -q '"version"' "$corps"; then
  verdict "GET /health/version        " oui "HTTP $code  $(cat "$corps")"
else
  verdict "GET /health/version        " non "HTTP $code  version illisible"
fi

# --- 5. Meme origine : le contrat versionne -----------------------------------
code=$(requete /api/v1/)
if [ "$code" = "200" ] && grep -q 'version_contrat' "$corps"; then
  verdict "GET /api/v1/               " oui "HTTP $code  contrat monte"
else
  verdict "GET /api/v1/               " non "HTTP $code  contrat injoignable"
fi

# --- 6. TEMOIN DISCRIMINANT : la sante n'est PAS sous le prefixe versionne ----
# Si ce chemin repondait 200, c'est que les endpoints d'exploitation auraient
# migre sous le contrat versionne, contre DEC-465. Un controle qui ne verifie
# que des succes ne distingue pas un montage juste d'un montage trop large.
code=$(requete /api/v1/health/ready)
if [ "$code" = "404" ]; then
  verdict "GET /api/v1/health/ready   " oui "HTTP $code  attendu : la sante est hors du prefixe (DEC-465)"
else
  verdict "GET /api/v1/health/ready   " non "HTTP $code  attendu 404"
fi

# --- Information, jamais un echec : le certificat est-il approuve ? -----------
echo
if curl -s -S --max-time 10 -o /dev/null "$BASE/" 2>/dev/null; then
  echo "  info     la racine de Caddy est approuvee : un navigateur n'affichera aucun avertissement"
else
  echo "  info     la racine de Caddy n'est PAS approuvee dans le trousseau macOS."
  echo "           Un navigateur affichera un avertissement de certificat. C'est"
  echo "           l'action de Jonathan, elle demande son mot de passe."
fi

echo
echo "  controles attendus : $attendus   executes : $examines"

if [ "$examines" -ne "$attendus" ]; then
  echo "  ECHEC : $examines controle(s) executes sur $attendus attendus" >&2
  exit 1
fi
if [ "$fautes" -ne 0 ]; then
  echo "  ECHEC : $fautes controle(s) non conformes" >&2
  exit 1
fi
echo "  --> la page de statut est servie et partage l'origine de l'API (DEC-470)"
