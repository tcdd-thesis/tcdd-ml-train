#!/usr/bin/env python3
"""
Three-way YOLO dataset format converter.

Converts all labels in a YOLOv8 dataset to one of three formats:

  bbox      Standard bounding boxes:          class xc yc w h                    (5 fields)
  obb       Oriented bounding boxes:          class x1 y1 x2 y2 x3 y3 x4 y4    (9 fields)
  segment   Instance segmentation polygons:   class x1 y1 x2 y2 ... xN yN      (7+ fields)

bbox → segment uses ultralytics.data.converter.yolo_bbox2segment (SAM auto-annotator).
All other conversions are purely mathematical.

Labels already in the target format are skipped.

Usage:
    python conv-yolo-dataset.py                                    # interactive
    python conv-yolo-dataset.py path/to/dataset --to bbox
    python conv-yolo-dataset.py path/to/dataset --to obb
    python conv-yolo-dataset.py path/to/dataset --to segment
    python conv-yolo-dataset.py path/to/dataset --to segment --sam-model sam_l.pt --device cuda:0
    python conv-yolo-dataset.py path/to/dataset --to bbox --remove       # delete non-bbox files instead of converting

Back up your dataset before running this script — conversions are in-place.
"""

import argparse
import shutil
import sys
from pathlib import Path

SPLITS = ("train", "valid", "test")
FORMAT_CHOICES = ("bbox", "obb", "segment")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


# ═══════════════════════════════════════════════════════════════════════════════
#  Format detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_line_format(fields: list[str]) -> str:
    """Classify a single annotation line by its field count.

    Returns 'bbox', 'obb', 'segment', or 'unknown'.
    Note: 9 fields is classified as 'obb'. If used as a 4-vertex polygon
    for segmentation, it is equally valid — handled contextually.
    """
    n = len(fields)
    if n == 5:
        return "bbox"
    elif n == 9:
        return "obb"
    elif n >= 7 and n % 2 == 1:
        return "segment"
    return "unknown"


def scan_dataset(root: Path) -> tuple[int, dict[str, int]]:
    """Count annotation lines by format across the entire dataset.

    Returns (total_files, {format: line_count}).
    """
    stats: dict[str, int] = {"bbox": 0, "obb": 0, "segment": 0, "unknown": 0}
    file_count = 0
    for split in SPLITS:
        label_dir = root / split / "labels"
        if not label_dir.exists():
            continue
        for txt in label_dir.glob("*.txt"):
            file_count += 1
            with open(txt) as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    fmt = detect_line_format(s.split())
                    stats[fmt] += 1
    return file_count, stats


def print_scan(file_count: int, stats: dict[str, int]) -> None:
    total = sum(stats.values())
    print(f"  Label files : {file_count}")
    print(f"  Total lines : {total}")
    print(f"    bbox      : {stats['bbox']:>6}")
    print(f"    obb       : {stats['obb']:>6}")
    print(f"    segment   : {stats['segment']:>6}")
    if stats["unknown"]:
        print(f"    unknown   : {stats['unknown']:>6}  (will be left unchanged)")
    formats_present = [k for k in ("bbox", "obb", "segment") if stats[k] > 0]
    if len(formats_present) > 1:
        print(f"  ⚠  Mixed formats detected: {', '.join(formats_present)}")
    elif formats_present:
        print(f"  Format: {formats_present[0]} (uniform)")


# ═══════════════════════════════════════════════════════════════════════════════
#  Mathematical helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float]:
    """Polygon/OBB coords → axis-aligned bbox (xc, yc, w, h)."""
    xs = coords[0::2]
    ys = coords[1::2]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xc = (xmin + xmax) / 2
    yc = (ymin + ymax) / 2
    return xc, yc, xmax - xmin, ymax - ymin


def _bbox_to_corners(xc: float, yc: float, w: float, h: float) -> list[float]:
    """Axis-aligned bbox → 4 corner points (TL, TR, BR, BL)."""
    x1, x2 = xc - w / 2, xc + w / 2
    y1, y2 = yc - h / 2, yc + h / 2
    return [x1, y1, x2, y1, x2, y2, x1, y2]


