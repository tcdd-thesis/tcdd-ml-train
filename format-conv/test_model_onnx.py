"""
Memory-efficient YOLOv8 ONNX inference on MOVA0571.avi
Processes video with ONNX Runtime for optimized performance
"""
import gc
from ultralytics import YOLO
from pathlib import Path

# Configuration
MODEL_PATH = "../Model/v0-20250827.1a.onnx"  # ONNX model
VIDEO_PATH = "Vids/MOVA0571.avi"
OUTPUT_NAME = "mova_test_onnx"

# Detection parameters (optimized)
CONF_THRESHOLD = 0.15
IOU_THRESHOLD = 0.3

def main():
    print("="*70)
    print("🚀 MEMORY-EFFICIENT YOLOV8 ONNX INFERENCE - MOVA0571.AVI")
    print("="*70)
    
    # Verify paths
    model_path = Path(MODEL_PATH)
    video_path = Path(VIDEO_PATH)
    
    if not model_path.exists():
        print(f"❌ Error: ONNX model not found at {model_path}")
        print(f"💡 Export your model to ONNX format using:")
        print(f"   from ultralytics import YOLO")
        print(f"   model = YOLO('path/to/model.pt')")
        print(f"   model.export(format='onnx')")
        return
    
    if not video_path.exists():
        print(f"❌ Error: Video not found at {video_path}")
        return
    
    print(f"\n📁 Model: {model_path} (ONNX format)")
    print(f"📁 Video: {video_path}")
    print(f"📊 Settings: conf={CONF_THRESHOLD}, iou={IOU_THRESHOLD}")
    print(f"💾 Memory optimization: ENABLED")
    print(f"⚡ ONNX Runtime acceleration: ENABLED")
    print("\n" + "-"*70)
    
    # Load ONNX model
    print("\n⏳ Loading YOLOv8 ONNX model...")
    try:
        model = YOLO(str(model_path), task='detect')
        print("✓ ONNX model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load ONNX model: {e}")
        print("💡 Make sure onnxruntime is installed: pip install onnxruntime")
        return
    
    # Run inference with memory-efficient settings
    print("\n🎬 Starting video processing with ONNX...")
    print("💡 Processing with memory optimization...")
    print("-"*70 + "\n")
    
    try:
        results = model.predict(
            source=str(video_path),
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
            save=True,
            save_txt=True,
            save_conf=True,
            project="runs/detect",
            name=OUTPUT_NAME,
            exist_ok=True,
            max_det=300,
            verbose=True,
            stream=True,  # Stream results to reduce memory usage
            vid_stride=1,  # Process every frame
        )
        
        # Process results in streaming mode to manage memory
        frame_count = 0
        for r in results:
            frame_count += 1
            
            # Periodically force garbage collection every 500 frames
            if frame_count % 500 == 0:
                gc.collect()
                print(f"💾 Memory cleanup at frame {frame_count}")
        
        print("\n" + "-"*70)
        print(f"\n✅ Processing complete! Processed {frame_count} frames")
        print(f"📁 Output saved to: runs/detect/{OUTPUT_NAME}/")
        print(f"   - Annotated video: MOVA0571.avi")
        print(f"   - Detection labels: labels/*.txt")
        print(f"\n⚡ ONNX Performance benefits:")
        print(f"   - Optimized inference speed")
        print(f"   - Cross-platform compatibility")
        print(f"   - Hardware acceleration support")
        
    except MemoryError as e:
        print(f"\n❌ Memory Error: {e}")
        print("💡 The video is too large. Consider:")
        print("   1. Closing other applications")
        print("   2. Processing in smaller segments")
        print("   3. Using a machine with more RAM")
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        print(f"Type: {type(e).__name__}")
    finally:
        # Clean up
        gc.collect()
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
