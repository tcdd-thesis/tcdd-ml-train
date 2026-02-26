"""
Convert PyTorch (.pt) model to ONNX format
===========================================
"""
from ultralytics import YOLO
import os

print("=" * 70)
print("PyTorch to ONNX Converter")
print("=" * 70)

# Load model
model_path = "v0-20250827.1a.pt"
print(f"\nLoading model: {model_path}")
model = YOLO(model_path)
print("✓ Model loaded successfully!")

# Export to ONNX
print("\nExporting to ONNX format...")
result = model.export(format="onnx")

print("\n" + "=" * 70)
print("✓ ONNX EXPORT SUCCESSFUL!")
print("=" * 70)
print(f"Output file: {result}")

# Display file info
if os.path.exists(result):
    size_mb = os.path.getsize(result) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

print("\nYou can now use this ONNX model with:")
print("  • ONNX Runtime (cross-platform)")
print("  • TensorFlow (via onnx-tf)")
print("  • Other ONNX-compatible frameworks")
print("=" * 70)