def _segment_to_obb(coords: list[float]) -> list[float]:
    """Polygon coords → minimum-area oriented bounding box (4 corners).

    Uses OpenCV minAreaRect when available; falls back to axis-aligned corners.
    """
    try:
        import cv2
        import numpy as np
        pts = np.array(coords, dtype=np.float32).reshape(-1, 2)
        # Scale up for numerical precision with normalised coords (0–1 range)
        scale = 100_000.0
        rect = cv2.minAreaRect((pts * scale).astype(np.float32))
        box = cv2.boxPoints(rect) / scale
        return box.flatten().tolist()
    except ImportError:
        # Fallback: axis-aligned bbox corners
        xc, yc, w, h = _polygon_to_bbox(coords)
        return _bbox_to_corners(xc, yc, w, h)


def _fmt(v: float) -> str:
    """Format a coordinate value, keeping precision but stripping trailing zeros."""
    return f"{v:.6f}".rstrip("0").rstrip(".")


# ═══════════════════════════════════════════════════════════════════════════════
#  Line converters  (return None when the line is already in target format)
# ═══════════════════════════════════════════════════════════════════════════════

def _line_to_bbox(fields: list[str]) -> str | None:
    fmt = detect_line_format(fields)
    if fmt == "bbox":
        return None  # already correct
    if fmt in ("obb", "segment"):
        cid = fields[0]
        coords = [float(v) for v in fields[1:]]
        xc, yc, w, h = _polygon_to_bbox(coords)
        return f"{cid} {_fmt(xc)} {_fmt(yc)} {_fmt(w)} {_fmt(h)}"
    return None  # unknown → leave as-is


def _line_to_obb(fields: list[str]) -> str | None:
    fmt = detect_line_format(fields)
    if fmt == "obb":
        return None  # already correct
    cid = fields[0]
    if fmt == "bbox":
        xc, yc, w, h = (float(v) for v in fields[1:5])
        corners = _bbox_to_corners(xc, yc, w, h)
    elif fmt == "segment":
        coords = [float(v) for v in fields[1:]]
        corners = _segment_to_obb(coords)
    else:
        return None  # unknown → leave as-is
    return cid + " " + " ".join(_fmt(c) for c in corners)


# ═══════════════════════════════════════════════════════════════════════════════
#  File-level math converter
# ═══════════════════════════════════════════════════════════════════════════════

def _convert_file_math(filepath: Path, line_fn) -> tuple[int, int]:
    """Apply a line converter to every line in a label file.

    Returns (converted, skipped).
    """
    converted = 0
    skipped = 0
    new_lines: list[str] = []

    with open(filepath) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            fields = s.split()
            result = line_fn(fields)
            if result is None:
                new_lines.append(s)
                skipped += 1
            else:
                new_lines.append(result)
                converted += 1

    with open(filepath, "w") as f:
        f.write("\n".join(new_lines))
        if new_lines:
            f.write("\n")

    return converted, skipped


# ═══════════════════════════════════════════════════════════════════════════════
#  Conversion drivers
# ═══════════════════════════════════════════════════════════════════════════════

def convert_to_bbox(root: Path) -> tuple[int, int]:
    """Convert all annotations to standard bounding boxes (math only)."""
    total_conv, total_skip = 0, 0
    for split in SPLITS:
        label_dir = root / split / "labels"
        if not label_dir.exists():
            continue
        split_conv, split_skip = 0, 0
        for f in sorted(label_dir.glob("*.txt")):
            c, s = _convert_file_math(f, _line_to_bbox)
            split_conv += c
            split_skip += s
        print(f"  {split}: {split_conv} converted, {split_skip} already bbox")
        total_conv += split_conv
        total_skip += split_skip
    return total_conv, total_skip


def convert_to_obb(root: Path) -> tuple[int, int]:
    """Convert all annotations to oriented bounding boxes (math only)."""
    total_conv, total_skip = 0, 0
    for split in SPLITS:
        label_dir = root / split / "labels"
        if not label_dir.exists():
            continue
        split_conv, split_skip = 0, 0
        for f in sorted(label_dir.glob("*.txt")):
            c, s = _convert_file_math(f, _line_to_obb)
            split_conv += c
            split_skip += s
        print(f"  {split}: {split_conv} converted, {split_skip} already obb")
        total_conv += split_conv
        total_skip += split_skip
    return total_conv, total_skip


