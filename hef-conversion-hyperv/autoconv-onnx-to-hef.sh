#!/usr/bin/env bash
# =============================================================================
# convert_onnx_to_hef.sh
# Automates the ONNX → HEF conversion pipeline using Hailo AI SW Suite.
# Run this script directly on the Ubuntu conversion VM.
#
# Usage:
#   ./convert_onnx_to_hef.sh [OPTIONS]
#
# Options:
#   -m, --model        Path to the .onnx model file                  (required)
#   -d, --dataset      Path to dataset root folder containing images  (required)
#   -o, --output       Output directory for the .hef file            (default: ./output)
#   -c, --classes      Number of classes (auto-derived from data.yaml if omitted)
#   -a, --arch         Hailo HW architecture target                  (default: hailo8l)
#   -n, --name         Hailo Model Zoo model config name             (default: yolov11n)
#   -i, --images       Max calibration images to use                 (default: 100)
#   -w, --workdir      Shared host↔container working directory       (default: <script_dir>/shared_with_docker)
#       --keep-calib   Do NOT delete staged calib images after compile
#   -h, --help         Show this help message
#
# Examples:
#   # Minimal — prompts for required values
#   ./convert_onnx_to_hef.sh
#
#   # Fully scripted
#   ./convert_onnx_to_hef.sh \
#       --model   /home/ubuntu/models/best.onnx \
#       --dataset /home/ubuntu/datasets/merged-ph-tcd-1 \
#       --output  /home/ubuntu/models/hef
#
#   # Override auto-detected class count
#   ./convert_onnx_to_hef.sh \
#       --model   /home/ubuntu/models/best.onnx \
#       --dataset /home/ubuntu/datasets/merged-ph-tcd-1 \
#       --classes 3
# =============================================================================

set -euo pipefail

# Resolve the directory this script lives in (works with symlinks)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Defaults ────────────────────────────────────────────────────────────────
ONNX_PATH=""
DATASET_DIR=""
OUTPUT_DIR="./output"
CLASSES=""          # empty = auto-detect from data.yaml
CLASSES_SOURCE=""  # tracks where the value came from
HW_ARCH="hailo8l"
MODEL_NAME="yolov11n"
MAX_CALIB=100
WORK_DIR="${SCRIPT_DIR}/shared_with_docker"
KEEP_CALIB=false

CONTAINER_NAME="hailo_conversion"
HAILO_IMAGE="hailo8_ai_sw_suite_2025-10:1"
HAILO_TAR_GLOB="${SCRIPT_DIR}/hailo8_ai_sw_suite*.tar.gz"

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

step()    { echo -e "\n${CYAN}==>${RESET} ${BOLD}$*${RESET}"; }
ok()      { echo -e "  ${GREEN}[OK]${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}[!!]${RESET} $*"; }
die()     { echo -e "\n${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ─── Argument Parsing ────────────────────────────────────────────────────────
usage() {
    grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \{0,2\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--model)       ONNX_PATH="$2";   shift 2 ;;
        -d|--dataset)     DATASET_DIR="$2"; shift 2 ;;
        -o|--output)      OUTPUT_DIR="$2";  shift 2 ;;
        -c|--classes)     CLASSES="$2"; CLASSES_SOURCE="--classes flag"; shift 2 ;;
        -a|--arch)        HW_ARCH="$2";     shift 2 ;;
        -n|--name)        MODEL_NAME="$2";  shift 2 ;;
        -i|--images)      MAX_CALIB="$2";   shift 2 ;;
        -w|--workdir)     WORK_DIR="$2";    shift 2 ;;
        --keep-calib)     KEEP_CALIB=true;  shift   ;;
        -h|--help)        usage ;;
        *) die "Unknown option: $1. Use --help for usage." ;;
    esac
done

# Expand tilde in WORK_DIR in case it was passed as a literal string
WORK_DIR="${WORK_DIR/#\~/$HOME}"

# ─── Interactive Prompts for Missing Required Values ─────────────────────────
prompt_if_empty() {
    local -n _var=$1
    local label="$2"
    local default="${3:-}"
    if [[ -z "${_var}" ]]; then
        if [[ -n "$default" ]]; then
            read -rp "${label} [default: ${default}]: " _input
            _var="${_input:-$default}"
        else
            while [[ -z "${_var}" ]]; do
                read -rp "${label}: " _var
            done
        fi
    fi
}

prompt_if_empty ONNX_PATH    "Path to .onnx model file"
prompt_if_empty DATASET_DIR  "Path to dataset root folder (must contain images)"

