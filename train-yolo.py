#!/usr/bin/env python3
"""
YOLO Training Script - train-yolo.py
=======================================
Supports both CLI arguments and interactive prompts.
Requires an active virtual environment with ultralytics installed.

Usage examples:
    # Activate your venv first, then run:
    python train-yolo.py

    # Fully specified
    python train-yolo.py -d datasets/merged-ph-tcd-1-bbox -m yolo11n.pt -e 100 -b 16

    # Partial — missing args are prompted interactively
    python train-yolo.py --epochs 50 --model yolo11n.pt
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────

def _banner(title: str) -> str:
    width = 50
    return (
        f"\n{'═' * width}\n"
        f"  {title}\n"
        f"{'═' * width}"
    )


def _prompt(label: str, default: str | None = None, validator=None) -> str:
    """Prompt the user for input with an optional default and validator."""
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"  {label}{suffix}: ").strip()
        if not value and default is not None:
            value = default
        if not value:
            print("    [!] A value is required.")
            continue
        if validator:
            err = validator(value)
            if err:
                print(f"    [!] {err}")
                continue
        return value


def _prompt_int(label: str, default: int | None = None, min_val: int = 1) -> int:
    """Prompt for a positive integer."""
    def _validate(v):
        try:
            n = int(v)
            if n < min_val:
                return f"Must be >= {min_val}."
        except ValueError:
            return "Enter a valid integer."
        return None
    return int(_prompt(label, str(default) if default else None, _validate))


def _confirm(message: str = "Proceed?", default_yes: bool = True) -> bool:
    hint = "Y/n" if default_yes else "y/N"
    answer = input(f"  {message} [{hint}]: ").strip().lower()
    if not answer:
        return default_yes
    return answer in ("y", "yes")


# ──────────────────────────────────────────────────────────────────────
#  Venv & environment checks
# ──────────────────────────────────────────────────────────────────────

def _check_active_venv() -> None:
    """Ensure the script is running inside an activated virtual environment."""
    if sys.prefix == sys.base_prefix:
        print("  [ERR] No virtual environment detected.")
        print("        Please activate your venv before running this script.")
        print("        Example: .venv.ml\\Scripts\\activate  (Windows)")
        print("                 source .venv.ml/bin/activate (Linux/Mac)")
        sys.exit(1)
    print(f"  [OK] Venv active: {sys.prefix}")


def _ensure_packages() -> None:
    """Check that required packages are importable in the active venv."""
    print("  Checking for required packages...")

    required = ["ultralytics"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        print("  [OK] All required packages are installed.")
        return

    print(f"  [!] Missing packages: {', '.join(missing)}")
    if _confirm("Install missing packages now?"):
        # Try pip, then uv, then python -m pip
        py = sys.executable
        methods = [
            ("pip",           ["pip", "install"] + missing),
            ("uv",            ["uv", "pip", "install"] + missing),
            ("python -m pip", [py, "-m", "pip", "install"] + missing),
        ]
        for label, cmd in methods:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  [OK] Packages installed successfully (via {label}).")
                    return
            except FileNotFoundError:
                pass
        print("  [ERR] All install methods failed. Try manually:")
        print(f"        pip install {' '.join(missing)}")
        print(f"    or: uv pip install {' '.join(missing)}")
        sys.exit(1)
    else:
        print("  [ERR] Cannot proceed without required packages.")
        sys.exit(1)


def _check_cuda() -> dict:
    """Check CUDA availability in the active environment. Returns GPU info dict."""
    try:
        import torch
        return {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "devices": [
                torch.cuda.get_device_name(i)
                for i in range(torch.cuda.device_count())
            ] if torch.cuda.is_available() else [],
        }
    except ImportError:
        return {"available": False, "count": 0, "devices": []}


# ──────────────────────────────────────────────────────────────────────
#  Dataset validation
# ──────────────────────────────────────────────────────────────────────

def _validate_dataset(data_root: str) -> str | None:
    """Validator for dataset root path."""
    root = Path(data_root)
    if not root.is_dir():
        return f"Directory not found: {root}"
    yaml_path = root / "data.yaml"
    if not yaml_path.exists():
        return f"data.yaml not found in {root}"
    return None


def _check_dataset_splits(data_root: Path) -> None:
    """Print warnings about missing splits (non-fatal)."""
    import yaml  # only needed here

    yaml_path = data_root / "data.yaml"
    with open(yaml_path) as f:
        cfg = yaml.safe_load(f)

    print(f"\n  Dataset: {data_root}")
    print(f"     Classes: {len(cfg.get('names', {}))} defined")

    for key in ("train", "val", "test"):
        if key in cfg:
            split_path = data_root / cfg[key]
            status = "[OK]" if split_path.exists() else "[!] (path missing)"
            print(f"     {key:>5}: {cfg[key]}  {status}")
        else:
            level = "[!]" if key == "test" else "[ERR]"
            print(f"     {key:>5}: {level} not defined in data.yaml")
            if key != "test":
                print("    [ERR] Fatal: 'train' and 'val' splits are required.")
                sys.exit(1)


# ──────────────────────────────────────────────────────────────────────
#  Argument parsing
# ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Robust & Flexible YOLO Training Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python train-yolo.py
              python train-yolo.py -d datasets/merged-ph-tcd-1-bbox -m yolo11n.pt -e 100 -b 16
              python train-yolo.py --epochs 50 --model yolo11n.pt
        """),
    )
    p.add_argument("-d", "--data", type=str, help="Path to YOLO dataset root directory (must contain data.yaml)")
    p.add_argument("-m", "--model", type=str, help="YOLO model name or path (e.g. yolo11n.pt, yolov8s.pt)")
    p.add_argument("-e", "--epochs", type=int, help="Number of training epochs")
    p.add_argument("-b", "--batch", type=int, help="Batch size")
    p.add_argument("-i", "--imgsz", type=int, help="Image size (default: 640)")
    p.add_argument("-o", "--output", type=str, help="Output project directory (default: runs)")
    p.add_argument("-n", "--name", type=str, help="Run name inside output directory")
    p.add_argument("-D", "--device", type=str, help="Device: 'auto', 'cpu', '0', '0,1', etc. (default: auto)")
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────
#  Interactive collection of missing arguments
# ──────────────────────────────────────────────────────────────────────