def convert_to_segment(root: Path, sam_model: str, device) -> tuple[int, int]:
    """Convert all annotations to segmentation polygons.

    - bbox lines  → converted using SAM (inlined; works around ultralytics
      int(cls[i]) bug in yolo_bbox2segment)
    - obb lines   → already a valid 4-vertex polygon; kept as-is
    - segment     → kept as-is (skipped)
    """
    try:
        import cv2
        from ultralytics import SAM
        from ultralytics.data import YOLODataset
        from ultralytics.utils import LOGGER, TQDM
        from ultralytics.utils.ops import xywh2xyxy
    except ImportError:
        print("  ERROR: ultralytics is not installed.")
        print("  Install it with:  pip install ultralytics")
        sys.exit(1)

    total_sam = 0
    total_skip = 0

    for split in SPLITS:
        im_dir = root / split / "images"
        label_dir = root / split / "labels"
        if not im_dir.exists() or not label_dir.exists():
            continue

        # Count how many bbox lines exist in this split
        bbox_lines = 0
        non_bbox_lines = 0
        for txt in label_dir.glob("*.txt"):
            with open(txt) as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    if len(s.split()) == 5:
                        bbox_lines += 1
                    else:
                        non_bbox_lines += 1

        if bbox_lines == 0:
            print(f"  {split}: all {non_bbox_lines} lines already segment/obb — skipping SAM")
            total_skip += non_bbox_lines
            continue

        print(f"  {split}: {bbox_lines} bbox lines to convert, "
              f"{non_bbox_lines} already segment/obb")
        print(f"    Running SAM ({sam_model}) — this may take a while...")

        # Load dataset + run SAM inference (equivalent to yolo_bbox2segment
        # but with a fix for the cls[i] scalar conversion bug)
        dataset = YOLODataset(str(im_dir), data=dict(names=list(range(1000)), channels=3))
        if len(dataset.labels[0]["segments"]) > 0:
            LOGGER.info("Segmentation labels already detected, skipping SAM.")
            total_skip += bbox_lines + non_bbox_lines
            continue

        LOGGER.info("Detection labels detected, generating segment labels by SAM model!")
        sam = SAM(sam_model)
        for label in TQDM(dataset.labels, total=len(dataset.labels),
                          desc="Generating segment labels"):
            h, w = label["shape"]
            boxes = label["bboxes"]
            if len(boxes) == 0:
                continue
            boxes[:, [0, 2]] *= w
            boxes[:, [1, 3]] *= h
            im = cv2.imread(label["im_file"])
            sam_results = sam(im, bboxes=xywh2xyxy(boxes), verbose=False,
                             save=False, device=device)
            label["segments"] = sam_results[0].masks.xyn

        # Save segment labels to temporary directory
        seg_dir = root / split / "labels-segment"
        seg_dir.mkdir(parents=True, exist_ok=True)
        for label in dataset.labels:
            texts = []
            lb_name = Path(label["im_file"]).with_suffix(".txt").name
            txt_file = seg_dir / lb_name
            cls = label["cls"]
            for i, s in enumerate(label["segments"]):
                if len(s) == 0:
                    continue
                # .item() converts any 0-d or single-element ndarray to a Python scalar
                line = (int(cls[i].item()), *s.reshape(-1))
                texts.append(("%g " * len(line)).rstrip() % line)
            with open(txt_file, "a", encoding="utf-8") as f:
                f.writelines(text + "\n" for text in texts)
        LOGGER.info(f"Generated segment labels saved in {seg_dir}")

        # Replace original labels with converted ones
        if seg_dir.exists():
            replaced = 0
            for seg_file in seg_dir.glob("*.txt"):
                shutil.copy2(seg_file, label_dir / seg_file.name)
                replaced += 1
            shutil.rmtree(seg_dir)
            print(f"    {replaced} label files updated")
            total_sam += bbox_lines
            total_skip += non_bbox_lines
        else:
            print(f"    WARNING: labels-segment directory not created for {split}")
            print(f"    (SAM may not have found matching image-label pairs)")

    return total_sam, total_skip


# ═══════════════════════════════════════════════════════════════════════════════
#  Removal driver
# ═══════════════════════════════════════════════════════════════════════════════

def _find_matching_image(images_dir: Path, stem: str) -> Path | None:
    """Find an image file matching the given label stem (filename without .txt)."""
    for ext in IMAGE_EXTENSIONS:
        candidate = images_dir / (stem + ext)
        if candidate.exists():
            return candidate
    return None