# ─── Validate Inputs ─────────────────────────────────────────────────────────
[[ -f "$ONNX_PATH" ]]      || die "ONNX file not found: $ONNX_PATH"
[[ -d "$DATASET_DIR" ]]    || die "Dataset directory not found: $DATASET_DIR"
command -v docker &>/dev/null || die "'docker' is not installed or not in PATH"

ONNX_FILENAME="$(basename "$ONNX_PATH")"
CALIB_DIR="${WORK_DIR}/calib_images"

# ─── Derive Class Count from data.yaml ───────────────────────────────────────
if [[ -z "$CLASSES" ]]; then
    step "Reading class count from dataset YAML"

    # Look for data.yaml or dataset.yaml in the dataset root
    YAML_FILE=""
    for candidate in "${DATASET_DIR}/data.yaml" "${DATASET_DIR}/dataset.yaml"; do
        if [[ -f "$candidate" ]]; then
            YAML_FILE="$candidate"
            break
        fi
    done

    [[ -z "$YAML_FILE" ]] && die "No data.yaml or dataset.yaml found in: ${DATASET_DIR}\n       Pass --classes manually or place a YOLO data.yaml at the dataset root."

    # Parse the 'nc' field — handles both 'nc: 3' and 'nc:3'
    NC_VALUE="$(grep -E '^nc[[:space:]]*:' "$YAML_FILE" | head -1 | awk -F: '{print $2}' | tr -d ' \t')"

    [[ -z "$NC_VALUE" ]] && die "Could not find 'nc' field in: ${YAML_FILE}"
    [[ "$NC_VALUE" =~ ^[0-9]+$ ]] || die "'nc' value '${NC_VALUE}' in ${YAML_FILE} is not a valid integer."

    CLASSES="$NC_VALUE"
    CLASSES_SOURCE="${YAML_FILE} (nc: ${NC_VALUE})"
    ok "Detected ${CLASSES} class(es) from: ${YAML_FILE}"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       Hailo ONNX → HEF Conversion Automation        ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ONNX model    : ${ONNX_PATH}"
echo -e "  Dataset root  : ${DATASET_DIR}"
echo -e "  Output dir    : ${OUTPUT_DIR}"
echo -e "  Model name    : ${MODEL_NAME}"
echo -e "  Classes       : ${CLASSES}  (source: ${CLASSES_SOURCE})"
echo -e "  HW arch       : ${HW_ARCH}"
echo -e "  Max calib imgs: ${MAX_CALIB}"
echo -e "  Shared workdir: ${WORK_DIR}"
echo ""
read -rp "Proceed? [Y/n]: " _confirm
[[ "${_confirm,,}" =~ ^n ]] && { echo "Aborted."; exit 0; }

# ─── Step 1: Sample Calibration Images ───────────────────────────────────────
step "Collecting calibration images from dataset"

# Search recursively for PNG/JPG images
mapfile -d '' ALL_IMAGES < <(find "$DATASET_DIR" \
    -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \) \
    -print0)

