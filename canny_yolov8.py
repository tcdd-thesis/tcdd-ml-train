import cv2
from ultralytics import YOLO
import numpy as np

# Placeholder image path
IMAGE_PATH = 'sample.jpg'

# Load image
image = cv2.imread(IMAGE_PATH)
if image is None:
    raise FileNotFoundError(f'Image not found: {IMAGE_PATH}')

# Apply Gaussian blur before Canny edge detection
blurred = cv2.GaussianBlur(image, (5, 5), 0)

# Apply Canny edge detection with adjusted thresholds
edges = cv2.Canny(blurred, 50, 150)

# Load YOLOv8 model (pretrained on COCO)
model = YOLO('yolov8n.pt')

# Run YOLOv8 detection
results = model(IMAGE_PATH)

# Draw YOLOv8 results on image
annotated_img = results[0].plot()

# Crop around the most confident detection (highlight)
detections = results[0].boxes
if detections is not None and len(detections) > 0:
    # Get the most confident detection
    best_idx = detections.conf.argmax().item()
    box = detections.xyxy[best_idx].cpu().numpy().astype(int)
    x1, y1, x2, y2 = box
    cropped_img = image[y1:y2, x1:x2]
    # Enhance contrast in cropped highlight
    cropped_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
    cropped_eq = cv2.equalizeHist(cropped_gray)
    cropped_blur = cv2.GaussianBlur(cropped_eq, (5, 5), 0)
    cropped_edges = cv2.Canny(cropped_blur, 50, 150)
else:
    cropped_img = image
    cropped_edges = edges

# Show results in resizable windows
window_size = (1920, 1080)  # width, height

def show_resized(title, img):
    h, w = img.shape[:2]
    scale_w = window_size[0] / w
    scale_h = window_size[1] / h
    scale = min(scale_w, scale_h, 1.0)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)))
    cv2.imshow(title, resized)

show_resized('Canny Edges', edges)
show_resized('YOLOv8 Detection', annotated_img)
show_resized('Cropped Highlight', cropped_img)
show_resized('Cropped Edges', cropped_edges)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Optionally, save results
cv2.imwrite('edges_output.jpg', edges)
cv2.imwrite('yolo_output.jpg', annotated_img)
cv2.imwrite('cropped_highlight.jpg', cropped_img)
cv2.imwrite('cropped_edges.jpg', cropped_edges)