def remove_non_compliant(root: Path, target: str) -> tuple[int, int]:
    """Delete label files (and their images) that contain ANY line not in the target format.

    A file is non-compliant if it has at least one annotation line whose format
    differs from `target`. Files that are entirely in the target format are kept.

    Returns (removed_files, kept_files).
    """
    total_removed = 0
    total_kept = 0

    for split in SPLITS:
        label_dir = root / split / "labels"
        images_dir = root / split / "images"
        if not label_dir.exists():
            continue

        split_removed = 0
        split_kept = 0

        for txt_file in sorted(label_dir.glob("*.txt")):
            has_non_compliant = False
            has_any_line = False

            with open(txt_file) as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    has_any_line = True
                    fmt = detect_line_format(s.split())
                    if fmt != target:
                        has_non_compliant = True
                        break

            if has_non_compliant or not has_any_line:
                # Remove label
                txt_file.unlink()
                # Remove corresponding image
                img = _find_matching_image(images_dir, txt_file.stem)
                if img:
                    img.unlink()
                split_removed += 1
            else:
                split_kept += 1

        print(f"  {split}: removed {split_removed}, kept {split_kept}")
        total_removed += split_removed
        total_kept += split_kept

    return total_removed, total_kept


# ═══════════════════════════════════════════════════════════════════════════════
#  Interactive prompt
# ═══════════════════════════════════════════════════════════════════════════════

def ask_dataset_root() -> Path:
    """Prompt the user for the dataset root path."""
    print("\nEnter the path to the dataset root folder")
    print("(the folder containing data.yaml, train/, valid/, test/):\n")
    while True:
        raw = input("> ").strip().strip('"').strip("'")
        p = Path(raw)
        if not p.exists():
            print(f"  Path does not exist: {p}")
            continue
        if not (p / "data.yaml").exists():
            print(f"  No data.yaml found in: {p}")
            continue
        return p


def ask_target_format() -> str:
    """Prompt the user for the desired output format."""
    print("\nChoose the target format:")
    print("  [1] bbox      — Standard bounding boxes      (class xc yc w h)")
    print("  [2] obb       — Oriented bounding boxes       (class x1 y1 x2 y2 x3 y3 x4 y4)")
    print("  [3] segment   — Segmentation polygons         (class x1 y1 ... xN yN)")
    print()
    while True:
        choice = input("> ").strip()
        if choice in ("1", "bbox"):
            return "bbox"
        elif choice in ("2", "obb"):
            return "obb"
        elif choice in ("3", "segment"):
            return "segment"
        else:
            print("  Please enter 1, 2, or 3.")