def collect_config(args: argparse.Namespace) -> dict:
    """Merge CLI args with interactively prompted values for anything missing."""
    cfg = {}

    print(_banner("YOLO Training Script — Configuration"))

    # ── Dataset ───────────────────────────────────────────────────────
    if args.data:
        err = _validate_dataset(args.data)
        if err:
            print(f"  [ERR] {err}")
            sys.exit(1)
        cfg["data"] = args.data
    else:
        print("\n  Specify the YOLO dataset root directory.")
        print("  It must contain a data.yaml file plus train/valid/test splits.")
        cfg["data"] = _prompt("Dataset root", None, _validate_dataset)

    # ── Model ─────────────────────────────────────────────────────────
    if args.model:
        cfg["model"] = args.model
    else:
        print("\n  Specify the YOLO model to use (name or .pt path).")
        print("  Examples: yolov8n.pt, yolov8s.pt, yolo11n.pt, yolov9c.pt")
        print("  Ultralytics will auto-download the model if not found locally.")
        cfg["model"] = _prompt("Model", "yolo11n.pt")

    # ── Epochs ────────────────────────────────────────────────────────
    if args.epochs:
        cfg["epochs"] = args.epochs
    else:
        cfg["epochs"] = _prompt_int("Epochs", default=100, min_val=1)

    # ── Batch size ────────────────────────────────────────────────────
    if args.batch:
        cfg["batch"] = args.batch
    else:
        cfg["batch"] = _prompt_int("Batch size", default=16, min_val=1)

    # ── Image size ────────────────────────────────────────────────────
    if args.imgsz:
        cfg["imgsz"] = args.imgsz
    else:
        cfg["imgsz"] = _prompt_int("Image size", default=640, min_val=32)

    # ── Output & name ─────────────────────────────────────────────────
    cfg["output"] = args.output or _prompt("Output dir", "runs")
    cfg["name"] = args.name or _prompt("Run name", "exp")

    # ── Device ────────────────────────────────────────────────────────
    if args.device:
        cfg["device"] = args.device
    else:
        gpu_info = _check_cuda()
        print()
        if gpu_info["available"]:
            for i, name in enumerate(gpu_info["devices"]):
                print(f"  [OK] GPU {i}: {name}")
            print("  Options: 'auto' (use GPU), 'cpu', '0', '0,1' (multi-GPU), etc.")
        else:
            print("  [!] CUDA not available — only CPU training is possible.")
            print("      To enable GPU, install PyTorch with CUDA support in your venv.")
        default_device = "auto" if gpu_info["available"] else "cpu"
        cfg["device"] = _prompt("Device", default_device)

    return cfg


