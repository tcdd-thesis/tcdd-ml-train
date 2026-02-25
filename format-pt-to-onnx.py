# Export trained model to ONNX for Hailo conversion
#
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

from ultralytics import YOLO
from ultralytics.nn.modules.head import Detect

model_pt = "models/v0-20250827.1a.pt"  # adjust path if needed

# ── Patch Detect head to output raw convolutions ────────────────────────
# Save the original so we can restore it after export (good hygiene)
_original_detect_forward = Detect.forward


def _hailo_detect_forward(self, x):
    """Return per-scale raw conv outputs for Hailo NMS compatibility.

    Instead of concatenating box+cls and decoding, output the 6 individual
    conv tensors that Hailo's NMS postprocess command expects to find.
    """
    outputs = []
    for i in range(self.nl):          # nl = number of detection scales (3)
        outputs.append(self.cv2[i](x[i]))  # bbox regression conv
        outputs.append(self.cv3[i](x[i]))  # classification conv
    return tuple(outputs)


# Apply at CLASS level — Ultralytics' exporter deepcopies the model,
# so an instance-level patch would be lost.
Detect.forward = _hailo_detect_forward

# ── Export ───────────────────────────────────────────────────────────────
export_model = YOLO(model_pt)
onnx_path = export_model.export(
    format="onnx",
    opset=11,       # Hailo-validated opset — do not raise this
    dynamic=False,  # static input shape required for Hailo compilation
    imgsz=640,
)

# Restore original forward (keeps the module usable for other callers)
Detect.forward = _original_detect_forward

print(f"Hailo-compatible ONNX saved to: {onnx_path}")