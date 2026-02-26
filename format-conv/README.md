# Model Conversion Scripts

This folder contains scripts and utilities for converting the trained YOLOv8 PyTorch model to various deployment formats (ONNX, TFLite, NCNN).

## 📁 Folder Contents

```
Conversion/
├── convert_to_onnx.py              # PyTorch → ONNX converter
├── convert_to_tflite.py            # PyTorch → TFLite converter
├── convert_pt_to_ncnn.py           # PyTorch → NCNN converter
├── calibration_image_sample_data_20x128x128x3_float32.npy  # Calibration data
├── v0-20250827.1a.pt               # Source PyTorch model
├── v0-20250827.1a.onnx             # ✅ Converted ONNX model
├── v0-20250827.1a.tflite           # ✅ Converted TFLite model
├── v0-20250827.1a_ncnn_model/      # ✅ Converted NCNN model
│   ├── model.ncnn.param            #    Network structure
│   └── model.ncnn.bin              #    Model weights
├── v0-20250827.1a_saved_model/     # TensorFlow SavedModel
└── output_tflite/                  # TFLite conversion output
```

## 🎯 Purpose

Convert the trained YOLOv8 traffic detection model (`20250827-best.pt`) to different formats for deployment on various platforms:

| Format | Use Case | Platforms |
|--------|----------|-----------|
| **ONNX** | Cross-platform deployment | Windows, Linux, macOS, Cloud |
| **TFLite** | Mobile & embedded devices | Android, iOS, Edge TPU, Coral |
| **NCNN** | ARM-based mobile devices | Android, iOS, Raspberry Pi |

## 🚀 Quick Start

### Prerequisites

```bash
# Install base requirements
pip install ultralytics

# For ONNX (usually included with ultralytics)
pip install onnx onnxruntime

# For TFLite conversion
pip install onnx2tf tensorflow

# For NCNN (handled automatically by ultralytics)
```

### Convert Models

#### 1. Convert to ONNX

```bash
python convert_to_onnx.py
```

**Output:** `v0-20250827.1a.onnx` (~11-12 MB)

**Use for:**
- Cross-platform inference
- Cloud deployment
- ONNX Runtime
- Integration with various frameworks

#### 2. Convert to TFLite

```bash
python convert_to_tflite.py
```

**Output:** `v0-20250827.1a.tflite` (~5-12 MB)

**Use for:**
- Android/iOS apps
- Edge TPU devices (Google Coral)
- Embedded Linux systems
- Raspberry Pi with TensorFlow Lite

#### 3. Convert to NCNN

```bash
python convert_pt_to_ncnn.py
```

**Output:** `v0-20250827.1a_ncnn_model/`
- `model.ncnn.param` (~17 KB) - Network structure
- `model.ncnn.bin` (~11.6 MB) - Model weights

**Use for:**
- ARM-based devices (Raspberry Pi)
- Android/iOS mobile apps
- Vulkan GPU acceleration
- Low-power edge devices

## 📊 Model Format Comparison

### File Structure

| Format | Files | Total Size |
|--------|-------|------------|
| **PyTorch (.pt)** | Single file | ~12 MB |
| **ONNX (.onnx)** | Single file | ~11-12 MB |
| **TFLite (.tflite)** | Single file | ~5-12 MB |
| **NCNN** | 2 files (.param + .bin) | ~11.6 MB |

### Performance Characteristics

| Format | Inference Speed | Memory Usage | Platform Support |
|--------|----------------|--------------|------------------|
| **PyTorch** | Baseline (fastest on GPU) | High | Limited (Python only) |
| **ONNX** | 95-100% of PyTorch | Medium | Excellent |
| **TFLite** | 80-95% of PyTorch | Low | Mobile-optimized |
| **NCNN** | 85-95% of PyTorch | Very Low | ARM-optimized |

## 🔧 Conversion Details

### ONNX Conversion

**Process:**
1. Load PyTorch model
2. Export using Ultralytics built-in ONNX exporter
3. Validate ONNX model structure

**Features:**
- Direct export from PyTorch
- Preserves model architecture
- Cross-platform compatibility
- ONNX Runtime acceleration

**Code snippet:**
```python
from ultralytics import YOLO

model = YOLO("v0-20250827.1a.pt")
model.export(format="onnx")
```

### TFLite Conversion

**Process:**
1. Convert PyTorch → ONNX (if not exists)
2. Use `onnx2tf` to convert ONNX → TensorFlow SavedModel
3. Convert SavedModel → TFLite

**Options:**
- Float32 (full precision)
- Float16 (half precision, smaller)
- INT8 quantization (requires calibration data)

**Note:** The `calibration_image_sample_data_20x128x128x3_float32.npy` file contains sample images for INT8 quantization calibration.

**Code snippet:**
```python
# Via ultralytics (simpler)
model = YOLO("v0-20250827.1a.pt")
model.export(format="tflite")

# Or use onnx2tf for more control
# See convert_to_tflite.py for detailed implementation
```

### NCNN Conversion

**Process:**
1. Export PyTorch model to ONNX
2. Use PNNX (PyTorch Neural Network eXchange) to convert to NCNN
3. Optimize for ARM/mobile deployment

**Output files:**
- `model.ncnn.param` - Text file with network topology
- `model.ncnn.bin` - Binary file with model weights

