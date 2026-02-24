image_dir = 'datasets/traffic-signs-detection1/train/images'
data_yaml = 'datasets/traffic-signs-detection1/data.yaml'
epoch_test = 1
epoch_train = 100

# Import Essential Libraries
import os
import random
import pandas as pd
from PIL import Image
import cv2
from ultralytics import YOLO
from IPython.display import Video
import numpy as np  
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(style='darkgrid')
import pathlib
import glob
from tqdm.notebook import trange, tqdm
from ultralytics import YOLO
import warnings
warnings.filterwarnings('ignore')

# Configure the visual appearance of Seaborn plots
sns.set(rc={'axes.facecolor': '#eae8fa'}, style='darkgrid')

# Import all images from the directory
image_files = os.listdir(image_dir)
imported_images = image_files
print(f'Total images imported: {len(imported_images)}')

# Print the shape of all imported images from the directory
image_files = os.listdir(image_dir)
for idx, image_name in enumerate(image_files):
    img_path = os.path.join(image_dir, image_name)
    img = cv2.imread(img_path)
    if img is not None:
        h, w, c = img.shape
        print(f'Image {idx+1}: {image_name} - shape: {w}x{h}, channels: {c}')
    else:
        print(f'Image {idx+1}: {image_name} - could not be loaded.')

model = YOLO('yolov8n.pt')  # You can use yolov8s.pt, yolov8m.pt, etc.
results = model.train(
    data=data_yaml,     # Full path to the dataset config file
    epochs=epoch_test,  # Number of epochs
    imgsz=640,          # Image size
    batch=16            # Batch size
)