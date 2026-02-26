# Export trained model to ONNX for Hailo conversion
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
        "onnx":        "pip install onnx",
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
from ultralytics.nn.modules.head import Detect

# ── Argument parsing / interactive mode ─────────────────────────────────
_DEFAULT_IMGSZ = 640
_HAILO_OPSET   = 11  # fixed — do not raise; Hailo is validated on opset 11

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a YOLOv8 .pt model to ONNX. Use --pre-hef for Hailo/HEF-compatible output (opset 11, raw conv outputs).",
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
        help="Destination path for the exported .onnx file (optional; "
             "defaults to Ultralytics' auto-generated path next to the .pt file)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        metavar="N",
        help=f"Input image size (square) for the exported graph (default: {_DEFAULT_IMGSZ})",
    )

    # TWO KEY REQUIREMENTS for Hailo compatibility:
    #
    # 1. opset=11 — Hailo Model Zoo is validated against opset 11.
    #    Higher opsets (e.g. the default opset 22) cause shape inference
    #    failures that lead to quantization errors.
    #
    # 2. Raw conv outputs — Hailo's yolov8n.alls NMS postprocessing expects
    #    the ONNX graph to end at convolution layers (per-scale box + cls
    #    predictions), NOT at the Detect head's Concat/Sigmoid nodes.
    #    The default Ultralytics export concatenates the outputs, which causes:
    #      AllocatorScriptParserException: expected conv but found concat layer
    #    We fix this by monkey-patching Detect.forward at the CLASS level
    #    (survives Ultralytics' internal deepcopy) to return the 6 individual
    #    conv outputs: [box_p3, cls_p3, box_p4, cls_p4, box_p5, cls_p5].

    parser.add_argument(
        "--pre-hef",
        action="store_true",
        help=(
            f"Enable Hailo/HEF conversion compatibility: forces opset {_HAILO_OPSET}, "
            "static input shape, and raw conv outputs (monkey-patches Detect.forward). "
            "Without this flag the standard Ultralytics ONNX defaults are used."
        ),
    )
    return parser


def _interactive_prompt(args: argparse.Namespace) -> argparse.Namespace:
    """Fill in any missing values by prompting the user."""
    print("=== ONNX export — interactive mode ===")

    if not args.pre_hef:
        val = input("Enable Hailo/HEF compatibility mode? (forces opset 11 + raw conv outputs) [y/N]: ").strip().lower()
        args.pre_hef = val in ("y", "yes")

    if args.pre_hef:
        print(f"  Hailo mode ON — opset fixed at {_HAILO_OPSET}, raw conv outputs enabled.\n")
    else:
        print("  Standard ONNX export (Ultralytics defaults).\n")

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
        val = input("Output .onnx path [auto]: ").strip()
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

    # Validate model path
    if not os.path.isfile(args.model):
        sys.exit(f"ERROR: Model file not found: {args.model}")

    return args


# ── Hailo Detect-head patch ─────────────────────────────────────────────
def _hailo_detect_forward(self, x):
    """Return per-scale raw conv outputs for Hailo NMS compatibility.

    Instead of concatenating box+cls and decoding, output the 6 individual
    conv tensors that Hailo's NMS postprocess command expects to find.

    Supports both legacy (v8/v9/v11) models that use cv2/cv3, and newer
    end-to-end models (e.g. YOLO26) that use one2one_cv2/one2one_cv3.
    """
    # Newer end-to-end architectures (YOLO26, etc.) may set cv2/cv3 to None
    # and use one2one_cv2/one2one_cv3 as the primary heads instead.
    box_head = self.cv2 if self.cv2 is not None else getattr(self, "one2one_cv2", None)
    cls_head = self.cv3 if self.cv3 is not None else getattr(self, "one2one_cv3", None)

    if box_head is None or cls_head is None:
        raise RuntimeError(
            "Detect head has neither cv2/cv3 nor one2one_cv2/one2one_cv3. "
            "This model architecture is not supported for Hailo export."
        )

    outputs = []
    for i in range(self.nl):          # nl = number of detection scales (3)
        outputs.append(box_head[i](x[i]))  # bbox regression conv
        outputs.append(cls_head[i](x[i]))  # classification conv
    return tuple(outputs)


# ── Export ───────────────────────────────────────────────────────────────
def main() -> None:
    args = _resolve_args()

    print(f"Model   : {args.model}")
    print(f"Imgsz   : {args.imgsz}")
    if args.pre_hef:
        print(f"Opset   : {_HAILO_OPSET} (fixed — Hailo mode)")
        print("Hailo   : ON (opset 11, raw conv outputs, static shape)")
    else:
        print("Hailo   : OFF (standard Ultralytics ONNX defaults)")
    if args.output:
        print(f"Output  : {args.output}")
    print()

    export_kwargs: dict = dict(
        format="onnx",
        imgsz=args.imgsz,
    )

    if args.pre_hef:
        # Apply Detect patch at CLASS level — Ultralytics deepcopies the model
        # during export, so an instance-level patch would be lost.
        _original_detect_forward = Detect.forward
        Detect.forward = _hailo_detect_forward
        export_kwargs["opset"]   = _HAILO_OPSET  # Hailo-validated — do not raise
        export_kwargs["dynamic"] = False          # static shape required by Hailo

    export_model = YOLO(args.model)
    onnx_path = export_model.export(**export_kwargs)

    if args.pre_hef:
        # Restore original forward so the module stays usable for other callers
        Detect.forward = _original_detect_forward

    # Optionally rename/move to the user-specified output path
    if args.output and onnx_path and os.path.abspath(onnx_path) != os.path.abspath(args.output):
        import shutil
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        shutil.move(onnx_path, args.output)
        onnx_path = args.output

    print(f"\nONNX saved to: {onnx_path}")


if __name__ == "__main__":
    main()