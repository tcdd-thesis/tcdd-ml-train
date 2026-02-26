"""
Convert PyTorch (.pt) model to TFLite format
============================================
This script converts a PyTorch model to TFLite format via ONNX
"""
import subprocess
import sys
import os
from ultralytics import YOLO

print("=" * 70)
print("PyTorch to TFLite Converter")
print("=" * 70)

# Step 1: Convert PT to ONNX
model_path = "v0-20250827.1a.pt"
onnx_file = "v0-20250827.1a.onnx"

print(f"\nStep 1: Converting {model_path} to ONNX...")
if not os.path.exists(onnx_file):
    model = YOLO(model_path)
    onnx_file = model.export(format="onnx")
    print(f"✓ ONNX created: {onnx_file}")
else:
    print(f"✓ ONNX file already exists: {onnx_file}")

# Step 2: Convert ONNX to TFLite using onnx2tf
print("\nStep 2: Converting ONNX to TFLite...")
print("This may take several minutes...")

try:
    # Use onnx2tf for conversion
    result = subprocess.run([
        sys.executable, "-m", "onnx2tf",
        "-i", onnx_file,
        "-o", "output_tflite",
        "-osd"  # Skip dimension matching
    ], capture_output=True, text=True, timeout=600)
    
    if result.returncode == 0:
        print("✓ Conversion successful!")
        
        # Find the TFLite file
        tflite_files = []
        for file in os.listdir('.'):
            if file.endswith('.tflite'):
                size_mb = os.path.getsize(file) / (1024 * 1024)
                print(f"\n✓ TFLite file created: {file} ({size_mb:.2f} MB)")
                tflite_files.append(file)
        
        if tflite_files:
            print("\n" + "=" * 70)
            print("✓✓✓ TFLITE CONVERSION SUCCESSFUL! ✓✓✓")
            print("=" * 70)
            print("\nYou can now use this TFLite model with:")
            print("  • TensorFlow Lite (Android/iOS)")
            print("  • Edge TPU devices")
            print("  • Embedded systems")
        else:
            print("\nTFLite file not found in root directory.")
            print("Check the output_tflite directory.")
    else:
        print(f"✗ Conversion failed: {result.stderr}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nMake sure onnx2tf is installed:")
    print("  pip install onnx2tf tensorflow")

print("=" * 70)