# ──────────────────────────────────────────────────────────────────────
#  Summary banner
# ──────────────────────────────────────────────────────────────────────

def print_summary(cfg: dict) -> None:
    w = 52
    print()
    print(f"  ╔{'═' * w}╗")
    print(f"  ║{'YOLO Training Configuration':^{w}}║")
    print(f"  ╠{'═' * w}╣")
    rows = [
        ("Model",    cfg["model"]),
        ("Dataset",  cfg["data"]),
        ("Epochs",   str(cfg["epochs"])),
        ("Batch",    str(cfg["batch"])),
        ("Img Size", str(cfg["imgsz"])),
        ("Output",   cfg["output"]),
        ("Name",     cfg["name"]),
        ("Device",   cfg["device"]),
        ("Venv",     sys.prefix),
    ]
    for label, value in rows:
        content = f"  {label + ':':<11} {value}"
        print(f"  ║{content:<{w}}║")
    print(f"  ╚{'═' * w}╝")


# ──────────────────────────────────────────────────────────────────────
#  Training
# ──────────────────────────────────────────────────────────────────────

def train(cfg: dict) -> None:
    """Run YOLO training with the given configuration."""
    from ultralytics import YOLO

    data_root = Path(cfg["data"]).resolve()
    data_yaml = str(data_root / "data.yaml")

    print(f"\n  Loading model: {cfg['model']}")
    model = YOLO(cfg["model"])

    # Resolve device for ultralytics
    device = None if cfg["device"] == "auto" else cfg["device"]

    print(f"  Starting training (device={cfg['device']})...\n")
    train_kwargs = dict(
        data=data_yaml,
        epochs=cfg["epochs"],
        imgsz=cfg["imgsz"],
        batch=cfg["batch"],
        project=cfg["output"],
        name=cfg["name"],
    )
    if device is not None:
        train_kwargs["device"] = device

    results = model.train(**train_kwargs)

    print(_banner("Training Complete"))
    print(f"  Results saved to: {cfg['output']}/{cfg['name']}")
    return results


# ──────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Ensure we're in a venv
    _check_active_venv()

    # 2. Parse args
    args = parse_args()

    # 3. Ensure required packages are installed
    _ensure_packages()

    # 4. Collect all configuration (CLI + interactive fallback)
    cfg = collect_config(args)

    # 5. Validate dataset
    _check_dataset_splits(Path(cfg["data"]))

    # 6. Show summary and confirm
    print_summary(cfg)
    if not _confirm("\n  Start training?"):
        print("  Aborted.")
        sys.exit(0)

    # 7. Train
    train(cfg)


if __name__ == "__main__":
    main()