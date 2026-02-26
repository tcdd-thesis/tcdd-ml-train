# Export trained model to NCNN format
#
import argparse
import importlib.util
import os
import sys

# ── Environment checks ───────────────────────────────────────────────────

def _check_venv() -> None:
    """Abort if no virtual environment is active."""
    in_venv = (
        sys.prefix != sys.base_prefix          # venv / virtualenv
        or os.environ.get("CONDA_DEFAULT_ENV") # conda
        or os.environ.get("VIRTUAL_ENV")       # explicitly set by some launchers
    )
    if not in_venv:
        sys.exit(
            "ERROR: No virtual environment is active.\n"
            "Activate one first, e.g.:\n"
            "  source .venv/bin/activate   # Linux/macOS\n"
            "  .venv\\Scripts\\Activate.ps1  # PowerShell"
        )


def _check_dependencies() -> None:
    """Abort with an actionable message if required packages are missing."""
    required = {
        "ultralytics": "pip install ultralytics",
    }
    missing = [
        (pkg, hint)
        for pkg, hint in required.items()
        if importlib.util.find_spec(pkg) is None
    ]
    if missing:
        lines = ["ERROR: Missing required package(s):"]
        for pkg, hint in missing:
            lines.append(f"  {pkg}  →  {hint}")
        sys.exit("\n".join(lines))


_check_venv()
_check_dependencies()

# ── Imports (after dependency check) ────────────────────────────────────
from ultralytics import YOLO

# ── Argument parsing / interactive mode ─────────────────────────────────
_DEFAULT_IMGSZ = 640


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a YOLO .pt model to NCNN format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m", "--model",
        metavar="PATH",
        help="Path to the source .pt model file (required)",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help="Destination directory for the exported NCNN files (optional; "
             "defaults to Ultralytics' auto-generated path next to the .pt file)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        metavar="N",
        help=f"Input image size (square) for the exported graph (default: {_DEFAULT_IMGSZ})",
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        default=True,
        help="Simplify the ONNX graph before NCNN conversion (default: True)",
    )
    parser.add_argument(
        "--no-simplify",
        action="store_true",
        help="Disable ONNX graph simplification",
    )
    return parser


def _interactive_prompt(args: argparse.Namespace) -> argparse.Namespace:
    """Fill in any missing values by prompting the user."""
    print("=== NCNN export — interactive mode ===\n")

    if args.model is None:
        val = input("Model .pt path: ").strip()
        if not val:
            sys.exit("ERROR: Model path is required.")
        args.model = val

    if args.imgsz is None:
        val = input(f"Image size [{_DEFAULT_IMGSZ}]: ").strip()
        try:
            args.imgsz = int(val) if val else _DEFAULT_IMGSZ
        except ValueError:
            sys.exit(f"ERROR: '{val}' is not a valid integer for image size.")

    if args.output is None:
        val = input("Output directory [auto]: ").strip()
        args.output = val or None

    return args


def _resolve_args() -> argparse.Namespace:
    parser = _build_parser()
    args = parser.parse_args()

    # Enter interactive mode when no arguments were given or the required
    # --model argument is missing (e.g. script run bare or with only flags).
    if len(sys.argv) == 1 or args.model is None:
        args = _interactive_prompt(args)

    # Require model path (catches interactive prompt that received empty input)
    if args.model is None:
        sys.exit("ERROR: Model path is required. Use -m/--model.")

    # Apply defaults for anything still unset
    if args.imgsz is None:
        args.imgsz = _DEFAULT_IMGSZ

    # Resolve --no-simplify flag
    if args.no_simplify:
        args.simplify = False

    # Validate model path
    if not os.path.isfile(args.model):
        sys.exit(f"ERROR: Model file not found: {args.model}")

    return args


# ── Export ───────────────────────────────────────────────────────────────
def main() -> None:
    args = _resolve_args()

    print(f"Model    : {args.model}")
    print(f"Imgsz    : {args.imgsz}")
    print(f"Simplify : {args.simplify}")
    if args.output:
        print(f"Output   : {args.output}")
    print()

    os.environ['NCNN_SIMPLIFIED'] = '1'

    export_model = YOLO(args.model)
    result = export_model.export(
        format="ncnn",
        imgsz=args.imgsz,
        simplify=args.simplify,
    )

    # Optionally move to the user-specified output directory
    if args.output and result and os.path.abspath(result) != os.path.abspath(args.output):
        import shutil
        os.makedirs(args.output, exist_ok=True)
        if os.path.isdir(result):
            # NCNN export produces a directory — move its contents
            for item in os.listdir(result):
                shutil.move(os.path.join(result, item), os.path.join(args.output, item))
            os.rmdir(result)
        else:
            shutil.move(result, args.output)
        result = args.output

    print(f"\nNCNN saved to: {result}")


if __name__ == "__main__":
    main()
