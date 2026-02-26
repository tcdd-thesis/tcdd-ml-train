"""
Convert PyTorch (.pt) model to NCNN format
==========================================
This script converts a PyTorch model directly to NCNN format
"""
import os
import sys
from ultralytics import YOLO

print("=" * 70)
print("PyTorch to NCNN Converter")
print("=" * 70)

# Load model
print("\nLoading model...")
model = YOLO("v0-20250827.1a.pt")
print("✓ Model loaded")

# Export to NCNN
print("\nExporting to NCNN format...")
print("This will install required dependencies automatically...")
print("Please wait, this may take several minutes...\n")

try:
    # Set environment variable to bypass certain checks
    os.environ['NCNN_SIMPLIFIED'] = '1'
    
    # Attempt NCNN export
    result = model.export(format='ncnn', simplify=True)
    
    print("\n" + "=" * 70)
    print("✓ EXPORT COMPLETED!")
    print("=" * 70)
    print(f"Result: {result}")
    
    # List all NCNN files
    print("\nNCNN files created:")
    ncnn_files = []
    for file in os.listdir('.'):
        if file.endswith('.param') or file.endswith('.bin') or '_ncnn_model' in file:
            size = os.path.getsize(file) / (1024*1024) if os.path.getsize(file) > 1024 else os.path.getsize(file)
            unit = "MB" if os.path.getsize(file) > 1024*1024 else "bytes"
            print(f"  ✓ {file} ({size:.2f} {unit})")
            ncnn_files.append(file)
    
    if ncnn_files:
        print(f"\n✓✓✓ SUCCESS! {len(ncnn_files)} NCNN file(s) created ✓✓✓")
    else:
        print("\nChecking for NCNN model directory...")
        for item in os.listdir('.'):
            if os.path.isdir(item) and 'ncnn' in item.lower():
                print(f"  Found directory: {item}")
                for file in os.listdir(item):
                    print(f"    • {file}")
    
except Exception as e:
    print(f"\n✗ Export failed: {e}")
    print("\nError details:")
    import traceback
    traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Alternative: Manual NCNN Creation")
    print("=" * 70)
    print("\nSince automatic NCNN export failed, you can:")
    print("1. Use the ONNX model with ONNX Runtime (cross-platform)")
    print("2. Use the TFLite model for mobile deployment")
    print("3. Install WSL and use Linux tools for NCNN conversion")
    print("4. Use a cloud service or remote Linux machine")

print("\n" + "=" * 70)