**Important:** Both files must be present in the same directory for inference!

**Code snippet:**
```python
from ultralytics import YOLO

model = YOLO("v0-20250827.1a.pt")
model.export(format="ncnn", simplify=True)
```

## 📝 Usage After Conversion

### ONNX Model

```python
from ultralytics import YOLO

# Load ONNX model
model = YOLO("v0-20250827.1a.onnx", task='detect')

# Run inference
results = model("test_video.mp4")
```

### TFLite Model

```python
from ultralytics import YOLO

# Load TFLite model
model = YOLO("v0-20250827.1a.tflite", task='detect')

# Run inference
results = model("test_video.mp4")
```

### NCNN Model

```python
from ultralytics import YOLO

# Load NCNN model (point to directory)
model = YOLO("v0-20250827.1a_ncnn_model", task='detect')

# Run inference
results = model("test_video.mp4")
```

## 🐛 Troubleshooting

### ONNX Conversion Issues

**Error: "onnx not found"**
```bash
pip install onnx onnxruntime
```

**Error: "opset version"**
- Update ultralytics: `pip install --upgrade ultralytics`
- Or specify opset: `model.export(format="onnx", opset=11)`

### TFLite Conversion Issues

**Error: "onnx2tf not found"**
```bash
pip install onnx2tf tensorflow
```

**Error: "Unsupported operation"**
- Some YOLOv8 operations may not be fully supported in TFLite
- Try simplifying the model or using dynamic=False

**Slow conversion:**
- TFLite conversion can take 5-15 minutes
- Be patient, especially for the first conversion

### NCNN Conversion Issues

**Error: "PNNX not found"**
- Ultralytics will attempt to auto-install PNNX
- On Windows, this may require WSL (Windows Subsystem for Linux)
- Alternative: Use Linux environment or Docker

**Error: "ncnn library missing"**
- NCNN requires specific system libraries
- On Linux: `sudo apt install libncnn-dev`
- On Windows: May need manual compilation or WSL

## 🎓 Best Practices

### Model Selection by Platform

**Desktop/Server Applications:**
- Use **ONNX** for maximum compatibility
- Use **PyTorch** if Python environment available

**Mobile Apps (Android/iOS):**
- Use **TFLite** for TensorFlow Lite runtime
- Use **NCNN** for better ARM CPU performance

**Embedded Devices:**
- Raspberry Pi: **NCNN** or **TFLite**
- Edge TPU/Coral: **TFLite** (with INT8 quantization)
- Jetson Nano: **ONNX** or **PyTorch**

**Cloud Deployment:**
- Use **ONNX** for maximum flexibility
- Use **PyTorch** with GPU for best performance

### Optimization Tips

1. **For speed:** Use FP16 (half-precision) if hardware supports it
2. **For size:** Use INT8 quantization with calibration data
3. **For compatibility:** Stick with ONNX
4. **For mobile:** Use NCNN on ARM, TFLite on accelerators

## 📂 Output Directory Structure

After running all conversions, you should have:

```
Model/                              # Main deployment directory
├── 20250827-best.pt               # Original PyTorch model
├── v0-20250827.1a.onnx           # ONNX model (copied from Conversion/)
├── v0-20250827.1a.tflite         # TFLite model (copied from Conversion/)
└── v0-20250827.1a_ncnn_model/    # NCNN model directory (copied from Conversion/)
    ├── model.ncnn.param
    └── model.ncnn.bin

Conversion/                         # Source conversion directory
├── v0-20250827.1a.onnx           # Generated ONNX
├── v0-20250827.1a.tflite         # Generated TFLite
└── v0-20250827.1a_ncnn_model/    # Generated NCNN
```

## 🔗 Related Files

- **Test scripts:** `../Test Model/test_model_*.py`
- **Documentation:** `../Test Model/MODEL_PATHS_VERIFICATION.md`
- **NCNN details:** `../Test Model/Docs/NCNN_MODEL_STRUCTURE.md`

## 📊 Validation

After conversion, validate models using test scripts:

```bash
cd "../Test Model"

# Test ONNX
python test_model_onnx.py

# Test TFLite
python test_model_tflite.py

# Test NCNN
python test_model_ncnn.py
```

All formats should produce identical detection results with slight performance variations.

## 🆘 Getting Help

**Common questions:**

1. **Which format should I use?**
   - Desktop/Server → ONNX
   - Android/iOS → TFLite or NCNN
   - Raspberry Pi → NCNN
   - Edge TPU → TFLite (quantized)

2. **Why are there multiple TFLite files?**
   - Float32 (full precision)
   - Float16 (half precision, smaller)
   - INT8 (quantized, smallest)
   - Use INT8 for best performance on mobile

3. **Can I use NCNN on Windows?**
   - Yes, but ONNX is recommended for Windows
   - NCNN is optimized for ARM/Linux

4. **How do I verify conversion was successful?**
   - Check file sizes (should be ~5-12 MB)
   - Run test scripts in `Test Model/` folder
   - Compare detection results with original model

## 📄 License

These conversion scripts are part of the TCDD ML training project for traffic sign/signal detection.

---

**Last Updated:** October 14, 2025  
**Model Version:** v0-20250827.1a  
**Source Model:** 20250827-best.pt (YOLOv8 traffic detection model)