TOTAL_IMAGES=${#ALL_IMAGES[@]}
[[ $TOTAL_IMAGES -eq 0 ]] && die "No PNG/JPG images found under: $DATASET_DIR"

if [[ $TOTAL_IMAGES -le $MAX_CALIB ]]; then
    SELECTED_IMAGES=("${ALL_IMAGES[@]}")
    ok "Using all ${TOTAL_IMAGES} images for calibration."
else
    warn "Found ${TOTAL_IMAGES} images. Randomly selecting ${MAX_CALIB}."
    # Shuffle using shuf and pick top N
    mapfile -d '' SELECTED_IMAGES < <(
        printf '%s\0' "${ALL_IMAGES[@]}" | shuf -z -n "$MAX_CALIB"
    )
fi

# ─── Step 2: Stage Calibration Images into Shared Workdir ────────────────────
step "Staging calibration images into shared workdir"

mkdir -p "$CALIB_DIR"
chmod 777 "$CALIB_DIR"

for img in "${SELECTED_IMAGES[@]}"; do
    cp "$img" "$CALIB_DIR/"
done
chmod 666 "$CALIB_DIR"/*

ok "Staged ${#SELECTED_IMAGES[@]} images to: $CALIB_DIR"

# ─── Step 3: Copy ONNX Model into Shared Workdir ─────────────────────────────
step "Copying ONNX model into shared workdir"

cp "$ONNX_PATH" "${WORK_DIR}/${ONNX_FILENAME}"
ok "Copied: ${ONNX_FILENAME} → ${WORK_DIR}/"

# ─── Step 4: Ensure Hailo Docker Container is Running ────────────────────────
step "Checking Hailo Docker container state"

CONTAINER_STATUS="$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "missing")"

case "$CONTAINER_STATUS" in
    running)
        ok "Container '${CONTAINER_NAME}' is already running."
        ;;
    exited|created|paused)
        warn "Container '${CONTAINER_NAME}' exists but is stopped. Starting it..."
        docker start "$CONTAINER_NAME"
        ok "Container started."
        ;;
    missing)
        warn "No existing container found. Creating '${CONTAINER_NAME}'..."

        # Load Docker image if not already loaded
        if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -qF "${HAILO_IMAGE}"; then
            step "Loading Hailo Docker image (this can take 15-45 minutes)..."
            TAR_FILE="$(ls ${HAILO_TAR_GLOB} 2>/dev/null | head -1)"
            [[ -z "$TAR_FILE" ]] && die "Hailo Docker image .tar.gz not found. Expected pattern: ${HAILO_TAR_GLOB}"
            docker load < "$TAR_FILE"
            ok "Docker image loaded: ${HAILO_IMAGE}"
        else
            ok "Docker image already loaded: ${HAILO_IMAGE}"
        fi

        # Create a detached container with the shared volume mounted
        docker run -d \
            --name "$CONTAINER_NAME" \
            -v "${WORK_DIR}:/local/shared_with_docker" \
            "$HAILO_IMAGE" \
            sleep infinity
        ok "Container '${CONTAINER_NAME}' created and running."
        ;;
    *)
        die "Unexpected container state: '${CONTAINER_STATUS}'"
        ;;
esac

# Verify the shared volume is mounted in the container
MOUNT_CHECK="$(docker inspect --format='{{range .Mounts}}{{.Source}} → {{.Destination}}{{"\n"}}{{end}}' "$CONTAINER_NAME" 2>/dev/null)"
if ! echo "$MOUNT_CHECK" | grep -qF "/local/shared_with_docker"; then
    warn "Shared volume not mounted in running container."
    warn "The container may have been created without the volume. Recreating..."
    docker stop "$CONTAINER_NAME"
    docker rm   "$CONTAINER_NAME"
    docker run -d \
        --name "$CONTAINER_NAME" \
        -v "${WORK_DIR}:/local/shared_with_docker" \
        "$HAILO_IMAGE" \
        sleep infinity
    ok "Container recreated with correct volume mapping."
fi

# ─── Step 5: Run hailomz compile ─────────────────────────────────────────────
step "Running hailomz compile inside Hailo container"
echo ""
echo -e "  Model  : ${MODEL_NAME}"
echo -e "  ONNX   : /local/shared_with_docker/${ONNX_FILENAME}"
echo -e "  Calib  : /local/shared_with_docker/calib_images/"
echo -e "  Target : ${HW_ARCH} — ${CLASSES} class(es)"
echo ""
warn "This step typically takes 20-40 minutes on CPU. Output streams below."
echo ""

docker exec "$CONTAINER_NAME" bash -c "
    source /hailo_virtualenv/bin/activate 2>/dev/null || true
    cd /local/shared_with_docker
    hailomz compile '${MODEL_NAME}' \
        --ckpt '/local/shared_with_docker/${ONNX_FILENAME}' \
        --hw-arch '${HW_ARCH}' \
        --calib-path '/local/shared_with_docker/calib_images/' \
        --classes '${CLASSES}'
"

ok "hailomz compile finished successfully!"

# ─── Step 6: Copy HEF to Output Directory ────────────────────────────────────
step "Saving .hef file to output directory"

HEF_IN_WORKDIR="${WORK_DIR}/${MODEL_NAME}.hef"
[[ -f "$HEF_IN_WORKDIR" ]] || die ".hef file not found at expected location: ${HEF_IN_WORKDIR}"

mkdir -p "$OUTPUT_DIR"
HEF_OUTPUT="${OUTPUT_DIR}/${MODEL_NAME}.hef"
cp "$HEF_IN_WORKDIR" "$HEF_OUTPUT"
ok "HEF saved: ${HEF_OUTPUT}"

# ─── Step 7: Optional Cleanup ────────────────────────────────────────────────
if [[ "$KEEP_CALIB" == false ]]; then
    step "Removing staged calibration images from shared workdir"
    rm -rf "$CALIB_DIR"
    ok "Cleaned up: ${CALIB_DIR}"
fi

# ─── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║                  Conversion Complete!               ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  HEF file: ${BOLD}${HEF_OUTPUT}${RESET}"
echo ""
echo -e "${CYAN}Next steps:${RESET}"
echo "  Transfer the HEF to your Raspberry Pi:"
echo "    scp \"${HEF_OUTPUT}\" pi@<PI_IP>:/home/pi/<project>/models/"
echo ""
