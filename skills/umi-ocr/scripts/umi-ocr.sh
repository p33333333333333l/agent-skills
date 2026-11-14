#!/usr/bin/env bash
# Umi-OCR helper: run OCR on an image or a screen region, managing the service.
#
# Usage:
#   umi-ocr.sh ocr <image> [options]
#   umi-ocr.sh shot [--rect x,y,w,h] [--screen N] [options]
#   umi-ocr.sh status
#   umi-ocr.sh stop
#
# Options for ocr/shot:
#   --format dict|text   dict = confidence + box + text per line (default); text = joined text
#   --lang LANG          chinese|en|chinese_cht|japan|korean|cyrillic (default: chinese)
#   --upscale N          resize image N times before OCR (small text: try 2 or 3)
#   --parser NAME        tbpu.parser; none keeps raw lines, better for code and small text
#   --limit N            ocr.limit_side_len (default 999999 = no downscale)
#   --json               emit the raw API JSON instead of the readable report
#   --keep               leave the service running when this call started it
#
# Exit codes: 0 ok, 1 usage/IO error, 2 OCR returned no text, 3 service unavailable.
set -uo pipefail

APP_DIR=${UMI_OCR_DIR:-$HOME/Applications/Umi-OCR}
HOST=${UMI_OCR_HOST:-127.0.0.1}
PORT=${UMI_OCR_PORT:-1224}
BASE="http://$HOST:$PORT"
START_TIMEOUT=${UMI_OCR_START_TIMEOUT:-25}

die() { printf '%s\n' "$1" >&2; exit "${2:-1}"; }

service_up() { curl -fsS -m 2 "$BASE/api/ocr/get_options" >/dev/null 2>&1; }

# Print "started" on stdout when this call launched the service.
ensure_service() {
    if service_up; then return 1; fi
    [ -x "$APP_DIR/umi-ocr.sh" ] || die "Umi-OCR not found at $APP_DIR (set UMI_OCR_DIR)" 3
    local display=${UMI_OCR_DISPLAY:-${DISPLAY:-:0}}
    ( cd "$APP_DIR" && DISPLAY="$display" nohup ./umi-ocr.sh --hide \
        >"${TMPDIR:-/tmp}/umi-ocr-service.log" 2>&1 & ) || die "failed to launch Umi-OCR" 3
    local waited=0
    while [ "$waited" -lt "$START_TIMEOUT" ]; do
        sleep 1
        waited=$((waited + 1))
        service_up && return 0
    done
    die "Umi-OCR HTTP service did not come up on $BASE within ${START_TIMEOUT}s; see ${TMPDIR:-/tmp}/umi-ocr-service.log" 3
}

stop_service() {
    service_up || return 0
    # /argv takes a plain JSON list of CLI arguments, not an {"argv": [...]} object.
    curl -fsS -m 10 -X POST "$BASE/argv" -H 'Content-Type: application/json' \
        -d '["--quit"]' >/dev/null 2>&1
    for _ in $(seq 1 10); do
        service_up || return 0
        sleep 1
    done
}

lang_file() {
    case "$1" in
        chinese|zh)   printf 'models/config_chinese.txt' ;;
        en|english)   printf 'models/config_en.txt' ;;
        cht|chinese_cht) printf 'models/config_chinese_cht.txt' ;;
        japan|ja)     printf 'models/config_japan.txt' ;;
        korean|ko)    printf 'models/config_korean.txt' ;;
        cyrillic|ru)  printf 'models/config_cyrillic.txt' ;;
        *) die "unknown --lang '$1' (chinese|en|chinese_cht|japan|korean|cyrillic)" ;;
    esac
}

MODE=${1:-}
shift || true
case "$MODE" in
    status)
        if service_up; then echo "running on $BASE"; else echo "not running"; fi
        exit 0 ;;
    stop)
        stop_service; echo "stopped"; exit 0 ;;
    ocr|shot) ;;
    ''|-h|--help)
        sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown command '$MODE' (ocr|shot|status|stop)" ;;
esac

IMAGE=''
FORMAT=dict
LANG=chinese
UPSCALE=1
PARSER=''
RAW=0
KEEP=0
RECT=''
SCREEN=''
LIMIT_SIDE=999999

while [ $# -gt 0 ]; do
    case "$1" in
        --format)  FORMAT=${2:?}; shift 2 ;;
        --lang)    LANG=${2:?}; shift 2 ;;
        --upscale) UPSCALE=${2:?}; shift 2 ;;
        --parser)  PARSER=${2:?}; shift 2 ;;
        --limit)   LIMIT_SIDE=${2:?}; shift 2 ;;
        --json)    RAW=1; shift ;;
        --keep)    KEEP=1; shift ;;
        --rect)    RECT=${2:?}; shift 2 ;;
        --screen)  SCREEN=${2:?}; shift 2 ;;
        -*)        die "unknown option '$1'" ;;
        *)         IMAGE=$1; shift ;;
    esac