def ask_remove() -> bool:
    """Prompt the user whether to remove non-compliant files instead of converting."""
    print("\nHow should non-compliant files be handled?")
    print("  [1] Convert   — Convert them to the target format (default)")
    print("  [2] Remove    — Delete the label + image entirely")
    print()
    while True:
        choice = input("> ").strip()
        if choice in ("", "1", "convert"):
            return False
        elif choice in ("2", "remove"):
            return True
        else:
            print("  Please enter 1 or 2.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def remove_all_annotations(root: Path) -> int:
    """Delete all annotation lines from label files (keep empty files).

    Returns number of files processed.
    """
    total_files = 0
    for split in SPLITS:
        label_dir = root / split / "labels"
        if not label_dir.exists():
            continue
        
        split_count = 0
        for txt_file in sorted(label_dir.glob("*.txt")):
            txt_file.write_text("")
            split_count += 1
        
        print(f"  {split}: cleared {split_count} files")
        total_files += split_count
    
    return total_files

def main():
    parser = argparse.ArgumentParser(
        description="Convert a YOLOv8 dataset between bbox / obb / segment formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conv-yolo-dataset.py                                 # interactive mode
  python conv-yolo-dataset.py path/to/dataset --to bbox
  python conv-yolo-dataset.py path/to/dataset --to obb
  python conv-yolo-dataset.py path/to/dataset --to segment
  python conv-yolo-dataset.py path/to/dataset --to segment --sam-model sam_l.pt --device cuda:0
  python conv-yolo-dataset.py path/to/dataset --to bbox --remove
  python conv-yolo-dataset.py path/to/dataset --remove-annotations
        """,
    )
    parser.add_argument("dataset", nargs="?", default=None,
                        help="Path to dataset root (contains data.yaml, train/, valid/, test/)")
    parser.add_argument("--to", dest="target", choices=("bbox", "obb", "seg", "segment"), default=None,
                        help="Target annotation format")
    parser.add_argument("--remove", action="store_true",
                        help="Delete non-compliant label files and their images instead of converting")
    parser.add_argument("--remove-annotations", action="store_true",
                        help="Remove all annotations from label files (keep empty files)")
    parser.add_argument("--sam-model", default="sam_b.pt",
                        help="SAM model for bbox→segment (default: sam_b.pt)")
    parser.add_argument("--device", default=None,
                        help="Device for SAM inference (e.g. cpu, cuda, cuda:0, 0)")
    args = parser.parse_args()

    # ── Resolve dataset root ───────────────────────────────────────────────
    if args.dataset:
        root = Path(args.dataset)
        if not root.exists():
            print(f"Error: path does not exist: {root}")
            sys.exit(1)
        if not (root / "data.yaml").exists():
            print(f"Error: no data.yaml in {root}")
            sys.exit(1)
    else:
        root = ask_dataset_root()

    # ── Handle remove-annotations mode ─────────────────────────────────────
    if args.remove_annotations:
        print(f"\n{'='*60}")
        print(f"Dataset : {root}")
        print(f"Mode    : REMOVE ALL ANNOTATIONS")
        print(f"{'='*60}\n")
        
        resp = input("This will clear all annotations. Proceed? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(0)
        
        print()
        total_files = remove_all_annotations(root)
        print(f"\nDone. Cleared {total_files} files.")
        sys.exit(0)

    # ── Resolve target format ──────────────────────────────────────────────
    target = args.target if args.target else ask_target_format()

    # ── Resolve remove mode ────────────────────────────────────────────────
    remove_mode = args.remove if args.remove else (
        ask_remove() if not args.target else False
    )

    # ── Scan current state ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Dataset : {root}")
    print(f"Target  : {target}")
    print(f"Mode    : {'REMOVE non-compliant' if remove_mode else 'CONVERT'}")
    print(f"{'='*60}")

    file_count, stats = scan_dataset(root)
    print_scan(file_count, stats)

    # Check if already uniform in target format
    target_count = stats[target]
    other_count = sum(v for k, v in stats.items() if k != target and k != "unknown")
    if other_count == 0:
        print(f"\n✓ All {target_count} annotations are already in '{target}' format. Nothing to do.")
        return

    # ── Confirm ────────────────────────────────────────────────────────────
    if remove_mode:
        print(f"\nFiles containing non-'{target}' annotations will be DELETED (label + image).")
    else:
        print(f"\n{other_count} annotations will be converted to '{target}'.")
        if target == "segment":
            print(f"SAM model: {args.sam_model}  (will be downloaded if not cached)")
            if args.device:
                print(f"Device: {args.device}")
    resp = input("Proceed? [y/N] ").strip().lower()
    if resp not in ("y", "yes"):
        print("Aborted.")
        return

    # ── Execute ────────────────────────────────────────────────────────────
    print()
    if remove_mode:
        removed, kept = remove_non_compliant(root, target)
        print(f"\n  Removed {removed} files, kept {kept} files.")
    elif target == "bbox":
        converted, skipped = convert_to_bbox(root)
    elif target == "obb":
        converted, skipped = convert_to_obb(root)
    elif target == "segment":
        converted, skipped = convert_to_segment(root, args.sam_model, args.device)

    # ── Verify ─────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Verification")
    print(f"{'='*60}")
    file_count2, stats2 = scan_dataset(root)
    print_scan(file_count2, stats2)

    other_after = sum(v for k, v in stats2.items() if k != target and k != "unknown")
    if other_after == 0:
        print(f"\n✓ All annotations are now in '{target}' format.")
        fmt_hints = {
            "bbox":    "Ultralytics YOLO Detection 1.0",
            "obb":     "Ultralytics YOLO OBB 1.0",
            "segment": "Ultralytics YOLO Segmentation 1.0",
        }
        print(f"  CVAT import format: {fmt_hints[target]}")
    else:
        print(f"\n  {other_after} annotations are still not in '{target}' format.")


if __name__ == "__main__":
    main()
