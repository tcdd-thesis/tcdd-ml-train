# Complete Hailo AI Guide: From ONNX to Raspberry Pi Deployment

## Overview

This comprehensive guide covers the complete workflow for deploying a YOLO11n model on Raspberry Pi 5 with Hailo-8L AI HAT+, including:
1. **Model Conversion**: ONNX to HEF format using Hailo SW Suite
2. **Hardware Integration**: HEF deployment and optimization on Raspberry Pi 5

**Project Details:**
- **Model:** YOLO11n (1 class: Label detection)
- **Source Format:** `.onnx` (from Ultralytics training)
- **Target Format:** `.hef` (Hailo Executable Format)
- **Hardware:** Raspberry Pi 5 + Hailo-8L AI HAT+
- **Application:** OCR-HandHeld-V2 (Flask web application)
- **Date:** January 31 - February 1, 2026

---

## Table of Contents

### Part 1: ONNX to HEF Conversion
1. [Conversion Prerequisites](#conversion-prerequisites)
2. [VM Setup](#vm-setup)
3. [Hailo SW Suite Installation](#hailo-sw-suite-installation)
4. [Conversion Process](#conversion-process)
5. [Conversion Troubleshooting](#conversion-troubleshooting)

### Part 2: Raspberry Pi Integration
6. [Integration Prerequisites](#integration-prerequisites)
7. [Hardware Setup](#hardware-setup)
8. [Software Integration](#software-integration)
9. [Integration Issues & Solutions](#integration-issues--solutions)
10. [Final Working Code](#final-working-code)
11. [Performance Results](#performance-results)

### Part 3: Reference & Resources
12. [Verification Commands](#verification-commands)
13. [Quick Reference](#quick-reference)
14. [Resources](#resources)

---

# Part 1: ONNX to HEF Conversion

## Conversion Prerequisites

### Hardware Requirements for Conversion

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32 GB |
| Storage | 50 GB | 100 GB |
| CPU | x86_64 with AVX | x86_64 with AVX |
| GPU | Optional | NVIDIA (speeds up optimization) |

### Software Requirements

- VMware Workstation (or similar virtualization)
- Ubuntu Server 24.04 LTS
- Docker
- Hailo AI SW Suite 2025-10

### Files Needed

| File | Description |
|------|-------------|
| `best.onnx` | Your trained YOLO model exported from Ultralytics |
| `hailo8_ai_sw_suite_2025-10_docker.zip` | Hailo SW Suite (download from Hailo Developer Zone) |
| Calibration images | 100+ PNG/JPG images from your training dataset |

---

## VM Setup

### Step 1: Create VM in VMware

**VM Settings:**
- **OS:** Ubuntu Server 24.04 LTS
- **RAM:** 20 GB (minimum 16 GB)
- **Storage:** 100 GB
- **CPU:** 4+ cores

> ⚠️ **Important:** When creating the disk, Ubuntu's LVM may only allocate 50% by default. You'll need to expand it.

### Step 2: Expand LVM to Full Disk Size

After Ubuntu installation, if disk shows less than allocated:

```bash
# Check current disk layout
lsblk

# Example output shows sda3 = 98GB but LVM only uses 49GB
# NAME                      SIZE  TYPE MOUNTPOINTS
# sda                       100G  disk
# ├─sda1                      1M  part
# ├─sda2                      2G  part /boot
# └─sda3                     98G  part
#   └─ubuntu--vg-ubuntu--lv  49G  lvm  /

# Extend LVM to use all available space
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv

# Verify
df -h /
# Should show ~97GB total
```

### Step 3: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y ca-certificates curl unzip

# Add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker run hello-world
```

### Step 4: Install Tailscale (Optional - for easy file transfer)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

## Hailo SW Suite Installation

### Step 1: Transfer Hailo SW Suite to VM

From Windows PowerShell:

```powershell
scp "C:\Users\hanst\Downloads\hailo8_ai_sw_suite_2025-10_docker.zip" mariobag@vm-ubuntu:/home/mariobag/
```

### Step 2: Extract and Prepare

```bash
cd ~
unzip hailo8_ai_sw_suite_2025-10_docker.zip

# Create shared folder for model files
mkdir -p ~/shared_with_docker
chmod 777 ~/shared_with_docker

# List extracted files
ls -la
# Should show:
# - hailo8_ai_sw_suite_2025-10.tar.gz
# - hailo_ai_sw_suite_docker_run.sh
```

### Step 3: Load and Run Hailo Docker

```bash
./hailo_ai_sw_suite_docker_run.sh
```

> ⚠️ **This takes 15-45 minutes!** The script loads a ~15-20GB Docker image.

**Expected output when complete:**

```
Loaded image: hailo8_ai_sw_suite_2025-10:1
Running Hailo AI SW suite Docker image...

Welcome to Hailo AI Software Suite Container
(hailo_virtualenv) hailo@vm-ubuntu:/local/workspace$
```

### Hailo Docker Commands Reference

| Command | Purpose |
|---------|---------|
| `./hailo_ai_sw_suite_docker_run.sh` | First run / create container |
| `./hailo_ai_sw_suite_docker_run.sh --resume` | Re-enter existing container |
| `./hailo_ai_sw_suite_docker_run.sh --override` | Delete and recreate container |
| `exit` | Exit container |

### Folder Mapping

| Host Path | Container Path |
|-----------|----------------|
| `/home/mariobag/shared_with_docker/` | `/local/shared_with_docker/` |

---

## Conversion Process

### Overview of Conversion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE (Already Done)              │
├─────────────────────────────────────────────────────────────────┤
│  CVAT (Annotate) → Ultralytics (Train) → best.pt → best.onnx   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    HAILO CONVERSION PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│  best.onnx → Parse (HAR) → Optimize (Quantize) → Compile (HEF) │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI DEPLOYMENT                       │
├─────────────────────────────────────────────────────────────────┤
│  yolov11n.hef → HailoRT → AI HAT+ → Real-time Detection        │
└─────────────────────────────────────────────────────────────────┘
```

### File Formats

| Extension | Name | Description |
|-----------|------|-------------|
| `.pt` | PyTorch | Ultralytics model weights |
| `.onnx` | ONNX | Open Neural Network Exchange (portable) |
| `.har` | Hailo Archive | Intermediate format (parsed/optimized) |
| `.hef` | Hailo Executable Format | Final format for Hailo hardware |

### Step 1: Transfer Model to VM

From Windows PowerShell:

```powershell
scp "C:\path\to\best.onnx" mariobag@vm-ubuntu:/home/mariobag/shared_with_docker/
```

### Step 2: Transfer Calibration Images

Calibration images are needed for quantization (float32 → int8). Use 100 random images from your training dataset.

```powershell
# Get 100 random PNG images
$images = Get-ChildItem "J:\THESIS\LabelsExport\images\train\*.png" | Get-Random -Count 100

# Create temp folder
$tempFolder = "C:\temp\calib_images"
New-Item -ItemType Directory -Force -Path $tempFolder

# Copy to temp folder
$images | Copy-Item -Destination $tempFolder

# Transfer to VM
scp -r "$tempFolder\*" mariobag@vm-ubuntu:/home/mariobag/shared_with_docker/calib_images/
```

On VM, set permissions:

```bash
sudo chmod 777 /home/mariobag/shared_with_docker/calib_images
sudo chmod 666 /home/mariobag/shared_with_docker/calib_images/*
```

### Step 3: Compile Using Hailo Model Zoo (Recommended Method)

Inside the Hailo container:

```bash
cd /local/shared_with_docker

# Compile YOLO11n model
hailomz compile yolov11n \
    --ckpt /local/shared_with_docker/best.onnx \
    --hw-arch hailo8l \
    --calib-path /local/shared_with_docker/calib_images/ \
    --classes 1
```

**Parameters:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `yolov11n` | Model config | Uses Hailo's optimized YOLO11n settings |
| `--ckpt` | `best.onnx` | Your trained model |
| `--hw-arch` | `hailo8l` | Target: Hailo-8L chip |
| `--calib-path` | Folder path | Calibration images (PNG/JPG) |
| `--classes` | `1` | Number of classes in your model |

**Expected Duration:** 20-40 minutes (on CPU without GPU)

### Step 4: Verify Output

```bash
ls -la /local/shared_with_docker/yolov11n.hef
```

**Successful Compilation Results:**

```
[info] Successful Mapping (allocation time: 18m 44s)
[info] Compiling kernels...
[info] Bandwidth of model inputs: 9.375 Mbps, outputs: 4.16565 Mbps
[info] Building HEF...
[info] Successful Compilation (compilation time: 13s)
<Hailo Model Zoo INFO> HEF file written to yolov11n.hef
```

### Output Files

| File | Location | Size |
|------|----------|------|
| `yolov11n.hef` | `/local/shared_with_docker/` (container) | ~2-5 MB |
| `yolov11n.har` | `/local/shared_with_docker/` (container) | ~10-20 MB |

Host path: `/home/mariobag/shared_with_docker/`

### Model Specifications

| Specification | Value |
|---------------|-------|
| Model | YOLO11n |
| Classes | 1 (label) |
| Input Size | 640×640×3 |
| Hardware Target | Hailo-8L |
| Contexts | 5 |
| Optimization Level | 0 (due to <1024 calibration images) |

---

## Conversion Troubleshooting

### Issue 1: VM Disk Space Errors

**Symptom:**
```
E: You don't have enough free space in /var/cache/apt/archives/
```

**Solution:**
```bash
sudo apt clean
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv
```

### Issue 2: Docker Permission Denied

**Symptom:**
```
permission denied while trying to connect to the docker API
```

**Solution:**
```bash
sudo usermod -aG docker $USER
# Logout and login again, or:
newgrp docker
```

### Issue 3: SCP Transfer Fails at 82%

**Symptom:**
```
scp: write remote: Failure
```

**Cause:** VM disk full

**Solution:** Expand VM disk and LVM (see VM Setup section)

### Issue 4: Calibration Image Permission Denied

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: 'frame_xxxxx.npy'
```

**Solution:**
```bash
# From VM terminal (outside container)
sudo chmod 777 /home/mariobag/shared_with_docker/calib_images
sudo chmod 666 /home/mariobag/shared_with_docker/calib_images/*
```

### Issue 5: Manual Compilation Fails (Allocation Error)

**Symptom:**
```
[error] Mapping Failed
[error] No successful assignments: concat21 errors: Agent infeasible
```

**Cause:** Manual `hailo parser` + `hailo optimize` + `hailo compiler` flow doesn't have proper allocation settings for YOLO on Hailo-8L.

**Solution:** Use Hailo Model Zoo instead:
```bash
hailomz compile yolov11n --ckpt best.onnx --hw-arch hailo8l --calib-path calib_images/ --classes 1
```

### Issue 6: Calibration Data Shape Mismatch

**Symptom:**
```
BadInputsShape: Data shape (1080, 1920, 3) doesn't match network's input shape (640, 640, 3)
```

**Cause:** Using raw `.npy` files instead of resized images

**Solution:** Use original PNG/JPG images - Hailo Model Zoo handles resizing automatically.

### Issue 7: Docker Load Appears Frozen

**Symptom:** Script stuck at "Loading Docker image..."

**This is normal!** Docker load takes 15-45 minutes.

**Monitor progress** in second terminal:
```bash
watch -n 30 'df -h / && sudo du -sh /var/lib/docker'
```

---

# Part 2: Raspberry Pi Integration

## Integration Prerequisites

### Hardware Requirements for Deployment

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

## Integration Issues & Solutions

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

# Part 3: Reference & Resources

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

## Quick Reference

### Training Configuration Reference

Your model was trained with these settings:

```python
from ultralytics import YOLO

model = YOLO('yolo11n.pt')
results = model.train(
    data='data.yaml',
    epochs=100,
    imgsz=640,              # Input size
    batch=-1,               # Auto batch
    device=0,               # GPU
    optimizer='AdamW',
    lr0=0.01,
    cos_lr=True,
    amp=True,               # Mixed precision
    mosaic=1.0,
    # ... other augmentation settings
)
```

**Key info for Hailo conversion:**
- Input size: 640×640
- Classes: 1 (label)
- Architecture: YOLO11n (nano)

### Hailo Container Commands

| Command | Purpose |
|---------|---------|
| `hailo -h` | Dataflow Compiler help |
| `hailomz compile --help` | Model Zoo compile help |
| `hailortcli -h` | HailoRT CLI help |

### One-Command Conversion (RECOMMENDED)

```bash
# Inside Hailo container
hailomz compile yolov11n \
    --ckpt /local/shared_with_docker/best.onnx \
    --hw-arch hailo8l \
    --calib-path /local/shared_with_docker/calib_images/ \
    --classes 1
```

### Manual Conversion (If Needed)

```bash
# Step 1: Parse
hailo parser onnx best.onnx --hw-arch hailo8l

# Step 2: Optimize
hailo optimize best.har --hw-arch hailo8l --calib-set-path calib_images/

# Step 3: Compile
hailo compiler best_optimized.har --hw-arch hailo8l
```

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

## Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Model Zoo GitHub](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo SW Suite Documentation](https://hailo.ai/developer-zone/documentation/)
- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)

---

## Summary

The complete Hailo workflow from ONNX to Raspberry Pi deployment was **successful** with the following key learnings:

### Conversion Phase:
1. **VM Setup**: Ubuntu 24.04 LTS with 20GB RAM and 100GB storage required
2. **Docker Image**: 15-45 minute load time is normal for Hailo SW Suite
3. **Model Zoo Approach**: Recommended over manual conversion steps
4. **Calibration**: Use original PNG/JPG images, not preprocessed arrays

### Integration Phase:
1. **Network Activation Required**: Always wrap inference in `network_group.activate()` context
2. **Output Format**: Hailo NMS returns nested lists, not direct arrays
3. **Color Space**: Hailo Model Zoo expects BGR input (convert from RGB)
4. **Background Processing**: Heavy operations (OCR) should run in separate threads
5. **Performance Gain**: ~5-10x faster inference compared to CPU

The final system successfully runs YOLO11n inference at 30-50+ FPS on Raspberry Pi 5 with Hailo-8L AI HAT+, dramatically improving performance over CPU-only solutions.

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-31 | 1.0 | ONNX to HEF conversion completed |
| 2026-02-01 | 1.1 | Raspberry Pi integration completed |
| 2026-02-05 | 2.0 | Combined complete guide |

---

*Generated from conversion and integration sessions, January 31 - February 1, 2026*