done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/umi-ocr.XXXXXX") || die "cannot create temp dir"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

STARTED=0
ensure_service && STARTED=1
finish() {
    if [ "$STARTED" = 1 ] && [ "$KEEP" = 0 ]; then stop_service; fi
}
trap 'finish; cleanup' EXIT

# --- obtain the image -------------------------------------------------------
if [ "$MODE" = shot ]; then
    command -v spectacle >/dev/null || die "spectacle not found; cannot capture the screen" 3
    IMAGE="$WORK/shot.png"
    # Capture the full screen, then crop: spectacle's own -r opens an interactive
    # selector, which blocks a non-interactive call.
    shot_args=(-b -n -f -o "$IMAGE")
    [ -n "$SCREEN" ] && shot_args+=(-m)
    spectacle "${shot_args[@]}" || die "spectacle capture failed" 3
    [ -s "$IMAGE" ] || die "spectacle produced no image" 3
    if [ -n "$RECT" ]; then
        IFS=, read -r RX RY RW RH <<<"$RECT"
        python3 - "$IMAGE" "$RX" "$RY" "$RW" "$RH" <<'PY' || die "crop failed" 1
import sys
from PIL import Image
path, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
im = Image.open(path)
im.crop((x, y, x + w, y + h)).save(path)
PY
    fi
else
    [ -n "$IMAGE" ] || die "usage: $0 ocr <image> [options]" 1
    [ -f "$IMAGE" ] || die "image not found: $IMAGE" 1
    # Normalize into a private PNG copy: --upscale rewrites the file, and the
    # user's image is read-only input. Re-encoding also strips odd formats.
    python3 - "$IMAGE" "$WORK/input.png" <<'PY' || die "cannot read $IMAGE (unsupported image format?)" 1
import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
Image.open(src).convert("RGB").save(dst)
PY
    IMAGE="$WORK/input.png"
fi

# --- optional upscale for small text --------------------------------------
# Coordinates in the report are divided back by the same factor, so they always
# refer to the image the caller passed in.
SCALE=1
if [ "$UPSCALE" != 1 ]; then
    python3 - "$IMAGE" "$UPSCALE" <<'PY' || die "upscale failed" 1
import sys
from PIL import Image
path, factor = sys.argv[1], float(sys.argv[2])
im = Image.open(path)
im.resize((round(im.width * factor), round(im.height * factor)), Image.LANCZOS).save(path)
PY
    SCALE=$UPSCALE
fi

# --- call the API ----------------------------------------------------------
# base64 goes through a file: a 4K screenshot exceeds the argv size limit.
B64_FILE="$WORK/image.b64"
base64 -w0 "$IMAGE" >"$B64_FILE" || die "base64 encode failed" 1
# Validate in the parent shell: die() inside $(...) would only exit the subshell.
LANG_FILE=$(lang_file "$LANG") || exit 1
[ -n "$LANG_FILE" ] || die "unknown --lang '$LANG'" 1
jq -n --rawfile b "$B64_FILE" --arg lang "$LANG_FILE" --arg fmt "$FORMAT" \
      --arg parser "$PARSER" --argjson side "$LIMIT_SIDE" '
    {base64: $b,
     options: ({"ocr.language": $lang, "data.format": $fmt, "ocr.limit_side_len": $side}
               + (if $parser == "" then {} else {"tbpu.parser": $parser} end))}' \
    >"$WORK/req.json" || die "failed to build request" 1

RESP=$(curl -sS -m 120 -X POST "$BASE/api/ocr" -H 'Content-Type: application/json' \
    --data-binary @"$WORK/req.json") || die "OCR request failed (service dropped?)" 3

if [ "$RAW" = 1 ]; then
    printf '%s\n' "$RESP"
    exit 0
fi

CODE=$(printf '%s' "$RESP" | jq -r '.code // "null"')
case "$CODE" in
    100) ;;
    101) echo "(no text detected)"; exit 2 ;;
    *)   printf 'OCR failed: %s\n' "$(printf '%s' "$RESP" | jq -r '.data // "unknown error"')" >&2
         exit 3 ;;
esac

printf '%s' "$RESP" | jq -r --arg fmt "$FORMAT" --argjson scale "$SCALE" '
    if $fmt == "text" then .data
    else
        (.data | map(
            "\(.score * 100 | floor / 100)\t[\(.box[0][0] / $scale | floor),\(.box[0][1] / $scale | floor) \(.box[2][0] / $scale | floor),\(.box[2][1] / $scale | floor)]\t\(.text)"
        ) | join("\n"))
    end'
