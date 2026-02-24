# Hailo HEF Integration on Raspberry Pi 5 AI HAT+

## Overview

This document provides a comprehensive guide for deploying a compiled YOLO11n HEF model on Raspberry Pi 5 with Hailo-8L AI HAT+. This is the continuation of the [HAILO_ONNX_TO_HEF_CONVERSION.md](./HAILO_ONNX_TO_HEF_CONVERSION.md) guide.

**Date:** February 1, 2026  
**Model:** `yolov11n.hef` (custom-trained, 1 class: Label)  
**Hardware:** Raspberry Pi 5 + Hailo-8L AI HAT+  
**Application:** OCR-HandHeld-V2 (Flask web application)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [Software Integration](#software-integration)
4. [Issues Encountered & Solutions](#issues-encountered--solutions)
5. [Final Working Code](#final-working-code)
6. [Performance Results](#performance-results)
7. [Verification Commands](#verification-commands)

---

## Prerequisites

### Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Raspberry Pi | Model 5 (4GB or 8GB) |
| AI Accelerator | Hailo-8L AI HAT+ |
| Camera | IMX708 (Camera Module 3) |
| Storage | microSD 32GB+ |

### Software Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| Raspberry Pi OS | Bookworm (64-bit) | Operating system |
| HailoRT | Latest | Hailo runtime library |
| hailo-all | Latest | Complete Hailo package |
| Python | 3.11+ | Application runtime |
| Flask | 2.x | Web server |
| PaddleOCR | 2.7+ | Text extraction |

### Files Required

| File | Location | Description |
|------|----------|-------------|
| `yolov11n.hef` | `models/yolov11n.hef` | Compiled Hailo model |
| `app.py` | Project root | Flask application |

---

## Hardware Setup

### Step 1: Install AI HAT+

1. Power off Raspberry Pi
2. Attach AI HAT+ to GPIO header
3. Connect FFC cable (if required for your HAT+ version)
4. Power on

### Step 2: Install Hailo Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Hailo runtime and tools
sudo apt install hailo-all -y

# Reboot to load kernel modules
sudo reboot
```

### Step 3: Verify Hardware Detection

```bash
# Check Hailo device
hailortcli fw-control identify
```

**Expected Output:**
```
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.20.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8L
Device Architecture: HAILO8L
Serial Number: HLDDLBB241601736
Part Number: HM21LB1C2LAE
Product Name: HAILO-8L AI ACC M.2 B+M KEY MODULE EXT TMP
```

---

## Software Integration

### Step 1: Transfer HEF Model to Pi

From your development machine:

```bash
# Via SCP
scp yolov11n.hef pi@<PI_IP>:/home/pi/OCR-HandHeld-V2/models/

# Or via Tailscale
scp yolov11n.hef pi@<TAILSCALE_HOSTNAME>:/home/pi/OCR-HandHeld-V2/models/
```

### Step 2: Python Dependencies

```bash
# Install Hailo Python bindings (included in hailo-all)
pip3 install hailo-platform  # Usually auto-installed

# Verify import works
python3 -c "from hailo_platform import HEF, VDevice; print('Hailo OK')"
```

### Step 3: Application Code Structure

The integration requires these key components in `app.py`:

```python
# 1. Import Hailo libraries
from hailo_platform import (
    HEF, VDevice, HailoStreamInterface, 
    ConfigureParams, InferVStreams, 
    InputVStreamParams, OutputVStreamParams
)

# 2. Global variables for Hailo
HAILO_AVAILABLE = False
hailo_device = None
hailo_hef = None
hailo_network_group = None
hailo_network_group_context = None  # Activated context

# 3. Configuration
HAILO_HEF_PATH = 'models/yolov11n.hef'
HAILO_INPUT_SIZE = (640, 640)
HAILO_CONFIDENCE_THRESHOLD = 0.25
```

---

## Issues Encountered & Solutions

### Issue 1: "Network group is not activated"

**Error Message:**
```
HailoRTStatusException: Network group is not activated
```

**Cause:** Hailo network group must be explicitly activated before inference.

**Solution:** Wrap InferVStreams inside `network_group.activate()` context manager:

```python
# ❌ WRONG - network not activated
with InferVStreams(hailo_network_group, input_params, output_params) as pipeline:
    results = pipeline.infer(input_data)

# ✅ CORRECT - activate network first
with hailo_network_group.activate():
    with InferVStreams(hailo_network_group, input_params, output_params) as pipeline:
        results = pipeline.infer(input_data)
```

---

### Issue 2: "'list' object has no attribute 'shape'"

**Error Message:**
```
AttributeError: 'list' object has no attribute 'shape'
```

**Cause:** Hailo NMS (Non-Maximum Suppression) post-processing returns a nested list structure, not a direct numpy array.

**Output Structure Analysis:**
```
Output 'yolov11n/yolov8_nms_postprocess': LIST with 1 items
   [0]: type=<class 'list'>, value=[array([], shape=(0, 5), dtype=float64)]
```

The structure is: `list[class_index] → list → ndarray(N, 5)`

**Solution:** Parse the nested list structure correctly:

```python
def parse_hailo_yolo_output(raw_output, frame_w, frame_h):
    """Parse Hailo YOLO NMS output (nested list structure)"""
    detections = []
    
    for output_name, output_data in raw_output.items():
        if 'nms' not in output_name.lower():
            continue
        
        # Handle nested list: list[class] -> list -> array
        if isinstance(output_data, list):
            for class_idx, class_detections in enumerate(output_data):
                # class_detections is also a list containing arrays
                if isinstance(class_detections, list):
                    for det_array in class_detections:
                        if isinstance(det_array, np.ndarray) and det_array.size > 0:
                            detections.extend(
                                _parse_detections_from_array(det_array, class_idx, frame_w, frame_h)
                            )
    
    return detections
```

---

### Issue 3: Wrong HEF File Path

**Symptom:** Application looking for `models/yolo/best.hef` instead of `models/yolov11n.hef`

**Cause:** Old code was still running on Pi (didn't pull latest changes)

**Solution:** 
```bash
cd ~/OCR-HandHeld-V2
git pull
python app.py
```

---

### Issue 4: Empty Detections (Model Returns No Results)

**Debug Output:**
```
Output 'yolov11n/yolov8_nms_postprocess': LIST with 1 items
   [0]: type=<class 'list'>, value=[array([], shape=(0, 5), dtype=float64)]
```

**Cause:** Color space mismatch - Hailo Model Zoo YOLO models expect **BGR** input, but Picamera2 provides **RGB**.

**Solution:** Convert RGB to BGR before inference:

```python
def run_hailo_inference(frame):
    # Resize to model input size
    resized = cv2.resize(frame, HAILO_INPUT_SIZE)
    
    # CRITICAL: Hailo Model Zoo YOLO models expect BGR format
    # Camera provides RGB, so we need to convert
    resized_bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR)
    
    # Normalize and prepare input
    input_data = resized_bgr.astype(np.float32) / 255.0
    input_data = np.expand_dims(input_data, axis=0)
    
    # Run inference...
```

---

### Issue 5: Video Stream Lag During OCR

**Symptom:** UI freezes at "Stabilizing... 33%" when OCR triggers

**Cause:** PaddleOCR was running synchronously inside the frame generation loop, blocking the MJPEG stream for 500-2000ms.

**Solution:** Move OCR to a background thread:

```python
import threading

def background_ocr_and_match(frame_copy, bbox_copy, timestamp_copy):
    """Process OCR and product matching without blocking video stream"""
    global app_state, latest_ocr_result
    
    # Run OCR
    ocr_text = extract_text_from_frame(frame_copy, crop_bbox=bbox_copy)
    
    # Run product matching
    matched_product = product_matcher.match(ocr_text)
    
    # Update app state
    app_state['last_scan_result']['text'] = ocr_text
    app_state['last_scan_result']['matched_product'] = matched_product
    app_state['ocr_processing'] = False
    
    # NOW transition to next screen
    app_state['current_screen'] = 'temperature'

# Start background thread
ocr_thread = threading.Thread(
    target=background_ocr_and_match,
    args=(clean_frame.copy(), bbox, timestamp),
    daemon=True
)
ocr_thread.start()
```

---

## Final Working Code

### Hailo Initialization

```python
# Initialize Hailo AI HAT+ for YOLO inference
HAILO_HEF_PATH = 'models/yolov11n.hef'
HAILO_INPUT_SIZE = (640, 640)
HAILO_CONFIDENCE_THRESHOLD = 0.25

USING_HAILO = False

if HAILO_AVAILABLE and os.path.exists(HAILO_HEF_PATH):
    try:
        print(f"🚀 Initializing Hailo with {HAILO_HEF_PATH}...")
        
        # Create virtual device
        hailo_device = VDevice()
        
        # Load HEF
        hailo_hef = HEF(HAILO_HEF_PATH)
        
        # Configure network
        configure_params = ConfigureParams.create_from_hef(
            hailo_hef, 
            interface=HailoStreamInterface.PCIe
        )
        network_groups = hailo_device.configure(hailo_hef, configure_params)
        hailo_network_group = network_groups[0]
        
        # Activate network group (keep active for entire session)
        hailo_network_group_context = hailo_network_group.activate()
        
        USING_HAILO = True
        print(f"⚡ YOLO11n running on Hailo-8L NPU (fast mode)")
        
    except Exception as e:
        print(f"❌ Hailo initialization failed: {e}")
        USING_HAILO = False
```

### Inference Function

```python
def run_hailo_inference(frame):
    """Run YOLO inference on Hailo AI HAT+"""
    global hailo_network_group, hailo_network_group_context
    
    if not USING_HAILO or hailo_network_group is None:
        return []
    
    try:
        frame_h, frame_w = frame.shape[:2]
        
        # Preprocess: resize to 640x640
        resized = cv2.resize(frame, HAILO_INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        
        # CRITICAL: Convert RGB to BGR for Hailo Model Zoo
        resized_bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR)
        
        # Normalize to float32 [0, 1]
        input_data = resized_bgr.astype(np.float32) / 255.0
        input_data = np.expand_dims(input_data, axis=0)
        
        # Get stream parameters
        input_vstream_info = hailo_network_group.get_input_vstream_infos()[0]
        output_vstream_infos = hailo_network_group.get_output_vstream_infos()
        
        input_params = InputVStreamParams.make(hailo_network_group)
        output_params = OutputVStreamParams.make(hailo_network_group)
        
        # Prepare input dict
        input_dict = {input_vstream_info.name: input_data}
        
        # Run inference (network already activated globally)
        with InferVStreams(hailo_network_group, input_params, output_params) as pipeline:
            raw_output = pipeline.infer(input_dict)
        
        # Parse output
        detections = parse_hailo_yolo_output(raw_output, frame_w, frame_h)
        
        return detections
        
    except Exception as e:
        print(f"❌ Hailo inference error: {e}")
        return []
```

### Output Parser

```python
def parse_hailo_yolo_output(raw_output, frame_w, frame_h):
    """Parse Hailo YOLO NMS output"""
    detections = []
    class_names = ['Label']  # Single class model
    
    for output_name, output_data in raw_output.items():
        if 'nms' not in output_name.lower():
            continue
        
        # Handle nested list structure
        if isinstance(output_data, list):
            for class_idx, class_detections in enumerate(output_data):
                if isinstance(class_detections, list):
                    for det_array in class_detections:
                        if isinstance(det_array, np.ndarray) and det_array.size > 0:
                            detections.extend(
                                _parse_detections_from_array(
                                    det_array, class_idx, frame_w, frame_h, class_names
                                )
                            )
    
    return detections


def _parse_detections_from_array(det_array, class_idx, frame_w, frame_h, class_names):
    """Parse individual detection array"""
    detections = []
    
    if det_array.ndim == 1:
        det_array = det_array.reshape(1, -1)
    
    for det in det_array:
        if len(det) >= 5:
            # Hailo NMS format: [y1, x1, y2, x2, confidence]
            y1, x1, y2, x2, confidence = det[:5]
            
            if confidence < HAILO_CONFIDENCE_THRESHOLD:
                continue
            
            # Scale to frame size
            x1_scaled = int(x1 * frame_w)
            y1_scaled = int(y1 * frame_h)
            x2_scaled = int(x2 * frame_w)
            y2_scaled = int(y2 * frame_h)
            
            # Clamp to frame bounds
            x1_scaled = max(0, min(frame_w - 1, x1_scaled))
            y1_scaled = max(0, min(frame_h - 1, y1_scaled))
            x2_scaled = max(0, min(frame_w - 1, x2_scaled))
            y2_scaled = max(0, min(frame_h - 1, y2_scaled))
            
            class_name = class_names[class_idx] if class_idx < len(class_names) else f'class_{class_idx}'
            
            detections.append({
                'bbox': (x1_scaled, y1_scaled, x2_scaled, y2_scaled),
                'confidence': float(confidence),
                'class_id': class_idx,
                'class_name': class_name
            })
    
    return detections
```

---

## Performance Results

### Before (NCNN on CPU)

| Metric | Value |
|--------|-------|
| Inference Time | ~100-200ms |
| FPS | ~5-10 |
| CPU Usage | ~80-100% |

### After (Hailo-8L NPU)

| Metric | Value |
|--------|-------|
| Inference Time | ~10-30ms |
| FPS | ~30-50+ |
| CPU Usage | ~20-40% |

**Improvement:** ~5-10x faster inference with significantly lower CPU usage.

---

## Verification Commands

### Check Hailo Hardware

```bash
# Identify device
hailortcli fw-control identify

# Check temperature
hailortcli fw-control temperature

# Monitor performance
hailortcli run --hef models/yolov11n.hef --measure-fps
```

### Check Application Logs

```bash
# Run application and watch for Hailo messages
python app.py

# Expected startup messages:
# ✅ Hailo Runtime loaded (AI HAT+ support)
# 🚀 Initializing Hailo with models/yolov11n.hef...
# ⚡ YOLO11n running on Hailo-8L NPU (fast mode)
```

### Verify Detection Working

1. Open browser: `http://<PI_IP>:5000`
2. Point camera at a label
3. Watch for green bounding box around detected label
4. Check terminal for inference timing logs

---

## Git Branch Information

All Hailo integration work was done on the `hailo-integration` branch:

```bash
git checkout hailo-integration
git log --oneline

# Key commits:
# - Initial Hailo integration
# - Fix: Network group activation
# - Fix: Nested list output parsing
# - Fix: RGB to BGR conversion for Hailo Model Zoo
# - Fix: Background thread for OCR (prevent video lag)
# - Fix: OCR processing indicator
```

---

## Known Issues (To Be Fixed)

### Progress Bar Not Incrementing 0-100%

**Status:** Pending fix  
**Description:** The stability progress bar should show gradual 0% → 100% during stabilization, then trigger OCR when complete. Currently the visual feedback may not be updating correctly on the video feed.

**Expected Behavior:**
1. Point at label → "Stabilizing... 0%"
2. Hold steady → Progress bar fills → "Stabilizing... 100%"
3. Auto-capture → "Processing OCR..."
4. OCR complete → Transition to temperature screen

---

## Summary

The Hailo HEF integration on Raspberry Pi 5 AI HAT+ was **successful** with the following key learnings:

1. **Network Activation Required**: Always wrap inference in `network_group.activate()` context
2. **Output Format**: Hailo NMS returns nested lists, not direct arrays
3. **Color Space**: Hailo Model Zoo expects BGR input (convert from RGB)
4. **Background Processing**: Heavy operations (OCR) should run in separate threads
5. **Performance Gain**: ~5-10x faster inference compared to CPU

---

## Related Documentation

- [HAILO_ONNX_TO_HEF_CONVERSION.md](./HAILO_ONNX_TO_HEF_CONVERSION.md) - Model conversion guide
- [YOLO_DEPLOYMENT.md](./YOLO_DEPLOYMENT.md) - Original YOLO deployment
- [PROGRESS_REPORT.md](../PROGRESS_REPORT.md) - Overall project status

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-01 | 1.0 | Initial integration completed |

---

*Generated from Hailo integration session on February 1, 2026*
