# Hailo ONNX to HEF Conversion Guide

## Overview

This document provides a comprehensive guide for converting a YOLO11n ONNX model to Hailo Executable Format (HEF) for deployment on Raspberry Pi 5 with Hailo-8L AI HAT+.

**Date:** January 31, 2026  
**Model:** YOLO11n (1 class: label detection)  
**Target Hardware:** Hailo-8L (Raspberry Pi 5 AI HAT+)  
**Source Format:** `.onnx` (from Ultralytics training)  
**Target Format:** `.hef` (Hailo Executable Format)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [VM Setup](#vm-setup)
3. [Hailo SW Suite Installation](#hailo-sw-suite-installation)
4. [Conversion Process](#conversion-process)
5. [Troubleshooting](#troubleshooting)
6. [Final Output](#final-output)
7. [Next Steps: Raspberry Pi Deployment](#next-steps-raspberry-pi-deployment)

---

## Prerequisites

### Hardware Requirements

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

---

## Troubleshooting

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

## Final Output

### Successful Compilation Results

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

## Next Steps: Raspberry Pi Deployment

### Step 1: Transfer HEF to Raspberry Pi

From VM:
```bash
scp /home/mariobag/shared_with_docker/yolov11n.hef pi@<RPI_IP>:/home/pi/models/
```

Or from Windows:
```powershell
# First copy from VM to Windows
scp mariobag@vm-ubuntu:/home/mariobag/shared_with_docker/yolov11n.hef C:\temp\

# Then to Raspberry Pi
scp C:\temp\yolov11n.hef pi@<RPI_IP>:/home/pi/models/
```

### Step 2: Install HailoRT on Raspberry Pi

```bash
# On Raspberry Pi 5
sudo apt update
sudo apt install hailo-all
```

### Step 3: Verify Hailo Device

```bash
hailortcli fw-control identify
```

### Step 4: Run Inference

Example Python code for inference:

```python
from hailo_platform import HEF, VDevice, ConfigureParams, InferVStreams, InputVStreamParams, OutputVStreamParams

# Load HEF
hef = HEF("/home/pi/models/yolov11n.hef")

# Configure device
with VDevice() as device:
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_group = device.configure(hef, configure_params)[0]
    
    # Run inference
    # ... (implementation depends on your application)
```

---

## Training Configuration Reference

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

---

## Quick Reference Commands

### Hailo Container

| Command | Purpose |
|---------|---------|
| `hailo -h` | Dataflow Compiler help |
| `hailomz compile --help` | Model Zoo compile help |
| `hailortcli -h` | HailoRT CLI help |

### Conversion (Inside Container)

```bash
# One-command conversion (RECOMMENDED)
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

## Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Model Zoo GitHub](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo SW Suite Documentation](https://hailo.ai/developer-zone/documentation/)
- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-31 | 1.0 | Initial conversion completed |

---

*Generated from conversion session on January 31, 2026*
